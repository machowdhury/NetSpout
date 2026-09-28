# NetSpout SNMP OID Architecture, MIB Governance & Licensing Strategy

**Author:** Mahamudul Chowdhury (`machowdhury@yahoo.com`)  
**Gate:** 12 (Native SNMP Architecture & Protocol Definition)  
**Scope:** Canonical OID Identity, MIB Licensing Audit, Standard IETF MIB Baseline, and Enterprise Vendor OID Governance

---

## 1. Canonical OID Architecture (Section 12)

In SNMP (`RFC 2578` SMIv2 / `RFC 3416`), the **authoritative wire identity** of every managed object and notification is its **numeric dotted-decimal `OBJECT IDENTIFIER` (OID)** including its instance suffix. Symbolic MIB names (such as `IF-MIB::ifOperStatus.10101`) exist strictly as human/search enrichment and never appear on the wire.

### 1.1 Structural Anatomy of a Canonical NetSpout OID

```text
Symbolic Enrichment:   IF-MIB :: ifOperStatus . 10101
                       └──┬──┘   └─────┬────┘   └──┬─┘
                      MIB Module   Object Name  Instance Suffix

Authoritative Wire:    1.3.6.1.2.1.2.2.1.8 . 10101
                       └────────┬────────┘   └──┬─┘
                         Base Column OID     Instance Suffix
```

### 1.2 Instance Suffix Rules
Every `SnmpVarBind` emitted or served by NetSpout must include a valid instance sub-identifier suffix:
1. **Scalar Objects (`is_table = False`):** Always terminate with `.0` (e.g., `SNMPv2-MIB::sysUpTime.0` $\rightarrow$ `1.3.6.1.2.1.1.3.0`). A scalar OID without `.0` is invalid in `Response-PDU`, `TRAPv2`, and `INFORM` varbinds.
2. **Single-Index Conceptual Table Columns (`INDEX { ifIndex }`):** Terminate with `.<integer_index>` (e.g., `IF-MIB::ifOperStatus.10101` $\rightarrow$ `1.3.6.1.2.1.2.2.1.8.10101`).
3. **IPv4-Indexed Conceptual Table Columns (`INDEX { bgpPeerRemoteAddr }`):** Terminate with the 4 dotted octets of the IPv4 address (e.g., `BGP4-MIB::bgpPeerState.10.255.0.2` $\rightarrow$ `1.3.6.1.2.1.15.3.1.2.10.255.0.2`).

### 1.3 Canonical OID Registry Schema
Each entry in NetSpout's precompiled OID catalog (`catalog/snmp_oids.json` / `snmp_engine.py`) will conform to:

```json
{
  "oid": "1.3.6.1.2.1.2.2.1.8",
  "name": "ifOperStatus",
  "mib_module": "IF-MIB",
  "asn1_syntax": "Integer32",
  "is_table": true,
  "index_syntax": "ifIndex",
  "default_instance": ".1",
  "vendor": "RFC",
  "enterprise_pen": null,
  "oid_fidelity": "STANDARD_VERIFIED",
  "enums": {
    "1": "up",
    "2": "down",
    "3": "testing",
    "4": "unknown",
    "5": "dormant",
    "6": "notPresent",
    "7": "lowerLayerDown"
  },
  "description": "Current operational state of the interface (RFC 2863)."
}
```

---

## 2. MIB Licensing, Redistribution & Compilation Strategy (Section 13)

### 2.1 Licensing & Redistribution Audit
| MIB Category | Copyright / License Status | Redistribution Policy in NetSpout Git Repository |
| :--- | :--- | :--- |
| **IETF Standard RFC MIBs** (`RFC 1213`, `RFC 2863`, `RFC 3418`, `RFC 4273`, etc.) | IETF Trust / Public Standards Track | Safe to reference OID numbers, object names, and enum values in metadata. Raw ASN.1 SMI text files are unnecessary in git. |
| **Vendor Enterprise MIB Files** (`CISCO-*.my`, `JUNIPER-*.mib`, `PAN-*.mib`, `FORTINET-*.mib`, `TIMETRA-*.mib`) | **Proprietary Vendor Copyright** (often restricted to licensed customers or prohibiting bulk open-source redistribution of raw `.mib`/`.my` files) | **DO NOT COMMIT RAW VENDOR `.mib` / `.my` FILES TO GIT.** Only factual numeric OIDs, object names, ASN.1 syntax tags, and `oid_fidelity` classifications are stored in NetSpout's precompiled metadata dictionary. |
| **User-Provided Local MIBs** | Customer-owned local files | Optional runtime lookup directory (`~/.netspout/mibs/`, git-ignored) for users running custom external receivers. |

