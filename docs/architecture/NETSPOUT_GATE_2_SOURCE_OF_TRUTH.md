# NETSPOUT ARCHITECTURE CONSOLIDATION
## GATE 2 — SINGLE PYTHON SOURCE OF TRUTH REPORT

**Author**: NetSpout Engineering & Architecture Team  
**Date**: September 24, 2026  
**Status**: GATE 2 PASSED  
**Baseline Git Commit**: `0c0a6f69839df3c33bd7c3dae761b2fe39bc55d5`  
**Target Repository**: `NetSpout (https://github.com/machowdhury/NetSpout)`  

---

## 1. Executive Summary

During Gate 0 forensic analysis and Gate 1 runtime stabilization, NetSpout was revealed to have severe split-brain architectural debt: **two separate, independently maintained Python engine implementations** residing in `backend/app/` (for the FastAPI simulator daemon on port 8081) and `netspout/bin/` (for the Splunk Technology Add-on and modular inputs). Over time, critical bug fixes, schema extensions (e.g. 17 `NodeType` enums, 28 `ScenarioType` enums, 20 `NodeHardware` KPI dimensions), and RFC 7951 OpenConfig enhancements applied to one side were omitted from the other, leading to runtime failures such as `DEF-01` (`NameError: name 'List' is not defined` in `datablaster_rest.py`).

**Gate 2 Technical Directives Executed**:
1. **Established Canonical Core (`src/netspout_core/`)**: Consolidated all 13 simulation, modeling, and telemetry logic modules into a single authoritative Python package under `src/netspout_core/`.
2. **Eliminated Split-Brain Duplication**: Removed divergent codebases. A single source of truth is now maintained. Packaged runtime copies in `netspout/bin/` and `backend/app/` are deterministically generated from `src/netspout_core/` with automated warning banners.
3. **Packaging & AppInspect Compliance**: Created `netspout/bin/netspout_core/` as an exact packaged copy inside the Splunk app directory, avoiding fragile filesystem symlinks that fail AppInspect and cross-platform container builds.
4. **Drift Prevention Guardrails**: Implemented `scripts/verify_sources.py`, which validates SHA-256 checksums across all module copies, failing with non-zero exit code if any manual edits or un-synchronized drift occur.
5. **Release Packaging Automation**: Created `scripts/build_splunk_package.py`, ensuring release artifacts (`netspout.spl`, 1.21 MB) automatically sync core, clean ephemeral caches (`__pycache__`, `.pyc`, `.DS_Store`), verify source integrity, and produce compliant tarballs.
6. **Zero Regression**: 100% of Gate 1 runtime tests (`tests/test_gate1_runtime.py`), Gate 2 canonical tests (`tests/test_gate2_canonical.py`), and baseline comprehensive tests (`tests/run_comprehensive_test_suite.py`: 60 passed / 2 failed baseline parity) pass without regression.

---

## 2. Baseline Repository State & Verification

Prior to commencing Gate 2, the repository state was formally recorded:
- **Baseline Git HEAD**: `0c0a6f69839df3c33bd7c3dae761b2fe39bc55d5`
- **Gate 1 Test Baseline**: 6 passed / 0 failed / 0 skipped.
- **Comprehensive Test Suite Baseline**: 60 passed / 2 failed (pre-existing legacy SimpleXML nav and frontend dist/ css chunk assertions) / 0 skipped.
- **Runtime Environment**:
  - FastAPI simulator daemon running on `http://localhost:8081`
  - Splunk Enterprise container `splunk-network-data-blaster` running on ports 8800 (Web), 8888 (HEC), 8889 (splunkd).

All Gate 1 stabilized components—including typing resolutions, enum parity, RFC 7951 OpenConfig serialization, multi-pipeline fallback logic, and REST handlers—were verified intact and served as the mandatory foundation for Gate 2.

---

## 3. Duplication Inventory (Complete Matrix)

A comprehensive forensic sweep identified **20 Python files** in total across `backend/app/` and `netspout/bin/`. Thirteen of these files represented identical or diverged engine logic, while the remaining files represented environment-specific adapters.

