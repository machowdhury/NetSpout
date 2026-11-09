#!/usr/bin/env python3
"""Sustained-load test at the supported ceiling (200 events/s) against a disposable Splunk container.

  P17_MGMT=... P17_PASSWORD_FILE=... P17_TARGET=<evidence subdir> [P17_NATIVE=1] python scripts/phase17_sustained.py <container> [duration_s] [host label]

Measures: events actually indexed per minute (by index time), indexing latency (_indextime - _time percentiles), engine / launcher / splunkd CPU and RSS,
index and filesystem disk use, errors and dropped events (accepted - indexed, rejected, HEC and queue warnings in Splunk's own logs, process restarts).
P17_NATIVE=1 (Docker on a native Linux host): per-process CPU% is measured with psutil on the host PIDs. Otherwise (Docker Desktop, emulation) it falls back to
`ps` inside the container, whose pcpu is a lifetime average and must be read as relative only. The host label is stored with the evidence."""
import json
import os
import shutil
import statistics
import subprocess
import sys
import time

import phase17_acceptance as a

container = sys.argv[1]
duration = int(sys.argv[2]) if len(sys.argv) > 2 else 900
host = sys.argv[3] if len(sys.argv) > 3 else "unlabelled"
NATIVE = os.environ.get("P17_NATIVE") == "1"
ST = ("pan:traffic", "palo_alto")
KEYS = {"engine": "pulseforge_engine_main", "launcher": "pulseforge_engine_launcher", "splunkd": "splunkd -p"}
if NATIVE:
    import psutil

    _procs = {}


def sh(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True).stdout


