# Codex live acceptance — 2026-10-27

**Result: the HTTP-to-Splunk vertical slice passes; complete browser acceptance remains blocked.** No production-readiness claim.

Branch `oc/ise-ta-1915-record`; HEAD at audit `ef9f54f48cf26f671287a230ab43910aa7ec2564`. Initial tracked modifications: `backend/app/main.py`, `backend/app/scenario_runner.py`, `frontend/src/App.tsx`, `frontend/src/app/navigation.ts`. Destination/UI additions and claimed completion reports were untracked. All unrelated work remains untouched and unstaged. The repair commit includes only destination/workflow dependencies and repairs, one export, tests, and these reports.

Original diff and overwritten untracked-file copies were retained under `/private/tmp/pf-*`. Full working-tree inventory and detailed sanitized results are in the companion JSON.

## Acceptance matrix

| Criterion | Status | Observed evidence |
|---|---|---|
| Backend startup | PASS | GET /api/health HTTP 200; uvicorn listening on 127.0.0.1:8081. |
| Frontend startup | PASS | npm ci and npm run build passed; Vite localhost:5173 GET / HTTP 200. |
| UI scenario selection | BLOCKED | Browser inventory empty; native Chrome: Computer Use permissions are not granted. API lists 14 executable legacy scenarios. |
| UI destination selection | BLOCKED | Same browser blocker. Selected codex_local_lab via the real run HTTP request. |
| Preview | PASS | POST /api/acceptance/preview/cisco_aci_microburst: HTTP 200; 14 generated, 5 returned samples, dispatch disabled. |
| Run execution | PASS | POST /api/scenarios/run-with-destination: HTTP 200; NS-20261027-12d7e798; actual transport used; no simulation timer. |
| WebSocket progress | PARTIAL | Real /ws/logs handshake and connection_established/simulation_state messages observed. No per-run progress stream; new workflow waits for synchronous results. |
| Docker HEC event ingestion | PASS | 10 event records accepted; all 14 event+metric requests returned successful HEC outcomes. |
| Docker indexed event verification | PASS | 10 events: five cisco:dc:aci:health and five cisco:dc:nexus9k:syslog in idx_network_ops; RAW 10/10 identical; timestamps 10/10 within run. |
| Docker metric ingestion | PASS | Four cisco:ios:mdt records accepted into existing idx_performance_metrics. |
| Docker indexed metric verification | PASS | mstats: four distinct metric event IDs, 12 points, three metric names; 12/12 generated values match; timestamps within run second. |
| Dashboard deployment | PASS | Namespaced pulseforge_acceptance_ns_20261027_12d7e798 created; management readback HTTP 200; stored definition equals submission on Splunk 10.2.7. |
| Dashboard search results | PASS | Actual deployed table query returned 10 events; disjoint -7d to -6d window returned zero. |
| Dashboard rendering | BLOCKED | Computer Use permissions are not granted. Splunk Web URL HTTP 200 alone does not establish rendered panels. |
| Dashboard navigation | PARTIAL | API returns direct Splunk URL and workflow renders anchor; destination Web HTTP 200. Browser click unverified. |
| External destination safety | PARTIAL | Controlled tests cover TLS defaults, credential exclusion/env-reference reload, read-only health probe, health 403, connection failure and management 403. Real local bad HEC token: HTTP 403/code 4. Zero external transmissions; external Splunk acceptance not tested. |
| Cisco multi-source incident | PARTIAL | IOS XR correlated syslog/SNMP/OpenConfig composition exists; real non-dispatching preview HTTP 200. Full five-source XE/XR incident including separate SNMP traps/polling and Cisco-native MDT is not established; no live execution of that composition in this acceptance. |

## Real Splunk evidence

Final run `NS-20261027-12d7e798`, seed `42`, scenario `cisco_aci_microburst`, Splunk `10.2.7`. Generated **14 records**: 10 events + 4 metric records. **14/14 HEC accepted**, zero failed. Independently indexed **10 events + 4 metric records / 12 points**. Backend returned `VERIFIED`, event count 10, metric record count 4, total 14, completeness 100%, no errors.

