# NETSPOUT INDEPENDENT PRODUCT ACCEPTANCE REPORT
## WAVE 2 — SCENARIO 03: SERVICE PROVIDER CORE (BGP COLLAPSE & TI-LFA FAST REROUTE)

**Evaluation Date:** 2026-09-25  
**Product Version:** NetSpout Gate 10 Baseline  
**Scenario ID:** `service_provider_cisco`  
**Evaluator Persona:** Principal Service Provider Backbone Architect & Peering Engineer  
**User Goal:** *"I need to demonstrate a service-provider core link failure, BGP impact and fast reroute in Splunk, but I don't have IOS-XR routers or an SR/MPLS lab."*  
**Acceptance Determination:** **`PASS WITH FRICTION`** (Friction: Timing Claim Truth Distinction: Modeled vs Empirically Measured)  
**Catalog Maturity Recommendation:** **`REMAIN_E2E_VALIDATED`** (Requires explicit Modeled Timing Badge prior to Golden Path Promotion)  

---

## 1. Transport Truth & Timing Truth

### 1.1. Telemetry Fidelity & Transport
* **Telemetry Format Classification:** **`VERIFIED_FORMAT`**
  * Event syslogs strictly match Cisco IOS-XR carrier routing messages:
    * Baseline route stability: `%ROUTING-BGP-6-STABILITY: Prefix 10.200.0.0/16 active via primary path...`
    * BGP Neighbor Drop: `%ROUTING-BGP-5-ADJCHANGE: neighbor 198.51.100.1 Down - Interface flap on HundredGigE0/0/0/1`
    * Transit Route Withdrawal: `%ROUTING-BGP-5-ADJCHANGE: neighbor 10.200.0.1 Down...`
    * TI-LFA Local Repair: `%MPLS-6-TI_LFA_LOCAL_REPAIR: Fast reroute activated for prefix 10.200.0.0/16 via HundredGigE0/0/0/2 backup path, convergence_ms=32`
    * BGP Session Restoration: `%ROUTING-BGP-5-ADJCHANGE: neighbor 198.51.100.1 Up - Peering re-established after carrier stabilization`
  * Streaming metrics match OpenConfig / Model-Driven Telemetry (MDT) interface counters dispatched to Splunk metric store (`cisco_mdt_metrics`).
* **Transport Classification:** **`HEC TRANSPORT`**
  * Event logs and metrics are transmitted over Splunk HTTP Event Collector (`https://127.0.0.1:8888/services/collector`). Zero native gRPC dial-out or native BGP peering is claimed.
* **Generic Fallback Telemetry Audit:** **`NONE`** (Zero occurrences of `%NETSPOUT-6-INFO` in essential evidence).

### 1.2. Timing Truth: Fast Reroute Claim
* **Gate 10 Description:** *"sub-50ms fast reroute"*
* **Timing Claim Classification:** **`MODELED`**
  * **Evidence:** In the TI-LFA event payload, NetSpout logs `convergence_ms=32`. This 32ms figure is generated deterministically by NetSpout's carrier simulation model to represent sub-50ms Topology-Independent Loop-Free Alternate (TI-LFA) fast reroute.
  * **Distinction:** NetSpout does not measure elapsed hardware ASIC packet delay using microsecond hardware timestamps. It faithfully **models** sub-50ms convergence.
* **Friction Finding (`W2-P2-001`):** NetSpout UI headers should clearly badge sub-50ms claims as *"MODELED PROTOCOL CONVERGENCE"* rather than allowing ambiguity with empirical hardware measurements.

---

## 2. Discovery Experience (Step 1)

* **Discovery Path:** Starting from NetSpout Canvas within Splunk Web.
* **Category Pill:** **`Service Provider`**
* **Scenario Card Title:** **`Service Provider Network - All Cisco (Cisco 8000, NCS 5500, IOS-XR SRv6)`**
* **Meaningful Interactions:** 2 (Category filter click + Scenario card selection).
* **Discovery Duration (T1 - T0):** **4.08 seconds**.

![SP Core Discovery](/docs/acceptance/images/w2_sp_01_discovery.png)

---

## 3. Preview & Blueprint Realism (Step 2)

