# NetSpout SNMPv2c Wire Protocol & ASN.1 BER Specification

**Author:** Mahamudul Chowdhury (`machowdhury@yahoo.com`)  
**Gate:** 12 (Native SNMP Architecture & Protocol Definition)  
**Standards Reference:** `ITU-T X.690` (ASN.1 BER), `RFC 2578` (SMIv2), `RFC 3416` (SNMPv2 Protocol Operations), `RFC 3418` (MIB for SNMP)

---

## 1. ASN.1 Basic Encoding Rules (BER) Wire Specification (Section 8)

All SNMP protocol messages are encoded using **ASN.1 Basic Encoding Rules (BER)** with **Definite-Length encoding only** (`RFC 3416 Section 8`). Every element on the wire is a recursive **TLV (`Tag` – `Length` – `Value`)** tuple:

```text
+-------------------+------------------------+-----------------------------------+
| Tag (1+ octets)   | Length (1..3 octets)   | Value (0..Length octets)          |
+-------------------+------------------------+-----------------------------------+
```

### 1.1 Canonical ASN.1 BER Tag Table for SNMPv2c

| ASN.1 / SMIv2 Type | Tag Hex | Tag Binary (`Class|P/C|Number`) | Class & Structure | Wire Value Representation |
| :--- | :---: | :---: | :--- | :--- |
| `SEQUENCE` / `SEQUENCE OF` | `0x30` | `00 1 10000` | Universal, Constructed | Concatenated child TLVs (Message, PDU VarBindList, VarBind) |
| `INTEGER` (`Integer32`) | `0x02` | `00 0 00010` | Universal, Primitive | Signed big-endian two's complement minimal octets (`-2147483648..2147483647`) |
| `OCTET STRING` | `0x04` | `00 0 00100` | Universal, Primitive | Raw byte sequence (UTF-8/ASCII string or binary octets) |
| `NULL` | `0x05` | `00 0 00101` | Universal, Primitive | Empty value (`Length = 0x00`); used in `GET`/`GETNEXT`/`GETBULK` request varbinds |
| `OBJECT IDENTIFIER` | `0x06` | `00 0 00110` | Universal, Primitive | Compressed first two sub-identifiers ($40X + Y$) followed by base-128 VLQ |
| `IpAddress` | `0x40` | `01 0 00000` | Application 0, Primitive | Exactly 4 octets in IPv4 network byte order (e.g., `10.0.1.1` $\rightarrow$ `0a 00 01 01`) |
| `Counter32` | `0x41` | `01 0 00001` | Application 1, Primitive | Unsigned 32-bit (`0..4294967295`); prepends `0x00` if MSB bit 7 is `1` |
| `Gauge32` / `Unsigned32` | `0x42` | `01 0 00010` | Application 2, Primitive | Unsigned 32-bit (`0..4294967295`); prepends `0x00` if MSB bit 7 is `1` |
| `TimeTicks` | `0x43` | `01 0 00011` | Application 3, Primitive | Unsigned 32-bit centiseconds (`0..4294967295`); prepends `0x00` if MSB bit 7 is `1` |
| `Opaque` | `0x44` | `01 0 00100` | Application 4, Primitive | Arbitrary BER-wrapped octet sequence |
| `Counter64` | `0x46` | `01 0 00110` | Application 6, Primitive | Unsigned 64-bit (`0..2^64-1`); prepends `0x00` if MSB bit 7 is `1` (`1..9` octets) |
| `noSuchObject` | `0x80` | `10 0 00000` | Context 0, Primitive | Exception value in `Response-PDU` (`Length = 0x00`) |
| `noSuchInstance` | `0x81` | `10 0 00001` | Context 1, Primitive | Exception value in `Response-PDU` (`Length = 0x00`) |
| `endOfMibView` | `0x82` | `10 0 00010` | Context 2, Primitive | Exception value in `Response-PDU` (`Length = 0x00`) |

### 1.2 PDU Context-Specific Constructed Tags

