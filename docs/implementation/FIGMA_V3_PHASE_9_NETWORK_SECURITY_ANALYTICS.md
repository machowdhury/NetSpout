# NetSpout Phase 9 — Network Security Analytics & SecOps Lab

## 1. Executive outcome

**Acceptance: PASS.**

Phase 9 adds an enterprise-state-driven network security lab with six bounded reference scenarios. A deterministic incident plan now drives DNS and IPFIX observations, native loopback receivers, Splunk evidence, investigations, and runtime-semantic detection validation. It does not execute attacks or generate unrelated logs that merely share timestamps.

Known boundaries are explicit: detection packs are `RUNTIME_VALIDATED`, CIM is `NOT_ESTABLISHED`, firewall/identity/endpoint evidence is not fabricated, and indicators are not presented as proof of compromise, denial of service, lateral movement, or exfiltration.

## 2. Starting HEAD and branch verification

- Branch: `feature/figma-v3-unified-telemetry-lab`
- Starting HEAD: `3cc705fa34ad127417366b405b2461aa6b676d62`
- Reported Phase 8C implementation commit `ac13032` is in the starting ancestry.
- The initial working tree was clean and the branch matched its remote (`0` ahead, `0` behind).
- The Phase 7, Phase 8, Phase 8B, and Phase 8C reports were reviewed before implementation.
- The bounded baseline completed with 41 passing tests.

No reset or overwrite of accepted work was performed.

## 3. Architecture changes

The implementation adds four reusable canonical components:

- `security_state.py`: deterministic incident entities, relationships, observations, explicit behavioral states, and six bounded profiles.
- `dns_wire.py`: strict RFC 1035 query/response encoding and parsing, including compression pointers and NXDOMAIN.
- `security_analytics.py`: required-field/source-gated analytics and runtime-semantic detection checks.
- `phase9_security_packs.py`: scenario, topology, KPI, investigation, expected-finding, and Detection Validation Pack assembly.

`UnifiedGenerationService` derives every source channel from one seeded incident plan. `NativeRuntimeFacade` adds a DNS channel with a bundled per-run loopback UDP receiver. Canonical modules and the Phase 9 catalog are synchronized into backend and Splunk package mirrors through the existing sync mechanism.

The behavior chain is:

`Behavior → Shared incident plan → DNS/IPFIX observations → Native receivers → Splunk → Investigation → Detection validation → Expected findings`

Generation is bounded to 32 DNS and 32 flow observations per channel. Seed, intensity, entity count, duration, and timing remain controlled inputs.

## 4. New and reused Source Contracts

### DNS

The new `ietf-dns-rfc1035` source uses:

- Native contract: RFC 1035 wire messages over UDP.
- Splunk contract: NetSpout's explicit lab normalization, not a vendor add-on claim.
- NetSpout contract: query, response code, addresses, phase, incident/run identifiers, and provenance derived from parsed wire observations.

The `netspout:dns:wire` sourcetype is labeled `NETSPOUT_DEFINED`. It is not represented as a resolver log, authoritative-server log, or DNS security-product log.

### Network flow

Phase 9 reuses the existing IETF IPFIX source and native binary encoder/collector contract. No information elements, templates, message IDs, or vendor fields were invented.

No firewall, identity, endpoint, Sysmon, Windows, EDR, or other vendor source was added merely to make scenarios look richer. Their absence is surfaced as missing evidence where relevant.

## 5. Native telemetry fidelity

DNS runtime evidence follows:

`GENERATED → ENCODED → UDP_SENT → RECEIVER_OBSERVED → RESPONSE_OBSERVED → NORMALIZED → SPLUNK_DISPATCHED → SPLUNK_OBSERVED`

The bundled receiver binds only to loopback, parses each query, emits a protocol-correct matching response, and shuts down after the bounded run.

IPFIX retains the existing native evidence chain:

`GENERATED → ENCODED → UDP_SENT → COLLECTOR_OBSERVED → DECODED → FORWARDED → SPLUNK_OBSERVED`

OS send acceptance is not treated as receiver observation, HEC acknowledgement is not treated as indexing, and search observation remains source scoped.

## 6. DNS capability and evidence

