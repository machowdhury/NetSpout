# Scenarios

Generated from the scenario registries by `scripts/generate_customer_docs.py`; do not edit by hand. **372** scenarios are defined; **148** are runnable in this release. The rest are catalog entries only: they describe a use case but have no generator yet.

| Runnable scenarios by type | Count |
|---|---|
| Incident pack | 37 |
| NetFlow / IPFIX | 10 |
| Replay pack (recorded data) | 33 |
| Scenario pack | 26 |
| Scenario runner | 17 |
| Unified generation | 25 |

**Runnable** means a real generator and run path exist and the output was independently found by a Splunk search in an isolated lab. It does not mean certified, and it does not mean every sourcetype in the scenario has a vendor add-on installed. **Maturity** is the tier recorded in the registry. Delivery is through HEC unless a row says otherwise; start a run from *Use Case Explorer* or *Scenario Studio* (see [QUICKSTART](QUICKSTART.md)).

## Incident pack (37)

| ID | Name | Category | Vendor / technology | Sourcetypes | Telemetry | Maturity | Dashboard |
|---|---|---|---|---|---|---|---|
| `network_01_campus_link` | Campus link failure/recovery | INCIDENT_PACK |  | `netspout:network:syslog`, `netspout:network:metric` | event/metric | CONTRACTED | `pf_network_01_campus_link` |
| `network_02_vlan_trunk` | VLAN/trunk misconfiguration | INCIDENT_PACK |  | `netspout:network:syslog`, `netspout:network:metric` | event/metric | CONTRACTED | `pf_network_02_vlan_trunk` |
| `network_03_stp_storm` | STP loop/broadcast storm | INCIDENT_PACK |  | `netspout:network:syslog`, `netspout:network:metric` | event/metric | CONTRACTED | `pf_network_03_stp_storm` |
| `network_04_wan_brownout` | WAN latency/jitter/packet-loss brownout | INCIDENT_PACK |  | `netspout:network:syslog`, `netspout:network:metric` | event/metric | CONTRACTED | `pf_network_04_wan_brownout` |
| `network_05_dual_isp` | Dual-ISP failover/recovery | INCIDENT_PACK |  | `netspout:network:syslog`, `netspout:network:metric` | event/metric | CONTRACTED | `pf_network_05_dual_isp` |
| `network_06_bgp_flap` | BGP neighbor flap/route withdrawal | INCIDENT_PACK |  | `netspout:network:syslog`, `netspout:network:metric` | event/metric | CONTRACTED | `pf_network_06_bgp_flap` |
| `network_07_ospf_adjacency` | OSPF adjacency failure/reconvergence | INCIDENT_PACK |  | `netspout:network:syslog`, `netspout:network:metric` | event/metric | CONTRACTED | `pf_network_07_ospf_adjacency` |
| `network_08_firewall_policy` | Firewall policy misconfiguration | INCIDENT_PACK |  | `netspout:network:syslog`, `netspout:network:metric` | event/metric | CONTRACTED | `pf_network_08_firewall_policy` |
| `network_09_ddos_flood` | DDoS/traffic flood/mitigation | INCIDENT_PACK |  | `netspout:network:syslog`, `netspout:network:metric` | event/metric | CONTRACTED | `pf_network_09_ddos_flood` |
| `network_10_dns_failure` | DNS resolver failure/recovery | INCIDENT_PACK |  | `netspout:network:syslog`, `netspout:network:metric` | event/metric | CONTRACTED | `pf_network_10_dns_failure` |
| `network_11_dhcp_exhaustion` | DHCP pool exhaustion/recovery | INCIDENT_PACK |  | `netspout:network:syslog`, `netspout:network:metric` | event/metric | CONTRACTED | `pf_network_11_dhcp_exhaustion` |
| `network_12_dc_congestion` | Data-center congestion/queue drops | INCIDENT_PACK |  | `netspout:network:syslog`, `netspout:network:metric` | event/metric | CONTRACTED | `pf_network_12_dc_congestion` |
| `network_13_mtu_pmtud` | MTU mismatch/PMTUD failure | INCIDENT_PACK |  | `netspout:network:syslog`, `netspout:network:metric` | event/metric | CONTRACTED | `pf_network_13_mtu_pmtud` |
| `network_14_wireless_outage` | Wireless controller/AP outage | INCIDENT_PACK |  | `netspout:network:syslog`, `netspout:network:metric` | event/metric | CONTRACTED | `pf_network_14_wireless_outage` |
| `network_15_device_resources` | Device CPU/memory exhaustion | INCIDENT_PACK |  | `netspout:network:syslog`, `netspout:network:metric` | event/metric | CONTRACTED | `pf_network_15_device_resources` |
| `network_16_retail_uplink` | Retail branch uplink flap and checkout interruption | INCIDENT_PACK |  | `netspout:network:syslog`, `netspout:network:metric` | event/metric | CONTRACTED | `pf_network_16_retail_uplink` |
| `network_17_hospital_mac_auth` | Hospital access MAC instability and login retries | INCIDENT_PACK |  | `netspout:network:syslog`, `netspout:network:metric` | event/metric | CONTRACTED | `pf_network_17_hospital_mac_auth` |
| `network_18_payment_deny` | Perimeter deny burst and payment availability loss | INCIDENT_PACK |  | `netspout:network:syslog`, `netspout:network:metric` | event/metric | CONTRACTED | `pf_network_18_payment_deny` |
| `network_19_ips_service` | IPS attack burst and legitimate-session degradation | INCIDENT_PACK |  | `netspout:network:syslog`, `netspout:network:metric` | event/metric | CONTRACTED | `pf_network_19_ips_service` |
| `network_20_backend_link` | Distribution-link loss and backend monitor failure | INCIDENT_PACK |  | `netspout:network:syslog`, `netspout:network:metric` | event/metric | CONTRACTED | `pf_network_20_backend_link` |
| `network_21_partial_pool` | Partial load-balancer pool outage with perimeter demand | INCIDENT_PACK |  | `netspout:network:syslog`, `netspout:network:metric` | event/metric | CONTRACTED | `pf_network_21_partial_pool` |
| `network_22_authentication_storm` | Campus authentication retry storm at perimeter | INCIDENT_PACK |  | `netspout:network:syslog`, `netspout:network:metric` | event/metric | CONTRACTED | `pf_network_22_authentication_storm` |
| `network_23_containment_request` | Simulated NAC containment request and service-access change | INCIDENT_PACK |  | `netspout:network:syslog`, `netspout:network:metric` | event/metric | CONTRACTED | `pf_network_23_containment_request` |
| `network_24_policy_disagreement` | Multi-firewall path-policy disagreement | INCIDENT_PACK |  | `netspout:network:syslog`, `netspout:network:metric` | event/metric | CONTRACTED | `pf_network_24_policy_disagreement` |
| `network_25_mpls_recovery` | Primary MPLS path-change observation and branch SLA recovery | INCIDENT_PACK |  | `netspout:network:syslog`, `netspout:network:metric` | event/metric | CONTRACTED | `pf_network_25_mpls_recovery` |
| `network_26_maintenance` | Planned maintenance versus unplanned service outage | INCIDENT_PACK |  | `netspout:network:syslog`, `netspout:network:metric` | event/metric | CONTRACTED | `pf_network_26_maintenance` |
| `network_27_stale_sessions` | Authentication recovery with stale perimeter sessions | INCIDENT_PACK |  | `netspout:network:syslog`, `netspout:network:metric` | event/metric | CONTRACTED | `pf_network_27_stale_sessions` |
| `telco_01_ran_cell` | 5G RAN cell degradation | INCIDENT_PACK |  | `netspout:telecom:log`, `netspout:telecom:metric` | event/metric | CONTRACTED | `pf_telco_01_ran_cell` |
| `telco_02_registration_auth` | 5G registration/authentication failure | INCIDENT_PACK |  | `netspout:telecom:log`, `netspout:telecom:metric` | event/metric | CONTRACTED | `pf_telco_02_registration_auth` |
| `telco_03_slice_sla` | 5G network slice SLA violation | INCIDENT_PACK |  | `netspout:telecom:log`, `netspout:telecom:metric` | event/metric | CONTRACTED | `pf_telco_03_slice_sla` |
| `telco_04_ims_volte` | IMS/VoLTE call-quality degradation | INCIDENT_PACK |  | `netspout:telecom:log`, `netspout:telecom:metric` | event/metric | CONTRACTED | `pf_telco_04_ims_volte` |
| `telco_05_mobile_transport` | Mobile transport/fronthaul congestion | INCIDENT_PACK |  | `netspout:telecom:log`, `netspout:telecom:metric` | event/metric | CONTRACTED | `pf_telco_05_mobile_transport` |
| `telco_06_broadband_cpe` | Broadband CPE service outage | INCIDENT_PACK |  | `netspout:telecom:log`, `netspout:telecom:metric` | event/metric | CONTRACTED | `pf_telco_06_broadband_cpe` |
| `telco_07_sdwan_service` | SD-WAN service degradation | INCIDENT_PACK |  | `netspout:telecom:log`, `netspout:telecom:metric` | event/metric | CONTRACTED | `pf_telco_07_sdwan_service` |
| `telco_08_roaming_mobility` | Roaming/mobility failure | INCIDENT_PACK |  | `netspout:telecom:log`, `netspout:telecom:metric` | event/metric | CONTRACTED | `pf_telco_08_roaming_mobility` |
| `telco_09_core_user_plane` | 5G core user-plane degradation | INCIDENT_PACK |  | `netspout:telecom:log`, `netspout:telecom:metric` | event/metric | CONTRACTED | `pf_telco_09_core_user_plane` |
| `telco_10_cross_layer` | Cross-layer telecom service outage and SLA impact | INCIDENT_PACK |  | `netspout:telecom:log`, `netspout:telecom:metric` | event/metric | CONTRACTED | `pf_telco_10_cross_layer` |

