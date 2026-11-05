# Phase 15 — upgrade, rollback, persistence and recovery

All in disposable labs only. Recorded states: `docs/verification/evidence/phase15/` (`upgrade_*.json`, `rollback_*.json`, `persist_*.json`). The recorder (`scripts/phase15_upgrade_check.py`) compares search counts, index definitions, saved objects and the sha256 of every file in the app's `local/` directory.

Seed data (known, ingested over HEC): 120 events (`ns15:upgrade`) in `idx_network_ops`, 40 events (`ns15:keep`) in a user-created index `ns15_keep`, 30 metric datapoints (`ns15.upgrade.value`) in `cisco_mdt_metrics`; plus a saved search, a custom dashboard and a custom configuration file saved in the app's `local/`.

## Upgrade 2.0.0 → 2.0.1 (lab `nsp15u`) — PASS

Installed the archived 2.0.0 Enterprise package (sha256 `3b086b80…c46f`), seeded, recorded, installed the 2.0.1 candidate over it through Splunk's app endpoint (update), restarted.

| check | result |
|---|---|
| Event counts by search: 120 / 40; metric datapoints by `mstats`: 30 | PASS (unchanged) |
| Indexes survive (`idx_network_ops`, `cisco_mdt_metrics`, user-created `ns15_keep`) with the same data types | PASS |
| Saved search, custom dashboard, custom config values | PASS |
| Files in the app's `local/` unchanged (sha256) | PASS |
| App version 2.0.0 → 2.0.1; dashboards 207 → 432 (225 new) | as expected |
| Engine address after the upgrade | **not configured** (2.0.0 used `NETSPOUT_BACKEND_URL`; 2.0.1 reads only Connections). Gateway answers 503 "Engine not configured." until an admin sets it |
| Engine address configured through the UI, then generation | PASS: packaged `[engine]` test; `asa` group 11/11; `pan` group 3/3 (Palo Alto scenario and its Dashboard Studio dashboard) |
| Data and config unchanged after the generation runs | PASS (`upgrade_2_after_generation.json`) |

Operator action required on upgrade: restart Splunk, then set the engine address once (Connections > PulseForge Engine); upgrade the engine to the 2.0.1 package too.

## Rollback to 2.0.0 (lab `nsp15r`, copy of the upgraded volumes) — PASS for data and config; limited for generation

The upgraded `nsp15u` Splunk volumes (`var`, `etc`) were copied with Splunk stopped into separate volumes; the copy was verified equal to the source first. The archived 2.0.0 package was then installed over the copy and Splunk restarted.

| check | result |
|---|---|
| Copy equals the upgraded state | PASS |
| After reinstalling 2.0.0: event counts 120/40, metric datapoints 30, index definitions, saved search, custom dashboard, custom config, all `local/` file hashes | **PASS** |
| App version 2.0.0; 2.0.1-only dashboards removed (433 → 208, which is the 207 original plus the custom one) | as expected |
| 2.0.0 gateway with the 2.0.0 engine, using 2.0.0's own method (`NETSPOUT_BACKEND_URL` in `splunk-launch.conf`) | `/health` and the catalog answer. Generation under 2.0.0 was **not** run through the UI: the packaged suite targets the 2.0.1 UI |
| Leftover | 2.0.1's `local/netspout_engine.conf` stays (ignored by 2.0.0, harmless) |

Rollback is safe for data and settings on this evidence. Roll the engine back together with the app. Not tested: rollback of a distributed deployment, and a restore from a pre-upgrade backup (the stated mechanism is a backup or volume snapshot taken before the upgrade).

## Persistence and recovery (lab `nsp15`) — PASS

| step | what it is | result |
|---|---|---|
| 1 | restart the Splunk container (volumes and container kept) | data, indexes, config, engine connection PASS |
| 2 | restart the engine container (its state volume kept: `connection.json`, `runs.json`) | gateway reports `connected:true` PASS |
| 3 | **recreate** both containers (`up --force-recreate`; new container ids, same named volumes) | data and config PASS; engine reconnects with the saved address |
| 4 | a new generation run after the recreate | PASS (`asa` group 11/11) |

Restart keeps the container; recreation replaces it and keeps only the named volumes; the recording tap is test scaffolding that lives in the engine container and had to be restarted after recreation (not a product behaviour). `totalEventCount` in index metadata lags behind search results for a short time after ingest; the checks use search counts and treat the metadata as non-decreasing.
