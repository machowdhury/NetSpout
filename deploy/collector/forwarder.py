#!/usr/bin/env python3
"""
NetSpout Flow Collector Forwarder (Hardened Production Service).
Tails GoFlow2 JSON output and forwards decoded NetFlow v9 / IPFIX events
to Splunk HTTP Event Collector (HEC) with bounded retries, backoff, and non-root execution.
Exposes a lightweight HTTP health/observability & Prometheus endpoint on port 8082.

Delivery Semantics:
  - AT-LEAST-ONCE: Up to 3 bounded retries with exponential backoff for transient HEC errors.
  - BEST-EFFORT on sustained downstream outage: Prevents unbounded memory growth.
"""

import http.server
import configparser
import json
import logging
import os
import ssl
import sys
import threading
import time
import urllib.error
import urllib.parse
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
SPLUNK_HEC_TOKEN_FILE = os.environ.get("SPLUNK_HEC_TOKEN_FILE", "")
SPLUNK_HEC_ALLOW_INSECURE_TLS = (
    os.environ.get("SPLUNK_HEC_ALLOW_INSECURE_TLS", "false").strip().lower()
    in {"1", "true", "yes"}
)
SPLUNK_INDEX = os.environ.get("SPLUNK_INDEX", "idx_network_ops")
SPLUNK_SOURCETYPE = os.environ.get("SPLUNK_SOURCETYPE", "netflow:collector")
STATUS_PORT = int(os.environ.get("STATUS_PORT", "8082"))
MAX_RETRIES = int(os.environ.get("MAX_RETRIES", "3"))
MAX_FILE_SIZE_BYTES = int(os.environ.get("MAX_FILE_SIZE_BYTES", str(50 * 1024 * 1024)))  # 50 MB

# Shared operational state
STATE = {
    "status": "HEALTHY",
    "flows_read": 0,
    "flows_forwarded": 0,
    "forward_failures": 0,
    "retry_attempts": 0,
    "last_forward_timestamp": 0.0,
    "last_error": None,
    "simulate_splunk_failure": False,
    "recent_flows": deque(maxlen=100),
    "correlations": {},
    "delivery_semantics": "AT_LEAST_ONCE_WITH_BOUNDED_RETRY",
    "service_started_at": time.time()
}
STATE_LOCK = threading.Lock()
_HEC_TOKEN: Optional[str] = None


def delivery_health_state() -> str:
    """Return destination delivery readiness independently of process liveness."""
    with STATE_LOCK:
        return (
            "DEGRADED"
            if STATE["simulate_splunk_failure"] or STATE["last_error"]
            else "HEALTHY"
        )


def load_hec_token() -> str:
    """Loads a HEC token from the environment or a read-only Splunk config."""
    global _HEC_TOKEN
    if _HEC_TOKEN:
        return _HEC_TOKEN

    token = os.environ.get("SPLUNK_HEC_TOKEN", "").strip()
    if not token and SPLUNK_HEC_TOKEN_FILE:
        parser = configparser.ConfigParser()
        try:
            with open(SPLUNK_HEC_TOKEN_FILE, "r", encoding="utf-8") as token_file:
                contents = token_file.read()
            if contents.lstrip().startswith("["):
                parser.read_string(contents)
                token = next(
                    (
                        parser.get(section, "token").strip()
                        for section in parser.sections()
                        if section.startswith("http://")
                        and parser.has_option(section, "token")
                    ),
                    "",
                )
            else:
                token = contents.strip()
        except (OSError, configparser.Error) as exc:
            raise RuntimeError(
                f"Unable to read SPLUNK_HEC_TOKEN_FILE: {exc}"
            ) from exc

    if not token:
        raise RuntimeError(
            "Splunk HEC token is required via SPLUNK_HEC_TOKEN or "
            "SPLUNK_HEC_TOKEN_FILE"
        )
    _HEC_TOKEN = token
    return token


def build_ssl_context() -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    if SPLUNK_HEC_ALLOW_INSECURE_TLS:
        hostname = urllib.parse.urlparse(SPLUNK_HEC_URL).hostname
        if hostname not in {
            "localhost",
            "127.0.0.1",
            "::1",
            "splunk-netspout",
            "host.docker.internal",
        }:
            raise RuntimeError(
                "TLS verification may be disabled only for the documented local lab"
            )
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    return ctx


