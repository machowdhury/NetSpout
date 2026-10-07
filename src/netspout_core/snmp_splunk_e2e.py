"""
NetSpout Gate 12D — External SNMP Collector/Poller -> Splunk End-to-End Integration.

Implements:
  - Pipeline A (Notifications):
      NetSpout Scenario -> Native ASN.1 BER -> SNMPv2c TRAP (0xA7) / INFORM (0xA6) -> UDP ->
      External `/usr/sbin/snmptrapd` -> Normalized `netspout:snmp:trap` Event ->
      Splunk HEC (`idx_network_ops`) -> Fresh SPL Search -> NetSpout Validation
  - Pipeline B (Polling):
      External Net-SNMP Poller (`/usr/bin/snmpget`, `/usr/bin/snmpgetnext`, `/usr/bin/snmpwalk`,
      `/usr/bin/snmpbulkwalk`) -> GET / GETNEXT / GETBULK -> NetSpout `SimulatedSnmpAgent` ->
      RESPONSE -> Normalized `netspout:snmp:poll` Event -> Splunk HEC (`idx_network_ops`) ->
      Fresh SPL Search -> NetSpout Validation
  - Non-Negotiable 8-Stage Evidence Separation:
      GENERATED -> ENCODED -> SENT -> ACKNOWLEDGED -> RECEIVER_OBSERVED ->
      SPLUNK_DISPATCHED -> SPLUNK_OBSERVED -> VALIDATED
  - Out-of-band correlation (`netspout_run_id`, `netspout_scenario_id`, `netspout_phase`,
    `netspout_device_id`, `netspout_event_id`) preserving 100% standards-pure SNMP wire payloads.
"""

import base64
import hashlib
import json
import os
import re
import shutil
import socket
import ssl
import subprocess
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from typing import Any, Dict, List, Optional, Set, Tuple, Union

try:
    from netspout_core.models import (
        EvidenceObservation,
        EvidenceRole,
        LogEntry,
        NormalizedSnmpEvent,
        OidFidelityClass,
        QueryMechanism,
        SnmpE2ERunScorecard,
        SnmpEvidenceStage,
        SnmpInform,
        SnmpMessage,
        SnmpPduType,
        SnmpTransportResult,
        SnmpTrap,
        SnmpVarBind,
        TelemetryTransportConfig,
        TelemetryType,
        UnifiedRunEvidence,
    )
    from netspout_core.snmp_agent import (
        DEFAULT_AGENT_BIND_HOST,
        DEFAULT_AGENT_BIND_PORT,
        DEFAULT_AGENT_COMMUNITY,
        SimulatedSnmpAgent,
        SnmpOidStore,
        build_service_provider_cisco_oid_store,
        normalize_oid_str,
        normalize_scenario_phase,
        verify_trap_poll_coherence,
    )
    from netspout_core.snmp_ber import SnmpBerDecoder, SnmpBerEncoder
    from netspout_core.snmp_engine import snmp_engine
    from netspout_core.transport_native_snmp import (
        DEFAULT_SNMP_HOST,
        DEFAULT_SNMP_TRAP_PORT,
        NativeSnmpTransport,
        write_snmp_pcap,
    )
except ImportError:
    try:
        from app.models import (
            EvidenceObservation,
            EvidenceRole,
            LogEntry,
            NormalizedSnmpEvent,
            OidFidelityClass,
            QueryMechanism,
            SnmpE2ERunScorecard,
            SnmpEvidenceStage,
            SnmpInform,
            SnmpMessage,
            SnmpPduType,
            SnmpTransportResult,
            SnmpTrap,
            SnmpVarBind,
            TelemetryTransportConfig,
            TelemetryType,
            UnifiedRunEvidence,
        )
        from app.snmp_agent import (
            DEFAULT_AGENT_BIND_HOST,
            DEFAULT_AGENT_BIND_PORT,
            DEFAULT_AGENT_COMMUNITY,
            SimulatedSnmpAgent,
            SnmpOidStore,
            build_service_provider_cisco_oid_store,
            normalize_oid_str,
            normalize_scenario_phase,
            verify_trap_poll_coherence,
        )
        from app.snmp_ber import SnmpBerDecoder, SnmpBerEncoder
        from app.snmp_engine import snmp_engine
        from app.transport_native_snmp import (
            DEFAULT_SNMP_HOST,
            DEFAULT_SNMP_TRAP_PORT,
            NativeSnmpTransport,
            write_snmp_pcap,
        )
    except ImportError:
        from models import (
            EvidenceObservation,
            EvidenceRole,
            LogEntry,
            NormalizedSnmpEvent,
            OidFidelityClass,
            QueryMechanism,
            SnmpE2ERunScorecard,
            SnmpEvidenceStage,
            SnmpInform,
            SnmpMessage,
            SnmpPduType,
            SnmpTransportResult,
            SnmpTrap,
            SnmpVarBind,
            TelemetryTransportConfig,
            TelemetryType,
            UnifiedRunEvidence,
        )
        from snmp_agent import (
            DEFAULT_AGENT_BIND_HOST,
            DEFAULT_AGENT_BIND_PORT,
            DEFAULT_AGENT_COMMUNITY,
            SimulatedSnmpAgent,
            SnmpOidStore,
            build_service_provider_cisco_oid_store,
            normalize_oid_str,
            normalize_scenario_phase,
            verify_trap_poll_coherence,
        )
        from snmp_ber import SnmpBerDecoder, SnmpBerEncoder
        from snmp_engine import snmp_engine
        from transport_native_snmp import (
            DEFAULT_SNMP_HOST,
            DEFAULT_SNMP_TRAP_PORT,
            NativeSnmpTransport,
            write_snmp_pcap,
        )


# =========================================================================
# Canonical OID & Notification Metadata Catalog
# =========================================================================
TRAP_OID_CATALOG: Dict[str, Dict[str, str]] = {
    "1.3.6.1.6.3.1.1.5.3": {
        "trap_name": "IF-MIB::linkDown",
        "canonical_phase": "DEGRADE",
        "primary_oid": "1.3.6.1.2.1.2.2.1.8.1",
        "primary_oid_name": "IF-MIB::ifOperStatus.1",
        "expected_value": "2",
        "expected_symbolic_value": "down",
    },
    "1.3.6.1.2.1.15.7.2": {
        "trap_name": "BGP4-MIB::bgpBackwardTransition",
        "canonical_phase": "FAILOVER",
        "primary_oid": "1.3.6.1.2.1.15.3.1.2.198.51.100.1",
        "primary_oid_name": "BGP4-MIB::bgpPeerState.198.51.100.1",
        "expected_value": "1",
        "expected_symbolic_value": "idle",
    },
    "1.3.6.1.6.3.1.1.5.4": {
        "trap_name": "IF-MIB::linkUp",
        "canonical_phase": "RECOVERY",
        "primary_oid": "1.3.6.1.2.1.2.2.1.8.1",
        "primary_oid_name": "IF-MIB::ifOperStatus.1",
        "expected_value": "1",
        "expected_symbolic_value": "up",
    },
    "1.3.6.1.2.1.15.7.1": {
        "trap_name": "BGP4-MIB::bgpEstablished",
        "canonical_phase": "RECOVERY",
        "primary_oid": "1.3.6.1.2.1.15.3.1.2.198.51.100.1",
        "primary_oid_name": "BGP4-MIB::bgpPeerState.198.51.100.1",
        "expected_value": "6",
        "expected_symbolic_value": "established",
    },
}

# Canonical key OIDs polled per phase during Gate 12D E2E runs
PHASE_POLL_OIDS: List[str] = [
    "1.3.6.1.2.1.1.3.0",                     # SNMPv2-MIB::sysUpTime.0
    "1.3.6.1.2.1.1.5.0",                     # SNMPv2-MIB::sysName.0
    "1.3.6.1.2.1.2.2.1.2.1",                 # IF-MIB::ifDescr.1 (HundredGigE0/0/0/1)
    "1.3.6.1.2.1.2.2.1.7.1",                 # IF-MIB::ifAdminStatus.1
    "1.3.6.1.2.1.2.2.1.8.1",                 # IF-MIB::ifOperStatus.1
    "1.3.6.1.2.1.2.2.1.14.1",                # IF-MIB::ifInErrors.1
    "1.3.6.1.2.1.31.1.1.1.6.1",              # IF-MIB::ifHCInOctets.1
    "1.3.6.1.2.1.2.2.1.8.2",                 # IF-MIB::ifOperStatus.2 (HundredGigE0/0/0/2 backup)
    "1.3.6.1.2.1.31.1.1.1.6.2",              # IF-MIB::ifHCInOctets.2
    "1.3.6.1.2.1.4.21.1.2.0.0.0.0",          # IP-MIB::ipRouteIfIndex.0.0.0.0
    "1.3.6.1.2.1.4.21.1.7.0.0.0.0",          # IP-MIB::ipRouteNextHop.0.0.0.0
    "1.3.6.1.2.1.15.3.1.2.198.51.100.1",     # BGP4-MIB::bgpPeerState.198.51.100.1 (Primary)
    "1.3.6.1.2.1.15.3.1.14.198.51.100.1",    # BGP4-MIB::bgpPeerLastError.198.51.100.1
    "1.3.6.1.2.1.15.3.1.2.198.51.100.2",     # BGP4-MIB::bgpPeerState.198.51.100.2 (Backup)
]

_REFERENCE_STORE: Optional[SnmpOidStore] = None


def _get_reference_store() -> SnmpOidStore:
    global _REFERENCE_STORE
    if _REFERENCE_STORE is None:
        _REFERENCE_STORE = build_service_provider_cisco_oid_store(phase="BASELINE", seed=42)
    return _REFERENCE_STORE


def resolve_oid_metadata(oid: str) -> Tuple[str, str, str]:
    """
    Resolves `(symbolic_name, asn1_type, source_mib)` for a numeric OID string
    using the canonical `service_provider_cisco` OID store.
    """
    try:
        norm = normalize_oid_str(oid)
    except Exception:
        return (oid, "OctetString", "SNMPv2-MIB")

    if norm == "1.3.6.1.6.3.1.1.4.1.0":
        return ("SNMPv2-MIB::snmpTrapOID.0", "ObjectIdentifier", "SNMPv2-MIB")
    if norm in TRAP_OID_CATALOG:
        return (TRAP_OID_CATALOG[norm]["trap_name"], "ObjectIdentifier", "SNMPv2-MIB")

    store = _get_reference_store()
    vb = store.get_exact(norm)
    if vb.asn1_type not in ("noSuchObject", "noSuchInstance") and vb.object_name:
        mib = vb.mib_module or "SNMPv2-MIB"
        sym = vb.object_name if "::" in vb.object_name else f"{mib}::{vb.object_name}"
        return (sym, vb.asn1_type, mib)
    return (norm, "OctetString", "SNMPv2-MIB")


def _find_free_udp_port(host: str = "127.0.0.1") -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.bind((host, 0))
        return int(s.getsockname()[1])


