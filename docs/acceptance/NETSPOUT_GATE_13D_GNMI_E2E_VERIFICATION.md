# NetSpout Gate 13D — Native gNMI/OpenConfig → External Collector → Splunk E2E Verification Report

## 1. Acceptance Overview

This report documents the formal end-to-end verification of NetSpout Gate 13D:
- **Baseline Commit:** `f4c3094887d95a1eaebbdf0e65cbdda4cb5018c2`
- **External Collector:** `/opt/homebrew/bin/gnmic` (version `0.49.0`)
- **Transport Stack:** Native gNMI 0.8.0 / Protobuf over gRPC / HTTP/2 on loopback TCP (127.0.0.1)
- **Splunk HEC Ingestion:** Event Index `idx_network_ops` (`netspout:gnmi:event`) + Metrics Index `cisco_mdt_metrics` (`netspout:gnmi:metric`)
- **Verification Engine:** `ValidationEngine` evaluating 9 contract rule types across live Splunk search and `| mstats` query outputs.
- **Result:** **27 of 27 Verification Items PASS (100% Green)**.

---

## 2. 27-Item Verification Matrix (Gate 13D Section 26)

| # | Verification Item | Test Method | Splunk Evidence File | Status |
|---|---|---|---|---|
| 1 | Native gNMI server -> external collector -> Splunk E2E run completes all 7 stages | `test_01_native_gnmi_server_to_collector_to_splunk_e2e` | `e2e_scorecard.json` | **PASS** |
| 2 | External gnmic v0.49.0 collector output is ingested into Splunk with collector metadata | `test_02_gnmic_collector_output_ingested_into_splunk` | `service_provider_cisco_splunk_events.json` | **PASS** |
| 3 | Event telemetry is indexed in `idx_network_ops` with sourcetype `netspout:gnmi:event` | `test_03_event_telemetry_indexed_and_searchable` | `service_provider_cisco_splunk_events.json` | **PASS** |
| 4 | Numeric leaf telemetry is indexed in `cisco_mdt_metrics` and queryable via `\| mstats` | `test_04_metric_telemetry_indexed_and_queryable_via_mstats` | `service_provider_cisco_splunk_metrics.json` | **PASS** |
| 5 | `SPLUNK_DISPATCHED` and `SPLUNK_OBSERVED` are tracked separately and never conflated | `test_05_splunk_dispatched_vs_splunk_observed_separation` | `stage_accounting_ledger.json` | **PASS** |
| 6 | `service_provider_cisco` E2E run passes all 10 validation rules across BASELINE -> DEGRADE -> FAILOVER -> RECOVERY | `test_06_service_provider_cisco_e2e_run` | `validation_engine_results.json` | **PASS** |
| 7 | `openconfig_mdt_streaming` E2E run verifies OpenConfig ONCE, SAMPLE, and ON_CHANGE in Splunk | `test_07_openconfig_mdt_streaming_e2e_run` | `openconfig_mdt_streaming_splunk.json` | **PASS** |
| 8 | `cisco_aci_microburst` E2E run verifies queue/drop progression and declares ACI DME MOs as `UNSUPPORTED_TELEMETRY` | `test_08_cisco_aci_microburst_e2e_run_and_honesty` | `cisco_aci_microburst_splunk.json` | **PASS** |
| 9 | Cisco IOS XR OpenConfig and `Cisco-IOS-XR-*` native paths observed in Splunk | `test_09_cisco_ios_xr_openconfig_and_native_in_splunk` | `multivendor_splunk_verification.json` | **PASS** |
| 10 | Cisco IOS XE OpenConfig and `Cisco-IOS-XE-*` native paths observed in Splunk | `test_10_cisco_ios_xe_openconfig_and_native_in_splunk` | `multivendor_splunk_verification.json` | **PASS** |
| 11 | Arista EOS OpenConfig and `eos_native` paths observed in Splunk | `test_11_arista_eos_openconfig_and_native_in_splunk` | `multivendor_splunk_verification.json` | **PASS** |
| 12 | Juniper Junos OpenConfig and `junos` native paths observed in Splunk | `test_12_juniper_junos_openconfig_and_native_in_splunk` | `multivendor_splunk_verification.json` | **PASS** |
| 13 | Interface state transitions (`UP` -> `DOWN` -> `UP`) observed in Splunk | `test_13_interface_state_transition_in_splunk` | `spl_query_outputs.json` | **PASS** |
| 14 | BGP neighbor state transitions (`ESTABLISHED` -> `IDLE` -> `ESTABLISHED`) observed in Splunk | `test_14_bgp_neighbor_state_transition_in_splunk` | `spl_query_outputs.json` | **PASS** |
| 15 | QoS queue depth and packet drop progression observed in Splunk via `\| mstats` | `test_15_qos_congestion_and_drop_progression_in_splunk` | `mstats_query_outputs.json` | **PASS** |
| 16 | Optical RX power degradation and recovery observed in Splunk via `\| mstats` | `test_16_optical_degradation_and_recovery_in_splunk` | `mstats_query_outputs.json` | **PASS** |
| 17 | CPU, memory, and temperature telemetry observed in Splunk via `\| mstats` | `test_17_cpu_memory_temperature_telemetry_in_splunk` | `mstats_query_outputs.json` | **PASS** |
| 18 | Out-of-band correlation fields are preserved in Splunk while wire payloads remain 100% pure | `test_18_correlation_fields_preserved_and_wire_pure` | `e2e_scorecard.json` | **PASS** |
| 19 | Keyed gNMI paths (`[name=HundredGigE0/0/0/0]`, `[neighbor-address=10.255.0.2]`) are preserved in Splunk | `test_19_keyed_gnmi_paths_preserved_in_splunk` | `service_provider_cisco_splunk_events.json` | **PASS** |
| 20 | Native datatypes (`int`, `float`, `bool`, `str`, `object`) are preserved across event and metric stores | `test_20_native_datatypes_preserved_in_splunk` | `service_provider_cisco_splunk_events.json` | **PASS** |
| 21 | All canonical SPL investigation queries (q1, q2, q3, q4, q8, q10) execute and return results | `test_21_spl_investigation_queries_execute_and_return_results` | `spl_query_outputs.json` | **PASS** |
| 22 | All canonical `\| mstats` queries (q5, q6, q7, q9) execute against `cisco_mdt_metrics` | `test_22_mstats_queries_execute_and_return_results` | `mstats_query_outputs.json` | **PASS** |
| 23 | ValidationEngine passes all scenario validation rules on valid Splunk evidence | `test_23_validation_engine_passes_on_valid_splunk_evidence` | `validation_engine_results.json` | **PASS** |
| 24 | ValidationEngine strictly fails when required Splunk event or metric evidence is missing | `test_24_validation_engine_fails_on_missing_splunk_evidence` | `validation_engine_results.json` | **PASS** |
| 25 | All 9 controlled failure scenarios (A through I) are verified with honest stage accounting | `test_25_controlled_failures_a_through_i_verified` | `controlled_failures.json` | **PASS** |
| 26 | Cross-transport coherence (gNMI + SNMP + Syslog + NetFlow/IPFIX) verified in Splunk | `test_26_cross_transport_coherence_verified_in_splunk` | `cross_transport_coherence_splunk.json` | **PASS** |
| 27 | Collector-to-Splunk performance benchmark and resource guardrails verified | `test_27_performance_and_resource_guardrails_verified` | `performance_benchmark.json` | **PASS** |

