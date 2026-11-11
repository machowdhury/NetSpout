#!/usr/bin/env python3
"""Disposable fake Splunk HEC (HTTPS, self-signed) for generator profiling: accepts /services/collector/event, counts events, replies like HEC. Not Splunk.
  python scripts/phase17_fakehec.py <port> <cert.pem> <key.pem> <count_file> [capture.ndjson]   (capture: one line per request: receive time + raw body)"""
import json, ssl, sys, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
port, cert, key, cfile = int(sys.argv[1]), sys.argv[2], sys.argv[3], sys.argv[4]
cap = open(sys.argv[5], "w", buffering=1) if len(sys.argv) > 5 else None
n = [0]; lock = threading.Lock()
class H(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        k = body.count(b'"event"')
        with lock:
            n[0] += k
            open(cfile, "w").write(str(n[0]))
        if cap:
            cap.write(json.dumps({"rx": __import__("time").time(), "body": body.decode()}) + "\n")
        out = b'{"text":"Success","code":0}'
        self.send_response(200); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(out))); self.end_headers(); self.wfile.write(out)
    def log_message(self, *a): pass
s = ThreadingHTTPServer(("127.0.0.1", port), H)
c = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER); c.load_cert_chain(cert, key)
s.socket = c.wrap_socket(s.socket, server_side=True)
s.serve_forever()
