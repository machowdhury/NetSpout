# NetSpout Phase 13A — Splunk Security Content Integration

## 1. Executive outcome

Phase 13A is **PARTIAL**. NetSpout now provides a useful metadata-first
Security Content Lab, selective Attack Data replay, conservative dependency
and telemetry analysis, ATT&CK relationship mapping, bounded detection
execution, and persisted validation provenance.

One reviewed upstream network detection completed an end-to-end positive and
negative validation in an isolated Splunk Enterprise 10.2 lab. Full Splunk
Security Content support is not claimed. Windows/endpoint, identity, and
additional live targets remain unvalidated, and the Phase 12F/13E live gates
could not be re-established because the required host ports were occupied by
an unrelated lab.

## 2. Starting HEAD

- Branch: `feature/figma-v3-unified-telemetry-lab`
- Verified local and remote starting HEAD:
  `5b1da66a15dd81eb8846ad88a4a905e6f37439b0`
- Starting tree: clean.
- Reported Phase 13 package, Docker, dashboard, Gate 12F, Gate 13E, and test
  baselines were treated as claims and checked where the current environment
  allowed.

## 3. Upstream repositories and pinned revisions

- Splunk Security Content, `develop`:
  `1b2142fdd2d1358b4ac6ad3dfc47e5e455e619e8`
- Splunk Attack Data, `master`:
  `4389fa7a4e74a7c083c0fbe448fa2c7c32378981`
- MITRE ATT&CK STIX Data, `master`:
  `6cda5ad8462c79e14fbb872f4e09059b18e0cfc4`
- Splunk contentctl, `main`, schema/tooling reference only:
  `e18df5c205929c4b7bfc00eaf4e0cc48150f0d9f`
- Splunk Attack Range, `develop`, architecture reference only:
  `fc9b9e719d8835da0bbb5c20d46c52a9778d64e2`

Security Content and Attack Data were shallow-cloned for metadata inspection.
Attack Data used `GIT_LFS_SKIP_SMUDGE=1`; its payload collection was not
downloaded. The contentctl Pydantic content models and authoritative upstream
YAML were inspected. NetSpout does not claim full contentctl semantic
validation or use Attack Range to execute attacks.

## 4. Integration architecture

`src/netspout_core/security_content_lab.py` is the canonical integration layer.
Generated mirrors serve the backend and Splunk App. It reuses:

- the existing Phase 13 source catalog for compatibility;
- `TelemetryDispatcher.emit_hec` for replay;
- `ReleaseCandidateConfiguration.execute_read_only_search` for Splunk search;
- Connection Center destinations, credentials, and index authorization;
- canonical catalog synchronization and package guardrails.

No second simulator, source registry, or Splunk client stack was created.

## 5. Catalog schema

`catalog/phase13a_splunk_security_content.json` records normalized upstream
IDs, repository revisions, paths, descriptions, categories, relationships,
hashes, SPL hashes, dependencies, licenses, and synchronization policy.

Actual inventory:

- 3,265 normalized Security Content items;
- 2,181 detections;
- 365 analytic stories;
- 317 data sources;
- 255 macros;
- 106 lookups;
- 41 baselines;
- 0 YAML parse failures;
- 23 duplicate Attack Data IDs, retained and quarantined;
- 858 authoritative Enterprise ATT&CK techniques.

The snapshot is offline and revision-pinned. Synchronization is explicit; no
scheduled external fetch runs by default.

## 6. Detection dependency model

The resolver records indexes, sourcetypes, fields, data models, macros,
lookups, KV Store, supporting apps, TAs, RBA, enrichment, commands, and time
scope. It combines authoritative data-source relationships with conservative
lexical SPL parsing. It explicitly states that this is not full SPL semantics.

2,024 of 2,181 detections have a resolved supported-subset dependency record.
157 remain `DEPENDENCY_UNRESOLVED`/`RESEARCH_REQUIRED`. Unresolved values are
never fabricated.

## 7. Attack Data metadata inventory

The snapshot contains 1,400 dataset manifests and 1,474 file records with
dataset IDs, MITRE mappings, environment, paths, format, source, sourcetype,
size, LFS SHA-256 where present, repository revision, and provenance.

Metadata-only synchronization is the default. Files with unknown size fail
closed for retrieval.

## 8. Compatibility engine

The engine keeps structural, runtime, Splunk, detection-validation, and
production-efficacy claims independent. Current results are:

