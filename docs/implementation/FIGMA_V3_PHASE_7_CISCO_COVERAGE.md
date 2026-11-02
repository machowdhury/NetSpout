# NetSpout Figma v3 — Phase 7 Cisco Coverage Foundation

## Baseline and outcome

- Branch: `feature/figma-v3-unified-telemetry-lab`
- Exact starting SHA: `d30db8fbda271467589cb4b123ccdb6630e4c174`
- Accepted Phase 6 implementation:
  `1042c47e1265965f5d378794a6d55be256a0c1b6`
- Phase 7 implementation commit:
  `e7782e04e69b596e26e95a710168bf031085e6c8`
- Report finalization: documentation-only successor commit

Before edits, fetch confirmed the requested branch, a clean worktree, local and
remote HEAD at the starting SHA, and the Phase 6 implementation as an
ancestor. Phase 6 smoke verification completed with **25 passed, 5 warnings,
and 9 subtests passed**. History was not rewritten.

Phase 7 establishes a vendor-neutral coverage/evidence model and uses Cisco as
its first deep implementation. It does not implement Cisco 100. The result is
one evidence-deep Cisco 8000 IOS XR Product Pack, one Golden source, one
three-channel Golden Scenario, and an intentionally blocked Cisco Secure
Access research record. The one-scenario result is below the 3–5 target but
meets the trust objective; no unsupported scenario was added to satisfy a
counter.

## Files and architecture

The implementation commit changes 73 files, including synchronized runtime
mirrors. Principal canonical changes are:

- `catalog/vendor_coverage.json`: Cisco taxonomy, evidence, maturity,
  troubleshooting, production guidance, and scenario relationships.
- `catalog/telemetry_catalog.json`: IOS XR syslog native/Splunk/NetSpout
  contracts and verified integration relationship.
- `catalog/extension_packs.json`: Cisco IOS XR Product Pack, declarative
  template, validator, composition, investigation, and shared-state scenario.
- `src/netspout_core/vendor_coverage.py`: vendor-neutral coverage contracts and
  computed readiness.
- `src/netspout_core/pack_contracts.py`: reusable declarative native-template
  and Studio state-key contracts.
- `src/netspout_core/unified_generation.py` and `native_runtime.py`: generic
  template rendering and native syslog lifecycle execution.
- `src/netspout_core/scenario_studio.py`: data-declared state compatibility;
  no Cisco branch.
- `backend/app/main.py`: coverage APIs.
- `frontend/src/components/catalog/CiscoCoverageView.tsx`: evidence-backed
  coverage, contracts, research gaps, scenario, and production guidance.
- `tests/test_phase7_cisco_coverage.py` and Phase 7 Playwright suites.

`scripts/sync_core.py` synchronizes `vendor_coverage.py` and the new catalog to
the backend and packaged runtimes. Canonical and generated copies were
regenerated together.

## Cisco taxonomy and researched products

The catalog represents:

- Enterprise Networking: IOS XE, Catalyst switching, Catalyst Center,
  Wireless Controllers, Meraki, and SD-WAN.
- Service Provider: IOS XR, carrier routing platforms, and carrier telemetry.
- Data Center: NX-OS, Nexus, ACI, Nexus Dashboard, UCS, and Intersight.
- Security: Secure Firewall/FTD/FMC, ASA, ISE, Secure Access, Umbrella, Secure
  Endpoint, Secure Network Analytics, Secure Client, Duo, XDR, Secure
  Workload, and Cyber Vision.
- Observability: ThousandEyes, AppDynamics, and OpenTelemetry integrations.
- Collaboration: CUCM and Webex.

Only Cisco IOS XR and Cisco Secure Access count as researched. Other products
are `DISCOVERED` taxonomy records, not support claims. No unverified alias or
lifecycle equivalence was encoded.

## Evidence methodology and sources

Each material assertion records a claim, evidence class, publisher, title,
reference, product/software applicability, verification date, confidence, and
notes. Evidence is reference-only; no Cisco or Splunk documentation or public
sample was copied into the repository.

Primary references:

1. Cisco 8000 IOS XR Implementing System Logging:
   <https://www.cisco.com/c/en/us/td/docs/iosxr/cisco8000/system-monitoring/25xx/configuration/guide/b-system-monitoring-cg-cisco8k-25xx/implementing-system-logging.html>
2. Cisco 8000 Logging Services Commands:
   <https://www.cisco.com/c/en/us/td/docs/iosxr/cisco8000/system-monitoring/b-system-monitoring-cr-cisco8k/logging_services_commands.html>
3. Cisco 8000 IOS XR 7.11.x Telemetry Configuration Guide:
   <https://www.cisco.com/c/en/us/td/docs/iosxr/cisco8000/telemetry/711x/configuration/guide/b-telemetry-cg-8000-711x.pdf>
