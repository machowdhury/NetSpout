"""Phase 4E Use Case Explorer: taxonomy, truthful maturity/readiness, workflow gating, saved-search enablement.

Hermetic: no live Splunk. The saved-search client is exercised against a local HTTP stub that mimics the
Splunk REST contract (create, 409 on duplicate, entity read-back).
"""
import json
import os
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
for sub in ("src", "backend"):
    p = os.path.join(REPO_ROOT, sub)
    if p not in sys.path:
        sys.path.insert(0, p)

from netspout_core.release_candidate import ReleaseCandidateConfiguration
from netspout_core.security_content_lab import (
    SUPPORTED_RUNTIME_DETECTIONS,
    DetectionValidationOrchestrator,
    SecurityContentCatalog,
)
from netspout_core.use_case_explorer import DEMO_READY_TIERS, UseCaseExplorer, load_taxonomy, maturity_tier

APPROVED_ID = next(iter(SUPPORTED_RUNTIME_DETECTIONS))
SCEN = [
    {"scenario_id": "S-GOLD", "title": "Gold", "description": "d", "domain": "X", "category": "C",
     "source_ids": ["src1"], "runnable": True, "scenario_maturity": "GOLDEN"},
    {"scenario_id": "S-BLOCKED", "title": "Blocked", "description": "d", "domain": "X", "category": "C",
     "source_ids": ["src1"], "runnable": False, "blocked_reason": "no contract", "scenario_maturity": "SPLUNK_VALIDATED"},
]
CATALOG = [
    {"id": "payment_processing_degradation", "name": "Payments", "description": "p", "category": "INDUSTRY_VERTICAL",
     "maturity": "E2E_VALIDATED", "vendor_scope": ["cisco"], "sourcetypes": ["st:a"]},
    {"id": "sleepy", "name": "Sleepy", "description": "p", "category": "NETWORK_OPERATIONS", "maturity": "CONTRACTED"},
]
DASH = [{"dashboard_id": "scenario-s-gold", "scenario_id": "S-GOLD", "runtime_scenario_id": "S-GOLD", "industry_id": None,
         "scenario_maturity": "GOLDEN", "dashboard_maturity": "NOT_STARTED", "state": "ELIGIBLE", "reasons": []}]


def make_explorer(validations=None, taxonomy=None):
    return UseCaseExplorer(
        taxonomy=taxonomy or load_taxonomy(),
        generation_scenarios=SCEN,
        generation_sources=[{"source_id": "src1", "vendor": "Cisco"}],
        dashboards=DASH,
        catalog_scenarios=CATALOG,
        security_catalog=SecurityContentCatalog(),
        validations=lambda: validations or [],
        runtime_approved_detections=SUPPORTED_RUNTIME_DETECTIONS,
    )


class TestTaxonomy(unittest.TestCase):
    def test_eighteen_unique_industries_and_valid_mappings(self):
        tax = load_taxonomy()
        self.assertEqual(len(tax["industries"]), 18)
        self.assertEqual(tax["taxonomy_status"], "PROPOSED_DEFAULT")
        ids = {i["id"] for i in tax["industries"]}
        for m in tax["scenario_industries"]:
            self.assertIn(m["basis"], ("industry_pack", "editorial"))
            self.assertTrue(set(m["industries"]) <= ids)

    def test_unknown_industry_in_mapping_is_rejected(self):
        tax = load_taxonomy()
        tax["scenario_industries"].append({"scenario_id": "x", "basis": "editorial", "industries": ["nope"]})
        tmp = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
        json.dump(tax, tmp)
        tmp.close()
        from pathlib import Path
        with self.assertRaises(ValueError):
            load_taxonomy(Path(tmp.name))
        os.unlink(tmp.name)

    def test_industry_counts_are_computed_and_empty_industries_are_zero(self):
        rows = {r["id"]: r for r in make_explorer().industries()}
        self.assertEqual(len(rows), 18)
        self.assertEqual(rows["financial-services"]["scenarios_total"], 1)
        self.assertEqual(rows["financial-services"]["bases"], ["industry_pack"])
        self.assertEqual(rows["insurance"]["scenarios_total"], 0)