Event index `idx_network_ops`; 5 `cisco:dc:aci:health`, 5 `cisco:dc:nexus9k:syslog`. RAW comparisons: 10/10 exact UTF-8 equality; per-event SHA-256 digests recorded in JSON. Event timestamps fall within the run; metric timestamps match the execution second. Payload authenticity is synthetic format fidelity, not Cisco hardware or TA parser validation.

```spl
search index=idx_network_ops netspout_run_id="NS-20261027-12d7e798" earliest=-1h latest=now | stats count min(_time) as first max(_time) as last by index sourcetype netspout_phase
```

```spl
| mstats count(_value) as points min(_value) as minimum max(_value) as maximum WHERE index=idx_performance_metrics metric_name=* netspout_run_id="NS-20261027-12d7e798" earliest=-1h latest=now BY metric_name device netspout_phase
```

Metrics are `buffer_utilization`, `egress_drops`, `queue_depth`, dimension `device=Nexus-9336-Leaf01`, phases BASELINE / FAULT / PROPAGATE / RECOVER. All 12 values equal the generated inputs. Buffer values: 12.5, 98.5, 99.1, 14; queue values: 1250000, 26500000, 28900000, 1400000; egress drops: 1420 each.

Initial verification returned no metrics because `metric_name=*` was omitted. Index enumeration also initially omitted metric indexes because its datatype filter defaulted to events. Both verification mistakes were corrected; `datatype=all` and read-only btool confirm existing metric indexes. No index was created or changed.

Two bounded ACI runs were performed in total: 28 HEC records accepted (20 events + 8 metric records). Earlier run `NS-20261027-dc7cd5ca` also remains in the lab. An invalid-token probe returned HTTP 403 / HEC code 4 and indexed no test event.

The fixed acceptance identifier is `pf-codex-20261027-ef9f54f-seed42-02`. Application run IDs are unique server UUIDs; caller-supplied deterministic run IDs are unsupported.

## Dashboard evidence

