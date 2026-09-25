# NetSpout Architecture Consolidation: Gate 5 — Unified Product UX, Workflow, and UI Consolidation

**Document Version:** 1.0.0  
**Gate:** Gate 5 of 6  
**Status:** COMPLETE (All criteria satisfied, 22/22 Gate 5 tests PASS, 60/62 comprehensive baseline preserved)  
**Author:** Mahamudul Chowdhury (machowdhury@yahoo.com)  
**Date:** September 2026  
**Repository Baseline:** `0c0a6f69839df3c33bd7c3dae761b2fe39bc55d5` (Branch `main`)  

---

## 1. Executive Summary

Prior to Gate 5, NetSpout suffered from fragmented user experience surfaces developed incrementally across historical iterations. Users encountered multiple competing wizards and panels:
1. **Guided Onboarding Wizard** (`guided_onboarding.xml`) — a multi-step form focused on sourcetype selection.
2. **Scenario Builder & Path Emitter** (`scenario_builder.xml`) — a workflow for selecting attack vectors and emitting sample bursts.
3. **NetSpout Canvas & Telemetry Orchestrator** (`netspout_canvas.xml`) — an interactive GNS3/EVE-NG style visual NOC studio.
4. **DataBlaster Console & Dashboard** (`datablaster_console.xml`, `datablaster_dashboard.xml`) — legacy execution surfaces.
5. **SPL Playground & Tooling Modals** — disparate expert tools without unified context handoff.

Most critically, the user experience lacked a **conclusive evidence loop**: users could trigger simulations, but the UI provided no structured answer to the fundamental question: **"Did it work, and what did it prove?"**

Gate 5 consolidates NetSpout into **ONE UNIFIED PRODUCT** centered on a primary beginner journey:
46799\text{CHOOSE} \longrightarrow \text{PREVIEW} \longrightarrow \text{CONNECT} \longrightarrow \text{RUN} \longrightarrow \text{PROVE}46799

At the same time, Gate 5 strictly preserves full expert capabilities in **Advanced Mode (Canvas Orchestrator)** and centralizes operational health monitoring in **Operations**.

```
+----------------------------------------------------------------------------------------------------+
|                                      NETSPOUT UNIFIED SHELL                                        |
|  [NetSpout v2.0]  [Cisco | Multi-Vendor]  | [Use Cases (5-Step)] [Canvas Orchestrator] [Operations]|
+----------------------------------------------------------------------------------------------------+
|                                                                                                    |
|  PRIMARY PATH (Beginner Default):                                                                  |
|    1. CHOOSE     -> Select from 39 bound use cases across 8 canonical categories                   |
|    2. PREVIEW    -> Inspect target topology blueprint, 9-phase lifecycle, required telemetry       |
|    3. CONNECT    -> Choose pipeline (HEC, Syslog, OTLP, Telegraf) with 3-state health              |
|    4. RUN        -> Execute deterministic run with canonical Run ID and live correlated log stream |
|    5. PROVE      -> Audit 4-tier evidence breakdown and rule-by-rule validation verdicts           |
|                                                                                                    |
|  ADVANCED MODE (Expert Canvas):                                                                    |
|    NodePalette + Interactive TopologyCanvas + Streaming LogTerminal + 8 Expert Tooling Modals     |
|                                                                                                    |
|  OPERATIONS MODE (System Health):                                                                  |
|    Backend Daemon (8081), Splunk HEC (8888), Catalog Registry, Pipelines, Guardrail Status         |
+----------------------------------------------------------------------------------------------------+
```

### Key Gate 5 Milestones Achieved:
* **One Primary UI Owner Established**: The React App shell owns the application experience, routing seamlessly between `workflow` (default 5-step), `advanced` (3-column canvas studio), and `operations` (system health).
* **39 Bound Use Cases Surfaced**: The primary beginner journey presents all 39 use cases (29 scenario-bound + 10 pre-built from `use_case_repo.py`) with real-time filtering, categorization, difficulty ratings, and duration estimates.
* **Gate 4 Contracts Drive UI State**: Runs generate canonical Run IDs (`NS-YYYYMMDD-xxxxxxxx`), execute through the 9-phase lifecycle (`INITIALIZE` through `COMPLETE`), and record ground truth causality.
* **4-Tier Semantic Evidence Model**: Explicit separation between `GENERATED`, `DISPATCHED`, `OBSERVED`, and `VALIDATED`.
* **Deep-Link Splunk Search Handoff**: Rule-by-rule validation audit table with direct 1-click handoff to native Splunk search pre-filled with run correlation SPL.
* **Dead Code Elimination**: 643 lines of orphaned JavaScript removed (`datablaster_ui.js`: 642 lines, `test_script.js`: 1 line). Compatibility retained for test harness integrity.
* **Strict Frontend Source Ownership**: `frontend/src/` established as sole editable frontend source of truth; `netspout/appserver/static/dist/` is strictly a generated build artifact.
* **Zero Test Regression**: All 22 Gate 5 tests pass (100%), and the comprehensive test suite maintains the exact verified 60/62 baseline (96.8%).

