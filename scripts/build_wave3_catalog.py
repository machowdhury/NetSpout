#!/usr/bin/env python3
"""Wave-3 catalog graduation: 26 new sourcetype rows, 3 vendor rows,
3 executable scenario rows. Idempotent (skips rows already present)."""
import json
import os
import sys

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CATALOG = os.path.join(REPO_ROOT, "catalog")

WAVE3_ROWS = [
    # splunk_sourcetype, id, display, vendor, category, protocol, data_kind, required_ta
    ("vmw-syslog", "vmw-syslog", "VMware vSphere ESXi Syslog",
     "vmware_nsx", "Enterprise Telemetry", "syslog", "event", None),
    ("cisco:cloud_security:firewall", "cisco-cloud-security-firewall",
     "Cisco Cloud Security Firewall",
     "cisco_asa", "Cisco Security & Telemetry", "syslog", "event",
     "Splunk Add-on for Cisco Cloud Security"),
    ("cisco:cloud_security:dns", "cisco-cloud-security-dns",
     "Cisco Cloud Security DNS",
     "cisco_asa", "Cisco Security & Telemetry", "syslog", "event",
     "Splunk Add-on for Cisco Cloud Security"),
    ("cisco:cloud_security:proxy", "cisco-cloud-security-proxy",
     "Cisco Cloud Security Web Proxy",
     "cisco_asa", "Cisco Security & Telemetry", "syslog", "event",
     "Splunk Add-on for Cisco Cloud Security"),
    ("cisco:isovalent", "cisco-isovalent",
     "Cisco Isovalent Cilium Events",
     "cisco_ios", "Container & Orchestration Telemetry", "hec_event", "event",
     "Cisco OpenVAD Add-on"),
    ("cisco:isovalent:processExec", "cisco-isovalent-processexec",
     "Cisco Isovalent Cilium processExec",
     "cisco_ios", "Container & Orchestration Telemetry", "hec_event", "event",
     "Cisco OpenVAD Add-on"),
    ("cisco:isovalent:processConnect", "cisco-isovalent-processconnect",
     "Cisco Isovalent Cilium processConnect",
     "cisco_ios", "Container & Orchestration Telemetry", "hec_event", "event",
     "Cisco OpenVAD Add-on"),
    ("aws:cloudtrail:lake", "aws-cloudtrail-lake",
     "AWS CloudTrail Lake (OCSF)",
     "amazon_aws", "Cloud Telemetry", "hec_event", "event",
     "Splunk Add-on for AWS"),
    ("linux_secure", "linux-secure", "Linux /var/log/secure",
     "linux_infrastructure", "Endpoint & Host Telemetry", "syslog", "event",
     "Splunk Add-on for Unix and Linux"),
    ("iis", "iis", "Microsoft IIS W3C Access",
     "microsoft_windows", "Endpoint & Host Telemetry", "syslog", "event",
     "Splunk Add-on for Microsoft IIS"),
    ("bro:conn:json", "bro-conn-json", "Zeek (Bro) conn JSON",
     "zeek", "Network Intrusion Detection", "hec_event", "event",
     "Splunk Add-on for Zeek"),
    ("MSExchange:Management", "msexchange-management",
     "MS Exchange Management Audit",
     "microsoft_365", "Enterprise Telemetry", "syslog", "event",
     "Splunk Add-on for Microsoft Exchange"),
    ("aws:cloudfront:accesslogs", "aws-cloudfront-accesslogs",
     "AWS CloudFront Access Logs",
     "amazon_aws", "Cloud Telemetry", "syslog", "event",
     "Splunk Add-on for AWS"),
    ("o365:reporting:messagetrace", "o365-reporting-messagetrace",
     "M365 Reporting Message Trace",
     "microsoft_365", "Identity & SaaS Telemetry", "hec_event", "event",
     "Splunk Add-on for Microsoft Office 365"),
    ("o365:graph:messagetrace", "o365-graph-messagetrace",
     "M365 Graph Message Trace",
     "microsoft_365", "Identity & SaaS Telemetry", "hec_event", "event",
     "Splunk Add-on for Microsoft Office 365"),
    ("gsuite:gmail:bigquery", "gsuite-gmail-bigquery",
     "Gmail BigQuery Message Export",
     "google_workspace", "Identity & SaaS Telemetry", "hec_event", "event",
     "Splunk Add-on for Google Workspace"),
    ("zscalernss-web", "zscaler-nss-web",
     "Zscaler NSS Web Proxy Logs",
     "zscaler_zia", "Zscaler SSE Infrastructure", "hec_event", "event",
     "Zscaler App for Splunk (NSS)"),
    ("cisco:secure_access:security_events_ravpn",
     "cisco-secure-access-security-events-ravpn",
     "Cisco Secure Access RA-VPN Events",
     "cisco_ios", "Cisco Security & Telemetry", "hec_event", "event",
     "Splunk Add-on for Cisco Secure Access"),
    ("cisco:sdwan:syslog", "cisco-sdwan-syslog",
     "Cisco SD-WAN (Viptela) Syslog",
     "cisco_sdwan", "Cisco SD-WAN", "syslog", "event", None),
    ("cisco:sdwan:access", "cisco-sdwan-access",
     "Cisco SD-WAN Management Access",
     "cisco_sdwan", "Cisco SD-WAN", "syslog", "event", None),
    ("cisco:ios", "cisco-ios", "Cisco IOS SEC_LOGIN Syslog",
     "cisco_ios", "Enterprise Telemetry", "syslog", "event", None),
    ("cisco:meraki:syslog", "cisco-meraki-syslog",
     "Cisco Meraki Syslog",
     "cisco_meraki", "Meraki", "syslog", "event", None),
    ("dhcpd", "dhcpd", "ISC dhcpd Lease Events",
     "linux_infrastructure", "Enterprise Telemetry", "syslog", "event", None),
    ("gcp:audit", "gcp-audit", "Google Cloud Audit Logs",
     "google_cloud", "Cloud Telemetry", "hec_event", "event",
     "Splunk Add-on for Google Cloud Platform"),
    ("opentelemetry:otlp", "opentelemetry-otlp",
     "OpenTelemetry OTLP/JSON",
     "opentelemetry", "Enterprise Telemetry", "hec_event", "event", None),
    ("XmlWinEventLog:System", "xmlwineventlog-system",
     "Windows System Channel XML",
     "microsoft_windows", "Endpoint & Host Telemetry", "hec", "event",
     "Splunk Add-on for Microsoft Windows"),
]

