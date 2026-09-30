"""
NetSpout Gate 13B — Native gNMI Server & OpenConfig Core Engine Verification Suite.

Covers:
  - Positive Protocol & Telemetry Tests: T13B-01 through T13B-12
  - Negative & Controlled-Failure Tests: T13B-NEG-01 through T13B-NEG-08 (Controlled Failures A-J)
  - Multi-Vendor OpenConfig + Vendor-Native Richness Verification across:
      * CISCO_IOS_XR (node-cisco8k)
      * CISCO_IOS_XE (node-cat-leaf)
      * ARISTA_EOS   (node-arista-spine)
      * JUNIPER_JUNOS (node-juniper-ptx)
  - Cross-Transport State Coherence (gNMI <-> SNMP <-> Syslog <-> NetFlow/IPFIX)
  - External Client Interoperability (pygnmi + gnmic CLI)
"""

import json
import os
import shutil
import socket
import subprocess
import sys
import threading
import time
import unittest
from typing import Any, Dict, Iterator, List

import grpc

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC_DIR = os.path.join(REPO_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from netspout_core.gnmi import (
    GNMI_SEMVER,
    VALID_PHASES,
    VENDOR_PROFILES,
    VendorProfileId,
    NativeGnmiServer,
    NativeGnmiServerConfig,
    ScenarioStateStore,
    TelemetrySensorRegistry,
    generate_ephemeral_tls_material,
    parse_xpath_string,
    to_proto_path,
)
from netspout_core.gnmi.proto import gnmi_pb2, gnmi_pb2_grpc
from netspout_core.snmp_agent import build_service_provider_cisco_oid_store


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _proto_path(xpath: str, origin: str = "", target: str = "") -> gnmi_pb2.Path:
    if not xpath or not xpath.strip():
        return gnmi_pb2.Path(origin=origin, target=target)
    parsed = parse_xpath_string(xpath, default_origin=origin, target=target)
    return to_proto_path(parsed)


class TestGate13BGnmiCore(unittest.TestCase):
    """Gate 13B comprehensive test suite for NativeGnmiServer and OpenConfig Core Engine."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.port = _find_free_port()
        cls.state_store = ScenarioStateStore(scenario_id="openconfig_mdt_streaming", initial_phase="BASELINE")
        cls.registry = TelemetrySensorRegistry()
        cls.config = NativeGnmiServerConfig(
            bind_address="127.0.0.1",
            bind_port=cls.port,
            security_mode="INSECURE_LOCAL_LAB",
            require_metadata_auth=False,
            default_target="node-cisco8k",
            min_sample_interval_ns=500_000_000,
        )
        cls.server = NativeGnmiServer(
            config=cls.config,
            state_store=cls.state_store,
            sensor_registry=cls.registry,
        )
        cls.server.start()
        cls.channel = grpc.insecure_channel(cls.server.endpoint)
        cls.stub = gnmi_pb2_grpc.gNMIStub(cls.channel)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.channel.close()
        cls.server.stop(grace=0.2)

    def setUp(self) -> None:
        self.state_store.set_phase("BASELINE", advance_tick=False)
        self.state_store._tick = 0

    # =========================================================================
    # POSITIVE TESTS: T13B-01 .. T13B-12
    # =========================================================================

    def test_t13b_01_capabilities_all_four_vendors(self) -> None:
        """T13B-01: Capabilities RPC returns gNMI 0.10.0, encodings, and vendor-specific models."""
        vendor_targets = [
            ("node-cisco8k", VendorProfileId.CISCO_IOS_XR, "Cisco-IOS-XR-infra-statsd-oper"),
            ("node-cat-leaf", VendorProfileId.CISCO_IOS_XE, "Cisco-IOS-XE-interfaces-oper"),
            ("node-arista-spine", VendorProfileId.ARISTA_EOS, "eos_native"),
            ("node-juniper-ptx", VendorProfileId.JUNIPER_JUNOS, "junos-telemetry-interface"),
        ]
        for target_id, vendor_id, expected_native_model in vendor_targets:
            resp = self.stub.Capabilities(
                gnmi_pb2.CapabilityRequest(),
                metadata=[("x-netspout-target", target_id)],
            )
            self.assertEqual(resp.gNMI_version, GNMI_SEMVER)
            self.assertEqual(
                list(resp.supported_encodings),
                [gnmi_pb2.JSON, gnmi_pb2.PROTO, gnmi_pb2.JSON_IETF],
            )
            model_names = {m.name for m in resp.supported_models}
            self.assertIn("openconfig-interfaces", model_names)
            self.assertIn("openconfig-bgp", model_names)
            self.assertIn("openconfig-qos", model_names)
            self.assertIn("openconfig-platform", model_names)
            self.assertIn("openconfig-terminal-device", model_names)
            self.assertIn(expected_native_model, model_names)
            self.assertEqual(len(resp.supported_models), len(VENDOR_PROFILES[vendor_id].supported_models))

    def test_t13b_02_get_datatypes_prefix_and_wildcards(self) -> None:
        """T13B-02: Get RPC supports ALL, CONFIG, STATE, OPERATIONAL, prefix + multi-path, and wildcards."""
        # 1. Check ALL, CONFIG, STATE, OPERATIONAL on /interfaces/interface[name=HundredGigE0/0/0/0]
        for dtype in [
            gnmi_pb2.GetRequest.ALL,
            gnmi_pb2.GetRequest.CONFIG,
            gnmi_pb2.GetRequest.STATE,
            gnmi_pb2.GetRequest.OPERATIONAL,
        ]:
            req = gnmi_pb2.GetRequest(
                path=[_proto_path("/interfaces/interface[name=HundredGigE0/0/0/0]")],
                type=dtype,
                encoding=gnmi_pb2.JSON_IETF,
            )
            resp = self.stub.Get(req, metadata=[("x-netspout-target", "node-cisco8k")])
            self.assertEqual(len(resp.notification), 1)
            payload = json.loads(resp.notification[0].update[0].val.json_ietf_val.decode("utf-8"))
            if dtype == gnmi_pb2.GetRequest.CONFIG:
                self.assertIn("openconfig-interfaces:config", payload)
                self.assertNotIn("openconfig-interfaces:state", payload)
            elif dtype in (gnmi_pb2.GetRequest.STATE, gnmi_pb2.GetRequest.OPERATIONAL):
                self.assertIn("openconfig-interfaces:state", payload)
                self.assertNotIn("openconfig-interfaces:config", payload)
            else:
                self.assertIn("openconfig-interfaces:config", payload)
                self.assertIn("openconfig-interfaces:state", payload)

        # 2. Wildcard expansion /interfaces/interface[name=*]/state
        w_req = gnmi_pb2.GetRequest(
            path=[_proto_path("/interfaces/interface[name=*]/state")],
            type=gnmi_pb2.GetRequest.STATE,
            encoding=gnmi_pb2.JSON_IETF,
        )
        w_resp = self.stub.Get(w_req, metadata=[("x-netspout-target", "node-cisco8k")])
        self.assertGreaterEqual(len(w_resp.notification), 2)

        # 3. Prefix + multi-path
        p_req = gnmi_pb2.GetRequest(
            prefix=_proto_path("/interfaces/interface[name=HundredGigE0/0/0/0]/state", target="node-cisco8k"),
            path=[
                _proto_path("oper-status"),
                _proto_path("counters"),
            ],
            encoding=gnmi_pb2.JSON_IETF,
        )
        p_resp = self.stub.Get(p_req)
        self.assertEqual(len(p_resp.notification), 2)

    def test_t13b_03_encodings_json_ietf_json_and_proto(self) -> None:
        """T13B-03: JSON_IETF stringifies uint64 counters per RFC 7951; JSON uses numbers; PROTO emits TypedValue."""
        path = _proto_path("/interfaces/interface[name=HundredGigE0/0/0/0]/state/counters")

        # 1. JSON_IETF: uint64 counters must be strings
        resp_ietf = self.stub.Get(
            gnmi_pb2.GetRequest(path=[path], encoding=gnmi_pb2.JSON_IETF),
            metadata=[("x-netspout-target", "node-cisco8k")],
        )
        val_ietf = json.loads(resp_ietf.notification[0].update[0].val.json_ietf_val.decode("utf-8"))
        self.assertIsInstance(val_ietf["in-octets"], str)
        self.assertEqual(val_ietf["in-octets"], "98504200000")

        # 2. JSON: counters are standard JSON integers
        resp_json = self.stub.Get(
            gnmi_pb2.GetRequest(path=[path], encoding=gnmi_pb2.JSON),
            metadata=[("x-netspout-target", "node-cisco8k")],
        )
        val_json = json.loads(resp_json.notification[0].update[0].val.json_val.decode("utf-8"))
        self.assertIsInstance(val_json["in-octets"], int)
        self.assertEqual(val_json["in-octets"], 98504200000)

        # 3. PROTO: container decomposes into leaf Updates with scalar TypedValues
        resp_proto = self.stub.Get(
            gnmi_pb2.GetRequest(path=[path], encoding=gnmi_pb2.PROTO),
            metadata=[("x-netspout-target", "node-cisco8k")],
        )
        updates = resp_proto.notification[0].update
        self.assertGreaterEqual(len(updates), 6)
        leaf_map = {u.path.elem[-1].name: u.val for u in updates}
        self.assertEqual(leaf_map["in-octets"].uint_val, 98504200000)
        self.assertEqual(leaf_map["out-octets"].uint_val, 91204200000)

    def test_t13b_04_subscribe_once_all_vendors(self) -> None:
        """T13B-04: Subscribe ONCE emits notifications followed by sync_response=true and closes stream."""
        for target_id in ["node-cisco8k", "node-cat-leaf", "node-arista-spine", "node-juniper-ptx"]:
            sub_req = gnmi_pb2.SubscribeRequest(
                subscribe=gnmi_pb2.SubscriptionList(
                    prefix=_proto_path("", target=target_id),
                    mode=gnmi_pb2.SubscriptionList.ONCE,
                    encoding=gnmi_pb2.JSON_IETF,
                    subscription=[
                        gnmi_pb2.Subscription(path=_proto_path("/system/state")),
                        gnmi_pb2.Subscription(path=_proto_path("/interfaces/interface[name=*]/state/counters")),
                    ],
                )
            )
            responses = list(self.stub.Subscribe(iter([sub_req])))
            self.assertGreaterEqual(len(responses), 3)
            self.assertTrue(responses[-1].sync_response)
            notif_count = sum(1 for r in responses if r.HasField("update"))
            self.assertGreaterEqual(notif_count, 2)

    def test_t13b_05_subscribe_poll_across_phases(self) -> None:
        """T13B-05: Subscribe POLL returns fresh snapshots on each client Poll() request."""
        req_q: List[gnmi_pb2.SubscribeRequest] = []
        cond = threading.Condition()
        closed = False

        def _req_gen() -> Iterator[gnmi_pb2.SubscribeRequest]:
            while True:
                with cond:
                    while not req_q and not closed:
                        cond.wait(timeout=1.0)
                    if req_q:
                        item = req_q.pop(0)
                    elif closed:
                        return
                    else:
                        continue
                yield item

        with cond:
            req_q.append(
                gnmi_pb2.SubscribeRequest(
                    subscribe=gnmi_pb2.SubscriptionList(
                        prefix=_proto_path("", target="node-cisco8k"),
                        mode=gnmi_pb2.SubscriptionList.POLL,
                        encoding=gnmi_pb2.JSON_IETF,
                        subscription=[
                            gnmi_pb2.Subscription(
                                path=_proto_path(
                                    "/interfaces/interface[name=HundredGigE0/0/0/0]/state/oper-status"
                                )
                            )
                        ],
                    )
                )
            )
            cond.notify_all()

        stream = self.stub.Subscribe(_req_gen())

        # Initial snapshot + sync_response
        r1 = next(stream)
        self.assertTrue(r1.HasField("update"))
        self.assertEqual(json.loads(r1.update.update[0].val.json_ietf_val.decode()), "UP")
        r2 = next(stream)
        self.assertTrue(r2.sync_response)

        # Advance to FAILOVER and send Poll()
        self.state_store.set_phase("FAILOVER")
        with cond:
            req_q.append(gnmi_pb2.SubscribeRequest(poll=gnmi_pb2.Poll()))
            cond.notify_all()

        r3 = next(stream)
        self.assertTrue(r3.HasField("update"))
        self.assertEqual(json.loads(r3.update.update[0].val.json_ietf_val.decode()), "DOWN")
        r4 = next(stream)
        self.assertTrue(r4.sync_response)

        with cond:
            closed = True
            cond.notify_all()

    def test_t13b_06_subscribe_stream_sample_cadence(self) -> None:
        """T13B-06: Subscribe STREAM / SAMPLE emits initial sync then periodic counter samples >= 500ms."""
        sub_req = gnmi_pb2.SubscribeRequest(
            subscribe=gnmi_pb2.SubscriptionList(
                prefix=_proto_path("", target="node-cisco8k"),
                mode=gnmi_pb2.SubscriptionList.STREAM,
                encoding=gnmi_pb2.JSON_IETF,
                subscription=[
                    gnmi_pb2.Subscription(
                        path=_proto_path("/interfaces/interface[name=HundredGigE0/0/0/0]/state/counters"),
                        mode=gnmi_pb2.SAMPLE,
                        sample_interval=500_000_000,  # 500ms floor
                    )
                ],
            )
        )
        call = self.stub.Subscribe(iter([sub_req]))
        try:
            # 1. Initial notification
            init_msg = next(call)
            self.assertTrue(init_msg.HasField("update"))
            c0 = int(json.loads(init_msg.update.update[0].val.json_ietf_val.decode())["in-octets"])

            # 2. Initial sync_response
            sync_msg = next(call)
            self.assertTrue(sync_msg.sync_response)

            # 3. Periodic sample #1
            s1_msg = next(call)
            self.assertTrue(s1_msg.HasField("update"))
            c1 = int(json.loads(s1_msg.update.update[0].val.json_ietf_val.decode())["in-octets"])
            self.assertGreater(c1, c0)
        finally:
            call.cancel()

    def test_t13b_07_subscribe_stream_on_change_phase_transitions(self) -> None:
        """T13B-07: Subscribe STREAM / ON_CHANGE emits immediately on phase transitions."""
        sub_req = gnmi_pb2.SubscribeRequest(
            subscribe=gnmi_pb2.SubscriptionList(
                prefix=_proto_path("", target="node-cisco8k"),
                mode=gnmi_pb2.SubscriptionList.STREAM,
                encoding=gnmi_pb2.JSON_IETF,
                subscription=[
                    gnmi_pb2.Subscription(
                        path=_proto_path("/interfaces/interface[name=HundredGigE0/0/0/0]/state/oper-status"),
                        mode=gnmi_pb2.ON_CHANGE,
                    )
                ],
            )
        )
        call = self.stub.Subscribe(iter([sub_req]))
        try:
            m1 = next(call)
            self.assertEqual(json.loads(m1.update.update[0].val.json_ietf_val.decode()), "UP")
            m2 = next(call)
            self.assertTrue(m2.sync_response)

            # Trigger transition to FAILOVER (oper-status -> DOWN)
            self.state_store.set_phase("FAILOVER")
            m3 = next(call)
            self.assertEqual(json.loads(m3.update.update[0].val.json_ietf_val.decode()), "DOWN")

            # Trigger transition to RECOVERY (oper-status -> UP)
            self.state_store.set_phase("RECOVERY")
            m4 = next(call)
            self.assertEqual(json.loads(m4.update.update[0].val.json_ietf_val.decode()), "UP")
        finally:
            call.cancel()

    def test_t13b_08_multi_vendor_openconfig_and_native_richness(self) -> None:
        """
        T13B-08: Prove all 11 OpenConfig domains and all 4 vendor-native origins,
        including rich telemetry fields impossible in legacy SNMP polling.
        """
        self.state_store.set_phase("DEGRADE")

        # 1. All OpenConfig domains on Cisco IOS XR
        oc_paths = [
            "/interfaces/interface[name=HundredGigE0/0/0/0]/state/counters",
            "/interfaces/interface[name=HundredGigE0/0/0/0]/subinterfaces/subinterface[index=0]/ipv4/addresses/address[ip=*]/state",
            "/lldp/interfaces/interface[name=HundredGigE0/0/0/0]/neighbors/neighbor[id=*]/state",
            "/lacp/interfaces/interface[name=Bundle-Ether10]/members/member[interface=HundredGigE0/0/0/0]/state",
            "/network-instances/network-instance[name=default]/protocols/protocol[identifier=BGP][name=BGP]/bgp/neighbors/neighbor[neighbor-address=10.100.1.2]/state",
            "/network-instances/network-instance[name=default]/afts/ipv4-unicast/ipv4-entries/ipv4-entry[prefix=10.100.0.0/16]/state",
            "/qos/interfaces/interface[interface-id=HundredGigE0/0/0/0]/output/queues/queue[name=BE-0]/state",
            "/components/component[name=Chassis-0]/state",
            "/components/component[name=Transceiver-HundredGigE0/0/0/0]/transceiver/state",
            "/system/state",
            "/system/cpus/cpu[index=0]/state",
            "/system/memory/state",
        ]
        for xp in oc_paths:
            resp = self.stub.Get(
                gnmi_pb2.GetRequest(path=[_proto_path(xp)], encoding=gnmi_pb2.JSON_IETF),
                metadata=[("x-netspout-target", "node-cisco8k")],
            )
            self.assertGreaterEqual(len(resp.notification), 1, f"Empty notification for {xp}")

        # Verify Arista EVPN/VXLAN OpenConfig domain
        evpn_resp = self.stub.Get(
            gnmi_pb2.GetRequest(
                path=[_proto_path("/network-instances/network-instance[name=default]/evpn/state")],
                encoding=gnmi_pb2.JSON_IETF,
            ),
            metadata=[("x-netspout-target", "node-arista-spine")],
        )
        evpn_payload = json.loads(evpn_resp.notification[0].update[0].val.json_ietf_val.decode())
        self.assertEqual(evpn_payload["vni-id"], 10100)
        self.assertGreater(evpn_payload["type2-mac-ip-routes"], 100)

        # 2. Verify all 4 vendor-native origins
        native_queries = [
            (
                "node-cisco8k",
                "Cisco-IOS-XR-qos-ma-oper",
                "/qos/interface-table/interface[interface-name=HundredGigE0/0/0/0]/output/service-policy-names/service-policy-instance/statistics",
            ),
            (
                "node-cat-leaf",
                "Cisco-IOS-XE-interfaces-oper",
                "/interfaces/interface[name=FortyGigE1/0/1]/statistics",
            ),
            (
                "node-arista-spine",
                "eos_native",
                "/Sysdb/hardware/counter/Lanz/intf[intf=Ethernet1/1]/queueStatus",
            ),
            (
                "node-juniper-ptx",
                "junos",
                "/junos/system/linecard/qmon[interface=et-0/0/0]",
            ),
        ]
        for target_id, origin, xp in native_queries:
            resp = self.stub.Get(
                gnmi_pb2.GetRequest(
                    path=[_proto_path(xp, origin=origin, target=target_id)],
                    encoding=gnmi_pb2.JSON_IETF,
                )
            )
            self.assertEqual(len(resp.notification), 1)
            self.assertEqual(resp.notification[0].prefix.origin, origin)

    def test_t13b_09_prefix_compression_and_suppress_redundant(self) -> None:
        """T13B-09: Prefix compression splits Notification.prefix and relative Update.path."""
        req = gnmi_pb2.GetRequest(
            prefix=_proto_path("/interfaces/interface[name=HundredGigE0/0/0/0]", target="node-cisco8k"),
            path=[_proto_path("state/counters")],
            encoding=gnmi_pb2.JSON_IETF,
        )
        resp = self.stub.Get(req)
        notif = resp.notification[0]
        self.assertEqual([e.name for e in notif.prefix.elem], ["interfaces", "interface"])
        self.assertEqual(notif.prefix.elem[1].key["name"], "HundredGigE0/0/0/0")
        self.assertEqual([e.name for e in notif.update[0].path.elem], ["state", "counters"])

    def test_t13b_10_cross_transport_coherence_gnmi_snmp_syslog_netflow(self) -> None:
        """
        T13B-10: Prove 100% mathematical coherence across gNMI, SNMP (Gate 12C OID store),
        Syslog events, and NetFlow/IPFIX flow metrics across BASELINE, DEGRADE, FAILOVER, RECOVERY.
        """
        oper_status_to_int = {"UP": 1, "DOWN": 2}
        bgp_state_to_int = {"ESTABLISHED": 6, "ACTIVE": 3, "IDLE": 1}

        for phase in VALID_PHASES:
            self.state_store.set_phase(phase, advance_tick=False)
            self.state_store._tick = 0
            snmp_store = build_service_provider_cisco_oid_store(phase, seed=42, device_id="cisco-asr9k-pe1")

            # Query gNMI server on cisco-asr9k-pe1 for primary interface state, counters, and BGP
            if_resp = self.stub.Get(
                gnmi_pb2.GetRequest(
                    path=[_proto_path("/interfaces/interface[name=HundredGigE0/0/0/0]/state")],
                    encoding=gnmi_pb2.JSON,
                ),
                metadata=[("x-netspout-target", "cisco-asr9k-pe1")],
            )
            if_state = json.loads(if_resp.notification[0].update[0].val.json_val.decode())

            bgp_resp = self.stub.Get(
                gnmi_pb2.GetRequest(
                    path=[
                        _proto_path(
                            "/network-instances/network-instance[name=default]/protocols/protocol[identifier=BGP][name=BGP]/bgp/neighbors/neighbor[neighbor-address=10.255.0.2]/state"
                        )
                    ],
                    encoding=gnmi_pb2.JSON,
                ),
                metadata=[("x-netspout-target", "cisco-asr9k-pe1")],
            )
            bgp_state = json.loads(bgp_resp.notification[0].update[0].val.json_val.decode())

            # Assert exact mathematical equality with SNMP OID store (ifOperStatus.1, ifHCInOctets.1, ifHCOutOctets.1, ifInErrors.1, bgpPeerState)
            self.assertEqual(
                oper_status_to_int[if_state["oper-status"]],
                snmp_store.get_exact("1.3.6.1.2.1.2.2.1.8.1").value,
            )
            self.assertEqual(
                if_state["counters"]["in-octets"],
                snmp_store.get_exact("1.3.6.1.2.1.31.1.1.1.6.1").value,
            )
            self.assertEqual(
                if_state["counters"]["out-octets"],
                snmp_store.get_exact("1.3.6.1.2.1.31.1.1.1.10.1").value,
            )
            self.assertEqual(
                if_state["counters"]["in-errors"],
                snmp_store.get_exact("1.3.6.1.2.1.2.2.1.14.1").value,
            )
            self.assertEqual(
                bgp_state_to_int[bgp_state["session-state"]],
                snmp_store.get_exact("1.3.6.1.2.1.15.3.1.2.198.51.100.1").value,
            )

            # Assert Syslog and NetFlow coherence from shared state snapshot
            snap = self.state_store.get_snapshot("cisco-asr9k-pe1")
            syslogs = snap.to_syslog_events()
            netflow = snap.to_netflow_coherence_summary()
            snmp_coh = snap.to_snmp_coherence_summary()
            self.assertGreaterEqual(len(syslogs), 1)
            self.assertEqual(snmp_coh["ifHCInOctets.1"], if_state["counters"]["in-octets"])
            self.assertEqual(netflow["in_bytes_total"], if_state["counters"]["in-octets"])

    def test_t13b_11_security_modes_tls_mtls_and_redaction(self) -> None:
        """T13B-11: Verify TLS_SERVER_AUTH, MTLS_CLIENT_AUTH, and credential redaction."""
        tls_mat = generate_ephemeral_tls_material()

        # 1. TLS_SERVER_AUTH
        tls_port = _find_free_port()
        tls_cfg = NativeGnmiServerConfig(
            bind_address="127.0.0.1",
            bind_port=tls_port,
            security_mode="TLS_SERVER_AUTH",
            require_metadata_auth=True,
            username="netspout-lab",
            password="netspout-lab-pass",
            tls_ca_cert_pem=tls_mat.ca_cert_pem,
            tls_server_cert_pem=tls_mat.server_cert_pem,
            tls_server_key_pem=tls_mat.server_key_pem,
        )
        redacted = tls_cfg.to_redacted_dict()
        self.assertEqual(redacted["password"], "***REDACTED***")
        self.assertEqual(redacted["tls_server_key_pem"], "***REDACTED***")

        tls_srv = NativeGnmiServer(config=tls_cfg, state_store=self.state_store)
        tls_srv.start()
        try:
            creds = grpc.ssl_channel_credentials(root_certificates=tls_mat.ca_cert_pem)
            with grpc.secure_channel(tls_srv.endpoint, creds) as ch:
                stub = gnmi_pb2_grpc.gNMIStub(ch)
                cap = stub.Capabilities(
                    gnmi_pb2.CapabilityRequest(),
                    metadata=[("username", "netspout-lab"), ("password", "netspout-lab-pass")],
                )
                self.assertEqual(cap.gNMI_version, GNMI_SEMVER)
        finally:
            tls_srv.stop(grace=0.1)

        # 2. MTLS_CLIENT_AUTH
        mtls_port = _find_free_port()
        mtls_cfg = NativeGnmiServerConfig(
            bind_address="127.0.0.1",
            bind_port=mtls_port,
            security_mode="MTLS_CLIENT_AUTH",
            tls_ca_cert_pem=tls_mat.ca_cert_pem,
            tls_server_cert_pem=tls_mat.server_cert_pem,
            tls_server_key_pem=tls_mat.server_key_pem,
        )
        mtls_srv = NativeGnmiServer(config=mtls_cfg, state_store=self.state_store)
        mtls_srv.start()
        try:
            mtls_creds = grpc.ssl_channel_credentials(
                root_certificates=tls_mat.ca_cert_pem,
                private_key=tls_mat.client_key_pem,
                certificate_chain=tls_mat.client_cert_pem,
            )
            with grpc.secure_channel(mtls_srv.endpoint, mtls_creds) as ch:
                stub = gnmi_pb2_grpc.gNMIStub(ch)
                cap = stub.Capabilities(gnmi_pb2.CapabilityRequest())
                self.assertEqual(cap.gNMI_version, GNMI_SEMVER)
        finally:
            mtls_srv.stop(grace=0.1)

    def test_t13b_12_external_clients_pygnmi_and_gnmic_plus_concurrency(self) -> None:
        """T13B-12: Verify external clients (pygnmi + gnmic CLI) and 16 concurrent streams."""
        # 1. pygnmi client verification
        from pygnmi.client import gNMIclient

        with gNMIclient(
            target=("127.0.0.1", self.port),
            insecure=True,
        ) as gc:
            cap = gc.capabilities()
            self.assertEqual(cap.get("gnmi_version") or cap.get("gNMI_version"), GNMI_SEMVER)
            get_res = gc.get(
                path=["/interfaces/interface[name=HundredGigE0/0/0/0]/state/oper-status"],
                datatype="state",
                encoding="json_ietf",
            )
            self.assertEqual(len(get_res["notification"]), 1)

        # 2. gnmic CLI verification
        gnmic_bin = shutil.which("gnmic") or "/opt/homebrew/bin/gnmic"
        if os.path.exists(gnmic_bin):
            cmd = [
                gnmic_bin,
                "-a",
                f"127.0.0.1:{self.port}",
                "--insecure",
                "capabilities",
                "--format",
                "json",
            ]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=10, check=True)
            self.assertIn("0.10.0", proc.stdout)

        # 3. 16 concurrent STREAM subscriptions benchmark
        calls = []
        try:
            for _ in range(16):
                req = gnmi_pb2.SubscribeRequest(
                    subscribe=gnmi_pb2.SubscriptionList(
                        prefix=_proto_path("", target="node-cisco8k"),
                        mode=gnmi_pb2.SubscriptionList.STREAM,
                        encoding=gnmi_pb2.JSON_IETF,
                        subscription=[
                            gnmi_pb2.Subscription(
                                path=_proto_path("/system/state"),
                                mode=gnmi_pb2.ON_CHANGE,
                            )
                        ],
                    )
                )
                c = self.stub.Subscribe(iter([req]))
                first = next(c)
                sync = next(c)
                self.assertTrue(first.HasField("update"))
                self.assertTrue(sync.sync_response)
                calls.append(c)
            self.assertGreaterEqual(self.server.diagnostics.snapshot()["peak_active_streams"], 16)
        finally:
            for c in calls:
                c.cancel()

    # =========================================================================
    # NEGATIVE & CONTROLLED-FAILURE TESTS: T13B-NEG-01 .. T13B-NEG-08
    # =========================================================================

    def test_t13b_neg_01_set_rpc_rejected_unimplemented(self) -> None:
        """T13B-NEG-01 (Controlled Failure A): Set RPC is rejected with StatusCode.UNIMPLEMENTED."""
        with self.assertRaises(grpc.RpcError) as ctx:
            self.stub.Set(gnmi_pb2.SetRequest())
        self.assertEqual(ctx.exception.code(), grpc.StatusCode.UNIMPLEMENTED)
        self.assertIn("read-only", ctx.exception.details())

    def test_t13b_neg_02_malformed_path_rejected_invalid_argument(self) -> None:
        """T13B-NEG-02 (Controlled Failure B): Malformed path syntax rejected with INVALID_ARGUMENT."""
        bad_path = gnmi_pb2.Path(elem=[gnmi_pb2.PathElem(name="interfaces[broken")])
        with self.assertRaises(grpc.RpcError) as ctx:
            self.stub.Get(gnmi_pb2.GetRequest(path=[bad_path], encoding=gnmi_pb2.JSON_IETF))
        self.assertEqual(ctx.exception.code(), grpc.StatusCode.INVALID_ARGUMENT)

    def test_t13b_neg_03_unsupported_path_and_unknown_target_not_found(self) -> None:
        """T13B-NEG-03 (Controlled Failure C): Unsupported path and unknown target return NOT_FOUND."""
        with self.assertRaises(grpc.RpcError) as ctx1:
            self.stub.Get(
                gnmi_pb2.GetRequest(
                    path=[_proto_path("/openconfig-nonexistent/foo/bar")],
                    encoding=gnmi_pb2.JSON_IETF,
                )
            )
        self.assertEqual(ctx1.exception.code(), grpc.StatusCode.NOT_FOUND)

        with self.assertRaises(grpc.RpcError) as ctx2:
            self.stub.Get(
                gnmi_pb2.GetRequest(
                    path=[_proto_path("/system/state", target="nonexistent-router-99")],
                    encoding=gnmi_pb2.JSON_IETF,
                )
            )
        self.assertEqual(ctx2.exception.code(), grpc.StatusCode.NOT_FOUND)

    def test_t13b_neg_04_foreign_vendor_origin_rejected(self) -> None:
        """T13B-NEG-04 (Controlled Failure C2): Foreign vendor-native origin on wrong vendor returns NOT_FOUND."""
        with self.assertRaises(grpc.RpcError) as ctx:
            self.stub.Get(
                gnmi_pb2.GetRequest(
                    path=[
                        _proto_path(
                            "/Sysdb/hardware/counter/Lanz/intf[intf=Ethernet1/1]/queueStatus",
                            origin="eos_native",
                            target="node-cisco8k",
                        )
                    ],
                    encoding=gnmi_pb2.JSON_IETF,
                )
            )
        self.assertEqual(ctx.exception.code(), grpc.StatusCode.NOT_FOUND)
        self.assertIn("FOREIGN_VENDOR_ORIGIN", ctx.exception.details())

    def test_t13b_neg_05_sample_interval_below_floor(self) -> None:
        """T13B-NEG-05 (Controlled Failure D): Sample interval < 500ms rejected with INVALID_ARGUMENT (or clamped when configured)."""
        sub_req = gnmi_pb2.SubscribeRequest(
            subscribe=gnmi_pb2.SubscriptionList(
                prefix=_proto_path("", target="node-cisco8k"),
                mode=gnmi_pb2.SubscriptionList.STREAM,
                encoding=gnmi_pb2.JSON_IETF,
                subscription=[
                    gnmi_pb2.Subscription(
                        path=_proto_path("/interfaces/interface[name=HundredGigE0/0/0/0]/state/counters"),
                        mode=gnmi_pb2.SAMPLE,
                        sample_interval=100_000_000,  # 100ms < 500ms floor
                    )
                ],
            )
        )
        with self.assertRaises(grpc.RpcError) as ctx:
            list(self.stub.Subscribe(iter([sub_req])))
        self.assertEqual(ctx.exception.code(), grpc.StatusCode.INVALID_ARGUMENT)
        self.assertIn("SAMPLE_INTERVAL_BELOW_FLOOR", ctx.exception.details())

        # Verify clamping mode works when clamp_sample_interval=True
        clamp_port = _find_free_port()
        clamp_srv = NativeGnmiServer(
            config=NativeGnmiServerConfig(
                bind_address="127.0.0.1",
                bind_port=clamp_port,
                clamp_sample_interval=True,
            ),
            state_store=self.state_store,
        )
        clamp_srv.start()
        try:
            with grpc.insecure_channel(clamp_srv.endpoint) as ch:
                stub = gnmi_pb2_grpc.gNMIStub(ch)
                call = stub.Subscribe(iter([sub_req]))
                first = next(call)
                sync = next(call)
                self.assertTrue(first.HasField("update"))
                self.assertTrue(sync.sync_response)
                call.cancel()
            self.assertEqual(clamp_srv.diagnostics.snapshot()["clamped_sample_intervals"], 1)
        finally:
            clamp_srv.stop(grace=0.1)

    def test_t13b_neg_06_auth_failure_unauthenticated(self) -> None:
        """T13B-NEG-06 (Controlled Failure E): Invalid metadata credentials return StatusCode.UNAUTHENTICATED."""
        with self.assertRaises(grpc.RpcError) as ctx:
            self.stub.Capabilities(
                gnmi_pb2.CapabilityRequest(),
                metadata=[("username", "attacker"), ("password", "wrong-pass")],
            )
        self.assertEqual(ctx.exception.code(), grpc.StatusCode.UNAUTHENTICATED)

    def test_t13b_neg_07_excessive_paths_and_excessive_streams(self) -> None:
        """T13B-NEG-07 (Controlled Failures F & G): >64 paths -> INVALID_ARGUMENT; >max_active_streams -> RESOURCE_EXHAUSTED."""
        # 1. Excessive paths (> 64)
        many_paths = [_proto_path("/system/state") for _ in range(65)]
        with self.assertRaises(grpc.RpcError) as ctx1:
            self.stub.Get(gnmi_pb2.GetRequest(path=many_paths, encoding=gnmi_pb2.JSON_IETF))
        self.assertEqual(ctx1.exception.code(), grpc.StatusCode.INVALID_ARGUMENT)
        self.assertIn("MAX_PATHS_EXCEEDED", ctx1.exception.details())

        # 2. Excessive active streams (> max_active_streams)
        lim_port = _find_free_port()
        lim_srv = NativeGnmiServer(
            config=NativeGnmiServerConfig(
                bind_address="127.0.0.1",
                bind_port=lim_port,
                max_active_streams=2,
            ),
            state_store=self.state_store,
        )
        lim_srv.start()
        active_calls = []
        try:
            with grpc.insecure_channel(lim_srv.endpoint) as ch:
                stub = gnmi_pb2_grpc.gNMIStub(ch)
                req = gnmi_pb2.SubscribeRequest(
                    subscribe=gnmi_pb2.SubscriptionList(
                        prefix=_proto_path("", target="node-cisco8k"),
                        mode=gnmi_pb2.SubscriptionList.STREAM,
                        encoding=gnmi_pb2.JSON_IETF,
                        subscription=[
                            gnmi_pb2.Subscription(path=_proto_path("/system/state"), mode=gnmi_pb2.ON_CHANGE)
                        ],
                    )
                )
                for _ in range(2):
                    c = stub.Subscribe(iter([req]))
                    next(c)
                    next(c)
                    active_calls.append(c)

                # 3rd stream must fail with RESOURCE_EXHAUSTED
                with self.assertRaises(grpc.RpcError) as ctx2:
                    list(stub.Subscribe(iter([req])))
                self.assertEqual(ctx2.exception.code(), grpc.StatusCode.RESOURCE_EXHAUSTED)
        finally:
            for c in active_calls:
                c.cancel()
            lim_srv.stop(grace=0.1)

    def test_t13b_neg_08_unsupported_encoding_non_loopback_and_slow_consumer(self) -> None:
        """T13B-NEG-08 (Controlled Failures H, I, J): Unsupported encoding, non-loopback guard, slow consumer overflow."""
        # 1. Unsupported encoding BYTES / ASCII -> UNIMPLEMENTED
        for bad_enc in (gnmi_pb2.BYTES, gnmi_pb2.ASCII):
            with self.assertRaises(grpc.RpcError) as ctx:
                self.stub.Get(
                    gnmi_pb2.GetRequest(path=[_proto_path("/system/state")], encoding=bad_enc)
                )
            self.assertEqual(ctx.exception.code(), grpc.StatusCode.UNIMPLEMENTED)

        # 2. Non-loopback bind without allow_non_loopback=True -> ValueError
        with self.assertRaises(ValueError) as vctx:
            NativeGnmiServer(
                config=NativeGnmiServerConfig(
                    bind_address="0.0.0.0",
                    bind_port=_find_free_port(),
                    allow_non_loopback=False,
                )
            )
        self.assertIn("NON_LOOPBACK_BIND_REJECTED", str(vctx.exception))

        # 3. Slow consumer queue overflow -> RESOURCE_EXHAUSTED
        sc_port = _find_free_port()
        sc_srv = NativeGnmiServer(
            config=NativeGnmiServerConfig(
                bind_address="127.0.0.1",
                bind_port=sc_port,
                max_queue_size_per_stream=3,
            ),
            state_store=self.state_store,
        )
        sc_srv.start()
        try:
            with grpc.insecure_channel(sc_srv.endpoint) as ch:
                stub = gnmi_pb2_grpc.gNMIStub(ch)
                # Initial snapshot has >3 wildcard notifications + sync_response, overflowing max_queue_size_per_stream=3
                req = gnmi_pb2.SubscribeRequest(
                    subscribe=gnmi_pb2.SubscriptionList(
                        prefix=_proto_path("", target="node-cisco8k"),
                        mode=gnmi_pb2.SubscriptionList.STREAM,
                        encoding=gnmi_pb2.JSON_IETF,
                        subscription=[
                            gnmi_pb2.Subscription(path=_proto_path("/interfaces/interface[name=*]/state")),
                            gnmi_pb2.Subscription(path=_proto_path("/components/component[name=*]/state")),
                        ],
                    )
                )
                with self.assertRaises(grpc.RpcError) as sctx:
                    list(stub.Subscribe(iter([req])))
                self.assertEqual(sctx.exception.code(), grpc.StatusCode.RESOURCE_EXHAUSTED)
                self.assertGreaterEqual(sc_srv.diagnostics.snapshot()["slow_consumer_drops"], 1)
        finally:
            sc_srv.stop(grace=0.1)


if __name__ == "__main__":
    unittest.main()
