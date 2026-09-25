# NETSPOUT NETFLOW V9 PROTOCOL SPECIFICATION

**Gate:** NetSpout Gate 11 (Native Transport Architecture & NetFlow/IPFIX Protocol Definition)  
**Status:** SPECIFICATION COMPLETE (FOR GATE 11B IMPLEMENTATION)  
**Author:** Mahamudul Chowdhury (`machowdhury@yahoo.com`)  
**Repository:** [https://github.com/machowdhury/NetSpout](https://github.com/machowdhury/NetSpout)  
**Reference Standard:** IETF RFC 3954 (Cisco Systems NetFlow Services Export Version 9)  

---

## 1. Scope & Objective

This document defines the wire-level protocol specification for the NetSpout NetFlow Version 9 binary packet encoder. NetSpout uses this specification to export high-fidelity flow telemetry over UDP (typically port 2055 or 9995) to commercial, open-source, and enterprise flow collectors—including Splunk Stream, ElastiFlow, nProbe, and Cisco Secure Network Analytics (Stealthwatch).

### Architectural Guarantees
1. **RFC 3954 Strict Compliance:** Every datagram produced conforms to the 16-byte packet header, FlowSet framing, and 4-byte word boundary padding rules of RFC 3954.
2. **Pure Standard Library Implementation:** Zero external binary dependencies. Encoding is performed using Python's standard `struct` module in big-endian network byte order (`!`).
3. **Decoupled Telemetry Mapping:** NetSpout `FlowRecord` objects are mapped deterministically to NetFlow v9 field types without corrupting or overloading RFC-standard fields with non-standard strings.
4. **AppInspect Safety:** The packet encoder is a pure byte-manipulation engine. Socket dispatch is isolated in the NetSpout backend runner and excluded from the core Splunk App package (`netspout.spl`).

---

## 2. NetFlow Version 9 Packet Header Structure

Every NetFlow v9 export datagram begins with a 16-byte header formatted according to RFC 3954 Section 5.1.

### 2.1. Header Format Diagram

```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|          Version (9)          |             Count             |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                         sysUpTime (ms)                        |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                       UNIX Seconds (epoch)                    |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                        Sequence Number                        |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                     Source ID (Engine ID)                     |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

### 2.2. Field Definitions & Semantics

| Offset (Bytes) | Field Name | Type / Length | NetSpout Value / Semantics | RFC 3954 Rule |
| :--- | :--- | :--- | :--- | :--- |
| **0 – 1** | `Version` | `uint16` (2B) | `0x0009` (constant decimal 9) | Must be 9 |
| **2 – 3** | `Count` | `uint16` (2B) | Total number of records (Templates + Data Records) in this export packet | Sum of all records contained in all FlowSets in this packet |
| **4 – 7** | `sysUpTime` | `uint32` (4B) | Milliseconds elapsed since simulated exporter device boot: `int((sim_time - boot_time) * 1000)` | Used by collector to resolve first/last switched timestamps |
| **8 – 11** | `UNIX Secs` | `uint32` (4B) | Current simulated epoch timestamp in whole seconds: `int(sim_time)` | Collector absolute wall-clock reference |
| **12 – 15** | `Sequence Number` | `uint32` (4B) | Incremental cumulative sequence counter of all **Flow Records** previously exported by this source engine | In RFC 3954, sequence number tracks *flow records*, not packet count. (Enables collector packet-loss detection). |
| **16 – 19** | `Source ID` | `uint32` (4B) | Exporter Observation Domain identifier. By default, maps to the low 32 bits of the exporter IPv4 or hash of device name. | Uniquely scopes template IDs for the collector. |

### 2.3. Python `struct` Format String
```python
NETFLOW_V9_HEADER_FORMAT = "!HHIIII"  # 16 bytes: uint16, uint16, uint32, uint32, uint32, uint32
```

---

## 3. FlowSet Architecture & Framing

Following the 16-byte header, a NetFlow v9 packet contains one or more FlowSets. Each FlowSet starts with a 4-byte header:

```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|          FlowSet ID           |            Length             |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                         FlowSet Body                          |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

| FlowSet Type | FlowSet ID Value | Description |
| :--- | :--- | :--- |
| **Template FlowSet** | `0` (`0x0000`) | Defines the schema (fields, lengths) of subsequent data records. |
| **Options Template FlowSet** | `1` (`0x0001`) | Defines metadata schemas (e.g. sampling rates, interface mappings). |
| **Data FlowSet** | `256 – 65535` | Contains raw binary data records conforming to the designated Template ID. |

### 3.1. 4-Byte Word Alignment Rule (Padding)
RFC 3954 Section 5.2 states:
> *"The FlowSet Length is the total length of the FlowSet in bytes, including the FlowSet ID, Length, and all records, plus any padding bytes."*
> *"All FlowSets MUST be aligned to 4-byte (32-bit) word boundaries."*

If the payload of a FlowSet is not a multiple of 4 bytes:
1. `padding_len = (4 - (len(body) % 4)) % 4`
2. Zero bytes (`b'\x00' * padding_len`) are appended to the FlowSet.
3. `FlowSet Length = 4 + len(body) + padding_len`.

---

## 4. Template FlowSet Specification (FlowSet ID = 0)

Before a collector can decode binary flow data, it must have received the corresponding Template definition.

### 4.1. Template FlowSet Layout

```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|       FlowSet ID = 0          |            Length             |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|          Template ID          |          Field Count          |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|        Field Type 1           |         Field Length 1        |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|        Field Type 2           |         Field Length 2        |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                             ...                               |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                          Padding (0-3 bytes)                  |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

- **Template ID:** An integer between `256` and `65535`. (NetSpout defaults: Template ID `256` for IPv4 Basic Flow, `257` for IPv4 Extended Flow, `258` for IPv6 Flow).
- **Field Count:** Number of fields defined in this template.
- **Field Specifier:** 4 bytes per field: `Field Type` (uint16) and `Field Length` (uint16).

### 4.2. NetSpout Canonical IPv4 Flow Template (Template ID 256)
NetSpout defines a standard, highly compatible IPv4 Flow Template containing the core 16 fields recognized by all industry collectors:

| Field Index | Field Name | RFC 3954 Type ID | Length (Bytes) | Python `struct` Format | Description |
| :---: | :--- | :---: | :---: | :---: | :--- |
| 1 | `IPV4_SRC_ADDR` | 8 | 4 | `!4s` | Source IPv4 address (packed bytes) |
| 2 | `IPV4_DST_ADDR` | 12 | 4 | `!4s` | Destination IPv4 address (packed bytes) |
| 3 | `BGP_IPV4_NEXT_HOP`| 18 | 4 | `!4s` | Next hop IPv4 address |
| 4 | `INPUT_SNMP` | 10 | 2 | `!H` | Ingress interface index |
| 5 | `OUTPUT_SNMP` | 14 | 2 | `!H` | Egress interface index |
| 6 | `IN_PKTS` | 2 | 4 | `!I` | Cumulative packet delta count |
| 7 | `IN_BYTES` | 1 | 4 | `!I` | Cumulative byte delta count |
| 8 | `FIRST_SWITCHED` | 22 | 4 | `!I` | sysUpTime when first packet was seen (ms) |
| 9 | `LAST_SWITCHED` | 21 | 4 | `!I` | sysUpTime when last packet was seen (ms) |
| 10 | `L4_SRC_PORT` | 7 | 2 | `!H` | Layer 4 source port |
| 11 | `L4_DST_PORT` | 11 | 2 | `!H` | Layer 4 destination port |
| 12 | `TCP_FLAGS` | 6 | 1 | `!B` | Cumulative TCP flags (SYN, ACK, etc.) |
| 13 | `PROTOCOL` | 4 | 1 | `!B` | IP protocol number (6=TCP, 17=UDP, 1=ICMP) |
| 14 | `SRC_TOS` | 5 | 1 | `!B` | Type of Service / DSCP |
| 15 | `SRC_AS` | 16 | 2 | `!H` | Origin BGP AS number |
| 16 | `DST_AS` | 17 | 2 | `!H` | Destination BGP AS number |

**Total Record Length for Template 256:** `4 + 4 + 4 + 2 + 2 + 4 + 4 + 4 + 4 + 2 + 2 + 1 + 1 + 1 + 2 + 2` = **43 bytes** per flow record.  
*Note on record padding:* Flow records themselves do not need individual 4-byte padding; however, the enclosing **Data FlowSet** must be padded to a 4-byte boundary.

---

## 5. Data FlowSet Specification (FlowSet ID >= 256)

A Data FlowSet carries actual flow measurements packed contiguously according to the field sequence of the template.

### 5.1. Data FlowSet Layout

```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|     FlowSet ID = Template ID  |            Length             |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                         Record 1 ...                          |
|                                                               |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                         Record 2 ...                          |
|                                                               |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                          Padding (0-3 bytes)                  |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

### 5.2. Packing Calculation & Batch Sizing
To prevent UDP fragmentation across standard Ethernet networks (MTU 1500 bytes, IP header 20 bytes, UDP header 8 bytes = maximum 1472 bytes payload):
- `MAX_PAYLOAD_BYTES = 1400` (safe conservative MTU margin)
- `HEADER_BYTES = 16`
- `FLOWSET_HEADER_BYTES = 4`
- Available record capacity: `1400 - 16 - 4 = 1380 bytes`.
- At 43 bytes/record, maximum flow records per datagram = `floor(1380 / 43) = 32 records`.
- `32 records * 43 bytes = 1376 bytes`.
- `1376` is divisible by 4 (`1376 % 4 == 0`), requiring **0 bytes of padding**.
- `FlowSet Length = 4 + 1376 = 1380 bytes`.
- `Total UDP Datagram Size = 16 + 1380 = 1396 bytes` (well within standard MTU).

---

## 6. Options Template FlowSet Specification (FlowSet ID = 1)

Options Templates export metadata about the NetFlow process itself, such as the sampling rate and exporter scope.

### 6.1. Options Template Layout
```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|       FlowSet ID = 1          |            Length             |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|          Template ID          |       Scope Length (bytes)    |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|     Option Length (bytes)     |        Scope Field 1 Type     |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|      Scope Field 1 Length     |       Option Field 1 Type     |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|      Option Field 1 Length    |             ...               |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

NetSpout emits Options Templates for scenarios involving sampled NetFlow (e.g., 1-out-of-1000 packet sampling), binding `SAMPLING_INTERVAL` (Type 34) and `SAMPLING_ALGORITHM` (Type 35) to the `METERING_PROCESS_ID`.

---

## 7. Operational Dynamics & Template Refresh Policy

NetFlow v9 runs over UDP, an unreliable transport protocol. If a collector reboots or packet loss occurs, the collector loses the template definitions and cannot decode incoming flow records.

### 7.1. Refresh Rules
1. **Initial Burst:** Upon starting a scenario run in Mode B, NetSpout MUST transmit a Template FlowSet in the very first datagram before or alongside the first data batch.
2. **Time-Based Refresh:** NetSpout retransmits active templates at least once every **60 seconds** (configurable via `NETSPOUT_FLOW_TEMPLATE_REFRESH_SEC`).
3. **Packet-Count Refresh:** NetSpout retransmits active templates every **20 datagrams** (configurable via `NETSPOUT_FLOW_TEMPLATE_REFRESH_PACKETS`).
4. **Co-Packaging:** Whenever a template refresh is due, the Template FlowSet (ID 0) and the Data FlowSet (ID 256) MAY be combined into the same UDP packet, provided the combined length remains `<= 1400 bytes`.

---

## 8. Concrete Hex Fixture: Verification Golden Datagram

Below is an exact, byte-by-byte hex fixture of a valid NetFlow v9 datagram containing 1 Template FlowSet (Template ID 256, 16 fields) and 1 Data FlowSet with 1 record.

### 8.1. Packet Metadata
- **Version:** 9 (`0x0009`)
- **Count:** 2 records (1 Template + 1 Data Record) (`0x0002`)
- **sysUpTime:** 125,000 ms (`0x0001E848`)
- **UNIX Secs:** 1774438400 (2026-03-25T16:00:00Z) (`0x69C3E400`)
- **Sequence Number:** 1 (`0x00000001`)
- **Source ID:** 101 (`0x00000065`)

### 8.2. Annotated Hex Dump

```hex
# --- NetFlow v9 Packet Header (16 bytes) ---
00 09                   # Version = 9
00 02                   # Count = 2 records
00 01 e8 48             # sysUpTime = 125,000 ms
69 c3 e4 00             # UNIX Secs = 1774438400
00 00 00 01             # Sequence Number = 1
00 00 00 65             # Source ID = 101

# --- FlowSet 1: Template FlowSet (FlowSet ID = 0, Length = 72 bytes) ---
00 00                   # FlowSet ID = 0 (Template)
00 48                   # Length = 72 bytes (4 header + 4 template header + 16*4 fields = 72 bytes, 0 padding)
01 00                   # Template ID = 256
00 10                   # Field Count = 16
00 08 00 04             # Type 8 (IPV4_SRC_ADDR), Len 4
00 0c 00 04             # Type 12 (IPV4_DST_ADDR), Len 4
00 12 00 04             # Type 18 (BGP_IPV4_NEXT_HOP), Len 4
00 0a 00 02             # Type 10 (INPUT_SNMP), Len 2
00 0e 00 02             # Type 14 (OUTPUT_SNMP), Len 2
00 02 00 04             # Type 2 (IN_PKTS), Len 4
00 01 00 04             # Type 1 (IN_BYTES), Len 4
00 16 00 04             # Type 22 (FIRST_SWITCHED), Len 4
00 15 00 04             # Type 21 (LAST_SWITCHED), Len 4
00 07 00 02             # Type 7 (L4_SRC_PORT), Len 2
00 0b 00 02             # Type 11 (L4_DST_PORT), Len 2
00 06 00 01             # Type 6 (TCP_FLAGS), Len 1
00 04 00 01             # Type 4 (PROTOCOL), Len 1
00 05 00 01             # Type 5 (SRC_TOS), Len 1
00 10 00 02             # Type 16 (SRC_AS), Len 2
00 11 00 02             # Type 17 (DST_AS), Len 2

# --- FlowSet 2: Data FlowSet (FlowSet ID = 256, Length = 48 bytes) ---
01 00                   # FlowSet ID = 256 (matches Template 256)
00 30                   # Length = 48 bytes (4 header + 43 data record + 1 pad byte = 48 bytes)
# Data Record 1 (43 bytes):
0a 00 01 0a             # IPV4_SRC_ADDR = 10.0.1.10
0a 00 02 14             # IPV4_DST_ADDR = 10.0.2.20
0a 00 01 01             # BGP_IPV4_NEXT_HOP = 10.0.1.1
00 03                   # INPUT_SNMP = 3 (GigabitEthernet0/1)
00 05                   # OUTPUT_SNMP = 5 (GigabitEthernet0/3)
00 00 04 00             # IN_PKTS = 1,024 packets
00 08 00 00             # IN_BYTES = 524,288 bytes
00 01 d4 c0             # FIRST_SWITCHED = 120,000 ms
00 01 e8 48             # LAST_SWITCHED = 125,000 ms
c0 01                   # L4_SRC_PORT = 49153
01 bb                   # L4_DST_PORT = 443 (HTTPS)
18                      # TCP_FLAGS = 0x18 (ACK + PSH)
06                      # PROTOCOL = 6 (TCP)
00                      # SRC_TOS = 0
ff ff                   # SRC_AS = 65535 (Private AS)
f0 00                   # DST_AS = 61440
00                      # Padding byte = 0x00 (aligns 47 bytes to 48 bytes)
```

---

## 9. Gate 11 Compliance Checklist

- [x] RFC 3954 Section 5.1 header format specified (16 bytes).
- [x] Template FlowSet (ID 0) and Data FlowSet (ID >= 256) structures defined.
- [x] 4-byte boundary padding rules strictly enforced.
- [x] Sequence numbering semantics defined (counts flow records, not packets).
- [x] Standard field catalog mapped to Python `struct` format strings.
- [x] MTU bounds and record batch calculations documented.
- [x] Annotated binary hex fixture provided for automated unit testing in Gate 11B.
