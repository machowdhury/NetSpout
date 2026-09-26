"""
Unit Tests for Gate 11 Golden Binary Flow Fixtures and Encoder Parity.
Proves byte-level accuracy of NetFlow v9 and IPFIX binary generation.
"""

import unittest
from netspout_core.models import FlowRecord
from netspout_core.exporter_session import ExporterSession
from netspout_core.netflow_v9_encoder import NetFlowV9Encoder
from netspout_core.ipfix_encoder import IPFIXEncoder
from tests.fixtures.golden_flows import (
    GOLDEN_BYTES_NETFLOW_V9,
    GOLDEN_BYTES_IPFIX
)
from tests.reference_flow_decoder import (
    ReferenceNetFlowV9Decoder,
    ReferenceIPFIXDecoder
)


class TestGoldenFlowFixtures(unittest.TestCase):

    def test_golden_netflow_v9_dissection(self):
        """Validates that the Gate 11 NetFlow v9 golden hex fixture decodes cleanly."""
        decoded = ReferenceNetFlowV9Decoder.decode_packet(GOLDEN_BYTES_NETFLOW_V9)
        self.assertEqual(decoded["version"], 9)
        self.assertEqual(decoded["count"], 2)
        self.assertEqual(decoded["sys_uptime_ms"], 125000)
        self.assertEqual(decoded["unix_secs"], 1774438400)
        self.assertEqual(decoded["sequence_number"], 1)
        self.assertEqual(decoded["source_id"], 101)
        self.assertIn(256, decoded["templates_learned"])
        self.assertEqual(len(decoded["templates_learned"][256]), 16)

        data_fs = [fs for fs in decoded["flowsets"] if fs["type"] == "DATA"][0]
        self.assertEqual(len(data_fs["records"]), 1)
        rec = data_fs["records"][0]
        self.assertEqual(rec["field_8"], "10.0.1.10")   # src_ip
        self.assertEqual(rec["field_12"], "10.0.2.20")  # dst_ip
        self.assertEqual(rec["field_7"], 49153)        # src_port
        self.assertEqual(rec["field_11"], 443)         # dst_port
        self.assertEqual(rec["field_2"], 1024)         # pkts
        self.assertEqual(rec["field_1"], 524288)       # bytes

    def test_netflow_v9_encoder_golden_parity(self):
        """Proves NetFlowV9Encoder generates byte-for-byte identical output to the golden fixture."""
        session = ExporterSession(node_id="test_node", source_id=101)
        session.sequence_number = 1
        # Set base time such that sysUpTime is 125000ms
        session.base_time_epoch_ms = 0

        record = FlowRecord(
            src_ip="10.0.1.10",
            dest_ip="10.0.2.20",
            bgp_next_hop="10.0.1.1",
            input_snmp=3,
            output_snmp=5,
            packets_count=1024,
            bytes_count=524288,
            start_time_ms=120000,
            end_time_ms=125000,
            src_port=49153,
            dest_port=443,
            tcp_flags=0x18,
            protocol=6,
            tos_dscp=0,
            src_as=65535,
            dest_as=61440
        )

        encoded = NetFlowV9Encoder.build_packet(
            session=session,
            data_records=[record],
            include_template=True,
            sim_time_sec=1774438400,
            sys_uptime_ms=125000
        )

        self.assertEqual(len(encoded), len(GOLDEN_BYTES_NETFLOW_V9))
        self.assertEqual(encoded, GOLDEN_BYTES_NETFLOW_V9)

    def test_golden_ipfix_dissection(self):
        """Validates that the Gate 11 IPFIX golden hex fixture decodes cleanly."""
        decoded = ReferenceIPFIXDecoder.decode_message(GOLDEN_BYTES_IPFIX)
        self.assertEqual(decoded["version"], 10)
        self.assertEqual(decoded["length"], 152)
        self.assertEqual(decoded["export_time"], 1774438400)
        self.assertEqual(decoded["sequence_number"], 1)
        self.assertEqual(decoded["observation_domain_id"], 101)
        self.assertIn(256, decoded["templates_learned"])
        self.assertEqual(len(decoded["templates_learned"][256]), 15)

        data_set = [s for s in decoded["sets"] if s["type"] == "DATA"][0]
        self.assertEqual(len(data_set["records"]), 1)
        rec = data_set["records"][0]
        self.assertEqual(rec["ie_8"], "10.0.1.10")   # src_ip
        self.assertEqual(rec["ie_12"], "10.0.2.20")  # dst_ip
        self.assertEqual(rec["ie_7"], 49153)        # src_port
        self.assertEqual(rec["ie_11"], 443)         # dst_port
        self.assertEqual(rec["ie_2"], 1024)         # pkts (uint64)
        self.assertEqual(rec["ie_1"], 524288)       # bytes (uint64)
        self.assertEqual(rec["ie_152"], 1774438400000) # start epoch ms
        self.assertEqual(rec["ie_153"], 1774438451000) # end epoch ms

    def test_ipfix_encoder_golden_parity(self):
        """Proves IPFIXEncoder generates byte-for-byte identical output to the golden fixture."""
        session = ExporterSession(node_id="test_node", observation_domain_id=101)
        session.sequence_number = 1

        record = FlowRecord(
            src_ip="10.0.1.10",
            dest_ip="10.0.2.20",
            src_port=49153,
            dest_port=443,
            protocol=6,
            tos_dscp=0,
            tcp_flags=0x0018,
            input_snmp=3,
            output_snmp=5,
            packets_count=1024,
            bytes_count=524288,
            start_time_ms=1774438400000,
            end_time_ms=1774438451000,
            src_as=65535,
            dest_as=61440
        )

        encoded = IPFIXEncoder.build_packet(
            session=session,
            data_records=[record],
            include_template=True,
            sim_time_sec=1774438400
        )

        self.assertEqual(len(encoded), len(GOLDEN_BYTES_IPFIX))
        self.assertEqual(encoded, GOLDEN_BYTES_IPFIX)


if __name__ == "__main__":
    unittest.main()
