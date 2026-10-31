# Live Delivery Monitor, HEC connection test and flow scenarios: verification record (2026-10-31)

Isolated Docker Splunk 10.2.7 lab only (`netspout_tavalidation_splunk`); engine on a non-8081 port; installed `netspout.spl` (not the repository UI). No Splunk Cloud endpoint was contacted. Scripts: `scripts/validate_monitor_live.py`, `scripts/render_monitor_live.mjs`, `scripts/validate_hec_test_live.py`, `scripts/validate_flow_scenarios.py`. Evidence: `docs/verification/evidence/monitor/` and `evidence/flow/`.

## 1. Counter accuracy by scenario family (engine API, independent Splunk search after the run)

| Case | State | Generated | Accepted | Rejected | Unknown | Indexed after Verify | Avg EPS | Verify |
|---|---|---|---|---|---|---|---|---|
| single_sourcetype | COMPLETED | 30 | 30 | 0 | 0 | 30 | 14.31 | VERIFIED |
| replay_pack_finite | COMPLETED | 12 | 12 | 0 | 0 | 12 | 39.42 | VERIFIED |
| native_pack | COMPLETED | 20 | 20 | 0 | 0 | 20 | 35.82 | VERIFIED |
| incident_pack | COMPLETED | 40 | 40 | 0 | 0 | 30 | 54.42 | VERIFIED |
| scenario_runner | COMPLETED | 10 | 10 | 0 | 0 | 10 | 9.39 | VERIFIED |
| unified_generation | COMPLETED | 9 | 9 | 0 | 0 | 9 | 62.28 | VERIFIED |
| pause_resume_stop | STOPPED | 200 | 74 | 0 | 0 | 74 | - | VERIFIED |

Incident pack: 40 accepted = 30 log events + 10 metric events carrying 50 gauge datapoints; the `mstats` search finds 50 datapoints, so the run is VERIFIED only because datapoints are compared with the datapoints of the accepted metric events (an event-for-datapoint comparison would have reported a false mismatch). Pause/resume/stop (batch): paused counters held, resumed, stopped with pending = 200 minus attempts, indexed equals accepted. Monotonic counters while polling were checked for every case.

## 2. Browser (Splunk Web, installed app, Use Case Explorer)

| Family | Result |
|---|---|
| replay_pack | PASS: final COMPLETED, accepted 131, Indexed `Not verified` before Verify then 131; refresh re-attached to the same run: True |
| unified_generation | PASS: final COMPLETED, accepted 4, Indexed `Not verified` before Verify then 4; refresh re-attached to the same run: True |
| scenario_runner | PASS: final COMPLETED, accepted 10, Indexed `Not verified` before Verify then 10; refresh re-attached to the same run: True |
| native_pack | PASS: final COMPLETED, accepted 10, Indexed `Not verified` before Verify then 10; refresh re-attached to the same run: True |
| incident_pack | PASS: final COMPLETED, accepted 40, Indexed `Not verified` before Verify then 40; refresh re-attached to the same run: True |

Screenshots (`screens/`): `*_running`, `*_final`, `*_after_refresh` per family. Visual review against the Figma V2 reference: dark surface and terracotta accent applied to the monitor; the surrounding legacy React UI still uses its older teal palette; IBM Plex Mono is requested for identifiers and falls back when not installed. The throughput chart is a plain SVG line (no axes).

## 3. External HEC connection test (isolated lab destination)

| Case | Overall | Statuses / error |
|---|---|---|
| valid_with_search | FULLY_VERIFIED | connection=REACHABLE, authentication=AUTHENTICATED, acceptance=ACCEPTED, indexing=VERIFIED |
| disallowed_index_via_engine | FAILED | connection=NOT_RUN, authentication=NOT_RUN, acceptance=NOT_RUN, indexing=NOT_RUN ; error INDEX_NOT_ALLOWED |
| accepted_without_search | ACCEPTED_NOT_VERIFIED | connection=REACHABLE, authentication=AUTHENTICATED, acceptance=ACCEPTED, indexing=NOT_CONFIGURED |
| invalid_token | FAILED | connection=REACHABLE, authentication=REFUSED, acceptance=REJECTED, indexing=NOT_RUN ; error AUTH_FAILED |
| unreachable | FAILED | connection=FAILED, authentication=NOT_RUN, acceptance=NOT_RUN, indexing=NOT_RUN ; error REFUSED |
| dns_failure | FAILED | connection=FAILED, authentication=NOT_RUN, acceptance=NOT_RUN, indexing=NOT_RUN ; error DNS |
| tls_certificate_not_trusted | FAILED | connection=FAILED, authentication=NOT_RUN, acceptance=NOT_RUN, indexing=NOT_RUN ; error TLS_CERTIFICATE |
| accepted_but_not_indexed_missing_index | ACCEPTED_NOT_VERIFIED | connection=REACHABLE, authentication=AUTHENTICATED, acceptance=ACCEPTED, indexing=NOT_FOUND |

