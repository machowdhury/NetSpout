# Figma v3 Phase 4 — Guided Scenarios

## Delivery record

- Starting commit: `b331ebdb090342cabf533c257ea9b00768aa1c22`
- Implementation commit: `73ad369`
- Final code and live-evidence commit: `f972ea4`
- Branch: `feature/figma-v3-unified-telemetry-lab`
- Scope: Phase 4 only. Main was not merged, no release was created, and Phase 5 was not started.

The supported executable claim remains deliberately narrow: modeled RFC 5424
events delivered through HEC to local Docker Splunk. Architecture fixtures and
manifest fields for other technologies do not claim runnable telemetry support.

## Files changed

Authoritative contracts and runtime:

- `src/netspout_core/pack_contracts.py`
- `src/netspout_core/unified_generation.py`
- `catalog/extension_packs.json`
- generated runtime/catalog mirrors under `backend/app`, `netspout/bin`, and
  `netspout/catalog`

Frontend:

- `frontend/src/App.tsx`
- `frontend/src/components/generation/GuidedScenarioLab.tsx`
- `frontend/src/components/generation/TopologyPreview.tsx`
- `frontend/src/components/generation/scenarioVisualization.ts`
- `frontend/src/types/generation.ts`
- `frontend/src/index.css`

Tests and evidence:

- `tests/test_phase4_guided_scenarios.py`
- `frontend/tests/guided-scenario.spec.ts`
- `frontend/tests/generation-workflow.spec.ts`
- `docs/implementation/images/phase4-01-scenario-home.png` through
  `phase4-18-mixed-vendor-fixture.png`

## Manifest and completeness contract

Phase 4 extends the Phase 2B `GuidedScenarioManifest`; it does not create a
second scenario database. Optional fields now describe identity, learning,
story, environment, topology, telemetry, timeline transitions, investigation,
validation, visualization, replay policy, and production portability. Missing
optional information remains absent or is shown as undeclared rather than
invented.

Reference validation rejects missing nodes, invalid relationships, timeline
references, telemetry references, and investigation references.

`evaluate_guided_scenario_completeness()` evaluates:

1. story;
2. environment;
3. topology;
4. telemetry manifest;
5. prerequisites;
6. execution;
7. evidence;
8. investigation;
9. expected findings;
10. validation;
11. replay/reset; and
12. provenance.

The policy supports `READY`, `PARTIAL`, `RESEARCH REQUIRED`, and `UNSUPPORTED`.
Structural completeness alone does not promote a scenario to `READY`. The
current modeled lifecycle scenario satisfies all 12 structural checks but
remains `PARTIAL` because the pack is only partially verified.

## Guided Scenario architecture

The scenario route now opens a Scenario Home before execution. Manifest content
drives its story, learning objectives, duration, maturity, environment,
telemetry, integration readiness, and actions.

The non-restrictive progress model is:

`UNDERSTAND → PREPARE → RUN → OBSERVE → INVESTIGATE → VALIDATE`

Completed and available sections remain navigable. Simple mode emphasizes
explanation and tasks. Advanced mode uses the same APIs and state, adds
technical navigation, and exposes run identity and declared transport and
destination identifiers without credentials.

Prepare reuses the Phase 3 preflight API. Run and replay reuse the Phase 3
execution API. Investigation uses the existing declarative Investigation Pack
recipe. No duplicate readiness, execution, or investigation engine was added.

## Visualization architecture

The implementation follows:

`Scenario manifest → visualization model → deterministic layout → SVG renderer → runtime overlay`

`scenarioVisualization.ts` normalizes zones, nodes, relationships, telemetry
paths, incident paths, and runtime state into renderer input. Automatic layout
is deterministic: stable manifest order and IDs produce stable zone, node,
edge, and label positions. The schema also accepts a future curated layout
reference, while automatic rendering remains the default.

The renderer uses neutral NetSpout-owned geometric treatments and text. It has
no vendor-specific rendering branches, logos, copied topology symbols, or
proprietary product artwork. Node role changes shape as well as label; runtime
state changes label, stroke treatment, and restrained color so meaning does not
depend on color alone.

The topology supports:

- zones and labeled nodes;
- clickable, keyboard-focusable nodes and relationships;
- operational, telemetry, and incident path styles;
- current-state overlays;
- zoom, pan, fit-to-view, and reset;
- source and relationship technical inspectors; and
- automatic and future curated modes.

The implementation targets scenario-scale diagrams and remains practical for
roughly 50–100 entities. It is not designed or represented as a full NMS or a
10,000-node production topology engine.

## Lenses and synchronization

Telemetry Lens derives source emphasis from manifest source mappings. Incident
Lens renders only the declared causal path. Splunk Lens highlights paths whose
evidence is configured for, generated for, sent to, observed by, or validated
in Splunk. Configuration and observation remain distinct states.

