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
