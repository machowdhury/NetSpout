# PulseForge install architecture: two options, one experience

Status: decision and phased plan, 2026-11-02. Nothing here is a release claim. "Verified" means run on this date and recorded under `docs/verification/evidence/install/`; everything else is labelled unverified.

## 1. Why there are two packages today

| Piece | What it is | Evidence |
|---|---|---|
| `netspout.spl` | Splunk UI (React in an Explorer view), 148 Dashboard Studio views, REST handlers, and `netspout_gateway`, a **reverse proxy** that forwards `/api/...` to `NETSPOUT_BACKEND_URL` (`netspout/bin/netspout_gateway.py`) | gateway source |
| Engine | FastAPI app (`backend/app/main.py`, about 3,500 lines) over `src/netspout_core`: runs, delivery accounting, HEC, searches, generators, native gNMI/SNMP/flow | `backend/requirements.txt` |

The split is an artifact of how the engine grew, not a Splunk requirement for Enterprise:

- The engine's HTTP dependencies (`fastapi`, `pydantic` 2, `uvicorn`, `httpx`, `websockets`) are not in Splunk's bundled Python (checked in Splunk 10.2.7: Python 3.9 and 3.13 both lack them). `grpcio`, `protobuf` and `cryptography` are bundled, at older versions than the engine's pins.
- **Probe (verified):** with 18 vendored wheels (3.8 MB; 13 MB unpacked; two compiled: `pydantic_core`, `websockets`), the real `app.main` imports and answers `/api/health` and `/api/search` inside Splunk's own Python 3.13, and the gNMI server module imports (`scripts/probe_splunk_python_engine.sh`, evidence `splunk_python_engine_probe_2026-11-02.json`). Not tested: running gNMI on the bundled grpc, Python 3.9, non-x86_64 platforms, running as a Splunk-managed process.
- Genuinely external: anything that **listens or sends on the network** (gNMI gRPC server, SNMP agent, syslog, IPFIX UDP export, GoFlow2 collector). Splunk Cloud cannot host these.

## 2. What can run inside the app, what cannot

| Capability | In a Splunk Enterprise app | Splunk Cloud app |
|---|---|---|
| UI, dashboards, search, scenario preview, HEC delivery with accounting, run monitor, Connection Center | feasible (stdlib plus vendored wheels; probe above) | UI/dashboards only; no Python execution of this kind is evidenced |
| Long-running streaming runs | feasible but needs a long-lived process (see options) | not feasible |
| gNMI / SNMP / syslog / IPFIX wire stages | feasible on Enterprise (sockets), unverified inside splunkd | **prohibited**: AppInspect `check_for_python_udp_network_communications` (25 findings in the full app) |
| Compiled dependencies | platform-specific wheels; AppInspect behaviour for bundled binaries is **untested** | bundled binaries are not expected to pass vetting (not tested) |

## 3. Option B (single `netspout.spl`) evaluated

| | A. Handlers only (ASGI app called inside persistent REST handlers) | B. In-process without HTTP | C. Splunk-managed companion: a modular input starts the engine on loopback |
|---|---|---|---|
| Mechanism | `scripttype = persist` handlers already exist in `restmap.conf` | call `netspout_core` directly | the app already declares a modular input (`netspout_streamer`); splunkd starts and logs it |
| Enterprise compatibility | plausible | plausible; needs a rewrite of the 3,500-line API layer | plausible |
| Long-running runs | live as threads in the handler process; lifetime tied to that process (**unverified**: recycling/idle behaviour) | same | own process; survives handler restarts |
| Request concurrency | persistent handlers serve one request at a time per process unless threaded (**unverified**); long searches could block polling | same | engine is a normal threaded ASGI server |
| Auth and RBAC | Splunk session only; no engine port exists | same | Splunk gateway plus a shared key; engine on 127.0.0.1 only |
| Secrets, config | Splunk `storage/passwords` (not yet used by the engine; it reads env vars today) | same | same |
| Upgrade | app update plus restart | same | app update plus restart restarts the engine |
| Size | about +4 MB wheels (+ platform variants) | smallest | same as A |
| Vetting | AppInspect cloud failures include UDP; Enterprise-only | same | same |
| Effort (estimate) | medium | high (speculative rewrite) | medium |

**Recommendation for Splunk Enterprise: C**, with A as the fallback, behind a prototype gate (Phase 1) that must pass the acceptance tests below before any customer-facing claim. C keeps the existing, verified gateway-to-engine contract and adds only a launcher and vendored dependencies; the engine stays on 127.0.0.1 with a per-install key, so no port is user-facing.

