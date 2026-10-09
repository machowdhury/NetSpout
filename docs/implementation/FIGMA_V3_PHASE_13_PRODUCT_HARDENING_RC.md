# NetSpout Phase 13 — Product Hardening Release Candidate

## 1. Executive result

Phase 13 engineering acceptance is **PASS**. NetSpout now has two tested
distribution modes: an installable Splunk App plus external telemetry engine,
and a clean-room Docker Lab. Both use the same canonical scenario, source,
generation, investigation, and dashboard contracts.

This is a V1.0 release candidate, not a V1.0 release. Publication remains
blocked on human legal/IP/licensing review, owner authorization, and Splunk
AppInspect/Splunk Cloud vetting where those claims are desired.

## 2. Starting HEAD

- Branch: `feature/figma-v3-unified-telemetry-lab`
- Local and remote starting HEAD:
  `a369f454bcbbdae15602c43df69e3df368e22b01`
- Ancestry: local HEAD, remote HEAD, and merge base were identical before work.
- Starting tree: clean.
- Phase 11B and Phase 12 reports, deployment files, manifests, installation
  documentation, and protected roots were inspected before implementation.

## 3. Packaging architecture

Canonical behavior remains in `src/netspout_core`. `scripts/sync_core.py`
produces the backend and Splunk-package mirrors, and `scripts/verify_sources.py`
verifies byte identity. Deployment adapters provide:

- Splunk App: navigation, packaged web assets, catalogs, dashboard content,
  and integration guidance. The external engine is not embedded as privileged
  search-head code.
- Docker Lab: Splunk Enterprise 10.2, the same external engine and web client,
  OpenTelemetry collector, GoFlow2, and the bounded flow forwarder.

Container images are version-and-digest pinned. Administrative and collector
ports bind to loopback. Persistent Splunk and flow data use named volumes.
No proprietary Splunk binary is stored in the repository or `.spl` archive.

## 4. Splunk App implementation

Artifact: `netspout.spl`

The package is Splunk-integrated, not fully native. Splunk Web provides the
packaged navigation and existing views; the Phase 13 source catalog, setup
wizard, Scenario Studio, and Dashboard Studio are served by the required
external companion engine UI.

- SHA-256:
  `05f3fe0c993b2c3eb537fcafea2c16077e100cc0b0cbfb7b9961c0b4ca8352d2`
- Manifest: `netspout.spl.manifest.json`
- Archive root: `netspout/`
- Members: 780
- Size: approximately 2.12 MiB
- Reproducible: two final builds produced the same SHA-256.
- Runtime `local/` configuration is excluded.

Filesystem lifecycle checks passed for safe extraction, layout, clean install,
single root, upgrade preserving `local/`, removal, and reinstall. A live
Splunk Enterprise 10.2 instance also passed app visibility, package upgrade,
`local/inputs.conf` checksum preservation, removal, clean reinstall, and
post-install visibility.

AppInspect was unavailable and is **NOT_TESTED**. No Splunkbase or Splunk
Cloud approval is claimed.

Evidence:

- `.artifacts/phase13-current/installation/splunk-app-installation.json`
- `.artifacts/phase13-current/installation/splunk-live-upgrade.json`
- `.artifacts/phase13-current/installation/splunk-live-removal-reinstall.json`
- `.artifacts/phase13-current/installation/exact-final-live-validation.json`
- `.artifacts/phase13-current/release/reproducibility.json`

## 5. Docker implementation

The supported command is:

```bash
cp .env.example .env
# Supply unique SPLUNK_PASSWORD and SPLUNK_HEC_TOKEN values.
docker compose up -d --build --wait
```

The clean-room test created unique volumes, built without developer volumes,
reached full health in 90 seconds, stopped and restarted in 67 seconds,
preserved configuration and five indexed scenario events, and then removed
all clean-room containers, network, and volumes safely.

The initial clean-room attempt exposed a first-run volume ownership defect.
The final image preserves the upstream non-root `ansible` bootstrap account,
uses the upstream ownership initialization, starts the external engine only
after Splunk management readiness, and health-checks both HEC and the engine.

Evidence:

- `.artifacts/phase13-current/clean-room/startup-metrics.json`
- `.artifacts/phase13-current/clean-room/restart-metrics.json`
- `.artifacts/phase13-current/clean-room/persistence-validation.json`
- `.artifacts/phase13-current/clean-room/reset-validation.json`

## 6. Splunk Cloud compatibility

- Splunk Enterprise 10.2: **PASS** in the disposable Docker environment.
- Docker-bundled Splunk Enterprise: **PASS**.
- Splunk Cloud Platform: **PARTIAL — architectural target only**.

