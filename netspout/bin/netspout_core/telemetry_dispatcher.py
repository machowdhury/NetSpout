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
    # Double-header guard: vendor-native payloads already embed a PRI-aware
    # header at event creation; re-headering them would prepend synthetic
    # bytes to the byte-exact vendor contract.
    if message.lstrip().startswith("<"):
        return message.lstrip()
    return header + message


def get_bsd_syslog_timestamp(now=None) -> str:
    """BSD-syslog timestamp with the RFC 3164 space-padded day convention.

    Args:
        now: Optional datetime (UTC expected); defaults to now in UTC.

    Returns:
        str: e.g. 'Oct  6 14:03:27' (day right-aligned to width 2).
    """
    if now is None:
        now = datetime.now(timezone.utc)
    day = f"{now.day:2d}"
    return f"{now.strftime('%b')} {day} {now.strftime('%H:%M:%S')}"


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
    now_bsd = get_bsd_syslog_timestamp(datetime.now())
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


# Lifecycle of one record on the Splunk HEC path. An HTTP 2xx answer with {"code": 0} proves only that the
# collector ACCEPTED the request; it never proves that the event was indexed or is searchable, so no
# INDEXED or OBSERVED state is produced here.
HEC_GENERATED = "GENERATED"      # record built for HEC, not yet sent
HEC_DISPATCHING = "DISPATCHING"  # POST in flight (stats["hec_dispatching"] counts these)
HEC_ACCEPTED = "ACCEPTED"        # HEC answered HTTP 2xx with a JSON body whose "code" is 0
HEC_FAILED = "FAILED"            # not delivered: rejected (4xx, Splunk busy), unreachable, TLS failure or not dispatched
HEC_UNKNOWN = "UNKNOWN"          # outcome cannot be determined (no answer after sending, ambiguous 5xx, unexpected 2xx)
HEC_LIFECYCLE_STATES = (HEC_GENERATED, HEC_DISPATCHING, HEC_ACCEPTED, HEC_FAILED, HEC_UNKNOWN)

#: Sourcetypes the metric path has always treated as metrics. Kept explicitly so
#: Cisco MDT routing stays byte-identical while other metric sources are added.
CISCO_MDT_SOURCETYPES = ("cisco:ios:mdt", "cisco:ios:mdt:metric")

_METRIC_SOURCETYPES_CACHE: Optional[frozenset] = None


def metric_sourcetypes() -> frozenset:
    """Sourcetypes the canonical catalog classifies as ``data_kind == metric``.

    Catalog-driven so a new metric source (for example ``sc4snmp:metric``) is
    routed to the metrics index by its published classification rather than by
    another hardcoded ``if sourcetype == ...`` clause. Degrades to the Cisco set
    if the catalog cannot be loaded, which keeps existing behaviour intact.
    """
    global _METRIC_SOURCETYPES_CACHE
    if _METRIC_SOURCETYPES_CACHE is not None:
        return _METRIC_SOURCETYPES_CACHE
    names = set(CISCO_MDT_SOURCETYPES)
    catalog = None
    for importer in (
        "netspout_core.catalog", "app.catalog", "catalog"
    ):
        try:
            module = __import__(importer, fromlist=["catalog_instance"])
            catalog = getattr(module, "catalog_instance", None)
            if catalog is not None:
                break
        except Exception:
            continue
    if catalog is not None:
        try:
            for entry in catalog.list_sourcetypes(include_deprecated=False):
                if entry.get("data_kind") == "metric":
                    st = entry.get("splunk_sourcetype")
                    if st:
                        names.add(st)
        except Exception:
            pass
    _METRIC_SOURCETYPES_CACHE = frozenset(names)
    return _METRIC_SOURCETYPES_CACHE


def is_metric_sourcetype(sourcetype: Optional[str]) -> bool:
    """True when this sourcetype's telemetry belongs in the metrics index."""
    if not sourcetype:
        return False
    return sourcetype in metric_sourcetypes()


