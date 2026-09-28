# NetSpout SNMPv3 Future Architecture & USM Security Blueprint (Gate 12E Target)

**Author:** Mahamudul Chowdhury (`machowdhury@yahoo.com`)  
**Gate:** 12 (Native SNMP Architecture & Protocol Definition — Future Gate 12E Target)  
**Standards Reference:** `RFC 3411` (Architecture), `RFC 3412` (Message Processing), `RFC 3414` (USM), `RFC 3826` (AES Privacy), `RFC 7860` (HMAC-SHA-2 Authentication)

---

## 1. Executive Summary & Scope

While Gates 12B–12D implement `SNMPv2c` (`RFC 3416`), enterprise security compliance and federal/financial network simulations require **SNMPv3 (`STD 62`)** with cryptographic authentication and privacy. This document defines NetSpout's future **Gate 12E SNMPv3 User-Based Security Model (USM)** architecture so that the `SNMPv2c` PDU and OID layers built in Gate 12B–12D drop cleanly into an `SNMPv3` `ScopedPDU` envelope without refactoring.

> [!IMPORTANT]
> **Gate 12 Constraint:** No SNMPv3 cryptography, USM state machines, or sockets are implemented in Gate 12. No plaintext SNMPv3 passphrases or localized keys may ever be committed to the repository.

---

## 2. SNMPv3 Message Structure (`RFC 3412`)

An `SNMPv3` message (`msgVersion = 3`) wraps the exact same `RFC 3416` PDU used in `SNMPv2c` inside a `ScopedPDU` alongside a `HeaderData` block and a `UsmSecurityParameters` OCTET STRING:

```asn1
SNMPv3Message ::= SEQUENCE {
    msgVersion              INTEGER (3),
    msgGlobalData           HeaderData,
    msgSecurityParameters   OCTET STRING,   -- BER-encoded UsmSecurityParameters
    msgData                 ScopedPduData
}

HeaderData ::= SEQUENCE {
    msgID                   INTEGER (0..2147483647),
    msgMaxSize              INTEGER (484..2147483647),  -- 1472 in NetSpout
    msgFlags                OCTET STRING (SIZE(1)),     -- bit0=authFlag, bit1=privFlag, bit2=reportableFlag
    msgSecurityModel        INTEGER (3)                 -- 3 = USM (RFC 3414)
}

ScopedPduData ::= CHOICE {
    plaintext               ScopedPDU,                  -- Used in noAuthNoPriv and authNoPriv
    encryptedPDU            OCTET STRING                -- AES-128-CFB ciphertext of ScopedPDU in authPriv
}

ScopedPDU ::= SEQUENCE {
    contextEngineID         OCTET STRING,
    contextName             OCTET STRING,               -- Default "" (empty string)
    data                    PDUs                        -- Identical 0xA0..0xA8 PDU from SNMPv2c!
}
```

### `msgFlags` Single-Octet Bitmask

| Security Level | `authFlag` (`0x01`) | `privFlag` (`0x02`) | `reportableFlag` (`0x04`) | `msgFlags` Hex (`TRAPv2`) | `msgFlags` Hex (`GET`/`INFORM`) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **`noAuthNoPriv`** | `0` | `0` | `0` or `1` | `0x00` | `0x04` |
| **`authNoPriv`** | `1` | `0` | `0` or `1` | `0x01` | `0x05` |
| **`authPriv`** | `1` | `1` | `0` or `1` | `0x03` | `0x07` |

*(Note: `privNoAuth` (`0x02`) is illegal per `RFC 3414`; encryption always requires authentication).*

---

## 3. User-Based Security Model (`USM` — `RFC 3414`)

The `msgSecurityParameters` field in `SNMPv3Message` contains a BER-encoded `SEQUENCE`:

```asn1
UsmSecurityParameters ::= SEQUENCE {
    msgAuthoritativeEngineID    OCTET STRING,
    msgAuthoritativeEngineBoots INTEGER (0..2147483647),
    msgAuthoritativeEngineTime  INTEGER (0..2147483647),
    msgUserName                 OCTET STRING (SIZE(0..32)),
    msgAuthenticationParameters OCTET STRING,   --Truncated HMAC digest (zeroed during calculation)
    msgPrivacyParameters        OCTET STRING    -- 8-octet salt for AES-128-CFB
}
```

### 3.1 Authoritative Engine Identity Rules (`engineID`)
Per `RFC 3411 Section 5`, the **Authoritative SNMP Engine** depends on the operation type:
1. **`SNMPv2-Trap (0xA7)`:** The **Sender (NetSpout Simulated Device)** is authoritative. The receiver only needs to be pre-configured with NetSpout's `msgAuthoritativeEngineID`; no round-trip engine discovery is required.
2. **`InformRequest (0xA6)`:** The **Receiver (`snmptrapd` / `SC4SNMP`)** is authoritative. Before sending an authenticated `INFORM`, NetSpout performs a 1-RTT USM Engine Discovery probe (`GetRequest` or unauthenticated `InformRequest` with empty `engineID` and `reportableFlag = 1`), receiving a `Report-PDU (0xA8)` containing `usmStatsUnknownEngineIDs.0` (`1.3.6.1.6.3.15.1.1.4.0`) and the receiver's authoritative `(engineID, engineBoots, engineTime)`.
3. **`GET` / `GETNEXT` / `GETBULK` (`0xA0`, `0xA1`, `0xA5`):** The **Simulated Agent (NetSpout)** is authoritative.

