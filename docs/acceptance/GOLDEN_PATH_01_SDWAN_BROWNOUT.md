# NETSPOUT PRODUCT ACCEPTANCE TEST REPORT
## GOLDEN PATH 01 — SD-WAN BROWNOUT WITHOUT REAL INFRASTRUCTURE

**Test Execution Date:** 2026-09-24 / 2026-09-25  
**Product Version:** NetSpout Gate 5 Unified UX Build  
**Evaluator Persona:** Splunk Solutions Engineer (Networking background, zero NetSpout internal knowledge, no physical or virtual Cisco SD-WAN lab)  
**Primary Goal:** *"I want to demonstrate an SD-WAN brownout in Splunk, but I have no Cisco SD-WAN infrastructure."*

---

## 1. Test Environment

| Component | Specification / Configuration |
| :--- | :--- |
| **Splunk Enterprise** | Version 9.4.0 (build 6b4ebe426ca6), standalone container `splunk-network-data-blaster` |
| **Splunk Web Interface** | `http://localhost:8800` (User: `admin`) |
| **Splunk HEC Port** | `https://localhost:8888/services/collector` (SSL enabled, default token `00000000-0000-0000-0000-000000000000`) |
| **Splunk REST API** | `https://localhost:8889` |
| **Target Index** | `idx_network_ops` |
| **NetSpout Daemon** | FastAPI 0.115 / Uvicorn running on `http://localhost:8081` (`backend/run.py`) |
| **NetSpout UI** | React 18 SPA built with Vite / TailwindCSS, hosted at `http://localhost:8081` and embedded in Splunk App `netspout` |
| **Test Client** | Chrome 140.0.7339.208 (macOS aarch64) driven via Chrome DevTools Protocol (CDP) |
| **Execution Mode** | Read-Only Product Acceptance Test (Zero code, UI, scenario, or catalog modifications) |

---

## 2. Starting State

1. **Infrastructure Zero-State:**
   * No Cisco vManage, vSmart, or vEdge physical or virtual devices exist in the environment.
   * No Cisco SD-WAN telemetry collector or syslog forwarder is configured.
2. **Splunk Data Zero-State:**
   * No existing SD-WAN brownout data exists in Splunk for the active test period.
   * A search for `index=idx_network_ops sourcetype="cisco:sdwan:*"` for the current test run returns 0 events.
3. **User Knowledge State:**
   * The evaluator assumes the perspective of a Solutions Engineer who knows Splunk searching and networking concepts (BFD, jitter, loss, SLA policies), but has **zero knowledge** of NetSpout internal code, scenario IDs, backend Python modules, or catalog schemas.

---

## 3. User Goal

The evaluator sets out to complete the following five objectives using only the product UI:
1. **Discover:** Locate an SD-WAN brownout demonstration use case within NetSpout without consulting source code.
2. **Preview:** Understand the simulated topology, lifecycle phases, and telemetry sourcetypes generated.
3. **Connect:** Configure and verify the telemetry pipeline to the local Splunk HEC collector.
4. **Execute:** Run the simulation, monitor real-time phase progression, and inspect live log streams.
5. **Observe & Prove:** Search Splunk Web to observe the brownout and app-route failover, then confirm scenario validation assertions in NetSpout.

---

## 4. Phase 4 — Discovery

* **Navigation:** The user opens the NetSpout home screen (`http://localhost:8081`).
* **Visual Presentation:** The screen opens directly to **Step 1: Discover Use Cases**, displaying a searchable catalog of **39 use cases** across 7 category filter pills: `All Categories`, `Enterprise LAN`, `Data Center & Fabric`, `WAN & SD-WAN`, `Cloud Networking`, `Wireless & Edge`, and `Security & Policy`.
* **Action:** The user clicks the `WAN & SD-WAN` category pill.
* **Result:** The catalog immediately filters from 39 cards down to 4 cards:
  1. *Mode A2: Enterprise WAN Circuit Brownout & App Route Failover* (SD-WAN)
  2. *Cisco SD-WAN Overlay Degradation* (SD-WAN)
  3. *BGP Route Leak & Blackhole Incident* (WAN Routing)
  4. *Multi-Cloud Transit Gateway Blackhole* (Cloud WAN)
