# NetSpout Gate 13 — OpenConfig & Multi-Vendor Rich Telemetry Model

**Author:** Mahamudul Chowdhury (`machowdhury@yahoo.com`)  
**Gate:** 13 (OpenConfig & Multi-Vendor Rich Telemetry Modeling)  
**Date:** 2026-09-29  
**Status:** SPECIFICATION COMPLETE (Zero Runtime Implementation in Gate 13)

---

## 1. Purpose & Evidence Classification Discipline

This document defines NetSpout's multi-vendor YANG / gNMI telemetry model across **Cisco IOS XR**, **Cisco IOS XE**, **Arista EOS**, and **Juniper Junos (and Junos OS Evolved)**. It establishes:
1. OpenConfig as the common cross-vendor denominator where supported, without making OpenConfig an artificial ceiling.
2. Coexistence of **`OPENCONFIG`** and **`VENDOR_NATIVE`** (`CISCO_NATIVE`, `EOS_NATIVE`, `JUNOS_NATIVE`) sensor paths.
3. The **Required 18-Row Vendor Support Matrix** (Section 2) and **14-Domain Telemetry Matrix** (Section 3).
4. Reusable **Device Profiles**, **Subscription Profiles**, and **Scenario Telemetry Profiles** (Sections 5–7).
5. Concrete **Same Incident $\rightarrow$ Different Vendor Telemetry** projections (Section 8).

### Evidence & Support Classifications
- **Evidence Basis:**
  - `DOCUMENTED`: Explicitly documented in official vendor documentation (`xrdocs.io`, Arista EOS / `goarista` docs, Juniper OpenConfig / JTI guides, or OpenConfig public YANG repository).
  - `VERIFIED`: Confirmed against official YANG modules / `gnmi.proto` specifications.
  - `INFERRED`: Architectural deduction from vendor OS family behavior; explicitly flagged and never represented as vendor documentation.
  - `MODELED`: NetSpout simulation projection used to drive deterministic scenario telemetry.
- **Path Support Classifications:**
  - `CROSS_VENDOR_VERIFIED`: OpenConfig path supported across Cisco, Arista, and Juniper.
  - `VENDOR_VERIFIED`: Vendor-native path or vendor-specific OpenConfig subtree verified in official vendor documentation.
  - `MODELED_MAPPING`: Normalized NetSpout mapping used when vendor hardware/OS versions vary.
  - `UNSUPPORTED` / `NOT_CONFIRMED`: Not supported on that platform or unconfirmed in public documentation.

---

## 2. Authoritative Vendor Research & Required 18-Dimension Matrix (Sections 29–31 & 52)

### 2.1 Authoritative Vendor Research Summary

#### A. Cisco (`CISCO_IOS_XR` & `CISCO_IOS_XE`)
- **Primary Reference (`DOCUMENTED`):** `https://xrdocs.io/telemetry` & Cisco YANG GitHub (`github.com/YangModels/yang/tree/main/vendor/cisco`).
- **Architectural Distinction (`IOS XR` vs `IOS XE`):**
  - **Cisco IOS XR** (Cisco 8000, NCS 5500, ASR 9000) uses the `Cisco-IOS-XR-*-oper` YANG namespace family (e.g., `Cisco-IOS-XR-infra-statsd-oper`, `Cisco-IOS-XR-pfi-im-cmd-oper`, `Cisco-IOS-XR-ipv4-bgp-oper`, `Cisco-IOS-XR-controller-optics-oper`, `Cisco-IOS-XR-wdsysmon-fd-oper`, `Cisco-IOS-XR-nto-misc-oper`, `Cisco-IOS-XR-qos-ma-oper`, `Cisco-IOS-XR-mpls-te-oper`, `Cisco-IOS-XR-segment-routing-ms-oper`, `Cisco-IOS-XR-plat-chas-invmgr-oper`) alongside OpenConfig models (`openconfig-interfaces`, `openconfig-bgp`, `openconfig-platform`, `openconfig-system`, `openconfig-mpls`, `openconfig-aft`).
  - **Cisco IOS XE** (Catalyst 9300/9500/9600, Catalyst 9800 WLC, ASR 1000 / Catalyst 8000) uses a **completely distinct** native YANG namespace family: `Cisco-IOS-XE-*-oper` (e.g., `Cisco-IOS-XE-interfaces-oper`, `Cisco-IOS-XE-bgp-oper`, `Cisco-IOS-XE-process-cpu-oper`, `Cisco-IOS-XE-memory-oper`, `Cisco-IOS-XE-platform-software-oper`, `Cisco-IOS-XE-environment-oper`, `Cisco-IOS-XE-wireless-client-oper`) alongside OpenConfig models.
  - **Rule:** NetSpout MUST NEVER emit `Cisco-IOS-XR-*-oper` paths from an `IOS XE` (`Catalyst`) node or vice versa.

