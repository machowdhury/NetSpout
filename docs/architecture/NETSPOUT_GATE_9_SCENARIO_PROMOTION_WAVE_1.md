# NetSpout Gate 9: Scenario Promotion Wave 1 Architecture Specification

**Status:** APPROVED FOR IMPLEMENTATION  
**Gate:** Gate 9 — Systematic Scenario Promotion Wave 1  
**Maturity Target:** `E2E_VALIDATED`  
**Prerequisites:** Gate 8 Unified Evidence Discovery (GP01–GP04 Certified Baseline)

---

## 1. Executive Summary

NetSpout has achieved complete Golden Path certification across four primary use cases:
1. **GP01** `cisco_sdwan_brownout` (WAN / SD-WAN) — `GOLDEN_PATH_CERTIFIED`
2. **GP02** `cisco_campus_rogue` (Campus / Wireless) — `GOLDEN_PATH_CERTIFIED`
3. **GP03** `cisco_aci_microburst` (Datacenter / Performance) — `GOLDEN_PATH_CERTIFIED`
4. **GP04** `mixed_edge_breach` (Multi-Vendor / Security) — `GOLDEN_PATH_CERTIFIED`

Gate 9 initiates **Systematic Scenario Promotion**. The core objective is to expand product depth rather than breadth by systematically promoting exactly **FIVE** existing NetSpout scenarios from `FORMAT_VALIDATED` / `CONTRACTED` to `E2E_VALIDATED`.

### Promotion Guardrails
* **No New Scenarios:** All 5 promoted scenarios exist in the audited 29-scenario catalog.
* **No Vendor Expansion:** Strict containment within the audited 36 canonical vendors.
* **No Scenario-Specific Runner Architecture:** Strict reuse of `ScenarioRunner`, `TopologyGraph`, `SplunkLogEngine`, `TelemetryDispatcher`, `UnifiedEvidenceDiscovery`, and `ValidationEngine`.
* **Zero Generic Fallback:** Total elimination of `%NETSPOUT-6-INFO` generic fallback logs from essential proof telemetry for the 5 selected scenarios.
* **Maturity Boundary:** Promoted scenarios reach `E2E_VALIDATED`. They are NOT promoted to `GOLDEN_PATH_CERTIFIED` until independent customer acceptance testing in subsequent gates.

---

## 2. Scenario Evaluation & Selection Matrix

A comprehensive audit of the remaining 25 scenarios evaluated domain coverage, customer operational pain, log formatter availability, and topological alignment.

| Scenario ID | Domain Category | Code | Ecosystem | Formatters Available | Selected? | Selection Rationale |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `mixed_sase_degradation` | Cloud / Hybrid Networking | `MIXED-B2` | `mixed_vendor` | Zscaler, Palo Alto, ThousandEyes, Nexus | **YES (1/5)** | Real-world cloud SWG/SASE SSL inspection bottleneck with active synthetic assurance. |
| `mixed_backbone_optical` | Core / SP Optical | `MIXED-B3` | `mixed_vendor` | Nokia SR-OS, Juniper Junos, Arista IPFIX | **YES (2/5)** | Critical sub-50ms MPLS RSVP-TE Fast Reroute (FRR) triggered by DWDM optical LOS. |
| `openconfig_mdt_streaming` | Performance / Assurance | `PERF-C1` | `both` | Cisco MDT, gNMI OpenConfig, Arista IPFIX | **YES (3/5)** | Proves dual-store streaming telemetry into `cisco_mdt_metrics` and `idx_network_ops`. |
| `sql_injection` | Firewall / App Security | `SEC-S1` | `both` | Cisco ASA, Nginx WAF, PostgreSQL Audit | **YES (4/5)** | Validates L7 application attack detection vs bypass exfiltration to database audit. |
| `ddos_attack` | WAN / Perimeter Defense | `SEC-D1` | `both` | Cisco ASA, F5 Big-IP, Nginx, Palo Alto | **YES (5/5)** | High-frequency TCP SYN flood mitigation via ASA embryonic limits and F5 LTM. |

### Top 5 Deferred Scenarios (Wave 2 Backlog)
1. **`arch_vpn_remote_workforce`**: Remote access VPN with Cisco AnyConnect and Duo Push MFA. Deferred pending multi-factor challenge-response simulator engine.
2. **`arch_can_multi_building`**: Multi-building campus backbone. Deferred pending Catalyst Center assurance graph synchronization engine.
3. **`arch_man_carrier_ring`**: Metro optical ring with G.8032 ERPS. Deferred pending ERPS ring-state-machine simulator.
4. **`service_provider_cisco`**: All-Cisco carrier core. Redundant with `mixed_backbone_optical` in Wave 1.
5. **`lateral_movement`**: Ransomware lateral movement (Port 445 SMB). Deferred to Wave 2 security focus; `sql_injection` provides clearer perimeter vs backend validation in Wave 1.

