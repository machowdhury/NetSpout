# =========================================================================
# AUTO-GENERATED PACKAGED COPY — DO NOT EDIT DIRECTLY!
# Authoritative Source of Truth: src/netspout_core/generator_modes.py
# Re-generate using: python3 scripts/sync_core.py
# =========================================================================
"""
NetSpout Multi-Mode Telemetry Generator.

Implements all 4 primary user-facing generation modes:
  - MODE A: SCENARIO — Full operational incident lifecycle (Baseline -> Degrade -> Failover -> Recovery)
  - MODE B: DATA SOURCE — Specific vendor/product telemetry stream (Cisco IOS XR, Arista EOS, Palo Alto, etc.)
  - MODE C: SOURCETYPE / EVENT FAMILY — Direct Splunk sourcetype generation (Count, EPS, event families)
  - MODE D: SINGLE EVENT — Precision 1-event generation for developer testing, dashboards, and detection tuning
"""

import json
import logging
import os
import random
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple, Union

from netspout_core.catalog import NetSpoutCatalog
from netspout_core.log_engine import SplunkLogEngine
from netspout_core.vendor_catalog import get_vendor_by_id
from netspout_core.models import (
    EcosystemMode,
    LogEntry,
    Node,
    NodeType,
    ScenarioRunRequest,
    ScenarioType,
    TelemetryTransportConfig,
)
from netspout_core.telemetry_dispatcher import dispatcher

logger = logging.getLogger("netspout.generator_modes")


def _find_samples_dirs() -> List[str]:
    candidates = [
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "netspout", "appserver", "static", "samples"),
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "netspout", "samples"),
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "samples"),
        "/opt/splunk/etc/apps/netspout/appserver/static/samples"
    ]
    return [c for c in candidates if os.path.isdir(c)]