## NetFlow / IPFIX (10)

| ID | Name | Category | Vendor / technology | Sourcetypes | Telemetry | Maturity | Dashboard |
|---|---|---|---|---|---|---|---|
| `NF-NOC-01-ELEPHANT` | NetFlow: bandwidth saturation and elephant flows | NETFLOW_SOLUTION |  | `netflow:collector` | event | CONTRACTED | `pf_NF-NOC-01-ELEPHANT` |
| `NF-NOC-02-DSCP` | NetFlow: QoS and DSCP marking validation | NETFLOW_SOLUTION |  | `netflow:collector` | event | CONTRACTED | `pf_NF-NOC-02-DSCP` |
| `NF-NOC-03-ROUTING-LOOP` | NetFlow: routing-loop indicators (flow-only) | NETFLOW_SOLUTION |  | `netflow:collector` | event | CONTRACTED | `pf_NF-NOC-03-ROUTING-LOOP` |
| `NF-NOC-04-ASYMMETRY` | NetFlow: asymmetric-routing indicators | NETFLOW_SOLUTION |  | `netflow:collector` | event | CONTRACTED | `pf_NF-NOC-04-ASYMMETRY` |
| `NF-NOC-05-BASELINE-DRIFT` | NetFlow: application baseline and duration drift | NETFLOW_SOLUTION |  | `netflow:collector` | event | CONTRACTED | `pf_NF-NOC-05-BASELINE-DRIFT` |
| `NF-SEC-06-DDOS` | NetFlow: volumetric DDoS indicators (SYN flood and UDP) | NETFLOW_SOLUTION |  | `netflow:collector` | event | CONTRACTED | `pf_NF-SEC-06-DDOS` |
| `NF-SEC-07-PORTSCAN` | NetFlow: network reconnaissance and port scanning | NETFLOW_SOLUTION |  | `netflow:collector` | event | CONTRACTED | `pf_NF-SEC-07-PORTSCAN` |
| `NF-SEC-08-EXFIL` | NetFlow: outbound data-exfiltration indicators | NETFLOW_SOLUTION |  | `netflow:collector` | event | CONTRACTED | `pf_NF-SEC-08-EXFIL` |
| `NF-SEC-09-BEACON` | NetFlow: command-and-control beaconing indicators | NETFLOW_SOLUTION |  | `netflow:collector` | event | CONTRACTED | `pf_NF-SEC-09-BEACON` |
| `NF-SEC-10-DNS-FLOW` | NetFlow: DNS-tunneling indicators (flow-only, limited evidence) | NETFLOW_SOLUTION |  | `netflow:collector` | event | CONTRACTED | `pf_NF-SEC-10-DNS-FLOW` |

