"""Phase 5 tests for collector-side flow correlation."""

import importlib.util
import os
import time
import unittest


REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MODULE_PATH = os.path.join(REPO_ROOT, "deploy", "collector", "forwarder.py")
SPEC = importlib.util.spec_from_file_location("phase5_flow_forwarder", MODULE_PATH)
assert SPEC and SPEC.loader
forwarder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(forwarder)


class TestPhase5FlowForwarder(unittest.TestCase):
    def setUp(self):
        with forwarder.STATE_LOCK:
            forwarder.STATE["correlations"].clear()
            forwarder.STATE["last_error"] = None
            forwarder.STATE["simulate_splunk_failure"] = False

    def test_correlation_is_attached_only_after_collector_decode(self):
        native_decoded = {
            "type": "IPFIX",
            "observation_domain_id": 42,
            "src_addr": "192.0.2.10",
            "dst_addr": "198.51.100.20",
        }
        with forwarder.STATE_LOCK:
            forwarder.STATE["correlations"]["42"] = {
                "netspout_run_id": "run-phase5",
                "netspout_scenario_id": "service_provider_cisco",
                "netspout_device_id": "cisco-asr9k-pe1",
                "netspout_phase": "BASELINE",
                "expires_at": time.time() + 60,
            }

        normalized = forwarder.attach_registered_correlation(native_decoded)

        self.assertNotIn("netspout_run_id", native_decoded)
        self.assertEqual(normalized["netspout_run_id"], "run-phase5")
        self.assertEqual(
            normalized["netspout_correlation_boundary"],
            "COLLECTOR_NORMALIZED",
        )

    def test_expired_or_unknown_domain_is_not_enriched(self):
        with forwarder.STATE_LOCK:
            forwarder.STATE["correlations"]["7"] = {
                "expires_at": time.time() - 1,
            }
        decoded = {"type": "NETFLOW_V9", "observation_domain_id": 7}
        self.assertEqual(forwarder.attach_registered_correlation(decoded), decoded)
        self.assertNotIn("netspout_run_id", decoded)

    def test_delivery_health_degrades_on_forwarding_error(self):
        self.assertEqual(forwarder.delivery_health_state(), "HEALTHY")
        with forwarder.STATE_LOCK:
            forwarder.STATE["last_error"] = "HEC unavailable"
        self.assertEqual(forwarder.delivery_health_state(), "DEGRADED")


if __name__ == "__main__":
    unittest.main()
