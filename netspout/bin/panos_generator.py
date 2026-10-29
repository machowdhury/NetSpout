# =========================================================================
# AUTO-GENERATED PACKAGED COPY — DO NOT EDIT DIRECTLY!
# Authoritative Source of Truth: src/netspout_core/panos_generator.py
# Re-generate using: python3 scripts/sync_core.py
# =========================================================================
"""Native PAN-OS syslog generator for PulseForge.

Emits *native* Palo Alto Networks PAN-OS CSV syslog records -- the format a PAN-OS
firewall forwards over syslog/UDP 514 -- not LEEF and not CEF. LEEF/CEF are optional,
customer-configured QRadar/ArcSight export templates; if they are ever needed they
must come from a separately named generator and must never be labelled native PAN-OS.

Field layout is pinned to the repository's own byte-frozen reference samples in
``netspout/appserver/static/samples/pan-{traffic,threat,system}/``::

    pan:traffic -> 54 fields
    pan:threat  -> 45 fields
    pan:system  -> 17 fields

Sourcetypes are the canonical Splunk Add-on names (``pan:traffic`` / ``pan:threat`` /
``pan:system``) already present in ``catalog/sourcetypes.json``. The invented
``paloalto:*`` form is not used by this module.

Determinism: every value is drawn from a seeded ``random.Random``. Same seed + same
phase plan + same base time => byte-stable output.

No customer data: external addresses come from RFC 5737 documentation space, internal
addresses from RFC 1918. No credentials appear anywhere in generated output.
"""
from __future__ import annotations

import csv
import io
import random
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Sequence

PAN_OS_VERSION = "10.2"
CONFIG_VERSION = "2304"

#: PAN-OS syslog timestamp format: slash date, space, second precision
#: (verified from the byte content of the frozen reference samples).
_TS_FMT = "%Y/%m/%d %H:%M:%S"

# ---------------------------------------------------------------------------
# Pinned field layout (indices are positional in the emitted CSV record)
# ---------------------------------------------------------------------------

TRAFFIC_FIELDS: Sequence[str] = (
    "future_use_1", "receive_time", "serial_number", "type", "threat_content_type",
    "config_version", "generated_time", "src_ip", "dst_ip", "nat_src_ip", "nat_dst_ip",
    "rule_name", "src_user", "dst_user", "application", "virtual_system",
    "source_zone", "destination_zone", "inbound_interface", "outbound_interface",
    "log_action", "time_logged_only", "session_id", "repeat_count", "src_port",
    "dst_port", "nat_src_port", "nat_dst_port", "flags", "protocol", "action",
    "total_bytes", "bytes_sent", "bytes_received", "packets", "start_time",
    "elapsed_time", "category", "stub_vmg", "sequence_number", "action_flags",
    "dest_boundary_policy", "source_country", "dst_overridden",
    "packets_sent", "packets_received", "session_end_reason", "dg_hier_level_1",
    "dg_hier_level_2", "dg_hier_level_3", "dg_hier_level_4", "virtual_system_name",
    "device_name", "action_source",
)

THREAT_FIELDS: Sequence[str] = (
    "future_use_1", "receive_time", "serial_number", "type", "threat_content_type",
    "config_version", "generated_time", "src_ip", "dst_ip", "nat_src_ip", "nat_dst_ip",
    "rule_name", "src_user", "dst_user", "application", "virtual_system",
    "source_zone", "destination_zone", "inbound_interface", "outbound_interface",
    "log_action", "time_logged_only", "session_id", "repeat_count", "src_port",
    "dst_port", "nat_src_port", "nat_dst_port", "flags", "protocol", "action",
    "url_filename", "threat_name", "category", "severity", "direction",
    "sequence_number", "action_flags", "source_location", "destination_location",
    "method", "tunnel_id_im_si", "content_type", "provider_group", "device_name",
)

SYSTEM_FIELDS: Sequence[str] = (
    "future_use_1", "receive_time", "serial_number", "type", "threat_content_type",
    "config_version", "generated_time", "src_ip", "dst_ip", "operation",
    "database_operation_number", "number_of_objects_updated", "module", "severity",
    "description", "sequence_number", "action_flags",
)

