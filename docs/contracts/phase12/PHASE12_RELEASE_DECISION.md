# Release decision, support boundary and approvals

## Decision

| Question | Answer |
|---|---|
| Is the branch safe to merge into `origin/main`? | **Yes, with conditions.** The merge is a fast-forward of 21 commits (728 files) onto `origin/main` `3f2e63f`; no conflicts are possible; the packaged product passes its acceptance; the mirrored code is verified identical. The conditions are the approvals below, chiefly the binary policy (A1) |
| Is it safe to *release* 2.0.1 to customers? | **No.** Splunk Cloud, non-Docker and distributed Splunk, the VM-service engine and the protected-lab Phase 4 suites are untested, the tracked binaries are 2.0.0, and the version policy is open |
| Controlled demo | **Ready** with `rc5-654762b` (not RC3; see the packaged result) |

## Candidate to use
**`rc5-654762b`** (`~/netspout/release-candidates/rc5-654762b/`, with `SHA256SUMS` and `BUILD_MANIFEST.json`; copies in this folder): Enterprise `0d46ca40…08f6`, Cloud `a233248f…3cfa`, engine `7c46313e…4512`. RC3 (`rc3-ae3342d`) is untouched and correct except for one UI defect found this phase: on Connections, the first engine-status response could replace a URL the admin had just typed or cleared, so Save stored the old value. RC4 (`rc4-036d59c`) fixed half of that, failed its own packaged test, and is marked superseded. All three carry the string 2.0.1.

## Enterprise support boundary (do not broaden)

