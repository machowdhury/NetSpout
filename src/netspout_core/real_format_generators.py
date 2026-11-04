"""Generators and format helpers corrected against real Splunk telemetry (Phase 7 evidence, Phase 8 corrections).

Evidence files: docs/contracts/phase7/ (real_metric_inventory.json, phase8_metric_evidence.json), tests/fixtures/phase7_real_samples/.
Nothing here invents a field: every metric name, dimension and value range below was observed on the reference instance, and every VMware column
keeps the type, order and delimiter of the observed row. What was NOT observed is stated beside the code that has to choose something anyway.
"""
import json
import random
import re
import threading
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from netspout_core.models import LogEntry

# ------------------------------------------------------------------ Duo / asctime
def asctime_utc(dt: datetime) -> str:
    """The ctime dialect Duo uses ('Tue Nov  3 10:33:44 2026'): weekday from the actual date, day space-padded, UTC. Naive datetimes are taken as UTC."""
    dt = dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    return "%s %s %2d %s %d" % (("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")[dt.weekday()],
                                ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")[dt.month - 1], dt.day, dt.strftime("%H:%M:%S"), dt.year)


# ------------------------------------------------------------------ Meraki family contract
# meraki:securityappliances in the real data is only the network-event schema. The AMP-style (ts/eventType) and Air Marshal (ssid/bssids) schemas belong to
# meraki:organizationsecurity and meraki:airmarshal; mixing them under this sourcetype is a defect.
FAMILY_CONTRACTS: Dict[str, Dict[str, object]] = {
    "meraki:securityappliances": {
        "required": ("occurredAt", "networkId", "type", "description", "category", "eventData", "organizationId"),
        "forbidden": ("eventType", "ts", "ssid", "bssids"),
    },
}


def family_violations(sourcetype: str, events: List[str]) -> List[str]:
    """Human-readable reasons events do not belong to the sourcetype's event family (empty = all conform or no contract)."""
    c = FAMILY_CONTRACTS.get(sourcetype)
    if not c:
        return []
    out = []
    for i, raw in enumerate(events):
        try:
            o = json.loads(raw)
        except (TypeError, ValueError):
            out.append("event %d is not JSON" % i)
            continue
        miss = [k for k in c["required"] if k not in o]
        foreign = [k for k in c["forbidden"] if k in o]
        if miss or foreign:
            out.append("event %d: missing %s; foreign keys %s" % (i, miss or "none", foreign or "none"))
    return out


# Plain-text samples carry fixed event times. For sourcetypes whose add-on takes _time from a field inside the event (Splunk_TA_cisco_meraki: TIME_PREFIX on
# "occurredAt"), a stale value means Splunk would date the event in the past, so the field is rendered at generation time in the observed format.
_EVENT_TIME_FIELDS = {"meraki:securityappliances": re.compile(r'("occurredAt"\s*:\s*")[^"]+(")')}


def refresh_event_time(sourcetype: str, raw: str, now: Optional[datetime] = None) -> str:
    rx = _EVENT_TIME_FIELDS.get(sourcetype)
    if not rx:
        return raw
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    return rx.sub(lambda m: m.group(1) + now.strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z" + m.group(2), raw)


# ------------------------------------------------------------------ VMware vmware:perf:cpu (TSV event in an event index)
VMWARE_CPU_SOURCETYPE = "vmware:perf:cpu"
VMWARE_CPU_SOURCE = "VMPerf:HostSystem"
VMWARE_VCENTER_HOST = "vcenter.example.invalid"
# One observed row (sanitized fixture 'vmware:perf:cpu'): moid, uuid, instance, samp_int, then 15 counter columns. Column types as observed:
# F = float rendered with Python str(), I = integer. The Splunk_TA_vmware 4.2.1 collector (performance_handlers._output_results) writes exactly this layout
# (moid, uuid, instance, samp_int, counters), tab separated, one row per event, time passed explicitly. The counter column NAMES come from vCenter at runtime
# and from the field-extraction add-on, which was not available, so column semantics and value ranges are NOT evidenced: each column varies around its single
# observed magnitude, keeps its type, and zero columns stay zero.
_VMWARE_CPU_OBSERVED = ("0.21", "0", "0.07", "0", "39933", "0", "0", "319723", "0.0", "243", "35", "0.14", "0.0", "0", "0")
_SAMP_INT = "20"


def vmware_cpu_row(rng: random.Random, host_index: int) -> str:
    cols = []
    for v in _VMWARE_CPU_OBSERVED:
        if "." in v:
            base = float(v)
            cols.append(str(round(rng.uniform(0, max(base * 2, 0.0)), 2)) if base else "0.0")
        else:
            base = int(v)
            cols.append(str(int(rng.uniform(base * 0.5, base * 1.5))) if base else "0")
    moid = "host-%d" % (80 + host_index)
    host_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, "%s/%s" % (VMWARE_VCENTER_HOST, moid)))
    return "\t".join([moid, host_uuid, "aggregated", _SAMP_INT] + cols)