#: Canonical field counts, derived from the pinned layout (single source of truth).
FIELD_COUNTS: Dict[str, int] = {
    "TRAFFIC": len(TRAFFIC_FIELDS),
    "THREAT": len(THREAT_FIELDS),
    "SYSTEM": len(SYSTEM_FIELDS),
}

# ---------------------------------------------------------------------------
# Vocabularies (PAN-OS documented value sets)
# ---------------------------------------------------------------------------

TRAFFIC_SUBTYPES = ("start", "end", "drop", "deny")
TRAFFIC_ACTIONS = ("allow", "deny", "drop", "reset-both", "reset-client", "reset-server")
THREAT_SUBTYPES = (
    "vulnerability", "spyware", "virus", "wildfire", "url", "data",
    "file", "flood", "packet", "scan", "credential-violation",
)
THREAT_SEVERITIES = ("informational", "low", "medium", "high", "critical")
THREAT_ACTIONS = ("alert", "drop", "reset-both", "reset-client", "reset-server", "blockip")
DIRECTIONS = ("client-to-server", "server-to-client", "client-to-client", "unknown")
PROTOCOLS = ("tcp", "udp")
APPLICATIONS = (
    "web-browsing", "ssl", "ms-update", "dns-base", "ssh", "ssh",
    " outlook-web-access", "ms-dce-rpc", "unknown-tcp", "unknown-udp",
)
RULES = (
    "Perimeter-Web-Access", "Perimeter-Inspection", "Perimeter-Drop-Rule",
    "Corp-Outbound-Allow", "DMZ-Inbound-HTTP",
)
END_REASONS = ("fin-reset", "age-out", "tcp-reset", "policy-deny", "idle-age-out")

# Documentation / test ranges only -- never customer data.
EXTERNAL_IPS = (
    "203.0.113.10", "203.0.113.44", "198.51.100.150", "198.51.100.201",
    "192.0.2.77", "192.0.2.140",
)
INTERNAL_IPS = (
    "10.0.10.80", "10.0.10.81", "10.0.20.25", "10.0.30.11", "172.16.4.9",
    "192.168.5.30",
)
USERS = ("jdoe", "asmith", "svc-update", "klee", "")

#: Lifecycle phases used by the threat-investigation scenario.
PHASES: Sequence[str] = (
    "baseline", "suspicious", "detection", "containment", "recovery",
)


@dataclass
class PanLogRecord:
    """One generated PAN-OS syslog record, pre-dispatch shape."""

    log_type: str
    sourcetype: str
    host: str
    source: str
    index: str
    raw: str
    fields: Dict[str, Any]
    phase: str
    event_time: datetime

    def as_dict(self) -> Dict[str, Any]:
        return {
            "log_type": self.log_type,
            "sourcetype": self.sourcetype,
            "host": self.host,
            "source": self.source,
            "index": self.index,
            "raw": self.raw,
            "fields": self.fields,
            "phase": self.phase,
            "time": self.event_time.isoformat(),
        }


def _csv_join(values: Sequence[str]) -> str:
    """Render PAN-OS CSV: quote only when needed (commas/quotes inside values)."""
    buf = io.StringIO()
    csv.writer(buf, lineterminator="", quoting=csv.QUOTE_MINIMAL).writerow(values)
    return buf.getvalue()


def _fmt(ts: datetime) -> str:
    return ts.strftime(_TS_FMT)


