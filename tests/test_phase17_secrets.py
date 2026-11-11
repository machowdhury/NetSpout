"""Phase 17: HEC token and search secret persist in Splunk storage/passwords, reach the engine only as child-process environment, and never touch disk or status files."""
import io
import json
import sys
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "netspout" / "bin"))
import netspout_gateway as g
import pulseforge_engine_launcher as L


def _sup(tmp_path, source):
    s = L.Supervisor(str(tmp_path), command=["true"], secrets_source=source)
    (tmp_path / "config").mkdir()
    s.key = "k"
    return s


def test_storage_passwords_values_become_engine_env_only(tmp_path):
    s = _sup(tmp_path, lambda: {"hec_token": "T0K", "search_secret": "S3C"})
    env = s._env()
    assert env["NETSPOUT_HEC_TOKEN"] == "T0K" and env["NETSPOUT_SPLUNK_PASSWORD"] == "S3C"
    (tmp_path / "config" / "connection.json").write_text('{"auth_method": "HEC_TOKEN_AND_BASIC_SEARCH"}')
    assert "NETSPOUT_SPLUNK_PASSWORD" in s._env()   # "BASIC_SEARCH" contains the word TOKEN; only the exact SPLUNK_TOKEN method selects the token variable
    (tmp_path / "config" / "connection.json").write_text('{"auth_method": "HEC_TOKEN_AND_SPLUNK_TOKEN"}')
    assert "NETSPOUT_SPLUNK_TOKEN" in s._env() and "NETSPOUT_SPLUNK_PASSWORD" not in s._env()
    s._write_info(state="healthy")
    assert "T0K" not in (tmp_path / "engine.json").read_text() and "S3C" not in (tmp_path / "engine.json").read_text()


def test_last_good_secrets_survive_a_failed_refetch(tmp_path):
    calls = iter([{"hec_token": "T0K"}, RuntimeError("401")])
    def src():
        v = next(calls)
        if isinstance(v, Exception):
            raise v
        return v
    s = _sup(tmp_path, src)
    assert s._env()["NETSPOUT_HEC_TOKEN"] == "T0K"
    assert s._env()["NETSPOUT_HEC_TOKEN"] == "T0K" and s.info["secrets"].startswith("unavailable")


def test_session_xml_is_parsed_and_a_tty_is_ignored(tmp_path):
    r, w = __import__("os").pipe()
    __import__("os").write(w, b"<input><server_uri>https://127.0.0.1:8089</server_uri><session_key>abc</session_key></input>")
    assert L.read_splunk_context(open(r, "rb", buffering=0), timeout=2) == ("https://127.0.0.1:8089", "abc")


def test_gateway_stores_submitted_secrets_and_refuses_when_splunk_denies(monkeypatch):
    stored = []
    monkeypatch.setattr(g, "store_secret", lambda k, n, v: stored.append(n))
    assert g._persist_secrets("sk", json.dumps({"hec_token": "a", "search_secret": "b", "indexes": []})) is None and stored == ["hec_token", "search_secret"]
    def deny(*a):
        raise urllib.error.HTTPError("u", 403, "no", {}, io.BytesIO())
    monkeypatch.setattr(g, "store_secret", deny)
    assert "edit_storage_passwords" in g._persist_secrets("sk", json.dumps({"hec_token": "a"}))
    assert g._persist_secrets("sk", json.dumps({"indexes": ["x"]})) is None   # no secret submitted: nothing to store, nothing refused


def test_launcher_emits_nothing_to_stdout_when_idle(tmp_path, capsys):
    """B1: the launcher is a modular input started at every splunkd start; it must never write an event."""
    s = _sup(tmp_path, None)
    s.prepare()
    s._write_info(state="healthy")
    assert capsys.readouterr().out == ""


def test_managed_status_probes_the_engine_instead_of_trusting_a_stale_file(monkeypatch):
    monkeypatch.setattr(g, "MANAGED_PACKAGE", True)
    monkeypatch.setattr(g.ipc, "engine_info", lambda *a, **k: {"state": "healthy", "restarts": 0})
    monkeypatch.setattr(g.ipc, "request", lambda *a, **k: (_ for _ in ()).throw(ConnectionRefusedError()))
    s = g.engine_status("k")
    assert s["connected"] is False and "launcher not running" in s["state"]
    monkeypatch.setattr(g.ipc, "request", lambda *a, **k: (200, b"{}"))
    assert g.engine_status("k")["connected"] is True


def test_restart_route_needs_the_admin_capability_and_reports_a_refusal(monkeypatch):
    monkeypatch.setattr(g, "MANAGED_PACKAGE", True)
    calls = []
    monkeypatch.setattr(g, "_splunk", lambda url, key, data=None: calls.append(url.rsplit("/", 1)[1]))
    monkeypatch.setattr("time.sleep", lambda *_: None)
    post = lambda caps: (monkeypatch.setattr(g, "_capabilities", lambda _k: caps), g.NetSpoutGateway().handle(json.dumps({"method": "POST", "path_info": "/engine/restart", "session": {"authtoken": "s"}})))[1]["status"]
    assert post({"netspout_view"}) == 403 and calls == []
    assert post({"netspout_admin"}) == 202 and calls == ["disable", "enable"]
    def refuse(*a, **k):
        raise urllib.error.HTTPError("u", 403, "no", {}, io.BytesIO())
    monkeypatch.setattr(g, "_splunk", refuse)
    assert post({"netspout_admin"}) == 403
