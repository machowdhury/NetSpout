# NETSPOUT IPFIX PROTOCOL SPECIFICATION

**Gate:** NetSpout Gate 11 (Native Transport Architecture & NetFlow/IPFIX Protocol Definition)  
**Status:** SPECIFICATION COMPLETE (FOR GATE 11B IMPLEMENTATION)  
**Author:** Mahamudul Chowdhury (`machowdhury@yahoo.com`)  
**Repository:** [https://github.com/machowdhury/NetSpout](https://github.com/machowdhury/NetSpout)  
**Reference Standards:** IETF RFC 7011 (IPFIX Protocol Specification) & IETF RFC 7012 (Information Model for IPFIX)  

---

## 1. Scope & Objective

This document defines the wire-level protocol specification for the NetSpout IPFIX (Internet Protocol Flow Information Export) binary packet encoder. IPFIX is the IETF open standard evolution of Cisco NetFlow v9. NetSpout uses this specification to export high-fidelity flow telemetry over UDP (port 4739 standard, or configurable) to modern telemetry collectors such as Splunk Stream, ElastiFlow, Kentik, PMACCT, and Arista CloudVision Flow Trackers.

### Architectural Guarantees
1. **RFC 7011 / RFC 7012 Strict Compliance:** All messages conform to the 16-byte IPFIX message header, Set framing, IANA Information Element registry, and Enterprise-Specific extension rules.
2. **Standard & Enterprise Field Flexibility:** Supports standard 4-byte IANA field specifiers as well as 8-byte Enterprise-Specific field specifiers with Private Enterprise Numbers (PEN).
3. **Variable-Length Field Support:** Conforms to RFC 7011 Section 7 for optional variable-length string encoding (used for metadata and scenario correlation).
4. **Pure Standard Library Implementation:** Zero binary C/C++ or third-party packet dependencies; encoded strictly via Python's standard `struct` module in network byte order (`!`).
5. **AppInspect Boundary:** Isolated within the NetSpout backend service runtime; zero socket code in the Splunk App bundle.

---

## 2. IPFIX Message Header Structure

Every IPFIX export datagram begins with a 16-byte message header formatted according to RFC 7011 Section 3.1.

### 2.1. Header Format Diagram

```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|          Version (10)         |            Length             |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                          Export Time                          |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                        Sequence Number                        |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                     Observation Domain ID                     |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

### 2.2. Field Definitions & Semantics

| Offset (Bytes) | Field Name | Type / Length | NetSpout Value / Semantics | RFC 7011 Requirement |
| :--- | :--- | :--- | :--- | :--- |
| **0 – 1** | `Version` | `uint16` (2B) | `0x000A` (constant decimal 10) | Must be 10 (`0x000A`) |
| **2 – 3** | `Length` | `uint16` (2B) | Total length of the entire IPFIX Message in bytes, **including the 16-byte header**. | Total octets in IPFIX message |
| **4 – 7** | `Export Time` | `uint32` (4B) | Current simulated epoch timestamp in whole seconds: `int(sim_time)` | Seconds since 00:00 UTC 1 Jan 1970 (UNIX epoch) |
| **8 – 11** | `Sequence Number` | `uint32` (4B) | Cumulative count of all **Data Records** previously sent by this Observation Domain over this session. | Incremental sequence number of Data Records (does not count Template records) |
| **12 – 15** | `Observation Domain ID` | `uint32` (4B) | Exporter Observation Domain identifier (e.g. `101`, `0x00000065`). Maps to simulated device routing engine. | Scopes template management and sequence numbering. |

### 2.3. Key Semantic Distinction: IPFIX vs NetFlow v9 Headers
1. **Length vs Count:** In NetFlow v9, bytes 2–3 indicate the record `Count`. In IPFIX, bytes 2–3 indicate the total message `Length` in octets.
2. **sysUpTime Eliminated:** IPFIX header removes `sysUpTime`. Exact timestamps are carried natively inside individual records as absolute epoch milliseconds (e.g., `flowStartMilliseconds`, `flowEndMilliseconds`).
3. **Sequence Number:** In IPFIX, the sequence number tracks the total number of **Data Records** transmitted, strictly excluding Template Records.

### 2.4. Python `struct` Format String
```python
IPFIX_HEADER_FORMAT = "!HHIII"  # 16 bytes: uint16, uint16, uint32, uint32, uint32
```

---

## 3. Set Architecture & Framing

Following the 16-byte message header, an IPFIX Message contains one or more Sets. Each Set starts with a 4-byte Set Header:

```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|            Set ID             |            Length             |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                           Set Body                            |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

| Set Type | Set ID Value | Description |
| :--- | :--- | :--- |
| **Template Set** | `2` (`0x0002`) | Defines the structure of data records (Set ID 0 and 1 are reserved in IPFIX). |
| **Options Template Set** | `3` (`0x0003`) | Defines metadata records (exporter process info, interface details). |
| **Data Set** | `256 – 65535` | Contains raw binary records conforming to Template ID `== Set ID`. |

### 3.1. 4-Byte Word Alignment Rule (Padding)
RFC 7011 Section 3.3.1 states:
> *"The Set Length is the total length of the Set in bytes, including the Set Header and all records, plus any padding octets."*
> *"All Sets SHOULD be aligned to 4-byte boundaries."*

If the payload of a Set is not a multiple of 4 bytes:
1. `padding_len = (4 - (len(body) % 4)) % 4`
2. Zero octets (`b'\x00' * padding_len`) are appended to the Set.
3. `Set Length = 4 + len(body) + padding_len`.

---

## 4. Template Set Specification (Set ID = 2)

A Template Set informs the collector how to parse subsequent Data Records.

### 4.1. Template Set Layout

```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|          Set ID = 2           |            Length             |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|          Template ID          |          Field Count          |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|E|     Information Element 1   |         Field Length 1        |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|         [Enterprise Number 1 (only present if E == 1)]         |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|E|     Information Element 2   |         Field Length 2        |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                             ...                               |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                          Padding (0-3 bytes)                  |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

### 4.2. Field Specifier Types
Each field definition consists of:
1. **Standard IANA Field (4 bytes):**
   - Bit 0 (Enterprise bit `E`) = `0`
   - Bits 1–15: IANA Information Element ID (1–32767)
   - Bits 16–31: Field Length in octets
2. **Enterprise-Specific Field (8 bytes):**
   - Bit 0 (Enterprise bit `E`) = `1` (`id | 0x8000`)
   - Bits 1–15: Enterprise Information Element ID
   - Bits 16–31: Field Length in octets (or `0xFFFF` for variable length)
   - Bits 32–63: 32-bit Private Enterprise Number (PEN)

---

## 5. NetSpout Canonical IPFIX Templates

### 5.1. Standard Core Flow Template (Template ID 256)
Designed for 100% interoperability with Splunk Stream, ElastiFlow, and Cisco collectors without custom enterprise definitions:

| Field Index | Field Name | IANA IE ID | Length (Bytes) | Format | Description |
| :---: | :--- | :---: | :---: | :---: | :--- |
| 1 | `sourceIPv4Address` | 8 | 4 | `!4s` | IPv4 source address |
| 2 | `destinationIPv4Address`| 12 | 4 | `!4s` | IPv4 destination address |
| 3 | `sourceTransportPort` | 7 | 2 | `!H` | Layer 4 source port |
| 4 | `destinationTransportPort`| 11 | 2 | `!H` | Layer 4 destination port |
| 5 | `protocolIdentifier` | 4 | 1 | `!B` | IP protocol number (6=TCP, 17=UDP) |
| 6 | `ipClassOfService` | 5 | 1 | `!B` | DSCP / ToS byte |
| 7 | `tcpControlBits` | 6 | 2 | `!H` | TCP flags (**2 octets** in RFC 7012) |
| 8 | `ingressInterface` | 10 | 4 | `!I` | Ingress ifIndex (32-bit) |
| 9 | `egressInterface` | 14 | 4 | `!I` | Egress ifIndex (32-bit) |
| 10 | `packetDeltaCount` | 2 | 8 | `!Q` | Cumulative packets (64-bit uint) |
| 11 | `octetDeltaCount` | 1 | 8 | `!Q` | Cumulative bytes (64-bit uint) |
| 12 | `flowStartMilliseconds` | 152 | 8 | `!Q` | Flow start timestamp in epoch ms |
| 13 | `flowEndMilliseconds` | 153 | 8 | `!Q` | Flow end timestamp in epoch ms |
| 14 | `bgpSourceAsNumber` | 16 | 4 | `!I` | Origin BGP AS number (32-bit) |
| 15 | `bgpDestinationAsNumber`| 17 | 4 | `!I` | Destination BGP AS number (32-bit) |

**Total Record Length for Template 256:** `4+4+2+2+1+1+2+4+4+8+8+8+8+4+4` = **64 bytes** per flow record.  
*64 is evenly divisible by 4, guaranteeing perfect word alignment across all record counts!*

### 5.2. Extended Enterprise Flow Template (Template ID 257)
Template 257 includes all 15 core fields plus NetSpout Enterprise Information Elements for direct scenario correlation:
- **NetSpout Private Enterprise Number (PEN):** `59999` (Configurable via `NETSPOUT_ENTERPRISE_PEN`).
- **Enterprise IE 1 (`0x8001`):** `netspoutScenarioId` (uint32 canonical scenario hash).
- **Enterprise IE 2 (`0x8002`):** `netspoutAnomalyCode` (uint16 anomaly flag: 0=normal, 1=syn_flood, 2=route_leak, 3=packet_drop).
- **Enterprise IE 3 (`0x8003`):** `netspoutSimulationPhase` (uint8 phase: 1=baseline, 2=fault, 3=recovery).

---

## 6. Variable-Length Information Element Encoding

For collectors configured to accept descriptive string tags (e.g. scenario name or tenant identifier), NetSpout supports RFC 7011 Section 7 variable-length encoding:

1. **Template Specification:** The `Field Length` in the Template Field Specifier is set to `65535` (`0xFFFF`).
2. **Data Record Encoding:**
   - If string length `< 255`: 1 octet length prefix followed by raw UTF-8 string bytes.
   - If string length `>= 255`: `0xFF` octet followed by 2 octets length (`!H`) followed by raw bytes.

---

## 7. MTU, Batch Sizing & Wire Transport Constraints

To ensure zero IP fragmentation over Ethernet networks:
- `MAX_PAYLOAD_BYTES = 1400`
- `IPFIX_HEADER_BYTES = 16`
- `SET_HEADER_BYTES = 4`
- Available record capacity: `1400 - 16 - 4 = 1380 bytes`.
- At 64 bytes/record, maximum flow records per datagram = `floor(1380 / 64) = 21 records`.
- `21 records * 64 bytes = 1344 bytes`.
- `Set Length = 4 + 1344 = 1348 bytes` (divisible by 4, padding = 0).
- `Total Message Length = 16 + 1348 = 1364 bytes` (leaves 136 bytes headroom under 1500 MTU).

---

## 8. Concrete Hex Fixture: Verification Golden Datagram

Below is an exact, byte-by-byte hex fixture of a valid IPFIX datagram containing 1 Template Set (Template ID 256, 15 fields) and 1 Data Set with 1 record.

### 8.1. Packet Metadata
- **Version:** 10 (`0x000A`)
- **Length:** 152 bytes (`0x0098`)
- **Export Time:** 1774438400 (2026-03-25T16:00:00Z) (`0x69C3E400`)
- **Sequence Number:** 1 (`0x00000001`)
- **Observation Domain ID:** 101 (`0x00000065`)

### 8.2. Annotated Hex Dump

```hex
# --- IPFIX Message Header (16 bytes) ---
00 0a                   # Version = 10 (IPFIX)
00 98                   # Length = 152 bytes total
69 c3 e4 00             # Export Time = 1774438400
00 00 00 01             # Sequence Number = 1 (1 Data Record)
00 00 00 65             # Observation Domain ID = 101

# --- Set 1: Template Set (Set ID = 2, Length = 68 bytes) ---
00 02                   # Set ID = 2 (Template)
00 44                   # Length = 68 bytes (4 header + 4 template header + 15*4 fields = 68 bytes)
01 00                   # Template ID = 256
00 0f                   # Field Count = 15
00 08 00 04             # IE 8 (sourceIPv4Address), Len 4
00 0c 00 04             # IE 12 (destinationIPv4Address), Len 4
00 07 00 02             # IE 7 (sourceTransportPort), Len 2
00 0b 00 02             # IE 11 (destinationTransportPort), Len 2
00 04 00 01             # IE 4 (protocolIdentifier), Len 1
00 05 00 01             # IE 5 (ipClassOfService), Len 1
00 06 00 02             # IE 6 (tcpControlBits), Len 2
00 0a 00 04             # IE 10 (ingressInterface), Len 4
00 0e 00 04             # IE 14 (egressInterface), Len 4
00 02 00 08             # IE 2 (packetDeltaCount), Len 8
00 01 00 08             # IE 1 (octetDeltaCount), Len 8
00 98 00 08             # IE 152 (flowStartMilliseconds), Len 8 (0x0098 = 152)
00 99 00 08             # IE 153 (flowEndMilliseconds), Len 8 (0x0099 = 153)
00 10 00 04             # IE 16 (bgpSourceAsNumber), Len 4
00 11 00 04             # IE 17 (bgpDestinationAsNumber), Len 4

# --- Set 2: Data Set (Set ID = 256, Length = 68 bytes) ---
01 00                   # Set ID = 256 (matches Template 256)
00 44                   # Length = 68 bytes (4 header + 64 data record = 68 bytes)
# Data Record 1 (64 bytes):
0a 00 01 0a             # sourceIPv4Address = 10.0.1.10
0a 00 02 14             # destinationIPv4Address = 10.0.2.20
c0 01                   # sourceTransportPort = 49153
01 bb                   # destinationTransportPort = 443 (HTTPS)
06                      # protocolIdentifier = 6 (TCP)
00                      # ipClassOfService = 0
00 18                   # tcpControlBits = 0x0018 (ACK + PSH, 2 bytes)
00 00 00 03             # ingressInterface = 3
00 00 00 05             # egressInterface = 5
00 00 00 00 00 00 04 00 # packetDeltaCount = 1,024 packets (uint64)
00 00 00 00 00 08 00 00 # octetDeltaCount = 524,288 bytes (uint64)
00 00 01 9d 4a e8 48 00 # flowStartMilliseconds = 1774438400000 ms
00 00 01 9d 4a e9 0f 40 # flowEndMilliseconds = 1774438451000 ms
00 00 ff ff             # bgpSourceAsNumber = 65535 (32-bit AS)
00 00 f0 00             # bgpDestinationAsNumber = 61440 (32-bit AS)
```

---

## 9. Gate 11 Compliance Checklist

- [x] RFC 7011 Section 3.1 message header format specified (16 bytes).
- [x] Template Set (ID 2) and Data Set (ID >= 256) structures defined.
- [x] Distinction between NetFlow v9 Count and IPFIX Length documented.
- [x] Standard 4-byte IANA vs 8-byte Enterprise-Specific field specifiers detailed.
- [x] 64-bit counters (`octetDeltaCount`, `packetDeltaCount`) and epoch millisecond timestamps defined.
- [x] RFC 7011 Section 7 variable-length string encoding defined.
- [x] MTU bounds, 64-byte record alignment, and batch calculations documented.
- [x] Annotated binary hex fixture provided for automated unit testing in Gate 11B.
