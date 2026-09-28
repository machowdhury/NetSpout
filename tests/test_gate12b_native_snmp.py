"""
NetSpout Gate 12B — Native SNMPv2c Trap & Inform Implementation & Protocol Verification Test Suite.
Covers all 26+ mandatory Gate 12B tests across:
  A. ASN.1 BER Unit Tests (short/long definite length, indefinite 0x80 rejection, signed/unsigned two's complement,
     base-128 VLQ OIDs, SMIv2 application types, exception tags, recursion depth <= 5, truncated/malformed packets)
  B. All 5 Golden Hex Fixtures (byte-for-byte + SHA-256 verification)
  C. Trap & Inform Loopback Transport & Failure Tests (varbind ordering, ACK/Response-PDU 0xA2, retry on dropped ACK,
     timeout when receiver down, wrong request-id rejection, malformed response, duplicate ACK, SENT != RECEIVER_OBSERVED)
  D. Safety & Guardrail Tests (public IP, multicast, broadcast rejection; rate limits; packet caps; 1,472-byte ceiling)
  E. Scenario Integration (service_provider_cisco ONLY) & Independent TShark Dissection (0 malformed packet warnings)
"""

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from netspout_core.models import (
    OidFidelityClass,
    SNMP_TRAP_OID,
    SYSUPTIME_OID,
    ScenarioRunRequest,
    SnmpAsn1Type,
    SnmpEvidenceStage,
    SnmpInform,
    SnmpMessage,
    SnmpPduType,
    SnmpResponse,
    SnmpTrap,
    SnmpVarBind,
    SnmpVersion,
)
from netspout_core.scenario_runner import ScenarioRunner
from netspout_core.snmp_ber import (
    GOLDEN_HEX_FIXTURES,
    InvalidSnmpOidError,
    MAX_ASN1_RECURSION_DEPTH,
    MAX_SNMP_UDP_PAYLOAD_BYTES,
    SnmpBerDecodeError,
    SnmpBerDecoder,
    SnmpBerEncodeError,
    SnmpBerEncoder,
    SnmpCommunityMismatchError,
    SnmpPayloadSizeError,
    SnmpValueTypeError,
    UnsupportedSnmpVersionError,
    build_golden_fixture_messages,
    verify_golden_fixtures,
)
from netspout_core.snmp_engine import (
    classify_oid_fidelity,
    derive_deterministic_request_id,
    format_instance_oid,
    snmp_engine,
)
from netspout_core.transport_native_snmp import (
    LoopbackSnmpTestReceiver,
    NativeSnmpTransport,
    write_snmp_pcap,
)
from netspout_core.transport_safety import DestinationSecurityException


def _find_tshark() -> str:
    for candidate in ("/opt/homebrew/bin/tshark", "/usr/local/bin/tshark", shutil.which("tshark") or ""):
        if candidate and os.path.exists(candidate):
            return candidate
    return ""


