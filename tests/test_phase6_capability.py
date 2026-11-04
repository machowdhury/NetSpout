"""Phase 6: honest capability status, trusted preview, routing-conflict safety and scenario eligibility, through the real API and delivery path."""
import random
import sys
import time
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
for _p in (str(ROOT / "src"), str(ROOT / "backend")):
    if _p not in sys.path:
        sys.path.insert(0, _p)
from fastapi.testclient import TestClient

from app import main
from netspout_core import capability
from netspout_core.delivery_monitor import RunMonitorService
from netspout_core.models import LogEntry, TelemetryTransportConfig
from netspout_core.replay_service import ReplayService
from netspout_core.telemetry_dispatcher import dispatcher

client = TestClient(main.app)
CFG = {"configured": True, "deployment_mode": "DOCKER_LAB", "indexes": ["dev_test_replay", "dev_test_replay_metrics"], "hec_url": "https://127.0.0.1:8088/services/collector"}
GT = TelemetryTransportConfig(hec_url="https://127.0.0.1:8088/services/collector", hec_token="tok-test", hec_metric_index="dev_test_replay_metrics")
VERIFIED = {"cisco:asa": "cisco_asa", "cisco:ios": "cisco_ios", "fortigate_traffic": "fortinet", "pan:traffic": "palo_alto", "pan:threat": "palo_alto", "pan:system": "palo_alto"}   # Phase 10 added pan:threat and pan:system
# vmware:perf:cpu left this list in Phase 8: the reference instance and Splunk_TA_vmware show it is a TSV event sourcetype, now generated as one
CONFLICTS = ["cisco:thousandeyes:metric", "cisco:intersight:metrics"]


class Out(tuple):
    def __new__(cls, ok, msg, state):
        o = super().__new__(cls, (ok, msg))
        o.state = state
        return o


@pytest.fixture()
def env(tmp_path):
    main.run_monitor = RunMonitorService(tmp_path / "runs.json")
    main.replay_service = ReplayService(tmp_path / "replay.json")
    sent = []

    def fake_emit(payload, url, token, **kw):
        sent.append(payload)
        return Out(True, "HEC HTTP 200", "ACCEPTED")

    with patch.object(main.release_candidate_configuration, "load", return_value=dict(CFG)), patch.object(main.current_topology, "global_transport", GT, create=True), \
            patch.object(main.dispatcher, "emit_hec", side_effect=fake_emit):
        yield sent


def wait_done(rid):
    for _ in range(150):
        s = client.get("/api/runs/" + rid).json()
        if s["state"] in ("COMPLETED", "STOPPED", "FAILED"):
            return s
        time.sleep(0.1)
    return s


def test_the_verified_integrations_are_exactly_the_live_evidence_and_lead_the_tree():
    live = {k for k, v in __import__("json").loads((ROOT / "docs/contracts/ta_live_results.json").read_text()).items() if v["passed"]}
    got = {s: r for s, r in capability.data()["sourcetypes"].items() if r["status"] == "VERIFIED"}
    assert set(got) == live == set(VERIFIED)
    tree = client.get("/api/compat/catalog").json()
    assert {v["id"] for v in tree["vendors"][:4]} == set(VERIFIED.values())           # verified vendors first
    first = tree["vendors"][0]["products"][0]["sourcetypes"][0]
    assert first["status"] == "VERIFIED" and first["evidence"]["live_checks"]
    only = client.get("/api/compat/catalog?verified_only=true").json()["vendors"]
    assert {s["sourcetype"] for v in only for p in v["products"] for s in p["sourcetypes"]} == set(VERIFIED)


def test_status_is_never_taken_from_tier_labels():
    cov = {r["sourcetype"]: r for r in __import__("json").loads((ROOT / "docs/reference/sourcetype_coverage.json").read_text())["rows"]}
    for st, r in capability.data()["sourcetypes"].items():
        if r["status"] == "FORMAT_CHECKED":
            assert not r["block"] and r["generator"]
        if cov[st]["generator_tier"] == "NATIVE_ENGINE" and r["status"] != "VERIFIED":
            assert r["status"] in ("FORMAT_CHECKED", "GENERATOR_UNVERIFIED", "UNSUPPORTED")