class PanOsGenerator:
    """Deterministic native PAN-OS traffic / threat / system log generator.

    ``count`` is honoured exactly: ``generate(..., count=N)`` returns N records or
    raises. This is the behaviour the ``AuthenticPaloAltoGenerator`` never delivered.
    """

    SOURCETYPE_BY_TYPE = {
        "TRAFFIC": "pan:traffic",
        "THREAT": "pan:threat",
        "SYSTEM": "pan:system",
    }

    def __init__(
        self,
        seed: Optional[int] = None,
        devices: Optional[Sequence[str]] = None,
        default_index: str = "idx_network_ops",
        base_time: Optional[datetime] = None,
    ) -> None:
        self.seed = seed
        self.rng = random.Random(seed)
        self.devices = list(devices) if devices else ["PA-5250", "PA-3260"]
        self.default_index = default_index
        self.base_time = (base_time or datetime.now(timezone.utc)).replace(microsecond=0)
        self._serials = ["001801000001", "001801000002", "001801000003"]
        self._session = 98421
        self._sequence = 12345678

    # -- helpers ----------------------------------------------------------
    def _device_host(self) -> str:
        return f"{self.rng.choice(self.devices).lower()}-01.lab.example"

    def _next_session(self) -> int:
        self._session += 1
        return self._session

    def _next_sequence(self) -> int:
        self._sequence += 1
        return self._sequence

    def _ts(self, offset_seconds: int) -> datetime:
        return self.base_time + timedelta(seconds=offset_seconds)

    @staticmethod
    def _phase_bias(phase: str) -> Dict[str, float]:
        """Per-phase probabilities that make a scenario read like a real incident."""
        return {
            # phase: (bad_action_p, threat_p, drop_p, volume_bytes_max)
            "baseline": {"bad": 0.05, "threat": 0.02, "drop": 0.05, "bytes": 4096},
            "suspicious": {"bad": 0.35, "threat": 0.25, "drop": 0.30, "bytes": 32768},
            "detection": {"bad": 0.70, "threat": 0.85, "drop": 0.65, "bytes": 65536},
            "containment": {"bad": 0.90, "threat": 0.60, "drop": 0.95, "bytes": 8192},
            "recovery": {"bad": 0.10, "threat": 0.05, "drop": 0.10, "bytes": 4096},
        }[phase]

    # -- traffic ----------------------------------------------------------
    def generate_traffic(
        self, count: int = 1, phase: str = "baseline", subtype: Optional[str] = None
    ) -> List[PanLogRecord]:
        if count < 0:
            raise ValueError("count must be >= 0")
        if phase not in PHASES:
            raise ValueError(f"unknown phase {phase!r}; expected one of {PHASES}")
        bias = self._phase_bias(phase)
        out: List[PanLogRecord] = []
        for i in range(count):
            ts = self._ts(i * self.rng.randint(1, 5))
            bad = self.rng.random() < bias["bad"]
            action = (
                self.rng.choice(("deny", "drop", "reset-both"))
                if bad
                else "allow"
            )
            st = subtype or (
                "end" if action == "allow" else self.rng.choice(("drop", "deny"))
            )
            src, dst = (
                (self.rng.choice(EXTERNAL_IPS), self.rng.choice(INTERNAL_IPS))
                if bad
                else (self.rng.choice(INTERNAL_IPS), self.rng.choice(EXTERNAL_IPS))
            )
            total = self.rng.randint(64, int(bias["bytes"]))
            sent = total // 2
            elapsed = self.rng.randint(0, 300) if action == "allow" else 0
            rule = "Perimeter-Drop-Rule" if bad else "Perimeter-Web-Access"
            values = [
                "1", _fmt(ts), self.rng.choice(self._serials), "TRAFFIC", st,
                CONFIG_VERSION, _fmt(ts), src, dst, "0.0.0.0", "0.0.0.0",
                rule, self.rng.choice(USERS), "", self.rng.choice(APPLICATIONS).strip(),
                "vsys1", "untrust" if bad else "trust", "trust" if bad else "untrust",
                "ethernet1/1", "ethernet1/2", "log-forwarder", _fmt(ts),
                str(self._next_session()), "1", str(self.rng.randint(49152, 65535)),
                self.rng.choice(("80", "443", "53", "22")), "0", "0", "0x0",
                self.rng.choice(PROTOCOLS), action, str(total), str(sent),
                str(total - sent), str(self.rng.randint(1, 40)), _fmt(ts),
                str(elapsed), "any", "0", str(self._next_sequence()), "0x0",
                "10.0.0.0-10.255.255.255", self.rng.choice(("US", "NL", "DE")),
                "0", str(self.rng.randint(1, 20)), str(self.rng.randint(1, 20)),
                self.rng.choice(END_REASONS), "0", "0", "0", "0", "",
                self.rng.choice(self.devices), "from-policy",
            ]
            raw = _csv_join(values)
            host = self._device_host()
            out.append(
                PanLogRecord(
                    log_type="TRAFFIC",
                    sourcetype=self.SOURCETYPE_BY_TYPE["TRAFFIC"],
                    host=host,
                    source="syslog:udp:514",
                    index=self.default_index,
                    raw=raw,
                    fields={
                        "pan_action": action, "pan_srcip": src, "pan_dstip": dst,
                        "pan_rule": rule, "pan_app": values[14],
                        "pan_bytes": total, "pan_subtype": st,
                    },
                    phase=phase,
                    event_time=ts,
                )
            )
        return out

    # -- threat -----------------------------------------------------------
    def generate_threat(
        self, count: int = 1, phase: str = "detection", severity: Optional[str] = None
    ) -> List[PanLogRecord]:
        if count < 0:
            raise ValueError("count must be >= 0")
        if phase not in PHASES:
            raise ValueError(f"unknown phase {phase!r}; expected one of {PHASES}")
        bias = self._phase_bias(phase)
        out: List[PanLogRecord] = []
        for i in range(count):
            ts = self._ts(i * self.rng.randint(1, 4))
            sev = severity or self.rng.choice(THREAT_SEVERITIES)
            if bias["threat"] > 0.5 and self.rng.random() < 0.5:
                sev = self.rng.choice(("high", "critical"))
            subtype = self.rng.choice(THREAT_SUBTYPES)
            action = self.rng.choice(THREAT_ACTIONS)
            src = self.rng.choice(EXTERNAL_IPS)
            dst = self.rng.choice(INTERNAL_IPS)
            threat_name = self.rng.choice((
                "Apache Log4j Remote Code Execution(30845)",
                "Microsoft Windows Kerberos Heap Overflow(29832)",
                "Phishing known-bad URL(46009)",
                "ET TROJAN Possible C2 Beacon(58232)",
            ))
            values = [
                "1", _fmt(ts), self.rng.choice(self._serials), "THREAT", subtype,
                CONFIG_VERSION, _fmt(ts), src, dst, "0.0.0.0", "0.0.0.0",
                "Perimeter-Inspection", self.rng.choice(USERS), "",
                self.rng.choice(APPLICATIONS).strip(), "vsys1", "untrust", "trust",
                "ethernet1/1", "ethernet1/2", "log-forwarder", _fmt(ts),
                str(self._next_session()), "1", str(self.rng.randint(49152, 65535)),
                self.rng.choice(("80", "443")), "0", "0", "0x0",
                self.rng.choice(PROTOCOLS), action,
                self.rng.choice(("/payload.bin", "/index.html", "example.test")),
                threat_name, "any", sev, self.rng.choice(DIRECTIONS),
                str(self._next_sequence()), "0x0",
                "10.0.0.0-10.255.255.255", "US", "0", "", "0", "",
                self.rng.choice(self.devices),
            ]
            raw = _csv_join(values)
            out.append(
                PanLogRecord(
                    log_type="THREAT",
                    sourcetype=self.SOURCETYPE_BY_TYPE["THREAT"],
                    host=self._device_host(),
                    source="syslog:udp:514",
                    index=self.default_index,
                    raw=raw,
                    fields={
                        "pan_threat_severity": sev, "pan_threat_name": threat_name,
                        "pan_action": action, "pan_srcip": src, "pan_dstip": dst,
                    },
                    phase=phase,
                    event_time=ts,
                )
            )
        return out

    # -- system -----------------------------------------------------------
    def generate_system(
        self, count: int = 1, phase: str = "baseline", module: Optional[str] = None
    ) -> List[PanLogRecord]:
        if count < 0:
            raise ValueError("count must be >= 0")
        if phase not in PHASES:
            raise ValueError(f"unknown phase {phase!r}; expected one of {PHASES}")
        modules = ("general", "globalprotect", "vpn", "ha", "config", "storage")
        sev_by_phase = {
            "baseline": "informational", "suspicious": "warning",
            "detection": "warning", "containment": "critical",
            "recovery": "informational",
        }
        out: List[PanLogRecord] = []
        for i in range(count):
            ts = self._ts(i * self.rng.randint(2, 6))
            mod = module or self.rng.choice(modules)
            sev = sev_by_phase[phase]
            desc = {
                "general": f"System monitoring check done: category=general, result=passed ({phase})",
                "globalprotect": "GlobalProtect gateway client connection established",
                "vpn": "IKE tunnel negotiated successfully",
                "ha": "HA peer heartbeat received",
                "config": "Config committed by admin; change validated",
                "storage": "Disk utilization within threshold",
            }[mod]
            values = [
                "1", _fmt(ts), self.rng.choice(self._serials), "SYSTEM", mod,
                CONFIG_VERSION, _fmt(ts), "", "firewall-management", "gateway-agent",
                "0", "0", mod, sev, desc, str(self._next_sequence()), "0x0",
            ]
            raw = _csv_join(values)
            out.append(
                PanLogRecord(
                    log_type="SYSTEM",
                    sourcetype=self.SOURCETYPE_BY_TYPE["SYSTEM"],
                    host=self._device_host(),
                    source="syslog:udp:514",
                    index=self.default_index,
                    raw=raw,
                    fields={"pan_module": mod, "pan_severity": sev,
                            "pan_description": desc},
                    phase=phase,
                    event_time=ts,
                )
            )
        return out

    # -- convenience ------------------------------------------------------
    def generate(self, log_type: str, count: int = 1, phase: str = "baseline", **kw: Any) -> List[PanLogRecord]:
        log_type = log_type.upper()
        if log_type == "TRAFFIC":
            return self.generate_traffic(count=count, phase=phase, subtype=kw.get("subtype"))
        if log_type == "THREAT":
            return self.generate_threat(count=count, phase=phase, severity=kw.get("severity"))
        if log_type == "SYSTEM":
            return self.generate_system(count=count, phase=phase, module=kw.get("module"))
        raise ValueError(f"unsupported PAN-OS log type {log_type!r}")

    @staticmethod
    def split_native_csv(raw: str) -> List[str]:
        """Parse a native record back into positional fields (used by tests)."""
        return next(csv.reader(io.StringIO(raw)))


