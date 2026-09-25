# NETSPOUT INDEPENDENT PRODUCT ACCEPTANCE REPORT
## WAVE 2 — SCENARIO 04: WIRELESS RF INTERFERENCE & EVIL TWIN CONTAINMENT

**Evaluation Date:** 2026-09-25  
**Product Version:** NetSpout Gate 10 Baseline  
**Scenario ID:** `arch_wlan_meraki_catalyst`  
**Evaluator Persona:** Senior Enterprise Wireless & RF Spectrum Engineer  
**User Goal:** *"I need to demonstrate RF interference and rogue wireless activity in Splunk, but I don't have Catalyst wireless or Meraki infrastructure."*  
**Acceptance Determination:** **`PASS WITH FRICTION`** (Friction: Wireless Semantics Nuance regarding DFS vs DCA)  
**Catalog Maturity Recommendation:** **`REMAIN_E2E_VALIDATED`** (Requires wireless terminology clarification prior to Golden Path Promotion)  

---

## 1. Transport Truth & Telemetry Fidelity

* **Telemetry Format Classification:** **`VERIFIED_FORMAT`**
  * Telemetry records accurately represent multi-vendor Cisco Catalyst CleanAir and Cisco Meraki Air Marshal wireless events:
    * Catalyst CleanAir RF Health: `%DOT11-6-CLEANAIR_HEALTH: Channel 100 clean, channel utilization=14.2% noise_floor=-92dBm, client SNR=38dB`
    * Catalyst CleanAir Interference Surge: `%DOT11-4-CLEANAIR_INTERFERENCE: Radio 1 Channel 36 interference surge detected: utilization=94.5% noise_floor=-58dBm duty_cycle=88%`
    * Catalyst WLC Rogue AP Alert: `%CATALYST_SEC-4-ROGUE_ALERT: Rogue AP detected on campus RF matrix. rogue_mac=00:14:22:01:23:45 bssid=00:14:22:01:23:45 ssid="Corp-Executive-Secure" channel=36 rssi=-48dBm`
    * Meraki Access Point JSON Webhook: JSON records with `alertType="air_marshal_rogue_detected"` and `alertType="client_health_report"`
    * CleanAir Channel Switch: `%DOT11-5-CLEANAIR_CHANNEL_SWITCH: Radio 1 shifted from congested Channel 36 to pristine Channel 100 via automated DCA/RRM`
    * Air Marshal Containment: `%CATALYST_SEC-5-ROGUE_CONTAINED: Evil-Twin SSID "Corp-Executive-Secure" BSSID 00:14:22:01:23:45 contained via 802.11 deauthentication matrix`
* **Transport Classification:** **`HEC TRANSPORT`**
  * Transmitted over Splunk HEC (`https://127.0.0.1:8888/services/collector`). Zero native Meraki Dashboard Cloud webhooks or native CAPWAP control tunnels are simulated.
* **Generic Fallback Telemetry Audit:** **`NONE`** (Zero occurrences of `%NETSPOUT-6-INFO` in essential evidence).

---

## 2. Discovery Experience (Step 1)

* **Discovery Path:** Starting from NetSpout Canvas within Splunk Web.
* **Category Pill:** **`Wireless`**
* **Scenario Card Title:** **`WLAN: Wireless Local Area Network - Catalyst 9800 & Meraki Wi-Fi 6E/7`**
* **Meaningful Interactions:** 2 (Category filter click + Scenario card selection).
* **Discovery Duration (T1 - T0):** **4.09 seconds**.

![WLAN Discovery](/docs/acceptance/images/w2_wlan_01_discovery.png)

---

## 3. Preview & Blueprint Realism (Step 2)

* **Topology Structure:** Enterprise hybrid wireless architecture (`arch_wlan_meraki_catalyst`):
  * `Catalyst-9130AX-AP01` (Cisco Catalyst 9130AX Wi-Fi 6E Access Point, 10.20.10.50)
  * `Meraki-MR56-AP01` (Cisco Meraki MR56 Cloud-Managed AP, 10.20.10.60)
  * `Catalyst-9800-CL-WLC` (Cisco Catalyst 9800-CL Wireless LAN Controller, 10.20.0.10)
  * `Catalyst-9300-Dist01` (Catalyst 9300 Distribution Switch, 10.20.0.1)
  * `Cisco-ISE-WLAN-Profiler` (ISE Wireless Profiler, 10.20.0.25)
  * `Unsanctioned-AP-Interferer` (Rogue / Jammer Endpoint, 10.20.10.99, Channel 36)