@pytest.mark.parametrize("st,vendor", sorted(VERIFIED.items()))
def test_verified_generation_sends_exactly_the_requested_sourcetype_and_accounts_for_every_event(env, st, vendor):
    r = client.post("/api/runs", json={"kind": "sourcetype", "target": st, "vendor_id": vendor, "count": 8, "eps": 500})
    assert r.status_code == 200, r.text
    s = wait_done(r.json()["run_id"])
    assert s["state"] == "COMPLETED" and s["counters"]["generated"] == s["counters"]["accepted"] == 8 and s["counters"]["indexed"] is None   # accepted is not indexed
    assert {p["sourcetype"] for p in env} == {st} and len(env) == 8 and all(p["fields"]["netspout_run_id"] == s["run_id"] for p in env)


@pytest.mark.parametrize("st,vendor", sorted(VERIFIED.items()))
def test_preview_uses_the_run_path_and_shows_the_exact_raw_event_and_sourcetype(env, st, vendor):
    random.seed(7)
    pv = client.post("/api/generate/preview", json={"vendor_id": vendor, "sourcetype": st, "count": 3})
    assert pv.status_code == 200, pv.text
    pv = pv.json()
    assert not env, "a preview must never send anything"
    assert pv["status"] == "VERIFIED" and [e["sourcetype"] for e in pv["events"]] == [st] * 3 and all(e["raw"] for e in pv["events"]) and "does not prove" in pv["disclaimer"]
    # a run builds events through the same function and payload builder: same sourcetype, same format class for every raw event
    r = client.post("/api/runs", json={"kind": "sourcetype", "target": st, "vendor_id": vendor, "count": 3, "eps": 500}).json()
    wait_done(r["run_id"])
    assert {p["sourcetype"] for p in env} == {e["sourcetype"] for e in pv["events"]}
    shape = lambda raw: __import__("re").sub(r"\d+", "9", raw)[:12]
    assert {shape(p["event"]) for p in env} == {shape(e["raw"]) for e in pv["events"]}


def test_preview_payload_is_built_by_the_dispatcher_not_by_a_hard_coded_example():
    cap = []
    e = LogEntry(id="1", timestamp="t", device_id="d1", src_ip="1.1.1.1", dest_ip="2.2.2.2", protocol="TCP", duration="1ms", signature="s", node_type="firewall", node_id="d1", vendor="cisco_asa",
                 sourcetype="cisco:asa", raw_log="UNIQUE-RAW-TEXT", status="normal", action="a")
    cfg = TelemetryTransportConfig(hec_enabled=True, hec_url="https://x.invalid/services/collector", hec_token="t", hec_index="i")
    with patch.object(dispatcher, "emit_hec", side_effect=AssertionError("preview must not send")):
        dispatcher._dispatch_log(e, cfg, capture=cap)
    assert cap[0]["event"] == "UNIQUE-RAW-TEXT" and cap[0]["sourcetype"] == "cisco:asa" and cap[0]["index"] == "i"


def test_unsupported_selection_is_refused_with_an_explanation_never_generated(env):
    st = next(s for s, r in capability.data()["sourcetypes"].items() if r["block"] and r["block"]["code"] == "NO_GENERATOR")
    vendor = capability.get(st)["vendor_id"]
    for call in (lambda: client.post("/api/generate/preview", json={"vendor_id": vendor, "sourcetype": st}),
                 lambda: client.post("/api/runs", json={"kind": "sourcetype", "target": st, "vendor_id": vendor, "count": 3})):
        r = call()
        assert r.status_code == 409 and "no verified generator" in r.json()["detail"]
    assert not env


@pytest.mark.parametrize("st", CONFLICTS)
def test_the_remaining_routing_conflicts_are_blocked_everywhere_and_never_converted(env, st):
    rec = capability.get(st)
    assert rec["status"] == "UNSUPPORTED" and rec["block"]["code"] == "ROUTING_CONFLICT" and "metric" in rec["block"]["message"] and "event sourcetype" in rec["block"]["message"]
    vendor = rec["vendor_id"]
    for r in (client.post("/api/generate/preview", json={"vendor_id": vendor, "sourcetype": st}), client.post("/api/runs", json={"kind": "sourcetype", "target": st, "vendor_id": vendor, "count": 2})):
        assert r.status_code == 409 and "generation is disabled" in r.json()["detail"]
    # last line of defence: even a direct dispatch (for example from a scenario) sends nothing, neither as a metric nor as a log
    e = LogEntry(id="1", timestamp="t", device_id="d1", src_ip="1.1.1.1", dest_ip="2.2.2.2", protocol="TCP", duration="1ms", signature="s", node_type="x", node_id="d1", vendor=vendor,
                 sourcetype=st, raw_log="x", status="normal", action="a")
    res = dispatcher._dispatch_log(e, TelemetryTransportConfig(hec_enabled=True, hec_url="https://x.invalid/services/collector", hec_token="t", hec_index="i"))
    assert res["hec"]["success"] is False and res["hec"]["error_class"] == "routing_conflict_not_dispatched" and not env


