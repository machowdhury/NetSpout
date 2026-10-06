# Figma v3 Implementation Baseline

Captured on 2026-10-05 before product implementation changes.

## Recovery point

- Repository: `https://github.com/machowdhury/NetSpout`
- Starting branch: `main`
- Starting commit: `b9521c131deffcd4d1a9f4f5fc9900486de58492`
- Verified `origin/main`: `b9521c131deffcd4d1a9f4f5fc9900486de58492`
- Existing release tag: `v1.0.0-rc1`
- Immutable backup tag: `pre-figma-v3-implementation`
- Implementation branch: `feature/figma-v3-unified-telemetry-lab`
- Both new refs were pushed and verified on `origin` before source changes.

Restore the pre-implementation application with:

```bash
git checkout pre-figma-v3-implementation
```

## Environment

- macOS 27.0 (Build 26A428), Apple Silicon (`arm64`)
- Docker Desktop 4.90.0
- Docker Engine 29.7.2, Linux `arm64`
- Docker Compose v5.5.1
- Built application image: Linux `amd64` under emulation
- Python 3.14.7
- Node.js 26.5.0
- npm 11.17.0

An older `netspout-clean-room` stack was already running. Its containers were stopped and preserved without deletion as:

- `splunk-netspout-pre-figma-v3-20261005`
- `netspout-otel-pre-figma-v3-20261005`

The current branch stack reused the existing named Splunk data/configuration volumes.

## Commands and results

### Repository safety

```bash
git fetch origin --prune --tags
git tag -a pre-figma-v3-implementation <starting-commit>
git switch -c feature/figma-v3-unified-telemetry-lab <starting-commit>
git push origin refs/tags/pre-figma-v3-implementation
git push -u origin feature/figma-v3-unified-telemetry-lab
```

Result: passed; local and remote refs resolve to the starting commit.

### Python regression

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
```

Result: 391 tests, 1 failure, 1 import error, 1 skip.

- Import error: `test_gate12f_snmp_productization` could not import `app` because the documented-style command did not include `backend` in `PYTHONPATH`.
- Failure: Gate 13C controlled-failure assertion did not receive the expected `SAMPLE_INTERVAL_BELOW_FLOOR` text while gRPC fork warnings were emitted.
- The suite rewrote historical Gate 13D evidence. Those incidental changes were immediately restored; no historical certification artifact was committed.

Targeted retests:

```bash
PYTHONPATH=src:backend python3 -m unittest tests/test_gate12f_snmp_productization.py
PYTHONPATH=src python3 -m unittest tests/test_gate13c_gnmi_collector.py
```

Result: 12/12 SNMP tests passed; 14/14 gNMI collector tests passed. The full-suite Gate 13C failure is therefore order/interference-sensitive.

### Frontend

```bash
cd frontend
npm ci
npm run lint
npm run build
npm audit --json
```

Result:

- install passed
- lint passed with warnings
- TypeScript/Vite production build passed
- generated bundle is approximately 748 KB before gzip and triggers the large-chunk warning
- npm audit reports one high-severity transitive `source-map-js` denial-of-service advisory with a fix available

### Docker

```bash
docker compose config --quiet
docker compose build
docker compose up -d
docker compose restart
```

Result:

- Compose validation passed with an obsolete `version` warning.
- Fresh image build passed.
- Startup passed after preserving the conflicting older stack.
- Restart passed.
- `splunk-netspout` became Docker `healthy`.
- OTel Collector started and accepted OTLP/HTTP.

Observed endpoints:

- backend `/health`: HTTP 200
- Splunk Web: HTTP 303 login redirect
- Splunk HEC health: HTTP 200
- Splunk REST search: authenticated search returned data
- standalone UI at backend `/`: HTTP 404

## Current capability findings

### Passing

- Docker image build on Apple Silicon using the declared `linux/amd64` platform
- backend health
- Splunk Web startup
- Splunk HEC health
- Splunk REST/search
- non-dispatch Mode B, C, and D API calls
- Mode C generated the requested count of 10
- container restart and recovery

### Failing or misleading

1. **Standalone Web UI is unavailable.** Port 8081 serves the API, but `/` returns 404 because the frontend distribution is not copied to the path expected by the FastAPI static mount.
2. **Canonical generator dispatch is broken.** Mode D with `dispatch=true` returns HTTP 500 because `TelemetryDispatcher` has no `dispatch_log_entry` method. Mode B/C use the same missing method.
3. **Native SNMP is incompatible with the container runtime.** Preflight returns HTTP 500 on Python 3.9 because a PEP 604 union annotation is evaluated at runtime.
4. **Native gNMI is incompatible with the packaged protobuf runtime.** Preflight returns HTTP 500 because generated protobuf code requires a newer runtime than the image installs.
5. **Native Flow collector is stopped.** Health reports no collector process, no UDP listeners, and no Splunk observation.
6. **OTel-to-Splunk was not observed.** The OTel Collector accepted an OTLP/HTTP log with HTTP 200, but a real Splunk search found zero matching events.
7. **Pipeline aggregate health is not truthful.** `/api/health/pipelines` reports overall `HEALTHY` while Syslog, SNMP, gNMI, and Flow are only `INITIALIZED`; direct native preflights fail or report stopped.
8. **Generation evidence is incomplete.** Mode C returns requested/generated/dispatched counts only. It does not measure receiver observation, Splunk observation, or duplicates.
9. **Sample parsing can treat YAML metadata as telemetry.** A “grounded” single-event request returned a metadata line rather than an event payload.
10. **The frontend includes an in-browser simulation fallback and embedded prototype telemetry strings.** These can present generated activity while the backend is disconnected and require isolation or removal from production truth paths.
11. **Tracked demo credentials exist in source, Compose, Docker, frontend, and OTel configuration.** New implementation work must move credentials to runtime configuration/secrets and fail closed outside an explicit demo profile.
12. **TLS verification is disabled in local Splunk/OTel paths.** No certificate files or embedded X.509 certificate data were found, so certificate expiration/key/signature checks were not applicable to this baseline.

## Phase 0 conclusion

The recovery baseline is valid and remotely available. The repository contains substantial reusable telemetry and catalog work, but several previously reported RC1-era runtime defects remain present. Phase 1 UI work must preserve the existing engine while avoiding false runtime claims; blocking runtime defects should be repaired incrementally in the relevant functional phases.