* **Topology Structure:** Multi-tier carrier backbone (`service_provider_cisco`):
  * `Upstream-Carrier-AS65000` (External Peer Autonomous System, 198.51.100.1)
  * `Cisco-8201-Core01` (Carrier Core Transit Router, 10.200.0.1, IOS-XR)
  * `Cisco-8201-Core02` (Carrier Core Backup Router, 10.200.0.2, IOS-XR)
  * `Cisco-NCS5504-Spine01` (Spine Optical Transit, 10.200.1.1)
  * `Cisco-NCS5504-Spine02` (Spine Optical Transit, 10.200.1.2)
  * `Cisco-ASR9010-PE01` (Provider Edge Aggregator, 10.200.2.1)
  * `Cisco-ASR9010-PE02` (Provider Edge Aggregator, 10.200.2.2)
  * `Metro-Customer-CE01` (Customer Edge Ingress, 10.200.3.1)
* **Setup Time (T3 - T1):** **9.87 seconds**.

![SP Core Preview](/docs/acceptance/images/w2_sp_02_preview.png)

---

## 4. Pipeline Connection (Step 3)

* **Target Endpoint:** `https://127.0.0.1:8888/services/collector`
* **Target Event Index:** `idx_network_ops`
* **Target Metric Store:** `cisco_mdt_metrics` (`datatype = metric`)
* **Self-Signed TLS:** Enabled (`allow_insecure_tls = true`)
* **Reachability Test:** Verified (HTTP 200 OK, latency 4ms).

![SP Core Connection](/docs/acceptance/images/w2_sp_03_connection.png)

---

## 5. Execution & Runtime Phase Evidence (Step 4)

* **Fresh Run Correlation ID:** **`NS-20260925-87422445`**
* **Total Events Generated:** **8** (5 event logs + 3 streaming metrics)
* **Dispatched (HEC):** **8 / 8 (100% HTTP 200)**
* **Dispatched Failed:** **0**
* **Run Time (T4 - T3):** **4.01 seconds** (Mode: `TEST`).

### Phase-by-Phase Observed Evidence:

1. **Baseline Phase:**
   * Cisco 8201 logs established BGP session with AS65000: `%ROUTING-BGP-6-STABILITY: Prefix 10.200.0.0/16 active via primary path HundredGigE0/0/0/1, fast-reroute disarmed`.
   * ASR 9010 PE streams nominal 100G interface counters: 840,291,000 octets, CPU 22%, memory 36%.
   ![SP Core Baseline](/docs/acceptance/images/w2_sp_04_baseline.png)

2. **Fault Phase (Carrier Link Flap & BGP Collapse):**
   * Primary optical transit interface `HundredGigE0/0/0/1` flaps; BGP adjacency with AS65000 collapses:
     * `%ROUTING-BGP-5-ADJCHANGE: neighbor 198.51.100.1 Down - Interface flap on HundredGigE0/0/0/1 event_type=BGP_DOWN`.
     * Telemetry stream indicates throughput drop to 24,000 octets and CPU surge to 68%.
   ![SP Core Fault](/docs/acceptance/images/w2_sp_05_fault.png)

3. **Propagation Phase (Core Route Withdrawal):**
   * Failure propagates across the backbone core: Cisco ASR 9010 PE logs route withdrawal notification:
     * `%ROUTING-BGP-5-ADJCHANGE: neighbor 10.200.0.1 Down - Interface flap on HundredGigE0/0/0/1 signature="Core Transit Route Withdrawal Notification Received"`.
   ![SP Core Propagation](/docs/acceptance/images/w2_sp_06_propagation.png)

4. **Mitigation Phase (TI-LFA Fast Reroute Activation):**
   * Segment Routing TI-LFA engages hardware backup path in 32ms:
     * `%MPLS-6-TI_LFA_LOCAL_REPAIR: Fast reroute activated for prefix 10.200.0.0/16 via HundredGigE0/0/0/2 backup path, convergence_ms=32 event_type=TI_LFA_REROUTE`.
     * Streaming metrics show traffic restored across backup interface: 810,291,000 octets, CPU drops to 34%.
   ![SP Core Mitigation](/docs/acceptance/images/w2_sp_07_mitigation.png)

5. **Recovery Phase (BGP Adjacency Re-Established):**
   * Carrier transport link stabilizes; BGP peering session re-establishes:
     * `%ROUTING-BGP-5-ADJCHANGE: neighbor 198.51.100.1 Up - Peering re-established after carrier stabilization event_type=BGP_UP`.
   ![SP Core Recovery](/docs/acceptance/images/w2_sp_08_recovery.png)

