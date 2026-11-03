# Phase 5 — inventory of all downloaded Splunk packages and mapping to the NetSpout catalog

Derived metadata only. Package contents, the external sample corpus and credentials are not in this repository. Nothing was installed, downloaded or sent to any Splunk instance in this phase. Inventory is not compatibility: a name in this matrix is never a claim that NetSpout supports that product.

## 1. Inventory

| measure | value |
|---|---|
| regular files in ~/netspout/private-packs | 171 |
| inspected | 171 |
| failed | 0 |
| byte-identical duplicate files (each keeps its own row) | 11 |
| unique files by SHA-256 | 160 |
| distinct app identities (id + version) | 162 |
| distinct app ids | 162 |
| distinct vendors by monitored product (rule-based; see limitations) | 97 |
| distinct publishers (app.conf author field) | 97 |
| distinct TA sourcetype names (literal) | 1634 |
| wildcard/pattern stanzas (not counted as names) | 15 |

The directory holds 171 files, not 172. Package types (per app identity): TA 53, mixed (TA, modular input) 50, mixed (sourcetype definitions, modular input) 36, modular input 15, sourcetype definitions 6, mixed (TA, modular input, app UI) 1, mixed (modular input, app UI) 1.

## 2. NetSpout catalog mapping

NetSpout catalog: 88 vendors, 347 products, 349 sourcetypes (docs/reference/sourcetype_coverage.json, reconciled with catalog/vendors.json).

| match type | catalog sourcetypes | meaning |
|---|---|---|
| exact | 126 | name literally defined by a downloaded add-on (file:stanza recorded) |
| conflict | 27 | add-on defines a close but different name, or only renames the catalog's name (naming conflict) |
| candidate | 121 | an add-on names the vendor/product, but none of its sourcetypes corresponds |
| none | 75 | no downloaded add-on covers the vendor |

| measure | value |
|---|---|
| exact matches with a payload-format conflict | 11 |
| exact matches with a routing (metric/event) conflict | 3 |
| naming conflicts | 27 |
| catalog sourcetypes with a generator that really produces events | 244 of 349 |
| ...of which exact matches | 95 |
| sample-backed catalog sourcetypes (shipped YAML or external corpus) | 235 |
| format verification | NOT_APPLICABLE 214, NOT_CHECKABLE 38, FORMAT_VERIFIED 16, FORMAT_PARTIAL 35, STRUCTURE_ONLY 35, FORMAT_CONFLICT 11 |
| ingestion support of the exact matches | SUPPORTED_DELIVERY 40, SUBSTITUTE_VIA_HEC 85, NOT_EMULATED 1 |
| live Splunk-verified (Phase 4 evidence only) | 4 |
| catalog sourcetypes with no covering package | 75 |
| catalog sourcetypes not defined by any package | 223 |
| TA sourcetype names absent from the NetSpout catalog | 1499 |

Live-verified (unchanged, evidence in docs/verification/evidence/ta_compat): cisco:asa (Splunk_TA_cisco-asa 6.1.2), cisco:ios (TA_cisco_catalyst 4.0.60), fortigate_traffic (Splunk_TA_fortinet_fortigate 1.6.10), pan:traffic (Splunk_TA_paloalto_networks 4.0.0).

Reconciliation with Phase 4: the 14 Phase 4 packages define 89 catalog names; Phase 5 finds the same 89 (equal=True). Phase 5 re-classifies add-on legacy names that the add-on renames as naming conflicts, so its exact count is lower than Phase 4's literal-name count.

## 3. Ingestion mechanisms (per app identity; config-declared first, README mentions are weaker evidence)

| mechanism category | app identities |
|---|---|
| REST/API modular input | 95 |
| not declared by the package (operator chooses syslog, file or HEC) | 42 |
| syslog/file | 21 |
| scripted input | 13 |
| HEC | 12 |
| cloud service pull | 9 |
| database (JDBC/DB Connect) | 5 |
| metrics | 5 |
| NetFlow/IPFIX | 2 |

NetSpout delivers HEC JSON events/metrics and syslog, and has NetFlow/IPFIX, SNMP and gNMI exporters. It does not emulate vendor REST APIs, host agents, scripted inputs, JDBC or the Stream collector. `SUBSTITUTE_VIA_HEC` means the add-on's real input is one of those and NetSpout could only deliver equivalent events over HEC; it does not mean the integration works.

