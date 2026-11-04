"""Phase 10.1: one run over several sourcetypes, through the real API, dispatcher and verification code (HEC and Splunk search are faked at the boundary)."""
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
from netspout_core.delivery_monitor import NO_TELEMETRY, DeliveryRun, RunMonitorService
from netspout_core.models import TelemetryTransportConfig
from netspout_core.replay_service import ReplayService

client = TestClient(main.app)
CFG = {"configured": True, "deployment_mode": "DOCKER_LAB", "indexes": ["idx_events", "idx_metrics"], "hec_url": "https://127.0.0.1:8088/services/collector"}
GT = TelemetryTransportConfig(hec_url="https://127.0.0.1:8088/services/collector", hec_token="tok-test", hec_metric_index="idx_metrics")
FOUR = [{"vendor_id": "cisco_asa", "sourcetype": "cisco:asa", "count": 5}, {"vendor_id": "cisco_ios", "sourcetype": "cisco:ios", "count": 4},
        {"vendor_id": "fortinet", "sourcetype": "fortigate_traffic", "count": 3}, {"vendor_id": "palo_alto", "sourcetype": "pan:traffic", "count": 2}]


class Out(tuple):
    def __new__(cls, ok, msg, state):
        o = super().__new__(cls, (ok, msg))
        o.state = state
        return o


@pytest.fixture()
def env(tmp_path):
    main.run_monitor = RunMonitorService(tmp_path / "runs.json")
    main.replay_service = ReplayService(tmp_path / "replay.json")
    sent, reject = [], set()

    def fake_emit(payload, url, token, **kw):
        sent.append(payload)
        if payload.get("sourcetype") in reject:
            return Out(False, "HEC HTTP 400: Incorrect index", "FAILED")
        return Out(True, "HEC HTTP 200", "ACCEPTED")

    with patch.object(main.release_candidate_configuration, "load", return_value=dict(CFG)), patch.object(main.current_topology, "global_transport", GT, create=True), \
            patch.object(main.dispatcher, "emit_hec", side_effect=fake_emit):
        yield sent, reject


def done(rid):
    for _ in range(200):
        s = client.get("/api/runs/" + rid).json()
        if s["state"] in ("COMPLETED", "STOPPED", "FAILED"):
            return s
        time.sleep(0.1)
    return s


def start(sources, **kw):
    return client.post("/api/runs", json={"kind": "multi", "sources": sources, "index": "idx_events", "eps": 500, **kw})


def splunk(found, metric=None):
    """Fake independent search: `found` = {sourcetype: (count, host)}; metric = datapoints in the metric index."""
    def search(q, **kw):
        if "mstats" in q:
            return ([{"n": str(metric or 0)}], None)
        return ([{"sourcetype": st, "indexed": str(n), "hosts": h} for st, (n, h) in found.items()], None)
    return patch.object(main.release_candidate_configuration, "execute_read_only_search", side_effect=search)


def test_four_event_sourcetypes_each_counted_and_verified_separately(env):
    sent, _ = env
    r = start(FOUR)
    assert r.status_code == 200, r.text
    snap = done(r.json()["run_id"])
    assert snap["kind"] == "multi" and snap["state"] == "COMPLETED"
    assert {k: v["accepted"] for k, v in snap["by_sourcetype"].items()} == {"cisco:asa": 5, "cisco:ios": 4, "fortigate_traffic": 3, "pan:traffic": 2}
    assert snap["counters"]["accepted"] == 14 and snap["counters"]["rejected"] == 0       # the aggregate is the sum, nothing counted twice
    assert [s["sourcetype"] for s in snap["sources"]] == [x["sourcetype"] for x in FOUR]
    assert {p["sourcetype"] for p in sent} == {x["sourcetype"] for x in FOUR} and all(p["index"] == "idx_events" and p["host"] for p in sent)
    with splunk({"cisco:asa": (5, "asa1"), "cisco:ios": (4, "ios1"), "fortigate_traffic": (3, "fw1"), "pan:traffic": (2, "pa1")}):
        v = client.post("/api/runs/%s/verify" % snap["run_id"]).json()
    assert v["status"] == "VERIFIED" and v["indexed"] == 14
    assert {k: x["status"] for k, x in v["by_sourcetype"].items()} == {k: "VERIFIED" for k in ("cisco:asa", "cisco:ios", "fortigate_traffic", "pan:traffic")}
    assert v["by_sourcetype"]["cisco:asa"]["hosts"] == ["asa1"] and v["by_sourcetype"]["cisco:asa"]["index"] == "idx_events"


