# NetSpout Telemetry Provenance Registry & Authenticity Specification

## 1. Absolute Telemetry Authenticity Directive

NetSpout models **real network operational states, failures, and dynamics** on realistic topologies. It **never invents vendor telemetry schema, contracts, OIDs, YANG paths, or sourcetypes**.

Any telemetry item emitted by NetSpout must possess documented provenance from one of the following authoritative source tiers:
1. **Tier 1 — Vendor Documentation**: Cisco, Arista, Juniper, Palo Alto Networks, Fortinet, Nokia, NVIDIA, F5, Aruba/HPE, NetApp.
2. **Tier 2 — International Standards**: IETF RFCs, IEEE 802.1/802.3, IANA registries, OpenConfig consortium models, ITU-T recommendations.
3. **Tier 3 — Splunk Technology Add-on (TA) Specifications**: Splunkbase published TAs, CIM (Common Information Model) mapping specs, Splunk Stream, Splunk Connect for Syslog (SC4S).

If a specific vendor object, counter, or transport method is not legitimately supported by public vendor or standards documentation, NetSpout classifies it as `UNSUPPORTED_TELEMETRY` rather than synthesizing an artificial field.

---

## 2. Telemetry Fidelity Classification Badges

Every scenario and telemetry stream in NetSpout carries an explicit fidelity badge visible in the UI and catalog metadata:

| Fidelity Badge | Classification | Description & Guarantees |
| :--- | :--- | :--- |
| **NATIVE TRANSPORT** | Level 1 - Real Wire Protocol | Emitted over standard wire protocol sockets (UDP 514 Syslog, UDP 161/162 SNMP BER, UDP 2055/4739 NetFlow/IPFIX, TCP 50051 gRPC/gNMI) adhering strictly to RFC/vendor binary and wire encodings. |
| **MODELED PAYLOAD** | Level 2 - Coherent State Stream | Telemetry payloads generated from underlying physical/topological graph state machines. Values reflect genuine physical conditions (e.g. queue microbursts, optical dBm attenuation, routing table convergence). |
| **SYNTHETIC** | Level 3 - Deterministic Event Stream | Replayed or deterministic pattern streams grounded in real vendor sample captures, used for baseline and stress validation. |

---

## 3. Canonical Telemetry Provenance Ledger

The machine-readable ledger is maintained in [`catalog/telemetry_sources.json`](file:///Users/mahamudc/Documents/NetSpout/catalog/telemetry_sources.json).

### Summary Table of Authoritative Sources

| Source ID | Vendor / Organization | Platform / Technology | Telemetry Protocol | Authoritative Artifact / Contract | Provenance Classification |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `SRC-CISCO-IOSXR-MPLS` | Cisco Systems | Cisco IOS-XR 7.x / ASR 9000 | Syslog | `LDP-5-NBR_RESET`, `MPLS_LDP-4-NBR_SESSION_DOWN` | VENDOR_DOCUMENTED |
| `SRC-CISCO-IOSXR-SRV6` | Cisco Systems | Cisco IOS-XR 7.3+ / 8000 | Syslog / MDT | `ROUTING-SRV6-5-LOCATOR_STATE`, `ISIS-5-SRV6_TILFA_ACTIVATED` | VENDOR_DOCUMENTED |
| `SRC-CISCO-NXOS-EVPN` | Cisco Systems | Cisco Nexus 9000 / NX-OS | Syslog / gNMI | `BGP-4-EVPN_MAC_DUPLICATE`, `VXLAN-4-NVE_VNI_STATE` | VENDOR_DOCUMENTED |
| `SRC-ARISTA-EOS-LANZ` | Arista Networks | Arista EOS 7050X / 7060X | Syslog / LANZ | `LANZ-6-CONGESTION`, `LANZ-4-BUFFER_THRESHOLD_EXCEEDED` | VENDOR_DOCUMENTED |
| `SRC-NVIDIA-SPECTRUM-ROCE` | NVIDIA / Mellanox | NVIDIA Spectrum-3/4 / Cumulus | Syslog / gNMI | `SPECTRUM-PFC-WARN`, `ROCE-4-ECN_CONGESTION_SPIKE` | VENDOR_DOCUMENTED |
| `SRC-NOKIA-SROS-7750` | Nokia | Nokia 7750 SR / SR OS 21.x | Syslog | `SYSTEM-CRITICAL-PORT_DOWN`, `ROUTING-BGP-EVPN_PEER_DOWN` | VENDOR_DOCUMENTED |
| `SRC-RFC-5036-LDP` | IETF | RFC 5036 LDP Standard | SNMPv2c | OID `1.3.6.1.2.1.10.166.4` (MPLS-LDP-STD-MIB) | STANDARDS_BASED |
| `SRC-IEEE-8021QBB-PFC` | IEEE | IEEE 802.1Qbb Priority Flow Control | gNMI / Counters | `openconfig-qos/.../queues/queue/state/transmit-pkts` | STANDARDS_BASED |
| `SRC-OPENCONFIG-INTERFACES` | OpenConfig | openconfig-interfaces.yang | gNMI | `/interfaces/interface/state/oper-status` | STANDARDS_BASED |
| `SRC-SPLUNK-TA-CISCO-IOS` | Splunk | Splunk Add-on for Cisco IOS | Splunk HEC / Syslog | `sourcetype=cisco:ios:syslog`, `sourcetype=cisco:ios:mpls` | SPLUNK_AUTHORITATIVE |
| `SRC-SPLUNK-TA-CISCO-SDWAN` | Splunk | Splunk Add-on for Cisco SD-WAN | Splunk HEC / Syslog | `sourcetype=cisco:sdwan:*` | SPLUNK_AUTHORITATIVE |
| `SRC-CISCO-MDS-SAN` | Cisco Systems | Cisco MDS 9700 Fabric Switches | Syslog / FC | `PORT-5-IF_DOWN_LINK_FAILURE`, `FLOGI-1-DEVICE_LOGIN` | VENDOR_DOCUMENTED |
| `SRC-ITU-G984-GPON-POLAN` | ITU-T | ITU-T G.984 / G.9807 (XGS-PON) | SNMP / Polling | OID `1.3.6.1.2.1.2.2.1` (IF-MIB) Rx Optical Power (dBm) | STANDARDS_BASED |

---

## 4. Multi-Protocol State Coherence Standard

When an incident is simulated (e.g. an optical link degradation or queue microburst):
1. **Device State Store** updates canonical counters and link status.
2. **Syslog Engine** emits RFC 5424/3164 formatted vendor strings reflecting the state change.
3. **SNMP Agent** reflects updated `ifOperStatus` (OID `1.3.6.1.2.1.2.2.1.8`) and emits corresponding `linkDown` traps (OID `1.3.6.1.6.3.1.1.5.3`).
4. **gNMI Streaming Engine** streams updated OpenConfig/YANG notifications with timestamps synchronized to the event.
5. **Flow Engine** records byte/packet count drops or TCP retransmits across affected flow records.

This guarantees that security analysts, network engineers, and Splunk observability pipelines see **one incident, multiple observations, and one coherent underlying state**.
