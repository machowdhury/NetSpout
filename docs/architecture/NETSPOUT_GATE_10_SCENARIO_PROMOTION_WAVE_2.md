# NetSpout Gate 10: Scenario Promotion Wave 2 Architecture Specification

**Status:** COMPLETE & E2E_VALIDATED  
**Gate:** Gate 10 — Systematic Scenario Promotion Wave 2 (Operational Use Cases)  
**Maturity Target:** `E2E_VALIDATED`  
**Prerequisites:** Gate 9.5 Complete (GP01–GP07 Golden Path Certified Baseline)  
**Platform Principle:** Prioritize high-frequency operational pain points that engineers need representative data for but cannot easily reproduce without physical lab gear.

---

## 1. Executive Summary & Verified Maturity State

Gate 10 completes the promotion of exactly **FIVE** existing `CONTRACTED` scenarios to `E2E_VALIDATED`, focusing strictly on practical operational usefulness across Enterprise Campus LAN, Remote Workforce VPN, Service Provider Core, Wireless RF Health, and Metro Optical MAN.

### 1.1. Verified Catalog Maturity Distribution (Total: 29 Scenarios, 36 Vendors)

| Maturity Tier | Count | Scenarios |
| :--- | :--- | :--- |
| **`GOLDEN_PATH_CERTIFIED`** | **7** | `cisco_sdwan_brownout`, `cisco_campus_rogue`, `cisco_aci_microburst`, `mixed_edge_breach`, `mixed_sase_degradation`, `sql_injection`, `openconfig_mdt_streaming` |
| **`E2E_VALIDATED`** | **7** | **Wave 1:** `mixed_backbone_optical`, `ddos_attack`<br>**Wave 2:** `arch_lan_campus_access`, `arch_vpn_remote_workforce`, `service_provider_cisco`, `arch_wlan_meraki_catalyst`, `arch_man_carrier_ring` |
| **`FORMAT_VALIDATED`** | **2** | `normal_traffic`, `lateral_movement` |
| **`CONTRACTED`** | **13** | `arch_wan_sdwan_dual_cpe`, `arch_can_multi_building`, `arch_dc_leaf_spine`, `arch_sec_multivendor_fw`, `arch_cloud_aws_transit`, `arch_iot_industrial`, `arch_san_fc_storage`, `mpls_vpn_leak`, `bgp_route_leak`, `dns_amplification`, `ztna_posture_failure`, `sdwan_underlay_loss`, `bgp_hijack` |
| **Total Catalog** | **29** | **100% SSOT Invariant, Zero Orphan Topologies/Vendors** |

---

## 2. Product Principle & Selection Rationale

Every candidate evaluated in Gate 10 answered the primary product question:

> *"Would a network, security, observability, or Splunk engineer realistically use NetSpout because they need representative data for this problem but do not have the infrastructure required to reproduce it?"*

Practical operational usefulness was prioritized over vendor-count expansion, exotic technology, or unnecessary complexity.

### 2.1. The 5 Promoted Operational Scenarios

