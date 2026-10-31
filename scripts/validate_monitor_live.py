#!/usr/bin/env python3
"""Live check of the delivery monitor against the engine and the isolated Docker lab (never the demo lab or any cloud).
Runs one bounded run per family through /api/runs, polls it while it runs, then verifies with an independent Splunk search via /api/runs/{id}/verify.
Usage: NETSPOUT_ENGINE=http://127.0.0.1:8091 python scripts/validate_monitor_live.py     Evidence: docs/verification/evidence/monitor/live.json (no secrets)."""
import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ENGINE = os.environ.get("NETSPOUT_ENGINE", "http://127.0.0.1:8091")
OUT = Path(__file__).resolve().parents[1] / "docs/verification/evidence/monitor/live.json"
FINAL = ("COMPLETED", "STOPPED", "FAILED", "INTERRUPTED")


def call(method, path, body=None):
    req = urllib.request.Request(ENGINE + path, method=method, data=None if body is None else json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def follow(rid, timeout=240):
    polls, t0 = [], time.time()
    while time.time() - t0 < timeout:
        _, s = call("GET", "/api/runs/" + rid)
        polls.append({"state": s["state"], "attempts": s["counters"]["attempts"], "eps": (s.get("rate") or {}).get("current_eps"), "pct": (s.get("progress") or {}).get("pct")})
        if s["state"] in FINAL:
            return s, polls
        time.sleep(0.5)
    return s, polls


def verify(rid, wait=45):
    last = None
    for _ in range(wait // 5):
        _, last = call("POST", "/api/runs/%s/verify" % rid)
        if last.get("status") == "VERIFIED":
            break
        time.sleep(5)
    return last


def case(name, body, expect_indexed=True):
    code, start = call("POST", "/api/runs", body)
    if code != 200:
        return {"name": name, "http": code, "detail": start.get("detail"), "ok": False}
    rid = start.get("run_id") or start.get("session_id")
    final, polls = follow(rid)
    c = final["counters"]
    v = verify(rid) if expect_indexed else None
    _, after = call("GET", "/api/runs/" + rid)
    mono = all(b["attempts"] >= a["attempts"] for a, b in zip(polls, polls[1:]))
    ok = (final["state"] == "COMPLETED" and c["generated"] == c["attempts"] == c["accepted"] + c["rejected"] + c["unknown"] and c["pending"] == 0 and mono
          and (not expect_indexed or (v and v.get("status") == "VERIFIED" and after["counters"]["indexed"] == c["accepted"])))
    return {"name": name, "run_id": rid, "mode": final.get("mode"), "state": final["state"], "counters": c, "polls": len(polls), "monotonic": mono,
            "peak_current_eps": max([p["eps"] or 0 for p in polls] + [0]), "avg_eps": (final.get("rate") or {}).get("average_eps"), "elapsed_s": final.get("elapsed_s"),
            "by_sourcetype": {k: v_.get("accepted") for k, v_ in (final.get("by_sourcetype") or {}).items()}, "phases": [(p["phase"], p.get("accepted"), p.get("total")) for p in final.get("by_phase") or []],
            "verification": {k: v.get(k) for k in ("status", "indexed", "accepted")} if v else None, "indexed_after": after["counters"]["indexed"], "ok": bool(ok)}


def controls():
    code, start = call("POST", "/api/runs", {"kind": "sourcetype", "target": "cisco:sdwan:utdhealth", "vendor_id": "cisco_sdwan", "count": 200, "eps": 20, "index": "dev_test_replay"})
    rid = start["run_id"]
    time.sleep(2)
    _, p = call("POST", "/api/runs/%s/pause" % rid)
    a = p["counters"]["attempts"]
    time.sleep(2)
    _, p2 = call("GET", "/api/runs/" + rid)
    held = p2["counters"]["attempts"] <= a + 1 and p2["state"] == "PAUSED"
    _, r = call("POST", "/api/runs/%s/resume" % rid)
    time.sleep(2)
    _, st = call("POST", "/api/runs/%s/stop" % rid)
    time.sleep(1)
    _, f = call("GET", "/api/runs/" + rid)
    c = f["counters"]
    v = verify(rid)
    return {"name": "pause_resume_stop", "run_id": rid, "paused_held": held, "state": f["state"], "counters": c, "verification": {k: v.get(k) for k in ("status", "indexed", "accepted")},
            "ok": held and f["state"] == "STOPPED" and 0 < c["attempts"] < 200 and c["pending"] == 200 - c["attempts"] and v["indexed"] == c["accepted"]}


def main():
    res = [
        case("single_sourcetype", {"kind": "sourcetype", "target": "cisco:sdwan:utdhealth", "vendor_id": "cisco_sdwan", "count": 30, "eps": 15, "index": "dev_test_replay"}),
        case("replay_pack_finite", {"kind": "scenario", "target": "rp_cloud_control_plane_activity", "speed": 50, "loops": 1, "index": "dev_test_replay"}),
        case("native_pack", {"kind": "scenario", "target": "ub5_cisco_change_induced_outage", "eps": 40, "index": "dev_test_replay"}),
        case("incident_pack", {"kind": "scenario", "target": "network_01_campus_link", "eps": 60, "index": "dev_test_replay"}),
        case("scenario_runner", {"kind": "scenario", "target": "arch_lan_campus_access", "index": "dev_test_replay"}),
        case("unified_generation", {"kind": "scenario", "target": "SEC-P9-B-DNS-ANOMALY", "count": 6, "eps": 20, "index": "dev_test_replay"}),
        controls(),
    ]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"generated_utc": datetime.now(timezone.utc).isoformat(), "engine": "isolated lab engine", "cases": res}, indent=1) + "\n")
    for r in res:
        print(("PASS " if r["ok"] else "FAIL ") + r["name"] + ("" if r["ok"] else " " + json.dumps(r)[:600]))


if __name__ == "__main__":
    main()
