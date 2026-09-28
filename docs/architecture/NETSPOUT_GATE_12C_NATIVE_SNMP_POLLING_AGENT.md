# NETSPOUT GATE 12C — NATIVE SNMPv2c POLLING AGENT ARCHITECTURE

## 1. Executive Summary

Gate 12C implements the canonical, bounded, read-only **Simulated SNMPv2c Polling Agent** (`src/netspout_core/snmp_agent.py`) for NetSpout. Building on the RFC 1155 / RFC 1901 / RFC 1905 / RFC 3416 ASN.1 BER codec (`src/netspout_core/snmp_ber.py`) introduced in Gate 12B, Gate 12C enables NetSpout to behave as a standards-compliant simulated SNMPv2c managed network device that external SNMP managers (`snmpget`, `snmpgetnext`, `snmpwalk`, `snmpbulkwalk`, and `TShark`) can query over local UDP (`127.0.0.1:1161`).

**NetSpout is simulating SNMP-managed network state. It is not claiming to emulate every behavior of physical Cisco hardware or every object in the vendor MIB ecosystem.**

**Gate 12C does not prove Splunk ingestion of native SNMP polling data.**

---

## 2. Canonical Module Inventory

| Module | Responsibility |
| :--- | :--- |
| `src/netspout_core/snmp_agent.py` | `SnmpOidStore`, numeric lexicographic OID helpers (`normalize_oid_str`, `oid_to_tuple`, `compare_oids`, `is_oid_in_subtree`), `build_service_provider_cisco_oid_store`, `verify_trap_poll_coherence`, `SimulatedSnmpAgent`, and `SnmpPollingClient` |
| `src/netspout_core/snmp_ber.py` | ASN.1 BER encoder/decoder supporting `GetRequest-PDU (0xA0)`, `GetNextRequest-PDU (0xA1)`, `Response-PDU (0xA2)`, `SetRequest-PDU (0xA3)`, `GetBulkRequest-PDU (0xA5)`, `SNMPv2-Trap-PDU (0xA7)`, `InformRequest-PDU (0xA6)`, and exception tags (`noSuchObject = 0x80`, `noSuchInstance = 0x81`, `endOfMibView = 0x82`) |
| `src/netspout_core/models.py` | `SnmpOidEntry`, `SnmpPollingEvidence`, `SnmpEvidenceStage` (`REQUEST_RECEIVED`, `REQUEST_DECODED`, `RESPONSE_GENERATED`, `RESPONSE_ENCODED`, `RESPONSE_SENT`, `MANAGER_OBSERVED`), and `CompanionControlManifest` polling metadata |
| `src/netspout_core/companion_manifest.py` | `CompanionManifestBuilder.build_snmp_polling_manifest()` for local companion polling agent orchestration |

---

## 3. Protocol Scope & PDU Semantics

The `SimulatedSnmpAgent` binds by default to `127.0.0.1:1161` (UDP, rootless high port) and enforces strict RFC 1905 / RFC 3416 semantics:

1. **Community Authentication (`community = "public"`):**
   - Requests with an invalid community string increment `authentication_failure_count` and are silently dropped per RFC 1901 / RFC 3416 standard behavior.
2. **Version Validation (`version = 1` for SNMPv2c):**
   - Requests with `version != 1` increment `unsupported_version_count` and are silently dropped.
3. **`GetRequest-PDU (0xA0)`:**
   - Exact OID match returns a `Response-PDU (0xA2)` with matching `request-id`, `error-status = 0`, `error-index = 0`, and the typed ASN.1 BER value.
   - Missing scalar or unknown prefix returns `noSuchObject (0x80)` in the VarBind slot (preserving `error-status = 0` per SNMPv2c rules).
   - Missing conceptual table instance under a registered column prefix returns `noSuchInstance (0x81)` in the VarBind slot.
4. **`GetNextRequest-PDU (0xA1)`:**
   - Strictly returns the next numeric lexicographic OID (`O_next > O_req`) in `SnmpOidStore`.
   - When `O_req` is greater than or equal to the final OID in the store, returns `endOfMibView (0x82)` at the requested OID without looping.
5. **`GetBulkRequest-PDU (0xA5)`:**
   - Decodes `non-repeaters (N)` and `max-repetitions (M)` (clamped to a safe ceiling of `64` and `4096` byte UDP payload limit).
   - Processes the first `N` VarBinds with a single `GETNEXT` step and the remaining `R` repeating VarBinds across up to `M` lexicographic repetitions, halting early on `endOfMibView (0x82)`.
