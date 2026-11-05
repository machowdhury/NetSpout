"""Field ownership: vendor/CIM fields belong to the vendor payload and the Splunk add-on; NetSpout metadata is namespaced. TA_PARSED_SOURCETYPES is derived from live evidence."""
import glob
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src")]
from netspout_core import telemetry_dispatcher as td  # noqa: E402
from netspout_core.models import LogEntry, TelemetryTransportConfig  # noqa: E402

LIVE = json.loads((ROOT / "docs/contracts/ta_live_results.json").read_text())


def _fields(sourcetype, monkeypatch, raw="Nov  3 10:00:00 fw %ASA-6-302013: x"):
    sent = []
    monkeypatch.setattr(td.dispatcher, "emit_hec", lambda ev, *a, **k: (sent.append(ev), td.HecOutcome(True, "ok", td.HEC_ACCEPTED, 200, None))[1])
    le = LogEntry(timestamp="", device_id="fw", src_ip="192.0.2.1", dest_ip="192.0.2.2", protocol="TCP", duration="0ms", action="streamed", signature="SIG", status="normal", raw_log=raw,
                  node_type="firewall", node_id="fw", vendor="v", sourcetype=sourcetype, netspout_run_id="r1", netspout_scenario_id="s1")
    td.dispatcher.dispatch_log(le, TelemetryTransportConfig(hec_url="https://127.0.0.1:8088/services/collector", hec_token="t", hec_index="i"))
    return sent[0]["fields"], sent[0]


def test_verified_sourcetypes_carry_no_bare_netspout_fields(monkeypatch):
    for st in td.TA_PARSED_SOURCETYPES:
        f, _ = _fields(st, monkeypatch)
        for k in td.NETSPOUT_NAMESPACED_FIELDS:
            assert k not in f, (st, k)
            assert f["netspout_" + k] is not None, (st, k)
        assert f["netspout_run_id"] == "r1" and f["netspout_scenario_id"] == "s1"      # correlation preserved


def test_other_sourcetypes_keep_bare_fields_and_gain_namespaced_copies(monkeypatch):
    f, _ = _fields("some:other:sourcetype", monkeypatch)
    for k in td.NETSPOUT_NAMESPACED_FIELDS:
        assert f[k] == f["netspout_" + k]


def test_raw_event_and_sourcetype_are_never_modified(monkeypatch):
    raw = "Nov  3 10:00:00 fw %ASA-6-302013: Built outbound TCP connection 1"
    for st in ("cisco:asa", "some:other"):
        _, ev = _fields(st, monkeypatch, raw=raw)
        assert ev["event"] == raw and ev["sourcetype"] == st


def test_metric_payload_is_untouched_by_the_policy(monkeypatch):
    sent = []
    monkeypatch.setattr(td.dispatcher, "emit_hec", lambda ev, *a, **k: (sent.append(ev), td.HecOutcome(True, "ok", td.HEC_ACCEPTED, 200, None))[1])
    le = LogEntry(timestamp="", device_id="r1", src_ip="1.1.1.1", dest_ip="2.2.2.2", protocol="gNMI", duration="0ms", action="allowed", signature="m", status="normal",
                  raw_log=json.dumps({"data": {"in_octets": 5}}), node_type="router", node_id="r1", vendor="cisco_ios", sourcetype="cisco:ios:mdt:metric")
    td.dispatcher.dispatch_log(le, TelemetryTransportConfig(hec_url="https://127.0.0.1:8088/services/collector", hec_token="t", hec_index="i", hec_metric_index="m"))
    ev = sent[0]
    assert ev["event"] == "metric" and ev["fields"]["metric_name:in_octets"] == 5.0 and not any(k.startswith("netspout_action") for k in ev["fields"])


def test_ta_parsed_sourcetypes_equal_the_live_evidence():
    passed = {st for st, r in LIVE.items() if r["passed"]}
    assert td.TA_PARSED_SOURCETYPES == passed
    for st, r in LIVE.items():
        assert (ROOT / r["evidence"]).is_file() and (ROOT / r["spec"]).is_file()
        ev = json.loads((ROOT / r["evidence"]).read_text())
        assert ev["summary"]["FAIL"] == 0 if r["passed"] else True


def test_phase_story_panels_read_namespaced_fields_with_fallback():
    """The three searches that read NetSpout's own status/action/signature use coalesce(netspout_x, x) in every contract dashboard (so TA-owned events still appear)."""
    n = 0
    for f in glob.glob(str(ROOT / "netspout/default/data/ui/views/pf_*.xml")):
        t = open(f).read()
        m = re.search(r"<definition><!\[CDATA\[(.*?)\]\]></definition>", t, re.S)
        if not m:
            continue
        for x in json.loads(m.group(1))["dataSources"].values():
            q = x.get("options", {}).get("query", "")
            if "by pf_ord, pf_phase, pf_host" in q or "chart count over step by pf_status" in q:
                n += 1
                assert "coalesce(netspout_status, status)" in q or "coalesce(netspout_action, action)" in q, f
            assert "chart count over step by status" not in q and "pf_host, action, signature" not in q, f
    assert n >= 440