* **User Assessment:** Discoverability is immediate and intuitive (1 click). Tag badges (`cisco`, `wan`, `sdwan`, `latency`, `packet-loss`, `failover`, `thousandeyes`) confirm exact alignment with the goal.
* **Friction Noted:** The scenario card is titled `Mode A2: Enterprise WAN Circuit Brownout & App Route Failover`. The prefix `Mode A2:` is internal classification jargon that creates minor hesitation for a new user.

---

## 5. Phase 5 — Choose

* **Action:** The user clicks the blue button **"Select Scenario"** on card `Mode A2: Enterprise WAN Circuit Brownout & App Route Failover`.
* **Visual Response:**
  * The selected card receives a bright blue highlight border and a blue badge indicating `Selected`.
  * The fixed bottom action bar illuminates:  
    `Selected: Mode A2: Enterprise WAN Circuit Brownout & App Route Failover | 6 Phases • Cisco SD-WAN • SLA Breach & Failover`
  * An enabled action button appears: **"Configure & Run Scenario ->"**.
* **Result:** The user clicks "Configure & Run Scenario ->" and is transitioned directly into Step 2 (Preview).

---

## 6. Phase 6 — Preview

* **Visual Presentation:** Step 2 displays a comprehensive operational preview with three primary cards:
  1. **Scenario Blueprint & Topology:**
     * Topology Blueprint: `cisco_sdwan`
     * Topology Nodes: `sdwan-vmanage-01` (Controller), `sdwan-vsmart-01` (Orchestrator), `sdwan-vedge-01` (Branch Edge), `sdwan-vedge-02` (Hub Edge), `inet-trans-01` (Internet Transit), `mpls-trans-01` (MPLS Underlay).
  2. **Required Telemetry & Sourcetypes:**
     * `cisco:sdwan:events`
     * `cisco:sdwan:bfd`
     * `cisco:sdwan:approute`
     * `thousandeyes:test`
  3. **Scenario Phase Lifecycle (6 Phases Previewed):**
     * Phase 1: Baseline Healthy State (SLA met, BFD RTT < 20ms)
     * Phase 2: Underlay Impairment Injection (Latency 185ms, Packet Loss 14.5%)
     * Phase 3: ThousandEyes Synthetic Breach (HTTP transaction time > 1200ms)
     * Phase 4: SD-WAN AppRoute SLA Violation (`violation-action: log-and-switch`)
     * Phase 5: Dynamic Tunnel Policy Failover (Traffic diverted from MPLS to Internet DIA)
     * Phase 6: Circuit Recovery & State Fallback (Jitter normalizes, BFD recovered)
* **User Assessment:** Outstanding clarity. The user knows exactly what network events will be simulated, which devices are involved, and what sourcetypes will be emitted, fulfilling the requirement without physical Cisco hardware.

---

## 7. Phase 7 — Connect

* **Action:** The user clicks "Continue to Connection ->" to enter Step 3.
* **Pre-populated Parameters:**
  * Splunk HEC URL: `https://localhost:8888/services/collector`
  * HEC Token: `00000000-0000-0000-0000-000000000000`
  * Target Index: `idx_network_ops`
  * Sourcetype: `cisco:sdwan:events`
* **Action:** The user clicks **"Test Connection"** to verify that Splunk is reachable.
* **CRITICAL FAILURE ENCOUNTERED (P1):**
  * The UI displays a red error badge: **`CONFIGURED (Method Not Allowed)`**.
  * The HTTP request `POST /api/telemetry/test-hec` failed with HTTP status **`405 Method Not Allowed`**.
  * *Investigation:* The frontend `StepConnect.tsx` calls `POST /api/telemetry/test-hec`, but the backend API in `backend/app/main.py` only implements `POST /api/telemetry/test-pipeline`.
  * *Impact on User:* A new user assumes the Splunk HEC server is broken or rejected the credentials. However, because the user has no choice, they click **"Continue to Execution ->"** to see if the run works anyway.

---

## 8. Phase 8 — Run

* **Execution Configuration:**
  * Scenario: `Mode A2: Enterprise WAN Circuit Brownout & App Route Failover`
  * Index: `idx_network_ops`
  * Speed: `1x (Real-time)`
  * Run ID: `NS-20260925-abaefac2` (auto-generated unique correlation ID)
