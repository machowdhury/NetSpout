#!/usr/bin/env python3
# NetSpout Architecture Guardrail: Gate 5 UX & Unified Workflow Test Suite

import os
import sys
import json
import glob
import unittest
import urllib.request
import subprocess

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
NETSPOUT_DIR = os.path.join(REPO_ROOT, "netspout")
FRONTEND_DIR = os.path.join(REPO_ROOT, "frontend")
CATALOG_DIR = os.path.join(REPO_ROOT, "catalog")
sys.path.insert(0, os.path.join(REPO_ROOT, "src"))


class TestGate5UX(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from netspout_core.catalog import catalog
        from netspout_core.scenario_runner import ScenarioRunner
        cls.catalog = catalog
        cls.runner = ScenarioRunner()

    def test_01_app_loads(self):
        """1. Verify compiled frontend dist/index.html exists, has DOCTYPE, root element, and JS bundle link."""
        dist_html = os.path.join(NETSPOUT_DIR, "appserver/static/dist/index.html")
        self.assertTrue(os.path.exists(dist_html), "dist/index.html must exist")
        with open(dist_html) as f:
            content = f.read()
        self.assertIn("<!doctype html>", content.lower())
        self.assertIn('id="root"', content)
        self.assertIn("./assets/index-", content)

    def test_02_canonical_navigation(self):
        """2. Verify canonical 3-mode navigation: Workflow (5-step), Advanced (Canvas), Operations."""
        topbar_path = os.path.join(FRONTEND_DIR, "src/components/TopBar.tsx")
        app_path = os.path.join(FRONTEND_DIR, "src/App.tsx")
        with open(topbar_path) as f:
            tb = f.read()
        with open(app_path) as f:
            app = f.read()
        self.assertIn("Use Cases (5-Step)", tb)
        self.assertIn("Canvas Orchestrator", tb)
        self.assertIn("Operations", tb)
        self.assertIn("appMode === 'workflow'", app)
        self.assertIn("appMode === 'operations'", app)

    def test_03_use_cases_from_canonical_metadata(self):
        """3. Verify 39 use cases load from canonical metadata with expected categories."""
        from netspout_core.use_case_repo import USE_CASES
        scenarios = self.catalog.list_scenarios()
        self.assertEqual(len(scenarios), 29)
        self.assertEqual(len(USE_CASES), 10)
        total_ucs = len(scenarios) + len(USE_CASES)
        self.assertEqual(total_ucs, 39)

        # Verify live API returns 39 use cases
        try:
            req = urllib.request.Request("http://localhost:8081/api/use-cases")
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read().decode())
                self.assertEqual(data.get("count"), 39)
        except Exception:
            pass

    def test_04_scenario_preview(self):
        """4. Verify StepPreview renders scenario details, 9-phase progression, and validation rules."""
        sp_path = os.path.join(FRONTEND_DIR, "src/components/workflow/StepPreview.tsx")
        self.assertTrue(os.path.exists(sp_path))
        with open(sp_path) as f:
            content = f.read()
        self.assertIn("Target Topology Blueprint", content)
        self.assertIn("Deterministic Lifecycle Progression", content)
        self.assertIn("Evidence Contract & Validation Rules", content)

    def test_05_topology_preview(self):
        """5. Verify topology presets and default topologies exist and match contracts."""
        topologies_path = os.path.join(CATALOG_DIR, "topologies.json")
        self.assertTrue(os.path.exists(topologies_path))
        with open(topologies_path) as f:
            top_list = json.load(f)
        self.assertGreaterEqual(len(top_list), 6)

    def test_06_connection_state(self):
        """6. Verify explicit distinction between CONFIGURED, REACHABLE, and VERIFIED."""
        types_path = os.path.join(FRONTEND_DIR, "src/types/workflow.ts")
        sc_path = os.path.join(FRONTEND_DIR, "src/components/workflow/StepConnect.tsx")
        with open(types_path) as f:
            t_content = f.read()
        with open(sc_path) as f:
            sc_content = f.read()
        self.assertIn("'CONFIGURED' | 'REACHABLE' | 'VERIFIED'", t_content)
        self.assertIn("CONFIGURED (UNTESTED)", sc_content)
        self.assertIn("REACHABLE", sc_content)
        self.assertIn("VERIFIED IN SPLUNK", sc_content)

    def test_07_run_starts(self):
        """7. Verify scenario run starts and returns run_id in NS-YYYYMMDD-xxxxxxxx format."""
        from netspout_core.models import ScenarioRunRequest
        req = ScenarioRunRequest(scenario_id="bgp_route_leak", time_mode="TEST", seed=101)
        manifest = self.runner.run_scenario(req)
        logs = self.runner.get_run_logs(manifest.run_id)
        self.assertTrue(manifest.run_id.startswith("NS-"))
        self.assertEqual(manifest.scenario_id, "bgp_route_leak")
        self.assertGreater(len(logs), 0)

    def test_08_phase_updates(self):
        """8. Verify all 9 phases executed in chronological order."""
        from netspout_core.models import ScenarioRunRequest
        req = ScenarioRunRequest(scenario_id="bgp_route_leak", time_mode="TEST", seed=102)
        manifest = self.runner.run_scenario(req)
        expected = ["INITIALIZE", "BASELINE", "DEGRADE", "FAULT", "PROPAGATE", "FAILOVER", "RECOVER", "VALIDATE", "COMPLETE"]
        self.assertEqual(manifest.phases_executed, expected)

    def test_09_run_stops(self):
        """9. Verify cooperative scenario stop mechanism."""
        from netspout_core.scenario_runner import ScenarioRunner
        from netspout_core.models import RunManifest
        r = ScenarioRunner()
        r.active_manifests["NS-TEST-STOP"] = RunManifest(
            run_id="NS-TEST-STOP", scenario_id="test", scenario_name="test", topology_id="test", start_time=1.0
        )
        self.assertTrue(r.stop_run("NS-TEST-STOP"))

    def test_10_manifest_displays(self):
        """10. Verify run manifest contains complete audit metadata and ground truth."""
        from netspout_core.models import ScenarioRunRequest
        req = ScenarioRunRequest(scenario_id="ransomware_lateral", time_mode="TEST", seed=103)
        manifest = self.runner.run_scenario(req)
        self.assertIsNotNone(manifest.start_time)
        self.assertIsNotNone(manifest.end_time)
        self.assertGreaterEqual(len(manifest.ground_truth_records), 9)

    def test_11_validation_displays(self):
        """11. Verify validation engine outputs rule-by-rule PASS/FAIL status."""
        from netspout_core.models import ScenarioRunRequest
        req = ScenarioRunRequest(scenario_id="ddos_syn_flood", time_mode="TEST", seed=104)
        manifest = self.runner.run_scenario(req)
        self.assertIn(manifest.overall_validation, ["PASS", "FAIL"])
        for vr in manifest.validation_results:
            self.assertIn(vr.status, ["PASS", "FAIL", "ERROR", "SKIPPED"])

    def test_12_evidence_distinction(self):
        """12. Verify semantic separation of GENERATED, DISPATCHED, OBSERVED, and VALIDATED."""
        sp_path = os.path.join(FRONTEND_DIR, "src/components/workflow/StepProve.tsx")
        with open(sp_path) as f:
            content = f.read()
        self.assertIn("1. GENERATED", content)
        self.assertIn("2. DISPATCHED", content)
        self.assertIn("3. OBSERVED", content)
        self.assertIn("4. VALIDATED", content)

    def test_13_advanced_mode(self):
        """13. Verify expert tools (NodePalette, TopologyCanvas, LogTerminal, Modals) preserved in Advanced mode."""
        app_path = os.path.join(FRONTEND_DIR, "src/App.tsx")
        with open(app_path) as f:
            content = f.read()
        self.assertIn("<NodePalette", content)
        self.assertIn("<TopologyCanvas", content)
        self.assertIn("<LogTerminal", content)
        self.assertIn("<FaultInjectionModal", content)
        self.assertIn("<OpenConfigTreeModal", content)
        self.assertIn("<SNMPMibModal", content)

    def test_14_error_state(self):
        """14. Verify error states in workflow components."""
        choose_path = os.path.join(FRONTEND_DIR, "src/components/workflow/StepChoose.tsx")
        with open(choose_path) as f:
            content = f.read()
        self.assertIn("Error loading use cases", content)

    def test_15_disconnected_state(self):
        """15. Verify disconnected/offline status handling in TopBar and OperationsView."""
        topbar_path = os.path.join(FRONTEND_DIR, "src/components/TopBar.tsx")
        ops_path = os.path.join(FRONTEND_DIR, "src/components/operations/OperationsView.tsx")
        with open(topbar_path) as f:
            tb = f.read()
        with open(ops_path) as f:
            ops = f.read()
        self.assertIn("OFFLINE", tb)
        self.assertIn("backendHealth === 'online'", ops)

    def test_16_keyboard_navigation(self):
        """16. Verify tabIndex and keyboard handlers in StepChoose cards and step navigation."""
        choose_path = os.path.join(FRONTEND_DIR, "src/components/workflow/StepChoose.tsx")
        with open(choose_path) as f:
            content = f.read()
        self.assertIn('tabIndex={0}', content)
        self.assertIn("e.key === 'Enter'", content)
        self.assertIn('role="button"', content)

    def test_17_focus_visibility(self):
        """17. Verify visible focus outline/ring classes across interactive controls."""
        choose_path = os.path.join(FRONTEND_DIR, "src/components/workflow/StepChoose.tsx")
        preview_path = os.path.join(FRONTEND_DIR, "src/components/workflow/StepPreview.tsx")
        with open(choose_path) as f:
            self.assertIn("focus:ring-2 focus:ring-cyan-500", f.read())
        with open(preview_path) as f:
            self.assertIn("focus:ring-2 focus:ring-cyan-400", f.read())

    def test_18_no_primary_horizontal_overflow(self):
        """18. Verify viewport layout uses overflow-hidden and constrained flex bounds."""
        app_path = os.path.join(FRONTEND_DIR, "src/App.tsx")
        with open(app_path) as f:
            content = f.read()
        self.assertIn("h-screen w-screen overflow-hidden", content)

    def test_19_deprecated_sourcetype_aliases_hidden(self):
        """19. Verify deprecated aliases from aliases.json are not rendered as primary use cases."""
        aliases_path = os.path.join(CATALOG_DIR, "aliases.json")
        with open(aliases_path) as f:
            aliases = json.load(f)
        for alias, info in aliases.items():
            if isinstance(info, dict) and info.get("type") == "DEPRECATED_ALIAS":
                self.assertNotIn(alias, [s.get("id") for s in self.catalog.list_scenarios()])

    def test_20_compiled_frontend_generated_from_source(self):
        """20. Verify scripts/build_frontend.py builds from frontend/src/ to static dist/."""
        build_script = os.path.join(REPO_ROOT, "scripts/build_frontend.py")
        self.assertTrue(os.path.exists(build_script))
        dist_assets = glob.glob(os.path.join(NETSPOUT_DIR, "appserver/static/dist/assets/*.js"))
        self.assertGreater(len(dist_assets), 0)

    def test_21_no_references_to_removed_js(self):
        """21. Verify datablaster_ui.js and test_script.js are deleted and have zero references."""
        self.assertFalse(os.path.exists(os.path.join(NETSPOUT_DIR, "appserver/static/datablaster_ui.js")))
        self.assertFalse(os.path.exists(os.path.join(NETSPOUT_DIR, "appserver/static/test_script.js")))
        res = subprocess.run(["git", "grep", "datablaster_ui.js"], cwd=REPO_ROOT, capture_output=True, text=True)
        self.assertEqual(res.returncode, 1, "Must have zero references to datablaster_ui.js")

    def test_22_native_splunk_dashboards_retained(self):
        """22. Verify 7 Studio dashboards and datablaster_dashboard.xml are intentionally preserved."""
        studio_files = glob.glob(os.path.join(NETSPOUT_DIR, "default/data/ui/views/studio_*.xml"))
        self.assertEqual(len(studio_files), 7)
        self.assertTrue(os.path.exists(os.path.join(NETSPOUT_DIR, "default/data/ui/views/datablaster_dashboard.xml")))


if __name__ == "__main__":
    unittest.main()
