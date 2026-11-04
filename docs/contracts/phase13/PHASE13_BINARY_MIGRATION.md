# Phase 13 — Policy A migration and review PR

Decisions applied: A1 Policy A approved; A2 RC5 is the controlled-demo candidate; A3 product version stays 2.0.1; A4 local `main` updated; A5 review PR (not merged); A6 legacy cleanup deferred; A7 Enterprise and Cloud have separate release-validation tracks; A8 baseline-test hygiene handled separately.

## 1. Archive of the previous release artifacts
Location (outside the repository, nothing in RC1–RC5 modified): `~/netspout/released-artifacts-2.0.0-pre-policy-a/`. Copies made with `cp -p` from the repo root at `3cb4322`; every copy was re-hashed and **equals the original**. RC1, RC2, RC3 and RC5 checksum files re-verified OK before and after.

| File | sha256 |
|---|---|
| `netspout.spl` (2.0.0) | `3b086b80e2e5a4f9b4864b649991e2685f76d991ae55f00ed10ba75e6563c46f` |
| `netspout_cloud.spl` (2.0.0) | `3f8a7cf771c9bd903fe29e0165d647d05b32301a2b106b71d4a807f0d001a3a7` |
| `pulseforge-engine.tar.gz` (2.0.0, never tracked) | `9b54120b1093d6248a3db38b7af5f312d5ee4ef27f89b88496d99c300b45bf1b` |
| `netspout.spl.manifest.json` | `9a6d29047545ec471110…` (full value in `SHA256SUMS.original-copy` in the archive folder) |
| `netspout_cloud.spl.manifest.json` | `64cfad425b8b5446bc9b…` (same) |

They also remain in Git history (`git show 3cb4322:netspout.spl`, `…:netspout_cloud.spl`, `…:netspout.spl.manifest.json`, `…:netspout_cloud.spl.manifest.json`).

## 2. What was changed (commit `df5dd81`)
- **Untracked with `git rm --cached` (files kept on disk, nothing deleted):** `netspout.spl`, `netspout_cloud.spl`, `netspout.spl.manifest.json`, `netspout_cloud.spl.manifest.json`. (`pulseforge-engine.tar.gz` was already untracked.)
- `.gitignore`: root-anchored `/netspout.spl`, `/netspout_cloud.spl`, both manifests, `/pulseforge-engine.tar.gz`, `/SHA256SUMS`, `/BUILD_MANIFEST.json` (the tracked copies under `docs/contracts/phase*/` are not ignored). The builders still write to those paths; nothing in them changed.
- New `docs/RELEASE_ARTIFACTS.md` (how to obtain a versioned artifact, verify it, or build from source; Enterprise vs Cloud; never install both); `README.md`, `docs/INSTALL.md`, `docs/guides/03_INSTALLATION.md` and `04_SPLUNK_CLOUD_GUIDE.md` now point to it.
- `Dockerfile.standalone`: a "BUILD FIRST" header (`python scripts/build_splunk_package.py`, then the compose build, and a version check before reuse). `docker-compose.standalone.yml` unchanged.
- Tests: `run_comprehensive_test_suite.py` Suite 19 skips (with a message) when no package is built; `test_phase5_inventory` now asserts that **no** `.spl/.tgz/.tar.gz` is tracked; `test_phase12_release_consistency` adds "packages not tracked and all git-ignored" and "builders still write the root paths". `test_gate2_canonical::test_08` and `test_phase13_release_candidate` already skip without a package.
- Guards against a stale 2.0.0 package: strict test (`NETSPOUT_STRICT_BINARIES=1`) fails on any root package of another version; `phase10_rc_install.py install` refuses it (shown against the archived 2.0.0 copy: "refusing to install … it is version 2.0.0, the source is 2.0.1").
- The 2.0.0 files still sit untracked and ignored in the maintainer's working copy (kept, per "no destructive deletion"). In a *clean checkout* there are none, so a stale package cannot be present at all.

## 3. Clean-checkout validation (evidence: `docs/verification/evidence/phase13/clean_checkout_build.json`)
Fresh `git clone` at `df5dd81`: no root packages, no `samples/`, no `netspout/datapet-test-es/`; `npm ci`; a virtualenv holding only `backend/requirements.txt` (Python 3.15.0).

| Step | Result |
|---|---|
| `build_frontend.py` | pass |
| `build_splunk_package.py` (core sync + `verify_sources`, now over all 78 modules) | pass |
| `build_splunk_cloud_package.py` | pass |
| `build_engine_package.py` (refuses on mirror drift) | pass |
| `verify_sources.py` | pass |
| `git status` after the build | **empty** (all outputs ignored; the committed UI bundle equals the rebuilt one) |
| Package audit, 3 archives, git provenance (`--repo` = the clone) and lab-credential check | **0 findings** |
| Versions | 2.0.1 everywhere (consistency test, strict mode) |
| Focused tests in the clean clone (`test_phase12_release_consistency`, `test_phase5_inventory`, `test_gate2_canonical`, `test_phase13_release_candidate`, strict mode) | **39 passed** |
| Compared with **RC5** (`rc5-654762b`) | `netspout.spl` **byte-identical** (`0d46ca40…08f6`, 1,393 members); Cloud 383/383 and engine 1,198/1,198 members identical (archive container bytes differ) |

