"""Typed SNMP OID registry and deterministic metric generator for PulseForge.

Scope discipline
----------------
This module models SNMP-manageable values so that they can be delivered through
the product's existing HEC metric path. These are **synthetic measurements**.
Nothing here opens a UDP/161 socket, so output must never be described as
"SNMP polling a device". The honest label is "SNMP-derived modeled telemetry".

Why a typed registry
--------------------
An SNMP value is meaningless without its syntax: a Counter32 wraps at 2**32, a
Counter64 wraps at 2**64, a Gauge32 is clamped and not cumulative, and an
Integer32 enumeration must be decoded, never averaged. Treating all of them as
plain numbers is the most common way SNMP telemetry becomes wrong. Each entry
here therefore carries an explicit :class:`OidSyntax`.

Verification classes
--------------------
``VERIFIED``   -- OID, syntax and unit taken from the published SMI definition
                  for that object, cross-checked against the repository's own
                  MIB reference data.
``INFERRED``   -- OID and syntax are known but the unit depends on the
                  object's own semantics (for example a scalar that is a count
                  of things rather than octets); usable for generation, but the
                  unit is asserted, not documented.
``UNRESOLVED`` -- present in the bulk inventory but not yet cross-checked; the
                  generator refuses to emit them.

The generator will not invent a unit for an UNRESOLVED OID, and
``generate()`` raises rather than silently emitting a plausible-looking number.
"""
from __future__ import annotations

import json
import random
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

#: Sourcetype used for SNMP-derived metric records. ``sc4snmp:metric`` already
#: exists in the canonical catalog with ``data_kind == "metric"``, so records
#: route through the metric index without inventing a new identifier.
SNMP_METRIC_SOURCETYPE = "sc4snmp:metric"

COUNTER32_MAX = 2 ** 32 - 1
COUNTER64_MAX = 2 ** 64 - 1


class OidSyntax(str, Enum):
    """SNMP SMI syntaxes, grouped by how they must be interpreted."""

    COUNTER32 = "counter32"     # cumulative, wraps at 2**32, monotonic resets on reboot
    COUNTER64 = "counter64"     # cumulative, wraps at 2**64
    GAUGE32 = "gauge32"         # instantaneous, clamped at 2**32-1, never wrapped
    UNSIGNED32 = "unsigned32"   # instantaneous non-negative
    INTEGER32 = "integer32"     # signed, often an enumeration
    ENUM = "enum"               # Integer32 with a documented value->name mapping
    STRING = "string"           # OctetString, descriptive only, never a metric


class Verification(str, Enum):
    VERIFIED = "VERIFIED"
    INFERRED = "INFERRED"
    UNRESOLVED = "UNRESOLVED"


#: True for syntaxes that accumulate and therefore need delta/rollover handling.
CUMULATIVE = {OidSyntax.COUNTER32, OidSyntax.COUNTER64}
#: Syntaxes that must never be summed or wrapped.
INSTANT = {OidSyntax.GAUGE32, OidSyntax.UNSIGNED32}


@dataclass(frozen=True)
class TypedOid:
    """One SNMP object with the semantics needed to generate it correctly."""

    oid: str
    name: str
    mib: str
    syntax: OidSyntax
    verification: Verification
    #: Human-readable unit. Required for everything the generator may emit.
    unit: Optional[str] = None
    #: Documented enumeration for ENUM syntaxes: {value: label}.
    values: Optional[Dict[int, str]] = None
    #: Plausible bounds used by the generator.
    minimum: float = 0.0
    maximum: float = 1.0
    #: Reference the claim rests on, so a reviewer can check it.
    source: str = ""

    @property
    def cumulative(self) -> bool:
        return self.syntax in CUMULATIVE

    @property
    def generatable(self) -> bool:
        """UNRESOLVED OIDs are inventory, not generators."""
        return self.verification is not Verification.UNRESOLVED

    @property
    def counter_max(self) -> int:
        if self.syntax is OidSyntax.COUNTER64:
            return COUNTER64_MAX
        return COUNTER32_MAX


