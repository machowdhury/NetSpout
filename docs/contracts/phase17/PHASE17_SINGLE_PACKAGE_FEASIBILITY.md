# Phase 17 — single-package Splunk Enterprise install: architecture feasibility report

Status: feasibility only. No migration code was written. Baseline: `main` at `269c4ee` (published pre-release v2.0.1, unchanged). "Evidence" means a file in this repository; "unverified" means nobody has run it.

## 1. Current two-component dependency map

| Component | What it contains | Needed for generation? |
|---|---|---|
| `netspout.spl` (Splunk app) | React UI, 432 Dashboard Studio views, `netspout_gateway` (a persistent REST handler that is a reverse proxy to the engine URL in `netspout_engine.conf`), older handlers (`/netspout`, `/datablaster/execute`, which launches `run_simulation.py` by subprocess), modular inputs `netspout_streamer` (B1-fixed) and `pulseforge_spool`, and a mirror of `netspout_core` in `bin/` | No. It renders and forwards |
| `pulseforge-engine.tar.gz` | FastAPI app `backend/app/main.py` (3,793 lines) over `src/netspout_core`: runs, delivery accounting, HEC sender, Splunk search verification, Connection Center, replay, scenarios, metrics, streaming, native gNMI/SNMP/flow | **Yes.** Every Generate Data, Scenario and Stream call is an engine HTTP call |
| Engine dependencies | fastapi 0.143, uvicorn 0.54, pydantic 2.14 (compiled `pydantic_core`), websockets 17 (compiled), httpx, PyYAML, grpcio, protobuf, cryptography, pygnmi; **Python 3.13** (pydantic 2.14 and fastapi 0.143 need at least 3.10) | |

Splunk's own Python (10.2.7: 3.9 and 3.13, checked again today) contains none of the HTTP stack. `grpcio`, `protobuf`, `cryptography` are bundled, older than the engine's pins.

## 2. Why the engine was separated (repository evidence)

`docs/architecture/PULSEFORGE_INSTALL_ARCHITECTURE_DECISION.md` (branch `install/two-options-audit`, not on main) says it directly: the split "is an artifact of how the engine grew, not a Splunk requirement for Enterprise". The engine is a standalone ASGI service with no Splunk imports, with dependencies Splunk's Python lacks, and with network listeners (gNMI, SNMP, syslog, IPFIX, GoFlow collector) that Splunk Cloud cannot host. `docs/guides/01_PRODUCT_OVERVIEW.md` documents it as "a Splunk app plus a separate engine". No document shows a Splunk technical reason for the split on Enterprise.

## 3. Prior art that already exists (important)

Branch `origin/install/two-options-audit` (7 commits, never merged) built and tested exactly this idea on **real Splunk Enterprise 10.6.1.1** (AWS EC2, 2026-11-02, `docs/verification/evidence/install/single_package_aws_ec2_2026-11-02.json`):

- A modular input `pulseforge_engine_launcher` starts and supervises the engine as a child process under Splunk's `python3.13`, with vendored wheels in `bin/lib/`, a Unix socket (0600, directory 0700, no TCP port), and a per-install key; the gateway talks over the socket.
- **PASS:** install of one package; launcher started by splunkd; one engine only; crash restart in about 4 s; no orphan after `splunk stop` or splunkd SIGKILL (after four fixed failures, all recorded); Splunk restart restores the engine; interrupted run reported INTERRUPTED and never resent; socket and key permissions; 401 without key; WebSocket rejected without key; capability model (POST needs `netspout_admin`, GET `netspout_view`, unauthenticated 401, revocation about 30 s); HEC token not in logs or state; Connection Center set up through the gateway; a bounded NetFlow run indexed 224 of 224 verified by independent search; in-place upgrade; uninstall stops the engine and keeps index data.
- **FAIL or limit:** HEC token and search password are **not retained** across an engine restart (they are read from environment variables a Splunk-managed process does not have); a killed launcher is not restarted by splunkd until Splunk restarts; state directory remains after uninstall; AppInspect 9 failures (6 after later edits).
- **NOT run:** gNMI on bundled grpc, aarch64, Splunk 10.2.7, non-admin browser sessions, browser checks were text-level only.

