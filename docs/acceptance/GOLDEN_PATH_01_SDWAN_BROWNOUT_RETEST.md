# NETSPOUT PRODUCT ACCEPTANCE RETEST REPORT
## GOLDEN PATH 01 — SD-WAN BROWNOUT WITHOUT REAL INFRASTRUCTURE (GATE 6 REMEDIATION)

**Test Retest Execution Date:** 2026-09-25  
**Product Version:** NetSpout Gate 6 Evidence Integrity Build  
**Evaluator Persona:** Splunk Solutions Engineer (Networking background, zero NetSpout internal knowledge, no physical or virtual Cisco SD-WAN lab)  
**Primary Goal:** *"I want to demonstrate an SD-WAN brownout in Splunk, but I have no Cisco SD-WAN infrastructure."*  
**Baseline Test Execution:** Golden Path 01 Initial Run (Result: **FAIL**, see historical report `docs/acceptance/GOLDEN_PATH_01_SDWAN_BROWNOUT.md`)  
**Retest Outcome:** **PASS (16 / 16 Acceptance Criteria Satisfied)**

---

## 1. Test Environment

| Component | Specification / Configuration |
| :--- | :--- |
| **Splunk Enterprise** | Version 9.4.0 (build 6b4ebe426ca6), standalone Docker container `splunk-network-data-blaster` |
| **Splunk Web Interface** | `http://localhost:8800` (User: `admin`, App context: `netspout` and `search`) |
| **Splunk HEC Port** | `https://127.0.0.1:8888/services/collector` (SSL enabled, token `00000000-0000-0000-0000-000000000000`) |
| **Splunk REST API** | `https://127.0.0.1:8889` (used for destination observation queries) |
| **Target Index** | `idx_network_ops` |
| **NetSpout Daemon** | FastAPI 0.115 / Uvicorn running on `http://localhost:8081` (`backend/run.py`) |
| **NetSpout UI** | React 18 SPA built with Vite / TailwindCSS, hosted standalone and embedded in Splunk App `netspout` |
| **Test Client** | Chrome 140.0.7339.208 (macOS aarch64) driven via Chrome DevTools Protocol (CDP) |
| **Retest Execution Mode** | Automated End-to-End Product Walkthrough & Retest (`execute_gate6_retest.py`) |

---

## 2. Retest Run Identifiers & Ground Truth

| Metric | Positive Retest Run | Negative / Failure-State Run |
| :--- | :--- | :--- |
| **Run Correlation ID** | `NS-20260925-c521cd8b` | `NS-20260925-587e0e08` |
| **Target Scenario** | `cisco_sdwan_brownout` | `cisco_sdwan_brownout` |
| **Scenario Name** | *Enterprise WAN Circuit Brownout & App Route Failover* | *Enterprise WAN Circuit Brownout & App Route Failover* |
| **Target Index** | `idx_network_ops` | `idx_network_ops` |
| **HEC Endpoint** | `https://127.0.0.1:8888/services/collector` | `https://127.0.0.1:59999/services/collector` (Unreachable) |
| **Allow Insecure TLS** | `true` (Local Lab Self-Signed Cert) | `true` |
| **Generated Events** | **6** | **6** |
| **Dispatched Events** | **6** (HTTP 200 ACK) | **0** (Connection Refused) |
| **Observed in Splunk** | **6** (Confirmed via Splunk REST API) | **0** |
| **Simulation Status** | **PASS** | **PASS** |
| **Destination Validation** | **PASS** | **FAIL** |
| **Overall Verification** | **PASS** | **FAIL** |

---

## 3. Resolution of Previously Verified Defects

All 7 defects logged during the initial Golden Path 01 evaluation have been completely remediated, audited, and verified:

### GP01-P0-001: Telemetry Not Dispatched to Splunk (P0)
* **Initial Failure:** `POST /api/scenarios/{id}/run` generated 8 events in server memory but omitted `dispatch_telemetry=True`. 0 events reached Splunk.
* **Remediation:** 
  1. Updated `backend/app/main.py` route `/api/scenarios/{scenario_id}/run` to accept `dispatch_telemetry: bool = True` and pass active `transport_config` directly to `runner.run_scenario()`.
  2. Frontend `FiveStepWorkflow.tsx` now forwards configured pipeline parameters (`endpoint`, `token`, `index`, `allow_insecure_tls`) on run launch.