- `MISSING_DATA_MODEL`: 1,042
- `MISSING_LOOKUP`: 45
- `MISSING_MACRO`: 936
- `REQUIRES_TRANSFORMATION`: 1
- `RESEARCH_REQUIRED`: 157
- structurally compatible native detections: 0

The one replay-capable Cisco detection does not promote the existing FTD
source contract; it remains replay evidence requiring transformation.
Production detection efficacy is `NOT_ESTABLISHED`.

## 9. Dataset replay implementation

Selective replay supports `.log`, `.json`, `.ndjson`, `.xml`, and `.csv`
incrementally. It enforces:

- pinned `media.githubusercontent.com` URLs and no redirects;
- path traversal rejection;
- known size and a 5 MiB maximum;
- 30-second download timeout;
- content-type rejection for HTML;
- SHA-256 integrity where supplied;
- owner-only temporary storage;
- 2,000-event maximum;
- cancellation, status, errors, cleanup, and bounded preview;
- immutable binding between retrieved bytes and selected dataset metadata;
- original event payload preservation, with NetSpout run metadata in HEC
  metadata fields.

Scripts, binaries, archives, and attack tooling are never executed.

## 10. Detection validation orchestration

Runtime SPL is allowlisted to the reviewed detection
`d36459b1-7901-401a-a67e-44426c15b168`. Execution requires:

- an authorized Connection Center destination and index;
- an explicit positive or negative expectation;
- reviewed macro expansion;
- run-ID and 15-minute time scoping;
- a 30-second search timeout and 500-result maximum;
- denial of write-capable and external-content SPL commands.

All other upstream SPL remains non-executable until reviewed. Evidence records
the upstream and executed SPL hashes, dataset/run identity, counts,
expectation, result, required fields, adaptations, and limitations.

## 11. MITRE ATT&CK coverage mapping

The machine matrix links technique → detections → data sources → NetSpout
compatibility → test data → execution → validation.

Measured relationships:

- 377 ATT&CK techniques referenced by Security Content;
- 2,879 detection-to-technique relationships;
- 1 technique with available replay telemetry;
- 366 techniques with associated test data;
- 1 technique with an allowlisted executable detection;
- 1 technique with a live-validated detection.

Content existence is not reported as defensive coverage.

## 12. Security Content Lab UI

The new `/security-content` route includes Overview, Detection Explorer,
Analytic Stories, Attack Datasets, Compatibility Matrix, MITRE Coverage,
Validation Runs, and Research Required views. Detection details show telemetry,
fields, macros, lookups, data models, TAs, MITRE mappings, missing
requirements, replay associations, validation evidence, and efficacy limits.
Advanced mode shows upstream SPL.

The browser journey passed and confirms that compatibility is not presented as
production efficacy.

## 13. Splunk App integration

The package adds a Security Content Lab navigation/view entry, reviewed macros,
and bounded Cisco Secure Firewall JSON field aliases. Heavy metadata
synchronization, downloads, replay, and simulation remain in the external
companion engine, not the search-head process.

Final package:

- lifecycle validation: PASS;
- size: 4.78 MiB;
- members: 790;
- SHA-256:
  `188a1b2de31412df73dcad80b9abe61f87bfdd237d141ef3204150eb1b487fc2`;
- AppInspect: NOT_TESTED.

## 14. Docker integration

The shared backend catalog and UI are copied into the existing standalone
image. A new isolated image reached healthy status without interrupting the
unrelated running containers. Selective retrieval, replay, fresh indexing,
search, positive control, and negative control passed. The disposable
container was removed after validation.

## 15. Security review

Tests cover invalid YAML, duplicate IDs, path traversal, unknown/oversized
files, unsafe indexes, write-capable SPL, unapproved detections, cancellation,
timeouts, missing dependencies, and evidence persistence.

The security review found one medium provenance issue: a caller could combine
one cached payload ID with another dataset path. Replay now derives the
expected cache ID from the selected pinned path and rejects mismatches; a
regression test passes.

No credentials, private keys, certificates, or attack payloads were added.
Runtime credentials remain environment/in-memory values. No deprecated or
custom cryptography was introduced; SHA-256 is used for integrity only.

The Docker Splunk certificate is image-generated and self-signed for the
loopback disposable lab. Production certificates must be checked with
`openssl x509 -text -noout -in <certificate_file>` for validity dates, key
strength, SHA-2 signature, issuer/subject, and chain.

## 16. Licensing and provenance

