# PulseForge Release Readiness Assessment (validation before expansion)

Scope of this pass: reconcile coverage evidence, run real vendor-TA parsing validation where packages exist, keep scenario maturity gates
unchanged, and record exactly what is and is not proven. **No new sourcetypes or generators were added.** All numbers below are produced by
`scripts/generate_coverage_report.py` and `scripts/build_ta_matrix.py` from committed evidence; commands to reproduce are in section 8.

Companion documents: `pulseforge_sourcetype_coverage.md` (reconciled coverage), `pulseforge_ta_validation_matrix.md` (TA matrix and 20-generator backlog),
`pulseforge_scenario_coverage.md` (scenario maturity), `pulseforge_phase4_prioritized_backlog.md` (blockers).

## 1. Verdict

| Area | Status |
|---|---|
| Demo workflows (Explorer operational + security, Dashboard Studio, gateway, RBAC) | Unchanged and still passing; deployed lab files hash-equal to source |
| Native generator coverage | **158 of 348 (45%)**; 70% target (244) not reachable on current evidence |
| Vendor-TA parsing | **Windows (6 channels) and Sysmon checked in an isolated lab; no other vendor TA run** (packages unavailable) |
| CIM data models, detection outcomes, ES | **Not validated** (Splunk_SA_CIM and ESCU not available) |
| Scenario maturity | **No promotions**; gates unchanged |
| Financial / telecom libraries | **Blocked**: original files and IDs not supplied |
| Regression vs baseline | 42 failing IDs, identical set to the live-lab baseline (0 new, 0 fixed) |

## 2. Reconciled inventory (348 catalog sourcetypes)

Partition (disjoint, sums to 348): **158 native + 143 sample-replay-only + 47 no generator.**

| Component of the native count | Count |
|---|---|
| Pre-Batch-5 baseline (re-derived with the original scanner rules; not a recorded historical number) | 112 |
| Scanner discovery corrections (generators that already existed) | +6 |
| Batch 5 net new (31 registered; `cisco:sdwan:BGP-5-ADJCHANGE` already native) | +30 |
| Batch 6 net new | +10 |
| **Now** | **158** |

The sum closes largely by construction (differences of sets), so it proves no sourcetype is double counted or dropped, not history.

| Measure | Count | Note |
|---|---|---|
| Byte-verified (HEC bytes equal indexed `_raw`) | 128 | all 128 are native; 30 native generators have no byte verification |
| Independently indexed, file-level harness evidence | 136 | counts every result file written by a post-then-search harness |
| ... of which row-level proof (`indexed_rows>0` or per-row `matches>=1`) | 76 | the other 52 come from older files with no row counts |
| ... of which run-evidence name mentions only | 8 | weakest; not row-level |
| Parsed by a real vendor TA in the isolated lab (this pass) | 6 channels | Windows/Sysmon; extraction, timestamps, tags only |
| Vendor TA validated, full or partial (earlier lab) | 1 | Cisco ISE only |

Definition changes made in this pass (not new capability): "independently indexed" rose 105 to 136 because the old filter trusted only result files whose
name contained "live"; the harness for every file posts to HEC and searches Splunk. The scanner also missed generators declared as default arguments or in
dedicated generator modules (+6, each inspected by hand: `pan:system`, `netspout:snmp:trap`, `netspout:snmp:poll`, `cisco:duo:remote:vpn`,
`cisco:catalyst:clienthealth`, `meraki:assurancealerts`). Five more sourcetypes (arista:eos:syslog, cisco:duo:auth, dell:os10:syslog, fortinet:fortigate:event, juniper:junos:syslog) have hand-authored fault-injection templates with no format
reference; they are reported separately and **not** counted as vendor-native.

Reachability: 156 of 158 native sourcetypes are emitted by at least one customer-facing path (118 by authentic scenario packs, 76 by native
Single Event/Sourcetype registries, 29 listed by ScenarioRunner scenarios, label-level). Only `sc4snmp:event` and `snmp:trap` are on none.

## 3. Vendor TA validation (what was actually run)

Isolated container `netspout_tavalidation_splunk` (Splunk Enterprise 10.2.7, own network and volumes, ports 19000/19191/19088; the demo lab was not
modified). Installed: Splunk Add-on for Microsoft Windows 10.0.1 and Splunk Add-on for Sysmon 5.0.1, both verified through Splunk's
`/configs/conf-props` endpoint, not just file copy.

14 native Windows/Sysmon events (distinct sourcetype x EventID from the authentic scenario packs), each sent two ways: exactly as NetSpout dispatches
(A) and as a forwarder would (B). Results:

