# =========================================================================
# AUTO-GENERATED PACKAGED COPY — DO NOT EDIT DIRECTLY!
# Authoritative Source of Truth: src/netspout_core/hec_connection_test.py
# Re-generate using: python3 scripts/sync_core.py
# =========================================================================
"""Connection test for the SAVED Connection Center destination (Splunk Enterprise or Splunk Cloud HEC).

Statuses are kept apart and never merged:
  connection      DNS, TCP and TLS (certificate trust) to the HEC endpoint, plus the HEC health endpoint
  authentication  the HEC token was accepted or refused
  acceptance      HEC acknowledged one clearly marked synthetic test event (HTTP 200, body code 0). This is NOT proof of indexing
  indexing        an independent authenticated search found that exact test event (only when search is configured)
Overall FULLY_VERIFIED requires all four. Anything less says exactly what was and was not shown.

The test event goes only to an index the caller names AND that is on the Connection Center allowlist; nothing is sent otherwise. No caller-supplied transport is accepted:
the function takes the saved configuration. Credentials never appear in the result (they are scrubbed from every message).
"""
import json
import socket
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timezone
from typing import Callable, Dict, List, Optional

CONNECT_TIMEOUT = 5.0
HTTP_TIMEOUT = 10.0
SEARCH_POLLS, SEARCH_INTERVAL = 6, 3.0
TEST_SOURCETYPE = "netspout:connection_test"
HEC_CODES = {0: "Success", 1: "Token disabled", 2: "Token required", 3: "Invalid authorization", 4: "Invalid token", 5: "No data", 6: "Invalid data format", 7: "Incorrect index",
             8: "Internal server error", 9: "Server is busy", 10: "Data channel is missing", 11: "Invalid data channel", 12: "Event field is required", 13: "Event field cannot be blank",
             14: "ACK is disabled", 15: "Error in handling indexed fields", 16: "Query string authorization is not enabled"}


def _scrub(text, secrets):
    t = str(text or "")
    for s in secrets:
        if s:
            t = t.replace(s, "***")
    return " ".join(t.split())[:300]


def hec_base(hec_url: str) -> str:
    """https://host:port from any saved HEC URL (…/services/collector or …/services/collector/event)."""
    u = urllib.parse.urlparse(hec_url)
    return "%s://%s" % (u.scheme, u.netloc)


def _step(steps, sid, status, detail, started):
    steps.append({"id": sid, "status": status, "detail": detail, "ms": int((time.monotonic() - started) * 1000)})
    return status


def _tls_context(allow_insecure: bool):
    ctx = ssl.create_default_context()
    if allow_insecure:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    return ctx


def classify_exception(exc, host) -> (str, str):
    """-> (category, plain-language message)."""
    if isinstance(exc, ssl.SSLCertVerificationError):
        reason = getattr(exc, "verify_message", "") or str(exc)
        return "TLS_CERTIFICATE", "TLS certificate is not trusted (%s). Install the CA, use a certificate the host name matches, or (lab loopback only) allow insecure TLS." % reason
    if isinstance(exc, ssl.SSLError):
        return "TLS", "TLS handshake failed (%s)" % getattr(exc, "reason", None) or "TLS handshake failed"
    if isinstance(exc, socket.gaierror):
        return "DNS", "DNS lookup for %s failed (%s)" % (host, exc.strerror or exc)
    if isinstance(exc, (socket.timeout, TimeoutError)):
        return "TIMEOUT", "Timed out connecting to or reading from %s" % host
    if isinstance(exc, ConnectionRefusedError):
        return "REFUSED", "Connection to %s was refused (nothing is listening on that port, or a firewall rejected it)" % host
    if isinstance(exc, urllib.error.URLError) and getattr(exc, "reason", None) is not None and exc.reason is not exc:
        return classify_exception(exc.reason, host)
    return "NETWORK", "Network error (%s)" % type(exc).__name__


