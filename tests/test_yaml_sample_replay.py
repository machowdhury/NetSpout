"""Structured sample replay: YAML metadata is never telemetry; tokens render; bad samples fail explicitly. The shipped sample directory is the regression corpus."""
import glob
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
import random

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src")]

from netspout_core import generator_modes  # noqa: E402
from netspout_core.yaml_sample_replay import (SampleFormatError, UnresolvedPlaceholderError, UnsupportedSampleError,  # noqa: E402
                                              load_sample_set, validate_sample_file)

SHIPPED = sorted(glob.glob(str(ROOT / "netspout/appserver/static/samples/*/*.yml")))
NOW = datetime(2026, 11, 3, 14, 5, 9, 123456, tzinfo=timezone.utc)
FIX = json.loads((ROOT / "tests/fixtures/cisco_asa/message_formats.json").read_text())


def _write(tmp_path, text, name="s.yml"):
    p = tmp_path / name
    p.write_text(text)
    return str(p)


def test_metadata_is_never_emitted(tmp_path):
    p = _write(tmp_path, """samples:
  - name: demo
    interval: 30
    count: 8
    randomizeEvents: false
    description: a configuration description that is far longer than twenty characters
    tokens:
      - name: HOST
        format: template
        type: static
        replacement: fw1
    lines:
      - index: i
        source: s
        sourcetype: vendor:product
        host: fw1
        _raw: "event from $HOST$"
""")
    out = load_sample_set(p).render_all(random.Random(1), NOW)
    assert out == ["event from fw1"]


def test_placeholder_rendering_and_go_layouts(tmp_path):
    p = _write(tmp_path, """samples:
  - name: t
    tokens:
      - {name: A, format: template, type: gotimestamp, replacement: "Jan 02 15:04:05"}
      - {name: B, format: template, type: gotimestamp, replacement: "2006-01-02T15:04:05Z"}
      - {name: C, format: template, type: gotimestamp, replacement: "2006-01-02 15:04:05.000 -07:00"}
      - {name: D, format: template, type: timestamp, replacement: "%Y-%m-%dT%H:%M:%S.%3NZ"}
      - {name: E, format: template, type: epochtimestamp}
      - {name: F, format: template, type: javatimestamp}
      - {name: G, format: template, type: random, replacement: int, lower: 7, upper: 7}
      - {name: H, format: template, type: weightedChoice, weightedChoice: [{weight: 1, choice: only}]}
      - {name: I, format: regex, token: "XX\\\\d+", type: static, replacement: done}
    lines:
      - {_raw: "$A$|$B$|$C$|$D$|$E$|$F$|$G$|$H$|XX123|$A$"}
""")
    out = load_sample_set(p).render_all(random.Random(1), NOW)[0]
    assert out == "Nov 03 14:05:09|2026-11-03T14:05:09Z|2026-11-03 14:05:09.123 +00:00|2026-11-03T14:05:09.123Z|%d|%d|7|only|done|Nov 03 14:05:09" % (
        int(NOW.timestamp()), int(NOW.timestamp() * 1000))


def test_unknown_placeholder_is_detected(tmp_path):
    p = _write(tmp_path, "samples:\n  - name: x\n    lines:\n      - {_raw: 'host $NOPE$ and $ALSO_NOPE$'}\n")
    with pytest.raises(UnresolvedPlaceholderError) as e:
        load_sample_set(p).render_all(random.Random(1), NOW)
    assert e.value.names == ["ALSO_NOPE", "NOPE"]
    assert validate_sample_file(p)["status"] == "UNRESOLVED_PLACEHOLDER"


@pytest.mark.parametrize("text,exc,fragment", [
    ("samples: [unclosed", SampleFormatError, "invalid YAML"),
    ("name: only config\ninterval: 1\n", SampleFormatError, "no `samples` list"),
    ("samples:\n  - name: empty\n    interval: 5\n", SampleFormatError, "no telemetry-bearing field"),
    ("samples:\n  - name: x\n    lines:\n      - {index: i}\n", SampleFormatError, "no _raw"),
    ("samples:\n  - name: x\n    fromRaw: missing.sample\n", SampleFormatError, "fromRaw file missing"),
    ("samples:\n  - name: x\n    tokens: [{name: A, format: template, type: fieldChoice}]\n    lines: [{_raw: a}]\n", UnsupportedSampleError, "fieldChoice"),
    ("samples:\n  - name: x\n    tokens: [{name: A, format: template, type: random, replacement: int}]\n    lines: [{_raw: a}]\n", SampleFormatError, "lower and upper"),
])
def test_malformed_samples_fail_clearly(tmp_path, text, exc, fragment):
    with pytest.raises(exc, match=re.escape(fragment)):
        load_sample_set(_write(tmp_path, text))


