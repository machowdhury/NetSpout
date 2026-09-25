# NETSPOUT MASTER SPECIFICATION RECONCILIATION & PRODUCT GAP ANALYSIS
## ARCHITECTURAL AUDIT & STRATEGIC ROADMAP (GATE 6.5)

**Document Reference:** `NETSPOUT-ARCH-GATE-06.5`  
**Date:** 2026-09-25  
**Review Type:** Read-Only Architecture & Product Review  
**Specification Under Review:** `netspout_master_specification_simulation_engine.md` (Downloads/v1.0)  
**Authoritative Baseline:** NetSpout Repository (Gates 1–6 Completed, 81/81 Tests Passing)  
**Status:** **APPROVED FOR REVIEW** (Zero Code Changes, Read-Only Audit)

---

## 1. Executive Summary

This document reconciles the current NetSpout production-grade implementation against the input document `netspout_master_specification_simulation_engine.md`. 

NetSpout has successfully navigated Gates 1 through 6, achieving:
* A consolidated single Python source of truth in `src/netspout_core/`.
* A canonical 8-file JSON catalog system (`netspout/catalog/`).
* A modern React 18 / TailwindCSS / Vite 5-step workflow SPA (`FiveStepWorkflow.tsx`, `StepChoose.tsx`, `StepPreview.tsx`, `StepConnect.tsx`, `StepRun.tsx`, `StepProve.tsx`) embedded within a certified Splunk application (`netspout.spl`).
* Complete mathematical evidence integrity and truthful delivery counters verified live against Splunk Enterprise (`NS-20260925-c521cd8b`, Golden Path 01 PASS).

The **Master Specification** presents a compelling vision for expanding NetSpout's domain reach: 72 vendors, 55 master scenarios spanning 18 distinct network types (from BAN/PAN and 5G Cellular to SCADA/ICS and Avionics), multi-vendor blueprints (BP-01, BP-02, BP-03), and realistic multi-stage breach chains. 

However, the master specification is an **external concept specification**, not production truth. Structurally, it proposes a separate parallel engine architecture (Jinja2 template hydrator, YAML loader, multi-threaded scheduler, and legacy Splunk Simple XML dashboards) that directly conflicts with the consolidated canonical architecture established in Gates 1–6. Furthermore, it references fictitious Splunkbase Technology Add-ons that do not exist.

This audit establishes an authoritative reconciliation: extracting high-value scenarios, templates, and multi-vendor blueprints while firmly rejecting parallel engine duplication and preserving NetSpout's single source of truth.

---

## 2. Current NetSpout Reality: Authoritative Inventory

Treating the repository and completed Gate 1–6 evidence as authoritative:

| Subsystem | Current Repository State | Maturity Status |
| :--- | :--- | :---: |
| **Canonical Core** | Centralized in `src/netspout_core/` (15 modules: `models.py`, `graph_engine.py`, `log_engine.py`, `scenario_runner.py`, `snmp_engine.py`, `gnmi_engine.py`, `fault_injection_engine.py`, `telemetry_dispatcher.py`, `cisco_sample_provider.py`, `spl_engine.py`, `use_case_repo.py`, `noc_soc_metrics.py`, `catalog.py`, `vendor_catalog.py`, `__init__.py`). | **IMPLEMENTED & TESTED** |
| **Catalogs** | 8 canonical JSON files in `netspout/catalog/` (`aliases.json`, `device_types.json`, `samples.json`, `scenarios.json`, `sourcetypes.json`, `telemetry_protocols.json`, `topologies.json`, `vendors.json`). | **IMPLEMENTED & AUDITED** |
| **Vendors** | **36 vendors** declared in `vendors.json`. 8 verified/modeled with high-fidelity formatting; 28 catalog-only or generic fallback. | **PARTIAL** |
| **Sourcetypes** | **263 sourcetypes** cataloged across Cisco, Palo Alto, Fortinet, Arista, Juniper, F5, SC4SNMP, etc. | **IMPLEMENTED** |
| **Scenarios** | **29 scenarios** in `scenarios.json`. 6 explicitly modeled in `scenario_runner.py`; 23 utilize contract-based generic synthesis. | **PARTIAL** |
| **Use Cases** | **39 use cases** presented in Step 1 (29 scenario-bound + 10 pre-built in `use_case_repo.py`). | **IMPLEMENTED** |
| **Topology Engine** | `graph_engine.py` (`TopologyGraph` with nodes, edges, interfaces, subnets, VLANs, VRFs, security zones, Dijkstra routing, link degradation). 28 topologies cataloged in `topologies.json`. | **IMPLEMENTED & TESTED** |
| **Scenario Contracts** | Gate 4 machine-readable contracts (`ScenarioContract`, `ValidationRule`, `GroundTruthRecord`). Evaluates `EVENT_EXISTS`, `COUNT_THRESHOLD`, `FIELD_VALUE`, `STATE_TRANSITION`, `SPL_QUERY`. | **IMPLEMENTED & TESTED** |
| **Telemetry Dispatchers** | `telemetry_dispatcher.py`: Splunk HEC (JSON `/event`, raw text `/raw`), Syslog socket (UDP port 514, TCP port 514), OTel Collector (`/v1/logs`, `/v1/metrics`), Telegraf Influx line protocol, SC4SNMP HEC traps. | **IMPLEMENTED & TESTED** |
| **Splunk Integration** | Packaged Splunk application `netspout.spl` (1.37 MB) with custom REST handler `/services/datablaster/execute` and embedded React SPA. Tested live on Splunk Enterprise 9.4.0. | **E2E VERIFIED** |
| **Frontend UI** | Modern React 18 SPA (`FiveStepWorkflow.tsx`, `CanvasOrchestrator.tsx`, `StepChoose`, `StepPreview`, `StepConnect`, `StepRun`, `StepProve`). Built with Vite & TailwindCSS. | **E2E VERIFIED** |
| **Connection Handling** | Canonical 5-state model (`NOT_CONFIGURED`, `CONFIGURED`, `REACHABLE`, `VERIFIED`, `ERROR`) with latency measurement, reachability probe, and preflight canary event. | **E2E VERIFIED** |
| **Run Correlation** | Stamped immutable attributes on all events: `netspout_run_id`, `netspout_scenario_id`, `netspout_phase`, `netspout_event_id`, `netspout_ground_truth`. | **E2E VERIFIED** |
| **Evidence Semantics** | Truthful counters (`dispatch_succeeded`, `dispatch_failed`, `observed_count`). Active Splunk REST observation polling with backoff. 5 strict mathematical invariants. | **E2E VERIFIED** |
| **Test Suites** | 81 unit & integration tests passing (100%) across Gates 1–6 (`test_gate1_runtime.py` through `test_gate6_integrity.py`). | **E2E VERIFIED** |
| **Golden Path Certification** | Golden Path 01 (*SD-WAN Brownout*) certified with 16/16 acceptance criteria satisfied (`GOLDEN_PATH_01_SDWAN_BROWNOUT_RETEST.md`). | **E2E VERIFIED** |