Created `pulseforge_acceptance_ns_20261027_12d7e798` using `POST /servicesNS/nobody/search/data/ui/views`, `name=<namespaced ID>`, `eai:data=<version 2 dashboard XML containing Studio JSON>`, `output_mode=json`, Basic authorization redacted. Create succeeded; GET readback HTTP 200 and definition equality passed. [Open local dashboard](http://127.0.0.1:18000/en-US/app/search/pulseforge_acceptance_ns_20261027_12d7e798).

The actual table query returned 10 rows; a disjoint -7d to -6d time range returned zero. Time-input tokens are wired in the definition, but interactive time-picker behavior is unverified. No drilldowns are defined. HTTP 200 from Splunk Web does not prove rendering.

All nine static exports parse as JSON. Initially all nine used an array for visualizations and omitted layout. `dashboard_cisco_aci_syslog.json` was repaired to a proper Studio object/layout and the actual Nexus sourcetype. Eight remain structurally unsuitable and were preserved. Live deployment used the same small definition builder with an exact run filter; it did not blindly import the original malformed export. Existing recipe-engine exports are a separate mechanism.

## Reproduction and commands

Backend:
```sh
PYTHONPATH=backend:netspout/bin .venv-test/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8081
```
Frontend:
```sh
cd frontend && npm run dev -- --host 127.0.0.1
```

Backend requires installed project dependencies plus httpx (now declared). Missing local uvicorn and websockets were installed into `.venv-test`; npm ci restored frontend dependencies. Local test environment used uvicorn 0.54.0, httpx 0.28.1 and websockets 17.3. The requirements pin websockets 17.2; that exact full requirements environment was not reinstalled.

Lab profile `codex_local_lab`: HEC `https://127.0.0.1:18088/services/collector`, event index `idx_network_ops`, metric index `idx_performance_metrics`, `hec_token_env=PULSEFORGE_LAB_HEC_TOKEN`. Existing `pulseforge-lab-hec` token was read in memory via Docker. No credentials were written to reports, source or destinations.json. The profile explicitly permits self-signed TLS only for this local test. External profiles default to TLS verification.

Independent observation/deployment requires explicit `PULSEFORGE_DASHBOARD_MANAGEMENT_URL=https://127.0.0.1:18089`, `PULSEFORGE_DASHBOARD_WEB_URL=http://127.0.0.1:18000`, and existing `NETSPOUT_SPLUNK_USER` / `NETSPOUT_SPLUNK_PASSWORD` process environment values. These credentials were obtained from the authorized lab in memory. Management URL must match the selected destination; there is no fallback to external hosts. Raw credentials supplied via destination API are session-only; use an environment reference for restart persistence.

Requests (no browser required):
```http
POST /api/acceptance/preview/cisco_aci_microburst
Content-Type: application/json

{}

POST /api/scenarios/run-with-destination
Content-Type: application/json

{"scenario_id":"cisco_aci_microburst","destination_id":"codex_local_lab","seed":42}

POST /api/acceptance/dashboards/NS-20261027-12d7e798
Content-Type: application/json

{"destination_id":"codex_local_lab"}
```

Independent searches used POST `https://127.0.0.1:18089/services/search/jobs/export`, form `search=<SPL above>&output_mode=json&preview=false`, Basic authorization `[REDACTED]`. Read-only authenticated health probe: GET `<HEC origin>/services/collector/health`. It explicitly does not attest ingestion or search permission.

Live harness commands and sanitized responses are enumerated in JSON; `/private/tmp/pf_accept.py` and follow-up scripts remain available locally. Full browser reproduction begins at `http://127.0.0.1:5173/#/guided-workflow`; select ACI and the lab destination, Preview, Execute, Deploy Run Dashboard, then Open Dashboard in Splunk. These UI actions could not be performed by this agent because computer-use permissions were denied.

## Defects and focused repairs

- Frontend initially failed TypeScript compilation: nonexistent primitives and handler used before declaration. Replaced the two broken screens with native controls; retained their routes. External profile editing is currently via API.
- Run endpoint ignored selected transport and left dispatch disabled. It now passes transport_config and dispatch_telemetry=True, returns the actual manifest and records the accepted count. It no longer starts an unrelated continuous simulation.
- Removed fabricated progress/completion and the wrong local `/dashboard` redirect. Dashboard navigation now uses a returned Splunk URL.
- Added explicit management observation with correct metric-aware SPL and distinct metric record counts. Legacy observation discovery remains unchanged outside this endpoint.
- Fixed shadowed deployment-types route and broken unsaved-connection probe. Health tests no longer write synthetic events to external destinations.
- Added TLS-safe defaults, independent event/metric indexes, secret-free profile persistence, environment credential references, URL validation, redacted failures, and preserved settings in public profiles.
- Added namespaced create-only dashboard deployment with explicit endpoint matching; management 403 is returned without hiding the permission failure. Existing dashboards are never overwritten.

## Cisco truth check

C100-SP-001 maps to executable `test-correlated-interface-degradation`; actual `/api/generation/preview` returned HTTP 200. Its composition binds IOS XR interface syslog, SNMPv2c IF-MIB and OpenConfig/gNMI, with shared `cisco-asr9k-pe1` / `HundredGigE0/0/0/1` identities and BASELINE → DEGRADE → FAILOVER → RECOVERY state planning. This is a different runtime path from the tested ACI scenario. Separate live polling, traps and gNMI behavior were not executed in this acceptance. Cisco-native MDT is absent from that composition. The requested complete five-source IOS XE/XR incident is therefore not established. The separate OpenConfig worktree was untouched.

## Validation and unresolved reproduction

```sh
PYTHONPATH=backend:netspout/bin .venv-test/bin/python -m pytest tests/test_live_acceptance_repairs.py tests/test_phase11_dashboard_recipe_engine.py tests/test_sec2b_credential_updates.py -q
npm run build --prefix frontend
git diff --check
```

**41 tests passed; 40 subtests passed; zero failures.** One Starlette TestClient deprecation warning. Frontend build passed with bundle-size and inlineDynamicImports warnings. Controlled tests cover transport routing, persistence, TLS/URL handling, no-write probes, denied permissions, redaction, actual counts and Studio structure.

Unresolved: browser tests/rendering require computer-use access; per-run WebSocket progress is absent (connect to `/ws/logs` to observe simulation messages only); eight exports still lack Studio structure; table drilldowns are absent; full external acceptance and complete Cisco five-source execution remain untested/unimplemented as described. No broad TA, Splunk configuration, PAN RAW, customer destination or separate worktree changes were made. No push or merge.
