# NETSPOUT GATE 12B — NATIVE SNMPv2c TRAP & INFORM IMPLEMENTATION

**Status:** COMPLETE  
**Gate:** 12B (Bounded Native SNMPv2c Trap & Inform Implementation + Protocol Verification)  
**Target Scenario:** `service_provider_cisco` (Single-Scenario Authorization)  
**Protocols Implemented:** `SNMPv2c` (`RFC 1901`, `RFC 3416`, `RFC 2578`) — `SNMPv2-Trap-PDU (0xA7)`, `InformRequest-PDU (0xA6)`, `Response-PDU (0xA2)`, plus Golden Fixture `GetRequest-PDU (0xA0)`  

---

## 1. Architectural Scope & Non-Expansion Boundaries

Gate 12B implements the bounded protocol core approved in Gate 12 without expanding scope into SNMP polling agents (`GET`/`GETNEXT`/`GETBULK` runtime responder), `SNMPv3/USM`, external container stacks (`SC4SNMP`, `snmptrapd` production containers), or Splunk end-to-end SNMP ingestion (`SPLUNK_OBSERVED`).

### Core Modules Added or Updated
| Module | Role |
|---|---|
| [`src/netspout_core/snmp_ber.py`](file:///Users/mahamudc/Documents/NetSpout/src/netspout_core/snmp_ber.py) | Deterministic ASN.1 BER encoder (`SnmpBerEncoder`), reference decoder (`SnmpBerDecoder`), and 5 Golden Hex Fixture verifier (`verify_golden_fixtures()`). |
| [`src/netspout_core/transport_native_snmp.py`](file:///Users/mahamudc/Documents/NetSpout/src/netspout_core/transport_native_snmp.py) | Safe UDP transport (`NativeSnmpTransport`), `INFORM` retry/acknowledgement state machine, `127.0.0.1` loopback test receiver (`LoopbackSnmpTestReceiver`), and libpcap writer (`write_snmp_pcap()`). |
| [`src/netspout_core/models.py`](file:///Users/mahamudc/Documents/NetSpout/src/netspout_core/models.py) | Canonical SNMPv2c models (`SnmpVersion`, `SnmpPduType`, `SnmpAsn1Type`, `OidFidelityClass`, `SnmpEvidenceStage`, `SnmpVarBind`, `SnmpMessage`, `SnmpTrap`, `SnmpInform`, `SnmpResponse`, `SnmpTransportResult`) and `validate_notification_varbind_order()`. |
| [`src/netspout_core/snmp_engine.py`](file:///Users/mahamudc/Documents/NetSpout/src/netspout_core/snmp_engine.py) | OID fidelity classification (`STANDARD_VERIFIED`, `VENDOR_VERIFIED`, `MODELED`, `SYNTHETIC`), `sysObjectID` (`1.3.6.1.2.1.1.2.0`) syntax correction to `ObjectIdentifier`, deterministic instance OID suffix formatting, seeded 31-bit `request-id` derivation, and `service_provider_cisco` native PDU builder. |
| [`src/netspout_core/companion_manifest.py`](file:///Users/mahamudc/Documents/NetSpout/src/netspout_core/companion_manifest.py) | Out-of-band correlation manifest builder (`CompanionManifestBuilder.build_snmp_manifest()`) mapping `run_id`, `scenario_id`, `seed`, `pdu_mode`, `request_ids`, and `acknowledged_request_ids` without polluting wire varbinds. |
| [`src/netspout_core/scenario_runner.py`](file:///Users/mahamudc/Documents/NetSpout/src/netspout_core/scenario_runner.py) | Bounded integration of Native SNMPv2c (`TRAP` and `INFORM`) with `service_provider_cisco` only. |

---

## 2. ASN.1 BER Wire Encoding & Decoding (`src/netspout_core/snmp_ber.py`)

`SnmpBerEncoder` and `SnmpBerDecoder` implement strict definite-length ASN.1 Basic Encoding Rules (`ITU-T X.690` / `RFC 3416` / `RFC 2578`):

1. **Length Octets:**
   - Short definite form (`0x00..0x7F`) for payload lengths `0..127`.
   - Long definite form (`0x81..0x82`) for payload lengths `>= 128`.
   - **Indefinite length (`0x80`) is strictly rejected** (`SnmpBerDecodeError`) per `RFC 3416`.
2. **Signed & Unsigned Integer Rules:**
   - `Integer32` (`0x02`) uses minimal two's-complement big-endian encoding in `-2,147,483,648 .. 2,147,483,647`.
   - Unsigned application types (`Counter32 0x41`, `Gauge32 0x42`, `TimeTicks 0x43`, `Counter64 0x46`) prepend a `0x00` pad byte when the most significant bit is `1` to preserve positive unsigned interpretation in ASN.1 two's complement.
3. **OBJECT IDENTIFIER (`0x06`) Base-128 VLQ:**
   - First two arcs encoded as `(arc0 * 40) + arc1` (`1.3` $\rightarrow$ `0x2B`).
   - Subsequent sub-identifiers encoded in minimal big-endian base-128 Variable-Length Quantity (VLQ) with continuation bit `0x80` on all leading septets and `0` on the final septet (e.g., `255` $\rightarrow$ `0x81 0x7F`).
4. **Defensive Decoder Controls:**
   - Enforces maximum ASN.1 nesting depth `<= 5` (`SnmpBerRecursionError`).
   - Rejects truncated TLVs, lengths exceeding packet boundaries, trailing garbage octets, unsupported SNMP versions (`!= 1` for `SNMPv2c`), and community mismatches (`SnmpCommunityMismatchError`).
   - Enforces maximum UDP payload size `<= 1,472 bytes` (`SnmpPayloadSizeError`) to prevent IPv4 fragmentation on standard 1,500-byte Ethernet MTUs.

---

## 3. Mandatory `RFC 3416` Notification VarBind Ordering

Both `SnmpTrap` (`0xA7`) and `SnmpInform` (`0xA6`) enforce `validate_notification_varbind_order()` at construction, encoding, and decoding boundaries:
- **`varbinds[0]`:** `sysUpTime.0` (`1.3.6.1.2.1.1.3.0`) with syntax `TimeTicks (0x43)`.
- **`varbinds[1]`:** `snmpTrapOID.0` (`1.3.6.1.6.3.1.1.4.1.0`) with syntax `ObjectIdentifier (0x06)`.
- **`varbinds[2..N]`:** Standard MIB notification objects (`ifIndex`, `ifAdminStatus`, `ifOperStatus`, `ifDescr` for `IF-MIB::linkDown`/`linkUp`; `bgpPeerLastError`, `bgpPeerState` for `BGP4-MIB::bgpBackwardTransition`/`bgpEstablished`).
- **Zero Proprietary VarBinds on Wire:** Correlation with NetSpout runs uses deterministic seeded 31-bit `request-id` values (`derive_deterministic_request_id(seed, scenario_id, pdu_index)`) recorded out-of-band in `CompanionControlManifest`.

---

## 4. Safe UDP Transport & `INFORM` Retry State Machine (`src/netspout_core/transport_native_snmp.py`)

### 4.1 Safety Guardrails
- **Default Target:** `127.0.0.1:1162` (unprivileged loopback port).
- **Destination Validation:** Reuses `transport_safety.validate_destination_target()` and explicitly rejects public Internet IPs (unless `NETSPOUT_ALLOW_PUBLIC_EXPORT=true`), multicast (`224.0.0.0/4`), broadcast (`255.255.255.255`), and unspecified (`0.0.0.0`) addresses.
- **Rate Limits & Packet Caps:**
  - `TRAP`: default `50 pps`, hard ceiling `250 pps`.
  - `INFORM`: default `25 pps`, hard ceiling `100 pps`.
  - Scenario packet cap: default `1,000` datagrams/run, hard ceiling `5,000` datagrams/run.

### 4.2 Honest Evidence Stages
- **`TRAP` (`0xA7`):** `GENERATED -> ENCODED -> SENT -> RECEIVER_OBSERVED`. `SENT` never implies `RECEIVER_OBSERVED`; `RECEIVER_OBSERVED` is only recorded when an active receiver (`LoopbackSnmpTestReceiver`) confirms receipt and decoding.
- **`INFORM` (`0xA6`):** `GENERATED -> ENCODED -> SENT -> ACKNOWLEDGED -> RECEIVER_OBSERVED`. Sends `InformRequest-PDU (0xA6)` and waits (`timeout_ms = 1500`, `max_retries = 2`, up to `3` total attempts) for a matching `Response-PDU (0xA2)` with identical `request-id` and `error-status == 0`.

---

## 5. `service_provider_cisco` Fault-to-Recovery Notification Progression

When `service_provider_cisco` runs with `TELEMETRY_TRANSPORTS` containing `SNMPV2C_TRAP` or `SNMPV2C_INFORM`, `SNMPEngine.build_service_provider_cisco_native_pdus()` emits the deterministic 4-PDU progression:
1. **`DEGRADE` (`pdu_index=0`):** `IF-MIB::linkDown` (`1.3.6.1.6.3.1.1.5.3`) — `ifIndex.1=1`, `ifAdminStatus.1=1 (up)`, `ifOperStatus.1=2 (down)`, `ifDescr.1="TenGigE0/0/0/1"`.
2. **`FAILOVER` (`pdu_index=1`):** `BGP4-MIB::bgpBackwardTransition` (`1.3.6.1.2.1.15.7.2`) — `bgpPeerLastError.198.51.100.1=0x0400` (Hold Timer Expired), `bgpPeerState.198.51.100.1=1 (idle)`.
3. **`RECOVERY` (`pdu_index=2`):** `IF-MIB::linkUp` (`1.3.6.1.6.3.1.1.5.4`) — `ifIndex.1=1`, `ifAdminStatus.1=1 (up)`, `ifOperStatus.1=1 (up)`, `ifDescr.1="TenGigE0/0/0/1"`.
4. **`RECOVERY` (`pdu_index=3`):** `BGP4-MIB::bgpEstablished` (`1.3.6.1.2.1.15.7.1`) — `bgpPeerLastError.198.51.100.1=0x0000`, `bgpPeerState.198.51.100.1=6 (established)`.