Secret scan of the whole evidence file: HEC token present = False, password present = False. The disallowed-index case sent nothing: an `index=*` search for its test id found 0 events. A nonexistent but allowlisted index was **accepted** by this lab's HEC and never indexed: acceptance is not indexing, which is why they are separate statuses.

## 4. Flow scenarios (GoFlow2 v2.2.5 + repo forwarder, isolated lab)

| Scenario | Collector flows read/forwarded (delta) | Indexed by sourcetype | Stages |
|---|---|---|---|
| SEC-P9-A-TRAFFIC-FLOOD | 11/11 | {'netflow:collector': 11} | SPLUNK_OBSERVED=PROVEN, SOURCETYPE_VERIFIED=PROVEN, FIELDS_VERIFIED=PROVEN |
| SEC-P9-C-BEACONING | 7/7 | {'netflow:collector': 7, 'netspout:dns:wire': 4} | SPLUNK_OBSERVED=PROVEN, SOURCETYPE_VERIFIED=PROVEN, FIELDS_VERIFIED=PROVEN |
| SEC-P9-D-INTERNAL-RECON | 11/11 | {'netflow:collector': 11} | SPLUNK_OBSERVED=PROVEN, SOURCETYPE_VERIFIED=PROVEN, FIELDS_VERIFIED=PROVEN |
| SEC-P9-E-DNS-TUNNEL | 9/9 | {'netflow:collector': 9, 'netspout:dns:wire': 9} | SPLUNK_OBSERVED=PROVEN, SOURCETYPE_VERIFIED=PROVEN, FIELDS_VERIFIED=PROVEN |
| SEC-P9-F-CROSS-SOURCE | 11/11 | {'netflow:collector': 11, 'netspout:dns:wire': 4} | SPLUNK_OBSERVED=PROVEN, SOURCETYPE_VERIFIED=PROVEN, FIELDS_VERIFIED=PROVEN |

All five now have Dashboard Studio views (138 of 138 runnable scenarios), installed, data-validated and opened in Splunk Web; one (`SEC-P9-F-CROSS-SOURCE`, Investigation tab) was inspected visually. Detection execution, TA parsing and CIM were not attempted.

## Not covered by this record
- Splunk Cloud (user validation pending: the request carried the endpoint but no token, credentials or test index name, so nothing was sent).
- Browser Pause/Resume/Stop (continuous replay pack, installed app): PASS on an otherwise idle machine (paused counters held, resumed, stopped; `replay_controls` in `browser.json`). Earlier attempts failed while leftover continuous sessions and the full regression were loading the lab, so treat the control path as passing but sensitive to a loaded lab. Runner families cannot be paused by design.
- SNMPv3, sFlow, gRPC dial-out MDT, J-Flow-specific and IPv6 flow: not implemented.

## Installed-app restart and regression
- Splunk restarted several times and the engine restarted several times (repository launcher and the extracted `pulseforge-engine.tar.gz`); `validate_installed_app.py` passed 12 of 12 afterwards.
- Final full regression: 55 failed, 1810 passed (before the last one-line fix of `run_scenario`). Ids: the 42 original baseline plus 12 lab-dependent SNMP plus one extra (`test_gate4_contract::test_18_run_cancellation_behavior`), which was caused by my run-id handling and is fixed; it passes together with the monitor tests afterwards. Two intermediate runs showed extra failures caused by the lab flow collector left running (flow preflight became READY) and two rewritten catalog mirror files; both were corrected, not hidden. No baseline failure was fixed or newly failing.

## Streaming, readiness, preview and incident Impact-map window (2026-10-31)