* **Setup Time (T3 - T1):** **9.89 seconds**.

![WLAN Preview](/docs/acceptance/images/w2_wlan_02_preview.png)

---

## 4. Pipeline Connection (Step 3)

* **Target Endpoint:** `https://127.0.0.1:8888/services/collector`
* **Target Splunk Index:** `idx_network_ops`
* **Self-Signed TLS:** Enabled (`allow_insecure_tls = true`)
* **Reachability Test:** Verified (HTTP 200 OK, latency 4ms).

![WLAN Connection](/docs/acceptance/images/w2_wlan_03_connection.png)

---

## 5. Execution & Runtime Phase Evidence (Step 4)

* **Fresh Run Correlation ID:** **`NS-20260925-11723a84`**
* **Total Events Generated:** **8**
* **Dispatched (HEC):** **8 / 8 (100% HTTP 200)**
* **Dispatched Failed:** **0**
* **Run Time (T4 - T3):** **4.01 seconds** (Mode: `TEST`).

### Phase-by-Phase Observed Evidence:

1. **Baseline Phase:**
   * Catalyst 9130 AP reports clean RF conditions on Channel 36: utilization 14.2%, noise floor -92dBm, SNR 38dB.
   * Meraki MR56 AP reports nominal client health report.
   ![WLAN Baseline](/docs/acceptance/images/w2_wlan_04_baseline.png)

2. **Fault Phase (Non-Wi-Fi RF Interference Surge):**
   * Non-Wi-Fi interference surge hits Channel 36: CleanAir detects 94.5% channel utilization, -58dBm noise floor, and 88% duty cycle:
     * `%DOT11-4-CLEANAIR_INTERFERENCE: Radio 1 Channel 36 interference surge detected: utilization=94.5% noise_floor=-58dBm duty_cycle=88%`.
   ![WLAN Fault](/docs/acceptance/images/w2_wlan_05_fault.png)

3. **Propagation Phase (Evil Twin Rogue AP Broadcast):**
   * An unauthorized rogue AP starts broadcasting a spoofed corporate SSID on Channel 36:
     * Catalyst 9800 WLC alert: `%CATALYST_SEC-4-ROGUE_ALERT: Rogue AP detected on campus RF matrix. rogue_mac=00:14:22:01:23:45 bssid=00:14:22:01:23:45 ssid="Corp-Executive-Secure" channel=36 rssi=-48dBm`.
     * Meraki MR56 Air Marshal alert: `alertType="air_marshal_rogue_detected" clientMac="00:14:22:01:23:45" channel=36`.
   ![WLAN Propagation](/docs/acceptance/images/w2_wlan_06_propagation.png)

4. **Mitigation Phase (CleanAir Channel Switch & Air Marshal Containment):**
   * CleanAir Dynamic Channel Assignment (DCA) shifts legitimate AP radio from congested Channel 36 to pristine Channel 100:
     * `%DOT11-5-CLEANAIR_CHANNEL_SWITCH: Radio 1 shifted from congested Channel 36 to pristine Channel 100 via automated DCA/RRM`.
   * Air Marshal containment triggers active 802.11 deauthentication against the rogue BSSID:
     * `%CATALYST_SEC-5-ROGUE_CONTAINED: Evil-Twin SSID "Corp-Executive-Secure" BSSID 00:14:22:01:23:45 contained via 802.11 deauthentication matrix`.
   ![WLAN Mitigation](/docs/acceptance/images/w2_wlan_07_mitigation.png)

5. **Recovery Phase (RF Spectrum Equilibrium Restored):**
   * On pristine Channel 100, RF health returns to nominal:
     * `%DOT11-6-CLEANAIR_HEALTH: Channel 100 clean, channel utilization=14.2% noise_floor=-92dBm, client SNR=38dB`.
   ![WLAN Recovery](/docs/acceptance/images/w2_wlan_08_recovery.png)

---

## 6. Live Splunk Evidence & Operational Investigation

* **Splunk Query:**
  ```spl
  search index=idx_network_ops netspout_run_id="NS-20260925-11723a84"
  ```
* **Observed Event Count:** **8 / 8 (100.0% completeness)**
* **Evidence Time (T5 - T4):** **11.31 seconds**.

![WLAN Splunk Evidence](/docs/acceptance/images/w2_wlan_09_splunk_evidence.png)

