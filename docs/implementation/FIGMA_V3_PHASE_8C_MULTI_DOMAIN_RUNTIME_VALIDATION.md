# NetSpout Phase 8C — Multi-Domain Evidence & Runtime Validation

## Executive Outcome

**PASS**, with explicit production limitations.

Phase 8C now has one evidence-backed, locally runnable reference for each Cisco
100 domain. Fresh validation proved supported native receiver paths, local
Splunk indexing, source-scoped investigation results, fail-closed behavior,
Scenario Studio cloning, and protected-artifact isolation. The inherited four
Gate 12F failures were reproduced, traced to one authentication environment
contract mismatch, fixed without changing SNMP protocol behavior, and rerun
successfully.

`GOLDEN` in this report means the complete NetSpout local lab experience passed.
It does not mean production-device validation, Cisco or Splunk certification,
an official Splunk sourcetype, or runtime-validated CIM.

## Baseline

- Repository: `machowdhury/NetSpout`
- Branch: `feature/figma-v3-unified-telemetry-lab`
- Accepted Phase 8B ancestor: `55ee337d0e638f6654261e57468551f3b9e43b9e`
- Expanded Phase 8C completion starting SHA:
  `c568c73d2216134708235f633cbb6410c324cd68`
- Starting local/remote divergence: `0 0`
- Starting worktree: clean
- Ancestry: the starting SHA descends from the accepted Phase 8B SHA
- Phase 7, Phase 8, Phase 8B, and accepted Phase 8C reports were reviewed
- Focused baseline: 58 passed
- Phase 8C Playwright baseline: 1 passed
- Catalog validation, source-mirror audit, and frontend lint passed

The earlier report's “40 focused tests” could not be reproduced from the
current named module combinations. Current reproducible counts are recorded
under Testing; no maturity claim relies on the historical count.

## Scope Discipline

- Cisco 100 remains exactly 100; no Cisco 101 or second catalog was created.
- Distribution remains 20/20/20/20/20.
- No Phase 9 Network Security Analytics platform was implemented.
- No Industry Studio, agentic AI, unrelated vendor, transport, or pack
  architecture was introduced.
- No general evidence, maturity, testing, or artifact framework was redesigned.
- Changes after the accepted Phase 8C implementation were bounded to Gate 12F
  environment compatibility, runnable Studio/guided handoff, exact regression
  expectations, visual-review capture, and this report.
- `main` was not merged. No release or tag was created.

## Domain Depth Summary

| Domain | Reference Scenario | Native Contract | Runtime | Splunk | CIM | Investigation | Final Maturity |
|---|---|---|---|---|---|---|---|
| Enterprise Networking | C100-ENT-001 | Cisco IOS XE 17.17 LINK-3-UPDOWN body; outer framing modeled | 4/4 receiver-observed | 4/4 fresh indexed observation | NOT_ESTABLISHED | Fresh source-scoped result | GOLDEN |
| Service Provider & Carrier | C100-SP-001 | IOS XR syslog, IF-MIB SNMPv2c, OpenConfig gNMI kept separate | Syslog/SNMP/gNMI accepted; Gate 12F 13/13 fresh | Fresh Gate 12F search/scorecard passed | NOT_ESTABLISHED | Correlated interface recipe validated | GOLDEN |
| Data Center & AI Cloud | C100-DC-001 | Cisco Nexus 9000 ETHPORT down/up structures | 4/4 receiver-observed | 4/4 fresh indexed observation | NOT_ESTABLISHED | Fresh source-scoped result | GOLDEN |
| Security & SASE | C100-SEC-001 | Cisco ASA 302013/302014 connection lifecycle | 11/11 receiver-observed | 11/11 fresh indexed observation | NOT_ESTABLISHED | Fresh rate/lifecycle result | GOLDEN |
| Critical Infrastructure / Cross-Domain | C100-CRI-002 | Reused IOS XE and IOS XR contracts | 8/8 across two receivers | 8/8 fresh, independently source-scoped | NOT_ESTABLISHED | Fresh two-source correlation result | GOLDEN |

## Enterprise Reference

`C100-ENT-001`, Campus Access Link Degradation, was revalidated rather than
rebuilt. Cisco IOS XE 17.17 Catalyst 9600 documentation establishes the
`%LINK-3-UPDOWN: Interface <interface>, changed state to <state>` body.
NetSpout models reserved entity/interface values, time, phase, and outer
framing. One shared lifecycle drives BASELINE, DEGRADE, FAILOVER, and RECOVERY.