* **Verification:** Run `NS-20260925-c521cd8b` dispatched 6 events over HEC (`dispatch_succeeded: 6`, `dispatch_failed: 0`). HTTP 200 acknowledgments confirmed from Splunk.

### GP01-P0-002: False Evidence Semantics in UI (P0)
* **Initial Failure:** `FiveStepWorkflow.tsx` fell back to `total_events_generated` when `dispatched_events` or `observed_events` were null, certifying that events were observed in Splunk even when 0 were sent.
* **Remediation:**
  1. Bound UI metric counters strictly to `runResult.dispatch_succeeded` and `runResult.observed_count`.
  2. Implemented active observation polling against `/api/scenarios/runs/{run_id}/observation`, executing real REST searches against Splunk with progressive backoff.
  3. Enforced five strict evidence invariants in both backend and frontend.
* **Verification:** When dispatch succeeds, the UI displays `DISPATCHED: 6` and `OBSERVED: 6`. In the negative test (`NS-20260925-587e0e08`), when dispatch fails, the UI truthfully displays `DISPATCHED: 0`, `OBSERVED: 0`, and `VALIDATED: FAIL` despite `GENERATED: 6`.

### GP01-P1-003: Broken Connection Preflight Route (P1)
* **Initial Failure:** Step 3 "Test Connection" button called `POST /api/telemetry/test-hec` which returned `405 Method Not Allowed`.
* **Remediation:**
  1. Unified `/api/telemetry/test-connection`, `/api/telemetry/test-hec`, and `/api/telemetry/test-pipeline` into a single canonical handler in `backend/app/main.py`.
  2. Dispatcher `test_connection()` performs two-stage verification (HTTP reachability check + authenticated preflight canary event with sourcetype `netspout:preflight`).
  3. Returns canonical 5-state response schema (`NOT_CONFIGURED`, `CONFIGURED`, `REACHABLE`, `VERIFIED`, `ERROR`) with latency measurement.
* **Verification:** Clicking "Test Connection" returns HTTP 200 and transitions Step 3 badge to `VERIFIED IN SPLUNK (4ms)`.

### GP01-P1-004: Missing Run-Specific Copyable SPL and Deep Link (P1)
* **Initial Failure:** No SPL query or link was provided; users had to manually guess index and fields.
* **Remediation:**
  1. Engine dynamically generates canonical search string `index={target_idx} netspout_run_id="{run_id}"`.
  2. Added **"Copy SPL"** button (copies exact SPL to clipboard with toast notification) and **"Open in Splunk ↗"** deep link (`http://localhost:8800/en-US/app/search/search?q=search%20...`) to both Step 4 (Run) and Step 5 (Prove).
* **Verification:** Clicked "Copy SPL" and navigated via deep link directly to Splunk Search, displaying all 6 events for `NS-20260925-c521cd8b`.

### GP01-P2-005: Internal Mode Labels Leaked into Display Names (P2)
* **Initial Failure:** Card title was prefixed with developer jargon: `Mode A2: Enterprise WAN Circuit Brownout & App Route Failover`.
* **Remediation:**
  1. Sanitized use case names across canonical catalog and repository (`src/netspout_core/use_case_repo.py` and `netspout/catalog/scenarios.json`).
  2. Display name renders cleanly as `Enterprise WAN Circuit Brownout & App Route Failover` with clean taxonomy pills.
* **Verification:** Retest screenshot `retest_01` and `retest_02` confirm clean, professional naming with zero internal mode leaks.

### GP01-P2-006: Missing Sourcetype Context in Live Log Stream (P2)
* **Initial Failure:** Live log stream showed raw message strings without indicating which sourcetype or index each line represented.
* **Remediation:**
  1. Updated `StepRun.tsx` live log viewer to parse structured event metadata.
  2. Rendered distinct visual badges for each log line: purple badge for `sourcetype` (`cisco:sdwan:linkhealth`, `cisco:thousandeyes:metric`, `cisco:sdwan:BGP-5-ADJCHANGE`) and amber badge for `host` (`vEdge-Branch-Austin`, `ThousandEyes Synthetic Agent`).
* **Verification:** Retest screenshot `retest_05` clearly displays sourcetype and host tags for each emitted event.

