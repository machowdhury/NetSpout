# =========================================================================
# AUTO-GENERATED PACKAGED COPY — DO NOT EDIT DIRECTLY!
# Authoritative Source of Truth: src/netspout_core/collector_evidence.py
# Re-generate using: python3 scripts/sync_core.py
# =========================================================================
"""
NetSpout Collector Evidence Adapter.
Interacts with the containerized GoFlow2 + Forwarder collector tier
to verify COLLECTOR_OBSERVED evidence state independently of Splunk ingestion.
Conforms to Gate 11C Architecture Phase 15.
"""

import json
import logging
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

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
        forwarder_status_url: str = "http://127.0.0.1:8082"
    ):
        self.goflow_metrics_url = goflow_metrics_url
        self.forwarder_status_url = forwarder_status_url.rstrip("/")

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
        except Exception as exc:
            details["forwarder_error"] = str(exc)

        overall_healthy = details["goflow_metrics"] and details["forwarder_status"]
        return overall_healthy, details

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
            # Check observation domain / source ID
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