WAVE3_VENDORS = [
    {
        "id": "zeek", "legacy_id": "zeek", "name": "Zeek (Bro)",
        "slug": "zeek", "category": "Network Security Monitoring",
        "splunk_app_name": "Splunk Add-on for Zeek",
        "splunkbase_id": "", "splunkbase_url": "",
        "doc_url": "https://docs.zeek.org/en/master/script-reference/proto-analyzers.html",  # noqa
        "supported_device_types": ["firewall"],
        "supported_protocols": ["hec"],
        "header_type": "JSON",
        "delimiter": "",
        "timestamp_format": "ISO 8601",
        "cim_models": ["Network Traffic"],
        "field_mappings": {},
        "sample_events": [],
        "primary_sourcetypes": ["bro:conn:json"],
    },
    {
        "id": "google_cloud", "legacy_id": "google_cloud",
        "name": "Google Cloud", "slug": "google_cloud",
        "category": "Cloud Platform",
        "splunk_app_name": "Splunk Add-on for Google Cloud Platform",
        "splunkbase_id": "", "splunkbase_url": "",
        "doc_url": "https://cloud.google.com/audit-logs/docs",
        "supported_device_types": ["web_server"],
        "supported_protocols": ["hec"],
        "header_type": "JSON",
        "delimiter": "",
        "timestamp_format": "ISO 8601",
        "cim_models": ["Authentication", "Cloud Services"],
        "field_mappings": {},
        "sample_events": [],
        "primary_sourcetypes": ["gcp:audit"],
    },
    {
        "id": "opentelemetry", "legacy_id": "opentelemetry",
        "name": "OpenTelemetry", "slug": "opentelemetry",
        "category": "Observability",
        "splunk_app_name": "OpenTelemetry Collector (OTLP/JSON)",
        "splunkbase_id": "", "splunkbase_url": "",
        "doc_url": "https://opentelemetry.io/docs/specs/otel/logs/",
        "supported_device_types": ["web_server"],
        "supported_protocols": ["hec"],
        "header_type": "JSON",
        "delimiter": "",
        "timestamp_format": "Unix ns",
        "cim_models": ["Performance"],
        "field_mappings": {},
        "sample_events": [],
        "primary_sourcetypes": ["opentelemetry:otlp"],
    },
]

