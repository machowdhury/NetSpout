# NetSpout Scenario Catalog Reference

Total Registered Scenarios: **37** across **22** Network Architectural Domains.

| Code | Scenario Name | Domain | Ecosystem | Maturity | Fidelity Badge | Primary Transports |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `ARCH-CAN` | CAN: Campus Area Network - Multi-Building Backbone & Catalyst Center | `NETWORK_OPERATIONS` | pure_cisco | `CONTRACTED` | MODELED PAYLOAD | syslog, snmp |
| `ARCH-EPN` | EPN: Enterprise Private Network - Isolated Corporate Intranet & Multi-Cloud VPC | `NETWORK_OPERATIONS` | both | `CONTRACTED` | MODELED PAYLOAD | syslog, snmp |
| `ARCH-GAN` | GAN: Global Area Network - Worldwide Multi-Cloud & Subsea Cable Transit | `NETWORK_OPERATIONS` | both | `CONTRACTED` | MODELED PAYLOAD | syslog, snmp |
| `ARCH-LAN` | LAN: Local Area Network - Campus Switching & 802.1Q Segments | `NETWORK_OPERATIONS` | pure_cisco | `GOLDEN_PATH_CERTIFIED` | MODELED PAYLOAD | syslog, hec |
| `ARCH-MAN` | MAN: Metropolitan Area Network - 100G Carrier Ethernet Ring & G.8032 ERPS | `SERVICE_PROVIDER` | mixed_vendor | `GOLDEN_PATH_CERTIFIED` | MODELED PAYLOAD | syslog, hec |
| `ARCH-NAS` | NAS: Network-Attached Storage - NetApp ONTAP & PowerScale Clusters | `DATACENTER` | both | `CONTRACTED` | MODELED PAYLOAD | syslog, snmp |
| `ARCH-PAN` | PAN: Personal Area Network - IoT Sensor Cluster & Bluetooth Mesh | `NETWORK_OPERATIONS` | both | `CONTRACTED` | MODELED PAYLOAD | syslog, snmp |
| `ARCH-SAN` | SAN: Storage Area Network - Cisco MDS 9700 Fibre Channel & NVMe-oF | `DATACENTER` | both | `CONTRACTED` | MODELED PAYLOAD | syslog, snmp |
| `ARCH-VPN` | VPN: Virtual Private Network - Cisco AnyConnect & Site-to-Site IPsec | `WAN` | both | `GOLDEN_PATH_CERTIFIED` | MODELED PAYLOAD | syslog, hec |
| `ARCH-WAN` | WAN: Wide Area Network - Global BGP/MPLS L3VPN Backbone & Optical DWDM | `WAN` | both | `CONTRACTED` | MODELED PAYLOAD | syslog, snmp |
| `ARCH-WLAN` | WLAN: Wireless Local Area Network - Catalyst 9800 & Meraki Wi-Fi 6E/7 | `WIRELESS` | both | `GOLDEN_PATH_CERTIFIED` | MODELED PAYLOAD | syslog, hec |
| `CISCO-A3` | Data Center Fabric ACI Ingress Microburst Traffic | `DATACENTER` | pure_cisco | `GOLDEN_PATH_CERTIFIED` | MODELED PAYLOAD | gnmi, syslog |
| `CISCO-A1` | Campus Core L2/3 Disturbance & Rogue AP | `WIRELESS` | pure_cisco | `GOLDEN_PATH_CERTIFIED` | MODELED PAYLOAD | syslog, snmp |
| `CISCO-A2` | Enterprise WAN Circuit Brownout & App Route Failover | `WAN` | pure_cisco | `GOLDEN_PATH_CERTIFIED` | MODELED PAYLOAD | syslog, gnmi, snmp |
| `BASE-02` | Distributed Denial of Service (DDoS SYN Flood) | `SECURITY` | both | `E2E_VALIDATED` | MODELED PAYLOAD | syslog, hec |
| `BASE-04` | Ransomware / Lateral Spread (Port 445) | `SECURITY` | both | `FORMAT_VALIDATED` | MODELED PAYLOAD | syslog, snmp |
| `MIXED-B3` | Multicast/MPLS Backbone Optical Carrier Shift | `DATACENTER` | mixed_vendor | `GOLDEN_PATH_CERTIFIED` | MODELED PAYLOAD | syslog, hec |
| `MIXED-B1` | Distributed Edge Breach & Internal Probing | `SECURITY` | mixed_vendor | `GOLDEN_PATH_CERTIFIED` | MODELED PAYLOAD | syslog, hec |
| `MIXED-B2` | SASE Cloud Ingress App Degradation & Synthetic Validation | `NETWORK_OPERATIONS` | mixed_vendor | `GOLDEN_PATH_CERTIFIED` | MODELED PAYLOAD | syslog, hec |
| `MIXED-ALL` | Mixed-Vendor Enterprise Network (Cisco, Arista, Palo Alto, Fortinet, Juniper, Aruba) | `NETWORK_OPERATIONS` | mixed_vendor | `CONTRACTED` | MODELED PAYLOAD | syslog, hec |
| `BASE-01` | Normal Operations (HTTP Round-Robin) | `NETWORK_OPERATIONS` | both | `FORMAT_VALIDATED` | MODELED PAYLOAD | syslog, snmp |
| `OC-001` | OpenConfig MDT Streaming & Telemetry Assurance | `SERVICE_ASSURANCE` | both | `GOLDEN_PATH_CERTIFIED` | MODELED PAYLOAD | gnmi, hec |
| `CISCO-ALL` | Pure Cisco Enterprise Fabric (Catalyst 9600, 9500, 9300, 9800, ISE, DNA-C) | `NETWORK_OPERATIONS` | pure_cisco | `CONTRACTED` | MODELED PAYLOAD | syslog, snmp |
| `SDWAN-CORE` | Separate SD-WAN Environment Connected to Core Backbone (All Cisco) | `WAN` | pure_cisco | `CONTRACTED` | MODELED PAYLOAD | syslog, snmp |
| `SP-CISCO` | Service Provider Network - All Cisco (Cisco 8000, NCS 5500, IOS-XR SRv6) | `SERVICE_PROVIDER` | pure_cisco | `GOLDEN_PATH_CERTIFIED` | MODELED PAYLOAD | syslog, gnmi, snmp |
| `SP-MIXED` | Service Provider Network - Mixed Vendor (Cisco 8000, Juniper PTX, Nokia 7750) | `SERVICE_PROVIDER` | mixed_vendor | `CONTRACTED` | MODELED PAYLOAD | syslog, snmp |
| `BASE-03` | SQL Injection / Application Breach | `SECURITY` | both | `GOLDEN_PATH_CERTIFIED` | MODELED PAYLOAD | syslog, hec |
| `WLAN-CORE-C` | Enterprise Wireless Connected to Campus Core (All Cisco) | `WIRELESS` | pure_cisco | `CONTRACTED` | MODELED PAYLOAD | syslog, snmp |
| `WLAN-CORE-M` | Enterprise Wireless Connected to Core (Mixed Vendor) | `WIRELESS` | mixed_vendor | `CONTRACTED` | MODELED PAYLOAD | syslog, snmp |
| `MPLS-01` | MPLS LDP Session Down & Core LSP Convergence | `SERVICE_PROVIDER` | mixed_vendor | `CONTRACTED` | MODELED PAYLOAD | Syslog, SNMP, gNMI |
| `SRV6-01` | SRv6 SID Path Failure & Topology-Independent LFA Reroute | `SERVICE_PROVIDER` | pure_cisco | `CONTRACTED` | MODELED PAYLOAD | Syslog, gNMI |
| `DC-CLOS-01` | Data Center Leaf-Spine Buffer Microburst & Incast Congestion | `DATACENTER` | mixed_vendor | `CONTRACTED` | MODELED PAYLOAD | Syslog, gNMI, Flow |
| `EVPN-01` | BGP EVPN / VXLAN Fabric MAC Mobility & Route Loop Detection | `DATACENTER` | mixed_vendor | `CONTRACTED` | MODELED PAYLOAD | Syslog, gNMI |
| `SAN-HPC-01` | System Area Network Heartbeat Loss & Dual-Link Interconnect Failover | `NETWORK_OPERATIONS` | mixed_vendor | `CONTRACTED` | MODELED PAYLOAD | Syslog, HEC |
| `POLAN-01` | Passive Optical LAN (POLAN) Feeder Fiber Attenuation & ONT Loss | `NETWORK_OPERATIONS` | mixed_vendor | `CONTRACTED` | MODELED PAYLOAD | Syslog, SNMP |
| `IBN-01` | Intent-Based Fabric Policy Drift & Automated Compliance Remediation | `NETWORK_OPERATIONS` | pure_cisco | `CONTRACTED` | MODELED PAYLOAD | Syslog, HEC |
| `AI-FAB-01` | AI Lossless Fabric RoCEv2 Incast Congestion & PFC Deadlock Warning | `DATACENTER` | mixed_vendor | `CONTRACTED` | MODELED PAYLOAD | Syslog, gNMI, SNMP |