class TestOperationalTruthfulness(unittest.TestCase):
    def setUp(self):
        self.ex = make_explorer()
        self.ops = {e["scenario_id"]: e for e in self.ex.search(kind="operational", limit=200)["items"]}

    def test_maturity_tiers_follow_raw_value(self):
        self.assertEqual(maturity_tier("GOLDEN_PATH_CERTIFIED"), "CERTIFIED")
        self.assertEqual(maturity_tier("CONTRACTED"), "CONTRACTED")
        self.assertEqual(maturity_tier("something-new"), "NOT_ESTABLISHED")
        self.assertEqual(self.ops["sleepy"]["maturity"]["tier"], "CONTRACTED")
        self.assertFalse(self.ops["sleepy"]["demo_ready"])

    def test_demo_ready_requires_runnable_and_strong_tier(self):
        for e in self.ops.values():
            if e["demo_ready"]:
                self.assertTrue(e["runnable"])
                self.assertIn(e["maturity"]["tier"], DEMO_READY_TIERS)
        self.assertTrue(self.ops["S-GOLD"]["demo_ready"])
        self.assertFalse(self.ops["S-BLOCKED"]["demo_ready"])  # validated but not runnable

    def test_dashboard_step_never_claims_readiness(self):
        steps = {s["step"]: s for s in self.ops["S-GOLD"]["workflow"]}
        self.assertTrue(steps["DASHBOARD"]["available"])
        self.assertEqual(self.ops["S-GOLD"]["dashboard"]["dashboard_maturity"], "NOT_STARTED")
        self.assertFalse({s["step"]: s for s in self.ops["sleepy"]["workflow"]}["DASHBOARD"]["available"])

    def test_runner_scenarios_do_not_get_a_dashboard_step_without_binding(self):
        self.assertIsNone(self.ops["payment_processing_degradation"]["dashboard"])

    def test_blocked_scenario_blocks_generation_steps_with_reason(self):
        steps = {s["step"]: s for s in self.ops["S-BLOCKED"]["workflow"]}
        for name in ("CONFIGURE", "GENERATE", "INGEST", "VERIFY", "DASHBOARD"):
            self.assertFalse(steps[name]["available"])
        self.assertEqual(steps["GENERATE"]["blocked_reason"], "no contract")

    def test_workflow_order_is_the_operational_contract(self):
        self.assertEqual([s["step"] for s in self.ops["S-GOLD"]["workflow"]],
                         ["SELECT", "CONFIGURE", "GENERATE", "INGEST", "VERIFY", "DASHBOARD"])

    def test_search_and_filters(self):
        self.assertEqual([e["scenario_id"] for e in self.ex.search(q="payments")["items"]],
                         ["payment_processing_degradation"])
        self.assertEqual(self.ex.search(industry="financial-services")["total"], 1)
        self.assertEqual(self.ex.search(demo_ready=True, kind="operational")["total"], 2)
        self.assertEqual(self.ex.search(vendor="cisco", kind="operational")["total"], 3)  # S-GOLD, S-BLOCKED ("Cisco") + payments ("cisco")


