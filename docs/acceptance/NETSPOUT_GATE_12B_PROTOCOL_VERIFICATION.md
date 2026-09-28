# NETSPOUT GATE 12B — INDEPENDENT SNMPv2c PROTOCOL VERIFICATION REPORT

**Status:** VERIFIED (`PASS`)  
**Gate:** 12B  
**Independent Dissector:** `TShark (Wireshark) /opt/homebrew/bin/tshark`  
**Malformed Packet Warnings:** `0`  
**Evidence Directory:** [`docs/acceptance/evidence/gate12b/`](file:///Users/mahamudc/Documents/NetSpout/docs/acceptance/evidence/gate12b/)

---

## 1. Golden Hex Fixture Verification (`5 / 5 PASS`)

All 5 canonical Golden Hex Fixtures defined in [`docs/architecture/NETSPOUT_SNMP_V2C_PROTOCOL_SPEC.md`](file:///Users/mahamudc/Documents/NetSpout/docs/architecture/NETSPOUT_SNMP_V2C_PROTOCOL_SPEC.md) and [`src/netspout_core/snmp_ber.py`](file:///Users/mahamudc/Documents/NetSpout/src/netspout_core/snmp_ber.py) were verified via `encode -> byte equality -> SHA-256 -> decode -> re-encode`:

| Fixture | PDU Tag | Request-ID | Byte Length | Expected == Actual Hex | SHA-256 Digest | Verdict |
|---|---|---|---|---|---|---|
| **1. `SNMPv2c linkDown TRAP`** | `0xA7` | `1001` | `127` | `True` | `f3039227a2fabeefdf04cff609e29a07f2ca0e9a9800089602a1177e045b0e12` | **PASS** |
| **2. `SNMPv2c linkUp TRAP`** | `0xA7` | `1002` | `127` | `True` | `f5013010de38b1cccd39c5ca740aab706c1b265561fc4484ef43dd72861d43aa` | **PASS** |
| **3. `SNMPv2c bgpBackwardTransition INFORM`** | `0xA6` | `2001` | `96` | `True` | `dc457da1877dc7510179da158b56eed4f8aecc1f0fe5616ac94d71626f7e2b6b` | **PASS** |
| **4. `SNMPv2c GET Request (ifOperStatus.1)`** | `0xA0` | `3001` | `49` | `True` | `0c52511b084a4a02b9fce48cc927792011b552c11efc26c2e09eb9313b154454` | **PASS** |
| **5. `SNMPv2c GET RESPONSE (ifOperStatus.1 = 1)`** | `0xA2` | `3001` | `50` | `True` | `db48e0af2aac0443ba3d8e399ceaf2d2fd255df018e9758758baa7ed29a11992` | **PASS** |

> [!NOTE]
> **Protocol Correctness Reconciliation (Gate 12B Section 1):**  
> During byte-level ASN.1 BER verification against `TShark`, Fixtures 1 and 2 (`127 bytes`) required zero adjustments, while the hand-computed outer length octets in Gate 12 for Fixtures 3, 4, and 5 were reconciled to exact ASN.1 definite lengths:
> - **Fixture 3 (`INFORM`):** VarBind lengths `18 + 24 + 21 = 63 (0x3F)` bytes $\rightarrow$ `VarBindList = 30 3f`, `PDU = a6 4b`, `Message = 30 5e` (`96 bytes`).
> - **Fixture 4 (`GET`):** OID TLV (`12 bytes`) + NULL TLV (`2 bytes`) = `14 (0x0E)` bytes $\rightarrow$ `VarBind = 30 0e`, `VarBindList = 30 10`, `PDU = a0 1c`, `Message = 30 2f` (`49 bytes`).
> - **Fixture 5 (`RESPONSE`):** OID TLV (`12 bytes`) + Integer32 TLV (`3 bytes`) = `15 (0x0F)` bytes $\rightarrow$ `VarBind = 30 0f`, `VarBindList = 30 11`, `PDU = a2 1d`, `Message = 30 30` (`50 bytes`).

---

## 2. Independent `TShark` Protocol Dissection Evidence

### 2.1 Commands Executed
```bash
# 1. Dissect all 5 Golden Hex Fixtures PCAP
/opt/homebrew/bin/tshark -r docs/acceptance/evidence/gate12b/gate12b_golden_fixtures.pcap -Y snmp -V

# 2. Dissect live loopback capture for service_provider_cisco (4 Traps + 4 Informs + 4 Response-PDUs = 12 frames)
/opt/homebrew/bin/tshark -r docs/acceptance/evidence/gate12b/gate12b_service_provider_cisco_live.pcap \
  -d udp.port==1162,snmp -Y snmp -T fields \
  -e frame.number -e snmp.version -e snmp.community -e snmp.data -e snmp.name
```

### 2.2 Live `service_provider_cisco` Dissected Frame Table (`12 / 12 Frames Verified`)

| Frame | SNMP Version | Community | PDU Type (`snmp.data`) | Dissected VarBind OIDs (`snmp.name`) |
|---|---|---|---|---|
| `1` | `1 (v2c)` | `netspout-lab` | `7 (snmpV2-trap)` | `1.3.6.1.2.1.1.3.0, 1.3.6.1.6.3.1.1.4.1.0, 1.3.6.1.2.1.2.2.1.1.1, 1.3.6.1.2.1.2.2.1.7.1, 1.3.6.1.2.1.2.2.1.8.1, 1.3.6.1.2.1.2.2.1.2.1` |
| `2` | `1 (v2c)` | `netspout-lab` | `7 (snmpV2-trap)` | `1.3.6.1.2.1.1.3.0, 1.3.6.1.6.3.1.1.4.1.0, 1.3.6.1.2.1.15.3.1.14.198.51.100.1, 1.3.6.1.2.1.15.3.1.2.198.51.100.1` |
| `3` | `1 (v2c)` | `netspout-lab` | `7 (snmpV2-trap)` | `1.3.6.1.2.1.1.3.0, 1.3.6.1.6.3.1.1.4.1.0, 1.3.6.1.2.1.2.2.1.1.1, 1.3.6.1.2.1.2.2.1.7.1, 1.3.6.1.2.1.2.2.1.8.1, 1.3.6.1.2.1.2.2.1.2.1` |
| `4` | `1 (v2c)` | `netspout-lab` | `7 (snmpV2-trap)` | `1.3.6.1.2.1.1.3.0, 1.3.6.1.6.3.1.1.4.1.0, 1.3.6.1.2.1.15.3.1.14.198.51.100.1, 1.3.6.1.2.1.15.3.1.2.198.51.100.1` |
| `5` | `1 (v2c)` | `netspout-lab` | `6 (informRequest)` | `1.3.6.1.2.1.1.3.0, 1.3.6.1.6.3.1.1.4.1.0, 1.3.6.1.2.1.2.2.1.1.1, 1.3.6.1.2.1.2.2.1.7.1, 1.3.6.1.2.1.2.2.1.8.1, 1.3.6.1.2.1.2.2.1.2.1` |
| `6` | `1 (v2c)` | `netspout-lab` | `2 (get-response)` | `1.3.6.1.2.1.1.3.0, 1.3.6.1.6.3.1.1.4.1.0, 1.3.6.1.2.1.2.2.1.1.1, 1.3.6.1.2.1.2.2.1.7.1, 1.3.6.1.2.1.2.2.1.8.1, 1.3.6.1.2.1.2.2.1.2.1` |
| `7` | `1 (v2c)` | `netspout-lab` | `6 (informRequest)` | `1.3.6.1.2.1.1.3.0, 1.3.6.1.6.3.1.1.4.1.0, 1.3.6.1.2.1.15.3.1.14.198.51.100.1, 1.3.6.1.2.1.15.3.1.2.198.51.100.1` |
| `8` | `1 (v2c)` | `netspout-lab` | `2 (get-response)` | `1.3.6.1.2.1.1.3.0, 1.3.6.1.6.3.1.1.4.1.0, 1.3.6.1.2.1.15.3.1.14.198.51.100.1, 1.3.6.1.2.1.15.3.1.2.198.51.100.1` |
| `9` | `1 (v2c)` | `netspout-lab` | `6 (informRequest)` | `1.3.6.1.2.1.1.3.0, 1.3.6.1.6.3.1.1.4.1.0, 1.3.6.1.2.1.2.2.1.1.1, 1.3.6.1.2.1.2.2.1.7.1, 1.3.6.1.2.1.2.2.1.8.1, 1.3.6.1.2.1.2.2.1.2.1` |
| `10` | `1 (v2c)` | `netspout-lab` | `2 (get-response)` | `1.3.6.1.2.1.1.3.0, 1.3.6.1.6.3.1.1.4.1.0, 1.3.6.1.2.1.2.2.1.1.1, 1.3.6.1.2.1.2.2.1.7.1, 1.3.6.1.2.1.2.2.1.8.1, 1.3.6.1.2.1.2.2.1.2.1` |
| `11` | `1 (v2c)` | `netspout-lab` | `6 (informRequest)` | `1.3.6.1.2.1.1.3.0, 1.3.6.1.6.3.1.1.4.1.0, 1.3.6.1.2.1.15.3.1.14.198.51.100.1, 1.3.6.1.2.1.15.3.1.2.198.51.100.1` |
| `12` | `1 (v2c)` | `netspout-lab` | `2 (get-response)` | `1.3.6.1.2.1.1.3.0, 1.3.6.1.6.3.1.1.4.1.0, 1.3.6.1.2.1.15.3.1.14.198.51.100.1, 1.3.6.1.2.1.15.3.1.2.198.51.100.1` |

- **Malformed Packet Warnings in Golden PCAP:** `0`
- **Malformed Packet Warnings in Live Loopback PCAP:** `0`

---

## 3. Gate 12B Test Matrix Summary (`26 / 26 PASS`)

All 26 mandatory unit, fixture, loopback transport, fault-injection, safety guardrail, scenario integration, and `TShark` protocol tests in [`tests/test_gate12b_native_snmp.py`](file:///Users/mahamudc/Documents/NetSpout/tests/test_gate12b_native_snmp.py) passed with `0` failures and `0` errors.
