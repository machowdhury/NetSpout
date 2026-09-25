# NetSpout Architecture Consolidation
## Gate 1 — P0 Runtime Stabilization Report

**Author:** NetSpout Core Engineering (Antigravity)  
**Date:** September 24, 2026  
**Status:** COMPLETE  
**Repository:** https://github.com/machowdhury/NetSpout  

---

## 1. Baseline

Before applying any code changes for Gate 1, the repository baseline state was captured and verified:

* **Git Branch:** `main`
* **Baseline HEAD SHA:** `0c0a6f69839df3c33bd7c3dae761b2fe39bc55d5`
* **Baseline Working Tree State:** Clean working tree relative to `origin/main`.
* **Pre-existing Untracked Artifacts:** `docs/architecture/NETSPOUT_GATE_0_FORENSIC_AUDIT.md` (Gate 0 deliverable).
* **Pre-existing Test Suite Baseline:** 60/62 tests passing (Suite 1 navigation tab count: 7 vs 8; Suite 3 CSS chunks: 0 due to inline Vite bundling).
* **Container Environment:** `splunk-network-data-blaster` (Splunk Enterprise 10.2, Python 3.9.18) running on host ports 8800 (Web), 8888 (HEC), 8889 (splunkd REST).
* **Companion Daemon:** Fast Simulation backend daemon running on port 8081.

---

## 2. Reproduced DEF-01

### 2.1 Symptom
When navigating to Splunk Web Scenario Builder (`http://localhost:8800/en-US/app/netspout/scenario_builder`), clicking **Emit 1 OpenConfig Metric Probe** or **Stream Continuous MDT (10/s)** resulted in immediate UI failures:
```text
[9:44:37 AM] ✖ REST ERROR: Unexpected token '<', "
[9:44:37 AM] OPENCONFIG MDT STOPPED: MDT telemetry stream halted.
[9:44:37 AM] ✖ REST ERROR: Unexpected token '<', "
```

### 2.2 Forensic Reproduction
To reproduce DEF-01 deterministically prior to modification, the REST handler was imported inside the target runtime environment (Python 3.9.18 inside `splunk-network-data-blaster`):
```bash
docker exec splunk-network-data-blaster /opt/splunk/bin/splunk cmd python -c "
import sys
sys.path.insert(0, '/opt/splunk/etc/apps/netspout/bin')
import datablaster_rest
"
```
**Observed Output:**
```text
Traceback (most recent call last):
  File "<string>", line 4, in <module>
  File "/opt/splunk/etc/apps/netspout/bin/datablaster_rest.py", line 128, in <module>
    def resolve_hec_urls(hec_url: str) -> List[str]:
NameError: name 'List' is not defined
```
When invoked via Splunk Web (`/splunkd/__raw/services/datablaster/execute`), splunkd caught this unhandled exception during handler instantiation and returned an HTTP 500 with XML content:
```xml
<msg type="ERROR">Error starting: name 'List' is not defined</msg>
```
The browser frontend in `scenario_builder.js` executed `r.json()`, which threw `SyntaxError: Unexpected token '<', "<msg type="...` because the response was XML rather than JSON.

---

## 3. Root Cause

1. **Missing Typing Import in `datablaster_rest.py`:**
   At line 25 of `netspout/bin/datablaster_rest.py`, the import statement was:
   ```python
   from typing import Dict, Any, Tuple, Optional
   ```
   At line 128, function `resolve_hec_urls` had the signature:
   ```python
   def resolve_hec_urls(hec_url: str) -> List[str]:
   ```
   Because `List` was not imported from `typing`, Python 3.9 evaluated the type annotation at function definition time during module load, raising `NameError: name 'List' is not defined`.
2. **Missing `Any` in `graph_engine.py`:**
   In both `netspout/bin/graph_engine.py` and `backend/app/graph_engine.py`, type annotations used `Any` (e.g. `Dict[str, Any]`), but line 9 only imported `from typing import List, Dict, Set, Optional, Tuple`. This caused secondary `NameError: name 'Any' is not defined`.
3. **Module Resolution Divergence (`from app.` vs flat `bin/`):**
   `netspout/bin/graph_engine.py`, `netspout/bin/log_engine.py`, and `netspout/bin/scenario_runner.py` previously attempted direct imports from `app.models` and `app.graph_engine`. In the Splunk runtime app environment, the directory is flat under `bin/`, so `import app` raised `ModuleNotFoundError: No module named 'app'`.

