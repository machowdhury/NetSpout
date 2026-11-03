"""Customer documentation stays true to its sources: numbers match the coverage data, generated catalogs are current, links resolve,
and the install guide never sends a customer to the engine port or to a hard-coded credential."""
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("gen_docs", ROOT / "scripts" / "generate_customer_docs.py")
gen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gen)
_, S = gen.load("scenario_coverage.json")
_, T = gen.load("sourcetype_coverage.json")


def test_generated_catalogs_are_current():
    assert (ROOT / "docs" / "SCENARIOS.md").read_text() == gen.scenarios_doc(S, T)
    assert (ROOT / "docs" / "TELEMETRY_COVERAGE.md").read_text() == gen.telemetry_doc(S, T)


def test_readme_numbers_match_the_data():
    readme = (ROOT / "README.md").read_text()
    runnable = sum(r["runnable"] for r in S)
    assert "**%d runnable scenarios** (%d defined)" % (runnable, len(S)) in readme
    assert "**%d sourcetypes from %d vendors**" % (len(T), len({t["vendor_id"] for t in T})) in readme
    assert "**%d Dashboard Studio dashboards**" % sum(1 for r in S if r.get("dashboard")) in readme


def test_every_listed_dashboard_exists():
    views = ROOT / "netspout" / "default" / "data" / "ui" / "views"
    assert all((views / (r["dashboard"] + ".xml")).exists() for r in S if r["runnable"] and r.get("dashboard"))


def test_links_and_paths_resolve():
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "check_readme_links.py"), "README.md", "docs/INSTALL.md", "docs/QUICKSTART.md", "docs/SECURITY.md", "docs/SCENARIOS.md", "docs/TELEMETRY_COVERAGE.md"],
                       cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


def test_customer_docs_do_not_ship_credentials_or_the_engine_port():
    for name in ("README.md", "docs/INSTALL.md", "docs/QUICKSTART.md", "docs/SECURITY.md"):
        text = (ROOT / name).read_text()
        assert not re.search(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", text), name   # no HEC token GUID
        assert not re.search(r"(?i)password\s*[:=]\s*\S*[A-Za-z0-9]{6,}", text.replace("SPLUNK_PASSWORD", "")), name
    install = (ROOT / "docs" / "INSTALL.md").read_text()
    assert "localhost:8081" not in install and "http://127.0.0.1:8081" not in install


def test_activation_audit_accounts_for_every_non_runnable_scenario():
    audit = json.loads((ROOT / "docs" / "reference" / "scenario_activation_audit.json").read_text())
    non = [r for r in S if not r["runnable"]]
    assert audit["non_runnable"] == len(non) == len(audit["rows"]) == sum(audit["classes"].values())
    assert {a["scenario_id"] for a in audit["rows"]} == {r["scenario_id"] for r in non}      # nothing missing, nothing runnable listed
    assert all(a["class"] in "ABCD" and a["reason"] for a in audit["rows"])
    assert audit["defined"] == len(S) and audit["runnable"] == len(S) - len(non)


def test_scenarios_doc_describes_every_scenario_without_placeholder_text():
    text = (ROOT / "docs" / "SCENARIOS.md").read_text()
    assert all("`%s`" % r["scenario_id"] in text for r in S)                                  # every defined scenario appears
    for banned in ("Cataloged candidate", "Not executable."):
        assert banned not in text
    assert not __import__("re").search(r"Documented \w+ candidate", text)
    assert "dashboard_views" not in text


def test_dashboard_accounting_matches_the_views():
    audit = json.loads((ROOT / "docs" / "reference" / "scenario_activation_audit.json").read_text())["dashboards"]
    views = list((ROOT / "netspout" / "default" / "data" / "ui" / "views").glob("pf_*.xml"))
    assert audit["dashboard_views"] == len(views) == sum(1 for r in S if r.get("dashboard"))
    assert audit["structural_spl_ok"] + len(audit["structural_spl_failed"]) == audit["dashboard_views"]
    assert audit["visually_verified"] == sum(1 for r in S if r.get("dashboard_maturity") == "DASHBOARD_VISUALLY_VERIFIED")


def test_every_runnable_scenario_is_registered_with_its_run_path():
    sys.path[:0] = [str(ROOT / "src"), str(ROOT / "backend")]
    from app.main import SUPPORTED_SCENARIO_IDS
    from netspout_core import incident_packs, netflow_solution, replay_packs
    from netspout_core.authentic_scenario_packs import SCENARIO_PACK_IDS
    registry = {"netflow_solution": set(netflow_solution.IDS), "incident_pack": set(incident_packs.incident_ids()), "scenario_pack": set(SCENARIO_PACK_IDS),
                "replay_pack": {p["id"] for p in replay_packs.packs()}, "scenario_runner": set(SUPPORTED_SCENARIO_IDS)}
    for r in S:
        if r["runnable"] and r["engine"] in registry:
            assert r["scenario_id"] in registry[r["engine"]], (r["engine"], r["scenario_id"])
    assert sum(1 for r in S if r["runnable"] and r["engine"] in registry) >= 120          # the five code-registered engines cover most runnable scenarios


def test_validation_claims_in_the_docs_match_the_evidence_files():
    ev = ROOT / "docs" / "verification" / "evidence"
    live_f = ev / "scenario_contracts" / "live_validation_all.json"
    if not live_f.exists():
        return
    live = {r["scenario_id"]: r for r in json.loads(live_f.read_text())["rows"]}
    dash = json.loads((ev / "dashboards" / "contract_dashboard_maturity.json").read_text())["dashboards"]
    text = (ROOT / "docs" / "SCENARIOS.md").read_text()
    rows = [l for l in text.splitlines() if l.startswith("| `")]
    by_id = {l.split("`")[1]: l for l in rows}
    for cid, line in by_id.items():
        if cid in live and live[cid]["status"] == "PASS":
            assert "live-indexed in the lab Splunk" in line, cid
        elif cid in dash:
            assert "live-indexed in the lab Splunk" not in line, "%s claims live indexing without a passing evidence row" % cid
        if cid in dash:
            assert ("visually inspected" in line) == bool(dash[cid]["screenshot_inspected"]), cid
            assert ("search-validated against indexed data" in line) == bool(dash[cid]["search_results_validated"]), cid
            assert ("parser-validated" in line) == bool(dash[cid]["splunk_spl_parser_validated"]), cid