* **Action:** The user clicks **"Start Simulation"**.
* **Visual Response & Progression:**
  * The simulation engine activates immediately.
  * The **Phase Tracker** visually steps through 9 lifecycle stages with green checks:
    * `1. Phase 1: Baseline Healthy`
    * `2. Phase 2: Underlay Latency Degrade`
    * `3. Phase 3: Packet Loss Escalation`
    * `4. Phase 4: ThousandEyes Synthetic Breach`
    * `5. Phase 5: SD-WAN SLA Violation`
    * `6. Phase 6: AppRoute Policy Failover`
    * `7. Phase 7: Secondary Path Stable`
    * `8. Phase 8: MPLS Underlay Recovery`
    * `9. Phase 9: Route Fallback & Stabilization`
  * The **Correlated Live Log Stream** displays 8 realistic telemetry events containing timestamp, Run ID `NS-20260925-abaefac2`, device names, and detailed event payloads:
    * Event 1: `%CISCO-SDWAN-BFD-6-STATE_CHANGE: vEdge-01 color=mpls latency=18ms loss=0.0% status=UP`
    * Event 2: `%CISCO-SDWAN-BFD-4-PERF_DEGRADED: vEdge-01 color=mpls latency=185ms loss=14.5% jitter=32ms`
    * Event 3: `thousandeyes: agent=TE-Branch1 test="ERP App Transaction" response_time=1450ms packet_loss=15.2% sla_breached=true`
    * Event 4: `%CISCO-SDWAN-APP-ROUTE-3-SLA_BREACH: Policy=Voice-Video-SLA color=mpls violated latency_threshold=100ms`
    * Event 5: `%CISCO-SDWAN-POLICY-5-FAILOVER: Traffic diverted from color=mpls to color=biz-internet tunnel=active`
    * Event 6: `%CISCO-SDWAN-BFD-6-STATE_RESTORED: vEdge-01 color=mpls latency=19ms loss=0.0% status=NORMAL`
  * After ~10 seconds, the run status updates to **`COMPLETED`**, and the bottom bar illuminates **"View Evidence & Validation ->"**.

---

## 9. Phase 9 — Splunk Observation

* **Action:** The user opens Splunk Web (`http://localhost:8800`) to verify the telemetry in the target index `idx_network_ops` and present the brownout to stakeholders.
* **Searches Executed by User:**
  1. `index=idx_network_ops netspout_run_id="NS-20260925-abaefac2"`
     * **Result:** **`0 events found`**
  2. `index=idx_network_ops sourcetype="cisco:sdwan:*"` (All Time)
     * **Result:** **`0 events found`**
  3. `index=idx_network_ops sourcetype="thousandeyes:*"`
     * **Result:** **`0 events found`**
  4. `index=idx_network_ops earliest=-15m`
     * **Result:** **`0 events found matching the scenario run`**
* **PRIMARY PRODUCT DEFECT (P0):**
  * **Telemetry was NEVER dispatched to Splunk.**
  * *Investigation:* In `backend/app/main.py` line 964, the route handler `POST /api/scenarios/{scenario_id}/run` accepts `ScenarioRunRequest` but does **not** set `dispatch_telemetry=True`.
  * Consequently, `scenario_runner.run_scenario()` generates the 8 brownout events in Python memory, feeds them to the UI WebSocket/logs endpoint, but **does not invoke the HEC dispatcher** to transmit them to Splunk!
  * **Impact:** The Solutions Engineer cannot show any brownout events in Splunk. The core product promise fails.

---

## 10. Phase 10 — Validation Engine

* **Action:** The user returns to NetSpout and clicks **"View Evidence & Validation ->"** to inspect Step 5 (Prove).
* **Validation Contract Results Displayed:**

| Validation Assertion | Target Metric | Status | Evidence / Detail |
| :--- | :--- | :--- | :--- |
| **Telemetry Volume** | Min 5 events | **PASS** | 8/5 events evaluated |
| **Brownout Progression** | Baseline -> Degraded -> Recovered | **PASS** | Complete 9-phase state transition verified |
| **Telemetry Diversity** | 3 distinct sourcetypes | **PASS** | `cisco:sdwan:events`, `cisco:sdwan:approute`, `thousandeyes:test` present |
| **Network Effect** | Failover triggered | **PASS** | MPLS -> Biz-Internet route diversion verified |
| **Overall Use Case** | Contract compliance | **PASS** | All contract rules satisfied |

* **User Assessment:** The Gate 4 validation contract engine functions logically against generated events. However, because events never reached Splunk, the validation was performed entirely on local generator memory.

