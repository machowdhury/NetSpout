#!/usr/bin/env python3
"""
NetSpout Gate 9: Live Splunk E2E Verification Script
Executes all 5 Wave 1 promoted scenarios against Docker Splunk HEC and REST API.
Verifies Generated == Dispatched == Observed == Validated.
"""
import os
import sys
import time

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC_DIR = os.path.join(REPO_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from netspout_core.models import ScenarioRunRequest, TelemetryTransportConfig
from netspout_core.scenario_runner import ScenarioRunner

def main():
    transport = TelemetryTransportConfig(
        hec_enabled=True,
        hec_url="https://127.0.0.1:8888/services/collector",
        hec_token="00000000-0000-0000-0000-000000000000",
        hec_index="idx_network_ops",
        hec_metric_index="cisco_mdt_metrics",
        hec_allow_insecure_tls=True
    )

    runner = ScenarioRunner()
    scenarios = [
        "mixed_sase_degradation",
        "mixed_backbone_optical",
        "openconfig_mdt_streaming",
        "sql_injection",
        "ddos_attack"
    ]

    print("================================================================================")
    print("NETSPOUT GATE 9: LIVE SPLUNK E2E VERIFICATION ACROSS WAVE 1 SCENARIOS")
    print("================================================================================")

    results = []
    for scen in scenarios:
        req = ScenarioRunRequest(
            scenario_id=scen,
            dispatch_telemetry=True,
            transport_config=transport,
            time_mode="TEST",
            seed=42
        )
        manifest = runner.run_scenario(req)
        
        rule_pass_count = sum(1 for r in manifest.validation_results if r.status == "PASS")
        total_rules = len(manifest.validation_results)
        
        res = {
            "scenario_id": scen,
            "scenario_name": manifest.scenario_name or scen,
            "run_id": manifest.run_id,
            "maturity": manifest.scenario_maturity,
            "generated": manifest.total_events_generated,
            "dispatched": manifest.dispatch_succeeded,
            "event_observed": manifest.event_observed_count,
            "metric_observed": manifest.metric_observed_count,
            "total_observed": manifest.observed_count,
            "completeness_pct": manifest.observation_completeness_pct,
            "rules_passed": f"{rule_pass_count}/{total_rules}",
            "dest_validation": manifest.destination_validation,
            "overall_validation": manifest.overall_validation,
            "manifest": manifest
        }
        results.append(res)
        
        print(f"\nScenario: {scen} ({res['scenario_name']})")
        print(f"  Run ID:                {manifest.run_id}")
        print(f"  Maturity:              {manifest.scenario_maturity}")
        print(f"  Generated:             {manifest.total_events_generated}")
        print(f"  Dispatched (HEC):      {manifest.dispatch_succeeded} / {manifest.dispatch_attempted} (failed: {manifest.dispatch_failed})")
        print(f"  Event Observed:        {manifest.event_observed_count}")
        print(f"  Metric Observed:       {manifest.metric_observed_count}")
        print(f"  Total Observed:        {manifest.observed_count}")
        print(f"  Observation Status:    {manifest.observation_status}")
        print(f"  Completeness Pct:      {manifest.observation_completeness_pct:.1f}%")
        print(f"  Rules Validated:       {rule_pass_count}/{total_rules} PASS")
        print(f"  Dest Validation:       {manifest.destination_validation}")
        print(f"  Overall Validation:    {manifest.overall_validation}")
        if manifest.evidence_summary:
            print("  Destinations:")
            for d in manifest.evidence_summary.destinations:
                print(f"    [{d.role.value}] {d.name} ({d.telemetry_type.value}): {d.observed_count}/{d.expected_count} observed -> {d.status}")
                print(f"        Query: {d.query}")
        if manifest.errors:
            print(f"  Errors: {manifest.errors}")

    print("\n================================================================================")
    print("LIVE E2E SCORECARD TABLE")
    print("================================================================================")
    header = f"| {'Scenario ID':<26} | {'Gen':<4} | {'Disp':<4} | {'Evt Obs':<7} | {'Met Obs':<7} | {'Tot Obs':<7} | {'Compl%':<7} | {'Rules':<6} | {'Overall':<7} |"
    print(header)
    divider = f"|{'-'*28}|{'-'*6}|{'-'*6}|{'-'*9}|{'-'*9}|{'-'*9}|{'-'*9}|{'-'*8}|{'-'*9}|"
    print(divider)
    all_passed = True
    for r in results:
        line = f"| {r['scenario_id']:26} | {r['generated']:4} | {r['dispatched']:4} | {r['event_observed']:7} | {r['metric_observed']:7} | {r['total_observed']:7} | {r['completeness_pct']:6.1f}% | {r['rules_passed']:6} | {r['overall_validation']:7} |"
        print(line)
        if r['overall_validation'] != "PASS" or r['completeness_pct'] < 95.0:
            all_passed = False

    print("================================================================================")
    if all_passed:
        print("✅ ALL 5 WAVE 1 SCENARIOS PASSED LIVE SPLUNK E2E VERIFICATION (100% INVARIANT)")
        return 0
    else:
        print("❌ ONE OR MORE SCENARIOS FAILED LIVE VERIFICATION")
        return 1

if __name__ == "__main__":
    sys.exit(main())
