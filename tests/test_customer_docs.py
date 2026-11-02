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