Fresh result:

- source: `cisco-ios-xe-interface-syslog`
- transport: Syslog/UDP through the bundled receiver
- generated/receiver/Splunk: 4/4/4
- sourcetype: `netspout:cisco:iosxe:syslog` (`NETSPOUT_DEFINED`)
- investigation: succeeded with one result
- CIM: `NOT_ESTABLISHED`
- production guidance: use supported IOS XE logging and validate the deployed
  Splunk parsing contract before relying on fields or CIM

## Service Provider & Carrier

### Candidate selection

All 20 Service Provider records were inspected. Strong candidates included
`C100-SP-001` IOS XR Interface Degradation, `C100-SP-003` BGP Peer Session
Instability, `C100-SP-004` BGP Route Withdrawal Propagation, and
`C100-SP-005` Provider Edge Access Link Failure.

`C100-SP-001` remained selected because it already had the strongest complete
evidence chain: accepted IOS XR syslog evidence, standards-backed IF-MIB,
OpenConfig interface paths, all three supported vendor-neutral runtimes,
shared state, bundled receivers, Splunk observation, investigation, and
production guidance. The BGP candidates were not promoted because Phase 8C did
not establish equally complete message/path, runtime, and Splunk contracts;
inventing an IOS XR gNMI BGP path was explicitly avoided.

### Contracts and validation

- product/platform: IOS XR / Cisco 8000-family modeled reference; applicability
  is bounded by each cited source and is not generalized to every IOS XR release
- native contracts: IOS XR link-state syslog, IF-MIB SNMPv2c, and OpenConfig
  interface gNMI
- shared state: interface status, loss, utilization, and path health
- timeline: BASELINE → DEGRADE → FAILOVER → RECOVERY
- runtime: native Syslog/UDP, SNMPv2c BER/UDP, and gNMI/gRPC receiver paths
- Splunk: fresh Gate 12F scorecards and authenticated searches passed
- sourcetypes: NetSpout-defined contracts; official App 7538 IOS XR
  sourcetype behavior remains unestablished
- CIM: `NOT_ESTABLISHED`
- troubleshooting: evidence-backed `show interfaces` operation reference
- production-portable SPL avoids `netspout_run_id`; the guided test query is
  correctly labeled `NETSPOUT_SPECIFIC`

Gate 12F retained ASN.1 BER, traps, informs and acknowledgements, GET,
GETNEXT, GETBULK, Response, OID-store behavior, and external/reference checks.

## Data Center & AI Cloud

### Candidate selection

All 20 Data Center records were inspected. Strong candidates included
`C100-DC-001` Nexus Fabric Uplink Degradation, `C100-DC-002` vPC Member
Failure, `C100-DC-003` EVPN Route Withdrawal, and `C100-DC-005` ACI
Leaf-Spine Link Failure.

`C100-DC-001` was selected because Cisco Nexus 9000 documentation provides
bounded ETHPORT link-failure and recovery structures compatible with the
existing Syslog/UDP runtime. vPC, EVPN, and ACI alternatives required more
product-specific structural evidence or subsystem work and were not promoted.

### Contracts and validation

- product/platform: Nexus 9000 / NX-OS; applicability is bounded to the cited
  Nexus troubleshooting material
- native contract: `%ETHPORT-5-IF_DOWN_LINK_FAILURE` and
  `%ETHPORT-5-IF_UP` structures; no undocumented speed suffix was added
- modeled values: reserved node, interface, timestamp, phase, and impact
- runtime: 4/4 bundled-receiver observations
- Splunk: 4/4 fresh indexed observations and one investigation result
- sourcetype: `netspout:cisco:nxos:syslog` (`NETSPOUT_DEFINED`)
- CIM: `NOT_ESTABLISHED`
- troubleshooting: cited `show interface` and logging operations
- limitation: link messages establish interface state, not application impact
  or root cause on real infrastructure

## Security & SASE

### Candidate selection

All 20 Security records were inspected. Strong candidates included
`C100-SEC-001` Secure Firewall Suspicious Connection Burst,
`C100-SEC-002` FTD Access-Control Policy Denial, and `C100-SEC-005` ISE
Authentication Failure Spike.

