# Sourcetype Coverage Reference

Generated 2026-10-31 by `scripts/generate_reference_docs.py` from `catalog/sourcetypes.json`, the coverage evidence and the replay registry. Machine-readable: `sourcetype_coverage.json` / `sourcetype_coverage.csv`.

| Measure | Count |
|---|---|
| Cataloged sourcetypes | 349 |
| Native generator | 159 |
| Byte-verified (HEC raw equality in Splunk) | 129 |
| Independently indexed | 137 |
| Recorded replay source (authentic recording, continuous replay) | 9 |
| TA parsing checked in an isolated lab | 6 |
| CIM validated | 0 (no CIM data model is installed in any lab) |
| Referenced by at least one dashboard-backed scenario | 152 |

Columns are separate evidence. A sample-replay catalog entry is **not** a native generator; a recorded replay source is **not** coverage of the catalog sourcetype unless its sourcetype name matches. `TA` shows the add-on named by the catalog (`verified` = Splunkbase declares that exact sourcetype for the app; declaration only). `TA lab` means parsing was exercised with the installed package; nothing else was.

Legend: **G** native generator, **R** sample-replay catalog only, **-** none; **B** byte-verified; **I** independently indexed; **RR** recorded replay source; **TA lab** parsing checked; **CIM** never validated.

## Cisco Systems (133)