#### B. Arista (`ARISTA_EOS`)
- **Primary Reference (`DOCUMENTED`):** `https://github.com/aristanetworks/goarista` (Apache-2.0 License) & Arista EOS OCTA (OpenConfig + TerminAttr) documentation.
- **License & Usage Rule:** `goarista` is used strictly as **architectural reference material** for Arista gNMI path conventions, `eos_native` origin semantics, and OpenConfig client behavior. Zero `goarista` code is copied into NetSpout.
- **Architectural Specifics:**
  - Arista EOS exposes gNMI via the `OpenConfig` / `TerminAttr` agent (default TCP port `6030`).
  - Standard OpenConfig paths use `origin = "openconfig"` (or empty default origin).
  - EOS native state (`Sysdb`, `Smash`, and `LANZ` microburst/queue-latency tables) is exposed via gNMI when `origin = "eos_native"` (e.g., `/Sysdb/interface/counter/eth/...`, `/Smash/routing/bgp/...`, `/Sysdb/lanz/status/...`), as well as Arista OpenConfig augmentations (`arista-exp-eos-*`).

#### C. Juniper (`JUNIPER_JUNOS`)
- **Primary Reference (`DOCUMENTED`):** `https://www.juniper.net/documentation/us/en/software/junos/open-config/index.html` (OpenConfig User Guide & Junos Telemetry Interface / JTI).
- **Architectural Specifics:**
  - Junos OS and Junos OS Evolved (MX, PTX, QFX, ACX series) expose gNMI via the `network-agent` (`na-grpcd`) package (commonly TCP port `32767` or `50051`).
  - Supports both **OpenConfig YANG paths** (`/interfaces/interface/...`, `/network-instances/network-instance/...`, `/components/component/...`, `/ system/...`, `/lldp/...`) and **Junos Native JTI sensor paths** rooted under `/junos/...` (e.g., `/junos/system/linecard/interface/traffic/`, `/junos/system/linecard/interface/queue/`, `/junos/system/linecard/optics/`, `/junos/system/linecard/npu/memory/`, `/junos/services/label-switched-path/usage/`).
  - Hardware/Linecard dependence: PFE/linecard sensors (`/junos/system/linecard/...`) stream directly from Packet Forwarding Engine (PFE) sensors on MX/PTX/QFX platforms, whereas Routing Engine (RE) sensors stream control-plane state (`BGP`, `RPD`, `chassisd`).

### 2.2 Required 18-Dimension Multi-Vendor Capability Matrix (Section 52)

