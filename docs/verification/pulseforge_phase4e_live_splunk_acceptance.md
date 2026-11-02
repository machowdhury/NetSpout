# PulseForge Phase 4E: Live Splunk Acceptance

Date: 2026-10-29/30 (UTC). Branch `phase4e/claude-implementation`. All evidence below was observed against a real Splunk
Enterprise instance in an isolated Docker lab. Credentials, HEC tokens and generated passwords are intentionally absent.

## 1. Lab architecture

| Item | Value |
|---|---|
| Image | `splunk/splunk:10.2` (linux/amd64, emulated on Apple Silicon) |
| Splunk | Enterprise **10.2.7**, build `c0bff5b0fac3`, product type `enterprise` |
| Container / network / volumes | `netspout_phase4e_splunk` / `netspout_phase4e_net` / `netspout_phase4e_splunk_var`, `netspout_phase4e_splunk_etc` |
| Host ports (loopback only) | Web **18000**→8000, management **18191**→8089, HEC **18088**→8088 (all free beforehand) |
| App | `NetSpout PulseForge` **2.0.0**, `netspout.spl` SHA-256 `fe692e1001da282d37427acf7f026b74d7411c39c04f15c6bb7a94700609a2a2` |
| Backend | FastAPI (`backend/run.py`) on 127.0.0.1:8081, destination configured through Connection Center |
| Definition | `tests/lab/phase4e/{docker-compose.yml,lab.sh}`; credentials in git-ignored `tests/lab/phase4e/.env.lab` |

`agentsec_splunk` and the other AgentSec containers were not touched, inspected for secrets, or reused.

Lab bring-up checks: Splunk Web 200; management API 401 unauthenticated and 200 with the lab admin; HEC global input
enabled on 8088 with SSL; HEC token accepted, a wrong token returned 403.

Sanitized HEC exchange (smoke test):

```
POST https://127.0.0.1:18088/services/collector/event
Authorization: Splunk <redacted lab token>
{"event":"phase4e lab smoke","index":"main","sourcetype":"phase4e:smoke","fields":{"netspout_run_id":"smoke-1"}}
-> {"text":"Success","code":0}
search index=main netspout_run_id="smoke-1" earliest=-15m | stats count   ->  count=1
```

## 2. Installation

1. `scripts/build_splunk_package.py` (venv with project requirements) builds `netspout.spl` (includes `use_case_explorer`, taxonomy, rebuilt bundle).
2. `docker cp netspout.spl` then `POST /services/apps/local` (`filename=true`, `update=true`), then Splunk restart.
3. Verified through Splunk REST, not file presence: app `NetSpout PulseForge` 2.0.0, `disabled=false`, `visible=true`;
   indexes `cisco_mdt_metrics` (metric), `idx_network_ops`, `idx_security_fw` exist and are enabled; app nav and views listed
   (Canvas Orchestrator, Security Content Lab, dashboards).
4. Logged in to Splunk Web as the real admin in a browser, opened `app/netspout/netspout_canvas`; the Canvas iframe loads the bundle and
   the **Use Case Explorer renders inside Splunk with 42 demo-ready cards and no errors** (after the API-base fix, section 7).
5. Reinstall as an app update preserved the enabled saved search.

Note: the product name "PulseForge Command Center" does not exist in the repository; the nearest surfaces are the Canvas Orchestrator
and Run Console. The Explorer is reached through the Canvas (`#/explore`), not as its own Splunk nav entry.

## 3. Operational end-to-end (Select → Configure → Generate → Ingest → Verify → Dashboard)

### 3a. `SEC-P9-B-DNS-ANOMALY` (unified pipeline, dashboard `scenario-sec-p9-b-dns-anomaly`)

Catalog maturity `SPLUNK_VALIDATED` (tier VALIDATED). Run `5c71bf91-65a7-485f-8018-59de26e68725`, 9 events.