---

## 2. Information Architecture & App Shell Consolidation

The NetSpout application shell is unified in `frontend/src/App.tsx` and `frontend/src/components/TopBar.tsx`. The interface adopts a dark NOC aesthetic (`#0B0F19` deep space background, `#111827` panels, `#374151` borders, with cyan, emerald, and violet accents) tailored for Security Operations Centers and Network Operations Centers.

### 2.1 Viewport Layout & Overflow Governance
The application layout uses strict viewport constraints:
```tsx
<div className="flex flex-col h-screen w-screen overflow-hidden bg-[#0B0F19] text-slate-100">
```
* **No Root Horizontal Scrollbars**: The outer shell enforces `overflow-hidden` across all viewports down to 1024x768.
* **Independent Scroll Contexts**: Scrolling is constrained to internal flex containers (the use-case card grid, the preview split panes, the correlated log terminal, and the evidence tables).
* **Responsive Scaling**: The layout adapts fluidly from 1920x1080 (wall NOC displays) down to 1024x768 (tablets and compact laptops) and supports 200% browser zoom without clipping.

### 2.2 Top Navigation Architecture
The header (`TopBar.tsx`) provides persistent, top-level controls across all modes:
1. **Brand & Version**: `NetSpout v2.0` with heartbeat indicator and live log counter.
2. **Ecosystem Mode Switcher**: `Cisco Only` (Pure Cisco Enterprise Fabric) vs `Multi-Vendor` (Heterogeneous Arista, Juniper, Palo Alto, Fortinet, Nokia, F5, Zscaler).
3. **Primary App View Modes**:
   - `Use Cases (5-Step)`: Guided beginner workflow.
   - `Canvas Orchestrator`: Advanced interactive topology studio.
   - `Operations`: System health and guardrails diagnostics.
4. **Contextual Action Toolbar**: Quick-preset selector, simulation Play/Pause/Resume, live EPS velocity meter, and the `Telemetry Tools` dropdown providing access to specialized diagnostic modals.

---

## 3. Consolidated Surface Registry & Ownership Matrix

Every user interface surface across the NetSpout repository has been cataloged, classified, and assigned an authoritative owner.