4. Cisco 8000 IOS XR 7.10.x SNMP Configuration Guide:
   <https://www.cisco.com/c/en/us/td/docs/iosxr/cisco8000/system-management/710x/configuration/guide/b-system-management-cg-8k-710x/configuring-simple-network-management-protocol.html>
5. Cisco 8000 Global Interface Commands:
   <https://www.cisco.com/c/en/us/td/docs/iosxr/cisco8000/Interfaces/b-interfaces-hardware-component-cr-8000/global-interface-commands.html>
6. Cisco Enterprise Networking Add-on for Splunk, Splunkbase app 7538:
   <https://splunkbase.splunk.com/app/7538>
7. IETF IF-MIB and OpenConfig interface models, used only for their standards
   roles.

Legacy repository Cisco samples were not used as authoritative evidence and
were not promoted.

## Coverage and contract matrix

### Cisco 8000 IOS XR

- Interface state syslog: `GOLDEN`
  - Native: documented node/timestamp/process and
    `%PKT_INFRA-LINK-3-UPDOWN` structure over syslog UDP.
  - Splunk: Cisco add-on 7538 is `RECOMMENDED`; the relationship is documented.
    The lab sourcetype `netspout:cisco:iosxr:syslog` is explicitly
    `NETSPOUT_DEFINED`.
  - NetSpout: allow-listed declarative template, structural validator, native
    UDP receiver, post-receipt HEC delivery, and modeled lifecycle.
  - CIM: **CIM NOT VALIDATED**.
- IF-MIB SNMP: `SPLUNK_VALIDATED`
  - Cisco documents IOS XR SNMP support; NetSpout uses its vendor-neutral
    IF-MIB protocol pack.
  - No Cisco-specific add-on, sourcetype, or CIM mapping is asserted.
- OpenConfig interfaces over gNMI: `SPLUNK_VALIDATED`
  - Applicability is restricted to documented IOS XR/OpenConfig releases.
  - NetSpout uses its vendor-neutral gNMI/OpenConfig protocol pack.
  - No official Cisco gNMI Splunk integration or CIM mapping is asserted.

Product maturity is `GOLDEN`; source maturity remains independent.

### Cisco Secure Access

Native telemetry, export mechanisms, Splunk integration, sourcetypes, and CIM
remain `RESEARCH_REQUIRED`. The UI shows the gaps. The source has no catalog
ID, generator, sourcetype, or integration recommendation. Generation fails
closed with HTTP 409 (`unknown catalog source`); no fallback event is emitted.

## Product Pack and raw fidelity

The `cisco-ios-xr-coverage` Pack depends on reusable syslog, SNMP, gNMI, and
destination capabilities. A generic `DeclarativeTemplateProfile` separates
structural, modeled, and derived fields and declares reusable Studio state
keys. Rendering and validation select data by profile ID; Core contains no
`if vendor == "Cisco"` branch.

The IOS XR fixture uses reserved fictional identity `cisco-asr9k-pe1` and
`HundredGigE0/0/0/1`. Structural validation checks the documented
category/group/severity/mnemonic/message shape separately from modeled node,
interface, state, timestamp, and process values. Runtime records retained the
documented raw shape; NetSpout correlation metadata was added only after the
native receiver boundary.

## Golden Scenario and shared state

`test-correlated-interface-degradation` is the single Phase 7 Golden Scenario.
One enterprise state and clock drive baseline, degradation, failover, and
recovery observations across:

1. IOS XR interface-state syslog;
2. IF-MIB SNMP;
3. OpenConfig interfaces over gNMI.

The composition validated common run, entity, interface, ordering, incident,
and recovery state. The Guided Experience reuses Understand → Prepare → Run →
Observe → Investigate → Validate → Replay. Scenario Studio cloned the Pack,
accepted a modeled `interface.status` change through data-declared state
compatibility, saved a private variant, and ran all three native channels.

The Investigation Pack covers incident discovery, affected-interface
identification, timeline reconstruction, three-source correlation, likely
cause, and recovery. Its current SPL is `NETSPOUT_SPECIFIC` because it depends
on run/scenario/phase metadata. The production guide separately provides a
portable search without those fields.

## Troubleshooting and production guidance

The verified troubleshooting operation is:

- Objective: inspect the affected interface.
- Platform: Cisco 8000 IOS XR.
- Command: `show interfaces HundredGigE 0/0/0/1`.
- Evidence: Cisco 8000 Global Interface Commands.
- Expected scenario result: modeled impact during the incident and healthy
  state after recovery. This modeled finding is not represented as a
  vendor-documented expected output.

“Take This to Production” lists real IOS XR sources, collection mechanisms,
the documented add-on relationship, NetSpout-defined lab sourcetypes,
production prerequisites, portable SPL, NetSpout differences, and known gaps.
It states that vendor deployment guidance remains authoritative.