| Scenario ID | Category | Domain | Vendor Ecosystem | Operational Problem & Ground Truth |
| :--- | :--- | :--- | :--- | :--- |
| **`arch_lan_campus_access`** | Campus Access Security | Enterprise LAN | Cisco Catalyst 9300, Catalyst 9600, Cisco ISE | Rogue DHCP server offering false gateway IPs, Dynamic ARP Inspection (DAI) burst violations, switchport error-disable, and 802.1X quarantine. |
| **`arch_vpn_remote_workforce`** | Remote Access Security | Enterprise WAN / VPN | Cisco ASA 5585-X, Cisco Duo Security MFA | High-volume external credential stuffing surge against SSL-VPN, fraudulent Duo push notification, automated account lockout, and IP blacklisting. |
| **`service_provider_cisco`** | Core / SP Routing | Service Provider WAN | Cisco 8201 Core, Cisco ASR 9010 PE, IOS-XR | BGP carrier transit adjacency collapse, TI-LFA (Topology-Independent Loop-Free Alternate) sub-50ms fast reroute, and MDT streaming telemetry shift. |
| **`arch_wlan_meraki_catalyst`** | Wireless RF Health | Enterprise WLAN | Cisco Catalyst 9130AX, Catalyst 9800 WLC, Meraki MR56 | Non-Wi-Fi RF interference surge (94.5% radio util), dynamic DFS channel switch, and Meraki Air Marshal evil-twin rogue containment. |
| **`arch_man_carrier_ring`** | Metro Optical MAN | MAN / Carrier Ring | Nokia 7750 SR-12, Juniper MX960, Arista 7280R | Terrestrial 100G fiber cut, ITU-T G.8032 ERPS sub-50ms ring protection (RPL unblock), and Wait-to-Restore (WTR) revertive healing. |

---

## 3. Deep-Dive: Scenario Progression & Telemetry Specifications

### 3.1. `arch_lan_campus_access`
* **Use Case:** Campus LAN / Access Port Security: Rogue DHCP & Dynamic ARP Inspection
* **Topology:** `arch_lan_campus_access` (Cat 9300 Access $\leftrightarrow$ Cat 9600 Core $\leftrightarrow$ Cisco ISE PSN $\leftrightarrow$ Host)
* **6-Phase Progression:**
  1. `BASELINE`: Client authorized on switchport `GigabitEthernet1/0/12` via 802.1X; core uplink nominal.
  2. `FAULT`: Attacker brings up rogue DHCP daemon emitting unauthorized offers (`DHCP_OFFER_DROPPED`).
  3. `PROPAGATE`: Attacker launches ARP spoofing flood exceeding 15 pps limit (`DAI_BURST_EXCEEDED`).
  4. `FAILOVER`: Port placed into `err-disable` state by Port Security; Cisco ISE issues CoA Quarantine (`ERR_DISABLE`, `action=blocked`).
  5. `RECOVER`: Rogue host unpatched; switchport auto-recovery timer expires, restoring port to forwarding (`PORT_RESTORED`).
  6. `VALIDATE`: Legitimate workstation re-authenticates; TrustSec policy compliance confirmed.
* **Telemetry Emitted:** `cisco:catalyst:security:events`, `cisco:ise:nac:8021x`, `cisco:ios:syslog`. Zero `%NETSPOUT-6-INFO` fallback.

### 3.2. `arch_vpn_remote_workforce`
* **Use Case:** WAN / Enterprise Remote Access: SSL-VPN Credential Stuffing & Duo Push Fraud
* **Topology:** `arch_vpn_remote_workforce` (Remote Client $\leftrightarrow$ Cisco ASA 5585-X $\leftrightarrow$ Cisco Duo Cloud MFA)
* **6-Phase Progression:**
  1. `BASELINE`: Legitimate employee `alice.smith@corp.internal` establishes AnyConnect SSL-VPN via Duo push.
  2. `FAULT`: Foreign IP (`185.220.101.5`, RU) floods ASA with invalid password attempts (`cisco:duo:remote:vpn`, `action=alerted`).
  3. `PROPAGATE`: Attacker guesses credential, triggering unauthorized Duo push; employee reports fraud (`result=FRAUD`).
  4. `FAILOVER`: Duo triggers automated user lockout; ASA shuns attacker IP at perimeter (`action=blocked`).
  5. `RECOVER`: User completes IT credential reset; authenticates from nominal corporate endpoint (`status=restored`).
  6. `VALIDATE`: Perimeter SSL-VPN tunnel health and authentication posture verified nominal.
* **Telemetry Emitted:** `cisco:duo:push:prompt`, `cisco:duo:remote:vpn`, `cisco:asa`. Zero `%NETSPOUT-6-INFO` fallback.

