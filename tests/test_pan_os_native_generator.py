"""Tests for the native PAN-OS syslog generator.

These guard the claims the previous ``AuthenticPaloAltoGenerator`` could not make:
exact record counts, native (non-LEEF) PAN-OS field layout pinned to the repo's
frozen reference samples, canonical ``pan:*`` sourcetypes, determinism, and
credential/data hygiene.
"""
from __future__ import annotations

import csv
import io
import re
from pathlib import Path

import pytest

from netspout_core.panos_generator import (
    CONFIG_VERSION,
    FIELD_COUNTS,
    PHASES,
    SYSTEM_FIELDS,
    THREAT_FIELDS,
    TRAFFIC_FIELDS,
    PanOsGenerator,
)

REPO = Path(__file__).resolve().parents[1]
SAMPLES = REPO / "netspout" / "appserver" / "static" / "samples"

#: Reference field counts taken from the repo's own byte-frozen YAML samples,
#: not from this module, so a change here cannot silently redefine the contract.
REFERENCE_COUNTS = {"TRAFFIC": 54, "THREAT": 45, "SYSTEM": 17}


def _reference_raw(name: str) -> list[str]:
    text = (SAMPLES / name / f"{name}.yml").read_text()
    raw = re.findall(r"_raw: '(.+)'", text)[0]
    return next(csv.reader(io.StringIO(raw)))


# ---------------------------------------------------------------------------
# Record-count correctness (the bug the old generator shipped with)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("log_type", ["TRAFFIC", "THREAT", "SYSTEM"])
@pytest.mark.parametrize("count", [0, 1, 2, 5, 20])
def test_requested_count_is_exact(log_type: str, count: int) -> None:
    g = PanOsGenerator(seed=42)
    recs = g.generate(log_type, count=count, phase="detection")
    assert len(recs) == count, (
        f"{log_type}: requested {count} but generator returned {len(recs)}"
    )


def test_negative_count_raises() -> None:
    with pytest.raises(ValueError):
        PanOsGenerator(seed=1).generate("TRAFFIC", count=-1)


def test_unknown_log_type_raises() -> None:
    with pytest.raises(ValueError):
        PanOsGenerator(seed=1).generate("LEEFCOERCE", count=1)


def test_unknown_phase_raises() -> None:
    with pytest.raises(ValueError):
        PanOsGenerator(seed=1).generate("TRAFFIC", count=1, phase="not-a-phase")


# ---------------------------------------------------------------------------
# Native field layout pinned to the frozen reference samples
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "log_type,name", [("TRAFFIC", "pan-traffic"), ("THREAT", "pan-threat"),
                      ("SYSTEM", "pan-system")]
)
def test_field_count_matches_frozen_reference(log_type: str, name: str) -> None:
    reference = _reference_raw(name)
    assert len(reference) == REFERENCE_COUNTS[log_type]
    generated = PanOsGenerator(seed=3).generate(log_type, count=1, phase="baseline")[0]
    fields = PanOsGenerator.split_native_csv(generated.raw)
    assert len(fields) == len(reference), (
        f"{name}: generated {len(fields)} fields, reference {len(reference)}"
    )


@pytest.mark.parametrize(
    "log_type", ["TRAFFIC", "THREAT", "SYSTEM"]
)
def test_positional_semantics_match_reference(log_type: str) -> None:
    name = {"TRAFFIC": "pan-traffic", "THREAT": "pan-threat",
            "SYSTEM": "pan-system"}[log_type]
    reference = _reference_raw(name)
    generated = PanOsGenerator(seed=5).generate(log_type, count=1, phase="baseline")[0]
    fields = PanOsGenerator.split_native_csv(generated.raw)
    index = 3
    assert reference[0] == "1"                              # future-use placeholder
    assert fields[0] == reference[0]
    assert reference[index] == log_type                     # type at documented position
    assert fields[index] == log_type
    assert fields[5] == CONFIG_VERSION                      # PAN-OS config version
    assert reference[5] == CONFIG_VERSION
    assert fields[2].isdigit() and len(fields[2]) == 12      # serial number shape


@pytest.mark.parametrize(
    "log_type,name", [("TRAFFIC", "pan-traffic"), ("THREAT", "pan-threat"),
                      ("SYSTEM", "pan-system")]
)
def test_timestamp_format_matches_reference(log_type: str, name: str) -> None:
    reference = _reference_raw(name)
    generated = PanOsGenerator(seed=9).generate(log_type, count=1, phase="baseline")[0]
    fields = PanOsGenerator.split_native_csv(generated.raw)
    # PAN-OS syslog uses slash-delimited dates. The pattern is taken from the
    # frozen reference bytes, not from an assumption, so the contract cannot drift.
    ts_pattern = r"\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}"
    assert re.fullmatch(ts_pattern, reference[1]), f"reference oddity: {reference[1]!r}"
    assert re.fullmatch(ts_pattern, fields[1]), fields[1]


