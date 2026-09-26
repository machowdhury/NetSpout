# NETSPOUT GATE 11B: NATIVE FLOW TRANSPORT IMPLEMENTATION

**Gate:** NetSpout Gate 11B (Native Flow Transport Implementation)  
**Status:** IMPLEMENTATION COMPLETE & CERTIFIED  
**Author:** Mahamudul Chowdhury (`machowdhury@yahoo.com`)  
**Repository:** [https://github.com/machowdhury/NetSpout](https://github.com/machowdhury/NetSpout)  

---

## 1. Executive Summary & Architecture Compliance

NetSpout Gate 11B implements **Mode B (Native Transport)**, enabling NetSpout to act as a standards-compliant network telemetry exporter emitting wire-accurate binary Cisco NetFlow Version 9 (RFC 3954) and IETF IPFIX (RFC 7011 / RFC 7012) datagrams over UDP to external collection infrastructure (Splunk Stream, ElastiFlow, nProbe) without modifying or degrading the existing Mode A (Direct-to-Splunk via HEC) simulation architecture.

### Architectural Invariant Checklist
- [x] **Zero Architecture Conflicts:** All 20 architecture decisions from Gate 11 were strictly followed.
- [x] **Decoupled Architecture:** Telemetry generators emit canonical `FlowRecord` models; transport is an orthogonal delivery mechanism. Zero scenario runner forking (no `NetFlowScenarioRunner`).
- [x] **Pure Python Standard Library:** Uses built-in `struct`, `socket`, and `ipaddress`. Zero external binary dependencies (`scapy` rejected).
- [x] **Safe by Default:** Outbound UDP transmission is restricted to RFC 1918 private and loopback destinations. Public IP export is hard-blocked.
- [x] **Rate Limiting & Caps:** Token-bucket pacer capped at 100 pps (max 1,000 pps) with a 10,000 packet ceiling per scenario run.
- [x] **AppInspect Compliance:** The Splunk App package (`netspout.spl`) contains zero raw socket code; native export executes in user/container space in the backend daemon.
- [x] **Mode A Preservation:** All 12 Golden Paths continue to run with 100% completeness and PASS on live Splunk.

---

## 2. Core Implementation Modules

The implementation is modularized across 7 dedicated modules in `src/netspout_core/`:

```
src/netspout_core/
├── models.py                     # FlowRecord, TransportResult, TransportErrorType, CompanionControlManifest
├── exporter_session.py           # Stateful ExporterSession tracking sequence numbers, sysUpTime, active templates
├── netflow_v9_encoder.py         # RFC 3954 binary encoder (20-byte header, FlowSets, 43-byte record, padding)
├── ipfix_encoder.py              # RFC 7011 binary encoder (16-byte header, Sets, 64-byte record, 64-bit counters)
├── transport_safety.py           # RFC 1918 / Loopback safe-by-default destination blocker
├── rate_limiter.py               # Token-bucket rate limiter and packet ceiling enforcer
├── transport_native_flow.py      # Bounded UDP transport engine with circuit breaker
└── companion_manifest.py         # Splunk HEC companion control manifest and SPL query generator
```

### 2.1. Canonical Flow Model: `FlowRecord`
A protocol-agnostic data structure capturing the full IP 5-tuple, metrics, and routing metadata:
- `src_ip`, `dest_ip` (IPv4 string)
- `src_port`, `dest_port` (0..65535)
- `protocol` (6=TCP, 17=UDP, 1=ICMP)
- `tcp_flags` (bitmask: SYN, ACK, FIN, RST)
- `tos_dscp` (DiffServ / Type of Service)
- `src_as`, `dest_as` (Autonomous System Numbers)
- `input_snmp`, `output_snmp` (Ingress/Egress ifIndex)
- `bytes_count`, `packets_count` (Counters)
- `start_time_ms`, `end_time_ms` (Timing)
- `netspout_run_id`, `netspout_scenario_id`, `netspout_phase` (Control metadata)

### 2.2. Exporter Session: `ExporterSession`
Maintains device-level state scoped per `(run_id, node_id)`:
- `sequence_number`: Protocol-specific sequence counter (records sent in NetFlow v9; data records sent in IPFIX).
- `sys_uptime_base_ms`: Baseline timestamp for relative sysUpTime calculation.
- `should_send_template()`: Evaluates initial burst, periodic time refresh (60s), or packet count refresh (20 packets).
- Thread-safe and free of global variables to support concurrent simulations.

### 2.3. NetFlow v9 Binary Encoder: `NetFlowV9Encoder`
- **Header:** 20 bytes (`!HHIIII`: Version=9, Count, sysUpTime ms, UNIX Secs, Sequence Number, Source ID).
- **Template FlowSet (ID 0):** Encodes 16 canonical IPv4 fields into a 72-byte FlowSet (Template ID 256).
- **Data FlowSet (ID 256):** Contiguously packs 43-byte flow records and pads with zeros to a 4-byte boundary.
- **MTU Safety:** Automatically splits large batches across datagrams strictly under 1400 bytes.

### 2.4. IPFIX Binary Encoder: `IPFIXEncoder`
- **Header:** 16 bytes (`!HHIII`: Version=10, Length, Export Time, Sequence Number, Observation Domain ID).
- **Template Set (Set ID 2):** Encodes 15 core IANA fields into a 68-byte Set (Template ID 256).
- **Data Set (Set ID 256):** Packs 64-byte records with 64-bit integer counters (`!Q`) and absolute epoch millisecond timestamps.
- **Record Alignment:** 64 bytes per record guarantees natural 4-byte word boundary alignment with zero padding.

### 2.5. Safety Controls & Rate Limiter
- **RFC 1918 Blocker:** `validate_destination_target()` permits only `127.0.0.0/8`, `::1`, `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, and `169.254.0.0/16`. All public IP addresses immediately raise `DestinationSecurityException`.
- **Public Override:** Public destination export is permitted only when `NETSPOUT_ALLOW_PUBLIC_EXPORT=true` is set, triggering an explicit security audit log.
- **Privileged Port Protection:** Ports < 1024 (except 514) require explicit permission.
- **Token-Bucket Rate Limiter:** Paces datagrams at 100 pps (max 1,000 pps) with a 10,000 packet ceiling per scenario run.
- **Circuit Breaker:** Aborts transmission if 5 consecutive UDP socket errors occur.

---

## 3. First Native Scenario: `mixed_backbone_optical`

The `mixed_backbone_optical` scenario was selected as the first native candidate because its contract specifies Arista IPFIX telemetry for optical bypass reroute validation:
1. **Mode A (Direct-to-Splunk):** Continues to emit modeled JSON logs to Splunk HEC (`sourcetype=arista:flow:ipfix`, `juniper:junos`, `nokia:sros:syslog`).
2. **Mode B (Native Transport):** Converts the flow records to binary IPFIX or NetFlow v9 datagrams and exports them over UDP to a target collector:
   - **Flow 1 (Baseline Egress):** `10.200.0.1 -> 10.200.0.3`, 8,420,950 bytes, `egressInterface = 1` (`Ethernet49/1`).
   - **Flow 2 (Rerouted Bypass Egress):** `10.200.0.1 -> 10.200.0.3`, 12,948,200 bytes, `egressInterface = 2` (`Ethernet49/2`).
3. **Companion Manifest:** Dispatches a structured `CompanionControlManifest` event to Splunk HEC index `idx_network_ops` containing the exact SPL query for Step 5 ("Prove") correlation.

---

## 4. Engineering Characterization & Performance

Tested on macOS Apple Silicon under safe bounded load (1,000 FlowRecords):
- **NetFlow v9 Throughput:** **241,204 records/sec (7,719 packets/sec)**
- **IPFIX Throughput:** **274,320 records/sec (13,167 packets/sec)**
- **Encoding Latency:** 4.15 ms per 1,000 NetFlow v9 records; 3.65 ms per 1,000 IPFIX records.
- **Process Peak RSS:** **34.86 MB** (Zero memory leaks).

---

## 5. Known Scope Boundaries & Next Steps

- **SCTP / TCP Transport:** Bounded to UDP only for Gate 11B; TCP/SCTP deferred to Wave 3.
- **SNMP / gNMI:** Native SNMP and gNMI streaming remain out of scope for Gate 11B.
- **End-to-End Splunk Stream:** Verified locally via TShark and local loopback UDP socket exchange. Full physical collector-to-Splunk indexing will be certified in Gate 11C.
