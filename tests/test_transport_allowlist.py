"""Caller-supplied transport_config must obey the Connection Center destination and index allowlist on every route."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
for _p in (str(ROOT / "src"), str(ROOT / "backend")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from fastapi import HTTPException  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

CONFIGURED = {"configured": True, "hec_url": "https://127.0.0.1:18088/services/collector", "indexes": ["idx_network_ops", "cisco_mdt_metrics"]}
GOOD = {"hec_url": "https://127.0.0.1:18088/services/collector", "hec_token": "placeholder-not-real", "hec_index": "idx_network_ops", "hec_metric_index": "cisco_mdt_metrics"}


@pytest.fixture()
def main(monkeypatch):
    import app.main as m
    monkeypatch.setattr(m.release_candidate_configuration, "load", lambda: dict(CONFIGURED))
    return m


def test_matching_destination_and_allowed_indexes_are_accepted(main):
    cfg = main._authorize_caller_transport(dict(GOOD))
    assert (cfg.hec_index, cfg.hec_metric_index) == ("idx_network_ops", "cisco_mdt_metrics")


@pytest.mark.parametrize("override,status", [
    ({"hec_index": "secret_index"}, 403),                                        # event index off the allowlist
    ({"hec_metric_index": "secret_metrics"}, 403),                               # metric index off the allowlist
    ({"hec_url": "https://attacker.example:8088/services/collector"}, 403),      # token + events redirected elsewhere
    ({"hec_url": "https://127.0.0.1:9999/services/collector"}, 403),             # same host, different port
    ({"hec_index": "bad index!"}, 422),                                           # unsafe name is rejected before any lookup
])
def test_caller_config_outside_the_connection_center_is_refused(main, override, status):
    with pytest.raises(HTTPException) as err:
        main._authorize_caller_transport({**GOOD, **override})
    assert err.value.status_code == status


def test_defaulted_indexes_are_checked_too(main):
    # a minimal caller config that omits indexes would otherwise send to the model's default indexes
    with pytest.raises(HTTPException) as err:
        main._authorize_caller_transport({"hec_url": GOOD["hec_url"], "hec_token": "x", "hec_index": "idx_network_ops", "hec_metric_index": "not_allowed_default"})
    assert err.value.status_code == 403


def test_scenario_pack_route_refuses_before_generating_or_sending(main, monkeypatch):
    from app.generator_modes import generator_service
    called = []
    monkeypatch.setattr(generator_service, "generate_universe_scenario", lambda *a, **k: called.append(1) or {})
    r = TestClient(main.app).post("/api/generate/scenario-pack", json={"scenario_id": "ub5_cisco_nac_radius_outage", "dispatch": True,
                                                                          "transport_config": {**GOOD, "hec_index": "secret_index"}})
    assert r.status_code == 403 and not called


def test_scenario_run_route_refuses_and_never_replaces_the_saved_transport(main):
    before = main.current_topology.global_transport
    r = TestClient(main.app).post("/api/scenarios/cisco_aci_microburst/run", json={"transport_config": {**GOOD, "hec_url": "https://attacker.example:8088/services/collector"}})
    assert r.status_code == 403
    assert main.current_topology.global_transport is before


def test_unconfigured_connection_center_keeps_legacy_behavior_with_safe_names(monkeypatch):
    import app.main as m
    monkeypatch.setattr(m.release_candidate_configuration, "load", lambda: {"configured": False})
    assert m._authorize_caller_transport(dict(GOOD)).hec_index == "idx_network_ops"
    with pytest.raises(HTTPException) as err:
        m._authorize_caller_transport({**GOOD, "hec_index": "bad index!"})
    assert err.value.status_code == 422
