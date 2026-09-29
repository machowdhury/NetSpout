# NETSPOUT GATE 12E — INDEPENDENT SNMP ACCEPTANCE SCORECARD

**Determination:** `PASS WITH FRICTION` (`NATIVE_SNMP_ACCEPTED_WITH_FRICTION`)

**Fresh Run ID:** `NS-20260929-6f40774b`

**Scenario:** `service_provider_cisco`

**Application Files Modified:** `NO`

## Customer Journey

**Scenario Discoverable:** `YES`

**Connection Preflight:** `PASS` (via CLI/env; UI preflight panel covers HEC & Native Flow only — `F-12E-02`)

**Scenario Execution:** `PASS` (via `ScenarioRunner` Python API; `FAIL` via HTTP `POST /api/scenarios/service_provider_cisco/run` due to `F-12E-01`)

**Splunk Investigation:** `PASS`

**Developer Knowledge Required:** `YES` (required to trigger `native_snmp_e2e=True` via Python because `POST /api/scenarios/{scenario_id}/run` drops native SNMP fields — `F-12E-01`)

**Meaningful Interactions:** `4`

**Time-to-Validated-Evidence:** `14.251s` (`9.360s` scenario & native SNMP E2E execution + `4.891s` fresh 8-query SPL reconstruction)

## Native SNMP

**Native SNMPv2c Transport:** `PASS` (RFC 3416 / RFC 1905 over local UDP)

**ASN.1 BER:** `PASS` (`592` frames dissected by `/opt/homebrew/bin/tshark`, `0` malformed packets)

**External snmptrapd:** `PASS` (`/usr/sbin/snmptrapd` Net-SNMP `5.6.2.1`)

**External Net-SNMP Polling:** `PASS` (`/usr/bin/snmpget`, `/usr/bin/snmpgetnext`, `/usr/bin/snmpwalk`, `/usr/bin/snmpbulkwalk` Net-SNMP `5.6.2.1`)

**TRAP Evidence:** `PASS` (`4` generated, `4` sent, `4` observed by `/usr/sbin/snmptrapd`, `4` observed in Splunk)

**INFORM Evidence:** `PASS` (`4` generated, `4` sent, `4` observed by `/usr/sbin/snmptrapd`, `4` observed in Splunk)

**INFORM ACK:** `PASS` (`4/4` acknowledged by `/usr/sbin/snmptrapd` via RFC 3416 `Response-PDU (0xA2)`)

**GET:** `PASS` (`4` requests / `4` responses across `BASELINE`, `DEGRADE`, `FAILOVER`, `RECOVERY`)

**GETNEXT:** `PASS` (`260` requests / `260` responses)

**GETBULK:** `PASS` (`26` requests / `26` responses with `-Cr10`)

**Walk:** `PASS` (`127` OIDs under `1.3.6.1.2.1`; `snmpwalk` and `snmpbulkwalk` match 100%)

## Evidence Pipeline

**Generated:** `8` notifications (`4` Traps + `4` Informs) + `127` exposed MIB OIDs per phase (`YES`)

**Encoded:** `8` notification PDUs + `290` polling Response-PDUs (`YES`)

**Sent:** `8` notification UDP datagrams + `290` polling Response UDP datagrams (`YES`)

**Acknowledged:** `4/4` InformRequests acknowledged via `Response-PDU (0xA2)` (`YES`)

**Receiver Observed:** `8` notifications observed by `/usr/sbin/snmptrapd` + `290` polling responses observed by Net-SNMP CLI (`YES`)

**Splunk Dispatched:** `326` normalized events (`8` `netspout:snmp:trap` + `318` `netspout:snmp:poll`) accepted by Splunk HEC (`YES`)

**Splunk Observed:** `326/326` events (`100.0%`) verified via fresh Splunk REST SPL searches for `netspout_run_id="NS-20260929-6f40774b"` (`YES`)

**Validated:** `PASS` (`4/4` contract checks and `9/9` Trap/Poll coherence invariants passed) (`YES`)

**False Evidence Equivalence Found:** `NO` (UDP `sendto()`, Inform ACK, receiver observation, HEC HTTP 200, and fresh SPL search observation are strictly separated)