### GP01-P3-007: Local HEC TLS Handling (P3)
* **Initial Failure:** Dockerized Splunk uses a self-signed TLS certificate on port 8888, causing Python `urllib` to fail cert verification unless explicitly configured.
* **Remediation:**
  1. Added `hec_allow_insecure_tls: bool = False` to `TelemetryTransportConfig` (secure by default).
  2. Added an explicit UI checkbox in Step 3: *"Allow self-signed certificate (Development/Lab only)"* bound to `allow_insecure_tls` (default OFF).
  3. Updated `telemetry_dispatcher.py` to catch `urllib.error.URLError` wrapping `SSLCertVerificationError` so TLS failures provide actionable messages rather than falling through to alternate port probes.
* **Verification:** With checkbox checked, HEC connection verifies immediately on `https://127.0.0.1:8888/services/collector`.

---

## 4. Phase-by-Phase Retest Walkthrough

### Phase 1 — Discovery
* **Action:** Opened NetSpout UI, filtered catalog by `WAN & SD-WAN`.
* **Observation:** The catalog rendered cleanly without mode prefixes. The card *Enterprise WAN Circuit Brownout & App Route Failover* was prominently displayed with badges: `cisco`, `wan`, `sdwan`, `latency`, `packet-loss`, `failover`, `thousandeyes`.
* **Visual Evidence:** `retest_01_discovery.png`

### Phase 2 — Choose
* **Action:** Selected *Enterprise WAN Circuit Brownout & App Route Failover* card.
* **Observation:** Card highlighted with cyan border and "Selected" checkmark. Bottom action bar activated with scenario summary: `6 Phases • Cisco SD-WAN • SLA Breach & Failover`.
* **Visual Evidence:** `retest_02_sdwan_selected.png`

### Phase 3 — Preview
* **Action:** Advanced to Step 2 (Preview).
* **Observation:** Inspected topology blueprint (`sdwan-vmanage-01`, `sdwan-vsmart-01`, `sdwan-vedge-01`, `sdwan-vedge-02`, transit underlays), required sourcetypes (`cisco:sdwan:linkhealth`, `cisco:sdwan:BGP-5-ADJCHANGE`, `cisco:thousandeyes:metric`), and 6-phase operational progression.
* **Visual Evidence:** `retest_03_preview_topology.png`

### Phase 4 — Connect Pipeline
* **Action:** Advanced to Step 3 (Connect). Checked "Allow self-signed certificate (Development/Lab only)" and clicked "Test Connection".
* **Observation:** HTTP POST to `/api/telemetry/test-connection` succeeded in 4ms. The connection state updated to **`VERIFIED IN SPLUNK`** with message: `Splunk HEC connection verified. Test event accepted (HEC HTTP 200: {"text":"Success","code":0}).`
* **Visual Evidence:** `retest_04_connect_verification.png`

### Phase 5 — Run Lifecycle Simulation
* **Action:** Clicked "Proceed to Run", then "Launch Scenario" with Run ID `NS-20260925-c521cd8b`.
* **Observation:** The scenario executed across all 9 lifecycle phases (`INITIALIZE`, `BASELINE`, `DEGRADE`, `FAULT`, `PROPAGATE`, `FAILOVER`, `RECOVER`, `VALIDATE`, `COMPLETE`). Live log stream rendered 6 events with purple sourcetype badges and yellow host badges. Delivery counters updated in real time:
  * Elapsed Time: **1.0s**
  * Generated: **6**
  * Dispatched: **6**
  * Observed in Splunk: **6**
  * Velocity: **6.0 EPS**
* **Visual Evidence:** `retest_05_baseline_phase.png`, `retest_06_degrade_phase.png`, `retest_07_failover_phase.png`, `retest_08_recovery_phase.png`

### Phase 6 — Splunk Observation
* **Action:** Clicked "Open in Splunk ↗" (or searched `index=idx_network_ops netspout_run_id="NS-20260925-c521cd8b"` in Splunk Web).
* **Observation:** Splunk Enterprise returned **`✓ 6 events`** indexed under `idx_network_ops`:
  * 3x `cisco:sdwan:linkhealth` (showing BFD latency jump from 16ms to 185ms, loss to 14.5%, and recovery)
  * 2x `cisco:sdwan:BGP-5-ADJCHANGE` (neighbor adjacency failover and restoration)
  * 1x `cisco:thousandeyes:metric` (SaaS synthetic latency elevated to 185ms)
  * All events stamped with `netspout_run_id="NS-20260925-c521cd8b"`, `netspout_scenario_id="cisco_sdwan_brownout"`, and ground-truth phase tags.
