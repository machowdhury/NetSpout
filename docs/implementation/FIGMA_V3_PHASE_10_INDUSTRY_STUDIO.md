# NetSpout Figma v3 Phase 10 — Industry Studio

## 1. Executive outcome

Phase 10 adds a versioned Industry Pack layer and a first-class Industry Studio without creating a second simulation runtime or telemetry model. Three bounded references—Financial Services, Healthcare, and Manufacturing—reuse existing verified Scenario Packs and Source Contracts. One declared entity/dependency graph drives both topology perspectives and deterministic impact propagation.

Fresh local Docker/Splunk validation observed every required technical source for all three references. Business effects remained explicitly `MODELED`; no transaction, patient, production, revenue, or clinical outcome was asserted. The implementation satisfies the Phase 10 acceptance criteria within the documented reference scope and does not claim comprehensive industry coverage.

Acceptance: **PASS**

Starting HEAD: `4a3cd0bd6f9866be02b259ebc2dcc7b09ffce899`

## 2. Starting HEAD and baseline

- Branch: `feature/figma-v3-unified-telemetry-lab`
- Starting local and remote HEAD: `4a3cd0bd6f9866be02b259ebc2dcc7b09ffce899`
- The starting tree was clean and synchronized.
- Initial bounded backend baseline: 69 passed, 5 warnings, 9 subtests.
- Protected-artifact baseline: 624 files.
- Cisco 100 baseline: 70 Candidate, 25 Research Required, 5 Golden.
- Phase 7, 8, 8B, 8C, and 9 reports and the pack, runtime, state, investigation, and topology architecture were reviewed before implementation.

## 3. Architecture changes

`src/netspout_core/industry_packs.py` is the canonical implementation. It defines strict, versioned Industry Pack models, catalog discovery, runtime-reference validation, deterministic dependency propagation, and fail-closed composition. Generated backend and Splunk copies remain byte-aligned through the existing source synchronization guardrail.

`catalog/industry_packs.json` is the only authored industry registry. `NetSpoutCatalog` loads and validates it, then registers discoverable `INDUSTRY` packs that contain references but no copied Source Contracts, generators, scenarios, or investigations.

The backend exposes catalog, detail, composition, and Scenario Studio draft endpoints. Industry logic remains outside generic generation code; generic runtime code contains no industry-name switch.

## 4. Industry Pack schema

Schema version `1.0.0` includes:

- industry and pack identity/version;
- implemented scope and maturity;
- business capabilities and operational objectives;
- environments and infrastructure archetypes;
- typed entities and explicit directed dependencies;
- modeled impacts with assumptions and exclusions;
- referenced Scenario Pack IDs and Source Contract IDs;
- investigation objectives, provenance, and validation requirements;
- dashboard-compatible industry, entity, dependency, topology, telemetry, evidence, and impact metadata.

Strict validation rejects duplicate references, unknown entities/dependencies/sources/scenarios, cyclic dependency graphs, observed business-impact claims, observed operational objectives without a telemetry contract, and incompatible scenario selections.

Only declared modeled parameters are accepted. `affected_entity_ids` and `impact_assumptions` cannot alter native scenario parameters or telemetry structure. Undeclared protocol/vendor/telemetry parameters fail closed.

## 5. Industry Studio UX

The existing Figma v3 shell now includes **Build → Industry Studio**. The guided flow is:

`Choose → Explore → Configure → Run → Observe → Investigate → Validate`

Simple mode emphasizes industry, environment, incident, impact, execution, and investigation. Advanced mode exposes source contracts, graph assumptions, dependency metadata, exclusions, and evidence boundaries. The implementation reuses the existing compact shell, status badges, generation controls, and topology component.

The UX deliberately presents:

- `OBSERVED` only after receiver and authenticated Splunk proof;
- `MODELED` for declared business dependency impact;
- `NOT ESTABLISHED` where no supporting contract exists.

## 6. Industry reference packs

| Industry | Bounded environment | Scenario | Native sources | Maturity | Business-impact state |
|---|---|---|---|---|---|
| Financial Services | Synthetic retail branch/WAN | `C100-CRI-002` | IOS XE and IOS XR interface syslog | SPLUNK_VALIDATED reference | MODELED |
| Healthcare | Synthetic hospital-campus application segment | `C100-ENT-001` | IOS XE interface syslog | SPLUNK_VALIDATED reference | MODELED |
| Manufacturing | Synthetic factory IT/OT connectivity boundary | `C100-DC-001` | NX-OS interface syslog | SPLUNK_VALIDATED reference | MODELED |

