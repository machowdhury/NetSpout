#!/usr/bin/env python3
"""Append industry scenario packs to catalog/replay_packs.json (idempotent: entries with ids starting `ind_` are regenerated).

Every pack is a SEQUENCE OF EXISTING authentic native packs (each already a correlated, vendor-format incident) and, where useful, replay recordings,
run by the existing replay-pack engine. Nothing is invented: no vendor message, identifier, event id or cross-source relation is authored here.
Honest framing: telemetry and the in-pack correlation are authentic; the INDUSTRY framing and the ordering of packs into one story are editorial, and the
relation BETWEEN constituent packs is temporal only (pack offsets). Maturity stays CONTRACTED; verification is delivery/indexing and panel-query evidence only.
Run: PYTHONPATH=src python scripts/build_industry_scenarios.py   then scripts/sync_core.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from netspout_core.authentic_scenario_packs import run_scenario_pack  # noqa: E402

PANELS = [
    ("Event volume by sourcetype", 'index=dev_test_replay netspout_replay_session="{session}" | timechart span=10s count by sourcetype'),
    ("Events by incident phase", 'index=dev_test_replay netspout_replay_session="{session}" | stats count by netspout_phase, netspout_pack_phase | sort netspout_phase'),
    ("Top reporting hosts", 'index=dev_test_replay netspout_replay_session="{session}" | stats count by host sourcetype | sort - count | head 10'),
]
SEC_PREREQ = ("No vendor add-on, CIM or Enterprise Security content is installed in any lab, so no detection is claimed. Detection work needs the add-ons for the constituent "
              "sourcetypes plus reviewed SPL; the constituent native packs' contracts list their own expectations.")
OPS_DASH = ("Panels (validated only as populated queries against the replayed run, in the isolated lab): " + "; ".join(t for t, _ in PANELS) +
            ". No Dashboard Studio object is built or claimed for these packs.")

# id, industry, subindustry, kind (OPERATIONAL|SECURITY), category, title, objective, outcome, [native packs in order]
S = [
 ("ind_bank_account_takeover_resilience", "banking-financial-services", "Retail banking", "SECURITY", "SOC", "Retail banking: workstation credential compromise, cloud SSO abuse, backup integrity check",
  "Follow an analyst-workstation credential compromise into cloud single-sign-on abuse, then confirm the backup and database estate is intact (ransomware resilience).",
  "Windows credential-attack chain, cloud identity stuffing/escalation, then Veeam and MongoDB integrity observations in one run.",
  ["wave2_ws_credential_compromise_chain", "wave2_cloud_identity_sso_hunt", "ub2_database_backup_integrity"]),
 ("ind_bank_payments_edge_defense", "banking-financial-services", "Payments and e-banking", "SECURITY", "SOC", "Payments edge: WAF/IDS/firewall observation then cloud control-plane reconnaissance",
  "Observe attacks against the internet-facing payment edge (WAF, IDS, firewall) and the follow-on reconnaissance of the cloud account hosting it.",
  "Barracuda WAF, Darktrace, Imperva and pfSense observations, then an AWS recon-to-escalation sequence.",
  ["ub3_multivendor_edge_observation", "wave2_aws_recon_escalation"]),
 ("ind_telco_change_induced_outage", "telecommunications", "Enterprise WAN and SD-WAN services", "OPERATIONAL", "NOC", "Telecom NOC: change-induced SD-WAN outage, then edge threat pipeline",
  "Reconstruct a change that triggers a BGP/CDP/DMI fault with recovery, then check the UTD threat pipeline on the same edge estate.",
  "Cisco SD-WAN/IOS-XE change, fault and recovery messages followed by UTD, SSE tunnel and health records.",
  ["ub5_cisco_change_induced_outage", "ub6_sdwan_utd_threat_pipeline"]),
 ("ind_telco_access_and_wireless_health", "telecommunications", "Access, wireless and subscriber edge", "OPERATIONAL", "NOC", "Telecom NOC: RADIUS/NAC outage, platform degradation and rogue wireless threat",
  "Correlate an authentication-server outage and platform health degradation with a wireless rogue-device threat on the access layer.",
  "AAA/RADIUS outage and recovery, platform degradation, then Catalyst rogue and threat records.",
  ["ub5_cisco_nac_radius_outage", "ub5_cisco_platform_health_degradation", "ub6_catalyst_wireless_rogue_threat"]),
 ("ind_health_ehr_ransomware_readiness", "healthcare", "Hospital systems and EHR", "SECURITY", "SOC", "Hospital: endpoint credential attack with backup and privileged-access audit",
  "Show a credential attack on a clinical workstation next to the backup integrity and privileged-access evidence an investigator needs.",
  "Windows credential chain, Veeam/MongoDB observations, identity and privileged-session audit records.",
  ["wave2_ws_credential_compromise_chain", "ub2_database_backup_integrity", "ub3_identity_runtime_audit"]),
 ("ind_health_clinical_network_edge", "healthcare", "Clinical network and medical IoT edge", "OPERATIONAL", "NOC", "Hospital network: edge and DNS/proxy health with wireless threat",
  "Watch clinical network edge health (DNS, proxy, firewall, flow) while a wireless rogue-device event is raised.",
  "Cisco Secure Access DNS/proxy/firewall, Zeek, Isovalent flow, then Catalyst rogue records.",
  ["wave3_ebpf_workload_hunt", "ub6_catalyst_wireless_rogue_threat"]),
 ("ind_mfg_it_ot_convergence", "manufacturing", "Discrete manufacturing plant", "SECURITY", "SOC", "Plant: OT proxy and edge routing observation, then command-and-control callback",
  "Observe the plant OT proxy and edge-routing estate, then a C2 callback and discovery from a host on the IT side.",
  "Nozomi/Wazuh/Docker/BlueCoat OT records, Claroty/MikroTik/NGINX/Traefik edge records, then osquery and Suricata callback evidence.",
  ["ub1_ot_proxy_host_hunt", "ub2_ot_edge_routing_observation", "wave2_c2_callback_detection"]),
 ("ind_mfg_plant_network_health", "manufacturing", "Plant network operations", "OPERATIONAL", "NOC", "Plant network: platform degradation and change-induced outage",
  "Track platform health degradation and a configuration change that causes an outage and recovery on the plant network.",
  "Cisco platform health, then change, fault and recovery messages.",
  ["ub5_cisco_platform_health_degradation", "ub5_cisco_change_induced_outage"]),
 ("ind_energy_substation_edge_observation", "energy-utilities", "Electric transmission and substations", "OPERATIONAL", "NOC", "Substation edge: OT routing observation and network platform health",
  "Observe the substation OT edge (Claroty, MikroTik, reverse proxies) and the health of the supporting Cisco network platform.",
  "OT edge records followed by a platform degradation and recovery sequence.",
  ["ub2_ot_edge_routing_observation", "ub5_cisco_platform_health_degradation"]),
 ("ind_energy_scada_proxy_intrusion", "energy-utilities", "Utility control systems", "SECURITY", "SOC", "Utility: OT proxy host hunt and C2 callback detection",
  "Hunt a compromised proxy/host in the control-system DMZ and the callback and discovery it produces.",
  "OT proxy, Wazuh, Docker and Nozomi records, then osquery and Suricata callback evidence.",
  ["ub1_ot_proxy_host_hunt", "wave2_c2_callback_detection"]),
 ("ind_insurance_claims_platform_audit", "insurance-insurtech", "Claims and policy administration", "SECURITY", "SOC", "Claims platform: SaaS and database/message audit with cloud mail exfiltration",
  "Review collaboration-platform audit, Oracle and IBM MQ audit of the claims system, and a cloud-mail exfiltration attempt.",
  "GitHub/GitLab/Slack audit, Oracle and IBM MQ audit, then the cloud-mail exfiltration sequence.",
  ["ub4_saas_collaboration_audit", "ub3_database_message_audit", "wave3_cloudmail_exfil"]),
 ("ind_insurance_underwriting_exposure", "insurance-insurtech", "Underwriting analytics and data platforms", "OPERATIONAL", "ITOPS", "Underwriting data platform: exposure management, vault and identity audit",
  "Combine vulnerability/exposure management, secrets and mail-security audit, and identity runtime audit for the underwriting data platform.",
  "Qualys/Rapid7/Elastic/QRadar records, Confluence/Vault/Proofpoint records, SailPoint/Tenable/Sysdig/BeyondTrust records.",
  ["ub4_exposure_infra_logging", "ub2_cloud_identity_mail_hunt", "ub3_identity_runtime_audit"]),
 ("ind_gov_citizen_identity_attack", "government-public-sector", "State and local government", "SECURITY", "SOC", "Citizen services: cloud identity attack, AWS reconnaissance, privileged-access audit",
  "Trace identity stuffing against citizen-facing cloud services, reconnaissance of the hosting account, and the privileged-access audit trail.",
  "Okta/Azure/Google/O365 identity events, AWS recon and escalation, identity audit records.",
  ["wave2_cloud_identity_sso_hunt", "wave2_aws_recon_escalation", "ub3_identity_runtime_audit"]),
 ("ind_gov_agency_mail_exfiltration", "government-public-sector", "Federal civilian and compliance (framing only)", "SECURITY", "SOC", "Agency: cloud mail exfiltration with containment and endpoint pipeline",
  "Follow a cloud-mail exfiltration attempt through containment and the endpoint-protection pipeline.",
  "CloudFront/CloudTrail Lake/Duo/Secure Access/Gmail records then endpoint-protection records.",
  ["wave3_cloudmail_exfil", "ub4_endpoint_threat_pipeline"]),
 ("ind_retail_pos_edge_defense", "retail-ecommerce", "Stores and point of sale", "SECURITY", "SOC", "Retail stores: edge defense observation and endpoint threat pipeline",
  "Observe the store/e-commerce edge (WAF, IDS, firewall) and the endpoint-protection pipeline covering store systems.",
  "Edge security records followed by Bitdefender/Cybereason/SentinelOne/Tanium/Trellix records.",
  ["ub3_multivendor_edge_observation", "ub4_endpoint_threat_pipeline"]),
 ("ind_retail_ecommerce_cloud_recon", "retail-ecommerce", "E-commerce platform", "SECURITY", "SOC", "E-commerce: AWS reconnaissance and escalation with exposure management",
  "Follow cloud reconnaissance and privilege escalation against the e-commerce account, then the exposure-management evidence for the same estate.",
  "AWS recon and escalation, then Qualys/Rapid7/Elastic/QRadar records.",
  ["wave2_aws_recon_escalation", "ub4_exposure_infra_logging"]),
 ("ind_edu_campus_identity_and_collab", "education", "Higher education", "SECURITY", "SOC", "Campus: cloud identity attack and collaboration-platform audit",
  "Show credential stuffing against campus single sign-on and the source-control/collaboration audit trail.",
  "Cloud identity events, then GitHub/GitLab/Slack audit records.",
  ["wave2_cloud_identity_sso_hunt", "ub4_saas_collaboration_audit"]),
 ("ind_saas_platform_runtime_attack", "technology-saas", "Cloud-native software platform", "SECURITY", "SOC", "SaaS platform: Kubernetes container escape, collaboration audit and exposure management",
  "Trace a container escape in the platform cluster alongside collaboration audit and exposure-management evidence.",
  "Kubernetes audit, Falco, osquery and Suricata records, collaboration audit, exposure records.",
  ["wave2_k8s_container_escape", "ub4_saas_collaboration_audit", "ub4_exposure_infra_logging"]),
 ("ind_media_content_delivery_exfil", "media-entertainment", "Streaming and content delivery", "SECURITY", "SOC", "Media: content-delivery access with cloud-mail exfiltration",
  "Observe CDN access logs and a cloud-mail exfiltration of pre-release content, with containment.",
  "CloudFront access, CloudTrail Lake, Duo, Secure Access and Gmail records.",
  ["wave3_cloudmail_exfil"]),
 ("ind_hospitality_guest_network_defense", "hospitality-travel", "Hotels and guest networks", "SECURITY", "SOC", "Hospitality: edge defense and guest/staff identity attack",
  "Observe guest-network edge defenses and credential stuffing against staff cloud identities.",
  "Edge security records, then cloud identity events.",
  ["ub3_multivendor_edge_observation", "wave2_cloud_identity_sso_hunt"]),
 ("ind_aero_defense_endpoint_c2", "aerospace-defense", "Defense contractor", "SECURITY", "SOC", "Defense contractor: C2 callback, endpoint pipeline and privileged-access audit",
  "Detect a callback and discovery from a contractor host, the endpoint-protection response and the privileged-access audit trail.",
  "osquery and Suricata callback evidence, endpoint-protection records, identity audit records.",
  ["wave2_c2_callback_detection", "ub4_endpoint_threat_pipeline", "ub3_identity_runtime_audit"]),
 ("ind_legal_matter_data_exfiltration", "legal-compliance-professional-services", "Law firms and professional services", "SECURITY", "SOC", "Law firm: client-matter data exfiltration across mail, vault and wiki",
  "Follow client-matter data leaving through cloud mail and the secrets, wiki and mail-security audit evidence around it.",
  "Cloud-mail exfiltration sequence, then Confluence/Vault/Proofpoint records.",
  ["wave3_cloudmail_exfil", "ub2_cloud_identity_mail_hunt"]),
 ("ind_agri_edge_gateway_health", "agriculture-agritech", "Precision farming and processing", "OPERATIONAL", "ITOPS", "Agritech: edge gateway routing observation and Linux gateway authentication anomaly",
  "Observe field/processing edge routing gear and an authentication anomaly on a Linux edge gateway.",
  "Claroty/MikroTik/NGINX/Traefik edge records, then Linux auditd/syslog/Sysmon records.",
  ["ub2_ot_edge_routing_observation", "wave2_linux_auth_anomaly"]),
 ("ind_realestate_building_exposure", "real-estate-proptech-construction", "Commercial property and construction", "OPERATIONAL", "ITOPS", "Property technology: exposure management and collaboration audit",
  "Track exposure-management findings for property systems and the collaboration/source-control audit trail of the platform team.",
  "Qualys/Rapid7/Elastic/QRadar records, then GitHub/GitLab/Slack audit records.",
  ["ub4_exposure_infra_logging", "ub4_saas_collaboration_audit"]),
 ("ind_nonprofit_donor_platform_attack", "nonprofit-ngo-global-aid", "Humanitarian and donor platforms", "SECURITY", "SOC", "Non-profit: staff identity attack and cloud-mail exfiltration of donor data",
  "Show credential stuffing against staff identities and a cloud-mail exfiltration of donor records.",
  "Cloud identity events, then the cloud-mail exfiltration sequence.",
  ["wave2_cloud_identity_sso_hunt", "wave3_cloudmail_exfil"]),
 ("ind_transport_fleet_network_change", "transportation-logistics", "Logistics and fleet networks", "OPERATIONAL", "NOC", "Logistics network: change-induced outage and edge routing observation",
  "Reconstruct a change that causes an outage on the logistics WAN, then observe edge routing and proxy services after recovery.",
  "Cisco change/fault/recovery messages, then edge routing records.",
  ["ub5_cisco_change_induced_outage", "ub2_ot_edge_routing_observation"]),
]
GAP_S, SPACING_S = 5.0, 1.0


def build():
    packs, seen = [], set()
    for n, (pid, ind, sub, kind, cat, title, obj, outcome, natives) in enumerate(S):
        assert pid not in seen
        seen.add(pid)
        offset, phases, sts = 0.0, [], set()
        for pack in natives:
            events = run_scenario_pack(pack, pid + "-probe")
            sts |= {e.sourcetype for e in events}
            phases.append({"id": pack.upper(), "offset_s": offset, "source": {"kind": "native", "pack": pack, "spacing_s": SPACING_S}})
            offset += len(events) * SPACING_S + GAP_S
        packs.append({"id": pid, "title": title, "category": cat, "kind": kind.lower(), "seed": 2000 + n, "industries": [ind], "subindustry": sub,
                      "objective": obj, "expected_outcome": outcome, "phases": phases, "required_sourcetypes": sorted(sts),
                      "execution_requirement": "native",
                      "correlation_note": "Correlated inside each constituent native pack; constituent packs are related by time only.",
                      "detection_prerequisites": SEC_PREREQ if kind == "SECURITY" else "Operational scenario: no detection claimed.",
                      "dashboard_requirement": OPS_DASH if kind == "OPERATIONAL" else "Security scenario: no dashboard required; panel queries are still available for the run.",
                      "dashboard_panels": [{"title": t, "spl": q} for t, q in PANELS],
                      "provenance": "Constituent native packs: " + ", ".join(natives) + " (authentic vendor-format telemetry from the vendored attack_data/universe samples; see each pack's contract). Industry framing is editorial.",
                      "verification_spl": 'index=dev_test_replay netspout_scenario_id="%s" | stats count by netspout_phase, netspout_pack_phase, sourcetype' % pid})
    return packs


def main():
    path = ROOT / "catalog" / "replay_packs.json"
    doc = json.loads(path.read_text())
    doc["packs"] = [p for p in doc["packs"] if not p["id"].startswith("ind_")] + build()
    path.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"industry_packs": len(S), "industries": sorted({s[1] for s in S}).__len__(), "total_packs": len(doc["packs"])}))


if __name__ == "__main__":
    main()
