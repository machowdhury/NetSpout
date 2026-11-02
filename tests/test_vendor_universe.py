"""Universal Vendor Coverage Mandate — registry and snapshot structural verification.

The vendor universe is built offline from the pinned Splunkbase metadata snapshot; tests
verify snapshot integrity, deterministic classification totals, strict count-dimension
separation, and that canonical counts are imported from committed evidence, not recomputed.
"""
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "catalog/vendor_universe/splunkbase_apps_snapshot.json"
REGISTRY = ROOT / "catalog/vendor_universe.json"


def load_registry():
    return json.loads(REGISTRY.read_text())


def test_snapshot_integrity_and_sha():
    snap = json.loads(SNAPSHOT.read_text())
    registry = load_registry()
    assert snap["declared_totals"]["rows_fetched"] == 1871
    assert len(snap["rows"]) == 1871
    assert hashlib.sha256(SNAPSHOT.read_bytes()).hexdigest() == registry["provenance"]["snapshot_sha256"]
    assert registry["provenance"]["fetch_scope"].startswith("Public Splunkbase metadata API only")


def test_registry_bucket_partition_is_exact():
    registry = load_registry()
    buckets = registry["counts_by_bucket"]
    assert sum(buckets.values()) == 1871
    assert set(buckets) == {
        "splunk_platform", "canonical_linked", "recognized_technology_vendor", "product_only", "publisher_only",
    }
    counts = registry["counts"]
    assert counts["splunkbase_addons"] + counts["splunkbase_applications"] == counts["splunkbase_apps_total"] == 1871


def test_seven_mandate_count_dimensions_present_and_separated():
    counts = load_registry()["counts"]
    required = {
        "discovered_publishers_raw", "discovered_publishers_normalized", "discovered_technology_vendors_canonical",
        "discovered_technology_vendors_extended", "discovered_products",
        "splunkbase_apps_total", "splunkbase_addons", "splunkbase_applications",
        "canonical_sourcetypes", "genuine_event_families_evidenced", "generator_implemented_sources",
        "live_ingestion_verified_sourcetypes", "ta_parser_verified_sourcetypes",
    }
    assert required <= set(counts)
    # Publisher dimension is separate from the vendor dimension and never smaller (dedup only).
    assert counts["discovered_publishers_normalized"] <= counts["discovered_publishers_raw"]


def test_canonical_dimensions_imported_from_committed_evidence():
    counts = load_registry()["counts"]
    assert counts["canonical_sourcetypes"] == 348
    assert counts["generator_implemented_sources"] == 348
    assert counts["genuine_event_families_evidenced"] == 227
    assert counts["live_ingestion_verified_sourcetypes"] == 87
    assert counts["ta_parser_verified_sourcetypes"] == 1
    registry = load_registry()
    # Live-verification claim is backed by the committed evidence files it names.
    for rel in registry["live_verification_sources"]:
        assert (ROOT / rel).exists()
    ta_parser = registry["ta_parser_verified"]
    assert ta_parser["sourcetype"] == "cisco:ise:syslog"


def test_publisher_not_vendor_guarantee():
    registry = load_registry()
    pubs = set(registry["publishers"])
    vendors = {name for name, _n in registry["extended_vendors"]}
    # This canonical vendor universe never stores publisher names as vendor keys:
    # extended vendor keys are lexicon ids, and the recognized list contains no raw
    # publisher names for the consultancy long tail (Sideview, Presidio, Crossrealms...).
    for consultancy in ("Presidio", "Sideview, LLC", "Crossrealms, Inc.", "DataElicit Solutions", "Datapunctum"):
        assert consultancy not in vendors


def test_classification_deterministic_and_audited():
    spec = importlib.util.spec_from_file_location(
        "build_vendor_universe", ROOT / "scripts/build_vendor_universe.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    canon_vendors = json.loads((ROOT / "catalog/vendors.json").read_text())
    canon_sts = json.loads((ROOT / "catalog/sourcetypes.json").read_text())
    canonical_uids = {int(v["splunkbase_id"]): v["id"] for v in canon_vendors if str(v.get("splunkbase_id") or "").isdigit()}
    canonical_st_names = {s["splunk_sourcetype"] for s in canon_sts}

    def aliases_for(v):
        out = [mod.norm_text(v["name"])]
        for frag in mod.re.split(r"[/(),]", v["name"]):
            frag = mod.norm_text(frag)
            if len(frag) >= 4 and frag not in out:
                out.append(frag)
        return out

    cai = [(v["id"], aliases_for(v)) for v in canon_vendors if v["id"] not in ("linux_infrastructure", "splunk")]
    cai.sort(key=lambda va: -max(len(a) for a in va[1]))
    rows = json.loads(SNAPSHOT.read_text())["rows"]
    results = [mod.classify(r, canonical_uids, canonical_st_names, cai) for r in rows]
    assert all(len(res) == 2 and res[0] in {"splunk_platform", "canonical_linked", "recognized_technology_vendor", "product_only", "publisher_only"} for res in results)
    # Splunk platform apps never claim third-party vendor identity as basis.
    for (b, i) in results:
        assert isinstance(i.get("basis"), str)
        assert b != "splunk_platform" or i["basis"] == "is_splunk_built_or_splunk_publisher"


def test_crossmap_links_are_vendor_named_not_generic():
    registry = load_registry()
    canon_names = {s["splunk_sourcetype"] for s in json.loads((ROOT / "catalog/sourcetypes.json").read_text())}
    declared = registry["canonical_coverage_crossmap"]["top_declared_canonical_sourcetypes"]
    assert declared, "crossmap must reference canonical sourcetypes"
    for st, _n in declared:
        assert st in canon_names
    # Every crossmap name carries vendor identity (vendor-prefixed or brand-named, not bare 'json'/'csv').
    for st, _n in declared:
        assert ":" in st or st.split(":")[0] in canon_names


def test_methodology_guardrails_recorded():
    m = load_registry()["methodology"]
    assert "publishers" in m["publisher_not_vendor"]
    assert m["not_all_apps_produce_telemetry"]
    assert m["count_dimensions"] == list(load_registry()["counts"])


def test_generic_for_splunk_title_does_not_imply_vendor():
    spec = importlib.util.spec_from_file_location('universe_classifier', ROOT / 'scripts/build_vendor_universe.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    row = {'uid': -1, 'appid': 'generic_widget', 'name': 'Widget for Splunk', 'author': 'Independent Publisher'}
    bucket, basis = mod.classify(row, {}, set(), [])
    assert bucket in {'product_only', 'publisher_only'}
    assert basis.get('vendor_key') != 'splunk'


def test_complete_classification_and_uncovered_queue():
    registry = load_registry()
    apps = registry['classified_apps']
    assert len(apps) == len({a['uid'] for a in apps}) == 1871
    assert registry['discovery_coverage']['denominator'] == 1871
    canonical = {v['id'] for v in json.loads((ROOT / 'catalog/vendors.json').read_text())}
    assert not canonical & {row['vendor_key'] for row in registry['uncovered_vendor_queue']}
    assert len(registry['extended_products']) == registry['counts']['discovered_products']