---

## 4. Exact Repair

All changes were narrowly scoped to restore runtime stability without architectural redesign:

1. **`netspout/bin/datablaster_rest.py` (Line 25):**
   ```python
   # Before:
   from typing import Dict, Any, Tuple, Optional
   # After:
   from typing import Dict, List, Any, Tuple, Optional
   ```
2. **`netspout/bin/graph_engine.py` & `backend/app/graph_engine.py`:**
   Added `Any` to `from typing import ...` and added robust `try / except ImportError` fallback import logic for `models` and `gnmi_engine.yang_store`.
3. **`netspout/bin/log_engine.py`:**
   Added `try / except ImportError` fallback:
   ```python
   try:
       from app.models import LogEntry, Node, NodeType
   except ImportError:
       from models import LogEntry, Node, NodeType
   ```
4. **`netspout/bin/scenario_runner.py`:**
   Added `from typing import List, Dict, Optional, Tuple` and `try / except ImportError` fallback for `models`, `graph_engine`, `log_engine`, and `telemetry_dispatcher`.
5. **Splunk Container Synchronization:**
   The repaired modules were synchronized into `/opt/splunk/etc/apps/netspout/bin/` and `/opt/splunk/etc/apps/TA-network-data-blaster/bin/` in the running container.

---

## 5. Models Divergence Analysis

Prior to modifying `netspout/bin/models.py`, a comprehensive semantic comparison was conducted against `backend/app/models.py`:

* **Total Classes:** Both files define all 16 core classes and enums (`NodeType`, `ScenarioType`, `SecurityZoneType`, `ZoneAnnotation`, `NetworkInterface`, `NodeHardware`, `TelemetryTransportConfig`, `NodePowerState`, `Node`, `Edge`, `SimulationEvent`, `LogEntry`, `TopologyState`, `OpenConfigSubscriptionMode`, `FaultScenarioType`, `FaultInjectionRequest`, `FaultEventRecord`, `FaultRecoveryRequest`, `SNMPTrapEvent`).
* **Classes Unique to Backend:** None.
* **Classes Unique to Splunk:** None.
* **Enum Divergence in `NodeType`:**
  * Backend had 6 additional types: `storage_san`, `storage_nas`, `vpn_gateway`, `cloud_transit`, `iot_sensor`, `wlc_controller`.
  * Splunk version was missing these 6 types.
* **Enum Divergence in `ScenarioType`:**
  * Backend had 18 additional scenario types covering 11 network architectures (`arch_pan_iot_mesh`, `arch_lan_campus_access`, `arch_wlan_meraki_catalyst`, `arch_can_multi_building`, `arch_man_carrier_ring`, `arch_wan_global_backbone`, `arch_san_fibre_channel`, `arch_nas_storage_cluster`, `arch_vpn_remote_workforce`, `arch_epn_isolated_intranet`, `arch_gan_subsea_cloud`) and 7 specialized enterprise/service provider topologies.
  * Splunk version lacked these enum values.
* **Field Divergence in `NodeHardware`:**
  * Backend had 20 specific KPI telemetry fields corresponding to the 4 NOC/SOC operational dimensions (bandwidth, throughput, latency, jitter, packet loss, uptime, cpu, memory, temp, psu, ups, routing table, bgp prefixes, route flaps, config drift, dhcp exhaustion, traffic spike, unauthorized attempts, firewall drops, threat severity).
  * Splunk version lacked these 20 fields.
* **Splunk-Specific Behavior Preserved:**
  * `ZoneAnnotation.zone_type: SecurityZoneType = SecurityZoneType.INTERNAL_TRUST` was preserved as the default in `netspout/bin/models.py`.

---

## 6. Schemas Synchronized

To ensure full schema compatibility without performing an unauthorized blind overwrite:

1. Added the 6 missing enum values to `netspout/bin/models.py:NodeType`.
2. Added the 18 missing enum values to `netspout/bin/models.py:ScenarioType`.
3. Added the 20 KPI dimension fields with default values to `netspout/bin/models.py:NodeHardware`.
4. Maintained default value parity and preserved Splunk-specific zone defaults.

