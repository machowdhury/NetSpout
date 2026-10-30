#!/usr/bin/env python3
"""Batch 7 byte-fidelity check in the ISOLATED validation lab (tests/lab/ta_validation; credentials from git-ignored .env.lab, never printed).

Sends each nginx:plus:access family once over HEC /event and reads it back by an independent search: indexed _raw must equal the submitted
bytes and carry the submitted sourcetype. No TA is installed for NGINX in this lab, so parsing/CIM are NOT checked.
Usage: python scripts/verify_batch7_live.py [--out catalog/universe_batch7_live_raw_equality_results.json]
"""
import argparse
import hashlib
import json
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
import validate_ta_windows as lab  # noqa: E402  (reuses its lab helpers; the module only reads .env.lab on import)


def main(out):
    from netspout_core.models import Node, NodeType
    from netspout_core.universe_batch7_engine import UniverseBatch7Engine as E, batch_registry
    run = uuid.uuid4().hex[:8]
    dev = Node(id="ub7-live", name="collector.example.test", type=NodeType.WEB_SERVER, ip_address="10.20.1.16")
    sent = []
    for f in batch_registry()["sources"][0]["families"]:
        host = "ub7-%s-%s" % (run, f["id"])
        raw = E.format_universe_batch7_log(dev, "nginx:plus:access", f["id"], when=datetime.now(timezone.utc)).raw_log
        lab.hec("/services/collector/event", {"event": raw, "sourcetype": "nginx:plus:access", "source": "pulseforge:batch7", "host": host, "index": lab.INDEX, "time": time.time()})
        sent.append((host, f["id"], raw))
    rows = []
    for _ in range(20):
        rows = lab.search('search index=%s host="ub7-%s-*" | table host _raw sourcetype source' % (lab.INDEX, run), earliest="-15m")
        if len(rows) >= len(sent):
            break
        time.sleep(3)
    by = {r["host"]: r for r in rows}
    checks = []
    for host, fid, raw in sent:
        r = by.get(host)
        checks.append({"sourcetype": "nginx:plus:access", "verdict": "PASS" if (r and r["_raw"].encode() == raw.encode() and r["sourcetype"] == "nginx:plus:access") else "FAIL",
                       "matches": 1 if r else 0, "family": fid, "indexed": r is not None, "raw_equal": bool(r) and r["_raw"].encode() == raw.encode(), "sourcetype_equal": bool(r) and r["sourcetype"] == "nginx:plus:access",
                       "submitted_sha256": hashlib.sha256(raw.encode()).hexdigest(), "indexed_sha256": hashlib.sha256(r["_raw"].encode()).hexdigest() if r else None})
    ta = [e["name"] for e in json.loads(lab.mgmt("/services/apps/local?output_mode=json&count=0"))["entry"] if "nginx" in e["name"].lower()]
    doc = {"run": run, "splunk_version": json.loads(lab.mgmt("/services/server/info?output_mode=json"))["entry"][0]["content"]["version"], "posted": len(sent), "post_failures": [], "indexed_rows": len(rows), "lab": "tests/lab/ta_validation (isolated)", "events": len(sent), "indexed": sum(c["indexed"] for c in checks),
           "raw_equal": sum(c["raw_equal"] for c in checks), "sourcetype_equal": sum(c["sourcetype_equal"] for c in checks), "nginx_ta_installed": ta, "ta_parsing_checked": False, "raw_equality": checks}
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(json.dumps(doc, indent=1) + "\n")
    print(json.dumps({k: doc[k] for k in ("splunk_version", "events", "indexed", "raw_equal", "sourcetype_equal", "nginx_ta_installed")}))
    return 0 if doc["raw_equal"] == doc["sourcetype_equal"] == doc["indexed"] == len(sent) else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "catalog/universe_batch7_live_raw_equality_results.json"))
    sys.exit(main(ap.parse_args().out))