def sample_procs():
    out = {}
    if NATIVE:
        for name, key in KEYS.items():
            p = _procs.get(name)
            if not p or not p.is_running():
                p = next((x for x in psutil.process_iter(["cmdline"]) if key in " ".join(x.info["cmdline"] or [])), None)
                _procs[name] = p
                if p:
                    p.cpu_percent(None)
            out[name] = (p.memory_info().rss // 1024, p.cpu_percent(None), p.pid) if p and p.is_running() else (None, None, None)
        return out
    lines = sh("docker exec -u root %s ps -eo rss,pcpu,args" % container).splitlines()
    for name, key in KEYS.items():
        out[name] = next(((int(l.split()[0]), float(l.split()[1]), None) for l in lines if key in l and "grep" not in l), (None, None, None))
    return out


def index_bytes():
    out = sh("docker exec -u root %s sh -c 'du -sb /opt/splunk/var/lib/splunk/%s 2>/dev/null; du -sb /opt/splunk/var/lib/splunk 2>/dev/null | head -1'" % (container, a.IDX)).split()
    return {"index_bytes": int(out[0]) if out else None, "all_indexes_bytes": int(out[2]) if len(out) > 2 else None}


def disk():
    u = shutil.disk_usage("/") if NATIVE else None
    return {"fs_used_gb": round(u.used / 1e9, 2), "fs_free_gb": round(u.free / 1e9, 2)} if u else {}


def search_latency():
    t = time.time()
    a.search("| makeresults | eval x=1 | table x", "-1m")
    return round(time.time() - t, 2)


def server_now():
    return int(float(a.search("| makeresults | eval t=now() | table t", "-1m")[0]["t"]))


before = a.count('index=%s sourcetype="%s"' % (a.IDX, ST[0]))
sample_procs()
idle_baseline = sample_procs()
disk_before = {**index_bytes(), **disk()}
t_start = server_now()
code, s = a.start({"kind": "sourcetype", "target": ST[0], "vendor_id": ST[1], "mode": "duration", "duration_s": duration, "eps": 200})
if code != 200:
    sys.exit("start refused: %s %s" % (code, s))
rid, t0, samples = s["run_id"], time.time(), []
while time.time() - t0 < duration + 120:
    _, snap = a.gw("GET", "/api/runs/" + rid)
    p = sample_procs()
    row = {"t": round(time.time() - t0), "state": snap["state"], "attempts": snap["counters"]["attempts"], "accepted": snap["counters"]["accepted"], "rejected": snap["counters"]["rejected"],
           "unknown": snap["counters"]["unknown"], "current_eps": (snap.get("rate") or {}).get("current_eps"), "recent_errors": len(snap.get("recent_errors") or []),
           "search_latency_s": search_latency() if len(samples) % 4 == 0 else None}
    for name, (rss, cpu, pid) in p.items():
        row[name + "_rss_kb"], row[name + "_cpu_pct"] = rss, cpu
    if len(samples) % 8 == 0:
        row.update(index_bytes())
        row.update(disk())
    samples.append(row)
    if snap["state"] in ("COMPLETED", "FAILED", "STOPPED"):
        break
    time.sleep(15)
final = a.gw("GET", "/api/runs/" + rid)[1]
t_done = time.time()
settle = None
while time.time() - t_done < 180:   # how long after the last event was sent until every accepted event is searchable
    indexed_delta = a.count('index=%s sourcetype="%s"' % (a.IDX, ST[0])) - before
    if indexed_delta >= final["counters"]["accepted"]:
        settle = round(time.time() - t_done, 1)
        break
    time.sleep(2)
v = a.verify(rid, 300)
time.sleep(15)
t_end = server_now()
indexed_delta = a.count('index=%s sourcetype="%s"' % (a.IDX, ST[0])) - before
window = "_index_earliest=%d _index_latest=%d earliest=0" % (t_start, t_end)
per_minute = a.search('index=%s sourcetype="%s" %s | eval m=floor(_indextime/60)*60 | stats count by m | sort m' % (a.IDX, ST[0], window), "0")
latency = a.search('index=%s sourcetype="%s" %s | eval lag=_indextime-_time | stats count perc50(lag) as p50 perc95(lag) as p95 perc99(lag) as p99 max(lag) as max' % (a.IDX, ST[0], window), "0")
warn = a.search('index=_internal source=*splunkd.log* earliest=%d latest=%d (log_level=WARN OR log_level=ERROR) (component=HttpInputDataHandler OR component=HttpListener OR component=TcpInputProc) | stats count by component, log_level' % (t_start, t_end), "0")
blocked = a.search('index=_internal source=*metrics.log* group=queue blocked=true earliest=%d latest=%d | stats count by name' % (t_start, t_end), "0")
c = final["counters"]
eps_min = [int(r["count"]) / 60.0 for r in per_minute[1:-1]]   # first and last minute are partial
rss = [x["engine_rss_kb"] for x in samples if x.get("engine_rss_kb")]
q = max(1, len(rss) // 4)
cpu = lambda k: [x[k + "_cpu_pct"] for x in samples if x.get(k + "_cpu_pct") is not None]
stat = lambda k: {"mean": round(statistics.mean(cpu(k)), 1), "max": max(cpu(k))} if cpu(k) else None
res = {"name": "sustained_200_eps", "host": host, "native": NATIVE, "run_id": rid, "requested_duration_s": duration, "requested_eps": 200, "final_state": final["state"], "counters": c,
       "elapsed_s": final.get("elapsed_s"), "mean_attempts_per_s": round(c["attempts"] / max(1, final.get("elapsed_s") or samples[-1]["t"]), 1),
       "engine_verification": v.get("status"), "independent_indexed_delta": indexed_delta, "dropped_events_accepted_minus_indexed": c["accepted"] - indexed_delta,
       "indexed_eps_per_full_minute": {"min": round(min(eps_min), 1) if eps_min else None, "mean": round(statistics.mean(eps_min), 1) if eps_min else None, "max": round(max(eps_min), 1) if eps_min else None, "minutes": len(eps_min)},
       "indexing_lag_vs_event_time_s": latency[0] if latency else None, "lag_note": "_indextime minus the event's own timestamp; negative values mean the engine stamps events slightly ahead of when they are sent, so read p95/max as an upper bound only",
       "seconds_from_last_event_sent_to_all_indexed": settle, "splunk_internal_warnings_in_window": warn, "blocked_queues_in_window": blocked,
       "idle_before": idle_baseline, "engine_rss_kb": {"min": min(rss), "max": max(rss), "first_quarter_mean": round(statistics.mean(rss[:q])), "last_quarter_mean": round(statistics.mean(rss[-q:]))},
       "engine_cpu_pct": stat("engine"), "splunkd_cpu_pct": stat("splunkd"), "splunkd_rss_kb_max": max(x["splunkd_rss_kb"] for x in samples if x.get("splunkd_rss_kb")),
       "disk_before": disk_before, "disk_after": {**index_bytes(), **disk()}, "search_latency_s": [x["search_latency_s"] for x in samples if x["search_latency_s"] is not None],
       "samples": samples, "indexed_per_minute": per_minute,
       "ok": final["state"] == "COMPLETED" and c["accepted"] == c["attempts"] and c["rejected"] == 0 and v.get("status") == "VERIFIED" and indexed_delta == c["accepted"]}
res["note"] = "cpu_pct is psutil's per-process CPU over each ~15 s interval (100 = one core)" if NATIVE else "cpu_pct is ps's lifetime average under emulation: relative only"
res["reached_ceiling"] = bool(res["mean_attempts_per_s"] >= 190)
a.save("sustained_200eps", {"results": [res]})
print(json.dumps({k: res[k] for k in ("final_state", "counters", "mean_attempts_per_s", "indexed_eps_per_full_minute", "indexing_lag_vs_event_time_s", "seconds_from_last_event_sent_to_all_indexed", "dropped_events_accepted_minus_indexed", "engine_rss_kb", "ok", "reached_ceiling")}))