Synchronization implemented in this phase includes:

- timeline phase → affected topology nodes;
- topology node → related evidence focus;
- evidence source → topology node selection;
- investigation step → relevant topology nodes and evidence sources; and
- runtime evidence counts → node and path state.

The timeline renders manifest-defined phases and state changes. Backend
execution is currently synchronous, so the UI does not fake progression with a
timer. Selecting a phase provides an inspection overlay while generated and
observed counts continue to come from backend evidence.

## Evidence, investigation, and validation

Observe retains the catalog provenance vocabulary and displays generated and
Splunk-observed counts separately. Raw previews remain subject to the existing
Phase 3 API boundary. Selecting an evidence source locates its entity; selecting
an entity filters the evidence context.

Guided investigation displays the declared question, optional hint,
portability badge, SPL, expected finding, optional explanation, and returned
result count. The current recipe remains visibly `NETSPOUT-SPECIFIC`; it is not
silently presented as production-portable.

Validation is evidence-derived. In the live journey it proved raw generation,
transport acceptance, Splunk observation, expected NetSpout sourcetype, and
declared field conditions. It truthfully reports:

- CIM: `NOT VALIDATED`
- Detection: `NOT CONFIGURED`

Those states are informational because neither capability is required by this
scenario.

## Replay/reset

Replay calls the existing run endpoint and creates a new UUID while preserving
the scenario definition and historical Splunk events. Guided runtime state and
progress restart for the new run. The UI displays previous and current run IDs,
and searches remain bounded by run identity rather than deleting historical
evidence.

## Accessibility and responsive behavior

- Interactive SVG nodes and paths are keyboard reachable and semantically
  labeled.
- Focus indicators remain visible.
- State is represented with text and shape/stroke treatment in addition to
  color.
- Controls and inspector fields have accessible labels.
- Reduced-motion media preferences disable path animation.
- The topology provides pan, zoom, fit, and reset for practical laptop and wide
  desktop widths.
- Phone-specific optimization remains outside Phase 4.

## Security review

The complete Phase 4 diff was checked for credential, provider-token,
private-key, certificate, and credential-bearing connection-string patterns.

- No password, API key, HEC token, Splunk credential, private key, or other
  secret was added.
- Existing authenticated operations continue to read credentials from backend
  environment/configuration; they are not returned to or rendered by the UI.
- Inspectors expose contract IDs and evidence counts, not sensitive connection
  values.
- No cryptographic implementation or TLS policy was added or weakened.
- No X.509 certificate material was added. Certificate expiration, key
  strength, signature algorithm, and self-signed checks are therefore not
  applicable to the Phase 4 diff.

These checks were required because the new inspectors and advanced view expose
more runtime metadata. Existing tracked demo credentials and local TLS
verification exceptions were not copied into new code and remain inherited
Phase 0 defects.

## Privacy, IP, and provenance review

- New architecture fixtures are explicitly non-production and make no telemetry
  support claim.
- Fixture identities are deterministic and fictional; no customer or lab
  identifiers were introduced.
- No captured telemetry was copied, expanded, sanitized, or reclassified.
- No Cisco topology icon, Splunk artwork, vendor logo, or proprietary product
  illustration was added.
- Vendor names in the mixed-vendor fixture are plain identity metadata rendered
  by the same neutral engine.
- Provenance remains visible and captured data is not relabeled synthetic merely
  because an identifier changes.

This phase does not replace the separate repository IP/confidentiality/licensing
audit or privacy-preserving sanitization workstream.

## Tests executed

Phase 4 contract and visualization tests:

```text
PYTHONPATH=src:backend python3 -m unittest -q \
  tests/test_phase4_guided_scenarios.py

12 tests passed.
```

Focused Phase 2B, Phase 3, and Phase 4 contract tests:

```text
39 tests passed.
```

Catalog and generated-mirror validation:

```text
69 tests passed.
```

Targeted backend, canonical-source, catalog, pack, transport-safety, native
NetFlow/IPFIX, SNMP, gNMI, and Splunk E2E regression:

```text
254 tests passed.
```

Frontend:

```text
npm run build
Passed. Bundle: 752.78 kB; gzip: 178.95 kB.

npm run lint
Passed with 13 inherited warnings outside Phase 4 files.

npx playwright test
12 tests passed.

npx playwright test tests/guided-scenario.spec.ts
4 tests passed.

PLAYWRIGHT_BASE_URL=http://127.0.0.1:8081 \
PLAYWRIGHT_LIVE_GUIDED=1 \
npx playwright test tests/guided-scenario.spec.ts --workers=1
4 tests passed against Docker.
```

