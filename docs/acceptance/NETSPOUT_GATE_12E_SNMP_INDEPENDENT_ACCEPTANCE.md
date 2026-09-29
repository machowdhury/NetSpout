# NetSpout Gate 12E — Independent SNMP Customer Acceptance & Governance Certification Report

## 0. Baseline Confirmation & Zero-Code-Change Rule

- **Repository:** `https://github.com/machowdhury/NetSpout`
- **Starting Baseline Commit (Gate 12D HEAD):** `d4cc7e7ef976ea7f61c2cdef296b114bcd155b2c`
- **Working Tree Status Prior to Test:** Clean (`git status -s` empty)
- **Application Files Modified:** **`NO`** (`0` changes to Python, React, catalog JSONs, scenario contracts, Docker definitions, Splunk app files, sourcetypes, validation rules, or runtime configuration defaults)
- **Gate 12D Documentation & Evidence Present:** Verified (`docs/architecture/NETSPOUT_GATE_12D_SNMP_SPLUNK_E2E.md`, `docs/acceptance/NETSPOUT_GATE_12D_SNMP_E2E_VERIFICATION.md`, and all `9` files in `docs/acceptance/evidence/gate12d/`)
- **Baseline Regression Verification:**
  - `python3 scripts/verify_sources.py`: `100% PASSED`
  - `python3 scripts/validate_catalog.py`: `100% VALID`
  - Gate 12B (`tests/test_gate12b_native_snmp.py`): `26 passed`
  - Gate 12C (`tests/test_gate12c_snmp_polling.py`): `40 passed`
  - Gate 12D (`tests/test_gate12d_snmp_splunk_e2e.py`): `22 passed`
  - Full repository regression suite: `323 passed`

---

## 1. Customer Problem Statement & Fresh Execution Identity

- **Customer Requirement Tested:**
  > "I want to demonstrate a realistic service-provider routing outage and recovery in Splunk using native SNMP traps and polling, but I do not have Cisco routing infrastructure."
- **Fresh Product-Generated Run ID (Gate 12E):** **`NS-20260929-6f40774b`**
- **HTTP API Defect Test Run ID (`F-12E-01`):** `NS-20260929-4fd7b02b`
- **Gate 12D Run Reused:** **`NO`** (`run-gate12d-canonical-001` and `NS-20260929-89224fdc` were not reused)

---

## 2. Customer Golden Path Evaluation (Steps 1–5)

### Step 1 — DISCOVER (`Scenario Discoverable: YES`, `Developer Knowledge Required: NO` for scenario selection, `YES` for SNMP capability discovery)
- The customer can discover `service_provider_cisco` (`Service Provider Network - All Cisco (Cisco 8000, NCS 5500, IOS-XR SRv6)`, code `SP-CISCO`, maturity `GOLDEN_PATH_CERTIFIED`) via the 5-step workflow UI (`StepChoose.tsx`) and `GET /api/scenarios/service_provider_cisco`.
- The scenario contract clearly communicates service-provider core routing, carrier link degradation, eBGP neighbor collapse, TI-LFA / backup path failover, and recovery.
- **Friction Recorded (`F-12E-02`, Severity P2):** In `src/netspout_core/catalog_data/scenarios.json`, `service_provider_cisco` lists `"telemetry_requirements": ["syslog", "gnmi"]`, `"sourcetypes": ["cisco:ios:mdt:metric", "cisco:ios:syslog"]`, and `"telemetry_model": "Cisco IOS-XR BGP Syslog & MDT Metrics"`. It does not advertise `"snmp"` or `"netspout:snmp:trap"` / `"netspout:snmp:poll"` on the catalog card.