| Capability / Dimension | Cisco IOS XR (`CISCO_IOS_XR`) | Cisco IOS XE (`CISCO_IOS_XE`) | Arista EOS (`ARISTA_EOS`) | Juniper Junos (`JUNIPER_JUNOS`) | Evidence Basis |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1. OpenConfig Support** | `BOTH` (`openconfig-*` + XR native) | `BOTH` (`openconfig-*` + XE native) | `BOTH` (`openconfig-*` primary + `arista-exp-eos-*`) | `BOTH` (`openconfig-*` via JTI + `/junos/...`) | `DOCUMENTED` |
| **2. Native Model Support** | `VENDOR_NATIVE` (`Cisco-IOS-XR-*-oper`) | `VENDOR_NATIVE` (`Cisco-IOS-XE-*-oper`) | `VENDOR_NATIVE` (`origin="eos_native"`: `Sysdb`, `Smash`, `LANZ`) | `VENDOR_NATIVE` (`/junos/system/linecard/...`, `junos-*` YANG) | `DOCUMENTED` |
| **3. Interfaces & Counters** | `BOTH` (`openconfig-interfaces` + `Cisco-IOS-XR-infra-statsd-oper`, `Cisco-IOS-XR-pfi-im-cmd-oper`) | `BOTH` (`openconfig-interfaces` + `Cisco-IOS-XE-interfaces-oper`) | `BOTH` (`openconfig-interfaces` + `eos_native:/Sysdb/interface/counter/eth/...`) | `BOTH` (`openconfig-interfaces` + `/junos/system/linecard/interface/traffic/`) | `DOCUMENTED` |
| **4. BGP** | `BOTH` (`openconfig-bgp` / `network-instance` + `Cisco-IOS-XR-ipv4-bgp-oper`) | `BOTH` (`openconfig-bgp` + `Cisco-IOS-XE-bgp-oper`) | `BOTH` (`openconfig-bgp` + `eos_native:/Smash/routing/bgp/status/...`) | `BOTH` (`openconfig-bgp` + `junos-routing` / `/network-instances/.../bgp`) | `DOCUMENTED` |
| **5. MPLS** | `BOTH` (`openconfig-mpls` + `Cisco-IOS-XR-mpls-te-oper`, `Cisco-IOS-XR-mpls-lsd-oper`) | `VENDOR_NATIVE` / `MODELED_ONLY` (LDP/TE on WAN XE; limited OC MPLS on campus switches) | `BOTH` (`openconfig-mpls` + EOS MPLS/LDP tables on 7280R/7500R) | `BOTH` (`openconfig-mpls` `/mpls/lsps/...` + `/junos/services/label-switched-path/usage/`) | `DOCUMENTED` |
| **6. SR / SRv6** | `BOTH` (`openconfig-segment-routing` + `Cisco-IOS-XR-segment-routing-ms-oper`, `Cisco-IOS-XR-segment-routing-srv6-oper`) | `MODELED_ONLY` (SR-MPLS on ASR1K/C8000; SRv6 primarily IOS XR) | `BOTH` (`openconfig-segment-routing` + EOS ISIS/BGP SR counters on R-series) | `BOTH` (`openconfig-segment-routing` + `/junos/services/segment-routing/...`) | `DOCUMENTED` |
| **7. Optics / Transceiver** | `BOTH` (`openconfig-platform-transceiver` / `terminal-device` + `Cisco-IOS-XR-controller-optics-oper`) | `BOTH` (`openconfig-platform-transceiver` + `Cisco-IOS-XE-transceiver-oper`) | `BOTH` (`openconfig-platform-transceiver` + `eos_native:/Sysdb/hardware/archer/xcvr/...`) | `BOTH` (`openconfig-platform-transceiver` / `terminal-device` + `/junos/system/linecard/optics/`) | `DOCUMENTED` |
| **8. Queue / QoS** | `BOTH` (`openconfig-qos` + `Cisco-IOS-XR-qos-ma-oper`, `Cisco-IOS-XR-fretta-bcm-dpa-drop-stats-oper`) | `BOTH` (`openconfig-qos` + `Cisco-IOS-XE-interfaces-oper` `qos-queue-stats`) | `BOTH` (`openconfig-qos` + `eos_native:/Sysdb/lanz/...` & QoS queue counters) | `BOTH` (`openconfig-qos` + `/junos/system/linecard/interface/queue/`) | `DOCUMENTED` |
| **9. CPU** | `BOTH` (`openconfig-system:system/cpus` + `Cisco-IOS-XR-wdsysmon-fd-oper`) | `BOTH` (`openconfig-system:system/cpus` + `Cisco-IOS-XE-process-cpu-oper`) | `BOTH` (`openconfig-system:system/cpus` + `openconfig-platform` CPU component) | `BOTH` (`openconfig-system:system/cpus` + `/components/component[type=CPU]` / RE CPU) | `DOCUMENTED` |
| **10. Memory** | `BOTH` (`openconfig-system:system/memory` + `Cisco-IOS-XR-nto-misc-oper`) | `BOTH` (`openconfig-system:system/memory` + `Cisco-IOS-XE-memory-oper`, `platform-software-oper`) | `BOTH` (`openconfig-system:system/memory` + `openconfig-platform` memory state) | `BOTH` (`openconfig-system:system/memory` + `/junos/system/linecard/npu/memory/`) | `DOCUMENTED` |
| **11. Platform Inventory** | `BOTH` (`openconfig-platform` + `Cisco-IOS-XR-plat-chas-invmgr-oper`, `invmgr-oper`) | `BOTH` (`openconfig-platform` + `Cisco-IOS-XE-platform-oper`) | `BOTH` (`openconfig-platform` `/components/component` + `eos_native` entity state) | `BOTH` (`openconfig-platform` `/components/component` + `/junos/chassis/...`) | `DOCUMENTED` |
| **12. FIB / AFT** | `BOTH` (`openconfig-aft` `/network-instances/.../afts` + `Cisco-IOS-XR-fib-common-oper`) | `MODELED_ONLY` (`Cisco-IOS-XE-cef-oper` native; `openconfig-aft` platform-dependent) | `BOTH` (`openconfig-aft` ipv4/ipv6/mpls + `eos_native:/Smash/forwarding/...`) | `BOTH` (`openconfig-aft` `/network-instances/.../afts` + `/junos/system/linecard/forwarding/`) | `DOCUMENTED` |
| **13. LLDP** | `BOTH` (`openconfig-lldp` + `Cisco-IOS-XR-ethernet-lldp-oper`) | `BOTH` (`openconfig-lldp` + `Cisco-IOS-XE-lldp-oper`) | `BOTH` (`openconfig-lldp` `/lldp/interfaces/interface/neighbors`) | `BOTH` (`openconfig-lldp` `/lldp/interfaces/interface/neighbors`) | `DOCUMENTED` |
| **14. VLAN / FDB (L2)** | `VENDOR_NATIVE` / `OPENCONFIG` (`Cisco-IOS-XR-l2vpn-oper` for bridge-domains/EVPN) | `BOTH` (`openconfig-vlan` + `Cisco-IOS-XE-vlan-oper`, `matm-oper`) | `BOTH` (`openconfig-vlan`, `openconfig-network-instance` fdb/mac-table) | `BOTH` (`openconfig-vlan`, `/network-instances/.../fdb/mac-table`) | `DOCUMENTED` |
| **15. Environmental** | `BOTH` (`openconfig-platform` temp/fan/psu + `Cisco-IOS-XR-envmon-oper`) | `BOTH` (`openconfig-platform` + `Cisco-IOS-XE-environment-oper`) | `BOTH` (`openconfig-platform` temp/fan/power-supply state) | `BOTH` (`openconfig-platform` `/components/component` temp/fan/psu + `/junos/system/linecard/environment/`) | `DOCUMENTED` |
| **16. Subscription Modes** | `ONCE`, `POLL`, `STREAM` (`SAMPLE`, `ON_CHANGE`, `TARGET_DEFINED`, heartbeat) | `ONCE`, `POLL`, `STREAM` (`SAMPLE`, `ON_CHANGE`) | `ONCE`, `POLL`, `STREAM` (`SAMPLE`, `ON_CHANGE`, `TARGET_DEFINED`, `suppress_redundant`, heartbeat) | `ONCE`, `POLL`, `STREAM` (`SAMPLE`, `ON_CHANGE`, `heartbeat_interval`, `suppress_redundant`) | `DOCUMENTED` |
| **17. Encodings** | `PROTO`, `JSON_IETF`, `JSON`, `ASCII` | `PROTO`, `JSON_IETF` | `PROTO`, `JSON`, `JSON_IETF`, `ASCII`, `BYTES` | `PROTO`, `JSON_IETF`, `JSON` | `DOCUMENTED` |
| **18. Auth / TLS** | TLS 1.2/1.3, mTLS, gRPC metadata `username`/`password` | TLS 1.2/1.3, mTLS, metadata `username`/`password` | TLS, mTLS, metadata `username`/`password` or token (`management api gnmi`) | TLS, mTLS (`jet-authentication`), metadata `username`/`password` | `DOCUMENTED` |

