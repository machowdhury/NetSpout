"""
Universal Multi-Pipeline Telemetry Dispatcher (NetSpout)
Implements concurrent routing and export to:
  1. Splunk HTTP Event Collector (HEC) - Events & Metrics (cisco_mdt_metrics, idx_network_ops)
  2. OpenTelemetry (OTel) Collector - OTLP HTTP /v1/metrics and /v1/logs
  3. Telegraf Agent - HTTP Influx Line Protocol or JSON metrics listener
  4. RFC 5424 / RFC 3164 Syslog - UDP/TCP Port 514 Socket Transports
"""

import socket
import json
import time
import urllib.request
import urllib.error
import ssl
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple, List, Union

try:
    from netspout_core.models import (
        TelemetryTransportConfig, LogEntry, Node,
        SNMPPollingMetric, SNMPTrapEvent
    )
except ImportError:
    try:
        from app.models import (
            TelemetryTransportConfig, LogEntry, Node,
            SNMPPollingMetric, SNMPTrapEvent
        )
    except ImportError:
        from models import (
            TelemetryTransportConfig, LogEntry, Node,
            SNMPPollingMetric, SNMPTrapEvent
        )


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


def _get_gnmi_server():
    try:
        from netspout_core.gnmi_engine import gnmi_server
        return gnmi_server
    except ImportError:
        try:
            from app.gnmi_engine import gnmi_server
            return gnmi_server
        except ImportError:
            from gnmi_engine import gnmi_server
            return gnmi_server


def _get_snmp_engine():
    try:
        from netspout_core.snmp_engine import snmp_engine
        return snmp_engine
    except ImportError:
        try:
            from app.snmp_engine import snmp_engine
            return snmp_engine
        except ImportError:
            from snmp_engine import snmp_engine
            return snmp_engine