---

## 11. Phase 11 — Evidence Semantics

* **CRITICAL MISLEADING EVIDENCE DEFECT (P0 / P1):**
  * At the top of Step 5 (Prove), NetSpout displays a 4-tier pipeline progress card:
    * `1. GENERATED: 8`
    * `2. DISPATCHED: 8`  *(FALSE)*
    * `3. OBSERVED: 8`   *(FALSE)*
    * `4. VALIDATED: PASS`
  * **The Problem:** The user is told that 8 events were dispatched to Splunk and 8 events were observed in Splunk, when in reality **0 events were dispatched** and **0 events exist in Splunk**.
  * *Root Cause Analysis:* In `frontend/src/components/workflow/FiveStepWorkflow.tsx` line 161:
    ```typescript
    dispatched_events: (runResult as any).dispatched_events ?? runResult.total_events_generated ?? 8,
    observed_events: (runResult as any).observed_events ?? runResult.total_events_generated ?? 8,
    ```
    The frontend unconditionally falls back to `total_events_generated` if the backend doesn't provide distinct counts.
  * **Evaluation:** This breaks the foundational trust of the product. The UI certifies that data is in Splunk when Splunk is completely empty.

---

## 12. Phase 12 — Cleanup

* **Post-Run State:**
  * The scenario run terminated cleanly with status `COMPLETED`.
  * No orphaned background processes, recurring timers, or endless syslog loops were left running.
  * The run record `NS-20260925-abaefac2` remained inspectable in memory and in the UI log viewer.
  * The user can click "Run Another Scenario" to reset back to Step 1 without browser reload.

---

## 13. Phase 13 — Failure-State Test

* **Controlled Failure Injection:**
  * To test failure handling, the destination was pointed to an unconfigured or unreached destination.
  * **Finding:** Because `FiveStepWorkflow.tsx` unconditionally defaults `observed_events` to `total_events_generated`, NetSpout **still reports `DISPATCHED: 8`, `OBSERVED: 8`, and `VALIDATED: PASS`** even when Splunk is completely unreachable!
  * **Determination:** NetSpout fails open instead of failing closed. It does not verify Splunk receipt before claiming observation.

---

## 14. Phase 14 — Interaction Count

| Workflow Stage | Action Taken | Meaningful Clicks |
| :--- | :--- | :---: |
| **Discovery** | Click `WAN & SD-WAN` filter pill on catalog | 1 |
| **Choose** | Click `Select Scenario` on SD-WAN Brownout card | 1 |
| **Preview** | Click `Configure & Run Scenario ->` bottom button | 1 |
| **Connect** | Click `Continue to Connection ->` bottom button | 1 |
| **Verify Connection** | Click `Test Connection` button (returned 405) | 1 |
| **Proceed to Run** | Click `Continue to Execution ->` bottom button | 1 |
| **Execution** | Click `Start Simulation` button | 1 |
| **Validation** | Click `View Evidence & Validation ->` bottom button | 1 |
| **Total Meaningful Interactions** | **Complete end-to-end user journey** | **8 clicks** |

* **UX Assessment:** The interaction path is remarkably lean and well-structured. A user can traverse the entire 5-step lifecycle in exactly 8 clicks.

---

## 15. Phase 15 — Documentation Dependency

* **Score: NONE / OPTIONAL**
* The stepper workflow (Discover -> Preview -> Connect -> Run -> Prove) is completely self-evident.
* No external manuals, PDFs, or CLI guides were needed to discover the scenario or trigger the simulation.

---

## 16. Phase 16 — Internal Knowledge Dependency

* **Score: BLOCKING (for Splunk Verification)**
  * Discovering and running the scenario required **zero** internal knowledge.
  * However, discovering why Splunk was empty required inspecting backend route handlers (`backend/app/main.py`), discovering that `dispatch_telemetry=False` was hardcoded, and investigating why the connection test failed with HTTP 405.
  * Furthermore, NetSpout did not provide a pre-constructed SPL search query to copy-paste into Splunk.

---

## 17. Friction Register

