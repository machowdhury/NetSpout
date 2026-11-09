# Phase 17 — single-package Splunk Enterprise implementation: report

Branch `feature/single-package-enterprise` (draft PR). Base: `main` at `269c4ee` (v2.0.1 pre-release, **unchanged**: no tag moved, no asset replaced). Architecture: approach B of `PHASE17_SINGLE_PACKAGE_FEASIBILITY.md` (Splunk-managed engine worker bundled in the app), approved.

## Artifact

| | |
|---|---|
| File | `build/single_package/netspout.spl` (git-ignored; rebuilt by `python scripts/build_single_package.py --verify`, byte-identical on rebuild) |
| sha256 | `3ea5aface7db9e9ccc05b9c80ca825d04f1376001500926f940eaade4eb3189b` |
| Bytes | 16,315,740 |
| Source commit | `35cef617d9fce69807af99453ea8682af6592f75`; `netspout/`, `backend/`, `src/` and the build script are identical at the branch head |
| App version | 2.1.0 (`app.conf` and `app.manifest` agree) |
| Bundled | the engine (`bin/engine/app`), wheels for Python 3.13 / Linux x86_64 (fastapi, uvicorn, pydantic, pydantic_core, websockets, httpx, PyYAML and dependencies); grpc, protobuf and cryptography come from Splunk's own Python |

## What changed (implementation gates)

1. **Ported** from `install/two-options-audit`, selectively (launcher, Unix-socket IPC, engine key check, capability model, build script, their tests); the gateway, `inputs.conf` and generated docs were merged by hand on top of main and the B1 fix. Not merged blindly.
2. **Secrets.** The HEC token and search credential are written by the gateway to Splunk `storage/passwords` (realm `netspout`) and read back by the launcher with its own session key at every engine start; they reach the engine only as its private environment. Verified after an engine kill and after a Splunk restart.
3. **First run in Splunk Web only**: the Connections page shows managed-engine status (no engine URL), a Restart engine button when the engine is down, and defaults to the existing-Enterprise mode.
4. **Workflows preserved**: Generate Data, Scenarios, Connections, Dashboard Studio views (same engine, same recipes).
5. **One engine, zero events**: single-instance launcher with a lock; launcher and idle engine write nothing (tests plus live idle windows).
6. **Failure handling**: engine crash → restart with backoff; launcher killed → the engine exits by itself (no orphan), status says so, `POST /engine/restart` (admin) restarts the input; `splunk stop` leaves no process; uninstall stops everything.
7. **Bounds**: install-level cap of 200 events/s and 3,600 s per stream (open-ended requests get the cap), 4 concurrent runs, engine at nice 5.
8. **AppInspect** on baseline and new package (below).
9. **Disposable Splunk Enterprise 10.2.7**, amd64 under emulation on an arm64 host.

## Defects found by the acceptance run and fixed (they would have shipped otherwise)

| Defect | Fix |
|---|---|
| Grounded samples registered in `samples.json` (Fortinet) failed under the bundled engine: the sample root was one directory level off | sample roots include `$SPLUNK_HOME/etc/apps` (`src/netspout_core/generator_modes.py`, mirrors synced) |
| The prototype launcher picked the *token* variable for `HEC_TOKEN_AND_BASIC_SEARCH` (the name contains "TOKEN") | exact match on `...SPLUNK_TOKEN`; unit test |
| `/engine` status trusted a stale status file and said "healthy" after the launcher was killed | the gateway probes the engine itself |
| The UI never sent `confirm_destination`, so every UI run against a non-lab destination was refused with 403 | explicit authorization checkbox in Generate Data and Scenarios; the button stays disabled until it is ticked |
| The built UI bundle in `netspout/appserver/static/dist` was not refreshed by `npm run build` (the repo syncs it with `scripts/build_frontend.py`) | synced; packages now contain the new UI |
| `app.manifest` still said 2.0.1 beside `app.conf` 2.1.0 (new AppInspect failure) | the build rewrites it and verifies consistency |
| Idle check by `eventcount` before/after reported a false +98 events (lazy hot-bucket counts) | idle is now measured by events *indexed* inside a time window (`_index_earliest/_index_latest`); the old-method files were removed |

## Acceptance evidence (`docs/verification/evidence/phase17/splunk-10.2.7/`)

Only `netspout.spl` was installed; no engine anywhere in the Splunk container; installed through Splunk Web (Playwright upload), Splunk restarted, no shell commands for setup.

