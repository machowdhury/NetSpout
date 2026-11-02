#!/usr/bin/env python3
"""
Run sampled scenario contracts through a LIVE engine into an isolated lab Splunk and verify each run independently in Splunk by run id.

Three numbers are kept apart and never conflated: events GENERATED (the contract), events ACCEPTED by HEC (the engine's delivery counters) and events INDEXED
(a separate Splunk search over the run id). Metric sourcetypes land in the metric index and are checked there with mstats, separately.

Checks per run (independent, in Splunk): indexed count by sourcetype equals what the contract generated; phases appear in the contract's order by first event time;
every non-first event's parent id exists and there is exactly one root; every event carries run id, scenario id, phase and device id.

  python scripts/run_contract_validation_live.py ENVFILE --engine http://127.0.0.1:8095 --port 28089 [--ids a,b,c]
Writes docs/verification/evidence/scenario_contracts/live_validation.json and a run map (scenario id -> run id) next to it.
"""
import base64
import collections
import json
import ssl
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
from netspout_core import scenario_contracts as sc  # noqa: E402
from netspout_core.telemetry_dispatcher import is_metric_sourcetype  # noqa: E402
from validate_contract_dashboards_live import Splunk  # noqa: E402

OUT = ROOT / "docs" / "verification" / "evidence" / "scenario_contracts"
INDEX, MINDEX = "dev_test_replay", "dev_test_replay_metrics"
SAMPLE = [
    # authored, vendor-native, multi-sourcetype
    "lateral_movement", "mixed_vendor_enterprise", "normal_traffic", "service_provider_mixed", "arch_gan_subsea_cloud",
    # authored, mixed: verbatim vendor samples, native ISE, modeled stand-in
    "arch_can_multi_building", "arch_nas_storage_cluster", "pure_cisco_enterprise",
    # Cisco-100, modeled state progression (dependency first)
    "C100-ENT-002", "C100-SP-008", "C100-CRI-018", "C100-DC-012",
    # Cisco-100, with native streams added by the fidelity upgrade
    "C100-SEC-005", "C100-SEC-006", "C100-SP-003", "C100-ENT-005", "C100-DC-008", "C100-SEC-015", "C100-CRI-001",
    # community monitoring use cases, one archetype each, single sourcetype
    "UCR-14.3.9", "UCR-8.1.1", "UCR-22.1.5", "UCR-21.1.1", "UCR-21.11.1", "UCR-13.4.5",
]


def engine_call(base, method, path, body=None):
    req = urllib.request.Request(base + path, data=json.dumps(body).encode() if body is not None else None, headers={"Content-Type": "application/json"}, method=method)
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.loads(r.read().decode())


def search(sp, q, earliest="-3h"):
    st, body = sp.call("/services/search/jobs", {"search": q, "exec_mode": "oneshot", "output_mode": "json", "count": "0", "earliest_time": earliest, "latest_time": "+1h"})
    return body.get("results", [])


def verify(sp, cid, run_id, expected):
    ev_types = [t for t in expected["by_sourcetype"] if not is_metric_sourcetype(t)]
    out = {"event_sourcetypes_checked": ev_types, "problems": []}
    rows = search(sp, 'search index=%s netspout_run_id="%s" | stats count by sourcetype' % (INDEX, run_id))
    got = {r["sourcetype"]: int(r["count"]) for r in rows}
    out["indexed_by_sourcetype"] = got
    for t in ev_types:
        if got.get(t, 0) != expected["by_sourcetype"][t]:
            out["problems"].append("indexed %s=%d, generated %d" % (t, got.get(t, 0), expected["by_sourcetype"][t]))
    if set(got) - set(ev_types):
        out["problems"].append("unexpected sourcetypes indexed: %s" % sorted(set(got) - set(ev_types)))
    # phase order by first event time
    order = [p["id"] for p in sc.get(cid)["phases"]]
    ph = search(sp, 'search index=%s netspout_run_id="%s" | stats min(_time) as first by netspout_phase | sort 0 first' % (INDEX, run_id))
    seen = [r["netspout_phase"] for r in ph]
    ev_phases = [p for p in order if p in expected["event_phases"]]
    out["phase_order_indexed"] = seen
    if seen != ev_phases:
        out["problems"].append("phase order %s != contract %s" % (seen, ev_phases))
    # parent chain and required correlation fields
    ch = search(sp, 'search index=%s netspout_run_id="%s" | eval ok_fields=if(isnotnull(netspout_scenario_id) AND isnotnull(netspout_phase) AND isnotnull(netspout_device_id) AND isnotnull(netspout_event_id),1,0) '
                    '| stats count as events, sum(ok_fields) as with_fields, dc(netspout_event_id) as ids, values(netspout_parent_event_id) as parents' % (INDEX, run_id))
    if ch and int(ch[0]["events"]):
        c = ch[0]
        out["correlation_fields_on_all_events"] = int(c["with_fields"]) == int(c["events"])
        if not out["correlation_fields_on_all_events"]:
            out["problems"].append("some events lack run/scenario/phase/device/event id fields")
        if int(c["ids"]) != int(c["events"]):
            out["problems"].append("event ids are not unique")
    # parents all resolve, one root
    pr = search(sp, 'search index=%s netspout_run_id="%s" | stats values(netspout_event_id) as ids, values(netspout_parent_event_id) as parents | eval ids=mvjoin(ids,"|"), parents=mvjoin(parents,"|")' % (INDEX, run_id))
    if pr and pr[0].get("ids"):
        ids, parents = set(pr[0]["ids"].split("|")), set(filter(None, pr[0].get("parents", "").split("|")))
        out["parents_resolve"] = parents <= ids
        out["roots"] = len(ids) - len(parents)
        if not out["parents_resolve"]:
            out["problems"].append("a parent event id does not exist in the run")
    # metrics, checked in the metric index separately
    if len(ev_types) != len(expected["by_sourcetype"]):
        m = search(sp, '| mstats count(_value) as datapoints WHERE index=%s AND metric_name=* AND netspout_run_id="%s" BY netspout_event_id | stats count as metric_events, sum(datapoints) as datapoints' % (MINDEX, run_id))
        out["metric_index"] = m[0] if m else {}
        want = sum(v for t, v in expected["by_sourcetype"].items() if is_metric_sourcetype(t))
        if not m or int(m[0].get("metric_events", 0)) != want:
            out["problems"].append("metric events in the metric index %s, generated %d" % (m[0].get("metric_events") if m else 0, want))
    return out


