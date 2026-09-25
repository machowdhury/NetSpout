# NETSPOUT GATE 8: UNIFIED EVIDENCE DISCOVERY & METRIC HARMONIZATION

**Author**: Mahamudul Chowdhury (`machowdhury@yahoo.com`)  
**Gate**: Gate 8 — Unified Evidence Discovery & Metric Harmonization  
**Status**: COMPLETE  
**Repository**: `machowdhury/NetSpout`  
**Date**: September 25, 2026  

---

## 1. Executive Summary & Defect Resolution

NetSpout Gate 8 resolves the primary acceptance friction identified during the Golden Paths 02–04 Independent Product Acceptance: **`GP03-P2-001`**.

### The Friction in Gate 7
During Golden Path 03 (`cisco_aci_microburst`), NetSpout generated **14 distinct telemetry events**:
* **10 log/syslog events** dispatched to the primary event index `idx_network_ops` (Cisco Nexus 9K ASIC syslog and Cisco ACI APIC fabric health events).
* **4 Model-Driven Telemetry (MDT) metric events** routed directly to the native metric index `cisco_mdt_metrics` (Cisco NX-OS buffer queue depth and peak utilization metrics).

In Gate 7, the user-facing Splunk evidence discovery path was hardcoded to query only `index=idx_network_ops`. As a result:
1. The UI reported only **10/14 (71.4%)** observed events.
2. The user required developer-level knowledge of Splunk internals to construct an `| mstats` query against `cisco_mdt_metrics` to verify that the remaining 4 events had indeed been ingested into the metrics store.
3. Observation completeness was conflated with contract rule validation.

### Gate 8 Resolution
Gate 8 introduces **Unified Evidence Discovery & Metric Harmonization**:
* **Dynamic Multi-Destination Discovery**: The platform dynamically discovers all storage destinations involved in a simulation run based on emitted telemetry, transport configuration, and sourcetype routing.
* **Preservation of True Splunk Semantics**: Native Splunk metric indexes (`datatype = metric`, HEC `"event": "metric"`, `cisco_mdt_metrics`) and event indexes (`idx_network_ops`) are strictly preserved. Metrics are queried using native `| mstats` syntax, while log events are queried using standard `search index=...`.
* **Decoupled Completeness from Contract Validation**: Telemetry observation completeness (14/14 = 100%) is tracked independently from semantic contract validation rules (`aci-val-01` through `aci-val-04`).
* **Harmonized User Experience**: Both Step 4 (Run) and Step 5 (Prove) in the Five-Step Workflow expose dedicated query copy buttons and Splunk search deep links for both log searches and metric `| mstats` searches.

---

## 2. Native Splunk Storage Model & Architectural Integrity

NetSpout strictly rejects any synthetic anti-patterns, such as flattening streaming metrics into fake log strings or routing metric data into event indexes merely to make unified querying easier.

```
                                  NetSpout Scenario Run
                                            │
                     ┌──────────────────────┴──────────────────────┐
                     ▼                                             ▼
          Event Telemetry (10 logs)                     Metric Telemetry (4 MDT)
    (cisco:dc:nexus9k:syslog, cisco:dc:aci:health)         (cisco:ios:mdt:metric)
                     │                                             │
                     ▼                                             ▼
            HEC Event Pipeline                            HEC Metric Pipeline
          "event": "<raw_log>"                            "event": "metric"
          "index": "idx_network_ops"                      "index": "cisco_mdt_metrics"
          "fields": {correlation}                         "fields": {metric_name:*, correlation}
                     │                                             │
                     ▼                                             ▼
          Splunk Event Index                           Splunk Metric Store
          (idx_network_ops)                             (cisco_mdt_metrics)
                     │                                             │
                     ▼                                             ▼
           SPL Search Query                              SPL | mstats Query
     search index=idx_network_ops ...             | mstats count where index=cisco_mdt_metrics ...
```

### 2.1 Native Metric Payload Formatting
When dispatching streaming metrics (such as `cisco:ios:mdt`), NetSpout constructs RFC-compliant Splunk HEC metric payloads:
```json
{
  "time": 1758807085.123,
  "event": "metric",
  "host": "leaf-101",
  "source": "cisco:ios:mdt",
  "sourcetype": "cisco:ios:mdt:metric",
  "index": "cisco_mdt_metrics",
  "fields": {
    "metric_name:queue_depth": 26500000.0,
    "_value": 26500000.0,
    "device": "leaf-101",
    "vendor": "cisco",
    "status": "degraded",
    "action": "alerted",
    "netspout_run_id": "NS-20260925-55343b43",
    "netspout_scenario_id": "cisco_aci_microburst",
    "netspout_phase": "FAULT"
  }
}
```

### 2.2 Dual-Query Mechanism Harmonization
* **Event Index Query**:
  ```spl
  search index=idx_network_ops netspout_run_id="NS-20260925-55343b43"
  ```
