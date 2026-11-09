"""Gateway authorization by Splunk capability (not role name), checked server-side and failing closed."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "netspout" / "bin"))
import netspout_gateway as g
import pulseforge_ipc


def _call(method, caps, monkeypatch, seen):
    monkeypatch.setattr(g, "_capabilities", lambda _k: caps)
    monkeypatch.setattr(g, "MANAGED_PACKAGE", True)
    monkeypatch.setattr(pulseforge_ipc, "engine_info", lambda *a, **k: {"state": "healthy"})
    monkeypatch.setattr(pulseforge_ipc, "request", lambda m, path, **kw: seen.append((m, path)) or (200, b"{}"))
    monkeypatch.delenv("NETSPOUT_BACKEND_URL", raising=False)
    return g.NetSpoutGateway().handle(json.dumps({"method": method, "path_info": "/api/search", "session": {"authtoken": "s"}, "payload": "{}", "query": []}))["status"]


def test_read_only_users_can_read_but_not_act(monkeypatch):
    seen = []
    assert _call("GET", {"netspout_view"}, monkeypatch, seen) == 200
    assert _call("POST", {"netspout_view"}, monkeypatch, seen) == 403
    assert seen == [("GET", "/api/search")]                         # the refused POST never reached the engine


def test_admin_capability_allows_actions_and_a_user_with_no_capability_is_refused(monkeypatch):
    seen = []
    assert _call("POST", {"netspout_view", "netspout_admin"}, monkeypatch, seen) == 200
    assert _call("GET", set(), monkeypatch, seen) == 403
    assert _call("POST", {"admin_all_objects"}, monkeypatch, seen) == 403   # other powerful capabilities do not substitute


def test_capabilities_are_granted_by_the_app_not_by_a_hardcoded_role_list():
    conf = (ROOT / "netspout" / "default" / "authorize.conf").read_text()
    for cap in ("netspout_admin", "netspout_view"):
        assert "[capability::%s]" % cap in conf
    assert "[role_user]\nnetspout_view = enabled" in conf
    for role in ("admin", "sc_admin", "power"):
        assert "[role_%s]\nnetspout_admin = enabled" % role in conf
    assert "WRITE_ROLES" not in (ROOT / "netspout" / "bin" / "netspout_gateway.py").read_text()


def test_capability_lookup_is_cached_by_hash_and_never_stores_the_raw_token(monkeypatch):
    calls = []

    class R:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self): return json.dumps({"entry": [{"content": {"capabilities": ["netspout_view"]}}]}).encode()

    monkeypatch.setattr(g.urllib.request, "urlopen", lambda req, timeout=0, context=None: calls.append(1) or R())
    g._caps_cache.clear()
    assert g._capabilities("raw-session-token") == {"netspout_view"}
    assert g._capabilities("raw-session-token") == {"netspout_view"}
    assert len(calls) == 1 and "raw-session-token" not in "".join(map(str, g._caps_cache))


def test_managed_package_never_falls_back_to_a_tcp_engine(tmp_path, monkeypatch):
    """Single-package build (MANAGED_ENGINE marker): no engine status record means a clear 503, never a call to 127.0.0.1:8081."""
    import json
    import netspout_gateway as g
    monkeypatch.setattr(g, "MANAGED_PACKAGE", True)
    monkeypatch.setattr(g, "_capabilities", lambda _k: {"netspout_view"})
    monkeypatch.setenv("PULSEFORGE_STATE_DIR", str(tmp_path))
    monkeypatch.setenv("NETSPOUT_BACKEND_URL", "http://127.0.0.1:8081")   # even an explicit URL is ignored in this build
    called = []
    monkeypatch.setattr(g.urllib.request, "urlopen", lambda *a, **k: called.append(a) or (_ for _ in ()).throw(AssertionError("TCP fallback used")))
    r = g.NetSpoutGateway().handle(json.dumps({"method": "GET", "path_info": "/api/health", "session": {"authtoken": "s"}}))
    assert r["status"] == 503 and not called
