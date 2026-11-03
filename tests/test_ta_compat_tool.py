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
GOOD_TRANS = "[force_v]\nDEST_KEY = MetaData:Sourcetype\nREGEX = %V-\\d-\\d{6}\nFORMAT = sourcetype::v:p\n[t_report]\nREGEX = %V-(?<lvl>\\d)\n"
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
    assert res["force_sourcetype.matches[e1]"] == "FAIL"


def test_unparseable_timestamp_format_fails(tmp_path):
    res = _run(_ta(tmp_path, GOOD_PROPS.replace("%b %d %H:%M:%S", "%Y/%m/%d"), GOOD_TRANS, GOOD_ET, GOOD_TAGS), _spec())
    assert res["timestamp.format_parses[e1]"] == "FAIL"


def test_eventtype_that_does_not_cover_the_message_id_fails(tmp_path):
    res = _run(_ta(tmp_path, GOOD_PROPS, GOOD_TRANS, GOOD_ET.replace("100001", "999999"), GOOD_TAGS), _spec())
    assert res["eventtype.covers_message_id[e1]"] == "FAIL"


def test_missing_report_transform_fails(tmp_path):
    res = _run(_ta(tmp_path, GOOD_PROPS, GOOD_TRANS.replace("[t_report]", "[renamed]"), GOOD_ET, GOOD_TAGS), _spec())
    assert res["props.report_transforms_exist"] == "FAIL"


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


# ------------------------------------------------------------ TA-safe payload
def _payload(sourcetype, monkeypatch):
    sent = []
    monkeypatch.setattr(td.dispatcher, "emit_hec", lambda ev, *a, **k: (sent.append(ev), td.HecOutcome(True, "ok", td.HEC_ACCEPTED, 200, None))[1])
    le = LogEntry(timestamp="", device_id="fw", src_ip="192.0.2.1", dest_ip="192.0.2.2", protocol="TCP", duration="0ms", action="streamed", signature="SIG", status="normal",
                  raw_log="Nov  3 10:00:00 fw %ASA-6-302013: x", node_type="firewall", node_id="fw", vendor="v", sourcetype=sourcetype, netspout_run_id="r1")
    td.dispatcher.dispatch_log(le, TelemetryTransportConfig(hec_url="https://127.0.0.1:8088/services/collector", hec_token="t", hec_index="i"))
    return sent[0]["fields"]


def test_ta_parsed_sourcetype_does_not_shadow_add_on_fields(monkeypatch):
    f = _payload("cisco:asa", monkeypatch)
    for k in td.TA_SHADOWED_FIELDS:
        assert k not in f and f["netspout_" + k] is not None, k
    assert f["status"] == "normal" and f["netspout_run_id"] == "r1"     # dashboards keep `status`; run id untouched


def test_other_sourcetypes_keep_their_fields(monkeypatch):
    f = _payload("cisco:ios", monkeypatch)
    assert f["action"] == "streamed" and f["src_ip"] == "192.0.2.1" and "netspout_action" not in f


def test_ta_parsed_sourcetypes_match_the_registry():
    reg = json.loads((ROOT / "docs/contracts/ta_compatibility_registry.json").read_text())
    verified = {e["canonical_sourcetype"] for e in reg["entries"] if e["verification"].get("ta_parsing_in_splunk", {}).get("status") == "VERIFIED"}
    assert td.TA_PARSED_SOURCETYPES == verified