| Sourcetype | Product | Kind | Protocol | Gen | B | I | RR | TA | TA lab | Scenarios | Provenance |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `cisco:aci:fault` | Cisco Aci Fault | event | syslog | - | - | - | - | - | - | - | none recorded |
| `cisco:aci:syslog` | Cisco Aci Syslog | event | syslog | - | - | - | - | - | - | - | none recorded |
| `cisco:asa` | Cisco ASA Firewall Connection & Policy | event | syslog | G | - | - | - | Splunk Add-on for Cisco ASA | - | 3 | vendored replay sample cisco-asa.yml |
| `cisco:asa:syslog` | Cisco ASA Syslog Message Stream | event | syslog | R | - | - | - | Splunk Add-on for Cisco ASA | - | - | vendored replay sample cisco-asa-syslog.yml |
| `cisco:catalyst:client` | Cisco Catalyst Client | event | syslog | R | - | - | - | Cisco Enterprise Networking Add-on for Splunk (verified) | - | - | vendored replay sample cisco-catalyst-client.yml |
| `cisco:catalyst:clienthealth` | Cisco Catalyst Clienthealth | event | syslog | G | - | - | - | Cisco Enterprise Networking Add-on for Splunk (verified) | - | 1 | vendored replay sample cisco-catalyst-clienthealth.yml |
| `cisco:catalyst:compliance` | Cisco Catalyst Compliance | event | syslog | R | - | - | - | Cisco Enterprise Networking Add-on for Splunk (verified) | - | - | vendored replay sample cisco-catalyst-compliance.yml |
| `cisco:catalyst:devicehealth` | Cisco Catalyst Devicehealth | event | syslog | R | - | - | - | Cisco Enterprise Networking Add-on for Splunk (verified) | - | - | vendored replay sample cisco-catalyst-devicehealth.yml |
| `cisco:catalyst:issue` | Cisco Catalyst Issue | event | syslog | R | - | - | - | Cisco Enterprise Networking Add-on for Splunk (verified) | - | - | vendored replay sample cisco-catalyst-issue.yml |
| `cisco:catalyst:networkhealth` | Cisco Catalyst Networkhealth | event | syslog | R | - | - | - | Cisco Enterprise Networking Add-on for Splunk (verified) | - | - | vendored replay sample cisco-catalyst-networkhealth.yml |
| `cisco:catalyst:rogue:allowed` | Cisco Catalyst Rogue Allowed | event | syslog | R | - | - | - | - | - | - | vendored replay sample cisco-catalyst-rogue-allowed.yml |
| `cisco:catalyst:rogue:counts` | Cisco Catalyst Rogue Counts | event | syslog | R | - | - | - | - | - | - | vendored replay sample cisco-catalyst-rogue-counts.yml |
| `cisco:catalyst:rogue:threat_details` | Cisco Catalyst Rogue Threat Details | event | syslog | G | - | - | - | - | - | 2 | vendored replay sample cisco-catalyst-rogue-threat-details.yml |
| `cisco:catalyst:rogue:verbose` | Cisco Catalyst Rogue Verbose | event | syslog | G | Y | Y | - | - | - | 3 | universe_batch6.json: Captured records in netspout/appserver/static/sa |
| `cisco:catalyst:rogue:verbose:legacy` | Cisco Catalyst Rogue Verbose Legacy | event | syslog | R | - | - | - | - | - | - | vendored replay sample cisco-catalyst-rogue-verbose-legacy.yml |
| `cisco:catalyst:rogue:wired` | Cisco Catalyst Rogue Wired | event | syslog | R | - | - | - | - | - | - | vendored replay sample cisco-catalyst-rogue-wired.yml |
| `cisco:catalyst:script:heartbeat` | Cisco Catalyst Script Heartbeat | event | syslog | R | - | - | - | - | - | - | vendored replay sample cisco-catalyst-script-heartbeat.yml |
| `cisco:catalyst:security:awips_signatures` | Cisco Catalyst Security Awips Signatures | event | syslog | R | - | - | - | - | - | - | vendored replay sample cisco-catalyst-security-awips-signatures.yml |
| `cisco:catalyst:security:events` | Cisco Catalyst Security Events | event | syslog | G | - | Y | - | - | - | 4 | vendored replay sample cisco-catalyst-security-events.yml |
| `cisco:catalyst:security:profile` | Cisco Catalyst Security Profile | event | syslog | R | - | - | - | - | - | - | vendored replay sample cisco-catalyst-security-profile.yml |
| `cisco:catalyst:security:profile_signatures` | Cisco Catalyst Security Profile Signatures | event | syslog | G | Y | Y | - | - | - | 3 | universe_batch6.json: Captured records in netspout/appserver/static/sa |
| `cisco:catalyst:security:rules` | Cisco Catalyst Security Rules | event | syslog | R | - | - | - | - | - | - | vendored replay sample cisco-catalyst-security-rules.yml |
| `cisco:catalyst:securityadvisory` | Cisco Catalyst Securityadvisory | event | syslog | R | - | - | - | Cisco Enterprise Networking Add-on for Splunk (verified) | - | - | vendored replay sample cisco-catalyst-securityadvisory.yml |
| `cisco:catalyst:syslog` | Cisco Catalyst Syslog | event | syslog | - | - | - | - | - | - | - | none recorded |
| `cisco:catalyst:threat:list` | Cisco Catalyst Threat List | event | syslog | R | - | - | - | - | - | - | vendored replay sample cisco-catalyst-threat-list.yml |
| `cisco:catalyst:threat:signatures` | Cisco Catalyst Threat Signatures | event | syslog | R | - | - | - | - | - | - | vendored replay sample cisco-catalyst-threat-signatures.yml |
| `cisco:catalyst:threat:summary` | Cisco Catalyst Threat Summary | event | syslog | G | Y | Y | - | - | - | 3 | universe_batch6.json: Captured records in netspout/appserver/static/sa |
| `cisco:catalyst:threat:summary:legacy` | Cisco Catalyst Threat Summary Legacy | event | syslog | G | Y | Y | - | - | - | 3 | universe_batch6.json: Captured records in netspout/appserver/static/sa |
| `cisco:cloud_security:dns` | Cisco Cloud Security DNS | event | syslog | G | Y | Y | - | Splunk Add-on for Cisco Cloud Security | - | 3 | none recorded |
| `cisco:cloud_security:firewall` | Cisco Cloud Security Firewall | event | syslog | G | Y | Y | - | Splunk Add-on for Cisco Cloud Security | - | 3 | none recorded |
| `cisco:cloud_security:proxy` | Cisco Cloud Security Web Proxy | event | syslog | G | Y | Y | - | Splunk Add-on for Cisco Cloud Security | - | 3 | none recorded |
| `cisco:dc:aci:class` | Cisco Dc Aci Class | event | syslog | G | Y | Y | - | - | - | - | universe_batch6.json: Captured records in netspout/appserver/static/sa |
| `cisco:dc:aci:events` | Cisco ACI Fabric State Events | event | syslog | R | - | - | - | Cisco ACI Add-on for Splunk Enterprise | - | - | vendored replay sample cisco-dc-aci-events.yml |
| `cisco:dc:aci:health` | Cisco Dc Aci Bridge Domain | event | syslog | G | - | Y | - | - | - | 1 | vendored replay sample cisco-dc-aci-bridge-domain.yml |
| `cisco:dc:nexus9k` | Cisco Dc Nexus9K | event | syslog | G | Y | Y | - | - | - | - | universe_batch6.json: Captured records in netspout/appserver/static/sa |
| `cisco:dc:nexus9k:syslog` | Cisco Dc Nexus9K Syslog | event | syslog | G | - | Y | - | - | - | 2 | vendored replay sample cisco-dc-nexus9k-syslog.yml |
| `cisco:dnac:audit:logs` | Cisco Dnac Audit Logs | event | syslog | R | - | - | - | Cisco Enterprise Networking Add-on for Splunk (verified) | - | - | vendored replay sample cisco-dnac-audit-logs.yml |
| `cisco:dnac:client` | Cisco Dnac Client | event | syslog | R | - | - | - | Cisco Enterprise Networking Add-on for Splunk (verified) | - | - | vendored replay sample cisco-dnac-client.yml |
| `cisco:dnac:clienthealth` | Cisco Dnac Clienthealth | event | syslog | R | - | - | - | Cisco Enterprise Networking Add-on for Splunk (verified) | - | - | vendored replay sample cisco-dnac-clienthealth.yml |
| `cisco:dnac:compliance` | Cisco Dnac Compliance | event | syslog | R | - | - | - | Cisco Enterprise Networking Add-on for Splunk (verified) | - | - | vendored replay sample cisco-dnac-compliance.yml |
| `cisco:dnac:devicehealth` | Cisco Dnac Devicehealth | event | syslog | R | - | - | - | Cisco Enterprise Networking Add-on for Splunk (verified) | - | - | vendored replay sample cisco-dnac-devicehealth.yml |
| `cisco:dnac:issue` | Cisco Dnac Issue | event | syslog | R | - | - | - | Cisco Enterprise Networking Add-on for Splunk (verified) | - | - | vendored replay sample cisco-dnac-issue.yml |
| `cisco:dnac:networkhealth` | Cisco Dnac Networkhealth | event | syslog | R | - | - | - | Cisco Enterprise Networking Add-on for Splunk (verified) | - | - | vendored replay sample cisco-dnac-networkhealth.yml |
| `cisco:dnac:securityadvisory` | Cisco Dnac Securityadvisory | event | syslog | R | - | - | - | Cisco Enterprise Networking Add-on for Splunk (verified) | - | - | vendored replay sample cisco-dnac-securityadvisory.yml |
| `cisco:dnac:site:topology` | Cisco Dnac Site Topology | event | syslog | R | - | - | - | Cisco Enterprise Networking Add-on for Splunk (verified) | - | - | vendored replay sample cisco-dnac-site-topology.yml |
| `cisco:ftd:syslog` | Cisco Ftd Syslog | event | syslog | R | - | - | - | Splunk Add-on for Cisco ASA | - | - | vendored replay sample cisco-ftd-syslog.yml |
| `cisco:intersight:advisories` | Cisco Intersight Advisories | event | syslog | R | - | - | - | Cisco Intersight Add-on for Splunk (verified) | - | - | vendored replay sample cisco-intersight-advisories.yml |
| `cisco:intersight:alarms` | Cisco Intersight Alarms | event | syslog | R | - | - | - | Cisco Intersight Add-on for Splunk (verified) | - | - | vendored replay sample cisco-intersight-alarms.yml |
| `cisco:intersight:auditrecords` | Cisco Intersight Auditrecords | event | syslog | R | - | - | - | Cisco Intersight Add-on for Splunk (verified) | - | - | vendored replay sample cisco-intersight-auditrecords.yml |
| `cisco:intersight:compute` | Cisco Intersight Compute | event | syslog | R | - | - | - | Cisco Intersight Add-on for Splunk (verified) | - | - | vendored replay sample cisco-intersight-compute.yml |
| `cisco:intersight:contracts` | Cisco Intersight Contracts | event | syslog | R | - | - | - | Cisco Intersight Add-on for Splunk (verified) | - | - | vendored replay sample cisco-intersight-contracts.yml |
| `cisco:intersight:licenses` | Cisco Intersight Licenses | event | syslog | R | - | - | - | Cisco Intersight Add-on for Splunk (verified) | - | - | vendored replay sample cisco-intersight-licenses.yml |
| `cisco:intersight:metrics` | Cisco Intersight Metrics | metric | hec | R | - | - | - | Splunk Add-on for Cisco Telemetry (TA-cisco-telemetry) | - | - | vendored replay sample cisco-intersight-metrics.yml |
| `cisco:intersight:networkelements` | Cisco Intersight Networkelements | event | syslog | R | - | - | - | Cisco Intersight Add-on for Splunk (verified) | - | - | vendored replay sample cisco-intersight-networkelements.yml |
| `cisco:intersight:networkobjects` | Cisco Intersight Networkobjects | event | syslog | R | - | - | - | Cisco Intersight Add-on for Splunk (verified) | - | - | vendored replay sample cisco-intersight-networkobjects.yml |
| `cisco:intersight:profiles` | Cisco Intersight Profiles | event | syslog | R | - | - | - | Cisco Intersight Add-on for Splunk (verified) | - | - | vendored replay sample cisco-intersight-profiles.yml |
| `cisco:intersight:targets` | Cisco Intersight Targets | event | syslog | R | - | - | - | Cisco Intersight Add-on for Splunk (verified) | - | - | vendored replay sample cisco-intersight-targets.yml |
| `cisco:ios` | Cisco Ios | event | syslog | G | Y | Y | - | Cisco Enterprise Networking Add-on for Splunk (verified) | - | 1 | vendored replay sample cisco-ios.yml |
| `cisco:ios:mdt` | Cisco Ios Mdt | event | syslog | G | - | Y | - | - | - | 2 | none recorded |
| `cisco:ios:mdt:metric` | Cisco IOS-XE / IOS-XR Model-Driven Telemetry (gRPC/JSON) | metric | hec | G | - | - | - | Splunk Add-on for Cisco IOS | - | 1 | vendored replay sample cisco-ios-mdt-metric.yml |
| `cisco:ios:syslog` | Cisco IOS System Syslog Facility | event | syslog | G | - | - | - | Splunk Add-on for Cisco IOS | - | 4 | vendored replay sample cisco-ios-syslog.yml |
| `cisco:ise:nac:8021x` | Cisco Ise Nac 8021X | event | syslog | - | - | - | - | - | - | 1 | none recorded |
| `cisco:ise:radius:authz:policy` | Cisco Ise Radius Authz Policy | event | syslog | R | - | - | - | Splunk Add-on for Cisco ISE | - | - | vendored replay sample cisco-ise-radius-authz-policy.yml |
| `cisco:ise:radius:policyset` | Cisco Ise Radius Policyset | event | syslog | R | - | - | - | Splunk Add-on for Cisco ISE | - | - | vendored replay sample cisco-ise-radius-policyset.yml |
| `cisco:ise:syslog` | Cisco Ise Syslog | event | syslog | G | - | - | - | Splunk Add-on for Cisco ISE | - | 1 | vendored replay sample cisco-ise-syslog.yml |
| `cisco:ise:tacacs:authz:policy` | Cisco Ise Tacacs Authz Policy | event | syslog | R | - | - | - | Splunk Add-on for Cisco ISE | - | - | vendored replay sample cisco-ise-tacacs-authz-policy.yml |
| `cisco:ise:tacacs:policyset` | Cisco Ise Tacacs Policyset | event | syslog | R | - | - | - | Splunk Add-on for Cisco ISE | - | - | vendored replay sample cisco-ise-tacacs-policyset.yml |
| `cisco:ise:trustsec:sgt` | Cisco Ise Trustsec Sgt | event | syslog | - | - | - | - | - | - | - | none recorded |
| `cisco:isovalent` | Cisco Isovalent Cilium Events | event | hec_event | G | Y | Y | - | Cisco OpenVAD Add-on | - | 3 | none recorded |
| `cisco:isovalent:processConnect` | Cisco Isovalent Cilium processConnect | event | hec_event | G | Y | Y | - | Cisco OpenVAD Add-on | - | 3 | none recorded |
| `cisco:isovalent:processExec` | Cisco Isovalent Cilium processExec | event | hec_event | G | Y | Y | - | Cisco OpenVAD Add-on | - | 3 | none recorded |
| `cisco:mds:san:fc` | Cisco Mds San Fc | event | syslog | - | - | - | - | - | - | - | none recorded |
| `cisco:metrics` | Cisco Metrics Splunk Otel | metric | hec | R | - | - | - | Splunk Add-on for Cisco Telemetry (TA-cisco-telemetry) | - | - | vendored replay sample cisco-metrics-splunk-otel.yml |
| `cisco:nexus` | Cisco Nexus DC Switch Event | event | syslog | R | - | - | - | Cisco Nexus Add-on for Splunk Enterprise | - | - | vendored replay sample cisco-nexus.yml |
| `cisco:nvm:flowdata` | Cisco Nvm Flowdata | event | syslog | R | - | - | - | Cisco Endpoint Security Analytics (CESA) Add-On for Splunk (verified) | - | - | vendored replay sample cisco-nvm-flowdata.yml |
| `cisco:nvm:flowdata:v2` | Cisco NVM Flow Data v2 | event | hec_event | G | Y | Y | - | Cisco Security OpenVAD Add-on | - | 1 | none recorded |
| `cisco:nxos` | Cisco NX-OS Structured Event Stream | event | syslog | R | - | - | - | Cisco Nexus Add-on for Splunk Enterprise | - | - | vendored replay sample cisco-nxos.yml |
| `cisco:nxos:syslog` | Cisco NX-OS Syslog Event | event | syslog | R | - | - | - | Cisco Nexus Add-on for Splunk Enterprise | - | - | vendored replay sample cisco-nxos-syslog.yml |
| `cisco:sdwan:AAA-6-METHOD_LIST_STATE` | Cisco Sdwan Aaa 6 Method List State | event | syslog | G | Y | Y | - | - | - | 2 | universe_batch5.json: Captured IOS-XE messages in netspout/appserver/s |
| `cisco:sdwan:AAA-6-NOTIFY_MLIST_STATE_TO_AAA_CLIENT` | Cisco Sdwan Aaa 6 Notify Mlist State To Aaa Client | event | syslog | G | Y | Y | - | - | - | 2 | universe_batch5.json: Captured IOS-XE messages in netspout/appserver/s |
| `cisco:sdwan:AAA_AUDIT_MESSAGE-6-METHOD_LIST_STATE` | Cisco Sdwan Aaa Audit Message 6 Method List State | event | syslog | G | Y | Y | - | - | - | 2 | universe_batch5.json: Captured IOS-XE messages in netspout/appserver/s |
| `cisco:sdwan:AAA_AUDIT_MESSAGE-6-NOTIFY_MLIST_STATE_TO_AAA_CLIENT` | Cisco Sdwan Aaa Audit Message 6 Notify Mlist State To Aaa Client | event | syslog | G | Y | Y | - | - | - | 2 | universe_batch5.json: Captured IOS-XE messages in netspout/appserver/s |
| `cisco:sdwan:BGP-5-ADJCHANGE` | Cisco Sdwan Bgp 5 Adjchange | event | syslog | G | Y | Y | - | - | - | 5 | universe_batch5.json: Captured IOS-XE messages in netspout/appserver/s |
| `cisco:sdwan:BGP-5-NBR_RESET` | Cisco Sdwan Bgp 5 Nbr Reset | event | syslog | G | Y | Y | - | - | - | 4 | universe_batch5.json: Captured IOS-XE messages in netspout/appserver/s |
| `cisco:sdwan:BGP-6-NEXTHOP` | Cisco Sdwan Bgp 6 Nexthop | event | syslog | G | Y | Y | - | - | - | - | universe_batch5.json: Captured IOS-XE messages in netspout/appserver/s |
| `cisco:sdwan:BGP_SESSION-5-ADJCHANGE` | Cisco Sdwan Bgp Session 5 Adjchange | event | syslog | G | Y | Y | - | - | - | - | universe_batch5.json: Captured IOS-XE messages in netspout/appserver/s |
| `cisco:sdwan:CDP-4-NATIVE_VLAN_MISMATCH` | Cisco Sdwan Cdp 4 Native Vlan Mismatch | event | syslog | G | Y | Y | - | - | - | 4 | universe_batch5.json: Captured IOS-XE messages in netspout/appserver/s |
| `cisco:sdwan:CRYPTO-6-ISAKMP_ON_OFF` | Cisco Sdwan Crypto 6 Isakmp On Off | event | syslog | G | Y | Y | - | - | - | - | universe_batch5.json: Captured IOS-XE messages in netspout/appserver/s |
| `cisco:sdwan:CTS-3-AAA_NO_RADIUS_SERVER` | Cisco Sdwan Cts 3 Aaa No Radius Server | event | syslog | G | Y | Y | - | - | - | 2 | universe_batch5.json: Captured IOS-XE messages in netspout/appserver/s |
| `cisco:sdwan:DMI-5-AUTH_PASSED` | Cisco Sdwan Dmi 5 Auth Passed | event | syslog | G | Y | Y | - | - | - | - | universe_batch5.json: Captured IOS-XE messages in netspout/appserver/s |
| `cisco:sdwan:DMI-5-CONFIG_I` | Cisco Sdwan Dmi 5 Config I | event | syslog | G | Y | Y | - | - | - | - | universe_batch5.json: Captured IOS-XE messages in netspout/appserver/s |
| `cisco:sdwan:DMI-5-SYNC_COMPLETE` | Cisco Sdwan Dmi 5 Sync Complete | event | syslog | G | Y | Y | - | - | - | 4 | universe_batch5.json: Captured IOS-XE messages in netspout/appserver/s |
| `cisco:sdwan:DMI-5-SYNC_NEEDED` | Cisco Sdwan Dmi 5 Sync Needed | event | syslog | G | Y | Y | - | - | - | 4 | universe_batch5.json: Captured IOS-XE messages in netspout/appserver/s |
| `cisco:sdwan:DMI-5-SYNC_START` | Cisco Sdwan Dmi 5 Sync Start | event | syslog | G | Y | Y | - | - | - | 4 | universe_batch5.json: Captured IOS-XE messages in netspout/appserver/s |
| `cisco:sdwan:ENVIRONMENTAL-1-ALERT` | Cisco Sdwan Environmental 1 Alert | event | syslog | G | Y | Y | - | - | - | 4 | universe_batch5.json: Captured IOS-XE messages in netspout/appserver/s |
| `cisco:sdwan:EVENTLIB-3-CPUHOG` | Cisco Sdwan Eventlib 3 Cpuhog | event | syslog | G | Y | Y | - | - | - | 4 | universe_batch5.json: Captured IOS-XE messages in netspout/appserver/s |
| `cisco:sdwan:IOSXE-3-PLATFORM` | Cisco Sdwan Iosxe 3 Platform | event | syslog | G | Y | Y | - | - | - | 4 | universe_batch5.json: Captured IOS-XE messages in netspout/appserver/s |
| `cisco:sdwan:IOSXE_INFRA-4-NO_PUNT_KEEPALIVE` | Cisco Sdwan Iosxe Infra 4 No Punt Keepalive | event | syslog | G | Y | Y | - | - | - | 4 | universe_batch5.json: Captured IOS-XE messages in netspout/appserver/s |
| `cisco:sdwan:IOSXE_RP_PAE_NOT-6-PAE_STARTUP` | Cisco Sdwan Iosxe Rp Pae Not 6 Pae Startup | event | syslog | G | Y | Y | - | - | - | - | universe_batch5.json: Captured IOS-XE messages in netspout/appserver/s |
| `cisco:sdwan:LINEPROTO-5-UPDOWN` | Cisco Sdwan Lineproto 5 Updown | event | syslog | G | Y | Y | - | - | - | 4 | universe_batch5.json: Captured IOS-XE messages in netspout/appserver/s |
| `cisco:sdwan:LINK-5-CHANGED` | Cisco Sdwan Link 5 Changed | event | syslog | G | Y | Y | - | - | - | 4 | universe_batch5.json: Captured IOS-XE messages in netspout/appserver/s |
| `cisco:sdwan:LINK-5-UPDOWN` | Cisco Sdwan Link 5 Updown | event | syslog | G | Y | Y | - | - | - | 4 | universe_batch5.json: Captured IOS-XE messages in netspout/appserver/s |
| `cisco:sdwan:MDT_CONNECTION-6-STATE_CHANGED` | Cisco Sdwan Mdt Connection 6 State Changed | event | syslog | G | Y | Y | - | Splunk Add-on for Cisco Telemetry (TA-cisco-telemetry) | - | 4 | universe_batch5.json: Captured IOS-XE messages in netspout/appserver/s |
| `cisco:sdwan:MSDP-5-PEER_UPDOWN` | Cisco Sdwan Msdp 5 Peer Updown | event | syslog | G | Y | Y | - | - | - | 4 | universe_batch5.json: Captured IOS-XE messages in netspout/appserver/s |
| `cisco:sdwan:NDBMAN-5-CONFIG_I` | Cisco Sdwan Ndbman 5 Config I | event | syslog | G | Y | Y | - | - | - | 4 | universe_batch5.json: Captured IOS-XE messages in netspout/appserver/s |
| `cisco:sdwan:OSPF-5-ADJCHG` | Cisco Sdwan Ospf 5 Adjchg | event | syslog | G | Y | Y | - | - | - | 4 | universe_batch5.json: Captured IOS-XE messages in netspout/appserver/s |
| `cisco:sdwan:PKI-6-AUTHORITATIVE_CLOCK` | Cisco Sdwan Pki 6 Authoritative Clock | event | syslog | G | Y | Y | - | - | - | 4 | universe_batch5.json: Captured IOS-XE messages in netspout/appserver/s |
| `cisco:sdwan:PLATFORM-4-ELEMENT_WARNING` | Cisco Sdwan Platform 4 Element Warning | event | syslog | G | Y | Y | - | - | - | 4 | universe_batch5.json: Captured IOS-XE messages in netspout/appserver/s |
| `cisco:sdwan:SYS-5-CONFIG_P` | Cisco Sdwan Sys 5 Config P | event | syslog | G | Y | Y | - | - | - | - | universe_batch5.json: Captured IOS-XE messages in netspout/appserver/s |
| `cisco:sdwan:access` | Cisco SD-WAN Management Access | event | syslog | G | Y | Y | - | - | - | 1 | none recorded |
| `cisco:sdwan:linkhealth` | Cisco Sdwan Linkhealth | event | syslog | G | - | - | - | Cisco Enterprise Networking Add-on for Splunk (verified) | - | 1 | vendored replay sample cisco-sdwan-linkhealth.yml |
| `cisco:sdwan:sitehealth` | Cisco Sdwan Sitehealth | event | syslog | R | - | - | - | Cisco Enterprise Networking Add-on for Splunk (verified) | - | - | vendored replay sample cisco-sdwan-sitehealth.yml |
| `cisco:sdwan:ssetunnels` | Cisco Sdwan Ssetunnels | event | syslog | G | Y | Y | - | Cisco Enterprise Networking Add-on for Splunk (verified) | - | 2 | universe_batch6.json: Captured records in netspout/appserver/static/sa |
| `cisco:sdwan:syslog` | Cisco Sdwan Syslog | event | syslog | G | Y | Y | - | Cisco Enterprise Networking Add-on for Splunk (verified) | - | 1 | vendored replay sample cisco-sdwan-syslog.yml |
| `cisco:sdwan:system:logs` | Cisco Sdwan System Logs | event | syslog | R | - | - | - | Cisco Enterprise Networking Add-on for Splunk (verified) | - | - | vendored replay sample cisco-sdwan-system-logs.yml |
| `cisco:sdwan:sytem:logs` | Cisco Sdwan Sytem Logs | event | syslog | G | Y | Y | - | Cisco Enterprise Networking Add-on for Splunk (verified) | - | - | universe_batch6.json: Captured records in netspout/appserver/static/sa |
| `cisco:sdwan:tunnelhealth` | Cisco Sdwan Tunnelhealth | event | syslog | R | - | - | - | Cisco Enterprise Networking Add-on for Splunk (verified) | - | - | vendored replay sample cisco-sdwan-tunnelhealth.yml |
| `cisco:sdwan:utd:logs` | Cisco Sdwan Utd Logs | event | syslog | G | Y | Y | - | Cisco Enterprise Networking Add-on for Splunk (verified) | - | 2 | universe_batch6.json: Captured records in netspout/appserver/static/sa |
| `cisco:sdwan:utdhealth` | Cisco Sdwan Utdhealth | event | syslog | G | Y | Y | - | Cisco Enterprise Networking Add-on for Splunk (verified) | - | 2 | universe_batch6.json: Captured records in netspout/appserver/static/sa |
| `cisco:se` | Cisco Se | event | syslog | R | - | - | - | - | - | - | vendored replay sample cisco-se.yml |
| `cisco:secure_access:security_events_ravpn` | Cisco Secure Access RA-VPN Events | event | hec_event | G | Y | Y | - | Splunk Add-on for Cisco Secure Access | - | 6 | none recorded |
| `cisco:sfw:estreamer` | Cisco Sfw Estreamer | event | syslog | G | Y | Y | - | - | - | 1 | vendored replay sample cisco-sfw-estreamer.yml |
| `cisco:sfw:policy` | Cisco Sfw Policy | event | syslog | R | - | - | - | - | - | - | vendored replay sample cisco-sfw-policy.yml |
| `cisco:thousandeyes:event` | Cisco Thousandeyes Event | event | syslog | R | - | - | - | - | - | - | vendored replay sample cisco-thousandeyes-event.yml |
| `cisco:thousandeyes:metric` | Cisco Thousandeyes Metric | metric | hec | G | - | - | - | Splunk Add-on for Cisco Telemetry (TA-cisco-telemetry) | - | 2 | vendored replay sample cisco-thousandeyes-metric.yml |
| `cisco:thousandeyes:path-vis` | Cisco Thousandeyes Path Vis | event | syslog | R | - | - | - | - | - | 1 | vendored replay sample cisco-thousandeyes-path-vis.yml |
| `cisco_syslog` | Cisco Syslog | event | syslog | R | - | - | - | - | - | - | vendored replay sample cisco-syslog.yml |
| `datablaster:preflight` | NetSpout Ingestion Preflight Probe | event | syslog | R | - | - | - | NetSpout Telemetry App | - | - | vendored replay sample datablaster-preflight.yml |
| `datablaster:probe` | NetSpout Telemetry Canary Probe | event | syslog | R | - | - | - | NetSpout Telemetry App | - | - | vendored replay sample datablaster-probe.yml |
| `netspout:snmp:poll` | NetSpout Native SNMPv2c Polling Events | event | snmp | G | - | - | - | - | - | 1 | none recorded |
| `netspout:snmp:trap` | NetSpout Native SNMPv2c Traps & Informs | event | snmp | G | - | - | - | - | - | 1 | none recorded |
| `openconfig:gnmi:telemetry` | Openconfig Gnmi Telemetry | event | syslog | - | - | - | - | - | - | - | none recorded |
| `opsec` | Opsec | event | syslog | - | - | - | - | - | - | - | none recorded |

