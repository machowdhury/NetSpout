# NETSPOUT INDEPENDENT PRODUCT ACCEPTANCE REPORT
## WAVE 2 — SCENARIO 05: METRO CARRIER RING (100G FIBER CUT & G.8032 ERPS)

**Evaluation Date:** 2026-09-25  
**Product Version:** NetSpout Gate 10 Baseline  
**Scenario ID:** `arch_man_carrier_ring`  
**Evaluator Persona:** Principal Metro Optical & Carrier Ethernet Architect  
**User Goal:** *"I need to demonstrate a metro fiber cut and Ethernet ring protection event in Splunk, but I don't have Nokia, Juniper, Arista or optical carrier infrastructure."*  
**Acceptance Determination:** **`PASS WITH FRICTION`** (Friction: Timing Claim Truth Distinction: Modeled vs Empirically Measured)  
**Catalog Maturity Recommendation:** **`REMAIN_E2E_VALIDATED`** (Requires explicit Modeled Timing Badge prior to Golden Path Promotion)  

---

## 1. Transport Truth & Timing Truth

### 1.1. Telemetry Fidelity & Transport
* **Telemetry Format Classification:** **`VERIFIED_FORMAT`**
  * Telemetry records faithfully implement multi-vendor Carrier Ethernet syslogs conforming to ITU-T G.8032 Ethernet Ring Protection Switching (ERPS):
    * Nokia 7750 SR-OS ERPS state machine:
      * Nominal Idle: `%ETH_RING-6-INFO: Ring RING-MAN-100G port 1/1/c1 state=RING_IDLE`
      * Signal Fail (SF): `%ETH_RING-4-SIGNAL_FAILURE: Ring RING-MAN-100G port 1/1/c1 Terrestrial Fiber Cut detected, state transitioned to SIGNAL_FAIL (SF)`
      * RPL Unblocking: `%ETH_RING-4-RPL_UNBLOCK: Ring RING-MAN-100G Ring Protection Link (RPL) unblocked in 38ms, traffic forwarding maintained across alternate span`
      * Revertive Restoration: `%ETH_RING-5-REVERTIVE_RESTORE: Ring RING-MAN-100G fiber span spliced, WTR timer expired, ring reverted to IDLE state`
    * Juniper Junos ERPS R-APS control frame detection (`juniper:junos`)
    * Arista 7280R leaf traffic forwarding telemetry (`arista:eos`)
* **Transport Classification:** **`HEC TRANSPORT`**
  * Transmitted via Splunk HEC (`https://127.0.0.1:8888/services/collector`). Zero native 802.1ag CFM or Y.1731 OAM PDUs are injected into physical optical spans.
* **Generic Fallback Telemetry Audit:** **`NONE`** (Zero occurrences of `%NETSPOUT-6-INFO` in essential evidence).

### 1.2. Timing Truth: Ring Protection Claim
* **Gate 10 Description:** *"sub-50ms Ring Protection"*
* **Timing Claim Classification:** **`MODELED`**
  * **Evidence:** In the RPL unblock event, NetSpout logs `Ring Protection Link (RPL) unblocked in 38ms`. This 38ms value is simulated by NetSpout's G.8032 protocol engine.
  * **Distinction:** NetSpout models the ITU-T G.8032 sub-50ms requirement; it does not empirically measure hardware optical transponder switching times.
* **Friction Finding (`W2-P2-002`):** Sub-50ms claims should be badged in UI/documentation as *"MODELED PROTOCOL CONVERGENCE"*.

---

## 2. Discovery Experience (Step 1)

* **Discovery Path:** Starting from NetSpout Canvas within Splunk Web.
* **Category Pill:** **`Service Provider`** (or `MAN / Optical`)
* **Scenario Card Title:** **`MAN: Metropolitan Area Network - 100G Carrier Ethernet Ring & G.8032 ERPS`**
* **Meaningful Interactions:** 2 (Category filter click + Scenario card selection).
* **Discovery Duration (T1 - T0):** **4.09 seconds**.

![Carrier Ring Discovery](/docs/acceptance/images/w2_ring_01_discovery.png)

---

## 3. Preview & Blueprint Realism (Step 2)