---

## 3. Comprehensive 14-Domain Vendor Support Matrix (Section 28)

| Domain | Cisco IOS XR | Cisco IOS XE | Arista EOS | Juniper Junos | Primary OpenConfig Module |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1. Interfaces (State/Admin/Speed/MTU)** | `BOTH` | `BOTH` | `BOTH` | `BOTH` | `openconfig-interfaces` |
| **2. Interface Counters / Errors / Discards** | `BOTH` | `BOTH` | `BOTH` | `BOTH` | `openconfig-interfaces` |
| **3. BGP (Session / Prefixes / Routes)** | `BOTH` | `BOTH` | `BOTH` | `BOTH` | `openconfig-bgp` / `openconfig-network-instance` |
| **4. CPU Utilization** | `BOTH` | `BOTH` | `BOTH` | `BOTH` | `openconfig-system` / `openconfig-platform` |
| **5. Memory Utilization** | `BOTH` | `BOTH` | `BOTH` | `BOTH` | `openconfig-system` / `openconfig-platform` |
| **6. Platform Inventory (Chassis/LC/PSU/Fan)** | `BOTH` | `BOTH` | `BOTH` | `BOTH` | `openconfig-platform` |
| **7. Optics (Rx/Tx dBm, Bias, BER, OSNR)** | `BOTH` | `BOTH` | `BOTH` | `BOTH` | `openconfig-platform-transceiver` / `openconfig-terminal-device` |
| **8. Queues / QoS / Congestion / PFC / ECN** | `BOTH` | `BOTH` | `BOTH` | `BOTH` | `openconfig-qos` |
| **9. MPLS (LSP State / Labels / Traffic)** | `BOTH` | `MODELED_ONLY` | `BOTH` | `BOTH` | `openconfig-mpls` |
| **10. Segment Routing (SR-MPLS / SRv6 / TI-LFA)** | `BOTH` | `MODELED_ONLY` | `BOTH` | `BOTH` | `openconfig-segment-routing` / `openconfig-srv6` |
| **11. FIB / AFT (Next-Hop / Route Programming)** | `BOTH` | `VENDOR_NATIVE` | `BOTH` | `BOTH` | `openconfig-aft` |
| **12. LLDP (Neighbor Discovery)** | `BOTH` | `BOTH` | `BOTH` | `BOTH` | `openconfig-lldp` |
| **13. VLAN / FDB (MAC Table / Trunk State)** | `VENDOR_NATIVE` | `BOTH` | `BOTH` | `BOTH` | `openconfig-vlan` / `openconfig-network-instance` |
| **14. Environmental (Temp / Voltage / Power)** | `BOTH` | `BOTH` | `BOTH` | `BOTH` | `openconfig-platform` |

