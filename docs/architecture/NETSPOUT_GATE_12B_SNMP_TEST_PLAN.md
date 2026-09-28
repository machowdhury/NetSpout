# NetSpout Gate 12B — Native SNMPv2c Verification & Acceptance Test Plan

**Author:** Mahamudul Chowdhury (`machowdhury@yahoo.com`)  
**Gate:** 12 (Native SNMP Architecture & Protocol Definition — Test Plan for Gate 12B/12C/12D)  
**Target Scope:** `SNMPv2c` ASN.1 BER Encoding/Decoding, `TRAPv2` (`0xA7`), `InformRequest` (`0xA6`) + `Response` (`0xA2`), Independent `TShark` Dissection, Safety Guardrails, and Negative Testing

---

## 1. Gate 12B Implementation & Verification Scope (Section 48)

Gate 12B will implement and verify the foundational **Native SNMPv2c Protocol & Transport Engine** (`TRAPv2` + `INFORM`) before external container orchestration in Gate 12C and polling agent execution in Gate 12D.

### Mandatory Gate 12B Acceptance Contract

| # | Acceptance Requirement | Verification Method | Pass Criterion |
| :-: | :--- | :--- | :--- |
| 1 | **ASN.1 BER Encoding Correctness** | Byte-exact comparison against the 5 Golden Hex Fixtures defined in `NETSPOUT_SNMP_V2C_PROTOCOL_SPEC.md` | `100%` byte-for-byte match across all TLV tags, definite lengths, base-128 VLQ OIDs, and two's complement values |
| 2 | **Independent `TShark` Dissection** | Capture/write PCAP of generated `TRAPv2` and `INFORM`/`RESPONSE` packets and dissect via `tshark -r <pcap> -V` | `snmp` dissector decodes `version: v2c (1)`, community `"netspout-lab"`, PDU type, `request-id`, and all varbinds |
| 3 | **Zero Malformed Packet Warnings** | Inspect `tshark` output for `[Malformed Packet]` or `[Expert Info (Warning/Error)]` | **`Malformed warnings = 0`** |
| 4 | **Mandatory `TRAPv2`/`INFORM` VarBind Order** | Inspect decoded `variable-bindings` index `0` and `1` | `VarBind[0] == 1.3.6.1.2.1.1.3.0 (sysUpTime.0)` (`TimeTicks`), `VarBind[1] == 1.3.6.1.6.3.1.1.4.1.0 (snmpTrapOID.0)` (`OID`) |
| 5 | **All ASN.1 SMIv2 Types Verified** | Encode and `TShark`-decode `Integer32`, `OctetString`, `Null`, `ObjectIdentifier`, `IpAddress`, `Counter32`, `Gauge32`, `TimeTicks`, `Opaque`, `Counter64` | All 10 primitive/application tags (`0x02..0x46`) decode to exact input values including MSB `>= 0x80` sign-padding cases |
| 6 | **Deterministic Generation** | Run encoder twice with identical `(scenario_id, seed, node_id, phase, timestamp_base)` | Identical `request-id`, `sysUpTime.0`, OID order, and identical wire hex output |
| 7 | **`INFORM` Acknowledgement Semantics** | Send `InformRequest (0xA6)` to local loopback responder returning `Response (0xA2)` with matching `request-id` | Transport state transitions `GENERATED -> ENCODED -> SENT -> ACKNOWLEDGED`; `rtt_ms > 0` recorded |
| 8 | **`INFORM` Timeout, Retry & Deduplication** | 1) Drop first packet on loopback responder $\rightarrow$ verify retry succeeds with same `request-id`.<br>2) Stop responder $\rightarrow$ verify timeout after `max_retries`. | 1) Retries preserve exact `request-id`; deduplicated by receiver.<br>2) Offline receiver stays at `SENT` (`acknowledged = False`), never falsely claiming `ACKNOWLEDGED`. |
| 9 | **Destination Safety Enforcement** | Attempt `SnmpTransport` to public IP (`8.8.8.8:162`), broadcast (`255.255.255.255`), or multicast (`224.0.0.1`) | Raises `DestinationSecurityException`; `0` packets transmitted |
| 10 | **Rate Limiting & Packet Caps** | Burst 200 traps against configured `rate_limit_pps` and `packet_cap = 50` | Token-bucket paces emission; burst halts cleanly at `50` packets with `packet_cap_exceeded = True` |
| 11 | **Receiver-Offline Truthfulness** | Send `TRAPv2 (0xA7)` to closed UDP port on `127.0.0.1` | State records `SENT` (OS socket send) and `RECEIVER_OBSERVED = False`; **UDP send is never reported as delivery** |
| 12 | **First Scenario Integration (`service_provider_cisco`)** | Execute `service_provider_cisco` in Native SNMP mode | Emits `IF-MIB::linkDown`, `BGP4-MIB::bgpBackwardTransition`, `IF-MIB::linkUp`, and `BGP4-MIB::bgpEstablished` PDUs + Companion Control Manifest |
| 13 | **Zero Platform Regression** | Run all existing Gate 1–11F tests (`235+` tests), `verify_sources.py`, and `validate_catalog.py` | `0 failures, 0 errors`; all 13 `GOLDEN_PATH_CERTIFIED` scenarios unchanged |

