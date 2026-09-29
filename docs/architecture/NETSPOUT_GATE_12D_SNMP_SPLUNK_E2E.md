# NetSpout Gate 12D — External SNMP Collector/Poller to Splunk End-to-End Architecture

## 1. Overview & Architectural Boundary

Gate 12D connects the native SNMPv2c notification transport (Gate 12B) and the simulated SNMPv2c managed-device polling agent (Gate 12C) to **real external Net-SNMP OS binaries** and **live Splunk Enterprise ingestion, SPL search reconstruction, and scenario contract validation** for the canonical scenario `service_provider_cisco` (`cisco-asr9k-pe1`).

Gate 12D proves the complete end-to-end boundary:

```text
Native SNMPv2c Wire (ASN.1 BER / UDP)
  --> External Net-SNMP Component (/usr/sbin/snmptrapd & /usr/bin/snmp*)
  --> Out-of-Band Collector/Poller Normalizer (SnmpCollectorNormalizer)
  --> Splunk HEC (index="idx_network_ops", sourcetypes="netspout:snmp:trap" | "netspout:snmp:poll")
  --> Fresh Splunk REST Search (/services/search/jobs/export)
  --> NetSpout Scenario Contract & Trap/Poll Coherence Validator
```

### Dual Pipeline Architecture

1. **Pipeline A — Native SNMP Notifications (`TRAP` & `INFORM`)**
   ```text
   NetSpout Scenario (service_provider_cisco)
     --> Native ASN.1 BER Encoder (SnmpBerEncoder)
     --> SNMPv2c Trap (0xA7) & InformRequest (0xA6) over UDP
     --> External SNMP Receiver (/usr/sbin/snmptrapd)
         [Returns RFC 3416 Response-PDU (0xA2) for InformRequest]
     --> SnmpCollectorNormalizer (sourcetype="netspout:snmp:trap")
     --> Splunk HEC (index="idx_network_ops")
     --> Fresh SPL Search
     --> NetSpout Validation
   ```

2. **Pipeline B — External SNMP Polling (`GET` / `GETNEXT` / `GETBULK` / Walk)**
   ```text
   External Net-SNMP Poller (/usr/bin/snmpget, /usr/bin/snmpgetnext, /usr/bin/snmpwalk, /usr/bin/snmpbulkwalk)
     --> GetRequest (0xA0) / GetNextRequest (0xA1) / GetBulkRequest (0xA5) over UDP
     --> NetSpout SimulatedSnmpAgent (MIB-II + IF-MIB + IP-MIB + BGP4-MIB)
     --> Response-PDU (0xA2) over UDP
     --> SnmpCollectorNormalizer (sourcetype="netspout:snmp:poll")
     --> Splunk HEC (index="idx_network_ops")
     --> Fresh SPL Search
     --> NetSpout Validation
   ```

---

## 2. External Trap/Inform Receiver Setup (`/usr/sbin/snmptrapd`)

`ExternalSnmpTrapReceiver` ([`src/netspout_core/snmp_splunk_e2e.py`](../../src/netspout_core/snmp_splunk_e2e.py)) manages a real external OS process (`/usr/sbin/snmptrapd`, Net-SNMP 5.6.2.1):

- **Rootless Local Execution:** Binds to an ephemeral or configured local loopback UDP port (`udp:127.0.0.1:<port>`) using an isolated temporary `snmptrapd.conf` containing `disableAuthorization yes`.
- **Command Flags:**
  ```bash
  /usr/sbin/snmptrapd -f -C -c <snmptrapd.conf> -Lf <snmptrapd.log> -p <snmptrapd.pid> -d -On -OQ -Oe -Ot udp:127.0.0.1:<port>
  ```
  - `-d`: Dumps raw incoming (`Received ... bytes from UDP:`) and outgoing (`Sending ... bytes to UDP:`) UDP packet hex frames, enabling independent wire-level BER decoding and PCAP export.
  - `-On`: Prints OIDs numerically.
  - `-OQ`: Prints simplified `OID = value` formatting.
  - `-Oe`: Prints MIB integer enumerations numerically (`1` for `up`, `2` for `down`, `6` for `established`).
  - `-Ot`: Prints `TimeTicks` as unformatted numeric integers.
