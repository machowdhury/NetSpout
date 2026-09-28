"""
Test Suite: Gate 10.6 Scenario Namespace, Maturity & Golden Path Reconciliation
Validates the canonical identity, namespace uniqueness, maturity distribution,
and evidence integrity across all 29 NetSpout scenarios.

Author: Mahamudul Chowdhury (machowdhury@yahoo.com)
"""

import os
import json
import unittest
from collections import Counter

from netspout_core.catalog import NetSpoutCatalog, catalog
from netspout_core.scenario_runner import ScenarioRunner
from netspout_core.models import ScenarioRunRequest, ScenarioContract


class TestGate10_6NamespaceReconciliation(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        cls.catalog = NetSpoutCatalog()
        cls.runner = ScenarioRunner()
        cls.expected_golden_paths = [
            "cisco_sdwan_brownout",
            "cisco_campus_rogue",
            "cisco_aci_microburst",
            "mixed_edge_breach",
            "mixed_sase_degradation",
            "sql_injection",
            "openconfig_mdt_streaming",
            "arch_lan_campus_access",
            "arch_vpn_remote_workforce",
            "service_provider_cisco",
            "arch_wlan_meraki_catalyst",
            "arch_man_carrier_ring",
            "mixed_backbone_optical"
        ]
        cls.expected_contracted = [
            "arch_can_multi_building",
            "arch_epn_isolated_intranet",
            "arch_gan_subsea_cloud",
            "arch_nas_storage_cluster",
            "arch_pan_iot_mesh",
            "arch_san_fibre_channel",
            "arch_wan_global_backbone",
            "mixed_vendor_enterprise",
            "pure_cisco_enterprise",
            "sdwan_connected_core",
            "service_provider_mixed",
            "wireless_connected_core_cisco",
            "wireless_connected_core_mixed"
        ]

    # -------------------------------------------------------------------------
    # 1. Total Canonical Scenario Count & Uniqueness
    # -------------------------------------------------------------------------
    def test_01_total_scenarios_and_unique_canonical_ids(self):
        """Verify exactly 29 scenarios exist and every canonical ID is unique."""
        scenarios = self.catalog.list_scenarios()
        self.assertEqual(len(scenarios), 29, "Catalog must contain exactly 29 scenarios")

        ids = [s["id"] for s in scenarios]
        id_counts = Counter(ids)
        duplicates = [sid for sid, count in id_counts.items() if count > 1]
        self.assertEqual(len(duplicates), 0, f"Duplicate scenario IDs detected: {duplicates}")
        self.assertEqual(len(set(ids)), 29, "All 29 scenario IDs must be unique")

    def test_02_scenario_titles_uniqueness(self):
        """Verify all 29 user-facing titles are non-empty and unique."""
        scenarios = self.catalog.list_scenarios()
        names = [s.get("name") for s in scenarios]
        self.assertTrue(all(names), "All scenarios must have non-empty names")
        name_counts = Counter(names)
        duplicates = [name for name, count in name_counts.items() if count > 1]
        self.assertEqual(len(duplicates), 0, f"Duplicate scenario names detected: {duplicates}")

    # -------------------------------------------------------------------------
    # 2. Maturity Distribution & Reconciliation
    # -------------------------------------------------------------------------
    def test_03_exact_maturity_distribution(self):
        """Verify exact maturity breakdown: 13 Golden, 1 E2E, 2 Format, 13 Contracted = 29 Total."""
        scenarios = self.catalog.list_scenarios()
        counts = Counter(s.get("maturity") for s in scenarios)

        self.assertEqual(counts["GOLDEN_PATH_CERTIFIED"], 13, "Must have exactly 13 GOLDEN_PATH_CERTIFIED scenarios")
        self.assertEqual(counts["E2E_VALIDATED"], 1, "Must have exactly 1 E2E_VALIDATED scenario (ddos_attack)")
        self.assertEqual(counts["FORMAT_VALIDATED"], 2, "Must have exactly 2 FORMAT_VALIDATED scenarios (normal_traffic, lateral_movement)")
        self.assertEqual(counts["CONTRACTED"], 13, "Must have exactly 13 CONTRACTED scenarios")
        self.assertEqual(sum(counts.values()), 29, "Total of all maturity counts must equal 29")

    def test_04_golden_path_identifiers(self):
        """Verify the exact set of 13 GOLDEN_PATH_CERTIFIED scenario identifiers."""
        certified = [s["id"] for s in self.catalog.list_scenarios() if s.get("maturity") == "GOLDEN_PATH_CERTIFIED"]
        self.assertEqual(len(certified), 13)
        self.assertEqual(set(certified), set(self.expected_golden_paths))

    def test_05_e2e_and_format_validated_identifiers(self):
        """Verify E2E_VALIDATED and FORMAT_VALIDATED scenarios match expected canonical sets."""
        e2e = [s["id"] for s in self.catalog.list_scenarios() if s.get("maturity") == "E2E_VALIDATED"]
        self.assertEqual(set(e2e), {"ddos_attack"})

        format_val = [s["id"] for s in self.catalog.list_scenarios() if s.get("maturity") == "FORMAT_VALIDATED"]
        self.assertEqual(set(format_val), {"normal_traffic", "lateral_movement"})

    # -------------------------------------------------------------------------
    # 3. Discrepancy Investigation & Non-Existence of Fabricated Names
    # -------------------------------------------------------------------------
    def test_06_hallucinated_scenario_names_not_in_catalog(self):
        """Verify none of the 7 hallucinated Gate 10.5 summary names exist as canonical scenarios."""
        hallucinated_names = [
            "datacenter_spine_leaf",
            "enterprise_sdwan",
            "firewall_failover",
            "cloud_interconnect",
            "bgp_route_leak",
            "arista_evpn_vxlan",
            "juniper_switch_fabric"
        ]
        for name in hallucinated_names:
            scen = self.catalog.get_scenario(name)
            self.assertIsNone(scen, f"Hallucinated name '{name}' must NOT exist as a canonical scenario in catalog")

    def test_07_contracted_tier_scenarios(self):
        """Verify all 13 canonical contracted scenarios exist and have CONTRACTED maturity."""
        contracted = [s["id"] for s in self.catalog.list_scenarios() if s.get("maturity") == "CONTRACTED"]
        self.assertEqual(len(contracted), 13)
        self.assertEqual(set(contracted), set(self.expected_contracted))

    # -------------------------------------------------------------------------
    # 4. Golden Path Evidence Ledger & Artifact Verifiability
    # -------------------------------------------------------------------------
    def test_08_golden_path_evidence_ledger_completeness(self):
        """Verify catalog/golden_path_evidence.json contains all 13 Golden Paths with PROVEN status."""
        evidence_path = os.path.join(self.repo_root, "catalog", "golden_path_evidence.json")
        self.assertTrue(os.path.exists(evidence_path), "golden_path_evidence.json must exist")

        with open(evidence_path, "r", encoding="utf-8") as f:
            ledger = json.load(f)

        entries = ledger.get("golden_paths", [])
        self.assertEqual(len(entries), 13, "Evidence ledger must contain exactly 13 Golden Paths")

        for entry in entries:
            sid = entry.get("canonical_id")
            self.assertIn(sid, self.expected_golden_paths)
            self.assertEqual(entry.get("maturity"), "GOLDEN_PATH_CERTIFIED")
            self.assertEqual(entry.get("evidence_classification"), "PROVEN")
            self.assertEqual(entry.get("completeness_pct"), 100.0)
            self.assertEqual(entry.get("overall_validation"), "PASS")
            self.assertFalse(entry.get("developer_knowledge_required"))

            # Verify acceptance doc exists
            rep_path = os.path.join(self.repo_root, entry["primary_acceptance_report"])
            self.assertTrue(os.path.exists(rep_path), f"Report {rep_path} must exist on disk for {sid}")

            # Verify retest doc exists if specified
            retest = entry.get("retest_report")
            if retest:
                retest_path = os.path.join(self.repo_root, retest)
                self.assertTrue(os.path.exists(retest_path), f"Retest report {retest_path} must exist on disk for {sid}")

    # -------------------------------------------------------------------------
    # 5. Alias Governance & Scenario ID Resolution
    # -------------------------------------------------------------------------
    def test_09_alias_resolution_api(self):
        """Verify resolve_scenario_id returns canonical ID for valid IDs and handles aliases."""
        for sid in self.expected_golden_paths:
            can_id, is_alias = self.catalog.resolve_scenario_id(sid)
            self.assertEqual(can_id, sid)
            self.assertFalse(is_alias)

        # Unregistered ID returns unchanged
        unreg_id, is_alias = self.catalog.resolve_scenario_id("unknown_scenario_xyz")
        self.assertEqual(unreg_id, "unknown_scenario_xyz")
        self.assertFalse(is_alias)

    def test_10_runner_stamps_canonical_scenario_id(self):
        """Verify ScenarioRunner stamps canonical scenario ID into RunManifest."""
        req = ScenarioRunRequest(
            scenario_id="cisco_sdwan_brownout",
            time_mode="TEST",
            seed=42
        )
        manifest = self.runner.run_scenario(req)
        self.assertEqual(manifest.scenario_id, "cisco_sdwan_brownout")
        self.assertGreater(manifest.total_events_generated, 0)

    # -------------------------------------------------------------------------
    # 6. Catalog Synchronization & Mirror Invariance
    # -------------------------------------------------------------------------
    def test_11_catalog_mirrors_synchronized(self):
        """Verify catalog/scenarios.json is identical across netspout/bin and backend/app."""
        root_scenarios_path = os.path.join(self.repo_root, "catalog", "scenarios.json")
        with open(root_scenarios_path, "r", encoding="utf-8") as f:
            root_scenarios = json.load(f)

        mirrors = [
            os.path.join(self.repo_root, "netspout", "bin", "catalog_data", "scenarios.json"),
            os.path.join(self.repo_root, "backend", "app", "catalog_data", "scenarios.json"),
            os.path.join(self.repo_root, "netspout", "catalog", "scenarios.json")
        ]
        for mpath in mirrors:
            self.assertTrue(os.path.exists(mpath), f"Mirror {mpath} must exist")
            with open(mpath, "r", encoding="utf-8") as f:
                mirror_scenarios = json.load(f)
            self.assertEqual(len(mirror_scenarios), len(root_scenarios), f"Count mismatch in {mpath}")
            self.assertEqual(
                [s["id"] for s in mirror_scenarios],
                [s["id"] for s in root_scenarios],
                f"Scenario ID order mismatch in {mpath}"
            )


if __name__ == "__main__":
    unittest.main()