## Scenario Details by Domain

### Domain: Enterprise LAN (`LAN`)
Campus local area switching, 802.1Q VLAN trunking, STP/RSTP topology changes, and port security.

- **LAN: Local Area Network - Campus Switching & 802.1Q Segments** (`ARCH-LAN`): High-density campus LAN with Cisco Catalyst 9300/9500 switches, 802.1Q trunking, DHCP snooping, and ARP inspection.
  - *Sourcetypes*: `['cisco:catalyst:security:events', 'cisco:ios:syslog', 'cisco:ise:nac:8021x']`
  - *Fidelity*: MODELED PAYLOAD | *Maturity*: `GOLDEN_PATH_CERTIFIED`
- **Pure Cisco Enterprise Fabric (Catalyst 9600, 9500, 9300, 9800, ISE, DNA-C)** (`CISCO-ALL`): Unified Cisco enterprise architecture spanning core, distribution, access, wireless, and identity.
  - *Sourcetypes*: `['cisco:catalyst:networkhealth', 'cisco:ise:nac:8021x', 'cisco:ise:trustsec:sgt', 'cisco:catalyst:rogue:threat_details']`
  - *Fidelity*: MODELED PAYLOAD | *Maturity*: `CONTRACTED`
- **Campus Core L2/3 Disturbance & Rogue AP** (`CISCO-A1`): Unsanctioned Rogue AP connects to campus switch; Cisco ISE applies 802.1X quarantine while Catalyst core detects MAC flapping.
  - *Sourcetypes*: `['cisco:catalyst:security:events', 'cisco:catalyst:rogue:threat_details', 'cisco:ise:syslog', 'cisco:ios:syslog']`
  - *Fidelity*: MODELED PAYLOAD | *Maturity*: `GOLDEN_PATH_CERTIFIED`