- **Native Inform Acknowledgement & Deduplication:**
  - When `NativeSnmpTransport` transmits an `InformRequest-PDU (0xA6)`, `/usr/sbin/snmptrapd` natively generates and returns a real RFC 3416 `Response-PDU (0xA2)` preserving the exact `request-id`.
  - If an `InformRequest` is retried or duplicated on the wire, `ExternalSnmpTrapReceiver.parse_snmptrapd_log_text()` deduplicates repeated deliveries by `(src_ip, request_id)` and increments `duplicate_informs_suppressed`.

---

## 3. External Polling Setup (`net-snmp` CLI Suite)

`ExternalNetSnmpPoller` ([`src/netspout_core/snmp_splunk_e2e.py`](../../src/netspout_core/snmp_splunk_e2e.py)) invokes real external Net-SNMP binaries over UDP against `SimulatedSnmpAgent`:

- `/usr/bin/snmpget -v2c -c public -t 2 -r 1 -On -OQ -Oe -Ot 127.0.0.1:<port> <OID...>`
- `/usr/bin/snmpgetnext -v2c -c public -t 2 -r 1 -On -OQ -Oe -Ot 127.0.0.1:<port> <OID...>`
- `/usr/bin/snmpwalk -v2c -c public -t 2 -r 1 -On -OQ -Oe -Ot 127.0.0.1:<port> 1.3.6.1.2.1`
- `/usr/bin/snmpbulkwalk -v2c -c public -t 2 -r 1 -On -OQ -Oe -Ot -Cr10 127.0.0.1:<port> 1.3.6.1.2.1`

Across each phase of `service_provider_cisco` (`BASELINE -> DEGRADE -> FAILOVER -> RECOVERY`), the external poller queries key operational OIDs (`PHASE_POLL_OIDS`) via `snmpget` and `snmpgetnext`, and performs full 127-OID MIB walks (`snmpwalk` and `snmpbulkwalk`) during `BASELINE` and `FAILOVER`. If the agent is unreachable, `ExternalNetSnmpPoller` records the timeout error and never fabricates poll results.

---

## 4. Normalized Splunk Event Model & Out-of-Band Run Correlation

### Wire Purity vs. Out-of-Band Collector Enrichment

NetSpout strictly forbids injecting proprietary NetSpout correlation varbinds onto the native SNMPv2c wire. Every UDP packet on the wire contains only RFC-compliant `SNMPv2-MIB`, `IF-MIB`, `IP-MIB`, and `BGP4-MIB` OIDs (`1.3.6.1.2.1.*` and `1.3.6.1.6.3.*`).

Run correlation metadata is attached **out-of-band** by `SnmpCollectorNormalizer` at the collector/poller normalization boundary using the run's `request_id -> phase` lookup table for notifications and the active polling phase context for polls.

### Target Index & Sourcetypes

- **Splunk Index:** `idx_network_ops`
- **Notification Sourcetype:** `netspout:snmp:trap`
- **Polling Sourcetype:** `netspout:snmp:poll`

### Normalized Event Schema (`NormalizedSnmpEvent`)

