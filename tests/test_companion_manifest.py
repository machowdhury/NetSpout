"""
Unit Tests for CompanionControlManifest Builder.
Verifies manifest metadata generation, SPL query synthesis, and HEC event formatting.
"""

import unittest
from netspout_core.companion_manifest import CompanionManifestBuilder


class TestCompanionManifest(unittest.TestCase):

    def test_build_manifest_and_spl(self):
        manifest = CompanionManifestBuilder.build_manifest(
            run_id="run_12345",
            scenario_id="mixed_backbone_optical",
            protocol="IPFIX",
            destination_host="10.0.0.50",
            destination_port=4739,
            exporter_ip="10.200.0.3",
            observation_domain_id=101,
            template_ids=[256],
            records_generated=50,
            records_encoded=50,
            datagrams_sent=3,
            bytes_sent=3400,
            start_time_epoch_ms=1774438400000,
            end_time_epoch_ms=1774438460000
        )

        self.assertEqual(manifest.run_id, "run_12345")
        self.assertEqual(manifest.scenario_id, "mixed_backbone_optical")
        self.assertEqual(manifest.protocol, "IPFIX")
        self.assertEqual(manifest.records_generated, 50)
        self.assertIn("sourcetype=\"stream:netflow\"", manifest.splunk_suggested_spl)
        self.assertIn("1774438390", manifest.splunk_suggested_spl)

    def test_hec_event_formatting(self):
        manifest = CompanionManifestBuilder.build_manifest(
            run_id="run_123",
            scenario_id="cisco_campus_rogue",
            protocol="NETFLOW_V9",
            destination_host="127.0.0.1",
            destination_port=2055,
            exporter_ip="10.0.0.1",
            observation_domain_id=1,
            template_ids=[256],
            records_generated=10,
            records_encoded=10,
            datagrams_sent=1,
            bytes_sent=140,
            start_time_epoch_ms=1000,
            end_time_epoch_ms=2000
        )
        hec_event = CompanionManifestBuilder.to_hec_event(manifest)
        self.assertEqual(hec_event["index"], "idx_network_ops")
        self.assertEqual(hec_event["sourcetype"], "netspout:control:manifest")
        self.assertEqual(hec_event["event"]["run_id"], "run_123")


if __name__ == "__main__":
    unittest.main()
