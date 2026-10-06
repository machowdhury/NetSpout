"""
Unit Tests for NetSpout NetFlow v9 Binary Encoder.
Tests RFC 3954 wire layout, field types, padding, sequence tracking, batching, and error rejection.
"""

import unittest
from netspout_core.models import FlowRecord
from netspout_core.exporter_session import ExporterSession
from netspout_core.netflow_v9_encoder import (
    NetFlowV9Encoder,
    NetFlowV9ValidationError,
    DEFAULT_TEMPLATE_ID_V4
)
from tests.reference_flow_decoder import ReferenceNetFlowV9Decoder


class TestNetFlowV9Encoder(unittest.TestCase):

    def setUp(self):
        self.session = ExporterSession(node_id="r1", source_id=101)
        self.valid_record = FlowRecord(
            src_ip="10.1.1.10",
            dest_ip="10.2.2.20",
            src_port=5000,
            dest_port=80,
            protocol=6,
            packets_count=100,
            bytes_count=15000,
            start_time_ms=1000,
            end_time_ms=2000
        )

    def test_encode_template_flowset(self):
        """Verifies Template FlowSet structure, field count, and 4-byte padding."""
        t_fs = NetFlowV9Encoder.encode_template_flowset(DEFAULT_TEMPLATE_ID_V4)
        self.assertEqual(len(t_fs) % 4, 0, "Template FlowSet must align to 4-byte word boundary")
        self.assertEqual(len(t_fs), 72, "16-field IPv4 template FlowSet must be exactly 72 bytes")

    def test_encode_data_flowset_and_padding(self):
        """Verifies Data FlowSet framing and zero-padding to 4-byte boundary."""
        fs, count = NetFlowV9Encoder.encode_data_flowset([self.valid_record], self.session)
        self.assertEqual(count, 1)
        self.assertEqual(len(fs) % 4, 0, "Data FlowSet must align to 4-byte word boundary")
        self.assertEqual(len(fs), 48, "Single-record Data FlowSet must be 48 bytes (4 header + 43 rec + 1 pad)")

    def test_build_packet_header_and_sequence(self):
        """Verifies the header and RFC 3954 export-packet sequence tracking."""
        pkt1 = NetFlowV9Encoder.build_packet(
            session=self.session,
            data_records=[self.valid_record],
            include_template=True
        )
        self.assertEqual(len(pkt1), 140)
        self.assertEqual(self.session.sequence_number, 1)

        rec2 = FlowRecord(
            src_ip="10.1.1.11",
            dest_ip="10.2.2.21",
            src_port=5001,
            dest_port=443,
            protocol=6,
            packets_count=50,
            bytes_count=8000
        )
        pkt2 = NetFlowV9Encoder.build_packet(
            session=self.session,
            data_records=[self.valid_record, rec2],
            include_template=False
        )
        self.assertEqual(
            self.session.sequence_number,
            2,
            "Sequence number should increment once for each export packet",
        )

        # Dissect second packet
        decoded = ReferenceNetFlowV9Decoder.decode_packet(pkt2)
        self.assertEqual(decoded["sequence_number"], 1, "Pkt 2 start sequence should be 1")
        self.assertEqual(decoded["count"], 2)

    def test_mtu_batch_splitting(self):
        """Verifies that large record batches are split safely under MTU (1400 bytes)."""
        records = [
            FlowRecord(
                src_ip=f"10.0.0.{i % 250 + 1}",
                dest_ip="10.1.0.1",
                src_port=1000 + i,
                dest_port=80,
                packets_count=10,
                bytes_count=500
            )
            for i in range(100)
        ]
        packets = NetFlowV9Encoder.encode_batch(
            records=records,
            session=self.session,
            include_template=True,
            max_bytes=1400
        )
        self.assertGreater(len(packets), 1, "100 records must be split into multiple datagrams")
        for pkt in packets:
            self.assertLessEqual(len(pkt), 1400, "Packet must not exceed MTU limit of 1400 bytes")

    def test_negative_invalid_ip_rejected(self):
        """Negative test: Invalid IP address raises NetFlowV9ValidationError."""
        bad_record = FlowRecord(
            src_ip="999.999.999.999",
            dest_ip="10.0.0.1",
            src_port=80,
            dest_port=80
        )
        with self.assertRaises(NetFlowV9ValidationError):
            NetFlowV9Encoder.encode_record(bad_record, self.session)

    def test_negative_port_out_of_range(self):
        """Negative test: Port > 65535 raises NetFlowV9ValidationError."""
        bad_record = FlowRecord(
            src_ip="10.0.0.1",
            dest_ip="10.0.0.2",
            src_port=70000,
            dest_port=80
        )
        with self.assertRaises(NetFlowV9ValidationError):
            NetFlowV9Encoder.encode_record(bad_record, self.session)

    def test_negative_negative_counters(self):
        """Negative test: Negative packet/byte counts raise NetFlowV9ValidationError."""
        bad_record = FlowRecord(
            src_ip="10.0.0.1",
            dest_ip="10.0.0.2",
            src_port=80,
            dest_port=80,
            packets_count=-1
        )
        with self.assertRaises(NetFlowV9ValidationError):
            NetFlowV9Encoder.encode_record(bad_record, self.session)


if __name__ == "__main__":
    unittest.main()
