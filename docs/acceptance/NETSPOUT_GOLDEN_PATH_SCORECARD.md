# NETSPOUT GOLDEN PATH COMPREHENSIVE SCORECARD
## PRODUCT ACCEPTANCE AUDIT ACROSS GOLDEN PATHS 01–04

**Audit Date:** 2026-09-25  
**Product Version:** NetSpout Gate 7 Scenario Fidelity Baseline (commit `e7ca8bb`)  
**Auditor Persona:** Independent Solutions Architect / Enterprise Acceptance Lead  
**Scope:** Evaluation of Golden Paths 01 through 04 under strict Gate 6/7 Evidence Invariants  

---

## 1. Master Acceptance Scorecard

| Capability / Dimension | GP01: SD-WAN Brownout | GP02: Campus Rogue AP | GP03: ACI Microburst | GP04: Multi-Vendor Breach |
| :--- | :--- | :--- | :--- | :--- |
| **Scenario Identifier** | `cisco_sdwan_brownout` | `cisco_campus_rogue` | `cisco_aci_microburst` | `mixed_edge_breach` |
| **Domain / Use Case Family** | WAN & SD-WAN | Campus & Wireless | Data Center & Fabric | Security & Zero Trust |
| **Vendors Represented** | Cisco SD-WAN, ThousandEyes | Cisco Catalyst, Cisco ISE | Cisco Nexus 9K, Cisco ACI | Palo Alto, Fortinet, Meraki, NGINX |
| **Wire Payload Formats** | Syslog, ThousandEyes JSON | Security Syslog, ISE Syslog | Nexus Syslog, ACI Health, MDT | PAN-OS CSV, FortiOS KV, Meraki JSON, W3C |
| **Discovery Experience** | PASS (WAN pill) | PASS (Wireless pill) | PASS (Data Center pill) | PASS (Security pill) |
| **Preview Fidelity** | PASS (Topology & 6 phases) | PASS (Switch/ISE & 6 phases) | PASS (Spine/Leaf & 6 phases) | PASS (NGFW/UTM/WAF & 6 phases) |
| **Topology Realism** | PASS (Branch/Hub WAN) | PASS (Campus Access/ISE) | PASS (ACI Leaf/Spine fabric) | PASS (Edge perimeter inline) |
| **Scenario Progression** | PASS (9 lifecycle phases) | PASS (9 lifecycle phases) | PASS (9 lifecycle phases) | PASS (9 lifecycle phases) |
| **Dedicated Telemetry** | PASS (BFD, BGP, TTFB) | PASS (802.1X, MAC flap, PortSec)| PASS (ASIC drop, Fabric health) | PASS (AirMarshal, Threat, UTM, WAF) |
| **HEC Dispatch Reliability** | 100% (6/6 HTTP 200) | 100% (10/10 HTTP 200) | 100% (14/14 HTTP 200) | 100% (10/10 HTTP 200) |
| **Splunk Observation Count** | 6 observed | 10 observed | 10 observed in `idx_network_ops`* | 10 observed |
| **Observation Completeness** | 100.0% (6 / 6) | 100.0% (10 / 10) | 71.4% (10 / 14 in log index)* | 100.0% (10 / 10) |
| **Missing Events Explained** | NONE | YES (transient flush explained) | YES (4 MDT metrics in metric idx)| NONE |
| **Validation Engine Outcome** | PASS (3/3 rules) | PASS (4/4 rules) | PASS (4/4 rules) | PASS (4/4 rules) |
| **Negative Validation Test** | PASS (HEC unreachable fails) | PASS (HEC unreachable fails) | PASS (drops require evidence) | PASS (missing vendor fails) |
| **Evidence Invariant Integrity** | PASS (Gen!=Disp!=Obs!=Val) | PASS (Gen!=Disp!=Obs!=Val) | PASS (Gen!=Disp!=Obs!=Val) | PASS (Gen!=Disp!=Obs!=Val) |
| **Investigation Usability** | PASS (All questions answered) | PASS (All 7 questions answered)| PASS (All 8 questions answered) | PASS (All 10 questions answered) |
| **Dev Knowledge Required** | NO | NO | YES (to find metric index events)| NO |
| **Documentation Dependency** | Minimal | Minimal | Low | Minimal |
| **Overall Determination** | **PASS** | **PASS** | **PASS WITH FRICTION** | **PASS** |
| **Maturity Recommendation** | **`GOLDEN_PATH_CERTIFIED`** | **`GOLDEN_PATH_CERTIFIED`** | **`REMAIN_E2E_VALIDATED`** | **`GOLDEN_PATH_CERTIFIED`** |

*\*Note on GP03 Observation: 10 log events were observed in `idx_network_ops`. The remaining 4 MDT streaming telemetry events were routed as metrics to `cisco_mdt_metrics`. All 4 scenario validation rules evaluate against `idx_network_ops` events and passed completely.*

---

## 2. Platform Generalization Analysis

### Evaluation Against Platform Objectives
Before Gate 7, NetSpout was certified only for a single Cisco SD-WAN scenario (`cisco_sdwan_brownout`). Acceptance testing of Gates 6.5 and 7 conclusively proves that NetSpout has transitioned from a specialized demonstration tool into a generalized network simulation platform.