def forward_to_splunk(flow: Dict[str, Any]) -> bool:
    """
    Forwards a decoded flow record to Splunk HEC with bounded retry and backoff.
    """
    with STATE_LOCK:
        if STATE["simulate_splunk_failure"]:
            STATE["forward_failures"] += 1
            STATE["last_error"] = "Simulated Splunk ingestion failure active"
            logger.warning("Dropping flow forward due to simulated Splunk failure")
            return False

    flow_time = time.time()
    # Scenario packets may intentionally model a historical device clock.
    # Index fresh lab telemetry at collector receipt time so bounded run
    # searches can observe it, while preserving the device timestamp in _raw.
    if "time_received_ns" in flow and flow["time_received_ns"]:
        flow_time = float(flow["time_received_ns"]) / 1e9
    elif "time_flow_end_ns" in flow and flow["time_flow_end_ns"]:
        flow_time = float(flow["time_flow_end_ns"]) / 1e9

    payload = {
        "time": flow_time,
        "host": "netspout-flow-collector",
        "source": f"goflow2:{flow.get('type', 'FLOW').lower()}",
        "sourcetype": SPLUNK_SOURCETYPE,
        "index": SPLUNK_INDEX,
        "event": flow
    }

    try:
        hec_token = load_hec_token()
    except RuntimeError as exc:
        with STATE_LOCK:
            STATE["forward_failures"] += 1
            STATE["last_error"] = str(exc)
        logger.error("%s", exc)
        return False

    body = json.dumps(payload).encode("utf-8")
    ctx = build_ssl_context() if SPLUNK_HEC_URL.startswith("https") else None

    # Bounded retry loop (at-least-once semantics)
    attempts = 0
    backoff = 0.1
    last_exc = None

    while attempts < MAX_RETRIES:
        attempts += 1
        req = urllib.request.Request(SPLUNK_HEC_URL, data=body, method="POST")
        req.add_header("Authorization", f"Splunk {hec_token}")
        req.add_header("Content-Type", "application/json")

        try:
            with urllib.request.urlopen(req, context=ctx, timeout=4.0) as resp:
                response_body = resp.read(4096).decode("utf-8", errors="replace")
                try:
                    response_payload = json.loads(response_body)
                except json.JSONDecodeError:
                    response_payload = {}
                hec_code = response_payload.get("code")
                if resp.status == 200 and hec_code == 0:
                    with STATE_LOCK:
                        STATE["flows_forwarded"] += 1
                        STATE["last_forward_timestamp"] = time.time()
                        STATE["last_error"] = None
                    return True
                else:
                    last_exc = (
                        f"HEC rejected flow: HTTP {resp.status}, "
                        f"code={hec_code}, text={response_payload.get('text', 'unknown')}"
                    )
                    if resp.status in (400, 401, 403) or (
                        hec_code is not None and hec_code != 0
                    ):
                        # Client error: do not retry invalid auth or bad request
                        break
        except Exception as exc:
            last_exc = str(exc)

        if attempts < MAX_RETRIES:
            with STATE_LOCK:
                STATE["retry_attempts"] += 1
            time.sleep(backoff)
            backoff *= 2.0

    # Retries exhausted or unrecoverable error
    err_msg = f"Failed to forward flow after {attempts} attempts: {last_exc}"
    with STATE_LOCK:
        STATE["forward_failures"] += 1
        STATE["last_error"] = err_msg
    logger.error(err_msg)
    return False


def attach_registered_correlation(flow: Dict[str, Any]) -> Dict[str, Any]:
    """Attach run metadata after decode without changing the native packet."""
    domain = str(flow.get("observation_domain_id", ""))
    now = time.time()
    with STATE_LOCK:
        expired = [
            key
            for key, value in STATE["correlations"].items()
            if float(value.get("expires_at", 0)) <= now
        ]
        for key in expired:
            STATE["correlations"].pop(key, None)
        correlation = STATE["correlations"].get(domain)
    if not correlation:
        return flow
    enriched = dict(flow)
    for key in (
        "netspout_run_id",
        "netspout_scenario_id",
        "netspout_device_id",
        "netspout_phase",
    ):
        enriched[key] = correlation[key]
    enriched["netspout_correlation_boundary"] = "COLLECTOR_NORMALIZED"
    return enriched


def check_and_rotate_file():
    """Performs safety size rotation on the collector output file if it exceeds limit."""
    try:
        if os.path.exists(FLOW_FILE):
            size = os.path.getsize(FLOW_FILE)
            if size > MAX_FILE_SIZE_BYTES:
                backup = f"{FLOW_FILE}.1"
                if os.path.exists(backup):
                    os.remove(backup)
                os.rename(FLOW_FILE, backup)
                logger.info(f"Rotated {FLOW_FILE} ({size} bytes) to {backup}")
    except Exception as exc:
        logger.warning(f"File rotation check failed: {exc}")