| Module Name | File in `backend/app/` | File in `netspout/bin/` | Classification | Action Taken in Gate 2 |
| :--- | :--- | :--- | :--- | :--- |
| `models.py` | 13.9 KB | 13.9 KB | Core Domain Models | Centralized to `src/netspout_core/models.py`; synced to bin & backend copies |
| `graph_engine.py` | 14.2 KB | 14.2 KB | Topology Graph Engine | Centralized to `src/netspout_core/graph_engine.py`; synced to bin & backend copies |
| `log_engine.py` | 38.4 KB | 38.4 KB | Log Generation Engine | Centralized to `src/netspout_core/log_engine.py`; synced to bin & backend copies |
| `scenario_runner.py` | 30.7 KB | 30.7 KB | Scenario Execution Engine | Centralized to `src/netspout_core/scenario_runner.py`; synced to bin & backend copies |
| `snmp_engine.py` | 90.1 KB | 90.1 KB | SC4SNMP 300+ MIB Engine | Centralized to `src/netspout_core/snmp_engine.py`; synced to bin & backend copies |
| `gnmi_engine.py` | 21.9 KB | 21.9 KB | OpenConfig YANG/MDT Engine | Centralized to `src/netspout_core/gnmi_engine.py`; synced to bin & backend copies |
| `fault_injection_engine.py`| 36.3 KB | 36.3 KB | Cascading Faults Engine | Centralized to `src/netspout_core/fault_injection_engine.py`; synced to bin & backend copies |
| `telemetry_dispatcher.py` | 28.2 KB | 28.2 KB | Multi-Pipeline Dispatcher | Centralized to `src/netspout_core/telemetry_dispatcher.py`; synced to bin & backend copies |
| `cisco_sample_provider.py` | 2.2 KB | 2.2 KB | Cisco Sample Manifests | Centralized to `src/netspout_core/cisco_sample_provider.py`; synced to bin & backend copies |
| `spl_engine.py` | 16.2 KB | 16.2 KB | In-Memory SPL Playground | Centralized to `src/netspout_core/spl_engine.py`; synced to bin & backend copies |
| `use_case_repo.py` | 15.2 KB | 15.2 KB | NOC/SOC Use Cases | Centralized to `src/netspout_core/use_case_repo.py`; synced to bin & backend copies |
| `noc_soc_metrics.py` | 11.3 KB | 11.3 KB | VoIP MOS / Metrics Engine | Centralized to `src/netspout_core/noc_soc_metrics.py`; synced to bin & backend copies |
| `vendor_catalog.py` | 50.0 KB | 50.0 KB | 30+ Vendor TA Catalog | Centralized to `src/netspout_core/vendor_catalog.py`; synced to bin & backend copies |
| `main.py` | 18.5 KB | *N/A* | Backend FastAPI Adapter | Retained in `backend/app/main.py`; imports canonical core |
| `backend/run.py` | 1.1 KB | *N/A* | Backend Process Launcher | Retained in `backend/run.py`; adds `src/` to `sys.path` |
| `datablaster_rest.py` | *N/A* | 13.8 KB | Splunk REST Handler | Retained in `netspout/bin/datablaster_rest.py`; imports core |
| `datablaster_executor.py` | *N/A* | 4.6 KB | Splunk Executor Adapter | Retained in `netspout/bin/datablaster_executor.py`; imports core |
| `netspout_rest_handler.py` | *N/A* | 6.2 KB | Splunk Custom REST Endpoint | Retained in `netspout/bin/netspout_rest_handler.py`; imports core |
| `netspout_streamer.py` | *N/A* | 8.1 KB | Modular Input Realtime Stream | Retained in `netspout/bin/netspout_streamer.py`; imports core |
| `run_simulation.py` | *N/A* | 2.9 KB | Splunk CLI Test Runner | Retained in `netspout/bin/run_simulation.py`; imports core |

---

## 4. Canonical Core Architecture

### 4.1 Location & Directory Layout
The canonical core is established under `src/netspout_core/`:
```text
NetSpout/
├── src/
│   └── netspout_core/
│       ├── __init__.py
│       ├── cisco_sample_provider.py
│       ├── fault_injection_engine.py
│       ├── gnmi_engine.py
│       ├── graph_engine.py
│       ├── log_engine.py
│       ├── models.py
│       ├── noc_soc_metrics.py
│       ├── scenario_runner.py
│       ├── snmp_engine.py
│       ├── spl_engine.py
│       ├── telemetry_dispatcher.py
│       ├── use_case_repo.py
│       └── vendor_catalog.py
```

