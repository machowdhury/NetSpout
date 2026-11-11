"""
Channel between the Splunk gateway and the Splunk-managed PulseForge engine (Phase 1 prototype). Standard library only.

The managed engine listens on a Unix domain socket inside the app's state directory (mode 0600, owned by the Splunk user), so there
is no TCP port to publish or to firewall. Every request must carry the per-install key kept in the same directory. Both files are
written by the launcher (pulseforge_engine_launcher.py) and read here; the key never goes to the browser or to logs.
"""
import http.client
import json
import os
import socket

KEY_FILE = "engine.key"
INFO_FILE = "engine.json"
SOCKET_FILE = "engine.sock"
KEY_HEADER = "X-PulseForge-Gateway-Key"


def state_dir():
    if os.environ.get("PULSEFORGE_STATE_DIR"):
        return os.environ["PULSEFORGE_STATE_DIR"]
    return os.path.join(os.environ.get("SPLUNK_HOME", "/opt/splunk"), "var", "lib", "netspout")


def read_key(directory=None):
    """Environment first (explicit deployments), then the launcher's key file."""
    if os.environ.get("PULSEFORGE_GATEWAY_KEY"):
        return os.environ["PULSEFORGE_GATEWAY_KEY"]
    try:
        with open(os.path.join(directory or state_dir(), KEY_FILE)) as f:
            return f.read().strip()
    except OSError:
        return ""


def engine_info(directory=None):
    """The launcher's status record, or None when no managed engine has been started on this host."""
    try:
        with open(os.path.join(directory or state_dir(), INFO_FILE)) as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


class _UnixHTTPConnection(http.client.HTTPConnection):
    def __init__(self, path, timeout):
        super().__init__("localhost", timeout=timeout)
        self._path = path

    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)
        self.sock.connect(self._path)


def request(method, path, body=None, headers=None, timeout=120, directory=None):
    """HTTP request to the managed engine over its Unix socket with the key attached; returns (status, bytes)."""
    directory = directory or state_dir()
    hdrs = dict(headers or {})
    key = read_key(directory)
    if key:
        hdrs[KEY_HEADER] = key
    conn = _UnixHTTPConnection(os.path.join(directory, SOCKET_FILE), timeout)
    try:
        conn.request(method, path, body=body, headers=hdrs)
        r = conn.getresponse()
        return r.status, r.read()
    finally:
        conn.close()
