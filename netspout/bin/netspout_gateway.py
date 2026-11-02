"""
NetSpout same-origin API gateway, registered under /services/netspout_gateway.

The React UI inside Splunk Web calls /<locale>/splunkd/__raw/services/netspout_gateway/api/... on the Splunk origin.
This handler forwards those calls server-side to the NetSpout backend, so the browser never needs to reach the backend
port. Splunk authenticates the session (requireAuthentication); this handler additionally requires a Splunk capability
(netspout_admin for POST, netspout_view for GET), checked against splunkd for the session. Standard library only, so it adds no import risk to the app.
"""

import json
import os
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request

BIN_DIR = os.path.dirname(os.path.abspath(__file__))
if BIN_DIR not in sys.path:  # splunkd loads this file by path without adding bin/ to sys.path
    sys.path.insert(0, BIN_DIR)
import pulseforge_ipc as ipc  # noqa: E402  Unix-socket channel to the Splunk-managed engine (same bin directory)

try:
    from splunk.persistconn.application import PersistentServerConnectionApplication
except ImportError:  # unit tests / non-Splunk import
    class PersistentServerConnectionApplication:
        pass

MANAGED_PACKAGE = os.path.exists(os.path.join(BIN_DIR, "MANAGED_ENGINE"))  # written only by the single-package build
ADMIN_CAPABILITY = "netspout_admin"   # POST: run, stop, configure (granted by default to admin, sc_admin and power in authorize.conf)
VIEW_CAPABILITY = "netspout_view"     # GET: read-only use (granted to the `user` role and so inherited by power and admin)
CAPS_TTL = 30
_caps_cache = {}
FORWARD_HEADERS = ("content-type", "accept")
MAX_BODY = 8 * 1024 * 1024
# The management port is this splunkd on loopback; its self-signed certificate cannot be verified by name.
_LOOPBACK_CTX = ssl.create_default_context()
_LOOPBACK_CTX.check_hostname = False
_LOOPBACK_CTX.verify_mode = ssl.CERT_NONE


def backend_url():
    configured = os.environ.get("NETSPOUT_BACKEND_URL", "").strip().rstrip("/")
    if configured:
        return configured
    # Docker Desktop reaches the host through host.docker.internal; a native Splunk uses loopback.
    return "http://host.docker.internal:8081" if os.path.exists("/.dockerenv") else "http://127.0.0.1:8081"


def _reply(status, body):
    return {"status": status, "headers": {"Content-Type": "application/json"},
            "payload": body if isinstance(body, str) else json.dumps(body)}


def _capabilities(session_key):
    """Capabilities of the authenticated Splunk user, asked of splunkd itself; cached briefly (keyed by a hash, never the raw token)."""
    import hashlib
    import time
    k = hashlib.sha256(session_key.encode()).hexdigest()
    hit = _caps_cache.get(k)
    if hit and time.monotonic() - hit[0] < CAPS_TTL:
        return hit[1]
    req = urllib.request.Request(
        "https://127.0.0.1:8089/services/authentication/current-context?output_mode=json",
        headers={"Authorization": "Splunk " + session_key})
    with urllib.request.urlopen(req, timeout=5, context=_LOOPBACK_CTX) as r:
        caps = set(json.loads(r.read().decode())["entry"][0]["content"].get("capabilities", []))
    if len(_caps_cache) > 256:
        _caps_cache.clear()
    _caps_cache[k] = (time.monotonic(), caps)
    return caps


def _authorized(session_key, method):
    """Fail closed: any error, or a missing capability list, is a refusal."""
    try:
        return (ADMIN_CAPABILITY if method == "POST" else VIEW_CAPABILITY) in _capabilities(session_key)
    except Exception:
        return False


class NetSpoutGateway(PersistentServerConnectionApplication):
    def __init__(self, command_line=None, command_arg=None):
        super().__init__()

    def handle(self, in_string):
        try:
            request = json.loads(in_string)
            method = request.get("method", "GET").upper()
            sub = "/" + (request.get("path_info") or "").lstrip("/")
            if method not in ("GET", "POST") or not (sub.startswith("/api/") or sub == "/health") or ".." in sub:
                return _reply(404, {"detail": "Not a gateway route"})
            session_key = request.get("session", {}).get("authtoken", "")
            if not session_key:
                return _reply(401, {"detail": "Splunk session required"})
            if not _authorized(session_key, method):
                return _reply(403, {"detail": "The Splunk capability %s is required%s" % (ADMIN_CAPABILITY if method == "POST" else VIEW_CAPABILITY, " to change PulseForge state" if method == "POST" else " to use PulseForge")})
            query = request.get("query") or []
            pairs = query.items() if isinstance(query, dict) else query
            qs = urllib.parse.urlencode([(k, v) for k, v in pairs])
            if MANAGED_PACKAGE and not ipc.engine_info():  # single-package build: the engine is Splunk-managed, there is no TCP engine to fall back to
                return _reply(503, {"detail": "PulseForge engine is not running yet; it is started by Splunk (check Settings > Data inputs > PulseForge engine, or restart Splunk)"})
            managed = None if os.environ.get("NETSPOUT_BACKEND_URL") and not MANAGED_PACKAGE else ipc.engine_info()  # external-engine installs: an explicit URL wins
            url = backend_url() + sub + ("?" + qs if qs else "")
            raw = request.get("payload") or ""
            if len(raw) > MAX_BODY:
                return _reply(413, {"detail": "Request body too large"})
            hdrs = request.get("headers") or []  # persistconn sends a list of [name, value] pairs
            headers = {k: v for k, v in (hdrs.items() if isinstance(hdrs, dict) else hdrs) if k.lower() in FORWARD_HEADERS}
            if managed:  # Splunk-managed engine: Unix socket plus the per-install key, no TCP port
                try:
                    status, data = ipc.request(method, sub + ("?" + qs if qs else ""), body=raw.encode() if method == "POST" else None, headers=headers, timeout=120)
                    return _reply(status, data.decode())
                except OSError as e:
                    return _reply(502, {"detail": "PulseForge engine is not running (managed engine socket: " + type(e).__name__ + ")"})
            if os.environ.get("PULSEFORGE_GATEWAY_KEY"):  # shared secret the engine checks when it is configured with the same key
                headers["X-PulseForge-Gateway-Key"] = os.environ["PULSEFORGE_GATEWAY_KEY"]
            req = urllib.request.Request(url, data=raw.encode() if method == "POST" else None, headers=headers, method=method)
            try:
                with urllib.request.urlopen(req, timeout=120) as r:
                    return _reply(r.status, r.read().decode())
            except urllib.error.HTTPError as e:
                return _reply(e.code, e.read().decode())
        except Exception as e:  # backend down, DNS, etc.
            return _reply(502, {"detail": "NetSpout gateway error: " + type(e).__name__ + ": " + str(e)[:120]})
