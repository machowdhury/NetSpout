"""Phase 1 prototype (offline): the Splunk-managed engine's bootstrap, private channel, supervision, graceful stop and no-resume rules.
No Splunk is involved; the launcher is exercised with the real engine as a subprocess on a Unix socket."""
import http.client
import json
import os
import shutil
import signal
import socket
import stat
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BIN = ROOT / "netspout" / "bin"
for _p in (str(ROOT / "src"), str(ROOT / "backend"), str(BIN)):
    if _p not in sys.path:
        sys.path.insert(0, _p)
import pulseforge_engine_launcher as launcher
import pulseforge_engine_main as engine_main
import pulseforge_ipc as ipc
from fastapi.testclient import TestClient

from app import main
from netspout_core.delivery_monitor import ACTIVE, DeliveryRun, Item, RunMonitorService


@pytest.fixture
def state():
    d = tempfile.mkdtemp(prefix="pf")  # short path: Unix socket paths are limited to about 100 characters
    yield d
    shutil.rmtree(d, ignore_errors=True)


def _raw(directory, path, key=None):
    """A request over the engine socket made the way an attacker with socket access (but no key) would."""
    class C(http.client.HTTPConnection):
        def connect(self):
            self.sock = socket.socket(socket.AF_UNIX)
            self.sock.connect(os.path.join(directory, ipc.SOCKET_FILE))
    c = C("localhost", timeout=10)
    c.request("GET", path, headers={ipc.KEY_HEADER: key} if key else {})
    r = c.getresponse()
    return r.status


def _wait(cond, seconds=60):
    end = time.time() + seconds
    while time.time() < end:
        if cond():
            return True
        time.sleep(0.2)
    return False


def test_key_is_created_once_private_and_stable(state):
    k1 = launcher.ensure_key(state)
    k2 = launcher.ensure_key(state)
    assert k1 == k2 and len(k1) >= 32
    assert stat.S_IMODE(os.stat(Path(state) / ipc.KEY_FILE).st_mode) == 0o600


def test_bootstrap_refuses_a_public_bind_and_a_missing_key():
    env = {**os.environ, "PULSEFORGE_GATEWAY_KEY": "k"}
    pub = subprocess.run([sys.executable, str(BIN / "pulseforge_engine_main.py"), "--host", "0.0.0.0", "--port", "1"], env=env, capture_output=True, text=True, timeout=30)
    assert pub.returncode == 2 and "loopback or socket only" in pub.stderr
    env.pop("PULSEFORGE_GATEWAY_KEY")
    nokey = subprocess.run([sys.executable, str(BIN / "pulseforge_engine_main.py"), "--uds", "/nonexistent/x.sock"], env=env, capture_output=True, text=True, timeout=30)
    assert nokey.returncode == 2 and "PULSEFORGE_GATEWAY_KEY is required" in nokey.stderr


def test_vendored_dependencies_are_selected_by_interpreter_and_platform():
    tag = engine_main.platform_tag()
    assert tag.startswith("py%d%d-" % sys.version_info[:2]) and tag.count("-") == 2


def test_supervisor_lifecycle_private_socket_restart_and_graceful_stop(state):
    sup = launcher.Supervisor(state, grace=20, probe_every=0.3)
    t = threading.Thread(target=sup.run, daemon=True)
    t.start()
    try:
        assert _wait(lambda: sup.info["state"] == "healthy"), sup.info
        first_pid = sup.info["pid"]
        # private channel: socket is 0600, directory 0700, key file 0600
        assert stat.S_IMODE(os.stat(Path(state) / ipc.SOCKET_FILE).st_mode) == 0o600
        assert stat.S_IMODE(os.stat(state).st_mode) == 0o700
        assert stat.S_IMODE(os.stat(Path(state) / ipc.KEY_FILE).st_mode) == 0o600
        # authentication is mandatory in this architecture
        key = ipc.read_key(state)
        assert _raw(state, "/api/search?q=NF-SEC-06") == 401
        assert _raw(state, "/api/search?q=NF-SEC-06", key="wrong") == 401
        assert _raw(state, "/api/search?q=NF-SEC-06", key=key) == 200
        assert _raw(state, "/api/health") == 200
        status, body = ipc.request("GET", "/api/search?q=NF-SEC-06", directory=state)
        assert status == 200 and json.loads(body)["total"] >= 1
        # no TCP listener at all
        if shutil.which("lsof"):
            out = subprocess.run(["lsof", "-nP", "-a", "-p", str(first_pid), "-iTCP", "-sTCP:LISTEN"], capture_output=True, text=True).stdout
            assert out.strip() == "", out
        # engine crash -> restart with a new pid, healthy again
        os.kill(first_pid, signal.SIGKILL)
        assert _wait(lambda: sup.info["restarts"] == 1 and sup.info["state"] == "healthy" and sup.info["pid"] != first_pid), sup.info
        assert "exited" in sup.info["last_error"]
        second_pid = sup.info["pid"]
    finally:
        sup.stop()
        t.join(60)
    # graceful stop: engine gone, socket removed, state recorded
    assert not t.is_alive() and sup.info["state"] == "stopped"
    assert not (Path(state) / ipc.SOCKET_FILE).exists()
    with pytest.raises(ProcessLookupError):
        os.kill(second_pid, 0)
    # the key survives a restart of the launcher (configuration persistence)
    assert launcher.ensure_key(state) == key