---

## 3. Master Specification Summary

The master specification (`netspout_master_specification_simulation_engine.md`) specifies:
* **72 Vendors**: 36 Core Infrastructure, 24 Security/NDR, 12 OT/SCADA/Medical.
* **55 Master Scenarios**: Across 5 geographic/architectural sections:
  1. Geographic & Scale-Based Networks (Scenarios 1–17: BAN, PAN, LAN, WLAN, CAN, MAN, WAN, SAN, WLAN-Mesh).
  2. Enterprise & Architecture-Driven Networks (Scenarios 18–27: SD-WAN, SDN, IBN, ZTNA, VPN, Hybrid Cloud).
  3. Service Provider & Telco Infrastructure (Scenarios 28–34: GPON, Core MPLS, SR-MPLS, Carrier Ethernet, CDN, SS7/Diameter).
  4. Mobile & Cellular Networks (Scenarios 35–44: 2G/3G, 4G LTE, 5G NSA, 5G SA, Private 5G, RAN, O-RAN).
  5. Specialized Industry & OT (Scenarios 45–55: Modbus/TCP, SCADA DNP3, Profinet, Smart Grid AMI, IEEE 1588, PACS DICOM, HL7, POS DNS Tunneling, AFDX Avionics, CAN Bus, Wi-SUN).
* **Multi-Vendor Correlated Breach Chains**:
  * `SEC-01`: Cobalt Strike C2 DNS Tunneling & Perimeter Evasion (Infoblox + Catalyst + Palo Alto + ExtraHop).
  * `SEC-02`: Ransomware Lateral Movement via SMB Exploitation (Catalyst + Fortinet + Vectra + Zeek).
* **10 Production-Grade Event Templates**: Cisco IOS-XE, Meraki Webhook, DNAC Webhook, ThousandEyes Webhook, Cisco MDT JSON, Palo Alto CSV, Fortinet Syslog, Zeek SSL JSON, IPFIX JSON, SNMPv2c Trap.
* **Proposed App Architecture**: Jinja2 hydrator (`hydrator.py`), YAML loader (`scenario_loader.py`), thread pool scheduler (`scheduler.py`), socket emitters, Simple XML dashboards (`netspout_catalog.xml`, etc.).
* **Target Audience**: Turnkey LLM build prompt for Cursor / Claude 3.5 Sonnet to scaffold a greenfield implementation.

---

## 4. Capability Reconciliation Matrix

| Master Spec Capability | Current NetSpout Implementation | Classification | Reconciliation Analysis & Disposition |
| :--- | :--- | :---: | :--- |
| **72-Vendor Ecosystem** | 36 vendors in `vendors.json`. | **PARTIAL** | The 36 core IT and security vendors are modeled. The remaining 36 (OT, SCADA, Avionics, Cellular) are currently unmodeled. Expand catalog metadata selectively; do not inflate vendor claims without telemetry support. |
| **55-Scenario Matrix** | 29 scenarios in `scenarios.json` + 10 pre-built use cases. | **PARTIAL** | 1 scenario is Golden-Path-Certified (`cisco_sdwan_brownout`), 5 are explicitly modeled in Python, and 23 use contract synthesis. The 55 master scenarios provide a rich backlog for future scenario expansions. |
| **Correlated Breach Chains (SEC-01, SEC-02)** | Modeled in `lateral_movement` and `mixed_edge_breach`. | **EXISTS** | NetSpout already models lateral movement (Port 445 SMB) and distributed edge breach. Can be upgraded to match the master spec's 4-vendor timeline. |
| **Multi-Vendor Topologies (BP-01, BP-02, BP-03)** | Modeled in `graph_engine.py` (`get_cisco_campus_topology`, `get_cisco_sdwan_topology`, `get_cisco_aci_topology`, `get_mixed_edge_topology`). | **EXISTS** | Topology graph engine already supports multi-tier, multi-vendor node graphs with edge link degradation and dynamic Dijkstra routing. |
| **Jinja2 Hydrator Engine (`hydrator.py`)** | `log_engine.py` (`SplunkLogEngine`) with deterministic formatting. | **DUPLICATE** | NetSpout's `SplunkLogEngine` generates high-fidelity, deterministic strings and JSON without external Jinja2 file-system overhead. Introducing `hydrator.py` would create duplicate template logic. |
| **YAML Scenario Loader (`scenario_loader.py`)** | Canonical JSON catalogs loaded by `catalog.py` & `ScenarioContract`. | **DUPLICATE** | NetSpout uses Pydantic V2 validated JSON contracts (`ScenarioContract`, `ValidationRule`). YAML files are unnecessary duplicates. |
| **ThreadPool Scheduler (`scheduler.py`)** | `scenario_runner.py` (`ScenarioRunner`) 9-phase lifecycle. | **DUPLICATE** | `ScenarioRunner` already orchestrates deterministic phase transitions, time-dilation modes (TEST, ACCELERATED, REALTIME), and cancellation. |
| **Socket Emitters (`syslog_emitter.py`, `hec_emitter.py`)** | `telemetry_dispatcher.py` (`TelemetryDispatcher`). | **DUPLICATE** | Dispatcher already handles HEC JSON, HEC raw text, Syslog UDP/TCP sockets, OTel OTLP, Telegraf, and SNMP traps. |
| **Splunk Simple XML Dashboards (`netspout_catalog.xml`)** | React 18 SPA (`FiveStepWorkflow.tsx`, `StepChoose.tsx`, etc.). | **CONFLICTS_WITH_CURRENT_ARCHITECTURE** | NetSpout completely deprecated Simple XML in Gate 5 in favor of a responsive, modern React SPA. Reintroducing Simple XML would be an architectural regression. |
| **Splunkbase TA Compliance** | Built into `log_engine.py` field mappings and `sourcetypes.json`. | **EXISTS** | Events parse cleanly against official Cisco, Palo Alto, and Fortinet TAs as verified in Gate 6. |
| **Fictitious Splunkbase TAs** | None in NetSpout. | **QUESTIONABLE** | Master spec references non-existent TAs (e.g. `Splunk Add-on for Medical Devices`, `Splunk Add-on for Connected Vehicles`). Rejected. |

