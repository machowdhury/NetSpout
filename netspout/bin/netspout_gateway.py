"""
NetSpout same-origin API gateway, registered under /services/netspout_gateway.

The React UI inside Splunk Web calls /<locale>/splunkd/__raw/services/netspout_gateway/api/... on the Splunk origin.
This handler forwards those calls server-side to the PulseForge Engine the customer configured (netspout_engine.conf, [engine] url; no default is ever assumed), so the browser never needs to reach the backend
port. Splunk authenticates the session (requireAuthentication); this handler additionally requires a Splunk write role
for anything that is not a GET. Standard library only, so it adds no import risk to the app.
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
import pulseforge_ipc as ipc  # noqa: E402  Unix-socket channel to the Splunk-managed engine

try:
    from splunk.persistconn.application import PersistentServerConnectionApplication
except ImportError:  # unit tests / non-Splunk import
    class PersistentServerConnectionApplication:
        pass

MANAGED_PACKAGE = os.path.exists(os.path.join(BIN_DIR, "MANAGED_ENGINE"))  # written only by the single-package build
ADMIN_CAPABILITY = "netspout_admin"  # POST: run, stop, configure (admin, sc_admin and power in authorize.conf)
VIEW_CAPABILITY = "netspout_view"    # GET: read-only use (the `user` role, inherited by power and admin)
CAPS_TTL = 30
_caps_cache = {}
FORWARD_HEADERS = ("content-type", "accept")
MAX_BODY = 8 * 1024 * 1024
# The management port is this splunkd on loopback; its self-signed certificate cannot be verified by name.
_LOOPBACK_CTX = ssl.create_default_context()
_LOOPBACK_CTX.check_hostname = False
_LOOPBACK_CTX.verify_mode = ssl.CERT_NONE


ENGINE_CONF = "https://127.0.0.1:8089/servicesNS/nobody/netspout/configs/conf-netspout_engine"


def normalize_engine_url(value):
    """The engine's base URL exactly as the customer typed it: http(s)://host[:port], nothing else. Raises ValueError otherwise."""
    value = (value or "").strip()
    if not value:
        return ""
    p = urllib.parse.urlparse(value)
    if p.scheme not in ("http", "https") or not p.hostname or p.username or p.password or p.query or p.fragment or p.path not in ("", "/"):
        raise ValueError("Engine URL must look like http://host:8081 (no path, query or credentials)")
    return "%s://%s" % (p.scheme, p.netloc)


def _splunk(url, session_key, data=None):
    body = urllib.parse.urlencode(data).encode() if data is not None else None
    req = urllib.request.Request(url + ("&" if "?" in url else "?") + "output_mode=json", data=body, headers={"Authorization": "Splunk " + session_key})
    with urllib.request.urlopen(req, timeout=5, context=_LOOPBACK_CTX) as r:
        return json.loads(r.read().decode() or "{}")


def configured_engine(session_key):
    """The URL the customer saved in the app's own configuration (netspout_engine.conf, stanza [engine]); "" when none. There is NO default engine: nothing is guessed.
    Read on every request (about 9 ms): a change made in Connections or directly in the configuration applies to the very next request and never routes to an old engine."""
    try:
        url = _splunk(ENGINE_CONF + "/engine", session_key)["entry"][0]["content"].get("url", "") or ""
    except urllib.error.HTTPError as e:
        if e.code != 404:
            raise
        url = ""
    return url.strip().rstrip("/")


def save_engine(session_key, url):
    try:
        _splunk(ENGINE_CONF + "/engine", session_key, {"url": url})
    except urllib.error.HTTPError as e:
        if e.code != 404:
            raise
        _splunk(ENGINE_CONF, session_key, {"name": "engine", "url": url})


NOT_CONFIGURED = {"detail": "Engine not configured.", "code": "ENGINE_NOT_CONFIGURED"}
NOT_CONNECTED = {"detail": "Engine not connected.", "code": "ENGINE_NOT_CONNECTED"}


