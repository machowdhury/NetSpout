# Phase 10 — Release-candidate readiness report

Candidate: `rc2-3f6cc0f` (built from commit 3f6cc0f in a clean worktree; artifacts live outside the repository in `~/netspout/release-candidates/rc2-3f6cc0f/`, with `SHA256SUMS` and `BUILD_MANIFEST.json`, copies in this folder).
Version identity is **2.0.0 for the app, the engine and the frontend, and the same 2.0.0 string as the previously released artifacts**: the RC cannot be told apart from the release by version number (see limitations).

| artifact | sha256 |
|---|---|
| netspout.spl | 86724bdf…178838 |
| netspout_cloud.spl | b3184d28…588f51 |
| pulseforge-engine.tar.gz | cbb18776…45b3c |

The released `.spl` files and engine archive in the repository root were re-checksummed after the build: unchanged.

## Gates

| # | Gate | Result | Evidence |
|---|---|---|---|
| 1 | Baseline (Python): 8 known failures, no new ones | PASS | 8 failed / 4634 passed / 2 skipped; the 8 are `test_gate6_integrity::test_07` and 7 subtests of `test_gate9_5_telemetry_semantics::test_01` (same set as before Phase 10) |
| 2 | Palo Alto scenario `paloalto_threat_investigation` verified (pan:threat, pan:system, 47 events, correlation ids, phase order, 14 searches) | PASS | `evidence/phase9/scenario_*.json`, `phase10/pan_*_after_fix.json`; also PASS in the packaged install (`phase10_rc/`) |
| 3 | Continuous `cisco_metrics` streaming through the browser (payloads, names, values, dimensions, mstats over time, prompt stop, outage, sustained failure) | PASS (source and packaged) | `streaming_*.json`, screenshots `p10_01..05`. Only the metric names the generator emits and the mstats run confirmed are claimed |
| 4 | Outstanding browser suites: Phase 6 UI, Phase 9 acceptance, phase6-scenario-studio, unified shell, phase4e explorer | PASS | 26 tests via `scripts/phase10_browser_regression.py`; Phase 9: 20 tests, all five groups, source stack and packaged install |
| 4b | Phase 4 specs bound to the protected lab (`phase4e-live-lab`, `phase4f-*`, `phase4g-pack-scenario`, `phase4h-incident-pack`) | **NOT TESTED** | They read the protected lab's credentials and target port 18000; forbidden to run |
| 5 | Packaged install in an isolated environment: UI loads, versions match, capability status, four integrations, indexes, preview/generate/verify, scenario + Studio link, no dev services | PASS | 19/19 install checks (`phase10/rc_install_check.json`); Phase 9 acceptance through Splunk Web + gateway + engine container built from the RC tarball, all five groups |
| 6 | Package audit (secrets, lab credentials, private samples, vendor add-ons, dev paths, provenance vs git) | PASS | `phase10/package_audit.json`: three archives clean; reviewed false positives listed with reasons in `package_audit_allowlist.json` |
| 7 | Security and configuration review | PASS with findings below | |

## Defects the RC testing found and fixed (all in the first RC attempts)

1. **Engine package missing PyYAML** — `backend/requirements.txt` lacked it, so `POST /api/generate/preview` returned 500 in every packaged engine (the source tree hid it). Fixed (`PyYAML==6.0.3`, already named in THIRD_PARTY_NOTICES). **Release blocker for RC1; closed in RC2.**
2. **Streaming that is never accepted now fails fast** (10 rejections) instead of running on; browser-tested.
3. IOS XR counters are cumulative across chunks; PAN threat/system use the add-on's own formats; THREAT action is `block-ip`.
4. RC installer: `NETSPOUT_BACKEND_URL` must be set in `splunk-launch.conf` (see risk 1).

## Security and configuration review

- Secrets: HEC token and search credential are held server-side in memory, never returned by `/api/setup` (only `*_configured` flags), never written to evidence, logs, or the archives (audit searched for the lab's actual values: none).
- Default destination: a fresh engine is unconfigured (`configured:false`); nothing is sent until the user saves a destination.
- Transport: plain HTTP is accepted only for loopback in lab mode, and TLS verification can be disabled only for loopback (both enforced server-side; both exercised in the packaged lab, which is why the lab tap and Splunk forwarder run on the engine's loopback).
- Gateway: authenticated Splunk session required; POST needs an admin/power/sc_admin role (fail closed); `..` and non-`/api/`+`/health` paths refused; 8 MB body cap; Splunk CSRF key sent by the UI.
- HEC auth and errors: `Authorization: Splunk <token>`; rejected tokens/indexes surface as plain failures and the run is never marked Verified (tested: rejection, accepted-not-indexed, wrong event index, wrong metric index, search unavailable).
- Index routing: event and metric indexes are the ones the app defines (`idx_network_ops`, `cisco_mdt_metrics`) in the packaged lab; a wrong index is detected by the independent search.
- Third-party: engine pins in `backend/requirements.txt`; THIRD_PARTY_NOTICES covers them; no vendor add-on packages or private sample corpora in any archive (provenance check against git).

### Risks and findings

1. **Gateway silently falls back to `host.docker.internal:8081` (the demo engine port) when `NETSPOUT_BACKEND_URL` does not reach splunkd's handler process.** In Docker, splunkd does not pass container environment to REST handlers, so the lab gateway talked to the *protected demo engine* until it was set in `splunk-launch.conf`. Only read-only GETs were sent (some during diagnosis); nothing was changed. Release notes must require `NETSPOUT_BACKEND_URL` in `splunk-launch.conf`; consider failing closed instead of falling back (not done: behaviour change outside scope).
2. Legacy handler `[script:netspout_api] match = /netspout` is a prefix of `/netspout_gateway`; it did not cause the failure (re-tested), left unchanged.
3. Builds are not byte-reproducible (archive timestamps differ between builds of the same commit).
4. `build_splunk_package.py` printed "PASS … (< 5.0 MB)" for a 7.5 MB archive; relabelled as an unlimited INFO line.

## Known limitations

- RC and the release share the version 2.0.0.
- VERIFIED integrations: cisco:asa, cisco:ios, fortigate_traffic, pan:traffic, pan:threat, pan:system; all other sourcetypes are not claimed.
- Only IOS XR `cisco_metrics` streaming is tested; no other metric names are claimed.
- Splunk Cloud was not tested (Cloud edition is dashboards only).
- Test-harness only: the packaged lab needs the in-container tap and forwarder (`phase10_rc_install.py start-tap`).

## Readiness

- **Controlled demo: READY** with the engine's `NETSPOUT_BACKEND_URL` set in `splunk-launch.conf` (risk 1) and the demo ports untouched.
- **Broader release: NOT READY.** Required gates not tested: the Phase 4 protected-lab specs (4b); real Splunk Cloud; a distinct version number; fail-closed gateway default decision; the RC has not been installed on a non-Docker Splunk or a customer-hosted engine host outside Docker.
