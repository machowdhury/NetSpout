# Figma v3 Phase 3 — Unified Generation Experience

Completed on 2026-10-06 on
`feature/figma-v3-unified-telemetry-lab`.

Starting commit: `0832572` (accepted Phase 2B).
Ending implementation and evidence commit: `01637b9`.

`main` was not merged. No release was created. Phase 4 was not started.

## Result

Phase 3 passes the bounded Unified Generation Experience gate for the
capabilities that NetSpout can currently support truthfully.

The application now provides one catalog-driven workflow:

`CHOOSE → PREVIEW → CONFIGURE → RUN → OBSERVE → INVESTIGATE`

All four modes use the same backend composition service:

- Scenario
- Data Source
- Sourcetype / Event Family
- Single Event

The production registry deliberately exposes only one runnable source and one
runnable scenario. Existing catalog entries without a validated Phase 3 runtime
binding remain visible but fail closed. Phase 3 did not convert legacy samples,
test fixtures, or Phase 2B architecture examples into supported telemetry.

## Truth boundary

The Phase 2/2B assessment found no verified public raw vendor sample suitable
for promotion into a production generation path. The narrow admitted path is:

- source: `ietf-syslog-rfc5424`;
- native authority: IETF RFC 5424 structure;
- payload classification: `MODELED_PAYLOAD`;
- sourcetype: NetSpout-defined `netspout:rfc5424`;
- generator: allow-listed `generator-rfc5424-modeled`;
- transport: `transport-local-hec`;
- destination: `destination-local-docker-splunk`;
- scenario: `rfc5424-link-state-lifecycle`; and
- investigation: `investigate-rfc5424-run`.

All generated identities use reserved fictional values such as
`edge-router.example.invalid`. The UI labels the structure, modeled payload,
sourcetype authority, provenance, and current verification state independently.
The scenario remains `PARTIALLY_VERIFIED`; a verified source contract does not
promote the scenario pack itself to `VERIFIED`.

## Files changed

Canonical runtime and contracts:

- `src/netspout_core/unified_generation.py`
- `src/netspout_core/pack_contracts.py`
- `src/netspout_core/catalog.py`
- `catalog/extension_packs.json`
- `catalog/telemetry_catalog.json`

Backend and API:

- `backend/app/main.py`
- generated backend catalog/runtime mirrors

Frontend:

- `frontend/src/App.tsx`
- `frontend/src/index.css`
- `frontend/src/components/generation/GenerationLab.tsx`
- `frontend/src/components/generation/TopologyPreview.tsx`
- `frontend/src/lib/generationApi.ts`
- `frontend/src/types/generation.ts`

Validation and packaging:

- `tests/test_phase3_unified_generation.py`
- `frontend/tests/generation-workflow.spec.ts`
- `tests/test_phase2_catalog.py`
- `tests/test_phase2b_extensibility.py`
- `scripts/sync_core.py`
- `scripts/verify_sources.py`
- generated Splunk runtime and catalog mirrors
- fourteen Phase 3 screenshots under `docs/implementation/images`

## Architecture changes

`UnifiedGenerationService` consumes the validated Phase 2 catalog and Phase 2B
pack registry. It resolves declarations into an allow-listed runtime adapter;
pack metadata is never dynamically imported or executed.

The execution boundary remains:

`Source Contract + Generator + Enterprise State + Scenario + Transport +
Destination + Investigation Pack`

Scenario manifests describe behavior, topology, timeline, expected evidence,
and investigations. Runtime compositions bind sources to compatible generators,
transports, destinations, and validators. The frontend does not branch on
vendor, scenario, or sourcetype names.

The APIs are:

- `GET /api/generation/capabilities`
- `POST /api/generation/preview`
- `POST /api/generation/preflight`
- `POST /api/generation/runs`
- `GET /api/generation/runs/{run_id}`
- `POST /api/generation/runs/{run_id}/observe`
- `POST /api/generation/runs/{run_id}/investigate/{recipe_id}`

Invalid source, transport, destination, generator, or composition references
are rejected. Research-required and unsupported sources cannot preview or run.

## UI implementation

The existing dark-navigation/light-workspace shell, domain selector,
typography, compact density, status language, and global Simple/Advanced switch
are preserved.

The generation workspace contains:

- a four-mode selector and metadata-driven browser;
- guided scenario story, impact, simulation, and expected outcome;
- generated topology when valid metadata exists;
- source/generator/transport/destination preview;
- Splunk integration readiness;
- provenance-aware raw preview;
- runtime-backed configuration and preflight;
- run identity, phase, timeline, topology state, and event counts;
- distinct evidence-stage cards and per-source totals; and
- attached investigation recipes with explicit SPL portability.

