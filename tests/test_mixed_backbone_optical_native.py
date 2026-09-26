"""
Integration Tests for First Native Scenario: mixed_backbone_optical.
Proves dual-mode execution (Direct-to-Splunk HEC vs Native UDP Wire Transport)
without forking scenario logic.
Conforms to Gate 11 Architecture Section 12 and Gate 11B Phases 17 & 18.
"""

import socket
import unittest
from netspout_core.models import ScenarioRunRequest, ValidationStatus
from netspout_core.scenario_runner import ScenarioRunner
from netspout_core.catalog import catalog_instance
from tests.reference_flow_decoder import (
    ReferenceNetFlowV9Decoder,
    ReferenceIPFIXDecoder
)


class TestMixedBackboneOpticalNative(unittest.TestCase):

    def setUp(self):
        self.runner = ScenarioRunner()

    def test_mixed_backbone_optical_direct_to_splunk_intact(self):
        """Proves existing Mode A (Direct-to-Splunk) behavior is 100% unchanged."""
        req = ScenarioRunRequest(
            scenario_id="mixed_backbone_optical",
            seed=102,
            time_mode="TEST",
            transport_mode="DIRECT_TO_SPLUNK"
        )
        manifest = self.runner.run_scenario(req)
        self.assertIsNotNone(manifest)
        self.assertEqual(manifest.scenario_id, "mixed_backbone_optical")
        self.assertIsNone(manifest.native_transport_result)

        logs = self.runner.get_run_logs(manifest.run_id)
        sourcetypes = {l.sourcetype for l in logs}
        self.assertIn("arista:flow:ipfix", sourcetypes)
        self.assertIn("nokia:sros:syslog", sourcetypes)
        self.assertIn("juniper:junos", sourcetypes)

    def test_mixed_backbone_optical_native_ipfix_execution(self):
        """Proves Mode B (Native Transport) emits wire-accurate IPFIX datagrams."""
        # 1. Ephemeral UDP receiver
        rx_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        rx_sock.bind(("127.0.0.1", 0))
        _, rx_port = rx_sock.getsockname()
        rx_sock.settimeout(2.0)

        try:
            req = ScenarioRunRequest(
                scenario_id="mixed_backbone_optical",
                seed=102,
                time_mode="TEST",
                transport_mode="NATIVE_TRANSPORT",
                native_protocol="IPFIX",
                native_destination_host="127.0.0.1",
                native_destination_port=rx_port
            )
            manifest = self.runner.run_scenario(req)

            # Assert manifest transport results
            self.assertIsNotNone(manifest.native_transport_result)
            res = manifest.native_transport_result
            self.assertEqual(res.transport_type, "IPFIX_UDP")
            self.assertEqual(res.records_received, 2)
            self.assertEqual(res.records_encoded, 2)
            self.assertGreaterEqual(res.datagrams_sent, 1)
            self.assertGreater(res.bytes_sent, 0)

            # Assert companion manifest
            self.assertIsNotNone(manifest.companion_manifest)
            self.assertEqual(manifest.companion_manifest.protocol, "IPFIX")
            self.assertEqual(manifest.companion_manifest.records_generated, 2)

            # Receive datagram and decode
            data, _ = rx_sock.recvfrom(2048)
            decoded = ReferenceIPFIXDecoder.decode_message(data)
            self.assertEqual(decoded["version"], 10)
            self.assertEqual(decoded["total_data_records"], 2)

            # Check flow 1 (Primary Egress) vs flow 2 (Bypass Egress)
            records = decoded["sets"][1]["records"]
            self.assertEqual(records[0]["ie_8"], "10.200.0.1")
            self.assertEqual(records[0]["ie_12"], "10.200.0.3")
            self.assertEqual(records[0]["ie_14"], 1)  # output ifIndex = 1 (Ethernet49/1)
            self.assertEqual(records[0]["ie_1"], 8420950)

            self.assertEqual(records[1]["ie_14"], 2)  # output ifIndex = 2 (Ethernet49/2 rerouted)
            self.assertEqual(records[1]["ie_1"], 12948200)

        finally:
            rx_sock.close()

    def test_mixed_backbone_optical_native_netflow_v9_execution(self):
        """Proves Mode B with NetFlow v9 emits wire-accurate NetFlow v9 datagrams."""
        rx_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        rx_sock.bind(("127.0.0.1", 0))
        _, rx_port = rx_sock.getsockname()
        rx_sock.settimeout(2.0)

        try:
            req = ScenarioRunRequest(
                scenario_id="mixed_backbone_optical",
                seed=102,
                time_mode="TEST",
                transport_mode="NATIVE_TRANSPORT",
                native_protocol="NETFLOW_V9",
                native_destination_host="127.0.0.1",
                native_destination_port=rx_port
            )
            manifest = self.runner.run_scenario(req)

            res = manifest.native_transport_result
            self.assertIsNotNone(res)
            self.assertEqual(res.transport_type, "NETFLOW_V9_UDP")
            self.assertEqual(res.records_encoded, 2)
            self.assertGreaterEqual(res.datagrams_sent, 1)

            data, _ = rx_sock.recvfrom(2048)
            decoded = ReferenceNetFlowV9Decoder.decode_packet(data)
            self.assertEqual(decoded["version"], 9)
            self.assertEqual(decoded["count"], 3)  # 1 template + 2 records

            records = decoded["flowsets"][1]["records"]
            self.assertEqual(records[0]["field_8"], "10.200.0.1")
            self.assertEqual(records[0]["field_12"], "10.200.0.3")
            self.assertEqual(records[0]["field_14"], 1)
            self.assertEqual(records[1]["field_14"], 2)

        finally:
            rx_sock.close()


if __name__ == "__main__":
    unittest.main()
