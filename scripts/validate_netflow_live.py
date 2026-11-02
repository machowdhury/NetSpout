#!/usr/bin/env python3
"""Run each NetFlow solution scenario through the engine API (isolated lab only): HEC-delivered normalized events, the IPFIX wire stage, independent Splunk verification and run-bound readiness.
Usage: NETSPOUT_ENGINE=http://127.0.0.1:8091 python scripts/validate_netflow_live.py     Evidence: docs/verification/evidence/netflow/live_runs.json (no secrets)."""
import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ENGINE = os.environ.get("NETSPOUT_ENGINE", "http://127.0.0.1:8091")
INDEX = os.environ.get("NETSPOUT_LAB_INDEX", "dev_test_replay")
OUT = Path(__file__).resolve().parents[1] / "docs/verification/evidence/netflow/live_runs.json"
IDS = ["NF-NOC-01-ELEPHANT", "NF-NOC-02-DSCP", "NF-NOC-03-ROUTING-LOOP", "NF-NOC-04-ASYMMETRY", "NF-NOC-05-BASELINE-DRIFT", "NF-SEC-06-DDOS", "NF-SEC-07-PORTSCAN", "NF-SEC-08-EXFIL", "NF-SEC-09-BEACON", "NF-SEC-10-DNS-FLOW"]


def call(method, path, body=None):
    req = urllib.request.Request(ENGINE + path, method=method, data=None if body is None else json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return {"http": e.code, "detail": json.loads(e.read() or b"{}").get("detail")}


def one(sid, sourcetype=None):
    body = {"kind": "scenario", "target": sid, "index": INDEX, "eps": 300, "wire": True}
    if sourcetype:
        body["sourcetype"] = sourcetype
    s = call("POST", "/api/runs", body)
    if "run_id" not in s:
        return {"scenario_id": sid, "ok": False, "error": s}
    rid = s["run_id"]
    for _ in range(240):
        s = call("GET", "/api/runs/" + rid)
        if s["state"] in ("COMPLETED", "FAILED", "STOPPED"):
            break
        time.sleep(0.5)
    ready = {}
    for _ in range(30):
        ready = call("POST", "/api/runs/%s/readiness" % rid)
        if ready.get("state") in ("READY", "DEGRADED", "FAILED"):
            break
        time.sleep(4)
    c, v = s["counters"], ready.get("verification") or {}
    w = s.get("flow_wire") or {}
    ok = (s["state"] == "COMPLETED" and c["generated"] == c["accepted"] > 0 and not c["rejected"] and not c["unknown"] and v.get("status") == "VERIFIED"
          and v.get("indexed") == c["accepted"] and ready.get("state") == "READY")
    return {"scenario_id": sid, "run_id": rid, "sourcetype": s.get("sourcetype"), "state": s["state"], "counters": {k: c[k] for k in ("generated", "attempts", "accepted", "rejected", "unknown", "pending")},
            "indexed_by_independent_search": v.get("indexed"), "verification": v.get("status"), "readiness": ready.get("state"), "elapsed_to_ready_s": ready.get("elapsed_to_ready_s"),
            "dashboard": (ready.get("dashboard") or {}).get("view"), "flow_summary": s.get("flow_summary"),
            "wire": {k: w.get(k) for k in ("state", "generated", "udp_exported", "datagrams", "collector_decoded")}, "ok": bool(ok)}


def main():
    res = [one(s) for s in IDS]
    res.append(dict(one("NF-SEC-09-BEACON", "cisco:ios:ipfix"), note="same scenario with the optional sourcetype cisco:ios:ipfix (not a catalog sourcetype)"))
    for r in res:
        print(("PASS " if r["ok"] else "FAIL ") + r["scenario_id"] + (" [%s]" % r.get("sourcetype") if r.get("sourcetype") else ""), r.get("counters"), r.get("indexed_by_independent_search"), r.get("readiness"), r.get("wire"), flush=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"generated_utc": datetime.now(timezone.utc).isoformat(timespec="minutes"), "engine": "isolated lab engine", "index": INDEX, "runs": res}, indent=1) + "\n")


if __name__ == "__main__":
    main()
