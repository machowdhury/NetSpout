"""
NetSpout Gate 13C — External gNMI Collector & Telemetry Pipeline Integration Tests.

Verifies:
  - T13C-01: Telemetry provenance registry audit (zero fabricated vendor paths)
  - T13C-02: External collector (`gnmic`) Subscribe ONCE across all 4 vendors (OpenConfig + Vendor-Native)
  - T13C-03: External collector (`gnmic`) Subscribe STREAM / SAMPLE periodic counter collection
  - T13C-04: External collector (`gnmic`) Subscribe STREAM / ON_CHANGE phase transition collection
  - T13C-05: External collector (`gnmic`) Subscribe POLL across phases
  - T13C-06: Normalization datatype preservation (int, float, bool, str, object) & path/key preservation
  - T13C-07: Out-of-band correlation enrichment & native wire payload purity
  - T13C-08: Cross-transport state coherence (gNMI <-> SNMP <-> Syslog <-> NetFlow/IPFIX)
  - T13C-09: Multi-vendor heterogeneous telemetry coherence across scenarios
  - T13C-10: Collector reconnection & deterministic duplicate accounting
  - T13C-11: Controlled failures A (Collector unavailable) & B (gNMI server unavailable)
  - T13C-12: Controlled failures C (Authentication failure) & D (TLS validation failure)
  - T13C-13: Controlled failures E (Unsupported path), G (Unsupported encoding), H (Excessive sampling)
  - T13C-14: Collector performance & simultaneous multi-vendor subscriptions
"""

import os
import socket
import sys
import tempfile
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for rel in ("src", "backend", ""):
    p = os.path.join(REPO_ROOT, rel) if rel else REPO_ROOT
    if p not in sys.path:
        sys.path.insert(0, p)

from netspout_core.gnmi import (
    ExternalGnmiCollector,
    GnmiCollectorPipelineLedger,
    NativeGnmiServer,
    NativeGnmiServerConfig,
    ScenarioStateStore,
    audit_sensor_provenance_registry,
    generate_ephemeral_tls_material,
    run_collector_performance_benchmark,
    run_reconnect_and_duplication_experiment,
    verify_cross_transport_coherence_via_collector,
    verify_wire_payload_purity,
)


def _find_unused_tcp_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


