# NETSPOUT INDEPENDENT ACCEPTANCE MASTER SCORECARD
## WAVE 1 SCENARIO PROMOTION EVALUATION

**Audit Date:** 2026-09-25  
**Product Version:** NetSpout Gate 9 Baseline  
**Auditor Persona:** Independent Observability Architect & Security Verification Lead  
**Scope:** Independent product acceptance of three representative Wave 1 scenarios (`mixed_sase_degradation`, `openconfig_mdt_streaming`, `sql_injection`) from the perspective of a first-time user.  

---

## 1. Cross-Scenario Master Scorecard

| Capability / Evaluation Dimension | SASE Cloud Ingress (`mixed_sase_degradation`) | OpenConfig MDT (`openconfig_mdt_streaming`) | SQL Injection (`sql_injection`) |
| :--- | :--- | :--- | :--- |
| **Domain Family** | Cloud / Hybrid Networking (B2) | Network Performance / Assurance (C1) | Application Security / WAF (S1) |
| **User Discovery** | **PASS** (Found via "Network Operations" pill) | **PASS** (Found via "Service Assurance" pill) | **PASS** (Found via "Security & Zero Trust" pill) |
| **Preview Clarity** | **PASS** (Branch to Dual-Cloud SASE + Probes) | **PASS** (Core routing, PE, Leaf distribution) | **PASS** (Perimeter Firewall, Web, Database) |
| **Topology Realism** | **PASS** (C8000V, Prisma, Zscaler, ThousandEyes) | **PASS** (Cisco 8000, Juniper PTX, Cat 9600) | **PASS** (Cisco ASA, NGINX, PostgreSQL) |
| **Scenario Coherence** | **PASS** (Causally modeled end-to-end story) | **PASS** (Buffer saturation to drain cycle) | **PASS** (Perimeter bypass to IPS block) |
| **Dedicated Telemetry** | **PASS** (Zscaler ZIA, ThousandEyes, PAN) | **PASS** (OpenConfig MDT + Cisco Syslog) | **PASS** (ASA Syslog, NGINX KV, Postgres Audit) |
| **Vendor Fidelity** | **PASS** (Authentic vendor payload schemas) | **PASS** (OpenConfig JSON + Cisco RFC 5424) | **PASS** (ASA, NGINX, and pgaudit formats) |
| **HEC Dispatch Reliability** | **100.0%** (9 / 9 HTTP 200 acknowledgments) | **100.0%** (12 / 12 HTTP 200 acknowledgments) | **100.0%** (8 / 8 HTTP 200 acknowledgments) |
| **Splunk Observation** | **100.0%** (9 / 9 in `idx_network_ops`) | **100.0%** (3 in event index, 9 in metric store) | **100.0%** (8 / 8 in `idx_network_ops`) |
| **Unified Evidence Discovery** | **PASS** (Auto-discovered event destination) | **PASS** (Auto-discovered dual event + metric) | **PASS** (Auto-discovered event destination) |
| **Investigation Usability** | **PASS** (All 9 operational questions answered) | **PASS** (All 9 assurance questions answered) | **PASS** (All 10 security questions answered) |
| **Contract Validation Engine** | **PASS** (4 / 4 rules passed: `sase-val-01..04`) | **PASS** (4 / 4 rules passed: `oc-val-01..04`) | **PASS** (4 / 4 rules passed: `sqli-val-01..04`) |
| **Negative Validation** | **PASS** (Tampering triggers validation failure)| **PASS** (Tampering triggers validation failure)| **PASS** (Tampering triggers validation failure)|
| **Failure Integrity** | **PASS** (Verified via controlled failure test) | **PASS** (Verified via controlled failure test) | **PASS** (Verified via controlled failure test) |
| **Generic Fallback Usage** | **ZERO** (`%NETSPOUT-6-INFO: 0`) | **ZERO** (`%NETSPOUT-6-INFO: 0`) | **ZERO** (`%NETSPOUT-6-INFO: 0`) |
| **Developer Knowledge Required**| **NO** (Zero source code inspection needed) | **NO** (Zero source code inspection needed) | **NO** (Zero source code inspection needed) |
| **Transport Semantics** | **PASS** (HTTP HEC Event Transport) | **FRICTION** (HTTP HEC Metric, not native gRPC)| **PASS** (HTTP HEC Event Transport) |
| **Final Acceptance Determination**| **PASS** | **PASS WITH FRICTION** | **PASS** |
| **Maturity Recommendation** | **`GOLDEN_PATH_CERTIFIED`** | **`REMAIN_E2E_VALIDATED`** | **`GOLDEN_PATH_CERTIFIED`** |