For Splunk Cloud, the engine remains external. An owner must provide approved
HEC ingress, search API connectivity, least-privilege authentication, allowed
indexes, and any required app-vetting process. Arbitrary server-side execution
is not assumed. No Splunk Cloud certification is claimed.

## 7. Security Event Source Catalog

Canonical machine-readable matrix:
`catalog/phase13_security_source_coverage.json`

Human-readable matrix:
`docs/SECURITY_SOURCE_COVERAGE.md`

The audit contains 33 source families:

- 9 `IMPLEMENTED_AND_VALIDATED`
- 4 `PARTIAL`
- 6 `RESEARCH_REQUIRED`
- 14 `NOT_IMPLEMENTED`
- 0 `IMPLEMENTED_NOT_VALIDATED`
- 0 `UNSUPPORTED`

Each record includes vendor, product/scope, domain, event family, native
format, transport, sourcetype, Technology Add-on dependency, CIM state,
required fields, scenarios, provenance, evidence, runtime maturity, Splunk
observation, distribution, sample-generation policy, and limitations.
Incomplete and research-required sources fail closed. CIM remains
`NOT_ESTABLISHED`; scenario maturity never promotes source maturity.

The UI supports independent source search, vendor/product/domain/event-family/
transport/maturity/Splunk filters, details, sample preview, provenance,
related scenarios, required configuration, and limitations. The existing four
generation modes remain Scenario, Data Source, Sourcetype/Event Family, and
Single Event.

## 8. Setup Wizard

`System → Connections` implements first-run setup and reconfiguration for
Docker Lab, existing Splunk Enterprise, and the Splunk Cloud architecture
target. It captures deployment type, endpoints, authentication, allowed
indexes, collectors, and guided-sample preference.

Security properties:

- credentials are request-body only, never URL parameters;
- API responses and metadata never return secrets;
- metadata is owner-readable (`0600`);
- durable credentials come from environment/platform secret injection;
- endpoint user-info, wildcard destinations, and non-loopback plaintext HTTP
  are rejected;
- TLS verification may be disabled only for documented local-lab hosts;
- validation performs an authorized bounded HEC probe, authenticated search,
  and an authorized-index search independently;
- indexes, roles, tokens, and listeners are not silently created.

Clean-room onboarding returned PASS for HEC, search, and index access.
After restart, configuration and both secret-presence states were restored
from metadata plus runtime environment.

Evidence:
`.artifacts/phase13-current/clean-room/final-setup-validation.json`

## 9. Installation tests

Splunk App:

1. Structure and manifest: PASS.
2. Safe extraction and package contents: PASS.
3. Live visibility in Splunk 10.2: PASS.
4. External-engine setup and health: PASS.
5. Scenario selection/execution and indexed evidence: PASS.
6. Investigation, dashboard generation, live panels, and export: PASS.
7. Upgrade preserving administrator `local/`: PASS.
8. Removal and reinstall: PASS.
9. AppInspect: NOT_TESTED (tool unavailable).

Docker:

1. Clean unique volumes: PASS.
2. Build/start/readiness: PASS.
3. Onboarding: PASS.
4. Security scenario: PASS.
5. Fresh authenticated Splunk search: PASS, five events.
6. Investigation: PASS, five results.
7. Dashboard: PASS, 14 generated panels and data validation.
8. Dashboard Studio export: PASS.
9. Stop/restart/persistence: PASS.
10. Safe disposable reset: PASS.

## 10. Security review

Release-oriented review covered active credentials, TLS, authentication,
sessions, input and endpoint validation, path/command injection surfaces,
SSRF, deserialization, container privileges, network exposure, dependencies,
logging, resource bounds, scenario sandboxing, and MCP/A2A endpoint policy.

Result: **PASS — no unresolved critical engineering defect found**.

- Runtime passwords/tokens are required inputs; no working default credential
  remains in active packaged code.
- The setup-control review identified and remediated a credential-retargeting
  path: initial or changed Splunk destinations now require credential
  re-entry, redirects are rejected, index identifiers are allowlisted, and the
  standalone engine binds to loopback by default.
- Secrets do not enter image layers, defaults, package `local/`, logs, browser
  URLs, API responses, or persisted connection metadata.
- The flow forwarder is non-root, drops capabilities, uses
  `no-new-privileges`, and permits insecure TLS only for an explicit local-lab
  hostname allowlist.
- External MCP/A2A, executable payload, and untrusted repository behavior
  remain blocked by existing bounded tests.
- No Docker socket is mounted.
- No new certificate or private key material was added.

The Docker Splunk certificate is an image-generated, self-signed lab
certificate. The loopback exception is intentional only for this disposable
lab. Production administrators must validate certificate dates, subject/
issuer, key strength, signature algorithm, and chain, for example:

