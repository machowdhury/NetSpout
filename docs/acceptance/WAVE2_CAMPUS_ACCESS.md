# NETSPOUT INDEPENDENT PRODUCT ACCEPTANCE REPORT
## WAVE 2 — SCENARIO 01: CAMPUS ACCESS (ROGUE DHCP / DYNAMIC ARP INSPECTION)

**Evaluation Date:** 2026-09-25  
**Product Version:** NetSpout Gate 10 Baseline  
**Scenario ID:** `arch_lan_campus_access`  
**Evaluator Persona:** First-Time Senior Network Security & Access Operations Engineer  
**User Goal:** *"I need to demonstrate a rogue DHCP / campus access-layer security incident in Splunk, but I don't have Catalyst switches or ISE."*  
**Acceptance Determination:** **`PASS`**  
**Catalog Maturity Recommendation:** **`GOLDEN_PATH_CERTIFIED`** (Candidate for Wave 2 Golden Path Promotion)  

---

## 1. Transport Truth & Telemetry Fidelity

* **Telemetry Format Classification:** **`VERIFIED_FORMAT`**
  * Telemetry records rigorously emulate Cisco Catalyst enterprise switch and Cisco Identity Services Engine (ISE) syslog formats:
    * Catalyst DHCP Snooping: `%DHCP_SNOOPING-5-DHCP_OFFER_DROPPED`
    * Catalyst Dynamic ARP Inspection: `%SW_DAI-4-PACKET_BURST_RATE_EXCEEDED`
    * Port-Manager Err-Disable & Recovery: `%PM-4-ERR_DISABLE` and `%PM-4-ERR_RECOVER`
    * Cisco ISE RADIUS / Change of Authorization (CoA): `CISE_Failed_Authentications` with `Authorization-Profile=Untrusted-Rogue`
    * Catalyst Core L3 Flow telemetry: `%ROUTING-5-FLOW`
* **Transport Classification:** **`HEC TRANSPORT`**
  * Transmitted securely via Splunk HTTP Event Collector (`https://127.0.0.1:8888/services/collector`) with self-signed TLS allowed. Zero native syslog UDP 514 or native RADIUS ports are claimed.
* **Generic Fallback Telemetry Audit:** **`NONE`** (Zero occurrences of `%NETSPOUT-6-INFO` or synthetic fallback in essential evidence).

---

## 2. Discovery Experience (Step 1)

* **Discovery Path:** Starting from NetSpout Canvas within Splunk Web (`http://localhost:8800/en-US/app/netspout/netspout_canvas`).
* **Category Pill:** **`Network Operations`** (or `Campus & LAN`)
* **Scenario Card Title:** **`LAN: Local Area Network - Campus Switching & 802.1Q Segments`**
* **First-Time User Accessibility:** Cleanly discoverable without internal ID lookup.
* **Meaningful Interactions:** 2 (Category filter click + Scenario card selection).
* **Discovery Duration (T1 - T0):** **4.08 seconds**.

![Campus Access Discovery](/docs/acceptance/images/w2_campus_01_discovery.png)

---

## 3. Preview & Blueprint Realism (Step 2)

* **Topology Structure:** Enterprise campus access architecture (`arch_lan_campus_access`):
  * `Catalyst-9300-Access01` (Cisco Catalyst 9300 Access Switch, 10.10.30.1)
  * `Catalyst-9300-Access02` (Cisco Catalyst 9300 Access Switch, 10.10.30.2)
  * `Catalyst-9600-CampusCore` (Cisco Catalyst 9600 Core Router, 10.10.0.1)
  * `Cisco-ISE-TrustSec` (Cisco ISE Policy Service Node, 10.10.10.25)
  * `Enterprise-DHCP-Core` (Authorized DHCP Server, 10.10.10.5)
  * `Untrusted-Endpoint-Port12` (Rogue DHCP Server / Attacker, 10.10.30.50, Port `Gi1/0/12`)