---

## 2. Controlled Destination Failure Integrity Test

A live controlled destination failure was executed against NetSpout by configuring an unreachable HEC endpoint (`https://127.0.0.1:9999/services/collector`) during Step 3 (Configure Connection):

* **Fresh Failure Run Correlation ID:** **`NS-20260925-1dbca9c5`**
* **Events Generated:** **9** (Multi-phase simulation engine generated all scenario events in memory)
* **Dispatch Attempted:** **9**
* **Dispatch Succeeded:** **0** (Connection refused on port 9999)
* **Dispatch Failed:** **9** (100% network transport failure accurately captured in manifest)
* **Observed Count:** **0** (Splunk REST query confirmed 0 events indexed)
* **Observation Status:** **`FAILED`**
* **Destination Validation:** **`FAIL`**
* **Overall Contract Validation:** **`FAIL`**

### Evidence Invariant Verification:

$$\text{GENERATED (9)} \neq \text{DISPATCHED (0)} = \text{OBSERVED (0)} \implies \text{VALIDATION (FAIL)}$$

* **Conclusion:** The NetSpout validation engine strictly respects evidence integrity. It **never** falsely certifies a scenario run when required evidence fails to dispatch or index.

![Controlled Failure State](/docs/acceptance/images/w1_failure_state.png)

---

## 3. Generic Fallback Audit

Following user-facing testing, an exhaustive inspection of emitted telemetry was conducted across all three scenarios:

* **`mixed_sase_degradation`:** 9 total events emitted $\rightarrow$ **0 generic `%NETSPOUT-6-INFO` fallback logs** (0.0%).
* **`openconfig_mdt_streaming`:** 12 total events emitted $\rightarrow$ **0 generic `%NETSPOUT-6-INFO` fallback logs** (0.0%).
* **`sql_injection`:** 8 total events emitted $\rightarrow$ **0 generic `%NETSPOUT-6-INFO` fallback logs** (0.0%).
* **Summary:** All 29 generated records across these three scenarios utilize authentic, vendor-specific payload formatters and canonical sourcetypes (`zscaler:zia`, `cisco:thousandeyes:metric`, `pan:threat`, `cisco:dc:nexus9k:syslog`, `cisco:ios:mdt`, `cisco:ios:syslog`, `cisco:asa`, `nginx:plus:kv`, `postgresql:audit`).

---

## 4. Vendor Fidelity & Transport Semantics Review

| Participating Vendor / Source | Telemetry Format | Wire Transport Classification | Transport Details |
| :--- | :--- | :--- | :--- |
| **Zscaler ZIA** | `zscaler:zia` | **MODELED_FORMAT** | HTTP HEC JSON with authentic ZIA transaction fields |
| **Cisco ThousandEyes** | `cisco:thousandeyes:metric` | **MODELED_FORMAT** | HTTP HEC JSON matching ThousandEyes Cloud Agent test schema |
| **Palo Alto Networks** | `pan:threat` | **VERIFIED_FORMAT** | PAN-OS RFC-compliant CSV wire format |
| **Cisco Nexus 9000** | `cisco:dc:nexus9k:syslog` | **VERIFIED_FORMAT** | NX-OS RFC 5424 syslog standard |
| **Cisco IOS / MDT** | `cisco:ios:mdt` | **MODELED_FORMAT** | OpenConfig YANG JSON mapped to native Splunk metric store |
| **Cisco IOS Syslog** | `cisco:ios:syslog` | **VERIFIED_FORMAT** | Cisco IOS RFC 5424 standard syslog |
| **Juniper Junos** | `juniper_junos` / MDT | **MODELED_FORMAT** | OpenConfig YANG JSON mapped to native Splunk metric store |
| **Cisco ASA** | `cisco:asa` | **VERIFIED_FORMAT** | Cisco %ASA-4-106023 standard connection drop syslog |
| **NGINX** | `nginx:plus:kv` | **VERIFIED_FORMAT** | W3C / NGINX Plus key-value access log format |
| **PostgreSQL** | `postgresql:audit` | **VERIFIED_FORMAT** | Standard pgaudit security event format |