```bash
openssl x509 -text -noout -in <certificate_file>
```

No deprecated or custom cryptographic algorithm was introduced. Package and
artifact hashes use SHA-256 for integrity, not password storage.

Evidence:
`.artifacts/phase13-current/release/security-scan.json`

## 11. Privacy and sanitization

Automated scanning is **PARTIAL** and does not establish clearance. It found
review candidates in 141 paths containing email-shaped values, 187 paths
containing non-private/non-documentation IPv4 values, 86 paths containing
UUID-shaped values, and eight PCAP files that require binary/manual review.
These include documentation, synthetic fixtures, vendor-shaped samples, and
accepted historical evidence; pattern matches are not proof of customer data.

No protected artifact was rewritten. Sanitization was deliberately not applied
without provenance and relationship review. Unknown binary redistribution
remains fail-closed for publication.

Evidence:
`.artifacts/phase13-current/release/privacy-provenance-audit.json`

## 12. Provenance and licensing

`THIRD_PARTY_NOTICES.md` describes major direct dependencies and the limits of
automated license metadata. The repository does not bundle Splunk Enterprise.
Static and generated vendor-shaped artifacts remain subject to human source,
employer-policy, trademark, and redistribution review.

Status: **REQUIRES_HUMAN_APPROVAL**.

## 13. SBOM and dependencies

- CycloneDX-format inventory: 122 components.
- Python direct dependencies are pinned.
- npm transitive versions are locked.
- Production npm audit: 0 vulnerabilities.
- `pip-audit`: 0 known vulnerabilities.
- Container image inventory: all listed release images version-and-digest
  pinned.
- Artifact checksum and reproducible-build evidence generated.
- No signature or external attestation was invented.

Evidence root: `.artifacts/phase13-current/release/`

## 14. Accessibility

Status: **PARTIAL**. Automated browser coverage verified semantic labels for
the new source/setup controls, keyboard focus progression, visible interactive
states, and 320 CSS-pixel reflow (a 1280-pixel layout at 400% zoom) without
horizontal document overflow. Existing browser suites also cover navigation
and responsive states.

Manual screen-reader testing, complete contrast measurement, browser-specific
200%/400% zoom review, and all applicable WCAG 2.2 AA success criteria were not
independently completed. Full WCAG compliance is not claimed.

## 15. Performance

Status: **PASS for bounded RC workloads; no soak-test claim**.

- Clean readiness: 90 seconds.
- Restart readiness: 67 seconds.
- Security scenario: five generated/sent events and five fresh indexed events;
  run/observe completed in approximately 1.3 seconds.
- Idle snapshot after validation:
  - Splunk/engine: 1.961 GiB, 10.53% CPU.
  - OpenTelemetry collector: 157.6 MiB, 0.01% CPU.
  - GoFlow2: 37.19 MiB, 0.00% CPU.
  - Flow forwarder: 24.45 MiB, 0.19% CPU.
- Existing bounded retry, backpressure, rate, event-count, packet, and duration
  tests passed.

Evidence: `.artifacts/phase13-current/performance/`

## 16. Beginner journey

Result: **automated clean-room validation**, not human usability acceptance.

Journey: create `.env`; start Compose; wait for health; open Connections;
save and validate; select validated `AI-001`; run; observe five events through
fresh Splunk search; run the attached investigation; generate and validate its
dashboard; export Dashboard Studio JSON; restart; verify persistence; reset.

Measured time to first ready UI was 90 seconds. Required manual configuration
was two runtime secrets and wizard endpoint/index choices. The first attempt
found and fixed volume ownership/readiness defects. Recovery is documented in
`docs/RELEASE_CANDIDATE_GUIDE.md`.

## 17. Regression

- Test environment: `.venv-phase13`, CPython 3.14.7, pytest 9.0.2;
  dependencies are pinned in `backend/requirements.txt` and
  `backend/requirements-test.txt`, with the complete inventory in the SBOM.
  The final backend command exited 0.
- Backend: 637 passed, 1 skipped, 2,314 warnings, 77 subtests.
- Gate 12F + Gate 13E: 19 passed (13/13 and 6/6), 53 warnings.
- Frontend build: PASS; one inherited bundle-size warning.
- Frontend lint: PASS; 11 warnings.
- Playwright: 33 passed, 16 conditional skips.
- Phase 13 browser journeys: 3 passed.
- Phase 12 references: 13/13 Splunk observed, field verified, investigated,
  detection executed, expected evidence matched, and false-positive behavior
  tested.
- Phase 12 dashboards: 13/13 SPL/data/export validated in this run; fresh
  visual marking was intentionally not manufactured.
