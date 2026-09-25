# NETSPOUT INDEPENDENT PRODUCT ACCEPTANCE REPORT (RE-TEST)
## GOLDEN PATH 03 — DATACENTER FABRIC ACI INGRESS MICROBURST TRAFFIC

**Evaluation Date:** 2026-09-25  
**Product Version:** NetSpout Gate 8 Unified Evidence Discovery Baseline  
**Evaluator Persona:** Data Center / Splunk Network Operations Engineer  
**User Goal:** *"I need to demonstrate a short-lived datacenter congestion/microburst problem in Splunk, but I don't have an ACI/Nexus fabric."*  
**Prior Determination:** PASS WITH FRICTION (`GP03-P2-001`, 10/14 evidence discrepancy in Gate 7)  
**New Acceptance Determination:** **PASS (100% UNIFIED OBSERVATION & METRIC HARMONIZATION)**  
**Maturity Recommendation:** **`GOLDEN_PATH_CERTIFIED`**  

---

## 1. Executive Summary & Defect GP03-P2-001 Closure

During Gate 7 independent acceptance, the `cisco_aci_microburst` scenario demonstrated flawless temporal progression, topology fidelity, and contract rule validation. However, acceptance friction **`GP03-P2-001`** occurred because the user-facing Splunk evidence path only searched the event log index (`index=idx_network_ops`), exposing 10 of 14 events (71.4% completeness) while the 4 MDT streaming telemetry events required developer knowledge to query via `| mstats` in `cisco_mdt_metrics`.

In Gate 8, **Unified Evidence Discovery & Metric Harmonization** was implemented, deployed, and tested against live Splunk Enterprise 10.2.7. 

### Gate 8 Evidence Invariant Verification

41976\text{GENERATED (14)} = \text{DISPATCHED (14)} = \text{OBSERVED (14)} = \text{VALIDATED (PASS)}41976

* **Generated:** **14 events** produced by the multi-phase engine (10 syslog/health records + 4 MDT streaming metric records).
* **Dispatched:** **14 events** transmitted over Splunk HEC (`dispatch_succeeded: 14`, `dispatch_failed: 0`, HTTP 200 acknowledgments).
* **Observed:** **14 events** confirmed across both storage destinations via Splunk REST API:
  * **10 event logs** in `idx_network_ops` via `search index=idx_network_ops netspout_run_id="..."` (Status: PASS).
  * **4 metric events** in `cisco_mdt_metrics` via `| mstats count where index=cisco_mdt_metrics metric_name=* AND netspout_run_id="..."` (Status: PASS).
* **Observation Completeness:** **100.0% (14 / 14 events observed across both event and metric stores)**.
* **Validated:** **4 of 4 contract validation rules passed** in the NetSpout Validation Engine (`aci-val-01`, `aci-val-02`, `aci-val-03`, `aci-val-04`).

| Evaluation Dimension | Gate 7 Result | Gate 8 Retest Result | Notes |
| :--- | :--- | :--- | :--- |
| **Product Discovery** | PASS | **PASS** | Discoverable via "Data Center" category pill |
| **Preview Fidelity** | PASS | **PASS** | Nexus 9336 Leaf topology, ASIC drop metrics, and ACI fabric score previewed |
| **Temporal Progression** | PASS | **PASS** | Coherent progression: baseline (<2MB) → incast (>25MB) → drops (2,450) → drain (<2MB) |
| **Splunk Observation** | PASS WITH FRICTION (10/14) | **PASS (14/14 = 100%)** | Full multi-store observation across event index and metric store |
| **Observation Completeness** | 71.4% (primary index only) | **100.0% (Unified)** | Both log index and metric index dynamically queried and reported |
| **Query Harmonization** | NO (Event search only) | **YES** | Dedicated SPL Search and Metric `| mstats` copy buttons & deep links |
| **Validation Engine** | PASS (4/4 rules) | **PASS (4/4 rules)** | Rules `aci-val-01` through `aci-val-04` pass |
| **Developer Knowledge Required** | YES | **NO** | Automated discovery of storage destinations and copyable queries |
| **Determination** | PASS WITH FRICTION | **PASS (ZERO FRICTION)** | Defect `GP03-P2-001` fully closed |
| **Maturity Recommendation** | REMAIN_E2E_VALIDATED | **GOLDEN_PATH_CERTIFIED** | Ready for full production certification |

---

## 2. Test Environment & Live Retest Identity