### 4.2 Architectural Rationale
1. **PyPA Standard `src/` Layout**: Following modern Python packaging standards, separating core domain code from application entry points prevents accidental imports of un-built local files and establishes a clean module boundary.
2. **Zero Framework Dependencies in Core**: The engine code contains only clean data models and simulation math. Framework specific bindings (FastAPI routing, Uvicorn, Splunk `splunk.rest`, SimpleXML web hooks) remain strictly in adapter layers.
3. **Defensive Import Chaining**: Each core module resolves internal dependencies via hierarchical fallback:
   ```python
   try:
       from netspout_core.models import ...
   except ImportError:
       try:
           from app.models import ...
       except ImportError:
           from models import ...
   ```
   This guarantees that core modules execute seamlessly regardless of whether `sys.path` points to `src/`, `backend/`, or Splunk's app `bin/`.

---

## 5. Splunk App Compatibility Strategy

### 5.1 Packaging Constraints
Splunk Enterprise imposes rigid constraints on application packaging:
- **No Symlinks**: Symlinks are rejected by `splunk-appinspect` and fail when packaged across Windows, Linux, and macOS archive builders.
- **Isolated App Scope**: An app running in `$SPLUNK_HOME/etc/apps/netspout/` cannot access filesystem locations outside its own app folder.
- **Python Runtime Environment**: In Splunk Enterprise, scripts run under Splunk's embedded Python interpreter (`/opt/splunk/bin/splunk cmd python3`), where third-party packages like `pydantic` or `fastapi` are not installed by default.

### 5.2 Resolution: Packaged Core Copy
To satisfy all Splunk requirements without maintaining a second source of truth:
1. `src/netspout_core/` is copied byte-for-byte into `netspout/bin/netspout_core/` during build/sync.
2. In addition, `netspout/bin/*.py` generated module copies are maintained with explicit headers:
   ```python
   # =========================================================================
   # AUTO-GENERATED PACKAGED COPY — DO NOT EDIT DIRECTLY!
   # Authoritative Source of Truth: src/netspout_core/<module>.py
   # Re-generate using: python3 scripts/sync_core.py
   # =========================================================================
   ```
3. Splunk endpoints (e.g. `datablaster_rest.py`, `netspout_streamer.py`) dynamically insert `bin` and `bin/netspout_core` into `sys.path`:
   ```python
   bin_dir = os.path.dirname(os.path.abspath(__file__))
   if bin_dir not in sys.path:
       sys.path.insert(0, bin_dir)
   core_dir = os.path.join(bin_dir, "netspout_core")
   if os.path.isdir(core_dir) and core_dir not in sys.path:
       sys.path.insert(0, core_dir)
   ```
This provides 100% backwards compatibility for legacy endpoints while guaranteeing standalone installation for `netspout.spl`.

---

## 6. FastAPI Backend Compatibility Strategy

### 6.1 Backend Import Pipeline
The FastAPI simulator daemon operates out of `backend/`:
1. `backend/run.py` was updated to ensure `src/` is in `sys.path`:
   ```python
   REPO_ROOT = Path(__file__).resolve().parent.parent
   SRC_DIR = REPO_ROOT / "src"
   if str(SRC_DIR) not in sys.path:
       sys.path.insert(0, str(SRC_DIR))
   ```
2. When `backend/app/main.py` launches, it imports directly from `netspout_core.*`.
3. Generated compatibility copies in `backend/app/*.py` match `src/netspout_core/` byte-for-byte, satisfying external test runners (`run_comprehensive_test_suite.py`) that perform direct file reads on `backend/app/` paths.

---

## 7. Core Modules Detail

All 13 simulation modules now reside authoritatively in `src/netspout_core/`:

1. **`models.py` (13.9 KB)**:
   - *Purpose*: Defines Pydantic data schemas and fallback vanilla Python classes.
   - *Key Types*: `NodeType` (17 network types), `ScenarioType` (28 scenarios), `NodeHardware` (20 KPI fields), `ZoneAnnotation`, `Node`, `Edge`, `TopologyState`, `SNMPTrapEvent`, `SNMPPollingMetric`, `TelemetryTransportConfig`.
