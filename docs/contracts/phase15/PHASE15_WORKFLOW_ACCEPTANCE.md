# Phase 15 — end-to-end workflow acceptance (installed Splunk Web UI, lab `nsp15`)

Every workflow ran in Chromium through Splunk Web and the app's gateway to the engine, then HEC to the real Splunk, and was confirmed by an **independent Splunk search** (events) or `mstats` (metrics) by run id. Nothing below is reported Verified on HEC acceptance alone. Packaged suite: **29/29** (asa 11, ios 1, fortinet 1, pan 3, metrics 4, multi 8, engine 1). The first run had 28 of 29 passing; the one failure (wrong metric index) was a missing lab index, passed on rerun after creating it. Evidence: `docs/verification/evidence/phase15_fresh/` (data) and `phase15_fresh_ui/` (screenshots).

| gate | result | what was observed |
|---|---|---|
| A. Single sourcetype, Cisco ASA | PASS | sent 20, "Verified: found 20 of 20 events in index idx_network_ops" (`journey_asa.json`); the same journey for cisco:ios and fortigate_traffic |
| B. Four sourcetypes together (ASA 8, IOS 6, FortiGate 5, PAN traffic 6) | PASS | sent and indexed counts equal per sourcetype; each keeps its sourcetype, host and index (`multi_four_sourcetypes.json`) |
| C. Events plus IOS XR metrics in one run | PASS | events by search 9 of 9 in `idx_network_ops`; metrics by `mstats` 33 of 33 datapoints in `cisco_mdt_metrics` (`multi_mixed_event_and_metric.json`); wrong metric index and wrong event index each end "Not confirmed" |
| D. Streaming, bounded | PASS | counts grow over time (ASA 7→13, metrics 6→12), Stop ends the stream in 0.15 s, counts frozen after Stop, indexed totals equal what was accepted; an outage mid-stream is counted and recovers; a sustained failure ends the run FAILED and a new run works (`multi_streaming.json`, `streaming_*.json`) |
| E. Scenario `paloalto_threat_investigation` | PASS | 47 sent, 47 indexed, 3 sourcetypes (traffic 25, threat 13, system 9), 5 phases in order BASELINE→DEGRADE→FAULT→FAILOVER→RECOVER, correlation fields preserved; Dashboard Studio dashboard `pf_paloalto_threat_investigation` opens with the run id bound and each of its searches returns rows (`scenario_paloalto_threat_investigation.json`). Scenarios without their own dashboard offer the generic run investigation dashboard |
| F1. Unsupported sourcetype | PASS | whole request refused, sourcetype named, nothing skipped |
| F2. Invalid destination | PASS | "Splunk did not receive this data", run FAILED |
| F3. HEC rejection (real Splunk refuses the token) | PASS | rejection shown with the HEC reason, not Verified |
| F4. HEC accepts, nothing indexed | PASS | "Not confirmed" after retries, never Verified |
| F5. Search unavailable | PASS | "could not check whether it is searchable"; HEC numbers shown as acceptance only |
| F6. Partial batch rejection | PASS | failed source named, others Verified, overall PARTIAL, nothing says Verified for the whole run |
| F7/F8. Engine not configured / not connected | PASS | 503 / 502 with the exact messages above |

Verified-in-Splunk parsing claims are limited to six sourcetypes (`cisco:asa`, `cisco:ios`, `fortigate_traffic`, `pan:traffic`, `pan:threat`, `pan:system`); every other sourcetype is labelled not verified.

## Other regression and package gates

| gate | result |
|---|---|
| Package install checks (fresh lab) | PASS 20/20 |
| Packaged browser acceptance | PASS 29/29 |
| Source browser regression (26 specs, no Splunk) | PASS 26/26 |
| Focused Python selection (39 files, clean checkout of `856418b`) | **9 failed, 4061 passed, 2 skipped, 84 subtests passed** — exactly the established nine (`test_gate6_integrity::test_07_successful_hec`; seven sub-failures of `test_gate9_5_telemetry_semantics::test_01` for `ub1_ot_proxy_host_hunt`, `ub2_cloud_identity_mail_hunt`, `ub2_database_backup_integrity`, `ub2_ot_edge_routing_observation`, `ub3_database_message_audit`, `ub3_identity_runtime_audit`, `ub3_multivendor_edge_observation`; and `test_phase12_agentic_supply_chain::…::test_dashboard_recipe_families_integrate_without_regression`, 30 vs 34 recipes). **No new failure.** The nine are known failures, not passes. The selection was rebuilt from its description (39 files by name pattern; the file list is saved in `evidence/phase15/python_selection_files.txt`), so the pass/skip totals (4061/2) differ from the Phase 14 run (3990/4); I did not isolate the cause (the Phase 14 run was in a working tree, this one in a clean checkout without the untracked sample folders), but the failing set is identical |
| Package audit and checksums | PASS (0 findings; `SHA256SUMS` OK) |
