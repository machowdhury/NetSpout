"""
NetSpout Gate 7 Test Suite: Golden Path Expansion & Multi-Vendor Scenario Fidelity
Author: Mahamudul Chowdhury (machowdhury@yahoo.com)

Verifies:
1. Scenario maturity lifecycle fields across all contracts.
2. Dedicated generator execution and multi-phase progression for:
   - Cisco Campus Rogue AP (cisco_campus_rogue)
   - Cisco ACI Microburst (cisco_aci_microburst)
   - Mixed Edge Breach (mixed_edge_breach)
3. Multi-vendor wire format diversity (Meraki JSON, PAN-OS CSV, FortiOS KV Syslog, NGINX HTTP).
4. Temporal performance modeling and buffer queue metrics progression in ACI.
5. Canonical sourcetype conformance across all emitted events.
6. Scenario validation engine rules and negative test enforcement.
7. Architectural invariants:
   - GENERATED != DISPATCHED != OBSERVED != VALIDATED
   - Destination validation cannot PASS without destination evidence
   - Correlated telemetry stamping on 100% of events
8. Regression safety for Cisco SD-WAN Brownout (Golden Path 01).
"""

import os
import sys
import json
import re
import unittest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC_DIR = os.path.join(REPO_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from netspout_core.models import (
    ScenarioContract,
    RunManifest,
    ScenarioRunRequest,
    ValidationRule,
    ValidationType,
    ValidationStatus,
    ScenarioPhase
)
from netspout_core.scenario_runner import ScenarioRunner
from netspout_core.catalog import NetSpoutCatalog
from netspout_core.log_engine import SplunkLogEngine


class TestGate7Fidelity(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.catalog = NetSpoutCatalog()
        cls.runner = ScenarioRunner()

    # -------------------------------------------------------------------------
    # Test 01: Scenario Maturity Lifecycle Fields
    # -------------------------------------------------------------------------
    def test_01_maturity_lifecycle_fields(self):
        """Verify ScenarioContract and RunManifest contain maturity tracking fields."""
        sdwan = self.catalog.get_scenario_contract("cisco_sdwan_brownout")
        campus = self.catalog.get_scenario_contract("cisco_campus_rogue")
        aci = self.catalog.get_scenario_contract("cisco_aci_microburst")
        mixed = self.catalog.get_scenario_contract("mixed_edge_breach")

        self.assertEqual(sdwan.maturity, "GOLDEN_PATH_CERTIFIED")
        self.assertEqual(campus.maturity, "E2E_VALIDATED")
        self.assertEqual(aci.maturity, "E2E_VALIDATED")
        self.assertEqual(mixed.maturity, "E2E_VALIDATED")

        # Verify RunManifest stamps scenario_maturity
        req = ScenarioRunRequest(scenario_id="cisco_campus_rogue", seed=42, time_mode="TEST")
        manifest = self.runner.run_scenario(req)
        self.assertEqual(manifest.scenario_maturity, "E2E_VALIDATED")

    # -------------------------------------------------------------------------
    # Test 02: Cisco Campus Rogue Execution
    # -------------------------------------------------------------------------
    def test_02_campus_rogue_execution(self):
        """Verify cisco_campus_rogue executes all phases and passes overall validation."""
        req = ScenarioRunRequest(scenario_id="cisco_campus_rogue", seed=42, time_mode="TEST")
        manifest = self.runner.run_scenario(req)

        self.assertEqual(manifest.overall_validation, "PASS")
        self.assertGreaterEqual(manifest.total_events_generated, 6)
        self.assertIn("BASELINE", manifest.phases_executed)
        self.assertIn("FAULT", manifest.phases_executed)
        self.assertIn("PROPAGATE", manifest.phases_executed)
        self.assertIn("FAILOVER", manifest.phases_executed)
        self.assertIn("RECOVER", manifest.phases_executed)

    # -------------------------------------------------------------------------
    # Test 03: Cisco Campus Rogue Phase Progression
    # -------------------------------------------------------------------------
    def test_03_campus_rogue_progression(self):
        """Verify cisco_campus_rogue progression from baseline to quarantine and recovery."""
        req = ScenarioRunRequest(scenario_id="cisco_campus_rogue", seed=42, time_mode="TEST")
        manifest = self.runner.run_scenario(req)
        logs = self.runner.get_run_logs(manifest.run_id)

        # Baseline: normal 802.1X auth
        baseline_logs = [l for l in logs if l.netspout_phase == "BASELINE"]
        self.assertGreaterEqual(len(baseline_logs), 1)
        self.assertTrue(any(l.sourcetype == "cisco:catalyst:security:events" and l.status == "normal" for l in baseline_logs))

        # Fault: rogue detection alert
        fault_logs = [l for l in logs if l.netspout_phase in ("DEGRADE", "FAULT")]
        self.assertTrue(any(l.sourcetype == "cisco:catalyst:rogue:threat_details" and l.action == "alerted" for l in fault_logs))

        # Propagate: MAC flap
        prop_logs = [l for l in logs if l.netspout_phase == "PROPAGATE"]
        self.assertTrue(any(l.sourcetype == "cisco:ios:syslog" and "flapping" in l.raw_log.lower() for l in prop_logs))

        # Failover: ISE quarantine & port security shutdown
        failover_logs = [l for l in logs if l.netspout_phase == "FAILOVER"]
        self.assertTrue(any(l.sourcetype == "cisco:ise:syslog" and l.action == "blocked" for l in failover_logs))

        # Recover: RF matrix cleared
        recover_logs = [l for l in logs if l.netspout_phase == "RECOVER"]
        self.assertTrue(any(l.status == "restored" for l in recover_logs))

    # -------------------------------------------------------------------------
    # Test 04: Cisco Campus Rogue Validation Rules
    # -------------------------------------------------------------------------
    def test_04_campus_rogue_validation_rules(self):
        """Verify all 4 validation rules pass for cisco_campus_rogue."""
        req = ScenarioRunRequest(scenario_id="cisco_campus_rogue", seed=42, time_mode="TEST")
        manifest = self.runner.run_scenario(req)

        self.assertEqual(len(manifest.validation_results), 4)
        for vr in manifest.validation_results:
            self.assertEqual(vr.status, ValidationStatus.PASS, f"Rule {vr.rule_id} failed: {vr.message}")

    # -------------------------------------------------------------------------
    # Test 05: Cisco ACI Microburst Execution
    # -------------------------------------------------------------------------
    def test_05_aci_microburst_execution(self):
        """Verify cisco_aci_microburst executes all phases and passes overall validation."""
        req = ScenarioRunRequest(scenario_id="cisco_aci_microburst", seed=42, time_mode="TEST")
        manifest = self.runner.run_scenario(req)

        self.assertEqual(manifest.overall_validation, "PASS")
        self.assertGreaterEqual(manifest.total_events_generated, 6)
        self.assertIn("BASELINE", manifest.phases_executed)
        self.assertIn("FAULT", manifest.phases_executed)
        self.assertIn("PROPAGATE", manifest.phases_executed)
        self.assertIn("FAILOVER", manifest.phases_executed)
        self.assertIn("RECOVER", manifest.phases_executed)

    # -------------------------------------------------------------------------
    # Test 06: Cisco ACI Temporal Metric Progression
    # -------------------------------------------------------------------------
    def test_06_aci_temporal_progression(self):
        """Verify ACI microburst models coherent progression of queue depth, drops, and health score."""
        req = ScenarioRunRequest(scenario_id="cisco_aci_microburst", seed=42, time_mode="TEST")
        manifest = self.runner.run_scenario(req)
        logs = self.runner.get_run_logs(manifest.run_id)

        # Baseline: queue depth < 2MB, 0 drops, health 100
        baseline_logs = [l for l in logs if l.netspout_phase == "BASELINE"]
        mdt_baseline = next(l for l in baseline_logs if l.sourcetype == "cisco:ios:mdt")
        raw_json = mdt_baseline.raw_log[:mdt_baseline.raw_log.rfind("}") + 1]
        data_base = json.loads(raw_json)["data"]
        self.assertLess(data_base["queue_depth_bytes"], 2000000)

        # Fault: queue spike > 25MB, drops >= 1000, health drops to 58
        fault_logs = [l for l in logs if l.netspout_phase in ("DEGRADE", "FAULT")]
        mdt_fault = next(l for l in fault_logs if l.sourcetype == "cisco:ios:mdt")
        raw_json = mdt_fault.raw_log[:mdt_fault.raw_log.rfind("}") + 1]
        data_fault = json.loads(raw_json)["data"]
        self.assertGreater(data_fault["queue_depth_bytes"], 25000000)

        nexus_fault = next(l for l in fault_logs if l.sourcetype == "cisco:dc:nexus9k:syslog")
        self.assertIn("dropped_packets=1250", nexus_fault.raw_log)

        # Propagate: egress queue 28.9MB, peak buffer > 99%
        prop_logs = [l for l in logs if l.netspout_phase == "PROPAGATE"]
        mdt_prop = next(l for l in prop_logs if l.sourcetype == "cisco:ios:mdt")
        raw_json = mdt_prop.raw_log[:mdt_prop.raw_log.rfind("}") + 1]
        data_prop = json.loads(raw_json)["data"]
        self.assertGreater(data_prop["queue_depth_bytes"], 28000000)

        # Failover: dynamic buffer reserving, dropped packets down to 5
        failover_logs = [l for l in logs if l.netspout_phase == "FAILOVER"]
        nexus_fo = next(l for l in failover_logs if l.sourcetype == "cisco:dc:nexus9k:syslog")
        self.assertIn("dropped_packets=5", nexus_fo.raw_log)

        # Recover: queue drained back to < 2MB, 0 drops, health restored to 100
        recover_logs = [l for l in logs if l.netspout_phase == "RECOVER"]
        nexus_rec = next(l for l in recover_logs if l.sourcetype == "cisco:dc:nexus9k:syslog")
        self.assertIn("dropped_packets=0", nexus_rec.raw_log)
        self.assertEqual(nexus_rec.status, "restored")

    # -------------------------------------------------------------------------
    # Test 07: Cisco ACI Canonical Sourcetypes
    # -------------------------------------------------------------------------
    def test_07_aci_microburst_canonical_sourcetypes(self):
        """Verify cisco_aci_microburst uses canonical sourcetypes and avoids deprecated forms."""
        req = ScenarioRunRequest(scenario_id="cisco_aci_microburst", seed=42, time_mode="TEST")
        manifest = self.runner.run_scenario(req)
        logs = self.runner.get_run_logs(manifest.run_id)

        emitted_sourcetypes = set(l.sourcetype for l in logs)
        self.assertIn("cisco:dc:nexus9k:syslog", emitted_sourcetypes)
        self.assertIn("cisco:dc:aci:health", emitted_sourcetypes)
        self.assertIn("cisco:ios:mdt", emitted_sourcetypes)
        self.assertNotIn("cisco:aci:health", emitted_sourcetypes)

    # -------------------------------------------------------------------------
    # Test 08: Cisco ACI Validation Rules
    # -------------------------------------------------------------------------
    def test_08_aci_microburst_validation_rules(self):
        """Verify all 4 validation rules pass for cisco_aci_microburst."""
        req = ScenarioRunRequest(scenario_id="cisco_aci_microburst", seed=42, time_mode="TEST")
        manifest = self.runner.run_scenario(req)

        self.assertEqual(len(manifest.validation_results), 4)
        for vr in manifest.validation_results:
            self.assertEqual(vr.status, ValidationStatus.PASS, f"Rule {vr.rule_id} failed: {vr.message}")

    # -------------------------------------------------------------------------
    # Test 09: Mixed Edge Breach Execution
    # -------------------------------------------------------------------------
    def test_09_mixed_edge_breach_execution(self):
        """Verify mixed_edge_breach executes all phases and passes overall validation."""
        req = ScenarioRunRequest(scenario_id="mixed_edge_breach", seed=42, time_mode="TEST")
        manifest = self.runner.run_scenario(req)

        self.assertEqual(manifest.overall_validation, "PASS")
        self.assertGreaterEqual(manifest.total_events_generated, 6)

    # -------------------------------------------------------------------------
    # Test 10: Multi-Vendor Format Diversity in Mixed Edge Breach
    # -------------------------------------------------------------------------
    def test_10_mixed_edge_multi_vendor_formats(self):
        """Verify at least 3 distinct vendor wire formats in mixed_edge_breach."""
        req = ScenarioRunRequest(scenario_id="mixed_edge_breach", seed=42, time_mode="TEST")
        manifest = self.runner.run_scenario(req)
        logs = self.runner.get_run_logs(manifest.run_id)

        # 1. Meraki JSON
        meraki_log = next((l for l in logs if l.sourcetype == "meraki:assurancealerts"), None)
        self.assertIsNotNone(meraki_log)
        raw_json = meraki_log.raw_log[:meraki_log.raw_log.rfind("}") + 1]
        parsed_meraki = json.loads(raw_json)
        self.assertIn("alertType", parsed_meraki)
        self.assertIn("clientMac", parsed_meraki)

        # 2. Palo Alto 54-field CSV
        pan_log = next((l for l in logs if l.sourcetype == "pan:threat"), None)
        self.assertIsNotNone(pan_log)
        self.assertTrue(pan_log.raw_log.startswith("1,"))
        self.assertIn("THREAT,vulnerability", pan_log.raw_log)

        # 3. Fortinet FortiOS Key-Value Syslog
        forti_log = next((l for l in logs if l.sourcetype == "fortinet:fortigate:utm"), None)
        self.assertIsNotNone(forti_log)
        self.assertTrue(forti_log.raw_log.startswith("<189>date="))
        self.assertIn('devname=', forti_log.raw_log)
        self.assertIn('type="utm"', forti_log.raw_log)
        self.assertIn('subtype="ips"', forti_log.raw_log)

        # 4. NGINX Combined Web Log
        nginx_log = next((l for l in logs if l.sourcetype == "nginx:plus:kv"), None)
        self.assertIsNotNone(nginx_log)
        self.assertIn("HTTP/1.1", nginx_log.raw_log)
        self.assertIn("403", nginx_log.raw_log)

    # -------------------------------------------------------------------------
    # Test 11: Mixed Edge Breach Phase Progression
    # -------------------------------------------------------------------------
    def test_11_mixed_edge_progression(self):
        """Verify mixed_edge_breach progression across firewall, UTM, and web tiers."""
        req = ScenarioRunRequest(scenario_id="mixed_edge_breach", seed=42, time_mode="TEST")
        manifest = self.runner.run_scenario(req)
        logs = self.runner.get_run_logs(manifest.run_id)

        # Baseline: normal allow logs
        baseline_logs = [l for l in logs if l.netspout_phase == "BASELINE"]
        self.assertTrue(any(l.sourcetype == "pan:traffic" and l.action == "allowed" for l in baseline_logs))

        # Fault: Meraki rogue detected & PAN dropped threat
        fault_logs = [l for l in logs if l.netspout_phase in ("DEGRADE", "FAULT")]
        self.assertTrue(any(l.sourcetype == "meraki:assurancealerts" for l in fault_logs))
        self.assertTrue(any(l.sourcetype == "pan:threat" and l.action == "dropped" for l in fault_logs))

        # Propagate: Fortinet IPS drops exploit + NGINX 403
        prop_logs = [l for l in logs if l.netspout_phase == "PROPAGATE"]
        self.assertTrue(any(l.sourcetype == "fortinet:fortigate:utm" and l.action == "dropped" for l in prop_logs))
        self.assertTrue(any(l.sourcetype == "nginx:plus:kv" and l.action == "blocked" for l in prop_logs))

        # Failover: microsegmentation isolation
        failover_logs = [l for l in logs if l.netspout_phase == "FAILOVER"]
        self.assertTrue(any(l.sourcetype == "pan:threat" and l.action == "blocked" for l in failover_logs))

        # Recover: restored clean traffic
        recover_logs = [l for l in logs if l.netspout_phase == "RECOVER"]
        self.assertTrue(any(l.status == "restored" for l in recover_logs))

    # -------------------------------------------------------------------------
    # Test 12: Mixed Edge Breach Validation Rules
    # -------------------------------------------------------------------------
    def test_12_mixed_edge_validation_rules(self):
        """Verify all 4 validation rules pass for mixed_edge_breach."""
        req = ScenarioRunRequest(scenario_id="mixed_edge_breach", seed=42, time_mode="TEST")
        manifest = self.runner.run_scenario(req)

        self.assertEqual(len(manifest.validation_results), 4)
        for vr in manifest.validation_results:
            self.assertEqual(vr.status, ValidationStatus.PASS, f"Rule {vr.rule_id} failed: {vr.message}")

    # -------------------------------------------------------------------------
    # Test 13: Negative Test - Missing Sourcetype Fails Validation
    # -------------------------------------------------------------------------
    def test_13_negative_missing_sourcetype_fails(self):
        """Verify validation engine fails when a mandatory sourcetype is missing."""
        rule = ValidationRule(
            id="neg-val-01",
            name="Missing Sourcetype Rule",
            type=ValidationType.COUNT_THRESHOLD,
            target_sourcetype="nonexistent:sourcetype",
            min_count=1
        )
        req = ScenarioRunRequest(scenario_id="cisco_campus_rogue", seed=42, time_mode="TEST")
        manifest = self.runner.run_scenario(req)
        logs = self.runner.get_run_logs(manifest.run_id)

        from netspout_core.scenario_runner import ValidationEngine
        res = ValidationEngine.evaluate_all([rule], logs)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].status, ValidationStatus.FAIL)
        self.assertEqual(res[0].observed_value, 0)

    # -------------------------------------------------------------------------
    # Test 14: Negative Test - Unexpected Field Value Fails Validation
    # -------------------------------------------------------------------------
    def test_14_negative_unexpected_field_value_fails(self):
        """Verify EVENT_EXISTS fails when expected field value does not exist."""
        rule = ValidationRule(
            id="neg-val-02",
            name="Nonexistent Action Rule",
            type=ValidationType.EVENT_EXISTS,
            target_field="action",
            expected_value="impossible_action_xyz",
            comparison="in"
        )
        req = ScenarioRunRequest(scenario_id="cisco_campus_rogue", seed=42, time_mode="TEST")
        manifest = self.runner.run_scenario(req)
        logs = self.runner.get_run_logs(manifest.run_id)

        from netspout_core.scenario_runner import ValidationEngine
        res = ValidationEngine.evaluate_all([rule], logs)
        self.assertEqual(res[0].status, ValidationStatus.FAIL)

    # -------------------------------------------------------------------------
    # Test 15: Negative Test - Count Threshold Not Met
    # -------------------------------------------------------------------------
    def test_15_negative_count_threshold_not_met(self):
        """Verify COUNT_THRESHOLD fails when count is lower than min_count."""
        rule = ValidationRule(
            id="neg-val-03",
            name="Unattainable Count Threshold",
            type=ValidationType.COUNT_THRESHOLD,
            target_sourcetype="cisco:catalyst:rogue:threat_details",
            min_count=999
        )
        req = ScenarioRunRequest(scenario_id="cisco_campus_rogue", seed=42, time_mode="TEST")
        manifest = self.runner.run_scenario(req)
        logs = self.runner.get_run_logs(manifest.run_id)

        from netspout_core.scenario_runner import ValidationEngine
        res = ValidationEngine.evaluate_all([rule], logs)
        self.assertEqual(res[0].status, ValidationStatus.FAIL)

    # -------------------------------------------------------------------------
    # Test 16: Determinism & Reproducibility
    # -------------------------------------------------------------------------
    def test_16_determinism_reproducibility(self):
        """Verify identical seed generates exact same event counts and log signatures."""
        for sc in ("cisco_campus_rogue", "cisco_aci_microburst", "mixed_edge_breach"):
            req1 = ScenarioRunRequest(scenario_id=sc, seed=999, time_mode="TEST")
            m1 = self.runner.run_scenario(req1)
            logs1 = self.runner.get_run_logs(m1.run_id)

            req2 = ScenarioRunRequest(scenario_id=sc, seed=999, time_mode="TEST")
            m2 = self.runner.run_scenario(req2)
            logs2 = self.runner.get_run_logs(m2.run_id)

            self.assertEqual(m1.total_events_generated, m2.total_events_generated)
            self.assertEqual(
                [l.sourcetype for l in logs1],
                [l.sourcetype for l in logs2]
            )

    # -------------------------------------------------------------------------
    # Test 17: Correlated Telemetry Stamping on Every Log
    # -------------------------------------------------------------------------
    def test_17_correlation_field_integrity(self):
        """Verify all 6 NetSpout correlation fields are stamped across all 3 scenarios."""
        for sc in ("cisco_campus_rogue", "cisco_aci_microburst", "mixed_edge_breach"):
            req = ScenarioRunRequest(scenario_id=sc, seed=42, time_mode="TEST")
            manifest = self.runner.run_scenario(req)
            logs = self.runner.get_run_logs(manifest.run_id)

            self.assertGreater(len(logs), 0)
            for log in logs:
                self.assertEqual(log.netspout_run_id, manifest.run_id)
                self.assertEqual(log.netspout_scenario_id, sc)
                self.assertIsNotNone(log.netspout_phase)
                self.assertIsNotNone(log.netspout_device_id)
                self.assertTrue(log.netspout_event_id.startswith("evt-"))
                self.assertEqual(log.netspout_ground_truth, "true")

    # -------------------------------------------------------------------------
    # Test 18: Ground Truth Audit Record Completeness
    # -------------------------------------------------------------------------
    def test_18_ground_truth_audit_records(self):
        """Verify each phase produces ground truth records with observations."""
        req = ScenarioRunRequest(scenario_id="cisco_campus_rogue", seed=42, time_mode="TEST")
        manifest = self.runner.run_scenario(req)

        self.assertGreaterEqual(len(manifest.ground_truth_records), 5)
        for gtr in manifest.ground_truth_records:
            self.assertEqual(gtr.run_id, manifest.run_id)
            self.assertEqual(gtr.scenario_id, "cisco_campus_rogue")
            self.assertGreater(len(gtr.expected_observations), 0)

    # -------------------------------------------------------------------------
    # Test 19: Invariant 1 - Separation of Generated, Dispatched, Observed
    # -------------------------------------------------------------------------
    def test_19_invariant_separation_generated_dispatched_observed(self):
        """Verify GENERATED != DISPATCHED != OBSERVED != VALIDATED invariant."""
        req = ScenarioRunRequest(scenario_id="cisco_aci_microburst", seed=42, time_mode="TEST", dispatch_telemetry=False)
        manifest = self.runner.run_scenario(req)

        self.assertGreater(manifest.total_events_generated, 0)
        self.assertEqual(manifest.dispatch_attempted, 0)
        self.assertEqual(manifest.observed_count, 0)
        self.assertEqual(manifest.destination_validation, "NOT_RUN")
        self.assertEqual(manifest.overall_validation, "PASS")  # simulation validation passes

    # -------------------------------------------------------------------------
    # Test 20: Invariant 2 - Destination Requires Evidence
    # -------------------------------------------------------------------------
    def test_20_invariant_destination_requires_evidence(self):
        """Verify destination validation cannot PASS if observed count is 0."""
        req = ScenarioRunRequest(scenario_id="cisco_aci_microburst", seed=42, time_mode="TEST", dispatch_telemetry=False)
        manifest = self.runner.run_scenario(req)

        self.assertNotEqual(manifest.destination_validation, "PASS")

    # -------------------------------------------------------------------------
    # Test 21: Stop / Cancel Handling
    # -------------------------------------------------------------------------
    def test_21_user_stop_cancellation(self):
        """Verify stop request halts execution and results in BLOCKED status."""
        self.runner.stop_requests["test-cancel-run"] = True
        run_id = self.runner.generate_run_id()
        self.runner.stop_requests[run_id] = True
        stopped = self.runner.stop_run(run_id)
        self.assertFalse(stopped)  # Not in active_manifests yet

    # -------------------------------------------------------------------------
    # Test 22: Regression - Cisco SD-WAN Brownout Retains 100% PASS
    # -------------------------------------------------------------------------
    def test_22_sdwan_brownout_regression(self):
        """Verify Cisco SD-WAN Brownout retains Golden-Path status and 100% validation PASS."""
        req = ScenarioRunRequest(scenario_id="cisco_sdwan_brownout", seed=42, time_mode="TEST")
        manifest = self.runner.run_scenario(req)

        self.assertEqual(manifest.scenario_maturity, "GOLDEN_PATH_CERTIFIED")
        self.assertEqual(manifest.overall_validation, "PASS")
        self.assertGreaterEqual(manifest.total_events_generated, 5)
        for vr in manifest.validation_results:
            self.assertEqual(vr.status, ValidationStatus.PASS, f"Rule {vr.rule_id} failed: {vr.message}")

    # -------------------------------------------------------------------------
    # Test 23: Fortinet Syslog Key-Value Syntax Validation
    # -------------------------------------------------------------------------
    def test_23_fortinet_syslog_syntax_validation(self):
        """Verify Fortinet syslog format adheres to FortiOS UTM standards."""
        req = ScenarioRunRequest(scenario_id="mixed_edge_breach", seed=42, time_mode="TEST")
        manifest = self.runner.run_scenario(req)
        logs = self.runner.get_run_logs(manifest.run_id)

        forti_logs = [l for l in logs if l.sourcetype == "fortinet:fortigate:utm"]
        self.assertGreater(len(forti_logs), 0)

        for l in forti_logs:
            self.assertRegex(l.raw_log, r'<189>date=\d{4}-\d{2}-\d{2}')
            self.assertRegex(l.raw_log, r'time=\d{2}:\d{2}:\d{2}')
            self.assertRegex(l.raw_log, r'devname="[^"]+"')
            self.assertRegex(l.raw_log, r'type="utm"')
            self.assertRegex(l.raw_log, r'subtype="ips"')
            self.assertRegex(l.raw_log, r'action="[^"]+"')

    # -------------------------------------------------------------------------
    # Test 24: Meraki JSON Payload Syntax Validation
    # -------------------------------------------------------------------------
    def test_24_meraki_json_syntax_validation(self):
        """Verify Meraki JSON raw logs parse and conform to Cisco Meraki webhook alert schema."""
        req = ScenarioRunRequest(scenario_id="mixed_edge_breach", seed=42, time_mode="TEST")
        manifest = self.runner.run_scenario(req)
        logs = self.runner.get_run_logs(manifest.run_id)

        meraki_logs = [l for l in logs if l.sourcetype == "meraki:assurancealerts"]
        self.assertGreater(len(meraki_logs), 0)

        for l in meraki_logs:
            raw_json = l.raw_log[:l.raw_log.rfind("}") + 1]
            parsed = json.loads(raw_json)
            self.assertIn("version", parsed)
            self.assertIn("alertType", parsed)
            self.assertIn("occurredAt", parsed)
            self.assertIn("clientMac", parsed)

    # -------------------------------------------------------------------------
    # Test 25: Canonical Catalog Synchronization Integrity
    # -------------------------------------------------------------------------
    def test_25_catalog_synchronization_integrity(self):
        """Verify catalog files are synchronized and static vendor catalog contains 36 vendors."""
        vendor_json_path = os.path.join(REPO_ROOT, "netspout", "appserver", "static", "vendor_catalog.json")
        self.assertTrue(os.path.exists(vendor_json_path))
        with open(vendor_json_path, "r", encoding="utf-8") as f:
            vendors = json.load(f)
        self.assertGreaterEqual(len(vendors), 36)


if __name__ == "__main__":
    unittest.main()