class TestSecurityReadiness(unittest.TestCase):
    def test_only_approved_replayable_story_is_runtime_approved(self):
        res = make_explorer().search(kind="security", readiness="RUNTIME_APPROVED")
        self.assertEqual(res["total"], 1)
        story = make_explorer().get(res["items"][0]["entry_id"])
        approved = [d for d in story["detections"] if d["runtime_approved"]]
        self.assertEqual([d["content_id"] for d in approved], [APPROVED_ID])
        self.assertTrue(approved[0]["replay_datasets"])
        self.assertEqual(story["readiness"]["production_detection_efficacy"], "NOT_ESTABLISHED")
        self.assertEqual([s["step"] for s in story["workflow"]],
                         ["SELECT", "PREREQUISITES", "GENERATE", "INGEST", "ENABLE_DETECTION", "VERIFY"])
        self.assertTrue(all(s["available"] for s in story["workflow"]))
        # Security stories have no dashboard step.
        self.assertNotIn("DASHBOARD", [s["step"] for s in story["workflow"]])

    def test_replay_only_story_blocks_enable_and_verify(self):
        item = make_explorer().search(kind="security", readiness="REPLAY_ONLY", limit=1)["items"][0]
        steps = {s["step"]: s for s in item["workflow"]}
        self.assertTrue(steps["INGEST"]["available"])
        self.assertFalse(steps["ENABLE_DETECTION"]["available"])
        self.assertFalse(steps["VERIFY"]["available"])

    def test_verified_requires_stored_positive_evidence(self):
        before = make_explorer().search(kind="security", readiness="DETECTION_VERIFIED")["total"]
        self.assertEqual(before, 0)
        evidence = [{"status": "EXECUTED_MATCHED", "detection_id": APPROVED_ID}]  # not a validated status
        self.assertEqual(make_explorer(evidence).search(kind="security", readiness="DETECTION_VERIFIED")["total"], 0)
        evidence = [{"status": "POSITIVE_CASE_VALIDATED", "detection_id": APPROVED_ID}]
        self.assertEqual(make_explorer(evidence).search(kind="security", readiness="DETECTION_VERIFIED")["total"], 1)

    def test_security_entries_have_no_industry_claims(self):
        self.assertTrue(all(not e["industries"] for e in make_explorer().search(kind="security", limit=200)["items"]))

    def test_prerequisites_report_local_state_only_and_no_secrets(self):
        ex = make_explorer()
        entry = ex.search(kind="security", readiness="RUNTIME_APPROVED")["items"][0]["entry_id"]
        unconfigured = ex.prerequisites(entry, {"configured": False, "secret_state": {}}, index="main")
        self.assertFalse(unconfigured["ready"])
        self.assertEqual(unconfigured["live_reachability"], "NOT_TESTED")
        ready = ex.prerequisites(entry, {"configured": True, "indexes": ["main"],
                                         "secret_state": {"hec_token_configured": True, "search_secret_configured": True}},
                                 index="main")
        self.assertTrue(ready["ready"])
        self.assertNotIn("token", json.dumps(ready).replace("token_configured", ""))
        with self.assertRaises(KeyError):
            ex.prerequisites("sec:missing", {})


class TestEnableDetection(unittest.TestCase):
    def test_prepare_enable_is_unscoped_and_only_for_approved(self):
        orch = DetectionValidationOrchestrator(SecurityContentCatalog(), lambda q: ([], None))
        prepared = orch.prepare_enable(APPROVED_ID, "main")
        self.assertNotIn("netspout_run_id", prepared["spl"])
        self.assertIn('index="main"', prepared["spl"])
        self.assertRegex(prepared["saved_search_name"], r"^NetSpout - [A-Za-z0-9 _.\-]+$")
        other = next(d["content_id"] for d in SecurityContentCatalog().document["detections"]
                     if d["content_id"] not in SUPPORTED_RUNTIME_DETECTIONS)
        with self.assertRaises(ValueError):
            orch.prepare_enable(other, "main")
        with self.assertRaises(ValueError):
            orch.prepare_enable(APPROVED_ID, "bad index!")

    def test_run_scoped_form_is_unchanged(self):
        orch = DetectionValidationOrchestrator(SecurityContentCatalog(), lambda q: ([], None))
        query, _ = orch.prepare_query(SecurityContentCatalog().get_detection(APPROVED_ID), "run-1", "main")
        self.assertIn('netspout_run_id="run-1"', query)


class _Splunk(BaseHTTPRequestHandler):
    store = {}
    mode = "ok"
    seen_auth = []

    def log_message(self, *a):
        pass

    def _send(self, code, body):
        data = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        type(self).seen_auth.append(self.headers.get("Authorization"))
        form = {k: v[0] for k, v in parse_qs(self.rfile.read(int(self.headers["Content-Length"])).decode()).items()}
        if self.mode == "forbidden":
            return self._send(403, {})
        path = urlparse(self.path).path
        if path.endswith("/saved/searches"):
            if form["name"] in self.store:
                return self._send(409, {})
            self.store[form["name"]] = dict(form)
            return self._send(201, {})
        name = path.rsplit("/", 1)[1].replace("%20", " ")
        self.store[name].update(form)
        self._send(200, {})

    def do_GET(self):
        name = urlparse(self.path).path.rsplit("/", 1)[1].replace("%20", " ")
        content = dict(self.store[name])
        if self.mode == "readback_disabled":
            content["disabled"] = "1"
        self._send(200, {"entry": [{"content": content}]})