`C100-SEC-001` was selected because Cisco publishes the ASA 302013/302014
connection lifecycle structures, the source works through supported Syslog/UDP,
and the sequence has useful Splunk investigative value without requiring the
future Phase 9 detection platform. FTD policy and ISE candidates were not
promoted without equivalent complete native/Splunk/runtime evidence.

### Trust-chain separation

- behavior: a NetSpout-modeled increase in connection creation rate
- native telemetry: Cisco-documented ASA 302013 connection creation and 302014
  teardown structures
- detection: no attack analytic or threshold is claimed
- Splunk normalization: a NetSpout-defined sourcetype and run fields
- CIM: `NOT_ESTABLISHED`

ASA 302013 is connection evidence, not proof of attack. All addresses are RFC
5737 test addresses. Fresh validation generated and receiver/Splunk-observed
11/11 records; the source-scoped investigation returned one result.

Production use requires Cisco-supported logging, a locally established normal
rate, verified extraction, and an independently validated detection policy.

## Critical Infrastructure / Cross-Domain

### Candidate selection and composition

All 20 mixed Cross-Domain records were inspected. `C100-CRI-002` Telecom
Operations Network Degradation was selected over industry-specific utility,
healthcare, transport, and identity scenarios because it composes the already
verified IOS XE and IOS XR contracts without inventing industry logs.

The modeled causal chain is:

`shared path condition → operations-edge interface transition → carrier-edge
dependency transition → service-path impact → two source-native observations`

Both channels consume one run and ordered state clock while retaining separate
entity, interface, message structure, receiver, sourcetype, and Splunk search
scope. Fresh validation observed 8/8 records across both families and returned
one correlated result. This proves causality inside the NetSpout state model;
shared lab time does not prove causality between independently collected
production events.

No utility, hospital, railway, banking, or government telemetry was invented.
Industry context supplies narrative and impact only.

## Evidence Reuse and Three-Contract Separation

- Native contracts are supported by Cisco documentation or standards.
- Splunk contracts define local ingestion/search and are not used as evidence
  for Cisco wire formats.
- NetSpout contracts declare modeled values, state keys, deterministic
  lifecycle generation, and strict structural validation.
- IOS XR source contracts are referenced, not copied.
- IOS XE is reused by Enterprise and Cross-Domain.
- Generic Syslog, SNMP, and gNMI runtimes remain vendor-neutral.
- The shared declarative lifecycle pack is reused; no scenario-ID-specific
  vendor message branch was added to Core.

## Cisco 100 Final Maturity

| Primary state | Count |
|---|---:|
| CANDIDATE | 70 |
| RESEARCHED | 0 |
| CONTRACTED | 0 |
| FORMAT_VALIDATED | 0 |
| RUNTIME_VALIDATED | 0 |
| SPLUNK_VALIDATED | 0 |
| GOLDEN | 5 |
| RESEARCH_REQUIRED | 25 |
| UNSUPPORTED | 0 |
| BLOCKED | 0 |
| **TOTAL** | **100** |

Domain distribution is exactly 20 Enterprise, 20 Service Provider, 20 Data
Center, 20 Security, and 20 Sovereign Critical Infrastructure / Mixed
Cross-Domain. Every scenario has exactly one primary maturity state.

## CIM

CIM is tracked independently from maturity. No selected reference has a
runtime-validated CIM mapping. All five reference outcomes are
`NOT_ESTABLISHED`; none was inferred from product names, a TA name, or local
sourcetype behavior.

## Investigation Packs and Expected Findings

Each Golden reference provides Find Incident, Build Timeline, Identify Entity,
Inspect State, Correlate Sources, Determine Impact, and Validate Recovery
through reusable recipes. Fresh local investigations returned results for
Enterprise, Data Center, Security, and Cross-Domain. Service Provider
investigation/scorecard behavior passed Gate 12F.

Queries using run IDs or `netspout_phase` are `NETSPOUT_SPECIFIC`.
Production-portable queries use product-documented message identifiers and
deployment placeholders; they do not depend on simulation-only fields.

## Scenario Studio and Guided Experience

The accepted Cisco 100 API previously cloned every definition as
definition-only, so Golden references opened an empty non-runnable Studio
draft. Golden definitions now clone their mapped runtime scenario; unresolved
definitions remain definition-only and fail closed.

Validation covered:

- Data Center Golden clone
- modify modeled state
- immutable contract fingerprint enforcement
- save and reload
- run
- tampered fingerprint rejection
- Guided Lab selection preserved from Cisco 100

