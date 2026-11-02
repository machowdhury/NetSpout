# NetSpout Phase 8C — Multi-Domain Evidence & Runtime Validation

## Outcome

Phase 8C is complete as a bounded NetSpout lab validation.

The Cisco 100 now has one `GOLDEN` reference in each domain:

- Enterprise Networking: `C100-ENT-001`
- Service Provider & Carrier: `C100-SP-001` (inherited accepted reference)
- Data Center & AI Cloud: `C100-DC-001`
- Security & SASE: `C100-SEC-001`
- Sovereign Critical Infrastructure & Mixed Cross-Domain: `C100-CRI-002`

`GOLDEN` means that the local NetSpout guided chain has vendor evidence,
strict source contracts, native receiver observation, authenticated
source-scoped Splunk observation, investigation results, replay, topology,
troubleshooting, and production guidance. It does not mean Cisco or Splunk
certification, production-device validation, an official sourcetype, or a
validated CIM mapping.

The authorization diagram described Enterprise as the existing validated
reference. The accepted repository proved that the inherited reference was
actually Service Provider `C100-SP-001`. Phase 8C preserved that truth and
added the other four references.

## Baseline

- Branch: `feature/figma-v3-unified-telemetry-lab`
- Exact starting SHA: `55ee337d0e638f6654261e57468551f3b9e43b9e`
- Starting local/remote divergence: `0 0`
- Starting worktree: clean
- Phase 7, Phase 8, and Phase 8B reports reviewed before implementation
- Focused baseline: **41 passed**
- `main` was not merged
- No release or Phase 9 work was performed

## Authoritative source evidence

### IOS XE

Cisco IOS XE 17.17 Catalyst 9600 documentation shows:

`%LINK-3-UPDOWN: Interface <interface>, changed state to up|down`

Reference:
<https://www.cisco.com/c/en/us/td/docs/switches/lan/catalyst9600/software/release/17-17/configuration_guide/sys_mgmt/b_1717_sys_mgmt_9600_cg/configuring_system_message_logs.html>

The body is vendor documented. Timestamp and outer framing remain modeled and
deployment-profile dependent.

### NX-OS

Cisco Nexus 9000 troubleshooting documentation provides the bounded ETHPORT
link lifecycle used by the Data Center reference:

- `%ETHPORT-5-IF_DOWN_LINK_FAILURE: Interface <interface> is down (Link failure)`
- `%ETHPORT-5-IF_UP: Interface <interface> is up in Layer3`

Reference:
<https://www.cisco.com/c/en/us/support/docs/switches/nexus-9000-series-switches/221572-troubleshoot-link-flap-issue-on-nexus-90.html>

No undocumented speed suffix was invented.

### Secure Firewall ASA

Cisco documents:

- `%ASA-6-302013` for TCP connection creation
- `%ASA-6-302014` for TCP connection teardown

Reference:
<https://www.cisco.com/c/en/us/td/docs/security/asa/syslog/asa-syslog/syslog-messages-302003-to-342008.html>

The Security reference uses reserved RFC 5737 addresses. A 302013 event is
normal connection evidence and is not represented as proof of malicious
activity. Only the modeled rate change is suspicious enough to investigate.

### IOS XR

The accepted IOS XR `PKT_INFRA-LINK-3-UPDOWN` evidence and source contract are
reused by ID. Phase 8C does not copy or redefine that accepted source.

## Architecture delivered

The remaining scenario-ID branch in unified correlation was replaced with a
strict composition execution contract:

- `SINGLE_EVENT`
- `SHARED_STATE_LIFECYCLE`
- explicit state profile, entity, and interface
- optional native-channel correlation
- per-binding runtime entity and interface identities

Phase-specific declarative templates permit documented members of one event
family without changing raw strings after generation. A generic structural
validator checks the selected template, and bounded per-phase event counts
model the ASA connection-rate increase.

The compact `phase8c_reference_packs.json` specification is expanded by one
reusable builder into source, generator, validator, transport, Guided
Scenario, Investigation Pack, and composition contracts. No Phase 8C
scenario ID, IOS XE message, NX-OS message, or ASA message is branched in
Core runtime code.

Pack-owned sources now receive source-scoped Splunk searches from their own
declared `NETSPOUT_DEFINED` sourcetypes. This prevents one source in a
correlated run from receiving another source's observation credit.

Raw current-run payloads are not copied into API state. SHA-256 digests are
retained per phase in channel evidence so exact runtime artifacts can be
audited without duplicating payloads.

## Runtime and Splunk evidence

Accepted summary:

`docs/implementation/evidence/phase8c/phase8c-live-validation-summary.json`

Guarded source run:

`.artifacts/phase8c/live-20261007T-phase8c-r4`

Results:

- `C100-ENT-001`: 4 generated, 4 receiver-observed, 4 Splunk-observed
- `C100-DC-001`: 4 generated, 4 receiver-observed, 4 Splunk-observed
- `C100-SEC-001`: 11 generated, 11 receiver-observed, 11 Splunk-observed
- `C100-CRI-002`: 8 generated across two source families, 8
  receiver-observed, 8 Splunk-observed
- all four source-scoped Investigation Packs returned results
- all required scenario validation expectations were `PROVEN`

The Cross-Domain reference used one run and ordered state clock while
preserving independent IOS XE and IOS XR entity, interface, raw-format, and
Splunk-search scopes.

The first complete live run proved all receiver and source-scoped Splunk
observations but exposed a missing `search` prefix in the Investigation Pack
SPL. That test-design defect was fixed; the accepted rerun proved all four
investigations. A later background shell wrapper stalled before starting
Python and was terminated. It created no artifact directory and changed no
repository file.

## UI

The Cisco 100 page now presents an evidence-backed reference strip containing
exactly one reference per domain. Each card displays:

- domain and stable scenario ID;
- current maturity;
- evidence-reference count;
- whether runtime evidence is recorded;
- whether Splunk evidence is recorded.

The cards open the full Evidence Inspector, source contracts, limitations,
Investigation Pack, troubleshooting guidance, and production guidance.

## Test artifact isolation

### Previously mutating legacy suites

The Phase 8B audit remains authoritative:

- Gate 13D wrote live gNMI/Splunk artifacts below accepted Gate 13D evidence.
- Gate 13E rewrote accepted customer scorecards.
- Gate 11E and Gate 14B wrote packet, scorecard, and certification artifacts
  below accepted evidence.
- Gate 10.5, Gate 11C, and Gate 11D wrote result/benchmark files below
  `docs/acceptance`.
- legacy Phase 1–8 Playwright suites wrote historical screenshots below
  `docs/implementation/images`.

### Accepted historical evidence locations

The guarded immutable roots remain:

- `catalog`
- `backend/app/catalog_data`
- `netspout/catalog`
- `netspout/bin/catalog_data`
- `netspout/bin/netspout_core/catalog_data`
- `netspout/appserver/static/vendor_catalog.json`
- `docs/acceptance`
- `docs/implementation/images`

Canonical catalog synchronization was an intentional reviewed development
operation performed before guarded validation, not test-generated output.

### Current-run evidence locations

- `.artifacts/phase8c/static-*`
- `.artifacts/phase8c/ui-*`
- `.artifacts/phase8c/live-20261007T-phase8c-r4`

Each guarded run records its command, output and Studio roots, before/after
Git status, protected file counts, mutation set, and child exit code.

### Temporary output

When no explicit root is supplied, test helpers continue to use process-scoped
OS temporary directories. Scenario Studio state is redirected under the
current-run output root. Python bytecode is disabled by the guard.

### Protections and regression coverage

- all native/live Phase 8C execution used `scripts/run_isolated_tests.py`;
- the accepted live run reported **619 protected files before and after**;
- the accepted live run reported **zero protected mutations**;
- no historical screenshot suite was run;
- the new Playwright regression writes no screenshot;
- Phase 8B mutation-guard regression remains in the focused suite;
- Phase 8C tests cover compact Pack expansion, five-domain maturity,
  exact vendor-bounded structures, generic shared lifecycle execution,
  source-specific identity, source-scoped search, raw digests, and absence of
  Phase 8C vendor/scenario branches in Core.

### Files restored after live testing

None. No accepted evidence fixture, provenance record, catalog, or historical
screenshot was changed by a test. Final tracked evidence consists only of
intentional Phase 8C implementation, synchronized mirrors, this report, and
the sanitized accepted evidence summary.

## Validation

- Focused Phase 7/8/8B/8C/native regression: **58 passed**
- Phase 8C focused factory/runtime regression: **40 passed**
- Phase 8C readiness Playwright regression: **1 passed**
- Frontend production build: passed
- Frontend lint: passed with inherited warnings and no Phase 8C error
- Canonical catalog validation: passed
- Source-of-truth synchronization: passed
- Guarded native receiver/Splunk/investigation journey: passed
- Guarded live protected-artifact mutation count: **0**

## Safety and remaining limits

- No credential, password, token, certificate, or key was added to source.
  Live credentials were read from environment/configuration and were not
  serialized into evidence.
- No certificate material was added or loaded. Certificate expiration,
  strength, signature, and self-signed-certificate inspection therefore did
  not apply to repository artifacts.
- The accepted local Splunk container uses an existing self-signed lab
  endpoint and the inherited lab-only insecure verification option. This is
  explicitly not production guidance.
- No cryptographic primitive or deprecated crypto API was added.
- The three new sourcetypes are `NETSPOUT_DEFINED`.
- Official Cisco add-on sourcetypes, extractions, and CIM mappings remain
  unvalidated.
- The evidence proves NetSpout's local modeled receiver-to-Splunk chain, not
  production device behavior, support entitlement, or vendor endorsement.