---

## 5. Authoritative Telemetry Protocol Capability Matrix

| Telemetry Protocol | Cataloged | Generated | Native Wire Format | Dispatchable | Observable in Splunk | Validatable | E2E Tested | Current Technical Reality |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **Splunk HEC Event (JSON)** | YES | YES | YES | YES | YES | YES | **YES** | Native HTTP POST to `/services/collector`. Verified live in Gate 6 with HTTP 200 ACKs. |
| **Splunk HEC Raw (Text)** | YES | YES | YES | YES | YES | YES | **YES** | Native HTTP POST to `/services/collector/raw`. Tested in dispatcher unit tests. |
| **Syslog UDP (RFC 3164)** | YES | YES | YES | YES | PARTIAL | YES | **YES** | Emits real UDP datagrams to port 514 via Python `socket.SOCK_DGRAM`. Requires external syslog receiver. |
| **Syslog TCP (RFC 5424)** | YES | YES | YES | YES | PARTIAL | YES | **YES** | Emits real TCP stream to port 514 with newline framing via `socket.SOCK_STREAM`. |
| **Cisco-Style Syslog** | YES | YES | YES | YES | YES | YES | **YES** | `%FACILITY-SEV-MNEMONIC` generated with microsecond UTC timestamps. Dispatched via Syslog or HEC. |
| **Palo Alto CSV Format** | YES | YES | YES | YES | YES | YES | **YES** | Exact 54-field CSV format generated for Threat, Traffic, and System logs. Dispatched via Syslog or HEC. |
| **SNMPv2c / v3 Traps** | YES | YES | **NO** | YES | YES | YES | **YES** | **Simulated as SC4SNMP HEC JSON payload.** NetSpout does NOT emit binary UDP 162 ASN.1 BER packets. |
| **SNMP Polling Metrics** | YES | YES | **NO** | YES | YES | YES | **YES** | **Simulated as SC4SNMP metric JSON** (`sourcetype="sc4snmp:metric"`). 300+ MIBs modeled. |
| **NetFlow v9 (RFC 3954)** | YES | YES | **NO** | YES | YES | YES | **YES** | **Simulated as normalized JSON records.** NetSpout does NOT emit binary UDP port 2055 NetFlow v9 packets. |
| **IPFIX (RFC 7011)** | YES | YES | **NO** | YES | YES | YES | **YES** | **Simulated as normalized JSON records** (`sourcetype="netflow:ipfix"`). Not binary IPFIX wire packets. |
| **sFlow v5 / J-Flow** | YES | YES | **NO** | YES | YES | YES | PARTIAL | Modeled in catalog and log samples as JSON. No binary sFlow UDP datagram emitter exists. |
| **Cisco MDT (Model-Driven)** | YES | YES | PARTIAL | YES | YES | YES | **YES** | Encoded as JSON dial-out payloads (`cisco_mdt_metrics`). Emitted via HEC or gNMI JSON. |
| **gNMI / OpenConfig** | YES | YES | PARTIAL | YES | YES | YES | **YES** | Modeled in `gnmi_engine.py` with hierarchical JSON trees. Dispatched via HEC; no native gRPC server. |
| **REST Webhooks** | YES | YES | YES | YES | YES | YES | **YES** | Native JSON payloads (Meraki Air Marshal, DNAC Assurance, ThousandEyes Alert) dispatched over HEC. |
| **OpenTelemetry (OTLP)** | YES | YES | YES | YES | PARTIAL | YES | **YES** | HTTP/JSON POST to `/v1/logs` and `/v1/metrics`. Dispatched to OTel collector; observation unverified. |

> [!IMPORTANT]
> **Wire Protocol Realism Boundary:** NetSpout's native wire formats are **HTTP/HTTPS (HEC, REST, OTLP)** and **Socket Syslog (UDP/TCP port 514)**. Protocols such as IPFIX, NetFlow, and SNMP are modeled at the **data and semantic layer** (using Splunk SC4SNMP and Stream normalized JSON payloads), NOT as binary UDP socket frames on ports 2055 or 162.

---

## 6. Vendor Support Maturity Matrix

NetSpout models **36 vendors** in `vendors.json`. The master specification proposes **72 vendors**. The authoritative maturity across all vendors is classified below:

### 6.1 Verified & Modeled Vendors (In NetSpout Core)

| Vendor | Maturity | Telemetry Formats Implemented | Splunk TA Status | Verified Scenarios |
| :--- | :---: | :--- | :--- | :--- |
| **Cisco Systems (IOS-XE/XR)** | **VERIFIED** | Syslog, BFD, BGP, MDT JSON, NetFlow JSON | `Splunk_TA_cisco-ios` (Real) | BGP Flap, UDLD, Core Routing |
| **Cisco SD-WAN (Viptela)** | **VERIFIED** | LinkHealth, BFD SLA, BGP Failover, Syslog | `Splunk_TA_cisco-viptela` (Real) | SD-WAN Brownout (GP-01 Certified) |
| **Cisco Catalyst & Wireless** | **VERIFIED** | Rogue AP Alerts, MAC Flap, Security Events | `Splunk_TA_cisco-wlc` (Real) | Campus Rogue AP (`cisco_campus_rogue`) |
| **Cisco ThousandEyes** | **VERIFIED** | Synthetic Page Load, Latency, Loss, Jitter | `thousandeyes:metric` (Webhook) | SD-WAN Brownout, Cloud Monitoring |
| **Cisco ISE** | **MODELED** | RADIUS 802.1X Syslog, Quarantine Alerts | `Splunk_TA_cisco-ise` (Real) | Campus Rogue Containment, Zero Trust |
| **Cisco ACI / Nexus 9k** | **MODELED** | Nexus Syslog, ACI Health, Buffer Incast | `Splunk_TA_cisco-nxos` (Real) | DC Microburst (`cisco_aci_microburst`) |
| **Palo Alto Networks** | **VERIFIED** | PAN-OS 54-field Threat CSV, Traffic CSV | `Splunk_TA_paloalto` (Real) | Distributed Edge Breach, Perimeter Policy |
| **Fortinet** | **VERIFIED** | FortiOS UTM/IPS Key-Value Syslog | `Splunk_TA_fortinet` (Real) | Firewall Capacity, IPS Drop |
| **Arista Networks** | **MODELED** | EOS Syslog, Interface Error-Disable, IPFIX | `Arista EOS TA` (Real) | Data Center Flap, BGP Peer |
| **Juniper Networks** | **MODELED** | Junos Syslog, RPD BGP Prefix Alarms | `Splunk_TA_juniper` (Real) | Core Routing Flap, Carrier Peering |
| **Cisco Meraki** | **MODELED** | Air Marshal Rogue Webhook JSON, Assurance | `meraki:api` (Webhook) | Wireless Threat, Rogue Containment |
| **F5 Networks (BIG-IP)** | **MODELED** | LTM/APM Syslog, Pool Member Health | `Splunk_TA_f5-bigip` (Real) | Core Load Balancing, SSL Saturation |
| **SC4SNMP / Splunk Native** | **MODELED** | SC4SNMP Metric JSON, IF-MIB Traps | `sc4snmp:metric` (Splunk App) | 300+ MIB Polling, SNMP Storm |
| **NGINX / HAProxy** | **MODELED** | HTTP Access/Error Logs, Gateway Timeouts | `Splunk_TA_nginx` (Real) | Lateral Spread, App Degradation |

