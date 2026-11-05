#!/usr/bin/env python3
"""Throwaway local HEC receiver for the Phase 6 browser tests (loopback only, no Splunk, no credentials). It acknowledges events like HEC does and counts them per sourcetype.
  python scripts/phase6_fake_hec.py [PORT]      GET /_stats shows counts; POST /_mode?m=reject makes it answer 403 like a bad token; POST /_mode?m=ok restores it.
It cannot index or search anything: a real 'indexed' confirmation is out of its reach by design."""
import json
import sys
from collections import Counter
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

STATE = {"mode": "ok", "by_sourcetype": Counter(), "events": 0}


class H(BaseHTTPRequestHandler):
    def _send(self, code, obj):
        b = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def log_message(self, *a):
        pass

    def do_GET(self):
        if self.path.startswith("/_stats"):
            return self._send(200, {"mode": STATE["mode"], "events": STATE["events"], "by_sourcetype": STATE["by_sourcetype"]})
        return self._send(200, {"text": "HEC is healthy", "code": 17})

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(n).decode("utf-8", "replace")
        if self.path.startswith("/_mode"):
            STATE["mode"] = "reject" if "m=reject" in self.path else "ok"
            return self._send(200, {"mode": STATE["mode"]})
        if STATE["mode"] == "reject":
            return self._send(403, {"text": "Invalid token", "code": 4})
        dec, i, body = json.JSONDecoder(), 0, body.strip()
        while i < len(body):
            obj, j = dec.raw_decode(body, i)
            STATE["events"] += 1
            STATE["by_sourcetype"][obj.get("sourcetype", "?")] += 1
            i = j
            while i < len(body) and body[i].isspace():
                i += 1
        return self._send(200, {"text": "Success", "code": 0})


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", int(sys.argv[1]) if len(sys.argv) > 1 else 18599), H).serve_forever()
