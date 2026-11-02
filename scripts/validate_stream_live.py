#!/usr/bin/env python3
"""Live check of single-sourcetype streaming (native and grounded-sample paths independently) against the engine and the isolated Docker lab.
Continuous run: counters over several intervals, pause holds, resume, stop, no orphan, independent Splunk verification. Also finite count and duration.
Usage: NETSPOUT_ENGINE=http://127.0.0.1:8091 python scripts/validate_stream_live.py     Evidence: docs/verification/evidence/monitor/stream_live.json (no secrets)."""
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from validate_monitor_live import call, follow, verify  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "docs/verification/evidence/monitor/stream_live.json"
CASES = [("native", "cisco:dc:aci:class", "cisco_aci"), ("grounded_sample", "arista:eos:syslog", "arista_eos")]
IDX = "dev_test_replay"


def snap(rid):
    return call("GET", "/api/runs/" + rid)[1]


def continuous(label, st, vendor):
    r = {"name": "continuous_" + label, "target": st}
    _, s = call("POST", "/api/runs", {"kind": "sourcetype", "target": st, "vendor_id": vendor, "index": IDX, "mode": "continuous", "eps": 8})
    rid = r["run_id"] = s["run_id"]
    r["source_mode"], r["mode"] = s.get("source_mode"), s.get("mode")
    series = []
    for _ in range(4):
        time.sleep(2.5)
        series.append(snap(rid)["counters"]["attempts"])
    r["attempts_over_intervals"] = series
    grew = all(b > a for a, b in zip(series, series[1:]))
    call("POST", "/api/runs/%s/pause" % rid); time.sleep(1.0)
    a = snap(rid)["counters"]["attempts"]; time.sleep(3)
    p = snap(rid)
    held = p["counters"]["attempts"] == a and p["state"] == "PAUSED"
    call("POST", "/api/runs/%s/resume" % rid); time.sleep(3)
    resumed = snap(rid)["counters"]["attempts"] > a
    call("POST", "/api/runs/%s/stop" % rid)
    fin, _ = follow(rid, 30)
    n1 = fin["counters"]["attempts"]; time.sleep(3)
    n2 = snap(rid)["counters"]["attempts"]
    active = [x for x in call("GET", "/api/runs")[1]["runs"] if x.get("state") in ("RUNNING", "PAUSED", "STOPPING")]
    v = verify(rid, 60)
    after = snap(rid)
    c = after["counters"]
    r.update(counters=c, final_state=fin["state"], grew_each_interval=grew, held_while_paused=held, resumed=resumed, no_growth_after_stop=n1 == n2, active_runs_after=len(active),
             verification=v.get("status") if v else None, indexed=c["indexed"], progress_pct_while_unbounded=fin["progress"]["pct"])
    r["ok"] = bool(grew and held and resumed and fin["state"] == "STOPPED" and n1 == n2 and not active and v and v.get("status") == "VERIFIED"
                   and c["indexed"] == c["accepted"] and c["accepted"] == c["attempts"] and c["pending"] == c["generated"] - c["attempts"])
    return r


def finite(label, st, vendor):
    out = []
    for name, body in (("count", {"mode": "finite", "count": 25, "eps": 50}), ("duration", {"mode": "duration", "duration_s": 5, "eps": 10})):
        _, s = call("POST", "/api/runs", {"kind": "sourcetype", "target": st, "vendor_id": vendor, "index": IDX, **body})
        rid = s["run_id"]; fin, _ = follow(rid, 60); v = verify(rid, 60); c = snap(rid)["counters"]
        want = 25 if name == "count" else None
        out.append({"name": "%s_%s" % (name, label), "run_id": rid, "state": fin["state"], "counters": c, "verification": v.get("status") if v else None,
                    "ok": fin["state"] == "COMPLETED" and (want is None or c["attempts"] == want) and v and v.get("status") == "VERIFIED" and c["indexed"] == c["accepted"] > 0})
    return out


def main():
    results = []
    for label, st, vendor in CASES:
        results.append(continuous(label, st, vendor)); print(("PASS " if results[-1]["ok"] else "FAIL ") + results[-1]["name"], json.dumps({k: results[-1][k] for k in ("attempts_over_intervals", "final_state", "verification", "indexed")}))
        for f in finite(label, st, vendor):
            results.append(f); print(("PASS " if f["ok"] else "FAIL ") + f["name"], f["state"], f["verification"])
    OUT.write_text(json.dumps({"generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"), "lab": "isolated Docker Splunk Enterprise 10.2.7", "results": results}, indent=1) + "\n")
    sys.exit(0 if all(r["ok"] for r in results) else 1)


if __name__ == "__main__":
    main()
