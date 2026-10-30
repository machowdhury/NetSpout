# Continuous sample replay (2026-10-30)

Code: `src/netspout_core/sample_replay.py` (engine), `replay_service.py` (sessions, limits, restart safety, independent verify), `replay_packs.py` (scenario packs on the engine),
API under `/api/replay/*` in `backend/app/main.py`, Explorer entries `engine: replay_pack`. Sources: `catalog/replay_sources.json` (10 vendored authentic recordings, rules verified at build).
Packs: `catalog/replay_packs.json` (7). Live evidence: `docs/verification/evidence/replay/replay_live.json`. Reproduce: `PYTHONPATH=src python scripts/validate_replay_live.py` (isolated lab only).

## Behaviour (what is guaranteed, and what is not)
| Topic | Behaviour |
|---|---|
| Formats | syslog, CSV (quoted multiline rows), JSON array (each element kept byte-exact), JSON Lines, Apache, Windows event XML, free text with `record_start` for multiline records |
| What changes | Only the bytes of the selected timestamp field. Rules: regex, nested `json_path` (found at the right depth, same-named keys elsewhere are never touched), `csv_column`; formats iso8601, epoch s/ms/us, syslog (year-less), any strptime format; time zones via the tz database (DST honoured); fractional precision, separator and offset style preserved |
| Spacing | Source spacing is preserved (divided by `speed`). An out-of-order source record is clamped to its predecessor and counted (`out_of_order`). Optional `max_gap_s` shortens idle gaps longer than the cap (opt-in, reported as `idle_time_compressed_s`) |
| Loop boundary | Loop k+1 starts `loop_gap_s` after the last event of loop k; default = median positive source spacing (min 1 ms; 1 s with no spacing). Timestamps never overlap or go backwards |
| No trustworthy timestamp | Refused. `fixed_interval` with an explicit interval emits records unmodified and is labelled USER_SPECIFIED_INTERVAL |
| Equal source timestamps | Stay equal (non-decreasing, not strictly increasing): a source with 102 events in one instant replays as a burst |
| Controls | start, pause (holds delivery too; queued events keep their schedule stamps), resume, stop (prompt; unsent events counted `discarded_on_stop`), finite loops or continuous |
| Throughput | `speed` 0.01-1000, `eps_limit` 0.1-2000, bounded queue (1-10000): a full queue blocks the producer, nothing is dropped, waits are counted |
| Counts | generated, delivered, accepted (HEC success code 0), rejected, unknown; `indexed_confirmed` only from an independent Splunk search on the session's unique `source` |
| Restart | Active sessions are persisted; after a restart they report INTERRUPTED and are never resumed or re-sent |
| Destination | Saved Connection Center destination only; caller `transport_config` is refused (422); index must be allowlisted (default `dev_test_replay`); host default `replayed-log-generator`; outside DOCKER_LAB the index must be `dev_*` and `confirm_destination` is required; the product never creates indexes |
| Known limits | Year-less syslog stamps assume a leap year and do not unwrap a year boundary; datetimes hold microseconds (a 7-digit Windows tick fraction round-trips to 6 digits); Ollama's mixed-format log was excluded (no single rule); records are held in memory (200,000 record cap, 2 MB upload cap) |

## Scenario packs
Replay phases (recordings) and native phases (existing authentic packs, regenerated each cycle) are merged on one schedule. Each event carries HEC indexed fields
`netspout_scenario_id / run_id / phase / source_kind / cycle` (never in `_raw`). Independent recordings are aligned in time only (`TEMPORAL_ONLY`); no identifier is rewritten to fake a shared incident.
One-shot playback = `loops: 1`; continuous operation = `continuous: true` (repeating incident cycles with `loop_gap_s` between them). Explorer tier stays CONTRACTED.

## Evidence (isolated Splunk 10.2.7 lab, index `dev_test_replay` created in that lab as a fixture)
`replay_live.json`: every check below is read back from Splunk, not from sender counters. Not validated: TA parsing, CIM, ES, detections, dashboards.
A: HEC acceptance, count equality, index/host/source isolation, current-clock stamps, spacing, loop boundary gap, byte identity except the timestamp, no leak to other indexes.
B: pause stops delivery, resume continues, stop halts, accounting matches Splunk, nothing after stop. C: EPS limit. D: backpressure without loss. E: rejected events counted and not indexed.
F: no-timestamp source refused. G: all 7 packs indexed with per-phase counts, phase order in Splunk time, one run id; continuous pack repeats cycles.
