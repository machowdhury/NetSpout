# Phase 8 report: correcting real telemetry formats and metrics

Branch `recovery/phase1-ta-compat`, from `508460e`. Evidence for every correction is the Phase 7 sanitized fixtures (`tests/fixtures/phase7_real_samples/`), the Phase 7 reference-instance inventories, the added read-only metric evidence (`docs/contracts/phase7/phase8_metric_evidence.json`) and the add-on packages' own definitions. Live validation ran only in the isolated TA-validation lab (`netspout_tavalidation_splunk`, mgmt 19191, HEC 19088); nothing was sent to the reference instance and the protected demo was not touched. The reference instance was only queried read-only for the additional metric evidence.

## 1. Baseline (before the changes)

| Integration | Generated before | Real structure (fixture) | Routing before | Mismatch | Fix | Regression risk |
|---|---|---|---|---|---|---|
| IOS XR metrics (`cisco:ios:mdt:metric`) | OpenConfig leaf names `in_octets`, `cpu_utilization`; dims device, host, vendor, status, action, node_id_str, sensor_path; source `cisco:ios:mdt`; index `cisco_mdt_metrics` | `interface_generic_counters.*` and native `Cisco-IOS-XR-wdsysmon-fd-oper:...total_cpu_*_minute`; dims interface_name+path or node_name+path+subscription; source = device address | HEC metric, metric index | names, dimensions, source differ | emit only the 14 observed series with their observed dimensions | gNMI and scenario paths share the dispatcher: kept on their own record shape |
| `meraki:securityappliances` | 150 sample lines: 99 network events, 43 AMP-style (`eventType`), 8 Air Marshal | only the network-event schema | event | foreign families under this sourcetype; stale `occurredAt` | remove foreign lines, add a family contract, render `occurredAt` at generation time | the sample is shared by single/batch/run paths: refresh applied to all three |
| `vmware:perf:cpu` | blocked as a metric routing conflict; the only sample was fabricated JSON | 19-column TSV row, event index, source `VMPerf:HostSystem` | blocked | wrong kind, wrong format | TSV event generator; catalog kind metric to event | other VMware sourcetypes untouched |
| Duo (5 sourcetypes) | `ctime` `Fri <MMM DD> 2026` hard-coded weekday and year, zero-padded day; static epoch `timestamp` of 2026-09-18 | `Tue Nov  3 10:33:44 2026` | event | weekday never followed the date; add-on dates events from the epoch field | render ctime from the event instant, epoch from the same instant | add-on `TIME_PREFIX` reads the epoch, so the stale epoch mis-dated events |
| `cisco:ios`, `cisco:ise:syslog` | direct vendor syslog only | SC4S shape: header-less IOS; ISE without `<PRI>`, with device address and a second stamp | event | no way to produce the observed shape | explicit `ingestion_profile` (`direct` default, `sc4s`) | no global stripping; unsupported sourcetypes refuse the profile |

## 2. IOS XR metrics

- **Before / after:** `in_octets` etc. in `cisco_mdt_metrics` with NetSpout bookkeeping as dimensions, to 14 observed series in the transport's metric index: 8 `interface_generic_counters.*` counters on path `.../generic-counters`, 3 (`bandwidth`, `input_load`, `output_load`) on `.../data-rate`, and `total_cpu_{one,five,fifteen}_minute` with `node_name`, `path`, `subscription=health`. Counters are cumulative and increase per interface; values stay inside the observed min/max; `source` is the device address; `device/host/vendor/status/action` are not sent (`netspout_*` bookkeeping dimensions remain).
- **Profile:** metric profile `iosxr_cisco_metrics` on `cisco:ios:mdt:metric` through Generate Data.
- **Tests:** payload names, dimensions, path, value ranges, cumulative counters, source and index against `phase8_metric_evidence.json`; gNMI/scenario record shape unchanged.
- **Live (isolated lab, new metric index `cisco_metrics`, `mstats`/`mcatalog`): 12 of 12 checks pass** (names, datapoint counts and value sums equal to what was sent, dimensions, path, ranges, time within 2 s of send, source, per-interface counter series). `mpreview` was not used and its validation is not claimed (it was denied on the reference instance).
- **Limitations:** 14 of the 330 observed names; dimension sets of the other 316 were not observed and were not invented; `sourcetype` stays `cisco:ios:mdt:metric` (real senders left the default `httpevent`); the real HEC request shape is unknown; the default metric index name is still `cisco_mdt_metrics` (set `hec_metric_index` to `cisco_metrics`); counters restart per call.