* **Metric Index Query**:
  ```spl
  | mstats count where index=cisco_mdt_metrics metric_name=* AND netspout_run_id="NS-20260925-55343b43"
  ```

---

## 3. Dynamic Multi-Destination Evidence Discovery Engine

The discovery engine (`ScenarioRunner.get_run_evidence`) dynamically analyzes the logs emitted by a run to discover every unique destination:

### 3.1 Destination Typing and Role Assignment
Each discovered destination is instantiated as an `EvidenceDestination`:
* `destination_id`: Unique identifier (e.g. `dest-event-idx_network_ops`, `dest-metric-cisco_mdt_metrics`).
* `telemetry_type`: `TelemetryType.EVENT` or `TelemetryType.METRIC`.
* `target_index`: Splunk index name (`idx_network_ops`, `cisco_mdt_metrics`).
* `query_mechanism`: `QueryMechanism.SPL_SEARCH` or `QueryMechanism.MSTATS`.
* `role`: `EvidenceRole.REQUIRED` (primary event log indexes) or `EvidenceRole.SUPPORTING` (specialized metric indexes).
* `expected_count`: Exact count of generated events routed to this specific destination.
* `observed_count`: Number of records confirmed via Splunk REST API.

### 3.2 Observation Completeness Formula
Observation completeness is computed across all discovered storage destinations:

41950\text{Observation Completeness (\%)} = \frac{\sum \text{Observed Events} + \sum \text{Observed Metrics}}{\text{Total Telemetry Generated}} \times 100\%41950

* **Status Lifecycle**:
  * `PENDING`: 0 records observed across all destinations.
  * `PARTIAL`: At least 1 record observed, but total observed is less than total generated.
  * `COMPLETE`: Total observed equals or exceeds total generated (\%$).
  * `ERROR`: REST query execution failure against Splunkd.

### 3.3 Decoupled Evaluation Invariant
1. Contract validation rules evaluate scenario-specific operational logic (e.g., whether buffer drops were logged, whether ISE quarantine occurred).
2. Observation completeness tracks ingest and storage pipeline health.
3. Destination validation cannot report `PASS` unless at least one required evidence record is physically observed in the destination index.

---

## 4. Full API & Data Model Specification

### 4.1 Data Models (`src/netspout_core/models.py`)
```python
class TelemetryType(str, Enum):
    EVENT = "EVENT"
    METRIC = "METRIC"

class QueryMechanism(str, Enum):
    SPL_SEARCH = "SPL_SEARCH"
    MSTATS = "MSTATS"

class EvidenceRole(str, Enum):
    REQUIRED = "REQUIRED"
    SUPPORTING = "SUPPORTING"

class EvidenceDestination(BaseModel):
    destination_id: str
    name: str
    telemetry_type: TelemetryType
    target_index: str
    query_mechanism: QueryMechanism
    query: str
    expected_count: int = 0
    observed_count: int = 0
    status: str = "PENDING"
    role: EvidenceRole = EvidenceRole.REQUIRED
    sourcetypes: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)

class UnifiedRunEvidence(BaseModel):
    run_id: str
    scenario_id: str
    total_generated: int = 0
    event_generated_count: int = 0
    metric_generated_count: int = 0
    total_observed: int = 0
    event_observed_count: int = 0
    metric_observed_count: int = 0
    observation_completeness_pct: float = 0.0
    observation_status: str = "PENDING"
    required_evidence_satisfied: bool = False
    destinations: List[EvidenceDestination] = Field(default_factory=list)
```

### 4.2 Endpoint: `GET /api/scenarios/runs/{run_id}/observation`
Returns the harmonized multi-store observation summary:
```json
{
  "run_id": "NS-20260925-55343b43",
  "observed_count": 14,
  "observation_status": "VERIFIED",
  "destination_validation": "PASS",
  "event_observed_count": 10,
  "metric_observed_count": 4,
  "observation_completeness_pct": 100.0,
  "destinations": [
    {
      "destination_id": "dest-metric-cisco_mdt_metrics",
      "name": "Splunk Metric Store (cisco_mdt_metrics)",
      "telemetry_type": "METRIC",
      "target_index": "cisco_mdt_metrics",
      "query_mechanism": "MSTATS",
      "query": "| mstats count where index=cisco_mdt_metrics metric_name=* AND netspout_run_id="NS-20260925-55343b43"",
      "expected_count": 4,
      "observed_count": 4,
      "status": "PASS",
      "role": "SUPPORTING",
      "sourcetypes": ["cisco:ios:mdt:metric"],
      "errors": []
    },
    {
      "destination_id": "dest-event-idx_network_ops",
      "name": "Splunk Event Index (idx_network_ops)",
      "telemetry_type": "EVENT",
      "target_index": "idx_network_ops",
      "query_mechanism": "SPL_SEARCH",
      "query": "search index=idx_network_ops netspout_run_id="NS-20260925-55343b43"",
      "expected_count": 10,
      "observed_count": 10,
      "status": "PASS",
      "role": "REQUIRED",
      "sourcetypes": ["cisco:dc:aci:health", "cisco:dc:nexus9k:syslog"],
      "errors": []
    }
  ]
}
```