## Splunk / Native (21)

| Sourcetype | Product | Kind | Protocol | Gen | B | I | RR | TA | TA lab | Scenarios | Provenance |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `geo_tokens:generic` | Geo_Tokens | event | syslog | R | - | - | - | Splunk Add-on for Unix and Linux | - | - | vendored replay sample hosts_core.sample |
| `httpevent` | Cisco Metrics Bgp Rib | event | syslog | R | - | - | - | Splunk Add-on for Cisco Telemetry (TA-cisco-telemetry) | - | - | vendored replay sample cisco-metrics-bgp-rib.yml |
| `kube:container:calico-kube-controllers` | Kube Container Calico Kube Controllers | event | syslog | R | - | - | - | Splunk Add-on for Unix and Linux | - | - | vendored replay sample kube-container-calico-kube-controllers.yml |
| `kube:container:calico-node` | Kube Container Calico Node | event | syslog | R | - | - | - | Splunk Add-on for Unix and Linux | - | - | vendored replay sample kube-container-calico-node.yml |
| `kube:container:controller` | Kube Container Controller | event | syslog | R | - | - | - | Splunk Add-on for Unix and Linux | - | - | vendored replay sample kube-container-controller.yml |
| `kube:container:coredns` | Kube Container Coredns | event | syslog | R | - | - | - | Splunk Add-on for Unix and Linux | - | - | vendored replay sample kube-container-coredns.yml |
| `kube:container:hostpath-provisioner` | Kube Container Hostpath Provisioner | event | syslog | R | - | - | - | Splunk Add-on for Unix and Linux | - | - | vendored replay sample kube-container-hostpath-provisioner.yml |
| `kube:container:install-cni` | Kube Container Install Cni | event | syslog | R | - | - | - | Splunk Add-on for Unix and Linux | - | - | vendored replay sample kube-container-install-cni.yml |
| `kube:container:metrics` | Kube Container Metrics | metric | hec | R | - | - | - | Splunk Add-on for Cisco Telemetry (TA-cisco-telemetry) | - | - | vendored replay sample kube-container-metrics.yml |
| `kube:container:metrics-server` | Kube Container Metrics Server | metric | hec | R | - | - | - | Splunk Add-on for Cisco Telemetry (TA-cisco-telemetry) | - | - | vendored replay sample kube-container-metrics-server.yml |
| `kube:container:mibserver` | Kube Container Mibserver | event | syslog | R | - | - | - | Splunk Add-on for Unix and Linux | - | - | vendored replay sample kube-container-mibserver.yml |
| `kube:container:mongodb` | Kube Container Mongodb | event | syslog | R | - | - | - | Splunk Add-on for Unix and Linux | - | - | vendored replay sample kube-container-mongodb.yml |
| `kube:container:redis` | Kube Container Redis | event | syslog | R | - | - | - | Splunk Add-on for Unix and Linux | - | - | vendored replay sample kube-container-redis.yml |
| `kube:container:speaker` | Kube Container Speaker | event | syslog | R | - | - | - | Splunk Add-on for Unix and Linux | - | - | vendored replay sample kube-container-speaker.yml |
| `kube:container:upgrade-ipam` | Kube Container Upgrade Ipam | event | syslog | R | - | - | - | Splunk Add-on for Unix and Linux | - | - | vendored replay sample kube-container-upgrade-ipam.yml |
| `kube:events` | Kube Events | event | syslog | R | - | - | - | Splunk Add-on for Unix and Linux | - | - | vendored replay sample kube-events.yml |
| `kube:object:pods` | Kube Object Pods | event | syslog | R | - | - | - | Splunk Add-on for Unix and Linux | - | - | vendored replay sample kube-object-pods.yml |
| `netapp:ontap:nas` | Netapp Ontap Nas | event | syslog | - | - | - | - | - | - | - | none recorded |
| `nginx:plus:kv` | Nginx Plus Kv | event | syslog | G | - | - | - | - | - | 3 | none recorded |
| `postgresql:audit` | Postgresql Audit | event | syslog | G | - | - | - | - | - | 1 | none recorded |
| `stream:netflow` | Stream Netflow | event | syslog | R | - | - | - | Splunk Add-on for Unix and Linux | - | - | vendored replay sample stream-netflow.yml |

