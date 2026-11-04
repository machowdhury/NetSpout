#!/usr/bin/env python3
"""Recording tap and fault injector in front of the isolated lab's real HEC (Phase 9 acceptance only).

  python scripts/phase9_hec_proxy.py [--port 19990] [--upstream-port 19088]

NetSpout's destination points at this tap; everything is forwarded to the REAL lab Splunk HEC unchanged (mode pass), so events and metrics really are indexed.
The tap records what NetSpout actually sent (sourcetype, index, host, source, time, metric names and dimension names; never values of secrets and never the Authorization
header) so the exact outgoing payload is independent evidence. Fault modes exist only for the failure-path tests:

  POST /_mode?m=pass                     forward unchanged
  POST /_mode?m=drop                     answer HEC's success reply for event/metric posts but forward nothing (accepted but never indexed)
  POST /_mode?m=reindex_event&to=main    forward, but rewrite the index of log events (events land in the wrong index)
  POST /_mode?m=reindex_metric&to=NAME   forward, but rewrite the index of metric events (metrics land in the wrong metric index)
  POST /_mode?m=reject                   answer HEC's "incorrect index" error
  GET  /_payloads  /  POST /_reset       read / clear the recorded summaries

Binds to 127.0.0.1 only and refuses any upstream other than the two isolated labs: the TA-validation lab (127.0.0.1:19088) and the release-candidate install lab (127.0.0.1:39088, or splunk:8088 when run inside that lab's engine container).
"""
import argparse
import http.client
import json
import ssl
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

STATE = {"mode": "pass", "to": "main", "log": [], "lock": threading.Lock()}
UPSTREAM = ("127.0.0.1", 19088)
CTX = ssl._create_unverified_context()      # the lab HEC has a self-signed certificate on loopback
SUCCESS = b'{"text":"Success","code":0}'


def split_json(body: bytes):
    dec, text, i, out = json.JSONDecoder(), body.decode("utf-8", "replace"), 0, []
    while i < len(text):
        while i < len(text) and text[i].isspace():
            i += 1
        if i >= len(text):
            break
        obj, i = dec.raw_decode(text, i)
        out.append(obj)
    return out


def summarize(o, mode, status):
    f = o.get("fields") or {}
    is_metric = o.get("event") == "metric"
    return {"t": time.time(), "mode": mode, "kind": "metric" if is_metric else "event", "sourcetype": o.get("sourcetype"), "index": o.get("index"), "host": o.get("host"), "source": o.get("source"),
            "time": o.get("time"), "metric_names": sorted(k[12:] for k in f if k.startswith("metric_name:")) if is_metric else None,
            "dimension_names": sorted(k for k in f if not k.startswith("metric_name:") and k != "_value") if is_metric else None,
            "field_names": sorted(f) if not is_metric else None, "upstream_status": status,
            "run_id": f.get("netspout_run_id"), "scenario_id": f.get("netspout_scenario_id"), "phase": f.get("netspout_phase"),
            "metric_values": {k[12:]: v for k, v in f.items() if k.startswith("metric_name:")} if is_metric else None,
            "run_dims": {k: v for k, v in f.items() if is_metric and not k.startswith(("metric_name:", "netspout_")) and k != "_value"} if is_metric else None}


class H(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype="application/json"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        u = urlparse(self.path)
        if u.path == "/_payloads":
            with STATE["lock"]:
                return self._send(200, json.dumps({"mode": STATE["mode"], "payloads": STATE["log"]}).encode())
        self._forward(b"")

    def do_POST(self):
        u = urlparse(self.path)
        n = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(n) if n else b""
        if u.path == "/_mode":
            q = parse_qs(u.query)
            STATE["mode"], STATE["to"] = q.get("m", ["pass"])[0], q.get("to", ["main"])[0]
            return self._send(200, json.dumps({"mode": STATE["mode"], "to": STATE["to"]}).encode())
        if u.path == "/_reset":
            with STATE["lock"]:
                STATE["log"].clear()
            return self._send(200, b'{"ok":true}')
        self._forward(body)

    def _forward(self, body):
        mode, to = STATE["mode"], STATE["to"]
        events = []
        if body and self.path.startswith("/services/collector") and "health" not in self.path:
            try:
                events = split_json(body)
            except ValueError:
                events = []
        if events and mode == "reject":
            with STATE["lock"]:
                STATE["log"] += [summarize(o, mode, 400) for o in events if isinstance(o, dict)]
            return self._send(400, b'{"text":"Incorrect index","code":7,"invalid-event-number":0}')
        if events and mode == "drop":
            with STATE["lock"]:
                STATE["log"] += [summarize(o, mode, "not forwarded") for o in events if isinstance(o, dict)]
            return self._send(200, SUCCESS)
        if events and mode in ("reindex_event", "reindex_metric"):
            want_metric = mode == "reindex_metric"
            for o in events:
                if isinstance(o, dict) and (o.get("event") == "metric") == want_metric:
                    o["index"] = to
            body = b"".join(json.dumps(o).encode() for o in events)
        conn = http.client.HTTPSConnection(*UPSTREAM, context=CTX, timeout=30)
        hdrs = {k: v for k, v in self.headers.items() if k.lower() not in ("host", "content-length", "connection")}
        try:
            conn.request(self.command, self.path, body=body or None, headers=hdrs)
            r = conn.getresponse()
            data = r.read()
            code = r.status
        except OSError as e:
            return self._send(502, json.dumps({"text": "upstream unreachable", "error": type(e).__name__}).encode())
        finally:
            conn.close()
        if events:
            with STATE["lock"]:
                STATE["log"] += [summarize(o, mode, code) for o in events if isinstance(o, dict)]
        self._send(code, data)


def main():
    global UPSTREAM
    a = argparse.ArgumentParser()
    a.add_argument("--port", type=int, default=19990)
    a.add_argument("--upstream-port", type=int, default=19088)
    a.add_argument("--upstream-host", default="127.0.0.1")
    a.add_argument("--bind", default="127.0.0.1")
    args = a.parse_args()
    # RC lab: the tap runs inside the engine container (bind 0.0.0.0 there, published to host loopback only) and fronts the lab's own HEC at splunk:8088 on the private network.
    assert (args.upstream_host, args.upstream_port) in (("127.0.0.1", 19088), ("127.0.0.1", 39088), ("splunk", 8088)), "this tap only fronts the isolated labs (HEC 19088 TA-validation, 39088 / splunk:8088 release-candidate install)"
    UPSTREAM = (args.upstream_host, args.upstream_port)
    ThreadingHTTPServer((args.bind, args.port), H).serve_forever()


if __name__ == "__main__":
    main()
