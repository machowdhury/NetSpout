# =========================================================================
# AUTO-GENERATED PACKAGED COPY — DO NOT EDIT DIRECTLY!
# Authoritative Source of Truth: src/netspout_core/collector_evidence.py
# Re-generate using: python3 scripts/sync_core.py
# =========================================================================
"""
NetSpout Collector Evidence Adapter.
Interacts with the containerized GoFlow2 + Forwarder collector tier
to verify COLLECTOR_OBSERVED evidence state independently of Splunk ingestion.
Conforms to Gate 11C Architecture Phase 15 and Gate 11D Productization.
"""

import json
import logging
import re
import socket
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional, Tuple, Union

from netspout_core.models import (
    CollectorDetailedHealth,
    CollectorHealthState,
    NativeFlowConfig,
    resolve_native_flow_config
)

logger = logging.getLogger("netspout.collector.evidence")


class CollectorEvidenceAdapter:
    """
    Independent evidence adapter for the external flow collector tier.
    Provides verifiable proof of collector health, packet reception,
    template learning, and record decoding before Splunk indexing.
    """
    def __init__(
        self,
        goflow_metrics_url: str = "http://127.0.0.1:8080/metrics",
        forwarder_status_url: str = "http://127.0.0.1:8082",
        splunk_hec_url: str = "https://127.0.0.1:8888/services/collector/health"
    ):
        self.goflow_metrics_url = goflow_metrics_url
        self.forwarder_status_url = forwarder_status_url.rstrip("/")
        self.splunk_hec_url = splunk_hec_url

    def get_prometheus_metrics(self, timeout: float = 3.0) -> Dict[str, Any]:
        """
        Scrapes and parses GoFlow2 Prometheus metrics from :8080/metrics.
        Extracts packet totals, byte totals, records decoded, and decode errors.
        """
        metrics = {
            "packets_total": 0,
            "bytes_total": 0,
            "records_total": 0,
            "templates_total": 0,
            "errors_total": 0,
            "decoding_time_sec": 0.0,
            "raw_metric_count": 0
        }
        try:
            req = urllib.request.Request(self.goflow_metrics_url)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if resp.status == 200:
                    for line in resp:
                        text = line.decode("utf-8", errors="replace").strip()
                        if not text or text.startswith("#"):
                            continue
                        metrics["raw_metric_count"] += 1
                        
                        # Packets total
                        if "goflow2_flow_traffic_packets_total" in text:
                            parts = text.rsplit(" ", 1)
                            if len(parts) == 2:
                                try:
                                    metrics["packets_total"] += int(float(parts[1]))
                                except ValueError:
                                    pass

                        # Bytes total
                        elif "goflow2_flow_traffic_bytes_total" in text:
                            parts = text.rsplit(" ", 1)
                            if len(parts) == 2:
                                try:
                                    metrics["bytes_total"] += int(float(parts[1]))
                                except ValueError:
                                    pass

                        # Flowset records total
                        elif "goflow2_flow_process_nf_flowset_records_total" in text and 'type="DataFlowSet"' in text:
                            parts = text.rsplit(" ", 1)
                            if len(parts) == 2:
                                try:
                                    metrics["records_total"] += int(float(parts[1]))
                                except ValueError:
                                    pass

                        # Templates total
                        elif "goflow2_flow_process_nf_templates_total" in text:
                            parts = text.rsplit(" ", 1)
                            if len(parts) == 2:
                                try:
                                    metrics["templates_total"] += int(float(parts[1]))
                                except ValueError:
                                    pass

                        # Errors total
                        elif "goflow2_flow_process_nf_errors_total" in text or "decode_errors" in text:
                            parts = text.rsplit(" ", 1)
                            if len(parts) == 2:
                                try:
                                    metrics["errors_total"] += int(float(parts[1]))
                                except ValueError:
                                    pass

                        # Avg decoding time
                        elif "goflow2_flow_decoding_time_seconds_sum" in text:
                            parts = text.rsplit(" ", 1)
                            if len(parts) == 2:
                                try:
                                    metrics["decoding_time_sec"] = float(parts[1])
                                except ValueError:
                                    pass
        except Exception as exc:
            metrics["error"] = str(exc)

        return metrics

    def check_health(self, timeout: float = 3.0) -> Tuple[bool, Dict[str, Any]]:
        """
        Verifies health of both GoFlow2 collector and Forwarder service.
        """
        details: Dict[str, Any] = {
            "goflow_metrics": False,
            "forwarder_status": False,
            "flows_read": 0,
            "flows_forwarded": 0,
            "forward_failures": 0,
            "last_error": None
        }

        # 1. Probe GoFlow2
        try:
            req = urllib.request.Request(self.goflow_metrics_url)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if resp.status == 200:
                    details["goflow_metrics"] = True
        except Exception as exc:
            details["goflow_error"] = str(exc)

        # 2. Probe Forwarder
        try:
            req = urllib.request.Request(f"{self.forwarder_status_url}/status")
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    details["forwarder_status"] = True
                    details["flows_read"] = data.get("flows_read", 0)
                    details["flows_forwarded"] = data.get("flows_forwarded", 0)
                    details["forward_failures"] = data.get("forward_failures", 0)
                    details["last_error"] = data.get("last_error")
                    details["simulate_splunk_failure"] = data.get("simulate_splunk_failure", False)
        except Exception as exc:
            details["forwarder_error"] = str(exc)

        overall_healthy = details["goflow_metrics"] and details["forwarder_status"]
        return overall_healthy, details

    def get_detailed_health(self, timeout: float = 3.0) -> CollectorDetailedHealth:
        """
        Constructs canonical 8-state health representation:
        STOPPED, STARTING, HEALTHY, DEGRADED, UNREACHABLE, RECEIVING, FORWARDER_BLOCKED, SPLUNK_UNAVAILABLE.
        """
        health = CollectorDetailedHealth()
        
        # 1. Scrape Prometheus
        prom = self.get_prometheus_metrics(timeout=timeout)
        goflow_ok = "error" not in prom and prom.get("raw_metric_count", 0) > 0
        health.collector_process = goflow_ok
        health.packets_received_total = prom.get("packets_total", 0)
        health.records_decoded_total = prom.get("records_total", 0)
        health.decode_errors_total = prom.get("errors_total", 0)

        # 2. Scrape Forwarder
        fwd_ok = False
        fwd_data: Dict[str, Any] = {}
        try:
            req = urllib.request.Request(f"{self.forwarder_status_url}/status")
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if resp.status == 200:
                    fwd_data = json.loads(resp.read().decode("utf-8"))
                    fwd_ok = True
                    health.forwarder_healthy = True
                    health.flows_forwarded_total = fwd_data.get("flows_forwarded", 0)
                    health.hec_failures_total = fwd_data.get("forward_failures", 0)
                    health.last_packet_timestamp = fwd_data.get("last_forward_timestamp")
        except Exception as exc:
            fwd_data["error"] = str(exc)

        # 3. Check Splunk HEC connectivity
        splunk_ok = False
        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            req = urllib.request.Request(self.splunk_hec_url)
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
                if resp.status in (200, 400, 401):
                    splunk_ok = True
                    health.hec_connectivity = True
        except Exception:
            health.hec_connectivity = False

        health.details = {
            "goflow": prom,
            "forwarder": fwd_data,
            "splunk_hec_reachable": splunk_ok
        }

        # 4. Resolve 8-state canonical classification
        if not goflow_ok and not fwd_ok:
            health.state = CollectorHealthState.STOPPED
        elif not goflow_ok or not fwd_ok:
            health.state = CollectorHealthState.DEGRADED
        elif fwd_data.get("simulate_splunk_failure", False) or (fwd_ok and not splunk_ok and health.hec_failures_total > 0):
            health.state = CollectorHealthState.SPLUNK_UNAVAILABLE
        elif fwd_data.get("forward_failures", 0) > 0 and fwd_data.get("flows_forwarded", 0) == 0:
            health.state = CollectorHealthState.FORWARDER_BLOCKED
        elif prom.get("errors_total", 0) > 0:
            health.state = CollectorHealthState.DEGRADED
        elif prom.get("packets_total", 0) > 0:
            health.state = CollectorHealthState.RECEIVING
        else:
            health.state = CollectorHealthState.HEALTHY

        health.udp_listeners_active = goflow_ok
        return health

    def run_preflight_check(self, config: Optional[NativeFlowConfig] = None) -> Dict[str, Any]:
        """
        Executes a pre-flight readiness audit across the telemetry pipeline.
        Audits collector host, UDP socket binding feasibility, forwarder health,
        and Splunk HEC reachability without falsely claiming UDP transmission certainty.
        """
        cfg = config or resolve_native_flow_config()
        results: Dict[str, Any] = {
            "overall_ready": False,
            "checks": {},
            "timestamp": time.time()
        }

        # Check 1: Collector Host Configuration
        results["checks"]["collector_host"] = {
            "host": cfg.collector_host,
            "valid": bool(cfg.collector_host),
            "status": "PASS" if cfg.collector_host else "FAIL"
        }

        # Check 2: UDP Socket Feasibility (Connectionless note included)
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(1.0)
            sock.close()
            results["checks"]["udp_socket"] = {
                "status": "PASS",
                "message": f"OS UDP socket initialized successfully for target port {cfg.netflow_port}/{cfg.ipfix_port}",
                "note": "Standard UDP is connectionless; socket creation confirms local stack capability, not remote listener state."
            }
        except Exception as exc:
            results["checks"]["udp_socket"] = {
                "status": "FAIL",
                "message": f"UDP socket initialization failed: {exc}"
            }

        # Check 3: Collector Metrics API Reachability
        prom = self.get_prometheus_metrics(timeout=2.0)
        goflow_up = "error" not in prom and prom.get("raw_metric_count", 0) > 0
        results["checks"]["collector_metrics"] = {
            "status": "PASS" if goflow_up else "FAIL",
            "url": self.goflow_metrics_url,
            "packets_received_total": prom.get("packets_total", 0)
        }

        # Check 4: Forwarder Health API
        fwd_up = False
        try:
            req = urllib.request.Request(f"{self.forwarder_status_url}/status")
            with urllib.request.urlopen(req, timeout=2.0) as resp:
                fwd_up = (resp.status == 200)
        except Exception:
            pass
        results["checks"]["forwarder_status"] = {
            "status": "PASS" if fwd_up else "FAIL",
            "url": f"{self.forwarder_status_url}/status"
        }

        # Check 5: Splunk HEC Reachability
        hec_up = False
        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            req = urllib.request.Request(self.splunk_hec_url)
            with urllib.request.urlopen(req, timeout=2.0, context=ctx) as resp:
                hec_up = (resp.status in (200, 400, 401))
        except Exception:
            pass
        results["checks"]["splunk_hec"] = {
            "status": "PASS" if hec_up else "FAIL",
            "url": self.splunk_hec_url,
            "index": cfg.splunk_index,
            "sourcetype": cfg.splunk_sourcetype
        }

        results["overall_ready"] = (
            results["checks"]["collector_host"]["status"] == "PASS" and
            results["checks"]["udp_socket"]["status"] == "PASS" and
            results["checks"]["collector_metrics"]["status"] == "PASS" and
            results["checks"]["forwarder_status"]["status"] == "PASS" and
            results["checks"]["splunk_hec"]["status"] == "PASS"
        )
        return results

    @staticmethod
    def diagnose_failure(stage: str, details: Optional[Dict[str, Any]] = None) -> str:
        """
        Translates raw telemetry errors into clear, actionable troubleshooting diagnostics.
        """
        d = details or {}
        st = stage.upper()
        if st in ("GENERATION_FAILED", "NETSPOUT_SEND_FAILED"):
            err = d.get("error", "Socket transmission error")
            return f"NetSpout generated records but UDP transmission failed: {err}"
        if st in ("COLLECTOR_TIMEOUT", "NO_COLLECTOR_EVIDENCE"):
            return "UDP datagrams were sent by NetSpout, but no collector evidence was observed (check listener port and firewall)."
        if st in ("DECODE_FAILED", "TEMPLATE_MISSING"):
            return "Collector received UDP datagrams but decoding failed (template missing or incompatible field layout)."
        if st in ("FORWARDER_FAILED", "SPLUNK_UNAVAILABLE"):
            return "Collector decoded records successfully, but the forwarder could not deliver events to Splunk HEC."
        if st in ("SPLUNK_INCOMPLETE", "MISSING_EVIDENCE"):
            return "Splunk received flow records, but expected scenario correlation criteria were incomplete."
        if st in ("VALIDATION_FAILED", "SEMANTIC_FAILURE"):
            return "All telemetry arrived at destination, but semantic scenario validation rules failed."
        return f"Pipeline failure at stage '{stage}': {d.get('error', 'Unspecified error')}"

    @staticmethod
    def build_investigation_query(
        observation_domain_id: int,
        exporter_ip: Optional[str] = None,
        protocol: Optional[str] = None,
        time_window_min: int = 5
    ) -> Dict[str, str]:
        """
        Generates copyable, dynamic SPL queries with bounded time ranges and field extractions.
        """
        base_search = (
            f"search index=idx_network_ops sourcetype=netflow:collector "
            f"(observation_domain_id={observation_domain_id} OR ObservationDomainID={observation_domain_id} OR ObservationDomainId={observation_domain_id})"
        )
        if exporter_ip:
            base_search += f" (host=\"*{exporter_ip}*\" OR sampler_address=\"*{exporter_ip}*\" OR SamplerAddress=\"*{exporter_ip}*\")"

        raw_events_spl = f"{base_search} | spath"
        table_spl = f"{base_search} | spath | table _time src_addr dst_addr src_port dst_port proto bytes packets in_if out_if observation_domain_id"
        stats_spl = f"{base_search} | spath | stats count as total_flows sum(bytes) as total_bytes sum(packets) as total_packets by src_addr dst_addr src_port dst_port proto"

        return {
            "table_spl": table_spl,
            "raw_events_spl": raw_events_spl,
            "stats_spl": stats_spl
        }

    def get_recent_flows(self, timeout: float = 3.0) -> List[Dict[str, Any]]:
        """Retrieves recent decoded flows from the collector forwarder."""
        try:
            req = urllib.request.Request(f"{self.forwarder_status_url}/flows")
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if resp.status == 200:
                    return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            logger.warning(f"Failed to fetch recent flows from collector: {exc}")
        return []

    def find_matching_flow(
        self,
        observation_domain_id: int,
        src_ip: Optional[str] = None,
        dest_ip: Optional[str] = None,
        src_port: Optional[int] = None,
        dest_port: Optional[int] = None,
        min_bytes: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Finds a decoded flow record matching specific session parameters
        directly from collector memory, proving COLLECTOR_OBSERVED state.
        """
        flows = self.get_recent_flows()
        for flow in flows:
            if flow.get("observation_domain_id") != observation_domain_id:
                continue
            if src_ip and flow.get("src_addr") != src_ip:
                continue
            if dest_ip and flow.get("dst_addr") != dest_ip:
                continue
            if src_port is not None and flow.get("src_port") != src_port:
                continue
            if dest_port is not None and flow.get("dst_port") != dest_port:
                continue
            if min_bytes is not None and flow.get("bytes", 0) < min_bytes:
                continue
            return flow
        return None

    def clear_buffer(self, timeout: float = 3.0) -> bool:
        """Clears recent flows buffer on the collector forwarder."""
        try:
            req = urllib.request.Request(f"{self.forwarder_status_url}/clear", data=b"", method="POST")
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.status == 200
        except Exception as exc:
            logger.warning(f"Failed to clear collector buffer: {exc}")
            return False

    def simulate_splunk_failure(self, fail: bool = True, timeout: float = 3.0) -> bool:
        """Toggles simulated Splunk failure mode in the forwarder."""
        try:
            body = json.dumps({"fail": fail}).encode("utf-8")
            req = urllib.request.Request(
                f"{self.forwarder_status_url}/simulate_splunk_failure",
                data=body,
                method="POST"
            )
            req.add_header("Content-Type", "application/json")
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.status == 200
        except Exception as exc:
            logger.warning(f"Failed to set simulate Splunk failure: {exc}")
            return False
