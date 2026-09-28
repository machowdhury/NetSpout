# NETSPOUT GATE 12C — NATIVE SNMPv2c POLLING AGENT & OID WALK VERIFICATION

## 1. Verification Summary

Gate 12C (`Native SNMPv2c Polling Agent, GET/GETNEXT/GETBULK & OID Walk`) has been implemented and independently verified against external Net-SNMP CLI utilities (`/usr/bin/snmpget`, `/usr/bin/snmpgetnext`, `/usr/bin/snmpwalk`, `/usr/bin/snmpbulkwalk`) and `TShark` (`/opt/homebrew/bin/tshark`).

**NetSpout is simulating SNMP-managed network state. It is not claiming to emulate every behavior of physical Cisco hardware or every object in the vendor MIB ecosystem.**

**Gate 12C does not prove Splunk ingestion of native SNMP polling data.**

---

## 2. Independent External Tool Verification

| Tool | Binary Path | Version | Status | Evidence Artifact |
| :--- | :--- | :--- | :--- | :--- |
| `snmpget` | `/usr/bin/snmpget` | `NET-SNMP version: 5.9.4` | **VERIFIED** | `docs/acceptance/evidence/gate12c/external_snmpget_output.txt` |
| `snmpgetnext` | `/usr/bin/snmpgetnext` | `NET-SNMP version: 5.9.4` | **VERIFIED** | `docs/acceptance/evidence/gate12c/external_snmpgetnext_output.txt` |
| `snmpwalk` | `/usr/bin/snmpwalk` | `NET-SNMP version: 5.9.4` | **VERIFIED** | `docs/acceptance/evidence/gate12c/external_snmpwalk_output.txt` |
| `snmpbulkwalk` | `/usr/bin/snmpbulkwalk` | `NET-SNMP version: 5.9.4` | **VERIFIED** | `docs/acceptance/evidence/gate12c/external_snmpbulkwalk_output.txt` |
| `tshark` | `/opt/homebrew/bin/tshark` | `TShark (Wireshark) 4.4.5` | **VERIFIED (`0` malformed warnings)** | `docs/acceptance/evidence/gate12c/tshark_verbose_output.txt` |

### Key External CLI Verification Results
1. **External `snmpget` (`127.0.0.1:1161`):**
   - Polled `sysDescr.0`, `sysObjectID.0`, `sysUpTime.0`, `sysName.0`, `ifOperStatus.1`, `ifHCInOctets.1`, and `bgpPeerState.10.0.0.2`.
   - Verified `No Such Object available on this agent at this OID` (`0x80`) for `1.3.6.1.2.1.999.1.0`.
   - Verified `No Such Instance currently exists at this OID` (`0x81`) for `1.3.6.1.2.1.2.2.1.8.999`.
2. **External `snmpgetnext` (`127.0.0.1:1161`):**
   - Verified root traversal `1.3.6.1.2.1` -> `1.3.6.1.2.1.1.1.0` (`sysDescr.0`).
   - Verified numeric lexicographic ordering across `ifIndex` and `ifOperStatus`.
   - Verified `No more variables left in this MIB View (It is past the end of the MIB tree)` (`0x82`) at the final OID `1.3.6.1.2.1.31.1.1.1.18.4`.
3. **External `snmpwalk` & `snmpbulkwalk` (`127.0.0.1:1161`):**
   - Full subtree walk of `1.3.6.1.2.1` returned all **127 OIDs** in identical numeric lexicographic order and terminated cleanly without infinite loops.

---

## 3. Packet Capture (`PCAP`) & TShark Dissection Evidence

Four independent packet captures were recorded and dissected with `tshark -r <file> -V`:
1. `docs/acceptance/evidence/gate12c/gate12c_get.pcap` (`get-request` + `get-response`)
2. `docs/acceptance/evidence/gate12c/gate12c_getnext.pcap` (`get-next-request` + `get-response`)
3. `docs/acceptance/evidence/gate12c/gate12c_getbulk.pcap` (`getBulkRequest` + `get-response`)
4. `docs/acceptance/evidence/gate12c/gate12c_walk.pcap` (Full 127-OID walk + terminal `endOfMibView`)

Across all four PCAP files, `TShark` reported **0 malformed packet warnings** and **0 BER decode errors**.

---

## 4. Scenario Phase Transitions & Trap/Poll State Coherence

Full phase snapshots and coherence proofs are stored in:
- `docs/acceptance/evidence/gate12c/oid_tree_snapshot.json`
- `docs/acceptance/evidence/gate12c/service_provider_cisco_phase_snapshots.json`
- `docs/acceptance/evidence/gate12c/state_coherence_evidence.json`
- `docs/acceptance/evidence/gate12c/controlled_failure_evidence.json`

### Verified Coherence Invariants (`service_provider_cisco` / `cisco-asr9k-pe1`)
- **`BASELINE`:** `ifOperStatus.1 = 1 (up)`, `ifInErrors.1 = 0`, `bgpPeerState.10.0.0.2 = 6 (established)`, active route next-hop `10.0.0.2`.
- **`DEGRADE`:** `ifOperStatus.1 = 1 (up)`, `ifInErrors.1 = 285` (rising input errors), `bgpPeerState.10.0.0.2 = 6 (established)`, `sysUpTime.0` monotonically increased (`12450000 -> 12456000`).
- **`FAILOVER`:** Matches `linkDown` and `bgpBackwardTransition` traps: `ifOperStatus.1 = 2 (down)`, `bgpPeerState.10.0.0.2 = 1 (idle)`, `bgpPeerLastError.10.0.0.2 = 0400`, backup peer `10.0.0.6` remains `6 (established)`, and active route next-hop shifts to `10.0.0.6`.
- **`RECOVERY`:** Matches `linkUp` and `bgpEstablished` traps: `ifOperStatus.1 = 1 (up)`, `bgpPeerState.10.0.0.2 = 6 (established)`, `bgpPeerLastError.10.0.0.2 = 0000`, and active route next-hop restores to `10.0.0.2`.

---

## 5. Performance Benchmark Summary

Measured on `127.0.0.1` (`docs/acceptance/evidence/gate12c/performance_summary.json`):
- **`GET` Throughput:** `4,604.1 req/sec`
- **`GETNEXT` Throughput:** `7,565.0 req/sec`
- **`GETBULK` Throughput (`max-repetitions=10`):** `1,997.1 req/sec`
- **Average Latency:** `0.283 ms`
- **p95 Latency:** `0.516 ms`
- **Peak CPU:** `88.0%` (single worker thread during synthetic burst)
- **Peak RSS Memory:** `39.16 MB`

---

## 6. Automated Test Coverage

- **Gate 12C Dedicated Test Suite (`tests/test_gate12c_snmp_polling.py`):** `40 / 40` tests passing.
- **Full Repository Regression Suite:** `301 / 301` tests passing (`261` prior tests + `40` Gate 12C tests).
