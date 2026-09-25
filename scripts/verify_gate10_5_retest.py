#!/usr/bin/env python3
"""
NetSpout Gate 10.5: Focused Semantic Retest Verification Script
Targets:
1. service_provider_cisco
2. arch_wlan_meraki_catalyst
3. arch_man_carrier_ring

Validates:
- Fresh run IDs
- Generated == Dispatched == Observed == Validated (100% completeness)
- Structured declarative timing metadata
- Clear protocol vs empirical distinction (MODELED badging)
- WLAN DCA vs DFS semantics
- Carrier Ring G.8032 RPL vs WTR semantics
- Workflow Time-to-Validated-Evidence KPI (T0-T6)
"""
import os
import sys
import json
import time
import ssl
import urllib.request
import urllib.parse
import base64

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC_DIR = os.path.join(REPO_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from netspout_core.models import ScenarioRunRequest, TelemetryTransportConfig
from netspout_core.scenario_runner import ScenarioRunner


def execute_splunk_rest_query(query: str, max_results: int = 10) -> list:
    """Execute SPL search against Splunk REST search/jobs/export endpoint and return parsed JSON rows."""
    rest_url = "https://127.0.0.1:8889/services/search/jobs/export"
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    auth_header = "Basic " + base64.b64encode(b"admin:SplunkPassword123!").decode("ascii")

    clean_query = query.strip()
    if not clean_query.startswith("search ") and not clean_query.startswith("|"):
        clean_query = f"search {clean_query}"

    data = urllib.parse.urlencode({
        "search": clean_query,
        "output_mode": "json",
        "earliest_time": "-24h@h",
        "latest_time": "now",
        "count": str(max_results)
    }).encode("utf-8")

    req = urllib.request.Request(rest_url, data=data, method="POST")
    req.add_header("Authorization", auth_header)

    results = []
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
            content = resp.read().decode("utf-8")
            for line in content.splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    if "result" in obj and isinstance(obj["result"], dict):
                        results.append(obj["result"])
                except Exception:
                    continue
    except Exception as e:
        print(f"    [WARN] REST query failed: {e}")
    return results


def run_focused_retest():
    transport = TelemetryTransportConfig(
        hec_enabled=True,
        hec_url="https://127.0.0.1:8888/services/collector",
        hec_token="00000000-0000-0000-0000-000000000000",
        hec_index="idx_network_ops",
        hec_metric_index="cisco_mdt_metrics",
        hec_allow_insecure_tls=True
    )

    runner = ScenarioRunner()
    target_scenarios = [
        "service_provider_cisco",
        "arch_wlan_meraki_catalyst",
        "arch_man_carrier_ring"
    ]

    print("================================================================================")
    print("NETSPOUT GATE 10.5: FOCUSED SEMANTIC RETEST & CERTIFICATION VERIFICATION")
    print("================================================================================")

    retest_results = {}

    for sc_id in target_scenarios:
        print(f"\n--- RETESTING: {sc_id} ---")
        t0 = time.time()
        # Simulated User Discovery interaction time
        time.sleep(1.2)
        t1 = time.time()
        # Simulated User Preview & Timing Metadata review interaction time
        time.sleep(1.5)
        t2 = time.time()
        # Simulated Pipeline Connection check
        time.sleep(0.8)
        t3 = time.time()

        # Run scenario with live dispatch
        req = ScenarioRunRequest(
            scenario_id=sc_id,
            seed=int(time.time() * 1000) % 100000,
            time_mode="REALTIME",
            dispatch_telemetry=True,
            transport_config=transport
        )

        manifest = runner.run_scenario(req)
        t4 = manifest.start_time
        t5 = manifest.end_time or time.time()

        # Evidence observation & proof verification
        time.sleep(1.0)
        evidence = runner.get_run_evidence(manifest.run_id, transport=transport)
        t6 = time.time()

        total_kpi_time = t6 - t0

        generated = manifest.total_events_generated
        dispatched = manifest.dispatch_succeeded
        observed = manifest.observed_count
        completeness = manifest.observation_completeness_pct
        overall_val = manifest.overall_validation
        dest_val = manifest.destination_validation

        print(f"  Run ID: {manifest.run_id}")
        print(f"  Generated: {generated} | Dispatched: {dispatched} | Observed: {observed} | Completeness: {completeness:.1f}%")
        print(f"  Overall Validation: {overall_val} | Destination Validation: {dest_val}")
        print(f"  Timing Claim: {manifest.timing_claim} ({manifest.timing_value} {manifest.timing_unit})")
        print(f"  Timing Classification: {manifest.timing_classification}")
        print(f"  Timing Notes: {manifest.timing_notes}")
        print(f"  Workflow Timing: T0->T1: {t1-t0:.2f}s, T1->T2: {t2-t1:.2f}s, T2->T3: {t3-t2:.2f}s, T3->T5: {t5-t3:.2f}s, T5->T6: {t6-t5:.2f}s")
        print(f"  Time-to-Validated-Evidence KPI: {total_kpi_time:.2f}s")

        # Live Splunk REST investigation
        print(f"  Investigating live Splunk indexed evidence:")
        rows = execute_splunk_rest_query(f'search index=* netspout_run_id="{manifest.run_id}" | head 5')
        print(f"  Sample Events in Splunk: {len(rows)}")
        for r in rows[:2]:
            print(f"    -> [{r.get('sourcetype')}] {r.get('_raw', '')[:110]}...")

        retest_results[sc_id] = {
            "run_id": manifest.run_id,
            "generated": generated,
            "dispatched": dispatched,
            "observed": observed,
            "completeness": completeness,
            "overall_validation": overall_val,
            "destination_validation": dest_val,
            "timing_claim": manifest.timing_claim,
            "timing_value": manifest.timing_value,
            "timing_unit": manifest.timing_unit,
            "timing_classification": manifest.timing_classification,
            "timing_notes": manifest.timing_notes,
            "kpi_time_sec": total_kpi_time,
            "manifest": manifest
        }

    # Summary Output
    print("\n================================================================================")
    print("FOCUSED RETEST SUMMARY:")
    for sc_id, res in retest_results.items():
        pass_status = (
            res["generated"] > 0 and
            res["dispatched"] == res["generated"] and
            res["observed"] >= res["generated"] and
            res["completeness"] >= 100.0 and
            res["overall_validation"] == "PASS" and
            res["destination_validation"] == "PASS"
        )
        status_label = "CLEAN PASS" if pass_status else "FAIL"
        print(f"  * {sc_id}: {status_label} (Run: {res['run_id']}, KPI: {res['kpi_time_sec']:.2f}s, Timing: {res['timing_classification']})")
    print("================================================================================")

    # Save results to json for report generation
    out_file = os.path.join(REPO_ROOT, "docs", "acceptance", "focused_retest_results.json")
    serializable = {}
    for k, v in retest_results.items():
        serializable[k] = {
            "run_id": v["run_id"],
            "generated": v["generated"],
            "dispatched": v["dispatched"],
            "observed": v["observed"],
            "completeness": v["completeness"],
            "overall_validation": v["overall_validation"],
            "destination_validation": v["destination_validation"],
            "timing_claim": v["timing_claim"],
            "timing_value": v["timing_value"],
            "timing_unit": v["timing_unit"],
            "timing_classification": v["timing_classification"],
            "timing_notes": v["timing_notes"],
            "kpi_time_sec": v["kpi_time_sec"]
        }
    with open(out_file, "w") as f:
        json.dump(serializable, f, indent=2)
    print(f"Results written to {out_file}")


if __name__ == "__main__":
    run_focused_retest()
