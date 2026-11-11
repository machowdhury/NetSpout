#!/usr/bin/env python3
"""Profile the single-sourcetype streaming path (the one the 200 events/s test drives) against a disposable fake HEC.
  python scripts/phase17_profile.py <hec_port> <label> [seconds] [outfile.json]
Stages timed on their own (µs/event), then the whole ContinuousRun worker under cProfile with the rate limiter off (maximum rate).
Run with HEC_REUSE unset for the committed code path."""
import cProfile, io, json, os, pstats, sys, time, tracemalloc
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [os.path.join(ROOT, "src"), os.path.join(ROOT, "backend")]
port, label = int(sys.argv[1]), sys.argv[2]
secs = float(sys.argv[3]) if len(sys.argv) > 3 else 20
out = sys.argv[4] if len(sys.argv) > 4 else None
from netspout_core.models import TelemetryTransportConfig
from netspout_core.telemetry_dispatcher import dispatcher
from netspout_core.delivery_monitor import ContinuousRun
from netspout_core.generator_modes import generator_service
import app.main as m                       # for _hec_item exactly as the engine builds it

ST, VENDOR = "pan:traffic", "palo_alto"
cfg = TelemetryTransportConfig(hec_enabled=True, hec_url="https://127.0.0.1:%d/services/collector/event" % port, hec_token="x" * 36, hec_index="dev_test_replay",
                               hec_ssl_verify=False, hec_allow_insecure_tls=True)
def per_event(fn, n):
    t = time.perf_counter(); r = None
    for _ in range(n): r = fn()
    return round((time.perf_counter() - t) / n * 1e6, 1), r

res = {"label": label, "stages_us_per_event": {}}
N = 400
us, ents = per_event(lambda: generator_service.prepare_sourcetype_entries(VENDOR, ST, 25, None, "run-prof", None), N // 25)
res["stages_us_per_event"]["generate_entries (render+random+timestamp)"] = round(us / 25, 1)
entries = [e for _ in range(N // 25) for e in generator_service.prepare_sourcetype_entries(VENDOR, ST, 25, None, "run-prof", None)[0]]
cap = []
t = time.perf_counter()
for e in entries: dispatcher._dispatch_log(e, cfg, capture=cap)
res["stages_us_per_event"]["build_hec_payload (capture only, nothing sent)"] = round((time.perf_counter() - t) / len(entries) * 1e6, 1)
t = time.perf_counter()
for p in cap: json.dumps(p).encode()
res["stages_us_per_event"]["json_serialize"] = round((time.perf_counter() - t) / len(cap) * 1e6, 1)
t = time.perf_counter()
for p in cap[:200]: dispatcher._send_hec(p, cfg.hec_url, cfg.hec_token, False, True)
res["stages_us_per_event"]["send_hec_one_request_per_event (incl. TLS)"] = round((time.perf_counter() - t) / 200 * 1e6, 1)

def make_run(n_secs, eps=None):
    def produce(n):
        es, _ = generator_service.prepare_sourcetype_entries(VENDOR, ST, n, None, "run-prof", None)
        return [m._hec_item(lambda e=e: dispatcher.dispatch_log(e, cfg), ST, None, m._metric_datapoints(e)) for e in es]
    return ContinuousRun("sourcetype", ST, ST, "fake", "dev_test_replay", [], eps_limit=eps, run_id="run-prof", produce=produce, duration_s=n_secs)

r = make_run(secs); r.state, r._t0 = "RUNNING", time.monotonic()
import resource
ru0 = resource.getrusage(resource.RUSAGE_SELF); t0 = time.perf_counter()
pr = cProfile.Profile(); pr.runcall(r._work)
wall = time.perf_counter() - t0; ru1 = resource.getrusage(resource.RUSAGE_SELF)
cpu = ru1.ru_utime + ru1.ru_stime - ru0.ru_utime - ru0.ru_stime
res["max_rate_run"] = {"seconds": round(wall, 1), "events": r.counts["attempts"], "accepted": r.counts["accepted"], "rejected": r.counts["rejected"], "unknown": r.counts["unknown"],
                       "eps_under_cprofile": round(r.counts["attempts"] / wall, 1), "cpu_pct_of_one_core": round(100 * cpu / wall, 1), "peak_rss_kb": ru1.ru_maxrss // 1024 if sys.platform == "darwin" else ru1.ru_maxrss}
s = io.StringIO(); ps = pstats.Stats(pr, stream=s).sort_stats("cumulative"); ps.print_stats(45)
res["top_cumulative"] = [l for l in s.getvalue().splitlines() if l.strip()][:60]
s2 = io.StringIO(); pstats.Stats(pr, stream=s2).sort_stats("tottime").print_stats(25)
res["top_tottime"] = [l for l in s2.getvalue().splitlines() if l.strip()][:40]
print(json.dumps({k: res[k] for k in ("label", "stages_us_per_event", "max_rate_run")}, indent=1))
if out: json.dump(res, open(out, "w"), indent=1)