---

## 3. Canonical Investigation Queries Executed

All investigation queries from Section 18 execute against live Splunk Enterprise:

### SPL Search Queries (Index: `idx_network_ops`, Sourcetype: `netspout:gnmi:event`)
- **q1 (Run Overview):**
  `search index=idx_network_ops sourcetype="netspout:gnmi:event" netspout_run_id="$RUN_ID" | stats count as event_count dc(gnmi_path) as unique_paths values(gnmi_vendor) as vendors values(gnmi_platform) as platforms values(collector_mode) as modes by netspout_phase`
  *Result: 4 phase rows (`BASELINE`, `DEGRADE`, `FAILOVER`, `RECOVERY`), 100% path coverage.*
- **q2 (Phase Progression):**
  `search index=idx_network_ops sourcetype="netspout:gnmi:event" netspout_run_id="$RUN_ID" is_leaf="true" | stats count as state_leaf_events values(gnmi_leaf) as observed_leaves values(gnmi_origin) as origins by netspout_phase gnmi_target`
  *Result: State leaf events validated per phase.*
- **q3 (Interface Transition):**
  `search index=idx_network_ops sourcetype="netspout:gnmi:event" netspout_run_id="$RUN_ID" telemetry_category="interface" (gnmi_leaf="oper-status" OR gnmi_leaf="admin-status" OR gnmi_leaf="state" OR gnmi_leaf="oper-state") | table _time netspout_phase gnmi_target gnmi_origin interface_name gnmi_path gnmi_leaf gnmi_value`
  *Result: Confirmed `HundredGigE0/0/0/0` transitioning `UP -> DOWN -> UP` across phases.*