These maturity labels apply only to the listed examples. They do not mean the industries as a whole are validated or supported.

Financial Services models branch payment-service reachability risk without generating transactions, cardholder data, counts, revenue, or customer outcomes.

Healthcare models clinical-application reachability risk without patient identity, health records, medical-device messages, care delays, or clinical-harm claims.

Manufacturing models production-monitoring visibility risk without PLC/fieldbus traffic, registers, safety-system events, control commands, production counts, downtime, or loss claims.

## 7. Enterprise dependency graph

The shared model supports business capability, business service, application, infrastructure service, network, device, security zone, site, and operational process entities. Directed relationships carry criticality and a human-readable assumption.

Propagation begins at an explicitly affected entity and traverses only declared environment dependencies. The result reports affected and propagated entities, traversed dependencies, technical evidence status, and applicable modeled impacts. Cycles and unknown references are rejected.

The Technical Topology and Business Dependency View are two filters over this same graph; there is no parallel business topology.

## 8. Cross-domain simulation

Industry composition delegates execution to the existing deterministic Scenario Pack runtime. The reference scenario, run ID, seed, clock state, entity IDs, and source bindings form one incident state. The financial reference freshly observed two source channels with the same run ID, seed, and clock, while dependency propagation used that same selected incident.

This phase adds no unrelated synthetic event stream and makes no claim that correlation alone proves a business outcome. Existing NetOps, SecOps, ITOps, application-observability, and cloud scenarios remain composable through the shared pack/runtime contracts. The validated Phase 10 references demonstrate cross-source causal state and business-dependency propagation; they do not add new cloud, application, or industrial telemetry.

## 9. Business impact assumptions

Business impact is a separate contract from technical evidence. Every impact:

- has one of `MODELED`, `INFERRED`, or `NOT_ESTABLISHED`;
- identifies trigger entities, impacted entities, and dependency IDs;
- exposes assumptions and exclusions;
- is rejected if authored as `OBSERVED`.

Fresh Splunk proof can update the technical-evidence section to `OBSERVED`; it cannot promote a business impact. No arbitrary revenue, transaction, patient, production, or downtime score exists.

## 10. Native and Splunk contracts

All three packs reuse the existing:

`Native Contract → Splunk Contract → NetSpout Contract`

No syslog format, sourcetype, OID, MIB, YANG path, NetFlow/IPFIX field, DNS structure, CIM mapping, or vendor API was invented. Fresh authenticated searches proved source-scoped records in `idx_network_ops` for all required channels.

CIM remains **NOT_ESTABLISHED**. Industry metadata does not create or imply a CIM mapping.

## 11. Scenario Studio integration

`StudioScenarioPack` now persists `industry_id`, `industry_environment_id`, and `business_impact_assumptions`. Industry Studio can clone the selected authoritative scenario into Scenario Studio, preserving Source Contract fingerprints and native telemetry structure.

The live manufacturing journey cloned, changed modeled layout/assumptions, saved, reloaded, compiled, ran, and reached `OBSERVED`. Contract fingerprints and business-impact assumptions were preserved.

## 12. Investigation recipes

Each reference exposes business context, hypothesis/objectives, affected infrastructure, dependency path, evidence boundary, modeled consequence, recovery criteria, and production guidance while referencing its existing authoritative Scenario Pack investigation recipes.

Fresh NetSpout-specific searches used the actual configured index, sourcetypes, run ID, host, and phase fields. All reference searches succeeded. Production portability remains explicitly separate: production guidance requires replacing NetSpout run fields and modeled dependencies with deployment-reviewed identifiers and service maps. No NetSpout-specific query is labeled production-portable.

## 13. Dashboard Extension V2 compatibility

No Dashboard Recipe Engine was implemented. Industry composition exposes the existing dashboard handoff boundary: industry ID, scenario ID, run ID, capability, entities, dependencies, shared topology, telemetry/source manifest, modeled impact, investigations, and evidence states.

No separate dashboard data model, fake KPI, or unsupported operational measure was added.

## 14. Docker journeys

- **A — Financial Services:** two native syslog channels observed in Splunk; investigation succeeded; payment-service impact remained modeled.
- **B — Healthcare:** native campus interface evidence observed; investigation succeeded; clinical-application impact remained modeled.
- **C — Manufacturing:** native NX-OS interface evidence observed; investigation succeeded; production-monitoring impact remained modeled.
- **D — Cross-Domain:** one deterministic financial run drove both source observations and one dependency graph; run ID, seed, entity identity, and clock were aligned.
- **E — Industry Studio:** manufacturing clone changed modeled data, saved/reloaded, ran, and was observed.
- **F — Fail Closed:** an undeclared industrial protocol parameter was rejected and generated no fallback telemetry.
- **G — Regression:** Cisco, Phase 9 security, and focused pack/runtime regressions passed; Gate 12F was rerun against the local lab.

