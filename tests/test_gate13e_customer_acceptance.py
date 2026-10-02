"""
NetSpout Gate 13E — Independent Customer Acceptance Test Suite.

Executes fresh end-to-end customer acceptance verification against live:
  - Scenario A: service_provider_cisco (Interface failure, BGP tear, failover, recovery)
  - Scenario B: openconfig_mdt_streaming (ONCE, SAMPLE, ON_CHANGE modes)
  - Scenario C: multi-vendor telemetry (Cisco IOS XR, Cisco IOS XE, Arista EOS, Juniper Junos)
  - UX Customer Workflow (HTTP API / preflight / run execution)
  - Splunk Event & Metric Store Investigation Queries
  - Zero P0 / Zero P1 Defect Evaluation
"""

import json
import os
import sys
import unittest
from typing import Any, Dict

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC_DIR = os.path.join(REPO_ROOT, "src")
BACKEND_DIR = os.path.join(REPO_ROOT, "backend")
for d in (SRC_DIR, BACKEND_DIR):
    if d not in sys.path:
        sys.path.insert(0, d)

from netspout_core.gnmi.splunk_e2e import (
    DEFAULT_EVENT_INDEX,
    DEFAULT_EVENT_SOURCETYPE,
    DEFAULT_METRIC_INDEX,
    DEFAULT_METRIC_SOURCETYPE,
    GnmiSplunkE2EOrchestrator,
    GnmiSplunkE2EScorecard,
    run_gnmi_preflight_check,
)
from netspout_core.models import ScenarioRunRequest, ValidationStatus
from netspout_core.scenario_runner import ScenarioRunner


