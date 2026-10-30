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
| Unique operational definitions (executable + documented candidates) | 362 |
| Runnable (a real generator and Run path exist) | 138 |
| Cataloged candidates only (documented; no generator or contract; never runnable) | 209 |
| Contract-only (catalog contracts without executable telemetry; no Run action) | 15 |
| Live-verified in Splunk (counts and, for incident packs, mstats values checked independently) | 76 |
| Dashboard-verified | 1 |
| Security analytic stories (reference stories; NOT counted as executable) | 365 |
| Security stories with a runnable workflow (runtime-approved detection) | 1 |
| Detection-verified | 1 |
| Duplicate candidates removed (already represented by an executable entry) | 0 |

By engine: cataloged 209, incident_pack 37, replay_pack 33, scenario_pack 26, scenario_runner 32, unified_generation 25. By tier: CATALOGED 209, CERTIFIED 18, CONTRACTED 109, FORMAT_VALIDATED 2, NOT_ESTABLISHED 1, VALIDATED 23.

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
| ind_bank_account_takeover_resilience | SOC | native | 3 | NATIVE_CORRELATED_WITHIN_PACKS_TEMPORAL_BETWEEN | YES | none | none | banking-financial-services |
| ind_bank_payments_edge_defense | SOC | native | 2 | NATIVE_CORRELATED_WITHIN_PACKS_TEMPORAL_BETWEEN | YES | none | none | banking-financial-services |
| ind_telco_change_induced_outage | NOC | native | 2 | NATIVE_CORRELATED_WITHIN_PACKS_TEMPORAL_BETWEEN | YES | none | none | telecommunications |
| ind_telco_access_and_wireless_health | NOC | native | 3 | NATIVE_CORRELATED_WITHIN_PACKS_TEMPORAL_BETWEEN | YES | none | none | telecommunications |
| ind_health_ehr_ransomware_readiness | SOC | native | 3 | NATIVE_CORRELATED_WITHIN_PACKS_TEMPORAL_BETWEEN | YES | none | none | healthcare |
| ind_health_clinical_network_edge | NOC | native | 2 | NATIVE_CORRELATED_WITHIN_PACKS_TEMPORAL_BETWEEN | YES | none | none | healthcare |
| ind_mfg_it_ot_convergence | SOC | native | 3 | NATIVE_CORRELATED_WITHIN_PACKS_TEMPORAL_BETWEEN | YES | none | none | manufacturing |
| ind_mfg_plant_network_health | NOC | native | 2 | NATIVE_CORRELATED_WITHIN_PACKS_TEMPORAL_BETWEEN | YES | none | none | manufacturing |
| ind_energy_substation_edge_observation | NOC | native | 2 | NATIVE_CORRELATED_WITHIN_PACKS_TEMPORAL_BETWEEN | YES | none | none | energy-utilities |
| ind_energy_scada_proxy_intrusion | SOC | native | 2 | NATIVE_CORRELATED_WITHIN_PACKS_TEMPORAL_BETWEEN | YES | none | none | energy-utilities |
| ind_insurance_claims_platform_audit | SOC | native | 3 | NATIVE_CORRELATED_WITHIN_PACKS_TEMPORAL_BETWEEN | YES | none | none | insurance-insurtech |
| ind_insurance_underwriting_exposure | ITOPS | native | 3 | NATIVE_CORRELATED_WITHIN_PACKS_TEMPORAL_BETWEEN | YES | none | none | insurance-insurtech |
| ind_gov_citizen_identity_attack | SOC | native | 3 | NATIVE_CORRELATED_WITHIN_PACKS_TEMPORAL_BETWEEN | YES | none | none | government-public-sector |
| ind_gov_agency_mail_exfiltration | SOC | native | 2 | NATIVE_CORRELATED_WITHIN_PACKS_TEMPORAL_BETWEEN | YES | none | none | government-public-sector |
| ind_retail_pos_edge_defense | SOC | native | 2 | NATIVE_CORRELATED_WITHIN_PACKS_TEMPORAL_BETWEEN | YES | none | none | retail-ecommerce |
| ind_retail_ecommerce_cloud_recon | SOC | native | 2 | NATIVE_CORRELATED_WITHIN_PACKS_TEMPORAL_BETWEEN | YES | none | none | retail-ecommerce |
| ind_edu_campus_identity_and_collab | SOC | native | 2 | NATIVE_CORRELATED_WITHIN_PACKS_TEMPORAL_BETWEEN | YES | none | none | education |
| ind_saas_platform_runtime_attack | SOC | native | 3 | NATIVE_CORRELATED_WITHIN_PACKS_TEMPORAL_BETWEEN | YES | none | none | technology-saas |
| ind_media_content_delivery_exfil | SOC | native | 1 | NATIVE_CORRELATED | YES | none | none | media-entertainment |
| ind_hospitality_guest_network_defense | SOC | native | 2 | NATIVE_CORRELATED_WITHIN_PACKS_TEMPORAL_BETWEEN | YES | none | none | hospitality-travel |
| ind_aero_defense_endpoint_c2 | SOC | native | 3 | NATIVE_CORRELATED_WITHIN_PACKS_TEMPORAL_BETWEEN | YES | none | none | aerospace-defense |
| ind_legal_matter_data_exfiltration | SOC | native | 2 | NATIVE_CORRELATED_WITHIN_PACKS_TEMPORAL_BETWEEN | YES | none | none | legal-compliance-professional-services |
| ind_agri_edge_gateway_health | ITOPS | native | 2 | NATIVE_CORRELATED_WITHIN_PACKS_TEMPORAL_BETWEEN | YES | none | none | agriculture-agritech |
| ind_realestate_building_exposure | ITOPS | native | 2 | NATIVE_CORRELATED_WITHIN_PACKS_TEMPORAL_BETWEEN | YES | none | none | real-estate-proptech-construction |
| ind_nonprofit_donor_platform_attack | SOC | native | 2 | NATIVE_CORRELATED_WITHIN_PACKS_TEMPORAL_BETWEEN | YES | none | none | nonprofit-ngo-global-aid |
| ind_transport_fleet_network_change | NOC | native | 2 | NATIVE_CORRELATED_WITHIN_PACKS_TEMPORAL_BETWEEN | YES | none | none | transportation-logistics |

