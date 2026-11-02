"""Declarative scenario contracts: every contract is validated, generated, previewed and run through the monitored run path. A registry flag is not evidence;
these tests execute each scenario. Parameterized so a new contract is covered the moment it is added to catalog/scenario_contracts.json."""
import ipaddress
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
for _p in (str(ROOT / "src"), str(ROOT / "backend"), str(ROOT / "tests")):
    if _p not in sys.path:
        sys.path.insert(0, _p)
from app import main
from netspout_core import scenario_contracts as sc
from test_delivery_monitor import client, env, wait_done  # noqa: F401  (env is a fixture)

IDS = sc.ids()
DOC_NETS = [ipaddress.ip_network(n) for n in ("192.0.2.0/24", "198.51.100.0/24", "203.0.113.0/24", "165.225.10.0/24")]


def _ok_ip(ip):
    a = ipaddress.ip_address(ip)
    return a.is_private or any(a in n for n in DOC_NETS)


def test_there_are_contracts():
    assert IDS


@pytest.mark.parametrize("cid", IDS)
def test_contract_is_valid_and_addresses_are_private_or_documentation(cid):
    c = sc.get(cid)
    assert sc.validate(c) == []
    assert c["description"] and len(c["description"]) > 60 and c["assumptions"]            # what it simulates, and the recorded assumptions
    assert all(_ok_ip(n["ip"]) for n in c["nodes"])


@pytest.mark.parametrize("cid", IDS)
def test_generation_is_bounded_ordered_and_tagged(cid):
    c = sc.get(cid)
    ev = sc.generate(cid, "run-x")
    assert 0 < len(ev) <= sc.MAX_EVENTS
    assert {e.sourcetype for e in ev} == set(sc.sourcetypes(c))                          # every declared sourcetype is emitted, nothing else
    order = [p["id"] for p in c["phases"]]
    seq = [order.index(e.netspout_phase) for e in ev]
    assert seq == sorted(seq) and set(e.netspout_phase for e in ev) == set(order)       # phases run in order and each produced events
    assert {e.netspout_run_id for e in ev} == {"run-x"} and {e.netspout_scenario_id for e in ev} == {cid}
    assert ev[0].netspout_parent_event_id is None and all(b.netspout_parent_event_id == a.netspout_event_id for a, b in zip(ev, ev[1:]))
    assert len({e.netspout_event_id for e in ev}) == len(ev)
    assert all(e.raw_log and e.netspout_device_id for e in ev)


@pytest.mark.parametrize("cid", IDS)
def test_declared_correlations_hold_in_every_listed_stream(cid):
    """Each contract declares the entities that tie its sourcetypes together; every listed stream's events must actually contain one of them.
    A contract with no shared identifier must say so (correlation_limit) instead of implying one."""
    c = sc.get(cid)
    ev = sc.generate(cid, "run-x")
    streams = {s["id"]: s["sourcetype"] for s in c["streams"]}
    assert c.get("correlation") or c.get("correlation_limit")
    for corr in c.get("correlation", []):
        assert len(corr["streams"]) >= 2
        for sid in corr["streams"]:
            hay = "\n".join(e.raw_log + " " + e.src_ip + " " + e.dest_ip + " " + e.device_id for e in ev if e.sourcetype == streams[sid])
            assert any(t in hay for t in corr["tokens"]), "%s: entity %r never appears in stream %s" % (cid, corr["entity"], sid)
    assert {e.device_id for e in ev} <= {n["name"] for n in c["nodes"]}               # events come from the declared nodes only


@pytest.mark.parametrize("cid", IDS)
def test_same_run_and_seed_give_the_same_structure(cid):
    key = lambda ev: [(e.sourcetype, e.netspout_phase, e.device_id, e.action, e.status, e.signature, e.src_ip, e.dest_ip) for e in ev]
    assert key(sc.generate(cid, "r1", seed=7)) == key(sc.generate(cid, "r1", seed=7))


@pytest.mark.parametrize("cid", IDS)
def test_no_credentials_or_private_customer_data(cid):
    text = "\n".join(e.raw_log for e in sc.generate(cid, "run-x"))
    assert not re.search(r"(?i)(password|passwd|token|secret|api[_-]?key)\s*[:=]\s*\S{6,}", text.replace("passwd FROM pg_shadow", ""))
    assert not re.search(r"-----BEGIN [A-Z ]*PRIVATE KEY", text)
    assert not re.search(r"[\w.+-]+@[\w-]+\.(com|net|org)\b", text)                      # no e-mail addresses


