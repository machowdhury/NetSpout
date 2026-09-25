# NETSPOUT INDEPENDENT PRODUCT ACCEPTANCE REPORT
## SCENARIO 01 — SASE CLOUD INGRESS APP DEGRADATION & SYNTHETIC VALIDATION

**Evaluation Date:** 2026-09-25  
**Product Version:** NetSpout Gate 9 Baseline (Wave 1 Promoted)  
**Evaluator Persona:** Principal Cloud Network & SASE Operations Engineer  
**User Goal:** *"I need to demonstrate a cloud/SASE application degradation problem in Splunk involving multiple network/security services, but I don't have the SASE infrastructure."*  
**Acceptance Determination:** **PASS**  
**Catalog Maturity Recommendation:** **`GOLDEN_PATH_CERTIFIED`** (Retained at `E2E_VALIDATED` during test per protocol)  

---

## 1. Discovery Experience

Starting from the fresh NetSpout Web UI within Splunk (`http://localhost:8800/en-US/app/netspout/netspout_canvas`):

* **User-Facing Title:** **`SASE Cloud Ingress App Degradation & Synthetic Validation`**
* **Category Pill:** **`Network Operations`**
* **Vendors Displayed:** `Zscaler`, `Palo Alto`, `Cisco ThousandEyes`, `Cisco Nexus`
* **Topology Displayed:** `mixed_sase` (5-node multi-vendor SASE topology)
* **Telemetry Displayed:** `zscaler:zia`, `pan:threat`, `cisco:thousandeyes:metric`, `cisco:dc:nexus9k:syslog`
* **Interactions Required:**
  1. Click category filter pill: `Network Operations`
  2. Locate and click scenario card: `SASE Cloud Ingress App Degradation & Synthetic Validation`
  3. Click `Preview Selection` to proceed to Step 2
* **Documentation Required:** None. The card displays a clear summary of the scenario, affected entities, and attack/defense objectives.
* **Developer Knowledge Required:** **NO**. Discovery was executed purely via standard UI categories, titles, and vendor pills without inspecting internal IDs or source code.

![SASE Discovery](/docs/acceptance/images/w1_sase_01_discovery.png)

---

## 2. Preview & Environment Realism

In Step 2 (Preview Selection), the user inspects the target topology, phase progression, and operational objectives before committing to execution:

* **Topology Realism:** The canvas visualizes an enterprise branch connected through dual cloud security gateways (Zscaler Cloud Edge and Palo Alto Prisma SD-WAN) with ThousandEyes synthetic monitoring probes and datacenter core interconnects.
* **Component Participation Breakdown:**
  * **Active Telemetry Producers:**
    1. `Zscaler-ZIA-CloudEdge` (Vendor: Zscaler, Sourcetype: `zscaler:zia`)
    2. `ThousandEyes-CloudAgent` (Vendor: Cisco ThousandEyes, Sourcetype: `cisco:thousandeyes:metric`)
    3. `PaloAlto-Prisma-SDWAN` (Vendor: Palo Alto Networks, Sourcetype: `pan:threat`)
    4. `Cisco-Nexus-DC-Core` (Vendor: Cisco Nexus, Sourcetype: `cisco:dc:nexus9k:syslog`)
  * **Topology Context Only:** Branch routing and edge boundary nodes establishing visual network perimeter context.
  * **Not Participating:** Zero dangling nodes.

![SASE Preview](/docs/acceptance/images/w1_sase_02_preview.png)

---

## 3. Connection Configuration

In Step 3 (Configure Connection), the user configures the telemetry transport pipeline:

* **Target Splunk Event Index:** `idx_network_ops`
* **HEC Endpoint:** `https://127.0.0.1:8888/services/collector`
* **HEC Token:** Pre-populated default container token
* **Self-Signed TLS:** Enabled checkbox for local Docker environment
* **Connection Test:** Succeeded immediately with green acknowledgment badge.

![SASE Connection](/docs/acceptance/images/w1_sase_03_connection.png)

---

## 4. Scenario Execution & Runtime Phase Evidence

The user advances to Step 4 (Execute & Observe) and clicks `Launch Scenario`. A fresh run executes across 6 distinct lifecycle phases:

* **Fresh Run Correlation ID:** **`NS-20260925-0509b5d9`**
* **Total Events Generated:** **9**
* **Dispatch Succeeded:** **9 / 9 (100% HTTP 200)**
* **Dispatch Failed:** **0**

### 4.1. Baseline Phase
* **Observed State:** Nominal cloud edge proxy throughput. Zscaler reports standard web inspection; ThousandEyes records synthetic baseline round-trip latency (~38ms).
![SASE Baseline](/docs/acceptance/images/w1_sase_04_baseline.png)

### 4.2. Fault / Degradation Phase
* **Observed State:** Cloud SASE Proxy TLS handshake scheduler bottleneck occurs on `Zscaler-ZIA-CloudEdge`. Handshake latency surges to 240ms, and ThousandEyes detects cloud path ingress latency breach (>200ms).
![SASE Fault](/docs/acceptance/images/w1_sase_05_fault.png)

