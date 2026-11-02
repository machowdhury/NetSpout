# Figma v3 Phase 2B — Extensibility Architecture Gate

Completed on 2026-10-06 on
`feature/figma-v3-unified-telemetry-lab`.

Accepted Phase 2 baseline: `676de802033dd96d58304da1b8da8392d7fa3e8e`.
Phase 3 was not started, and `main` was not merged.

## Result

Phase 2B passes the bounded architecture gate.

The Phase 2 trust catalog remains authoritative for telemetry contracts. A new
strict, declarative pack and composition layer can now describe extension
content without adding vendor or scenario branches to NetSpout Core. The layer
contains no plugin importer and executes no catalog-supplied code.

The production pack registry is intentionally empty. Architecture examples are
isolated under `tests/fixtures/packs`, labeled fixture-only, excluded from the
UI, and make no production support claim.

## Architecture assessment

Phase 2 already separated Native, Splunk, and NetSpout contracts and provided
strict provenance, evidence, verification, sourcetype authority, and
fail-closed behavior. It did not yet provide a declarative runtime composition
boundary.

The current execution path still contains legacy coupling:

- scenario names and topology selection are encoded in Core enums and Python
  branches;
- scenario execution calls vendor-specific formatters;
- some telemetry channels are emitted implicitly by runtime conditions;
- destination/index behavior and investigation SPL are inferred or embedded in
  several runtime modules; and
- evidence-stage models remain partly protocol-specific.

Phase 2B does not rewrite those working paths. It establishes the typed target
boundary that Phase 3 can consume incrementally.

## Changes made

Canonical implementation:

- `src/netspout_core/pack_contracts.py`
- `catalog/extension_packs.json`

Validation:

- `tests/test_phase2b_extensibility.py`
- `tests/fixtures/packs/phase2b_architecture_gate.json`

Integration:

- `src/netspout_core/catalog.py` loads the pack registry;
- `scripts/sync_core.py` packages the new canonical module and registry; and
- `scripts/verify_sources.py` enforces mirror parity for both.

Generated backend and Splunk runtime mirrors were refreshed from the canonical
files.

## Pack model

Five independently versioned pack kinds are supported:

- `VENDOR_PRODUCT`
- `PROTOCOL_TELEMETRY`
- `SCENARIO`
- `INVESTIGATION`
- `INDUSTRY`

A pack has an identity, semantic version, maturity, verification state,
dependencies, and typed resources. Resources can include evidence, source
contracts, Splunk integrations, generators, validators, transports,
destinations, integration recommendations, guided scenarios, investigations,
and industry associations.

Pack dependencies reject missing references and cycles. Resource identifiers
are globally unique within a registry. The Phase 2 `TelemetryCatalog` validator
is reused for pack-owned evidence, source contracts, sourcetype claims, and
Splunk integration relationships, avoiding a second trust system.

Implementation references are opaque metadata. The schema does not dynamically
import or execute them.

## Composition model

The responsibilities are separate:

`Source Contract + Generator + Enterprise State + Scenario + Transport +
Destination + Investigation Pack`

A guided scenario declares what happens, the participating sources, topology,
timeline, evidence, and learning flow. It contains no transport binding.

A composition binds each scenario source to:

- one compatible generator;
- one compatible, runnable transport;
- one destination that accepts that transport; and
- zero or more compatible validators.

Every scenario source must be bound exactly once. Unknown, incompatible,
research-required, unsupported, or unimplemented capabilities fail closed.
Tests compose the same unchanged scenario with Syslog/UDP and Syslog/TCP.

## Transport abstraction

`TransportCapability` separates the delivery component, wire protocol,
supported telemetry signals, source compatibility, implementation status,
verification, and evidence.

The fixture proves the model can represent HEC, Splunk S2S, Syslog TCP/UDP,
OTLP, SNMP, NetFlow, IPFIX, gNMI, and vendor API/webhook delivery without
changing scenario definitions. These declarations do not imply that every
transport is currently implemented.

OpenTelemetry terminology is explicit:

- OpenTelemetry Collector is a component;
- OTLP is a transport protocol; and
- logs, metrics, and traces are separate supported signals.

## Protocol/telemetry and mixed-vendor readiness

Protocol capabilities are not owned by a vendor pack. Vendor/product source
contracts reference compatible generators, validators, and transports from
protocol/telemetry packs.