### Step 2 — UNDERSTAND TELEMETRY (`Telemetry Semantics Accurate: YES` in native SNMP records/docs; `PARTIAL` on catalog card)
- Every normalized SNMP event (`netspout:snmp:trap` and `netspout:snmp:poll`) and the `SnmpE2ERunScorecard` explicitly carry `"telemetry_semantics": "NATIVE TRANSPORT / MODELED DEVICE STATE"`, and `sysDescr.0` states `"Cisco IOS XR Software (ASR9K), Version 7.9.2 [NetSpout Simulated Agent]"`.
- The architecture documentation (`docs/architecture/NETSPOUT_GATE_12D_SNMP_SPLUNK_E2E.md`) clearly distinguishes **NATIVE TRANSPORT** (RFC 3416 / RFC 1905 ASN.1 BER over UDP via `/usr/sbin/snmptrapd` and `/usr/bin/snmp*`) from **MODELED DEVICE STATE** (deterministic state progression without physical Cisco IOS-XR hardware).

### Step 3 — CONNECT (`Connection Preflight: PASS` via CLI/env; `Developer Knowledge Required: YES`)
- Local Splunk HEC (`https://127.0.0.1:8888/services/collector/event`, index `idx_network_ops`), Splunk REST search (`https://127.0.0.1:8889/services/search/jobs/export`), `/usr/sbin/snmptrapd`, and `/usr/bin/snmpget`, `/usr/bin/snmpgetnext`, `/usr/bin/snmpwalk`, `/usr/bin/snmpbulkwalk` are available and operational without root privileges.
- **Friction Recorded (`F-12E-02`, Severity P2):** The React UI (`StepConnect.tsx` and `TelemetryPipelinesModal.tsx`) exposes preflight and configuration controls for Splunk HEC and Native Flow (`NetFlow v9 / IPFIX`), plus a legacy synthetic `SC4SNMP` modal (`F-12E-05`, Severity P3), but does not provide a UI preflight or configuration panel for the Gate 12B–12D Native SNMPv2c pipeline.

