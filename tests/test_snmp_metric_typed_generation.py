"""Tests for typed SNMP metric generation and metric routing.

These cover the claims the recovery has to be able to make honestly:
syntax-correct OIDs, wrap/reset-aware counters, exact record counts,
determinism, and delivery through the *existing* dispatcher metric path
without relabelling SNMP data as Cisco telemetry.
"""
from __future__ import annotations

import json
import math
from typing import Any, Dict, List

import pytest

from netspout_core.snmp_metrics import (
    COUNTER32_MAX,
    COUNTER64_MAX,
    IF_OPER_STATUS_VALUES,
    INFERRED_OIDS,
    REGISTRY,
    SNMP_METRIC_SOURCETYPE,
    UNRESOLVED_BY_DESIGN,
    VERIFIED_OIDS,
    OidSyntax,
    SnmpMetricGenerator,
    Verification,
    counter_delta,
    counter_rate,
    oid_is_generatable,
    to_log_entry,
)

PHASES = ("baseline", "suspicious", "detection", "containment", "recovery")


# ---------------------------------------------------------------------------
# Registry typing and honesty
# ---------------------------------------------------------------------------

def test_every_registry_entry_declares_syntax_and_unit() -> None:
    for name, entry in REGISTRY.items():
        assert isinstance(entry.syntax, OidSyntax), name
        assert entry.syntax is not OidSyntax.STRING, name
        assert entry.unit, f"{name} has no unit"
        assert entry.source, f"{name} has no reference for its claim"
        assert entry.oid.count(".") >= 4, f"{name} has no plausible OID"


def test_enumerations_have_a_value_map() -> None:
    for entry in REGISTRY.values():
        if entry.syntax is OidSyntax.ENUM:
            assert entry.values, f"{entry.name} is ENUM with no value map"
            assert set(entry.values) == set(range(1, 8))


def test_unresolved_inventory_is_never_generatable() -> None:
    for name in UNRESOLVED_BY_DESIGN:
        assert not oid_is_generatable(name), f"{name} must stay held back"
        assert name not in REGISTRY or REGISTRY[name].generatable is False


def test_verification_classes_are_declared_not_assumed() -> None:
    assert len(VERIFIED_OIDS) >= 8
    kinds = {o.verification for o in REGISTRY.values()}
    assert Verification.UNRESOLVED not in kinds
    assert {o.verification for o in INFERRED_OIDS} == {Verification.INFERRED}


def test_counter_widths_match_syntax() -> None:
    assert REGISTRY["ifInOctets"].syntax is OidSyntax.COUNTER32
    assert REGISTRY["ifInOctets"].counter_max == COUNTER32_MAX
    assert REGISTRY["ifHCInOctets"].syntax is OidSyntax.COUNTER64
    assert REGISTRY["ifHCInOctets"].counter_max == COUNTER64_MAX
    assert COUNTER64_MAX > COUNTER32_MAX


def test_gauge_and_counter_are_not_conflated() -> None:
    """The classic SNMP mistake: differencing a Gauge32."""
    assert REGISTRY["hrProcessorLoad"].cumulative is False
    assert REGISTRY["ifHCInOctets"].cumulative is True
    with pytest.raises(ValueError):
        counter_delta(10.0, 20.0, OidSyntax.GAUGE32)


# ---------------------------------------------------------------------------
# Counter arithmetic: increase, wrap, reset
# ---------------------------------------------------------------------------

def test_plain_increase() -> None:
    delta, how = counter_delta(1000.0, 2500.0, OidSyntax.COUNTER64)
    assert (delta, how) == (1500.0, "increase")


def test_counter32_wrap_is_not_read_as_a_huge_negative() -> None:
    previous = float(COUNTER32_MAX) - 500.0
    current = 400.0
    delta, how = counter_delta(previous, current, OidSyntax.COUNTER32)
    assert how == "wrap"
    # (max+1 - previous) + current == 501 + 400
    assert delta == 901.0
    assert delta > 0


def test_counter64_wrap() -> None:
    previous = COUNTER64_MAX - 1000
    current = 250
    delta, how = counter_delta(previous, current, OidSyntax.COUNTER64)
    assert how == "wrap"
    # (max+1) - previous + current == 1001 + 250
    assert delta == 1251.0


