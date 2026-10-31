# Scenario Coverage Reference

Generated 2026-10-31 by `scripts/generate_reference_docs.py` from the Use Case Explorer registry (all scenario registries merged and deduplicated by scenario id). Machine-readable: `scenario_coverage.json` / `scenario_coverage.csv`.

| Measure | Count |
|---|---|
| Unique operational scenario definitions | 362 |
| Runnable (a real generator and run path exist) | 138 |
| Cataloged candidates only (documented, not executable) | 209 |
| Independently indexed in an isolated lab | 138 |
| With a Dashboard Studio dashboard | 138 |
| Dashboards DATA_VALIDATED or better | 137 |
| Dashboards VISUALLY_VERIFIED | 9 |
| Detection verified | 0 (no add-on, CIM or Enterprise Security content installed) |

Tiers (as recorded, never upgraded by indexing): CATALOGED 209, CERTIFIED 18, CONTRACTED 109, FORMAT_VALIDATED 2, NOT_ESTABLISHED 1, VALIDATED 23.

The original 100 financial-services and 100 telecom use-case libraries were not supplied; they are **not** part of these counts and none of the scenarios below were derived from them. Industry mappings are editorial unless an industry pack binds them. Splunk Analytic Stories are a separate reference universe (see the Explorer's Security view); they are not counted as scenarios.

## How the counts relate (one partition, plus overlapping attributes)

| Group | Count | Meaning |
|---|---|---|
| Runnable | 138 | A real generator and run path exist; every one has a Dashboard Studio dashboard |
| Contract only | 15 | A topology or format contract exists but no executable telemetry (reason recorded per scenario) |
| Cataloged only | 209 | Documented candidates with no execution path |
| Total | 362 | The three groups above are mutually exclusive and add up to the total |

**Overlapping attributes** (not additional groups): *independently indexed* (138) is a subset of the runnable group, i.e. runnable scenarios whose events from a fresh run were read back from Splunk by an independent search in an isolated lab (scenario-level live checks, dashboard data validation, the monitored runs and the flow scenarios); 0 runnable scenarios lack that proof. Earlier status reports counted 76 because they used only the scenario-level live-equality evidence; the dashboard data validation (a fresh run per scenario, read back from Splunk by run id, KPIs equal to separately written searches) extends the same kind of proof to every runnable scenario, which is why the figure is now higher. The two numbers measure different evidence, not different scenarios. *Tier* (CERTIFIED, VALIDATED, CONTRACTED, ...) is the maturity recorded by the catalog and is never upgraded by indexing.

## Coverage by approved industry

| Industry | Definitions | Runnable | Indexed | Dashboards | Dashboards data-validated |
|---|---|---|---|---|---|
| Banking and Financial Services | 16 | 7 | 7 | 7 | 7 |
| Healthcare | 14 | 5 | 5 | 5 | 5 |
| Retail and E-commerce | 12 | 6 | 6 | 6 | 6 |
| Manufacturing | 18 | 6 | 6 | 6 | 6 |
| Energy and Utilities | 22 | 6 | 6 | 6 | 6 |
| Telecommunications | 43 | 15 | 15 | 15 | 15 |
| Government and Public Sector | 25 | 5 | 5 | 5 | 5 |
| Transportation and Logistics | 13 | 2 | 2 | 2 | 2 |
| Education | 13 | 4 | 4 | 4 | 4 |
| Technology and SaaS | 24 | 19 | 19 | 19 | 19 |
| Media and Entertainment | 6 | 2 | 2 | 2 | 2 |
| Hospitality and Travel | 10 | 4 | 4 | 4 | 4 |
| Aerospace and Defense | 6 | 2 | 2 | 2 | 2 |
| Legal, Compliance and Professional Services | 10 | 5 | 5 | 5 | 5 |
| Agriculture and Agritech | 6 | 2 | 2 | 2 | 2 |
| Real Estate, PropTech and Construction | 8 | 3 | 3 | 3 | 3 |
| Insurance and InsurTech | 9 | 3 | 3 | 3 | 3 |
| Non-Profit, NGOs and Global Aid | 8 | 3 | 3 | 3 | 3 |

## Runnable scenarios

| ID | Title | Execution | Kind | Industries | Sourcetypes | Indexed | Dashboard | Dashboard maturity |
|---|---|---|---|---|---|---|---|---|
| `AI-001` | Indirect Prompt Injection | native (unified_generation) | security | technology-saas | 1 | Y | pf_AI-001 | VISUALLY_VERIFIED |
| `AI-002` | Unauthorized Tool Invocation | native (unified_generation) | security | technology-saas | 1 | Y | pf_AI-002 | DATA_VALIDATED |
| `AI-003` | MCP Tool Output Manipulation | native (unified_generation) | security | technology-saas | 1 | Y | pf_AI-003 | DATA_VALIDATED |
| `AI-004` | Agent Identity and Privilege Drift | native (unified_generation) | security | technology-saas | 1 | Y | pf_AI-004 | DATA_VALIDATED |
| `AI-005` | A2A Delegation Abuse | native (unified_generation) | security | technology-saas | 1 | Y | pf_AI-005 | DATA_VALIDATED |
| `AI-006` | Multi-Agent Incident | native (unified_generation) | security | technology-saas | 1 | Y | pf_AI-006 | DATA_VALIDATED |
| `C100-CRI-002` | Telecom Operations Network Degradation — Correlated Reference | native (unified_generation) | operational | banking-financial-services, energy-utilities, government-public-sector | 2 | Y | pf_C100-CRI-002 | DATA_VALIDATED |
| `C100-DC-001` | Nexus Fabric Uplink Degradation — NX-OS Reference | native (unified_generation) | operational | manufacturing | 1 | Y | pf_C100-DC-001 | VISUALLY_VERIFIED |
| `C100-ENT-001` | Campus Access Link Degradation — IOS XE Reference | native (unified_generation) | operational | healthcare | 1 | Y | pf_C100-ENT-001 | DATA_VALIDATED |
| `C100-SEC-001` | Secure Firewall Suspicious Connection Burst — ASA Reference | native (unified_generation) | security | not mapped | 1 | Y | pf_C100-SEC-001 | DATA_VALIDATED |
| `P12-XD-001` | AI Agent to Infrastructure | native (unified_generation) | security | not mapped | 1 | Y | pf_P12-XD-001 | DATA_VALIDATED |
| `P12-XD-002` | Supply Chain to Application | native (unified_generation) | security | not mapped | 1 | Y | pf_P12-XD-002 | DATA_VALIDATED |
| `SC-001` | Suspicious Dependency Change | native (unified_generation) | security | technology-saas | 1 | Y | pf_SC-001 | DATA_VALIDATED |
| `SC-002` | CI Workflow Permission Escalation | native (unified_generation) | security | technology-saas | 1 | Y | pf_SC-002 | DATA_VALIDATED |
| `SC-003` | Build Artifact Provenance Gap | native (unified_generation) | security | technology-saas | 1 | Y | pf_SC-003 | DATA_VALIDATED |
| `SC-004` | Repository Automation Abuse | native (unified_generation) | security | technology-saas | 1 | Y | pf_SC-004 | DATA_VALIDATED |
| `SC-005` | Supply Chain to Runtime Correlation | native (unified_generation) | security | technology-saas | 1 | Y | pf_SC-005 | DATA_VALIDATED |
| `SEC-P9-A-TRAFFIC-FLOOD` | Controlled Traffic Flood Indicators | native (unified_generation) | security | not mapped | 1 | Y | pf_SEC-P9-A-TRAFFIC-FLOOD | DATA_VALIDATED |
| `SEC-P9-B-DNS-ANOMALY` | DNS Diversity and NXDOMAIN Indicators | native (unified_generation) | security | not mapped | 1 | Y | pulseforge_dns_anomaly_studio | SPL_VALIDATED |
| `SEC-P9-C-BEACONING` | Periodic External Communication Indicators | native (unified_generation) | security | not mapped | 2 | Y | pf_SEC-P9-C-BEACONING | DATA_VALIDATED |
| `SEC-P9-D-INTERNAL-RECON` | Internal Reconnaissance Indicators | native (unified_generation) | security | not mapped | 1 | Y | pf_SEC-P9-D-INTERNAL-RECON | DATA_VALIDATED |
| `SEC-P9-E-DNS-TUNNEL` | DNS Tunneling and Exfiltration Indicators | native (unified_generation) | security | not mapped | 2 | Y | pf_SEC-P9-E-DNS-TUNNEL | DATA_VALIDATED |
| `SEC-P9-F-CROSS-SOURCE` | Cross-Source DNS, Beaconing, and Reconnaissance Incident | native (unified_generation) | security | not mapped | 2 | Y | pf_SEC-P9-F-CROSS-SOURCE | VISUALLY_VERIFIED |
| `arch_lan_campus_access` | LAN: Local Area Network - Campus Switching & 802.1Q Segments | native (scenario_runner) | operational | not mapped | 3 | Y | pf_arch_lan_campus_access | DATA_VALIDATED |
| `arch_man_carrier_ring` | MAN: Metropolitan Area Network - 100G Carrier Ethernet Ring & G.8032 E | native (scenario_runner) | operational | telecommunications | 3 | Y | pf_arch_man_carrier_ring | DATA_VALIDATED |
| `arch_vpn_remote_workforce` | VPN: Virtual Private Network - Cisco AnyConnect & Site-to-Site IPsec | native (scenario_runner) | operational | legal-compliance-professional-services, technology-saas | 3 | Y | pf_arch_vpn_remote_workforce | DATA_VALIDATED |
| `arch_wlan_meraki_catalyst` | WLAN: Wireless Local Area Network - Catalyst 9800 & Meraki Wi-Fi 6E/7 | native (scenario_runner) | operational | education, hospitality-travel, retail-ecommerce | 3 | Y | pf_arch_wlan_meraki_catalyst | DATA_VALIDATED |
| `cisco_aci_microburst` | Data Center Fabric ACI Ingress Microburst Traffic | native (scenario_runner) | operational | not mapped | 3 | Y | pf_cisco_aci_microburst | VISUALLY_VERIFIED |
| `cisco_campus_rogue` | Campus Core L2/3 Disturbance & Rogue AP | native (scenario_runner) | operational | education, hospitality-travel | 4 | Y | pf_cisco_campus_rogue | DATA_VALIDATED |
| `cisco_sdwan_brownout` | Enterprise WAN Circuit Brownout & App Route Failover | native (scenario_runner) | operational | not mapped | 4 | Y | pf_cisco_sdwan_brownout | DATA_VALIDATED |
| `ddos_attack` | Distributed Denial of Service (DDoS SYN Flood) | native (scenario_runner) | security | not mapped | 3 | Y | pf_ddos_attack | DATA_VALIDATED |
| `ind_aero_defense_endpoint_c2` | Defense contractor: C2 callback, endpoint pipeline and privileged-acce | native (replay_pack) | security | aerospace-defense | 11 | Y | pf_ind_aero_defense_endpoint_c2 | DATA_VALIDATED |
| `ind_agri_edge_gateway_health` | Agritech: edge gateway routing observation and Linux gateway authentic | native (replay_pack) | operational | agriculture-agritech | 7 | Y | pf_ind_agri_edge_gateway_health | DATA_VALIDATED |
| `ind_bank_account_takeover_resilience` | Retail banking: workstation credential compromise, cloud SSO abuse, ba | native (replay_pack) | security | banking-financial-services | 13 | Y | pf_ind_bank_account_takeover_resilience | DATA_VALIDATED |
| `ind_bank_payments_edge_defense` | Payments edge: WAF/IDS/firewall observation then cloud control-plane r | native (replay_pack) | security | banking-financial-services | 6 | Y | pf_ind_bank_payments_edge_defense | DATA_VALIDATED |
| `ind_edu_campus_identity_and_collab` | Campus: cloud identity attack and collaboration-platform audit | native (replay_pack) | security | education | 8 | Y | pf_ind_edu_campus_identity_and_collab | DATA_VALIDATED |
| `ind_energy_scada_proxy_intrusion` | Utility: OT proxy host hunt and C2 callback detection | native (replay_pack) | security | energy-utilities | 6 | Y | pf_ind_energy_scada_proxy_intrusion | DATA_VALIDATED |
| `ind_energy_substation_edge_observation` | Substation edge: OT routing observation and network platform health | native (replay_pack) | operational | energy-utilities | 11 | Y | pf_ind_energy_substation_edge_observation | DATA_VALIDATED |
| `ind_gov_agency_mail_exfiltration` | Agency: cloud mail exfiltration with containment and endpoint pipeline | native (replay_pack) | security | government-public-sector | 13 | Y | pf_ind_gov_agency_mail_exfiltration | DATA_VALIDATED |
| `ind_gov_citizen_identity_attack` | Citizen services: cloud identity attack, AWS reconnaissance, privilege | native (replay_pack) | security | government-public-sector | 11 | Y | pf_ind_gov_citizen_identity_attack | VISUALLY_VERIFIED |
| `ind_health_clinical_network_edge` | Hospital network: edge and DNS/proxy health with wireless threat | native (replay_pack) | operational | healthcare | 13 | Y | pf_ind_health_clinical_network_edge | DATA_VALIDATED |
| `ind_health_ehr_ransomware_readiness` | Hospital: endpoint credential attack with backup and privileged-access | native (replay_pack) | security | healthcare | 12 | Y | pf_ind_health_ehr_ransomware_readiness | DATA_VALIDATED |
| `ind_hospitality_guest_network_defense` | Hospitality: edge defense and guest/staff identity attack | native (replay_pack) | security | hospitality-travel | 9 | Y | pf_ind_hospitality_guest_network_defense | DATA_VALIDATED |
| `ind_insurance_claims_platform_audit` | Claims platform: SaaS and database/message audit with cloud mail exfil | native (replay_pack) | security | insurance-insurtech | 13 | Y | pf_ind_insurance_claims_platform_audit | DATA_VALIDATED |
| `ind_insurance_underwriting_exposure` | Underwriting data platform: exposure management, vault and identity au | native (replay_pack) | operational | insurance-insurtech | 11 | Y | pf_ind_insurance_underwriting_exposure | DATA_VALIDATED |
| `ind_legal_matter_data_exfiltration` | Law firm: client-matter data exfiltration across mail, vault and wiki | native (replay_pack) | security | legal-compliance-professional-services | 11 | Y | pf_ind_legal_matter_data_exfiltration | DATA_VALIDATED |
| `ind_media_content_delivery_exfil` | Media: content-delivery access with cloud-mail exfiltration | native (replay_pack) | security | media-entertainment | 8 | Y | pf_ind_media_content_delivery_exfil | DATA_VALIDATED |
| `ind_mfg_it_ot_convergence` | Plant: OT proxy and edge routing observation, then command-and-control | native (replay_pack) | security | manufacturing | 10 | Y | pf_ind_mfg_it_ot_convergence | DATA_VALIDATED |
| `ind_mfg_plant_network_health` | Plant network: platform degradation and change-induced outage | native (replay_pack) | operational | manufacturing | 19 | Y | pf_ind_mfg_plant_network_health | DATA_VALIDATED |
| `ind_nonprofit_donor_platform_attack` | Non-profit: staff identity attack and cloud-mail exfiltration of donor | native (replay_pack) | security | nonprofit-ngo-global-aid | 13 | Y | pf_ind_nonprofit_donor_platform_attack | DATA_VALIDATED |
| `ind_realestate_building_exposure` | Property technology: exposure management and collaboration audit | native (replay_pack) | operational | real-estate-proptech-construction | 7 | Y | pf_ind_realestate_building_exposure | DATA_VALIDATED |
| `ind_retail_ecommerce_cloud_recon` | E-commerce: AWS reconnaissance and escalation with exposure management | native (replay_pack) | security | retail-ecommerce | 6 | Y | pf_ind_retail_ecommerce_cloud_recon | DATA_VALIDATED |
| `ind_retail_pos_edge_defense` | Retail stores: edge defense observation and endpoint threat pipeline | native (replay_pack) | security | retail-ecommerce | 9 | Y | pf_ind_retail_pos_edge_defense | DATA_VALIDATED |
| `ind_saas_platform_runtime_attack` | SaaS platform: Kubernetes container escape, collaboration audit and ex | native (replay_pack) | security | technology-saas | 11 | Y | pf_ind_saas_platform_runtime_attack | DATA_VALIDATED |
| `ind_telco_access_and_wireless_health` | Telecom NOC: RADIUS/NAC outage, platform degradation and rogue wireles | native (replay_pack) | operational | telecommunications | 16 | Y | pf_ind_telco_access_and_wireless_health | DATA_VALIDATED |
| `ind_telco_change_induced_outage` | Telecom NOC: change-induced SD-WAN outage, then edge threat pipeline | native (replay_pack) | operational | telecommunications | 15 | Y | pf_ind_telco_change_induced_outage | VISUALLY_VERIFIED |
| `ind_transport_fleet_network_change` | Logistics network: change-induced outage and edge routing observation | native (replay_pack) | operational | transportation-logistics | 16 | Y | pf_ind_transport_fleet_network_change | DATA_VALIDATED |
| `mixed_backbone_optical` | Multicast/MPLS Backbone Optical Carrier Shift | native (scenario_runner) | operational | not mapped | 3 | Y | pf_mixed_backbone_optical | DATA_VALIDATED |
| `mixed_edge_breach` | Distributed Edge Breach & Internal Probing | native (scenario_runner) | security | not mapped | 5 | Y | pf_mixed_edge_breach | DATA_VALIDATED |
| `mixed_sase_degradation` | SASE Cloud Ingress App Degradation & Synthetic Validation | native (scenario_runner) | operational | legal-compliance-professional-services, technology-saas | 4 | Y | pf_mixed_sase_degradation | DATA_VALIDATED |
| `network_01_campus_link` | Campus link failure/recovery | native (incident_pack) | operational | not mapped | 2 | Y | pf_network_01_campus_link | DATA_VALIDATED |
| `network_02_vlan_trunk` | VLAN/trunk misconfiguration | native (incident_pack) | operational | not mapped | 2 | Y | pf_network_02_vlan_trunk | DATA_VALIDATED |
| `network_03_stp_storm` | STP loop/broadcast storm | native (incident_pack) | operational | not mapped | 2 | Y | pf_network_03_stp_storm | DATA_VALIDATED |
| `network_04_wan_brownout` | WAN latency/jitter/packet-loss brownout | native (incident_pack) | operational | not mapped | 2 | Y | pf_network_04_wan_brownout | DATA_VALIDATED |
| `network_05_dual_isp` | Dual-ISP failover/recovery | native (incident_pack) | operational | not mapped | 2 | Y | pf_network_05_dual_isp | DATA_VALIDATED |
| `network_06_bgp_flap` | BGP neighbor flap/route withdrawal | native (incident_pack) | operational | not mapped | 2 | Y | pf_network_06_bgp_flap | DATA_VALIDATED |
| `network_07_ospf_adjacency` | OSPF adjacency failure/reconvergence | native (incident_pack) | operational | not mapped | 2 | Y | pf_network_07_ospf_adjacency | DATA_VALIDATED |
| `network_08_firewall_policy` | Firewall policy misconfiguration | native (incident_pack) | operational | not mapped | 2 | Y | pf_network_08_firewall_policy | DATA_VALIDATED |
| `network_09_ddos_flood` | DDoS/traffic flood/mitigation | native (incident_pack) | operational | not mapped | 2 | Y | pf_network_09_ddos_flood | DATA_VALIDATED |
| `network_10_dns_failure` | DNS resolver failure/recovery | native (incident_pack) | operational | not mapped | 2 | Y | pf_network_10_dns_failure | DATA_VALIDATED |
| `network_11_dhcp_exhaustion` | DHCP pool exhaustion/recovery | native (incident_pack) | operational | not mapped | 2 | Y | pf_network_11_dhcp_exhaustion | DATA_VALIDATED |
| `network_12_dc_congestion` | Data-center congestion/queue drops | native (incident_pack) | operational | not mapped | 2 | Y | pf_network_12_dc_congestion | DATA_VALIDATED |
| `network_13_mtu_pmtud` | MTU mismatch/PMTUD failure | native (incident_pack) | operational | not mapped | 2 | Y | pf_network_13_mtu_pmtud | DATA_VALIDATED |
| `network_14_wireless_outage` | Wireless controller/AP outage | native (incident_pack) | operational | not mapped | 2 | Y | pf_network_14_wireless_outage | DATA_VALIDATED |
| `network_15_device_resources` | Device CPU/memory exhaustion | native (incident_pack) | operational | not mapped | 2 | Y | pf_network_15_device_resources | DATA_VALIDATED |
| `network_16_retail_uplink` | Retail branch uplink flap and checkout interruption | native (incident_pack) | operational | retail-ecommerce | 2 | Y | pf_network_16_retail_uplink | DATA_VALIDATED |
| `network_17_hospital_mac_auth` | Hospital access MAC instability and login retries | native (incident_pack) | operational | healthcare | 2 | Y | pf_network_17_hospital_mac_auth | DATA_VALIDATED |
| `network_18_payment_deny` | Perimeter deny burst and payment availability loss | native (incident_pack) | operational | banking-financial-services, retail-ecommerce | 2 | Y | pf_network_18_payment_deny | DATA_VALIDATED |
| `network_19_ips_service` | IPS attack burst and legitimate-session degradation | native (incident_pack) | operational | not mapped | 2 | Y | pf_network_19_ips_service | DATA_VALIDATED |
| `network_20_backend_link` | Distribution-link loss and backend monitor failure | native (incident_pack) | operational | not mapped | 2 | Y | pf_network_20_backend_link | DATA_VALIDATED |
| `network_21_partial_pool` | Partial load-balancer pool outage with perimeter demand | native (incident_pack) | operational | not mapped | 2 | Y | pf_network_21_partial_pool | DATA_VALIDATED |
| `network_22_authentication_storm` | Campus authentication retry storm at perimeter | native (incident_pack) | operational | not mapped | 2 | Y | pf_network_22_authentication_storm | DATA_VALIDATED |
| `network_23_containment_request` | Simulated NAC containment request and service-access change | native (incident_pack) | operational | not mapped | 2 | Y | pf_network_23_containment_request | DATA_VALIDATED |
| `network_24_policy_disagreement` | Multi-firewall path-policy disagreement | native (incident_pack) | operational | not mapped | 2 | Y | pf_network_24_policy_disagreement | DATA_VALIDATED |
| `network_25_mpls_recovery` | Primary MPLS path-change observation and branch SLA recovery | native (incident_pack) | operational | not mapped | 2 | Y | pf_network_25_mpls_recovery | DATA_VALIDATED |
| `network_26_maintenance` | Planned maintenance versus unplanned service outage | native (incident_pack) | operational | not mapped | 2 | Y | pf_network_26_maintenance | DATA_VALIDATED |
| `network_27_stale_sessions` | Authentication recovery with stale perimeter sessions | native (incident_pack) | operational | not mapped | 2 | Y | pf_network_27_stale_sessions | DATA_VALIDATED |
| `network_security_correlation` | Network Degradation With Security Correlation | native (scenario_runner) | operational | not mapped | 5 | Y | pf_network_security_correlation | DATA_VALIDATED |
| `openconfig_mdt_streaming` | OpenConfig MDT Streaming & Telemetry Assurance | native (scenario_runner) | operational | not mapped | 3 | Y | pf_openconfig_mdt_streaming | DATA_VALIDATED |
| `paloalto_threat_investigation` | Palo Alto Networks Threat Investigation | native (scenario_runner) | security | not mapped | 3 | Y | pf_paloalto_threat_investigation | VISUALLY_VERIFIED |
| `payment_processing_degradation` | Financial Services Payment Application Degradation | native (scenario_runner) | operational | banking-financial-services | 5 | Y | pf_payment_processing_degradation | DATA_VALIDATED |
| `rfc5424-link-state-lifecycle` | Modeled Link-State Lifecycle | native (unified_generation) | operational | not mapped | 1 | Y | pf_rfc5424-link-state-lifecycle | DATA_VALIDATED |
| `rp_agentic_ai_mcp_runtime_hybrid` | Agentic AI: recorded MCP server log plus native exfiltration attempt ( | hybrid (replay_pack) | security | technology-saas, legal-compliance-professional-services | 3 | Y | pf_rp_agentic_ai_mcp_runtime_hybrid | DATA_VALIDATED |
| `rp_cloud_control_plane_activity` | AWS control-plane activity (replayed CloudTrail) | replay (replay_pack) | security | technology-saas, insurance-insurtech, media-entertainment | 1 | Y | pf_rp_cloud_control_plane_activity | DATA_VALIDATED |
| `rp_edr_and_cloud_activity` | Endpoint sensor and cloud audit side by side (aligned in time only) | replay (replay_pack) | security | banking-financial-services, aerospace-defense | 2 | Y | pf_rp_edr_and_cloud_activity | DATA_VALIDATED |
| `rp_linux_credential_access` | Linux credential-file access with system context (replayed recordings) | replay (replay_pack) | security | technology-saas, government-public-sector, banking-financial-services | 2 | Y | pf_rp_linux_credential_access | DATA_VALIDATED |
| `rp_web_exploitation_recordings` | Web exploitation observed from three recordings (aligned in time only) | replay (replay_pack) | security | retail-ecommerce, hospitality-travel, government-public-sector | 3 | Y | pf_rp_web_exploitation_recordings | DATA_VALIDATED |
| `rp_windows_endpoint_process_chain` | Windows endpoint process and network activity (replayed Sysmon) | replay (replay_pack) | security | healthcare, manufacturing, education | 1 | Y | pf_rp_windows_endpoint_process_chain | DATA_VALIDATED |
| `rp_workload_sysmon_ebpf_hybrid` | Linux workload: recorded Sysmon-for-Linux plus native eBPF hunt (hybri | hybrid (replay_pack) | security | technology-saas, telecommunications, transportation-logistics | 10 | Y | pf_rp_workload_sysmon_ebpf_hybrid | DATA_VALIDATED |
| `service_provider_cisco` | Service Provider Network - All Cisco (Cisco 8000, NCS 5500, IOS-XR SRv | native (scenario_runner) | operational | telecommunications | 4 | Y | pf_service_provider_cisco | DATA_VALIDATED |
| `sql_injection` | SQL Injection / Application Breach | native (scenario_runner) | security | not mapped | 3 | Y | pf_sql_injection | DATA_VALIDATED |
| `telco_01_ran_cell` | 5G RAN cell degradation | native (incident_pack) | operational | telecommunications | 2 | Y | pf_telco_01_ran_cell | DATA_VALIDATED |
| `telco_02_registration_auth` | 5G registration/authentication failure | native (incident_pack) | operational | telecommunications | 2 | Y | pf_telco_02_registration_auth | DATA_VALIDATED |
| `telco_03_slice_sla` | 5G network slice SLA violation | native (incident_pack) | operational | telecommunications | 2 | Y | pf_telco_03_slice_sla | DATA_VALIDATED |
| `telco_04_ims_volte` | IMS/VoLTE call-quality degradation | native (incident_pack) | operational | telecommunications | 2 | Y | pf_telco_04_ims_volte | VISUALLY_VERIFIED |
| `telco_05_mobile_transport` | Mobile transport/fronthaul congestion | native (incident_pack) | operational | telecommunications | 2 | Y | pf_telco_05_mobile_transport | DATA_VALIDATED |
| `telco_06_broadband_cpe` | Broadband CPE service outage | native (incident_pack) | operational | telecommunications | 2 | Y | pf_telco_06_broadband_cpe | DATA_VALIDATED |
| `telco_07_sdwan_service` | SD-WAN service degradation | native (incident_pack) | operational | telecommunications | 2 | Y | pf_telco_07_sdwan_service | DATA_VALIDATED |
| `telco_08_roaming_mobility` | Roaming/mobility failure | native (incident_pack) | operational | telecommunications | 2 | Y | pf_telco_08_roaming_mobility | DATA_VALIDATED |
| `telco_09_core_user_plane` | 5G core user-plane degradation | native (incident_pack) | operational | telecommunications | 2 | Y | pf_telco_09_core_user_plane | DATA_VALIDATED |
| `telco_10_cross_layer` | Cross-layer telecom service outage and SLA impact | native (incident_pack) | operational | telecommunications | 2 | Y | pf_telco_10_cross_layer | DATA_VALIDATED |
| `test-correlated-interface-degradation` | Cisco IOS XR Interface Degradation — Golden Scenario | native (unified_generation) | operational | not mapped | 1 | Y | pf_test-correlated-interface-degradation | DATA_VALIDATED |
| `ub1_ot_proxy_host_hunt` | OT Tamper to Container Host Hunt (Universe Batch-1) | native (scenario_pack) | security | manufacturing, energy-utilities | 4 | Y | pf_ub1_ot_proxy_host_hunt | DATA_VALIDATED |
| `ub2_cloud_identity_mail_hunt` | Ub2 Cloud Identity Mail Hunt | native (scenario_pack) | security | not mapped | 3 | Y | pf_ub2_cloud_identity_mail_hunt | DATA_VALIDATED |
| `ub2_database_backup_integrity` | Ub2 Database Backup Integrity | native (scenario_pack) | operational | not mapped | 2 | Y | pf_ub2_database_backup_integrity | DATA_VALIDATED |
| `ub2_ot_edge_routing_observation` | Ub2 Ot Edge Routing Observation | native (scenario_pack) | operational | manufacturing, energy-utilities | 4 | Y | pf_ub2_ot_edge_routing_observation | DATA_VALIDATED |
| `ub3_database_message_audit` | Ub3 Database Message Audit | native (scenario_pack) | operational | not mapped | 2 | Y | pf_ub3_database_message_audit | DATA_VALIDATED |
| `ub3_identity_runtime_audit` | Ub3 Identity Runtime Audit | native (scenario_pack) | operational | not mapped | 4 | Y | pf_ub3_identity_runtime_audit | DATA_VALIDATED |
| `ub3_multivendor_edge_observation` | Ub3 Multivendor Edge Observation | native (scenario_pack) | operational | not mapped | 4 | Y | pf_ub3_multivendor_edge_observation | DATA_VALIDATED |
| `ub4_endpoint_threat_pipeline` | Ub4 Endpoint Threat Pipeline | native (scenario_pack) | security | not mapped | 5 | Y | pf_ub4_endpoint_threat_pipeline | DATA_VALIDATED |
| `ub4_exposure_infra_logging` | Ub4 Exposure Infra Logging | native (scenario_pack) | operational | not mapped | 4 | Y | pf_ub4_exposure_infra_logging | DATA_VALIDATED |
| `ub4_saas_collaboration_audit` | Ub4 Saas Collaboration Audit | native (scenario_pack) | operational | not mapped | 3 | Y | pf_ub4_saas_collaboration_audit | DATA_VALIDATED |
| `ub5_cisco_change_induced_outage` | Cisco Change-Induced Outage | native (scenario_pack) | operational | not mapped | 12 | Y | pf_ub5_cisco_change_induced_outage | DATA_VALIDATED |
| `ub5_cisco_nac_radius_outage` | Cisco NAC RADIUS Outage | native (scenario_pack) | operational | not mapped | 5 | Y | pf_ub5_cisco_nac_radius_outage | DATA_VALIDATED |
| `ub5_cisco_platform_health_degradation` | Cisco Platform Health Degradation | native (scenario_pack) | operational | not mapped | 7 | Y | pf_ub5_cisco_platform_health_degradation | DATA_VALIDATED |
| `ub6_catalyst_wireless_rogue_threat` | Catalyst Wireless Rogue And Threat Summary | native (scenario_pack) | operational | not mapped | 4 | Y | pf_ub6_catalyst_wireless_rogue_threat | DATA_VALIDATED |
| `ub6_sdwan_utd_threat_pipeline` | SD-WAN UTD Threat Pipeline | native (scenario_pack) | security | not mapped | 3 | Y | pf_ub6_sdwan_utd_threat_pipeline | DATA_VALIDATED |
| `wave2_agentic_ai_exfil_attempt` | Agentic AI Runtime Exfiltration Attempt (Wave-2 pack) | native (scenario_pack) | security | technology-saas | 3 | Y | pf_wave2_agentic_ai_exfil_attempt | DATA_VALIDATED |
| `wave2_aws_recon_escalation` | AWS CloudTrail Recon & Escalation (Wave-2 pack) | native (scenario_pack) | security | not mapped | 2 | Y | pf_wave2_aws_recon_escalation | DATA_VALIDATED |
| `wave2_bigip_openconfig_itops` | Big-IP ADC & OpenConfig Observability Health (Wave-2 pack) | native (scenario_pack) | operational | not mapped | 4 | Y | pf_wave2_bigip_openconfig_itops | DATA_VALIDATED |
| `wave2_c2_callback_detection` | Network C2 Callback & Discovery Behaviors (Wave-2 pack) | native (scenario_pack) | security | not mapped | 2 | Y | pf_wave2_c2_callback_detection | DATA_VALIDATED |
| `wave2_cloud_identity_sso_hunt` | Cross-Cloud Identity SSO Brute Force (Wave-2 pack) | native (scenario_pack) | security | not mapped | 5 | Y | pf_wave2_cloud_identity_sso_hunt | DATA_VALIDATED |
| `wave2_k8s_container_escape` | Kubernetes Auth Abuse + Container Escape (Wave-2 pack) | native (scenario_pack) | security | not mapped | 3 | Y | pf_wave2_k8s_container_escape | DATA_VALIDATED |
| `wave2_linux_auth_anomaly` | Linux Infrastructure Auth Anomaly (Wave-2 pack) | native (scenario_pack) | security | not mapped | 3 | Y | pf_wave2_linux_auth_anomaly | DATA_VALIDATED |
| `wave2_ws_credential_compromise_chain` | Windows Credential Compromise Kill Chain (Wave-2 pack) | native (scenario_pack) | security | not mapped | 6 | Y | pf_wave2_ws_credential_compromise_chain | DATA_VALIDATED |
| `wave3_cloudmail_exfil` | Cloud Mail Exfiltration Chain (Wave-3 pack) | native (scenario_pack) | security | not mapped | 8 | Y | pf_wave3_cloudmail_exfil | VISUALLY_VERIFIED |
| `wave3_ebpf_workload_hunt` | eBPF Workload Hunt (Wave-3 pack) | native (scenario_pack) | security | not mapped | 9 | Y | pf_wave3_ebpf_workload_hunt | DATA_VALIDATED |
| `wave3_vsphere_hostpath_triage` | vSphere Host Path Triage (Wave-3 pack) | native (scenario_pack) | operational | not mapped | 10 | Y | pf_wave3_vsphere_hostpath_triage | DATA_VALIDATED |

## Not runnable

| ID | Title | Tier | Reason |
|---|---|---|---|
| `C100-CRI-001` | Financial Trading Campus-to-Data-Center Latency | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `C100-CRI-003` | Utility Substation WAN Loss | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `C100-CRI-004` | Energy Pipeline Remote-Site Isolation | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `C100-CRI-005` | Manufacturing Cell Network Congestion | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `C100-CRI-006` | Healthcare Clinical Application Path Failure | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `C100-CRI-007` | Transportation Control-Site Failover | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `C100-CRI-008` | Public Sector Identity and Network Access Failure | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `C100-CRI-009` | Remote Infrastructure Telemetry Blackout | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `C100-CRI-010` | OT/IT Segmentation Policy Drift | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `C100-CRI-011` | Sovereign Cloud Interconnect Degradation | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `C100-CRI-012` | Critical Communications Path Congestion | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `C100-CRI-013` | Distributed Government Site Outage | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `C100-CRI-014` | Mixed-Vendor Application Delivery Degradation | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `C100-CRI-015` | Cisco Network and Microsoft Identity Correlation | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `C100-CRI-016` | Hybrid Hospital Wireless and Cloud Dependency | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `C100-CRI-017` | Industrial Site Security and Availability Incident | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `C100-CRI-018` | Cross-Domain DNS Dependency Failure | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `C100-CRI-019` | Sovereign Multi-Region Routing Instability | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `C100-CRI-020` | National Critical Infrastructure Evidence Gap | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `C100-DC-002` | Nexus vPC Member Failure | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `C100-DC-003` | EVPN Route Withdrawal | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `C100-DC-004` | VXLAN Tunnel Endpoint Reachability Loss | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `C100-DC-005` | ACI Leaf-Spine Link Failure | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `C100-DC-006` | ACI Endpoint Movement Anomaly | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `C100-DC-007` | ACI Contract Policy Denial | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `C100-DC-008` | Data Center East-West Congestion | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `C100-DC-009` | Underlay Routing Instability | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `C100-DC-010` | Overlay-Underlay Correlation Gap | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `C100-DC-011` | UCS Fabric Interconnect Degradation | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `C100-DC-012` | UCS Service Profile Drift | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `C100-DC-013` | Intersight Managed-System Visibility Gap | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `C100-DC-014` | Hybrid Cloud Data Path Degradation | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `C100-DC-015` | Storage Network Dependency Congestion | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `C100-DC-016` | Application Tier Fabric Isolation | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `C100-DC-017` | GPU Fabric East-West Congestion Candidate | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `C100-DC-018` | Lossless Ethernet Pause Propagation Candidate | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `C100-DC-019` | AI Cluster Network Telemetry Gap | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `C100-DC-020` | Multi-Fabric Data Center Service Impact | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `C100-ENT-002` | Distribution Uplink Failure | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `C100-ENT-003` | Campus Oversubscription Congestion | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `C100-ENT-004` | Branch WAN Packet Loss | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `C100-ENT-005` | SD-WAN Preferred-Path Change | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `C100-ENT-006` | SD-WAN Brownout Before Failover | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `C100-ENT-007` | Campus Routing Adjacency Instability | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `C100-ENT-008` | Branch Route Withdrawal | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `C100-ENT-009` | Wireless Client Roaming Failure | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `C100-ENT-010` | Wireless Capacity Saturation | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `C100-ENT-011` | Campus DHCP Dependency Failure | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `C100-ENT-012` | Campus DNS Path Degradation | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `C100-ENT-013` | Network Access Authentication Delay | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `C100-ENT-014` | Network Access Authorization Drift | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `C100-ENT-015` | Campus Path Asymmetry | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `C100-ENT-016` | Catalyst Configuration Drift | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `C100-ENT-017` | Catalyst Center Assurance Data Gap | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `C100-ENT-018` | Meraki Multi-Site Reachability Degradation | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `C100-ENT-019` | Branch Application Path Regression | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `C100-ENT-020` | Enterprise Telemetry Blind Spot | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `C100-SEC-002` | FTD Access-Control Policy Denial | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `C100-SEC-003` | ASA Remote Access Failure | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `C100-SEC-004` | Firewall Rulebase Drift | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `C100-SEC-005` | ISE Authentication Failure Spike | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `C100-SEC-006` | ISE Policy Authorization Mismatch | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `C100-SEC-007` | Secure Access Policy Block | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `C100-SEC-008` | Umbrella DNS Abuse Indicator | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `C100-SEC-009` | Umbrella DNS Tunneling Candidate | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `C100-SEC-010` | Secure Endpoint Malware Activity Candidate | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `C100-SEC-011` | Secure Endpoint Isolation Impact | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `C100-SEC-012` | Secure Network Analytics Beaconing Candidate | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `C100-SEC-013` | Secure Network Analytics Lateral Movement Candidate | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `C100-SEC-014` | Secure Client Posture Failure | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `C100-SEC-015` | Duo Authentication Anomaly | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `C100-SEC-016` | Cisco XDR Cross-Signal Incident Candidate | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `C100-SEC-017` | Secure Workload Policy Violation Candidate | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `C100-SEC-018` | Cyber Vision OT Asset Anomaly Candidate | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `C100-SEC-019` | Reconnaissance and Firewall Correlation | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `C100-SEC-020` | Potential Exfiltration Path Correlation | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `C100-SP-002` | Carrier Interface Error Burst | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `C100-SP-003` | BGP Peer Session Instability | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `C100-SP-004` | BGP Route Withdrawal Propagation | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `C100-SP-005` | Provider Edge Access Link Failure | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `C100-SP-006` | BGP Path Preference Shift | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `C100-SP-007` | Route Reflector Propagation Delay | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `C100-SP-008` | MPLS Label-Switched Path Degradation | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `C100-SP-009` | MPLS VPN Reachability Loss | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `C100-SP-010` | Segment Routing Policy Path Change | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `C100-SP-011` | SR-MPLS Constraint Violation | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `C100-SP-012` | SRv6 Service Path Interruption | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `C100-SP-013` | Carrier Core Congestion | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `C100-SP-014` | Provider Traffic Engineering Imbalance | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `C100-SP-015` | Optical Transport Dependency Degradation | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `C100-SP-016` | IOS XR Model-Driven Telemetry Loss | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `C100-SP-017` | Inter-AS Routing Leak Candidate | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `C100-SP-018` | Carrier Control-Plane Resource Pressure | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `C100-SP-019` | Multi-Domain Path Failover | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `C100-SP-020` | PE-CE Policy Mismatch | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-13.4.5` | AI/LLM Gateway Rate-Limit Breaches, Quota Burn, Tenant-Fairness Starva | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-14.1.1` | HVAC Performance Monitoring | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-14.1.29` | HVAC Setpoint Override Frequency and Duration | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-14.1.37` | Elevator Door Fault Frequency and Prediction | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-14.1.42` | Fire Alarm Panel Zone Health and Event Monitoring | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-14.2.1` | PLC/RTU Health Monitoring | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-14.2.2` | Process Variable Anomalies | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-14.3.11` | Greenhouse Humidity & Growth Optimization | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-14.3.9` | Cold Storage Room Temperature Excursion Alert | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-15.3.36` | Workspace Utilization and Ghost Booking Detection | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-17.1.4` | Guest Network Usage | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-21.1.1` | SCADA Alarm Rate Monitoring and Alarm Flooding Detection | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-21.1.12` | Outage Management System vs SCADA State Correlation | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-21.1.2` | Substation RTU Communication Failure | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-21.1.7` | Transformer Dissolved Gas Analysis (DGA) Trending | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-21.1.8` | Generator Trip Event Correlation | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-21.10.1` | Claims Processing Cycle Time Monitoring | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-21.10.2` | First Notice of Loss Channel Analysis | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-21.10.5` | Policy Underwriting Decision Audit Trail | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-21.10.6` | Insurance Fraud Ring Detection | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-21.10.8` | Catastrophe Event Claims Surge Capacity Monitoring | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-21.10.9` | Claims Leakage and Overpayment Detection | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-21.11.1` | Consumer credit card transaction monitoring | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-21.11.10` | Failed trade settlement ML prediction | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-21.11.13` | ATM usage pattern anomaly | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-21.11.14` | Retail banking transaction end-to-end trace | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-21.11.18` | MiFID II transaction reporting compliance | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-21.11.2` | Mobile device payment monitoring | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-21.11.21` | PCI Edge Processor cardholder filter | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-21.12.1` | Law enforcement accident reconstruction | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-21.12.10` | Higher-ed FERPA student record access audit | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-21.12.11` | Campus network outage academic impact | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-21.12.12` | Research grant expenditure anomaly | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-21.12.13` | Student information system login geo-velocity | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-21.12.16` | Voting system audit log integrity (where applicable) | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-21.12.17` | Emergency services CAD dispatch latency | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-21.12.18` | 911 call answer time SLA | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-21.12.19` | Public health outbreak reporting timeliness | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-21.12.2` | Law enforcement active investigation timeline | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-21.12.20` | Social services case management backlog | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-21.12.21` | Building permit inspection scheduling gap | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-21.13.1` | FERPA student record unauthorized access | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-21.13.10` | Telehealth student health portal latency | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-21.13.12` | Alumni donation portal anomaly | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-21.13.13` | Title IX case management timeline SLA | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-21.13.17` | Classroom AV system uptime | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-21.13.18` | Dormitory environmental safety sensor | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-21.13.2` | LMS (Canvas/Blackboard) login anomaly | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-21.14.1` | Genesys Cloud integration health | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-21.2.1` | Overall Equipment Effectiveness (OEE) Calculation | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-21.2.11` | Robotic Cell Cycle Time Deviation | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-21.2.12` | Conveyor Belt Speed and Jam Detection | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-21.2.2` | Unplanned Downtime Root Cause Correlation | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-21.2.3` | Production Batch Yield Tracking | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-21.2.4` | Quality SPC Chart Monitoring | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-21.3.1` | EHR System Response Time Monitoring | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-21.3.12` | Emergency Department Wait Time Tracking | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-21.3.2` | Clinical Application Uptime SLA Tracking | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-21.3.3` | Nurse Call System Response Time | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-21.3.4` | Blood Bank Refrigerator Temperature Compliance | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-21.3.5` | Pharmaceutical Cold Chain Deviation Alerting | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-21.4.1` | Fleet Vehicle GPS Tracking and Geofence Alerting | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-21.4.10` | Cold Chain Temperature Excursion for Perishable Goods | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-21.4.12` | Traffic Management System Sensor Availability | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-21.4.4` | Vehicle Diagnostic Trouble Code Monitoring | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-21.4.6` | Rail Signaling System Health Monitoring | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-21.4.9` | Last-Mile Delivery SLA Compliance | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-21.5.1` | Pipeline Pressure and Flow Rate Anomaly Detection | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-21.5.8` | Safety Instrumented System Trip Event Analysis | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-21.6.1` | POS Terminal Transaction Response Time Monitoring | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-21.6.10` | Mobile POS Device Battery and Connectivity | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-21.6.2` | Self-Checkout Lane Availability and Error Rate | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-21.6.3` | In-Store Wi-Fi and Network Infrastructure Health | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-21.6.5` | Click-and-Collect Order Fulfillment Cycle Time | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-21.6.6` | E-Commerce Platform Checkout Funnel Latency | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-21.7.1` | Baggage Handling System Throughput and Misroute Detection | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-21.7.10` | Airport SCADA Alarm Monitoring | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-21.7.2` | Security Lane Processing Time and Queue Length | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-21.7.3` | Aircraft Turnaround Time Monitoring (A-CDM) | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-21.7.5` | Flight Information Display System (FIDS) Health | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-21.7.7` | Runway and Taxiway Lighting System Status | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-21.7.9` | Passenger Flow and Terminal Capacity | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-21.8.1` | RAN Cell Site Availability | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-21.8.2` | Core Network Element Health (MME, SGW, PGW) | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-21.8.20` | Call Failure Root Cause Correlation (SIP + CDR + Element Logs) | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-21.8.3` | Subscriber Provisioning Workflow Completion Rate | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-21.8.4` | Network Capacity Planning (Spectrum Utilization Trending) | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-21.8.5` | Service Activation and Billing Mediation Latency | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-21.8.6` | OSS/BSS System Integration Health | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-21.8.8` | 5G NR gNodeB Performance Monitoring | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-21.9.1` | Treatment Plant Process Parameter Monitoring | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-21.9.3` | Distribution System Pressure Zone Monitoring | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-21.9.4` | Sewer Overflow Early Warning | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-21.9.6` | SCADA RTU Communication Health Across Remote Sites | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-22.1.16` | GDPR Consent Withdrawal Processing Enforcement | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-22.1.4` | GDPR Data Retention Policy Enforcement | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-22.1.5` | GDPR Consent Management Audit Trail | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-22.20.4` | CMMC AU.L2-3.3.2 — User-to-action traceability on CUI systems | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-22.20.6` | CMMC CM.L2-3.4.1 — Baseline configuration drift detection on CUI syste | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-22.20.7` | CMMC IR.L2-3.6.1 — Incident response lifecycle tracking for CUI incide | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-22.20.8` | CMMC SC.L2-3.13.8 — Cryptographic protection of CUI in transit | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-22.5.15` | MiFID II Conflicts of Interest — Personal Account Dealing Near Client  | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-22.5.16` | MiFID II Conflicts of Interest — Research Analyst vs Trading Desk Info | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-22.5.2` | MiFID II Communications Recording and Retention Audit | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-22.7.44` | Legal Hold Population — Elevated File Export Activity | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-22.8.7` | SOC 2 Privacy — Consent Log Integrity and Downstream Propagation Check | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-3.2.7` | Kubernetes Control Plane Health (apiserver, etcd, scheduler, controlle | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-4.2.19` | Azure Front Door / CDN Origin Errors and Cache Hit | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-4.3.15` | Cloud CDN Cache Hit Ratio and Egress | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-5.4.30` | Guest Network Access Patterns and Usage (Meraki MR) | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-5.8.26` | CDN Origin Hit Rate and Cache Efficiency (CloudFront / Akamai / Fastly | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-5.9.32` | CDN Edge Network Performance | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-8.1.1` | HTTP Error Rate Monitoring | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `UCR-8.3.1` | Consumer Lag Monitoring | CATALOGED | Cataloged candidate: a documented definition exists but NetSpout has no generator or scenario contract for it. |
| `arch_can_multi_building` | CAN: Campus Area Network - Multi-Building Backbone & Catalyst Center | CONTRACTED | Contract only in this release: no executable telemetry is implemented for this scenario |
| `arch_epn_isolated_intranet` | EPN: Enterprise Private Network - Isolated Corporate Intranet & Multi- | CONTRACTED | Contract only in this release: no executable telemetry is implemented for this scenario |
| `arch_gan_subsea_cloud` | GAN: Global Area Network - Worldwide Multi-Cloud & Subsea Cable Transi | CONTRACTED | Contract only in this release: no executable telemetry is implemented for this scenario |
| `arch_nas_storage_cluster` | NAS: Network-Attached Storage - NetApp ONTAP & PowerScale Clusters | CONTRACTED | Contract only in this release: no executable telemetry is implemented for this scenario |
| `arch_pan_iot_mesh` | PAN: Personal Area Network - IoT Sensor Cluster & Bluetooth Mesh | CONTRACTED | Contract only in this release: no executable telemetry is implemented for this scenario |
| `arch_san_fibre_channel` | SAN: Storage Area Network - Cisco MDS 9700 Fibre Channel & NVMe-oF | CONTRACTED | Contract only in this release: no executable telemetry is implemented for this scenario |
| `arch_wan_global_backbone` | WAN: Wide Area Network - Global BGP/MPLS L3VPN Backbone & Optical DWDM | CONTRACTED | Contract only in this release: no executable telemetry is implemented for this scenario |
| `mixed_vendor_enterprise` | Mixed-Vendor Enterprise Network (Cisco, Arista, Palo Alto, Fortinet, J | CONTRACTED | Contract only in this release: no executable telemetry is implemented for this scenario |
| `pure_cisco_enterprise` | Pure Cisco Enterprise Fabric (Catalyst 9600, 9500, 9300, 9800, ISE, DN | CONTRACTED | Contract only in this release: no executable telemetry is implemented for this scenario |
| `sdwan_connected_core` | Separate SD-WAN Environment Connected to Core Backbone (All Cisco) | CONTRACTED | Contract only in this release: no executable telemetry is implemented for this scenario |
| `service_provider_mixed` | Service Provider Network - Mixed Vendor (Cisco 8000, Juniper PTX, Noki | CONTRACTED | Contract only in this release: no executable telemetry is implemented for this scenario |
| `wireless_connected_core_cisco` | Enterprise Wireless Connected to Campus Core (All Cisco) | CONTRACTED | Contract only in this release: no executable telemetry is implemented for this scenario |
| `wireless_connected_core_mixed` | Enterprise Wireless Connected to Core (Mixed Vendor) | CONTRACTED | Contract only in this release: no executable telemetry is implemented for this scenario |
| `lateral_movement` | Ransomware / Lateral Spread (Port 445) | FORMAT_VALIDATED | Contract only in this release: no executable telemetry is implemented for this scenario |
| `normal_traffic` | Normal Operations (HTTP Round-Robin) | FORMAT_VALIDATED | Contract only in this release: no executable telemetry is implemented for this scenario |