## Cisco Meraki (17)

| Sourcetype | Product | Kind | Protocol | Gen | B | I | RR | TA | TA lab | Scenarios | Provenance |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `cisco:meraki:syslog` | Cisco Meraki Syslog | event | syslog | G | Y | Y | - | - | - | 1 | none recorded |
| `meraki:accesspoints` | Meraki Accesspoints | event | syslog | R | - | - | - | Splunk Add-on for Cisco Meraki | - | 1 | vendored replay sample meraki-accesspoints.yml |
| `meraki:airmarshal` | Meraki Airmarshal | event | syslog | R | - | - | - | Splunk Add-on for Cisco Meraki | - | - | vendored replay sample meraki-airmarshal.yml |
| `meraki:appliance` | Meraki Appliance | event | syslog | - | - | - | - | - | - | - | none recorded |
| `meraki:appliancesdwanstatistics` | Meraki Appliancesdwanstatistics | event | syslog | R | - | - | - | Splunk Add-on for Cisco Telemetry (TA-cisco-telemetry) | - | - | vendored replay sample meraki-appliancesdwanstatistics.yml |
| `meraki:appliancesdwanstatuses` | Meraki Appliancesdwanstatuses | event | syslog | R | - | - | - | Splunk Add-on for Cisco Meraki | - | - | vendored replay sample meraki-appliancesdwanstatuses.yml |
| `meraki:assurancealerts` | Meraki Assurancealerts | event | syslog | G | - | - | - | Splunk Add-on for Cisco Meraki | - | 1 | vendored replay sample meraki-assurancealerts.yml |
| `meraki:devices` | Meraki Devices | event | syslog | R | - | - | - | Splunk Add-on for Cisco Meraki | - | - | vendored replay sample meraki-devices.yml |
| `meraki:devicesavailabilitieschangehistory` | Meraki Devices Availabilities | event | syslog | R | - | - | - | Splunk Add-on for Cisco Meraki | - | - | vendored replay sample meraki-devices-availabilities.yml |
| `meraki:organizationsecurity` | Meraki Organizationsecurity | event | syslog | R | - | - | - | Splunk Add-on for Cisco Meraki | - | - | vendored replay sample meraki-organizationsecurity.yml |
| `meraki:security` | Meraki Security | event | syslog | - | - | - | - | - | - | - | none recorded |
| `meraki:securityappliances` | Meraki Securityappliances | event | syslog | - | - | - | - | - | - | - | none recorded |
| `meraki:summarytopappliancesbyutilization` | Meraki Summarytopappliancesbyutilization | event | syslog | R | - | - | - | Splunk Add-on for Cisco Meraki | - | - | vendored replay sample meraki-summarytopappliancesbyutilization.yml |
| `meraki:summarytopclientsbyusage` | Meraki Summarytopclientsbyusage | event | syslog | R | - | - | - | Splunk Add-on for Cisco Meraki | - | - | vendored replay sample meraki-summarytopclientsbyusage.yml |
| `meraki:summarytopdevicesbyusage` | Meraki Summarytopdevicesbyusage | event | syslog | R | - | - | - | Splunk Add-on for Cisco Meraki | - | - | vendored replay sample meraki-summarytopdevicesbyusage.yml |
| `meraki:switchportsbyswitch` | Meraki Switchportsbyswitch | event | syslog | R | - | - | - | Splunk Add-on for Cisco Meraki | - | - | vendored replay sample meraki-switchportsbyswitch.yml |
| `meraki:switchportsoverview` | Meraki Switchportsoverview | event | syslog | R | - | - | - | Splunk Add-on for Cisco Meraki | - | - | vendored replay sample meraki-switchportsoverview.yml |

## Nutanix (16)

| Sourcetype | Product | Kind | Protocol | Gen | B | I | RR | TA | TA lab | Scenarios | Provenance |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `nutanixPC_disks` | Nutanixpc Disks | event | syslog | R | - | - | - | Nutanix Add-on for Splunk | - | - | vendored replay sample nutanixpc-disks.yml |
| `nutanixpc:syslog` | Nutanix Prism Central Syslog (Colon Format) | event | syslog | R | - | - | - | Nutanix Technology Add-on for Splunk | - | - | vendored replay sample nutanixpc-syslog.yml |
| `nutanixpc:vms` | Nutanix Prism Central VM Inventory (Colon Format) | event | syslog | R | - | - | - | Nutanix Technology Add-on for Splunk | - | - | vendored replay sample nutanixpc-vms.yml |
| `nutanixpc_alerts` | Nutanixpc Alerts | event | syslog | R | - | - | - | Nutanix Add-on for Splunk | - | - | vendored replay sample nutanixpc-alerts.yml |
| `nutanixpc_cluster_performance` | Nutanixpc Cluster Performance | metric | hec | R | - | - | - | Splunk Add-on for Cisco Telemetry (TA-cisco-telemetry) | - | - | vendored replay sample nutanixpc-cluster-performance.yml |
| `nutanixpc_clusters` | Nutanixpc Clusters | event | syslog | R | - | - | - | Nutanix Add-on for Splunk | - | - | vendored replay sample nutanixpc-clusters.yml |
| `nutanixpc_disk_performance` | Nutanixpc Disk Performance | metric | hec | R | - | - | - | Splunk Add-on for Cisco Telemetry (TA-cisco-telemetry) | - | - | vendored replay sample nutanixpc-disk-performance.yml |
| `nutanixpc_events` | Nutanixpc Events | event | syslog | R | - | - | - | Nutanix Add-on for Splunk | - | - | vendored replay sample nutanixpc-events.yml |
| `nutanixpc_host_performance` | Nutanixpc Host Performance | metric | hec | R | - | - | - | Splunk Add-on for Cisco Telemetry (TA-cisco-telemetry) | - | - | vendored replay sample nutanixpc-host-performance.yml |
| `nutanixpc_hosts` | Nutanixpc Hosts | event | syslog | R | - | - | - | Nutanix Add-on for Splunk | - | - | vendored replay sample nutanixpc-hosts.yml |
| `nutanixpc_prismCentrals` | Nutanixpc Prismcentrals | event | syslog | R | - | - | - | Nutanix Add-on for Splunk | - | - | vendored replay sample nutanixpc-prismcentrals.yml |
| `nutanixpc_storage_containers` | Nutanixpc Storage Containers | event | syslog | R | - | - | - | Nutanix Add-on for Splunk | - | - | vendored replay sample nutanixpc-storage-containers.yml |
| `nutanixpc_syslog` | Nutanixpc Syslog | event | syslog | R | - | - | - | Nutanix Add-on for Splunk | - | - | vendored replay sample nutanixpc-syslog.yml |
| `nutanixpc_vm_performance` | Nutanixpc Vm Performance | metric | hec | R | - | - | - | Splunk Add-on for Cisco Telemetry (TA-cisco-telemetry) | - | - | vendored replay sample nutanixpc-vm-performance.yml |
| `nutanixpc_vms` | Nutanixpc Vms | event | syslog | R | - | - | - | Nutanix Add-on for Splunk | - | - | vendored replay sample nutanixpc-vms.yml |
| `nutanixpc_volume_groups` | Nutanixpc Volume Groups | event | syslog | R | - | - | - | Nutanix Add-on for Splunk | - | - | vendored replay sample nutanixpc-volume-groups.yml |