TOPOLOGY_IDS = {
    "wave3_ebpf_workload_hunt": "mixed_sase",
    "wave3_cloudmail_exfil": "mixed_sase",
    "wave3_vsphere_hostpath_triage": "mixed_vendor_enterprise",
}

SCENARIOS = [
    {
        "id": "wave3_ebpf_workload_hunt", "code": "SEC-EBPF-03",
        "name": "eBPF Workload Hunt (Wave-3 pack)",
        "display_name": "eBPF Workload Hunt (Wave-3 pack)",
        "category": "SECURITY", "ecosystem": "mixed_vendor",
        "maturity": "CONTRACTED",
        "description": ("Kubernetes workload compromise chain: Cilium "
                        "Tetragon process exec/connect, Cisco Cloud "
                        "Security DNS/proxy/cloud-firewall rows and Zeek "
                        "conn records - delivered as authentic vendor-native"
                        " RAW with correlation on HEC fields only."),
        "attack_vector": "T1059 command and scripting interpreter, "
                         "T1048 exfiltration over ICMP, T1552 metadata "
                         "service discovery.",
        "defense_mechanism": "eBPF syscall visibility, cloud DNS/proxy "
                             "risk verdicts, Zeek conn telemetry.",
        "generation_mode": "SCENARIO_DERIVED",
        "sourcetypes": [
            "cisco:isovalent", "cisco:isovalent:processExec",
            "cisco:isovalent:processConnect",
            "cisco:cloud_security:dns", "cisco:cloud_security:proxy",
            "cisco:cloud_security:firewall", "bro:conn:json",
        ],
        "default_topology_id": TOPOLOGY_IDS["wave3_ebpf_workload_hunt"],
        "topology_id": TOPOLOGY_IDS["wave3_ebpf_workload_hunt"],
        "difficulty": "ADVANCED", "estimated_duration_sec": 45,
        "vendor_scope": ["cisco_ios", "cisco_asa", "zeek"],
        "telemetry_requirements": ["hec_event"],
        "generation_modes": ["SCENARIO_DERIVED"],
        "affected_entities": [TOPOLOGY_IDS["wave3_ebpf_workload_hunt"]],
        "expected_observations": [
            "Tetragon process_exec curl anomalies",
            "Metadata service process_connect (IMDS prober)",
            "Cloud Security proxy 404 gobuster recon burst",
            "ICMP S2C tunnel attempt (large_icmp layout)",
            "Zeek conn S1/rdp external record",
        ],
        "expected_phases": ["baseline", "degrade", "fault", "propagate",
                            "validate"],
        "use_case": {
            "objective": "eBPF-native workload hunt across container, cloud "
                         "edge and NSM raw sources",
            "required_telemetry": ["cisco:isovalent",
                                   "cisco:cloud_security:firewall"],
        },
        "phases": [
            {"phase": "BASELINE", "name": "Nominal pod work",
             "duration_ticks": 2,
             "description": "Curl health fetch plus internal SSH Zeek conn "
                            "flow.",
             "expected_observations": ["cisco:isovalent process_exec normal",
                                       "bro:conn:json ssh SF"]},
            {"phase": "DEGRADE", "name": "DNS recon",
             "duration_ticks": 1,
             "description": "Anonymizer-category DNS query for pastebin-pool "
                            "domain.",
             "expected_observations": ["cloud dns Proxy/Anonymizer verdict"]},
            {"phase": "FAULT", "name": "Exec + web recon",
             "duration_ticks": 2,
             "description": "curl to attacker pool plus gobuster proxy 404 "
                            "scan.",
             "expected_observations": ["process_exec curl attacker",
                                       "proxy 404 burst"]},
            {"phase": "PROPAGATE", "name": "Metadata + RDP escape",
             "duration_ticks": 2,
             "description": "IMDS connect event and RDP conn record.",
             "expected_observations": ["process_connect 169.254.169.254",
                                       "zeek rdp S1"]},
            {"phase": "VALIDATE", "name": "ICMP tunnel close",
             "duration_ticks": 1,
             "description": "Cloud firewall captures S2C ICMP tunnel row.",
             "expected_observations": ["csl icmp event capture"]},
        ],
        "validation_rules": {
            "raw_is_vendor_native": True,
            "correlation_fields_hek_only": True,
            "phases_min": 5,
        },
        "telemetry_model": "Standard Telemetry Payload",
        "transport_protocol": "Splunk HEC",
        "splunk_storage": "Splunk Event Index (idx_network_ops)",
        "fidelity_badge": "MODELED PAYLOAD",
    },
    {
        "id": "wave3_cloudmail_exfil", "code": "SEC-CMAIL-03",
        "name": "Cloud Mail Exfiltration Chain (Wave-3 pack)",
        "display_name": "Cloud Mail Exfiltration Chain (Wave-3 pack)",
        "category": "SECURITY", "ecosystem": "mixed_vendor",
        "maturity": "CONTRACTED",
        "description": ("SaaS identity + mail exfiltration chain: Duo admin "
                        "activity, M365 reporting/Graph message traces, Gmail"
                        " BigQuery export, Zscaler NSS web rows and CloudFront"
                        " edge pull - authentic vendor-native RAW."),
        "attack_vector": "T1567 exfiltration to cloud storage, T1562 "
                         "impair defenses, T1078 valid accounts.",
        "defense_mechanism": "Duo admin audit, mail trace policy hits, SASE "
                             "proxy block verdicts.",
        "generation_mode": "SCENARIO_DERIVED",
        "sourcetypes": [
            "cisco:duo:administrator", "o365:reporting:messagetrace",
            "o365:graph:messagetrace", "gsuite:gmail:bigquery",
            "zscalernss-web", "aws:cloudfront:accesslogs",
        ],
        "default_topology_id": TOPOLOGY_IDS["wave3_cloudmail_exfil"],
        "topology_id": TOPOLOGY_IDS["wave3_cloudmail_exfil"],
        "difficulty": "ADVANCED", "estimated_duration_sec": 40,
        "vendor_scope": ["cisco_duo", "microsoft_365", "google_workspace",
                         "zscaler_zia", "amazon_aws"],
        "telemetry_requirements": ["hec_event"],
        "generation_modes": ["SCENARIO_DERIVED"],
        "affected_entities": [TOPOLOGY_IDS["wave3_cloudmail_exfil"]],
        "expected_observations": [
            "Duo admin policy_download from anomalous device",
            "Mail traces to vault-drop external recipient",
            "Gmail BigQuery export to external domain",
            "Zscaler block verdict on payload drop",
            "CloudFront edge pull from open staging bucket",
        ],
        "expected_phases": ["baseline", "degrade", "fault", "complete"],
        "use_case": {
            "objective": "Multi-SaaS mail and storage exfil chain with "
                         "identity audit trail",
            "required_telemetry": ["o365:reporting:messagetrace",
                                   "cisco:duo:administrator"],
        },
        "phases": [
            {"phase": "BASELINE", "name": "Nominal SaaS posture",
             "duration_ticks": 2,
             "description": "Duo admin login plus normal M365 mail trace.",
             "expected_observations": ["duo admin_login normal",
                                       "messagetrace Delivered"]},
            {"phase": "DEGRADE", "name": "Account recon",
             "duration_ticks": 1,
             "description": "Proxy allow to paste service plus Duo policy "
                            "download.",
             "expected_observations": ["zscaler allow anomaly",
                                       "duo policy_download"]},
            {"phase": "FAULT", "name": "Mail exfil burst",
             "duration_ticks": 2,
             "description": "Gmail + Graph traces to external vault drop and "
                            "CloudFront pull.",
             "expected_observations": ["gmail external export",
                                       "graph trace external recipient",
                                       "cloudfront staging pull"]},
            {"phase": "COMPLETE", "name": "Block + account response",
             "duration_ticks": 1,
             "description": "Zscaler block verdict plus Duo admin action "
                            "query.",
             "expected_observations": ["zscaler Blocked",
                                       "duo policy_bulk_delete"]},
        ],
        "validation_rules": {
            "raw_is_vendor_native": True,
            "correlation_fields_hek_only": True,
            "phases_min": 4,
        },
        "telemetry_model": "Standard Telemetry Payload",
        "transport_protocol": "Splunk HEC",
        "splunk_storage": "Splunk Event Index (idx_network_ops)",
        "fidelity_badge": "MODELED PAYLOAD",
    },
    {
        "id": "wave3_vsphere_hostpath_triage", "code": "OPS-VSPH-03",
        "name": "vSphere Host Path Triage (Wave-3 pack)",
        "display_name": "vSphere Host Path Triage (Wave-3 pack)",
        "category": "OPERATIONS", "ecosystem": "mixed_vendor",
        "maturity": "CONTRACTED",
        "description": ("Hypervisor/identity triage sequence: Windows System "
                        "channel XML, Viptela SD-WAN control+access, ISC "
                        "dhcpd leases, ESXi shell reads, /var/log/secure su "
                        "chain and IOS SEC_LOGIN failures - authentic "
                        "vendor-native RAW."),
        "attack_vector": "T1083 host file discovery, T1003 credential "
                         "dumping, T1078 STIG drift identity probing.",
        "defense_mechanism": "ESXi shell auditing, log/secure PAM monitoring,"
                             " SD-WAN management access logging.",
        "generation_mode": "SCENARIO_DERIVED",
        "sourcetypes": [
            "XmlWinEventLog:System", "cisco:sdwan:syslog", "dhcpd",
            "iis", "vmw-syslog", "linux_secure", "cisco:sdwan:access",
            "cisco:ios", "cisco:meraki:syslog",
        ],
        "default_topology_id": TOPOLOGY_IDS["wave3_vsphere_hostpath_triage"],
        "topology_id": TOPOLOGY_IDS["wave3_vsphere_hostpath_triage"],
        "difficulty": "INTERMEDIATE", "estimated_duration_sec": 40,
        "vendor_scope": ["microsoft_windows", "cisco_sdwan", "vmware_nsx",
                         "linux_infrastructure", "cisco_ios", "cisco_meraki"],
        "telemetry_requirements": ["syslog"],
        "generation_modes": ["SCENARIO_DERIVED"],
        "affected_entities": [TOPOLOGY_IDS["wave3_vsphere_hostpath_triage"]],
        "expected_observations": [
            "Windows System 6005 service start",
            "VDAEMON control-connection up",
            "ESXi shell cat /etc/shadow read",
            "su session chain on /var/log/secure",
            "SD-WAN envoy access probe + IOS SEC_LOGIN failure",
        ],
        "expected_phases": ["baseline", "fault", "propagate", "validate"],
        "use_case": {
            "objective": "Hypervisor and identity plane triage across "
                         "Windows/Linux/viptela raw surfaces",
            "required_telemetry": ["vmw-syslog", "linux_secure"],
        },
        "phases": [
            {"phase": "BASELINE", "name": "Nominal infra boot",
             "duration_ticks": 3,
             "description": "System event log start, control-connection up, "
                            "dhcp lease ack and IIS access.",
             "expected_observations": ["6005 start", "dhcpack lease",
                                       "vdaemon up"]},
            {"phase": "FAULT", "name": "Host path reads",
             "duration_ticks": 2,
             "description": "ESXi root shell reads plus su session chain.",
             "expected_observations": ["shell cat /etc/shadow",
                                       "su opened session"]},
            {"phase": "PROPAGATE", "name": "SD-WAN mgmt spread",
             "duration_ticks": 2,
             "description": "Envoy management probe plus IOS bad-password "
                            "failure.",
             "expected_observations": ["sdwan access probe",
                                       "SEC_LOGIN-4 failure"]},
            {"phase": "VALIDATE", "name": "Edge capture confirm",
             "duration_ticks": 1,
             "description": "Hostd benign download completed plus Meraki url"
                            " edge record.",
             "expected_observations": ["hostd event completed",
                                       "meraki urls capture"]},
        ],
        "validation_rules": {
            "raw_is_vendor_native": True,
            "correlation_fields_hek_only": True,
            "phases_min": 4,
        },
        "telemetry_model": "Standard Telemetry Payload",
        "transport_protocol": "Splunk HEC",
        "splunk_storage": "Splunk Event Index (idx_network_ops)",
        "fidelity_badge": "MODELED PAYLOAD",
    },
]


