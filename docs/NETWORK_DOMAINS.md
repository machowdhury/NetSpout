# NetSpout 22-Domain Network Architecture Specification

## Overview

NetSpout provides a comprehensive **Network Digital Telemetry Lab** covering 22 modern network domains. Each domain is defined with authentic device roles, standard topologies, supported telemetry protocols, and canonical scenarios.

---

## The 22 Network Architectural Domains

### 1. Enterprise LAN (`LAN`)
- **Focus**: Campus local area access and distribution switching, 802.1Q VLAN trunking, Spanning Tree Protocol (STP/RSTP), 802.1X port security.
- **Key Scenarios**: `arch_lan_campus_access`, `pure_cisco_enterprise`, `cisco_campus_rogue`, `normal_traffic`
- **Supported Transports**: Syslog, SNMP, NetFlow v9, HEC, gNMI

### 2. Wireless LAN (`WLAN`)
- **Focus**: Enterprise Wi-Fi 6E / Wi-Fi 7 infrastructure, Catalyst 9800 WLC, Cisco Meraki cloud dashboard, client roaming, RF channel interference, rogue AP detection.
- **Key Scenarios**: `arch_wlan_meraki_catalyst`, `wireless_connected_core_cisco`, `wireless_connected_core_mixed`
- **Supported Transports**: Syslog, SNMP, HEC

### 3. Campus Area Network (`CAN`)
- **Focus**: Multi-building enterprise backbone, redundant 100G fiber interconnects, OSPF/EIGRP area routing, Cisco Catalyst Center (DNA-C) automated assurance.
- **Key Scenarios**: `arch_can_multi_building`
- **Supported Transports**: Syslog, SNMP, HEC, gNMI

### 4. Wide Area Network (`WAN`)
- **Focus**: Global provider WAN transit, BGP route flaps, MPLS L3VPN provider edges, DWDM optical interconnects.
- **Key Scenarios**: `arch_wan_global_backbone`
- **Supported Transports**: Syslog, SNMP, IPFIX, HEC, gNMI

### 5. Software-Defined WAN (`SDWAN`)
- **Focus**: Cisco Catalyst SD-WAN (Viptela), vSmart controllers, vEdge/cEdge routers, BFD tunnel loss, SLA jitter/latency brownouts, application-aware route failover.
- **Key Scenarios**: `cisco_sdwan_brownout` (Golden Path), `sdwan_connected_core`
- **Supported Transports**: Syslog, SNMP, IPFIX, HEC, gNMI

### 6. Virtual Private Network (`VPN`)
- **Focus**: Remote workforce Cisco AnyConnect / Secure Client, IPsec IKEv2 Phase 1/2 tunnel negotiations, posture validation with Cisco ISE.
- **Key Scenarios**: `arch_vpn_remote_workforce`
- **Supported Transports**: Syslog, SNMP, HEC

### 7. SASE & Security Service Edge (`SASE_SSE`)
- **Focus**: Secure Access Service Edge, Cloud Access Security Broker (CASB), Zero Trust Network Access (ZTNA) degradation, Palo Alto Prisma / FortiSASE synthetic validation.
- **Key Scenarios**: `mixed_sase_degradation`
- **Supported Transports**: Syslog, HEC

### 8. Service Provider Core & Edge (`SP`)
- **Focus**: Carrier-grade routing fabrics (Cisco 8000, NCS 5500, Juniper PTX, Nokia 7750 SR), multi-AS transit, carrier peering.
- **Key Scenarios**: `service_provider_cisco`, `service_provider_mixed`
- **Supported Transports**: Syslog, SNMP, IPFIX, HEC, gNMI

### 9. MPLS & LDP Core (`MPLS_LDP`)
- **Focus**: Label Distribution Protocol (RFC 5036), MPLS label binding failures, RSVP-TE fast reroute, LSP convergence.
- **Key Scenarios**: `mpls_ldp_lsp_failure`
- **Supported Transports**: Syslog, SNMP, IPFIX, HEC

### 10. Segment Routing (`SR_SRV6`)
- **Focus**: Segment Routing over IPv6 (SRv6), SID allocation, Topology-Independent Loop-Free Alternate (TI-LFA) sub-50ms protection.
- **Key Scenarios**: `srv6_tilfa_fast_reroute`
- **Supported Transports**: Syslog, gNMI, HEC