def vmware_perf_cpu_entries(count: int) -> List[LogEntry]:
    rng = random.Random()
    out = []
    for n in range(count):
        out.append(LogEntry(timestamp=datetime.now(timezone.utc).isoformat(), device_id=VMWARE_VCENTER_HOST, src_ip="0.0.0.0", dest_ip="0.0.0.0", protocol="n/a", duration="0ms",
                            action="collected", signature="vmware:perf:cpu", status="normal", raw_log=vmware_cpu_row(rng, n % 4), node_type="vcenter", node_id=VMWARE_VCENTER_HOST,
                            vendor="vmware", sourcetype=VMWARE_CPU_SOURCETYPE, hec_source=VMWARE_CPU_SOURCE, hec_host=VMWARE_VCENTER_HOST))
    return out


# ------------------------------------------------------------------ Cisco IOS XR metrics for the documented cisco_metrics series
IOSXR_METRIC_PROFILE = "iosxr_cisco_metrics"
_GC_PATH = "Cisco-IOS-XR-infra-statsd-oper:/infra-statistics/interfaces/interface/generic-counters"
_DR_PATH = "Cisco-IOS-XR-infra-statsd-oper:/infra-statistics/interfaces/interface/data-rate"
_CPU_PATH = "Cisco-IOS-XR-wdsysmon-fd-oper:system-monitoring/cpu-utilization"
# Observed on the reference instance (mcatalog by metric_name, mstats min/max over one hour): dimensions per metric, and value ranges. Series that were constant 0
# are emitted as 0. Interface names are observed values; node_name and subscription are observed values.
INTERFACES = ("FortyGigE0/0/1/0", "FortyGigE0/0/1/1", "GigabitEthernet0/0/0/20", "GigabitEthernet0/0/0/21.100")
NODES = ("0/RP0/CPU0", "0/0/CPU0")
SUBSCRIPTION = "health"
_BW = {"FortyGigE": 40000000, "GigabitEthernet": 1000000}      # kbit/s; both inside the observed 0..100000000 range
DEVICE_ADDRESSES = ("192.0.2.171", "192.0.2.172")


def _plan():
    p = []
    for i in INTERFACES:
        p += [("gc", i), ("dr", i)]
    p += [("cpu", n) for n in NODES]
    return p


_XR_LOCK = threading.Lock()
_XR_STATE: Dict[str, object] = {"cursor": 0, "ctr": {}}