@pytest.mark.parametrize("cid", IDS)
def test_preview_sends_nothing_and_describes_the_run(cid):
    pv = sc.preview(cid)
    assert pv["total_events"] == sum(p["events"] for p in pv["phases"]) > 0
    assert set(pv["sample"]) == set(pv["sourcetypes"]) and pv["assumptions"]


@pytest.mark.parametrize("cid", IDS)
def test_scenario_runs_through_the_monitored_run_path(cid, env):
    expected = sc.generate(cid, "x")
    r = client.post("/api/runs", json={"kind": "scenario", "target": cid, "eps": 2000})
    assert r.status_code == 200, r.text
    s = wait_done(r.json()["run_id"])
    assert s["state"] == "COMPLETED" and s["counters"]["generated"] == s["counters"]["accepted"] == len(expected) and s["counters"]["indexed"] is None
    assert {p["phase"] for p in s["by_phase"]} == {p["id"] for p in sc.get(cid)["phases"]}
    assert {x[2] for x in env} == {s["run_id"]}                                         # one run id across the whole run


def test_bad_contracts_are_refused():
    base = sc.get(IDS[0])
    bad = dict(base, streams=[dict(base["streams"][0], formatter="format_does_not_exist")])
    assert any("not a SplunkLogEngine" in p for p in sc.validate(bad))
    bad = dict(base, streams=[dict(base["streams"][0], params={**base["streams"][0]["params"], "no_such_parameter": 1})])
    assert sc.validate(bad)
    bad = dict(base, streams=[dict(base["streams"][0], sourcetype="wrong:sourcetype")])
    assert sc.validate(bad) == []                                                       # static checks pass ...
    import copy
    c2 = copy.deepcopy(sc.contracts())
    c2[IDS[0]]["streams"][0]["sourcetype"] = "wrong:sourcetype"
    orig = sc.contracts
    sc.contracts = lambda: c2
    try:
        with pytest.raises(sc.ContractError, match="declares wrong:sourcetype"):             # ... and the run refuses a sourcetype mismatch
            sc.generate(IDS[0], "r")
    finally:
        sc.contracts = orig


# ---- dashboards and registry. Levels verified here: JSON validity, structural SPL (balanced delimiters, recognizable start), run/scenario binding,
# registration in the Explorer. NOT verified here: Splunk's SPL parser, results against indexed data, browser rendering.
VIEWS = ROOT / "netspout" / "default" / "data" / "ui" / "views"


def _view(cid):
    import json
    text = (VIEWS / ("pf_%s.xml" % cid)).read_text()
    return json.loads(re.search(r"<definition><!\[CDATA\[(.*?)\]\]></definition>", text, re.S).group(1))


@pytest.mark.parametrize("cid", IDS)
def test_dashboard_exists_is_valid_and_bound_to_the_run(cid):
    sys.path.insert(0, str(ROOT / "scripts"))
    from audit_scenario_activation import structural_spl_ok
    d = _view(cid)
    srcs = {k: x["options"]["query"] for k, x in d["dataSources"].items() if x.get("type", "").endswith("ds.search")}
    assert srcs and all(structural_spl_ok(q) for q in srcs.values())
    assert all('netspout_scenario_id="%s"' % cid in q for q in srcs.values())                       # every search is scoped to this scenario
    assert all("$run_tok$" in q for k, q in srcs.items() if k != "ds_runs")                         # ... and to the chosen run (ds_runs is the run picker)
    titles = " ".join(v.get("title", "") for v in d["visualizations"].values())
    assert "Status by phase" in titles and "What each phase reported" in titles                    # the contract-specific panels are present
    assert len({v.get("title") for v in d["visualizations"].values()}) > 8                         # not a one-panel placeholder


def test_dashboard_titles_are_unique_across_contracts():
    import json
    labels = [re.search(r"<label>(.*?)</label>", (VIEWS / ("pf_%s.xml" % c)).read_text()).group(1) for c in IDS]
    assert len(set(labels)) == len(labels)


@pytest.mark.parametrize("cid", IDS)
def test_explorer_registers_the_contract_as_runnable_with_its_dashboard(cid):
    e = next(x for x in main._explorer().all_entries() if x["scenario_id"] == cid and x["kind"] == "operational")
    assert e["engine"] == "scenario_contract" and e["runnable"] and not e["blocked_reason"]
    assert e["dashboard"] and e["dashboard"]["splunk_view"] == "pf_" + cid
