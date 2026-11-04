"""
NetSpout same-origin API gateway, registered under /services/netspout_gateway.

The React UI inside Splunk Web calls /<locale>/splunkd/__raw/services/netspout_gateway/api/... on the Splunk origin.
This handler forwards those calls server-side to the PulseForge Engine the customer configured (netspout_engine.conf, [engine] url; no default is ever assumed), so the browser never needs to reach the backend
port. Splunk authenticates the session (requireAuthentication); this handler additionally requires a Splunk write role
for anything that is not a GET. Standard library only, so it adds no import risk to the app.
"""

import json
import ssl
import urllib.error
import urllib.parse
import urllib.request

try:
    from splunk.persistconn.application import PersistentServerConnectionApplication
except ImportError:  # unit tests / non-Splunk import
    class PersistentServerConnectionApplication:
        pass

WRITE_ROLES = {"admin", "sc_admin", "power"}
FORWARD_HEADERS = ("content-type", "accept")
MAX_BODY = 8 * 1024 * 1024
# The management port is this splunkd on loopback; its self-signed certificate cannot be verified by name.
_LOOPBACK_CTX = ssl.create_default_context()
_LOOPBACK_CTX.check_hostname = False
_LOOPBACK_CTX.verify_mode = ssl.CERT_NONE


ENGINE_CONF = "https://127.0.0.1:8089/servicesNS/nobody/netspout/configs/conf-netspout_engine"
_CACHE = {"url": None, "at": 0.0}
CACHE_SECONDS = 5


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
    """The URL the customer saved in the app's own configuration (netspout_engine.conf, stanza [engine]); "" when none. There is NO default engine: nothing is guessed."""
    import time
    if _CACHE["url"] is not None and time.time() - _CACHE["at"] < CACHE_SECONDS:
        return _CACHE["url"]
    try:
        url = _splunk(ENGINE_CONF + "/engine", session_key)["entry"][0]["content"].get("url", "") or ""
    except urllib.error.HTTPError as e:
        if e.code != 404:
            raise
        url = ""
    _CACHE.update(url=url.strip().rstrip("/"), at=time.time())
    return _CACHE["url"]


def save_engine(session_key, url):
    try:
        _splunk(ENGINE_CONF + "/engine", session_key, {"url": url})
    except urllib.error.HTTPError as e:
        if e.code != 404:
            raise
        _splunk(ENGINE_CONF, session_key, {"name": "engine", "url": url})
    _CACHE.update(url=url, at=0.0)


NOT_CONFIGURED = {"detail": "Engine not configured.", "code": "ENGINE_NOT_CONFIGURED"}
NOT_CONNECTED = {"detail": "Engine not connected.", "code": "ENGINE_NOT_CONNECTED"}


def engine_status(session_key):
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


def _roles(session_key):
    req = urllib.request.Request(
        "https://127.0.0.1:8089/services/authentication/current-context?output_mode=json",
        headers={"Authorization": "Splunk " + session_key})
    with urllib.request.urlopen(req, timeout=5, context=_LOOPBACK_CTX) as r:
        return set(json.loads(r.read().decode())["entry"][0]["content"].get("roles", []))


class NetSpoutGateway(PersistentServerConnectionApplication):
    def __init__(self, command_line=None, command_arg=None):
        super().__init__()

    def handle(self, in_string):
        try:
            request = json.loads(in_string)
            method = request.get("method", "GET").upper()
            sub = "/" + (request.get("path_info") or "").lstrip("/")
            if method not in ("GET", "POST") or not (sub.startswith("/api/") or sub in ("/health", "/engine")) or ".." in sub:
                return _reply(404, {"detail": "Not a gateway route"})
            session_key = request.get("session", {}).get("authtoken", "")
            if not session_key:
                return _reply(401, {"detail": "Splunk session required"})
            if sub == "/engine" and method == "GET":
                return _reply(200, engine_status(session_key))
            if method == "POST":
                try:
                    allowed = bool(_roles(session_key) & WRITE_ROLES)
                except Exception:
                    allowed = False  # fail closed: unknown role is not a write role
                if not allowed:
                    return _reply(403, {"detail": "A Splunk admin or power role is required to change NetSpout state"})
            if sub == "/engine":
                try:
                    url = normalize_engine_url(json.loads(request.get("payload") or "{}").get("url", ""))
                except (ValueError, AttributeError) as exc:
                    return _reply(422, {"detail": str(exc)})
                save_engine(session_key, url)
                return _reply(200, engine_status(session_key))
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