## Operational Story

**BASELINE:** `PASS` (`ifOperStatus.1=1`, `ifInErrors.1=0`, `bgpPeerState.198.51.100.1=6`, `ipRouteNextHop.0.0.0.0=198.51.100.1`)

**DEGRADE:** `PASS` (`IF-MIB::linkDown` `1.3.6.1.6.3.1.1.5.3` + polled `ifOperStatus.1=2`, `ifInErrors.1=48`, `sysUpTime.0=8641000`)

**FAILOVER:** `PASS` (`BGP4-MIB::bgpBackwardTransition` `1.3.6.1.2.1.15.7.2` + polled `bgpPeerState.198.51.100.1=1`, `bgpPeerLastError.198.51.100.1=0400`, backup `bgpPeerState.198.51.100.2=6`, `ipRouteNextHop.0.0.0.0=198.51.100.2`, `ipRouteIfIndex.0.0.0.0=2`)

**RECOVERY:** `PASS` (`IF-MIB::linkUp` `1.3.6.1.6.3.1.1.5.4` + `BGP4-MIB::bgpEstablished` `1.3.6.1.2.1.15.7.1` + polled `ifOperStatus.1=1`, `bgpPeerState.198.51.100.1=6`, `bgpPeerFsmEstablishedTransitions.198.51.100.1=2`, `ipRouteNextHop.0.0.0.0=198.51.100.1`, `ipRouteIfIndex.0.0.0.0=1`)

**Trap/Poll Coherence:** `PASS` (`9/9` coherence checks `true`)

**Route Failover Evidence:** `PASS` (`ipRouteNextHop.0.0.0.0` `198.51.100.1 -> 198.51.100.2` and `ipRouteIfIndex.0.0.0.0` `1 -> 2` in `FAILOVER`)

**Recovery Evidence:** `PASS` (`ipRouteNextHop.0.0.0.0` `198.51.100.2 -> 198.51.100.1`, `ifOperStatus.1=1`, `bgpPeerState.198.51.100.1=6` in `RECOVERY`)

## Splunk

**Trap Sourcetype:** `netspout:snmp:trap` (`8` events)

**Poll Sourcetype:** `netspout:snmp:poll` (`318` events)

**Index:** `idx_network_ops`

**Run Correlation:** `PASS` (`netspout_run_id="NS-20260929-6f40774b"`, `netspout_scenario_id="service_provider_cisco"`, `netspout_phase`, `netspout_device_id="cisco-asr9k-pe1"`, `netspout_event_id`; zero proprietary varbinds on the SNMP wire)

**Fresh SPL Reconstruction:** `PASS` (All `8` customer-facing SPL queries executed against `NS-20260929-6f40774b`: counts `326`, `8`, `318`, `20`, `22`, `12`, `4`, `1`)

**Developer Knowledge Required for SPL:** `NO`

## Semantics

**Native Transport / Modeled State Distinction:** `YES` (`telemetry_semantics="NATIVE TRANSPORT / MODELED DEVICE STATE"` in events/scorecard; catalog card still shows Mode A `MODELED PAYLOAD` — `F-12E-02`)

**Evidence-Stage Semantics:** `SEMANTIC_DEFECT` (`F-12E-03`: per-event `evidence_stage` is serialized to HEC as `"RECEIVER_OBSERVED"` before dispatch, so events queried inside Splunk still carry `evidence_stage="RECEIVER_OBSERVED"` instead of distinguishing `origin_evidence_stage` from `current_evidence_stage`)

**Customer Claim Supported:** `YES`

## Controlled Failures

**Receiver Down:** `PASS` (`SENT=YES`, `ACKNOWLEDGED=NO`, `RECEIVER_OBSERVED=NO`, `SPLUNK_OBSERVED=NO`, `VALIDATED=NO`)

**Splunk Down:** `PASS` (`RECEIVER_OBSERVED=YES`, `SPLUNK_DISPATCHED=NO`, `SPLUNK_OBSERVED=NO`, `VALIDATED=NO`)

**Agent Unreachable:** `PASS` (Poller timeout recorded, `polling_responses=0`, `splunk_observed_poll_records=0`, zero fabricated poll records)

