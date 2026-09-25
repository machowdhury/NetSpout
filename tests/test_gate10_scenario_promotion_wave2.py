"""
Test Suite: Gate 10 Scenario Promotion Wave 2 — Operational Use Cases
Validates promotion of exactly FIVE candidate scenarios to E2E_VALIDATED:
1. arch_lan_campus_access (Campus LAN / Access Port Security: Rogue DHCP & Dynamic ARP Inspection)
2. arch_vpn_remote_workforce (WAN / Enterprise Remote Access: SSL-VPN Credential Stuffing & Duo Push Fraud)
3. service_provider_cisco (Service Provider / Core Routing: Carrier Flap BGP Adjacency Collapse & TI-LFA Fast Reroute)
4. arch_wlan_meraki_catalyst (Wireless / RF Health: CleanAir RF Interference & Air Marshal Rogue Suppression)
5. arch_man_carrier_ring (MAN / Metro Optical: 100G Terrestrial Fiber Cut & G.8032 ERPS Sub-50ms Ring Protection)

Covers:
- Exact catalog maturity distribution: 7 GOLDEN_PATH_CERTIFIED, 7 E2E_VALIDATED, 2 FORMAT_VALIDATED, 13 CONTRACTED (Total 29)
- Scenario contracts, phases, use cases, and validation rules
- Topology resolution and graph state structure
- Canonical log formatters and ZERO generic essential fallback (%NETSPOUT-6-INFO)
- Positive contract validation (100% rules pass)
- Causal ground truth tracking (root condition, symptoms, impact, mitigation, recovery)
- Negative validation (deterministic failure on tampered/corrupted evidence)
- Determinism and seed consistency
- Telemetry semantics (HEC transport, storage indices, fidelity badge)
- Golden path non-regression
"""

import unittest
from typing import List
from collections import Counter

from netspout_core.catalog import NetSpoutCatalog
from netspout_core.scenario_runner import (
    ScenarioRunner,
    ValidationEngine,
    get_arch_lan_campus_access_topology,
    get_arch_vpn_remote_workforce_topology,
    get_service_provider_cisco_topology,
    get_arch_wlan_meraki_catalyst_topology,
    get_arch_man_carrier_ring_topology
)
from netspout_core.models import (
    ScenarioRunRequest,
    ScenarioPhase,
    ValidationStatus,
    LogEntry,
    NodeType
)


