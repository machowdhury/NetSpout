"""No parameterless GET route returns a configured HEC token or search password (sentinels planted in the environment and the transport)."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (str(ROOT / "src"), str(ROOT / "backend")):
    if _p not in sys.path:
        sys.path.insert(0, _p)
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from app import main

TOKEN, PASSWORD = "SENTINEL-HEC-TOKEN-7f3a91", "SENTINEL-SPLUNK-PW-2c8d44"


def test_get_routes_never_return_configured_secrets(monkeypatch):
    monkeypatch.setenv("NETSPOUT_HEC_TOKEN", TOKEN)
    monkeypatch.setenv("NETSPOUT_SPLUNK_PASSWORD", PASSWORD)
    gt = getattr(main.current_topology, "global_transport", None) if main.current_topology else None
    if gt is not None:
        monkeypatch.setattr(gt, "hec_token", TOKEN, raising=False)
        monkeypatch.setattr(gt, "hec_url", "https://example.invalid:8088/services/collector", raising=False)
    # The gNMI preflight route waits ~70 s for a Splunk HEC listener that this test does not have; readiness is not what is under test, so answer "not ready" at once.
    from app.gnmi import splunk_e2e
    monkeypatch.setattr(splunk_e2e.GnmiSplunkBridge, "wait_for_hec_ready",
                        lambda self: {"ready": False, "attempts": 0, "elapsed_ms": 0.0, "error": "not probed in this test"})
    c = TestClient(main.app, raise_server_exceptions=False)
    paths = sorted({r.path for r in main.app.routes if isinstance(r, APIRoute) and "GET" in r.methods and "{" not in r.path})
    assert len(paths) > 40
    leaks = []
    for p in paths:
        body = c.get(p).text          # one request per route (it used to be two, which doubled the run time)
        if TOKEN in body or PASSWORD in body:
            leaks.append(p)
    assert leaks == []