def tail_flow_file():
    """Continuously tails FLOW_FILE with inode tracking and truncation detection."""
    logger.info(f"Starting hardened flow file tailer on: {FLOW_FILE}")
    last_inode = None
    last_pos = 0
    file_obj = None

    while True:
        try:
            if not os.path.exists(FLOW_FILE):
                time.sleep(0.5)
                continue

            stat = os.stat(FLOW_FILE)
            
            # Case 1: Inode change (file rotated / replaced)
            if file_obj is None or stat.st_ino != last_inode:
                if file_obj is not None:
                    file_obj.close()
                file_obj = open(FLOW_FILE, "r", encoding="utf-8")
                last_inode = stat.st_ino
                last_pos = 0
                logger.info(f"Opened flow file {FLOW_FILE} (inode={last_inode})")

            # Case 2: File truncated in place
            elif stat.st_size < last_pos:
                logger.info(f"File truncation detected (size {stat.st_size} < pos {last_pos}). Seeking to 0.")
                file_obj.seek(0)
                last_pos = 0

            line = file_obj.readline()
            if not line:
                last_pos = file_obj.tell()
                time.sleep(0.1)
                continue

            last_pos = file_obj.tell()
            line = line.strip()
            if not line:
                continue

            try:
                flow = json.loads(line)
            except json.JSONDecodeError:
                logger.warning(f"Malformed JSON in flow file: {line[:100]}")
                continue
            flow = attach_registered_correlation(flow)

            with STATE_LOCK:
                STATE["flows_read"] += 1
                STATE["recent_flows"].append(flow)

            logger.info(
                f"Decoded {flow.get('type', 'FLOW')} record: "
                f"{flow.get('src_addr')}:{flow.get('src_port')} -> "
                f"{flow.get('dst_addr')}:{flow.get('dst_port')} "
                f"({flow.get('bytes', 0)} bytes, obs_domain={flow.get('observation_domain_id')})"
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
            delivery_status = delivery_health_state()
            with STATE_LOCK:
                resp_data = {
                    "status": delivery_status,
                    "delivery_semantics": STATE["delivery_semantics"],
                    "uptime_sec": round(time.time() - STATE["service_started_at"], 2),
                    "flows_read": STATE["flows_read"],
                    "flows_forwarded": STATE["flows_forwarded"],
                    "forward_failures": STATE["forward_failures"],
                    "retry_attempts": STATE["retry_attempts"],
                    "last_forward_timestamp": STATE["last_forward_timestamp"],
                    "last_error": STATE["last_error"],
                    "simulate_splunk_failure": STATE["simulate_splunk_failure"],
                    "recent_flows_count": len(STATE["recent_flows"]),
                    "active_correlations": len(STATE["correlations"]),
                }
            self.wfile.write(json.dumps(resp_data, indent=2).encode("utf-8"))

        elif self.path == "/metrics":
            # Prometheus text format
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; version=0.0.4")
            self.end_headers()
            with STATE_LOCK:
                f_read = STATE["flows_read"]
                f_fwd = STATE["flows_forwarded"]
                f_fail = STATE["forward_failures"]
                f_retries = STATE["retry_attempts"]
                q_depth = len(STATE["recent_flows"])
            prom_text = (
                f"# HELP netspout_forwarder_flows_read_total Total flows read from collector\n"
                f"# TYPE netspout_forwarder_flows_read_total counter\n"
                f"netspout_forwarder_flows_read_total {f_read}\n"
                f"# HELP netspout_forwarder_flows_forwarded_total Total flows forwarded to Splunk HEC\n"
                f"# TYPE netspout_forwarder_flows_forwarded_total counter\n"
                f"netspout_forwarder_flows_forwarded_total {f_fwd}\n"
                f"# HELP netspout_forwarder_failures_total Total forward failures\n"
                f"# TYPE netspout_forwarder_failures_total counter\n"
                f"netspout_forwarder_failures_total {f_fail}\n"
                f"# HELP netspout_forwarder_retry_attempts_total Total retry attempts\n"
                f"# TYPE netspout_forwarder_retry_attempts_total counter\n"
                f"netspout_forwarder_retry_attempts_total {f_retries}\n"
                f"# HELP netspout_forwarder_queue_depth In-memory recent flow buffer depth\n"
                f"# TYPE netspout_forwarder_queue_depth gauge\n"
                f"netspout_forwarder_queue_depth {q_depth}\n"
            )
            self.wfile.write(prom_text.encode("utf-8"))

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
                STATE["retry_attempts"] = 0
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

        elif self.path == "/correlations":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            try:
                data = json.loads(body)
                domain = int(data["observation_domain_id"])
                metadata = {
                    key: str(data[key])
                    for key in (
                        "netspout_run_id",
                        "netspout_scenario_id",
                        "netspout_device_id",
                        "netspout_phase",
                    )
                }
                if any(not value or len(value) > 256 for value in metadata.values()):
                    raise ValueError("correlation values must be 1-256 characters")
                metadata["expires_at"] = time.time() + 300
                with STATE_LOCK:
                    STATE["correlations"][str(domain)] = metadata
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(
                    json.dumps(
                        {
                            "registered": True,
                            "observation_domain_id": domain,
                            "boundary": "COLLECTOR_NORMALIZED",
                        }
                    ).encode("utf-8")
                )
            except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(exc)}).encode("utf-8"))

        else:
            self.send_response(404)
            self.end_headers()


def start_status_server():
    server = http.server.ThreadingHTTPServer(("0.0.0.0", STATUS_PORT), StatusHTTPHandler)
    logger.info(f"Health and status server running on port {STATUS_PORT}")
    server.serve_forever()


def main():
    logger.info("Initializing NetSpout Flow Collector Forwarder (Hardened Mode)")
    logger.info(f"Target Splunk HEC: {SPLUNK_HEC_URL} (index={SPLUNK_INDEX}, sourcetype={SPLUNK_SOURCETYPE})")
    logger.info(f"Running as UID={os.getuid()}, GID={os.getgid()}")
    load_hec_token()

    server_thread = threading.Thread(target=start_status_server, daemon=True)
    server_thread.start()

    tail_flow_file()


if __name__ == "__main__":
    main()