class TestGate13CGnmiCollectorPipeline(unittest.TestCase):
    """Gate 13C verification test suite for the external gNMI collector pipeline."""

    def setUp(self) -> None:
        self.state_store = ScenarioStateStore(
            run_id="NS-GATE13C-TEST",
            scenario_id="openconfig_mdt_streaming",
            seed=42,
            initial_phase="BASELINE",
        )
        self.server_config = NativeGnmiServerConfig(
            bind_address="127.0.0.1",
            bind_port=0,
            security_mode="INSECURE_LOCAL_LAB",
            require_metadata_auth=False,
        )
        self.server = NativeGnmiServer(self.server_config, state_store=self.state_store)
        self.port = self.server.start()
        self.collector = ExternalGnmiCollector(host="127.0.0.1", port=self.port)

    def tearDown(self) -> None:
        if self.server is not None:
            self.server.stop()

    def test_t13c_01_provenance_registry_zero_fabricated_paths(self) -> None:
        """T13C-01: Every canonical sensor traces to a legitimate provenance reference; zero fabricated paths."""
        audit = audit_sensor_provenance_registry()
        self.assertTrue(audit["all_verified"])
        self.assertEqual(audit["fabricated_vendor_paths_found"], 0)
        self.assertGreaterEqual(audit["provenance_verified_count"], 34)

    def test_t13c_02_external_collector_subscribe_once_all_vendors_openconfig_and_native(self) -> None:
        """T13C-02: External gnmic collects OpenConfig and vendor-native telemetry across all 4 vendors in ONCE mode."""
        vendor_matrix = [
            (
                "node-cisco8k",
                "CISCO_IOS_XR",
                [
                    "/interfaces/interface[name=HundredGigE0/0/0/0]/state",
                    "/network-instances/network-instance[name=default]/protocols/protocol[identifier=BGP][name=BGP]/bgp/neighbors/neighbor[neighbor-address=10.100.1.2]/state",
                    "/qos/interfaces/interface[interface-id=HundredGigE0/0/0/0]/output/queues/queue[name=BE-0]/state",
                    "/components/component[name=Chassis-0]/state",
                    "/components/component[name=Transceiver-HundredGigE0/0/0/0]/transceiver/state",
                    "/system/state",
                    "/system/cpus/cpu[index=0]/state",
                    "/system/memory/state",
                ],
                [
                    "Cisco-IOS-XR-infra-statsd-oper:/infra-statistics/interfaces/interface[interface-name=HundredGigE0/0/0/0]/latest/generic-counters",
                    "Cisco-IOS-XR-pfi-im-cmd-oper:/interfaces/interface-xr/interface[interface-name=HundredGigE0/0/0/0]",
                    "Cisco-IOS-XR-ipv4-bgp-oper:/bgp/instances/instance[instance-name=default]/instance-active/default-vrf/neighbors/neighbor[neighbor-address=10.100.1.2]",
                    "Cisco-IOS-XR-qos-ma-oper:/qos/interface-table/interface[interface-name=HundredGigE0/0/0/0]/output/service-policy-names/service-policy-instance/statistics",
                    "Cisco-IOS-XR-controller-optics-oper:/optics-oper/optics-ports/optics-port[name=HundredGigE0/0/0/0]/optics-info",
                    "Cisco-IOS-XR-wdsysmon-fd-oper:/system-monitoring/cpu-utilization[node-name=0/RP0/CPU0]",
                ],
            ),
            (
                "node-cat-leaf",
                "CISCO_IOS_XE",
                [
                    "/interfaces/interface[name=FortyGigE1/0/1]/state",
                    "/network-instances/network-instance[name=default]/protocols/protocol[identifier=BGP][name=BGP]/bgp/neighbors/neighbor[neighbor-address=10.100.2.1]/state",
                    "/qos/interfaces/interface[interface-id=FortyGigE1/0/1]/output/queues/queue[name=BE-0]/state",
                    "/components/component[name=Chassis-0]/state",
                    "/system/state",
                    "/system/cpus/cpu[index=0]/state",
                    "/system/memory/state",
                ],
                [
                    "Cisco-IOS-XE-interfaces-oper:/interfaces/interface[name=FortyGigE1/0/1]/statistics",
                    "Cisco-IOS-XE-bgp-oper:/bgp-state-data/neighbors/neighbor[neighbor-id=10.100.2.1]",
                    "Cisco-IOS-XE-environment-oper:/environment-sensors/environment-sensor[name=Chassis-0]",
                    "Cisco-IOS-XE-transceiver-oper:/transceiver-oper-data/transceiver[name=FortyGigE1/0/1]",
                    "Cisco-IOS-XE-process-cpu-oper:/cpu-usage/cpu-utilization",
                ],
            ),
            (
                "node-arista-spine",
                "ARISTA_EOS",
                [
                    "/interfaces/interface[name=Ethernet1/1]/state",
                    "/network-instances/network-instance[name=default]/protocols/protocol[identifier=BGP][name=BGP]/bgp/neighbors/neighbor[neighbor-address=10.100.1.2]/state",
                    "/network-instances/network-instance[name=default]/evpn/state",
                    "/qos/interfaces/interface[interface-id=Ethernet1/1]/output/queues/queue[name=BE-0]/state",
                    "/components/component[name=Chassis-0]/state",
                    "/system/state",
                    "/system/cpus/cpu[index=0]/state",
                    "/system/memory/state",
                ],
                [
                    "eos_native:/Sysdb/interface/counter/eth/slice/phy/intf[intf=Ethernet1/1]/currentStatistics",
                    "eos_native:/Sysdb/hardware/counter/Lanz/intf[intf=Ethernet1/1]/queueStatus",
                    "eos_native:/Smash/routing/bgp/bgpPeerInfoStatus/vrf[vrf=default]/bgpPeerStatusEntry[peerAddr=10.100.1.2]",
                    "eos_native:/Smash/vxlan/vtepStatus",
                ],
            ),
            (
                "node-juniper-ptx",
                "JUNIPER_JUNOS",
                [
                    "/interfaces/interface[name=et-0/0/0]/state",
                    "/network-instances/network-instance[name=default]/protocols/protocol[identifier=BGP][name=BGP]/bgp/neighbors/neighbor[neighbor-address=10.100.1.1]/state",
                    "/qos/interfaces/interface[interface-id=et-0/0/0]/output/queues/queue[name=BE-0]/state",
                    "/components/component[name=Chassis-0]/state",
                    "/components/component[name=Transceiver-et-0/0/0]/transceiver/state",
                    "/system/state",
                    "/system/cpus/cpu[index=0]/state",
                    "/system/memory/state",
                ],
                [
                    "junos:/junos/system/linecard/interface[name=et-0/0/0]/statistics",
                    "junos:/junos/system/linecard/optics[name=et-0/0/0]",
                    "junos:/junos/system/linecard/qmon[interface=et-0/0/0]",
                    "junos:/junos/services/bgp/neighbors/neighbor[neighbor-address=10.100.1.1]",
                ],
            ),
        ]

        for target, expected_platform, oc_paths, native_paths in vendor_matrix:
            res_oc = self.collector.collect_once(target=target, paths=oc_paths)
            self.assertEqual(res_oc.returncode, 0)
            self.assertTrue(res_oc.sync_response_observed)
            self.assertEqual(res_oc.ledger.highest_verified_stage, "NORMALIZED")
            self.assertFalse(res_oc.ledger.splunk_dispatched)
            self.assertFalse(res_oc.ledger.splunk_observed)
            self.assertTrue(all(r.platform == expected_platform for r in res_oc.normalized_records))
            self.assertTrue(all(r.telemetry_model == "OPENCONFIG" for r in res_oc.normalized_records))

            for np in native_paths:
                res_nat = self.collector.collect_once(target=target, paths=[np])
                self.assertEqual(res_nat.returncode, 0, f"Failed native path {np} on {target}: {res_nat.stderr}")
                self.assertTrue(res_nat.sync_response_observed)
                self.assertEqual(res_nat.ledger.highest_verified_stage, "NORMALIZED")
                self.assertTrue(all(r.telemetry_model == "VENDOR_NATIVE" for r in res_nat.normalized_records))

    def test_t13c_03_external_collector_subscribe_stream_sample(self) -> None:
        """T13C-03: External gnmic receives periodic STREAM / SAMPLE updates at 500ms interval."""
        res = self.collector.collect_stream_sample(
            target="node-cisco8k",
            paths=["/interfaces/interface[name=HundredGigE0/0/0/0]/state/counters"],
            state_store=self.state_store,
            sample_interval="500ms",
            sample_ticks=2,
            tick_sleep_sec=0.55,
        )
        self.assertTrue(res.sync_response_observed)
        self.assertEqual(res.ledger.highest_verified_stage, "NORMALIZED")
        in_octets_series = [
            r.value
            for r in res.normalized_records
            if r.gnmi_path == "/interfaces/interface[name=HundredGigE0/0/0/0]/state/counters/in-octets"
        ]
        self.assertGreaterEqual(len(in_octets_series), 2)
        self.assertGreater(in_octets_series[-1], in_octets_series[0])

    def test_t13c_04_external_collector_subscribe_stream_on_change(self) -> None:
        """T13C-04: External gnmic receives STREAM / ON_CHANGE updates across phase transitions."""
        res = self.collector.collect_stream_on_change(
            target="node-cisco8k",
            paths=[
                "/interfaces/interface[name=HundredGigE0/0/0/0]/state/oper-status",
                "/network-instances/network-instance[name=default]/protocols/protocol[identifier=BGP][name=BGP]/bgp/neighbors/neighbor[neighbor-address=10.100.1.2]/state/session-state",
            ],
            state_store=self.state_store,
            phase_sequence=("DEGRADE", "RECOVERY"),
        )
        self.assertTrue(res.sync_response_observed)
        oper_vals = [
            (r.phase, r.value)
            for r in res.normalized_records
            if r.gnmi_path.endswith("/oper-status")
        ]
        self.assertEqual(oper_vals[0][1], "UP")
        self.assertIn(("DEGRADE", "DOWN"), oper_vals)
        self.assertIn(("RECOVERY", "UP"), oper_vals)

    def test_t13c_05_external_collector_subscribe_poll_across_phases(self) -> None:
        """T13C-05: External gnmic interactive POLL subscription receives fresh snapshots across phases."""
        res = self.collector.collect_poll_across_phases(
            target="node-cisco8k",
            paths=["/interfaces/interface[name=HundredGigE0/0/0/0]/state/oper-status"],
            state_store=self.state_store,
            poll_phases=("FAILOVER", "RECOVERY"),
        )
        self.assertTrue(res.sync_response_observed)
        self.assertGreaterEqual(res.sync_response_count, 2)
        vals = [r.value for r in res.normalized_records if r.gnmi_path.endswith("/oper-status")]
        self.assertIn("UP", vals)
        self.assertIn("DOWN", vals)

    def test_t13c_06_normalization_datatype_and_path_preservation(self) -> None:
        """T13C-06: Normalizer preserves full keyed gNMI paths and native int, float, bool, str, and object types."""
        res = self.collector.collect_once(
            target="node-cisco8k",
            paths=[
                "/interfaces/interface[name=HundredGigE0/0/0/0]/state",
                "/lacp/interfaces/interface[name=Bundle-Ether10]/members/member[interface=HundredGigE0/0/0/0]/state",
                "/components/component[name=Chassis-0]/state",
            ],
            include_leaf_records=True,
        )
        by_path = {r.gnmi_path: r for r in res.normalized_records}

        # 1. Container object type preserved with full keyed path
        if_state_rec = by_path["/interfaces/interface[name=HundredGigE0/0/0/0]/state"]
        self.assertEqual(if_state_rec.value_type, "object")
        self.assertIsInstance(if_state_rec.value, dict)

        # 2. Integer leaf restored from RFC 7951 stringified uint64
        in_oct_rec = by_path["/interfaces/interface[name=HundredGigE0/0/0/0]/state/counters/in-octets"]
        self.assertEqual(in_oct_rec.value_type, "int")
        self.assertIsInstance(in_oct_rec.value, int)
        self.assertEqual(in_oct_rec.value, 98504200000)

        # 3. Float leaf preserved
        temp_rec = by_path["/components/component[name=Chassis-0]/state/temperature/instant"]
        self.assertEqual(temp_rec.value_type, "float")
        self.assertIsInstance(temp_rec.value, float)
        self.assertAlmostEqual(temp_rec.value, 41.2, places=2)

        # 4. Boolean leaf preserved
        lacp_col_rec = by_path[
            "/lacp/interfaces/interface[name=Bundle-Ether10]/members/member[interface=HundredGigE0/0/0/0]/state/collecting"
        ]
        self.assertEqual(lacp_col_rec.value_type, "bool")
        self.assertIs(lacp_col_rec.value, True)

        # 5. String leaf preserved
        oper_rec = by_path["/interfaces/interface[name=HundredGigE0/0/0/0]/state/oper-status"]
        self.assertEqual(oper_rec.value_type, "str")
        self.assertEqual(oper_rec.value, "UP")

    def test_t13c_07_correlation_enrichment_and_wire_payload_purity(self) -> None:
        """T13C-07: Wire gNMI notifications contain zero netspout_* fields; correlation attaches at normalizer boundary."""
        res = self.collector.collect_once(
            target="node-cisco8k",
            paths=["/interfaces/interface[name=HundredGigE0/0/0/0]/state"],
            run_id="NS-RUN-CORR-01",
            scenario_id="openconfig_mdt_streaming",
            phase="DEGRADE",
        )
        purity = verify_wire_payload_purity(res.raw_notifications)
        self.assertTrue(purity["wire_payload_pure"])
        self.assertEqual(len(purity["violations"]), 0)

        for rec in res.normalized_records:
            self.assertEqual(rec.netspout_run_id, "NS-RUN-CORR-01")
            self.assertEqual(rec.netspout_scenario_id, "openconfig_mdt_streaming")
            self.assertEqual(rec.netspout_phase, "DEGRADE")
            self.assertEqual(rec.netspout_device_id, "node-cisco8k")
            self.assertTrue(len(rec.netspout_event_id) > 10)

    def test_t13c_08_cross_transport_state_coherence(self) -> None:
        """T13C-08: Shared ScenarioStateStore drives coherent gNMI, SNMP, Syslog, and NetFlow observations."""
        proof = verify_cross_transport_coherence_via_collector(
            port=self.port,
            state_store=self.state_store,
            target="cisco-asr9k-pe1",
        )
        self.assertTrue(proof["all_phases_coherent"])
        self.assertEqual(proof["phases"]["DEGRADE"]["interface_coherence"]["gnmi_oper_status"], "DOWN")
        self.assertEqual(proof["phases"]["DEGRADE"]["interface_coherence"]["snmp_ifOperStatus_1"], 2)
        self.assertEqual(proof["phases"]["DEGRADE"]["routing_bgp_coherence"]["gnmi_bgp_session_state"], "IDLE")
        self.assertEqual(proof["phases"]["DEGRADE"]["routing_bgp_coherence"]["snmp_bgpPeerState"], 1)

    def test_t13c_09_multi_vendor_coherence_heterogeneous_telemetry(self) -> None:
        """T13C-09: Same modeled DEGRADE incident observed across all 4 vendors via OpenConfig and Vendor-Native models."""
        self.state_store.set_phase("DEGRADE", advance_tick=False)
        self.state_store._tick = 0

        # Query queue tail-drops across all 4 vendors (OpenConfig + Vendor-Native where supported)
        xr_nat = self.collector.collect_once(
            target="node-cisco8k",
            paths=[
                "Cisco-IOS-XR-qos-ma-oper:/qos/interface-table/interface[interface-name=HundredGigE0/0/0/0]/output/service-policy-names/service-policy-instance/statistics"
            ],
            phase="DEGRADE",
        )
        eos_nat = self.collector.collect_once(
            target="node-arista-spine",
            paths=["eos_native:/Sysdb/hardware/counter/Lanz/intf[intf=Ethernet1/1]/queueStatus"],
            phase="DEGRADE",
        )
        junos_nat = self.collector.collect_once(
            target="node-juniper-ptx",
            paths=["junos:/junos/system/linecard/qmon[interface=et-0/0/0]"],
            phase="DEGRADE",
        )
        xe_oc = self.collector.collect_once(
            target="node-cat-leaf",
            paths=["/qos/interfaces/interface[interface-id=FortyGigE1/0/1]/output/queues/queue[name=BE-0]/state"],
            phase="DEGRADE",
        )

        xr_by_path = {r.gnmi_path: r.value for r in xr_nat.normalized_records}
        eos_by_path = {r.gnmi_path: r.value for r in eos_nat.normalized_records}
        junos_by_path = {r.gnmi_path: r.value for r in junos_nat.normalized_records}
        xe_by_path = {r.gnmi_path: r.value for r in xe_oc.normalized_records}

        # All 4 reflect the exact same 4820 dropped packets and 14,850,000 byte queue depth in their native schemas
        self.assertEqual(
            xr_by_path[
                "/qos/interface-table/interface[interface-name=HundredGigE0/0/0/0]/output/service-policy-names/service-policy-instance/statistics/tail-drop-packets"
            ],
            4820,
        )
        self.assertEqual(
            eos_by_path["/Sysdb/hardware/counter/Lanz[intf=Ethernet1/1]/queueStatus/outDiscards"],
            4820,
        )
        self.assertEqual(
            junos_by_path["/junos/system/linecard/qmon[interface=et-0/0/0]/tail-drop-packets"],
            4820,
        )
        self.assertEqual(
            xe_by_path[
                "/qos/interfaces/interface[interface-id=FortyGigE1/0/1]/output/queues/queue[name=BE-0]/state/dropped-pkts"
            ],
            4820,
        )

    def test_t13c_10_reconnect_and_duplication_semantics(self) -> None:
        """T13C-10: External collector reconnects after server restart and accurately accounts for duplicate initial sync."""
        report, new_srv = run_reconnect_and_duplication_experiment(
            port=self.port,
            state_store=self.state_store,
            server_instance=self.server,
            target="node-cisco8k",
        )
        self.server = new_srv
        self.assertTrue(report["reconnect_succeeded"])
        self.assertGreaterEqual(report["unfiltered_accounting"]["duplicate_count"], 1)
        self.assertEqual(
            report["deduplicated_accounting"]["suppressed_count"],
            report["unfiltered_accounting"]["duplicate_count"],
        )

    def test_t13c_11_controlled_failures_collector_and_server_unavailable(self) -> None:
        """T13C-11: Controlled failures A (Collector unavailable) and B (Server unavailable) never fabricate evidence."""
        # A. Collector unavailable (missing binary)
        missing_collector = ExternalGnmiCollector(
            host="127.0.0.1",
            port=self.port,
            gnmic_bin="/nonexistent/bin/gnmic_missing",
        )
        res_a = missing_collector.collect_once(
            target="node-cisco8k",
            paths=["/system/state"],
        )
        self.assertFalse(res_a.ledger.collector_received)
        self.assertFalse(res_a.ledger.normalized)
        self.assertEqual(len(res_a.normalized_records), 0)

        # B. gNMI server unavailable (closed port)
        closed_port = _find_unused_tcp_port()
        dead_server_collector = ExternalGnmiCollector(
            host="127.0.0.1",
            port=closed_port,
        )
        res_b = dead_server_collector.collect_once(
            target="node-cisco8k",
            paths=["/system/state"],
        )
        self.assertNotEqual(res_b.returncode, 0)
        self.assertFalse(res_b.ledger.collector_received)
        self.assertEqual(len(res_b.normalized_records), 0)

    def test_t13c_12_controlled_failures_auth_and_tls(self) -> None:
        """T13C-12: Controlled failures C (Authentication failure) and D (TLS validation failure)."""
        # C. Authentication failure
        auth_srv = NativeGnmiServer(
            NativeGnmiServerConfig(
                bind_address="127.0.0.1",
                bind_port=0,
                require_metadata_auth=True,
                username="netspout-lab",
                password="correct-password",
            ),
            state_store=self.state_store,
        )
        auth_port = auth_srv.start()
        try:
            bad_auth_collector = ExternalGnmiCollector(
                host="127.0.0.1",
                port=auth_port,
                username="netspout-lab",
                password="wrong-password",
            )
            res_c = bad_auth_collector.collect_once(target="node-cisco8k", paths=["/system/state"])
            self.assertNotEqual(res_c.returncode, 0)
            self.assertFalse(res_c.ledger.collector_received)
            self.assertIn("UNAUTHENTICATED", res_c.stderr.upper() + res_c.stdout.upper())
        finally:
            auth_srv.stop()

        # D. TLS validation failure (untrusted server cert without --tls-ca and without --skip-verify)
        tls_mat = generate_ephemeral_tls_material()
        tls_srv = NativeGnmiServer(
            NativeGnmiServerConfig(
                bind_address="127.0.0.1",
                bind_port=0,
                security_mode="TLS_SERVER_AUTH",
                tls_ca_cert_pem=tls_mat.ca_cert_pem,
                tls_server_cert_pem=tls_mat.server_cert_pem,
                tls_server_key_pem=tls_mat.server_key_pem,
            ),
            state_store=self.state_store,
        )
        tls_port = tls_srv.start()
        try:
            untrusted_tls_collector = ExternalGnmiCollector(
                host="127.0.0.1",
                port=tls_port,
                insecure=False,
                skip_verify=False,
            )
            res_d_fail = untrusted_tls_collector.collect_once(target="node-cisco8k", paths=["/system/state"])
            self.assertNotEqual(res_d_fail.returncode, 0)
            self.assertFalse(res_d_fail.ledger.collector_received)

            # Verify valid TLS with ephemeral CA succeeds
            with tempfile.NamedTemporaryFile("wb", suffix=".pem", delete=True) as ca_file:
                ca_file.write(tls_mat.ca_cert_pem)
                ca_file.flush()
                trusted_tls_collector = ExternalGnmiCollector(
                    host="127.0.0.1",
                    port=tls_port,
                    insecure=False,
                    tls_ca_file=ca_file.name,
                )
                res_d_ok = trusted_tls_collector.collect_once(target="node-cisco8k", paths=["/system/state"])
                self.assertEqual(res_d_ok.returncode, 0)
                self.assertTrue(res_d_ok.ledger.collector_received)
        finally:
            tls_srv.stop()

    def test_t13c_13_controlled_failures_unsupported_path_encoding_and_guardrails(self) -> None:
        """T13C-13: Controlled failures E (Unsupported path), G (Unsupported encoding), H (Excessive sampling)."""
        # E. Unsupported path
        res_e = self.collector.collect_once(
            target="node-cisco8k",
            paths=["/openconfig-fabricated/nonexistent/state"],
        )
        self.assertNotEqual(res_e.returncode, 0)
        self.assertFalse(res_e.ledger.collector_received)
        self.assertEqual(len(res_e.normalized_records), 0)

        # G. Unsupported encoding (ASCII)
        res_g = self.collector.collect_once(
            target="node-cisco8k",
            paths=["/system/state"],
            encoding="ascii",
        )
        self.assertNotEqual(res_g.returncode, 0)
        self.assertFalse(res_g.ledger.collector_received)

        # H. Excessive sampling request (100ms < 500ms floor)
        res_h = self.collector.collect_stream_sample(
            target="node-cisco8k",
            paths=["/interfaces/interface[name=HundredGigE0/0/0/0]/state/counters"],
            state_store=self.state_store,
            sample_interval="100ms",
            sample_ticks=1,
            tick_sleep_sec=0.1,
        )
        self.assertFalse(res_h.ledger.collector_received)
        self.assertIn("SAMPLE_INTERVAL_BELOW_FLOOR", res_h.stderr)

    def test_t13c_14_collector_performance_and_simultaneous_subscriptions(self) -> None:
        """T13C-14: Collector benchmark sustains 4 simultaneous multi-vendor subscriptions with sub-50ms p95 normalization."""
        perf = run_collector_performance_benchmark(
            port=self.port,
            state_store=self.state_store,
        )
        self.assertEqual(perf["simultaneous_subscriptions"], 4)
        self.assertGreater(perf["total_raw_updates"], 20)
        self.assertGreater(perf["total_normalized_records"], 100)
        self.assertLess(perf["p95_normalization_latency_ms"], 50.0)


if __name__ == "__main__":
    unittest.main()
