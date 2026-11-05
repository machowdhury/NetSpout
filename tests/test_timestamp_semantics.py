"""Timestamp semantics per integration (docs/contracts/timestamp_semantics.md)."""
import glob
import random
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src")]
from netspout_core import telemetry_dispatcher as td  # noqa: E402
from netspout_core.models import LogEntry, TelemetryTransportConfig  # noqa: E402
from netspout_core.yaml_sample_replay import load_sample_set  # noqa: E402

NOW = datetime(2026, 11, 3, 14, 5, 9, tzinfo=timezone.utc)
# a sample that renders a timestamp token and also holds a literal timestamp, with the reason it is left as is
ALLOWED = {"cisco-dc-aci-class": "ACI class sample: the literal timestamp is a field of the recorded object, not an event time"}
LITERAL = re.compile(r"\b20\d\d [A-Z][a-z]{2} +\d+ \d\d:\d\d:\d\d|\b[A-Z][a-z]{2} +\d+ +20\d\d \d\d:\d\d:\d\d|\b20\d\d-\d\d-\d\dT\d\d:\d\d:\d\d")


def test_hec_event_time_is_the_send_time_and_the_raw_text_is_unchanged(monkeypatch):
    """Product path: HEC JSON event. _time is the HEC `time` (send time), never parsed from the event text; the text keeps its own timestamp byte for byte."""
    sent = []
    monkeypatch.setattr(td.dispatcher, "emit_hec", lambda ev, *a, **k: (sent.append(ev), td.HecOutcome(True, "ok", td.HEC_ACCEPTED, 200, None))[1])
    raw = "Jan  2 03:04:05 fw %ASA-6-302013: Built outbound TCP connection 1"          # text claims an old time
    le = LogEntry(timestamp="2020-01-02 03:04:05.000 UTC", device_id="fw", src_ip="1.1.1.1", dest_ip="2.2.2.2", protocol="TCP", duration="0ms", action="a", signature="s", status="ok",
                  raw_log=raw, node_type="firewall", node_id="fw", vendor="v", sourcetype="cisco:asa")
    import time
    t0 = time.time()
    td.dispatcher.dispatch_log(le, TelemetryTransportConfig(hec_url="https://127.0.0.1:8088/services/collector", hec_token="t", hec_index="i"))
    assert isinstance(sent[0]["time"], float) and t0 - 1 <= sent[0]["time"] <= time.time() + 1
    assert sent[0]["event"] == raw


def test_rendered_sample_timestamps_use_utc_and_the_given_clock():
    ss = load_sample_set(str(ROOT / "netspout/appserver/static/samples/cisco-asa/cisco-asa.yml"))
    for raw in ss.render_all(random.Random(1), NOW):
        assert raw.startswith("Nov 03 14:05:09 ")        # rendered from the supplied UTC clock, no year (as ASA syslog)


def test_cisco_ios_sample_renders_one_consistent_time():
    ss = load_sample_set(str(ROOT / "netspout/appserver/static/samples/cisco-ios/cisco-ios.yml"))
    for raw in ss.render_all(random.Random(1), NOW):
        head = re.match(r"^([A-Z][a-z]{2} \d\d \d\d:\d\d:\d\d) ", raw).group(1)
        dev = re.search(r": (\d{4}) ([A-Z][a-z]{2} \d\d \d\d:\d\d:\d\d) UTC: %", raw)
        assert dev and dev.group(2) == head and dev.group(1) == "2026", raw       # the header time and the device time agree


def test_no_shipped_sample_mixes_a_rendered_timestamp_with_a_stale_literal_one():
    bad = []
    for f in sorted(glob.glob(str(ROOT / "netspout/appserver/static/samples/*/*.yml"))):
        ss = load_sample_set(f)
        for t in ss.templates:
            has_tok = any(("$%s$" % k.name) in t.raw and k.type in ("gotimestamp", "timestamp", "epochtimestamp", "javatimestamp") for k in t.tokens)
            if has_tok and LITERAL.search(re.sub(r"\$[A-Za-z_]+\$", "", t.raw)) and Path(f).parent.name not in ALLOWED:
                bad.append(Path(f).parent.name)
    assert not bad, sorted(set(bad))
