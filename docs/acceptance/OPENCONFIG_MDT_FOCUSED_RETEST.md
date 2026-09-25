# OpenConfig MDT Streaming Focused Retest Record (Gate 9.5)

## 1. Context & Purpose

During Wave 1 Independent Product Acceptance, `openconfig_mdt_streaming` received a **PASS WITH FRICTION** rating (`W1-P2-001`) due to ambiguity regarding whether the telemetry was streamed over a native gRPC/gNMI dial-out session or modeled via Splunk HEC.

Gate 9.5 delivered focused UX clarifications ensuring telemetry semantics are transparent before scenario execution:
1. **Telemetry Model:** `OpenConfig / MDT`
2. **Transport Protocol:** `Splunk HEC`
3. **Splunk Storage Destination:** `Metrics Index (cisco_mdt_metrics) + Event Index (idx_network_ops)`
4. **Fidelity Badge:** `MODELED PAYLOAD` (allowed states: `NATIVE TRANSPORT`, `MODELED PAYLOAD`, `SYNTHETIC`)
5. **Educational Callout Note:** *"NetSpout models OpenConfig/MDT telemetry fields and metric behavior. In this scenario the telemetry is delivered to Splunk through HEC rather than a native gNMI/gRPC session."*

This retest document verifies the end-to-end execution of `openconfig_mdt_streaming` in the live Splunk environment with the updated UI.

---

## 2. Telemetry Semantics Verification (Pre-Execution Audit)

Before triggering execution, the UI was inspected via Chrome Developer Protocol (CDP) at `http://localhost:8800/en-US/app/netspout/netspout_canvas`:

| Semantic Dimension | Verified UI State | Status |
| :--- | :--- | :--- |
| **Telemetry Model** | Displayed in Card Advanced Details and Preview Card as `"OpenConfig / MDT"` | **CONFIRMED** |
| **Transport Protocol** | Displayed as `"Splunk HEC"` (never claiming native gRPC dial-out) | **CONFIRMED** |
| **Splunk Storage** | Displayed as `"Metrics Index (cisco_mdt_metrics) + Event Index (idx_network_ops)"` | **CONFIRMED** |
| **Fidelity Badge** | Styled violet badge displaying `"MODELED PAYLOAD"` on Step 1 card and Step 2 preview | **CONFIRMED** |
| **Educational Callout** | Dedicated informational box explaining modeled payload delivered via HEC rather than native gNMI/gRPC | **CONFIRMED** |
| **Topology Description** | `zone-oc-1` description displays `"OpenConfig YANG streaming routers with modeled telemetry payload"` | **CONFIRMED** |

---

## 3. End-to-End Live Execution Results

### Run Metadata
- **Run ID:** `NS-20260925-3535dbbf`
- **Scenario ID:** `openconfig_mdt_streaming`
- **Catalog Maturity at Retest:** `GOLDEN_PATH_CERTIFIED`
- **Seed:** `200`
- **Pipeline Transport:** Splunk HEC (`https://127.0.0.1:8888/services/collector`) with self-signed TLS allowed

### Observability & Dispatch Accounting
| Metric | Planned / Expected | Actual Observed | Result |
| :--- | :--- | :--- | :--- |
| **Total Generated Records** | 12 | 12 | **100% MATCH** |
| **HEC Dispatch Succeeded** | 12 | 12 | **100% MATCH** |
| **HEC Dispatch Failed** | 0 | 0 | **0 FAILURES** |
| **Event Index Observed (`idx_network_ops`)** | 3 | 3 | **100% OBSERVED** |
| **Metrics Index Observed (`cisco_mdt_metrics`)** | 9 | 9 | **100% OBSERVED** |
| **Total Observed Records in Splunk** | 12 | 12 | **100% COMPLETENESS** |

### Automated Contract Validation Rules
| Rule ID | Rule Name | Target / Field | Condition | Status |
| :--- | :--- | :--- | :--- | :--- |
| `oc-val-01` | MDT Telemetry Stream Emitted | `cisco:ios:mdt` | count >= 1 | **PASS** |
| `oc-val-02` | Core Interface Congestion Detected | `status` | `degraded` | **PASS** |
| `oc-val-03` | MDT Telemetry Streaming Active | `action` | `allowed` | **PASS** |
| `oc-val-04` | Core Interface Restored to Nominal | `status` | `restored` | **PASS** |
| **Overall Validation** | **All Rules Satisfied** | **End-to-End** | **100% PASS** | **PASS** |

---

## 4. Photographic Evidence

All evidence screenshots were automatically captured during the live retest:

1. **Step 1: Use Case Selection Card with Fidelity Badge and Expanded Details**  
   ![Step 1 Card](/Users/mahamudc/Documents/NetSpout/docs/acceptance/images/openconfig_retest_01_card.png)

2. **Step 2: Preview Step with Telemetry Semantics & Architecture Card and Educational Callout**  
   ![Step 2 Semantics Preview](/Users/mahamudc/Documents/NetSpout/docs/acceptance/images/openconfig_retest_02_preview_semantics.png)

3. **Step 3: Pipeline Connection Verification**  
   ![Step 3 Connection](/Users/mahamudc/Documents/NetSpout/docs/acceptance/images/openconfig_retest_03_connection.png)

4. **Step 4: Scenario Execution & Multi-Phase Progression**  
   ![Step 4 Execution](/Users/mahamudc/Documents/NetSpout/docs/acceptance/images/openconfig_retest_04_execution.png)

5. **Splunk Search App: Event Telemetry in `idx_network_ops`**  
   ![Splunk Events](/Users/mahamudc/Documents/NetSpout/docs/acceptance/images/openconfig_retest_05_splunk_events.png)

6. **Splunk Search App: Metric Telemetry in `cisco_mdt_metrics` via `| mstats`**  
   ![Splunk Metrics](/Users/mahamudc/Documents/NetSpout/docs/acceptance/images/openconfig_retest_06_splunk_metrics.png)

7. **Step 5: Automated Evidence & Proof Evaluation**  
   ![Step 5 Validation](/Users/mahamudc/Documents/NetSpout/docs/acceptance/images/openconfig_retest_07_validation.png)

---

## 5. Resolution of Friction Point W1-P2-001

- **Defect ID:** `W1-P2-001` (OpenConfig Telemetry Ambiguity)
- **Root Cause:** Absence of pre-flight architectural disclosure specifying payload model vs transport protocol vs index destination.
- **Resolution:**
  1. Core contracts and canonical catalog enriched with explicit telemetry semantics fields.
  2. UI Step 1 (Choose) and Step 2 (Preview) prominently display `MODELED PAYLOAD`, `OpenConfig / MDT`, `Splunk HEC`, dual-destination indexing, and educational guidance.
  3. Topology preset descriptions updated to avoid ambiguous native gRPC streaming claims.
  4. Comprehensive test suite validates metadata integrity, absence of native gRPC claims, and zero regressions across Golden Paths.
- **Status:** **RESOLVED & CERTIFIED**.

---

## 6. Promotion Recommendation

With `W1-P2-001` resolved and verified under live end-to-end testing:
- **`openconfig_mdt_streaming`** is formally promoted from `E2E_VALIDATED` to **`GOLDEN_PATH_CERTIFIED`**.
- All 3 evaluated Wave 1 scenarios (`mixed_sase_degradation`, `sql_injection`, and `openconfig_mdt_streaming`) now hold **`GOLDEN_PATH_CERTIFIED`** maturity.
- Platform is ready for **Wave 2**.
