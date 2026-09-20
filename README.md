# NetSpout ⚡

**Splunk-Native Network Simulation, Multi-Protocol Telemetry Generation & Interactive SPL Playground**

[![Splunk Enterprise](https://img.shields.io/badge/Splunk_Enterprise-9.0%2B_|_Cloud-ed5b26.svg?logo=splunk&logoColor=white)](https://www.splunk.com/)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![OpenConfig](https://img.shields.io/badge/YANG-OpenConfig_RFC7950-emerald.svg)](https://www.openconfig.net/)
[![TypeScript](https://img.shields.io/badge/Frontend-React_TypeScript-3178c6.svg?logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Python](https://img.shields.io/badge/Backend-FastAPI_Python_3.11%2B-3776ab.svg?logo=python&logoColor=white)](https://fastapi.tiangolo.com/)

NetSpout is a production-ready, Splunk-native Network Simulation and Multi-Protocol Telemetry Generation platform engineered for network engineers, SOC analysts, and SREs. It pairs a visual, drag-and-drop network topology canvas with a high-throughput multi-protocol telemetry generation engine, an **interactive Jupyter-like SPL Playground**, an automated **NOC/SOC Use Case Test Harness**, OpenConfig model-driven telemetry (MDT), and dynamic failure injection with cross-device graph cascades.

---

## 🏛️ Core Platform Capabilities

### 1. Splunk-Native Dark NOC Canvas (`#0B0F19`)
- High-density, utilitarian Network Operations Center (NOC) interface styled for seamless Splunk Enterprise Dark Mode integration.
- Deep Slate Charcoal background (`#0B0F19`) with dot-matrix alignment grid (`#1E293B`).
- Panels and sidebars (`#1F2937`) with precise borders (`#374151`).
- Semantic Alert Palette:
  - **Critical / Down / Severe**: Vivid Crimson (`#EF4444`)
  - **Warning / Degraded / High CPU**: Amber (`#F59E0B`)
  - **Healthy / Operational / Active**: Emerald Green (`#10B981`)
  - **Telemetry Stream Active**: Electric Blue / Violet (`#8B5CF6`)

### 2. Interactive Jupyter-like SPL Playground
- Run Search Processing Language (SPL) queries directly in the UI against live simulated streams.
- **Notebook-Style Interface**: Mix Markdown explanation cells with executable SPL query cells.
- **In-Memory SPL Execution Engine**: Evaluates SPL commands in real-time (`stats`, `where`, `eval`, `table`, `sort`, `head`, `timechart`).
- **Tri-Mode Results Inspection**:
  - **Tabular View**: Formatted dataset view with row numbers and column sorters.
  - **CIM Raw Event Inspector**: Event viewer highlighting extracted Splunk CIM fields (`action`, `signature`, `src`, `dest`, `vendor`, `sourcetype`).
  - **Automatic Chart Visualizer**: Renders interactive bar charts, distribution line charts, or pie charts based on query aggregations.

### 3. NOC & SOC Use Case Repository & Test Harness
- **10+ Prebuilt Production Use Cases**:
  1. **BGP Route Flap & Convergence Triage**: HoldTimer expiration and prefix dampening.
  2. **Perimeter DDoS SYN Flood & Firewall Capacity**: 50,000 pps volumetric flood and state-table exhaustion.
  3. **Optical Signal Loss (BER) & Transceiver Degradation**: -24.5 dBm attenuation and pre-FEC alarms.
  4. **Lateral Movement & Zero Trust Quarantine**: Cisco ISE 802.1X quarantine and Duo MFA lockout.
  5. **VoIP Quality Degradation & MOS E-Model Rating**: ITU-T G.107 Mean Opinion Score tracking.
  6. **DDI Exhaustion & DNS Tunneling Exfiltration**: High-entropy base64 query exfiltration and DHCP exhaustion.
  7. **SD-WAN Underlay Brownout & Dynamic Path Steering**: BFD SLA violations and broadband failover.
  8. **SSL/TLS Decryption & Shadow Rule Inefficiency**: Redundant shadow rule evaluation and uninspected traffic.
  9. **Data Center Microburst & PFC Pause Frame Drops**: Sub-millisecond buffer saturation and packet drops.
  10. **C2 Beaconing & Covert Tunneling Detection**: Periodic HTTP/S outbound beaconing detection.
- **One-Click Automated Verification**: Validates live simulation streams against expected assertions and minimum event counts.

### 4. Comprehensive 30-Vendor Splunkbase Directory
- Audited reference catalog across **30 enterprise vendors** spanning Routing & Switching, Next-Gen Firewalls, SASE/SSE, Load Balancers/ADCs, and Cloud Infrastructure.
- Maps official vendor documentation and Splunkbase Technology Add-ons (TAs) to target NetSpout sourcetypes and Splunk CIM data models without bundling bloated binary artifacts (< 5MB package size).

### 5. NOC & SOC Metric Emulation Matrix
- **Data Plane & Flow Efficiency**: ITU-T G.107 VoIP MOS rating (1.0 to 4.5), Goodput vs Throughput, TCP Retransmission %, RTT & Jitter, and BGP convergence time.
- **Physical & Optical Health**: Optical transceiver Rx/Tx power (dBm), ASIC & chassis thermal sensors (°C), MTBF hours, and configuration drift detection.
- **DDI Infrastructure**: DNS query latency & failure rates, DHCP pool exhaustion %, and NTP stratum/microsecond offset.
- **SOC Firewall State & NDR**: State table session utilization %, Deep Packet Inspection bypass %, shadow rule audit, micro-segmentation quarantines, and C2 beacon threat scoring.
- **3-Frequency Operational Blueprints**: Real-time Tactical (1s-5s fast polling), Weekly Trends (capacity forecasting), and Annual Strategic (NIST/CIS compliance).

### 6. OpenConfig YANG State Engine & Mock gNMI Telemetry
- RFC 7950 operational trees across `openconfig-interfaces`, `openconfig-bgp`, `openconfig-platform`, and `openconfig-system`.
- Dual subscription modes: `SAMPLE` (periodic metrics) and `ON_CHANGE` (event-driven pushes).

### 7. Dynamic Fault & Anomaly Injection Engine
- Graph cascades: cutting a fiber link automatically triggers interface LOS, drops BGP adjacencies (`ESTABLISHED -> IDLE`), and tears down OSPF neighbor states across adjacent nodes.

### 8. Splunk Modular Input & Multi-Pipeline Export
- Ships with Splunk Modular Input (`netspout_streamer.py`) reading streaming events into Splunk indexers via stdout XML streaming.
- Multi-pipeline dispatcher supporting Splunk HEC, Direct Syslog (UDP/TCP 514), OpenTelemetry Collector (OTLP/gRPC/HTTP), and Telegraf.

---

## 🌐 30-Vendor Splunkbase TA Directory

| Vendor | Category | Recommended Splunkbase Add-on | App ID | Target NetSpout Sourcetypes |
| :--- | :--- | :--- | :---: | :--- |
| **Cisco Systems (IOS-XE)** | Routing & Switching | [Splunk Add-on for Cisco IOS](https://splunkbase.splunk.com/app/1467) | `1467` | `cisco:ios:syslog`, `cisco:ios:mdt:metric` |
| **Cisco Catalyst Center** | Network Management | [Splunk Add-on for Cisco Catalyst Center](https://splunkbase.splunk.com/app/5580) | `5580` | `cisco:catalyst:devicehealth`, `cisco:catalyst:issue` |
| **Cisco SD-WAN (Viptela)** | SD-WAN | [Cisco SD-WAN Add-on for Splunk](https://splunkbase.splunk.com/app/7538) | `7538` | `cisco:sdwan:linkhealth`, `cisco:sdwan:alert` |
| **Cisco Identity Services (ISE)** | NAC & Identity | [Splunk Add-on for Cisco ISE](https://splunkbase.splunk.com/app/1924) | `1924` | `cisco:ise:syslog`, `cisco:ise:nac:8021x` |
| **Cisco Duo Security** | MFA & Zero Trust | [Splunk Add-on for Cisco Duo Security](https://splunkbase.splunk.com/app/3466) | `3466` | `cisco:duo:auth`, `cisco:duo:telephony` |
| **Cisco Nexus / ACI** | Data Center Fabric | [Cisco ACI Add-on for Splunk](https://splunkbase.splunk.com/app/1896) | `1896` | `cisco:aci:fault`, `cisco:aci:health` |
| **Cisco Meraki** | Cloud Managed WLAN/Switch | [Cisco Meraki Add-on for Splunk](https://splunkbase.splunk.com/app/6043) | `6043` | `meraki:accesspoints`, `meraki:traffic` |
| **Cisco Secure Firewall (FTD/ASA)** | Next-Gen Firewall | [Cisco Security Cloud Add-on](https://splunkbase.splunk.com/app/6259) | `6259` | `cisco:asa`, `cisco:sfw:estreamer` |
| **Juniper Networks (Junos)** | Routing & Switching | [Splunk Add-on for Juniper](https://splunkbase.splunk.com/app/2855) | `2855` | `juniper:junos:syslog`, `juniper:firewall` |
| **Arista Networks (EOS)** | Data Center & Cloud | [Arista Networks EOS Add-on](https://splunkbase.splunk.com/app/3350) | `3350` | `arista:eos:syslog`, `arista:metrics:telemetry` |
| **Dell Technologies (PowerSwitch)**| Data Center Switching | [Dell PowerSwitch Add-on for Splunk](https://splunkbase.splunk.com/app/4621) | `4621` | `dell:os10:syslog` |
| **Aruba Networks (HPE)** | Campus WLAN & Switching | [Aruba Networks Add-on for Splunk](https://splunkbase.splunk.com/app/4155) | `4155` | `aruba:mobility:syslog`, `aruba:clearpass` |
| **Extreme Networks** | Enterprise Fabric | [Extreme Networks Add-on for Splunk](https://splunkbase.splunk.com/app/4312) | `4312` | `extreme:exos:syslog` |
| **Huawei (CloudEngine)** | Enterprise Networking | [Huawei CloudEngine Add-on for Splunk](https://splunkbase.splunk.com/app/4820) | `4820` | `huawei:vrp:syslog` |
| **Nokia (SR OS)** | Service Provider Routing | [Nokia Service Router Add-on](https://splunkbase.splunk.com/app/5210) | `5210` | `nokia:sros:syslog` |
| **Palo Alto Networks (PAN-OS)** | Next-Gen Firewall | [Palo Alto Networks Add-on for Splunk](https://splunkbase.splunk.com/app/2757) | `2757` | `pan:traffic`, `pan:threat`, `pan:system` |
| **Fortinet (FortiGate)** | Next-Gen Firewall | [Fortinet FortiGate Add-on for Splunk](https://splunkbase.splunk.com/app/2800) | `2800` | `fortinet:fortigate:traffic`, `fortinet:utm` |
| **Check Point (Quantum)** | Enterprise Firewall | [Check Point Add-on for Splunk](https://splunkbase.splunk.com/app/4297) | `4297` | `checkpoint:firewall:log` |
| **SonicWall (SonicOS)** | Network Security | [SonicWall Add-on for Splunk](https://splunkbase.splunk.com/app/3982) | `3982` | `sonicwall:firewall` |
| **Sophos (XGS)** | Firewall & Threat Defense | [Sophos XG Firewall Add-on](https://splunkbase.splunk.com/app/4751) | `4751` | `sophos:xg:traffic` |
| **WatchGuard (Firebox)** | UTM Firewall | [WatchGuard Firebox Add-on](https://splunkbase.splunk.com/app/3620) | `3620` | `watchguard:firebox` |
| **Forcepoint (Next-Gen FW)** | Edge & Proxy Security | [Forcepoint NGFW Add-on](https://splunkbase.splunk.com/app/3914) | `3914` | `forcepoint:ngfw` |
| **A10 Networks (Thunder ADC)** | ADC & DDoS Protection | [A10 Networks Add-on for Splunk](https://splunkbase.splunk.com/app/3150) | `3150` | `a10:thunder:slb` |
| **Radware (DefensePro)** | DDoS Mitigation | [Radware DefensePro Add-on](https://splunkbase.splunk.com/app/3540) | `3540` | `radware:defensepro` |
| **F5 Networks (BIG-IP)** | Application Delivery (ADC) | [F5 BIG-IP Add-on for Splunk](https://splunkbase.splunk.com/app/2680) | `2680` | `f5:bigip:traffic`, `f5:bigip:syslog` |
| **Citrix (NetScaler ADC)** | Application Delivery (ADC) | [Citrix ADC Add-on for Splunk](https://splunkbase.splunk.com/app/3215) | `3215` | `citrix:netscaler:syslog` |
| **Cloudflare** | Edge Cloud & WAF | [Cloudflare Add-on for Splunk](https://splunkbase.splunk.com/app/4501) | `4501` | `cloudflare:http`, `cloudflare:waf` |
| **Zscaler (ZIA/ZPA)** | SASE / Cloud Security | [Zscaler Add-on for Splunk](https://splunkbase.splunk.com/app/4363) | `4363` | `zscaler:web`, `zscaler:zpa` |
| **Netskope** | SSE & CASB | [Netskope Add-on for Splunk](https://splunkbase.splunk.com/app/4224) | `4224` | `netskope:events`, `netskope:alerts` |
| **VMware NSX** | Software-Defined Networking | [VMware NSX-T Add-on for Splunk](https://splunkbase.splunk.com/app/5120) | `5120` | `vmware:nsx:firewall` |

---

## 🚀 Quickstart & Installation

### Option 1: Native Splunk App Deployment (Enterprise or Cloud)
1. Copy or extract `netspout` into `$SPLUNK_HOME/etc/apps/netspout`:
   ```bash
   tar -xzf netspout.spl -C $SPLUNK_HOME/etc/apps/
   ```
2. Restart Splunk:
   ```bash
   $SPLUNK_HOME/bin/splunk restart
   ```
3. Open Splunk Web and navigate to the **NetSpout** app:
   `http://localhost:8000/en-US/app/netspout/netspout_canvas`

### Option 2: Docker All-In-One Container
Run Splunk Enterprise 10.2 + NetSpout + 500GB Metric Tier + Fast Simulation companion in a single container:
```bash
docker run -d \
  --name splunk-netspout-standalone \
  -p 8000:8000 \
  -p 8088:8088 \
  -p 8089:8089 \
  -p 8081:8081 \
  -p 514:514/udp \
  -p 514:514/tcp \
  -e SPLUNK_START_ARGS="--accept-license" \
  -e SPLUNK_GENERAL_TERMS="--accept-sgt-current-at-splunk-com" \
  -e SPLUNK_PASSWORD="SplunkPassword123!" \
  netspout:standalone
```

Access endpoints:
- **Splunk Web & NetSpout Canvas**: `http://localhost:8000` (`admin` / `SplunkPassword123!`)
- **Interactive UI (Direct Port)**: `http://localhost:8081`
- **Splunk HEC Ingestion**: `https://localhost:8088/services/collector`

---

## 📊 Sample Production SPL Queries

### 1. BGP Convergence & Peer Adjacency Flaps
```spl
index=idx_network_ops (sourcetype="cisco:ios:syslog" OR sourcetype="juniper:junos:syslog" OR sourcetype="arista:eos:syslog") ("%BGP-5-ADJCHANGE" OR "HoldTimer" OR "DAMP")
| stats count, latest(signature) as last_event by host, peer
| where count > 0
```

### 2. Next-Gen Firewall Dropped Traffic by Application & Vendor
```spl
(sourcetype="pan:traffic" OR sourcetype="fortinet:fortigate:traffic" OR sourcetype="cisco:asa") action="dropped"
| stats count by vendor, app, dest_port
| sort -count
| head 10
```

### 3. OpenConfig Real-Time High-Capacity Octets & Bitrate
```spl
| mstats rate(interface.octets.in) AS rx_bps, rate(interface.octets.out) AS tx_bps
  WHERE index=cisco_mdt_metrics span=10s BY host, interface
```

---

## 👨‍💻 Creator & Maintainer

- **Architect & Author**: Mahamudul Chowdhury ([mchowdhury@splunk.com](mailto:mchowdhury@splunk.com))
- **GitHub Repository**: [https://github.com/machowdhury/NetSpout](https://github.com/machowdhury/NetSpout)
- **License**: Apache-2.0
