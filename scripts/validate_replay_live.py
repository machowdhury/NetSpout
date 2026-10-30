#!/usr/bin/env python3
"""Continuous sample replay validated against the ISOLATED validation lab only (tests/lab/ta_validation; credentials from git-ignored .env.lab, never printed).

Every number below is read back from Splunk by an independent search, not taken from sender counters. The index `dev_test_replay` is the replay
default; it is created ONLY in this isolated lab as a test fixture (the product never creates indexes). Evidence: docs/verification/evidence/replay/replay_live.json
Usage: PYTHONPATH=src python scripts/validate_replay_live.py
"""
import json
import re
import sys
import time
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
import validate_ta_windows as lab  # noqa: E402  (lab helpers: mgmt/search; reads .env.lab on import)
from netspout_core.replay_service import resolve  # noqa: E402
from netspout_core.sample_replay import HecSink, ReplayError, ReplaySession, build_timeline, TimestampRule  # noqa: E402

INDEX, HOST = "dev_test_replay", "replayed-log-generator"
URL = "https://127.0.0.1:%s/services/collector" % lab.ENV["LAB_HEC_PORT"]
results, failures = {}, []


def check(name, ok, **detail):
    results[name] = {"pass": bool(ok), **detail}
    if not ok:
        failures.append(name)
    print(("PASS " if ok else "FAIL ") + name)


class Recording:
    """Wraps the real HecSink; records what was sent and when so rates and stamps can be compared with Splunk's view."""

    def __init__(self, sink, delay=0.0):
        self.sink, self.delay, self.sent = sink, delay, []

    def send(self, raw, when, meta=None):
        time.sleep(self.delay)
        outcome = self.sink.send(raw, when, meta)
        self.sent.append((raw, when, time.monotonic(), outcome))
        return outcome


def session(source_id, token=None, delay=0.0, **kw):
    text, fmt, rule, sourcetype, label, rs = resolve({"source_id": source_id})
    tl = build_timeline(text, fmt, rule, record_start=rs, loop_gap_s=kw.pop("loop_gap_s", None), max_gap_s=kw.pop("max_gap_s", None))
    sink = Recording(HecSink(URL, token or lab.ENV["LAB_HEC_TOKEN"], INDEX, HOST, "placeholder", sourcetype, False, True), delay)
    s = ReplaySession(tl, sink, source_label=label, sourcetype=sourcetype, index=INDEX, host=HOST, **kw)
    sink.sink._m["source"] = s.source
    return s, sink, tl