6. **Read-Only `SetRequest-PDU (0xA3)` Rejection:**
   - Returns `Response-PDU (0xA2)` with `error-status = 17` (`notWritable`), `error-index = 1`, and leaves `SnmpOidStore` 100% unmutated.

---

## 4. Numeric Lexicographic OID Store (`SnmpOidStore`)

`SnmpOidStore` normalizes all OID strings via `normalize_oid_str()` and indexes them by integer component tuple `tuple(int(part) for part in oid.split("."))`.

- Numeric sorting ensures `(1, 3, 6, 1, 2, 1, 2, 2, 1, 1, 2) < (1, 3, 6, 1, 2, 1, 2, 2, 1, 1, 10)`, avoiding string-sorting bugs where `.10` precedes `.2`.
- All 127 OIDs for `service_provider_cisco` (`device_id="cisco-asr9k-pe1"`) are strictly ordered across four canonical MIB families:
  1. **`SNMPv2-MIB` (`1.3.6.1.2.1.1.*`)**: `sysDescr.0` through `sysName.0` (`7` scalar OIDs).
  2. **`IF-MIB` (`1.3.6.1.2.1.2.*` and `1.3.6.1.2.1.31.1.1.1.*`)**: `ifNumber.0` (`1` scalar), `ifTable` (`11` columns x `4` interfaces = `44` OIDs), and `ifXTable` (`8` columns x `4` interfaces = `32` OIDs, including 64-bit `Counter64` `ifHCInOctets`, `ifHCOutOctets`, `ifHCInUcastPkts`, `ifHCOutUcastPkts`, `ifHighSpeed`, and `ifAlias`).
  3. **`IP-MIB` (`1.3.6.1.2.1.4.24.4.1.*`)**: `ipCidrRouteStatus` (`1.3.6.1.2.1.4.24.4.1.4`) and `ipCidrRouteNextHop` (`1.3.6.1.2.1.4.24.4.1.5`) for active core forwarding verification (`2` OIDs).
  4. **`BGP4-MIB` (`1.3.6.1.2.1.15.*`)**: `bgpVersion.0`, `bgpLocalAs.0`, `bgpIdentifier.0` (`3` scalars) and `bgpPeerTable` (`19` columns x `2` peers `10.0.0.2` and `10.0.0.6` = `38` OIDs).

---

## 5. Scenario Phase State Coherence (`service_provider_cisco`)

The OID store transitions deterministically across the four canonical scenario phases of `service_provider_cisco` (`device_id="cisco-asr9k-pe1"`), maintaining 100% state coherence with Gate 12B Traps/Informs:

| Metric / OID | `BASELINE` | `DEGRADE` | `FAILOVER` | `RECOVERY` |
| :--- | :--- | :--- | :--- | :--- |
| `sysUpTime.0` (`1.3.6.1.2.1.1.3.0`) | `12450000` | `12456000` | `12462000` | `12468000` |
| `ifOperStatus.1` (`TenGigE0/0/0/0`) | `1` (`up`) | `1` (`up`) | `2` (`down`) | `1` (`up`) |
| `ifInErrors.1` (`1.3.6.1.2.1.2.2.1.14.1`) | `0` | `285` | `1420` | `1420` |
| `bgpPeerState.10.0.0.2` (Primary Core Peer) | `6` (`established`) | `6` (`established`) | `1` (`idle`) | `6` (`established`) |
| `bgpPeerLastError.10.0.0.2` | `0x0000` | `0x0000` | `0x0400` (Hold Timer) | `0x0000` |
| `bgpPeerState.10.0.0.6` (Backup Core Peer) | `6` (`established`) | `6` (`established`) | `6` (`established`) | `6` (`established`) |
| `ipCidrRouteNextHop` (`10.200.0.0/16`) | `10.0.0.2` | `10.0.0.2` | `10.0.0.6` | `10.0.0.2` |

`verify_trap_poll_coherence()` programmatically proves that:
- `FAILOVER` `linkDown` and `bgpBackwardTransition` traps match polled `ifOperStatus.1 = 2 (down)`, `bgpPeerState.10.0.0.2 = 1 (idle)`, `bgpPeerLastError.10.0.0.2 = 0x0400`, and backup route `10.0.0.6`.
- `RECOVERY` `linkUp` and `bgpEstablished` traps match polled `ifOperStatus.1 = 1 (up)`, `bgpPeerState.10.0.0.2 = 6 (established)`, and restored primary route `10.0.0.2`.