* Configure: preflight `READY_WITH_WARNINGS` (HEC reachable, authenticated search succeeded, bundled loopback DNS receiver passed).
* Generate/Ingest: native RFC 1035 loopback exchange; channel evidence `GENERATED … NORMALIZED PROVEN 9`, `SPLUNK_DISPATCHED PROVEN 9`.
* Verify (NetSpout): `SPLUNK_OBSERVED PROVEN 9`, status `OBSERVED`.
* Verify (independent):
  `search index=* netspout_run_id="<run>" earliest=-1h | stats count by index sourcetype` → `idx_network_ops / netspout:dns:wire / 9`
  (`_time` 2026-10-30 00:47:20 GMT; host `test-resolver-01`; `netspout_scenario_id=SEC-P9-B-DNS-ANOMALY`; phases NORMAL, SUSPICIOUS_ACTIVITY).
  Multivalue check `eval n=mvcount(netspout_phase) | stats max(n)` → `1`.
* Dashboard (10 panels, 8 executable, 2 non-executable by design): `GET /api/dashboards/{id}?run_id=…` then
  `POST /api/dashboards/{id}/validate` → `maturity DATA_VALIDATED`, `spl_validated`, `data_validated`, `source_coverage_validated` true, no failures.
  Independently re-ran two panel queries:
  * `panel-operational-summary`: `search index="idx_network_ops" (sourcetype="netspout:dns:wire") netspout_run_id="<run>" earliest=-15m latest=now | stats count as observed_records dc(sourcetype) as observed_sources` → `9, 1`
  * `panel-dns-security`: `… | stats count as queries dc(query) as unique_queries count(eval(response_code=3)) as nxdomain by netspout_phase` → `NORMAL 3/3/0`, `SUSPICIOUS_ACTIVITY 6/6/6` (sum 9 = events).
* **Not claimed:** `VISUALLY_VALIDATED` / `DASHBOARD_READY`. Only `DATA_VALIDATED` was reached.
* Through the UI: `frontend/tests/phase4e-live-lab.spec.ts` drives all six steps, each turning green from backend evidence.

### 3b. `cisco_aci_microburst` (ScenarioRunner, event + metric, Gate 8 contract)

Catalog maturity `GOLDEN_PATH_CERTIFIED`. Run `NS-20261030-aca110c8`: 14 generated, 14 dispatched, 0 failed.

Evidence summary (sanitized; `schema_version` 1.0 with `observed_at`):

```json
{"schema_version":"1.0","observed_at":1793321372.60,"run_id":"NS-20261030-aca110c8","scenario_id":"cisco_aci_microburst",
 "total_generated":14,"total_dispatched":14,"total_observed":22,
 "event_observed_count":10,"event_expected_count":10,"metric_observed_count":12,"metric_expected_count":12,
 "observation_completeness_pct":100.0,"observation_status":"COMPLETE","required_evidence_satisfied":true,
 "destinations":[
  {"telemetry_type":"METRIC","target_index":"cisco_mdt_metrics","query_mechanism":"MSTATS","expected_count":12,"observed_count":12,"status":"PASS","role":"SUPPORTING",
   "query":"| mstats count where index=cisco_mdt_metrics metric_name=* AND netspout_run_id=\"<run>\""},
  {"telemetry_type":"EVENT","target_index":"idx_network_ops","query_mechanism":"SPL_SEARCH","expected_count":10,"observed_count":10,"status":"PASS","role":"REQUIRED",
   "query":"search index=idx_network_ops netspout_run_id=\"<run>\""}]}
```

Independent verification:

* Events: `search index=idx_network_ops netspout_run_id="<run>" earliest=-1h | stats count … by sourcetype` → `cisco:dc:aci:health 5`, `cisco:dc:nexus9k:syslog 5`; raw event is
  vendor-native BSD syslog (`%BUFFER_MGR-3-QUEUE_DROP: Ingress queue threshold exceeded on Ethernet1/24 …`); `mvcount(netspout_run_id)` max `1`.