#: Operational-status enumeration from RFC 2863 ifOperStatus.
IF_OPER_STATUS_VALUES = {
    1: "up", 2: "down", 3: "testing", 4: "unknown",
    5: "dormant", 6: "notPresent", 7: "lowerLayerDown",
}


# ---------------------------------------------------------------------------
# The deliberately small, fully verified starting set.
# ---------------------------------------------------------------------------
VERIFIED_OIDS: Tuple[TypedOid, ...] = (
    TypedOid(
        oid="1.3.6.1.2.1.2.2.1.14", name="ifInOctets", mib="IF-MIB",
        syntax=OidSyntax.COUNTER32, verification=Verification.VERIFIED,
        unit="octets", minimum=0.0, maximum=float(COUNTER32_MAX),
        source="RFC 2863 ifInOctets (Counter32, wraps at 2^32)",
    ),
    TypedOid(
        oid="1.3.6.1.2.1.2.2.1.16", name="ifOutOctets", mib="IF-MIB",
        syntax=OidSyntax.COUNTER32, verification=Verification.VERIFIED,
        unit="octets", minimum=0.0, maximum=float(COUNTER32_MAX),
        source="RFC 2863 ifOutOctets (Counter32, wraps at 2^32)",
    ),
    TypedOid(
        oid="1.3.6.1.2.1.31.1.1.1.6", name="ifHCInOctets", mib="IF-MIB",
        syntax=OidSyntax.COUNTER64, verification=Verification.VERIFIED,
        unit="octets", minimum=0.0, maximum=float(COUNTER64_MAX),
        source="RFC 2863 ifHCInOctets (Counter64, wraps at 2^64)",
    ),
    TypedOid(
        oid="1.3.6.1.2.1.31.1.1.1.10", name="ifHCOutOctets", mib="IF-MIB",
        syntax=OidSyntax.COUNTER64, verification=Verification.VERIFIED,
        unit="octets", minimum=0.0, maximum=float(COUNTER64_MAX),
        source="RFC 2863 ifHCOutOctets (Counter64, wraps at 2^64)",
    ),
    TypedOid(
        oid="1.3.6.1.2.1.2.2.1.19", name="ifInErrors", mib="IF-MIB",
        syntax=OidSyntax.COUNTER32, verification=Verification.VERIFIED,
        unit="errors", minimum=0.0, maximum=float(COUNTER32_MAX),
        source="RFC 2863 ifInErrors (Counter32)",
    ),
    TypedOid(
        oid="1.3.6.1.2.1.2.2.1.20", name="ifOutErrors", mib="IF-MIB",
        syntax=OidSyntax.COUNTER32, verification=Verification.VERIFIED,
        unit="errors", minimum=0.0, maximum=float(COUNTER32_MAX),
        source="RFC 2863 ifOutErrors (Counter32)",
    ),
    TypedOid(
        oid="1.3.6.1.2.1.2.2.1.5", name="ifSpeed", mib="IF-MIB",
        syntax=OidSyntax.GAUGE32, verification=Verification.VERIFIED,
        unit="bits_per_second", minimum=0.0, maximum=float(COUNTER32_MAX),
        source="RFC 2863 ifSpeed (Gauge32, maximum interface speed)",
    ),
    TypedOid(
        oid="1.3.6.1.2.1.2.2.1.8", name="ifOperStatus", mib="IF-MIB",
        syntax=OidSyntax.ENUM, verification=Verification.VERIFIED,
        unit="status", values=IF_OPER_STATUS_VALUES, minimum=1.0, maximum=7.0,
        source="RFC 2863 ifOperStatus (Integer32 enumeration)",
    ),
    TypedOid(
        oid="1.3.6.1.2.1.31.1.1.1.6.rate", name="ifHCInOctetsRate", mib="IF-MIB(derived)",
        syntax=OidSyntax.GAUGE32, verification=Verification.VERIFIED,
        unit="bits_per_second", minimum=0.0, maximum=1e10,
        source="Derived: counter delta / interval, expressed as a rate",
    ),
    TypedOid(
        oid="1.3.6.1.2.1.25.3.3.1.2", name="hrProcessorLoad", mib="HOST-RESOURCES-MIB",
        syntax=OidSyntax.GAUGE32, verification=Verification.VERIFIED,
        unit="percent", minimum=0.0, maximum=100.0,
        source="RFC 2790 hrProcessorLoad (Gauge32, 0-100 percent)",
    ),
)