| Component | Value | Notes |
| :--- | :--- | :--- |
| **Test Execution Engine** | NetSpout Gate 8 Live Telemetry Dispatcher | Live Splunk REST & HEC validation |
| **Splunk Enterprise** | Version 10.2.7 | Docker container `splunk-network-data-blaster` |
| **Splunk Web** | `http://localhost:8800` | Search & Reporting App |
| **Splunk HEC** | `https://127.0.0.1:8888/services/collector` | Token `00000000-0000-0000-0000-000000000000` |
| **Target Event Index** | `idx_network_ops` | Primary event log index |
| **Target Metric Store** | `cisco_mdt_metrics` | Native Splunk metric index (`datatype = metric`) |
| **NetSpout Daemon** | FastAPI 0.115 on `http://localhost:8081` | Background task |
| **Run Correlation ID** | `NS-20260925-55343b43` | Verified live run correlation stamp |
| **Target Scenario** | `cisco_aci_microburst` | *Data Center Fabric ACI Ingress Microburst Traffic* |
| **Execution Duration** | 1.0s (Accelerated mode) | Real-time rate: 14.0 EPS |

---

## 3. Storage Destination Discovery & Query Verification

### Destination 1: Splunk Event Index (`idx_network_ops`)
* **Role:** `REQUIRED` (Primary Event Log Index)
* **Telemetry Type:** `EVENT`
* **Target Index:** `idx_network_ops`
* **Query Mechanism:** `SPL_SEARCH`
* **Expected Count:** 10
* **Observed Count:** 10
* **Status:** `PASS`
* **Query:**
  ```spl
  search index=idx_network_ops netspout_run_id="NS-20260925-55343b43"
  ```
* **Observed Sourcetypes:**
  * 5x `cisco:dc:nexus9k:syslog`
  * 5x `cisco:dc:aci:health`

### Destination 2: Splunk Metric Store (`cisco_mdt_metrics`)
* **Role:** `SUPPORTING` (High-frequency Streaming Telemetry)
* **Telemetry Type:** `METRIC`
* **Target Index:** `cisco_mdt_metrics`
* **Query Mechanism:** `MSTATS`
* **Expected Count:** 4
* **Observed Count:** 4
* **Status:** `PASS`
* **Query:**
  ```spl
  | mstats count where index=cisco_mdt_metrics metric_name=* AND netspout_run_id="NS-20260925-55343b43"
  ```
* **Observed Sourcetypes:**
  * 4x `cisco:ios:mdt:metric` (`metric_name:queue_depth`, `metric_name:peak_buffer_pct`)

---

## 4. Contract Validation Results

All 4 scenario validation rules executed and passed in the Validation Engine:

1. **`aci-val-01`**: *ACI Health Telemetry Emitted* (`cisco:dc:aci:health` count $\ge 1$) → **PASS** (Observed: 5 events).
2. **`aci-val-02`**: *Degradation Status Logged* (`status=degraded`) → **PASS** (Observed: 2 events with degraded status during FAULT and PROPAGATE phases).
3. **`aci-val-03`**: *Nexus 9K ASIC Congestion Logged* (`cisco:dc:nexus9k:syslog` count $\ge 1$) → **PASS** (Observed: 5 events).
4. **`aci-val-04`**: *Health Restored to Nominal* (`status=restored`) → **PASS** (Observed: 2 events with restored status during RECOVER phase).

---

## 5. Closure of Acceptance Defect GP03-P2-001

| Defect ID | Severity | Scenario | Original Finding | Resolution in Gate 8 |
| :--- | :--- | :--- | :--- | :--- |
| **GP03-P2-001** | **P2** | `cisco_aci_microburst` | Dual-index routing sends 4 MDT events to `cisco_mdt_metrics` while UI search deep link queries only `index=idx_network_ops`. The user sees 10/14 events (71.4%) and requires internal developer knowledge to discover the 4 metric events via `| mstats`. | **RESOLVED**: Dynamic evidence discovery identifies both destinations. Step 4 and Step 5 provide dedicated copyable queries and deep links for both log search and metric `| mstats`. Observation completeness displays 14/14 (100.0%). |

---

## 6. Final Recommendation

With defect **`GP03-P2-001`** fully resolved and verified against live Splunk Enterprise:
* The user experience for Golden Path 03 is seamless, self-guided, and requires zero developer workarounds.
* True native Splunk metric semantics are preserved without compromise.
* Observation completeness is 100.0% (14/14 records verified across event and metric stores).
* Contract validation rules pass 100% (4/4 rules).

**Determination:** **PASS — ZERO FRICTION**  
**Recommendation:** **PROMOTE `cisco_aci_microburst` (GP03) TO `GOLDEN_PATH_CERTIFIED`**.