def test_counter64_wrap_math_needs_integers_not_float64() -> None:
    """Why the arithmetic is integer-based: 2**64-1 is not a float64.

    ``float(2**64 - 1)`` rounds up to ``2**64``, so the ceiling and the spacing
    between representable values (4096 here) destroy the boundary case. Feeding
    floats into a Counter64 delta silently produces the wrong answer; integers
    keep it exact. This is the reason a real poller must carry 64-bit counters
    as integers end to end.
    """
    as_float = float(COUNTER64_MAX - 1000)
    assert as_float == float(COUNTER64_MAX) or as_float % 4096 == 0.0
    # Exact integer form is what the generator stores and what the maths needs.
    assert COUNTER64_MAX - 1000 != int(as_float)
    delta, how = counter_delta(COUNTER64_MAX - 1000, 250, OidSyntax.COUNTER64)
    assert (delta, how) == (1251.0, "wrap")


def test_reboot_reset_is_distinguished_from_wrap() -> None:
    """A fall from a mid-range value is a restart, not a wrap."""
    previous, current = 50_000_000_000.0, 120.0
    delta, how = counter_delta(previous, current, OidSyntax.COUNTER64)
    assert how == "reset"
    assert delta == 120.0


def test_wrap_detection_boundary_is_at_the_ceiling() -> None:
    near_max = float(COUNTER32_MAX) * 0.96
    assert counter_delta(near_max, 10.0, OidSyntax.COUNTER32)[1] == "wrap"
    mid = float(COUNTER32_MAX) * 0.5
    assert counter_delta(mid, 10.0, OidSyntax.COUNTER32)[1] == "reset"


def test_rate_uses_delta_over_interval() -> None:
    res = counter_rate(0.0, 3000.0, OidSyntax.COUNTER64, interval_seconds=30.0)
    assert res["rate"] == 100.0
    assert res["method"] == "increase"
    assert res["unit"] == "per_second"


def test_rate_rejects_non_positive_interval() -> None:
    with pytest.raises(ValueError):
        counter_rate(1.0, 2.0, OidSyntax.COUNTER64, interval_seconds=0.0)


# ---------------------------------------------------------------------------
# Generator behaviour
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("count", [0, 1, 2, 5, 12])
def test_generate_honours_count_exactly(count: int) -> None:
    gen = SnmpMetricGenerator(seed=3)
    assert len(gen.generate(count=count, phase="baseline")) == count


def test_negative_count_raises() -> None:
    with pytest.raises(ValueError):
        SnmpMetricGenerator(seed=3).generate(count=-1)


def test_unknown_phase_raises() -> None:
    with pytest.raises(ValueError):
        SnmpMetricGenerator(seed=3).generate(count=1, phase="meltdown")


def test_unknown_interface_raises() -> None:
    with pytest.raises(ValueError):
        SnmpMetricGenerator(seed=3).sample(interface="Vlanif999")


def test_counters_increase_monotonically_without_forced_events() -> None:
    gen = SnmpMetricGenerator(seed=11)
    series: List[float] = []
    for _ in range(8):
        rec = gen.sample(phase="baseline", interface="GigabitEthernet0/0/1")
        series.append(rec.values["ifHCInOctets"])
    assert all(b > a for a, b in zip(series, series[1:]))
    assert all(float(a).is_integer() for a in series), "counters must be integral"


def test_forced_wrap_is_reported_as_wrap() -> None:
    gen = SnmpMetricGenerator(seed=5)
    gen.sample(phase="baseline", interface="GigabitEthernet0/0/1")
    rec = gen.sample(
        phase="detection", interface="GigabitEthernet0/0/1", force_counter_event="wrap"
    )
    assert rec.raw_fields["snmp_method:ifHCInOctets"] == "wrap"
    assert rec.raw_fields["snmp_delta:ifHCInOctets"] > 0


def test_forced_reset_is_reported_as_reset() -> None:
    gen = SnmpMetricGenerator(seed=5)
    gen.sample(phase="baseline", interface="GigabitEthernet0/0/1")
    rec = gen.sample(
        phase="detection", interface="GigabitEthernet0/0/1", force_counter_event="reset"
    )
    assert rec.raw_fields["snmp_method:ifHCInOctets"] == "reset"


def test_forced_wrap_yields_sane_rate_not_a_stratospheric_one() -> None:
    """After a wrap the derived rate must stay within the link capacity."""
    gen = SnmpMetricGenerator(seed=17)
    gen.sample(phase="baseline", interface="GigabitEthernet0/0/1")
    rec = gen.sample(
        phase="detection", interface="GigabitEthernet0/0/1", force_counter_event="wrap"
    )
    capacity = rec.values["ifSpeed"]
    rate = rec.values["ifHCInOctetsRate"]
    assert 0 <= rate <= capacity * 1.5, (
        f"rate {rate} bps exceeds capacity {capacity} bps after a wrap"
    )


def test_gauge_values_stay_within_documented_bounds() -> None:
    gen = SnmpMetricGenerator(seed=23)
    for phase in PHASES:
        for rec in gen.generate(count=4, phase=phase):
            assert 0.0 <= rec.values["hrProcessorLoad"] <= 100.0
            assert 0.0 <= rec.values["interface_utilization_percent"] <= 100.0