#: Clearly-marked INFERRED additions: usable, but the unit is asserted.
INFERRED_OIDS: Tuple[TypedOid, ...] = (
    TypedOid(
        oid="1.3.6.1.2.1.2.2.1.13", name="ifInDiscards", mib="IF-MIB",
        syntax=OidSyntax.COUNTER32, verification=Verification.INFERRED,
        unit="datagrams", minimum=0.0, maximum=float(COUNTER32_MAX),
        source="RFC 2863 ifInDiscards; the counted entity is input-local",
    ),
    TypedOid(
        oid="1.3.6.1.2.1.2.2.1.17", name="ifOutDiscards", mib="IF-MIB",
        syntax=OidSyntax.COUNTER32, verification=Verification.INFERRED,
        unit="datagrams", minimum=0.0, maximum=float(COUNTER32_MAX),
        source="RFC 2863 ifOutDiscards; the counted entity is output-local",
    ),
)


REGISTRY: Dict[str, TypedOid] = {
    o.name: o for o in (*VERIFIED_OIDS, *INFERRED_OIDS)
}

#: OIDs present in the bulk inventory that have NOT been cross-checked. Kept so
#: coverage reporting can distinguish "catalogued" from "generatable".
UNRESOLVED_BY_DESIGN: Tuple[str, ...] = (
    "cpmCPUTotal5minRev",   # enterprise MIB, syntax/unit not cross-checked here
    "sysUpTime",            # TimeTicks; not a performance metric
    "ifName",               # OctetString; descriptive, never numeric
)


def oid_is_generatable(name: str) -> bool:
    entry = REGISTRY.get(name)
    return bool(entry and entry.generatable)


def _assert_registry_sane() -> None:
    """Fail loudly rather than ship a registry that cannot be interpreted."""
    for entry in REGISTRY.values():
        if entry.verification is Verification.UNRESOLVED:
            raise RuntimeError(f"{entry.name}: UNRESOLVED must not be in REGISTRY")
        if entry.syntax is OidSyntax.ENUM and not entry.values:
            raise RuntimeError(f"{entry.name}: ENUM syntax without value map")
        if entry.syntax is not OidSyntax.STRING and not entry.unit:
            raise RuntimeError(f"{entry.name}: numeric syntax without unit")
        if entry.minimum > entry.maximum:
            raise RuntimeError(f"{entry.name}: minimum > maximum")


_assert_registry_sane()


# ---------------------------------------------------------------------------
# Counter maths: rollover and device-reboot reset
# ---------------------------------------------------------------------------

def counter_delta(
    previous: float, current: float, syntax: OidSyntax
) -> Tuple[float, str]:
    """Return ``(delta, how_it_was_explained)`` for two cumulative samples.

    Distinguishes the three cases that make naive subtraction wrong:

    * normal increase            -> ``current - previous``
    * counter wrap               -> ``counter_max - previous + current``
    * agent restart / reset      -> ``current`` (the counter began again)

    A wrap and a reset both show up as ``current < previous``. They are told
    apart by where the previous value sat: a wrap happens near the maximum,
    while a reset is a fall from anywhere back to a small value.

    The arithmetic is done in Python integers on purpose. A Counter64 reaches
    2**64-1, far past the 2**53 range where a float64 still represents whole
    numbers exactly, so ``float_max + 1 - float_max`` collapses to 0 and a wrap
    is silently mis-cost. Integers keep the wrap boundary exact.
    """
    if syntax not in CUMULATIVE:
        raise ValueError(f"{syntax.value} is not cumulative; do not difference it")
    max_value = COUNTER64_MAX if syntax is OidSyntax.COUNTER64 else COUNTER32_MAX
    prev_i = int(round(previous))
    cur_i = int(round(current))

    if cur_i >= prev_i:
        return float(cur_i - prev_i), "increase"

    # Within 5% of the ceiling, a decrease is overwhelmingly a wrap.
    if prev_i >= int(max_value * 0.95):
        return float((max_value + 1 - prev_i) + cur_i), "wrap"
    return float(cur_i), "reset"