### 11. MAN & Carrier Optical (`MAN_OPTICAL`)
- **Focus**: ITU-T G.8032 Ethernet Ring Protection Switching (ERPS), DWDM EDFA amplifier optical power shifts, ROADM attenuation.
- **Key Scenarios**: `arch_man_carrier_ring`, `mixed_backbone_optical`
- **Supported Transports**: Syslog, SNMP, HEC

### 12. Data Center Leaf-Spine (`DC_CLOS`)
- **Focus**: Clos fabric spine-leaf architecture, ECMP hashing imbalances, Arista EOS LANZ microburst telemetry, buffer congestion.
- **Key Scenarios**: `dc_leaf_spine_microburst`
- **Supported Transports**: Syslog, gNMI, HEC, IPFIX

### 13. BGP EVPN & VXLAN (`EVPN_VXLAN`)
- **Focus**: Data center network virtualization, BGP EVPN Type-2 MAC/IP routes, VTEP flood lists, MAC mobility and loop suppression.
- **Key Scenarios**: `evpn_vxlan_mac_mobility`
- **Supported Transports**: Syslog, SNMP, HEC, gNMI

### 14. Cisco ACI (`CISCO_ACI`)
- **Focus**: Cisco Application Centric Infrastructure, APIC controllers, Spine-Leaf policy fabric, Endpoint Groups (EPG), microburst detection.
- **Key Scenarios**: `cisco_aci_microburst`
- **Supported Transports**: Syslog, SNMP, HEC

### 15. Cloud & Hybrid Connectivity (`CLOUD_HYBRID`)
- **Focus**: Direct Connect, Azure ExpressRoute, Cloud Interconnect, multi-cloud VPC routing flaps.
- **Key Scenarios**: `arch_epn_isolated_intranet`, `arch_gan_subsea_cloud`
- **Supported Transports**: Syslog, HEC, NetFlow v9

### 16. Network Security & Threat Operations (`SECURITY`)
- **Focus**: DDoS SYN flood volumetric attacks, lateral movement (SMB port 445), SQL injection web app breaches, perimeter DMZ firewall events.
- **Key Scenarios**: `ddos_attack`, `lateral_movement`, `sql_injection`, `mixed_edge_breach`
- **Supported Transports**: Syslog, NetFlow v9, IPFIX, HEC

### 17. Storage Area Networks (`SAN_NAS`)
- **Focus**: Cisco MDS 9700 Fibre Channel fabric, FLOGI/PLOGI login states, NVMe-oF latency spikes, NetApp ONTAP NFS/SMB throttling.
- **Key Scenarios**: `arch_san_fibre_channel`, `arch_nas_storage_cluster`
- **Supported Transports**: Syslog, SNMP, HEC

### 18. System Area Network & HPC Interconnect (`SYSTEM_AREA`)
- **Focus**: High-performance compute clusters, low-latency interconnects, dual-link heartbeat loss and failover.
- **Key Scenarios**: `cluster_interconnect_failover`
- **Supported Transports**: Syslog, SNMP, HEC

### 19. Passive Optical LAN (`POLAN`)
- **Focus**: Enterprise GPON / XGS-PON, Optical Line Terminal (OLT) feeder fiber attenuation, Optical Network Terminal (ONT) optical budget loss.
- **Key Scenarios**: `polan_olt_fiber_attenuation`
- **Supported Transports**: Syslog, SNMP, HEC

### 20. Intent-Based Networking (`INTENT_BASED`)
- **Focus**: Cisco Catalyst Center (DNA-C), Software-Defined Access (SDA) virtual networks, intent drift detection, policy reconciliation.
- **Key Scenarios**: `intent_policy_divergence`
- **Supported Transports**: Syslog, HEC, gNMI

### 21. AI Lossless Fabric (`AI_LOSSLESS`)
- **Focus**: GPU training backend fabric, IEEE 802.1Qbb Priority Flow Control (PFC) pause frames, RFC 3168 ECN congestion marking, RoCEv2 incast congestion.
- **Key Scenarios**: `ai_fabric_rocev2_incast`
- **Supported Transports**: Syslog, gNMI, HEC

### 22. Edge AI & IoT Mesh (`EDGE_AI`)
- **Focus**: Industrial edge gateways, Bluetooth Low Energy (BLE) / 802.15.4 mesh nodes, intermittent wireless sensor connectivity, telemetry batching.
- **Key Scenarios**: `arch_pan_iot_mesh`
- **Supported Transports**: Syslog, HEC