## Runtime and Splunk validation

Live Docker source run:

- Run `21db863d-8eda-457d-ae19-e37d27c3cdd3`
- Status `OBSERVED`
- Native syslog receiver: completed
- Splunk: 1 event observed
- `SPLUNK_OBSERVED`, `SOURCETYPE_VERIFIED`, and `FIELDS_VERIFIED`: `PROVEN`

Live three-channel Golden Scenario:

- Run `9dd80797-6bab-4456-8fab-ee1d6016b2ad`
- All three required channel results: `COMPLETED`
- Generated records: 16
- Post-index observation: `OBSERVED`
- Investigation: `SUCCEEDED`, 4 correlated results
- CIM: **NOT VALIDATED**

Live Scenario Studio private clone:

- Run `f4fe758a-8a64-4e4a-8562-f7e29be6b399`
- Three channel results: `COMPLETED`
- Generated records: 16
- Subsequent Splunk observation proved all three channel observations.
- A second UI-driven run completed and produced the final completion capture.

Counts above are runtime observations, not claims about Cisco product
throughput or production sizing.

## Automated verification

- Final Phase 2–7 focused regression:
  **100 passed, 9 warnings, 9 subtests passed**.
- Phase 7 focused backend: **9 passed, 5 warnings**.
- Full frontend Playwright: **20 passed, 2 skipped**.
- Phase 7 coverage Playwright: **1 passed**.
- Phase 7 live Docker Studio Playwright: **1 passed**.
- TypeScript no-emit check: passed.
- Frontend production build: passed.
- Frontend lint: passed with inherited warnings; no Phase 7 lint error.
- `git diff --check`: passed.

The broad stable-stack command excluded the same four resource-heavy live
suites as Phase 6 and completed with **441 passed, 1 skipped, 67 subtests
passed, and 4 failures**. The four failures are the inherited Gate 12F
environment-dependent checks:

1. native SNMP customer-workflow scorecard;
2. HTTP native-SNMP scorecard;
3. native SNMP preflight readiness;
4. controlled-failure observation.

Their classification and behavior did not change in Phase 7. The unfiltered
repository run was also executed, but its live suites competed with the
already-running acceptance stack and therefore is not used as a stable
regression result.

## Docker journeys

- Journey A — Cisco Golden Source: preview/preflight/native run/Splunk
  observation passed.
- Journey B — Golden Scenario: three native channels, shared state, Splunk
  observation, investigation, validation, and repeat execution passed.
- Journey C — Research Required: Cisco Secure Access displayed evidence gaps
  and generation was blocked without sourcetype or TA fallback.
- Journey D — Scenario Studio: clone, modeled-state edit, private save,
  three-channel run, and Splunk observation passed.

## Screenshot inventory

The 21 files `docs/implementation/images/phase7-01-*.png` through
`phase7-21-*.png` cover the requested catalog, product, three contracts,
evidence, maturity, research-required state, scenario, topology/evidence chain,
telemetry/incident/Splunk lenses, runtime, raw evidence, investigation,
field/CIM status, troubleshooting, production guidance, Studio clone, and
completion. All were manually inspected. Contrast was corrected before final
capture. No unsupported content or sensitive identifier was found.

## Privacy, security, licensing, and provenance

- No customer/internal capture, hostname, URL, tenant ID, employee identifier,
  token, password, key, or functional certificate was added.
- Test identities use reserved or explicitly fictional values.
- No hardcoded credential was introduced; Docker credentials remain
  environment supplied.
- No X.509 certificate was added or loaded. Certificate marker strings in the
  inherited Studio scanner tests are nonfunctional detection fixtures, so
  certificate expiration/key/signature/self-signed checks are not applicable.
- No cryptographic primitive or algorithm was introduced.
- Evidence and public samples are referenced rather than redistributed.
- Third-party names are factual. No Cisco/Splunk certification, approval, or
  endorsement is claimed.

## Limitations and Phase 8 recommendation

- Only one Golden Scenario was created; the remaining 3–5 target was
  deliberately not filled without equivalent evidence.
- Add-on 7538 IOS XR parsing, official sourcetypes, extracted fields, and CIM
  remain unvalidated.
- IOS XR coverage is release-specific and limited to the documented source
  subset.
- Syslog TCP and OpenTelemetry remain inherited partial capabilities.
- Cisco aliases, lifecycle mappings, additional products, APIs, webhooks,
  MIBs, and YANG paths remain a research backlog.
- No new P0/P1 issue remains.

Phase 8 should begin only with authorization. It should scale by adding
evidence matrices first, then reuse this Product Pack, declarative-template,
Scenario Studio, Guided Experience, native-runtime, investigation, and
production-guidance pattern. `RESEARCH_REQUIRED` must remain the default when
any contract layer is unproven.