Blockers that remain real until proven otherwise: (1) compiled wheels per platform (Linux x86_64 and aarch64 for the Splunk Python in use; macOS and Windows Splunk hosts would be unsupported); (2) whether AppInspect (non-Cloud tags) accepts bundled wheels; (3) bundled `grpcio`/`protobuf`/`cryptography` are older than the engine's pins, so the gNMI path needs its own tests; (4) splunkd's lifecycle of a modular-input child is assumed, not verified.

## 4. Splunk Cloud

Not feasible as a single full package. Evidence: AppInspect (Cloud tags, 4.4.0) on the full app, `docs/verification/evidence/appinspect/cloud.json`: 8 failures. Seven are packaging fixes (modular-input/REST `python.version`/`python.required`, `indexes.conf` properties, `is_configured`, `[triggers]`). One is fundamental: programmatic UDP in 25 places, plus the engine's need to host listeners. `netspout_cloud.spl` (dashboards only, 148 views) passed the Cloud ruleset with 0 failures, 0 errors; that is a pre-submission result, not approval.

Honest Cloud offering, recommended name: **PulseForge for Splunk Cloud: dashboards plus a customer-hosted engine.** It is two parts and says so: `netspout_cloud.spl` plus the engine-only Docker deployment below, which talks to the Cloud HEC endpoint. What was tested against Cloud: a bounded metrics check (`test_metrics`); the Cloud app was never installed. Requires Splunk's own vetting and approval, which has not been requested.

## 5. Option A: Docker

Existing assets:

| Asset | State |
|---|---|
| `docker-compose.yml` + `Dockerfile.standalone` | all-in-one: Splunk Enterprise 10.2, the app and the engine in one container; collector and OTel as extra services. Validated in earlier phases ("clean-room" images exist); **not re-run in this branch** because a second Splunk would have competed with the demo lab for memory |
| `deploy/docker/Dockerfile.engine` + `docker-compose.engine.yml` (new) | engine only, for an existing Splunk or the Cloud edition. **Verified 2026-11-02** (`engine_docker_2026-11-02.json`): builds, healthy, search works, non-root, read-only root filesystem, loopback-only publish, restart keeps the state volume. One defect found and fixed: the incident-pack generators (in `netspout/bin`) were not copied |

Defects found in the all-in-one profile by reading, **not fixed** because they cannot be validated without starting a second Splunk:

1. It publishes the engine port (`127.0.0.1:8081`).
2. The gateway's default engine URL inside a container is `host.docker.internal:8081` and no `NETSPOUT_BACKEND_URL` is set, so it works on Docker Desktop only through the published port and would fail on a Linux host.
3. The collector and OTel services are not optional profiles; UDP 514 is published.
4. It runs the engine with `start_backend &` and nothing restarts it if it dies.

## 6. Security

| Finding | State |
|---|---|
| The engine has **no authentication**; Splunk RBAC holds only while its port is unreachable | open (documented) |
| Gateway: Splunk session required; POST needs one of the role names `admin`, `sc_admin`, `power` (role names, not capabilities); GET is open to any authenticated user | open |
| **Implemented now (opt-in, off by default):** `PULSEFORGE_GATEWAY_KEY`. With it set, the engine returns 401 to any request without the matching `X-PulseForge-Gateway-Key` except `/api/health`; the gateway adds the header from the same variable. `tests/test_gateway_key.py` (3 tests) pass; the existing NetFlow and scenario-dashboard tests still pass | implemented, unit-tested, **not exercised through a live Splunk** and not enabled in the demo lab |
| Keys for the Docker profiles are not generated yet | open (Phase 2) |
| WebSocket endpoints are not covered by the key middleware | open |

## 7. Phased plan

| Phase | Deliverable | Acceptance test | Risk |
|---|---|---|---|
| 0 (done here) | decision, probe, engine-only Docker, opt-in gateway key | evidence above; 3 new tests | low |
| 1 | Prototype C on Splunk 10.2 in an isolated container: vendored wheels, modular-input launcher, loopback port, key | fresh Splunk: install one `.spl`, restart, `curl` to the engine port from outside fails without the key, UI search and a bounded scenario run through Splunk Web, run survives a handler restart, splunkd restart does not resend a run, AppInspect (Enterprise tags) result recorded | medium: lifecycle and AppInspect unknowns |
| 2 | all-in-one Docker hardening: generate the key at first start (0600, in the volume), `NETSPOUT_BACKEND_URL=http://127.0.0.1:8081`, stop publishing 8081, collector and OTel as profiles, engine supervision | fresh Linux host: `docker compose up -d`, log in, run a bounded scenario, no engine port on the host, restart and upgrade keep state | medium |
| 3 | capability-based gateway authorization, first-run readiness panel (detect indexes, HEC, search permission, collectors) | low-privilege user cannot POST or read configuration; readiness result is actionable | medium |
| 4 | Cloud: packaging fixes only if a Cloud-vetted scope is agreed with Splunk | Splunk's vetting result | high: needs Splunk's approval |