- **q4 (BGP Transition):**
  `search index=idx_network_ops sourcetype="netspout:gnmi:event" netspout_run_id="$RUN_ID" telemetry_category="bgp" (gnmi_leaf="session-state" OR gnmi_leaf="connection-state") | table _time netspout_phase gnmi_target gnmi_origin neighbor_address gnmi_path gnmi_leaf gnmi_value`
  *Result: Confirmed neighbor `10.255.0.2` transitioning `ESTABLISHED -> IDLE -> ESTABLISHED`.*
- **q8 (Multi-Vendor Comparison):**
  `search index=idx_network_ops sourcetype="netspout:gnmi:event" netspout_run_id="$RUN_ID" | stats count as event_count dc(gnmi_sensor_id) as sensor_count values(gnmi_origin) as origins values(gnmi_os_version) as os_versions by gnmi_vendor gnmi_platform gnmi_model gnmi_target`
  *Result: 4 rows returned covering Cisco IOS XR, Cisco IOS XE, Arista EOS, and Juniper Junos.*
- **q10 (Cross-Source Correlation):**
  `search index=idx_network_ops netspout_run_id="$RUN_ID" (sourcetype="netspout:gnmi:event" OR sourcetype="netspout:snmp:trap" OR sourcetype="netspout:snmp:poll" OR sourcetype="cisco:ios:syslog" OR sourcetype="netflow:collector") | stats count as records dc(sourcetype) as source_count values(sourcetype) as sourcetypes by netspout_phase netspout_device_id`
  *Result: 4 phase rows returned, each correlating 5 independent sourcetypes.*

### `| mstats` Queries (Index: `cisco_mdt_metrics`, Sourcetype: `netspout:gnmi:metric`)
- **q5 (QoS Congestion & Drops):**
  `| mstats max(_value) as max_val avg(_value) as avg_val latest(_value) as latest_val WHERE index=cisco_mdt_metrics metric_name=* netspout_run_id="$RUN_ID" telemetry_category="qos" BY netspout_phase gnmi_target gnmi_leaf gnmi_path`
  *Result: Measured `queue-current-size-bytes` surging from 64,000 to 14,850,000 bytes and `tail-drop-packets` reaching 5,120 during microburst degradation.*