Merging that branch onto today's main conflicts in only `netspout/bin/netspout_gateway.py`, `.gitignore`, `README.md` and generated docs (checked with `git merge-tree`); the launcher, bootstrap, IPC, auth and build script merge cleanly. It was not rebuilt or run for this report, and it predates RC1 to RC7, Policy A and the B1 fix.

## 4. The two approaches

The two approaches you named are different **process models** that share the same engine code and the same vendored wheels.

| | **A. Embedded: ASGI app inside splunkd's persistent REST handler** | **B. App-managed worker: a launcher input starts the engine as a child process; REST handlers control it** |
|---|---|---|
| Install | one `.spl` | one `.spl`; splunkd starts the launcher at start-up |
| Security | no port at all; Splunk session and capabilities only | no TCP port (Unix socket 0600), plus a per-install key; capabilities at the gateway (verified on EC2) |
| Runtime | wheels in `bin/lib`, Splunk Python 3.13 | same |
| Long runs and streaming | live as threads in the handler's Python process; its recycling and idle behaviour is **unverified**; persistent handlers serve one request at a time unless threaded, so a long search can block progress polling (**unverified**) | own process; survives handler restarts; normal threaded ASGI server (**verified** on EC2) |
| Failure handling | a crashing run can take the handler process with it; nothing restarts it except splunkd's next request | supervisor with backoff restart (verified); orphan guards (verified) |
| Job isolation | shares memory with the handler process | separate process, one place to cap memory and stop |
| Upgrade and rollback | app update and restart | same (verified in place) |
| AppInspect | compiled wheels; UDP check; Enterprise only | the same findings (see 7) plus a modular input that is meant to stay running |
| Existing recipes | works unchanged only if the 3,793-line API is callable in-process | unchanged; the API runs as is |
| Evidence | only the import probe (`app.main` answers `/api/health` in Splunk Python 3.13) | 20+ checks passed on real Splunk |

**Recommendation: B**, in the form already prototyped. It reuses the engine and the verified gateway contract, and its failure modes were found and fixed on a real Splunk. A is smaller in theory but would put long-running generation inside a request-serving process whose lifecycle nobody has measured.

**What is honest to say:** B is still a separate OS process. It is *installed and started by the app with no customer action*, so it meets "one file, no separate engine installation", but it is not "no engine process". Marketing and docs must not claim the generator runs inside splunkd's request path.

## 5. Required code and packaging changes

