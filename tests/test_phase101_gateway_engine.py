"""Phase 10.1: the gateway talks only to the engine the customer configured; nothing is guessed."""
import json
import sys
import urllib.error
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "netspout" / "bin"))
import netspout_gateway as g  # noqa: E402


@pytest.fixture
def gw(monkeypatch):
    monkeypatch.setattr(g, "_capabilities", lambda _k: {"netspout_admin", "netspout_view"})
    return g.NetSpoutGateway()


def call(gw, method="GET", path="/api/runs", payload=None):
    r = gw.handle(json.dumps({"method": method, "path_info": path, "session": {"authtoken": "k"}, "payload": json.dumps(payload) if payload is not None else ""}))
    return r["status"], json.loads(r["payload"])


def conf(monkeypatch, url):
    def fake(u, key, data=None):
        if data is None:
            if url is None:
                raise urllib.error.HTTPError(u, 404, "nf", {}, None)
            return {"entry": [{"content": {"url": url}}]}
        conf.saved = data["url"]
        return {}
    monkeypatch.setattr(g, "_splunk", fake)


def test_no_default_engine_not_configured(gw, monkeypatch):
    conf(monkeypatch, "")
    monkeypatch.delenv("NETSPOUT_BACKEND_URL", raising=False)
    assert call(gw) == (503, g.NOT_CONFIGURED)
    assert call(gw, path="/engine") == (200, {"configured": False, "connected": False, "url": "", "message": "Engine not configured."})


def test_env_variable_is_not_a_fallback(gw, monkeypatch):
    conf(monkeypatch, "")
    monkeypatch.setenv("NETSPOUT_BACKEND_URL", "http://127.0.0.1:8081")
    assert call(gw)[0] == 503


def test_missing_conf_file_entry_is_not_configured(gw, monkeypatch):
    conf(monkeypatch, None)
    assert call(gw)[0] == 503


def test_unreachable_engine_says_not_connected(gw, monkeypatch):
    conf(monkeypatch, "http://127.0.0.1:1")
    assert call(gw) == (502, g.NOT_CONNECTED)
    s, body = call(gw, path="/engine")
    assert s == 200 and body["configured"] and not body["connected"] and body["message"] == "Engine not connected."


def test_forwards_to_exactly_the_configured_engine(gw, monkeypatch):
    conf(monkeypatch, "http://engine.example:8081")
    seen = []

    class R:
        status = 200
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self): return b'{"runs":[]}'
    monkeypatch.setattr(g.urllib.request, "urlopen", lambda req, timeout=0: seen.append(req.full_url) or R())
    assert call(gw, path="/api/runs") == (200, {"runs": []})
    assert seen == ["http://engine.example:8081/api/runs"]


@pytest.mark.parametrize("bad", ["ftp://h", "http://", "http://u:p@h:1", "http://h:1/x", "http://h:1?q=1", "notaurl"])
def test_engine_url_validation(gw, monkeypatch, bad):
    conf(monkeypatch, "")
    assert call(gw, "POST", "/engine", {"url": bad})[0] == 422


def test_saving_requires_a_write_role_and_stores_normalized_url(gw, monkeypatch):
    conf(monkeypatch, "")
    conf.saved = None
    monkeypatch.setattr(g, "_capabilities", lambda _k: {"netspout_view"})
    assert call(gw, "POST", "/engine", {"url": "http://h:8081"})[0] == 403 and conf.saved is None
    monkeypatch.setattr(g, "_capabilities", lambda _k: {"netspout_admin", "netspout_view"})
    s, body = call(gw, "POST", "/engine", {"url": " http://h:8081/ "})
    assert s == 200 and conf.saved == "http://h:8081"


def test_a_changed_engine_url_applies_to_the_very_next_request(gw, monkeypatch):
    urls = iter(["http://engine-a:8081", "http://engine-b:8081", ""])
    seen = []
    monkeypatch.setattr(g, "_splunk", lambda u, key, data=None: {"entry": [{"content": {"url": next(urls)}}]})
    monkeypatch.setattr(g, "_forward", lambda base, *a, **k: seen.append(base) or (200, {}), raising=False)
    assert g.configured_engine("k") == "http://engine-a:8081"
    assert g.configured_engine("k") == "http://engine-b:8081"      # no cache: the second read sees the new value at once
    assert g.configured_engine("k") == ""


def test_run_authorization_is_enforced_by_the_gateway_not_the_page(gw, monkeypatch):
    conf(monkeypatch, "http://engine:8081")
    monkeypatch.setattr(g, "_capabilities", lambda _k: {"netspout_view"})            # a read-only Splunk user
    calls = []
    monkeypatch.setattr(g.urllib.request, "urlopen", lambda *a, **k: calls.append(a) or (_ for _ in ()).throw(AssertionError("must not reach the engine")))
    for method, path in (("POST", "/api/runs"), ("POST", "/api/runs/run-1/stop"), ("POST", "/engine")):
        status, body = call(gw, method, path, {"url": "http://x:1"} if path == "/engine" else {})
        assert status == 403 and "admin or power" in body["detail"], (method, path, status)
    assert call(gw, "DELETE", "/api/runs/run-1")[0] == 404          # other methods are not routed at all
    assert not calls