The implementation supports native DNS query/response exchanges, A-record responses, response-code 3 (Name Error/NXDOMAIN), compressed names, deterministic timestamps, baseline and incident phases, and safe synthetic names under `.example` and `.invalid`.

The source contract is grounded in RFC 1035. IANA special-purpose registries support the safe test identifiers. Runtime tests verify valid encoding, parsing, malformed-message rejection, loopback transport, response matching, and the distinction between native wire evidence and NetSpout normalization.

## 7. NetFlow/IPFIX capability

Security profiles reuse the existing native IPFIX runtime for source/destination addresses, protocol, ports, bytes, packets, timing, duration, direction, frequency, and bounded distributions. Fresh Docker runs proved collector observation, decoding, forwarding, and Splunk indexing.

The current collector labels some flow events with its registration phase. Phase 9 therefore does not claim that collector-side phase labels alone prove phase-specific detection semantics.

## 8. Security scenario catalog

The catalog contains exactly six Phase 9 references:

1. Controlled Traffic Flood Indicators
2. DNS Diversity and NXDOMAIN Indicators
3. Periodic External Communication Indicators
4. Internal Reconnaissance Indicators
5. DNS Tunneling and Exfiltration Indicators
6. Cross-Source DNS, Beaconing, and Reconnaissance Incident

Every pack exposes scenario ID, security domain, entities, relationships, topology, timeline, telemetry manifest, evidence-gated KPI definitions, investigations, detection validation, expected findings, false-positive controls, blind spots, and evidence states. This extends the existing Scenario Pack model; it does not create a dashboard-specific parallel model.

## 9. Reference scenario maturity

| Scenario | Native Contract | Runtime | Splunk | Detection | CIM | Final Maturity |
|---|---|---|---|---|---|---|
| Traffic Flood | Reused verified IPFIX | Validated | Freshly observed | Runtime-semantic validated | NOT_ESTABLISHED | SPLUNK_VALIDATED |
| DNS Anomaly | RFC 1035 | Validated | Freshly observed | Runtime-semantic validated | NOT_ESTABLISHED | SPLUNK_VALIDATED |
| Beaconing | RFC 1035 + IPFIX | Validated | Freshly observed | Runtime-semantic validated | NOT_ESTABLISHED | SPLUNK_VALIDATED |
| Internal Reconnaissance | Reused verified IPFIX | Validated | Freshly observed | Runtime-semantic validated | NOT_ESTABLISHED | SPLUNK_VALIDATED |
| DNS Tunneling Indicators | RFC 1035 + IPFIX | Validated | Freshly observed | Runtime-semantic validated | NOT_ESTABLISHED | SPLUNK_VALIDATED |
| Cross-Source Incident | RFC 1035 + IPFIX | Validated | Freshly observed | Runtime-semantic validated | NOT_ESTABLISHED | SPLUNK_VALIDATED |

`SPLUNK_VALIDATED` applies to the scenario telemetry and investigation chain. It does not promote Detection Validation Packs beyond their independently proven `RUNTIME_VALIDATED` outcome.

## 10. Shared-state correlation

The security state model uses:

`NORMAL → PRECURSOR → SUSPICIOUS_ACTIVITY → CONFIRMED_BEHAVIOR → IMPACT → RECOVERY`

Profiles use only the stages that apply. DNS and flow projections share the incident ID, seed, simulation clock, entities, destinations, and behavioral plan. Tests prove deterministic replay and stable cross-source identifiers. Baseline and incident observations are generated from the same model rather than assembled as independent fixtures.

## 11. Detection Validation Packs

Each scenario declares its objective, ATT&CK behavior mapping, telemetry and field prerequisites, SPL, expected baseline and incident behavior, false-positive controls, blind spots, and validation outcome.

Validation executes the corresponding analytics against generated observations and checks required fields, baseline/incident separation, and scenario-specific behavior. Outcomes are `RUNTIME_VALIDATED`. Fresh Splunk searches proved the SPL executes against actual onboarded fields, but successful parsing or result return is intentionally not promoted to Splunk-semantic detection validation.

MITRE ATT&CK is used only as a behavior taxonomy:

- T1498.001 for direct network-flood behavior
- T1071.004 for DNS use
- T1046 for network service discovery
- T1048.003 for unencrypted non-C2 exfiltration behavior; the lab models indicators only