## 8. Unverified in this work

Option C and A mechanisms inside a running splunkd; gNMI on bundled grpc; Python 3.9; any non-x86_64 Splunk; bundled-wheel AppInspect result; the all-in-one image today; the gateway key through a live Splunk; first-run setup quality (the existing setup wizard was not audited here).

## 9. Packages in this branch

`netspout_gateway.py` and `backend/app/main.py` changed (opt-in key). The committed `netspout.spl`, `netspout_cloud.spl` and the engine package were **not rebuilt** (the Nov 3 demo packages stay as released), so `netspout.spl` no longer matches the gateway source on this branch. Rebuild only when this work is released.

## 10. Phase 1 offline prototype (done 2026-11-02; no Splunk was started)

Implemented in the app's `bin/` (not enabled by default; no `default/inputs.conf` stanza; the committed packages were not rebuilt):

| File | Role |
|---|---|
| `pulseforge_engine_launcher.py` | modular input and supervisor: single-instance lock, persistent per-install key, spawn, health probe, restart with backoff (1 to 30 s), graceful stop, orphan guard (exits if splunkd is gone), status record `engine.json` |
| `pulseforge_engine_main.py` | engine bootstrap: picks vendored dependencies from `bin/lib/<py313-linux-x86_64>`, binds a Unix socket created at mode 0600, refuses any non-loopback host, **refuses to start without the key** |
| `pulseforge_ipc.py` | gateway-to-engine channel over the socket; key from the environment or the 0600 key file |
| `backend/app/gateway_auth.py` | pure ASGI key check for **HTTP and WebSocket**; `PULSEFORGE_REQUIRE_GATEWAY_KEY=1` makes it mandatory and fail-closed |
| `netspout_gateway.py` | uses the managed engine when `NETSPOUT_BACKEND_URL` is unset and the launcher's status record exists; otherwise unchanged |
| `delivery_monitor.stop_all` + lifespan | on shutdown, active runs are stopped and final counters persisted |

Findings, each backed by `tests/test_engine_launcher.py` and `tests/test_gateway_key.py` (278 targeted tests pass together with the NetFlow, dashboard, monitor and incident-pack suites):

- The existing FastAPI engine initializes with no virtual environment, from vendored packages plus the interpreter's own (earlier probe) and now starts as a supervised subprocess from the bootstrap.
- **Private boundary:** the socket is 0600 inside a 0700 directory, no TCP listener exists for the engine process (checked with `lsof`), and a request without or with a wrong key gets 401 while `/api/health` stays open for supervision. **Defect found and fixed:** uvicorn chmods a socket it creates to 0666; the bootstrap now binds the socket itself and passes the file descriptor.
- **Authentication is mandatory in the managed architecture.** The earlier opt-in key remains for standalone and lab engines (unchanged behaviour when neither variable is set, so the demo lab is unaffected). WebSocket connections (`/ws/logs`, `/ws/run-progress`) are rejected without the key; the browser never reaches the engine anyway (the gateway proxies GET and POST only). Comparison is `hmac.compare_digest`; the key and the supplied value are never echoed in responses.
- The shared key is **not** user authorization. Splunk authentication and the gateway's role check still gate every call (a request with no Splunk session is refused before the engine is contacted: tested). Remaining weakness: the role check is by role name, and GET is open to any authenticated user (Phase 3).
- **Lifecycle:** start, health, crash restart (new pid, restart count, last error recorded), graceful stop (engine gone, socket removed, state `stopped`), and a second launcher on the same state directory is refused. The key survives a launcher restart.
- **Active runs and restart:** shutdown stops active runs and persists counters; a run found active in persisted state after a restart is reported INTERRUPTED and nothing is re-sent (existing engine behaviour, now tested end to end). Replay sessions follow the same rule.
- **Configuration persistence:** `NETSPOUT_CONFIG_DIR`, replay and run state live in the state directory under `$SPLUNK_HOME/var/lib/netspout`, outside the app directory (so an app upgrade keeps them). Persistence across a *Splunk* restart is not yet tested.
- **Credentials:** the engine still reads the HEC token and search password from the launcher's environment, which a Splunk-managed process does not have. Phase 3 must read them from Splunk `storage/passwords` through the modular input's session key. Until then the managed engine cannot deliver to HEC from a pure app install. This is the largest functional gap.

