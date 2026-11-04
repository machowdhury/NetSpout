# Phase 12 — merge readiness

Branch `recovery/phase1-ta-compat` → **`origin/main`** (`3f2e63f`). Phase 12 starting point `817e116`. Candidate: **`rc5-654762b`** (version string 2.0.1). Deliverables: this file, `PHASE12_BINARY_POLICY.md`, `PHASE12_CHANGE_INVENTORY.md`, `PHASE12_PACKAGING_REPRODUCIBILITY.md`, `PHASE12_RELEASE_DECISION.md` (decision, support boundary, approvals, proposed PR).

## Summary
- **Merge shape:** `origin/main` is an ancestor of the branch. The PR is **21 commits / 728 files** and cannot conflict. (Phase 11 had compared against the stale local `main` and overstated it as 196 commits / 2,357 files; corrected in `PHASE12_CHANGE_INVENTORY.md`.)
- **Verdict:** safe to merge once you decide the binary policy (A1); **not** ready for a customer release (untested environments, 2.0.0 tracked binaries, open version policy).
- **Found and fixed this phase:** (1) the mirror guardrail covered 59 of 78 mirrored modules; (2) the engine build did not check the mirrors; (3) a UI defect on Connections (the first status response overwrote a typed or emptied Engine URL), found by the packaged `engine` test, which is why RC3 is superseded by RC5; (4) a stale test expectation (verified sourcetypes 4 → 6); (5) the RC installer can no longer install a package whose version differs from the source.
- **Not changed:** product behaviour apart from fix (3); no features, vendors, sourcetypes, scenarios or dashboards; no catalog file removed; RC1–RC3 and the released root files untouched (RC3 checksums re-verified OK).

## Evidence

| # | Check | Result | Evidence |
|---|---|---|---|
| 1 | Mirrored core: 266 files + all catalog copies byte-compared with `src/netspout_core` | **0 differences** | `PHASE12_PACKAGING_REPRODUCIBILITY.md` §1 |
| 2 | Guardrail tamper test (one mirror line appended) | caught (exit 1), restored | same |
| 3 | Clean-checkout rebuild of RC3 (no `samples/`, new venv with only `backend/requirements.txt`, `npm ci`) | Enterprise archive **byte-identical** to RC3; Cloud and engine identical by member | same §2 |
| 4 | RC5 built from a clean worktree; worktree shows no change besides rebuilt root artifacts (committed bundle = rebuilt bundle) | pass | `RC5_BUILD_MANIFEST.json`, `RC5_SHA256SUMS` |
| 5 | Package audit of RC5, 3 archives, git provenance | **0 findings** (reviewed false positives as in earlier audits) | `evidence/phase12/package_audit.json` |
| 6 | RC5 installed into the RC lab; install checks | **20/20 PASS** (versions match the source, files equal the archive, gateway reaches the configured engine) | `evidence/phase12/rc5_install_check.json` |
| 7 | **Packaged RC5 acceptance** (Splunk Web → gateway → Docker engine → HEC → search): asa 11, ios 1, fortinet 1, pan 3 (incl. the scenario and its Dashboard Studio dashboard), metrics 4, multi 8, engine 1 = **29 tests, all groups exit 0** | **PASS** | `evidence/phase12_rc/` (data), `phase12_rc_ui/` (screenshots) |
| 8 | Browser regression on the source stack (Phase 6 UI, scenario studio, explorer, shell) | **26 passed** | run of `scripts/phase10_browser_regression.py` |
| 9 | Python regression, the established selection (39 test files: generators, replay, capability, TA compatibility, scenarios, delivery monitor, dispatch, metrics, Phase 6/8/9/10/10.1/12) | **9 failed, 3,986 passed, 4 skipped** | below |
| 10 | Focused tests for the Phase 12 changes (`test_phase12_release_consistency`, `test_phase5_inventory`, `test_gate2_canonical`, `test_phase13_release_candidate`) | pass; the two root-binary checks skip normally and **fail in strict mode** on the tracked 2.0.0 files, by design | |
| 11 | Previous in-place 2.0.0 → 2.0.1 upgrade test (Phase 11) | pass | `evidence/phase11/` |

### Requested rechecks, all on the packaged RC5
| Recheck | Where it is covered |
|---|---|
| Single-sourcetype generation | `[asa]` 11, `[ios]`, `[fortinet]`, `[pan]` tests |
| Multiple-sourcetype generation (events + metric, streaming) | `[multi]` 8 tests |
| Scenario generation | `[pan]` scenario test (47 events, 3 sources, 5 phases, correlation ids and phase order) |
| Splunk indexing confirmation (accepted-but-not-indexed, wrong index, search unavailable, partial rejection) | `[asa]` failure tests, `[multi]` tests |
| Dashboard investigation | `[pan]` Studio dashboard test; `[multi]` run investigation dashboard |
| Engine not configured | `[engine]` test: "Engine not configured." (503), generation disabled |
| Engine unreachable | `[engine]` test: "Engine not connected." (502), nothing sent |
| Installed-package behaviour | install checks 20/20 + all of the above run through the installed app |

### Python baseline
- **Known baseline (8):** `test_gate6_integrity::test_07_successful_hec` and 7 sub-failures of `test_gate9_5_telemetry_semantics::test_01` (scenarios `ub1_*`, `ub2_*`, `ub3_*`). Unchanged.
- **One more failure, reported separately and not caused by Phase 11 or 12:** `tests/test_phase12_agentic_supply_chain.py::…::test_dashboard_recipe_families_integrate_without_regression` expects 30 dashboard recipes and finds 34. It is a stale count from a feature already on `origin/main`; the same failure occurs at `cb52875`, before this phase's changes. This file was not in the earlier selection (its name matches the new Phase 12 file pattern). Not changed here (approval A8).
- **Fixed here:** `test_phase5_inventory::test_matrix_reconciles_with_catalog_and_phase4_evidence` hard-coded 4 verified sourcetypes; Phase 10 made it 6 (the sets already agreed). Updated to 6.
- **Not run on purpose:** the whole `tests/` directory. Legacy Gate 12d/12f/13d tests need live SNMP/gNMI-to-Splunk environments (they failed or hung here without one); they are not part of any recorded regression and I stopped the run rather than let them probe unknown endpoints. The protected-lab Phase 4 browser specs were not run.

## What I could not or did not do
- Splunk Cloud, non-Docker Splunk, distributed Splunk, engine as a VM service, TLS to the engine, other browsers: NOT TESTED.
- No tracked release binary was changed, deleted or replaced; the binary policy is a recommendation awaiting approval.
- The protected demo (8081), the remote reference Splunk, RC1–RC3 and the released root artifacts were not touched. (Port 8081 still answers.)
- A real in-place upgrade (existing data and runs) is untested.
- The lab Splunk once failed to restart by itself after a heavy app reinstall during the Phase 11 upgrade test (amd64 emulation); a later reinstall of RC5 restarted normally.

## Residual risks for the reviewer
1. The dist bundle and four mirrored trees are generated: review `frontend/src` and `src/netspout_core`, not the copies.
2. 224 dashboards changed by one mechanical query regeneration (field ownership).
3. `EngineConnection` is a client-side race fix verified by the packaged test, not by a unit test (the repository has no React unit-test setup).
4. RC3, RC4 and RC5 all say 2.0.1: only the directory, commit and checksums tell them apart (A3).