## 3. Meraki security appliances

- **Before / after:** 150 mixed lines to the 99 network events (`occurredAt, networkId, type, description, category, eventData, organizationId`). A family contract (`real_format_generators.FAMILY_CONTRACTS`) makes a mixed sample set invalid (`SAMPLE_INVALID`). `occurredAt` is rendered at generation time in the observed format.
- **Tests (negative included):** AMP-style, Air Marshal and non-JSON events rejected; a mixed sample file makes the sourcetype unsupported; shipped sample and the real fixture conform; generated batches never contain a foreign family.
- **Live (Splunk_TA_cisco_meraki 3.5.0): 9 of 9 pass:** 30 of 30 events, no `eventType`/`ts`/`ssid` field, the add-on extracts every field the real data shows, the add-on's `occurredAt` time rule parses the generated value, and NetSpout metadata no longer appears under bare names (protocol, vendor, node_type were).
- **Limitations:** the real instance runs add-on 3.2.0, the lab 3.5.0; only the network-event family is covered.

## 4. VMware performance

- **Before / after:** blocked with no usable generator, to one TSV event per row: `moid, uuid, instance, samp_int` plus 15 counter columns, 19 tab-separated columns, no header, no JSON; source `VMPerf:HostSystem`, host a vCenter name, event index, explicit HEC time. Column order and delimiter follow the Splunk_TA_vmware 4.2.1 collector (`performance_handlers._output_results`) and the fixture.
- **Scope:** `vmware:perf:cpu` only. `vmware:perf:net` and other VMware generators are unchanged (tested). The shipped fabricated-JSON `vmware-esx-perf.yml` is no longer reachable for `cpu`; it was not edited.
- **Tests:** 19 columns, numeric type per column equal to the fixture, zero columns stay zero, no JSON/header, routed as an event, not blocked by capability.
- **Live (Splunk_TA_vmware 4.2.1): 10 of 10 pass, status FORMAT_VERIFIED, not SPLUNK_VERIFIED:** tabs preserved byte for byte, sourcetype/source/host/index correct, stored in an event index, `_time` equals the explicit HEC time (the add-on sets `MAX_TIMESTAMP_LOOKAHEAD=1`), NetSpout metadata not under bare names.
- **Limitations:** the add-on that names the 15 counters (field extraction) was not available, so column meaning and value ranges are not verified; values vary around the single observed row. The two-app package would not install (a scratch copy of the `Splunk_TA_vmware` directory was used; the package was not modified).

## 5. Duo timestamps