---

## 3. Wave 1 Selected Scenarios Detail

### 3.1. `mixed_sase_degradation` (SASE Cloud Ingress Degradation & Synthetic Validation)
* **Problem Statement:** A remote workforce accessing cloud ERP/SaaS applications encounters severe degradation. A cloud Secure Web Gateway (Zscaler ZIA) experiences TLS inspection latency surges, causing session queuing at the on-premise perimeter (Palo Alto Prisma SD-WAN).
* **Topology:** `mixed_sase` (Zscaler CloudEdge $\rightarrow$ Palo Alto Prisma $\rightarrow$ Nexus DC Core $\rightarrow$ SaaS ERP Target).
* **Telemetry Emitted:**
  * `zscaler:zia`: Cloud proxy latency metrics (28ms baseline $\rightarrow$ 450ms degraded $\rightarrow$ 32ms restored).
  * `cisco:thousandeyes:metric`: HTTP TTFB synthetics isolating hop latency to cloud proxy.
  * `pan:threat`: Palo Alto Prisma queue congestion and dynamic cloud breakout reroute.
  * `cisco:dc:nexus9k:syslog`: DC core transit buffer status.
* **Validation Rules:**
  1. `sase-val-01`: `zscaler:zia` log presence ($\ge 1$).
  2. `sase-val-02`: Degradation status detected (`status == "degraded"`).
  3. `sase-val-03`: ThousandEyes synthetic metric presence ($\ge 1$).
  4. `sase-val-04`: Restoration status verified (`status == "restored"`).

---

### 3.2. `mixed_backbone_optical` (Multicast/MPLS Backbone Optical Carrier Shift & FRR)
* **Problem Statement:** A terrestrial fiber cut drops a 100G coherent DWDM optical wavelength on a Nokia 7750 SR-12 transport node. Juniper MX960 PE routers detect carrier Loss of Signal (LOS) and trigger sub-50ms MPLS RSVP-TE Fast Reroute (FRR) facility bypass switchover. Arista EOS leaf switches track flow redirection via IPFIX.
* **Topology:** `mixed_optical` (Nokia 7750 SR-12 $\rightarrow$ Juniper MX960 PE $\rightarrow$ Arista 7280R Leaf).
* **Telemetry Emitted:**
  * `nokia:sros:syslog`: `%ROUTING-3-OPTICAL_LOS` alarm on 100G port `1/1/c1`.
  * `juniper:junos`: `RPD_MPLS_LSP_CHANGE` switchover from primary next-hop to bypass next-hop.
  * `arista:flow:ipfix`: JSON flow record with `reroute_flag=1` and egress interface divert.
* **Validation Rules:**
  1. `optical-val-01`: Nokia SR-OS syslog presence ($\ge 1$).
  2. `optical-val-02`: Juniper Junos RSVP-TE FRR switchover logged ($\ge 1$).
  3. `optical-val-03`: Arista EOS IPFIX telemetry record presence ($\ge 1$).
  4. `optical-val-04`: Optical carrier restoration verified (`status == "restored"`).

---

### 3.3. `openconfig_mdt_streaming` (OpenConfig MDT Streaming & Telemetry Assurance)
* **Problem Statement:** High-capacity backbone routers stream real-time OpenConfig YANG telemetry (interface counters, queue depth, CPU) via gNMI / Model-Driven Telemetry (MDT) to Splunk. A traffic surge causes interface buffer queues to build, triggering dynamic rate-shaping.
* **Topology:** `openconfig_core` (Cisco 8000 Core $\rightarrow$ Juniper PTX PE $\rightarrow$ Arista 7280R Spine $\rightarrow$ Catalyst 9600 Leaf).
* **Dual-Store Telemetry:**
  * Event Store (`idx_network_ops`): `cisco:ios:mdt` event notifications, `arista:telemetry:json`.
  * Metric Store (`cisco_mdt_metrics`): High-frequency metric points (`metric_name:queue_depth`, `metric_name:buffer_utilization`, `metric_name:in_octets`) stamped with `netspout_run_id`.
* **Validation Rules:**
  1. `oc-val-01`: MDT telemetry records emitted ($\ge 1$).
  2. `oc-val-02`: Core buffer congestion detected (`status == "degraded"`).
  3. `oc-val-03`: Telemetry streaming active (`action == "allowed"`).
  4. `oc-val-04`: Core interface restoration verified (`status == "restored"`).

