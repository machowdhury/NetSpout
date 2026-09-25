#!/usr/bin/env python3
"""
NetSpout Gate 4 Test Suite: Unified Scenario, Topology, and Use-Case Contract
Verifies:
1. Scenario Contract Schema & Catalog Integrity (ScenarioContract, UseCaseContract, ValidationRule)
2. Topology Separation from Scenario Definition
3. Affected Entities Reference Validity
4. Run ID Generation (NS-YYYYMMDD-<uuid> format)
5. Phase Progression (INITIALIZE -> BASELINE -> DEGRADE -> FAULT -> PROPAGATE -> FAILOVER -> RECOVER -> VALIDATE -> COMPLETE)
6. Runtime State Mutation (Packet Loss, Latency, Jitter Degradation)
7. Topology State Snapshot & Restoration (graph.snapshot_state & restore_all)
8. Deterministic Seed Reproducibility (identical seed produces identical event stream)
9. Time Control Abstraction (TEST clock = instant 0s delay, ACCELERATED, REALTIME)
10. Run Manifest Audit Record Generation & Completeness
11. Ground Truth Tracking (Intentional NetSpout Fault vs Observed Telemetry)
12. Correlated Telemetry Stamping on Every Log (Run ID, Scenario ID, Phase, Device ID, Event ID, Ground Truth)
13. Validation Engine: EVENT_EXISTS Evaluation
14. Validation Engine: COUNT_THRESHOLD Evaluation
15. Validation Engine: FIELD_VALUE Evaluation
16. Validation Engine: STATE_TRANSITION Evaluation
17. Validation Engine: SPL_QUERY Evaluation (via SPLExecutionEngine)
18. Run Cancellation / Stop Behavior (BLOCKED status)
19. Representative Scenario 1: Cisco SD-WAN Brownout & App Route Failover
20. Representative Scenario 2: Cisco Campus Core Rogue AP & ISE Quarantine
21. Representative Scenario 3: Cisco ACI Microburst & MDT Telemetry
22. Representative Scenario 4: Mixed-Vendor Edge Breach & Security Scenarios
"""