Simple and Advanced modes render the same capability and preview objects.
Advanced mode reveals the Native, Splunk, and NetSpout contracts plus technical
bindings and transport details.

## Generation modes

### Scenario

The manifest-defined lifecycle emits six correlated modeled RFC 5424 events:

`BASELINE → PRECURSOR → INCIDENT → IMPACT → DETECTION → RECOVERY`

The scenario, source, generator, transport, destination, topology,
integrations, and investigation are resolved from catalog/pack metadata.

### Data Source

The source can run without a scenario. Count is honored and no scenario
identifier or background scenario is introduced.

### Sourcetype / Event Family

The NetSpout-defined sourcetype is searchable and retains its distinct
authority, source, provenance, integration, and generation controls.
A sourcetype label is not treated as proof of native vendor authenticity.

### Single Event

Single Event enforces a count of exactly one in request validation and runtime
execution. It produces no background scenario or unrelated event.

## Scenario workflow and topology

The guided summary comes from the scenario manifest. Missing values are not
invented. The Phase 3 scenario supplies valid story, impact, duration,
difficulty, source, expected evidence, timeline, topology, and investigation
metadata.

`TopologyPreview` renders neutral SVG primitives from:

`Zones + Nodes + Relationships + Telemetry Paths + Incident Path + Runtime State`

It has no product logos or per-scenario handcrafted SVG. Runtime state changes
alter node presentation. Scenarios without valid topology receive an explicit
unavailable state. A curated artwork/layout reference remains optional in the
pack contract but is not used here.

## Preview and raw fidelity

Preview shows the exact resolved binding and separates:

- Native Contract;
- Splunk Contract; and
- NetSpout Contract.

Raw preview identifies source, contract, provenance, transport, sourcetype
authority, phase, and modeled status. The RFC 5424 structure is validated, but
the modeled message is not presented as captured vendor data.

No event is rewritten to claim CIM compliance. The intended chain remains:

`Supported Raw Event → Transport → Splunk → Integration → Parsing/Extraction → CIM`

## Splunk integration readiness

Integration readiness is resolved only from explicit pack relationships and
evidence IDs. No product-name matching is used. The admitted path declares
NetSpout direct structured ingestion as `REQUIRED`, detected as a built-in lab
capability, and `LAB_ONLY`.

The UI supports the Phase 2B relationship states:

- `REQUIRED`
- `RECOMMENDED`
- `NOT_REQUIRED`
- `RESEARCH_REQUIRED`

No speculative TA, app, sourcetype, or CIM recommendation was added.

## Preflight

Preflight executes on the backend for the exact selected composition. It checks:

- composition and source contract validity;
- allow-listed generator availability;
- transport/source compatibility;
- destination/transport compatibility;
- destination reachability; and
- required integration readiness.

The current valid path returns `READY_WITH_WARNINGS` because index confirmation
occurs through post-send authenticated search rather than being assumed before
the run. `READY` is never derived from frontend state.

## Execution and evidence model

Runs retain separate evidence states:

- `GENERATED`
- `ENCODED_PUBLISHED`
- `SENT`
- `RECEIVER_OBSERVED`
- `NORMALIZED`
- `SPLUNK_DISPATCHED`
- `SPLUNK_OBSERVED`
- `SOURCETYPE_VERIFIED`
- `FIELDS_VERIFIED`
- `VALIDATED`

HEC HTTP acceptance proves dispatch, not indexing. The current HEC path reports
independent receiver observation and CIM normalization as `NOT_AVAILABLE`.
Authenticated Splunk search is required to promote `SPLUNK_OBSERVED` to
`PROVEN`.

Live Docker validation proved generated, sent, and indexed counts for:

- Scenario: 6;
- Data Source: 3;
- Sourcetype: 4; and
- Single Event: 1.

## Splunk observation and investigation

Observation performs an authenticated Splunk REST search for the run ID,
configured index, and sourcetype. A successful request with no result remains
pending; transport acceptance alone never marks observation proven.

The attached investigation recipe is labeled `NETSPOUT_SPECIFIC` because it
depends on `netspout_run_id`. The UI explains that it must be adapted for
production. `RUN IN SPLUNK` reports success only after Splunk returns a result.
The live guided investigation returned six results.