Routing conflicts (catalog promises a metric index, add-on defines an event sourcetype): `cisco:intersight:metrics`, `cisco:thousandeyes:metric`, `vmware:perf:cpu`.

## 4. Vendor coverage

| vendor | products | ST | add-ons | exact | naming conf. | payload/route conf. | valid gen. | sample | live | specialized ingest | main blockers |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A10 Networks | 2 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | no downloaded add-on covers this vendor; 2 sourcetypes have no working generator |
| Amazon Web Services | 4 | 4 | 2 | 4 | 0 | 0 | 0 | 4 | 0 | 2 | no exact match live-verified; 4 sourcetypes have no working generator |
| Arista Networks | 4 | 4 | 1 | 0 | 0 | 0 | 3 | 3 | 0 | 0 | covering add-on defines none of the catalog's sourcetype names; 1 sourcetypes have no working generator |
| Aruba / HPE | 6 | 6 | 1 | 3 | 1 | 0 | 4 | 4 | 0 | 0 | 1 naming conflicts; no exact match live-verified; 2 sourcetypes have no working generator |
| Atlassian | 1 | 1 | 2 | 1 | 0 | 0 | 1 | 0 | 0 | 1 | no exact match live-verified |
| Barracuda Networks | 1 | 1 | 1 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | covering add-on defines none of the catalog's sourcetype names |
| BeyondTrust | 1 | 1 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | no downloaded add-on covers this vendor |
| Bitdefender | 1 | 1 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | no downloaded add-on covers this vendor |
| Check Point Software | 3 | 3 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | no downloaded add-on covers this vendor; 2 sourcetypes have no working generator |
| Cisco Duo | 10 | 10 | 1 | 7 | 1 | 1 | 8 | 9 | 0 | 10 | 1 naming conflicts; 1 exact matches with payload/routing conflicts; no exact match live-verified; 2 sourcetypes have no working generator |
| Cisco Meraki | 17 | 17 | 1 | 14 | 0 | 0 | 14 | 14 | 0 | 17 | no exact match live-verified; 3 sourcetypes have no working generator |
| Cisco Systems | 8 | 8 | 0 | 0 | 0 | 0 | 6 | 6 | 0 | 0 | no downloaded add-on covers this vendor; 2 sourcetypes have no working generator |
| Cisco Systems | 6 | 6 | 2 | 5 | 1 | 0 | 2 | 3 | 1 | 1 | 1 naming conflicts; 4 sourcetypes have no working generator |
| Cisco Systems | 34 | 34 | 1 | 17 | 2 | 0 | 32 | 32 | 0 | 33 | 2 naming conflicts; no exact match live-verified; 2 sourcetypes have no working generator |
| Cisco Systems | 11 | 11 | 1 | 11 | 0 | 2 | 10 | 11 | 0 | 11 | 2 exact matches with payload/routing conflicts; no exact match live-verified; 1 sourcetypes have no working generator |
| Cisco Systems | 26 | 26 | 1 | 13 | 5 | 2 | 14 | 18 | 1 | 23 | 5 naming conflicts; 2 exact matches with payload/routing conflicts; 12 sourcetypes have no working generator |
| Cisco Systems | 7 | 7 | 2 | 5 | 0 | 0 | 6 | 7 | 0 | 4 | no exact match live-verified; 1 sourcetypes have no working generator |
| Cisco Systems | 41 | 41 | 1 | 8 | 2 | 1 | 40 | 40 | 0 | 37 | 2 naming conflicts; 1 exact matches with payload/routing conflicts; no exact match live-verified; 1 sourcetypes have no working generator |
| Citrix / Cloud Software Group | 2 | 2 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 1 | 1 naming conflicts; no exact match live-verified; 2 sourcetypes have no working generator |
| Claroty | 1 | 1 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | no downloaded add-on covers this vendor |
| Cloudflare | 3 | 3 | 2 | 1 | 1 | 0 | 2 | 2 | 0 | 3 | 1 naming conflicts; no exact match live-verified; 1 sourcetypes have no working generator |
| CrowdStrike | 1 | 1 | 4 | 1 | 0 | 1 | 1 | 1 | 0 | 1 | 1 exact matches with payload/routing conflicts; no exact match live-verified |
| CrushFTP | 1 | 1 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | no downloaded add-on covers this vendor |
| Cybereason | 1 | 1 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | no downloaded add-on covers this vendor |
| Darktrace | 1 | 1 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | no downloaded add-on covers this vendor |
| Dell Technologies | 1 | 1 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | no downloaded add-on covers this vendor |
| Docker | 1 | 1 | 1 | 0 | 0 | 0 | 1 | 0 | 0 | 1 | covering add-on defines none of the catalog's sourcetype names |
| Elastic | 1 | 1 | 1 | 1 | 0 | 0 | 1 | 0 | 0 | 1 | no exact match live-verified |
| ExtraHop Networks | 2 | 2 | 1 | 0 | 0 | 0 | 2 | 2 | 0 | 2 | covering add-on defines none of the catalog's sourcetype names |
| Extreme Networks | 2 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | no downloaded add-on covers this vendor; 2 sourcetypes have no working generator |
| F5 Networks | 2 | 2 | 1 | 1 | 0 | 1 | 2 | 2 | 0 | 1 | 1 exact matches with payload/routing conflicts; no exact match live-verified |
| Forcepoint | 2 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | no downloaded add-on covers this vendor; 2 sourcetypes have no working generator |
| Fortinet | 7 | 8 | 1 | 2 | 2 | 0 | 5 | 5 | 1 | 0 | 2 naming conflicts; 3 sourcetypes have no working generator |
| GitHub | 1 | 1 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | no downloaded add-on covers this vendor |
| GitLab | 1 | 1 | 3 | 1 | 0 | 0 | 1 | 0 | 0 | 0 | no exact match live-verified |
| Google Cloud | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | covering add-on defines none of the catalog's sourcetype names; 1 sourcetypes have no working generator |
| Google Workspace | 2 | 2 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 2 | no exact match live-verified; 2 sourcetypes have no working generator |
| HashiCorp | 1 | 1 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | no downloaded add-on covers this vendor |
| Huawei Technologies | 2 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | no downloaded add-on covers this vendor; 2 sourcetypes have no working generator |
| IBM | 1 | 1 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | no downloaded add-on covers this vendor |
| IBM MQ | 1 | 1 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | no downloaded add-on covers this vendor |
| Imperva | 1 | 1 | 1 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | covering add-on defines none of the catalog's sourcetype names |
| Juniper Networks | 3 | 3 | 1 | 0 | 1 | 0 | 3 | 3 | 0 | 0 | covering add-on defines none of the catalog's sourcetype names; 1 naming conflicts |
| Kubernetes & Falco (CNCF) | 2 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | no downloaded add-on covers this vendor; 2 sourcetypes have no working generator |
| Linux Infrastructure | 4 | 4 | 1 | 3 | 0 | 0 | 0 | 3 | 0 | 2 | no exact match live-verified; 4 sourcetypes have no working generator |
| Microsoft 365 | 4 | 4 | 3 | 3 | 0 | 0 | 0 | 2 | 0 | 4 | no exact match live-verified; 4 sourcetypes have no working generator |
| Microsoft Azure Monitor | 2 | 2 | 2 | 2 | 0 | 0 | 0 | 1 | 0 | 2 | no exact match live-verified; 2 sourcetypes have no working generator |
| Microsoft Windows | 8 | 8 | 3 | 0 | 5 | 0 | 0 | 2 | 0 | 3 | covering add-on defines none of the catalog's sourcetype names; 5 naming conflicts; 8 sourcetypes have no working generator |
| MikroTik | 1 | 1 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | no downloaded add-on covers this vendor |
| Model Context Protocol (agentic AI) | 1 | 1 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | no downloaded add-on covers this vendor |
| MongoDB | 1 | 1 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | no downloaded add-on covers this vendor |
| NetScout Systems | 1 | 1 | 1 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | covering add-on defines none of the catalog's sourcetype names |
| Netskope | 4 | 4 | 1 | 0 | 2 | 0 | 2 | 2 | 0 | 4 | covering add-on defines none of the catalog's sourcetype names; 2 naming conflicts; 2 sourcetypes have no working generator |
| NGINX (F5) | 2 | 2 | 1 | 1 | 1 | 0 | 2 | 1 | 0 | 1 | 1 naming conflicts; no exact match live-verified |
| Nokia | 3 | 3 | 0 | 0 | 0 | 0 | 2 | 2 | 0 | 0 | no downloaded add-on covers this vendor; 1 sourcetypes have no working generator |
| Nozomi Networks | 1 | 1 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | no downloaded add-on covers this vendor |
| Nutanix | 16 | 16 | 0 | 0 | 0 | 0 | 10 | 14 | 0 | 0 | no downloaded add-on covers this vendor; 6 sourcetypes have no working generator |
| Okta | 1 | 1 | 1 | 1 | 0 | 0 | 1 | 1 | 0 | 1 | no exact match live-verified |
| Ollama (local LLM runtime) | 1 | 1 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | no downloaded add-on covers this vendor |
| OpenTelemetry | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | covering add-on defines none of the catalog's sourcetype names; 1 sourcetypes have no working generator |
| Oracle | 1 | 1 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | no downloaded add-on covers this vendor |
| osquery | 1 | 1 | 1 | 1 | 0 | 1 | 1 | 1 | 0 | 1 | 1 exact matches with payload/routing conflicts; no exact match live-verified |
| Palo Alto Networks | 5 | 5 | 1 | 4 | 0 | 0 | 3 | 3 | 1 | 1 | 2 sourcetypes have no working generator |
| pfSense (Netgate) | 1 | 1 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | no downloaded add-on covers this vendor |
| Proofpoint | 1 | 1 | 4 | 0 | 0 | 0 | 1 | 0 | 0 | 1 | covering add-on defines none of the catalog's sourcetype names |
| Qualys | 1 | 1 | 1 | 0 | 0 | 0 | 1 | 0 | 0 | 1 | covering add-on defines none of the catalog's sourcetype names |
| Radware | 3 | 4 | 0 | 0 | 0 | 0 | 2 | 2 | 0 | 0 | no downloaded add-on covers this vendor; 2 sourcetypes have no working generator |
| Rapid7 | 1 | 1 | 2 | 1 | 0 | 0 | 1 | 0 | 0 | 0 | no exact match live-verified |
| SailPoint | 1 | 1 | 1 | 1 | 0 | 0 | 1 | 0 | 0 | 1 | no exact match live-verified |
| SentinelOne | 1 | 1 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | no downloaded add-on covers this vendor |
| Slack | 1 | 1 | 1 | 1 | 0 | 0 | 1 | 1 | 0 | 1 | no exact match live-verified |
| SonicWall | 1 | 1 | 1 | 0 | 0 | 0 | 1 | 0 | 0 | 1 | covering add-on defines none of the catalog's sourcetype names |
| Sophos | 2 | 2 | 3 | 1 | 0 | 0 | 1 | 1 | 0 | 0 | no exact match live-verified; 1 sourcetypes have no working generator |
| Splunk / Native | 21 | 21 | 3 | 2 | 0 | 0 | 16 | 18 | 0 | 1 | no exact match live-verified; 5 sourcetypes have no working generator |
| Splunk Community / SC4SNMP | 6 | 6 | 0 | 0 | 0 | 0 | 5 | 5 | 0 | 0 | no downloaded add-on covers this vendor; 1 sourcetypes have no working generator |
| Suricata (OISF) | 1 | 1 | 1 | 1 | 0 | 1 | 1 | 1 | 0 | 0 | 1 exact matches with payload/routing conflicts; no exact match live-verified |
| Symantec (Broadcom), Web & Network Security | 1 | 1 | 3 | 1 | 0 | 0 | 1 | 0 | 0 | 0 | no exact match live-verified |
| Sysdig | 1 | 1 | 1 | 1 | 0 | 1 | 1 | 0 | 0 | 0 | 1 exact matches with payload/routing conflicts; no exact match live-verified |
| Tanium | 1 | 1 | 1 | 1 | 0 | 1 | 1 | 0 | 0 | 0 | 1 exact matches with payload/routing conflicts; no exact match live-verified |
| Tenable | 1 | 1 | 1 | 1 | 0 | 1 | 1 | 0 | 0 | 1 | 1 exact matches with payload/routing conflicts; no exact match live-verified |
| Traefik Labs | 1 | 1 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | no downloaded add-on covers this vendor |
| Trellix (formerly McAfee) | 1 | 1 | 1 | 0 | 0 | 0 | 1 | 0 | 0 | 1 | covering add-on defines none of the catalog's sourcetype names |
| Veeam | 1 | 1 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | no downloaded add-on covers this vendor |
| VMware by Broadcom | 4 | 4 | 5 | 2 | 0 | 1 | 0 | 1 | 0 | 0 | 1 exact matches with payload/routing conflicts; no exact match live-verified; 4 sourcetypes have no working generator |
| WatchGuard | 2 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | no downloaded add-on covers this vendor; 2 sourcetypes have no working generator |
| Wazuh | 1 | 1 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | no downloaded add-on covers this vendor |
| Zeek (Bro) | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | no downloaded add-on covers this vendor; 1 sourcetypes have no working generator |
| Zscaler | 6 | 6 | 1 | 1 | 2 | 0 | 3 | 4 | 0 | 5 | 2 naming conflicts; no exact match live-verified; 3 sourcetypes have no working generator |