| Field | Type | Description |
| :--- | :--- | :--- |
| `netspout_run_id` | `str` | Unique run identifier isolating Splunk evidence per run |
| `netspout_scenario_id` | `str` | Canonical scenario ID (`service_provider_cisco`) |
| `netspout_phase` | `str` | Canonical phase (`BASELINE`, `DEGRADE`, `FAILOVER`, `RECOVERY`) |
| `netspout_device_id` | `str` | Simulated device identifier (`cisco-asr9k-pe1`) |
| `netspout_event_id` | `str` | Deterministic deduplication event ID (`snmp-trap-...` / `snmp-poll-...`) |
| `snmp_version` | `str` | `"2c"` |
| `snmp_pdu_type` | `str` | `"SNMPv2-Trap"`, `"InformRequest"`, `"GetRequest"`, `"GetNextRequest"`, or `"GetBulkRequest"` |
| `snmp_request_id` | `Optional[int]` | Wire `request-id` for notifications |
| `snmp_trap_oid` | `Optional[str]` | Numeric `snmpTrapOID.0` value for notifications (`None` for polls) |
| `snmp_trap_name` | `Optional[str]` | Symbolic notification name (`IF-MIB::linkDown`, `BGP4-MIB::bgpBackwardTransition`, `IF-MIB::linkUp`, `BGP4-MIB::bgpEstablished`) |
| `snmp_oid` | `str` | Primary numeric OID |
| `snmp_oid_name` | `str` | Symbolic MIB OID name (`IF-MIB::ifOperStatus.1`, `BGP4-MIB::bgpPeerState.198.51.100.1`, etc.) |
| `snmp_value` | `str` | Normalized string value |
| `snmp_numeric_value` | `Optional[float]` | Parsed numeric value when applicable |
| `snmp_value_type` | `str` | ASN.1 type (`Integer32`, `Counter32`, `Counter64`, `Gauge32`, `TimeTicks`, `IpAddress`, `OctetString`, `ObjectIdentifier`) |
| `snmp_source` | `str` | Source IP (`127.0.0.1`) |
| `snmp_collector` | `str` | `"snmptrapd"` or `"net-snmp-cli"` |
| `snmp_transport` | `str` | `"SNMPV2C_UDP"` |
| `evidence_stage` | `str` | Current evidence lifecycle stage |
| `sys_uptime` | `Optional[int]` | `sysUpTime.0` hundredths of seconds for notifications |
| `varbinds` | `Dict[str, Any]` | Symbolic varbind map |
| `raw_collector_line` | `str` | Raw line emitted by `snmptrapd` or `net-snmp` CLI |
| `telemetry_semantics` | `str` | `"NATIVE TRANSPORT / MODELED DEVICE STATE"` |

---

## 5. Canonical SPL Investigation Reference

`build_snmp_investigation_queries(run_id, index="idx_network_ops")` generates 7 copyable, executable SPL queries:

1. **All SNMP Evidence for a Run (`all_snmp_evidence_spl`):**
   ```spl
   search index=idx_network_ops (sourcetype="netspout:snmp:trap" OR sourcetype="netspout:snmp:poll") netspout_run_id="<RUN_ID>" | table _time netspout_phase sourcetype snmp_pdu_type snmp_request_id snmp_trap_name snmp_oid_name snmp_value snmp_collector
   ```
2. **Trap & Inform Evidence (`trap_inform_evidence_spl`):**
   ```spl
   search index=idx_network_ops sourcetype="netspout:snmp:trap" netspout_run_id="<RUN_ID>" | table _time netspout_phase snmp_pdu_type snmp_request_id snmp_trap_name snmp_trap_oid snmp_oid_name snmp_value sys_uptime
   ```
3. **Polling Evidence (`polling_evidence_spl`):**
   ```spl
   search index=idx_network_ops sourcetype="netspout:snmp:poll" netspout_run_id="<RUN_ID>" | table _time netspout_phase snmp_pdu_type snmp_oid_name snmp_oid snmp_value snmp_value_type
   ```
4. **Scenario Phase Timeline (`timeline_spl`):**
   ```spl
   search index=idx_network_ops (sourcetype="netspout:snmp:trap" OR sourcetype="netspout:snmp:poll") netspout_run_id="<RUN_ID>" | stats count as evidence_count values(sourcetype) as sourcetypes values(snmp_pdu_type) as pdu_types values(snmp_trap_name) as notifications by netspout_phase
   ```