ATT&CK is not used as a telemetry contract or proof that the modeled behavior succeeded.

## 12. Splunk integrations and sourcetypes

- IPFIX: existing `netflow:collector` path and bundled GoFlow2/forwarder pipeline.
- DNS: `netspout:dns:wire`, explicitly `NETSPOUT_DEFINED`, delivered through the configured HEC destination after native loopback observation.
- Index used in fresh validation: `idx_network_ops`.

No Splunk integration, vendor parser, or sourcetype ownership was invented. DNS lab normalization remains separate from native protocol evidence.

## 13. CIM status

**CIM: NOT_ESTABLISHED.**

Raw source fidelity is preserved. Similar field names do not establish CIM compliance. The five Phase 8C Cisco Golden references also remain `NOT_ESTABLISHED`; Phase 9 provides no independent evidence that would justify changing them.

## 14. Investigation SPL

Every reference supplies find-incident, timeline, source analytics, detection review, and validation recipes. Required fields are declared and recipes fail closed when prerequisites are absent. Queries use the actual index and sourcetypes above.

Run-scoped recipes are marked `NETSPOUT_SPECIFIC` because they use `netspout_run_id` and behavioral phase metadata. Portable guidance describes replacing lab-only metadata with production entity/time scoping; NetSpout-specific correlation metadata is never presented as production-portable SPL.

## 15. Guided lab UX

The existing guided experience now presents the security progression and evidence-gated analytics in **Understand**, then Detection Validation Pack outcome, required telemetry, false positives, blind spots, and limitations in **Validate**. Existing topology and evidence-path views render Phase 9 metadata without scenario-specific renderers.

The resulting journey is:

`Learn → Understand → Prepare → Run → Observe → Investigate → Detect → Validate → Take to Production`

Simple mode retains the guided path; Advanced mode retains contract and runtime detail.

## 16. Scenario Studio compatibility

The fresh Docker journey cloned the beaconing reference, changed bounded modeled intensity to 2 and a layout value, saved it, reloaded it, compiled it while preserving contract fingerprints, and ran it to `OBSERVED`. The clone retained its own scenario/run identity while explicitly deriving telemetry from the supported source profile. Unsupported origins still fail closed.

## 17. Docker journeys

Fresh local Docker validation completed:

- Traffic Flood: IPFIX collector and Splunk observation succeeded.
- DNS Anomaly: native DNS and Splunk observation succeeded.
- Beaconing: DNS/IPFIX and investigations succeeded.
- Internal Reconnaissance: IPFIX and investigations succeeded.
- DNS Tunneling Indicators: DNS/IPFIX and investigations succeeded.
- Cross-Source Incident: shared DNS/IPFIX plan and investigations succeeded.
- Fail Closed: tests reject absent/unsupported authoritative contracts and missing required analytic fields.
- Existing Cisco Golden: regression succeeded.
- Scenario Studio: clone/save/reload/modify/run reached `OBSERVED`.

Evidence: `.artifacts/phase9/live-final-20261007T232622Z/phase9-live-validation.json`.

## 18. Test results

- Initial bounded baseline: 41 passed.
- Phase 9/8C/artifact focused regression: 43 passed.
- Cisco 100 and multi-domain regression: 31 passed.
- Gate 12F SNMP productization: 13/13 passed.
- Gate 13E live customer acceptance with environment-supplied lab credentials: 6/6 passed.
- Frontend TypeScript/Vite build: passed.
- Frontend lint: passed with 13 pre-existing warnings.
- Guided/Phase 9 Playwright with current-run screenshot output enabled: 6 passed.
- Fresh Docker/Splunk validation: six of six scenarios observed; all investigation searches succeeded; Studio clone observed.
- Guarded stable backend regression: 514 collected; 513 passed, 1 skipped, 0 failed.

Tests cover DNS wire behavior, deterministic plans, bounds, safe identifiers, analytics prerequisites, fail-closed behavior, native DNS, pack contracts, detection semantics, cross-source correlation, Studio compatibility, mirrors, Cisco references, and accepted artifact isolation.

## 19. Screenshot review

The following live states were captured and manually inspected:

- `.artifacts/phase9/ui-final/01-security-scenario-gallery-and-detail.png`
- `.artifacts/phase9/ui-final/02-cross-source-topology.png`
- `.artifacts/phase9/ui-final/03-security-understand-baseline-incident.png`
- `.artifacts/phase9/ui-final/04-security-incident-lens.png`
- `.artifacts/phase9/ui-final/05-security-evidence-paths.png`
- `.artifacts/phase9/ui-final/screenshots/guided-scenario/phase4-11-observe-evidence.png`
- `.artifacts/phase9/ui-final/screenshots/guided-scenario/phase4-13-spl-results.png`
- `.artifacts/phase9/ui-final/screenshots/guided-scenario/phase4-14-validation.png`
- `.artifacts/phase9/ui-final/screenshots/guided-scenario/phase4-16-replay.png`

They show the actual Phase 9 gallery/detail metadata, shared topology, behavioral states, analytics, evidence paths, observation, investigation results, detection limitations, false-positive controls, CIM/missing-evidence state, validation, and replay. Studio clone state is recorded in the fresh runtime artifact. Historical accepted screenshots were not regenerated or modified.

## 20. Artifact isolation

The Phase 8C baseline contained 619 protected files. Phase 9 legitimately adds one catalog file in each of the five protected catalog roots, producing 624 protected files.

Final protection result: **624 before → 624 after; zero mutations**. Git-status changes in protected roots were limited to the five expected new `phase9_security_packs.json` mirrors. All runtime, Playwright, Studio, and Splunk evidence used isolated `.artifacts/phase9` paths.

## 21. Security and privacy

- No real attacks, malware, credential theft, exfiltration, public targets, customer data, or production identifiers are used.
- Addresses are loopback or IANA documentation ranges; names use special-use test suffixes.
- Event counts, intensity, seed, and retries are bounded.
- Credentials are supplied through environment/configuration and are not serialized into evidence or added to source.
- No certificates were introduced or loaded. The existing localhost self-signed Splunk TLS exception is restricted to the local lab and is not production guidance.
- No cryptographic algorithm or custom cryptography was added; therefore no banned/deprecated cryptography or PQC migration claim applies.

These controls implement the repository credential, certificate, and cryptographic-security rules because this phase touches authenticated Splunk delivery and a native network protocol.

## 22. Provenance and licensing

Protocol semantics cite the IETF RFC 1035 and the already-established IPFIX standards/contracts. Safe identifiers cite IANA registries. ATT&CK references describe behavior only. Detection logic is small, original, scenario-specific validation logic; no proprietary Splunk Security Content collection, vendor capture, Sigma corpus, or YARA rules were copied.

Sanitization is not treated as redistribution permission. No third-party capture is redistributed.

## 23. Limitations

- Detection packs are runtime-semantic validated, not Splunk-semantic validated.
- CIM remains `NOT_ESTABLISHED`.
- DNS normalization is NetSpout-defined and is not interchangeable with resolver, authoritative, or security-product logs.
- Firewall, identity, and endpoint corroboration is not present because no additional authoritative contract was required or justified.
- Flow sampling can understate traffic. Flow evidence cannot prove availability impact, successful lateral movement, command content, compromise, attribution, or exfiltration.
- NetFlow v9 over UDP supplies no native confidentiality, integrity, or peer authentication; Phase 9 confines it to the trusted local lab. Production IPFIX transport must follow current organizational security policy rather than the obsolete TLS/DTLS versions cited by the original RFC.
- DNS frequency, diversity, entropy-like patterns, long labels, and NXDOMAIN rates are indicators with legitimate alternatives.
- The existing collector phase-label limitation prevents treating flow phase labels alone as detection proof.

## 24. Phase 10 readiness

**READY.**

The six scenario packs expose reusable metadata that a future Dashboard Recipe Engine can consume without a parallel model. Phase 9 does not implement Dashboard Extension V2, the Dashboard Recipe Engine, Industry Studio, agentic AI, software supply-chain functionality, SOAR, or remediation.

The Cisco catalog remains exactly 100 references: 70 Candidate, 25 Research Required, and the same five Golden references (`C100-ENT-001`, `C100-SP-001`, `C100-DC-001`, `C100-SEC-001`, `C100-CRI-002`). No maturity was inflated.