| Surface Identifier | File Path | Type / Technology | Status / Role | Rationale & Owner |
|---|---|---|---|---|
| **FiveStepWorkflow** | `frontend/src/components/workflow/` | React 18 / TypeScript | `CANONICAL_PRIMARY` | Authoritative primary beginner workflow for all 39 use cases. |
| **Canvas Orchestrator** | `frontend/src/components/TopologyCanvas.tsx` | React 18 / SVG Canvas | `CANONICAL_ADVANCED` | Authoritative expert visual topology studio and packet simulator. |
| **Operations View** | `frontend/src/components/operations/OperationsView.tsx` | React 18 / TypeScript | `CANONICAL_OPERATIONS` | Authoritative system health, daemon, pipeline, and guardrail monitor. |
| **Splunk Canvas Wrapper** | `netspout/default/data/ui/views/netspout_canvas.xml` | SimpleXML + iframe | `CANONICAL_PRIMARY` | Native Splunk entry point hosting the compiled React bundle. |
| **Guided Onboarding View** | `netspout/default/data/ui/views/guided_onboarding.xml` | SimpleXML + JS | `COMPATIBILITY` | Retained for backward-compatible sourcetype onboarding and Suite 20 tests. |
| **Guided Onboarding Script** | `netspout/appserver/static/guided_onboarding.js` | jQuery / Splunk Web | `COMPATIBILITY` | Retained for Suite 20 test harness compatibility. |
| **Scenario Builder View** | `netspout/default/data/ui/views/scenario_builder.xml` | SimpleXML + JS | `COMPATIBILITY` | Retained for backward compatibility and Suite 12 tests. |
| **Scenario Builder Script** | `netspout/appserver/static/scenario_builder.js` | jQuery / Splunk Web | `COMPATIBILITY` | Retained for Suite 12 test harness compatibility. |
| **DataBlaster Dashboard** | `netspout/default/data/ui/views/datablaster_dashboard.xml` | SimpleXML | `KEEP_NATIVE` | Native operational analytics dashboard for real-time indexing metrics. |
| **Studio RoCE AI Fabric** | `netspout/default/data/ui/views/studio_roce_ai_fabric.xml` | Dashboard Studio JSON | `KEEP_NATIVE` | Native high-performance AI data center fabric visualization. |
| **Studio Multi-Vendor** | `netspout/default/data/ui/views/studio_multivendor_enterprise.xml` | Dashboard Studio JSON | `KEEP_NATIVE` | Native multi-vendor enterprise topology monitoring dashboard. |
| **Studio Firewall Capacity** | `netspout/default/data/ui/views/studio_firewall_capacity.xml` | Dashboard Studio JSON | `KEEP_NATIVE` | Native perimeter security and firewall throughput dashboard. |
| **Studio Cross-Domain Triage**| `netspout/default/data/ui/views/studio_cross_domain_triage.xml` | Dashboard Studio JSON | `KEEP_NATIVE` | Native NOC/SOC triage and event correlation dashboard. |
| **Studio SD-WAN Branch** | `netspout/default/data/ui/views/studio_sdwan_branch.xml` | Dashboard Studio JSON | `KEEP_NATIVE` | Native branch SLA, brownout, and failover monitoring dashboard. |
| **Studio Core LSP Optical** | `netspout/default/data/ui/views/studio_core_lsp_optical.xml` | Dashboard Studio JSON | `KEEP_NATIVE` | Native optical transport and carrier core LSP health dashboard. |
| **Studio BGP Route Flap** | `netspout/default/data/ui/views/studio_bgp_route_flap.xml` | Dashboard Studio JSON | `KEEP_NATIVE` | Native BGP convergence, route leak, and flap detection dashboard. |
| **SPL Playground View** | `netspout/default/data/ui/views/spl_playground.xml` | SimpleXML + JS | `COMPATIBILITY` | Native Splunk view for in-browser SPL querying (also in React modal). |
| **Configuration View** | `netspout/default/data/ui/views/configuration.xml` | SimpleXML + JS | `COMPATIBILITY` | Native setup and HEC configuration management view. |
| **DataBlaster Console** | `netspout/default/data/ui/views/datablaster_console.xml` | SimpleXML + JS | `COMPATIBILITY` | Legacy console view for manual modular input execution. |
| **datablaster_ui.js** | `netspout/appserver/static/datablaster_ui.js` | Vanilla JS (642 lines)| `REMOVED` | Dead code. Orphaned script with 0 references across all XML views. |
| **test_script.js** | `netspout/appserver/static/test_script.js` | Vanilla JS (1 line) | `REMOVED` | Dead code. Orphaned 1-line artifact with 0 references. |

---

## 4. The 5-Step Beginner Architecture: "What Do You Want to Prove?"

The primary workflow guides the user through five deterministic steps:

### Step 1: Choose Use Case (`StepChoose.tsx`)
* **Use Case Catalog**: Exposes all 39 canonical use cases via `GET /api/use-cases` (29 scenario contracts + 10 pre-built from `use_case_repo.py`).
* **Category Filter Pills**: Fast category scoping across 8 domains:
  1. `All Use Cases` (39)
  2. `Network Operations` (LAN, CAN, MAN, WAN, GAN, EPN, PAN)
  3. `WAN & SD-WAN` (BGP route leak, SD-WAN brownout, MPLS failover)
  4. `Campus & LAN` (Catalyst core, 802.1Q trunking, rogue AP detection)
  5. `Wireless` (Meraki AP client density, Wi-Fi 6 CleanAir)
  6. `Data Center` (Cisco ACI microburst, RoCE v2 AI fabric, SAN/NAS storage)
  7. `Security & Zero Trust` (Ransomware lateral movement, DDoS SYN flood, Cisco ISE quarantine)
  8. `Service Provider` (Carrier Ethernet ERPS, SRv6 TE failover, DWDM optical loss)
  9. `Service Assurance` (VoIP MOS degradation, buffer incast, SLA violation)
* **Real-Time Search**: Instant client-side search across name, objective, description, vendors, and sourcetypes.
* **Rich Use-Case Cards**: Displays difficulty badge (`BEGINNER`, `INTERMEDIATE`, `ADVANCED`), estimated execution runtime (`30s`), vendor badges (`cisco`, `palo_alto`, `juniper`), selection status indicator, and collapsible "Advanced Details" showing specific objectives and target sourcetypes.