### 6.2 Catalog-Only Vendors (Declared in `vendors.json`, Synthetic Fallback)

The following 22 vendors exist in NetSpout's catalog with metadata, but currently generate contract-synthesized generic logs (`%NETSPOUT-6-INFO`) rather than dedicated high-fidelity payloads:
* A10 Networks, Check Point Software, Citrix / Cloud Software Group, Cloudflare, Dell Technologies, ExtraHop Networks, Extreme Networks, Forcepoint, Huawei Technologies, NetScout Systems, Netskope, Nokia, Nutanix, Radware, SonicWall, Sophos, VMware by Broadcom, WatchGuard, Zscaler (ZIA/ZPA), Cisco Duo, Cisco Intersight, Cisco ASA.

### 6.3 Master-Spec-Only Vendors (Unimplemented / Catalog Only)

The master specification describes an additional 36 vendors across telecommunications, wireless, and operational technology that have **zero implementation** in NetSpout:
* **Telco Core & Optical (8)**: Ciena, Ericsson, ZTE, Infinera, ADVA Optical, Calix, Adtran, RAD Data.
* **Whitebox & SmartNIC (5)**: NVIDIA Mellanox (Cumulus), Broadcom, Edgecore, Celestica (SONiC), Pensando/AMD.
* **Cellular & Private 5G (8)**: Celona, Samsung Networks, Cambium, Ubiquiti, Ruckus, Baicells, JMA Wireless, Mavenir.
* **SCADA / ICS / OT (8)**: Siemens, Schneider Electric, Rockwell Automation, Beckhoff Automation, Phoenix Contact, Claroty, Nozomi Networks, Dragos.
* **Smart Grid & Utilities (4)**: Schweitzer Engineering Laboratories (SEL), GE Grid Solutions, Itron, Landis+Gyr.
* **Healthcare & IoMT (3)**: Baxter, B. Braun, GE Healthcare.

---

## 7. Splunk Technology Add-on (TA) Verification Backlog

A critical responsibility of NetSpout is ensuring field names and sourcetypes map cleanly to **real Splunkbase Technology Add-ons**. The master specification lists several TAs that do not exist:

| TA Name Referenced in Master Spec | Validity Classification | True Splunkbase Product / Mapping Disposition |
| :--- | :---: | :--- |
| `Splunk_TA_cisco-ios` | **VERIFIED_REAL_TA** | Splunk Add-on for Cisco IOS (Splunkbase ID 1467) |
| `Splunk_TA_cisco-viptela` | **VERIFIED_REAL_TA** | Splunk Add-on for Cisco SD-WAN (Splunkbase ID 5282) |
| `Splunk_TA_paloalto` | **VERIFIED_REAL_TA** | Palo Alto Networks App and Add-on for Splunk (Splunkbase ID 491) |
| `Splunk_TA_fortinet` | **VERIFIED_REAL_TA** | Splunk Add-on for Fortinet FortiGate (Splunkbase ID 2800) |
| `Splunk_TA_cisco-nxos` | **VERIFIED_REAL_TA** | Splunk Add-on for Cisco NX-OS (Splunkbase ID 1473) |
| `Splunk_TA_juniper` | **VERIFIED_REAL_TA** | Splunk Add-on for Juniper Junos (Splunkbase ID 1989) |
| `Splunk_TA_f5-bigip` | **VERIFIED_REAL_TA** | Splunk Add-on for F5 BIG-IP (Splunkbase ID 2680) |
| `Splunk_TA_cisco-wlc` | **VERIFIED_REAL_TA** | Splunk Add-on for Cisco WLC (Splunkbase ID 1504) |
| `Splunk_TA_zscaler-zpa` | **VERIFIED_REAL_TA** | Splunk Add-on for Zscaler Private Access (Splunkbase ID 4431) |
| `Splunk_TA_infoblox` | **VERIFIED_REAL_TA** | Splunk Add-on for Infoblox NIOS (Splunkbase ID 2831) |
| `Splunk_TA_zeek` | **VERIFIED_REAL_TA** | Splunk Add-on for Zeek (Splunkbase ID 5466) |
| `Arista EOS TA` | **LIKELY_REAL_BUT_UNVERIFIED** | Arista Networks Technology Add-on for Splunk (Splunkbase ID 3088) |
| `Nozomi TA` | **LIKELY_REAL_BUT_UNVERIFIED** | Nozomi Networks App for Splunk (Splunkbase ID 3971) |
| `Celona Orchestrator TA` | **LIKELY_REAL_BUT_UNVERIFIED** | Celona 5G LAN Add-on (Requires external partner verification) |
| `Splunk Add-on for Medical Devices` | **QUESTIONABLE** | **DOES NOT EXIST.** Splunkbase has no generic medical device TA. |
| `Splunk Add-on for Healthcare IoT` | **QUESTIONABLE** | **DOES NOT EXIST.** Requires mapping to generic CIM or Claroty TA. |
| `Splunk Telecom TA` | **QUESTIONABLE** | **DOES NOT EXIST.** Generic label for telco signaling. |
| `Splunk Add-on for BGP` | **QUESTIONABLE** | **DOES NOT EXIST.** BGP is parsed by vendor routing TAs (`cisco-iosxr`, `juniper`). |
| `Splunk Add-on for Connected Vehicles` | **QUESTIONABLE** | **DOES NOT EXIST.** Fictitious TA. |
| `Splunk Add-on for Healthcare HL7` | **QUESTIONABLE** | **DOES NOT EXIST.** Fictitious TA. |
| `Splunk Add-on for 5G Core` | **QUESTIONABLE** | **DOES NOT EXIST.** 5G Core telemetry typically uses OTLP or Open5GS JSON. |
| `Splunk Add-on for Smart Grid / AMI` | **QUESTIONABLE** | **DOES NOT EXIST.** Fictitious TA. |
| `Splunk Add-on for Aerospace Telemetry`| **QUESTIONABLE** | **DOES NOT EXIST.** Fictitious TA. |