class TelemetryGeneratorService:
    """
    Unified Telemetry Generation Engine for Modes B, C, and D.
    (Mode A is handled via ScenarioRunner).
    Enforces strict anti-fabrication principles and source provenance tracking.
    """

    def __init__(self, catalog: Optional[NetSpoutCatalog] = None):
        self.catalog = catalog or NetSpoutCatalog()
        self.samples_dirs = _find_samples_dirs()
        self._parsed_samples_cache: Dict[str, Tuple[List[str], str, Optional[str]]] = {}
        self._repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

    def get_grounded_samples(self, sourcetype: str, vendor_id: Optional[str] = None) -> Tuple[List[str], str, Optional[str]]:
        """
        Retrieves authentic vendor telemetry samples and provenance.
        Returns:
            (events_list, provenance_classification, source_reference)
        If not grounded, returns:
            ([], 'UNSUPPORTED_TELEMETRY', reason)
        """
        if sourcetype in self._parsed_samples_cache:
            return self._parsed_samples_cache[sourcetype]

        events: List[str] = []
        prov_class = "UNSUPPORTED_TELEMETRY"
        source_ref: Optional[str] = None

        # 1. Check samples registered in catalog._samples
        for sm in self.catalog._samples:
            if sm.get("sourcetype") == sourcetype:
                cand_path = os.path.join(self._repo_root, sm.get("sample_path", ""))
                if os.path.isfile(cand_path):
                    parsed = self._parse_sample_file(cand_path)
                    if parsed:
                        events = parsed
                        prov_class = "VERIFIED_PUBLIC_SAMPLE"
                        source_ref = sm.get("sample_path")
                        break

        # 2. Check catalog sourcetype definition & sample directories
        if not events:
            st_meta = self.catalog.get_sourcetype(sourcetype)
            if st_meta:
                sf = st_meta.get("sample_file")
                sid = st_meta.get("id")
                for sd in self.samples_dirs:
                    candidates = [
                        os.path.join(sd, sf) if sf else "",
                        os.path.join(sd, sid, sf) if sid and sf else "",
                        os.path.join(sd, sid, sid + ".yml") if sid else "",
                        os.path.join(sd, sid, sid + ".sample") if sid else "",
                        os.path.join(sd, sourcetype.replace(":", "_") + ".sample"),
                        os.path.join(sd, sourcetype.replace(":", "_") + ".log"),
                    ]
                    for c in candidates:
                        if c and os.path.isfile(c):
                            parsed = self._parse_sample_file(c)
                            if parsed:
                                events = parsed
                                prov_class = "VERIFIED_PUBLIC_SAMPLE"
                                source_ref = c
                                break
                    if events:
                        break

                # 3. Check vendor catalog embedded samples
                if not events:
                    vid = vendor_id or st_meta.get("vendor_id")
                    if vid:
                        v_obj = get_vendor_by_id(vid)
                        if v_obj and v_obj.get("sample_events"):
                            ses = list(v_obj["sample_events"].values())
                            if ses:
                                events = ses
                                prov_class = "VENDOR_DOCUMENTED"
                                source_ref = f"vendor_catalog:{vid}"

        if not events:
            prov_class = "UNSUPPORTED_TELEMETRY"
            source_ref = f"No verified public sample or documented vendor contract exists for sourcetype '{sourcetype}'"

        result = (events, prov_class, source_ref)
        self._parsed_samples_cache[sourcetype] = result
        return result

    def _parse_sample_file(self, file_path: str) -> List[str]:
        events = []
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    line_str = line.strip()
                    if "_raw:" in line_str:
                        parts = line_str.split("_raw:", 1)
                        val = parts[1].strip()
                        if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                            val = val[1:-1]
                        if val:
                            events.append(val)
                    elif not line_str.startswith("#") and not line_str.startswith("-") and not line_str.endswith(":") and len(line_str) > 20:
                        events.append(line_str)
        except Exception as e:
            logger.debug(f"Failed parsing sample file {file_path}: {e}")
        return events

    def generate_single_event(
        self,
        vendor_id: str,
        sourcetype: str,
        event_name: Optional[str] = None,
        dispatch: bool = False,
        transport_config: Optional[TelemetryTransportConfig] = None,
        index: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        MODE D: Generate exactly one precision event.
        Guarantees zero fabricated vendor telemetry.
        """
        samples, prov_class, source_ref = self.get_grounded_samples(sourcetype, vendor_id=vendor_id)
        if not samples:
            return {
                "mode": "SINGLE_EVENT",
                "status": "TELEMETRY_NOT_GROUNDED",
                "error": "UNSUPPORTED_TELEMETRY",
                "vendor_id": vendor_id,
                "sourcetype": sourcetype,
                "reason": f"No authoritative vendor log schema or verified sample exists for sourcetype '{sourcetype}'.",
                "provenance_status": prov_class,
                "source_requirement": "Must be documented in vendor specification or catalog/telemetry_sources.json"
            }

        raw_event = random.choice(samples)
        event_id = str(uuid.uuid4())
        target_index = index or "idx_network_ops"
        target_host = "sim-device-01"

        log_entry = LogEntry(
            id=event_id,
            timestamp=SplunkLogEngine.current_timestamp_iso(),
            device_id=target_host,
            src_ip="198.51.100.25",
            dest_ip="10.0.1.10",
            protocol="TCP",
            duration="15ms",
            signature="NETSPOUT_SINGLE_EVENT",
            node_type="router",
            node_id=target_host,
            vendor=vendor_id,
            sourcetype=sourcetype,
            raw_log=raw_event,
            status="normal",
            action="emitted",
            netspout_event_id=event_id,
            netspout_ground_truth="true"
        )

        dispatch_result = None
        if dispatch:
            cfg = transport_config or TelemetryTransportConfig(
                hec_url="https://127.0.0.1:8088/services/collector",
                hec_index=target_index
            )
            dispatch_result = dispatcher.dispatch_log_entry(log_entry, cfg)

        return {
            "mode": "SINGLE_EVENT",
            "status": "GROUNDED",
            "event_id": event_id,
            "vendor_id": vendor_id,
            "sourcetype": sourcetype,
            "event_name": event_name or "Event",
            "index": target_index,
            "host": target_host,
            "raw": raw_event,
            "provenance": {
                "classification": prov_class,
                "source": source_ref
            },
            "dispatched": dispatch,
            "dispatch_result": dispatch_result
        }

    def generate_sourcetype_batch(
        self,
        vendor_id: str,
        sourcetype: str,
        count: int = 10,
        rate_eps: int = 10,
        event_families: Optional[List[str]] = None,
        dispatch: bool = False,
        transport_config: Optional[TelemetryTransportConfig] = None,
        index: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        MODE C: Generate a batch of events for a specific sourcetype / event family.
        Guarantees zero fabricated vendor telemetry.
        """
        samples, prov_class, source_ref = self.get_grounded_samples(sourcetype, vendor_id=vendor_id)
        if not samples:
            return {
                "mode": "SOURCETYPE_BATCH",
                "status": "TELEMETRY_NOT_GROUNDED",
                "error": "UNSUPPORTED_TELEMETRY",
                "vendor_id": vendor_id,
                "sourcetype": sourcetype,
                "reason": f"No authoritative vendor log schema or verified sample exists for sourcetype '{sourcetype}'.",
                "provenance_status": prov_class,
                "source_requirement": "Must be documented in vendor specification or catalog/telemetry_sources.json"
            }

        total_generated = 0
        dispatched_count = 0
        events_generated: List[str] = []
        target_index = index or "idx_network_ops"

        cfg = transport_config or TelemetryTransportConfig(
            hec_url="https://127.0.0.1:8088/services/collector",
            hec_index=target_index
        )

        for i in range(count):
            base_sample = random.choice(samples)
            ev_id = str(uuid.uuid4())
            events_generated.append(base_sample)
            total_generated += 1

            if dispatch:
                dev_name = f"device-{(i % 3) + 1:02d}"
                entry = LogEntry(
                    id=ev_id,
                    timestamp=SplunkLogEngine.current_timestamp_iso(),
                    device_id=dev_name,
                    src_ip=f"10.0.1.{(i % 250) + 1}",
                    dest_ip="10.0.2.50",
                    protocol="TCP",
                    duration="10ms",
                    signature="NETSPOUT_BATCH_STREAM",
                    node_type="switch",
                    node_id=dev_name,
                    vendor=vendor_id,
                    sourcetype=sourcetype,
                    raw_log=base_sample,
                    status="normal",
                    action="streamed",
                    netspout_event_id=ev_id,
                    netspout_ground_truth="true"
                )
                res = dispatcher.dispatch_log_entry(entry, cfg)
                if res.get("hec", {}).get("success") or res.get("syslog", {}).get("success"):
                    dispatched_count += 1

        return {
            "mode": "SOURCETYPE_BATCH",
            "status": "GROUNDED",
            "vendor_id": vendor_id,
            "sourcetype": sourcetype,
            "count_requested": count,
            "count_generated": total_generated,
            "count_dispatched": dispatched_count,
            "rate_eps": rate_eps,
            "index": target_index,
            "provenance": {
                "classification": prov_class,
                "source": source_ref
            },
            "sample_preview": events_generated[:3]
        }

    def generate_data_source(
        self,
        vendor_id: str,
        product: str,
        transport: str = "syslog",
        count: int = 50,
        rate_eps: int = 20,
        dispatch: bool = False,
        transport_config: Optional[TelemetryTransportConfig] = None,
        index: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        MODE B: Generate data stream for a specific vendor / product data source.
        """
        sourcetypes = [
            s["splunk_sourcetype"]
            for s in self.catalog._sourcetypes
            if s.get("vendor_id") == vendor_id
        ]
        if not sourcetypes:
            sourcetypes = [f"{vendor_id}:{product.lower()}"]

        chosen_st = sourcetypes[0]
        res = self.generate_sourcetype_batch(
            vendor_id=vendor_id,
            sourcetype=chosen_st,
            count=count,
            rate_eps=rate_eps,
            dispatch=dispatch,
            transport_config=transport_config,
            index=index
        )
        res["mode"] = "DATA_SOURCE"
        res["product"] = product
        res["transport"] = transport
        return res


generator_service = TelemetryGeneratorService()