Focused Studio backend tests passed 42/42 during implementation; final combined
focused validation passed 62 tests plus 9 subtests. Playwright passed 3/3,
including runnable Studio handoff.

## Gate 12F Root Cause

The four historical failures were reproduced before modification.

| Test | Reproduced | Root Cause | Test Valid | Fix / Disposition | Current Result | Residual Risk |
|---|---|---|---|---|---|---|
| Native SNMP workflow scorecard | Yes | `SnmpSplunkBridge` read only `NETSPOUT_SPLUNK_PASSWORD`; the guarded environment supplied `SPLUNK_PASSWORD`, causing Splunk REST HTTP 401 after valid native SNMP work | Yes | Accept standard and NetSpout-prefixed environment names; preserve protocol assertions | PASS | Live Splunk availability remains environmental |
| HTTP workflow scorecard | Yes | Same REST credential-name mismatch propagated through the API result | Yes | Same bounded environment contract fix | PASS | API still requires a configured lab destination |
| Native SNMP preflight | Yes | REST-search authentication check received HTTP 401; HEC, binaries, UDP bind, and index path were not the root cause | Yes | Resolve runtime password from either supported environment name | PASS | Self-signed local TLS remains lab-only |
| Controlled Failure D, missing phase | Yes | The intentionally partial run could not complete its Splunk observation checks because REST auth failed before the missing-phase assertion could be evaluated | Yes | Restore authenticated observation; retain missing-RECOVERY failure semantics | PASS | Timing remains dependent on a healthy local stack |

No port conflict, BER defect, receiver race, process-lifecycle leak, socket-state
error, stale fixture, or test-order dependency explained the reproduced four.
Supplying the already-present `SPLUNK_PASSWORD` under the old NetSpout-specific
name made all 12 original tests pass before the code fix, isolating the cause.

The final suite adds a nonfunctional-placeholder regression for both standard
environment aliases and passes 13/13. No SNMP assertion was deleted, skipped,
or mocked away.

## Research-Required Fail-Closed Behavior

An unresolved Cisco 100 scenario was opened during Playwright validation.
The UI reported the missing native contract, transport/version applicability,
and Splunk relationship, blocked execution, and explicitly promised no
fallback event, sourcetype, TA, or CIM mapping. Backend regression also covers
fail-closed generation. No generic fallback telemetry was introduced.

## Artifact Isolation

All fresh backend/live runs used `scripts/run_isolated_tests.py`. Current-run
evidence is under `.artifacts/phase8c/` and is not committed.

- stable backend regression: 619 protected files before → 619 after; 0 mutations
- Gate 12F: 619 before → 619 after; 0 mutations
- live domain validation: 619 before → 619 after; 0 mutations
- guarded UI run: protected artifacts unchanged
- historical screenshots were not overwritten
- no accepted fixture was regenerated

## Testing

Final and implementation validation:

- stale exact-registry regressions corrected: 42 passed
- guarded stable backend regression: 487 run, 486 passed, 1 skipped, 0 failed
- focused Phase 7/8/8B/8C/Studio/API: 62 passed, 9 subtests passed
- Gate 12F: 13 passed
- Phase 8C Playwright: 3 passed
- catalog schema/reference validation: passed
- source-of-truth mirror audit: passed
- frontend production build: passed
- frontend lint: passed with 13 inherited warnings and no error
- `git diff --check`: passed before final commit

An unfiltered discovery attempt entered resource-heavy live suites and was
terminated after approximately nine minutes; it is not acceptance evidence.
The stable broad command explicitly excluded Gate 11C, Gate 12D, Gate 13D, and
Gate 13E live suites, which are validated separately against their required
services.

## Docker / Live Journeys

The healthy local Docker stack supplied Splunk, the flow collector/forwarder,
and the OpenTelemetry collector. Fresh backend journeys used the real local
Splunk endpoints:

- Enterprise: 4 generated → 4 receiver-observed → 4 Splunk-observed →
  investigation succeeded
- Service Provider: native SNMP workflow, API, preflight, controlled failures,
  and scorecards passed 13/13
- Data Center: 4 → 4 → 4 → investigation succeeded
- Security: 11 → 11 → 11 → investigation succeeded
- Cross-Domain: 8 records across two independent sources → 8 observed →
  correlated investigation succeeded
- Fail closed: unresolved source blocked with no fallback
- Studio: new Data Center reference cloned as runnable and retained immutable
  structural fingerprints

