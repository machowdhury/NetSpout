"""
Splunk modular input that runs the PulseForge engine as a Splunk-managed child process. Phase 1 prototype, standard library only.

splunkd starts this script (python.version and python.required set in inputs.conf.spec); it keeps the engine alive on a private
Unix socket and stops it when splunkd stops it. Lifecycle:

  start    create the state directory, a persistent per-install key (0600) and a lock (one launcher per host), spawn the engine
  health   probe GET /api/health over the socket; the status record engine.json carries state, pid, restarts and the last error
  restart  engine exits or stops answering -> restart with backoff (1, 2, 4 ... 30 s; the counter resets after 60 s of health)
  stop     SIGTERM/SIGINT or splunkd gone -> SIGTERM the engine (it finishes in-flight deliveries and persists counters), kill after
           the grace period, remove the socket, record "stopped"

Nothing is resumed after a restart: active runs are reported INTERRUPTED by the engine and never re-sent. Configuration lives in the
state directory (NETSPOUT_CONFIG_DIR), outside the app directory, so upgrades keep it.
"""
import fcntl
import json
import os
import secrets
import signal
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pulseforge_ipc as ipc  # noqa: E402

SCHEME = """<scheme>
  <title>PulseForge engine</title>
  <description>Runs the PulseForge engine as a Splunk-managed process on a private socket</description>
  <use_external_validation>false</use_external_validation>
  <use_single_instance>true</use_single_instance>
  <streaming_mode>simple</streaming_mode>
  <endpoint><args></args></endpoint>
</scheme>"""
PASS_ENV = ("PATH", "HOME", "LANG", "LC_ALL", "SPLUNK_HOME", "LD_LIBRARY_PATH", "DYLD_LIBRARY_PATH", "PYTHONHOME", "OPENSSL_CONF", "OPENSSL_MODULES",
            "NETSPOUT_HEC_TOKEN", "NETSPOUT_SPLUNK_PASSWORD")  # shortcut: secrets still come from the environment, not storage/passwords; Phase 3


def ensure_key(directory):
    """Create the per-install key once (0600, exclusive create); later calls and later starts return the same key."""
    path = Path(directory) / ipc.KEY_FILE
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as f:
            f.write(secrets.token_urlsafe(32))
    except FileExistsError:
        pass
    os.chmod(path, 0o600)
    return path.read_text().strip()


class Supervisor:
    def __init__(self, directory, command=None, grace=15, healthy_after=60, probe_every=2, parent_pid=None):
        self.dir = Path(directory)
        self.sock = self.dir / ipc.SOCKET_FILE
        self.command = command or [sys.executable, str(Path(__file__).resolve().parent / "pulseforge_engine_main.py"), "--uds", str(self.sock)]
        self.grace, self.healthy_after, self.probe_every = grace, healthy_after, probe_every
        self.parent_pid = parent_pid
        self.proc = None
        self.info = {"state": "stopped", "pid": None, "restarts": 0, "last_error": None, "transport": "uds", "socket": str(self.sock)}
        self._stop = False
        self._lock = None

    # state -------------------------------------------------------------------------------------------------------------------
    def _write_info(self, **kw):
        self.info.update(kw)
        tmp = self.dir / (ipc.INFO_FILE + ".tmp")
        tmp.write_text(json.dumps(self.info))
        os.chmod(tmp, 0o600)
        tmp.replace(self.dir / ipc.INFO_FILE)

    def prepare(self):
        self.dir.mkdir(parents=True, exist_ok=True)
        os.chmod(self.dir, 0o700)
        (self.dir / "config").mkdir(exist_ok=True)
        self._lock = open(self.dir / "launcher.lock", "w")
        try:
            fcntl.flock(self._lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            raise SystemExit("another PulseForge launcher already owns %s" % self.dir)
        self.key = ensure_key(self.dir)

    def _env(self):
        env = {k: os.environ[k] for k in PASS_ENV if k in os.environ}
        env.update(PULSEFORGE_GATEWAY_KEY=self.key, PULSEFORGE_REQUIRE_GATEWAY_KEY="1", PYTHONUNBUFFERED="1",
                   NETSPOUT_CONFIG_DIR=str(self.dir / "config"), NETSPOUT_REPLAY_STATE=str(self.dir / "config" / "replay_sessions.json"),
                   NETSPOUT_RUNS_STATE=str(self.dir / "config" / "runs.json"))
        return env

    # child -------------------------------------------------------------------------------------------------------------------
    def _spawn(self):
        if self.sock.exists():
            self.sock.unlink()
        self.proc = subprocess.Popen(self.command, env=self._env(), stdin=subprocess.DEVNULL)
        self._write_info(state="starting", pid=self.proc.pid)

    def healthy(self):
        try:
            status, body = ipc.request("GET", "/api/health", timeout=3, directory=str(self.dir))
            return status == 200 and b"healthy" in body
        except Exception:
            return False

    def _terminate(self):
        if not self.proc or self.proc.poll() is not None:
            return
        self.proc.terminate()
        try:
            self.proc.wait(self.grace)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            self.proc.wait(5)

    def stop(self):
        self._stop = True

    def run(self):
        self.prepare()
        backoff, healthy_since = 1, None
        try:
            self._spawn()
            while not self._stop:
                if self.parent_pid and os.getppid() != self.parent_pid:
                    break  # splunkd went away; do not leave an orphan engine
                time.sleep(self.probe_every)
                code = self.proc.poll()
                if code is not None:
                    self._write_info(state="restarting", pid=None, restarts=self.info["restarts"] + 1, last_error="engine exited with code %s" % code)
                    healthy_since = None
                    for _ in range(int(backoff * 10)):
                        if self._stop:
                            break
                        time.sleep(0.1)
                    backoff = min(backoff * 2, 30)
                    if not self._stop:
                        self._spawn()
                elif self.healthy():
                    healthy_since = healthy_since or time.monotonic()
                    if self.info["state"] != "healthy":
                        self._write_info(state="healthy")
                    if time.monotonic() - healthy_since > self.healthy_after:
                        backoff = 1
                elif self.info["state"] == "healthy":
                    self._write_info(state="unresponsive", last_error="health probe failed")
        finally:
            self._write_info(state="stopping")
            self._terminate()
            if self.sock.exists():
                self.sock.unlink()
            self._write_info(state="stopped", pid=None)


def main(argv):
    if "--scheme" in argv:
        print(SCHEME)
        return 0
    if "--validate-arguments" in argv:
        return 0
    sup = Supervisor(ipc.state_dir(), parent_pid=os.getppid())
    for s in (signal.SIGTERM, signal.SIGINT):
        signal.signal(s, lambda *_: sup.stop())
    sup.run()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
