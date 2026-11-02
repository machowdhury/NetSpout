"""Live verification of the 37 NetSpout incident packs against the local Splunk lab (reads git-ignored tests/lab/phase4e/.env.lab).

Each pack is run through the product route (/api/generate/scenario-pack, dispatching to the Connection Center destination). Evidence is then
read back with independent splunkd searches: log events per phase, mstats datapoint counts and per-metric averages versus the values the
deterministic generator produces locally, dimensions present on the datapoints, and absence of run metadata leaking nowhere it should not.
Modeled NetSpout telemetry: this proves delivery, correlation and metric fidelity, not vendor-native format, TA parsing or detections.
Writes docs/verification/evidence/incident_packs/live_results.json (no credentials). Usage: verify_incident_packs_live.py [--backend URL] [--only ID]
"""
import argparse
import base64
import json
import ssl
import sys
import time
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from netspout_core import incident_packs as ip

ENV = dict(l.strip().split("=", 1) for l in (ROOT / "tests/lab/phase4e/.env.lab").read_text().splitlines() if "=" in l)
CTX = ssl._create_unverified_context()  # isolated loopback lab, self-signed certificate
EVENT_INDEX, METRIC_INDEX = "idx_network_ops", "cisco_mdt_metrics"


def search(spl, earliest="-30m"):
    req = urllib.request.Request("https://127.0.0.1:%s/services/search/jobs/export" % ENV["LAB_MGMT_PORT"],
                                 urllib.parse.urlencode({"search": spl, "output_mode": "json", "earliest_time": earliest, "preview": "false"}).encode())
    req.add_header("Authorization", "Basic " + base64.b64encode(("admin:" + ENV["LAB_SPLUNK_PASSWORD"]).encode()).decode())
    out = urllib.request.urlopen(req, context=CTX, timeout=120).read().decode()
    return [json.loads(l)["result"] for l in out.splitlines() if '"result"' in l]


def run(base, sid):
    req = urllib.request.Request(base + "/api/generate/scenario-pack", json.dumps({"scenario_id": sid, "dispatch": True, "index": EVENT_INDEX}).encode(),
                                 {"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=180).read())


def verify(base, entry):
    sid = entry["scenario_id"]
    reply = run(base, sid)
    rid = reply["run_id"]
    accepted = sum(1 for d in reply["dispatch_results"] if d["hec"]["success"])
    local = ip.generate_pack(sid, rid)  # deterministic values; run id only changes correlation fields
    exp_phase = Counter(e["fields"]["netspout_phase"] for e in local if "metrics" not in e)
    exp_metric = {}
    for e in local:
        for name, value in e.get("metrics", {}).items():
            exp_metric.setdefault(name, []).append(float(value))
    by_phase, metric_rows, dims = {}, [], []
    for _ in range(15):
        time.sleep(3)
        by_phase = {r["netspout_phase"]: int(r["count"]) for r in search('search index=%s netspout_run_id="%s" | stats count by netspout_phase' % (EVENT_INDEX, rid))}
        metric_rows = search('| mstats count(_value) as n avg(_value) as avg WHERE index=%s AND metric_name=* AND netspout_run_id="%s" BY metric_name' % (METRIC_INDEX, rid))
        if sum(by_phase.values()) >= 30 and sum(int(r["n"]) for r in metric_rows) >= sum(len(v) for v in exp_metric.values()):
            break
    dims = search('| mstats count(_value) as n WHERE index=%s AND metric_name=* AND netspout_run_id="%s" BY netspout_phase netspout_device_id netspout_scenario_id' % (METRIC_INDEX, rid))
    got = {r["metric_name"]: (int(r["n"]), float(r["avg"])) for r in metric_rows}
    values_ok = set(got) == set(exp_metric) and all(
        got[k][0] == len(v) and abs(got[k][1] - sum(v) / len(v)) < 1e-6 for k, v in exp_metric.items())
    sourcetypes = {r["sourcetype"] for r in search('search index=%s netspout_run_id="%s" | stats count by sourcetype' % (EVENT_INDEX, rid))}
    ok = (accepted == reply["count_generated"] == 40 and by_phase == dict(exp_phase) and values_ok and bool(dims)
          and sum(int(r["n"]) for r in metric_rows) == reply["metric_datapoints_expected"])
    return {"scenario_id": sid, "run_id": rid, "family": entry["family"], "hec_accepted": accepted, "generated": reply["count_generated"],
            "log_events_by_phase_indexed": by_phase, "log_events_by_phase_expected": dict(exp_phase),
            "metric_datapoints_indexed": sum(int(r["n"]) for r in metric_rows), "metric_datapoints_expected": reply["metric_datapoints_expected"],
            "metric_names": sorted(got), "metric_values_match_generator": values_ok, "dimension_rows": len(dims),
            "sourcetypes_indexed": sorted(sourcetypes), "verdict": "PASS" if ok else "FAIL"}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", default="http://127.0.0.1:8081")
    ap.add_argument("--only")
    a = ap.parse_args()
    rows = [verify(a.backend, e) for e in ip.catalog() if not a.only or e["scenario_id"] == a.only]
    doc = {"index": EVENT_INDEX, "metric_index": METRIC_INDEX, "telemetry": "MODELED_NETSPOUT_SCHEMA", "ta_parser_checks_performed": 0,
           "detection_checks_performed": 0, "scenario_runs": rows}
    out = ROOT / "docs/verification/evidence/incident_packs/live_results.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, indent=1) + "\n")
    print(json.dumps({"packs": len(rows), "pass": sum(r["verdict"] == "PASS" for r in rows), "fail": [r["scenario_id"] for r in rows if r["verdict"] != "PASS"]}))
