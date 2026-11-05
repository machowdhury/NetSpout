# Phase 2: sample replay repair (evidence)

Branch `recovery/phase1-ta-compat`. Inventory: `sample_inventory.json` (every YAML, per-file status). Metric gate: `metric_sample_gate.json`. Registry: `docs/contracts/ta_compatibility_registry.json`.

## Defect (before)
`_parse_sample_file` emitted every YAML line longer than 20 characters that did not look like a key header, and never rendered `$TOKEN$` placeholders.
`cisco:asa` (`cisco-asa.yml`): 27 "events", 25 of them failed the ASA format contract, 8 contained unrendered tokens. Examples emitted as telemetry:
```
randomizeEvents: false
replacement: "Jan 02 15:04:05"
choice: fw-cisco-asa-01
$TS$ $HOST$ %ASA-6-302013: Built outbound TCP connection 984210 for outside:198.51.100.80/443 ...
```
Across the 220 shipped YAML files: 220 emitted non-telemetry lines, 115 emitted unrendered tokens.

## After
`src/netspout_core/yaml_sample_replay.py` parses with PyYAML and reads only `samples[].lines[]._raw`, `fromRaw` (one event per line) and `fromSample` (CSV `_raw` column). `lines[]` entries with an empty `_raw` next to `fromRaw`/`fromSample` are metadata (sourcetype/source/host/index) for those events, never events. Tokens are rendered fresh on every call (the old cache froze timestamps).
```
Nov 03 15:49:15 fw-cisco-asa-01 %ASA-6-302013: Built outbound TCP connection 984210 for outside:198.51.100.80/443 (198.51.100.80/443) to inside:10.20.10.45/52140 (198.51.100.200/52140)
Nov 03 15:49:15 fw-cisco-asa-01 %ASA-6-302014: Teardown TCP connection 984210 for outside:198.51.100.80/443 to inside:10.20.10.45/52140 duration 0:02:14 bytes 148920 TCP FINs
Nov 03 15:49:15 fw-cisco-asa-01 %ASA-4-106023: Deny tcp src outside:203.0.113.88/44820 dst inside:10.20.10.5/22 by access-group "outside_in" [0x8f2a1b9c, 0x0]
```
8 events (equals the 8 `_raw` fields), 0 unrendered tokens.

## Counts
| | files | replayable | unresolved placeholders | unsupported | oversize | invalid | config only |
|---|---|---|---|---|---|---|---|
| shipped (`netspout/appserver/static/samples`) | 220 | **220** | 0 | 0 | 0 | 0 | 0 |
| external corpus (`samples/`, not committed, 8.2 GB) | 1359 | **1044** | 34 | 183 | 87 | 8 | 3 |

Not-replayable reasons are explicit per file in the inventory (for example token types `fieldChoice`, `goskew-*`, `epochskew`; regex tokens with several capture groups; files over 8 MB; unresolved `$INDEX$`/`$HOST$`). They are not guessed and not counted as repaired.
Also in the corpus: 3,482 files in total, of which 1,455 `.sample`, 477 `.csv`, 115 `.multi`, 51 `.txt` and 9 `.md`; only files referenced by a YAML `fromRaw`/`fromSample`/choice `sample` are read. `.multi` and unreferenced files are not read.

Limits of this validation: the dry render covers the first 5,000 events of each file; a placeholder further down a very large file surfaces at replay as `SAMPLE_INVALID`, not as silent output.

## Sourcetype safety
Catalog sourcetypes after the change (349): 198 replay from a valid sample, 9 vendor-documented, 2 native (Phase 1), 126 no sample, 9 refused metric replay, 5 refused because the sample file claims a different sourcetype (`cisco:metrics`, `fortinet:fortigate:traffic`, `nutanixpc_syslog`, `nutanixpc_vms`, `radware:cwaf:waf`). Those five were previously relabelled silently; they now return `SAMPLE_INVALID` until each is verified against its TA.

## Metrics
13 catalog metric sourcetypes (`metric_sample_gate.json`): replay is allowed only when every event carries numeric measurements. Result: 2 replay as metrics, 9 refused (`METRIC_REPLAY_UNSUPPORTED`: events have no measurements), 1 sample invalid, 1 no sample (`cisco:ios:mdt:metric` also has the native Phase 1 generator). Log sourcetypes with numeric fields are never converted to metrics. Metric-index verification (mstats) in Splunk was not run in this phase.

## Splunk TA
Verified (official sources): add-on identity and latest version for ASA (Splunkbase 1620, 6.1.2, 2026-07-29, public metadata API); canonical names `cisco:asa`, `cisco:ise:syslog`, `cisco:ios` against Splunk's documentation table. Not verified: any TA props/transforms/field extraction (package download needs an authenticated Splunkbase session). No Splunk instance was used in this phase.
