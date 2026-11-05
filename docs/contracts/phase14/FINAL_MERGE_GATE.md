# Final merge gate for PR #7 — review report

**Tested commit: `85d72cf`** (`recovery/phase1-ta-compat`). The PR head is this commit plus documentation-only commits holding this report, its evidence and the PR text (no source, test, packaging or UI file differs; check with `git diff --stat 85d72cf..HEAD`). Candidate under test: **`rc7-85d72cf`**, built from a fresh clone of that exact commit. RC1, RC2, RC3, RC5 and the 2.0.0 archive were not touched (all checksums re-verified OK after the run); rc6-3a4ee76 failed its engine test and is marked superseded.

## What this gate found and fixed
Re-running the full packaged acceptance on a build of the PR head found a real, repeatable UI defect that earlier runs only passed by timing: the Connections page let the admin use the Engine URL form before the saved URL had loaded, so the late load could overwrite what was typed or leave Save acting on an empty or old value. Two partial fixes (rc4, rc6) failed their own packaged test; the root cause fix (rc7) keeps the field and Save disabled until the saved URL is known. The gateway also changed: it no longer caches the engine URL (an edit made directly in the configuration took 5.4 s to apply; the uncached read costs about 9 ms). Nothing else in the product changed.

## Package checksums (`~/netspout/release-candidates/rc7-85d72cf/`, with `SHA256SUMS` and `BUILD_MANIFEST.json`)
| Artifact | sha256 |
|---|---|
| `netspout.spl` (2.0.1, Enterprise) | `1b7e71e842ea416350ddeea7976a1f9880c0c0efd88770e0834f631a3e55b044` |
| `netspout_cloud.spl` (2.0.1, Cloud edition; not installed in this gate) | `6e3bbc4d593deed492c56b4d283d10ebab8d7c147024c32e9c92e643e9a5b5f7` |
| `pulseforge-engine.tar.gz` (2.0.1) | `944cfafea4f54bb2c3c90bc2ce966bc4131f1641f9b24700c816761a40e7bc8d` |

Versus RC5: the Cloud package and the engine package are identical member by member; the Enterprise app differs in exactly three files: `netspout/bin/netspout_gateway.py`, the UI bundle and `dist/index.html`.

## Results
| # | Check | Result | Evidence |
|---|---|---|---|
| 1 | Clean checkout of the exact head: no root packages, no sample folders, `npm ci`, venv with only `backend/requirements.txt` → frontend, Enterprise, Cloud, engine builds, `verify_sources` (78 modules) | all pass; `git status` empty afterwards (outputs git-ignored, committed bundle = rebuilt bundle) | `PHASE13_BINARY_MIGRATION.md` method, `rc7` manifest |
| 2 | Package audit, 3 archives, git provenance and lab-credential check | **0 findings** | `evidence/phase14/package_audit.json` |
| 3 | Packaged RC7 installed into the isolated lab (fresh engine container from the tarball) | version 2.0.1 | |
| 4 | **Installation checks** | **20/20 PASS** | `evidence/phase14/rc7_install_check.json` |
| 5 | **Packaged browser acceptance**: asa 11, ios 1, fortinet 1, pan 3, metrics 4, multi 8, engine 1 | **29/29 pass**, all groups exit 0 | `evidence/phase14_rc/`, `phase14_rc_ui/` |
| | covers single source (ASA, IOS, FortiGate, PAN), four sourcetypes in one run, event + IOS XR metric mix, streaming (several sourcetypes; metrics stream; outage and sustained failure), the Palo Alto scenario with its Dashboard Studio dashboard and the run investigation dashboard, per-sourcetype indexing verification, and the failure cases (invalid destination, HEC rejection, accepted-not-indexed, wrong event index, wrong metric index, unsupported sourcetype, preview failure, search unavailable, partial rejection, engine not configured, engine unreachable) | | |
| 6 | Browser regression on the source stack (26 specs) | **26 pass** | |
| 7 | Focused packaging tests in the clean clone, strict mode (`NETSPOUT_STRICT_BINARIES=1`) | **53 passed** | |
| 8 | Python regression (the established 39-file selection) | **9 failed, 3,990 passed, 4 skipped**: exactly the established nine (below). **No new failure** | |

