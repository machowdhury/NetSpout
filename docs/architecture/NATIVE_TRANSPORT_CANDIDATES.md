# NetSpout Architecture: Native Transport Candidates Register

**Status:** REGISTER MAINTAINED (NON-IMPLEMENTED)  
**Gate Context:** NetSpout Gate 10 (Scenario Promotion Wave 2)  
**Platform Policy:** Strict containment of simulation telemetry within Splunk HTTP Event Collector (HEC) transport modeling. Native wire socket transport is explicitly deferred to inform a future dedicated Native Protocol Engine phase.

---

## 1. Executive Overview & Policy

NetSpout models realistic network device telemetry using canonical vendor log formats and JSON payloads dispatched via Splunk HEC (`transport_protocol = "Splunk HEC"`, `fidelity_badge = "MODELED PAYLOAD"`).

While HEC payload modeling provides 100% indexed fidelity for Splunk dashboards, SPL searches, and SOC/NOC alerting workflows, certain advanced engineering use cases (such as testing third-party collectors, hardware appliances, or live packet brokers) may benefit from native wire socket emissions.

**Gate 10 Policy:** **NO NATIVE WIRE PROTOCOLS ARE IMPLEMENTED IN GATE 10.**  
This document serves as the formal register of candidate wire transports, evaluating their potential value, technical architecture, and complexity to guide future platform roadmap decisions.

---

## 2. Candidate Native Transport Register

### 2.1. Candidate 1: SNMP Traps & Polling (UDP 161 / UDP 162)
* **Relevant Scenarios:**
  * `arch_lan_campus_access` (Link-up/down, Port Security err-disable traps)
  * `arch_man_carrier_ring` (ITU-T G.8032 ERPS state change traps)
  * `arch_wlan_meraki_catalyst` (CleanAir radio interference trap notifications)
* **Protocol Standard:** SNMPv2c / SNMPv3 (RFC 3411–3418), RFC 1213 (MIB-II), Cisco Enterprise MIBs (`CISCO-PORT-SECURITY-MIB`, `CISCO-ERR-DISABLE-MIB`).
* **Current Implementation:**
  * Modeled payload: Traps and poll states are translated to canonical syslog / JSON event records dispatched directly to Splunk HEC with `node_type`, `vendor`, and status tags.
* **Potential Native Implementation:**
  * Python-based `asyncio` UDP socket daemon listening on port 161 (SNMP GET/WALK responder with simulated MIB tree) and UDP client emitting SNMPv2c/v3 Trap PDUs to port 162 on external network management systems (NMS).
* **User Value:** **MEDIUM-HIGH**  
  * Enables integration testing with legacy network management systems (e.g., SolarWinds, OpenNMS, Micro Focus NNMi) that ingest raw SNMP traps rather than Splunk HEC.
* **Implementation Complexity:** **HIGH**  
  * Requires full ASN.1 BER (Basic Encoding Rules) encoder/decoder, SNMP PDU serialization, simulated OID trees for 36 vendors, and community string/USM credential management.
* **Recommendation:** **DEFER**. Current HEC payload modeling satisfies 100% of Splunk observability requirements. Native SNMP belongs in a dedicated protocol simulator gate.

---

### 2.2. Candidate 2: IPFIX & NetFlow v9 Flow Exporter (UDP 2055 / UDP 4739)
* **Relevant Scenarios:**
  * `service_provider_cisco` (Carrier transit route flow shift and diversion)
  * `arch_man_carrier_ring` (Metro aggregation leaf flow export)
  * `mixed_backbone_optical` (MPLS RSVP-TE bypass flow shift)
* **Protocol Standard:** IPFIX (RFC 7011–7015), NetFlow v9 (RFC 3954).
* **Current Implementation:**
  * Modeled payload: Flow records are structured as JSON flow summaries with canonical IPFIX field semantics (`in_octets`, `out_octets`, `src_ip`, `dest_ip`, `flow_flags`) and sent to HEC.
* **Potential Native Implementation:**
  * Binary UDP datagram generator emitting NetFlow v9 / IPFIX Template and Data FlowSets to external flow collectors (e.g., Splunk Stream, Kentik, Plixer Scrutinizer).
* **User Value:** **HIGH**  
  * Flow records allow testing network traffic analysis (NTA) and network detection and response (NDR) appliances without needing high-throughput traffic generators.
* **Implementation Complexity:** **HIGH**  
  * Requires binary struct packing of flowset headers, periodic template refresh intervals, sequence number tracking, and multi-threaded UDP transmission.