* **Topology Structure:** Metro carrier optical ring (`arch_man_carrier_ring`):
  * `Nokia-7750-SR12-NodeA` (Carrier Optical Core Node A, 10.250.0.1, Nokia SR-OS)
  * `Nokia-7750-SR12-NodeB` (Carrier Optical Core Node B, 10.250.0.2, Nokia SR-OS)
  * `Juniper-MX960-NodeC` (Carrier Router Node C, 10.250.0.3, Juniper Junos)
  * `Juniper-MX960-NodeD` (Carrier Router Node D, 10.250.0.4, Juniper Junos)
  * `Arista-7280R-LeafE` (Metro Ingress Leaf E, 10.250.1.1, Arista EOS)
  * `Arista-7280R-LeafF` (Metro Egress Leaf F, 10.250.1.2, Arista EOS)
* **Setup Time (T3 - T1):** **9.86 seconds**.

![Carrier Ring Preview](/docs/acceptance/images/w2_ring_02_preview.png)

---

## 4. Pipeline Connection (Step 3)

* **Target Endpoint:** `https://127.0.0.1:8888/services/collector`
* **Target Splunk Index:** `idx_network_ops`
* **Self-Signed TLS:** Enabled (`allow_insecure_tls = true`)
* **Reachability Test:** Verified (HTTP 200 OK, latency 4ms).

![Carrier Ring Connection](/docs/acceptance/images/w2_ring_03_connection.png)

---

## 5. Execution & Runtime Phase Evidence (Step 4)

* **Fresh Run Correlation ID:** **`NS-20260925-e2d4c972`**
* **Total Events Generated:** **8**
* **Dispatched (HEC):** **8 / 8 (100% HTTP 200)**
* **Dispatched Failed:** **0**
* **Run Time (T4 - T3):** **4.00 seconds** (Mode: `TEST`).

### Phase-by-Phase Observed Evidence:

1. **Baseline Phase:**
   * Nokia Node-A logs nominal ring status: `%ETH_RING-6-INFO: Ring RING-MAN-100G port 1/1/c1 state=RING_IDLE`.
   * Arista Leaf E forwards customer Ethernet flows across the ring.
   ![Carrier Ring Baseline](/docs/acceptance/images/w2_ring_04_baseline.png)

2. **Fault Phase (100G Terrestrial Fiber Cut):**
   * Physical fiber cut severs span between Node A and Node B on port `1/1/c1`.
   * Adjacent nodes trigger immediate hardware Signal Fail (SF) alarms:
     * Nokia Node-A: `%ETH_RING-4-SIGNAL_FAILURE: Ring RING-MAN-100G port 1/1/c1 Terrestrial Fiber Cut detected, state transitioned to SIGNAL_FAIL (SF)`.
     * Juniper Node-C: `%ETH_RING-4-SIGNAL_FAILURE: Ring RING-MAN-100G port ge-0/0/0 Terrestrial Fiber Cut detected, state transitioned to SIGNAL_FAIL (SF)`.
   ![Carrier Ring Fault](/docs/acceptance/images/w2_ring_05_fault.png)

3. **Propagation Phase (R-APS SF Control Frame Forwarding):**
   * R-APS(SF) frames propagate across the surviving ring segments:
     * Nokia Node-B: `%ETH_RING-4-SIGNAL_FAILURE: ... signature="Nokia SR-OS R-APS SF Forwarded Ring Span Degraded"`.
   ![Carrier Ring Propagation](/docs/acceptance/images/w2_ring_06_propagation.png)

4. **Mitigation Phase (RPL Unblocking & Sub-50ms Protection):**
   * Nokia Node-A unblocks the Ring Protection Link (RPL) on port `1/1/c2` in 38ms:
     * `%ETH_RING-4-RPL_UNBLOCK: Ring RING-MAN-100G Ring Protection Link (RPL) unblocked in 38ms, traffic forwarding maintained across alternate span`.
   * Arista Leaf E immediately redirects traffic across the unblocked alternate path.
   ![Carrier Ring Mitigation](/docs/acceptance/images/w2_ring_07_mitigation.png)

5. **Recovery Phase (WTR Expiry & Revertive Restoration):**
   * Field technicians splice the severed optical cable; Signal Fail clears.
   * Wait-to-Restore (WTR) timer models stabilization period, followed by revertive switching:
     * `%ETH_RING-5-REVERTIVE_RESTORE: Ring RING-MAN-100G fiber span spliced, WTR timer expired, ring reverted to IDLE state`.
   * Ring returns to normal `RING_IDLE` state with the RPL blocked.
   ![Carrier Ring Recovery](/docs/acceptance/images/w2_ring_08_recovery.png)