def interpret_hec(http_status: Optional[int], body: str) -> (str, str):
    """-> (outcome, message): ACCEPTED | AUTH_FAILED | INDEX_REFUSED | REJECTED | UNKNOWN."""
    code, text = None, None
    try:
        parsed = json.loads(body)
        code, text = parsed.get("code"), parsed.get("text")
    except (ValueError, AttributeError):
        pass
    if http_status == 200 and code == 0:
        return "ACCEPTED", "HEC acknowledged the event (HTTP 200, code 0)"
    if http_status == 200 and code is None:
        return "UNKNOWN", "HTTP 200 but the body was not a HEC acknowledgement; acceptance is not proven"
    if http_status in (401, 403) or code in (2, 3, 4):
        return "AUTH_FAILED", "HEC token authentication failed (HTTP %s, %s). Check the token value, that it is enabled, and that it belongs to this HEC endpoint." % (http_status, HEC_CODES.get(code, text or "unauthorized"))
    if code == 1:
        return "AUTH_FAILED", "HEC token is disabled (code 1)"
    if code == 7:
        return "INDEX_REFUSED", "HEC refused the index (code 7, incorrect index): the index does not exist or this token is not allowed to write to it"
    if http_status == 503 or code == 9:
        return "REJECTED", "HEC is busy or unavailable (HTTP %s, %s)" % (http_status, HEC_CODES.get(code, text or "service unavailable"))
    return "REJECTED", "HEC rejected the event (HTTP %s, code %s: %s)" % (http_status, code, HEC_CODES.get(code, text or "unknown"))


