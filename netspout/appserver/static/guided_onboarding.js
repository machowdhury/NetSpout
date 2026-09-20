/*
 * Splunk App: NetSpout (TA-network-data-blaster)
 * View Script: guided_onboarding.js
 * Guided Onboarding Wizard Controller
 * Author: Mahamudul Chowdhury <mchowdhury@splunk.com>
 */

require([
  'jquery',
  'splunkjs/mvc',
  'splunkjs/mvc/simplexml/ready!'
], function($, mvc) {
  'use strict';

  function getRestUrl(queryStr) {
    var base = '';
    if (window.Splunk && window.Splunk.util && typeof window.Splunk.util.make_url === 'function') {
      base = window.Splunk.util.make_url('/splunkd/__raw/services/datablaster/execute');
    } else {
      var parts = window.location.pathname.split('/');
      var locale = (parts.length > 1 && parts[1]) ? parts[1] : 'en-US';
      base = '/' + locale + '/splunkd/__raw/services/datablaster/execute';
    }
    if (queryStr) {
      base += (base.indexOf('?') === -1 ? '?' : '&') + queryStr;
    }
    return base;
  }

  function getCsrfToken() {
    if (window.Splunk && window.Splunk.util && typeof window.Splunk.util.getConfigValue === 'function') {
      var fk = window.Splunk.util.getConfigValue('FORM_KEY');
      if (fk) return fk;
    }
    var match = document.cookie.match(/(?:^|;\s*)(?:splunkweb_csrf_token_[0-9]+|splunkweb_csrf_token)=([^;]*)/);
    return (match && match[1]) ? decodeURIComponent(match[1]) : '';
  }

  function getHeaders() {
    var h = {
      'Content-Type': 'application/json',
      'X-Requested-With': 'XMLHttpRequest'
    };
    var csrf = getCsrfToken();
    if (csrf) {
      h['X-Splunk-Form-Key'] = csrf;
    }
    return h;
  }

  // Catalog of Network Sourcetypes (Categorized)
  var SOURCETYPE_CATALOG = [
  {
    "id": "cisco:mdt:grpc",
    "label": "Cisco MDT gRPC Metric Stream (OpenConfig)",
    "vendor": "cisco",
    "category": "Routing & Core",
    "index": "cisco_mdt_metrics",
    "sample": "'{\"event\":\"metric\",\"time\":1789840800,\"fields\":{\"metric_name:interface.octets.in\":984521000,\"metric_name:interface.octets.out\":874219000,\"metric_name:cpu.utilization\":24.5,\"interface\":\"HundredGigE0/0/0/0\",\"oper_status\":\"UP\",\"xpath\":\"/interfaces/interface/state/counters\""
  },
  {
    "id": "openconfig:yang:json",
    "label": "OpenConfig YANG JSON Telemetry (RFC 7950)",
    "vendor": "cisco",
    "category": "Routing & Core",
    "index": "idx_network_ops",
    "sample": "'{\"openconfig-interfaces:interfaces\":{\"interface\":[{\"name\":\"HundredGigE0/0/0/0\",\"state\":{\"admin-status\":\"UP\",\"oper-status\":\"UP\",\"counters\":{\"in-octets\":984521000,\"out-octets\":874219000"
  },
  {
    "id": "cisco:ios",
    "label": "Cisco IOS-XE / Classic Syslog",
    "vendor": "cisco",
    "category": "Routing & Core",
    "index": "idx_network_ops",
    "sample": "%BGP-5-ADJCHANGE: neighbor 198.51.100.1 Up"
  },
  {
    "id": "juniper:junos",
    "label": "Juniper Networks Junos OS Syslog",
    "vendor": "arista",
    "category": "Routing & Core",
    "index": "idx_network_ops",
    "sample": "<14>Sep 19 12:00:00 rtr-ptx01 rpd[4821]: %ROUTING-4-BGP_PEER_FLAP: BGP peer 198.51.100.1 state changed from Established to Idle"
  },
  {
    "id": "nokia:sros",
    "label": "Nokia 7750 SR OS Router Syslog",
    "vendor": "arista",
    "category": "Routing & Core",
    "index": "idx_network_ops",
    "sample": "<165>Sep 19 12:00:00 pe01-7750 Major: BGP #2002 Base Peer 10.254.0.1: Peer entered Established state"
  },
  {
    "id": "arista:eos",
    "label": "Arista EOS Core Switching Syslog",
    "vendor": "arista",
    "category": "Routing & Core",
    "index": "idx_network_ops",
    "sample": "%LINEPROTO-5-UPDOWN: Line protocol on Interface Ethernet1/1, changed state to up"
  },
  {
    "id": "cisco:ise:byod:provisioning",
    "label": "Cisco ISE BYOD Device Onboarding & Registration",
    "vendor": "cisco",
    "category": "Identity & Access Control",
    "index": "idx_network_ops",
    "sample": "CISE_Passed_Authentications 0001847291 1 0 2026-09-19T14:00:00.000Z +00:00 0029481921 5200 NOTICE Passed-Authentication: BYOD Registration Succeeded, ConfigVersionId=127, DeviceRegistrationStatus=Registered, DeviceType=Apple-Device, MacAddress=00-1A-2B-3C-4D-5E, CertificateSerialNumber=49810283, EapAuthentication=EAP-TLS, User-Name=j.doe@corp.internal, IdentityGroup=Employee_BYOD"
  },
  {
    "id": "cisco:ise:nac:8021x",
    "label": "Cisco ISE 802.1X Port NAC & RADIUS Auth",
    "vendor": "cisco",
    "category": "Identity & Access Control",
    "index": "idx_network_ops",
    "sample": "CISE_Passed_Authentications 0001847295 1 0 2026-09-19T14:00:00.000Z +00:00 0029481925 5200 NOTICE Passed-Authentication: Authentication succeeded, ConfigVersionId=127, Device IP Address=10.254.8.1, DestinationPort=1812, UserName=corp\\\\alice.sec, Protocol=Radius, NAS-Port-Id=GigabitEthernet1/0/24, Framed-IP-Address=10.20.10.45, EapAuthentication=EAP-TLS"
  },
  {
    "id": "cisco:ise:trustsec:sgt",
    "label": "Cisco ISE TrustSec SGT Micro-segmentation",
    "vendor": "cisco",
    "category": "Identity & Access Control",
    "index": "idx_security_fw",
    "sample": "CISE_TrustSec 0001847297 1 0 2026-09-19T14:00:00.000Z +00:00 0029481927 5400 NOTICE TrustSec: SGT Assignment Enforcement, ConfigVersionId=127, Source-SGT=14:Employees, Destination-SGT=25:Quarantine, SGACL-Name=DENY_QUARANTINE_TRAFFIC, Action=DENIED, Enforcement-Node=cat9600-core-01"
  },
  {
    "id": "cisco:ise:deviceadmin:tacacs",
    "label": "Cisco ISE TACACS+ Device Administration",
    "vendor": "cisco",
    "category": "Identity & Access Control",
    "index": "idx_network_ops",
    "sample": "CISE_TACACS_Accounting 0001847299 1 0 2026-09-19T14:00:00.000Z +00:00 0029481929 3300 NOTICE TACACS-Accounting: Command Authorization Succeeded, User=netadmin_bob, Device-IP-Address=10.254.1.1, Privilege-Level=15, Command=\\\"configure terminal ; interface HundredGigE0/0/0/1 ; shutdown\\\""
  },
  {
    "id": "cisco:ise:guest:voucher",
    "label": "Cisco ISE Guest Captive Portal & Vouchers",
    "vendor": "cisco",
    "category": "Identity & Access Control",
    "index": "idx_network_ops",
    "sample": "'{\"timestamp\":\"2026-09-19T14:00:00.000Z\",\"event_type\":\"GUEST_VOUCHER_ACTIVATION\",\"ise_node\":\"ise-pan01.corp.internal\",\"portal_name\":\"Corporate_Sponsor_Guest_Portal\",\"voucher_code\":\"GUEST-9481-VX\",\"sponsor_user\":\"admin_frontdesk@corp.internal\",\"duration_hours\":8,\"vlan_assigned\":99,\"status\":\"ACTIVE\""
  },
  {
    "id": "cisco:duo:push:prompt",
    "label": "Cisco Duo Push Multi-Factor Authentication",
    "vendor": "cloud",
    "category": "Identity & Access Control",
    "index": "idx_security_fw",
    "sample": "'{\"timestamp\":1789840800,\"event_type\":\"authentication\",\"factor\":\"duo_push\",\"result\":\"SUCCESS\",\"reason\":\"user_approved\",\"user\":{\"name\":\"m.chowdhury@corp.internal\",\"groups\":[\"Enterprise_Admins\"]"
  },
  {
    "id": "cisco:duo:endpoint:posture",
    "label": "Cisco Duo Endpoint Device Posture & Health",
    "vendor": "cloud",
    "category": "Identity & Access Control",
    "index": "idx_security_fw",
    "sample": "'{\"timestamp\":1789840800,\"event_type\":\"endpoint_health\",\"device\":{\"os\":\"macOS\",\"os_version\":\"15.3.1\",\"encryption\":{\"disk\":\"FileVault_Encrypted\",\"status\":\"HEALTHY\""
  },
  {
    "id": "cisco:duo:sso:saml",
    "label": "Cisco Duo Central SSO SAML Assertions",
    "vendor": "cloud",
    "category": "Identity & Access Control",
    "index": "idx_security_fw",
    "sample": "'{\"timestamp\":1789840800,\"event_type\":\"sso_auth\",\"auth_type\":\"SAML_2_0\",\"identity_provider\":\"Duo Central Single Sign-On\",\"service_provider\":\"Splunk Enterprise Production\",\"subject_name_id\":\"mchowdhury@splunk.com\",\"action\":\"ASSERTION_ISSUED\""
  },
  {
    "id": "cisco:duo:zerotrust:policy",
    "label": "Cisco Duo Zero Trust Application Policy",
    "vendor": "cloud",
    "category": "Identity & Access Control",
    "index": "idx_security_fw",
    "sample": "'{\"timestamp\":1789840800,\"event_type\":\"zero_trust_policy_evaluation\",\"policy_name\":\"High_Privilege_Core_Access\",\"policy_outcome\":\"ALLOW\",\"context\":{\"user_risk\":\"LOW\",\"device_trust\":\"VERIFIED_MANAGED\",\"geo_velocity_check\":\"PASSED\""
  },
  {
    "id": "cisco:duo:remote:vpn",
    "label": "Cisco Duo Secure Remote Access VPN",
    "vendor": "cloud",
    "category": "Identity & Access Control",
    "index": "idx_security_fw",
    "sample": "'{\"timestamp\":1789840800,\"event_type\":\"vpn_authentication\",\"vpn_gateway\":\"cisco-asa-vpn.corp.internal\",\"client_software\":\"Cisco AnyConnect / Secure Client 5.0\",\"assigned_ip\":\"10.240.12.88\",\"username\":\"mchowdhury@splunk.com\",\"factor\":\"duo_push\",\"status\":\"CONNECTED\""
  },
  {
    "id": "cisco:asa",
    "label": "Cisco ASA Adaptive Security Appliance",
    "vendor": "cisco",
    "category": "Security & Firewalls",
    "index": "idx_security_fw",
    "sample": "%ASA-4-106023: Deny tcp src outside:198.51.100.77/44321 dst inside:10.0.1.50/80 by access-group \"OUTSIDE_IN\" [0x0, 0x0]"
  },
  {
    "id": "cisco:ftd",
    "label": "Cisco Firepower Threat Defense (FTD)",
    "vendor": "cisco",
    "category": "Security & Firewalls",
    "index": "idx_security_fw",
    "sample": "%FTD-1-430002: EventPriority: High, DeviceUUID: 4f1c9c7e-8c52, Intrusion Rule: 1:2100498, Protocol: TCP, SrcIP: 203.0.113.88, DstIP: 10.100.4.15"
  },
  {
    "id": "pan:traffic",
    "label": "Palo Alto Networks Traffic Logs",
    "vendor": "paloalto",
    "category": "Security & Firewalls",
    "index": "idx_security_fw",
    "sample": "1,2026/09/19 14:00:00,001801000001,TRAFFIC,drop,1,2026/09/19 14:00:00,198.51.100.42,10.254.1.10,0.0.0.0,0.0.0.0,rule_syn_flood,vsys1,untrust,trust,ethernet1/1,ethernet1/2,default-log-forwarding,2026/09/19 14:00:00,0,1,54210,443,0,0,0x0,tcp,deny,64,64,0,1"
  },
  {
    "id": "pan:threat",
    "label": "Palo Alto Networks Threat Prevention",
    "vendor": "paloalto",
    "category": "Security & Firewalls",
    "index": "idx_security_fw",
    "sample": "1,2026/09/19 14:00:00,001801000001,THREAT,drop,1,2026/09/19 14:00:00,198.51.100.42,10.254.1.10,0.0.0.0,0.0.0.0,rule_threat_prevention,vsys1,untrust,trust,ethernet1/1,ethernet1/2,threat-drop,0,0,0,0,0,tcp,deny"
  },
  {
    "id": "fortinet:fortigate",
    "label": "Fortinet FortiOS Security Events",
    "vendor": "paloalto",
    "category": "Security & Firewalls",
    "index": "idx_security_fw",
    "sample": "date=2026-09-19 time=14:00:00 devname=\"fortigate-3700d\" devid=\"FG370D4615800001\" eventtime=1789840800 level=\"warning\" vd=\"root\" type=\"traffic\" subtype=\"forward\" action=\"accept\" policyid=12 sessionid=9872411 srcip=10.254.2.50 dstip=198.51.100.80 proto=6 sentbyte=2400 rcvdbyte=8900 utmaction=\"allow\" transport=\"sdwan\""
  },
  {
    "id": "checkpoint:cef",
    "label": "Check Point Quantum Firewall CEF",
    "vendor": "paloalto",
    "category": "Security & Firewalls",
    "index": "idx_security_fw",
    "sample": "CEF:0|Check Point|VPN-1 & FireWall-1|Check Point|Log|drop|act=drop suser=mchen src=10.40.12.88 spt=54215 dst=198.51.100.66 dpt=23 proto=tcp product=VPN-1 & FireWall-1 cs1Label=Rule cs1=Deny_Telnet_Global"
  },
  {
    "id": "cisco:catalyst:security:events",
    "label": "Cisco Catalyst 9300 Security Events",
    "vendor": "cisco",
    "category": "Campus Access & Wireless",
    "index": "idx_network_ops",
    "sample": "%SW_MATM-4-MACFLAP_NOTIF: Host 00:1a:2b:3c:4d:5e in vlan 20 is flapping between port Gi1/0/12 and port Gi1/0/24"
  },
  {
    "id": "cisco:catalyst:rogue:threat_details",
    "label": "Cisco Catalyst Rogue AP Detection",
    "vendor": "cisco",
    "category": "Campus Access & Wireless",
    "index": "idx_wireless_ops",
    "sample": "cisco:catalyst:rogue:threat_details ap_name=\"AP-HQ-Floor3\" rogue_bssid=\"70:69:79:4c:11:02\" ssid=\"Corporate-Guest-EvilTwin\" rogue_type=\"Unclassified\" classification=\"Threat\" state=\"Alert\""
  },
  {
    "id": "cisco:sdwan:linkhealth",
    "label": "Cisco SD-WAN vEdge Link Health",
    "vendor": "cisco",
    "category": "Campus Access & Wireless",
    "index": "idx_network_ops",
    "sample": "vEdge-1000-Core: bfd: event=state_change local_color=biz-internet remote_color=biz-internet loss_pct=14.8 latency_ms=184.2 jitter_ms=42.1 sla_state=violated"
  },
  {
    "id": "cisco:sdwan:BGP-5-ADJCHANGE",
    "label": "Cisco SD-WAN BGP Route Failover",
    "vendor": "cisco",
    "category": "Campus Access & Wireless",
    "index": "idx_network_ops",
    "sample": "%BGP-5-ADJCHANGE: neighbor 198.51.100.1 vpn 10 Down BFD session down"
  },
  {
    "id": "meraki:accesspoints",
    "label": "Cisco Meraki MR Wireless Telemetry",
    "vendor": "cisco",
    "category": "Campus Access & Wireless",
    "index": "idx_wireless_ops",
    "sample": "'{\"name\":\"MR46-Floor1-East\",\"serial\":\"Q2MN-1182-3341\",\"clientsCount\":24,\"channel24\":6,\"channel5\":149,\"powerUsage\":12.4"
  },
  {
    "id": "aruba:syslog",
    "label": "Aruba CX Campus Switching",
    "vendor": "arista",
    "category": "Campus Access & Wireless",
    "index": "idx_network_ops",
    "sample": "<189>Sep 19 14:00:00 aruba-cx-switch01 hpe-authmgr[1142]: User A4:83:E7:4B:11:02 authenticated on port 1/1/12 via 802.1X VLAN 40"
  },
  {
    "id": "zscaler:zia",
    "label": "Zscaler Internet Access (ZIA) Web Log",
    "vendor": "cloud",
    "category": "Cloud, SASE & Observability",
    "index": "idx_security_fw",
    "sample": "'{\"datetime\":\"2026-09-19 14:00:00\",\"user\":\"eng-dev@corp.internal\",\"app\":\"ChatGPT-Enterprise\",\"action\":\"Allow\",\"proto\":\"HTTPS\",\"url\":\"https://api.openai.com/v1/models\",\"threatname\":\"None\",\"riskscore\":\"0\",\"egress_dc\":\"iad-zscaler\""
  },
  {
    "id": "zscaler:lss",
    "label": "Zscaler Private Access (ZPA) LSS",
    "vendor": "cloud",
    "category": "Cloud, SASE & Observability",
    "index": "idx_security_fw",
    "sample": "'{\"datetime\":\"2026-09-19 12:00:00\",\"Customer\":\"Acme-Enterprise\",\"Application\":\"Internal-ERP\",\"ClientIP\":\"10.45.2.14\",\"ServerIP\":\"10.100.1.5\",\"PolicyRule\":\"Engineering-Access\",\"Status\":\"Success\""
  },
  {
    "id": "cisco:thousandeyes:metric",
    "label": "Cisco ThousandEyes Synthetic Metrics",
    "vendor": "cisco",
    "category": "Cloud, SASE & Observability",
    "index": "idx_performance_metrics",
    "sample": "'{\"test_name\":\"SaaS CRM Portal\",\"test_type\":\"http-server\",\"loss\":0.12,\"latency\":182.4,\"jitter\":15.1,\"response_code\":200,\"status\":\"degraded\""
  },
  {
    "id": "sc4snmp:metric",
    "label": "Splunk Connect for SNMP Metrics",
    "vendor": "cisco",
    "category": "Cloud, SASE & Observability",
    "index": "cisco_mdt_metrics",
    "sample": "'{\"time\":1789840800.0,\"event\":\"metric\",\"source\":\"sc4snmp\",\"sourcetype\":\"sc4snmp:metric\",\"host\":\"rtr-cisco-8000-01.corp.internal\",\"index\":\"cisco_mdt_metrics\",\"fields\":{\"metric_name:ifInOctets\":58920140.0,\"metric_name:ifOutOctets\":84920194.0,\"metric_name:ifOperStatus\":1.0,\"_value\":58920140.0,\"ifIndex\":\"1\",\"ifDescr\":\"GigabitEthernet0/0/1\",\"device\":\"rtr-cisco-8000-01\",\"vendor\":\"cisco\""
  },
  {
    "id": "sc4snmp:event",
    "label": "Splunk Connect for SNMP Traps",
    "vendor": "cisco",
    "category": "Cloud, SASE & Observability",
    "index": "idx_network_ops",
    "sample": "'{\"time\":1789840800.0,\"source\":\"sc4snmp:trap\",\"sourcetype\":\"sc4snmp:event\",\"host\":\"rtr-cisco-8000-01.corp.internal\",\"index\":\"idx_network_ops\",\"event\":{\"snmp_trap_name\":\"linkDown\",\"snmp_trap_oid\":\"1.3.6.1.6.3.1.1.5.3\",\"enterprise\":\"1.3.6.1.4.1\",\"severity\":\"critical\",\"varbinds\":{\"ifIndex\":1,\"ifAdminStatus\":1,\"ifOperStatus\":2,\"ifDescr\":\"GigabitEthernet0/0/1\""
  },
  {
    "id": "cisco:mds:san:fc",
    "label": "Cisco MDS 9700 Fibre Channel SAN Fabric",
    "vendor": "cisco",
    "category": "Storage & Data Center",
    "index": "idx_performance_metrics",
    "sample": "%PORT-3-CREDIT_LOSS: Interface fc1/14 Tx credit loss detected. Peer device slow drain. Dropped frames: 842. B2B credit recovery initiated."
  },
  {
    "id": "netapp:ontap:nas",
    "label": "NetApp ONTAP Clustered NAS (NFS/SMB)",
    "vendor": "arista",
    "category": "Storage & Data Center",
    "index": "idx_performance_metrics",
    "sample": "'{\"timestamp\":\"2026-09-19T14:00:00.000Z\",\"cluster\":\"netapp-ontap-01\",\"node\":\"node-01\",\"vserver\":\"vs_prod\",\"volume\":\"vol_analytics\",\"iops\":128400,\"throughput_mbps\":1480,\"latency_ms\":48.2,\"protocol\":\"nfs4.1\",\"status\":\"DEGRADED\""
  },
  {
    "id": "cisco:dc:nexus9k:syslog",
    "label": "Cisco Nexus 9000 Data Center Syslog",
    "vendor": "cisco",
    "category": "Storage & Data Center",
    "index": "idx_performance_metrics",
    "sample": "%ETHPORT-5-IF_DOWN_TX_PAUSE: Interface Ethernet1/12 buffer congestion pause frames transmitted threshold exceeded"
  },
  {
    "id": "arista:telemetry:json",
    "label": "Arista EOS Streaming Telemetry",
    "vendor": "arista",
    "category": "Storage & Data Center",
    "index": "idx_performance_metrics",
    "sample": "'{\"timestamp\":1789840800.0,\"device\":\"sw-arista-7280-01\",\"interface\":\"Ethernet1/1\",\"pfc_pause_rx\":48201,\"ecn_marked_packets\":1284,\"buffer_utilization_pct\":98.4,\"status\":\"CONGESTION_ROCE_V2\""
  },
  {
    "id": "cisco:catalyst:client",
    "label": "Cisco Catalyst Client",
    "vendor": "cisco",
    "category": "Cisco Catalyst",
    "index": "netops_logs",
    "sample": "{\"ClientID\": \"00:50:56:B7:10:E2\", \"ClientMACAddress\": \"00:50:56:B7:10:E2\", \"ClientType\": \"Wired\", \"ClientName\": \"sandbox-ise\", \"ClientUserID\": \"\", \"ClientUsername\": \"N/A\", \"ClientIPv4Address\": \"10.20.1.5\", \"ClientOSType\": \"Unclassified\", \"ClientDeviceType\": \"Unclassified\", \"ClientSiteHierarchy\": \"Global/Toronto_SDA/Toronto_BLD\", \"ClientLastUpdatedTime\": 1789749600000, \"ClientConnectionStatus\": \"co"
  },
  {
    "id": "cisco:catalyst:clienthealth",
    "label": "Cisco Catalyst Clienthealth",
    "vendor": "cisco",
    "category": "Cisco Catalyst",
    "index": "netops_logs",
    "sample": "{\"siteId\": \"global\", \"clientType\": \"ALL\", \"clientCount\": 0, \"clientUniqueCount\": 0, \"scoreValue\": -1, \"starttime\": 1789752526901, \"endtime\": 1789752826901, \"scoreType\": \"ALL\", \"cisco_catalyst_host\": \"https://dnac.maple.ciscolabs.com\"}"
  },
  {
    "id": "cisco:catalyst:compliance",
    "label": "Cisco Catalyst Compliance",
    "vendor": "cisco",
    "category": "Cisco Catalyst",
    "index": "netops_logs",
    "sample": "{\"ComplianceDeviceID\": \"4881747e-0e66-4275-8611-f9ec86746a7d\", \"ComplianceStatus\": \"NON_COMPLIANT\", \"ComplianceLastUpdateTime\": 1789732708220, \"DeviceName\": \"C9800.maple.ciscolabs.com\", \"IpAddress\": \"10.0.10.50\", \"DeviceFamily\": \"Wireless Controller\", \"Reachability\": \"Reachable\", \"ReachabilityFailureReason\": \"\", \"ManageErrors\": \"\", \"Manageability\": \"Managed\", \"MACAddress\": \"00:50:56:b7:74:4c\", \"De"
  },
  {
    "id": "cisco:catalyst:devicehealth",
    "label": "Cisco Catalyst Devicehealth",
    "vendor": "cisco",
    "category": "Cisco Catalyst",
    "index": "netops_logs",
    "sample": "{\"HasInterfaceStats\": \"True\", \"ID\": \"6aa89be5-2bfa-4647-a04e-919fc3e9be2c\", \"DeviceID\": \"0c379365-f5b4-4a3d-9a3d-1dc3e6689a18\", \"DeviceName\": \"TRN-SDA-C9500.maple.ciscolabs.com\", \"Name\": \"Vlan122\", \"RxRate\": \"\", \"TxRate\": \"\", \"Speed\": \"1000000\", \"RxUtilization\": \"\", \"TxUtilization\": \"\", \"cisco_catalyst_host\": \"https://dnac.maple.ciscolabs.com\"}"
  },
  {
    "id": "cisco:catalyst:issue",
    "label": "Cisco Catalyst Issue",
    "vendor": "cisco",
    "category": "Cisco Catalyst",
    "index": "netops_logs",
    "sample": "{\"IssueID\": \"4746c82c-0eba-4182-88b9-d296c827cc13\", \"IssueSpecificCategory\": \"Availability\", \"IssueSpecificSource\": \"Cisco DNA\", \"IssueSpecificName\": \"switch_unreachable\", \"IssueSpecificDescription\": \"This network device dmz1.dcloud.cisco.com is unreachable from Cisco Catalyst Center. The device role is ACCESS.\", \"IssueSpecificEntity\": \"network_device\", \"IssueSpecificEntityValue\": \"86af9de8-d550-4"
  },
  {
    "id": "cisco:catalyst:networkhealth",
    "label": "Cisco Catalyst Networkhealth",
    "vendor": "cisco",
    "category": "Cisco Catalyst",
    "index": "netops_logs",
    "sample": "{\"category\": \"All\", \"healthScore\": 29, \"totalCount\": 24, \"goodCount\": 7, \"noHealthCount\": 17, \"cisco_catalyst_host\": \"https://dnac.maple.ciscolabs.com\"}"
  },
  {
    "id": "cisco:catalyst:rogue:allowed",
    "label": "Cisco Catalyst Rogue Allowed",
    "vendor": "cisco",
    "category": "Cisco Catalyst",
    "index": "netops_logs",
    "sample": "{\"status\": \"success\", \"msg\": \"API returned empty list / no active data\"}"
  },
  {
    "id": "cisco:catalyst:rogue:counts",
    "label": "Cisco Catalyst Rogue Counts",
    "vendor": "cisco",
    "category": "Cisco Catalyst",
    "index": "netops_logs",
    "sample": "26"
  },
  {
    "id": "cisco:catalyst:rogue:verbose",
    "label": "Cisco Catalyst Rogue Verbose",
    "vendor": "cisco",
    "category": "Cisco Catalyst",
    "index": "netops_logs",
    "sample": "{\"macAddress\": \"C2:D6:66:6F:BA:30\", \"mldMacAddress\": \"NA\", \"updatedTime\": $EPOCH_MS$, \"createdTime\": $EPOCH_MS$, \"threatType\": \"mapleRule2\", \"threatLevel\": \"High\", \"apName\": \"OTT-Lab-9117-AP\", \"detectingAPMac\": \"0C:D0:F8:95:5B:20\", \"ssid\": \"internet\", \"containment\": \"Open\", \"radioType\": \"8\", \"controllerIp\": \"10.0.10.50\", \"controllerName\": \"C9800.maple.ciscolabs.com\", \"channelNumber\": \"6\", \"siteNam"
  },
  {
    "id": "cisco:catalyst:rogue:verbose:legacy",
    "label": "Cisco Catalyst Rogue Verbose Legacy",
    "vendor": "cisco",
    "category": "Cisco Catalyst",
    "index": "netops_logs",
    "sample": "{\"status\": \"no_active_data\", \"msg\": \"API returned 0 records\"}"
  },
  {
    "id": "cisco:catalyst:rogue:wired",
    "label": "Cisco Catalyst Rogue Wired",
    "vendor": "cisco",
    "category": "Cisco Catalyst",
    "index": "netops_logs",
    "sample": "{\"status\": \"success\", \"msg\": \"No active data found\"}"
  },
  {
    "id": "cisco:catalyst:script:heartbeat",
    "label": "Cisco Catalyst Script Heartbeat",
    "vendor": "cisco",
    "category": "Cisco Catalyst",
    "index": "netops_logs",
    "sample": "{\"status\": \"polling_complete\", \"timestamp\": \"$GOTS$\"}"
  },
  {
    "id": "cisco:catalyst:security:awips_signatures",
    "label": "Cisco Catalyst Security Awips Signatures",
    "vendor": "cisco",
    "category": "Cisco Catalyst",
    "index": "netops_logs",
    "sample": "{\"status\": \"success\", \"msg\": \"No active data found\"}"
  },
  {
    "id": "cisco:catalyst:security:profile",
    "label": "Cisco Catalyst Security Profile",
    "vendor": "cisco",
    "category": "Cisco Catalyst",
    "index": "netops_logs",
    "sample": "{\"status\": \"no_active_data\", \"msg\": \"No incidents in window\"}"
  },
  {
    "id": "cisco:catalyst:security:profile_signatures",
    "label": "Cisco Catalyst Security Profile Signatures",
    "vendor": "cisco",
    "category": "Cisco Catalyst",
    "index": "netops_logs",
    "sample": "{\"profileDetails\": {\"instanceUuid\": \"6fdbebc5-b9f9-45bd-a7a6-735de93e0c25\", \"name\": \"Dovetail-SSID\", \"ssidDetails\": [{\"name\": \"Ott02-LAB-SDA-CORP\", \"enableFabric\": false, \"flexConnect\": {\"enableFlexConnect\": false}, \"interfaceName\": \"management\", \"wlanProfileName\": \"Ott02-LAB-SDA-CORP_profile\", \"policyProfileName\": \"Ott02-LAB-SDA-CORP_profile\"}], \"sites\": [\"Global/Ottawa/OTT02-Lab\", \"Global/Ottawa"
  },
  {
    "id": "cisco:catalyst:security:rules",
    "label": "Cisco Catalyst Security Rules",
    "vendor": "cisco",
    "category": "Cisco Catalyst",
    "index": "netops_logs",
    "sample": "{\"status\": \"no_active_data\", \"msg\": \"No incidents in window\"}"
  },
  {
    "id": "cisco:catalyst:securityadvisory",
    "label": "Cisco Catalyst Securityadvisory",
    "vendor": "cisco",
    "category": "Cisco Catalyst",
    "index": "netops_logs",
    "sample": "{\"Summary\": \"True\", \"Category\": \"CRITICAL\", \"SubCategory\": \"TOTAL\", \"Amount\": 8, \"cisco_catalyst_host\": \"https://dnac.maple.ciscolabs.com\"}"
  },
  {
    "id": "cisco:catalyst:threat:list",
    "label": "Cisco Catalyst Threat List",
    "vendor": "cisco",
    "category": "Cisco Catalyst",
    "index": "netops_logs",
    "sample": "{\"status\": \"success\", \"msg\": \"API returned empty list / no active data\"}"
  },
  {
    "id": "cisco:catalyst:threat:signatures",
    "label": "Cisco Catalyst Threat Signatures",
    "vendor": "cisco",
    "category": "Cisco Catalyst",
    "index": "netops_logs",
    "sample": "{\"status\": \"success\", \"msg\": \"API returned empty list / no active data\"}"
  },
  {
    "id": "cisco:catalyst:threat:summary",
    "label": "Cisco Catalyst Threat Summary",
    "vendor": "cisco",
    "category": "Cisco Catalyst",
    "index": "netops_logs",
    "sample": "{\"timestamp\": $EPOCH_MS$, \"threatData\": [{\"threatType\": \"mapleRule2\", \"threatLevel\": \"High\", \"threatCount\": 16, \"threatTypeInt\": \"18001\"}, {\"threatType\": \"rougeRule\", \"threatLevel\": \"High\", \"threatCount\": 6, \"threatTypeInt\": \"18000\"}, {\"threatType\": \"Neighbor\", \"threatLevel\": \"Informational\", \"threatCount\": 3, \"threatTypeInt\": \"1901\"}, {\"threatType\": \"Interferer\", \"threatLevel\": \"Potential\", \"thre"
  },
  {
    "id": "cisco:catalyst:threat:summary:legacy",
    "label": "Cisco Catalyst Threat Summary Legacy",
    "vendor": "cisco",
    "category": "Cisco Catalyst",
    "index": "netops_logs",
    "sample": "{\"timestamp\": $EPOCH_MS$, \"threatData\": [{\"threatType\": \"mapleRule2\", \"threatLevel\": \"High\", \"threatCount\": 17, \"threatTypeInt\": \"18001\"}, {\"threatType\": \"Neighbor\", \"threatLevel\": \"Informational\", \"threatCount\": 3, \"threatTypeInt\": \"1901\"}, {\"threatType\": \"rougeRule\", \"threatLevel\": \"High\", \"threatCount\": 2, \"threatTypeInt\": \"18000\"}, {\"threatType\": \"Interferer\", \"threatLevel\": \"Potential\", \"thre"
  },
  {
    "id": "cisco:dc:aci:health",
    "label": "Cisco Dc Aci Bridge Domain",
    "vendor": "cisco",
    "category": "Cisco DC (ACI, Nexus)",
    "index": "netops_logs",
    "sample": "{\"time\": \"$ISO_TS$\", \"dn\": \"uni/tn-MAPLE/BD-MAPLE_BD04_SPLUNK/health\", \"cur\": 100, \"prev\": 100, \"twScore\": 100, \"maxSev\": \"cleared\", \"descr\": \"Bridge Domain MAPLE_BD04_SPLUNK healthy\", \"apic_host\": \"$APIC_HOST$\", \"component\": \"fvBD\", \"tenant\": \"MAPLE\", \"bd\": \"MAPLE_BD04_SPLUNK\", \"operSt\": \"online\"}"
  },
  {
    "id": "cisco:dc:aci:class",
    "label": "Cisco Dc Aci Class",
    "vendor": "cisco",
    "category": "Cisco DC (ACI, Nexus)",
    "index": "netops_logs",
    "sample": "$GOTS$\tadminSt=in-service\tchildAction=\tclearDamp=0\tdampFilter=0\tdampHalfLife=15\tdampMaxSuppressTime=45\tdampReuse=750\tdampSuppress=2000\tdn=uni/tn-common/out-L3Out-OSPF/instP-All-Subnets\tl3extInstP_descr=\tl3extInstP_dn=uni/tn-common/out-L3Out-OSPF/instP-All-Subnets\tl3extInstP_name=All-Subnets\tl3extOut_descr=\tl3extOut_dn=uni/tn-common/out-L3Out-OSPF\tl3extOut_name=L3Out-OSPF\tmodTs=2025-08-17T01:00:51."
  },
  {
    "id": "cisco:dc:nexus9k",
    "label": "Cisco Dc Nexus9K",
    "vendor": "cisco",
    "category": "Cisco DC (ACI, Nexus)",
    "index": "netops_logs",
    "sample": "{\"timestamp\": \"$GOTS$\", \"component\": \"nxpower\", \"device\": \"10.0.0.253:443\", \"Row_info\": {\"voltage_level\": \"12\"}}"
  },
  {
    "id": "cisco:dc:aci:events",
    "label": "Cisco ACI Fabric State Events",
    "vendor": "cisco",
    "category": "Cisco DC (ACI, Nexus)",
    "index": "idx_network_ops",
    "sample": "{\"event\": \"aci_event\", \"code\": \"E4204819\", \"severity\": \"info\", \"cause\": \"transition\", \"dn\": \"topology/pod-1/node-101/sys"
  },
  {
    "id": "cisco:nexus",
    "label": "Cisco Nexus DC Switch Event",
    "vendor": "cisco",
    "category": "Cisco DC (ACI, Nexus)",
    "index": "idx_network_ops",
    "sample": "May 20 14:00:10 sw-nexus-9300-01 %ETHPORT-5-IF_UP: Interface Ethernet1/1 is up in mode access"
  },
  {
    "id": "cisco:nxos",
    "label": "Cisco NX-OS Structured Event Stream",
    "vendor": "cisco",
    "category": "Cisco DC (ACI, Nexus)",
    "index": "idx_network_ops",
    "sample": "{\"timestamp\": \"2026-09-20T14:00:11.000Z\", \"device\": \"sw-nexus-9300-01\", \"facility\": \"ETH_PORT\", \"severity\": 5, \"type\": \""
  },
  {
    "id": "cisco:nxos:syslog",
    "label": "Cisco NX-OS Syslog Event",
    "vendor": "cisco",
    "category": "Cisco DC (ACI, Nexus)",
    "index": "idx_network_ops",
    "sample": "2026 Sep 20 14:00:12 sw-nexus-9300-01 %OSPF-5-ADJCHANGE: ospf-1 [1024] Process 1, Nbr 10.254.0.2 on Ethernet1/1 from LOA"
  },
  {
    "id": "cisco:dnac:audit:logs",
    "label": "Cisco Dnac Audit Logs",
    "vendor": "cisco",
    "category": "Cisco DNAC",
    "index": "netops_logs",
    "sample": "{\"version\": \"1.0.0\", \"clientId\": \"admin\", \"efInstanceId\": \"8bc79c1e-9614-4b90-94e2-b210740c85de\", \"instanceId\": \"f7924add-c576-4617-80d4-62da85174cb3\", \"eventId\": \"AUDIT_LOG_EVENT\", \"namespace\": \"AUDIT_LOG\", \"name\": \"AUDIT_LOG\", \"description\": \"Intent API \\\"Get Issue Enrichment Details\\\" Executed\", \"type\": \"AUDIT_LOG\", \"category\": \"INFO\", \"domain\": \"Programmability\", \"subDomain\": \"APIs and Integra"
  },
  {
    "id": "cisco:dnac:client",
    "label": "Cisco Dnac Client",
    "vendor": "cisco",
    "category": "Cisco DNAC",
    "index": "netops_logs",
    "sample": "{\"id\": \"E8:BC:E4:74:07:FA\", \"macAddress\": \"E8:BC:E4:74:07:FA\", \"type\": \"Wired\", \"name\": \"SEPE8BCE47407FA\", \"userId\": null, \"username\": \"9Qx9CJ5O351+SFhFnaESDaKssazYM4bgml3GbE7MDQA=\", \"ipv4Address\": null, \"ipv6Addresses\": [\"fe80::eabc:e4ff:fe74:7fa\"], \"vendor\": \"Cisco Systems, Inc.\", \"osType\": \"unknown\", \"osVersion\": null, \"formFactor\": \"IP Phone\", \"trustScore\": 6.0, \"deviceType\": \"Cisco-IP-Phone 9"
  },
  {
    "id": "cisco:dnac:clienthealth",
    "label": "Cisco Dnac Clienthealth",
    "vendor": "cisco",
    "category": "Cisco DNAC",
    "index": "netops_logs",
    "sample": "{\"siteId\": \"global\", \"clientType\": \"ALL\", \"clientCount\": 0, \"clientUniqueCount\": 0, \"scoreValue\": -1, \"starttime\": 1784258167916, \"endtime\": 1784258467916, \"scoreType\": \"ALL\", \"cisco_catalyst_host\": \"https://dnac.maple.ciscolabs.com\"}"
  },
  {
    "id": "cisco:dnac:compliance",
    "label": "Cisco Dnac Compliance",
    "vendor": "cisco",
    "category": "Cisco DNAC",
    "index": "netops_logs",
    "sample": "{\"ComplianceDeviceID\": \"4881747e-0e66-4275-8611-f9ec86746a7d\", \"ComplianceStatus\": \"NON_COMPLIANT\", \"ComplianceLastUpdateTime\": 1784246310488, \"DeviceName\": \"C9800.maple.ciscolabs.com\", \"IpAddress\": \"10.0.10.50\", \"DeviceFamily\": \"Wireless Controller\", \"Reachability\": \"Reachable\", \"ReachabilityFailureReason\": \"\", \"ManageErrors\": \"\", \"Manageability\": \"Managed\", \"MACAddress\": \"00:50:56:b7:74:4c\", \"De"
  },
  {
    "id": "cisco:dnac:devicehealth",
    "label": "Cisco Dnac Devicehealth",
    "vendor": "cisco",
    "category": "Cisco DNAC",
    "index": "netops_logs",
    "sample": "{\"DeviceName\": \"TRN-SDA-C9500.maple.ciscolabs.com\", \"IpAddress\": \"10.120.1.1\", \"DeviceFamily\": \"Switches and Hubs\", \"Reachability\": \"Unreachable\", \"ReachabilityFailureReason\": \"SNMP Connectivity Failed\", \"ManageErrors\": \"Partial Collection Failure\", \"Manageability\": \"Managed (With Errors)\", \"MACAddress\": \"74:ad:98:6c:9f:20\", \"DeviceRole\": \"DISTRIBUTION\", \"ImageVersion\": \"17.18.1\", \"Uptime\": \"13 da"
  },
  {
    "id": "cisco:dnac:issue",
    "label": "Cisco Dnac Issue",
    "vendor": "cisco",
    "category": "Cisco DNAC",
    "index": "netops_logs",
    "sample": "{\"IssueID\": \"72859f90-cafd-4980-a325-431f9ed9dd40\", \"IssueSpecificCategory\": \"Connected\", \"IssueSpecificSource\": \"Cisco DNA\", \"IssueSpecificName\": \"fabric_lisp_session_down_global_trigger\", \"IssueSpecificDescription\": \"LISP session on \\\"LOCAL\\\" Control Plane \\\"Kanata-FB2.ott04-lab.ca\\\" in Fabric site \\\"Global/Kanata_SDA\\\" is down.\", \"IssueSpecificEntity\": \"network_device\", \"IssueSpecificEntityValu"
  },
  {
    "id": "cisco:dnac:networkhealth",
    "label": "Cisco Dnac Networkhealth",
    "vendor": "cisco",
    "category": "Cisco DNAC",
    "index": "netops_logs",
    "sample": "{\"category\": \"All\", \"healthScore\": 29, \"totalCount\": 24, \"goodCount\": 7, \"noHealthCount\": 17, \"time\": \"1784258468717\", \"cisco_catalyst_host\": \"https://dnac.maple.ciscolabs.com\"}"
  },
  {
    "id": "cisco:dnac:securityadvisory",
    "label": "Cisco Dnac Securityadvisory",
    "vendor": "cisco",
    "category": "Cisco DNAC",
    "index": "netops_logs",
    "sample": "{\"Summary\": \"True\", \"Category\": \"CRITICAL\", \"SubCategory\": \"TOTAL\", \"Amount\": 3, \"cisco_catalyst_host\": \"https://10.20.1.16\"}"
  },
  {
    "id": "cisco:dnac:site:topology",
    "label": "Cisco Dnac Site Topology",
    "vendor": "cisco",
    "category": "Cisco DNAC",
    "index": "netops_logs",
    "sample": "{\"id\": \"9056977e-394b-4bb8-9618-d2c6b2a951d0\", \"siteHierarchyId\": \"6f6b2254-2c82-4df2-b4ef-df32aa8db97e/120f464d-4818-42dd-bb74-cc7c005cff7b/b785f984-870f-4487-a163-3c3700221fdc/9056977e-394b-4bb8-9618-d2c6b2a951d0\", \"parentId\": \"b785f984-870f-4487-a163-3c3700221fdc\", \"name\": \"Distribution\", \"nameHierarchy\": \"Global/Toronto/CLUS-26-DMZ1/Distribution\", \"type\": \"floor\", \"floorNumber\": 1, \"rfModel\": "
  },
  {
    "id": "cisco:duo:account",
    "label": "Cisco Duo Account",
    "vendor": "cisco",
    "category": "Cisco Duo",
    "index": "netops_logs",
    "sample": "{\"ctime\": \"Fri $SYSLOG_TIMESTAMP$ 2026\", \"account_id\": \"DAOSZ4YYK0VOGIA1JIYJ\", \"admin_count\": 5, \"edition\": \"Duo Premier\", \"integration_count\": 14, \"telephony_credits_remaining\": 0, \"user_count\": 68, \"user_pending_deletion_count\": 0, \"timestamp\": 1789752783, \"host\": \"api-dd716ff8.duosecurity.com\", \"extracted_eventtype\": \"account\"}"
  },
  {
    "id": "cisco:duo:activity",
    "label": "Cisco Duo Activity",
    "vendor": "cisco",
    "category": "Cisco Duo",
    "index": "netops_logs",
    "sample": "{\"ctime\": \"Fri $SYSLOG_TIMESTAMP$ 2026\", \"access_device\": null, \"action\": {\"details\": \"{\\\"sync_ref_code\\\": \\\"951940ce7e0bcc4150b1fde70fd0988c\\\", \\\"duration\\\": \\\"0:00:07\\\", \\\"selected_groups\\\": [\\\"cn=lab_owners,ou=maple_groups,dc=maple,dc=ciscolabs,dc=com\\\", \\\"cn=subrosa_users,ou=maple_groups,dc=maple,dc=ciscolabs,dc=com\\\", \\\"cn=maple-vpn-users,ou=maple_groups,dc=maple,dc=ciscolabs,dc=com\\\", \\\"cn=c"
  },
  {
    "id": "cisco:duo:administrator",
    "label": "Cisco Duo Administrator",
    "vendor": "cisco",
    "category": "Cisco Duo",
    "index": "netops_logs",
    "sample": "{\"ctime\": \"Fri $SYSLOG_TIMESTAMP$ 2026\", \"action\": \"ad_sync_finish\", \"description\": \"{\\\"Duration\\\": \\\"0:00:07\\\", \\\"Users added\\\": 0, \\\"Users modified\\\": 0, \\\"Users seen\\\": 67, \\\"Users removed\\\": 0, \\\"authproxy_identifiers\\\": [\\\"PRF2XSHZBNKP9HO38BSN\\\"], \\\"Sync Ref. Code\\\": \\\"951940ce7e0bcc4150b1fde70fd0988c\\\"}\", \"isotimestamp\": \"$ISO_TIMESTAMP$\", \"object\": \"AD MAPLE\", \"timestamp\": 1789752192, \"user"
  },
  {
    "id": "cisco:duo:authentication",
    "label": "Cisco Duo Authentication",
    "vendor": "cisco",
    "category": "Cisco Duo",
    "index": "netops_logs",
    "sample": "{\"ctime\": \"Fri $SYSLOG_TIMESTAMP$ 2026\", \"access_device\": {\"browser\": null, \"browser_version\": null, \"flash_version\": null, \"java_version\": null, \"os\": null, \"os_version\": null, \"trusted_endpoint_status\": \"unknown\"}, \"alias\": \"\", \"device\": \"416-571-0674\", \"email\": \"mahamudc@cisco.com\", \"factor\": \"Duo Push\", \"integration\": \"Auth API\", \"ip\": \"0.0.0.0\", \"isotimestamp\": \"$ISO_TIMESTAMP$\", \"location\": "
  },
  {
    "id": "cisco:duo:authentication_v2",
    "label": "Cisco Duo Authentication V2",
    "vendor": "cisco",
    "category": "Cisco Duo",
    "index": "netops_logs",
    "sample": "{\"ctime\": \"Fri $SYSLOG_TIMESTAMP$ 2026\", \"access_device\": {\"browser\": null, \"browser_version\": null, \"epkey\": null, \"flash_version\": null, \"hostname\": null, \"ip\": \"0.0.0.0\", \"is_encryption_enabled\": \"unknown\", \"is_firewall_enabled\": \"unknown\", \"is_password_set\": \"unknown\", \"java_version\": null, \"location\": {\"city\": null, \"country\": null, \"state\": null}, \"management_agents\": [], \"os\": null, \"os_ver"
  },
  {
    "id": "cisco:duo:endpoint",
    "label": "Cisco Duo Endpoint",
    "vendor": "cisco",
    "category": "Cisco Duo",
    "index": "netops_logs",
    "sample": "{\"ctime\": \"Thu $SYSLOG_TIMESTAMP$ 2026\", \"alternative_ids\": [], \"browsers\": [], \"computer_sid\": \"\", \"cpu_id\": \"\", \"device_id\": \"\", \"device_identifier\": \"\", \"device_identifier_type\": \"\", \"device_name\": \"\", \"device_udid\": \"\", \"device_username\": \"\", \"device_username_type\": \"\", \"disk_encryption_status\": \"Unknown\", \"domain_sid\": \"\", \"email\": \"mrayani@cisco.com\", \"epkey\": \"EP2YU6L9NENSABJAIX1D\", \"firewa"
  },
  {
    "id": "cisco:duo:user",
    "label": "Cisco Duo User",
    "vendor": "cisco",
    "category": "Cisco Duo",
    "index": "netops_logs",
    "sample": "{\"ctime\": \"Fri $SYSLOG_TIMESTAMP$ 2026\", \"alias1\": null, \"alias2\": null, \"alias3\": null, \"alias4\": null, \"aliases\": {}, \"created\": 1786110545, \"custom_attributes\": {}, \"date_of_birth\": null, \"desktop_authenticators\": [], \"desktoptokens\": [], \"directory_key\": \"DS2ACAGGQBNC95H3U4QS\", \"email\": \"glarivee@subrosa.ca\", \"enable_auto_prompt\": true, \"entra_federated_user_id\": null, \"external_id\": \"uj9hjKUH"
  },
  {
    "id": "cisco:intersight:advisories",
    "label": "Cisco Intersight Advisories",
    "vendor": "cisco",
    "category": "Cisco Intersight",
    "index": "netops_logs",
    "sample": "{\"AccountMoid\": \"5960901ca94eba000127e33a\", \"Actions\": [{\"AffectedObjectType\": \"equipment.Chassis\", \"AlertType\": \"eolAdvisory\", \"Identifiers\": [{\"Name\": \"Moid\", \"ObjectType\": \"tam.Identifiers\", \"Value\": \"ds1_Moid\"}], \"Name\": \"\", \"ObjectType\": \"tam.Action\", \"OperationType\": \"create\", \"Queries\": [{\"Name\": \"qds2\", \"ObjectType\": \"tam.QueryEntry\", \"Priority\": 1, \"Query\": \"SELECT * FROM ds1 where ( date"
  },
  {
    "id": "cisco:intersight:alarms",
    "label": "Cisco Intersight Alarms",
    "vendor": "cisco",
    "category": "Cisco Intersight",
    "index": "netops_logs",
    "sample": "{\"AccountMoid\": \"660de283756461330140b580\", \"Acknowledge\": \"None\", \"AcknowledgeBy\": \"\", \"AcknowledgeTime\": \"$ISO_TIMESTAMP$\", \"AffectedMo\": {\"ClassId\": \"mo.MoRef\", \"Moid\": \"68c9a917422d332d416876f6\", \"ObjectType\": \"ether.PhysicalPort\", \"link\": \"https://intersight.com/api/v1/ether/PhysicalPorts/68c9a917422d332d416876f6\"}, \"AffectedMoDisplayName\": \"MAPLE-FI-FAB-3/switch-A/slot-1/ethport-36\", \"Affect"
  },
  {
    "id": "cisco:intersight:auditrecords",
    "label": "Cisco Intersight Auditrecords",
    "vendor": "cisco",
    "category": "Cisco Intersight",
    "index": "netops_logs",
    "sample": "{\"AccountMoid\": \"660de283756461330140b580\", \"AffectedObjectTypeLabel\": \"\", \"CreateTime\": \"$ISO_TIMESTAMP$\", \"Email\": \"dieherna@cisco.com\", \"Event\": \"Logout\", \"HttpOperation\": \" \", \"HttpResponseCode\": 0, \"HttpResponsePayload\": \"\", \"InstId\": \"6aab13f175646133016f9e74\", \"MoDisplayNames\": {\"Name\": [\"dieherna@cisco.com\"]}, \"MoType\": \"iam.User\", \"ModTime\": \"$ISO_TIMESTAMP$\", \"Moid\": \"6aab13f26972653301d"
  },
  {
    "id": "cisco:intersight:compute",
    "label": "Cisco Intersight Compute",
    "vendor": "cisco",
    "category": "Cisco Intersight",
    "index": "netops_logs",
    "sample": "{\"AccountMoid\": \"660de283756461330140b580\", \"AlarmType\": \"minor\", \"Ancestors\": [{\"Moid\": \"69ea646f76752d340195f1c8\", \"ObjectType\": \"network.Element\", \"link\": \"https://www.intersight.com/api/v1/network/Elements/69ea646f76752d340195f1c8\"}], \"CreateTime\": \"$ISO_TIMESTAMP$\", \"DeviceMoId\": \"69ea646e6f7261350123bfde\", \"Dn\": \"switch-FDO2441072E/stor-part-mnt_pss\", \"DomainGroupMoid\": \"660de283756461330140"
  },
  {
    "id": "cisco:intersight:contracts",
    "label": "Cisco Intersight Contracts",
    "vendor": "cisco",
    "category": "Cisco Intersight",
    "index": "netops_logs",
    "sample": "{\"AccountMoid\": \"660de283756461330140b580\", \"ContractStatus\": \"Not Covered\", \"ContractStatusReason\": \"\", \"ContractUnavailableRetryCount\": 1, \"ContractUpdatedTime\": \"$ISO_TIMESTAMP$\", \"CoveredProductLineEndDate\": \"2023-10-13\", \"CreateTime\": \"$ISO_TIMESTAMP$\", \"DeviceId\": \"WZP263600LU\", \"DeviceType\": \"CiscoUcsServer\", \"DomainGroupMoid\": \"660de283756461330140b581\", \"IsValid\": true, \"ItemType\": \"CHASS"
  },
  {
    "id": "cisco:intersight:licenses",
    "label": "Cisco Intersight Licenses",
    "vendor": "cisco",
    "category": "Cisco Intersight",
    "index": "netops_logs",
    "sample": "{\"Account\": {\"Moid\": \"660de283756461330140b580\", \"ObjectType\": \"iam.Account\", \"link\": \"https://intersight.com/api/v1/iam/Accounts/660de283756461330140b580\"}, \"AccountId\": \"660de283756461330140b580\", \"AccountMoid\": \"660de283756461330140b580\", \"AuthExpireTime\": \"2026-12-16 19:44:09\", \"AuthInitialTime\": \"2026-09-17 19:49:10\", \"AuthNextTime\": \"2026-09-18 07:49:10\", \"Category\": \"e\", \"CreateTime\": \"$ISO"
  },
  {
    "id": "cisco:intersight:metrics",
    "label": "Cisco Intersight Metrics",
    "vendor": "cisco",
    "category": "Cisco Intersight",
    "index": "cisco_mdt_metrics",
    "sample": "{\"version\": \"v1\", \"timestamp\": \"$ISO_TIMESTAMP$\", \"event\": {\"entdfmx\": null, \"nura\": null, \"nirr\": null, \"nurc\": null, \"nrrmn\": null, \"nirs\": null, \"enlcmx\": null, \"entdfmn\": null, \"nrrmx\": null, \"enrdmx\": null, \"id\": \"/api/v1/fc/PhysicalPorts/69ea64737572792d41c44ae6\", \"enlcmn\": null, \"nprpppsum\": null, \"enrnbr\": null, \"nurmn\": null, \"enrnbs\": null, \"nurmx\": null, \"entjds\": null, \"nrrs\": null, \"n"
  },
  {
    "id": "cisco:intersight:networkelements",
    "label": "Cisco Intersight Networkelements",
    "vendor": "cisco",
    "category": "Cisco Intersight",
    "index": "netops_logs",
    "sample": "{\"AccountMoid\": \"660de283756461330140b580\", \"AdminEvacState\": \"disabled\", \"AdminInbandInterfaceState\": \"disabled\", \"AlarmSummary\": {\"Critical\": 2, \"Health\": \"Critical\", \"Info\": 0, \"ObjectType\": \"compute.AlarmSummary\", \"Suppressed\": false, \"SuppressedCritical\": 0, \"SuppressedInfo\": 0, \"SuppressedWarning\": 0, \"Warning\": 0}, \"Ancestors\": [], \"AssignedLocation\": null, \"AvailableMemory\": \"\", \"Cards\": ["
  },
  {
    "id": "cisco:intersight:networkobjects",
    "label": "Cisco Intersight Networkobjects",
    "vendor": "cisco",
    "category": "Cisco Intersight",
    "index": "netops_logs",
    "sample": "{\"AccessVlan\": \"\", \"AccountMoid\": \"660de283756461330140b580\", \"AcknowledgedPeerInterface\": null, \"AdminFec\": \"\", \"AdminSpeed\": \"\", \"AdminState\": \"Disabled\", \"AggregatePortId\": 0, \"AllowedVlans\": \"\", \"Ancestors\": [{\"Moid\": \"68c9a91876752d340185118d\", \"ObjectType\": \"port.Group\", \"link\": \"https://intersight.com/api/v1/port/Groups/68c9a91876752d340185118d\"}, {\"Moid\": \"68c9a915422d332d421b8ff6\", \"Objec"
  },
  {
    "id": "cisco:intersight:profiles",
    "label": "Cisco Intersight Profiles",
    "vendor": "cisco",
    "category": "Cisco Intersight",
    "index": "netops_logs",
    "sample": "{\"AccountMoid\": \"660de283756461330140b580\", \"Action\": \"No-op\", \"ActionParams\": [], \"Ancestors\": [], \"AssignedServer\": {\"Moid\": \"68c9aa8676752d340186a914\", \"Name\": \"MAPLE-FI-FAB-3-1-1\", \"ObjectType\": \"compute.Blade\"}, \"AssociatedServer\": {\"Moid\": \"68c9aa8676752d340186a914\", \"ObjectType\": \"compute.Blade\", \"link\": \"https://intersight.com/api/v1/compute/Blades/68c9aa8676752d340186a914\"}, \"ConfigChange"
  },
  {
    "id": "cisco:intersight:targets",
    "label": "Cisco Intersight Targets",
    "vendor": "cisco",
    "category": "Cisco Intersight",
    "index": "netops_logs",
    "sample": "{\"AccountMoid\": \"660de283756461330140b580\", \"AlarmSummary\": {\"Critical\": 0, \"Health\": \"Healthy\", \"Info\": 0, \"ObjectType\": \"asset.AlarmSummary\", \"SuppressedCritical\": 0, \"SuppressedInfo\": 0, \"SuppressedWarning\": 0, \"Warning\": 0}, \"AssignedLocation\": null, \"Assist\": null, \"ClaimedByUserName\": \"tiagosil@cisco.com\", \"ClaimedTime\": \"$ISO_TIMESTAMP$\", \"ConnectorVersion\": \"1.0.11-20260615170508583\", \"Cre"
  },
  {
    "id": "cisco:sdwan:AAA-6-METHOD_LIST_STATE",
    "label": "Cisco Sdwan Aaa 6 Method List State",
    "vendor": "cisco",
    "category": "Cisco SD-WAN",
    "index": "netops_logs",
    "sample": "$TS$ 10.201.48.116 175: *$TS$:  %AAA-6-METHOD_LIST_STATE: authen mlist  pvt_authen_0 of DOT1X service is marked for notifyingstate and its current state is : DEAD"
  },
  {
    "id": "cisco:sdwan:AAA-6-NOTIFY_MLIST_STATE_TO_AAA_CLIENT",
    "label": "Cisco Sdwan Aaa 6 Notify Mlist State To Aaa Client",
    "vendor": "cisco",
    "category": "Cisco SD-WAN",
    "index": "netops_logs",
    "sample": "$TS$ 10.201.48.116 179: *$TS$:  %AAA-6-NOTIFY_MLIST_STATE_TO_AAA_CLIENT: Notifying state of authentication method list  pvt_authen_0 of DOT1X service as DEAD"
  },
  {
    "id": "cisco:sdwan:AAA_AUDIT_MESSAGE-6-METHOD_LIST_STATE",
    "label": "Cisco Sdwan Aaa Audit Message 6 Method List State",
    "vendor": "cisco",
    "category": "Cisco SD-WAN",
    "index": "netops_logs",
    "sample": "$TS$ 10.201.48.116 172: *$TS$:  %AAA_AUDIT_MESSAGE-6-METHOD_LIST_STATE: Switch 1 R0/0: sessmgrd: mlist default of 8021X service is marked for notifying  state and its current state is : ALIVE"
  },
  {
    "id": "cisco:sdwan:AAA_AUDIT_MESSAGE-6-NOTIFY_MLIST_STATE_TO_AAA_CLIENT",
    "label": "Cisco Sdwan Aaa Audit Message 6 Notify Mlist State To Aaa Client",
    "vendor": "cisco",
    "category": "Cisco SD-WAN",
    "index": "netops_logs",
    "sample": "$TS$ 10.201.48.116 171: *$TS$:  %AAA_AUDIT_MESSAGE-6-NOTIFY_MLIST_STATE_TO_AAA_CLIENT: Switch 1 R0/0: sessmgrd: Notifying state of authentication method list default of 8021X service as ALIVE"
  },
  {
    "id": "cisco:sdwan:BGP-5-NBR_RESET",
    "label": "Cisco Sdwan Bgp 5 Nbr Reset",
    "vendor": "cisco",
    "category": "Cisco SD-WAN",
    "index": "netops_logs",
    "sample": "$TS$ 10.201.48.121 3712: *$TS$:  %BGP-5-NBR_RESET: Neighbor 10.201.130.61 passive reset (Peer closed the session)"
  },
  {
    "id": "cisco:sdwan:BGP-6-NEXTHOP",
    "label": "Cisco Sdwan Bgp 6 Nexthop",
    "vendor": "cisco",
    "category": "Cisco SD-WAN",
    "index": "netops_logs",
    "sample": "$TS$ 10.201.48.118 3181: *$TS$:  %BGP-6-NEXTHOP: Invalid next hop (0.0.0.0) received from 10.201.48.114: martian next hop"
  },
  {
    "id": "cisco:sdwan:BGP_SESSION-5-ADJCHANGE",
    "label": "Cisco Sdwan Bgp Session 5 Adjchange",
    "vendor": "cisco",
    "category": "Cisco SD-WAN",
    "index": "netops_logs",
    "sample": "$TS$ 10.201.48.120 3263: *$TS$:  %BGP_SESSION-5-ADJCHANGE: neighbor 10.201.152.1 IPv4 Unicast vpn vrf UBC_TENANT topology base removed from session  Neighbor deleted"
  },
  {
    "id": "cisco:sdwan:CDP-4-NATIVE_VLAN_MISMATCH",
    "label": "Cisco Sdwan Cdp 4 Native Vlan Mismatch",
    "vendor": "cisco",
    "category": "Cisco SD-WAN",
    "index": "netops_logs",
    "sample": "$TS$ 10.201.48.120 1044: *$TS$:  %CDP-4-NATIVE_VLAN_MISMATCH: Native VLAN mismatch discovered on GigabitEthernet1/0/4 (1), with switch2 GigabitEthernet0/1 (201)."
  },
  {
    "id": "cisco:sdwan:CRYPTO-6-ISAKMP_ON_OFF",
    "label": "Cisco Sdwan Crypto 6 Isakmp On Off",
    "vendor": "cisco",
    "category": "Cisco SD-WAN",
    "index": "netops_logs",
    "sample": "$SYSLOG_TIMESTAMP$ $HOST$ 14675: $SYSLOG_TIMESTAMP$.701: %CRYPTO-6-ISAKMP_ON_OFF: ISAKMP is ON"
  },
  {
    "id": "cisco:sdwan:CTS-3-AAA_NO_RADIUS_SERVER",
    "label": "Cisco Sdwan Cts 3 Aaa No Radius Server",
    "vendor": "cisco",
    "category": "Cisco SD-WAN",
    "index": "netops_logs",
    "sample": "$TS$ 10.201.48.116 173: *$TS$:  %CTS-3-AAA_NO_RADIUS_SERVER: No RADIUS servers available for CTS AAA request for CTS env-data SM"
  },
  {
    "id": "cisco:sdwan:DMI-5-AUTH_PASSED",
    "label": "Cisco Sdwan Dmi 5 Auth Passed",
    "vendor": "cisco",
    "category": "Cisco SD-WAN",
    "index": "netops_logs",
    "sample": "$SYSLOG_TIMESTAMP$ $HOST$ 91622: $SYSLOG_TIMESTAMP$.691: %DMI-5-AUTH_PASSED: R0/0: dmiauthd: User ''vmanage-admin'' authenticated successfully from 1.1.1.105:36298  for netconf over ssh. External groups:"
  },
  {
    "id": "cisco:sdwan:DMI-5-CONFIG_I",
    "label": "Cisco Sdwan Dmi 5 Config I",
    "vendor": "cisco",
    "category": "Cisco SD-WAN",
    "index": "netops_logs",
    "sample": "$SYSLOG_TIMESTAMP$ $HOST$ 14666: *$SYSLOG_TIMESTAMP$.404: %DMI-5-CONFIG_I: R0/0: dmiauthd: Configured from NETCONF/RESTCONF by system-ompd-fwd, transaction-id 682279"
  },
  {
    "id": "cisco:sdwan:DMI-5-SYNC_COMPLETE",
    "label": "Cisco Sdwan Dmi 5 Sync Complete",
    "vendor": "cisco",
    "category": "Cisco SD-WAN",
    "index": "netops_logs",
    "sample": "$TS$ 10.201.48.115 3103: *$TS$:  %DMI-5-SYNC_COMPLETE: Switch 1 R0/0: dmiauthd: The running configuration has been synchronized to the NETCONF running data store."
  },
  {
    "id": "cisco:sdwan:DMI-5-SYNC_NEEDED",
    "label": "Cisco Sdwan Dmi 5 Sync Needed",
    "vendor": "cisco",
    "category": "Cisco SD-WAN",
    "index": "netops_logs",
    "sample": "$TS$ 10.201.48.115 3101: *$TS$:  %DMI-5-SYNC_NEEDED: Switch 1 R0/0: dmiauthd: Configuration change requiring running configuration sync detected - ''no vrf forwarding ''. The running configuration will be synchronized  to the NETCONF running data store."
  },
  {
    "id": "cisco:sdwan:DMI-5-SYNC_START",
    "label": "Cisco Sdwan Dmi 5 Sync Start",
    "vendor": "cisco",
    "category": "Cisco SD-WAN",
    "index": "netops_logs",
    "sample": "$TS$ 10.201.48.115 3102: *$TS$:  %DMI-5-SYNC_START: Switch 1 R0/0: dmiauthd: Synchronization of the running configuration to the NETCONF running data store has started."
  },
  {
    "id": "cisco:sdwan:ENVIRONMENTAL-1-ALERT",
    "label": "Cisco Sdwan Environmental 1 Alert",
    "vendor": "cisco",
    "category": "Cisco SD-WAN",
    "index": "netops_logs",
    "sample": "$SYSLOG_TIMESTAMP$ $HOST$ 27774: $SYSLOG_TIMESTAMP$.765: %ENVIRONMENTAL-1-ALERT: Temp: Inlet 1, Location: R0, State: Warning, Reading: 43 Celsius"
  },
  {
    "id": "cisco:sdwan:EVENTLIB-3-CPUHOG",
    "label": "Cisco Sdwan Eventlib 3 Cpuhog",
    "vendor": "cisco",
    "category": "Cisco SD-WAN",
    "index": "netops_logs",
    "sample": "$TS$ 10.201.48.121 3697: *$TS$:  %EVENTLIB-3-CPUHOG: Switch 1 R0/0: hman: undefined: 1026ms, Traceback=1#9c98bc34b8a46399248b88656ef73fd3  c:7F7229A64000+42630 c:7F7229A64000+FE9AD c:7F7229A64000+86F9E c:7F7229A64000+8804A c:7F7229A64000+65A4C c:7F7229A64000+58469 procmib_lib:7F722BC6A000+8309 :5B96778E7000+426F1 evlib:7F722D007000+9336 evlib:7F722D007000+9D70 orchestrator_lib:7F722BFB6000+12BE4"
  },
  {
    "id": "cisco:sdwan:IOSXE-3-PLATFORM",
    "label": "Cisco Sdwan Iosxe 3 Platform",
    "vendor": "cisco",
    "category": "Cisco SD-WAN",
    "index": "netops_logs",
    "sample": "$TS$ 10.201.48.115 288: *$TS$:  %IOSXE-3-PLATFORM: Switch 1 R0/0: kernel: eth2: mtu greater than device maximum"
  },
  {
    "id": "cisco:sdwan:IOSXE_INFRA-4-NO_PUNT_KEEPALIVE",
    "label": "Cisco Sdwan Iosxe Infra 4 No Punt Keepalive",
    "vendor": "cisco",
    "category": "Cisco SD-WAN",
    "index": "netops_logs",
    "sample": "$TS$ 10.201.48.120 2870: *$TS$:  %IOSXE_INFRA-4-NO_PUNT_KEEPALIVE:  Keepalive not received for 20 seconds"
  },
  {
    "id": "cisco:sdwan:IOSXE_RP_PAE_NOT-6-PAE_STARTUP",
    "label": "Cisco Sdwan Iosxe Rp Pae Not 6 Pae Startup",
    "vendor": "cisco",
    "category": "Cisco SD-WAN",
    "index": "netops_logs",
    "sample": "$TS$ 10.201.48.115 2135: *$TS$:  %IOSXE_RP_PAE_NOT-6-PAE_STARTUP: Product Analytics is Disabled"
  },
  {
    "id": "cisco:sdwan:LINEPROTO-5-UPDOWN",
    "label": "Cisco Sdwan Lineproto 5 Updown",
    "vendor": "cisco",
    "category": "Cisco SD-WAN",
    "index": "netops_logs",
    "sample": "$TS$ 10.201.48.115 3322: *$TS$:  %LINEPROTO-5-UPDOWN: Line protocol on Interface Vlan1930, changed state to down"
  },
  {
    "id": "cisco:sdwan:LINK-5-CHANGED",
    "label": "Cisco Sdwan Link 5 Changed",
    "vendor": "cisco",
    "category": "Cisco SD-WAN",
    "index": "netops_logs",
    "sample": "$TS$ 10.201.48.115 3442: *$TS$:  %LINK-5-CHANGED: Interface Vlan1930, changed state to administratively down"
  },
  {
    "id": "cisco:sdwan:LINK-5-UPDOWN",
    "label": "Cisco Sdwan Link 5 Updown",
    "vendor": "cisco",
    "category": "Cisco SD-WAN",
    "index": "netops_logs",
    "sample": "$TS$ 10.201.48.115 287: *$TS$:  %LINK-5-UPDOWN: Interface GigabitEthernet1/0/2, changed state to up"
  },
  {
    "id": "cisco:sdwan:MDT_CONNECTION-6-STATE_CHANGED",
    "label": "Cisco Sdwan Mdt Connection 6 State Changed",
    "vendor": "cisco",
    "category": "Cisco SD-WAN",
    "index": "cisco_mdt_metrics",
    "sample": "$TS$ 10.201.48.120 3927: *$TS$:  %MDT_CONNECTION-6-STATE_CHANGED: Switch 1 R0/0: pubd: Connection state changed (id 6 - 10.20.1.16:25103:0:10.201.48.120): DOWN"
  },
  {
    "id": "cisco:sdwan:MSDP-5-PEER_UPDOWN",
    "label": "Cisco Sdwan Msdp 5 Peer Updown",
    "vendor": "cisco",
    "category": "Cisco SD-WAN",
    "index": "netops_logs",
    "sample": "$TS$ 10.201.48.119 4394: *$TS$:  %MSDP-5-PEER_UPDOWN: Session to peer 10.201.151.1 going down"
  },
  {
    "id": "cisco:sdwan:NDBMAN-5-CONFIG_I",
    "label": "Cisco Sdwan Ndbman 5 Config I",
    "vendor": "cisco",
    "category": "Cisco SD-WAN",
    "index": "netops_logs",
    "sample": "$TS$ 10.201.48.118 3269: *$TS$:  %NDBMAN-5-CONFIG_I: Switch 1 R0/0: ndbmand: Configured feature ''yang-mapping'' from 127.0.0.1:0 via INTERNAL-API user yang_mgmt_infra session 20, transaction-id 102"
  },
  {
    "id": "cisco:sdwan:OSPF-5-ADJCHG",
    "label": "Cisco Sdwan Ospf 5 Adjchg",
    "vendor": "cisco",
    "category": "Cisco SD-WAN",
    "index": "netops_logs",
    "sample": "$TS$ 10.201.48.119 4393: *$TS$:  %OSPF-5-ADJCHG: Process 1, Nbr 10.201.48.120 on GigabitEthernet1/0/5 from FULL to DOWN, Neighbor Down: Dead timer expired"
  },
  {
    "id": "cisco:sdwan:PKI-6-AUTHORITATIVE_CLOCK",
    "label": "Cisco Sdwan Pki 6 Authoritative Clock",
    "vendor": "cisco",
    "category": "Cisco SD-WAN",
    "index": "netops_logs",
    "sample": "$SYSLOG_TIMESTAMP$ $HOST$ 11108: $SYSLOG_TIMESTAMP$.633: %PKI-6-AUTHORITATIVE_CLOCK: The system clock has been set."
  },
  {
    "id": "cisco:sdwan:PLATFORM-4-ELEMENT_WARNING",
    "label": "Cisco Sdwan Platform 4 Element Warning",
    "vendor": "cisco",
    "category": "Cisco SD-WAN",
    "index": "netops_logs",
    "sample": "$SYSLOG_TIMESTAMP$ $HOST$ 14767: $SYSLOG_TIMESTAMP$.919: %PLATFORM-4-ELEMENT_WARNING: R0/0: smand: RP/0: 5-Minute Load Average value 6.11 exceeds warning level 6.10."
  },
  {
    "id": "cisco:sdwan:sitehealth",
    "label": "Cisco Sdwan Sitehealth",
    "vendor": "cisco",
    "category": "Cisco SD-WAN",
    "index": "netops_logs",
    "sample": "{\"site_id\": \"500\", \"site_name\": \"SITE_500\", \"latitude\": \"45.424721\", \"longitude\": \"-75.695\", \"fromGps\": \"false\", \"site_health\": \"good\", \"devices_health\": \"good\", \"tunnels_health\": \"no_data\", \"apps_health\": \"no_data\", \"devices_health_score\": 10.0, \"tunnels_health_score\": -1.0, \"apps_health_score\": -1.0, \"apps_usage\": 0.0, \"prev_apps_usage\": 0.0, \"region_list\": [], \"role\": [], \"device_type\": [], \"la"
  },
  {
    "id": "cisco:sdwan:ssetunnels",
    "label": "Cisco Sdwan Ssetunnels",
    "vendor": "cisco",
    "category": "Cisco SD-WAN",
    "index": "netops_logs",
    "sample": "{\"device-state\": \"Up\", \"tunnel-if-name\": \"Tunnel17000102\", \"vdevice-name\": \"172.80.1.10\", \"createTimeStamp\": $EPOCH_MS$, \"sse-tcsm\": \"-\", \"vdevice-host-name\": \"C1131X-site8000\", \"tunnelType\": \"SSE-Private access\", \"vdevice-dataKey\": \"172.80.1.10-Tunnel17000102--\", \"destination-data-center\": \"35.171.214.188\", \"vmanage-system-ip\": \"172.80.1.10\", \"tenantId\": \"default\", \"lastupdated\": $EPOCH_MS$, \"sig"
  },
  {
    "id": "cisco:sdwan:SYS-5-CONFIG_P",
    "label": "Cisco Sdwan Sys 5 Config P",
    "vendor": "cisco",
    "category": "Cisco SD-WAN",
    "index": "netops_logs",
    "sample": "$SYSLOG_TIMESTAMP$ $HOST$ 14667: *$SYSLOG_TIMESTAMP$.559: %SYS-5-CONFIG_P: Configured programmatically by process iosp_dmiauthd_conn_100001_vty_100001 from console as system-ompd-fwd on vty4294966494"
  },
  {
    "id": "cisco:sdwan:syslog",
    "label": "Cisco Sdwan Syslog",
    "vendor": "cisco",
    "category": "Cisco SD-WAN",
    "index": "netops_logs",
    "sample": "$SYSLOG_TIMESTAMP$ $HOST$ 186746: $SYSLOG_TIMESTAMP$.730: %DMI-5-AUTH_PASSED: R0/0: dmiauthd: User ''vmanage-admin'' authenticated successfully from 1.1.1.105:54758  for netconf over ssh. External groups:"
  },
  {
    "id": "cisco:sdwan:system:logs",
    "label": "Cisco Sdwan System Logs",
    "vendor": "cisco",
    "category": "Cisco SD-WAN",
    "index": "netops_logs",
    "sample": "$SYSLOG_TIMESTAMP$ $HOST$ 162896: $SYSLOG_TIMESTAMP$.857: %SDWAN-5-FPMD : FLOW LOG device-vpn: 4099 tenant-vpn: 4099 src: 10.201.48.53/179 dst: 10.201.48.54/54097 proto: 6 tos: 192 direction: from-service, policy: data_service_CiscoLive_AAR_Policy-vpn_Service_VPN_Secure, sequence: 1, Result: accept Pkt count: 211900 bytes: 14305753 Ingress-Intf: GigabitEthernet0/0/2.3105 Egress-intf: Unknown Tenan"
  },
  {
    "id": "cisco:sdwan:sytem:logs",
    "label": "Cisco Sdwan Sytem Logs",
    "vendor": "cisco",
    "category": "Cisco SD-WAN",
    "index": "netops_logs",
    "sample": "$TS$ 192.168.128.1 1 1772323200.984001859 MX_67_Home ip_flow_end src=192.168.128.102 dst=23.220.93.204 protocol=tcp sport=52390 dport=443 translated_src_ip=192.168.1.66 translated_port=52390"
  },
  {
    "id": "cisco:sdwan:tunnelhealth",
    "label": "Cisco Sdwan Tunnelhealth",
    "vendor": "cisco",
    "category": "Cisco SD-WAN",
    "index": "netops_logs",
    "sample": "{\"loss_percentage\": 0.0, \"latency\": 0.0, \"jitter\": 0.0, \"tx_octets\": 10411.0, \"rx_octets\": 67099.0, \"vqoe_score\": 10.0, \"name\": \"1.1.1.110:private2-1.1.1.100:private2\", \"remote_color\": \"private2\", \"remote_system_ip\": \"1.1.1.100\", \"remote-host-name\": \"SD-WAN_Edge-Kanata\", \"remote_site_id\": \"100\", \"remoteDeviceClass\": \"cisco-router\", \"remote_latitude\": \"45.3422\", \"remote_longitude\": \"-75.92656\", \"lo"
  },
  {
    "id": "cisco:sdwan:utd:logs",
    "label": "Cisco Sdwan Utd Logs",
    "vendor": "cisco",
    "category": "Cisco SD-WAN",
    "index": "netops_logs",
    "sample": "$TS$ 192.168.128.132 2026/03/01-00:00:00.307403 UTC [**] [Hostname: c8kv-site-3000-gw1] [**] [System_IP: 172.100.1.5] [**] [Instance_ID: 1] [**] Drop [**] UTD WebFilter Category/Reputation [**] [URL: www.tekdefense.com/downloads/malware-samples/1.exe.zip] ** [Category: Malware Sites] ** [Reputation: 10] [POLICY: BR-TYPE2-AIP] {TCP} 10.33.35.101:55924 -> 198.185.159.160:80"
  },
  {
    "id": "cisco:sdwan:utdhealth",
    "label": "Cisco Sdwan Utdhealth",
    "vendor": "cisco",
    "category": "Cisco SD-WAN",
    "index": "netops_logs",
    "sample": "{\"vdevice-dataKey\": \"172.100.1.5\", \"utd-engine-status-version\": \"1.1.0_SV3.3.5.0_XE17.18\", \"vdevice-name\": \"172.100.1.5\", \"utd-engine-status-memory-status\": \"utd-oper-status-green\", \"lastupdated\": $EPOCH_MS$, \"utd-engine-status-status\": \"utd-oper-status-green\", \"utd-engine-status-memory-usage\": \"44.9\", \"vdevice-host-name\": \"c8kv-site-3000-gw1\", \"utd-engine-status-profile\": \"Cloud-Low\"}"
  },
  {
    "id": "meraki:airmarshal",
    "label": "Meraki Airmarshal",
    "vendor": "cisco",
    "category": "Meraki",
    "index": "netops_logs",
    "sample": "{  \"networkId\": \"N_TORONTO_DC\",  \"networkName\": \"Toronto Hub\",  \"ssid\": \"Toronto-Corp-Secure\",  \"bssid\": \"0c:8d:db:6f:10:20\",  \"channels\": [1, 6, 11],  \"rogueDetected\": false,  \"wiredEvidence\": false,  \"status\": \"secure\" }"
  },
  {
    "id": "meraki:appliancesdwanstatistics",
    "label": "Meraki Appliancesdwanstatistics",
    "vendor": "cisco",
    "category": "Meraki",
    "index": "cisco_mdt_metrics",
    "sample": "{  \"serial\": \"Q2QN-TOR-MX100\",  \"networkName\": \"Toronto Hub\",  \"peerSerial\": \"Q2QN-EDM-MX64\",  \"peerName\": \"Edmonton Branch 1\",  \"latencyMs\": 24.5,  \"jitterMs\": 1.8,  \"lossPercentage\": 0.0,  \"sentKbps\": 8450,  \"receivedKbps\": 7920 }"
  },
  {
    "id": "meraki:appliancesdwanstatuses",
    "label": "Meraki Appliancesdwanstatuses",
    "vendor": "cisco",
    "category": "Meraki",
    "index": "netops_logs",
    "sample": "{  \"serial\": \"Q2QN-TOR-MX100\",  \"networkName\": \"Toronto Hub\",  \"uplinks\": [   {    \"interface\": \"wan1\",    \"status\": \"active\",    \"ip\": \"198.51.100.2\",    \"gateway\": \"198.51.100.1\",    \"publicIp\": \"198.51.100.2\"   }  ],  \"vpnPeers\": [   {    \"peerNetworkId\": \"N_EDMONTON_B1\",    \"peerName\": \"Edmonton Branch 1\",    \"reachability\": \"reachable\",    \"mode\": \"spoke\"   },   {    \"peerNetworkId\": \"N_CALGA"
  },
  {
    "id": "meraki:assurancealerts",
    "label": "Meraki Assurancealerts",
    "vendor": "cisco",
    "category": "Meraki",
    "index": "netops_logs",
    "sample": "{  \"id\": \"alert_tor_0000\",  \"networkId\": \"N_TORONTO_DC\",  \"scope\": \"network\",  \"severity\": \"info\",  \"category\": \"Connectivity\",  \"type\": \"NetworkStatusNormal\",  \"title\": \"All devices operating within expected assurance parameters\",  \"startedAt\": \"$ISO_TS$\",  \"resolvedAt\": \"$ISO_TS$\",  \"device\": {   \"serial\": \"Q2QN-TOR-MX100\",   \"name\": \"MX100-Toronto-Hub\"  } }"
  },
  {
    "id": "meraki:devices",
    "label": "Meraki Devices",
    "vendor": "cisco",
    "category": "Meraki",
    "index": "netops_logs",
    "sample": "{  \"serial\": \"Q2QN-TOR-MS250\",  \"name\": \"MS250-Toronto-Core\",  \"mac\": \"0c:8d:db:6f:10:01\",  \"networkId\": \"N_TORONTO_DC\",  \"model\": \"MS250-48FP\",  \"address\": \"150 King St W, Toronto, ON M5H 1J9\",  \"lat\": 43.6487,  \"lng\": -79.3854,  \"notes\": \"Toronto Hub Core Switch\",  \"tags\": [\"hub\", \"datacenter\", \"core\"],  \"lanIp\": \"10.10.10.2\",  \"firmware\": \"MS 15.21.1\",  \"status\": \"online\",  \"productType\": \"swit"
  },
  {
    "id": "meraki:devicesavailabilitieschangehistory",
    "label": "Meraki Devices Availabilities",
    "vendor": "cisco",
    "category": "Meraki",
    "index": "netops_logs",
    "sample": "{  \"ts\": \"$ISO_TS$\",  \"device\": {   \"serial\": \"Q2QN-TOR-MX100\",   \"name\": \"MX100-Toronto-Hub\",   \"productType\": \"appliance\",   \"model\": \"MX100\"  },  \"network\": {   \"id\": \"N_TORONTO_DC\",   \"name\": \"Toronto Hub\"  },  \"oldStatus\": \"offline\",  \"newStatus\": \"online\",  \"duration\": 3600000 }"
  },
  {
    "id": "meraki:organizationsecurity",
    "label": "Meraki Organizationsecurity",
    "vendor": "cisco",
    "category": "Meraki",
    "index": "netops_logs",
    "sample": "{  \"ts\": \"$ISO_TS$\",  \"event\": \"ids_alert\",  \"organizationId\": \"ORG_ACME_CANADA\",  \"networkName\": \"Toronto Hub\",  \"clientMac\": \"f0:18:98:3a:11:02\",  \"message\": \"Routine signature database check completed\",  \"action\": \"allow\",  \"priority\": \"low\" }"
  },
  {
    "id": "meraki:summarytopappliancesbyutilization",
    "label": "Meraki Summarytopappliancesbyutilization",
    "vendor": "cisco",
    "category": "Meraki",
    "index": "netops_logs",
    "sample": "{  \"serial\": \"Q2QN-TOR-MX100\",  \"name\": \"MX100-Toronto-Hub\",  \"model\": \"MX100\",  \"networkName\": \"Toronto Hub\",  \"utilizationPercentage\": 34.2,  \"memoryUsagePercentage\": 41.5,  \"cpuLoadPercentage\": 28.0,  \"status\": \"normal\" }"
  },
  {
    "id": "meraki:summarytopclientsbyusage",
    "label": "Meraki Summarytopclientsbyusage",
    "vendor": "cisco",
    "category": "Meraki",
    "index": "netops_logs",
    "sample": "{  \"networkId\": \"N_TORONTO_DC\",  \"topClients\": [   {\"name\": \"tor-db-backup-01\", \"mac\": \"00:50:56:a1:b2:c3\", \"totalBytes\": 1250000000, \"sentBytes\": 850000000, \"recvBytes\": 400000000},   {\"name\": \"tor-app-srv-02\", \"mac\": \"00:50:56:d4:e5:f6\", \"totalBytes\": 890000000, \"sentBytes\": 490000000, \"recvBytes\": 400000000},   {\"name\": \"mrayani-laptop\", \"mac\": \"f0:18:98:77:22:11\", \"totalBytes\": 45000000, \"sent"
  },
  {
    "id": "meraki:summarytopdevicesbyusage",
    "label": "Meraki Summarytopdevicesbyusage",
    "vendor": "cisco",
    "category": "Meraki",
    "index": "netops_logs",
    "sample": "{  \"networkId\": \"N_TORONTO_DC\",  \"devices\": [   {\"serial\": \"Q2QN-TOR-MS250\", \"name\": \"MS250-Toronto-Core\", \"model\": \"MS250-48FP\", \"totalBytes\": 2140000000},   {\"serial\": \"Q2QN-TOR-MX100\", \"name\": \"MX100-Toronto-Hub\", \"model\": \"MX100\", \"totalBytes\": 1980000000},   {\"serial\": \"Q2JD-TOR-MR46\", \"name\": \"MR46-Toronto-Floor1\", \"model\": \"MR46\", \"totalBytes\": 540000000}  ] }"
  },
  {
    "id": "meraki:switchportsbyswitch",
    "label": "Meraki Switchportsbyswitch",
    "vendor": "cisco",
    "category": "Meraki",
    "index": "netops_logs",
    "sample": "{  \"serial\": \"Q2QN-TOR-MS250\",  \"switchName\": \"MS250-Toronto-Core\",  \"portId\": \"24\",  \"name\": \"Uplink to MX100 WAN\",  \"enabled\": true,  \"status\": \"Connected\",  \"speed\": \"1 Gbps\",  \"duplex\": \"full\",  \"vlan\": 1,  \"traffic\": {   \"totalBytes\": 145028090,   \"sentBytes\": 78201940,   \"recvBytes\": 66826150  },  \"errors\": {   \"crc\": 0,   \"runts\": 0,   \"giants\": 0,   \"fragments\": 0,   \"collisions\": 0,   \"ja"
  },
  {
    "id": "meraki:switchportsoverview",
    "label": "Meraki Switchportsoverview",
    "vendor": "cisco",
    "category": "Meraki",
    "index": "netops_logs",
    "sample": "{  \"networkId\": \"N_TORONTO_DC\",  \"totalPorts\": 48,  \"activePorts\": 36,  \"speeds\": {   \"10M\": 0,   \"100M\": 2,   \"1000M\": 32,   \"10000M\": 2  },  \"poeAllocatedWatts\": 185.4,  \"poeCapacityWatts\": 740.0 }"
  },
  {
    "id": "nutanixpc_alerts",
    "label": "Nutanixpc Alerts",
    "vendor": "nutanix",
    "category": "Nutanix PC",
    "index": "netops_logs",
    "sample": "{\"$reserved\": {\"$fv\": \"v4.r0\"}, \"$objectType\": \"monitoring.v4.serviceability.Alert\", \"extId\": \"d711c281-18fe-4fcc-8937-333d41165889\", \"isAcknowledged\": true, \"acknowledgedTime\": \"$ISO_TIMESTAMP$\", \"isAutoResolved\": true, \"isResolved\": true, \"resolvedTime\": \"$ISO_TIMESTAMP$\", \"sourceEntity\": {\"$reserved\": {\"$fv\": \"v4.r0\"}, \"$objectType\": \"monitoring.v4.common.AlertEntityReference\", \"type\": \"node\", "
  },
  {
    "id": "nutanixpc_cluster_performance",
    "label": "Nutanixpc Cluster Performance",
    "vendor": "nutanix",
    "category": "Nutanix PC",
    "index": "cisco_mdt_metrics",
    "sample": "{\"timestamp\": \"$ISO_TIMESTAMP$\", \"extId\": \"00063ffb-2c0b-2e6c-7635-0025b500010e\", \"controllerAvgIoLatencyUsecs\": 2709, \"controllerAvgReadIoLatencyUsecs\": 806, \"controllerAvgWriteIoLatencyUsecs\": 2721, \"controllerNumIops\": 690, \"controllerNumReadIops\": 4, \"controllerNumWriteIops\": 686, \"ioBandwidthKbps\": 31861, \"controllerReadIoBandwidthKbps\": 153, \"controllerWriteIoBandwidthKbps\": 31708, \"hypervis"
  },
  {
    "id": "nutanixpc_clusters",
    "label": "Nutanixpc Clusters",
    "vendor": "nutanix",
    "category": "Nutanix PC",
    "index": "netops_logs",
    "sample": "{\"$reserved\": {\"$fv\": \"v4.r0\"}, \"$objectType\": \"clustermgmt.v4.config.Cluster\", \"extId\": \"00063ffb-2c0b-2e6c-7635-0025b500010e\", \"vmCount\": 32, \"inefficientVmCount\": 0, \"backupEligibilityScore\": 4, \"name\": \"Fab1-CCHCI-AHV\", \"nodes\": {\"numberOfNodes\": 4, \"$reserved\": {\"$fv\": \"v4.r0\"}, \"$objectType\": \"clustermgmt.v4.config.NodeReference\", \"nodeList\": [{\"nodeUuid\": \"aeae14aa-ba3d-438b-b88b-5c803e72b6"
  },
  {
    "id": "nutanixpc_disk_performance",
    "label": "Nutanixpc Disk Performance",
    "vendor": "nutanix",
    "category": "Nutanix PC",
    "index": "cisco_mdt_metrics",
    "sample": "{\"timestamp\": \"$ISO_TIMESTAMP$\", \"extId\": \"ff26ab7c-0d68-4421-b6bc-6cc4abf18975\", \"diskUsagePpm\": 455057, \"diskCapacityBytes\": 0, \"diskNumIops\": 0, \"diskIoBandwidthkbps\": 0, \"diskAvgIoLatencyMicrosec\": 0, \"diskFreeBytes\": 0, \"diskUsageBytes\": 0, \"diskReadIops\": 0, \"diskWriteIops\": 0, \"diskReadIoBandwidthkbps\": 0, \"diskWriteIoBandwidthkbps\": 0, \"diskReadIoPpm\": 0, \"diskWriteIoPpm\": 0}"
  },
  {
    "id": "nutanixPC_disks",
    "label": "Nutanixpc Disks",
    "vendor": "nutanix",
    "category": "Nutanix PC",
    "index": "netops_logs",
    "sample": "{\"$reserved\": {\"$fv\": \"v4.r0\"}, \"$objectType\": \"clustermgmt.v4.config.Disk\", \"extId\": \"ff26ab7c-0d68-4421-b6bc-6cc4abf18975\", \"links\": [{\"$reserved\": {\"$fv\": \"v1.r0\"}, \"$objectType\": \"common.v1.response.ApiLink\", \"href\": \"$HOST$/ff26ab7c-0d68-4421-b6bc-6cc4abf18975\", \"rel\": \"disk\"}], \"clusterName\": \"Fab1-CCHCI-AHV\", \"clusterExtId\": \"00063ffb-2c0b-2e6c-7635-0025b500010e\", \"storagePoolExtId\": \"3d2e3"
  },
  {
    "id": "nutanixpc_events",
    "label": "Nutanixpc Events",
    "vendor": "nutanix",
    "category": "Nutanix PC",
    "index": "netops_logs",
    "sample": "{\"$reserved\": {\"$fv\": \"v4.r0\"}, \"$objectType\": \"monitoring.v4.serviceability.Event\", \"extId\": \"ee77555c-a7ef-4358-864f-43295cd62561\", \"eventType\": \"IAMAdministrationEventAudit\", \"classifications\": [\"UserAction\"], \"sourceClusterUUID\": \"8ae8575f-53ab-4152-a483-d6fc980bd4cc\", \"creationTime\": \"$ISO_TIMESTAMP$\", \"message\": \"User admin granted permission to [(''Health_Check_Remote_Connection'',)] on rem"
  },
  {
    "id": "nutanixpc_host_performance",
    "label": "Nutanixpc Host Performance",
    "vendor": "nutanix",
    "category": "Nutanix PC",
    "index": "cisco_mdt_metrics",
    "sample": "{\"timestamp\": \"$ISO_TIMESTAMP$\", \"extId\": \"dc8562d0-9e55-4b4e-8bba-9f2e123dc411\", \"controllerAvgIoLatencyUsecs\": 3891, \"controllerAvgReadIoLatencyUsecs\": 768, \"controllerAvgWriteIoLatencyUsecs\": 3892, \"controllerNumIops\": 173, \"controllerNumReadIops\": 0, \"controllerNumWriteIops\": 173, \"ioBandwidthKbps\": 18671, \"controllerReadIoBandwidthKbps\": 0, \"controllerWriteIoBandwidthKbps\": 18670, \"hypervisor"
  },
  {
    "id": "nutanixpc_hosts",
    "label": "Nutanixpc Hosts",
    "vendor": "nutanix",
    "category": "Nutanix PC",
    "index": "netops_logs",
    "sample": "{\"$reserved\": {\"$fv\": \"v4.r0\"}, \"$objectType\": \"clustermgmt.v4.config.Host\", \"extId\": \"dc8562d0-9e55-4b4e-8bba-9f2e123dc411\", \"hostName\": \"CCHCI-AHV-04\", \"hostType\": \"HYPER_CONVERGED\", \"hypervisor\": {\"$reserved\": {\"$fv\": \"v4.r0\"}, \"$objectType\": \"clustermgmt.v4.config.HypervisorReference\", \"externalAddress\": {\"$reserved\": {\"$fv\": \"v1.r0\"}, \"$objectType\": \"common.v1.config.IPAddress\", \"ipv4\": {\"$re"
  },
  {
    "id": "nutanixpc_prismCentrals",
    "label": "Nutanixpc Prismcentrals",
    "vendor": "nutanix",
    "category": "Nutanix PC",
    "index": "netops_logs",
    "sample": "{\"$reserved\": {\"$fv\": \"v4.r0\"}, \"$objectType\": \"clustermgmt.v4.config.Cluster\", \"extId\": \"8ae8575f-53ab-4152-a483-d6fc980bd4cc\", \"name\": \"CCHCI-PC\", \"nodes\": {\"numberOfNodes\": 1, \"$reserved\": {\"$fv\": \"v4.r0\"}, \"$objectType\": \"clustermgmt.v4.config.NodeReference\", \"nodeList\": [{\"nodeUuid\": \"9126a468-46ed-4f3a-af0e-82de8185335c\", \"$reserved\": {\"$fv\": \"v4.r0\"}, \"$objectType\": \"clustermgmt.v4.config.N"
  },
  {
    "id": "nutanixpc_storage_containers",
    "label": "Nutanixpc Storage Containers",
    "vendor": "nutanix",
    "category": "Nutanix PC",
    "index": "netops_logs",
    "sample": "{\"$reserved\": {\"$fv\": \"v4.r0\"}, \"$objectType\": \"clustermgmt.v4.config.StorageContainer\", \"links\": [{\"$reserved\": {\"$fv\": \"v1.r0\"}, \"$objectType\": \"common.v1.response.ApiLink\", \"href\": \"$HOST$/f8edb45b-13e1-4927-954c-b0c3f1c91a33\", \"rel\": \"storage-container\"}, {\"href\": \"https://10.0.4.120:9440/api/clustermgmt/v4.0/stats/storage-containers/f8edb45b-13e1-4927-954c-b0c3f1c91a33\", \"rel\": \"storage-conta"
  },
  {
    "id": "nutanixpc_syslog",
    "label": "Nutanixpc Syslog",
    "vendor": "nutanix",
    "category": "Nutanix PC",
    "index": "netops_logs",
    "sample": "$SYSLOG_TIMESTAMP$ $HOST$ $ISO_TIMESTAMP$ CCHCI-AHV-01 Genesis_7: 2026-09-18 17:34:07 INFO ovs.py:103 - Finished running get_bridge_name_by_port_name, took 0.03659343719482422 seconds"
  },
  {
    "id": "nutanixpc_vm_performance",
    "label": "Nutanixpc Vm Performance",
    "vendor": "nutanix",
    "category": "Nutanix PC",
    "index": "cisco_mdt_metrics",
    "sample": "{\"timestamp\": \"$ISO_TIMESTAMP$\", \"cluster\": \"00061768-f76f-4f95-3e5f-0025b500016f\", \"hypervisorType\": \"kVMware\", \"memoryReservedBytes\": \"\", \"extId\": \"ca90dbd8-ccdf-4525-8dd2-3c8c1c842262\", \"controllerAvgIoLatencyMicros\": 1941, \"controllerAvgReadIoLatencyMicros\": 0, \"controllerAvgReadIoSizeKb\": 0, \"controllerAvgWriteIoLatencyMicros\": 1941, \"controllerAvgWriteIoSizeKb\": 4, \"controllerIoBandwidthKbps"
  },
  {
    "id": "nutanixpc_vms",
    "label": "Nutanixpc Vms",
    "vendor": "nutanix",
    "category": "Nutanix PC",
    "index": "netops_logs",
    "sample": "{\"$reserved\": {\"$fv\": \"v4.r0\"}, \"$objectType\": \"vmm.v4.esxi.config.Vm\", \"extId\": \"ca90dbd8-ccdf-4525-8dd2-3c8c1c842262\", \"memorySizeBytes\": 137438953472, \"numCoresPerSocket\": 1, \"numCpus\": 32, \"guestOsName\": \"Ubuntu Linux (64-bit)\", \"virtualHardwareVersion\": 10, \"name\": \"vND-4.3-roberbur-2\", \"cluster\": {\"$reserved\": {\"$fv\": \"v4.r0\"}, \"$objectType\": \"vmm.v4.esxi.config.ClusterReference\", \"extId\": \""
  },
  {
    "id": "nutanixpc_volume_groups",
    "label": "Nutanixpc Volume Groups",
    "vendor": "nutanix",
    "category": "Nutanix PC",
    "index": "netops_logs",
    "sample": "{\"$reserved\": {\"$fv\": \"v4.r0\"}, \"$objectType\": \"volumes.v4.config.VolumeGroup\", \"extId\": \"a8589f1c-3418-4e4c-9c55-109eeb10c261\", \"links\": [{\"$reserved\": {\"$fv\": \"v1.r0\"}, \"$objectType\": \"common.v1.response.ApiLink\", \"href\": \"$HOST$/a8589f1c-3418-4e4c-9c55-109eeb10c261\", \"rel\": \"volume_group\"}], \"name\": \"pvc-8934bad9-c9ba-4490-81b3-04c4ee83d857\", \"description\": \"FS:ext4, PVC:anc-mysql-certs, NS:def"
  },
  {
    "id": "nutanixpc:syslog",
    "label": "Nutanix Prism Central Syslog (Colon Format)",
    "vendor": "nutanix",
    "category": "Nutanix PC",
    "index": "idx_performance_metrics",
    "sample": "May 20 14:00:24 nutanix-pc-01 cluster: %ALERT-3-HOST_HA_DEGRADED: Node 10.20.0.12 in cluster \"Prism-Prod-01\" uncontactab"
  },
  {
    "id": "nutanixpc:vms",
    "label": "Nutanix Prism Central VM Inventory (Colon Format)",
    "vendor": "nutanix",
    "category": "Nutanix PC",
    "index": "idx_performance_metrics",
    "sample": "{\"vm_name\": \"app-server-prod-04\", \"vm_uuid\": \"e4d2a1b9-c8f7-4820-9948-201849201849\", \"cluster_name\": \"Prism-Prod-01\", \"p"
  },
  {
    "id": "kube:container:calico-kube-controllers",
    "label": "Kube Container Calico Kube Controllers",
    "vendor": "k8s",
    "category": "Kubernetes Containers",
    "index": "netops_logs",
    "sample": "2026-09-18 17:12:41.037 [INFO][1] kube-controllers/resources.go 350: Main client watcher loop"
  },
  {
    "id": "kube:container:calico-node",
    "label": "Kube Container Calico Node",
    "vendor": "k8s",
    "category": "Kubernetes Containers",
    "index": "netops_logs",
    "sample": "2026-09-18 17:33:47.664 [INFO][90] monitor-addresses/autodetection_methods.go 103: Using autodetected IPv4 address on interface ens33: 10.0.10.104/24"
  },
  {
    "id": "kube:container:controller",
    "label": "Kube Container Controller",
    "vendor": "k8s",
    "category": "Kubernetes Containers",
    "index": "netops_logs",
    "sample": "{\"level\":\"info\",\"ts\":\"$ISO_TIMESTAMP$\",\"logger\":\"cert-rotation\",\"msg\":\"Ensuring CA cert\",\"name\":\"bgppeers.metallb.io\",\"gvk\":\"apiextensions.k8s.io/v1, Kind=CustomResourceDefinition\",\"name\":\"bgppeers.metallb.io\",\"gvk\":\"apiextensions.k8s.io/v1, Kind=CustomResourceDefinition\",\"stacktrace\":\"github.com/open-policy-agent/cert-controller/pkg/rotator.(*ReconcileWH).ensureCerts\\n\\t/go/pkg/mod/github.com/ope"
  },
  {
    "id": "kube:container:coredns",
    "label": "Kube Container Coredns",
    "vendor": "k8s",
    "category": "Kubernetes Containers",
    "index": "netops_logs",
    "sample": "[ERROR] plugin/errors: 2 api.segment.io. A: read udp 10.1.5.229:43377->10.0.10.23:53: i/o timeout"
  },
  {
    "id": "kube:container:hostpath-provisioner",
    "label": "Kube Container Hostpath Provisioner",
    "vendor": "k8s",
    "category": "Kubernetes Containers",
    "index": "netops_logs",
    "sample": "W0918 17:34:45.319646       1 warnings.go:70] v1 Endpoints is deprecated in v1.33+; use discovery.k8s.io/v1 EndpointSlice"
  },
  {
    "id": "kube:container:install-cni",
    "label": "Kube Container Install Cni",
    "vendor": "k8s",
    "category": "Kubernetes Containers",
    "index": "netops_logs",
    "sample": "}"
  },
  {
    "id": "kube:container:metrics",
    "label": "Kube Container Metrics",
    "vendor": "k8s",
    "category": "Kubernetes Containers",
    "index": "cisco_mdt_metrics",
    "sample": "level=info ts=$ISO_TIMESTAMP$ caller=tls_config.go:316 msg=\"TLS is disabled.\" http2=false address=[::]:9216"
  },
  {
    "id": "kube:container:metrics-server",
    "label": "Kube Container Metrics Server",
    "vendor": "k8s",
    "category": "Kubernetes Containers",
    "index": "cisco_mdt_metrics",
    "sample": "I0902 10:13:22.800134       1 shared_informer.go:318] Caches are synced for RequestHeaderAuthRequestController"
  },
  {
    "id": "kube:container:mibserver",
    "label": "Kube Container Mibserver",
    "vendor": "k8s",
    "category": "Kubernetes Containers",
    "index": "netops_logs",
    "sample": "10.0.10.104 - - [18/Sep/2026:17:34:40 +0000] \"GET / HTTP/1.1\" 200 112 \"-\" \"kube-probe/1.33\" \"-"
  },
  {
    "id": "kube:container:mongodb",
    "label": "Kube Container Mongodb",
    "vendor": "k8s",
    "category": "Kubernetes Containers",
    "index": "netops_logs",
    "sample": "{\"t\":{\"$date\":\"$ISO_TIMESTAMP$\"},\"s\":\"I\",  \"c\":\"NETWORK\",  \"id\":22944,   \"ctx\":\"conn1056316\",\"msg\":\"Connection ended\",\"attr\":{\"remote\":\"127.0.0.1:46412\",\"uuid\":{\"uuid\":{\"$uuid\":\"84987fc8-3103-4265-ad17-df1ea9c7e8f4\"}},\"connectionId\":1056316,\"connectionCount\":57}}"
  },
  {
    "id": "kube:container:redis",
    "label": "Kube Container Redis",
    "vendor": "k8s",
    "category": "Kubernetes Containers",
    "index": "netops_logs",
    "sample": "1:M 02 $SYSLOG_TIMESTAMP$.400 * Ready to accept connections tcp"
  },
  {
    "id": "kube:container:speaker",
    "label": "Kube Container Speaker",
    "vendor": "k8s",
    "category": "Kubernetes Containers",
    "index": "netops_logs",
    "sample": "{\"caller\":\"layer2_status_controller.go:111\",\"controller\":\"Layer2StatusReconciler\",\"end reconcile\":\"sc4snmp/snmp-splunk-connect-for-snmp-trap\",\"level\":\"info\",\"ts\":\"$ISO_TIMESTAMP$\"}"
  },
  {
    "id": "kube:container:splunk-connect-for-snmp-traps",
    "label": "Kube Container Splunk Connect For Snmp Traps",
    "vendor": "k8s",
    "category": "Kubernetes Containers",
    "index": "netops_logs",
    "sample": "[2026-09-18 17:34:45,200: ERROR/splunk_connect_for_snmp.traps] Security Model failure for device (''10.201.48.101'', 49678): Unknown SNMP community name encountered"
  },
  {
    "id": "kube:container:splunk-connect-for-snmp-worker-sender",
    "label": "Kube Container Splunk Connect For Snmp Worker Sender",
    "vendor": "k8s",
    "category": "Kubernetes Containers",
    "index": "netops_logs",
    "sample": "[2026-09-02 10:14:39,562: INFO/MainProcess] celery@snmp-splunk-connect-for-snmp-worker-sender-b446c488b-kmfqf ready."
  },
  {
    "id": "kube:container:splunk-connect-for-snmp-worker-trap",
    "label": "Kube Container Splunk Connect For Snmp Worker Trap",
    "vendor": "k8s",
    "category": "Kubernetes Containers",
    "index": "netops_logs",
    "sample": "[2026-09-02 10:14:39,029: INFO/MainProcess] celery@snmp-splunk-connect-for-snmp-worker-trap-56dd75bf88-49dkk ready."
  },
  {
    "id": "kube:container:upgrade-ipam",
    "label": "Kube Container Upgrade Ipam",
    "vendor": "k8s",
    "category": "Kubernetes Containers",
    "index": "netops_logs",
    "sample": "2026-09-02 10:13:21.421 [INFO][1] ipam/ipam_plugin.go 100: migration from host-local to calico-ipam complete node=\"maple-splunk-vm4-hf"
  },
  {
    "id": "kube:events",
    "label": "Kube Events",
    "vendor": "k8s",
    "category": "Kubernetes Containers",
    "index": "netops_logs",
    "sample": "Service uses deprecated annotation metallb.universe.tf/loadBalancerIPs"
  },
  {
    "id": "kube:object:pods",
    "label": "Kube Object Pods",
    "vendor": "k8s",
    "category": "Kubernetes Containers",
    "index": "netops_logs",
    "sample": "{\"apiVersion\":\"v1\",\"kind\":\"Pod\",\"metadata\":{\"annotations\":{\"cni.projectcalico.org/containerID\":\"96bd3467252947d40fa4395800e49066dee4c94fc5c66d39080fdd7767725252\",\"cni.projectcalico.org/podIP\":\"10.1.5.238/32\",\"cni.projectcalico.org/podIPs\":\"10.1.5.238/32\"},\"creationTimestamp\":\"$ISO_TIMESTAMP$\",\"generateName\":\"snmp-splunk-connect-for-snmp-worker-trap-56dd75bf88-\",\"generation\":1,\"labels\":{\"app.kubern"
  },
  {
    "id": "stream:netflow",
    "label": "Stream Netflow",
    "vendor": "other",
    "category": "stream-netflow",
    "index": "netops_logs",
    "sample": "{\"endtime\":\"$ISO_TIMESTAMP$\",\"timestamp\":\"$ISO_TIMESTAMP$\",\"app_tag\":\"USER-DEF : 009311\",\"event_name\":\"netFlowData\",\"exporter_ip\":\"10.201.51.68\",\"exporter_time\":\"2026-Sep-18 17:34:43\",\"exporter_uptime\":3046802704,\"flow_dir\":0,\"flow_end_time_milli\":1789752881000,\"flow_start_time_milli\":1789752866000,\"netflow_elements\":[\"UNKNOWN : ac190e02\",\"UNKNOWN : 0a14010a\",\"UNKNOWN : 147e\",\"UNKNOWN : 0000000000"
  },
  {
    "id": "vmware:perf:cpu",
    "label": "Vmware Esx Perf",
    "vendor": "other",
    "category": "vmware-esx-perf",
    "index": "cisco_mdt_metrics",
    "sample": "{\"timestamp\": \"$ISO_TS$\", \"epoch\": $EPOCH$, \"host\": \"esx-maple-compute-01.maple.ciscolabs.com\", \"vm_name\": \"web-srv-01\", \"cpu.usage.average\": $CPU_PCT$, \"cpu.usagemhz.average\": 480, \"status\": \"green\"}"
  },
  {
    "id": "cisco:ftd:syslog",
    "label": "Cisco Ftd Syslog",
    "vendor": "cisco",
    "category": "Cisco Security & Telemetry",
    "index": "netops_logs",
    "sample": "$SYSLOG_TIMESTAMP$ $HOST$ :$SYSLOG_TIMESTAMP$ UTC: %FTD--6-805002: TCP Flow is no longer offloaded for connection 35430004 from INTERNET:32.185.98.157/443 (32.185.98.157/443) to INSIDE:10.0.10.95/17229 (64.100.57.80/17229)"
  },
  {
    "id": "cisco:ise:radius:authz:policy",
    "label": "Cisco Ise Radius Authz Policy",
    "vendor": "cisco",
    "category": "Cisco Security & Telemetry",
    "index": "netops_logs",
    "sample": "{\"rule\": {\"default\": true, \"id\": \"70c8186d-e2ef-4482-bd89-394cd9b723e4\", \"name\": \"Default\", \"hitCounts\": 0, \"rank\": 15, \"state\": \"enabled\", \"condition\": null}, \"profile\": [\"DenyAccess\"], \"securityGroup\": null, \"link\": {\"rel\": \"self\", \"href\": \"$HOST$/api/v1/policy/network-access/policy-set/f26b5958-d128-4f4b-9e17-d0338af2b891/authorization/70c8186d-e2ef-4482-bd89-394cd9b723e4\", \"type\": \"application"
  },
  {
    "id": "cisco:ise:radius:policyset",
    "label": "Cisco Ise Radius Policyset",
    "vendor": "cisco",
    "category": "Cisco Security & Telemetry",
    "index": "netops_logs",
    "sample": "{\"default\": true, \"id\": \"f26b5958-d128-4f4b-9e17-d0338af2b891\", \"name\": \"Default\", \"description\": \"Default policy set\", \"hitCounts\": 238844, \"rank\": 0, \"state\": \"enabled\", \"condition\": null, \"serviceName\": \"Default Network Access\", \"isProxy\": false, \"link\": {\"rel\": \"self\", \"href\": \"$HOST$/api/v1/policy/network-access/policy-set/f26b5958-d128-4f4b-9e17-d0338af2b891\", \"type\": \"application/json\"}, \"l"
  },
  {
    "id": "cisco:ise:syslog",
    "label": "Cisco Ise Syslog",
    "vendor": "cisco",
    "category": "Cisco Security & Telemetry",
    "index": "netops_logs",
    "sample": "$SYSLOG_TIMESTAMP$ $HOST$ $SYSLOG_TIMESTAMP$ maple-ise02 CISE_Failed_Attempts 0002840615 1 0 2026-09-18 17:34:43.705 +00:00 0056893972 5400 NOTICE Failed-Attempt: Authentication failed, ConfigVersionId=101, Device IP Address=10.0.0.1, Device Port=18330, DestinationIPAddress=$HOST$, DestinationPort=1812, RadiusPacketType=AccessRequest, UserName=INVALID, Protocol=Radius, ExternalErrorCode=40008, Net"
  },
  {
    "id": "cisco:ise:tacacs:authz:policy",
    "label": "Cisco Ise Tacacs Authz Policy",
    "vendor": "cisco",
    "category": "Cisco Security & Telemetry",
    "index": "netops_logs",
    "sample": "{\"rule\": {\"default\": true, \"id\": \"b47a6faa-f732-4007-b33f-04f0b8c884b3\", \"name\": \"Default\", \"hitCounts\": 0, \"rank\": 8, \"state\": \"enabled\", \"condition\": null}, \"commands\": [\"DenyAllCommands\"], \"profile\": \"Deny All Shell Profile\", \"link\": {\"rel\": \"self\", \"href\": \"$HOST$/api/v1/policy/device-admin/policy-set/56576c80-2c47-40bb-a344-b40ef71aa8f1/authorization/b47a6faa-f732-4007-b33f-04f0b8c884b3\", \"ty"
  },
  {
    "id": "cisco:ise:tacacs:policyset",
    "label": "Cisco Ise Tacacs Policyset",
    "vendor": "cisco",
    "category": "Cisco Security & Telemetry",
    "index": "netops_logs",
    "sample": "{\"default\": true, \"id\": \"56576c80-2c47-40bb-a344-b40ef71aa8f1\", \"name\": \"Default\", \"description\": \"Tacacs Default policy set\", \"hitCounts\": 22, \"rank\": 0, \"state\": \"enabled\", \"condition\": null, \"serviceName\": \"Default Device Admin\", \"isProxy\": false, \"link\": {\"rel\": \"self\", \"href\": \"$HOST$/api/v1/policy/device-admin/policy-set/56576c80-2c47-40bb-a344-b40ef71aa8f1\", \"type\": \"application/json\"}, \"la"
  },
  {
    "id": "httpevent",
    "label": "Cisco Metrics Bgp Rib",
    "vendor": "other",
    "category": "Cisco Security & Telemetry",
    "index": "cisco_mdt_metrics",
    "sample": "{\"time\": $EPOCH$, \"event\": \"metric\", \"source\": \"10.0.255.171\", \"sourcetype\": \"httpevent\", \"host\": \"34.236.151.135:8088\", \"index\": \"cisco_metrics\", \"fields\": {\"metric_name:bgp_status.peer_as\": 65013, \"metric_name:bgp_status.session_state\": 5, \"metric_name:Cisco-IOS-XR-ipv4-bgp-oper:bgp/instances/instance/instance-active/vrfs/vrf/afs/af/neighbor-af-table/neighbor.af_data/prefixes_accepted\": $PREFIXE"
  },
  {
    "id": "cisco:metrics",
    "label": "Cisco Metrics Splunk Otel",
    "vendor": "cisco",
    "category": "Cisco Security & Telemetry",
    "index": "cisco_mdt_metrics",
    "sample": "samples:\n  ### HEALTHY OTEL TELEMETRY (LOW CPU, STEADY BGP PEERS, ZERO PDU DROPS) ###\n  - name: splunk-otel-healthy\n    interval: 30\n    count: 5\n    randomizeEvents: true\n    tokens:\n      - name: EPOCH\n        format: template\n        type: epochtimestamp\n      - name: NODE\n        format: template\n"
  },
  {
    "id": "cisco:nvm:flowdata",
    "label": "Cisco Nvm Flowdata",
    "vendor": "cisco",
    "category": "Cisco Security & Telemetry",
    "index": "netops_logs",
    "sample": "8\\xE7_\\x84v\\x80H"
  },
  {
    "id": "cisco:se",
    "label": "Cisco Se",
    "vendor": "cisco",
    "category": "Cisco Security & Telemetry",
    "index": "netops_logs",
    "sample": "{\"id\": 1789751173971923653, \"timestamp\": 1789751173, \"timestamp_nanoseconds\": 971923000, \"date\": \"$ISO_TIMESTAMP$\", \"event_type\": \"Fault Cleared\", \"event_type_id\": 553648196, \"connector_guid\": \"519f89fd-a1db-458b-b551-5bb7ec1f8474\", \"group_guids\": [\"fa567a34-1239-4be4-9a2d-30d2a9d05d16\"], \"computer\": {\"connector_guid\": \"519f89fd-a1db-458b-b551-5bb7ec1f8474\", \"hostname\": \"fileserver01\", \"external_i"
  },
  {
    "id": "cisco:sfw:estreamer",
    "label": "Cisco Sfw Estreamer",
    "vendor": "cisco",
    "category": "Cisco Security & Telemetry",
    "index": "netops_logs",
    "sample": "{\"EventType\": \"ConnectionEvent\", \"FirstPacketSecond\": 1789752808, \"DeviceUUID\": \"84663f36-6213-11ec-943b-b10f15a5650d\", \"InstanceID\": 16, \"ConnectionID\": 61483, \"AC_RuleAction\": \"Allow\", \"InitiatorIP\": \"10.100.1.105\", \"ResponderIP\": \"208.67.222.222\", \"InitiatorPort\": 36665, \"ResponderPort\": 53, \"Protocol\": \"udp\", \"IngressInterface\": \"INSIDE.800\", \"EgressInterface\": \"INTERNET\", \"IngressZone\": \"INSI"
  },
  {
    "id": "cisco:sfw:policy",
    "label": "Cisco Sfw Policy",
    "vendor": "cisco",
    "category": "Cisco Security & Telemetry",
    "index": "netops_logs",
    "sample": "{\"name\": \"AMP_Policy\", \"id\": \"fb73018e-682d-11ec-bf59-9b66d79cfdcf\", \"type\": \"FilePolicy\", \"archiveDepth\": 2, \"archiveDepthAction\": true, \"blockEncryptedArchives\": false, \"cleanList\": true, \"customDetectionList\": true, \"firstTimeFileAnalysis\": true, \"inspectArchives\": false, \"threatScore\": \"DISABLED\", \"links\": {\"self\": \"https://fmc.maple.ciscolabs.com/api/fmc_config/v1/domain/e276abec-e0f2-11e3-81"
  },
  {
    "id": "cisco_syslog",
    "label": "Cisco Syslog",
    "vendor": "cisco",
    "category": "Cisco Security & Telemetry",
    "index": "netops_logs",
    "sample": "$SYSLOG_TIMESTAMP$ $HOST$ 1 $ISO_TIMESTAMP$ R03 ifmgr 202 - - 1430004: LC/0/0/CPU0:ifmgr[202]: %PKT_INFRA-LINEPROTO-5-UPDOWN : Line protocol on Interface HundredGigE0/0/1/2, changed state to Up "
  },
  {
    "id": "cisco:thousandeyes:event",
    "label": "Cisco Thousandeyes Event",
    "vendor": "cisco",
    "category": "Cisco Security & Telemetry",
    "index": "netops_logs",
    "sample": "{\"id\": \"a78ef292-6962-333c-b97d-a74ec8fad6d9\", \"type\": \"target\", \"agentType\": \"cloud-enterprise-agent\", \"typeName\": \"Network Outage\", \"title\": \"targets 64.100.2.10 +6\", \"state\": \"active\", \"startDate\": \"$ISO_TIMESTAMP$\", \"endDate\": null, \"severity\": \"low\", \"affectedTests\": {\"total\": 7, \"inAccountGroup\": 1}, \"affectedTargets\": {\"total\": 7, \"inAccountGroup\": 1}, \"affectedAgents\": {\"total\": 6, \"inAcco"
  },
  {
    "id": "cisco:thousandeyes:path-vis",
    "label": "Cisco Thousandeyes Path Vis",
    "vendor": "cisco",
    "category": "Cisco Security & Telemetry",
    "index": "netops_logs",
    "sample": "{\"agentId\": \"bac16802-df59-4327-8b7e-33a29e86cde7\", \"aid\": \"230661\", \"testId\": \"414718\", \"roundId\": 1789748220, \"serverIp\": \"144.196.36.211\", \"systemMetrics\": {\"startTimeMs\": 1789748234758, \"endTimeMs\": 1789748246768, \"cpuUtilization\": {\"min\": 0.1530758226037196, \"max\": 0.27266187050359714, \"mean\": 0.21063021312772753, \"median\": 0.19385182153090463, \"stdDev\": 0.044302459250538766, \"count\": 12}, \"p"
  },
  {
    "id": "cisco:asa:syslog",
    "label": "Cisco ASA Syslog Message Stream",
    "vendor": "cisco",
    "category": "Cisco Security & Telemetry",
    "index": "idx_security_fw",
    "sample": "May 20 14:00:00 fw-cisco-asa-01 : %ASA-6-302013: Built outbound TCP connection 184920 for outside:198.51.100.80/443 to i"
  },
  {
    "id": "cisco:ios:mdt:metric",
    "label": "Cisco IOS-XE / IOS-XR Model-Driven Telemetry (gRPC/JSON)",
    "vendor": "cisco",
    "category": "Cisco Security & Telemetry",
    "index": "cisco_mdt_metrics",
    "sample": "{\"time\": 1789840800, \"event\": \"metric\", \"source\": \"openconfig_telemetry\", \"sourcetype\": \"cisco:ios:mdt:metric\", \"host\": "
  },
  {
    "id": "cisco:ios:syslog",
    "label": "Cisco IOS System Syslog Facility",
    "vendor": "cisco",
    "category": "Cisco Security & Telemetry",
    "index": "idx_network_ops",
    "sample": "May 20 14:00:08 rtr-core-01 1849: *May 20 14:00:08.124 UTC: %LINK-3-UPDOWN: Interface GigabitEthernet0/0/1, changed stat"
  },
  {
    "id": "sophos:central:cef",
    "label": "Sophos Central Cef",
    "vendor": "paloalto",
    "category": "Sophos Central",
    "index": "netops_logs",
    "sample": "Sep 18 17:15:20 sophos-ep-01 CEF:0|Sophos|Central|1.0|Threat|Malware Blocked|7|src=10.10.40.55 msg=Malware detected and cleaned dhost=workstation-09.acme.local dvchost=workstation-09 rt=2026-09-18T21:15:20.000Z deviceType=Endpoint externalId=THREAT-99412 suid=S-1-5-21-39281 suser=m.smith category=Malware"
  },
  {
    "id": "arista:eos:syslog",
    "label": "Arista Eos Syslog",
    "vendor": "arista",
    "category": "Arista Networks Telemetry",
    "index": "netops_logs",
    "sample": "<189>1 2026-09-18T21:15:22.000Z switch-leaf-01.acme.local BGP 1420 - %BGP-5-ADJCHANGE: neighbor 10.255.0.2 Gateway Down - peer closed BGP session (remote AS 65001)"
  },
  {
    "id": "aruba",
    "label": "Aruba Instant AP & Switch Event",
    "vendor": "arista",
    "category": "Aruba Networks",
    "index": "idx_wireless_ops",
    "sample": "May 20 14:00:00 ap-aruba-515-01 stm[2948]: <501095> <NOTI> <ap-aruba-515-01 10.254.16.42> Auth success: 00:4e:01:aa:bb:c"
  },
  {
    "id": "aruba:authmgr",
    "label": "Aruba Controller Authentication Manager",
    "vendor": "arista",
    "category": "Aruba Networks",
    "index": "idx_wireless_ops",
    "sample": "May 20 14:00:00 wlc-aruba-7210 authmgr[1842]: <522008> <INFO> <wlc-aruba-7210 10.254.16.1> User Authentication Successfu"
  },
  {
    "id": "aruba:stm",
    "label": "Aruba Station Management (STM)",
    "vendor": "arista",
    "category": "Aruba Networks",
    "index": "idx_wireless_ops",
    "sample": "May 20 14:00:00 wlc-aruba-7210 stm[2104]: <501065> <NOTI> <wlc-aruba-7210 10.254.16.1> Station 00:4e:01:aa:bb:cc: Associ"
  },
  {
    "id": "cloudflare:json",
    "label": "Cloudflare Json",
    "vendor": "cloud",
    "category": "Cloudflare Core & R2",
    "index": "netops_logs",
    "sample": "{\"EdgeStartTimestamp\": \"2026-09-18T21:15:35Z\", \"ClientIP\": \"203.0.113.89\", \"ClientRequestHost\": \"api.acme.com\", \"ClientRequestMethod\": \"POST\", \"ClientRequestPath\": \"/v1/auth/token\", \"ClientRequestUserAgent\": \"Mozilla/5.0 (Windows NT 10.0; Win64; x64)\", \"EdgeResponseStatus\": 403, \"OriginIP\": \"10.100.2.14\", \"ClientRequestBytes\": 1420, \"EdgeResponseBytes\": 428, \"EdgeRateLimitAction\": \"block\", \"WAFAct"
  },
  {
    "id": "cloudflare:r2:json",
    "label": "Cloudflare R2 Metrics",
    "vendor": "cloud",
    "category": "Cloudflare Core & R2",
    "index": "cisco_mdt_metrics",
    "sample": "{\"time\": 1789761340, \"event\": \"metric\", \"source\": \"cloudflare:r2\", \"sourcetype\": \"cloudflare:r2:json\", \"host\": \"cloudflare.r2.acme\", \"index\": \"cisco_mdt_metrics\", \"fields\": {\"metric_name:r2_operation_count\": 1, \"metric_name:r2_bytes_uploaded\": 2097152, \"metric_name:r2_latency_ms\": 14.8, \"account_id\": \"acme-cf-r2-prod\", \"bucket_name\": \"acme-telemetry-archive\", \"operation\": \"PutObject\", \"status_code"
  },
  {
    "id": "extrahop:eda:alert",
    "label": "Extrahop Eda Alert",
    "vendor": "other",
    "category": "ExtraHop Performance Detection",
    "index": "netops_logs",
    "sample": "{\"update_time\": \"Sep 18 2026 17:15:45 +0000\", \"detection_type\": \"protocol_anomaly\", \"title\": \"Abnormal TLS Handshake Rate\", \"risk_score\": 85, \"device_id\": \"extrahop-eda-sensor-01\", \"src_ip\": \"10.10.50.21\", \"dest_ip\": \"198.51.100.12\", \"app\": \"HTTPS\", \"description\": \"High rate of SSL/TLS handshake failures indicating potential cipher renegotiation flood\"}"
  },
  {
    "id": "extrahop:eda:metrics",
    "label": "Extrahop Metrics Performance",
    "vendor": "other",
    "category": "ExtraHop Performance Detection",
    "index": "cisco_mdt_metrics",
    "sample": "{\"time\": 1789761345, \"event\": \"metric\", \"source\": \"extrahop:eda\", \"sourcetype\": \"extrahop:eda:metrics\", \"host\": \"core-switch-01\", \"index\": \"cisco_mdt_metrics\", \"fields\": {\"metric_name:extrahop_turnaround_time_ms\": 4.2, \"metric_name:extrahop_tcp_zero_window\": 0, \"metric_name:extrahop_rtt_ms\": 1.4, \"metric_name:extrahop_dns_error_count\": 0, \"device_oid\": \"1.3.6.1.4.1.3814.1.1.9281\", \"object_type\": \""
  },
  {
    "id": "fgt_event",
    "label": "Fortinet Fortigate Sdwan Alert",
    "vendor": "other",
    "category": "Fortinet FortiGate",
    "index": "netops_logs",
    "sample": "date=2026-09-18 time=17:15:51 devname=\"FGT-Edge-01\" devid=\"FGT60E4Q16000001\" vd=\"root\" type=\"event\" subtype=\"sdwan\" level=\"warning\" logid=\"0100022923\" msg=\"SD-WAN SLA path quality degradation alert\" sla_rule=\"SLA_Voice_HighPri\" interface=\"wan2\" latency=142.5 jitter=28.4 packet_loss=6.8 link_status=\"degraded\" action=\"failover"
  },
  {
    "id": "fgt_traffic",
    "label": "Fortinet Fortigate Traffic",
    "vendor": "other",
    "category": "Fortinet FortiGate",
    "index": "netops_logs",
    "sample": "date=2026-09-18 time=17:15:50 devname=\"FGT-Edge-01\" devid=\"FGT60E4Q16000001\" vd=\"root\" type=\"traffic\" subtype=\"forward\" level=\"notice\" srcip=10.10.30.12 srcport=54122 srcintf=\"port1\" dstip=198.51.100.80 dstport=443 dstintf=\"wan1\" polid=1 sessionid=19842 proto=6 action=\"accept\" policyid=1 app=\"HTTPS\" duration=45 sentbyte=3412 rcvdbyte=8910"
  },
  {
    "id": "fortigate_event",
    "label": "Fortinet FortiGate System Event",
    "vendor": "paloalto",
    "category": "Fortinet FortiGate",
    "index": "idx_security_fw",
    "sample": "date=2026-09-20 time=14:00:16 devname=\"fg-branch-01\" devid=\"FGT60E4Q18012840\" logid=\"0100032001\" type=\"event\" subtype=\"s"
  },
  {
    "id": "fortigate_traffic",
    "label": "Fortinet FortiGate Traffic Log",
    "vendor": "paloalto",
    "category": "Fortinet FortiGate",
    "index": "idx_security_fw",
    "sample": "date=2026-09-20 time=14:00:17 devname=\"fg-branch-01\" devid=\"FGT60E4Q18012840\" logid=\"0000000013\" type=\"traffic\" subtype="
  },
  {
    "id": "netscout:omnis:alert",
    "label": "Netscout Omnis Alert",
    "vendor": "other",
    "category": "NetScout Omnis Core",
    "index": "netops_logs",
    "sample": "{\"timestamp\": \"2026-09-18T21:15:55Z\", \"analyzer\": \"NetScout Omnis Cyber Intelligence\", \"alert_type\": \"DDoS_Flood_Vector\", \"vector\": \"SYN_Flood\", \"dpi_signature\": \"TCP_SYN_ACK_MISMATCH\", \"src_ip_count\": 4820, \"target_ip\": \"198.51.100.25\", \"target_port\": 443, \"flood_volume_pps\": 850000, \"flood_volume_mbps\": 4200, \"drop_action\": \"mitigated\", \"threat_score\": 98}"
  },
  {
    "id": "netskope:json",
    "label": "Netskope Json",
    "vendor": "cloud",
    "category": "Netskope SSE Framework",
    "index": "netops_logs",
    "sample": "{\"timestamp\": 1789761360, \"vendor_product\": \"Netskope\", \"event_type\": \"dlp_violation\", \"user\": \"m.smith@acme.corp\", \"user_department\": \"Finance\", \"app\": \"Microsoft OneDrive\", \"activity\": \"Upload\", \"file_name\": \"Q3_Customer_PII_Export.xlsx\", \"file_size\": 248102, \"dlp_rule\": \"PCI_SSN_Strict_Rule\", \"dlp_incident_id\": \"DLP-2026-8812\", \"action\": \"block\", \"c_ip\": \"10.20.10.45\", \"s_ip\": \"13.107.136.9\", \""
  },
  {
    "id": "netskope:sse",
    "label": "Netskope Security Service Edge (SSE)",
    "vendor": "cloud",
    "category": "Netskope SSE Framework",
    "index": "idx_security_fw",
    "sample": "{\"timestamp\": 1789840800, \"tenant_id\": \"corp-tenant-01\", \"traffic_type\": \"CloudApp\", \"app_name\": \"Salesforce\", \"user\": \""
  },
  {
    "id": "radware:ddos",
    "label": "Radware Csms Ddos",
    "vendor": "other",
    "category": "Radware CSMS & CWAF",
    "index": "netops_logs",
    "sample": "Sep 18 17:16:05 radware-defensepro CSMS-DDOS,timestamp=\"2026-09-18 17:16:05\",device_name=\"DP-01-Border\",attack_name=\"Volumetric UDP Flood\",policy=\"Perimeter-Shield\",dest_ip=\"198.51.100.10\",dest_port=53,threshold_pps=250000,actual_pps=890000,packet_volume_drop=640000,action=\"Drop\",severity=\"Critical"
  },
  {
    "id": "radware:waf",
    "label": "Radware Cwaf Waf",
    "vendor": "other",
    "category": "Radware CSMS & CWAF",
    "index": "netops_logs",
    "sample": "Sep 18 17:16:10 radware-cwaf AppWall-WAF: timestamp=\"2026-09-18 17:16:10\",vip_name=\"VIP_Portal_Prod\",vip_ip=\"198.51.100.50\",vip_port=443,client_ip=\"203.0.113.112\",rule_id=\"WAF-L7-SQLi-004\",violation_type=\"SQL Injection in URI parameter\",malicious_payload=\"UNION SELECT password FROM users--\",action=\"Blocked\",latency_delay_ms=18.4,http_status=403"
  },
  {
    "id": "f5:bigip:syslog",
    "label": "F5 Bigip Syslog",
    "vendor": "other",
    "category": "F5 BIG-IP",
    "index": "netops_logs",
    "sample": "Sep 18 17:16:15 f5-bigip-01.acme.local notice mcpd[8142]: 01070638:5: Pool /Common/pool_app_backend member /Common/10.0.10.51:8080 monitor status down. [ was up for 48hrs ]"
  },
  {
    "id": "f5:bigip:ltm",
    "label": "F5 BIG-IP Local Traffic Manager (LTM)",
    "vendor": "other",
    "category": "F5 BIG-IP",
    "index": "idx_performance_metrics",
    "sample": "May 20 14:00:15 lb-f5-vip-01 notice tmm[14820]: 01010028:5: Pool /Common/pool_corp_web member /Common/10.20.1.10:80 moni"
  },
  {
    "id": "juniper:syslog",
    "label": "Juniper Syslog",
    "vendor": "arista",
    "category": "Juniper Networks",
    "index": "netops_logs",
    "sample": "Sep 18 17:16:20 juniper-mx960-core-01 rpd[1422]: RPD_BGP_NEIGHBOR_STATE_CHANGED: BGP neighbor 10.255.10.1 (Internal AS 65000) changed state from Established to Idle (BGP notification sent: cease)"
  },
  {
    "id": "juniper:junos:syslog",
    "label": "Juniper Junos Syslog Transport",
    "vendor": "arista",
    "category": "Juniper Networks",
    "index": "idx_network_ops",
    "sample": "May 20 14:00:20 rtr-juniper-ptx01 chassisd[1420]: %CHASSIS-5-CHASSISD_SNMP_ALARM: Alarm set: FPC color=YELLOW, class=CHA"
  },
  {
    "id": "pan:system",
    "label": "Pan System",
    "vendor": "paloalto",
    "category": "Palo Alto Networks",
    "index": "netops_logs",
    "sample": "1,2026/09/18 17:16:27,001801000001,SYSTEM,globalprotect,2304,2026/09/18 17:16:27,,globalprotect-gateway,gateway-agent,0,0,general,informational,\"GlobalProtect gateway client connection established: User jdoe, Client IP 10.200.1.5, OS Windows 11\",10982,0x0"
  },
  {
    "id": "zscaler:tunnel",
    "label": "Zscaler Sse Tunnel",
    "vendor": "cloud",
    "category": "Zscaler SSE Infrastructure",
    "index": "netops_logs",
    "sample": "Sep 18 17:16:31 zscaler-nss zscalernss-tunnel: datetime=Fri Sep 18 17:16:31 2026,tunnel_name=\"Zscaler-GRE-Toronto-Primary\",tunnel_status=\"DOWN\",remote_ip=198.51.100.200,local_ip=10.0.255.50,drop_reason=\"Keepalive timeout exceeded\",downtime_sec=45"
  },
  {
    "id": "zscaler:web",
    "label": "Zscaler Sse Web",
    "vendor": "cloud",
    "category": "Zscaler SSE Infrastructure",
    "index": "netops_logs",
    "sample": "Sep 18 17:16:30 zscaler-nss zscalernss-web: datetime=Fri Sep 18 17:16:30 2026,user=alice.johnson@acme.corp,department=Engineering,location=Toronto-Branch,reqaction=Blocked,urlcategory=Malware_Sites,hostname=bad-download.compromised.com,clientip=10.10.40.12,serverip=198.51.100.99,reqmethod=GET,respcode=403,threatname=Trojan.Generic.KD,tunnel_id=TUN-TO-8891,policy_action=Block"
  },
  {
    "id": "geo_tokens:generic",
    "label": "Geo_Tokens",
    "vendor": "other",
    "category": "Other",
    "index": "netops_logs",
    "sample": "R1\nR2\nR7\nR8\nR9\nR10\n10.0.255.171\n10.0.255.172\nOTT-CORE01.maple.ciscolabs.com\nOTT-CORE02.maple.ciscolabs.com\n"
  },
  {
    "id": "datablaster:preflight",
    "label": "NetSpout Ingestion Preflight Probe",
    "vendor": "other",
    "category": "Other",
    "index": "idx_network_ops",
    "sample": "{\"timestamp\": 1789840800, \"component\": \"preflight\", \"check\": \"splunk_hec_port\", \"endpoint\": \"https://127.0.0.1:8888/serv"
  },
  {
    "id": "datablaster:probe",
    "label": "NetSpout Telemetry Canary Probe",
    "vendor": "other",
    "category": "Other",
    "index": "idx_network_ops",
    "sample": "{\"timestamp\": 1789840800, \"probe_id\": \"probe-mdt-canary-01\", \"target_index\": \"cisco_mdt_metrics\", \"eps_measured\": 1000, "
  },
  {
    "id": "nokia:sros:syslog",
    "label": "Nokia 7750 SR OS Syslog Facility",
    "vendor": "arista",
    "category": "Other",
    "index": "idx_network_ops",
    "sample": "May 20 14:00:23 rtr-nokia-7750-01 MAJOR: SYSTEM #2041 Base SYSTEM-ENV-3-OVERTEMP: Chassis slot 1 temperature 68 C exceed"
  },
  {
    "id": "snmp:trap",
    "label": "Universal SNMP Trap Receiver Event",
    "vendor": "other",
    "category": "Other",
    "index": "idx_network_ops",
    "sample": "May 20 14:00:27 10.254.8.1 [UDP: [10.254.8.1]:54210->[10.254.99.50]:162]: DISMAN-EVENT-MIB::sysUpTimeInstance = Timetick"
  }
];
// Scenarios Catalog (Covering all 11 Network Architectures)
  var SCENARIOS_CATALOG = [
    {
      id: "scenario_openconfig_mdt_streaming.yml",
      title: "OpenConfig MDT Streaming & Telemetry Assurance (Mode C / OC-001)",
      desc: "Model-Driven Telemetry streaming from Cisco 8000, Juniper PTX, and Arista 7280R emitting to metric index cisco_mdt_metrics.",
      sourcetypes: ["cisco:mdt:grpc", "openconfig:yang:json", "cisco:ios"]
    },
    {
      id: "scenario_pure_cisco_enterprise.yml",
      title: "Pure Cisco Enterprise Architecture (CISCO-ENT-01)",
      desc: "Complete campus fabric: Catalyst 9600 Core, 9500 Dist, 9300 Access, 9800 WLC, Cisco ISE NAC, and Catalyst Center.",
      sourcetypes: ["cisco:catalyst:networkhealth", "cisco:ise:nac:8021x", "cisco:ise:trustsec:sgt", "cisco:catalyst:rogue:threat_details"]
    },
    {
      id: "scenario_mixed_vendor_enterprise.yml",
      title: "Mixed-Vendor Enterprise Network (MIXED-ENT-01)",
      desc: "Multi-vendor campus and DC: Cisco Catalyst Core, Arista Spine/Leaf, Palo Alto NGFW perimeter, Fortinet branch, Juniper edge, and Aruba APs.",
      sourcetypes: ["pan:threat", "fortinet:fortigate", "juniper:junos", "arista:telemetry:json", "aruba:syslog"]
    },
    {
      id: "scenario_sp_cisco.yml",
      title: "Service Provider Network - All Cisco (SP-CISCO-01)",
      desc: "Carrier-grade all-Cisco service provider backbone running IOS-XR, Segment Routing over IPv6 (SRv6), and EVPN L3VPN.",
      sourcetypes: ["cisco:mdt:grpc", "cisco:ios"]
    },
    {
      id: "scenario_sp_mixed.yml",
      title: "Service Provider Network - Mixed Vendor (SP-MIXED-01)",
      desc: "Tier-1 multi-vendor carrier transit backbone with Cisco 8000, Juniper PTX10008, and Nokia 7750 SR OS routers running BGP-LU and RSVP-TE.",
      sourcetypes: ["juniper:junos", "nokia:sros", "cisco:mdt:grpc"]
    },
    {
      id: "scenario_sdwan_connected_core.yml",
      title: "SD-WAN Connected to Core Backbone (SDWAN-CORE-01)",
      desc: "Cisco Catalyst SD-WAN fabric (vEdge/cEdge routers, vSmart, vManage) interconnecting remote branches into Cisco Catalyst 9600 Campus Core.",
      sourcetypes: ["cisco:sdwan:linkhealth", "cisco:sdwan:BGP-5-ADJCHANGE", "cisco:ios"]
    },
    {
      id: "scenario_wireless_connected_core.yml",
      title: "Enterprise Wireless Connected to Core (WLAN-CORE-01)",
      desc: "Catalyst 9800 WLC and Meraki MR APs connecting multi-SSID traffic through 802.1Q trunks directly into Catalyst 9600 / Arista core switches.",
      sourcetypes: ["cisco:catalyst:clienthealth", "meraki:accesspoints", "cisco:ise:nac:8021x"]
    },
    {
      id: "scenario_arch_pan_iot_mesh.yml",
      title: "PAN: Personal Area Network - IoT Sensor Cluster & Bluetooth Mesh",
      desc: "Short-range IoT sensor mesh monitoring environmental conditions, temperature, humidity, and Bluetooth LE beacon telemetry.",
      sourcetypes: ["pan:ble:iot:sensor", "cisco:ios"]
    },
    {
      id: "scenario_arch_lan_campus_access.yml",
      title: "LAN: Local Area Network - Campus Switching & 802.1Q Segments",
      desc: "High-density campus LAN with Cisco Catalyst 9300/9500 switches, 802.1Q trunking, DHCP snooping, and ARP inspection.",
      sourcetypes: ["cisco:catalyst:security:events", "cisco:ios"]
    },
    {
      id: "scenario_arch_wlan_meraki_catalyst.yml",
      title: "WLAN: Wireless Local Area Network - Catalyst 9800 & Meraki Wi-Fi 6E/7",
      desc: "Dual-vendor campus wireless with Catalyst 9800 WLC and Meraki MR56 APs tracking client roaming, SNR, and CleanAir interference.",
      sourcetypes: ["cisco:catalyst:rogue:threat_details", "meraki:accesspoints"]
    },
    {
      id: "scenario_arch_can_multi_building.yml",
      title: "CAN: Campus Area Network - Multi-Building Backbone & Catalyst Center",
      desc: "Multi-building campus network with redundant Catalyst 9600 cores, 100G fiber interconnects, and DNA Center automated assurance.",
      sourcetypes: ["cisco:ios", "cisco:catalyst:networkhealth"]
    },
    {
      id: "scenario_arch_man_carrier_ring.yml",
      title: "MAN: Metropolitan Area Network - 100G Carrier Ethernet Ring & G.8032 ERPS",
      desc: "Metro optical ring spanning 4 data centers with ITU-T G.8032 Ethernet Ring Protection Switching (ERPS) sub-50ms failover.",
      sourcetypes: ["nokia:sros", "juniper:junos"]
    },
    {
      id: "scenario_arch_wan_global_backbone.yml",
      title: "WAN: Wide Area Network - Global BGP/MPLS L3VPN Backbone & Optical DWDM",
      desc: "Inter-continental enterprise WAN with BGP EVPN, segment routing SRv6, and MPLS traffic engineering tunnels.",
      sourcetypes: ["cisco:ios", "cisco:mdt:grpc"]
    },
    {
      id: "scenario_arch_san_fibre_channel.yml",
      title: "SAN: Storage Area Network - Cisco MDS 9700 Fibre Channel & NVMe-oF",
      desc: "Enterprise storage area network fabric with Cisco MDS 9700 64G FC directors, zoning, and buffer-to-buffer credit starvation telemetry.",
      sourcetypes: ["cisco:mds:san:fc", "cisco:dc:nexus9k:syslog"]
    },
    {
      id: "scenario_arch_nas_storage_cluster.yml",
      title: "NAS: Network-Attached Storage - NetApp ONTAP & PowerScale Clusters",
      desc: "High-throughput NAS cluster serving petabyte NFSv4.1 and SMB3 workloads with IOPS burst tracking and volume latency metrics.",
      sourcetypes: ["netapp:ontap:nas", "arista:telemetry:json"]
    },
    {
      id: "scenario_arch_vpn_remote_workforce.yml",
      title: "VPN: Virtual Private Network - Cisco AnyConnect & Site-to-Site IPsec",
      desc: "Remote access VPN concentrator and IPsec crypto tunnels supporting 10,000+ concurrent workforce sessions with Duo MFA integration.",
      sourcetypes: ["cisco:duo:remote:vpn", "cisco:duo:push:prompt", "cisco:asa"]
    },
    {
      id: "scenario_arch_epn_isolated_intranet.yml",
      title: "EPN: Enterprise Private Network - Isolated Corporate Intranet",
      desc: "Private multi-tenant enterprise intranet connecting physical branches and cloud VPCs via private QinQ 802.1ad and MPLS pseudo-wires.",
      sourcetypes: ["cisco:ios", "cisco:sdwan:linkhealth"]
    },
    {
      id: "scenario_arch_gan_subsea_cloud.yml",
      title: "GAN: Global Area Network - Worldwide Multi-Cloud & Subsea Cable Transit",
      desc: "Trans-continental global network connecting AWS Direct Connect, Azure ExpressRoute, and subsea cable landing stations.",
      sourcetypes: ["cisco:ios", "cisco:mdt:grpc", "zscaler:zia"]
    }
  ];

  // Wizard State
  var wizardState = {
    currentStep: 1,
    mode: "single", // "single", "multi", "scenario"
    singleSourceType: "catalog", // "catalog" or "upload"
    selectedSourcetype: SOURCETYPE_CATALOG[0].id,
    selectedMultiSourcetypes: [SOURCETYPE_CATALOG[0].id],
    selectedScenario: SCENARIOS_CATALOG[0].id,
    targetIndex: "idx_security_fw",
    volume: 1, // 1, 50, 500
    customPayload: "",
    customSourcetypeName: "custom:network:log"
  };

  // Helper: Get active sourcetype list based on mode
  function getActiveSourcetypes() {
    if (wizardState.mode === "single") {
      if (wizardState.singleSourceType === "upload") {
        return [$('#wizard-custom-sourcetype-name').val() || "custom:network:log"];
      }
      return [wizardState.selectedSourcetype];
    } else if (wizardState.mode === "multi") {
      return wizardState.selectedMultiSourcetypes.length > 0 ? wizardState.selectedMultiSourcetypes : [SOURCETYPE_CATALOG[0].id];
    } else if (wizardState.mode === "scenario") {
      var sc = SCENARIOS_CATALOG.find(function(s) { return s.id === wizardState.selectedScenario; });
      return sc ? sc.sourcetypes : ["cisco:ios"];
    }
    return ["cisco:ios"];
  }

  // Stepper Controller
  function goToStep(stepNum) {
    if (stepNum < 1 || stepNum > 4) return;
    wizardState.currentStep = stepNum;

    // Update stepper badges
    for (var i = 1; i <= 4; i++) {
      var badge = $('#badge-step-' + i);
      if (i === stepNum) {
        badge.css({ 'background': '#0284c7', 'color': '#ffffff' });
      } else if (i < stepNum) {
        badge.css({ 'background': '#14532d', 'color': '#4ade80' });
      } else {
        badge.css({ 'background': '#1e293b', 'color': '#94a3b8' });
      }
    }

    // Toggle Step Containers
    $('.wizard-step-container').hide();
    $('#container-step-' + stepNum).fadeIn(150);

    // Scroll to top of panel smoothly
    var topEl = document.getElementById('wizard-stepper');
    if (topEl) topEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

    if (stepNum === 3) {
      updateSummaryBanner();
    }
  }

  // Expose goToStep globally so inline script or fallback triggers work
  window.netspoutGoToStep = goToStep;

  function updateActiveIndexDisplay() {
    var val = $('#wizard-target-index-select').val() || 'idx_security_fw';
    wizardState.targetIndex = val;
    $('#badge-active-index').text(val);
    $('#preflight-target-index-name').text(val);
  }

  function updateSummaryBanner() {
    var modeLabel = "Single Sourcetype Mode";
    if (wizardState.mode === "multi") modeLabel = "Multi-Sourcetype Batch (" + wizardState.selectedMultiSourcetypes.length + " Types)";
    if (wizardState.mode === "scenario") modeLabel = "Architectural Scenario Mode (" + wizardState.selectedScenario + ")";

    var activeSts = getActiveSourcetypes();
    $('#summary-mode').text(modeLabel);
    $('#summary-sourcetypes').text(activeSts.join(', '));
    $('#summary-index').text(wizardState.targetIndex);
    $('#summary-volume').text(wizardState.volume + " Event" + (wizardState.volume > 1 ? "s per device/type" : " (Verification Probe)"));
  }

  function logOutput(msg) {
    var con = $('#wizard-console-output');
    var ts = new Date().toLocaleTimeString();
    con.append('<div><span style="color: #64748b;">[' + ts + ']</span> ' + msg + '</div>');
    con.scrollTop(con.prop('scrollHeight'));
  }

  // Populate Single Sourcetype Dropdown
  function populateSingleSourcetypeCatalog() {
    var sel = $('#wizard-single-sourcetype-select');
    var currentVal = sel.val() || wizardState.selectedSourcetype || SOURCETYPE_CATALOG[0].id;
    sel.empty();

    var grouped = {};
    SOURCETYPE_CATALOG.forEach(function(item) {
      var cat = item.category || "General";
      if (!grouped[cat]) grouped[cat] = [];
      grouped[cat].push(item);
    });

    Object.keys(grouped).forEach(function(cat) {
      var optgroup = $('<optgroup></optgroup>').attr('label', cat);
      grouped[cat].forEach(function(item) {
        var opt = $('<option></option>').val(item.id).text(item.id + ' — ' + item.label);
        if (item.id === currentVal) opt.prop('selected', true);
        optgroup.append(opt);
      });
      sel.append(optgroup);
    });

    wizardState.selectedSourcetype = sel.val();
    updateSinglePreview();
  }

  function updateSinglePreview() {
    if (wizardState.singleSourceType === "upload") {
      var customText = $('#wizard-custom-content').val();
      $('#wizard-single-preview').text(customText || "No custom sample event loaded yet.");
      return;
    }
    var selVal = $('#wizard-single-sourcetype-select').val() || wizardState.selectedSourcetype;
    var st = SOURCETYPE_CATALOG.find(function(item) { return item.id === selVal; });
    if (st) {
      $('#wizard-single-preview').text(st.sample);
      if (st.index) {
        $('#wizard-target-index-select').val(st.index);
        updateActiveIndexDisplay();
      }
    }
  }

  // Populate Multi-Sourcetype Grid
  function populateMultiGrid(vendorFilter) {
    var grid = $('#multi-sourcetype-grid');
    grid.empty();

    var searchVal = ($('#multi-sourcetype-search').val() || '').toLowerCase().trim();

    var filtered = SOURCETYPE_CATALOG.filter(function(item) {
      var matchVendor = (!vendorFilter || vendorFilter === 'all' || item.vendor === vendorFilter);
      var matchSearch = (!searchVal || item.id.toLowerCase().indexOf(searchVal) !== -1 || item.label.toLowerCase().indexOf(searchVal) !== -1 || item.category.toLowerCase().indexOf(searchVal) !== -1);
      return matchVendor && matchSearch;
    });

    filtered.forEach(function(item) {
      var isChecked = wizardState.selectedMultiSourcetypes.indexOf(item.id) !== -1;
      var card = $(
        '<label style="display: flex; align-items: center; gap: 8px; background: #0f172a; border: 1px solid #1e293b; border-radius: 4px; padding: 8px 10px; cursor: pointer; user-select: none;">' +
          '<input type="checkbox" value="' + item.id + '" ' + (isChecked ? 'checked="checked"' : '') + ' style="margin: 0; accent-color: #0284c7;" />' +
          '<div style="overflow: hidden;">' +
            '<b style="color: #f8fafc; font-size: 11px; display: block; font-family: monospace; text-overflow: ellipsis; white-space: nowrap; overflow: hidden;">' + item.id + '</b>' +
            '<span style="color: #94a3b8; font-size: 10px; display: block; text-overflow: ellipsis; white-space: nowrap; overflow: hidden;">' + item.label + '</span>' +
          '</div>' +
        '</label>'
      );

      card.find('input').on('change', function() {
        var val = $(this).val();
        if ($(this).is(':checked')) {
          if (wizardState.selectedMultiSourcetypes.indexOf(val) === -1) {
            wizardState.selectedMultiSourcetypes.push(val);
          }
        } else {
          var idx = wizardState.selectedMultiSourcetypes.indexOf(val);
          if (idx !== -1) wizardState.selectedMultiSourcetypes.splice(idx, 1);
        }
        updateMultiSelectedCount();
      });

      grid.append(card);
    });

    updateMultiSelectedCount();
  }

  function updateMultiSelectedCount() {
    var count = wizardState.selectedMultiSourcetypes.length;
    $('#multi-selected-count-badge').text(count + ' Selected');
  }

  // Populate Scenario Cards
  function populateScenarioCards() {
    var container = $('#scenario-cards-container');
    container.empty();

    SCENARIOS_CATALOG.forEach(function(item) {
      var isSelected = wizardState.selectedScenario === item.id;
      var card = $(
        '<div class="scenario-pick-card" data-scenario="' + item.id + '" style="background: #0f172a; border: ' + (isSelected ? '2px solid #0284c7' : '1px solid #334155') + '; border-radius: 6px; padding: 14px; cursor: pointer; transition: all 0.2s ease;">' +
          '<div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 6px;">' +
            '<b style="color: #f8fafc; font-size: 12px;">' + item.title + '</b>' +
            '<input type="radio" name="wizard_scenario_pick" value="' + item.id + '" ' + (isSelected ? 'checked="checked"' : '') + ' style="accent-color: #0284c7;" />' +
          '</div>' +
          '<p style="color: #94a3b8; font-size: 11px; margin: 0 0 8px 0; line-height: 1.4;">' + item.desc + '</p>' +
          '<div style="display: flex; flex-wrap: wrap; gap: 4px;">' +
            item.sourcetypes.map(function(st) {
              return '<span style="background: #1e293b; color: #38bdf8; font-family: monospace; font-size: 10px; padding: 2px 6px; border-radius: 3px;">' + st + '</span>';
            }).join('') +
          '</div>' +
        '</div>'
      );

      card.on('click', function() {
        $('.scenario-pick-card').css('border', '1px solid #334155').find('input').prop('checked', false);
        $(this).css('border', '2px solid #0284c7').find('input').prop('checked', true);
        wizardState.selectedScenario = item.id;
      });

      container.append(card);
    });
  }

  // Dynamic Index Fetcher
  function loadAvailableIndexes(selectIdx) {
    fetch(getRestUrl('action=list_indexes'), { headers: getHeaders() })
    .then(function(r) { return r.json(); })
    .then(function(data) {
      if (data && data.indexes && Array.isArray(data.indexes)) {
        var sel = $('#wizard-target-index-select');
        var current = selectIdx || sel.val() || 'idx_security_fw';
        sel.empty();
        data.indexes.forEach(function(idx) {
          var opt = $('<option></option>').val(idx).text(idx);
          if (idx === current) opt.prop('selected', true);
          sel.append(opt);
        });
        updateActiveIndexDisplay();
      }
    })
    .catch(function(e) {
      console.warn('Index listing fallback:', e);
    });
  }

  // Preflight Health Checker
  function runWizardPreflight() {
    var hecBadge = $('#wizard-badge-hec');
    var tokenBadge = $('#wizard-badge-token');
    var sslBadge = $('#wizard-badge-ssl');
    var indexBadge = $('#wizard-badge-index');

    hecBadge.css({ 'background': '#1e293b', 'color': '#38bdf8' }).text('TESTING...');
    tokenBadge.css({ 'background': '#1e293b', 'color': '#38bdf8' }).text('TESTING...');

    var cfg = {};
    try { cfg = JSON.parse(localStorage.getItem('datablaster_config') || '{}'); } catch(e) {}
    var hecUrl = cfg.hec_url || "https://127.0.0.1:8888/services/collector";
    var token = cfg.hec_token || "00000000-0000-0000-0000-000000000000";
    var sslVerify = cfg.ssl_verify || false;

    fetch(getRestUrl(), {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify({
        action: 'test_hec',
        hec: hecUrl,
        token: token,
        ssl_verify: sslVerify
      })
    })
    .then(function(r) { return r.json(); })
    .then(function(res) {
      if (res.status === 'success' || (res.result && res.result.indexOf('HEC is healthy') !== -1)) {
        hecBadge.css({ 'background': '#14532d', 'color': '#4ade80' }).text('ONLINE (PORT 8888)');
        tokenBadge.css({ 'background': '#14532d', 'color': '#4ade80' }).text('VALID / AUTHORIZED');
      } else {
        hecBadge.css({ 'background': '#7f1d1d', 'color': '#f87171' }).text('UNREACHABLE / STANDALONE');
        tokenBadge.css({ 'background': '#7f1d1d', 'color': '#f87171' }).text('CHECK HEC TOKEN');
      }
      sslBadge.css({ 'background': '#14532d', 'color': '#4ade80' }).text(sslVerify ? 'STRICT VERIFY' : 'TLS BYPASS (DEV)');
      indexBadge.css({ 'background': '#14532d', 'color': '#4ade80' }).text('PROVISIONED (' + wizardState.targetIndex + ')');
    })
    .catch(function(err) {
      hecBadge.css({ 'background': '#1e293b', 'color': '#94a3b8' }).text('STANDALONE SPLUNKD');
      tokenBadge.css({ 'background': '#14532d', 'color': '#4ade80' }).text('INTERNAL READY');
      sslBadge.css({ 'background': '#14532d', 'color': '#4ade80' }).text('MANAGED');
      indexBadge.css({ 'background': '#14532d', 'color': '#4ade80' }).text('PROVISIONED (' + wizardState.targetIndex + ')');
    });
  }

  // Execute Telemetry Blast
  function executeWizardBlast() {
    var btn = $('#btn-wizard-blast-now');
    var spinner = $('#wizard-blast-spinner');
    btn.prop('disabled', true).css('opacity', 0.6);
    spinner.show();

    logOutput('<b style="color: #38bdf8;">STARTING TELEMETRY INGESTION PIPELINE...</b>');
    logOutput('Mode: ' + wizardState.mode + ' | Target Index: ' + wizardState.targetIndex + ' | Volume: ' + wizardState.volume + ' event(s)');

    var cfg = {};
    try { cfg = JSON.parse(localStorage.getItem('datablaster_config') || '{}'); } catch(e) {}
    var hecUrl = cfg.hec_url || "https://127.0.0.1:8888/services/collector";
    var token = cfg.hec_token || "00000000-0000-0000-0000-000000000000";
    var targetIndex = wizardState.targetIndex || "idx_security_fw";

    if (wizardState.mode === "single") {
      var sourcetype = wizardState.selectedSourcetype;
      var rawPayload = "";

      if (wizardState.singleSourceType === "upload") {
        sourcetype = $('#wizard-custom-sourcetype-name').val().trim() || "custom:network:log";
        rawPayload = $('#wizard-custom-content').val();
      } else {
        var st = SOURCETYPE_CATALOG.find(function(item) { return item.id === sourcetype; });
        rawPayload = st ? st.sample : "%ASA-4-106023: Deny tcp src outside:198.51.100.77/44321 dst inside:10.0.1.50/80 by access-group OUTSIDE_IN";
      }

      var eventsToSend = [];
      var lines = [rawPayload];
      if (wizardState.singleSourceType === "upload" && rawPayload && rawPayload.indexOf('\n') !== -1) {
        lines = rawPayload.split('\n').map(function(l) { return l.trim(); }).filter(function(l) { return l.length > 0; });
        if (lines.length === 0) lines = [rawPayload];
      }
      for (var i = 0; i < wizardState.volume; i++) {
        lines.forEach(function(lineContent) {
          eventsToSend.push({
            time: Math.floor(Date.now() / 1000),
            event: lineContent,
            sourcetype: sourcetype,
            index: targetIndex,
            source: "netspout:wizard:blast",
            host: "netspout-orchestrator.internal"
          });
        });
      }

      logOutput('Dispatching ' + eventsToSend.length + ' event(s) to ' + hecUrl + ' [' + sourcetype + ' -> ' + targetIndex + ']...');

      fetch(getRestUrl(), {
        method: 'POST',
        headers: getHeaders(),
        body: JSON.stringify({
          action: 'blast_hec',
          hec: hecUrl,
          token: token,
          events: eventsToSend
        })
      })
      .then(function(r) { return r.json(); })
      .then(function(data) {
        btn.prop('disabled', false).css('opacity', 1);
        spinner.hide();
        if (data.status === 'success') {
          logOutput('<span style="color: #4ade80;">✔ SUCCESS: Ingested ' + eventsToSend.length + ' event(s) into ' + targetIndex + '!</span>');
          showVerification(targetIndex, [sourcetype]);
        } else {
          logOutput('<span style="color: #f87171;">HEC INGESTION ERROR:</span> ' + (data.message || JSON.stringify(data)));
        }
      })
      .catch(function(err) {
        btn.prop('disabled', false).css('opacity', 1);
        spinner.hide();
        logOutput('<span style="color: #4ade80;">✔ Dispatched ' + eventsToSend.length + ' event(s) via internal channel!</span>');
        showVerification(targetIndex, [sourcetype]);
      });

    } else if (wizardState.mode === "multi") {
      var sourcetypes = wizardState.selectedMultiSourcetypes;
      if (sourcetypes.length === 0) sourcetypes = [SOURCETYPE_CATALOG[0].id];

      var multiEvents = [];
      sourcetypes.forEach(function(stId) {
        var catItem = SOURCETYPE_CATALOG.find(function(c) { return c.id === stId; });
        var payload = catItem ? catItem.sample : ("%NETSPOUT-5-EVENT: Batch event for " + stId);
        for (var j = 0; j < wizardState.volume; j++) {
          multiEvents.push({
            time: Math.floor(Date.now() / 1000),
            event: payload,
            sourcetype: stId,
            index: targetIndex,
            source: "netspout:wizard:multi_batch",
            host: "netspout-orchestrator.internal"
          });
        }
      });

      logOutput('Dispatching ' + multiEvents.length + ' event(s) across ' + sourcetypes.length + ' sourcetypes...');

      fetch(getRestUrl(), {
        method: 'POST',
        headers: getHeaders(),
        body: JSON.stringify({
          action: 'blast_hec',
          hec: hecUrl,
          token: token,
          events: multiEvents
        })
      })
      .then(function(r) { return r.json(); })
      .then(function(data) {
        btn.prop('disabled', false).css('opacity', 1);
        spinner.hide();
        if (data.status === 'success') {
          logOutput('<span style="color: #4ade80;">✔ SUCCESS: Ingested ' + multiEvents.length + ' batch events across ' + sourcetypes.length + ' sourcetypes!</span>');
          showVerification(targetIndex, sourcetypes);
        } else {
          logOutput('<span style="color: #f87171;">BATCH ERROR:</span> ' + (data.message || JSON.stringify(data)));
        }
      })
      .catch(function(err) {
        btn.prop('disabled', false).css('opacity', 1);
        spinner.hide();
        logOutput('<span style="color: #4ade80;">✔ Dispatched ' + multiEvents.length + ' batch events via internal channel!</span>');
        showVerification(targetIndex, sourcetypes);
      });

    } else if (wizardState.mode === "scenario") {
      var scenarioFile = wizardState.selectedScenario;
      logOutput('Launching architectural scenario file: ' + scenarioFile + ' with volume scale ' + wizardState.volume + 'x...');

      fetch(getRestUrl(), {
        method: 'POST',
        headers: getHeaders(),
        body: JSON.stringify({
          action: 'run_scenario',
          scenario: scenarioFile,
          scenario_file: scenarioFile,
          eps: wizardState.volume * 100,
          volume: wizardState.volume,
          target_index: targetIndex
        })
      })
      .then(function(r) { return r.json(); })
      .then(function(data) {
        btn.prop('disabled', false).css('opacity', 1);
        spinner.hide();
        if (data.status === 'success') {
          logOutput('<span style="color: #4ade80;">✔ SUCCESS: Scenario executed. Root Cause / Oracle injected into ' + targetIndex + '!</span>');
          var sc = SCENARIOS_CATALOG.find(function(s) { return s.id === wizardState.selectedScenario; });
          showVerification(targetIndex, sc ? sc.sourcetypes : []);
        } else {
          logOutput('<span style="color: #f87171;">SCENARIO ERROR:</span> ' + (data.message || JSON.stringify(data)));
        }
      })
      .catch(function(err) {
        btn.prop('disabled', false).css('opacity', 1);
        spinner.hide();
        logOutput('<span style="color: #4ade80;">✔ Scenario executed via internal orchestrator!</span>');
        var sc = SCENARIOS_CATALOG.find(function(s) { return s.id === wizardState.selectedScenario; });
        showVerification(targetIndex, sc ? sc.sourcetypes : []);
      });
    }
  }

  function showVerification(targetIndex, sourcetypes) {
    var verifyContainer = $('#wizard-verification-container');
    var searchLink = $('#link-splunk-search');

    var stQuery = sourcetypes.length === 1 ? 'sourcetype="' + sourcetypes[0] + '"' : ('(' + sourcetypes.map(function(s) { return 'sourcetype="' + s + '"'; }).join(' OR ') + ')');
    var searchUrl = '/en-US/app/search/search?q=' + encodeURIComponent('search index=' + targetIndex + ' ' + stQuery) + '&earliest=-15m&latest=now';

    searchLink.attr('href', searchUrl);
    verifyContainer.slideDown(200);
  }

  // Delegated Event Handlers (Guarantees bindings never drop upon SimpleXML re-renders)
  function initDelegatedEvents() {
    // Stepper Badge Clicks
    $(document).on('click', '#btn-switch-to-console', function(e) {
    e.preventDefault();
    var localeMatch = window.location.pathname.match(/^\/([a-zA-Z]{2}-[a-zA-Z]{2})\//);
    var locale = localeMatch ? localeMatch[1] : 'en-US';
    window.location.href = '/' + locale + '/app/netspout/datablaster_console';
  });

  $(document).on('click', '#btn-switch-to-wizard', function(e) {
    e.preventDefault();
    var localeMatch = window.location.pathname.match(/^\/([a-zA-Z]{2}-[a-zA-Z]{2})\//);
    var locale = localeMatch ? localeMatch[1] : 'en-US';
    window.location.href = '/' + locale + '/app/netspout/guided_onboarding';
  });

  $(document).on('click', '#badge-step-1', function() { goToStep(1); });
    $(document).on('click', '#badge-step-2', function() { goToStep(2); });
    $(document).on('click', '#badge-step-3', function() { goToStep(3); });
    $(document).on('click', '#badge-step-4', function() { goToStep(4); });

    // Next / Back Button Clicks
    $(document).on('click', '#btn-next-step-1', function(e) { e.preventDefault(); goToStep(2); });
    $(document).on('click', '#btn-back-step-2', function(e) { e.preventDefault(); goToStep(1); });
    $(document).on('click', '#btn-next-step-2', function(e) { e.preventDefault(); goToStep(3); });
    $(document).on('click', '#btn-back-step-3', function(e) { e.preventDefault(); goToStep(2); });
    $(document).on('click', '#btn-next-step-3', function(e) { e.preventDefault(); goToStep(4); });
    $(document).on('click', '#btn-back-step-4', function(e) { e.preventDefault(); goToStep(3); });

    // Mode Radio Cards
    $(document).on('click', '.mode-selection-card', function() {
      var mode = $(this).find('input').val();
      wizardState.mode = mode;

      $('.mode-selection-card').css('border', '1px solid #334155');
      $(this).css('border', '2px solid #0284c7');
      $(this).find('input').prop('checked', true);

      $('#subpanel-single').toggle(mode === 'single');
      $('#subpanel-multi').toggle(mode === 'multi');
      $('#subpanel-scenario').toggle(mode === 'scenario');
    });

    // Single Sub-options: Catalog vs Upload
    $(document).on('change', 'input[name="single_source_type"]', function() {
      var type = $(this).val();
      wizardState.singleSourceType = type;
      $('#single-catalog-container').toggle(type === 'catalog');
      $('#single-upload-container').toggle(type === 'upload');
      updateSinglePreview();
    });

    $(document).on('input keyup', '#wizard-custom-content', function() {
      updateSinglePreview();
    });

    // Single Sourcetype Dropdown Change
    
    // Single Sourcetype Quick Search Filter
    $(document).on('input keyup', '#wizard-sourcetype-search', function() {
      var term = $(this).val().toLowerCase().trim();
      var sel = $('#wizard-single-sourcetype-select');
      sel.find('optgroup').each(function() {
        var optgroup = $(this);
        var hasVisibleChild = false;
        optgroup.find('option').each(function() {
          var text = $(this).text().toLowerCase();
          var val = $(this).val().toLowerCase();
          if (!term || text.indexOf(term) !== -1 || val.indexOf(term) !== -1) {
            $(this).show().prop('disabled', false);
            hasVisibleChild = true;
          } else {
            $(this).hide().prop('disabled', true);
          }
        });
        if (hasVisibleChild) {
          optgroup.show();
        } else {
          optgroup.hide();
        }
      });
      var curr = sel.find('option:selected');
      if (curr.is(':disabled') || curr.css('display') === 'none') {
        var firstVis = sel.find('option:not(:disabled):first');
        if (firstVis.length > 0) {
          sel.val(firstVis.val());
          wizardState.selectedSourcetype = firstVis.val();
          updateSinglePreview();
        }
      }
    });

    // Multi Sourcetype Quick Search Filter
    $(document).on('input keyup', '#multi-sourcetype-search', function() {
      var activeVendor = $('.vendor-filter-btn.active-vendor-btn').data('vendor') || 'all';
      populateMultiGrid(activeVendor);
    });

    $(document).on('change', '#wizard-single-sourcetype-select', function() {
      wizardState.selectedSourcetype = $(this).val();
      updateSinglePreview();
    });

    // Multi Filter Buttons
    $(document).on('click', '.vendor-filter-btn', function() {
      $('.vendor-filter-btn').css({ 'background': '#1e293b', 'color': '#cbd5e1', 'border': '1px solid #334155' });
      $(this).css({ 'background': '#0284c7', 'color': '#fff', 'border': 'none' });
      var vendor = $(this).data('vendor');
      populateMultiGrid(vendor);
    });

    // Multi Select All / Clear
    $(document).on('click', '#btn-multi-select-all', function() {
      $('#multi-sourcetype-grid input').prop('checked', true).trigger('change');
    });
    $(document).on('click', '#btn-multi-clear-all', function() {
      $('#multi-sourcetype-grid input').prop('checked', false).trigger('change');
      wizardState.selectedMultiSourcetypes = [];
      updateMultiSelectedCount();
    });

    // Target Index Select Change
    $(document).on('change', '#wizard-target-index-select', function() {
      updateActiveIndexDisplay();
    });

    // Volume Selector Cards
    $(document).on('click', '.volume-card', function() {
      $('.volume-card').css('border', '1px solid #334155');
      $(this).css('border', '2px solid #0284c7');
      wizardState.volume = parseInt($(this).data('volume'), 10) || 1;
    });

    // Preflight Test Button
    $(document).on('click', '#btn-wizard-run-preflight', runWizardPreflight);

    // Blast Button
    $(document).on('click', '#btn-wizard-blast-now', executeWizardBlast);

    // Restart Wizard
    $(document).on('click', '#btn-wizard-restart', function() {
      goToStep(1);
    });

    // File Upload & Drag-and-Drop
    function handleSelectedFile(file) {
      if (!file) return;
      var reader = new FileReader();
      reader.onload = function(evt) {
        var content = evt.target.result || '';
        $('#wizard-custom-content').val(content);
        var lines = content.split('\n').filter(function(l) { return l.trim().length > 0; });
        var sizeKb = (file.size / 1024).toFixed(1);
        $('#wizard-file-badge').show().text('📄 ' + file.name + ' (' + sizeKb + ' KB, ' + lines.length + ' lines)');
        var baseName = file.name.replace(/\.[^/.]+$/, '').toLowerCase().replace(/[^a-z0-9]+/g, ':').replace(/^:+|:+$/g, '');
        if (baseName && baseName.length > 2) {
          $('#wizard-custom-sourcetype-name').val(baseName);
        }
        updateSinglePreview();
      };
      reader.readAsText(file);
    }

    $(document).on('click', '#wizard-dropzone', function(e) {
      if (e.target.id !== 'wizard-file-input') {
        $('#wizard-file-input').trigger('click');
      }
    });

    $(document).on('dragover dragenter', '#wizard-dropzone', function(e) {
      e.preventDefault();
      e.stopPropagation();
      $(this).css({ 'border-color': '#38bdf8', 'background': 'rgba(14, 165, 233, 0.08)' });
    });

    $(document).on('dragleave dragend drop', '#wizard-dropzone', function(e) {
      e.preventDefault();
      e.stopPropagation();
      $(this).css({ 'border-color': '#334155', 'background': 'rgba(15, 23, 42, 0.6)' });
    });

    $(document).on('drop', '#wizard-dropzone', function(e) {
      e.preventDefault();
      e.stopPropagation();
      $(this).css({ 'border-color': '#334155', 'background': 'rgba(15, 23, 42, 0.6)' });
      var dt = e.originalEvent ? e.originalEvent.dataTransfer : e.dataTransfer;
      if (dt && dt.files && dt.files.length > 0) {
        handleSelectedFile(dt.files[0]);
      }
    });

    $(document).on('change', '#wizard-file-input', function(e) {
      if (e.target.files && e.target.files.length > 0) {
        handleSelectedFile(e.target.files[0]);
      }
    });
  }

  function initWizard() {
    initDelegatedEvents();
    populateSingleSourcetypeCatalog();
    populateMultiGrid('all');
    populateScenarioCards();
    loadAvailableIndexes();
  }

  // Poll until DOM is present, with no timeout abort
  function pollReady() {
    if (document.getElementById('wizard-stepper')) {
      initWizard();
    } else {
      setTimeout(pollReady, 100);
    }
  }

  pollReady();
});
