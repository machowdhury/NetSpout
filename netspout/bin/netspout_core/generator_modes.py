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


def _find_samples_dir() -> Optional[str]:
    candidates = [
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "samples"),
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "netspout", "samples"),
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "netspout", "appserver", "static", "samples"),
        "/opt/splunk/etc/apps/netspout/appserver/static/samples"
    ]
    for c in candidates:
        if os.path.isdir(c):
            return c
    return None


class TelemetryGeneratorService:
    """
    Unified Telemetry Generation Engine for Modes B, C, and D.
    (Mode A is handled via ScenarioRunner).
    """

    def __init__(self, catalog: Optional[NetSpoutCatalog] = None):
        self.catalog = catalog or NetSpoutCatalog()
        self.samples_dir = _find_samples_dir()
        self._parsed_samples_cache: Dict[str, List[str]] = {}

    def _get_sample_events(self, sourcetype: str) -> List[str]:
        if sourcetype in self._parsed_samples_cache:
            return self._parsed_samples_cache[sourcetype]

        st_meta = self.catalog.get_sourcetype(sourcetype)
        events: List[str] = []

        if self.samples_dir and st_meta and st_meta.get("sample_file"):
            sample_file_name = st_meta["sample_file"]
            sample_id = st_meta.get("id") or sourcetype.replace(":", "-")
            candidates = [
                os.path.join(self.samples_dir, sample_file_name),
                os.path.join(self.samples_dir, sample_id, sample_file_name),
                os.path.join(self.samples_dir, sourcetype.replace(":", "_") + ".sample"),
                os.path.join(self.samples_dir, sourcetype.replace(":", "_") + ".log"),
            ]
            for cand in candidates:
                if os.path.isfile(cand):
                    try:
                        with open(cand, "r", encoding="utf-8", errors="replace") as f:
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
                        if events:
                            break
                    except Exception as e:
                        logger.debug(f"Failed parsing sample file {cand}: {e}")

        # Fallback to realistic synthetic generation if no static sample file is found
        if not events:
            events = self._generate_fallback_synthetic_events(sourcetype)

        self._parsed_samples_cache[sourcetype] = events
        return events

    def _generate_fallback_synthetic_events(self, sourcetype: str) -> List[str]:
        now_syslog = SplunkLogEngine.current_timestamp_syslog()
        dummy_node = Node(id="sim-gw-01", name="sim-gw-01", type=NodeType.ROUTER, vendor="cisco_ios")

        if "cisco:ios" in sourcetype or "cisco:xr" in sourcetype:
            return [
                f"{now_syslog} sim-gw-01 %ROUTING-6-BGP_NEIGHBOR_UP: BGP neighbor 198.51.100.2 AS 65001 state changed to ESTABLISHED",
                f"{now_syslog} sim-gw-01 %LINEPROTO-5-UPDOWN: Line protocol on Interface GigabitEthernet0/0/0, changed state to up",
                f"{now_syslog} sim-gw-01 %OSPF-5-ADJCHANGE: Process 1, Nbr 10.254.1.1 on GigabitEthernet0/0/0 from LOADING to FULL, Done",
                f"{now_syslog} sim-gw-01 %SYS-5-CONFIG_I: Configured from console by netops on vty0 (10.0.1.50)",
                f"{now_syslog} sim-gw-01 %ENV-4-FAN_SPEED: Chassis cooling fan 1 RPM at 7200, within normal operating envelope"
            ]
        elif "arista:eos" in sourcetype:
            return [
                f"{now_syslog} sw-arista-01 Rib: %ROUTING-6-BGP_NEIGHBOR_UP: BGP neighbor 10.254.1.2 AS 64512 state changed from OPENCONFIRM to ESTABLISHED",
                f"{now_syslog} sw-arista-01 Lineproto: %LINEPROTO-5-UPDOWN: Line protocol on Interface Ethernet1/1, changed state to up",
                f"{now_syslog} sw-arista-01 Ebgp: %BGP-5-ADJCHANGE: neighbor 198.51.100.1 Up (VRF default)",
                f"{now_syslog} sw-arista-01 Sand: %SAND-6-PFC_WATCHDOG_RECOVERED: Priority-flow-control watchdog recovered on Ethernet1/1 priority 3"
            ]
        elif "pan:" in sourcetype or "paloalto" in sourcetype:
            return [
                f"1,{time.strftime('%Y/%m/%d %H:%M:%S')},001801000000,TRAFFIC,allow,2304,198.51.100.42,10.0.1.10,0.0.0.0,0.0.0.0,OUTSIDE_IN,user-guest,ssl,vsys1,outside,inside,ethernet1/1,ethernet1/2,default,2026/10/01 21:00:00,1024,1,443,12450,0,0,0x400000,tcp,allow,1420,720,700,12,2026/10/01 21:00:00,14,any,0,12345678,0x0,United States,10.0.0.0-10.255.255.255,1,11,client-rst,0,0,0,0,,pa-fw-01,from-policy",
                f"1,{time.strftime('%Y/%m/%d %H:%M:%S')},001801000000,THREAT,vulnerability,2304,198.51.100.99,10.0.1.50,0.0.0.0,0.0.0.0,OUTSIDE_IN,unknown,web-browsing,vsys1,outside,inside,ethernet1/1,ethernet1/2,default,2026/10/01 21:00:00,1025,1,80,33412,0,0,0x400000,tcp,alert,0,0,0,0,2026/10/01 21:00:00,0,any,0,12345679,0x0,United States,10.0.0.0-10.255.255.255,1,11,alert,Apache Log4j RCE (CVE-2021-44228),high,client-to-server,pa-fw-01,from-policy"
            ]
        elif "cisco:asa" in sourcetype:
            entry = SplunkLogEngine.format_cisco_asa_log(
                device=dummy_node,
                src_ip="198.51.100.45",
                dest_ip="10.0.1.10",
                src_port=49210,
                dest_port=443,
                proto="TCP",
                action="permitted",
                signature="OUTSIDE_IN",
                status="normal"
            )
            return [entry.raw_log]
        else:
            return [
                f"{now_syslog} generic-node-01 SystemEvent: sourcetype={sourcetype} status=normal action=streamed event_id={uuid.uuid4().hex[:8]}"
            ]

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
        """
        samples = self._get_sample_events(sourcetype)
        raw_event = random.choice(samples) if samples else f"timestamp={time.time()} sourcetype={sourcetype} event=single_event"

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
                hec_url="https://127.0.0.1:8888/services/collector",
                hec_token="00000000-0000-0000-0000-000000000000",
                hec_index=target_index
            )
            dispatch_result = dispatcher.dispatch_log_entry(log_entry, cfg)

        return {
            "mode": "SINGLE_EVENT",
            "event_id": event_id,
            "vendor_id": vendor_id,
            "sourcetype": sourcetype,
            "event_name": event_name or "Event",
            "index": target_index,
            "host": target_host,
            "raw": raw_event,
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
        """
        samples = self._get_sample_events(sourcetype)
        total_generated = 0
        dispatched_count = 0
        events_generated: List[str] = []
        target_index = index or "idx_network_ops"

        cfg = transport_config or TelemetryTransportConfig(
            hec_url="https://127.0.0.1:8888/services/collector",
            hec_token="00000000-0000-0000-0000-000000000000",
            hec_index=target_index
        )

        for i in range(count):
            base_sample = random.choice(samples) if samples else f"time={time.time()} st={sourcetype} seq={i}"
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
            "vendor_id": vendor_id,
            "sourcetype": sourcetype,
            "count_requested": count,
            "count_generated": total_generated,
            "count_dispatched": dispatched_count,
            "rate_eps": rate_eps,
            "index": target_index,
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
        return self.generate_sourcetype_batch(
            vendor_id=vendor_id,
            sourcetype=chosen_st,
            count=count,
            rate_eps=rate_eps,
            dispatch=dispatch,
            transport_config=transport_config,
            index=index
        )


generator_service = TelemetryGeneratorService()
