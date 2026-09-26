#!/usr/bin/env python3
"""
NetSpout Flow Collector Forwarder
Tails GoFlow2 JSON output and forwards decoded NetFlow v9 / IPFIX events
to Splunk HTTP Event Collector (HEC) without NetSpout bypassing the collector tier.
Exposes a lightweight HTTP health/observability endpoint on port 8082.
"""

import http.server
import json
import logging
import os
import ssl
import sys
import threading
import time
import urllib.error
import urllib.request
from collections import deque
from typing import Any, Dict, List, Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("flow_forwarder")

FLOW_FILE = os.environ.get("FLOW_FILE", "/flows/flows.json")
SPLUNK_HEC_URL = os.environ.get(
    "SPLUNK_HEC_URL",
    "https://host.docker.internal:8888/services/collector/event"
)
SPLUNK_HEC_TOKEN = os.environ.get(
    "SPLUNK_HEC_TOKEN",
    "00000000-0000-0000-0000-000000000000"
)
SPLUNK_INDEX = os.environ.get("SPLUNK_INDEX", "idx_network_ops")
SPLUNK_SOURCETYPE = os.environ.get("SPLUNK_SOURCETYPE", "netflow:collector")
STATUS_PORT = int(os.environ.get("STATUS_PORT", "8082"))

# Shared state
STATE = {
    "status": "healthy",
    "flows_read": 0,
    "flows_forwarded": 0,
    "forward_failures": 0,
    "last_forward_timestamp": 0.0,
    "last_error": None,
    "simulate_splunk_failure": False,
    "recent_flows": deque(maxlen=50)
}
STATE_LOCK = threading.Lock()


def build_ssl_context() -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def forward_to_splunk(flow: Dict[str, Any]) -> bool:
    """Forwards a decoded flow record to Splunk HEC."""
    with STATE_LOCK:
        if STATE["simulate_splunk_failure"]:
            STATE["forward_failures"] += 1
            STATE["last_error"] = "Simulated Splunk ingestion failure active"
            logger.warning("Dropping flow forward due to simulated Splunk failure")
            return False

    # Extract flow timestamp in seconds if available
    flow_time = time.time()
    if "time_flow_end_ns" in flow and flow["time_flow_end_ns"]:
        flow_time = float(flow["time_flow_end_ns"]) / 1e9
    elif "time_received_ns" in flow and flow["time_received_ns"]:
        flow_time = float(flow["time_received_ns"]) / 1e9

    payload = {
        "time": flow_time,
        "host": "netspout-flow-collector",
        "source": f"goflow2:{flow.get('type', 'FLOW').lower()}",
        "sourcetype": SPLUNK_SOURCETYPE,
        "index": SPLUNK_INDEX,
        "event": flow
    }

    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(SPLUNK_HEC_URL, data=body, method="POST")
    req.add_header("Authorization", f"Splunk {SPLUNK_HEC_TOKEN}")
    req.add_header("Content-Type", "application/json")

    ctx = build_ssl_context() if SPLUNK_HEC_URL.startswith("https") else None

    try:
        with urllib.request.urlopen(req, context=ctx, timeout=5.0) as resp:
            if resp.status == 200:
                with STATE_LOCK:
                    STATE["flows_forwarded"] += 1
                    STATE["last_forward_timestamp"] = time.time()
                    STATE["last_error"] = None
                return True
            else:
                err_msg = f"HEC responded with HTTP {resp.status}"
                with STATE_LOCK:
                    STATE["forward_failures"] += 1
                    STATE["last_error"] = err_msg
                logger.error(err_msg)
                return False
    except Exception as exc:
        with STATE_LOCK:
            STATE["forward_failures"] += 1
            STATE["last_error"] = str(exc)
        logger.error(f"Failed to forward flow to Splunk: {exc}")
        return False