---

## 8. Scenario Reconciliation: Current vs. 55 Master Scenarios

Comparing NetSpout's 29 scenarios and 10 pre-built use cases against the 55 Master Scenarios:

| Master Scenario # & Title | Current NetSpout Equivalent | Classification | Analysis |
| :--- | :--- | :---: | :--- |
| **#5 LAN: UDLD & Asymmetric Fiber Cut** | `arch_lan_campus_access` | **CURRENT_PARTIAL** | NetSpout models campus access; can incorporate UDLD error-disable events. |
| **#7 WLAN: 802.11k/v/r Sticky Client** | `arch_wlan_meraki_catalyst` | **CURRENT_PARTIAL** | Low-RSSI client roam starvation can be added to wireless scenario. |
| **#8 WLAN: Deauth Storm & Evil Twin** | `cisco_campus_rogue` | **CURRENT_EQUIVALENT** | NetSpout already models rogue AP beaconing, ISE quarantine, and MAC flap. |
| **#9 CAN: MLAG/vPC Split-Brain** | `arch_can_multi_building` | **CURRENT_PARTIAL** | Nexus vPC peer-link failure modeled in catalog; needs high-fidelity logs. |
| **#11 MAN: DWDM Fiber Pinch & G.8032** | `arch_man_carrier_ring` | **CURRENT_PARTIAL** | Carrier Ethernet ring switch modeled; TL1/ERPS alarms can be refined. |
| **#13 WAN: BGP Route-Flap Damping** | `uc-noc-01-bgp-flap` | **CURRENT_EQUIVALENT** | BGP hold timer expiration and prefix dampening fully modeled in `use_case_repo.py`. |
| **#15 SAN: Fibre Channel B2B Credit** | `arch_san_fibre_channel` | **CURRENT_PARTIAL** | Cisco MDS 9700 slow-drain credit starvation modeled in catalog. |
| **#16 SAN: RoCEv2 Incast & PFC Storm** | `cisco_aci_microburst` | **CURRENT_PARTIAL** | Leaf buffer incast and PFC drop modeled in DC microburst scenario. |
| **#18 SD-WAN: Underlay Brownout** | `cisco_sdwan_brownout` | **CURRENT_EQUIVALENT** | **GOLDEN PATH 01 CERTIFIED.** Latency, loss, BFD breach, AppRoute failover. |
| **#21 SDN: Leaf TCAM Table Full** | `cisco_aci_microburst` | **CURRENT_PARTIAL** | Buffer exhaustion modeled; TCAM overflow can be incorporated. |
| **#25 VPN: IKEv2 DPD Timeout & MTU** | `arch_vpn_remote_workforce` | **CURRENT_PARTIAL** | Cisco ASA/AnyConnect IPsec DPD timeout modeled in catalog. |
| **Breach SEC-01: Cobalt Strike C2 DNS**| `mixed_edge_breach` / `uc-soc-08` | **CURRENT_PARTIAL** | DNS tunneling and NDR beaconing modeled; can unite into 4-vendor chain. |
| **Breach SEC-02: Ransomware SMB** | `lateral_movement` / `uc-soc-04` | **CURRENT_EQUIVALENT** | Port 445 SMB burst and lateral spread isolation modeled. |
| **Scenarios 1–4 (BAN / PAN Medical/RF)**| None | **NEW_CANDIDATE** | Low priority for core networking; specialized IoT/medical. |
| **Scenarios 28–31 (Telco Access/MPLS)** | `arch_man_carrier_ring` | **NEW_CANDIDATE** | High-value carrier expansion (GPON, SR-MPLS label drop). |
| **Scenarios 35–44 (Cellular 4G/5G/O-RAN)**| None | **REQUIRES_SPECIALIZED_DOMAIN_VALIDATION** | Highly specialized 3GPP/O-RAN protocols; defer until core IT is complete. |
| **Scenarios 45–55 (SCADA/ICS/Avionics)** | None | **REQUIRES_SPECIALIZED_DOMAIN_VALIDATION** | Modbus, DNP3, and CAN bus require specialized protocol validation. |

### NetSpout Scenarios Not Represented in the 55 Master Scenarios
NetSpout contains several operational scenarios that are distinct from the master specification:
* `cisco_aci_microburst`: Dedicated Cisco ACI fabric health and MDT telemetry degradation.
* `mixed_backbone_optical`: Multicast PIM-SM and carrier optical shift.
* `mixed_sase_degradation`: Cloud SASE synthetic transaction failure and CASB policy.
* `ddos_attack`: Volumetric SYN flood hitting perimeter firewall with drop metrics.
* `sql_injection`: Web application database breach with reverse proxy logging.
* `openconfig_mdt_streaming`: Model-Driven Telemetry YANG assurance streaming.

---

## 9. Scenario Maturity Model

To bridge the gap between declared catalog entries and production-verified scenarios, NetSpout establishes a 6-stage **Scenario Maturity Lifecycle**:

```mermaid
flowchart LR
    A[1. CANDIDATE] --> B[2. CONTRACTED]
    B --> C[3. IMPLEMENTED]
    C --> D[4. FORMAT_VALIDATED]
    D --> E[5. E2E_VALIDATED]
    E --> F[6. GOLDEN_PATH_CERTIFIED]
```

1. **CANDIDATE:** Scenario concept identified, documented, and given an ID (e.g. Master Scenarios 1–55).
2. **CONTRACTED:** Machine-readable `ScenarioContract` defined in `scenarios.json` with topology ID, vendor scope, sourcetypes, phases, and `ValidationRule` assertions.
3. **IMPLEMENTED:** Dedicated Python generator logic implemented in `scenario_runner.py` / `log_engine.py` (no generic fallback logs).
4. **FORMAT_VALIDATED:** Generated events verified to match exact vendor syntax and official Splunkbase TA field extraction via unit tests.
5. **E2E_VALIDATED:** Scenario executed against live Splunk HEC; verified `observed_count == dispatch_succeeded` and `destination_validation == PASS`.
6. **GOLDEN_PATH_CERTIFIED:** End-to-end user journey validated via headless browser CDP automation; verified 16/16 acceptance criteria with zero manual interventions.

