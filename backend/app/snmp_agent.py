# =========================================================================
# AUTO-GENERATED PACKAGED COPY — DO NOT EDIT DIRECTLY!
# Authoritative Source of Truth: src/netspout_core/snmp_agent.py
# Re-generate using: python3 scripts/sync_core.py
# =========================================================================
"""
NetSpout Gate 12C — Native SNMPv2c Simulated Polling Agent, Canonical OID Store & Walk Engine.
Conforms to:
  - RFC 1901 (Community-Based SNMPv2c)
  - RFC 2578 (SMIv2 Structure of Management Information)
  - RFC 3416 (Version 2 of the Protocol Operations for SNMP: GET, GETNEXT, GETBULK, RESPONSE)
  - RFC 3418 (SNMPv2-MIB)
  - RFC 2863 (IF-MIB)
  - RFC 4273 (BGP4-MIB)
"""

import bisect
import ipaddress
import socket
import subprocess
import threading
import time
from typing import Any, Dict, List, Optional, Set, Tuple, Union

try:
    from netspout_core.models import (
        OidFidelityClass,
        SnmpAsn1Type,
        SnmpEvidenceStage,
        SnmpMessage,
        SnmpOidEntry,
        SnmpPduType,
        SnmpPollingEvidence,
        SnmpResponse,
        SnmpVarBind,
        SnmpVersion,
    )
    from netspout_core.rate_limiter import TokenBucketRateLimiter
    from netspout_core.snmp_ber import (
        MAX_OID_ARCS,
        MAX_SNMP_UDP_PAYLOAD_BYTES,
        InvalidSnmpOidError,
        SnmpBerDecodeError,
        SnmpBerDecoder,
        SnmpBerEncodeError,
        SnmpBerEncoder,
        SnmpCommunityMismatchError,
        SnmpPayloadSizeError,
        UnsupportedSnmpVersionError,
    )
    from netspout_core.transport_native_snmp import write_snmp_pcap
    from netspout_core.transport_safety import (
        DestinationSecurityException,
        is_safe_ip,
    )
except ImportError:
    try:
        from app.models import (
            OidFidelityClass,
            SnmpAsn1Type,
            SnmpEvidenceStage,
            SnmpMessage,
            SnmpOidEntry,
            SnmpPduType,
            SnmpPollingEvidence,
            SnmpResponse,
            SnmpVarBind,
            SnmpVersion,
        )
        from app.rate_limiter import TokenBucketRateLimiter
        from app.snmp_ber import (
            MAX_OID_ARCS,
            MAX_SNMP_UDP_PAYLOAD_BYTES,
            InvalidSnmpOidError,
            SnmpBerDecodeError,
            SnmpBerDecoder,
            SnmpBerEncodeError,
            SnmpBerEncoder,
            SnmpCommunityMismatchError,
            SnmpPayloadSizeError,
            UnsupportedSnmpVersionError,
        )
        from app.transport_native_snmp import write_snmp_pcap
        from app.transport_safety import (
            DestinationSecurityException,
            is_safe_ip,
        )
    except ImportError:
        from models import (
            OidFidelityClass,
            SnmpAsn1Type,
            SnmpEvidenceStage,
            SnmpMessage,
            SnmpOidEntry,
            SnmpPduType,
            SnmpPollingEvidence,
            SnmpResponse,
            SnmpVarBind,
            SnmpVersion,
        )
        from rate_limiter import TokenBucketRateLimiter
        from snmp_ber import (
            MAX_OID_ARCS,
            MAX_SNMP_UDP_PAYLOAD_BYTES,
            InvalidSnmpOidError,
            SnmpBerDecodeError,
            SnmpBerDecoder,
            SnmpBerEncodeError,
            SnmpBerEncoder,
            SnmpCommunityMismatchError,
            SnmpPayloadSizeError,
            UnsupportedSnmpVersionError,
        )
        from transport_native_snmp import write_snmp_pcap
        from transport_safety import (
            DestinationSecurityException,
            is_safe_ip,
        )


# =========================================================================
# Gate 12C Safety & Protocol Constants
# =========================================================================
DEFAULT_AGENT_BIND_HOST = "127.0.0.1"
DEFAULT_AGENT_BIND_PORT = 1161
DEFAULT_AGENT_COMMUNITY = "netspout-lab"

DEFAULT_GETBULK_MAX_REPETITIONS = 25
HARD_MAX_GETBULK_REPETITIONS = 50
MAX_VARBINDS_PER_RESPONSE = 100

DEFAULT_AGENT_RATE_LIMIT_PPS = 250
MAX_AGENT_RATE_LIMIT_PPS = 1000
DEFAULT_AGENT_MAX_PACKETS = 50000

# RFC 3416 Error-Status Codes
SNMP_ERR_NO_ERROR = 0
SNMP_ERR_TOO_BIG = 1
SNMP_ERR_NO_SUCH_NAME = 2
SNMP_ERR_BAD_VALUE = 3
SNMP_ERR_READ_ONLY = 4
SNMP_ERR_GEN_ERR = 5
SNMP_ERR_NO_ACCESS = 6
SNMP_ERR_NOT_WRITABLE = 17


# =========================================================================
# Numeric Lexicographic OID Ordering Utilities (Section 6)
# =========================================================================
def normalize_oid_str(oid: str) -> str:
    """
    Normalizes an OID string by stripping an optional leading dot (e.g., '.1.3.6.1...' -> '1.3.6.1...')
    and validating numeric dotted-decimal syntax.
    """
    if not isinstance(oid, str):
        raise InvalidSnmpOidError(f"OID must be a string, got {type(oid).__name__}")
    s = oid.strip()
    if s.startswith("."):
        s = s[1:]
    if not s:
        raise InvalidSnmpOidError("Empty OID string")
    parts = s.split(".")
    if len(parts) < 2:
        raise InvalidSnmpOidError(f"OID must have at least 2 numeric arcs: {oid!r}")
    if len(parts) > MAX_OID_ARCS:
        raise InvalidSnmpOidError(f"OID exceeds maximum {MAX_OID_ARCS} arcs: {oid!r}")
    arcs: List[int] = []
    for p in parts:
        if not p.isdigit() or (len(p) > 1 and p.startswith("0")):
            raise InvalidSnmpOidError(f"Invalid OID arc {p!r} in {oid!r}")
        val = int(p)
        if val < 0 or val > 0xFFFFFFFF:
            raise InvalidSnmpOidError(f"OID arc {val} out of 32-bit range in {oid!r}")
        arcs.append(val)
    if arcs[0] not in (0, 1, 2):
        raise InvalidSnmpOidError(f"First OID arc must be 0, 1, or 2, got {arcs[0]}")
    if arcs[0] in (0, 1) and arcs[1] >= 40:
        raise InvalidSnmpOidError(f"Second OID arc must be < 40 when first arc is {arcs[0]}")
    return ".".join(str(a) for a in arcs)


def oid_to_tuple(oid: str) -> Tuple[int, ...]:
    """
    Converts a dotted-decimal OID string into a tuple of integers for strict
    numeric lexicographic comparison (e.g. (1, 3, 6, 1, 2, 1, 2, 2, 1, 10, 2) < (..., 10, 10)).
    """
    norm = normalize_oid_str(oid)
    return tuple(int(part) for part in norm.split("."))


def compare_oids(oid_a: str, oid_b: str) -> int:
    """
    Compares two OID strings numerically:
      returns -1 if oid_a < oid_b
      returns  0 if oid_a == oid_b
      returns +1 if oid_a > oid_b
    """
    ta = oid_to_tuple(oid_a)
    tb = oid_to_tuple(oid_b)
    if ta < tb:
        return -1
    if ta > tb:
        return 1
    return 0


def is_oid_in_subtree(oid: str, subtree_prefix: str) -> bool:
    """
    Returns True if `oid` is numerically inside `subtree_prefix` (either equal or a descendant arc).
    """
    t_oid = oid_to_tuple(oid)
    t_pre = oid_to_tuple(subtree_prefix)
    return len(t_oid) >= len(t_pre) and t_oid[: len(t_pre)] == t_pre