---

## 4. Evaluation of the 13 Required OpenConfig Modules (Section 5)

| OpenConfig Module | Canonical Root Path | Support Classification | Multi-Vendor Assessment |
| :--- | :--- | :--- | :--- |
| **`openconfig-interfaces`** | `/interfaces/interface[name=*]/state` | `CROSS_VENDOR_VERIFIED` | Universal foundation across Cisco XR/XE, Arista EOS, and Juniper Junos. |
| **`openconfig-if-ip`** | `/interfaces/interface[name=*]/subinterfaces/subinterface[index=*]/ipv4/addresses` | `CROSS_VENDOR_VERIFIED` | Supported across all four platforms for interface IPv4/IPv6 state. |
| **`openconfig-platform`** | `/components/component[name=*]/state` | `CROSS_VENDOR_VERIFIED` | Supported across all four platforms for chassis, linecard, CPU, fan, PSU, and temperature state. |
| **`openconfig-platform-transceiver`** | `/components/component[name=*]/transceiver/state` | `CROSS_VENDOR_VERIFIED` | Standard optical transceiver laser power (`output-power`, `input-power`), bias current, voltage, and temperature. |
| **`openconfig-terminal-device`** | `/terminal-device/logical-channels/channel[index=*]/otn/state` | `VENDOR_VERIFIED` | Supported on coherent DWDM platforms (Cisco XR 8000/NCS, Juniper PTX/MX, Arista 7280R coherent optics) for `pre-fec-ber`, `q-value`, `osnr`, `chromatic-dispersion`. |
| **`openconfig-system`** | `/system/state`, `/system/cpus/cpu[index=*]/state`, `/system/memory/state` | `CROSS_VENDOR_VERIFIED` | Supported across Cisco, Arista, and Juniper for hostname, boot-time, CPU, and memory. |
| **`openconfig-network-instance`** | `/network-instances/network-instance[name=*]` | `CROSS_VENDOR_VERIFIED` | Container for VRFs, protocols (`BGP`, `ISIS`, `OSPF`), MPLS, AFTs, and L2 FDB tables. |
| **`openconfig-bgp`** | `/network-instances/network-instance[name=*]/protocols/protocol[identifier=BGP][name=*]/bgp` | `CROSS_VENDOR_VERIFIED` | Universal BGP neighbor `session-state` and `afi-safis/afi-safi/state/prefixes` (`received`, `installed`, `sent`). |
| **`openconfig-mpls`** | `/network-instances/network-instance[name=*]/mpls/lsps/constrained-path/tunnels/tunnel[name=*]/state` | `VENDOR_VERIFIED` | Supported on Cisco IOS XR, Juniper Junos, and Arista R-series; `MODELED_MAPPING` on campus switches. |
| **`openconfig-aft`** | `/network-instances/network-instance[name=*]/afts/ipv4-unicast/ipv4-entry[prefix=*]/state` | `VENDOR_VERIFIED` | Supported on Juniper PTX/MX, Arista EOS, and Cisco IOS XR for forwarding next-hop verification. |
| **`openconfig-lldp`** | `/lldp/interfaces/interface[name=*]/neighbors/neighbor[id=*]/state` | `CROSS_VENDOR_VERIFIED` | Supported across Cisco, Arista, and Juniper for topology adjacency verification. |
| **`openconfig-vlan`** | `/vlans/vlan[vlan-id=*]/state` | `VENDOR_VERIFIED` | Supported on Cisco IOS XE (Catalyst), Arista EOS, and Juniper Junos switches. |
| **`openconfig-telemetry`** | `/telemetry-system/subscriptions/persistent-subscriptions` | `VENDOR_VERIFIED` | Describes telemetry subscription state itself. |

---

## 5. Reusable Device Profiles (Section 17)

NetSpout defines four canonical `DeviceTelemetryProfile` definitions. Device profiles declare **capabilities, encodings, interface naming conventions, and path bindings**—they NEVER contain scenario-specific fault logic:

