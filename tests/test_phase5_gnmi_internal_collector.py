"""Focused Phase 5 tests for the bundled Python gNMI subscriber."""

import os
import sys
import unittest
from unittest.mock import patch

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC_DIR = os.path.join(REPO_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from netspout_core.gnmi.collector_pipeline import (
    InternalGrpcGnmiCollector,
    verify_wire_payload_purity,
)
from netspout_core.gnmi.server import NativeGnmiServer, NativeGnmiServerConfig
from netspout_core.gnmi.splunk_e2e import (
    GnmiSplunkBridge,
    GnmiSplunkE2EOrchestrator,
    run_gnmi_preflight_check,
)
from netspout_core.gnmi.state_store import ScenarioStateStore


class _HealthResponse:
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


class TestPhase5InternalGnmiCollector(unittest.TestCase):
    def setUp(self):
        self.store = ScenarioStateStore(
            run_id="phase5-internal-test",
            scenario_id="openconfig_mdt_streaming",
            seed=42,
        )
        self.server = NativeGnmiServer(
            NativeGnmiServerConfig(bind_address="127.0.0.1", bind_port=0),
            state_store=self.store,
        )
        self.port = self.server.start()

    def tearDown(self):
        self.server.stop()

    def test_internal_collector_executes_capabilities_get_and_subscribe_without_binary(self):
        collector = InternalGrpcGnmiCollector(host="127.0.0.1", port=self.port)
        with patch("subprocess.run", side_effect=AssertionError("external process invoked")):
            result = collector.collect_once(
                target="node-cisco8k",
                paths=["/system/state"],
                run_id="phase5-internal-test",
            )

        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.collector_binary, "internal://netspout-python-grpc")
        self.assertTrue(result.sync_response_observed)
        self.assertGreater(len(result.normalized_records), 0)
        diagnostics = self.server.diagnostics.snapshot()
        self.assertEqual(diagnostics["capabilities_requests"], 1)
        self.assertEqual(diagnostics["get_requests"], 1)
        self.assertEqual(diagnostics["subscribe_once_requests"], 1)
        self.assertTrue(verify_wire_payload_purity(result.raw_notifications)["wire_payload_pure"])
        self.assertNotIn("netspout_run_id", str(result.raw_notifications))

    def test_malformed_path_and_subscription_failure_are_truthful(self):
        malformed = InternalGrpcGnmiCollector(host="127.0.0.1", port=self.port).collect_once(
            target="node-cisco8k",
            paths=["/interfaces/interface[name=broken/state"],
        )
        self.assertNotEqual(malformed.returncode, 0)
        self.assertFalse(malformed.ledger.collector_received)
        self.assertFalse(malformed.ledger.normalized)
        self.assertEqual(malformed.ledger.error_stage, "COLLECTOR_RECEIVED")
        self.assertTrue(malformed.stderr)

        self.server.stop()
        unavailable = InternalGrpcGnmiCollector(
            host="127.0.0.1",
            port=self.port,
            timeout_sec=0.25,
        ).collect_once(target="node-cisco8k", paths=["/system/state"])
        self.assertNotEqual(unavailable.returncode, 0)
        self.assertFalse(unavailable.sync_response_observed)
        self.assertEqual(unavailable.ledger.highest_verified_stage, "NONE")
        self.assertTrue(unavailable.stderr)

    def test_orchestrator_defaults_to_internal_collector(self):
        orchestrator = GnmiSplunkE2EOrchestrator(splunk_bridge=GnmiSplunkBridge())
        self.assertIs(orchestrator.collector_factory, InternalGrpcGnmiCollector)

    def test_preflight_does_not_block_when_optional_gnmic_is_missing(self):
        index_rows = [
            {"title": "idx_network_ops", "totalEventCount": "0", "datatype": "event"},
            {"title": "cisco_mdt_metrics", "totalEventCount": "0", "datatype": "metric"},
        ]
        with patch("os.path.isfile", return_value=False), patch(
            "shutil.which", return_value=None
        ), patch("urllib.request.urlopen", return_value=_HealthResponse()), patch.object(
            GnmiSplunkBridge, "execute_spl_search", return_value=index_rows
        ):
            preflight = run_gnmi_preflight_check()

        verifier = next(
            check for check in preflight["checks"] if check["id"] == "optional_gnmic_verifier"
        )
        self.assertTrue(verifier["passed"])
        self.assertFalse(verifier["available"])
        self.assertTrue(preflight["all_passed"])
        self.assertEqual(preflight["collector_binary"], "internal://netspout-python-grpc")


if __name__ == "__main__":
    unittest.main()