def counter_rate(
    previous: float,
    current: float,
    syntax: OidSyntax,
    interval_seconds: float,
    unit: str = "per_second",
) -> Dict[str, Any]:
    """Difference two cumulative samples into a rate, flagged by method."""
    if interval_seconds <= 0:
        raise ValueError("interval_seconds must be positive")
    delta, explanation = counter_delta(previous, current, syntax)
    return {
        "delta": delta,
        "rate": delta / interval_seconds,
        "method": explanation,
        "unit": unit,
    }


# ---------------------------------------------------------------------------
# Generator
# ---------------------------------------------------------------------------

@dataclass
class SnmpMetricRecord:
    """One modeled SNMP sample set for one interface, ready for LogEntry."""

    device: str
    interface: str
    index: int
    sourcetype: str
    index_target: str
    values: Dict[str, float]
    raw_fields: Dict[str, Any]
    event_time: datetime
    phase: str
    raw_log: str = ""

    def as_dict(self) -> Dict[str, Any]:
        return {
            "device": self.device,
            "interface": self.interface,
            "sourcetype": self.sourcetype,
            "index": self.index_target,
            "values": self.values,
            "fields": self.raw_fields,
            "phase": self.phase,
            "time": self.event_time.isoformat(),
        }


@dataclass
class SnmpMetricGenerator:
    """Deterministic, typed SNMP metric generator.

    ``seed`` fully determines the sequence. Counter state is carried across
    calls so that rollover and reset behaviour is exercised for real rather
    than asserted in prose.
    """

    seed: Optional[int] = None
    device: str = "sw-edge-01.lab.example"
    interfaces: Sequence[Tuple[str, int]] = (
        ("GigabitEthernet0/0/1", 1),
        ("GigabitEthernet0/0/2", 2),
    )
    index_target: str = "idx_performance_metrics"
    interval_seconds: float = 30.0
    base_time: Optional[datetime] = None

    def __post_init__(self) -> None:
        self.rng = random.Random(self.seed)
        self.clock = self.base_time or datetime.now(timezone.utc)
        # name -> {ifindex: last raw counter value}
        self._counters: Dict[str, Dict[int, float]] = {}
        self._observations: List[Dict[str, Any]] = []

    # -- phase-shaped load profiles -------------------------------------
    @staticmethod
    def _profile(phase: str) -> Dict[str, float]:
        return {
            "baseline": {"utilisation": 0.18, "errors": 0.02, "cpu": 22.0, "up_p": 1.0},
            "suspicious": {"utilisation": 0.52, "errors": 0.10, "cpu": 58.0, "up_p": 0.98},
            "detection": {"utilisation": 0.91, "errors": 0.42, "cpu": 88.0, "up_p": 0.90},
            "containment": {"utilisation": 0.34, "errors": 0.08, "cpu": 46.0, "up_p": 0.96},
            "recovery": {"utilisation": 0.20, "errors": 0.02, "cpu": 25.0, "up_p": 1.0},
        }[phase]

    def _capacity_bps(self) -> float:
        return float(self.rng.choice((1_000_000_000, 10_000_000_000)))

    def sample(
        self,
        phase: str = "baseline",
        interface: Optional[str] = None,
        force_counter_event: Optional[str] = None,
    ) -> SnmpMetricRecord:
        """Produce one typed sample set.

        ``force_counter_event`` in ``{"wrap", "reset"}`` drives the counter
        maths deliberately so tests can prove the handling, instead of waiting
        for a wrap to occur by chance.
        """
        prof = self._profile(phase)
        ifname, ifindex = self._pick_interface(interface)
        capacity = self._capacity_bps()

        values: Dict[str, float] = {}
        fields: Dict[str, Any] = {
            "if_index": ifindex,
            "if_name": ifname,
            "snmp_device": self.device,
            "snmp_phase": phase,
        }

        # --- cumulative counters (delta + rollover aware) ---
        for name in ("ifHCInOctets", "ifHCOutOctets", "ifInErrors", "ifOutErrors"):
            entry = REGISTRY[name]
            state = self._counters.setdefault(name, {})
            previous = state.get(ifindex)
            increment = self._increment(name, prof, capacity)

            if force_counter_event == "wrap" and previous is not None:
                # Park the counter just under the ceiling so the next step
                # genuinely crosses it, instead of hoping a wrap happens by chance.
                previous = float(entry.counter_max - int(increment * 0.5))
                state[ifindex] = previous

            current = self._advance(previous, increment, entry, force_counter_event)
            state[ifindex] = current
            values[name] = current
            fields[f"snmp_oid:{name}"] = entry.oid
            if previous is not None:
                rate = counter_rate(
                    previous, current, entry.syntax,
                    self.interval_seconds, unit="octets_per_second"
                    if "Octets" in name else "errors_per_second",
                )
                fields[f"snmp_delta:{name}"] = rate["delta"]
                fields[f"snmp_method:{name}"] = rate["method"]
                if "Octets" in name:
                    # Use the wrap/reset-aware delta, not a naive subtraction.
                    values[f"{name}Rate"] = round(
                        rate["delta"] * 8.0 / self.interval_seconds, 3
                    )

        # --- instantaneous gauges (never differenced, never wrapped) ---
        cpu = REGISTRY["hrProcessorLoad"]
        values["hrProcessorLoad"] = round(
            min(cpu.maximum, max(cpu.minimum, prof["cpu"] + self.rng.uniform(-6, 6))), 2
        )
        fields["snmp_oid:hrProcessorLoad"] = cpu.oid
        values["ifSpeed"] = capacity
        fields["snmp_oid:ifSpeed"] = REGISTRY["ifSpeed"].oid

        # --- enumeration (decoded, NOT published as a metric) ---
        # Averaging or summing ifOperStatus is meaningless, so the numeric code
        # stays in the descriptive fields alongside its decoded label and is
        # deliberately excluded from the metric data map.
        oper = REGISTRY["ifOperStatus"]
        code = 1 if self.rng.random() < prof["up_p"] else 2
        fields["snmp_ifOperStatus_code"] = code
        fields["snmp_ifOperStatus"] = IF_OPER_STATUS_VALUES[code]
        fields["snmp_oid:ifOperStatus"] = oper.oid

        utilisation = round(prof["utilisation"] * 100 * self.rng.uniform(0.92, 1.08), 2)
        values["interface_utilization_percent"] = min(100.0, max(0.0, utilisation))

        # Invariant: no enumeration may leak into the metric data map.
        for published in values:
            entry = REGISTRY.get(published)
            if entry is not None and entry.syntax in (OidSyntax.ENUM, OidSyntax.STRING):
                raise RuntimeError(
                    f"{published} is {entry.syntax.value} and must not be "
                    f"published as a metric"
                )

        record = SnmpMetricRecord(
            device=self.device,
            interface=ifname,
            index=ifindex,
            sourcetype=SNMP_METRIC_SOURCETYPE,
            index_target=self.index_target,
            values=values,
            raw_fields=fields,
            event_time=self.clock,
            phase=phase,
        )
        record.raw_log = json.dumps(
            {
                "data": {k: v for k, v in values.items()},
                "fields": fields,
                "oid_syntax": {k: REGISTRY[k].syntax.value for k in values if k in REGISTRY},
            },
            sort_keys=True,
        )
        self._observations.append({"phase": phase, "if": ifname, "values": dict(values)})
        return record

    def generate(
        self, count: int = 1, phase: str = "baseline", interface: Optional[str] = None
    ) -> List[SnmpMetricRecord]:
        """Emit exactly ``count`` records (or raise)."""
        if count < 0:
            raise ValueError("count must be >= 0")
        if phase not in self._profile_names():
            raise ValueError(f"unknown phase {phase!r}")
        out = []
        for _ in range(count):
            out.append(self.sample(phase=phase, interface=interface))
        return out

    def _profile_names(self) -> Sequence[str]:
        return ("baseline", "suspicious", "detection", "containment", "recovery")

    def _pick_interface(self, interface: Optional[str]) -> Tuple[str, int]:
        if interface:
            for name, idx in self.interfaces:
                if name == interface:
                    return name, idx
            raise ValueError(f"unknown interface {interface!r}")
        return self.interfaces[self.rng.randrange(len(self.interfaces))]

    def _increment(self, name: str, prof: Dict[str, float], capacity: float) -> float:
        if name.endswith("Errors") or name.endswith("Discards"):
            return float(self.rng.randint(0, 50) * (1.0 + prof["errors"] * 8))
        # octets over the interval at the phase's utilisation
        return capacity * prof["utilisation"] * self.interval_seconds / 8.0 * self.rng.uniform(0.85, 1.15)

    def _advance(
        self,
        previous: Optional[float],
        increment: float,
        entry: TypedOid,
        force_counter_event: Optional[str],
    ) -> float:
        """Advance a cumulative counter, in integer space.

        SNMP counters are integral, and a Counter64 lives beyond exact float64
        integer range, so the ceiling arithmetic below is done with ints.
        """
        max_value = entry.counter_max
        if previous is None:
            return float(int(round(increment)))
        if force_counter_event == "reset":
            # Agent restarted: the counter begins again from a small value.
            return float(int(round(increment * 0.25)))
        nxt = int(round(previous)) + int(round(increment))
        if nxt > max_value:
            # Genuine wrap past the ceiling.
            return float(nxt - (max_value + 1))
        return float(nxt)

    # -- introspection for coverage reporting ----------------------------
    @property
    def observations(self) -> List[Dict[str, Any]]:
        return list(self._observations)

    @staticmethod
    def registry_summary() -> Dict[str, Any]:
        by_verification: Dict[str, int] = {}
        by_syntax: Dict[str, int] = {}
        for entry in REGISTRY.values():
            key = entry.verification.value
            by_verification[key] = by_verification.get(key, 0) + 1
            syntax_key = entry.syntax.value
            by_syntax[syntax_key] = by_syntax.get(syntax_key, 0) + 1
        return {
            "registry_size": len(REGISTRY),
            "generatable": sum(1 for e in REGISTRY.values() if e.generatable),
            "by_syntax": by_syntax,
            "by_verification": by_verification,
            "unresolved_held_back": len(UNRESOLVED_BY_DESIGN),
        }