- **Normal Operations (HTTP Round-Robin)** (`BASE-01`): Legitimate external clients make distributed HTTP requests passing through Firewall and Load Balancer to Web tier.
  - *Sourcetypes*: `['cisco:asa', 'pan:traffic', 'f5:bigip:ltm', 'nginx:plus:kv', 'postgresql:audit']`
  - *Fidelity*: MODELED PAYLOAD | *Maturity*: `FORMAT_VALIDATED`

### Domain: Wireless LAN (WLAN) (`WLAN`)
Enterprise Wi-Fi 6E/7 infrastructure, Catalyst 9800 / Meraki access points, client roaming, and RF interference.

- **WLAN: Wireless Local Area Network - Catalyst 9800 & Meraki Wi-Fi 6E/7** (`ARCH-WLAN`): Dual-vendor campus wireless with Catalyst 9800 WLC and Meraki MR56 APs tracking client roaming, SNR, and CleanAir interference.
  - *Sourcetypes*: `['cisco:catalyst:rogue:threat_details', 'meraki:accesspoints', 'cisco:catalyst:clienthealth']`
  - *Fidelity*: MODELED PAYLOAD | *Maturity*: `GOLDEN_PATH_CERTIFIED`
- **Enterprise Wireless Connected to Campus Core (All Cisco)** (`WLAN-CORE-C`): Catalyst 9800 WLC trunking wireless VLANs directly into Catalyst 9600 core switches.
  - *Sourcetypes*: `['cisco:catalyst:clienthealth', 'cisco:catalyst:rogue:threat_details', 'cisco:ise:nac:8021x']`
  - *Fidelity*: MODELED PAYLOAD | *Maturity*: `CONTRACTED`
- **Enterprise Wireless Connected to Core (Mixed Vendor)** (`WLAN-CORE-M`): Meraki and Aruba APs routing through Palo Alto NGFW into Arista 7280 core.
  - *Sourcetypes*: `['meraki:accesspoints', 'pan:traffic', 'arista:telemetry:json']`
  - *Fidelity*: MODELED PAYLOAD | *Maturity*: `CONTRACTED`