---

## 2. Independent Protocol Verification Strategy (Sections 32 & 33)

NetSpout's internal reference decoder may **never** be the sole judge of protocol correctness. Every SNMP gate must validate wire output against independent industry-standard tools:

| Tool | Gate Phase | Verification Role | Exact Command Pattern |
| :--- | :---: | :--- | :--- |
| **`TShark` / `Wireshark`** (`/opt/homebrew/bin/tshark`) | **Gate 12B, 12C, 12D, 12E** | Independent wire-level ASN.1 BER and SNMP PDU dissector | `tshark -r snmp_capture.pcap -V -Y "snmp"` |
| **Net-SNMP `snmptrapd`** | **Gate 12C** | Independent C reference trap/inform receiver & `Response-PDU (0xA2)` responder | `snmptrapd -f -Lo -c snmptrapd.conf udp:127.0.0.1:1162` |
| **Net-SNMP `snmpget`** | **Gate 12D** | Independent C client verifying `GetRequest (0xA0)` and `noSuchObject`/`noSuchInstance` | `snmpget -v2c -c netspout-lab 127.0.0.1:1161 1.3.6.1.2.1.2.2.1.8.1` |
| **Net-SNMP `snmpwalk`** | **Gate 12D** | Independent C client verifying lexicographic `GetNextRequest (0xA1)` traversal and `endOfMibView (0x82)` termination | `snmpwalk -v2c -c netspout-lab 127.0.0.1:1161 1.3.6.1.2.1.2.2.1` |
| **Net-SNMP `snmpbulkget` / `snmpbulkwalk`** | **Gate 12D** | Independent C client verifying `GetBulkRequest (0xA5)` (`non-repeaters`, `max-repetitions`) | `snmpbulkwalk -v2c -Cn0 -Cr10 -c netspout-lab 127.0.0.1:1161 1.3.6.1.2.1.2.2.1` |

### Required `TShark` Field Assertions (Section 33)
For every captured `TRAPv2` and `INFORM` packet, the automated test harness must parse `tshark -T json` or `-V` output and assert:
1. `snmp.version == "1"` (`version-2c`)
2. `snmp.community == "netspout-lab"`
3. `snmp.data == "7"` (`snmpV2-trap`) or `"6"` (`informRequest`) or `"2"` (`response`)
4. `snmp.request_id` matches the deterministic `request_id` in `CompanionControlManifest`
5. `snmp.name` list contains `1.3.6.1.2.1.1.3.0`, `1.3.6.1.6.3.1.1.4.1.0`, and expected scenario OIDs
6. `_ws.malformed` is absent (`Malformed warnings == 0`).

---

## 3. Comprehensive 14-Case Negative Test Plan (Section 31)