def test_connection_failure_is_reported_not_hidden(env):
    with patch.object(main.release_candidate_configuration, "load", return_value={"configured": False, "indexes": []}):
        r = client.post("/api/runs", json={"kind": "sourcetype", "target": "cisco:asa", "vendor_id": "cisco_asa", "count": 2})
    assert r.status_code == 409 and "not configured" in r.json()["detail"]
    fail = lambda payload, url, token, **kw: Out(False, "HEC HTTP 403 (code 4)", "FAILED")
    with patch.object(main.dispatcher, "emit_hec", side_effect=fail):
        rid = client.post("/api/runs", json={"kind": "sourcetype", "target": "cisco:asa", "vendor_id": "cisco_asa", "count": 4, "eps": 500}).json()["run_id"]
        s = wait_done(rid)
    assert s["counters"]["accepted"] == 0 and s["counters"]["rejected"] == 4 and "403" in s["recent_errors"][0]["message"]


def test_scenario_eligibility_separates_runnable_from_splunk_verified(env):
    sc = client.get("/api/compat/scenarios").json()["scenarios"]
    assert len(sc) == 372 and {s["run_state"] for s in sc} <= {"VERIFIED_IN_SPLUNK", "RUNNABLE_UNVERIFIED", "NOT_RUNNABLE"}
    assert not any(s["verified"] and not s["runnable"] for s in sc)
    for s in sc:
        if s["verified"]:
            assert all(r["status"] == "VERIFIED" for r in s["required"])
        if s["run_state"] == "NOT_RUNNABLE":
            assert s["reasons"]
    blocked = [s for s in sc if s["run_state"] == "NOT_RUNNABLE"]
    runnable = [s for s in sc if s["run_state"] == "RUNNABLE_UNVERIFIED"]
    assert blocked and runnable
    r = client.post("/api/runs", json={"kind": "scenario", "target": blocked[0]["id"]})
    assert r.status_code == 409 and "not runnable" in r.json()["detail"]


def test_a_scenario_that_requires_a_routing_conflict_sourcetype_is_not_runnable():
    row = {"id": "x", "title": "x", "category": None, "summary": None, "engine": None, "dashboard": None, "catalog_runnable": True, "catalog_blocked_reason": None, "sourcetypes": ["cisco:asa", "cisco:intersight:metrics"]}
    s = capability.scenario(row)
    assert not s["runnable"] and s["run_state"] == "NOT_RUNNABLE" and "cisco:intersight:metrics" in s["reasons"][0]
    row["sourcetypes"] = ["cisco:asa", "cisco:ios", "fortigate_traffic", "pan:traffic"]
    s = capability.scenario(row)
    assert s["runnable"] and s["verified"] and s["run_state"] == "VERIFIED_IN_SPLUNK"


def test_scenarios_whose_sources_only_their_own_engine_builds_stay_runnable():
    sc = {s["id"]: s for s in capability.scenarios()}
    for sid in ("lateral_movement", "normal_traffic"):                       # contain postgresql:audit, which has no standalone generator but is built by the scenario contract
        assert sc[sid]["runnable"] and sc[sid]["run_state"] == "RUNNABLE_UNVERIFIED"
        assert any(r["sourcetype"] == "postgresql:audit" and "own engine" in r.get("note", "") for r in sc[sid]["required"])
    for sid in ("C100-CRI-001", "arch_gan_subsea_cloud"):                    # these really emit cisco:thousandeyes:metric
        assert not sc[sid]["runnable"] and "cisco:thousandeyes:metric" in " ".join(sc[sid]["reasons"])