* Metrics: `| mcatalog` shows names `buffer_utilization`, `egress_drops`, `queue_depth` and dimensions
  `action, device, netspout_device_id, netspout_event_id, netspout_ground_truth, netspout_phase, netspout_run_id, netspout_scenario_id, node_id_str, sensor_path, status, subscription_id, vendor`.
  `| mstats … by netspout_phase`: `queue_depth` BASELINE 1,250,000 → FAULT 26,500,000 → PROPAGATE 28,900,000 → RECOVER 1,400,000;
  `buffer_utilization` 12.5 → 98.5 → 99.1 → 14.0. `| mstats count where index=cisco_mdt_metrics metric_name=* AND netspout_run_id="<run>"` → `12`.
* Observation: `egress_drops` is a constant 1420 in all four phases, so it is not a meaningful signal in this generator.

## 4. Security end-to-end: React2Shell (Select → Prerequisites → Generate → Ingest → Enable Detection → Verify)

Story `React2Shell` (`sec:d0ff3419-275e-4fe9-8ebd-4270fc1632f0`), readiness `RUNTIME_APPROVED`; runtime-approved detection
`d36459b1-7901-401a-a67e-44426c15b168` "Cisco Secure Firewall - React Server Components RCE Attempt".

* Prerequisites: Connection Center, index `idx_security_fw`, HEC and search credentials present (presence only), replay dataset, runtime approval: all PASS; live reachability reported `NOT_TESTED` by this call (reachability was proven separately).
* Dependencies: sourcetype `cisco:sfw:estreamer`; macros `cisco_secure_firewall`, `security_content_ctime`, upstream filter macro (expanded by NetSpout); no lookups or data models; required fields app, dest, dest_port, rule, signature, signature_id, src, transport.
  Upstream TA "Cisco Security Cloud" is **not installed**; NetSpout's adaptation aliases fields from the JSON event (compatibility status `REQUIRES_TRANSFORMATION`). **Not Enterprise Security**: no ES, CIM data model acceleration or notable-event actions were involved.
* Generate: dataset `/datasets/cisco_secure_firewall_threat_defense/react2shell/react2shell.log`, 2331 bytes, SHA-256 `01c4370b…9806a`, upstream commit `4389fa7a…`.
* Ingest: replay run `p13a-1693aa94-f9f9-4ffe-bf37-1e6a387db44c`, sent 1; independent `search index=idx_security_fw netspout_run_id="<run>" | stats count` → 1; `observe` → `OBSERVED 1`.
* Enable Detection: saved search `NetSpout - Cisco Secure Firewall - React Server Components RCE Attempt`, app `netspout`, owner `admin`,
  `disabled=0`, `is_scheduled=1`, cron `*/15 * * * *`, no alert actions; read back independently from `saved/searches`.
* Verify:
  * NetSpout validation (run-scoped, `-15m`): `POSITIVE_CASE_VALIDATED`, 1 match; negative control with an unknown run id: `NEGATIVE_CASE_VALIDATED`, 0 matches.
  * Independent: dispatching the real saved search through Splunk returned `resultCount 1` (`dest 172.16.3.110`, signature "SERVER-WEBAPP React Server Components remote code execution attempt", src `146.75.78.172`, `InlineResult Would block`).
  * **Scheduler firing observed**: `index=_internal sourcetype=scheduler savedsearch_name="NetSpout - …"` → `2026-10-30 01:00:01 GMT status=success result_count=1`.
* Limits: replay validation does not establish production detection efficacy; ES detection enablement was **not tested**.
* Through the UI: the security spec drives all six steps green against live Splunk.

### RBAC

* Management API requires authentication (401 unauthenticated). Wrong HEC token returns 403.
* A temporary user with the stock `user` role (removed afterwards): NetSpout's saved-search create returned `FAILED`, `enabled=false` (Splunk rejected it, HTTP 400) and **no saved search was created**. The same user could run bounded searches, as the role allows.
* App static assets (JS/HTML) under `/static/app/netspout/` are served without authentication, which is Splunk's behavior for app static content; no data is returned by them. All data calls go through the backend and Splunk REST.

