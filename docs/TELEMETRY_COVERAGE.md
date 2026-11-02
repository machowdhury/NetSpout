# Telemetry coverage

Generated from `catalog/sourcetypes.json` and the coverage evidence by `scripts/generate_customer_docs.py`; do not edit by hand. Each column is separate evidence. **Catalog presence is not proof that a sourcetype works.**

| Level | Meaning | Sourcetypes |
|---|---|---|
| Cataloged | Listed in the catalog | 349 |
| Generated | A native generator produces events (`G`) | 159 |
| Sample replay | Replays a bundled sample, not a native generator (`R`) | 143 |
| Streamable | Can be sent as a bounded run through HEC (generated or sample replay) | 302 |
| Byte-verified | Raw event equal to what was sent, checked in an isolated Splunk | 129 |
| Independently indexed | Found by a separate Splunk search in an isolated lab | 137 |
| Add-on parsing checked | Parsed by the installed add-on in a lab | 6 |
| CIM validated | No CIM data model was installed in any lab | 0 |
| Dashboard-validated | Referenced by a scenario with a data-validated dashboard | 152 |

Everything else is **not tested**. Detection content (Enterprise Security, correlation searches) is not claimed.

## Transports

| Transport | Status in this release |
|---|---|
| HEC (events and metrics) | Supported; verified end to end, including independent indexing, on Splunk Enterprise 10.6.1.1 and in a Docker lab |
| Syslog (UDP/TCP) | Supported by the generator for Enterprise and Docker; not available for restricted Splunk Cloud |
| SNMP | Traps and metric-style records for the sourcetypes marked `snmp`; limited coverage |
| NetFlow / IPFIX | Normalized flow events over HEC (verified); IPFIX wire export is a separate, separately reported stage |
| OpenTelemetry | OTLP collector is part of the Docker deployment; see [guides/06_NETWORK_TELEMETRY_GUIDE.md](guides/06_NETWORK_TELEMETRY_GUIDE.md) |
| gNMI / native streaming | Generators exist; **not validated** on the Enterprise single package (a native library is missing on the tested host) |

## By vendor

| Vendor | Sourcetypes | Generated | Sample replay | Indexed-verified | Protocols |
|---|---|---|---|---|---|
| A10 Networks | 2 | 0 | 0 | 0 | syslog |
| Amazon Web Services | 4 | 4 | 0 | 4 | hec_event, syslog |
| Arista Networks | 4 | 1 | 3 | 0 | syslog |
| Aruba / HPE | 6 | 0 | 4 | 0 | syslog |
| Atlassian | 1 | 1 | 0 | 1 | hec |
| Barracuda Networks | 1 | 1 | 0 | 1 | hec |
| BeyondTrust | 1 | 1 | 0 | 1 | hec |
| Bitdefender | 1 | 1 | 0 | 1 | hec |
| Check Point Software | 3 | 0 | 1 | 0 | syslog |
| Cisco Duo | 10 | 2 | 6 | 1 | syslog |
| Cisco Meraki | 17 | 2 | 12 | 1 | syslog |
| Cisco Systems | 133 | 67 | 58 | 57 | hec, hec_event, snmp, syslog |
| Citrix / Cloud Software Group | 2 | 0 | 0 | 0 | syslog |
| Claroty | 1 | 1 | 0 | 1 | hec |
| Cloudflare | 3 | 0 | 2 | 0 | syslog |
| CrowdStrike | 1 | 1 | 0 | 1 | hec_event |
| CrushFTP | 1 | 1 | 0 | 1 | syslog_rfc3164 |
| Cybereason | 1 | 1 | 0 | 1 | hec |
| Darktrace | 1 | 1 | 0 | 1 | hec |
| Dell Technologies | 1 | 0 | 0 | 0 | syslog |
| Docker | 1 | 1 | 0 | 1 | hec |
| Elastic | 1 | 1 | 0 | 1 | hec |
| ExtraHop Networks | 2 | 0 | 2 | 0 | hec, syslog |
| Extreme Networks | 2 | 0 | 0 | 0 | syslog |
| F5 Networks | 2 | 1 | 1 | 0 | syslog |
| Forcepoint | 2 | 0 | 0 | 0 | syslog |
| Fortinet | 8 | 1 | 5 | 0 | syslog |
| GitHub | 1 | 1 | 0 | 1 | hec |
| GitLab | 1 | 1 | 0 | 1 | hec |
| Google Cloud | 1 | 1 | 0 | 1 | hec_event |
| Google Workspace | 2 | 2 | 0 | 2 | hec_event |
| HashiCorp | 1 | 1 | 0 | 1 | hec |
| Huawei Technologies | 2 | 0 | 0 | 0 | syslog |
| IBM | 1 | 1 | 0 | 1 | hec |
| IBM MQ | 1 | 1 | 0 | 1 | hec |
| Imperva | 1 | 1 | 0 | 1 | hec |
| Juniper Networks | 3 | 1 | 2 | 0 | syslog |
| Kubernetes & Falco (CNCF) | 2 | 2 | 0 | 2 | hec_event |
| Linux Infrastructure | 4 | 4 | 0 | 4 | syslog, syslog_rfc3164 |
| Microsoft 365 | 4 | 4 | 0 | 4 | hec_event, syslog |
| Microsoft Azure Monitor | 2 | 2 | 0 | 2 | hec_event |
| Microsoft Windows | 8 | 8 | 0 | 8 | hec, hec_event, syslog |
| MikroTik | 1 | 1 | 0 | 1 | hec |
| Model Context Protocol (agentic AI) | 1 | 1 | 0 | 1 | hec_event |
| MongoDB | 1 | 1 | 0 | 1 | hec |
| NetScout Systems | 1 | 0 | 1 | 0 | syslog |
| Netskope | 4 | 0 | 2 | 0 | syslog |
| NGINX (F5) | 2 | 2 | 0 | 2 | hec |
| Nokia | 3 | 1 | 1 | 0 | syslog |
| Nozomi Networks | 1 | 1 | 0 | 1 | syslog |
| Nutanix | 16 | 0 | 16 | 0 | hec, syslog |
| Okta | 1 | 1 | 0 | 1 | hec_event |
| Ollama (local LLM runtime) | 1 | 1 | 0 | 1 | hec_event |
| OpenTelemetry | 1 | 1 | 0 | 1 | hec_event |
| Oracle | 1 | 1 | 0 | 1 | hec |
| osquery | 1 | 1 | 0 | 1 | hec_event |
| Palo Alto Networks | 5 | 3 | 0 | 3 | syslog |
| pfSense (Netgate) | 1 | 1 | 0 | 1 | hec |
| Proofpoint | 1 | 1 | 0 | 1 | hec |
| Qualys | 1 | 1 | 0 | 1 | hec |
| Radware | 4 | 0 | 2 | 0 | syslog |
| Rapid7 | 1 | 1 | 0 | 1 | hec |
| SailPoint | 1 | 1 | 0 | 1 | hec |
| SentinelOne | 1 | 1 | 0 | 1 | hec |
| Slack | 1 | 1 | 0 | 1 | hec |
| SonicWall | 1 | 0 | 0 | 0 | syslog |
| Sophos | 2 | 0 | 1 | 0 | syslog |
| Splunk / Native | 21 | 2 | 18 | 0 | hec, syslog |
| Splunk Community / SC4SNMP | 6 | 3 | 3 | 1 | hec, syslog |
| Suricata (OISF) | 1 | 1 | 0 | 1 | hec_event |
| Symantec (Broadcom), Web & Network Secu… | 1 | 1 | 0 | 1 | syslog |
| Sysdig | 1 | 1 | 0 | 1 | hec |
| Tanium | 1 | 1 | 0 | 1 | hec |
| Tenable | 1 | 1 | 0 | 1 | hec |
| Traefik Labs | 1 | 1 | 0 | 1 | hec |
| Trellix (formerly McAfee) | 1 | 1 | 0 | 1 | hec |
| Veeam | 1 | 1 | 0 | 1 | hec |
| VMware by Broadcom | 4 | 1 | 1 | 1 | hec, syslog |
| WatchGuard | 2 | 0 | 0 | 0 | syslog |
| Wazuh | 1 | 1 | 0 | 1 | syslog |
| Zeek (Bro) | 1 | 1 | 0 | 1 | hec_event |
| Zscaler | 6 | 2 | 2 | 1 | hec_event, syslog |