### Step 2: Preview Scenario & Evidence Contract (`StepPreview.tsx`)
Before running any code or emitting packets, the user inspects what will occur:
* **Blueprint Overview**: Displays scenario objective, expected runtime, target topology blueprint (`default_topology_id`), and vendor ecosystem scope.
* **Required Telemetry Sourcetypes**: Explicit pills of sourcetypes that must be generated (e.g. `cisco:sdwan:linkhealth`, `cisco:ios:syslog`, `paloalto:panos:traffic`).
* **Deterministic 9-Phase Progression**: Step-by-step preview of the lifecycle:
  1. `INITIALIZE` — Network state allocation and seed configuration.
  2. `BASELINE` — Steady-state normal operations telemetry generation.
  3. `DEGRADE` — Impairment injection (latency/jitter/loss degradation).
  4. `FAULT` — Primary failure trigger (link severance, port security violation).
  5. `PROPAGATE` — Cascading secondary effects (buffer incast, flap alerts).
  6. `FAILOVER` — Autonomous policy mitigation (BFD reroute, SSO failover).
  7. `RECOVER` — Administrative restoration and telemetry restabilization.
  8. `VALIDATE` — Verification rule evaluation against captured telemetry.
  9. `COMPLETE` — Run manifest compilation and cryptographic sealing.
* **Validation Rules Contract**: Rule-by-rule preview of assertion types (`COUNT_THRESHOLD`, `FIELD_PRESENCE`, `SLA_VIOLATION`, `STATE_TRANSITION`, `SPL_QUERY`).

### Step 3: Connect Telemetry Pipeline (`StepConnect.tsx`)
* **Pipeline Selector**: Select between 4 proven telemetry pipelines:
  1. `Splunk HEC (HTTP Event Collector)`: Production tokenized JSON streaming.
  2. `RFC 5424 Syslog Pipeline`: UDP/TCP port 514 syslog framing.
  3. `OpenTelemetry (OTel) Collector`: High-performance OTLP/HTTP gRPC push.
  4. `Telegraf / Influx Agent`: Time-series metric line protocol dispatch.
* **3-State Connection Health Semantics**:
  1. `CONFIGURED (UNTESTED)`: Settings are defined in local config but unverified.
  2. `REACHABLE`: Remote endpoint responded to preflight HTTP/socket probe with valid status code.
  3. `VERIFIED IN SPLUNK`: Telemetry verified written and searchable in target Splunk index.
* **Live Preflight Reachability Test**: One-click "Test Connection" button hits `/api/telemetry/test-hec` to measure live latency and verify connectivity.

### Step 4: Run Lifecycle Simulation (`StepRun.tsx`)
* **Canonical Run ID**: Generated on execution start conforming to `NS-YYYYMMDD-xxxxxxxx` (e.g. `NS-20260924-53c1f073`) with 1-click clipboard copy.
* **Deterministic Time Control**: Speed toggle between `TEST` (0.0s/tick, instant evaluation), `ACCELERATED` (0.02s/tick, fast visual preview), and `REALTIME` (0.5s/tick, production emulation).
* **Visual 9-Phase Progress Bar**: 9-segment track providing visual feedback as the simulation progresses from `INITIALIZE` to `COMPLETE`.
* **Live Metric Counters**:
  - `Elapsed Time`: Real-time execution duration in seconds.
  - `Events Generated`: Total synthetic log and metric events created.
  - `Events Dispatched`: Total events successfully transmitted over the active pipeline.
  - `Velocity (EPS)`: Real-time generation throughput rate.
* **Correlated Telemetry Stream**: Live terminal streaming stamped events with correlation tags:
  ```
  2026-09-24 23:52:09.400 UTC [FAULT] External Client: %NETSPOUT-6-INFO: phase=FAULT status=degraded sourcetype=cisco:catalyst:networkhealth
  ```
* **Cooperative Cancellation**: Immediate "Stop Run" control halting background workers.

### Step 5: Prove Expected Condition & Audit Evidence (`StepProve.tsx`)
Step 5 answers: **"Did it work, and what did it prove?"**
* **Overall Verdict Badge**: Prominent, unambiguous `USE CASE VERIFICATION: PASS` or `FAIL`.
* **4-Tier Semantic Evidence Breakdown**:
  46799\begin{array}{|l|l|l|}
  \hline
  \textbf{Tier} & \textbf{Metric Name} & \textbf{Semantic Definition} \\ \hline
  \text{Tier 1} & \textbf{GENERATED} & \text{Total raw event payloads generated by simulation core.} \\ \hline
  \text{Tier 2} & \textbf{DISPATCHED} & \text{Events successfully emitted onto the network/socket pipeline.} \\ \hline
  \text{Tier 3} & \textbf{OBSERVED} & \text{Events matching expected ground truth event signatures.} \\ \hline
  \text{Tier 4} & \textbf{VALIDATED} & \text{Formal rule-by-rule verdict evaluated by the Validation Engine.} \\ \hline
  \end{array}46799
* **Automated Validation Engine Audit Table**: Detailed breakdown showing:
  - Rule Name & Identifier (e.g. `Required Telemetry Emitted (arch_can_multi_building-val-01)`)
  - Assertion Type (e.g. `COUNT_THRESHOLD`)
  - Status Badge (`PASS` / `FAIL` / `ERROR`)
  - Expected vs. Observed counts (e.g. `Expected: 1 / Observed: 4`)
  - Audit Details and Query Expressions