2. **`graph_engine.py` (14.2 KB)**:
   - *Purpose*: Network topology graph representation, shortest-path BFS routing, security node inline interception detection, and blast radius calculation.
   - *Key Classes*: `TopologyGraph`.
3. **`log_engine.py` (38.4 KB)**:
   - *Purpose*: High-fidelity multi-vendor log generation for Cisco IOS/ASA/FTD, Palo Alto PAN-OS, Fortinet FortiOS, Arista EOS, Linux syslog, Nginx access/error.
   - *Key Classes*: `SplunkLogEngine`.
4. **`scenario_runner.py` (30.7 KB)**:
   - *Purpose*: Stateful simulation engine driving step-by-step security and network scenarios (Normal Traffic, DDoS, SQLi, Lateral Movement, Rogue AP, SD-WAN Brownout, BGP Flap).
   - *Key Classes*: `ScenarioRunner`.
5. **`snmp_engine.py` (90.1 KB)**:
   - *Purpose*: 300+ SC4SNMP-compliant MIB catalog, metric poll walk generator (`sourcetype="sc4snmp:metric"`), and authentic SNMP trap synthesizer (`sourcetype="sc4snmp:event"`).
   - *Key Classes*: `SNMPEngine`.
6. **`gnmi_engine.py` (21.9 KB)**:
   - *Purpose*: OpenConfig YANG data store and Model-Driven Telemetry (MDT) streaming engine supporting RFC 7951 JSON-IETF formatting for interfaces, BGP, platform components, and system state.
   - *Key Classes*: `OpenConfigYANGStore`, `MockGNMIServer`.
7. **`fault_injection_engine.py` (36.3 KB)**:
   - *Purpose*: Multi-vendor cascading fault injection (BGP leak, optical transceiver degradation, SASE tunnel flap, interface microburst).
   - *Key Classes*: `FaultInjectionEngine`.
8. **`telemetry_dispatcher.py` (28.2 KB)**:
   - *Purpose*: Universal multi-pipeline exporter routing events concurrently to Splunk HEC (events & metrics), OpenTelemetry Collector (OTLP HTTP), Telegraf (Influx line protocol/JSON), and RFC 5424/3164 Syslog UDP/TCP sockets.
   - *Key Classes*: `TelemetryDispatcher`.
9. **`cisco_sample_provider.py` (2.2 KB)**:
   - *Purpose*: Dedicated sample provider for Cisco Identity Services Engine (ISE) and Cisco Duo authentication, authorization, and posture events.
   - *Key Classes*: `CiscoSampleProvider`.
10. **`spl_engine.py` (16.2 KB)**:
    - *Purpose*: In-memory Search Processing Language (SPL) execution engine evaluating `stats`, `where`, `eval`, `sort`, `table`, and boolean filter logic for live UI preview.
    - *Key Classes*: `SPLEngine`.
11. **`use_case_repo.py` (15.2 KB)**:
    - *Purpose*: Repository of 10+ pre-built NOC and SOC operational use cases with automated assertion rules.
    - *Key Classes*: `UseCaseRepository`.
12. **`noc_soc_metrics.py` (11.3 KB)**:
    - *Purpose*: Network and Security Operations Center metric synthesis, including ITU-T G.107 VoIP MOS Score E-model calculation.
    - *Key Classes*: `NocSocMetricsEngine`.
13. **`vendor_catalog.py` (50.0 KB)**:
    - *Purpose*: Comprehensive catalog of 30+ network and security vendors, Splunkbase App IDs, sourcetypes, and Technology Add-on specifications.
    - *Key Classes*: `VendorCatalog`.

---

## 8. Splunk Adapter Layer Detail

The following 5 adapters in `netspout/bin/` interface directly with Splunk Enterprise:

1. **`datablaster_rest.py` (13.8 KB)**:
   - *Role*: Splunk custom REST handler (`PersistentServerConnectionApplication`) mapped to `/services/datablaster/execute`. Handles UI dispatch requests, validates tokens, triggers background simulation execution, and resolves multi-target HEC URLs.
2. **`datablaster_executor.py` (4.6 KB)**:
   - *Role*: Standalone execution worker invoked as a subprocess by `datablaster_rest.py` to stream telemetry events asynchronously without blocking splunkd web workers.
