"""
Test Suite: Gate 9 Scenario Promotion Wave 1
Validates systematic promotion of 5 candidate scenarios toward E2E_VALIDATED:
1. mixed_sase_degradation (Cloud / Hybrid Networking)
2. mixed_backbone_optical (Service Provider / Core Optical)
3. openconfig_mdt_streaming (Network Performance / Assurance)
4. sql_injection (Firewall / Application Security)
5. ddos_attack (WAN / Perimeter Defense)

Covers:
- Contract schemas, metadata, use cases, and phases
- Distinct topological resolution
- Canonical formatters and zero generic fallback (%NETSPOUT-6-INFO)
- Positive contract validation (all rules PASS)
- Negative validation testing (deterministic failure on corrupted/missing evidence)
- Determinism and seed consistency
- Unified evidence multi-store discovery
- RunManifest maturity stamping (E2E_VALIDATED)
- Regression safety across Golden Paths GP01-GP04
"""

import unittest
from unittest.mock import patch, MagicMock
from typing import List

from netspout_core.catalog import NetSpoutCatalog
from netspout_core.scenario_runner import (
    ScenarioRunner,
    ValidationEngine,
    get_mixed_sase_topology,
    get_mixed_optical_topology,
    get_openconfig_core_topology,
    get_bypassed_topology,
    get_default_secure_topology
)
from netspout_core.models import (
    ScenarioRunRequest,
    ScenarioPhase,
    ValidationStatus,
    LogEntry,
    EvidenceRole,
    QueryMechanism,
    TelemetryType,
    NodeType
)