---

## 7. Runtime Execution Trace

The live execution flow from Splunk Web to HEC was verified:

```
[Splunk Web UI] (Scenario Builder / Onboarding)
       │  HTTP POST /splunkd/__raw/services/datablaster/execute
       ▼
[splunkd REST Server] (port 8800/8889)
       │  Dispatches to Registered Persistent REST Application
       ▼
[DataBlasterRestHandler.handle()] (netspout/bin/datablaster_rest.py)
       │  Parses action, scenario, sourcetype, token, hec url
       ├─────────────────────────────────┬─────────────────────────────────┐
       ▼ (action == "onboard_sample")    ▼ (action == "start")             ▼ (action == "status")
[Sample / OpenConfig MDT Handler] [start_simulation()]              [get_current_status()]
       │                                 │                                 │
       ▼                                 ▼                                 ▼
[cisco_sample_provider /          [subprocess.Popen]                [PID file & proc check]
 gnmi_engine RFC 7951 Generator]   (bin/run_simulation.py)                 │
       │                                 │                                 ▼
       ▼                                 ▼                          Returns JSON status
[test_hec_connection() &          [Events generated & streamed]
 direct HEC POST]                        │
       │                                 ▼
       ▼                          [HEC / Metric Store]
[Splunk HEC Endpoint]
 (https://127.0.0.1:8888/services/collector)
       │
       ▼  HTTP 200 {"text":"Success","code":0}
[Splunk Web UI receives Clean JSON Response]
```

---

## 8. OpenConfig / MDT Validation

* **Engine:** `netspout/bin/gnmi_engine.py` (and container equivalent) was validated.
* **Compliance:** Implements strict RFC 7951 JSON-IETF formatting across 4 OpenConfig YANG trees:
  1. `openconfig-interfaces:interfaces` (`/interfaces/interface/state/counters`)
  2. `openconfig-platform:components` (`/components/component/state` for CPU and memory)
  3. `openconfig-network-instance:network-instances` (`/protocols/protocol/bgp`)
  4. `openconfig-system:system` (`/system/state`)
* **Live Ingestion Verification:**
  * Sample probe emitted for `cisco:mdt:grpc` into index `cisco_mdt_metrics`.
  * HEC endpoint returned HTTP 200 `{"text":"Success","code":0}`.
  * Verified metric indexing in `cisco_mdt_metrics`.

---

## 9. Continuous Streaming Validation

The continuous streaming lifecycle was exercised directly through the REST handler:

1. **Initial State:** `action: status` returned `running: False`, `pid: null`.
2. **Start Invocation:** `action: start` with scenario `scenario_acme_full_network_topology.yml` spawned background process under active PID.
3. **Duplicate Prevention:** A second `action: start` was issued while the simulation was running. The handler returned:
   ```json
   {
     "status": "warning",
     "message": "Simulation already running under PID 524417. Stop it first.",
     "pid": 524417
   }
   ```
   No duplicate processes or runaway threads were spawned.
4. **Stop Invocation:** `action: stop` issued `SIGTERM` followed by PID verification and cleanup. Returned `status: success, message: Terminated process 524417`.
5. **Post-Stop State:** `action: status` confirmed `running: False`.

---

## 10. Splunk Validation

* **Classification:** **LIVE_VALIDATED**
* **Splunk Environment:**
  * Container: `splunk-network-data-blaster`
  * Splunk Version: 10.2
  * Splunk Web: `http://localhost:8800`
  * Splunk HEC: `https://127.0.0.1:8888`
  * Splunkd REST: `https://localhost:8889`
* **Evidence:**
  * REST endpoint `/services/datablaster/execute` responds with HTTP 200 JSON.
  * Live REST probe verified: `running=False` reported via authenticated splunkd probe.
  * Metric event delivery confirmed with HEC return code 0.

---

## 11. Test Results Before & After

| Test Suite | Before Fix | After Fix | Delta |
|---|---|---|---|
| Comprehensive Test Suite (`tests/run_comprehensive_test_suite.py`) | 60 Passed / 2 Failed / 0 Skipped | 60 Passed / 2 Failed / 0 Skipped | No regression (0) |
| Gate 1 Targeted Tests (`tests/test_gate1_runtime.py`) | N/A (did not exist) | 6 Passed / 0 Failed / 0 Skipped | +6 Passing Tests |

