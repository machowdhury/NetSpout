# NetSpout Figma v3 — Phase 8B Evidence Expansion and Artifact Isolation

## Outcome

Phase 8B addresses the accepted Phase 8 test-harness defect: live and
screenshot suites could overwrite tracked historical evidence while attempting
current validation. Test output is now isolated by default, accepted evidence
is snapshotted before execution, and guarded runs fail if protected files
change. The guard never auto-restores files.

Acceptance criterion 39 passes: live/regression execution no longer silently
mutates accepted evidence fixtures, provenance catalogs, or historical
screenshots.

## Baseline

- Branch: `feature/figma-v3-unified-telemetry-lab`
- Exact starting HEAD: `fb473097f09ba20b7c8b22070cba3a2ad2222e85`
- Phase 8 implementation: `72b3f654cf0928fd0272b4b6dc1717822d3dbafa`
- Starting local/remote synchronization: `0 0`
- Starting worktree: clean
- Accepted HEAD ancestry: verified
- Protected accepted tree: **609 tracked files**
- Accepted tree manifest SHA-256:
  `bcbc61af90f69d31d03fa7d6e40da3ffce80c34dd0d5377538cd31b96538830b`

The digest is over `git ls-tree -r` output for all protected roots at the
accepted Phase 8 commit, including path, mode, object type, and Git blob ID.

## Previously mutating legacy suites

The audit identified these direct tracked-output paths:

- `tests/test_gate13d_gnmi_splunk_e2e.py` wrote 13 live gNMI/Splunk artifacts
  below `docs/acceptance/evidence/gate13d`.
- `tests/test_gate13e_customer_acceptance.py` rewrote three customer scorecards
  below `docs/acceptance/evidence/gate13e`.
- `docs/acceptance/evidence/gate11e/run_acceptance_suite.py` wrote packet,
  collector, Splunk, and scorecard evidence into the accepted Gate 11E tree.
- Gate 11E evidence/SVG generators wrote into accepted evidence and image
  locations.
- `scripts/verify_gate14b_certification.py` wrote 20 certification artifacts
  into `docs/acceptance/evidence/gate14b`.
- Gate 10.5, Gate 11C, and Gate 11D scripts wrote result/benchmark files into
  `docs/acceptance`.
- Playwright suites for Phases 1–8 wrote screenshots directly into
  `docs/implementation/images`, including Phase 5/7 live suites and the Phase
  8 Cisco 100 review.

Gate 12D reads committed evidence to validate its presence but does not write
that location, so its accepted fixture path remains read-only.

## Artifact classes and locations

### Accepted historical evidence

Guarded roots:

- `catalog`
- `backend/app/catalog_data`
- `netspout/catalog`
- `netspout/bin/catalog_data`
- `netspout/bin/netspout_core/catalog_data`
- `netspout/appserver/static/vendor_catalog.json`
- `docs/acceptance`
- `docs/implementation/images`

These locations contain accepted contracts, provenance, evidence, reports, or
historical visual review artifacts. Tests may read them but must not rewrite
them.

### Current-run evidence

Explicit Phase 8B runs use ignored directories below:

`/.artifacts/phase8b/<run>/`

Each guarded run writes:

- `artifact-isolation-manifest.json`
- `outputs/evidence/<suite>/...`
- `outputs/screenshots/<suite>/...`

The manifest classifies the output as `CURRENT_RUN_EVIDENCE` and records the
command, output root, protected roots, before/after protected file counts, Git
status, mutation result, and child exit code.

### Temporary test output

Without an explicit root, Python and Playwright helpers write below the
platform temporary directory:

`<tmp>/netspout-test-artifacts/temporary/process-<pid>/`

No default test path resolves into a tracked accepted-evidence directory.

## Protections introduced

- `scripts/artifact_isolation.py` provides a common safe output resolver,
  protected-root definition, SHA-256 snapshots, and add/modify/delete
  detection.
- `scripts/run_isolated_tests.py` wraps arbitrary test commands, injects
  `NETSPOUT_TEST_ARTIFACT_ROOT`, disables Python bytecode output, records a
  current-run manifest, isolates `NETSPOUT_STUDIO_DIR` below the current-run
  root, and returns exit code 86 if protected state changes.
- The wrapper compares both file content and scoped Git status before and
  after execution. It reports mutation and leaves investigation/restoration
  explicit.