Fixture tests prove:

- one scenario can reference three Cisco product identities and multiple
  telemetry channels;
- one scenario can reference Cisco, Palo Alto Networks, Microsoft, and AWS
  identities without vendor conditionals in the pack model;
- NetFlow and DNS evidence can corroborate one incident; and
- a scenario cannot claim corroboration when only one evidence source exists.

The identities are architecture fixtures only. No Cisco, Palo Alto, Microsoft,
AWS, flow, DNS, sourcetype, TA, CIM, or raw-event claim was added to the
production catalog.

## Guided scenario manifest

The model can drive a future guided UI and generated topology from:

- title, story, difficulty, duration, objectives, impact, and prerequisites;
- technologies, entities, nodes, zones, and relationships;
- telemetry and incident paths;
- runtime state keys;
- source manifest and expected evidence;
- investigation and integration references;
- troubleshooting, CIM validation, and production replication guidance;
- optional curated layout/artwork; and
- ordered lifecycle stages:
  `BASELINE → PRECURSOR → INCIDENT → IMPACT → DETECTION → RECOVERY`.

Scenario parameters are constrained to modeled values and cannot authorize
changes to verified telemetry structure.

## Custom-source readiness

The model supports:

`Import Sample → Analyze → Identify Stable Structure → Identify Variable
Values → Associate Evidence → Define Source Contract → Validate → Create
Custom Source Pack → Use in Scenario`

Lifecycle states are:

`DRAFT → SAMPLE_VERIFIED → CONTRACT_VERIFIED → SPLUNK_VERIFIED →
E2E_VALIDATED → READY`

Sample-derived sources require explicit human-review authority. AI-assisted
analysis is recorded separately and cannot establish vendor documentation.
The test fixture stops at `SAMPLE_VERIFIED`.

## Raw fidelity, TA, and CIM architecture

Every pack source has a strict raw-fidelity policy:

- preserve native raw structure;
- scenario parameters may change modeled values;
- structural mutation is forbidden;
- the Splunk integration owns normalization; and
- CIM validation occurs after ingestion.

Validators can declare the complete evidence chain:

`RAW_VERIFIED → SENT → RECEIVER_OBSERVED → SPLUNK_OBSERVED →
SOURCETYPE_VERIFIED → FIELDS_VERIFIED → CIM_VERIFIED`

Splunk integration recommendations use only:

- `REQUIRED`
- `RECOMMENDED`
- `NOT_REQUIRED`
- `RESEARCH_REQUIRED`

Every recommendation requires evidence, and positive recommendations require
an explicit integration whose supported-source relationship includes the
source. Product-name similarity is never used.

## Investigation-pack architecture

Investigation recipes explicitly classify SPL as:

- `PRODUCTION_PORTABLE`; or
- `NETSPOUT_SPECIFIC`.

Production-portable recipes cannot declare NetSpout-only fields.
NetSpout-specific recipes must declare the lab fields they depend on, such as
`netspout_run_id`. Recipes also carry source, field, CIM, and evidence
dependencies.

## Dynamic topology and visualization metadata

Scenario topology is declarative:

`Nodes + Zones + Relationships + Telemetry Paths + Incident Path + Runtime
State`

Reference integrity is validated across nodes, zones, sources, paths,
incidents, and timeline steps. A curated layout reference remains optional for
flagship experiences; ordinary scenarios do not require hand-authored SVGs.

## Cisco 100 readiness

The Cisco 100 library can be delivered as versioned vendor/product,
protocol/telemetry, scenario, investigation, and optional industry packs.
Adding scenarios becomes data registration and pack validation rather than 100
new Core switch branches.

This gate does not claim the scenarios are ready. Each future READY scenario
must still bring verified technologies, native contracts, Splunk relationships,
platform-correct validation, correlated evidence, investigations, and
production replication guidance.

## Network Security Analytics readiness

One incident can reference multiple telemetry sources and one scenario can
combine flow, DNS, firewall, endpoint, identity, host, application,
infrastructure, and OTel evidence. The flow-plus-DNS fixture explicitly
requires corroboration; flow records alone are not modeled as proof of an
attack.

Ordered state and modeled-value parameters support future baseline, precursor,
incident, impact, detection, and recovery behavior without changing verified
event structure.

