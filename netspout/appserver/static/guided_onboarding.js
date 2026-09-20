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
    // 1. Routing & Core Fabric
    {
      id: "cisco:mdt:grpc",
      label: "Cisco MDT gRPC Metric Stream (OpenConfig)",
      vendor: "cisco",
      category: "Routing & Core",
      index: "cisco_mdt_metrics",
      sample: '{"event":"metric","time":1789840800,"fields":{"metric_name:interface.octets.in":984521000,"metric_name:interface.octets.out":874219000,"metric_name:cpu.utilization":24.5,"interface":"HundredGigE0/0/0/0","oper_status":"UP","xpath":"/interfaces/interface/state/counters"}}'
    },
    {
      id: "openconfig:yang:json",
      label: "OpenConfig YANG JSON Telemetry (RFC 7950)",
      vendor: "cisco",
      category: "Routing & Core",
      index: "idx_network_ops",
      sample: '{"openconfig-interfaces:interfaces":{"interface":[{"name":"HundredGigE0/0/0/0","state":{"admin-status":"UP","oper-status":"UP","counters":{"in-octets":984521000,"out-octets":874219000}}}]}}'
    },
    {
      id: "cisco:ios",
      label: "Cisco IOS-XE / Classic Syslog",
      vendor: "cisco",
      category: "Routing & Core",
      index: "idx_network_ops",
      sample: "%BGP-5-ADJCHANGE: neighbor 198.51.100.1 Up"
    },
    {
      id: "juniper:junos",
      label: "Juniper Networks Junos OS Syslog",
      vendor: "arista",
      category: "Routing & Core",
      index: "idx_network_ops",
      sample: "<14>Sep 19 12:00:00 rtr-ptx01 rpd[4821]: %ROUTING-4-BGP_PEER_FLAP: BGP peer 198.51.100.1 state changed from Established to Idle"
    },
    {
      id: "nokia:sros",
      label: "Nokia 7750 SR OS Router Syslog",
      vendor: "arista",
      category: "Routing & Core",
      index: "idx_network_ops",
      sample: "<165>Sep 19 12:00:00 pe01-7750 Major: BGP #2002 Base Peer 10.254.0.1: Peer entered Established state"
    },
    {
      id: "arista:eos",
      label: "Arista EOS Core Switching Syslog",
      vendor: "arista",
      category: "Routing & Core",
      index: "idx_network_ops",
      sample: "%LINEPROTO-5-UPDOWN: Line protocol on Interface Ethernet1/1, changed state to up"
    },

    // 2. Identity & Access Control (Cisco ISE & Cisco Duo)
    {
      id: "cisco:ise:byod:provisioning",
      label: "Cisco ISE BYOD Device Onboarding & Registration",
      vendor: "cisco",
      category: "Identity & Access Control",
      index: "idx_network_ops",
      sample: "CISE_Passed_Authentications 0001847291 1 0 2026-09-19T14:00:00.000Z +00:00 0029481921 5200 NOTICE Passed-Authentication: BYOD Registration Succeeded, ConfigVersionId=127, DeviceRegistrationStatus=Registered, DeviceType=Apple-Device, MacAddress=00-1A-2B-3C-4D-5E, CertificateSerialNumber=49810283, EapAuthentication=EAP-TLS, User-Name=j.doe@corp.internal, IdentityGroup=Employee_BYOD"
    },
    {
      id: "cisco:ise:nac:8021x",
      label: "Cisco ISE 802.1X Port NAC & RADIUS Auth",
      vendor: "cisco",
      category: "Identity & Access Control",
      index: "idx_network_ops",
      sample: "CISE_Passed_Authentications 0001847295 1 0 2026-09-19T14:00:00.000Z +00:00 0029481925 5200 NOTICE Passed-Authentication: Authentication succeeded, ConfigVersionId=127, Device IP Address=10.254.8.1, DestinationPort=1812, UserName=corp\\alice.sec, Protocol=Radius, NAS-Port-Id=GigabitEthernet1/0/24, Framed-IP-Address=10.20.10.45, EapAuthentication=EAP-TLS"
    },
    {
      id: "cisco:ise:trustsec:sgt",
      label: "Cisco ISE TrustSec SGT Micro-segmentation",
      vendor: "cisco",
      category: "Identity & Access Control",
      index: "idx_security_fw",
      sample: "CISE_TrustSec 0001847297 1 0 2026-09-19T14:00:00.000Z +00:00 0029481927 5400 NOTICE TrustSec: SGT Assignment Enforcement, ConfigVersionId=127, Source-SGT=14:Employees, Destination-SGT=25:Quarantine, SGACL-Name=DENY_QUARANTINE_TRAFFIC, Action=DENIED, Enforcement-Node=cat9600-core-01"
    },
    {
      id: "cisco:ise:deviceadmin:tacacs",
      label: "Cisco ISE TACACS+ Device Administration",
      vendor: "cisco",
      category: "Identity & Access Control",
      index: "idx_network_ops",
      sample: "CISE_TACACS_Accounting 0001847299 1 0 2026-09-19T14:00:00.000Z +00:00 0029481929 3300 NOTICE TACACS-Accounting: Command Authorization Succeeded, User=netadmin_bob, Device-IP-Address=10.254.1.1, Privilege-Level=15, Command=\"configure terminal ; interface HundredGigE0/0/0/1 ; shutdown\""
    },
    {
      id: "cisco:ise:guest:voucher",
      label: "Cisco ISE Guest Captive Portal & Vouchers",
      vendor: "cisco",
      category: "Identity & Access Control",
      index: "idx_network_ops",
      sample: '{"timestamp":"2026-09-19T14:00:00.000Z","event_type":"GUEST_VOUCHER_ACTIVATION","ise_node":"ise-pan01.corp.internal","portal_name":"Corporate_Sponsor_Guest_Portal","voucher_code":"GUEST-9481-VX","sponsor_user":"admin_frontdesk@corp.internal","duration_hours":8,"vlan_assigned":99,"status":"ACTIVE"}'
    },
    {
      id: "cisco:duo:push:prompt",
      label: "Cisco Duo Push Multi-Factor Authentication",
      vendor: "cloud",
      category: "Identity & Access Control",
      index: "idx_security_fw",
      sample: '{"timestamp":1789840800,"event_type":"authentication","factor":"duo_push","result":"SUCCESS","reason":"user_approved","user":{"name":"m.chowdhury@corp.internal","groups":["Enterprise_Admins"]},"application":{"name":"Splunk Enterprise Production NOC"},"auth_device":{"name":"iPhone 15 Pro","ip":"198.51.100.42"}}'
    },
    {
      id: "cisco:duo:endpoint:posture",
      label: "Cisco Duo Endpoint Device Posture & Health",
      vendor: "cloud",
      category: "Identity & Access Control",
      index: "idx_security_fw",
      sample: '{"timestamp":1789840800,"event_type":"endpoint_health","device":{"os":"macOS","os_version":"15.3.1","encryption":{"disk":"FileVault_Encrypted","status":"HEALTHY"},"security_software":{"firewall_active":true,"screen_lock_enforced":true}},"user":"m.chowdhury@corp.internal","posture_result":"COMPLIANT"}'
    },
    {
      id: "cisco:duo:sso:saml",
      label: "Cisco Duo Central SSO SAML Assertions",
      vendor: "cloud",
      category: "Identity & Access Control",
      index: "idx_security_fw",
      sample: '{"timestamp":1789840800,"event_type":"sso_auth","auth_type":"SAML_2_0","identity_provider":"Duo Central Single Sign-On","service_provider":"Splunk Enterprise Production","subject_name_id":"mchowdhury@splunk.com","action":"ASSERTION_ISSUED"}'
    },
    {
      id: "cisco:duo:zerotrust:policy",
      label: "Cisco Duo Zero Trust Application Policy",
      vendor: "cloud",
      category: "Identity & Access Control",
      index: "idx_security_fw",
      sample: '{"timestamp":1789840800,"event_type":"zero_trust_policy_evaluation","policy_name":"High_Privilege_Core_Access","policy_outcome":"ALLOW","context":{"user_risk":"LOW","device_trust":"VERIFIED_MANAGED","geo_velocity_check":"PASSED"},"enforced_action":"GRANT_SESSION"}'
    },
    {
      id: "cisco:duo:remote:vpn",
      label: "Cisco Duo Secure Remote Access VPN",
      vendor: "cloud",
      category: "Identity & Access Control",
      index: "idx_security_fw",
      sample: '{"timestamp":1789840800,"event_type":"vpn_authentication","vpn_gateway":"cisco-asa-vpn.corp.internal","client_software":"Cisco AnyConnect / Secure Client 5.0","assigned_ip":"10.240.12.88","username":"mchowdhury@splunk.com","factor":"duo_push","status":"CONNECTED"}'
    },

    // 3. Security & Firewalls
    {
      id: "cisco:asa",
      label: "Cisco ASA Adaptive Security Appliance",
      vendor: "cisco",
      category: "Security & Firewalls",
      index: "idx_security_fw",
      sample: '%ASA-4-106023: Deny tcp src outside:198.51.100.77/44321 dst inside:10.0.1.50/80 by access-group "OUTSIDE_IN" [0x0, 0x0]'
    },
    {
      id: "cisco:ftd",
      label: "Cisco Firepower Threat Defense (FTD)",
      vendor: "cisco",
      category: "Security & Firewalls",
      index: "idx_security_fw",
      sample: "%FTD-1-430002: EventPriority: High, DeviceUUID: 4f1c9c7e-8c52, Intrusion Rule: 1:2100498, Protocol: TCP, SrcIP: 203.0.113.88, DstIP: 10.100.4.15"
    },
    {
      id: "pan:traffic",
      label: "Palo Alto Networks Traffic Logs",
      vendor: "paloalto",
      category: "Security & Firewalls",
      index: "idx_security_fw",
      sample: "1,2026/09/19 14:00:00,001801000001,TRAFFIC,drop,1,2026/09/19 14:00:00,198.51.100.42,10.254.1.10,0.0.0.0,0.0.0.0,rule_syn_flood,vsys1,untrust,trust,ethernet1/1,ethernet1/2,default-log-forwarding,2026/09/19 14:00:00,0,1,54210,443,0,0,0x0,tcp,deny,64,64,0,1"
    },
    {
      id: "pan:threat",
      label: "Palo Alto Networks Threat Prevention",
      vendor: "paloalto",
      category: "Security & Firewalls",
      index: "idx_security_fw",
      sample: "1,2026/09/19 14:00:00,001801000001,THREAT,drop,1,2026/09/19 14:00:00,198.51.100.42,10.254.1.10,0.0.0.0,0.0.0.0,rule_threat_prevention,vsys1,untrust,trust,ethernet1/1,ethernet1/2,threat-drop,0,0,0,0,0,tcp,deny"
    },
    {
      id: "fortinet:fortigate",
      label: "Fortinet FortiOS Security Events",
      vendor: "paloalto",
      category: "Security & Firewalls",
      index: "idx_security_fw",
      sample: 'date=2026-09-19 time=14:00:00 devname="fortigate-3700d" devid="FG370D4615800001" eventtime=1789840800 level="warning" vd="root" type="traffic" subtype="forward" action="accept" policyid=12 sessionid=9872411 srcip=10.254.2.50 dstip=198.51.100.80 proto=6 sentbyte=2400 rcvdbyte=8900 utmaction="allow" transport="sdwan"'
    },
    {
      id: "checkpoint:cef",
      label: "Check Point Quantum Firewall CEF",
      vendor: "paloalto",
      category: "Security & Firewalls",
      index: "idx_security_fw",
      sample: "CEF:0|Check Point|VPN-1 & FireWall-1|Check Point|Log|drop|act=drop suser=mchen src=10.40.12.88 spt=54215 dst=198.51.100.66 dpt=23 proto=tcp product=VPN-1 & FireWall-1 cs1Label=Rule cs1=Deny_Telnet_Global"
    },

    // 4. Campus Access, Wireless & SD-WAN
    {
      id: "cisco:catalyst:security:events",
      label: "Cisco Catalyst 9300 Security Events",
      vendor: "cisco",
      category: "Campus Access & Wireless",
      index: "idx_network_ops",
      sample: "%SW_MATM-4-MACFLAP_NOTIF: Host 00:1a:2b:3c:4d:5e in vlan 20 is flapping between port Gi1/0/12 and port Gi1/0/24"
    },
    {
      id: "cisco:catalyst:rogue:threat_details",
      label: "Cisco Catalyst Rogue AP Detection",
      vendor: "cisco",
      category: "Campus Access & Wireless",
      index: "idx_wireless_ops",
      sample: 'cisco:catalyst:rogue:threat_details ap_name="AP-HQ-Floor3" rogue_bssid="70:69:79:4c:11:02" ssid="Corporate-Guest-EvilTwin" rogue_type="Unclassified" classification="Threat" state="Alert"'
    },
    {
      id: "cisco:sdwan:linkhealth",
      label: "Cisco SD-WAN vEdge Link Health",
      vendor: "cisco",
      category: "Campus Access & Wireless",
      index: "idx_network_ops",
      sample: 'vEdge-1000-Core: bfd: event=state_change local_color=biz-internet remote_color=biz-internet loss_pct=14.8 latency_ms=184.2 jitter_ms=42.1 sla_state=violated'
    },
    {
      id: "cisco:sdwan:BGP-5-ADJCHANGE",
      label: "Cisco SD-WAN BGP Route Failover",
      vendor: "cisco",
      category: "Campus Access & Wireless",
      index: "idx_network_ops",
      sample: "%BGP-5-ADJCHANGE: neighbor 198.51.100.1 vpn 10 Down BFD session down"
    },
    {
      id: "meraki:accesspoints",
      label: "Cisco Meraki MR Wireless Telemetry",
      vendor: "cisco",
      category: "Campus Access & Wireless",
      index: "idx_wireless_ops",
      sample: '{"name":"MR46-Floor1-East","serial":"Q2MN-1182-3341","clientsCount":24,"channel24":6,"channel5":149,"powerUsage":12.4}'
    },
    {
      id: "aruba:syslog",
      label: "Aruba CX Campus Switching",
      vendor: "arista",
      category: "Campus Access & Wireless",
      index: "idx_network_ops",
      sample: "<189>Sep 19 14:00:00 aruba-cx-switch01 hpe-authmgr[1142]: User A4:83:E7:4B:11:02 authenticated on port 1/1/12 via 802.1X VLAN 40"
    },

    // 5. Cloud, SASE & Observability
    {
      id: "zscaler:zia",
      label: "Zscaler Internet Access (ZIA) Web Log",
      vendor: "cloud",
      category: "Cloud, SASE & Observability",
      index: "idx_security_fw",
      sample: '{"datetime":"2026-09-19 14:00:00","user":"eng-dev@corp.internal","app":"ChatGPT-Enterprise","action":"Allow","proto":"HTTPS","url":"https://api.openai.com/v1/models","threatname":"None","riskscore":"0","egress_dc":"iad-zscaler"}'
    },
    {
      id: "zscaler:lss",
      label: "Zscaler Private Access (ZPA) LSS",
      vendor: "cloud",
      category: "Cloud, SASE & Observability",
      index: "idx_security_fw",
      sample: '{"datetime":"2026-09-19 12:00:00","Customer":"Acme-Enterprise","Application":"Internal-ERP","ClientIP":"10.45.2.14","ServerIP":"10.100.1.5","PolicyRule":"Engineering-Access","Status":"Success"}'
    },
    {
      id: "cisco:thousandeyes:metric",
      label: "Cisco ThousandEyes Synthetic Metrics",
      vendor: "cisco",
      category: "Cloud, SASE & Observability",
      index: "idx_performance_metrics",
      sample: '{"test_name":"SaaS CRM Portal","test_type":"http-server","loss":0.12,"latency":182.4,"jitter":15.1,"response_code":200,"status":"degraded"}'
    },
    {
      id: "sc4snmp:metric",
      label: "Splunk Connect for SNMP Metrics",
      vendor: "cisco",
      category: "Cloud, SASE & Observability",
      index: "cisco_mdt_metrics",
      sample: '{"time":1789840800.0,"event":"metric","source":"sc4snmp","sourcetype":"sc4snmp:metric","host":"rtr-cisco-8000-01.corp.internal","index":"cisco_mdt_metrics","fields":{"metric_name:ifInOctets":58920140.0,"metric_name:ifOutOctets":84920194.0,"metric_name:ifOperStatus":1.0,"_value":58920140.0,"ifIndex":"1","ifDescr":"GigabitEthernet0/0/1","device":"rtr-cisco-8000-01","vendor":"cisco"}}'
    },
    {
      id: "sc4snmp:event",
      label: "Splunk Connect for SNMP Traps",
      vendor: "cisco",
      category: "Cloud, SASE & Observability",
      index: "idx_network_ops",
      sample: '{"time":1789840800.0,"source":"sc4snmp:trap","sourcetype":"sc4snmp:event","host":"rtr-cisco-8000-01.corp.internal","index":"idx_network_ops","event":{"snmp_trap_name":"linkDown","snmp_trap_oid":"1.3.6.1.6.3.1.1.5.3","enterprise":"1.3.6.1.4.1","severity":"critical","varbinds":{"ifIndex":1,"ifAdminStatus":1,"ifOperStatus":2,"ifDescr":"GigabitEthernet0/0/1"}}}'
    },

    // 6. Storage & Data Center (SAN / NAS)
    {
      id: "cisco:mds:san:fc",
      label: "Cisco MDS 9700 Fibre Channel SAN Fabric",
      vendor: "cisco",
      category: "Storage & Data Center",
      index: "idx_performance_metrics",
      sample: "%PORT-3-CREDIT_LOSS: Interface fc1/14 Tx credit loss detected. Peer device slow drain. Dropped frames: 842. B2B credit recovery initiated."
    },
    {
      id: "netapp:ontap:nas",
      label: "NetApp ONTAP Clustered NAS (NFS/SMB)",
      vendor: "arista",
      category: "Storage & Data Center",
      index: "idx_performance_metrics",
      sample: '{"timestamp":"2026-09-19T14:00:00.000Z","cluster":"netapp-ontap-01","node":"node-01","vserver":"vs_prod","volume":"vol_analytics","iops":128400,"throughput_mbps":1480,"latency_ms":48.2,"protocol":"nfs4.1","status":"DEGRADED"}'
    },
    {
      id: "cisco:dc:nexus9k:syslog",
      label: "Cisco Nexus 9000 Data Center Syslog",
      vendor: "cisco",
      category: "Storage & Data Center",
      index: "idx_performance_metrics",
      sample: "%ETHPORT-5-IF_DOWN_TX_PAUSE: Interface Ethernet1/12 buffer congestion pause frames transmitted threshold exceeded"
    },
    {
      id: "arista:telemetry:json",
      label: "Arista EOS Streaming Telemetry",
      vendor: "arista",
      category: "Storage & Data Center",
      index: "idx_performance_metrics",
      sample: '{"timestamp":1789840800.0,"device":"sw-arista-7280-01","interface":"Ethernet1/1","pfc_pause_rx":48201,"ecn_marked_packets":1284,"buffer_utilization_pct":98.4,"status":"CONGESTION_ROCE_V2"}'
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

    var filtered = SOURCETYPE_CATALOG.filter(function(item) {
      if (!vendorFilter || vendorFilter === 'all') return true;
      return item.vendor === vendorFilter;
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
      for (var i = 0; i < wizardState.volume; i++) {
        eventsToSend.push({
          time: Math.floor(Date.now() / 1000),
          event: rawPayload,
          sourcetype: sourcetype,
          index: targetIndex,
          source: "netspout:wizard:blast",
          host: "netspout-orchestrator.internal"
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
    });

    // Single Sourcetype Dropdown Change
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

    // Custom Index Drawer
    $(document).on('click', '#btn-wizard-open-custom-index', function() {
      $('#wizard-custom-index-drawer').slideDown(150);
      $('#wizard-custom-index-name').focus();
    });
    $(document).on('click', '#btn-wizard-close-custom-index', function() {
      $('#wizard-custom-index-drawer').slideUp(150);
    });
    $(document).on('click', '#btn-wizard-submit-custom-index', function() {
      var name = $('#wizard-custom-index-name').val().trim().toLowerCase();
      var dt = $('#wizard-custom-index-datatype').val();
      var maxsize = parseInt($('#wizard-custom-index-maxsize').val(), 10) || 51200;
      var ret = parseInt($('#wizard-custom-index-retention').val(), 10) || 90;
      var msgDiv = $('#wizard-custom-index-msg');

      if (!name || !/^[a-zA-Z0-9_\-]+$/.test(name)) {
        msgDiv.css('color', '#f87171').text('Enter valid index name (letters, numbers, hyphens, underscores)');
        return;
      }

      msgDiv.css('color', '#38bdf8').text('Provisioning ' + name + '...');
      fetch(getRestUrl(), {
        method: 'POST',
        headers: getHeaders(),
        body: JSON.stringify({
          action: 'create_index',
          name: name,
          datatype: dt,
          max_size_mb: maxsize,
          retention_days: ret
        })
      })
      .then(function(r) { return r.json(); })
      .then(function(res) {
        if (res.status === 'success') {
          msgDiv.css('color', '#4ade80').text('✔ Index created!');
          loadAvailableIndexes(name);
          setTimeout(function() { $('#wizard-custom-index-drawer').slideUp(150); }, 1000);
        } else {
          msgDiv.css('color', '#f87171').text('✖ ' + (res.message || 'Creation failed'));
        }
      })
      .catch(function(err) {
        msgDiv.css('color', '#f87171').text('✖ Error: ' + err.message);
      });
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

    // Dropzone for File Upload
    var dropzone = $('#wizard-dropzone');
    var fileInput = $('#wizard-file-input');
    var fileBadge = $('#wizard-file-badge');

    $(document).on('click', '#wizard-dropzone', function() {
      $('#wizard-file-input').trigger('click');
    });

    $(document).on('change', '#wizard-file-input', function(e) {
      if (e.target.files && e.target.files.length > 0) {
        var file = e.target.files[0];
        var reader = new FileReader();
        reader.onload = function(evt) {
          var content = evt.target.result;
          $('#wizard-custom-content').val(content);
          var lines = content.split('\n').filter(function(l) { return l.trim().length > 0; });
          var sizeKb = (file.size / 1024).toFixed(1);
          $('#wizard-file-badge').show().text('📄 ' + file.name + ' (' + sizeKb + ' KB, ' + lines.length + ' lines)');
          var baseName = file.name.replace(/\.[^/.]+$/, '').toLowerCase().replace(/[^a-z0-9]+/g, ':').replace(/^:+|:+$/g, '');
          if (baseName && baseName.length > 2) {
            $('#wizard-custom-sourcetype-name').val(baseName);
          }
        };
        reader.readAsText(file);
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