Because the rebuilt packages are identical to RC5, packaged behaviour did **not** change, so the full packaged acceptance was **not** re-run for this phase; its RC5 result stands (29 tests, all seven groups, install checks 20/20 — `docs/contracts/phase12/PHASE12_MERGE_READINESS.md`).

**Regression after the migration:** Python selection (39 files) **9 failed, 3,988 passed, 4 skipped** — the same nine as Phase 12 (the 8 known baseline failures: `test_gate6_integrity::test_07` and 7 sub-failures of `test_gate9_5_telemetry_semantics::test_01`; plus the pre-existing `test_phase12_agentic_supply_chain` stale count, 30 vs 34 recipes). No new failure; two new tests pass. The browser regression was not re-run: no frontend or packaged file changed since Phase 12 (26 passed there).

Checksums and manifest of the candidate: RC5 (`docs/contracts/phase12/RC5_SHA256SUMS`, `RC5_BUILD_MANIFEST.json`). The clean rebuild's own hashes are in the evidence file.

## 4. Review against the latest `origin/main`
- `git fetch`: `origin/main` is still `3f2e63f`; **it is an ancestor** of the branch; 0 upstream commits are missing; the branch is about 25 commits ahead (the recovery phases 1–13). No conflict is possible.
- **224 dashboard changes, as one mechanical group:** all 224 modified views (plus one new view) were parsed. XML is well formed in every file; every embedded Dashboard Studio JSON parses; the number of queries per file is unchanged; the counts of `$run_tok$`, `$index_tok$`, `netspout_run_id` and `netspout_scenario_id` in each changed query are unchanged; there are no empty or doubled pipes. The only change is the Phase 4 field-ownership rewrite: `eval pf_action=coalesce(netspout_action, action), pf_signature=coalesce(netspout_signature, signature)` (224 files) and `pf_status=coalesce(netspout_status, status)` (223 files) before the `stats`, then `rename … as action/signature/status`. That prefers NetSpout's namespaced fields and falls back to the bare fields, so older data still works. Residual risk: the queries were not each executed in Splunk; the Palo Alto Studio dashboard and the run-investigation dashboard were, with real data.
- **Gateway configuration:** the URL lives only in `netspout_engine.conf`; changes need a write role (fail closed); no default and no environment fallback; the gateway uses `https://127.0.0.1:8089` on the Splunk host only. **New observations, low risk:** (1) `GET /engine` is allowed for any authenticated user and returns the engine URL and version (read-only, internal address); (2) everything that is not a GET (including starting runs) needs an admin/power role, so a read-only Splunk user cannot generate; this is intended but worth stating in the user docs; (3) the URL is cached for 5 s, so an edit made outside Connections is seen after up to 5 s.
- **Multi-sourcetype generation:** 1–20 unique sourcetypes, counts 1–1000, unsupported sourcetypes refuse the whole request and are named, per-source accepted/rejected/found, mixed event and metric routing; covered by 12 unit tests and 8 packaged tests. Risk: continuous multi-source runs have no server-side maximum duration beyond Stop and the existing failure limits (same as the single-sourcetype stream).
- **Scenario verification:** per-sourcetype and per-phase verification by run id; `PARTIAL` status; a run that sent nothing is `FAILED`; only `paloalto_threat_investigation` was run end to end.
- **Packaged engine dependencies:** `backend/requirements.txt` (pinned; PyYAML added after the RC2 defect) is the only dependency file; the Docker engine ran from it alone on Python 3.13.18, and the builders ran from it alone on Python 3.15.0. No new unpinned dependency.
- **New risks found:** none beyond the three low-risk gateway notes above.

## 5. Local `main`
Checked first: no uncommitted work on `main`, 0 local-only commits, `main` an ancestor of `origin/main`, not checked out in any worktree. Updated with `git fetch origin main:main` (fast-forward only, refuses otherwise): `b9521c1` → `3f2e63f`. No reset, no force, nothing discarded. The working branch was not switched.

## 6. Review PR
See the PR (title and text in `PHASE13_PR_DESCRIPTION.md`): targets `main`, **not merged**, **not a customer-release approval**, no GitHub release created, nothing deployed.

## 7. Remaining blockers for a customer release
1. Splunk Cloud (`netspout_cloud.spl`): separate validation track, NOT TESTED.
2. Enterprise on non-Docker, distributed Splunk, engine as a VM service with TLS, other browsers and Splunk versions: NOT TESTED.
3. Protected-lab Phase 4 suites: NOT TESTED (need that lab's credentials).
4. Publishing: no versioned release artifacts exist yet (RC5 files live under `~/netspout/release-candidates/`); a release needs the artifact upload with `SHA256SUMS` and `BUILD_MANIFEST.json` (not done: no GitHub release without approval).
5. Real in-place upgrade of an install with data and runs: untested.
6. Pre-existing baseline test failures (8 known + `test_phase12_agentic_supply_chain` stale count), deferred per A8.
7. Legacy root-level scripts and `design/*.zip` (A6, deferred).
8. After merge, anyone who pulls will have the four tracked package files removed from their working tree; the archive and Git history keep them.