### 4.3. Telemetry Propagation Phase
* **Observed State:** Telemetry cascades across transit layers. Palo Alto Prisma SD-WAN logs application queue congestion (`App-Queue-Congestion-Spike`); Cisco Nexus DC Core logs transit queue saturation.
![SASE Propagation](/docs/acceptance/images/w1_sase_06_propagation.png)

### 4.4. Policy Mitigation / Failover Phase
* **Observed State:** Palo Alto Prisma SD-WAN activates Policy-Based Forwarding (`Policy-Based-Forwarding-Engaged`) to steer enterprise SaaS sessions away from the congested proxy gateway to secondary paths.
![SASE Mitigation](/docs/acceptance/images/w1_sase_07_mitigation.png)

### 4.5. Steady State Recovery Phase
* **Observed State:** Zscaler ZIA TLS inspection latency normalizes; ThousandEyes confirms cloud path latency restores to nominal baseline (<40ms).
![SASE Recovery](/docs/acceptance/images/w1_sase_08_recovery.png)

---

## 5. Splunk Observation & Investigation

The user navigates directly into the Splunk Search & Reporting app using the copyable run query:

```spl
search index=idx_network_ops netspout_run_id="NS-20260925-0509b5d9"
```

* **Splunk Event Count Observed:** **9 of 9 (100.0% completeness)**
* **Sourcetypes Observed in Splunk:**
  * 3x `zscaler:zia`
  * 3x `cisco:thousandeyes:metric`
  * 2x `pan:threat`
  * 1x `cisco:dc:nexus9k:syslog`

![SASE Splunk Evidence](/docs/acceptance/images/w1_sase_09_splunk_evidence.png)

### Operational Investigation Questions Answered Purely via Evidence:

1. **Which application/service degraded?**
   Enterprise cloud SaaS application egress via SASE web proxy.
2. **Which path/service component was implicated?**
   `Zscaler-ZIA-CloudEdge` proxy TLS handshake scheduler bottleneck.
3. **What changed from baseline?**
   Zscaler TLS inspection duration escalated from normal to degraded, and ThousandEyes synthetic test latency surged from 38ms to over 200ms.
4. **Which vendor/source observed the problem?**
   Zscaler (`zscaler:zia`), Cisco ThousandEyes (`cisco:thousandeyes:metric`), Palo Alto (`pan:threat`), and Cisco Nexus (`cisco:dc:nexus9k:syslog`).
5. **Was there measurable performance impact?**
   Yes. ThousandEyes probe logged `duration_ms=215` with signature `ThousandEyes Cloud Path Ingress Latency Violation`.
6. **Was another path/service involved?**
   Yes. Palo Alto Prisma SD-WAN and Cisco Nexus datacenter core experienced queue congestion before traffic steering engaged.
7. **What mitigation occurred?**
   Palo Alto Prisma SD-WAN engaged Policy-Based Forwarding (`Policy-Based-Forwarding-Engaged`) to divert traffic.
8. **Did service recover?**
   Yes. Zscaler inspection latency normalized and ThousandEyes logged `ThousandEyes Cloud Path Latency Restored`.
9. **Which Splunk evidence supports the conclusion?**
   Correlated events under `netspout_run_id="NS-20260925-0509b5d9"` documenting the timeline from baseline to fault, propagation, mitigation, and recovery.

---

## 6. Correlation Classification

* **Classification:** **`CAUSALLY_MODELED`**
* **Rationale:** The scenario exhibits true causal chain modeling rather than superficial temporal juxtaposition. The initial root cause (Zscaler TLS bottleneck) directly triggers synthetic probe SLA violations, which propagates queue backpressure to the Palo Alto SD-WAN edge, compelling dynamic policy re-routing, and finally resolving in verified synthetic latency restoration.

---

## 7. Validation Engine Results

In Step 5 (Prove Expected Condition), the NetSpout validation engine evaluates the run against 4 distinct contract validation rules:

* **Observation Completeness:** **100.0% (9 / 9)**
* **Destination Status:** **`PASS`**
* **Overall Contract Validation:** **`PASS`**

| Rule ID | Rule Name | Criteria | Outcome | Detail |
| :--- | :--- | :--- | :---: | :--- |
| `sase-val-01` | SASE Service Degradation Detected | `status == "degraded"` | **PASS** | Count 3 >= 1 |
| `sase-val-02` | Synthetic Probe Confirms Latency Breach | `duration > 150ms` | **PASS** | Observed 4 events matching criteria |
| `sase-val-03` | Multi-Vendor SASE Telemetry Present | Multi-vendor representation | **PASS** | Count 3 >= 1 |
| `sase-val-04` | Service Restored Post-Mitigation | `status == "normal"` | **PASS** | Observed 2 events matching criteria |

![SASE Validation](/docs/acceptance/images/w1_sase_10_validation.png)

---

## 8. Final Acceptance Determination

* **Determination:** **`PASS`**
* **Developer Knowledge Required:** **`NO`**
* **Maturity Recommendation:** **`GOLDEN_PATH_CERTIFIED`** (Maintained at `E2E_VALIDATED` during test per protocol)