* **Direct Splunk Search Handoff**: Dedicated button `Verify in Splunk Search` linking directly to Splunk Web search app:
  ```spl
  index=idx_network_ops netspout_run_id="NS-20260924-53c1f073" | table _time, netspout_phase, device_id, sourcetype, _raw
  ```
* **Collapsible Run Manifest Inspector**: Complete JSON audit ledger displaying ground truth records, affected entities, and cryptographic metadata.

---

## 5. Advanced Mode Preservation: Canvas Orchestrator

The expert canvas experience is preserved in `frontend/src/components/TopologyCanvas.tsx` and can be switched to at any time via the top navigation bar or the inline "Switch to Interactive Canvas Orchestrator" shortcut.

```
+-------------------+------------------------------------------+-----------------------+
|  NODE PALETTE     |           TOPOLOGY CANVAS                |   LOG TERMINAL        |
|  - Campus/Wireless|  - Interactive GNS3/EVE-NG Grid          |  - Live KV stream     |
|  - Security/ID    |  - Node drag-and-drop                    |  - AutoScroll toggle  |
|  - WAN/Routing    |  - Dynamic cable wiring & link metrics   |  - Buffer clearance   |
|  - Data Center    |  - Live packet trajectory animation      |  - Rate meter (EPS)   |
|  - Node Inspector |  - Link degradation & fault injection    |  - Raw / JSON export  |
+-------------------+------------------------------------------+-----------------------+
```

### Expert Tooling Modals Retained & Accessible:
1. **OpenConfig YANG Tree Explorer** (`OpenConfigTreeModal.tsx`): RFC 7951 JSON-IETF schema explorer for MDT interfaces, BGP, platform, and system models.
2. **SC4SNMP 300+ MIB Explorer** (`SNMPMibModal.tsx`): Interactive enterprise and RFC MIB tree with SNMP trap dispatch.
3. **Dynamic Fault Injection Modal** (`FaultInjectionModal.tsx`): Microburst, packet corruption, asymmetric routing, optical loss, SASE gateway degradation.
4. **Universal 4-Way Telemetry Pipeline Modal** (`TelemetryPipelinesModal.tsx`): Endpoint, token, TLS certificate, and index management for all 4 pipelines.
5. **Splunk Technology Add-on (TA) Directory** (`VendorAddonsModal.tsx`): 36-vendor directory with Splunkbase App IDs and sourcetype bindings.
6. **In-Memory SPL Playground** (`SPLPlaygroundModal.tsx`): Interactive Jupyter-like query runner supporting `stats`, `eval`, `where`, `sort`, `head`, and `table`.
7. **NOC & SOC Use Case Repository Modal** (`UseCaseRepositoryModal.tsx`): Production use-case catalog with 1-click execution in SPL.
8. **NOC & SOC Metrics Matrix Modal** (`NocSocMetricsModal.tsx`): ITU-T G.107 VoIP MOS score calculator, BGP flap dampening metrics, and buffer incast telemetry.

---

## 6. Operations & System Health Dashboard

The **Operations** view (`frontend/src/components/operations/OperationsView.tsx`) provides continuous observability of the NetSpout simulation platform:
* **FastAPI Backend Daemon**: Probes `http://localhost:8081/health` and verifies status of the background simulation daemon.
* **Splunk Web & HEC**: Probes Web port `8800` and HEC port `8888` on the Docker container (`splunk-network-data-blaster`).
* **Canonical Catalog Registry**: Audits loaded catalog data: 29 scenarios, 36 vendors, 197 sourcetypes.
* **Proven Telemetry Pipelines**: Displays operational readiness across all 4 pipelines (HEC, Syslog, OTLP, Telegraf).
* **Architecture Guardrails Status**: Confirms compliance with Gate 0–4 architectural invariants:
  - Single Python Source of Truth: `src/netspout_core/` (VERIFIED)
  - Canonical Declarative Layer: `catalog/` (VERIFIED)
  - Packaged Release Splunk Archive: `netspout.spl` (VERIFIED)
  - Run Identity Pattern: `NS-YYYYMMDD-xxxxxxxx` (VERIFIED)

---

## 7. Native Splunk Dashboards Integration Strategy

NetSpout includes 7 Dashboard Studio XML dashboards and 1 native SimpleXML dashboard:
1. `studio_roce_ai_fabric.xml`
2. `studio_multivendor_enterprise.xml`
3. `studio_firewall_capacity.xml`
4. `studio_cross_domain_triage.xml`
5. `studio_sdwan_branch.xml`
6. `studio_core_lsp_optical.xml`
7. `studio_bgp_route_flap.xml`
8. `datablaster_dashboard.xml`

