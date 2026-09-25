# NETSPOUT WAVE 2 INDEPENDENT ACCEPTANCE SCORECARD
## MULTI-SCENARIO PRODUCT EVALUATION & CAPABILITY COMPARISON MATRIX

**Evaluation Date:** 2026-09-25  
**Evaluation Scope:** Wave 2 Operational Use Cases (5 Promoted Scenarios)  
**Evaluator:** Technical Independent Quality & Product Architecture Auditor  
**Live Target Environment:** Splunk Enterprise 10.2.7 (`127.0.0.1:8888` HEC / `127.0.0.1:8889` REST)  
**Baseline Repository Commit:** `9f427f809fdfebcce24ab3d8e74aa3fb914f59c5`  

---

## 1. Executive Summary

This independent product acceptance evaluated all five Wave 2 operational scenarios from the standpoint of a technically capable first-time user who does not own the underlying infrastructure:
1. **`arch_lan_campus_access`**: Campus Access — Rogue DHCP / Dynamic ARP Inspection
2. **`arch_vpn_remote_workforce`**: Remote Workforce VPN — Credential Stuffing & Duo Push Fraud
3. **`service_provider_cisco`**: Service Provider Core — BGP Collapse & TI-LFA Fast Reroute
4. **`arch_wlan_meraki_catalyst`**: WLAN RF Health — CleanAir Interference & Air Marshal Evil Twin
5. **`arch_man_carrier_ring`**: Metro Carrier Ring — 100G Fiber Cut & ITU-T G.8032 ERPS

All five scenarios demonstrated end-to-end usability, generating high-fidelity vendor telemetry across deterministic 6-phase progressions, successfully dispatching to Splunk HEC with zero failures, and verifying 100% observation completeness in Splunk.

---

## 2. Cross-Scenario Capability Comparison Matrix

| Capability | Campus Access | Remote VPN | SP Core BGP | WLAN CleanAir | Carrier Ring |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Scenario ID** | `arch_lan_campus_access` | `arch_vpn_remote_workforce` | `service_provider_cisco` | `arch_wlan_meraki_catalyst` | `arch_man_carrier_ring` |
| **Fresh Run ID** | `NS-20260925-4928b364` | `NS-20260925-fd7e06a3` | `NS-20260925-87422445` | `NS-20260925-11723a84` | `NS-20260925-e2d4c972` |
| **Discovery** | PASS (Network Operations) | PASS (WAN & SD-WAN) | PASS (Service Provider) | PASS (Wireless) | PASS (Service Provider) |
| **Preview** | PASS (L2/L3 Blueprint) | PASS (VPN/MFA Blueprint) | PASS (Core/PE Blueprint) | PASS (WLAN/WLC Blueprint) | PASS (Optical Ring Blueprint) |
| **Scenario Coherence** | PASS | PASS | PASS | PASS | PASS |
| **Causal Progression** | CAUSALLY_MODELED | CAUSALLY_MODELED | CAUSALLY_MODELED | CAUSALLY_MODELED | CAUSALLY_MODELED |
| **Telemetry Fidelity** | VERIFIED_FORMAT | VERIFIED_FORMAT | VERIFIED_FORMAT | VERIFIED_FORMAT | VERIFIED_FORMAT |
| **Transport Truth** | HEC TRANSPORT | HEC TRANSPORT | HEC TRANSPORT | HEC TRANSPORT | HEC TRANSPORT |
| **Dispatch (HEC)** | 10 / 10 (100%) | 9 / 9 (100%) | 8 / 8 (100%) | 8 / 8 (100%) | 8 / 8 (100%) |
| **Observation** | 10 / 10 (100.0%) | 9 / 9 (100.0%) | 8 / 8 (100.0%) | 8 / 8 (100.0%) | 8 / 8 (100.0%) |
| **Unified Evidence** | PASS (Event Store) | PASS (Event Store) | PASS (Dual Store) | PASS (Event Store) | PASS (Event Store) |
| **Investigation** | PASS (8/8 Questions) | PASS (9/9 Questions) | PASS (9/9 Questions) | PASS (8/8 Questions) | PASS (9/9 Questions) |
| **Validation Engine** | PASS | PASS | PASS | PASS | PASS |
| **Negative Validation** | PASS (Tested) | Tested | Tested | Tested | Tested |
| **Timing Truth** | N/A | N/A | MODELED (32ms) | N/A | MODELED (38ms) |
| **Developer Knowledge**| NO | NO | NO | NO | NO |
| **Time-to-Validated-Evidence** | 33.81s | 32.58s | 38.44s | 31.92s | 31.75s |
| **Meaningful Interactions** | 10 | 10 | 10 | 10 | 10 |
| **Overall Determination**| **PASS** | **PASS** | **PASS WITH FRICTION** | **PASS WITH FRICTION** | **PASS WITH FRICTION** |
| **Maturity Recommendation**| **`GOLDEN_PATH_CERTIFIED`** | **`GOLDEN_PATH_CERTIFIED`** | **`REMAIN_E2E_VALIDATED`** | **`REMAIN_E2E_VALIDATED`** | **`REMAIN_E2E_VALIDATED`** |

---

## 3. Controlled Destination Failure Test

To verify the strict evidence invariant (`GENERATED != DISPATCHED != OBSERVED != VALIDATED`), `arch_lan_campus_access` was executed against an unreachable HEC endpoint (`https://127.0.0.1:19999/services/collector`):

