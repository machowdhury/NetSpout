# NetSpout Figma v3 Phase 11 — Dashboard Recipe Engine

## 1. Executive result

Acceptance: **PARTIAL**

The reusable Dashboard Pack architecture, recipe engine, scenario-aware UI, bounded SPL validation, export adapter, NOC wallboard, and Gate 13E reliability fix are implemented. All 14 eligible dashboard contexts were freshly generated, SPL validated, data-shape validated, and export validated against the authorized local Splunk lab.

Visual-design acceptance remains pending because `DASHBOARD_V2_HANDOFF.md` and the Design NetSpout Dashboard Extension V2 source were not present in the repository or approved local project materials. No claim is made that the implementation matches an unavailable design. Consequently, no dashboard was promoted to `VISUALLY_VALIDATED` or `DASHBOARD_READY`.

## 2. Starting HEAD and baseline

- Branch: `feature/figma-v3-unified-telemetry-lab`
- Starting local and remote HEAD: `45aa1678aeeed41369d4dff965860b0b073974a8`
- Initial divergence: 0 ahead / 0 behind; starting tree clean.
- Bounded baseline: 87 passed, 5 warnings.
- Protected-artifact baseline: 629 files.
- Phase 8C, Phase 9, and Phase 10 reports and the existing Gallery, Scenario/Industry Studios, Source/Splunk Contracts, Investigation Packs, entity graphs, live validation, and Splunk integration were reviewed.

## 3. Design handoff availability

`DASHBOARD_V2_HANDOFF.md` and an identifiable V2 design source were **NOT FOUND**. Searches covered the repository and approved local project stores. Existing Figma v3 shell patterns were reused, but missing V2 material blocks visual-design acceptance.

## 4. Dashboard Pack architecture

`src/netspout_core/dashboard_recipes.py` is canonical and is synchronized to backend and Splunk packaging copies. Its strict, versioned `DashboardPack` references the scenario/version/run, domain/industry, Source and Splunk Contracts, Investigation and Detection references, shared entity graph, topology reference, telemetry manifest, observed fields, KPIs/panels, SPL, drilldowns, dependencies, validation evidence, CIM status, and export compatibility.

Packs reference authoritative contracts; they do not copy or mutate native telemetry, vendor raw events, Investigation Packs, or enterprise state. The topology explicitly records `shared_with_scenario: true`.

## 5. Recipe registry

`catalog/dashboard_recipes.json` is the single authored registry and contains 19 reusable recipes across the requested families: routing, WAN, data-center fabric, traffic, DNS, beaconing, security policy, reconnaissance, service health, infrastructure health, business dependency impact, and cross-domain incident, plus shared operational/evidence/recovery recipes.

Every executable search requires index, sourcetype, run ID, and bounded-time placeholders. Unbounded joins are rejected. Recipes declare expected shape, required/optional fields, evidence, drilldowns, portability, and validation requirements.

## 6. Eligible scenario inventory

Generic discovery produced 16 honest entries:

- 14 `ELIGIBLE`: five Cisco Golden references, six Phase 9 security references, and three Phase 10 industry references.
- 2 `RESEARCH_REQUIRED`: `rfc5424-link-state-lifecycle` and the raw `test-correlated-interface-degradation` runtime context because their own scenario maturity is `NOT_ESTABLISHED`.

`C100-SP-001` remains eligible through its verified Cisco definition and binds to the existing `test-correlated-interface-degradation` runtime; no new identifier was invented.

## 7. Scenario-to-dashboard validation matrix

