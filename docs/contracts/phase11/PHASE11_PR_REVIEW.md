# PR review summary — `recovery/phase1-ta-compat` → `main`

**Not opened.** This is the draft text and the review, for your decision. Branch head at the start of Phase 11: `cb52875`.

## Size and shape
- 196 commits (2026-10-05 → 2026-11-04) on a merge-base of `b9521c1` (main, 2026-10-02). 2,357 files changed (+1.76 M / −66 k lines): 2,137 added, 219 modified, 1 deleted.
- That is the whole post-main release line, not only the recovery phases: feature work (79 `feat`, 28 `fix`, 26 `docs`, 10 `test` commits), then recovery phases 5–10.1.
- The diff is dominated by generated data and evidence, not logic. Approximate changed lines by area: `netspout/bin` 383 k and `backend/app` 194 k (both mostly catalog JSON and the synced mirrors of `src/netspout_core`), `docs/verification` 365 k (evidence), `netspout/default` 319 k (dashboards, views), `netspout/catalog` 161 k, `docs/contracts` 55 k, `catalog/` ~60 k, `src/netspout_core` 30 k, `netspout/appserver` 21 k (built UI), `frontend/src` 17 k. Tests: 131 files, +22.6 k lines.
- Suggestion: review by area (below) rather than as one diff, and consider squashing or merging with a merge commit rather than rebasing 196 commits.

## What ships (product)
| Area | Paths | Notes |
|---|---|---|
| Splunk app | `netspout/` (default conf, 400+ dashboard views, nav, REST gateway `bin/netspout_gateway.py`, built UI `appserver/static/dist`, `netspout_engine.conf` + spec) | Version 2.0.1 |
| Engine | `backend/app`, `backend/requirements.txt` (adds PyYAML), `deploy/engine`, `deploy/collector` | Packaged as `pulseforge-engine.tar.gz` |
| Shared core | `src/netspout_core` (source of truth) mirrored by `scripts/sync_core.py` into `backend/app`, `netspout/bin`, `netspout/bin/netspout_core` | Never edit the mirrors |
| UI | `frontend/src` (Generate Data, Scenarios, Connections; multi-source, preview, Outcome, Investigate) | |
| Catalog | `catalog/`, `netspout/catalog`, `backend/app/catalog_data` | Data, no secrets |
| Package builders | `scripts/build_splunk_package.py`, `build_splunk_cloud_package.py`, `build_engine_package.py` | |

Phase 10.1 behaviour changes users will notice: **no default engine address** (Connections > PulseForge Engine; `NETSPOUT_BACKEND_URL` no longer read), several sourcetypes in one run, scenario preview, run investigation dashboard, `PARTIAL` verification status, and a run that delivered nothing is `FAILED`.

## What does not ship but is in the diff
- Tests and lab scaffolding: `tests/` (131 files), `tests/lab/*` (isolated Docker labs), `frontend/tests/*.spec.ts`, `scripts/phase*` (acceptance, tap, forwarder, audit, RC installer).
- Evidence and reports: `docs/verification/evidence/**` (511 files, 55 MB of screenshots and JSON), `docs/contracts/phase*/`, `docs/implementation`, `docs/reference` (generated).
- Reference inputs: `catalog/raw_reference`, `catalog/mib_reference`.
- The packages exclude all of this (package audit: 3 archives, 0 findings, git provenance checked).

## Unrelated and untracked files (must not be committed)
| Path | Size | Status | Action |
|---|---|---|---|
| `samples/` | 8.2 GB | untracked, outside any package | Added to `.gitignore` in Phase 11 |
| `netspout/datapet-test-es/` | 1.0 GB | untracked, sits inside the app folder | Added to `.gitignore` in Phase 11. It is inside `netspout/`, so a careless `git add netspout` or a hand-made zip would ship it; the builders use tracked-file lists and the audit proves the RC3 archives do not contain it |
| `docs/recovery/CONTEXT.md` | 8 KB | untracked working notes, mentions an environment | Leave untracked or delete; not for the PR |
| `~/netspout/private-packs/` | outside repo | vendor add-on packages | Never commit |
| `~/netspout/release-candidates/` | outside repo | RC1, RC2, RC3 binaries | Never commit |

No credential files are tracked (`.env.example` templates only). Lab credentials live in git-ignored `.env.lab` files; the package audit also checks the archives for those values.

## Packaging and version consistency
- Version **2.0.1** in `netspout/default/app.conf`, `netspout/app.manifest` (`info.id.version`), `frontend/package.json` and lock, `backend/app/main.py` (two places), `scripts/build_splunk_cloud_package.py`; the RC3 install check proves they match the installed app and the engine's OpenAPI version. `app.manifest` `schemaVersion` 2.0.0 is the manifest schema, not the product.
- **Blocker for a clean merge: the three release files tracked at the repo root are not RC3.**
  - `netspout.spl` (6.6 MB, tracked) and `netspout_cloud.spl` (264 KB, tracked) are the 2.0.0 builds from the earlier release commit; `pulseforge-engine.tar.gz` is untracked (ignored) at the root.
  - RC3 binaries (2.0.1) exist only in `~/netspout/release-candidates/rc3-ae3342d/`. Merging as is would put a stale 2.0.0 binary next to 2.0.1 source.
  - Decision needed: stop tracking binaries in git and publish RC3 (or its rebuild) as release assets; or replace the tracked files with the final build. I did not touch them (standing constraint).
- Builds are not byte-reproducible; the manifest records commit, sizes and SHA256.
- `docs/guides/*` and `docs/INSTALL.md` were corrected in Phase 11 to remove the old `NETSPOUT_BACKEND_URL` instructions. `scripts/validate_installed_app.py` still describes the old variable; it is a legacy protected-lab script not used by RC3.

## Upgrade implications
See `PHASE11_UPGRADE.md`. Summary: the engine URL must be entered once after upgrading; the engine needs its dependencies refreshed (PyYAML); the app adds a dashboard and a conf file; nothing is migrated or deleted.

## Test status
- Packaged RC3 browser acceptance (asa, ios, fortinet, pan, metrics, multi, engine): pass (Phase 10.1), and asa + multi + pan re-run in Phase 11: 22 tests pass (`docs/verification/evidence/phase11_demo*`).
- Install checks 20/20; package audit clean; Python regression 8 failed (the known baseline) / 4,658 passed / 2 skipped; browser regression (26) pass.
- **Not run:** the protected-lab Phase 4 specs; Splunk Cloud; non-Docker Splunk; engine as a VM service.

## Draft PR description
> **PulseForge 2.0.1: telemetry from one sourcetype, several sourcetypes or a scenario, with Splunk indexing confirmation and investigation**
>
> Select → Preview → Generate → Verify → Investigate for a single sourcetype, a multi-sourcetype run (events and metrics together) and the `paloalto_threat_investigation` scenario. Indexing is confirmed by an independent search by run id (events) or `mstats` (metrics), per sourcetype; HEC acceptance is reported separately and *Verified* is never shown without search evidence. The engine address is a customer setting (Connections); there is no default. Verified in a packaged install on Splunk Enterprise 10.2.7 with a Docker engine; Splunk Cloud not tested.
> Breaking: set the engine URL once after upgrading. See `docs/contracts/phase11/`.
