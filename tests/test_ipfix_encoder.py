"""
Unit Tests for NetSpout IPFIX Binary Encoder.
Tests RFC 7011/7012 wire layout, field types, 64-bit counters, sequence tracking, batching, and error rejection.
"""

import unittest
from netspout_core.models import FlowRecord
from netspout_core.exporter_session import ExporterSession
from netspout_core.ipfix_encoder import (
    IPFIXEncoder,
    IPFIXValidationError,
    DEFAULT_TEMPLATE_ID_IPFIX
)
from tests.reference_flow_decoder import ReferenceIPFIXDecoder


class TestIPFIXEncoder(unittest.TestCase):

    def setUp(self):
        self.session = ExporterSession(node_id="r1", observation_domain_id=101)
        self.valid_record = FlowRecord(
            src_ip="10.1.1.10",
            dest_ip="10.2.2.20",
            src_port=5000,
            dest_port=443,
            protocol=6,
            packets_count=1000,
            bytes_count=500000,
            start_time_ms=1774438400000,
            end_time_ms=1774438450000
        )

    def test_encode_template_set(self):
        """Verifies Template Set structure, field count, and 4-byte alignment."""
        t_set = IPFIXEncoder.encode_template_set(DEFAULT_TEMPLATE_ID_IPFIX)
        self.assertEqual(len(t_set) % 4, 0, "Template Set must align to 4-byte word boundary")
        self.assertEqual(len(t_set), 68, "15-field core IPFIX template must be exactly 68 bytes")

    def test_encode_data_set(self):
        """Verifies Data Set framing with 64-byte record alignment."""
        d_set, count = IPFIXEncoder.encode_data_set([self.valid_record], self.session)
        self.assertEqual(count, 1)
        self.assertEqual(len(d_set) % 4, 0, "Data Set must align to 4-byte word boundary")
        self.assertEqual(len(d_set), 68, "Single-record Data Set must be 68 bytes (4 header + 64 rec)")

    def test_build_packet_header_and_sequence(self):
        """Verifies IPFIX 16-byte header, length field, and Data Record sequence counting."""
        # Packet with Template + 1 Data Record
        pkt1 = IPFIXEncoder.build_packet(
            session=self.session,
            data_records=[self.valid_record],
            include_template=True
        )
        self.assertEqual(len(pkt1), 152)
        # RFC 7011: sequence counts DATA records only
        self.assertEqual(self.session.sequence_number, 1)

        # Dissect message
        decoded1 = ReferenceIPFIXDecoder.decode_message(pkt1)
        self.assertEqual(decoded1["version"], 10)
        self.assertEqual(decoded1["length"], len(pkt1))
        self.assertEqual(decoded1["sequence_number"], 0)  # Pkt 1 started at seq 0
        self.assertEqual(decoded1["observation_domain_id"], 101)

        # Packet with 2 Data Records (no template)
        rec2 = FlowRecord(
            src_ip="10.1.1.11",
            dest_ip="10.2.2.21",
            src_port=5001,
            dest_port=80,
            packets_count=200,
            bytes_count=100000
        )
        pkt2 = IPFIXEncoder.build_packet(
            session=self.session,
            data_records=[self.valid_record, rec2],
            include_template=False
        )
        self.assertEqual(self.session.sequence_number, 3, "Sequence should advance by 2 data records (1 + 2 = 3)")

        decoded2 = ReferenceIPFIXDecoder.decode_message(pkt2)
        self.assertEqual(decoded2["sequence_number"], 1)

    def test_mtu_batch_splitting(self):
        """Verifies that large record batches are split safely under MTU (1400 bytes)."""
        records = [
            FlowRecord(
                src_ip=f"10.0.0.{i % 250 + 1}",
                dest_ip="10.1.0.1",
                src_port=2000 + i,
                dest_port=443,
                packets_count=10,
                bytes_count=500
            )
            for i in range(100)
        ]
        packets = IPFIXEncoder.encode_batch(
            records=records,
            session=self.session,
            include_template=True,
            max_bytes=1400
        )
        self.assertGreater(len(packets), 1, "100 records must be split into multiple datagrams")
        for pkt in packets:
            self.assertLessEqual(len(pkt), 1400, "Packet must not exceed MTU limit of 1400 bytes")

    def test_negative_invalid_ip_rejected(self):
        """Negative test: Invalid IPv4 address raises IPFIXValidationError."""
        bad_record = FlowRecord(
            src_ip="not_an_ip",
            dest_ip="10.0.0.1",
            src_port=80,
            dest_port=80
        )
        with self.assertRaises(IPFIXValidationError):
            IPFIXEncoder.encode_record(bad_record, self.session)

    def test_negative_port_out_of_range(self):
        """Negative test: Port > 65535 raises IPFIXValidationError."""
        bad_record = FlowRecord(
            src_ip="10.0.0.1",
            dest_ip="10.0.0.2",
            src_port=80,
            dest_port=99999
        )
        with self.assertRaises(IPFIXValidationError):
            IPFIXEncoder.encode_record(bad_record, self.session)

    def test_negative_negative_counters(self):
        """Negative test: Negative byte count raises IPFIXValidationError."""
        bad_record = FlowRecord(
            src_ip="10.0.0.1",
            dest_ip="10.0.0.2",
            src_port=80,
            dest_port=80,
            bytes_count=-500
        )
        with self.assertRaises(IPFIXValidationError):
            IPFIXEncoder.encode_record(bad_record, self.session)


if __name__ == "__main__":
    unittest.main()