### Step 4 — RUN (`Scenario Execution: PASS` via `ScenarioRunner` Python API; `FAIL` via HTTP REST `/api/scenarios/service_provider_cisco/run`)
- **Major Customer Workflow Defect Discovered (`F-12E-01`, Severity P1):**
  - In [`backend/app/main.py`](../../backend/app/main.py#L1057-L1089), `POST /api/scenarios/{scenario_id}/run` extracts only `seed`, `time_mode`, `topology_id`, `dispatch_telemetry`, and `transport_config` from the request JSON body and constructs `ScenarioRunRequest` **without** forwarding `transport_mode`, `native_protocol`, `native_snmp_pdu_mode`, `native_snmp_e2e`, `native_destination_host`, or `native_destination_port`.
  - Similarly, `FiveStepWorkflow.tsx` (`handleStartRun`) posts only `{mode, seed, dispatch_telemetry, transport_config}`.
  - Evidence saved in [`docs/acceptance/evidence/gate12e/http_api_defect_f12e01.json`](evidence/gate12e/http_api_defect_f12e01.json): calling `POST /api/scenarios/service_provider_cisco/run` with `{"transport_mode": "NATIVE_TRANSPORT", "native_protocol": "SNMPV2C_E2E", "native_snmp_e2e": true}` returned `run_id: "NS-20260929-4fd7b02b"` with `"returned_snmp_e2e_scorecard": null` and `"returned_native_snmp_result": null`.
  - Consequently, triggering the Native SNMPv2c E2E run currently requires invoking `ScenarioRunner().run_scenario(ScenarioRunRequest(..., transport_mode="NATIVE_TRANSPORT", native_protocol="SNMPV2C_E2E", native_snmp_e2e=True))` in Python (`Developer Knowledge Required: YES`).
- When executed via `ScenarioRunner().run_scenario(ScenarioRunRequest(scenario_id="service_provider_cisco", seed=42, time_mode="TEST", transport_mode="NATIVE_TRANSPORT", native_protocol="SNMPV2C_E2E", native_snmp_e2e=True))`, the scenario generated fresh Run ID **`NS-20260929-6f40774b`** and completed all four operational phases (`BASELINE -> DEGRADE -> FAILOVER -> RECOVERY`) with `validation_result = "PASS"`.

---

## 3. Native SNMP Notification Acceptance (Section 8 — Run `NS-20260929-6f40774b`)

Independently verified using `/usr/sbin/snmptrapd` ([`snmptrapd_output.txt`](evidence/gate12e/snmptrapd_output.txt)), `/opt/homebrew/bin/tshark` ([`tshark_verbose_output.txt`](evidence/gate12e/tshark_verbose_output.txt)), and [`gate12e_e2e.pcap`](evidence/gate12e/gate12e_e2e.pcap):

| Stage / Metric | Count / Status | Independent Evidence Source |
| :--- | :--- | :--- |
| `Generated` | `8` (`4` `SNMPv2-Trap`, `4` `InformRequest`) | `SnmpE2ERunScorecard.generated_notifications` |
| `Encoded` | `8` (`8` valid ASN.1 BER PDUs) | `SnmpE2ERunScorecard.encoded_notifications` |
| `Sent` | `8` UDP datagrams (`4` `0xA7`, `4` `0xA6`) | `SnmpE2ERunScorecard.sent_notifications` |
| `Receiver Observed` | `8` (`4` Traps + `4` Informs decoded by `/usr/sbin/snmptrapd`) | `snmptrapd_output.txt` (`8` `Received ... bytes from UDP:` blocks + `8` formatted varbind lines) |
| `Inform Acknowledged` | `4` (`4` RFC 3416 `Response-PDU (0xA2)` sent by `/usr/sbin/snmptrapd`) | `snmptrapd_output.txt` (`4` `Sending 92 bytes to UDP:` blocks) + `tshark_verbose_output.txt` |

### Verified Notification Progression (`NS-20260929-6f40774b`)

1. **`DEGRADE` (`sysUpTime.0 = 8641000`):** `IF-MIB::linkDown` (`1.3.6.1.6.3.1.1.5.3`) with `ifIndex.1 = 1`, `ifAdminStatus.1 = 1`, `ifOperStatus.1 = 2`, `ifDescr.1 = "HundredGigE0/0/0/1"` (both `SNMPv2-Trap` req `1915291068` and `InformRequest` req `396494801`).
2. **`FAILOVER` (`sysUpTime.0 = 8642000`):** `BGP4-MIB::bgpBackwardTransition` (`1.3.6.1.2.1.15.7.2`) with `bgpPeerLastError.198.51.100.1 = 0400` (Hold Timer Expired) and `bgpPeerState.198.51.100.1 = 1` (`idle`) (both `SNMPv2-Trap` req `444682559` and `InformRequest` req `1693954106`).
3. **`RECOVERY` (`sysUpTime.0 = 8643500`):**
   - `IF-MIB::linkUp` (`1.3.6.1.6.3.1.1.5.4`) with `ifIndex.1 = 1`, `ifAdminStatus.1 = 1`, `ifOperStatus.1 = 1`, `ifDescr.1 = "HundredGigE0/0/0/1"` (both `SNMPv2-Trap` req `100516607` and `InformRequest` req `720942702`).
   - `BGP4-MIB::bgpEstablished` (`1.3.6.1.2.1.15.7.1`) with `bgpPeerLastError.198.51.100.1 = 0000` and `bgpPeerState.198.51.100.1 = 6` (`established`) (both `SNMPv2-Trap` req `1937873828` and `InformRequest` req `1448858006`).

---

## 4. External SNMP Polling Acceptance (Section 9 — Run `NS-20260929-6f40774b`)

Independently verified using `/usr/bin/snmpget`, `/usr/bin/snmpgetnext`, `/usr/bin/snmpwalk`, and `/usr/bin/snmpbulkwalk` ([`external_polling_output.txt`](evidence/gate12e/external_polling_output.txt)):

- **Total Poll Requests / Responses:** `290` requests / `290` responses (`4` `GET`, `260` `GETNEXT`, `26` `GETBULK`)
- **Full MIB Walk Count:** `127` OIDs under `1.3.6.1.2.1` (`snmpwalk` and `snmpbulkwalk` matched 100%)
- **TShark Wire Verification:** `592` total UDP SNMP frames in `gate12e_e2e.pcap`, **`0` `[Malformed Packet]` warnings**.

| OID / Metric | `BASELINE` | `DEGRADE` | `FAILOVER` | `RECOVERY` | Agrees with Trap/Inform |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `ifOperStatus.1` (`1.3.6.1.2.1.2.2.1.8.1`) | `1` (`up`) | `2` (`down`) | `2` (`down`) | `1` (`up`) | `YES` (`linkDown` / `linkUp`) |
| `ifInErrors.1` (`1.3.6.1.2.1.2.2.1.14.1`) | `0` | `48` | `48` | `48` | `YES` |
| `bgpPeerState.198.51.100.1` (`...15.3.1.2.198.51.100.1`) | `6` (`established`) | `6` (`established`) | `1` (`idle`) | `6` (`established`) | `YES` (`bgpBackwardTransition` / `bgpEstablished`) |
| `bgpPeerLastError.198.51.100.1` (`...15.3.1.14.198.51.100.1`) | `0000` | `0000` | `0400` | `0000` | `YES` |
| `bgpPeerState.198.51.100.2` (`...15.3.1.2.198.51.100.2`) | `6` (`established`) | `6` (`established`) | `6` (`established`) | `6` (`established`) | `YES` (Backup peer active) |
| `ipRouteNextHop.0.0.0.0` (`1.3.6.1.2.1.4.21.1.7.0.0.0.0`) | `198.51.100.1` | `198.51.100.1` | `198.51.100.2` | `198.51.100.1` | `YES` (Backup failover & primary restore) |
| `ipRouteIfIndex.0.0.0.0` (`1.3.6.1.2.1.4.21.1.2.0.0.0.0`) | `1` | `1` | `2` | `1` | `YES` (`Hu0/0/0/1` -> `Hu0/0/0/2` -> `Hu0/0/0/1`) |

- **`External Polling`:** `PASS`
- **`Trap/Poll Coherence`:** `PASS`

---

## 5. Splunk Acceptance & 10 Customer Operational Questions (Section 10)

All 10 customer operational questions were answered directly from fresh Splunk searches against `netspout_run_id="NS-20260929-6f40774b"` ([`phase_reconstruction.json`](evidence/gate12e/phase_reconstruction.json) and [`splunk_search_evidence.json`](evidence/gate12e/splunk_search_evidence.json)):

1. **What failed?** Primary 100G core transit interface `HundredGigE0/0/0/1` (`ifIndex=1`) suffered carrier degradation (`IF-MIB::linkDown`), followed by eBGP peer `198.51.100.1` (AS 65002) hold-timer expiration (`BGP4-MIB::bgpBackwardTransition`).
2. **Which interface changed state?** `IF-MIB::ifIndex.1` (`HundredGigE0/0/0/1`, alias `Primary-Core-Transit-AS65002`) transitioned `1 (up) -> 2 (down) -> 2 (down) -> 1 (up)`.
3. **When did degradation begin?** Phase `DEGRADE` at `sysUpTime.0 = 8641000` (`10.0s` after `BASELINE` `sysUpTime.0 = 8640000`), with `ifInErrors.1` jumping from `0` to `48`.
4. **Did BGP fail?** Yes. In `FAILOVER` (`sysUpTime.0 = 8642000`), `BGP4-MIB::bgpBackwardTransition` (`1.3.6.1.2.1.15.7.2`) fired and polled `bgpPeerState.198.51.100.1` dropped from `6` (`established`) to `1` (`idle`) with `bgpPeerLastError = 0400`.
5. **What was the failed peer?** `198.51.100.1` (remote AS `65002`).
6. **Did routing move to a different next hop?** Yes. Polled `IP-MIB::ipRouteNextHop.0.0.0.0` shifted from `198.51.100.1` (`ipRouteIfIndex = 1`) in `BASELINE`/`DEGRADE` to backup next hop `198.51.100.2` (`ipRouteIfIndex = 2`, `HundredGigE0/0/0/2`, AS `65003`, metric `20`) in `FAILOVER`.
7. **Did SNMP polling corroborate the notification?** Yes — all 9 coherence invariants between `netspout:snmp:trap` and `netspout:snmp:poll` passed (`trap_poll_coherence = true`).
8. **Did the interface recover?** Yes. In `RECOVERY` (`sysUpTime.0 = 8643500`), `IF-MIB::linkUp` (`1.3.6.1.6.3.1.1.5.4`) was observed and polled `ifOperStatus.1` returned to `1` (`up`).
9. **Did BGP re-establish?** Yes. In `RECOVERY` (`sysUpTime.0 = 8643500`), `BGP4-MIB::bgpEstablished` (`1.3.6.1.2.1.15.7.1`) was observed, polled `bgpPeerState.198.51.100.1` returned to `6` (`established`), `bgpPeerLastError.198.51.100.1` cleared to `0000`, and `bgpPeerFsmEstablishedTransitions.198.51.100.1` incremented from `1` to `2`.
10. **Was the original route restored?** Yes. In `RECOVERY`, polled `IP-MIB::ipRouteNextHop.0.0.0.0` returned to `198.51.100.1` over `ipRouteIfIndex.0.0.0.0 = 1` with metric `10`.

- **`Splunk Investigation`:** `PASS`
- **`Developer Knowledge Required for SPL`:** `NO` (standard Splunk fields `netspout_run_id`, `netspout_phase`, `sourcetype`, `snmp_pdu_type`, `snmp_trap_name`, `snmp_oid_name`, `snmp_value`)

---

## 6. Correlation & Wire-Purity Acceptance (Section 11)

- All `326` indexed events (`8` `netspout:snmp:trap`, `318` `netspout:snmp:poll`) contain `netspout_run_id="NS-20260929-6f40774b"`, `netspout_scenario_id="service_provider_cisco"`, `netspout_phase` (`BASELINE`, `DEGRADE`, `FAILOVER`, `RECOVERY`), `netspout_device_id="cisco-asr9k-pe1"`, and `netspout_event_id`.
- Wire-level inspection of all `592` frames in `gate12e_e2e.pcap` confirms **zero** proprietary NetSpout correlation varbinds or strings on the UDP wire; all wire OIDs belong strictly to `1.3.6.1.2.1.*` and `1.3.6.1.6.3.*`.
- **`Run Correlation`:** `PASS`
- **`Standards Fidelity Preserved`:** `YES`

---

## 7. Evidence-State Semantics Review (Section 12)

- **Determination:** **`SEMANTIC_DEFECT`** (recorded as Finding **`F-12E-03`**, Severity **P2**)
- **Reasoning:**
  - When `SnmpCollectorNormalizer` constructs a `NormalizedSnmpEvent`, it sets `evidence_stage = "RECEIVER_OBSERVED"`.
  - In `SnmpSplunkBridge.dispatch_events()`, `ev.to_hec_payload()` serializes the event JSON **before** dispatching to Splunk HEC and only mutates `ev.evidence_stage = "SPLUNK_DISPATCHED"` in Python memory after HEC returns HTTP 200.
  - Consequently, every event indexed in Splunk permanently carries `"evidence_stage": "RECEIVER_OBSERVED"` inside its indexed `_raw` JSON payload, even when queried inside Splunk (`SPLUNK_OBSERVED`) and after validation passes (`VALIDATED`).
  - While the run-level `SnmpE2ERunScorecard` accurately tracks all 8 stages (`GENERATED -> ENCODED -> SENT -> ACKNOWLEDGED -> RECEIVER_OBSERVED -> SPLUNK_DISPATCHED -> SPLUNK_OBSERVED -> VALIDATED`), a customer inspecting individual events in Splunk Search could be confused by seeing `evidence_stage="RECEIVER_OBSERVED"` on an event already indexed in Splunk. Separating `origin_evidence_stage="RECEIVER_OBSERVED"` from `current_evidence_stage` is recommended in a future remediation gate.

---

## 8. Fresh SPL Reconstruction Executed Against `NS-20260929-6f40774b` (Section 13)

Every query below was executed against live Splunk (`index=idx_network_ops`) for `netspout_run_id="NS-20260929-6f40774b"` ([`splunk_search_evidence.json`](evidence/gate12e/splunk_search_evidence.json)):

| # | Purpose | Executed SPL Query | Observed Count |
| :--- | :--- | :--- | :--- |
| 1 | **Complete SNMP Evidence** | `search index=idx_network_ops (sourcetype="netspout:snmp:trap" OR sourcetype="netspout:snmp:poll") netspout_run_id="NS-20260929-6f40774b" \| table _time netspout_phase sourcetype snmp_pdu_type snmp_request_id snmp_trap_name snmp_oid_name snmp_value snmp_collector` | **`326`** |
| 2 | **Notification Timeline** | `search index=idx_network_ops sourcetype="netspout:snmp:trap" netspout_run_id="NS-20260929-6f40774b" \| table _time netspout_phase snmp_pdu_type snmp_request_id snmp_trap_name snmp_trap_oid snmp_oid_name snmp_value sys_uptime` | **`8`** |
| 3 | **Polling Timeline** | `search index=idx_network_ops sourcetype="netspout:snmp:poll" netspout_run_id="NS-20260929-6f40774b" \| table _time netspout_phase snmp_pdu_type snmp_oid_name snmp_oid snmp_value snmp_value_type` | **`318`** |
| 4 | **Interface State Progression** | `search index=idx_network_ops (sourcetype="netspout:snmp:trap" OR sourcetype="netspout:snmp:poll") netspout_run_id="NS-20260929-6f40774b" (snmp_oid="1.3.6.1.2.1.2.2.1.8.1" OR snmp_oid="1.3.6.1.2.1.2.2.1.14.1" OR snmp_trap_oid="1.3.6.1.6.3.1.1.5.3" OR snmp_trap_oid="1.3.6.1.6.3.1.1.5.4") \| table _time netspout_phase sourcetype snmp_pdu_type snmp_trap_name snmp_oid_name snmp_value` | **`20`** |
| 5 | **BGP State Progression** | `search index=idx_network_ops (sourcetype="netspout:snmp:trap" OR sourcetype="netspout:snmp:poll") netspout_run_id="NS-20260929-6f40774b" (snmp_oid="1.3.6.1.2.1.15.3.1.2.198.51.100.1" OR snmp_oid="1.3.6.1.2.1.15.3.1.14.198.51.100.1" OR snmp_oid="1.3.6.1.2.1.15.3.1.2.198.51.100.2" OR snmp_trap_oid="1.3.6.1.2.1.15.7.2" OR snmp_trap_oid="1.3.6.1.2.1.15.7.1") \| table _time netspout_phase sourcetype snmp_pdu_type snmp_trap_name snmp_oid_name snmp_value` | **`22`** |
| 6 | **Route Next-Hop Progression** | `search index=idx_network_ops sourcetype="netspout:snmp:poll" netspout_run_id="NS-20260929-6f40774b" (snmp_oid="1.3.6.1.2.1.4.21.1.7.0.0.0.0" OR snmp_oid="1.3.6.1.2.1.4.21.1.2.0.0.0.0") \| table _time netspout_phase snmp_pdu_type snmp_oid_name snmp_oid snmp_value` | **`12`** |
| 7 | **Trap vs Polling Correlation** | `search index=idx_network_ops (sourcetype="netspout:snmp:trap" OR sourcetype="netspout:snmp:poll") netspout_run_id="NS-20260929-6f40774b" \| stats count(eval(sourcetype="netspout:snmp:trap")) as notification_count count(eval(sourcetype="netspout:snmp:poll")) as poll_count values(snmp_trap_name) as notifications values(eval(if(sourcetype="netspout:snmp:poll", snmp_oid_name."=".snmp_value, null()))) as polled_states by netspout_phase` | **`4`** |
| 8 | **Recovery Confirmation** | `search index=idx_network_ops (sourcetype="netspout:snmp:trap" OR sourcetype="netspout:snmp:poll") netspout_run_id="NS-20260929-6f40774b" netspout_phase="RECOVERY" \| stats count(eval(sourcetype="netspout:snmp:trap")) as recovery_traps_and_informs values(snmp_trap_name) as recovery_notifications values(eval(if(sourcetype="netspout:snmp:poll" AND (snmp_oid="1.3.6.1.2.1.2.2.1.8.1" OR snmp_oid="1.3.6.1.2.1.15.3.1.2.198.51.100.1" OR snmp_oid="1.3.6.1.2.1.4.21.1.7.0.0.0.0"), snmp_oid_name."=".snmp_value, null()))) as restored_states` | **`1`** |

---

## 9. Controlled Failure Acceptance (Section 14)

All 6 controlled failures were independently executed and recorded in [`controlled_failures_evidence.json`](evidence/gate12e/controlled_failures_evidence.json):

- **Failure A — SNMP Receiver Down (`NS-20260929-6f40774b-cf-a`):** `SENT=YES` (`traps_sent=4`, `informs_sent=4`), `ACKNOWLEDGED=NO` (`0`), `RECEIVER_OBSERVED=NO` (`0`), `SPLUNK_OBSERVED=NO` (`0`), `VALIDATED=NO` (`validation_result=FAIL`). **`PASS`**
- **Failure B — Splunk Down (`NS-20260929-6f40774b-cf-b`):** `RECEIVER_OBSERVED=YES` (`8` notifications, `290` polls), `SPLUNK_DISPATCHED=NO` (`0` dispatched, `326` failed), `SPLUNK_OBSERVED=NO` (`0`), `VALIDATED=NO` (`validation_result=FAIL`). **`PASS`**
- **Failure C — SNMP Agent Unreachable (`NS-20260929-6f40774b-cf-c`):** Poll timeout error recorded (`Timeout: No Response`), `polling_responses=0`, `splunk_observed_poll_records=0` (zero fabricated poll records), `validation_result=FAIL`. **`PASS`**
- **Failure D — Missing Required Phase (`NS-20260929-6f40774b-cf-d`):** `RECOVERY` suppressed; `splunk_observed_records=306`, `observed_phases=["BASELINE","DEGRADE","FAILOVER"]`, `all_four_phases_present=false`, `validation_result=FAIL`. **`PASS`**
- **Failure E — Cross-Run Contamination (`NS-20260929-foreign99` injected into `NS-20260929-6f40774b`):** `run_correlation_isolation` check failed (`foreign_records=1`), `validation_result=FAIL`. **`PASS`**
- **Failure F — Duplicate INFORM (`NS-20260929-6f40774b-cf-e`):** `8` Inform PDUs transmitted (`4` originals + `4` duplicates with identical `request_id`), `4` deduplicated by `ExternalSnmpTrapReceiver` (`duplicate_informs_suppressed=4`) and `4` deduplicated by `SnmpCollectorNormalizer` (`duplicate_events_suppressed=4`), preventing false duplicate incident transitions. **`PASS`**

---

## 10. Classified Findings Register (Section 20)

| ID | Severity | Component | Summary & Evidence |
| :--- | :--- | :--- | :--- |
| **`F-12E-01`** | **P1** | [`backend/app/main.py`](../../backend/app/main.py#L1057-L1089), [`FiveStepWorkflow.tsx`](../../frontend/src/components/workflow/FiveStepWorkflow.tsx#L142-L157) | **HTTP Scenario Run Endpoint & 5-Step UI Do Not Forward Native SNMP Parameters:** `POST /api/scenarios/{scenario_id}/run` ignores `transport_mode`, `native_protocol`, `native_snmp_pdu_mode`, and `native_snmp_e2e` in the JSON request body. Triggering the native SNMPv2c E2E run requires calling `ScenarioRunner().run_scenario(...)` or `SnmpSplunkE2EOrchestrator().execute_e2e_run()` in Python (`Developer Knowledge Required: YES`). Evidence: [`http_api_defect_f12e01.json`](evidence/gate12e/http_api_defect_f12e01.json). |
| **`F-12E-02`** | **P2** | [`scenarios.json`](../../src/netspout_core/catalog_data/scenarios.json), [`StepConnect.tsx`](../../frontend/src/components/workflow/StepConnect.tsx) | **Catalog Metadata & Connect UI Omit Native SNMPv2c Mode B:** `service_provider_cisco` catalog metadata lists only `["syslog", "gnmi"]` and `["cisco:ios:mdt:metric", "cisco:ios:syslog"]` (`MODELED PAYLOAD` over `Splunk HEC`), and the UI Connect step lacks a configuration/preflight panel for `/usr/sbin/snmptrapd` and `SimulatedSnmpAgent`. |
| **`F-12E-03`** | **P2** | [`src/netspout_core/snmp_splunk_e2e.py`](../../src/netspout_core/snmp_splunk_e2e.py#L960-L1153) | **Per-Event `evidence_stage="RECEIVER_OBSERVED"` Frozen in Splunk `_raw` JSON (`SEMANTIC_DEFECT`):** `ev.to_hec_payload()` serializes `evidence_stage: "RECEIVER_OBSERVED"` before HEC dispatch, so events queried inside Splunk still display `evidence_stage="RECEIVER_OBSERVED"` rather than distinguishing `origin_evidence_stage="RECEIVER_OBSERVED"` from `current_evidence_stage="SPLUNK_OBSERVED"`. |
| **`F-12E-04`** | **P2** | [`src/netspout_core/scenario_runner.py`](../../src/netspout_core/scenario_runner.py#L2897-L2965) | **Dual Native Emission & Device ID Split in `ScenarioRunner.run_scenario()`:** When `native_snmp_e2e=True`, `ScenarioRunner` first emits Mode B PDUs for `node-cisco8k-core01` to port `1162` (`companion_manifest.evidence_stage="SENT"`) and then invokes `SnmpSplunkE2EOrchestrator` for `cisco-asr9k-pe1` (`snmp_e2e_scorecard.evidence_stage="VALIDATED"`). |
| **`F-12E-05`** | **P3** | [`SNMPMibModal.tsx`](../../frontend/src/components/SNMPMibModal.tsx), [`backend/app/main.py`](../../backend/app/main.py#L664-L725) | **Legacy SC4SNMP Modal Emits Synthetic Text Logs Directly to HEC:** The top-bar `SC4SNMP (330+ MIBs)` modal sends synthetic key-value text logs (`raw_log="SNMP-COMMUNITY=public TRAP-TYPE=..."`) directly to HEC rather than using the native ASN.1 BER UDP engine. |

---

## 11. Governance & Certification Verdict

- **Existing Scenario Maturity:** `GOLDEN_PATH_CERTIFIED` (unchanged)
- **Customer Claim Supported:** **`YES`**
- **Native SNMP Recommendation:** **`NATIVE_SNMP_ACCEPTED_WITH_FRICTION`**
- **Gate 12E Verdict:** **`PASS WITH FRICTION`** (`P0 = 0`, `P1 = 1`, `P2 = 3`, `P3 = 1`)
- **Recommended Next Step:** Authorize a tightly bounded **Gate 12F — Native SNMP Productization & Closure Gate** to wire `native_snmp_e2e` / `transport_mode` through `POST /api/scenarios/{scenario_id}/run` and the 5-step UI (`F-12E-01`, `F-12E-02`), separate `origin_evidence_stage` from `current_evidence_stage` (`F-12E-03`), and unify the `ScenarioRunner` device ID and companion manifest (`F-12E-04`).
