## Recovery: verified telemetry generation from one or several sourcetypes or a scenario, with Splunk indexing confirmation and investigation (2.0.1)

> **Review PR. This is NOT a customer-release approval.** It is not to be merged without explicit approval; no GitHub release, no deployment and no publication of artifacts are part of it. Customer release: **NO-GO** (see below).

**Size, exactly:** 30 commits on top of `origin/main` (`3f2e63f`, an ancestor of this branch, so no conflicts; GitHub: mergeable/clean), **901 files, +229,265 / −1,041 lines**. The line count is dominated by generated and evidence files, not logic:

| What | Files | Why it is large and how to review it |
|---|---|---|
| **Generated dashboards** (`netspout/default/data/ui/views`) | 225 (224 modified, 1 new) | One mechanical rewrite of the same few lines per dashboard: queries now read NetSpout's namespaced fields with a fallback (`eval pf_action=coalesce(netspout_action, action), pf_signature=coalesce(netspout_signature, signature)`, `pf_status=coalesce(netspout_status, status)`, then `rename … as action/signature/status`), so NetSpout values no longer shadow add-on fields. Checked for all 225: XML well formed, embedded JSON parses, query counts and the `$run_tok$`, `$index_tok$`, `netspout_run_id`, `netspout_scenario_id` tokens unchanged, no empty pipes. Do not read line by line; the one new view is `netspout_run_investigation.xml` |
| **Mirrored code** (generated copies of `src/netspout_core`) | 14 in `netspout/bin/netspout_core`, 12 in `netspout/bin`, 12 in `backend/app` (against 12 changed source files) | `scripts/sync_core.py` writes them; `scripts/verify_sources.py` now guards all 78 mirrored modules (it guarded 59); 266 mirrored files compared, 0 differences. **Review `src/netspout_core`, not the copies** |
| **Evidence** (`docs/verification/evidence/**`) | 445 (257 screenshots, the rest JSON) | outputs of the lab runs that back the claims; no code |
| Tests | 34 | 29 packaged browser acceptance tests live in `frontend/tests/phase9-acceptance.spec.ts` |
| Docs | 69 | phase reports, runbook, support matrix, upgrade guide, release-artifact guide |
| Built UI bundle | 3 | generated from `frontend/src` (13 files); a clean rebuild equals the committed bundle |

### What changes for users
Generate Data (one sourcetype or several, events and metrics together, bounded or continuous: Preview → Generate → Verify → Investigate), Scenarios (preview, run, Dashboard Studio investigation) and Connections. Every run is checked by an independent Splunk search by run id (`mstats` for metrics): *Verified* appears only with search evidence, HEC acceptance is reported separately, partly rejected or unconfirmed runs are labelled, a run that sent nothing is `FAILED`. Real telemetry formats for ASA, IOS, FortiGate and Palo Alto were verified against the vendor add-ons.
**Breaking:** the engine address is a customer setting (Connections > PulseForge Engine): no default, `NETSPOUT_BACKEND_URL` is no longer read, and the gateway reads the URL on every request. After upgrading, an admin enters it once; until then the app says "Engine not configured." Upgrade, rollback and what was tested: `docs/contracts/phase11/PHASE11_UPGRADE.md`.

### Binary policy (approved, Policy A)
`netspout.spl`, `netspout_cloud.spl` and their two manifests are no longer tracked (`git rm --cached`) and are git-ignored; they were stale 2.0.0 builds. They are archived outside the repo and remain in Git history. Get a versioned artifact or build from source: `docs/RELEASE_ARTIFACTS.md`. **After merging, `git pull` removes those four files from working trees.** A stale root package fails the strict release test and is refused by the RC installer; `Dockerfile.standalone` documents build-first.

### Evidence on the exact head (`85d72cf`; later commits are documentation only)
Built from a fresh clone (no sample folders, venv with only `backend/requirements.txt`): candidate **`rc7-85d72cf`** — `netspout.spl` `1b7e71e8…b044`, `netspout_cloud.spl` `6e3bbc4d…b5f7`, `pulseforge-engine.tar.gz` `944cfafe…bc8d`; audit 0 findings. Installed in the isolated lab: **install checks 20/20; packaged browser acceptance 29/29**; browser regression 26/26; Python selection (39 files) 9 failed / 3,990 passed, exactly the established nine (8 baseline + the stale `test_phase12_agentic_supply_chain` count), **no new failures**. Live gateway checks: no fallback (503 when unset); 210 requests right after URL changes (through the gateway and by direct edit) all reached the new engine; a read-only Splunk user gets 403 for run, stop and engine-URL changes; the engine URL is visible to signed-in users by design and documented. Report: `docs/contracts/phase14/FINAL_MERGE_GATE.md`.

### Tested support boundary
**Tested:** Splunk Enterprise 10.2.7 in an isolated Docker lab; the packaged app with a local Docker PulseForge Engine (Python 3.13.18); six verified event sourcetypes (`cisco:asa`, `cisco:ios`, `fortigate_traffic`, `pan:traffic`, `pan:threat`, `pan:system`; add-ons ASA 6.1.2, Cisco Enterprise Networking 4.0.6, FortiGate 1.6.10, Palo Alto 4.0.0); 14 IOS XR metric names via `mstats`; the Palo Alto scenario with Dashboard Studio; the failure cases; in-place 2.0.0 → 2.0.1 on a fresh install.
**NOT TESTED:** Splunk Cloud (separate validation track for `netspout_cloud.spl`), non-Docker Splunk Enterprise, distributed Splunk, the engine as a VM service or with TLS, the protected-lab Phase 4 suites, other browsers or Splunk versions, an upgrade of an install with real data.

### Known limitations
Run Investigation is one generic dashboard; only `paloalto_threat_investigation` was run end to end with its own dashboard (no claim for the other 371 scenarios); scenario duration is an estimate; continuous multi-source runs run until stopped; Enterprise and Cloud packages share the app id `netspout` and must never be installed on the same Splunk; the nine known test failures and the legacy root-level Phase 4 scripts (already on `main`) are handled separately.

### Reviewer guide
Start with `docs/contracts/phase12/PHASE12_CHANGE_INVENTORY.md` (by subsystem, with risks). Read `frontend/src`, `src/netspout_core`, `netspout/bin/netspout_gateway.py` and `backend/app/main.py`; skip generated mirrors, the bundle, the dashboards (see table) and evidence. Upgrade and runbook: `docs/contracts/phase11/`.