def slug_id(splunk_sourcetype: str) -> str:
    return splunk_sourcetype.replace(":", "-").lower()


def build_row(row) -> dict:
    (st_name, custom_id, display, vendor, category, protocol, kind,
     required_ta) = row
    return {
        "id": custom_id,
        "splunk_sourcetype": st_name,
        "display_name": display,
        "vendor_id": vendor,
        "category": category,
        "data_kind": kind,
        "default_index": "idx_network_ops",
        "recommended_index": "netops_logs",
        "generation_mode": "STATEFUL",
        "protocol": protocol,
        "sample_file": None,
        "required_ta": required_ta,
        "aliases": [custom_id, st_name],
        "deprecated_aliases": [],
        "is_benchmark_197": False,
        "status": "active",
    }


def main() -> None:
    with open(os.path.join(CATALOG, "sourcetypes.json")) as f:
        st_rows = json.load(f)
    existing = {r["splunk_sourcetype"] for r in st_rows}
    added = []
    for row in WAVE3_ROWS:
        if row[0] in existing:
            continue
        st_rows.append(build_row(row))
        added.append(row[0])
    with open(os.path.join(CATALOG, "sourcetypes.json"), "w") as f:
        json.dump(st_rows, f, indent=1)

    with open(os.path.join(CATALOG, "vendors.json")) as f:
        vendors = json.load(f)
    v_ids = {v["id"] for v in vendors}
    vend_added = []
    for v in WAVE3_VENDORS:
        if v["id"] in v_ids:
            continue
        vendors.append(v)
        vend_added.append(v["id"])
    with open(os.path.join(CATALOG, "vendors.json"), "w") as f:
        json.dump(vendors, f, indent=1)

    with open(os.path.join(CATALOG, "scenarios.json")) as f:
        scenarios = json.load(f)
    s_ids = {s["id"] for s in scenarios}
    scn_added = []
    for s in SCENARIOS:
        if s["id"] in s_ids:
            continue
        scenarios.append(s)
        scn_added.append(s["id"])
    with open(os.path.join(CATALOG, "scenarios.json"), "w") as f:
        json.dump(scenarios, f, indent=1)

    print("wave3 sourcetype rows added:", len(added))
    print("vendor rows added:", vend_added)
    print("scenario rows added:", scn_added)


if __name__ == "__main__":
    main()