class TestGate12BNativeSnmp(unittest.TestCase):
    # =====================================================================
    # A. ASN.1 BER Unit Tests
    # =====================================================================

    def test_ber_short_and_long_definite_length(self):
        # Short form: 0..127
        self.assertEqual(SnmpBerEncoder.encode_length(0), b"\x00")
        self.assertEqual(SnmpBerEncoder.encode_length(127), b"\x7f")
        self.assertEqual(SnmpBerDecoder.decode_length(b"\x00", 0), (0, 1))
        self.assertEqual(SnmpBerDecoder.decode_length(b"\x7f" + (b"a" * 127), 0), (127, 1))

        # Long form: 128..1472
        self.assertEqual(SnmpBerEncoder.encode_length(128), b"\x81\x80")
        self.assertEqual(SnmpBerEncoder.encode_length(255), b"\x81\xff")
        self.assertEqual(SnmpBerEncoder.encode_length(256), b"\x82\x01\x00")
        self.assertEqual(SnmpBerEncoder.encode_length(1400), b"\x82\x05\x78")

        self.assertEqual(SnmpBerDecoder.decode_length(b"\x81\x80" + (b"x" * 128), 0), (128, 2))
        self.assertEqual(SnmpBerDecoder.decode_length(b"\x82\x01\x00" + (b"x" * 256), 0), (256, 3))

    def test_ber_rejects_indefinite_length(self):
        # 0x80 is ASN.1 BER indefinite length and is strictly prohibited in SNMP
        with self.assertRaises(SnmpBerDecodeError) as ctx:
            SnmpBerDecoder.decode_length(b"\x80\x00\x00", 0)
        self.assertIn("0x80", str(ctx.exception))

        # Long form > 4 octets (0x85) must also be rejected
        with self.assertRaises(SnmpBerDecodeError):
            SnmpBerDecoder.decode_length(b"\x85\x01\x02\x03\x04\x05", 0)

    def test_ber_integer_signed_twos_complement(self):
        cases = [
            (0, b"\x02\x01\x00"),
            (1, b"\x02\x01\x01"),
            (127, b"\x02\x01\x7f"),
            (128, b"\x02\x02\x00\x80"),
            (255, b"\x02\x02\x00\xff"),
            (1001, b"\x02\x02\x03\xe9"),
            (2147483647, b"\x02\x04\x7f\xff\xff\xff"),
            (-1, b"\x02\x01\xff"),
            (-128, b"\x02\x01\x80"),
            (-129, b"\x02\x02\xff\x7f"),
            (-2147483648, b"\x02\x04\x80\x00\x00\x00"),
        ]
        for val, expected_tlv in cases:
            encoded = SnmpBerEncoder.encode_value("Integer32", val)
            self.assertEqual(encoded, expected_tlv, f"Failed encoding for {val}")
            tag, body, _ = SnmpBerDecoder.decode_tlv(encoded, 0)
            self.assertEqual(tag, 0x02)
            decoded = SnmpBerDecoder.decode_integer(body, signed=True, bits=32)
            self.assertEqual(decoded, val)

        # Reject non-minimal integer encodings (redundant 0x00 or 0xFF)
        with self.assertRaises(SnmpBerDecodeError):
            SnmpBerDecoder.decode_integer(b"\x00\x01", signed=True, bits=32)
        with self.assertRaises(SnmpBerDecodeError):
            SnmpBerDecoder.decode_integer(b"\xff\x80", signed=True, bits=32)

        # Reject out-of-range or non-integer values
        with self.assertRaises(SnmpValueTypeError):
            SnmpBerEncoder.encode_value("Integer32", "not-an-int")
        with self.assertRaises(SnmpValueTypeError):
            SnmpBerEncoder.encode_value("Integer32", True)
        with self.assertRaises(SnmpValueTypeError):
            SnmpBerEncoder.encode_value("Integer32", 2147483648)

    def test_ber_octet_string_and_null(self):
        # OctetString UTF-8 and raw bytes
        s_tlv = SnmpBerEncoder.encode_value("OctetString", "netspout-lab")
        self.assertEqual(s_tlv, b"\x04\x0cnetspout-lab")
        _, body, _ = SnmpBerDecoder.decode_tlv(s_tlv, 0)
        self.assertEqual(SnmpBerDecoder.decode_value(0x04, body), ("OctetString", "netspout-lab"))

        b_tlv = SnmpBerEncoder.encode_value("OctetString", b"\x04\x00")
        self.assertEqual(b_tlv, b"\x04\x02\x04\x00")

        # NULL (05 00)
        null_tlv = SnmpBerEncoder.encode_value("Null", None)
        self.assertEqual(null_tlv, b"\x05\x00")
        self.assertEqual(SnmpBerDecoder.decode_value(0x05, b""), ("Null", None))

        with self.assertRaises(SnmpBerDecodeError):
            SnmpBerDecoder.decode_value(0x05, b"\x00")

    def test_ber_oid_base128_vlq_encoding(self):
        # Standard sysUpTime.0
        oid1 = "1.3.6.1.2.1.1.3.0"
        tlv1 = SnmpBerEncoder.encode_oid(oid1)
        self.assertEqual(tlv1, bytes.fromhex("06082b06010201010300"))
        self.assertEqual(SnmpBerDecoder.decode_oid(tlv1[2:]), oid1)

        # Enterprise OID with multi-byte base-128 VLQ arcs:
        # 255 -> 0x81 0x7f; 2636 (Juniper) -> 0x94 0x4c; 30065 (Arista) -> 0xea 0x71
        oid2 = "1.3.6.1.4.1.2636.3.1.13.1.8.255"
        tlv2 = SnmpBerEncoder.encode_oid(oid2)
        self.assertEqual(SnmpBerDecoder.decode_oid(tlv2[2:]), oid2)

        oid3 = "1.3.6.1.4.1.30065.3.1.1"
        tlv3 = SnmpBerEncoder.encode_oid(oid3)
        self.assertEqual(SnmpBerDecoder.decode_oid(tlv3[2:]), oid3)

        # Invalid OIDs rejected (NEG-02)
        for bad_oid in ("", ".1.3.6.1", "1.3.6.1.", "1.3..6.1", "1", "1.3.6.invalid.0", "9.99.1", "1.45.1"):
            with self.assertRaises(InvalidSnmpOidError):
                SnmpBerEncoder.encode_oid(bad_oid)

        # Unterminated or non-minimal VLQ rejected
        with self.assertRaises(SnmpBerDecodeError):
            SnmpBerDecoder.decode_oid(b"\x2b\x06\x81")  # Last byte has continuation bit set
        with self.assertRaises(SnmpBerDecodeError):
            SnmpBerDecoder.decode_oid(b"\x2b\x80\x01")  # Non-minimal leading 0x80

    def test_ber_ipaddress_counter32_gauge32_timeticks_counter64(self):
        # IpAddress (0x40)
        ip_tlv = SnmpBerEncoder.encode_value("IpAddress", "10.200.0.1")
        self.assertEqual(ip_tlv, b"\x40\x04\x0a\xc8\x00\x01")
        self.assertEqual(SnmpBerDecoder.decode_value(0x40, ip_tlv[2:]), ("IpAddress", "10.200.0.1"))

        with self.assertRaises(SnmpValueTypeError):
            SnmpBerEncoder.encode_value("IpAddress", "999.1.1.1")
        with self.assertRaises(SnmpBerDecodeError):
            SnmpBerDecoder.decode_value(0x40, b"\x0a\x00\x01")  # 3 bytes instead of 4

        # Counter32 (0x41), Gauge32 (0x42), TimeTicks (0x43) including MSB >= 0x80 sign-padding
        c32_val = 0x80000001
        c32_tlv = SnmpBerEncoder.encode_value("Counter32", c32_val)
        self.assertEqual(c32_tlv, b"\x41\x05\x00\x80\x00\x00\x01")
        self.assertEqual(SnmpBerDecoder.decode_value(0x41, c32_tlv[2:]), ("Counter32", c32_val))

        g32_val = 100000
        g32_tlv = SnmpBerEncoder.encode_value("Gauge32", g32_val)
        self.assertEqual(SnmpBerDecoder.decode_value(0x42, g32_tlv[2:]), ("Gauge32", g32_val))

        tt_val = 8640000  # 0x83D600 -> requires leading 0x00 -> 00 83 d6 00
        tt_tlv = SnmpBerEncoder.encode_value("TimeTicks", tt_val)
        self.assertEqual(tt_tlv, bytes.fromhex("43040083d600"))
        self.assertEqual(SnmpBerDecoder.decode_value(0x43, tt_tlv[2:]), ("TimeTicks", tt_val))

        # Opaque (0x44)
        op_tlv = SnmpBerEncoder.encode_value("Opaque", b"\xde\xad\xbe\xef")
        self.assertEqual(op_tlv, b"\x44\x04\xde\xad\xbe\xef")
        self.assertEqual(SnmpBerDecoder.decode_value(0x44, op_tlv[2:]), ("Opaque", b"\xde\xad\xbe\xef"))

        # Counter64 (0x46)
        c64_val = 0xFEDCBA9876543210
        c64_tlv = SnmpBerEncoder.encode_value("Counter64", c64_val)
        self.assertEqual(c64_tlv[:3], b"\x46\x09\x00")
        self.assertEqual(SnmpBerDecoder.decode_value(0x46, c64_tlv[2:]), ("Counter64", c64_val))

        # Negative values rejected for unsigned types (NEG-12)
        for unsigned_type in ("Counter32", "Gauge32", "TimeTicks", "Counter64"):
            with self.assertRaises(SnmpValueTypeError):
                SnmpBerEncoder.encode_value(unsigned_type, -5)

    def test_ber_exception_tags_no_such_object_instance_end_of_mib(self):
        for name, expected_tag in (
            ("noSuchObject", 0x80),
            ("noSuchInstance", 0x81),
            ("endOfMibView", 0x82),
        ):
            tlv = SnmpBerEncoder.encode_value(name, None)
            self.assertEqual(tlv, bytes([expected_tag, 0x00]))
            dec_name, dec_val = SnmpBerDecoder.decode_value(expected_tag, b"")
            self.assertEqual(dec_name, name)
            self.assertIsNone(dec_val)

            # Non-empty exception value rejected
            with self.assertRaises(SnmpBerDecodeError):
                SnmpBerDecoder.decode_value(expected_tag, b"\x01")

    def test_ber_recursion_depth_limit(self):
        # Construct a 10-level nested SEQUENCE (0x30) payload
        nested = b"\x05\x00"
        for _ in range(10):
            nested = b"\x30" + bytes([len(nested)]) + nested

        with self.assertRaises(SnmpBerDecodeError) as ctx:
            curr = nested
            for d in range(1, 10):
                _, curr, _ = SnmpBerDecoder.decode_tlv(curr, 0, depth=d, max_depth=MAX_ASN1_RECURSION_DEPTH)
        self.assertIn("recursion depth", str(ctx.exception))

    def test_ber_truncated_and_malformed_packets_rejected(self):
        valid_hex = GOLDEN_HEX_FIXTURES["fixture_1_linkdown_trap"]["expected_hex"]
        valid_bytes = bytes.fromhex(valid_hex)

        # NEG-01: Wrong outer tag (0x31 SET instead of 0x30 SEQUENCE)
        bad_outer = b"\x31" + valid_bytes[1:]
        with self.assertRaises(SnmpBerDecodeError) as ctx1:
            SnmpBerDecoder.decode_message(bad_outer)
        self.assertIn("0x30", str(ctx1.exception))

        # NEG-04: Truncated packet at byte 64
        truncated = valid_bytes[:64]
        with self.assertRaises(SnmpBerDecodeError) as ctx2:
            SnmpBerDecoder.decode_message(truncated)
        self.assertIn("Truncated", str(ctx2.exception))

        # NEG-05: Wrong community string
        with self.assertRaises(SnmpCommunityMismatchError):
            SnmpBerDecoder.decode_message(valid_bytes, expected_community="wrong-community")

        # NEG-10: Unsupported SNMP version (SNMPv1 = 0)
        v1_bytes = valid_bytes[:4] + b"\x00" + valid_bytes[5:]
        with self.assertRaises(UnsupportedSnmpVersionError):
            SnmpBerDecoder.decode_message(v1_bytes)

    # =====================================================================
    # B. Golden Hex Fixture Tests
    # =====================================================================

    def _assert_golden_fixture(self, fixture_key: str):
        spec = GOLDEN_HEX_FIXTURES[fixture_key]
        msg = build_golden_fixture_messages()[fixture_key]
        expected_bytes = bytes.fromhex(spec["expected_hex"])
        actual_bytes = SnmpBerEncoder.encode_message(msg)

        self.assertEqual(len(actual_bytes), spec["expected_length"])
        self.assertEqual(actual_bytes.hex(), spec["expected_hex"])
        self.assertEqual(
            hashlib.sha256(actual_bytes).hexdigest(),
            hashlib.sha256(expected_bytes).hexdigest(),
        )

        # Round-trip decode -> re-encode must be byte-identical
        decoded = SnmpBerDecoder.decode_message(actual_bytes, expected_community="netspout-lab")
        reencoded = SnmpBerEncoder.encode_message(decoded)
        self.assertEqual(reencoded, expected_bytes)

    def test_golden_fixture_1_linkdown_trap(self):
        self._assert_golden_fixture("fixture_1_linkdown_trap")

    def test_golden_fixture_2_linkup_trap(self):
        self._assert_golden_fixture("fixture_2_linkup_trap")

    def test_golden_fixture_3_bgp_backward_transition_inform(self):
        self._assert_golden_fixture("fixture_3_bgp_backward_transition_inform")
        # Also verify the matching Response-PDU (0xA2)
        spec = GOLDEN_HEX_FIXTURES["fixture_3_bgp_backward_transition_inform"]
        inform_msg = build_golden_fixture_messages()["fixture_3_bgp_backward_transition_inform"]
        resp_msg = SnmpResponse.from_inform(inform_msg)
        resp_bytes = SnmpBerEncoder.encode_message(resp_msg)
        self.assertEqual(resp_bytes.hex(), spec["expected_response_hex"])

    def test_golden_fixture_4_get_request(self):
        self._assert_golden_fixture("fixture_4_get_request")

    def test_golden_fixture_5_get_response(self):
        self._assert_golden_fixture("fixture_5_get_response")

    # =====================================================================
    # C. Trap & Inform Transport Tests
    # =====================================================================

    def test_trap_v2_mandatory_varbind_ordering(self):
        # Missing sysUpTime.0 at VarBind[0] must fail
        with self.assertRaises(ValueError):
            SnmpTrap(
                request_id=100,
                varbinds=[
                    SnmpVarBind(oid=SNMP_TRAP_OID, asn1_type="ObjectIdentifier", value="1.3.6.1.6.3.1.1.5.3"),
                    SnmpVarBind(oid=SYSUPTIME_OID, asn1_type="TimeTicks", value=1000),
                ],
            )

        # Wrong ASN.1 syntax for sysUpTime.0 (Integer32 instead of TimeTicks) must fail
        with self.assertRaises(ValueError):
            SnmpTrap(
                request_id=101,
                varbinds=[
                    SnmpVarBind(oid=SYSUPTIME_OID, asn1_type="Integer32", value=1000),
                    SnmpVarBind(oid=SNMP_TRAP_OID, asn1_type="ObjectIdentifier", value="1.3.6.1.6.3.1.1.5.3"),
                ],
            )

    def test_trap_loopback_receive_and_decode(self):
        trap = build_golden_fixture_messages()["fixture_1_linkdown_trap"]
        with LoopbackSnmpTestReceiver() as receiver:
            transport = NativeSnmpTransport(
                destination_host="127.0.0.1",
                destination_port=receiver.bound_port,
                test_mode=True,
                receiver=receiver,
            )
            res = transport.send_trap(trap)

            self.assertEqual(res.pdus_generated, 1)
            self.assertEqual(res.pdus_encoded, 1)
            self.assertEqual(res.datagrams_sent, 1)
            self.assertEqual(res.receiver_observed_count, 1)
            self.assertEqual(res.evidence_stage, SnmpEvidenceStage.RECEIVER_OBSERVED.value)
            self.assertEqual(
                res.stage_history,
                ["GENERATED", "ENCODED", "SENT", "RECEIVER_OBSERVED"],
            )
            self.assertEqual(receiver.traps_received, 1)
            self.assertEqual(receiver.decoded_messages[0].request_id, 1001)

    def test_inform_loopback_ack_response(self):
        inform = build_golden_fixture_messages()["fixture_3_bgp_backward_transition_inform"]
        with LoopbackSnmpTestReceiver() as receiver:
            transport = NativeSnmpTransport(
                destination_host="127.0.0.1",
                destination_port=receiver.bound_port,
                inform_timeout_ms=500,
                inform_max_retries=2,
                test_mode=True,
                receiver=receiver,
            )
            res = transport.send_inform(inform)

            self.assertEqual(res.informs_sent, 1)
            self.assertEqual(res.informs_acknowledged, 1)
            self.assertEqual(res.inform_retries, 0)
            self.assertEqual(res.inform_timeouts, 0)
            self.assertEqual(res.acknowledged_request_ids, [2001])
            self.assertEqual(res.receiver_observed_count, 1)
            self.assertEqual(res.evidence_stage, SnmpEvidenceStage.RECEIVER_OBSERVED.value)
            self.assertEqual(
                res.stage_history,
                ["GENERATED", "ENCODED", "SENT", "ACKNOWLEDGED", "RECEIVER_OBSERVED"],
            )
            self.assertEqual(receiver.informs_received, 1)
            self.assertEqual(receiver.responses_sent, 1)

    def test_inform_retry_on_dropped_ack(self):
        inform = build_golden_fixture_messages()["fixture_3_bgp_backward_transition_inform"]
        # Receiver drops the first ACK, then replies on the first retry
        with LoopbackSnmpTestReceiver(drop_acks_count=1) as receiver:
            transport = NativeSnmpTransport(
                destination_host="127.0.0.1",
                destination_port=receiver.bound_port,
                inform_timeout_ms=80,
                inform_max_retries=2,
                test_mode=True,
                receiver=receiver,
            )
            res = transport.send_inform(inform)

            self.assertEqual(res.informs_sent, 1)
            self.assertEqual(res.informs_acknowledged, 1)
            self.assertEqual(res.inform_retries, 1)
            self.assertEqual(res.datagrams_sent, 2)
            self.assertEqual(res.inform_timeouts, 0)
            # Receiver saw 2 raw Inform packets with same request-id, deduplicated to 1 logical event
            self.assertEqual(receiver.informs_received, 2)
            self.assertEqual(receiver.duplicate_informs_received, 1)
            self.assertEqual(len(receiver.deduplicated_messages), 1)

    def test_inform_timeout_when_receiver_down(self):
        # Bind an ephemeral socket and close it immediately to guarantee a closed UDP port
        temp_receiver = LoopbackSnmpTestReceiver()
        closed_port = temp_receiver.start()
        temp_receiver.stop()

        inform = build_golden_fixture_messages()["fixture_3_bgp_backward_transition_inform"]
        transport = NativeSnmpTransport(
            destination_host="127.0.0.1",
            destination_port=closed_port,
            inform_timeout_ms=40,
            inform_max_retries=2,
            test_mode=True,
        )
        res = transport.send_inform(inform)

        self.assertEqual(res.informs_sent, 1)
        self.assertEqual(res.informs_acknowledged, 0)
        self.assertEqual(res.inform_retries, 2)
        self.assertEqual(res.datagrams_sent, 3)  # 1 initial + 2 retries
        self.assertEqual(res.inform_timeouts, 1)
        self.assertEqual(res.acknowledged_request_ids, [])
        self.assertEqual(res.receiver_observed_count, 0)
        # Crucial honesty invariant: UDP sendto() is NEVER reported as ACKNOWLEDGED or RECEIVER_OBSERVED
        self.assertEqual(res.evidence_stage, SnmpEvidenceStage.SENT.value)
        self.assertNotIn(SnmpEvidenceStage.ACKNOWLEDGED.value, res.stage_history)
        self.assertNotIn(SnmpEvidenceStage.RECEIVER_OBSERVED.value, res.stage_history)

    def test_inform_rejects_mismatched_request_id(self):
        inform = build_golden_fixture_messages()["fixture_3_bgp_backward_transition_inform"]
        # Receiver injects wrong request-id (9999 instead of 2001) -> sender must reject ACK and time out
        with LoopbackSnmpTestReceiver(inject_wrong_request_id=9999) as receiver:
            transport = NativeSnmpTransport(
                destination_host="127.0.0.1",
                destination_port=receiver.bound_port,
                inform_timeout_ms=50,
                inform_max_retries=1,
                test_mode=True,
            )
            res = transport.send_inform(inform)

            self.assertEqual(res.informs_acknowledged, 0)
            self.assertEqual(res.inform_timeouts, 1)
            self.assertGreaterEqual(res.late_or_mismatched_acks, 2)
            self.assertEqual(res.evidence_stage, SnmpEvidenceStage.SENT.value)

        # Also test malformed response injection and duplicate ACK handling
        with LoopbackSnmpTestReceiver(inject_malformed_response=b"\x30\xff\x00\x01") as bad_receiver:
            transport2 = NativeSnmpTransport(
                destination_host="127.0.0.1",
                destination_port=bad_receiver.bound_port,
                inform_timeout_ms=50,
                inform_max_retries=1,
                test_mode=True,
            )
            res2 = transport2.send_inform(inform)
            self.assertEqual(res2.informs_acknowledged, 0)
            self.assertEqual(res2.inform_timeouts, 1)
            self.assertGreaterEqual(res2.late_or_mismatched_acks, 2)

        # Duplicate ACK handling
        with LoopbackSnmpTestReceiver(duplicate_ack_count=2) as dup_receiver:
            transport3 = NativeSnmpTransport(
                destination_host="127.0.0.1",
                destination_port=dup_receiver.bound_port,
                inform_timeout_ms=100,
                inform_max_retries=1,
                test_mode=True,
                receiver=dup_receiver,
            )
            res3 = transport3.send_inform(inform)
            self.assertEqual(res3.informs_acknowledged, 1)
            self.assertEqual(res3.acknowledged_request_ids, [2001])

    def test_trap_sent_is_not_receiver_observed_when_receiver_down(self):
        temp_receiver = LoopbackSnmpTestReceiver()
        closed_port = temp_receiver.start()
        temp_receiver.stop()

        trap = build_golden_fixture_messages()["fixture_1_linkdown_trap"]
        transport = NativeSnmpTransport(
            destination_host="127.0.0.1",
            destination_port=closed_port,
            test_mode=True,
        )
        res = transport.send_trap(trap)

        # OS UDP socket sendto() succeeds on loopback, so stage is SENT,
        # but receiver_observed_count MUST be 0 and stage MUST NOT be RECEIVER_OBSERVED or SPLUNK_OBSERVED.
        self.assertEqual(res.datagrams_sent, 1)
        self.assertEqual(res.receiver_observed_count, 0)
        self.assertEqual(res.evidence_stage, SnmpEvidenceStage.SENT.value)
        self.assertNotIn(SnmpEvidenceStage.RECEIVER_OBSERVED.value, res.stage_history)
        self.assertNotIn(SnmpEvidenceStage.SPLUNK_OBSERVED.value, res.stage_history)

    # =====================================================================
    # D. Safety & Guardrail Tests
    # =====================================================================

    def test_snmp_rejects_public_ip_multicast_and_broadcast(self):
        trap = build_golden_fixture_messages()["fixture_1_linkdown_trap"]

        for forbidden_host in ("8.8.8.8", "1.1.1.1", "224.0.0.1", "255.255.255.255"):
            transport = NativeSnmpTransport(
                destination_host=forbidden_host,
                destination_port=1162,
                allow_public=False,
                test_mode=True,
            )
            res = transport.send_trap(trap)
            self.assertEqual(res.datagrams_sent, 0, f"Should block {forbidden_host}")
            self.assertGreater(len(res.errors), 0)

        # LoopbackSnmpTestReceiver must also refuse to bind to non-127.0.0.1
        with self.assertRaises(DestinationSecurityException):
            LoopbackSnmpTestReceiver(host="0.0.0.0")

    def test_snmp_rate_limiter_and_packet_cap(self):
        # Hard ceilings above 250 pps (trap), 100 pps (inform), or 5,000 packet cap must raise ValueError
        with self.assertRaises(ValueError):
            NativeSnmpTransport(trap_rate_pps=251)
        with self.assertRaises(ValueError):
            NativeSnmpTransport(inform_rate_pps=101)
        with self.assertRaises(ValueError):
            NativeSnmpTransport(packet_cap=5001)

        # Packet cap enforcement on a burst of 20 traps with packet_cap=5
        traps = [
            SnmpTrap(
                request_id=1000 + i,
                sys_uptime=8640000 + i,
                trap_oid="1.3.6.1.6.3.1.1.5.3",
                varbinds=[SnmpVarBind(oid="1.3.6.1.2.1.2.2.1.1.1", asn1_type="Integer32", value=1)],
            )
            for i in range(20)
        ]
        with LoopbackSnmpTestReceiver() as receiver:
            transport = NativeSnmpTransport(
                destination_host="127.0.0.1",
                destination_port=receiver.bound_port,
                packet_cap=5,
                test_mode=True,
                receiver=receiver,
            )
            res = transport.send_batch(traps)
            self.assertEqual(res.datagrams_sent, 5)
            self.assertTrue(res.packet_cap_exceeded)

    def test_snmp_max_udp_payload_1472_enforced(self):
        oversized_trap = SnmpTrap(
            request_id=5555,
            sys_uptime=8640000,
            trap_oid="1.3.6.1.6.3.1.1.5.3",
            varbinds=[
                SnmpVarBind(
                    oid="1.3.6.1.2.1.2.2.1.2.1",
                    asn1_type="OctetString",
                    value="X" * 1500,
                )
            ],
        )
        with self.assertRaises(SnmpPayloadSizeError):
            SnmpBerEncoder.encode_message(oversized_trap, max_payload_bytes=MAX_SNMP_UDP_PAYLOAD_BYTES)

        with LoopbackSnmpTestReceiver() as receiver:
            transport = NativeSnmpTransport(
                destination_host="127.0.0.1",
                destination_port=receiver.bound_port,
                test_mode=True,
                receiver=receiver,
            )
            res = transport.send_trap(oversized_trap)
            self.assertEqual(res.datagrams_sent, 0)
            self.assertEqual(res.encoding_failures, 1)

    # =====================================================================
    # E. Scenario & Independent TShark Verification Tests
    # =====================================================================

    def test_service_provider_cisco_native_snmp_progression(self):
        # Verify sysObjectID metadata fix and OID fidelity classifications
        mibs_by_name = {m.name: m for m in snmp_engine.list_mibs()}
        self.assertEqual(mibs_by_name["sysObjectID"].data_type, "ObjectIdentifier")
        self.assertEqual(mibs_by_name["sysObjectID"].fidelity, OidFidelityClass.STANDARD_VERIFIED.value)
        self.assertEqual(
            classify_oid_fidelity("1.3.6.1.4.1.9.9.109.1.1.1.1.8", "CISCO-PROCESS-MIB", "Cisco"),
            OidFidelityClass.VENDOR_VERIFIED.value,
        )
        self.assertEqual(
            classify_oid_fidelity("1.3.6.1.4.1.30065.3.1.1", "ARISTA-QUEUE-MIB", "Arista"),
            OidFidelityClass.MODELED.value,
        )
        self.assertEqual(
            classify_oid_fidelity("1.3.6.1.4.1.59999.1.1.0", "SYNTHETIC-MIB", "SYNTHETIC"),
            OidFidelityClass.SYNTHETIC.value,
        )

        # Verify deterministic request-id derivation
        r1 = derive_deterministic_request_id("service_provider_cisco", seed=42, pdu_index=0)
        r2 = derive_deterministic_request_id("service_provider_cisco", seed=42, pdu_index=0)
        self.assertEqual(r1, r2)
        self.assertGreater(r1, 0)

        # Run service_provider_cisco in NATIVE_TRANSPORT (INFORM mode) against LoopbackSnmpTestReceiver
        with LoopbackSnmpTestReceiver() as receiver:
            runner = ScenarioRunner()
            req = ScenarioRunRequest(
                scenario_id="service_provider_cisco",
                seed=42,
                time_mode="TEST",
                dispatch_telemetry=False,
                transport_mode="NATIVE_TRANSPORT",
                native_protocol="SNMPV2C_INFORM",
                native_destination_host="127.0.0.1",
                native_destination_port=receiver.bound_port,
                native_snmp_pdu_mode="INFORM",
            )
            manifest = runner.run_scenario(req)

            # 1. Existing HEC log generation and contract validation remain intact
            self.assertEqual(manifest.overall_validation, "PASS")
            self.assertGreater(manifest.total_events_generated, 0)

            # 2. 4 Native SNMPv2c PDUs generated in exact progression:
            #    linkDown -> bgpBackwardTransition -> linkUp -> bgpEstablished
            self.assertEqual(len(manifest.native_snmp_pdus), 4)
            trap_oids = [p.trap_oid for p in manifest.native_snmp_pdus]
            self.assertEqual(
                trap_oids,
                [
                    "1.3.6.1.6.3.1.1.5.3",  # IF-MIB::linkDown
                    "1.3.6.1.2.1.15.7.2",   # BGP4-MIB::bgpBackwardTransition
                    "1.3.6.1.6.3.1.1.5.4",  # IF-MIB::linkUp
                    "1.3.6.1.2.1.15.7.1",   # BGP4-MIB::bgpEstablished
                ],
            )

            # 3. Verify all 4 Informs were acknowledged and CompanionControlManifest correlates by request_ids
            snmp_res = manifest.native_snmp_result
            self.assertEqual(snmp_res.pdus_generated, 4)
            self.assertEqual(snmp_res.informs_acknowledged, 4)
            self.assertEqual(len(snmp_res.acknowledged_request_ids), 4)
            self.assertEqual(manifest.companion_manifest.request_ids, snmp_res.request_ids)
            self.assertEqual(manifest.companion_manifest.trap_oids, trap_oids)

            # 4. Verify zero proprietary NetSpout varbinds were injected onto the wire
            for msg in receiver.decoded_messages:
                for vb in msg.varbinds:
                    self.assertFalse(vb.oid.startswith("1.3.6.1.4.1.59999"))
                    self.assertNotIn("netspout_run_id", str(vb.value))

    def test_tshark_dissects_snmp_trap_and_inform_zero_malformed(self):
        tshark_bin = _find_tshark()
        self.assertTrue(tshark_bin, "TShark binary (/opt/homebrew/bin/tshark) is required for Gate 12B")

        with tempfile.TemporaryDirectory() as tmpdir:
            with LoopbackSnmpTestReceiver() as receiver:
                bound_port = receiver.bound_port
                # Send TRAP progression + INFORM progression through live loopback UDP socket
                trap_pdus = snmp_engine.build_service_provider_cisco_native_pdus(
                    seed=42, pdu_mode="TRAP", community="netspout-lab"
                )
                inform_pdus = snmp_engine.build_service_provider_cisco_native_pdus(
                    seed=99, pdu_mode="INFORM", community="netspout-lab"
                )
                transport = NativeSnmpTransport(
                    destination_host="127.0.0.1",
                    destination_port=bound_port,
                    test_mode=True,
                    receiver=receiver,
                )
                res_trap = transport.send_batch(trap_pdus)
                res_inform = transport.send_batch(inform_pdus)

                self.assertEqual(res_trap.datagrams_sent, 4)
                self.assertEqual(res_inform.informs_acknowledged, 4)
                self.assertTrue(receiver.wait_for_packets(8, timeout_sec=2.0))

                pcap_path = os.path.join(tmpdir, "gate12b_snmp_verification.pcap")
                receiver.export_pcap(pcap_path)

            decode_arg = f"udp.port=={bound_port},snmp"

            # 1. Run tshark verbose dissection and verify zero Malformed Packet warnings
            proc_v = subprocess.run(
                [tshark_bin, "-r", pcap_path, "-d", decode_arg, "-Y", "snmp", "-V"],
                capture_output=True,
                text=True,
                check=True,
            )
            v_out = proc_v.stdout
            self.assertNotIn("[Malformed Packet", v_out)
            self.assertNotIn("Malformed Packet", v_out)
            self.assertIn("Simple Network Management Protocol", v_out)
            self.assertIn("version: v2c (1)", v_out)
            self.assertIn("community: netspout-lab", v_out)
            self.assertIn("snmpV2-trap (7)", v_out)
            self.assertIn("informRequest (6)", v_out)
            self.assertIn("get-response (2)", v_out)
            self.assertIn("1.3.6.1.2.1.1.3.0", v_out)
            self.assertIn("1.3.6.1.6.3.1.1.4.1.0", v_out)
            self.assertIn("1.3.6.1.6.3.1.1.5.3", v_out)
            self.assertIn("1.3.6.1.2.1.15.7.2", v_out)
            self.assertIn("1.3.6.1.6.3.1.1.5.4", v_out)
            self.assertIn("1.3.6.1.2.1.15.7.1", v_out)

            # 2. Run tshark fields check to verify all 12 frames (4 Traps + 4 Informs + 4 Responses)
            proc_fields = subprocess.run(
                [
                    tshark_bin,
                    "-r",
                    pcap_path,
                    "-d",
                    decode_arg,
                    "-Y",
                    "snmp",
                    "-T",
                    "fields",
                    "-e",
                    "snmp.version",
                    "-e",
                    "snmp.community",
                    "-e",
                    "snmp.data",
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            lines = [ln.strip() for ln in proc_fields.stdout.strip().splitlines() if ln.strip()]
            self.assertEqual(len(lines), 12)
            for ln in lines:
                parts = ln.split("\t")
                self.assertEqual(parts[0], "1")
                self.assertEqual(parts[1], "netspout-lab")
                self.assertIn(parts[2], ("7", "6", "2"))


if __name__ == "__main__":
    unittest.main()