## 5. Defects found by live testing (all fixed, with tests)

| # | Defect | Effect | Fix |
|---|---|---|---|
| 1 | Unified generation and ScenarioRunner read search credentials from env only | Preflight blocked despite validated Connection Center; endpoint guess `:8088→:8089` wrong on remapped ports | `search_provider` hook fed by Connection Center; env remains fallback |
| 2 | `/api/setup` used the alphabetically-first index as event index (`cisco_mdt_metrics`) | Dispatcher fail-closed every event; `SPLUNK_DISPATCHED FAILED` | Event/metric indexes chosen with the dispatcher's own rule; UI default likewise |
| 3 | HEC event path duplicated `netspout_*` in `fields` and JSON `_raw`; sent `None` as `"null"` | Multivalue fields; `stats … by netspout_phase` counted 18 for 9 events (NetSpout's own validation did not notice) | Duplicates and `None` dropped, `_raw` untouched |
| 4 | Evidence compared `mstats` datapoints with event counts | Completeness 157.1% | Metric expectation counts datapoints via shared `extract_metric_fields`; like-for-like denominator |
| 5 | Saved-search SPL stored with a leading `search` | Splunk doubled it (`search search …`); the scheduled detection could never match despite reporting enabled | Leading `search ` stripped; verified by dispatch and scheduler |
| 6 | `POST /api/topology` replaced `global_transport` (`hec_token` is `exclude=True`) | Any UI topology sync wiped destination and credentials | Backend preserves its transport |
| 7 | Splunk-hosted React UI called `/api` on Splunk's origin | 404 for every API call (also existing views) | Canvas passes loopback-only `api_base`; frontend honors loopback only |

## 6. Tests

| Run | Result |
|---|---|
| Gate 8 unified evidence | 27/27 |
| Explorer backend + API (hermetic) | 25/25 |
| Live UI spec (`PLAYWRIGHT_LIVE=1`), operational + security | 2/2 |
| Explorer, shell, product, Cisco 100, security-content specs (unconfigured backend) | 16/16 |
| Full suite, lab environment configured | 1349 passed, **42 failed**, 9 skipped |
| Full suite, no lab (previous report) | 1334 passed, 54 failed |

Compared with the 54-failure baseline: **0 new failures**; 12 now pass against the live lab (all 9 `test_gate12d_snmp_splunk_e2e`, 3 of 4 `test_gate12f_snmp_productization`).

Remaining 42 (all pre-existing, none introduced here): `test_gate13d_gnmi_splunk_e2e` 25 and `test_gate13e_customer_acceptance` 5 (gNMI E2E ends at `NORMALIZED`, not `VALIDATED`; it needs the external collector stage, which this Splunk-only lab does not provision), `test_gate9_5_telemetry_semantics` 7 (`ub*` scenarios lack `telemetry_model`),
`test_gate4_contract` 2 (stale tests using dict scenarios), `test_gate11f_governance_closure` 1 (collector and forwarder preflight), `test_gate12f_snmp_productization` 1, `test_phase12_agentic_supply_chain` 1.

## 7. Not verified / blocked

* Splunk Enterprise Security enablement, CIM data models, notable events: not available or tested.
* Dashboard visual validation and `DASHBOARD_READY`: not performed. The pack was validated to `DATA_VALIDATED` only; the dashboard was not deployed as a Splunk Dashboard Studio object.
* gNMI/OTel/collector-dependent E2E (gate13d/13e) and the flow collector: not provisioned.
* Only one security story is runtime-approved; the other 364 are replay-only, content-only or empty, by design.
* Detection efficacy in production, TA-based parsing (the upstream Cisco TA was not installed), and Splunk Cloud: not tested.
* The Explorer is reached inside the Canvas, not as a native Splunk nav entry. The Splunk-hosted UI expects the backend on loopback `:8081` (override `localStorage['netspout.apiBase']`).
* The 18-industry taxonomy remains a proposed default pending approval.