### Domain: Campus Area Network (CAN) (`CAN`)
Multi-building fiber interconnects, redundant core routing, and Cisco Catalyst Center / DNA-C assurance.

- **CAN: Campus Area Network - Multi-Building Backbone & Catalyst Center** (`ARCH-CAN`): Multi-building campus network with redundant Catalyst 9600 cores, 100G fiber interconnects, and DNA Center automated assurance.
  - *Sourcetypes*: `['cisco:catalyst:networkhealth', 'cisco:ios:syslog', 'cisco:ise:trustsec:sgt']`
  - *Fidelity*: MODELED PAYLOAD | *Maturity*: `CONTRACTED`

### Domain: Wide Area Network (WAN) (`WAN`)
Carrier transit links, BGP route flapping, MPLS provider interconnects, and DWDM optical interfaces.

- **WAN: Wide Area Network - Global BGP/MPLS L3VPN Backbone & Optical DWDM** (`ARCH-WAN`): Inter-continental enterprise WAN with BGP EVPN, segment routing SRv6, and MPLS traffic engineering tunnels.
  - *Sourcetypes*: `['cisco:ios:mdt:metric', 'cisco:ios:syslog', 'juniper:junos']`
  - *Fidelity*: MODELED PAYLOAD | *Maturity*: `CONTRACTED`

### Domain: Software-Defined WAN (SD-WAN) (`SDWAN`)
Cisco Catalyst SD-WAN / Viptela BFD tunnel loss, SLA jitter/latency brownout, and app-aware route failover.

- **Enterprise WAN Circuit Brownout & App Route Failover** (`CISCO-A2`): MPLS transport experiences high latency and packet loss; Cisco SD-WAN vEdge triggers SLA violation and BGP failover to secondary LTE/Broadband.
  - *Sourcetypes*: `['cisco:sdwan:linkhealth', 'cisco:sdwan:BGP-5-ADJCHANGE', 'cisco:thousandeyes:path-vis', 'cisco:thousandeyes:metric']`
  - *Fidelity*: MODELED PAYLOAD | *Maturity*: `GOLDEN_PATH_CERTIFIED`
- **Separate SD-WAN Environment Connected to Core Backbone (All Cisco)** (`SDWAN-CORE`): Catalyst SD-WAN fabric peering dynamically with Catalyst 9600 campus core.
  - *Sourcetypes*: `['cisco:sdwan:linkhealth', 'cisco:sdwan:BGP-5-ADJCHANGE', 'cisco:ios:syslog']`
  - *Fidelity*: MODELED PAYLOAD | *Maturity*: `CONTRACTED`

### Domain: Virtual Private Network (VPN) (`VPN`)
Remote workforce AnyConnect / Secure Client, IPsec IKEv2 Phase 1/2 tunnel flaps, and posture validation.

- **VPN: Virtual Private Network - Cisco AnyConnect & Site-to-Site IPsec** (`ARCH-VPN`): Remote access VPN concentrator and IPsec crypto tunnels supporting 10,000+ concurrent workforce sessions with Duo MFA integration.
  - *Sourcetypes*: `['cisco:duo:remote:vpn', 'cisco:duo:push:prompt', 'cisco:asa']`
  - *Fidelity*: MODELED PAYLOAD | *Maturity*: `GOLDEN_PATH_CERTIFIED`

### Domain: SASE / Security Service Edge (SSE) (`SASE_SSE`)
Cloud security gateway, CASB inspection, ZTNA authentication degradation, and synthetic endpoint probing.

- **SASE Cloud Ingress App Degradation & Synthetic Validation** (`MIXED-B2`): Zscaler/Cloudflare edge proxy experiences SSL inspection latency surge; Palo Alto SD-WAN queues sessions and ThousandEyes detects SaaS TTFB slowdown.
  - *Sourcetypes*: `['zscaler:zia', 'pan:threat', 'cisco:thousandeyes:metric', 'cisco:dc:nexus9k:syslog']`
  - *Fidelity*: MODELED PAYLOAD | *Maturity*: `GOLDEN_PATH_CERTIFIED`

### Domain: Service Provider Core & Edge (`SP`)
Carrier-grade routing (Cisco 8000, NCS 5500, Juniper PTX, Nokia 7750), multi-chassis core, and multi-AS transit.