def test_enum_is_decoded_and_never_silently_numeric() -> None:
    gen = SnmpMetricGenerator(seed=29)
    for phase in PHASES:
        for rec in gen.generate(count=3, phase=phase):
            code = int(rec.raw_fields["snmp_ifOperStatus_code"])
            assert code in IF_OPER_STATUS_VALUES
            assert rec.raw_fields["snmp_ifOperStatus"] == IF_OPER_STATUS_VALUES[code]


def test_down_phase_loads_more_errors_than_baseline() -> None:
    base = SnmpMetricGenerator(seed=31)
    hard = SnmpMetricGenerator(seed=31)

    def err(gen: SnmpMetricGenerator, phase: str) -> float:
        total = 0.0
        for _ in range(30):
            rec = gen.sample(phase=phase, interface="GigabitEthernet0/0/1")
            # The first sample of a counter has no predecessor, so no delta yet.
            total += float(rec.raw_fields.get("snmp_delta:ifInErrors", 0.0))
        return total

    assert err(hard, "detection") > err(base, "baseline")


def test_same_seed_is_reproducible() -> None:
    a = [r.raw_log for r in SnmpMetricGenerator(seed=101).generate(4, "detection")]
    b = [r.raw_log for r in SnmpMetricGenerator(seed=101).generate(4, "detection")]
    assert a == b


def test_different_seed_differs() -> None:
    a = SnmpMetricGenerator(seed=1).generate(3, "detection")[1].raw_log
    b = SnmpMetricGenerator(seed=2).generate(3, "detection")[1].raw_log
    assert a != b


def test_raw_log_is_json_with_numeric_data_map() -> None:
    """The dispatcher extracts metric names from raw_log["data"]; keep that shape."""
    rec = SnmpMetricGenerator(seed=7).sample(phase="baseline")
    obj = json.loads(rec.raw_log)
    assert isinstance(obj["data"], dict) and obj["data"]
    for key, value in obj["data"].items():
        assert isinstance(value, (int, float)) and not isinstance(value, bool), key
        assert math.isfinite(float(value)), key
    assert isinstance(obj["fields"], dict)


def test_metric_names_do_not_include_enumerations() -> None:
    """Averaging ifOperStatus would be meaningless; it must not arrive as a metric."""
    rec = SnmpMetricGenerator(seed=9).sample(phase="baseline")
    obj = json.loads(rec.raw_log)
    assert "ifOperStatus" not in obj["data"], "enumeration published as a metric"
    for name in obj["data"]:
        entry = REGISTRY.get(name)
        if entry is not None:
            assert entry.syntax not in (OidSyntax.ENUM, OidSyntax.STRING), name
    # The code is still available, decoded, as a descriptive field.
    assert "snmp_ifOperStatus" in rec.raw_fields
    assert rec.raw_fields["snmp_ifOperStatus"] in IF_OPER_STATUS_VALUES.values()


# ---------------------------------------------------------------------------
# Production routing: dispatcher metric path
# ---------------------------------------------------------------------------

def test_sourcetype_is_canonical_metric_kind() -> None:
    from netspout_core.catalog import catalog_instance

    entry = catalog_instance.get_sourcetype(SNMP_METRIC_SOURCETYPE)
    assert entry, f"{SNMP_METRIC_SOURCETYPE} missing from canonical catalog"
    assert entry["data_kind"] == "metric"
    assert entry["status"] == "active"


def test_dispatcher_routes_snmp_sourcetype_as_metric() -> None:
    from netspout_core.telemetry_dispatcher import is_metric_sourcetype

    assert is_metric_sourcetype(SNMP_METRIC_SOURCETYPE)
    assert is_metric_sourcetype("cisco:ios:mdt")
    assert is_metric_sourcetype("cisco:ios:mdt:metric")
    assert not is_metric_sourcetype("pan:traffic")
    assert not is_metric_sourcetype("cisco:dc:aci:health")
    assert not is_metric_sourcetype(None)