| ID | Priority | Workflow Step | Description | Impact |
| :--- | :---: | :--- | :--- | :--- |
| **FR-01** | **P0** | **Step 4: Run / Backend** | `/api/scenarios/{id}/run` does not set `dispatch_telemetry=True`. Events are generated in memory but never sent to Splunk HEC. | **Blocks primary goal.** Splunk has 0 events; brownout cannot be demonstrated in Splunk. |
| **FR-02** | **P0** | **Step 5: Prove** | Step 5 displays `DISPATCHED: 8` and `OBSERVED: 8` due to frontend defaulting to generated count, even when 0 events were sent or observed. | **Destroys evidence credibility.** Falsely claims events were observed in Splunk. |
| **FR-03** | **P1** | **Step 3: Connect** | "Test Connection" button calls `POST /api/telemetry/test-hec` which returns `405 Method Not Allowed` (backend has `/api/telemetry/test-pipeline`). | Connection verification is broken; leaves user believing Splunk is down. |
| **FR-04** | **P1** | **Step 4 & 5: Run / Prove** | NetSpout does not provide an "Open in Splunk" link or copyable SPL search string (e.g. `index=idx_network_ops netspout_run_id="..."`). | User must guess the index, sourcetypes, and field names to construct search. |
| **FR-05** | **P2** | **Step 1: Discover** | Scenario title contains developer jargon prefix: `Mode A2: ...`. | Confuses new users who do not know NetSpout's internal catalog nomenclature. |
| **FR-06** | **P2** | **Step 4: Run** | Correlated Live Log Stream displays raw log lines but omits sourcetype and target index badges. | User cannot easily see which sourcetype corresponds to which log line. |
| **FR-07** | **P3** | **Step 3: Connect** | HEC port defaults to `8888` (HTTPS) without an explicit SSL verification toggle in the UI. | Self-signed Splunk certs may silently fail in some environments without warning. |

---

## 18. Screenshots / Visual Evidence

The following visual evidence was captured during live execution of Golden Path 01 and archived in `docs/acceptance/images/`:

| Figure | Image File | Description |
| :--- | :--- | :--- |
| **Fig 1** | [gp01_01_discovery.png](images/gp01_01_discovery.png) | Step 1 Discover Use Cases: Landing catalog showing 39 use cases and category pills. |
| **Fig 2** | [gp01_02_sdwan_selected.png](images/gp01_02_sdwan_selected.png) | Step 1 Discover: Filtered by `WAN & SD-WAN`, selecting `Mode A2: SD-WAN Brownout`. |
| **Fig 3** | [gp01_03_preview_topology.png](images/gp01_03_preview_topology.png) | Step 2 Preview: Topology blueprint `cisco_sdwan`, 6 phases, and required sourcetypes. |
| **Fig 4** | [gp01_04_connect_verification.png](images/gp01_04_connect_verification.png) | Step 3 Connect: Pre-populated HEC parameters and `405 Method Not Allowed` error banner. |
| **Fig 5** | [gp01_05_baseline_phase.png](images/gp01_05_baseline_phase.png) | Step 4 Run: Simulation running, Phase 1 Baseline check, and live log stream. |
| **Fig 6** | [gp01_06_degrade_phase.png](images/gp01_06_degrade_phase.png) | Step 4 Run: Progression into underlay degradation and ThousandEyes synthetic breach. |
| **Fig 7** | [gp01_07_failover_phase.png](images/gp01_07_failover_phase.png) | Step 4 Run: SD-WAN AppRoute SLA violation and policy failover to Internet DIA. |
| **Fig 8** | [gp01_08_recovery_phase.png](images/gp01_08_recovery_phase.png) | Step 4 Run: Phase 9 route fallback, recovery, and completion with Run ID `NS-20260925-abaefac2`. |
| **Fig 9** | [gp01_09_splunk_evidence.png](images/gp01_09_splunk_evidence.png) | Splunk Web: Search for `index=idx_network_ops netspout_run_id="NS-20260925-abaefac2"` returning **0 events**. |
| **Fig 10** | [gp01_10_validation_result.png](images/gp01_10_validation_result.png) | Step 5 Prove: Validation contract evaluation table and false `DISPATCHED: 8 / OBSERVED: 8` metrics. |

---

## 19. Acceptance Criteria Verification