| Dashboard | Scenario/runtime | Recipes | SPL | Data | Visual | Export |
|---|---|---:|---|---|---|---|
| `scenario-c100-ent-001` | `C100-ENT-001` | 8 | PASS | PASS | PENDING | PASS |
| `scenario-c100-sp-001` | `C100-SP-001` / `test-correlated-interface-degradation` | 10 | PASS | PASS | PENDING | PASS |
| `scenario-c100-dc-001` | `C100-DC-001` | 9 | PASS | PASS | PENDING | PASS |
| `scenario-c100-sec-001` | `C100-SEC-001` | 9 | PASS | PASS | PENDING | PASS |
| `scenario-c100-cri-002` | `C100-CRI-002` | 11 | PASS | PASS | PENDING | PASS |
| `scenario-sec-p9-a-traffic-flood` | `SEC-P9-A-TRAFFIC-FLOOD` | 10 | PASS | PASS | PENDING | PASS |
| `scenario-sec-p9-b-dns-anomaly` | `SEC-P9-B-DNS-ANOMALY` | 10 | PASS | PASS | PENDING | PASS |
| `scenario-sec-p9-c-beaconing` | `SEC-P9-C-BEACONING` | 14 | PASS | PASS | PENDING | PASS |
| `scenario-sec-p9-d-internal-recon` | `SEC-P9-D-INTERNAL-RECON` | 11 | PASS | PASS | PENDING | PASS |
| `scenario-sec-p9-e-dns-tunnel` | `SEC-P9-E-DNS-TUNNEL` | 13 | PASS | PASS | PENDING | PASS |
| `scenario-sec-p9-f-cross-source` | `SEC-P9-F-CROSS-SOURCE` | 14 | PASS | PASS | PENDING | PASS |
| `industry-financial-services` | `C100-CRI-002` | 14 | PASS | PASS | PENDING | PASS |
| `industry-healthcare` | `C100-ENT-001` | 10 | PASS | PASS | PENDING | PASS |
| `industry-manufacturing` | `C100-DC-001` | 11 | PASS | PASS | PENDING | PASS |

Fresh matrix artifact: `.artifacts/phase10/backend-regression/phase11-dashboard-live-validation.json`.

The backing `test-correlated-interface-degradation` run reported `DEGRADED` because not every scenario-level source was observed in that combined run. The C100-SP dashboard searches still returned valid run-scoped data and expected shapes. This partial source observation is exposed rather than converted into a false scenario-level success.

## 8. NOC, Engineer, and Evidence perspectives

All perspectives consume the same Dashboard Pack, scenario ID, and run ID.

- NOC presents status, affected entities, topology, critical observed KPIs, incident timeline, and recovery.
- Engineer presents source detail, correlated telemetry, technical trends, investigation SPL, and related entities.
- Evidence presents Native/Splunk/NetSpout boundaries, provenance, observed fields, expected shape, validation, CIM, and portability.

No unobserved metric is presented as observed. Unknown CIM remains `NOT_ESTABLISHED`.

## 9. Topology integration

Topology is rendered from the existing pack/entity graph and relationship metadata. Entity and relationship selection, affected state/path, dependency direction, run context, and drilldown tokens are derived from that graph. There is no per-scenario hard-coded topology and no second business graph.

## 10. SPL generation and validation

The engine resolves the configured destination, index, sourcetypes, run ID, and verified fields before rendering bounded SPL. Live validation executes each executable panel against fresh run-scoped data, records returned fields, checks the expected shape and scenario relevance, and persists separate evidence.

The IPFIX forwarder was corrected to use collector receipt time for HEC indexing while preserving modeled device time in the raw event. HEC HTTP responses now require Splunk response code 0, not only HTTP 200. Recipe fields use observed `dst_addr`/`dst_port`; JSON extraction uses `spath`.

NetSpout-specific and production-portable classifications remain separate. Current executable recipes are explicitly NetSpout-specific unless reviewed otherwise.

## 11. Dashboard maturity

Independent states are:

`NOT_STARTED → GENERATED → SPL_VALIDATED → DATA_VALIDATED → VISUALLY_VALIDATED → DASHBOARD_READY`