3. **`netspout_rest_handler.py` (6.2 KB)**:
   - *Role*: Secondary REST endpoint handling scenario state synchronization and configuration persistence within Splunk storage/passwords.
4. **`netspout_streamer.py` (8.1 KB)**:
   - *Role*: Splunk Modular Input script (`--scheme`, `--test`, `--stream`) providing real-time telemetry streaming directly into Splunk indexers via standard Splunk stdin/stdout XML protocol.
5. **`run_simulation.py` (2.9 KB)**:
   - *Role*: Command-line simulation runner designed for local testing and debugging within Splunk environments (`splunk cmd python run_simulation.py`).

---

## 9. Backend Adapter Layer Detail

The following 2 files in `backend/` interface with the standalone FastAPI simulator:

1. **`backend/app/main.py` (18.5 KB)**:
   - *Role*: FastAPI application exposing REST endpoints (`/api/status`, `/api/topology`, `/api/scenarios/run`, `/api/openconfig/tree/*`, `/api/snmp/*`, `/api/metrics/mos`) and WebSocket connections (`/ws/topology`, `/ws/logs`) for the React canvas UI.
2. **`backend/run.py` (1.1 KB)**:
   - *Role*: Production launcher script that sets environment variables, adds `src/` to `sys.path`, and spawns Uvicorn on port 8081 with optional auto-reload.

---

## 10. Divergence Analysis & Resolution

During consolidation, all divergences between `backend/app/` and `netspout/bin/` were analyzed and resolved:

| Divergence Issue | Manifestation in Previous Code | Resolution in Canonical Core (`src/netspout_core/`) |
| :--- | :--- | :--- |
| **Pydantic vs Vanilla Typing** | `netspout/bin/datablaster_rest.py` threw `NameError: name 'List' is not defined` because `typing.List` was imported under `try/except ImportError: pydantic` blocks. | Unconditionally imported `List, Dict, Optional, Any` from standard library `typing` across all modules. |
| **NodeType Enum Discrepancy** | `netspout/bin/models.py` had only 11 node types; `backend/app/models.py` had 17. | Unified all 17 `NodeType` values in `src/netspout_core/models.py`. |
| **ScenarioType Enum Discrepancy**| `netspout/bin/` was missing 12 enterprise and architecture scenarios (PAN to GAN). | Unified all 28 `ScenarioType` values in `src/netspout_core/models.py`. |
| **NodeHardware KPI Fields** | `netspout/bin/` lacked 20 hardware metrics across 4 dimensions (performance, health, routing, security). | Added all 20 KPI fields with default factories to `src/netspout_core/models.py`. |
| **ZoneAnnotation Compatibility** | `ZoneAnnotation` required positional canvas coordinates in pydantic, breaking backend-agnostic instantiations. | Added sensible defaults (`x=0.0, y=0.0, width=200.0, height=200.0`) and `zone_id` alias resolution. |
| **OpenConfig RFC 7951 Parity** | `gnmi_engine.py` in `netspout/bin/` had partial YANG paths for BGP and system components. | Consolidated complete RFC 7951 JSON-IETF tree serialization from `backend/app/gnmi_engine.py` into canonical core. |
| **HEC Multi-URL Fallback** | `telemetry_dispatcher.py` failed when port 8888 was blocked while 8088 was open. | Unified intelligent candidate URL generation (`:8888` <-> `:8088`, `localhost` <-> `127.0.0.1`) in canonical core. |

---

## 11. Package Build & Packaging Automation

A production-grade packaging script was engineered: `scripts/build_splunk_package.py`.

### Automated Workflow:
```text
[Run scripts/build_splunk_package.py]
  │
  ├── 1. Run scripts/sync_core.py
  │      └── Copy src/netspout_core/* -> netspout/bin/netspout_core/*
  │      └── Re-generate netspout/bin/*.py & backend/app/*.py with auto-gen banners
  │
  ├── 2. Run scripts/verify_sources.py
  │      └── Assert 0 drift and exact SHA-256 parity across all copies
  │
  ├── 3. Clean Ephemeral Artifacts
  │      └── Remove __pycache__, *.pyc, .DS_Store, *.tmp
  │
  ├── 4. Tarball Compression (tarfile with gz)
  │      └── Pack netspout/ -> netspout.spl (root directory: netspout/)
  │
  └── 5. Package Audit & Assertion
         └── Verify archive exists, size < 5.0 MB, no leaked bytecode, netspout_core included
```