- Dashboard registry: 27 eligible of 29; two research-required.
- Five Cisco Golden references: preserved.
- Cisco 100 effective maturity: 5 Golden, 70 Candidate, 25 Research Required.
- Scenario Studio, Dashboard Studio export, native transports, and fresh
  Splunk observation passed the broad suite.

Warning classification:

- 2,300 low-risk Python `datetime.utcnow()` deprecations.
- 13 low-risk Pydantic v2 `.dict()` migration warnings.
- 1 Starlette/FastAPI TestClient dependency deprecation.
- 11 frontend warnings: component-refresh/export and React effect/dependency/
  immutability findings. No warning was globally suppressed.

High-risk regressions found during execution (missing `os` import, flow
forwarder secret injection, fresh-volume ownership/readiness) were fixed and
retested.

## 18. Protected artifact audit

- Reported before Phase 13: 644.
- After: 649.
- Additions: five canonical/mirrored Phase 13 source-catalog files.
- Existing protected modifications/deletions: 0.
- Mutations during final release audit: 0.

Evidence:
`.artifacts/phase13-current/release/protected-artifacts.json`

## 19. Release Candidate acceptance matrix

- Splunk App package: PASS.
- Docker package: PASS.
- Splunk Enterprise compatibility: PASS (10.2 disposable lab).
- Splunk Cloud architecture: PARTIAL; unvalidated and uncertified.
- Security source catalog: PASS.
- Setup Wizard: PASS.
- Ingestion verification: PASS.
- Dashboard integration: PASS; fresh visual re-acceptance not repeated.
- Scenario Studio: PASS through regression.
- Security hardening: PASS.
- Privacy audit: REQUIRES_HUMAN_APPROVAL.
- Dependency/licensing audit: PARTIAL; automated inventory complete, legal
  conclusions unavailable.
- Accessibility: PARTIAL.
- Performance: PASS for bounded workloads.
- Documentation: PASS.
- Clean installation: PASS.
- Regression: PASS.
- Human legal/IP review: REQUIRES_HUMAN_APPROVAL.

## 20. Known limitations

- The Splunk App depends on an external engine/web integration; it is not a
  fully native search-head execution model.
- Splunk Cloud architecture is not certification or compatibility proof.
- AppInspect was not available.
- CIM remains `NOT_ESTABLISHED`.
- Two dashboards and 24 of 33 audited source families remain below implemented
  and validated status.
- Full manual WCAG review and sustained performance/soak testing remain.
- Lab TLS exceptions must never be copied to production.

## 21. Human approval requirements

1. Employer and contributor intellectual-property approval.
2. Third-party sample, PCAP, screenshot, documentation, and vendor-artifact
   redistribution review.
3. Dependency and third-party-notice legal review.
4. Splunk AppInspect/Splunkbase vetting if publication is requested.
5. Splunk Cloud vetting and tenant validation before compatibility claims.
6. Owner authorization before V1.0 publication.

## 22. V1.0 release blockers

- Resolve or explicitly approve all privacy/provenance scan candidates,
  especially eight PCAP files.
- Run applicable Splunk AppInspect checks and remediate findings.
- Complete manual accessibility review.
- Obtain legal/IP/licensing/employer-policy approvals.
- Obtain explicit owner authorization.

These are publication blockers. No unresolved critical Phase 13 engineering
defect was found in the validated deployment paths.

## 23. Recommended next steps

1. Conduct human artifact provenance and redistribution review.
2. Run Splunk AppInspect in an approved environment and retain exact output.
3. Perform screen-reader, contrast, zoom, and keyboard acceptance with a human
   tester.
4. Run an owner-approved longer Docker soak/backpressure test.
5. If Splunk Cloud support is desired, validate an authorized tenant and
   complete its app-vetting process.
6. Review this RC, then separately authorize or reject V1.0 release work.

## Exact validation commands

```bash
python3 -m venv .venv-phase13
.venv-phase13/bin/pip install -r backend/requirements-test.txt
PYTHONPATH=backend:src .venv-phase13/bin/python -m pytest -q -p no:cacheprovider

cd frontend
npm run build
npm run lint
npx playwright test

cd ..
.venv-phase13/bin/python scripts/sync_core.py
.venv-phase13/bin/python scripts/verify_sources.py
.venv-phase13/bin/python scripts/build_splunk_package.py
.venv-phase13/bin/python scripts/run_phase13_package_validation.py
.venv-phase13/bin/python scripts/run_phase13_release_audit.py

docker compose up -d --build --wait
docker compose ps
docker compose stop
docker compose start --wait
docker compose down --volumes
```

No main merge, tag, release, public image publication, Splunkbase submission,
or production deployment was performed.