Security Content and Attack Data root licenses are Apache-2.0. PyYAML 6.0.3 is
MIT-licensed. ATT&CK data carries the MITRE repository terms and required 2026
copyright designation, reproduced in `THIRD_PARTY_NOTICES.md`.

Repository-level licensing does not establish rights for every external or
embedded dataset artifact. Dataset payloads remain reference-only pending
human review and are not redistributed.

## 17. Live Splunk validation

Validated detection:

- Cisco Secure Firewall — React Server Components RCE Attempt;
- Security Content revision: `1b2142f…`;
- Attack Data dataset: `f0aeed06-629e-4d1e-9dae-b4687c779668`;
- dataset SHA-256: `01c4370…6a`;
- sourcetype: `cisco:sfw:estreamer`;
- final run: `phase13a-positive-final`;
- fresh indexed events: 1;
- matched results: 1;
- status: `POSITIVE_CASE_VALIDATED`.

The SPL was adapted only to add authorized run/index/time scope, map documented
JSON fields, remove display-only time formatting, and expand the upstream
empty filter macro.

## 18. Positive and negative controls

- Positive: 1 fresh indexed event, 1 detection result, PASS.
- Negative: no matching run data, 0 results, `NEGATIVE_CASE_VALIDATED`.
- Required-field evidence included `EventType=IntrusionEvent`,
  `SignatureID/signature_id=65554`, destination, and sourcetype.

The machine-readable evidence is
`catalog/phase13a_validation_evidence.json`.

## 19. Regression

- Phase 13A focused backend/API/release tests: 46 passed.
- Full browser suite: 34 passed, 16 conditional skips.
- Frontend build: PASS; inherited bundle-size warning.
- Frontend lint: PASS; 11 inherited warnings.
- Canonical source/catalog mirror audit: PASS.
- Splunk App filesystem lifecycle: PASS.
- Standalone image build and health: PASS.
- Broad backend run without a compatible live Splunk lab: 599 passed,
  44 environment-dependent failures, 10 skipped, 77 subtests passed.

The failed broad tests were concentrated in live SNMP/gNMI/Splunk gates and
artifact paths, not Phase 13A focused tests. An unrelated `agentsec_splunk`
container occupied host ports 8000/8088 and exposed no 8089 management port,
so the established Phase 12F/13E topology could not be recreated without
interrupting unrelated work.

## 20. Protected artifacts

- Before: 649.
- After: 660.
- Additions: 11 Phase 13A canonical/mirrored catalog, coverage, and validation
  evidence files.
- Existing protected modifications/deletions: 0.
- Audit-time mutations: 0 in the direct final snapshot/status check.

Existing source maturity, five Cisco Golden references, Cisco 100 counts,
Phase 12 scenarios, and the two non-ready dashboards were not promoted.

## 21. Performance and resource efficiency

Attack Data was not bulk-downloaded. Synchronization used shallow metadata
clones, LFS pointer inspection, compact JSON, hashes, bounded file/event sizes,
bounded search execution, and reusable fixtures. The package remains below
its 5 MiB guardrail.

## 22. Known limitations

- SPL parsing is a conservative supported subset, not full semantics.
- Only one upstream detection is runtime-allowlisted and live-validated.
- Search export does not provide a durable search job ID.
- Archive formats and files above 5 MiB are unsupported.
- No Splunk Cloud runtime validation or AppInspect approval exists.
- No production efficacy, complete ATT&CK coverage, or authentic native FTD
  generation claim is made.

## 23. Unimplemented upstream coverage

2,180 detections remain unsupported or unresolved for runtime validation.
Data-model acceleration, most macros/lookups/TAs, KV Store, RBA, enrichment,
and arbitrary upstream commands are not provisioned automatically. Windows,
endpoint, and identity/authentication live validation targets remain future
work because compatible reviewed evidence and dependencies were not
established in this phase.

## 24. Release blockers

- Re-establish and pass Gate 12F and Gate 13E in their authorized disposable
  topology without conflicting host services.
- Add evidence-backed Windows/endpoint and identity/authentication validations.
- Complete human legal/IP/dataset redistribution review.
- Run Splunk AppInspect and any required Splunk Cloud vetting.
- Obtain owner approval for release/publication.

## 25. Recommended next phase

Phase 13B should add a small owner-approved validation set for endpoint and
identity telemetry, integrate supported contentctl validation where practical,
expand macro/lookup dependency packaging under explicit review, and rerun all
live Phase 12/13 gates in an isolated port-compatible environment.

No merge, tag, release, publication, image push, or production deployment was
performed.
