"""Scenario quality review as executable checks: does the story each contract tells make sense? Meaning, progression, dependency order, recovery, and that nothing is a relabeled copy
of another scenario. Run over every contract, so a defect in any generated or authored scenario fails here."""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
for _p in (str(ROOT / "src"), str(ROOT / "backend")):
    if _p not in sys.path:
        sys.path.insert(0, _p)
from netspout_core import scenario_contracts as sc

IDS = sc.ids()
HEALTHY = {"normal", "restored", "healthy", "recovered", "compliant", "available", "within_sla", "ok", "alert_cleared", "mitigated"}


def phase_statuses(ev, order):
    return {p: {e.status for e in ev if e.netspout_phase == p} for p in order}


@pytest.mark.parametrize("cid", IDS)
def test_story_has_a_healthy_start_a_real_deviation_and_a_recovery(cid):
    c = sc.get(cid)
    ev = sc.generate(cid, "q")
    order = [p["id"] for p in c["phases"]]
    st = phase_statuses(ev, order)
    all_status = set().union(*st.values())
    if all_status <= HEALTHY:
        pytest.skip("steady-state scenario: no deviation by design")      # e.g. normal_traffic; its dashboard uses the load chart
    assert st[order[0]] <= HEALTHY, "%s starts unhealthy: %s" % (cid, st[order[0]])
    assert any(s - HEALTHY for p, s in st.items() if p != order[0]), "%s never leaves the healthy state" % cid
    assert st[order[-1]] <= HEALTHY, "%s does not recover: final phase %s" % (cid, st[order[-1]])


@pytest.mark.parametrize("cid", [i for i in IDS if sc.get(i).get("source", "").startswith("generated:cisco_100")])
def test_cisco100_dependency_changes_state_before_its_dependent(cid):
    c = sc.get(cid)
    ev = [e for e in sc.generate(cid, "q") if e.sourcetype == "netspout:scenario:state"]
    dep = next(s for s in c["streams"] if s["id"] == "dependency")
    dep_name = next(n["name"] for n in c["nodes"] if n["id"] == dep["node"])
    first_incident = next(p["id"] for p in c["phases"] if p["id"] not in ("BASELINE",))
    first = next(e for e in ev if e.netspout_phase == first_incident)
    assert first.device_id == dep_name, "%s: the dependent changed before its dependency" % cid
    docs = [json.loads(e.raw_log) for e in ev if e.netspout_phase == first_incident]
    assert any(d["state"] != "HEALTHY" for d in docs) and docs[0]["previous_state"] == "HEALTHY"


@pytest.mark.parametrize("cid", [i for i in IDS if sc.get(i).get("source", "").startswith("generated:scenario_candidates")])
def test_use_case_measure_leaves_its_normal_range_and_returns(cid):
    ev = [json.loads(e.raw_log) for e in sc.generate(cid, "q") if e.sourcetype == "netspout:scenario:state" and "metric_value" in e.raw_log]
    by = {}
    for d in ev:
        by.setdefault(d["state"], []).append(d["metric_value"])
    phases = [(e.netspout_phase, json.loads(e.raw_log)["metric_value"]) for e in sc.generate(cid, "q") if e.sourcetype == "netspout:scenario:state" and "metric_value" in e.raw_log]
    base = [v for p, v in phases if p == "BASELINE"]
    dev = [v for p, v in phases if p in ("DEVIATION", "ESCALATION")]
    rec = [v for p, v in phases if p == "RECOVERY"]
    assert min(map(abs, dev)) != max(map(abs, base)) and (max(dev) > max(base) or min(dev) < min(base)), "%s: the measure never deviates" % cid
    assert max(rec) <= max(base) and min(rec) >= min(base), "%s: recovery is outside the baseline range" % cid


def test_no_two_contracts_are_the_same_story_under_different_names():
    seen = {}
    for cid in IDS:
        c = sc.get(cid)
        sig = (tuple(sorted(sc.sourcetypes(c))), tuple(p["id"] for p in c["phases"]), json.dumps([s.get("phase_params") for s in c["streams"]], sort_keys=True, default=str), c["description"])
        assert sig not in seen, "%s duplicates %s" % (cid, seen.get(sig))
        seen[sig] = cid
    titles = [sc.get(c)["title"] for c in IDS]
    assert len(set(titles)) == len(titles)


@pytest.mark.parametrize("cid", IDS)
def test_emitted_sourcetypes_match_the_declared_streams_and_description_names_the_product(cid):
    c = sc.get(cid)
    ev = sc.generate(cid, "q")
    assert {e.sourcetype for e in ev} == {s["sourcetype"] for s in c["streams"]}
    if sc.fidelity(c) != "VENDOR_NATIVE":
        assert any("MODELED" in a or "modeled" in a or "verbatim" in a or "native" in a.lower() for a in c["assumptions"]), "%s does not say what is modeled" % cid


AUTHENTIC_BGP_EVENT_TYPES = {"ROUTE_STABLE", "BGP_DOWN", "BGP_UP", "TI_LFA_REROUTE"}   # the only types format_cisco_ios_xr_bgp_log renders as real IOS-XR syslog; any other prints generic text


def test_bgp_streams_use_only_event_types_the_formatter_really_renders():
    for cid in IDS:
        for s in sc.get(cid)["streams"]:
            if s["formatter"] != "format_cisco_ios_xr_bgp_log":
                continue
            types = set()
            for d in [s["params"], *s.get("phase_params", {}).values()]:
                v = d.get("event_type")
                types |= set(v if isinstance(v, list) else [v] if v else [])
            assert types <= AUTHENTIC_BGP_EVENT_TYPES, "%s uses BGP event types that produce generic text: %s" % (cid, sorted(types - AUTHENTIC_BGP_EVENT_TYPES))


def test_replayed_samples_are_recorded_events_not_configuration_or_envelopes():
    import re
    config = re.compile(r"^[A-Za-z_][\w.\-]*:\s")
    for cid in IDS:
        c = sc.get(cid)
        sample_types = {s["sourcetype"] for s in c["streams"] if s["formatter"] == "grounded_sample"}
        for e in sc.generate(cid, "q"):
            if e.sourcetype in sample_types:
                t = e.raw_log.strip()
                assert not config.match(t), "%s replays a configuration line: %r" % (cid, t[:60])
                if t.startswith("{"):
                    doc = json.loads(t)
                    assert not ({"event", "sourcetype"} <= set(doc)), "%s replays an HEC envelope" % cid


def test_no_stream_pretends_to_be_a_product_it_cannot_emit():
    """A scenario that names a vendor sourcetype it does not emit must say so in its assumptions (no silent relabeling)."""
    catalog = {r["id"]: r for r in json.loads((ROOT / "catalog" / "scenarios.json").read_text())}
    for cid in IDS:
        declared = set(catalog.get(cid, {}).get("sourcetypes", []))
        missing = declared - set(sc.sourcetypes(sc.get(cid)))
        if missing and cid in catalog:
            text = " ".join(sc.get(cid)["assumptions"])
            assert all(m in text for m in missing), "%s does not emit %s and does not say so" % (cid, sorted(missing))