| Profile ID | Target OS / Hardware Family | Default Native gNMI Port (Real World) | Supported Encodings | Interface Naming Convention | Supported `gnmi.Path.origin` Values | Default `CapabilitiesResponse.gNMI_version` |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`CISCO_IOS_XR`** | Cisco IOS XR (8000, NCS 5500, ASR 9000) | `57400` | `PROTO`, `JSON_IETF`, `JSON` | `HundredGigE0/0/0/0`, `TenGigE0/0/0/1`, `Bundle-Ether1` | `"openconfig"`, `"Cisco-IOS-XR-*"` | `"0.7.0"` |
| **`CISCO_IOS_XE`** | Cisco IOS XE (Catalyst 9300/9500/9600/9800, C8300) | `57400` / `9339` | `PROTO`, `JSON_IETF` | `FortyGigE1/0/1`, `TenGigabitEthernet1/1/1`, `GigabitEthernet1/0/12` | `"openconfig"`, `"Cisco-IOS-XE-*"` | `"0.7.0"` |
| **`ARISTA_EOS`** | Arista EOS (7280R3, 7050X3, 7500R3) | `6030` | `PROTO`, `JSON`, `JSON_IETF` | `Ethernet1/1`, `Ethernet49/1`, `Port-Channel1` | `"openconfig"`, `"eos_native"` | `"0.8.0"` |
| **`JUNIPER_JUNOS`** | Juniper Junos OS / Evolved (PTX10000, MX960, QFX5120) | `32767` / `50051` | `PROTO`, `JSON_IETF`, `JSON` | `et-0/0/0`, `ge-0/0/0`, `xe-0/0/1`, `ae0` | `"openconfig"`, `"junos"` | `"0.7.0"` |

---

## 6. Reusable Subscription Profiles (Section 32)

Subscription profiles select **canonical signal IDs**, subscription modes (`SAMPLE` vs `ON_CHANGE`), and cadences. The target device's `DeviceTelemetryProfile` resolves those canonical signals to either `OPENCONFIG` or `VENDOR_NATIVE` paths at runtime:

| Subscription Profile ID | Canonical Signals Included | Subscription Mode & Cadence | Primary Operational Use Case |
| :--- | :--- | :--- | :--- |
| **`INTERFACE_HEALTH`** | `interface.admin_status`, `interface.oper_status`, `interface.carrier_transitions` (`ON_CHANGE`); `interface.in_octets`, `interface.out_octets`, `interface.in_unicast_pkts`, `interface.out_unicast_pkts`, `interface.in_errors`, `interface.out_errors`, `interface.in_discards`, `interface.out_discards`, `interface.utilization_pct` (`SAMPLE` `5s`) | `ON_CHANGE` + `SAMPLE (5s)` | Link flap detection, bandwidth saturation, CRC/FCS error troubleshooting |
| **`BGP_ASSURANCE`** | `bgp.session_state`, `bgp.last_established` (`ON_CHANGE`); `bgp.prefixes_received`, `bgp.prefixes_installed`, `bgp.prefixes_advertised`, `bgp.input_queue_messages` (`SAMPLE` `10s`) | `ON_CHANGE` + `SAMPLE (10s)` | BGP peering assurance, route leak/withdrawal detection, failover validation |
| **`QUEUE_CONGESTION`** | `queue.depth_bytes`, `queue.max_depth_bytes`, `queue.transmit_pkts`, `queue.transmit_octets`, `queue.dropped_pkts`, `queue.dropped_octets`, `qos.buffer_utilization_pct`, `qos.ecn_marked_pkts`, `qos.pfc_pause_frames` (`SAMPLE` `1s`) | `SAMPLE (1s)` | Data center incast microburst, VOQ/buffer exhaustion, QoS tail-drop analysis |
| **`OPTICS_HEALTH`** | `optics.los_alarm` (`ON_CHANGE`); `optics.rx_power_dbm`, `optics.tx_power_dbm`, `optics.laser_bias_ma`, `optics.temperature_celsius`, `optics.supply_voltage_volts`, `optics.pre_fec_ber`, `optics.q_factor_db`, `optics.osnr_db`, `optics.chromatic_dispersion_ps_nm` (`SAMPLE` `5s`) | `ON_CHANGE` + `SAMPLE (5s)` | Coherent DWDM degradation, fiber attenuation, transceiver aging & FEC threshold alerts |
| **`SYSTEM_HEALTH`** | `system.cpu_utilization_pct`, `system.memory_utilization_pct`, `system.uptime_sec`, `platform.temperature_celsius`, `platform.fan_speed_rpm`, `platform.psu_oper_status`, `platform.alarm_state` (`SAMPLE` `10s` + `ON_CHANGE` on alarms) | `SAMPLE (10s)` + `ON_CHANGE` | Control-plane CPU/memory exhaustion, thermal alarms, PSU/fan hardware faults |
| **`MPLS_SR_HEALTH`** | `mpls.lsp_oper_state`, `sr.ti_lfa_active`, `sr.active_path_ candidate` (`ON_CHANGE`); `mpls.lsp_octets`, `mpls.lsp_packets`, `sr.sid_traffic_octets` (`SAMPLE` `5s`) | `ON_CHANGE` + `SAMPLE (5s)` | MPLS TE / SR-TE / SRv6 path switchover, TI-LFA fast reroute verification |
| **`FIB_ASSURANCE`** | `aft.ipv4_prefix_next_hop`, `aft.nh_group_programmed`, `lldp.neighbor_state` (`ON_CHANGE` + `SAMPLE` `15s`) | `ON_CHANGE` + `SAMPLE (15s)` | Control-plane vs forwarding-plane (RIB-to-FIB) consistency & blackhole detection |

