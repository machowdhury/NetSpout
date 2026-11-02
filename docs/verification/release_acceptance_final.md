# Final release acceptance (2026-11-01)

Branch `phase4e/claude-implementation`. Lab: `netspout_phase4e_splunk` (Web 18000, management 18191, HEC 18088), index `idx_network_ops`, engine on 8091. This is acceptance evidence for a demo, **not** a production certification.

## Regression

| | Count |
|---|---|
| Passed | 1,848 |
| Failed tests | 47 |
| Failing subtests | 7 (`test_gate9_5_telemetry_semantics`, scenarios ub1/ub2/ub3) |
| Skipped | 10 |
| New failures versus the established baseline | **0** |
| Baseline failure now passing | `test_native_discovery::NativeDiscoveryTests::test_navigation_and_dashboard_queries` |

Not clean: 47 tests and 7 subtests still fail, all of them in the baseline set (exact IDs: `evidence/regression/final_2026-11-01.json`): 30 in `test_gate13d_gnmi_splunk_e2e` / `test_gate13e_customer_acceptance`, 9 in `test_gate12d_snmp_splunk_e2e`, 4 in `test_gate12f_snmp_productization`, 2 in `test_gate4_contract`, and the rest in single files. They are environment-dependent: they expect a live Splunk (HEC 127.0.0.1:8088, REST 127.0.0.1:8089) and gNMI/SNMP collectors that this machine does not provide at those addresses. They were not modified, skipped or disabled.

The three fixes from the previous pass (README heading test, Explorer dashboard-link test, syslog day-padding test) hold: all three pass in the final run.

### The stalled run

The run that looked stuck near 9% was not hung. `test_gate13d_gnmi_splunk_e2e` builds all its evidence in `setUpClass` (`run_scenario_e2e` → `execute_spl_search`). With no Splunk at the default addresses, `execute_spl_search` swallows each connection error and retries (0.35 s sleep) against a 60 s readiness deadline per scenario, so the class setup takes about 6 minutes and uses almost no CPU, with no open sockets. The 27 tests then fail. Process sampling showed `0:04` CPU in `2:13` elapsed and no sockets.

Recovery: stopped only the pytest process (never Splunk, Docker or the engine), installed `pytest-timeout` into the scratch virtualenv (not a repository dependency), and ran the whole suite with `--timeout=45 -o faulthandler_timeout=40 -v`: finished in 3 min 18 s. At 45 s the gate13d/e class setup is cut off, which turns three baseline-passing tests (`test_18`, `test_24`, `test_gate13e::test_06`) into setup errors; those two files were rerun with `--timeout=900` and then match the baseline exactly (30 failed, 3 passed, 9 min 44 s). The combined result above is the full run plus that rerun. Partial logs of the two interrupted runs were kept in the scratchpad.

## Dashboards

| | Count |
|---|---|
| Installed `pf_` Dashboard Studio views | 148 (138 template + 10 NetFlow) |
| Data-validated or better (evidence) | 148 |
| Visually verified | 20 (10 template + 10 NetFlow) |

Reconciliation of 147 vs 148: scenario `SEC-P9-B-DNS-ANOMALY` linked to the older recipe view `pulseforge_dns_anomaly_studio` (SPL-validated only) although its `pf_SEC-P9-B-DNS-ANOMALY` view was already data-validated. The `pf_` view is now the Explorer's primary link; the recipe view is `alternate_view`.

## Verification in the phase4e lab

See [NetFlow verification, final acceptance section](netflow_solution_verification.md#final-acceptance-in-the-netspout_phase4e_splunk-lab-2026-11-01). Summary: 11/11 API runs READY with accepted = indexed; wire 100% decoded; 10/10 dashboards (data, render, drilldown), 10/10 browser flows; native and recorded-sample sourcetype streaming in finite, timed and continuous modes with pause/resume/stop; HEC test 8/8; 0 orphan runs.

A real defect was found and fixed during this pass: the run-bound dashboard link did not carry the run's index, so dashboards were empty in any lab whose index is not `dev_test_replay` (the earlier checker did not detect it). The checkers now count Splunk Web's actual empty-state text.

## Not done / blocked

* Cloud HEC: **BLOCKED BY MISSING LOCAL CREDENTIAL** (no `NETSPOUT_HEC_TOKEN`); nothing sent to Cloud, the Cloud app not touched. `netspout_cloud.spl` is dashboards only and was built, not installed anywhere.
* No Classic Simple XML dashboards; the NetFlow views are Dashboard Studio JSON.
* No CIM data model or detection validation.
* Manual opening of a dashboard shows the `dev_test_replay` default in its Index input; set it to your index.
* The README Quick Start was exercised partly (see the README verification section of the final report): clean venv install and package builds, engine extraction and start on a spare port with health, search and preview, and the Splunk install by REST into the lab; the interactive Splunk Web upload and the Docker `docker-compose.yml` demo stack were not re-run.