| PDU Name | Tag Hex | Tag Binary | Direction | Description |
| :--- | :---: | :---: | :--- | :--- |
| `GetRequest-PDU` | `0xA0` | `10 1 00000` | Poller $\rightarrow$ Agent | Retrieve exact scalar/column instance values |
| `GetNextRequest-PDU` | `0xA1` | `10 1 00001` | Poller $\rightarrow$ Agent | Retrieve next lexicographical OID in MIB tree |
| `Response-PDU` | `0xA2` | `10 1 00010` | Agent/Receiver $\rightarrow$ Caller | Response to `GET`, `GETNEXT`, `GETBULK`, or `INFORM` |
| `SetRequest-PDU` | `0xA3` | `10 1 00011` | Manager $\rightarrow$ Agent | Rejected with `noAccess (6)` / `notWritable (17)` by NetSpout |
| `GetBulkRequest-PDU` | `0xA5` | `10 1 00101` | Poller $\rightarrow$ Agent | High-efficiency bulk table walk (`non-repeaters`, `max-repetitions`) |
| `InformRequest-PDU` | `0xA6` | `10 1 00110` | Agent/Manager $\rightarrow$ Receiver | Confirmed notification requiring `Response-PDU (0xA2)` |
| `SNMPv2-Trap-PDU` | `0xA7` | `10 1 00111` | Agent $\rightarrow$ Receiver | Unconfirmed asynchronous notification |
| `Report-PDU` | `0xA8` | `10 1 01000` | Engine $\rightarrow$ Engine | SNMPv3 USM engine/time discovery report |

---

## 2. BER Length & Value Encoding Rules (With Worked Examples)

### 2.1 BER Definite Length Encoding
Indefinite length (`0x80` followed by `0x00 0x00` EOC) is **strictly forbidden** by `RFC 3416`.
1. **Short Form (`0 <= L <= 127`):**
   - Encoded as a single byte containing $L$ directly (`0x00` through `0x7F`).
   - *Example:* Length $68\text{ bytes} \rightarrow \text{0x44}$.
2. **Long Form (`128 <= L <= 65535`):**
   - First byte has bit 7 set (`0x80`) ORed with the number of subsequent length bytes ($k \in \{1, 2\}$).
   - *Example 1 ($L = 180$):* $180 = \text{0xB4}$ fits in 1 unsigned byte $\rightarrow$ `0x81 0xB4`.
   - *Example 2 ($L = 512$):* $512 = \text{0x0200}$ requires 2 unsigned bytes $\rightarrow$ `0x82 0x02 0x00`.

### 2.2 Minimal Two's Complement Integer & Unsigned Counter Padding Rule
ITU-T X.690 Section 8.3 requires integers to be encoded in the **minimum number of octets** such that the leading 9 bits are not all `0` or all `1`:
- **Small Positive Integer (`1`):** `02 01 01`
- **Zero (`0`):** `02 01 00` (Length is always `1`, never `0`!)
- **Positive Value with MSB $\ge 0x80$ (`128`):** Because `0x80` alone would be interpreted as $-128$ in two's complement, a leading `0x00` pad byte is mandatory: `02 02 00 80`.
- **`TimeTicks` (`8,640,000` centiseconds = 24 hours = `0x0083D600`):**
  - Top byte of `83 D6 00` is `0x83` ($\ge \text{0x80}$), so a leading `0x00` byte is required:
  - Wire bytes: `43 04 00 83 d6 00` (Tag `0x43`, Length `4`, Value `00 83 d6 00`).
- **`Counter64` (`10,000,000,000` octets = `0x02540BE400`):**
  - Top byte is `0x02` ($< \text{0x80}$):
  - Wire bytes: `46 05 02 54 0b e4 00` (Tag `0x46`, Length `5`, Value `02 54 0b e4 00`).

### 2.3 `OBJECT IDENTIFIER` (`0x06`) Base-128 VLQ Encoding
Given an OID $a_1 . a_2 . a_3 \dots a_n$ (with $a_1 = 1, a_2 = 3$ for `iso.org`):
1. **First Octet:** Combines the first two arcs: $40 \times a_1 + a_2 = 40(1) + 3 = 43 = \text{0x2B}$.
2. **Subsequent Sub-Identifiers ($a_k$ for $k \ge 3$):**
   - If $a_k < 128$: single byte `a_k` (MSB bit 7 = `0`).
   - If $a_k \ge 128$: split $a_k$ into 7-bit groups from most-significant to least-significant; set bit 7 (`0x80`) on every byte **except the final byte**.
