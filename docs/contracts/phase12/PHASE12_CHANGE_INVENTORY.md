# Change inventory — `recovery/phase1-ta-compat` vs `origin/main`

> **Correction to Phase 11.** The Phase 11 PR review compared the branch with the **local** `main` (`b9521c1`), which is stale. The merge target is **`origin/main` (`3f2e63f`, "Merge pull request #4 … complete-scenario-coverage-v2", 2026-11-02)**. `origin/main` is an ancestor of this branch, so the merge is a fast-forward-able set of **21 commits, 728 files** (423 added, 304 modified, 1 deleted; +225,244 / −1,017 lines), not "196 commits, 2,357 files". The ~178 earlier commits are already on `origin/main`. Local `main` should be updated (`git fetch && git branch -f main origin/main`, or `git switch main && git pull --ff-only`); I did not touch it. `PHASE11_PR_REVIEW.md` carries a pointer to this correction.

The 21 commits are the recovery phases: 1 (native ASA generator, MDT metric path), 2 (structured YAML sample replay), 3 (`cisco:asa` against the real add-on; HEC fields no longer shadow add-on fields), 4 (14-add-on inventory, add-on-backed registry, mismatch report, field-ownership policy), 5 (171-package inventory, vendor ids), 6 (three-section UI, capability status), 7 (read-only discovery), 8 (real telemetry formats and IOS XR metrics), 9 (browser-to-Splunk acceptance), 10 (Palo Alto threat/system, RC lab, package audit, PyYAML fix), 10.1 (engine address setting, multi-sourcetype, scenario preview, investigation), 11 (docs) and 12 (packaging fixes, UI fix).

Counts come from a fixed path rule (last section): every file is in exactly one row. Nothing was removed from the catalog.

| Subsystem | Files | Lines (+/−) |
|---|---|---|
| Splunk app and UI | 20 | +805 / −105 |
| Gateway and engine connection | 3 | +88 / −11 |
| PulseForge Engine | 3 | +249 / −19 |
| Generators and TA compatibility (core + mirrors) | 49 | +25,208 / −192 |
| Catalog and sample replay | 20 | +1,481 / −78 |
| Scenarios | 2 | +3 / −3 |
| Dashboards | 225 | +535 / −447 |
| Packaging | 8 | +22 / −67 |
| Tests and evidence | 335 | +161,823 / −29 |
| Documentation | 50 | +33,050 / −15 |
| Developer scripts and config | 13 | +1,980 / −51 |

Inside those rows: the mirrors of `src/netspout_core` (14 files in `netspout/bin/netspout_core`, 13 in `netspout/bin`, 13 in `backend/app`, against 12 changed source files), catalog JSON copies (6 `catalog_data`, 2 `netspout/catalog`, 2 canonical `catalog/`), the built UI bundle (3 files), 292 evidence files (156,695 lines, mostly JSON and screenshots) and 29 test files (+2,855) plus 4 Playwright specs (+1,141). **No tracked release binary and no root-level stray file is changed by this PR** (see the last table).

## 1. Splunk app and UI (20 files)
- **Key changes:** Generate Data / Scenarios / Connections UI (`frontend/src`, 13 files, +779), engine connection card, per-sourcetype Outcome and Investigate block, new `netspout_run_investigation` view, `restmap.conf` (+13) and `web.conf` (+4) for the gateway, version 2.0.1, rebuilt bundle.
- **Risks:** the bundle is generated from `frontend/src`; the rebuild in a clean worktree reproduced the committed bundle exactly. A UI race (typed URL overwritten by the first status load) was found by the packaged test and fixed in Phase 12.
- **Tests and evidence:** packaged browser acceptance (asa, ios, fortinet, pan, metrics, multi, engine), 26-spec browser regression on the source stack.
- **Unresolved:** Chromium only; tested through Splunk Web on one Splunk version.

## 2. Gateway and engine connection (3 files)
- **Key changes:** `netspout_gateway.py` reads the engine URL only from `netspout_engine.conf` (+ spec). No default and no environment variable; 503 "Engine not configured." / 502 "Engine not connected."; `GET/POST /engine` with role check and URL validation.
- **Risks:** a breaking change for 2.0.0 installs (one-time URL entry; see `PHASE11_UPGRADE.md`). The handler caches the URL for 5 seconds, so an edit made outside Connections (directly in the conf) is seen after up to 5 s (observed in the Phase 12 lab); a save through Connections refreshes it.
- **Tests and evidence:** `tests/test_phase101_gateway_engine.py`; packaged missing/unreachable engine test; in-place 2.0.0 → 2.0.1 test.
- **Unresolved:** TLS to the engine; an engine running as a VM service.

## 3. PulseForge Engine (3 files)
- **Key changes:** `backend/app/main.py` (+multi-sourcetype runs, scenario preview, per-sourcetype verification with `mstats`, `PARTIAL`), `backend/requirements.txt` (PyYAML), version 2.0.1.
- **Risks:** `main.py` is one 3,793-line file. The engine package carries both `backend/app` and `src/netspout_core`.
- **Tests and evidence:** `tests/test_phase101_multi_source.py` (12), packaged multi group (8), Docker engine built from the tarball.
- **Unresolved:** VM service install, TLS, non-Docker host.