### Answers to Operational Investigation Questions:

1. **Which AP/channel was affected?**  
   `Catalyst-9130AX-AP01` (Radio 1) and `Meraki-MR56-AP01`, on **Channel 36** (5 GHz).
2. **What was baseline channel utilization?**  
   `14.2%` channel utilization with `-92dBm` noise floor and `38dB` client SNR.
3. **What did utilization rise to?**  
   Utilization spiked to **`94.5%`**, with noise floor jumping to `-58dBm` and duty cycle reaching `88%`.
4. **What indicated non-Wi-Fi interference?**  
   CleanAir syslog: `%DOT11-4-CLEANAIR_INTERFERENCE: Radio 1 Channel 36 interference surge detected: utilization=94.5% noise_floor=-58dBm duty_cycle=88% signature="CleanAir Non-Wi-Fi RF Interference Surge on Channel 36"`.
5. **What identified the rogue/evil-twin AP?**  
   Catalyst 9800 WLC alert: `%CATALYST_SEC-4-ROGUE_ALERT: Rogue AP detected on campus RF matrix. rogue_mac=00:14:22:01:23:45 bssid=00:14:22:01:23:45 ssid="Corp-Executive-Secure" channel=36 rssi=-48dBm` and Meraki alert `alertType="air_marshal_rogue_detected"`.
6. **Did DFS/channel reassignment occur?**  
   Yes. Catalyst CleanAir triggered automated dynamic channel reassignment from Channel 36 to Channel 100 (`%DOT11-5-CLEANAIR_CHANNEL_SWITCH`).
7. **Did Air Marshal containment occur?**  
   Yes. The controller and Meraki sensor enforced containment: `%CATALYST_SEC-5-ROGUE_CONTAINED: Evil-Twin SSID "Corp-Executive-Secure" BSSID 00:14:22:01:23:45 contained via 802.11 deauthentication matrix`.
8. **Did RF conditions recover?**  
   Yes. Spectrum normalized on pristine Channel 100: `%DOT11-6-CLEANAIR_HEALTH: Channel 100 clean, channel utilization=14.2% noise_floor=-92dBm`.

### Wireless Semantics & Technical Nuance:
* **Separation of Concerns:** NetSpout cleanly separates RF interference, Evil Twin SSID spoofing, and rogue suppression:
  * Non-Wi-Fi interference -> Elevated noise floor & duty cycle -> Dynamic Channel Assignment.
  * Evil Twin SSID spoofing -> Air Marshal deauthentication containment.
* **Friction Finding (`W2-P2-003`):** The scenario uses the signature text *"CleanAir Dynamic Frequency Selection Channel Reassignment"* during mitigation. In IEEE 802.11 specifications, Dynamic Frequency Selection (DFS) specifically refers to radar detection on DFS channels (52-144). Shifting away from continuous non-Wi-Fi interference is Dynamic Channel Assignment (DCA) / Radio Resource Management (RRM). The scenario should refine its signature label in Wave 3 to prevent minor semantic confusion.

---

## 7. Validation Engine & Ground Truth Audit (Step 5)

* **Validation Status:** **`PASS`**
* **Destination Status:** **`PASS`**
* **Overall Contract Validation:** **`PASS`**

| Rule ID | Rule Name | Contract Criteria | Observed Status | Evidence Detail |
| :--- | :--- | :--- | :---: | :--- |
| `arch_wlan_meraki_catalyst-val-01` | Required Telemetry Emitted | Required sourcetypes & sequence | **PASS** | 8 events verified across CleanAir & Meraki profiles |

![WLAN Validation](/docs/acceptance/images/w2_wlan_10_validation.png)

---

## 8. Final Determination & Metrics

* **Acceptance Determination:** **`PASS WITH FRICTION`**
* **Friction Summary:** Minor wireless semantic terminology: DFS label used for DCA non-Wi-Fi interference mitigation (`W2-P2-003`).
* **Causality Classification:** **`CAUSALLY_MODELED`**
* **Telemetry Fidelity:** **`VERIFIED_FORMAT`**
* **Transport Truth:** **`HEC TRANSPORT`**
* **Total Time-to-Validated-Evidence:** **31.92 seconds**
* **Meaningful User Interactions:** **10**
* **Developer Knowledge Required:** **`NO`**
* **Catalog Maturity Recommendation:** **`REMAIN_E2E_VALIDATED`**