- **Service Provider Network - All Cisco (Cisco 8000, NCS 5500, IOS-XR SRv6)** (`SP-CISCO`): Carrier-scale Cisco 8000 / NCS core running Segment Routing over IPv6 (SRv6).
  - *Sourcetypes*: `['cisco:ios:mdt:metric', 'cisco:ios:syslog', 'netspout:snmp:trap', 'netspout:snmp:poll']`
  - *Fidelity*: MODELED PAYLOAD | *Maturity*: `GOLDEN_PATH_CERTIFIED`
- **Service Provider Network - Mixed Vendor (Cisco 8000, Juniper PTX, Nokia 7750)** (`SP-MIXED`): Tier-1 carrier transit core with Cisco, Juniper, and Nokia interconnects.
  - *Sourcetypes*: `['juniper:junos', 'nokia:sros:syslog', 'cisco:ios:mdt:metric']`
  - *Fidelity*: MODELED PAYLOAD | *Maturity*: `CONTRACTED`

### Domain: MPLS & LDP Core (`MPLS_LDP`)
Label Distribution Protocol (LDP) adjacency loss, MPLS-TE tunnel re-routing, and targeted LDP peering failures.

- **MPLS LDP Session Down & Core LSP Convergence** (`MPLS-01`): Simulates an MPLS Label Distribution Protocol (LDP) adjacency loss between P and PE routers, triggering fast label withdrawal and backup LSP convergence.
  - *Sourcetypes*: `['cisco:ios:mpls', 'cisco:ios:syslog', 'juniper:junos:syslog']`
  - *Fidelity*: MODELED PAYLOAD | *Maturity*: `CONTRACTED`

### Domain: Segment Routing (SR-MPLS / SRv6) (`SR_SRV6`)
Segment Routing over IPv6 (SRv6), SID allocation, TI-LFA sub-50ms fast reroute, and Micro-SID telemetry.

- **SRv6 SID Path Failure & Topology-Independent LFA Reroute** (`SRV6-01`): Models a carrier Segment Routing over IPv6 (SRv6) transit link failure where TI-LFA activates sub-50ms protection using pre-computed backup segment lists.
  - *Sourcetypes*: `['cisco:ios:srv6', 'cisco:ios:syslog']`
  - *Fidelity*: MODELED PAYLOAD | *Maturity*: `CONTRACTED`

### Domain: Metropolitan Area Network (MAN) & Optical (`MAN_OPTICAL`)
Carrier Ethernet G.8032 ring protection switching, DWDM EDFA amplifier optical power shifts, and ROADM attenuation.

- **MAN: Metropolitan Area Network - 100G Carrier Ethernet Ring & G.8032 ERPS** (`ARCH-MAN`): Metro optical ring spanning 4 data centers with ITU-T G.8032 Ethernet Ring Protection Switching (ERPS) sub-50ms failover.
  - *Sourcetypes*: `['nokia:sros:syslog', 'juniper:junos', 'arista:eos']`
  - *Fidelity*: MODELED PAYLOAD | *Maturity*: `GOLDEN_PATH_CERTIFIED`
- **Multicast/MPLS Backbone Optical Carrier Shift** (`MIXED-B3`): DWDM Loss-of-Signal alarm on Nokia SR-OS core triggers Juniper Junos RSVP-TE Fast Reroute (FRR) switchover; Arista IPFIX telemetry tracks rerouted flow.
  - *Sourcetypes*: `['nokia:sros:syslog', 'juniper:junos', 'arista:flow:ipfix']`
  - *Fidelity*: MODELED PAYLOAD | *Maturity*: `GOLDEN_PATH_CERTIFIED`

### Domain: Data Center Leaf-Spine (Clos Fabric) (`DC_CLOS`)
Spine-leaf IP fabric, ECMP hashing imbalances, queue buffer microbursts, and Arista EOS LANZ telemetry.

- **Data Center Leaf-Spine Buffer Microburst & Incast Congestion** (`DC-CLOS-01`): Simulates synchronization of multi-server query replies causing egress port buffer exhaustion, latency analyzer microburst alarms, and tail drops.
  - *Sourcetypes*: `['arista:eos:lanz', 'arista:eos:syslog', 'cisco:dc:nexus9k:syslog']`
  - *Fidelity*: MODELED PAYLOAD | *Maturity*: `CONTRACTED`

### Domain: BGP EVPN & VXLAN Overlay (`EVPN_VXLAN`)
Network virtualization overlay, BGP EVPN Type-2 MAC/IP advertisement, VTEP reachability, and MAC mobility loops.

