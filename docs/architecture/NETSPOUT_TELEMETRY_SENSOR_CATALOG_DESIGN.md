# NETSPOUT TELEMETRY SENSOR CATALOG DESIGN

**Document ID:** `NETSPOUT-ARCH-G13-CATALOG`  
**Gate:** Gate 13 (Architecture & Protocol Definition)  
**Status:** APPROVED SPECIFICATION  

---

## 1. Architectural Purpose & Single-Registry Rule

In accordance with NetSpout's single canonical registry architecture:
- **`catalog/scenarios.json`** remains the sole source of truth for scenarios and golden-path definitions.
- **`catalog/telemetry_protocols.json`** remains the canonical protocol metadata catalog.
- In Gate 13B/13C, the **Telemetry Sensor Registry** (`src/netspout_core/gnmi/sensor_registry.py` backed by `catalog/telemetry_sensors.json`) will define the declarative mapping from **gNMI Path ASTs** (both OpenConfig and vendor-native origins) to **`ScenarioStateStore` state extractors**, **SNMP OID equivalents**, and **Syslog mnemonic triggers**.
- No sensor definition duplicates scenario topology or timeline logic; sensors purely project the live `DeviceStateSnapshot` into YANG-compliant trees.

---

## 2. Canonical Sensor Entry Schema

Each entry in the Telemetry Sensor Registry adheres to the following strict schema:

```json
{
  "sensor_id": "oc_interfaces_counters",
  "domain": "interfaces",
  "title": "Interface High-Capacity Packet & Octet Counters",
  "openconfig": {
    "origin": "openconfig",
    "module": "openconfig-interfaces",
    "revision": "2022-10-25",
    "xpath": "/interfaces/interface[name=*]/state/counters",
    "subscription_modes": ["SAMPLE"],
    "default_sample_interval_ms": 5000
  },
  "vendor_native_mappings": {
    "CISCO_IOS_XR": {
      "origin": "Cisco-IOS-XR-infra-statsd-oper",
      "xpath": "/infra-statistics/interfaces/interface[interface-name=*]/latest/generic-counters",
      "classification": "VERIFIED",
      "reference": "https://xrdocs.io/telemetry"
    },
    "CISCO_IOS_XE": {
      "origin": "Cisco-IOS-XE-interfaces-oper",
      "xpath": "/interfaces/interface[name=*]/statistics",
      "classification": "VERIFIED",
      "reference": "https://github.com/YangModels/yang/tree/main/vendor/cisco/xe"
    },
    "ARISTA_EOS": {
      "origin": "eos_native",
      "xpath": "/Sysdb/interface/counter/eth/slice/phy/[intf=*]/currentStatistics",
      "classification": "VERIFIED",
      "reference": "https://github.com/aristanetworks/goarista"
    },
    "JUNIPER_JUNOS": {
      "origin": "junos",
      "xpath": "/junos/system/linecard/interface[name=*]/statistics",
      "classification": "VERIFIED",
      "reference": "https://www.juniper.net/documentation/us/en/software/junos/open-config/index.html"
    }
  },
  "cross_transport_bindings": {
    "state_store_path": "interfaces[*].counters",
    "snmp_oids": [
      "1.3.6.1.2.1.31.1.1.1.6 (ifHCInOctets)",
      "1.3.6.1.2.1.31.1.1.1.10 (ifHCOutOctets)",
      "1.3.6.1.2.1.2.2.1.14 (ifInErrors)",
      "1.3.6.1.2.1.2.2.1.20 (ifOutErrors)"
    ],
    "netflow_fields": ["IN_BYTES", "IN_PKTS", "INPUT_SNMP", "OUTPUT_SNMP"],
    "syslog_mnemonics": []
  },
  "leaves": [
    {"name": "in-octets", "yang_type": "uint64", "json_ietf_type": "string", "unit": "bytes"},
    {"name": "out-octets", "yang_type": "uint64", "json_ietf_type": "string", "unit": "bytes"},
    {"name": "in-unicast-pkts", "yang_type": "uint64", "json_ietf_type": "string", "unit": "packets"},
    {"name": "out-unicast-pkts", "yang_type": "uint64", "json_ietf_type": "string", "unit": "packets"},
    {"name": "in-errors", "yang_type": "uint64", "json_ietf_type": "string", "unit": "packets"},
    {"name": "out-errors", "yang_type": "uint64", "json_ietf_type": "string", "unit": "packets"},
    {"name": "in-fcs-errors", "yang_type": "uint64", "json_ietf_type": "string", "unit": "packets"},
    {"name": "in-discards", "yang_type": "uint64", "json_ietf_type": "string", "unit": "packets"},
    {"name": "out-discards", "yang_type": "uint64", "json_ietf_type": "string", "unit": "packets"},
    {"name": "carrier-transitions", "yang_type": "uint64", "json_ietf_type": "string", "unit": "transitions"}
  ]
}
```

