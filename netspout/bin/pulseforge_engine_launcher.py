"""
Splunk modular input that runs the PulseForge engine as a Splunk-managed child process. Phase 1 prototype, standard library only.

splunkd starts this script (python.version and python.required set in inputs.conf.spec); it keeps the engine alive on a private
Unix socket and stops it when splunkd stops it. Lifecycle:

  start    create the state directory, a persistent per-install key (0600) and a lock (one launcher per host), spawn the engine
  health   probe GET /api/health over the socket; the status record engine.json carries state, pid, restarts and the last error
  restart  engine exits or stops answering -> restart with backoff (1, 2, 4 ... 30 s; the counter resets after 60 s of health)
  stop     SIGTERM/SIGINT or splunkd stopped (its pid file gone or changed) -> SIGTERM the engine (it finishes in-flight deliveries and persists counters), kill after
           the grace period, remove the socket, record "stopped"

Nothing is resumed after a restart: active runs are reported INTERRUPTED by the engine and never re-sent. Configuration lives in the
state directory (NETSPOUT_CONFIG_DIR), outside the app directory, so upgrades keep it.
"""
import fcntl
import json
import os
import re
import secrets
import select
import signal
import ssl
import subprocess
import sys
import time
import urllib.parse
import urllib.request
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
            "NETSPOUT_HEC_TOKEN", "NETSPOUT_SPLUNK_PASSWORD")  # explicit-deployment overrides; storage/passwords values (below) take precedence
_LOOPBACK_CTX = ssl.create_default_context()
_LOOPBACK_CTX.check_hostname = False  # the management port is this splunkd on loopback with a self-signed certificate
_LOOPBACK_CTX.verify_mode = ssl.CERT_NONE


def read_splunk_context(stream=None, timeout=5.0):
    """splunkd writes the modular-input configuration XML (server_uri, session_key) to stdin. Returns (server_uri, session_key) or (None, None)."""
    fd = (stream or sys.stdin).fileno() if (stream or sys.stdin) else None
    if fd is None or os.isatty(fd):
        return None, None
    buf, end = "", time.monotonic() + timeout
    while time.monotonic() < end and "</input>" not in buf and "</items>" not in buf:
        ready, _, _ = select.select([fd], [], [], 0.5)
        if ready:
            chunk = os.read(fd, 65536).decode("utf-8", "replace")
            if not chunk:
                break
            buf += chunk
    uri, key = re.search(r"<server_uri>([^<]+)</server_uri>", buf), re.search(r"<session_key>([^<]+)</session_key>", buf)
    return (uri.group(1) if uri else None), (key.group(1) if key else None)


def fetch_secrets(server_uri, session_key, app="netspout", realm="netspout"):
    """The app's credentials from Splunk's encrypted storage/passwords: {username: clear_password}. Raises on any failure; values are never logged."""
    url = "%s/servicesNS/nobody/%s/storage/passwords?output_mode=json&count=0&search=%s" % (server_uri.rstrip("/"), app, urllib.parse.quote("realm=" + realm))
    req = urllib.request.Request(url, headers={"Authorization": "Splunk " + session_key})
    with urllib.request.urlopen(req, timeout=10, context=_LOOPBACK_CTX) as r:
        entries = json.loads(r.read().decode())["entry"]
    out = {}
    for e in entries:
        c = e["content"]
        if c.get("realm") == realm and c.get("clear_password"):
            out[c["username"]] = c["clear_password"]
    return out


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


def engine_python():
    """The interpreter for the engine. The pinned fastapi/pydantic need Python >= 3.10, so prefer Splunk's bundled 3.13 even if this
    launcher itself was started with an older interpreter; fall back to the launcher's own only when it is new enough."""
    candidate = Path(os.environ.get("SPLUNK_HOME", "/opt/splunk")) / "bin" / "python3.13"
    if candidate.is_file():
        return str(candidate)
    if sys.version_info >= (3, 10):
        return sys.executable
    raise SystemExit("PulseForge engine needs Python 3.10+ (Splunk's bundled python3.13 was not found and this interpreter is %d.%d)" % sys.version_info[:2])


