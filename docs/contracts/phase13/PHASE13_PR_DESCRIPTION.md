## Recovery: verified telemetry generation from one or several sourcetypes or a scenario, with Splunk indexing confirmation and investigation (2.0.1)

> **This is a review PR. It is NOT a customer-release approval.** Do not merge until the reviewers have signed off; no GitHub release, no deployment and no publication of artifacts is part of it.

Brings recovery phases 1–13 onto `main`: about 25 commits on top of `origin/main` (`3f2e63f`, an ancestor of this branch, so no conflicts); about 730 files, mostly evidence, tests and dashboards.

### What changes for users
- **Generate Data**: one sourcetype, or several at once (events and metrics together, bounded or continuous), with Preview → Generate → Verify → Investigate. **Scenarios**: preview, run, Dashboard Studio investigation. **Connections**.
- **Verification is honest.** Every run is checked by an independent Splunk search by run id (`mstats` for metrics). *Verified* appears only with search evidence; HEC acceptance is reported separately; partly rejected or unconfirmed runs are labelled (`PARTIAL`, *Not confirmed*); a run that sent nothing is `FAILED`.
- Real telemetry formats for ASA, IOS, FortiGate and Palo Alto were verified against the vendor add-ons; NetSpout fields no longer shadow add-on fields (224 dashboards now read the namespaced fields with a fallback).
- **Breaking:** the engine address is a customer setting (Connections > PulseForge Engine). There is no default and `NETSPOUT_BACKEND_URL` is no longer read. After upgrading, an admin enters the URL once; until then the app says "Engine not configured." Upgrade steps, rollback and what was tested: `docs/contracts/phase11/PHASE11_UPGRADE.md`.

### Binary policy (approved): generated packages are no longer in Git
`netspout.spl`, `netspout_cloud.spl` and their two manifest files are removed from the index (`git rm --cached`) and git-ignored; `pulseforge-engine.tar.gz` already was. They were 2.0.0 builds, stale against the 2.0.1 source. Obtain a versioned release artifact (with `SHA256SUMS` and `BUILD_MANIFEST.json`) or build from source: `docs/RELEASE_ARTIFACTS.md`. The old files are archived outside the repo and stay in Git history. **After merging, a `git pull` removes those four files from working trees.** `Dockerfile.standalone` documents build-first; tests skip when no package is built; a stale root package fails the strict release test and is refused by the RC installer. Details: `docs/contracts/phase12/PHASE12_BINARY_POLICY.md`, `docs/contracts/phase13/PHASE13_BINARY_MIGRATION.md`.

### Packaging
Mirrored core: all 78 mirrored modules are now guarded (it was 59); 266 mirrored files compared, 0 differences; the engine build refuses to build from drifted mirrors; version 2.0.1 everywhere. A fresh clone with no sample folders and a venv of only `backend/requirements.txt` builds all three packages with the committed UI bundle unchanged; the Enterprise archive is byte-identical to the candidate **RC5** (`rc5-654762b`), Cloud and engine are identical member by member; package audit: 0 findings.

### Tested support boundary (do not read more into it)
| | |
|---|---|
| **Tested** | Splunk Enterprise **10.2.7** in an isolated Docker lab; the packaged app with a local Docker PulseForge Engine (Python 3.13.18); six verified event sourcetypes (`cisco:asa`, `cisco:ios`, `fortigate_traffic`, `pan:traffic`, `pan:threat`, `pan:system`; add-ons ASA 6.1.2, Cisco Enterprise Networking 4.0.6, FortiGate 1.6.10, Palo Alto 4.0.0); 14 IOS XR metric names by `mstats`; single, multi (event + metric, streaming) and the Palo Alto scenario with Dashboard Studio; failure cases (engine not configured / not connected, accepted-not-indexed, wrong index, search unavailable, partial rejection, unsupported sourcetype, invalid destination); in-place 2.0.0 → 2.0.1 on a fresh install |
| **NOT TESTED** | Splunk Cloud (separate validation track for `netspout_cloud.spl`); non-Docker Splunk Enterprise; distributed Splunk; the engine as a VM service or with TLS; the protected-lab Phase 4 suites; other browsers or Splunk versions; an upgrade of an install with real data |

### Evidence
Packaged acceptance on RC5 (Splunk Web → gateway → Docker engine → HEC → search): asa 11, ios 1, fortinet 1, pan 3, metrics 4, multi 8, engine 1 — 29 tests, all pass; install checks 20/20; browser regression 26 pass; Python selection (39 files): the 8 known baseline failures plus one pre-existing stale-count failure (`test_phase12_agentic_supply_chain`, 30 vs 34 recipes, fails the same way before this PR; baseline hygiene is handled separately). Reports: `docs/contracts/phase12/PHASE12_MERGE_READINESS.md`; evidence under `docs/verification/evidence/phase12*` and `phase13`.

### Known limitations
Run Investigation is one generic dashboard; only `paloalto_threat_investigation` was exercised end to end with its own dashboard (no claim for the other 371 scenarios); scenario duration is an estimate; continuous multi-source runs run until stopped; `GET /engine` shows the engine URL and version to any authenticated user (writes need an admin/power role); Enterprise and Cloud packages share the app id `netspout` and must never be installed on the same Splunk; legacy root-level Phase 4 scripts and `design/*.zip` (already on `main`) are deferred to a separate cleanup.

### Reviewer guide
Start with `docs/contracts/phase12/PHASE12_CHANGE_INVENTORY.md` (grouped by subsystem with file counts and risks). Review `frontend/src`, `src/netspout_core`, `netspout/bin/netspout_gateway.py`, `backend/app/main.py`; do not read the generated mirrors, the built bundle or the 224 mechanical dashboard edits line by line (inventory §Dashboards explains and verifies them). Support matrix, runbook, upgrade guide: `docs/contracts/phase11/`.