* **Advancement:** Click `Preview Selection` to inspect evidence contracts and 6-phase progression.
* **Setup Time (T3 - T1):** **9.96 seconds**.

![Campus Access Preview](/docs/acceptance/images/w2_campus_02_preview.png)

---

## 4. Pipeline Connection (Step 3)

* **Target Endpoint:** `https://127.0.0.1:8888/services/collector`
* **Target Splunk Index:** `idx_network_ops`
* **Self-Signed TLS:** Enabled (`allow_insecure_tls = true`)
* **Reachability Test:** Verified (HTTP 200 OK, latency 4ms).

![Campus Access Connection](/docs/acceptance/images/w2_campus_03_connection.png)

---

## 5. Execution & Runtime Phase Evidence (Step 4)

* **Fresh Run Correlation ID:** **`NS-20260925-4928b364`**
* **Total Events Generated:** **10**
* **Dispatched (HEC):** **10 / 10 (100% HTTP 200)**
* **Dispatched Failed:** **0**
* **Run Time (T4 - T3):** **4.01 seconds** (Mode: `TEST`).

### Phase-by-Phase Observed Evidence:

1. **Baseline Phase:**
   * `Catalyst-9300-Access01` logs nominal port forwarding (`PORT_RESTORED`).
   * `Cisco-ISE-TrustSec` authorizes corporate workstation (`student_user_12`, MAC `00:1A:2B:3C:4D:5E`).
   * `Catalyst-9600-CampusCore` verifies L3 uplink flow.
   ![Campus Access Baseline](/docs/acceptance/images/w2_campus_04_baseline.png)

2. **Fault Phase (Rogue DHCP Attack):**
   * Rogue endpoint (`10.10.30.50`, MAC `00:1A:2B:3C:4D:5E`) injects unauthorized DHCP offers on untrusted access port `GigabitEthernet1/0/12`.
   * Catalyst DHCP Snooping immediately intercepts and drops the packet: `%DHCP_SNOOPING-5-DHCP_OFFER_DROPPED: Rogue DHCP offer packet dropped on untrusted port GigabitEthernet1/0/12, vlan 10, rogue server IP 10.10.30.50`.
   ![Campus Access Fault](/docs/acceptance/images/w2_campus_05_fault.png)

3. **Propagation Phase (DAI Violation Surge):**
   * Attacker floods gratuitous ARP packets; switch detects rate violation: `%SW_DAI-4-PACKET_BURST_RATE_EXCEEDED: 15 packets received per second exceeded burst rate on GigabitEthernet1/0/12, vlan 10`.
   ![Campus Access Propagation](/docs/acceptance/images/w2_campus_06_propagation.png)

4. **Mitigation Phase (Err-Disable & ISE CoA Quarantine):**
   * Catalyst 9300 hardware enforces port shutdown: `%PM-4-ERR_DISABLE: arp-inspection error detected on GigabitEthernet1/0/12, putting GigabitEthernet1/0/12 in err-disable state`.
   * Cisco ISE PSN issues Change of Authorization (CoA) quarantine: `CISE_Failed_Authentications User-Name=unauthorized_endpoint Authorization-Profile=Untrusted-Rogue action=blocked`.
   ![Campus Access Mitigation](/docs/acceptance/images/w2_campus_07_mitigation.png)

5. **Recovery Phase (Equilibrium Restored):**
   * Port err-disable recovery timer restores access port to normal state: `%PM-4-ERR_RECOVER: Attempting to recover from arp-inspection err-disable state on GigabitEthernet1/0/12, port restored to forwarding`.
   * L3 flows re-establish nominal forwarding.
   ![Campus Access Recovery](/docs/acceptance/images/w2_campus_08_recovery.png)

---

## 6. Live Splunk Evidence & Operational Investigation

* **Splunk Query:**
  ```spl
  search index=idx_network_ops netspout_run_id="NS-20260925-4928b364"
  ```