def test_a_metric_sourcetype_run_without_an_index_uses_the_saved_event_index_and_sends_metrics(env):
    """Found by the Phase 9 browser acceptance: a metric run from Generate Data sent no index, and the backend fell back to an unconfigured default, so it answered 403."""
    saved = dict(CFG, indexes=["ta_validation", "cisco_metrics"])                     # a real destination: no dev_test_replay anywhere
    gt = GT.model_copy(update={"hec_metric_index": "cisco_metrics"})
    with patch.object(main.release_candidate_configuration, "load", return_value=saved), patch.object(main.current_topology, "global_transport", gt, create=True):
        r = client.post("/api/runs", json={"kind": "sourcetype", "target": "cisco:ios:mdt:metric", "vendor_id": "cisco_ios", "count": 3, "eps": 500})
        assert r.status_code == 200, r.text
        assert r.json()["destination"]["index"] == "ta_validation" and r.json()["destination"]["metric_index"] == "cisco_metrics"
        snap = wait_done(r.json()["run_id"])
        rid = r.json()["run_id"]
        dp = sum(1 for p in env for k in p["fields"] if k.startswith("metric_name:"))
        assert len(env) == 3 and all(p["event"] == "metric" and p["index"] == "cisco_metrics" for p in env)
        assert any(k.startswith("metric_name:interface_generic_counters.") for p in env for k in p["fields"])
        assert snap["metric_accepted"] == {"events": 3, "datapoints": dp}             # metric events are counted as datapoints, not as log events
        # verification: the metric index is searched with mstats, the event index is not what proves metrics
        queries = []

        def search(q, **kw):
            queries.append(q)
            return ([{"n": str(dp)}], None) if "mstats" in q else ([{"indexed": "0"}], None)
        with patch.object(main.release_candidate_configuration, "execute_read_only_search", side_effect=search):
            v = client.post("/api/runs/%s/verify" % rid).json()
        assert v["status"] == "VERIFIED" and v["metric_datapoints_indexed"] == dp and v["metric_datapoints_expected"] == dp and v["expected_log_events"] == 0
        assert any('mstats' in q and 'index="cisco_metrics"' in q and rid in q for q in queries)
        with patch.object(main.release_candidate_configuration, "execute_read_only_search", side_effect=lambda q, **kw: ([{"n": "0"}], None) if "mstats" in q else ([{"indexed": "0"}], None)):
            assert client.post("/api/runs/%s/verify" % rid).json()["status"] == "INCOMPLETE"          # nothing in the metric index: never Verified


def test_a_scenario_run_without_an_index_uses_the_saved_event_index(env):
    """Found by the Phase 9 browser acceptance: a scenario started from the UI named no index and every real destination answered 403."""
    saved = dict(CFG, indexes=["ta_validation", "cisco_metrics"])
    gt = GT.model_copy(update={"hec_metric_index": "cisco_metrics"})
    with patch.object(main.release_candidate_configuration, "load", return_value=saved), patch.object(main.current_topology, "global_transport", gt, create=True):
        r = client.post("/api/runs", json={"kind": "scenario", "target": "wireless_connected_core_mixed", "eps": 2000})
        assert r.status_code == 200, r.text
        assert r.json()["destination"]["index"] == "ta_validation"
        wait_done(r.json()["run_id"])
        # an explicit index outside the destination is still refused
        assert client.post("/api/runs", json={"kind": "scenario", "target": "wireless_connected_core_mixed", "index": "somewhere_else"}).status_code == 403
    assert env and all(p["index"] in ("ta_validation", "cisco_metrics") for p in env) and any(p["index"] == "ta_validation" for p in env)


def test_a_scenario_runner_scenario_started_from_the_ui_really_delivers_with_the_saved_token(env):
    """Found by the Phase 9 browser acceptance: the scenario runner got a copy of the transport built with model_dump(), which drops the HEC token, so it generated
    events, attempted no delivery and still finished COMPLETED. The token here is NOT in the environment, as in a normal Connections-only setup."""
    import os
    saved = dict(CFG, indexes=["ta_validation", "cisco_metrics"])
    gt = main.TelemetryTransportConfig(hec_url=GT.hec_url, hec_token="tok-only-in-the-saved-destination", hec_metric_index="cisco_metrics")   # main validates against its own copy of the model class
    seen = []
    orig = main.scenario_runner.run_scenario

    def spy(request, *a, **k):
        seen.append(request.transport_config.hec_token)
        return orig(request, *a, **k)
    with patch.dict(os.environ, {"NETSPOUT_HEC_TOKEN": ""}), patch.object(main.release_candidate_configuration, "load", return_value=saved), \
            patch.object(main.current_topology, "global_transport", gt, create=True), patch.object(main.scenario_runner, "run_scenario", side_effect=spy):
        r = client.post("/api/runs", json={"kind": "scenario", "target": "paloalto_threat_investigation", "eps": 2000})
        assert r.status_code == 200, r.text
        for _ in range(100):
            if seen:
                break
            time.sleep(0.1)
    assert seen == ["tok-only-in-the-saved-destination"]