def to_log_entry(rec: SnmpMetricRecord):
    """Bridge a modeled SNMP sample onto the production ``LogEntry`` model.

    The dispatcher turns a metric-kind ``LogEntry`` into an HEC metric payload
    by reading the numeric ``data`` mapping out of ``raw_log``, which
    :meth:`SnmpMetricGenerator.sample` already writes. Reusing that path is the
    point: no parallel dispatch framework, and the record lands in the metrics
    index like any other metric source.
    """
    from netspout_core.models import LogEntry, NodeType

    oper = rec.raw_fields.get("snmp_ifOperStatus", "up")
    degraded = oper != "up" or rec.values.get("interface_utilization_percent", 0) > 85
    return LogEntry(
        timestamp=rec.event_time.isoformat(),
        device_id=rec.device,
        src_ip="0.0.0.0",
        dest_ip="0.0.0.0",
        protocol="snmp",
        duration=f"{rec.raw_fields.get('if_index', 0)}",
        #: "modeled" -- not "polled". Nothing here opened a socket.
        action="modeled",
        status="degraded" if degraded else "normal",
        signature=(
            f"SNMP modeled telemetry: {rec.interface} "
            f"({REGISTRY['ifHCInOctets'].oid} family, {rec.phase})"
        ),
        raw_log=rec.raw_log,
        node_type=NodeType.SWITCH.value,
        node_id=rec.device,
        vendor="generic_snmp",
        sourcetype=rec.sourcetype,
        netspout_ground_truth=(
            f"snmp/{rec.interface}/{rec.phase}/"
            f"{rec.raw_fields.get('snmp_method:ifHCInOctets', 'increase')}"
        ),
    )
