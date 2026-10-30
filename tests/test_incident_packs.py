"""NetSpout incident packs (27 network + 10 telecom) as runnable scenario packs: modeled telemetry, deterministic, correctly routed."""
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
for _p in (str(ROOT / "src"), str(ROOT / "backend")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from netspout_core import incident_packs as ip  # noqa: E402

CATALOG = ip.catalog()
IDS = ip.incident_ids()


def test_thirty_seven_unique_ids_that_do_not_collide_with_catalog_scenarios():
    assert len(IDS) == len(set(IDS)) == 37
    assert sum(r["family"] == "network" for r in CATALOG) == 27 and sum(r["family"] == "telecom" for r in CATALOG) == 10
    catalog_ids = {s["id"] for s in json.loads((ROOT / "catalog/scenarios.json").read_text())}
    assert not set(IDS) & catalog_ids
    assert all(r["title"] for r in CATALOG)


@pytest.mark.parametrize("scenario_id", IDS)
def test_each_pack_is_30_logs_plus_10_gauges_correlated_by_run_id(scenario_id):
    events = ip.generate_pack(scenario_id, "run-A", now=1_793_400_000.0)
    s = ip.summarize(events)
    assert (s["records"], s["log_events"], s["metric_events"]) == (40, 30, 10)
    assert s["metric_datapoints"] == sum(len(e.get("metrics", {})) for e in events) and 30 <= s["metric_datapoints"] <= 50  # 3 to 5 metrics per gauge record
    assert all(e["fields"]["netspout_run_id"] == "run-A" for e in events)
    assert {e["fields"]["netspout_scenario_id"] for e in events} <= {scenario_id.removeprefix("network_"), scenario_id}
    assert max(e["time"] for e in events) < 1_793_400_000.0  # every record time is already in the past when sent


def test_generation_is_deterministic_and_run_id_only_changes_the_correlation_fields():
    a = ip.generate_pack("network_06_bgp_flap", "run-A", now=1_793_400_000.0)
    assert a == ip.generate_pack("network_06_bgp_flap", "run-A", now=1_793_400_000.0)
    b = ip.generate_pack("network_06_bgp_flap", "run-B", now=1_793_400_000.0)
    assert [e["host"] for e in a] == [e["host"] for e in b] and [e["time"] for e in a] == [e["time"] for e in b]
    assert a != b and not any("run-A" in e["raw"] for e in b)


def test_hec_payloads_send_logs_to_the_event_index_and_gauges_to_the_metric_index():
    events = ip.generate_pack("telco_01_ran_cell", "r", now=1_793_400_000.0)
    payloads = ip.hec_payloads(events, "evt_idx", "met_idx")
    logs = [p for p in payloads if p["index"] == "evt_idx"]
    gauges = [p for p in payloads if p["index"] == "met_idx"]
    assert (len(logs), len(gauges)) == (30, 10)
    assert all(p["event"] != "metric" for p in logs) and all(p["event"] == "metric" for p in gauges)
    assert all(sum(k.startswith("metric_name:") for k in p["fields"]) == len(e["metrics"]) for p, e in zip(gauges, [x for x in events if "metrics" in x]))
    assert not any(k.startswith("metric_name:") for p in logs for k in p["fields"])


def test_unknown_pack_is_refused():
    with pytest.raises(ValueError):
        ip.generate_pack("network_99_nope", "r")


def test_dispatch_requires_an_explicit_transport_and_routes_each_record(monkeypatch):
    from netspout_core.generator_modes import TelemetryGeneratorService
    import netspout_core.generator_modes as gm
    svc = TelemetryGeneratorService()
    with pytest.raises(ValueError):
        svc.generate_universe_scenario("network_01_campus_link", dispatch=True, transport_config=None)
    sent = []
    monkeypatch.setattr(gm.dispatcher, "emit_hec", lambda payload, url, token, ssl_verify=True, allow_insecure_tls=False: sent.append((payload["index"], url)) or (True, "ok"))
    cfg = SimpleNamespace(hec_index="idx_network_ops", hec_metric_index="cisco_mdt_metrics", hec_url="https://127.0.0.1:1/services/collector",
                          hec_token="placeholder", hec_ssl_verify=True, hec_allow_insecure_tls=False)
    out = svc.generate_universe_scenario("network_01_campus_link", run_id="rid", dispatch=True, transport_config=cfg)
    assert out["count_generated"] == 40 and out["event_count"] == 30 and out["metric_datapoints_expected"] >= 30
    assert out["telemetry"] == "MODELED_NETSPOUT_SCHEMA" and all(d["hec"]["success"] for d in out["dispatch_results"])
    assert sorted({i for i, _ in sent}) == ["cisco_mdt_metrics", "idx_network_ops"] and len(sent) == 40


def test_route_checks_the_metric_index_against_the_allowlist(monkeypatch):
    from fastapi.testclient import TestClient
    import app.main as main
    monkeypatch.setattr(main.release_candidate_configuration, "load", lambda: {"configured": True, "indexes": ["idx_network_ops"], "hec_url": "https://127.0.0.1:1/services/collector"})
    gt = main.current_topology.global_transport
    saved = (gt.hec_url, gt.hec_index, gt.hec_metric_index)
    gt.hec_url, gt.hec_index, gt.hec_metric_index = "https://127.0.0.1:1/services/collector", "idx_network_ops", "metrics_not_allowed"
    try:
        r = TestClient(main.app).post("/api/generate/scenario-pack", json={"scenario_id": "network_01_campus_link", "dispatch": True, "index": "idx_network_ops"})
        assert r.status_code == 403 and "Metric index" in r.json()["detail"]
    finally:
        gt.hec_url, gt.hec_index, gt.hec_metric_index = saved


def test_explorer_lists_all_incident_packs_as_runnable_modeled_contracted_scenarios():
    from fastapi.testclient import TestClient
    import app.main as main
    client = TestClient(main.app)
    items = []
    for demo in ("true", "false"):
        items += client.get("/api/explorer/entries", params={"kind": "operational", "limit": 200, "demo_ready": demo}).json()["items"]
    inc = [i for i in items if i["engine"] == "incident_pack"]
    assert len(inc) == 37 and all(i["runnable"] and i["maturity"]["tier"] == "CONTRACTED" and not i["demo_ready"] for i in inc)
    verify = next(s for s in inc[0]["workflow"] if s["step"] == "VERIFY")
    assert "mstats" in verify["success_criterion"] and verify["endpoint"]["body"]["metric_index"]


def test_observe_counts_events_and_metric_datapoints_and_guards_the_metric_index(monkeypatch):
    from fastapi.testclient import TestClient
    import app.main as main
    queries = []
    def fake(q, **kw):
        queries.append(q)
        return ([{"datapoints": "30"}] if q.startswith("| mstats") else [{"count": "30"}]), None
    monkeypatch.setattr(main.release_candidate_configuration, "load", lambda: {"configured": True, "indexes": ["idx_network_ops", "cisco_mdt_metrics"]})
    monkeypatch.setattr(main.release_candidate_configuration, "execute_read_only_search", fake)
    c = TestClient(main.app)
    body = c.post("/api/explorer/observe", json={"index": "idx_network_ops", "run_id": "rid-1", "metric_index": "cisco_mdt_metrics"}).json()
    assert body["indexed_event_count"] == 30 and body["indexed_metric_datapoints"] == 30
    assert any('| mstats count(_value) as datapoints WHERE index="cisco_mdt_metrics" AND metric_name=* AND netspout_run_id="rid-1"' in q for q in queries)  # metric_name=* is required for _value aggregation
    assert c.post("/api/explorer/observe", json={"index": "idx_network_ops", "run_id": "rid-1", "metric_index": "other"}).status_code == 403
    assert c.post("/api/explorer/observe", json={"index": "idx_network_ops", "run_id": "rid 1"}).status_code == 422


def test_committed_live_evidence_covers_every_pack_and_claims_nothing_beyond_delivery_and_metric_fidelity():
    doc = json.loads((ROOT / "docs/verification/evidence/incident_packs/live_results.json").read_text())
    runs = doc["scenario_runs"]
    assert {r["scenario_id"] for r in runs} == set(IDS) and len(runs) == 37
    assert all(r["verdict"] == "PASS" and r["hec_accepted"] == r["generated"] == 40 and r["metric_values_match_generator"] for r in runs)
    assert all(r["metric_datapoints_indexed"] == r["metric_datapoints_expected"] for r in runs)
    assert doc["telemetry"] == "MODELED_NETSPOUT_SCHEMA" and doc["ta_parser_checks_performed"] == 0 and doc["detection_checks_performed"] == 0