* Extraction of the fields each event carries: mean 0.976; 13 of 14 events 1.0; the exception is System 6005 (`param1` not extracted).
  This is a self-consistency check: it shows the TA parses what the generator emits, not that the generator emits every field a real source would.
* Metadata: NetSpout's sourcetype/source convention is normalized by the Windows TA's own index-time fixups, so variant A extracts like B.
* Timestamps (48 h shifted event time): Sysmon parses the event time (4/4, TA rule `<Data Name='UtcTime'>`); Security, System, PowerShell, NTLM and
  Defender do not, because the Windows TA defines no timestamp rule for those channels (props dump in the evidence). NetSpout stamps `_time` with send
  time (variant A: 0/14 by construction of that path). One authentic-bytes control (0/3) is consistent with this.
* Tags the TA assigned: 14/14 events, for example 4624/4625 `authentication`, Sysmon 1/7/10 `process`+`report`, Sysmon 22 `dns`+`resolution`.
* **Not validated:** CIM data models, detection outcomes, ES behavior, behavior on a real Windows forwarder.

Prioritized 20-generator backlog (Cisco networking/security, Palo Alto, Linux, DNS): see the matrix. **All 20 are BLOCKED_PACKAGE.**

## 4. Defects and risks found in this pass

Fixed:
1. **Single Event mislabeling.** For multi-sourcetype vendors, Single Event mode picked a random vendor-level sample, so a Sysmon request could return a Security 4624 or a
   *Linux* Sysmon event. The fallback is now allowed only when the vendor has one active sourcetype. **Behavior change: 87 active catalog sourcetypes that were answered
   with an unrelated sample now report `TELEMETRY_NOT_GROUNDED`** (largest: cisco_ios 10, microsoft_windows 8, amazon_aws 4, microsoft_365 4, linux_infrastructure 4).
   Wave/core formatters are not wired into Single Event mode; that is new exposure work, not done here.
2. **Fail-closed regression I introduced (Batch 5).** The generator routes fell back to the default transport when nothing was configured, so `dispatch:true` no longer
   failed closed; earlier full runs passed only by test-order luck. Now the Connection Center destination is used only when configured, and an omitted index is checked against
   the allowlist too. Tests cover unconfigured, configured, disallowed and omitted index.
3. **Coverage counting**: indexed-evidence undercount and the missed generators above.

Open (not fixed):
* ~~A caller-supplied `transport_config` bypassed the index allowlist.~~ **Fixed** (see section 11): both routes that accept one now authorize it.
* `catalog/vendors.json` Splunkbase IDs disagree with `telemetry_catalog.json` and the ISE-verified ID (ISE 2736 vs 1915; ASA 6259 vs 7404). Confirm IDs before any download. (The wrong `required_ta` on 100 Cisco rows is corrected, section 11.)
* The coverage scanner uses pattern matching for generators; the six corrections were inspected by hand, and any future ones need the same check.
* NetSpout's dispatcher uses send time for `_time` and a constant `source`; correct for simulation, but detections written against event time or per-channel `source` depend on the TA's fixups.

## 5. Scenario maturity

No promotion. 58 catalog scenarios: GOLDEN_PATH_CERTIFIED 13, E2E_VALIDATED 4, FORMAT_VALIDATED 2 (governed), CONTRACTED 39. Runnable 43 (17 ScenarioRunner, 26 packs), contract-only 15
with no Run action. Live-verified pack runs: 5. Dashboard-verified: 1 (DNS operational, Dashboard Studio). Detection-verified: 1 (React2Shell saved search fired on the scheduler).
Byte equality or successful ingestion never promotes a scenario; the 26 packs lack topology wiring, an independent acceptance retest, dashboards and detections.

## 6. Release blockers and exact inputs needed

| Blocker | Input needed |
|---|---|
| Cisco, Palo Alto, Linux, DNS TA validation | Authenticated Splunkbase downloads of the packages in the matrix backlog (this repo never downloads TAs); re-fetch ISE 1915 5.0.0 |
| CIM compatibility | Splunk Common Information Model (`Splunk_SA_CIM`) |
| Detection outcomes | ESCU (`DA-ESS-ContentUpdate`) macros; none were written here |
| Financial/telecom libraries | The original 100 financial and 100 telecom use-case files with their original IDs |
| FortiGate (7 rows) | Pinned authentic logs or the PDF samples (official HTML pages print field tables only) |
| 70% native target | Authentic captures or documented sample lines for ~86 more sourcetypes; the remainder are demo-authored samples |

## 7. Claims explicitly not made

No vendor TA compatibility beyond Windows/Sysmon; no CIM data model result; no detection firing beyond the existing React2Shell saved search; no Enterprise Security
behavior; no TA parsing for any Cisco, Palo Alto, Linux or DNS source; no scenario promotion.