## 4. Generators and TA compatibility (49 files)
- **Key changes:** 12 changed modules in `src/netspout_core` (ASA/PAN/IOS generators, dispatcher, delivery monitor, capability, YAML sample replay), their mirrors, field-ownership so NetSpout fields no longer shadow add-on fields, six verified sourcetypes.
- **Risks:** 78 modules are mirrored to three places; Phase 12 audit found **0 differences in 266 mirrored files**, and fixed a guardrail that covered only 59 of the 78 modules.
- **Tests and evidence:** 4,658 passing tests in the Phase 10.1 regression and a re-run this phase (9 failures, all outside this PR's change; see `PHASE12_MERGE_READINESS.md`); six sourcetypes verified against the vendor add-ons in the lab (`tests/ta_specs`, `docs/contracts/ta_live_results.json`).
- **Unresolved:** every other sourcetype is generated but not verified in a packaged install.

## 5. Catalog and sample replay (20 files)
- **Key changes:** `capability_status.json` and `sourcetypes.json` (canonical + copies), `yaml_sample_replay.py`, recorded YAML samples under `netspout/appserver/static/samples` and `netspout/samples/meraki_securityappliances.sample`.
- **Risks:** low (+1,481 lines). The 40 MB scenario catalog and the raw reference samples are **not** in this PR; they are already on `origin/main`.
- **Tests and evidence:** YAML replay tests, `tests/test_phase8_real_formats.py`.
- **Unresolved:** none specific to this PR.

## 6. Scenarios (2 files)
- **Key changes:** only `docs/reference/scenario_coverage.json` and a dashboard-builder script touch scenario files; the scenario preview endpoint is counted under the engine. No scenario definitions changed.
- **Risks:** only `paloalto_threat_investigation` was run end to end with its dashboard; the other 371 definitions are not claimed compatible.

## 7. Dashboards (225 files)
- **Key changes:** 224 Simple XML views modified by one regeneration (Phase 4 field ownership: queries read `netspout_status` / `netspout_action` / `netspout_signature` and rename them, instead of bare names the add-ons own), plus the new `netspout_run_investigation.xml`.
- **Risks:** a mechanical, repeated change to the same few lines in 224 files; not every view rendered in a browser in a packaged install. Spot-checked: the Palo Alto Studio dashboard and the run-investigation dashboard return the run's data.
- **Tests and evidence:** 14 dashboard searches for the PAN scenario; dashboard data-validation evidence from earlier phases.

## 8. Packaging (8 files)
- **Key changes:** app.conf / app.manifest version, `sync_core.py`, `verify_sources.py`, `build_engine_package.py`, `.gitignore` (private sample folders), `Dockerfile.standalone` unchanged in this PR. **Release binaries are not modified by the PR.**
- **Risks and answer:** the tracked 2.0.0 binaries on `origin/main` are stale against the 2.0.1 source (`PHASE12_BINARY_POLICY.md`).
- **Evidence:** package audit of RC4 (3 archives, 0 findings), RC3 reproduced from a clean checkout.

## 9. Tests and evidence (335 files)
- **Key changes:** 29 test files, 4 Playwright specs, isolated labs (`tests/lab/rc_install`, `ta_validation`), acceptance/audit/RC scripts, 292 evidence files.
- **Risks:** evidence size; labs read credentials only from git-ignored `.env.lab`.
- **Unresolved:** the Phase 4 specs bound to the protected lab are not run.

## 10. Documentation (50 files)
- Phase 5–12 reports and contracts, support matrix, runbook, upgrade guide, install-guide corrections. Older Gate and Phase reports that already sit on `origin/main` still describe 2.0.0 behaviour (not rewritten).

## Accidental, generated, duplicate and unrelated content
| Item | Finding | In this PR? | Recommendation (needs your decision) |
|---|---|---|---|
| Tracked `netspout.spl`, `netspout_cloud.spl`, their `.manifest.json` | stale 2.0.0 builds, tracked on `origin/main` since PR #4 | **no** (unchanged) | Policy A in `PHASE12_BINARY_POLICY.md` |
| 20 root-level one-off scripts and notes (`add_paloalto_sourcetypes.py`, `analyze_actual_coverage.py`, `verify_indexing.py`, `phase4a/4b_*`, `PHASE4C_FINAL_SUMMARY.md`, …) and `design/*.zip` | Phase 4 ad-hoc harnesses, design hand-offs. No hard-coded credentials (they read `PULSEFORGE_LAB_HEC_TOKEN` / `SPLUNK_PASSWORD`); several send to a HEC when those are set | **no** (already on `origin/main`) | optional separate cleanup PR (move to `scripts/legacy/`) |
| Mirror trees and catalog copies | generated, byte-identical to the source (verified) | yes (small) | keep; review only `src/netspout_core` and `catalog/` |
| `netspout/appserver/static/dist` | generated bundle committed on purpose | yes (3 files) | keep; a clean rebuild equals it |
| `docs/verification/evidence/**` | generated evidence (292 files) | yes | keep, or move to an artifact store later |
| `netspout/bin/main.py` vs `backend/app/main.py` | two different entry points, not mirrors | no change | note for later cleanup |
| Untracked `samples/` (8.2 GB), `netspout/datapet-test-es/` (1 GB), `docs/recovery/` | local only; first two git-ignored | **no** | keep local; move out of `netspout/` |

## Path rule used for the table
First match wins: tests/evidence (`tests/`, `frontend/tests/`, `docs/verification/`, `docs/acceptance/evidence`, `scripts/phase*|run_*|validate_*|render_*|lab_*|benchmark_*|test_*`) → root-level stray or `design/` → packaging (`*.spl`, `.gitignore`, `.dockerignore`, `Dockerfile.standalone`, app.conf/app.manifest, build/sync/verify scripts) → gateway → dashboards (`netspout/default/data/ui/views/`, `dashboards/`) → scenarios (path contains `scenario`) → catalog/replay → app/UI (`frontend/`, `netspout/appserver|default|metadata|README`) → engine (`deploy/`, `backend/app/main.py`, `requirements.txt`, destination/run-progress modules) → generators/core/mirrors (`src/netspout_core`, `netspout/bin`, `backend/app`, `docs/contracts/ta_*`) → documentation → other.
