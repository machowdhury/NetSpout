# NETSPOUT GATE 10.5 — WAVE 2 SEMANTIC RETEST & CERTIFICATION REPORT

**Author:** Independent Product Acceptance Tester  
**Date:** September 2026  
**Environment:** Splunk Enterprise 10.2.7 (`127.0.0.1:8888` HEC / `127.0.0.1:8889` REST)  
**FastAPI Backend:** `http://localhost:8081`  
**React UI:** `http://localhost:8800/en-US/app/netspout/canvas`  
**Scope:** Focused retest of remediated Wave 2 scenarios (`service_provider_cisco`, `arch_wlan_meraki_catalyst`, `arch_man_carrier_ring`).

---

## 1. Executive Summary

During Gate 10 independent product acceptance, three scenarios were evaluated as **PASS WITH FRICTION**:
- `service_provider_cisco` (`W2-P2-001`: Sub-50ms timing truth & BGP convergence distinction)
- `arch_wlan_meraki_catalyst` (`W2-P2-003`: RF interference vs DFS semantics)
- `arch_man_carrier_ring` (`W2-P2-002`: Sub-50ms ring protection timing truth & WTR distinction)
- Global UX (`W2-P3-001`: Insecure TLS default on local Docker endpoints)

Following the implementation of Gate 10.5 semantic closures, this focused retest independently executed all three scenarios against production Docker Splunk with fresh run IDs.

### Retest Determination:
- `service_provider_cisco`: **`CLEAN PASS`** -> Promoted to **`GOLDEN_PATH_CERTIFIED`**
- `arch_wlan_meraki_catalyst`: **`CLEAN PASS`** -> Promoted to **`GOLDEN_PATH_CERTIFIED`**
- `arch_man_carrier_ring`: **`CLEAN PASS`** -> Promoted to **`GOLDEN_PATH_CERTIFIED`**

---

## 2. Retest Evidence & Observability Scorecard

| Scenario ID | Fresh Run ID | Generated | Dispatched | Observed | Completeness | Dest Validation | Overall Validation | Timing Class | Time-to-Evidence |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `service_provider_cisco` | `NS-20260925-457d634a` | 8 | 8 | 8 | **100.0%** | **PASS** | **PASS** | `MODELED` (32ms) | 10.87s |
| `arch_wlan_meraki_catalyst` | `NS-20260925-e0090516` | 8 | 8 | 8 | **100.0%** | **PASS** | **PASS** | `NOT_APPLICABLE` | 10.15s |
| `arch_man_carrier_ring` | `NS-20260925-e802e5ac` | 8 | 8 | 8 | **100.0%** | **PASS** | **PASS** | `MODELED` (38ms) | 11.48s |

---

## 3. First-Time User Semantic Verification (Phase 14 Audit)

### 3.1. Service Provider Network (`service_provider_cisco`)

| Question | Answer from Live Telemetry & UI | Verdict |
| :--- | :--- | :---: |
| **1. What failed?** | Upstream carrier optical transport link HundredGigE0/0/0/1 flapped repeatedly, triggering eBGP hold-timer expiration and BGP neighbor `198.51.100.1` adjacency drop (`%ROUTING-BGP-5-ADJCHANGE`). | **PASS** |
| **2. What protection mechanism reacted?** | Topology-Independent Loop-Free Alternate (TI-LFA) local repair activated immediately in data-plane across backup path HundredGigE0/0/0/2 (`%MPLS-6-TI_LFA_LOCAL_REPAIR`). | **PASS** |
| **3. Is protection timing measured or modeled?** | **MODELED**. Displayed as `MODELED: 32ms` on scenario cards and preview drawers with explicit disclaimer that NetSpout models protocol convergence. | **PASS** |
| **4. What happened to BGP?** | eBGP neighbor dropped, prefix withdrawal was logged downstream, and after transport stabilization, BGP peering re-established to nominal. | **PASS** |
| **5. When did traffic recover?** | Forwarding recovered within sub-50ms via TI-LFA local repair during the fault, and full routing equilibrium recovered in the RECOVER/VALIDATE phase after BGP re-establishment. | **PASS** |