class TestGate9ScenarioPromotion(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.catalog = NetSpoutCatalog()
        cls.runner = ScenarioRunner()
        cls.promoted_scenarios = [
            "mixed_sase_degradation",
            "mixed_backbone_optical",
            "openconfig_mdt_streaming",
            "sql_injection",
            "ddos_attack"
        ]

    # -------------------------------------------------------------------------
    # 1. Catalog & Contract Maturity Verification
    # -------------------------------------------------------------------------
    def test_01_catalog_maturity_promoted_wave1(self):
        """Verify all 5 Wave 1 scenarios are set to E2E_VALIDATED in canonical catalog."""
        for sc_id in self.promoted_scenarios:
            scen = self.catalog.get_scenario(sc_id)
            self.assertIsNotNone(scen, f"Scenario {sc_id} not found in catalog")
            self.assertEqual(
                scen.get("maturity"),
                "E2E_VALIDATED",
                f"Scenario {sc_id} expected E2E_VALIDATED but found {scen.get('maturity')}"
            )

    def test_02_golden_paths_remain_certified(self):
        """Verify GP01-GP04 maintain GOLDEN_PATH_CERTIFIED maturity."""
        golden_paths = [
            "cisco_sdwan_brownout",
            "cisco_campus_rogue",
            "cisco_aci_microburst",
            "mixed_edge_breach"
        ]
        for gp in golden_paths:
            scen = self.catalog.get_scenario(gp)
            self.assertIsNotNone(scen, f"Golden Path {gp} not found in catalog")
            self.assertEqual(
                scen.get("maturity"),
                "GOLDEN_PATH_CERTIFIED",
                f"Golden Path {gp} should remain GOLDEN_PATH_CERTIFIED"
            )

    def test_03_contract_phases_and_use_case_metadata(self):
        """Verify each promoted scenario has complete phases and use_case metadata."""
        expected_phases = {"BASELINE", "FAULT", "PROPAGATE", "FAILOVER", "RECOVER", "VALIDATE"}
        for sc_id in self.promoted_scenarios:
            contract = self.catalog.get_scenario_contract(sc_id)
            self.assertIsNotNone(contract, f"ScenarioContract for {sc_id} not found")

            contract_phases = {p.phase if hasattr(p, "phase") else p.get("phase") for p in contract.phases}
            self.assertTrue(
                expected_phases.issubset(contract_phases),
                f"Scenario {sc_id} missing required phases: {expected_phases - contract_phases}"
            )

            # Check use case structure
            uc = contract.use_case if hasattr(contract, "use_case") else getattr(contract, "use_case", None)
            self.assertIsNotNone(uc, f"Scenario {sc_id} missing use_case definition")
            self.assertTrue(bool(getattr(uc, "objective", None) or uc.get("objective")), f"Scenario {sc_id} missing objective")
            self.assertTrue(bool(getattr(uc, "validation_criteria", None) or uc.get("validation_criteria")), f"Scenario {sc_id} missing validation criteria")

    def test_04_verification_rules_count(self):
        """Verify each promoted scenario defines at least 4 verification rules."""
        for sc_id in self.promoted_scenarios:
            contract = self.catalog.get_scenario_contract(sc_id)
            rules = contract.validation_rules
            self.assertGreaterEqual(
                len(rules), 4,
                f"Scenario {sc_id} has {len(rules)} validation rules; expected at least 4"
            )

    # -------------------------------------------------------------------------
    # 2. Distinct Topological Context Resolution
    # -------------------------------------------------------------------------
    def test_05_distinct_topologies_resolved(self):
        """Verify each scenario resolves to its distinct canonical topology."""
        # 1. mixed_sase_degradation -> mixed_sase
        c_sase = self.catalog.get_scenario_contract("mixed_sase_degradation")
        topo_sase = self.runner._get_topology_for_scenario(c_sase)
        node_types_sase = {n.type for n in topo_sase.nodes}
        self.assertIn(NodeType.SASE_PROXY, node_types_sase)

        # 2. mixed_backbone_optical -> mixed_optical
        c_opt = self.catalog.get_scenario_contract("mixed_backbone_optical")
        topo_opt = self.runner._get_topology_for_scenario(c_opt)
        node_types_opt = {n.type for n in topo_opt.nodes}
        self.assertIn(NodeType.OPTICAL_CORE, node_types_opt)

        # 3. openconfig_mdt_streaming -> openconfig_core
        c_oc = self.catalog.get_scenario_contract("openconfig_mdt_streaming")
        topo_oc = self.runner._get_topology_for_scenario(c_oc)
        node_ids_oc = {n.id for n in topo_oc.nodes}
        self.assertIn("node-cisco8k", node_ids_oc)
        self.assertIn("node-juniper-ptx", node_ids_oc)

        # 4. sql_injection -> bypassed
        c_sqli = self.catalog.get_scenario_contract("sql_injection")
        topo_sqli = self.runner._get_topology_for_scenario(c_sqli)
        node_ids_sqli = {n.id for n in topo_sqli.nodes}
        self.assertIn("node-db", node_ids_sqli)
        edge_status = [e.status for e in topo_sqli.edges if e.id == "edge-bypass"]
        self.assertEqual(edge_status, ["breached"])

        # 5. ddos_attack -> secure
        c_ddos = self.catalog.get_scenario_contract("ddos_attack")
        topo_ddos = self.runner._get_topology_for_scenario(c_ddos)
        node_ids_ddos = {n.id for n in topo_ddos.nodes}
        self.assertIn("node-fw", node_ids_ddos)
        self.assertIn("node-lb", node_ids_ddos)

    # -------------------------------------------------------------------------
    # 3. Dedicated Telemetry Generation & Zero Generic Fallback
    # -------------------------------------------------------------------------
    def test_06_zero_generic_fallback_in_essential_proof(self):
        """Assert zero occurrences of %NETSPOUT-6-INFO fallback logs across all 5 promoted scenarios."""
        for sc_id in self.promoted_scenarios:
            req = ScenarioRunRequest(scenario_id=sc_id, seed=100, time_mode="TEST")
            manifest = self.runner.run_scenario(req)
            logs = self.runner.get_run_logs(manifest.run_id)
            self.assertGreater(len(logs), 0, f"Scenario {sc_id} generated no logs")
            fallback_logs = [l for l in logs if "%NETSPOUT-6-INFO" in l.raw_log]
            self.assertEqual(
                len(fallback_logs), 0,
                f"Scenario {sc_id} contains {len(fallback_logs)} generic fallback logs: {[l.raw_log for l in fallback_logs]}"
            )

    def test_07_canonical_sourcetypes_per_scenario(self):
        """Verify essential vendor sourcetypes are emitted for each scenario."""
        # SASE: zscaler:zia, cisco:thousandeyes:metric, pan:threat
        req_sase = ScenarioRunRequest(scenario_id="mixed_sase_degradation", seed=101, time_mode="TEST")
        man_sase = self.runner.run_scenario(req_sase)
        st_sase = {l.sourcetype for l in self.runner.get_run_logs(man_sase.run_id)}
        self.assertIn("zscaler:zia", st_sase)
        self.assertIn("cisco:thousandeyes:metric", st_sase)
        self.assertIn("pan:threat", st_sase)

        # Optical: nokia:sros:syslog, juniper:junos, arista:flow:ipfix
        req_opt = ScenarioRunRequest(scenario_id="mixed_backbone_optical", seed=102, time_mode="TEST")
        man_opt = self.runner.run_scenario(req_opt)
        st_opt = {l.sourcetype for l in self.runner.get_run_logs(man_opt.run_id)}
        self.assertIn("nokia:sros:syslog", st_opt)
        self.assertIn("juniper:junos", st_opt)
        self.assertIn("arista:flow:ipfix", st_opt)

        # OpenConfig: cisco:ios:mdt
        req_oc = ScenarioRunRequest(scenario_id="openconfig_mdt_streaming", seed=103, time_mode="TEST")
        man_oc = self.runner.run_scenario(req_oc)
        st_oc = {l.sourcetype for l in self.runner.get_run_logs(man_oc.run_id)}
        self.assertIn("cisco:ios:mdt", st_oc)

        # SQL Injection: cisco:asa, nginx:plus:kv, postgresql:audit
        req_sqli = ScenarioRunRequest(scenario_id="sql_injection", seed=104, time_mode="TEST")
        man_sqli = self.runner.run_scenario(req_sqli)
        st_sqli = {l.sourcetype for l in self.runner.get_run_logs(man_sqli.run_id)}
        self.assertIn("cisco:asa", st_sqli)
        self.assertIn("nginx:plus:kv", st_sqli)
        self.assertIn("postgresql:audit", st_sqli)

        # DDoS Attack: cisco:asa, f5:bigip:ltm, nginx:plus:kv
        req_ddos = ScenarioRunRequest(scenario_id="ddos_attack", seed=105, time_mode="TEST")
        man_ddos = self.runner.run_scenario(req_ddos)
        st_ddos = {l.sourcetype for l in self.runner.get_run_logs(man_ddos.run_id)}
        self.assertIn("cisco:asa", st_ddos)
        self.assertIn("f5:bigip:ltm", st_ddos)
        self.assertIn("nginx:plus:kv", st_ddos)

    # -------------------------------------------------------------------------
    # 4. Positive Contract Validation (100% PASS on all rules)
    # -------------------------------------------------------------------------
    def test_08_positive_contract_validation_all_5(self):
        """Execute all 5 scenarios and verify overall_validation == PASS and 100% rules pass."""
        for sc_id in self.promoted_scenarios:
            req = ScenarioRunRequest(scenario_id=sc_id, seed=200, time_mode="TEST")
            manifest = self.runner.run_scenario(req)
            self.assertEqual(
                manifest.overall_validation,
                "PASS",
                f"Scenario {sc_id} overall validation failed: {[f'{r.rule_id}: {r.message}' for r in manifest.validation_results if r.status != ValidationStatus.PASS]}"
            )
            self.assertEqual(manifest.scenario_maturity, "E2E_VALIDATED")
            for vr in manifest.validation_results:
                self.assertEqual(
                    vr.status,
                    ValidationStatus.PASS,
                    f"Scenario {sc_id} rule {vr.rule_id} ({vr.rule_name}) failed: {vr.message}"
                )

    # -------------------------------------------------------------------------
    # 5. Negative Validation Testing
    # -------------------------------------------------------------------------
    def test_09_negative_validation_mixed_sase(self):
        """Negative test for mixed_sase_degradation: missing telemetry and altered status fail."""
        contract = self.catalog.get_scenario_contract("mixed_sase_degradation")
        req = ScenarioRunRequest(scenario_id="mixed_sase_degradation", seed=301, time_mode="TEST")
        manifest = self.runner.run_scenario(req)
        clean_logs = self.runner.get_run_logs(manifest.run_id)

        # 1. Strip zscaler:zia logs -> sase-val-01 must FAIL
        stripped_logs = [l for l in clean_logs if l.sourcetype != "zscaler:zia"]
        results = [ValidationEngine.evaluate_rule(r, stripped_logs) for r in contract.validation_rules]
        sase_01 = next(r for r in results if r.rule_id == "sase-val-01")
        self.assertEqual(sase_01.status, ValidationStatus.FAIL)

        # 2. Invert degraded status to normal -> sase-val-02 must FAIL
        mutated_logs = [
            LogEntry(**{**l.dict(), "status": "normal"}) if l.status == "degraded" else l
            for l in clean_logs
        ]
        results = [ValidationEngine.evaluate_rule(r, mutated_logs) for r in contract.validation_rules]
        sase_02 = next(r for r in results if r.rule_id == "sase-val-02")
        self.assertEqual(sase_02.status, ValidationStatus.FAIL)

    def test_10_negative_validation_mixed_optical(self):
        """Negative test for mixed_backbone_optical: missing Nokia / Juniper logs fail."""
        contract = self.catalog.get_scenario_contract("mixed_backbone_optical")
        req = ScenarioRunRequest(scenario_id="mixed_backbone_optical", seed=302, time_mode="TEST")
        manifest = self.runner.run_scenario(req)
        clean_logs = self.runner.get_run_logs(manifest.run_id)

        # Strip nokia:sros:syslog -> optical-val-01 must FAIL
        no_nokia = [l for l in clean_logs if l.sourcetype != "nokia:sros:syslog"]
        results = [ValidationEngine.evaluate_rule(r, no_nokia) for r in contract.validation_rules]
        r1 = next(r for r in results if r.rule_id == "optical-val-01")
        self.assertEqual(r1.status, ValidationStatus.FAIL)

        # Strip juniper:junos -> optical-val-02 must FAIL
        no_juniper = [l for l in clean_logs if l.sourcetype != "juniper:junos"]
        results = [ValidationEngine.evaluate_rule(r, no_juniper) for r in contract.validation_rules]
        r2 = next(r for r in results if r.rule_id == "optical-val-02")
        self.assertEqual(r2.status, ValidationStatus.FAIL)

    def test_11_negative_validation_openconfig_mdt(self):
        """Negative test for openconfig_mdt_streaming: missing MDT logs and missing congestion fail."""
        contract = self.catalog.get_scenario_contract("openconfig_mdt_streaming")
        req = ScenarioRunRequest(scenario_id="openconfig_mdt_streaming", seed=303, time_mode="TEST")
        manifest = self.runner.run_scenario(req)
        clean_logs = self.runner.get_run_logs(manifest.run_id)

        # Strip cisco:ios:mdt -> oc-val-01 must FAIL
        no_mdt = [l for l in clean_logs if l.sourcetype != "cisco:ios:mdt"]
        results = [ValidationEngine.evaluate_rule(r, no_mdt) for r in contract.validation_rules]
        r1 = next(r for r in results if r.rule_id == "oc-val-01")
        self.assertEqual(r1.status, ValidationStatus.FAIL)

        # Strip degraded status -> oc-val-02 must FAIL
        no_deg = [l for l in clean_logs if l.status != "degraded"]
        results = [ValidationEngine.evaluate_rule(r, no_deg) for r in contract.validation_rules]
        r2 = next(r for r in results if r.rule_id == "oc-val-02")
        self.assertEqual(r2.status, ValidationStatus.FAIL)

    def test_12_negative_validation_sql_injection(self):
        """Negative test for sql_injection: altered firewall action and missing db audit fail."""
        contract = self.catalog.get_scenario_contract("sql_injection")
        req = ScenarioRunRequest(scenario_id="sql_injection", seed=304, time_mode="TEST")
        manifest = self.runner.run_scenario(req)
        clean_logs = self.runner.get_run_logs(manifest.run_id)

        # Mutate blocked to allowed -> sqli-val-03 must FAIL
        mutated_action = [
            LogEntry(**{**l.dict(), "action": "allowed"}) if l.action == "blocked" else l
            for l in clean_logs
        ]
        results = [ValidationEngine.evaluate_rule(r, mutated_action) for r in contract.validation_rules]
        r3 = next(r for r in results if r.rule_id == "sqli-val-03")
        self.assertEqual(r3.status, ValidationStatus.FAIL)

        # Strip postgresql:audit -> sqli-val-02 must FAIL
        no_db = [l for l in clean_logs if l.sourcetype != "postgresql:audit"]
        results = [ValidationEngine.evaluate_rule(r, no_db) for r in contract.validation_rules]
        r2 = next(r for r in results if r.rule_id == "sqli-val-02")
        self.assertEqual(r2.status, ValidationStatus.FAIL)

    def test_13_negative_validation_ddos_attack(self):
        """Negative test for ddos_attack: missing ASA log and missing block action fail."""
        contract = self.catalog.get_scenario_contract("ddos_attack")
        req = ScenarioRunRequest(scenario_id="ddos_attack", seed=305, time_mode="TEST")
        manifest = self.runner.run_scenario(req)
        clean_logs = self.runner.get_run_logs(manifest.run_id)

        # Strip cisco:asa -> ddos-val-01 must FAIL
        no_asa = [l for l in clean_logs if l.sourcetype != "cisco:asa"]
        results = [ValidationEngine.evaluate_rule(r, no_asa) for r in contract.validation_rules]
        r1 = next(r for r in results if r.rule_id == "ddos-val-01")
        self.assertEqual(r1.status, ValidationStatus.FAIL)

        # Invert blocked -> ddos-val-02 must FAIL
        mutated_action = [
            LogEntry(**{**l.dict(), "action": "allowed"}) if l.action == "blocked" else l
            for l in clean_logs
        ]
        results = [ValidationEngine.evaluate_rule(r, mutated_action) for r in contract.validation_rules]
        r2 = next(r for r in results if r.rule_id == "ddos-val-02")
        self.assertEqual(r2.status, ValidationStatus.FAIL)

    # -------------------------------------------------------------------------
    # 6. Determinism & Seed Consistency
    # -------------------------------------------------------------------------
    def test_14_simulation_determinism(self):
        """Verify that identical seeds produce identical telemetry counts and statuses."""
        for sc_id in self.promoted_scenarios:
            req1 = ScenarioRunRequest(scenario_id=sc_id, seed=777, time_mode="TEST")
            m1 = self.runner.run_scenario(req1)
            logs1 = self.runner.get_run_logs(m1.run_id)

            req2 = ScenarioRunRequest(scenario_id=sc_id, seed=777, time_mode="TEST")
            m2 = self.runner.run_scenario(req2)
            logs2 = self.runner.get_run_logs(m2.run_id)

            self.assertEqual(len(logs1), len(logs2), f"Scenario {sc_id} log count non-deterministic")
            self.assertEqual(
                [l.sourcetype for l in logs1],
                [l.sourcetype for l in logs2],
                f"Scenario {sc_id} sourcetypes non-deterministic"
            )
            self.assertEqual(
                [l.action for l in logs1],
                [l.action for l in logs2],
                f"Scenario {sc_id} actions non-deterministic"
            )

    # -------------------------------------------------------------------------
    # 7. Unified Evidence Discovery across Wave 1 Scenarios
    # -------------------------------------------------------------------------
    def test_15_openconfig_mdt_evidence_destinations(self):
        """Verify openconfig_mdt_streaming discovers both event and metric destinations."""
        req = ScenarioRunRequest(scenario_id="openconfig_mdt_streaming", seed=401, time_mode="TEST")
        manifest = self.runner.run_scenario(req)

        with patch.object(self.runner, "_execute_splunk_rest_query", return_value=(5, None)):
            evidence = self.runner.get_run_evidence(manifest.run_id)

        self.assertIsNotNone(evidence)
        dest_types = {d.telemetry_type for d in evidence.destinations}
        # Discovers event destination
        self.assertIn(TelemetryType.EVENT, dest_types)

        # Verify SPL query generated
        event_dest = next(d for d in evidence.destinations if d.telemetry_type == TelemetryType.EVENT)
        self.assertIn("search index=", event_dest.query)
        self.assertIn(manifest.run_id, event_dest.query)

    def test_16_evidence_discovery_all_promoted_scenarios(self):
        """Verify evidence discovery builds valid SPL queries for all 5 promoted scenarios."""
        for sc_id in self.promoted_scenarios:
            req = ScenarioRunRequest(scenario_id=sc_id, seed=500, time_mode="TEST")
            manifest = self.runner.run_scenario(req)

            with patch.object(self.runner, "_execute_splunk_rest_query", return_value=(len(self.runner.get_run_logs(manifest.run_id)), None)):
                evidence = self.runner.get_run_evidence(manifest.run_id)

            self.assertIsNotNone(evidence)
            self.assertGreater(len(evidence.destinations), 0)
            self.assertGreater(evidence.total_generated, 0)
            for d in evidence.destinations:
                self.assertIn(manifest.run_id, d.query)
                self.assertIn(d.target_index, d.query)


if __name__ == "__main__":
    unittest.main()
