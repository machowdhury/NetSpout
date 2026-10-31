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