## Industry readiness

Industry packs associate existing source and scenario IDs. They do not clone
source contracts. The fixture associates the same source identities with
Banking and Healthcare to prove many-to-many reuse.

The model is ready for the planned industry list, but Phase 2B adds no Industry
Studio, industry generators, speculative telemetry, or production industry
content.

## Extensibility tests

`tests/test_phase2b_extensibility.py` contains 16 tests covering:

- all five pack kinds;
- the existing Phase 2 catalog and empty production registry;
- Cisco multi-product composition;
- mixed-vendor composition without vendor branching;
- flow plus DNS corroboration;
- sanitized sample-derived custom sources;
- transport-independent scenarios;
- OTel Collector/OTLP terminology and signal coverage;
- raw fidelity and post-ingestion CIM;
- evidence-backed integration recommendations;
- SPL portability;
- guided topology and lifecycle metadata;
- reusable industry associations;
- research-required fail-closed behavior;
- duplicate, unknown, and cyclic references; and
- the no-execution schema boundary.

Together with Phase 2 catalog and targeted protocol regressions, 55/55 tests
passed. Existing datetime/Pydantic deprecation warnings and gRPC diagnostic
messages remain; they are not Phase 2B regressions.

## Docker validation

- `docker compose build splunk-netspout`: passed.
- `docker compose up -d --force-recreate`: passed.
- Splunk/NetSpout container: healthy.
- OTel Collector: running.
- standalone UI: HTTP 200.
- backend health: HTTP 200.
- catalog summary: HTTP 200.
- Splunk Web: HTTP 303 login redirect.
- HEC health: HTTP 200.
- authenticated Splunk REST/search: HTTP 200.

The existing obsolete Compose `version` warning, constant `linux/amd64`
platform warning, and reused-volume project-label warnings remain.

## Security application

- No credential, password, API token, private key, or certificate was added.
- New canonical code and fixtures contain no common credential, private-key,
  certificate, or provider-token patterns.
- No X.509 material was introduced, so expiration, key-strength, signature,
  and issuer checks are not applicable to the Phase 2B diff.
- No cryptographic algorithm or protocol policy was introduced.
- The gNMI negative TLS test emitted its expected bad-certificate handshake
  diagnostic and passed.
- Existing tracked demo credentials and local TLS-verification exceptions were
  not copied into pack data and remain Phase 0 defects.

## Regressions

No regression was found in the Phase 2 catalog, source mirrors, SNMP, gNMI,
Docker startup, UI/backend reachability, or Splunk connectivity.

## Unresolved Phase 0 defects

- Mode B/C/D dispatch calls a missing dispatcher method.
- Native SNMP remains incompatible with the Python 3.9 container path.
- Packaged gNMI protobuf runtime compatibility remains unresolved.
- Flow collection is stopped and not orchestrated.
- OTel acceptance is not yet proven as Splunk-indexed observation.
- Aggregate pipeline health remains too optimistic.
- Generation evidence lacks receiver, Splunk, and duplicate measurements.
- Sample parsing may treat YAML metadata as telemetry.
- The retained canvas still contains an in-browser simulation fallback.
- Existing tracked demo credentials remain outside the Phase 2B additions.
- Existing local Splunk/OTel paths disable TLS verification.

## Remaining limitations and decisions

- Phase 2B defines and validates declarations; it does not execute packs.
- Existing runtime scenario branches have not yet migrated to compositions.
- The production registry remains empty until individual packs have
  authoritative evidence.
- Pack signing, remote distribution, dynamic Python loading, and a generic
  plugin framework were intentionally excluded.
- Full import, Scenario Studio, topology rendering, integration readiness
  aggregation, and SPL cookbook UX remain future work.
- Protocol-specific evidence implementations can be unified behind the
  declared validation stages incrementally.

## Phase 3 recommendation

Phase 3 can safely proceed against the declarative contracts, provided it
consumes validated compositions incrementally and does not treat test fixtures,
legacy catalogs, or unimplemented transport declarations as supported runtime
content.

Phase 3 should not dynamically execute arbitrary pack references. It should use
an allow-listed runtime adapter registry, preserve the Phase 2 trust catalog as
the authority, and retain fail-closed behavior for research-required and
unsupported capabilities.