---

## 5. User Experience Harmonization

### 5.1 Step 4 (Run Phase)
* Direct query preview for both event search (`search index=...`) and metric search (`| mstats ...`).
* One-click clipboard copy for both query types.
* One-click "Open Metric Search in Splunk" deep link alongside the existing event deep link.

### 5.2 Step 5 (Prove Phase)
* **Unified Observation Completeness Card**:
  * Displays Overall Completeness (\%$), Total Observed (/14$), Event Logs (/10$), and Metrics (/4$).
* **Discovered Storage Destinations & Query Harmonization Table**:
  * Lists each discovered destination with its telemetry type badge (`EVENT` or `METRIC`).
  * Shows target index, query mechanism (`SPL_SEARCH` or `MSTATS`), expected vs observed counts, and destination status badge (`PASS`).
  * Provides per-destination query copy and direct Splunk search launch buttons.

---

## 6. Golden Path Status & Scorecard Reconciliation

Following Gate 8 implementation and independent product acceptance:

| Golden Path ID | Scenario Identifier | Domain | Gate 7 Status | Gate 8 Status | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **GP01** | `cisco_sdwan_brownout` | WAN / SD-WAN | `GOLDEN_PATH_CERTIFIED` | `GOLDEN_PATH_CERTIFIED` | Zero defects. Certified baseline. |
| **GP02** | `cisco_campus_rogue` | Campus / Wireless | `E2E_VALIDATED` | `GOLDEN_PATH_CERTIFIED` | Promoted in Gate 8 catalog. Full fidelity pass. |
| **GP03** | `cisco_aci_microburst` | Datacenter / ACI Fabric | `E2E_VALIDATED` (Friction) | `E2E_VALIDATED` (Retested, 100% Pass) | Friction `GP03-P2-001` resolved. Retested with 14/14 observation. Recommended for certification. |
| **GP04** | `mixed_edge_breach` | Multi-Vendor Security | `E2E_VALIDATED` | `GOLDEN_PATH_CERTIFIED` | Promoted in Gate 8 catalog. Full 4-vendor fidelity pass. |

---

## 7. Verification Suite

All 22 Gate 8 test areas in `tests/test_gate8_unified_evidence.py` are passing:
* `test_01_multi_destination_discovery`: Discovers event and metric stores dynamically.
* `test_02_storage_destination_typing`: Validates typing (`EVENT` vs `METRIC`).
* `test_03_destination_role_assignment`: Assigns `REQUIRED` vs `SUPPORTING` roles.
* `test_04_query_mechanism_assignment`: Verifies `SPL_SEARCH` and `MSTATS` assignment.
* `test_05_spl_search_query_generation`: Generates canonical SPL query.
* `test_06_mstats_query_generation`: Generates canonical `| mstats` query.
* `test_07_observation_completeness_calculation`: Verifies completeness percentage calculation.
* `test_08_decoupled_contract_vs_observation`: Ensures contract pass does not depend on observation completeness.
* `test_09_partial_observation_status`: Verifies `PARTIAL` status behavior.
* `test_10_complete_observation_status`: Verifies `COMPLETE` status when all records observed.
* `test_11_failed_observation_status`: Verifies `ERROR` handling.
* `test_12_hec_metric_payload_dimensions`: Verifies `netspout_run_id` and dimension stamping.
* `test_13_metric_extraction_from_raw_log`: Verifies extraction into `metric_name:*` fields.
* `test_14_preservation_of_true_splunk_metric_semantics`: Validates metric index payload compliance.
* `test_15_api_observation_response_structure`: Tests serialization of observation endpoint.
* `test_16_run_manifest_serialization`: Tests Pydantic serialization of extended manifest.
* `test_17_contract_pass_does_not_require_supporting_metrics`: Invariant check.
* `test_18_destination_pass_requires_observed_evidence`: Invariant check.
* `test_19_gp01_evidence_discovery`: GP01 single-destination verification.
* `test_20_gp02_evidence_discovery_certified`: GP02 certification and evidence discovery.
* `test_21_gp03_evidence_discovery_dual_store`: GP03 dual-store evidence discovery (10 events + 4 metrics = 14).
* `test_22_gp04_evidence_discovery_certified`: GP04 certification and evidence discovery.

Additionally, full regression across **all 128 tests** spanning Gates 1 through 8 passed with 100% success.