One defect was found during live validation: the declarative recipe omitted the
REST search-command prefix, so Splunk returned an HTTP error. The recipe was
corrected to valid REST-ready SPL, mirrors were regenerated, and the live test
then passed.

## Simple and Advanced behavior

Simple mode exposes only the decision and execution information needed for the
supported workflow. Advanced mode adds source contracts, bindings, provenance,
transport details, sourcetype authority, integration details, raw preview, and
technical limitations. Both modes use identical APIs and state.

## Security review

The Phase 3 diff was scanned for credential, provider-token, private-key,
certificate, email, and non-fictional URL patterns.

- No credential, password, API key, token, private key, certificate, customer
  identifier, or real environment URL was added.
- Runtime HEC tokens and Splunk search credentials are read from existing
  backend configuration/environment and are never returned by Phase 3 APIs.
- Preflight responses, errors, UI state, logs, and screenshots contain no
  secrets.
- No cryptographic implementation or TLS policy was added or weakened.
- No X.509 material was introduced, so certificate expiration, public-key
  strength, signature algorithm, and self-signed checks are not applicable to
  the Phase 3 diff.

These checks were required because Phase 3 invokes authenticated HEC and Splunk
search paths and renders their status in the browser. Existing tracked demo
credentials and local TLS exceptions were not copied into new declarations and
remain inherited Phase 0 defects.

## Privacy and provenance review

- New event values use reserved fictional domains and generated run IDs.
- No captured sample was copied, expanded, sanitized, or reclassified.
- No new Cisco/Splunk logo, artwork, certification, endorsement, or support
  claim was introduced.
- IETF structure, NetSpout-modeled values, Splunk contract, and sourcetype
  authority remain visibly distinct.
- Test fixtures and unsupported catalog records are not represented as
  production-supported generation.

## Exact tests executed

Backend/catalog/composition:

```text
PYTHONPATH=src:backend python3 -m unittest \
  tests/test_phase3_unified_generation.py \
  tests/test_phase2_catalog.py \
  tests/test_phase2b_extensibility.py

40 tests passed.
```

Targeted catalog, source-mirror, transport, SNMP, and gNMI regression:

```text
PYTHONPATH=src:backend python3 -m unittest \
  tests/test_phase3_unified_generation.py \
  tests/test_phase2_catalog.py \
  tests/test_phase2b_extensibility.py \
  tests/test_gate2_canonical.py \
  tests/test_gate3_catalog.py \
  tests/test_transport_safety.py \
  tests/test_netflow_v9_encoder.py \
  tests/test_ipfix_encoder.py \
  tests/test_native_flow_loopback.py \
  tests/test_gate12b_native_snmp.py \
  tests/test_gate12c_snmp_polling.py \
  tests/test_gate12d_snmp_splunk_e2e.py \
  tests/test_gate12f_snmp_productization.py \
  tests/test_gate13b_gnmi_core.py \
  tests/test_gate13c_gnmi_collector.py \
  tests/test_gate13d_gnmi_splunk_e2e.py

242 tests passed.
```

This run also passed the canonical source and generated-mirror audit. Historical
acceptance artifacts rewritten by the regression harness were restored and are
not part of the Phase 3 diff.

Frontend:

```text
npm run build
Passed. Production bundle: 705.58 kB (170.11 kB gzip).

npm run lint
Passed with 13 pre-existing warnings outside Phase 3 files.

npx playwright test
8 tests passed.

npx playwright test tests/generation-workflow.spec.ts
3 tests passed.

PLAYWRIGHT_BASE_URL=http://127.0.0.1:8081 \
PLAYWRIGHT_LIVE_GENERATION=1 \
npx playwright test tests/generation-workflow.spec.ts
3 tests passed against the rebuilt Docker application.
```

The 390×844 responsive assertion found no document-level horizontal overflow.

## Docker and Splunk validation

- `docker compose build splunk-netspout`: passed from repository state.
- `docker compose up -d --force-recreate`: passed.
- Splunk/NetSpout container: healthy.
- OTel Collector container: running.
- backend health: HTTP 200.
- generation capabilities API: HTTP 200.
- HEC health: HTTP 200.
- Splunk Web: HTTP 303 login redirect.
- authenticated run-observation search: passed for all four generation modes.
- authenticated investigation search: passed with six returned results.

The obsolete Compose `version`, constant `linux/amd64`, reused-volume label,
frontend chunk-size, npm `devdir`, datetime/Pydantic deprecation, and gRPC
diagnostic warnings remain non-Phase-3 defects/warnings.

