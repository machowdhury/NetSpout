"""
NetSpout Gate 12C Test Suite — Native SNMPv2c Polling Agent, GET/GETNEXT/GETBULK & OID Walk.
Covers all 40 mandatory Gate 12C test requirements:
  1..5:   OID numeric comparison, tree ordering, SNMPv2-MIB, IF-MIB, BGP4-MIB surface
  6..17:  GET, GETNEXT, GETBULK, endOfMibView, noSuchObject, noSuchInstance, MTU bounds
  18..23: Read-only SET rejection, malformed BER/request resilience, rate limits, loopback bind, clean shutdown
  24..29: Deterministic state, BASELINE->DEGRADE->FAILOVER->RECOVERY transitions, Trap/Inform/Poll state coherence
  30..34: Independent external verification via Net-SNMP CLI (`snmpget`, `snmpgetnext`, `snmpwalk`, `snmpbulkwalk`) & TShark
  35..40: Zero regression across Gate 12B Golden Fixtures, Trap, Inform, NetFlow v9, IPFIX, and 13 Golden Paths
"""

import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from netspout_core.catalog import catalog
from netspout_core.companion_manifest import CompanionManifestBuilder
from netspout_core.exporter_session import ExporterSession
from netspout_core.ipfix_encoder import IPFIXEncoder
from netspout_core.models import (
    FlowRecord,
    OidFidelityClass,
    SnmpEvidenceStage,
    SnmpMessage,
    SnmpOidEntry,
    SnmpPduType,
    SnmpVarBind,
    SnmpVersion,
)
from netspout_core.netflow_v9_encoder import NetFlowV9Encoder
from netspout_core.snmp_agent import (
    DEFAULT_AGENT_BIND_HOST,
    DEFAULT_AGENT_BIND_PORT,
    DEFAULT_AGENT_COMMUNITY,
    HARD_MAX_GETBULK_REPETITIONS,
    MAX_VARBINDS_PER_RESPONSE,
    SNMP_ERR_NOT_WRITABLE,
    SNMP_ERR_NO_ERROR,
    SimulatedSnmpAgent,
    SnmpOidStore,
    SnmpPollingClient,
    build_service_provider_cisco_oid_store,
    compare_oids,
    is_oid_in_subtree,
    oid_to_tuple,
    verify_trap_poll_coherence,
)
from netspout_core.snmp_ber import (
    GOLDEN_HEX_FIXTURES,
    MAX_SNMP_UDP_PAYLOAD_BYTES,
    SnmpBerDecoder,
    SnmpBerEncoder,
    verify_golden_fixtures,
)
from netspout_core.snmp_engine import snmp_engine
from netspout_core.transport_native_snmp import (
    LoopbackSnmpTestReceiver,
    NativeSnmpTransport,
)
from netspout_core.transport_safety import DestinationSecurityException


def _find_bin(name: str, fallback: str) -> str:
    found = shutil.which(name)
    if found:
        return found
    if os.path.exists(fallback):
        return fallback
    return ""