`DEPENDENCY_BLOCKED` and `VALIDATION_FAILED` represent non-success states. Evidence is persisted independently from scenario maturity. Current totals are 14 generated, 14 SPL validated, 14 data validated, 0 visually validated, and 0 Dashboard Ready.

## 12. Visualization registry

The registry contains 11 visualizations. Native NetSpout topology plus documented Dashboard Studio table, single-value, line, area, and column types are available. Network Diagram, 3D Graph, Topology, Flow Map, and Sankey dependencies remain `NOT_VERIFIED`; each fails gracefully to a native/table fallback. No Splunkbase installation or Dashboard Studio compatibility is assumed.

## 13. Drilldowns and filtering

Stable tokens cover entity, relationship, source, phase/timeline, security event, investigation, and business dependency semantics. Scenario and run IDs remain in the URL. Filters can be cleared without changing the selected scenario. Drilldown fields are validated against recipe and observed-field metadata; unavailable fields remain unverified.

## 14. Advanced Inspector

The Inspector implements Overview, Visualization, Data, SPL, Fields, CIM, Tokens, Dependencies, and Validation tabs. It displays the effective/fallback visualization, bounded query, expected and observed fields, portability, token mapping, dependencies, and validation evidence. Unknown data is labeled `NOT VERIFIED`; CIM is `NOT ESTABLISHED`.

## 15. Dashboard Studio export and deployment

A separate adapter emits Splunk Dashboard Studio JSON and validates structure, visualization types, data sources/searches, tokens, time bounds, layout, drilldown field references, and dependencies. All 14 eligible exports validated.

Deployment output is preview-only and shows target, name/identifier, permissions, dependencies, workload, validation status, and `overwrite_allowed: false`. No dashboard was deployed. Production deployment and automatic overwrite are prohibited.

## 16. NOC Wallboard

The full-screen wallboard is a presentation of the selected pack's NOC perspective. It shares incident state, topology, KPIs, affected entities, and recovery data with the normal dashboard and introduces no second data model.

## 17. Gate 13E root cause and result

Root cause: the legacy dispatcher began HEC work while Splunk's container process existed but the HEC listener was not yet ready. Environment password fallback was also incomplete, diagnostics obscured dispatch failures, and HTTPS could downgrade to HTTP.

Fix:

- bounded HEC `/health` readiness with exponential backoff;
- readiness used by preflight and dispatch;
- documented environment credential fallbacks;
- no automatic HTTPS-to-HTTP downgrade;
- detailed dispatch errors;
- TLS bypass restricted to explicit loopback lab endpoints;
- unit fixture updated to validate the health response body.

Controlled Docker restart results:

- Run 1: 6 passed, 13 warnings in 15.11s.
- Immediate restart repeat: 6 passed, 13 warnings in 49.61s.

No arbitrary sleeps, disabled authentication, weakened assertions, or global TLS bypass were introduced.

## 18. Cisco Golden validation

All five references generated distinct packs and passed dashboard SPL, expected-shape, perspective, drilldown, and export checks. C100-SP's backing combined runtime had partial source observation as disclosed in section 7; Gate 12F and Gate 13E independently passed their SNMP and gNMI acceptance gates.

## 19. Security scenario validation

All six discovered Phase 9 IDs passed dashboard SPL, data-shape, perspective, drilldown, and export validation:

`SEC-P9-A-TRAFFIC-FLOOD`, `SEC-P9-B-DNS-ANOMALY`, `SEC-P9-C-BEACONING`, `SEC-P9-D-INTERNAL-RECON`, `SEC-P9-E-DNS-TUNNEL`, and `SEC-P9-F-CROSS-SOURCE`.

## 20. Industry validation

Financial Services, Healthcare, and Manufacturing passed dashboard SPL, data-shape, perspective, drilldown, and export validation while reusing their authoritative Cisco runtime references. Business effects remain `MODELED`; dashboards do not promote them to observed outcomes.

## 21. Docker journeys

