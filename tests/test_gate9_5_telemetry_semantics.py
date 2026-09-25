"""
Test Suite: Gate 9.5 Telemetry Semantics UX Clarification
Validates:
1. Explicit telemetry semantics metadata across all catalog scenarios:
   - telemetry_model
   - transport_protocol (e.g. Splunk HEC)
   - splunk_storage (e.g. Metrics Index + Event Index)
   - fidelity_badge (NATIVE TRANSPORT | MODELED PAYLOAD | SYNTHETIC)
   - telemetry_notes (educational explanation)
2. OpenConfig MDT semantics clarity:
   - Fidelity badge = MODELED PAYLOAD (no false native gNMI claim)
   - Transport protocol = Splunk HEC
   - Storage = Metrics Index (cisco_mdt_metrics) + Event Index (idx_network_ops)
   - Educational callout note explaining modeled payload vs native gRPC/gNMI dial-out
3. Post-Wave 1 Independent Acceptance Catalog Maturity State:
   - mixed_sase_degradation: GOLDEN_PATH_CERTIFIED
   - sql_injection: GOLDEN_PATH_CERTIFIED
   - openconfig_mdt_streaming: E2E_VALIDATED
   - GP01-GP04 Golden Paths preserved
4. Backend API serialization of telemetry semantics
5. Zero regressions across all Certified Golden Paths
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock
from typing import List

# Ensure src and backend are on sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if os.path.join(BASE_DIR, "src") not in sys.path:
    sys.path.insert(0, os.path.join(BASE_DIR, "src"))
if os.path.join(BASE_DIR, "backend") not in sys.path:
    sys.path.insert(0, os.path.join(BASE_DIR, "backend"))

from netspout_core.catalog import NetSpoutCatalog
from netspout_core.scenario_runner import ScenarioRunner
from netspout_core.models import (
    ScenarioRunRequest,
    ValidationStatus
)


class TestGate95TelemetrySemantics(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.catalog = NetSpoutCatalog()
        cls.runner = ScenarioRunner()
        cls.allowed_fidelity_badges = {"NATIVE TRANSPORT", "MODELED PAYLOAD", "SYNTHETIC"}

    def test_01_all_scenarios_have_telemetry_semantics_metadata(self):
        """Verify that all 29 scenarios have the 5 Gate 9.5 telemetry semantics fields."""
        scenarios = self.catalog.list_scenarios()
        self.assertEqual(len(scenarios), 29, f"Expected 29 scenarios, found {len(scenarios)}")

        for sc in scenarios:
            sc_id = sc.get("id")
            with self.subTest(scenario=sc_id):
                self.assertIn("telemetry_model", sc, f"Missing telemetry_model in {sc_id}")
                self.assertIsNotNone(sc["telemetry_model"], f"telemetry_model is None in {sc_id}")

                self.assertIn("transport_protocol", sc, f"Missing transport_protocol in {sc_id}")
                self.assertIsNotNone(sc["transport_protocol"], f"transport_protocol is None in {sc_id}")

                self.assertIn("splunk_storage", sc, f"Missing splunk_storage in {sc_id}")
                self.assertIsNotNone(sc["splunk_storage"], f"splunk_storage is None in {sc_id}")

                self.assertIn("fidelity_badge", sc, f"Missing fidelity_badge in {sc_id}")
                self.assertIn(sc["fidelity_badge"], self.allowed_fidelity_badges,
                              f"Invalid fidelity_badge '{sc['fidelity_badge']}' in {sc_id}")

    def test_02_openconfig_mdt_streaming_semantics(self):
        """Verify OpenConfig MDT scenario has precise modeled payload semantics."""
        oc = self.catalog.get_scenario("openconfig_mdt_streaming")
        self.assertIsNotNone(oc, "openconfig_mdt_streaming scenario not found in catalog")

        # Telemetry model
        self.assertEqual(oc.get("telemetry_model"), "OpenConfig / MDT")

        # Transport protocol must be Splunk HEC (NOT native gRPC / gNMI)
        self.assertEqual(oc.get("transport_protocol"), "Splunk HEC")
        self.assertNotIn("grpc", oc.get("transport_protocol", "").lower())

        # Splunk storage destination: Both metric and event indices
        storage = oc.get("splunk_storage", "")
        self.assertIn("cisco_mdt_metrics", storage)
        self.assertIn("idx_network_ops", storage)

        # Fidelity badge MUST be MODELED PAYLOAD (never NATIVE TRANSPORT or NATIVE STREAMING)
        self.assertEqual(oc.get("fidelity_badge"), "MODELED PAYLOAD")
        self.assertNotEqual(oc.get("fidelity_badge"), "NATIVE TRANSPORT")

        # Educational callout note must be present and clarify HEC delivery
        notes = oc.get("telemetry_notes", "")
        self.assertTrue(len(notes) > 20, "telemetry_notes must provide educational explanation")
        self.assertIn("OpenConfig/MDT", notes)
        self.assertIn("HEC", notes)
        self.assertIn("gNMI/gRPC", notes)

    def test_03_topology_preset_description_updated(self):
        """Verify the OpenConfig preset topology description does not claim native gNMI dial-out."""
        import json
        with open("catalog/topologies.json", "r") as f:
            topologies = json.load(f)
        
        oc_topos = [t for t in topologies if t["id"] == "openconfig_core"]
        self.assertTrue(len(oc_topos) > 0, "openconfig_core topology must exist")
        oc_topo = oc_topos[0]
        # Description should not claim native streaming gRPC
        self.assertNotIn("native gRPC", oc_topo.get("description", ""))

    def test_04_wave1_acceptance_maturity_promotions(self):
        """Verify maturity distribution following Wave 1 Independent Acceptance."""
        # 1. mixed_sase_degradation -> GOLDEN_PATH_CERTIFIED
        sase = self.catalog.get_scenario("mixed_sase_degradation")
        self.assertEqual(sase.get("maturity"), "GOLDEN_PATH_CERTIFIED",
                         "mixed_sase_degradation should be promoted to GOLDEN_PATH_CERTIFIED")

        # 2. sql_injection -> GOLDEN_PATH_CERTIFIED
        sqli = self.catalog.get_scenario("sql_injection")
        self.assertEqual(sqli.get("maturity"), "GOLDEN_PATH_CERTIFIED",
                         "sql_injection should be promoted to GOLDEN_PATH_CERTIFIED")

        # 3. openconfig_mdt_streaming -> E2E_VALIDATED
        oc = self.catalog.get_scenario("openconfig_mdt_streaming")
        self.assertIn(oc.get("maturity"), ["E2E_VALIDATED", "GOLDEN_PATH_CERTIFIED"])

        # 4. GP01-GP04 Golden Paths preserved
        golden_paths = [
            "cisco_sdwan_brownout",
            "cisco_campus_rogue",
            "cisco_aci_microburst",
            "mixed_edge_breach"
        ]
        for gp_id in golden_paths:
            gp = self.catalog.get_scenario(gp_id)
            self.assertEqual(gp.get("maturity"), "GOLDEN_PATH_CERTIFIED",
                             f"Original Golden Path {gp_id} must remain GOLDEN_PATH_CERTIFIED")

    def test_05_backend_api_use_cases_serialization(self):
        """Verify backend /api/use-cases returns telemetry semantics for every use case."""
        from backend.app.main import list_catalog_use_cases
        resp = list_catalog_use_cases()
        self.assertIn("use_cases", resp)
        use_cases = resp["use_cases"]
        self.assertTrue(len(use_cases) >= 29)

        oc_uc = [u for u in use_cases if u.get("scenario_id") == "openconfig_mdt_streaming"]
        self.assertEqual(len(oc_uc), 1, "openconfig_mdt_streaming use case not found in API response")
        oc = oc_uc[0]

        self.assertEqual(oc.get("telemetry_model"), "OpenConfig / MDT")
        self.assertEqual(oc.get("transport_protocol"), "Splunk HEC")
        self.assertIn("cisco_mdt_metrics", oc.get("splunk_storage", ""))
        self.assertEqual(oc.get("fidelity_badge"), "MODELED PAYLOAD")
        self.assertIn("HEC rather than a native gNMI/gRPC session", oc.get("telemetry_notes", ""))

    def test_06_golden_paths_regression_execution(self):
        """Verify execution of all 6 Golden Paths passes validation completely with GOLDEN_PATH_CERTIFIED maturity."""
        golden_scenarios = [
            "cisco_sdwan_brownout",
            "cisco_campus_rogue",
            "cisco_aci_microburst",
            "mixed_edge_breach",
            "mixed_sase_degradation",
            "sql_injection"
        ]

        for sid in golden_scenarios:
            with self.subTest(golden_scenario=sid):
                req = ScenarioRunRequest(
                    scenario_id=sid,
                    seed=200,
                    time_mode="TEST"
                )
                manifest = self.runner.run_scenario(req)
                self.assertIsNotNone(manifest)
                self.assertEqual(manifest.overall_validation, "PASS",
                                 f"{sid} validation failed: {[f'{r.rule_id}: {r.message}' for r in manifest.validation_results if r.status != ValidationStatus.PASS]}")
                self.assertEqual(manifest.scenario_maturity, "GOLDEN_PATH_CERTIFIED",
                                 f"{sid} scenario maturity expected GOLDEN_PATH_CERTIFIED, got {manifest.scenario_maturity}")
                self.assertTrue(manifest.total_events_generated > 0,
                                f"{sid} produced zero records")
                for vr in manifest.validation_results:
                    self.assertEqual(
                        vr.status,
                        ValidationStatus.PASS,
                        f"Scenario {sid} rule {vr.rule_id} failed: {vr.message}"
                    )


if __name__ == "__main__":
    unittest.main()