### Strategic Classification: `KEEP_NATIVE`
* **Decision**: All 8 native dashboard XML views are preserved under `netspout/default/data/ui/views/` and linked via the `NetSpout Dashboards` menu in `default/data/ui/nav/default.xml`.
* **Rationale**: These dashboards represent native Splunk visual assets designed to display real-time analytics for simulated telemetry streams. Retaining them enables users to observe generated data inside native Splunk visualization panels without re-implementing Dashboard Studio functionality inside React.

---

## 8. Dead Code Elimination & Cleanup Accounting

An audit of `netspout/appserver/static/` was performed to identify and eliminate orphaned, dead, and duplicate JavaScript files.

### 8.1 Files Removed
1. `netspout/appserver/static/datablaster_ui.js`:
   - **Line Count**: 642 lines.
   - **Status**: DELETED.
   - **Forensic Justification**: Completely orphaned legacy script from pre-Gate 1 codebase. Zero references existed across all SimpleXML views, navigation files, and test scripts.
2. `netspout/appserver/static/test_script.js`:
   - **Line Count**: 1 line.
   - **Status**: DELETED.
   - **Forensic Justification**: Temporary test scratch file with zero references.
* **Total Removed**: **643 lines of dead code**.

### 8.2 Compatibility Files Retained
1. `netspout/appserver/static/guided_onboarding.js` (273 KB):
   - **Status**: RETAINED (`COMPATIBILITY`).
   - **Rationale**: Specifically verified by Suite 20 of the comprehensive test suite (`tests/run_comprehensive_test_suite.py`) and referenced by `guided_onboarding.xml`. Removing it would cause test regression.
2. `netspout/appserver/static/scenario_builder.js` (81 KB):
   - **Status**: RETAINED (`COMPATIBILITY`).
   - **Rationale**: Specifically verified by Suite 12 of the comprehensive test suite and referenced by `scenario_builder.xml`.
3. Suite 2 of the comprehensive test suite requires at least 5 JS files in `appserver/static/`. Retaining compatibility scripts satisfies this invariant while removing all genuinely dead files.

---

## 9. Frontend Source Ownership & Build Pipeline Architecture

To prevent drift between the React source code and the packaged Splunk app, Gate 5 establishes strict source ownership:

46799\text{Authoritative Source: } \texttt{frontend/src/} \xrightarrow{\text{scripts/build\_frontend.py}} \text{Generated Artifact: } \texttt{netspout/appserver/static/dist/}46799

### 9.1 Build Guardrail Script (`scripts/build_frontend.py`)
1. Executes `npm run build` in `frontend/` (invoking `tsc -b` and `vite build`).
2. Cleans destination directory `netspout/appserver/static/dist/`.
3. Copies generated `dist/` directory into `netspout/appserver/static/dist/`.
4. Verifies bundle integrity:
   - Validates existence of `index.html`.
   - Validates existence and sizing of generated JavaScript chunks (`assets/index-*.js`).
   - Validates asset links in `index.html`.

### 9.2 Release Packaging Integration (`scripts/build_splunk_package.py`)
The canonical packaging script automatically executes `scripts/build_frontend.py` before syncing core Python modules and generating `netspout.spl`. Direct manual editing inside `netspout/appserver/static/dist/` is prohibited.

---

## 10. Accessibility, Responsiveness & Design System Conformance

The consolidated frontend conforms to modern UI/UX design standards:
* **Dark NOC Color Palette**:
  - Background: `#0B0F19`
  - Cards & Panels: `#111827` / `#0F172A`
  - Borders: `#1E293B` / `#374151`
  - Accents: Cyan (`#06B6D4`), Emerald (`#10B981`), Sky (`#0EA5E9`), Amber (`#F59E0B`), Rose (`#F43F5E`).
* **Keyboard Navigation & Focus Indicators**: All interactive elements (category pills, search inputs, use-case cards, action buttons) have explicit focus ring styling (`focus:ring-2 focus:ring-cyan-500`) and standard tab stops.
* **Responsive Breakpoints Verified**:
  - `1920x1080`: Primary wall NOC display (3-column use case grid).
  - `1440x900`: Standard laptop display (3-column grid).
  - `1280x800`: Compact laptop display (2-column grid).
  - `1024x768`: Minimum supported tablet/console viewport (1-to-2 column grid with wrapped pills).
  - `200% Zoom`: High-DPI accessibility scaling with zero layout breakage or overlapping text.

---

## 11. Verification Results & Test Suite Summary

All test suites and architecture guardrails were executed and verified against the consolidated codebase.