1. Port the prototype onto main (resolve `netspout_gateway.py`; merge the rest) and rebuild the vendored wheels against today's pins (`cp313`, manylinux x86_64; the aarch64 variant is dropped, see 7).
2. **Secrets:** read the HEC token and search credential from Splunk `storage/passwords` through the launcher's session key and keep them out of environment variables, logs and state. This is the biggest functional gap: today a pure app install cannot deliver to HEC after an engine restart.
3. Make the managed engine the default path: no engine URL page, "Connections" shows managed-engine status; destination index selection and validation stay in the existing Connection Center.
4. Launcher inputs must emit **nothing**: the launcher is a single-instance modular input that, like the streamer behind defect B1, is started at every splunkd start. It must be enabled by default (otherwise nothing runs), so the B1 test "every shipped input disabled" must change to "no shipped input generates events", with a test proving the launcher and an idle engine write zero events.
5. Supervision gap: a killed launcher is not restarted until Splunk restarts; add a health check in the gateway that reports it clearly (and, if supported, reloads the input).
6. Explicit bounds for streaming (maximum duration and rate) enforced in the engine and shown in the UI; confirm what exists today.
7. Cleanup choices on uninstall (state directory) documented.
8. Build, audit and manifest scripts for the single package (the prototype's `scripts/build_single_package_test.py` is the starting point).

## 6. Splunk runtime and security risks

- Splunk must provide Python 3.13 (`python.required=3.13`). Verified only on 10.2.7 (image) and 10.6.1.1 (EC2). Earlier Splunk versions are **unsupported until tested**.
- Linux x86_64 only. Compiled wheels (`pydantic_core`, `websockets`, possibly grpc) are per platform; Windows, macOS and aarch64 Splunk hosts are unsupported.
- splunkd's handling of a modular-input child is not a documented contract: the EC2 run found no restart on kill, orphans on stop, and an ignored `interval`; they were worked around, not guaranteed.
- Distributed deployments: the launcher would start on every instance that has the app (search heads, possibly forwarders and indexers). Unverified, treat as unsupported; the guidance would be search-head standalone only.
- The engine process runs as the Splunk OS user with network egress to HEC and search; it has no inbound port, but it is code in the Splunk host's trust boundary.
- Memory and CPU of the engine on the Splunk host are unmeasured.
- Session and capability changes take about 30 s to apply (cache).
- gNMI server on Splunk's bundled grpc: an import test passed, but running it was never tested and `grpc` failed to load on one image; wire protocols (gNMI, SNMP, syslog, IPFIX) stay out of scope.

## 7. Effects on existing features, AppInspect, distribution

| Feature | Effect |
|---|---|
| Generate Data, Scenarios (HEC events), metrics as metrics, streaming, run verification by search, Dashboard Studio views | Expected unchanged (same engine). Must be re-proven by the Phase E acceptance suite, not assumed |
| gNMI, SNMP, syslog, NetFlow/IPFIX wire stages | Not part of the single-package promise; remain engine-with-listeners, unverified in splunkd |
| Splunk Cloud | **Out of scope and must not be implied.** AppInspect Cloud tags found a fundamental failure (programmatic UDP in 25 places) and the engine cannot run on Cloud; `netspout_cloud.spl` stays dashboards only |

AppInspect (4.4.0, precert) on the prototype package: 9 failures, 6 after later edits. Remaining: x86_64 `.so` files (`check_aarch64_compatibility`), `python.required` on existing inputs, `maxTotalDataSizeMB` in `indexes.conf`, a contradictory REST-handler Python pair, and 25 UDP findings. The single package would therefore **not** pass AppInspect cleanly and cannot be submitted to Splunkbase or Splunk Cloud as built. It is a self-distributed Enterprise app. The AppInspect state of today's main was not re-measured for this report.

## 8. Implementation phases and test strategy

1. **Port and rebuild.** Merge the prototype, rebuild wheels, build the package from a clean checkout, source-consistency and package audit, AppInspect baseline of both main and the new package.
2. **Secrets and setup.** `storage/passwords`; first-run Connection Center in the UI; tests that secrets never reach logs, state, GET responses or the package.
3. **Lifecycle and B1.** Idle events across install, restart, upgrade, uninstall (control index), launcher kill, Splunk restart, upgrade from 2.0.1 with its configuration preserved.
4. **Workflows in a fresh Splunk 10.2.7 container, only `netspout.spl` installed, no engine, no shell:** Cisco, Fortinet and Palo Alto events; IOS XR metrics (`mstats`); the Palo Alto investigation scenario with its dashboard; bounded streaming with start, stop and duration; errors and permissions (viewer, no-capability, unauthenticated); each confirmed by an independent Splunk search.
5. **Packaged browser acceptance and Python regression** (the nine known failures stay documented, no new ones).
6. **Release decision** after review; nothing is published by this work.

## 9. GO / NO-GO

**GO (conditional)** to implement a self-contained Enterprise package using **approach B**, scoped to **Splunk Enterprise on Linux x86_64 with Python 3.13 (10.2.7 as the test target), single-instance search head.**

Conditions that need your explicit decision:
1. Accept that "single package" means an **app-managed engine process**, not code running inside splunkd's request path.
2. Accept the support boundary: Linux x86_64, Splunk with Python 3.13, no distributed deployment, no Windows, macOS or aarch64, no Splunk Cloud.
3. Accept that the package will have AppInspect failures (compiled binaries, UDP) and is not suitable for Splunkbase or Cloud submission.
4. Secrets must move to `storage/passwords` before any claim of working HEC delivery from a pure install (it is a required part of the work, not an optional one).

**NO-GO** for: Splunk Cloud, non-Linux or non-x86_64 hosts, distributed Splunk, running gNMI/SNMP/syslog/IPFIX inside this package, and approach A as the primary design (no evidence of its lifecycle behaviour).

## 10. Not verified in this report

The prototype was not rebuilt or run on today's main. Its EC2 results are from 10.6.1.1 on 2026-11-02; Splunk 10.2.7 behaviour of the launcher was not run. Memory use, AppInspect on today's main, gNMI under splunkd, and Python 3.9 are all untested.