### Python: the established nine
`test_gate6_integrity::test_07_successful_hec`; seven sub-failures of `test_gate9_5_telemetry_semantics::test_01` (scenarios `ub1_*`, `ub2_*`, `ub3_*`); and `test_phase12_agentic_supply_chain::…::test_dashboard_recipe_families_integrate_without_regression` (expects 30 recipes, finds 34; fails identically before this PR). New failures: **none**. New tests that pass: gateway URL change applies to the very next request; run authorization enforced by the gateway.

## Gateway behaviour (live, packaged RC7; `evidence/phase14/gateway_live_checks.json`)
| Requirement | Result |
|---|---|
| No implicit engine fallback | No default, no environment variable, no `host.docker.internal` in the gateway source (the only `8081` is the example in an error message). With an empty setting, `GET` and `POST /api/runs` → **503 "Engine not configured."**; nothing is sent anywhere |
| URL changes take effect correctly | Engine A and a distinguishable fake engine B were alternated: **150 requests right after 30 saves through the gateway and 60 requests right after 20 direct edits of the configuration: 0 went to the old engine or failed** |
| No stale routing after a save | the 5-second cache is removed; the URL is read on every request (about 9 ms); a unit test proves two consecutive reads see the new value |
| Run authorization is server-side | a real read-only Splunk user (`user` role, created and deleted in the lab): `POST /api/runs` **403**, `POST /api/runs/x/stop` **403**, `POST /engine` **403**, `GET /api/runs` 200; the engine URL was unchanged afterwards. An admin's `POST /api/runs` reaches the engine (its own validation answers 422). Unit tests confirm nothing reaches the engine for a read-only role, and other HTTP methods are not routed (404) |
| Engine URL visibility intentional and documented | `GET /engine` returns the URL and version to any signed-in user (200 for the read-only user); this is intended (the page needs it to say "not configured / not connected"). Documented in `docs/guides/03_INSTALLATION.md` step 5: treat the URL as non-secret, no credentials in it (the app refuses credentials, paths and queries), only admin/power/sc_admin can change it or start runs |

## origin/main and the PR
`origin/main` is `3f2e63f`, still an ancestor of the branch, 0 upstream commits missing. GitHub reports PR #7 **MERGEABLE / CLEAN** (draft until this report is posted).

## Remaining limitations
Splunk Cloud, non-Docker and distributed Splunk, the engine as a VM service or with TLS, other browsers and Splunk versions, the protected-lab Phase 4 suites and an upgrade of a real install with data are **NOT TESTED**. Only six sourcetypes (`cisco:asa`, `cisco:ios`, `fortigate_traffic`, `pan:traffic`, `pan:threat`, `pan:system`) and 14 IOS XR metric names are verified against vendor add-ons; only `paloalto_threat_investigation` was run end to end with its Dashboard Studio dashboard. Run Investigation is one generic dashboard. Continuous multi-source runs run until stopped. The Enterprise and Cloud packages share the app id `netspout` and must not be installed on the same Splunk. After the PR merges, `git pull` removes the four formerly tracked package files from working trees (archived and in history). No release artifacts have been published. The failing nine tests and the legacy root-level scripts are handled separately. The gateway has no automated test against a real second engine in CI; that check lives in the lab script used here.

## Decisions
- **GO to merge PR #7** (no conflicts; mergeable; packaged acceptance 29/29, install 20/20, no new test failures; policy A applied; the defects found were fixed and re-verified on the exact head). Merge only with your approval; I have not merged.
- **NO-GO for a customer release.** Unvalidated: Splunk Cloud (its own track), non-Docker/distributed Splunk, VM-service engine with TLS, protected-lab suites, upgrade of a real install; no versioned release artifacts are published (use `rc7-85d72cf` as the controlled-demo candidate, not RC5 or RC3).