def test_one_missing_sourcetype_is_never_verified_even_when_the_total_looks_close(env):
    snap = done(start(FOUR).json()["run_id"])
    with splunk({"cisco:asa": (5, "a"), "cisco:ios": (4, "i"), "fortigate_traffic": (3, "f")}):          # pan:traffic never arrived
        v = client.post("/api/runs/%s/verify" % snap["run_id"]).json()
    assert v["status"] == "INCOMPLETE" and v["by_sourcetype"]["pan:traffic"]["status"] == "INCOMPLETE" and v["by_sourcetype"]["cisco:asa"]["status"] == "VERIFIED"


def test_partial_rejection_is_visible_per_sourcetype(env):
    _, reject = env
    reject.add("fortigate_traffic")
    snap = done(start(FOUR).json()["run_id"])
    assert snap["counters"]["accepted"] == 11 and snap["counters"]["rejected"] == 3
    assert snap["by_sourcetype"]["fortigate_traffic"]["rejected"] == 3 and snap["by_sourcetype"]["fortigate_traffic"].get("accepted", 0) == 0
    with splunk({"cisco:asa": (5, "a"), "cisco:ios": (4, "i"), "pan:traffic": (2, "p")}):
        v = client.post("/api/runs/%s/verify" % snap["run_id"]).json()
    assert v["status"] == "PARTIAL"           # everything accepted was found, but a whole source was refused: never Verified
    assert v["by_sourcetype"]["fortigate_traffic"]["status"] == "NOT_SENT" and v["by_sourcetype"]["fortigate_traffic"]["rejected"] == 3
    assert snap["counters"]["rejected"] > 0       # the UI turns any rejection into "only N of M were accepted", never Verified


def test_mixed_event_and_metric_sources_route_to_their_own_index(env):
    sent, _ = env
    snap = done(start([{"vendor_id": "cisco_asa", "sourcetype": "cisco:asa", "count": 3}, {"vendor_id": "cisco_ios", "sourcetype": "cisco:ios:mdt:metric", "count": 3}]).json()["run_id"])
    assert snap["destination"] == {"name": snap["destination"]["name"], "index": "idx_events", "metric_index": "idx_metrics"}
    metrics = [p for p in sent if p.get("event") == "metric"]
    assert len(metrics) == 3 and all(p["index"] == "idx_metrics" for p in metrics) and all(p["index"] == "idx_events" for p in sent if p.get("event") != "metric")
    dp = snap["metric_accepted"]["datapoints"]
    assert dp > 0 and snap["by_sourcetype"]["cisco:ios:mdt:metric"]["datapoints"] == dp
    with splunk({"cisco:asa": (3, "a")}, metric=dp):
        v = client.post("/api/runs/%s/verify" % snap["run_id"]).json()
    assert v["status"] == "VERIFIED" and v["by_sourcetype"]["cisco:ios:mdt:metric"]["kind"] == "metric" and v["by_sourcetype"]["cisco:ios:mdt:metric"]["indexed"] == dp
    with splunk({"cisco:asa": (3, "a")}, metric=0):
        assert client.post("/api/runs/%s/verify" % snap["run_id"]).json()["status"] == "INCOMPLETE"       # events found, metrics not: not verified


def test_unsupported_sourcetype_rejects_the_whole_request_and_names_it(env):
    sent, _ = env
    r = start(FOUR + [{"vendor_id": "cisco_thousandeyes", "sourcetype": "cisco:thousandeyes:metric", "count": 1}])
    assert r.status_code == 409 and "cisco:thousandeyes:metric" in r.json()["detail"] and not sent


@pytest.mark.parametrize("sources", [[], "x", [{"sourcetype": "cisco:asa", "count": 0}], [{"sourcetype": "cisco:asa", "count": 1}, {"sourcetype": "cisco:asa", "count": 1}], [{"count": 1}]])
def test_bad_selections_are_refused(env, sources):
    assert start(sources).status_code == 422


def test_continuous_multi_run_spreads_events_over_every_source_and_stops(env):
    sent, _ = env
    rid = start(FOUR, mode="continuous", eps=200).json()["run_id"]
    for _ in range(100):
        if client.get("/api/runs/" + rid).json()["counters"]["accepted"] >= 40:
            break
        time.sleep(0.1)
    client.post("/api/runs/%s/stop" % rid)
    snap = done(rid)
    assert snap["state"] == "STOPPED" and snap["mode"] == "continuous"
    assert all(snap["by_sourcetype"][x["sourcetype"]].get("accepted", 0) > 0 for x in FOUR)


def test_a_run_that_delivered_nothing_is_not_completed():
    run = DeliveryRun("scenario", "x", "x", "d", "i", [])
    run.start()
    run.wait(5)
    assert run.state == "FAILED" and run.error == NO_TELEMETRY
