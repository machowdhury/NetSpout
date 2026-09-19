"""
Telemetry Dispatcher Engine: Dual Transport for Splunk HEC and Syslog (UDP/TCP)
"""

import socket
import json
import time
import urllib.request
import urllib.error
import ssl
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple

from app.models import TelemetryTransportConfig, LogEntry, Node


def format_rfc5424_message(
    facility: int,
    severity: int,
    hostname: str,
    app_name: str,
    procid: str,
    msg_id: str,
    message: str,
    structured_data: str = "-"
) -> str:
    """
    Format message according to RFC 5424 Syslog Protocol:
    <PRI>VERSION TIMESTAMP HOSTNAME APP-NAME PROCID MSGID STRUCTURED-DATA MSG
    PRI = Facility * 8 + Severity
    """
    pri = (facility * 8) + severity
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    clean_host = hostname.replace(" ", "_") or "sim-node"
    clean_app = app_name.replace(" ", "_") or "network-sim"
    clean_proc = str(procid) or "-"
    clean_msgid = msg_id or "-"
    
    header = f"<{pri}>1 {now_iso} {clean_host} {clean_app} {clean_proc} {clean_msgid} {structured_data} "
    return header + message


def format_rfc3164_message(
    facility: int,
    severity: int,
    hostname: str,
    app_name: str,
    message: str
) -> str:
    """
    Format message according to RFC 3164 (The BSD syslog Protocol):
    <PRI>Mmm dd hh:mm:ss HOSTNAME APP-NAME: MSG
    """
    pri = (facility * 8) + severity
    now_bsd = datetime.now().strftime("%b %d %H:%M:%S")
    clean_host = hostname.replace(" ", "_") or "sim-node"
    clean_app = app_name.replace(" ", "_") or "network-sim"
    return f"<{pri}>{now_bsd} {clean_host} {clean_app}: {message}"


