# NetSpout Gate 13E — Independent Customer Acceptance Report

## 1. Executive Summary & Acceptance Determination

NetSpout Gate 13E Independent Customer Acceptance has been executed using a completely fresh run set without reusing Gate 13D identifiers or evidence artifacts.

### Formal Acceptance Verdict
**`NATIVE_GNMI_ACCEPTED`**

- **Customer Requirement:**
  > “I need to demonstrate a realistic network incident using native gNMI/OpenConfig telemetry from Cisco, Arista, and Juniper devices, correlate it with SNMP, Syslog, and flow evidence where appropriate, send it into Splunk, and investigate the incident without physical network equipment.”
- **Customer Usability Outcome:**
  - Zero P0 Defects
  - Zero P1 Defects
  - Preflight Status: **`READY`** (all 6 checks verified)
  - Workflow Integration: Supported directly via React UI and FastAPI endpoints
  - Wire Payload Purity: **100% Standards-Pure gNMI / Protobuf / HTTP/2**
  - Observation Verification: Validated in Splunk HEC event store (`idx_network_ops`) and metric store (`cisco_mdt_metrics`) via fresh SPL and `| mstats` queries.

---

## 2. 13-Point Customer Acceptance Criteria Evaluation

| # | Customer Acceptance Condition | Verification Method | Result | Evidence File |
|---|---|---|---|---|
| 1 | Discover the appropriate scenario | React UI Step 1 (Choose) catalog search & badges | **MET** | `StepChoose.tsx` |
| 2 | Understand supported telemetry | UI Step 2 (Preview) with fidelity & provenance | **MET** | `StepPreview.tsx` |
| 3 | Distinguish native transport from modeled state | Explicit `NATIVE TRANSPORT / MODELED DEVICE STATE` badges | **MET** | UI & Scorecard |
| 4 | Connect / preflight required dependencies | Unified Preflight API (`/api/native-gnmi/preflight`) checking binaries & ports | **MET** | `scenario_a_scorecard.json` |
| 5 | Execute scenario through normal product workflow | REST POST `/api/scenarios/{id}/run` with `native_gnmi_e2e: true` | **MET** | `test_gate13e_customer_acceptance.py` |
| 6 | Receive real gNMI through external collector | Live external `/opt/homebrew/bin/gnmic` v0.49.0 execution | **MET** | `scenario_a_scorecard.json` |
| 7 | Find event telemetry in Splunk | Indexed in `idx_network_ops` as `netspout:gnmi:event` | **MET** | `scenario_a_scorecard.json` |
| 8 | Find metric telemetry in Splunk | Indexed in `cisco_mdt_metrics` as `netspout:gnmi:metric` | **MET** | `scenario_a_scorecard.json` |
| 9 | Correlate telemetry across phases | Verified across `BASELINE -> DEGRADE -> FAILOVER -> RECOVERY` | **MET** | `scenario_a_scorecard.json` |
| 10 | Understand vendor / path provenance | Grounded public OpenConfig & vendor YANG paths (RFC/public docs) | **MET** | `scenario_c_scorecard.json` |
| 11 | Reconstruct the incident | 10 Splunk investigation queries (SPL & `\| mstats`) provided | **MET** | UI Step 5 (Prove) |
| 12 | Prove recovery | `RECOVERY` phase state asserted in Splunk search output | **MET** | `scenario_a_scorecard.json` |
| 13 | Operate without Python/source knowledge | Pure web UI / REST workflow with zero developer scripts needed | **MET** | Web Application |

---

## 3. Fresh Scenario Acceptance Runs

### Scenario A: `service_provider_cisco`
- **Fresh Run ID:** `run-13e-acc-spc-001`
- **Target Device:** `cisco-asr9k-pe1` (Cisco IOS XR)
- **Validation Rules:** 10 of 10 Passed (**100%**)
- **Events Dispatched / Observed:** 20 / 20 (**100%**)
- **Metrics Dispatched / Observed:** 12 / 12 (**100%**)
- **Observation Completeness:** **100.0%**
- **Evidence Stages Verified:** All 7 stages (`GENERATED -> SERVER_PUBLISHED -> COLLECTOR_RECEIVED -> NORMALIZED -> SPLUNK_DISPATCHED -> SPLUNK_OBSERVED -> VALIDATED`)

### Scenario B: `openconfig_mdt_streaming`
- **Fresh Run ID:** `run-13e-acc-oc-001`
- **Target Device:** `node-cisco8k`
- **Subscription Modes Verified:** `ONCE`, `STREAM/SAMPLE`, `STREAM/ON_CHANGE`
- **Validation Status:** **PASS**
- **Metrics Ingestion:** Full interface octet rates, discard spikes, and carrier transitions observed via `| mstats`.

### Scenario C: `multi_vendor_telemetry`
- **Fresh Run ID:** `run-13e-acc-mv-001`
- **Vendor Profiles Verified:**
  - `CISCO_IOS_XR` (`node-cisco8k`)
  - `CISCO_IOS_XE` (`node-cat-leaf`)
  - `ARISTA_EOS` (`node-arista-spine`)
  - `JUNIPER_JUNOS` (`node-juniper-ptx`)
- **Validation Status:** **PASS**
- **Honesty Guardrail:** Cisco ACI DME MOs correctly declared `UNSUPPORTED_TELEMETRY` without schema fabrication.

---

## 4. Defect Classification

- **P0 (Blocker):** 0
- **P1 (Critical):** 0
- **P2 (Major):** 0
- **P3 (Minor/Cosmetic):** 0

**Conclusion:** Acceptance granted without reservations. Product proceeds directly to documentation polish, release packaging, and final push.