---

### 3.4. `sql_injection` (SQL Injection / Application Perimeter Breach)
* **Problem Statement:** An attacker launches OWASP SQL injection attacks against an enterprise web application. Cisco ASA firewall inspects HTTP payloads inline and drops malicious requests (`action="blocked"`). In bypassed topology mode, the attack penetrates the web tier and triggers PostgreSQL security audit alerts.
* **Topology:** `bypassed` / `secure` (External Client $\rightarrow$ Cisco ASA $\rightarrow$ F5 LTM $\rightarrow$ NGINX $\rightarrow$ PostgreSQL).
* **Telemetry Emitted:**
  * `cisco:asa`: `%ASA-4-106023` TCP packet deny on perimeter inspection.
  * `nginx:plus:kv`: Inbound HTTP request query string logging.
  * `postgresql:audit`: Database query audit log alerting on SQL injection syntax.
* **Validation Rules:**
  1. `sqli-val-01`: Cisco ASA firewall security log emitted ($\ge 1$).
  2. `sqli-val-02`: PostgreSQL audit threat log emitted ($\ge 1$).
  3. `sqli-val-03`: Threat packet drop/blocked action verified (`action == "blocked"`).
  4. `sqli-val-04`: Database security posture restored (`status == "restored"`).

---

### 3.5. `ddos_attack` (Distributed Denial of Service TCP SYN Flood)
* **Problem Statement:** A botnet floods the perimeter with 50,000 SYN packets/sec targeting the corporate VIP. Cisco ASA detects embryonic connection limit exhaustion, activates TCP Intercept SYN cookies, and drops unauthenticated SYN bursts. F5 LTM isolates the server pool.
* **Topology:** `secure` (External Client $\rightarrow$ Cisco ASA $\rightarrow$ F5 LTM $\rightarrow$ NGINX Web Tier $\rightarrow$ PostgreSQL).
* **Telemetry Emitted:**
  * `cisco:asa`: `%ASA-2-106017` embryonic connection limit exceeded, TCP Intercept engaged.
  * `f5:bigip:ltm`: Virtual Server SYN flood rate-limiting alert.
  * `nginx:plus:kv`: Upstream connection queue alert.
* **Validation Rules:**
  1. `ddos-val-01`: Cisco ASA perimeter defense log emitted ($\ge 1$).
  2. `ddos-val-02`: Volumetric SYN flood blocked (`action == "blocked"`).
  3. `ddos-val-03`: F5 Big-IP load balancer SYN protection logged ($\ge 1$).
  4. `ddos-val-04`: Service restoration verified (`status == "restored"`).

---

## 4. Elimination of Generic Fallback

Previously, unspecialized scenarios routed through the general fallback branch in `scenario_runner.py`:
```python
raw_log = f"{now_ts} {switch_node.name} %NETSPOUT-6-INFO: phase={phase} status={status} sourcetype={st}"
```
In Gate 9, all 5 Wave 1 scenarios have dedicated generators implementing realistic phase progressions and real vendor formatters (`format_zscaler_zia_log`, `format_nokia_sros_log`, `format_juniper_junos_log`, `format_arista_ipfix_log`, `format_mdt_stream`, `format_cisco_asa_log`, `format_nginx_web_log`, `format_postgres_db_log`, `format_f5_lb_log`).

Essential proof telemetry for all 5 scenarios contains **0% generic fallback logs**.

---

## 5. Negative Validation Design

Each of the 5 scenarios is verified under positive and negative conditions:
* **Missing Telemetry Test:** Suppressing key sourcetypes (e.g. omitting `zscaler:zia` or `nokia:sros:syslog`) results in deterministic `FAIL` for `COUNT_THRESHOLD` rules.
* **Corrupted Status Test:** Inverting status (e.g. omitting `degraded` or `restored`) results in deterministic `FAIL` for `EVENT_EXISTS` rules.
* **Corrupted Action Test:** Altering firewall action from `blocked` to `allowed` results in deterministic `FAIL` for security enforcement rules.

---

## 6. Verification & Acceptance Architecture

Validation utilizes the unified evidence discovery engine established in Gate 8:
$$\text{Completeness} = \frac{\text{Total Observed Events \& Metrics}}{\text{Total Dispatched Records}} \ge 95\%$$

The promotion criteria require:
1. `contract_validation == "PASS"` across all 4 verification rules per scenario.
2. `observation_completeness_pct >= 95%` against live Splunk.
3. Zero `%NETSPOUT-6-INFO` logs in essential proof telemetry.
4. Clean regression across all 4 certified Golden Paths.