def test_adapters_fromraw_fromsample_and_multiline(tmp_path):
    (tmp_path / "raw.sample").write_text("line one\n\nline two\n")
    (tmp_path / "rows.csv").write_text('_raw,index,host,source,sourcetype\n"csv $X$",main,h,s,v:t\n')
    p = _write(tmp_path, """samples:
  - name: a
    fromRaw: raw.sample
    tokens: [{name: X, format: template, type: static, replacement: ok}]
  - name: b
    fromSample: rows.csv
    tokens: [{name: X, format: template, type: static, replacement: ok}]
  - name: c
    lines:
      - _raw: |
          first line
          second line
""")
    ss = load_sample_set(p)
    assert len(ss) == 4  # 2 raw lines (blank skipped) + 1 csv row + 1 inline
    out = ss.render_all(random.Random(1), NOW)
    assert out == ["line one", "line two", "csv ok", "first line\nsecond line"]
    assert ss.templates[2].sourcetype == "v:t"


def test_restrict_to_never_relabels(tmp_path):
    p = _write(tmp_path, "samples:\n  - name: x\n    lines:\n      - {sourcetype: a:b, _raw: one}\n      - {sourcetype: c:d, _raw: two}\n")
    ss = load_sample_set(p)
    assert ss.restrict_to("a:b").render_all() == ["one"]
    with pytest.raises(SampleFormatError, match="claims"):
        ss.restrict_to("z:z")


def test_oversize_is_refused_not_parsed(tmp_path, monkeypatch):
    from netspout_core import yaml_sample_replay as m
    monkeypatch.setattr(m, "MAX_YAML_BYTES", 10)
    with pytest.raises(SampleFormatError, match="OVERSIZE"):
        load_sample_set(_write(tmp_path, "samples:\n  - name: x\n    lines: [{_raw: a}]\n"))


# ------------------------------------------------------------- shipped corpus
def _raw_fields(path):
    doc = yaml.safe_load(open(path))
    return {str(l["_raw"]).rstrip("\n") for s in doc["samples"] for l in s.get("lines") or []}


def test_shipped_corpus_is_nonempty():
    assert len(SHIPPED) == 220


@pytest.mark.parametrize("path", SHIPPED, ids=[Path(p).parent.name for p in SHIPPED])
def test_every_shipped_file_replays_only_recognized_fields(path):
    rec = validate_sample_file(path)
    assert rec["status"] == "REPLAYABLE", rec
    ss = load_sample_set(path)
    assert {t.raw for t in ss.templates} <= _raw_fields(path)       # every event comes from a lines[]._raw field
    for out in ss.render_all(random.Random(3), NOW):
        assert not re.search(r"\$[A-Za-z_]\w*\$", out), out          # tokens rendered
        assert not re.match(r"^\s*(sourcetype|source|index|host|interval|count|randomizeEvents|replacement|choice|weight|name|format|type|lower|upper):\s", out), out


def test_event_count_matches_extracted_sample_events():
    for path in SHIPPED:
        doc = yaml.safe_load(open(path))
        expected = sum(len(s.get("lines") or []) for s in doc["samples"])
        assert len(load_sample_set(path)) == expected, path


def test_cisco_asa_replay_emits_real_asa_messages():
    p = ROOT / "netspout/appserver/static/samples/cisco-asa/cisco-asa.yml"
    out = load_sample_set(str(p)).render_all(random.Random(1), NOW)
    assert len(out) == 8
    header = re.compile(FIX["header"])
    fmt = {k: re.compile(v) for k, v in FIX["formats"].items()}
    for raw in out:
        assert header.match(raw), raw
        code = re.search(r"%ASA-\d-(\d{6})", raw).group(1)
        if code in fmt:
            assert fmt[code].search(raw), raw
    assert any("%ASA-6-302013" in r for r in out) and any("%ASA-4-106023" in r for r in out)


def test_service_replay_path_emits_asa_not_yaml():
    svc = generator_modes.TelemetryGeneratorService()
    pool, prov_class, _ = svc.get_grounded_samples("cisco:asa:syslog", vendor_id="cisco_asa")
    assert prov_class == "VERIFIED_PUBLIC_SAMPLE" and len(pool) == 8
    assert all("%ASA-" in e and "sourcetype:" not in e and "$" not in e for e in pool)