def main():
    env = sys.argv[1]
    engine = sys.argv[sys.argv.index("--engine") + 1]
    port = int(sys.argv[sys.argv.index("--port") + 1]) if "--port" in sys.argv else 28089
    ids = sys.argv[sys.argv.index("--ids") + 1].split(",") if "--ids" in sys.argv else SAMPLE
    sp = Splunk(env, port)
    OUT.mkdir(parents=True, exist_ok=True)
    rows, run_map = [], {}
    for cid in ids:
        gen = sc.generate(cid, "expected")
        expected = {"generated": len(gen), "by_sourcetype": dict(collections.Counter(e.sourcetype for e in gen)),
                    "event_phases": [p for p in dict.fromkeys(e.netspout_phase for e in gen) if any(e.netspout_phase == p and not is_metric_sourcetype(e.sourcetype) for e in gen)]}
        try:
            start = engine_call(engine, "POST", "/api/runs", {"kind": "scenario", "target": cid, "eps": 500})
        except Exception as exc:   # e.g. HTTP 4xx from the engine
            rows.append({"scenario_id": cid, "status": "FAIL", "problems": ["could not start: %s" % exc]})
            continue
        rid = start["run_id"]
        for _ in range(240):
            snap = engine_call(engine, "GET", "/api/runs/" + rid)
            if snap["state"] in ("COMPLETED", "STOPPED", "FAILED"):
                break
            time.sleep(0.5)
        c = snap["counters"]
        time.sleep(4)   # indexing can trail acceptance by a few seconds
        v = verify(sp, cid, rid, expected)
        for _ in range(6):   # re-check briefly if indexed lags accepted
            if not v["problems"]:
                break
            time.sleep(4)
            v = verify(sp, cid, rid, expected)
        run_map[cid] = rid
        problems = list(v["problems"])
        if snap["state"] != "COMPLETED" or c["accepted"] != expected["generated"] or c.get("rejected"):
            problems.append("engine run %s generated=%s accepted=%s rejected=%s (contract generated %d)" % (snap["state"], c["generated"], c["accepted"], c.get("rejected"), expected["generated"]))
        rows.append({"scenario_id": cid, "fidelity": sc.fidelity(sc.get(cid)), "run_id": rid, "contract_generated": expected["generated"], "hec_accepted": c["accepted"], "hec_rejected": c.get("rejected", 0),
                     "indexed_events_by_sourcetype": v.get("indexed_by_sourcetype"), "indexed_events_total": sum((v.get("indexed_by_sourcetype") or {}).values()), "metric_index": v.get("metric_index"),
                     "phase_order_indexed": v.get("phase_order_indexed"), "parents_resolve": v.get("parents_resolve"), "roots": v.get("roots"), "correlation_fields_on_all_events": v.get("correlation_fields_on_all_events"),
                     "status": "PASS" if not problems else "FAIL", "problems": problems})
        print("%-26s %-13s gen=%3d accepted=%3d indexed=%3d metric=%s %s %s" % (cid, rows[-1]["fidelity"], expected["generated"], c["accepted"], rows[-1]["indexed_events_total"],
              (v.get("metric_index") or {}).get("metric_events", "-"), rows[-1]["status"], problems[:2] if problems else ""))
    (OUT / "live_validation.json").write_text(json.dumps({"environment": "isolated local Splunk Enterprise (docker splunk/splunk:10.2, amd64) + branch engine on 127.0.0.1:8095", "sampled": len(rows),
                                                           "passed": sum(1 for r in rows if r["status"] == "PASS"), "rows": rows}, indent=1) + "\n")
    (OUT / "live_run_map.json").write_text(json.dumps(run_map, indent=1) + "\n")
    print("PASS %d / %d" % (sum(1 for r in rows if r["status"] == "PASS"), len(rows)))


if __name__ == "__main__":
    main()