- **BGP EVPN / VXLAN Fabric MAC Mobility & Route Loop Detection** (`EVPN-01`): Demonstrates rapid virtual machine migration causing EVPN Type-2 MAC/IP route updates across VTEPs, triggering MAC mobility duplicate sequence warnings.
  - *Sourcetypes*: `['cisco:nexus:evpn', 'juniper:junos:syslog']`
  - *Fidelity*: MODELED PAYLOAD | *Maturity*: `CONTRACTED`

### Domain: Cisco Application Centric Infrastructure (ACI) (`CISCO_ACI`)
APIC SDN policy-driven data center switching, endpoint groups (EPG), microburst traffic, and fabric health scoring.

- **Data Center Fabric ACI Ingress Microburst Traffic** (`CISCO-A3`): Microburst traffic pattern saturates Nexus 9K leaf switch ingress ASIC buffers; ACI fabric health score drops and MDT telemetry flags queue incast.
  - *Sourcetypes*: `['cisco:dc:nexus9k:syslog', 'cisco:dc:aci:health', 'cisco:ios:mdt']`
  - *Fidelity*: MODELED PAYLOAD | *Maturity*: `GOLDEN_PATH_CERTIFIED`

### Domain: Cloud & Hybrid Connectivity (`CLOUD_HYBRID`)
AWS Direct Connect, Azure ExpressRoute, cloud interconnect gateways, and VPC transit routing flaps.

- **EPN: Enterprise Private Network - Isolated Corporate Intranet & Multi-Cloud VPC** (`ARCH-EPN`): Private multi-tenant enterprise intranet connecting physical branches and cloud VPCs via private QinQ 802.1ad and MPLS pseudo-wires.
  - *Sourcetypes*: `['cisco:ios:syslog', 'cisco:sdwan:linkhealth']`
  - *Fidelity*: MODELED PAYLOAD | *Maturity*: `CONTRACTED`
- **GAN: Global Area Network - Worldwide Multi-Cloud & Subsea Cable Transit** (`ARCH-GAN`): Trans-continental global network connecting AWS Direct Connect, Azure ExpressRoute, and subsea cable landing stations.
  - *Sourcetypes*: `['cisco:ios:mdt:metric', 'zscaler:zia', 'cisco:thousandeyes:metric']`
  - *Fidelity*: MODELED PAYLOAD | *Maturity*: `CONTRACTED`

### Domain: Network Security & Threat Operations (`SECURITY`)
SYN flood DDoS mitigation, lateral movement ransomware detection, SQL injection, and perimeter breach response.

- **Distributed Denial of Service (DDoS SYN Flood)** (`BASE-02`): Malicious botnet IPs launch high-rate TCP SYN floods targeting internal infrastructure.
  - *Sourcetypes*: `['cisco:asa', 'f5:bigip:ltm', 'nginx:plus:kv']`
  - *Fidelity*: MODELED PAYLOAD | *Maturity*: `E2E_VALIDATED`
- **Ransomware / Lateral Spread (Port 445)** (`BASE-04`): Malware attempts lateral propagation between internal servers across subnet boundaries using SMB Port 445.
  - *Sourcetypes*: `['cisco:ios:syslog', 'cisco:asa', 'postgresql:audit']`
  - *Fidelity*: MODELED PAYLOAD | *Maturity*: `FORMAT_VALIDATED`
- **SQL Injection / Application Breach** (`BASE-03`): Adversary injects malicious SQL exploitation payload through HTTP query parameters targeting Database backend.
  - *Sourcetypes*: `['cisco:asa', 'nginx:plus:kv', 'postgresql:audit']`
  - *Fidelity*: MODELED PAYLOAD | *Maturity*: `GOLDEN_PATH_CERTIFIED`
- **Distributed Edge Breach & Internal Probing** (`MIXED-B1`): Attacker probes wireless network via Meraki AP through Catalyst Core toward internal servers; Palo Alto NGFW inspects traffic.
  - *Sourcetypes*: `['meraki:assurancealerts', 'pan:threat', 'pan:traffic', 'fortinet:fortigate:utm', 'nginx:plus:kv']`
  - *Fidelity*: MODELED PAYLOAD | *Maturity*: `GOLDEN_PATH_CERTIFIED`

### Domain: Storage Area Network (SAN & NAS) (`SAN_NAS`)
Cisco MDS Fibre Channel fabric, NVMe-oF latency spikes, NetApp ONTAP NFS/SMB throttling, and storage port errors.