5. **Interface State Progression (`interface_state_spl`):**
   ```spl
   search index=idx_network_ops (sourcetype="netspout:snmp:trap" OR sourcetype="netspout:snmp:poll") netspout_run_id="<RUN_ID>" (snmp_oid="1.3.6.1.2.1.2.2.1.8.1" OR snmp_oid="1.3.6.1.2.1.2.2.1.14.1" OR snmp_trap_oid="1.3.6.1.6.3.1.1.5.3" OR snmp_trap_oid="1.3.6.1.6.3.1.1.5.4") | table _time netspout_phase sourcetype snmp_pdu_type snmp_trap_name snmp_oid_name snmp_value
   ```
6. **BGP Peer State Progression (`bgp_state_spl`):**
   ```spl
   search index=idx_network_ops (sourcetype="netspout:snmp:trap" OR sourcetype="netspout:snmp:poll") netspout_run_id="<RUN_ID>" (snmp_oid="1.3.6.1.2.1.15.3.1.2.198.51.100.1" OR snmp_oid="1.3.6.1.2.1.15.3.1.14.198.51.100.1" OR snmp_oid="1.3.6.1.2.1.15.3.1.2.198.51.100.2" OR snmp_trap_oid="1.3.6.1.2.1.15.7.2" OR snmp_trap_oid="1.3.6.1.2.1.15.7.1") | table _time netspout_phase sourcetype snmp_pdu_type snmp_trap_name snmp_oid_name snmp_value
   ```
7. **Notification vs. Poll State Correlation (`notification_vs_poll_correlation_spl`):**
   ```spl
   search index=idx_network_ops (sourcetype="netspout:snmp:trap" OR sourcetype="netspout:snmp:poll") netspout_run_id="<RUN_ID>" | stats count(eval(sourcetype="netspout:snmp:trap")) as notification_count count(eval(sourcetype="netspout:snmp:poll")) as poll_count values(snmp_trap_name) as notifications values(eval(if(sourcetype="netspout:snmp:poll", snmp_oid_name."=".snmp_value, null()))) as polled_states by netspout_phase
   ```

---

## 6. Scenario Validation Contract & Trap/Poll State Coherence

`SnmpSplunkE2EOrchestrator.validate_splunk_evidence()` evaluates four strict contract gates exclusively against **fresh Splunk search results** filtered by `netspout_run_id`:

1. **`run_correlation_isolation`:** Zero foreign records (`netspout_run_id != run_id`) and `matched_records > 0`.
2. **`all_four_phases_present`:** All four canonical phases (`BASELINE`, `DEGRADE`, `FAILOVER`, `RECOVERY`) are observed in Splunk.
3. **`required_notifications_observed`:** Both `SNMPv2-Trap` and `InformRequest` PDU types and all four required notification OIDs (`1.3.6.1.6.3.1.1.5.3`, `1.3.6.1.2.1.15.7.2`, `1.3.6.1.6.3.1.1.5.4`, `1.3.6.1.2.1.15.7.1`) are observed in Splunk.
4. **`trap_poll_state_coherence`:** Nine cross-pipeline coherence invariants between `netspout:snmp:trap` and `netspout:snmp:poll`:
   - `baseline_if_up`: `ifOperStatus.1 == 1` (`up`)
   - `baseline_bgp_est`: `bgpPeerState.198.51.100.1 == 6` (`established`)
   - `degrade_if_down_matches_linkDown_trap`: `ifOperStatus.1 == 2` (`down`) AND `IF-MIB::linkDown` (`1.3.6.1.6.3.1.1.5.3`) observed
   - `degrade_if_errors_elevated`: `ifInErrors.1 > 0` (`48`)
   - `failover_bgp_idle_matches_bgpBackwardTransition_trap`: `bgpPeerState.198.51.100.1 == 1` (`idle`) AND `BGP4-MIB::bgpBackwardTransition` (`1.3.6.1.2.1.15.7.2`) observed
   - `failover_backup_route_active`: `ipRouteNextHop.0.0.0.0 == 198.51.100.2` AND `bgpPeerState.198.51.100.2 == 6`
   - `recovery_if_up_matches_linkUp_trap`: `ifOperStatus.1 == 1` (`up`) AND `IF-MIB::linkUp` (`1.3.6.1.6.3.1.1.5.4`) observed
   - `recovery_bgp_est_matches_bgpEstablished_trap`: `bgpPeerState.198.51.100.1 == 6` (`established`) AND `BGP4-MIB::bgpEstablished` (`1.3.6.1.2.1.15.7.1`) observed
   - `recovery_primary_route_restored`: `ipRouteNextHop.0.0.0.0 == 198.51.100.1`