## Screenshot inventory and review

All screenshots were captured from the rebuilt live Docker application:

1. `phase3-01-choose-scenario.png`
2. `phase3-02-scenario-preview.png`
3. `phase3-03-scenario-topology.png`
4. `phase3-04-configure.png`
5. `phase3-05-preflight.png`
6. `phase3-06-live-run.png`
7. `phase3-07-evidence-observe.png`
8. `phase3-08-investigate.png`
9. `phase3-09-data-source-mode.png`
10. `phase3-10-sourcetype-mode.png`
11. `phase3-11-single-event-mode.png`
12. `phase3-12-simple-mode.png`
13. `phase3-13-advanced-mode.png`
14. `phase3-14-unsupported-state.png`

Visual inspection confirmed:

- no document-level clipping or horizontal overflow at tested sizes;
- technical values remain readable at the existing compact enterprise density;
- status badges and hierarchy are consistent with the established shell;
- topology is neutral, manifest-driven, and free of product artwork;
- the Advanced capture exposes all three contract cards;
- the unsupported capture includes the selected record, reason, evidence link,
  and disabled Preview action;
- raw/run values are fictional or generated; and
- no credentials or private environment details are visible.

An overlapping vertical relationship label and the initially clipped
unsupported-state capture were corrected before the final inventory.

## Defects discovered

Fixed in Phase 3:

- Investigation SPL was not valid for the Splunk export REST endpoint until the
  explicit `search` command was added.
- Scenario verification initially inherited the verified source status instead
  of retaining the scenario pack's partial status.
- One topology edge label overlapped a node label.
- Live Playwright originally assumed a fixture run ID and was corrected to
  validate runtime UUIDs.

No new P0 or P1 regression was found.

## Inherited Phase 0 defects

Phase 3 does not claim these legacy issues are fixed:

- the legacy Mode B/C/D dispatcher calls a missing `dispatch_log_entry`;
- native SNMP remains incompatible with the Python 3.9 container path;
- packaged gNMI protobuf runtime compatibility remains unresolved;
- flow collection is stopped and not orchestrated;
- OTel acceptance is not yet generally proven as Splunk-indexed observation;
- aggregate pipeline health remains too optimistic;
- legacy generation lacks general receiver/Splunk/duplicate evidence;
- sample parsing may treat YAML metadata as telemetry;
- the legacy Scenario Builder retains an in-browser simulation fallback;
- tracked demo credentials remain in existing local deployment configuration;
  and
- existing local Splunk/OTel paths include TLS-verification exceptions.

The new unified workflow does not call the missing legacy dispatcher method and
does prove Splunk observation for its admitted HEC path.

## Remaining limitations

- Only the modeled RFC 5424 source and lifecycle scenario are runnable.
- Only local Docker Splunk over the declared HEC transport is admitted.
- HEC is a lab delivery path, not claimed as native syslog transport.
- Receiver observation is unavailable independently of HEC acceptance.
- No CIM mapping or normalization is claimed for the admitted sourcetype.
- Runs execute synchronously; the UI renders manifest phases and final runtime
  state but does not stream long-running phase transitions yet.
- The source-level Evidence panel provides runtime counts; a broader
  multi-source evidence drilldown awaits additional truthful runnable sources.
- Only one NetSpout-specific investigation recipe is populated.
- Remote Splunk, Splunk Cloud, Syslog, S2S, OTLP, SNMP, gNMI, NetFlow, and IPFIX
  remain unavailable in this workflow until runtime capability and evidence
  gates are satisfied.
- Cisco 100, Industry Studio, full Scenario Studio, sample import/AI analysis,
  bulk vendor content, and Phase 4 work remain deferred.

## Deferred features

- verified vendor/product content programs;
- production-portable investigation packs;
- independent receiver evidence adapters;
- post-ingestion field, sourcetype, and CIM validators;
- asynchronous run streaming and cancellation;
- broader destination management in Connection Center;
- additional data-driven topology node treatments and curated overrides; and
- multi-source integration-readiness aggregation once multiple production
  compositions exist.

## Recommendation

Phase 3 is safe to accept for the narrow, explicitly modeled RFC 5424/HEC/local
Splunk capability.

The next phase should proceed only after separate authorization. It must keep
the same fail-closed catalog boundary, add capabilities incrementally with
authoritative evidence, and must not interpret this Phase 3 UI foundation as
approval to populate Cisco 100, speculative vendor telemetry, or unsupported
transports.
