"""
Integration Tests for NetSpout Native Flow UDP Transport.
Tests local loopback UDP reception, field validation, and controlled failure modes.
Conforms to Gate 11B Test Plan Section 5 and Phases 23, 25, 26.
"""

import socket
import unittest
from netspout_core.models import FlowRecord, TransportErrorType
from netspout_core.exporter_session import ExporterSession
from netspout_core.transport_native_flow import NativeFlowTransport
from tests.reference_flow_decoder import (
    ReferenceNetFlowV9Decoder,
    ReferenceIPFIXDecoder
)


class TestNativeFlowLoopback(unittest.TestCase):

    def test_loopback_ipfix_exchange(self):
        """Proves local UDP loopback export and reception of IPFIX datagram."""
        # 1. Bind ephemeral UDP receiver
        rx_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        rx_sock.bind(("127.0.0.1", 0))
        _, port = rx_sock.getsockname()
        rx_sock.settimeout(2.0)

        try:
            # 2. Configure NativeFlowTransport
            transport = NativeFlowTransport(
                destination_host="127.0.0.1",
                destination_port=port,
                protocol="IPFIX",
                test_mode=True
            )

            session = ExporterSession(node_id="leaf1", observation_domain_id=101)
            record = FlowRecord(
                src_ip="10.100.1.5",
                dest_ip="10.200.2.10",
                src_port=52000,
                dest_port=443,
                protocol=6,
                packets_count=500,
                bytes_count=250000,
                start_time_ms=1000,
                end_time_ms=5000
            )

            # 3. Transmit batch
            result = transport.send_batch([record], session, force_template=True)

            self.assertEqual(result.records_received, 1)
            self.assertEqual(result.records_encoded, 1)
            self.assertEqual(result.datagrams_sent, 1)
            self.assertGreater(result.bytes_sent, 0)
            self.assertEqual(len(result.errors), 0)

            # 4. Receive and decode on local receiver
            packet_data, _ = rx_sock.recvfrom(2048)
            decoded = ReferenceIPFIXDecoder.decode_message(packet_data)
            self.assertEqual(decoded["version"], 10)
            self.assertEqual(decoded["total_data_records"], 1)

            rec = decoded["sets"][1]["records"][0]
            self.assertEqual(rec["ie_8"], "10.100.1.5")
            self.assertEqual(rec["ie_12"], "10.200.2.10")
            self.assertEqual(rec["ie_7"], 52000)
            self.assertEqual(rec["ie_11"], 443)
            self.assertEqual(rec["ie_2"], 500)
            self.assertEqual(rec["ie_1"], 250000)

        finally:
            rx_sock.close()

    def test_loopback_netflow_v9_exchange(self):
        """Proves local UDP loopback export and reception of NetFlow v9 datagram."""
        rx_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        rx_sock.bind(("127.0.0.1", 0))
        _, port = rx_sock.getsockname()
        rx_sock.settimeout(2.0)

        try:
            transport = NativeFlowTransport(
                destination_host="127.0.0.1",
                destination_port=port,
                protocol="NETFLOW_V9",
                test_mode=True
            )

            session = ExporterSession(node_id="border1", source_id=202)
            record = FlowRecord(
                src_ip="192.168.10.50",
                dest_ip="172.16.0.1",
                src_port=49000,
                dest_port=80,
                protocol=6,
                packets_count=20,
                bytes_count=1200
            )

            result = transport.send_batch([record], session, force_template=True)
            self.assertEqual(result.datagrams_sent, 1)

            packet_data, _ = rx_sock.recvfrom(2048)
            decoded = ReferenceNetFlowV9Decoder.decode_packet(packet_data)
            self.assertEqual(decoded["version"], 9)
            self.assertEqual(decoded["source_id"], 202)

            rec = decoded["flowsets"][1]["records"][0]
            self.assertEqual(rec["field_8"], "192.168.10.50")
            self.assertEqual(rec["field_12"], "172.16.0.1")
            self.assertEqual(rec["field_7"], 49000)
            self.assertEqual(rec["field_11"], 80)

        finally:
            rx_sock.close()

    def test_controlled_failure_no_collector_listening(self):
        """
        Controlled failure: When sending UDP to an open/unbound port,
        OS sendto() succeeds (datagrams_sent == 1), proving that UDP send
        is strictly stage 3 (DATAGRAMS_SENT) and does NOT prove stage 4 (COLLECTOR_RECEIVED).
        """
        # Pick an arbitrary unlistened high port
        unlistened_port = 59992
        transport = NativeFlowTransport(
            destination_host="127.0.0.1",
            destination_port=unlistened_port,
            protocol="IPFIX",
            test_mode=True
        )
        session = ExporterSession(node_id="r1")
        record = FlowRecord(
            src_ip="10.0.0.1",
            dest_ip="10.0.0.2",
            src_port=1000,
            dest_port=2000
        )
        result = transport.send_batch([record], session)

        # OS reports success placing packet onto network stack
        self.assertEqual(result.datagrams_sent, 1)
        self.assertEqual(result.send_failures, 0)
        # Invariant check: sender result proves ONLY datagrams_sent, never delivery
        self.assertFalse(hasattr(result, "collector_received") and result.collector_received)


if __name__ == "__main__":
    unittest.main()
