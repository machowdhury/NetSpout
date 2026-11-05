"""scripts/ta_compat.py and the TA-safe HEC payload. The tool must fail on a wrong add-on, a payload the add-on would not claim and a missing stanza."""
import io
import json
import sys
import tarfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
import ta_compat  # noqa: E402
from netspout_core import telemetry_dispatcher as td  # noqa: E402
from netspout_core.models import LogEntry, TelemetryTransportConfig  # noqa: E402

SPEC = json.loads((ROOT / "tests/ta_specs/cisco_asa.json").read_text())
PACKS = Path("~/netspout/private-packs").expanduser()


def _ta(tmp_path, props, transforms, eventtypes="", tags="", version="1.0.0"):
    p = tmp_path / "ta.tgz"
    files = {"default/app.conf": "[launcher]\nversion = %s\n[id]\nname = T\n" % version, "default/props.conf": props, "default/transforms.conf": transforms,
             "default/eventtypes.conf": eventtypes, "default/tags.conf": tags}
    with tarfile.open(p, "w:gz") as tf:
        for n, c in files.items():
            b = c.encode()
            ti = tarfile.TarInfo("T/" + n); ti.size = len(b); tf.addfile(ti, io.BytesIO(b))
    return ta_compat.TA(str(p))


def _spec():
    return {"ta": {"expected_version": "1.0.0"}, "sourcetype": "v:p", "events": [{"id": "e1", "raw": "{TS} {HOST} %V-6-100001: hello", "eventtype": "et", "tags": ["network"], "expect": {"message_id": "100001"}}],
            "negative": [{"id": "n1", "raw": "{TS} {HOST} plain text", "expect_no_force_match": True}]}


GOOD_PROPS = "[v:p]\nTIME_PREFIX = ^\nTIME_FORMAT = %b %d %H:%M:%S\nMAX_TIMESTAMP_LOOKAHEAD = 30\nREPORT-x = t_report\n"
GOOD_TRANS = "[force_v]\nDEST_KEY = MetaData:Sourcetype\nREGEX = %V-\\d-\\d{6}\nFORMAT = sourcetype::v:p\n[t_report]\nREGEX = %V-(?<lvl>\\d)-(?<message_id>\\d{6})\n"
GOOD_ET = '[et]\nsearch = (sourcetype="v:p") message_id IN ("100001")\n'
GOOD_TAGS = "[eventtype=et]\nnetwork = enabled\n"


def _run(ta, spec):
    rep = ta_compat.Report()
    ta_compat.offline(spec, ta, rep)
    return {r["check"]: r["status"] for r in rep.rows}


def test_conf_parser_joins_continuation_lines():
    c = ta_compat.parse_conf("[s]\na = one, \\\n  two\nb = 2\n# c\n")
    assert c == {"s": {"a": "one, two", "b": "2"}}


def test_synthetic_ta_passes_offline(tmp_path):
    res = _run(_ta(tmp_path, GOOD_PROPS, GOOD_TRANS, GOOD_ET, GOOD_TAGS), _spec())
    assert res and set(res.values()) == {"PASS"}, res


def test_wrong_sourcetype_stanza_fails(tmp_path):
    res = _run(_ta(tmp_path, GOOD_PROPS.replace("[v:p]", "[other:thing]"), GOOD_TRANS, GOOD_ET, GOOD_TAGS), _spec())
    assert res["props.sourcetype_stanza"] == "FAIL"


def test_force_regex_claiming_a_negative_payload_fails(tmp_path):
    res = _run(_ta(tmp_path, GOOD_PROPS, GOOD_TRANS.replace("%V-\\d-\\d{6}", ".*"), GOOD_ET, GOOD_TAGS), _spec())
    assert res["force_sourcetype.rejects[n1]"] == "FAIL"


def test_event_not_matching_the_force_regex_fails(tmp_path):
    res = _run(_ta(tmp_path, GOOD_PROPS, GOOD_TRANS.replace("%V-", "%NOPE-"), GOOD_ET, GOOD_TAGS), _spec())
    assert res["force_sourcetype.assigns_expected[e1]"] == "FAIL"


def test_unparseable_timestamp_format_fails(tmp_path):
    res = _run(_ta(tmp_path, GOOD_PROPS.replace("%b %d %H:%M:%S", "%Y/%m/%d"), GOOD_TRANS, GOOD_ET, GOOD_TAGS), _spec())
    assert res["timestamp.format_parses[e1]"] == "FAIL"


def test_eventtype_that_does_not_cover_the_message_id_fails(tmp_path):
    res = _run(_ta(tmp_path, GOOD_PROPS, GOOD_TRANS, GOOD_ET.replace("100001", "999999"), GOOD_TAGS), _spec())
    assert res["eventtype.defined_and_covers[e1]"] == "FAIL"


def test_missing_report_transform_fails(tmp_path):
    res = _run(_ta(tmp_path, GOOD_PROPS, GOOD_TRANS.replace("[t_report]", "[renamed]"), GOOD_ET, GOOD_TAGS), _spec())
    assert res["props.report_transforms_exist"] == "FAIL"


def test_expected_field_the_add_on_does_not_define_fails(tmp_path):
    spec = _spec()
    spec["events"][0]["expect"]["made_up_field"] = "x"
    res = _run(_ta(tmp_path, GOOD_PROPS, GOOD_TRANS, GOOD_ET, GOOD_TAGS), spec)
    assert res["ta_defines_field[e1.made_up_field]"] == "FAIL" and res["ta_defines_field[e1.message_id]"] == "PASS"


def test_missing_time_format_is_not_run_not_pass(tmp_path):
    res = _run(_ta(tmp_path, "[v:p]\nREPORT-x = t_report\n", GOOD_TRANS, GOOD_ET, GOOD_TAGS), _spec())
    assert res["timestamp.format_parses[e1]"] == "NOT_RUN"


def test_version_mismatch_fails(tmp_path):
    assert _run(_ta(tmp_path, GOOD_PROPS, GOOD_TRANS, GOOD_ET, GOOD_TAGS, version="9.9"), _spec())["ta.version"] == "FAIL"


def test_missing_package_is_not_run_not_pass(tmp_path, capsys):
    spec = tmp_path / "s.json"
    s = _spec(); s["ta"]["package_glob"] = "nothing-*.spl"
    spec.write_text(json.dumps(s))
    assert ta_compat.main([str(spec), "--packs", str(tmp_path)]) == 2
    assert "NOT_RUN" in capsys.readouterr().out


@pytest.mark.skipif(not list(PACKS.glob(SPEC["ta"]["package_glob"])), reason="Cisco ASA add-on package not present (never committed)")
def test_real_cisco_asa_package_offline_checks_pass():
    ta = ta_compat.TA(str(sorted(PACKS.glob(SPEC["ta"]["package_glob"]))[-1]))
    res = _run(ta, SPEC)
    assert ta.version == "6.1.2" and set(res.values()) == {"PASS"}, {k: v for k, v in res.items() if v != "PASS"}
