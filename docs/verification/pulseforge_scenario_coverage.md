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
| Banking and Financial Services | 3 | 1 |
| Healthcare | 2 | 0 |
| Retail and E-commerce | 3 | 1 |
| Manufacturing | 4 | 2 |
| Energy and Utilities | 3 | 2 |
| Telecommunications | 14 | 2 |
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

## Unique scenario inventory (the Explorer's own view; nothing counted twice)

| Measure | Count |
|---|---|
| Unique operational definitions (executable + documented candidates) | 336 |
| Runnable (a real generator and Run path exist) | 112 |
| Cataloged candidates only (documented; no generator or contract; never runnable) | 209 |
| Contract-only (catalog contracts without executable telemetry; no Run action) | 15 |
| Live-verified in Splunk (counts and, for incident packs, mstats values checked independently) | 50 |
| Dashboard-verified | 1 |
| Security analytic stories (reference stories; NOT counted as executable) | 365 |
| Security stories with a runnable workflow (runtime-approved detection) | 1 |
| Detection-verified | 1 |
| Duplicate candidates removed (already represented by an executable entry) | 0 |

By engine: cataloged 209, incident_pack 37, replay_pack 7, scenario_pack 26, scenario_runner 32, unified_generation 25. By tier: CATALOGED 209, CERTIFIED 18, CONTRACTED 83, FORMAT_VALIDATED 2, NOT_ESTABLISHED 1, VALIDATED 23.

Incident packs (27 network + 10 telecom) emit NetSpout-defined MODELED telemetry (`netspout:*`), not vendor-native formats; they stay CONTRACTED. Cataloged candidates come from `catalog/scenario_candidates.json` (MIT community use-case catalog pinned to a commit, plus Cisco 100 definitions that are not execution-enabled).

## Replay packs (scenario packs on the continuous-replay engine)

Each pack mixes recorded (authentic) phases and/or existing native packs. Tier stays CONTRACTED: events indexing is evidence of delivery, not E2E validation, a dashboard or a detection. Independent recordings are aligned in time only (TEMPORAL_ONLY).

| Pack | Category | Source mode | Phases | Correlation | Indexed-verified (isolated lab) | Dashboard | Detection | Industries (editorial) |
|---|---|---|---|---|---|---|---|---|
| rp_linux_credential_access | SOC | replay | 2 | TEMPORAL_ONLY | YES | none | none | technology-saas, government-public-sector, banking-financial-services |
| rp_cloud_control_plane_activity | SOC | replay | 1 | TEMPORAL_ONLY | YES | none | none | technology-saas, insurance-insurtech, media-entertainment, nonprofit-ngo-global-aid, real-estate-proptech-construction |
| rp_windows_endpoint_process_chain | SOC | replay | 1 | TEMPORAL_ONLY | YES | none | none | healthcare, manufacturing, education, legal-compliance-professional-services, energy-utilities, agriculture-agritech |
| rp_web_exploitation_recordings | SOC | replay | 3 | TEMPORAL_ONLY | YES | none | none | retail-ecommerce, hospitality-travel, government-public-sector, nonprofit-ngo-global-aid, real-estate-proptech-construction |
| rp_edr_and_cloud_activity | SOC | replay | 2 | TEMPORAL_ONLY | YES | none | none | banking-financial-services, aerospace-defense |
| rp_agentic_ai_mcp_runtime_hybrid | AI_SECURITY | both | 2 | MIXED_TEMPORAL_ONLY_BETWEEN_SOURCES | YES | none | none | technology-saas, legal-compliance-professional-services |
| rp_workload_sysmon_ebpf_hybrid | SOC | both | 2 | MIXED_TEMPORAL_ONLY_BETWEEN_SOURCES | YES | none | none | technology-saas, telecommunications, transportation-logistics |

Replay-verified canonical sourcetypes (9): auditd, aws:cloudtrail, crowdstrike:events:sensor, crushftp:sessionlogs, linux_messages_syslog, mcp:jsonrpc, nginx:access, suricata, sysmon:linux. Recorded sources whose sourcetype is not a catalog canonical name (1): XmlWinEventLog (replayable, not counted as coverage).