- **SAN: Storage Area Network - Cisco MDS 9700 Fibre Channel & NVMe-oF** (`ARCH-SAN`): Enterprise storage area network fabric with Cisco MDS 9700 64G FC directors, zoning, and buffer-to-buffer credit starvation telemetry.
  - *Sourcetypes*: `['cisco:mds:san:fc', 'cisco:dc:nexus9k:syslog']`
  - *Fidelity*: MODELED PAYLOAD | *Maturity*: `CONTRACTED`
- **NAS: Network-Attached Storage - NetApp ONTAP & PowerScale Clusters** (`ARCH-NAS`): High-throughput NAS cluster serving petabyte NFSv4.1 and SMB3 workloads with IOPS burst tracking and volume latency metrics.
  - *Sourcetypes*: `['netapp:ontap:nas', 'arista:telemetry:json']`
  - *Fidelity*: MODELED PAYLOAD | *Maturity*: `CONTRACTED`

### Domain: System Area Network & HPC Interconnect (`SYSTEM_AREA`)
High-performance computing cluster interconnect, dual-redundant low-latency fabric, and node heartbeat failover.

- **System Area Network Heartbeat Loss & Dual-Link Interconnect Failover** (`SAN-HPC-01`): Models a redundant compute cluster heartbeat link drop, quorum renegotiation, and seamless traffic failover to the secondary low-latency transit path.
  - *Sourcetypes*: `['cisco:ios:syslog', 'nutanixpc_clusters']`
  - *Fidelity*: MODELED PAYLOAD | *Maturity*: `CONTRACTED`

### Domain: Passive Optical LAN (POLAN) (`POLAN`)
Enterprise GPON / XGS-PON, optical line terminal (OLT) feeder fiber attenuation, and optical network terminal (ONT) link loss.

- **Passive Optical LAN (POLAN) Feeder Fiber Attenuation & ONT Loss** (`POLAN-01`): Simulates GPON/XGS-PON optical feeder fiber micro-bend attenuation exceeding dB loss budget, leading to dying gasp and Loss of Signal (LOS) across downstream ONTs.
  - *Sourcetypes*: `['nokia:sros:syslog']`
  - *Fidelity*: MODELED PAYLOAD | *Maturity*: `CONTRACTED`

### Domain: Intent-Based Networking (IBN) (`INTENT_BASED`)
Cisco Catalyst Center / Software-Defined Access (SDA) intent drift, automated SLA assurance, and policy reconciliation.

- **Intent-Based Fabric Policy Drift & Automated Compliance Remediation** (`IBN-01`): Models unauthorized manual CLI configuration changes on an enterprise edge switch, divergence detection by Catalyst Center (DNA-C), and automated intent enforcement.
  - *Sourcetypes*: `['cisco:catalyst:compliance', 'cisco:catalyst:issue', 'cisco:catalyst:devicehealth']`
  - *Fidelity*: MODELED PAYLOAD | *Maturity*: `CONTRACTED`

### Domain: AI Lossless Fabric (RoCEv2 / InfiniBand) (`AI_LOSSLESS`)
GPU cluster backend fabric, RoCEv2 incast congestion, Priority Flow Control (PFC) pauses, and ECN early marking.

- **AI Lossless Fabric RoCEv2 Incast Congestion & PFC Deadlock Warning** (`AI-FAB-01`): Models an all-to-all collective communication phase in a multi-node GPU training job, creating buffer queue incast, PFC pause storms, and ECN early congestion marking.
  - *Sourcetypes*: `['nvidia:spectrum:telemetry', 'arista:eos:syslog']`
  - *Fidelity*: MODELED PAYLOAD | *Maturity*: `CONTRACTED`

### Domain: Edge AI & IoT Sensor Mesh (`EDGE_AI`)
Distributed edge gateways, IoT Bluetooth mesh nodes, intermittent wireless sensor connectivity, and telemetry batching.

- **PAN: Personal Area Network - IoT Sensor Cluster & Bluetooth Mesh** (`ARCH-PAN`): Short-range IoT sensor mesh monitoring environmental conditions, temperature, humidity, and Bluetooth LE beacon telemetry.
  - *Sourcetypes*: `['pan:ble:iot:sensor', 'cisco:ios:syslog']`
  - *Fidelity*: MODELED PAYLOAD | *Maturity*: `CONTRACTED`