def tail_flow_file():
    """Continuously tails FLOW_FILE and ships records to Splunk."""
    logger.info(f"Starting flow file tailer on: {FLOW_FILE}")
    last_inode = None
    file_obj = None

    while True:
        try:
            if not os.path.exists(FLOW_FILE):
                time.sleep(0.5)
                continue

            stat = os.stat(FLOW_FILE)
            if file_obj is None or stat.st_ino != last_inode:
                if file_obj is not None:
                    file_obj.close()
                file_obj = open(FLOW_FILE, "r", encoding="utf-8")
                last_inode = stat.st_ino
                logger.info(f"Opened flow file {FLOW_FILE} (inode={last_inode})")

            line = file_obj.readline()
            if not line:
                time.sleep(0.1)
                continue

            line = line.strip()
            if not line:
                continue

            try:
                flow = json.loads(line)
            except json.JSONDecodeError:
                logger.warning(f"Malformed JSON in flow file: {line[:100]}")
                continue

            with STATE_LOCK:
                STATE["flows_read"] += 1
                STATE["recent_flows"].append(flow)

            logger.info(
                f"Decoded {flow.get('type', 'FLOW')} record: "
                f"{flow.get('src_addr')}:{flow.get('src_port')} -> "
                f"{flow.get('dst_addr')}:{flow.get('dst_port')} "
                f"({flow.get('bytes', 0)} bytes, {flow.get('packets', 0)} pkts, "
                f"obs_domain={flow.get('observation_domain_id')})"
            )

            forward_to_splunk(flow)

        except Exception as exc:
            logger.error(f"Error in tail loop: {exc}")
            time.sleep(1.0)


class StatusHTTPHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # Suppress default noisy access logs

    def do_GET(self):
        if self.path in ["/health", "/status"]:
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            with STATE_LOCK:
                resp_data = {
                    "status": STATE["status"],
                    "flows_read": STATE["flows_read"],
                    "flows_forwarded": STATE["flows_forwarded"],
                    "forward_failures": STATE["forward_failures"],
                    "last_forward_timestamp": STATE["last_forward_timestamp"],
                    "last_error": STATE["last_error"],
                    "simulate_splunk_failure": STATE["simulate_splunk_failure"],
                    "recent_flows_count": len(STATE["recent_flows"])
                }
            self.wfile.write(json.dumps(resp_data, indent=2).encode("utf-8"))

        elif self.path == "/flows":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            with STATE_LOCK:
                flows_list = list(STATE["recent_flows"])
            self.wfile.write(json.dumps(flows_list, indent=2).encode("utf-8"))

        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == "/clear":
            with STATE_LOCK:
                STATE["recent_flows"].clear()
                STATE["flows_read"] = 0
                STATE["flows_forwarded"] = 0
                STATE["forward_failures"] = 0
                STATE["last_error"] = None
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"message": "State cleared"}')

        elif self.path == "/simulate_splunk_failure":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            try:
                data = json.loads(body) if body else {}
                fail = bool(data.get("fail", True))
                with STATE_LOCK:
                    STATE["simulate_splunk_failure"] = fail
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                resp = json.dumps({"simulate_splunk_failure": fail})
                self.wfile.write(resp.encode("utf-8"))
            except Exception as e:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(str(e).encode("utf-8"))

        else:
            self.send_response(404)
            self.end_headers()


def start_status_server():
    server = http.server.ThreadingHTTPServer(("0.0.0.0", STATUS_PORT), StatusHTTPHandler)
    logger.info(f"Health and status server running on port {STATUS_PORT}")
    server.serve_forever()


def main():
    logger.info("Initializing NetSpout Flow Collector Forwarder")
    logger.info(f"Target Splunk HEC: {SPLUNK_HEC_URL} (index={SPLUNK_INDEX}, sourcetype={SPLUNK_SOURCETYPE})")

    server_thread = threading.Thread(target=start_status_server, daemon=True)
    server_thread.start()

    tail_flow_file()


if __name__ == "__main__":
    main()