* **Recommendation:** **DEFER**. JSON flow records accurately simulate flow telemetry inside Splunk without the overhead of binary wire encoding.

---

### 2.3. Candidate 3: gNMI & Model-Driven Telemetry (MDT) Dial-Out (gRPC / HTTP/2 TCP 57400 / 50051)
* **Relevant Scenarios:**
  * `openconfig_mdt_streaming` (OpenConfig interface and component telemetry)
  * `service_provider_cisco` (ASR 9000 / Cisco 8000 MDT streaming telemetry)
* **Protocol Standard:** gNMI (gRPC Network Management Interface), OpenConfig YANG data models, Cisco MDT Dial-Out (gRPC / TCP).
* **Current Implementation:**
  * Modeled payload: GPBKV (Google Protocol Buffers Key-Value) JSON structures dispatched via HEC directly into Splunk event (`idx_network_ops`) and metric (`cisco_mdt_metrics`) stores.
* **Potential Native Implementation:**
  * gRPC client initiating dial-out streaming sessions with protobuf-encoded telemetry messages (`telemetry.proto`) pushed to external gRPC collectors or Telegraf plugins.
* **User Value:** **MEDIUM**  
  * Allows validating pipeline collectors like Splunk OpenTelemetry Collector or Telegraf before ingestion into Splunk.
* **Implementation Complexity:** **VERY HIGH**  
  * Requires compiling Protocol Buffers, managing HTTP/2 gRPC channels, handling TLS client certificates, and implementing YANG schema validation.
* **Recommendation:** **DEFER**. Dual-store HEC emission cleanly proves metric store separation and pipeline discovery without gRPC daemon dependencies.

---

### 2.4. Candidate 4: Native Syslog Wire Transport (RFC 5424 / RFC 3164 UDP 514 / TCP 6514 TLS)
* **Relevant Scenarios:**
  * `arch_lan_campus_access` (Catalyst switchport syslog)
  * `arch_vpn_remote_workforce` (Cisco ASA VPN syslog)
  * `arch_wlan_meraki_catalyst` (Catalyst CleanAir syslog)
  * All 29 NetSpout scenarios.
* **Protocol Standard:** RFC 5424 (The Syslog Protocol), RFC 3164 (BSD Syslog), RFC 5425 (TLS Transport).
* **Current Implementation:**
  * Modeled payload: Canonical RFC 3164/5424 header formatting with facility/severity tags and ISO/syslog timestamps dispatched via HEC.
* **Potential Native Implementation:**
  * Raw UDP/TCP socket emitter pushing formatted syslog lines directly to Splunk Universal Forwarder (UF) syslog inputs, Heavy Forwarders, or rsyslog/syslog-ng relays.
* **User Value:** **MEDIUM**  
  * Useful for environments where Splunk HEC is blocked or where syslog aggregation relays (e.g., Cribl, rsyslog) are mandatory.
* **Implementation Complexity:** **LOW-MEDIUM**  
  * Straightforward UDP/TCP socket connection, but requires destination availability and lacks delivery acknowledgments (for UDP).
* **Recommendation:** **DEFER**. HEC provides guaranteed HTTP response codes (`200 OK`, `total_events_generated == dispatch_succeeded`), enabling programmatic validation and destination failure integrity that raw UDP syslog cannot match.

---

## 3. Register Summary & Platform Strategy

| Candidate Protocol | Target Scenarios | User Operational Value | Implementation Complexity | Wave 2 Status | Strategic Roadmap Gate |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **SNMP Traps / Poll (UDP 161/162)** | LAN, MAN, WLAN | Medium-High | High | **DEFERRED** | Dedicated SNMP Protocol Engine Gate |
| **IPFIX / NetFlow (UDP 2055/4739)** | SP Core, Optical, DC | High | High | **DEFERRED** | Dedicated Flow Telemetry Engine Gate |
| **gNMI / MDT (gRPC TCP 57400)** | SP Core, OpenConfig | Medium | Very High | **DEFERRED** | Advanced Observability Pipeline Gate |
| **Native Syslog (UDP 514 / TCP 6514)** | All 29 scenarios | Medium | Low-Medium | **DEFERRED** | Syslog Forwarder Integration Gate |

### Conclusion
By maintaining strict HEC transport modeling in Gate 10, NetSpout preserves architectural stability, ensures deterministic test reproducibility, and avoids fragile socket-level dependencies while fully delivering 100% verified operational use-case telemetry to Splunk.