3. **Worked OID Examples:**
   - **`sysUpTime.0` (`1.3.6.1.2.1.1.3.0`):**
     - `1.3` $\rightarrow$ `2b`, followed by `06 01 02 01 01 03 00` (8 bytes)
     - Full TLV: `06 08 2b 06 01 02 01 01 03 00`
   - **`snmpTrapOID.0` (`1.3.6.1.6.3.1.1.4.1.0`):**
     - `1.3` $\rightarrow$ `2b`, followed by `06 01 06 03 01 01 04 01 00` (10 bytes)
     - Full TLV: `06 0a 2b 06 01 06 03 01 01 04 01 00`
   - **`linkDown` (`1.3.6.1.6.3.1.1.5.3`):**
     - Full TLV: `06 09 2b 06 01 06 03 01 01 05 03`
   - **Juniper Enterprise OID (`1.3.6.1.4.1.2636.3.1.13.1.8.1` — `jnxOperatingCPU.1`):**
     - Arc `2636` $= 20 \times 128 + 76$:
       - High 7 bits: $20 | \text{0x80} = 148 = \text{0x94}$
       - Low 7 bits: $76 = \text{0x4C}$
     - Full TLV: `06 0d 2b 06 01 04 01 94 4c 03 01 0d 01 08 01`

---

## 3. SNMPv2c Message & PDU Structure (Sections 9 & 10)

### 3.1 Top-Level SNMPv2c Message Envelope (`RFC 1901`)
```asn1
Message ::= SEQUENCE {
    version     INTEGER { version-2c(1) },   -- Always 02 01 01 for SNMPv2c
    community   OCTET STRING,                -- e.g., "netspout-lab" (04 0c 6e 65 74 73 70 6f 75 74 2d 6c 61 62)
    data        PDUs                         -- Context tag 0xA0..0xA7
}
```

### 3.2 Standard PDU Layout (`GET` `0xA0`, `GETNEXT` `0xA1`, `RESPONSE` `0xA2`, `INFORM` `0xA6`, `TRAPv2` `0xA7`)
```asn1
PDU ::= [PDU-TAG] IMPLICIT SEQUENCE {
    request-id          INTEGER (-2147483648..2147483647),
    error-status        INTEGER { noError(0), tooBig(1), noSuchName(2), badValue(3), readOnly(4), genErr(5), ... },
    error-index         INTEGER (0..max-bindings),
    variable-bindings   VarBindList
}

VarBindList ::= SEQUENCE OF VarBind

VarBind ::= SEQUENCE {
    name    ObjectName,          -- OBJECT IDENTIFIER (0x06)
    CHOICE {
        value           ObjectSyntax,
        unSpecified     NULL,                -- Used in GET / GETNEXT / GETBULK requests
        noSuchObject    [0] IMPLICIT NULL,   -- 0x80 0x00
        noSuchInstance  [1] IMPLICIT NULL,   -- 0x81 0x00
        endOfMibView    [2] IMPLICIT NULL    -- 0x82 0x00
    }
}
```

### 3.3 `GetBulkRequest-PDU` (`0xA5`) Layout
```asn1
BulkPDU ::= [5] IMPLICIT SEQUENCE {          -- Tag 0xA5
    request-id          INTEGER (-2147483648..2147483647),
    non-repeaters       INTEGER (0..max-bindings),
    max-repetitions     INTEGER (0..max-bindings),
    variable-bindings   VarBindList
}
```

### 3.4 Mandatory `TRAPv2` (`0xA7`) & `INFORM` (`0xA6`) VarBind Ordering (`RFC 3416 Section 4.2.6`)
Every `SNMPv2-Trap-PDU` and `InformRequest-PDU` **MUST** place the following two varbinds at index `0` and index `1` of `variable-bindings`:
1. **VarBind[0] — `sysUpTime.0` (`1.3.6.1.2.1.1.3.0`):**
   - Syntax: `TimeTicks` (`0x43`)
   - Value: Centiseconds since simulated agent initialization.