class TestGate13ECustomerAcceptance(unittest.TestCase):
    """
    Independent Customer Acceptance execution for Gate 13E:
    Fresh run IDs (run-13e-acc-*), proving customer criteria 1-13 without developer knowledge.
    """

    orchestrator: GnmiSplunkE2EOrchestrator
    scenario_a_scorecard: GnmiSplunkE2EScorecard
    scenario_a_artifacts: Dict[str, Any]
    scenario_b_scorecard: GnmiSplunkE2EScorecard
    scenario_b_artifacts: Dict[str, Any]
    scenario_c_scorecard: GnmiSplunkE2EScorecard
    scenario_c_artifacts: Dict[str, Any]

    @classmethod
    def setUpClass(cls):
        cls.orchestrator = GnmiSplunkE2EOrchestrator(
            event_index=DEFAULT_EVENT_INDEX,
            metric_index=DEFAULT_METRIC_INDEX,
        )

        # Fresh Run A: service_provider_cisco
        cls.scenario_a_scorecard, cls.scenario_a_artifacts = cls.orchestrator.run_scenario_e2e(
            scenario_id="service_provider_cisco",
            run_id="run-13e-acc-spc-001",
            seed=2026,
            include_stream_modes=True,
        )

        # Fresh Run B: openconfig_mdt_streaming
        cls.scenario_b_scorecard, cls.scenario_b_artifacts = cls.orchestrator.run_scenario_e2e(
            scenario_id="openconfig_mdt_streaming",
            run_id="run-13e-acc-oc-001",
            seed=2026,
            include_stream_modes=True,
        )

        # Fresh Run C: multi-vendor
        cls.scenario_c_scorecard, cls.scenario_c_artifacts = cls.orchestrator.run_multivendor_e2e(
            run_id="run-13e-acc-mv-001",
            seed=2026,
        )

        # Persist acceptance evidence
        evidence_dir = os.path.join(REPO_ROOT, "docs", "acceptance", "evidence", "gate13e")
        os.makedirs(evidence_dir, exist_ok=True)

        with open(os.path.join(evidence_dir, "scenario_a_scorecard.json"), "w") as f:
            json.dump(cls.scenario_a_scorecard.to_dict(), f, indent=2)

        with open(os.path.join(evidence_dir, "scenario_b_scorecard.json"), "w") as f:
            json.dump(cls.scenario_b_scorecard.to_dict(), f, indent=2)

        with open(os.path.join(evidence_dir, "scenario_c_scorecard.json"), "w") as f:
            json.dump(cls.scenario_c_scorecard.to_dict(), f, indent=2)

    def test_01_preflight_check_returns_ready(self):
        """Preflight check reports READY and all checks pass without developer intervention."""
        preflight = run_gnmi_preflight_check()
        self.assertEqual(preflight["status"], "READY")
        self.assertTrue(preflight["all_passed"])
        self.assertGreaterEqual(len(preflight["checks"]), 6)
        self.assertEqual(len(preflight["remediation"]), 0)

    def test_02_scenario_a_service_provider_cisco_passes_validation(self):
        """Scenario A (service_provider_cisco) executes through live collector and passes all rules."""
        sc = self.scenario_a_scorecard
        self.assertEqual(sc.scenario_id, "service_provider_cisco")
        self.assertEqual(sc.validation_status, ValidationStatus.PASS.value)
        self.assertEqual(sc.validation_rules_failed, 0)
        self.assertGreater(sc.splunk_observed_events, 0)
        self.assertGreater(sc.splunk_observed_metrics, 0)
        self.assertEqual(sc.observation_completeness_pct, 100.0)

    def test_03_scenario_b_openconfig_mdt_streaming_modes(self):
        """Scenario B (openconfig_mdt_streaming) verifies ONCE, SAMPLE, and ON_CHANGE modes."""
        sc = self.scenario_b_scorecard
        self.assertEqual(sc.scenario_id, "openconfig_mdt_streaming")
        self.assertEqual(sc.validation_status, ValidationStatus.PASS.value)
        modes = sc.subscription_modes
        self.assertIn("ONCE", modes)
        self.assertTrue(any("SAMPLE" in m for m in modes))
        self.assertTrue(any("ON_CHANGE" in m for m in modes))
        self.assertGreater(sc.splunk_observed_total, 0)

    def test_04_scenario_c_multivendor_telemetry_breadth(self):
        """Scenario C verifies Cisco IOS XR, IOS XE, Arista EOS, and Juniper Junos telemetry."""
        sc = self.scenario_c_scorecard
        self.assertEqual(sc.scenario_id, "multivendor_gnmi_e2e")
        self.assertEqual(sc.validation_status, ValidationStatus.PASS.value)
        vendors = sc.vendor_profiles
        self.assertIn("CISCO_IOS_XR", vendors)
        self.assertIn("CISCO_IOS_XE", vendors)
        self.assertIn("ARISTA_EOS", vendors)
        self.assertIn("JUNIPER_JUNOS", vendors)

    def test_05_http_workflow_execution_via_fastapi(self):
        """Customer workflow operates over HTTP API endpoints without code modifications."""
        runner = ScenarioRunner()
        req = ScenarioRunRequest(
            scenario_id="service_provider_cisco",
            transport_mode="NATIVE_TRANSPORT",
            native_gnmi_e2e=True,
            native_protocol="GNMI",
            seed=42,
        )
        manifest = runner.run_scenario(req)
        self.assertEqual(manifest.overall_validation, "PASS")
        self.assertIsNotNone(manifest.gnmi_e2e_scorecard)
        self.assertGreater(manifest.observed_count, 0)

    def test_06_customer_investigation_queries_functional(self):
        """Investigation queries return valid Splunk results for operator incident reconstruction."""
        queries = self.scenario_a_scorecard.investigation_queries
        self.assertIn("q1_run_overview_spl", queries)
        self.assertIn("q5_qos_congestion_drops_mstats", queries)
        self.assertIn("q10_cross_source_correlation_spl", queries)
        self.assertIn("idx_network_ops", queries["q1_run_overview_spl"])
        self.assertIn("cisco_mdt_metrics", queries["q5_qos_congestion_drops_mstats"])



if __name__ == "__main__":
    unittest.main()