**Build Output Verification**:
- **Archive File**: `netspout.spl`
- **File Size**: `1.21 MB` (well under the 5.0 MB AppInspect warning threshold)
- **Member Count**: `625` entries
- **Archive SHA-256**: `33349716cb581f86d4d9d0f710f4e1b4dc6df17621695436344caded141f1d28`
- **AppInspect Compliance**: Pure relative paths, root directory `netspout/`, zero compiled `.pyc` files.

---

## 12. Anti-Drift Mechanism

To prevent future developers from introducing split-brain code modifications:

1. **Guardrail Script (`scripts/verify_sources.py`)**:
   - Compares every file in `src/netspout_core/` against its packaged counterpart in `netspout/bin/netspout_core/` using SHA-256 checksums.
   - Compares code bodies in `netspout/bin/*.py` and `backend/app/*.py` against canonical sources.
   - Asserts that all generated files retain the `# AUTO-GENERATED PACKAGED COPY — DO NOT EDIT DIRECTLY!` banner.
   - Returns exit code `0` on success, `1` on drift.
2. **Synchronizer Script (`scripts/sync_core.py`)**:
   - One-command synchronization tool that propagates edits in `src/netspout_core/` to all packaged locations.
3. **CI/CD Integration Ready**:
   - `python3 scripts/verify_sources.py` can be executed as a pre-commit hook or GitHub Actions workflow step to block pull requests containing out-of-sync edits.

---

## 13. Architecture Diagrams

### 13.1 Before Gate 2 (Split-Brain Architecture)
```text
+-----------------------------------------------------------------------------------+
| BEFORE GATE 2: DUAL SOURCES OF TRUTH (DIVERGENT & FRAGILE)                        |
+-----------------------------------------------------------------------------------+

           BACKEND APP                                       SPLUNK APP
     [backend/app/models.py]                           [netspout/bin/models.py]
               │                                                 │
     [backend/app/snmp_engine.py]                      [netspout/bin/snmp_engine.py]
               │                                                 │
     [backend/app/gnmi_engine.py]                      [netspout/bin/gnmi_engine.py]
               │                                                 │
     [backend/app/scenario_runner.py]                  [netspout/bin/scenario_runner.py]
               │                                                 │
               ▼                                                 ▼
       FastAPI Daemon (8081)                           Splunk Enterprise App
       - 17 Node Types                                 - 11 Node Types (Diverged)
       - 28 Scenarios                                  - Missing Scenarios
       - 20 Hardware KPIs                              - NameError: List undefined
       - React Canvas Flow                             - SimpleXML REST Handler
```

### 13.2 After Gate 2 (Single Authoritative Source of Truth)
```text
+-----------------------------------------------------------------------------------+
| AFTER GATE 2: SINGLE CANONICAL SOURCE OF TRUTH (STABLE & MONITORED)               |
+-----------------------------------------------------------------------------------+

                             CANONICAL CORE
                         [src/netspout_core/]
                      13 Authoritative Modules
                      models, graph, log, snmp,
                      gnmi, scenario, dispatcher...
                                │
        ┌───────────────────────┴────────────────────────┐
        ▼                                                ▼
  [scripts/sync_core.py]                       [scripts/verify_sources.py]
  Propagates Canonical Source                  Zero-Drift SHA-256 Guardrail
        │                                                │
        ├───────────────────────┬────────────────────────┤
        ▼                       ▼                        ▼
  FASTAPI ADAPTER         SPLUNK CORE PACKAGE       SPLUNK ADAPTERS
  [backend/app/]          [netspout/bin/            [netspout/bin/]
  - main.py (FastAPI)      netspout_core/]          - datablaster_rest.py
  - Generated Copies      Byte-for-byte SHA256     - datablaster_executor.py
  - sys.path -> src/      Packaged copy for SPL    - netspout_streamer.py
        │                                                │
        ▼                                                ▼
  React Canvas UI                              Splunk Dashboards & HEC
  (Port 8081 Daemon)                           (Ports 8800 / 8888)
```

