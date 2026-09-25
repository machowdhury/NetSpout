# NETSPOUT INDEPENDENT PRODUCT ACCEPTANCE REPORT
## SCENARIO 02 — OPENCONFIG MDT STREAMING & TELEMETRY ASSURANCE

**Evaluation Date:** 2026-09-25  
**Product Version:** NetSpout Gate 9 Baseline (Wave 1 Promoted)  
**Evaluator Persona:** Senior Network Assurance & Observability Architect  
**User Goal:** *"I need realistic streaming network telemetry in Splunk to demonstrate performance monitoring and telemetry assurance, but I don't have routers/switches exporting MDT or gNMI."*  
**Acceptance Determination:** **PASS WITH FRICTION** (Friction: Payload Fidelity vs Native Wire Transport distinction)  
**Catalog Maturity Recommendation:** **`REMAIN_E2E_VALIDATED`**  

---

## 1. Transport Truth: Payload Fidelity vs Native Transport

A fundamental principle of independent product acceptance is establishing **Transport Truth** without marketing exaggeration:

* **What NetSpout Provides:**
  * **High-Fidelity OpenConfig / MDT Payloads:** Telemetry records conform to OpenConfig sensor path structures (e.g. `/interfaces/interface/state/counters`, queue depths, and buffer utilization metrics).
  * **Native Splunk Metric Ingestion:** MDT metrics are transmitted via Splunk HEC using Splunk's native metric payload standard (`"event": "metric"`, `fields: {"metric_name:...": value}`) and stored in a true metric index (`cisco_mdt_metrics`, `datatype = metric`).
  * **True Dual-Store Evidence Discovery:** Event logs (gRPC session lifecycle, buffer watermark alerts) route to the event store (`idx_network_ops`), while streaming measurements route to the metric store (`cisco_mdt_metrics`).
* **What NetSpout Does NOT Claim:**
  * NetSpout does **NOT** establish a native out-of-band gRPC TCP streaming connection or UDP dial-out collector process directly into Splunk's indexer ports.
  * Telemetry is simulated and transported over Splunk HTTP Event Collector (HEC), where it maps cleanly to Splunk metric and event tables.
* **Friction Finding (`W1-P2-001`):** While the product accurately delivers true metric storage semantics, the UI header label "OpenConfig MDT Streaming" could lead a first-time operator to assume native gRPC dial-out collection. A tooltip or descriptor distinguishing *HTTP HEC Metric Ingestion* from *Native gRPC Dial-Out* would enhance transparency.

---

## 2. Discovery Experience

Starting from NetSpout Canvas within Splunk:

* **User-Facing Title:** **`OpenConfig MDT Streaming & Telemetry Assurance`**
* **Category Pill:** **`Service Assurance`**
* **Vendors Displayed:** `Cisco IOS`, `Juniper Junos`, `Arista EOS`, `Cisco Catalyst`
* **Topology Displayed:** `openconfig_core` (Core routing & leaf switching topology)
* **Telemetry Displayed:** `cisco:ios:mdt`, `arista:telemetry:json`, `cisco:ios:syslog`
* **Interactions Required:**
  1. Click category filter pill: `Service Assurance`
  2. Select scenario card: `OpenConfig MDT Streaming & Telemetry Assurance`
  3. Click `Preview Selection`
* **Developer Knowledge Required:** **NO**. Discovered cleanly via the "Service Assurance" category pill.

![OpenConfig MDT Discovery](/docs/acceptance/images/w1_mdt_01_discovery.png)

---

## 3. Preview & Environment Realism

In Step 2 (Preview Selection), the user reviews the multi-vendor telemetry environment:

* **Topology Structure:** Enterprise backbone core containing Cisco 8000 Core routing, Juniper PTX10K PE routers, and Catalyst 9600 distribution leaf switches.
* **Component Participation Breakdown:**
  * **Active Telemetry Producers:**
    1. `Cisco-8000-Core01` (Vendor: Cisco IOS / Cisco MDT, Sourcetype: `cisco:ios:mdt`) — Streams real-time interface queue depth and buffer occupancy metrics.
    2. `Juniper-PTX10K-PE01` (Vendor: Juniper Junos, Sourcetype: `cisco:ios:mdt`) — Streams MPLS transit buffer metrics.
    3. `Catalyst-9600-Leaf` (Vendor: Cisco Catalyst, Sourcetypes: `cisco:ios:syslog`, `cisco:ios:mdt`) — Produces discrete event syslogs and MDT metric watermarks.
  * **Topology Context Only:** Surrounding access interfaces.

![OpenConfig MDT Preview](/docs/acceptance/images/w1_mdt_02_preview.png)

---

## 4. Connection Configuration

In Step 3 (Configure Connection):

* **Event Index:** `idx_network_ops`
* **Metric Store:** `cisco_mdt_metrics`
* **HEC Endpoint:** `https://127.0.0.1:8888/services/collector`
* **Self-Signed TLS:** Enabled
* **Test Connection:** Successful (HTTP 200 acknowledgment).

![OpenConfig MDT Connection](/docs/acceptance/images/w1_mdt_03_connection.png)

---

## 5. Scenario Execution & Runtime Phase Evidence

In Step 4 (Execute & Observe), the scenario executes across 6 distinct phases:

* **Fresh Run Correlation ID:** **`NS-20260925-842ba4ce`**
* **Total Events Generated:** **12** (3 event logs + 9 streaming metrics)
* **Dispatch Succeeded:** **12 / 12 (100% HTTP 200)**
* **Dispatch Failed:** **0**