class Supervisor:
    def __init__(self, directory, command=None, grace=15, healthy_after=60, probe_every=2, parent_pid=None, splunkd_pid_file=None, lock_wait=0, secrets_source=None):
        self.dir = Path(directory)
        self.sock = self.dir / ipc.SOCKET_FILE
        self.command = command or [engine_python(), str(Path(__file__).resolve().parent / "pulseforge_engine_main.py"), "--uds", str(self.sock)]
        self.grace, self.healthy_after, self.probe_every = grace, healthy_after, probe_every
        self.parent_pid = parent_pid
        self.pid_file, self.lock_wait, self.splunkd_pid = splunkd_pid_file, lock_wait, None
        self.secrets_source = secrets_source  # callable returning {name: value} from storage/passwords, or None
        self._secrets = {}  # in launcher memory only; reused if a later fetch fails (the session key may have expired)
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
        end = time.monotonic() + self.lock_wait  # a restarting splunkd may start us while the previous launcher is still shutting down
        while True:
            try:
                fcntl.flock(self._lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError:
                if time.monotonic() >= end:
                    raise SystemExit("another PulseForge launcher already owns %s" % self.dir)
                time.sleep(0.5)
        self.splunkd_pid = self._read_splunkd_pid()
        self.key = ensure_key(self.dir)

    def _read_splunkd_pid(self):
        try:
            return int(Path(self.pid_file).read_text().split()[0]) if self.pid_file else None
        except (OSError, ValueError, IndexError):
            return None

    def splunkd_gone(self):
        """Observed on Splunk 10.6.1.1: `splunk stop` neither signals this launcher nor leaves it a parent to watch (it is reparented to
        PID 1), so liveness is taken from splunkd's own pid file: gone, changed or dead pid means splunkd stopped or restarted."""
        if self.parent_pid and os.getppid() != self.parent_pid:
            return True
        if not self.splunkd_pid:
            return False
        if self._read_splunkd_pid() != self.splunkd_pid:
            return True
        try:
            os.kill(self.splunkd_pid, 0)
        except ProcessLookupError:
            return True
        except PermissionError:
            pass
        return False

    def _env(self):
        env = {k: os.environ[k] for k in PASS_ENV if k in os.environ}
        env.update(PULSEFORGE_GATEWAY_KEY=self.key, PULSEFORGE_REQUIRE_GATEWAY_KEY="1", PYTHONUNBUFFERED="1",
                   NETSPOUT_MAX_STREAM_SECONDS=os.environ.get("NETSPOUT_MAX_STREAM_SECONDS", "3600"), NETSPOUT_MAX_STREAM_EPS=os.environ.get("NETSPOUT_MAX_STREAM_EPS", "200"),
                   NETSPOUT_CONFIG_DIR=str(self.dir / "config"), NETSPOUT_REPLAY_STATE=str(self.dir / "config" / "replay_sessions.json"),
                   NETSPOUT_RUNS_STATE=str(self.dir / "config" / "runs.json"))
        env.update(self._secret_env())
        return env

    def _secret_env(self):
        if self.secrets_source:
            try:
                self._secrets = self.secrets_source() or self._secrets
                self.info["secrets"] = "loaded" if self._secrets else "none saved"
            except Exception as e:  # keep the last good values; the status record says why they may be stale
                self.info["secrets"] = "unavailable (%s)" % type(e).__name__
        out = {}
        if self._secrets.get("hec_token"):
            out["NETSPOUT_HEC_TOKEN"] = self._secrets["hec_token"]
        if self._secrets.get("search_secret"):
            auth = ""
            try:
                auth = json.loads((self.dir / "config" / "connection.json").read_text()).get("auth_method", "")
            except (OSError, ValueError):
                pass
            out["NETSPOUT_SPLUNK_TOKEN" if str(auth).upper().endswith("SPLUNK_TOKEN") else "NETSPOUT_SPLUNK_PASSWORD"] = self._secrets["search_secret"]
        return out

    # child -------------------------------------------------------------------------------------------------------------------
    def _spawn(self):
        if self.sock.exists():
            self.sock.unlink()
        self.proc = subprocess.Popen(self.command, env=self._env(), stdin=subprocess.DEVNULL, preexec_fn=lambda: os.nice(5))  # lower priority: splunkd comes first
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
                if self.splunkd_gone():
                    break  # splunkd stopped or restarted; do not leave an orphan engine
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
    pid_file = Path(os.environ.get("SPLUNK_HOME", "/opt/splunk")) / "var" / "run" / "splunk" / "splunkd.pid"
    uri, key = read_splunk_context()
    sup = Supervisor(ipc.state_dir(), parent_pid=os.getppid(), splunkd_pid_file=pid_file if pid_file.is_file() else None, lock_wait=30,
                     secrets_source=(lambda: fetch_secrets(uri, key)) if uri and key else None)
    for s in (signal.SIGTERM, signal.SIGINT):
        signal.signal(s, lambda *_: sup.stop())
    sup.run()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