- **q6 (Optical Signal Degradation):**
  `| mstats min(_value) as min_dbm avg(_value) as avg_dbm latest(_value) as latest_dbm WHERE index=cisco_mdt_metrics metric_name=* netspout_run_id="$RUN_ID" telemetry_category="optics" BY netspout_phase gnmi_target gnmi_leaf gnmi_path`
  *Result: Measured `receive-power` dropping from -6.20 dBm to -24.80 dBm before recovering to -6.10 dBm.*
- **q7 (System CPU & Memory Health):**
  `| mstats max(_value) as max_val avg(_value) as avg_val WHERE index=cisco_mdt_metrics metric_name=* netspout_run_id="$RUN_ID" (telemetry_category="system" OR telemetry_category="environment") BY netspout_phase gnmi_target telemetry_category gnmi_leaf gnmi_unit`
  *Result: Verified system CPU utilization and thermal power metrics across phases.*
- **q9 (Metric Catalog Overview):**
  `| mstats count(_value) as metric_samples min(_value) as min_val max(_value) as max_val WHERE index=cisco_mdt_metrics metric_name=* netspout_run_id="$RUN_ID" BY telemetry_category gnmi_leaf gnmi_unit gnmi_platform netspout_phase`
  *Result: 68 distinct metric time-series cataloged across interfaces, routing, QoS, optics, and system.*

---

## 4. Controlled Failure Verification Matrix

All 9 negative testing scenarios from Section 21 were verified:

| Failure | Condition Tested | Expected Behavior | Observed Result |
|---|---|---|---|
| **A** | Server Unavailable (closed port) | Collector exits nonzero; no dispatch; no fake observations | `returncode != 0`, `COLLECTOR_RECEIVED=False`, `SPLUNK_DISPATCHED=False` |
| **B** | Collector Unavailable (bad binary path) | Subprocess error code 127; no synthetic records emitted | `returncode == 127`, zero normalized records |
| **C** | Splunk Unavailable (simulate 503) | Normalization passes; HEC dispatch fails; `highest_verified_stage=NORMALIZED` | `SPLUNK_DISPATCHED=False`, `highest_verified_stage="NORMALIZED"` |
| **D** | Invalid gNMI Credentials | Server rejects authentication; zero data collected | `returncode != 0`, zero normalized records |
| **E** | Unsupported gNMI Path | Server returns gRPC `NOT_FOUND`; zero events fabricated | `returncode != 0`, zero normalized records |
| **F** | Missing Correlation Field (`netspout_phase`) | Adapter rejects records; `dropped_missing_correlation > 0` | 100% of invalid records dropped, validation strictly fails |
| **G** | Missing Vendor Metadata (`vendor`/`platform`) | Adapter rejects records; `dropped_missing_vendor > 0` | 100% of invalid records dropped, validation strictly fails |
| **H** | Metric Destination Failure | Event store succeeds, metric store fails; overall run cannot pass | `DESTINATION_CHECK` rule fails, `SPLUNK_OBSERVED_METRICS=0` |
| **I** | Duplicate Collector Records | Collector deduplication suppresses duplicates deterministically | Duplicate count matches exactly, 0 duplicate events sent |

---

## 5. Performance and Resource Benchmarks

From `docs/acceptance/evidence/gate13d/performance_benchmark.json`:
- **Collector Receive Latency:** ~74 ms
- **Normalization & Adaptation Latency:** ~0.8 ms
- **Splunk HEC Dispatch Latency:** ~28 ms
- **Searchable Observation Latency:** ~1,120 ms
- **Total E2E Completion Time:** ~1,230 ms
- **Dispatch Errors:** 0
- **Process Memory RSS:** Stable (< 120 MB max RSS)
- **Loopback Enforced:** `127.0.0.1`

---

## 6. Conclusion & Gate 13D Sign-off

NetSpout Gate 13D fulfills all primary gate objectives, establishes verified end-to-end telemetry from modeled network states through the native gNMI server, independent `gnmic` collector, Splunk HEC, and fresh search/`| mstats` inspection, and strictly adheres to the anti-fabrication mandate.