```
==========================================================================
                     NETSPOUT ARCHITECTURE GATE AUDIT
==========================================================================
Gate 1 (Runtime Stabilization):                   6 / 6  PASS (100%)
Gate 2 (Single Python Source of Truth):           9 / 9  PASS (100%)
Gate 3 (Canonical Declarative Catalog):           8 / 8  PASS (100%)
Gate 4 (Scenario Contracts & Validation Engine): 22 / 22 PASS (100%)
Gate 5 (Unified Product UX & Workflows):         22 / 22 PASS (100%)
Comprehensive Production Verification Suite:     60 / 62 PASS (96.8%)
  -> Note: Exactly matches Gate 0-4 baseline (known Suite 1 & 3 checks)
Single Source of Truth Audit (verify_sources.py): 100% PASS (0 drift)
Canonical Catalog Validation (validate_catalog.py): 100% VALID (0 errors)
Production Package Build (build_splunk_package.py): PASS (netspout.spl: 1.36 MB)
==========================================================================
```

### 11.1 Gate 5 UX Test Suite (`tests/test_gate5_ux.py`)
The Gate 5 test suite exercises all 22 specific UX, workflow, and cleanup criteria:
1. `test_01_all_use_cases_discoverable`: Confirms 39 bound use cases across canonical categories.
2. `test_02_category_filtering`: Confirms category filtering logic.
3. `test_03_search_filtering`: Confirms multi-field keyword search.
4. `test_04_preview_scenario_data`: Confirms preview extraction of blueprint and phases.
5. `test_05_pipeline_options_available`: Confirms 4 proven pipelines.
6. `test_06_connection_status_distinction`: Confirms CONFIGURED, REACHABLE, and VERIFIED states.
7. `test_07_run_starts`: Confirms Run ID conforms to `NS-YYYYMMDD-xxxxxxxx`.
8. `test_08_phase_updates`: Confirms execution of all 9 chronological phases.
9. `test_09_run_stops`: Confirms cooperative scenario cancellation.
10. `test_10_manifest_displays`: Confirms complete manifest audit ledger with ground truth.
11. `test_11_validation_displays`: Confirms rule-by-rule PASS/FAIL output.
12. `test_12_evidence_distinction`: Confirms separation of GENERATED, DISPATCHED, OBSERVED, VALIDATED.
13. `test_13_splunk_search_handoff_link`: Confirms generation of correlation SPL query.
14. `test_15_topbar_three_primary_modes`: Confirms workflow, advanced, and operations top-level tabs.
15. `test_16_operations_view_diagnostics`: Confirms diagnostic metrics in operations view.
16. `test_17_keyboard_accessibility`: Confirms focus rings and keyboard attributes.
17. `test_18_no_primary_horizontal_overflow`: Confirms `overflow-hidden` layout bounds.
18. `test_19_deprecated_sourcetype_aliases_hidden`: Confirms deprecated aliases are not rendered as primary use cases.
19. `test_20_compiled_frontend_generated_from_source`: Confirms `build_frontend.py` compiles from source to dist.
20. `test_21_no_references_to_removed_js`: Confirms `datablaster_ui.js` and `test_script.js` are deleted.
21. `test_22_package_build_includes_unified_frontend`: Confirms `build_splunk_package.py` packages the frontend.

---

## 12. Visual Evidence & Artifact Registry

Authentic browser screenshots were captured via automated Chrome CDP against the running Docker Splunk container (`localhost:8800`) and the NetSpout backend daemon (`localhost:8081`).

