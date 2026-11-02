#!/usr/bin/env python3
"""PulseForge Phase 4C — control / scenario live acceptance driver.

Executes the real production ``ScenarioRunner`` against the authorized local Docker
Splunk lab, then independently verifies what Splunk actually indexed (events with
SPL, metrics with ``| mstats``). Emits a JSON evidence record that reconciles
generated -> dispatched -> indexed counts.

This deliberately does NOT trust HEC HTTP 200 as proof of ingestion.

Usage:
  backend/venv/bin/python scripts/phase4c_control_run.py \
      --scenario cisco_aci_microburst --seed 42001 --out evidence.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "backend"))

from pf_lab_query import run_spl, metric_names_from_mstats, count_metric_points  # noqa: E402


def build_transport():
    from netspout_core.models import TelemetryTransportConfig
    return TelemetryTransportConfig(
        hec_url=os.environ.get("PF_HEC_URL", "https://127.0.0.1:18088/services/collector"),
        hec_token=os.environ.get("PULSEFORGE_LAB_HEC_TOKEN", ""),
        hec_index=os.environ.get("PF_EVENT_INDEX", "idx_network_ops"),
        hec_metric_index=os.environ.get("PF_METRIC_INDEX", "idx_performance_metrics"),
        hec_ssl_verify=False,
        hec_allow_insecure_tls=True,
    )


def run_and_verify(scenario_id: str, seed: int, wait_seconds: int = 90):
    from netspout_core.scenario_runner import ScenarioRunner
    from netspout_core.models import ScenarioRunRequest

    transport = build_transport()
    t0 = time.time()
    runner = ScenarioRunner()
    req = ScenarioRunRequest(scenario_id=scenario_id, seed=seed,
                             dispatch_telemetry=True, transport_config=transport)
    manifest = runner.run_scenario(req)
    gen_seconds = time.time() - t0
    run_id = manifest.run_id

    m = manifest.model_dump() if hasattr(manifest, "model_dump") else dict(manifest.__dict__)
    m.update({
        "scenario_id": scenario_id,
        "run_id": run_id,
        "seed": seed,
        "generation_wall_seconds": round(gen_seconds, 2),
        "event_index": transport.hec_index,
        "metric_index": transport.hec_metric_index,
        "hec_url": transport.hec_url,
        "started_at_utc": datetime.fromtimestamp(t0, tz=timezone.utc).isoformat(),
    })

    entries = runner.run_logs.get(run_id, [])
    by_st = {}
    metric_points_generated = 0
    for e in entries:
        st = e.sourcetype or "generic"
        by_st[st] = by_st.get(st, 0) + 1
        raw = e.raw_log
        obj = None
        if isinstance(raw, str):
            try:
                obj, _ = json.JSONDecoder().raw_decode(raw.lstrip())
            except Exception:
                obj = None
        elif isinstance(raw, dict):
            obj = raw
        if isinstance(obj, dict):
            if isinstance(obj.get("data"), dict):
                metric_points_generated += sum(
                    1 for v in obj["data"].values()
                    if isinstance(v, (int, float)) and not isinstance(v, bool))
            if isinstance(obj.get("fields"), dict):
                metric_points_generated += sum(
                    1 for v in obj["fields"].values()
                    if isinstance(v, (int, float)) and not isinstance(v, bool))
    m["generated_records"] = len(entries)
    m["generated_by_sourcetype"] = by_st
    m["generated_metric_points"] = metric_points_generated

    accepted = rejected = 0
    reject_reasons = []
    for eid, res in (m.get("dispatch_results") or {}).items():
        h = (res or {}).get("hec") or {}
        if h.get("success"):
            accepted += 1
        else:
            rejected += 1
            reject_reasons.append(str(h.get("message") or h.get("error_class") or "unknown"))
    m["hec_accepted_records"] = accepted
    m["hec_rejected_records"] = rejected
    m["hec_reject_reasons"] = sorted(set(reject_reasons))[:10]

    # ---- independent Splunk verification -------------------------------------
    earliest = datetime.fromtimestamp(t0 - 300, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000+0000")
    event_spl = f'index=* netspout_run_id="{run_id}" | stats count by sourcetype, index'
    idx_rows = []
    deadline = time.time() + wait_seconds
    while time.time() < deadline:
        time.sleep(6)
        idx_rows = run_spl(event_spl, earliest=earliest)
        if idx_rows:
            break

    indexed_total = sum(int(r.get("count", 0)) for r in idx_rows)
    m["indexed_event_records"] = indexed_total
    m["indexed_by_sourcetype"] = {r["sourcetype"]: int(r["count"]) for r in idx_rows}
    m["indexed_indexes"] = sorted({r["index"] for r in idx_rows if r.get("index")})
    m["event_spl"] = event_spl
    m["event_spl_rows"] = idx_rows

    mstats_spl = (f'| mstats avg(*) span=1m where index={transport.hec_metric_index} '
                  f'netspout_run_id="{run_id}"')
    mrows = run_spl(mstats_spl, earliest=earliest)
    m["metric_query_spl"] = mstats_spl
    m["indexed_metric_rows"] = mrows
    m["indexed_metric_names"] = metric_names_from_mstats(mrows)
    m["indexed_metric_points"] = count_metric_points(mrows)

    # per-metric-name breakdown, for name-level reconciliation
    name_spl = (f'| mstats avg(*) span=1m where index={transport.hec_metric_index} '
                f'netspout_run_id="{run_id}" | outputstats collapse=t')
    try:
        m["metric_query_spl_extended_rows"] = run_spl(name_spl, earliest=earliest)
    except Exception:
        m["metric_query_spl_extended_rows"] = []

    print(f"[{scenario_id}] run_id={run_id} seed={seed} "
          f"generated={len(entries)} hec_ok={accepted} hec_fail={rejected} | "
          f"indexed_events={indexed_total} metric_points={m['indexed_metric_points']} "
          f"metrics={m['indexed_metric_names']}", file=sys.stderr)
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", default="cisco_aci_microburst")
    ap.add_argument("--seed", type=int, default=int(time.time()) % 100000)
    ap.add_argument("--wait", type=int, default=90)
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    evidence = run_and_verify(args.scenario, args.seed, args.wait)
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w") as fh:
            json.dump(evidence, fh, indent=1, default=str)
        print(f"[out] {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