def engine_status(session_key):
    if MANAGED_PACKAGE:
        info = ipc.engine_info() or {}
        try:  # the status file can be stale (a killed launcher cannot update it), so ask the engine itself
            status, _ = ipc.request("GET", "/api/health", timeout=3)
            alive = status == 200
        except Exception:
            alive = False
        state = info.get("state", "not started") if alive else ("stopped (launcher not running; use Restart engine or restart Splunk)" if info else "not started")
        return {"configured": True, "managed": True, "connected": alive, "url": "", "state": state, "restarts": info.get("restarts", 0), "last_error": info.get("last_error"),
                "message": "PulseForge engine is managed by Splunk (%s)." % state}
    url = configured_engine(session_key)
    if not url:
        return {"configured": False, "connected": False, "url": "", "message": "Engine not configured."}
    try:
        with urllib.request.urlopen(url + "/api/health", timeout=4) as r:
            health = json.loads(r.read().decode() or "{}")
        return {"configured": True, "connected": True, "url": url, "message": "Engine connected.", "version": health.get("version")}
    except Exception:
        return {"configured": True, "connected": False, "url": url, "message": "Engine not connected."}


def _reply(status, body):
    return {"status": status, "headers": {"Content-Type": "application/json"},
            "payload": body if isinstance(body, str) else json.dumps(body)}


def _capabilities(session_key):
    """Capabilities of the authenticated Splunk user, asked of splunkd; cached briefly under a hash, never the raw token."""
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
    """Fail closed: any error or a missing capability is a refusal."""
    try:
        return (ADMIN_CAPABILITY if method == "POST" else VIEW_CAPABILITY) in _capabilities(session_key)
    except Exception:
        return False


LAUNCHER_INPUT = "https://127.0.0.1:8089/servicesNS/nobody/netspout/data/inputs/pulseforge_engine_launcher/default/"


def restart_managed_engine(session_key):
    """Disable then enable the launcher input: splunkd stops the launcher (and with it the engine) and starts a fresh one. Needs the caller to be allowed to edit inputs."""
    if not MANAGED_PACKAGE:
        return 409, {"detail": "This install has no Splunk-managed engine"}
    try:
        _splunk(LAUNCHER_INPUT + "disable", session_key, {})
        import time
        time.sleep(3)
        _splunk(LAUNCHER_INPUT + "enable", session_key, {})
    except urllib.error.HTTPError as e:
        return 403, {"detail": "Splunk refused to restart the engine input (HTTP %s); an administrator can enable it in Settings > Data inputs > PulseForge engine" % e.code}
    return 202, {"detail": "Engine restart requested; check Connections in about 30 seconds"}


PASSWORDS = "https://127.0.0.1:8089/servicesNS/nobody/netspout/storage/passwords"


def store_secret(session_key, name, value):
    """Create or replace one secret in Splunk's encrypted storage/passwords (realm netspout). The value is never logged."""
    ident = urllib.parse.quote("netspout:%s:" % name, safe="")
    for url, data in ((PASSWORDS + "/" + ident, {"password": value}), (PASSWORDS, {"name": name, "realm": "netspout", "password": value})):
        body = urllib.parse.urlencode(data).encode()
        req = urllib.request.Request(url + "?output_mode=json", data=body, headers={"Authorization": "Splunk " + session_key})
        try:
            urllib.request.urlopen(req, timeout=10, context=_LOOPBACK_CTX).read()
            return
        except urllib.error.HTTPError as e:
            if e.code != 404:
                raise


def _persist_secrets(session_key, raw):
    """Save a submitted HEC token / search secret so they survive an engine or Splunk restart. Returns an error string or None."""
    try:
        payload = json.loads(raw or "{}")
    except ValueError:
        return None  # the engine rejects malformed bodies itself
    try:
        for field in ("hec_token", "search_secret"):
            if isinstance(payload, dict) and payload.get(field):
                store_secret(session_key, field, payload[field])
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            return "Saving credentials needs the Splunk capability edit_storage_passwords (the admin role); nothing was saved"
        return "Splunk could not store the credential (HTTP %s); nothing was saved" % e.code
    except Exception as e:
        return "Splunk could not store the credential (%s); nothing was saved" % type(e).__name__
    return None


