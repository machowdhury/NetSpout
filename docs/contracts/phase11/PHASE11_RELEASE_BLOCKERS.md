# Remaining release blockers (as of Phase 11)

Controlled demo: **READY** (RC3, packaged, isolated lab; engine URL set once). Broader release: **NOT READY** for the reasons below.

| # | Blocker | Owner / what is needed | Severity |
|---|---|---|---|
| 1 | **Tracked release binaries are stale.** Repo-root `netspout.spl` and `netspout_cloud.spl` are 2.0.0 builds; RC3 (2.0.1) lives only in `~/netspout/release-candidates/`. Merging would pair 2.0.0 binaries with 2.0.1 source | Decide: stop tracking binaries and publish RC3 or its rebuild as release assets, or replace the tracked files with the final build. Needs a version-policy decision | High |
| 2 | **Splunk Cloud NOT TESTED.** Needs app vetting and installation on a Cloud stack, a HEC token, and an engine reachable from that stack | Someone with Cloud access | High for Cloud customers |
| 3 | **Protected-lab Phase 4 specs NOT RUN** (`phase4e-live-lab`, `phase4f-*`, `phase4g`, `phase4h`; they use the protected lab's credentials and port 18000) | Someone with that lab, or a re-pointed isolated equivalent | Medium |
| 4 | **Engine as a service on a VM, non-Docker Splunk, distributed Splunk, TLS engine URL** not tested | Environment and time | Medium |
| 5 | **Real in-place upgrade** (existing data, saved destinations, runs) not tested; only a fresh 2.0.0 → 2.0.1 in the lab | A copy of a real 2.0.0 install | Medium |
| 6 | **PR scope**: 196 commits, 2,357 files; no human review of the whole line yet | Reviewer plan (by area, see the PR summary) | Medium |
| 7 | **Private corpora next to the app** (`netspout/datapet-test-es`, 1 GB) — now git-ignored but still inside the app folder | Move it out of `netspout/` | Low (the audit proves archives exclude it) |
| 8 | Scenario coverage claim: only `paloalto_threat_investigation` was run end to end with its Dashboard Studio dashboard; the other 371 definitions are not verified against vendor add-ons | Do not claim; per-scenario work if wanted | Low for a controlled demo |
| 9 | Build reproducibility: RC3+ archives are not byte-reproducible; identity is the manifest plus SHA256 | Policy | Low |
| 10 | Known Python baseline failures (8: `test_gate6_integrity::test_07` and 7 `test_gate9_5` subtests) | Triage | Low (unchanged since the clean baseline) |
| 11 | `scripts/validate_installed_app.py` still describes `NETSPOUT_BACKEND_URL` (legacy protected-lab validator) | Retire or update | Low |

Not blockers but to disclose: the demo's failure cases use a fault-injecting tap in front of a real HEC (lab scaffolding), and the scenario duration is an estimate.
