# NetSpout Architecture Consolidation
## Gate 0 — Forensic Inventory, Runtime Trace, and Refactor Plan

**Repository:** [https://github.com/machowdhury/NetSpout](https://github.com/machowdhury/NetSpout)  
**Document:** `docs/architecture/NETSPOUT_GATE_0_FORENSIC_AUDIT.md`  
**Date:** September 22, 2026  
**Auditor:** Antigravity Forensic Engine  
**Gate Status:** COMPLETE (Read-Only Forensic Audit)

---

## 1. Executive Summary

NetSpout is a network telemetry and event simulation platform designed to prove Splunk network, security, observability, and service-assurance use cases without requiring physical hardware or complex lab connectivity.

A comprehensive forensic audit of the entire NetSpout repository reveals that the codebase has evolved through four distinct architectural generations without consolidating previous iterations:

1. **Generation 1 (Splunk Classic App — `TA-network-data-blaster` / `TA-datablaster`):** SimpleXML views (`datablaster_console.xml`), jQuery-based controllers, a custom persistent REST handler (`/services/datablaster/execute`), and an external native binary orchestration wrapper (`run_simulation.py`).
2. **Generation 2 (Static YAML & JSON Sample Ecosystem):** 213 pre-generated YAML sample files, 36 enterprise vendor definitions, and 37 YAML scenario definitions, cataloged across `samples_manifest.json` and `vendor_catalog.json`.
3. **Generation 3 (Standalone Simulation Engine):** A standalone Python 3.11+ FastAPI backend (`backend/app`) listening on port 8081 with a WebSocket log stream, paired with a React 18 / TypeScript SPA (`frontend/src`) developed using Vite.
4. **Generation 4 (Hybrid Splunk Ingest & Native React Canvas):** Embedding the compiled React bundle into Splunk Web via an iframe (`netspout_canvas.js` -> `dist/index.html`), introducing a second custom REST handler (`/services/netspout`), and adding live Splunkd REST API proxying for an honest SPL Playground (`spl_playground.js`).

### Critical Strategic Findings:
* **Severe Python Engine Duplication:** 11 core simulation files in `backend/app/*` and `netspout/bin/*` are **100% byte-for-byte identical duplicates**, while 4 files have diverged in critical features (node KPI metrics, WebSocket broadcasting, HEC port resolution).
* **Packaged Splunk App Isolation:** The packaged Splunk application (`netspout/`) **never imports or executes code from `backend/app/`**. It relies solely on `netspout/bin/*`. Conversely, `backend/run.py` only imports from `backend/app/*`.
* **Triple UI Redundancy:** NetSpout currently contains 3 concurrent UI architectures:
  1. Modern React/TypeScript Canvas (`frontend/src` built to `dist/index.html`).
  2. Monolithic SimpleXML + jQuery view controllers (`guided_onboarding.js` [273KB], `scenario_builder.js` [81KB], `spl_playground.js` [41KB]).
  3. Legacy unreferenced React application (`datablaster_react_app.js` [171KB]) and unreferenced legacy scripts (`datablaster_ui.js` [26KB], `datablaster_ui.css`).
* **Active Runtime Failure (P0 Defect):** `netspout/bin/datablaster_rest.py` (line 128) contains an unimported type annotation `List[str]`. Under Python 3.9 (the runtime bundled inside Splunk Enterprise 10.2), this triggers `NameError: name 'List' is not defined` during module initialization, causing all REST calls from `scenario_builder.js` and `guided_onboarding.js` to fail with HTTP 500 (`Unexpected token '<'`).
* **Source-of-Truth Drift:** Topology presets, vendor sourcetypes, and scenario definitions are maintained in 3 to 4 independent locations across TypeScript, Python, YAML, and JSON.

---

## 2. Repository Baseline

Before conducting forensic analysis, the baseline git working tree was recorded:

| Item | Value |
| :--- | :--- |
| **Branch** | `main` |
| **HEAD SHA** | `0c0a6f69839df3c33bd7c3dae761b2fe39bc55d5` |
| **Working Tree** | **CLEAN** (0 uncommitted changes, 0 untracked files) |
| **Modified Files** | NONE |
| **Untracked Files** | NONE |
| **Backend Entry Point** | `backend/run.py` (FastAPI `app.main:app` via Uvicorn on port 8081) |
| **Frontend Entry Point** | `frontend/src/main.tsx` (Vite SPA compiled to `frontend/dist` & `netspout/appserver/static/dist`) |
| **Splunk App Entry Point**| `netspout/default/data/ui/nav/default.xml` (Default view: `guided_onboarding`) |
| **Packaging / Build** | `npm --prefix frontend run build`, `Dockerfile.standalone`, `entrypoint-standalone.sh` |

---

## 3. Current Architecture

```
                                    +-----------------------------------------------+
                                    |                NetSpout Users                 |
                                    +-----------------------+-----------------------+
                                                            |
                             +------------------------------+-------------------------------+
                             |                                                              |
                             v (Port 8800)                                                  v (Port 8081)
               +-----------------------------+                                +-----------------------------+
               |     Splunk Web Interface    |                                |   Standalone Web Console    |
               +--------------+--------------+                                +--------------+--------------+
                              |                                                              |
     +------------------------+------------------------+                                     |
     |                        |                        |                                     |
     v (SimpleXML + JS)       v (RequireJS iframe)     v (Splunkd REST Proxy)                | (Vite React Build)
+--------------------+   +-----------------------+   +--------------------+                  |
| guided_onboarding  |   | netspout_canvas       |   | spl_playground     |                  |
| scenario_builder   |   | (dist/index.html)     |   | (/services/search) |                  |
| datablaster_console|   +-----------+-----------+   +---------+----------+                  |
+---------+----------+               |                         |                             |
          |                          +------------+------------+                             |
          v                                       |                                          |
+--------------------+                            v                                          |
| REST Handlers:     |                  +--------------------+                               |
| /datablaster/exec  |                  | Splunk Enterprise  |                               |
| /services/netspout |                  | Indexing Pipeline  |                               |
+---------+----------+                  | (idx_network_ops,  |                               |
          |                             |  cisco_mdt_metrics)|                               |
          v                             +---------^----------+                               |
+--------------------+                            |                                          |
| netspout/bin/      |                            | HEC Push                                 |
| - datablaster_rest |----------------------------+                                          |
| - run_simulation   |                                                                       |
| - models.py        |                                                                       |
+--------------------+                                                                       |
                                                                                             v
                                                                              +-----------------------------+
                                                                              | backend/run.py (Port 8081)  |
                                                                              +--------------+--------------+
                                                                                             |
                                                                                             v
                                                                              +-----------------------------+
                                                                              | backend/app/main.py         |
                                                                              | - ScenarioRunner            |
                                                                              | - TelemetryDispatcher       |
                                                                              | - WebSocket (/ws/logs)      |
                                                                              +-----------------------------+
```

---

## 4. Runtime Execution Trace

### 4.1 Standalone / Backend Execution
When running outside of Splunk (or via port 8081 in the companion container):
```
User / Web Browser
  → GET http://localhost:8081/ (Serves frontend/dist/index.html)
  → WebSocket Connection: ws://localhost:8081/ws/logs
  → REST API: POST http://localhost:8081/api/scenarios/run
      ↳ Handled by backend/app/main.py:run_scenario()
      ↳ Instantiates/executes backend/app/scenario_runner.py:ScenarioRunner
      ↳ Evaluates network graph via backend/app/graph_engine.py:TopologyGraph
      ↳ Generates synthetic payloads via:
          - backend/app/log_engine.py (Syslog/CEF/KV)
          - backend/app/gnmi_engine.py (gNMI/OpenConfig YANG)
          - backend/app/snmp_engine.py (SNMP v2c traps/metrics)
      ↳ Dispatches payloads via backend/app/telemetry_dispatcher.py:TelemetryDispatcher
          - HTTP POST -> Splunk HEC (https://127.0.0.1:8888/services/collector)
          - Socket sendto -> Syslog UDP/TCP (127.0.0.1:514)
          - HTTP POST -> OpenTelemetry Collector (http://localhost:4318/v1/metrics)
      ↳ Streams log entries back to UI over WebSocket broadcast
```
*Note on Client-Side Fallback:* If `ws://localhost:8081/ws/logs` connection fails, `frontend/src/App.tsx` (lines 384–440) initiates an **in-browser JavaScript simulation loop**, generating logs in the client and calling `fetch(hec_url)` directly from the user's browser.

### 4.2 Splunk Enterprise App Execution
When running within Splunk Web (`http://localhost:8800/en-US/app/netspout/`):
```
Splunk Navigation (netspout/default/data/ui/nav/default.xml)
  │
  ├── View 1: guided_onboarding.xml
  │     ↳ Loads netspout/appserver/static/guided_onboarding.js
  │     ↳ User clicks "Blast Events to Splunk"
  │     ↳ AJAX POST /en-US/splunkd/__raw/services/datablaster/execute
  │     ↳ Handled by netspout/bin/datablaster_rest.py:DataBlasterRestHandler
  │     ↳ Emits events via urllib to Splunk HEC (https://127.0.0.1:8888/services/collector)
  │
  ├── View 2: scenario_builder.xml
  │     ↳ Loads netspout/appserver/static/scenario_builder.js
  │     ↳ User clicks "Emit 1 OpenConfig Metric Probe" or "Stream Continuous MDT"
  │     ↳ AJAX POST /en-US/splunkd/__raw/services/datablaster/execute
  │     ↳ Handled by netspout/bin/datablaster_rest.py:DataBlasterRestHandler
  │     ↳ CRASHES under Python 3.9 due to NameError: name 'List' is not defined (Line 128)
  │     ↳ Returns HTTP 500 XML/HTML -> JS throws "Unexpected token '<'"
  │
  ├── View 3: netspout_canvas.xml
  │     ↳ Loads netspout/appserver/static/netspout_canvas.js
  │     ↳ Creates iframe pointing to /en-US/static/app/netspout/dist/index.html
  │     ↳ React App connects to companion backend ws://localhost:8081/ws/logs
  │     ↳ If companion backend is offline, falls back to in-browser JavaScript generator
  │
  ├── View 4: spl_playground.xml
  │     ↳ Loads netspout/appserver/static/spl_playground.js
  │     ↳ User clicks "Execute Search (Splunk REST API)"
  │     ↳ AJAX POST /en-US/splunkd/__raw/services/search/jobs
  │     ↳ Polls search status and retrieves real job results from Splunk Core
  │
  └── View 5: datablaster_console.xml
        ↳ Loads netspout/appserver/static/datablaster_console.js
        ↳ User clicks "Launch Scenario"
        ↳ AJAX POST /en-US/splunkd/__raw/services/datablaster/execute { action: 'start' }
        ↳ Spawns netspout/bin/run_simulation.py as background subprocess
```

**Definitive Architecture Proof:**
* The Splunk app runtime **never** imports or invokes `backend/app/*`.
* `backend/app/*` is **only** executed when running standalone or through the companion container entrypoint (`entrypoint-standalone.sh` calling `/opt/netspout-backend/run.py`).

---

## 5. Duplicate Code Analysis: `backend/app/*` vs `netspout/bin/*`

A cryptographic SHA-256 comparison and semantic analysis between `backend/app/` and `netspout/bin/` yields the following classification:

| Backend File | Splunk File | Classification | Runtime Used By | Differences & Divergence Details | Maintenance Risk |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `__init__.py` | `__init__.py` | **DIVERGED** | Both | Splunk version injects virtual `sys.modules['app']` package alias; backend version is minimal. | Medium |
| `cisco_sample_provider.py` | `cisco_sample_provider.py` | **EXACT_DUPLICATE** | Both | Byte-for-byte identical (SHA: `cdb960eb...`). Generates `cisco_catalog.json`. | High (Sync drift) |
| `fault_injection_engine.py`| `fault_injection_engine.py`| **EXACT_DUPLICATE** | Both | Byte-for-byte identical (SHA: `872391e8...`). Graph cascade failure solver. | High (Sync drift) |
| `gnmi_engine.py` | `gnmi_engine.py` | **EXACT_DUPLICATE** | Both | Byte-for-byte identical (SHA: `3454d9d9...`). RFC 7950 YANG tree engine. | High (Sync drift) |
| `graph_engine.py` | `graph_engine.py` | **EXACT_DUPLICATE** | Both | Byte-for-byte identical (SHA: `0e8a206d...`). Network graph & Dijkstra pathing. | High (Sync drift) |
| `log_engine.py` | `log_engine.py` | **EXACT_DUPLICATE** | Both | Byte-for-byte identical (SHA: `5a695183...`). Token replacement & log generation. | High (Sync drift) |
| `main.py` | `main.py` | **DIVERGED** | Both | `backend/app/main.py` broadcasts WebSocket state to all connected clients; `netspout/bin/main.py` only sends to the single caller. | High (Inconsistent state) |
| `models.py` | `models.py` | **DIVERGED** | Both | `backend/app/models.py` contains 6 additional `NodeType`s, 11 `arch_*` `ScenarioType`s, and 16 Node KPI telemetry fields that `netspout/bin/models.py` completely lacks! | Critical (Type mismatch) |
| `noc_soc_metrics.py` | `noc_soc_metrics.py` | **EXACT_DUPLICATE** | Both | Byte-for-byte identical (SHA: `a7e38c53...`). Metric calculation formulas. | High (Sync drift) |
| `scenario_runner.py` | `scenario_runner.py` | **EXACT_DUPLICATE** | Both | Byte-for-byte identical (SHA: `14312713...`). Multi-hop scenario event synthesizer. | High (Sync drift) |
| `snmp_engine.py` | `snmp_engine.py` | **EXACT_DUPLICATE** | Both | Byte-for-byte identical (SHA: `103fa0ad...`). 333 SC4SNMP MIB definitions. | High (Sync drift) |
| `spl_engine.py` | `spl_engine.py` | **EXACT_DUPLICATE** | Both | Byte-for-byte identical (SHA: `ba341dbf...`). Legacy in-memory SPL parser. | Medium (Dead logic) |
| `telemetry_dispatcher.py` | `telemetry_dispatcher.py` | **DIVERGED** | Both | `backend/app/telemetry_dispatcher.py` has candidate URL fallback logic (`:8888` <-> `:8088`, `127.0.0.1` <-> `localhost`); `netspout/bin/` lacks it. | High (Connection failure) |
| `use_case_repo.py` | `use_case_repo.py` | **EXACT_DUPLICATE** | Both | Byte-for-byte identical (SHA: `875ed3c6...`). 10 NOC/SOC use case tests. | High (Sync drift) |
| `vendor_catalog.py` | `vendor_catalog.py` | **EXACT_DUPLICATE** | Both | Byte-for-byte identical (SHA: `f6bf545d...`). 36 enterprise vendor definitions. | High (Sync drift) |
| — | `datablaster_executor.py` | **UNIQUE_SPLUNK** | Splunk | Process manager for legacy `data-blaster` binary execution. | Medium |
| — | `datablaster_rest.py` | **UNIQUE_SPLUNK** | Splunk | Custom REST handler for `/services/datablaster/execute`. Contains fatal Python 3.9 bug. | Critical (Runtime defect) |
| — | `netspout_rest_handler.py`| **UNIQUE_SPLUNK** | Splunk | Custom REST handler for `/services/netspout`. KV Store persistence. | Medium |
| — | `netspout_streamer.py` | **UNIQUE_SPLUNK** | Splunk | Splunk Modular Input for streaming events via stdout XML. | Low |
| — | `run_simulation.py` | **UNIQUE_SPLUNK** | Splunk | CLI orchestration script. Contains hardcoded macOS paths. | High (Portability break) |

---

## 6. UI Forensics

An exhaustive audit of all user interface files across `frontend/src`, `netspout/appserver/static`, and `netspout/default/data/ui/views` establishes the following:

| UI File | Referenced By | Runtime Status | Equivalent React / Modern UI | Recommendation |
| :--- | :--- | :--- | :--- | :--- |
| `frontend/src/*` (TypeScript/React) | Vite Build Engine | **CURRENT** | Source of truth for Canvas & Orchestrator | **KEEP & CONSOLIDATE** |
| `netspout/appserver/static/dist/*` | `netspout_canvas.js` (via iframe) | **CURRENT** | Compiled production artifact of `frontend/src` | **GENERATED** (Keep build target) |
| `netspout/appserver/static/netspout_canvas.js` | `netspout_canvas.xml` | **CURRENT** | Minimal iframe loader bridge | **KEEP** |
| `netspout/appserver/static/guided_onboarding.js` | `guided_onboarding.xml` | **CURRENT** | None (Custom DOM wizard with 273KB logic) | **MIGRATE TO REACT** |
| `netspout/appserver/static/scenario_builder.js` | `scenario_builder.xml` | **CURRENT** | Partially exists in React (`TopologyCanvas`) | **MIGRATE TO REACT** |
| `netspout/appserver/static/spl_playground.js` | `spl_playground.xml` | **CURRENT** | Exists in React (`SPLPlaygroundModal.tsx`) | **CONSOLIDATE TO REACT** |
| `netspout/appserver/static/configuration.js` | `configuration.xml` | **CURRENT** | Exists in React (`SyslogConfigModal.tsx`) | **CONSOLIDATE TO REACT** |
| `netspout/appserver/static/datablaster_console.js`| `datablaster_console.xml`| **LEGACY_BUT_ACTIVE** | Overlapped by Guided Onboarding / Canvas | **CANDIDATE_FOR_REMOVAL** |
| `netspout/appserver/static/datablaster_react_app.js`| `static/index.html` only | **PROBABLY_UNUSED** | Superseded by `frontend/src/App.tsx` | **CANDIDATE_FOR_REMOVAL** |
| `netspout/appserver/static/datablaster_ui.js` | **NONE** (0 references) | **PROBABLY_UNUSED** | Completely unreferenced legacy script | **SAFE_CANDIDATE_FOR_REMOVAL** |
| `netspout/appserver/static/datablaster_ui.css` | **NONE** (0 references) | **PROBABLY_UNUSED** | Completely unreferenced stylesheet | **SAFE_CANDIDATE_FOR_REMOVAL** |
| `netspout/appserver/static/test_script.js` | **NONE** (0 references) | **PROBABLY_UNUSED** | 72-byte empty dummy test script | **SAFE_CANDIDATE_FOR_REMOVAL** |
| `netspout/appserver/static/index.html` | **NONE** (Direct URL only) | **PROBABLY_UNUSED** | Legacy container for `datablaster_react_app` | **CANDIDATE_FOR_REMOVAL** |
| `netspout/appserver/static/vendor/*` | `static/index.html` only | **PROBABLY_UNUSED** | React 18 & Tailwind UMD scripts | **CANDIDATE_FOR_REMOVAL** |
| `netspout/default/data/ui/views/*.xml` (15 views) | `default.xml` | **CURRENT** | SimpleXML dashboard wrappers | **KEEP (Core) / PRUNE (Redundant)** |

---

## 7. Source-of-Truth Analysis

| Domain | Sources Found in Codebase | Current Authority | Duplicated? | Drift Risk | Proposed Authority |
| :--- | :--- | :--- | :---: | :--- | :--- |
| **Enterprise Vendors** | 1. `backend/app/vendor_catalog.py`<br>2. `netspout/bin/vendor_catalog.py`<br>3. `vendor_catalog.json` | Python list (`VENDOR_CATALOG`) | **YES** (3x) | High | Single canonical `vendor_catalog.json` loaded dynamically |
| **Sourcetypes** | 1. `vendor_catalog.py`<br>2. `cisco_catalog.json`<br>3. `samples_manifest.json`<br>4. `requested_sourcetypes.csv` | `vendor_catalog.py` (238 sourcetypes) | **YES** (4x) | Critical | Single canonical schema in `netspout/catalog/` |
| **Topologies** | 1. `frontend/src/presets/defaultTopologies.ts`<br>2. `backend/app/main.py` (Preset functions)<br>3. `scenarios/*.yml` | TypeScript `defaultTopologies.ts` | **YES** (3x) | High | JSON Schema format in `netspout/topologies/` |
| **Scenarios** | 1. `scenarios/*.yml` (37 files)<br>2. `scenarios_manifest.json` (19 entries)<br>3. `models.py` (`ScenarioType`)<br>4. `use_case_repo.py` (10 tests) | Unclear (Split between YAML & TS) | **YES** (4x) | Critical | Unified `scenarios/` directory with 100% manifest alignment |
| **Sample Datasets** | 1. `netspout/appserver/static/samples/` (213 dirs)<br>2. `netspout/samples/*.sample` (34 files)<br>3. `eventgen.conf` | `samples/` directory | **YES** (2x) | High | Consolidated `samples/` directory |
| **SNMP MIB Definitions**| 1. `snmp_engine.py` (`RAW_MIB_DEFINITIONS`)<br>2. `SNMPMibModal.tsx` | Python `snmp_engine.py` (333 MIBs) | **YES** (2x) | Medium | External JSON/YAML MIB definition directory |
| **gNMI/OpenConfig Models**| 1. `gnmi_engine.py`<br>2. `OpenConfigTreeModal.tsx`<br>3. `scenario_builder.js` | Python `gnmi_engine.py` (24 XPaths) | **YES** (3x) | High | Schema-driven OpenConfig registry |
| **Splunk Indexes** | 1. `inputs.conf` / `indexes.conf`<br>2. `datablaster_rest.py`<br>3. `scenario_builder.js`<br>4. `App.tsx` | `indexes.conf` (`idx_network_ops`, `cisco_mdt_metrics`, etc.) | **YES** (4x) | Medium | Centralized configuration contract |

---

## 8. Sourcetype & Identifier Integrity Findings

### 8.1 The `cisco-sdwan-sytem-logs` vs `cisco-sdwan-system-logs` Investigation
Forensic audit confirms that **both identifiers exist concurrently** in the repository:

1. **`cisco-sdwan-sytem-logs` (Typo Variant):**
   * Registered in `netspout/appserver/static/samples_manifest.json` (lines 1748–1754):
     ```json
     "id": "cisco-sdwan-sytem-logs",
     "sampleFile": "cisco-sdwan-sytem-logs.yml"
     ```
   * Sample YAML file exists at: `netspout/appserver/static/samples/cisco-sdwan-sytem-logs/cisco-sdwan-sytem-logs.yml`.
   * Configured in `netspout/default/eventgen.conf` (line 1):
     ```ini
     [cisco_sdwan_sytem_logs.sample]
     sourcetype = cisco:sdwan:sytem:logs
     ```
   * Raw payload inspection: Contains **Meraki MX firewall flow logs** (`MX_67_Home ip_flow_end`).
2. **`cisco-sdwan-system-logs` (Standard Variant):**
   * Registered in `netspout/appserver/static/samples_manifest.json` (lines 1730–1736):
     ```json
     "id": "cisco-sdwan-system-logs",
     "sampleFile": "cisco-sdwan-system-logs.yml"
     ```
   * Sample YAML file exists at: `netspout/appserver/static/samples/cisco-sdwan-system-logs/cisco-sdwan-system-logs.yml`.
   * Configured in `netspout/default/eventgen.conf` (line 13):
     ```ini
     [cisco_sdwan_system_logs.sample]
     sourcetype = cisco:sdwan:system:logs
     ```
   * Raw payload inspection: Contains genuine **Cisco SD-WAN `%SDWAN-5-FPMD` flow records**.

**Recommended Canonical Strategy:**
* **Canonical Identifier:** `cisco:sdwan:system:logs` (standard spelling).
* **Backward-Compatible Strategy:** Retain `cisco:sdwan:sytem:logs` in Splunk `props.conf` as a `rename = cisco:sdwan:system:logs` or sourcetype alias, ensuring legacy queries never break.

### 8.2 Other Identifier Anomalies
* **Duplicate Sample IDs in `samples_manifest.json`:**
  - `nutanixpc-syslog` is defined twice (lines 1150 and 1168).
  - `nutanixpc-vms` is defined twice (lines 1186 and 1204).
* **10 Orphan Sample Directories on Disk (Unregistered in Manifest):**
  - `cisco-duo-push`
  - `cisco-duo-remote-vpn`
  - `cisco-duo-sso`
  - `cisco-duo-zerotrust`
  - `cisco-ise-byod`
  - `cisco-ise-guest`
  - `cisco-ise-nac-8021x`
  - `cisco-ise-tacacs`
  - `cisco-ise-trustsec`
  - `cisco-mdt-streaming-metrics`
* **18 Unmanifested Scenario YAML Files on Disk:**
  - 11 architecture scenarios (`scenario_arch_can_multi_building.yml`, `scenario_arch_epn_isolated_intranet.yml`, etc.) exist in `scenarios/` but are omitted from `scenarios_manifest.json`.

---

## 9. Scenario Engine Inventory & Analysis

The repository contains **37 scenario files** in `netspout/appserver/static/scenarios/`, which fall into 4 distinct groups:

| Scenario Group | Files Discovered | Manifested? | Telemetry Types | Deterministic Assertions? | Classification |
| :--- | :---: | :---: | :--- | :---: | :--- |
| **ACME Multi-Tier Enterprise** | 7 files (`scenario_acme_*.yml`) | **YES** (7/7) | Syslog, NetFlow, ACI Health, MDT | **YES** (Count & fields) | **COMPLETE** |
| **Domain-Specific Architectural** | 11 files (`scenario_arch_*.yml`) | **NO** (0/11) | Syslog, gNMI, IoT, Storage SAN/NAS | Partial | **PARTIAL** |
| **Unified Enterprise Modes** | 7 files (`scenario_pure_cisco_*.yml`, etc.) | **NO** (0/7) | Multi-hop Syslog, 802.1X, gNMI | Partial | **PARTIAL** |
| **Legacy Proof-of-Concept** | 12 files (`scenario_campus.yml`, `scenario_mix.yml`, etc.) | **YES** (12/12)| Basic Syslog / Static samples | No (Demo replay only) | **DEMO_ONLY** |

---

## 10. Telemetry Pipeline Analysis

NetSpout implements 5 distinct telemetry output pipelines in `backend/app/telemetry_dispatcher.py` and `netspout/bin/telemetry_dispatcher.py`:

```
+------------------+     +-------------------+     +-------------------------+     +------------------------+
| Telemetry Source | --> | Protocol Formatter| --> | Dispatcher Engine       | --> | Destination Transport  |
+------------------+     +-------------------+     +-------------------------+     +------------------------+
| LogEngine        |     | RFC 5424 / 3164   |     | emit_syslog()           |     | UDP / TCP Socket (514) |
| gNMIEngine       |     | JSON-IETF / MDT   |     | emit_hec()              |     | Splunk HEC HTTPS (8088)|
| SNMPEngine       |     | SNMPv2 Trap / PDU |     | emit_snmp_trap()        |     | UDP Socket (162)       |
| MetricsEngine    |     | OTLP Metric JSON  |     | emit_otel()             |     | HTTP POST (/v1/metrics)|
| MetricsEngine    |     | Influx Line Proto |     | emit_telegraf()         |     | HTTP POST (:8186/write)|
+------------------+     +-------------------+     +-------------------------+     +------------------------+
```

### Pipeline Weaknesses:
1. **Tight Coupling:** The payload formatting (e.g., converting a metric to Splunk HEC JSON) is mixed directly inside the transport dispatch functions.
2. **Missing Retry & Backoff:** `emit_hec()` and `emit_otel()` make single-shot requests with short timeouts (2.0s). If an indexer pipeline stalls, packets are dropped immediately without a buffer queue.
3. **Dispatcher Divergence:** `backend/app/telemetry_dispatcher.py` implements intelligent port substitution (`:8888` <-> `:8088`), but `netspout/bin/telemetry_dispatcher.py` lacks this logic, causing connections to fail in container-to-host setups.

---

## 11. Test Quality Analysis

The repository contains a single test script: `tests/run_comprehensive_test_suite.py` (619 lines).

### Forensic Test Classification:
* **Suite 1 (SimpleXML & Navigation):** `STATIC` & `IMPLEMENTATION_PRESENCE`. Validates that XML files parse and navigation contains specific exact label strings.
* **Suite 2 (JavaScript Syntax):** `STATIC`. Executes `node -c` on `.js` files.
* **Suite 3 (Python Syntax & Execution):** `STATIC` / `SMOKE`. Tests `py_compile` and imports modules in a clean virtual environment.
* **Suite 4 (Catalog & Manifest Coverage):** `CONTRACT`. Checks that sourcetypes in `requested_sourcetypes.csv` match `vendor_catalog.py`.
* **Suite 5 (Packaging & Archive):** `PACKAGING`. Verifies `netspout.spl` tarball contents.

### Critical Testing Deficits:
* **ZERO Behavioral Tests:** There is not a single automated test that verifies:
  `Trigger Scenario -> Generate Telemetry -> Push HEC -> Ingest -> Search SPL -> Validate Result`.
* **Fragile String Matching:** Suite 1 fails if a human changes a UI menu label, even if all functionality remains 100% operational.

---

## 12. Dead Code and Redundancy Candidates

| File Path | Classification | Evidence / Justification |
| :--- | :--- | :--- |
| `netspout/appserver/static/datablaster_ui.js` | **SAFE_CANDIDATE_FOR_REMOVAL** | 0 references in any view, JS script, or manifest. |
| `netspout/appserver/static/datablaster_ui.css` | **SAFE_CANDIDATE_FOR_REMOVAL** | 0 references in any view or stylesheet link. |
| `netspout/appserver/static/test_script.js` | **SAFE_CANDIDATE_FOR_REMOVAL** | 72-byte dummy file (`console.log("Test script loaded");`). |
| `netspout/appserver/static/datablaster_react_app.js`| **PROBABLY_UNUSED** | 171KB script only referenced in standalone `static/index.html`. |
| `netspout/appserver/static/index.html` | **PROBABLY_UNUSED** | Legacy standalone runner for `datablaster_react_app.js`. |
| `netspout/appserver/static/vendor/*` | **PROBABLY_UNUSED** | Standalone React 18 & Tailwind UMD scripts only loaded by `static/index.html`. |
| `backend/app/spl_engine.py` | **PROBABLY_UNUSED** | In-memory SPL engine replaced by live Splunk REST searches. |
| `netspout/bin/datablaster_executor.py` | **PROBABLY_UNUSED** | Redundant process manager duplicated by `datablaster_rest.py`. |
| `netspout/bin/*.py` (11 duplicate files) | **REDUNDANT (DUPLICATE)** | Exact byte-for-byte duplicates of `backend/app/*.py`. |

---

## 13. Top 15 Complexity Hotspots

1. **`netspout/bin/datablaster_rest.py` (60KB, 1,471 lines):**
   * Combines REST routing, subprocess management, direct HEC HTTP dispatch, PID file tracking, and payload formatting in a single monolithic handler. Contains the fatal Python 3.9 `List` syntax bug.
2. **`netspout/appserver/static/guided_onboarding.js` (273KB, 7,200+ lines):**
   * Massive monolithic jQuery script with hardcoded HTML strings, inline JSON sample payloads, manual DOM event bindings, and multi-step state machines.
3. **`backend/app/snmp_engine.py` / `netspout/bin/snmp_engine.py` (92KB, 2,100+ lines):**
   * 333 SC4SNMP MIBs hardcoded as raw Python dictionaries inside the source code rather than external data files.
4. **`netspout/appserver/static/scenario_builder.js` (81KB, 1,300+ lines):**
   * Directly implements SVG vector rendering, dynamic Dijkstra path calculations, timer intervals, and REST event handling in one unstructured file.
5. **`frontend/src/presets/defaultTopologies.ts` (60KB, 1,500+ lines):**
   * Massive hardcoded TypeScript dictionary defining coordinates, interfaces, and metadata for 17 network topologies.
6. **`backend/app/vendor_catalog.py` / `netspout/bin/vendor_catalog.py` (51KB, 1,437 lines):**
   * Hardcoded 36-vendor Python array duplicating data found in `vendor_catalog.json`.
7. **`frontend/src/App.tsx` (31KB, 740 lines):**
   * Central state container handling 20+ modal states, dual-mode switches, WebSocket lifecycle, and in-browser fallback simulation.
8. **`backend/app/main.py` (39KB, 858 lines):**
   * FastAPI routing mixed with global simulation state variables, WebSocket connection management, and procedural topology generators.
9. **`netspout/bin/run_simulation.py` (27KB, 628 lines):**
   * Contains hardcoded local macOS file paths (`/Users/mahamudc/...`) and complex subprocess wrappers.
10. **`netspout/appserver/static/spl_playground.js` (41KB, 950 lines):**
    * Manages query libraries, asynchronous Splunk REST job creation, polling loops, and raw DOM table rendering.
11. **`backend/app/telemetry_dispatcher.py` (29KB, 679 lines):**
    * Bundles 5 disparate network transports (HEC, OTel, Telegraf, Syslog UDP, Syslog TCP) in a single class without interface abstractions.
12. **`netspout/bin/fault_injection_engine.py` (36KB, 800+ lines):**
    * Multi-layer fault graph cascade solver with complex state tracking across physical, protocol, and application layers.
13. **`netspout/bin/log_engine.py` (39KB, 900+ lines):**
    * Multi-vendor regex template engine for syslog synthesis with hundreds of branching statements.
14. **`netspout/appserver/static/samples_manifest.json` (206KB, 5,500+ lines):**
    * Monolithic manifest tracking 213 samples, containing duplicate IDs and orphan entries.
15. **`netspout/appserver/static/dashboard_queries.json` (382KB, 8,000+ lines):**
    * Massive static query repository used by studio dashboards.

---

## 14. Product Scope Assessment

| Feature Area | Classification | Strategic Evaluation |
| :--- | :--- | :--- |
| **Guided Telemetry Onboarding Wizard** | **CORE** | Directly fulfills primary mission: allows instant log blasting of realistic multi-vendor data into Splunk. |
| **Interactive Topology Canvas** | **CORE** | Visual drag-and-drop network topology with live HEC streaming and fault injection. |
| **Honest SPL Playground** | **CORE** | High value for network engineers learning SPL against live ingested events. |
| **Scenario Builder & Path Emitter** | **CORE** | Proves multi-hop correlated log propagation (Client -> Switch -> FW -> WAN). |
| **Multi-Protocol Dispatcher (HEC, Syslog)** | **CORE** | Essential transport protocols for network telemetry ingestion. |
| **OpenConfig MDT / gNMI Streaming** | **ADVANCED** | Valuable for modern network observability, but must not complicate basic onboarding. |
| **SC4SNMP 300+ MIB Catalog** | **ADVANCED** | Excellent for enterprise network assurance; should be modularized into external catalogs. |
| **OTel / Telegraf Dispatchers** | **SUPPORTING** | Useful for hybrid architectures; secondary to native Splunk HEC. |
| **Legacy `data-blaster` Subprocess Wrapper**| **OVERLAPPING** | Redundant legacy mechanism superseded by native Python and REST dispatchers. |
| **In-Memory SPL Execution Engine** | **QUESTIONABLE**| Fake simulation engine; fully superseded by live Splunkd REST API execution. |

---

## 15. NetSpout Functionality Preservation Matrix

The following table documents capabilities that are currently functional and **must be protected from regression** during subsequent refactoring gates:

| Capability | Current Implementation | Must Preserve | Validation Method |
| :--- | :--- | :---: | :--- |
| **Splunk HEC Event Dispatch** | `telemetry_dispatcher.py:emit_hec` | **YES** | HTTP 200 from Splunk HEC, count verified in `index=idx_network_ops`. |
| **Splunk HEC Metric Dispatch** | `telemetry_dispatcher.py` (`cisco_mdt_metrics`) | **YES** | Metric data points verified via `| mstats` query. |
| **Syslog Socket Ingestion** | `telemetry_dispatcher.py:emit_syslog` | **YES** | Socket listener receives RFC 5424 / 3164 framed packets. |
| **Live Canvas Orchestrator** | `frontend/src/App.tsx` (React 18) | **YES** | Visual topology renders, drag-and-drop works, live HEC status displays. |
| **Live Telemetry Pause / Freeze** | `App.tsx` / `LogTerminal.tsx` | **YES** | Auto-scroll stops, banner displays, 0 EPS reflected. |
| **Multi-Hop Path Emitter** | `scenario_builder.js` / `scenario_runner.py` | **YES** | Synchronized logs emit across all devices in selected path. |
| **Guided Onboarding Wizard** | `guided_onboarding.js` (Batch + Scenario) | **YES** | 10 batch presets and 18 architectural scenarios trigger HEC events. |
| **Live SPL Playground Searches** | `spl_playground.js` -> Splunkd REST | **YES** | Executes query against `/services/search/jobs` and displays real rows. |
| **Fault Injection Cascades** | `fault_injection_engine.py` | **YES** | Cutting link triggers interface DOWN and drops BGP neighbors. |
| **OpenConfig MDT Models** | `gnmi_engine.py` (24 XPaths) | **YES** | Structured YANG JSON emitted to `cisco_mdt_metrics`. |

---

## 16. Defect Register

| Defect ID | Severity | File & Component | Observed Evidence | Expected Behavior | Actual Behavior | Likely Root Cause | Recommended Future Fix |
| :--- | :---: | :--- | :--- | :--- | :--- | :--- | :--- |
| **DEF-01** | **P0** | `netspout/bin/datablaster_rest.py`<br>`resolve_hec_urls()` (line 128) | `NameError: name 'List' is not defined` when loaded in Splunk. | REST endpoint initializes cleanly and handles POST requests. | Python crashes on startup; all REST calls return HTTP 500 HTML/XML (`Unexpected token '<'`). | Missing `List` in `from typing import ...` on line 25; Python 3.9 evaluates annotations at import time. | Import `List` from `typing` or add `from __future__ import annotations`. |
| **DEF-02** | **P1** | `netspout/bin/models.py`<br>`NodeType` & `Node` | Missing `storage_san`, `iot_sensor`, `wlc_controller`, and KPI fields. | Models should support all 11 network architectures and device health metrics. | Type validation errors if extended topologies are passed to Splunk Python runtime. | `netspout/bin/models.py` diverged from `backend/app/models.py`. | Consolidate onto canonical `models.py`. |
| **DEF-03** | **P1** | `netspout/bin/run_simulation.py`<br>`PLATFORM_MAP` (lines 30–44) | Hardcoded user path `/Users/mahamudc/...`. | Portable binary resolution across environments. | Fails on any external machine or Docker container lacking the exact local path. | Development machine paths left in production script. | Use relative path resolution or containerized binaries. |
| **DEF-04** | **P1** | `netspout/appserver/static/samples_manifest.json` | Duplicate IDs: `nutanixpc-syslog`, `nutanixpc-vms`. | Every sample ID must be unique. | Manifest parsers and index lookups produce duplicate entries or collisions. | Copy-paste error during manifest generation. | Deduplicate manifest entries. |
| **DEF-05** | **P2** | `netspout/default/eventgen.conf` & `samples_manifest.json` | Typo `cisco:sdwan:sytem:logs` (missing 's'). | Standard naming: `cisco:sdwan:system:logs`. | Inconsistent sourcetypes indexed; search queries fail. | Legacy typographical error. | Canonicalize to `system` with backward-compatible alias. |
| **DEF-06** | **P2** | `netspout/bin/telemetry_dispatcher.py` | Missing candidate URL substitution (`:8888` <-> `:8088`). | Seamless dispatch regardless of host vs container networking. | HEC dispatch fails if container port mapping differs from host. | Diverged from `backend/app/telemetry_dispatcher.py`. | Unify dispatcher into shared package. |
| **DEF-07** | **P3** | `backend/app/main.py` | Unrestricted CORS: `allow_origins=["*"]`. | Restricted CORS policy. | Any web origin can trigger simulator controls if port 8081 is exposed. | Permissive dev configuration. | Restrict CORS to localhost and configured Splunk Web host. |

---

## 17. Security Review

A lightweight, code-level static security review identified the following posture characteristics:
* **CORS Wildcard:** `backend/app/main.py` configures `allow_origins=["*"]` with `allow_credentials=True`. When exposed on external interfaces, this allows cross-site request execution against simulation control endpoints.
* **Unauthenticated Management Endpoints:** Fast simulation API routes on port 8081 (`/api/scenarios/run`, `/api/topology`, `/api/logs`) enforce no authentication or bearer tokens.
* **Shell Execution Safety:** Both `datablaster_rest.py` and `datablaster_executor.py` strictly enforce `shell=False` and execute processes using explicit argument arrays, preventing command injection vulnerabilities.
* **Hardcoded Default Tokens:** NetSpout defaults to `00000000-0000-0000-0000-000000000000` for Splunk HEC across templates and manifests. While convenient for local development, production deployment guides must enforce token rotation.
* **Local Path Exposure:** Hardcoded paths in `run_simulation.py` leak the development directory structure (`/Users/mahamudc/...`).

---

## 18. Proposed Target Architecture

To eliminate architectural duplication while preserving 100% of working capabilities, NetSpout should consolidate onto a **Single Canonical Core Engine**:

```
                                  +---------------------------------------+
                                  |         Unified React Web UI          |
                                  |   (Canvas + Wizard + Path + SPL)      |
                                  +-------------------+-------------------+
                                                      |
                         +----------------------------+----------------------------+
                         |                                                         |
                         v (Embedded Splunk Iframe)                                v (Direct REST / WebSocket)
            +-------------------------+                               +-------------------------+
            |  Splunk App Wrapper     |                               | Standalone FastAPI App  |
            |  (netspout/default)     |                               | (netspout_api / CLI)    |
            +------------+------------+                               +------------+------------+
                         |                                                         |
                         +----------------------------+----------------------------+
                                                      |
                                                      v
                                  +---------------------------------------+
                                  |         netspout_core Engine          |
                                  |  - Canonical Models & Types           |
                                  |  - Graph & Dijkstra Cascade Solver    |
                                  |  - Multi-Protocol Telemetry Generator |
                                  |  - Unified Telemetry Dispatcher       |
                                  +-------------------+-------------------+
                                                      |
                                  +-------------------+-------------------+
                                  |           Data Catalogs               |
                                  |  - vendor_catalog.json                |
                                  |  - scenarios/                         |
                                  |  - samples/                           |
                                  +---------------------------------------+
```

### Architectural Principles:
1. **One Core Library (`netspout_core`):** A single Python package containing models, graph solvers, engines, and dispatchers, shared by both the Splunk App and the Standalone API.
2. **One Primary UI:** The React application (`frontend/src`) expands to host the Onboarding Wizard and Path Emitter natively as first-class components, eliminating 350KB+ of fragile jQuery DOM scripts.
3. **One Canonical Data Catalog:** Vendor definitions, sourcetypes, and scenarios stored as structured JSON/YAML files, eliminating hardcoded Python dictionaries.

---

## 19. Proposed Directory Structure

```
NetSpout/
├── netspout_core/                    # Canonical Shared Python Engine
│   ├── __init__.py
│   ├── models.py                     # Unified Pydantic models
│   ├── graph.py                      # Network graph & Dijkstra pathing
│   ├── scenarios/                    # Scenario execution engine
│   ├── generators/                   # Telemetry format generators
│   │   ├── syslog.py
│   │   ├── gnmi.py
│   │   ├── snmp.py
│   │   └── flow.py
│   ├── dispatcher/                   # Universal multi-pipeline dispatcher
│   │   ├── hec.py
│   │   ├── syslog.py
│   │   └── otel.py
│   └── catalog/                      # Canonical JSON catalogs
│       ├── vendors.json
│       └── scenarios.json
├── splunk_app/                       # Splunk Enterprise App Packaging
│   ├── default/
│   │   ├── app.conf
│   │   ├── inputs.conf
│   │   ├── indexes.conf
│   │   ├── restmap.conf
│   │   └── data/ui/nav/default.xml
│   ├── bin/
│   │   ├── netspout_rest.py          # Clean, vetted REST handler
│   │   └── netspout_streamer.py      # Modular input
│   └── appserver/static/
│       └── dist/                     # Compiled React SPA assets
├── standalone_api/                   # Fast Companion API Service
│   ├── run.py
│   └── server.py                     # Lightweight FastAPI wrapper around netspout_core
├── frontend/                         # Unified React 18 / TypeScript SPA
│   ├── src/
│   │   ├── components/
│   │   ├── views/                    # Canvas, Wizard, Scenarios, SPL
│   │   └── types/
│   ├── package.json
│   └── vite.config.ts
├── tests/
│   ├── unit/                         # Unit tests for core engines
│   ├── integration/                  # HEC and socket dispatch tests
│   └── e2e/                          # Full behavioral simulation-to-search tests
├── Dockerfile.standalone
└── docker-compose.yml
```

---

## 20. Refactor Dependency Graph

Consolidation must occur in strictly gated, test-verified stages to ensure zero disruption to live Splunk users:

```
[ Gate 0: Forensic Audit (Read-Only) ] -> CURRENT
                  │
                  v
[ Gate 1: Fix Active P0 Defect (List in datablaster_rest.py) ]
                  │
                  v
[ Gate 2: Unify Canonical Python Engine (Resolve backend vs netspout/bin) ]
                  │
                  v
[ Gate 3: Catalog & Sourcetype Normalization (Canonicalize sdwan typo & manifest) ]
                  │
                  v
[ Gate 4: Scenario & Topology Schema Harmonization ]
                  │
                  v
[ Gate 5: UI Consolidation (Integrate Wizard & Path into React SPA) ]
                  │
                  v
[ Gate 6: Telemetry Dispatcher Hardening (Retry buffers & connection pooling) ]
                  │
                  v
[ Gate 7: End-to-End Behavioral Test Suite ]
                  │
                  v
[ Gate 8: Dead Code Pruning (Remove datablaster_ui.js, unused legacy assets) ]
                  │
                  v
[ Gate 9: Production Release Verification & Splunk Packaging ]
```

### Stage Details:
* **Gate 1: Resolve P0 Runtime Defect**
  * *Objective:* Fix `NameError: name 'List' is not defined` in `netspout/bin/datablaster_rest.py`.
  * *Files Affected:* `netspout/bin/datablaster_rest.py`.
  * *Risk:* Very low (import fix).
  * *Completion Criteria:* REST calls return HTTP 200; OpenConfig probe succeeds in browser.
* **Gate 2: Consolidate Duplicated Python Engines**
  * *Objective:* Eliminate the 11 duplicate files by creating a single shared core package.
  * *Files Affected:* `backend/app/*`, `netspout/bin/*`.
  * *Risk:* Medium (import path updates).
  * *Completion Criteria:* Both standalone API and Splunk app run from identical engine code.
* **Gate 3: Sourcetype & Catalog Normalization**
  * *Objective:* Deduplicate `samples_manifest.json`, establish canonical `cisco:sdwan:system:logs`.
  * *Files Affected:* `samples_manifest.json`, `eventgen.conf`, `props.conf`.
  * *Risk:* Low (alias preservation protects existing searches).
  * *Completion Criteria:* 100% manifest integrity, zero duplicate IDs, zero broken searches.

---

## 21. Gate 1 Recommendation

**Gate 1 is ready to be initiated immediately upon user approval.**  
The primary objective of Gate 1 must be to resolve the active **P0 runtime failure (DEF-01)** in `netspout/bin/datablaster_rest.py` (adding `List` to the typing imports) and syncing `netspout/bin/models.py` with `backend/app/models.py`. This immediately restores full functionality to the "Emit 1 OpenConfig Metric Probe" and "Stream Continuous MDT" features reported by the user in Splunk Web, while setting a clean foundation for subsequent architectural unification.

---

## 22. Risks and Unknowns

1. **Docker Container Permissions:** The standalone container runs with non-root Splunk user permissions. Any file reorganization must preserve ownership (`splunk:splunk`).
2. **AppInspect Vetting Boundaries:** Consolidation of REST handlers must comply strictly with Splunk Cloud AppInspect rules (no dynamic `exec`, explicit subprocess argument lists).
3. **Browser CORS in Split Deployments:** When users access Splunk on port 8800 and the standalone engine on port 8081, cross-origin socket policies must be carefully managed.