Replay-verified canonical sourcetypes (9): auditd, aws:cloudtrail, crowdstrike:events:sensor, crushftp:sessionlogs, linux_messages_syslog, mcp:jsonrpc, nginx:access, suricata, sysmon:linux. Recorded sources whose sourcetype is not a catalog canonical name (1): XmlWinEventLog (replayable, not counted as coverage).

## Industry scenario packs added 2026-10-30 (26; all native sequences of existing authentic packs, run by the replay engine)

Framing by industry/sub-industry is editorial; telemetry and in-pack correlation are authentic; constituent packs are related by time only. Maturity CONTRACTED. `Panels` = every panel query returned rows for a live run in the isolated lab (not a Dashboard Studio object). Detections are not claimed (no add-on, CIM or ES content installed).

| Scenario | Industry / sub-industry | Kind | Constituent native packs | Sourcetypes | Indexed | Panels | Dashboard (Studio view) | Dashboard maturity |
|---|---|---|---|---|---|---|---|---|
| ind_bank_account_takeover_resilience | banking-financial-services / Retail banking | security | wave2_ws_credential_compromise_chain, wave2_cloud_identity_sso_hunt, ub2_database_backup_integrity | 13 | YES | YES | pf_ind_bank_account_takeover_resilience | DASHBOARD_DATA_VALIDATED |
| ind_bank_payments_edge_defense | banking-financial-services / Payments and e-banking | security | ub3_multivendor_edge_observation, wave2_aws_recon_escalation | 6 | YES | YES | pf_ind_bank_payments_edge_defense | DASHBOARD_DATA_VALIDATED |
| ind_telco_change_induced_outage | telecommunications / Enterprise WAN and SD-WAN services | operational | ub5_cisco_change_induced_outage, ub6_sdwan_utd_threat_pipeline | 15 | YES | YES | pf_ind_telco_change_induced_outage | DASHBOARD_VISUALLY_VERIFIED |
| ind_telco_access_and_wireless_health | telecommunications / Access, wireless and subscriber edge | operational | ub5_cisco_nac_radius_outage, ub5_cisco_platform_health_degradation, ub6_catalyst_wireless_rogue_threat | 16 | YES | YES | pf_ind_telco_access_and_wireless_health | DASHBOARD_DATA_VALIDATED |
| ind_health_ehr_ransomware_readiness | healthcare / Hospital systems and EHR | security | wave2_ws_credential_compromise_chain, ub2_database_backup_integrity, ub3_identity_runtime_audit | 12 | YES | YES | pf_ind_health_ehr_ransomware_readiness | DASHBOARD_DATA_VALIDATED |
| ind_health_clinical_network_edge | healthcare / Clinical network and medical IoT edge | operational | wave3_ebpf_workload_hunt, ub6_catalyst_wireless_rogue_threat | 13 | YES | YES | pf_ind_health_clinical_network_edge | DASHBOARD_DATA_VALIDATED |
| ind_mfg_it_ot_convergence | manufacturing / Discrete manufacturing plant | security | ub1_ot_proxy_host_hunt, ub2_ot_edge_routing_observation, wave2_c2_callback_detection | 10 | YES | YES | pf_ind_mfg_it_ot_convergence | DASHBOARD_DATA_VALIDATED |
| ind_mfg_plant_network_health | manufacturing / Plant network operations | operational | ub5_cisco_platform_health_degradation, ub5_cisco_change_induced_outage | 19 | YES | YES | pf_ind_mfg_plant_network_health | DASHBOARD_DATA_VALIDATED |
| ind_energy_substation_edge_observation | energy-utilities / Electric transmission and substations | operational | ub2_ot_edge_routing_observation, ub5_cisco_platform_health_degradation | 11 | YES | YES | pf_ind_energy_substation_edge_observation | DASHBOARD_DATA_VALIDATED |
| ind_energy_scada_proxy_intrusion | energy-utilities / Utility control systems | security | ub1_ot_proxy_host_hunt, wave2_c2_callback_detection | 6 | YES | YES | pf_ind_energy_scada_proxy_intrusion | DASHBOARD_DATA_VALIDATED |
| ind_insurance_claims_platform_audit | insurance-insurtech / Claims and policy administration | security | ub4_saas_collaboration_audit, ub3_database_message_audit, wave3_cloudmail_exfil | 13 | YES | YES | pf_ind_insurance_claims_platform_audit | DASHBOARD_DATA_VALIDATED |
| ind_insurance_underwriting_exposure | insurance-insurtech / Underwriting analytics and data platforms | operational | ub4_exposure_infra_logging, ub2_cloud_identity_mail_hunt, ub3_identity_runtime_audit | 11 | YES | YES | pf_ind_insurance_underwriting_exposure | DASHBOARD_DATA_VALIDATED |
| ind_gov_citizen_identity_attack | government-public-sector / State and local government | security | wave2_cloud_identity_sso_hunt, wave2_aws_recon_escalation, ub3_identity_runtime_audit | 11 | YES | YES | pf_ind_gov_citizen_identity_attack | DASHBOARD_VISUALLY_VERIFIED |
| ind_gov_agency_mail_exfiltration | government-public-sector / Federal civilian and compliance (framing only) | security | wave3_cloudmail_exfil, ub4_endpoint_threat_pipeline | 13 | YES | YES | pf_ind_gov_agency_mail_exfiltration | DASHBOARD_DATA_VALIDATED |
| ind_retail_pos_edge_defense | retail-ecommerce / Stores and point of sale | security | ub3_multivendor_edge_observation, ub4_endpoint_threat_pipeline | 9 | YES | YES | pf_ind_retail_pos_edge_defense | DASHBOARD_DATA_VALIDATED |
| ind_retail_ecommerce_cloud_recon | retail-ecommerce / E-commerce platform | security | wave2_aws_recon_escalation, ub4_exposure_infra_logging | 6 | YES | YES | pf_ind_retail_ecommerce_cloud_recon | DASHBOARD_DATA_VALIDATED |
| ind_edu_campus_identity_and_collab | education / Higher education | security | wave2_cloud_identity_sso_hunt, ub4_saas_collaboration_audit | 8 | YES | YES | pf_ind_edu_campus_identity_and_collab | DASHBOARD_DATA_VALIDATED |
| ind_saas_platform_runtime_attack | technology-saas / Cloud-native software platform | security | wave2_k8s_container_escape, ub4_saas_collaboration_audit, ub4_exposure_infra_logging | 11 | YES | YES | pf_ind_saas_platform_runtime_attack | DASHBOARD_DATA_VALIDATED |
| ind_media_content_delivery_exfil | media-entertainment / Streaming and content delivery | security | wave3_cloudmail_exfil | 8 | YES | YES | pf_ind_media_content_delivery_exfil | DASHBOARD_DATA_VALIDATED |
| ind_hospitality_guest_network_defense | hospitality-travel / Hotels and guest networks | security | ub3_multivendor_edge_observation, wave2_cloud_identity_sso_hunt | 9 | YES | YES | pf_ind_hospitality_guest_network_defense | DASHBOARD_DATA_VALIDATED |
| ind_aero_defense_endpoint_c2 | aerospace-defense / Defense contractor | security | wave2_c2_callback_detection, ub4_endpoint_threat_pipeline, ub3_identity_runtime_audit | 11 | YES | YES | pf_ind_aero_defense_endpoint_c2 | DASHBOARD_DATA_VALIDATED |
| ind_legal_matter_data_exfiltration | legal-compliance-professional-services / Law firms and professional services | security | wave3_cloudmail_exfil, ub2_cloud_identity_mail_hunt | 11 | YES | YES | pf_ind_legal_matter_data_exfiltration | DASHBOARD_DATA_VALIDATED |
| ind_agri_edge_gateway_health | agriculture-agritech / Precision farming and processing | operational | ub2_ot_edge_routing_observation, wave2_linux_auth_anomaly | 7 | YES | YES | pf_ind_agri_edge_gateway_health | DASHBOARD_VISUALLY_VERIFIED |
| ind_realestate_building_exposure | real-estate-proptech-construction / Commercial property and construction | operational | ub4_exposure_infra_logging, ub4_saas_collaboration_audit | 7 | YES | YES | pf_ind_realestate_building_exposure | DASHBOARD_DATA_VALIDATED |
| ind_nonprofit_donor_platform_attack | nonprofit-ngo-global-aid / Humanitarian and donor platforms | security | wave2_cloud_identity_sso_hunt, wave3_cloudmail_exfil | 13 | YES | YES | pf_ind_nonprofit_donor_platform_attack | DASHBOARD_DATA_VALIDATED |
| ind_transport_fleet_network_change | transportation-logistics / Logistics and fleet networks | operational | ub5_cisco_change_induced_outage, ub2_ot_edge_routing_observation | 16 | YES | YES | pf_ind_transport_fleet_network_change | DASHBOARD_DATA_VALIDATED |