---

## 3. Comprehensive Multi-Vendor Sensor Catalog Matrix

Every sensor in the catalog is explicitly classified per vendor as:
- **`VERIFIED`**: Verified against public OpenConfig YANG schemas and official vendor telemetry documentation (`xrdocs.io`, `goarista`, Juniper JTI docs, `YangModels/yang`).
- **`MODELED`**: Representative synthesis following vendor YANG structure conventions where hardware/ASIC-specific subtrees vary by linecard generation.
- **`NOT_SUPPORTED`**: Explicitly excluded from a specific vendor profile and rejected with `StatusCode.NOT_FOUND`.

| Sensor ID | Domain | OpenConfig Path (`origin="openconfig"`) | Mode | Cisco IOS XR (`VERIFIED`/`MODELED`) | Cisco IOS XE (`VERIFIED`/`MODELED`) | Arista EOS (`VERIFIED`/`MODELED`) | Juniper Junos (`VERIFIED`/`MODELED`) | Shared State / SNMP / Syslog Binding |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `oc_if_state` | Interfaces | `/interfaces/interface[name=*]/state` | `ON_CHANGE` / `SAMPLE` | `VERIFIED` (`Cisco-IOS-XR-pfi-im-cmd-oper`) | `VERIFIED` (`Cisco-IOS-XE-interfaces-oper`) | `VERIFIED` (`eos_native:/Sysdb/interface/status/...`) | `VERIFIED` (`openconfig-interfaces`) | `ifAdminStatus`, `ifOperStatus`, `LINK-3-UPDOWN`, `UI_NETCONF_CMD` |
| `oc_if_counters` | Interfaces | `/interfaces/interface[name=*]/state/counters` | `SAMPLE` | `VERIFIED` (`Cisco-IOS-XR-infra-statsd-oper`) | `VERIFIED` (`Cisco-IOS-XE-interfaces-oper`) | `VERIFIED` (`eos_native:/Sysdb/interface/counter/...`) | `VERIFIED` (`junos:/junos/system/linecard/interface/statistics`) | `ifHCInOctets`, `ifHCOutOctets`, `ifInErrors`, NetFlow `IN_BYTES` |
| `oc_subif_ipv4` | Subinterfaces | `/interfaces/interface[name=*]/subinterfaces/subinterface[index=*]/ipv4/addresses/address[ip=*]/state` | `ON_CHANGE` | `VERIFIED` (`Cisco-IOS-XR-ipv4-io-oper`) | `VERIFIED` (`Cisco-IOS-XE-interfaces-oper`) | `VERIFIED` (`openconfig-if-ip`) | `VERIFIED` (`openconfig-if-ip`) | `DeviceStateSnapshot.interfaces[*].ipv4_addresses` |
| `oc_lldp_nbr` | LLDP | `/lldp/interfaces/interface[name=*]/neighbors/neighbor[id=*]/state` | `ON_CHANGE` / `SAMPLE` | `VERIFIED` (`Cisco-IOS-XR-ethernet-lldp-oper`) | `VERIFIED` (`Cisco-IOS-XE-lldp-oper`) | `VERIFIED` (`openconfig-lldp`) | `VERIFIED` (`openconfig-lldp`) | `LLDP-MIB::lldpRemSysName`, `lldpRemPortId`, Topology Graph Edges |
| `oc_lacp_mbr` | LACP | `/lacp/interfaces/interface[name=*]/members/member[interface=*]/state` | `ON_CHANGE` / `SAMPLE` | `VERIFIED` (`Cisco-IOS-XR-bundlemgr-oper`) | `MODELED` (`Cisco-IOS-XE-lacp-oper`) | `VERIFIED` (`openconfig-lacp`) | `VERIFIED` (`openconfig-lacp`) | `IEEE8023-LAG-MIB`, Bundle member active/standby state |
| `oc_bgp_nbr` | BGP | `/network-instances/network-instance[name=*]/protocols/protocol[identifier=BGP][name=*]/bgp/neighbors/neighbor[neighbor-address=*]/state` | `ON_CHANGE` / `SAMPLE` | `VERIFIED` (`Cisco-IOS-XR-ipv4-bgp-oper`) | `VERIFIED` (`Cisco-IOS-XE-bgp-oper`) | `VERIFIED` (`eos_native:/Smash/routing/bgp/...`) | `VERIFIED` (`openconfig-bgp` + `/junos/services/bgp/...`) | `BGP4-MIB::bgpPeerState`, `BGP-5-ADJCHANGE`, `RPD_BGP_NEIGHBOR_STATE_CHANGED` |
| `oc_bgp_afi` | BGP Prefixes | `.../bgp/neighbors/neighbor[neighbor-address=*]/afi-safis/afi-safi[afi-safi-name=*]/state/prefixes` | `SAMPLE` / `ON_CHANGE` | `VERIFIED` (`Cisco-IOS-XR-ipv4-bgp-oper`) | `VERIFIED` (`Cisco-IOS-XE-bgp-oper`) | `VERIFIED` (`openconfig-bgp`) | `VERIFIED` (`openconfig-bgp`) | `prefixes.received`, `prefixes.installed`, `prefixes.sent` |
| `oc_ospf_nbr` | OSPF | `.../protocols/protocol[identifier=OSPF][name=*]/ospfv2/areas/area[identifier=*]/interfaces/interface[id=*]/neighbors/neighbor[router-id=*]/state` | `ON_CHANGE` | `VERIFIED` (`Cisco-IOS-XR-ipv4-ospf-oper`) | `VERIFIED` (`Cisco-IOS-XE-ospf-oper`) | `MODELED` (`openconfig-ospfv2`) | `VERIFIED` (`openconfig-ospfv2`) | `OSPF-MIB::ospfNbrState`, `OSPF-5-ADJCHG`, `RPD_OSPF_NBRDOWN` |
| `oc_isis_adj` | IS-IS | `.../protocols/protocol[identifier=ISIS][name=*]/isis/interfaces/interface[interface-id=*]/levels/level[level-number=*]/adjacencies/adjacency[system-id=*]/state` | `ON_CHANGE` | `VERIFIED` (`Cisco-IOS-XR-clns-isis-oper`) | `MODELED` (`openconfig-isis`) | `VERIFIED` (`openconfig-isis`) | `VERIFIED` (`openconfig-isis`) | `ISIS-MIB`, `ISIS-ADJCHANGE`, `RPD_ISIS_ADJDOWN` |
| `oc_aft_ipv4` | Routing / FIB | `/network-instances/network-instance[name=*]/afts/ipv4-unicast/ipv4-entries/ipv4-entry[prefix=*]/state` | `ON_CHANGE` / `SAMPLE` | `MODELED` (`Cisco-IOS-XR-fib-common-oper`) | `MODELED` (`Cisco-IOS-XE-fib-oper`) | `VERIFIED` (`openconfig-aft`) | `VERIFIED` (`openconfig-aft`) | Active next-hop group, ECMP path count, FIB packets-forwarded |
| `oc_qos_queue` | QoS / Buffers | `/qos/interfaces/interface[interface-id=*]/output/queues/queue[name=*]/state` | `SAMPLE` | `VERIFIED` (`Cisco-IOS-XR-qos-ma-oper`) | `VERIFIED` (`Cisco-IOS-XE-interfaces-oper:qos-queue-stats`) | `VERIFIED` (`eos_native:/Sysdb/hardware/counter/Lanz/...`) | `VERIFIED` (`junos:/junos/system/linecard/qmon/...`) | `transmit-pkts`, `transmit-octets`, `dropped-pkts`, `max-queue-len` |
| `oc_platform_comp` | Platform / Env | `/components/component[name=*]/state` | `SAMPLE` / `ON_CHANGE` | `VERIFIED` (`Cisco-IOS-XR-plat-chas-invmgr-oper`) | `VERIFIED` (`Cisco-IOS-XE-environment-oper`) | `VERIFIED` (`openconfig-platform`) | `VERIFIED` (`junos:/junos/system/linecard/environment/`) | `ENTITY-SENSOR-MIB`, `cpmCPUTotal5minRev`, `temperature.instant` |
| `oc_platform_optics` | Optics / DOM | `/components/component[name=*]/transceiver/state` | `SAMPLE` | `VERIFIED` (`Cisco-IOS-XR-controller-optics-oper`) | `VERIFIED` (`Cisco-IOS-XE-transceiver-oper`) | `VERIFIED` (`openconfig-platform-transceiver`) | `VERIFIED` (`junos:/junos/system/linecard/optics/`) | `input-power.instant` (dBm), `output-power.instant` (dBm), `laser-bias-current.instant` (mA) |
| `oc_system_cpu_mem` | System Health | `/system/cpus/cpu[index=*]/state` & `/system/memory/state` | `SAMPLE` | `VERIFIED` (`Cisco-IOS-XR-wdsysmon-fd-oper`) | `VERIFIED` (`Cisco-IOS-XE-process-cpu-oper` / `memory-oper`) | `VERIFIED` (`openconfig-system`) | `VERIFIED` (`openconfig-system`) | `CISCO-PROCESS-MIB`, `HOST-RESOURCES-MIB`, CPU total/user/kernel %, memory used/free |
| `oc_evpn_vxlan` | EVPN / VXLAN | `/network-instances/network-instance[name=*]/evpn/` | `ON_CHANGE` / `SAMPLE` | `MODELED` (`Cisco-IOS-XR-l2vpn-oper`) | `MODELED` (`Cisco-IOS-XE-l2vpn-oper`) | `VERIFIED` (`eos_native:/Smash/vxlan/vtepStatus`) | `MODELED` (`openconfig-evpn`) | Type-2 MAC/IP count, Type-5 prefix count, VTEP peer status (`NOT_SUPPORTED` on pure L3 nodes without EVPN role) |

---

## 4. Path Resolution & Subscription Dispatch Pipeline

1. **Path Tokenization:** Incoming `gnmi.Path` (`origin`, `target`, `elem[]`) is normalized into a canonical `(origin, path_pattern, keys_dict)` tuple.
2. **Vendor Profile Guard:** The target node's `VendorProfile` (`CISCO_IOS_XR`, `CISCO_IOS_XE`, `ARISTA_EOS`, `JUNIPER_JUNOS`) validates whether the requested `origin` is supported by that platform. Requesting `origin="eos_native"` from a `CISCO_IOS_XR` target immediately returns `StatusCode.NOT_FOUND`.
3. **Extractor Execution:** The matched `SensorDefinition` invokes its pure state extractor function against the immutable `DeviceStateSnapshot` for the current simulation tick, applying vendor-specific interface naming, key formatting, and leaf type coercion (e.g., RFC 7951 stringified `uint64` for `JSON_IETF`).