| Criterion | Evaluation | Detail |
| :--- | :---: | :--- |
| **1. Use case discoverable** | **PASS** | Discoverable within 1 click via `WAN & SD-WAN` pill. |
| **2. Scenario understandable** | **PASS** | Objectives, network devices, and 6-phase lifecycle clearly explained. |
| **3. No Cisco infrastructure required** | **PASS** | Zero Cisco routers or controllers required; simulation generates all telemetry. |
| **4. Telemetry requirements understandable** | **PASS** | Explicitly lists `cisco:sdwan:events`, `cisco:sdwan:bfd`, `thousandeyes:test`. |
| **5. Splunk connection verifiable** | **FAIL** | "Test Connection" button fails with HTTP 405 (`/api/telemetry/test-hec`). |
| **6. Simulation starts through UI** | **PASS** | "Start Simulation" button triggers 9-phase generator and live log stream. |
| **7. Phase progression visible** | **PASS** | UI displays real-time progression across all phases with status badges. |
| **8. Correlated data generated** | **PASS** | 8 realistic events generated with consistent Run ID `NS-20260925-abaefac2`. |
| **9. Data reaches Splunk** | **FAIL** | **0 events dispatched to Splunk.** `dispatch_telemetry=True` missing in runner API. |
| **10. Splunk evidence discoverable** | **FAIL** | Searching Splunk returns 0 events for the run. |
| **11. Brownout observable in Splunk** | **FAIL** | No brownout data exists in Splunk to observe or visualize. |
| **12. Expected recovery observable** | **FAIL** | No recovery data exists in Splunk. |
| **13. Validation engine confirms evidence** | **PASS** | Validation contract correctly verifies generated rules. |
| **14. Evidence semantics remain accurate** | **FAIL** | Step 5 falsely claims 8 events dispatched and 8 events observed. |
| **15. No source-code knowledge required** | **FAIL** | Diagnosing the missing Splunk data required inspecting backend API code. |
| **16. No manual dataset engineering** | **PASS** | Telemetry payloads are automatically synthesized without CSV/scripting. |

---

## 20. Product Determination

### **FINAL DETERMINATION: FAIL**

**Justification:**  
While NetSpout demonstrates an exceptionally well-designed UX architecture—allowing a user to discover, preview, configure, and execute an SD-WAN brownout scenario in just 8 clicks without any Cisco equipment—it **fails its primary core value proposition**:

1. **The brownout cannot be demonstrated in Splunk:** The scenario execution API generates events only within backend memory and does not dispatch them over HEC to Splunk (`dispatch_telemetry=False`).
2. **False Evidence Semantics:** The UI actively misleads the user by asserting that 8 events were dispatched and 8 events were observed in Splunk, when in fact Splunk contains 0 events.
3. **Broken Preflight Check:** The "Test Connection" button fails with HTTP 405 Method Not Allowed.

A Splunk Solutions Engineer cannot successfully use this build in front of a customer or in a demonstration environment without manual developer intervention.

---

## 21. Recommended Improvements (Post-Acceptance Roadmap)

1. **Fix Scenario Runner Dispatch (P0):**
   * In `backend/app/main.py` (`POST /api/scenarios/{scenario_id}/run`), pass `dispatch_telemetry=True` (or bind it to a user toggle in `ScenarioRunRequest`) so that the scenario runner actually transmits generated telemetry to the configured Splunk HEC endpoint.
2. **Correct Evidence Semantics in UI (P0):**
   * In `frontend/src/components/workflow/FiveStepWorkflow.tsx`, do not default `dispatched_events` and `observed_events` to `total_events_generated`.
   * Return real dispatch counts (`events_sent`, `events_acked`) from the backend HEC dispatcher.
   * If telemetry was not dispatched or observed, Step 5 should truthfully indicate `DISPATCHED: 0` and `OBSERVED: 0` with a warning alert.
3. **Align Connection Test API Route (P1):**
   * Route `POST /api/telemetry/test-hec` in `backend/app/main.py` or update `frontend/src/components/workflow/StepConnect.tsx` to call `POST /api/telemetry/test-pipeline`.
4. **Provide Copyable SPL & Deep Link to Splunk Search (P1):**
   * In Step 4 and Step 5, display a copyable search card:  
     `index=idx_network_ops netspout_run_id="<RUN_ID>"`  
     and a direct link: `http://localhost:8800/en-US/app/netspout/search?q=search%20index%3Didx_network_ops%20netspout_run_id%3D...`.
5. **Sanitize Scenario Names for End-Users (P2):**
   * Strip developer mode codes like `Mode A2:` from customer-facing titles, presenting clean names like `Enterprise WAN Circuit Brownout & App Route Failover`.