### 2.2 Precompiled Metadata Dictionary vs. Runtime SMI Compilation
- **Why Runtime ASN.1 SMI Compilation (`pysmi` / `libsmi`) is Rejected for Core Runtime:**
  1. Parsing raw ASN.1 SMI text files at runtime introduces external library dependencies, startup latency, and parser attack surface (`MIB poisoning` threat).
  2. Requires distributing hundreds of raw vendor `.mib` files in the repository.
- **Selected Strategy — Precompiled Canonical OID Dictionary:**
  - NetSpout stores a curated, schema-validated JSON/Python OID dictionary containing numeric OIDs, symbolic names, MIB module names, `SnmpAsn1Type` wire tags, index rules, and `OidFidelityClass`.
  - Zero external MIB compiler is required at runtime.

---

## 3. Standard IETF MIB Baseline Evaluation (Section 14)

All 11 standard IETF MIB modules were evaluated for NetSpout scenario utility:

| # | Standard MIB Module | IETF RFC | Base OID Prefix | Key Objects / Notifications | NetSpout Priority & Scenario Mapping |
| :-: | :--- | :--- | :--- | :--- | :--- |
| 1 | **`SNMPv2-MIB`** | `RFC 3418` | `1.3.6.1.2.1.1` / `1.3.6.1.6.3.1` | `sysDescr.0`, `sysObjectID.0`, `sysUpTime.0`, `sysName.0`, `coldStart`, `warmStart`, `authenticationFailure` | **MANDATORY BASELINE (Gate 12B)** — Required in every `TRAPv2` and `INFORM` header (`sysUpTime.0`, `snmpTrapOID.0`). |
| 2 | **`IF-MIB`** | `RFC 2863` | `1.3.6.1.2.1.2` / `1.3.6.1.2.1.31` | `linkDown`, `linkUp`, `ifIndex`, `ifDescr`, `ifName`, `ifAlias`, `ifAdminStatus`, `ifOperStatus`, `ifInErrors`, `ifOutDiscards`, `ifHCInOctets`, `ifHCOutOctets` | **MANDATORY BASELINE (Gate 12B)** — Primary carrier/campus interface fault & recovery telemetry. |
| 3 | **`BGP4-MIB`** | `RFC 4273` | `1.3.6.1.2.1.15` | `bgpEstablished` (`15.7.1`), `bgpBackwardTransition` (`15.7.2`), `bgpPeerState`, `bgpPeerLastError`, `bgpPeerRemoteAddr`, `bgpPeerRemoteAs` | **MANDATORY BASELINE (Gate 12B)** — Core routing adjacency telemetry for `service_provider_cisco` and `cisco_sdwan_brownout`. |
| 4 | **`OSPF-MIB`** | `RFC 4750` | `1.3.6.1.2.1.14` | `ospfNbrStateChange` (`14.16.2.2`), `ospfRouterId`, `ospfNbrIpAddr`, `ospfNbrState` | **HIGH (Gate 12B/12D)** — Used in `arch_wan_global_backbone` and `arch_can_multi_building`. |
| 5 | **`ENTITY-MIB`** | `RFC 6933` | `1.3.6.1.2.1.47` | `entPhysicalDescr`, `entPhysicalClass`, `entPhysicalName`, `entPhysicalModelName`, `entPhysicalSerialNum`, `entConfigChange` | **HIGH (Gate 12D)** — Hardware chassis/module inventory for polling and environmental correlation. |
| 6 | **`IP-MIB`** | `RFC 4293` | `1.3.6.1.2.1.4` | `ipInReceives`, `ipInDiscards`, `ipOutNoRoutes`, `ipSystemStatsInOctets` | **MEDIUM (Gate 12D)** — Layer 3 forwarding & route discard counters during polling. |
| 7 | **`TCP-MIB`** | `RFC 4022` | `1.3.6.1.2.1.6` | `tcpCurrEstab`, `tcpAttemptFails`, `tcpEstabResets`, `tcpRetransSegs` | **MEDIUM (Gate 12D)** — Transport connection stress indicators (`ddos_attack`, `mixed_sase_degradation`). |
| 8 | **`UDP-MIB`** | `RFC 4113` | `1.3.6.1.2.1.7` | `udpInDatagrams`, `udpNoPorts`, `udpInErrors`, `udpOutDatagrams` | **MEDIUM (Gate 12D)** — Baseline UDP datagram statistics. |
| 9 | **`HOST-RESOURCES-MIB`** | `RFC 2790` | `1.3.6.1.2.1.25` | `hrSystemUptime`, `hrStorageUsed`, `hrProcessorLoad` | **MEDIUM (Gate 12D)** — Server/appliance CPU & storage polling (`arch_nas_storage_cluster`). |
| 10 | **`BRIDGE-MIB`** | `RFC 4188` | `1.3.6.1.2.1.17` | `newRoot` (`17.0.1`), `topologyChange` (`17.0.2`), `dot1dTpFdbPort` | **MEDIUM (Gate 12D)** — L2 spanning-tree and MAC table telemetry (`arch_lan_campus_access`, `cisco_campus_rogue`). |
| 11 | **`LLDP-MIB`** | `IEEE 802.1AB` | `1.0.8802.1.1.2` | `lldpRemTableChange`, `lldpRemSysName`, `lldpRemPortId` | **MEDIUM (Gate 12D)** — Neighbor topology discovery validation. |