def indexed(sid, wait_for=None, timeout=45):
    rows = []
    for _ in range(timeout // 3):
        rows = lab.search('search index=* netspout_replay_session="%s" | eval t=_time, it=_indextime | table index host source sourcetype t it _raw | sort 0 t' % sid, earliest="-2h")
        if wait_for is None or len(rows) >= wait_for:
            break
        time.sleep(3)
    return rows


def main():
    if INDEX not in [e["name"] for e in json.loads(lab.mgmt("/services/data/indexes?output_mode=json&count=0"))["entry"]]:
        lab.mgmt("/services/data/indexes", {"name": INDEX, "datatype": "event"})  # isolated lab fixture only
        results["fixture"] = "created index %s in the isolated validation lab" % INDEX
    info = json.loads(lab.mgmt("/services/server/info?output_mode=json"))["entry"][0]["content"]

    # A. timestamp transformation, spacing, current clock, loop boundary, isolation, byte fidelity
    t0 = datetime.now(timezone.utc)
    s, sink, tl = session("aws_cloudtrail", speed=5, loops=2, loop_gap_s=5)
    s.start(); s.wait(60)
    rows = indexed(s.id, 24)
    sent = [x[1].timestamp() for x in sink.sent]
    ts = [float(r["t"]) for r in rows]
    check("A1_hec_accepts_every_event", s.counts["accepted"] == 24 == s.counts["delivered"] and not s.counts["rejected"], counts=s.counts)
    check("A2_independent_search_count_equals_accepted", len(rows) == 24, indexed=len(rows))
    check("A3_isolation_index_host_source", {r["index"] for r in rows} == {INDEX} and {r["host"] for r in rows} == {HOST} and {r["source"] for r in rows} == {s.source},
          index=INDEX, host=HOST)
    check("A4_timestamps_are_on_the_current_clock", all(t0.timestamp() - 3 <= t <= time.time() + 3 for t in ts), earliest=min(ts) - t0.timestamp(), latest=max(ts) - t0.timestamp())
    expected = [(tl.items[i].offset if k == 0 else tl.period_s + tl.items[i].offset) / 5 for k in (0, 1) for i in range(12)]
    gaps_idx = [round(b - a, 3) for a, b in zip(ts, ts[1:])]
    gaps_exp = [round(b - a, 3) for a, b in zip(expected, expected[1:])]
    check("A5_relative_spacing_preserved_in_splunk_time", all(abs(a - b) < 0.05 for a, b in zip(gaps_idx, gaps_exp)), max_error_s=max(abs(a - b) for a, b in zip(gaps_idx, gaps_exp)))
    boundary = ts[12] - ts[11]
    check("A6_loop_boundary_monotonic_gap_is_the_documented_loop_gap", abs(boundary - 5 / 5) < 0.05 and all(b > a for a, b in zip(ts, ts[1:])), boundary_gap_s=round(boundary, 3), expected_s=1.0)
    originals = {i.record for i in tl.items}
    stripped = lambda r: re.sub(r'"eventTime":"[^"]+"', '"eventTime":"X"', r)
    check("A7_everything_but_the_timestamp_is_byte_identical", {stripped(r["_raw"]) for r in rows} == {stripped(o) for o in originals} and
          all(r["_raw"] not in originals for r in rows), distinct_records=len({r['_raw'] for r in rows}))
    check("A8_no_leak_to_other_indexes", {r["index"] for r in lab.search('search index=* netspout_replay_session="%s" | table index' % s.id, earliest="-2h")} == {INDEX})

    # B. continuous replay with pause / resume / stop
    s, sink, tl = session("suricata_eve", speed=20, loops=None, loop_gap_s=2)
    s.start(); time.sleep(2.5)
    s.pause(); paused_at = time.time(); time.sleep(0.5)
    n_pause = s.counts["accepted"]
    time.sleep(3)
    r1 = indexed(s.id)
    check("B1_pause_stops_delivery", s.counts["accepted"] == n_pause and s.state == "PAUSED" and len(r1) == n_pause and max(float(r["it"]) for r in r1) <= paused_at + 1.5,
          accepted_during_pause=s.counts["accepted"] - n_pause, indexed=len(r1))
    s.resume(); time.sleep(2.5)
    s.stop()
    final = indexed(s.id, s.counts["accepted"])
    ts = [float(r["t"]) for r in final]
    check("B2_resume_continues_and_stop_halts", s.state == "STOPPED" and s.counts["accepted"] > n_pause, accepted=s.counts["accepted"], before_pause=n_pause)
    check("B3_continuous_loops_more_than_once", s.counts["generated"] > len(tl.items), generated=s.counts["generated"], records=len(tl.items))
    check("B4_stop_accounting_matches_splunk", len(final) == s.counts["accepted"] and not s.counts["rejected"], indexed=len(final), counts=s.counts)
    check("B5_stamps_never_go_backwards_across_pause_and_loops", all(b >= a for a, b in zip(ts, ts[1:])), note="equal stamps occur where the source itself has equal timestamps")
    time.sleep(3)
    check("B6_nothing_arrives_after_stop", len(indexed(s.id)) == len(final))

    # C. EPS throttle
    s, sink, _ = session("sysmon_linux_xml", speed=1000, loops=1, eps_limit=15)
    s.start(); s.wait(60)
    t = [x[2] for x in sink.sent]
    rate = (len(t) - 1) / (t[-1] - t[0])
    rows = indexed(s.id, len(t))
    check("C1_eps_limit_respected", rate <= 15 * 1.1 and len(t) == 129, observed_eps=round(rate, 2), limit=15)
    check("C2_all_throttled_events_indexed", len(rows) == s.counts["accepted"] == 129, indexed=len(rows))

    # D. backpressure: slow consumer, tiny queue, nothing dropped
    s, sink, _ = session("aws_cloudtrail", delay=0.05, speed=1000, loops=3, queue_size=2)
    s.start(); s.wait(60)
    rows = indexed(s.id, 36)
    check("D1_backpressure_blocks_producer_without_loss", s.counts["backpressure_waits"] > 0 and s.counts["generated"] == s.counts["delivered"] == 36 == len(rows), counts=s.counts, indexed=len(rows))

    # E. wrong token: HEC rejections are counted as rejected and nothing is indexed
    s, sink, _ = session("aws_cloudtrail", token="00000000-0000-0000-0000-000000000000", speed=1000, loops=1)
    s.start(); s.wait(30)
    time.sleep(3)
    check("E1_rejected_events_counted_and_not_indexed", s.counts["rejected"] == s.counts["delivered"] == 12 and s.counts["accepted"] == 0 and not indexed(s.id, None, 6), counts=s.counts)

    # F. a source with no trustworthy timestamp is refused
    try:
        build_timeline("a\nb\n", "text", None)
        check("F1_no_timestamp_source_refused", False)
    except ReplayError as exc:
        check("F1_no_timestamp_source_refused", "refusing to invent" in str(exc))

    # G. scenario packs: replay phases + native phases, phase/run tagging as indexed fields, ordering, cycles
    from netspout_core import replay_packs
    pack_ok, panels_ok = [], []
    for pid, loops in [(p["id"], 1) for p in replay_packs.packs()]:
        tl = replay_packs.build_pack_timeline(pid, cycle_gap_s=2)
        sink = Recording(HecSink(URL, lab.ENV["LAB_HEC_TOKEN"], INDEX, HOST, "placeholder", "x", False, True))
        s = ReplaySession(tl, sink, source_label=pid, sourcetype="(per event)", index=INDEX, host=HOST, speed=50, loops=loops)
        sink.sink._m["source"] = s.source
        s.start(); s.wait(120)
        rows = indexed(s.id, len(tl.items))
        by_phase = lab.search('search index=%s netspout_replay_session="%s" | stats count min(_time) as first max(_time) as last by netspout_phase' % (INDEX, s.id), earliest="-2h")
        expected_by_phase = {}
        for it in tl.items:
            expected_by_phase[it.fields["netspout_phase"]] = expected_by_phase.get(it.fields["netspout_phase"], 0) + 1
        got = {r["netspout_phase"]: int(r["count"]) for r in by_phase}
        order = [r["netspout_phase"] for r in sorted(by_phase, key=lambda r: float(r["first"]))]
        check("G1_%s_every_event_indexed_and_counted_per_phase" % pid, len(rows) == len(tl.items) == s.counts["accepted"] and got == expected_by_phase, expected=expected_by_phase, indexed=got)
        check("G2_%s_phase_order_in_splunk_time" % pid, order == [ph["id"] for ph in replay_packs.get(pid)["phases"]], order=order)
        run_ids = lab.search('search index=%s netspout_replay_session="%s" | stats dc(netspout_run_id) as runs, values(netspout_scenario_id) as scn, dc(sourcetype) as sourcetypes' % (INDEX, s.id), earliest="-2h")
        check("G3_%s_single_run_id_and_scenario_tag" % pid, run_ids and run_ids[0]["runs"] == "1" and run_ids[0]["scn"] == pid, sourcetypes=run_ids[0].get("sourcetypes") if run_ids else None)
        pk = replay_packs.get(pid)
        if pk.get("required_sourcetypes"):
            sts = lab.search('search index=%s netspout_replay_session="%s" | stats values(sourcetype) as st' % (INDEX, s.id), earliest="-2h")
            got_st = sorted(sts[0]["st"] if sts and isinstance(sts[0]["st"], list) else [sts[0]["st"]] if sts else [])
            # The Windows add-on installed in this lab rewrites sourcetype XmlWinEventLog:<channel> to XmlWinEventLog (and source to the channel) at index time.
            want = sorted({"XmlWinEventLog" if st.startswith("XmlWinEventLog:") else st for st in pk["required_sourcetypes"]})
            check("G5_%s_required_sourcetypes_all_present" % pid, got_st == want, expected=pk["required_sourcetypes"], indexed=got_st,
                  note="XmlWinEventLog:<channel> is indexed as XmlWinEventLog by the installed Windows add-on" if want != sorted(pk["required_sourcetypes"]) else None)
        if pk.get("dashboard_panels"):
            empty = [pn["title"] for pn in pk["dashboard_panels"] if not lab.search("search " + pn["spl"].replace("{session}", s.id), earliest="-2h")]
            check("H1_%s_dashboard_panel_queries_populated" % pid, not empty, empty_panels=empty)
            if not empty:
                panels_ok.append(pid)
        if all(results["G%d_%s_%s" % (n, pid, suffix)]["pass"] for n, suffix in ((1, "every_event_indexed_and_counted_per_phase"), (2, "phase_order_in_splunk_time"), (3, "single_run_id_and_scenario_tag"))):
            pack_ok.append(pid)
    tl = replay_packs.build_pack_timeline("rp_cloud_control_plane_activity", cycle_gap_s=1)
    sink = Recording(HecSink(URL, lab.ENV["LAB_HEC_TOKEN"], INDEX, HOST, "placeholder", "x", False, True))
    s = ReplaySession(tl, sink, source_label="rp_cloud_control_plane_activity", sourcetype="(per event)", index=INDEX, host=HOST, speed=10, loops=None)
    sink.sink._m["source"] = s.source
    s.start(); time.sleep(6); s.stop()
    indexed(s.id, s.counts["accepted"])   # wait until Splunk has everything that was accepted
    cyc = lab.search('search index=%s netspout_replay_session="%s" | stats count by netspout_cycle | sort 0 netspout_cycle' % (INDEX, s.id), earliest="-2h")
    check("G4_continuous_pack_repeats_incident_cycles", len(cyc) >= 2 and sum(int(c["count"]) for c in cyc) == s.counts["accepted"], cycles={c["netspout_cycle"]: c["count"] for c in cyc})

    doc = {"generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"), "lab": "tests/lab/ta_validation (isolated)", "splunk_version": info["version"],
           "index": INDEX, "host": HOST, "ta_cim_detection_validated": False, "passed": sum(v["pass"] for k, v in results.items() if isinstance(v, dict)),
           "failed": failures, "packs_indexed_verified": pack_ok, "packs_panels_populated": panels_ok, "checks": results}
    out = ROOT / "docs/verification/evidence/replay/replay_live.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, indent=1, default=str) + "\n")
    print(json.dumps({"splunk": info["version"], "passed": doc["passed"], "failed": failures}))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
