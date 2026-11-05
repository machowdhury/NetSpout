"""Cisco ASA (sourcetype cisco:asa) format contract. Fixtures: tests/fixtures/cisco_asa/message_formats.json (Cisco ASA syslog guide shapes).
Checks vendor format only; Splunk Add-on for Cisco ASA parsing is verified separately (docs/contracts/cisco_asa_ta_compat.md)."""
import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src")]

from netspout_core import generator_modes  # noqa: E402
from netspout_core.asa_generator import generate_asa_entries  # noqa: E402

FIX = json.loads((ROOT / "tests/fixtures/cisco_asa/message_formats.json").read_text())
FORMATS = {k: re.compile(v) for k, v in FIX["formats"].items()}
HEADER = re.compile(FIX["header"])


def _code(raw):
    return re.search(r"%ASA-\d-(\d{6}):", raw).group(1)


def test_fixture_examples_match_templates():
    for raw in FIX["documented_examples"]:
        assert HEADER.match(raw)
        assert FORMATS[_code(raw)].search(raw), raw


def test_every_generated_event_matches_a_documented_template():
    entries = generate_asa_entries(200, seed=7)
    assert len(entries) == 200
    seen = set()
    for e in entries:
        assert e.sourcetype == "cisco:asa" and e.vendor == "cisco_asa"
        assert HEADER.match(e.raw_log), e.raw_log
        code = _code(e.raw_log)
        assert FORMATS[code].search(e.raw_log), e.raw_log
        seen.add(code)
    assert {"302013", "302014", "106023"} <= seen


def test_no_yaml_metadata_or_unrendered_tokens():
    for e in generate_asa_entries(50, seed=1):
        assert "$" not in e.raw_log and "sourcetype:" not in e.raw_log and "randomizeEvents" not in e.raw_log


def test_teardown_follows_its_build_and_direction_is_consistent():
    built = {}
    for e in generate_asa_entries(100, seed=3):
        b = re.search(r"%ASA-6-30201[35]: Built (\w+) \w+ connection (\d+) ", e.raw_log)
        if b:
            built[b.group(2)] = b.group(1)
        t = re.search(r"%ASA-6-30201[46]: Teardown \w+ connection (\d+) ", e.raw_log)
        if t:
            assert t.group(1) in built, "teardown before (or without) its build"
    assert built and set(built.values()) == {"outbound"}


def test_deterministic_for_same_seed_and_time():
    a = [e.raw_log for e in generate_asa_entries(20, seed=5, now=1_700_000_000)]
    b = [e.raw_log for e in generate_asa_entries(20, seed=5, now=1_700_000_000)]
    assert a == b


def test_preview_equals_dispatched_output(monkeypatch):
    sent = []
    monkeypatch.setattr(generator_modes.dispatcher, "dispatch_log", lambda e, cfg: (sent.append((e.raw_log, e.sourcetype)), {"hec": {"success": True}})[1])
    svc = generator_modes.TelemetryGeneratorService()
    assert len(svc.generate_sourcetype_batch("cisco_asa", "cisco:asa", 5, 10, dispatch=False)["sample_preview"]) == 3
    out = svc.generate_sourcetype_batch("cisco_asa", "cisco:asa", 5, 10, dispatch=True)
    assert out["count_dispatched"] == 5 and all(st == "cisco:asa" for _, st in sent)
    assert out["sample_preview"] == [r for r, _ in sent][:3]  # the preview of a run is the first events actually delivered
    assert not any("$" in r or "sourcetype:" in r for r, _ in sent)
    for raw, _ in sent:
        assert FORMATS[_code(raw)].search(raw)


def test_prepare_entries_uses_native_generator():
    entries, prov = generator_modes.TelemetryGeneratorService().prepare_sourcetype_entries("cisco_asa", "cisco:asa", 10, run_id="r1")
    assert prov["mode"] == "native" and len(entries) == 10
    assert all(e.sourcetype == "cisco:asa" and e.netspout_run_id == "r1" and FORMATS[_code(e.raw_log)].search(e.raw_log) for e in entries)


def test_non_ta_sourcetype_is_refused():
    svc = generator_modes.TelemetryGeneratorService()
    with pytest.raises(ValueError, match="NON_CANONICAL_SOURCETYPE"):
        svc.generate_sourcetype_batch("cisco_asa", "cisco:asa:syslog", 3, 10)
    with pytest.raises(ValueError, match="NON_CANONICAL_SOURCETYPE"):
        svc.prepare_sourcetype_entries("cisco_asa", "cisco:asa:syslog", 3)