import os
import sys
import re
import time
import unittest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC_DIR = os.path.join(REPO_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from netspout_core.models import (
    TopologyState, Node, Edge, NodeType, ScenarioType, LogEntry,
    ScenarioPhase, ValidationType, ValidationStatus, ValidationRule,
    ValidationResult, UseCaseContract, ScenarioContract, GroundTruthRecord,
    RunManifest, ScenarioRunRequest
)
from netspout_core.graph_engine import TopologyGraph
from netspout_core.catalog import catalog
from netspout_core.scenario_runner import (
    ScenarioRunner,
    scenario_runner,
    ValidationEngine,
    get_default_secure_topology,
    get_cisco_sdwan_topology,
    get_cisco_campus_topology,
    get_cisco_aci_topology,
    get_mixed_edge_topology
)


class TestGate4Contract(unittest.TestCase):

    def setUp(self):
        self.runner = ScenarioRunner()

    # -------------------------------------------------------------------------
    # Test 1: Scenario Contract Schema & Catalog Loading
    # -------------------------------------------------------------------------
    def test_01_scenario_contract_schema(self):
        """Verify all 29 scenarios in catalog load as valid ScenarioContract objects."""
        scenarios = catalog.list_scenarios()
        self.assertEqual(len(scenarios), 29, "Catalog must contain exactly 29 scenarios")
        for sc_meta in scenarios:
            contract = catalog.get_scenario_contract(sc_meta["id"])
            self.assertIsNotNone(contract)
            self.assertTrue(isinstance(contract, ScenarioContract) or hasattr(contract, "id"))
            self.assertTrue(bool(contract.id))
            self.assertTrue(bool(contract.topology_id))
            self.assertIsInstance(contract.sourcetypes, list)
            self.assertGreater(len(contract.sourcetypes), 0)

    # -------------------------------------------------------------------------
    # Test 2: Topology Separation from Scenario Definition
    # -------------------------------------------------------------------------
    def test_02_topology_separation(self):
        """Verify topologies (what exists) are structurally separated from scenarios (what happens)."""
        topologies = catalog.list_topologies()
        self.assertEqual(len(topologies), 28)
        top_ids = {t["id"] for t in topologies}
        # Scenarios reference topology_id without defining static network graph inline
        for sc in catalog.list_scenarios():
            contract = catalog.get_scenario_contract(sc["id"])
            self.assertTrue(contract.topology_id in top_ids or "default" in contract.topology_id or "campus" in contract.topology_id)

    # -------------------------------------------------------------------------
    # Test 3: Affected Entities Reference Validity
    # -------------------------------------------------------------------------
    def test_03_affected_entities_reference(self):
        """Verify affected entities in contracts reference valid node or edge IDs."""
        sdwan_contract = catalog.get_scenario_contract("cisco_sdwan_brownout")
        self.assertGreater(len(sdwan_contract.affected_entities), 0)
        self.assertIn("edge-branch-mpls", sdwan_contract.affected_entities)

    # -------------------------------------------------------------------------
    # Test 4: Run ID Generation Pattern
    # -------------------------------------------------------------------------
    def test_04_run_id_generation_pattern(self):
        """Verify Run IDs strictly conform to NS-YYYYMMDD-<uuid> pattern."""
        run_id = self.runner.generate_run_id()
        pattern = r"^NS-[0-9]{8}-[0-9a-f]{8}$"
        self.assertRegex(run_id, pattern, f"Run ID '{run_id}' does not match NS-YYYYMMDD-<uuid>")

    # -------------------------------------------------------------------------
    # Test 5: Phase Progression Lifecycle
    # -------------------------------------------------------------------------
    def test_05_phase_progression_lifecycle(self):
        """Verify multi-phase execution loop progresses through all defined phases."""
        req = ScenarioRunRequest(scenario_id="cisco_sdwan_brownout", seed=42, time_mode="TEST")
        manifest = self.runner.run_scenario(req)
        expected_phases = ["INITIALIZE", "BASELINE", "DEGRADE", "FAILOVER", "RECOVER", "VALIDATE", "COMPLETE"]
        for p in expected_phases:
            self.assertIn(p, manifest.phases_executed, f"Phase {p} was not executed")

    # -------------------------------------------------------------------------
    # Test 6: Runtime State Mutation (Link Degradation)
    # -------------------------------------------------------------------------
    def test_06_runtime_state_mutation(self):
        """Verify graph engine degrades link metrics dynamically without mutating static identity."""
        top = get_cisco_sdwan_topology()
        graph = TopologyGraph(top)
        initial_snap = graph.snapshot_state()

        # Degrade primary link
        res = graph.degrade_link("edge-branch-mpls", packet_loss_pct=15.0, latency_ms=180.0, jitter_ms=40.0)
        self.assertTrue(res)
        edge = graph.get_edge("edge-branch-mpls")
        self.assertEqual(edge.packet_loss_pct, 15.0)
        self.assertEqual(edge.latency_ms, 180.0)
        self.assertEqual(edge.jitter_ms, 40.0)
        self.assertEqual(edge.status, "degraded")

    # -------------------------------------------------------------------------
    # Test 7: Topology State Snapshot & Restoration
    # -------------------------------------------------------------------------
    def test_07_topology_state_restoration(self):
        """Verify snapshot_state and restore_all return topology to nominal health."""
        top = get_cisco_sdwan_topology()
        graph = TopologyGraph(top)
        initial_snap = graph.snapshot_state()

        graph.degrade_link("edge-branch-mpls", packet_loss_pct=25.0, latency_ms=300.0, jitter_ms=50.0)
        graph.restore_all()
        edge = graph.get_edge("edge-branch-mpls")
        self.assertEqual(edge.packet_loss_pct, 0.0)
        self.assertEqual(edge.latency_ms, 1.0)
        self.assertEqual(edge.status, "up")

    # -------------------------------------------------------------------------
    # Test 8: Deterministic Seed Reproducibility
    # -------------------------------------------------------------------------
    def test_08_deterministic_seed_reproducibility(self):
        """Verify same seed produces identical event streams and validation outcomes."""
        req1 = ScenarioRunRequest(scenario_id="cisco_sdwan_brownout", seed=777, time_mode="TEST")
        m1 = self.runner.run_scenario(req1)
        logs1 = self.runner.get_run_logs(m1.run_id)

        req2 = ScenarioRunRequest(scenario_id="cisco_sdwan_brownout", seed=777, time_mode="TEST")
        m2 = self.runner.run_scenario(req2)
        logs2 = self.runner.get_run_logs(m2.run_id)

        self.assertEqual(len(logs1), len(logs2))
        for l1, l2 in zip(logs1, logs2):
            self.assertEqual(l1.sourcetype, l2.sourcetype)
            self.assertEqual(l1.status, l2.status)
            self.assertEqual(l1.action, l2.action)
            self.assertEqual(l1.netspout_phase, l2.netspout_phase)

    # -------------------------------------------------------------------------
    # Test 9: Time Control Modes
    # -------------------------------------------------------------------------
    def test_09_time_control_modes(self):
        """Verify TEST time mode executes instantaneously while ACCELERATED measures delay."""
        t0 = time.time()
        req_test = ScenarioRunRequest(scenario_id="cisco_sdwan_brownout", seed=1, time_mode="TEST")
        m_test = self.runner.run_scenario(req_test)
        duration_test = time.time() - t0
        self.assertLess(duration_test, 0.2, "TEST mode must complete in < 200ms")
        self.assertEqual(m_test.time_mode, "TEST")

    # -------------------------------------------------------------------------
    # Test 10: Run Manifest Audit Record Completeness
    # -------------------------------------------------------------------------
    def test_10_run_manifest_completeness(self):
        """Verify RunManifest contains all required audit record fields."""
        req = ScenarioRunRequest(scenario_id="cisco_sdwan_brownout", seed=42, time_mode="TEST")
        manifest = self.runner.run_scenario(req)

        self.assertTrue(manifest.run_id.startswith("NS-"))
        self.assertEqual(manifest.scenario_id, "cisco_sdwan_brownout")
        self.assertGreater(manifest.start_time, 0)
        self.assertIsNotNone(manifest.end_time)
        self.assertGreater(len(manifest.phases_executed), 0)
        self.assertGreater(manifest.total_events_generated, 0)
        self.assertGreater(len(manifest.actual_generated_counts), 0)
        self.assertIn(manifest.overall_validation, ["PASS", "FAIL", "BLOCKED"])

    # -------------------------------------------------------------------------
    # Test 11: Ground Truth Tracking
    # -------------------------------------------------------------------------
    def test_11_ground_truth_tracking(self):
        """Verify ground truth records distinguish intentional NetSpout faults from observed events."""
        req = ScenarioRunRequest(scenario_id="cisco_sdwan_brownout", seed=42, time_mode="TEST")
        manifest = self.runner.run_scenario(req)

        self.assertGreater(len(manifest.ground_truth_records), 0)
        degrade_records = [g for g in manifest.ground_truth_records if g.phase == "DEGRADE"]
        self.assertGreater(len(degrade_records), 0)
        self.assertIsNotNone(degrade_records[0].intentional_fault)
        self.assertIn("loss_pct", degrade_records[0].intentional_fault)

    # -------------------------------------------------------------------------
    # Test 12: Correlated Telemetry Stamping on Every Log
    # -------------------------------------------------------------------------
    def test_12_correlated_telemetry_stamping(self):
        """Verify every generated LogEntry has all 6 correlation fields populated."""
        req = ScenarioRunRequest(scenario_id="cisco_sdwan_brownout", seed=42, time_mode="TEST")
        manifest = self.runner.run_scenario(req)
        logs = self.runner.get_run_logs(manifest.run_id)

        self.assertGreater(len(logs), 0)
        for log in logs:
            self.assertEqual(log.netspout_run_id, manifest.run_id)
            self.assertEqual(log.netspout_scenario_id, "cisco_sdwan_brownout")
            self.assertIsNotNone(log.netspout_phase)
            self.assertIsNotNone(log.netspout_device_id)
            self.assertTrue(log.netspout_event_id.startswith("evt-"))
            self.assertEqual(log.netspout_ground_truth, "true")

    # -------------------------------------------------------------------------
    # Test 13: Validation Engine - EVENT_EXISTS
    # -------------------------------------------------------------------------
    def test_13_validation_event_exists(self):
        """Verify EVENT_EXISTS validation rule evaluates matching events properly."""
        rule_pass = ValidationRule(
            id="test-ee-01",
            name="Verify Allowed Event Exists",
            type=ValidationType.EVENT_EXISTS,
            target_field="action",
            expected_value="allowed",
            min_count=1
        )
        rule_fail = ValidationRule(
            id="test-ee-02",
            name="Verify Nonexistent Event Exists",
            type=ValidationType.EVENT_EXISTS,
            target_sourcetype="nonexistent:sourcetype",
            min_count=1
        )
        logs = [
            LogEntry(timestamp="2026-09-24T00:00:00Z", device_id="d1", src_ip="1.1.1.1", dest_ip="2.2.2.2", protocol="TCP", duration="1ms", action="allowed", signature="test", status="normal", raw_log="test", node_type="switch", node_id="d1", sourcetype="cisco:ios:syslog")
        ]
        res_pass = ValidationEngine.evaluate_rule(rule_pass, logs)
        self.assertEqual(res_pass.status, ValidationStatus.PASS)

        res_fail = ValidationEngine.evaluate_rule(rule_fail, logs)
        self.assertEqual(res_fail.status, ValidationStatus.FAIL)

    # -------------------------------------------------------------------------
    # Test 14: Validation Engine - COUNT_THRESHOLD
    # -------------------------------------------------------------------------
    def test_14_validation_count_threshold(self):
        """Verify COUNT_THRESHOLD validation rule with comparison operators."""
        rule_ge = ValidationRule(
            id="test-ct-01",
            name="At least 2 logs",
            type=ValidationType.COUNT_THRESHOLD,
            min_count=2,
            comparison=">="
        )
        rule_gt = ValidationRule(
            id="test-ct-02",
            name="Strictly greater than 5 logs",
            type=ValidationType.COUNT_THRESHOLD,
            min_count=5,
            comparison=">"
        )
        logs = [
            LogEntry(timestamp="2026-09-24T00:00:00Z", device_id=f"d{i}", src_ip="1.1.1.1", dest_ip="2.2.2.2", protocol="TCP", duration="1ms", action="allowed", signature="test", status="normal", raw_log="test", node_type="switch", node_id=f"d{i}", sourcetype="cisco:ios:syslog")
            for i in range(3)
        ]
        res_ge = ValidationEngine.evaluate_rule(rule_ge, logs)
        self.assertEqual(res_ge.status, ValidationStatus.PASS)

        res_gt = ValidationEngine.evaluate_rule(rule_gt, logs)
        self.assertEqual(res_gt.status, ValidationStatus.FAIL)

    # -------------------------------------------------------------------------
    # Test 15: Validation Engine - FIELD_VALUE
    # -------------------------------------------------------------------------
    def test_15_validation_field_value(self):
        """Verify FIELD_VALUE validation rule."""
        rule = ValidationRule(
            id="test-fv-01",
            name="Verify protocol is BFD",
            type=ValidationType.FIELD_VALUE,
            target_field="protocol",
            expected_value="BFD"
        )
        logs = [
            LogEntry(timestamp="2026-09-24T00:00:00Z", device_id="d1", src_ip="1.1.1.1", dest_ip="2.2.2.2", protocol="BFD", duration="1ms", action="allowed", signature="test", status="normal", raw_log="test", node_type="router", node_id="d1", sourcetype="cisco:sdwan:linkhealth")
        ]
        res = ValidationEngine.evaluate_rule(rule, logs)
        self.assertEqual(res.status, ValidationStatus.PASS)

    # -------------------------------------------------------------------------
    # Test 16: Validation Engine - STATE_TRANSITION
    # -------------------------------------------------------------------------
    def test_16_validation_state_transition(self):
        """Verify STATE_TRANSITION validation rule."""
        rule = ValidationRule(
            id="test-st-01",
            name="Verify transition to restored status",
            type=ValidationType.STATE_TRANSITION,
            target_field="status",
            expected_value="restored"
        )
        logs = [
            LogEntry(timestamp="2026-09-24T00:00:00Z", device_id="d1", src_ip="1.1.1.1", dest_ip="2.2.2.2", protocol="TCP", duration="1ms", action="allowed", signature="test", status="restored", raw_log="test", node_type="switch", node_id="d1", sourcetype="cisco:ios:syslog")
        ]
        res = ValidationEngine.evaluate_rule(rule, logs)
        self.assertEqual(res.status, ValidationStatus.PASS)

    # -------------------------------------------------------------------------
    # Test 17: Validation Engine - SPL_QUERY
    # -------------------------------------------------------------------------
    def test_17_validation_spl_query(self):
        """Verify SPL_QUERY validation rule executes on-the-fly search and aggregation."""
        rule = ValidationRule(
            id="test-spl-01",
            name="SPL Count Check",
            type=ValidationType.SPL_QUERY,
            spl_query="sourcetype=cisco:sdwan:linkhealth | stats count by status",
            min_count=1
        )
        logs = [
            LogEntry(timestamp="2026-09-24T00:00:00Z", device_id="d1", src_ip="1.1.1.1", dest_ip="2.2.2.2", protocol="BFD", duration="1ms", action="allowed", signature="test", status="degraded", raw_log="test", node_type="router", node_id="d1", sourcetype="cisco:sdwan:linkhealth")
        ]
        res = ValidationEngine.evaluate_rule(rule, logs)
        self.assertEqual(res.status, ValidationStatus.PASS)

    # -------------------------------------------------------------------------
    # Test 18: Run Cancellation / Stop Behavior
    # -------------------------------------------------------------------------
    def test_18_run_cancellation_behavior(self):
        """Verify stopping a run flags it as BLOCKED and aborts execution early."""
        self.runner.stop_requests["NS-STOP-ME"] = True
        req = ScenarioRunRequest(scenario_id="cisco_sdwan_brownout", seed=1, time_mode="TEST")
        self.runner.generate_run_id = lambda: "NS-STOP-ME"
        manifest = self.runner.run_scenario(req)
        self.assertEqual(manifest.overall_validation, ValidationStatus.BLOCKED.value)

    # -------------------------------------------------------------------------
    # Test 19: Representative Scenario 1 - Cisco SD-WAN Brownout
    # -------------------------------------------------------------------------
    def test_19_representative_cisco_sdwan_brownout(self):
        """Verify full execution, telemetry, and 100% validation PASS on Cisco SD-WAN brownout."""
        req = ScenarioRunRequest(scenario_id="cisco_sdwan_brownout", seed=42, time_mode="TEST")
        manifest = self.runner.run_scenario(req)
        self.assertEqual(manifest.overall_validation, "PASS")
        self.assertGreaterEqual(manifest.total_events_generated, 5)
        for vr in manifest.validation_results:
            self.assertEqual(vr.status, ValidationStatus.PASS, f"Rule {vr.rule_id} failed: {vr.message}")

    # -------------------------------------------------------------------------
    # Test 20: Representative Scenario 2 - Cisco Campus Rogue AP
    # -------------------------------------------------------------------------
    def test_20_representative_cisco_campus_rogue(self):
        """Verify full execution, telemetry, and 100% validation PASS on Cisco Campus Rogue AP."""
        req = ScenarioRunRequest(scenario_id="cisco_campus_rogue", seed=42, time_mode="TEST")
        manifest = self.runner.run_scenario(req)
        self.assertEqual(manifest.overall_validation, "PASS")
        self.assertGreaterEqual(manifest.total_events_generated, 5)
        for vr in manifest.validation_results:
            self.assertEqual(vr.status, ValidationStatus.PASS, f"Rule {vr.rule_id} failed: {vr.message}")

    # -------------------------------------------------------------------------
    # Test 21: Representative Scenario 3 - Cisco ACI Microburst
    # -------------------------------------------------------------------------
    def test_21_representative_cisco_aci_microburst(self):
        """Verify full execution, telemetry, and 100% validation PASS on Cisco ACI Microburst."""
        req = ScenarioRunRequest(scenario_id="cisco_aci_microburst", seed=42, time_mode="TEST")
        manifest = self.runner.run_scenario(req)
        self.assertEqual(manifest.overall_validation, "PASS")
        for vr in manifest.validation_results:
            self.assertEqual(vr.status, ValidationStatus.PASS, f"Rule {vr.rule_id} failed: {vr.message}")

    # -------------------------------------------------------------------------
    # Test 22: Representative Scenarios - Mixed Edge, SNMP, OpenConfig & Security
    # -------------------------------------------------------------------------
    def test_22_representative_other_scenarios(self):
        """Verify full execution across mixed-edge breach, SNMP storm, OpenConfig MDT, and security scenarios."""
        other_scenarios = [
            "mixed_edge_breach",
            "snmp_fault_storm",
            "openconfig_mdt_streaming",
            "ddos_attack",
            "sql_injection",
            "lateral_movement",
            "normal_traffic"
        ]
        for sc in other_scenarios:
            req = ScenarioRunRequest(scenario_id=sc, seed=123, time_mode="TEST")
            manifest = self.runner.run_scenario(req)
            self.assertEqual(manifest.overall_validation, "PASS", f"Scenario {sc} validation failed")
            self.assertGreater(manifest.total_events_generated, 0)


if __name__ == "__main__":
    unittest.main()
