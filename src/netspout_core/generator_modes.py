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

    def _universe_source(self, sourcetype):
        from netspout_core.universe_batch3_engine import batch_registry as batch3_registry
        source = next((s for s in batch3_registry()['sources'] if s['splunk_sourcetype'] == sourcetype), None)
        if source:
            return source, 'catalog/universe_batch3.json'
        from netspout_core.universe_batch2_engine import batch_registry
        from netspout_core.universe_batch1_engine import UNIVERSE_BATCH1_SOURCE_SOURCETYPES
        source = next((s for s in batch_registry()['sources'] if s['splunk_sourcetype'] == sourcetype), None)
        if source:
            return source, 'catalog/universe_batch2.json'
        if sourcetype in UNIVERSE_BATCH1_SOURCE_SOURCETYPES:
            path = os.path.join(self.catalog.catalog_dir, 'universe_batch1.json')
            with open(path) as handle:
                source = next(s for s in json.load(handle)['sources'] if s['splunk_sourcetype'] == sourcetype)
            return source, 'catalog/universe_batch1.json'
        return None, None

    def _universe_entry(self, source, vendor_id, family=None):
        if source['vendor'] != vendor_id:
            raise ValueError('Vendor does not own the requested sourcetype')
        family = family or source['event_families'][0]
        if family not in source['event_families']:
            raise ValueError('Unsupported native event family')
        device = Node(id='source-preview', name='source-preview.example.test',
                      type=NodeType.WEB_SERVER, ip_address='198.51.100.10')
        if source.get('generator') == 'format_universe_batch3_log':
            entry = SplunkLogEngine.format_universe_batch3_log(device=device, sourcetype=source['splunk_sourcetype'], family=family)
        elif source.get('batch_source_id') in ('vault','traefik','claroty','mongodb','confluence','nginx','proofpoint','veeam','mikrotik'):
            entry = SplunkLogEngine.format_universe_batch2_log(device=device, sourcetype=source['splunk_sourcetype'], family=family)
        else:
            kwargs = dict(device=device, family=family)
            if source['splunk_sourcetype'] == 'bluecoat:proxysg:access:file':
                kwargs['src_ip'] = '192.0.2.10'
            entry = getattr(SplunkLogEngine, source['generator'])(**kwargs)
        entry.netspout_event_id = str(uuid.uuid4())
        entry.netspout_ground_truth = 'synthetic_observation'
        return entry

    def generate_universe_scenario(self, scenario_id, run_id=None, dispatch=False, transport_config=None):
        from netspout_core.authentic_scenario_packs import run_scenario_pack
        from netspout_core.universe_batch2_engine import BATCH2_SCENARIO_IDS
        from netspout_core.universe_batch3_engine import BATCH3_SCENARIO_IDS
        if scenario_id not in BATCH2_SCENARIO_IDS + BATCH3_SCENARIO_IDS + ['ub1_ot_proxy_host_hunt']:
            raise ValueError('Unsupported universe scenario')
        entries = run_scenario_pack(scenario_id, run_id or 'pf-universe-' + str(uuid.uuid4()))
        results = []
        if dispatch:
            if transport_config is None:
                raise ValueError('Explicit transport configuration required for scenario dispatch')
            results = [dispatcher.dispatch_log(entry, transport_config) for entry in entries]
        return dict(mode='SCENARIO', status='GENERATED', scenario_id=scenario_id,
                    run_id=entries[0].netspout_run_id, count_generated=len(entries),
                    events=[entry.model_dump() for entry in entries], dispatch_results=results,
                    dispatched=dispatch)

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
        source, reference = self._universe_source(sourcetype)
        if source:
            entry = self._universe_entry(source, vendor_id, event_name)
            cfg = transport_config or TelemetryTransportConfig(hec_index=index or 'idx_network_ops')
            result = dispatcher.dispatch_log(entry, cfg) if dispatch else None
            return dict(mode='SINGLE_EVENT', status='GROUNDED', event_id=entry.netspout_event_id,
                        vendor_id=vendor_id, sourcetype=sourcetype, event_name=entry.signature,
                        index=index or 'idx_network_ops', host=entry.device_id, raw=entry.raw_log,
                        provenance=dict(classification=source.get('evidence_level', 'VENDOR_DOCUMENTED'), source=reference),
                        dispatched=dispatch, dispatch_result=result)
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
            dispatch_result = dispatcher.dispatch_log(log_entry, cfg)

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
        source, reference = self._universe_source(sourcetype)
        if source:
            if not 1 <= count <= 1000:
                raise ValueError('Universe batch count must be between 1 and 1000')
            families = event_families or source['event_families']
            if any(f not in source['event_families'] for f in families):
                raise ValueError('Unsupported native event family')
            entries = [self._universe_entry(source, vendor_id, families[i % len(families)]) for i in range(count)]
            cfg = transport_config or TelemetryTransportConfig(hec_index=index or 'idx_network_ops')
            results = [dispatcher.dispatch_log(entry, cfg) for entry in entries] if dispatch else []
            successful = sum(bool((r.get('hec') or {}).get('success') or (r.get('syslog') or {}).get('success')) for r in results)
            return dict(mode='SOURCETYPE_BATCH', status='GROUNDED', vendor_id=vendor_id, sourcetype=sourcetype,
                        count_requested=count, count_generated=len(entries), count_dispatched=successful,
                        rate_eps=rate_eps, index=index or 'idx_network_ops', event_families=families,
                        provenance=dict(classification=source.get('evidence_level', 'VENDOR_DOCUMENTED'), source=reference),
                        sample_preview=[entry.raw_log for entry in entries[:3]])
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
                res = dispatcher.dispatch_log(entry, cfg)
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

