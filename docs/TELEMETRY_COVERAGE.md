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
| Dashboard implemented only | Referenced by a scenario whose dashboard exists but is not validated against data | 1 |
| Visually verified | Referenced by a scenario whose dashboard was rendered and inspected | 40 |
| Executed by a scenario contract | Emitted by a declarative scenario contract in automated tests (HEC stubbed), not indexed in Splunk | 25 |
| Not yet implemented | No generator: cataloged only | 47 |

**Modeled sourcetype.** `netspout:scenario:state` is a NetSpout-defined schema (JSON with entity, component, state, previous state, severity, message and an optional measurement), used by 214 scenario contracts where a definition specifies a state progression or a monitoring use case and no vendor log format exists. It is **not** vendor-native and is not in the catalog above.

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

`G` generated, `R` sample replay, `-` none. **Event categories** are the generator's own event families (— where the generator does not enumerate them). Scenarios counts the registered scenarios that emit the sourcetype; Dash validated counts those whose dashboard is validated against data; Dash implemented counts those whose dashboard is not yet validated; Visual counts those visually verified.

| Vendor | Product | Sourcetype | Kind | Event categories | Transport | Gen | Byte | Indexed | Scenarios | Dash validated | Dash implemented | Visual |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A10 Networks | A10 Acos Cgnat | `a10:acos:cgnat` | event | — | HEC (syslog format) | - | - | - | 0 | 0 | 0 | 0 |
| A10 Networks | A10 Acos Syslog | `a10:acos:syslog` | event | — | HEC (syslog format) | - | - | - | 0 | 0 | 0 | 0 |
| Amazon Web Services | AWS CloudFront Access Logs | `aws:cloudfront:accesslogs` | event | — | HEC (syslog format) | G | yes | yes | 6 | 6 | 0 | 1 |
| Amazon Web Services | AWS CloudTrail | `aws:cloudtrail` | event | — | HEC (hec_event format) | G | yes | yes | 6 | 6 | 0 | 1 |
| Amazon Web Services | AWS CloudTrail Lake (OCSF) | `aws:cloudtrail:lake` | event | — | HEC (hec_event format) | G | yes | yes | 6 | 6 | 0 | 1 |
| Amazon Web Services | AWS VPC Flow Logs (CloudWatch) | `aws:cloudwatchlogs:vpcflow` | event | — | HEC (hec_event format) | G | yes | yes | 4 | 4 | 0 | 1 |
| Arista Networks | Arista EOS Core Switching | `arista:eos` | event | — | HEC (syslog format) | R | - | - | 1 | 1 | 0 | 0 |
| Arista Networks | Arista Eos Syslog | `arista:eos:syslog` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Arista Networks | Arista Flow Ipfix | `arista:flow:ipfix` | event | — | HEC (syslog format) | G | - | - | 1 | 1 | 0 | 0 |
| Arista Networks | Arista Metrics Telemetry | `arista:telemetry:json` | event | — | HEC (syslog format) | R | - | - | 2 | 1 | 1 | 0 |
| Aruba / HPE | Aruba Instant AP & Switch Event | `aruba` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Aruba / HPE | Aruba Controller Authentication Manager | `aruba:authmgr` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Aruba / HPE | Aruba Cx Security | `aruba:cx:security` | event | — | HEC (syslog format) | - | - | - | 0 | 0 | 0 | 0 |
| Aruba / HPE | Aruba Cx Syslog | `aruba:cx:syslog` | event | — | HEC (syslog format) | - | - | - | 0 | 0 | 0 | 0 |
| Aruba / HPE | Aruba Station Management (STM) | `aruba:stm` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Aruba / HPE | Aruba Syslog | `aruba:syslog` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Atlassian | Confluence Cloud audit | `Confluence:audit log` | event | space_created, group_membership_added | HEC (hec format) | G | yes | yes | 3 | 3 | 0 | 0 |
| Barracuda Networks | Web Application Firewall | `barracuda:waf:web_firewall` | event | parameter_profile_violation, url_profile_violation | HEC (hec format) | G | yes | yes | 4 | 4 | 0 | 0 |
| BeyondTrust | Password Safe audit | `ccx:beyondinsight:passwordsafe` | event | secret_folder_added | HEC (hec format) | G | yes | yes | 5 | 5 | 0 | 1 |
| Bitdefender | GravityZone push notifications | `bitdefender:gz` | event | phishing_blocked, av_malware_detected, firewall_portscan_bl… | HEC (hec format) | G | yes | yes | 4 | 4 | 0 | 0 |
| Check Point Software | Checkpoint Cef | `checkpoint:cef` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Check Point Software | Checkpoint Firewall | `checkpoint:firewall` | event | — | HEC (syslog format) | - | - | - | 0 | 0 | 0 | 0 |
| Check Point Software | Checkpoint Threat | `checkpoint:threat` | event | — | HEC (syslog format) | - | - | - | 0 | 0 | 0 | 0 |
| Cisco Duo | Cisco Duo Account | `cisco:duo:account` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Cisco Duo | Cisco Duo Activity | `cisco:duo:activity` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Cisco Duo | Cisco Duo Administrator | `cisco:duo:administrator` | event | — | HEC (syslog format) | G | yes | yes | 6 | 6 | 0 | 1 |
| Cisco Duo | Cisco Duo Auth | `cisco:duo:auth` | event | — | HEC (syslog format) | - | - | - | 0 | 0 | 0 | 0 |
| Cisco Duo | Cisco Duo Authentication | `cisco:duo:authentication` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Cisco Duo | Cisco Duo Authentication V2 | `cisco:duo:authentication_v2` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Cisco Duo | Cisco Duo Endpoint | `cisco:duo:endpoint` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Cisco Duo | Cisco Duo Push Prompt | `cisco:duo:push:prompt` | event | — | HEC (syslog format) | - | - | - | 1 | 1 | 0 | 0 |
| Cisco Duo | Cisco Duo Remote Vpn | `cisco:duo:remote:vpn` | event | — | HEC (syslog format) | G | - | - | 2 | 1 | 1 | 0 |
| Cisco Duo | Cisco Duo User | `cisco:duo:user` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Cisco Meraki | Cisco Meraki Syslog | `cisco:meraki:syslog` | event | — | HEC (syslog format) | G | yes | yes | 1 | 1 | 0 | 0 |
| Cisco Meraki | Meraki Accesspoints | `meraki:accesspoints` | event | — | HEC (syslog format) | R | - | - | 2 | 1 | 1 | 0 |
| Cisco Meraki | Meraki Airmarshal | `meraki:airmarshal` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Cisco Meraki | Meraki Appliance | `meraki:appliance` | event | — | HEC (syslog format) | - | - | - | 0 | 0 | 0 | 0 |
| Cisco Meraki | Meraki Appliancesdwanstatistics | `meraki:appliancesdwanstatistics` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Cisco Meraki | Meraki Appliancesdwanstatuses | `meraki:appliancesdwanstatuses` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Cisco Meraki | Meraki Assurancealerts | `meraki:assurancealerts` | event | — | HEC (syslog format) | G | - | - | 2 | 1 | 1 | 0 |
| Cisco Meraki | Meraki Devices | `meraki:devices` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Cisco Meraki | Meraki Devices Availabilities | `meraki:devicesavailabilitieschangehistory` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Cisco Meraki | Meraki Organizationsecurity | `meraki:organizationsecurity` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Cisco Meraki | Meraki Security | `meraki:security` | event | — | HEC (syslog format) | - | - | - | 0 | 0 | 0 | 0 |
| Cisco Meraki | Meraki Securityappliances | `meraki:securityappliances` | event | — | HEC (syslog format) | - | - | - | 0 | 0 | 0 | 0 |
| Cisco Meraki | Meraki Summarytopappliancesbyutilization | `meraki:summarytopappliancesbyutilization` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Cisco Meraki | Meraki Summarytopclientsbyusage | `meraki:summarytopclientsbyusage` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Cisco Meraki | Meraki Summarytopdevicesbyusage | `meraki:summarytopdevicesbyusage` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Cisco Meraki | Meraki Switchportsbyswitch | `meraki:switchportsbyswitch` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Cisco Meraki | Meraki Switchportsoverview | `meraki:switchportsoverview` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Cisco Systems | Cisco Aci Fault | `cisco:aci:fault` | event | — | HEC (syslog format) | - | - | - | 0 | 0 | 0 | 0 |
| Cisco Systems | Cisco Aci Syslog | `cisco:aci:syslog` | event | — | HEC (syslog format) | - | - | - | 0 | 0 | 0 | 0 |
| Cisco Systems | Cisco ASA Firewall Connection & Policy | `cisco:asa` | event | — | HEC (syslog format) | G | - | - | 5 | 3 | 2 | 0 |
| Cisco Systems | Cisco ASA Syslog Message Stream | `cisco:asa:syslog` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Cisco Systems | Cisco Catalyst Client | `cisco:catalyst:client` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Cisco Systems | Cisco Catalyst Clienthealth | `cisco:catalyst:clienthealth` | event | — | HEC (syslog format) | G | - | - | 4 | 1 | 3 | 0 |
| Cisco Systems | Cisco Catalyst Compliance | `cisco:catalyst:compliance` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Cisco Systems | Cisco Catalyst Devicehealth | `cisco:catalyst:devicehealth` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Cisco Systems | Cisco Catalyst Issue | `cisco:catalyst:issue` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Cisco Systems | Cisco Catalyst Networkhealth | `cisco:catalyst:networkhealth` | event | — | HEC (syslog format) | R | - | - | 2 | 0 | 2 | 0 |
| Cisco Systems | Cisco Catalyst Rogue Allowed | `cisco:catalyst:rogue:allowed` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Cisco Systems | Cisco Catalyst Rogue Counts | `cisco:catalyst:rogue:counts` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Cisco Systems | Cisco Catalyst Rogue Threat Details | `cisco:catalyst:rogue:threat_details` | event | — | HEC (syslog format) | G | - | - | 4 | 2 | 2 | 0 |
| Cisco Systems | Cisco Catalyst Rogue Verbose | `cisco:catalyst:rogue:verbose` | event | captured_1, captured_2 | HEC (syslog format) | G | yes | yes | 3 | 3 | 0 | 0 |
| Cisco Systems | Cisco Catalyst Rogue Verbose Legacy | `cisco:catalyst:rogue:verbose:legacy` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Cisco Systems | Cisco Catalyst Rogue Wired | `cisco:catalyst:rogue:wired` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Cisco Systems | Cisco Catalyst Script Heartbeat | `cisco:catalyst:script:heartbeat` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Cisco Systems | Cisco Catalyst Security Awips Signatures | `cisco:catalyst:security:awips_signatures` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Cisco Systems | Cisco Catalyst Security Events | `cisco:catalyst:security:events` | event | — | HEC (syslog format) | G | - | yes | 4 | 4 | 0 | 0 |
| Cisco Systems | Cisco Catalyst Security Profile | `cisco:catalyst:security:profile` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Cisco Systems | Cisco Catalyst Security Profile Signatu… | `cisco:catalyst:security:profile_signatures` | event | captured_1 | HEC (syslog format) | G | yes | yes | 3 | 3 | 0 | 0 |
| Cisco Systems | Cisco Catalyst Security Rules | `cisco:catalyst:security:rules` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Cisco Systems | Cisco Catalyst Securityadvisory | `cisco:catalyst:securityadvisory` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Cisco Systems | Cisco Catalyst Syslog | `cisco:catalyst:syslog` | event | — | HEC (syslog format) | - | - | - | 0 | 0 | 0 | 0 |
| Cisco Systems | Cisco Catalyst Threat List | `cisco:catalyst:threat:list` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Cisco Systems | Cisco Catalyst Threat Signatures | `cisco:catalyst:threat:signatures` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Cisco Systems | Cisco Catalyst Threat Summary | `cisco:catalyst:threat:summary` | event | captured_1, captured_2 | HEC (syslog format) | G | yes | yes | 3 | 3 | 0 | 0 |
| Cisco Systems | Cisco Catalyst Threat Summary Legacy | `cisco:catalyst:threat:summary:legacy` | event | captured_1, captured_2 | HEC (syslog format) | G | yes | yes | 3 | 3 | 0 | 0 |
| Cisco Systems | Cisco Cloud Security DNS | `cisco:cloud_security:dns` | event | — | HEC (syslog format) | G | yes | yes | 3 | 3 | 0 | 0 |
| Cisco Systems | Cisco Cloud Security Firewall | `cisco:cloud_security:firewall` | event | — | HEC (syslog format) | G | yes | yes | 3 | 3 | 0 | 0 |
| Cisco Systems | Cisco Cloud Security Web Proxy | `cisco:cloud_security:proxy` | event | — | HEC (syslog format) | G | yes | yes | 3 | 3 | 0 | 0 |
| Cisco Systems | Cisco Dc Aci Class | `cisco:dc:aci:class` | event | captured_1 | HEC (syslog format) | G | yes | yes | 0 | 0 | 0 | 0 |
| Cisco Systems | Cisco ACI Fabric State Events | `cisco:dc:aci:events` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Cisco Systems | Cisco Dc Aci Bridge Domain | `cisco:dc:aci:health` | event | — | HEC (syslog format) | G | - | yes | 3 | 1 | 2 | 1 |
| Cisco Systems | Cisco Dc Nexus9K | `cisco:dc:nexus9k` | event | captured_1, captured_2 | HEC (syslog format) | G | yes | yes | 0 | 0 | 0 | 0 |
| Cisco Systems | Cisco Dc Nexus9K Syslog | `cisco:dc:nexus9k:syslog` | event | — | HEC (syslog format) | G | - | yes | 5 | 2 | 3 | 1 |
| Cisco Systems | Cisco Dnac Audit Logs | `cisco:dnac:audit:logs` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Cisco Systems | Cisco Dnac Client | `cisco:dnac:client` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Cisco Systems | Cisco Dnac Clienthealth | `cisco:dnac:clienthealth` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Cisco Systems | Cisco Dnac Compliance | `cisco:dnac:compliance` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Cisco Systems | Cisco Dnac Devicehealth | `cisco:dnac:devicehealth` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Cisco Systems | Cisco Dnac Issue | `cisco:dnac:issue` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Cisco Systems | Cisco Dnac Networkhealth | `cisco:dnac:networkhealth` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Cisco Systems | Cisco Dnac Securityadvisory | `cisco:dnac:securityadvisory` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Cisco Systems | Cisco Dnac Site Topology | `cisco:dnac:site:topology` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Cisco Systems | Cisco Ftd Syslog | `cisco:ftd:syslog` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Cisco Systems | Cisco Intersight Advisories | `cisco:intersight:advisories` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Cisco Systems | Cisco Intersight Alarms | `cisco:intersight:alarms` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Cisco Systems | Cisco Intersight Auditrecords | `cisco:intersight:auditrecords` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Cisco Systems | Cisco Intersight Compute | `cisco:intersight:compute` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Cisco Systems | Cisco Intersight Contracts | `cisco:intersight:contracts` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Cisco Systems | Cisco Intersight Licenses | `cisco:intersight:licenses` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Cisco Systems | Cisco Intersight Metrics | `cisco:intersight:metrics` | metric | — | HEC (hec format) | R | - | - | 0 | 0 | 0 | 0 |
| Cisco Systems | Cisco Intersight Networkelements | `cisco:intersight:networkelements` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Cisco Systems | Cisco Intersight Networkobjects | `cisco:intersight:networkobjects` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Cisco Systems | Cisco Intersight Profiles | `cisco:intersight:profiles` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Cisco Systems | Cisco Intersight Targets | `cisco:intersight:targets` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Cisco Systems | Cisco Ios | `cisco:ios` | event | — | HEC (syslog format) | G | yes | yes | 1 | 1 | 0 | 0 |
| Cisco Systems | Cisco Ios Mdt | `cisco:ios:mdt` | event | — | HEC (syslog format) | G | - | yes | 2 | 2 | 0 | 1 |
| Cisco Systems | Cisco IOS-XE / IOS-XR Model-Driven Tele… | `cisco:ios:mdt:metric` | metric | — | HEC (hec format) | G | - | - | 4 | 1 | 3 | 0 |
| Cisco Systems | Cisco IOS System Syslog Facility | `cisco:ios:syslog` | event | — | HEC (syslog format) | G | - | - | 18 | 4 | 14 | 0 |
| Cisco Systems | Cisco Ise Nac 8021X | `cisco:ise:nac:8021x` | event | — | HEC (syslog format) | - | - | - | 1 | 1 | 0 | 0 |
| Cisco Systems | Cisco Ise Radius Authz Policy | `cisco:ise:radius:authz:policy` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Cisco Systems | Cisco Ise Radius Policyset | `cisco:ise:radius:policyset` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Cisco Systems | Cisco Ise Syslog | `cisco:ise:syslog` | event | — | HEC (syslog format) | G | - | - | 7 | 1 | 6 | 0 |
| Cisco Systems | Cisco Ise Tacacs Authz Policy | `cisco:ise:tacacs:authz:policy` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Cisco Systems | Cisco Ise Tacacs Policyset | `cisco:ise:tacacs:policyset` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Cisco Systems | Cisco Ise Trustsec Sgt | `cisco:ise:trustsec:sgt` | event | — | HEC (syslog format) | - | - | - | 0 | 0 | 0 | 0 |
| Cisco Systems | Cisco Isovalent Cilium Events | `cisco:isovalent` | event | — | HEC (hec_event format) | G | yes | yes | 3 | 3 | 0 | 0 |
| Cisco Systems | Cisco Isovalent Cilium processConnect | `cisco:isovalent:processConnect` | event | — | HEC (hec_event format) | G | yes | yes | 3 | 3 | 0 | 0 |
| Cisco Systems | Cisco Isovalent Cilium processExec | `cisco:isovalent:processExec` | event | — | HEC (hec_event format) | G | yes | yes | 3 | 3 | 0 | 0 |
| Cisco Systems | Cisco Mds San Fc | `cisco:mds:san:fc` | event | — | HEC (syslog format) | - | - | - | 0 | 0 | 0 | 0 |
| Cisco Systems | Cisco Metrics Splunk Otel | `cisco:metrics` | metric | — | HEC (hec format) | R | - | - | 0 | 0 | 0 | 0 |
| Cisco Systems | Cisco Nexus DC Switch Event | `cisco:nexus` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Cisco Systems | Cisco Nvm Flowdata | `cisco:nvm:flowdata` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Cisco Systems | Cisco NVM Flow Data v2 | `cisco:nvm:flowdata:v2` | event | — | HEC (hec_event format) | G | yes | yes | 1 | 1 | 0 | 0 |
| Cisco Systems | Cisco NX-OS Structured Event Stream | `cisco:nxos` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Cisco Systems | Cisco NX-OS Syslog Event | `cisco:nxos:syslog` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Cisco Systems | Cisco Sdwan Aaa 6 Method List State | `cisco:sdwan:AAA-6-METHOD_LIST_STATE` | event | dead, alive | HEC (syslog format) | G | yes | yes | 2 | 2 | 0 | 0 |
| Cisco Systems | Cisco Sdwan Aaa 6 Notify Mlist State To… | `cisco:sdwan:AAA-6-NOTIFY_MLIST_STATE_TO_AAA_CLIENT` | event | dead, alive | HEC (syslog format) | G | yes | yes | 2 | 2 | 0 | 0 |
| Cisco Systems | Cisco Sdwan Aaa Audit Message 6 Method … | `cisco:sdwan:AAA_AUDIT_MESSAGE-6-METHOD_LIST_STATE` | event | captured_1 | HEC (syslog format) | G | yes | yes | 2 | 2 | 0 | 0 |
| Cisco Systems | Cisco Sdwan Aaa Audit Message 6 Notify … | `cisco:sdwan:AAA_AUDIT_MESSAGE-6-NOTIFY_MLIST_STATE_TO_AAA_CLIENT` | event | captured_1 | HEC (syslog format) | G | yes | yes | 2 | 2 | 0 | 0 |
| Cisco Systems | Cisco Sdwan Bgp 5 Adjchange | `cisco:sdwan:BGP-5-ADJCHANGE` | event | vrf_down, up | HEC (syslog format) | G | yes | yes | 8 | 5 | 3 | 1 |
| Cisco Systems | Cisco Sdwan Bgp 5 Nbr Reset | `cisco:sdwan:BGP-5-NBR_RESET` | event | peer_closed | HEC (syslog format) | G | yes | yes | 4 | 4 | 0 | 1 |
| Cisco Systems | Cisco Sdwan Bgp 6 Nexthop | `cisco:sdwan:BGP-6-NEXTHOP` | event | captured_1 | HEC (syslog format) | G | yes | yes | 0 | 0 | 0 | 0 |
| Cisco Systems | Cisco Sdwan Bgp Session 5 Adjchange | `cisco:sdwan:BGP_SESSION-5-ADJCHANGE` | event | captured_1, captured_2 | HEC (syslog format) | G | yes | yes | 0 | 0 | 0 | 0 |
| Cisco Systems | Cisco Sdwan Cdp 4 Native Vlan Mismatch | `cisco:sdwan:CDP-4-NATIVE_VLAN_MISMATCH` | event | vlan_mismatch | HEC (syslog format) | G | yes | yes | 4 | 4 | 0 | 1 |
| Cisco Systems | Cisco Sdwan Crypto 6 Isakmp On Off | `cisco:sdwan:CRYPTO-6-ISAKMP_ON_OFF` | event | captured_1 | HEC (syslog format) | G | yes | yes | 0 | 0 | 0 | 0 |
| Cisco Systems | Cisco Sdwan Cts 3 Aaa No Radius Server | `cisco:sdwan:CTS-3-AAA_NO_RADIUS_SERVER` | event | captured_1 | HEC (syslog format) | G | yes | yes | 2 | 2 | 0 | 0 |
| Cisco Systems | Cisco Sdwan Dmi 5 Auth Passed | `cisco:sdwan:DMI-5-AUTH_PASSED` | event | captured_1 | HEC (syslog format) | G | yes | yes | 0 | 0 | 0 | 0 |
| Cisco Systems | Cisco Sdwan Dmi 5 Config I | `cisco:sdwan:DMI-5-CONFIG_I` | event | captured_1 | HEC (syslog format) | G | yes | yes | 0 | 0 | 0 | 0 |
| Cisco Systems | Cisco Sdwan Dmi 5 Sync Complete | `cisco:sdwan:DMI-5-SYNC_COMPLETE` | event | captured_1 | HEC (syslog format) | G | yes | yes | 4 | 4 | 0 | 1 |
| Cisco Systems | Cisco Sdwan Dmi 5 Sync Needed | `cisco:sdwan:DMI-5-SYNC_NEEDED` | event | sync_needed | HEC (syslog format) | G | yes | yes | 4 | 4 | 0 | 1 |
| Cisco Systems | Cisco Sdwan Dmi 5 Sync Start | `cisco:sdwan:DMI-5-SYNC_START` | event | captured_1 | HEC (syslog format) | G | yes | yes | 4 | 4 | 0 | 1 |
| Cisco Systems | Cisco Sdwan Environmental 1 Alert | `cisco:sdwan:ENVIRONMENTAL-1-ALERT` | event | temperature | HEC (syslog format) | G | yes | yes | 4 | 4 | 0 | 0 |
| Cisco Systems | Cisco Sdwan Eventlib 3 Cpuhog | `cisco:sdwan:EVENTLIB-3-CPUHOG` | event | captured_1, captured_2 | HEC (syslog format) | G | yes | yes | 4 | 4 | 0 | 0 |
| Cisco Systems | Cisco Sdwan Iosxe 3 Platform | `cisco:sdwan:IOSXE-3-PLATFORM` | event | captured_1, captured_2 | HEC (syslog format) | G | yes | yes | 4 | 4 | 0 | 0 |
| Cisco Systems | Cisco Sdwan Iosxe Infra 4 No Punt Keepa… | `cisco:sdwan:IOSXE_INFRA-4-NO_PUNT_KEEPALIVE` | event | captured_1 | HEC (syslog format) | G | yes | yes | 4 | 4 | 0 | 0 |
| Cisco Systems | Cisco Sdwan Iosxe Rp Pae Not 6 Pae Star… | `cisco:sdwan:IOSXE_RP_PAE_NOT-6-PAE_STARTUP` | event | captured_1 | HEC (syslog format) | G | yes | yes | 0 | 0 | 0 | 0 |
| Cisco Systems | Cisco Sdwan Lineproto 5 Updown | `cisco:sdwan:LINEPROTO-5-UPDOWN` | event | line_protocol | HEC (syslog format) | G | yes | yes | 4 | 4 | 0 | 1 |
| Cisco Systems | Cisco Sdwan Link 5 Changed | `cisco:sdwan:LINK-5-CHANGED` | event | admin_down | HEC (syslog format) | G | yes | yes | 4 | 4 | 0 | 1 |
| Cisco Systems | Cisco Sdwan Link 5 Updown | `cisco:sdwan:LINK-5-UPDOWN` | event | link_state | HEC (syslog format) | G | yes | yes | 4 | 4 | 0 | 1 |
| Cisco Systems | Cisco Sdwan Mdt Connection 6 State Chan… | `cisco:sdwan:MDT_CONNECTION-6-STATE_CHANGED` | event | connection_state | HEC (syslog format) | G | yes | yes | 4 | 4 | 0 | 0 |
| Cisco Systems | Cisco Sdwan Msdp 5 Peer Updown | `cisco:sdwan:MSDP-5-PEER_UPDOWN` | event | peer_state | HEC (syslog format) | G | yes | yes | 4 | 4 | 0 | 1 |
| Cisco Systems | Cisco Sdwan Ndbman 5 Config I | `cisco:sdwan:NDBMAN-5-CONFIG_I` | event | captured_1, captured_2 | HEC (syslog format) | G | yes | yes | 4 | 4 | 0 | 1 |
| Cisco Systems | Cisco Sdwan Ospf 5 Adjchg | `cisco:sdwan:OSPF-5-ADJCHG` | event | adjacency | HEC (syslog format) | G | yes | yes | 4 | 4 | 0 | 1 |
| Cisco Systems | Cisco Sdwan Pki 6 Authoritative Clock | `cisco:sdwan:PKI-6-AUTHORITATIVE_CLOCK` | event | captured_1 | HEC (syslog format) | G | yes | yes | 4 | 4 | 0 | 0 |
| Cisco Systems | Cisco Sdwan Platform 4 Element Warning | `cisco:sdwan:PLATFORM-4-ELEMENT_WARNING` | event | load_average | HEC (syslog format) | G | yes | yes | 4 | 4 | 0 | 0 |
| Cisco Systems | Cisco Sdwan Sys 5 Config P | `cisco:sdwan:SYS-5-CONFIG_P` | event | captured_1 | HEC (syslog format) | G | yes | yes | 0 | 0 | 0 | 0 |
| Cisco Systems | Cisco SD-WAN Management Access | `cisco:sdwan:access` | event | — | HEC (syslog format) | G | yes | yes | 1 | 1 | 0 | 0 |
| Cisco Systems | Cisco Sdwan Linkhealth | `cisco:sdwan:linkhealth` | event | — | HEC (syslog format) | G | - | - | 7 | 1 | 6 | 0 |
| Cisco Systems | Cisco Sdwan Sitehealth | `cisco:sdwan:sitehealth` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Cisco Systems | Cisco Sdwan Ssetunnels | `cisco:sdwan:ssetunnels` | event | captured_1, captured_2 | HEC (syslog format) | G | yes | yes | 2 | 2 | 0 | 1 |
| Cisco Systems | Cisco Sdwan Syslog | `cisco:sdwan:syslog` | event | — | HEC (syslog format) | G | yes | yes | 1 | 1 | 0 | 0 |
| Cisco Systems | Cisco Sdwan System Logs | `cisco:sdwan:system:logs` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Cisco Systems | Cisco Sdwan Sytem Logs | `cisco:sdwan:sytem:logs` | event | captured_1, captured_2 | HEC (syslog format) | G | yes | yes | 0 | 0 | 0 | 0 |
| Cisco Systems | Cisco Sdwan Tunnelhealth | `cisco:sdwan:tunnelhealth` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Cisco Systems | Cisco Sdwan Utd Logs | `cisco:sdwan:utd:logs` | event | captured_1, captured_2 | HEC (syslog format) | G | yes | yes | 2 | 2 | 0 | 1 |
| Cisco Systems | Cisco Sdwan Utdhealth | `cisco:sdwan:utdhealth` | event | captured_1, captured_2 | HEC (syslog format) | G | yes | yes | 2 | 2 | 0 | 1 |
| Cisco Systems | Cisco Se | `cisco:se` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Cisco Systems | Cisco Secure Access RA-VPN Events | `cisco:secure_access:security_events_ravpn` | event | — | HEC (hec_event format) | G | yes | yes | 6 | 6 | 0 | 1 |
| Cisco Systems | Cisco Sfw Estreamer | `cisco:sfw:estreamer` | event | — | HEC (syslog format) | G | yes | yes | 1 | 1 | 0 | 0 |
| Cisco Systems | Cisco Sfw Policy | `cisco:sfw:policy` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Cisco Systems | Cisco Thousandeyes Event | `cisco:thousandeyes:event` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Cisco Systems | Cisco Thousandeyes Metric | `cisco:thousandeyes:metric` | metric | — | HEC (hec format) | G | - | - | 6 | 2 | 4 | 0 |
| Cisco Systems | Cisco Thousandeyes Path Vis | `cisco:thousandeyes:path-vis` | event | — | HEC (syslog format) | R | - | - | 1 | 1 | 0 | 0 |
| Cisco Systems | Cisco Syslog | `cisco_syslog` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Cisco Systems | NetSpout Ingestion Preflight Probe | `datablaster:preflight` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Cisco Systems | NetSpout Telemetry Canary Probe | `datablaster:probe` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Cisco Systems | NetSpout Native SNMPv2c Polling Events | `netspout:snmp:poll` | event | — | HEC (snmp format) | G | - | - | 1 | 1 | 0 | 0 |
| Cisco Systems | NetSpout Native SNMPv2c Traps & Informs | `netspout:snmp:trap` | event | — | HEC (snmp format) | G | - | - | 1 | 1 | 0 | 0 |
| Cisco Systems | Openconfig Gnmi Telemetry | `openconfig:gnmi:telemetry` | event | — | HEC (syslog format) | - | - | - | 0 | 0 | 0 | 0 |
| Cisco Systems | Opsec | `opsec` | event | — | HEC (syslog format) | - | - | - | 0 | 0 | 0 | 0 |
| Citrix / Cloud Software Group | Citrix Netscaler Syslog | `citrix:netscaler:syslog` | event | — | HEC (syslog format) | - | - | - | 0 | 0 | 0 | 0 |
| Citrix / Cloud Software Group | Citrix Netscaler Web | `citrix:netscaler:web` | event | — | HEC (syslog format) | - | - | - | 0 | 0 | 0 | 0 |
| Claroty | CTD CEF | `claroty:cef` | event | new_asset, asset_information_change, health | HEC (hec format) | G | yes | yes | 5 | 5 | 0 | 0 |
| Cloudflare | Cloudflare Firewall | `cloudflare:firewall` | event | — | HEC (syslog format) | - | - | - | 0 | 0 | 0 | 0 |
| Cloudflare | Cloudflare Json | `cloudflare:json` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Cloudflare | Cloudflare R2 Metrics | `cloudflare:r2:json` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| CrowdStrike | CrowdStrike Falcon Sensor Events | `crowdstrike:events:sensor` | event | — | HEC (hec_event format) | G | yes | yes | 4 | 4 | 0 | 0 |
| CrushFTP | CrushFTP Session Logs | `crushftp:sessionlogs` | event | — | HEC (syslog_rfc3164 format) | G | yes | yes | 2 | 2 | 0 | 0 |
| Cybereason | Malops feed | `cybereason:malops` | event | malop_process_injection | HEC (hec format) | G | yes | yes | 4 | 4 | 0 | 0 |
| Darktrace | Model breach alerts | `darktrace` | event | uncommon_outbound_model, antigena_internal_transfer | HEC (hec format) | G | yes | yes | 4 | 4 | 0 | 0 |
| Dell Technologies | Dell Os10 Syslog | `dell:os10:syslog` | event | — | HEC (syslog format) | - | - | - | 0 | 0 | 0 | 0 |
| Docker | Docker Engine Events | `docker_events` | event | container_lifecycle, network_connect | HEC (hec format) | G | yes | yes | 3 | 3 | 0 | 0 |
| Elastic | Elasticsearch server logs | `elasticsearch:json` | event | data_stream_provisioning, shard_bootstrapping | HEC (hec format) | G | yes | yes | 5 | 5 | 0 | 0 |
| ExtraHop Networks | Extrahop Eda Alert | `extrahop:eda:alert` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| ExtraHop Networks | Extrahop Metrics Performance | `extrahop:eda:metrics` | metric | — | HEC (hec format) | R | - | - | 0 | 0 | 0 | 0 |
| Extreme Networks | Extreme Exos Syslog | `extreme:exos:syslog` | event | — | HEC (syslog format) | - | - | - | 0 | 0 | 0 | 0 |
| Extreme Networks | Extreme Voss Syslog | `extreme:voss:syslog` | event | — | HEC (syslog format) | - | - | - | 0 | 0 | 0 | 0 |
| F5 Networks | F5 BIG-IP Local Traffic Manager (LTM) | `f5:bigip:ltm` | event | — | HEC (syslog format) | G | - | - | 3 | 2 | 1 | 0 |
| F5 Networks | F5 Bigip Syslog | `f5:bigip:syslog` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Forcepoint | Forcepoint Ngfw Alert | `forcepoint:ngfw:alert` | event | — | HEC (syslog format) | - | - | - | 0 | 0 | 0 | 0 |
| Forcepoint | Forcepoint Ngfw Traffic | `forcepoint:ngfw:traffic` | event | — | HEC (syslog format) | - | - | - | 0 | 0 | 0 | 0 |
| Fortinet | Fortinet Fortigate Sdwan Alert | `fgt_event` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Fortinet | Fortinet Fortigate Traffic | `fgt_traffic` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Fortinet | Fortinet FortiGate System Event | `fortigate_event` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Fortinet | Fortinet FortiGate Traffic Log | `fortigate_traffic` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Fortinet | Fortinet FortiGate Unified Security Eve… | `fortinet:fortigate` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Fortinet | Fortinet Fortigate Event | `fortinet:fortigate:event` | event | — | HEC (syslog format) | - | - | - | 0 | 0 | 0 | 0 |
| Fortinet | Fortinet Fortigate Traffic | `fortinet:fortigate:traffic` | event | — | HEC (syslog format) | - | - | - | 0 | 0 | 0 | 0 |
| Fortinet | Fortinet Fortigate Utm | `fortinet:fortigate:utm` | event | — | HEC (syslog format) | G | - | - | 2 | 1 | 1 | 0 |
| GitHub | Enterprise audit logs | `github:enterprise:audit` | event | enterprise_user_login, repository_merge | HEC (hec format) | G | yes | yes | 5 | 5 | 0 | 0 |
| GitLab | Self-Managed audit events | `gitlab:audit:json` | event | session_login, git_operation | HEC (hec format) | G | yes | yes | 5 | 5 | 0 | 0 |
| Google Cloud | Google Cloud Audit Logs | `gcp:audit` | event | — | HEC (hec_event format) | G | yes | yes | 3 | 3 | 0 | 0 |
| Google Workspace | Gmail BigQuery Message Export | `gsuite:gmail:bigquery` | event | — | HEC (hec_event format) | G | yes | yes | 6 | 6 | 0 | 1 |
| Google Workspace | Google Workspace Login Reports | `gws:reports:login` | event | — | HEC (hec_event format) | G | yes | yes | 6 | 6 | 0 | 1 |
| HashiCorp | Vault audit | `hashicorp_vault_audit_log` | event | audit_request, audit_response | HEC (hec format) | G | yes | yes | 3 | 3 | 0 | 0 |
| Huawei Technologies | Huawei Vrp Syslog | `huawei:vrp:syslog` | event | — | HEC (syslog format) | - | - | - | 0 | 0 | 0 | 0 |
| Huawei Technologies | Huawei Vrp Traffic | `huawei:vrp:traffic` | event | — | HEC (syslog format) | - | - | - | 0 | 0 | 0 | 0 |
| IBM | QRadar offense events | `ibm:qradar:offense` | event | generic_log_offense, message_offense, authentication_offense | HEC (hec format) | G | yes | yes | 5 | 5 | 0 | 0 |
| IBM MQ | IBM MQ native error log | `ibm:mq:errorlog` | event | queue_manager_created, control_command_issued | HEC (hec format) | G | yes | yes | 2 | 2 | 0 | 0 |
| Imperva | SecureSphere CEF | `imperva:securesphere:cef` | event | administrator_login, database_audit | HEC (hec format) | G | yes | yes | 4 | 4 | 0 | 0 |
| Juniper Networks | Juniper Junos Routing & System Log | `juniper:junos` | event | — | HEC (syslog format) | G | - | - | 4 | 2 | 2 | 0 |
| Juniper Networks | Juniper Junos Syslog Transport | `juniper:junos:syslog` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Juniper Networks | Juniper Syslog | `juniper:syslog` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Kubernetes & Falco (CNCF) | Kubernetes Audit Log | `kube:audit` | event | — | HEC (hec_event format) | G | yes | yes | 2 | 2 | 0 | 0 |
| Kubernetes & Falco (CNCF) | Falco Runtime Security Events | `kube:container:falco` | event | — | HEC (hec_event format) | G | yes | yes | 2 | 2 | 0 | 0 |
| Linux Infrastructure | Linux auditd Records | `auditd` | event | — | HEC (syslog_rfc3164 format) | G | yes | yes | 3 | 3 | 0 | 0 |
| Linux Infrastructure | ISC dhcpd Lease Events | `dhcpd` | event | — | HEC (syslog format) | G | yes | yes | 1 | 1 | 0 | 0 |
| Linux Infrastructure | Linux /var/log/messages | `linux_messages_syslog` | event | — | HEC (syslog_rfc3164 format) | G | yes | yes | 3 | 3 | 0 | 0 |
| Linux Infrastructure | Linux /var/log/secure | `linux_secure` | event | — | HEC (syslog format) | G | yes | yes | 1 | 1 | 0 | 0 |
| Microsoft 365 | MS Exchange Management Audit | `MSExchange:Management` | event | — | HEC (syslog format) | G | yes | yes | 1 | 1 | 0 | 0 |
| Microsoft 365 | M365 Graph Message Trace | `o365:graph:messagetrace` | event | — | HEC (hec_event format) | G | yes | yes | 6 | 6 | 0 | 1 |
| Microsoft 365 | Microsoft 365 Management Activity | `o365:management:activity` | event | — | HEC (hec_event format) | G | yes | yes | 6 | 6 | 0 | 1 |
| Microsoft 365 | M365 Reporting Message Trace | `o365:reporting:messagetrace` | event | — | HEC (hec_event format) | G | yes | yes | 6 | 6 | 0 | 1 |
| Microsoft Azure Monitor | Microsoft Entra ID (Azure AD) Monitor | `azure:monitor:aad` | event | — | HEC (hec_event format) | G | yes | yes | 6 | 6 | 0 | 1 |
| Microsoft Azure Monitor | Azure Activity Log | `azure:monitor:activity` | event | — | HEC (hec_event format) | G | yes | yes | 6 | 6 | 0 | 1 |
| Microsoft Windows | Windows NTLM Operational XML | `XmlWinEventLog:Microsoft-Windows-NTLM/Operational` | event | — | HEC (hec_event format) | G | yes | yes | 3 | 3 | 0 | 0 |
| Microsoft Windows | Windows PowerShell Operational XML | `XmlWinEventLog:Microsoft-Windows-PowerShell/Operational` | event | — | HEC (hec_event format) | G | yes | yes | 3 | 3 | 0 | 0 |
| Microsoft Windows | Windows Sysmon XML | `XmlWinEventLog:Microsoft-Windows-Sysmon/Operational` | event | — | HEC (hec_event format) | G | yes | yes | 3 | 3 | 0 | 0 |
| Microsoft Windows | Windows Defender Operational XML | `XmlWinEventLog:Microsoft-Windows-Windows Defender/Operational` | event | — | HEC (hec_event format) | G | yes | yes | 3 | 3 | 0 | 0 |
| Microsoft Windows | Windows Security Audit XML | `XmlWinEventLog:Security` | event | — | HEC (hec_event format) | G | yes | yes | 3 | 3 | 0 | 0 |
| Microsoft Windows | Windows System Channel XML | `XmlWinEventLog:System` | event | — | HEC (hec format) | G | yes | yes | 1 | 1 | 0 | 0 |
| Microsoft Windows | Microsoft IIS W3C Access | `iis` | event | — | HEC (syslog format) | G | yes | yes | 1 | 1 | 0 | 0 |
| Microsoft Windows | Sysmon for Linux | `sysmon:linux` | event | — | HEC (hec_event format) | G | yes | yes | 3 | 3 | 0 | 0 |
| MikroTik | RouterOS console log | `mikrotik:routeros` | event | administrator_login, ospf_hello_sent | HEC (hec format) | G | yes | yes | 5 | 5 | 0 | 0 |
| Model Context Protocol (agent… | Model Context Protocol JSON-RPC | `mcp:jsonrpc` | event | — | HEC (hec_event format) | G | yes | yes | 2 | 2 | 0 | 0 |
| MongoDB | MongoDB structured server log | `mongodb:log` | event | server_start, index_build | HEC (hec format) | G | yes | yes | 3 | 3 | 0 | 0 |
| NetScout Systems | Netscout Omnis Alert | `netscout:omnis:alert` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Netskope | Netskope Alerts | `netskope:alerts` | event | — | HEC (syslog format) | - | - | - | 0 | 0 | 0 | 0 |
| Netskope | Netskope Events | `netskope:events` | event | — | HEC (syslog format) | - | - | - | 0 | 0 | 0 | 0 |
| Netskope | Netskope Json | `netskope:json` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Netskope | Netskope Security Service Edge (SSE) | `netskope:sse` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| NGINX (F5) | NGINX combined access log | `nginx:access` | event | http_access | HEC (hec format) | G | yes | yes | 6 | 6 | 0 | 0 |
| NGINX (F5) | NGINX Plus access (key=value) | `nginx:plus:access` | event | captured_1, captured_2, captured_3, captured_4, captured_5 | HEC (hec format) | G | yes | yes | 0 | 0 | 0 | 0 |
| Nokia | Nokia Sr Syslog | `nokia:sr:syslog` | event | — | HEC (syslog format) | - | - | - | 0 | 0 | 0 | 0 |
| Nokia | Nokia 7750 SR OS Service Router Event | `nokia:sros` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Nokia | Nokia 7750 SR OS Syslog Facility | `nokia:sros:syslog` | event | — | HEC (syslog format) | G | - | - | 3 | 2 | 1 | 0 |
| Nozomi Networks | Nozomi Networks Universal Alert | `nozomi:universal_alert` | event | ot_ids_program_change | HEC (syslog format) | G | yes | yes | 3 | 3 | 0 | 0 |
| Nutanix | Nutanixpc Disks | `nutanixPC_disks` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Nutanix | Nutanix Prism Central Syslog (Colon For… | `nutanixpc:syslog` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Nutanix | Nutanix Prism Central VM Inventory (Col… | `nutanixpc:vms` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Nutanix | Nutanixpc Alerts | `nutanixpc_alerts` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Nutanix | Nutanixpc Cluster Performance | `nutanixpc_cluster_performance` | metric | — | HEC (hec format) | R | - | - | 0 | 0 | 0 | 0 |
| Nutanix | Nutanixpc Clusters | `nutanixpc_clusters` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Nutanix | Nutanixpc Disk Performance | `nutanixpc_disk_performance` | metric | — | HEC (hec format) | R | - | - | 0 | 0 | 0 | 0 |
| Nutanix | Nutanixpc Events | `nutanixpc_events` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Nutanix | Nutanixpc Host Performance | `nutanixpc_host_performance` | metric | — | HEC (hec format) | R | - | - | 0 | 0 | 0 | 0 |
| Nutanix | Nutanixpc Hosts | `nutanixpc_hosts` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Nutanix | Nutanixpc Prismcentrals | `nutanixpc_prismCentrals` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Nutanix | Nutanixpc Storage Containers | `nutanixpc_storage_containers` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Nutanix | Nutanixpc Syslog | `nutanixpc_syslog` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Nutanix | Nutanixpc Vm Performance | `nutanixpc_vm_performance` | metric | — | HEC (hec format) | R | - | - | 0 | 0 | 0 | 0 |
| Nutanix | Nutanixpc Vms | `nutanixpc_vms` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Nutanix | Nutanixpc Volume Groups | `nutanixpc_volume_groups` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Okta | Okta IM2 Logs | `OktaIM2:log` | event | — | HEC (hec_event format) | G | yes | yes | 6 | 6 | 0 | 1 |
| Ollama (local LLM runtime) | Ollama Server Logs | `ollama:server` | event | — | HEC (hec_event format) | G | yes | yes | 2 | 2 | 0 | 0 |
| OpenTelemetry | OpenTelemetry OTLP/JSON | `opentelemetry:otlp` | event | — | HEC (hec_event format) | G | yes | yes | 3 | 3 | 0 | 0 |
| Oracle | Database native audit | `oracle:audit:text` | event | sql_select_audit | HEC (hec format) | G | yes | yes | 2 | 2 | 0 | 0 |
| osquery | osquery Results | `osquery:results` | event | — | HEC (hec_event format) | G | yes | yes | 7 | 7 | 0 | 0 |
| Palo Alto Networks | Pan Ble Iot Sensor | `pan:ble:iot:sensor` | event | — | HEC (syslog format) | - | - | - | 0 | 0 | 0 | 0 |
| Palo Alto Networks | Pan Config | `pan:config` | event | — | HEC (syslog format) | - | - | - | 0 | 0 | 0 | 0 |
| Palo Alto Networks | Pan System | `pan:system` | event | — | HEC (syslog format) | G | - | yes | 3 | 3 | 0 | 1 |
| Palo Alto Networks | Pan Threat | `pan:threat` | event | — | HEC (syslog format) | G | - | yes | 6 | 5 | 1 | 1 |
| Palo Alto Networks | Pan Traffic | `pan:traffic` | event | — | HEC (syslog format) | G | - | yes | 7 | 4 | 3 | 1 |
| pfSense (Netgate) | pfSense filterlog | `pfsense:filterlog` | event | ipv4_tcp_block, ipv4_udp_pass, ipv6_udp_block | HEC (hec format) | G | yes | yes | 4 | 4 | 0 | 0 |
| Proofpoint | Targeted Attack Protection SIEM | `proofpoint_tap_siem` | event | malware_message_blocked, phishing_message_blocked | HEC (hec format) | G | yes | yes | 3 | 3 | 0 | 0 |
| Qualys | Platform user activity log | `qualys:activityLog` | event | console_login, configuration_change | HEC (hec format) | G | yes | yes | 5 | 5 | 0 | 0 |
| Radware | Radware Cwaf Waf | `radware:cwaf:waf` | event | — | HEC (syslog format) | - | - | - | 0 | 0 | 0 | 0 |
| Radware | Radware Csms Ddos | `radware:ddos` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Radware | Radware Defensepro Attack | `radware:defensepro:attack` | event | — | HEC (syslog format) | - | - | - | 0 | 0 | 0 | 0 |
| Radware | Radware Cwaf Waf | `radware:waf` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Rapid7 | InsightVM asset vulnerabilities | `rapid7:insightvm:asset:vulnerability_finding` | event | steady_state_asset_exposure, critical_findings_asset_exposu… | HEC (hec format) | G | yes | yes | 5 | 5 | 0 | 0 |
| SailPoint | Identity Security Cloud audit | `sailpoint_identitynow` | event | password_update, machine_identity_created | HEC (hec format) | G | yes | yes | 5 | 5 | 0 | 1 |
| SentinelOne | Threats channel | `sentinelone:channel:threats` | event | threat_trojan_detected, threat_malware_agent_reported | HEC (hec format) | G | yes | yes | 4 | 4 | 0 | 0 |
| Slack | Enterprise Grid audit logs | `slack:audit` | event | user_login, admin_console_anomaly, malicious_file_detected | HEC (hec format) | G | yes | yes | 5 | 5 | 0 | 0 |
| SonicWall | Sonicwall Firewall | `sonicwall:firewall` | event | — | HEC (syslog format) | - | - | - | 0 | 0 | 0 | 0 |
| Sophos | Sophos Central Cef | `sophos:central:cef` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Sophos | Sophos Xg Firewall | `sophos:xg:firewall` | event | — | HEC (syslog format) | - | - | - | 0 | 0 | 0 | 0 |
| Splunk / Native | Geo_Tokens | `geo_tokens:generic` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Splunk / Native | Cisco Metrics Bgp Rib | `httpevent` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Splunk / Native | Kube Container Calico Kube Controllers | `kube:container:calico-kube-controllers` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Splunk / Native | Kube Container Calico Node | `kube:container:calico-node` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Splunk / Native | Kube Container Controller | `kube:container:controller` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Splunk / Native | Kube Container Coredns | `kube:container:coredns` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Splunk / Native | Kube Container Hostpath Provisioner | `kube:container:hostpath-provisioner` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Splunk / Native | Kube Container Install Cni | `kube:container:install-cni` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Splunk / Native | Kube Container Metrics | `kube:container:metrics` | metric | — | HEC (hec format) | R | - | - | 0 | 0 | 0 | 0 |
| Splunk / Native | Kube Container Metrics Server | `kube:container:metrics-server` | metric | — | HEC (hec format) | R | - | - | 0 | 0 | 0 | 0 |
| Splunk / Native | Kube Container Mibserver | `kube:container:mibserver` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Splunk / Native | Kube Container Mongodb | `kube:container:mongodb` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Splunk / Native | Kube Container Redis | `kube:container:redis` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Splunk / Native | Kube Container Speaker | `kube:container:speaker` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Splunk / Native | Kube Container Upgrade Ipam | `kube:container:upgrade-ipam` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Splunk / Native | Kube Events | `kube:events` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Splunk / Native | Kube Object Pods | `kube:object:pods` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Splunk / Native | Netapp Ontap Nas | `netapp:ontap:nas` | event | — | HEC (syslog format) | - | - | - | 0 | 0 | 0 | 0 |
| Splunk / Native | Nginx Plus Kv | `nginx:plus:kv` | event | — | HEC (syslog format) | G | - | - | 5 | 3 | 2 | 0 |
| Splunk / Native | Postgresql Audit | `postgresql:audit` | event | — | HEC (syslog format) | G | - | - | 3 | 1 | 2 | 0 |
| Splunk / Native | Stream Netflow | `stream:netflow` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Splunk Community / SC4SNMP | Kube Container Splunk Connect For Snmp … | `kube:container:splunk-connect-for-snmp-traps` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Splunk Community / SC4SNMP | Kube Container Splunk Connect For Snmp … | `kube:container:splunk-connect-for-snmp-worker-sender` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Splunk Community / SC4SNMP | Kube Container Splunk Connect For Snmp … | `kube:container:splunk-connect-for-snmp-worker-trap` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Splunk Community / SC4SNMP | Splunk Connect for SNMP (SC4SNMP) Metri… | `sc4snmp:event` | event | — | HEC (syslog format) | G | - | - | 0 | 0 | 0 | 0 |
| Splunk Community / SC4SNMP | Sc4Snmp Metric | `sc4snmp:metric` | metric | — | HEC (hec format) | G | - | yes | 2 | 2 | 0 | 0 |
| Splunk Community / SC4SNMP | Universal SNMP Trap Receiver Event | `snmp:trap` | event | — | HEC (syslog format) | G | - | - | 0 | 0 | 0 | 0 |
| Suricata (OISF) | Suricata EVE JSON | `suricata` | event | — | HEC (hec_event format) | G | yes | yes | 7 | 7 | 0 | 0 |
| Symantec (Broadcom), Web & Ne… | Symantec/Broadcom ProxySG Access Log (f… | `bluecoat:proxysg:access:file` | event | proxy_observed, proxy_denied | HEC (syslog format) | G | yes | yes | 3 | 3 | 0 | 0 |
| Sysdig | Sysdig Secure runtime and Kubernetes au… | `SysdigSecureEvents` | event | runtime_activity, kubernetes_audit | HEC (hec format) | G | yes | yes | 5 | 5 | 0 | 1 |
| Tanium | Discover managed machines | `tanium:discover:managed` | event | managed_endpoint_inventory | HEC (hec format) | G | yes | yes | 4 | 4 | 0 | 0 |
| Tenable | Vulnerability Management audit | `tenable:io:audit_logs` | event | password_authentication_failure, session_created, session_d… | HEC (hec format) | G | yes | yes | 5 | 5 | 0 | 1 |
| Traefik Labs | Traefik Proxy access | `traefik:access:json` | event | http_access | HEC (hec format) | G | yes | yes | 5 | 5 | 0 | 0 |
| Trellix (formerly McAfee) | ePO threat events | `trellix_epo:threat_events` | event | nips_port_scan_handled, blocked_process_access, nids_would_… | HEC (hec format) | G | yes | yes | 4 | 4 | 0 | 0 |
| Veeam | Backup & Replication | `veeam_vbr_syslog` | event | backup_job_started, backup_job_completed, malware_detected | HEC (hec format) | G | yes | yes | 3 | 3 | 0 | 0 |
| VMware by Broadcom | VMware vSphere ESXi Syslog | `vmw-syslog` | event | — | HEC (syslog format) | G | yes | yes | 1 | 1 | 0 | 0 |
| VMware by Broadcom | Vmware Nsx Audit | `vmware:nsx:audit` | event | — | HEC (syslog format) | - | - | - | 0 | 0 | 0 | 0 |
| VMware by Broadcom | Vmware Nsx Firewall | `vmware:nsx:firewall` | event | — | HEC (syslog format) | - | - | - | 0 | 0 | 0 | 0 |
| VMware by Broadcom | Vmware Esx Perf | `vmware:perf:cpu` | metric | — | HEC (hec format) | R | - | - | 0 | 0 | 0 | 0 |
| WatchGuard | Watchguard Fireware Alarm | `watchguard:fireware:alarm` | event | — | HEC (syslog format) | - | - | - | 0 | 0 | 0 | 0 |
| WatchGuard | Watchguard Fireware Traffic | `watchguard:fireware:traffic` | event | — | HEC (syslog format) | - | - | - | 0 | 0 | 0 | 0 |
| Wazuh | Wazuh Manager Alerts (alerts.log) | `wazuh:alerts` | event | rootcheck_hidden_process, rootcheck_hidden_file | HEC (syslog format) | G | yes | yes | 3 | 3 | 0 | 0 |
| Zeek (Bro) | Zeek (Bro) conn JSON | `bro:conn:json` | event | — | HEC (hec_event format) | G | yes | yes | 3 | 3 | 0 | 0 |
| Zscaler | Zscaler Sse Tunnel | `zscaler:tunnel` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Zscaler | Zscaler Sse Web | `zscaler:web` | event | — | HEC (syslog format) | R | - | - | 0 | 0 | 0 | 0 |
| Zscaler | Zscaler Internet Access (ZIA) NSS Log | `zscaler:zia` | event | — | HEC (syslog format) | G | - | - | 2 | 1 | 1 | 0 |
| Zscaler | Zscaler Zia Tunnel | `zscaler:zia:tunnel` | event | — | HEC (syslog format) | - | - | - | 0 | 0 | 0 | 0 |
| Zscaler | Zscaler Zia Web | `zscaler:zia:web` | event | — | HEC (syslog format) | - | - | - | 0 | 0 | 0 | 0 |
| Zscaler | Zscaler NSS Web Proxy Logs | `zscalernss-web` | event | — | HEC (hec_event format) | G | yes | yes | 6 | 6 | 0 | 1 |
