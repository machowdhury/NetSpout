"""Opt-in gateway key: the engine refuses direct calls when PULSEFORGE_GATEWAY_KEY is set; the Splunk gateway forwards it."""
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (str(ROOT / "src"), str(ROOT / "backend"), str(ROOT / "netspout" / "bin")):
    if p not in sys.path:
        sys.path.insert(0, p)
from fastapi.testclient import TestClient

from app import main
import netspout_gateway


def test_engine_is_open_when_no_key_is_configured(monkeypatch):
    monkeypatch.delenv("PULSEFORGE_GATEWAY_KEY", raising=False)
    assert TestClient(main.app).get("/api/search", params={"q": "NF-SEC-06"}).status_code == 200


def test_engine_rejects_direct_calls_when_a_key_is_configured_but_keeps_health_open(monkeypatch):
    monkeypatch.setenv("PULSEFORGE_GATEWAY_KEY", "k-test")
    c = TestClient(main.app)
    assert c.get("/api/health").status_code == 200
    assert c.get("/api/search", params={"q": "x"}).status_code == 401
    assert c.post("/api/runs", json={}).status_code == 401
    assert c.get("/api/search", params={"q": "x"}, headers={"X-PulseForge-Gateway-Key": "wrong"}).status_code == 401
    assert c.get("/api/search", params={"q": "NF-SEC-06"}, headers={"X-PulseForge-Gateway-Key": "k-test"}).status_code == 200


def test_gateway_forwards_the_key_only_when_configured(monkeypatch):
    seen = []

    class R:
        status = 200
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self): return b"{}"

    monkeypatch.setattr(urllib.request, "urlopen", lambda req, timeout=0: seen.append(dict(req.header_items())) or R())
    req = json.dumps({"method": "GET", "path_info": "/api/health", "session": {"authtoken": "s"}, "query": []})
    monkeypatch.delenv("PULSEFORGE_GATEWAY_KEY", raising=False)
    netspout_gateway.NetSpoutGateway().handle(req)
    monkeypatch.setenv("PULSEFORGE_GATEWAY_KEY", "k-test")
    netspout_gateway.NetSpoutGateway().handle(req)
    assert "X-pulseforge-gateway-key" not in seen[0] and seen[1]["X-pulseforge-gateway-key"] == "k-test"
