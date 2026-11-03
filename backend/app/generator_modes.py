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
from netspout_core.yaml_sample_replay import SampleError, SampleSet, load_sample_set
from netspout_core.asa_generator import SOURCETYPE as ASA_SOURCETYPE, generate_asa_entries
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
from netspout_core.telemetry_dispatcher import dispatcher, is_metric_sourcetype

logger = logging.getLogger("netspout.generator_modes")


def _find_samples_dirs() -> List[str]:
    here = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(here, "..", "appserver", "static", "samples"),          # Splunk app layout: <app>/bin/netspout_core/ -> <app>/appserver/static/samples
        os.path.join(here, "..", "..", "appserver", "static", "samples"),    # <app>/bin/ -> <app>/appserver/static/samples
        os.path.join(os.environ.get("SPLUNK_HOME", "/opt/splunk"), "etc", "apps", "netspout", "appserver", "static", "samples"),
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "netspout", "appserver", "static", "samples"),
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "netspout", "samples"),
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "samples"),
        "/opt/splunk/etc/apps/netspout/appserver/static/samples"
    ]
    return [c for c in candidates if os.path.isdir(c)]


def _has_measurements(raw: str, sourcetype: str) -> bool:
    e = LogEntry(timestamp="", device_id="d", src_ip="0.0.0.0", dest_ip="0.0.0.0", protocol="n/a", duration="0ms", action="streamed", signature="x",
                 status="normal", raw_log=raw, node_type="router", node_id="d", vendor="v", sourcetype=sourcetype)
    return any(k.startswith("metric_name:") for k in dispatcher.extract_metric_fields(e))


MDT_METRIC_SOURCETYPE = "cisco:ios:mdt:metric"


def _mdt_metric_entries(count: int) -> List[LogEntry]:
    """Interface and platform counters as OpenConfig MDT records, one per interface in turn; delivered as HEC metrics (metric_name:* fields)."""
    rng = random.Random()
    dev = Node(id="ncs-edge-01", name="ncs-edge-01", type=NodeType.ROUTER, x=0, y=0, ip_address="10.200.1.1", vendor="cisco_ios", sourcetype=MDT_METRIC_SOURCETYPE)
    ifs = ["GigabitEthernet0/0/0", "GigabitEthernet0/0/1", "TenGigE0/0/0/1"]
    base = {i: rng.randint(10**7, 10**9) for i in ifs}
    out = []
    for n in range(count):
        i = ifs[n % len(ifs)]
        base[i] += rng.randint(10**5, 5 * 10**6)
        out.append(SplunkLogEngine.format_mdt_stream(dev, interface_name=i, in_octets=base[i], out_octets=int(base[i] * 1.2), cpu_pct=round(rng.uniform(5, 60), 1),
                                                     memory_pct=round(rng.uniform(20, 70), 1), sourcetype=MDT_METRIC_SOURCETYPE))
    return out