Still not tested offline, and so open: splunkd actually starting, stopping and restarting the modular input; Splunk's bundled Python running the launcher; gNMI on the bundled grpc; the vendored `bin/lib` layout inside a built package; AppInspect on the result; behaviour on Python 3.9 and non-x86_64 Splunk.

## 11. Post-demo clean-container acceptance plan (not run)

Run in a new, isolated container project on a free port set, only after the demo. A step passes only with recorded output.

1. Build a prototype package (not `netspout.spl`) that includes `bin/lib/py313-linux-x86_64`, `bin/engine`, the three new scripts, and a `default/inputs.conf` stanza for the launcher. Run AppInspect (Enterprise tags); record every failure.
2. Fresh `splunk/splunk:10.2`; install the single package; restart; wait for `engine.json` `state: healthy`.
3. From the host: the engine socket and key file are not reachable; no new listening port beyond 8000/8088/8089 (`ss -ltn` inside the container).
4. Log in to Splunk Web; open PulseForge; a user without write role cannot POST (403); an unauthenticated request to the gateway gets 401.
5. Direct request to the engine socket without the key: 401; WebSocket without the key: closed 1008.
6. Configure authorized indexes and HEC in Connection Center (with Phase 3 credential storage); execute a bounded stream (30 events).
7. Independent indexing check by an `index=... netspout_run_id=...` search; accepted equals indexed.
8. Restart splunkd mid-run: the run is INTERRUPTED, counters are final, no events are sent after the restart, the engine returns healthy.
9. Kill the engine process: it restarts, the UI recovers on refresh.
10. Upgrade: install a newer package over the old one; key, configuration and run history survive; the engine runs the new code after restart.
11. Uninstall: the engine process stops, no orphan; document what remains in `var/lib/netspout` and how to remove it.

## 12. Post-demo Docker fix plan (not started; the running stack is untouched)

| Problem | Fix | Test |
|---|---|---|
| Engine port 8081 published | stop publishing it; the gateway reaches the engine inside the container | `docker port` shows no 8081; UI works |
| Gateway default URL is Docker Desktop specific | set `NETSPOUT_BACKEND_URL=http://127.0.0.1:8081` in the compose service, or (after Phase 1) use the managed engine socket | works on a Linux host without `host.docker.internal` |
| Collector and OTel not optional; UDP 514 published | compose `profiles: [netflow]` and `[otel]`; drop the 514 mapping from the default | default `up` starts one service; `--profile netflow` adds the collector |
| Nothing restarts the engine | supervise it (the Phase 1 launcher, or a minimal wrapper loop) and make the container healthcheck fail when the engine is down | kill the engine: it returns and health recovers |

Do each in a fresh isolated project and re-run the all-in-one image there before trusting it.

## 13. Phase 2, offline part (2026-11-02, before the demo; no Splunk was started)

Phase 2 as authorized ("prove it in a clean Splunk") needs a new Splunk container and so waits until after the Nov 3 demo. These parts did not need one and were done:

