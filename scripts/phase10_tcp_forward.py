#!/usr/bin/env python3
"""Plain TCP forwarder (stdlib): LISTEN_PORT on 127.0.0.1 -> HOST:PORT. Run inside the RC lab engine container so the engine reaches the lab Splunk's management port on its own loopback
(the product only allows a self-signed certificate on loopback). Refuses any target other than the RC lab's Splunk container.  usage: phase10_tcp_forward.py LISTEN_PORT splunk PORT"""
import socket
import sys
import threading

listen, host, port = int(sys.argv[1]), sys.argv[2], int(sys.argv[3])
assert host == "splunk", "only the RC lab Splunk container is a valid target"


def pump(a, b):
    try:
        while (d := a.recv(65536)):
            b.sendall(d)
    except OSError:
        pass
    finally:
        for s in (a, b):
            try:
                s.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass


srv = socket.socket()
srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
srv.bind(("127.0.0.1", listen))
srv.listen(64)
while True:
    c, _ = srv.accept()
    try:
        u = socket.create_connection((host, port), timeout=10)
    except OSError:
        c.close()
        continue
    threading.Thread(target=pump, args=(c, u), daemon=True).start()
    threading.Thread(target=pump, args=(u, c), daemon=True).start()
