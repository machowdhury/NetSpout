"""
NetSpout same-origin API gateway, registered under /services/netspout_gateway.

The React UI inside Splunk Web calls /<locale>/splunkd/__raw/services/netspout_gateway/api/... on the Splunk origin.
This handler forwards those calls server-side to the NetSpout backend, so the browser never needs to reach the backend
port. Splunk authenticates the session (requireAuthentication); this handler additionally requires a Splunk write role
for anything that is not a GET. Standard library only, so it adds no import risk to the app.
"""

import json
import os
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


def backend_url():
    configured = os.environ.get("NETSPOUT_BACKEND_URL", "").strip().rstrip("/")
    if configured:
        return configured
    # Docker Desktop reaches the host through host.docker.internal; a native Splunk uses loopback.
    return "http://host.docker.internal:8081" if os.path.exists("/.dockerenv") else "http://127.0.0.1:8081"


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
            if method not in ("GET", "POST") or not (sub.startswith("/api/") or sub == "/health") or ".." in sub:
                return _reply(404, {"detail": "Not a gateway route"})
            session_key = request.get("session", {}).get("authtoken", "")
            if not session_key:
                return _reply(401, {"detail": "Splunk session required"})
            if method == "POST":
                try:
                    allowed = bool(_roles(session_key) & WRITE_ROLES)
                except Exception:
                    allowed = False  # fail closed: unknown role is not a write role
                if not allowed:
                    return _reply(403, {"detail": "A Splunk admin or power role is required to change NetSpout state"})
            query = request.get("query") or []
            pairs = query.items() if isinstance(query, dict) else query
            qs = urllib.parse.urlencode([(k, v) for k, v in pairs])
            url = backend_url() + sub + ("?" + qs if qs else "")
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
        except Exception as e:  # backend down, DNS, etc.
            return _reply(502, {"detail": "NetSpout gateway error: " + type(e).__name__ + ": " + str(e)[:120]})