def to_log_entry(rec: "PanLogRecord", correlation_id: str = ""):
    """Bridge a native PAN-OS record onto the production ``LogEntry`` model.

    Using ``LogEntry`` is what makes the record flow through the existing
    ``TelemetryDispatcher`` path (index/sourcetype routing, run-id tagging)
    instead of requiring a parallel dispatch framework.
    """
    from netspout_core.models import LogEntry, NodeType

    fields = PanOsGenerator.split_native_csv(rec.raw)
    log_type = rec.log_type
    if log_type == "TRAFFIC":
        src_ip, dest_ip = fields[7], fields[8]
        protocol, action = fields[29], fields[30]
        signature = f"{fields[14]}:{fields[11]}"
        status = "normal" if action == "allow" else "blocked"
        duration = f"{fields[36]}s"
    elif log_type == "THREAT":
        src_ip, dest_ip = fields[7], fields[8]
        protocol, action = fields[29], fields[30]
        signature = fields[32]
        status = "breached" if fields[33] in ("high", "critical") else "alerted"
        duration = "0s"
    else:
        src_ip, dest_ip = fields[7] or "0.0.0.0", fields[8]
        protocol, action = "n/a", fields[9]
        signature = fields[14]
        status = "normal" if fields[13] == "informational" else "degraded"
        duration = "0s"

    return LogEntry(
        timestamp=rec.event_time.isoformat(),
        device_id=rec.host,
        src_ip=src_ip,
        dest_ip=dest_ip,
        protocol=protocol,
        duration=duration,
        action=action,
        signature=signature,
        status=status,
        raw_log=rec.raw,
        node_type=NodeType.FIREWALL.value,
        node_id=rec.host,
        vendor="palo_alto",
        sourcetype=rec.sourcetype,
        netspout_parent_event_id=correlation_id or None,
        netspout_ground_truth=(
            f"pan/{log_type}/{rec.phase}/{fields[30] if log_type != 'SYSTEM' else fields[13]}"
        ),
    )
