"""Documented scenario candidates: provenance, deduplication, and the rule that cataloged never means runnable."""
import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
for _p in (str(ROOT / "src"), str(ROOT / "backend")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from netspout_core.security_content_lab import SecurityContentCatalog  # noqa: E402
from netspout_core.use_case_explorer import UseCaseExplorer, load_candidates, load_curated_stories, load_taxonomy  # noqa: E402

DOC = json.loads((ROOT / "catalog" / "scenario_candidates.json").read_text())
CANDS = DOC["candidates"]
TAX = load_taxonomy()
SUBDOMAINS = {d["id"] for i in TAX["industries"] for d in i.get("subdomains", [])}


def explorer(candidates=CANDS, catalog_scenarios=()):
    return UseCaseExplorer(taxonomy=TAX, generation_scenarios=[], generation_sources=[], dashboards=[], catalog_scenarios=list(catalog_scenarios),
                           security_catalog=SecurityContentCatalog(), validations=lambda: [], runtime_approved_detections=[], candidates=candidates)


def test_registry_provenance_and_shape():
    assert len({c["candidate_id"] for c in CANDS}) == len(CANDS) >= 200
    sources = {s["source_id"]: s for s in DOC["sources"]}
    assert re.fullmatch(r"[0-9a-f]{40}", sources["community-uc"]["commit"]) and "MIT" in sources["community-uc"]["license"]
    for c in CANDS:
        assert c["status"] == "CATALOGED" and c["source_id"] in sources and c["title"]
        assert not ({"spl", "search", "runbook", "description"} & set(c)), "only id/title/labels are recorded, never upstream SPL or prose"
        if c["source_id"] == "community-uc":
            assert c["url"].startswith("https://github.com/fenre/splunk-monitoring-use-cases/blob/" + sources["community-uc"]["commit"] + "/content/")


def test_every_candidate_industry_and_subdomain_is_approved_and_has_a_basis():
    ids = {i["id"] for i in TAX["industries"]}
    for c in CANDS:
        for i in c["industries"]:
            assert i["id"] in ids and i["basis"] in ("SOURCE_LABEL", "EDITORIAL_TITLE", "EDITORIAL_DOMAIN")
            if i.get("subdomain"):
                assert i["subdomain"] in SUBDOMAINS and i["id"] == "government-public-sector"


def test_cisco_100_candidates_exclude_scenarios_that_already_execute():
    promoted = {p["scenario_id"] for p in json.loads((ROOT / "catalog/phase8c_scenario_promotions.json").read_text())["promotions"]}
    cisco = [c for c in CANDS if c["source_id"] == "cisco-100"]
    assert len(cisco) == 95 and not ({c["candidate_id"] for c in cisco} & promoted)
    assert "C100-SP-001" not in {c["candidate_id"] for c in cisco}  # execution-enabled in the Cisco 100 catalog itself


def test_cataloged_entries_are_never_runnable_or_demo_ready_and_expose_no_steps():
    entries = [e for e in explorer().all_entries() if e.get("engine") == "cataloged"]
    assert len(entries) == len(CANDS)
    for e in entries:
        assert e["runnable"] is False and e["demo_ready"] is False and e["maturity"]["tier"] == "CATALOGED"
        assert "no generator or scenario contract" in e["blocked_reason"]
        assert all(not s["available"] for s in e["workflow"] if s["step"] != "SELECT")
        assert e["provenance"]["source_id"] and e["live_verified"] is False


def test_every_approved_industry_has_documented_scenarios_and_counts_each_entry_once():
    rows = {r["id"]: r for r in explorer().industries()}
    assert set(rows) == {i["id"] for i in TAX["industries"]} and len(rows) == 18
    for r in rows.values():
        assert r["scenarios_total"] >= 3, r["id"]
        assert r["scenarios_runnable"] == 0 and r["scenarios_cataloged_only"] == r["scenarios_total"]  # candidates alone: documented, not executable
    ex = explorer()
    for ind in rows:
        ids = [e["entry_id"] for e in ex.all_entries() if e["kind"] == "operational" and any(i["id"] == ind for i in e["industries"])]
        assert len(ids) == len(set(ids)) == rows[ind]["scenarios_total"]


def test_a_candidate_already_represented_by_an_executable_entry_is_not_counted_twice():
    existing = [{"id": "C100-ENT-001", "name": "Reference", "maturity": "GOLDEN_PATH_CERTIFIED", "sourcetypes": []}]
    dup = {"candidate_id": "C100-ENT-001", "source_id": "cisco-100", "source_ref": "C100-ENT-001", "title": "dup", "kind": "operational", "industries": [], "status": "CATALOGED", "dependencies": {}}
    ex = explorer(candidates=[dup], catalog_scenarios=existing)
    assert ex.duplicate_candidates == ["C100-ENT-001"]
    assert [e["scenario_id"] for e in ex.all_entries() if e["kind"] == "operational"] == ["C100-ENT-001"]


def test_candidate_with_an_unapproved_industry_is_rejected():
    bad = {"candidate_id": "UCR-0.0.0", "source_id": "community-uc", "source_ref": "UC-0.0.0", "title": "x", "kind": "operational", "status": "CATALOGED",
           "industries": [{"id": "made-up-industry", "basis": "EDITORIAL_TITLE"}], "dependencies": {}}
    with pytest.raises(ValueError):
        explorer(candidates=[bad])


def test_shipped_registry_loads_through_the_runtime_loader():
    assert [c["candidate_id"] for c in load_candidates()] == [c["candidate_id"] for c in CANDS]


STORIES = json.loads((ROOT / "catalog" / "curated_analytic_stories.json").read_text())["stories"]


def test_curated_stories_have_verified_research_links_and_no_copied_prose():
    assert len(STORIES) >= 15 and len({s["content_id"] for s in STORIES}) == len(STORIES)
    ids = {i["id"] for i in TAX["industries"]}
    for s in STORIES:
        assert re.fullmatch(r"https://research\.splunk\.com/stories/[a-z0-9_\-]+/", s["research_url"]) and s["research_url_http_status"] == 200
        assert not ({"narrative", "description"} & set(s))
        for i in s["industries"]:
            assert i["id"] in ids and i["basis"] == "NARRATIVE_TARGET_SECTOR" and i["matched_phrase"]


def test_curated_stories_are_never_marked_executable_by_curation_alone():
    sec = SecurityContentCatalog()
    ex = UseCaseExplorer(taxonomy=TAX, generation_scenarios=[], generation_sources=[], dashboards=[], catalog_scenarios=[], security_catalog=sec,
                         validations=lambda: [], runtime_approved_detections=[], curated_stories=STORIES)
    curated = [e for e in ex.security_entries() if e["curation"]]
    assert len(curated) == len(STORIES)
    assert all(not e["demo_ready"] and e["readiness"]["detections_runtime_approved"] == 0 for e in curated)  # nothing approved in this fixture
    assert all(e["curation"]["research_url"].startswith("https://research.splunk.com/stories/") for e in curated)
    rows = {r["id"]: r for r in ex.industries()}
    assert sum(r["security_stories_runnable"] for r in rows.values()) == 0 and sum(r["security_detections_verified"] for r in rows.values()) == 0


def test_curated_story_with_an_unapproved_industry_is_rejected():
    bad = [{**STORIES[0], "industries": [{"id": "made-up", "basis": "NARRATIVE_TARGET_SECTOR", "matched_phrase": "x"}]}]
    ex = UseCaseExplorer(taxonomy=TAX, generation_scenarios=[], generation_sources=[], dashboards=[], catalog_scenarios=[], security_catalog=SecurityContentCatalog(),
                         validations=lambda: [], runtime_approved_detections=[], curated_stories=bad)
    with pytest.raises(ValueError):
        ex.security_entries()


def test_shipped_curated_registry_loads_through_the_runtime_loader():
    assert [s["content_id"] for s in load_curated_stories()] == [s["content_id"] for s in STORIES]