## Cisco Duo (10)

| Sourcetype | Product | Kind | Protocol | Gen | B | I | RR | TA | TA lab | Scenarios | Provenance |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `cisco:duo:account` | Cisco Duo Account | event | syslog | R | - | - | - | - | - | - | vendored replay sample cisco-duo-account.yml |
| `cisco:duo:activity` | Cisco Duo Activity | event | syslog | R | - | - | - | - | - | - | vendored replay sample cisco-duo-activity.yml |
| `cisco:duo:administrator` | Cisco Duo Administrator | event | syslog | G | Y | Y | - | - | - | 6 | vendored replay sample cisco-duo-administrator.yml |
| `cisco:duo:auth` | Cisco Duo Auth | event | syslog | - | - | - | - | - | - | - | none recorded |
| `cisco:duo:authentication` | Cisco Duo Authentication | event | syslog | R | - | - | - | - | - | - | vendored replay sample cisco-duo-authentication.yml |
| `cisco:duo:authentication_v2` | Cisco Duo Authentication V2 | event | syslog | R | - | - | - | - | - | - | vendored replay sample cisco-duo-authentication-v2.yml |
| `cisco:duo:endpoint` | Cisco Duo Endpoint | event | syslog | R | - | - | - | - | - | - | vendored replay sample cisco-duo-endpoint.yml |
| `cisco:duo:push:prompt` | Cisco Duo Push Prompt | event | syslog | - | - | - | - | - | - | 1 | none recorded |
| `cisco:duo:remote:vpn` | Cisco Duo Remote Vpn | event | syslog | G | - | - | - | - | - | 1 | none recorded |
| `cisco:duo:user` | Cisco Duo User | event | syslog | R | - | - | - | - | - | - | vendored replay sample cisco-duo-user.yml |

## Fortinet (8)

| Sourcetype | Product | Kind | Protocol | Gen | B | I | RR | TA | TA lab | Scenarios | Provenance |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `fgt_event` | Fortinet Fortigate Sdwan Alert | event | syslog | R | - | - | - | Fortinet FortiGate Add-on for Splunk | - | - | vendored replay sample fortinet-fortigate-sdwan-alert.yml |
| `fgt_traffic` | Fortinet Fortigate Traffic | event | syslog | R | - | - | - | Fortinet FortiGate Add-on for Splunk | - | - | vendored replay sample fortinet-fortigate-traffic.yml |
| `fortigate_event` | Fortinet FortiGate System Event | event | syslog | R | - | - | - | Fortinet FortiGate Add-on for Splunk | - | - | vendored replay sample fortigate-event.yml |
| `fortigate_traffic` | Fortinet FortiGate Traffic Log | event | syslog | R | - | - | - | Fortinet FortiGate Add-on for Splunk | - | - | vendored replay sample fortigate-traffic.yml |
| `fortinet:fortigate` | Fortinet FortiGate Unified Security Event | event | syslog | R | - | - | - | Fortinet FortiGate Add-on for Splunk | - | - | vendored replay sample fortinet-fortigate.yml |
| `fortinet:fortigate:event` | Fortinet Fortigate Event | event | syslog | - | - | - | - | - | - | - | none recorded |
| `fortinet:fortigate:traffic` | Fortinet Fortigate Traffic | event | syslog | - | - | - | - | - | - | - | none recorded |
| `fortinet:fortigate:utm` | Fortinet Fortigate Utm | event | syslog | G | - | - | - | - | - | 1 | none recorded |

## Microsoft Windows (8)

| Sourcetype | Product | Kind | Protocol | Gen | B | I | RR | TA | TA lab | Scenarios | Provenance |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `XmlWinEventLog:Microsoft-Windows-NTLM/Operational` | Windows NTLM Operational XML | event | hec_event | G | Y | Y | - | Splunk Add-on for Microsoft Windows | Y | 3 | none recorded |
| `XmlWinEventLog:Microsoft-Windows-PowerShell/Operational` | Windows PowerShell Operational XML | event | hec_event | G | Y | Y | - | Splunk Add-on for Microsoft Windows | Y | 3 | none recorded |
| `XmlWinEventLog:Microsoft-Windows-Sysmon/Operational` | Windows Sysmon XML | event | hec_event | G | Y | Y | - | Splunk Add-on for Microsoft Windows | Y | 3 | none recorded |
| `XmlWinEventLog:Microsoft-Windows-Windows Defender/Operational` | Windows Defender Operational XML | event | hec_event | G | Y | Y | - | Splunk Add-on for Microsoft Windows | Y | 3 | none recorded |
| `XmlWinEventLog:Security` | Windows Security Audit XML | event | hec_event | G | Y | Y | - | Splunk Add-on for Microsoft Windows | Y | 3 | none recorded |
| `XmlWinEventLog:System` | Windows System Channel XML | event | hec | G | Y | Y | - | Splunk Add-on for Microsoft Windows | Y | 1 | none recorded |
| `iis` | Microsoft IIS W3C Access | event | syslog | G | Y | Y | - | Splunk Add-on for Microsoft IIS | - | 1 | none recorded |
| `sysmon:linux` | Sysmon for Linux | event | hec_event | G | Y | Y | Y | Splunk Add-on for Sysmon on Linux | - | 3 | authentic recording, splunk/attack_data pinned commit 4389fa7a4e74a7c0 |

## Aruba / HPE (6)

| Sourcetype | Product | Kind | Protocol | Gen | B | I | RR | TA | TA lab | Scenarios | Provenance |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `aruba` | Aruba Instant AP & Switch Event | event | syslog | R | - | - | - | Splunk Add-on for Aruba Networks | - | - | vendored replay sample aruba.yml |
| `aruba:authmgr` | Aruba Controller Authentication Manager | event | syslog | R | - | - | - | Splunk Add-on for Aruba Networks | - | - | vendored replay sample aruba-authmgr.yml |
| `aruba:cx:security` | Aruba Cx Security | event | syslog | - | - | - | - | - | - | - | none recorded |
| `aruba:cx:syslog` | Aruba Cx Syslog | event | syslog | - | - | - | - | - | - | - | none recorded |
| `aruba:stm` | Aruba Station Management (STM) | event | syslog | R | - | - | - | Splunk Add-on for Aruba Networks | - | - | vendored replay sample aruba-stm.yml |
| `aruba:syslog` | Aruba Syslog | event | syslog | R | - | - | - | Aruba Networks Add-on for Splunk | - | - | vendored replay sample aruba-syslog.yml |

## Splunk Community / SC4SNMP (6)

| Sourcetype | Product | Kind | Protocol | Gen | B | I | RR | TA | TA lab | Scenarios | Provenance |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `kube:container:splunk-connect-for-snmp-traps` | Kube Container Splunk Connect For Snmp Traps | event | syslog | R | - | - | - | Splunk Add-on for Unix and Linux | - | - | vendored replay sample kube-container-splunk-connect-for-snmp-traps.ym |
| `kube:container:splunk-connect-for-snmp-worker-sender` | Kube Container Splunk Connect For Snmp Worker Sender | event | syslog | R | - | - | - | Splunk Add-on for Unix and Linux | - | - | vendored replay sample kube-container-splunk-connect-for-snmp-worker-s |
| `kube:container:splunk-connect-for-snmp-worker-trap` | Kube Container Splunk Connect For Snmp Worker Trap | event | syslog | R | - | - | - | Splunk Add-on for Unix and Linux | - | - | vendored replay sample kube-container-splunk-connect-for-snmp-worker-t |
| `sc4snmp:event` | Splunk Connect for SNMP (SC4SNMP) Metric / Poller Event | event | syslog | G | - | - | - | SC4SNMP Add-on | - | - | vendored replay sample sc4snmp-event.yml |
| `sc4snmp:metric` | Sc4Snmp Metric | metric | hec | G | - | Y | - | - | - | 2 | none recorded |
| `snmp:trap` | Universal SNMP Trap Receiver Event | event | syslog | G | - | - | - | SC4SNMP Add-on | - | - | vendored replay sample snmp-trap.yml |

## Zscaler (6)

| Sourcetype | Product | Kind | Protocol | Gen | B | I | RR | TA | TA lab | Scenarios | Provenance |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `zscaler:tunnel` | Zscaler Sse Tunnel | event | syslog | R | - | - | - | Zscaler Technical Add-on for Splunk | - | - | vendored replay sample zscaler-sse-tunnel.yml |
| `zscaler:web` | Zscaler Sse Web | event | syslog | R | - | - | - | Zscaler Technical Add-on for Splunk | - | - | vendored replay sample zscaler-sse-web.yml |
| `zscaler:zia` | Zscaler Internet Access (ZIA) NSS Log | event | syslog | G | - | - | - | TA-Zscaler_CIM | - | 1 | vendored replay sample zscaler-zia.yml |
| `zscaler:zia:tunnel` | Zscaler Zia Tunnel | event | syslog | - | - | - | - | - | - | - | none recorded |
| `zscaler:zia:web` | Zscaler Zia Web | event | syslog | - | - | - | - | - | - | - | none recorded |
| `zscalernss-web` | Zscaler NSS Web Proxy Logs | event | hec_event | G | Y | Y | - | Zscaler App for Splunk (NSS) | - | 6 | none recorded |

## Palo Alto Networks (5)