### 3.3. `service_provider_cisco`
* **Use Case:** Service Provider / Core Routing: Carrier Flap BGP Adjacency Collapse & TI-LFA Fast Reroute
* **Topology:** `service_provider_cisco` (Cisco 8201 Core01/02 $\leftrightarrow$ Cisco ASR 9010 PE01/02 $\leftrightarrow$ Transit Carrier)
* **6-Phase Progression:**
  1. `BASELINE`: BGP peering AS65000 established over `HundredGigE0/0/0/1`; MDT interface metrics nominal.
  2. `FAULT`: Physical carrier link flaps, tearing down BGP peering (`%ROUTING-BGP-5-ADJCHANGE: neighbor Down`).
  3. `PROPAGATE`: PE router receives core transit route withdrawal notifications; octets drop on primary link.
  4. `FAILOVER`: Segment Routing TI-LFA fast reroute activates within 32ms; backup link `HundredGigE0/0/0/2` takes load.
  5. `RECOVER`: Carrier stabilizes link; BGP peering re-establishes nominal session.
  6. `VALIDATE`: Core transit equilibrium restored; backup fast-reroute path disarmed.
* **Telemetry Emitted:** `cisco:ios:xr`, `cisco:ios:mdt:metric` (dual-store to `cisco_mdt_metrics`), `cisco:ios:syslog`. Zero generic fallback.

### 3.4. `arch_wlan_meraki_catalyst`
* **Use Case:** Wireless / RF Health: CleanAir RF Interference & Air Marshal Rogue Suppression
* **Topology:** `arch_wlan_meraki_catalyst` (Cat 9130AX AP $\leftrightarrow$ Meraki MR56 AP $\leftrightarrow$ Cat 9800 WLC $\leftrightarrow$ Core)
* **6-Phase Progression:**
  1. `BASELINE`: CleanAir 5 GHz radio health nominal on channel 36 (utilization 14.2%, noise floor -92 dBm).
  2. `FAULT`: Non-Wi-Fi continuous RF transmitter creates severe interference surge (utilization 94.5%, noise -58 dBm).
  3. `PROPAGATE`: Rogue evil-twin AP broadcasts spoofed corporate SSID `Corp-Executive-Secure` on channel 36.
  4. `FAILOVER`: Dynamic Frequency Selection (DFS) shifts clean traffic to channel 100; Air Marshal suppresses rogue.
  5. `RECOVER`: CleanAir confirms pristine RF spectrum on channel 100 (client SNR restored to 38 dB).
  6. `VALIDATE`: Meraki Air Marshal and Catalyst WLC complete containment audit.
* **Telemetry Emitted:** `cisco:catalyst:clienthealth`, `meraki:accesspoints`, `cisco:catalyst:rogue:threat_details`. Zero generic fallback.

### 3.5. `arch_man_carrier_ring`
* **Use Case:** MAN / Metro Optical: 100G Terrestrial Fiber Cut & G.8032 ERPS Sub-50ms Ring Protection
* **Topology:** `arch_man_carrier_ring` (Nokia 7750 SR-12 RingA/B $\leftrightarrow$ Juniper MX960 RingC/D $\leftrightarrow$ Arista 7280R Leaf)
* **6-Phase Progression:**
  1. `BASELINE`: G.8032 ERPS ring in IDLE state; Ring Protection Link (RPL) blocked on RingA port `1/1/c2`.
  2. `FAULT`: Excavator cuts 100G terrestrial optical fiber between NodeA and NodeC (`SIGNAL_FAIL`).
  3. `PROPAGATE`: R-APS Signal Fail (SF) control frames propagate across Nokia SR-OS and Juniper Junos ring nodes.
  4. `FAILOVER`: Ring Protection Link (RPL) unblocks in 38ms; Arista aggregation leaf switches maintain uninterrupted forwarding.
  5. `RECOVER`: Fiber span spliced; Wait-to-Restore (WTR) timer expires; ring returns to revertive state.
  6. `VALIDATE`: Ring reaches nominal IDLE state; topology equilibrium verified.