# =========================================================================
# Canonical Deterministic OID Store (Section 6)
# =========================================================================
class SnmpOidStore:
    """
    Deterministic, read-only, numerically ordered OID store representing simulated
    SNMPv2c device state for a given scenario, seed, device, and operational phase.
    """

    def __init__(
        self,
        scenario_id: str = "service_provider_cisco",
        device_id: str = "cisco-asr9k-pe1",
        phase: str = "BASELINE",
        seed: int = 42,
    ):
        self.scenario_id = scenario_id
        self.device_id = device_id
        self.phase = phase.upper()
        self.seed = int(seed)

        self._entries_by_oid: Dict[str, SnmpOidEntry] = {}
        self._sorted_tuples: List[Tuple[int, ...]] = []
        self._sorted_oids: List[str] = []
        self._base_oid_tuples: Set[Tuple[int, ...]] = set()

    def register(self, entry: SnmpOidEntry) -> None:
        """
        Inserts or updates an SnmpOidEntry in strict numeric lexicographic order.
        Forces writable=False to guarantee read-only agent behavior (Section 16).
        """
        norm_oid = normalize_oid_str(entry.oid)
        oid_tup = oid_to_tuple(norm_oid)
        entry.oid = norm_oid
        entry.writable = False
        if entry.scenario_id is None:
            entry.scenario_id = self.scenario_id
        if entry.device_id is None:
            entry.device_id = self.device_id
        if entry.phase is None:
            entry.phase = self.phase

        if entry.base_oid:
            self._base_oid_tuples.add(oid_to_tuple(entry.base_oid))
        else:
            # Infer base scalar/column prefix (strip .0 or last index arc)
            if len(oid_tup) > 2:
                self._base_oid_tuples.add(oid_tup[:-1])

        if norm_oid not in self._entries_by_oid:
            idx = bisect.bisect_left(self._sorted_tuples, oid_tup)
            self._sorted_tuples.insert(idx, oid_tup)
            self._sorted_oids.insert(idx, norm_oid)

        self._entries_by_oid[norm_oid] = entry

    def __len__(self) -> int:
        return len(self._sorted_oids)

    def all_entries(self) -> List[SnmpOidEntry]:
        """Returns all SnmpOidEntry objects in strict numeric lexicographic OID order."""
        return [self._entries_by_oid[oid] for oid in self._sorted_oids]

    def all_oids(self) -> List[str]:
        """Returns all numeric OID strings in strict numeric lexicographic order."""
        return list(self._sorted_oids)

    def mib_families(self) -> List[str]:
        """Returns sorted list of distinct source MIB families in the store."""
        return sorted({e.source_mib for e in self._entries_by_oid.values() if e.source_mib})

    def has_base_object(self, oid_tup: Tuple[int, ...]) -> bool:
        """
        Determines whether `oid_tup` matches or falls under a known implemented base
        scalar or table column OID (used to distinguish noSuchInstance vs noSuchObject per RFC 3416).
        """
        for base_tup in self._base_oid_tuples:
            if len(oid_tup) >= len(base_tup) and oid_tup[: len(base_tup)] == base_tup:
                return True
        return False

    def get_exact(self, oid: str) -> SnmpVarBind:
        """
        RFC 3416 Section 4.2.1 GET lookup:
          - Exact OID match -> returns object's SnmpVarBind.
          - Base object exists but instance missing -> returns noSuchInstance (0x81).
          - Object subtree not implemented -> returns noSuchObject (0x80).
        """
        norm_oid = normalize_oid_str(oid)
        entry = self._entries_by_oid.get(norm_oid)
        if entry is not None:
            return entry.to_varbind()

        oid_tup = oid_to_tuple(norm_oid)
        if self.has_base_object(oid_tup):
            return SnmpVarBind(
                oid=norm_oid,
                asn1_type="noSuchInstance",
                value=None,
                fidelity=OidFidelityClass.STANDARD_VERIFIED.value,
            )
        return SnmpVarBind(
            oid=norm_oid,
            asn1_type="noSuchObject",
            value=None,
            fidelity=OidFidelityClass.STANDARD_VERIFIED.value,
        )

    def get_next(self, oid: str) -> SnmpVarBind:
        """
        RFC 3416 Section 4.2.2 GETNEXT lookup:
          - Finds the strictly greater numeric lexicographic successor OID in the store.
          - If no greater OID exists -> returns endOfMibView (0x82) with the requested OID.
          - Never wraps around to the beginning of the tree.
        """
        norm_oid = normalize_oid_str(oid)
        oid_tup = oid_to_tuple(norm_oid)
        idx = bisect.bisect_right(self._sorted_tuples, oid_tup)
        if idx < len(self._sorted_oids):
            next_oid = self._sorted_oids[idx]
            return self._entries_by_oid[next_oid].to_varbind()
        return SnmpVarBind(
            oid=norm_oid,
            asn1_type="endOfMibView",
            value=None,
            fidelity=OidFidelityClass.STANDARD_VERIFIED.value,
        )

    def walk_subtree(self, subtree_prefix: str) -> List[SnmpVarBind]:
        """
        Walks all objects within `subtree_prefix` using repeated `get_next` operations,
        terminating when `endOfMibView` is reached or the returned OID leaves `subtree_prefix`.
        """
        norm_prefix = normalize_oid_str(subtree_prefix)
        results: List[SnmpVarBind] = []
        current_oid = norm_prefix
        seen: Set[str] = set()

        while True:
            vb = self.get_next(current_oid)
            if vb.asn1_type == "endOfMibView":
                break
            if not is_oid_in_subtree(vb.oid, norm_prefix):
                break
            if vb.oid in seen:
                break
            seen.add(vb.oid)
            results.append(vb)
            current_oid = vb.oid

        return results

    def to_snapshot_dict(self) -> Dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "device_id": self.device_id,
            "phase": self.phase,
            "seed": self.seed,
            "total_oids": len(self._sorted_oids),
            "mib_families": self.mib_families(),
            "entries": [
                {
                    "oid": e.oid,
                    "symbolic_name": e.symbolic_name,
                    "asn1_type": e.asn1_type,
                    "value": e.value.hex() if isinstance(e.value, (bytes, bytearray)) else e.value,
                    "fidelity": e.fidelity,
                    "source_mib": e.source_mib,
                    "writable": e.writable,
                }
                for e in self.all_entries()
            ],
        }


# =========================================================================
# Canonical Phase Normalization & `service_provider_cisco` State Builder
# =========================================================================
CANONICAL_PHASE_MAP: Dict[str, str] = {
    "BASELINE": "BASELINE",
    "DEGRADE": "DEGRADE",
    "FAULT": "DEGRADE",
    "FAILOVER": "FAILOVER",
    "PROPAGATE": "FAILOVER",
    "RECOVERY": "RECOVERY",
    "RECOVER": "RECOVERY",
    "VALIDATE": "RECOVERY",
}


def normalize_scenario_phase(phase: str) -> str:
    p = (phase or "BASELINE").strip().upper()
    if p not in CANONICAL_PHASE_MAP:
        raise ValueError(
            f"Unsupported scenario phase {phase!r}; expected BASELINE, DEGRADE, FAILOVER, or RECOVERY"
        )
    return CANONICAL_PHASE_MAP[p]