| Sourcetype | Product | Kind | Protocol | Gen | B | I | RR | TA | TA lab | Scenarios | Provenance |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `pan:ble:iot:sensor` | Pan Ble Iot Sensor | event | syslog | - | - | - | - | - | - | - | none recorded |
| `pan:config` | Pan Config | event | syslog | - | - | - | - | - | - | - | none recorded |
| `pan:system` | Pan System | event | syslog | G | - | Y | - | Splunk Add-on for Palo Alto Networks | - | 3 | vendored replay sample pan-system.yml |
| `pan:threat` | Pan Threat | event | syslog | G | - | Y | - | Splunk Add-on for Palo Alto Networks | - | 5 | vendored replay sample pan-threat.yml |
| `pan:traffic` | Pan Traffic | event | syslog | G | - | Y | - | Splunk Add-on for Palo Alto Networks | - | 4 | vendored replay sample pan-traffic.yml |

## Amazon Web Services (4)

| Sourcetype | Product | Kind | Protocol | Gen | B | I | RR | TA | TA lab | Scenarios | Provenance |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `aws:cloudfront:accesslogs` | AWS CloudFront Access Logs | event | syslog | G | Y | Y | - | Splunk Add-on for AWS | - | 6 | none recorded |
| `aws:cloudtrail` | AWS CloudTrail | event | hec_event | G | Y | Y | Y | Splunk Add-on for AWS | - | 6 | authentic recording, splunk/attack_data pinned commit 4389fa7a4e74a7c0 |
| `aws:cloudtrail:lake` | AWS CloudTrail Lake (OCSF) | event | hec_event | G | Y | Y | - | Splunk Add-on for AWS | - | 6 | none recorded |
| `aws:cloudwatchlogs:vpcflow` | AWS VPC Flow Logs (CloudWatch) | event | hec_event | G | Y | Y | - | Splunk Add-on for AWS | - | 4 | none recorded |

## Arista Networks (4)

| Sourcetype | Product | Kind | Protocol | Gen | B | I | RR | TA | TA lab | Scenarios | Provenance |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `arista:eos` | Arista EOS Core Switching | event | syslog | R | - | - | - | Arista Networks App for Splunk | - | 1 | vendored replay sample arista-eos.yml |
| `arista:eos:syslog` | Arista Eos Syslog | event | syslog | R | - | - | - | Arista Networks Telemetry for Splunk | - | - | vendored replay sample arista-eos-syslog.yml |
| `arista:flow:ipfix` | Arista Flow Ipfix | event | syslog | G | - | - | - | - | - | 1 | none recorded |
| `arista:telemetry:json` | Arista Metrics Telemetry | event | syslog | R | - | - | - | Arista Networks Telemetry for Splunk | - | 1 | vendored replay sample arista-metrics-telemetry.yml |

## Linux Infrastructure (4)

| Sourcetype | Product | Kind | Protocol | Gen | B | I | RR | TA | TA lab | Scenarios | Provenance |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `auditd` | Linux auditd Records | event | syslog_rfc3164 | G | Y | Y | Y | Splunk Add-on for Unix and Linux | - | 3 | authentic recording, splunk/attack_data pinned commit 4389fa7a4e74a7c0 |
| `dhcpd` | ISC dhcpd Lease Events | event | syslog | G | Y | Y | - | - | - | 1 | none recorded |
| `linux_messages_syslog` | Linux /var/log/messages | event | syslog_rfc3164 | G | Y | Y | Y | Splunk Add-on for Unix and Linux | - | 3 | authentic recording, splunk/attack_data pinned commit 4389fa7a4e74a7c0 |
| `linux_secure` | Linux /var/log/secure | event | syslog | G | Y | Y | - | Splunk Add-on for Unix and Linux | - | 1 | none recorded |

## Microsoft 365 (4)

| Sourcetype | Product | Kind | Protocol | Gen | B | I | RR | TA | TA lab | Scenarios | Provenance |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `MSExchange:Management` | MS Exchange Management Audit | event | syslog | G | Y | Y | - | Splunk Add-on for Microsoft Exchange | - | 1 | none recorded |
| `o365:graph:messagetrace` | M365 Graph Message Trace | event | hec_event | G | Y | Y | - | Splunk Add-on for Microsoft Office 365 | - | 6 | none recorded |
| `o365:management:activity` | Microsoft 365 Management Activity | event | hec_event | G | Y | Y | - | Splunk Add-on for Microsoft Office 365 | - | 6 | none recorded |
| `o365:reporting:messagetrace` | M365 Reporting Message Trace | event | hec_event | G | Y | Y | - | Splunk Add-on for Microsoft Office 365 | - | 6 | none recorded |

## Netskope (4)

| Sourcetype | Product | Kind | Protocol | Gen | B | I | RR | TA | TA lab | Scenarios | Provenance |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `netskope:alerts` | Netskope Alerts | event | syslog | - | - | - | - | - | - | - | none recorded |
| `netskope:events` | Netskope Events | event | syslog | - | - | - | - | - | - | - | none recorded |
| `netskope:json` | Netskope Json | event | syslog | R | - | - | - | Netskope Add-on for Splunk | - | - | vendored replay sample netskope-json.yml |
| `netskope:sse` | Netskope Security Service Edge (SSE) | event | syslog | R | - | - | - | TA-NetSkopeAppForSplunk | - | - | vendored replay sample netskope-sse.yml |

## Radware (4)

| Sourcetype | Product | Kind | Protocol | Gen | B | I | RR | TA | TA lab | Scenarios | Provenance |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `radware:cwaf:waf` | Radware Cwaf Waf | event | syslog | - | - | - | - | - | - | - | none recorded |
| `radware:ddos` | Radware Csms Ddos | event | syslog | R | - | - | - | Radware CSMS & CWAF Event Collector | - | - | vendored replay sample radware-csms-ddos.yml |
| `radware:defensepro:attack` | Radware Defensepro Attack | event | syslog | - | - | - | - | - | - | - | none recorded |
| `radware:waf` | Radware Cwaf Waf | event | syslog | R | - | - | - | Radware CSMS & CWAF Event Collector | - | - | vendored replay sample radware-cwaf-waf.yml |

## VMware by Broadcom (4)

| Sourcetype | Product | Kind | Protocol | Gen | B | I | RR | TA | TA lab | Scenarios | Provenance |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `vmw-syslog` | VMware vSphere ESXi Syslog | event | syslog | G | Y | Y | - | - | - | 1 | none recorded |
| `vmware:nsx:audit` | Vmware Nsx Audit | event | syslog | - | - | - | - | - | - | - | none recorded |
| `vmware:nsx:firewall` | Vmware Nsx Firewall | event | syslog | - | - | - | - | - | - | - | none recorded |
| `vmware:perf:cpu` | Vmware Esx Perf | metric | hec | R | - | - | - | Splunk Add-on for Cisco Telemetry (TA-cisco-telemetry) | - | - | vendored replay sample vmware-esx-perf.yml |

## Check Point Software (3)

| Sourcetype | Product | Kind | Protocol | Gen | B | I | RR | TA | TA lab | Scenarios | Provenance |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `checkpoint:cef` | Checkpoint Cef | event | syslog | R | - | - | - | CCX Unified Splunk Add-on for Check Point | - | - | vendored replay sample checkpoint-cef.yml |
| `checkpoint:firewall` | Checkpoint Firewall | event | syslog | - | - | - | - | - | - | - | none recorded |
| `checkpoint:threat` | Checkpoint Threat | event | syslog | - | - | - | - | - | - | - | none recorded |

## Cloudflare (3)

| Sourcetype | Product | Kind | Protocol | Gen | B | I | RR | TA | TA lab | Scenarios | Provenance |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `cloudflare:firewall` | Cloudflare Firewall | event | syslog | - | - | - | - | - | - | - | none recorded |
| `cloudflare:json` | Cloudflare Json | event | syslog | R | - | - | - | Cloudflare App for Splunk | - | - | vendored replay sample cloudflare-json.yml |
| `cloudflare:r2:json` | Cloudflare R2 Metrics | event | syslog | R | - | - | - | Splunk Add-on for Cisco Telemetry (TA-cisco-telemetry) | - | - | vendored replay sample cloudflare-r2-metrics.yml |

## Juniper Networks (3)

| Sourcetype | Product | Kind | Protocol | Gen | B | I | RR | TA | TA lab | Scenarios | Provenance |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `juniper:junos` | Juniper Junos Routing & System Log | event | syslog | G | - | - | - | Juniper Networks Add-on for Splunk | - | 2 | vendored replay sample juniper-junos.yml |
| `juniper:junos:syslog` | Juniper Junos Syslog Transport | event | syslog | R | - | - | - | Juniper Networks Add-on for Splunk | - | - | vendored replay sample juniper-junos-syslog.yml |
| `juniper:syslog` | Juniper Syslog | event | syslog | R | - | - | - | Splunk Add-on for Juniper | - | - | vendored replay sample juniper-syslog.yml |

## Nokia (3)

| Sourcetype | Product | Kind | Protocol | Gen | B | I | RR | TA | TA lab | Scenarios | Provenance |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `nokia:sr:syslog` | Nokia Sr Syslog | event | syslog | - | - | - | - | - | - | - | none recorded |
| `nokia:sros` | Nokia 7750 SR OS Service Router Event | event | syslog | R | - | - | - | Nokia SR OS Splunk Add-on | - | - | vendored replay sample nokia-sros.yml |
| `nokia:sros:syslog` | Nokia 7750 SR OS Syslog Facility | event | syslog | G | - | - | - | Nokia SR OS Splunk Add-on | - | 2 | vendored replay sample nokia-sros-syslog.yml |

## A10 Networks (2)

| Sourcetype | Product | Kind | Protocol | Gen | B | I | RR | TA | TA lab | Scenarios | Provenance |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `a10:acos:cgnat` | A10 Acos Cgnat | event | syslog | - | - | - | - | - | - | - | none recorded |
| `a10:acos:syslog` | A10 Acos Syslog | event | syslog | - | - | - | - | - | - | - | none recorded |

## Citrix / Cloud Software Group (2)

| Sourcetype | Product | Kind | Protocol | Gen | B | I | RR | TA | TA lab | Scenarios | Provenance |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `citrix:netscaler:syslog` | Citrix Netscaler Syslog | event | syslog | - | - | - | - | - | - | - | none recorded |
| `citrix:netscaler:web` | Citrix Netscaler Web | event | syslog | - | - | - | - | - | - | - | none recorded |

## ExtraHop Networks (2)

