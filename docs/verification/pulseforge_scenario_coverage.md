# PulseForge Scenario Coverage

Generated 2026-10-30 by `scripts/generate_coverage_report.py`. Catalog presence, runnability, live Splunk verification and maturity are separate columns of evidence.

| Measure | Count |
|---|---|
| Unique catalog scenarios | 58 |
| Runnable (ScenarioRunner or authentic pack) | 43 (runner 17, packs 26) |
| Contract only (not runnable) | 15 |
| Live-verified in Splunk (pack scenario run, per-phase counts match, no leak) | 5 |
| E2E_VALIDATED (catalog maturity) | 4 |
| GOLDEN_PATH_CERTIFIED (catalog maturity) | 13 |
| Dashboard-verified (DASHBOARD_READY evidence) | 1 |
| Detection-verified (stored evidence) | 1 |

Unified-generation scenarios (25, `/api/generation/capabilities`) are not catalog rows and are counted separately in the Explorer.

| Maturity (catalog value, not upgraded) | Count |
|---|---|
| CONTRACTED | 39 |
| GOLDEN_PATH_CERTIFIED | 13 |
| E2E_VALIDATED | 4 |
| FORMAT_VALIDATED | 2 |

## Maturity gates (unchanged; definitions from docs/architecture/NETSPOUT_CANONICAL_SCENARIO_REGISTRY.md)

| Tier | Gate | Count now |
|---|---|---|
| GOLDEN_PATH_CERTIFIED | Independently verified through live Splunk acceptance with 100% telemetry observation completeness, zero developer knowledge, clean validation | 13 |
| E2E_VALIDATED | Wired to multi-vendor topology graphs with deterministic simulation runners and passing contract rules; pending independent acceptance retest | 4 |
| FORMAT_VALIDATED | Baseline traffic emitting compliant wire formats (governed counter, pinned) | 2 |
| CONTRACTED | Blueprint with schema definitions, expected observations; implementation may be absent | 39 |

No scenario was promoted in this pass. The 26 authentic observation packs are `CONTRACTED`: they have live byte-equality and per-phase indexing evidence (batch 1-6 result files) but are not wired to topology graphs, have no independent acceptance retest, no dashboard and no detection, so they meet none of the higher gates. Byte-equal bytes or successful ingestion never promote a scenario.

| Group | Scenarios | Evidence now | Missing for the next tier |
|---|---|---|---|
| Authentic packs (wave*, ub1-ub6) | 26 | byte-equal families; per-phase counts for 5 packs | topology wiring, runner determinism contract, independent acceptance retest |
| ScenarioRunner scenarios | 17 | GOLDEN 13 / E2E 4 per catalog | E2E_VALIDATED ones need the independent acceptance retest |
| Contract-only | 15 | none | any executable telemetry; no Run action is offered |

Pack scenarios stay `CONTRACTED`: `FORMAT_VALIDATED` is a governed counter pinned at 2 and live byte equality is not E2E validation.

Dashboard-verified: SEC-P9-B-DNS-ANOMALY (unified generation; Dashboard Studio view pulseforge_dns_anomaly_studio)

Detection-verified: React2Shell / d36459b1-7901-401a-a67e-44426c15b168 (saved search fired on Splunk's scheduler). Not Enterprise Security, CIM or Cisco TA.

## Scenarios by approved industry (editorial mapping unless an industry pack binds it)

| Industry | Mapped scenarios | Runnable |
|---|---|---|
| Banking and Financial Services | 2 | 1 |
| Healthcare | 1 | 0 |
| Retail and E-commerce | 1 | 1 |
| Manufacturing | 4 | 2 |
| Energy and Utilities | 3 | 2 |
| Telecommunications | 4 | 2 |
| Government and Public Sector | 1 | 0 |
| Transportation and Logistics | 0 | 0 |
| Education | 2 | 2 |
| Technology and SaaS | 14 | 3 |
| Media and Entertainment | 0 | 0 |
| Hospitality and Travel | 2 | 2 |
| Aerospace and Defense | 0 | 0 |
| Legal, Compliance and Professional Services | 2 | 2 |
| Agriculture and Agritech | 1 | 0 |
| Real Estate, PropTech and Construction | 0 | 0 |
| Insurance and InsurTech | 0 | 0 |
| Non-Profit, NGOs and Global Aid | 0 | 0 |

Live-verified scenarios: ub5_cisco_change_induced_outage, ub5_cisco_nac_radius_outage, ub5_cisco_platform_health_degradation, ub6_catalyst_wireless_rogue_threat, ub6_sdwan_utd_threat_pipeline