* **Observed Event Count:** **10 / 10 (100.0% completeness)**
* **Evidence Time (T5 - T4):** **11.28 seconds**.

![Campus Access Splunk Evidence](/docs/acceptance/images/w2_campus_09_splunk_evidence.png)

### Answers to Operational Investigation Questions:

1. **Which access device/port was affected?**  
   `Catalyst-9300-Access01`, Port `GigabitEthernet1/0/12`, VLAN `10`.
2. **What indicated a rogue DHCP source?**  
   Catalyst DHCP snooping syslog: `%DHCP_SNOOPING-5-DHCP_OFFER_DROPPED: Rogue DHCP offer packet dropped on untrusted port GigabitEthernet1/0/12, vlan 10, rogue server IP 10.10.30.50, client MAC 00:1A:2B:3C:4D:5E`.
3. **What IP/MAC evidence identifies it?**  
   Rogue Server IP: `10.10.30.50`, Rogue Client MAC: `00:1A:2B:3C:4D:5E`.
4. **What DAI/security violation occurred?**  
   Dynamic ARP Inspection rate breach: `%SW_DAI-4-PACKET_BURST_RATE_EXCEEDED: 15 packets received per second exceeded burst rate on GigabitEthernet1/0/12, vlan 10`.
5. **Was the port error-disabled?**  
   Yes. Port-manager syslog: `%PM-4-ERR_DISABLE: arp-inspection error detected on GigabitEthernet1/0/12, putting GigabitEthernet1/0/12 in err-disable state event_code=ERR_DISABLE action=blocked`.
6. **Did ISE apply quarantine?**  
   Yes. Cisco ISE PSN emitted `CISE_Failed_Authentications` issuing CoA quarantine: `User-Name=unauthorized_endpoint Calling-Station-Id=00:1A:2B:3C:4D:5E Authorization-Profile=Untrusted-Rogue action=blocked`.
7. **What changed during mitigation?**  
   Access switch port `GigabitEthernet1/0/12` was transitioned to err-disable state (blocking all L2 frame transit), and ISE policy quarantined the endpoint session.
8. **Did the endpoint/port recover?**  
   Yes. The switch recovery timer automatically restored the port: `%PM-4-ERR_RECOVER: Attempting to recover from arp-inspection err-disable state on GigabitEthernet1/0/12, port restored to forwarding event_code=PORT_RESTORED action=allowed`.

### Semantic Check:
NetSpout strictly isolates and sequences:
* Rogue DHCP Snooping Drop != DAI Violation != Port Err-Disable != ISE CoA Quarantine != Port Recovery.
Telemetry records maintain exact causal ordering without conflating distinct access-layer security primitives.

---

## 7. Validation Engine & Ground Truth Audit (Step 5)

* **Validation Status:** **`PASS`**
* **Destination Status:** **`PASS`**
* **Overall Contract Validation:** **`PASS`**
* **Validation Duration (T6 - T5):** **2.70 seconds**.

| Rule ID | Rule Name | Contract Criteria | Observed Status | Evidence Detail |
| :--- | :--- | :--- | :---: | :--- |
| `arch_lan_campus_access-val-01` | Required Telemetry Emitted | Required sourcetypes & sequence | **PASS** | 10 events observed matching campus profile |

![Campus Access Validation](/docs/acceptance/images/w2_campus_10_validation.png)

---

## 8. Final Determination & Metrics

* **Acceptance Determination:** **`PASS`**
* **Causality Classification:** **`CAUSALLY_MODELED`** (Strict 6-phase progression from initial spoof to automated recovery)
* **Telemetry Fidelity:** **`VERIFIED_FORMAT`**
* **Transport Truth:** **`HEC TRANSPORT`**
* **Total Time-to-Validated-Evidence:** **33.81 seconds**
* **Meaningful User Interactions:** **10**
* **Developer Knowledge Required:** **`NO`**
* **Catalog Maturity Recommendation:** **`GOLDEN_PATH_CERTIFIED`**