def test_name_lists_and_emitted_values_cannot_drift() -> None:
    """Layout metadata length must equal emitted field length for every type."""
    g = PanOsGenerator(seed=11)
    for log_type, names in (
        ("TRAFFIC", TRAFFIC_FIELDS), ("THREAT", THREAT_FIELDS), ("SYSTEM", SYSTEM_FIELDS)
    ):
        emitted = PanOsGenerator.split_native_csv(
            g.generate(log_type, count=1, phase="baseline")[0].raw
        )
        assert len(names) == len(emitted) == FIELD_COUNTS[log_type]
        assert len(set(names)) == len(names), f"{log_type}: duplicate field name"


# ---------------------------------------------------------------------------
# It must be native PAN-OS, never LEEF/CEF
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("log_type", ["TRAFFIC", "THREAT", "SYSTEM"])
def test_output_is_native_not_leef_or_cef(log_type: str) -> None:
    for rec in PanOsGenerator(seed=2).generate(log_type, count=4, phase="detection"):
        assert not rec.raw.startswith("LEEF"), "LEEF payload labelled native"
        assert not rec.raw.startswith("CEF"), "CEF payload labelled native"
        assert "|PaloAlto|" not in rec.raw
        assert rec.raw.split(",")[3] == log_type


def test_leef_marker_is_absent_from_module_source() -> None:
    import netspout_core.panos_generator as mod

    source = Path(mod.__file__).read_text()
    assert "LEEF:2.0" not in source


# ---------------------------------------------------------------------------
# Canonical sourcetypes
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "log_type,expected",
    [("TRAFFIC", "pan:traffic"), ("THREAT", "pan:threat"), ("SYSTEM", "pan:system")],
)
def test_canonical_sourcetype(log_type: str, expected: str) -> None:
    rec = PanOsGenerator(seed=4).generate(log_type, count=1, phase="baseline")[0]
    assert rec.sourcetype == expected
    assert "paloalto" not in rec.sourcetype


@pytest.mark.parametrize("expected", ["pan:traffic", "pan:threat", "pan:system"])
def test_sourcetypes_exist_in_canonical_catalog(expected: str) -> None:
    catalog = REPO / "catalog" / "sourcetypes.json"
    text = catalog.read_text()
    assert expected in text, f"{expected} missing from canonical catalog"


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------

def test_same_seed_is_byte_identical() -> None:
    a = [r.raw for r in PanOsGenerator(seed=1234).generate("TRAFFIC", 6, phase="detection")]
    b = [r.raw for r in PanOsGenerator(seed=1234).generate("TRAFFIC", 6, phase="detection")]
    assert a == b


def test_different_seed_differs() -> None:
    a = PanOsGenerator(seed=1).generate("THREAT", 5, phase="detection")[0].raw
    b = PanOsGenerator(seed=2).generate("THREAT", 5, phase="detection")[0].raw
    assert a != b


# ---------------------------------------------------------------------------
# Scenario phase semantics
# ---------------------------------------------------------------------------

def test_phase_changes_security_mix() -> None:
    """Baseline should be mostly allowed; containment should mostly block."""
    def deny_share(phase: str) -> float:
        recs = PanOsGenerator(seed=8).generate("TRAFFIC", 200, phase=phase)
        blocked = sum(1 for r in recs if r.raw.split(",")[30] != "allow")
        return blocked / len(recs)

    assert deny_share("baseline") < 0.25
    assert deny_share("containment") > 0.75


def test_all_phases_generate() -> None:
    g = PanOsGenerator(seed=6)
    for phase in PHASES:
        assert len(g.generate("TRAFFIC", 3, phase=phase)) == 3
        assert len(g.generate("THREAT", 3, phase=phase)) == 3
        assert len(g.generate("SYSTEM", 3, phase=phase)) == 3


def test_system_severity_follows_phase() -> None:
    base = PanOsGenerator(seed=1).generate("SYSTEM", 20, phase="baseline")
    cont = PanOsGenerator(seed=1).generate("SYSTEM", 20, phase="containment")
    assert {r.fields["pan_severity"] for r in base} == {"informational"}
    assert {r.fields["pan_severity"] for r in cont} == {"critical"}


# ---------------------------------------------------------------------------
# Hygiene: no credentials, no customer data
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("log_type", ["TRAFFIC", "THREAT", "SYSTEM"])
def test_no_credentials_or_customer_data_in_output(log_type: str) -> None:
    g = PanOsGenerator(seed=13)
    blob = "\n".join(
        r.raw for phase in PHASES for r in g.generate(log_type, 10, phase=phase)
    )
    lowered = blob.lower()
    for forbidden in ("password", "token", "secret", "authorization", "splunk "):
        assert forbidden not in lowered, f"{forbidden!r} leaked into output"
    # External addresses must stay in documentation space.
    for ip in re.findall(r"\b\d{1,3}(?:\.\d{1,3}){3}\b", blob):
        if ip in ("0.0.0.0", "10.0.0.0"):
            continue
        first = int(ip.split(".")[0])
        assert first in (10, 172, 192, 198, 203, 169), f"non-documentation IP {ip}"


def test_field_name_lists_are_unique_and_ordered() -> None:
    assert FIELD_COUNTS == {"TRAFFIC": 54, "THREAT": 45, "SYSTEM": 17}
    assert TRAFFIC_FIELDS[:4] == (
        "future_use_1", "receive_time", "serial_number", "type"
    )