def iosxr_metric_entries(count: int) -> List[LogEntry]:
    """One HEC metric event per (device, path group): generic-counters and data-rate per interface (interface_generic_counters.*), total CPU per node (native name).
    Counters are cumulative and strictly increasing per (device, interface), and that state lives for the whole process: a streaming run asks for a few events at a time,
    so a per-call state would restart the counters at every chunk and a counter would appear to go backwards. Dimensions are exactly the observed ones (plus netspout_*
    bookkeeping added by the dispatcher)."""
    rng = random.Random()
    plan = _plan()
    out = []
    with _XR_LOCK:
        ctr = _XR_STATE["ctr"]
        for _ in range(count):
            n = _XR_STATE["cursor"]
            _XR_STATE["cursor"] = n + 1
            kind, key = plan[n % len(plan)]
            di = (n // len(plan)) % len(DEVICE_ADDRESSES)
            device, addr = "xr-edge-%02d" % (di + 1), DEVICE_ADDRESSES[di]
            if kind == "gc":
                c = ctr.setdefault((device, key), {"pr": rng.randint(10**6, 10**8), "ps": rng.randint(10**6, 10**8), "br": rng.randint(10**9, 10**11), "bs": rng.randint(10**9, 10**11)})
                dp = rng.randint(10**3, 10**5)
                c["pr"] += dp
                c["ps"] += rng.randint(10**3, 10**5)
                c["br"] += int(dp * rng.uniform(600, 1100))               # observed bytes/packet ratio of the series is about 875
                c["bs"] += int(rng.randint(10**3, 10**5) * rng.uniform(600, 1100))
                f = {"interface_name": key, "path": _GC_PATH,
                     "metric_name:interface_generic_counters.packets_received": c["pr"], "metric_name:interface_generic_counters.packets_sent": c["ps"],
                     "metric_name:interface_generic_counters.bytes_received": c["br"], "metric_name:interface_generic_counters.bytes_sent": c["bs"],
                     "metric_name:interface_generic_counters.input_drops": 0, "metric_name:interface_generic_counters.output_drops": 0,
                     "metric_name:interface_generic_counters.input_errors": 0, "metric_name:interface_generic_counters.output_errors": 0}
            elif kind == "dr":
                bw = next(v for k, v in _BW.items() if key.startswith(k))
                f = {"interface_name": key, "path": _DR_PATH, "metric_name:interface_generic_counters.bandwidth": bw,
                     "metric_name:interface_generic_counters.input_load": rng.randint(0, 9), "metric_name:interface_generic_counters.output_load": rng.randint(0, 29)}
            else:
                f = {"node_name": key, "path": _CPU_PATH, "subscription": SUBSCRIPTION,
                     _m("total_cpu_one_minute"): rng.randint(1, 11), _m("total_cpu_five_minute"): rng.randint(1, 7), _m("total_cpu_fifteen_minute"): rng.randint(1, 6)}
            f = {k: (float(v) if k.startswith("metric_name:") else v) for k, v in f.items()}
            out.append(LogEntry(timestamp=datetime.now(timezone.utc).isoformat(), device_id=device, src_ip=addr, dest_ip="0.0.0.0", protocol="n/a", duration="0ms", action="streamed",
                                signature="iosxr_" + kind, status="normal", raw_log=json.dumps({"fields": f}), node_type="router", node_id=device, vendor="cisco_ios",
                                sourcetype="cisco:ios:mdt:metric", hec_source=addr, metric_profile=IOSXR_METRIC_PROFILE))
    return out


def _m(leaf: str) -> str:
    return "metric_name:%s.%s" % (_CPU_PATH, leaf)


# ------------------------------------------------------------------ Palo Alto pan:threat / pan:system for Generate Data
# Generate Data used two fixed YAML lines for each of these sourcetypes: the dates were fixed text (2026/09/18) and, for threat, a column was missing (the add-on's severity and direction regex missed).
# PanOsGenerator is what the paloalto scenarios already use; its columns line up with the add-on's own field lists (checked live in Phase 10).
PAN_TRAFFIC_SOURCETYPE, PAN_THREAT_SOURCETYPE, PAN_SYSTEM_SOURCETYPE = "pan:traffic", "pan:threat", "pan:system"


def _pan_entries(log_type: str, count: int) -> List[LogEntry]:
    from netspout_core.panos_generator import PHASES, PanOsGenerator, to_log_entry
    gen = PanOsGenerator(base_time=datetime.now(timezone.utc) - timedelta(seconds=count))
    out = []
    for i in range(count):
        out += [to_log_entry(r) for r in gen.generate(log_type, 1, phase=PHASES[i % len(PHASES)])]
        gen.base_time += timedelta(seconds=1)
    return out


def pan_traffic_entries(count: int) -> List[LogEntry]:
    return _pan_entries("TRAFFIC", count)


def pan_threat_entries(count: int) -> List[LogEntry]:
    return _pan_entries("THREAT", count)


def pan_system_entries(count: int) -> List[LogEntry]:
    return _pan_entries("SYSTEM", count)