Browser state validation and native/Splunk runtime validation were intentionally
separate: the former used deterministic API fixtures, while the latter used
fresh local Docker Splunk searches. This avoids presenting mocked browser data
as indexed evidence.

## Screenshot Review

Thirty-one meaningful current-run screenshots were captured under
`.artifacts/phase8c/screenshots-expanded-final/`, including the overview,
five references, topologies, contracts/evidence, runtime claims,
investigations, troubleshooting, production guidance, CIM status,
Cross-Domain propagation, fail-closed state, Studio clone, maturity matrix, and
final evidence-debt view.

Review findings:

- five Golden references and the 20/20/20/20/20 distribution are visible;
- native/Splunk contracts and `NOT_ESTABLISHED` CIM status are explicit;
- Research Required clearly blocks generation without fallback;
- Studio opens the Data Center clone as runnable rather than definition-only;
- Cross-Domain topology and simulation clock expose the modeled dependency;
- dense Service Provider topology labels overlap at the full six-entity view.
  This is a presentation limitation, not a hidden contract/runtime failure, and
  was not expanded into a Phase 8C visualization redesign.

No screenshot was promoted into historical evidence or committed.

## Performance

No material regression was observed in Cisco 100 load, detail selection,
evidence views, Studio load, or focused scenario execution. The production
frontend built successfully. The existing minified bundle remains about 846 kB
and emits the inherited large-chunk warning; Phase 8C did not undertake a
performance project.

## Security and Privacy

- New fixtures use reserved/test-only identifiers.
- No customer or internal data was introduced.
- No new password, token, API key, private key, or certificate was committed.
- The encountered SNMP bridge password fallback was removed; runtime passwords
  now come from `NETSPOUT_SPLUNK_PASSWORD` or `SPLUNK_PASSWORD`.
- Test coverage uses explicit nonfunctional credential placeholders.
- Credentials were not serialized into current-run evidence.
- No cryptographic algorithm or deprecated crypto API was added or changed.
- No certificate file or embedded certificate was introduced, so certificate
  expiration/key/signature/issuer checks do not apply to changed artifacts.
- The existing localhost Splunk endpoint uses a self-signed certificate with
  verification disabled only for the bounded lab run. This is not production
  guidance and must not be copied into a production deployment.

This applies the no-hardcoded-credentials rule by removing the encountered
functional-looking password fallback and requiring environment-supplied
credentials. It applies the certificate and crypto rules by making no new
certificate/crypto claim and by explicitly limiting inherited insecure TLS
behavior to the local test environment.

## Provenance and Licensing

Only factual contract metadata and references are stored. No vendor
documentation, diagram, packet capture, proprietary dataset, or questionable
legacy sample was copied. New raw values are contract-derived synthetic data.
Privacy/sanitization, provenance, and redistribution remain separate concepts.
No new third-party runtime dependency was added.

NetSpout makes no Cisco or Splunk certification, approval, or endorsement
claim.

## Limitations

- Three new Phase 8C sourcetypes and the IOS XR lab sourcetype are
  NetSpout-defined.
- Official current Cisco add-on sourcetypes, extractions, and CIM mappings are
  not validated for the new references.
- Product-version applicability is bounded by cited evidence.
- Local Docker results do not prove real-device behavior, production sizing,
  entitlement, or security configuration.
- ASA connection creation is not attack attribution.
- Cross-Domain shared state proves modeled causality only.
- Service Provider topology labels need future presentation refinement.
- Inherited frontend lint and bundle-size warnings remain.

## Commit Discipline

- Starting HEAD: `c568c73d2216134708235f633cbb6410c324cd68`
- Gate 12F environment fix: `c3e86a3`
- Golden Studio productization: `360effb`
- Guided selection preservation: `2d6ace7`
- Regression expectation alignment: `01a1060`
- Validation/security completion: `ac13032`
- Final report commit: this report's commit
- Final remote HEAD: recorded after push

Accepted history was not rewritten.

## Phase 9 Readiness

**READY** for explicit Phase 9 authorization.

Phase 8C now supplies five defensible reference chains, actual Gate 12F root
cause, runnable non-Enterprise Studio handoff, fresh Splunk evidence, and zero
protected-artifact mutation. Phase 9 must not infer official sourcetypes, CIM,
detections, or production causality from these local lab results.

No Phase 9 work was started. Await explicit authorization.