Dashboard maturity is assembled from stored evidence (`docs/verification/evidence/dashboards/`): IMPLEMENTED = installed in Splunk and read back identical; DATA_VALIDATED = every data source populated with the run context, KPIs equal independent SPL, tokens bound, drilldowns return rows; VISUALLY_VERIFIED = also opened in Splunk Web with the run context and the final screenshot inspected. Installed-and-opened is separate from visually verified. All 33 packs (26 industry + 7 recorded-telemetry) have a Studio view; existing operational scenarios outside the replay-pack engine have none yet.

**Missing inputs (not reconstructed, not claimed integrated):** the original 100 financial-services and 100 telecom use-case libraries. Their IDs are still needed; none of the scenarios above came from them.

Replay sample corpus: 10 vendored authentic recordings (`catalog/replay_sources.json`). The Ollama server log was excluded because it mixes three timestamp formats. SA-Eventgen was not evaluated against its version-specific spec (not installed in any lab); the PulseForge replay engine was reused.

## 18-industry coverage matrix

Columns are separate evidence: documented is not runnable, runnable is not verified, verified is not TA-parsed or detected. Mappings are editorial unless the source labels the industry (`*` in the Explorer).

| Industry | Documented (all) | Cataloged only | Contracted | Runnable | Independently indexed | Panel queries populated | Dashboards installed | Dashboards data-validated | Dashboards visually verified | Dashboard-verified (legacy gate) | Curated stories | Stories runnable | Detections verified | Named sourcetypes without a native generator | Government subdomains covered |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Banking and Financial Services | 16 | 9 | 5 | 7 | 5 | 2 | 4 | 4 | 0 | 0 | 4 | 0 | 0 | 0 | - |
| Healthcare | 14 | 9 | 4 | 5 | 4 | 2 | 3 | 3 | 0 | 0 | 4 | 0 | 0 | 0 | - |
| Retail and E-commerce | 12 | 6 | 5 | 6 | 5 | 2 | 3 | 3 | 0 | 0 | 1 | 0 | 0 | 1 | - |
| Manufacturing | 18 | 11 | 6 | 6 | 3 | 2 | 3 | 3 | 0 | 0 | 4 | 0 | 0 | 1 | - |
| Energy and Utilities | 22 | 16 | 5 | 6 | 3 | 2 | 3 | 3 | 0 | 0 | 4 | 0 | 0 | 0 | - |
| Telecommunications | 43 | 27 | 14 | 15 | 13 | 2 | 3 | 3 | 1 | 0 | 4 | 0 | 0 | 2 | - |
| Government and Public Sector | 25 | 20 | 4 | 5 | 4 | 2 | 4 | 4 | 1 | 0 | 4 | 0 | 0 | 0 | critical-infrastructure, national-security, state-local |
| Transportation and Logistics | 13 | 11 | 2 | 2 | 2 | 1 | 2 | 2 | 0 | 0 | 3 | 0 | 0 | 0 | - |
| Education | 13 | 9 | 2 | 4 | 2 | 1 | 2 | 2 | 0 | 0 | 4 | 0 | 0 | 1 | - |
| Technology and SaaS | 24 | 5 | 6 | 19 | 5 | 1 | 5 | 5 | 0 | 0 | 0 | 0 | 0 | 1 | - |
| Media and Entertainment | 6 | 4 | 2 | 2 | 2 | 1 | 2 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | - |
| Hospitality and Travel | 10 | 6 | 2 | 4 | 2 | 1 | 2 | 2 | 0 | 0 | 1 | 0 | 0 | 1 | - |
| Aerospace and Defense | 6 | 4 | 2 | 2 | 2 | 1 | 2 | 2 | 0 | 0 | 3 | 0 | 0 | 0 | - |
| Legal, Compliance and Professional Services | 10 | 5 | 3 | 5 | 3 | 1 | 3 | 3 | 0 | 0 | 1 | 0 | 0 | 1 | - |
| Agriculture and Agritech | 6 | 3 | 3 | 2 | 2 | 1 | 2 | 2 | 1 | 0 | 0 | 0 | 0 | 1 | - |
| Real Estate, PropTech and Construction | 8 | 5 | 3 | 3 | 3 | 1 | 3 | 3 | 0 | 0 | 1 | 0 | 0 | 0 | - |
| Insurance and InsurTech | 9 | 6 | 3 | 3 | 3 | 2 | 3 | 3 | 0 | 0 | 1 | 0 | 0 | 0 | - |
| Non-Profit, NGOs and Global Aid | 8 | 5 | 3 | 3 | 3 | 1 | 3 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | - |

Curated stories are Splunk Analytic Stories whose own text names the sector as a threat target (basis NARRATIVE_TARGET_SECTOR) and whose original research.splunk.com page was verified (HTTP 200); they are NOT executable: only a story with a runtime-approved detection is runnable, and the single detection-verified item (React2Shell) is not curated to an industry. Technology/SaaS, media, non-profit and agriculture have no story whose text names the sector and whose link resolves. Government subdomains: State/Local, National Security and Critical Infrastructure have editorial or source-labeled entries; **Federal Civilian and Compliance has none** (no authoritative source selected). TA validation is not tracked per industry: only Windows/Sysmon channels were TA-checked (see the TA matrix). Industries whose documented scenarios have no runnable counterpart (for example transportation, media, aerospace/defense, agriculture, real estate, insurance, non-profit) need authentic telemetry sources before they can become runnable.
