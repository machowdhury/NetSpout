# Figma v3 Phase 2 — Catalog and Provenance

Completed on 2026-10-05 on `feature/figma-v3-unified-telemetry-lab`.

## Result

Phase 2 adds a strict, backend-owned telemetry catalog that separates:

- the Native Contract produced by the technology;
- the Splunk Contract used for ingestion and interpretation; and
- the NetSpout Contract used to model and validate the source.

The catalog fails closed when provenance, verification, relationships, or
sourcetype authority are invalid. The Phase 1 shell now renders backend-driven
Provenance and Splunk Integrations workspaces in Simple and Advanced modes.

## Commits

- `ba94eb8` — `feat(catalog): add authoritative telemetry contracts`
- `0ca3eeb` — `fix(catalog): bind OTLP support to implemented generator`
- `63f172e` — `feat(ui): add catalog provenance workspace`
- `ec0a8ae` — `build(ui): package catalog workspace`
- `2f79130` — `test(catalog): validate live provenance workspace`
- `28e81ca` — `fix(catalog): retire unverified integration fixtures`
- `c7bf731` — `chore(release): enforce complete source mirror parity`

## Catalog architecture

The canonical data is `catalog/telemetry_catalog.json`. Strict models and
cross-record guardrails live in `src/netspout_core/catalog_contracts.py`.

Normalized entities:

- evidence references;
- telemetry sources;
- Splunk integrations;
- Native, Splunk, and NetSpout contracts;
- sourcetype authority claims;
- CIM claims;
- scenario source manifests; and
- production versus NetSpout-only SPL field scope.

The source model includes `applicable_industries` as a many-valued association.
It is intentionally empty in Phase 2. Future industry work can associate one
source with multiple industries without cloning its telemetry contract.

The legacy vendor and sourcetype catalogs remain available for compatibility,
but the Phase 2 UI does not infer verification from them. The previous
hard-coded vendor add-on modal was retired because its CIM, sourcetype, and
support claims lacked per-record evidence. Its canvas entry point now directs
users to the authoritative backend catalog.

## Catalog inventory

Sources: 10

Verification states:

- VERIFIED: 1
- PARTIALLY_VERIFIED: 7
- RESEARCH_REQUIRED: 1
- UNSUPPORTED: 1

Provenance occurrences:

- STANDARD_DOCUMENTED: 6
- MODELED_VALUE: 6
- MODELED_PAYLOAD: 2
- NETSPOUT_SCHEMA: 2
- SPLUNK_DOCUMENTED: 2
- VENDOR_DOCUMENTED: 1
- RESEARCH_REQUIRED: 1
- UNSUPPORTED_TELEMETRY: 1

Domain associations:

- NetOps: 6
- SecOps: 5
- ITOps: 3
- Observability: 2
- Agentic AI: 1
- Supply Chain: 1

Domain counts overlap because one legitimate source may serve multiple
operational perspectives.

Evidence references: 14

Source manifests: 3

- `openconfig_mdt_streaming`
- `service_provider_cisco`
- `pure_cisco_enterprise`

## Splunk integrations

Four integration records are represented:

- Splunk TCP/UDP Network Input — supported native input;
- Splunk Distribution of the OpenTelemetry Collector HEC exporter — supported
  collector integration;
- Splunkbase app 1467 — verified identity but explicitly DEPRECATED; and
- NetSpout direct structured ingestion — explicitly LAB_ONLY.

Splunkbase app 1467 was found to be deprecated in favor of app 7538. The
catalog therefore does not recommend app 1467 as current. It records only the
`cisco:ios` sourcetype supported by the cited evidence and does not promote
`cisco:ios:syslog` as official.

No CIM mapping is promoted because the current evidence set is insufficient
for a strict per-record claim.

## NetSpout-defined schemas

Two sourcetypes are explicitly labeled `NETSPOUT-DEFINED`:

- `openconfig:gnmi:telemetry`
- `netspout:agentic:activity`

They cannot pass schema validation as `SPLUNK_DOCUMENTED` without Splunk
evidence. Conversely, official sourcetype claims cannot pass without evidence
classified as `SPLUNK_DOCUMENTED`.

## Research-required and unsupported

- Windows Security auditing is `RESEARCH_REQUIRED`. Event identifiers,
  integration, sourcetype, CIM, and scenario mapping are not promoted.
- Supply Chain remains `UNSUPPORTED`. No platform, vendor schema, sourcetype,
  or integration is generated.

## API

Added:

- `GET /api/catalog/telemetry`
- `GET /api/catalog/summary`
- `GET /api/catalog/sources`
- `GET /api/catalog/sources/{source_id}`
- `GET /api/catalog/integrations`
- `GET /api/catalog/integrations/{integration_id}`
- `GET /api/catalog/evidence`
- `GET /api/catalog/source-manifests`

The existing `/api/catalog/provenance` endpoint remains as a legacy
compatibility surface.

## UI

The Provenance workspace answers:

- what the source is;
- where each contract came from;
- how it reaches Splunk;
- what Splunk calls it;
- whether NetSpout can generate it; and
- which evidence supports the claim.

Advanced mode exposes all three contracts, evidence, source relationships,
transports, structural and modeled fields, generation modes, runtime state,
maturity, scenarios, limitations, and SPL field portability.

The Splunk Integrations workspace distinguishes native inputs, collectors,
Splunkbase add-ons, and lab-only ingestion. Sourcetypes are visibly labeled
`SPLUNK-DOCUMENTED` or `NETSPOUT-DEFINED`.

## Validation

Catalog and backend:

- canonical catalog validator: passed;
- single-source and catalog-mirror audit: passed;
- Phase 2, Gate 3, and Gate 5 targeted set: 43/43 passed;
- strict tests cover invalid provenance, unsupported and research-required
  fail-closed behavior, duplicate identity, invalid official sourcetypes,
  NetSpout-defined schemas, integration relationships, source manifests,
  filters, summaries, industry associations, and legacy modal retirement.

Frontend:

- lint: passed with 13 pre-existing warnings;
- TypeScript/Vite build: passed;
- Playwright: 5/5 fixture-driven UI tests passed;
- live Docker catalog screenshot test: 1/1 passed;
- final bundle: approximately 777 KB before gzip, with the existing
  large-chunk warning.

Protocol regression:

- targeted SNMP and gNMI suites: 26/26 passed after Splunk completed startup;
- the first immediate post-recreate SNMP attempt failed four live-observation
  assertions while Splunk Web was still resetting connections. The identical
  suite passed after readiness, confirming startup timing rather than a code
  regression.

Docker Desktop:

- clean image build: passed;
- Compose recreate: passed;
- Splunk/NetSpout container: healthy;
- OTel Collector: running;
- standalone UI: HTTP 200;
- backend health: HTTP 200;
- catalog summary: HTTP 200, 10 sources;
- source API: HTTP 200, 10 records;
- integration API: HTTP 200, 4 records;
- evidence API: HTTP 200, 14 records;
- source manifest API: HTTP 200, 3 records;
- Splunk Web: HTTP 303 login redirect;
- HEC health: HTTP 200;
- authenticated REST/search: HTTP 200.

## Security application

- No credential, password, token, private key, or certificate was added.
- Frontend and authoritative catalog scans found no common credential,
  private-key, or certificate patterns.
- Evidence records contain public documentation links and repository-relative
  references only.
- No X.509 certificate was introduced, so expiration, key-strength, signature,
  and self-signed checks were not applicable.
- No cryptographic algorithm or protocol policy was introduced or changed.
- Existing local TLS-verification exceptions remain documented Phase 0 defects.

## Regressions

No Phase 2 regression remains in the targeted catalog, UI, SNMP, or gNMI
coverage.

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
- Existing tracked demo credentials remain outside the new frontend/catalog.
- Existing local Splunk/OTel paths disable TLS verification.

## Newly discovered limitations

- Legacy `vendors.json`, `sourcetypes.json`, and
  `telemetry_sources.json` contain broader historical claims than the strict
  catalog. They remain compatibility data and must be migrated or individually
  researched before being admitted to the authoritative catalog.
- Docker continues to report the obsolete Compose `version` field, reused
  volume project labels, and the constant `linux/amd64` platform warning.
- The frontend remains a single large bundle.

Resolved during Phase 2:

- the deprecated app 1467 status and unsupported official-sourcetype inference;
- the hard-coded legacy add-on UI;
- incomplete source-mirror auditing for `catalog_contracts.py`,
  `embedded_pipelines.py`, and `generator_modes.py`; and
- canonical/package drift in `embedded_pipelines.py`.

## Phase 3 readiness

The strict catalog, query APIs, source manifests, authority labels, provenance
UI, and source-to-integration relationships are ready to support Phase 3
generation UX. Phase 3 has not started.

## Recovery

- Starting commit: `b9521c131deffcd4d1a9f4f5fc9900486de58492`
- Immutable backup tag: `pre-figma-v3-implementation`