def build_service_provider_cisco_oid_store(
    phase: str = "BASELINE",
    seed: int = 42,
    device_id: str = "cisco-asr9k-pe1",
) -> SnmpOidStore:
    """
    Constructs the deterministic, phase-coherent OID store for `service_provider_cisco`
    across BASELINE -> DEGRADE -> FAILOVER -> RECOVERY.

    Guarantees 100% state coherence with Gate 12B Trap/Inform notifications:
      - BASELINE:
          sysUpTime.0 = 8639000
          ifOperStatus.1 (HundredGigE0/0/0/1) = 1 (up)
          bgpPeerState.198.51.100.1 = 6 (established), bgpPeerLastError = 0x0000
          ipRouteNextHop.0.0.0.0 = 198.51.100.1 (ifIndex 1, metric 10)
      - DEGRADE (coherent with IF-MIB::linkDown Trap/Inform at sysUpTime=8640000):
          sysUpTime.0 = 8640000
          ifOperStatus.1 (HundredGigE0/0/0/1) = 2 (down), ifInErrors.1 spikes
          bgpPeerState.198.51.100.1 = 1 (idle), bgpPeerLastError = 0x0400 (Hold Timer Expired)
          ipRouteNextHop.0.0.0.0 = 198.51.100.2 (ifIndex 2, metric 20)
      - FAILOVER (coherent with BGP4-MIB::bgpBackwardTransition Trap/Inform at sysUpTime=8640500):
          sysUpTime.0 = 8640500
          ifOperStatus.1 (HundredGigE0/0/0/1) = 2 (down)
          bgpPeerState.198.51.100.1 = 1 (idle), bgpPeerLastError = 0x0400
          ifOperStatus.2 (HundredGigE0/0/0/2) = 1 (up), backup interface & peer 198.51.100.2 carry failover load
          ipRouteNextHop.0.0.0.0 = 198.51.100.2 (ifIndex 2, metric 20)
      - RECOVERY (coherent with IF-MIB::linkUp + BGP4-MIB::bgpEstablished at sysUpTime=8643500):
          sysUpTime.0 = 8643500
          ifOperStatus.1 (HundredGigE0/0/0/1) = 1 (up), ifLastChange.1 = 8643000
          bgpPeerState.198.51.100.1 = 6 (established), bgpPeerLastError = 0x0000
          ipRouteNextHop.0.0.0.0 = 198.51.100.1 (ifIndex 1, metric 10)
    """
    norm_phase = normalize_scenario_phase(phase)
    seed_offset = (abs(int(seed)) % 997) * 100

    store = SnmpOidStore(
        scenario_id="service_provider_cisco",
        device_id=device_id,
        phase=norm_phase,
        seed=seed,
    )

    def _add(
        oid: str,
        name: str,
        asn1_type: str,
        value: Any,
        mib: str,
        base_oid: str,
        fidelity: str = OidFidelityClass.STANDARD_VERIFIED.value,
    ) -> None:
        store.register(
            SnmpOidEntry(
                oid=oid,
                symbolic_name=name,
                asn1_type=asn1_type,
                value=value,
                fidelity=fidelity,
                source_mib=mib,
                writable=False,
                base_oid=base_oid,
                scenario_id="service_provider_cisco",
                device_id=device_id,
                phase=norm_phase,
            )
        )

    # Phase-dependent timing and state parameters
    if norm_phase == "BASELINE":
        sys_uptime = 8639000
        if1_oper = 1  # up
        if1_last_change = 12000
        if1_in_octets = 125000000 + seed_offset
        if1_out_octets = 118000000 + seed_offset
        if1_hc_in_octets = 98500000000 + (seed_offset * 1000)
        if1_hc_out_octets = 91200000000 + (seed_offset * 1000)
        if1_in_pkts = 950000 + seed_offset
        if1_out_pkts = 910000 + seed_offset
        if1_in_errors = 0
        if1_out_errors = 0

        if2_in_octets = 15000000 + seed_offset
        if2_out_octets = 14000000 + seed_offset
        if2_hc_in_octets = 4200000000 + (seed_offset * 100)
        if2_hc_out_octets = 4100000000 + (seed_offset * 100)
        if2_in_pkts = 120000 + seed_offset
        if2_out_pkts = 115000 + seed_offset

        peer1_state = 6  # established
        peer1_last_err = b"\x00\x00"
        peer1_transitions = 1
        peer1_est_time = 86270
        peer1_in_updates = 1420 + (seed % 50)
        peer1_out_updates = 1380 + (seed % 50)

        peer2_in_updates = 640 + (seed % 30)
        peer2_out_updates = 610 + (seed % 30)

        active_route_if = 1
        active_route_metric = 10
        active_route_nexthop = "198.51.100.1"
        active_route_age = 86270

    elif norm_phase == "DEGRADE":
        sys_uptime = 8640000
        if1_oper = 2  # down (matches IF-MIB::linkDown Trap/Inform)
        if1_last_change = 8640000
        if1_in_octets = 126500000 + seed_offset
        if1_out_octets = 119200000 + seed_offset
        if1_hc_in_octets = 98650000000 + (seed_offset * 1000)
        if1_hc_out_octets = 91320000000 + (seed_offset * 1000)
        if1_in_pkts = 962000 + seed_offset
        if1_out_pkts = 921000 + seed_offset
        if1_in_errors = 485 + (seed % 25)
        if1_out_errors = 19 + (seed % 7)

        if2_in_octets = 28000000 + seed_offset
        if2_out_octets = 26500000 + seed_offset
        if2_hc_in_octets = 6800000000 + (seed_offset * 100)
        if2_hc_out_octets = 6600000000 + (seed_offset * 100)
        if2_in_pkts = 230000 + seed_offset
        if2_out_pkts = 220000 + seed_offset

        peer1_state = 1  # idle (transitioned away from established)
        peer1_last_err = b"\x04\x00"  # Hold Timer Expired
        peer1_transitions = 1
        peer1_est_time = 0
        peer1_in_updates = 1425 + (seed % 50)
        peer1_out_updates = 1385 + (seed % 50)

        peer2_in_updates = 980 + (seed % 30)
        peer2_out_updates = 940 + (seed % 30)

        active_route_if = 2
        active_route_metric = 20
        active_route_nexthop = "198.51.100.2"
        active_route_age = 1

    elif norm_phase == "FAILOVER":
        sys_uptime = 8640500
        if1_oper = 2  # down
        if1_last_change = 8640000
        if1_in_octets = 126500000 + seed_offset
        if1_out_octets = 119200000 + seed_offset
        if1_hc_in_octets = 98650000000 + (seed_offset * 1000)
        if1_hc_out_octets = 91320000000 + (seed_offset * 1000)
        if1_in_pkts = 962000 + seed_offset
        if1_out_pkts = 921000 + seed_offset
        if1_in_errors = 485 + (seed % 25)
        if1_out_errors = 19 + (seed % 7)

        if2_in_octets = 94000000 + seed_offset
        if2_out_octets = 89000000 + seed_offset
        if2_hc_in_octets = 42800000000 + (seed_offset * 1000)
        if2_hc_out_octets = 40600000000 + (seed_offset * 1000)
        if2_in_pkts = 780000 + seed_offset
        if2_out_pkts = 755000 + seed_offset

        peer1_state = 1  # idle (matches BGP4-MIB::bgpBackwardTransition Trap/Inform)
        peer1_last_err = b"\x04\x00"
        peer1_transitions = 1
        peer1_est_time = 0
        peer1_in_updates = 1425 + (seed % 50)
        peer1_out_updates = 1385 + (seed % 50)

        peer2_in_updates = 1850 + (seed % 30)
        peer2_out_updates = 1790 + (seed % 30)

        active_route_if = 2
        active_route_metric = 20
        active_route_nexthop = "198.51.100.2"
        active_route_age = 5

    else:  # RECOVERY
        sys_uptime = 8643500
        if1_oper = 1  # up (matches IF-MIB::linkUp Trap/Inform)
        if1_last_change = 8643000
        if1_in_octets = 168000000 + seed_offset
        if1_out_octets = 159000000 + seed_offset
        if1_hc_in_octets = 124500000000 + (seed_offset * 1000)
        if1_hc_out_octets = 116800000000 + (seed_offset * 1000)
        if1_in_pkts = 1290000 + seed_offset
        if1_out_pkts = 1240000 + seed_offset
        if1_in_errors = 485 + (seed % 25)
        if1_out_errors = 19 + (seed % 7)

        if2_in_octets = 102000000 + seed_offset
        if2_out_octets = 96000000 + seed_offset
        if2_hc_in_octets = 46500000000 + (seed_offset * 1000)
        if2_hc_out_octets = 44100000000 + (seed_offset * 1000)
        if2_in_pkts = 840000 + seed_offset
        if2_out_pkts = 815000 + seed_offset

        peer1_state = 6  # established (matches BGP4-MIB::bgpEstablished Trap/Inform)
        peer1_last_err = b"\x00\x00"
        peer1_transitions = 2
        peer1_est_time = 5
        peer1_in_updates = 2940 + (seed % 50)
        peer1_out_updates = 2880 + (seed % 50)

        peer2_in_updates = 2010 + (seed % 30)
        peer2_out_updates = 1950 + (seed % 30)

        active_route_if = 1
        active_route_metric = 10
        active_route_nexthop = "198.51.100.1"
        active_route_age = 5

    # ---------------------------------------------------------------------
    # 1. SNMPv2-MIB System Group (1.3.6.1.2.1.1.*)
    # ---------------------------------------------------------------------
    _add(
        "1.3.6.1.2.1.1.1.0",
        "sysDescr.0",
        "OctetString",
        "Cisco IOS XR Software (ASR9K), Version 7.9.2 [NetSpout Simulated Agent]",
        "SNMPv2-MIB",
        "1.3.6.1.2.1.1.1",
    )
    _add(
        "1.3.6.1.2.1.1.2.0",
        "sysObjectID.0",
        "ObjectIdentifier",
        "1.3.6.1.4.1.9.1.1639",
        "SNMPv2-MIB",
        "1.3.6.1.2.1.1.2",
    )
    _add(
        "1.3.6.1.2.1.1.3.0",
        "sysUpTime.0",
        "TimeTicks",
        sys_uptime,
        "SNMPv2-MIB",
        "1.3.6.1.2.1.1.3",
    )
    _add(
        "1.3.6.1.2.1.1.4.0",
        "sysContact.0",
        "OctetString",
        "noc-ops@netspout.lab",
        "SNMPv2-MIB",
        "1.3.6.1.2.1.1.4",
    )
    _add(
        "1.3.6.1.2.1.1.5.0",
        "sysName.0",
        "OctetString",
        f"{device_id}.netspout.lab",
        "SNMPv2-MIB",
        "1.3.6.1.2.1.1.5",
    )
    _add(
        "1.3.6.1.2.1.1.6.0",
        "sysLocation.0",
        "OctetString",
        "Ashburn-Core-POP1-Rack04",
        "SNMPv2-MIB",
        "1.3.6.1.2.1.1.6",
    )
    _add(
        "1.3.6.1.2.1.1.7.0",
        "sysServices.0",
        "Integer32",
        78,
        "SNMPv2-MIB",
        "1.3.6.1.2.1.1.7",
    )

    # ---------------------------------------------------------------------
    # 2. IF-MIB (1.3.6.1.2.1.2.* and 1.3.6.1.2.1.31.1.1.1.*)
    # ---------------------------------------------------------------------
    _add(
        "1.3.6.1.2.1.2.1.0",
        "ifNumber.0",
        "Integer32",
        3,
        "IF-MIB",
        "1.3.6.1.2.1.2.1",
    )

    if_rows = [
        {
            "idx": 1,
            "descr": "HundredGigE0/0/0/1",
            "name": "Hu0/0/0/1",
            "alias": "Primary-Core-Transit-AS65002",
            "type": 6,
            "mtu": 9192,
            "speed": 4294967295,
            "high_speed": 100000,
            "mac": "00:1e:be:01:00:01",
            "admin": 1,
            "oper": if1_oper,
            "last_change": if1_last_change,
            "in_octets": if1_in_octets,
            "in_ucast": if1_in_pkts,
            "in_discards": 0 if if1_oper == 1 else 32,
            "in_errors": if1_in_errors,
            "out_octets": if1_out_octets,
            "out_ucast": if1_out_pkts,
            "out_discards": 0,
            "out_errors": if1_out_errors,
            "hc_in_octets": if1_hc_in_octets,
            "hc_in_ucast": if1_in_pkts * 10,
            "hc_out_octets": if1_hc_out_octets,
            "hc_out_ucast": if1_out_pkts * 10,
        },
        {
            "idx": 2,
            "descr": "HundredGigE0/0/0/2",
            "name": "Hu0/0/0/2",
            "alias": "Backup-Core-Transit-AS65003",
            "type": 6,
            "mtu": 9192,
            "speed": 4294967295,
            "high_speed": 100000,
            "mac": "00:1e:be:01:00:02",
            "admin": 1,
            "oper": 1,
            "last_change": 12000,
            "in_octets": if2_in_octets,
            "in_ucast": if2_in_pkts,
            "in_discards": 0,
            "in_errors": 0,
            "out_octets": if2_out_octets,
            "out_ucast": if2_out_pkts,
            "out_discards": 0,
            "out_errors": 0,
            "hc_in_octets": if2_hc_in_octets,
            "hc_in_ucast": if2_in_pkts * 10,
            "hc_out_octets": if2_hc_out_octets,
            "hc_out_ucast": if2_out_pkts * 10,
        },
        {
            "idx": 3,
            "descr": "Loopback0",
            "name": "Lo0",
            "alias": "BGP-Router-ID-10.254.0.1",
            "type": 24,
            "mtu": 1500,
            "speed": 1000000000,
            "high_speed": 1000,
            "mac": "00:00:00:00:00:00",
            "admin": 1,
            "oper": 1,
            "last_change": 1000,
            "in_octets": 450000 + seed_offset,
            "in_ucast": 4200 + (seed % 100),
            "in_discards": 0,
            "in_errors": 0,
            "out_octets": 450000 + seed_offset,
            "out_ucast": 4200 + (seed % 100),
            "out_discards": 0,
            "out_errors": 0,
            "hc_in_octets": 450000 + seed_offset,
            "hc_in_ucast": 4200 + (seed % 100),
            "hc_out_octets": 450000 + seed_offset,
            "hc_out_ucast": 4200 + (seed % 100),
        },
    ]

    for row in if_rows:
        idx = row["idx"]
        _add(f"1.3.6.1.2.1.2.2.1.1.{idx}", f"ifIndex.{idx}", "Integer32", idx, "IF-MIB", "1.3.6.1.2.1.2.2.1.1")
        _add(f"1.3.6.1.2.1.2.2.1.2.{idx}", f"ifDescr.{idx}", "OctetString", row["descr"], "IF-MIB", "1.3.6.1.2.1.2.2.1.2")
        _add(f"1.3.6.1.2.1.2.2.1.3.{idx}", f"ifType.{idx}", "Integer32", row["type"], "IF-MIB", "1.3.6.1.2.1.2.2.1.3")
        _add(f"1.3.6.1.2.1.2.2.1.4.{idx}", f"ifMtu.{idx}", "Integer32", row["mtu"], "IF-MIB", "1.3.6.1.2.1.2.2.1.4")
        _add(f"1.3.6.1.2.1.2.2.1.5.{idx}", f"ifSpeed.{idx}", "Gauge32", row["speed"], "IF-MIB", "1.3.6.1.2.1.2.2.1.5")
        _add(f"1.3.6.1.2.1.2.2.1.6.{idx}", f"ifPhysAddress.{idx}", "OctetString", row["mac"], "IF-MIB", "1.3.6.1.2.1.2.2.1.6")
        _add(f"1.3.6.1.2.1.2.2.1.7.{idx}", f"ifAdminStatus.{idx}", "Integer32", row["admin"], "IF-MIB", "1.3.6.1.2.1.2.2.1.7")
        _add(f"1.3.6.1.2.1.2.2.1.8.{idx}", f"ifOperStatus.{idx}", "Integer32", row["oper"], "IF-MIB", "1.3.6.1.2.1.2.2.1.8")
        _add(f"1.3.6.1.2.1.2.2.1.9.{idx}", f"ifLastChange.{idx}", "TimeTicks", row["last_change"], "IF-MIB", "1.3.6.1.2.1.2.2.1.9")
        _add(f"1.3.6.1.2.1.2.2.1.10.{idx}", f"ifInOctets.{idx}", "Counter32", row["in_octets"], "IF-MIB", "1.3.6.1.2.1.2.2.1.10")
        _add(f"1.3.6.1.2.1.2.2.1.11.{idx}", f"ifInUcastPkts.{idx}", "Counter32", row["in_ucast"], "IF-MIB", "1.3.6.1.2.1.2.2.1.11")
        _add(f"1.3.6.1.2.1.2.2.1.13.{idx}", f"ifInDiscards.{idx}", "Counter32", row["in_discards"], "IF-MIB", "1.3.6.1.2.1.2.2.1.13")
        _add(f"1.3.6.1.2.1.2.2.1.14.{idx}", f"ifInErrors.{idx}", "Counter32", row["in_errors"], "IF-MIB", "1.3.6.1.2.1.2.2.1.14")
        _add(f"1.3.6.1.2.1.2.2.1.16.{idx}", f"ifOutOctets.{idx}", "Counter32", row["out_octets"], "IF-MIB", "1.3.6.1.2.1.2.2.1.16")
        _add(f"1.3.6.1.2.1.2.2.1.17.{idx}", f"ifOutUcastPkts.{idx}", "Counter32", row["out_ucast"], "IF-MIB", "1.3.6.1.2.1.2.2.1.17")
        _add(f"1.3.6.1.2.1.2.2.1.19.{idx}", f"ifOutDiscards.{idx}", "Counter32", row["out_discards"], "IF-MIB", "1.3.6.1.2.1.2.2.1.19")
        _add(f"1.3.6.1.2.1.2.2.1.20.{idx}", f"ifOutErrors.{idx}", "Counter32", row["out_errors"], "IF-MIB", "1.3.6.1.2.1.2.2.1.20")
        # 64-bit ifXTable extensions
        _add(f"1.3.6.1.2.1.31.1.1.1.1.{idx}", f"ifName.{idx}", "OctetString", row["name"], "IF-MIB", "1.3.6.1.2.1.31.1.1.1.1")
        _add(f"1.3.6.1.2.1.31.1.1.1.6.{idx}", f"ifHCInOctets.{idx}", "Counter64", row["hc_in_octets"], "IF-MIB", "1.3.6.1.2.1.31.1.1.1.6")
        _add(f"1.3.6.1.2.1.31.1.1.1.7.{idx}", f"ifHCInUcastPkts.{idx}", "Counter64", row["hc_in_ucast"], "IF-MIB", "1.3.6.1.2.1.31.1.1.1.7")
        _add(f"1.3.6.1.2.1.31.1.1.1.10.{idx}", f"ifHCOutOctets.{idx}", "Counter64", row["hc_out_octets"], "IF-MIB", "1.3.6.1.2.1.31.1.1.1.10")
        _add(f"1.3.6.1.2.1.31.1.1.1.11.{idx}", f"ifHCOutUcastPkts.{idx}", "Counter64", row["hc_out_ucast"], "IF-MIB", "1.3.6.1.2.1.31.1.1.1.11")
        _add(f"1.3.6.1.2.1.31.1.1.1.15.{idx}", f"ifHighSpeed.{idx}", "Gauge32", row["high_speed"], "IF-MIB", "1.3.6.1.2.1.31.1.1.1.15")
        _add(f"1.3.6.1.2.1.31.1.1.1.18.{idx}", f"ifAlias.{idx}", "OctetString", row["alias"], "IF-MIB", "1.3.6.1.2.1.31.1.1.1.18")

    # ---------------------------------------------------------------------
    # 3. IP-MIB Forwarding & Active Default Route (1.3.6.1.2.1.4.*)
    # ---------------------------------------------------------------------
    _add("1.3.6.1.2.1.4.1.0", "ipForwarding.0", "Integer32", 1, "IP-MIB", "1.3.6.1.2.1.4.1")
    _add("1.3.6.1.2.1.4.21.1.1.0.0.0.0", "ipRouteDest.0.0.0.0", "IpAddress", "0.0.0.0", "IP-MIB", "1.3.6.1.2.1.4.21.1.1")
    _add("1.3.6.1.2.1.4.21.1.2.0.0.0.0", "ipRouteIfIndex.0.0.0.0", "Integer32", active_route_if, "IP-MIB", "1.3.6.1.2.1.4.21.1.2")
    _add("1.3.6.1.2.1.4.21.1.3.0.0.0.0", "ipRouteMetric1.0.0.0.0", "Integer32", active_route_metric, "IP-MIB", "1.3.6.1.2.1.4.21.1.3")
    _add("1.3.6.1.2.1.4.21.1.7.0.0.0.0", "ipRouteNextHop.0.0.0.0", "IpAddress", active_route_nexthop, "IP-MIB", "1.3.6.1.2.1.4.21.1.7")
    _add("1.3.6.1.2.1.4.21.1.8.0.0.0.0", "ipRouteType.0.0.0.0", "Integer32", 4, "IP-MIB", "1.3.6.1.2.1.4.21.1.8")
    _add("1.3.6.1.2.1.4.21.1.9.0.0.0.0", "ipRouteProto.0.0.0.0", "Integer32", 14, "IP-MIB", "1.3.6.1.2.1.4.21.1.9")
    _add("1.3.6.1.2.1.4.21.1.10.0.0.0.0", "ipRouteAge.0.0.0.0", "Integer32", active_route_age, "IP-MIB", "1.3.6.1.2.1.4.21.1.10")

    # ---------------------------------------------------------------------
    # 4. BGP4-MIB (1.3.6.1.2.1.15.*)
    # ---------------------------------------------------------------------
    _add("1.3.6.1.2.1.15.1.0", "bgpVersion.0", "OctetString", b"\x10", "BGP4-MIB", "1.3.6.1.2.1.15.1")
    _add("1.3.6.1.2.1.15.2.0", "bgpLocalAs.0", "Integer32", 65001, "BGP4-MIB", "1.3.6.1.2.1.15.2")
    _add("1.3.6.1.2.1.15.4.0", "bgpIdentifier.0", "IpAddress", "10.254.0.1", "BGP4-MIB", "1.3.6.1.2.1.15.4")

    bgp_peers = [
        {
            "peer_ip": "198.51.100.1",
            "peer_id": "198.51.100.1",
            "state": peer1_state,
            "admin": 2,
            "version": 4,
            "local_addr": "198.51.100.0",
            "local_port": 52179,
            "remote_addr": "198.51.100.1",
            "remote_port": 179,
            "remote_as": 65002,
            "in_updates": peer1_in_updates,
            "out_updates": peer1_out_updates,
            "in_total": peer1_in_updates + 1400,
            "out_total": peer1_out_updates + 1400,
            "last_error": peer1_last_err,
            "transitions": peer1_transitions,
            "est_time": peer1_est_time,
            "hold_time": 180,
            "keepalive": 60,
        },
        {
            "peer_ip": "198.51.100.2",
            "peer_id": "198.51.100.2",
            "state": 6,  # established across all phases (backup carrier path)
            "admin": 2,
            "version": 4,
            "local_addr": "198.51.100.4",
            "local_port": 52180,
            "remote_addr": "198.51.100.2",
            "remote_port": 179,
            "remote_as": 65003,
            "in_updates": peer2_in_updates,
            "out_updates": peer2_out_updates,
            "in_total": peer2_in_updates + 1400,
            "out_total": peer2_out_updates + 1400,
            "last_error": b"\x00\x00",
            "transitions": 1,
            "est_time": 86270 + ((sys_uptime - 8639000) // 100),
            "hold_time": 180,
            "keepalive": 60,
        },
    ]

    for peer in bgp_peers:
        pip = peer["peer_ip"]
        _add(f"1.3.6.1.2.1.15.3.1.1.{pip}", f"bgpPeerIdentifier.{pip}", "IpAddress", peer["peer_id"], "BGP4-MIB", "1.3.6.1.2.1.15.3.1.1")
        _add(f"1.3.6.1.2.1.15.3.1.2.{pip}", f"bgpPeerState.{pip}", "Integer32", peer["state"], "BGP4-MIB", "1.3.6.1.2.1.15.3.1.2")
        _add(f"1.3.6.1.2.1.15.3.1.3.{pip}", f"bgpPeerAdminStatus.{pip}", "Integer32", peer["admin"], "BGP4-MIB", "1.3.6.1.2.1.15.3.1.3")
        _add(f"1.3.6.1.2.1.15.3.1.4.{pip}", f"bgpPeerNegotiatedVersion.{pip}", "Integer32", peer["version"], "BGP4-MIB", "1.3.6.1.2.1.15.3.1.4")
        _add(f"1.3.6.1.2.1.15.3.1.5.{pip}", f"bgpPeerLocalAddr.{pip}", "IpAddress", peer["local_addr"], "BGP4-MIB", "1.3.6.1.2.1.15.3.1.5")
        _add(f"1.3.6.1.2.1.15.3.1.6.{pip}", f"bgpPeerLocalPort.{pip}", "Integer32", peer["local_port"], "BGP4-MIB", "1.3.6.1.2.1.15.3.1.6")
        _add(f"1.3.6.1.2.1.15.3.1.7.{pip}", f"bgpPeerRemoteAddr.{pip}", "IpAddress", peer["remote_addr"], "BGP4-MIB", "1.3.6.1.2.1.15.3.1.7")
        _add(f"1.3.6.1.2.1.15.3.1.8.{pip}", f"bgpPeerRemotePort.{pip}", "Integer32", peer["remote_port"], "BGP4-MIB", "1.3.6.1.2.1.15.3.1.8")
        _add(f"1.3.6.1.2.1.15.3.1.9.{pip}", f"bgpPeerRemoteAs.{pip}", "Integer32", peer["remote_as"], "BGP4-MIB", "1.3.6.1.2.1.15.3.1.9")
        _add(f"1.3.6.1.2.1.15.3.1.10.{pip}", f"bgpPeerInUpdates.{pip}", "Counter32", peer["in_updates"], "BGP4-MIB", "1.3.6.1.2.1.15.3.1.10")
        _add(f"1.3.6.1.2.1.15.3.1.11.{pip}", f"bgpPeerOutUpdates.{pip}", "Counter32", peer["out_updates"], "BGP4-MIB", "1.3.6.1.2.1.15.3.1.11")
        _add(f"1.3.6.1.2.1.15.3.1.12.{pip}", f"bgpPeerInTotalMessages.{pip}", "Counter32", peer["in_total"], "BGP4-MIB", "1.3.6.1.2.1.15.3.1.12")
        _add(f"1.3.6.1.2.1.15.3.1.13.{pip}", f"bgpPeerOutTotalMessages.{pip}", "Counter32", peer["out_total"], "BGP4-MIB", "1.3.6.1.2.1.15.3.1.13")
        _add(f"1.3.6.1.2.1.15.3.1.14.{pip}", f"bgpPeerLastError.{pip}", "OctetString", peer["last_error"], "BGP4-MIB", "1.3.6.1.2.1.15.3.1.14")
        _add(f"1.3.6.1.2.1.15.3.1.15.{pip}", f"bgpPeerFsmEstablishedTransitions.{pip}", "Counter32", peer["transitions"], "BGP4-MIB", "1.3.6.1.2.1.15.3.1.15")
        _add(f"1.3.6.1.2.1.15.3.1.16.{pip}", f"bgpPeerFsmEstablishedTime.{pip}", "Gauge32", peer["est_time"], "BGP4-MIB", "1.3.6.1.2.1.15.3.1.16")
        _add(f"1.3.6.1.2.1.15.3.1.18.{pip}", f"bgpPeerHoldTime.{pip}", "Integer32", peer["hold_time"], "BGP4-MIB", "1.3.6.1.2.1.15.3.1.18")
        _add(f"1.3.6.1.2.1.15.3.1.19.{pip}", f"bgpPeerKeepAlive.{pip}", "Integer32", peer["keepalive"], "BGP4-MIB", "1.3.6.1.2.1.15.3.1.19")

    return store


def verify_trap_poll_coherence(
    pdu: SnmpMessage,
    store: SnmpOidStore,
) -> Dict[str, Any]:
    """
    Verifies that every non-header varbind in a `service_provider_cisco` Trap or Inform PDU
    (starting at varbind index 2) matches the exact value reported by the polling OID store
    for the corresponding phase.
    """
    mismatches: List[Dict[str, Any]] = []
    checked: List[Dict[str, Any]] = []

    for vb in pdu.varbinds[2:]:
        polled_vb = store.get_exact(vb.oid)
        match = (
            polled_vb.asn1_type == vb.asn1_type
            and polled_vb.value == vb.value
        )
        record = {
            "oid": vb.oid,
            "object_name": vb.object_name or polled_vb.object_name,
            "notification_value": vb.value.hex() if isinstance(vb.value, (bytes, bytearray)) else vb.value,
            "polled_value": polled_vb.value.hex() if isinstance(polled_vb.value, (bytes, bytearray)) else polled_vb.value,
            "coherent": match,
        }
        checked.append(record)
        if not match:
            mismatches.append(record)

    return {
        "pdu_type": "INFORM" if int(pdu.pdu_type) == SnmpPduType.INFORM_REQUEST.value else "TRAP",
        "request_id": pdu.request_id,
        "trap_oid": str(pdu.varbinds[1].value) if len(pdu.varbinds) >= 2 else "",
        "store_phase": store.phase,
        "checked_varbinds": checked,
        "mismatches": mismatches,
        "coherent": len(mismatches) == 0,
    }


# =========================================================================
# Simulated SNMPv2c Polling Agent (Sections 5, 9, 10, 11, 16, 17, 18)
# =========================================================================
class SimulatedSnmpAgent:
    """
    Bounded, read-only SNMPv2c simulated device agent supporting:
      - GetRequest-PDU (0xA0)
      - GetNextRequest-PDU (0xA1)
      - GetBulkRequest-PDU (0xA5)
      - Response-PDU (0xA2)
      - Read-only rejection of SetRequest-PDU (0xA3) with error-status=notWritable (17)

    Defaults to loopback 127.0.0.1:1161 without requiring root privileges.
    Never binds to 0.0.0.0 or public interfaces by default.
    """

    def __init__(
        self,
        bind_host: str = DEFAULT_AGENT_BIND_HOST,
        bind_port: int = DEFAULT_AGENT_BIND_PORT,
        community: str = DEFAULT_AGENT_COMMUNITY,
        oid_store: Optional[SnmpOidStore] = None,
        scenario_id: str = "service_provider_cisco",
        phase: str = "BASELINE",
        seed: int = 42,
        device_id: str = "cisco-asr9k-pe1",
        max_repetitions_default: int = DEFAULT_GETBULK_MAX_REPETITIONS,
        max_repetitions_hard_cap: int = HARD_MAX_GETBULK_REPETITIONS,
        max_varbinds_per_response: int = MAX_VARBINDS_PER_RESPONSE,
        max_udp_payload_bytes: int = MAX_SNMP_UDP_PAYLOAD_BYTES,
        rate_limit_pps: int = DEFAULT_AGENT_RATE_LIMIT_PPS,
        max_packets: int = DEFAULT_AGENT_MAX_PACKETS,
        allow_non_loopback_rfc1918: bool = False,
        test_mode: bool = True,
    ):
        self._validate_bind_address(bind_host, bind_port, allow_non_loopback_rfc1918)
        self.bind_host = bind_host
        self.requested_port = int(bind_port)
        self.bound_port: int = int(bind_port)
        self.community = community
        self.scenario_id = scenario_id
        self.phase = normalize_scenario_phase(phase)
        self.seed = int(seed)
        self.device_id = device_id

        self.max_repetitions_default = min(
            max(1, int(max_repetitions_default)), HARD_MAX_GETBULK_REPETITIONS
        )
        self.max_repetitions_hard_cap = min(
            max(1, int(max_repetitions_hard_cap)), HARD_MAX_GETBULK_REPETITIONS
        )
        self.max_varbinds_per_response = min(
            max(1, int(max_varbinds_per_response)), MAX_VARBINDS_PER_RESPONSE
        )
        self.max_udp_payload_bytes = min(
            max(128, int(max_udp_payload_bytes)), MAX_SNMP_UDP_PAYLOAD_BYTES
        )

        self.rate_limit_pps = min(max(1, int(rate_limit_pps)), MAX_AGENT_RATE_LIMIT_PPS)
        self.max_packets = max(1, int(max_packets))
        self.test_mode = test_mode

        self.request_limiter = TokenBucketRateLimiter(
            rate_pps=self.rate_limit_pps, max_packets_per_run=self.max_packets
        )
        self.response_limiter = TokenBucketRateLimiter(
            rate_pps=self.rate_limit_pps, max_packets_per_run=self.max_packets
        )

        self.oid_store: SnmpOidStore = (
            oid_store
            if oid_store is not None
            else build_service_provider_cisco_oid_store(
                phase=self.phase, seed=self.seed, device_id=self.device_id
            )
        )

        self._sock: Optional[socket.socket] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._lock = threading.Lock()

        # Telemetry & Evidence Counters
        self.requests_received: int = 0
        self.requests_decoded: int = 0
        self.get_requests: int = 0
        self.getnext_requests: int = 0
        self.getbulk_requests: int = 0
        self.set_requests_rejected: int = 0
        self.unsupported_pdu_rejected: int = 0
        self.malformed_requests: int = 0
        self.bad_community_requests: int = 0
        self.bad_version_requests: int = 0
        self.rate_limited_requests: int = 0
        self.responses_generated: int = 0
        self.responses_encoded: int = 0
        self.responses_sent: int = 0
        self.manager_observed_responses: int = 0
        self.evidence_stage: str = "IDLE"
        self.stage_history: List[str] = []
        self.captured_frames: List[Dict[str, Any]] = []

    @staticmethod
    def _validate_bind_address(
        host: str, port: int, allow_non_loopback_rfc1918: bool = False
    ) -> None:
        if not (0 <= int(port) <= 65535):
            raise DestinationSecurityException(f"Invalid SNMP agent port: {port}")
        if 0 < int(port) < 1024:
            raise DestinationSecurityException(
                f"Privileged SNMP agent port {port} (< 1024) is forbidden; use 1161 or high port"
            )
        if host in ("0.0.0.0", "::", "*"):
            raise DestinationSecurityException(
                f"Wildcard bind address {host!r} is strictly prohibited for SimulatedSnmpAgent"
            )
        try:
            ip_obj = ipaddress.ip_address(host)
        except ValueError as e:
            raise DestinationSecurityException(
                f"Invalid SNMP agent bind IP address {host!r}: {e}"
            ) from e

        if ip_obj.is_loopback:
            return
        if allow_non_loopback_rfc1918 and is_safe_ip(ip_obj) and not ip_obj.is_multicast:
            return
        raise DestinationSecurityException(
            f"SimulatedSnmpAgent must bind to loopback (127.0.0.1) by default; got {host!r}"
        )

    def _record_stage(self, stage: str) -> None:
        self.evidence_stage = stage
        if stage not in self.stage_history:
            self.stage_history.append(stage)

    def set_phase(self, phase: str) -> None:
        """
        Transitions the simulated agent's deterministic OID store to the requested
        scenario phase (BASELINE, DEGRADE, FAILOVER, or RECOVERY).
        """
        norm_phase = normalize_scenario_phase(phase)
        new_store = build_service_provider_cisco_oid_store(
            phase=norm_phase, seed=self.seed, device_id=self.device_id
        )
        with self._lock:
            self.phase = norm_phase
            self.oid_store = new_store

    def start(self) -> int:
        if self._running:
            return self.bound_port
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((self.bind_host, self.requested_port))
        sock.settimeout(0.05)
        self.bound_port = sock.getsockname()[1]
        self._sock = sock
        self._running = True
        self._thread = threading.Thread(target=self._serve_loop, daemon=True)
        self._thread.start()
        return self.bound_port

    def stop(self) -> None:
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        if self._sock:
            try:
                self._sock.close()
            except Exception:
                pass
            self._sock = None

    def __enter__(self) -> "SimulatedSnmpAgent":
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.stop()

    def process_request_message(self, req: SnmpMessage) -> Optional[SnmpResponse]:
        """
        Processes a decoded SNMPv2c request PDU against the canonical OID store and returns
        the corresponding SnmpResponse (0xA2) or None if the PDU type is ignored.
        """
        pdu_tag = int(req.pdu_type)

        # 1. Read-Only SET Rejection (Section 16)
        if pdu_tag == SnmpPduType.SET_REQUEST.value:
            self.set_requests_rejected += 1
            err_idx = 1 if req.varbinds else 0
            return SnmpResponse(
                version=SnmpVersion.V2C.value,
                community=req.community,
                request_id=req.request_id,
                error_status=SNMP_ERR_NOT_WRITABLE,
                error_index=err_idx,
                varbinds=list(req.varbinds),
            )

        # 2. Reject non-polling PDUs sent to the agent port
        if pdu_tag not in (
            SnmpPduType.GET_REQUEST.value,
            SnmpPduType.GET_NEXT_REQUEST.value,
            SnmpPduType.GET_BULK_REQUEST.value,
        ):
            self.unsupported_pdu_rejected += 1
            return None

        # Reject excessive input varbinds
        if len(req.varbinds) > self.max_varbinds_per_response:
            return SnmpResponse(
                version=SnmpVersion.V2C.value,
                community=req.community,
                request_id=req.request_id,
                error_status=SNMP_ERR_TOO_BIG,
                error_index=0,
                varbinds=[],
            )

        store = self.oid_store

        # 3. GET Request (0xA0)
        if pdu_tag == SnmpPduType.GET_REQUEST.value:
            self.get_requests += 1
            resp_vbs = [store.get_exact(vb.oid) for vb in req.varbinds]
            return self._fit_response_within_mtu(req, resp_vbs)

        # 4. GETNEXT Request (0xA1)
        if pdu_tag == SnmpPduType.GET_NEXT_REQUEST.value:
            self.getnext_requests += 1
            resp_vbs = [store.get_next(vb.oid) for vb in req.varbinds]
            return self._fit_response_within_mtu(req, resp_vbs)

        # 5. GETBULK Request (0xA5)
        self.getbulk_requests += 1
        raw_non_rep = (
            req.non_repeaters if req.non_repeaters is not None else req.error_status
        )
        raw_max_rep = (
            req.max_repetitions if req.max_repetitions is not None else req.error_index
        )
        non_repeaters = max(0, int(raw_non_rep))
        max_repetitions = min(max(0, int(raw_max_rep)), self.max_repetitions_hard_cap)

        total_req_vbs = len(req.varbinds)
        n_Count = min(non_repeaters, total_req_vbs)
        r_Count = total_req_vbs - n_Count

        resp_vbs: List[SnmpVarBind] = []

        # Process N non-repeaters (1 lexicographic successor each)
        for i in range(n_Count):
            if len(resp_vbs) >= self.max_varbinds_per_response:
                break
            next_vb = store.get_next(req.varbinds[i].oid)
            candidate = resp_vbs + [next_vb]
            if not self._can_encode_within_mtu(req, candidate):
                break
            resp_vbs.append(next_vb)

        # Process M repetitions across R repeaters
        if r_Count > 0 and max_repetitions > 0:
            current_oids = [req.varbinds[n_Count + r].oid for r in range(r_Count)]
            for _ in range(max_repetitions):
                all_end_of_mib = True
                stop_bulk = False
                for r in range(r_Count):
                    if len(resp_vbs) >= self.max_varbinds_per_response:
                        stop_bulk = True
                        break
                    next_vb = store.get_next(current_oids[r])
                    if next_vb.asn1_type != "endOfMibView":
                        all_end_of_mib = False
                    candidate = resp_vbs + [next_vb]
                    if not self._can_encode_within_mtu(req, candidate):
                        stop_bulk = True
                        break
                    resp_vbs.append(next_vb)
                    current_oids[r] = next_vb.oid
                if stop_bulk or all_end_of_mib:
                    break

        return SnmpResponse(
            version=SnmpVersion.V2C.value,
            community=req.community,
            request_id=req.request_id,
            error_status=SNMP_ERR_NO_ERROR,
            error_index=0,
            varbinds=resp_vbs,
        )

    def _can_encode_within_mtu(
        self, req: SnmpMessage, varbinds: List[SnmpVarBind]
    ) -> bool:
        candidate_resp = SnmpResponse(
            version=SnmpVersion.V2C.value,
            community=req.community,
            request_id=req.request_id,
            error_status=SNMP_ERR_NO_ERROR,
            error_index=0,
            varbinds=varbinds,
        )
        try:
            SnmpBerEncoder.encode_message(
                candidate_resp, max_payload_bytes=self.max_udp_payload_bytes
            )
            return True
        except SnmpPayloadSizeError:
            return False

    def _fit_response_within_mtu(
        self, req: SnmpMessage, varbinds: List[SnmpVarBind]
    ) -> SnmpResponse:
        resp = SnmpResponse(
            version=SnmpVersion.V2C.value,
            community=req.community,
            request_id=req.request_id,
            error_status=SNMP_ERR_NO_ERROR,
            error_index=0,
            varbinds=varbinds,
        )
        if self._can_encode_within_mtu(req, varbinds):
            return resp
        # RFC 3416 Section 4.2.1/4.2.2: if GET/GETNEXT response exceeds max message size, return tooBig (1)
        return SnmpResponse(
            version=SnmpVersion.V2C.value,
            community=req.community,
            request_id=req.request_id,
            error_status=SNMP_ERR_TOO_BIG,
            error_index=0,
            varbinds=[],
        )

    def handle_raw_datagram(
        self,
        data: bytes,
        src_addr: Tuple[str, int] = ("127.0.0.1", 54161),
    ) -> Optional[bytes]:
        """
        Processes a raw incoming UDP datagram through rate limiting, size validation,
        ASN.1 BER decoding, OID store lookup, and Response-PDU BER encoding.
        Returns the wire bytes to send back, or None if the request must be dropped.
        """
        with self._lock:
            self.requests_received += 1
            self._record_stage(SnmpEvidenceStage.REQUEST_RECEIVED.value)
            self.captured_frames.append(
                {
                    "direction": "IN",
                    "src_ip": src_addr[0],
                    "dst_ip": self.bind_host,
                    "src_port": src_addr[1],
                    "dst_port": self.bound_port,
                    "payload": bytes(data),
                    "timestamp": time.time(),
                }
            )

            # 1. Request Rate Limit check
            try:
                self.request_limiter.acquire(1, test_mode=self.test_mode)
            except Exception:
                self.rate_limited_requests += 1
                return None

            # 2. Maximum UDP payload size check
            if not data or len(data) > self.max_udp_payload_bytes:
                self.malformed_requests += 1
                return None

            # 3. ASN.1 BER Decode
            try:
                req_msg = SnmpBerDecoder.decode_message(
                    data, expected_community=self.community
                )
            except UnsupportedSnmpVersionError:
                self.bad_version_requests += 1
                return None
            except SnmpCommunityMismatchError:
                self.bad_community_requests += 1
                return None
            except SnmpBerDecodeError:
                self.malformed_requests += 1
                return None
            except Exception:
                self.malformed_requests += 1
                return None

            self.requests_decoded += 1
            self._record_stage(SnmpEvidenceStage.REQUEST_DECODED.value)

            # 4. Generate Response-PDU
            resp_msg = self.process_request_message(req_msg)
            if resp_msg is None:
                return None

            self.responses_generated += 1
            self._record_stage(SnmpEvidenceStage.RESPONSE_GENERATED.value)

            # 5. Encode Response-PDU
            try:
                resp_bytes = SnmpBerEncoder.encode_message(
                    resp_msg, max_payload_bytes=self.max_udp_payload_bytes
                )
            except SnmpPayloadSizeError:
                fallback = SnmpResponse(
                    version=SnmpVersion.V2C.value,
                    community=req_msg.community,
                    request_id=req_msg.request_id,
                    error_status=SNMP_ERR_TOO_BIG,
                    error_index=0,
                    varbinds=[],
                )
                resp_bytes = SnmpBerEncoder.encode_message(fallback)

            self.responses_encoded += 1
            self._record_stage(SnmpEvidenceStage.RESPONSE_ENCODED.value)
            return resp_bytes

    def _serve_loop(self) -> None:
        while self._running and self._sock:
            try:
                data, addr = self._sock.recvfrom(65535)
            except socket.timeout:
                continue
            except OSError:
                break

            resp_bytes = self.handle_raw_datagram(data, src_addr=addr)
            if resp_bytes is not None and self._running and self._sock:
                try:
                    self.response_limiter.acquire(1, test_mode=self.test_mode)
                    self._sock.sendto(resp_bytes, addr)
                    with self._lock:
                        self.responses_sent += 1
                        self._record_stage(SnmpEvidenceStage.RESPONSE_SENT.value)
                        self.captured_frames.append(
                            {
                                "direction": "OUT",
                                "src_ip": self.bind_host,
                                "dst_ip": addr[0],
                                "src_port": self.bound_port,
                                "dst_port": addr[1],
                                "payload": resp_bytes,
                                "timestamp": time.time(),
                            }
                        )
                except Exception:
                    pass

    def record_manager_observation(self, count: int = 1) -> None:
        """
        Records independent confirmation that an SNMP manager/client received and decoded
        the agent's Response-PDU(s). Never claims SPLUNK_OBSERVED in Gate 12C.
        """
        with self._lock:
            self.manager_observed_responses += max(0, int(count))
            if self.manager_observed_responses > 0:
                self._record_stage(SnmpEvidenceStage.MANAGER_OBSERVED.value)

    def clear_captured_frames(self) -> None:
        with self._lock:
            self.captured_frames.clear()

    def export_pcap(
        self, filepath: str, normalize_agent_port: Optional[int] = None
    ) -> str:
        with self._lock:
            frames = [dict(fr) for fr in self.captured_frames]
        if normalize_agent_port is not None:
            for fr in frames:
                if fr.get("direction") == "IN":
                    fr["dst_port"] = int(normalize_agent_port)
                else:
                    fr["src_port"] = int(normalize_agent_port)
        return write_snmp_pcap(filepath, frames)

    def get_evidence(self) -> SnmpPollingEvidence:
        with self._lock:
            return SnmpPollingEvidence(
                bind_host=self.bind_host,
                bind_port=self.bound_port,
                scenario_id=self.scenario_id,
                phase=self.phase,
                seed=self.seed,
                simulated_device_ids=[self.device_id],
                exposed_oid_count=len(self.oid_store),
                mib_families=self.oid_store.mib_families(),
                requests_received=self.requests_received,
                requests_decoded=self.requests_decoded,
                get_requests=self.get_requests,
                getnext_requests=self.getnext_requests,
                getbulk_requests=self.getbulk_requests,
                set_requests_rejected=self.set_requests_rejected,
                unsupported_pdu_rejected=self.unsupported_pdu_rejected,
                malformed_requests=self.malformed_requests,
                bad_community_requests=self.bad_community_requests,
                bad_version_requests=self.bad_version_requests,
                rate_limited_requests=self.rate_limited_requests,
                responses_generated=self.responses_generated,
                responses_encoded=self.responses_encoded,
                responses_sent=self.responses_sent,
                manager_observed_responses=self.manager_observed_responses,
                evidence_stage=self.evidence_stage,
                stage_history=list(self.stage_history),
            )


# =========================================================================
# UDP SNMPv2c Manager Client Helper for Loopback & Performance Testing
# =========================================================================
class SnmpPollingClient:
    """
    Lightweight SNMPv2c UDP polling client for sending GET, GETNEXT, GETBULK, and SET
    requests to SimulatedSnmpAgent over loopback sockets.
    """

    def __init__(
        self,
        host: str = DEFAULT_AGENT_BIND_HOST,
        port: int = DEFAULT_AGENT_BIND_PORT,
        community: str = DEFAULT_AGENT_COMMUNITY,
        timeout_sec: float = 1.0,
    ):
        self.host = host
        self.port = int(port)
        self.community = community
        self.timeout_sec = timeout_sec
        self._req_counter = 10000

    def _next_request_id(self) -> int:
        self._req_counter = ((self._req_counter + 1) & 0x7FFFFFFF) or 1
        return self._req_counter

    def send_message(
        self,
        msg: SnmpMessage,
        agent: Optional[SimulatedSnmpAgent] = None,
    ) -> SnmpResponse:
        wire = SnmpBerEncoder.encode_message(msg)
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(self.timeout_sec)
            sock.sendto(wire, (self.host, self.port))
            resp_bytes, _ = sock.recvfrom(65535)
        decoded = SnmpBerDecoder.decode_message(
            resp_bytes, expected_community=msg.community
        )
        if not isinstance(decoded, SnmpResponse):
            raise SnmpBerDecodeError(
                f"Expected Response-PDU (0xA2), got PDU tag 0x{int(decoded.pdu_type):02x}"
            )
        if decoded.request_id != msg.request_id:
            raise SnmpBerDecodeError(
                f"Response request-id {decoded.request_id} != request {msg.request_id}"
            )
        if agent is not None:
            agent.record_manager_observation(1)
        return decoded

    def get(
        self,
        oids: Union[str, List[str]],
        request_id: Optional[int] = None,
        agent: Optional[SimulatedSnmpAgent] = None,
    ) -> SnmpResponse:
        oid_list = [oids] if isinstance(oids, str) else list(oids)
        msg = SnmpMessage(
            version=SnmpVersion.V2C.value,
            community=self.community,
            pdu_type=SnmpPduType.GET_REQUEST.value,
            request_id=request_id if request_id is not None else self._next_request_id(),
            varbinds=[
                SnmpVarBind(oid=normalize_oid_str(o), asn1_type="Null", value=None)
                for o in oid_list
            ],
        )
        return self.send_message(msg, agent=agent)

    def get_next(
        self,
        oids: Union[str, List[str]],
        request_id: Optional[int] = None,
        agent: Optional[SimulatedSnmpAgent] = None,
    ) -> SnmpResponse:
        oid_list = [oids] if isinstance(oids, str) else list(oids)
        msg = SnmpMessage(
            version=SnmpVersion.V2C.value,
            community=self.community,
            pdu_type=SnmpPduType.GET_NEXT_REQUEST.value,
            request_id=request_id if request_id is not None else self._next_request_id(),
            varbinds=[
                SnmpVarBind(oid=normalize_oid_str(o), asn1_type="Null", value=None)
                for o in oid_list
            ],
        )
        return self.send_message(msg, agent=agent)

    def get_bulk(
        self,
        oids: Union[str, List[str]],
        non_repeaters: int = 0,
        max_repetitions: int = 10,
        request_id: Optional[int] = None,
        agent: Optional[SimulatedSnmpAgent] = None,
    ) -> SnmpResponse:
        oid_list = [oids] if isinstance(oids, str) else list(oids)
        msg = SnmpMessage(
            version=SnmpVersion.V2C.value,
            community=self.community,
            pdu_type=SnmpPduType.GET_BULK_REQUEST.value,
            request_id=request_id if request_id is not None else self._next_request_id(),
            error_status=non_repeaters,
            error_index=max_repetitions,
            non_repeaters=non_repeaters,
            max_repetitions=max_repetitions,
            varbinds=[
                SnmpVarBind(oid=normalize_oid_str(o), asn1_type="Null", value=None)
                for o in oid_list
            ],
        )
        return self.send_message(msg, agent=agent)

    def walk(
        self,
        subtree_oid: str = "1.3.6.1.2.1",
        use_bulk: bool = False,
        max_repetitions: int = 15,
        agent: Optional[SimulatedSnmpAgent] = None,
    ) -> List[SnmpVarBind]:
        norm_prefix = normalize_oid_str(subtree_oid)
        current_oid = norm_prefix
        results: List[SnmpVarBind] = []
        seen: Set[str] = set()

        while True:
            if use_bulk:
                resp = self.get_bulk(
                    current_oid,
                    non_repeaters=0,
                    max_repetitions=max_repetitions,
                    agent=agent,
                )
                if not resp.varbinds:
                    break
                stopped = False
                for vb in resp.varbinds:
                    if vb.asn1_type == "endOfMibView" or not is_oid_in_subtree(
                        vb.oid, norm_prefix
                    ):
                        stopped = True
                        break
                    if vb.oid in seen:
                        stopped = True
                        break
                    seen.add(vb.oid)
                    results.append(vb)
                    current_oid = vb.oid
                if stopped:
                    break
            else:
                resp = self.get_next(current_oid, agent=agent)
                if not resp.varbinds:
                    break
                vb = resp.varbinds[0]
                if vb.asn1_type == "endOfMibView" or not is_oid_in_subtree(
                    vb.oid, norm_prefix
                ):
                    break
                if vb.oid in seen:
                    break
                seen.add(vb.oid)
                results.append(vb)
                current_oid = vb.oid

        return results
