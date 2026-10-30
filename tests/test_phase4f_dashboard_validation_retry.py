"""Dashboard validation tolerates Splunk indexing latency but never invents rows."""
import sys
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
for _p in (str(ROOT / "backend"), str(ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

DASH = "scenario-sec-p9-b-dns-anomaly"


def _setup(monkeypatch, rows_for_attempt):
    from app import main

    pack = main.dashboard_recipe_service.generate(DASH, run_id="r1", index="idx_network_ops")
    run = SimpleNamespace(scenario_id=pack.runtime_scenario_id, selection_id=pack.runtime_scenario_id, channel_results=[])
    monkeypatch.setattr(main.unified_generation_service, "get_run", lambda _id: run)
    monkeypatch.setattr(main.time, "sleep", lambda _s: None)
    calls = {}

    def execute(query, _cfg):
        calls[query] = calls.get(query, 0) + 1
        return rows_for_attempt(pack, query, calls[query]), None

    monkeypatch.setattr(main.unified_generation_service, "execute_bounded_spl", execute)
    monkeypatch.setattr(main, "_unified_transport_config", lambda: None)
    return main, pack, calls


def _full_row(pack, query):
    panel = next(p for p in pack.panels if p.query == query)
    return [{f: "1" for f in panel.expected_shape}]


def test_empty_panels_are_retried_until_rows_arrive(monkeypatch):
    main, pack, calls = _setup(monkeypatch, lambda pack, q, n: [] if n < 3 else _full_row(pack, q))
    body = TestClient(main.app).post(f"/api/dashboards/{DASH}/validate", json={"run_id": "r1", "index": "idx_network_ops"}).json()
    assert body["maturity"] == "DATA_VALIDATED", body["failures"]
    assert max(calls.values()) == 3


def test_never_indexed_data_stays_unvalidated_after_bounded_retries(monkeypatch):
    main, pack, calls = _setup(monkeypatch, lambda pack, q, n: [])
    body = TestClient(main.app).post(f"/api/dashboards/{DASH}/validate", json={"run_id": "r1", "index": "idx_network_ops"}).json()
    assert body["maturity"] != "DATA_VALIDATED"
    assert max(calls.values()) == main.DASHBOARD_PANEL_RETRIES