_NATIVE = {ASA_SOURCETYPE: generate_asa_entries, MDT_METRIC_SOURCETYPE: _mdt_metric_entries}


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
        cached = self._parsed_samples_cache.get(sourcetype)
        if cached is None:
            cached = self._resolve_samples(sourcetype, vendor_id)
            self._parsed_samples_cache[sourcetype] = cached
        source, prov_class, source_ref = cached
        if isinstance(source, SampleSet):
            # templates are cached; tokens (timestamps, hosts, ids) are rendered fresh on every call
            try:
                return source.render_all(), prov_class, source_ref
            except SampleError as exc:
                return [], "SAMPLE_INVALID", "sample invalid: %s" % exc
        return list(source), prov_class, source_ref

    def _resolve_samples(self, sourcetype: str, vendor_id: Optional[str]):
        events: Any = []
        prov_class = "UNSUPPORTED_TELEMETRY"
        source_ref: Optional[str] = None
        invalid: Optional[str] = None

        # 1. Check samples registered in catalog._samples
        for sm in self.catalog._samples:
            if sm.get("sourcetype") == sourcetype:
                # sample_path is relative to the directory that contains the `netspout` app: the repo root in development, <splunk>/etc/apps when installed
                roots = [self._repo_root, os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))]
                cand_path = next((c for c in (os.path.join(r, sm.get("sample_path", "")) for r in roots) if os.path.isfile(c)), "")
                if cand_path and os.path.isfile(cand_path):
                    try:
                        parsed = self._load_sample_events(cand_path, sourcetype)
                    except SampleError as exc:
                        invalid = "%s: %s" % (os.path.basename(cand_path), exc)
                        continue
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
                            try:
                                parsed = self._load_sample_events(c, sourcetype)
                            except SampleError as exc:
                                invalid = "%s: %s" % (os.path.basename(c), exc)
                                continue
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
                        # Vendor-level embedded samples carry no sourcetype, so they are only valid when this is the vendor's ONLY
                        # catalog sourcetype; otherwise an unrelated event (e.g. a Security 4624 for a Sysmon request) would be
                        # emitted under the requested sourcetype.
                        siblings = [r for r in self.catalog._sourcetypes if r.get("vendor_id") == vid and r.get("status") == "active"]
                        if v_obj and v_obj.get("sample_events") and len(siblings) <= 1:
                            ses = list(v_obj["sample_events"].values())
                            if ses:
                                events = ses
                                prov_class = "VENDOR_DOCUMENTED"
                                source_ref = f"vendor_catalog:{vid}"

        if events and is_metric_sourcetype(sourcetype):
            # a Splunk metric-index stream is never produced by replaying log text: every replayed event must carry numeric measurements
            sample = events.render_all() if isinstance(events, SampleSet) else list(events)
            if not sample or not all(_has_measurements(e, sourcetype) for e in sample):
                events, prov_class = [], "METRIC_REPLAY_UNSUPPORTED"
                source_ref = "%s is a metric-index sourcetype; its sample events carry no numeric measurements, so replay would not produce metrics" % sourcetype

        if not events:
            if prov_class != "METRIC_REPLAY_UNSUPPORTED":
                prov_class = "SAMPLE_INVALID" if invalid else "UNSUPPORTED_TELEMETRY"
                source_ref = ("sample invalid: " + invalid) if invalid else f"No verified public sample or documented vendor contract exists for sourcetype '{sourcetype}'"
        return events, prov_class, source_ref

    @staticmethod
    def _load_sample_events(file_path: str, sourcetype: str):
        """YAML samples go through the structured parser (only lines/_raw, fromRaw, fromSample are telemetry). Other files are plain one-event-per-line text."""
        if file_path.lower().endswith((".yml", ".yaml")):
            ss = load_sample_set(file_path)
            return ss.restrict_to(sourcetype) if sourcetype else ss
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            return [ln.rstrip("\r\n") for ln in f if ln.strip() and not ln.lstrip().startswith("#")]

    def _parse_sample_file(self, file_path: str) -> List[str]:
        """Rendered events of one sample file (kept for callers that want text); YAML is parsed structurally and invalid files raise SampleError."""
        events = self._load_sample_events(file_path, "")
        return events.render_all() if isinstance(events, SampleSet) else events

    def _universe_source(self, sourcetype):
        from netspout_core.universe_batch7_engine import batch_registry as batch7_registry
        source = next((s for s in batch7_registry()['sources'] if s['splunk_sourcetype'] == sourcetype), None)
        if source:
            return source, 'catalog/universe_batch7.json'
        from netspout_core.universe_batch6_engine import batch_registry as batch6_registry
        source = next((s for s in batch6_registry()['sources'] if s['splunk_sourcetype'] == sourcetype), None)
        if source:
            return source, 'catalog/universe_batch6.json'
        from netspout_core.universe_batch5_engine import batch_registry as batch5_registry
        source = next((s for s in batch5_registry()['sources'] if s['splunk_sourcetype'] == sourcetype), None)
        if source:
            return source, 'catalog/universe_batch5.json'
        from netspout_core.universe_batch4_engine import batch_registry as batch4_registry
        source = next((s for s in batch4_registry()['sources'] if s['splunk_sourcetype'] == sourcetype), None)
        if source:
            return source, 'catalog/universe_batch4.json'
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
        if source.get('generator') == 'format_universe_batch7_log':
            entry = SplunkLogEngine.format_universe_batch7_log(device=device, sourcetype=source['splunk_sourcetype'], family=family)
        elif source.get('generator') == 'format_universe_batch6_log':
            entry = SplunkLogEngine.format_universe_batch6_log(device=device, sourcetype=source['splunk_sourcetype'], family=family)
        elif source.get('generator') == 'format_universe_batch5_log':
            entry = SplunkLogEngine.format_universe_batch5_log(device=device, sourcetype=source['splunk_sourcetype'], family=family)
        elif source.get('generator') == 'format_universe_batch4_log':
            entry = SplunkLogEngine.format_universe_batch4_log(device=device, sourcetype=source['splunk_sourcetype'], family=family)
        elif source.get('generator') == 'format_universe_batch3_log':
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

    def generate_incident_pack(self, scenario_id, run_id=None, dispatch=False, transport_config=None):
        """Run one of the 37 finite NetSpout incident packs (modeled telemetry): 30 logs to the event index, 10 gauges to the metric index."""
        from netspout_core import incident_packs
        rid = run_id or 'pf-incident-' + str(uuid.uuid4())
        events = incident_packs.generate_pack(scenario_id, rid)
        results = []
        if dispatch:
            if transport_config is None:
                raise ValueError('Explicit transport configuration required for scenario dispatch')
            for payload in incident_packs.hec_payloads(events, transport_config.hec_index, transport_config.hec_metric_index):
                outcome = dispatcher.emit_hec(payload, transport_config.hec_url, transport_config.hec_token,
                                              ssl_verify=transport_config.hec_ssl_verify,
                                              allow_insecure_tls=transport_config.hec_allow_insecure_tls)
                results.append({'hec': {'success': bool(outcome[0]), 'state': str(getattr(outcome, 'state', ''))}})
        summary = incident_packs.summarize(events)
        indexes = {'events': (transport_config.hec_index if transport_config else None),
                   'metrics': (transport_config.hec_metric_index if transport_config else None)}
        return dict(mode='SCENARIO', status='GENERATED', scenario_id=scenario_id, run_id=rid, count_generated=len(events),
                    event_count=summary['log_events'], metric_event_count=summary['metric_events'],
                    metric_datapoints_expected=summary['metric_datapoints'], indexes=indexes, telemetry='MODELED_NETSPOUT_SCHEMA',
                    events=[{'time': e['time'], 'host': e['host'], 'sourcetype': e['sourcetype'], 'phase': e['fields']['netspout_phase'],
                             'kind': 'metric' if 'metrics' in e else 'log'} for e in events],
                    dispatch_results=results, dispatched=dispatch)

    def generate_universe_scenario(self, scenario_id, run_id=None, dispatch=False, transport_config=None):
        from netspout_core import incident_packs
        if scenario_id in incident_packs.incident_ids():
            return self.generate_incident_pack(scenario_id, run_id=run_id, dispatch=dispatch, transport_config=transport_config)
        from netspout_core.authentic_scenario_packs import run_scenario_pack, SCENARIO_PACK_IDS
        if scenario_id not in SCENARIO_PACK_IDS:   # every authentic pack the Explorer lists as runnable (wave2/wave3 and ub1-ub6)
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
        if sourcetype in _NATIVE:
            e = _NATIVE[sourcetype](1)[0]
            target_index = index or "idx_network_ops"
            res = dispatcher.dispatch_log(e, transport_config or TelemetryTransportConfig(hec_url="https://127.0.0.1:8088/services/collector", hec_index=target_index)) if dispatch else None
            return {"mode": "SINGLE_EVENT", "status": "GROUNDED", "event_id": e.netspout_event_id, "vendor_id": vendor_id, "sourcetype": sourcetype, "event_name": event_name or "Event",
                    "index": target_index, "host": e.device_id, "raw": e.raw_log, "provenance": self._NATIVE_PROVENANCE[sourcetype], "dispatched": dispatch, "dispatch_result": res}
        self._reject_non_ta_name(sourcetype)
        samples, prov_class, source_ref = self.get_grounded_samples(sourcetype, vendor_id=vendor_id)
        if not samples:
            return {
                "mode": "SINGLE_EVENT",
                "status": "TELEMETRY_NOT_GROUNDED",
                "error": "UNSUPPORTED_TELEMETRY",
                "vendor_id": vendor_id,
                "sourcetype": sourcetype,
                "reason": source_ref if prov_class in ("SAMPLE_INVALID", "METRIC_REPLAY_UNSUPPORTED") else f"No authoritative vendor log schema or verified sample exists for sourcetype '{sourcetype}'.",
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
        if sourcetype in _NATIVE:
            return self._native_batch(vendor_id, sourcetype, count, rate_eps, dispatch, transport_config, index)
        self._reject_non_ta_name(sourcetype)
        samples, prov_class, source_ref = self.get_grounded_samples(sourcetype, vendor_id=vendor_id)
        if not samples:
            return {
                "mode": "SOURCETYPE_BATCH",
                "status": "TELEMETRY_NOT_GROUNDED",
                "error": "UNSUPPORTED_TELEMETRY",
                "vendor_id": vendor_id,
                "sourcetype": sourcetype,
                "reason": source_ref if prov_class in ("SAMPLE_INVALID", "METRIC_REPLAY_UNSUPPORTED") else f"No authoritative vendor log schema or verified sample exists for sourcetype '{sourcetype}'.",
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

    _NATIVE_PROVENANCE = {
        ASA_SOURCETYPE: {"classification": "VENDOR_DOCUMENTED", "source": "netspout_core/asa_generator.py; message formats per Cisco ASA syslog guide (302013-302016, 106023); sourcetype declared by Splunk Add-on for Cisco ASA (Splunkbase 1620); TA parsing NOT verified"},
        MDT_METRIC_SOURCETYPE: {"classification": "VENDOR_DOCUMENTED", "source": "SplunkLogEngine.format_mdt_stream (OpenConfig interface and platform counters); delivered as Splunk HEC metrics"},
    }

    @staticmethod
    def _reject_non_ta_name(sourcetype: str):
        if sourcetype == "cisco:asa:syslog":
            raise ValueError("NON_CANONICAL_SOURCETYPE: 'cisco:asa:syslog' is not a Splunk Add-on for Cisco ASA sourcetype; use 'cisco:asa'")

    def _native_batch(self, vendor_id, sourcetype, count, rate_eps, dispatch, transport_config, index):
        target_index = index or "idx_network_ops"
        entries = _NATIVE[sourcetype](count)
        cfg = transport_config or TelemetryTransportConfig(hec_url="https://127.0.0.1:8088/services/collector", hec_index=target_index)
        sent = 0
        for e in entries:
            e.netspout_event_id = e.netspout_event_id or str(uuid.uuid4())
            e.netspout_ground_truth = "true"
            if dispatch:
                res = dispatcher.dispatch_log(e, cfg)
                sent += bool(res.get("hec", {}).get("success") or res.get("syslog", {}).get("success"))
        return {"mode": "SOURCETYPE_BATCH", "status": "GROUNDED", "vendor_id": vendor_id, "sourcetype": sourcetype, "count_requested": count, "count_generated": len(entries),
                "count_dispatched": sent, "rate_eps": rate_eps, "index": target_index, "provenance": self._NATIVE_PROVENANCE[sourcetype], "sample_preview": [e.raw_log for e in entries[:3]]}

    def prepare_sourcetype_entries(self, vendor_id: str, sourcetype: str, count: int, event_families: Optional[List[str]] = None,
                                   run_id: Optional[str] = None):
        """Build (not send) the LogEntry list for one sourcetype so a monitored run can deliver them with exact per-event accounting.
        Same grounding rules as generate_sourcetype_batch: native registries first, then verified samples; never a fabricated payload.
        Returns (entries, provenance) or raises ValueError('TELEMETRY_NOT_GROUNDED: ...')."""
        if not 1 <= count <= 1000:
            raise ValueError("count must be between 1 and 1000")
        source, reference = self._universe_source(sourcetype)
        if source:
            families = event_families or source["event_families"]
            if any(f not in source["event_families"] for f in families):
                raise ValueError("Unsupported native event family")
            entries = [self._universe_entry(source, vendor_id, families[i % len(families)]) for i in range(count)]
            prov = dict(classification=source.get("evidence_level", "VENDOR_DOCUMENTED"), source=reference, mode="native")
        elif sourcetype in _NATIVE:
            entries = _NATIVE[sourcetype](count)
            for e in entries:
                e.netspout_event_id = e.netspout_event_id or str(uuid.uuid4())
                e.netspout_ground_truth = "true"
            prov = dict(self._NATIVE_PROVENANCE[sourcetype], mode="native")
        else:
            self._reject_non_ta_name(sourcetype)
            samples, prov_class, source_ref = self.get_grounded_samples(sourcetype, vendor_id=vendor_id)
            if not samples:
                raise ValueError("TELEMETRY_NOT_GROUNDED: " + (source_ref if prov_class in ("SAMPLE_INVALID", "METRIC_REPLAY_UNSUPPORTED") else "no authoritative vendor log schema or verified sample exists for " + sourcetype))
            entries = []
            for i in range(count):
                dev = f"device-{(i % 3) + 1:02d}"
                ev_id = str(uuid.uuid4())
                entries.append(LogEntry(id=ev_id, timestamp=SplunkLogEngine.current_timestamp_iso(), device_id=dev, src_ip=f"10.0.1.{(i % 250) + 1}", dest_ip="10.0.2.50",
                                        protocol="TCP", duration="10ms", signature="NETSPOUT_BATCH_STREAM", node_type="switch", node_id=dev, vendor=vendor_id,
                                        sourcetype=sourcetype, raw_log=random.choice(samples), status="normal", action="streamed", netspout_event_id=ev_id,
                                        netspout_ground_truth="true"))
            prov = dict(classification=prov_class, source=source_ref, mode="grounded_sample")
        if run_id:
            for e in entries:
                e.netspout_run_id = run_id
        return entries, prov

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

