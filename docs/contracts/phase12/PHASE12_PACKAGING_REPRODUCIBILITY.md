# Packaging, mirrors and reproducibility

## 1. Mirrored `netspout_core` copies

**Authoritative source: `src/netspout_core/`** (72 files). `scripts/sync_core.py` copies it, from one list (`CORE_MODULES`, 78 modules, plus the 16-file `gnmi/` subpackage and the catalog JSONs), into:

| Target | Form | Used by |
|---|---|---|
| `netspout/bin/netspout_core/` | exact bytes | the Splunk app (package import path) |
| `netspout/bin/<module>.py` | auto-generated header + source | the Splunk app (flat imports) |
| `backend/app/<module>.py` | auto-generated header + source | the engine (FastAPI) |
| `netspout/bin/netspout_core/catalog_data`, `netspout/bin/catalog_data`, `backend/app/catalog_data`, `netspout/catalog` | catalog JSON copies of `catalog/` | app and engine |

The packages: `netspout.spl` carries the first two and the catalog copies; `pulseforge-engine.tar.gz` carries `backend/app` **and** `src/netspout_core` and `catalog/`.

**Audit (Phase 12):** 266 mirrored files (78 modules × 3 locations + 32 gNMI copies) and every catalog copy were compared byte for byte with the source: **0 differences**. No module exists in a mirror without a source, and none in `src` is missing from the list. So the installed Splunk app and the Docker engine run the same generator code.

**Gaps found and fixed (packaging only, no behaviour change):**
1. `scripts/verify_sources.py` (the guardrail the Enterprise build runs) kept its **own** copy of the module list and covered only **59 of 78** modules. The 19 it missed include `asa_generator.py`, `panos_generator.py`, `real_format_generators.py`, `scenario_contracts.py`, `universal_search.py` and `telemetry_config_api.py`; drift in any of them would have shipped unnoticed. It now imports `CORE_MODULES` from `sync_core.py`. Tamper test: appending a line to `backend/app/panos_generator.py` made the guardrail fail (exit 1) where it previously passed; restored afterwards.
2. `scripts/build_engine_package.py` told the operator to "run sync_core first" but did not check. It now runs the guardrail and refuses to build on drift.
3. New tests (`tests/test_phase12_release_consistency.py`): the guardrail uses the same list as the sync tool; mirrors equal the source; one release version in every source file; a stale root binary is detected.

**Differences that could make the app and the engine behave differently (remaining, by design):** the engine adds code that does not exist in the app (`backend/app/main.py`, destination manager, run progress) and the app adds the gateway and Splunk handlers (`netspout/bin/netspout_gateway.py`, `main.py`, executors). `netspout/bin/main.py` (863 lines, existed on main) is a different program from `backend/app/main.py` (3,793 lines) and is not a mirror. Behaviour that matters to a customer (generation, dispatch, verification) lives in the mirrored core and the engine, and the engine is the only component that generates or sends.

## 2. Clean-checkout reproduction of RC3

Method: `git worktree` of commit `0c83df0` (a clean tree: `git status` empty, **no `samples/` and no `netspout/datapet-test-es/`**), `npm ci` from the lockfile, a **new virtualenv holding only `backend/requirements.txt`** (Python 3.15.0, 29 packages including dependencies; no pytest, Playwright or other developer packages), then `build_frontend.py`, `build_splunk_package.py`, `build_splunk_cloud_package.py`, `build_engine_package.py`. All four succeeded.

| Artifact | Result vs RC3 (`rc3-ae3342d`) |
|---|---|
| `netspout.spl` | **byte-for-byte identical** (sha256 `c070b29e…8149`, 1,393 members) |
| `netspout_cloud.spl` | all 383 members identical; archive bytes differ (container metadata) |
| `pulseforge-engine.tar.gz` | 1,197 of 1,198 members identical; the one difference is `deploy/engine/pulseforge-engine`, whose comment was corrected in Phase 11 after RC3 |

So the Enterprise archive is reproducible from source; the other two are reproducible member by member. (Earlier notes saying "not byte-reproducible" were too broad for the Enterprise app.)

| Check | Result |
|---|---|
| Version 2.0.1 in app.conf, app.manifest, frontend package + lock, engine API, Cloud builder | one value (test `test_one_release_version_in_every_source`); the rebuilt app reports 2.0.1 |
| App and engine dependencies | the engine runs from `backend/requirements.txt` alone (Docker image of RC3/RC4, Python 3.13.18); the builders ran in a venv with only those packages; PyYAML is listed |
| Reliance on untracked samples | none: the build and the audit ran in a tree without them; the audit's provenance check proves every archived file is tracked in Git at the build commit |
| Developer-only Python packages | none needed to build or run; tests need `pytest`; browser tests need Node and Playwright (not packaged) |
| Build manifest and checksums | written for RC3 (Phase 10.1) and RC4 (this phase): `BUILD_MANIFEST.json` + `SHA256SUMS` in the candidate directory, copies in `docs/contracts/phase101/` and `phase12/` |
| Enterprise vs Cloud separation | `netspout.spl`: UI, gateway, REST handlers, `bin/`, catalogs, engine config (1,393 members). `netspout_cloud.spl`: dashboards and navigation only, **no `bin/`, no gateway, no REST handler, no engine setting** (383 members). **Both use the app id `netspout`**: installing one on top of the other replaces it. Never install both into one Splunk |
| Stale 2.0.0 binaries | the tracked root files are 2.0.0. They cannot be chosen by the RC tooling (`phase10_rc_install.py install` now refuses a package whose version differs from the source, shown with the root file) and the strict release test fails on them. `Dockerfile.standalone` still copies whatever `netspout.spl` is in the root (see `PHASE12_BINARY_POLICY.md`) |

## 3. RC3 and RC4

RC3 is untouched (checksums re-verified). The packaged regression found one defect in the shipped UI (the Connections page could replace a URL the admin had just typed with the previously saved one when the first status check was slow), fixed in `EngineConnection.tsx`. Because that changes the UI bundle, the fixed build is a **new candidate `rc4-036d59c`** built in a clean worktree: Enterprise `3aa06f4f…e4ab`, Cloud `cd6c8345…923d`, engine `d626c7bb…84a`. Its version string is still 2.0.1 (nothing has been released as 2.0.1); the identity is the directory, the commit and the checksums. Whether the final release takes 2.0.1 or a bump is a decision for you (`PHASE12_RELEASE_DECISION.md`, A3).

## 4. Recommended release procedure (for the final build)
1. Clean worktree of the release commit; `npm ci`; venv from `backend/requirements.txt`.
2. `python scripts/build_frontend.py`, then the three builders (the Enterprise builder syncs and verifies the mirrors itself; the engine builder now verifies).
3. `git status` in the worktree must show only the rebuilt root artifacts; `phase10_package_audit.py` must report 0 findings with `--repo <worktree>`.
4. Write `SHA256SUMS` and `BUILD_MANIFEST.json`; keep both beside the artifacts; run `NETSPOUT_STRICT_BINARIES=1 pytest tests/test_phase12_release_consistency.py` in the build tree.
5. Install into a fresh lab with `phase10_rc_install.py install`, run `check` (20 checks) and the packaged acceptance.
Shortcut remaining: steps 4's manifest and checksum files are written by hand; a small script would remove that (not added: no feature work).