### Explicit Distinction: Payload Format vs Transport Protocol
* **Payload Format:** NetSpout achieves high fidelity across all modeled and verified vendor schemas. The telemetry structures, field names, and status progressions mirror real enterprise equipment.
* **Transport Protocol:** All data is dispatched across HTTP Event Collector (HEC). NetSpout does not establish native out-of-band gRPC TCP sessions or MDT UDP streams. The UI and documentation should explicitly identify this distinction so users understand they are evaluating HEC-ingested metric and log streams.

---

## 5. First-Time User Friction Register

| Finding ID | Severity | Scenario | Step | Expected Behavior | Actual Behavior | User Impact / Recommendation |
| :--- | :---: | :--- | :---: | :--- | :--- | :--- |
| **W1-P2-001** | **P2** | `openconfig_mdt_streaming` | Step 1 / Step 2 | Clear distinction that streaming telemetry is delivered via Splunk HEC metric payloads. | UI labels scenario as "OpenConfig MDT Streaming", which could imply native gRPC dial-out. | Add informative badge: *"OpenConfig Payload via Splunk HEC Metric Ingestion"* to prevent protocol confusion. |
| **W1-P3-001** | **P3** | All Scenarios | Step 3 | Self-signed TLS toggle clear for local Docker container. | Unchecked self-signed TLS results in connection failure in local lab. | Keep secure-by-default; add helper tooltip: *"Check this box for local Docker lab testing."* |

* **P0 Findings (Blockers):** `0`
* **P1 Findings (Major Workarounds):** `0`
* **P2 Findings (UX Clarification):** `1`
* **P3 Findings (Minor Inconvenience):** `1`

---

## 6. Platform Generalization Assessment

### 1. Did Gate 9 produce three genuinely usable scenarios?
**YES.** All three scenarios provide compelling, complete, and reproducible operational demonstrations. A user without physical firewalls, SASE gateways, or OpenConfig routers can spin up NetSpout, click through the 5-step workflow, and investigate authentic logs and metrics in Splunk within 60 seconds.

### 2. Did it merely satisfy automated contracts?
**NO.** The incident stories are causally coherent, multi-phase progressions that make sense from network operations, performance assurance, and security perspectives. The investigation questions can be answered strictly by querying the evidence in Splunk.

### 3. Does unified evidence generalize?
**YES.** NetSpout automatically detected single event destinations for SASE and SQL Injection, and correctly discovered dual event + metric destinations for OpenConfig MDT without requiring hardcoded scenario branching.

### 4. Are security semantics defensible?
**YES.** The SQL Injection scenario cleanly differentiates between an initial permitted HTTPS perimeter connection, application-level detection, database query rejection, and firewall IP blacklisting. It avoids teaching the false premise that a detection event equates to a successful breach.

---

## 7. Catalog Maturity Recommendations

In accordance with strict testing protocols:
* **`mixed_sase_degradation`:** **`PASS`** $\rightarrow$ Recommended for future **`GOLDEN_PATH_CERTIFIED`**
* **`openconfig_mdt_streaming`:** **`PASS WITH FRICTION`** $\rightarrow$ Recommended to **`REMAIN_E2E_VALIDATED`**
* **`sql_injection`:** **`PASS`** $\rightarrow$ Recommended for future **`GOLDEN_PATH_CERTIFIED`**
* **Catalog Status During Testing:** Maintained strictly at **`E2E_VALIDATED`**; zero catalog JSON files or application code were modified.
