#!/usr/bin/env python3
"""Short, un-profiled screening run of the streaming worker against a disposable fake HEC: paced at <eps> for <seconds>, reports achieved rate, CPU, memory, outcomes and per-event CPU time,
and checks that the events the fake HEC received are distinct, correctly timestamped and carry the run id.
  python scripts/phase17_screen.py <hec_port> <label> <eps> <seconds> <outfile.json> [hec_capture.ndjson]"""
import json, os, resource, sys, time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [os.path.join(ROOT, "src"), os.path.join(ROOT, "backend")]
port, label, eps, secs, out = int(sys.argv[1]), sys.argv[2], float(sys.argv[3]), float(sys.argv[4]), sys.argv[5]
from netspout_core.models import TelemetryTransportConfig
from netspout_core.telemetry_dispatcher import dispatcher
from netspout_core.delivery_monitor import ContinuousRun
from netspout_core.generator_modes import generator_service
import app.main as m
ST, VENDOR = "pan:traffic", "palo_alto"
cfg = TelemetryTransportConfig(hec_enabled=True, hec_url="https://127.0.0.1:%d/services/collector/event" % port, hec_token="x" * 36, hec_index="dev_test_replay", hec_ssl_verify=False, hec_allow_insecure_tls=True)
def produce(n):
    es, _ = generator_service.prepare_sourcetype_entries(VENDOR, ST, n, None, "run-screen", None)
    return [m._hec_item(lambda e=e: dispatcher.dispatch_log(e, cfg), ST, None, m._metric_datapoints(e)) for e in es]
r = ContinuousRun("sourcetype", ST, ST, "fake", "dev_test_replay", [], eps_limit=eps, run_id="run-screen", produce=produce, duration_s=secs)
r.state, r._t0 = "RUNNING", time.monotonic()
ru0, t0 = resource.getrusage(resource.RUSAGE_SELF), time.perf_counter()
r._work()
wall = time.perf_counter() - t0; ru1 = resource.getrusage(resource.RUSAGE_SELF)
cpu = ru1.ru_utime + ru1.ru_stime - ru0.ru_utime - ru0.ru_stime
c = r.counts
res = {"label": label, "requested_eps": eps, "seconds": round(wall, 1), "attempts": c["attempts"], "accepted": c["accepted"], "rejected": c["rejected"], "unknown": c["unknown"],
       "achieved_eps": round(c["attempts"] / wall, 1), "cpu_pct_of_one_core": round(100 * cpu / wall, 1), "cpu_ms_per_event": round(1000 * cpu / max(1, c["attempts"]), 3),
       "peak_rss_mb": round(ru1.ru_maxrss / (1024 * 1024 if sys.platform == "darwin" else 1024), 1), "final_state": r.state}
if len(sys.argv) > 6:   # correctness of what the collector actually received
    time.sleep(1)
    evs = []
    for ln in open(sys.argv[6]):
        row = json.loads(ln)
        dec, b = json.JSONDecoder(), row["body"]; i = 0
        while i < len(b):
            o, j = dec.raw_decode(b, i); evs.append((row["rx"], o)); i = j
            while i < len(b) and b[i].isspace(): i += 1
    raws = [e["event"] for _, e in evs]; lag = sorted(rx - e["time"] for rx, e in evs)
    res["received"] = {"events": len(evs), "distinct_raw_events": len(set(raws)), "distinct_ratio": round(len(set(raws)) / max(1, len(raws)), 4), "all_have_sourcetype_index_host": all(e.get("sourcetype") == ST and e.get("index") == "dev_test_replay" and e.get("host") for _, e in evs),
                       "run_id_on_every_event": all((e.get("fields") or {}).get("netspout_run_id") == "run-screen" or "run-screen" in json.dumps(e) for _, e in evs),
                       "send_to_receive_lag_s": {"min": round(lag[0], 4), "p50": round(lag[len(lag) // 2], 4), "p99": round(lag[int(len(lag) * .99)], 4), "max": round(lag[-1], 4)},
                       "event_time_monotonic_non_decreasing": all(evs[i][1]["time"] <= evs[i + 1][1]["time"] for i in range(len(evs) - 1))}
json.dump(res, open(out, "w"), indent=1); print(json.dumps(res))