| Test ID | Negative Test Case | Input / Fault Condition | Expected Deterministic Behavior |
| :--- | :--- | :--- | :--- |
| **NEG-01** | **Malformed ASN.1 BER Envelope** | First byte is `0x31` (`SET`) or `0xFF` instead of `0x30` (`SEQUENCE`) | Decoder raises `SnmpBerDecodeError("Expected outer SEQUENCE tag 0x30")`; increments `decode_errors_total` |
| **NEG-02** | **Invalid OID Syntax** | OID string `"1.3.6.1.invalid.0"`, `".1.3.6"`, `"9.99.1"`, or fewer than 2 arcs | Validator raises `InvalidSnmpOidError` before encoding |
| **NEG-03** | **Invalid / Indefinite BER Length** | Length byte `0x80` (indefinite) or length `0x85` (>4 length octets) or length > remaining buffer | Decoder raises `SnmpBerDecodeError("Invalid or indefinite BER length")` without buffer over-read |
| **NEG-04** | **Truncated Packet** | Valid 127-byte `linkDown` trap truncated at byte 64 | Decoder raises `SnmpBerDecodeError("Truncated TLV value: expected N bytes, got M")` |
| **NEG-05** | **Wrong Community String** | Incoming `GET` or `INFORM` response carries `"wrong-community"` instead of `"netspout-lab"` | Rejected; increments `snmpInBadCommunityNames`; never updates state to `ACKNOWLEDGED` |
| **NEG-06** | **Receiver Unavailable (Trap & Inform)** | Target UDP listener on `127.0.0.1:1162` is stopped | `TRAP` records `SENT` only (`RECEIVER_OBSERVED = False`); `INFORM` retries `max_retries` times and records `INFORM_TIMEOUT` (`ACKNOWLEDGED = False`) |
| **NEG-07** | **Wrong UDP Port** | Send `INFORM` to closed/wrong port `127.0.0.1:19999` | Socket `ICMP Port Unreachable` / timeout caught cleanly; `inform_timeouts_total += 1`; health transitions to `RECEIVER_UNAVAILABLE` |
| **NEG-08** | **Duplicate `INFORM` Transmission** | Network drops ACK; sender retransmits identical `InformRequest` with same `request-id` | Receiver recognizes duplicate `request-id`, re-sends `Response-PDU (0xA2)`, and emits only **1** deduplicated event to Splunk |
| **NEG-09** | **`INFORM` Timeout & Late ACK** | Responder delays `Response-PDU` beyond `timeout_ms * (max_retries + 1)` or returns wrong `request-id` | Sender marks `INFORM` unacknowledged (`inform_timeouts_total += 1`); late/mismatched ACK is discarded (`late_ack_ignored_total += 1`) |
| **NEG-10** | **Unsupported SNMP Version** | Packet with `version = 0 (SNMPv1)` or `version = 99` sent to decoder | Decoder rejects with `UnsupportedSnmpVersionError`; increments `snmpInBadVersions` |
| **NEG-11** | **Unknown OID in Polling Request (Gate 12D)** | Poller sends `GetRequest` for `1.3.6.1.2.1.999.1.0` or missing instance `ifOperStatus.999` | Agent returns `Response-PDU (0xA2)` with `error-status = 0` and varbind exception tag `noSuchObject (0x80)` or `noSuchInstance (0x81)` per RFC 3416 |
| **NEG-12** | **Invalid VarBind Value Type** | Pass string `"abc"` to `Integer32`/`Counter64` varbind or negative integer `-5` to unsigned `Counter32`/`TimeTicks` | Encoder raises `SnmpValueTypeError` at construction time |
| **NEG-13** | **External Collector / Forwarder Unavailable (Gate 12C)** | `snmptrapd` is down while NetSpout sends traps | Pipeline stage halts at `SENT`; `RECEIVER_OBSERVED = False`, `SPLUNK_OBSERVED = False`; health state = `RECEIVER_UNAVAILABLE` |
| **NEG-14** | **Splunk HEC Unavailable (Gate 12C)** | `snmptrapd` receives and decodes trap, but Splunk HEC `:8888` is unreachable | Pipeline stage records `RECEIVER_OBSERVED = True` and `SPLUNK_OBSERVED = False`; health state = `SPLUNK_UNAVAILABLE` |

---

## 4. Planned Gate 12B Test Suite Files

When Gate 12B begins (after user approval of Gate 12), the following unit and protocol verification test suites will be created:
1. `tests/test_snmp_ber_encoder.py` — Tests all 10 ASN.1 BER primitive/application types, short/long definite lengths, VLQ OID encoding, sign-bit padding, and the 5 Golden Hex Fixtures.
2. `tests/test_snmp_negative_ber.py` — Executes `NEG-01` through `NEG-12` (malformed BER, truncated packets, indefinite length, deep recursion, invalid OIDs, wrong community, bad versions).
3. `tests/test_snmp_trap_inform_loopback.py` — Tests `TRAPv2 (0xA7)` and `InformRequest (0xA6)` $\rightarrow$ `Response (0xA2)` acknowledgement, retry, deduplication, timeout, and rate limiting over `127.0.0.1` loopback.
4. `tests/test_snmp_tshark_verification.py` — Independent `TShark` dissection of generated PCAPs asserting `0` malformed warnings and exact field extraction.