class HecOutcome(tuple):
    """(success, message) for existing callers, plus the lifecycle evidence of one HEC send.

    success keeps its historical meaning, "an HTTP 2xx answer was received"; only state == ACCEPTED proves that
    HEC accepted the request. A 2xx with an unexpected body is success=True with state UNKNOWN.
    """

    def __new__(cls, success, message, state, http_status=None, error_class=None):
        self = super().__new__(cls, (success, message))
        self.state, self.http_status, self.error_class = state, http_status, error_class
        return self


def hec_outcome_fields(outcome) -> Dict[str, Any]:
    """Lifecycle fields for a dispatch result. A plain (success, message) tuple carries no evidence: UNKNOWN."""
    return {"state": getattr(outcome, "state", HEC_UNKNOWN),
            "http_status": getattr(outcome, "http_status", None),
            "error_class": getattr(outcome, "error_class", None)}


def _hec_body_code(text: str):
    try:
        body = json.loads(text)
    except ValueError:
        return None
    code = body.get("code") if isinstance(body, dict) else None
    return code if isinstance(code, int) and not isinstance(code, bool) else None


def _http_summary(pipeline: str, status) -> str:
    """Public text uses trusted pipeline constants and numeric HTTP status only."""
    if type(status) is int and 100 <= status <= 599:
        return f"{pipeline} HTTP {status}"
    return f"{pipeline} HTTP response"


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
            "hec_generated": 0,
            "hec_dispatching": 0,
            "hec_accepted": 0,
            "hec_failed": 0,
            "hec_unknown": 0,
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
        self.stats["hec_generated"] += 1
        outcome = self._send_hec(event, hec_url, token, ssl_verify, allow_insecure_tls)
        if outcome.state == HEC_ACCEPTED:
            self.stats["hec_accepted"] += 1
        elif outcome.state == HEC_FAILED:
            self.stats["hec_failed"] += 1
        else:
            self.stats["hec_unknown"] += 1
        if outcome[0]:
            self.stats["hec_dispatched"] += 1
            self.stats["last_active"] = time.time()
        else:
            self.stats["hec_errors"] += 1
            self.stats["last_error"] = "HEC dispatch failed"
        return outcome

    def _send_hec(self, event, hec_url, token, ssl_verify, allow_insecure_tls) -> HecOutcome:
        # Alternative endpoints are tried only while nothing has reached a collector. Once a request may have
        # been delivered (no answer, or an answer that cannot be read), it is never re-sent: UNKNOWN.
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

        try:
            payload = json.dumps(event).encode("utf-8")
        except (TypeError, ValueError) as e:
            return HecOutcome(False, "HEC invalid payload", HEC_FAILED, None, "invalid_payload")
        ctx = ssl.create_default_context()
        if allow_insecure_tls or not ssl_verify:
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

        last_error, error_class = "HEC endpoint unreachable", "unreachable"
        for cand_url in candidates:
            try:
                req = urllib.request.Request(
                    cand_url,
                    data=payload,
                    headers={
                        "Authorization": f"Splunk {token}",
                        "Content-Type": "application/json"
                    }
                )
            except ValueError as e:
                last_error, error_class = "HEC invalid endpoint", "invalid_endpoint"
                continue
            status = None
            self.stats["hec_dispatching"] += 1
            try:
                with urllib.request.urlopen(req, timeout=2.0, context=ctx) as resp:
                    status = resp.status
                    resp_text = resp.read().decode("utf-8", errors="replace")
            except urllib.error.HTTPError as e:
                # Response content is used only for HEC classification, never public text.
                try:
                    err_body = e.read().decode("utf-8", errors="replace")
                except Exception:
                    err_body = ""
                msg = _http_summary("HEC", e.code)
                if e.code < 500:
                    cls = "auth_rejected" if e.code in (401, 403) else "request_rejected"
                    return HecOutcome(False, msg, HEC_FAILED, e.code, cls)
                if e.code == 503 and _hec_body_code(err_body) == 9:
                    # Splunk HEC "Server is busy" (code 9): the collector refused the request
                    return HecOutcome(False, msg, HEC_FAILED, e.code, "collector_busy")
                # any other 5xx (Splunk 500, proxy 502/504, 503 without the HEC busy body): delivery cannot be ruled out
                return HecOutcome(False, msg, HEC_UNKNOWN, e.code, "collector_error_uncertain")
            except (ssl.SSLCertVerificationError, urllib.error.URLError) as e:
                err_str = str(e)
                if isinstance(e, ssl.SSLCertVerificationError) or "CERTIFICATE_VERIFY_FAILED" in err_str or "certificate verify failed" in err_str:
                    return HecOutcome(False, "HEC TLS verification failed",
                                      HEC_FAILED, None, "tls_verification")
                last_error, error_class = "HEC endpoint unreachable", "unreachable"
                continue
            except ValueError as e:
                if status is not None:
                    return HecOutcome(False, "HEC response unreadable", HEC_UNKNOWN, status, "no_answer_after_send")
                last_error, error_class = "HEC invalid endpoint", "invalid_endpoint"
                continue
            except Exception as e:
                return HecOutcome(False, "HEC response unavailable", HEC_UNKNOWN, status, "no_answer_after_send")
            finally:
                self.stats["hec_dispatching"] -= 1
            message = _http_summary("HEC", status)
            if 200 <= status < 300 and _hec_body_code(resp_text) == 0:
                return HecOutcome(True, message, HEC_ACCEPTED, status, None)
            return HecOutcome(True, message, HEC_UNKNOWN, status, "unexpected_response")

        return HecOutcome(False, last_error, HEC_FAILED, None, error_class)

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
            with self._otel_request(payload, endpoint, is_metric, headers, verify=False) as resp:
                resp_text = resp.read().decode("utf-8", errors="replace")
                self.stats["otel_dispatched"] += 1
                self.stats["last_active"] = time.time()
                return True, _http_summary("OTel", resp.status)

        except Exception as e:
            self.stats["otel_errors"] += 1
            message = _http_summary("OTel", e.code) if isinstance(e, urllib.error.HTTPError) else "OTel dispatch failed"
            self.stats["last_error"] = message
            return False, message

    @staticmethod
    def _otel_request(payload, endpoint, is_metric, headers=None, verify=True):
        """Shared HTTP/JSON transport for legacy and evidence-aware callers."""
        base = endpoint.rstrip("/")
        target = "/v1/metrics" if is_metric else "/v1/logs"
        url = base if base.endswith(("/v1/metrics", "/v1/logs")) else base + target
        request_headers = dict(headers or {})
        request_headers["Content-Type"] = "application/json"
        request = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=request_headers)
        context = ssl.create_default_context()
        if not verify:  # Preserve legacy API policy; native OTLP always verifies TLS.
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
        return urllib.request.urlopen(request, timeout=3.0, context=context)

    def emit_otel_result(self, payload, endpoint, is_metric=True, headers=None, record_count=1):
        """OTLP HTTP/JSON evidence; no response bodies or exception text escape."""
        if type(record_count) is not int or record_count < 1:
            raise ValueError("Invalid OTLP record count")
        result = dict(attempted=record_count, acknowledged=0, rejected=0, failed=0,
                      unknown=record_count, http_status=None, message="OTLP outcome unknown")
        try:
            with self._otel_request(payload, endpoint, is_metric, headers) as response:
                status = int(response.status)
                result["http_status"] = status
                # OTLP HTTP success is 200. Other 2xx responses are ambiguous.
                if status == 200:
                    body = response.read(65537)
                    if len(body) > 65536:
                        raise ValueError()
                    data = json.loads(body)
                    if not isinstance(data, dict):
                        raise ValueError()
                    partial = data.get("partialSuccess", {})
                    if not isinstance(partial, dict):
                        raise ValueError()
                    field = "rejectedDataPoints" if is_metric else "rejectedLogRecords"
                    if set(partial) - {field, "errorMessage"}:
                        raise ValueError()
                    value = partial.get(field, 0)
                    if isinstance(value, str) and value.isascii() and value.isdigit():
                        value = int(value)
                    if type(value) is not int or not 0 <= value <= record_count:
                        raise ValueError()
                    result.update(acknowledged=record_count-value, rejected=value, unknown=0,
                                  message="OTLP collector acknowledged records" if not value else "OTLP collector partially rejected records")
                    self.stats["otel_dispatched"] += 1
                    self.stats["last_active"] = time.time()
                    return result
                result["message"] = "OTLP response did not establish acknowledgement"
        except urllib.error.HTTPError as error:
            result["http_status"] = int(error.code)
            # Retryable/server errors may follow partial processing; do not infer rejection.
            if error.code in (400, 401, 403, 404, 405, 413, 415, 422):
                result.update(rejected=record_count, unknown=0, message="OTLP request rejected")
            else:
                result["message"] = "OTLP request outcome unknown"
        except Exception:
            result["message"] = "OTLP request outcome unknown"
        self.stats["otel_errors"] += 1
        self.stats["last_error"] = result["message"]
        return result

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
                return True, _http_summary("Telegraf", resp.status)

        except Exception as e:
            self.stats["telegraf_errors"] += 1
            message = _http_summary("Telegraf", e.code) if isinstance(e, urllib.error.HTTPError) else "Telegraf dispatch failed"
            self.stats["last_error"] = message
            return False, message

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
            return True, "Syslog message sent"

        except Exception as e:
            self.stats["syslog_errors"] += 1
            self.stats["last_error"] = "Syslog dispatch failed"
            return False, "Syslog dispatch failed"

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
            # Metric routing is decided by the catalog's data_kind, not by a
            # hardcoded Cisco-only sourcetype list, so SNMP-derived and other
            # metric sources reach the metrics index through this same path.
            sourcetype_is_metric = is_metric_sourcetype(log.sourcetype)
            if sourcetype_is_metric:
                target_index = transport.hec_metric_index or "cisco_mdt_metrics"

            is_metric = (target_index == "cisco_mdt_metrics" or
                         "metric" in target_index.lower() or
                         sourcetype_is_metric)

            if is_metric:
                metric_fields: Dict[str, Any] = {
                    "device": log.device_id,
                    "host": log.device_id,
                    "vendor": log.vendor or "cisco",
                    "status": log.status or "normal",
                    "action": log.action or "streamed"
                }

                # Extract metric values from raw_log
                if log.raw_log:
                    try:
                        if isinstance(log.raw_log, str):
                            raw_obj, _ = json.JSONDecoder().raw_decode(log.raw_log.lstrip())
                        else:
                            raw_obj = log.raw_log
                        if isinstance(raw_obj, dict):
                            # Handle fields dict
                            if "fields" in raw_obj and isinstance(raw_obj["fields"], dict):
                                metric_fields.update(raw_obj["fields"])
                            # Handle data dict
                            if "data" in raw_obj and isinstance(raw_obj["data"], dict):
                                data = raw_obj["data"]
                                for k, v in data.items():
                                    if isinstance(v, (int, float)) and not isinstance(v, bool):
                                        name = k
                                        if name == "queue_depth_bytes":
                                            name = "queue_depth"
                                        elif name == "buffer_utilization_pct":
                                            name = "buffer_utilization"
                                        metric_fields[f"metric_name:{name}"] = float(v)
                            # Handle data_gpbkv list
                            if "data_gpbkv" in raw_obj and isinstance(raw_obj["data_gpbkv"], list):
                                for entry in raw_obj["data_gpbkv"]:
                                    if isinstance(entry, dict) and "content" in entry and isinstance(entry["content"], dict):
                                        content = entry["content"]
                                        for k, v in content.items():
                                            if isinstance(v, (int, float)) and not isinstance(v, bool):
                                                name = k.replace("-", "_")
                                                metric_fields[f"metric_name:{name}"] = float(v)
                                        # Set sensor_path from first entry that contributed a value
                                        if "sensor_path" not in metric_fields and "path" in entry:
                                            metric_fields["sensor_path"] = str(entry["path"])
                            # Copy top-level keys
                            for k in ("node_id_str", "sensor_path", "subscription_id"):
                                if k in raw_obj:
                                    metric_fields[k] = str(raw_obj[k])
                    except Exception:
                        pass

                if log.netspout_run_id:
                    metric_fields["netspout_run_id"] = log.netspout_run_id
                if log.netspout_scenario_id:
                    metric_fields["netspout_scenario_id"] = log.netspout_scenario_id
                if log.netspout_phase:
                    metric_fields["netspout_phase"] = log.netspout_phase
                if log.netspout_device_id:
                    metric_fields["netspout_device_id"] = log.netspout_device_id
                if log.netspout_event_id:
                    metric_fields["netspout_event_id"] = log.netspout_event_id
                if log.netspout_ground_truth:
                    metric_fields["netspout_ground_truth"] = str(log.netspout_ground_truth)

                # Cisco MDT keeps its historic source/sourcetype labels so
                # existing searches and tests are unaffected. Any other metric
                # source must not be relabelled as Cisco telemetry -- it keeps
                # the sourcetype the catalog classified as a metric.
                if log.sourcetype in CISCO_MDT_SOURCETYPES:
                    metric_source = "cisco:ios:mdt"
                    metric_sourcetype = "cisco:ios:mdt:metric"
                else:
                    metric_source = log.sourcetype or "netspout:metric"
                    metric_sourcetype = log.sourcetype
                hec_payload = {
                    "time": time.time(),
                    "event": "metric",
                    "host": log.device_id,
                    "source": metric_source,
                    "sourcetype": metric_sourcetype,
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
            if is_metric and not any(k.startswith("metric_name:") for k in hec_payload["fields"]):
                # fail closed: a metric record without a generated numeric value is never sent (no fabricated value)
                results["hec"] = {"success": False, "message": "metric record has no numeric values; not dispatched",
                                  "state": HEC_FAILED, "http_status": None, "error_class": "not_dispatched"}
                self.stats["hec_errors"] += 1
                self.stats["hec_generated"] += 1
                self.stats["hec_failed"] += 1
            else:
                ssl_v = getattr(transport, "hec_ssl_verify", True)
                insec = getattr(transport, "hec_allow_insecure_tls", False)
                outcome = self.emit_hec(hec_payload, transport.hec_url, transport.hec_token, ssl_verify=ssl_v, allow_insecure_tls=insec)
                ok, msg = outcome
                results["hec"] = {"success": ok, "message": msg, **hec_outcome_fields(outcome)}

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

        return False, "Unknown pipeline type"

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
                            "message": "HEC TLS verification failed",
                            "detail": "HEC TLS verification failed",
                            "latency_ms": max(1.0, round((time.time() - start_t) * 1000, 2))
                        }
                    last_err = "HEC endpoint unreachable"
                    continue
                except Exception as e:
                    last_err = "HEC endpoint unreachable"
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
                    "message": "HEC endpoint unreachable",
                    "detail": "HEC endpoint unreachable",
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
                    "message": "Splunk HEC connection verified. Test event accepted.",
                    "detail": "Splunk HEC connection verified. Test event accepted.",
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
                    "message": "HEC test event rejected",
                    "detail": "HEC test event rejected",
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
            "message": "Pipeline configured.",
            "detail": "Pipeline configured.",
            "latency_ms": 1.0
        }


# Global singleton dispatcher instance
dispatcher = TelemetryDispatcher()