Replay sample corpus: 10 vendored authentic recordings (`catalog/replay_sources.json`). The Ollama server log was excluded because it mixes three timestamp formats. SA-Eventgen was not evaluated against its version-specific spec (not installed in any lab); the PulseForge replay engine was reused.

## 18-industry coverage matrix

Columns are separate evidence: documented is not runnable, runnable is not verified, verified is not TA-parsed or detected. Mappings are editorial unless the source labels the industry (`*` in the Explorer).

| Industry | Documented | Cataloged only | Runnable | Live-verified | Dashboard-verified | Curated stories | Stories runnable | Detections verified | Named sourcetypes without a native generator | Government subdomains covered |
|---|---|---|---|---|---|---|---|---|---|---|
| Banking and Financial Services | 14 | 9 | 5 | 3 | 0 | 4 | 0 | 0 | 0 | - |
| Healthcare | 12 | 9 | 3 | 2 | 0 | 4 | 0 | 0 | 0 | - |
| Retail and E-commerce | 10 | 6 | 4 | 3 | 0 | 1 | 0 | 0 | 1 | - |
| Manufacturing | 16 | 11 | 4 | 1 | 0 | 4 | 0 | 0 | 1 | - |
| Energy and Utilities | 20 | 16 | 4 | 1 | 0 | 4 | 0 | 0 | 0 | - |
| Telecommunications | 41 | 27 | 13 | 11 | 0 | 4 | 0 | 0 | 2 | - |
| Government and Public Sector | 23 | 20 | 3 | 2 | 0 | 4 | 0 | 0 | 0 | critical-infrastructure, national-security, state-local |
| Transportation and Logistics | 12 | 11 | 1 | 1 | 0 | 3 | 0 | 0 | 0 | - |
| Education | 12 | 9 | 3 | 1 | 0 | 4 | 0 | 0 | 1 | - |
| Technology and SaaS | 23 | 5 | 18 | 4 | 0 | 0 | 0 | 0 | 1 | - |
| Media and Entertainment | 5 | 4 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | - |
| Hospitality and Travel | 9 | 6 | 3 | 1 | 0 | 1 | 0 | 0 | 1 | - |
| Aerospace and Defense | 5 | 4 | 1 | 1 | 0 | 3 | 0 | 0 | 0 | - |
| Legal, Compliance and Professional Services | 9 | 5 | 4 | 2 | 0 | 1 | 0 | 0 | 1 | - |
| Agriculture and Agritech | 5 | 3 | 1 | 1 | 0 | 0 | 0 | 0 | 1 | - |
| Real Estate, PropTech and Construction | 7 | 5 | 2 | 2 | 0 | 1 | 0 | 0 | 0 | - |
| Insurance and InsurTech | 7 | 6 | 1 | 1 | 0 | 1 | 0 | 0 | 0 | - |
| Non-Profit, NGOs and Global Aid | 7 | 5 | 2 | 2 | 0 | 0 | 0 | 0 | 0 | - |

Curated stories are Splunk Analytic Stories whose own text names the sector as a threat target (basis NARRATIVE_TARGET_SECTOR) and whose original research.splunk.com page was verified (HTTP 200); they are NOT executable: only a story with a runtime-approved detection is runnable, and the single detection-verified item (React2Shell) is not curated to an industry. Technology/SaaS, media, non-profit and agriculture have no story whose text names the sector and whose link resolves. Government subdomains: State/Local, National Security and Critical Infrastructure have editorial or source-labeled entries; **Federal Civilian and Compliance has none** (no authoritative source selected). TA validation is not tracked per industry: only Windows/Sysmon channels were TA-checked (see the TA matrix). Industries whose documented scenarios have no runnable counterpart (for example transportation, media, aerospace/defense, agriculture, real estate, insurance, non-profit) need authentic telemetry sources before they can become runnable.
