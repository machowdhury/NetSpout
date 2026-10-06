# NetSpout Figma v3 — Phase 6 Scenario Studio

## Scope and starting-head gate

- Branch: `feature/figma-v3-unified-telemetry-lab`
- Exact Phase 6 baseline: `177ad9b95ffffea648c64427064c38f82930d409`
- Accepted Phase 5 implementation: `d5286325f46c4835cc57af72aefb906c79ee4f44`
- Phase 6 implementation commit:
  `1042c47e1265965f5d378794a6d55be256a0c1b6`
- Report finalization: documentation-only successor commit
- Phase 7: not started

Before any Phase 6 edit, the branch was fetched and the worktree was clean.
Local HEAD, `origin/feature/figma-v3-unified-telemetry-lab`, and their merge
base were all `177ad9b95ffffea648c64427064c38f82930d409`.
`d5286325f46c4835cc57af72aefb906c79ee4f44` is an ancestor of that commit.
The only intervening commit was:

```text
177ad9b95ffffea648c64427064c38f82930d409 docs: finalize Phase 5 native runtime evidence
```

The accepted Phase 5 code and report were present at the actual baseline. No
history was reset or rewritten.

## Outcome

Phase 6 adds the first production-oriented Scenario Studio and Custom Source
Builder. A scenario can be composed from verified catalog sources, cloned
from an existing scenario while preserving contract fingerprints, or built
from a locally analyzed sanitized sample. Studio packs compile into the
existing Phase 2B pack/runtime model; no NetSpout Core edit is required for
each authored scenario.

The implemented workflow is:

```text
Create → Choose/Import → Environment → State → Timeline → Telemetry
       → Investigation → Preview → Validate → Save → Run → Observe
```

Studio-created content begins as `DRAFT`. Saving never implies `READY`,
vendor verification, Splunk validation, CIM mapping, or redistribution
permission.

## Files changed

The implementation changes 51 files, including this report:

- Canonical Studio/runtime:
  `src/netspout_core/scenario_studio.py`, `unified_generation.py`,
  `native_runtime.py`, and `gnmi/state_store.py`.
- Generated runtime mirrors: corresponding modules under `backend/app`,
  `netspout/bin`, and `netspout/bin/netspout_core`; `scripts/sync_core.py`
  now includes the Studio module.
- API and deployment: `backend/app/main.py`, `docker-compose.yml`, and
  `docker-compose.standalone.yml`.
- Frontend: `ScenarioStudio.tsx`, Studio API/types, application navigation,
  shell integration, styles, and a narrowed inherited Playwright selector.
- Verification: two Python suites, the Phase 6 Playwright suite, and 20
  manually inspected screenshots under `docs/implementation/images`.

## Studio architecture

`ScenarioStudioService` is the application boundary for:

- home/catalog capabilities and the three distinct creation paths;
- local sample analysis and custom-source review;
- draft creation and protected cloning;
- fail-closed validation and maturity calculation;
- atomic private persistence, reload, replacement, and deletion;
- compilation to existing scenario, source, guided-lab, and runtime models;
- private generator registration and registration cleanup;
- run and export gates.

The FastAPI surface is under `/api/studio` and provides sample analysis,
custom-source validation, draft creation, pack CRUD, validation, export-gate,
and run operations. CORS is restricted to loopback development origins.

The React Studio is one guided authoring surface rather than a replacement
for existing advanced tooling. It reuses the Phase 4 topology renderer and
guided-lab presentation, and calls the Phase 5 unified generation runtime.

## Creation paths and contract protection

The UI and service keep these paths separate:

1. **Existing verified sources** — choose only evidence-backed catalog
   bindings.
2. **Import sanitized sample** — acknowledge authorization, scan locally,
   review classification/provenance, then create a private custom source.
3. **Clone existing scenario** — copy modeled state while retaining immutable
   source-contract fingerprints.

Fields use explicit semantics: `STRUCTURAL`, `MODELED`, `CORRELATION`,
`DERIVED`, `SENSITIVE`, or `UNKNOWN`. Classification authority is also
recorded. An unexplained field remains unknown; a user description is
`USER_PROVIDED`, not vendor verified. Structural fields cannot be exposed as
runtime scenario parameters.

The contract review keeps three layers separate:

- **Native contract** — the emitted record shape.
- **Splunk contract** — ingestion/parsing only when established.
- **NetSpout contract** — deterministic generation and modeled inputs.

Unknown sourcetypes report research required. A private custom sourcetype is
explicitly `NETSPOUT_DEFINED`; it is never represented as official Splunk
metadata. Missing integration and CIM evidence remain `NOT_ESTABLISHED`.
Raw imported telemetry is not rewritten to claim CIM compliance.

## Custom Source architecture

An approved custom-source draft contains reviewed field definitions, native
format/record boundaries, provenance, privacy status, redistribution status,
contract status, and a sanitized template. Compilation creates an existing
Pack-compatible telemetry source plus a narrowly scoped deterministic
template generator and validator.

Custom source execution is deliberately limited:

