# PulseForge Sourcetype Coverage

Generated 2026-10-30 by `scripts/generate_coverage_report.py` from repository evidence (replaces the Phase 3 scanner output).

| Measure | Count | Of catalog |
|---|---|---|
| Cataloged sourcetypes | 348 | 100.0% |
| Vendor-native generator | 158 | 45.4% |
| Sample replay only | 143 | 41.1% |
| No generator | 47 | 13.5% |
| Format verified (byte-equal raw in Splunk) | 128 | 36.8% |
| Vendor TA validated (full or partial; Cisco ISE only, earlier lab) | 1 | 0.3% |
| Parsed by a real vendor TA in the isolated lab this phase (extraction of emitted fields, timestamps and tags; not CIM or detections) | 6 | 1.7% |
| Independently indexed (live evidence) | 136 | 39.1% |

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

## Reconciliation (origin arithmetic; internal-consistency check)

| Component | Count |
|---|---|
| Pre-Batch-5 native baseline (re-derived with the ORIGINAL scanner rules and the pre-Batch-5 registries; not a recorded historical number) | 112 |
| + Scanner discovery corrections (generators that already existed) | +6 (cisco:catalyst:clienthealth, cisco:duo:remote:vpn, meraki:assurancealerts, netspout:snmp:poll, netspout:snmp:trap, pan:system) |
| + Batch 5 net new (registered 31; already native: cisco:sdwan:BGP-5-ADJCHANGE) | +30 |
| + Batch 6 net new (registered 10) | +10 |
| **Native generators now** | **158** |

The sum closes largely by construction (corrections and batch net-new are defined as set differences), so it checks that no sourcetype is counted twice or dropped; it is not an independent historical audit. Registries added after Batch 6 would be treated as part of the baseline until this function is extended.

Partition: native + sample-replay-only + no-generator = 158 + 143 + 47 = 348 (disjoint).

Evidence overlaps (a sourcetype is counted once per measure; measures are independent):

| Overlap | Count |
|---|---|
| Byte-verified AND native | 128 |
| Byte-verified but NOT native (verified through a retired or fixture path) | 0 |
| Native but never byte-verified | 30 |
| Independently indexed AND byte-verified | 128 |
| Independently indexed but NOT byte-verified (run-evidence files only) | 8 |
| Byte-verified but no live-indexing record (offline/current-fixture equality only) | 0 |
| Independently indexed with ROW-LEVEL proof (indexed_rows>0 or per-row matches>=1) | 76 |
| Independently indexed on FILE-LEVEL harness evidence only (older result files without row counts) | 52 |

Definition change: the earlier report counted only result files whose NAME contained 'live' (105). Every result file is written by a harness that posts to HEC and searches Splunk, so the measure now counts all of them (136 = file-level), and the row above separates what has row-level proof. The increase is a correction of an undercount, not new indexing.

## Reachability of native generators (a formatter existing is not the same as a customer being able to run it)

| Customer-facing path | Native sourcetypes reachable |
|---|---|
| Single Event / Sourcetype generator modes (native registries UB1-UB6) | 76 |
| Authentic scenario packs (`/api/generate/scenario-pack`, Explorer `scenario_pack`) emit them | 118 |
| Listed by a ScenarioRunner scenario (label-level; the runner may use a different formatter) | 29 |
| **Native but on none of the above** | **2** |

Native but not reachable from any listed path: sc4snmp:event, snmp:trap

Single Event / Sourcetype modes serve native registries for UB1-UB6 sourcetypes only; elsewhere they serve sample files. 87 active catalog sourcetypes used to be answered with an unrelated vendor-level sample and now report TELEMETRY_NOT_GROUNDED (the fallback is limited to vendors with a single active sourcetype). The script does not verify which other path serves a given sourcetype beyond the three rows above.

## Reconciliation notes

* Batch 5 registers 31 sourcetypes but added 30 to the count: `cisco:sdwan:BGP-5-ADJCHANGE` already had a native formatter (`format_cisco_sdwan_bgp_log`), so it now has two generators. Not a counting defect.
* Each of the six corrections was inspected by hand, not just pattern-matched: `pan:system` is emitted by `PanOsGenerator` (`SOURCETYPE_BY_TYPE['SYSTEM']` used when building the LogEntry, 17 documented fields); `netspout:snmp:trap` / `netspout:snmp:poll` are set on the normalized events built in `snmp_splunk_e2e.py` (live E2E evidence exists); `cisco:duo:remote:vpn`, `cisco:catalyst:clienthealth` and `meraki:assurancealerts` are the default `sourcetype` of `format_cisco_duo_vpn_log`, `format_cisco_catalyst_wlan_rf_log` and `format_meraki_alert_log` in `log_engine.py`. Pattern matching alone would also hit comments and lookups, so any future correction needs the same inspection.
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
