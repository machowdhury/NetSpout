#!/usr/bin/env python3
"""
NetSpout Gate 10: Live Splunk E2E Verification Script
Executes all 5 Wave 2 promoted scenarios against Docker Splunk HEC and REST API:
1. arch_lan_campus_access
2. arch_vpn_remote_workforce
3. service_provider_cisco
4. arch_wlan_meraki_catalyst
5. arch_man_carrier_ring

Verifies:
- Generated == Dispatched == Observed == Validated
- Controlled destination failure test on unreachable endpoint (Generated != Dispatched != Observed != Validated)
- Live Splunk REST investigation queries answering the 5 key questions per scenario.
"""
import os
import sys
import json
import urllib.request
import urllib.parse
import ssl

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

    import base64
    username = os.environ.get("SPLUNK_USERNAME", "")
    password = os.environ.get("SPLUNK_PASSWORD", "")
    if not username or not password:
        print("    [WARN] SPLUNK_USERNAME/SPLUNK_PASSWORD are not configured")
        return []
    auth_header = "Basic " + base64.b64encode(
        f"{username}:{password}".encode("utf-8")
    ).decode("ascii")

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


def main():
    transport = TelemetryTransportConfig(
        hec_enabled=True,
        hec_url="https://127.0.0.1:8888/services/collector",
        hec_token=os.environ.get("SPLUNK_HEC_TOKEN", ""),
        hec_index="idx_network_ops",
        hec_metric_index="cisco_mdt_metrics",
        hec_allow_insecure_tls=True
    )

    runner = ScenarioRunner()
    wave2_scenarios = [
        "arch_lan_campus_access",
        "arch_vpn_remote_workforce",
        "service_provider_cisco",
        "arch_wlan_meraki_catalyst",
        "arch_man_carrier_ring"
    ]

    print("================================================================================")
    print("NETSPOUT GATE 10: LIVE SPLUNK E2E VERIFICATION ACROSS WAVE 2 SCENARIOS")
    print("================================================================================")

    results = []
    run_ids = {}

    for scen in wave2_scenarios:
        req = ScenarioRunRequest(
            scenario_id=scen,
            dispatch_telemetry=True,
            transport_config=transport,
            time_mode="TEST",
            seed=42
        )
        manifest = runner.run_scenario(req)
        run_ids[scen] = manifest.run_id

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

    # -------------------------------------------------------------------------
    # PHASE 14: CONTROLLED DESTINATION FAILURE TEST
    # -------------------------------------------------------------------------
    print("\n================================================================================")
    print("PHASE 14: CONTROLLED DESTINATION FAILURE INTEGRITY TEST")
    print("================================================================================")
    bad_transport = TelemetryTransportConfig(
        hec_enabled=True,
        hec_url="https://127.0.0.1:19999/services/collector",  # Unreachable port
        hec_token=os.environ.get("SPLUNK_HEC_TOKEN", ""),
        hec_index="idx_network_ops",
        hec_allow_insecure_tls=True
    )
    fail_req = ScenarioRunRequest(
        scenario_id="arch_lan_campus_access",
        dispatch_telemetry=True,
        transport_config=bad_transport,
        time_mode="TEST",
        seed=999
    )
    fail_manifest = runner.run_scenario(fail_req)
    print(f"Testing Unreachable HEC on arch_lan_campus_access:")
    print(f"  Generated:             {fail_manifest.total_events_generated}")
    print(f"  Dispatch Attempted:    {fail_manifest.dispatch_attempted}")
    print(f"  Dispatch Succeeded:    {fail_manifest.dispatch_succeeded}")
    print(f"  Dispatch Failed:       {fail_manifest.dispatch_failed}")
    print(f"  Observed Count:        {fail_manifest.observed_count}")
    print(f"  Destination Validation:{fail_manifest.destination_validation}")
    print(f"  Overall Validation:    {fail_manifest.overall_validation}")

    dest_fail_passed = (
        fail_manifest.total_events_generated > 0 and
        fail_manifest.dispatch_succeeded == 0 and
        fail_manifest.observed_count == 0 and
        fail_manifest.destination_validation == "FAIL"
    )
    if dest_fail_passed:
        print("  [PASS] Controlled Destination Failure Verified: Generated != Dispatched != Observed != Validated")
    else:
        print("  [FAIL] Controlled Destination Failure Integrity Violated!")

    # -------------------------------------------------------------------------
    # PHASE 16: INVESTIGATION PROOF (5 SPL QUESTIONS PER SCENARIO)
    # -------------------------------------------------------------------------
    print("\n================================================================================")
    print("PHASE 16: INVESTIGATION PROOF (SPL QUERIES AGAINST LIVE SPLUNK EVIDENCE)")
    print("================================================================================")

    investigations = [
        {
            "scenario": "arch_lan_campus_access",
            "title": "Campus LAN: Rogue DHCP & Dynamic ARP Inspection",
            "questions": [
                ("Which switchport dropped unauthorized rogue DHCP traffic?",
                 f'search index=idx_network_ops netspout_run_id="{run_ids["arch_lan_campus_access"]}" DHCP_OFFER_DROPPED | head 1'),
                ("What port security violations caused switchport shutdown?",
                 f'search index=idx_network_ops netspout_run_id="{run_ids["arch_lan_campus_access"]}" ERR_DISABLE | head 1'),
                ("Did Cisco ISE enforce 802.1X TrustSec quarantine policy?",
                 f'search index=idx_network_ops netspout_run_id="{run_ids["arch_lan_campus_access"]}" sourcetype="cisco:ise:nac:8021x" action=blocked | head 1'),
                ("What client MAC and rogue IP triggered security alerts?",
                 f'search index=idx_network_ops netspout_run_id="{run_ids["arch_lan_campus_access"]}" rogue_ip=* OR "10.10.30.50" | head 1'),
                ("Did switchport GigabitEthernet1/0/12 recover to forwarding state?",
                 f'search index=idx_network_ops netspout_run_id="{run_ids["arch_lan_campus_access"]}" PORT_RESTORED status=restored | head 1')
            ]
        },
        {
            "scenario": "arch_vpn_remote_workforce",
            "title": "WAN VPN: Credential Stuffing & Duo Push Fraud",
            "questions": [
                ("What username and attacker IP originated the credential stuffing surge?",
                 f'search index=idx_network_ops netspout_run_id="{run_ids["arch_vpn_remote_workforce"]}" sourcetype="cisco:duo:remote:vpn" action=alerted | head 1'),
                ("Did the targeted corporate user report an unauthorized push as fraud?",
                 f'search index=idx_network_ops netspout_run_id="{run_ids["arch_vpn_remote_workforce"]}" sourcetype="cisco:duo:push:prompt" result=FRAUD | head 1'),
                ("What account lockout and perimeter firewall blocks were triggered?",
                 f'search index=idx_network_ops netspout_run_id="{run_ids["arch_vpn_remote_workforce"]}" action=blocked | head 1'),
                ("Which Cisco ASA gateway terminated the enterprise SSL-VPN tunnels?",
                 f'search index=idx_network_ops netspout_run_id="{run_ids["arch_vpn_remote_workforce"]}" sourcetype="cisco:asa" | head 1'),
                ("Did legitimate user authentication recover after credential reset?",
                 f'search index=idx_network_ops netspout_run_id="{run_ids["arch_vpn_remote_workforce"]}" status=restored | head 1')
            ]
        },
        {
            "scenario": "service_provider_cisco",
            "title": "Service Provider: BGP Collapse & TI-LFA Fast Reroute",
            "questions": [
                ("Which BGP peer adjacency collapsed due to carrier interface flap?",
                 f'search index=idx_network_ops netspout_run_id="{run_ids["service_provider_cisco"]}" event_type=BGP_DOWN | head 1'),
                ("Did TI-LFA sub-50ms fast reroute activate for the transit prefix?",
                 f'search index=idx_network_ops netspout_run_id="{run_ids["service_provider_cisco"]}" event_type=TI_LFA_REROUTE | head 1'),
                ("How many MDT streaming telemetry metrics were collected in the metric store during the flap?",
                 f'| mstats count where index=cisco_mdt_metrics metric_name=* AND netspout_run_id="{run_ids["service_provider_cisco"]}" | head 1'),
                ("What core transit route withdrawals propagated across the provider edge?",
                 f'search index=idx_network_ops netspout_run_id="{run_ids["service_provider_cisco"]}" signature="*Withdrawal*" | head 1'),
                ("Was BGP peering and MPLS transit restored to nominal state?",
                 f'search index=idx_network_ops netspout_run_id="{run_ids["service_provider_cisco"]}" event_type=BGP_UP status=restored | head 1')
            ]
        },
        {
            "scenario": "arch_wlan_meraki_catalyst",
            "title": "Wireless RF Health: CleanAir Interference & Air Marshal Suppression",
            "questions": [
                ("Which channel and access point suffered severe RF interference surge?",
                 f'search index=idx_network_ops netspout_run_id="{run_ids["arch_wlan_meraki_catalyst"]}" INTERFERENCE_SURGE | head 1'),
                ("What rogue AP SSID was identified by Catalyst and Meraki Air Marshal?",
                 f'search index=idx_network_ops netspout_run_id="{run_ids["arch_wlan_meraki_catalyst"]}" ssid=* | head 1'),
                ("Did CleanAir dynamic channel reassignment successfully mitigate RF utilization?",
                 f'search index=idx_network_ops netspout_run_id="{run_ids["arch_wlan_meraki_catalyst"]}" CHANNEL_SWITCH | head 1'),
                ("Was evil-twin rogue containment engaged by the wireless controller?",
                 f'search index=idx_network_ops netspout_run_id="{run_ids["arch_wlan_meraki_catalyst"]}" ROGUE_CONTAINED | head 1'),
                ("Did client SNR and noise floor normalize on the newly assigned channel?",
                 f'search index=idx_network_ops netspout_run_id="{run_ids["arch_wlan_meraki_catalyst"]}" RF_RESTORED | head 1')
            ]
        },
        {
            "scenario": "arch_man_carrier_ring",
            "title": "Metro Optical MAN: Fiber Cut & G.8032 ERPS Protection",
            "questions": [
                ("Which optical ring span and port detected physical signal failure from fiber cut?",
                 f'search index=idx_network_ops netspout_run_id="{run_ids["arch_man_carrier_ring"]}" event_type=SIGNAL_FAIL sourcetype="nokia:sros:syslog" | head 1'),
                ("Did adjacent Juniper MX ring routers receive R-APS Signal Fail frames?",
                 f'search index=idx_network_ops netspout_run_id="{run_ids["arch_man_carrier_ring"]}" sourcetype="juniper:junos" event_type=SIGNAL_FAIL | head 1'),
                ("Did the Ring Protection Link (RPL) unblock to restore MAN packet forwarding in sub-50ms?",
                 f'search index=idx_network_ops netspout_run_id="{run_ids["arch_man_carrier_ring"]}" event_type=RPL_UNBLOCK | head 1'),
                ("What alternate path status was confirmed by Arista metro leaf switches?",
                 f'search index=idx_network_ops netspout_run_id="{run_ids["arch_man_carrier_ring"]}" host="*Arista*" status=mitigated | head 1'),
                ("Did the ring transition to revertive restoration upon WTR timer expiry?",
                 f'search index=idx_network_ops netspout_run_id="{run_ids["arch_man_carrier_ring"]}" event_type=REVERTIVE_RESTORE | head 1')
            ]
        }
    ]

    all_investigations_passed = True
    for inv in investigations:
        print(f"\n--- {inv['scenario']} ({inv['title']}) ---")
        for q_idx, (q_text, q_spl) in enumerate(inv["questions"], start=1):
            rows = execute_splunk_rest_query(q_spl, max_results=1)
            if rows:
                row_preview = {k: v for k, v in rows[0].items() if not k.startswith("_") and k != "raw"}
                print(f"  Q{q_idx}: {q_text}")
                print(f"      SPL: {q_spl}")
                print(f"      [ANSWER PROVEN VIA SPLUNK]: {row_preview}")
            else:
                print(f"  Q{q_idx}: {q_text}")
                print(f"      SPL: {q_spl}")
                print(f"      [WARN] No results returned from Splunk!")
                all_investigations_passed = False

    # -------------------------------------------------------------------------
    # SCORECARD SUMMARY
    # -------------------------------------------------------------------------
    print("\n================================================================================")
    print("LIVE E2E SCORECARD TABLE (WAVE 2)")
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
    if all_passed and dest_fail_passed and all_investigations_passed:
        print("✅ ALL 5 WAVE 2 SCENARIOS PASSED LIVE SPLUNK E2E VERIFICATION (100% INVARIANT)")
        return 0
    else:
        print("❌ ONE OR MORE SCENARIOS FAILED LIVE VERIFICATION")
        return 1


if __name__ == "__main__":
    sys.exit(main())