- one reviewed private source per custom draft;
- only modeled/correlation/derived values may vary;
- structural literals remain fixed;
- unsupported formats, generators, transports, or mixed custom-source
  combinations fail closed;
- imported sources are never assigned `VENDOR_VERIFIED` or `SYNTHETIC`.

This is deterministic authoring infrastructure, not AI auto-authoring.
Future assistance can enter only as suggested/unverified metadata.

## Privacy and temporary-import model

Imported samples are analyzed locally. They are not sent to an external
service, logged, stored in browser persistence, or included in a report.
The frontend holds an approved sample only in an in-memory temporary
reference and clears it after draft construction.

`SensitiveDataScanner` detects likely hostnames, IP addresses, usernames,
email addresses, UUIDs, credential/token/password/API-key shapes, MAC
addresses, domains, serial numbers, tenant/account/customer identifiers, and
certificate/private-key material. Findings contain category and location,
but the preview is always `[REDACTED]`; credential-like values are not echoed.
Detected sensitive or environment-specific input blocks contract analysis
pending explicit review. Unknown input is not silently sanitized.

The scanner is a single service boundary so a future reproducible sanitizer
can replace or extend it without distributing ad hoc transformations through
the frontend. No reversible original-to-sanitized mapping is persisted.

## Provenance and redistribution

Privacy, provenance, and redistribution are independent fields.

Supported provenance includes customer/lab sanitized samples, public samples,
vendor-documented material, unknown origin, and NetSpout-generated material.
Imported content does not receive vendor verification automatically.

Supported redistribution states are `PRIVATE`, `LOCAL_ONLY`,
`REDISTRIBUTION_UNKNOWN`, and `REDISTRIBUTION_PERMITTED`. Imported custom
sources default to private/local. Public export is blocked unless privacy,
provenance, redistribution, validation, and contract requirements are met.
Phase 6 implements the gate, not public-pack publication.

## Environment, state, topology, and timeline

The environment builder uses Phase 4 entities and semantic relationships.
Layout coordinates are optional hints; entity and relationship metadata
remain authoritative. Existing entities receive automatic initial placement
and can be rearranged without requiring handcrafted SVG.

State values are constrained by selected generator/source capabilities rather
than accepted as an unrestricted property bag. Baselines and transitions
contain modeled values such as interface status/loss or application latency.
Timeline transitions alter shared enterprise state; source adapters then
derive telemetry:

```text
Enterprise state transition → verified generator → native telemetry
```

Phase 5's state store now separates Studio scenario identity from the
evidence-backed state-profile identity. This lets a Studio-authored SNMP plus
gNMI scenario retain its own scenario/run identity while both protocols read
the same verified state and simulation clock. Deleting or replacing a private
pack unregisters its runtime definitions.

## Parameters and correlation

Parameters support type, default, units, description, numeric bounds, and
enumerations. Invalid defaults, values outside bounds, invalid enums, and
attempts to parameterize structural fields fail validation.

Correlation mappings relate device, interface, user, host, application,
session, flow, or transaction identities to source-specific fields. Sources
do not need identical field names. One transition can drive multiple selected
sources from the same state.

## Investigation Builder

Investigation steps carry an objective, question, SPL, expected finding,
explanation, evidence dependency, and portability classification. The
existing `PRODUCTION_PORTABLE` versus `NETSPOUT_SPECIFIC` distinction is
preserved. Validation records execution and expected-result evidence
separately; parsing alone does not establish Splunk validation. Expected
findings support machine-checkable or human-readable forms.

## Persistence and private-pack handling

Studio packs are strict JSON models serialized atomically under
`NETSPOUT_STUDIO_DIR` (defaulting to controlled local application storage).
The directory is mode `0700` and files are mode `0600`. Loads reject corrupt
or invalid packs and retain diagnostics instead of partially registering
them. Save/reload preserves topology, layout hints, timeline, sources,
parameters, investigations, provenance, and validation state.

Private pack storage is outside the repository and is not automatically
Git-tracked. Docker uses `/opt/splunk/var/lib/netspout/studio`. The backend
API port is loopback-bound. Standalone Compose no longer contains a default
Splunk password or HEC token; operators must provide both through the
environment.

## Validation and maturity

Validation checks entity and relationship references, source contracts,
generator availability, transport support, timeline/state compatibility,
parameter constraints, correlation mappings, privacy, provenance,
redistribution, Splunk relationships, and investigation dependencies.
Unsupported transports, missing sources, unknown generators, invalid fields,
and unresolved sensitive input cannot become ready.

The lifecycle is:

```text
DRAFT → STRUCTURE_VALIDATED → SOURCE_VALIDATED → RUNTIME_VALIDATED
      → SPLUNK_VALIDATED → READY
```

Appropriate drafts may run locally, but remain prominently labeled. `READY`
is an evidence-derived maturity state, not a save action.

## Test fixtures

All new fixtures are visibly synthetic and use `.example`/`.invalid`, RFC
documentation addresses, locally administered MAC addresses, fictional
identities, deterministic fictional UUIDs, and nonfunctional credential
shapes. Scanner tests intentionally contain certificate/private-key marker
text only to prove blocking and redaction; no functional credential,
certificate, private key, token, or original-value mapping is committed.