**Missing Phase:** `PASS` (`RECOVERY` suppressed -> `observed_phases=["BASELINE","DEGRADE","FAILOVER"]`, `validation_result=FAIL`)

**Cross-Run Contamination:** `PASS` (Foreign run `NS-20260929-foreign99` rejected by `run_correlation_isolation`, `validation_result=FAIL`)

**Duplicate INFORM:** `PASS` (`8` raw Inform PDUs -> `4` deduplicated by receiver and `4` deduplicated by normalizer; no duplicate incident transitions)

## Findings

**P0:** `0`

**P1:** `1` (`F-12E-01`)

**P2:** `3` (`F-12E-02`, `F-12E-03`, `F-12E-04`)

**P3:** `1` (`F-12E-05`)

- **`F-12E-01` (P1):** `POST /api/scenarios/{scenario_id}/run` in [`backend/app/main.py`](../../backend/app/main.py#L1057-L1089) and `FiveStepWorkflow.tsx` do not pass `transport_mode`, `native_protocol`, `native_snmp_pdu_mode`, or `native_snmp_e2e` into `ScenarioRunRequest`. Executing the native SNMPv2c E2E pipeline requires Python invocation (`Developer Knowledge Required: YES`). Evidence: [`http_api_defect_f12e01.json`](evidence/gate12e/http_api_defect_f12e01.json).
- **`F-12E-02` (P2):** `service_provider_cisco` catalog metadata in [`scenarios.json`](../../src/netspout_core/catalog_data/scenarios.json) lists only `["syslog", "gnmi"]` and `["cisco:ios:mdt:metric", "cisco:ios:syslog"]` (`MODELED PAYLOAD`), and the UI Connect step lacks a configuration/preflight panel for Native SNMPv2c.
- **`F-12E-03` (P2 — `SEMANTIC_DEFECT`):** `NormalizedSnmpEvent.to_hec_payload()` serializes `"evidence_stage": "RECEIVER_OBSERVED"` into `_raw` prior to HEC dispatch, so Splunk-indexed events permanently display `evidence_stage="RECEIVER_OBSERVED"` rather than distinguishing `origin_evidence_stage="RECEIVER_OBSERVED"` from `current_evidence_stage="SPLUNK_OBSERVED"`.
- **`F-12E-04` (P2):** `ScenarioRunner.run_scenario()` emits Mode B PDUs for `node-cisco8k-core01` to port `1162` (`companion_manifest.evidence_stage="SENT"`) before invoking `SnmpSplunkE2EOrchestrator` for `cisco-asr9k-pe1` (`snmp_e2e_scorecard.evidence_stage="VALIDATED"`), resulting in two different device IDs and evidence stages inside the same `RunManifest`.
- **`F-12E-05` (P3):** Legacy `SNMPMibModal.tsx` (`SC4SNMP 330+ MIBs`) emits synthetic text strings (`raw_log="SNMP-COMMUNITY=public TRAP-TYPE=..."`) directly to HEC rather than using the native ASN.1 BER UDP engine.

## Regression

**Gate 12B:** `26 passed`

**Gate 12C:** `40 passed`

**Gate 12D:** `22 passed`

**Full Repository:** `323 passed`

**Source Verification:** `100% PASSED` (`scripts/verify_sources.py`)

**Catalog Validation:** `100% VALID` (`scripts/validate_catalog.py`)

## Governance

**Existing Scenario Maturity:** `GOLDEN_PATH_CERTIFIED`

**Native SNMP Recommendation:** `NATIVE_SNMP_ACCEPTED_WITH_FRICTION`

**Gate 12E Verdict:** `PASS WITH FRICTION`

**Recommended Next Step:** Authorize a bounded remediation gate (**Gate 12F — Native SNMP Productization & Closure**) to expose `native_snmp_e2e` through `POST /api/scenarios/{scenario_id}/run` and the 5-step UI (`F-12E-01`, `F-12E-02`), separate `origin_evidence_stage` from `current_evidence_stage` (`F-12E-03`), and unify `ScenarioRunner` device IDs and companion manifest state (`F-12E-04`).