---

## 7. Strict 8-Stage Evidence State Model & Controlled Failure Modes

Gate 12D enforces strict separation across eight non-collapsible evidence stages:

1. `GENERATED`: PDUs/OID states constructed in memory.
2. `ENCODED`: ASN.1 BER wire bytes encoded and verified.
3. `SENT`: UDP datagrams transmitted on loopback socket.
4. `ACKNOWLEDGED`: `InformRequest (0xA6)` acknowledged via `Response-PDU (0xA2)` from `/usr/sbin/snmptrapd`.
5. `RECEIVER_OBSERVED`: External `/usr/sbin/snmptrapd` and/or `/usr/bin/snmp*` CLI observed and decoded the SNMP wire traffic.
6. `SPLUNK_DISPATCHED`: Normalized `netspout:snmp:trap` and `netspout:snmp:poll` payloads accepted with HTTP 200 by Splunk HEC.
7. `SPLUNK_OBSERVED`: Fresh Splunk REST search (`/services/search/jobs/export`) returned indexed events matching `netspout_run_id`.
8. `VALIDATED`: All scenario contract and Trap/Poll state coherence checks passed against Splunk-observed records.

### Controlled Failure Modes

- **Failure A (SNMP Receiver Unavailable):** `SENT = YES`, `ACKNOWLEDGED = NO`, `RECEIVER_OBSERVED = NO`, `SPLUNK_OBSERVED = NO`, `validation_result = FAIL`.
- **Failure B (Receiver Up, Splunk Down / HEC Unreachable):** `RECEIVER_OBSERVED = YES`, `SPLUNK_DISPATCHED = NO`, `SPLUNK_OBSERVED = NO`, `validation_result = FAIL`.
- **Failure C (SNMP Agent Unreachable During Poll):** External poller records timeout, `polling_responses = 0`, `splunk_observed_poll_records = 0` (zero fabricated records), `validation_result = FAIL`.
- **Failure D (Missing Scenario Phase):** Suppressing `RECOVERY` produces partial Splunk evidence (`306` records across 3 phases) and fails `all_four_phases_present` and `trap_poll_state_coherence`.
- **Failure E (Duplicate / Retried Inform):** Re-transmitting identical `InformRequest` PDUs (`request_id` preserved) is deterministically deduplicated at both `ExternalSnmpTrapReceiver` (`duplicate_informs_suppressed = 4`) and `SnmpCollectorNormalizer` (`duplicate_events_suppressed = 4`).

---

## 8. Product Truth Boundaries

- **Wire Protocol:** Real RFC 3416 / RFC 1905 ASN.1 BER over UDP (`SNMPv2c`), verified by external `/usr/sbin/snmptrapd`, `/usr/bin/snmpget`, `/usr/bin/snmpgetnext`, `/usr/bin/snmpwalk`, `/usr/bin/snmpbulkwalk`, and `/opt/homebrew/bin/tshark`.
- **Device State:** Deterministic, scenario-driven modeled router state (`NATIVE TRANSPORT / MODELED DEVICE STATE`), not a hardware ASIC or full NOS control-plane emulator.