*Note on Pre-existing Failures in Comprehensive Suite:*
The two failing tests are legacy structural checks documented in Gate 0:
1. `Suite 1 :: Top Navigation 8 Exact Tabs` (default.xml has 7 active tabs).
2. `Suite 3 :: CSS Theme Bundle Compiled` (Vite compiles CSS inline into the JS bundle, leaving 0 standalone `.css` chunks in `dist/assets`).
Per Gate 1 instructions, these existing tests were not weakened or deleted.

---

## 12. Regression Tests Added

Added file: `tests/test_gate1_runtime.py` with 6 dedicated test cases:

1. `test_01_def01_datablaster_rest_import`: Verifies `datablaster_rest.py` imports cleanly, resolves `List` and typing symbols without `NameError`, and checks `resolve_hec_urls` functionality.
2. `test_02_all_bin_modules_importability`: Verifies all 10 core modules in `netspout/bin/` import without `NameError`, `ImportError`, or `SyntaxError`.
3. `test_03_models_schema_synchronization`: Validates synchronized `NodeType`, `ScenarioType`, and all 20 `NodeHardware` KPI fields.
4. `test_04_openconfig_mdt_generation`: Validates RFC 7951 OpenConfig YANG tree structure and sample metric generation.
5. `test_05_continuous_streaming_lifecycle`: Validates status query, duplicate start rejection, and process termination.
6. `test_06_live_splunk_container_rest_probe`: Validates live HTTP response from Splunk container REST handler on `localhost:8889`.

---

## 13. Files Changed

```text
modified:   backend/app/graph_engine.py
modified:   netspout/bin/datablaster_rest.py
modified:   netspout/bin/graph_engine.py
modified:   netspout/bin/log_engine.py
modified:   netspout/bin/models.py
modified:   netspout/bin/scenario_runner.py
untracked:  tests/test_gate1_runtime.py
untracked:  docs/architecture/NETSPOUT_GATE_1_RUNTIME_STABILIZATION.md
```

Summary of line changes: 6 files modified, 117 insertions(+), 40 deletions(-).

---

## 14. Unresolved Defects (Deferred to Gate 2+)

1. **Directory Duplication (`backend/app` vs `netspout/bin`):** 14 modules exist in both directories with slight syntactic differences. Consolidation is reserved for Gate 2.
2. **Dual Splunk App Stanzas in Container:** The Splunk container has both `/opt/splunk/etc/apps/netspout` and legacy `/opt/splunk/etc/apps/TA-network-data-blaster`. Both match `/datablaster/execute`. Unification/symlinking is reserved for Gate 2.
3. **SimpleXML vs React UI Migration:** Seven SimpleXML views remain active. Migration or embedding decision is deferred.
4. **Standalone Port 8081 Daemon vs Embedded Splunk Backend:** Decoupling or single-port consolidation is deferred.

---

## 15. Rollback Instructions

To return the NetSpout repository to its exact pre-Gate-1 state:

```bash
cd /Users/mahamudc/Documents/NetSpout
git checkout HEAD -- backend/app/graph_engine.py netspout/bin/datablaster_rest.py netspout/bin/graph_engine.py netspout/bin/log_engine.py netspout/bin/models.py netspout/bin/scenario_runner.py
rm -f tests/test_gate1_runtime.py
rm -f docs/architecture/NETSPOUT_GATE_1_RUNTIME_STABILIZATION.md
```

To rollback the running Splunk container:
```bash
/Users/mahamudc/.docker/bin/docker restart splunk-network-data-blaster
```

---

## 16. Gate 2 Recommendation

Gate 1 has successfully stabilized the P0 runtime defects, eliminated the REST XML error in Scenario Builder, synchronized schema models, and validated continuous streaming and OpenConfig MDT generation across both the local host and the live Splunk container. Gate 2 should proceed with **Source-of-Truth Consolidation**, establishing a single authoritative Python package for NetSpout engine logic (eliminating the divergence between `backend/app/` and `netspout/bin/`) and deduplicating the container app stanzas (`netspout` vs `TA-network-data-blaster`) while maintaining backward compatibility with both Splunk Web and the React canvas.