def test_metric_sourcetype_without_measurements_is_refused_not_replayed():
    svc = generator_modes.TelemetryGeneratorService()
    pool, prov_class, why = svc.get_grounded_samples("cisco:thousandeyes:metric")
    assert pool == [] and prov_class == "METRIC_REPLAY_UNSUPPORTED" and "numeric measurements" in why
    with pytest.raises(ValueError, match="TELEMETRY_NOT_GROUNDED"):
        svc.prepare_sourcetype_entries("cisco_thousandeyes", "cisco:thousandeyes:metric", 1)


def test_corpus_wide_event_samples_never_become_metrics():
    # a log sourcetype whose events contain numbers is not a metric stream and must not be treated as one
    from netspout_core.telemetry_dispatcher import is_metric_sourcetype
    assert not is_metric_sourcetype("cisco:asa") and not is_metric_sourcetype("cisco:asa:syslog")


def test_lines_without_raw_are_metadata_for_fromraw(tmp_path):
    (tmp_path / "ev.sample").write_text("alpha\nbeta\n")
    p = _write(tmp_path, "samples:\n  - name: x\n    fromRaw: ev.sample\n    lines:\n      - {index: main, sourcetype: v:t, source: s, host: h, _raw: ''}\n")
    ss = load_sample_set(p)
    assert ss.render_all() == ["alpha", "beta"]          # the empty _raw is not an event
    assert ss.sourcetypes() == ["v:t"] and {t.host for t in ss.templates} == {"h"}


def test_conflicting_sourcetype_claims_for_external_events_are_refused(tmp_path):
    (tmp_path / "ev.sample").write_text("alpha\n")
    p = _write(tmp_path, "samples:\n  - name: x\n    fromRaw: ev.sample\n    lines:\n      - {sourcetype: a:a, _raw: ''}\n      - {sourcetype: b:b, _raw: ''}\n")
    with pytest.raises(SampleFormatError, match="several sourcetypes"):
        load_sample_set(p)


def test_regex_token_single_group_replaces_only_the_group(tmp_path):
    p = _write(tmp_path, "samples:\n  - name: x\n    tokens: [{name: T, format: regex, token: 'time=([0-9]+)', type: static, replacement: NOW}]\n    lines: [{_raw: 'a time=123 b'}]\n")
    assert load_sample_set(p).render_all() == ["a time=NOW b"]


def test_regex_token_with_several_groups_is_unsupported_not_guessed(tmp_path):
    p = _write(tmp_path, "samples:\n  - name: x\n    tokens: [{name: T, format: regex, token: '(k=([0-9]+))', type: static, replacement: 1}]\n    lines: [{_raw: 'k=5'}]\n")
    with pytest.raises(UnsupportedSampleError, match="capture groups"):
        load_sample_set(p)


def test_corrupt_csv_fails_clearly(tmp_path):
    big = "x" * 200_000
    (tmp_path / "rows.csv").write_text('_raw\n"%s"\n' % big)
    p = _write(tmp_path, "samples:\n  - name: x\n    fromSample: rows.csv\n")
    with pytest.raises(SampleFormatError, match="not valid CSV"):
        load_sample_set(p)


def test_configuration_only_file_is_classified_not_replayed(tmp_path):
    rec = validate_sample_file(_write(tmp_path, "raters:\n  - name: r\nglobal:\n  x: 1\n"))
    assert rec["status"] == "CONFIG_ONLY" and rec["events"] == 0


def _config_strings(node, in_telemetry=False):
    """Every string in the YAML that is NOT a lines[]._raw telemetry field."""
    out = set()
    if isinstance(node, dict):
        for k, v in node.items():
            if k == "_raw":
                continue
            out |= _config_strings(v)
    elif isinstance(node, list):
        for v in node:
            out |= _config_strings(v)
    elif isinstance(node, str) and len(node) > 3:
        out.add(node.strip())
    return out


def _no_leak(path, limit=300):
    cfg = _config_strings(yaml.safe_load(open(path)))
    ss = load_sample_set(path)
    rng = random.Random(5)
    for t in ss.templates[:limit]:
        out = t.render(rng, NOW)
        assert out.strip() not in cfg, "configuration text emitted as telemetry in %s: %r" % (path, out[:80])


def test_no_configuration_value_is_ever_emitted_shipped_corpus():
    for path in SHIPPED:
        _no_leak(path)


def test_no_configuration_value_is_emitted_external_corpus_bounded():
    files = sorted(f for f in glob.glob(str(ROOT / "samples/*/*.yml")) if Path(f).stat().st_size < 1_000_000)[::7]
    if not files:
        pytest.skip("external samples/ corpus not present")
    checked = 0
    for path in files:
        if validate_sample_file(path, limit=50)["status"] != "REPLAYABLE":
            continue
        _no_leak(path, limit=50)
        checked += 1
    assert checked >= 20