- **Before / after:** `Fri Nov 03 ... 2026` to `Tue Nov  3 20:18:47 2026` (weekday from the instant, space-padded day, UTC), with `timestamp` rendered from the same instant. Applied to the five Duo YAML samples that carried the pattern and to the native admin/activity log (`asctime_utc`).
- **Tests:** leap day, a non-leap century, both New York DST transitions, the year boundary and the real fixture instant; aware inputs are converted to UTC (23:30 on New Year's Eve in New York is already Friday in UTC); every Duo sample renders `ctime` and epoch consistently.
- **Live (CiscoSecurityCloud 3.7.3): 31 of 31 pass:** for all five sourcetypes `ctime` matches the epoch, the add-on's `TIME_PREFIX` reads the epoch through the HEC raw endpoint, and `ctime` agrees with Splunk's `_time`.
- **Limitations:** other Duo sourcetypes (`endpoint`, `authentication`, ...) and the plain `.sample` files carry static text and were not changed; the add-on's field extraction was not part of the check.

## 6. IOS and ISE ingestion profiles

- **Definition:** `docs/contracts/phase8/ingestion_profiles.json`. `direct` is the default and unchanged. `sc4s` exists only for `cisco:ios` (header-less `%FAC-SEV-MNEM: text`, source `sc4s`, host = device address) and `cisco:ise:syslog` (no `<PRI>`, `<stamp> <device address> <stamp> <node> CISE_...`, source `sc4s`). Other sourcetypes refuse any profile but `direct`. Events that cannot be expressed in the profile are never guessed.
- **Tests:** shapes match the fixtures; direct keeps headers and `<PRI>`; `cisco:ftd:syslog`, `cisco:asa`, `cisco:sdwan:utd:logs` refuse `sc4s` and keep their headers.
- **Live (TA_cisco_catalyst 4.0.60): 43 of 43 pass** for both profiles of both sourcetypes: raw text is exactly what was sent, sourcetype/index/source/host follow the profile, `_time` equals the explicit HEC time, the add-on extracts facility, mnemonic and severity for IOS in both shapes and parses the ISE in-event time through the raw endpoint, and `vendor` is the add-on's value.
- **Found and fixed:** ISE indexed NetSpout's `src_ip` and `node_type` under bare names.
- **Limitations:** the `sc4s_*` indexed fields and SC4S timezone handling are not reproduced (only their names/offset were observed); ISE extraction was compared between profiles, not against a field list from the add-on.

## 7. Field ownership (found by the live checks)

Bare NetSpout values were indexed under vendor/CIM names for ISE, Meraki, VMware and the five Duo sourcetypes. They join a new `NAMESPACED_ONLY_SOURCETYPES` set (bare names not sent, `netspout_*` copies kept). `TA_PARSED_SOURCETYPES` (Phase 4 live evidence) is unchanged and `tests/test_field_ownership.py` still enforces it; a new test ties the new set to passing Phase 8 evidence.

## 8. Regression

| Live path (Phase 4 specs, unchanged) | Phase 4 | Phase 8 on the final code |
|---|---|---|
| `cisco:asa` (Splunk_TA_cisco-asa 6.1.2) | 131 pass | 131 pass, 0 fail |
| `cisco:ios` (TA_cisco_catalyst 4.0.60) | 43 pass, 3 not run | 43 pass, 0 fail, 3 not run |
| `fortigate_traffic` (1.6.10) | 79 pass, 2 not run | 79 pass, 0 fail, 2 not run |
| `pan:traffic` (4.0.0) | 96 pass | 96 pass, 0 fail |

Test totals (64 relevant files: generator, sample replay, capability status, preview, dispatch, scenario, field ownership, plus the new Phase 8 file): **4,625 passed, 8 failed, 2 skipped**, 1,918 subtests passed. The Phase 8 file alone: 43 passed. The 8 failures are the same ones that fail on pristine `508460e`: 7 subtests of `test_gate9_5_telemetry_semantics::test_01` and `test_gate6_integrity::test_07_successful_hec` (order-dependent; passes when the file runs alone, fails in the same grouping at `508460e`). `test_sec2c_dispatch_redaction` failed twice in the first baseline run, which overlapped my first edits, and passed on pristine HEAD and in every later run, so it is treated as flaky, not as a Phase 8 effect. Four existing tests were updated because they encoded the old behaviour: `test_phase1_metric_path` (old OpenConfig metric names) and three in `test_phase6_capability` (`vmware:perf:cpu` as a routing conflict).

## 9. Capability status

`vmware:perf:cpu` moved UNSUPPORTED to GENERATOR_UNVERIFIED (routing block removed; the two remaining routing conflicts are `cisco:thousandeyes:metric` and `cisco:intersight:metrics`; 6 of 372 scenarios stay blocked, all by ThousandEyes). No entry was promoted to VERIFIED: that stays reserved for the spec-based add-on checks, and this phase used a different harness. The Phase 8 live evidence is attached to the affected entries as notes. Phase 5 matrix and reference docs were regenerated; only the `vmware:perf:cpu` row changed.

## 10. Not done

- Phase 7 item 5 (RFC 3164 space-padded day for single-digit days in BSD syslog generators) was not changed.
- The Playwright browser spec was edited for the two remaining conflicts but not re-run.
- No generated data was sent to the reference instance, as required; metric values were never compared to real values beyond observed ranges.