| Check | Result |
|---|---|
| Install census | 1 launcher + 1 engine process, no extra listening TCP port, no engine app (`install_census.json`) |
| Cisco ASA, Cisco IOS, Fortinet FortiGate, Palo Alto traffic / threat / system events, 25 each | 6/6: engine counters, engine verification and an independent search delta all equal 25 (`events.json`) |
| IOS XR metrics (`cisco:ios:mdt:metric`) | 20 events → 100 datapoints found by `mstats` in a metrics index (`metrics.json`) |
| Palo Alto threat investigation scenario | completed, verified, all three sourcetypes found by search; the dashboard `pf_paloalto_threat_investigation` panels return rows for that run (`scenario.json`) |
| Streaming | continuous start/stop (attempts grow, no growth after stop, no active runs), 6 s duration run, open-ended request gets the 3,600 s cap, eps and duration over the cap refused, no run without authorization (`stream.json`) |
| Access | unauthenticated 401/403; no-capability 403; viewer can read, cannot run or save; admin can run; `power` cannot store credentials and nothing is saved; `/api/setup` never returns secrets (`authz.json`) |
| Browser (Splunk Web) | Connections shows managed status and no URL field; first-run configuration and a tested connection; Generate Data from the UI → "found 10 of 10 events"; a viewer gets a clear capability message (`phase17-splunk-web.spec.ts`, screenshots) |
| Credential persistence | after engine kill and after Splunk restart the engine reloads credentials (`secrets: loaded`) and all six event sourcetypes verify again |
| Zero idle telemetry | 0 events indexed in any non-internal index over 3-minute windows: fresh unconfigured install, after runs + upgrade, after launcher kill + restart |
| Upgrade (same package, in place) | customer `local/` stanza, saved connection and credentials preserved; workflows pass |
| Secrets at rest | none in `var/lib/netspout` or the app directory or the package or the evidence; `passwords.conf` holds `$7$` values (Splunk's own audit log holds the token written by the container's own setup, before the app was installed) |
| Resources | idle after runs: engine 166 MB RSS, launcher 41 MB, splunkd 447 MB |

## AppInspect 4.4.0 (every failure, both packages)

| Package | precert failures | cloud-tag failures |
|---|---|---|
| Baseline v2.0.1 `netspout.spl` (sha 53f09e5f…ff17) | **8** | 8 |
| New single package | **9** | 8 |

Common to both (all 8): `check_for_python_udp_network_communications` (25 findings), `check_indexes_conf_properties` (7), `check_inputs_conf_spec_stanzas_has_python_version_property` (2), `check_modular_inputs_python_required` (4), `check_reload_trigger_for_all_custom_confs` (1), `check_rest_handler_python_executable_exists` (2), `check_script_restmap_conf_python_required` (2), `check_that_setup_has_not_been_performed` (1).
Added by the single package: `check_aarch64_compatibility` (3 x86_64 `.so` files: PyYAML `_yaml`, websockets `speedups`, `pydantic_core`). The package therefore **cannot be submitted to Splunkbase or Splunk Cloud** as built; it is a self-distributed Enterprise app. Full reports: `appinspect_*_precert_full.json`, summary `appinspect_summary.json`.

## Regression

Phase 16 selection (39 files) plus the 9 files added or touched here: **9 failed, 4110 passed, 5 skipped**. The 9 failures are the same nine documented for v2.0.1 (`test_gate6_integrity::test_07_successful_hec`; `test_gate9_5_telemetry_semantics::test_01` with its seven sub-failures; `test_phase12_agentic_supply_chain::…test_dashboard_recipe_families_integrate_without_regression`); no new failures. 4110 passed here against 4072 for v2.0.1 (+38, from the launcher, IPC, key, capability, secret and limit tests). Not re-run: the whole `tests/` tree outside that selection, and the Playwright suites other than the new Splunk Web spec.

## Limitations and what was not verified

- Supported scope only: Splunk Enterprise 10.2.7, Linux x86_64, single instance. Everything was run on an amd64 image emulated on arm64: timing is not representative, and native amd64 hardware was not tested.
- "Single package" means an **app-managed engine process**, not code inside splunkd's request path. The engine is code running as the Splunk OS user.
- Splunk Cloud: not supported, not designed here.
- Saving credentials needs `edit_storage_passwords` (admin); a `power` user can run generation but cannot configure it.
- splunkd does not restart a killed launcher by itself (it restarts at the next Splunk start, or via Restart engine). The `interval` of the input is ignored by splunkd.
- Uninstall leaves `$SPLUNK_HOME/var/lib/netspout` (settings, per-install key). Reinstalling then reuses the saved settings but not the credentials.
- Not tested: upgrade from the v2.0.1 two-component install to this package (same app id; the old Engine URL setting is ignored); `splunk stop` and uninstall on the final artifact (done on the previous build, which differs only in the manifest version string); memory/CPU under sustained 200 events/s streaming; gNMI/SNMP/syslog/IPFIX wire listeners; Splunk versions other than 10.2.7; Python 3.9; distributed Splunk; a native amd64 host; browsers other than headless Chromium; the Dashboard Studio dashboards were checked by running their searches for the run, not by rendering all panels.
- The Docker host also ran an unrelated evaluation stack with its own engine (host port 8081). It was not touched. The package never uses a TCP engine URL, and the Splunk under test is in its own container.
- The engine's own `/api/health` still reports its code version `2.0.1`.

## GO / NO-GO for merging

**NO-GO for merging to `main` or releasing now**; GO for review of this draft PR. Reasons: AppInspect failures and the x86_64-only binaries make it a self-distributed candidate, nothing but 10.2.7 was tested, emulated hardware only, and the untested items above. If review accepts the support boundary (Linux x86_64, Splunk 10.2.7, single instance, no Splunk Cloud) and the listed AppInspect failures, the remaining gating work is: repeat the acceptance on native amd64, test the 2.0.1 → 2.1.0 upgrade, and measure sustained streaming resource use.