---

## 6. Live Splunk Evidence & Operational Investigation

### 6.1. Event Evidence in `idx_network_ops`
* **Query:**
  ```spl
  search index=idx_network_ops netspout_run_id="NS-20260925-87422445"
  ```
* **Observed Event Count:** **5 / 5 (100.0%)**

![SP Core Splunk Evidence](/docs/acceptance/images/w2_sp_09_splunk_evidence.png)

### 6.2. Metric Evidence in `cisco_mdt_metrics`
* **Query:**
  ```spl
  | mstats count where index=cisco_mdt_metrics metric_name=* AND netspout_run_id="NS-20260925-87422445"
  ```
* **Observed Metric Count:** **3 / 3 (100.0%)**

![SP Core Metric Evidence](/docs/acceptance/images/w2_sp_09b_splunk_metric.png)

### Answers to Operational Investigation Questions:

1. **Which physical/logical link failed?**  
   Primary 100G transit link: `HundredGigE0/0/0/1` between `Cisco-8201-Core01` and upstream carrier peer `Upstream-Carrier-AS65000`.
2. **Which BGP neighbor/session was affected?**  
   BGP neighbor `198.51.100.1` (AS65000), logged via `%ROUTING-BGP-5-ADJCHANGE: neighbor 198.51.100.1 Down`.
3. **Were routes withdrawn?**  
   Yes. Core route withdrawal was propagated across the transit layer to `Cisco-ASR9010-PE01` (`neighbor 10.200.0.1 Down`).
4. **What downstream impact occurred?**  
   Transit octets dropped from 840M to 24K, and router control-plane CPU surged from 22% to 68% during route invalidation.
5. **Was an alternate path selected?**  
   Yes. Segment Routing backup path `HundredGigE0/0/0/2` was dynamically engaged.
6. **What evidence indicates TI-LFA / fast reroute?**  
   IOS-XR syslog: `%MPLS-6-TI_LFA_LOCAL_REPAIR: Fast reroute activated for prefix 10.200.0.0/16 via HundredGigE0/0/0/2 backup path, convergence_ms=32 event_type=TI_LFA_REROUTE`.
7. **Did BGP converge?**  
   Yes. The peering stabilized after carrier recovery: `%ROUTING-BGP-5-ADJCHANGE: neighbor 198.51.100.1 Up - Peering re-established after carrier stabilization`.
8. **Did traffic recover?**  
   Yes. Forwarding throughput restored to nominal (810M octets).
9. **What metrics changed during the event?**  
   Throughput octets dropped sharply during link flap and recovered post-reroute; CPU utilization spiked during re-computation (68%) and stabilized to nominal (34%).

### Routing Semantics Check:
NetSpout strictly isolates and sequences:
* `LINK_FAILURE` -> `BGP_SESSION_LOSS` -> `ROUTE_WITHDRAWAL` -> `TI_LFA_REPAIR` -> `BGP_CONVERGENCE`.
These are never collapsed into a single generic "failover" alert.

---

## 7. Validation Engine & Ground Truth Audit (Step 5)

* **Validation Status:** **`PASS`**
* **Destination Status:** **`PASS`** (Dual-store contract verified across both event and metric tiers)
* **Overall Contract Validation:** **`PASS`**

| Rule ID | Rule Name | Contract Criteria | Observed Status | Evidence Detail |
| :--- | :--- | :--- | :---: | :--- |
| `service_provider_cisco-val-01` | Required Telemetry Emitted | Required sourcetypes & sequence | **PASS** | 8 records verified across event and metric stores |

![SP Core Validation](/docs/acceptance/images/w2_sp_10_validation.png)

---

## 8. Final Determination & Metrics

* **Acceptance Determination:** **`PASS WITH FRICTION`**
* **Friction Summary:** Sub-50ms timing claim is modeled in simulation logic rather than measured with microsecond hardware packet timers (`W2-P2-001`).
* **Causality Classification:** **`CAUSALLY_MODELED`**
* **Telemetry Fidelity:** **`VERIFIED_FORMAT`**
* **Transport Truth:** **`HEC TRANSPORT`**
* **Total Time-to-Validated-Evidence:** **38.44 seconds**
* **Meaningful User Interactions:** **10**
* **Developer Knowledge Required:** **`NO`**
* **Catalog Maturity Recommendation:** **`REMAIN_E2E_VALIDATED`**
