# Phase 10.1 — final product workflow and RC3

Candidate: **`rc3-ae3342d`**, built from commit `ae3342d` in a clean worktree; artifacts, `SHA256SUMS` and `BUILD_MANIFEST.json` are in `~/netspout/release-candidates/rc3-ae3342d/` (copies of the manifest and checksums are in this folder). RC1 and RC2 and the released artifacts are untouched (released-artifact checksums re-verified OK).
**Build identity: version 2.0.1** (app.conf, app.manifest, frontend, engine API) — the release and RC1/RC2 are 2.0.0.

| artifact | sha256 |
|---|---|
| netspout.spl | c070b29e…018149 |
| netspout_cloud.spl | 01f0bd84…ea9c |
| pulseforge-engine.tar.gz | aa33e60a…ddcb |

## What changed
1. **Engine address is a customer setting.** The gateway has no default engine and ignores the environment. It reads `[engine] url` from the app's `netspout_engine.conf` (Splunk's own configuration endpoint; saved to `local/`). Connections > PulseForge Engine edits it (admin/power role). Empty: **"Engine not configured."** (HTTP 503). Unreachable: **"Engine not connected."** (HTTP 502). Generate Data and Scenarios show the notice and disable sending. Tested in the packaged app, including the exact messages and that nothing is sent.
2. **Several sourcetypes in one run** (`kind: "multi"`): same generators and dispatcher as a single run, one monitored run, per-sourcetype accepted/rejected/found, mixed event + metric routing (events to the event index, metrics to the saved metric index), bounded or continuous. Unsupported sourcetypes refuse the whole request and name the sourcetype (nothing is skipped silently).
3. **Per-sourcetype verification**: one independent search by run id (count, index, hosts per sourcetype) and `mstats` for metrics. New overall status `PARTIAL` when everything accepted is found but something was rejected, so a partly rejected run is never shown as Verified.
4. **Scenario preview** (counts per sourcetype and phase, a representative event per source, rough duration) and, for every run, an **Investigate** block: the scenario's own Dashboard Studio dashboard (with run id, index and time range) and one new generic **NetSpout Run Investigation** dashboard (events by sourcetype/host, timeline, phases, mstats metrics, latest events) plus a Splunk search link.
5. A run that delivered nothing is now `FAILED` ("No telemetry was sent"), never `COMPLETED`.
6. Fixes found on the way: engine package missing PyYAML (RC2), the fixed build size label, a configure race in the acceptance spec.

## Gates

| # | Gate | Result | Evidence |
|---|---|---|---|
| A | Single sourcetype: Cisco ASA, 20 events indexed and searchable (packaged) | PASS | `phase101_rc/journey_asa.json` |
| B | Four sourcetypes (ASA, IOS, FortiGate traffic, PAN traffic) in one run, counts/index/host verified independently, aggregate exact (packaged) | PASS | `multi_four_sourcetypes.json`, `p101_02`, `p101_03` |
| C | Mixed: ASA events + IOS XR metrics; events by search, metrics by mstats, own indexes (packaged) | PASS | `multi_mixed_event_and_metric.json`, `p101_05` |
| C2 | Continuous streaming of several sourcetypes: every source grows, Stop < 5 s, nothing after Stop, events and metrics verified (packaged) | PASS | `multi_streaming.json`, `p101_11` |
| D | `paloalto_threat_investigation`: 47 events, fields, correlation ids, phase order, 14 dashboard searches, Dashboard Studio dashboard opened with the run (47 events, 3 sources, 5 phases visible) | PASS | `scenario_paloalto_threat_investigation.json`, `p101_scenario_studio_dashboard.png` |
| E1 | Missing engine URL | PASS | `failure_engine_connection.json`, `p101_08/09` |
| E2 | Unreachable engine | PASS | `p101_10` |
| E3 | Invalid Splunk destination (single and multi) | PASS | `failure_invalid_destination.json` |
| E4 | Partly rejected multi-source batch (fortigate_traffic refused): named, others Verified, run status PARTIAL, text never "Verified" | PASS | `failure_multi_partial_rejection.json`, `p101_06` |
| E5 | Unsupported sourcetype (single and multi) | PASS | `failure_unsupported_and_routing.json`, `failure_multi_unsupported.json` |
| E6 | Accepted but not indexed (single and multi) | PASS | `p101_07`, `p9_14` |
| E7 | Splunk search unavailable (single and multi) | PASS | `failure_search_unavailable.json` |
| 5 | Packaged install: 20/20 checks (versions match, files equal archive, indexes, gateway reaches the configured engine, engine URL is the saved setting) | PASS | `phase101/rc_install_check.json` |
| 6 | Package audit (3 archives clean; private samples dir and vendor add-ons absent; git provenance) | PASS | `phase101/package_audit.json` |
| R1 | Python regression | PASS vs baseline | 8 failed / 4658 passed / 2 skipped; the 8 are the known `test_gate6_integrity::test_07` and 7 `test_gate9_5` subtests |
| R2 | Browser: Phase 6 UI, scenario studio, explorer, shell (26) | PASS | isolated runner |
| R3 | Phase 9 acceptance, source stack (asa ios fortinet pan metrics multi) | PASS | all groups exit 0 |
| R4 | Phase 9 acceptance, packaged RC3 (asa ios fortinet pan metrics multi engine) | PASS | all groups exit 0 (multi re-run once more after the streaming test was added) |
| R5 | Phase 4 specs bound to the protected lab (`phase4e-live-lab`, `phase4f-*`, `phase4g`, `phase4h`) | **NOT TESTED** | read the protected lab's credentials and port 18000 |
| R6 | Splunk Cloud instance offered in the request | **NOT TESTED** | see limitations |

## Limitations and notes
- **Upgrade impact:** an existing install (including the demo app) has no engine address after this version. The admin must enter it once in Connections > PulseForge Engine; until then the app says "Engine not configured." This is the intended behaviour, not a regression.
- Run Investigation is one generic dashboard; there are no per-sourcetype dashboards. A scenario's own dashboard exists only for scenarios that have one (the 372-scenario claim is not made).
- Scenario preview exists for the scenario-runner and declarative-contract families; for other families the page says no preview is available.
- The duration shown for a scenario is a rough estimate (0.1 s per event), not a measurement.
- Verified integrations remain cisco:asa, cisco:ios, fortigate_traffic, pan:traffic, pan:threat, pan:system; the IOS XR metric names are not claimed beyond what mstats confirmed in the runs.
- Splunk Cloud was not tested: the app needs a customer-hosted engine reachable from the Splunk server, the app would need Splunk Cloud app vetting and installation, and no HEC token for that instance was provided. The host named in the request is the same remote reference instance that Phase 7 documents and that the phase constraints say not to access; it was not contacted, and its credentials are not stored in this repository.
- The two sample folders mentioned (`netspout/datapet-test-es`, `netspout/samples`) were not used, not committed and not packaged (provenance audit proves the archives hold only git-tracked files).
- The packaged lab runs the recording tap and a loopback forwarder inside the engine container only because the product refuses plain HTTP and unverified TLS to non-loopback hosts; that is test scaffolding, not product behaviour.
- Builds are not byte-reproducible; no non-Docker Splunk was tested.

## Readiness
- **Controlled demo: READY** (set the engine URL once in Connections).
- **Broader release: NOT READY** until the protected-lab Phase 4 specs and a Splunk Cloud pass are run by someone with access, and the release version policy is decided.