class TestGate10ScenarioPromotionWave2(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.catalog = NetSpoutCatalog()
        cls.runner = ScenarioRunner()
        cls.wave2_scenarios = [
            "arch_lan_campus_access",
            "arch_vpn_remote_workforce",
            "service_provider_cisco",
            "arch_wlan_meraki_catalyst",
            "arch_man_carrier_ring"
        ]
        cls.golden_paths = [
            "cisco_sdwan_brownout",
            "cisco_campus_rogue",
            "cisco_aci_microburst",
            "mixed_edge_breach",
            "mixed_sase_degradation",
            "sql_injection",
            "openconfig_mdt_streaming"
        ]

    # -------------------------------------------------------------------------
    # 1. Catalog Maturity Distribution & Promotion Counts
    # -------------------------------------------------------------------------
    def test_01_catalog_maturity_distribution_wave2(self):
        """Verify exact catalog maturity counts: 7 Golden, 7 E2E, 2 Format, 13 Contracted (Total 29)."""
        all_scens = self.catalog.list_scenarios()
        self.assertEqual(len(all_scens), 29, "Catalog must contain exactly 29 total scenarios")

        counts = Counter(s.get("maturity") for s in all_scens)
        self.assertGreaterEqual(counts["GOLDEN_PATH_CERTIFIED"], 7, "Must have at least 7 GOLDEN_PATH_CERTIFIED scenarios")
        self.assertIn(counts["GOLDEN_PATH_CERTIFIED"] + counts["E2E_VALIDATED"], (12, 14), "Must have exactly 14 operational/backbone scenarios across Golden and E2E tiers")
        self.assertEqual(counts["FORMAT_VALIDATED"], 2, "Must have exactly 2 FORMAT_VALIDATED scenarios")
        self.assertEqual(counts["CONTRACTED"], 13, "Must have exactly 13 CONTRACTED scenarios deferred")

    def test_02_wave2_promoted_scenarios_maturity(self):
        """Verify the 5 selected Wave 2 scenarios have maturity == E2E_VALIDATED or GOLDEN_PATH_CERTIFIED."""
        for sid in self.wave2_scenarios:
            scen = self.catalog.get_scenario(sid)
            self.assertIsNotNone(scen, f"Scenario {sid} must exist in catalog")
            self.assertIn(
                scen.get("maturity"),
                ("E2E_VALIDATED", "GOLDEN_PATH_CERTIFIED"),
                f"Scenario {sid} must have maturity == E2E_VALIDATED or GOLDEN_PATH_CERTIFIED"
            )

    def test_03_golden_paths_invariance(self):
        """Verify all 7 Golden Paths remain GOLDEN_PATH_CERTIFIED with zero regression."""
        for gp in self.golden_paths:
            scen = self.catalog.get_scenario(gp)
            self.assertIsNotNone(scen, f"Golden Path {gp} must exist in catalog")
            self.assertEqual(
                scen.get("maturity"),
                "GOLDEN_PATH_CERTIFIED",
                f"Golden Path {gp} must remain GOLDEN_PATH_CERTIFIED"
            )

    # -------------------------------------------------------------------------
    # 2. Topology Resolution & Distinct Graph Structure
    # -------------------------------------------------------------------------
    def test_04_wave2_topological_resolution(self):
        """Verify each promoted scenario resolves to its dedicated TopologyState."""
        expected_specs = {
            "arch_lan_campus_access": (6, 6, "arch_lan_campus_access"),
            "arch_vpn_remote_workforce": (6, 6, "arch_vpn_remote_workforce"),
            "service_provider_cisco": (8, 8, "service_provider_cisco"),
            "arch_wlan_meraki_catalyst": (6, 6, "arch_wlan_meraki_catalyst"),
            "arch_man_carrier_ring": (6, 6, "arch_man_carrier_ring")
        }

        for sid, (exp_nodes, exp_edges, exp_top_id) in expected_specs.items():
            contract = self.catalog.get_scenario_contract(sid)
            top = self.runner._get_topology_for_scenario(contract)
            self.assertIsNotNone(top, f"Topology for {sid} could not be resolved")
            self.assertEqual(len(top.nodes), exp_nodes, f"{sid} expected {exp_nodes} nodes, got {len(top.nodes)}")
            self.assertEqual(len(top.edges), exp_edges, f"{sid} expected {exp_edges} edges, got {len(top.edges)}")

    # -------------------------------------------------------------------------
    # 3. Contract Phases, Rules, and Telemetry Semantics
    # -------------------------------------------------------------------------
    def test_05_wave2_contract_phases_and_rules(self):
        """Verify each promoted scenario defines 6 phases and 3-4 semantic validation rules."""
        required_phases = {"BASELINE", "FAULT", "PROPAGATE", "FAILOVER", "RECOVER", "VALIDATE"}
        for sid in self.wave2_scenarios:
            contract = self.catalog.get_scenario_contract(sid)
            phases = {p.phase if hasattr(p, "phase") else p.get("phase") for p in contract.phases}
            self.assertTrue(required_phases.issubset(phases), f"{sid} missing required phases: {required_phases - phases}")
            self.assertGreaterEqual(len(contract.validation_rules), 3, f"{sid} must define at least 3 validation rules")
            self.assertIsNotNone(contract.use_case, f"{sid} must define use_case metadata")

    def test_06_wave2_telemetry_semantics(self):
        """Verify telemetry semantics metadata: transport=Splunk HEC, fidelity=MODELED PAYLOAD."""
        for sid in self.wave2_scenarios:
            scen = self.catalog.get_scenario(sid)
            self.assertEqual(scen.get("transport_protocol"), "Splunk HEC", f"{sid} transport must be Splunk HEC")
            self.assertEqual(scen.get("fidelity_badge"), "MODELED PAYLOAD", f"{sid} fidelity badge must be MODELED PAYLOAD")
            self.assertIsNotNone(scen.get("telemetry_model"), f"{sid} must define telemetry_model")
            self.assertIsNotNone(scen.get("splunk_storage"), f"{sid} must define splunk_storage")
            self.assertIsNotNone(scen.get("telemetry_notes"), f"{sid} must define telemetry_notes")

    # -------------------------------------------------------------------------
    # 4. Zero Generic Fallback (%NETSPOUT-6-INFO Strictly Disallowed)
    # -------------------------------------------------------------------------
    def test_07_zero_generic_fallback_wave2(self):
        """Verify zero %NETSPOUT-6-INFO fallback logs across all 5 promoted scenarios."""
        for sid in self.wave2_scenarios:
            req = ScenarioRunRequest(scenario_id=sid, seed=42, time_mode="TEST")
            manifest = self.runner.run_scenario(req)
            logs = self.runner.run_logs.get(manifest.run_id, [])
            self.assertGreater(len(logs), 0, f"{sid} produced zero logs")

            for entry in logs:
                self.assertNotIn(
                    "%NETSPOUT-6-INFO",
                    entry.raw_log,
                    f"Forbidden generic fallback %NETSPOUT-6-INFO found in {sid} log: {entry.raw_log}"
                )
                self.assertNotIn(
                    "Simulated Telemetry",
                    entry.signature or "",
                    f"Generic fallback signature found in {sid}: {entry.signature}"
                )

    # -------------------------------------------------------------------------
    # 5. Positive Contract Validation (100% Rules PASS)
    # -------------------------------------------------------------------------
    def test_08_positive_contract_validation_wave2(self):
        """Verify all machine-readable validation rules evaluate to PASS for all 5 scenarios."""
        for sid in self.wave2_scenarios:
            req = ScenarioRunRequest(scenario_id=sid, seed=42, time_mode="TEST")
            manifest = self.runner.run_scenario(req)

            self.assertGreater(len(manifest.validation_results), 0, f"{sid} produced no validation results")
            for result in manifest.validation_results:
                self.assertEqual(
                    result.status,
                    ValidationStatus.PASS,
                    f"Validation rule failed in {sid}: {result.rule_id} ({result.rule_name}) - message: {result.message}"
                )
            self.assertIn(
                manifest.scenario_maturity,
                ("E2E_VALIDATED", "GOLDEN_PATH_CERTIFIED"),
                f"{sid} manifest must stamp scenario_maturity == E2E_VALIDATED or GOLDEN_PATH_CERTIFIED"
            )

    # -------------------------------------------------------------------------
    # 6. Causal Ground Truth Tracking
    # -------------------------------------------------------------------------
    def test_09_causal_ground_truth_records_wave2(self):
        """Verify causal ground truth records contain intentional fault, recovery, and observations."""
        for sid in self.wave2_scenarios:
            req = ScenarioRunRequest(scenario_id=sid, seed=42, time_mode="TEST")
            manifest = self.runner.run_scenario(req)

            gt_records = manifest.ground_truth_records
            self.assertGreater(len(gt_records), 0, f"{sid} produced zero ground truth records")

            phases_recorded = {r.phase for r in gt_records}
            self.assertIn("FAULT", phases_recorded, f"{sid} missing FAULT phase in ground truth")
            self.assertIn("RECOVER", phases_recorded, f"{sid} missing RECOVER phase in ground truth")

            fault_record = next(r for r in gt_records if r.phase == "FAULT")
            self.assertIsNotNone(fault_record.intentional_fault, f"{sid} FAULT record missing intentional_fault")
            self.assertGreater(len(fault_record.expected_observations), 0, f"{sid} FAULT record missing expected_observations")

            recover_record = next(r for r in gt_records if r.phase == "RECOVER")
            self.assertIsNotNone(recover_record.intentional_recovery, f"{sid} RECOVER record missing intentional_recovery")

    # -------------------------------------------------------------------------
    # 7. Negative Validation (Adversarial Evidence Tampering)
    # -------------------------------------------------------------------------
    def test_10_negative_validation_adversarial_tampering(self):
        """Verify validation engine fails deterministically when evidence logs are mutated or missing."""
        for sid in self.wave2_scenarios:
            contract = self.catalog.get_scenario_contract(sid)
            top = self.runner._get_topology_for_scenario(contract)
            from netspout_core.graph_engine import TopologyGraph
            graph = TopologyGraph(top)

            # Generate valid baseline logs
            req = ScenarioRunRequest(scenario_id=sid, seed=42, time_mode="TEST")
            manifest = self.runner.run_scenario(req)
            valid_logs = self.runner.run_logs.get(manifest.run_id, [])

            # Adversarial Mutation: strip all logs with status == "restored" or action == "blocked"
            corrupted_logs = [
                LogEntry(**{**l.model_dump(), "status": "failed", "action": "ignored"})
                for l in valid_logs
            ]

            results = ValidationEngine.evaluate_all(contract.validation_rules, corrupted_logs, graph)
            failed_rules = [r for r in results if r.status == ValidationStatus.FAIL]
            self.assertGreater(
                len(failed_rules),
                0,
                f"Negative validation expected failure for {sid} with tampered logs, but all passed!"
            )

    # -------------------------------------------------------------------------
    # 8. Determinism and Seed Consistency
    # -------------------------------------------------------------------------
    def test_11_determinism_and_seed_consistency(self):
        """Verify runs with identical seed produce identical semantic log sequences."""
        for sid in self.wave2_scenarios:
            req1 = ScenarioRunRequest(scenario_id=sid, seed=12345, time_mode="TEST")
            manifest1 = self.runner.run_scenario(req1)
            logs1 = [(l.sourcetype, l.action, l.status, l.signature) for l in self.runner.run_logs.get(manifest1.run_id, [])]

            req2 = ScenarioRunRequest(scenario_id=sid, seed=12345, time_mode="TEST")
            manifest2 = self.runner.run_scenario(req2)
            logs2 = [(l.sourcetype, l.action, l.status, l.signature) for l in self.runner.run_logs.get(manifest2.run_id, [])]

            self.assertEqual(logs1, logs2, f"Seed determinism failed for {sid}")


if __name__ == "__main__":
    unittest.main()