## 8. Reproduce

```
python scripts/generate_coverage_report.py [--check]      # reconciled coverage and scenario reports (assertions run in --check too)
tests/lab/ta_validation/lab.sh up                          # isolated lab; credentials generated into git-ignored .env.lab
#   install the Windows 10.0.1 and Sysmon 5.0.1 packages (REST apps/local, filename=true), create index ta_validation, restart
PYTHONPATH=src:backend python scripts/validate_ta_windows.py
python scripts/build_ta_matrix.py
tests/lab/ta_validation/lab.sh down                        # stop the isolated lab (volumes kept); `destroy` removes only its volumes
```

Tests: `tests/test_ta_readiness.py`, `tests/test_universe_batch2.py`, `tests/test_universe_batch5.py`, `tests/test_universe_batch6.py`.

## 9. Independent review disposition

A fresh agent re-ran the coverage script and the new tests and attacked the claims. Confirmed: the counts, mirror sync, no secrets in the new files, `.env.lab` ignored, no weakened assertions.
Acted on: the redefined indexed measure (now disclosed and split into row-level versus file-level), the tautological test (replaced by tests that exercise the harness rules),
the overstated "closes exactly" wording, the allowlist gap when `index` is omitted, verdict names and control wording in the matrix, and the TA measure missing from the coverage report.
The explicit-transport allowlist bypass the review flagged was fixed in the follow-up batch (section 11).

## 10. Hygiene

The isolated lab password was echoed once into this session's terminal output by a mis-quoted command; it was a generated, loopback-only lab credential, rotated immediately
through Splunk's REST API and never committed. `tests/lab/**/.env*` is git-ignored.

## 11. Follow-up batch: industry coverage, incident packs, allowlist, TA mapping, curated stories

**Security fix.** `transport_config` supplied by a caller (`/api/generate/scenario-pack`, `/api/scenarios/{id}/run`) is now authorized: when the Connection Center is
configured it must target the configured destination (same host:port) and both the event and metric index must be on the allowlist (403, or 422 for an unsafe name, before
anything is sent); a request can no longer replace the saved transport. `tests/test_transport_allowlist.py` covers wrong index, wrong metric index, redirected URL, other port,
defaulted index, both routes and the unconfigured legacy path.

**37 incident packs now runnable** (27 network + 10 telecom, already in the repo but invisible to the product): deterministic, 30 logs + 10 gauge records, correlated by run id, NetSpout-defined MODELED
telemetry (`netspout:*`, not vendor-native), maturity CONTRACTED. Live evidence (`docs/verification/evidence/incident_packs/live_results.json`, 37/37 PASS): 40/40 HEC accepted, per-phase log counts exact,
`mstats` datapoint counts and per-metric averages equal to the generator's values, dimensions present; two packs re-proven through the Explorer UI inside Splunk Web (30/30 events plus mstats 50/50 and 30/30).
Defect found by that verification: the Explorer's new metric check used `mstats` without `metric_name=*` and would have reported 0 datapoints for every pack; fixed with a regression test.

**Industry coverage (18 approved industries).** `catalog/scenario_candidates.json` records 209 documented, CATALOGED candidates (114 selected entries from the MIT-licensed community use-case catalog pinned
to commit `8d26053`, 95 Cisco 100 definitions that are not execution-enabled; 4 already-promoted Cisco 100 scenarios excluded to avoid double counting). Only id, title, labels, URL and an unverified data-source hint are
recorded. Mapping basis is SOURCE_LABEL, EDITORIAL_TITLE or EDITORIAL_DOMAIN; government subdomains only where a title supports one (Federal Civilian and Compliance has none). The Explorer shows them as
`CATALOGED`, never runnable, with no Run action. The 18-industry matrix is in `pulseforge_scenario_coverage.md`.

**Curated Analytic Stories.** `catalog/curated_analytic_stories.json`: 20 stories (14 industries) whose own text names the sector as a threat target; every original `research.splunk.com` URL was HTTP-checked (57 of 365
stories have no resolving page and were excluded). Curated is not executable: only a runtime-approved detection makes a story runnable (still only React2Shell).

**TA mapping.** 100 Cisco rows no longer claim the Unix and Linux add-on (`required_ta: null` + review record). No replacement ID is asserted.

**Evidence limits unchanged.** No sourcetype was promoted: the remaining 143 sample-replay and 47 missing sources have no authentic format reference, and the pinned attack-data corpus backs none of them.
The original 100 financial and 100 telecom files are still missing; when supplied they should be imported as a new source in `scenario_candidates.json` using their original IDs and the same dedupe rule.