Vendors with no downloaded add-on: 35 of 88.

## 5. Top 10 next integrations to repair

Ranking: exact name, working generator and a replayable sample or native generator, delivery NetSpout already performs, scenario references, then risk. Number of sourcetypes an add-on defines is not a factor. None is verified; each is a candidate for the Phase 4 method (spec, one add-on at a time in the validation lab).

| # | integration | add-on | ready sourcetypes (first 4) | evidence | complexity | risks |
|---|---|---|---|---|---|---|
| 1 | Cisco Systems | TA_cisco_catalyst 4.0.60 | cisco:sdwan:linkhealth, cisco:sdwan:sitehealth, cisco:sdwan:ssetunnels, cisco:sdwan:syslog (+3) | exact names defined at default/props.conf:[cisco:sdwan:linkhealth] in cisco-enterprise-networking-add-on-for-splunk_4060.tgz; NetSpout generator output produced for each; rendered events checked against the add-on's own extractions (2 FORMAT_VERIFIED, 5 partial/structure-only) | Low | JSON structure only; field names not yet compared to the add-on |
| 2 | Palo Alto Networks | Splunk_TA_paloalto_networks 4.0.0 | pan:system, pan:threat | exact names defined at default/props.conf:[pan_system] rename in splunk-add-on-for-palo-alto-networks_400.spl; NetSpout generator output produced for each; rendered events checked against the add-on's own extractions (2 FORMAT_VERIFIED, 0 partial/structure-only) | Low | none found |
| 3 | Aruba / HPE | TA-aruba_networks 1.1.2 | aruba, aruba:authmgr, aruba:stm | exact names defined at default/props.conf:[aruba:syslog] rename in aruba-networks-add-on-for-splunk_112.tgz; NetSpout generator output produced for each; rendered events checked against the add-on's own extractions (2 FORMAT_VERIFIED, 0 partial/structure-only) | Low | the add-on defines no extraction rules to check against for some sourcetypes |
| 4 | Cisco Systems | TA_cisco_catalyst 4.0.60 | cisco:ise:radius:authz:policy, cisco:ise:radius:policyset, cisco:ise:syslog, cisco:ise:tacacs:authz:policy (+1) | exact names defined at default/props.conf:[cisco:ise:radius:authz:policy] in cisco-enterprise-networking-add-on-for-splunk_4060.tgz; NetSpout generator output produced for each; rendered events checked against the add-on's own extractions (1 FORMAT_VERIFIED, 4 partial/structure-only) | Low | some sourcetypes emit fewer columns than the add-on lists |
| 5 | Cisco Systems | CiscoSecurityCloud 3.7.3 | cisco:ftd:syslog | exact names defined at default/props.conf:[cisco:ftd:syslog] in cisco-security-cloud_373.tar.gz; NetSpout generator output produced for each; rendered events checked against the add-on's own extractions (1 FORMAT_VERIFIED, 0 partial/structure-only) | Low | none found |
| 6 | Fortinet | Splunk_TA_fortinet_fortigate 1.6.10 | fortigate_event | exact names defined at default/props.conf:[fortigate_event] in fortinet-fortigate-add-on-for-splunk_1610.tar.gz; NetSpout generator output produced for each; rendered events checked against the add-on's own extractions (1 FORMAT_VERIFIED, 0 partial/structure-only) | Low | none found |
| 7 | NGINX (F5) | Splunk_TA_nginx 3.3.2 | nginx:plus:access | exact names defined at default/props.conf:[nginx:plus:access] in splunk-add-on-for-nginx_332.spl; NetSpout generator output produced for each; rendered events checked against the add-on's own extractions (1 FORMAT_VERIFIED, 0 partial/structure-only) | Low | none found |
| 8 | Cisco Systems | Splunk_TA_Cisco_Intersight 3.2.2 | cisco:intersight:advisories, cisco:intersight:alarms, cisco:intersight:auditrecords, cisco:intersight:contracts (+5) | exact names defined at default/props.conf:[cisco:intersight:advisories] in cisco-intersight-add-on-for-splunk_322.spl; NetSpout generator output produced for each; rendered events checked against the add-on's own extractions (1 FORMAT_VERIFIED, 8 partial/structure-only) | Medium | JSON structure only; field names not yet compared to the add-on; the add-on's real input is an API/agent/script: NetSpout can only deliver the events over HEC |
| 9 | Symantec (Broadcom), Web & Network Security | Splunk_TA_bluecoat-proxysg 3.9.0 | bluecoat:proxysg:access:file | exact names defined at default/props.conf:[bluecoat:proxysg:access:file] in splunk-add-on-for-symantec-blue-coat-proxysg_390.tgz; NetSpout generator output produced for each; rendered events checked against the add-on's own extractions (1 FORMAT_VERIFIED, 0 partial/structure-only) | Low | none found |
| 10 | Okta | Splunk_TA_okta_identity_cloud 5.1.0 | OktaIM2:log | exact names defined at default/props.conf:[OktaIM2:log] in splunk-add-on-for-okta-identity-cloud_510.spl; NetSpout generator output produced for each; rendered events checked against the add-on's own extractions (1 FORMAT_VERIFIED, 0 partial/structure-only) | Medium | the add-on's real input is an API/agent/script: NetSpout can only deliver the events over HEC |