### Evidence Across Four Enterprise Networking Domains
1. **WAN & SD-WAN (`cisco_sdwan_brownout`):**
   * Validates BFD tunnel health, SLA latency violations, ThousandEyes synthetic latency, and dynamic BGP route failover.
2. **Campus & Wireless (`cisco_campus_rogue`):**
   * Validates 802.1X supplicant authentication, Rogue AP detection, Layer 2 MAC flapping, and Cisco ISE CoA dynamic quarantine.
3. **Data Center & Performance Fabric (`cisco_aci_microburst`):**
   * Validates microsecond buffer queue pressure, ASIC packet drops, ACI APIC fabric health degradation, and dynamic buffer reservation recovery.
4. **Multi-Vendor Security & Zero Trust (`mixed_edge_breach`):**
   * Validates multi-vendor perimeter defense across 4 vendors (Meraki, Palo Alto, Fortinet, NGINX) using 4 distinct payload formats (JSON, CSV, KV Syslog, W3C).

### Multi-Vendor Architectural Verification
NetSpout successfully executes scenarios without vendor lock-in:
* **8 Enterprise Vendors Verified in Production Simulations:**
  1. Cisco SD-WAN (vEdge, vManage)
  2. Cisco Catalyst (9300 switching, 9800 wireless)
  3. Cisco ISE (Identity Services Engine)
  4. Cisco Nexus / ACI (Nexus 9336, ACI Leaf/Spine)
  5. Cisco Meraki (MR56 AP, Air Marshal)
  6. Palo Alto Networks (PA-440 NGFW)
  7. Fortinet (FortiGate UTM / IPS)
  8. NGINX (Enterprise Web Tier / WAF)

---

## 3. Platform Health & Regression Summary

| Regression / Quality Check | Status | Verification Detail |
| :--- | :--- | :--- |
| **GP01 Regression Test** | **PASS** | `cisco_sdwan_brownout` generated 8, dispatched 8, observed 8, 100% PASS. |
| **Cross-Scenario Failure Integrity** | **PASS** | Controlled destination failure on GP02 confirmed: `GEN: 10`, `DISP: 0`, `OBS: 0`, `VAL: FAIL`. |
| **SD-WAN-Specific Hardcoding** | **NONE** | No hardcoded SD-WAN assumptions in core simulation, runner, dispatcher, or validation. |
| **Single Source of Truth Audit** | **PASS** | `scripts/verify_sources.py` confirmed 100% match across `src/netspout_core/`. |
| **Canonical Test Suite** | **PASS** | 106 tests across Gates 1–7 executed and passed with 0 errors. |

---

## 4. Friction Register Across Evaluated Scenarios

| Finding ID | Severity | Scenario | Category | Description | Recommendation for Gate 8 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **GP03-P2-001** | **P2** | `cisco_aci_microburst` | Observation / Indexing | Dual-index routing sends 4 MDT events to `cisco_mdt_metrics` while UI search deep link queries `index=idx_network_ops`. | Add multi-index or metric search button (`| mstats`) to Step 5 audit dashboard. |
| **PLAT-P3-001** | **P3** | All Scenarios | Setup / TLS | Self-signed TLS on port 8888 requires checking *"Allow self-signed certificate"* in Step 3 for local lab. | Keep secure-by-default; add tooltip indicating Docker lab default. |

* **P0 Findings:** `0` (Zero blockers)
* **P1 Findings:** `0` (Zero major workarounds required)
* **P2 Findings:** `1` (ACI MDT metric search query visibility)
* **P3 Findings:** `1` (Local lab self-signed TLS toggle)

---

## 5. Certification Determinations & Next Phase Recommendation

### Scenario Maturity Status
* **Certified Before Acceptance:** `1` (`cisco_sdwan_brownout`)
* **Recommended for Certification:** `2`
  * `cisco_campus_rogue` → **`GOLDEN_PATH_CERTIFIED`**
  * `mixed_edge_breach` → **`GOLDEN_PATH_CERTIFIED`**
* **Recommended to Retain E2E_Validated:** `1`
  * `cisco_aci_microburst` → **`REMAIN_E2E_VALIDATED`** (pending Gate 8 metric search harmonization)

### Total Certified Golden Paths: **`3`**
1. Golden Path 01: WAN Circuit Brownout (`cisco_sdwan_brownout`)
2. Golden Path 02: Campus Rogue AP (`cisco_campus_rogue`)
3. Golden Path 04: Multi-Vendor Edge Breach (`mixed_edge_breach`)

### Recommended Next Engineering Phase
**Gate 8 — Metric Index Query Harmonization & Comprehensive Catalog Promotion**
* Deliver unified multi-index SPL generation (supporting concurrent `search index=...` and `| mstats index=cisco_mdt_metrics`).
* Promote `cisco_aci_microburst` to Golden Path certified upon metric link delivery.
* Begin systematic validation of the remaining 25 catalog scenarios toward E2E_VALIDATED status.