---

## 4. Enterprise Vendor OID Strategy & Fidelity Classification (Section 15)

### 4.1 Four-Tier OID Fidelity Classification
Every OID in NetSpout carries an explicit `oid_fidelity` attribute surfaced in manifests and UI badges:
1. **`STANDARD_VERIFIED`:** Official IETF / IEEE standard OID (`1.3.6.1.2.1.*`, `1.3.6.1.6.3.*`, `1.0.8802.*`) verified against published RFCs.
2. **`VENDOR_VERIFIED`:** Enterprise OID (`1.3.6.1.4.1.<PEN>.*`) verified against published vendor MIB specifications (exact arc path, ASN.1 syntax, and enum semantics).
3. **`MODELED`:** Uses the vendor's authentic IANA Private Enterprise Number (`1.3.6.1.4.1.<PEN>`), but models a representative sub-tree where vendor hardware sub-tables vary by platform OS.
4. **`SYNTHETIC`:** Experimental sandbox OID (`1.3.6.1.4.1.59999.*`) used exclusively in unit/negative tests.

### 4.2 Multi-Vendor IANA Private Enterprise Number (PEN) & OID Audit

| Vendor Family | IANA PEN | Enterprise Prefix | Verified / Audited MIBs & OIDs | Fidelity Tier |
| :--- | :---: | :--- | :--- | :---: |
| **Cisco Systems** | `9` | `1.3.6.1.4.1.9` | `CISCO-PROCESS-MIB` (`9.9.109.1.1.1.1.8` `cpmCPUTotal5minRev`), `CISCO-MEMORY-POOL-MIB` (`9.9.48.1.1.1.5` `ciscoMemoryPoolUsed`), `CISCO-ENVMON-MIB` (`9.9.13.1.3.1.3` `ciscoEnvMonTemperatureStatusValue`, `9.9.13.3.0.2` `ciscoEnvMonTemperatureNotification`), `CISCO-BGP4-MIB` (`9.9.187.1.2.5.1.3` `cbgpPeer2State`) | **`VENDOR_VERIFIED`** |
| **Juniper Networks** | `2636` | `1.3.6.1.4.1.2636` | `JUNIPER-MIB` (`2636.3.1.13.1.7` `jnxOperatingTemp`, `2636.3.1.13.1.8` `jnxOperatingCPU`, `2636.3.1.13.1.6` `jnxOperatingState`), `JUNIPER-ALARM-MIB` (`2636.4.1.3.1.1.3` `jnxRedAlarmCount`) | **`VENDOR_VERIFIED`** |
| **Arista Networks** | `30065` | `1.3.6.1.4.1.30065` | `ARISTA-QUEUE-MIB` (`30065.3.6.1...`) & `ENTITY-SENSOR-MIB` (`1.3.6.1.2.1.99`) are **`VENDOR_VERIFIED` / `STANDARD_VERIFIED`**; existing `snmp_engine.py` entries under `30065.3.1..3.4` are explicitly classified as **`MODELED`**. | **`VENDOR_VERIFIED` + `MODELED`** |
| **Palo Alto Networks** | `25461` | `1.3.6.1.4.1.25461` | `PAN-COMMON-MIB` (`25461.2.1.2.3.1.0` `panSessionUtilization`, `25461.2.1.2.3.3.0` `panSessionActive`) | **`VENDOR_VERIFIED`** |
| **Fortinet** | `12356` | `1.3.6.1.4.1.12356` | `FORTINET-FORTIGATE-MIB` (`12356.101.4.1.3.0` `fgSysCpuUsage`, `12356.101.4.1.4.0` `fgSysMemUsage`, `12356.101.4.1.8.0` `fgSysSesCount`) | **`VENDOR_VERIFIED`** |
| **Nokia (Alcatel-Lucent / TiMetra)** | `6527` | `1.3.6.1.4.1.6527` | `TIMETRA-SYSTEM-MIB` (`6527.3.1.2.1.1.1.0` `sgiCpuUsage`), `TIMETRA-CHASSIS-MIB` (`6527.3.1.2.2.1...`) | **`VENDOR_VERIFIED`** |
| **F5 Networks** | `3375` | `1.3.6.1.4.1.3375` | `F5-BIGIP-SYSTEM-MIB` (`3375.2.1.1.2.1.44.0` `sysStatClientCurConns`), `F5-BIGIP-LOCAL-MIB` (`3375.2.2.10.2.3.1.12` `ltmVirtualServStatClientCurConns`) | **`VENDOR_VERIFIED`** |
| **VMware** | `6876` | `1.3.6.1.4.1.6876` | `VMWARE-SYSTEM-MIB` (`6876.1.1.0` `vmwProdName`), `VMWARE-VMINFO-MIB` (`6876.2.1.1.6` `vmwVmState`) | **`VENDOR_VERIFIED`** |
| **Linux / Net-SNMP (UCD-SNMP)** | `2021` / `8072` | `1.3.6.1.4.1.2021` / `.8072` | `UCD-SNMP-MIB` (`2021.11.9.0` `ssCpuUser`, `2021.4.6.0` `memAvailReal`), `NET-SNMP-AGENT-MIB` (`8072.3.2.10` `netSnmp.linux`) | **`VENDOR_VERIFIED`** |

### 4.3 Specific Schema Corrections Identified for Gate 12B
During the Gate 12 audit of `src/netspout_core/snmp_engine.py`, two metadata refinements were cataloged for Gate 12B:
1. `SNMPv2-MIB::sysObjectID` (`1.3.6.1.2.1.1.2.0`) is currently listed with `type="OctetString"` in `RAW_MIB_DEFINITIONS`; on the wire in ASN.1 BER it **must** be encoded as `OBJECT IDENTIFIER (0x06)`.
2. Table column definitions (`is_table=True`) in `RAW_MIB_DEFINITIONS` store the column base OID (e.g., `1.3.6.1.2.1.2.2.1.8` for `ifOperStatus`); the Gate 12B varbind builder will automatically append the deterministic interface/entity instance suffix (e.g., `.1`) when constructing wire varbinds.