* **Visual Evidence:** `retest_09_splunk_evidence.png`

### Phase 7 — Validation Engine (Step 5: Prove)
* **Action:** Advanced to Step 5 (Prove Expected Condition).
* **Observation:** The audit dashboard reported complete verification:
  * Top Status Badges: `OVERALL VERIFICATION: PASS`, `SIMULATION: PASS`, `DESTINATION: PASS`
  * Metric Cards: `1. GENERATED: 6`, `2. DISPATCHED: 6`, `3. OBSERVED IN SPLUNK: 6`, `4. VALIDATED: PASS`
  * Contract Rules Table:
    * `SD-WAN Sourcetypes Present` (Expected: 1, Observed: 3) — **PASS**
    * `AppRoute Failover Action` (Expected: 1, Observed: 4) — **PASS**
    * `Link Health Transition` (Expected: restored, Observed: restored) — **PASS**
* **Visual Evidence:** `retest_10_validation_result.png`

### Phase 8 — Negative / Controlled Failure-State Verification
* **Action:** Re-configured HEC endpoint to unreachable port `https://127.0.0.1:59999/services/collector` and launched run `NS-20260925-587e0e08`.
* **Observation:** 
  * Generation succeeded (6 records generated in memory).
  * HEC dispatch failed with Connection Refused (`dispatch_succeeded: 0`, `dispatch_failed: 6`).
  * Destination observation returned 0 events (`observed_count: 0`).
  * The UI truthfully reported:
    * Header Badge: `OVERALL VERIFICATION: FAIL`, `SIMULATION: PASS`, `DESTINATION: FAIL`
    * Metric Cards: `1. GENERATED: 6`, `2. DISPATCHED: 0`, `3. OBSERVED IN SPLUNK: 0`, `4. VALIDATED: FAIL` (red)
  * **Invariant Verification:** Proved that NetSpout fails closed, never fabricating delivery or observation.
* **Visual Evidence:** `retest_11_failure_state.png`

---

## 5. Visual Evidence Archive

All screenshots were captured live via CDP in Chrome 140 and are permanently archived in `docs/acceptance/images/`:

| Figure | Image File | Description | Verification State |
| :--- | :--- | :--- | :---: |
| **Fig 1** | [retest_01_discovery.png](images/retest_01_discovery.png) | Step 1 Discover Use Cases: Sanitized names, 39 use cases, category filters. | **PASS** |
| **Fig 2** | [retest_02_sdwan_selected.png](images/retest_02_sdwan_selected.png) | Step 1 Discover: Filtered by `WAN & SD-WAN`, clean card selected without `Mode A2:` prefix. | **PASS** |
| **Fig 3** | [retest_03_preview_topology.png](images/retest_03_preview_topology.png) | Step 2 Preview: Cisco SD-WAN topology nodes, required sourcetypes, 6-phase progression. | **PASS** |
| **Fig 4** | [retest_04_connect_verification.png](images/retest_04_connect_verification.png) | Step 3 Connect: Preflight test passed with self-signed TLS toggle, badge `VERIFIED IN SPLUNK`. | **PASS** |
| **Fig 5** | [retest_05_baseline_phase.png](images/retest_05_baseline_phase.png) | Step 4 Run: Stamped Run ID `NS-20260925-c521cd8b`, "Copy SPL" & "Open in Splunk" buttons, sourcetype badges. | **PASS** |
| **Fig 6** | [retest_06_degrade_phase.png](images/retest_06_degrade_phase.png) | Step 4 Run: Progression into underlay degradation phase, real-time dispatch counters. | **PASS** |
| **Fig 7** | [retest_07_failover_phase.png](images/retest_07_failover_phase.png) | Step 4 Run: AppRoute SLA breach and BFD failover event dispatch. | **PASS** |
| **Fig 8** | [retest_08_recovery_phase.png](images/retest_08_recovery_phase.png) | Step 4 Run: Route fallback, BFD state restored, 100% completion (6/6 dispatched, 6/6 observed). | **PASS** |
| **Fig 9** | [retest_09_splunk_evidence.png](images/retest_09_splunk_evidence.png) | Splunk Web: Real search `index=idx_network_ops netspout_run_id="NS-20260925-c521cd8b"` returning **✓ 6 events**. | **PASS** |
| **Fig 10** | [retest_10_validation_result.png](images/retest_10_validation_result.png) | Step 5 Prove: Truthful audit metrics (`DISPATCHED: 6`, `OBSERVED: 6`), `DESTINATION: PASS`, `OVERALL: PASS`. | **PASS** |
| **Fig 11** | [retest_11_failure_state.png](images/retest_11_failure_state.png) | Negative Test: Unreachable endpoint proves failure semantics (`DISPATCHED: 0`, `OBSERVED: 0`, `VALIDATED: FAIL`). | **PASS** |