- `frontend/tests/artifact-paths.ts` provides the equivalent process-scoped
  Playwright screenshot path.
- All Phase 1–8 screenshot-writing suites now use the shared helper.
- Gate 13D/13E and legacy Gate 10.5/11C/11D/11E/14B writers now use isolated
  evidence directories.
- `.artifacts/` is ignored so current-run evidence cannot be accidentally
  committed as accepted evidence.

Canonical catalog builders and `scripts/sync_core.py` remain intentional source
generators rather than test-output writers. Their destinations are protected
by guarded test execution; deliberate catalog regeneration remains a reviewed
development action.

Intentional promotion of a current-run artifact requires a separate reviewed
copy/change; there is no environment switch that silently targets historical
locations.

## Regression coverage

`tests/test_phase8b_artifact_isolation.py` verifies:

1. configured output roots are honored;
2. default output is temporary and outside accepted roots;
3. added, modified, and deleted files are detected;
4. a clean guarded command preserves protected state and writes a manifest;
5. a guarded command that rewrites a protected fixture fails with exit 86;
6. Gate 13D/13E writers use isolation;
7. Playwright suites contain no historical screenshot target;
8. an explicitly configured output root cannot target accepted evidence.

The mutation test uses a temporary Git repository and never alters NetSpout
accepted evidence.

## Validation

- Artifact-isolation regression: **9 passed**
- Phase 7 + Phase 8 + Phase 8B focused backend: **41 passed**
- Guarded Playwright screenshot smoke: **4 passed**
- Guarded full frontend: **22 passed, 4 expected skips**
- Frontend build: passed
- Frontend lint: passed with inherited warnings only
- Updated Python live-harness compilation: passed
- Guarded Phase 8 live Docker journey: **1 passed**
- Guarded stable broad backend: **476 tests: 471 passed, 1 skipped, 4
  inherited Gate 12F failures**; protected files remained **608 → 608** with
  zero mutations.
- Final expanded guard validation, including the static vendor-catalog mirror
  and isolated Studio state: **41 passed**, **609 → 609**, zero mutations.
- `git diff --check`: passed

Representative current-run manifests:

- `.artifacts/phase8b/frontend-full/artifact-isolation-manifest.json`
- `.artifacts/phase8b/backend-focused-final/artifact-isolation-manifest.json`
- `.artifacts/phase8b/live-phase8/artifact-isolation-manifest.json`
- `.artifacts/phase8b/backend-broad-final/artifact-isolation-manifest.json`
- `.artifacts/phase8b/followup-focused-final/artifact-isolation-manifest.json`

Every final accepted guarded validation run reported zero mutation of protected
roots. An earlier broad run was deliberately rejected by the guard because the
three ignored bytecode files described below were deleted concurrently; it was
not used as acceptance evidence.

## Files restored after testing

No accepted evidence fixture, provenance record, catalog, report, or
historical screenshot required restoration. Three ignored Python bytecode
files produced by a manual compile check inside the legacy Gate 11E source
directory were identified as temporary output and deleted. They were never
tracked or accepted evidence. The wrapper now sets
`PYTHONDONTWRITEBYTECODE=1` to prevent recurrence.

Final tracked evidence therefore represents intentional committed state.

## Credential, certificate, and crypto handling

While updating legacy live harnesses, pre-existing hardcoded local Splunk
credentials/tokens were removed from Gate 9, Gate 10, Gate 10.5, and Gate 14B
scripts. They now read `SPLUNK_USERNAME`, `SPLUNK_PASSWORD`, and
`SPLUNK_HEC_TOKEN` from the environment. This applies the no-hardcoded-
credentials rule because repository source is public/untrusted and live
credentials must remain externally configured.

No certificate was added or loaded, so certificate expiration, strength,
signature, and self-signed verification are not applicable to this change.
Legacy localhost live scripts still disable TLS verification; that pre-existing
test-only behavior was not expanded or represented as production security.
No cryptographic algorithm or key material was introduced.

## Final assessment

The known Phase 8 harness side effect is closed for the audited suites.
Accepted historical evidence is immutable during guarded execution, current
run evidence has an explicit classification and location, temporary output is
outside the repository, and mutation attempts fail visibly.

No main merge, release, or Phase 9 work was performed.