| Sourcetype | Product | Kind | Protocol | Gen | B | I | RR | TA | TA lab | Scenarios | Provenance |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `extrahop:eda:alert` | Extrahop Eda Alert | event | syslog | R | - | - | - | ExtraHop Add-on for Splunk | - | - | vendored replay sample extrahop-eda-alert.yml |
| `extrahop:eda:metrics` | Extrahop Metrics Performance | metric | hec | R | - | - | - | ExtraHop Add-on for Splunk | - | - | vendored replay sample extrahop-metrics-performance.yml |

## Extreme Networks (2)

| Sourcetype | Product | Kind | Protocol | Gen | B | I | RR | TA | TA lab | Scenarios | Provenance |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `extreme:exos:syslog` | Extreme Exos Syslog | event | syslog | - | - | - | - | - | - | - | none recorded |
| `extreme:voss:syslog` | Extreme Voss Syslog | event | syslog | - | - | - | - | - | - | - | none recorded |

## F5 Networks (2)

| Sourcetype | Product | Kind | Protocol | Gen | B | I | RR | TA | TA lab | Scenarios | Provenance |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `f5:bigip:ltm` | F5 BIG-IP Local Traffic Manager (LTM) | event | syslog | G | - | - | - | F5 Networks Add-on for Splunk | - | 1 | vendored replay sample f5-bigip-ltm.yml |
| `f5:bigip:syslog` | F5 Bigip Syslog | event | syslog | R | - | - | - | Splunk Add-on for F5 BIG-IP | - | - | vendored replay sample f5-bigip-syslog.yml |

## Forcepoint (2)

| Sourcetype | Product | Kind | Protocol | Gen | B | I | RR | TA | TA lab | Scenarios | Provenance |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `forcepoint:ngfw:alert` | Forcepoint Ngfw Alert | event | syslog | - | - | - | - | - | - | - | none recorded |
| `forcepoint:ngfw:traffic` | Forcepoint Ngfw Traffic | event | syslog | - | - | - | - | - | - | - | none recorded |

## Google Workspace (2)

| Sourcetype | Product | Kind | Protocol | Gen | B | I | RR | TA | TA lab | Scenarios | Provenance |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `gsuite:gmail:bigquery` | Gmail BigQuery Message Export | event | hec_event | G | Y | Y | - | Splunk Add-on for Google Workspace | - | 6 | none recorded |
| `gws:reports:login` | Google Workspace Login Reports | event | hec_event | G | Y | Y | - | Add-on for Google Workspace | - | 6 | none recorded |

## Huawei Technologies (2)

| Sourcetype | Product | Kind | Protocol | Gen | B | I | RR | TA | TA lab | Scenarios | Provenance |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `huawei:vrp:syslog` | Huawei Vrp Syslog | event | syslog | - | - | - | - | - | - | - | none recorded |
| `huawei:vrp:traffic` | Huawei Vrp Traffic | event | syslog | - | - | - | - | - | - | - | none recorded |

## Kubernetes & Falco (CNCF) (2)

| Sourcetype | Product | Kind | Protocol | Gen | B | I | RR | TA | TA lab | Scenarios | Provenance |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `kube:audit` | Kubernetes Audit Log | event | hec_event | G | Y | Y | - | - | - | 2 | none recorded |
| `kube:container:falco` | Falco Runtime Security Events | event | hec_event | G | Y | Y | - | - | - | 2 | none recorded |

## Microsoft Azure Monitor (2)

| Sourcetype | Product | Kind | Protocol | Gen | B | I | RR | TA | TA lab | Scenarios | Provenance |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `azure:monitor:aad` | Microsoft Entra ID (Azure AD) Monitor | event | hec_event | G | Y | Y | - | Splunk Add-on for Microsoft Cloud Services | - | 6 | none recorded |
| `azure:monitor:activity` | Azure Activity Log | event | hec_event | G | Y | Y | - | Splunk Add-on for Microsoft Cloud Services | - | 6 | none recorded |

## NGINX (F5) (2)

