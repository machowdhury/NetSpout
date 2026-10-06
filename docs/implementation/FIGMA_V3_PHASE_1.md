# Figma v3 Phase 1 — Unified UI Shell

Completed on 2026-10-05 on `feature/figma-v3-unified-telemetry-lab`.

## Result

Phase 1 establishes the shared NetSpout application shell without replacing the
existing telemetry engine. The product now identifies itself as **NetSpout —
Unified Enterprise Telemetry Lab** and provides:

- the approved Home, Generate, Build, Observe, Investigate, Catalog, and System navigation;
- six domain perspectives with explicit maturity states;
- Simple and Advanced experiences;
- responsive desktop and mobile navigation;
- shared design tokens, status/provenance badges, panels, state views, and technical tables;
- hash-based routes that work in both standalone hosting and a Splunk iframe;
- truthful loading, empty, unavailable, planned, research-required, degraded, and error states;
- Home and Pipeline Health views backed by current backend responses; and
- retained access to the existing workflow, operations, and canvas experiences.

No prototype event count, pipeline result, Splunk observation, or detection
claim is presented as measured runtime data. Unsupported views remain visible
as explicit product states rather than fabricated functionality.

## Commits

- `dc65748` — `feat(ui): add unified telemetry lab shell`
- `a6d9d7c` — `fix(docker): serve unified shell from standalone endpoint`

## Changed files

Application architecture and shared UI:

- `frontend/src/App.tsx`
- `frontend/src/app/navigation.ts`
- `frontend/src/app/useHashRoute.ts`
- `frontend/src/lib/api.ts`
- `frontend/src/components/shell/AppShell.tsx`
- `frontend/src/components/home/HomeView.tsx`
- `frontend/src/components/operations/PipelineHealthView.tsx`
- `frontend/src/components/states/ProductStateView.tsx`
- `frontend/src/components/ui/SystemPrimitives.tsx`
- `frontend/src/index.css`
- `frontend/src/main.tsx`

Preserved legacy integration adjustments:

- `frontend/src/components/OpenConfigTreeModal.tsx`
- `frontend/src/components/SyslogConfigModal.tsx`
- `frontend/src/components/TopBar.tsx`
- `frontend/src/components/workflow/FiveStepWorkflow.tsx`
- `frontend/src/components/workflow/StepConnect.tsx`

Build, tests, and packaged application:

- `.dockerignore`
- `.gitignore`
- `Dockerfile.standalone`
- `frontend/package.json`
- `frontend/package-lock.json`
- `frontend/playwright.config.ts`
- `frontend/tests/unified-shell.spec.ts`
- `tests/test_gate5_ux.py`
- `netspout/appserver/static/dist/index.html`
- `netspout/appserver/static/dist/assets/index-AXr0k-nJ.js`
- `docs/implementation/images/phase1-unified-shell.png`

## Validation

Frontend:

- `npm run lint`: passed with 13 pre-existing warnings; three touched-file
  unused-catch warnings were removed.
- `npm run build`: passed; production bundle is 783.59 KB before gzip and
  retains the existing large-chunk warning.
- `npm run test:e2e`: 2/2 passed against the Vite development endpoint.
- `PLAYWRIGHT_BASE_URL=http://127.0.0.1:8081 npm run test:e2e`: 2/2 passed
  against the Docker-hosted product endpoint, including navigation, all six
  domains, Simple/Advanced switching, and mobile navigation.
- `tests/test_gate5_ux.py`: 22/22 passed after updating obsolete source-string
  assertions to validate the new shell architecture.

Protocol regression:

- SNMP productization and gNMI collector targeted suites: 26/26 passed.
- No backend telemetry or protocol implementation was replaced.

Docker Desktop on Apple Silicon:

- Compose configuration: passed, with the existing obsolete `version` warning.
- `docker compose build splunk-netspout`: passed.
- `docker compose up -d --force-recreate`: passed.
- Splunk/NetSpout container: Docker `healthy`.
- OTel Collector: running.
- standalone UI `/`: HTTP 200.
- backend `/health`: HTTP 200.
- pipeline health API: HTTP 200.
- Splunk Web: HTTP 303 login redirect, as expected.
- Splunk HEC health: HTTP 200.
- authenticated Splunk REST/search: HTTP 200.

The screenshot is a deterministic layout test fixture. Runtime status
validation was performed separately against the live Docker endpoints.

## Security application

- No new hardcoded credential was introduced. Frontend credential defaults now
  remain empty, and the standalone image no longer embeds a Splunk password.
- A frontend scan found no private-key, certificate, or common provider-token
  patterns.
- No X.509 certificate data was added, so certificate validity, strength,
  signature, and issuer checks were not applicable to the Phase 1 diff.
- No cryptographic algorithm or protocol policy was introduced or changed.
- Existing demo credentials and insecure local TLS behavior outside the
  frontend remain Phase 0 defects and were not broadened by this phase.

## Regressions and limitations

No Phase 1 regression was found in the targeted UI, SNMP, or gNMI suites.

The following Phase 0 defects remain intentionally unresolved:

- Mode B/C/D dispatch calls a missing dispatcher method.
- Native SNMP container runtime uses incompatible Python syntax.
- Packaged gNMI protobuf runtime is incompatible.
- Flow collection is stopped and not orchestrated.
- OTel acceptance is not yet proven as Splunk observation.
- Aggregate backend pipeline health remains misleading.
- Generation evidence lacks receiver, Splunk, and duplicate measurements.
- Sample parsing may treat YAML metadata as telemetry.
- The retained legacy UI still contains an in-browser simulation fallback.
- Existing tracked demo credentials remain outside the new frontend code.
- Existing local Splunk/OTel paths disable TLS verification.

The Compose run also reused volumes originally created by the
`netspout-clean-room` project; Docker reported the existing project-label
mismatch without preventing startup.

## Phase 2 readiness

The shell, routing, reusable state components, backend API boundary, and
provenance/status vocabulary are ready for Phase 2 catalog and provenance work.
Phase 2 has not started.

## Recovery

- Starting commit: `b9521c131deffcd4d1a9f4f5fc9900486de58492`
- Immutable backup tag: `pre-figma-v3-implementation`