class TestSavedSearchClient(unittest.TestCase):
    def setUp(self):
        _Splunk.store, _Splunk.mode, _Splunk.seen_auth = {}, "ok", []
        self.server = HTTPServer(("127.0.0.1", 0), _Splunk)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.shutdown)
        tmp = tempfile.mkdtemp()
        with open(os.path.join(tmp, "connection.json"), "w") as f:
            json.dump({"search_url": f"http://127.0.0.1:{self.server.server_port}/services/search/jobs/export",
                       "auth_method": "HEC_TOKEN_AND_SPLUNK_TOKEN", "indexes": ["main"]}, f)
        self.cfg = ReleaseCandidateConfiguration(config_dir=tmp)
        self.cfg.secrets.search_secret = "test-secret-not-real"

    def test_create_then_update_and_readback(self):
        first = self.cfg.upsert_saved_search("NetSpout - T", "search index=main | head 1")
        self.assertEqual((first["status"], first["enabled"], first["read_back"]), ("ENABLED", True, True))
        second = self.cfg.upsert_saved_search("NetSpout - T", "search index=main | head 2")  # 409 -> update
        self.assertTrue(second["enabled"])
        self.assertEqual(_Splunk.store["NetSpout - T"]["search"], "search index=main | head 2")
        self.assertEqual(_Splunk.store["NetSpout - T"]["is_scheduled"], "1")
        self.assertNotIn("action.email", _Splunk.store["NetSpout - T"])  # no alert actions
        self.assertTrue(all(a == "Bearer test-secret-not-real" for a in _Splunk.seen_auth))

    def test_forbidden_is_reported_not_enabled(self):
        _Splunk.mode = "forbidden"
        res = self.cfg.upsert_saved_search("NetSpout - T", "search index=main")
        self.assertEqual((res["status"], res["enabled"], res["error"]), ("FAILED", False, "HTTP 403"))
        self.assertNotIn("test-secret-not-real", json.dumps(res))

    def test_enabled_requires_readback_not_request(self):
        _Splunk.mode = "readback_disabled"
        res = self.cfg.upsert_saved_search("NetSpout - T", "search index=main")
        self.assertEqual((res["status"], res["enabled"]), ("NOT_ENABLED", False))

    def test_not_configured_and_input_validation(self):
        bare = ReleaseCandidateConfiguration(config_dir=tempfile.mkdtemp())
        self.assertEqual(bare.upsert_saved_search("n", "s")["status"], "NOT_CONFIGURED")
        with self.assertRaises(ValueError):
            self.cfg.upsert_saved_search("bad/name", "s")
        with self.assertRaises(ValueError):
            self.cfg.upsert_saved_search("ok", "s", cron="; rm -rf")


class TestExplorerApi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from fastapi.testclient import TestClient
        from app.main import app
        cls.client = TestClient(app)

    def test_summary_and_search_contract(self):
        body = self.client.get("/api/explorer/summary").json()
        self.assertEqual(len(body["industries"]), 18)
        self.assertEqual(body["security"]["total"], 365)
        self.assertEqual(body["taxonomy"]["status"], "PROPOSED_DEFAULT")
        res = self.client.get("/api/explorer/entries", params={"q": "dns", "limit": 5}).json()
        self.assertGreater(res["total"], 0)
        self.assertLessEqual(len(res["items"]), 5)

    def test_bad_inputs(self):
        self.assertEqual(self.client.get("/api/explorer/entries", params={"kind": "bogus"}).status_code, 422)
        self.assertEqual(self.client.get("/api/explorer/entries/nope").status_code, 404)
        self.assertEqual(self.client.get("/api/explorer/entries/sec:x/prerequisites", params={"index": "a b"}).status_code, 422)

    def test_mutating_routes_refuse_without_connection_center(self):
        # Backend default in tests: Connection Center is unconfigured, so nothing may reach Splunk.
        r = self.client.post(f"/api/explorer/detections/{APPROVED_ID}/enable", json={"index": "main"})
        self.assertIn(r.status_code, (403, 409))
        r = self.client.post("/api/explorer/security/observe", json={"index": "main", "run_id": "r1"})
        self.assertIn(r.status_code, (403, 409))


if __name__ == "__main__":
    unittest.main()