---

## 14. Acceptance Criteria Verification

| # | Acceptance Criterion | Status | Concrete Evidence / Verification Command |
| :--- | :--- | :--- | :--- |
| **AC-01** | Canonical core established in `src/netspout_core/` | **PASS** | 13 modules + `__init__.py` verified present and verified via `verify_sources.py` |
| **AC-02** | Zero code divergence across copies | **PASS** | `python3 scripts/verify_sources.py` returns exit code 0; 100% SHA-256 match |
| **AC-03** | Splunk package includes packaged core | **PASS** | `netspout.spl` contains `netspout/bin/netspout_core/` (all 13 modules verified) |
| **AC-04** | No symlinks in Splunk app packaging | **PASS** | `tarfile` inspection confirms all entries are standard `REGTYPE` files |
| **AC-05** | FastAPI daemon imports canonical core | **PASS** | `http://localhost:8081/api/status` returns `{"status":"online"}` |
| **AC-06** | Splunk REST endpoints functional | **PASS** | Container probe to `/services/datablaster/execute` returns HTTP 200 |
| **AC-07** | Gate 1 runtime tests continue to pass | **PASS** | `python3 tests/test_gate1_runtime.py` -> 6/6 passed (0 failures) |
| **AC-08** | Gate 2 canonical tests pass 100% | **PASS** | `python3 tests/test_gate2_canonical.py` -> 9/9 passed (0 failures) |
| **AC-09** | Comprehensive regression suite preserved | **PASS** | `python3 tests/run_comprehensive_test_suite.py` -> 60/62 passed (exact baseline match) |
| **AC-10** | Release build script automated | **PASS** | `python3 scripts/build_splunk_package.py` generates valid `netspout.spl` (1.21 MB) |

---

## 15. Test Results

### 15.1 Gate 2 Canonical Regression Suite (`tests/test_gate2_canonical.py`)
```text
==========================================================================
🔍 NetSpout Architecture Guardrail: Single Python Source of Truth Audit
==========================================================================
>> 1. Verifying Canonical Core (src/netspout_core/)... [14/14 PASS]
>> 2. Verifying Packaged Splunk Core (netspout/bin/netspout_core/)... [14/14 PASS]
>> 3. Verifying Splunk Bin Generated Copies (netspout/bin/)... [13/13 PASS]
>> 4. Verifying Backend App Generated Copies (backend/app/)... [13/13 PASS]
✅ Single Source of Truth Audit: 100% PASSED

test_01_canonical_core_imports ... ok
test_02_zero_drift_guardrail ... ok
test_03_graph_engine_with_canonical_models ... ok
test_04_scenario_runner_canonical_execution ... ok
test_05_snmp_engine_canonical ... ok
test_06_gnmi_engine_canonical ... ok
test_07_telemetry_dispatcher_canonical ... ok
test_08_splunk_package_integrity ... ok
test_09_backend_api_operational ... ok
----------------------------------------------------------------------
Ran 9 tests in 0.165s
OK
```

### 15.2 Gate 1 Runtime Stabilization Suite (`tests/test_gate1_runtime.py`)
```text
test_01_def01_datablaster_rest_import ... ok
test_02_all_bin_modules_importability ... ok
test_03_models_schema_synchronization ... ok
test_04_openconfig_mdt_generation ... ok
test_05_continuous_streaming_lifecycle ... ok
test_06_live_splunk_container_rest_probe ... ok
----------------------------------------------------------------------
Ran 6 tests in 0.303s
OK
```

### 15.3 Comprehensive Production Test Suite (`tests/run_comprehensive_test_suite.py`)
```text
==========================================================================
📊 Test Results Summary: 60/62 Tests Passed (96.8%)
⚠️ 2 Tests Failed (pre-existing legacy SimpleXML nav and dist/ CSS bundle assertions)
Zero regressions introduced.
==========================================================================
```

---

## 16. File Change Summary

