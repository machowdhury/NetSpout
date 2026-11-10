"""No parameterless GET route returns a configured HEC token or search password (sentinels planted in the environment and the transport)."""
import socket
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (str(ROOT / "src"), str(ROOT / "backend")):
    if _p not in sys.path:
        sys.path.insert(0, _p)
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from app import main

TOKEN, PASSWORD = "SENTINEL-HEC-TOKEN-7f3a91", "SENTINEL-SPLUNK-PW-2c8d44"


PROTECTED_PORTS = {8000, 8081, 8088, 8089, 8888, 8889}     # the protected local stack's published ports (and their alternates probed by the routes)


def _no_protected_network(monkeypatch):
    """Refuse every connection that is off this host or to a protected port, at the socket, so redirects, hostnames and environment-derived endpoints are covered alike.
    Returns the list of refused attempts."""
    blocked = []

    def _guard(addr):
        if not isinstance(addr, tuple):
            return                                   # unix-domain sockets are local by construction
        host, port = addr[0], addr[1]
        if host not in ("127.0.0.1", "::1", "localhost") or port in PROTECTED_PORTS:
            blocked.append((host, port))
            raise ConnectionRefusedError("blocked by test: %s:%s" % (host, port))

    real_connect, real_connect_ex, real_cc = socket.socket.connect, socket.socket.connect_ex, socket.create_connection
    monkeypatch.setattr(socket.socket, "connect", lambda self, addr, *a: (_guard(addr), real_connect(self, addr, *a))[1])
    monkeypatch.setattr(socket.socket, "connect_ex", lambda self, addr, *a: (_guard(addr), real_connect_ex(self, addr, *a))[1])
    monkeypatch.setattr(socket, "create_connection", lambda addr, *a, **k: (_guard(addr), real_cc(addr, *a, **k))[1])
    monkeypatch.setenv("NETSPOUT_HEC_URL", "https://127.0.0.1:1/services/collector/event")
    monkeypatch.setenv("NETSPOUT_REST_SEARCH_URL", "https://127.0.0.1:1/services/search/jobs/export")
    return blocked


def test_the_guard_refuses_protected_ports_redirects_and_remote_hosts(monkeypatch):
    import threading
    import urllib.request
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    class Redirect(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(302)
            self.send_header("Location", "http://localhost:8089/services/server/info")
            self.end_headers()

        def log_message(self, *a):
            pass
    srv = ThreadingHTTPServer(("127.0.0.1", 0), Redirect)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        blocked = _no_protected_network(monkeypatch)
        for url in ("http://127.0.0.1:%d/" % srv.server_port,       # allowed hop, then a redirect to the protected REST port
                    "https://127.0.0.1:8088/services/collector",     # direct
                    "http://example.com/"):                          # off host
            try:
                urllib.request.urlopen(url, timeout=3)
            except Exception:
                pass
        ports = {p for _h, p in blocked}
        assert {8089, 8088, 80} <= ports, blocked
        import os
        assert ":8088" not in os.environ["NETSPOUT_HEC_URL"] and ":8089" not in os.environ["NETSPOUT_REST_SEARCH_URL"]
    finally:
        srv.shutdown()


def test_get_routes_never_return_configured_secrets(monkeypatch):
    monkeypatch.setenv("NETSPOUT_HEC_TOKEN", TOKEN)
    monkeypatch.setenv("NETSPOUT_SPLUNK_PASSWORD", PASSWORD)
    gt = getattr(main.current_topology, "global_transport", None) if main.current_topology else None
    if gt is not None:
        monkeypatch.setattr(gt, "hec_token", TOKEN, raising=False)
        monkeypatch.setattr(gt, "hec_url", "https://example.invalid:8088/services/collector", raising=False)
    blocked = _no_protected_network(monkeypatch)
    # The gNMI preflight route waits ~70 s for a Splunk HEC listener that this test does not have; readiness is not what is under test, so answer "not ready" at once.
    from app.gnmi import splunk_e2e
    monkeypatch.setattr(splunk_e2e.GnmiSplunkBridge, "wait_for_hec_ready",
                        lambda self: {"ready": False, "attempts": 0, "elapsed_ms": 0.0, "error": "not probed in this test"})
    c = TestClient(main.app, raise_server_exceptions=False)
    paths = sorted({r.path for r in main.app.routes if isinstance(r, APIRoute) and "GET" in r.methods and "{" not in r.path})
    assert len(paths) > 40
    leaks = []
    for p in paths:
        body = c.get(p).text          # one request per route (it used to be two, which doubled the run time)
        if TOKEN in body or PASSWORD in body:
            leaks.append(p)
    assert leaks == []
