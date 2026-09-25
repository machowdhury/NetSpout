# NETSPOUT CANONICAL SCENARIO REGISTRY & IDENTITY REFERENCE

**Authoritative Specification — Gate 10.6 Baseline**  
**Author:** Mahamudul Chowdhury (`machowdhury@yahoo.com`)  
**Repository:** [https://github.com/machowdhury/NetSpout](https://github.com/machowdhury/NetSpout)  
**Total Canonical Scenarios:** 29  
**Total Vendors:** 36  
**Total Topologies:** 28  

---

## 1. Executive Summary

This document establishes the single, authoritative, human-readable scenario namespace registry for NetSpout. In accordance with the Single Source of Truth architecture established in Gate 3 and audited in Gate 10.6, every scenario in NetSpout has **exactly one canonical identifier**.

### Canonical Namespace Rules
1. **Identifier Invariance:** Canonical scenario identifiers are permanent, lowercase, underscore-delimited strings (e.g., `cisco_sdwan_brownout`, `arch_lan_campus_access`).
2. **Deterministic Aliasing:** If legacy slugs or scenario-to-topology convenience mappings exist, they must be registered in `catalog/aliases.json` and resolve deterministically to their canonical targets. They never replace canonical IDs.
3. **Maturity Boundaries:**
   - **`GOLDEN_PATH_CERTIFIED` (12):** Independently verified through live Splunk acceptance, achieving 100% telemetry observation completeness, zero developer knowledge requirement, and clean validation.
   - **`E2E_VALIDATED` (2):** Fully wired to multi-vendor topology graphs with deterministic simulation runners and passing contract rules; pending independent acceptance retest.
   - **`FORMAT_VALIDATED` (2):** Baseline synthetic traffic and lateral movement scenarios emitting compliant wire formats.
   - **`CONTRACTED` (13):** Formally contracted architectural blueprints with complete schema definitions, topological zone graphs, and expected observations; deferred to future implementation waves.

---

## 2. Authoritative Scenario Registry (All 29 Scenarios)

| # | Canonical Scenario ID | User-Facing Display Name | Maturity | Domain / Category | Default Topology | Telemetry Model | Transport | Splunk Storage | Fidelity Badge | Acceptance Status |
| :-: | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **1** | `cisco_sdwan_brownout` | Enterprise WAN Circuit Brownout & App Route Failover | **`GOLDEN_PATH_CERTIFIED`** | WAN & SD-WAN | `cisco_sdwan` | Standard Telemetry Payload | Splunk HEC | `idx_network_ops` | `MODELED PAYLOAD` | **PROVEN (100%)** — `GOLDEN_PATH_01_SDWAN_BROWNOUT_RETEST.md` (Run: `NS-20260925-587e0e08`) |
| **2** | `cisco_campus_rogue` | Campus Core L2/3 Disturbance & Rogue AP | **`GOLDEN_PATH_CERTIFIED`** | Campus & Wireless | `cisco_campus` | Standard Telemetry Payload | Splunk HEC | `idx_network_ops` | `MODELED PAYLOAD` | **PROVEN (100%)** — `GOLDEN_PATH_02_CAMPUS_ROGUE.md` (Run: `NS-20260925-3456ff87`) |
| **3** | `cisco_aci_microburst` | Data Center Fabric ACI Ingress Microburst Traffic | **`GOLDEN_PATH_CERTIFIED`** | Data Center & Fabric | `cisco_aci` | Cisco MDT & Nexus Syslog | Splunk HEC | `cisco_mdt_metrics` + `idx_network_ops` | `MODELED PAYLOAD` | **PROVEN (100%)** — `GOLDEN_PATH_03_ACI_RETEST.md` (Run: `NS-20260925-55343b43`) |
| **4** | `mixed_edge_breach` | Distributed Edge Breach & Internal Probing | **`GOLDEN_PATH_CERTIFIED`** | Security & Zero Trust | `mixed_edge` | Standard Telemetry Payload | Splunk HEC | `idx_network_ops` | `MODELED PAYLOAD` | **PROVEN (100%)** — `GOLDEN_PATH_04_MULTI_VENDOR_EDGE_BREACH.md` (Run: `NS-20260925-d0c8a046`) |
| **5** | `mixed_sase_degradation` | SASE Cloud Ingress App Degradation & Synthetic Validation | **`GOLDEN_PATH_CERTIFIED`** | Cloud & Hybrid Networking | `mixed_sase` | Cloud SASE & ThousandEyes Synthetics | Splunk HEC | `idx_network_ops` | `MODELED PAYLOAD` | **PROVEN (100%)** — `WAVE1_ACCEPTANCE_SASE.md` (Run: `NS-20260925-0509b5d9`) |
| **6** | `sql_injection` | SQL Injection / Application Breach | **`GOLDEN_PATH_CERTIFIED`** | Firewall & App Security | `bypassed` | Perimeter Firewall, WAF & DB Audit | Splunk HEC | `idx_network_ops` | `MODELED PAYLOAD` | **PROVEN (100%)** — `WAVE1_ACCEPTANCE_SQL_INJECTION.md` (Run: `NS-20260925-024b5239`) |
| **7** | `openconfig_mdt_streaming` | OpenConfig MDT Streaming & Telemetry Assurance | **`GOLDEN_PATH_CERTIFIED`** | Service Assurance & Telemetry | `openconfig_core` | OpenConfig / MDT | Splunk HEC | `cisco_mdt_metrics` + `idx_network_ops` | `MODELED PAYLOAD` | **PROVEN (100%)** — `OPENCONFIG_MDT_FOCUSED_RETEST.md` (Run: `NS-20260925-3535dbbf`) |
| **8** | `arch_lan_campus_access` | LAN: Local Area Network - Campus Switching & 802.1Q Segments | **`GOLDEN_PATH_CERTIFIED`** | Campus Access Security | `arch_lan_campus_access` | Standard Telemetry Payload | Splunk HEC | `idx_network_ops` | `MODELED PAYLOAD` | **PROVEN (100%)** — `WAVE2_CAMPUS_ACCESS.md` (Run: `NS-20260925-4928b364`) |
| **9** | `arch_vpn_remote_workforce` | VPN: Virtual Private Network - Cisco AnyConnect & Site-to-Site IPsec | **`GOLDEN_PATH_CERTIFIED`** | Remote Access Security | `arch_vpn_remote_workforce` | Standard Telemetry Payload | Splunk HEC | `idx_network_ops` | `MODELED PAYLOAD` | **PROVEN (100%)** — `WAVE2_REMOTE_VPN.md` (Run: `NS-20260925-fd7e06a3`) |
| **10** | `service_provider_cisco` | Service Provider Network - All Cisco (Cisco 8000, NCS 5500, IOS-XR SRv6) | **`GOLDEN_PATH_CERTIFIED`** | Core / SP Routing | `service_provider_cisco` | Standard Telemetry Payload | Splunk HEC | `idx_network_ops` | `MODELED PAYLOAD` | **PROVEN (100%)** — `WAVE2_SEMANTIC_RETEST.md` (Run: `NS-20260925-457d634a`) |
| **11** | `arch_wlan_meraki_catalyst` | WLAN: Wireless Local Area Network - Catalyst 9800 & Meraki Wi-Fi 6E/7 | **`GOLDEN_PATH_CERTIFIED`** | Wireless RF Health | `arch_wlan_meraki_catalyst` | Standard Telemetry Payload | Splunk HEC | `idx_network_ops` | `MODELED PAYLOAD` | **PROVEN (100%)** — `WAVE2_SEMANTIC_RETEST.md` (Run: `NS-20260925-e0090516`) |
| **12** | `arch_man_carrier_ring` | MAN: Metropolitan Area Network - 100G Carrier Ethernet Ring & G.8032 ERPS | **`GOLDEN_PATH_CERTIFIED`** | Metro Optical MAN | `arch_man_carrier_ring` | Standard Telemetry Payload | Splunk HEC | `idx_network_ops` | `MODELED PAYLOAD` | **PROVEN (100%)** — `WAVE2_SEMANTIC_RETEST.md` (Run: `NS-20260925-e802e5ac`) |
| **13** | `mixed_backbone_optical` | Multicast/MPLS Backbone Optical Carrier Shift | **`E2E_VALIDATED`** | Core / SP Optical | `mixed_optical` | Nokia SR-OS, Juniper Junos, Arista IPFIX | Splunk HEC | `idx_network_ops` | `MODELED PAYLOAD` | E2E Validated in Gate 9; Wave 1 Backlog |
| **14** | `ddos_attack` | Distributed Denial of Service (DDoS SYN Flood) | **`E2E_VALIDATED`** | WAN & Perimeter Defense | `secure` | Standard Telemetry Payload | Splunk HEC | `idx_network_ops` | `SYNTHETIC` | E2E Validated in Gate 9; Wave 1 Backlog |
| **15** | `normal_traffic` | Normal Operations (HTTP Round-Robin) | **`FORMAT_VALIDATED`** | Network Operations | `secure` | Standard Telemetry Payload | Splunk HEC | `idx_network_ops` | `SYNTHETIC` | Baseline Operations Format Validated |
| **16** | `lateral_movement` | Ransomware / Lateral Spread (Port 445) | **`FORMAT_VALIDATED`** | Security & Threat Detection | `lateral` | Standard Telemetry Payload | Splunk HEC | `idx_network_ops` | `SYNTHETIC` | Security Operations Format Validated |
| **17** | `arch_can_multi_building` | CAN: Campus Area Network - Multi-Building Backbone & Catalyst Center | **`CONTRACTED`** | Campus Area Network | `arch_can_multi_building` | Standard Telemetry Payload | Splunk HEC | `idx_network_ops` | `MODELED PAYLOAD` | Contracted Architectural Blueprint |
| **18** | `arch_epn_isolated_intranet` | EPN: Enterprise Private Network - Isolated Corporate Intranet & Multi-Cloud VPC | **`CONTRACTED`** | Enterprise Private Network | `arch_epn_isolated_intranet` | Standard Telemetry Payload | Splunk HEC | `idx_network_ops` | `MODELED PAYLOAD` | Contracted Architectural Blueprint |
| **19** | `arch_gan_subsea_cloud` | GAN: Global Area Network - Worldwide Multi-Cloud & Subsea Cable Transit | **`CONTRACTED`** | Global Area Network | `arch_gan_subsea_cloud` | Standard Telemetry Payload | Splunk HEC | `idx_network_ops` | `MODELED PAYLOAD` | Contracted Architectural Blueprint |
| **20** | `arch_nas_storage_cluster` | NAS: Network-Attached Storage - NetApp ONTAP & PowerScale Clusters | **`CONTRACTED`** | Network Storage | `arch_nas_storage_cluster` | Standard Telemetry Payload | Splunk HEC | `idx_network_ops` | `MODELED PAYLOAD` | Contracted Architectural Blueprint |
| **21** | `arch_pan_iot_mesh` | PAN: Personal Area Network - IoT Sensor Cluster & Bluetooth Mesh | **`CONTRACTED`** | IoT & Sensor Mesh | `arch_pan_iot_mesh` | Standard Telemetry Payload | Splunk HEC | `idx_network_ops` | `MODELED PAYLOAD` | Contracted Architectural Blueprint |
| **22** | `arch_san_fibre_channel` | SAN: Storage Area Network - Cisco MDS 9700 Fibre Channel & NVMe-oF | **`CONTRACTED`** | Storage Area Network | `arch_san_fibre_channel` | Standard Telemetry Payload | Splunk HEC | `idx_network_ops` | `MODELED PAYLOAD` | Contracted Architectural Blueprint |
| **23** | `arch_wan_global_backbone` | WAN: Wide Area Network - Global BGP/MPLS L3VPN Backbone & Optical DWDM | **`CONTRACTED`** | Wide Area Network | `arch_wan_global_backbone` | Standard Telemetry Payload | Splunk HEC | `idx_network_ops` | `MODELED PAYLOAD` | Contracted Architectural Blueprint |
| **24** | `mixed_vendor_enterprise` | Mixed-Vendor Enterprise Network (Cisco, Arista, Palo Alto, Fortinet, Juniper, Aruba) | **`CONTRACTED`** | Enterprise Multi-Vendor | `mixed_vendor_enterprise` | Standard Telemetry Payload | Splunk HEC | `idx_network_ops` | `MODELED PAYLOAD` | Contracted Architectural Blueprint |
| **25** | `pure_cisco_enterprise` | Pure Cisco Enterprise Fabric (Catalyst 9600, 9500, 9300, 9800, ISE, DNA-C) | **`CONTRACTED`** | Pure Cisco Fabric | `pure_cisco_enterprise` | Standard Telemetry Payload | Splunk HEC | `idx_network_ops` | `MODELED PAYLOAD` | Contracted Architectural Blueprint |
| **26** | `sdwan_connected_core` | Separate SD-WAN Environment Connected to Core Backbone (All Cisco) | **`CONTRACTED`** | WAN & Backbone Core | `sdwan_connected_core` | Standard Telemetry Payload | Splunk HEC | `idx_network_ops` | `MODELED PAYLOAD` | Contracted Architectural Blueprint |
| **27** | `service_provider_mixed` | Service Provider Network - Mixed Vendor (Cisco 8000, Juniper PTX, Nokia 7750) | **`CONTRACTED`** | Multi-Vendor Core / SP | `service_provider_mixed` | Standard Telemetry Payload | Splunk HEC | `idx_network_ops` | `MODELED PAYLOAD` | Contracted Architectural Blueprint |
| **28** | `wireless_connected_core_cisco` | Enterprise Wireless Connected to Campus Core (All Cisco) | **`CONTRACTED`** | Wireless & Campus Core | `wireless_connected_core_cisco` | Standard Telemetry Payload | Splunk HEC | `idx_network_ops` | `MODELED PAYLOAD` | Contracted Architectural Blueprint |
| **29** | `wireless_connected_core_mixed` | Enterprise Wireless Connected to Core (Mixed Vendor) | **`CONTRACTED`** | Multi-Vendor Wireless Core | `wireless_connected_core_mixed` | Standard Telemetry Payload | Splunk HEC | `idx_network_ops` | `MODELED PAYLOAD` | Contracted Architectural Blueprint |

---

## 3. Discrepancy Forensic Audit: Clarification of Earlier vs Later Names

During Gate 10.5 reporting, seven unauthorized identifiers were inadvertently introduced in conversational text:
- `datacenter_spine_leaf`
- `enterprise_sdwan`
- `firewall_failover`
- `cloud_interconnect`
- `bgp_route_leak`
- `arista_evpn_vxlan`
- `juniper_switch_fabric`

### Forensic Investigation Finding:
1. **Zero Git Occurrence:** None of these strings (with the exception of `bgp_route_leak` as an uncontracted speculative draft name) have ever appeared in Git commit history, code, test files, or `catalog/scenarios.json`.
2. **Root Cause:** Documentation error / conversational synthesis hallucination in the concluding narrative of Gate 10.5.
3. **Authoritative Canonical Golden Paths:** The actual Golden Paths have always been the 12 verified scenarios in Section 2 (`cisco_sdwan_brownout`, `cisco_campus_rogue`, `cisco_aci_microburst`, `mixed_edge_breach`, `mixed_sase_degradation`, `sql_injection`, `openconfig_mdt_streaming`, `arch_lan_campus_access`, `arch_vpn_remote_workforce`, `service_provider_cisco`, `arch_wlan_meraki_catalyst`, `arch_man_carrier_ring`).

---

## 4. Alias & Topology Lookup Mapping

The following aliases exist in `catalog/aliases.json` to facilitate cross-subsystem lookups without mutating canonical scenario identity:

| Alias Key | Target Canonical ID | Alias Type | Operational Purpose |
| :--- | :--- | :--- | :--- |
| `cisco_campus_rogue` | `cisco_campus` | `TOPOLOGY_ALIAS` | Resolves topology lookup when querying by scenario ID |
| `cisco_sdwan_brownout` | `cisco_sdwan` | `TOPOLOGY_ALIAS` | Resolves topology lookup when querying by scenario ID |
| `cisco_aci_microburst` | `cisco_aci` | `TOPOLOGY_ALIAS` | Resolves topology lookup when querying by scenario ID |

---

## 5. Machine-Readable Audit Ledger

Automated verification of Golden Path maturity is enforced by:
- File: [`catalog/golden_path_evidence.json`](file:///Users/mahamudc/Documents/NetSpout/catalog/golden_path_evidence.json)
- Builder: [`scripts/build_golden_path_evidence.py`](file:///Users/mahamudc/Documents/NetSpout/scripts/build_golden_path_evidence.py)
- Guardrail: [`scripts/validate_catalog.py`](file:///Users/mahamudc/Documents/NetSpout/scripts/validate_catalog.py)