class NetSpoutGateway(PersistentServerConnectionApplication):
    def __init__(self, command_line=None, command_arg=None):
        super().__init__()

    def handle(self, in_string):
        try:
            request = json.loads(in_string)
            method = request.get("method", "GET").upper()
            sub = "/" + (request.get("path_info") or "").lstrip("/")
            if method not in ("GET", "POST") or not (sub.startswith("/api/") or sub in ("/health", "/engine", "/engine/restart")) or ".." in sub:
                return _reply(404, {"detail": "Not a gateway route"})
            session_key = request.get("session", {}).get("authtoken", "")
            if not session_key:
                return _reply(401, {"detail": "Splunk session required"})
            if sub == "/engine" and method == "GET":
                return _reply(200, engine_status(session_key))
            if not _authorized(session_key, method):
                return _reply(403, {"detail": "The Splunk capability %s is required%s (admin or power role required to change NetSpout state)" % (
                    ADMIN_CAPABILITY if method == "POST" else VIEW_CAPABILITY, " to change PulseForge state" if method == "POST" else " to use PulseForge")})
            if sub == "/engine/restart":
                return _reply(*restart_managed_engine(session_key))
            if sub == "/engine" and MANAGED_PACKAGE:
                return _reply(409, {"detail": "The engine is managed by Splunk in this package; there is no engine URL to set"})
            if sub == "/engine":
                try:
                    url = normalize_engine_url(json.loads(request.get("payload") or "{}").get("url", ""))
                except (ValueError, AttributeError) as exc:
                    return _reply(422, {"detail": str(exc)})
                save_engine(session_key, url)
                return _reply(200, engine_status(session_key))
            if MANAGED_PACKAGE:
                if not ipc.engine_info():
                    return _reply(503, {"detail": "PulseForge engine is not running yet; Splunk starts it (Settings > Data inputs > PulseForge engine, or restart Splunk)", "code": "ENGINE_NOT_STARTED"})
                engine = ""
            else:
                engine = configured_engine(session_key)
                if not engine:
                    return _reply(503, NOT_CONFIGURED)
            query = request.get("query") or []
            pairs = query.items() if isinstance(query, dict) else query
            qs = urllib.parse.urlencode([(k, v) for k, v in pairs])
            url = engine + sub + ("?" + qs if qs else "")
            raw = request.get("payload") or ""
            if len(raw) > MAX_BODY:
                return _reply(413, {"detail": "Request body too large"})
            hdrs = request.get("headers") or []  # persistconn sends a list of [name, value] pairs
            headers = {k: v for k, v in (hdrs.items() if isinstance(hdrs, dict) else hdrs) if k.lower() in FORWARD_HEADERS}
            if MANAGED_PACKAGE:  # Unix socket plus the per-install key: no TCP port
                if method == "POST" and sub == "/api/setup":
                    err = _persist_secrets(session_key, raw)
                    if err:
                        return _reply(403, {"detail": err})
                try:
                    status, data = ipc.request(method, sub + ("?" + qs if qs else ""), body=raw.encode() if method == "POST" else None, headers=headers, timeout=120)
                    return _reply(status, data.decode())
                except OSError as e:
                    return _reply(502, {"detail": "PulseForge engine is not running (managed engine socket: " + type(e).__name__ + ")", "code": "ENGINE_NOT_CONNECTED"})
            if os.environ.get("PULSEFORGE_GATEWAY_KEY"):  # external engine configured with the same shared secret
                headers["X-PulseForge-Gateway-Key"] = os.environ["PULSEFORGE_GATEWAY_KEY"]
            req = urllib.request.Request(url, data=raw.encode() if method == "POST" else None, headers=headers, method=method)
            try:
                with urllib.request.urlopen(req, timeout=120) as r:
                    return _reply(r.status, r.read().decode())
            except urllib.error.HTTPError as e:
                return _reply(e.code, e.read().decode())
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            return _reply(502, NOT_CONNECTED)
        except Exception as e:
            return _reply(502, {"detail": "NetSpout gateway error: " + type(e).__name__ + ": " + str(e)[:120]})