## Automated verification

Final focused verification:

- Phase 6 domain/API plus Phase 5 native runtime:
  **25 passed, 5 warnings, 9 subtests passed**.
- Earlier expanded Phase 6/runtime regression:
  **55 passed, 5 warnings, 9 subtests passed**.
- Full frontend Playwright suite:
  **19 passed, 2 skipped**.
- Focused Phase 6 Playwright:
  **3 passed**.
- Frontend production build: passed.
- Frontend lint: passed with inherited warnings and no Phase 6 warning or
  error.
- Canonical/runtime mirrors: byte comparison passed.
- `git diff --check`: passed.

The final broad stable-stack Python run intentionally excluded four
resource-heavy live suites and completed with **428 passed, 1 skipped, 67
subtests passed, and 4 failures**. All four failures are inherited Gate 12F
SNMP productization checks that assume live Splunk/preflight observations:
two native SNMP scorecards, preflight readiness, and one controlled-failure
observation. They do not reproduce in the required Phase 6 Docker SNMP/gNMI
journey, which passed against the rebuilt healthy image. This report does not
claim a clean full-repository Python run.

## Live Docker journeys

The final rebuilt root stack was healthy. Required journeys produced:

1. Existing source → save/reload → run → Splunk:
   run `2cce27d6-46fd-4c32-84f9-108a8cbe4521`, `OBSERVED`, 3 records,
   reload preserved.
2. Clone → modeled-state change → SNMP plus gNMI:
   run `dc54d103-e918-41b6-a9cf-b5280d452a9d`, `OBSERVED`, unchanged
   contract fingerprint, shared clock, 326 SNMP and 212 gNMI observations.
3. Synthetic custom source → private pack → run:
   run `26e4ff5a-b473-43c3-812a-e3ca402ec01c`, `OBSERVED`, 3 records,
   `LAB SAMPLE — SANITIZED`, not vendor verified.
4. Guided correlated scenario:
   the same SNMP/gNMI run retained shared-state consistency through Guided
   Lab and Splunk observation.
5. Sensitive synthetic sample:
   import blocked with 2 fully redacted findings and no secret-shaped value
   echoed.

## Screenshots and manual inspection

The following committed screenshots were manually reviewed for layout,
contrast, retained scrolling, truthful status, and sensitive-fixture leakage:

1. `phase6-01-studio-home.png`
2. `phase6-02-existing-source-selection.png`
3. `phase6-03-clone-scenario.png`
4. `phase6-04-import-sample.png`
5. `phase6-05-sensitive-data-warning.png`
6. `phase6-06-field-classification.png`
7. `phase6-07-contract-builder.png`
8. `phase6-08-environment-builder.png`
9. `phase6-09-topology-builder.png`
10. `phase6-10-state-builder.png`
11. `phase6-11-timeline-builder.png`
12. `phase6-12-telemetry-configuration.png`
13. `phase6-13-scenario-parameters.png`
14. `phase6-14-investigation-builder.png`
15. `phase6-15-preview.png`
16. `phase6-16-guided-lab-preview.png`
17. `phase6-17-validation.png`
18. `phase6-18-save-private-pack.png`
19. `phase6-19-custom-live-run.png`
20. `phase6-20-splunk-validation.png`

The sensitive-data warning shows only `[REDACTED]`. No sample credential value
appears in a screenshot.

## Security findings

- No imported sample is transmitted externally or retained in browser
  persistence.
- No hardcoded credential was added. Existing standalone defaults were
  removed and replaced with required environment variables.
- No certificate or private key was added. Certificate/key detection markers
  are scanner rules and explicitly test-only fixtures.
- No insecure/deprecated cryptographic algorithm or custom cryptography was
  introduced. Fingerprints use SHA-256 only for deterministic integrity
  comparison, not password storage or authentication.
- Private files use restrictive permissions and atomic replacement.
- No original-sensitive-value mapping, real customer identifier, or
  functional secret is present in committed artifacts.

## Limitations and deferred functionality

- Phase 6 does not perform arbitrary sample sanitization; it detects, blocks,
  and supports reviewed sanitized input.
- Public-pack publication is not implemented; only the stronger export gate
  is architected.
- Custom-source runtime support is intentionally narrow and deterministic.
- Connected Splunk evidence is needed to advance Splunk maturity.
- Syslog TCP and OTel remain truthfully partial as inherited from Phase 5.
- Phase 6 does not add transports, AI scenario generation, Cisco 100, or the
  16-industry Studio.
- The four live-assumption Gate 12F failures above remain inherited defects.
  No new P0/P1 Phase 6 issue was found.

## Recommendation for Phase 7

Authorize Phase 7 only after deciding whether the inherited Gate 12F
live-test assumptions should be isolated as environment-gated acceptance
tests or repaired to provision their own observation dependencies. A future
phase can then build on the Studio's validated private-pack boundary and
public-pack gate without weakening privacy, provenance, contract, or runtime
evidence requirements.

Phase 6 is complete. Wait for explicit authorization before beginning any
Phase 7 work.