| Statement | Status | Evidence |
|---|---|---|
| Splunk Enterprise **10.2.7** in the isolated Docker lab (image `splunk/splunk:10.2`, amd64 on an arm64 macOS host, Docker 29.7.2) | **Tested** | install checks 20/20; packaged acceptance |
| Packaged app (`netspout.spl`, installed through Splunk's app endpoint) with the PulseForge Engine in a local Docker container built from `pulseforge-engine.tar.gz` (Python 3.13.18) | **Tested** | `phase12_rc`, `phase11_demo`, Phase 10.1 |
| Six verified event sourcetypes: `cisco:asa`, `cisco:ios`, `fortigate_traffic`, `pan:traffic`, `pan:threat`, `pan:system`, with the add-ons ASA 6.1.2, Cisco Enterprise Networking 4.0.6, FortiGate 1.6.10, Palo Alto 4.0.0 | **Tested** | `docs/contracts/ta_live_results.json`, `journey_*.json`, PAN scenario |
| 14 IOS XR metric names confirmed by `mstats` in `cisco_mdt_metrics` (`interface_generic_counters.*` ×11, `…wdsysmon-fd-oper:system-monitoring/cpu-utilization.total_cpu_{one,five,fifteen}_minute`) | **Tested** | `journey_metrics.json` |
| Single sourcetype, several sourcetypes (events + metrics), the Palo Alto scenario with its Dashboard Studio investigation; engine not configured / not connected; accepted-but-not-indexed; search unavailable; partly rejected batch | **Tested** (packaged) | see merge readiness |
| In-place 2.0.0 → 2.0.1 upgrade on a fresh 2.0.0 install | **Tested** (lab) | `evidence/phase11/upgrade_2.0.0_to_2.0.1.txt` |
| Splunk Cloud | **NOT TESTED** | |
| Non-Docker Splunk Enterprise (VM or bare metal) | **NOT TESTED** | |
| Distributed Splunk (search head or indexer cluster, forwarder tier in front of HEC) | **NOT TESTED** | |
| Engine deployed as a VM service (systemd/launchd), TLS between Splunk and the engine | **NOT TESTED** | |
| Protected-lab Phase 4 suites (`phase4e-live-lab`, `phase4f-*`, `phase4g`, `phase4h`) | **NOT TESTED** | read the protected lab's credentials |
| Any sourcetype other than the six, any scenario other than `paloalto_threat_investigation` end to end, all 372 scenarios | **Not verified** (generated, labelled by the UI) | |
| Browsers other than Chromium; Splunk other than 10.2.x | **NOT TESTED** | |

## Actions that need your approval (nothing below was done)

| # | Action | Why | Reversible? |
|---|---|---|---|
| **A1** | **Binary policy.** Approve Policy A (stop tracking `netspout.spl`, `netspout_cloud.spl` and their manifests; publish versioned release artifacts) — or choose Policy B (replace the tracked files with the final 2.0.1 build). Before either: archive the three root files outside the repo | They are 2.0.0 and tracked on `origin/main`; the PR raises the source to 2.0.1 | yes (Git history, archived copies); see `PHASE12_BINARY_POLICY.md` §4–5 |
| **A2** | Pick the candidate to publish: `rc5-654762b` (recommended) or rebuild from the merge commit (byte-identical `netspout.spl` expected if no packaged source changes) | RC3 has the UI defect | yes |
| **A3** | **Version policy.** Keep 2.0.1 for the final release (nothing has shipped as 2.0.1) or bump to 2.0.2 so RC3 can never be confused with the final build | RC3 and RC5 share a version string | bumping touches ~7 files and one rebuild |
| **A4** | Update local `main` (`b9521c1`) to `origin/main` (`3f2e63f`) | the local branch is stale and misled the Phase 11 review | yes |
| **A5** | Open the PR (title and text below) and choose merge style (fast-forward or merge commit; I suggest a merge commit so the 21 phase commits stay grouped) | not opened | n/a |
| **A6** | Optional cleanup PR for the 20 root-level Phase 4 harnesses and `design/*.zip` (already on `origin/main`) | they send to a HEC when lab variables are set | yes |
| **A7** | Decide who runs Splunk Cloud, non-Docker, distributed, VM-service and protected-lab tests, and when; none of them is possible from this environment without access | blockers for a customer release | n/a |
| **A8** | Whether to commit the Phase 4 tests' stale-count fixes beyond the ones made here (see merge readiness) and the pre-existing failing test `test_phase12_agentic_supply_chain` | baseline hygiene | yes |

## Proposed PR

**Title:** `Recovery: verified telemetry generation from one or several sourcetypes or a scenario, with Splunk indexing confirmation and investigation (2.0.1)`

**Description:**
> Brings the recovery line (phases 1–12) onto `main`: 21 commits, 728 files.
>
> **What changes for users.** Generate Data (one sourcetype or several, events and metrics together), Scenarios (preview, run, Dashboard Studio investigation) and Connections. Every run is checked by an independent Splunk search by run id (`mstats` for metrics); *Verified* is shown only with search evidence, HEC acceptance is reported separately, and partly rejected or unconfirmed runs are labelled as such. Real telemetry formats for ASA, IOS, FortiGate and Palo Alto were verified against the vendor add-ons; NetSpout fields no longer shadow add-on fields.
> **Breaking.** The engine address is now a customer setting (Connections > PulseForge Engine); there is no default and `NETSPOUT_BACKEND_URL` is no longer read. After upgrading, an admin enters the URL once. See `docs/contracts/phase11/PHASE11_UPGRADE.md`.
> **Packaging.** The mirror guardrail now covers all 78 mirrored core modules (it covered 59); the engine build refuses drifted mirrors; version 2.0.1 everywhere. The tracked 2.0.0 binaries at the repo root are not touched by this PR; see `docs/contracts/phase12/PHASE12_BINARY_POLICY.md` before release.
> **Tested.** Packaged app on Splunk Enterprise 10.2.7 with a Docker engine: single, multi, mixed event+metric, streaming, the Palo Alto scenario, and the failure cases. **Not tested:** Splunk Cloud, non-Docker/distributed Splunk, engine as a VM service, the protected-lab Phase 4 specs.
> Reviewer guide: `docs/contracts/phase12/PHASE12_CHANGE_INVENTORY.md`.