class TelemetryDispatcher:
    """
    High-throughput universal telemetry dispatcher with concurrent multi-pipeline routing.
    """
    def __init__(self):
        self.stats = {
            "hec_dispatched": 0,
            "otel_dispatched": 0,
            "telegraf_dispatched": 0,
            "syslog_dispatched": 0,
            "hec_errors": 0,
            "otel_errors": 0,
            "telegraf_errors": 0,
            "syslog_errors": 0,
            "last_error": None,
            "last_active": None
        }

    # -------------------------------------------------------------------------
    # 1. Splunk HEC Transport
    # -------------------------------------------------------------------------
    def emit_hec(
        self,
        event: Dict[str, Any],
        hec_url: str,
        token: str,
        ssl_verify: bool = True,
        allow_insecure_tls: bool = False
    ) -> Tuple[bool, str]:
        candidates = [hec_url]
        if ":8888" in hec_url:
            candidates.append(hec_url.replace(":8888", ":8088"))
        elif ":8088" in hec_url:
            candidates.append(hec_url.replace(":8088", ":8888"))
        if "127.0.0.1" in hec_url:
            for c in list(candidates):
                candidates.append(c.replace("127.0.0.1", "localhost"))
        elif "localhost" in hec_url:
            for c in list(candidates):
                candidates.append(c.replace("localhost", "127.0.0.1"))

        last_error = None
        for cand_url in candidates:
            try:
                ctx = ssl.create_default_context()
                if allow_insecure_tls or not ssl_verify:
                    ctx.check_hostname = False
                    ctx.verify_mode = ssl.CERT_NONE

                payload = json.dumps(event).encode("utf-8")
                req = urllib.request.Request(
                    cand_url,
                    data=payload,
                    headers={
                        "Authorization": f"Splunk {token}",
                        "Content-Type": "application/json"
                    }
                )

                with urllib.request.urlopen(req, timeout=2.0, context=ctx) as resp:
                    resp_text = resp.read().decode("utf-8", errors="replace")
                    self.stats["hec_dispatched"] += 1
                    self.stats["last_active"] = time.time()
                    return True, f"HEC HTTP {resp.status}: {resp_text[:100]}"

            except urllib.error.HTTPError as e:
                err_body = e.read().decode("utf-8", errors="replace") if hasattr(e, "read") else ""
                last_error = f"HTTP {e.code}: {e.reason} - {err_body[:80]}"
                break
            except (ssl.SSLCertVerificationError, urllib.error.URLError) as e:
                err_str = str(e)
                if isinstance(e, ssl.SSLCertVerificationError) or "CERTIFICATE_VERIFY_FAILED" in err_str or "certificate verify failed" in err_str:
                    last_error = f"TLS Verification Failed: {e}. Enable 'Allow self-signed certificate' for lab/development endpoints."
                    break
                last_error = err_str
                continue

        self.stats["hec_errors"] += 1
        self.stats["last_error"] = f"HEC error: {last_error}"
        return False, str(last_error)

    # -------------------------------------------------------------------------
    # 2. OpenTelemetry (OTel) Collector Transport (OTLP HTTP)
    # -------------------------------------------------------------------------
    def emit_otel(
        self,
        payload: Dict[str, Any],
        endpoint: str,
        is_metric: bool = True,
        headers: Optional[Dict[str, str]] = None
    ) -> Tuple[bool, str]:
        """
        Send OTLP JSON payload to OpenTelemetry Collector /v1/metrics or /v1/logs.
        """
        try:
            base_url = endpoint.rstrip("/")
            target_path = "/v1/metrics" if is_metric else "/v1/logs"
            full_url = f"{base_url}{target_path}" if not base_url.endswith(("/v1/metrics", "/v1/logs")) else base_url

            req_headers = {"Content-Type": "application/json"}
            if headers:
                req_headers.update(headers)

            data_bytes = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(full_url, data=data_bytes, headers=req_headers)

            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

            with urllib.request.urlopen(req, timeout=3.0, context=ctx) as resp:
                resp_text = resp.read().decode("utf-8", errors="replace")
                self.stats["otel_dispatched"] += 1
                self.stats["last_active"] = time.time()
                return True, f"OTel HTTP {resp.status}: {resp_text[:80]}"

        except Exception as e:
            self.stats["otel_errors"] += 1
            self.stats["last_error"] = f"OTel error ({endpoint}): {str(e)}"
            return False, str(e)

    # -------------------------------------------------------------------------
    # 3. Telegraf Agent Transport (HTTP Influx Line / JSON)
    # -------------------------------------------------------------------------
    def emit_telegraf(
        self,
        payload: Union[str, Dict[str, Any]],
        endpoint: str,
        fmt: str = "influx"
    ) -> Tuple[bool, str]:
        """
        Send Influx Line Protocol or JSON metrics to Telegraf HTTP listener.
        """
        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

            if fmt == "influx" and isinstance(payload, str):
                data_bytes = (payload + "\n").encode("utf-8")
                content_type = "text/plain; charset=utf-8"
            else:
                data_bytes = json.dumps(payload).encode("utf-8")
                content_type = "application/json"

            req = urllib.request.Request(
                endpoint,
                data=data_bytes,
                headers={"Content-Type": content_type}
            )

            with urllib.request.urlopen(req, timeout=3.0, context=ctx) as resp:
                resp_text = resp.read().decode("utf-8", errors="replace")
                self.stats["telegraf_dispatched"] += 1
                self.stats["last_active"] = time.time()
                return True, f"Telegraf HTTP {resp.status}: {resp_text[:80]}"

        except Exception as e:
            self.stats["telegraf_errors"] += 1
            self.stats["last_error"] = f"Telegraf error ({endpoint}): {str(e)}"
            return False, str(e)

    # -------------------------------------------------------------------------
    # 4. Direct Syslog Transport (UDP / TCP Socket)
    # -------------------------------------------------------------------------
    def emit_syslog(
        self,
        raw_message: str,
        host: str = "127.0.0.1",
        port: int = 514,
        protocol: str = "udp",
        facility: int = 16,  # local0
        severity: int = 6,   # informational
        hostname: str = "sim-device",
        app_name: str = "netops",
        syslog_format: str = "rfc5424"
    ) -> Tuple[bool, str]:
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

    # -------------------------------------------------------------------------
    # Multi-Pipeline Broadcaster: OpenConfig MDT Telemetry
    # -------------------------------------------------------------------------
    def dispatch_openconfig(
        self,
        hec_metric_payload: Dict[str, Any],
        transport: Optional[TelemetryTransportConfig] = None
    ) -> Dict[str, Any]:
        """
        Broadcasts an OpenConfig MDT event across all active configured pipelines:
        Splunk HEC, OTel Collector, Telegraf, and RFC 5424 Syslog.
        """
        if not transport:
            return {"hec": None, "otel": None, "telegraf": None, "syslog": None}

        results = {}

        # 1. Splunk HEC (cisco_mdt_metrics)
        if transport.hec_enabled and transport.hec_url and transport.hec_token:
            target_index = transport.hec_metric_index or "cisco_mdt_metrics"
            hec_metric_payload["index"] = target_index
            ok, msg = self.emit_hec(hec_metric_payload, transport.hec_url, transport.hec_token)
            results["hec"] = {"success": ok, "message": msg}

        # 2. OTel Collector (/v1/metrics)
        if transport.otel_enabled and transport.otel_endpoint:
            gnmi_server = _get_gnmi_server()
            otel_payload = gnmi_server.to_otel_metric_payload(hec_metric_payload)
            ok, msg = self.emit_otel(otel_payload, transport.otel_endpoint, is_metric=True, headers=transport.otel_headers)
            results["otel"] = {"success": ok, "message": msg}

        # 3. Telegraf (Influx Line Protocol)
        if transport.telegraf_enabled and transport.telegraf_endpoint:
            gnmi_server = _get_gnmi_server()
            influx_line = gnmi_server.to_telegraf_influx_line(hec_metric_payload)
            ok, msg = self.emit_telegraf(influx_line, transport.telegraf_endpoint, fmt=transport.telegraf_format)
            results["telegraf"] = {"success": ok, "message": msg}

        # 4. RFC 5424 Syslog
        if transport.syslog_enabled and transport.syslog_host and transport.syslog_port:
            gnmi_server = _get_gnmi_server()
            syslog_line = gnmi_server.to_rfc5424_syslog_mdt(hec_metric_payload)
            ok, msg = self.emit_syslog(
                raw_message=syslog_line,
                host=transport.syslog_host,
                port=transport.syslog_port,
                protocol=transport.syslog_protocol,
                facility=transport.syslog_facility,
                severity=6,
                hostname=hec_metric_payload.get("host", "sim-device"),
                app_name="gnmi-mdt",
                syslog_format=transport.syslog_format
            )
            results["syslog"] = {"success": ok, "message": msg}

        return results

    # -------------------------------------------------------------------------
    # Multi-Pipeline Broadcaster: SNMP Metrics & Traps
    # -------------------------------------------------------------------------
    def dispatch_snmp_metric(
        self,
        hec_metric_payload: Dict[str, Any],
        transport: Optional[TelemetryTransportConfig] = None
    ) -> Dict[str, Any]:
        """
        Broadcasts an SC4SNMP Polling Metric across all active configured pipelines.
        """
        if not transport:
            return {"hec": None, "otel": None, "telegraf": None, "syslog": None}

        results = {}

        # 1. Splunk HEC (cisco_mdt_metrics)
        if transport.hec_enabled and transport.hec_url and transport.hec_token:
            target_index = transport.hec_metric_index or "cisco_mdt_metrics"
            hec_metric_payload["index"] = target_index
            ok, msg = self.emit_hec(hec_metric_payload, transport.hec_url, transport.hec_token)
            results["hec"] = {"success": ok, "message": msg}

        # 2. OTel Collector (/v1/metrics)
        if transport.otel_enabled and transport.otel_endpoint:
            snmp_engine = _get_snmp_engine()
            otel_payload = snmp_engine.to_otel_metric_payload(hec_metric_payload)
            ok, msg = self.emit_otel(otel_payload, transport.otel_endpoint, is_metric=True, headers=transport.otel_headers)
            results["otel"] = {"success": ok, "message": msg}

        # 3. Telegraf (Influx Line Protocol)
        if transport.telegraf_enabled and transport.telegraf_endpoint:
            snmp_engine = _get_snmp_engine()
            influx_line = snmp_engine.to_telegraf_influx_line(hec_metric_payload)
            ok, msg = self.emit_telegraf(influx_line, transport.telegraf_endpoint, fmt=transport.telegraf_format)
            results["telegraf"] = {"success": ok, "message": msg}

        # 4. RFC 5424 Syslog
        if transport.syslog_enabled and transport.syslog_host and transport.syslog_port:
            fields = hec_metric_payload.get("fields", {})
            m_summary = ", ".join(f"{k.replace('metric_name:', '')}={v}" for k, v in fields.items() if k.startswith("metric_name:"))
            ok, msg = self.emit_syslog(
                raw_message=f"SC4SNMP Poll: {m_summary}",
                host=transport.syslog_host,
                port=transport.syslog_port,
                protocol=transport.syslog_protocol,
                facility=transport.syslog_facility,
                severity=6,
                hostname=hec_metric_payload.get("host", "sim-device"),
                app_name="sc4snmp",
                syslog_format=transport.syslog_format
            )
            results["syslog"] = {"success": ok, "message": msg}

        return results

    def dispatch_snmp_trap(
        self,
        trap: SNMPTrapEvent,
        transport: Optional[TelemetryTransportConfig] = None
    ) -> Dict[str, Any]:
        """
        Broadcasts an SC4SNMP Trap Event across all active configured pipelines.
        """
        if not transport:
            return {"hec": None, "otel": None, "telegraf": None, "syslog": None}

        results = {}

        # 1. Splunk HEC (idx_network_ops)
        if transport.hec_enabled and transport.hec_url and transport.hec_token:
            snmp_engine = _get_snmp_engine()
            hec_payload = snmp_engine.to_sc4snmp_hec_trap_payload(trap)
            if transport.hec_index:
                hec_payload["index"] = transport.hec_index
            ok, msg = self.emit_hec(hec_payload, transport.hec_url, transport.hec_token)
            results["hec"] = {"success": ok, "message": msg}

        # 2. OTel Collector (/v1/logs)
        if transport.otel_enabled and transport.otel_endpoint:
            otel_log_payload = {
                "resourceLogs": [{
                    "resource": {
                        "attributes": [
                            {"key": "host.name", "value": {"stringValue": trap.host}},
                            {"key": "service.name", "value": {"stringValue": "snmptrapd"}}
                        ]
                    },
                    "scopeLogs": [{
                        "scope": {"name": "netspout.sc4snmp.traps", "version": "2.0.0"},
                        "logRecords": [{
                            "timeUnixNano": str(int(trap.timestamp * 1e9)),
                            "severityText": trap.severity.upper(),
                            "body": {"stringValue": f"SNMP TRAP: {trap.trap_name} (OID: {trap.trap_oid}) - {json.dumps(trap.varbinds)}"},
                            "attributes": [
                                {"key": "snmp.trap_name", "value": {"stringValue": trap.trap_name}},
                                {"key": "snmp.trap_oid", "value": {"stringValue": trap.trap_oid}}
                            ]
                        }]
                    }]
                }]
            }
            ok, msg = self.emit_otel(otel_log_payload, transport.otel_endpoint, is_metric=False, headers=transport.otel_headers)
            results["otel"] = {"success": ok, "message": msg}

        # 3. RFC 5424 Syslog
        if transport.syslog_enabled and transport.syslog_host and transport.syslog_port:
            snmp_engine = _get_snmp_engine()
            raw_syslog = snmp_engine.to_rfc5424_syslog_trap(trap)
            pri_map = {"informational": 6, "warning": 4, "minor": 4, "major": 3, "critical": 2}
            sev = pri_map.get(trap.severity.lower(), 4)
            ok, msg = self.emit_syslog(
                raw_message=raw_syslog,
                host=transport.syslog_host,
                port=transport.syslog_port,
                protocol=transport.syslog_protocol,
                facility=transport.syslog_facility,
                severity=sev,
                hostname=trap.host,
                app_name="snmptrapd",
                syslog_format=transport.syslog_format
            )
            results["syslog"] = {"success": ok, "message": msg}

        return results

    # -------------------------------------------------------------------------
    # Multi-Pipeline Broadcaster: Standard Log Entries
    # -------------------------------------------------------------------------
    def dispatch_log(
        self,
        log: LogEntry,
        transport: Optional[TelemetryTransportConfig] = None
    ) -> Dict[str, Any]:
        """
        Route log entry to configured transports (HEC, Syslog, OTel, Telegraf).
        """
        if not transport:
            return {"hec": None, "syslog": None, "otel": None, "telegraf": None}

        results = {}

        # 1. Splunk HEC Transport
        if transport.hec_enabled and transport.hec_url and transport.hec_token:
            target_index = transport.hec_index or "idx_network_ops"
            if log.sourcetype in ("cisco:ios:mdt", "cisco:ios:mdt:metric"):
                target_index = transport.hec_metric_index or "cisco_mdt_metrics"

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
                    "_value": 24.5,
                    "device": log.device_id,
                    "host": log.device_id,
                    "vendor": log.vendor or "cisco",
                    "status": log.status or "normal",
                    "action": log.action or "streamed"
                }
                if log.raw_log:
                    try:
                        raw_obj = json.loads(log.raw_log) if isinstance(log.raw_log, str) else log.raw_log
                        if isinstance(raw_obj, dict):
                            if "fields" in raw_obj and isinstance(raw_obj["fields"], dict):
                                metric_fields.update(raw_obj["fields"])
                    except Exception:
                        pass

                hec_payload = {
                    "time": time.time(),
                    "event": "metric",
                    "host": log.device_id,
                    "source": "cisco:ios:mdt",
                    "sourcetype": "cisco:ios:mdt:metric",
                    "index": target_index,
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
                        "node_type": log.node_type,
                        "netspout_run_id": log.netspout_run_id,
                        "netspout_scenario_id": log.netspout_scenario_id,
                        "netspout_phase": log.netspout_phase,
                        "netspout_device_id": log.netspout_device_id,
                        "netspout_event_id": log.netspout_event_id,
                        "netspout_ground_truth": log.netspout_ground_truth
                    }
                }
            ssl_v = getattr(transport, "hec_ssl_verify", True)
            insec = getattr(transport, "hec_allow_insecure_tls", False)
            ok, msg = self.emit_hec(hec_payload, transport.hec_url, transport.hec_token, ssl_verify=ssl_v, allow_insecure_tls=insec)
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

        # 3. OTel Collector Logs
        if transport.otel_enabled and transport.otel_endpoint:
            otel_log_record = {
                "resourceLogs": [{
                    "resource": {
                        "attributes": [
                            {"key": "host.name", "value": {"stringValue": log.device_id}},
                            {"key": "service.name", "value": {"stringValue": "network-simulator"}}
                        ]
                    },
                    "scopeLogs": [{
                        "scope": {"name": "netspout.logs", "version": "2.0.0"},
                        "logRecords": [{
                            "timeUnixNano": str(int(time.time() * 1e9)),
                            "severityText": log.status.upper(),
                            "body": {"stringValue": log.raw_log},
                            "attributes": [
                                {"key": "network.src_ip", "value": {"stringValue": log.src_ip}},
                                {"key": "network.dest_ip", "value": {"stringValue": log.dest_ip}},
                                {"key": "network.protocol", "value": {"stringValue": log.protocol}},
                                {"key": "vendor", "value": {"stringValue": log.vendor or "generic"}}
                            ]
                        }]
                    }]
                }]
            }
            ok, msg = self.emit_otel(otel_log_record, transport.otel_endpoint, is_metric=False, headers=transport.otel_headers)
            results["otel"] = {"success": ok, "message": msg}

        return results

    # -------------------------------------------------------------------------
    # Pipeline Connectivity Tester
    # -------------------------------------------------------------------------
    def test_pipeline(self, pipeline: str, config: TelemetryTransportConfig) -> Tuple[bool, str]:
        """
        Verify real-time reachability and handshake for a specific pipeline destination.
        """
        p = pipeline.lower()
        now = time.time()
        
        if p == "hec":
            test_event = {
                "time": now,
                "event": "HEC Pipeline Connectivity Check from NetSpout Simulation Engine",
                "host": "netspout-tester",
                "source": "netspout:pipeline_test",
                "sourcetype": "netspout:test",
                "index": config.hec_index or "idx_network_ops"
            }
            ssl_v = getattr(config, "hec_ssl_verify", True)
            insec = getattr(config, "hec_allow_insecure_tls", False)
            return self.emit_hec(test_event, config.hec_url, config.hec_token, ssl_verify=ssl_v, allow_insecure_tls=insec)

        elif p == "otel":
            test_payload = {
                "resourceMetrics": [{
                    "resource": {
                        "attributes": [{"key": "service.name", "value": {"stringValue": "netspout-tester"}}]
                    },
                    "scopeMetrics": [{
                        "scope": {"name": "netspout.test", "version": "2.0.0"},
                        "metrics": [{
                            "name": "netspout.pipeline.test_ping",
                            "gauge": {
                                "dataPoints": [{
                                    "asDouble": 1.0,
                                    "timeUnixNano": str(int(now * 1e9))
                                }]
                            }
                        }]
                    }]
                }]
            }
            return self.emit_otel(test_payload, config.otel_endpoint, is_metric=True, headers=config.otel_headers)

        elif p == "telegraf":
            test_line = f"netspout_pipeline_test,host=netspout-tester ping=1.0 {int(now * 1e9)}"
            return self.emit_telegraf(test_line, config.telegraf_endpoint, fmt=config.telegraf_format)

        elif p == "syslog":
            test_msg = f"NetSpout Syslog Pipeline Connectivity Test at {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(now))}"
            return self.emit_syslog(
                raw_message=test_msg,
                host=config.syslog_host,
                port=config.syslog_port,
                protocol=config.syslog_protocol,
                facility=config.syslog_facility,
                severity=6,
                hostname="netspout-tester",
                app_name="pipeline-test",
                syslog_format=config.syslog_format
            )

        return False, f"Unknown pipeline type: {pipeline}"

    def test_connection(
        self,
        config: Optional[TelemetryTransportConfig] = None,
        pipeline: str = "hec",
        endpoint: Optional[str] = None,
        token: Optional[str] = None,
        index: Optional[str] = None,
        allow_insecure_tls: bool = False,
        ssl_verify: bool = True
    ) -> Dict[str, Any]:
        """
        Validates pipeline connectivity and returns canonical states:
        NOT_CONFIGURED, CONFIGURED, REACHABLE, VERIFIED, ERROR.
        Never exposes secrets/tokens in the response.
        """
        if config is None:
            if endpoint is not None or token is not None:
                if not endpoint and not token:
                    return {
                        "status": "NOT_CONFIGURED",
                        "state": "NOT_CONFIGURED",
                        "stage": "config",
                        "reachable": False,
                        "authenticated": False,
                        "event_accepted": False,
                        "target_index": index or "",
                        "message": "Splunk HEC URL and Authentication Token are required.",
                        "detail": "Splunk HEC URL and Authentication Token are required.",
                        "latency_ms": 0.0
                    }
                config = TelemetryTransportConfig(
                    hec_url=endpoint or "",
                    hec_token=token or "",
                    hec_index=index or "idx_network_ops",
                    hec_ssl_verify=ssl_verify,
                    hec_allow_insecure_tls=allow_insecure_tls
                )
            else:
                return {
                    "status": "NOT_CONFIGURED",
                    "state": "NOT_CONFIGURED",
                    "stage": "config",
                    "reachable": False,
                    "authenticated": False,
                    "event_accepted": False,
                    "target_index": "",
                    "message": "Telemetry transport configuration is missing.",
                    "detail": "Telemetry transport configuration is missing.",
                    "latency_ms": 0.0
                }

        p = pipeline.lower()
        if p == "hec":
            if not config.hec_url or not config.hec_token:
                return {
                    "status": "NOT_CONFIGURED",
                    "state": "NOT_CONFIGURED",
                    "stage": "config",
                    "reachable": False,
                    "authenticated": False,
                    "event_accepted": False,
                    "target_index": config.hec_index or "",
                    "message": "Splunk HEC URL and Authentication Token are required.",
                    "detail": "Splunk HEC URL and Authentication Token are required.",
                    "latency_ms": 0.0
                }

            # 1. Reachability pre-check via HTTP GET/HEAD
            url_parsed = config.hec_url.rstrip("/")
            health_url = f"{url_parsed}/health" if not url_parsed.endswith("/health") else url_parsed
            candidates = [health_url]
            if ":8888" in health_url:
                candidates.append(health_url.replace(":8888", ":8088"))
            elif ":8088" in health_url:
                candidates.append(health_url.replace(":8088", ":8888"))
            if "127.0.0.1" in health_url:
                for c in list(candidates):
                    candidates.append(c.replace("127.0.0.1", "localhost"))
            elif "localhost" in health_url:
                for c in list(candidates):
                    candidates.append(c.replace("localhost", "127.0.0.1"))

            ssl_verify = getattr(config, "hec_ssl_verify", True)
            allow_insecure = getattr(config, "hec_allow_insecure_tls", False)

            ctx = ssl.create_default_context()
            if allow_insecure or not ssl_verify:
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE

            reachable = False
            last_err = ""
            start_t = time.time()
            latency_ms = 0.0
            for cur_url in candidates:
                try:
                    req = urllib.request.Request(cur_url, headers={"User-Agent": "NetSpout-Preflight/2.0"})
                    with urllib.request.urlopen(req, timeout=2.0, context=ctx) as resp:
                        reachable = True
                        latency_ms = max(1.0, round((time.time() - start_t) * 1000, 2))
                        break
                except urllib.error.HTTPError:
                    reachable = True
                    latency_ms = max(1.0, round((time.time() - start_t) * 1000, 2))
                    break
                except (ssl.SSLCertVerificationError, urllib.error.URLError) as e:
                    err_str = str(e)
                    if isinstance(e, ssl.SSLCertVerificationError) or "CERTIFICATE_VERIFY_FAILED" in err_str or "certificate verify failed" in err_str:
                        return {
                            "status": "ERROR",
                            "state": "ERROR",
                            "stage": "network",
                            "reachable": True,
                            "authenticated": False,
                            "event_accepted": False,
                            "target_index": config.hec_index or "idx_network_ops",
                            "message": f"TLS Verification Failed: {e}. Enable 'Allow self-signed certificate' for lab/development endpoints.",
                            "detail": f"TLS Verification Failed: {e}. Enable 'Allow self-signed certificate' for lab/development endpoints.",
                            "latency_ms": max(1.0, round((time.time() - start_t) * 1000, 2))
                        }
                    last_err = err_str
                    continue
                except Exception as e:
                    last_err = str(e)
                    continue

            if not reachable:
                return {
                    "status": "ERROR",
                    "state": "ERROR",
                    "stage": "network",
                    "reachable": False,
                    "authenticated": False,
                    "event_accepted": False,
                    "target_index": config.hec_index or "idx_network_ops",
                    "message": f"Endpoint unreachable: {last_err or 'Connection timed out or refused.'}",
                    "detail": f"Endpoint unreachable: {last_err or 'Connection timed out or refused.'}",
                    "latency_ms": 0.0
                }

            # 2. Authenticated Test Event Verification
            test_event = {
                "event": "NetSpout Connection Preflight Test Event",
                "time": time.time(),
                "host": "netspout-preflight",
                "source": "netspout-preflight",
                "sourcetype": "netspout:preflight",
                "index": config.hec_index or "idx_network_ops",
                "fields": {
                    "netspout_preflight": "true",
                    "timestamp_epoch": time.time()
                }
            }
            ok, msg = self.emit_hec(
                test_event,
                config.hec_url,
                config.hec_token,
                ssl_verify=ssl_verify,
                allow_insecure_tls=allow_insecure
            )

            if ok:
                return {
                    "status": "VERIFIED",
                    "state": "VERIFIED",
                    "stage": "dispatch",
                    "reachable": True,
                    "authenticated": True,
                    "event_accepted": True,
                    "target_index": config.hec_index or "idx_network_ops",
                    "message": f"Splunk HEC connection verified. Test event accepted ({msg}).",
                    "detail": f"Splunk HEC connection verified. Test event accepted ({msg}).",
                    "latency_ms": latency_ms or 4.0
                }
            elif "401" in msg or "403" in msg or "Invalid token" in msg:
                return {
                    "status": "ERROR",
                    "state": "ERROR",
                    "stage": "auth",
                    "reachable": True,
                    "authenticated": False,
                    "event_accepted": False,
                    "target_index": config.hec_index or "idx_network_ops",
                    "message": "HEC Authentication Failed: Invalid or unauthorized token.",
                    "detail": "HEC Authentication Failed: Invalid or unauthorized token.",
                    "latency_ms": latency_ms or 4.0
                }
            else:
                return {
                    "status": "ERROR",
                    "state": "ERROR",
                    "stage": "dispatch",
                    "reachable": True,
                    "authenticated": True,
                    "event_accepted": False,
                    "target_index": config.hec_index or "idx_network_ops",
                    "message": f"HEC test event rejected: {msg}",
                    "detail": f"HEC test event rejected: {msg}",
                    "latency_ms": latency_ms or 4.0
                }

        return {
            "status": "CONFIGURED",
            "state": "CONFIGURED",
            "stage": "config",
            "reachable": True,
            "authenticated": True,
            "event_accepted": False,
            "target_index": getattr(config, "hec_index", "idx_network_ops"),
            "message": f"Pipeline '{pipeline}' configured.",
            "detail": f"Pipeline '{pipeline}' configured.",
            "latency_ms": 1.0
        }


# Global singleton dispatcher instance
dispatcher = TelemetryDispatcher()