### Catalog Schema Gap
Currently, `scenarios.json` does not include an explicit `maturity_level` field (it uses `generation_mode: SCENARIO_DERIVED`). 
* **Gap Identified:** Add `maturity: "CANDIDATE" | "CONTRACTED" | "IMPLEMENTED" | "FORMAT_VALIDATED" | "E2E_VALIDATED" | "GOLDEN_PATH_CERTIFIED"` to `ScenarioContract` model in a future schema version.

---

## 10. Multi-Vendor Topology Assessment

NetSpout's topology engine (`graph_engine.py`) was evaluated against the Master Specification's blueprints:

### Blueprint 1: Modern Hybrid Enterprise (BP-01)
* **Chain:** Meraki Wireless $\rightarrow$ Catalyst Core $\rightarrow$ Catalyst Center $\rightarrow$ ThousandEyes $\rightarrow$ Palo Alto SD-WAN $\rightarrow$ Fortinet NGFW.
* **Assessment:** **CAPABLE & IMPLEMENTED.** NetSpout already models Meraki APs, Catalyst switches, ThousandEyes agents, and Palo Alto/Fortinet firewalls. Node types (`NodeType.SWITCH`, `ROUTER`, `FIREWALL`, `WIRELESS_AP`, `CLIENT_EXTERNAL`), interfaces, and link degradation are fully supported.

### Blueprint 2: High-Performance Data Center Fabric (BP-02)
* **Chain:** Arista Spine $\rightarrow$ NVIDIA Mellanox Leaf $\rightarrow$ Pure Storage / MDS SAN $\rightarrow$ F5 BIG-IP $\rightarrow$ Zeek Sensor.
* **Assessment:** **CAPABLE & PARTIALLY MODELED.** NetSpout models Spine/Leaf fabrics in `get_cisco_aci_topology()` and Arista/F5 in `use_case_repo.py`. RoCEv2 PFC deadlock and NVMe-oF slow-drain telemetry require high-fidelity event templates.

### Topology Engine Gaps
1. **Dynamic Causal Fault Cascading:** Link degradation degrades bandwidth and latency on a single edge, but failure does not automatically propagate to upstream routing protocols via topology physics (e.g. BFD timer expiration is triggered by scenario phase logic, not by simulated packet loss physics in the graph engine).
2. **Service-Layer Modeling:** Edges represent physical and logical network links, but application-layer service dependencies (e.g. DNS resolution preceding HTTP transaction) are represented implicitly in scenario phases rather than explicitly as service graph edges.

---

## 11. Correlated Timeline Capability

Can NetSpout represent multi-vendor chronological progressions?
```
T+00 source A observes symptom
T+03 source B observes degradation
T+07 source C observes failure
T+12 routing/failover occurs
T+20 service recovers
```

**Assessment: FULLY SUPPORTED.**
NetSpout's `ScenarioRunner` executes a 9-phase lifecycle:
`INITIALIZE` $\rightarrow$ `BASELINE` $\rightarrow$ `DEGRADE` $\rightarrow$ `FAULT` $\rightarrow$ `PROPAGATE` $\rightarrow$ `FAILOVER` $\rightarrow$ `RECOVER` $\rightarrow$ `VALIDATE` $\rightarrow$ `COMPLETE`.

Each phase:
* Advances the chronological clock deterministically.
* Emits events stamped with `netspout_run_id`, `netspout_scenario_id`, `netspout_phase`, `netspout_event_id`, and `netspout_ground_truth`.
* Binds the exact device, vendor, and sourcetype corresponding to that operational milestone.

### Identified Gap: Explicit Causal Linkage
While events are ordered chronologically and tagged by phase, individual events do not carry an explicit `causal_parent_id` (e.g. linking Event 4's AppRoute failover directly to Event 1's BFD SLA breach). Adding an optional `causal_parent_id: Optional[str]` to `LogEntry` will enhance graph-based root-cause analysis in Splunk ITSI and graph visualizations.

---

## 12. Event Realism & Fidelity Review

Representative generators were sampled and evaluated against production vendor logs:

| Vendor / Telemetry Type | Generator Implementation | Fidelity Rating | Assessment & Alignment with Master Spec |
| :--- | :--- | :---: | :--- |
| **Cisco IOS-XE Syslog** | `SplunkLogEngine.format_cisco_syslog()` | **HIGH_FIDELITY** | Matches exact Cisco standard: `<PRI>SEQ: *TIMESTAMP UTC: %FACILITY-SEV-MNEMONIC: Description`. |
| **Cisco SD-WAN Link Health** | `SplunkLogEngine.format_cisco_sdwan_linkhealth_log()` | **HIGH_FIDELITY** | Accurate BFD probe metrics: `local_color`, `remote_color`, `latency`, `jitter`, `loss`, `sla_class`. Verified in Splunk index. |
| **Palo Alto Threat CSV** | `SplunkLogEngine.format_palo_alto_threat_log()` | **HIGH_FIDELITY** | Matches exact 54-field PAN-OS CSV format (`THREAT,vulnerability,2561,...`). Parses cleanly in `Splunk_TA_paloalto`. |
| **Fortinet FortiOS Syslog** | `SplunkLogEngine.format_fortinet_log()` | **HIGH_FIDELITY** | Key-value format matching FortiOS 7.x (`date=... time=... devname=... logid=... subtype=ips msg=...`). |
| **Cisco Meraki Webhook** | `cisco_sample_provider.py` | **HIGH_FIDELITY** | Exact JSON schema matching Meraki Dashboard API Air Marshal rogue alert. |
| **Cisco ThousandEyes** | `cisco_sample_provider.py` | **HIGH_FIDELITY** | Exact alert webhook schema (`alertId`, `testId`, `agents`, `metrics`, `permalink`). |
| **Arista EOS Syslog** | `log_engine.py` | **HIGH_FIDELITY** | Accurate EOS formatting (`%ETH-4-ERRDISABLE`, `%BGP-5-ADJCHANGE`). |
| **Juniper Junos Syslog** | `log_engine.py` | **PLAUSIBLE** | Key Junos daemons modeled (`rpd`, `chassisd`), but could benefit from structured syslog tags. |
| **SNMP Polling & Traps** | `snmp_engine.py` | **SYNTHETIC_BUT_USEFUL** | 300+ MIBs modeled; emitted as SC4SNMP HEC JSON. Useful for Splunk, but not native binary UDP 162 packets. |
| **IPFIX / NetFlow** | `log_engine.py` | **SYNTHETIC_BUT_USEFUL** | Emitted as normalized JSON flow records. Useful for Splunk HEC ingestion, but not binary UDP 2055 packets. |
| **Model-Driven Telemetry** | `gnmi_engine.py` | **SYNTHETIC_BUT_USEFUL** | Accurate OpenConfig YANG paths and counters emitted as JSON; not gRPC binary streams. |

