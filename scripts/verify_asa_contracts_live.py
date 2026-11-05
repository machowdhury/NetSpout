#!/usr/bin/env python3
"""Run the ASA-containing scenario contracts (lateral_movement, normal_traffic) through the product's HEC dispatcher into the isolated TA lab and execute their
dashboard searches. Three arms per contract, same searches counted by rows returned:
  A  current dispatcher (TA-owned sourcetypes send no bare NetSpout fields) + current dashboard searches
  B  legacy dispatcher behaviour (bare fields only, no netspout_* copies) + current searches            -> backward compatibility of the new searches
  C  current dispatcher + the dashboard searches as committed before this change (git HEAD)          -> what the dashboard change fixes
Lab credentials come from the git-ignored env file and are never printed.   python scripts/verify_asa_contracts_live.py ENVFILE OUT.json
"""
import json
import re
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
import ta_compat  # noqa: E402
from netspout_core import scenario_contracts, telemetry_dispatcher as td  # noqa: E402
from netspout_core.models import TelemetryTransportConfig  # noqa: E402

INDEX = "dev_test_replay"
VIEWS = ROOT / "netspout/default/data/ui/views"


def searches(text):
    d = json.loads(re.search(r"<definition><!\[CDATA\[(.*?)\]\]></definition>", text, re.S).group(1))
    return {k: x["options"]["query"] for k, x in d["dataSources"].items() if x.get("type", "").endswith("ds.search")}, d


def sub(q, run, phase="*"):
    q = q.replace("$index_tok$", INDEX).replace("$mindex_tok$", INDEX + "_metrics").replace("$run_tok$", run).replace("$phase_tok$", phase)
    q = re.sub(r"\$[A-Za-z_][\w.]*\$", "*", q)
    return q if q.strip().startswith(("|", "search")) else "search " + q


def deliver(contract, lab, legacy):
    run = "p4-%s-%s" % ("legacy" if legacy else "ta", uuid.uuid4().hex[:8])
    entries = scenario_contracts.generate(contract, run_id=run, seed=7)
    cfg = TelemetryTransportConfig(hec_url="https://127.0.0.1:%s/services/collector/event" % lab.hec_port, hec_token=lab.token, hec_index=INDEX, hec_ssl_verify=False, hec_allow_insecure_tls=True)
    saved = (td.TA_PARSED_SOURCETYPES, td.NETSPOUT_NAMESPACED_FIELDS)
    if legacy:
        td.TA_PARSED_SOURCETYPES, td.NETSPOUT_NAMESPACED_FIELDS = frozenset(), ()
    try:
        ok = sum(bool(td.dispatcher.dispatch_log(e, cfg)["hec"]["success"]) for e in entries)
    finally:
        td.TA_PARSED_SOURCETYPES, td.NETSPOUT_NAMESPACED_FIELDS = saved
    rows = lab.wait_count("index=%s netspout_run_id=%s | stats count" % (INDEX, run), 1)
    n = 0
    for _ in range(10):
        r = lab.search("index=%s netspout_run_id=%s | stats count" % (INDEX, run), earliest="-1h")
        n = int(r[0]["count"]) if r else 0
        if n >= len(entries):
            break
        import time; time.sleep(3)
    return run, len(entries), ok, n


def rowcounts(qs, lab, run):
    out = {}
    for k, q in qs.items():
        res = lab.search(sub(q, run), earliest="-2h")
        out[k] = {"rows": len(res), "error": res[0]["error"][:100] if res and "error" in res[0] else None}
    return out


def main(env, out):
    lab = ta_compat.Lab(env)
    result = {}
    for cid in ("lateral_movement", "normal_traffic"):
        new_qs, _ = searches((VIEWS / ("pf_%s.xml" % cid)).read_text())
        old_qs, _ = searches(subprocess.check_output(["git", "show", "HEAD:netspout/default/data/ui/views/pf_%s.xml" % cid], cwd=ROOT, text=True))
        runA, nA, okA, ixA = deliver(cid, lab, legacy=False)
        runB, nB, okB, ixB = deliver(cid, lab, legacy=True)
        A, B, C = rowcounts(new_qs, lab, runA), rowcounts(new_qs, lab, runB), rowcounts(old_qs, lab, runA)
        changed = [k for k in new_qs if new_qs[k] != old_qs.get(k)]
        asa = lab.search('index=%s netspout_run_id=%s sourcetype="cisco:asa" | eval s=coalesce(netspout_status,status), a=coalesce(netspout_action,action) | stats count by s, a' % (INDEX, runA), earliest="-2h")
        asa_old = lab.search('index=%s netspout_run_id=%s sourcetype="cisco:asa" | stats count by status, action, signature' % (INDEX, runA), earliest="-2h")
        result[cid] = {"streams": scenario_contracts.sourcetypes(scenario_contracts.get(cid)),
                       "arm_A_current": {"run_id": runA, "generated": nA, "hec_accepted": okA, "indexed": ixA}, "arm_B_legacy_fields": {"run_id": runB, "generated": nB, "hec_accepted": okB, "indexed": ixB},
                       "changed_searches": changed, "searches": len(new_qs),
                       "rows_new_searches_on_TA_owned_data": A, "rows_new_searches_on_legacy_data": B, "rows_old_searches_on_TA_owned_data": C,
                       "asa_events_seen_by_new_phase_panels": asa, "asa_events_seen_by_old_phase_panels (status, action, signature)": asa_old,
                       "errors": [k for d in (A, B, C) for k, v in d.items() if v["error"]]}
        diffs = {k: (A[k]["rows"], B[k]["rows"], C[k]["rows"]) for k in changed}
        print(cid, "A", nA, okA, ixA, "| B", nB, okB, ixB, "| changed searches rows (new/TA, new/legacy, old/TA):", diffs, "| errors:", result[cid]["errors"])
    Path(out).write_text(json.dumps(result, indent=1) + "\n")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