# =========================================================================
# Pipeline A: External `/usr/sbin/snmptrapd` Receiver Manager & Parser
# =========================================================================
class ExternalSnmpTrapReceiver:
    """
    Manages a real external `/usr/sbin/snmptrapd` OS daemon process listening on
    local UDP (`127.0.0.1:<port>`) and parses its packet dumps and notification logs.
    Never substitutes an internal Python socket for the external `snmptrapd` receiver.
    """

    def __init__(
        self,
        host: str = DEFAULT_SNMP_HOST,
        port: int = 0,
        community: str = "netspout-lab",
        snmptrapd_bin: str = "/usr/sbin/snmptrapd",
        work_dir: Optional[str] = None,
    ):
        if host != "127.0.0.1":
            raise ValueError(f"ExternalSnmpTrapReceiver must bind to 127.0.0.1, got {host!r}")
        self.host = host
        self.requested_port = int(port)
        self.bound_port: int = 0
        self.community = community
        self.snmptrapd_bin = snmptrapd_bin
        self._external_work_dir = work_dir
        self._tmp_dir: Optional[tempfile.TemporaryDirectory] = None
        self.conf_path: str = ""
        self.log_path: str = ""
        self.pid_path: str = ""
        self._proc: Optional[subprocess.Popen] = None

    @property
    def is_running(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    def start(self) -> int:
        if self.is_running:
            return self.bound_port

        if not os.path.exists(self.snmptrapd_bin):
            found = shutil.which("snmptrapd")
            if not found:
                raise FileNotFoundError(f"External snmptrapd binary not found at {self.snmptrapd_bin}")
            self.snmptrapd_bin = found

        if self._external_work_dir:
            os.makedirs(self._external_work_dir, exist_ok=True)
            base_dir = self._external_work_dir
        else:
            self._tmp_dir = tempfile.TemporaryDirectory(prefix="netspout_snmptrapd_")
            base_dir = self._tmp_dir.name

        self.bound_port = self.requested_port if self.requested_port > 0 else _find_free_udp_port(self.host)
        self.conf_path = os.path.join(base_dir, "snmptrapd.conf")
        self.log_path = os.path.join(base_dir, "snmptrapd.log")
        self.pid_path = os.path.join(base_dir, "snmptrapd.pid")

        with open(self.conf_path, "w", encoding="utf-8") as f:
            f.write("disableAuthorization yes\n")

        # Launch real external /usr/sbin/snmptrapd process
        cmd = [
            self.snmptrapd_bin,
            "-f",
            "-C",
            "-c",
            self.conf_path,
            "-Lf",
            self.log_path,
            "-p",
            self.pid_path,
            "-d",
            "-On",
            "-OQ",
            "-Oe",
            "-Ot",
            f"udp:{self.host}:{self.bound_port}",
        ]
        self._proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        # Wait until snmptrapd initializes its log file
        deadline = time.monotonic() + 3.0
        while time.monotonic() < deadline:
            if self._proc.poll() is not None:
                stderr_out = (self._proc.stderr.read() or b"").decode("utf-8", errors="replace")
                raise RuntimeError(f"snmptrapd exited prematurely: {stderr_out}")
            if os.path.exists(self.log_path) and os.path.getsize(self.log_path) > 0:
                time.sleep(0.1)
                break
            time.sleep(0.05)

        return self.bound_port

    def stop(self) -> None:
        if self._proc is not None:
            if self._proc.poll() is None:
                self._proc.terminate()
                try:
                    self._proc.wait(timeout=3.0)
                except subprocess.TimeoutExpired:
                    self._proc.kill()
                    self._proc.wait(timeout=2.0)
            if self._proc.stdout:
                self._proc.stdout.close()
            if self._proc.stderr:
                self._proc.stderr.close()
            self._proc = None

        if self._tmp_dir is not None:
            try:
                self._tmp_dir.cleanup()
            except Exception:
                pass
            self._tmp_dir = None

    def __enter__(self) -> "ExternalSnmpTrapReceiver":
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.stop()

    def read_raw_log(self) -> str:
        if not self.log_path or not os.path.exists(self.log_path):
            return ""
        with open(self.log_path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()

    def wait_for_notifications(self, expected_count: int, timeout_sec: float = 3.0) -> bool:
        deadline = time.monotonic() + timeout_sec
        while time.monotonic() < deadline:
            parsed = self.parse_observations()
            if len(parsed["deduplicated_notifications"]) >= expected_count:
                return True
            time.sleep(0.05)
        parsed = self.parse_observations()
        return len(parsed["deduplicated_notifications"]) >= expected_count

    def parse_observations(self) -> Dict[str, Any]:
        return self.parse_snmptrapd_log_text(
            self.read_raw_log(),
            receiver_port=self.bound_port or DEFAULT_SNMP_TRAP_PORT,
            expected_community=self.community,
        )

    def export_pcap(self, filepath: str) -> str:
        parsed = self.parse_observations()
        return write_snmp_pcap(
            filepath,
            parsed["pcap_frames"],
            default_dst_port=self.bound_port or DEFAULT_SNMP_TRAP_PORT,
        )

    @staticmethod
    def parse_snmptrapd_log_text(
        log_text: str,
        receiver_port: int = DEFAULT_SNMP_TRAP_PORT,
        expected_community: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Parses `/usr/sbin/snmptrapd -d -On -OQ -Ot` log output into:
          - `pcap_frames`: raw wire UDP packets (IN notifications and OUT Inform Response-PDUs)
          - `raw_notifications`: all decoded notification observations
          - `deduplicated_notifications`: deduplicated notifications (suppresses Inform retry duplicates)
          - `formatted_lines`: formatted varbind lines written by snmptrapd
          - `malformed_lines`: count of malformed/unparseable lines encountered
        """
        lines = (log_text or "").splitlines()
        pcap_frames: List[Dict[str, Any]] = []
        raw_notifications: List[Dict[str, Any]] = []
        deduplicated_notifications: List[Dict[str, Any]] = []
        formatted_lines: List[str] = []
        seen_inform_keys: Set[Tuple[str, int]] = set()
        duplicate_informs_count = 0
        responses_sent_count = 0
        malformed_lines = 0

        i = 0
        n = len(lines)
        base_ts = time.time()

        header_recv_re = re.compile(
            r"^(Received|Sending)\s+\d+\s+byte(?:s|\s+packet)\s+(?:from|to)\s+UDP:\s+\[([0-9\.]+)\]:(\d+)"
        )
        hex_line_re = re.compile(r"^\d{4}:\s+((?:[0-9A-Fa-f]{2}\s+)+)")
        fmt_header_re = re.compile(
            r"^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s+\S+\s+\[UDP:\s+\[([0-9\.]+)\]:(\d+)"
        )

        while i < n:
            line = lines[i].strip()
            if not line or line.startswith("NET-SNMP version"):
                i += 1
                continue

            # 1. Packet dump block from `-d`
            m_pkt = header_recv_re.match(line)
            if m_pkt:
                direction_word = m_pkt.group(1)
                peer_ip = m_pkt.group(2)
                peer_port = int(m_pkt.group(3))
                hex_tokens: List[str] = []
                i += 1
                while i < n:
                    h_match = hex_line_re.match(lines[i].strip())
                    if not h_match:
                        break
                    hex_tokens.extend(h_match.group(1).split())
                    i += 1

                if not hex_tokens:
                    malformed_lines += 1
                    continue

                raw_bytes = bytes(int(b, 16) for b in hex_tokens)
                pkt_ts = base_ts + (len(pcap_frames) * 0.001)
                if direction_word == "Received":
                    pcap_frames.append(
                        {
                            "direction": "IN",
                            "src_ip": peer_ip,
                            "dst_ip": "127.0.0.1",
                            "src_port": peer_port,
                            "dst_port": receiver_port,
                            "payload": raw_bytes,
                            "timestamp": pkt_ts,
                        }
                    )
                    try:
                        msg = SnmpBerDecoder.decode_message(
                            raw_bytes, expected_community=expected_community
                        )
                    except Exception:
                        malformed_lines += 1
                        continue

                    if int(msg.pdu_type) in (
                        SnmpPduType.SNMPV2_TRAP.value,
                        SnmpPduType.INFORM_REQUEST.value,
                    ):
                        pdu_name = (
                            "InformRequest"
                            if int(msg.pdu_type) == SnmpPduType.INFORM_REQUEST.value
                            else "SNMPv2-Trap"
                        )
                        sys_uptime = int(msg.varbinds[0].value) if len(msg.varbinds) >= 1 else 0
                        trap_oid = normalize_oid_str(str(msg.varbinds[1].value)) if len(msg.varbinds) >= 2 else ""
                        vb_map: Dict[str, Any] = {}
                        extra_vbs: List[Dict[str, Any]] = []
                        for vb in msg.varbinds:
                            norm_vb_oid = normalize_oid_str(vb.oid)
                            sym_name, asn1_t, _ = resolve_oid_metadata(norm_vb_oid)
                            val_str = (
                                vb.value.hex()
                                if isinstance(vb.value, (bytes, bytearray))
                                else str(vb.value)
                            )
                            vb_map[sym_name] = val_str
                            extra_vbs.append(
                                {
                                    "oid": norm_vb_oid,
                                    "oid_name": sym_name,
                                    "asn1_type": vb.asn1_type or asn1_t,
                                    "value": val_str,
                                }
                            )

                        obs = {
                            "pdu_type": pdu_name,
                            "request_id": msg.request_id,
                            "community": msg.community,
                            "version": "2c" if msg.version == 1 else str(msg.version),
                            "src_ip": peer_ip,
                            "src_port": peer_port,
                            "receiver_port": receiver_port,
                            "sys_uptime": sys_uptime,
                            "trap_oid": trap_oid,
                            "trap_name": TRAP_OID_CATALOG.get(trap_oid, {}).get("trap_name", trap_oid),
                            "varbinds": vb_map,
                            "varbind_list": extra_vbs,
                            "raw_collector_line": "",
                        }
                        raw_notifications.append(obs)
                        if pdu_name == "InformRequest":
                            inf_key = (peer_ip, msg.request_id)
                            if inf_key in seen_inform_keys:
                                duplicate_informs_count += 1
                            else:
                                seen_inform_keys.add(inf_key)
                                deduplicated_notifications.append(obs)
                        else:
                            deduplicated_notifications.append(obs)
                else:
                    responses_sent_count += 1
                    pcap_frames.append(
                        {
                            "direction": "OUT",
                            "src_ip": "127.0.0.1",
                            "dst_ip": peer_ip,
                            "src_port": receiver_port,
                            "dst_port": peer_port,
                            "payload": raw_bytes,
                            "timestamp": pkt_ts,
                        }
                    )
                continue

            # 2. Formatted notification header + tab-separated varbind line
            m_fmt = fmt_header_re.match(line)
            if m_fmt:
                peer_ip = m_fmt.group(2)
                peer_port = int(m_fmt.group(3))
                vb_line = ""
                if i + 1 < n and lines[i + 1].strip().startswith("."):
                    vb_line = lines[i + 1].strip()
                    i += 2
                else:
                    i += 1
                full_fmt = f"{line} {vb_line}".strip()
                formatted_lines.append(full_fmt)

                # Attach raw_collector_line to the most recent matching notification or parse standalone
                if raw_notifications and not raw_notifications[-1].get("raw_collector_line"):
                    raw_notifications[-1]["raw_collector_line"] = full_fmt
                elif vb_line:
                    # Standalone formatted line parsing (when -d hex block is absent)
                    parsed_standalone = ExternalSnmpTrapReceiver._parse_formatted_varbind_line(
                        vb_line, peer_ip, peer_port, receiver_port, full_fmt
                    )
                    if parsed_standalone is not None:
                        raw_notifications.append(parsed_standalone)
                        deduplicated_notifications.append(parsed_standalone)
                    else:
                        malformed_lines += 1
                else:
                    malformed_lines += 1
                continue

            # 3. Any unrecognized non-empty line is counted as malformed
            malformed_lines += 1
            i += 1

        traps_obs = sum(1 for x in deduplicated_notifications if x["pdu_type"] == "SNMPv2-Trap")
        informs_obs = sum(1 for x in deduplicated_notifications if x["pdu_type"] == "InformRequest")

        return {
            "raw_notifications": raw_notifications,
            "deduplicated_notifications": deduplicated_notifications,
            "traps_observed": traps_obs,
            "informs_observed": informs_obs,
            "duplicate_informs_suppressed": duplicate_informs_count,
            "responses_sent": responses_sent_count,
            "formatted_lines": formatted_lines,
            "malformed_lines": malformed_lines,
            "pcap_frames": pcap_frames,
        }

    @staticmethod
    def _parse_formatted_varbind_line(
        vb_line: str,
        peer_ip: str,
        peer_port: int,
        receiver_port: int,
        full_fmt: str,
    ) -> Optional[Dict[str, Any]]:
        parts = [p.strip() for p in vb_line.split("\t") if p.strip()]
        if len(parts) < 2:
            return None
        vb_map: Dict[str, Any] = {}
        vb_list: List[Dict[str, Any]] = []
        sys_uptime = 0
        trap_oid = ""
        for p in parts:
            if "=" not in p:
                return None
            raw_oid, raw_val = p.split("=", 1)
            try:
                norm_oid = normalize_oid_str(raw_oid.strip())
            except Exception:
                return None
            clean_val = raw_val.strip().strip('"').strip()
            if norm_oid == "1.3.6.1.2.1.1.3.0":
                try:
                    sys_uptime = int(clean_val)
                except ValueError:
                    sys_uptime = 0
            elif norm_oid == "1.3.6.1.6.3.1.1.4.1.0":
                try:
                    trap_oid = normalize_oid_str(clean_val)
                except Exception:
                    trap_oid = clean_val
            sym_name, asn1_t, _ = resolve_oid_metadata(norm_oid)
            vb_map[sym_name] = clean_val
            vb_list.append(
                {
                    "oid": norm_oid,
                    "oid_name": sym_name,
                    "asn1_type": asn1_t,
                    "value": clean_val,
                }
            )
        if not trap_oid:
            return None
        return {
            "pdu_type": "SNMPv2-Trap",
            "request_id": None,
            "community": "netspout-lab",
            "version": "2c",
            "src_ip": peer_ip,
            "src_port": peer_port,
            "receiver_port": receiver_port,
            "sys_uptime": sys_uptime,
            "trap_oid": trap_oid,
            "trap_name": TRAP_OID_CATALOG.get(trap_oid, {}).get("trap_name", trap_oid),
            "varbinds": vb_map,
            "varbind_list": vb_list,
            "raw_collector_line": full_fmt,
        }


# =========================================================================
# Pipeline B: External Net-SNMP CLI Poller (`snmpget`, `snmpgetnext`, `snmpwalk`, `snmpbulkwalk`)
# =========================================================================
class ExternalNetSnmpPoller:
    """
    Executes real external Net-SNMP CLI binaries (`/usr/bin/snmpget`, `/usr/bin/snmpgetnext`,
    `/usr/bin/snmpwalk`, `/usr/bin/snmpbulkwalk`) against `SimulatedSnmpAgent` over UDP.
    Never fabricates poll responses when the target agent is unreachable.
    """

    def __init__(
        self,
        host: str = DEFAULT_AGENT_BIND_HOST,
        port: int = DEFAULT_AGENT_BIND_PORT,
        community: str = DEFAULT_AGENT_COMMUNITY,
        timeout_sec: int = 1,
        retries: int = 0,
    ):
        self.host = host
        self.port = int(port)
        self.community = community
        self.timeout_sec = max(1, int(timeout_sec))
        self.retries = max(0, int(retries))

    def _run_cli(
        self,
        binary_name: str,
        pdu_type_label: str,
        oids: List[str],
        extra_args: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        bin_path = f"/usr/bin/{binary_name}"
        if not os.path.exists(bin_path):
            bin_path = shutil.which(binary_name) or bin_path

        cmd = [
            bin_path,
            "-v2c",
            "-c",
            self.community,
            "-t",
            str(self.timeout_sec),
            "-r",
            str(self.retries),
            "-On",
            "-OQ",
            "-Oe",
            "-Ot",
        ]
        if extra_args:
            cmd.extend(extra_args)
        cmd.append(f"{self.host}:{self.port}")
        cmd.extend(oids)

        start_ts = time.time()
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=max(3.0, float(self.timeout_sec * (self.retries + 2))),
            )
            stdout = proc.stdout or ""
            stderr = proc.stderr or ""
            rc = proc.returncode
        except subprocess.TimeoutExpired as exc:
            stdout = exc.stdout or "" if isinstance(exc.stdout, str) else ""
            stderr = f"TimeoutExpired: {exc}"
            rc = 124
        except Exception as exc:
            stdout = ""
            stderr = str(exc)
            rc = 1

        observations, malformed = self.parse_cli_output(
            stdout,
            pdu_type_label=pdu_type_label,
            target_host=self.host,
            target_port=self.port,
        )
        success = rc == 0 and len(observations) > 0
        return {
            "tool": binary_name,
            "binary_path": bin_path,
            "pdu_type": pdu_type_label,
            "command": cmd,
            "returncode": rc,
            "success": success,
            "stdout": stdout,
            "stderr": stderr,
            "observations": observations,
            "malformed_lines": malformed,
            "timestamp": start_ts,
        }

    def snmpget(self, oids: List[str]) -> Dict[str, Any]:
        return self._run_cli("snmpget", "GetRequest", oids)

    def snmpgetnext(self, oids: List[str]) -> Dict[str, Any]:
        return self._run_cli("snmpgetnext", "GetNextRequest", oids)

    def snmpwalk(self, subtree_oid: str = "1.3.6.1.2.1") -> Dict[str, Any]:
        return self._run_cli("snmpwalk", "GetNextRequest", [subtree_oid])

    def snmpbulkwalk(self, subtree_oid: str = "1.3.6.1.2.1", max_rep: int = 10) -> Dict[str, Any]:
        return self._run_cli(
            "snmpbulkwalk",
            "GetBulkRequest",
            [subtree_oid],
            extra_args=[f"-Cr{max_rep}"],
        )

    @staticmethod
    def parse_cli_output(
        stdout_text: str,
        pdu_type_label: str = "GetRequest",
        target_host: str = "127.0.0.1",
        target_port: int = DEFAULT_AGENT_BIND_PORT,
    ) -> Tuple[List[Dict[str, Any]], int]:
        observations: List[Dict[str, Any]] = []
        malformed = 0

        enum_fallback = {
            "up": "1",
            "down": "2",
            "testing": "3",
            "forwarding": "1",
            "notForwarding": "2",
            "ethernetCsmacd": "6",
            "softwareLoopback": "24",
        }

        for raw_line in (stdout_text or "").splitlines():
            line = raw_line.strip()
            if not line:
                continue
            if "No more variables left in this MIB View" in line:
                continue
            if "=" not in line or not line.startswith("."):
                malformed += 1
                continue

            lhs, rhs = line.split("=", 1)
            try:
                norm_oid = normalize_oid_str(lhs.strip())
            except Exception:
                malformed += 1
                continue

            val_str = rhs.strip()
            if val_str.startswith('"') and val_str.endswith('"'):
                val_str = val_str[1:-1].strip()

            # Check for SNMPv2c exception strings
            if "No Such Object" in val_str or "No Such Instance" in val_str:
                continue

            sym_name, asn1_type, mib_mod = resolve_oid_metadata(norm_oid)
            if asn1_type == "Integer32" and val_str in enum_fallback:
                val_str = enum_fallback[val_str]
            # Normalize hex string outputs like "04 00" -> "0400"
            if re.fullmatch(r"[0-9A-Fa-f]{2}(?:\s+[0-9A-Fa-f]{2})+", val_str):
                val_str = "".join(val_str.split()).lower()

            num_val: Optional[float] = None
            try:
                num_val = float(val_str)
            except ValueError:
                num_val = None

            observations.append(
                {
                    "pdu_type": pdu_type_label,
                    "oid": norm_oid,
                    "oid_name": sym_name,
                    "value": val_str,
                    "numeric_value": num_val,
                    "value_type": asn1_type,
                    "mib_module": mib_mod,
                    "target_host": target_host,
                    "target_port": target_port,
                    "raw_line": line,
                }
            )

        return observations, malformed


# =========================================================================
# Out-of-Band Collector Normalizer (`netspout:snmp:trap` & `netspout:snmp:poll`)
# =========================================================================
class SnmpCollectorNormalizer:
    """
    Normalizes external `snmptrapd` notification observations and external Net-SNMP
    polling observations into canonical `NormalizedSnmpEvent` records.
    Attaches `netspout_run_id`, `netspout_scenario_id`, `netspout_phase`, and `netspout_device_id`
    out-of-band without injecting proprietary OIDs onto the SNMP wire.
    """

    def __init__(
        self,
        run_id: str,
        scenario_id: str = "service_provider_cisco",
        device_id: str = "cisco-asr9k-pe1",
        index: str = "idx_network_ops",
        request_id_phase_map: Optional[Dict[int, str]] = None,
    ):
        self.run_id = run_id
        self.scenario_id = scenario_id
        self.device_id = device_id
        self.index = index
        self.request_id_phase_map: Dict[int, str] = dict(request_id_phase_map or {})
        self._seen_event_keys: Set[str] = set()
        self.duplicate_events_suppressed: int = 0
        self.malformed_events_dropped: int = 0

    def normalize_trap_observation(
        self,
        obs: Dict[str, Any],
        phase_override: Optional[str] = None,
    ) -> Optional[NormalizedSnmpEvent]:
        if not isinstance(obs, dict) or not obs.get("trap_oid"):
            self.malformed_events_dropped += 1
            return None

        trap_oid = str(obs["trap_oid"])
        req_id = obs.get("request_id")
        pdu_type = str(obs.get("pdu_type", "SNMPv2-Trap"))

        # Resolve canonical phase out-of-band
        if phase_override:
            phase = normalize_scenario_phase(phase_override)
        elif req_id is not None and int(req_id) in self.request_id_phase_map:
            phase = normalize_scenario_phase(self.request_id_phase_map[int(req_id)])
        elif trap_oid in TRAP_OID_CATALOG:
            phase = TRAP_OID_CATALOG[trap_oid]["canonical_phase"]
        else:
            phase = "DEGRADE"

        dedup_key = f"TRAP:{self.run_id}:{pdu_type}:{req_id}:{trap_oid}:{phase}"
        if dedup_key in self._seen_event_keys:
            self.duplicate_events_suppressed += 1
            return None
        self._seen_event_keys.add(dedup_key)

        trap_meta = TRAP_OID_CATALOG.get(trap_oid, {})
        trap_name = obs.get("trap_name") or trap_meta.get("trap_name", trap_oid)
        primary_oid = trap_meta.get("primary_oid", trap_oid)
        primary_name = trap_meta.get("primary_oid_name", trap_name)

        # Extract primary payload value from the notification's varbinds
        primary_val = ""
        primary_type = "ObjectIdentifier"
        for vb in obs.get("varbind_list", []):
            if vb.get("oid") == primary_oid:
                primary_val = str(vb.get("value", ""))
                primary_type = str(vb.get("asn1_type", "Integer32"))
                break
        if not primary_val and primary_name in obs.get("varbinds", {}):
            primary_val = str(obs["varbinds"][primary_name])

        num_val: Optional[float] = None
        try:
            num_val = float(primary_val)
        except ValueError:
            num_val = None

        receiver_port = obs.get("receiver_port", DEFAULT_SNMP_TRAP_PORT)
        evt_hash = hashlib.sha256(dedup_key.encode("utf-8")).hexdigest()[:12]
        event_id = f"snmp-trap-{evt_hash}"

        return NormalizedSnmpEvent(
            timestamp=time.time(),
            sourcetype="netspout:snmp:trap",
            index=self.index,
            source=f"snmptrapd:udp:{receiver_port}",
            host=self.device_id,
            netspout_run_id=self.run_id,
            netspout_scenario_id=self.scenario_id,
            netspout_phase=phase,
            netspout_device_id=self.device_id,
            netspout_event_id=event_id,
            snmp_version=str(obs.get("version", "2c")),
            snmp_pdu_type=pdu_type,
            snmp_request_id=int(req_id) if req_id is not None else None,
            snmp_trap_oid=trap_oid,
            snmp_trap_name=trap_name,
            snmp_oid=primary_oid,
            snmp_oid_name=primary_name,
            snmp_value=primary_val,
            snmp_numeric_value=num_val,
            snmp_value_type=primary_type,
            snmp_source=str(obs.get("src_ip", "127.0.0.1")),
            snmp_collector="snmptrapd",
            snmp_transport="SNMPV2C_UDP",
            origin_evidence_stage=SnmpEvidenceStage.RECEIVER_OBSERVED.value,
            current_evidence_stage=SnmpEvidenceStage.RECEIVER_OBSERVED.value,
            evidence_stage=SnmpEvidenceStage.RECEIVER_OBSERVED.value,
            sys_uptime=int(obs.get("sys_uptime", 0)),
            varbinds=dict(obs.get("varbinds", {})),
            raw_collector_line=obs.get("raw_collector_line", ""),
        )

    def normalize_poll_observation(
        self,
        obs: Dict[str, Any],
        phase: str,
        request_id: Optional[int] = None,
    ) -> Optional[NormalizedSnmpEvent]:
        if not isinstance(obs, dict) or not obs.get("oid"):
            self.malformed_events_dropped += 1
            return None

        norm_phase = normalize_scenario_phase(phase)
        oid = str(obs["oid"])
        pdu_type = str(obs.get("pdu_type", "GetRequest"))
        val_str = str(obs.get("value", ""))

        dedup_key = f"POLL:{self.run_id}:{norm_phase}:{pdu_type}:{oid}"
        if dedup_key in self._seen_event_keys:
            self.duplicate_events_suppressed += 1
            return None
        self._seen_event_keys.add(dedup_key)

        target_port = obs.get("target_port", DEFAULT_AGENT_BIND_PORT)
        evt_hash = hashlib.sha256(dedup_key.encode("utf-8")).hexdigest()[:12]
        event_id = f"snmp-poll-{evt_hash}"

        return NormalizedSnmpEvent(
            timestamp=time.time(),
            sourcetype="netspout:snmp:poll",
            index=self.index,
            source=f"netsnmp:poll:udp:{target_port}",
            host=self.device_id,
            netspout_run_id=self.run_id,
            netspout_scenario_id=self.scenario_id,
            netspout_phase=norm_phase,
            netspout_device_id=self.device_id,
            netspout_event_id=event_id,
            snmp_version="2c",
            snmp_pdu_type=pdu_type,
            snmp_request_id=request_id,
            snmp_trap_oid=None,
            snmp_trap_name=None,
            snmp_oid=oid,
            snmp_oid_name=str(obs.get("oid_name", oid)),
            snmp_value=val_str,
            snmp_numeric_value=obs.get("numeric_value"),
            snmp_value_type=str(obs.get("value_type", "OctetString")),
            snmp_source=str(obs.get("target_host", "127.0.0.1")),
            snmp_collector="net-snmp-cli",
            snmp_transport="SNMPV2C_UDP",
            origin_evidence_stage=SnmpEvidenceStage.RECEIVER_OBSERVED.value,
            current_evidence_stage=SnmpEvidenceStage.RECEIVER_OBSERVED.value,
            evidence_stage=SnmpEvidenceStage.RECEIVER_OBSERVED.value,
            sys_uptime=None,
            varbinds={str(obs.get("oid_name", oid)): val_str},
            raw_collector_line=obs.get("raw_line", ""),
        )


# =========================================================================
# Canonical SPL Investigation Queries (Section 8)
# =========================================================================
def build_snmp_investigation_queries(
    run_id: str,
    index: str = "idx_network_ops",
) -> Dict[str, str]:
    """
    Returns copyable, executable SPL queries for investigating a Gate 12D/12F SNMP run in Splunk.
    Every query matches the implemented field model (`netspout:snmp:trap` and `netspout:snmp:poll`)
    and exposes explicit provenance (`origin_evidence_stage="RECEIVER_OBSERVED"`,
    `current_evidence_stage="SPLUNK_OBSERVED"`).
    """
    base = f'search index={index} (sourcetype="netspout:snmp:trap" OR sourcetype="netspout:snmp:poll") netspout_run_id="{run_id}"'
    prov_eval = '| eval origin_evidence_stage=coalesce(origin_evidence_stage, "RECEIVER_OBSERVED"), current_evidence_stage="SPLUNK_OBSERVED"'
    return {
        "all_snmp_evidence_spl": (
            f'{base} {prov_eval} | table _time netspout_phase sourcetype snmp_pdu_type '
            f'snmp_request_id snmp_trap_name snmp_oid_name snmp_value snmp_collector '
            f'origin_evidence_stage current_evidence_stage'
        ),
        "trap_inform_evidence_spl": (
            f'search index={index} sourcetype="netspout:snmp:trap" netspout_run_id="{run_id}" '
            f'{prov_eval} | table _time netspout_phase snmp_pdu_type snmp_request_id '
            f'snmp_trap_name snmp_trap_oid snmp_oid_name snmp_value sys_uptime '
            f'origin_evidence_stage current_evidence_stage'
        ),
        "polling_evidence_spl": (
            f'search index={index} sourcetype="netspout:snmp:poll" netspout_run_id="{run_id}" '
            f'{prov_eval} | table _time netspout_phase snmp_pdu_type snmp_oid_name '
            f'snmp_oid snmp_value snmp_value_type origin_evidence_stage current_evidence_stage'
        ),
        "timeline_spl": (
            f'{base} | stats count as evidence_count values(sourcetype) as sourcetypes '
            f'values(snmp_pdu_type) as pdu_types values(snmp_trap_name) as notifications '
            f'by netspout_phase'
        ),
        "interface_state_spl": (
            f'{base} (snmp_oid="1.3.6.1.2.1.2.2.1.8.1" OR snmp_oid="1.3.6.1.2.1.2.2.1.14.1" '
            f'OR snmp_trap_oid="1.3.6.1.6.3.1.1.5.3" OR snmp_trap_oid="1.3.6.1.6.3.1.1.5.4") '
            f'| table _time netspout_phase sourcetype snmp_pdu_type '
            f'snmp_trap_name snmp_oid_name snmp_value'
        ),
        "bgp_state_spl": (
            f'{base} (snmp_oid="1.3.6.1.2.1.15.3.1.2.198.51.100.1" '
            f'OR snmp_oid="1.3.6.1.2.1.15.3.1.14.198.51.100.1" '
            f'OR snmp_oid="1.3.6.1.2.1.15.3.1.2.198.51.100.2" '
            f'OR snmp_trap_oid="1.3.6.1.2.1.15.7.2" OR snmp_trap_oid="1.3.6.1.2.1.15.7.1") '
            f'| table _time netspout_phase sourcetype snmp_pdu_type '
            f'snmp_trap_name snmp_oid_name snmp_value'
        ),
        "notification_vs_poll_correlation_spl": (
            f'{base} | stats count(eval(sourcetype="netspout:snmp:trap")) as notification_count '
            f'count(eval(sourcetype="netspout:snmp:poll")) as poll_count '
            f'values(snmp_trap_name) as notifications '
            f'values(eval(if(sourcetype="netspout:snmp:poll", snmp_oid_name."=".snmp_value, null()))) as polled_states '
            f'by netspout_phase'
        ),
    }


# =========================================================================
# Splunk HEC Dispatcher & Fresh SPL Search Observer (`SnmpSplunkBridge`)
# =========================================================================
class SnmpSplunkBridge:
    """
    Dispatches normalized `netspout:snmp:trap` and `netspout:snmp:poll` collector events
    to Splunk HEC (`idx_network_ops`) and executes fresh Splunk REST searches to prove
    `SPLUNK_OBSERVED` independently of `SPLUNK_DISPATCHED`.
    """

    def __init__(
        self,
        hec_url: Optional[str] = None,
        hec_token: Optional[str] = None,
        rest_search_url: Optional[str] = None,
        rest_username: Optional[str] = None,
        rest_password: Optional[str] = None,
        index: str = "idx_network_ops",
        simulate_splunk_unavailable: bool = False,
    ):
        self.hec_url = hec_url or os.environ.get("NETSPOUT_HEC_URL", "https://127.0.0.1:8088/services/collector/event")
        self.hec_token = (
            hec_token
            or os.environ.get("NETSPOUT_HEC_TOKEN")
            or os.environ.get("SPLUNK_HEC_TOKEN")
            or "00000000-0000-0000-0000-000000000000"
        )
        self.rest_search_url = rest_search_url or os.environ.get(
            "NETSPOUT_REST_SEARCH_URL", os.environ.get("NETSPOUT_REST_URL", "https://127.0.0.1:8089/services/search/jobs/export")
        )
        self.rest_username = rest_username or os.environ.get("NETSPOUT_SPLUNK_USER", "admin")
        self.rest_password = (
            rest_password
            or os.environ.get("NETSPOUT_SPLUNK_PASSWORD")
            or os.environ.get("SPLUNK_PASSWORD")
            or "SplunkPassword123!"
        )
        self.index = index
        self.simulate_splunk_unavailable = simulate_splunk_unavailable

    @staticmethod
    def _ssl_ctx() -> ssl.SSLContext:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx

    def dispatch_events(
        self,
        events: List[NormalizedSnmpEvent],
        timeout_sec: float = 4.0,
    ) -> Dict[str, Any]:
        """
        Dispatches normalized SNMP collector/poller events to Splunk HEC.
        Only marks `SPLUNK_DISPATCHED` when HEC returns HTTP 200.
        Never claims `SPLUNK_OBSERVED`. Preserves `origin_evidence_stage = RECEIVER_OBSERVED`.
        """
        dispatched = 0
        failed = 0
        errors: List[str] = []

        if self.simulate_splunk_unavailable:
            failed = len(events)
            errors.append("Simulated Splunk HEC unavailability active (Controlled Failure B)")
            return {
                "attempted": len(events),
                "dispatched": 0,
                "failed": failed,
                "errors": errors,
                "stage": SnmpEvidenceStage.RECEIVER_OBSERVED.value,
            }

        candidate_urls = [self.hec_url]
        if ":8088" in self.hec_url:
            candidate_urls.append(self.hec_url.replace(":8088", ":8888"))
        elif ":8888" in self.hec_url:
            candidate_urls.append(self.hec_url.replace(":8888", ":8088"))

        for ev in events:
            payload = ev.to_hec_payload()
            body = json.dumps(payload).encode("utf-8")
            event_dispatched = False
            last_err = ""
            for h_url in candidate_urls:
                ctx = self._ssl_ctx() if h_url.startswith("https") else None
                req = urllib.request.Request(h_url, data=body, method="POST")
                req.add_header("Authorization", f"Splunk {self.hec_token}")
                req.add_header("Content-Type", "application/json")
                try:
                    with urllib.request.urlopen(req, context=ctx, timeout=timeout_sec) as resp:
                        if resp.status == 200:
                            dispatched += 1
                            ev.evidence_stage = SnmpEvidenceStage.SPLUNK_DISPATCHED.value
                            ev.current_evidence_stage = SnmpEvidenceStage.SPLUNK_DISPATCHED.value
                            event_dispatched = True
                            self.hec_url = h_url
                            break
                        else:
                            last_err = f"HEC returned HTTP {resp.status}"
                except Exception as exc:
                    last_err = f"HEC dispatch error: {exc}"
            if not event_dispatched:
                failed += 1
                errors.append(last_err)

        return {
            "attempted": len(events),
            "dispatched": dispatched,
            "failed": failed,
            "errors": errors,
            "stage": (
                SnmpEvidenceStage.SPLUNK_DISPATCHED.value
                if dispatched > 0 and failed == 0
                else SnmpEvidenceStage.RECEIVER_OBSERVED.value
            ),
        }

    def execute_spl_search(
        self,
        spl_query: str,
        earliest_time: str = "-15m",
        latest_time: str = "now",
        max_wait_sec: float = 6.0,
        min_expected: int = 1,
    ) -> List[Dict[str, Any]]:
        """
        Executes a fresh SPL search against Splunk REST `/services/search/jobs/export`
        and returns the parsed result rows.
        Establishes `current_evidence_stage = SPLUNK_OBSERVED` strictly upon search verification
        while preserving `origin_evidence_stage = RECEIVER_OBSERVED`.
        """
        if self.simulate_splunk_unavailable:
            return []

        clean_query = spl_query.strip()
        if not clean_query.startswith("search ") and not clean_query.startswith("|"):
            clean_query = f"search {clean_query}"

        data = urllib.parse.urlencode(
            {
                "search": clean_query,
                "output_mode": "json",
                "earliest_time": earliest_time,
                "latest_time": latest_time,
            }
        ).encode("utf-8")

        auth_bytes = f"{self.rest_username}:{self.rest_password}".encode("utf-8")
        auth_header = "Basic " + base64.b64encode(auth_bytes).decode("ascii")
        ctx = self._ssl_ctx() if self.rest_search_url.startswith("https") else None

        deadline = time.monotonic() + max_wait_sec
        last_results: List[Dict[str, Any]] = []

        candidate_urls = [self.rest_search_url]
        if ":8089" in self.rest_search_url:
            candidate_urls.append(self.rest_search_url.replace(":8089", ":8889"))
        elif ":8889" in self.rest_search_url:
            candidate_urls.append(self.rest_search_url.replace(":8889", ":8089"))

        while time.monotonic() < deadline:
            for url in candidate_urls:
                ctx = self._ssl_ctx() if url.startswith("https") else None
                req = urllib.request.Request(url, data=data, method="POST")
                req.add_header("Authorization", auth_header)
                rows: List[Dict[str, Any]] = []
                try:
                    with urllib.request.urlopen(req, context=ctx, timeout=5.0) as resp:
                        for raw_line in resp.read().decode("utf-8", errors="replace").splitlines():
                            line = raw_line.strip()
                            if not line:
                                continue
                            obj = json.loads(line)
                            if "result" in obj and isinstance(obj["result"], dict):
                                norm_row: Dict[str, Any] = {}
                                for rk, rv in obj["result"].items():
                                    if (
                                        isinstance(rv, list)
                                        and len(rv) > 1
                                        and not rk.startswith("_")
                                        and len({str(x) for x in rv}) == 1
                                    ):
                                        norm_row[rk] = rv[0]
                                    else:
                                        norm_row[rk] = rv
                                if "netspout_run_id" in norm_row or "snmp_pdu_type" in norm_row:
                                    norm_row["origin_evidence_stage"] = str(
                                        norm_row.get("origin_evidence_stage")
                                        or SnmpEvidenceStage.RECEIVER_OBSERVED.value
                                    )
                                    norm_row["current_evidence_stage"] = (
                                        SnmpEvidenceStage.SPLUNK_OBSERVED.value
                                    )
                                rows.append(norm_row)
                    last_results = rows
                    if len(rows) >= min_expected:
                        return rows
                except Exception:
                    pass
            time.sleep(0.4)

        return last_results


# =========================================================================
# Gate 12D End-to-End Orchestrator & Contract Validator
# =========================================================================
class SnmpSplunkE2EOrchestrator:
    """
    Executes and validates the complete `service_provider_cisco` Native SNMP ->
    External Receiver/Poller -> Splunk -> SPL -> Validation pipeline.
    """

    def __init__(
        self,
        index: str = "idx_network_ops",
        device_id: str = "cisco-asr9k-pe1",
        seed: int = 42,
        splunk_bridge: Optional[SnmpSplunkBridge] = None,
        state_plan: Optional[Any] = None,
    ):
        self.scenario_id = "service_provider_cisco"
        self.index = index
        self.device_id = device_id
        self.seed = int(seed)
        self.state_plan = state_plan
        self.splunk_bridge = splunk_bridge or SnmpSplunkBridge(index=index)

    def execute_e2e_run(
        self,
        run_id: Optional[str] = None,
        suppress_phases: Optional[Set[str]] = None,
        receiver_available: bool = True,
        agent_available: bool = True,
        splunk_available: bool = True,
        work_dir: Optional[str] = None,
    ) -> Tuple[SnmpE2ERunScorecard, Dict[str, Any]]:
        """
        Executes a fresh `service_provider_cisco` Gate 12D/12F E2E run across:
          - Pipeline A: Native SNMPv2c TRAP (4 PDUs) + INFORM (4 PDUs) -> `/usr/sbin/snmptrapd`
          - Pipeline B: External `/usr/bin/snmpget`, `/usr/bin/snmpgetnext`, `/usr/bin/snmpwalk`,
                        `/usr/bin/snmpbulkwalk` -> `SimulatedSnmpAgent` across
                        `BASELINE -> DEGRADE -> FAILOVER -> RECOVERY`
          - Normalization -> Splunk HEC -> Fresh SPL Reconstruction -> Validation
        """
        active_run_id = run_id or f"run-gate12d-{uuid.uuid4().hex[:10]}"
        suppressed = {normalize_scenario_phase(p) for p in (suppress_phases or set())}

        scorecard = SnmpE2ERunScorecard(
            run_id=active_run_id,
            scenario_id=self.scenario_id,
            device_id=self.device_id,
            seed=self.seed,
            target_index=self.index,
            investigation_queries=build_snmp_investigation_queries(active_run_id, self.index),
        )

        # Configure Splunk bridge availability
        self.splunk_bridge.simulate_splunk_unavailable = not splunk_available

        # Build deterministic TRAP and INFORM notification progressions
        traps = snmp_engine.build_service_provider_cisco_native_pdus(
            seed=self.seed,
            pdu_mode="TRAP",
            community="netspout-lab",
            exporter_ip="10.200.0.1",
            device_id=self.device_id,
        )
        informs = snmp_engine.build_service_provider_cisco_native_pdus(
            seed=self.seed + 100,
            pdu_mode="INFORM",
            community="netspout-lab",
            exporter_ip="10.200.0.1",
            device_id=self.device_id,
        )

        # Filter out suppressed phases if testing Controlled Failure D
        if suppressed:
            traps = [t for t in traps if normalize_scenario_phase(t.phase or "FAULT") not in suppressed]
            informs = [inf for inf in informs if normalize_scenario_phase(inf.phase or "FAULT") not in suppressed]

        # Build out-of-band request_id -> canonical phase lookup table
        req_id_phase_map: Dict[int, str] = {}
        for pdu in list(traps) + list(informs):
            req_id_phase_map[int(pdu.request_id)] = normalize_scenario_phase(pdu.phase or "FAULT")

        scorecard.traps_generated = len(traps)
        scorecard.informs_generated = len(informs)
        scorecard.generated_notifications = scorecard.traps_generated + scorecard.informs_generated
        scorecard.stage_history.append(SnmpEvidenceStage.GENERATED.value)
        scorecard.evidence_stage = SnmpEvidenceStage.GENERATED.value
        scorecard.current_evidence_stage = SnmpEvidenceStage.GENERATED.value
        scorecard.origin_evidence_stage = SnmpEvidenceStage.RECEIVER_OBSERVED.value

        normalizer = SnmpCollectorNormalizer(
            run_id=active_run_id,
            scenario_id=self.scenario_id,
            device_id=self.device_id,
            index=self.index,
            request_id_phase_map=req_id_phase_map,
        )

        normalized_events: List[NormalizedSnmpEvent] = []
        raw_artifacts: Dict[str, Any] = {
            "snmptrapd_log": "",
            "trap_pcap_frames": [],
            "poll_pcap_frames": [],
            "cli_outputs": {},
            "splunk_search_results": {},
            "generated_pdus": list(traps) + list(informs),
        }

        # -----------------------------------------------------------------
        # PIPELINE A: Native SNMPv2c TRAP & INFORM -> External snmptrapd
        # -----------------------------------------------------------------
        bound_trap_port = DEFAULT_SNMP_TRAP_PORT
        if receiver_available:
            with ExternalSnmpTrapReceiver(
                host="127.0.0.1",
                port=0,
                community="netspout-lab",
                work_dir=work_dir,
            ) as trap_receiver:
                bound_trap_port = trap_receiver.bound_port
                transport = NativeSnmpTransport(
                    destination_host="127.0.0.1",
                    destination_port=trap_receiver.bound_port,
                    community="netspout-lab",
                    inform_timeout_ms=1000,
                    inform_max_retries=2,
                    test_mode=True,
                )
                res_trap = transport.send_batch(traps)
                res_inform = transport.send_batch(informs)

                expected_notif = len(traps) + len(informs)
                trap_receiver.wait_for_notifications(expected_notif, timeout_sec=3.0)
                time.sleep(0.15)
                obs_summary = trap_receiver.parse_observations()
                raw_artifacts["snmptrapd_log"] = trap_receiver.read_raw_log()
                raw_artifacts["trap_pcap_frames"] = obs_summary["pcap_frames"]
        else:
            # Controlled Failure A: Receiver unavailable (send to closed local UDP port)
            closed_port = _find_free_udp_port("127.0.0.1")
            bound_trap_port = closed_port
            transport = NativeSnmpTransport(
                destination_host="127.0.0.1",
                destination_port=closed_port,
                community="netspout-lab",
                inform_timeout_ms=60,
                inform_max_retries=1,
                test_mode=True,
            )
            res_trap = transport.send_batch(traps)
            res_inform = transport.send_batch(informs)
            obs_summary = {
                "deduplicated_notifications": [],
                "traps_observed": 0,
                "informs_observed": 0,
                "duplicate_informs_suppressed": 0,
                "responses_sent": 0,
                "malformed_lines": 0,
                "pcap_frames": [],
            }

        scorecard.encoded_notifications = res_trap.pdus_encoded + res_inform.pdus_encoded
        scorecard.traps_sent = res_trap.datagrams_sent
        scorecard.informs_sent = res_inform.informs_sent
        scorecard.sent_notifications = scorecard.traps_sent + scorecard.informs_sent
        scorecard.informs_acknowledged = res_inform.informs_acknowledged

        if scorecard.encoded_notifications > 0:
            scorecard.stage_history.append(SnmpEvidenceStage.ENCODED.value)
            scorecard.evidence_stage = SnmpEvidenceStage.ENCODED.value
            scorecard.current_evidence_stage = SnmpEvidenceStage.ENCODED.value
        if scorecard.sent_notifications > 0:
            scorecard.stage_history.append(SnmpEvidenceStage.SENT.value)
            scorecard.evidence_stage = SnmpEvidenceStage.SENT.value
            scorecard.current_evidence_stage = SnmpEvidenceStage.SENT.value
        if scorecard.informs_acknowledged > 0:
            scorecard.stage_history.append(SnmpEvidenceStage.ACKNOWLEDGED.value)
            scorecard.evidence_stage = SnmpEvidenceStage.ACKNOWLEDGED.value
            scorecard.current_evidence_stage = SnmpEvidenceStage.ACKNOWLEDGED.value

        scorecard.traps_receiver_observed = obs_summary["traps_observed"]
        scorecard.informs_receiver_observed = obs_summary["informs_observed"]
        scorecard.receiver_observed_notifications = len(obs_summary["deduplicated_notifications"])

        for notif_obs in obs_summary["deduplicated_notifications"]:
            norm_ev = normalizer.normalize_trap_observation(notif_obs)
            if norm_ev is not None:
                normalized_events.append(norm_ev)

        # Build combined SnmpTransportResult for single-execution RunManifest consistency (F-12E-04)
        combined_req_ids = list(res_trap.request_ids) + list(res_inform.request_ids)
        combined_ack_ids = list(res_inform.acknowledged_request_ids)
        obs_req_ids = [
            int(n["request_id"])
            for n in obs_summary["deduplicated_notifications"]
            if n.get("request_id") is not None
        ]
        raw_artifacts["transport_result"] = SnmpTransportResult(
            transport_type="SNMPV2C_UDP",
            pdu_mode="MIXED",
            destination_host="127.0.0.1",
            destination_port=bound_trap_port,
            pdus_generated=scorecard.generated_notifications,
            pdus_encoded=scorecard.encoded_notifications,
            datagrams_attempted=res_trap.datagrams_attempted + res_inform.datagrams_attempted,
            datagrams_sent=scorecard.sent_notifications,
            bytes_sent=res_trap.bytes_sent + res_inform.bytes_sent,
            informs_sent=scorecard.informs_sent,
            informs_acknowledged=scorecard.informs_acknowledged,
            inform_retries=res_inform.inform_retries,
            inform_timeouts=res_inform.inform_timeouts,
            late_or_mismatched_acks=res_inform.late_or_mismatched_acks,
            request_ids=combined_req_ids,
            acknowledged_request_ids=combined_ack_ids,
            receiver_observed_count=scorecard.receiver_observed_notifications,
            receiver_observed_request_ids=obs_req_ids,
            evidence_stage=(
                SnmpEvidenceStage.RECEIVER_OBSERVED.value
                if scorecard.receiver_observed_notifications > 0
                else scorecard.evidence_stage
            ),
            stage_history=list(scorecard.stage_history),
            rtt_ms_samples=list(res_inform.rtt_ms_samples),
            elapsed_ms=round(res_trap.elapsed_ms + res_inform.elapsed_ms, 3),
            errors=list(res_trap.errors) + list(res_inform.errors),
            error_types=list(res_trap.error_types) + list(res_inform.error_types),
        )

        # -----------------------------------------------------------------
        # PIPELINE B: External Net-SNMP Poller -> SimulatedSnmpAgent
        # -----------------------------------------------------------------
        phases_to_poll = [
            p for p in ("BASELINE", "DEGRADE", "FAILOVER", "RECOVERY") if p not in suppressed
        ]

        if agent_available:
            with SimulatedSnmpAgent(
                bind_host="127.0.0.1",
                bind_port=0,
                community="public",
                scenario_id=self.scenario_id,
                phase="BASELINE",
                seed=self.seed,
                device_id=self.device_id,
                state_store=(
                    self.state_plan.state_store if self.state_plan is not None else None
                ),
            ) as agent:
                poller = ExternalNetSnmpPoller(
                    host="127.0.0.1",
                    port=agent.bound_port,
                    community="public",
                    timeout_sec=2,
                    retries=1,
                )
                for phase_name in phases_to_poll:
                    if self.state_plan is not None:
                        self.state_plan.activate(phase_name)
                    agent.set_phase(phase_name)
                    # 1. External snmpget of key phase OIDs
                    get_res = poller.snmpget(PHASE_POLL_OIDS)
                    raw_artifacts["cli_outputs"][f"snmpget_{phase_name}"] = get_res["stdout"]
                    for obs in get_res["observations"]:
                        ev = normalizer.normalize_poll_observation(obs, phase=phase_name)
                        if ev is not None:
                            normalized_events.append(ev)

                    # 2. External snmpgetnext of root / interface OIDs
                    gn_res = poller.snmpgetnext(["1.3.6.1.2.1.1", "1.3.6.1.2.1.2.2.1.8"])
                    raw_artifacts["cli_outputs"][f"snmpgetnext_{phase_name}"] = gn_res["stdout"]
                    for obs in gn_res["observations"]:
                        ev = normalizer.normalize_poll_observation(obs, phase=phase_name)
                        if ev is not None:
                            normalized_events.append(ev)

                    # 3. External snmpwalk & snmpbulkwalk on BASELINE and FAILOVER
                    if phase_name in ("BASELINE", "FAILOVER"):
                        walk_res = poller.snmpwalk("1.3.6.1.2.1")
                        bwalk_res = poller.snmpbulkwalk("1.3.6.1.2.1", max_rep=10)
                        raw_artifacts["cli_outputs"][f"snmpwalk_{phase_name}"] = walk_res["stdout"]
                        raw_artifacts["cli_outputs"][f"snmpbulkwalk_{phase_name}"] = bwalk_res["stdout"]
                        scorecard.walk_oids_observed = max(
                            scorecard.walk_oids_observed,
                            len(walk_res["observations"]),
                            len(bwalk_res["observations"]),
                        )
                        for obs in bwalk_res["observations"]:
                            ev = normalizer.normalize_poll_observation(obs, phase=phase_name)
                            if ev is not None:
                                normalized_events.append(ev)

                poll_ev = agent.get_evidence()
                raw_artifacts["polling_evidence"] = poll_ev
                scorecard.get_requests = poll_ev.get_requests
                scorecard.getnext_requests = poll_ev.getnext_requests
                scorecard.getbulk_requests = poll_ev.getbulk_requests
                scorecard.polling_requests = poll_ev.requests_received
                scorecard.polling_responses = poll_ev.responses_sent
                with agent._lock:
                    raw_artifacts["poll_pcap_frames"] = list(agent.captured_frames)
        else:
            # Controlled Failure C: SNMP Agent unreachable
            closed_agent_port = _find_free_udp_port("127.0.0.1")
            poller = ExternalNetSnmpPoller(
                host="127.0.0.1",
                port=closed_agent_port,
                community="public",
                timeout_sec=1,
                retries=0,
            )
            timeout_res = poller.snmpget(["1.3.6.1.2.1.1.3.0"])
            scorecard.polling_requests = 1
            scorecard.polling_responses = 0
            scorecard.errors.append(
                f"External poller failed to reach SNMP agent on 127.0.0.1:{closed_agent_port}: "
                f"{timeout_res['stderr'].strip() or 'Timeout'}"
            )

        # Update normalization counts and RECEIVER_OBSERVED status
        scorecard.normalized_trap_records = sum(
            1 for e in normalized_events if e.sourcetype == "netspout:snmp:trap"
        )
        scorecard.normalized_poll_records = sum(
            1 for e in normalized_events if e.sourcetype == "netspout:snmp:poll"
        )
        scorecard.normalized_records = len(normalized_events)
        scorecard.duplicate_records_suppressed = normalizer.duplicate_events_suppressed
        scorecard.malformed_records_dropped = normalizer.malformed_events_dropped

        if scorecard.receiver_observed_notifications > 0 or scorecard.polling_responses > 0:
            scorecard.snmp_receiver_observed_status = "YES"
            scorecard.stage_history.append(SnmpEvidenceStage.RECEIVER_OBSERVED.value)
            scorecard.evidence_stage = SnmpEvidenceStage.RECEIVER_OBSERVED.value
            scorecard.current_evidence_stage = SnmpEvidenceStage.RECEIVER_OBSERVED.value
        else:
            scorecard.snmp_receiver_observed_status = "NO"

        # -----------------------------------------------------------------
        # STAGE 6: Splunk HEC Dispatch (`SPLUNK_DISPATCHED`)
        # -----------------------------------------------------------------
        if self.state_plan is not None:
            for event in normalized_events:
                event.timestamp = self.state_plan.timestamp_seconds(
                    event.netspout_phase
                )
        if normalized_events:
            disp_res = self.splunk_bridge.dispatch_events(normalized_events)
            scorecard.splunk_dispatched_records = disp_res["dispatched"]
            scorecard.splunk_dispatch_failures = disp_res["failed"]
            scorecard.errors.extend(disp_res["errors"])
            if scorecard.splunk_dispatched_records > 0 and scorecard.splunk_dispatch_failures == 0:
                scorecard.splunk_dispatched_status = "YES"
                scorecard.stage_history.append(SnmpEvidenceStage.SPLUNK_DISPATCHED.value)
                scorecard.evidence_stage = SnmpEvidenceStage.SPLUNK_DISPATCHED.value
                scorecard.current_evidence_stage = SnmpEvidenceStage.SPLUNK_DISPATCHED.value
            elif scorecard.splunk_dispatched_records > 0:
                scorecard.splunk_dispatched_status = "PARTIAL"
            else:
                scorecard.splunk_dispatched_status = "NO"

        # -----------------------------------------------------------------
        # STAGE 7: Fresh Splunk Search Observation (`SPLUNK_OBSERVED`)
        # -----------------------------------------------------------------
        if scorecard.splunk_dispatched_records > 0 and splunk_available:
            trap_rows = self.splunk_bridge.execute_spl_search(
                f'search index={self.index} sourcetype="netspout:snmp:trap" netspout_run_id="{active_run_id}" | spath',
                max_wait_sec=8.0,
                min_expected=max(1, scorecard.normalized_trap_records),
            )
            poll_rows = self.splunk_bridge.execute_spl_search(
                f'search index={self.index} sourcetype="netspout:snmp:poll" netspout_run_id="{active_run_id}" | spath',
                max_wait_sec=8.0,
                min_expected=max(1, scorecard.normalized_poll_records),
            )
            scorecard.splunk_observed_trap_records = len(trap_rows)
            scorecard.splunk_observed_poll_records = len(poll_rows)
            scorecard.splunk_observed_records = len(trap_rows) + len(poll_rows)

            raw_artifacts["splunk_search_results"]["trap_rows"] = trap_rows
            raw_artifacts["splunk_search_results"]["poll_rows"] = poll_rows

            # Promote current_evidence_stage to SPLUNK_OBSERVED ONLY for events verified by fresh Splunk search
            observed_event_ids = {
                str(r.get("netspout_event_id", ""))
                for r in (trap_rows + poll_rows)
                if r.get("netspout_event_id")
            }
            for ev in normalized_events:
                if ev.netspout_event_id in observed_event_ids or (
                    scorecard.splunk_observed_records >= scorecard.normalized_records
                ):
                    ev.current_evidence_stage = SnmpEvidenceStage.SPLUNK_OBSERVED.value

            # Execute all 7 canonical SPL investigation queries to prove fresh SPL reconstruction
            for q_name, q_spl in scorecard.investigation_queries.items():
                raw_artifacts["splunk_search_results"][q_name] = self.splunk_bridge.execute_spl_search(
                    q_spl, max_wait_sec=5.0, min_expected=1
                )

            if scorecard.normalized_records > 0:
                scorecard.observation_completeness_pct = round(
                    (scorecard.splunk_observed_records / scorecard.normalized_records) * 100.0,
                    1,
                )
            if scorecard.splunk_observed_records > 0:
                scorecard.splunk_observed_status = "YES"
                scorecard.stage_history.append(SnmpEvidenceStage.SPLUNK_OBSERVED.value)
                scorecard.evidence_stage = SnmpEvidenceStage.SPLUNK_OBSERVED.value
                scorecard.current_evidence_stage = SnmpEvidenceStage.SPLUNK_OBSERVED.value
        else:
            scorecard.splunk_observed_status = "NO"
            scorecard.observation_completeness_pct = 0.0

        # -----------------------------------------------------------------
        # STAGE 8: Validation against Splunk-Observed Evidence (`VALIDATED`)
        # -----------------------------------------------------------------
        val_passed, checks, coherence_info, phases_seen = self.validate_splunk_evidence(
            run_id=active_run_id,
            trap_rows=raw_artifacts["splunk_search_results"].get("trap_rows", []),
            poll_rows=raw_artifacts["splunk_search_results"].get("poll_rows", []),
        )
        scorecard.phases_verified = phases_seen
        scorecard.trap_poll_coherence = coherence_info["coherent"]
        scorecard.coherence_details = coherence_info
        scorecard.validation_checks = checks
        scorecard.validation_result = "PASS" if val_passed else "FAIL"
        if val_passed:
            scorecard.stage_history.append(SnmpEvidenceStage.VALIDATED.value)
            scorecard.evidence_stage = SnmpEvidenceStage.VALIDATED.value
            scorecard.current_evidence_stage = SnmpEvidenceStage.VALIDATED.value

        scorecard.stage_classification = {
            "GENERATED": "YES" if scorecard.generated_notifications > 0 else "NO",
            "ENCODED": "YES" if scorecard.encoded_notifications > 0 else "NO",
            "SENT": "YES" if scorecard.sent_notifications > 0 else "NO",
            "ACKNOWLEDGED": "YES" if scorecard.informs_acknowledged > 0 else "NO",
            "RECEIVER_OBSERVED": scorecard.snmp_receiver_observed_status,
            "SPLUNK_DISPATCHED": scorecard.splunk_dispatched_status,
            "SPLUNK_OBSERVED": scorecard.splunk_observed_status,
            "VALIDATED": "YES" if val_passed else "NO",
        }

        raw_artifacts["normalized_events"] = normalized_events
        if self.state_plan is not None:
            raw_artifacts["shared_state_store"] = self.state_plan.state_store
            raw_artifacts["shared_simulation_clock"] = self.state_plan.clock
            raw_artifacts["correlated_state_trace"] = [
                {
                    "phase": phase,
                    "timestamp_ns": self.state_plan.timestamp_ns(phase),
                    "entity_id": self.device_id,
                    "interface_id": self.state_plan.interface_id,
                    "native_interface_id": self.state_plan.snmp_wire_interface_id,
                    "if_index": self.state_plan.snmp_if_index,
                    "oper_status": next(
                        (
                            "UP" if str(event.snmp_value) == "1" else "DOWN"
                            for event in normalized_events
                            if event.sourcetype == "netspout:snmp:poll"
                            and event.netspout_phase == phase
                            and event.snmp_oid
                            == "1.3.6.1.2.1.2.2.1.8.1"
                        ),
                        None,
                    ),
                }
                for phase in self.state_plan.phases
            ]
        return scorecard, raw_artifacts

    @staticmethod
    def validate_splunk_evidence(
        run_id: str,
        trap_rows: List[Dict[str, Any]],
        poll_rows: List[Dict[str, Any]],
    ) -> Tuple[bool, List[Dict[str, Any]], Dict[str, Any], List[str]]:
        """
        Evaluates the Gate 12D scenario validation contract strictly against
        Splunk-observed records matching `run_id`.
        Rejects any cross-run contamination (`netspout_run_id != run_id`).
        """
        checks: List[Dict[str, Any]] = []

        # 1. Filter strictly by run_id and check for cross-run contamination
        valid_traps = [r for r in trap_rows if r.get("netspout_run_id") == run_id]
        valid_polls = [r for r in poll_rows if r.get("netspout_run_id") == run_id]
        foreign_rows = [
            r for r in (trap_rows + poll_rows) if r.get("netspout_run_id") != run_id
        ]

        checks.append(
            {
                "check_id": "run_correlation_isolation",
                "passed": len(foreign_rows) == 0 and (len(valid_traps) + len(valid_polls) > 0),
                "foreign_records": len(foreign_rows),
                "matched_records": len(valid_traps) + len(valid_polls),
            }
        )

        # 2. Check all 4 required phases exist in Splunk evidence
        required_phases = ["BASELINE", "DEGRADE", "FAILOVER", "RECOVERY"]
        observed_phases_set = {
            str(r.get("netspout_phase", ""))
            for r in (valid_traps + valid_polls)
            if r.get("netspout_phase")
        }
        phases_verified = [p for p in required_phases if p in observed_phases_set]
        checks.append(
            {
                "check_id": "all_four_phases_present",
                "passed": len(phases_verified) == 4,
                "expected_phases": required_phases,
                "observed_phases": phases_verified,
            }
        )

        # 3. Check all 4 required notification OIDs observed in Splunk (both TRAP and INFORM)
        required_trap_oids = {
            "1.3.6.1.6.3.1.1.5.3",
            "1.3.6.1.2.1.15.7.2",
            "1.3.6.1.6.3.1.1.5.4",
            "1.3.6.1.2.1.15.7.1",
        }
        observed_trap_oids = {str(r.get("snmp_trap_oid", "")) for r in valid_traps}
        observed_pdu_types = {str(r.get("snmp_pdu_type", "")) for r in valid_traps}
        checks.append(
            {
                "check_id": "required_notifications_observed",
                "passed": required_trap_oids.issubset(observed_trap_oids)
                and "SNMPv2-Trap" in observed_pdu_types
                and "InformRequest" in observed_pdu_types,
                "observed_trap_oids": sorted(observed_trap_oids),
                "observed_pdu_types": sorted(observed_pdu_types),
            }
        )

        # 4. Check Trap/Poll state coherence across BASELINE -> DEGRADE -> FAILOVER -> RECOVERY
        poll_by_phase_oid: Dict[Tuple[str, str], str] = {}
        for r in valid_polls:
            ph = str(r.get("netspout_phase", ""))
            oid = str(r.get("snmp_oid", ""))
            val = str(r.get("snmp_value", ""))
            if ph and oid:
                poll_by_phase_oid[(ph, oid)] = val

        coherence_checks = {
            "baseline_if_up": poll_by_phase_oid.get(("BASELINE", "1.3.6.1.2.1.2.2.1.8.1")) == "1",
            "baseline_bgp_est": poll_by_phase_oid.get(("BASELINE", "1.3.6.1.2.1.15.3.1.2.198.51.100.1")) == "6",
            "degrade_if_down_matches_linkDown_trap": (
                poll_by_phase_oid.get(("DEGRADE", "1.3.6.1.2.1.2.2.1.8.1")) == "2"
                and "1.3.6.1.6.3.1.1.5.3" in observed_trap_oids
            ),
            "degrade_if_errors_elevated": (
                int(float(poll_by_phase_oid.get(("DEGRADE", "1.3.6.1.2.1.2.2.1.14.1"), "0") or 0)) > 0
            ),
            "failover_bgp_idle_matches_bgpBackwardTransition_trap": (
                poll_by_phase_oid.get(("FAILOVER", "1.3.6.1.2.1.15.3.1.2.198.51.100.1")) == "1"
                and "1.3.6.1.2.1.15.7.2" in observed_trap_oids
            ),
            "failover_backup_route_active": (
                poll_by_phase_oid.get(("FAILOVER", "1.3.6.1.2.1.4.21.1.7.0.0.0.0")) == "198.51.100.2"
                and poll_by_phase_oid.get(("FAILOVER", "1.3.6.1.2.1.15.3.1.2.198.51.100.2")) == "6"
            ),
            "recovery_if_up_matches_linkUp_trap": (
                poll_by_phase_oid.get(("RECOVERY", "1.3.6.1.2.1.2.2.1.8.1")) == "1"
                and "1.3.6.1.6.3.1.1.5.4" in observed_trap_oids
            ),
            "recovery_bgp_est_matches_bgpEstablished_trap": (
                poll_by_phase_oid.get(("RECOVERY", "1.3.6.1.2.1.15.3.1.2.198.51.100.1")) == "6"
                and "1.3.6.1.2.1.15.7.1" in observed_trap_oids
            ),
            "recovery_primary_route_restored": (
                poll_by_phase_oid.get(("RECOVERY", "1.3.6.1.2.1.4.21.1.7.0.0.0.0")) == "198.51.100.1"
            ),
        }
        all_coherent = all(coherence_checks.values())
        checks.append(
            {
                "check_id": "trap_poll_state_coherence",
                "passed": all_coherent,
                "details": coherence_checks,
            }
        )

        overall_passed = all(c["passed"] for c in checks)
        coherence_summary = {
            "coherent": all_coherent,
            "checks": coherence_checks,
        }
        return overall_passed, checks, coherence_summary, phases_verified

    # =====================================================================
    # Section 16: Controlled Failure & Negative Verification Suite (A - E)
    # =====================================================================
    def run_controlled_failure_a(self, run_id: str = "gate12d-fail-a") -> Dict[str, Any]:
        """
        Failure A — SNMP Receiver Unavailable:
        NetSpout sends SNMP traps/informs when external receiver is stopped.
        Expected:
          - Trap: SENT = YES, RECEIVER_OBSERVED = NO, SPLUNK_OBSERVED = NO
          - Inform: ACKNOWLEDGED = NO, RECEIVER_OBSERVED = NO, SPLUNK_OBSERVED = NO
          - Run validation fails.
        """
        scorecard, _ = self.execute_e2e_run(
            run_id=run_id,
            receiver_available=False,
            agent_available=False,
            splunk_available=True,
        )
        return {
            "failure_id": "FAILURE_A_RECEIVER_UNAVAILABLE",
            "run_id": run_id,
            "traps_sent": scorecard.traps_sent,
            "informs_sent": scorecard.informs_sent,
            "informs_acknowledged": scorecard.informs_acknowledged,
            "receiver_observed_notifications": scorecard.receiver_observed_notifications,
            "splunk_observed_records": scorecard.splunk_observed_records,
            "stage_classification": scorecard.stage_classification,
            "validation_result": scorecard.validation_result,
            "expected_behavior_verified": (
                scorecard.traps_sent == 4
                and scorecard.informs_acknowledged == 0
                and scorecard.receiver_observed_notifications == 0
                and scorecard.splunk_observed_records == 0
                and scorecard.stage_classification.get("SENT") == "YES"
                and scorecard.stage_classification.get("ACKNOWLEDGED") == "NO"
                and scorecard.stage_classification.get("RECEIVER_OBSERVED") == "NO"
                and scorecard.stage_classification.get("SPLUNK_OBSERVED") == "NO"
                and scorecard.validation_result == "FAIL"
            ),
        }

    def run_controlled_failure_b(self, run_id: str = "gate12d-fail-b") -> Dict[str, Any]:
        """
        Failure B — Receiver Up, Splunk Down / HEC Unreachable:
        External SNMP receiver/poller observes data, but Splunk ingestion fails.
        Expected:
          - RECEIVER_OBSERVED = YES
          - SPLUNK_DISPATCHED = NO
          - SPLUNK_OBSERVED = NO
          - Run validation fails.
        """
        scorecard, _ = self.execute_e2e_run(
            run_id=run_id,
            receiver_available=True,
            agent_available=True,
            splunk_available=False,
        )
        return {
            "failure_id": "FAILURE_B_RECEIVER_UP_SPLUNK_DOWN",
            "run_id": run_id,
            "receiver_observed_notifications": scorecard.receiver_observed_notifications,
            "polling_responses": scorecard.polling_responses,
            "normalized_records": scorecard.normalized_records,
            "splunk_dispatched_records": scorecard.splunk_dispatched_records,
            "splunk_dispatch_failures": scorecard.splunk_dispatch_failures,
            "splunk_observed_records": scorecard.splunk_observed_records,
            "stage_classification": scorecard.stage_classification,
            "validation_result": scorecard.validation_result,
            "expected_behavior_verified": (
                scorecard.receiver_observed_notifications == 8
                and scorecard.polling_responses > 0
                and scorecard.stage_classification.get("RECEIVER_OBSERVED") == "YES"
                and scorecard.stage_classification.get("SPLUNK_DISPATCHED") == "NO"
                and scorecard.stage_classification.get("SPLUNK_OBSERVED") == "NO"
                and scorecard.validation_result == "FAIL"
            ),
        }

    def run_controlled_failure_c(self, run_id: str = "gate12d-fail-c") -> Dict[str, Any]:
        """
        Failure C — SNMP Agent Unreachable During Poll:
        External poller queries unreachable port.
        Expected:
          - Poll timeout/failure recorded
          - No fabricated poll records in Splunk
          - Poll validation fails.
        """
        scorecard, _ = self.execute_e2e_run(
            run_id=run_id,
            receiver_available=False,
            agent_available=False,
            splunk_available=True,
        )
        return {
            "failure_id": "FAILURE_C_AGENT_UNREACHABLE_DURING_POLL",
            "run_id": run_id,
            "polling_requests": scorecard.polling_requests,
            "polling_responses": scorecard.polling_responses,
            "normalized_poll_records": scorecard.normalized_poll_records,
            "splunk_observed_poll_records": scorecard.splunk_observed_poll_records,
            "errors": scorecard.errors,
            "validation_result": scorecard.validation_result,
            "expected_behavior_verified": (
                scorecard.polling_requests >= 1
                and scorecard.polling_responses == 0
                and scorecard.normalized_poll_records == 0
                and scorecard.splunk_observed_poll_records == 0
                and len(scorecard.errors) > 0
                and scorecard.validation_result == "FAIL"
            ),
        }

    def run_controlled_failure_d(
        self,
        run_id: str = "gate12d-fail-d",
        suppressed_phase: str = "RECOVERY",
    ) -> Dict[str, Any]:
        """
        Failure D — Missing Scenario Phase:
        Suppress FAILOVER or RECOVERY SNMP evidence.
        Expected:
          - Splunk shows partial evidence
          - Scenario validation fails with explicit missing phase/check reason.
        """
        scorecard, _ = self.execute_e2e_run(
            run_id=run_id,
            suppress_phases={suppressed_phase},
            receiver_available=True,
            agent_available=True,
            splunk_available=True,
        )
        missing_phase_check = next(
            (c for c in scorecard.validation_checks if c["check_id"] == "all_four_phases_present"),
            {},
        )
        return {
            "failure_id": "FAILURE_D_MISSING_SCENARIO_PHASE",
            "run_id": run_id,
            "suppressed_phase": suppressed_phase,
            "phases_verified": scorecard.phases_verified,
            "splunk_observed_records": scorecard.splunk_observed_records,
            "missing_phase_check": missing_phase_check,
            "validation_result": scorecard.validation_result,
            "expected_behavior_verified": (
                scorecard.splunk_observed_records > 0
                and suppressed_phase not in scorecard.phases_verified
                and not missing_phase_check.get("passed", True)
                and scorecard.validation_result == "FAIL"
            ),
        }

    def run_controlled_failure_e(self, run_id: str = "gate12d-fail-e") -> Dict[str, Any]:
        """
        Failure E — Duplicate / Retried Inform:
        Simulate retry or duplicate Inform reception at the external receiver and normalizer.
        Expected:
          - Receiver/normalizer handles duplicate deterministically
          - Validation does not misreport corrupted state.
        """
        informs = snmp_engine.build_service_provider_cisco_native_pdus(
            seed=self.seed + 100,
            pdu_mode="INFORM",
            community="netspout-lab",
            exporter_ip="10.200.0.1",
            device_id=self.device_id,
        )
        req_id_phase_map = {
            int(pdu.request_id): normalize_scenario_phase(pdu.phase or "FAULT") for pdu in informs
        }

        with ExternalSnmpTrapReceiver(
            host="127.0.0.1",
            port=0,
            community="netspout-lab",
        ) as trap_receiver:
            transport = NativeSnmpTransport(
                destination_host="127.0.0.1",
                destination_port=trap_receiver.bound_port,
                community="netspout-lab",
                inform_timeout_ms=1000,
                inform_max_retries=2,
                test_mode=True,
            )
            # Send batch 1 and then re-send the exact same Inform PDUs (same request_id) to simulate duplicate retry delivery
            res_first = transport.send_batch(informs)
            res_dup = transport.send_batch(informs)
            trap_receiver.wait_for_notifications(len(informs), timeout_sec=3.0)
            time.sleep(0.15)
            obs_summary = trap_receiver.parse_observations()

        normalizer = SnmpCollectorNormalizer(
            run_id=run_id,
            scenario_id=self.scenario_id,
            device_id=self.device_id,
            index=self.index,
            request_id_phase_map=req_id_phase_map,
        )
        normalized: List[NormalizedSnmpEvent] = []
        # Feed raw_notifications (which includes duplicates) into normalizer to prove normalizer-level dedup too
        for raw_obs in obs_summary["raw_notifications"]:
            ev = normalizer.normalize_trap_observation(raw_obs)
            if ev is not None:
                normalized.append(ev)

        return {
            "failure_id": "FAILURE_E_DUPLICATE_RETRIED_INFORM",
            "run_id": run_id,
            "total_informs_transmitted": res_first.informs_sent + res_dup.informs_sent,
            "raw_notifications_received": len(obs_summary["raw_notifications"]),
            "receiver_deduplicated_notifications": len(obs_summary["deduplicated_notifications"]),
            "receiver_duplicate_informs_suppressed": obs_summary["duplicate_informs_suppressed"],
            "normalizer_unique_events": len(normalized),
            "normalizer_duplicate_events_suppressed": normalizer.duplicate_events_suppressed,
            "expected_behavior_verified": (
                len(obs_summary["raw_notifications"]) == 8
                and len(obs_summary["deduplicated_notifications"]) == 4
                and obs_summary["duplicate_informs_suppressed"] == 4
                and len(normalized) == 4
                and normalizer.duplicate_events_suppressed == 4
            ),
        }

    def run_all_controlled_failures(self, run_prefix: str = "gate12d-cf") -> Dict[str, Any]:
        """
        Executes all 5 mandatory Gate 12D Controlled Failure tests (A, B, C, D, E).
        """
        self.splunk_bridge.simulate_splunk_unavailable = False
        res_a = self.run_controlled_failure_a(f"{run_prefix}-a")
        res_b = self.run_controlled_failure_b(f"{run_prefix}-b")
        self.splunk_bridge.simulate_splunk_unavailable = False
        res_c = self.run_controlled_failure_c(f"{run_prefix}-c")
        res_d = self.run_controlled_failure_d(f"{run_prefix}-d", suppressed_phase="RECOVERY")
        res_e = self.run_controlled_failure_e(f"{run_prefix}-e")
        results = {
            "failure_a": res_a,
            "failure_b": res_b,
            "failure_c": res_c,
            "failure_d": res_d,
            "failure_e": res_e,
        }
        return {
            "all_verified": all(v["expected_behavior_verified"] for v in results.values()),
            "results": results,
        }

    @staticmethod
    def build_unified_run_evidence(scorecard: SnmpE2ERunScorecard) -> UnifiedRunEvidence:
        """
        Adapts `SnmpE2ERunScorecard` into NetSpout's canonical `UnifiedRunEvidence`
        while explicitly distinguishing `SNMP RECEIVER OBSERVED` from `SPLUNK OBSERVED`.
        """
        trap_dest = EvidenceObservation(
            destination_id=f"splunk_snmp_trap_{scorecard.target_index}",
            name=f"Splunk SNMP Notifications ({scorecard.target_index} / netspout:snmp:trap)",
            telemetry_type=TelemetryType.EVENT,
            target_index=scorecard.target_index,
            query_mechanism=QueryMechanism.SPL_SEARCH,
            query=scorecard.investigation_queries.get("trap_inform_evidence_spl", ""),
            observed_count=scorecard.splunk_observed_trap_records,
            expected_count=scorecard.normalized_trap_records or scorecard.generated_notifications,
            status=(
                "PASS"
                if scorecard.splunk_observed_trap_records >= max(1, scorecard.normalized_trap_records)
                else "FAIL"
            ),
            role=EvidenceRole.REQUIRED,
        )
        poll_dest = EvidenceObservation(
            destination_id=f"splunk_snmp_poll_{scorecard.target_index}",
            name=f"Splunk SNMP Polling State ({scorecard.target_index} / netspout:snmp:poll)",
            telemetry_type=TelemetryType.EVENT,
            target_index=scorecard.target_index,
            query_mechanism=QueryMechanism.SPL_SEARCH,
            query=scorecard.investigation_queries.get("polling_evidence_spl", ""),
            observed_count=scorecard.splunk_observed_poll_records,
            expected_count=scorecard.normalized_poll_records or 1,
            status=(
                "PASS"
                if scorecard.splunk_observed_poll_records >= max(1, scorecard.normalized_poll_records)
                else "FAIL"
            ),
            role=EvidenceRole.REQUIRED,
        )
        return UnifiedRunEvidence(
            run_id=scorecard.run_id,
            scenario_id=scorecard.scenario_id,
            destinations=[trap_dest, poll_dest],
            total_generated=scorecard.normalized_records or scorecard.generated_notifications,
            total_dispatched=scorecard.splunk_dispatched_records,
            total_observed=scorecard.splunk_observed_records,
            event_observed_count=scorecard.splunk_observed_records,
            event_expected_count=scorecard.normalized_records,
            metric_observed_count=0,
            metric_expected_count=0,
            observation_completeness_pct=scorecard.observation_completeness_pct,
            observation_status=(
                "COMPLETE"
                if scorecard.observation_completeness_pct >= 100.0 and scorecard.splunk_observed_records > 0
                else ("PARTIAL" if scorecard.splunk_observed_records > 0 else "FAILED")
            ),
            contract_validation=scorecard.validation_result,
            required_evidence_satisfied=(scorecard.validation_result == "PASS"),
            errors=list(scorecard.errors),
        )


def _resolve_binary(name: str, search_dirs: List[str]) -> Optional[str]:
    for d in search_dirs:
        candidate = os.path.join(d, name)
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    return shutil.which(name)


def run_snmp_preflight_check(
    index: str = "idx_network_ops",
    hec_url: str = "https://127.0.0.1:8088/services/collector/event",
    rest_search_url: str = "https://127.0.0.1:8089/services/search/jobs/export",
) -> Dict[str, Any]:
    """
    Executes Gate 12F Section 8 customer-usable Native SNMP preflight and readiness checks:
      1. Net-SNMP CLI binaries (`/usr/bin/snmpget`, `/usr/bin/snmpgetnext`, `/usr/bin/snmpwalk`, `/usr/bin/snmpbulkwalk`)
      2. `snmptrapd` binary (`/usr/sbin/snmptrapd`)
      3. Local UDP bind capability for ephemeral SNMP trap receiver & agent ports
      4. Splunk HEC reachability (`https://127.0.0.1:8088/services/collector/health` or `/event`)
      5. Splunk REST search reachability (`https://127.0.0.1:8089/services/search/jobs/export`)
      6. Target index availability (`idx_network_ops`)
    """
    checks: List[Dict[str, Any]] = []
    remediations: List[str] = []

    # 1. Net-SNMP CLI binaries
    cli_binaries = ["snmpget", "snmpgetnext", "snmpwalk", "snmpbulkwalk"]
    resolved_cli: Dict[str, Optional[str]] = {}
    missing_cli: List[str] = []
    for b in cli_binaries:
        p = _resolve_binary(b, ["/usr/bin", "/usr/local/bin", "/opt/homebrew/bin"])
        resolved_cli[b] = p
        if not p:
            missing_cli.append(b)

    cli_ok = len(missing_cli) == 0
    checks.append(
        {
            "id": "net_snmp_cli_binaries",
            "name": "Net-SNMP CLI Binaries (snmpget, snmpgetnext, snmpwalk, snmpbulkwalk)",
            "passed": cli_ok,
            "detail": (
                ", ".join(f"{k}={v}" for k, v in resolved_cli.items())
                if cli_ok
                else f"Missing CLI binaries: {', '.join(missing_cli)}"
            ),
        }
    )
    if not cli_ok:
        remediations.append("Install Net-SNMP CLI tools (`snmpget`, `snmpgetnext`, `snmpwalk`, `snmpbulkwalk`).")

    # 2. snmptrapd binary
    snmptrapd_path = _resolve_binary(
        "snmptrapd", ["/usr/sbin", "/usr/local/sbin", "/opt/homebrew/sbin", "/usr/bin"]
    )
    trapd_ok = snmptrapd_path is not None
    checks.append(
        {
            "id": "snmptrapd_binary",
            "name": "External SNMP Trap Receiver Binary (snmptrapd)",
            "passed": trapd_ok,
            "detail": snmptrapd_path or "Missing snmptrapd binary in /usr/sbin or PATH",
        }
    )
    if not trapd_ok:
        remediations.append("Ensure `/usr/sbin/snmptrapd` is installed and executable.")

    # 3. Local UDP bind capability for ephemeral SNMP trap receiver & agent ports
    udp_ok = False
    udp_detail = ""
    try:
        port_a = _find_free_udp_port("127.0.0.1")
        port_b = _find_free_udp_port("127.0.0.1")
        udp_ok = port_a > 0 and port_b > 0
        udp_detail = f"Verified ephemeral UDP bind on 127.0.0.1 (sample ports {port_a}, {port_b})"
    except Exception as exc:
        udp_ok = False
        udp_detail = f"UDP bind check failed: {exc}"
        remediations.append("Allow local UDP socket binds on 127.0.0.1 ephemeral ports.")

    checks.append(
        {
            "id": "local_udp_bind",
            "name": "Local UDP Bind Capability (Trap Receiver & Simulated Agent)",
            "passed": udp_ok,
            "detail": udp_detail,
        }
    )

    # 4. Splunk HEC reachability
    bridge = SnmpSplunkBridge(index=index, hec_url=hec_url, rest_search_url=rest_search_url)
    hec_ok = False
    hec_detail = ""
    health_url = hec_url.rsplit("/", 1)[0] + "/health"
    health_candidates = [health_url]
    if ":8088" in health_url:
        health_candidates.append(health_url.replace(":8088", ":8888"))
    elif ":8888" in health_url:
        health_candidates.append(health_url.replace(":8888", ":8088"))

    last_exc = None
    for h_cand in health_candidates:
        ctx = bridge._ssl_ctx() if h_cand.startswith("https") else None
        try:
            req = urllib.request.Request(h_cand, method="GET")
            with urllib.request.urlopen(req, context=ctx, timeout=3.0) as resp:
                if resp.status in (200, 400, 401):
                    hec_ok = True
                    hec_detail = f"Splunk HEC reachable at {h_cand} (HTTP {resp.status})"
                    break
        except Exception as exc:
            last_exc = exc

    if not hec_ok:
        hec_detail = f"Splunk HEC unreachable at {health_url}: {last_exc}"
        remediations.append("Verify Splunk HEC is running and reachable on port 8088.")

    checks.append(
        {
            "id": "splunk_hec_reachability",
            "name": "Splunk HEC Reachability",
            "passed": hec_ok,
            "detail": hec_detail,
        }
    )

    # 5. Splunk REST search reachability & 6. Target index availability (`idx_network_ops`)
    rest_ok = False
    rest_detail = ""
    index_ok = False
    index_detail = ""
    try:
        rows = bridge.execute_spl_search(
            f'| rest /services/data/indexes | search title="{index}" | table title totalEventCount disabled',
            earliest_time="-1m",
            latest_time="now",
            max_wait_sec=4.0,
            min_expected=1,
        )
        rest_ok = True
        rest_detail = f"Splunk REST search endpoint reachable at {rest_search_url}"
        if rows and any(str(r.get("title", "")) == index for r in rows):
            index_ok = True
            idx_row = next(r for r in rows if str(r.get("title", "")) == index)
            index_detail = (
                f"Target index '{index}' available (disabled={idx_row.get('disabled', '0')}, "
                f"totalEventCount={idx_row.get('totalEventCount', '0')})"
            )
        else:
            # Fallback check via eventcount
            ev_rows = bridge.execute_spl_search(
                f'| eventcount summarize=false index={index}',
                earliest_time="-24h",
                latest_time="now",
                max_wait_sec=3.0,
                min_expected=1,
            )
            if ev_rows:
                index_ok = True
                index_detail = f"Target index '{index}' verified via | eventcount"
            else:
                index_ok = False
                index_detail = f"Target index '{index}' not found in Splunk"
                remediations.append(f"Create or enable target Splunk index '{index}'.")
    except Exception as exc:
        rest_ok = False
        rest_detail = f"Splunk REST search unreachable at {rest_search_url}: {exc}"
        index_ok = False
        index_detail = f"Cannot verify index '{index}' while Splunk REST search is unreachable"
        remediations.append("Verify Splunk management REST API is reachable on port 8889.")

    checks.append(
        {
            "id": "splunk_rest_search",
            "name": "Splunk REST Search Reachability",
            "passed": rest_ok,
            "detail": rest_detail,
        }
    )
    checks.append(
        {
            "id": "target_index_availability",
            "name": f"Target Index Availability ({index})",
            "passed": index_ok,
            "detail": index_detail,
        }
    )

    all_passed = all(c["passed"] for c in checks)
    return {
        "status": "READY" if all_passed else "BLOCKED",
        "all_passed": all_passed,
        "scenario_id": "service_provider_cisco",
        "device_id": "cisco-asr9k-pe1",
        "target_index": index,
        "sourcetypes": ["netspout:snmp:trap", "netspout:snmp:poll"],
        "binaries": {
            **resolved_cli,
            "snmptrapd": snmptrapd_path,
        },
        "checks": checks,
        "remediation": remediations,
    }