The guided coverage includes Understand, Prepare, Run, Observe, Investigate,
Validate, completion, replay, advanced detail, deterministic rendering,
runtime state, optional metadata, mixed-vendor and multi-product fixtures, and
timeline/topology/evidence/investigation synchronization.

All four Phase 3 generation modes, catalog and pack validation, source mirrors,
native transport tests, authenticated Splunk observation, investigation,
frontend tests, and Docker journeys remained covered by the regression runs.

## Docker validation

- `docker compose build splunk-netspout`: passed from Phase 4 source.
- `docker compose up -d --force-recreate`: passed.
- Splunk/NetSpout container: healthy.
- OTel Collector container: running.
- Backend health: HTTP 200.
- Generation capabilities: HTTP 200.
- HTTPS HEC health: HTTP 200.
- Splunk Web: HTTP 303 login redirect.

The live journey completed:

`Open → Understand → inspect topology → Prepare → preflight → Run → timeline → Observe → investigate → Splunk results → Validate → Complete → Replay`

The run generated six events. Authenticated Splunk observation proved six
indexed events with the expected sourcetype and declared fields. The guided
investigation returned six ordered results. Replay produced a different run ID
without deleting prior events.

## Screenshot inventory and visual inspection

All runtime screenshots except the explicitly non-production architecture
fixture were captured from the rebuilt Docker application:

1. `phase4-01-scenario-home.png`
2. `phase4-02-guided-understand.png`
3. `phase4-03-automatic-topology.png`
4. `phase4-04-node-inspector.png`
5. `phase4-05-telemetry-lens.png`
6. `phase4-06-incident-lens.png`
7. `phase4-07-splunk-lens.png`
8. `phase4-08-prepare-preflight.png`
9. `phase4-09-running-scenario.png`
10. `phase4-10-active-timeline.png`
11. `phase4-11-observe-evidence.png`
12. `phase4-12-guided-investigation.png`
13. `phase4-13-spl-results.png`
14. `phase4-14-validation.png`
15. `phase4-15-completion.png`
16. `phase4-16-replay.png`
17. `phase4-17-advanced-mode.png`
18. `phase4-18-mixed-vendor-fixture.png`

Manual inspection found no clipping, node overlap, unreadable edge, excessive
whitespace, decorative fake metric, false observed status, provenance
ambiguity, secret, or sensitive identifier. Path types are distinguishable,
the layout is stable and compact, negative validation states are visible, and
the advanced capture exposes runtime identity. Relationship-label offsets were
adjusted before final capture to reduce collisions.

## Defects discovered

Fixed during Phase 4:

- relationship labels initially shared a center point and could overlap;
- the live observation assertion assumed fixture wording rather than the
  backend's more specific indexed-observation wording;
- the first advanced-mode screenshot showed preparation rather than advanced
  runtime detail; and
- investigation capture framing initially hid the question above the topology.

No new P0 or P1 regression remains.

## Inherited Phase 0 defects

Phase 4 does not claim these legacy issues are fixed:

- the legacy Mode B/C/D dispatcher calls a missing `dispatch_log_entry`;
- native SNMP remains incompatible with the Python 3.9 container path;
- packaged gNMI protobuf runtime compatibility remains unresolved;
- flow collection is stopped and not orchestrated;
- OTel acceptance is not generally proven as Splunk-indexed observation;
- aggregate pipeline health remains too optimistic;
- legacy generation lacks general receiver/Splunk/duplicate evidence;
- sample parsing may treat YAML metadata as telemetry;
- the legacy Scenario Builder retains an in-browser simulation fallback;
- tracked demo credentials remain in existing local deployment configuration;
  and
- existing local Splunk/OTel paths include TLS-verification exceptions.

The obsolete Compose `version`, constant `linux/amd64`, reused-volume label,
frontend chunk-size, npm `devdir`, datetime/Pydantic deprecation, and gRPC
diagnostic warnings also remain inherited warnings.

## Limitations and deferred functionality

- Only modeled RFC 5424 → HEC → local Splunk is runnable.
- The current scenario remains `PARTIAL`, not `READY`.
- Backend execution is synchronous; there is no fake frontend timer.
- Independent receiver observation and CIM validation remain unavailable.
- The scenario topology is not a full NMS.
- Cisco/multi-product and mixed-vendor fixtures validate renderer architecture
  only and do not fabricate support or telemetry.
- Production guidance is represented by the schema but is not treated as a
  verified production deployment.
- Cisco 100, Industry Studio, full Scenario Studio, broader transports,
  streaming execution, and Phase 5 are deferred.

## Recommendation for Phase 5

Authorize Phase 5 only after Phase 4 review. Preserve the manifest-first
architecture and narrow runtime admission policy. The next phase should build
on evidence-backed adapters and explicit readiness gates rather than promoting
architecture fixtures or optional metadata into support claims.
