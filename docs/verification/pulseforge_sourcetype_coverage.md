# PulseForge Sourcetype Coverage

Generated 2026-10-30 by `scripts/generate_coverage_report.py` from repository evidence (replaces the Phase 3 scanner output).

| Measure | Count | Of catalog |
|---|---|---|
| Cataloged sourcetypes | 348 | 100.0% |
| Vendor-native generator | 158 | 45.4% |
| Sample replay only | 143 | 41.1% |
| No generator | 47 | 13.5% |
| Format verified (byte-equal raw in Splunk) | 128 | 36.8% |
| Vendor TA validated (full or partial) | 1 | 0.3% |
| Independently indexed (live evidence) | 105 | 30.2% |

Tier definitions are in the script header. `TA validated` counts only a parser that was installed and exercised; mapping-only assessments are not counted. `Sample replay only` is recorded-event replay, not a vendor-native formatter.

## Vendors with the most uncovered sourcetypes

| Vendor | Cataloged | Native generator |
|---|---|---|
| cisco_catalyst | 34 | 7 |
| splunk | 21 | 2 |
| nutanix | 16 | 0 |
| cisco_meraki | 17 | 2 |
| cisco_ios | 26 | 13 |
| cisco_intersight | 11 | 0 |
| cisco_duo | 10 | 2 |
| fortinet | 8 | 1 |
| aruba_cx | 6 | 0 |
| cisco_ise | 7 | 1 |
| cisco_aci | 8 | 4 |
| netskope | 4 | 0 |
| radware | 4 | 0 |
| zscaler_zia | 6 | 2 |
| arista_eos | 4 | 1 |

## Reconciliation notes

* Batch 5 registers 31 sourcetypes but added 30 to the count: `cisco:sdwan:BGP-5-ADJCHANGE` already had a native formatter (`format_cisco_sdwan_bgp_log`), so it now has two generators. Not a counting defect.
* Scanner fix (Batch 6 pass): sourcetypes declared as default arguments (`sourcetype: str = "..."`) and in dedicated generator modules (panos_generator.py, snmp_splunk_e2e.py) were missed, which hid `pan:system`, `cisco:duo:remote:vpn`, `cisco:catalyst:clienthealth`, `meraki:assurancealerts`, `netspout:snmp:poll` and `netspout:snmp:trap` (+6).
* Hand-authored fault-injection templates exist for 5 more sourcetypes (arista:eos:syslog, cisco:duo:auth, dell:os10:syslog, fortinet:fortigate:event, juniper:junos:syslog) but no format reference backs them, so they are not counted as vendor-native.
* The 70% target (244 of 348) is not reachable on current evidence: the remaining sample-replay rows are demo-authored or empty-poller captures, and the no-generator rows have no authentic reference. See the backlog for the exact blockers.

## Native generators by vendor (top 15 by catalog size)

| Vendor | Cataloged | Native | Format verified | Indexed |
|---|---|---|---|---|
| cisco_sdwan | 41 | 38 | 37 | 37 |
| cisco_catalyst | 34 | 7 | 4 | 5 |
| cisco_ios | 26 | 13 | 7 | 8 |
| splunk | 21 | 2 | 0 | 0 |
| cisco_meraki | 17 | 2 | 1 | 1 |
| nutanix | 16 | 0 | 0 | 0 |
| cisco_intersight | 11 | 0 | 0 | 0 |
| cisco_duo | 10 | 2 | 1 | 1 |
| cisco_aci | 8 | 4 | 2 | 4 |
| fortinet | 8 | 1 | 0 | 0 |
| microsoft_windows | 8 | 8 | 8 | 8 |
| cisco_ise | 7 | 1 | 0 | 0 |
| aruba_cx | 6 | 0 | 0 | 0 |
| cisco_asa | 6 | 4 | 3 | 3 |
| sc4snmp | 6 | 3 | 0 | 1 |