Current-run artifact: `.artifacts/phase10/live-final/phase10-live-validation.json`

## 15. Test results

- Phase 10 focused suite: 20 passed.
- Phase 10 plus extensibility, guided UX, Phase 9, Phase 8C, Cisco, and artifact-isolation regressions: 127 passed.
- Cisco 100 regression: passed; 70 Candidate, 25 Research Required, 5 Golden.
- Gate 12F SNMP productization: 13/13 passed with the healthy local Docker/Splunk lab.
- Canonical source/mirror verification: passed.
- Frontend TypeScript/Vite build: passed; inherited chunk-size warning only.
- Frontend lint: passed with 13 pre-existing warnings and no Phase 10 error.
- Industry Studio Playwright: 2 passed.
- Guarded stable backend regression: 527 passed, 1 skipped, and 67 subtests passed using the established live-suite exclusions.
- Gate 13E gNMI live acceptance was run separately twice after Docker restart: preflight and static checks passed, while four runtime checks failed because its legacy HEC dispatcher received connection refusal. Phase 10's HEC/Splunk path succeeded immediately afterward for all references, so this is recorded as an explained environment-specific legacy live-suite limitation rather than a Phase 10 telemetry regression.

## 16. Screenshot review

Five current-run screenshots cover selection, business dependency view, observed-versus-modeled evidence, investigation validation, and advanced Source Contract details under `frontend/.artifacts/phase10/ui-final/screenshots/phase10-industry/`.

Review confirmed the compact Figma v3 shell, seven-step workflow, three real catalog choices, shared graph perspectives, visible evidence labels, impact guardrails, and advanced disclosure. No fake KPI, decorative graph, neon gradient, or separate visual language was introduced.

## 17. Artifact protection

Protected artifacts changed from 624 to 629 files solely because the canonical `industry_packs.json` was added to the five protected catalog roots. Existing protected files had zero modifications or deletions. The final protected snapshot contains 629 files and all five additions are synchronized copies.

Current-run test and screenshot output was isolated under `.artifacts` / `frontend/.artifacts`; accepted historical evidence was not overwritten.

## 18. Security and privacy

- Credentials were supplied through process environment only and were not serialized into artifacts or source.
- No credential, token, password, private key, or connection string was added.
- No certificate file or embedded certificate was introduced. The existing localhost Splunk endpoint uses a self-signed lab certificate and the bounded live runner retains the existing localhost-only insecure verification exception; this is not production guidance. Certificate expiration, key strength, signature algorithm, and issuer must be verified before any production use.
- No cryptographic algorithm or protocol policy was added or changed.
- All industry identities, entities, addresses, and dependencies are synthetic.
- No customer topology, patient information, cardholder data, proprietary capture, or industrial command was introduced.

## 19. Provenance and licensing

Industry context references the public FFIEC Architecture, Infrastructure, and Operations material, HHS 405(d) Health Industry Cybersecurity Practices, and NIST SP 800-82r3. These references support context and dependency assumptions only; they are not used to infer telemetry contracts.

The implementation links to authoritative material and copies no proprietary packet capture, vendor documentation, patient/payment data, or third-party dataset. Privacy review and redistribution permission remain separate checks; sanitization is not treated as a license.

## 20. Known limitations

- Each industry has one deeply validated synthetic reference, not comprehensive industry coverage.
- Business outcomes are models, not independent Splunk observations.
- Application health, transactions, clinical systems, PLCs, industrial protocols, production output, and alternate paths are not instrumented.
- The validated cross-domain boundary proves shared state, multiple source observations, and dependency propagation; it does not claim new five-domain telemetry coverage.
- CIM is not established.
- Dashboard Extension V2 metadata is exposed, but the recipe engine is intentionally deferred.
- The legacy Gate 13E gNMI live suite remained 2/6 after a Docker restart because its HEC dispatcher received connection refusal; its preflight was ready, Gate 12F passed 13/13, and the Phase 10 HEC journeys all reached fresh Splunk observation.
- Existing frontend lint and bundle-size warnings remain outside the Phase 10 change.

## 21. Phase 11 readiness

**READY**, subject to explicit authorization. Phase 10 leaves a versioned, discoverable extension point for additional reviewed packs and dashboard composition without registering empty future-industry placeholders.

No merge, release, or Phase 11 work was performed.