def test_metric_payload_keeps_snmp_sourcetype_not_cisco() -> None:
    """SNMP data must never be relabelled as Cisco MDT telemetry."""
    from netspout_core.models import TelemetryTransportConfig
    from netspout_core.telemetry_dispatcher import TelemetryDispatcher

    captured: Dict[str, Any] = {}

    def fake_emit(payload, url, token, **kwargs):
        captured["payload"] = payload
        return True, "ok"

    dispatcher = TelemetryDispatcher()
    dispatcher.emit_hec = fake_emit  # type: ignore[assignment]

    rec = SnmpMetricGenerator(seed=4).sample(phase="detection")
    transport = TelemetryTransportConfig(
        hec_enabled=True,
        hec_url="https://127.0.0.1:18088/services/collector",
        hec_token="token-not-a-secret-in-tests",
        hec_index="idx_network_ops",
        hec_metric_index="idx_performance_metrics",
    )
    dispatcher.dispatch_log(to_log_entry(rec), transport)

    payload = captured.get("payload")
    assert payload, "no HEC payload was produced"
    assert payload["event"] == "metric"
    assert payload["index"] == "idx_performance_metrics"
    assert payload["sourcetype"] == SNMP_METRIC_SOURCETYPE
    assert "cisco" not in payload["sourcetype"]
    names = [k for k in payload["fields"] if k.startswith("metric_name:")]
    assert names, "metric_name:* fields missing from payload"


def test_metric_payload_still_cisco_for_mdt_logs() -> None:
    """Backward compatibility: Cisco MDT keeps its historic labels."""
    from netspout_core.log_engine import SplunkLogEngine
    from netspout_core.models import Node, NodeType, TelemetryTransportConfig
    from netspout_core.telemetry_dispatcher import TelemetryDispatcher

    captured: Dict[str, Any] = {}
    dispatcher = TelemetryDispatcher()
    dispatcher.emit_hec = lambda p, u, t, **k: (captured.update(payload=p), (True, "ok"))[1]

    node = Node(id="n1", name="nx9k-01", type=NodeType.SWITCH, ip_address="10.0.0.1",
                vendor="cisco_nexus", sourcetype="cisco:ios:mdt")
    transport = TelemetryTransportConfig(
        hec_enabled=True, hec_url="https://127.0.0.1:18088/services/collector",
        hec_token="t", hec_index="idx_network_ops",
        hec_metric_index="idx_performance_metrics",
    )
    dispatcher.dispatch_log(
        SplunkLogEngine.format_cisco_mdt_log(
            device=node, sensor_path="ifmc-if:statistics",
            queue_depth_bytes=1000, peak_buffer_pct=10.0,
            action="streamed", status="normal", signature="MDT nominal"
        ),
        transport,
    )
    payload = captured["payload"]
    assert payload["sourcetype"] == "cisco:ios:mdt:metric"
    assert payload["source"] == "cisco:ios:mdt"
    assert payload["index"] == "idx_performance_metrics"


def test_event_sourcetypes_still_route_to_event_index() -> None:
    from netspout_core.panos_generator import PanOsGenerator
    from netspout_core.panos_generator import to_log_entry as pan_to_entry
    from netspout_core.models import TelemetryTransportConfig
    from netspout_core.telemetry_dispatcher import TelemetryDispatcher

    captured: Dict[str, Any] = {}
    dispatcher = TelemetryDispatcher()
    dispatcher.emit_hec = lambda p, u, t, **k: (captured.update(payload=p), (True, "ok"))[1]

    pan_rec = PanOsGenerator(seed=2).generate("TRAFFIC", 1, phase="baseline")[0]
    transport = TelemetryTransportConfig(
        hec_enabled=True, hec_url="https://127.0.0.1:18088/services/collector",
        hec_token="t", hec_index="idx_network_ops",
        hec_metric_index="idx_performance_metrics",
    )
    dispatcher.dispatch_log(pan_to_entry(pan_rec), transport)
    payload = captured["payload"]
    assert payload["index"] == "idx_network_ops"
    assert payload["sourcetype"] == "pan:traffic"
    assert payload.get("event") != "metric"


# ---------------------------------------------------------------------------
# Language: modeled telemetry, never "polled"
# ---------------------------------------------------------------------------

def test_no_claim_of_polling_in_generated_output() -> None:
    """The word 'polled' would imply a wire that was never touched."""
    for rec in SnmpMetricGenerator(seed=6).generate(3, "detection"):
        assert "polled" not in rec.raw_log.lower()
        assert "SNMP polling" not in rec.raw_log


def test_module_declares_it_is_modeled_not_live() -> None:
    import netspout_core.snmp_metrics as mod
    from pathlib import Path

    doc = Path(mod.__file__).read_text()
    assert "synthetic measurements" in doc.lower()
    assert "never" in doc.lower()


def test_registry_summary_reports_classes() -> None:
    s = SnmpMetricGenerator.registry_summary()
    assert s["registry_size"] == len(REGISTRY)
    assert s["generatable"] == len(REGISTRY)
    assert s["unresolved_held_back"] == len(UNRESOLVED_BY_DESIGN)
    assert set(s["by_syntax"]) & {"counter32", "counter64", "gauge32", "enum"} == {
        "counter32", "counter64", "gauge32", "enum"
    }