Files: master_matrix.json/.csv, vendor_coverage.json/.csv, sourcetype_mismatches.json, ingestion_classification.json, top10_shortlist.json, package_inventory.json/.csv, ta_sourcetype_index.csv (every TA sourcetype with its defining file:stanza).

## 6. Limitations

- The inventory reads configuration only. No package was installed or executed, so modular-input behaviour, lookups' contents, scripts and search-time behaviour were not observed.
- Sourcetype lists come from props.conf stanzas, transforms.conf routing rules, inputs.conf and rename targets. Sourcetypes assigned inside modular-input code (bin/) are not visible; the true list for API add-ons can be larger.
- Catalog-vendor to add-on mapping is a by-name identification (VENDOR_PACKAGES in scripts/build_phase5_matrix.py). It yields `candidate`, never a support claim; `exact` needs a defined sourcetype.
- 'Distinct vendors by monitored product' uses rules over app labels (scripts/build_phase5_matrix.py); publishers in app.conf are inconsistent, so both numbers are given.
- FORMAT_VERIFIED means NetSpout's rendered events satisfy the add-on's own regex/DELIMS extractions as evaluated by Python `re` (a stand-in for Splunk's PCRE); STRUCTURE_ONLY means JSON parses but field names were not compared; none of this is live evidence.
- Ingestion support is inferred from inputs.conf stanza types, README mentions and sourcetype shape. A README that only mentions OpenTelemetry/CEF as framework boilerplate is ignored unless the app is a telemetry collector.
- CIM data-model validation, non-UTC time zones, and every sourcetype other than the four Phase 4 integrations remain unverified in Splunk.
- Catalog metadata quirks are reported, not fixed (for example, `cisco:sdwan:sytem:logs` and `cisco:sdwan:system:logs` both exist; Windows data uses sourcetype `XmlWinEventLog` with source `XmlWinEventLog:Security`).