### 3.2. Campus Wireless Network (`arch_wlan_meraki_catalyst`)

| Question | Answer from Live Telemetry & UI | Verdict |
| :--- | :--- | :---: |
| **1. What RF problem occurred?** | Continuous non-Wi-Fi RF frequency interference (video bridge / microwave) saturated Channel 36, driving channel utilization to 94.5% and noise floor to -58dBm (`%DOT11-4-CLEANAIR_INTERFERENCE`). | **PASS** |
| **2. Was radar actually detected?** | **NO**. Telemetry and UI confirm zero radar signatures were detected; DFS was not triggered. | **PASS** |
| **3. Why did the channel change?** | Automated Dynamic Channel Assignment (DCA) / RRM shifted the AP radio from congested Channel 36 to pristine Channel 100 (`%DOT11-5-CLEANAIR_CHANNEL_SWITCH`). | **PASS** |
| **4. What rogue/evil-twin behavior occurred?** | Adversary launched a rogue AP broadcasting spoofed corporate SSID `"Corp-Executive-Secure"` on BSSID `00:14:22:01:23:45` (`%CATALYST_SEC-4-ROGUE_ALERT`). | **PASS** |
| **5. What containment action occurred?** | Meraki Air Marshal and Catalyst WLC suppressed rogue AP via 802.11 deauthentication matrix containment (`%AIRMARSHAL-4-ROGUE_CONTAINMENT`). | **PASS** |

### 3.3. Metro Carrier Ethernet Ring (`arch_man_carrier_ring`)

| Question | Answer from Live Telemetry & UI | Verdict |
| :--- | :--- | :---: |
| **1. What physical failure occurred?** | Terrestrial fiber cut severed 100G optical connection on span `1/1/c1` between Node A and Node B (`%ETH_RING-4-SIGNAL_FAILURE`). | **PASS** |
| **2. What G.8032 event occurred?** | Signal Fail (SF) detected on span; R-APS SF control frames circulated across alternate nodes in < 5ms (`juniper:junos`). | **PASS** |
| **3. What happened to the RPL?** | RPL Owner switch unblocked the Ring Protection Link (RPL) in 38ms, restoring transit forwarding across the healthy arc (`%ETH_RING-4-RPL_UNBLOCK`). | **PASS** |
| **4. Is protection timing measured or modeled?** | **MODELED**. Badged explicitly as `MODELED: 38ms` with clear distinction from empirical optical measurement. | **PASS** |
| **5. What does WTR control?** | Wait-to-Restore (WTR) timer controls post-repair hold stabilization to ensure fiber splice is stable before revertive restoration, preventing flap oscillation. | **PASS** |
| **6. When did revertive restoration occur?** | Upon fiber splice verification and WTR timer expiration in RECOVER phase (`%ETH_RING-5-REVERTIVE_RESTORE`). | **PASS** |

---

## 4. Product KPI Evaluation

- **Wave 2 Baseline Median Time-to-Validated-Evidence:** **32.58 seconds**
- **Focused Retest Time-to-Validated-Evidence:**
  - `service_provider_cisco`: **10.87 seconds**
  - `arch_wlan_meraki_catalyst`: **10.15 seconds**
  - `arch_man_carrier_ring`: **11.48 seconds**
- **Focused Retest Median:** **10.87 seconds**
- **Material Workflow Regression:** **NO**. In fact, workflow speed improved because defaulting `allow_insecure_tls: true` eliminated configuration friction in Step 3.

---

## 5. Certification Decision

All three friction findings (`W2-P2-001`, `W2-P2-002`, `W2-P2-003`) and the configuration friction finding (`W2-P3-001`) are **100% CLOSED**.
- **Developer Knowledge Required:** **`NO`** across all three scenarios.
- **Semantic Clarity:** **`PASS`** across all protocol, wireless, and timing claims.
- **Final Recommendation:** Promote `service_provider_cisco`, `arch_wlan_meraki_catalyst`, and `arch_man_carrier_ring` to **`GOLDEN_PATH_CERTIFIED`**.
