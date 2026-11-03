"""One navigation architecture: five primary destinations in the Splunk bar, every other page still reachable, no dead or duplicate entries."""
import re
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "netspout"
NAV = APP / "default/data/ui/nav/default.xml"
VIEWS = APP / "default/data/ui/views"


def top_level():
    return list(ET.parse(NAV).getroot())


def test_primary_destinations_are_overview_scenarios_live_runs_investigate_dashboards():
    labels = [e.get("label") for e in top_level()]
    assert labels[:5] == ["Overview", "Scenarios", "Live Runs", "Investigate", "Dashboards"]
    assert len(labels) <= 6, "the bar is the five destinations plus one overflow menu, not a multi-row list"
    assert top_level()[0].get("default") == "true"


def test_destination_names_come_from_the_view_titles():
    """Splunk shows a view's own <label> in the bar and ignores a label attribute on a nav <view>, so the title is what must say it."""
    titles = {n: ET.parse(VIEWS / f"{n}.xml").getroot().find("label").text for n in ("pulseforge_command_center", "use_case_explorer", "pulseforge_live_runs", "pulseforge_investigate")}
    assert titles == {"pulseforge_command_center": "Overview", "use_case_explorer": "Scenarios", "pulseforge_live_runs": "Live Runs", "pulseforge_investigate": "Investigate"}


def test_every_nav_entry_is_a_real_view_and_appears_once():
    names = [v.get("name") for v in ET.parse(NAV).getroot().iter("view")]
    missing = [n for n in names if n != "search" and not (VIEWS / f"{n}.xml").exists()]
    assert not missing, missing
    dupes = sorted({n for n in names if names.count(n) > 1})
    assert not dupes, dupes


def test_every_view_of_the_app_is_still_reachable_from_the_nav():
    named = {v.get("name") for v in ET.parse(NAV).getroot().iter("view")}
    shipped = {p.stem for p in VIEWS.glob("*.xml")}
    hidden_by_design = set()   # a view that is deliberately not in the menu would be listed here, with the reason
    assert not (shipped - named - hidden_by_design), sorted(shipped - named)[:10]


def test_new_destinations_open_their_own_react_route():
    js = (APP / "appserver/static/netspout_canvas.js").read_text()
    for view, route in (("pulseforge_live_runs", "#/observe/live-runs"), ("pulseforge_investigate", "#/investigate"), ("pulseforge_dashboards", "#/observe/dashboards"), ("use_case_explorer", "#/explore")):
        assert re.search(r"%s: '%s'" % (view, re.escape(route)), js), (view, route)
        assert "netspout_canvas.js" in (VIEWS / f"{view}.xml").read_text()


def test_sidebar_offers_no_placeholder_pages():
    nav = (ROOT / "frontend/src/app/navigation.ts").read_text()
    body = nav[nav.index("export const NAVIGATION"):nav.index("export const LEGACY_REDIRECTS")]
    assert "PLANNED" not in body and "RESEARCH REQUIRED" not in body
    for gone in ("/investigate/timeline", "/investigate/incident", "/investigate/security-intelligence", "/observe/telemetry"):
        assert gone not in body
        assert "'%s'" % gone in nav[nav.index("LEGACY_REDIRECTS"):]   # old bookmarks redirect instead of landing on a stub


def test_generators_keep_working_with_the_nested_dashboards_menu():
    text = NAV.read_text()
    assert re.search(r'  <collection label="Scenario Dashboards">.*?</collection>\s*</collection>', text, re.S)
    assert '  <collection label="NetFlow / IPFIX">' in text and '  <collection label="Operations">' in text