def test_second_launcher_on_the_same_state_directory_is_refused(state):
    a = launcher.Supervisor(state)
    a.prepare()
    with pytest.raises(SystemExit):
        launcher.Supervisor(state).prepare()


def test_scheme_is_a_single_instance_modular_input(capsys):
    assert launcher.main(["--scheme"]) == 0
    out = capsys.readouterr().out
    assert "<use_single_instance>true</use_single_instance>" in out and "PulseForge engine" in out


def test_shutdown_stops_active_runs_and_a_restart_never_resumes_them(state):
    persisted = Path(state) / "runs.json"
    svc = RunMonitorService(persisted)
    main.run_monitor = svc
    def slow(i):
        def send():
            time.sleep(0.05)
            return "accepted", None
        return Item("x:y", "P1", send)
    with TestClient(main.app):
        run = svc.start(DeliveryRun("sourcetype", "x:y", "x:y", "d", "i", [slow(i) for i in range(400)]))
        assert _wait(lambda: run.snapshot()["counters"]["attempts"] > 0, 10)
    snap = run.snapshot()                      # leaving the app context ran the lifespan shutdown
    assert snap["state"] not in ACTIVE and snap["counters"]["attempts"] < 400
    attempts = snap["counters"]["attempts"]
    time.sleep(0.3)
    assert run.snapshot()["counters"]["attempts"] == attempts
    # an active run found in persisted state after a restart is INTERRUPTED and nothing is re-sent
    data = json.loads(persisted.read_text())
    data[run.id]["state"] = "RUNNING"
    persisted.write_text(json.dumps(data))
    reborn = RunMonitorService(persisted)
    assert reborn.get(run.id) is None or reborn.get(run.id).snapshot()["state"] == "INTERRUPTED"
    assert reborn.snapshot(run.id)["state"] == "INTERRUPTED"


def test_gateway_reaches_the_managed_engine_over_the_socket_and_reports_it_down(state, monkeypatch):
    import netspout_gateway
    monkeypatch.setenv("PULSEFORGE_STATE_DIR", state)
    monkeypatch.delenv("NETSPOUT_BACKEND_URL", raising=False)
    monkeypatch.delenv("PULSEFORGE_GATEWAY_KEY", raising=False)
    monkeypatch.setattr(netspout_gateway, "_capabilities", lambda _k: {"netspout_view"})
    call = lambda path: netspout_gateway.NetSpoutGateway().handle(json.dumps({"method": "GET", "path_info": path, "session": {"authtoken": "s"}, "query": [["q", "NF-SEC-06"]]}))
    sup = launcher.Supervisor(state, grace=20, probe_every=0.3)
    t = threading.Thread(target=sup.run, daemon=True)
    t.start()
    try:
        assert _wait(lambda: sup.info["state"] == "healthy"), sup.info
        r = call("/api/search")
        assert r["status"] == 200 and json.loads(r["payload"])["total"] >= 1      # key added by the gateway, never by the browser
        assert netspout_gateway.NetSpoutGateway().handle(json.dumps({"method": "GET", "path_info": "/api/health", "session": {}}))["status"] == 401   # Splunk session still required
    finally:
        sup.stop()
        t.join(60)
    assert call("/api/search")["status"] == 502                                      # engine stopped: a clear error, not a hang


def test_engine_interpreter_prefers_splunks_python313_and_refuses_old_pythons(tmp_path, monkeypatch):
    monkeypatch.setenv("SPLUNK_HOME", str(tmp_path))
    (tmp_path / "bin").mkdir()
    (tmp_path / "bin" / "python3.13").write_text("")
    assert launcher.engine_python() == str(tmp_path / "bin" / "python3.13")
    (tmp_path / "bin" / "python3.13").unlink()
    assert launcher.engine_python() == sys.executable                      # this test interpreter is new enough
    monkeypatch.setattr(sys, "version_info", (3, 9, 0, "final", 0))
    with pytest.raises(SystemExit):
        launcher.engine_python()