class TestGate12CSnmpPolling(unittest.TestCase):
    """Comprehensive 40-test verification suite for Gate 12C Native SNMPv2c Polling Agent."""

    def test_01_oid_numeric_comparison(self) -> None:
        """1. OID components must be compared numerically, never as strings."""
        self.assertEqual(
            compare_oids("1.3.6.1.2.1.2.2.1.10.2", "1.3.6.1.2.1.2.2.1.10.10"),
            -1,
        )
        self.assertEqual(
            compare_oids("1.3.6.1.2.1.2.2.1.10.10", "1.3.6.1.2.1.2.2.1.10.2"),
            1,
        )
        self.assertEqual(
            compare_oids(".1.3.6.1.2.1.1.1.0", "1.3.6.1.2.1.1.1.0"),
            0,
        )
        self.assertLess(
            oid_to_tuple("1.3.6.1.2.1.2.2.1.8.9"),
            oid_to_tuple("1.3.6.1.2.1.2.2.1.8.10"),
        )

    def test_02_oid_tree_ordering(self) -> None:
        """2. OID tree maintains strict numeric lexicographic order regardless of insertion order."""
        store = SnmpOidStore()
        unruly_oids = [
            "1.3.6.1.2.1.2.2.1.10.10",
            "1.3.6.1.2.1.2.2.1.10.2",
            "1.3.6.1.2.1.2.2.1.10.1",
            "1.3.6.1.2.1.15.3.1.2.198.51.100.2",
            "1.3.6.1.2.1.15.3.1.2.198.51.100.1",
            "1.3.6.1.2.1.1.1.0",
        ]
        for o in unruly_oids:
            store.register(
                SnmpOidEntry(
                    oid=o,
                    asn1_type="Integer32",
                    value=1,
                    source_mib="IF-MIB",
                )
            )
        ordered = store.all_oids()
        self.assertEqual(
            ordered,
            [
                "1.3.6.1.2.1.1.1.0",
                "1.3.6.1.2.1.2.2.1.10.1",
                "1.3.6.1.2.1.2.2.1.10.2",
                "1.3.6.1.2.1.2.2.1.10.10",
                "1.3.6.1.2.1.15.3.1.2.198.51.100.1",
                "1.3.6.1.2.1.15.3.1.2.198.51.100.2",
            ],
        )

    def test_03_snmpv2_mib_objects(self) -> None:
        """3. Verify mandatory SNMPv2-MIB system scalars (sysDescr..sysServices)."""
        store = build_service_provider_cisco_oid_store(phase="BASELINE", seed=42)
        expected = {
            "1.3.6.1.2.1.1.1.0": "OctetString",       # sysDescr.0
            "1.3.6.1.2.1.1.2.0": "ObjectIdentifier",  # sysObjectID.0
            "1.3.6.1.2.1.1.3.0": "TimeTicks",         # sysUpTime.0
            "1.3.6.1.2.1.1.4.0": "OctetString",       # sysContact.0
            "1.3.6.1.2.1.1.5.0": "OctetString",       # sysName.0
            "1.3.6.1.2.1.1.6.0": "OctetString",       # sysLocation.0
            "1.3.6.1.2.1.1.7.0": "Integer32",         # sysServices.0
        }
        for oid, asn1_type in expected.items():
            vb = store.get_exact(oid)
            self.assertEqual(vb.asn1_type, asn1_type)
            self.assertIsNotNone(vb.value)
            self.assertEqual(vb.fidelity, OidFidelityClass.STANDARD_VERIFIED.value)

    def test_04_if_mib_objects(self) -> None:
        """4. Verify mandatory IF-MIB scalars, 32-bit counters, and 64-bit ifXTable counters."""
        store = build_service_provider_cisco_oid_store(phase="BASELINE", seed=42)
        self.assertEqual(store.get_exact("1.3.6.1.2.1.2.1.0").value, 3)  # ifNumber.0
        required_cols = [
            ("1.3.6.1.2.1.2.2.1.1.1", "Integer32", 1),                     # ifIndex.1
            ("1.3.6.1.2.1.2.2.1.2.1", "OctetString", "HundredGigE0/0/0/1"), # ifDescr.1
            ("1.3.6.1.2.1.2.2.1.3.1", "Integer32", 6),                     # ifType.1
            ("1.3.6.1.2.1.2.2.1.4.1", "Integer32", 9192),                  # ifMtu.1
            ("1.3.6.1.2.1.2.2.1.5.1", "Gauge32", 4294967295),              # ifSpeed.1
            ("1.3.6.1.2.1.2.2.1.6.1", "OctetString", "00:1e:be:01:00:01"), # ifPhysAddress.1
            ("1.3.6.1.2.1.2.2.1.7.1", "Integer32", 1),                     # ifAdminStatus.1
            ("1.3.6.1.2.1.2.2.1.8.1", "Integer32", 1),                     # ifOperStatus.1
            ("1.3.6.1.2.1.2.2.1.10.1", "Counter32", None),                 # ifInOctets.1
            ("1.3.6.1.2.1.2.2.1.11.1", "Counter32", None),                 # ifInUcastPkts.1
            ("1.3.6.1.2.1.2.2.1.14.1", "Counter32", 0),                    # ifInErrors.1
            ("1.3.6.1.2.1.2.2.1.16.1", "Counter32", None),                 # ifOutOctets.1
            ("1.3.6.1.2.1.2.2.1.17.1", "Counter32", None),                 # ifOutUcastPkts.1
            ("1.3.6.1.2.1.2.2.1.20.1", "Counter32", 0),                    # ifOutErrors.1
            ("1.3.6.1.2.1.31.1.1.1.6.1", "Counter64", None),               # ifHCInOctets.1
            ("1.3.6.1.2.1.31.1.1.1.10.1", "Counter64", None),              # ifHCOutOctets.1
        ]
        for oid, expected_type, expected_val in required_cols:
            vb = store.get_exact(oid)
            self.assertEqual(vb.asn1_type, expected_type, f"Mismatch on {oid}")
            if expected_val is not None:
                self.assertEqual(vb.value, expected_val, f"Value mismatch on {oid}")

    def test_05_bgp4_mib_objects(self) -> None:
        """5. Verify BGP4-MIB peer state, peer address, remote AS, and local AS objects."""
        store = build_service_provider_cisco_oid_store(phase="BASELINE", seed=42)
        self.assertEqual(store.get_exact("1.3.6.1.2.1.15.2.0").value, 65001)  # bgpLocalAs.0
        self.assertEqual(store.get_exact("1.3.6.1.2.1.15.4.0").value, "10.254.0.1")  # bgpIdentifier.0
        self.assertEqual(store.get_exact("1.3.6.1.2.1.15.3.1.2.198.51.100.1").value, 6)  # established
        self.assertEqual(store.get_exact("1.3.6.1.2.1.15.3.1.7.198.51.100.1").value, "198.51.100.1")
        self.assertEqual(store.get_exact("1.3.6.1.2.1.15.3.1.9.198.51.100.1").value, 65002)
        self.assertEqual(store.get_exact("1.3.6.1.2.1.15.3.1.9.198.51.100.2").value, 65003)

    def test_06_get_exact_match(self) -> None:
        """6. GET exact match over live loopback UDP preserves request-id, community, version, and value."""
        with SimulatedSnmpAgent(bind_port=0, phase="BASELINE", seed=42) as agent:
            client = SnmpPollingClient(port=agent.bound_port)
            resp = client.get("1.3.6.1.2.1.2.2.1.8.1", request_id=7001, agent=agent)
            self.assertEqual(resp.pdu_type, SnmpPduType.RESPONSE.value)
            self.assertEqual(resp.version, SnmpVersion.V2C.value)
            self.assertEqual(resp.community, DEFAULT_AGENT_COMMUNITY)
            self.assertEqual(resp.request_id, 7001)
            self.assertEqual(resp.error_status, 0)
            self.assertEqual(resp.error_index, 0)
            self.assertEqual(len(resp.varbinds), 1)
            self.assertEqual(resp.varbinds[0].oid, "1.3.6.1.2.1.2.2.1.8.1")
            self.assertEqual(resp.varbinds[0].asn1_type, "Integer32")
            self.assertEqual(resp.varbinds[0].value, 1)

    def test_07_get_unknown_oid(self) -> None:
        """7. GET unknown OID returns Response-PDU with error-status=0 and SNMPv2c exception varbind."""
        with SimulatedSnmpAgent(bind_port=0, phase="BASELINE", seed=42) as agent:
            client = SnmpPollingClient(port=agent.bound_port)
            resp = client.get("1.3.6.1.2.1.999.1.0", request_id=7002, agent=agent)
            self.assertEqual(resp.error_status, 0)
            self.assertEqual(resp.varbinds[0].oid, "1.3.6.1.2.1.999.1.0")
            self.assertEqual(resp.varbinds[0].asn1_type, "noSuchObject")

    def test_08_multi_varbind_get(self) -> None:
        """8. Multi-varbind GET preserves exact varbind ordering across existing and missing OIDs."""
        with SimulatedSnmpAgent(bind_port=0, phase="DEGRADE", seed=42) as agent:
            client = SnmpPollingClient(port=agent.bound_port)
            oids = [
                "1.3.6.1.2.1.1.3.0",
                "1.3.6.1.2.1.2.2.1.8.1",
                "1.3.6.1.2.1.15.3.1.2.198.51.100.1",
                "1.3.6.1.2.1.2.2.1.8.99",
            ]
            resp = client.get(oids, request_id=7003, agent=agent)
            self.assertEqual([vb.oid for vb in resp.varbinds], oids)
            self.assertEqual(resp.varbinds[0].value, 8640000)
            self.assertEqual(resp.varbinds[1].value, 2)  # down in DEGRADE
            self.assertEqual(resp.varbinds[2].value, 1)  # idle in DEGRADE
            self.assertEqual(resp.varbinds[3].asn1_type, "noSuchInstance")

    def test_09_getnext_exact(self) -> None:
        """9. GETNEXT on an existing OID returns the strictly greater lexicographic successor."""
        with SimulatedSnmpAgent(bind_port=0, phase="BASELINE", seed=42) as agent:
            client = SnmpPollingClient(port=agent.bound_port)
            resp = client.get_next("1.3.6.1.2.1.1.1.0", agent=agent)
            self.assertEqual(resp.varbinds[0].oid, "1.3.6.1.2.1.1.2.0")
            self.assertEqual(resp.varbinds[0].value, "1.3.6.1.4.1.9.1.1639")

    def test_10_getnext_between_objects(self) -> None:
        """10. GETNEXT before tree or between existing OIDs finds the next numeric OID."""
        with SimulatedSnmpAgent(bind_port=0, phase="BASELINE", seed=42) as agent:
            client = SnmpPollingClient(port=agent.bound_port)
            # Before tree (1.3) -> first object in store (1.3.6.1.2.1.1.1.0)
            resp_before = client.get_next("1.3", agent=agent)
            self.assertEqual(resp_before.varbinds[0].oid, "1.3.6.1.2.1.1.1.0")
            # Between 1.3.6.1.2.1.1.7.0 and 1.3.6.1.2.1.2.1.0
            resp_between = client.get_next("1.3.6.1.2.1.1.99.0", agent=agent)
            self.assertEqual(resp_between.varbinds[0].oid, "1.3.6.1.2.1.2.1.0")

    def test_11_getnext_end_of_tree(self) -> None:
        """11. GETNEXT at or beyond the final OID returns endOfMibView (0x82) and never wraps around."""
        with SimulatedSnmpAgent(bind_port=0, phase="BASELINE", seed=42) as agent:
            client = SnmpPollingClient(port=agent.bound_port)
            last_oid = agent.oid_store.all_oids()[-1]
            resp_last = client.get_next(last_oid, agent=agent)
            self.assertEqual(resp_last.varbinds[0].oid, last_oid)
            self.assertEqual(resp_last.varbinds[0].asn1_type, "endOfMibView")

            resp_beyond = client.get_next("1.3.6.1.99.1.0", agent=agent)
            self.assertEqual(resp_beyond.varbinds[0].oid, "1.3.6.1.99.1.0")
            self.assertEqual(resp_beyond.varbinds[0].asn1_type, "endOfMibView")

    def test_12_getbulk_non_repeaters(self) -> None:
        """12. GETBULK correctly handles non-repeaters (1 successor each) + repeaters (M successors)."""
        with SimulatedSnmpAgent(bind_port=0, phase="BASELINE", seed=42) as agent:
            client = SnmpPollingClient(port=agent.bound_port)
            resp = client.get_bulk(
                ["1.3.6.1.2.1.1.2.0", "1.3.6.1.2.1.2.2.1.8"],
                non_repeaters=1,
                max_repetitions=3,
                agent=agent,
            )
            # 1 non-repeater (sysUpTime.0) + 3 repetitions of ifOperStatus.{1,2,3} = 4 varbinds
            self.assertEqual(len(resp.varbinds), 4)
            self.assertEqual(resp.varbinds[0].oid, "1.3.6.1.2.1.1.3.0")
            self.assertEqual(resp.varbinds[1].oid, "1.3.6.1.2.1.2.2.1.8.1")
            self.assertEqual(resp.varbinds[2].oid, "1.3.6.1.2.1.2.2.1.8.2")
            self.assertEqual(resp.varbinds[3].oid, "1.3.6.1.2.1.2.2.1.8.3")

    def test_13_getbulk_max_repetitions(self) -> None:
        """13. GETBULK returns exact requested repetitions in numeric OID order."""
        with SimulatedSnmpAgent(bind_port=0, phase="BASELINE", seed=42) as agent:
            client = SnmpPollingClient(port=agent.bound_port)
            resp = client.get_bulk(
                "1.3.6.1.2.1.1",
                non_repeaters=0,
                max_repetitions=7,
                agent=agent,
            )
            self.assertEqual(len(resp.varbinds), 7)
            self.assertEqual(
                [vb.oid for vb in resp.varbinds],
                [f"1.3.6.1.2.1.1.{i}.0" for i in range(1, 8)],
            )

    def test_14_getbulk_response_bound(self) -> None:
        """14. GETBULK clamps max-repetitions <= 50 and max varbinds <= 100."""
        with SimulatedSnmpAgent(bind_port=0, phase="BASELINE", seed=42) as agent:
            client = SnmpPollingClient(port=agent.bound_port)
            resp = client.get_bulk(
                "1.3.6.1.2.1.1",
                non_repeaters=0,
                max_repetitions=500,
                agent=agent,
            )
            self.assertLessEqual(len(resp.varbinds), HARD_MAX_GETBULK_REPETITIONS)
            self.assertLessEqual(len(resp.varbinds), MAX_VARBINDS_PER_RESPONSE)
            wire = SnmpBerEncoder.encode_message(resp)
            self.assertLessEqual(len(wire), MAX_SNMP_UDP_PAYLOAD_BYTES)

    def test_15_getbulk_oversized_request(self) -> None:
        """15. GETBULK with multiple repeaters and excessive max-repetitions stays <= 1,472 bytes without crashing."""
        with SimulatedSnmpAgent(bind_port=0, phase="BASELINE", seed=42) as agent:
            client = SnmpPollingClient(port=agent.bound_port)
            resp = client.get_bulk(
                [
                    "1.3.6.1.2.1.1",
                    "1.3.6.1.2.1.2.2.1.2",
                    "1.3.6.1.2.1.31.1.1.1.18",
                    "1.3.6.1.2.1.15.3.1",
                ],
                non_repeaters=0,
                max_repetitions=65535,
                agent=agent,
            )
            wire = SnmpBerEncoder.encode_message(resp)
            self.assertLessEqual(len(wire), MAX_SNMP_UDP_PAYLOAD_BYTES)
            self.assertGreater(len(resp.varbinds), 0)

    def test_16_end_of_mib_view_behavior(self) -> None:
        """16. GETBULK at the tail of the MIB tree terminates with endOfMibView (0x82) without repeating infinitely."""
        with SimulatedSnmpAgent(bind_port=0, phase="BASELINE", seed=42) as agent:
            client = SnmpPollingClient(port=agent.bound_port)
            all_oids = agent.oid_store.all_oids()
            second_last = all_oids[-2]
            resp = client.get_bulk(second_last, non_repeaters=0, max_repetitions=10, agent=agent)
            # Should return the final OID and then a single endOfMibView
            self.assertEqual(len(resp.varbinds), 2)
            self.assertEqual(resp.varbinds[0].oid, all_oids[-1])
            self.assertEqual(resp.varbinds[1].asn1_type, "endOfMibView")

    def test_17_no_such_object_and_no_such_instance_behavior(self) -> None:
        """17. Distinguish RFC 3416 noSuchObject (0x80) vs noSuchInstance (0x81) on GET."""
        store = build_service_provider_cisco_oid_store(phase="BASELINE", seed=42)
        # Missing instance under implemented column ifOperStatus (1.3.6.1.2.1.2.2.1.8)
        vb_inst = store.get_exact("1.3.6.1.2.1.2.2.1.8.99")
        self.assertEqual(vb_inst.asn1_type, "noSuchInstance")
        self.assertEqual(vb_inst.tag, 0x81)
        # Unimplemented MIB subtree
        vb_obj = store.get_exact("1.3.6.1.2.1.200.1.1.0")
        self.assertEqual(vb_obj.asn1_type, "noSuchObject")
        self.assertEqual(vb_obj.tag, 0x80)

    def test_18_read_only_set_rejection(self) -> None:
        """18. SET requests (0xA3) are rejected with error-status=notWritable (17) and zero state mutation."""
        with SimulatedSnmpAgent(bind_port=0, phase="BASELINE", seed=42) as agent:
            client = SnmpPollingClient(port=agent.bound_port)
            set_msg = SnmpMessage(
                version=SnmpVersion.V2C.value,
                community=DEFAULT_AGENT_COMMUNITY,
                pdu_type=SnmpPduType.SET_REQUEST.value,
                request_id=8001,
                varbinds=[
                    SnmpVarBind(
                        oid="1.3.6.1.2.1.1.5.0",
                        asn1_type="OctetString",
                        value="hacked-router",
                    )
                ],
            )
            resp = client.send_message(set_msg, agent=agent)
            self.assertEqual(resp.error_status, SNMP_ERR_NOT_WRITABLE)
            self.assertEqual(resp.error_index, 1)
            self.assertEqual(agent.set_requests_rejected, 1)
            # Confirm state was not mutated
            verify_resp = client.get("1.3.6.1.2.1.1.5.0", agent=agent)
            self.assertEqual(verify_resp.varbinds[0].value, "cisco-asr9k-pe1.netspout.lab")

    def test_19_malformed_ber_rejection(self) -> None:
        """19. Malformed BER, truncated TLV, indefinite length (0x80), and deep nesting do not crash agent."""
        with SimulatedSnmpAgent(bind_port=0, phase="BASELINE", seed=42) as agent:
            malformed_payloads = [
                b"",
                b"\x30\x80\x02\x01\x01\x00\x00",  # indefinite length 0x80
                b"\x30\x20\x02\x01\x01",          # truncated packet
                b"\x31\x05\x02\x01\x01\x05\x00",  # wrong outer tag
                b"\x30\x12\x30\x10\x30\x0e\x30\x0c\x30\x0a\x30\x08\x30\x06\x30\x04\x05\x00",  # excessive nesting
                b"\xff" * 1600,                   # oversized > 1472 bytes
            ]
            for payload in malformed_payloads:
                out = agent.handle_raw_datagram(payload)
                self.assertIsNone(out)
            self.assertEqual(agent.malformed_requests, len(malformed_payloads))
            # Agent remains healthy and responsive
            client = SnmpPollingClient(port=agent.bound_port)
            resp = client.get("1.3.6.1.2.1.1.3.0", agent=agent)
            self.assertEqual(resp.varbinds[0].value, 8639000)

    def test_20_malformed_request_handling(self) -> None:
        """20. Invalid SNMP version, wrong community, unsupported PDU, and replay handling."""
        with SimulatedSnmpAgent(bind_port=0, phase="BASELINE", seed=42) as agent:
            # SNMPv1 (version=0) packet
            v1_pkt = bytes.fromhex("3026020100040c6e657473706f75742d6c6162a0130201010201000201003008300606022b060500")
            self.assertIsNone(agent.handle_raw_datagram(v1_pkt))
            self.assertEqual(agent.bad_version_requests, 1)

            # Wrong community string
            bad_comm_msg = SnmpMessage(
                community="wrong-secret",
                pdu_type=SnmpPduType.GET_REQUEST.value,
                request_id=91,
                varbinds=[SnmpVarBind(oid="1.3.6.1.2.1.1.1.0", asn1_type="Null", value=None)],
            )
            self.assertIsNone(agent.handle_raw_datagram(SnmpBerEncoder.encode_message(bad_comm_msg)))
            self.assertEqual(agent.bad_community_requests, 1)

            # Trapv2 (0xA7) sent to polling agent port -> ignored safely
            trap_bytes = bytes.fromhex(GOLDEN_HEX_FIXTURES["fixture_1_linkdown_trap"]["expected_hex"])
            self.assertIsNone(agent.handle_raw_datagram(trap_bytes))
            self.assertEqual(agent.unsupported_pdu_rejected, 1)

    def test_21_request_rate_limiting(self) -> None:
        """21. Agent enforces max_packets rate ceiling to prevent amplification/DoS."""
        agent = SimulatedSnmpAgent(bind_port=0, max_packets=3, test_mode=True)
        req_msg = SnmpMessage(
            community=DEFAULT_AGENT_COMMUNITY,
            pdu_type=SnmpPduType.GET_REQUEST.value,
            request_id=101,
            varbinds=[SnmpVarBind(oid="1.3.6.1.2.1.1.3.0", asn1_type="Null", value=None)],
        )
        wire = SnmpBerEncoder.encode_message(req_msg)
        for _ in range(3):
            self.assertIsNotNone(agent.handle_raw_datagram(wire))
        self.assertIsNone(agent.handle_raw_datagram(wire))
        self.assertEqual(agent.rate_limited_requests, 1)

    def test_22_loopback_bind_safety(self) -> None:
        """22. Default bind is 127.0.0.1:1161; 0.0.0.0, public IPs, and privileged ports (<1024) are rejected."""
        default_agent = SimulatedSnmpAgent()
        self.assertEqual(default_agent.bind_host, DEFAULT_AGENT_BIND_HOST)
        self.assertEqual(default_agent.requested_port, DEFAULT_AGENT_BIND_PORT)

        for bad_host, bad_port in [
            ("0.0.0.0", 1161),
            ("8.8.8.8", 1161),
            ("224.0.0.1", 1161),
            ("127.0.0.1", 161),
        ]:
            with self.assertRaises(DestinationSecurityException):
                SimulatedSnmpAgent(bind_host=bad_host, bind_port=bad_port)

    def test_23_clean_shutdown(self) -> None:
        """23. Agent starts, serves requests, shuts down cleanly, and releases its UDP port."""
        agent = SimulatedSnmpAgent(bind_port=0)
        port = agent.start()
        self.assertTrue(agent._running)
        agent.stop()
        self.assertFalse(agent._running)
        self.assertIsNone(agent._sock)

        # Verify offline agent times out cleanly and never claims MANAGER_OBSERVED
        client = SnmpPollingClient(port=port, timeout_sec=0.1)
        with self.assertRaises((socket.timeout, OSError)):
            client.get("1.3.6.1.2.1.1.1.0")
        ev = agent.get_evidence()
        self.assertEqual(ev.manager_observed_responses, 0)
        self.assertNotEqual(ev.evidence_stage, SnmpEvidenceStage.SPLUNK_OBSERVED.value)

    def test_24_deterministic_state(self) -> None:
        """24. Identical (scenario, seed, phase, device) produces identical OID trees and values."""
        for phase in ("BASELINE", "DEGRADE", "FAILOVER", "RECOVERY"):
            s1 = build_service_provider_cisco_oid_store(phase=phase, seed=77)
            s2 = build_service_provider_cisco_oid_store(phase=phase, seed=77)
            self.assertEqual(s1.to_snapshot_dict(), s2.to_snapshot_dict())

    def test_25_scenario_phase_state_transition(self) -> None:
        """25. Agent transitions deterministically across BASELINE -> DEGRADE -> FAILOVER -> RECOVERY."""
        with SimulatedSnmpAgent(bind_port=0, phase="BASELINE", seed=42) as agent:
            client = SnmpPollingClient(port=agent.bound_port)
            phases_expected = [
                ("BASELINE", 8639000, 1, 6, "198.51.100.1"),
                ("DEGRADE", 8640000, 2, 1, "198.51.100.2"),
                ("FAILOVER", 8640500, 2, 1, "198.51.100.2"),
                ("RECOVERY", 8643500, 1, 6, "198.51.100.1"),
            ]
            for phase, exp_uptime, exp_if_oper, exp_bgp_state, exp_nexthop in phases_expected:
                agent.set_phase(phase)
                resp = client.get(
                    [
                        "1.3.6.1.2.1.1.3.0",
                        "1.3.6.1.2.1.2.2.1.8.1",
                        "1.3.6.1.2.1.15.3.1.2.198.51.100.1",
                        "1.3.6.1.2.1.4.21.1.7.0.0.0.0",
                    ],
                    agent=agent,
                )
                self.assertEqual(resp.varbinds[0].value, exp_uptime)
                self.assertEqual(resp.varbinds[1].value, exp_if_oper)
                self.assertEqual(resp.varbinds[2].value, exp_bgp_state)
                self.assertEqual(resp.varbinds[3].value, exp_nexthop)

    def test_26_interface_state_coherence(self) -> None:
        """26. Interface operational state, error counters, and backup traffic evolve coherently."""
        s_base = build_service_provider_cisco_oid_store("BASELINE", seed=42)
        s_deg = build_service_provider_cisco_oid_store("DEGRADE", seed=42)
        s_fail = build_service_provider_cisco_oid_store("FAILOVER", seed=42)
        s_rec = build_service_provider_cisco_oid_store("RECOVERY", seed=42)

        self.assertEqual(s_base.get_exact("1.3.6.1.2.1.2.2.1.8.1").value, 1)
        self.assertEqual(s_base.get_exact("1.3.6.1.2.1.2.2.1.14.1").value, 0)

        self.assertEqual(s_deg.get_exact("1.3.6.1.2.1.2.2.1.8.1").value, 2)
        self.assertGreater(s_deg.get_exact("1.3.6.1.2.1.2.2.1.14.1").value, 0)

        # Backup interface ifHCInOctets surges during FAILOVER
        self.assertGreater(
            s_fail.get_exact("1.3.6.1.2.1.31.1.1.1.6.2").value,
            s_deg.get_exact("1.3.6.1.2.1.31.1.1.1.6.2").value,
        )
        self.assertEqual(s_rec.get_exact("1.3.6.1.2.1.2.2.1.8.1").value, 1)

    def test_27_bgp_state_coherence(self) -> None:
        """27. BGP peer 198.51.100.1 state, last error, and FSM transitions evolve coherently."""
        s_base = build_service_provider_cisco_oid_store("BASELINE", seed=42)
        s_fail = build_service_provider_cisco_oid_store("FAILOVER", seed=42)
        s_rec = build_service_provider_cisco_oid_store("RECOVERY", seed=42)

        self.assertEqual(s_base.get_exact("1.3.6.1.2.1.15.3.1.2.198.51.100.1").value, 6)
        self.assertEqual(s_base.get_exact("1.3.6.1.2.1.15.3.1.14.198.51.100.1").value, b"\x00\x00")

        self.assertEqual(s_fail.get_exact("1.3.6.1.2.1.15.3.1.2.198.51.100.1").value, 1)
        self.assertEqual(s_fail.get_exact("1.3.6.1.2.1.15.3.1.14.198.51.100.1").value, b"\x04\x00")

        self.assertEqual(s_rec.get_exact("1.3.6.1.2.1.15.3.1.2.198.51.100.1").value, 6)
        self.assertEqual(s_rec.get_exact("1.3.6.1.2.1.15.3.1.14.198.51.100.1").value, b"\x00\x00")
        self.assertGreater(
            s_rec.get_exact("1.3.6.1.2.1.15.3.1.15.198.51.100.1").value,
            s_base.get_exact("1.3.6.1.2.1.15.3.1.15.198.51.100.1").value,
        )

    def test_28_trap_poll_coherence(self) -> None:
        """28. Gate 12B Traps (linkDown, bgpBackwardTransition, linkUp, bgpEstablished) are 100% coherent with polling state."""
        trap_pdus = snmp_engine.build_service_provider_cisco_native_pdus(seed=42, pdu_mode="TRAP")
        phase_sequence = ["DEGRADE", "FAILOVER", "RECOVERY", "RECOVERY"]
        for pdu, phase in zip(trap_pdus, phase_sequence):
            store = build_service_provider_cisco_oid_store(phase=phase, seed=42)
            report = verify_trap_poll_coherence(pdu, store)
            self.assertTrue(report["coherent"], f"Trap/Poll mismatch in {phase}: {report}")

    def test_29_inform_poll_coherence(self) -> None:
        """29. Gate 12B Informs are 100% coherent with polling state across all 4 notifications."""
        inform_pdus = snmp_engine.build_service_provider_cisco_native_pdus(seed=42, pdu_mode="INFORM")
        phase_sequence = ["DEGRADE", "FAILOVER", "RECOVERY", "RECOVERY"]
        for pdu, phase in zip(inform_pdus, phase_sequence):
            store = build_service_provider_cisco_oid_store(phase=phase, seed=42)
            report = verify_trap_poll_coherence(pdu, store)
            self.assertTrue(report["coherent"], f"Inform/Poll mismatch in {phase}: {report}")

    def test_30_external_snmpget_verification(self) -> None:
        """30. Independent Net-SNMP `snmpget` CLI queries SimulatedSnmpAgent on 127.0.0.1."""
        snmpget_bin = _find_bin("snmpget", "/usr/bin/snmpget")
        self.assertTrue(snmpget_bin, "snmpget binary is required for Gate 12C external verification")

        with SimulatedSnmpAgent(bind_port=0, phase="DEGRADE", seed=42) as agent:
            target = f"127.0.0.1:{agent.bound_port}"
            proc = subprocess.run(
                [
                    snmpget_bin,
                    "-v2c",
                    "-c",
                    DEFAULT_AGENT_COMMUNITY,
                    "-On",
                    target,
                    "1.3.6.1.2.1.1.5.0",
                    "1.3.6.1.2.1.2.2.1.8.1",
                    "1.3.6.1.2.1.15.3.1.2.198.51.100.1",
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            agent.record_manager_observation(1)
            out = proc.stdout
            self.assertIn(".1.3.6.1.2.1.1.5.0", out)
            self.assertIn("cisco-asr9k-pe1.netspout.lab", out)
            self.assertTrue(
                "INTEGER: down(2)" in out or "INTEGER: 2" in out,
                f"Expected down(2) or 2 in snmpget output: {out!r}",
            )
            self.assertIn(".1.3.6.1.2.1.15.3.1.2.198.51.100.1 = INTEGER: 1", out)

    def test_31_external_snmpgetnext_verification(self) -> None:
        """31. Independent Net-SNMP `snmpgetnext` CLI traverses SimulatedSnmpAgent lexicographically."""
        snmpgetnext_bin = _find_bin("snmpgetnext", "/usr/bin/snmpgetnext")
        self.assertTrue(snmpgetnext_bin, "snmpgetnext binary is required for Gate 12C")

        with SimulatedSnmpAgent(bind_port=0, phase="BASELINE", seed=42) as agent:
            target = f"127.0.0.1:{agent.bound_port}"
            proc = subprocess.run(
                [
                    snmpgetnext_bin,
                    "-v2c",
                    "-c",
                    DEFAULT_AGENT_COMMUNITY,
                    "-On",
                    target,
                    "1.3.6.1.2.1.1.1.0",
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            agent.record_manager_observation(1)
            self.assertIn(".1.3.6.1.2.1.1.2.0", proc.stdout)
            self.assertIn(".1.3.6.1.4.1.9.1.1639", proc.stdout)

    def test_32_external_snmpwalk_verification(self) -> None:
        """32. Independent Net-SNMP `snmpwalk` CLI walks the full MIB tree in numeric order and terminates cleanly."""
        snmpwalk_bin = _find_bin("snmpwalk", "/usr/bin/snmpwalk")
        self.assertTrue(snmpwalk_bin, "snmpwalk binary is required for Gate 12C")

        with SimulatedSnmpAgent(bind_port=0, phase="BASELINE", seed=42) as agent:
            target = f"127.0.0.1:{agent.bound_port}"
            proc = subprocess.run(
                [
                    snmpwalk_bin,
                    "-v2c",
                    "-c",
                    DEFAULT_AGENT_COMMUNITY,
                    "-On",
                    target,
                    "1.3.6.1.2.1",
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            lines = [
                ln.strip()
                for ln in proc.stdout.strip().splitlines()
                if ln.strip()
                and " = " in ln
                and "No more variables left in this MIB View" not in ln
            ]
            walked_oids = [ln.split(" = ")[0].lstrip(".") for ln in lines]
            self.assertEqual(len(walked_oids), len(agent.oid_store))
            self.assertEqual(walked_oids, agent.oid_store.all_oids())

    def test_33_external_snmpbulkwalk_verification(self) -> None:
        """33. Independent Net-SNMP `snmpbulkwalk` CLI walks the full MIB tree via GETBULK and matches snmpwalk 100%."""
        snmpbulkwalk_bin = _find_bin("snmpbulkwalk", "/usr/bin/snmpbulkwalk")
        self.assertTrue(snmpbulkwalk_bin, "snmpbulkwalk binary is required for Gate 12C")

        with SimulatedSnmpAgent(bind_port=0, phase="FAILOVER", seed=42) as agent:
            target = f"127.0.0.1:{agent.bound_port}"
            proc = subprocess.run(
                [
                    snmpbulkwalk_bin,
                    "-v2c",
                    "-Cn0",
                    "-Cr15",
                    "-c",
                    DEFAULT_AGENT_COMMUNITY,
                    "-On",
                    target,
                    "1.3.6.1.2.1",
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            lines = [
                ln.strip()
                for ln in proc.stdout.strip().splitlines()
                if ln.strip()
                and " = " in ln
                and "No more variables left in this MIB View" not in ln
            ]
            walked_oids = [ln.split(" = ")[0].lstrip(".") for ln in lines]
            self.assertEqual(len(walked_oids), len(agent.oid_store))
            self.assertEqual(walked_oids, agent.oid_store.all_oids())
            self.assertGreater(agent.getbulk_requests, 0)

    def test_34_tshark_request_response_verification(self) -> None:
        """34. Independent TShark dissection of captured GET, GETNEXT, and GETBULK exchanges with 0 malformed warnings."""
        tshark_bin = _find_bin("tshark", "/opt/homebrew/bin/tshark")
        self.assertTrue(tshark_bin, "TShark binary is required for Gate 12C")

        with tempfile.TemporaryDirectory() as tmpdir:
            with SimulatedSnmpAgent(bind_port=0, phase="BASELINE", seed=42) as agent:
                client = SnmpPollingClient(port=agent.bound_port)
                client.get("1.3.6.1.2.1.1.1.0", agent=agent)
                client.get_next("1.3.6.1.2.1.1.1.0", agent=agent)
                client.get_bulk("1.3.6.1.2.1.2.2.1.8", non_repeaters=0, max_repetitions=3, agent=agent)

                pcap_path = os.path.join(tmpdir, "gate12c_polling.pcap")
                agent.export_pcap(pcap_path, normalize_agent_port=161)

            proc_v = subprocess.run(
                [tshark_bin, "-r", pcap_path, "-Y", "snmp", "-V"],
                capture_output=True,
                text=True,
                check=True,
            )
            v_out = proc_v.stdout
            self.assertNotIn("[Malformed Packet", v_out)
            self.assertNotIn("Malformed Packet", v_out)
            self.assertIn("get-request (0)", v_out)
            self.assertIn("get-next-request (1)", v_out)
            self.assertIn("getBulkRequest (5)", v_out)
            self.assertIn("get-response (2)", v_out)

    def test_35_gate12b_fixture_regression(self) -> None:
        """35. All 5 Gate 12B Golden Hex Fixtures remain 100% byte-identical."""
        results = verify_golden_fixtures()
        self.assertEqual(len(results), 5)
        for r in results:
            self.assertEqual(r["status"], "PASS", f"Fixture drift detected in {r['fixture_id']}")
            self.assertEqual(r["actual_hex"], r["expected_hex"])

    def test_36_gate12b_trap_regression(self) -> None:
        """36. Gate 12B Trapv2 loopback transport remains 100% operational."""
        with LoopbackSnmpTestReceiver() as receiver:
            pdus = snmp_engine.build_service_provider_cisco_native_pdus(seed=42, pdu_mode="TRAP")
            transport = NativeSnmpTransport(
                destination_host="127.0.0.1",
                destination_port=receiver.bound_port,
                test_mode=True,
                receiver=receiver,
            )
            res = transport.send_batch(pdus)
            self.assertEqual(res.datagrams_sent, 4)
            self.assertEqual(res.evidence_stage, SnmpEvidenceStage.RECEIVER_OBSERVED.value)

    def test_37_gate12b_inform_regression(self) -> None:
        """37. Gate 12B InformRequest ACK and retry semantics remain 100% operational."""
        with LoopbackSnmpTestReceiver(drop_acks_count=1) as receiver:
            pdus = snmp_engine.build_service_provider_cisco_native_pdus(seed=42, pdu_mode="INFORM")
            transport = NativeSnmpTransport(
                destination_host="127.0.0.1",
                destination_port=receiver.bound_port,
                inform_timeout_ms=60,
                inform_max_retries=2,
                test_mode=True,
                receiver=receiver,
            )
            res = transport.send_batch(pdus[:1])
            self.assertEqual(res.informs_acknowledged, 1)
            self.assertEqual(res.inform_retries, 1)

    def test_38_netflow_v9_regression(self) -> None:
        """38. Native NetFlow v9 binary encoding remains intact."""
        session = ExporterSession(node_id="rtr-1", exporter_ip="10.0.0.1", observation_domain_id=1, source_id=1)
        flow = FlowRecord(src_ip="10.1.1.1", dest_ip="10.2.2.2", src_port=12345, dest_port=443, protocol=6, bytes_count=1500, packets_count=10)
        pkt = NetFlowV9Encoder.build_packet(session, [flow], include_template=True)
        self.assertGreater(len(pkt), 20)
        self.assertEqual(int.from_bytes(pkt[0:2], "big"), 9)

    def test_39_ipfix_regression(self) -> None:
        """39. Native IPFIX (RFC 7011) binary encoding remains intact."""
        session = ExporterSession(node_id="rtr-1", exporter_ip="10.0.0.1", observation_domain_id=1, source_id=1)
        flow = FlowRecord(src_ip="10.1.1.1", dest_ip="10.2.2.2", src_port=12345, dest_port=443, protocol=6, bytes_count=1500, packets_count=10)
        pkt = IPFIXEncoder.build_packet(session, [flow], include_template=True)
        self.assertGreater(len(pkt), 16)
        self.assertEqual(int.from_bytes(pkt[0:2], "big"), 10)

    def test_40_golden_path_regression(self) -> None:
        """40. Canonical catalog retains all 29 scenarios and all 13 GOLDEN_PATH_CERTIFIED scenarios."""
        scenarios = catalog.list_scenarios() if hasattr(catalog, "list_scenarios") else catalog._scenarios
        self.assertGreaterEqual(len(scenarios), 29)
        gp_certified = [s for s in scenarios if s.get("maturity") == "GOLDEN_PATH_CERTIFIED"]
        self.assertEqual(len(gp_certified), 13)


if __name__ == "__main__":
    unittest.main()