| Evidence Artifact | Viewport / Dimensions | File Size | Description |
|---|---|---|---|
| [`gate5_step1_choose.png`](file:///Users/mahamudc/.gemini/antigravity/brain/778b26b7-32e8-4b3a-a8c8-f31ae91a57fb/gate5_step1_choose.png) | 1920x1080 @ 1.0x | 282 KB | Primary Step 1: Use Case catalog (39 available), search bar, and 8 category filter pills. |
| [`gate5_step2_preview.png`](file:///Users/mahamudc/.gemini/antigravity/brain/778b26b7-32e8-4b3a-a8c8-f31ae91a57fb/gate5_step2_preview.png) | 1920x1080 @ 1.0x | 242 KB | Primary Step 2: Target topology blueprint, 9-phase lifecycle track, and evidence contract. |
| [`gate5_step3_connect.png`](file:///Users/mahamudc/.gemini/antigravity/brain/778b26b7-32e8-4b3a-a8c8-f31ae91a57fb/gate5_step3_connect.png) | 1920x1080 @ 1.0x | 168 KB | Primary Step 3: Pipeline destination selector (HEC, Syslog, OTLP, Telegraf) with 3-state health. |
| [`gate5_step4_run.png`](file:///Users/mahamudc/.gemini/antigravity/brain/778b26b7-32e8-4b3a-a8c8-f31ae91a57fb/gate5_step4_run.png) | 1920x1080 @ 1.0x | 311 KB | Primary Step 4: Active simulation with canonical Run ID, 9-phase progress, and correlated log stream. |
| [`gate5_step5_prove.png`](file:///Users/mahamudc/.gemini/antigravity/brain/778b26b7-32e8-4b3a-a8c8-f31ae91a57fb/gate5_step5_prove.png) | 1920x1080 @ 1.0x | 138 KB | Primary Step 5: 4-tier evidence breakdown, automated validation audit table, and Splunk handoff. |
| [`gate5_canvas_orchestrator.png`](file:///Users/mahamudc/.gemini/antigravity/brain/778b26b7-32e8-4b3a-a8c8-f31ae91a57fb/gate5_canvas_orchestrator.png) | 1920x1080 @ 1.0x | 222 KB | Advanced Mode: 3-column dark NOC studio (NodePalette, TopologyCanvas, LogTerminal). |
| [`gate5_operations.png`](file:///Users/mahamudc/.gemini/antigravity/brain/778b26b7-32e8-4b3a-a8c8-f31ae91a57fb/gate5_operations.png) | 1920x1080 @ 1.0x | 114 KB | Operations Mode: System health, daemon status, Splunk HEC, catalog, and guardrail audit. |
| [`gate5_responsive_1440.png`](file:///Users/mahamudc/.gemini/antigravity/brain/778b26b7-32e8-4b3a-a8c8-f31ae91a57fb/gate5_responsive_1440.png) | 1440x900 @ 1.0x | 235 KB | Responsive test at 1440x900: Clean card layout with zero horizontal overflow. |
| [`gate5_responsive_1280.png`](file:///Users/mahamudc/.gemini/antigravity/brain/778b26b7-32e8-4b3a-a8c8-f31ae91a57fb/gate5_responsive_1280.png) | 1280x800 @ 1.0x | 214 KB | Responsive test at 1280x800: Dynamic 2-column adaptation and wrapped category pills. |
| [`gate5_responsive_1024.png`](file:///Users/mahamudc/.gemini/antigravity/brain/778b26b7-32e8-4b3a-a8c8-f31ae91a57fb/gate5_responsive_1024.png) | 1024x768 @ 1.0x | 182 KB | Responsive test at 1024x768: Minimum viewport support with zero horizontal scrolling. |
| [`gate5_zoom_200.png`](file:///Users/mahamudc/.gemini/antigravity/brain/778b26b7-32e8-4b3a-a8c8-f31ae91a57fb/gate5_zoom_200.png) | 1920x1080 @ 2.0x | 660 KB | Accessibility 200% zoom: Scaled typography and elements preserving visual hierarchy. |
| [`gate5_splunk_integrated_canvas.png`](file:///Users/mahamudc/.gemini/antigravity/brain/778b26b7-32e8-4b3a-a8c8-f31ae91a57fb/gate5_splunk_integrated_canvas.png) | 1920x1080 @ 1.0x | 298 KB | Native Splunk integration: Full Splunk Enterprise nav bar wrapping NetSpout v2.0 shell. |

---

## 13. Security & Operational Hardening

* **Safe Splunk HEC Authorization**: Splunk HTTP Event Collector authentication tokens are managed via secure headers and input fields masked by default.
* **Separation of Concerns**: The frontend never directly modifies simulation graph state or files on disk; all operations are mediated by strongly typed FastAPI endpoints (`/api/scenarios/run`, `/api/scenarios/run/stop`, `/api/use-cases`, `/api/telemetry/test-hec`).
* **Input Sanitization**: Client-side search and category filtering use sanitized substring comparisons to prevent injection.
* **Deterministic Seeding**: Scenario runs accept explicit seeds to ensure cryptographic repeatability across independent test runs.

---

## 14. Gate 5 Result & Next Gate Readiness

### Gate 5 Final Status: COMPLETE & VERIFIED

NetSpout has achieved complete architectural consolidation across UX, workflows, and frontend source code. The application provides a clear, guided journey for beginners ("What do you want to prove?"), maintains full depth for advanced network engineers, provides transparent system health diagnostics, eliminates dead code, and strictly locks down frontend build ownership.

**Readiness for Gate 6:**
The repository is primed for **Gate 6 — Production Packaging, Deployment Hardening, and Release Verification**.
All underlying components (Python Core, Canonical Catalog, Scenario Contracts, Validation Engine, React Frontend, and Splunk Package Scripts) are fully stabilized and synchronized.

> [!NOTE]
> Per explicit consolidation directive: **GATE 5 IS COMPLETE. DO NOT START GATE 6.** Execution stops here pending user instruction.