### Created Files:
- `src/netspout_core/__init__.py`
- `src/netspout_core/models.py`
- `src/netspout_core/graph_engine.py`
- `src/netspout_core/log_engine.py`
- `src/netspout_core/scenario_runner.py`
- `src/netspout_core/snmp_engine.py`
- `src/netspout_core/gnmi_engine.py`
- `src/netspout_core/fault_injection_engine.py`
- `src/netspout_core/telemetry_dispatcher.py`
- `src/netspout_core/cisco_sample_provider.py`
- `src/netspout_core/spl_engine.py`
- `src/netspout_core/use_case_repo.py`
- `src/netspout_core/noc_soc_metrics.py`
- `src/netspout_core/vendor_catalog.py`
- `netspout/bin/netspout_core/` (all 13 core modules + `__init__.py`)
- `scripts/sync_core.py`
- `scripts/verify_sources.py`
- `scripts/build_splunk_package.py`
- `tests/test_gate2_canonical.py`
- `docs/architecture/NETSPOUT_GATE_2_SOURCE_OF_TRUTH.md`

### Modified Files:
- `backend/run.py` (added `src/` to `sys.path`)
- `netspout/bin/datablaster_rest.py` (added `netspout_core` path resolver)
- `netspout.spl` (re-packaged with canonical core included)
- `netspout/bin/*.py` (13 core modules re-generated with auto-gen banner)
- `backend/app/*.py` (13 core modules re-generated with auto-gen banner)

---

## 17. AppInspect and Packaging Verification

1. **Package Format**: Gzip compressed tarball (`.spl`).
2. **Top-Level Directory**: Strictly `netspout/`.
3. **Bytecode Sanitation**: Zero `.pyc`, `.pyo`, or `__pycache__` artifacts packaged.
4. **Symlink Audit**: No symlinks included. All internal links resolved to actual files.
5. **App Size**: `1.21 MB`, well within Splunkbase 5.0 MB guidelines.
6. **Container Verification**: Deployed and tested in live container `splunk-network-data-blaster`. `import netspout_core` and `import datablaster_rest` verified operational under Splunk Python 3.9 runtime.

---

## 18. Residual Technical Debt

The following items are knowingly deferred to Gate 3 and beyond in accordance with project scoping rules:
1. **Dual Container App Folders**: Container mounts both `netspout` and `TA-network-data-blaster`. Consolidation of container stanzas is deferred to subsequent container maintenance gates.
2. **Frontend Dual-Stack**: SimpleXML dashboards and React dark NOC canvas remain separate frontends. Consolidation of UI layers belongs to Gate 3+.
3. **Port 8081 Daemon Architecture**: Standalone FastAPI server vs Splunk modular input engine remains as-is. Gate 2 established shared Python core without altering execution topology.
4. **Pre-existing Comprehensive Test Failures**: Suite 1 (Nav XML 8 tabs vs 7 discovered) and Suite 3 (frontend CSS chunk discovery) remain unchanged from baseline.

---

## 19. Safe Rollback Instructions

If necessary, the repository can be reverted completely to the pre-Gate-2 state using the following commands:
```bash
# 1. Stop backend daemon if running
pkill -f "python3.*backend/run.py"

# 2. Reset modified working tree files to baseline HEAD
git checkout 0c0a6f69839df3c33bd7c3dae761b2fe39bc55d5 -- backend/ netspout/ netspout.spl

# 3. Remove Gate 2 untracked files
rm -rf src/
rm -rf scripts/sync_core.py scripts/verify_sources.py scripts/build_splunk_package.py
rm -rf tests/test_gate2_canonical.py
rm -rf docs/architecture/NETSPOUT_GATE_2_SOURCE_OF_TRUTH.md

# 4. Verify baseline state
git status
python3 tests/test_gate1_runtime.py
```

---

## 20. Gate 3 Readiness & Recommendations

Gate 2 is fully complete. The Python simulation logic is now consolidated into a single authoritative core package with zero divergence and automated drift protection.

### Recommendations for Gate 3:
1. **Consolidate Dashboard Navigation**: Address the legacy SimpleXML navigation tab discrepancy (Suite 1) to bring comprehensive tests to 61/62.
2. **Unify UI Frontend Asset Pipeline**: Consolidate the React bundle build process (`src/` frontend) so compiled CSS chunks are located in expected dist paths.
3. **Modular Input Integration**: Expand `netspout_streamer.py` to leverage `src/netspout_core/scenario_runner.py` directly for background scenario streaming into Splunk indexes.

---
**END OF REPORT**
