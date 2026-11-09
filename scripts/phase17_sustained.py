#!/usr/bin/env python3
"""Sustained-load test at the supported ceiling (200 events/s) against the disposable Splunk container, sampling the engine, launcher and splunkd.
  P17_MGMT=... P17_PASSWORD_FILE=... P17_TARGET=splunk-10.6.1 python scripts/phase17_sustained.py <container> [duration_s] [host label]
Resource numbers come from `ps` inside the container; on an emulated amd64 container CPU time is inflated and is labelled as such."""
import json
import statistics
import subprocess
import sys
import time

import phase17_acceptance as a

container = sys.argv[1]
duration = int(sys.argv[2]) if len(sys.argv) > 2 else 900
host = sys.argv[3] if len(sys.argv) > 3 else "unlabelled"
ST = ("pan:traffic", "palo_alto")


def procs():
    out = subprocess.run("docker exec -u root %s ps -eo rss,pcpu,args" % container, shell=True, capture_output=True, text=True).stdout.splitlines()
    pick = lambda key: next(((int(l.split()[0]), float(l.split()[1])) for l in out if key in l and "grep" not in l), (None, None))
    return {"engine": pick("pulseforge_engine_main"), "launcher": pick("pulseforge_engine_launcher"), "splunkd": pick("splunkd -p")}


def search_latency():
    t = time.time()
    a.search("| makeresults | eval x=1 | table x", "-1m")
    return round(time.time() - t, 2)


before = a.count('index=%s sourcetype="%s"' % (a.IDX, ST[0]))
code, s = a.start({"kind": "sourcetype", "target": ST[0], "vendor_id": ST[1], "mode": "duration", "duration_s": duration, "eps": 200})
if code != 200:
    sys.exit("start refused: %s %s" % (code, s))
rid, t0, samples = s["run_id"], time.time(), []
idle_baseline = procs()
while time.time() - t0 < duration + 90:
    _, snap = a.gw("GET", "/api/runs/" + rid)
    p = procs()
    samples.append({"t": round(time.time() - t0), "state": snap["state"], "attempts": snap["counters"]["attempts"], "accepted": snap["counters"]["accepted"], "rejected": snap["counters"]["rejected"],
                    "current_eps": (snap.get("rate") or {}).get("current_eps"), "engine_rss_kb": p["engine"][0], "engine_pcpu": p["engine"][1], "splunkd_rss_kb": p["splunkd"][0], "launcher_rss_kb": p["launcher"][0],
                    "search_latency_s": search_latency() if len(samples) % 4 == 0 else None})
    if snap["state"] in ("COMPLETED", "FAILED", "STOPPED"):
        break
    time.sleep(15)
final = a.gw("GET", "/api/runs/" + rid)[1]
v = a.verify(rid, 180)
time.sleep(10)
indexed_delta = a.count('index=%s sourcetype="%s"' % (a.IDX, ST[0])) - before
c = final["counters"]
wall = samples[-1]["t"]
rss = [x["engine_rss_kb"] for x in samples if x["engine_rss_kb"]]
q = max(1, len(rss) // 4)
res = {"name": "sustained_200_eps", "host": host, "run_id": rid, "requested_duration_s": duration, "requested_eps": 200, "final_state": final["state"], "counters": c, "wall_s_to_final_sample": wall,
       "mean_attempts_per_s": round(c["attempts"] / max(1, final.get("elapsed_s") or wall), 1), "engine_verification": v.get("status"), "independent_indexed_delta": indexed_delta,
       "idle_before": idle_baseline, "engine_rss_kb": {"min": min(rss), "max": max(rss), "first_quarter_mean": round(statistics.mean(rss[:q])), "last_quarter_mean": round(statistics.mean(rss[-q:]))},
       "engine_pcpu_mean": round(statistics.mean(x["engine_pcpu"] for x in samples if x["engine_pcpu"] is not None), 1), "splunkd_rss_kb_max": max(x["splunkd_rss_kb"] for x in samples if x["splunkd_rss_kb"]),
       "search_latency_s": [x["search_latency_s"] for x in samples if x["search_latency_s"] is not None], "samples": samples,
       "ok": final["state"] == "COMPLETED" and c["accepted"] == c["attempts"] and v.get("status") == "VERIFIED" and indexed_delta == c["accepted"]}
res["note"] = "pcpu is ps's lifetime-average per process under emulation; read it as relative, not as native CPU cost"
a.save("sustained_200eps", {"results": [res]})
print(json.dumps({k: res[k] for k in ("final_state", "counters", "mean_attempts_per_s", "engine_rss_kb", "independent_indexed_delta", "engine_verification", "ok")}))