## Replay pack (recorded data) (33)

| ID | Name | Category | Vendor / technology | Sourcetypes | Telemetry | Maturity | Dashboard |
|---|---|---|---|---|---|---|---|
| `ind_aero_defense_endpoint_c2` | Defense contractor: C2 callback, endpoint pipeline and privileged-acc… | REPLAY_PACK |  | `SysdigSecureEvents`, `bitdefender:gz`, `ccx:beyondinsight:passwordsafe`, `cybereason:malops`, `osquery:results`, `sail… | event | CONTRACTED | `pf_ind_aero_defense_endpoint_c2` |
| `ind_agri_edge_gateway_health` | Agritech: edge gateway routing observation and Linux gateway authenti… | REPLAY_PACK |  | `auditd`, `claroty:cef`, `linux_messages_syslog`, `mikrotik:routeros`, `nginx:access`, `sysmon:linux`, `traefik:access:… | event | CONTRACTED | `pf_ind_agri_edge_gateway_health` |
| `ind_bank_account_takeover_resilience` | Retail banking: workstation credential compromise, cloud SSO abuse, b… | REPLAY_PACK |  | `OktaIM2:log`, `XmlWinEventLog:Microsoft-Windows-NTLM/Operational`, `XmlWinEventLog:Microsoft-Windows-PowerShell/Operat… | event | CONTRACTED | `pf_ind_bank_account_takeover_resilience` |
| `ind_bank_payments_edge_defense` | Payments edge: WAF/IDS/firewall observation then cloud control-plane … | REPLAY_PACK |  | `aws:cloudtrail`, `aws:cloudwatchlogs:vpcflow`, `barracuda:waf:web_firewall`, `darktrace`, `imperva:securesphere:cef`, … | event | CONTRACTED | `pf_ind_bank_payments_edge_defense` |
| `ind_edu_campus_identity_and_collab` | Campus: cloud identity attack and collaboration-platform audit | REPLAY_PACK |  | `OktaIM2:log`, `azure:monitor:aad`, `azure:monitor:activity`, `github:enterprise:audit`, `gitlab:audit:json`, `gws:repo… | event | CONTRACTED | `pf_ind_edu_campus_identity_and_collab` |
| `ind_energy_scada_proxy_intrusion` | Utility: OT proxy host hunt and C2 callback detection | REPLAY_PACK |  | `bluecoat:proxysg:access:file`, `docker_events`, `nozomi:universal_alert`, `osquery:results`, `suricata`, `wazuh:alerts` | event | CONTRACTED | `pf_ind_energy_scada_proxy_intrusion` |
| `ind_energy_substation_edge_observation` | Substation edge: OT routing observation and network platform health | REPLAY_PACK |  | `cisco:sdwan:ENVIRONMENTAL-1-ALERT`, `cisco:sdwan:EVENTLIB-3-CPUHOG`, `cisco:sdwan:IOSXE-3-PLATFORM`, `cisco:sdwan:IOSX… | event | CONTRACTED | `pf_ind_energy_substation_edge_observation` |
| `ind_gov_agency_mail_exfiltration` | Agency: cloud mail exfiltration with containment and endpoint pipeline | REPLAY_PACK |  | `aws:cloudfront:accesslogs`, `aws:cloudtrail:lake`, `bitdefender:gz`, `cisco:duo:administrator`, `cisco:secure_access:s… | event | CONTRACTED | `pf_ind_gov_agency_mail_exfiltration` |
| `ind_gov_citizen_identity_attack` | Citizen services: cloud identity attack, AWS reconnaissance, privileg… | REPLAY_PACK |  | `OktaIM2:log`, `SysdigSecureEvents`, `aws:cloudtrail`, `aws:cloudwatchlogs:vpcflow`, `azure:monitor:aad`, `azure:monito… | event | CONTRACTED | `pf_ind_gov_citizen_identity_attack` |
| `ind_health_clinical_network_edge` | Hospital network: edge and DNS/proxy health with wireless threat | REPLAY_PACK |  | `bro:conn:json`, `cisco:catalyst:rogue:verbose`, `cisco:catalyst:security:profile_signatures`, `cisco:catalyst:threat:s… | event | CONTRACTED | `pf_ind_health_clinical_network_edge` |
| `ind_health_ehr_ransomware_readiness` | Hospital: endpoint credential attack with backup and privileged-acces… | REPLAY_PACK |  | `SysdigSecureEvents`, `XmlWinEventLog:Microsoft-Windows-NTLM/Operational`, `XmlWinEventLog:Microsoft-Windows-PowerShell… | event | CONTRACTED | `pf_ind_health_ehr_ransomware_readiness` |
| `ind_hospitality_guest_network_defense` | Hospitality: edge defense and guest/staff identity attack | REPLAY_PACK |  | `OktaIM2:log`, `azure:monitor:aad`, `azure:monitor:activity`, `barracuda:waf:web_firewall`, `darktrace`, `gws:reports:l… | event | CONTRACTED | `pf_ind_hospitality_guest_network_defense` |
| `ind_insurance_claims_platform_audit` | Claims platform: SaaS and database/message audit with cloud mail exfi… | REPLAY_PACK |  | `aws:cloudfront:accesslogs`, `aws:cloudtrail:lake`, `cisco:duo:administrator`, `cisco:secure_access:security_events_rav… | event | CONTRACTED | `pf_ind_insurance_claims_platform_audit` |
| `ind_insurance_underwriting_exposure` | Underwriting data platform: exposure management, vault and identity a… | REPLAY_PACK |  | `Confluence:audit log`, `SysdigSecureEvents`, `ccx:beyondinsight:passwordsafe`, `elasticsearch:json`, `hashicorp_vault_… | event | CONTRACTED | `pf_ind_insurance_underwriting_exposure` |
| `ind_legal_matter_data_exfiltration` | Law firm: client-matter data exfiltration across mail, vault and wiki | REPLAY_PACK |  | `Confluence:audit log`, `aws:cloudfront:accesslogs`, `aws:cloudtrail:lake`, `cisco:duo:administrator`, `cisco:secure_ac… | event | CONTRACTED | `pf_ind_legal_matter_data_exfiltration` |
| `ind_media_content_delivery_exfil` | Media: content-delivery access with cloud-mail exfiltration | REPLAY_PACK |  | `aws:cloudfront:accesslogs`, `aws:cloudtrail:lake`, `cisco:duo:administrator`, `cisco:secure_access:security_events_rav… | event | CONTRACTED | `pf_ind_media_content_delivery_exfil` |
| `ind_mfg_it_ot_convergence` | Plant: OT proxy and edge routing observation, then command-and-contro… | REPLAY_PACK |  | `bluecoat:proxysg:access:file`, `claroty:cef`, `docker_events`, `mikrotik:routeros`, `nginx:access`, `nozomi:universal_… | event | CONTRACTED | `pf_ind_mfg_it_ot_convergence` |
| `ind_mfg_plant_network_health` | Plant network: platform degradation and change-induced outage | REPLAY_PACK |  | `cisco:sdwan:BGP-5-ADJCHANGE`, `cisco:sdwan:BGP-5-NBR_RESET`, `cisco:sdwan:CDP-4-NATIVE_VLAN_MISMATCH`, `cisco:sdwan:DM… | event | CONTRACTED | `pf_ind_mfg_plant_network_health` |
| `ind_nonprofit_donor_platform_attack` | Non-profit: staff identity attack and cloud-mail exfiltration of dono… | REPLAY_PACK |  | `OktaIM2:log`, `aws:cloudfront:accesslogs`, `aws:cloudtrail:lake`, `azure:monitor:aad`, `azure:monitor:activity`, `cisc… | event | CONTRACTED | `pf_ind_nonprofit_donor_platform_attack` |
| `ind_realestate_building_exposure` | Property technology: exposure management and collaboration audit | REPLAY_PACK |  | `elasticsearch:json`, `github:enterprise:audit`, `gitlab:audit:json`, `ibm:qradar:offense`, `qualys:activityLog`, `rapi… | event | CONTRACTED | `pf_ind_realestate_building_exposure` |
| `ind_retail_ecommerce_cloud_recon` | E-commerce: AWS reconnaissance and escalation with exposure management | REPLAY_PACK |  | `aws:cloudtrail`, `aws:cloudwatchlogs:vpcflow`, `elasticsearch:json`, `ibm:qradar:offense`, `qualys:activityLog`, `rapi… | event | CONTRACTED | `pf_ind_retail_ecommerce_cloud_recon` |
| `ind_retail_pos_edge_defense` | Retail stores: edge defense observation and endpoint threat pipeline | REPLAY_PACK |  | `barracuda:waf:web_firewall`, `bitdefender:gz`, `cybereason:malops`, `darktrace`, `imperva:securesphere:cef`, `pfsense:… | event | CONTRACTED | `pf_ind_retail_pos_edge_defense` |
| `ind_saas_platform_runtime_attack` | SaaS platform: Kubernetes container escape, collaboration audit and e… | REPLAY_PACK |  | `elasticsearch:json`, `github:enterprise:audit`, `gitlab:audit:json`, `ibm:qradar:offense`, `kube:audit`, `kube:contain… | event | CONTRACTED | `pf_ind_saas_platform_runtime_attack` |
| `ind_telco_access_and_wireless_health` | Telecom NOC: RADIUS/NAC outage, platform degradation and rogue wirele… | REPLAY_PACK |  | `cisco:catalyst:rogue:verbose`, `cisco:catalyst:security:profile_signatures`, `cisco:catalyst:threat:summary`, `cisco:c… | event | CONTRACTED | `pf_ind_telco_access_and_wireless_health` |
| `ind_telco_change_induced_outage` | Telecom NOC: change-induced SD-WAN outage, then edge threat pipeline | REPLAY_PACK |  | `cisco:sdwan:BGP-5-ADJCHANGE`, `cisco:sdwan:BGP-5-NBR_RESET`, `cisco:sdwan:CDP-4-NATIVE_VLAN_MISMATCH`, `cisco:sdwan:DM… | event | CONTRACTED | `pf_ind_telco_change_induced_outage` |
| `ind_transport_fleet_network_change` | Logistics network: change-induced outage and edge routing observation | REPLAY_PACK |  | `cisco:sdwan:BGP-5-ADJCHANGE`, `cisco:sdwan:BGP-5-NBR_RESET`, `cisco:sdwan:CDP-4-NATIVE_VLAN_MISMATCH`, `cisco:sdwan:DM… | event | CONTRACTED | `pf_ind_transport_fleet_network_change` |
| `rp_agentic_ai_mcp_runtime_hybrid` | Agentic AI: recorded MCP server log plus native exfiltration attempt … | REPLAY_PACK |  | `mcp:jsonrpc`, `ollama:server`, `osquery:results` | event | CONTRACTED | `pf_rp_agentic_ai_mcp_runtime_hybrid` |
| `rp_cloud_control_plane_activity` | AWS control-plane activity (replayed CloudTrail) | REPLAY_PACK |  | `aws:cloudtrail` | event | CONTRACTED | `pf_rp_cloud_control_plane_activity` |
| `rp_edr_and_cloud_activity` | Endpoint sensor and cloud audit side by side (aligned in time only) | REPLAY_PACK |  | `aws:cloudtrail`, `crowdstrike:events:sensor` | event | CONTRACTED | `pf_rp_edr_and_cloud_activity` |
| `rp_linux_credential_access` | Linux credential-file access with system context (replayed recordings) | REPLAY_PACK |  | `auditd`, `linux_messages_syslog` | event | CONTRACTED | `pf_rp_linux_credential_access` |
| `rp_web_exploitation_recordings` | Web exploitation observed from three recordings (aligned in time only) | REPLAY_PACK |  | `crushftp:sessionlogs`, `nginx:access`, `suricata` | event | CONTRACTED | `pf_rp_web_exploitation_recordings` |
| `rp_windows_endpoint_process_chain` | Windows endpoint process and network activity (replayed Sysmon) | REPLAY_PACK |  | `XmlWinEventLog` | event | CONTRACTED | `pf_rp_windows_endpoint_process_chain` |
| `rp_workload_sysmon_ebpf_hybrid` | Linux workload: recorded Sysmon-for-Linux plus native eBPF hunt (hybr… | REPLAY_PACK |  | `bro:conn:json`, `cisco:cloud_security:dns`, `cisco:cloud_security:firewall`, `cisco:cloud_security:proxy`, `cisco:isov… | event | CONTRACTED | `pf_rp_workload_sysmon_ebpf_hybrid` |

## Scenario pack (26)

| ID | Name | Category | Vendor / technology | Sourcetypes | Telemetry | Maturity | Dashboard |
|---|---|---|---|---|---|---|---|
| `ub1_ot_proxy_host_hunt` | OT Tamper to Container Host Hunt (Universe Batch-1) | SECURITY | nozomi_networks, broadcom_symantec, wazuh, docker | `nozomi:universal_alert`, `bluecoat:proxysg:access:file`, `wazuh:alerts`, `docker_events` | event | CONTRACTED | `pf_ub1_ot_proxy_host_hunt` |
| `ub2_cloud_identity_mail_hunt` | Ub2 Cloud Identity Mail Hunt | SECURITY | hashicorp, atlassian, proofpoint | `hashicorp_vault_audit_log`, `Confluence:audit log`, `proofpoint_tap_siem` | event | CONTRACTED | `pf_ub2_cloud_identity_mail_hunt` |
| `ub2_database_backup_integrity` | Ub2 Database Backup Integrity | INFRASTRUCTURE | mongodb, veeam | `mongodb:log`, `veeam_vbr_syslog` | event | CONTRACTED | `pf_ub2_database_backup_integrity` |
| `ub2_ot_edge_routing_observation` | Ub2 Ot Edge Routing Observation | INFRASTRUCTURE | traefik, claroty, nginx_f5, mikrotik | `traefik:access:json`, `claroty:cef`, `nginx:access`, `mikrotik:routeros` | event | CONTRACTED | `pf_ub2_ot_edge_routing_observation` |
| `ub3_database_message_audit` | Ub3 Database Message Audit | INFRASTRUCTURE | oracle, ibm_mq | `oracle:audit:text`, `ibm:mq:errorlog` | event | CONTRACTED | `pf_ub3_database_message_audit` |
| `ub3_identity_runtime_audit` | Ub3 Identity Runtime Audit | INFRASTRUCTURE | sysdig, sailpoint, beyondtrust, tenable | `SysdigSecureEvents`, `sailpoint_identitynow`, `ccx:beyondinsight:passwordsafe`, `tenable:io:audit_logs` | event | CONTRACTED | `pf_ub3_identity_runtime_audit` |
| `ub3_multivendor_edge_observation` | Ub3 Multivendor Edge Observation | INFRASTRUCTURE | pfsense_netgate, imperva, barracuda, darktrace | `pfsense:filterlog`, `imperva:securesphere:cef`, `barracuda:waf:web_firewall`, `darktrace` | event | CONTRACTED | `pf_ub3_multivendor_edge_observation` |
| `ub4_endpoint_threat_pipeline` | Ub4 Endpoint Threat Pipeline | SECURITY | cybereason, sentinelone, tanium, trellix_mcafee, … | `cybereason:malops`, `sentinelone:channel:threats`, `tanium:discover:managed`, `trellix_epo:threat_events`, `bitdefende… | event | CONTRACTED | `pf_ub4_endpoint_threat_pipeline` |
| `ub4_exposure_infra_logging` | Ub4 Exposure Infra Logging | INFRASTRUCTURE | qualys, rapid7, ibm_qradar, elastic | `qualys:activityLog`, `rapid7:insightvm:asset:vulnerability_finding`, `ibm:qradar:offense`, `elasticsearch:json` | event | CONTRACTED | `pf_ub4_exposure_infra_logging` |
| `ub4_saas_collaboration_audit` | Ub4 Saas Collaboration Audit | INFRASTRUCTURE | slack, github, gitlab | `slack:audit`, `github:enterprise:audit`, `gitlab:audit:json` | event | CONTRACTED | `pf_ub4_saas_collaboration_audit` |
| `ub5_cisco_change_induced_outage` | Cisco Change-Induced Outage | NETWORK_OPERATIONS | cisco_sdwan | `cisco:sdwan:OSPF-5-ADJCHG`, `cisco:sdwan:BGP-5-ADJCHANGE`, `cisco:sdwan:MSDP-5-PEER_UPDOWN`, `cisco:sdwan:DMI-5-SYNC_N… | event | CONTRACTED | `pf_ub5_cisco_change_induced_outage` |
| `ub5_cisco_nac_radius_outage` | Cisco NAC RADIUS Outage | NETWORK_OPERATIONS | cisco_sdwan | `cisco:sdwan:AAA-6-METHOD_LIST_STATE`, `cisco:sdwan:CTS-3-AAA_NO_RADIUS_SERVER`, `cisco:sdwan:AAA-6-NOTIFY_MLIST_STATE_… | event | CONTRACTED | `pf_ub5_cisco_nac_radius_outage` |
| `ub5_cisco_platform_health_degradation` | Cisco Platform Health Degradation | NETWORK_OPERATIONS | cisco_sdwan | `cisco:sdwan:PKI-6-AUTHORITATIVE_CLOCK`, `cisco:sdwan:MDT_CONNECTION-6-STATE_CHANGED`, `cisco:sdwan:ENVIRONMENTAL-1-ALE… | event | CONTRACTED | `pf_ub5_cisco_platform_health_degradation` |
| `ub6_catalyst_wireless_rogue_threat` | Catalyst Wireless Rogue And Threat Summary | NETWORK_OPERATIONS | cisco_catalyst | `cisco:catalyst:security:profile_signatures`, `cisco:catalyst:threat:summary:legacy`, `cisco:catalyst:rogue:verbose`, `… | event | CONTRACTED | `pf_ub6_catalyst_wireless_rogue_threat` |
| `ub6_sdwan_utd_threat_pipeline` | SD-WAN UTD Threat Pipeline | SECURITY | cisco_sdwan | `cisco:sdwan:utdhealth`, `cisco:sdwan:ssetunnels`, `cisco:sdwan:utd:logs` | event | CONTRACTED | `pf_ub6_sdwan_utd_threat_pipeline` |
| `wave2_agentic_ai_exfil_attempt` | Agentic AI Runtime Exfiltration Attempt (Wave-2 pack) | SECURITY | ollama, model_context_protocol, osquery | `ollama:server`, `mcp:jsonrpc`, `osquery:results` | event | CONTRACTED | `pf_wave2_agentic_ai_exfil_attempt` |
| `wave2_aws_recon_escalation` | AWS CloudTrail Recon & Escalation (Wave-2 pack) | SECURITY | amazon_aws | `aws:cloudtrail`, `aws:cloudwatchlogs:vpcflow` | event | CONTRACTED | `pf_wave2_aws_recon_escalation` |
| `wave2_bigip_openconfig_itops` | Big-IP ADC & OpenConfig Observability Health (Wave-2 pack) | SERVICE_ASSURANCE | cisco, crushftp, f5 | `cisco:sfw:estreamer`, `cisco:nvm:flowdata:v2`, `crushftp:sessionlogs`, `f5:bigip:ltm` | event | CONTRACTED | `pf_wave2_bigip_openconfig_itops` |
| `wave2_c2_callback_detection` | Network C2 Callback & Discovery Behaviors (Wave-2 pack) | SECURITY | suricata_oisf, osquery | `suricata`, `osquery:results` | event | CONTRACTED | `pf_wave2_c2_callback_detection` |
| `wave2_cloud_identity_sso_hunt` | Cross-Cloud Identity SSO Brute Force (Wave-2 pack) | SECURITY | microsoft_365, microsoft_azure, okta, google_work… | `o365:management:activity`, `azure:monitor:aad`, `azure:monitor:activity`, `gws:reports:login`, `OktaIM2:log` | event | CONTRACTED | `pf_wave2_cloud_identity_sso_hunt` |
| `wave2_k8s_container_escape` | Kubernetes Auth Abuse + Container Escape (Wave-2 pack) | SECURITY | kubernetes, suricata_oisf | `kube:audit`, `kube:container:falco`, `suricata` | event | CONTRACTED | `pf_wave2_k8s_container_escape` |
| `wave2_linux_auth_anomaly` | Linux Infrastructure Auth Anomaly (Wave-2 pack) | SECURITY | linux_infrastructure, microsoft_windows | `auditd`, `linux_messages_syslog`, `sysmon:linux` | event | CONTRACTED | `pf_wave2_linux_auth_anomaly` |
| `wave2_ws_credential_compromise_chain` | Windows Credential Compromise Kill Chain (Wave-2 pack) | SECURITY | microsoft_windows, crowdstrike | `XmlWinEventLog:Security`, `XmlWinEventLog:Microsoft-Windows-Sysmon/Operational`, `XmlWinEventLog:Microsoft-Windows-Pow… | event | CONTRACTED | `pf_wave2_ws_credential_compromise_chain` |
| `wave3_cloudmail_exfil` | Cloud Mail Exfiltration Chain (Wave-3 pack) | SECURITY | cisco_duo, microsoft_365, google_workspace, zscal… | `cisco:duo:administrator`, `o365:reporting:messagetrace`, `o365:graph:messagetrace`, `gsuite:gmail:bigquery`, `zscalern… | event | CONTRACTED | `pf_wave3_cloudmail_exfil` |
| `wave3_ebpf_workload_hunt` | eBPF Workload Hunt (Wave-3 pack) | SECURITY | cisco_ios, cisco_asa, zeek | `cisco:isovalent`, `cisco:isovalent:processExec`, `cisco:isovalent:processConnect`, `cisco:cloud_security:dns`, `cisco:… | event | CONTRACTED | `pf_wave3_ebpf_workload_hunt` |
| `wave3_vsphere_hostpath_triage` | vSphere Host Path Triage (Wave-3 pack) | OPERATIONS | microsoft_windows, cisco_sdwan, vmware_nsx, linux… | `XmlWinEventLog:System`, `cisco:sdwan:syslog`, `dhcpd`, `iis`, `vmw-syslog`, `linux_secure`, `cisco:sdwan:access`, `cis… | event | CONTRACTED | `pf_wave3_vsphere_hostpath_triage` |

## Scenario runner (17)

| ID | Name | Category | Vendor / technology | Sourcetypes | Telemetry | Maturity | Dashboard |
|---|---|---|---|---|---|---|---|
| `arch_lan_campus_access` | LAN: Local Area Network - Campus Switching & 802.1Q Segments | NETWORK_OPERATIONS | cisco_catalyst, cisco_ise | `cisco:catalyst:security:events`, `cisco:ios:syslog`, `cisco:ise:nac:8021x` | event | CERTIFIED | `pf_arch_lan_campus_access` |
| `arch_man_carrier_ring` | MAN: Metropolitan Area Network - 100G Carrier Ethernet Ring & G.8032 … | SERVICE_PROVIDER | nokia_sros, juniper_junos, arista_eos | `nokia:sros:syslog`, `juniper:junos`, `arista:eos` | event | CERTIFIED | `pf_arch_man_carrier_ring` |
| `arch_vpn_remote_workforce` | VPN: Virtual Private Network - Cisco AnyConnect & Site-to-Site IPsec | WAN | cisco_asa, cisco_duo | `cisco:duo:remote:vpn`, `cisco:duo:push:prompt`, `cisco:asa` | event | CERTIFIED | `pf_arch_vpn_remote_workforce` |
| `arch_wlan_meraki_catalyst` | WLAN: Wireless Local Area Network - Catalyst 9800 & Meraki Wi-Fi 6E/7 | WIRELESS | cisco_catalyst, meraki | `cisco:catalyst:rogue:threat_details`, `meraki:accesspoints`, `cisco:catalyst:clienthealth` | event | CERTIFIED | `pf_arch_wlan_meraki_catalyst` |
| `cisco_aci_microburst` | Data Center Fabric ACI Ingress Microburst Traffic | DATACENTER | cisco_nexus, cisco_aci | `cisco:dc:nexus9k:syslog`, `cisco:dc:aci:health`, `cisco:ios:mdt` | event | CERTIFIED | `pf_cisco_aci_microburst` |
| `cisco_campus_rogue` | Campus Core L2/3 Disturbance & Rogue AP | WIRELESS | cisco_catalyst, cisco_ise | `cisco:catalyst:security:events`, `cisco:catalyst:rogue:threat_details`, `cisco:ise:syslog`, `cisco:ios:syslog` | event | CERTIFIED | `pf_cisco_campus_rogue` |
| `cisco_sdwan_brownout` | Enterprise WAN Circuit Brownout & App Route Failover | WAN | cisco_sdwan | `cisco:sdwan:linkhealth`, `cisco:sdwan:BGP-5-ADJCHANGE`, `cisco:thousandeyes:path-vis`, `cisco:thousandeyes:metric` | event/metric | CERTIFIED | `pf_cisco_sdwan_brownout` |
| `ddos_attack` | Distributed Denial of Service (DDoS SYN Flood) | SECURITY | cisco_asa, f5, nginx | `cisco:asa`, `f5:bigip:ltm`, `nginx:plus:kv` | event | VALIDATED | `pf_ddos_attack` |
| `mixed_backbone_optical` | Multicast/MPLS Backbone Optical Carrier Shift | DATACENTER | nokia_sros, juniper_junos, arista_eos | `nokia:sros:syslog`, `juniper:junos`, `arista:flow:ipfix` | event | CERTIFIED | `pf_mixed_backbone_optical` |
| `mixed_edge_breach` | Distributed Edge Breach & Internal Probing | SECURITY | palo_alto, fortinet, cisco_asa, arista_eos, junip… | `meraki:assurancealerts`, `pan:threat`, `pan:traffic`, `fortinet:fortigate:utm`, `nginx:plus:kv` | event | CERTIFIED | `pf_mixed_edge_breach` |
| `mixed_sase_degradation` | SASE Cloud Ingress App Degradation & Synthetic Validation | NETWORK_OPERATIONS | zscaler, palo_alto, cisco_thousandeyes, cisco_nex… | `zscaler:zia`, `pan:threat`, `cisco:thousandeyes:metric`, `cisco:dc:nexus9k:syslog` | event/metric | CERTIFIED | `pf_mixed_sase_degradation` |
| `network_security_correlation` | Network Degradation With Security Correlation | MIXED | cisco_catalyst, palo_alto | `cisco:catalyst:security:events`, `pan:traffic`, `pan:threat`, `pan:system`, `sc4snmp:metric` | event/metric | VALIDATED | `pf_network_security_correlation` |
| `openconfig_mdt_streaming` | OpenConfig MDT Streaming & Telemetry Assurance | SERVICE_ASSURANCE | cisco_ios, juniper_junos, arista_eos, cisco_catal… | `cisco:ios:mdt`, `arista:telemetry:json`, `cisco:ios:syslog` | event | CERTIFIED | `pf_openconfig_mdt_streaming` |
| `paloalto_threat_investigation` | Palo Alto Networks Threat Investigation | SECURITY | palo_alto | `pan:traffic`, `pan:threat`, `pan:system` | event | VALIDATED | `pf_paloalto_threat_investigation` |
| `payment_processing_degradation` | Financial Services Payment Application Degradation | INDUSTRY_VERTICAL | palo_alto, cisco_catalyst | `pan:traffic`, `pan:threat`, `pan:system`, `cisco:catalyst:security:events`, `sc4snmp:metric` | event/metric | VALIDATED | `pf_payment_processing_degradation` |
| `service_provider_cisco` | Service Provider Network - All Cisco (Cisco 8000, NCS 5500, IOS-XR SR… | SERVICE_PROVIDER | cisco_ios | `cisco:ios:mdt:metric`, `cisco:ios:syslog`, `netspout:snmp:trap`, `netspout:snmp:poll` | event/metric | CERTIFIED | `pf_service_provider_cisco` |
| `sql_injection` | SQL Injection / Application Breach | SECURITY | cisco_asa, nginx, postgresql | `cisco:asa`, `nginx:plus:kv`, `postgresql:audit` | event | CERTIFIED | `pf_sql_injection` |

## Unified generation (25)

| ID | Name | Category | Vendor / technology | Sourcetypes | Telemetry | Maturity | Dashboard |
|---|---|---|---|---|---|---|---|
| `AI-001` | Indirect Prompt Injection | PROMPT_INJECTION | NetSpout | `netspout:phase12:agentic` | event | VALIDATED | `pf_AI-001` |
| `AI-002` | Unauthorized Tool Invocation | TOOL_AUTHORIZATION | NetSpout | `netspout:phase12:agentic` | event | VALIDATED | `pf_AI-002` |
| `AI-003` | MCP Tool Output Manipulation | MCP_TOOL_OUTPUT | NetSpout | `netspout:phase12:agentic` | event | VALIDATED | `pf_AI-003` |
| `AI-004` | Agent Identity and Privilege Drift | IDENTITY_DRIFT | NetSpout | `netspout:phase12:agentic` | event | VALIDATED | `pf_AI-004` |
| `AI-005` | A2A Delegation Abuse | A2A_DELEGATION | NetSpout | `netspout:phase12:agentic` | event | VALIDATED | `pf_AI-005` |
| `AI-006` | Multi-Agent Incident | MULTI_AGENT_INCIDENT | NetSpout | `netspout:phase12:agentic` | event | VALIDATED | `pf_AI-006` |
| `C100-CRI-002` | Telecom Operations Network Degradation — Correlated Reference | TELECOMMUNICATIONS | Cisco | `netspout:cisco:iosxe:syslog`, `netspout:cisco:iosxr:syslog` | event | CERTIFIED | `pf_C100-CRI-002` |
| `C100-DC-001` | Nexus Fabric Uplink Degradation — NX-OS Reference | INTERFACE_HEALTH | Cisco | `netspout:cisco:nxos:syslog` | event | CERTIFIED | `pf_C100-DC-001` |
| `C100-ENT-001` | Campus Access Link Degradation — IOS XE Reference | INTERFACE_HEALTH | Cisco | `netspout:cisco:iosxe:syslog` | event | CERTIFIED | `pf_C100-ENT-001` |
| `C100-SEC-001` | Secure Firewall Suspicious Connection Burst — ASA Reference | FIREWALL_ACTIVITY | Cisco | `netspout:cisco:asa:syslog` | event | CERTIFIED | `pf_C100-SEC-001` |
| `P12-XD-001` | AI Agent to Infrastructure | AGENT_INFRASTRUCTURE | NetSpout | `netspout:phase12:cross_domain` | event | VALIDATED | `pf_P12-XD-001` |
| `P12-XD-002` | Supply Chain to Application | SUPPLY_CHAIN_APPLICATION | NetSpout | `netspout:phase12:cross_domain` | event | VALIDATED | `pf_P12-XD-002` |
| `SC-001` | Suspicious Dependency Change | DEPENDENCY_CHANGE | NetSpout | `netspout:phase12:supply_chain` | event | VALIDATED | `pf_SC-001` |
| `SC-002` | CI Workflow Permission Escalation | CI_PERMISSION_CHANGE | NetSpout | `netspout:phase12:supply_chain` | event | VALIDATED | `pf_SC-002` |
| `SC-003` | Build Artifact Provenance Gap | PROVENANCE_GAP | NetSpout | `netspout:phase12:supply_chain` | event | VALIDATED | `pf_SC-003` |
| `SC-004` | Repository Automation Abuse | AUTOMATION_AUTHORIZATION | NetSpout | `netspout:phase12:supply_chain` | event | VALIDATED | `pf_SC-004` |
| `SC-005` | Supply Chain to Runtime Correlation | BUILD_RUNTIME_CORRELATION | NetSpout | `netspout:phase12:supply_chain` | event | VALIDATED | `pf_SC-005` |
| `SEC-P9-A-TRAFFIC-FLOOD` | Controlled Traffic Flood Indicators | TRAFFIC_FLOOD | IETF | `netflow:collector` | event | VALIDATED | `pf_SEC-P9-A-TRAFFIC-FLOOD` |
| `SEC-P9-B-DNS-ANOMALY` | DNS Diversity and NXDOMAIN Indicators | DNS_ANOMALY | IETF | `netspout:dns:wire` | event | VALIDATED | `pf_SEC-P9-B-DNS-ANOMALY` |
| `SEC-P9-C-BEACONING` | Periodic External Communication Indicators | BEACONING | IETF | `netflow:collector`, `netspout:dns:wire` | event | VALIDATED | `pf_SEC-P9-C-BEACONING` |
| `SEC-P9-D-INTERNAL-RECON` | Internal Reconnaissance Indicators | INTERNAL_RECON | IETF | `netflow:collector` | event | VALIDATED | `pf_SEC-P9-D-INTERNAL-RECON` |
| `SEC-P9-E-DNS-TUNNEL` | DNS Tunneling and Exfiltration Indicators | DNS_TUNNEL_INDICATORS | IETF | `netflow:collector`, `netspout:dns:wire` | event | VALIDATED | `pf_SEC-P9-E-DNS-TUNNEL` |
| `SEC-P9-F-CROSS-SOURCE` | Cross-Source DNS, Beaconing, and Reconnaissance Incident | CROSS_SOURCE_INCIDENT | IETF | `netflow:collector`, `netspout:dns:wire` | event | VALIDATED | `pf_SEC-P9-F-CROSS-SOURCE` |
| `rfc5424-link-state-lifecycle` | Modeled Link-State Lifecycle | OPERATIONAL_RESILIENCE | IETF | `netspout:rfc5424` | event | NOT_ESTABLISHED | `pf_rfc5424-link-state-lifecycle` |
| `test-correlated-interface-degradation` | Cisco IOS XR Interface Degradation — Golden Scenario | OPERATIONAL_RESILIENCE | Cisco, IETF, OpenConfig | `netspout:cisco:iosxr:syslog` | event | CERTIFIED | `pf_test-correlated-interface-degradation` |

## Defined but not runnable (224)

- Cataloged candidate: 209
- Contract only in this release: 15

The full list, with objectives, is in [reference/SCENARIO_REFERENCE.md](reference/SCENARIO_REFERENCE.md) (also CSV and JSON in `docs/reference/`).
