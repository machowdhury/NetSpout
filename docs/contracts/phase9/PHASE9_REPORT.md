# Phase 9 report: browser-to-Splunk acceptance

Branch `recovery/phase1-ta-compat`, from `4af05a3`. Everything below was driven through the real browser UI (Playwright, Chromium) into the isolated TA-validation lab (`netspout_tavalidation_splunk`, Splunk 10.2.7, mgmt 19191, HEC 19088). Nothing was written to the remote reference instance, the protected demo was not touched, no released package was modified, no PR was opened. Lab configuration: `docs/verification/evidence/phase9/lab_config.json` (indexes, add-ons, HEC token names; `cisco_metrics` is a metric index created in this lab in Phase 8). Credentials stay in the git-ignored `tests/lab/ta_validation/.env.lab`; the spec reads them at run time, secret fields are filled without echoing and the evidence was scanned for them (none).

## How the acceptance is built
- **Real destination.** The saved destination is the real lab HEC, reached through `scripts/phase9_hec_proxy.py`, a recording tap that forwards unchanged (events and metrics are really indexed) and records what NetSpout actually sent: sourcetype, index, host, source, time, metric names and dimension names, never the Authorization header. It has fault modes used only in the failure tests. It is not the Phase 6 fake receiver.
- **Independent proof.** A pass is never "HEC accepted". Each test also searches the lab Splunk directly with the lab credentials (not the app's own verification): counts, sourcetype, index, host, `_time`, TA-extracted fields, and the absence of NetSpout values under vendor field names.
- **Add-ons one at a time** (`scripts/phase9_acceptance.py`): Splunk_TA_cisco-asa 6.1.2, TA_cisco_catalyst 4.0.60, Splunk_TA_fortinet_fortigate 1.6.10, Splunk_TA_paloalto_networks 4.0.0; the lab is returned to the ASA add-on at the end.

## Result: 17 of 17 browser tests pass on the final code
Connections (save, one Test connection) → Generate Data (vendor, product, sourcetype) → Preview → Generate → result, in the UI each time.

| Integration | UI result | Outgoing (tap) | In Splunk (own search) |
|---|---|---|---|
| `cisco:asa` | Verified: found 20 of 20 events in index ta_validation | sourcetype cisco:asa, index ta_validation, host asa-fw-01, HEC 200 | 20 events, same sourcetype/index/host; message_id, vendor_action, action, src_ip, dest_ip extracted on all 20 |
| `cisco:ios` | same, 20 of 20 | cisco:ios | facility, severity_id, mnemonic extracted on all 20 |
| `fortigate_traffic` | same, 20 of 20 | fortigate_traffic | src/dest ip and port, transport, vendor_action, action, dvc extracted |
| `pan:traffic` | same, 20 of 20 | pan:traffic | src/dest ip, rule, zones, app, vendor_action, action extracted |

For all four: `_time` equals the explicit send time within 3 s, the stored host set equals the sent host set, the preview's sourcetype and index equal what was sent, no vendor/CIM name (action, signature, status, src_ip, dest_ip, protocol, vendor, node_type) appears in the outgoing field names or as an indexed field in Splunk (checked with `tstats`; a value-equality check was tried first and rejected because the add-on's own `action` legitimately equals NetSpout's). Evidence: `docs/verification/evidence/phase9/journey_*.json`; screenshots `docs/verification/evidence/phase9_ui/p9_01..03`.

## Metrics (IOS XR, metric index `cisco_metrics` set explicitly in Connections)
- Preview shows the metric index and the 14 documented series; the status badge stays *Can send data, not tested in Splunk* (untested names are not promoted).
- 28 HEC metric events carrying 144 datapoints, 14 distinct names, all to `cisco_metrics`, HEC 200. UI: *Verified: found 144 of 144 metric datapoints in metric index cisco_metrics (mstats search)*; it never phrases metric success as an event-index result.
- Independent `mstats` / `mcatalog` by run id: the same 14 names, datapoint count 144, per-metric value sums equal to the sent values, dimensions equal to the documented set per metric (plus `netspout_*` bookkeeping), `path` equal to the documented path, nothing for the run in the event index, index datatype `metric`. `mpreview` was not used and is not claimed. Evidence: `journey_metrics.json`, `p9_04`, `p9_05`.

## Failure paths (UI never says Verified because HEC accepted)
| Case | How produced | What the UI said | Splunk reality |
|---|---|---|---|
| Invalid destination | closed HEC port | Connections: *Not working: Splunk HEC could not be used … Connection refused*; run: *Splunk did not receive this data. HEC endpoint unreachable* | 0 events |
| HEC rejection | real Splunk refuses a wrong token | *Not working*; run: *did not receive this data. HEC HTTP 403* | 0 events |
| Accepted but not indexed | tap answers HEC's success and forwards nothing | Connections: *Partly working*; run (after 6 checks): *Not confirmed: Splunk accepted 10, but a search found none of the 10 events…* | 0 in any index |
| Wrong event index | tap rewrites the index to `main` | *Not confirmed* | 10 in `main`, 0 in `ta_validation` |
| Wrong metric index | tap rewrites the metric index to `dev_test_replay_metrics` | *Not confirmed: … found none of the 72 metric datapoints in metric index cisco_metrics (mstats search)* | 0 in `cisco_metrics`; the points are in the other index |
| Unsupported sourcetype | catalog entry with no generator | status *Cannot send data*, no Generate control, server answers 409 | none sent |
| Routing conflict | `cisco:thousandeyes:metric` | *Cannot send data*, message names the metric-index conflict, 409 for run and preview | none sent |
| Preview failure | HTTP 500 injected into the preview request (browser route interception) | *Preview failed: …*, Generate disabled with the reason | none sent |
| Search unavailable | search endpoint closed, HEC fine | Connections: *Partly working: … the search check failed … cannot confirm that anything is searchable*; run: *accepted, but this app could not check whether it is searchable … not verified* | the events were indexed (checked by the test), the app still did not claim Verified |

Evidence: `failure_*.json`, screenshots `p9_10..p9_20a`. The only injected (not natural) cases are the tap-based ones and the preview error; the HEC rejection and invalid destination are real refusals.

## Defects the browser acceptance found, and fixed
1. **Scenarios from the UI could not run on a real destination.** A scenario run sent no index, the backend fell back to `dev_test_replay` and answered 403. Now: no index means the saved destination's first event index (the old default is kept only where it is configured); the Scenarios page also sends and shows its index.
2. **Metric runs from Generate Data answered 403** for the same reason; fixed by the same change and by the UI always sending the index.
3. **A correct metric delivery could never be Verified.** Sourcetype runs recorded no metric index and no datapoints, so verification searched the event index for metric events. Runs now carry the metric index and datapoint counts; verification uses `mstats` on the metric index.
4. **Scenario-runner scenarios sent nothing.** The runner got a transport rebuilt with `model_dump()`, which drops the HEC token (it is excluded from dumps), so events were generated, no delivery was attempted and the run still ended COMPLETED. Fixed by carrying the token. (Only visible when the token is saved in Connections and not also in the environment.)
5. **Connections form race.** Typing before the saved destination had loaded could join old and new text (a URL repeated three times was saved once). The form is now locked until the saved destination loads.
6. **The Dashboard Studio link never appeared.** The page read a field that the API does not return, and guessed a dashboard id that did not match. Fixed to use the real ids.
7. **Wording and states**: "still checking" never ended for accepted-but-not-found data (now *Not confirmed* after the retries); a failed preview left Generate enabled (now disabled); the Connections verdict conflated "search is down" with "event not indexed".

Each backend defect has a regression test that fails without the fix (`tests/test_phase6_capability.py`, three tests; `tests/test_delivery_monitor.py` covers the scenario-runner path).

## Simple UI finishing (only the listed items)
One Test connection control (Validate removed); readable Cisco names; product search when a vendor has more than eight products; plain status words (*Verified in Splunk*, *Checked offline only, not tested in Splunk*, *Can send data, not tested in Splunk*, *Cannot send data*; scenarios *Can run, not fully tested in Splunk*, *Cannot run*); *Why it cannot run* lists the exact reason per source; mode and rate moved under *More options*. Screenshots: `p9_30..p9_33`.

## Scenario acceptance
`paloalto_threat_investigation`, started in the UI (state *Can run, not fully tested in Splunk*: `pan:traffic` verified, `pan:threat` and `pan:system` only offline-checked), Palo Alto add-on installed:
- UI: *Verified: found 47 of 47 events*; Splunk: 47 events (25 traffic, 13 threat, 9 system), each with the run id, the scenario id and its own event id.
- Phases BASELINE, DEGRADE, FAULT, FAILOVER, RECOVER appear in Splunk in the order sent, with non-decreasing times.
- All 14 data sources of the scenario's own dashboard (`pf_paloalto_threat_investigation`) return rows for this run.
- No Dashboard Studio dashboard exists for it (the page says so; no dead link). `C100-SEC-001`, which has one, shows the link with its real id and run id and its 11 events were indexed.
- **Not claimed as fully verified**: `pan:threat` and `pan:system` parsing was not tested against the add-on; the second scenario's source is NetSpout-defined, not a TA sourcetype.

## Regression (final code)
| Suite | Passed | Failed | Skipped |
|---|---|---|---|
| Python, 64 relevant files (generator, replay, capability status, preview, dispatch, metric routing, TA compatibility, scenario, delivery monitor, field ownership, Phase 8 formats) | 4,628 | 8 | 2 (+1,918 subtests passed) |
| Playwright: Phase 6 spec (also the file Phase 8 modified) + `unified-shell` | 17 (12 + 5) | 0 | 0 |
| Playwright: Phase 9 browser-to-Splunk acceptance (5 groups) | 17 | 0 | 0 (tests of other groups are filtered, not skipped) |

The 8 Python failures are exactly the ones that also fail on a clean checkout of `4af05a3`: 7 subtests of `test_gate9_5_telemetry_semantics::test_01` and `test_gate6_integrity::test_07_successful_hec` (order-dependent). No new failure is attributed to the baseline without that evidence. Earlier in this phase two further failures appeared and were real: `test_delivery_monitor::test_scenario_runner_run_is_monitored_through_the_real_dispatcher` (my first token fix rebuilt the transport through the wrong model class; fixed) and the Phase 6 spec's old wording assertions (updated for the new wording and the single Test connection control). Four tests were added: the metric run, the scenario index, the scenario token and the verify outcomes (all in `tests/test_phase6_capability.py`). The live Phase 4 add-on specs were not re-run in this phase; the dispatcher and generators were not changed, and the browser journeys above exercise ASA, IOS, FortiGate and Palo Alto live. The packaged UI bundle (`netspout/appserver/static/dist`) was rebuilt.

## Remaining blockers and limits
- No scenario is fully verified (all need at least one source tested against its add-on).
- Only four sourcetypes are VERIFIED; the 14 metric series are generated and found, other metric names are not generated.
- `mpreview` was denied on the reference instance and not used; metrics are verified with `mstats`.
- The tap-based failure cases are fault injection in front of a real Splunk, not natural server faults; the preview failure is an injected HTTP 500.
- Verification retries about 30 s; a slower indexer would show *Not confirmed* until "Check Splunk again".
- Keep-streaming mode for metrics, the packaged Splunk app UI inside Splunk Web, and `phase6-scenario-studio` / `phase4*` Playwright specs were not run.
- Real-data field comparison for ISE and Meraki in the browser was not repeated (Phase 8 covered them with a script).

## Reproduce
Start the tap (`scripts/phase9_hec_proxy.py`), a backend with its own `NETSPOUT_CONFIG_DIR` (`backend/run.py --port 18681`) and the Vite dev server (14273), then `python scripts/phase9_acceptance.py`. The Phase 6 regression uses `scripts/phase6_fake_hec.py`, backend 18581 and Vite 14173.