| Item | Result |
|---|---|
| Test package builder `scripts/build_single_package_test.py` | builds `build/single_package_test/netspout_single_test.spl` (git-ignored; 17.8 MB) from a copy of `netspout/` plus `bin/engine/app`, vendored `bin/lib/<variant>`, a manifest with wheel hashes, and an enabled launcher stanza. The released packages are untouched |
| Completeness check (`--verify`) | all required runtime files present; every third-party import of the engine and core resolves in each bundled variant (except `pygnmi`, guarded by `try/except`, and `gnmi`, the last import fallback); no private keys; offline only, **not** an import test under Splunk's Python |
| Python versions | the pinned `fastapi` 0.143 and `pydantic` 2.14 require Python >= 3.10, so **no Python 3.9 variant can be built**. The managed engine is Python 3.13 only. Bundled variants: `py313-linux-x86_64`, `py313-linux-aarch64`. Untested: everything else |
| Selecting 3.13 | per the Splunk 10.2 `inputs.conf` spec, `python.version` is deprecated and has no 3.13 value; `python.required = 3.13` is the supported request and takes precedence. The stanza sets both (AppInspect still requires `python.version`). The launcher also starts the engine with `$SPLUNK_HOME/bin/python3.13` explicitly, so the launcher's own interpreter does not matter (unit-tested selection; not run under Splunk) |
| Restart semantics | the spec says `interval = 0` runs a scripted input continuously and restarts it when it exits; the spec says **nothing** about how splunkd stops modular-input processes at shutdown or disable. The launcher handles SIGTERM and exits if splunkd disappears, but whether splunkd sends SIGTERM, a kill, or closes a pipe is **unverified** and decides whether the engine is ever orphaned. This is the main reason to run Phase 2 before any claim |
| AppInspect 4.4.0 on the real package (`python:3.13-slim` container; host Python 3.15 breaks its analyzer) | 0 errors, **9 failures**, 12 warnings, 139 passed. The launcher stanza is named by no failure. One failure is new because of bundling: `check_aarch64_compatibility` flags the **x86_64** `.so` files (the aarch64 variant is not flagged). The other 8 are the release app's existing findings (python settings of `netspout_streamer`/`pulseforge_spool` and the REST handlers, `[triggers]`, `is_configured`, `indexes.conf` properties, programmatic UDP). Evidence: `evidence/install/single_package_test_build_2026-11-02.json` |
| Consequence for distribution | a single package carrying binaries for several architectures fails this check as written. Options to decide in Phase 2: one package per architecture, or accept a private-install-only package. Not decided; **not** claimed to be vettable |
| Authorization by capability | the gateway no longer uses a role-name list. POST needs capability `netspout_admin`, GET needs `netspout_view`, both asked of splunkd for the session (`authentication/current-context`), cached 30 s by hash, failing closed on any error. `authorize.conf` grants `netspout_admin` to admin, sc_admin and power (the roles allowed before) and `netspout_view` to `user` (inherited upward). Roles that do not inherit `user` lose read access: stricter than before. Unit-tested with stubs (`tests/test_gateway_capabilities.py`); **whether splunkd returns a `capabilities` list in that response is unverified** and the check fails closed if it does not |
| Secrets in responses | a sweep of every parameterless GET route (more than 40) with sentinel token and password planted finds neither (`tests/test_no_secret_in_get_responses.py`). Parameterised routes, logs and WebSocket frames were not swept |
| Tests | 286 targeted tests pass (launcher, key, capabilities, surface, monitor, NetFlow, dashboards, incident packs) |

Phase 2 container steps are exactly section 11, with these additions: confirm the process tree shows one engine under splunkd; record what signal the engine receives on `splunk stop` and on disabling the input; confirm `current-context` returns capabilities; run the AppInspect command above again on the built package; decide per-architecture packaging.

## 14. Phase 2 on a real Splunk Enterprise (AWS EC2, 2026-11-02)

Evidence: `docs/verification/evidence/install/single_package_aws_ec2_2026-11-02.json`. Splunk Enterprise **10.6.1.1**, one throwaway Ubuntu 24.04 x86_64 host, no inbound access. The plan named 10.2.7; results apply to 10.6.1.1 only.

**What the first real run exposed (all four defects fixed here, original failures kept in the evidence file):** the launcher's spec had no parameter of its own, so splunkd never defined the scheme; the gateway imported a sibling module that splunkd's by-path loader does not make importable; `splunk stop` neither signals the launcher nor leaves it a parent, so launcher and engine survived as orphans; a killed launcher is not restarted and left the engine orphaned. splunkd itself logs that it ignores `interval` for modular inputs, so `interval = 0` is not a restart guarantee.

**Verified:** splunkd starts the managed engine under `python3.13` from one package; one engine; no TCP listener; capability RBAC (admin and power read/write, viewer read-only, no-capability and unauthenticated refused; revocation lags up to 30 s); WebSocket and HTTP key enforcement; crash restart; clean stop/start; upgrade in place; Connection Center setup, a bounded NetFlow run with 224 accepted and 224 indexed by independent search; interrupted runs are not resumed or resent; uninstall stops the engine and keeps index data.

**Not solved:** secrets do not survive an engine restart (Phase 3, `storage/passwords`); a killed launcher stays down until Splunk restarts; state directory remains after uninstall; AppInspect still reports 9 failures (one packaging, eight existing); gNMI untested (bundled grpc needs `libcares.so.2` on this OS); only x86_64, only Splunk 10.6.1.1. Browser checks were headless text-level checks on the host. No Cloud claim, no AppInspect approval, no Python 3.9 support.