## By sourcetype

`G` generated, `R` sample replay, `-` none. Scenarios counts the registered scenarios that use the sourcetype; Dash counts those with a dashboard.

| Vendor | Product | Sourcetype | Kind | Protocol | Gen | Byte | Indexed | Scenarios | Dash |
|---|---|---|---|---|---|---|---|---|---|
| A10 Networks | A10 Acos Cgnat | `a10:acos:cgnat` | event | syslog | - | - | - | 0 | 0 |
| A10 Networks | A10 Acos Syslog | `a10:acos:syslog` | event | syslog | - | - | - | 0 | 0 |
| Amazon Web Services | AWS CloudFront Access Logs | `aws:cloudfront:accesslogs` | event | syslog | G | yes | yes | 6 | 6 |
| Amazon Web Services | AWS CloudTrail | `aws:cloudtrail` | event | hec_event | G | yes | yes | 6 | 6 |
| Amazon Web Services | AWS CloudTrail Lake (OCSF) | `aws:cloudtrail:lake` | event | hec_event | G | yes | yes | 6 | 6 |
| Amazon Web Services | AWS VPC Flow Logs (CloudWatch) | `aws:cloudwatchlogs:vpcflow` | event | hec_event | G | yes | yes | 4 | 4 |
| Arista Networks | Arista EOS Core Switching | `arista:eos` | event | syslog | R | - | - | 1 | 1 |
| Arista Networks | Arista Eos Syslog | `arista:eos:syslog` | event | syslog | R | - | - | 0 | 0 |
| Arista Networks | Arista Flow Ipfix | `arista:flow:ipfix` | event | syslog | G | - | - | 1 | 1 |
| Arista Networks | Arista Metrics Telemetry | `arista:telemetry:json` | event | syslog | R | - | - | 3 | 1 |
| Aruba / HPE | Aruba Instant AP & Switch Event | `aruba` | event | syslog | R | - | - | 0 | 0 |
| Aruba / HPE | Aruba Controller Authentication Manager | `aruba:authmgr` | event | syslog | R | - | - | 0 | 0 |
| Aruba / HPE | Aruba Cx Security | `aruba:cx:security` | event | syslog | - | - | - | 0 | 0 |
| Aruba / HPE | Aruba Cx Syslog | `aruba:cx:syslog` | event | syslog | - | - | - | 0 | 0 |
| Aruba / HPE | Aruba Station Management (STM) | `aruba:stm` | event | syslog | R | - | - | 0 | 0 |
| Aruba / HPE | Aruba Syslog | `aruba:syslog` | event | syslog | R | - | - | 0 | 0 |
| Atlassian | Confluence Cloud audit | `Confluence:audit log` | event | hec | G | yes | yes | 3 | 3 |
| Barracuda Networks | Web Application Firewall | `barracuda:waf:web_firewall` | event | hec | G | yes | yes | 4 | 4 |
| BeyondTrust | Password Safe audit | `ccx:beyondinsight:passwordsafe` | event | hec | G | yes | yes | 5 | 5 |
| Bitdefender | GravityZone push notifications | `bitdefender:gz` | event | hec | G | yes | yes | 4 | 4 |
| Check Point Software | Checkpoint Cef | `checkpoint:cef` | event | syslog | R | - | - | 0 | 0 |
| Check Point Software | Checkpoint Firewall | `checkpoint:firewall` | event | syslog | - | - | - | 0 | 0 |
| Check Point Software | Checkpoint Threat | `checkpoint:threat` | event | syslog | - | - | - | 0 | 0 |
| Cisco Duo | Cisco Duo Account | `cisco:duo:account` | event | syslog | R | - | - | 0 | 0 |
| Cisco Duo | Cisco Duo Activity | `cisco:duo:activity` | event | syslog | R | - | - | 0 | 0 |
| Cisco Duo | Cisco Duo Administrator | `cisco:duo:administrator` | event | syslog | G | yes | yes | 6 | 6 |
| Cisco Duo | Cisco Duo Auth | `cisco:duo:auth` | event | syslog | - | - | - | 0 | 0 |
| Cisco Duo | Cisco Duo Authentication | `cisco:duo:authentication` | event | syslog | R | - | - | 0 | 0 |
| Cisco Duo | Cisco Duo Authentication V2 | `cisco:duo:authentication_v2` | event | syslog | R | - | - | 0 | 0 |
| Cisco Duo | Cisco Duo Endpoint | `cisco:duo:endpoint` | event | syslog | R | - | - | 0 | 0 |
| Cisco Duo | Cisco Duo Push Prompt | `cisco:duo:push:prompt` | event | syslog | - | - | - | 1 | 1 |
| Cisco Duo | Cisco Duo Remote Vpn | `cisco:duo:remote:vpn` | event | syslog | G | - | - | 1 | 1 |
| Cisco Duo | Cisco Duo User | `cisco:duo:user` | event | syslog | R | - | - | 0 | 0 |
| Cisco Meraki | Cisco Meraki Syslog | `cisco:meraki:syslog` | event | syslog | G | yes | yes | 1 | 1 |
| Cisco Meraki | Meraki Accesspoints | `meraki:accesspoints` | event | syslog | R | - | - | 2 | 1 |
| Cisco Meraki | Meraki Airmarshal | `meraki:airmarshal` | event | syslog | R | - | - | 0 | 0 |
| Cisco Meraki | Meraki Appliance | `meraki:appliance` | event | syslog | - | - | - | 0 | 0 |
| Cisco Meraki | Meraki Appliancesdwanstatistics | `meraki:appliancesdwanstatistics` | event | syslog | R | - | - | 0 | 0 |
| Cisco Meraki | Meraki Appliancesdwanstatuses | `meraki:appliancesdwanstatuses` | event | syslog | R | - | - | 0 | 0 |
| Cisco Meraki | Meraki Assurancealerts | `meraki:assurancealerts` | event | syslog | G | - | - | 2 | 1 |
| Cisco Meraki | Meraki Devices | `meraki:devices` | event | syslog | R | - | - | 0 | 0 |
| Cisco Meraki | Meraki Devices Availabilities | `meraki:devicesavailabilitieschangehistory` | event | syslog | R | - | - | 0 | 0 |
| Cisco Meraki | Meraki Organizationsecurity | `meraki:organizationsecurity` | event | syslog | R | - | - | 0 | 0 |
| Cisco Meraki | Meraki Security | `meraki:security` | event | syslog | - | - | - | 0 | 0 |
| Cisco Meraki | Meraki Securityappliances | `meraki:securityappliances` | event | syslog | - | - | - | 0 | 0 |
| Cisco Meraki | Meraki Summarytopappliancesbyutilization | `meraki:summarytopappliancesbyutilization` | event | syslog | R | - | - | 0 | 0 |
| Cisco Meraki | Meraki Summarytopclientsbyusage | `meraki:summarytopclientsbyusage` | event | syslog | R | - | - | 0 | 0 |
| Cisco Meraki | Meraki Summarytopdevicesbyusage | `meraki:summarytopdevicesbyusage` | event | syslog | R | - | - | 0 | 0 |
| Cisco Meraki | Meraki Switchportsbyswitch | `meraki:switchportsbyswitch` | event | syslog | R | - | - | 0 | 0 |
| Cisco Meraki | Meraki Switchportsoverview | `meraki:switchportsoverview` | event | syslog | R | - | - | 0 | 0 |
| Cisco Systems | Cisco Aci Fault | `cisco:aci:fault` | event | syslog | - | - | - | 0 | 0 |
| Cisco Systems | Cisco Aci Syslog | `cisco:aci:syslog` | event | syslog | - | - | - | 0 | 0 |
| Cisco Systems | Cisco ASA Firewall Connection & Policy | `cisco:asa` | event | syslog | G | - | - | 5 | 3 |
| Cisco Systems | Cisco ASA Syslog Message Stream | `cisco:asa:syslog` | event | syslog | R | - | - | 0 | 0 |
| Cisco Systems | Cisco Catalyst Client | `cisco:catalyst:client` | event | syslog | R | - | - | 0 | 0 |
| Cisco Systems | Cisco Catalyst Clienthealth | `cisco:catalyst:clienthealth` | event | syslog | G | - | - | 2 | 1 |
| Cisco Systems | Cisco Catalyst Compliance | `cisco:catalyst:compliance` | event | syslog | R | - | - | 0 | 0 |
| Cisco Systems | Cisco Catalyst Devicehealth | `cisco:catalyst:devicehealth` | event | syslog | R | - | - | 0 | 0 |
| Cisco Systems | Cisco Catalyst Issue | `cisco:catalyst:issue` | event | syslog | R | - | - | 0 | 0 |
| Cisco Systems | Cisco Catalyst Networkhealth | `cisco:catalyst:networkhealth` | event | syslog | R | - | - | 2 | 0 |
| Cisco Systems | Cisco Catalyst Rogue Allowed | `cisco:catalyst:rogue:allowed` | event | syslog | R | - | - | 0 | 0 |
| Cisco Systems | Cisco Catalyst Rogue Counts | `cisco:catalyst:rogue:counts` | event | syslog | R | - | - | 0 | 0 |
| Cisco Systems | Cisco Catalyst Rogue Threat Details | `cisco:catalyst:rogue:threat_details` | event | syslog | G | - | - | 4 | 2 |
| Cisco Systems | Cisco Catalyst Rogue Verbose | `cisco:catalyst:rogue:verbose` | event | syslog | G | yes | yes | 3 | 3 |
| Cisco Systems | Cisco Catalyst Rogue Verbose Legacy | `cisco:catalyst:rogue:verbose:legacy` | event | syslog | R | - | - | 0 | 0 |
| Cisco Systems | Cisco Catalyst Rogue Wired | `cisco:catalyst:rogue:wired` | event | syslog | R | - | - | 0 | 0 |
| Cisco Systems | Cisco Catalyst Script Heartbeat | `cisco:catalyst:script:heartbeat` | event | syslog | R | - | - | 0 | 0 |
| Cisco Systems | Cisco Catalyst Security Awips Signatures | `cisco:catalyst:security:awips_signatures` | event | syslog | R | - | - | 0 | 0 |
| Cisco Systems | Cisco Catalyst Security Events | `cisco:catalyst:security:events` | event | syslog | G | - | yes | 4 | 4 |
| Cisco Systems | Cisco Catalyst Security Profile | `cisco:catalyst:security:profile` | event | syslog | R | - | - | 0 | 0 |
| Cisco Systems | Cisco Catalyst Security Profile Signatu… | `cisco:catalyst:security:profile_signatures` | event | syslog | G | yes | yes | 3 | 3 |
| Cisco Systems | Cisco Catalyst Security Rules | `cisco:catalyst:security:rules` | event | syslog | R | - | - | 0 | 0 |
| Cisco Systems | Cisco Catalyst Securityadvisory | `cisco:catalyst:securityadvisory` | event | syslog | R | - | - | 0 | 0 |
| Cisco Systems | Cisco Catalyst Syslog | `cisco:catalyst:syslog` | event | syslog | - | - | - | 0 | 0 |
| Cisco Systems | Cisco Catalyst Threat List | `cisco:catalyst:threat:list` | event | syslog | R | - | - | 0 | 0 |
| Cisco Systems | Cisco Catalyst Threat Signatures | `cisco:catalyst:threat:signatures` | event | syslog | R | - | - | 0 | 0 |
| Cisco Systems | Cisco Catalyst Threat Summary | `cisco:catalyst:threat:summary` | event | syslog | G | yes | yes | 3 | 3 |
| Cisco Systems | Cisco Catalyst Threat Summary Legacy | `cisco:catalyst:threat:summary:legacy` | event | syslog | G | yes | yes | 3 | 3 |
| Cisco Systems | Cisco Cloud Security DNS | `cisco:cloud_security:dns` | event | syslog | G | yes | yes | 3 | 3 |
| Cisco Systems | Cisco Cloud Security Firewall | `cisco:cloud_security:firewall` | event | syslog | G | yes | yes | 3 | 3 |
| Cisco Systems | Cisco Cloud Security Web Proxy | `cisco:cloud_security:proxy` | event | syslog | G | yes | yes | 3 | 3 |
| Cisco Systems | Cisco Dc Aci Class | `cisco:dc:aci:class` | event | syslog | G | yes | yes | 0 | 0 |
| Cisco Systems | Cisco ACI Fabric State Events | `cisco:dc:aci:events` | event | syslog | R | - | - | 0 | 0 |
| Cisco Systems | Cisco Dc Aci Bridge Domain | `cisco:dc:aci:health` | event | syslog | G | - | yes | 1 | 1 |
| Cisco Systems | Cisco Dc Nexus9K | `cisco:dc:nexus9k` | event | syslog | G | yes | yes | 0 | 0 |
| Cisco Systems | Cisco Dc Nexus9K Syslog | `cisco:dc:nexus9k:syslog` | event | syslog | G | - | yes | 3 | 2 |
| Cisco Systems | Cisco Dnac Audit Logs | `cisco:dnac:audit:logs` | event | syslog | R | - | - | 0 | 0 |
| Cisco Systems | Cisco Dnac Client | `cisco:dnac:client` | event | syslog | R | - | - | 0 | 0 |
| Cisco Systems | Cisco Dnac Clienthealth | `cisco:dnac:clienthealth` | event | syslog | R | - | - | 0 | 0 |
| Cisco Systems | Cisco Dnac Compliance | `cisco:dnac:compliance` | event | syslog | R | - | - | 0 | 0 |
| Cisco Systems | Cisco Dnac Devicehealth | `cisco:dnac:devicehealth` | event | syslog | R | - | - | 0 | 0 |
| Cisco Systems | Cisco Dnac Issue | `cisco:dnac:issue` | event | syslog | R | - | - | 0 | 0 |
| Cisco Systems | Cisco Dnac Networkhealth | `cisco:dnac:networkhealth` | event | syslog | R | - | - | 0 | 0 |
| Cisco Systems | Cisco Dnac Securityadvisory | `cisco:dnac:securityadvisory` | event | syslog | R | - | - | 0 | 0 |
| Cisco Systems | Cisco Dnac Site Topology | `cisco:dnac:site:topology` | event | syslog | R | - | - | 0 | 0 |
| Cisco Systems | Cisco Ftd Syslog | `cisco:ftd:syslog` | event | syslog | R | - | - | 0 | 0 |
| Cisco Systems | Cisco Intersight Advisories | `cisco:intersight:advisories` | event | syslog | R | - | - | 0 | 0 |
| Cisco Systems | Cisco Intersight Alarms | `cisco:intersight:alarms` | event | syslog | R | - | - | 0 | 0 |
| Cisco Systems | Cisco Intersight Auditrecords | `cisco:intersight:auditrecords` | event | syslog | R | - | - | 0 | 0 |
| Cisco Systems | Cisco Intersight Compute | `cisco:intersight:compute` | event | syslog | R | - | - | 0 | 0 |
| Cisco Systems | Cisco Intersight Contracts | `cisco:intersight:contracts` | event | syslog | R | - | - | 0 | 0 |
| Cisco Systems | Cisco Intersight Licenses | `cisco:intersight:licenses` | event | syslog | R | - | - | 0 | 0 |
| Cisco Systems | Cisco Intersight Metrics | `cisco:intersight:metrics` | metric | hec | R | - | - | 0 | 0 |
| Cisco Systems | Cisco Intersight Networkelements | `cisco:intersight:networkelements` | event | syslog | R | - | - | 0 | 0 |
| Cisco Systems | Cisco Intersight Networkobjects | `cisco:intersight:networkobjects` | event | syslog | R | - | - | 0 | 0 |
| Cisco Systems | Cisco Intersight Profiles | `cisco:intersight:profiles` | event | syslog | R | - | - | 0 | 0 |
| Cisco Systems | Cisco Intersight Targets | `cisco:intersight:targets` | event | syslog | R | - | - | 0 | 0 |
| Cisco Systems | Cisco Ios | `cisco:ios` | event | syslog | G | yes | yes | 1 | 1 |
| Cisco Systems | Cisco Ios Mdt | `cisco:ios:mdt` | event | syslog | G | - | yes | 2 | 2 |
| Cisco Systems | Cisco IOS-XE / IOS-XR Model-Driven Tele… | `cisco:ios:mdt:metric` | metric | hec | G | - | - | 4 | 1 |
| Cisco Systems | Cisco IOS System Syslog Facility | `cisco:ios:syslog` | event | syslog | G | - | - | 10 | 4 |
| Cisco Systems | Cisco Ise Nac 8021X | `cisco:ise:nac:8021x` | event | syslog | - | - | - | 3 | 1 |
| Cisco Systems | Cisco Ise Radius Authz Policy | `cisco:ise:radius:authz:policy` | event | syslog | R | - | - | 0 | 0 |
| Cisco Systems | Cisco Ise Radius Policyset | `cisco:ise:radius:policyset` | event | syslog | R | - | - | 0 | 0 |
| Cisco Systems | Cisco Ise Syslog | `cisco:ise:syslog` | event | syslog | G | - | - | 1 | 1 |
| Cisco Systems | Cisco Ise Tacacs Authz Policy | `cisco:ise:tacacs:authz:policy` | event | syslog | R | - | - | 0 | 0 |
| Cisco Systems | Cisco Ise Tacacs Policyset | `cisco:ise:tacacs:policyset` | event | syslog | R | - | - | 0 | 0 |
| Cisco Systems | Cisco Ise Trustsec Sgt | `cisco:ise:trustsec:sgt` | event | syslog | - | - | - | 2 | 0 |
| Cisco Systems | Cisco Isovalent Cilium Events | `cisco:isovalent` | event | hec_event | G | yes | yes | 3 | 3 |
| Cisco Systems | Cisco Isovalent Cilium processConnect | `cisco:isovalent:processConnect` | event | hec_event | G | yes | yes | 3 | 3 |
| Cisco Systems | Cisco Isovalent Cilium processExec | `cisco:isovalent:processExec` | event | hec_event | G | yes | yes | 3 | 3 |
| Cisco Systems | Cisco Mds San Fc | `cisco:mds:san:fc` | event | syslog | - | - | - | 1 | 0 |
| Cisco Systems | Cisco Metrics Splunk Otel | `cisco:metrics` | metric | hec | R | - | - | 0 | 0 |
| Cisco Systems | Cisco Nexus DC Switch Event | `cisco:nexus` | event | syslog | R | - | - | 0 | 0 |
| Cisco Systems | Cisco Nvm Flowdata | `cisco:nvm:flowdata` | event | syslog | R | - | - | 0 | 0 |
| Cisco Systems | Cisco NVM Flow Data v2 | `cisco:nvm:flowdata:v2` | event | hec_event | G | yes | yes | 1 | 1 |
| Cisco Systems | Cisco NX-OS Structured Event Stream | `cisco:nxos` | event | syslog | R | - | - | 0 | 0 |
| Cisco Systems | Cisco NX-OS Syslog Event | `cisco:nxos:syslog` | event | syslog | R | - | - | 0 | 0 |
| Cisco Systems | Cisco Sdwan Aaa 6 Method List State | `cisco:sdwan:AAA-6-METHOD_LIST_STATE` | event | syslog | G | yes | yes | 2 | 2 |
| Cisco Systems | Cisco Sdwan Aaa 6 Notify Mlist State To… | `cisco:sdwan:AAA-6-NOTIFY_MLIST_STATE_TO_AAA_CLIENT` | event | syslog | G | yes | yes | 2 | 2 |
| Cisco Systems | Cisco Sdwan Aaa Audit Message 6 Method … | `cisco:sdwan:AAA_AUDIT_MESSAGE-6-METHOD_LIST_STATE` | event | syslog | G | yes | yes | 2 | 2 |
| Cisco Systems | Cisco Sdwan Aaa Audit Message 6 Notify … | `cisco:sdwan:AAA_AUDIT_MESSAGE-6-NOTIFY_MLIST_STATE_TO_AAA_CLIENT` | event | syslog | G | yes | yes | 2 | 2 |
| Cisco Systems | Cisco Sdwan Bgp 5 Adjchange | `cisco:sdwan:BGP-5-ADJCHANGE` | event | syslog | G | yes | yes | 6 | 5 |
| Cisco Systems | Cisco Sdwan Bgp 5 Nbr Reset | `cisco:sdwan:BGP-5-NBR_RESET` | event | syslog | G | yes | yes | 4 | 4 |
| Cisco Systems | Cisco Sdwan Bgp 6 Nexthop | `cisco:sdwan:BGP-6-NEXTHOP` | event | syslog | G | yes | yes | 0 | 0 |
| Cisco Systems | Cisco Sdwan Bgp Session 5 Adjchange | `cisco:sdwan:BGP_SESSION-5-ADJCHANGE` | event | syslog | G | yes | yes | 0 | 0 |
| Cisco Systems | Cisco Sdwan Cdp 4 Native Vlan Mismatch | `cisco:sdwan:CDP-4-NATIVE_VLAN_MISMATCH` | event | syslog | G | yes | yes | 4 | 4 |
| Cisco Systems | Cisco Sdwan Crypto 6 Isakmp On Off | `cisco:sdwan:CRYPTO-6-ISAKMP_ON_OFF` | event | syslog | G | yes | yes | 0 | 0 |
| Cisco Systems | Cisco Sdwan Cts 3 Aaa No Radius Server | `cisco:sdwan:CTS-3-AAA_NO_RADIUS_SERVER` | event | syslog | G | yes | yes | 2 | 2 |
| Cisco Systems | Cisco Sdwan Dmi 5 Auth Passed | `cisco:sdwan:DMI-5-AUTH_PASSED` | event | syslog | G | yes | yes | 0 | 0 |
| Cisco Systems | Cisco Sdwan Dmi 5 Config I | `cisco:sdwan:DMI-5-CONFIG_I` | event | syslog | G | yes | yes | 0 | 0 |
| Cisco Systems | Cisco Sdwan Dmi 5 Sync Complete | `cisco:sdwan:DMI-5-SYNC_COMPLETE` | event | syslog | G | yes | yes | 4 | 4 |
| Cisco Systems | Cisco Sdwan Dmi 5 Sync Needed | `cisco:sdwan:DMI-5-SYNC_NEEDED` | event | syslog | G | yes | yes | 4 | 4 |
| Cisco Systems | Cisco Sdwan Dmi 5 Sync Start | `cisco:sdwan:DMI-5-SYNC_START` | event | syslog | G | yes | yes | 4 | 4 |
| Cisco Systems | Cisco Sdwan Environmental 1 Alert | `cisco:sdwan:ENVIRONMENTAL-1-ALERT` | event | syslog | G | yes | yes | 4 | 4 |
| Cisco Systems | Cisco Sdwan Eventlib 3 Cpuhog | `cisco:sdwan:EVENTLIB-3-CPUHOG` | event | syslog | G | yes | yes | 4 | 4 |
| Cisco Systems | Cisco Sdwan Iosxe 3 Platform | `cisco:sdwan:IOSXE-3-PLATFORM` | event | syslog | G | yes | yes | 4 | 4 |
| Cisco Systems | Cisco Sdwan Iosxe Infra 4 No Punt Keepa… | `cisco:sdwan:IOSXE_INFRA-4-NO_PUNT_KEEPALIVE` | event | syslog | G | yes | yes | 4 | 4 |
| Cisco Systems | Cisco Sdwan Iosxe Rp Pae Not 6 Pae Star… | `cisco:sdwan:IOSXE_RP_PAE_NOT-6-PAE_STARTUP` | event | syslog | G | yes | yes | 0 | 0 |
| Cisco Systems | Cisco Sdwan Lineproto 5 Updown | `cisco:sdwan:LINEPROTO-5-UPDOWN` | event | syslog | G | yes | yes | 4 | 4 |
| Cisco Systems | Cisco Sdwan Link 5 Changed | `cisco:sdwan:LINK-5-CHANGED` | event | syslog | G | yes | yes | 4 | 4 |
| Cisco Systems | Cisco Sdwan Link 5 Updown | `cisco:sdwan:LINK-5-UPDOWN` | event | syslog | G | yes | yes | 4 | 4 |
| Cisco Systems | Cisco Sdwan Mdt Connection 6 State Chan… | `cisco:sdwan:MDT_CONNECTION-6-STATE_CHANGED` | event | syslog | G | yes | yes | 4 | 4 |
| Cisco Systems | Cisco Sdwan Msdp 5 Peer Updown | `cisco:sdwan:MSDP-5-PEER_UPDOWN` | event | syslog | G | yes | yes | 4 | 4 |
| Cisco Systems | Cisco Sdwan Ndbman 5 Config I | `cisco:sdwan:NDBMAN-5-CONFIG_I` | event | syslog | G | yes | yes | 4 | 4 |
| Cisco Systems | Cisco Sdwan Ospf 5 Adjchg | `cisco:sdwan:OSPF-5-ADJCHG` | event | syslog | G | yes | yes | 4 | 4 |
| Cisco Systems | Cisco Sdwan Pki 6 Authoritative Clock | `cisco:sdwan:PKI-6-AUTHORITATIVE_CLOCK` | event | syslog | G | yes | yes | 4 | 4 |
| Cisco Systems | Cisco Sdwan Platform 4 Element Warning | `cisco:sdwan:PLATFORM-4-ELEMENT_WARNING` | event | syslog | G | yes | yes | 4 | 4 |
| Cisco Systems | Cisco Sdwan Sys 5 Config P | `cisco:sdwan:SYS-5-CONFIG_P` | event | syslog | G | yes | yes | 0 | 0 |
| Cisco Systems | Cisco SD-WAN Management Access | `cisco:sdwan:access` | event | syslog | G | yes | yes | 1 | 1 |
| Cisco Systems | Cisco Sdwan Linkhealth | `cisco:sdwan:linkhealth` | event | syslog | G | - | - | 3 | 1 |
| Cisco Systems | Cisco Sdwan Sitehealth | `cisco:sdwan:sitehealth` | event | syslog | R | - | - | 0 | 0 |
| Cisco Systems | Cisco Sdwan Ssetunnels | `cisco:sdwan:ssetunnels` | event | syslog | G | yes | yes | 2 | 2 |
| Cisco Systems | Cisco Sdwan Syslog | `cisco:sdwan:syslog` | event | syslog | G | yes | yes | 1 | 1 |
| Cisco Systems | Cisco Sdwan System Logs | `cisco:sdwan:system:logs` | event | syslog | R | - | - | 0 | 0 |
| Cisco Systems | Cisco Sdwan Sytem Logs | `cisco:sdwan:sytem:logs` | event | syslog | G | yes | yes | 0 | 0 |
| Cisco Systems | Cisco Sdwan Tunnelhealth | `cisco:sdwan:tunnelhealth` | event | syslog | R | - | - | 0 | 0 |
| Cisco Systems | Cisco Sdwan Utd Logs | `cisco:sdwan:utd:logs` | event | syslog | G | yes | yes | 2 | 2 |
| Cisco Systems | Cisco Sdwan Utdhealth | `cisco:sdwan:utdhealth` | event | syslog | G | yes | yes | 2 | 2 |
| Cisco Systems | Cisco Se | `cisco:se` | event | syslog | R | - | - | 0 | 0 |
| Cisco Systems | Cisco Secure Access RA-VPN Events | `cisco:secure_access:security_events_ravpn` | event | hec_event | G | yes | yes | 6 | 6 |
| Cisco Systems | Cisco Sfw Estreamer | `cisco:sfw:estreamer` | event | syslog | G | yes | yes | 1 | 1 |
| Cisco Systems | Cisco Sfw Policy | `cisco:sfw:policy` | event | syslog | R | - | - | 0 | 0 |
| Cisco Systems | Cisco Thousandeyes Event | `cisco:thousandeyes:event` | event | syslog | R | - | - | 0 | 0 |
| Cisco Systems | Cisco Thousandeyes Metric | `cisco:thousandeyes:metric` | metric | hec | G | - | - | 3 | 2 |
| Cisco Systems | Cisco Thousandeyes Path Vis | `cisco:thousandeyes:path-vis` | event | syslog | R | - | - | 1 | 1 |
| Cisco Systems | Cisco Syslog | `cisco_syslog` | event | syslog | R | - | - | 0 | 0 |
| Cisco Systems | NetSpout Ingestion Preflight Probe | `datablaster:preflight` | event | syslog | R | - | - | 0 | 0 |
| Cisco Systems | NetSpout Telemetry Canary Probe | `datablaster:probe` | event | syslog | R | - | - | 0 | 0 |
| Cisco Systems | NetSpout Native SNMPv2c Polling Events | `netspout:snmp:poll` | event | snmp | G | - | - | 1 | 1 |
| Cisco Systems | NetSpout Native SNMPv2c Traps & Informs | `netspout:snmp:trap` | event | snmp | G | - | - | 1 | 1 |
| Cisco Systems | Openconfig Gnmi Telemetry | `openconfig:gnmi:telemetry` | event | syslog | - | - | - | 2 | 0 |
| Cisco Systems | Opsec | `opsec` | event | syslog | - | - | - | 0 | 0 |
| Citrix / Cloud Software Group | Citrix Netscaler Syslog | `citrix:netscaler:syslog` | event | syslog | - | - | - | 0 | 0 |
| Citrix / Cloud Software Group | Citrix Netscaler Web | `citrix:netscaler:web` | event | syslog | - | - | - | 0 | 0 |
| Claroty | CTD CEF | `claroty:cef` | event | hec | G | yes | yes | 5 | 5 |
| Cloudflare | Cloudflare Firewall | `cloudflare:firewall` | event | syslog | - | - | - | 0 | 0 |
| Cloudflare | Cloudflare Json | `cloudflare:json` | event | syslog | R | - | - | 0 | 0 |
| Cloudflare | Cloudflare R2 Metrics | `cloudflare:r2:json` | event | syslog | R | - | - | 0 | 0 |
| CrowdStrike | CrowdStrike Falcon Sensor Events | `crowdstrike:events:sensor` | event | hec_event | G | yes | yes | 4 | 4 |
| CrushFTP | CrushFTP Session Logs | `crushftp:sessionlogs` | event | syslog_rfc3164 | G | yes | yes | 2 | 2 |
| Cybereason | Malops feed | `cybereason:malops` | event | hec | G | yes | yes | 4 | 4 |
| Darktrace | Model breach alerts | `darktrace` | event | hec | G | yes | yes | 4 | 4 |
| Dell Technologies | Dell Os10 Syslog | `dell:os10:syslog` | event | syslog | - | - | - | 0 | 0 |
| Docker | Docker Engine Events | `docker_events` | event | hec | G | yes | yes | 3 | 3 |
| Elastic | Elasticsearch server logs | `elasticsearch:json` | event | hec | G | yes | yes | 5 | 5 |
| ExtraHop Networks | Extrahop Eda Alert | `extrahop:eda:alert` | event | syslog | R | - | - | 0 | 0 |
| ExtraHop Networks | Extrahop Metrics Performance | `extrahop:eda:metrics` | metric | hec | R | - | - | 0 | 0 |
| Extreme Networks | Extreme Exos Syslog | `extreme:exos:syslog` | event | syslog | - | - | - | 0 | 0 |
| Extreme Networks | Extreme Voss Syslog | `extreme:voss:syslog` | event | syslog | - | - | - | 0 | 0 |
| F5 Networks | F5 BIG-IP Local Traffic Manager (LTM) | `f5:bigip:ltm` | event | syslog | G | - | - | 3 | 2 |
| F5 Networks | F5 Bigip Syslog | `f5:bigip:syslog` | event | syslog | R | - | - | 0 | 0 |
| Forcepoint | Forcepoint Ngfw Alert | `forcepoint:ngfw:alert` | event | syslog | - | - | - | 0 | 0 |
| Forcepoint | Forcepoint Ngfw Traffic | `forcepoint:ngfw:traffic` | event | syslog | - | - | - | 0 | 0 |
| Fortinet | Fortinet Fortigate Sdwan Alert | `fgt_event` | event | syslog | R | - | - | 0 | 0 |
| Fortinet | Fortinet Fortigate Traffic | `fgt_traffic` | event | syslog | R | - | - | 0 | 0 |
| Fortinet | Fortinet FortiGate System Event | `fortigate_event` | event | syslog | R | - | - | 0 | 0 |
| Fortinet | Fortinet FortiGate Traffic Log | `fortigate_traffic` | event | syslog | R | - | - | 0 | 0 |
| Fortinet | Fortinet FortiGate Unified Security Eve… | `fortinet:fortigate` | event | syslog | R | - | - | 0 | 0 |
| Fortinet | Fortinet Fortigate Event | `fortinet:fortigate:event` | event | syslog | - | - | - | 0 | 0 |
| Fortinet | Fortinet Fortigate Traffic | `fortinet:fortigate:traffic` | event | syslog | - | - | - | 0 | 0 |
| Fortinet | Fortinet Fortigate Utm | `fortinet:fortigate:utm` | event | syslog | G | - | - | 2 | 1 |
| GitHub | Enterprise audit logs | `github:enterprise:audit` | event | hec | G | yes | yes | 5 | 5 |
| GitLab | Self-Managed audit events | `gitlab:audit:json` | event | hec | G | yes | yes | 5 | 5 |
| Google Cloud | Google Cloud Audit Logs | `gcp:audit` | event | hec_event | G | yes | yes | 3 | 3 |
| Google Workspace | Gmail BigQuery Message Export | `gsuite:gmail:bigquery` | event | hec_event | G | yes | yes | 6 | 6 |
| Google Workspace | Google Workspace Login Reports | `gws:reports:login` | event | hec_event | G | yes | yes | 6 | 6 |
| HashiCorp | Vault audit | `hashicorp_vault_audit_log` | event | hec | G | yes | yes | 3 | 3 |
| Huawei Technologies | Huawei Vrp Syslog | `huawei:vrp:syslog` | event | syslog | - | - | - | 0 | 0 |
| Huawei Technologies | Huawei Vrp Traffic | `huawei:vrp:traffic` | event | syslog | - | - | - | 0 | 0 |
| IBM | QRadar offense events | `ibm:qradar:offense` | event | hec | G | yes | yes | 5 | 5 |
| IBM MQ | IBM MQ native error log | `ibm:mq:errorlog` | event | hec | G | yes | yes | 2 | 2 |
| Imperva | SecureSphere CEF | `imperva:securesphere:cef` | event | hec | G | yes | yes | 4 | 4 |
| Juniper Networks | Juniper Junos Routing & System Log | `juniper:junos` | event | syslog | G | - | - | 4 | 2 |
| Juniper Networks | Juniper Junos Syslog Transport | `juniper:junos:syslog` | event | syslog | R | - | - | 0 | 0 |
| Juniper Networks | Juniper Syslog | `juniper:syslog` | event | syslog | R | - | - | 0 | 0 |
| Kubernetes & Falco (CNCF) | Kubernetes Audit Log | `kube:audit` | event | hec_event | G | yes | yes | 2 | 2 |
| Kubernetes & Falco (CNCF) | Falco Runtime Security Events | `kube:container:falco` | event | hec_event | G | yes | yes | 2 | 2 |
| Linux Infrastructure | Linux auditd Records | `auditd` | event | syslog_rfc3164 | G | yes | yes | 3 | 3 |
| Linux Infrastructure | ISC dhcpd Lease Events | `dhcpd` | event | syslog | G | yes | yes | 1 | 1 |
| Linux Infrastructure | Linux /var/log/messages | `linux_messages_syslog` | event | syslog_rfc3164 | G | yes | yes | 3 | 3 |
| Linux Infrastructure | Linux /var/log/secure | `linux_secure` | event | syslog | G | yes | yes | 1 | 1 |
| Microsoft 365 | MS Exchange Management Audit | `MSExchange:Management` | event | syslog | G | yes | yes | 1 | 1 |
| Microsoft 365 | M365 Graph Message Trace | `o365:graph:messagetrace` | event | hec_event | G | yes | yes | 6 | 6 |
| Microsoft 365 | Microsoft 365 Management Activity | `o365:management:activity` | event | hec_event | G | yes | yes | 6 | 6 |
| Microsoft 365 | M365 Reporting Message Trace | `o365:reporting:messagetrace` | event | hec_event | G | yes | yes | 6 | 6 |
| Microsoft Azure Monitor | Microsoft Entra ID (Azure AD) Monitor | `azure:monitor:aad` | event | hec_event | G | yes | yes | 6 | 6 |
| Microsoft Azure Monitor | Azure Activity Log | `azure:monitor:activity` | event | hec_event | G | yes | yes | 6 | 6 |
| Microsoft Windows | Windows NTLM Operational XML | `XmlWinEventLog:Microsoft-Windows-NTLM/Operational` | event | hec_event | G | yes | yes | 3 | 3 |
| Microsoft Windows | Windows PowerShell Operational XML | `XmlWinEventLog:Microsoft-Windows-PowerShell/Operational` | event | hec_event | G | yes | yes | 3 | 3 |
| Microsoft Windows | Windows Sysmon XML | `XmlWinEventLog:Microsoft-Windows-Sysmon/Operational` | event | hec_event | G | yes | yes | 3 | 3 |
| Microsoft Windows | Windows Defender Operational XML | `XmlWinEventLog:Microsoft-Windows-Windows Defender/Operational` | event | hec_event | G | yes | yes | 3 | 3 |
| Microsoft Windows | Windows Security Audit XML | `XmlWinEventLog:Security` | event | hec_event | G | yes | yes | 3 | 3 |
| Microsoft Windows | Windows System Channel XML | `XmlWinEventLog:System` | event | hec | G | yes | yes | 1 | 1 |
| Microsoft Windows | Microsoft IIS W3C Access | `iis` | event | syslog | G | yes | yes | 1 | 1 |
| Microsoft Windows | Sysmon for Linux | `sysmon:linux` | event | hec_event | G | yes | yes | 3 | 3 |
| MikroTik | RouterOS console log | `mikrotik:routeros` | event | hec | G | yes | yes | 5 | 5 |
| Model Context Protocol (agent… | Model Context Protocol JSON-RPC | `mcp:jsonrpc` | event | hec_event | G | yes | yes | 2 | 2 |
| MongoDB | MongoDB structured server log | `mongodb:log` | event | hec | G | yes | yes | 3 | 3 |
| NetScout Systems | Netscout Omnis Alert | `netscout:omnis:alert` | event | syslog | R | - | - | 0 | 0 |
| Netskope | Netskope Alerts | `netskope:alerts` | event | syslog | - | - | - | 0 | 0 |
| Netskope | Netskope Events | `netskope:events` | event | syslog | - | - | - | 0 | 0 |
| Netskope | Netskope Json | `netskope:json` | event | syslog | R | - | - | 0 | 0 |
| Netskope | Netskope Security Service Edge (SSE) | `netskope:sse` | event | syslog | R | - | - | 0 | 0 |
| NGINX (F5) | NGINX combined access log | `nginx:access` | event | hec | G | yes | yes | 6 | 6 |
| NGINX (F5) | NGINX Plus access (key=value) | `nginx:plus:access` | event | hec | G | yes | yes | 0 | 0 |
| Nokia | Nokia Sr Syslog | `nokia:sr:syslog` | event | syslog | - | - | - | 0 | 0 |
| Nokia | Nokia 7750 SR OS Service Router Event | `nokia:sros` | event | syslog | R | - | - | 0 | 0 |
| Nokia | Nokia 7750 SR OS Syslog Facility | `nokia:sros:syslog` | event | syslog | G | - | - | 3 | 2 |
| Nozomi Networks | Nozomi Networks Universal Alert | `nozomi:universal_alert` | event | syslog | G | yes | yes | 3 | 3 |
| Nutanix | Nutanixpc Disks | `nutanixPC_disks` | event | syslog | R | - | - | 0 | 0 |
| Nutanix | Nutanix Prism Central Syslog (Colon For… | `nutanixpc:syslog` | event | syslog | R | - | - | 0 | 0 |
| Nutanix | Nutanix Prism Central VM Inventory (Col… | `nutanixpc:vms` | event | syslog | R | - | - | 0 | 0 |
| Nutanix | Nutanixpc Alerts | `nutanixpc_alerts` | event | syslog | R | - | - | 0 | 0 |
| Nutanix | Nutanixpc Cluster Performance | `nutanixpc_cluster_performance` | metric | hec | R | - | - | 0 | 0 |
| Nutanix | Nutanixpc Clusters | `nutanixpc_clusters` | event | syslog | R | - | - | 0 | 0 |
| Nutanix | Nutanixpc Disk Performance | `nutanixpc_disk_performance` | metric | hec | R | - | - | 0 | 0 |
| Nutanix | Nutanixpc Events | `nutanixpc_events` | event | syslog | R | - | - | 0 | 0 |
| Nutanix | Nutanixpc Host Performance | `nutanixpc_host_performance` | metric | hec | R | - | - | 0 | 0 |
| Nutanix | Nutanixpc Hosts | `nutanixpc_hosts` | event | syslog | R | - | - | 0 | 0 |
| Nutanix | Nutanixpc Prismcentrals | `nutanixpc_prismCentrals` | event | syslog | R | - | - | 0 | 0 |
| Nutanix | Nutanixpc Storage Containers | `nutanixpc_storage_containers` | event | syslog | R | - | - | 0 | 0 |
| Nutanix | Nutanixpc Syslog | `nutanixpc_syslog` | event | syslog | R | - | - | 0 | 0 |
| Nutanix | Nutanixpc Vm Performance | `nutanixpc_vm_performance` | metric | hec | R | - | - | 0 | 0 |
| Nutanix | Nutanixpc Vms | `nutanixpc_vms` | event | syslog | R | - | - | 0 | 0 |
| Nutanix | Nutanixpc Volume Groups | `nutanixpc_volume_groups` | event | syslog | R | - | - | 0 | 0 |
| Okta | Okta IM2 Logs | `OktaIM2:log` | event | hec_event | G | yes | yes | 6 | 6 |
| Ollama (local LLM runtime) | Ollama Server Logs | `ollama:server` | event | hec_event | G | yes | yes | 2 | 2 |
| OpenTelemetry | OpenTelemetry OTLP/JSON | `opentelemetry:otlp` | event | hec_event | G | yes | yes | 3 | 3 |
| Oracle | Database native audit | `oracle:audit:text` | event | hec | G | yes | yes | 2 | 2 |
| osquery | osquery Results | `osquery:results` | event | hec_event | G | yes | yes | 7 | 7 |
| Palo Alto Networks | Pan Ble Iot Sensor | `pan:ble:iot:sensor` | event | syslog | - | - | - | 1 | 0 |
| Palo Alto Networks | Pan Config | `pan:config` | event | syslog | - | - | - | 0 | 0 |
| Palo Alto Networks | Pan System | `pan:system` | event | syslog | G | - | yes | 3 | 3 |
| Palo Alto Networks | Pan Threat | `pan:threat` | event | syslog | G | - | yes | 6 | 5 |
| Palo Alto Networks | Pan Traffic | `pan:traffic` | event | syslog | G | - | yes | 7 | 4 |
| pfSense (Netgate) | pfSense filterlog | `pfsense:filterlog` | event | hec | G | yes | yes | 4 | 4 |
| Proofpoint | Targeted Attack Protection SIEM | `proofpoint_tap_siem` | event | hec | G | yes | yes | 3 | 3 |
| Qualys | Platform user activity log | `qualys:activityLog` | event | hec | G | yes | yes | 5 | 5 |
| Radware | Radware Cwaf Waf | `radware:cwaf:waf` | event | syslog | - | - | - | 0 | 0 |
| Radware | Radware Csms Ddos | `radware:ddos` | event | syslog | R | - | - | 0 | 0 |
| Radware | Radware Defensepro Attack | `radware:defensepro:attack` | event | syslog | - | - | - | 0 | 0 |
| Radware | Radware Cwaf Waf | `radware:waf` | event | syslog | R | - | - | 0 | 0 |
| Rapid7 | InsightVM asset vulnerabilities | `rapid7:insightvm:asset:vulnerability_finding` | event | hec | G | yes | yes | 5 | 5 |
| SailPoint | Identity Security Cloud audit | `sailpoint_identitynow` | event | hec | G | yes | yes | 5 | 5 |
| SentinelOne | Threats channel | `sentinelone:channel:threats` | event | hec | G | yes | yes | 4 | 4 |
| Slack | Enterprise Grid audit logs | `slack:audit` | event | hec | G | yes | yes | 5 | 5 |
| SonicWall | Sonicwall Firewall | `sonicwall:firewall` | event | syslog | - | - | - | 0 | 0 |
| Sophos | Sophos Central Cef | `sophos:central:cef` | event | syslog | R | - | - | 0 | 0 |
| Sophos | Sophos Xg Firewall | `sophos:xg:firewall` | event | syslog | - | - | - | 0 | 0 |
| Splunk / Native | Geo_Tokens | `geo_tokens:generic` | event | syslog | R | - | - | 0 | 0 |
| Splunk / Native | Cisco Metrics Bgp Rib | `httpevent` | event | syslog | R | - | - | 0 | 0 |
| Splunk / Native | Kube Container Calico Kube Controllers | `kube:container:calico-kube-controllers` | event | syslog | R | - | - | 0 | 0 |
| Splunk / Native | Kube Container Calico Node | `kube:container:calico-node` | event | syslog | R | - | - | 0 | 0 |
| Splunk / Native | Kube Container Controller | `kube:container:controller` | event | syslog | R | - | - | 0 | 0 |
| Splunk / Native | Kube Container Coredns | `kube:container:coredns` | event | syslog | R | - | - | 0 | 0 |
| Splunk / Native | Kube Container Hostpath Provisioner | `kube:container:hostpath-provisioner` | event | syslog | R | - | - | 0 | 0 |
| Splunk / Native | Kube Container Install Cni | `kube:container:install-cni` | event | syslog | R | - | - | 0 | 0 |
| Splunk / Native | Kube Container Metrics | `kube:container:metrics` | metric | hec | R | - | - | 0 | 0 |
| Splunk / Native | Kube Container Metrics Server | `kube:container:metrics-server` | metric | hec | R | - | - | 0 | 0 |
| Splunk / Native | Kube Container Mibserver | `kube:container:mibserver` | event | syslog | R | - | - | 0 | 0 |
| Splunk / Native | Kube Container Mongodb | `kube:container:mongodb` | event | syslog | R | - | - | 0 | 0 |
| Splunk / Native | Kube Container Redis | `kube:container:redis` | event | syslog | R | - | - | 0 | 0 |
| Splunk / Native | Kube Container Speaker | `kube:container:speaker` | event | syslog | R | - | - | 0 | 0 |
| Splunk / Native | Kube Container Upgrade Ipam | `kube:container:upgrade-ipam` | event | syslog | R | - | - | 0 | 0 |
| Splunk / Native | Kube Events | `kube:events` | event | syslog | R | - | - | 0 | 0 |
| Splunk / Native | Kube Object Pods | `kube:object:pods` | event | syslog | R | - | - | 0 | 0 |
| Splunk / Native | Netapp Ontap Nas | `netapp:ontap:nas` | event | syslog | - | - | - | 1 | 0 |
| Splunk / Native | Nginx Plus Kv | `nginx:plus:kv` | event | syslog | G | - | - | 5 | 3 |
| Splunk / Native | Postgresql Audit | `postgresql:audit` | event | syslog | G | - | - | 3 | 1 |
| Splunk / Native | Stream Netflow | `stream:netflow` | event | syslog | R | - | - | 0 | 0 |
| Splunk Community / SC4SNMP | Kube Container Splunk Connect For Snmp … | `kube:container:splunk-connect-for-snmp-traps` | event | syslog | R | - | - | 0 | 0 |
| Splunk Community / SC4SNMP | Kube Container Splunk Connect For Snmp … | `kube:container:splunk-connect-for-snmp-worker-sender` | event | syslog | R | - | - | 0 | 0 |
| Splunk Community / SC4SNMP | Kube Container Splunk Connect For Snmp … | `kube:container:splunk-connect-for-snmp-worker-trap` | event | syslog | R | - | - | 0 | 0 |
| Splunk Community / SC4SNMP | Splunk Connect for SNMP (SC4SNMP) Metri… | `sc4snmp:event` | event | syslog | G | - | - | 0 | 0 |
| Splunk Community / SC4SNMP | Sc4Snmp Metric | `sc4snmp:metric` | metric | hec | G | - | yes | 2 | 2 |
| Splunk Community / SC4SNMP | Universal SNMP Trap Receiver Event | `snmp:trap` | event | syslog | G | - | - | 0 | 0 |
| Suricata (OISF) | Suricata EVE JSON | `suricata` | event | hec_event | G | yes | yes | 7 | 7 |
| Symantec (Broadcom), Web & Ne… | Symantec/Broadcom ProxySG Access Log (f… | `bluecoat:proxysg:access:file` | event | syslog | G | yes | yes | 3 | 3 |
| Sysdig | Sysdig Secure runtime and Kubernetes au… | `SysdigSecureEvents` | event | hec | G | yes | yes | 5 | 5 |
| Tanium | Discover managed machines | `tanium:discover:managed` | event | hec | G | yes | yes | 4 | 4 |
| Tenable | Vulnerability Management audit | `tenable:io:audit_logs` | event | hec | G | yes | yes | 5 | 5 |
| Traefik Labs | Traefik Proxy access | `traefik:access:json` | event | hec | G | yes | yes | 5 | 5 |
| Trellix (formerly McAfee) | ePO threat events | `trellix_epo:threat_events` | event | hec | G | yes | yes | 4 | 4 |
| Veeam | Backup & Replication | `veeam_vbr_syslog` | event | hec | G | yes | yes | 3 | 3 |
| VMware by Broadcom | VMware vSphere ESXi Syslog | `vmw-syslog` | event | syslog | G | yes | yes | 1 | 1 |
| VMware by Broadcom | Vmware Nsx Audit | `vmware:nsx:audit` | event | syslog | - | - | - | 0 | 0 |
| VMware by Broadcom | Vmware Nsx Firewall | `vmware:nsx:firewall` | event | syslog | - | - | - | 0 | 0 |
| VMware by Broadcom | Vmware Esx Perf | `vmware:perf:cpu` | metric | hec | R | - | - | 0 | 0 |
| WatchGuard | Watchguard Fireware Alarm | `watchguard:fireware:alarm` | event | syslog | - | - | - | 0 | 0 |
| WatchGuard | Watchguard Fireware Traffic | `watchguard:fireware:traffic` | event | syslog | - | - | - | 0 | 0 |
| Wazuh | Wazuh Manager Alerts (alerts.log) | `wazuh:alerts` | event | syslog | G | yes | yes | 3 | 3 |
| Zeek (Bro) | Zeek (Bro) conn JSON | `bro:conn:json` | event | hec_event | G | yes | yes | 3 | 3 |
| Zscaler | Zscaler Sse Tunnel | `zscaler:tunnel` | event | syslog | R | - | - | 0 | 0 |
| Zscaler | Zscaler Sse Web | `zscaler:web` | event | syslog | R | - | - | 0 | 0 |
| Zscaler | Zscaler Internet Access (ZIA) NSS Log | `zscaler:zia` | event | syslog | G | - | - | 2 | 1 |
| Zscaler | Zscaler Zia Tunnel | `zscaler:zia:tunnel` | event | syslog | - | - | - | 0 | 0 |
| Zscaler | Zscaler Zia Web | `zscaler:zia:web` | event | syslog | - | - | - | 0 | 0 |
| Zscaler | Zscaler NSS Web Proxy Logs | `zscalernss-web` | event | hec_event | G | yes | yes | 6 | 6 |