---

## 7. Scenario Telemetry Profiles — Auditing Existing Catalog Scenarios (Sections 9 & 33)

Without adding any new scenarios, Gate 13 maps existing catalog scenarios to reusable Subscription Profile bundles:

| Existing Canonical Scenario ID | Topology ID & Nodes | Selected Subscription Profiles | Phase-Driven Telemetry Trajectory (`BASELINE -> DEGRADE -> FAILOVER -> RECOVERY`) |
| :--- | :--- | :--- | :--- |
| **`openconfig_mdt_streaming`** *(GOLDEN_PATH_CERTIFIED — Primary Gate 13B Candidate)* | `openconfig_core`: `node-cisco8k` (`CISCO_IOS_XR`), `node-juniper-ptx` (`JUNIPER_JUNOS`), `node-arista-spine` (`ARISTA_EOS`), `node-cat-leaf` (`CISCO_IOS_XE`) | `INTERFACE_HEALTH` + `BGP_ASSURANCE` + `SYSTEM_HEALTH` + `QUEUE_CONGESTION` | **BASELINE:** All 4 vendor nodes report `oper-status=UP`, `session-state=ESTABLISHED` (`1420` prefixes), CPU `18.5%`, drops `0`. **DEGRADE:** Inter-router link `HundredGigE0/0/0/0 <-> et-0/0/0` experiences congestion (`utilization=96.4%`, queue drops rising) and CPU spike (`94%`). **FAILOVER:** Link drops to `DOWN`, BGP session transitions `ESTABLISHED -> IDLE`, backup path carries traffic. **RECOVERY:** Link & BGP restore to `UP` / `ESTABLISHED`. |
| **`service_provider_cisco`** *(GOLDEN_PATH_CERTIFIED)* | `service_provider_cisco`: `cisco-asr9k-pe1`, `node-cisco8k-core02`, `node-ncs5500-spine01/02`, `node-asr9k-pe01/02` (`CISCO_IOS_XR`) | `BGP_ASSURANCE` + `INTERFACE_HEALTH` + `MPLS_SR_HEALTH` + `FIB_ASSURANCE` | Coherent with Gate 12F Native SNMPv2c: `HundredGigE0/0/0/1` degrades (`in-errors` rise), fails over via SRv6 / TI-LFA backup spine (`node-ncs5500-spine02`), and recovers. |
| **`cisco_aci_microburst`** *(GOLDEN_PATH_CERTIFIED)* | `cisco_aci`: `node-leaf-nexus` (`Nexus-9336-Leaf01`), `node-spine1/2` (`Nexus-9508`), `node-leaf-dst` | `QUEUE_CONGESTION` + `INTERFACE_HEALTH` + `SYSTEM_HEALTH` | **DEGRADE:** `Eth1/24` and uplink `Eth1/49` exhibit sub-second buffer spike (`buffer_utilization_pct = 98.2%`, `queue.depth_bytes = 18,450,000`, `queue.dropped_pkts` and `qos.ecn_marked_pkts` surge). |
| **`mixed_backbone_optical`** *(GOLDEN_PATH_CERTIFIED)* | `mixed_optical`: `node-nokia-core`, `node-juniper-pe` (`Juniper-MX960-PE01`), `node-arista-leaf` (`Arista-7280R-Leaf01`) | `OPTICS_HEALTH` + `INTERFACE_HEALTH` + `MPLS_SR_HEALTH` | **DEGRADE:** Optical laser power degrades (`rx_power_dbm` drops from `-6.2 dBm` to `-24.8 dBm`, `pre_fec_ber` degrades from `1.0e-9` to `1.4e-3`, `osnr_db` drops from `28.5 dB` to `11.2 dB`), triggering MPLS FRR bypass before optical restoration. |
| **`service_provider_mixed`** | `service_provider_mixed`: Cisco 8000 (`CISCO_IOS_XR`), Juniper PTX (`JUNIPER_JUNOS`), Nokia 7750 | `BGP_ASSURANCE` + `INTERFACE_HEALTH` + `MPLS_SR_HEALTH` + `OPTICS_HEALTH` | Multi-vendor core transit link degradation and BGP/MPLS path convergence across Cisco XR and Juniper PTX. |
| **`mixed_vendor_enterprise`** *(GOLDEN_PATH_CERTIFIED)* | `mixed_vendor_enterprise`: Cisco Catalyst (`CISCO_IOS_XE`), Arista (`ARISTA_EOS`), Juniper (`JUNIPER_JUNOS`) | `INTERFACE_HEALTH` + `SYSTEM_HEALTH` + `BGP_ASSURANCE` | Enterprise campus-to-DC fabric health and cross-vendor interface/CPU/BGP correlation. |