2. **VarBind[1] — `snmpTrapOID.0` (`1.3.6.1.6.3.1.1.4.1.0`):**
   - Syntax: `OBJECT IDENTIFIER` (`0x06`)
   - Value: Authoritative notification OID (e.g., `1.3.6.1.6.3.1.1.5.3` for `linkDown`).
3. **VarBind[2..N] — Notification `OBJECTS` Clause & Vendor VarBinds:**
   - For `linkDown` (`1.3.6.1.6.3.1.1.5.3`) and `linkUp` (`1.3.6.1.6.3.1.1.5.4`), `RFC 2863` mandates in exact order:
     - `VarBind[2]`: `ifIndex.<idx>` (`1.3.6.1.2.1.2.2.1.1.<idx>`, `Integer32`)
     - `VarBind[3]`: `ifAdminStatus.<idx>` (`1.3.6.1.2.1.2.2.1.7.<idx>`, `Integer32`: `1=up, 2=down`)
     - `VarBind[4]`: `ifOperStatus.<idx>` (`1.3.6.1.2.1.2.2.1.8.<idx>`, `Integer32`: `1=up, 2=down`)
   - Additional context varbinds (such as `ifDescr.<idx>` or `ifName.<idx>`) are appended starting at `VarBind[5]`.

---

## 4. Worked Deterministic Hexadecimal Protocol Fixtures (Section 47)

All 5 fixtures below use `version = 1 (SNMPv2c)` and `community = "netspout-lab"` (`04 0c 6e 65 74 73 70 6f 75 74 2d 6c 61 62`).

### Fixture 1: `SNMPv2c linkDown TRAP` (`0xA7`)
- **Parameters:** `request-id = 1001 (0x03E9)`, `sysUpTime.0 = 8640000 (0x0083D600)`, `snmpTrapOID.0 = 1.3.6.1.6.3.1.1.5.3 (linkDown)`, `ifIndex.1 = 1`, `ifAdminStatus.1 = 1 (up)`, `ifOperStatus.1 = 2 (down)`.
- **Byte Breakdown:**
  - VarBind[0] (`sysUpTime.0 = 8640000`): `30 10 06 08 2b 06 01 02 01 01 03 00 43 04 00 83 d6 00` (18 bytes)
  - VarBind[1] (`snmpTrapOID.0 = linkDown`): `30 17 06 0a 2b 06 01 06 03 01 01 04 01 00 06 09 2b 06 01 06 03 01 01 05 03` (25 bytes)
  - VarBind[2] (`ifIndex.1 = 1`): `30 0f 06 0a 2b 06 01 02 01 02 02 01 01 01 02 01 01` (17 bytes)
  - VarBind[3] (`ifAdminStatus.1 = 1`): `30 0f 06 0a 2b 06 01 02 01 02 02 01 07 01 02 01 01` (17 bytes)
  - VarBind[4] (`ifOperStatus.1 = 2`): `30 0f 06 0a 2b 06 01 02 01 02 02 01 08 01 02 01 02` (17 bytes)
  - `VarBindList`: Tag `30`, Length `94 (0x5E)` $\rightarrow$ 96 bytes
  - `PDU (0xA7)`: `02 02 03 e9` (`req-id=1001`, 4B) + `02 01 00` (`err=0`, 3B) + `02 01 00` (`idx=0`, 3B) + `VarBindList` (96B) = 106 (`0x6A`) bytes $\rightarrow$ `a7 6a ...` (108 bytes)
  - `Message (0x30)`: `02 01 01` (3B) + `04 0c 6e 65 74 73 70 6f 75 74 2d 6c 61 62` (14B) + `PDU` (108B) = 125 (`0x7D`) bytes $\rightarrow$ Total 127 bytes.
- **Complete Hex Stream (127 bytes):**
```text
307d020101040c6e657473706f75742d6c6162a76a020203e9020100020100305e301006082b0601020101030043040083d6003017060a2b06010603010104010006092b0601060301010503300f060a2b060102010202010101020101300f060a2b060102010202010701020101300f060a2b060102010202010801020102
```