* **Telemetry Emitted:** `nokia:sros:syslog`, `juniper:junos`, `arista:eos`. Zero generic fallback.

---

## 4. Deferral Rationale for Remaining 13 Contracted Scenarios

To ensure technical rigor and prevent arbitrary future selection, each deferred scenario is cataloged with its specific deferral rationale:

| Scenario ID | Primary Domain | Technical Deferral Rationale |
| :--- | :--- | :--- |
| `arch_wan_sdwan_dual_cpe` | SD-WAN Multi-CPE | Deferred to avoid functional duplication with existing GP01 (`cisco_sdwan_brownout`). Dual-CPE failover will be promoted in Wave 3 alongside BFD sub-second probing. |
| `arch_can_multi_building` | Multi-Building Campus | Deferred pending Catalyst Center assurance graph synchronization engine. Core campus access is adequately proven by `arch_lan_campus_access`. |
| `arch_dc_leaf_spine` | Datacenter Fabric | Deferred to avoid overlap with GP03 (`cisco_aci_microburst`). Requires multi-tenant EVPN-VXLAN telemetry models planned for Wave 3. |
| `arch_sec_multivendor_fw` | Multi-Vendor Perimeter | Requires synchronization between Fortinet FortiGate, Check Point, and Palo Alto rule-matching engines. Deferred to Wave 3 firewall matrix. |
| `arch_cloud_aws_transit` | Public Cloud / Transit GW | Requires AWS CloudWatch / VPC Flow Log parser enhancements. Deferred to cloud-specific promotion wave. |
| `arch_iot_industrial` | Industrial IoT / SCADA | Requires specialized OT protocols (Modbus / DNP3) not yet prioritized by enterprise SecOps users. |
| `arch_san_fc_storage` | Storage Area Network | Specialized Fibre Channel (FC) buffer credit starvation use case with limited general Splunk observability demand. |
| `mpls_vpn_leak` | Service Provider MPLS | High implementation complexity; L3VPN BGP route-target leak requires multi-VRF graph simulation deferred to advanced routing gate. |
| `bgp_route_leak` | Internet Core Routing | Requires internet-scale peer simulation. Peering collapse is cleanly covered in Wave 2 by `service_provider_cisco`. |
| `dns_amplification` | DDoS / Infrastructure | High volumetric UDP telemetry duplication with existing `ddos_attack` (SYN flood). Deferred to DNS-focused promotion cycle. |
| `ztna_posture_failure` | Zero Trust Remote Access | Requires client-side MDM/EDR telemetry integration (CrowdStrike/Intune) beyond current network scope. |
| `sdwan_underlay_loss` | WAN Underlay Degradation | Overlaps significantly with `cisco_sdwan_brownout` and `mixed_sase_degradation`. |
| `bgp_hijack` | Internet Core / Security | Requires RPKI ROA invalidation models; deferred to inter-domain routing assurance wave. |

---

## 5. Architectural Guardrails Maintained

1. **Zero Architecture Expansion:** Reused standard NetSpout runtime without modifying core message queues or daemon architectures.
2. **Zero Native Transport Injection:** Maintained strict HEC transport modeling (`transport_protocol = "Splunk HEC"`, `fidelity_badge = "MODELED PAYLOAD"`). Native wire socket candidate register created in `docs/architecture/NATIVE_TRANSPORT_CANDIDATES.md`.
3. **Single Source of Truth (SSOT):** Canonical simulation logic centralized in `src/netspout_core/`. Synchronized across all targets with verified SHA-256 integrity.
4. **Golden Paths Invariance:** All 7 Golden Paths (`cisco_sdwan_brownout`, `cisco_campus_rogue`, `cisco_aci_microburst`, `mixed_edge_breach`, `mixed_sase_degradation`, `sql_injection`, `openconfig_mdt_streaming`) execute with zero regression.