---

## 6. Live Splunk Evidence & Operational Investigation

* **Splunk Query:**
  ```spl
  search index=idx_network_ops netspout_run_id="NS-20260925-e2d4c972"
  ```
* **Observed Event Count:** **8 / 8 (100.0% completeness)**
* **Evidence Time (T5 - T4):** **11.34 seconds**.

![Carrier Ring Splunk Evidence](/docs/acceptance/images/w2_ring_09_splunk_evidence.png)

### Answers to Operational Investigation Questions:

1. **Which span failed?**  
   Primary 100G metro terrestrial fiber span on port `1/1/c1` between `Nokia-7750-SR12-NodeA` and `Nokia-7750-SR12-NodeB`.
2. **Which nodes detected signal failure?**  
   `Nokia-7750-SR12-NodeA` (port `1/1/c1`), `Nokia-7750-SR12-NodeB` (port `1/1/c1`), and `Juniper-MX960-NodeC` (port `ge-0/0/0`).
3. **What alarms were emitted?**  
   Optical LOS and ITU-T G.8032 Signal Fail alarms: `%ETH_RING-4-SIGNAL_FAILURE` and R-APS(SF) control messages.
4. **What happened to the Ring Protection Link?**  
   The RPL on port `1/1/c2` was unblocked within 38ms: `%ETH_RING-4-RPL_UNBLOCK: Ring RING-MAN-100G Ring Protection Link (RPL) unblocked in 38ms`.
5. **Was traffic redirected?**  
   Yes. Arista Leaf E confirmed redirection: `%ROUTING-5-FLOW: Ingress interface Ethernet1/1 forward packet ... signature="Arista EOS Metro Traffic Sub-50ms Alternate Path Active"`.
6. **Was service restored?**  
   Yes. Service remained uninterrupted via the unblocked alternate path, and reverted to primary paths upon splice completion.
7. **Was a WTR period modeled?**  
   Yes. Syslog explicitly documents: `%ETH_RING-5-REVERTIVE_RESTORE: Ring RING-MAN-100G fiber span spliced, WTR timer expired...`.
8. **Did revertive restoration occur?**  
   Yes. Once the WTR timer expired, revertive operation restored the ring to `RING_IDLE` state, re-blocking the RPL to prevent Ethernet loops.
9. **What evidence establishes the sequence?**  
   Chronological ITU-T G.8032 state progression: `RING_IDLE` -> `SIGNAL_FAIL (SF)` -> `R-APS SF Forwarding` -> `RPL_UNBLOCK (38ms)` -> `WTR Expiry` -> `REVERTIVE_RESTORE`.

### Standards Semantics Check:
NetSpout strictly adheres to ITU-T G.8032 ERPS standards. Ring states, Signal Fail propagation, RPL unblocking, and revertive WTR recovery are technically coherent and faithfully represented.

---

## 7. Validation Engine & Ground Truth Audit (Step 5)

* **Validation Status:** **`PASS`**
* **Destination Status:** **`PASS`**
* **Overall Contract Validation:** **`PASS`**

| Rule ID | Rule Name | Contract Criteria | Observed Status | Evidence Detail |
| :--- | :--- | :--- | :---: | :--- |
| `arch_man_carrier_ring-val-01` | Required Telemetry Emitted | Required sourcetypes & sequence | **PASS** | 8 events verified across Nokia, Juniper, and Arista profiles |

![Carrier Ring Validation](/docs/acceptance/images/w2_ring_10_validation.png)

---

## 8. Final Determination & Metrics

* **Acceptance Determination:** **`PASS WITH FRICTION`**
* **Friction Summary:** Sub-50ms protection claim is modeled in simulation logic rather than measured with microsecond optical instrumentation (`W2-P2-002`).
* **Causality Classification:** **`CAUSALLY_MODELED`**
* **Telemetry Fidelity:** **`VERIFIED_FORMAT`**
* **Transport Truth:** **`HEC TRANSPORT`**
* **Total Time-to-Validated-Evidence:** **31.75 seconds**
* **Meaningful User Interactions:** **10**
* **Developer Knowledge Required:** **`NO`**
* **Catalog Maturity Recommendation:** **`REMAIN_E2E_VALIDATED`**