---

## 6. Acceptance Criteria Verification Matrix

| # | Acceptance Criterion | Baseline Evaluation | Retest Evaluation | Retest Evidence & Justification |
| :-: | :--- | :---: | :---: | :--- |
| **1** | **Use case discoverable** | PASS | **PASS** | Discoverable within 1 click via `WAN & SD-WAN` pill. Clean title without `Mode A2:` prefix. |
| **2** | **Scenario understandable** | PASS | **PASS** | Clear topology blueprint, network roles, and 6-phase operational lifecycle previewed. |
| **3** | **No Cisco infrastructure required** | PASS | **PASS** | Zero Cisco routers or controllers required; simulation generates all telemetry. |
| **4** | **Telemetry requirements understandable** | PASS | **PASS** | Explicitly lists `cisco:sdwan:linkhealth`, `cisco:sdwan:BGP-5-ADJCHANGE`, `cisco:thousandeyes:metric`. |
| **5** | **Splunk connection verifiable** | FAIL | **PASS** | "Test Connection" button executes preflight check and returns `VERIFIED IN SPLUNK (4ms)`. |
| **6** | **Simulation starts through UI** | PASS | **PASS** | "Launch Scenario" triggers runner, streams live logs, and forwards telemetry to HEC. |
| **7** | **Phase progression visible** | PASS | **PASS** | Real-time progression across all 9 phases with green checkmarks and status indicators. |
| **8** | **Correlated data generated** | PASS | **PASS** | 6 realistic events stamped with Run ID `NS-20260925-c521cd8b` and lifecycle phase tags. |
| **9** | **Data reaches Splunk** | FAIL | **PASS** | **6 events dispatched via HEC and acknowledged with HTTP 200.** |
| **10** | **Splunk evidence discoverable** | FAIL | **PASS** | Copyable SPL `index=idx_network_ops netspout_run_id="..."` and deep link locate all 6 events. |
| **11** | **Brownout observable in Splunk** | FAIL | **PASS** | Link health degradation (185ms latency, 14.5% loss) observable in Splunk Web. |
| **12** | **Expected recovery observable** | FAIL | **PASS** | Primary MPLS recovery and BGP adjacency restoration observable in Splunk Web. |
| **13** | **Validation engine confirms evidence** | PASS | **PASS** | Validation rules confirm SD-WAN sourcetypes, failover actions, and link recovery. |
| **14** | **Evidence semantics remain accurate** | FAIL | **PASS** | Counters reflect truthful delivery (`DISPATCHED: 6`, `OBSERVED: 6`), failing closed on error. |
| **15** | **No source-code knowledge required** | FAIL | **PASS** | Entire workflow navigable via UI buttons, copyable SPL, and deep links without code inspection. |
| **16** | **No manual dataset engineering** | PASS | **PASS** | Telemetry payloads, headers, timestamps, and indexes are fully automated by NetSpout. |

---

## 7. Product Determination

### **FINAL RETEST DETERMINATION: PASS**

**Summary Justification:**  
NetSpout has successfully remediated all defects identified during the initial Golden Path 01 evaluation. The application now provides a completely truthful, end-to-end evidence pipeline:
1. **The brownout is fully demonstrable in Splunk:** Dispatched events are received, indexed, and queryable in Splunk Enterprise within seconds.
2. **Evidence Semantics are 100% Truthful:** Counters reflect verified transport and indexed observation. When network failure occurs, the UI displays `DISPATCHED: 0`, `OBSERVED: 0`, and `VALIDATED: FAIL`.
3. **Connection Preflight is Robust:** Two-stage verification validates reachability and index authorization with clear latency metrics.
4. **Friction is Eliminated:** Copyable SPL and deep links allow immediate transition from NetSpout to Splunk Search.
