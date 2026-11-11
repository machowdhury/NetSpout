"""Streaming HEC connection reuse (Phase 17 performance): same outcomes as the per-event path, one connection per stream, never a silent re-send."""
import sys
import threading
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

ROOT = Path(__file__).resolve().parents[1]
for _p in (str(ROOT / "src"), str(ROOT / "backend")):
    if _p not in sys.path:
        sys.path.insert(0, _p)
from netspout_core import telemetry_dispatcher as td  # noqa: E402

EV = {"event": "x", "sourcetype": "t", "index": "i"}


class Hec:
    def __init__(self, status=200, body=b'{"text":"Success","code":0}', drop_after_read=False, close=False):
        self.posts, self.conns = 0, set()
        me = self

        class H(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def do_POST(self):
                self.rfile.read(int(self.headers["Content-Length"]))
                me.posts += 1
                me.conns.add(self.client_address)
                if drop_after_read:
                    self.close_connection = True
                    return
                self.send_response(status)
                self.send_header("Content-Length", str(len(body)))
                if close:
                    self.send_header("Connection", "close")
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *a):
                pass
        self.srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.url = "http://127.0.0.1:%d/services/collector/event" % self.srv.server_port
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()

    def stop(self):
        self.srv.shutdown()


@pytest.fixture
def d():
    return td.TelemetryDispatcher()


def send(d, url, n=1):
    return [d._send_hec(EV, url, "tok", True, False) for _ in range(n)]


def test_stream_reuses_one_connection_and_classifies_like_the_normal_path(d):
    h = Hec()
    try:
        with td.hec_keepalive():
            outs = send(d, h.url, 20)
        assert all(o.state == td.HEC_ACCEPTED and o[0] for o in outs)
        assert h.posts == 20 and len(h.conns) == 1
        send(d, h.url, 3)                                   # outside the scope: the unchanged urllib path, a connection each
        assert len(h.conns) == 4
    finally:
        h.stop()


@pytest.mark.parametrize("status,body,state,cls", [(403, b"{}", td.HEC_FAILED, "auth_rejected"), (400, b"{}", td.HEC_FAILED, "request_rejected"),
                                                   (503, b'{"code":9}', td.HEC_FAILED, "collector_busy"), (500, b"{}", td.HEC_UNKNOWN, "collector_error_uncertain"),
                                                   (200, b'{"code":5}', td.HEC_UNKNOWN, "unexpected_response")])
def test_outcome_classes_match_the_urllib_path(d, status, body, state, cls):
    h = Hec(status, body)
    try:
        with td.hec_keepalive():
            pooled = send(d, h.url)[0]
        plain = send(d, h.url)[0]
        assert (pooled.state, pooled.error_class if hasattr(pooled, "error_class") else pooled[-1]) == (plain.state, plain.error_class if hasattr(plain, "error_class") else plain[-1]) == (state, cls)
    finally:
        h.stop()


def test_idle_connection_is_replaced_not_reused(d, monkeypatch):
    h = Hec()
    try:
        with td.hec_keepalive():
            send(d, h.url)
            monkeypatch.setattr(td, "_KEEPALIVE_IDLE_S", -1)
            send(d, h.url)
        assert len(h.conns) == 2
    finally:
        h.stop()


def test_server_that_closes_each_reply_still_works(d):
    h = Hec(close=True)
    try:
        with td.hec_keepalive():
            assert all(o.state == td.HEC_ACCEPTED for o in send(d, h.url, 5))
        assert h.posts == 5
    finally:
        h.stop()


def test_a_drop_after_the_request_was_sent_is_unknown_and_never_resent(d):
    h = Hec(drop_after_read=True)
    try:
        with td.hec_keepalive():
            o = send(d, h.url)[0]
        assert o.state == td.HEC_UNKNOWN and o[0] is False
        assert h.posts == 1
    finally:
        h.stop()


def test_unreachable_destination_is_failed_unreachable(d):
    with td.hec_keepalive():
        o = send(d, "http://127.0.0.1:9/services/collector/event")[0]
    assert o.state == td.HEC_FAILED and not o[0]


def test_tls_context_is_built_once_per_mode():
    assert td._hec_ssl_context(True) is td._hec_ssl_context(True) and td._hec_ssl_context(False) is td._hec_ssl_context(False)
    assert td._hec_ssl_context(True).verify_mode.name == "CERT_NONE" and td._hec_ssl_context(False).verify_mode.name == "CERT_REQUIRED"


def test_connections_are_not_shared_across_tokens_or_tls_modes(d):
    h = Hec()
    try:
        with td.hec_keepalive():
            d._send_hec(EV, h.url, "tokA", True, False)
            d._send_hec(EV, h.url, "tokA", True, False)
            assert len(h.conns) == 1                       # same destination, token and mode: reused
            d._send_hec(EV, h.url, "tokB", True, False)    # another credential gets its own connection
            d._send_hec(EV, h.url, "tokA", False, True)    # another TLS verification mode gets its own connection
            assert len(h.conns) == 3
    finally:
        h.stop()


def test_connections_are_not_shared_across_destinations(d):
    a, b = Hec(), Hec()
    try:
        with td.hec_keepalive():
            d._send_hec(EV, a.url, "tok", True, False)
            d._send_hec(EV, b.url, "tok", True, False)
            d._send_hec(EV, a.url, "tok", True, False)
        assert (a.posts, b.posts, len(a.conns), len(b.conns)) == (2, 1, 1, 1)
    finally:
        a.stop(); b.stop()


@pytest.mark.parametrize("kw", [dict(drop_after_read=True), dict(body=b'{"text":"x","code":5}'), dict(status=500, body=b"{}")])
def test_ambiguous_delivery_in_a_real_stream_is_never_counted_as_accepted(d, kw):
    """End to end: pooled sends through the stream's own outcome mapping (backend/app/main._hec_item). UNKNOWN stays UNKNOWN: not accepted, not re-sent."""
    from app import main
    from netspout_core.delivery_monitor import ContinuousRun, Item
    h = Hec(**kw)
    try:
        def produce(n):
            def disp():
                o = d._send_hec(EV, h.url, "tok", True, False)
                return {"hec": {"state": o.state, "success": o[0], "message": o[1], "error_class": o.error_class}}
            return [main._hec_item(disp, "t", None) for _ in range(n)]
        r = ContinuousRun("sourcetype", "x:y", "x:y", "dest", "idx", [], produce=produce, max_events=6, eps_limit=1000).start()
        r.wait(30)
        c = r.snapshot()["counters"]
        assert c["accepted"] == 0 and c["unknown"] == c["attempts"] == 6, c
        assert h.posts == 6                       # exactly one POST per event: nothing was silently re-sent
    finally:
        h.stop()