The authorized local lab exercised fresh Cisco, security, and industry runs, native receivers/collectors, HEC dispatch, authenticated Splunk searches, field inspection, expected-shape checks, evidence persistence, and export validation. The flow collector and forwarder shared the existing acceptance volume; no historical volume was replaced.

## 22. Test results

- Focused Phase 11/backend: 49 passed, 5 warnings; final Phase 11 module: 18 passed, 5 warnings.
- Cisco/Phase 8C/Phase 9/Phase 10 regressions: 78 passed, 5 warnings.
- Gate 12F: 13 passed, 44 warnings.
- Gate 13E: 6/6 passed twice after controlled restarts.
- Live dashboard matrix: 14/14 generated, 14/14 SPL validated, 14/14 data validated, 14/14 export validated.
- Source/mirror audit: passed; 20 catalog JSON files verified in every mirror.
- Full backend regression: 614 passed, 1 skipped, 67 subtests passed; warnings are inherited deprecations.
- Frontend build: passed with inherited bundle-size warning.
- Frontend lint: passed with 13 inherited warnings and no Phase 11 warning.
- Full Playwright: 30 passed, 6 skipped.
- Phase 11 Playwright: 3 passed, including all 14 eligible contexts.

The first unguarded broad runs exposed two actionable test-environment issues: absent `pygnmi` and a stale HEC health mock. The dependency and mock were corrected. Full Playwright also exposed an ambiguous Phase 8 Cisco selector; it is now scoped to the scenario list.

## 23. Screenshot review

Current screenshots cover Gallery/research state, NOC perspective, Advanced Inspector, and NOC Wallboard under `frontend/.artifacts/phase10/backend-regression/screenshots/phase11-dashboard/`. Review confirmed scenario/run persistence, distinct contexts, three perspectives, evidence labels, inspector disclosure, fallbacks, and wallboard readability.

This confirms implementation integrity only. It is not acceptance against the missing Dashboard Extension V2 source.

## 24. Artifact protection

Protected artifacts changed from 629 to 634 files solely through the five synchronized `dashboard_recipes.json` additions. Existing protected files had zero modifications or deletions. Current-run evidence is isolated under ignored artifact directories; historical evidence was not overwritten.

## 25. Security and privacy

- No hardcoded credential was added; live validation and deployment preview consume environment-provided credentials.
- No credential, token, password, private key, or authenticated connection string is serialized in source, reports, exports, screenshots, or evidence.
- No certificate material was introduced or loaded by Phase 11.
- The existing self-signed TLS exception is limited to the authorized loopback lab; non-loopback and production verification remains enabled. Any production certificate still requires expiry, key-strength, signature, issuer, and trust verification.
- No cryptographic algorithm was introduced, deprecated algorithm enabled, or protocol security weakened.
- No customer data, production capture, or production topology was used.

## 26. Provenance and licensing

The implementation references existing NetSpout contracts and public Splunk Dashboard Studio definition documentation. It copies no proprietary dashboard asset, unlicensed visualization code, vendor capture, or third-party dataset. Optional Splunkbase visualizations are metadata-only `NOT_VERIFIED` dependencies and are not bundled.

## 27. Limitations

- V2 design handoff/source is unavailable; visual acceptance and Dashboard Ready promotion are pending.
- Optional third-party visualizations are not installed or compatibility-verified.
- CIM remains `NOT_ESTABLISHED`.
- C100-SP's combined backing run had partial scenario-level source observation, although dashboard searches and shapes validated.
- Export validation is not deployment validation; deployment remains preview-only.
- Production-portable SPL requires deployment-specific review and identifiers.

## 28. Phase 12 readiness

**NOT READY** for Phase 12 acceptance because Phase 11 visual-design acceptance remains blocked by the missing V2 handoff. The engineering foundation is recoverable and ready for visual reconciliation when that source is supplied.

No merge, release, production deployment, or Phase 12 work was performed.