| Sourcetype | Product | Kind | Protocol | Gen | B | I | RR | TA | TA lab | Scenarios | Provenance |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `nginx:access` | NGINX combined access log | event | hec | G | Y | Y | Y | Mapping pending | - | 6 | vendored recording |
| `nginx:plus:access` | NGINX Plus access (key=value) | event | hec | G | Y | Y | - | Splunk Add-on for NGINX (verified) | - | - | universe_batch7.json: {"corpus": "splunk/attack_data", "pinned_commit" |

## Sophos (2)

| Sourcetype | Product | Kind | Protocol | Gen | B | I | RR | TA | TA lab | Scenarios | Provenance |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `sophos:central:cef` | Sophos Central Cef | event | syslog | R | - | - | - | Sophos Central Add-on for Splunk | - | - | vendored replay sample sophos-central-cef.yml |
| `sophos:xg:firewall` | Sophos Xg Firewall | event | syslog | - | - | - | - | - | - | - | none recorded |

## WatchGuard (2)

| Sourcetype | Product | Kind | Protocol | Gen | B | I | RR | TA | TA lab | Scenarios | Provenance |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `watchguard:fireware:alarm` | Watchguard Fireware Alarm | event | syslog | - | - | - | - | - | - | - | none recorded |
| `watchguard:fireware:traffic` | Watchguard Fireware Traffic | event | syslog | - | - | - | - | - | - | - | none recorded |

## Atlassian (1)

| Sourcetype | Product | Kind | Protocol | Gen | B | I | RR | TA | TA lab | Scenarios | Provenance |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `Confluence:audit log` | Confluence Cloud audit | event | hec | G | Y | Y | - | Confluence and Jira Audit Add-on for Splunk | - | 3 | universe_batch2.json: "" |

## Barracuda Networks (1)

| Sourcetype | Product | Kind | Protocol | Gen | B | I | RR | TA | TA lab | Scenarios | Provenance |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `barracuda:waf:web_firewall` | Web Application Firewall | event | hec | G | Y | Y | - | Mapping pending: CCX Unified Splunk Add-on for Barracuda | - | 4 | universe_batch3.json: "" |

## BeyondTrust (1)

| Sourcetype | Product | Kind | Protocol | Gen | B | I | RR | TA | TA lab | Scenarios | Provenance |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `ccx:beyondinsight:passwordsafe` | Password Safe audit | event | hec | G | Y | Y | - | CCX Add-on for BeyondTrust Products | - | 5 | universe_batch3.json: "" |

## Bitdefender (1)

| Sourcetype | Product | Kind | Protocol | Gen | B | I | RR | TA | TA lab | Scenarios | Provenance |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `bitdefender:gz` | GravityZone push notifications | event | hec | G | Y | Y | - | Gravityzone Add-on for Splunk | - | 4 | universe_batch4.json: "" |

## Claroty (1)

| Sourcetype | Product | Kind | Protocol | Gen | B | I | RR | TA | TA lab | Scenarios | Provenance |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `claroty:cef` | CTD CEF | event | hec | G | Y | Y | - | Claroty Continuous Threat Detection (CTD) Add-On for Splunk | - | 5 | universe_batch2.json: "" |

## CrowdStrike (1)

| Sourcetype | Product | Kind | Protocol | Gen | B | I | RR | TA | TA lab | Scenarios | Provenance |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `crowdstrike:events:sensor` | CrowdStrike Falcon Sensor Events | event | hec_event | G | Y | Y | Y | Splunk Add-on for CrowdStrike FDR | - | 4 | authentic recording, splunk/attack_data pinned commit 4389fa7a4e74a7c0 |

## CrushFTP (1)

| Sourcetype | Product | Kind | Protocol | Gen | B | I | RR | TA | TA lab | Scenarios | Provenance |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `crushftp:sessionlogs` | CrushFTP Session Logs | event | syslog_rfc3164 | G | Y | Y | Y | - | - | 2 | authentic recording, splunk/attack_data pinned commit 4389fa7a4e74a7c0 |

## Cybereason (1)

| Sourcetype | Product | Kind | Protocol | Gen | B | I | RR | TA | TA lab | Scenarios | Provenance |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `cybereason:malops` | Malops feed | event | hec | G | Y | Y | - | Cybereason Addon For Splunk | - | 4 | universe_batch4.json: "" |

## Darktrace (1)

| Sourcetype | Product | Kind | Protocol | Gen | B | I | RR | TA | TA lab | Scenarios | Provenance |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `darktrace` | Model breach alerts | event | hec | G | Y | Y | - | Darktrace App for Splunk | - | 4 | universe_batch3.json: "" |

## Dell Technologies (1)

| Sourcetype | Product | Kind | Protocol | Gen | B | I | RR | TA | TA lab | Scenarios | Provenance |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `dell:os10:syslog` | Dell Os10 Syslog | event | syslog | - | - | - | - | - | - | - | none recorded |

## Docker (1)

| Sourcetype | Product | Kind | Protocol | Gen | B | I | RR | TA | TA lab | Scenarios | Provenance |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `docker_events` | Docker Engine Events | event | hec | G | Y | Y | - | Docker Monitoring (monitoringdocker Add-on) | - | 3 | universe_batch1.json: "" |

## Elastic (1)

| Sourcetype | Product | Kind | Protocol | Gen | B | I | RR | TA | TA lab | Scenarios | Provenance |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `elasticsearch:json` | Elasticsearch server logs | event | hec | G | Y | Y | - | Add-on for Elasticsearch | - | 5 | universe_batch4.json: "" |

## GitHub (1)

| Sourcetype | Product | Kind | Protocol | Gen | B | I | RR | TA | TA lab | Scenarios | Provenance |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `github:enterprise:audit` | Enterprise audit logs | event | hec | G | Y | Y | - | GitHub Dashboard Collection | - | 5 | universe_batch4.json: "" |

## GitLab (1)

| Sourcetype | Product | Kind | Protocol | Gen | B | I | RR | TA | TA lab | Scenarios | Provenance |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `gitlab:audit:json` | Self-Managed audit events | event | hec | G | Y | Y | - | GitLab Self-Managed Add-on for Splunk (CIM) | - | 5 | universe_batch4.json: "" |

## Google Cloud (1)

| Sourcetype | Product | Kind | Protocol | Gen | B | I | RR | TA | TA lab | Scenarios | Provenance |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `gcp:audit` | Google Cloud Audit Logs | event | hec_event | G | Y | Y | - | Splunk Add-on for Google Cloud Platform | - | 3 | none recorded |

## HashiCorp (1)

| Sourcetype | Product | Kind | Protocol | Gen | B | I | RR | TA | TA lab | Scenarios | Provenance |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `hashicorp_vault_audit_log` | Vault audit | event | hec | G | Y | Y | - | HashiCorp Vault App for Splunk | - | 3 | universe_batch2.json: "" |

## IBM (1)

| Sourcetype | Product | Kind | Protocol | Gen | B | I | RR | TA | TA lab | Scenarios | Provenance |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `ibm:qradar:offense` | QRadar offense events | event | hec | G | Y | Y | - | Mapping pending: IBM QRadar SOAR Add-on for Splunk | - | 5 | universe_batch4.json: "" |

## IBM MQ (1)

| Sourcetype | Product | Kind | Protocol | Gen | B | I | RR | TA | TA lab | Scenarios | Provenance |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `ibm:mq:errorlog` | IBM MQ native error log | event | hec | G | Y | Y | - | Mapping pending: Source type add-on for IBM MQ error logs | - | 2 | universe_batch3.json: "" |

## Imperva (1)

| Sourcetype | Product | Kind | Protocol | Gen | B | I | RR | TA | TA lab | Scenarios | Provenance |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `imperva:securesphere:cef` | SecureSphere CEF | event | hec | G | Y | Y | - | Mapping pending: Imperva AppSecurity View | - | 4 | universe_batch3.json: "" |

## MikroTik (1)

| Sourcetype | Product | Kind | Protocol | Gen | B | I | RR | TA | TA lab | Scenarios | Provenance |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `mikrotik:routeros` | RouterOS console log | event | hec | G | Y | Y | - | Technology Add-On for Mikrotik RouterOS | - | 5 | universe_batch2.json: "" |

## Model Context Protocol (agentic AI) (1)

| Sourcetype | Product | Kind | Protocol | Gen | B | I | RR | TA | TA lab | Scenarios | Provenance |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `mcp:jsonrpc` | Model Context Protocol JSON-RPC | event | hec_event | G | Y | Y | Y | - | - | 2 | authentic recording, splunk/attack_data pinned commit 4389fa7a4e74a7c0 |

## MongoDB (1)

| Sourcetype | Product | Kind | Protocol | Gen | B | I | RR | TA | TA lab | Scenarios | Provenance |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `mongodb:log` | MongoDB structured server log | event | hec | G | Y | Y | - | Mapping pending | - | 3 | universe_batch2.json: "" |

## NetScout Systems (1)

| Sourcetype | Product | Kind | Protocol | Gen | B | I | RR | TA | TA lab | Scenarios | Provenance |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `netscout:omnis:alert` | Netscout Omnis Alert | event | syslog | R | - | - | - | NetScout Omnis Cyber Intelligence Add-on for Splunk | - | - | vendored replay sample netscout-omnis-alert.yml |

## Nozomi Networks (1)

| Sourcetype | Product | Kind | Protocol | Gen | B | I | RR | TA | TA lab | Scenarios | Provenance |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `nozomi:universal_alert` | Nozomi Networks Universal Alert | event | syslog | G | Y | Y | - | Nozomi Networks Universal Add-on | - | 3 | universe_batch1.json: "" |

## Okta (1)

| Sourcetype | Product | Kind | Protocol | Gen | B | I | RR | TA | TA lab | Scenarios | Provenance |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `OktaIM2:log` | Okta IM2 Logs | event | hec_event | G | Y | Y | - | Okta Add-on for Splunk | - | 6 | none recorded |

## Ollama (local LLM runtime) (1)

| Sourcetype | Product | Kind | Protocol | Gen | B | I | RR | TA | TA lab | Scenarios | Provenance |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `ollama:server` | Ollama Server Logs | event | hec_event | G | Y | Y | - | - | - | 2 | none recorded |

## OpenTelemetry (1)

| Sourcetype | Product | Kind | Protocol | Gen | B | I | RR | TA | TA lab | Scenarios | Provenance |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `opentelemetry:otlp` | OpenTelemetry OTLP/JSON | event | hec_event | G | Y | Y | - | - | - | 3 | none recorded |

## Oracle (1)

| Sourcetype | Product | Kind | Protocol | Gen | B | I | RR | TA | TA lab | Scenarios | Provenance |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `oracle:audit:text` | Database native audit | event | hec | G | Y | Y | - | Splunk Add-on for Oracle Database | - | 2 | universe_batch3.json: "" |

## Proofpoint (1)

| Sourcetype | Product | Kind | Protocol | Gen | B | I | RR | TA | TA lab | Scenarios | Provenance |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `proofpoint_tap_siem` | Targeted Attack Protection SIEM | event | hec | G | Y | Y | - | Proofpoint TAP Modular Input | - | 3 | universe_batch2.json: "" |

## Qualys (1)

| Sourcetype | Product | Kind | Protocol | Gen | B | I | RR | TA | TA lab | Scenarios | Provenance |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `qualys:activityLog` | Platform user activity log | event | hec | G | Y | Y | - | Qualys Technology Add-on (TA) for Splunk | - | 5 | universe_batch4.json: "" |

## Rapid7 (1)

| Sourcetype | Product | Kind | Protocol | Gen | B | I | RR | TA | TA lab | Scenarios | Provenance |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `rapid7:insightvm:asset:vulnerability_finding` | InsightVM asset vulnerabilities | event | hec | G | Y | Y | - | Rapid7 InsightVM Technology Add-On for Splunk | - | 5 | universe_batch4.json: "" |

## SailPoint (1)

| Sourcetype | Product | Kind | Protocol | Gen | B | I | RR | TA | TA lab | Scenarios | Provenance |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `sailpoint_identitynow` | Identity Security Cloud audit | event | hec | G | Y | Y | - | SailPoint Identity Security Cloud AuditEvent Add-on | - | 5 | universe_batch3.json: "" |

## SentinelOne (1)

| Sourcetype | Product | Kind | Protocol | Gen | B | I | RR | TA | TA lab | Scenarios | Provenance |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `sentinelone:channel:threats` | Threats channel | event | hec | G | Y | Y | - | SentinelOne App For Splunk | - | 4 | universe_batch4.json: "" |

## Slack (1)

| Sourcetype | Product | Kind | Protocol | Gen | B | I | RR | TA | TA lab | Scenarios | Provenance |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `slack:audit` | Enterprise Grid audit logs | event | hec | G | Y | Y | - | Slack Add-on for Splunk | - | 5 | universe_batch4.json: "" |

## SonicWall (1)

| Sourcetype | Product | Kind | Protocol | Gen | B | I | RR | TA | TA lab | Scenarios | Provenance |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `sonicwall:firewall` | Sonicwall Firewall | event | syslog | - | - | - | - | - | - | - | none recorded |

## Suricata (OISF) (1)

| Sourcetype | Product | Kind | Protocol | Gen | B | I | RR | TA | TA lab | Scenarios | Provenance |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `suricata` | Suricata EVE JSON | event | hec_event | G | Y | Y | Y | - | - | 7 | authentic recording, splunk/attack_data pinned commit 4389fa7a4e74a7c0 |

## Symantec (Broadcom), Web & Network Security (1)

| Sourcetype | Product | Kind | Protocol | Gen | B | I | RR | TA | TA lab | Scenarios | Provenance |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `bluecoat:proxysg:access:file` | Symantec/Broadcom ProxySG Access Log (file/main format) | event | syslog | G | Y | Y | - | Splunk Add-on for Symantec Blue Coat ProxySG | - | 3 | universe_batch1.json: "" |

## Sysdig (1)

| Sourcetype | Product | Kind | Protocol | Gen | B | I | RR | TA | TA lab | Scenarios | Provenance |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `SysdigSecureEvents` | Sysdig Secure runtime and Kubernetes audit | event | hec | G | Y | Y | - | Sysdig Add-on for Splunk | - | 5 | universe_batch3.json: "" |

## Tanium (1)

| Sourcetype | Product | Kind | Protocol | Gen | B | I | RR | TA | TA lab | Scenarios | Provenance |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `tanium:discover:managed` | Discover managed machines | event | hec | G | Y | Y | - | TA-Tanium | - | 4 | universe_batch4.json: "" |

## Tenable (1)

| Sourcetype | Product | Kind | Protocol | Gen | B | I | RR | TA | TA lab | Scenarios | Provenance |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `tenable:io:audit_logs` | Vulnerability Management audit | event | hec | G | Y | Y | - | Tenable Add-On for Splunk | - | 5 | universe_batch3.json: "" |

## Traefik Labs (1)

| Sourcetype | Product | Kind | Protocol | Gen | B | I | RR | TA | TA lab | Scenarios | Provenance |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `traefik:access:json` | Traefik Proxy access | event | hec | G | Y | Y | - | Add On for Traefik Proxy | - | 5 | universe_batch2.json: "" |

## Trellix (formerly McAfee) (1)

| Sourcetype | Product | Kind | Protocol | Gen | B | I | RR | TA | TA lab | Scenarios | Provenance |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `trellix_epo:threat_events` | ePO threat events | event | hec | G | Y | Y | - | Trellix ePO All in one | - | 4 | universe_batch4.json: "" |

## Veeam (1)

| Sourcetype | Product | Kind | Protocol | Gen | B | I | RR | TA | TA lab | Scenarios | Provenance |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `veeam_vbr_syslog` | Backup & Replication | event | hec | G | Y | Y | - | CCX Splunk Add-on for Veeam VBR | - | 3 | universe_batch2.json: "" |

## Wazuh (1)

| Sourcetype | Product | Kind | Protocol | Gen | B | I | RR | TA | TA lab | Scenarios | Provenance |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `wazuh:alerts` | Wazuh Manager Alerts (alerts.log) | event | syslog | G | Y | Y | - | Wazuh Splunk Integration (alerts.log file monitor) | - | 3 | universe_batch1.json: "" |

## Zeek (Bro) (1)

| Sourcetype | Product | Kind | Protocol | Gen | B | I | RR | TA | TA lab | Scenarios | Provenance |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `bro:conn:json` | Zeek (Bro) conn JSON | event | hec_event | G | Y | Y | - | Splunk Add-on for Zeek | - | 3 | none recorded |

## osquery (1)

| Sourcetype | Product | Kind | Protocol | Gen | B | I | RR | TA | TA lab | Scenarios | Provenance |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `osquery:results` | osquery Results | event | hec_event | G | Y | Y | - | - | - | 8 | none recorded |

## pfSense (Netgate) (1)

| Sourcetype | Product | Kind | Protocol | Gen | B | I | RR | TA | TA lab | Scenarios | Provenance |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `pfsense:filterlog` | pfSense filterlog | event | hec | G | Y | Y | - | Mapping pending: Pfsense Add-On for Splunk | - | 4 | universe_batch3.json: "" |