class TelemetryDispatcher:
    """
    High-throughput asynchronous telemetry dispatcher with dual HEC and Syslog streaming.
    """
    def __init__(self):
        self.stats = {
            "hec_dispatched": 0,
            "syslog_dispatched": 0,
            "hec_errors": 0,
            "syslog_errors": 0,
            "last_error": None,
            "last_active": None
        }

    def emit_syslog(
        self,
        raw_message: str,
        host: str = "127.0.0.1",
        port: int = 514,
        protocol: str = "udp",
        facility: int = 16, # local0
        severity: int = 6,  # informational
        hostname: str = "sim-device",
        app_name: str = "netops",
        syslog_format: str = "rfc5424"
    ) -> Tuple[bool, str]:
        """
        Send raw message to target Syslog destination over UDP or TCP socket.
        """
        try:
            if syslog_format.lower() == "rfc3164":
                payload_str = format_rfc3164_message(facility, severity, hostname, app_name, raw_message)
            else:
                payload_str = format_rfc5424_message(facility, severity, hostname, app_name, "-", "-", raw_message)

            payload_bytes = payload_str.encode("utf-8")

            if protocol.lower() == "udp":
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.settimeout(2.0)
                try:
                    sock.sendto(payload_bytes, (host, port))
                finally:
                    sock.close()
            else:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2.0)
                try:
                    sock.connect((host, port))
                    sock.sendall(payload_bytes + b"\n")
                finally:
                    sock.close()

            self.stats["syslog_dispatched"] += 1
            self.stats["last_active"] = time.time()
            return True, f"Sent {len(payload_bytes)} bytes to syslog://{host}:{port} ({protocol.upper()})"

        except Exception as e:
            self.stats["syslog_errors"] += 1
            self.stats["last_error"] = f"Syslog error ({host}:{port}): {str(e)}"
            return False, str(e)

    def emit_hec(
        self,
        event: Dict[str, Any],
        hec_url: str,
        token: str,
        ssl_verify: bool = False
    ) -> Tuple[bool, str]:
        """
        Send structured event payload to Splunk HTTP Event Collector.
        """
        try:
            ctx = ssl.create_default_context()
            if not ssl_verify:
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE

            payload = json.dumps(event).encode("utf-8")
            req = urllib.request.Request(
                hec_url,
                data=payload,
                headers={
                    "Authorization": f"Splunk {token}",
                    "Content-Type": "application/json"
                }
            )

            with urllib.request.urlopen(req, timeout=3.0, context=ctx) as resp:
                resp_text = resp.read().decode("utf-8", errors="replace")
                self.stats["hec_dispatched"] += 1
                self.stats["last_active"] = time.time()
                return True, f"HEC HTTP {resp.status}: {resp_text[:100]}"

        except Exception as e:
            self.stats["hec_errors"] += 1
            self.stats["last_error"] = f"HEC error: {str(e)}"
            return False, str(e)

    def dispatch_log(
        self,
        log: LogEntry,
        transport: Optional[TelemetryTransportConfig] = None
    ) -> Dict[str, Any]:
        """
        Route log entry to configured transports (HEC, Syslog, or both).
        """
        if not transport:
            return {"hec": None, "syslog": None}

        results = {}

        # 1. Splunk HEC Transport
        if transport.hec_enabled and transport.hec_url and transport.hec_token:
            target_index = transport.hec_index or "idx_network_ops"
            # Route MDT telemetry to dedicated metric index if appropriate
            if log.sourcetype in ("cisco:ios:mdt", "cisco:ios:mdt:metric") and not transport.hec_index:
                target_index = "cisco_mdt_metrics"

            is_metric = (target_index == "cisco_mdt_metrics" or 
                         "metric" in target_index.lower() or 
                         log.sourcetype in ("cisco:ios:mdt", "cisco:ios:mdt:metric"))

            if is_metric:
                metric_fields = {
                    "metric_name:cpu.utilization": 24.5,
                    "metric_name:memory.utilization": 38.2,
                    "metric_name:interface.octets.in": 48920194.0,
                    "metric_name:interface.octets.out": 78920140.0,
                    "metric_name:interface.errors.in": 0.0,
                    "metric_name:queue_depth_bytes": 14200.0,
                    "metric_name:buffer_utilization_pct": 18.5,
                    "_value": 24.5,
                    "device": log.device_id,
                    "host": log.device_id,
                    "vendor": log.vendor or "cisco",
                    "status": log.status or "normal",
                    "action": log.action or "streamed"
                }
                # Parse raw_log if it contains JSON to extract real telemetry numbers
                if log.raw_log:
                    try:
                        raw_obj = json.loads(log.raw_log) if isinstance(log.raw_log, str) else log.raw_log
                        if isinstance(raw_obj, dict):
                            if "fields" in raw_obj and isinstance(raw_obj["fields"], dict):
                                metric_fields.update(raw_obj["fields"])
                            if "data" in raw_obj and isinstance(raw_obj["data"], dict):
                                for k, v in raw_obj["data"].items():
                                    if isinstance(v, (int, float)):
                                        metric_fields[f"metric_name:{k}"] = float(v)
                            for k, v in raw_obj.items():
                                if isinstance(v, (int, float)) and k not in ("time", "timestamp", "telemetry_timestamp"):
                                    metric_fields[f"metric_name:{k}"] = float(v)
                    except Exception:
                        pass

                hec_payload = {
                    "time": time.time(),
                    "event": "metric",
                    "host": log.device_id,
                    "source": "cisco:ios:mdt",
                    "sourcetype": "cisco:ios:mdt:metric",
                    "index": target_index if target_index != "idx_network_ops" else "cisco_mdt_metrics",
                    "fields": metric_fields
                }
            else:
                hec_payload = {
                    "event": log.raw_log,
                    "time": time.time(),
                    "host": log.device_id,
                    "source": "network-topology-simulator",
                    "sourcetype": log.sourcetype or "cisco:ios",
                    "index": target_index,
                    "fields": {
                        "action": log.action,
                        "signature": log.signature,
                        "status": log.status,
                        "src_ip": log.src_ip,
                        "dest_ip": log.dest_ip,
                        "protocol": log.protocol,
                        "vendor": log.vendor,
                        "node_type": log.node_type
                    }
                }
            ok, msg = self.emit_hec(hec_payload, transport.hec_url, transport.hec_token)
            results["hec"] = {"success": ok, "message": msg}

        # 2. Syslog Transport (UDP/TCP)
        if transport.syslog_enabled and transport.syslog_host and transport.syslog_port:
            severity_map = {
                "blocked": 4,  # Warning
                "breached": 2, # Critical
                "degraded": 3, # Error
                "normal": 6    # Informational
            }
            sev = severity_map.get(log.status, 6)
            ok, msg = self.emit_syslog(
                raw_message=log.raw_log,
                host=transport.syslog_host,
                port=transport.syslog_port,
                protocol=transport.syslog_protocol,
                facility=transport.syslog_facility,
                severity=sev,
                hostname=log.device_id,
                app_name=log.sourcetype or log.vendor,
                syslog_format=transport.syslog_format
            )
            results["syslog"] = {"success": ok, "message": msg}

        return results


# Global singleton dispatcher instance
dispatcher = TelemetryDispatcher()