def run_test(config: Dict, hec_token: str, test_index: str, allowed_indexes: List[str], search: Optional[Callable[[str], tuple]] = None, search_secret: Optional[str] = None,
             *, connect_timeout: float = CONNECT_TIMEOUT, http_timeout: float = HTTP_TIMEOUT, polls: int = SEARCH_POLLS, interval: float = SEARCH_INTERVAL) -> Dict:
    secrets = [hec_token, search_secret]
    steps: List[Dict] = []
    test_id = uuid.uuid4().hex
    out = {"test_id": test_id, "tested_at": datetime.now(timezone.utc).isoformat(), "test_index": test_index, "statuses": {"connection": "NOT_RUN", "authentication": "NOT_RUN", "acceptance": "NOT_RUN", "indexing": "NOT_RUN"},
           "steps": steps, "overall": "FAILED", "error": None}

    def fail(category, message):
        out["error"] = {"category": category, "message": _scrub(message, secrets)}
        return out

    t = time.monotonic()
    if test_index not in allowed_indexes:
        _step(steps, "allowlist", "FAIL", "Index %r is not on the Connection Center allowlist; no event was sent." % test_index, t)
        out["statuses"]["connection"] = "NOT_RUN"
        return fail("INDEX_NOT_ALLOWED", "Index is not authorized by Connection Center; nothing was sent")
    _step(steps, "allowlist", "PASS", "Test index is on the allowlist", t)
    url = config.get("hec_url") or ""
    u = urllib.parse.urlparse(url)
    t = time.monotonic()
    if u.scheme not in ("http", "https") or not u.hostname:
        _step(steps, "config", "FAIL", "HEC URL is not a valid http(s) URL", t)
        return fail("CONFIG", "The saved HEC URL is not valid")
    if u.scheme == "http" and config.get("deployment_mode") != "DOCKER_LAB":
        _step(steps, "config", "FAIL", "Plain http is allowed only for the loopback lab destination", t)
        return fail("CONFIG", "HEC over plain http is not allowed outside the lab destination")
    host, port = u.hostname, u.port or (443 if u.scheme == "https" else 80)
    insecure = bool(config.get("allow_insecure_tls"))
    _step(steps, "config", "PASS", "%s://%s:%s (%s)" % (u.scheme, host, port, "Splunk Cloud-style host" if ".splunkcloud." in host else "Splunk Enterprise or custom host"), t)
    # DNS, TCP, TLS (one retry on a transient connect failure; never a re-send of an event)
    last = None
    for attempt in (1, 2):
        t = time.monotonic()
        try:
            addrs = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
            _step(steps, "dns", "PASS", "%s resolves to %s" % (host, addrs[0][4][0]), t)
            t = time.monotonic()
            raw = socket.create_connection((host, port), timeout=connect_timeout)
            _step(steps, "tcp", "PASS", "TCP connection established", t)
            if u.scheme == "https":
                t = time.monotonic()
                with _tls_context(insecure).wrap_socket(raw, server_hostname=host) as tls:
                    detail = "%s, cipher %s, certificate %s" % (tls.version(), tls.cipher()[0], "NOT verified (lab loopback exception)" if insecure else "verified against the system trust store and host name")
                    _step(steps, "tls", "WARN" if insecure else "PASS", detail, t)
            else:
                raw.close()
            last = None
            break
        except Exception as exc:
            last = exc
            category, message = classify_exception(exc, host)
            if category in ("TLS_CERTIFICATE", "DNS", "REFUSED") or attempt == 2:
                _step(steps, {"DNS": "dns", "REFUSED": "tcp", "TIMEOUT": "tcp", "TLS_CERTIFICATE": "tls", "TLS": "tls"}.get(category, "tcp"), "FAIL", _scrub(message, secrets), t)
                out["statuses"]["connection"] = "FAILED"
                return fail(category, message)
            time.sleep(0.5)
    # health endpoint (no token needed)
    t = time.monotonic()
    ctx = _tls_context(insecure) if u.scheme == "https" else None
    health_url = hec_base(url) + "/services/collector/health"
    try:
        with urllib.request.urlopen(urllib.request.Request(health_url), timeout=http_timeout, context=ctx) as r:
            _step(steps, "health", "PASS", "HEC health endpoint answered HTTP %s" % r.status, t)
    except urllib.error.HTTPError as exc:
        _step(steps, "health", "WARN", "HEC health endpoint answered HTTP %s (HEC may be disabled, or the endpoint is not exposed)" % exc.code, t)
    except Exception as exc:
        category, message = classify_exception(exc, host)
        _step(steps, "health", "FAIL", _scrub(message, secrets), t)
        out["statuses"]["connection"] = "FAILED"
        return fail(category, message)
    out["statuses"]["connection"] = "REACHABLE"
    # authentication and acceptance: one synthetic, clearly marked event
    payload = {"time": round(time.time(), 3), "host": "pulseforge-connection-test", "source": "pulseforge:connection-test", "sourcetype": TEST_SOURCETYPE, "index": test_index,
               "event": "PulseForge connection test %s (synthetic; safe to delete)" % test_id, "fields": {"pulseforge_connection_test_id": test_id}}
    t = time.monotonic()
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={"Authorization": "Splunk " + hec_token, "Content-Type": "application/json"}, method="POST")
    status, body = None, ""
    try:
        with urllib.request.urlopen(req, timeout=http_timeout, context=ctx) as r:
            status, body = r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        status, body = exc.code, exc.read().decode("utf-8", "replace")
    except Exception as exc:
        category, message = classify_exception(exc, host)
        _step(steps, "hec_event", "UNKNOWN", "The send did not complete (%s); it may or may not have been delivered and is not retried" % _scrub(message, secrets), t)
        out["statuses"]["acceptance"] = "UNKNOWN"
        out["statuses"]["authentication"] = "UNKNOWN"
        return fail(category, message)
    outcome, message = interpret_hec(status, body)
    out["hec_response"] = {"http_status": status, "body": _scrub(body, secrets)}
    if outcome == "ACCEPTED":
        out["statuses"]["authentication"] = "AUTHENTICATED"
        out["statuses"]["acceptance"] = "ACCEPTED"
        _step(steps, "hec_event", "PASS", message, t)
    elif outcome == "UNKNOWN":
        out["statuses"]["acceptance"] = "UNKNOWN"
        _step(steps, "hec_event", "UNKNOWN", message, t)
        return fail("HEC_UNKNOWN", message)
    else:
        out["statuses"]["authentication"] = "REFUSED" if outcome == "AUTH_FAILED" else "AUTHENTICATED"
        out["statuses"]["acceptance"] = "REJECTED"
        _step(steps, "hec_event", "FAIL", message, t)
        out["overall"] = "FAILED"
        return fail(outcome, message)
    # independent verification
    if search is None:
        out["statuses"]["indexing"] = "NOT_CONFIGURED"
        _step(steps, "indexing", "SKIP", "No search endpoint and credentials are configured, so indexing was not checked", time.monotonic())
        out["overall"] = "ACCEPTED_NOT_VERIFIED"
        return out
    query = 'search index="%s" pulseforge_connection_test_id="%s" earliest=-15m latest=+5m | stats count' % (test_index, test_id)
    t = time.monotonic()
    found, error = 0, None
    for i in range(polls):
        try:
            rows, error = search(query)
        except Exception as exc:
            rows, error = [], "%s" % type(exc).__name__
        if error:
            break
        found = int(float((rows[0].get("count") if rows else 0) or 0))
        if found:
            break
        time.sleep(interval)
    if error:
        out["statuses"]["indexing"] = "SEARCH_FAILED"
        _step(steps, "indexing", "FAIL", "Search verification failed: " + _scrub(error, secrets), t)
        out["overall"] = "ACCEPTED_NOT_VERIFIED"
        out["error"] = {"category": "SEARCH", "message": _scrub(error, secrets)}
        return out
    if found:
        out["statuses"]["indexing"] = "VERIFIED"
        _step(steps, "indexing", "PASS", "An independent search found the test event in index %s" % test_index, t)
        out["overall"] = "FULLY_VERIFIED"
    else:
        out["statuses"]["indexing"] = "NOT_FOUND"
        _step(steps, "indexing", "WARN", "HEC acknowledged the event but the search did not find it within %d s (indexing delay, a different index routing, or search permissions)" % int(polls * interval), t)
        out["overall"] = "ACCEPTED_NOT_VERIFIED"
    return out