- **Single-sourcetype streaming** (`scripts/validate_stream_live.py`, evidence `evidence/monitor/stream_live.json`): native `cisco:dc:aci:class` and grounded-sample `arista:eos:syslog` each passed continuous (counters grew in every 2.5 s interval, pause held counters, resume continued, stop left no active run or growth, Splunk search verified indexed == accepted), finite count (25) and finite duration (5 s). Lab only.
- **Browser (installed app, `scripts/render_search_live.mjs`, evidence `evidence/search/`)**: search, kind filter, dashboard link, scenario open and state kept after reload passed; continuous stream reattached after a refresh and paused/stopped/verified (207 of 207 indexed); a scenario run reached readiness READY with the notification and a run-bound dashboard that showed the run id with no empty panels. The browser script's overall flag was still FAIL in its last run: the pause label read RUNNING for >10 s while the Splunk gateway was stalling, although pause, resume and stop returned HTTP 200 and the final counts verified. Two UI hardening changes followed (one control retry with state reconciliation; one poll in flight at a time). They were built and installed but the browser script was **not rerun** after them.
- **Readiness**: states are computed by `_readiness_state` (unit-tested for every state, including unrelated data never giving READY and a missing phase blocking READY).
- **Dashboards**: `scripts/audit_dashboards.py` found 138 views share 6 visualization types and 5 panel signatures. 37 incident-pack dashboards gained an Impact-map tab; all 37 panel queries return rows for their validation run (`evidence/dashboards/impact_tab_validation.json`). One tab was inspected in Splunk Web: the donut and severity panels render; the bubble chart is accurate but sparse for that replay-speed validation session. These 37 were not promoted to visually verified.
- **Regression** (one full run after the last substantive change, before the final test edit): 91 failed / 1783 passed. 54 failures equal the known baseline IDs; the other 37 were `test_scenario_dashboards` tab-label assertions for the new tab, fixed in the test (that file plus the monitor and search tests now pass: 170). No fourth full run was made after the fix.
- **Splunk Cloud HEC**: BLOCKED BY MISSING LOCAL CREDENTIALS (no `NETSPOUT_HEC_TOKEN` in the engine environment). Nothing was sent.

## Browser acceptance closure and Metric-impact redesign (2026-10-31)

- **Cause of the earlier pause-state stall** (diagnosed, not hidden by timeouts): through the Splunk gateway every completed status poll took 4 ms at the median and 28 ms at the maximum, and control POSTs returned 200. A single poll lost at the connection level never answered, and the one-poll-at-a-time guard added in the previous window held every later poll behind it until the 25 s timeout, so the label stayed RUNNING. Fixes: status polls abandon after 5 s (the next one goes out), controls retry once and reconcile against the engine state, the label shows PAUSING/RESUMING/STOPPING while a control is in flight, and a "no answer from the engine for Ns" notice replaces a silently stale state. Lost polls still occur (2 of 945 in the passing run) and are now recovered within seconds.
- **Installed-app browser acceptance: PASS** (`scripts/render_search_live.mjs`, `evidence/search/browser.json`) with a second continuous stream (25 EPS) running on the engine as background load: one pause, one resume and one stop POST each (no duplicates), state transitions correct, refresh reattached to the same run, final 183 indexed of 183 accepted, no active run left on the engine, scenario run reached READY and its run-bound dashboard showed the run id with no empty panels. Earlier runs of the same script failed (listed above) before the fixes.
- **Impact map replaced.** Pack definitions show every incident pack has exactly 30 log events, 3 devices, 1 site and a ~4 s span, so the device bubbles, role donut and severity area made in the previous window were misleading and were removed. The 37 incident dashboards now have a **Metric impact** tab: a scorecard per metric (baseline, worst point, last value, change, a plain arithmetic back-within-10% check), metric shapes scaled to their own range, and the first event of each phase. All three panels return rows for all 37 validation runs (`evidence/dashboards/impact_tab_validation.json`). One tab (telco_09_core_user_plane) was inspected in Splunk Web and recorded as visually verified: 10 dashboards are now visually verified, 128 data-validated only.
- **Not done: broad dashboard diversification and coverage expansion.** The audit of the other 101 template dashboards stands (`design_audit.json`) but no family redesign was made. `scripts/analyze_catalog_only_unlock.py` (evidence `evidence/coverage/catalog_only_unlock.json`) shows why no scenario was converted: of 224 catalog-only scenarios, 209 are titles with no sourcetype binding or phases (2 have any binding), and the 15 contract-only ones carry generic phase names with no per-phase telemetry mapping, although 7 of them have every sourcetype streamable. Tagging recorded samples with phase names would invent a correlation, so counts are unchanged.
- **Search after restart**: the cache rebuilt at engine start; 1214 results (349 sourcetypes, 727 scenario entries, 138 dashboards), 259 streamable and 90 catalog-only sourcetypes, 138 runnable scenario entries.
- **Final full regression**: 56 failed / 1818 passed. 53 failures equal known baseline IDs; `test_native_discovery::test_navigation_and_dashboard_queries` (a known failure) passed in this run. Two new failures were mine and are fixed: the maturity test needed the inspected screenshot named `telco_09_core_user_plane__*.jpg`, and `netspout_cloud.spl` had not been rebuilt with the new views. Those files and the monitor/search tests pass (181 passed); the full suite was not run a second time, so the baseline failures remain: the regression is not clean.
- **Release artifacts rebuilt**: `netspout.spl` (installed in the lab, splunkd restarted, browser acceptance PASS), `netspout_cloud.spl` (138 views, dashboards only, not installed in Cloud) and `pulseforge-engine.tar.gz` (937 files, sha256 222efc5f…; the package was rebuilt but its clean-extract run was not repeated in this window).