---

## 8. Same Incident — Different Vendor Telemetry Projection (Section 10)

Central to NetSpout's multi-vendor value proposition is proving that **one canonical operational incident** emits authentic vendor-specific paths across Cisco, Arista, and Juniper while normalizing to identical canonical semantics in Splunk.

### Concrete Example: Interface Congestion & Queue Tail-Drop on Uplink (`DEGRADE` Phase)

#### 1. Canonical Scenario State (`ScenarioPhaseState`)
```text
scenario_id              = "openconfig_mdt_streaming"
phase                    = "DEGRADE"
interface.utilization    = 96.4 %
queue.id                 = "0" (best-effort / default queue)
queue.depth_bytes        = 14850000
queue.dropped_pkts       = 4820
interface.oper_status    = "UP"
```

#### 2. Cisco IOS XR Projection (`node-cisco8k`, `HundredGigE0/0/0/0`)
- **OpenConfig Path (`origin="openconfig"`):**
  - `/qos/interfaces/interface[interface-id=HundredGigE0/0/0/0]/output/queues/queue[name=0]/state/max-queue-len` $\rightarrow$ `uint_val: 14850000`
  - `/qos/interfaces/interface[interface-id=HundredGigE0/0/0/0]/output/queues/queue[name=0]/state/dropped-pkts` $\rightarrow$ `uint_val: 4820`
- **Cisco IOS XR Native Path (`origin="Cisco-IOS-XR-qos-ma-oper"`):**
  - `/qos/interface-table/interface[interface-name=HundredGigE0/0/0/0]/output/service-policy-names/service-policy-instance/statistics/class-stats[class-name=class-default]/general-stats/tail-drop-packets` $\rightarrow$ `uint_val: 4820`
  - `/qos/interface-table/interface[interface-name=HundredGigE0/0/0/0]/output/service-policy-names/service-policy-instance/statistics/class-stats[class-name=class-default]/general-stats/queue-current-size-bytes` $\rightarrow$ `uint_val: 14850000`

#### 3. Arista EOS Projection (`node-arista-spine`, `Ethernet1/1`)
- **OpenConfig Path (`origin="openconfig"`):**
  - `/qos/interfaces/interface[interface-id=Ethernet1/1]/output/queues/queue[name=0]/state/max-queue-len` $\rightarrow$ `uint_val: 14850000`
  - `/qos/interfaces/interface[interface-id=Ethernet1/1]/output/queues/queue[name=0]/state/dropped-pkts` $\rightarrow$ `uint_val: 4820`
- **Arista EOS Native / LANZ Path (`origin="eos_native"`):**
  - `/Sysdb/lanz/status/intfStatus[intfName=Ethernet1/1]/queueLengthBytes` $\rightarrow$ `uint_val: 14850000`
  - `/Sysdb/interface/counter/eth/slice/phy/1/intfCounterDir[intfId=Ethernet1/1]/intfCounter/outDiscards` $\rightarrow$ `uint_val: 4820`

#### 4. Juniper Junos Projection (`node-juniper-ptx`, `et-0/0/0`)
- **OpenConfig Path (`origin="openconfig"`):**
  - `/qos/interfaces/interface[interface-id=et-0/0/0]/output/queues/queue[name=0]/state/max-queue-len` $\rightarrow$ `uint_val: 14850000`
  - `/qos/interfaces/interface[interface-id=et-0/0/0]/output/queues/queue[name=0]/state/dropped-pkts` $\rightarrow$ `uint_val: 4820`
- **Junos Native JTI Path (`origin="junos"`):**
  - `/junos/system/linecard/interface[name=et-0/0/0]/queue[queue-number=0]/allocated-buffer-size` $\rightarrow$ `uint_val: 14850000`
  - `/junos/system/linecard/interface[name=et-0/0/0]/queue[queue-number=0]/tail-drop-packets` $\rightarrow$ `uint_val: 4820`

#### 5. Unified Splunk Normalized View (Preserving Raw Vendor Provenance)
All three vendor projections index into Splunk with:
- `metric_name:queue.depth_bytes = 14850000`, `metric_name:queue.dropped_pkts = 4820`
- Preserved raw dimensions: `vendor` (`cisco` / `arista` / `juniper`), `platform` (`cisco_ios_xr` / `arista_eos` / `juniper_junos`), `gnmi_origin`, `gnmi_path`, `openconfig_path`, and `vendor_native_path`.