### Fixture 2: `SNMPv2c linkUp TRAP` (`0xA7`)
- **Parameters:** `request-id = 1002 (0x03EA)`, `sysUpTime.0 = 8643000 (0x0083E1B8)`, `snmpTrapOID.0 = 1.3.6.1.6.3.1.1.5.4 (linkUp)`, `ifIndex.1 = 1`, `ifAdminStatus.1 = 1 (up)`, `ifOperStatus.1 = 1 (up)`.
- **Complete Hex Stream (127 bytes):**
```text
307d020101040c6e657473706f75742d6c6162a76a020203ea020100020100305e301006082b0601020101030043040083e1b83017060a2b06010603010104010006092b0601060301010504300f060a2b060102010202010101020101300f060a2b060102010202010701020101300f060a2b060102010202010801020101
```

### Fixture 3: `SNMPv2c INFORM Request` (`0xA6`) & Matching `RESPONSE` (`0xA2`)
- **Parameters:** `request-id = 2001 (0x07D1)`, `sysUpTime.0 = 8640500 (0x0083D7F4)`, `snmpTrapOID.0 = 1.3.6.1.2.1.15.7.2 (bgpBackwardTransition)`, `bgpPeerState.10.255.0.2 = 1 (idle)`.
  - VarBind[0] (`sysUpTime.0`): `30 10 06 08 2b 06 01 02 01 01 03 00 43 04 00 83 d7 f4` (18 bytes)
  - VarBind[1] (`snmpTrapOID.0 = 1.3.6.1.2.1.15.7.2`): `30 16 06 0a 2b 06 01 06 03 01 01 04 01 00 06 08 2b 06 01 02 01 0f 07 02` (24 bytes)
  - VarBind[2] (`bgpPeerState.10.255.0.2 = 1`): OID `1.3.6.1.2.1.15.3.1.2.10.255.0.2` (`255` = `0x81 0x7F` in VLQ $\rightarrow$ `06 0e 2b 06 01 02 01 0f 03 01 02 0a 81 7f 00 02`, Value `02 01 01`) $\rightarrow$ `30 13 06 0e 2b 06 01 02 01 0f 03 01 02 0a 81 7f 00 02 02 01 01` (21 bytes)
  - `VarBindList`: Tag `30`, Length `63 (0x3F)` (18 + 24 + 21 = 63 bytes) $\rightarrow$ 65 bytes; `PDU`: Tag `A6`, Length `75 (0x4B)` $\rightarrow$ 77 bytes; `Message`: Tag `30`, Length `94 (0x5E)` $\rightarrow$ Total 96 bytes.
- **Complete `InformRequest-PDU (0xA6)` Hex Stream (96 bytes):**
```text
305e020101040c6e657473706f75742d6c6162a64b020207d1020100020100303f301006082b0601020101030043040083d7f43016060a2b06010603010104010006082b060102010f07023013060e2b060102010f0301020a817f0002020101
```
- **Matching `Response-PDU (0xA2)` Acknowledgement Hex Stream (96 bytes, PDU tag `0xA6` $\rightarrow$ `0xA2`):**
```text
305e020101040c6e657473706f75742d6c6162a24b020207d1020100020100303f301006082b0601020101030043040083d7f43016060a2b06010603010104010006082b060102010f07023013060e2b060102010f0301020a817f0002020101
```

### Fixture 4: `SNMPv2c GetRequest-PDU` (`0xA0`) for `ifOperStatus.1`
- **Parameters:** `request-id = 3001 (0x0BB9)`, OID `1.3.6.1.2.1.2.2.1.8.1` (`ifOperStatus.1`), Value = `NULL (05 00)`.
- **Complete Hex Stream (49 bytes):**
```text
302f020101040c6e657473706f75742d6c6162a01c02020bb90201000201003010300e060a2b0601020102020108010500
```

### Fixture 5: `SNMPv2c Response-PDU` (`0xA2`) for `ifOperStatus.1 = 1 (up)`
- **Parameters:** `request-id = 3001 (0x0BB9)`, OID `1.3.6.1.2.1.2.2.1.8.1` (`ifOperStatus.1`), Value = `Integer32(1) (02 01 01)`.
- **Complete Hex Stream (50 bytes):**
```text
3030020101040c6e657473706f75742d6c6162a21d02020bb90201000201003011300f060a2b060102010202010801020101
```