---

## 13. Security Hygiene Review

An inspection of the repository for security posture and credential handling revealed:
1. **Zero Committed Production Secrets:** All API keys, tokens, and credentials in the repository are standard RFC/Splunk development placeholders (`00000000-0000-0000-0000-000000000000`, `admin:Changeme1!`).
2. **Safe Example IPs:** All network telemetry samples use RFC 1918 private subnets (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`) or RFC 5737 documentation ranges (`198.51.100.0/24`, `203.0.113.0/24`). No real-world public IP addresses are present.
3. **Secure-by-Default TLS:** In `telemetry_dispatcher.py`, `hec_ssl_verify` defaults to `True` and `hec_allow_insecure_tls` defaults to `False`. The self-signed certificate bypass is an explicit, user-toggled lab override.
4. **Credential Redaction in Logs & Preflight:** The preflight test response schema explicitly strips and omits authentication tokens, returning only status, latency, and index validation.

---

## 14. Product Scope & Strategic Positioning Review

How should NetSpout be positioned?

| Positioning Category | Evaluation | Analysis & Gaps |
| :--- | :---: | :--- |
| **Network Event Generator** | **REJECTED** | Too narrow. Tools like `syslog-gen` or `logbench` generate raw strings. NetSpout models topologies, network states, and validation. |
| **Network Telemetry Simulator** | **PARTIAL** | Captures the simulation aspect, but misses the closed-loop verification against customer analytics platforms. |
| **Network Use-Case Simulator** | **STRONG** | Accurately describes the 5-step workflow (Discover $\rightarrow$ Preview $\rightarrow$ Connect $\rightarrow$ Run $\rightarrow$ Prove). |
| **Network Use-Case Validation Platform** | **OPTIMAL** | **The most accurate and commercially defensible positioning.** NetSpout's unique capability is executing realistic multi-vendor scenarios and **mathematically auditing whether expected observations occurred in Splunk**. |

### Requirements for "Network Use-Case Validation Platform":
* Retain and expand the Gate 4 Validation Contract Engine (`ValidationRule`).
* Maintain strict evidence integrity (Invariants 1–5).
* Expand Golden Path certification to prove validation across diverse operational domains.

---

## 15. Redundancy & Obsolete Architecture Findings

The repository was searched for redundant and obsolete components:

1. **15 Legacy Simple XML Views in Splunk Package (`netspout/default/data/ui/views/`):**
   * Files: `configuration.xml`, `datablaster_console.xml`, `datablaster_dashboard.xml`, `guided_onboarding.xml`, `help.xml`, `scenario_builder.xml`, `spl_playground.xml`, `studio_*.xml`.
   * **Finding:** These are legacy pre-Gate-5 views that predate the React SPA. They clutter the Splunk app navigation menu.
   * **Disposition:** Do NOT delete in this read-only review. Flag for deprecation and cleanup in the next technical debt pass.
2. **Triple Python Core Copies:**
   * Canonical: `src/netspout_core/*.py`
   * Clones: `backend/app/*.py`, `netspout/bin/*.py`, `netspout/bin/netspout_core/*.py`
   * **Finding:** Maintained via `scripts/sync_core.py` and audited by `scripts/verify_sources.py`. Required due to Splunk packaging vs. FastAPI standalone structure, but represents build maintenance overhead.
3. **Dual Use Case Registries:**
   * `netspout/catalog/scenarios.json` (29 entries) vs. `src/netspout_core/use_case_repo.py` (10 entries).
   * **Finding:** `/api/use-cases` merges both dynamically to produce 39 use cases. They should eventually be consolidated into a single unified JSON catalog.
4. **Historical "DataBlaster" Nomenclature:**
   * Container name: `splunk-network-data-blaster`
   * REST endpoint: `/services/datablaster/execute`
   * **Finding:** Residual naming from the project's original prototype phase.

---

## 16. Prioritized Technical Debt Register

### Priority 0 (P0) — Correctness, Evidence Integrity & Security
* *None.* (All P0 defects from Golden Path 01 were fully resolved and verified in Gate 6).

### Priority 1 (P1) — Architecture & Product Reliability
1. **Generic Fallback Generator for 23 Catalog Scenarios:** Out of 29 catalog scenarios, only 6 have dedicated multi-vendor high-fidelity generators in `scenario_runner.py`. The remaining 23 emit generic `%NETSPOUT-6-INFO` fallback logs.
2. **Simulated vs. Native Wire Format for Flow & SNMP:** Flow telemetry (IPFIX/NetFlow) and SNMP traps are transmitted as JSON over HEC, not native binary UDP packets on ports 2055 or 162. Customers attempting to test physical flow/SNMP collectors cannot ingest this data without HEC.
3. **Unverifiable Destination Observation for OTel & Syslog:** Observation polling only queries Splunk REST (`/services/search/jobs/export`). For pure Syslog or OTel destinations without a query API, observation status defaults to UNCHECKED.

### Priority 2 (P2) — Maintainability & Usability
1. **15 Legacy Simple XML Views in Splunk Package:** Pre-Gate-5 views clutter the app navigation.
2. **Triple Core Synchronization Dependency:** Code changes require running `sync_core.py` to update backend and Splunk bin copies.
3. **Splunk Web Session Isolation:** Deep links open Splunk Search in a new tab, but require an existing authenticated session.
4. **Missing Causal Linkage in Log Entries:** Events have chronological phase order, but no explicit `causal_parent_id`.
5. **Dual Scenario / Use-Case Storage:** 29 scenarios in `scenarios.json` and 10 use cases in `use_case_repo.py` are merged in code.

### Priority 3 (P3) — Cleanup & Documentation
1. **Historical "DataBlaster" References:** In Docker container name and Splunk REST endpoint.
2. **Deprecation Warnings:** In Python 3.14 (`datetime.utcnow()` and Pydantic V2 `.dict()`).
3. **Unused `tier=None` in `vendors.json`:** Metadata fields that are not populated.
4. **Outdated Frontend README:** Does not mention the 5-step workflow or Gate 6 evidence integrity.

---

## 17. Top 20 Product Gaps

1. **Gap 01:** Only 1 scenario (`cisco_sdwan_brownout`) is Golden-Path-Certified; 28 scenarios lack certified E2E browser evidence.
2. **Gap 02:** 23 catalog scenarios fall back to generic log synthesis rather than dedicated vendor-specific telemetry.
3. **Gap 03:** No native binary wire-format IPFIX/NetFlow UDP packet emitter (JSON-over-HEC only).
4. **Gap 04:** No native binary wire-format SNMP trap UDP packet emitter (SC4SNMP HEC JSON only).
5. **Gap 05:** 15 legacy Simple XML dashboards remain in the packaged Splunk app.
6. **Gap 06:** 22 declared vendors lack dedicated event templates (catalog-only status).
7. **Gap 07:** 36 master-spec vendors (OT, Cellular, Telco) have zero representation in NetSpout.
8. **Gap 08:** Master-spec breach chains (Cobalt Strike C2, Ransomware SMB) lack unified multi-vendor contracts.
9. **Gap 09:** Scenario contracts lack an explicit `maturity_level` attribute in the catalog schema.
10. **Gap 10:** LogEntry lacks an explicit `causal_parent_id` for root-cause graph tracing.
11. **Gap 11:** Graph engine link degradation does not dynamically trigger routing protocol timeouts via simulated physics.
12. **Gap 12:** Destination observation verification is limited to Splunk REST; unavailable for OTel/Syslog collectors.
13. **Gap 13:** Dual repository storage between `scenarios.json` and `use_case_repo.py`.
14. **Gap 14:** Splunk Web deep links require pre-existing browser authentication.
15. **Gap 15:** Fictitious Splunkbase TAs in the master spec risk confusing catalog consumers.
16. **Gap 16:** Topology blueprints lack multi-cloud transit VPC / DirectConnect templates.
17. **Gap 17:** Python 3.14 deprecation warnings in `log_engine.py` (`utcnow()`) and `spl_engine.py` (`.dict()`).
18. **Gap 18:** Absence of multi-tenant or multi-token rotation in HEC preflight testing.
19. **Gap 19:** Residual "DataBlaster" naming in container and custom REST endpoint.
20. **Gap 20:** Lack of automated student/workshop reset and multi-user concurrency testing.

---

## 18. Capabilities NOT Recommended for Implementation

To protect NetSpout's architectural integrity and prevent scope explosion, the following capabilities from the master specification are **EXPLICITLY REJECTED**:

1. **DO NOT Build a Parallel Jinja2 Hydrator & YAML Scheduler:**  
   NetSpout's single source of truth in `src/netspout_core/` (`scenario_runner.py`, `log_engine.py`, `graph_engine.py`) is superior, faster, type-safe, and audited. Introducing raw Jinja2 file-system templates and YAML parsers would resurrect duplicate code debt.
2. **DO NOT Reintroduce Splunk Simple XML Dashboards:**  
   The React 18 SPA is modern, interactive, and production-ready. Simple XML is legacy technology scheduled for eventual deprecation by Splunk.
3. **DO NOT Add Fictitious Splunkbase TAs:**  
   Do not declare support for invented TAs (`Splunk Add-on for Medical Devices`, `Splunk Add-on for Connected Vehicles`). All TAs must exist on Splunkbase.
4. **DO NOT Expand to 72 Vendors Prematurely:**  
   Declaring 72 vendors when 36 are unmodeled dilutes product credibility. NetSpout must focus on high-fidelity depth for its core 14 enterprise networking and security vendors before expanding to SCADA, Avionics, or 5G Core.
5. **DO NOT Build Native Binary Flow/SNMP Engines Yet:**  
   98% of Splunk network telemetry use cases ingest via HEC, SC4SNMP, or Syslog. Building a low-level C-based raw socket binary packet generator for NetFlow v9 / IPFIX / SNMP wire protocols would introduce massive kernel/OS socket complexity with minimal customer benefit at this stage.

---

## 19. Recommended Next Development Phase

### **RECOMMENDED PHASE: GOLDEN PATH EXPANSION & MULTI-VENDOR SCENARIO FIDELITY**

**Primary Objective:** Elevate NetSpout from **1 Golden-Path-Certified scenario to 4 Certified Scenarios** by implementing dedicated high-fidelity telemetry generators and end-to-end CDP browser verification for the three most critical operational domains:

1. **Golden Path 02: Campus Wireless Threat & Automated Quarantine (WLAN / LAN)**
   * Scenario: `cisco_campus_rogue`
   * Multi-Vendor Scope: Cisco Meraki (Air Marshal Webhook) + Cisco Catalyst 9300 (IOS-XE Syslog & MAC Flap) + Cisco ISE (802.1X Quarantine Syslog).
   * Verified Outcome: Wireless intrusion detected, port quarantined, verified in Splunk Web.
2. **Golden Path 03: Data Center Fabric Microburst & Buffer Telemetry (DC / SASE)**
   * Scenario: `cisco_aci_microburst`
   * Multi-Vendor Scope: Cisco Nexus 9k / ACI + Arista EOS + Model-Driven Telemetry (MDT queue-depth metrics).
   * Verified Outcome: Buffer incast and queue saturation indexed in `cisco_mdt_metrics` and verified in Splunk.
3. **Golden Path 04: Multi-Vendor Security Breach Chain (Perimeter / NDR)**
   * Scenario: `mixed_edge_breach` / `SEC-01`
   * Multi-Vendor Scope: Infoblox NIOS (DNS RPZ) + Palo Alto Networks (PAN-OS Threat CSV) + Fortinet (FortiOS IPS) + ExtraHop / NGINX.
   * Verified Outcome: Multi-stage breach chain correlated across 4 distinct sourcetypes in Splunk Enterprise Security.

### What NOT to Build Yet:
* Do NOT implement binary wire-format flow generators.
* Do NOT add OT, SCADA, or cellular vendors.
* Do NOT refactor the core engine into Jinja2/YAML.

---

## 20. Golden Path Sequencing & Workshop Readiness

Should Golden Paths 02–04 run **BEFORE** next implementation or **AFTER** a specific missing capability is fixed?

### **RECOMMENDED SEQUENCING: RUN GOLDEN PATHS 02–04 AFTER SCENARIO GENERATOR ELEVATION**

**Justification & Sequencing Plan:**
1. **Step 1 (Scenario Generator Elevation):** Before running Golden Path acceptance tests for GP-02, GP-03, and GP-04, update `scenario_runner.py` to ensure their telemetry generators emit 100% production-grade, TA-compliant events rather than falling into generic synthesis.
2. **Step 2 (Automated CDP Acceptance Walkthrough):** Execute automated browser testing for each Golden Path, capturing 11-step visual proof archives and verifying Splunk indexing.
3. **Step 3 (20-Student Workshop Repeatability Audit):** Run concurrency and reset testing to certify that NetSpout can support 20 concurrent users running scenarios against a shared or multi-tenant Splunk instance without state collision.