### 3.2 Canonical Deterministic `snmpEngineID` Format (`RFC 3411`)
NetSpout generates deterministic 12-octet (`24 hex char`) RFC 3411 format `0x03` (IPv4-based) or format `0x04` (Text/Node-hash) `snmpEngineID` values per simulated node:
- Octets `0..3`: `(0x80000000 | enterprise_pen)` in big-endian (e.g., `80 00 00 09` for Cisco PEN `9`, `80 00 1f 88` for Net-SNMP PEN `8072`).
- Octet `4`: `0x01` (IPv4 address format).
- Octets `5..8`: Node's simulated IPv4 address (4 octets, e.g., `0a ff 00 01` for `10.255.0.1`).
-Example `engineID` hex: `80000009010aff0001`.

---

## 4. Timeliness, `engineBoots`, `engineTime` & Replay Protection

To prevent packet replay attacks, `RFC 3414 Section 2.2.3` enforces a two-tier clock window:
- **`msgAuthoritativeEngineBoots`:** Count of times the authoritative SNMP engine has initialized/rebooted (`1 .. 2147483647`; `2147483647` latches if exceeded).
- **`msgAuthoritativeEngineTime`:** Seconds elapsed since `msgAuthoritativeEngineBoots` last incremented (`floor(sysUpTime / 100)`).
- **150-Second Replay Window:** An authenticated message is rejected with `usmStatsNotInTimeWindows.0` (`1.3.6.1.6.3.15.1.1.2.0`) if:
  1. `msgAuthoritativeEngineBoots != localEngineBoots`, OR
  2. $| \text{msgAuthoritativeEngineTime} - \text{localEngineTime} | > 150\text{ seconds}$.

---

## 5. Authentication & Privacy Algorithms & Key Localization

### 5.1 Supported Authentication Protocols (`authNoPriv` & `authPriv`)

| Protocol Name | Standard | Hash Output | Truncated MAC in `msgAuthenticationParameters` | Support Status in Gate 12E |
| :--- | :--- | :---: | :---: | :--- |
| **`usmHMAC192SHA256AuthProtocol`** | `RFC 7860` | 32 bytes | **24 octets (192 bits)** | **RECOMMENDED DEFAULT** |
| **`usmHMAC384SHA512AuthProtocol`** | `RFC 7860` | 64 bytes | **48 octets (384 bits)** | Supported |
| **`usmHMACSHAAuthProtocol` (SHA-1)** | `RFC 3414` | 20 bytes | 12 octets (96 bits) | Legacy compatibility only |
| **`usmHMACMD5AuthProtocol` (MD5)** | `RFC 3414` | 16 bytes | 12 octets (96 bits) | **DEPRECATED / DISABLED BY DEFAULT** |

### 5.2 Supported Privacy Protocols (`authPriv`)

| Protocol Name | Standard | Key Length | IV Construction (`128 bits / 16 octets`) | Support Status in Gate 12E |
| :--- | :--- | :---: | :--- | :--- |
| **`usmAesCfb128Protocol` (AES-128-CFB)** | `RFC 3826` | 16 octets (128 bits) | `BigEndian32(engineBoots) \|\| BigEndian32(engineTime) \|\| 64-bit Salt (msgPrivacyParameters)` | **RECOMMENDED DEFAULT** |
| **`usmDESPrivProtocol` (56-bit DES)** | `RFC 3414` | 8 octets | 32-bit salt XORed with pre-IV | **PROHIBITED (Cryptographically Broken)** |

### 5.3 Key Localization Algorithm (`RFC 3414 Section 2.6` & `RFC 7860`)
User passphrases are never used directly as HMAC or AES keys. Instead, a 2-step **Key Localization** transform binds the key to a single `msgAuthoritativeEngineID` so that compromising one device's localized key cannot compromise other devices sharing the same passphrase:
1. **Password-to-Master-Key ($Ku$):** Repeat the user passphrase (minimum 8 characters) to fill a $1\text{ MB}$ ($1,048,576\text{ byte}$) buffer and hash with the selected SHA algorithm:
   $$Ku = \text{Hash}(\text{Repeat}_{1048576}(\text{passphrase}))$$
2. **Master-Key-to-Localized-Key ($Kul$):** Hash the concatenation of $Ku$, `msgAuthoritativeEngineID`, and $Ku$:
   $$Kul = \text{Hash}(Ku \,\|\, \text{msgAuthoritativeEngineID} \,\|\, Ku)$$
   For `AES-128-CFB`, the first 16 octets of $Kul_{\text{priv}}$ form the 128-bit AES key.

---

## 6. Secret Management & Zero-Plaintext Repository Policy

1. **No Secrets in Git:** Repository files (`catalog/`, `src/`, `tests/`, `deploy/`) must **never** contain production SNMPv3 passphrases or localized keys.
2. **Runtime Injection Only:** In Gate 12E, SNMPv3 credentials will be supplied strictly via runtime environment variables:
   - `NETSPOUT_SNMPV3_USERNAME`
   - `NETSPOUT_SNMPV3_AUTH_PROTOCOL` (`SHA256` default)
   - `NETSPOUT_SNMPV3_AUTH_KEY_ENV` (read from environment or ephemeral Docker secret file `/run/secrets/snmpv3_auth`)
   - `NETSPOUT_SNMPV3_PRIV_PROTOCOL` (`AES128` default)
   - `NETSPOUT_SNMPV3_PRIV_KEY_ENV` (read from `/run/secrets/snmpv3_priv`)
3. **Ephemeral Test Key Generation:** Unit tests in Gate 12E will dynamically generate random per-test passphrases in memory (`secrets.token_hex(16)`) at test execution time.