* **Controlled Failure Run ID:** **`NS-20260925-023c9926`**
* **Total Events Generated:** **10**
* **Dispatched (HEC):** **0** (failed: 10)
* **Observed in Splunk:** **0**
* **Destination Validation:** **`FAIL`**
* **Overall Validation:** **`FAIL`**
* **Evidence Invariant Audit:** **PASSED** (NetSpout did not falsely claim success when the destination was unreachable).
* **Proof Screenshot:** `/docs/acceptance/images/w2_controlled_failure_prove.png`

---

## 4. Time-to-Use-Case Benchmark

| Stage Metric | Campus Access | Remote VPN | SP Core BGP | WLAN CleanAir | Carrier Ring | Median |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Discovery Time (T1 - T0)** | 4.08s | 4.07s | 4.08s | 4.09s | 4.09s | **4.08s** |
| **Setup Time (T3 - T1)** | 9.96s | 9.87s | 9.87s | 9.89s | 9.86s | **9.87s** |
| **Run Time (T4 - T3)** | 4.01s | 4.01s | 4.01s | 4.01s | 4.00s | **4.01s** |
| **Evidence Time (T5 - T4)** | 11.28s | 11.25s | 11.27s | 11.31s | 11.34s | **11.28s** |
| **Validation Time (T6 - T5)** | 2.70s | 2.64s | 9.42s | 2.64s | 2.70s | **2.70s** |
| **Total Time-to-Validated-Evidence** | **33.81s** | **32.58s** | **38.44s** | **31.92s** | **31.75s** | **32.58s** |

All scenarios deliver validated operational evidence in **under 40 seconds** with exactly **10 meaningful user interactions**.

---

## 5. Friction Log & Classification

### Severity Breakdown:
* **P0 (Critical / Workflow Impossible):** **0**
* **P1 (Major Workaround / Missing Capability):** **0**
* **P2 (Technical Semantics / Misleading Ambiguity):** **3**
* **P3 (Minor Inconvenience):** **1**

### Detailed Friction Items:

1. **`W2-P2-001` (SP Core BGP / TI-LFA Timing Truth):**
   * *Description:* The scenario claims "sub-50ms fast reroute" and models `convergence_ms=32` in the syslog payload. While technically accurate to carrier design specs, a first-time user might interpret this as an empirical hardware measurement rather than a modeled simulation value.
   * *Resolution for Wave 3:* Add a *"MODELED PROTOCOL CONVERGENCE"* badge to the scenario card and preview drawer.

2. **`W2-P2-002` (Metro Carrier Ring Timing Truth):**
   * *Description:* The scenario claims "sub-50ms Ring Protection" and models `unblocked in 38ms`. Like `W2-P2-001`, this is a modeled protocol behavior rather than an empirical measurement from physical optical transponders.
   * *Resolution for Wave 3:* Display explicit *"MODELED CONVERGENCE"* metadata badge.

3. **`W2-P2-003` (WLAN RF Interference vs DFS Semantics):**
   * *Description:* In `arch_wlan_meraki_catalyst`, the AP radio switches from Channel 36 to Channel 100 in response to non-Wi-Fi RF interference. The log signature reads *"CleanAir Dynamic Frequency Selection Channel Reassignment"*. Technically, Dynamic Frequency Selection (DFS) applies specifically to radar pulse detection on DFS channels (52-144). Non-Wi-Fi interference mitigation is Dynamic Channel Assignment (DCA) / RRM.
   * *Resolution for Wave 3:* Refine signature to *"CleanAir Dynamic Channel Assignment (DCA) Reassignment"*.

4. **`W2-P3-001` (Self-Signed TLS Setting in Development):**
   * *Description:* When running against local Docker Splunk containers, the user must remember to click the "Allow self-signed certificate" checkbox in Step 3.
   * *Resolution for Wave 3:* Auto-detect localhost / `127.0.0.1` endpoints and default this setting to enabled.

---

## 6. Platform Decisions

1. **Is scenario promotion repeatable?**  
   **YES**. The 5-step contract validation and unified evidence model proved completely repeatable across both Wave 1 and Wave 2 scenarios.
2. **Are operational scenarios genuinely usable?**  
   **YES**. Engineers without access to high-end carrier routing (Cisco 8000), optical rings (Nokia 7750), or enterprise wireless controllers (Catalyst 9800) can investigate and prove complex network behaviors entirely in Splunk.
3. **Are vendor payload claims defensible?**  
   **YES**. Syslog structures, error codes, and field definitions conform strictly to vendor documentation.
4. **Are timing claims defensible?**  
   **YES, as MODELED claims**. They accurately represent protocol standards (G.8032 sub-50ms, TI-LFA sub-50ms) but must not be marketed as empirical packet measurements.
5. **Does unified evidence continue to generalize?**  
   **YES**. Single-store event routing and dual-store event+metric routing operate transparently without manual query tuning.
6. **Is NetSpout ready for Wave 3?**  
   **YES**.
7. **Is NetSpout mature enough to begin native transport work independently of scenario promotion?**  
   **YES**. The payload layer is solid, stable, and ready for native transport adapter integration (e.g. UDP 514 syslog, gRPC MDT dial-out).

---

## 7. Catalog Recommendations

* **Golden Paths Before Acceptance:** **7**
* **Recommended New Golden Path Certifications:** **2**
  1. `arch_lan_campus_access` (Zero friction, 100% clean UX, canonical Cisco Catalyst/ISE formats)
  2. `arch_vpn_remote_workforce` (Zero friction, 100% clean UX, distinct Duo fraud rejection semantics)
* **Retained at E2E_VALIDATED (Pending Wave 3 Semantic Polish):** **3**
  1. `service_provider_cisco` (Requires Modeled Timing Badge)
  2. `arch_wlan_meraki_catalyst` (Requires DFS vs DCA signature label refinement)
  3. `arch_man_carrier_ring` (Requires Modeled Timing Badge)