### 5.1. Baseline Phase
* **Observed State:** Subscription sessions active. Interface ingress counters nominal; queue depth < 1.2MB; buffer utilization < 12%. Catalyst 9600 logs L3 route established.
![OpenConfig MDT Baseline](/docs/acceptance/images/w1_mdt_04_baseline.png)

### 5.2. Fault / Congestion Phase
* **Observed State:** Ingress micro-burst and traffic surge induces interface buffer watermark spike (>80%) and queue depth surge to 11.4MB.
![OpenConfig MDT Fault](/docs/acceptance/images/w1_mdt_05_fault.png)

### 5.3. Propagation Phase
* **Observed State:** Buffer saturation cascades to Juniper PTX10K PE core. Catalyst 9600 emits discrete event syslog alerting on queue watermark threshold breach.
![OpenConfig MDT Propagation](/docs/acceptance/images/w1_mdt_06_propagation.png)

### 5.4. Mitigation Phase
* **Observed State:** Dynamic queue shaping and priority flow control engage; queue occupancy begins shedding.
![OpenConfig MDT Mitigation](/docs/acceptance/images/w1_mdt_07_mitigation.png)

### 5.5. Recovery Phase
* **Observed State:** Buffer equilibrium restored across all nodes; Catalyst 9600 logs normal queue status.
![OpenConfig MDT Recovery](/docs/acceptance/images/w1_mdt_08_recovery.png)

---

## 6. Splunk Observation & Unified Evidence Discovery

In Splunk, NetSpout automatically discovers **both** storage destinations and generates appropriate queries:

### 6.1. Destination 1: Splunk Event Index (`idx_network_ops`)
* **Role:** `REQUIRED` (Event log verification)
* **Telemetry Type:** `EVENT`
* **Observed Count:** **3 / 3 (100.0%)**
* **Query:**
  ```spl
  search index=idx_network_ops netspout_run_id="NS-20260925-842ba4ce"
  ```
* **Observed Sourcetypes:** 3x `cisco:ios:syslog` (Catalyst 9600 routing, watermark alert, and recovery events).

![OpenConfig MDT Event Evidence](/docs/acceptance/images/w1_mdt_09a_splunk_event_evidence.png)

### 6.2. Destination 2: Splunk Metric Store (`cisco_mdt_metrics`)
* **Role:** `SUPPORTING` (Streaming metric assurance)
* **Telemetry Type:** `METRIC`
* **Observed Count:** **9 / 9 (100.0%)**
* **Query:**
  ```spl
  | mstats count where index=cisco_mdt_metrics metric_name=* AND netspout_run_id="NS-20260925-842ba4ce"
  ```
* **Observed Metrics:** `queue_depth`, `buffer_utilization`, `peak_buffer_pct` across Cisco 8000 and Juniper PTX.

![OpenConfig MDT Metric Evidence](/docs/acceptance/images/w1_mdt_09b_splunk_metric_evidence.png)

### Operational Investigation Questions Answered Purely via Evidence:

1. **Which devices produced telemetry?**
   `Cisco-8000-Core01`, `Juniper-PTX10K-PE01`, and `Catalyst-9600-Leaf`.
2. **Which metrics changed?**
   `metric_name:queue_depth` (escalated from ~1.2MB to >11MB) and `metric_name:buffer_utilization` (spiked from 12% to >82%).
3. **What is baseline?**
   Queue depth < 2MB, buffer utilization < 15%.
4. **What abnormal condition occurred?**
   Buffer congestion and queue depth spike across core transit paths.
5. **Which event evidence accompanies metrics?**
   Discrete Cisco IOS syslog events (`cisco:ios:syslog`) documenting route establishment, watermark threshold breach, and recovery.
6. **Did telemetry continue throughout the scenario?**
   Yes. Continuous metric streaming was maintained across all 6 phases.
7. **Did metrics recover?**
   Yes. Queue depth drained back to 1.1MB, and buffer utilization normalized to < 14%.
8. **Where are metrics stored?**
   Splunk native metric index `cisco_mdt_metrics` (`datatype = metric`).
9. **How can the user inspect them in Splunk?**
   Via the copyable `| mstats` query provided automatically in NetSpout Step 4 and Step 5.

---

## 7. Validation Engine Results

In Step 5 (Prove Expected Condition):

* **Observation Completeness:** **100.0% (12 / 12 observed across both event and metric stores)**
* **Destination Status:** **`PASS`**
* **Overall Contract Validation:** **`PASS`**

| Rule ID | Rule Name | Criteria | Outcome | Detail |
| :--- | :--- | :--- | :---: | :--- |
| `oc-val-01` | MDT Streaming Telemetry Subscription Active | MDT signature matching | **PASS** | Count 9 >= 1 |
| `oc-val-02` | Queue Depth Surge Detected | `queue_depth_bytes > 5000000` | **PASS** | Observed 5 events matching criteria |
| `oc-val-03` | Multi-Vendor Core Representation | Multi-vendor switch representation | **PASS** | Observed 7 events matching criteria |
| `oc-val-04` | Telemetry Equilibrium Restored | `status == "normal"` | **PASS** | Observed 3 events matching criteria |

![OpenConfig MDT Validation](/docs/acceptance/images/w1_mdt_10_validation.png)

---

## 8. Final Acceptance Determination

* **Determination:** **`PASS WITH FRICTION`**
* **Friction Detail:** Minor UX ambiguity regarding HTTP HEC metric transport vs native gRPC dial-out (`W1-P2-001`).
* **Developer Knowledge Required:** **`NO`** (Auto-discovered queries eliminate need for manual `mstats` construction).
* **Maturity Recommendation:** **`REMAIN_E2E_VALIDATED`**
