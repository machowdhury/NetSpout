#!/usr/bin/env python3
"""Run the five flow-based SEC-P9 scenarios through the engine against the repo GoFlow2 collector and forwarder (isolated Docker lab) and verify each independently:
generation (native UDP IPFIX), the collector's own counters, and indexed decoded flows read back from Splunk by run id.
Prerequisites: docker compose -p pf-lab-flow -f deploy/collector/docker-compose.collector.yml up (see docs/guides/NATIVE_FLOW_QUICKSTART.md), engine started with
NETSPOUT_GOFLOW_METRICS_URL / NETSPOUT_FLOW_FORWARDER_STATUS_URL / NETSPOUT_COLLECTOR_HOST.   Evidence: docs/verification/evidence/flow/scenarios.json (no secrets)."""
import json
import os
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import validate_ta_windows as lab  # noqa: E402

ENGINE = os.environ.get("NETSPOUT_ENGINE", "http://127.0.0.1:8091")
FWD = os.environ.get("NETSPOUT_FLOW_FORWARDER_STATUS_URL", "http://127.0.0.1:8082")
SCENARIOS = ["SEC-P9-A-TRAFFIC-FLOOD", "SEC-P9-C-BEACONING", "SEC-P9-D-INTERNAL-RECON", "SEC-P9-E-DNS-TUNNEL", "SEC-P9-F-CROSS-SOURCE"]


def post(path, body=None):
    req = urllib.request.Request(ENGINE + path, method="POST", data=json.dumps(body or {}).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read())


def fwd():
    return json.loads(urllib.request.urlopen(FWD + "/health", timeout=10).read())


def main():
    out = {}
    for sid in SCENARIOS:
        before = fwd()
        run = post("/api/generation/runs", {"mode": "SCENARIO", "selection_id": sid, "count": 6})
        rid = run["run_id"]
        obs, indexed = {}, []
        for _ in range(8):
            time.sleep(6)
            obs = post("/api/generation/runs/%s/observe" % rid)
            stages = {e["stage"]: e["state"] for e in obs.get("evidence", [])}
            if stages.get("SPLUNK_OBSERVED") == "PROVEN":
                break
        after = fwd()
        rows = lab.search('search index=* netspout_run_id="%s" | stats count by sourcetype' % rid, "-2h")
        total = sum(int(r["count"]) for r in rows)
        rows2 = lab.search('search index=* netspout_run_id="%s" | stats count as flows dc(src_addr) as sources dc(dst_addr) as dests dc(proto) as protos sum(bytes) as bytes earliest(_time) as first latest(_time) as last' % rid, "-2h")
        d = rows2[0] if rows2 else {}
        stages = {e["stage"]: e["state"] for e in obs.get("evidence", [])}
        out[sid] = {"run_id": rid, "generated": run.get("status"), "observed_status": obs.get("status"), "stages": stages,
                    "collector": {"flows_read_delta": after["flows_read"] - before["flows_read"], "flows_forwarded_delta": after["flows_forwarded"] - before["flows_forwarded"], "forward_failures": after["forward_failures"]},
                    "indexed_by_sourcetype": {r["sourcetype"]: int(r["count"]) for r in rows}, "indexed_total": total, "decoded": {k: d.get(k) for k in ("flows", "sources", "dests", "protos", "bytes")},
                    "ok": stages.get("SPLUNK_OBSERVED") == "PROVEN" and stages.get("FIELDS_VERIFIED") == "PROVEN" and total > 0 and after["flows_forwarded"] > before["flows_forwarded"]}
        print(("PASS " if out[sid]["ok"] else "FAIL ") + sid, json.dumps({k: out[sid][k] for k in ("indexed_total", "collector", "decoded")}))
    p = ROOT / "docs/verification/evidence/flow/scenarios.json"
    p.write_text(json.dumps({"generated_utc": datetime.now(timezone.utc).isoformat(), "collector": "GoFlow2 v2.2.5 + repo forwarder (isolated Docker lab)", "scenarios": out}, indent=1) + "\n")


main()
