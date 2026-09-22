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
    "sample": "{\"event\":\"metric\",\"time\":1789840800,\"fields\":{\"metric_name:interface.octets.in\":984521000,\"metric_name:interface.octets.out\":874219000,\"metric_name:cpu.utilization\":24.5,\"interface\":\"HundredGigE0/0/0/0\",\"oper_status\":\"UP\",\"xpath\":\"/interfaces/interface/state/counters\"}}"
  },
  {
    "id": "openconfig:yang:json",
    "label": "OpenConfig YANG JSON Telemetry (RFC 7950)",
    "vendor": "openconfig",
    "category": "Routing & Core",
    "index": "idx_network_ops",
    "sample": "{\"openconfig-interfaces:interfaces\":{\"interface\":[{\"name\":\"HundredGigE0/0/0/0\",\"state\":{\"admin-status\":\"UP\",\"oper-status\":\"UP\",\"counters\":{\"in-octets\":984521000,\"out-octets\":874219000}}}]}}"
  },
  {
    "id": "cisco:ios",
    "label": "Cisco IOS-XE / Classic Syslog",
    "vendor": "cisco",
    "category": "Routing & Core",
    "index": "idx_network_ops",
    "sample": "2026-09-20T14:30:00.000ZTS2026-09-20T14:30:00.000Z 10.0.0.253 : 2026 Feb 28 19:00:01 EST: %OSPF-4-DUPRID:  ospf-10 [32135] (default) Router 10.0.10.2 on interface Vlan810 is using our routerid, packet dropped"
  },
  {
    "id": "juniper:junos",
    "label": "Juniper Networks Junos OS Syslog",
    "vendor": "juniper",
    "category": "Routing & Core",
    "index": "idx_network_ops",
    "sample": "May 20 14:00:19 rtr-juniper-ptx01 rpd[2481]: %ROUTING-5-BGP_PREFIX_LIMIT: BGP peer 10.254.1.1 (External AS 64512): Received 849200 prefixes; warning threshold 80% reached"
  },
  {
    "id": "nokia:sros",
    "label": "Nokia 7750 SR OS Router Syslog",
    "vendor": "nokia",
    "category": "Routing & Core",
    "index": "idx_network_ops",
    "sample": "2026-09-20T14:00:22.000Z rtr-nokia-7750-01 TiMOS-B-23.10.R1: BGP-5-BGP_ESTABLISHED: Peer 10.254.2.1 Router-ID 10.254.2.1 in VRF default ASN 64512 transitioned to state ESTABLISHED"
  },
  {
    "id": "arista:eos",
    "label": "Arista EOS Core Switching Syslog",
    "vendor": "arista",
    "category": "Routing & Core",
    "index": "idx_network_ops",
    "sample": "May 20 14:00:00 sw-arista-7280-01 Rib: %ROUTING-6-BGP_NEIGHBOR_UP: BGP neighbor 10.254.1.2 AS 64512 state changed from OPENCONFIRM to ESTABLISHED"
  },
  {
    "id": "cisco:ise:byod:provisioning",
    "label": "Cisco ISE BYOD Device Onboarding & Registration",
    "vendor": "cisco",
    "category": "Identity & Access Control",
    "index": "idx_network_ops",
    "sample": "2026-09-20T14:30:00.000ZSYSLOG_TIMESTAMP2026-09-20T14:30:00.000Z ise-pan01.corp.internal CISE_Passed_Authentications 0001847291 1 0 2026-09-20T14:30:00.000ZISO_TIMESTAMP2026-09-20T14:30:00.000Z +00:00 0029481921 5200 NOTICE Passed-Authentication: BYOD Registration Succeeded, ConfigVersionId=127, DeviceRegistrationStatus=Registered, DeviceType=Apple-Device, MacAddress=00-1A-2B-3C-4D-5E, CertificateSerialNumber=49810283, EapAuthentication=EAP-TLS, User-Name=j.doe@corp.internal, NAS-IP-Address=10.254.8.1, NAS-Port=GigabitEthernet1/0/12, IdentityGroup=Employee_BYOD, SelectedAuthorizationProfiles=PermitAccess"
  },
  {
    "id": "cisco:ise:nac:8021x",
    "label": "Cisco ISE 802.1X Port NAC & RADIUS Auth",
    "vendor": "cisco",
    "category": "Identity & Access Control",
    "index": "idx_network_ops",
    "sample": "2026-09-20T14:30:00.000ZSYSLOG_TIMESTAMP2026-09-20T14:30:00.000Z ise-pan01.corp.internal CISE_Passed_Authentications 0001847295 1 0 2026-09-20T14:30:00.000ZISO_TIMESTAMP2026-09-20T14:30:00.000Z +00:00 0029481925 5200 NOTICE Passed-Authentication: Authentication succeeded, ConfigVersionId=127, Device IP Address=10.254.8.1, DestinationIPAddress=10.254.1.50, DestinationPort=1812, UserName=corp\\\\\\\\alice.sec, Protocol=Radius, NAS-IP-Address=10.254.8.1, NAS-Port-Id=GigabitEthernet1/0/24, Framed-IP-Address=10.20.10.45, Tunnel-Private-Group-Id=(tag=1) 20, Tunnel-Type=(tag=1) 13, Tunnel-Medium-Type=(tag=1) 6, EapAuthentication=EAP-TLS, IdentityGroup=SecOps_Endpoints, SelectedAuthorizationProfiles=TrustSec_SecOps_Permit"
  },
  {
    "id": "cisco:ise:trustsec:sgt",
    "label": "Cisco ISE TrustSec SGT Micro-segmentation",
    "vendor": "cisco",
    "category": "Identity & Access Control",
    "index": "idx_security_fw",
    "sample": "2026-09-20T14:30:00.000ZSYSLOG_TIMESTAMP2026-09-20T14:30:00.000Z ise-pan01.corp.internal CISE_TrustSec 0001847297 1 0 2026-09-20T14:30:00.000ZISO_TIMESTAMP2026-09-20T14:30:00.000Z +00:00 0029481927 5400 NOTICE TrustSec: SGT Assignment Enforcement, ConfigVersionId=127, Source-SGT=14:Employees, Destination-SGT=25:Quarantine, SGACL-Name=DENY_QUARANTINE_TRAFFIC, Action=DENIED, Packet-Count=412, Byte-Count=328400, Enforcement-Node=cat9600-core-01, Source-IP=10.20.10.45, Dest-IP=10.50.4.12, Protocol=TCP, Dest-Port=445"
  },
  {
    "id": "cisco:ise:deviceadmin:tacacs",
    "label": "Cisco ISE TACACS+ Device Administration",
    "vendor": "cisco",
    "category": "Identity & Access Control",
    "index": "idx_network_ops",
    "sample": "2026-09-20T14:30:00.000ZSYSLOG_TIMESTAMP2026-09-20T14:30:00.000Z ise-pan01.corp.internal CISE_TACACS_Accounting 0001847299 1 0 2026-09-20T14:30:00.000ZISO_TIMESTAMP2026-09-20T14:30:00.000Z +00:00 0029481929 3300 NOTICE TACACS-Accounting: Command Authorization Succeeded, ConfigVersionId=127, User=netadmin_bob, Remote-Address=10.254.99.12, Device-IP-Address=10.254.1.1, Port=tty0, Privilege-Level=15, Command=configure terminal ; interface HundredGigE0/0/0/1 ; shutdown, Authen-Method=TACACS+"
  },
  {
    "id": "cisco:ise:guest:voucher",
    "label": "Cisco ISE Guest Captive Portal & Vouchers",
    "vendor": "cisco",
    "category": "Identity & Access Control",
    "index": "idx_network_ops",
    "sample": "{\\\"timestamp\\\":\\\"2026-09-20T14:30:00.000ZISO_TIMESTAMP2026-09-20T14:30:00.000Z\\\",\\\"event_type\\\":\\\"GUEST_VOUCHER_ACTIVATION\\\",\\\"ise_node\\\":\\\"ise-pan01.corp.internal\\\",\\\"portal_name\\\":\\\"Corporate_Sponsor_Guest_Portal\\\",\\\"voucher_code\\\":\\\"GUEST-9481-VX\\\",\\\"sponsor_user\\\":\\\"admin_frontdesk@corp.internal\\\",\\\"guest_phone\\\":\\\"+1-555-0199\\\",\\\"guest_email\\\":\\\"vendor_contractor@partner.com\\\",\\\"mac_address\\\":\\\"f4:f5:e8:11:22:33\\\",\\\"duration_hours\\\":8,\\\"vlan_assigned\\\":99,\\\"status\\\":\\\"ACTIVE\\\"}"
  },
  {
    "id": "cisco:duo:push:prompt",
    "label": "Cisco Duo Push Multi-Factor Authentication",
    "vendor": "cisco",
    "category": "Identity & Access Control",
    "index": "idx_security_fw",
    "sample": "{\\\"timestamp\\\":2026-09-20T14:30:00.000ZEPOCH2026-09-20T14:30:00.000Z,\\\"iso_timestamp\\\":\\\"2026-09-20T14:30:00.000ZISO_TIMESTAMP2026-09-20T14:30:00.000Z\\\",\\\"event_type\\\":\\\"authentication\\\",\\\"factor\\\":\\\"duo_push\\\",\\\"result\\\":\\\"SUCCESS\\\",\\\"reason\\\":\\\"user_approved\\\",\\\"user\\\":{\\\"name\\\":\\\"m.chowdhury@corp.internal\\\",\\\"groups\\\":[\\\"Enterprise_Admins\\\",\\\"NetDevOps\\\"]},\\\"application\\\":{\\\"name\\\":\\\"Splunk Enterprise Production NOC\\\",\\\"key\\\":\\\"DI94810294810\\\"},\\\"auth_device\\\":{\\\"name\\\":\\\"iPhone 15 Pro\\\",\\\"ip\\\":\\\"198.51.100.42\\\",\\\"location\\\":{\\\"city\\\":\\\"San Jose\\\",\\\"state\\\":\\\"California\\\",\\\"country\\\":\\\"US\\\"}},\\\"txid\\\":\\\"duo-tx-9948201\\\"}"
  },
  {
    "id": "cisco:duo:endpoint:posture",
    "label": "Cisco Duo Endpoint Device Posture & Health",
    "vendor": "cisco",
    "category": "Identity & Access Control",
    "index": "idx_security_fw",
    "sample": "{\\\"timestamp\\\":2026-09-20T14:30:00.000ZEPOCH2026-09-20T14:30:00.000Z,\\\"iso_timestamp\\\":\\\"2026-09-20T14:30:00.000ZISO_TIMESTAMP2026-09-20T14:30:00.000Z\\\",\\\"event_type\\\":\\\"endpoint_health\\\",\\\"device\\\":{\\\"os\\\":\\\"macOS\\\",\\\"os_version\\\":\\\"15.3.1\\\",\\\"model\\\":\\\"MacBookPro18,1\\\",\\\"encryption\\\":{\\\"disk\\\":\\\"FileVault_Encrypted\\\",\\\"status\\\":\\\"HEALTHY\\\"},\\\"security_software\\\":{\\\"edr\\\":\\\"CrowdStrike Falcon 7.14\\\",\\\"firewall_active\\\":true,\\\"screen_lock_enforced\\\":true},\\\"jailbroken\\\":false},\\\"user\\\":\\\"m.chowdhury@corp.internal\\\",\\\"posture_result\\\":\\\"COMPLIANT\\\",\\\"trusted_endpoint\\\":true}"
  },
  {
    "id": "cisco:duo:sso:saml",
    "label": "Cisco Duo Central SSO SAML Assertions",
    "vendor": "cisco",
    "category": "Identity & Access Control",
    "index": "idx_security_fw",
    "sample": "{\\\"timestamp\\\":2026-09-20T14:30:00.000ZEPOCH2026-09-20T14:30:00.000Z,\\\"iso_timestamp\\\":\\\"2026-09-20T14:30:00.000ZISO_TIMESTAMP2026-09-20T14:30:00.000Z\\\",\\\"event_type\\\":\\\"sso_auth\\\",\\\"auth_type\\\":\\\"SAML_2_0\\\",\\\"identity_provider\\\":\\\"Duo Central Single Sign-On\\\",\\\"service_provider\\\":\\\"Splunk Enterprise Production\\\",\\\"relay_state\\\":\\\"/app/netspout/netspout_canvas\\\",\\\"subject_name_id\\\":\\\"mchowdhury@splunk.com\\\",\\\"session_index\\\":\\\"duo_sso_sess_849201\\\",\\\"mfa_method\\\":\\\"duo_push\\\",\\\"ip_address\\\":\\\"198.51.100.42\\\",\\\"action\\\":\\\"ASSERTION_ISSUED\\\"}"
  },
  {
    "id": "cisco:duo:zerotrust:policy",
    "label": "Cisco Duo Zero Trust Application Policy",
    "vendor": "cisco",
    "category": "Identity & Access Control",
    "index": "idx_security_fw",
    "sample": "{\\\"timestamp\\\":2026-09-20T14:30:00.000ZEPOCH2026-09-20T14:30:00.000Z,\\\"iso_timestamp\\\":\\\"2026-09-20T14:30:00.000ZISO_TIMESTAMP2026-09-20T14:30:00.000Z\\\",\\\"event_type\\\":\\\"zero_trust_policy_evaluation\\\",\\\"policy_name\\\":\\\"High_Privilege_Core_Access\\\",\\\"policy_outcome\\\":\\\"ALLOW\\\",\\\"context\\\":{\\\"user_risk\\\":\\\"LOW\\\",\\\"device_trust\\\":\\\"VERIFIED_MANAGED\\\",\\\"location_risk\\\":\\\"DOMESTIC_ALLOWED\\\",\\\"geo_velocity_check\\\":\\\"PASSED\\\"},\\\"requested_resource\\\":\\\"cisco-catalyst-center-api\\\",\\\"enforced_action\\\":\\\"GRANT_SESSION\\\"}"
  },
  {
    "id": "cisco:duo:remote:vpn",
    "label": "Cisco Duo Secure Remote Access VPN",
    "vendor": "cisco",
    "category": "Identity & Access Control",
    "index": "idx_security_fw",
    "sample": "{\\\"timestamp\\\":2026-09-20T14:30:00.000ZEPOCH2026-09-20T14:30:00.000Z,\\\"iso_timestamp\\\":\\\"2026-09-20T14:30:00.000ZISO_TIMESTAMP2026-09-20T14:30:00.000Z\\\",\\\"event_type\\\":\\\"vpn_authentication\\\",\\\"vpn_gateway\\\":\\\"cisco-asa-vpn.corp.internal\\\",\\\"client_software\\\":\\\"Cisco AnyConnect / Secure Client 5.0\\\",\\\"assigned_ip\\\":\\\"10.240.12.88\\\",\\\"username\\\":\\\"mchowdhury@splunk.com\\\",\\\"factor\\\":\\\"duo_push\\\",\\\"status\\\":\\\"CONNECTED\\\",\\\"bytes_rx\\\":12849000,\\\"bytes_tx\\\":4820100,\\\"duration_seconds\\\":14400}"
  },
  {
    "id": "cisco:asa",
    "label": "Cisco ASA Adaptive Security Appliance",
    "vendor": "cisco",
    "category": "Security & Firewalls",
    "index": "idx_security_fw",
    "sample": "%ASA-6-302013: Built outbound TCP connection 984210 for outside:198.51.100.80/443 (198.51.100.80/443) to inside:10.20.10.45/52140 (198.51.100.200/52140)"
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
    "sample": "1,2026/09/18 17:16:25,001801000001,TRAFFIC,drop,2304,2026/09/18 17:16:25,198.51.100.150,10.0.10.80,0.0.0.0,0.0.0.0,Perimeter-Drop-Rule,jdoe,,web-browsing,vsys1,untrust,trust,ethernet1/1,ethernet1/2,log-forwarder,2026/09/18 17:16:25,98421,1,58210,80,0,0,0x0,tcp,deny,1420,0,1420,1,2026/09/18 17:16:25,0,any,0,12345678,0x0,10.0.0.0-10.255.255.255,US,0,1,0,policy-deny,0,0,0,0,,PA-5250,from-policy"
  },
  {
    "id": "pan:threat",
    "label": "Palo Alto Networks Threat Prevention",
    "vendor": "paloalto",
    "category": "Security & Firewalls",
    "index": "idx_security_fw",
    "sample": "1,2026/09/18 17:16:26,001801000001,THREAT,vulnerability,2304,2026/09/18 17:16:26,203.0.113.88,10.0.10.80,0.0.0.0,0.0.0.0,Perimeter-Inspection,attacker,,web-browsing,vsys1,untrust,trust,ethernet1/1,ethernet1/2,log-forwarder,2026/09/18 17:16:26,98425,1,49182,80,0,0,0x0,tcp,reset-both,\"Apache Log4j Remote Code Execution(30845)\",any,critical,client-to-server,92841,0x0,10.0.0.0-10.255.255.255,US,0,,0,,,PA-5250"
  },
  {
    "id": "fortinet:fortigate",
    "label": "Fortinet FortiOS Security Events",
    "vendor": "fortinet",
    "category": "Security & Firewalls",
    "index": "idx_security_fw",
    "sample": "date=2026-09-20 time=14:00:18 devname=\\\"fg-core-01\\\" devid=\\\"FG100E4Q18029481\\\" logid=\\\"0101037128\\\" type=\\\"event\\\" subtype=\\\"sdwan\\\" level=\\\"warning\\\" vd=\\\"root\\\" msg=\\\"SD-WAN rule 1: member wan2 SLA status changed to DEAD (latency: 184ms, packet loss: 12%)\\\""
  },
  {
    "id": "checkpoint:cef",
    "label": "Check Point Quantum Firewall CEF",
    "vendor": "checkpoint",
    "category": "Security & Firewalls",
    "index": "idx_security_fw",
    "sample": "time=1789761330|hostname=cp-gw-perimeter-01|product=Firewall|action=drop|src=198.51.100.44|dst=10.0.10.22|proto=tcp|src_port=49210|dst_port=445|service=smb|client_outbound_interface=eth1|dest_interface=eth2|rule=104|rule_name=\"Block_Inbound_SMB\"|policy=Standard_Perimeter|severity=High|severity_id=3|inzone=External|outzone=DMZ|reason=\"Drop by security policy rule\""
  },
  {
    "id": "cisco:catalyst:security:events",
    "label": "Cisco Catalyst 9300 Security Events",
    "vendor": "cisco",
    "category": "Campus Access & Wireless",
    "index": "idx_network_ops",
    "sample": "{\"status\": \"no_active_data\", \"msg\": \"No incidents in window\"}"
  },
  {
    "id": "cisco:catalyst:rogue:threat_details",
    "label": "Cisco Catalyst Rogue AP Detection",
    "vendor": "cisco",
    "category": "Campus Access & Wireless",
    "index": "idx_wireless_ops",
    "sample": "{\"macAddress\": \"C2:D6:76:6F:BA:30\", \"updatedTime\": 2026-09-20T14:30:00.000ZEPOCH_MS2026-09-20T14:30:00.000Z, \"vendor\": \"UNKNOWN\", \"threatType\": \"mapleRule2\", \"threatLevel\": \"High\", \"apName\": \"OTT-Lab-2802-AP\", \"detectingAPMac\": \"70:7D:B9:13:97:20\", \"siteId\": \"e2f0aaaa-896d-4ca3-8ed0-069c49b0be32\", \"rssi\": \"-55\", \"ssid\": \"internet\", \"containment\": \"Open\", \"state\": \"Active\", \"siteNameHierarchy\": \"Global/Ottawa/OTT02-Lab/OTT02-SDA\", \"totalClients\": 0, \"site_name_resolved\": \"Unknown\"}"
  },
  {
    "id": "cisco:sdwan:linkhealth",
    "label": "Cisco SD-WAN vEdge Link Health",
    "vendor": "cisco",
    "category": "Campus Access & Wireless",
    "index": "idx_network_ops",
    "sample": "{\"vdevice-name\": \"1.1.1.110\", \"rx-errors\": 0, \"tx-kbps\": 0, \"if-admin-status\": \"if-state-up\", \"ipv6-tcp-adjust-mss\": \"0\", \"tx-pps\": 0, \"tx-errors\": 0, \"ifname\": \"vmanage_system\", \"interface-type\": \"iana-iftype-sw-loopback\", \"rx-pps\": 0, \"if-oper-status\": \"if-oper-state-ready\", \"ifindex\": \"16\", \"num-flaps\": \"0\", \"ipv4-tcp-adjust-mss\": \"0\", \"rx-packets\": 0, \"bia-address\": \"00:00:00:00:00:00\", \"vpn-id\": \"0\", \"vdevice-host-name\": \"SD-WANEdge-TOR\", \"ipv4-subnet-mask\": \"255.255.255.255\", \"mtu\": \"0\", \"rx-drops\": 0, \"tx-drops\": 0, \"hwaddr\": \"00:d6:fe:c4:26:40\", \"ip-address\": \"0.0.0.0\", \"speed-mbps\": 10000, \"auto-downstream-bandwidth\": \"N/A\", \"vdevice-dataKey\": \"1.1.1.110-0-vmanage_system-0.0.0.0-00:d6:fe:c4:26:40\", \"tx-octets\": 0, \"auto-upstream-bandwidth\": \"N/A\", \"tx-packets\": 0, \"rx-kbps\": 0, \"rx-octets\": 0, \"lastupdated\": 1784258219839}"
  },
  {
    "id": "cisco:sdwan:BGP-5-ADJCHANGE",
    "label": "Cisco SD-WAN BGP Route Failover",
    "vendor": "cisco",
    "category": "Campus Access & Wireless",
    "index": "idx_network_ops",
    "sample": "2026-09-20T14:30:00.000ZTS2026-09-20T14:30:00.000Z 10.201.48.120 3264: *2026-09-20T14:30:00.000ZTS2026-09-20T14:30:00.000Z:  %BGP-5-ADJCHANGE: neighbor 10.201.152.1 vpn vrf UBC_TENANT Down Neighbor deleted"
  },
  {
    "id": "meraki:accesspoints",
    "label": "Cisco Meraki MR Wireless Telemetry",
    "vendor": "cisco",
    "category": "Campus Access & Wireless",
    "index": "idx_wireless_ops",
    "sample": "{  \"serial\": \"Q2JD-TOR-MR46\",  \"name\": \"MR46-Toronto-Floor1\",  \"model\": \"MR46\",  \"networkId\": \"N_TORONTO_DC\",  \"status\": \"online\",  \"clientCount\": 28,  \"channel24\": 6,  \"channel5\": 36,  \"authFailures\": 0,  \"assocFailures\": 0,  \"dhcpFailures\": 0,  \"dnsFailures\": 0,  \"utilization24\": 18,  \"utilization5\": 14 }"
  },
  {
    "id": "aruba:syslog",
    "label": "Aruba CX Campus Switching",
    "vendor": "aruba",
    "category": "Campus Access & Wireless",
    "index": "idx_network_ops",
    "sample": "Sep 18 17:15:25 aruba-wlc-01 authmgr[1842]: <522008> <INFO> client_mac=00:1a:1e:2b:4c:5d username=jdoe@acme.corp bssid=20:a6:cd:44:11:00 ap_name=AP-Campus-Fl2-West radio_channel=36 rssi=42 snr=38 auth_status=SUCCESS vlan=104 reason=\"Client authentication succeeded\""
  },
  {
    "id": "zscaler:zia",
    "label": "Zscaler Internet Access (ZIA) Web Log",
    "vendor": "zscaler",
    "category": "Cloud, SASE & Observability",
    "index": "idx_security_fw",
    "sample": "May 20 14:00:28 zia-gateway-sjc zscaler-nss: sourcetype=zscaler:zia datetime=\\\"2026-09-20 14:00:28 UTC\\\" user=\\\"alice.sec@corp.internal\\\" department=\\\"SecOps\\\" reqmethod=\\\"GET\\\" url=\\\"https://portal.azure.com\\\" action=\\\"Allowed\\\" appname=\\\"Azure Portal\\\" dlprules=\\\"None\\\" traffic_class=\\\"Business\\\""
  },
  {
    "id": "zscaler:lss",
    "label": "Zscaler Private Access (ZPA) LSS",
    "vendor": "zscaler",
    "category": "Cloud, SASE & Observability",
    "index": "idx_security_fw",
    "sample": "{\"datetime\":\"2026-09-20 14:30:00\",\"Customer\":\"Acme-Enterprise\",\"SAMAccountName\":\"alex.turner@corp.internal\",\"Application\":\"Corporate Intranet ERP\",\"AppConnector\":\"app-conn-us-east-01\",\"ClientPublicIP\":\"198.51.100.44\",\"ServerIP\":\"10.100.4.50\",\"ServerPort\":443,\"PolicyAction\":\"Allow\",\"ConnectionStatus\":\"Success\"}"
  },
  {
    "id": "cisco:thousandeyes:metric",
    "label": "Cisco ThousandEyes Synthetic Metrics",
    "vendor": "cisco",
    "category": "Cloud, SASE & Observability",
    "index": "idx_performance_metrics",
    "sample": "metric"
  },
  {
    "id": "sc4snmp:metric",
    "label": "Splunk Connect for SNMP Metrics",
    "vendor": "cisco",
    "category": "Cloud, SASE & Observability",
    "index": "cisco_mdt_metrics",
    "sample": "{\"time\":1789840800.0,\"event\":\"metric\",\"source\":\"sc4snmp\",\"sourcetype\":\"sc4snmp:metric\",\"host\":\"sw-cisco-8000-01\",\"vendor\":\"cisco\",\"fields\":{\"metric_name:ifHCInOctets\":48910294810,\"metric_name:ifHCOutOctets\":39184719280,\"ifDescr\":\"HundredGigE1/0/1\"}}"
  },
  {
    "id": "sc4snmp:event",
    "label": "Splunk Connect for SNMP Traps",
    "vendor": "cisco",
    "category": "Cloud, SASE & Observability",
    "index": "idx_network_ops",
    "sample": "{\\\"timestamp\\\": 1789840800, \\\"host\\\": \\\"10.254.8.1\\\", \\\"snmp_version\\\": \\\"3\\\", \\\"mib\\\": \\\"IF-MIB\\\", \\\"oid\\\": \\\"1.3.6.1.2.1.2.2.1.8.1\\\", \\\"metric_name\\\": \\\"ifOperStatus\\\", \\\"value\\\": 1, \\\"value_name\\\": \\\"up\\\", \\\"tags\\\": {\\\"interface\\\": \\\"GigabitEthernet1/0/1\\\", \\\"device_vendor\\\": \\\"Cisco\\\"}}"
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
    "vendor": "netapp",
    "category": "Storage & Data Center",
    "index": "idx_performance_metrics",
    "sample": "{\"timestamp\":\"2026-09-20T14:30:00.000Z\",\"cluster\":\"netapp-ontap-cl01\",\"node\":\"node-01\",\"svm\":\"svm_cifs_nfs\",\"volume\":\"vol_finance_nfs\",\"protocol\":\"nfs4.1\",\"ops\":14200,\"latency_us\":850,\"throughput_mbps\":412.5,\"status\":\"NORMAL\"}"
  },
  {
    "id": "cisco:dc:nexus9k:syslog",
    "label": "Cisco Nexus 9000 Data Center Syslog",
    "vendor": "cisco",
    "category": "Storage & Data Center",
    "index": "idx_performance_metrics",
    "sample": "2026-09-20T14:30:00.000ZSYSLOG_TIMESTAMP2026-09-20T14:30:00.000Z 2026-09-20T14:30:00.000ZHOST2026-09-20T14:30:00.000Z OTT-CORE01: 2026 2026-09-20T14:30:00.000ZSYSLOG_TIMESTAMP2026-09-20T14:30:00.000Z EST: %ICMPV6-3-ND_RA_LOG:  icmpv6 [19815]  fe80::232:17ff:fe3c:ac58 on Vlan506 Current-hop-limit:64, m-bit:0, o-bit:0, rtr-lifetime:1800, reachable-time:0, retrans-timer:0 "
  },
  {
    "id": "arista:telemetry:json",
    "label": "Arista EOS Streaming Telemetry",
    "vendor": "arista",
    "category": "Storage & Data Center",
    "index": "idx_performance_metrics",
    "sample": "{\"time\": 1789761320, \"event\": \"metric\", \"source\": \"switch-leaf-01\", \"sourcetype\": \"arista:telemetry:json\", \"host\": \"switch-leaf-01.acme.local\", \"index\": \"cisco_mdt_metrics\", \"fields\": {\"metric_name:arista_interface_in_octets\": 984120394, \"metric_name:arista_interface_out_octets\": 1284910283, \"metric_name:arista_interface_in_errors\": 0, \"metric_name:arista_queue_depth_bytes\": 14200, \"interface\": \"Ethernet1/1\", \"speed\": 100000000000}}"
  },
  {
    "id": "cisco:catalyst:client",
    "label": "Cisco Catalyst Client",
    "vendor": "cisco",
    "category": "Cisco Catalyst",
    "index": "netops_logs",
    "sample": "{\"ClientID\": \"00:50:56:B7:10:E2\", \"ClientMACAddress\": \"00:50:56:B7:10:E2\", \"ClientType\": \"Wired\", \"ClientName\": \"sandbox-ise\", \"ClientUserID\": \"\", \"ClientUsername\": \"N/A\", \"ClientIPv4Address\": \"10.20.1.5\", \"ClientOSType\": \"Unclassified\", \"ClientDeviceType\": \"Unclassified\", \"ClientSiteHierarchy\": \"Global/Toronto_SDA/Toronto_BLD\", \"ClientLastUpdatedTime\": 1789749600000, \"ClientConnectionStatus\": \"connected\", \"ClientTrafficTXBytes\": 1619129685, \"ClientTrafficRXBytes\": 1276507, \"ClientTrafficUsage\": 1620406192, \"ClientTrafficRXPackets\": 0, \"ClientTrafficTXPackets\": 0, \"ClientTrafficRXRate\": 34040.0, \"ClientTrafficTXRate\": 43177511, \"ClientTrafficRXLinkErrorPercentage\": 0, \"ClientTrafficTXLinkErrorPercentage\": 0, \"ClientTrafficRXRetries\": 0, \"ClientTrafficRXRetryPercentage\": 0, \"ClientTrafficTXDrops\": 0, \"ClientTrafficTXDropPercentage\": 0, \"ClientTrafficDNSRequestCount\": 0, \"ClientTrafficDNSResponseCount\": 0, \"ClientConnectedNetworkDeviceID\": \"e3653cdd-e7af-4c7e-ad3f-b5bc15cd56ee\", \"ClientConnectedNetworkDeviceName\": \"Toronto_WLC.ott04-lab.ca\", \"ClientConnectedNetworkDeviceManagementIP\": \"10.20.1.8\", \"ClientConnectedNetworkDeviceMAC\": \"\", \"ClientConnectedNetworkDeviceType\": \"Switch\", \"ClientConnectionVLANID\": \"1\", \"ClientConnectionSessionDuration\": -1, \"ClientConnectionVNID\": \"\", \"ClientConnectionSecurityGroupTag\": \"0.0\", \"ClientConnectionLinkSpeed\": 1000000000, \"ClientConnectionBand\": \"Unclassified\", \"ClientConnectionSSID\": \"\", \"ClientConnectionAuthType\": \"\", \"ClientConnectionAPMAC\": \"\", \"ClientConnectionAPEthernetMAC\": \"-1\", \"ClientConnectionChannel\": \"0\", \"ClientConnectionChannelWidth\": \"\", \"ClientConnectionProtocol\": \"Unclassified\", \"ClientConnectionRSSI\": 0, \"ClientConnectionSNR\": 0, \"ClientConnectionDataRate\": 0, \"cisco_catalyst_host\": \"https://10.20.1.16\"}"
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
    "sample": "{\"ComplianceDeviceID\": \"4881747e-0e66-4275-8611-f9ec86746a7d\", \"ComplianceStatus\": \"NON_COMPLIANT\", \"ComplianceLastUpdateTime\": 1789732708220, \"DeviceName\": \"C9800.maple.ciscolabs.com\", \"IpAddress\": \"10.0.10.50\", \"DeviceFamily\": \"Wireless Controller\", \"Reachability\": \"Reachable\", \"ReachabilityFailureReason\": \"\", \"ManageErrors\": \"\", \"Manageability\": \"Managed\", \"MACAddress\": \"00:50:56:b7:74:4c\", \"DeviceRole\": \"UNKNOWN\", \"ImageVersion\": \"17.12.3\", \"Uptime\": \"84 days, 18:12:33.02\", \"UptimeSeconds\": 7339426, \"LastUpdated\": \"2026-09-18 12:57:01\", \"LastUpdateTime\": 1789736221088, \"SerialNumber\": \"93LQHUBXAAL\", \"DeviceSeries\": \"Cisco Catalyst 9800 Wireless Controllers for Cloud\", \"Platform\": \"C9800-CL-K9\", \"SupportType\": \"Supported\", \"AssociatedWLCIP\": \"\", \"Site\": \"Global/Ottawa/OTT02-Lab/OTT02-SDA\", \"ComplianceDetail\": \"False\", \"ComplianceCount\": \"False\", \"cisco_catalyst_host\": \"https://dnac.maple.ciscolabs.com\"}"
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
    "sample": "{\"IssueID\": \"4746c82c-0eba-4182-88b9-d296c827cc13\", \"IssueSpecificCategory\": \"Availability\", \"IssueSpecificSource\": \"Cisco DNA\", \"IssueSpecificName\": \"switch_unreachable\", \"IssueSpecificDescription\": \"This network device dmz1.dcloud.cisco.com is unreachable from Cisco Catalyst Center. The device role is ACCESS.\", \"IssueSpecificEntity\": \"network_device\", \"IssueSpecificEntityValue\": \"86af9de8-d550-4478-b4b1-d0168800ff47\", \"IssueSpecificSeverity\": \"HIGH\", \"IssueSpecificPriority\": \"P1\", \"IssueSpecificSummary\": \"Network Device dmz1.dcloud.cisco.com is unreachable from Cisco Catalyst Center\", \"IssueSpecificTimestamp\": 1789421432804, \"IssueName\": \"Network Device dmz1.dcloud.cisco.com is unreachable from Cisco Catalyst Center\", \"IssueDeviceRole\": \"\", \"IssueAiDriven\": \"No\", \"IssueClientMac\": \"\", \"IssueCount\": 1, \"IssueStatus\": \"active\", \"IssuePriority\": \"P1\", \"IssueCategory\": \"\", \"DeviceID\": \"86af9de8-d550-4478-b4b1-d0168800ff47\", \"DeviceName\": \"dmz1.dcloud.cisco.com\", \"DeviceIpAddress\": \"10.0.1.107\", \"DeviceFamily\": \"Switches and Hubs\", \"DeviceMACAddress\": \"52:54:00:bb:3d:25\", \"DeviceRole\": \"ACCESS\", \"DeviceImageVersion\": \"17.18.2\", \"DeviceUptime\": \"24 days, 20:32:13.00\", \"DeviceUptimeSeconds\": 2229687, \"DeviceLastUpdated\": \"2026-09-17 18:44:31\", \"DeviceLastUpdateTime\": 1789670671698, \"DeviceSerialNumber\": \"CML12107UAD\", \"DeviceSeries\": \"Cisco Catalyst 9000 Series Virtual Switches\", \"DevicePlatform\": \"C9KV-UADP-8P\", \"DeviceSupportType\": \"Supported\", \"cisco_catalyst_host\": \"https://dnac.maple.ciscolabs.com\"}"
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
    "sample": "{\"macAddress\": \"C2:D6:66:6F:BA:30\", \"mldMacAddress\": \"NA\", \"updatedTime\": 2026-09-20T14:30:00.000ZEPOCH_MS2026-09-20T14:30:00.000Z, \"createdTime\": 2026-09-20T14:30:00.000ZEPOCH_MS2026-09-20T14:30:00.000Z, \"threatType\": \"mapleRule2\", \"threatLevel\": \"High\", \"apName\": \"OTT-Lab-9117-AP\", \"detectingAPMac\": \"0C:D0:F8:95:5B:20\", \"ssid\": \"internet\", \"containment\": \"Open\", \"radioType\": \"8\", \"controllerIp\": \"10.0.10.50\", \"controllerName\": \"C9800.maple.ciscolabs.com\", \"channelNumber\": \"6\", \"siteNameHierarchy\": \"Global/Ottawa/OTT02-Lab/OTT02-SDA\", \"encryption\": \"Open\", \"switchIp\": \"-\", \"switchName\": \"-\", \"portDescription\": \"-\"}"
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
    "sample": "{\"status\": \"polling_complete\", \"timestamp\": \"2026-09-20T14:30:00.000ZGOTS2026-09-20T14:30:00.000Z\"}"
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
    "sample": "{\"profileDetails\": {\"instanceUuid\": \"6fdbebc5-b9f9-45bd-a7a6-735de93e0c25\", \"name\": \"Dovetail-SSID\", \"ssidDetails\": [{\"name\": \"Ott02-LAB-SDA-CORP\", \"enableFabric\": false, \"flexConnect\": {\"enableFlexConnect\": false}, \"interfaceName\": \"management\", \"wlanProfileName\": \"Ott02-LAB-SDA-CORP_profile\", \"policyProfileName\": \"Ott02-LAB-SDA-CORP_profile\"}], \"sites\": [\"Global/Ottawa/OTT02-Lab\", \"Global/Ottawa/OTT02-Lab/OTT02-SDA\"]}}"
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
    "sample": "{\"timestamp\": 2026-09-20T14:30:00.000ZEPOCH_MS2026-09-20T14:30:00.000Z, \"threatData\": [{\"threatType\": \"mapleRule2\", \"threatLevel\": \"High\", \"threatCount\": 16, \"threatTypeInt\": \"18001\"}, {\"threatType\": \"rougeRule\", \"threatLevel\": \"High\", \"threatCount\": 6, \"threatTypeInt\": \"18000\"}, {\"threatType\": \"Neighbor\", \"threatLevel\": \"Informational\", \"threatCount\": 3, \"threatTypeInt\": \"1901\"}, {\"threatType\": \"Interferer\", \"threatLevel\": \"Potential\", \"threatCount\": 1, \"threatTypeInt\": \"5001\"}]}"
  },
  {
    "id": "cisco:catalyst:threat:summary:legacy",
    "label": "Cisco Catalyst Threat Summary Legacy",
    "vendor": "cisco",
    "category": "Cisco Catalyst",
    "index": "netops_logs",
    "sample": "{\"timestamp\": 2026-09-20T14:30:00.000ZEPOCH_MS2026-09-20T14:30:00.000Z, \"threatData\": [{\"threatType\": \"mapleRule2\", \"threatLevel\": \"High\", \"threatCount\": 17, \"threatTypeInt\": \"18001\"}, {\"threatType\": \"Neighbor\", \"threatLevel\": \"Informational\", \"threatCount\": 3, \"threatTypeInt\": \"1901\"}, {\"threatType\": \"rougeRule\", \"threatLevel\": \"High\", \"threatCount\": 2, \"threatTypeInt\": \"18000\"}, {\"threatType\": \"Interferer\", \"threatLevel\": \"Potential\", \"threatCount\": 1, \"threatTypeInt\": \"5001\"}]}"
  },
  {
    "id": "cisco:dc:aci:health",
    "label": "Cisco Dc Aci Bridge Domain",
    "vendor": "cisco",
    "category": "Cisco DC (ACI, Nexus)",
    "index": "netops_logs",
    "sample": "{\"time\": \"2026-09-20T14:30:00.000ZISO_TS2026-09-20T14:30:00.000Z\", \"dn\": \"uni/tn-MAPLE/BD-MAPLE_BD04_SPLUNK/health\", \"cur\": 100, \"prev\": 100, \"twScore\": 100, \"maxSev\": \"cleared\", \"descr\": \"Bridge Domain MAPLE_BD04_SPLUNK healthy\", \"apic_host\": \"2026-09-20T14:30:00.000ZAPIC_HOST2026-09-20T14:30:00.000Z\", \"component\": \"fvBD\", \"tenant\": \"MAPLE\", \"bd\": \"MAPLE_BD04_SPLUNK\", \"operSt\": \"online\"}"
  },
  {
    "id": "cisco:dc:aci:class",
    "label": "Cisco Dc Aci Class",
    "vendor": "cisco",
    "category": "Cisco DC (ACI, Nexus)",
    "index": "netops_logs",
    "sample": "{\"time\": \"2026-09-20T14:30:00.000ZISO_TS2026-09-20T14:30:00.000Z\", \"dn\": \"uni/tn-MAPLE/BD-MAPLE_BD04_SPLUNK/subnet-[10.20.104.200/24]\", \"ip\": \"10.20.104.200/24\", \"scope\": \"public,shared\", \"ctrl\": \"unspecified\", \"name\": \"web-subnet\", \"parentDn\": \"uni/tn-MAPLE/BD-MAPLE_BD04_SPLUNK\", \"apic_host\": \"2026-09-20T14:30:00.000ZAPIC_HOST2026-09-20T14:30:00.000Z\", \"component\": \"fvSubnet\", \"l3out_associated\": \"out-L3Out-OSPF\"}"
  },
  {
    "id": "cisco:dc:nexus9k",
    "label": "Cisco Dc Nexus9K",
    "vendor": "cisco",
    "category": "Cisco DC (ACI, Nexus)",
    "index": "netops_logs",
    "sample": "{\"timestamp\": \"2026-09-20T14:30:00.000ZGOTS2026-09-20T14:30:00.000Z\", \"component\": \"nxpower\", \"device\": \"10.0.0.253:443\", \"Row_info\": {\"voltage_level\": \"12\"}}"
  },
  {
    "id": "cisco:dc:aci:events",
    "label": "Cisco ACI Fabric State Events",
    "vendor": "cisco",
    "category": "Cisco DC (ACI, Nexus)",
    "index": "idx_network_ops",
    "sample": "{\"time\": \"2026-09-20T14:30:00.000ZISO_TS2026-09-20T14:30:00.000Z\", \"code\": \"E4208451\", \"type\": \"config-change\", \"severity\": \"major\", \"affected\": \"uni/tn-MAPLE/BD-MAPLE_BD04_SPLUNK/subnet-[10.20.104.200/24]\", \"descr\": \"Subnet 10.20.104.200/24 unadvertised from L3Out out-L3Out-OSPF (route withdrawn from BGP/OSPF core)\", \"user\": \"admin_ops\", \"cause\": \"route-withdrawn\", \"apic_host\": \"2026-09-20T14:30:00.000ZAPIC_HOST2026-09-20T14:30:00.000Z\"}"
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
    "sample": "{\\\"timestamp\\\": \\\"2026-09-20T14:00:11.000Z\\\", \\\"device\\\": \\\"sw-nexus-9300-01\\\", \\\"facility\\\": \\\"ETH_PORT\\\", \\\"severity\\\": 5, \\\"type\\\": \\\"LINK_STATUS\\\", \\\"interface\\\": \\\"Ethernet1/1\\\", \\\"status\\\": \\\"UP\\\", \\\"speed_gbps\\\": 100}"
  },
  {
    "id": "cisco:nxos:syslog",
    "label": "Cisco NX-OS Syslog Event",
    "vendor": "cisco",
    "category": "Cisco DC (ACI, Nexus)",
    "index": "idx_network_ops",
    "sample": "2026 Sep 20 14:00:12 sw-nexus-9300-01 %OSPF-5-ADJCHANGE: ospf-1 [1024] Process 1, Nbr 10.254.0.2 on Ethernet1/1 from LOADING to FULL, Done"
  },
  {
    "id": "cisco:dnac:audit:logs",
    "label": "Cisco Dnac Audit Logs",
    "vendor": "cisco",
    "category": "Cisco DNAC",
    "index": "netops_logs",
    "sample": "{\"version\": \"1.0.0\", \"clientId\": \"admin\", \"efInstanceId\": \"8bc79c1e-9614-4b90-94e2-b210740c85de\", \"instanceId\": \"f7924add-c576-4617-80d4-62da85174cb3\", \"eventId\": \"AUDIT_LOG_EVENT\", \"namespace\": \"AUDIT_LOG\", \"name\": \"AUDIT_LOG\", \"description\": \"Intent API \\\"Get Issue Enrichment Details\\\" Executed\", \"type\": \"AUDIT_LOG\", \"category\": \"INFO\", \"domain\": \"Programmability\", \"subDomain\": \"APIs and Integrations\", \"severity\": 1, \"timestamp\": 1784258442784, \"details\": {\"requestPayload\": \"The request to execute BAPI with technical name \\\"issue-enrichment-details\\\" and rest method \\\"GET\\\" was received\"}, \"ciscoDnaEventLink\": \"\", \"note\": null, \"productId\": \"Cisco Catalyst Center\", \"tntId\": \"631807903ddfd1674bd7ce02\", \"context\": null, \"userId\": \"admin\", \"i18n\": null, \"eventHierarchy\": null, \"message\": null, \"messageParams\": null, \"additionalDetails\": {\"eventMetadata\": {\"auditLogMetadata\": {\"type\": \"API\", \"version\": \"1.0.0\"}}}, \"parentInstanceId\": null, \"network\": null, \"isSimulated\": false, \"startTime\": 1784258442786, \"isPrivateEvent\": true, \"dnacIP\": \"10.0.10.86\", \"payloadSize\": 1815, \"eventSize\": 1949, \"userName\": \"admin\", \"childCount\": 0, \"isACKnowledgeable\": false, \"isAlert\": false, \"isDeprecated\": false, \"resourceDomain\": {\"name\": \"SUPER-ADMIN_GLOBAL\", \"resourceGroups\": [{\"srcResourceId\": \"*\", \"type\": \"site\", \"name\": \"Global\"}], \"_id\": \"9801e2fd865464c18b469cd5d18c1fd6a1147ebf\"}, \"tenantId\": \"SYS0\", \"src\": \"10.0.10.86\"}"
  },
  {
    "id": "cisco:dnac:client",
    "label": "Cisco Dnac Client",
    "vendor": "cisco",
    "category": "Cisco DNAC",
    "index": "netops_logs",
    "sample": "{\"id\": \"E8:BC:E4:74:07:FA\", \"macAddress\": \"E8:BC:E4:74:07:FA\", \"type\": \"Wired\", \"name\": \"SEPE8BCE47407FA\", \"userId\": null, \"username\": \"9Qx9CJ5O351+SFhFnaESDaKssazYM4bgml3GbE7MDQA=\", \"ipv4Address\": null, \"ipv6Addresses\": [\"fe80::eabc:e4ff:fe74:7fa\"], \"vendor\": \"Cisco Systems, Inc.\", \"osType\": \"unknown\", \"osVersion\": null, \"formFactor\": \"IP Phone\", \"trustScore\": 6.0, \"deviceType\": \"Cisco-IP-Phone 9841\", \"siteHierarchy\": \"Global/Toronto_SDA/Toronto_BLD\", \"siteHierarchyId\": \"/34a9c832-12d0-4d71-90c2-f538a791012d/9ce279dd-e59c-426b-9b0e-de29a0954cff/8b6f4e1f-7f5c-4996-a871-75ca6c832493/\", \"siteId\": \"8b6f4e1f-7f5c-4996-a871-75ca6c832493\", \"lastUpdatedTime\": 1784258040000, \"connectionStatus\": \"connected\", \"tracked\": \"No\", \"isPrivateMacAddress\": false, \"health\": {\"overallScore\": 1, \"onboardingScore\": 1, \"connectedScore\": 0, \"linkErrorPercentageThreshold\": 1.0, \"isLinkErrorIncluded\": true, \"discardsThreshold\": 10.0, \"isDiscardsIncluded\": false, \"utilizationThreshold\": 90.0, \"isUtilizationIncluded\": false, \"rssiThreshold\": -72, \"snrThreshold\": 9, \"dataRateThreshold\": -1, \"retriesThreshold\": 50, \"isRssiIncluded\": true, \"isSnrIncluded\": true, \"isDataRateIncluded\": false, \"isRetriesIncluded\": false}, \"traffic\": {\"txBytes\": 7524, \"rxBytes\": 20949, \"usage\": 28473, \"rxPackets\": 0, \"txPackets\": 0, \"rxRate\": 558.0, \"txRate\": 200.0, \"rxLinkErrorPercentage\": 0.0, \"txLinkErrorPercentage\": 0.0, \"inDiscards\": 0.0, \"outDiscards\": 0.0, \"inUtilization\": 0.0, \"outUtilization\": 0.0, \"rxRetries\": 0, \"rxRetryPercentage\": 0.0, \"txDrops\": 0, \"txDropPercentage\": null, \"dnsRequestCount\": 0, \"dnsResponseCount\": 0}, \"connectedNetworkDevice\": {\"connectedNetworkDeviceId\": \"8f4a9102-0208-4790-96ec-ffc35cd5b844\", \"connectedNetworkDeviceName\": \"TOR-FIAB.ott04-lab.ca\", \"connectedNetworkDeviceManagementIp\": \"10.201.48.105\", \"connectedNetworkDeviceMac\": null, \"connectedNetworkDeviceType\": \"Switch\", \"interfaceName\": \"TenGigabitEthernet1/0/2\", \"interfaceSpeed\": 1000000000, \"duplexMode\": \"Full Duplex\"}, \"connection\": {\"vlanId\": \"2046\", \"sessionDuration\": -1, \"vnId\": null, \"l2Vn\": null, \"l3Vn\": null, \"securityGroupTag\": \"0.0\", \"linkSpeed\": 1000000000, \"bridgeVMMode\": \"0.0\", \"band\": null, \"ssid\": null, \"authType\": null, \"wlcName\": null, \"wlcId\": null, \"apMac\": null, \"apEthernetMac\": \"-1\", \"apMode\": \"Unknown\", \"radioId\": 0, \"channel\": \"0\", \"channelWidth\": null, \"protocol\": \"Unclassified\", \"protocolCapability\": \"Unclassified\", \"upnId\": null, \"upnName\": null, \"upnOwner\": null, \"upnDuid\": null, \"rssi\": 0, \"snr\": 0, \"dataRate\": 0, \"isIosAnalyticsCapable\": false, \"isFabricClient\": true}, \"onboarding\": {\"avgRunDuration\": 0, \"maxRunDuration\": 0, \"avgAssocDuration\": 0, \"maxAssocDuration\": 0, \"avgAuthDuration\": 0, \"maxAuthDuration\": 0, \"avgDhcpDuration\": 0, \"maxDhcpDuration\": 0, \"maxRoamingDuration\": null, \"aaaServerIp\": null, \"dhcpServerIp\": null, \"onboardingTime\": 0, \"authDoneTime\": 0, \"assocDoneTime\": 0, \"dhcpDoneTime\": 0, \"roamingTime\": 0, \"failedRoamingCount\": 0, \"successfulRoamingCount\": 0, \"totalRoamingAttempts\": 0, \"assocFailureReason\": null, \"aaaFailureReason\": \"SUCCESS\", \"dhcpFailureReason\": \"dhcpRootCause\", \"otherFailureReason\": null, \"latestFailureReason\": \"dhcpRootCause\"}, \"latency\": {\"video\": null, \"voice\": null, \"bestEffort\": null, \"background\": null}, \"cisco_catalyst_host\": \"2026-09-20T14:30:00.000ZHOST2026-09-20T14:30:00.000Z\"}"
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
    "sample": "{\"ComplianceDeviceID\": \"4881747e-0e66-4275-8611-f9ec86746a7d\", \"ComplianceStatus\": \"NON_COMPLIANT\", \"ComplianceLastUpdateTime\": 1784246310488, \"DeviceName\": \"C9800.maple.ciscolabs.com\", \"IpAddress\": \"10.0.10.50\", \"DeviceFamily\": \"Wireless Controller\", \"Reachability\": \"Reachable\", \"ReachabilityFailureReason\": \"\", \"ManageErrors\": \"\", \"Manageability\": \"Managed\", \"MACAddress\": \"00:50:56:b7:74:4c\", \"DeviceRole\": \"UNKNOWN\", \"ImageVersion\": \"17.12.3\", \"Uptime\": \"21 days, 6:15:29.40\", \"UptimeSeconds\": 1845569, \"LastUpdated\": \"2026-07-17 00:56:40\", \"LastUpdateTime\": 1784249800208, \"SerialNumber\": \"93LQHUBXAAL\", \"DeviceSeries\": \"Cisco Catalyst 9800 Wireless Controllers for Cloud\", \"Platform\": \"C9800-CL-K9\", \"SupportType\": \"Supported\", \"AssociatedWLCIP\": \"\", \"cisco_catalyst_host\": \"https://dnac.maple.ciscolabs.com\", \"ComplianceDetail\": \"False\", \"ComplianceCount\": \"False\"}"
  },
  {
    "id": "cisco:dnac:devicehealth",
    "label": "Cisco Dnac Devicehealth",
    "vendor": "cisco",
    "category": "Cisco DNAC",
    "index": "netops_logs",
    "sample": "{\"DeviceName\": \"TRN-SDA-C9500.maple.ciscolabs.com\", \"IpAddress\": \"10.120.1.1\", \"DeviceFamily\": \"Switches and Hubs\", \"Reachability\": \"Unreachable\", \"ReachabilityFailureReason\": \"SNMP Connectivity Failed\", \"ManageErrors\": \"Partial Collection Failure\", \"Manageability\": \"Managed (With Errors)\", \"MACAddress\": \"74:ad:98:6c:9f:20\", \"DeviceRole\": \"DISTRIBUTION\", \"ImageVersion\": \"17.18.1\", \"Uptime\": \"13 days, 0:18:47.17\", \"UptimeSeconds\": 1155260, \"LastUpdated\": \"2026-07-16 18:44:48\", \"LastUpdateTime\": 1784227488350, \"SerialNumber\": \"FDO25250L53\", \"DeviceSeries\": \"Cisco Catalyst 9500 Series Switches\", \"Platform\": \"C9500-48Y4C\", \"SupportType\": \"Supported\", \"AssociatedWLCIP\": \"\", \"DeviceID\": \"0c379365-f5b4-4a3d-9a3d-1dc3e6689a18\", \"DeviceDescription\": \"Cisco IOS Software [IOSXE], Catalyst L3 Switch Software (CAT9K_IOSXE), Version 17.18.1, RELEASE SOFTWARE (fc2) Technical Support: http://www.cisco.com/techsupport Copyright (c) 1986-2025 by Cisco Systems, Inc. Compiled Wed 06-Aug-25 03:56 by mcpre\", \"DeviceType\": \"Cisco Catalyst C9500-48Y4C Switch\", \"HasHealthReport\": \"True\", \"OverallHealth\": -2, \"HealthScore\": -2, \"IssueCount\": 0, \"Site\": \"Global/Toronto/TRN01-LAb\", \"Location\": \"Global/Toronto/TRN01-LAb\", \"InterfaceLinkErrHealth\": -1, \"CPUUtilization\": 0, \"CPUHealth\": -1, \"MemoryUtilizationHealth\": -1.0, \"MemoryUtilization\": 0, \"InterDeviceLinkAvailHealth\": 0, \"HasClientCount\": \"False\", \"ClientCountRadio0\": 0, \"ClientCountRadio1\": 0, \"ClientCountGhz24\": 0, \"ClientCountGhz50\": 0, \"HasInterferenceHealth\": \"False\", \"InterferenceHealthRadio0\": 0, \"InterferenceHealthRadio1\": 0, \"InterferenceHealthGhz24\": 0, \"InterferenceHealthGhz50\": 0, \"HasNoiseHealth\": \"False\", \"NoiseHealthRadio1\": 0, \"NoiseHealthGhz50\": 0, \"NoiseHealthRadio0\": 0, \"NoiseHealthGhz24\": 0, \"HasAirQualityHealth\": \"False\", \"AirQualityHealthRadio0\": 0, \"AirQualityHealthRadio1\": 0, \"AirQualityHealthGhz24\": 0, \"AirQualityHealthGhz50\": 0, \"HasUtilization\": \"False\", \"UtilizationRadio0\": 0, \"UtilizationRadio1\": 0, \"UtilizationGhz24\": 0, \"UtilizationGhz50\": 0, \"cisco_catalyst_host\": \"https://dnac.maple.ciscolabs.com\"}"
  },
  {
    "id": "cisco:dnac:issue",
    "label": "Cisco Dnac Issue",
    "vendor": "cisco",
    "category": "Cisco DNAC",
    "index": "netops_logs",
    "sample": "{\"IssueID\": \"72859f90-cafd-4980-a325-431f9ed9dd40\", \"IssueSpecificCategory\": \"Connected\", \"IssueSpecificSource\": \"Cisco DNA\", \"IssueSpecificName\": \"fabric_lisp_session_down_global_trigger\", \"IssueSpecificDescription\": \"LISP session on \\\"LOCAL\\\" Control Plane \\\"Kanata-FB2.ott04-lab.ca\\\" in Fabric site \\\"Global/Kanata_SDA\\\" is down.\", \"IssueSpecificEntity\": \"network_device\", \"IssueSpecificEntityValue\": \"0ea585c1-6b35-48a5-807e-1547cc84976e\", \"IssueSpecificSeverity\": \"HIGH\", \"IssueSpecificPriority\": \"P1\", \"IssueSpecificSummary\": \"LISP session on LOCAL Control Plane ''Kanata-FB2.ott04-lab.ca in Fabric site ''Global/Kanata_SDA'' is down\", \"IssueSpecificTimestamp\": 1784258274901, \"IssueName\": \"LISP session on LOCAL Control Plane ''Kanata-FB2.ott04-lab.ca in Fabric site ''Global/Kanata_SDA'' is down\", \"IssueDeviceRole\": \"\", \"IssueAiDriven\": \"No\", \"IssueClientMac\": \"\", \"IssueCount\": 1, \"IssueStatus\": \"active\", \"IssuePriority\": \"P1\", \"IssueCategory\": \"\", \"DeviceID\": \"0ea585c1-6b35-48a5-807e-1547cc84976e\", \"DeviceName\": \"Kanata-FB2.ott04-lab.ca\", \"DeviceIpAddress\": \"10.201.48.102\", \"DeviceFamily\": \"Switches and Hubs\", \"DeviceMACAddress\": \"70:c9:c6:4c:49:80\", \"DeviceRole\": \"DISTRIBUTION\", \"DeviceImageVersion\": \"17.12.2\", \"DeviceUptime\": \"21 days, 0:27:09.37\", \"DeviceUptimeSeconds\": 1847146, \"DeviceLastUpdated\": \"2026-07-16 18:42:25\", \"DeviceLastUpdateTime\": 1784227345860, \"DeviceSerialNumber\": \"FCW2247F0YN\", \"DeviceSeries\": \"Cisco Catalyst 9500 Series Switches\", \"DevicePlatform\": \"C9500-40X\", \"DeviceSupportType\": \"Supported\", \"cisco_catalyst_host\": \"https://10.20.1.16\"}"
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
    "sample": "{\"id\": \"9056977e-394b-4bb8-9618-d2c6b2a951d0\", \"siteHierarchyId\": \"6f6b2254-2c82-4df2-b4ef-df32aa8db97e/120f464d-4818-42dd-bb74-cc7c005cff7b/b785f984-870f-4487-a163-3c3700221fdc/9056977e-394b-4bb8-9618-d2c6b2a951d0\", \"parentId\": \"b785f984-870f-4487-a163-3c3700221fdc\", \"name\": \"Distribution\", \"nameHierarchy\": \"Global/Toronto/CLUS-26-DMZ1/Distribution\", \"type\": \"floor\", \"floorNumber\": 1, \"rfModel\": \"Cubes And Walled Offices\", \"width\": 100.0, \"length\": 100.0, \"height\": 10.0, \"unitsOfMeasure\": \"feet\", \"cisco_catalyst_host\": \"2026-09-20T14:30:00.000ZHOST2026-09-20T14:30:00.000Z\"}"
  },
  {
    "id": "cisco:duo:account",
    "label": "Cisco Duo Account",
    "vendor": "cisco",
    "category": "Cisco Duo",
    "index": "netops_logs",
    "sample": "{\"ctime\": \"Fri 2026-09-20T14:30:00.000ZSYSLOG_TIMESTAMP2026-09-20T14:30:00.000Z 2026\", \"account_id\": \"DAOSZ4YYK0VOGIA1JIYJ\", \"admin_count\": 5, \"edition\": \"Duo Premier\", \"integration_count\": 14, \"telephony_credits_remaining\": 0, \"user_count\": 68, \"user_pending_deletion_count\": 0, \"timestamp\": 1789752783, \"host\": \"api-dd716ff8.duosecurity.com\", \"extracted_eventtype\": \"account\"}"
  },
  {
    "id": "cisco:duo:activity",
    "label": "Cisco Duo Activity",
    "vendor": "cisco",
    "category": "Cisco Duo",
    "index": "netops_logs",
    "sample": "{\"ctime\": \"Fri 2026-09-20T14:30:00.000ZSYSLOG_TIMESTAMP2026-09-20T14:30:00.000Z 2026\", \"access_device\": null, \"action\": {\"details\": \"{\\\"sync_ref_code\\\": \\\"951940ce7e0bcc4150b1fde70fd0988c\\\", \\\"duration\\\": \\\"0:00:07\\\", \\\"selected_groups\\\": [\\\"cn=lab_owners,ou=maple_groups,dc=maple,dc=ciscolabs,dc=com\\\", \\\"cn=subrosa_users,ou=maple_groups,dc=maple,dc=ciscolabs,dc=com\\\", \\\"cn=maple-vpn-users,ou=maple_groups,dc=maple,dc=ciscolabs,dc=com\\\", \\\"cn=cisco_rdp_dng,ou=maple_groups,dc=maple,dc=ciscolabs,dc=com\\\", \\\"cn=cisco_users,ou=maple_groups,dc=maple,dc=ciscolabs,dc=com\\\"]}\", \"name\": \"ad_sync_finish\"}, \"activity_id\": \"384adfdb-96ab-46c6-9745-b86407048ab7\", \"actor\": {\"details\": \"{\\\"created\\\": null, \\\"last_login\\\": null, \\\"email\\\": null, \\\"status\\\": null, \\\"groups\\\": null, \\\"role\\\": null}\", \"key\": null, \"name\": \"Active Directory User Sync: AD MAPLE\", \"type\": \"ldap_sync\"}, \"akey\": \"DAOSZ4YYK0VOGIA1JIYJ\", \"application\": null, \"old_target\": null, \"outcome\": {\"result\": \"SUCCESS\"}, \"target\": {\"details\": \"{\\\"ldname\\\": \\\"AD MAPLE\\\", \\\"sync_phones\\\": true, \\\"send_enrollment\\\": false, \\\"username_attribute\\\": \\\"samaccountname\\\", \\\"realname_attribute\\\": \\\"displayname\\\", \\\"phone1_attribute\\\": \\\"telephonenumber\\\", \\\"phone2_attribute\\\": \\\"mobile\\\", \\\"email_attribute\\\": \\\"mail\\\", \\\"notes_attribute\\\": null, \\\"directory_type\\\": \\\"activedirectory\\\", \\\"connection\\\": {\\\"ldap_conn_name\\\": null, \\\"ldap_conn_key\\\": null, \\\"base_dn\\\": null, \\\"ntlm_domain\\\": null, \\\"ntlm_workstation\\\": null, \\\"ssl_verify_hostname\\\": null, \\\"used_by_user_syncs\\\": null, \\\"used_by_admin_syncs\\\": null}, \\\"group_change_desc\\\": null, \\\"groups\\\": null, \\\"authproxy_identifiers\\\": null}\", \"key\": \"DS2ACAGGQBNC95H3U4QS\", \"name\": \"AD MAPLE\", \"type\": \"ldap_directory\"}, \"ts\": \"2026-09-20T14:30:00.000ZISO_TIMESTAMP2026-09-20T14:30:00.000Z\", \"timestamp\": 1789752192, \"host\": \"api-dd716ff8.duosecurity.com\", \"extracted_eventtype\": \"activity\"}"
  },
  {
    "id": "cisco:duo:administrator",
    "label": "Cisco Duo Administrator",
    "vendor": "cisco",
    "category": "Cisco Duo",
    "index": "netops_logs",
    "sample": "{\"ctime\": \"Fri 2026-09-20T14:30:00.000ZSYSLOG_TIMESTAMP2026-09-20T14:30:00.000Z 2026\", \"action\": \"ad_sync_finish\", \"description\": \"{\\\"Duration\\\": \\\"0:00:07\\\", \\\"Users added\\\": 0, \\\"Users modified\\\": 0, \\\"Users seen\\\": 67, \\\"Users removed\\\": 0, \\\"authproxy_identifiers\\\": [\\\"PRF2XSHZBNKP9HO38BSN\\\"], \\\"Sync Ref. Code\\\": \\\"951940ce7e0bcc4150b1fde70fd0988c\\\"}\", \"isotimestamp\": \"2026-09-20T14:30:00.000ZISO_TIMESTAMP2026-09-20T14:30:00.000Z\", \"object\": \"AD MAPLE\", \"timestamp\": 1789752192, \"username\": \"Active Directory User Sync: AD MAPLE\", \"host\": \"api-dd716ff8.duosecurity.com\", \"extracted_eventtype\": \"administrator\", \"actionlabel\": \"AD Sync completed\"}"
  },
  {
    "id": "cisco:duo:authentication",
    "label": "Cisco Duo Authentication",
    "vendor": "cisco",
    "category": "Cisco Duo",
    "index": "netops_logs",
    "sample": "{\"timestamp\": 2026-09-20T14:30:00.000Z, \"isotimestamp\": \"2026-09-20T14:30:00.000Z\", \"username\": \"mchowdhury@splunk.com\", \"user\": {\"key\": \"DU19284101\", \"name\": \"mchowdhury@splunk.com\"}, \"factor\": \"Duo Push\", \"result\": \"SUCCESS\", \"reason\": \"User approved\", \"integration\": \"Cisco AnyConnect SSL-VPN\", \"ip\": \"198.51.100.42\", \"location\": {\"city\": \"San Jose\", \"state\": \"California\", \"country\": \"US\"}, \"access_device\": {\"ip\": \"198.51.100.42\", \"location\": {\"city\": \"San Jose\", \"state\": \"California\", \"country\": \"US\"}, \"browser\": \"Safari\", \"browser_version\": \"17.4\", \"os\": \"macOS\", \"os_version\": \"14.4\", \"trusted_endpoint_status\": \"trusted\"}, \"auth_device\": {\"name\": \"iPhone 15 Pro\", \"ip\": \"198.51.100.42\", \"location\": {\"city\": \"San Jose\", \"state\": \"California\", \"country\": \"US\"}}, \"host\": \"api-dd716ff8.duosecurity.com\", \"extracted_eventtype\": \"authentication\"}"
  },
  {
    "id": "cisco:duo:authentication_v2",
    "label": "Cisco Duo Authentication V2",
    "vendor": "cisco",
    "category": "Cisco Duo",
    "index": "netops_logs",
    "sample": "{\"ctime\": \"Fri 2026-09-20T14:30:00.000ZSYSLOG_TIMESTAMP2026-09-20T14:30:00.000Z 2026\", \"access_device\": {\"browser\": null, \"browser_version\": null, \"epkey\": null, \"flash_version\": null, \"hostname\": null, \"ip\": \"0.0.0.0\", \"is_encryption_enabled\": \"unknown\", \"is_firewall_enabled\": \"unknown\", \"is_password_set\": \"unknown\", \"java_version\": null, \"location\": {\"city\": null, \"country\": null, \"state\": null}, \"management_agents\": [], \"os\": null, \"os_version\": null, \"security_agents\": []}, \"adaptive_trust_assessments\": {\"more_secure_auth\": {\"detected_attack_detectors\": null, \"features_version\": \"3.0\", \"model_version\": \"2022.07.19.001\", \"policy_enabled\": false, \"preview_mode_enabled\": true, \"reason\": \"Normal level of trust; no detection of known attack pattern\", \"trust_level\": \"NORMAL\"}, \"remember_me\": {\"features_version\": \"3.0\", \"model_version\": \"2022.07.19.001\", \"policy_enabled\": false, \"reason\": \"Novel Access IP\", \"trust_level\": \"LOW\"}}, \"alias\": \"\", \"application\": {\"key\": \"DI2A8NH4BYXCVZDIA0FQ\", \"name\": \"Auth API\"}, \"auth_device\": {\"ip\": \"99.232.130.106\", \"key\": \"DPQUCMMDM8I0C0KMA8OL\", \"location\": {\"city\": \"Ajax\", \"country\": \"Canada\", \"state\": \"Ontario\"}, \"name\": \"416-571-0674\", \"serial\": null, \"type\": null}, \"email\": \"mahamudc@cisco.com\", \"event_type\": \"authentication\", \"factor\": \"duo_push\", \"isotimestamp\": \"2026-09-20T14:30:00.000ZISO_TIMESTAMP2026-09-20T14:30:00.000Z\", \"ood_software\": null, \"rbfs_triggered_attacks\": null, \"reason\": \"user_approved\", \"result\": \"success\", \"timestamp\": 1789751848, \"trusted_endpoint_status\": \"unknown\", \"txid\": \"bdf8e568-f08a-4b4c-b96f-590480b30d78\", \"user\": {\"groups\": [\"maple-vpn-users (from AD sync \\\"AD MAPLE\\\")\", \"cisco_users (from AD sync \\\"AD MAPLE\\\")\"], \"key\": \"DUZ0V1OUJNM1Y4V7XEPA\", \"name\": \"mahamudc\"}, \"host\": \"api-dd716ff8.duosecurity.com\", \"extracted_eventtype\": \"authentication_v2\"}"
  },
  {
    "id": "cisco:duo:endpoint",
    "label": "Cisco Duo Endpoint",
    "vendor": "cisco",
    "category": "Cisco Duo",
    "index": "netops_logs",
    "sample": "{\"timestamp\":1789914600,\"iso_timestamp\":\"2026-09-20T14:30:00.000Z\",\"event_type\":\"endpoint_health\",\"device\":{\"os\":\"macOS\",\"os_version\":\"15.3.1\",\"model\":\"MacBookPro18,1\",\"encryption\":{\"disk\":\"FileVault_Encrypted\",\"status\":\"HEALTHY\"},\"security_software\":{\"edr\":\"CrowdStrike Falcon 7.14\",\"firewall_active\":true,\"screen_lock_enforced\":true},\"jailbroken\":false},\"user\":\"m.chowdhury@corp.internal\",\"posture_result\":\"COMPLIANT\",\"trusted_endpoint\":true}"
  },
  {
    "id": "cisco:duo:user",
    "label": "Cisco Duo User",
    "vendor": "cisco",
    "category": "Cisco Duo",
    "index": "netops_logs",
    "sample": "{\"ctime\": \"Fri 2026-09-20T14:30:00.000ZSYSLOG_TIMESTAMP2026-09-20T14:30:00.000Z 2026\", \"alias1\": null, \"alias2\": null, \"alias3\": null, \"alias4\": null, \"aliases\": {}, \"created\": 1786110545, \"custom_attributes\": {}, \"date_of_birth\": null, \"desktop_authenticators\": [], \"desktoptokens\": [], \"directory_key\": \"DS2ACAGGQBNC95H3U4QS\", \"email\": \"glarivee@subrosa.ca\", \"enable_auto_prompt\": true, \"entra_federated_user_id\": null, \"external_id\": \"uj9hjKUHJUOVFzqbmf+2Sw==\", \"firstname\": \"\", \"groups\": [{\"desc\": \"\", \"group_id\": \"DGUEDKSHAFCXU8OZPN4N\", \"mobile_otp_enabled\": false, \"name\": \"cisco_rdp_dng (from AD sync \\\"AD MAPLE\\\")\", \"push_enabled\": false, \"sms_enabled\": false, \"status\": \"Active\", \"voice_enabled\": false}, {\"desc\": \"\", \"group_id\": \"DGBGJDR8XC8A9ZXF7XIV\", \"mobile_otp_enabled\": false, \"name\": \"maple-vpn-users (from AD sync \\\"AD MAPLE\\\")\", \"push_enabled\": false, \"sms_enabled\": false, \"status\": \"Active\", \"voice_enabled\": false}, {\"desc\": \"\", \"group_id\": \"DGOHQ8URA3WD7P74K190\", \"mobile_otp_enabled\": false, \"name\": \"subrosa_users (from AD sync \\\"AD MAPLE\\\")\", \"push_enabled\": false, \"sms_enabled\": false, \"status\": \"Active\", \"voice_enabled\": false}], \"has_password\": false, \"is_enrolled\": true, \"last_directory_sync\": 1789750359, \"last_login\": null, \"lastname\": \"\", \"lockout_reason\": null, \"notes\": \"\", \"password_last_updated\": null, \"phones\": [{\"activated\": true, \"app_version\": \"4.120.0\", \"capabilities\": [\"auto\", \"push\", \"mobile_otp\"], \"creation_date\": \"\", \"encrypted\": \"Encrypted\", \"extension\": \"\", \"fingerprint\": \"Configured\", \"last_activated_date\": \"\", \"last_seen\": \"2026-09-20T14:30:00.000ZISO_TIMESTAMP2026-09-20T14:30:00.000Z\", \"model\": \"Samsung SM-S906W\", \"name\": \"\", \"number\": \"+16132863862\", \"os_version\": \"16\", \"phone_id\": \"DPDE7W8M416P6810I0QZ\", \"platform\": \"Google Android\", \"postdelay\": \"\", \"predelay\": \"\", \"quarantined\": false, \"screenlock\": \"Locked\", \"sms_passcodes_sent\": false, \"tampered\": \"Not tampered\", \"type\": \"Mobile\"}], \"realname\": \"Gilles Larivee\", \"status\": \"active\", \"tokens\": [], \"u2ftokens\": [], \"user_id\": \"DUZ0G4XDSFL9O7D5OFSD\", \"username\": \"glarivee\", \"webauthncredentials\": [], \"timestamp\": 1789751322, \"host\": \"api-dd716ff8.duosecurity.com\", \"extracted_eventtype\": \"user\"}"
  },
  {
    "id": "cisco:intersight:advisories",
    "label": "Cisco Intersight Advisories",
    "vendor": "cisco",
    "category": "Cisco Intersight",
    "index": "netops_logs",
    "sample": "{\"AccountMoid\": \"5960901ca94eba000127e33a\", \"Actions\": [{\"AffectedObjectType\": \"equipment.Chassis\", \"AlertType\": \"eolAdvisory\", \"Identifiers\": [{\"Name\": \"Moid\", \"ObjectType\": \"tam.Identifiers\", \"Value\": \"ds1_Moid\"}], \"Name\": \"\", \"ObjectType\": \"tam.Action\", \"OperationType\": \"create\", \"Queries\": [{\"Name\": \"qds2\", \"ObjectType\": \"tam.QueryEntry\", \"Priority\": 1, \"Query\": \"SELECT * FROM ds1 where ( datediff(current_date(), ''2030-02-28'' ) >= -90 and datediff(current_date(), ''2030-02-28'' ) < 0 )\"}], \"Type\": \"restApi\"}], \"AdvisoryDetails\": {\"AllMilestones\": [{\"Date\": \"2026-09-20T14:30:00.000ZISO_TIMESTAMP2026-09-20T14:30:00.000Z\", \"Description\": \"The last date to receive applicable service and support for the product as entitled by active service contracts or by warranty terms and conditions. After this date, all support services for the product are unavailable, and the product becomes obsolete.\", \"EndOffset\": 2147483647, \"LabelHint\": \"upcoming\", \"MilestoneType\": \"unknown\", \"Name\": \"Last Date of (Hardware) Support\", \"ObjectType\": \"tam.Milestone\", \"StartOffset\": 0}], \"Description\": \"\", \"Milestone\": {\"Date\": \"2026-09-20T14:30:00.000ZISO_TIMESTAMP2026-09-20T14:30:00.000Z\", \"Description\": \"The last date to receive applicable service and support for the product as entitled by active service contracts or by warranty terms and conditions. After this date, all support services for the product are unavailable, and the product becomes obsolete.\", \"EndOffset\": 0, \"LabelHint\": \"imminent\", \"MilestoneType\": \"lastDateOfSupport\", \"Name\": \"Last Date Of Support(LDOS) Date\", \"ObjectType\": \"tam.Milestone\", \"StartOffset\": -90}, \"ObjectType\": \"tam.EolAdvisoryDetails\", \"Release\": \"UCSB-5108-HVDC\"}, \"AdvisoryId\": \"ucsb-5108-dc-ldos-medium\", \"Ancestors\": [], \"ApiDataSources\": [{\"MoType\": \"equipmentChassis\", \"Name\": \"ds1\", \"ObjectType\": \"tam.ApiDataSource\", \"Queries\": [{\"Name\": \"qds1\", \"ObjectType\": \"tam.QueryEntry\", \"Priority\": 1, \"Query\": \"SELECT ds1_Moid, ds1_AccountMoid, ds1_DomainGroupMoid, ds1_RegisteredDevice.Moid as ds1_RegisteredDeviceMoid, ds1_Model, ds1_ManagementMode FROM ds1 WHERE ds1_Model RLIKE ''(UCSB-5108-HVDC|UCSB-5108-DC2)''\"}], \"Type\": \"intersightApi\"}], \"CreateTime\": \"2026-09-20T14:30:00.000ZISO_TIMESTAMP2026-09-20T14:30:00.000Z\", \"DatePublished\": \"2026-09-20T14:30:00.000ZISO_TIMESTAMP2026-09-20T14:30:00.000Z\", \"DateUpdated\": \"2026-09-20T14:30:00.000ZISO_TIMESTAMP2026-09-20T14:30:00.000Z\", \"Description\": \"Cisco announced the end-of-sale and end-of-life dates for the Cisco 5108 DC and HVDC Chassis. The last date of (hardware) support for the affected product(s) is February 28, 2030. Customers with active service contracts will continue to receive support from the Cisco Technical Assistance Center (TAC) based on EoL bulletin.\", \"DomainGroupMoid\": \"5b2541877a7662743465cc89\", \"ExecuteOnPod\": \"tier1\", \"ExternalUrl\": \"https://www.cisco.com/c/en/us/products/collateral/servers-unified-computing/ucs-b-series-blade-servers/5108-dc-hvdc-chassis-eol.html\", \"ModTime\": \"2026-09-20T14:30:00.000ZISO_TIMESTAMP2026-09-20T14:30:00.000Z\", \"Moid\": \"68250f936f636b3901fcbc44\", \"Name\": \"Last Date of Support for the Cisco 5108 DC and HVDC Chassis is imminent\", \"ObjectType\": \"tam.AdvisoryDefinition\", \"Organization\": {\"Moid\": \"5dde9f896972652d3353a082\", \"ObjectType\": \"organization.Organization\", \"link\": \"https://intersight.com/api/v1/organization/Organizations/5dde9f896972652d3353a082\"}, \"OtherRefUrls\": [], \"Owners\": [\"5960901ca94eba000127e33a\", \"shared\"], \"PermissionResources\": [{\"Moid\": \"5dde9f896972652d3353a082\", \"ObjectType\": \"organization.Organization\", \"link\": \"https://intersight.com/api/v1/organization/Organizations/5dde9f896972652d3353a082\"}], \"Recommendation\": \"There is no replacement available for the Cisco 5108 DC and HVDC Chassis at this time.\\n\\nCustomers may be able to use the Cisco Technology Migration Program (TMP) where applicable to trade-in eligible products and receive credit toward the purchase of new Cisco equipment. For more information about Cisco TMP, customers should work with their Cisco Partner or Cisco account team. Cisco Partners can find additional TMP information on Partner Central at: [https://www.cisco.com/web/partners/incentives_and_promotions/tmp.html](https://www.cisco.com/web/partners/incentives_and_promotions/tmp.html).\\n\\nCustomers may be able to continue to purchase the Cisco 5108 DC and HVDC Chassis through the Cisco Certified Refurbished Equipment program. Refurbished units may be available in limited supply for sale in certain countries on a first-come, first-served basis until the Last Date of Support has been reached. For information about the Cisco Certified Refurbished Equipment program, go to: [https://www.cisco.com/go/eos](https://www.cisco.com/go/eos).\\n\\nThe Cisco Takeback and Recycle program helps businesses properly dispose of surplus products that have reached their end of useful life. The program is open to all business users of Cisco equipment and its associated brands and subsidiaries. For more information, go to: [https://www.cisco.com/web/about/ac227/ac228/ac231/about_cisco_takeback_recycling.html](https://www.cisco.com/web/about/ac227/ac228/ac231/about_cisco_takeback_recycling.html).\\n\\nFor more information about the Cisco End-of-Life Policy, go to: [https://www.cisco.com/c/en/us/products/eos-eol-policy.html](https://www.cisco.com/c/en/us/products/eos-eol-policy.html).\\n\\nFor more information about the Cisco Product Warranties, go to: [https://www.cisco.com/c/en/us/products/warranty-listing.html](https://www.cisco.com/c/en/us/products/warranty-listing.html).\\n\\nTo subscribe to receive end-of-life/end-of-sale information, go to: [https://cway.cisco.com/mynotifications](https://cway.cisco.com/mynotifications).\", \"S3DataSources\": [], \"Severity\": {\"Level\": \"info\", \"ObjectType\": \"tam.EolSeverity\"}, \"SharedScope\": \"shared\", \"State\": \"ready\", \"Tags\": [], \"Type\": \"eolAdvisory\", \"Version\": \"1.0\", \"Workaround\": \"\", \"account_name\": \"MAPLE\", \"updated_at\": \"2026-09-20T14:30:00.000ZISO_TIMESTAMP2026-09-20T14:30:00.000Z\"}"
  },
  {
    "id": "cisco:intersight:alarms",
    "label": "Cisco Intersight Alarms",
    "vendor": "cisco",
    "category": "Cisco Intersight",
    "index": "netops_logs",
    "sample": "{\"AccountMoid\": \"660de283756461330140b580\", \"Acknowledge\": \"None\", \"AcknowledgeBy\": \"\", \"AcknowledgeTime\": \"2026-09-20T14:30:00.000ZISO_TIMESTAMP2026-09-20T14:30:00.000Z\", \"AffectedMo\": {\"ClassId\": \"mo.MoRef\", \"Moid\": \"68c9a917422d332d416876f6\", \"ObjectType\": \"ether.PhysicalPort\", \"link\": \"https://intersight.com/api/v1/ether/PhysicalPorts/68c9a917422d332d416876f6\"}, \"AffectedMoDisplayName\": \"MAPLE-FI-FAB-3/switch-A/slot-1/ethport-36\", \"AffectedMoId\": \"\", \"AffectedMoType\": \"\", \"AffectedObject\": \"\", \"AlarmSummaryAggregators\": [{\"ClassId\": \"mo.MoRef\", \"Moid\": \"68c9a91576752d3401850f31\", \"ObjectType\": \"network.Element\", \"link\": \"https://intersight.com/api/v1/network/Elements/68c9a91576752d3401850f31\"}], \"AncestorMoId\": \"68c9a91576752d3401850f31\", \"AncestorMoType\": \"network.Element\", \"Ancestors\": [], \"Code\": \"EtherPortLinkDown\", \"CreateTime\": \"2026-09-20T14:30:00.000ZISO_TIMESTAMP2026-09-20T14:30:00.000Z\", \"CreationTime\": \"2026-09-20T14:30:00.000ZISO_TIMESTAMP2026-09-20T14:30:00.000Z\", \"Definition\": {\"ClassId\": \"mo.MoRef\", \"Moid\": \"601cb9466c65722d37c54729\", \"ObjectType\": \"cond.AlarmDefinition\", \"link\": \"https://intersight.com/api/v1/cond/AlarmDefinitions/601cb9466c65722d37c54729\"}, \"Description\": \"Port MAPLE-FI-FAB-3/switch-A/slot-1/ethport-36 is link-down\", \"Flapping\": \"NotFlapping\", \"FlappingCount\": 0, \"FlappingStartTime\": \"2026-09-20T14:30:00.000ZISO_TIMESTAMP2026-09-20T14:30:00.000Z\", \"LastTransitionTime\": \"2026-09-20T14:30:00.000ZISO_TIMESTAMP2026-09-20T14:30:00.000Z\", \"LocationDetails\": null, \"ModTime\": \"2026-09-20T14:30:00.000ZISO_TIMESTAMP2026-09-20T14:30:00.000Z\", \"Moid\": \"6aaabfec65696e34013db1eb\", \"MsAffectedObject\": \"\", \"Name\": \"EtherPortLinkDown\", \"ObjectType\": \"cond.Alarm\", \"OrigSeverity\": \"Warning\", \"Owners\": [\"660de283756461330140b580\", \"68c9a9116f72613501b9a069\"], \"PermissionResources\": [{\"ClassId\": \"mo.MoRef\", \"Moid\": \"660de2876972653301d369bd\", \"ObjectType\": \"organization.Organization\", \"link\": \"https://intersight.com/api/v1/organization/Organizations/660de2876972653301d369bd\"}], \"RegisteredDevice\": {\"ClassId\": \"mo.MoRef\", \"Moid\": \"68c9a9116f72613501b9a069\", \"ObjectType\": \"asset.DeviceRegistration\", \"link\": \"https://intersight.com/api/v1/asset/DeviceRegistrations/68c9a9116f72613501b9a069\"}, \"Severity\": \"Cleared\", \"Suppressed\": false, \"SuppressedTime\": \"2026-09-20T14:30:00.000ZISO_TIMESTAMP2026-09-20T14:30:00.000Z\", \"SuppressionRules\": [], \"Tags\": [{\"Key\": \"cisco.meta.AlarmSource\", \"Propagated\": false, \"SysTag\": true, \"Type\": \"KeyValue\", \"Value\": \"Intersight\"}], \"updated_at\": \"2026-09-20T14:30:00.000ZISO_TIMESTAMP2026-09-20T14:30:00.000Z\", \"account_name\": \"MAPLE\"}"
  },
  {
    "id": "cisco:intersight:auditrecords",
    "label": "Cisco Intersight Auditrecords",
    "vendor": "cisco",
    "category": "Cisco Intersight",
    "index": "netops_logs",
    "sample": "{\"AccountMoid\": \"660de283756461330140b580\", \"AffectedObjectTypeLabel\": \"\", \"CreateTime\": \"2026-09-20T14:30:00.000ZISO_TIMESTAMP2026-09-20T14:30:00.000Z\", \"Email\": \"dieherna@cisco.com\", \"Event\": \"Logout\", \"HttpOperation\": \" \", \"HttpResponseCode\": 0, \"HttpResponsePayload\": \"\", \"InstId\": \"6aab13f175646133016f9e74\", \"MoDisplayNames\": {\"Name\": [\"dieherna@cisco.com\"]}, \"MoType\": \"iam.User\", \"ModTime\": \"2026-09-20T14:30:00.000ZISO_TIMESTAMP2026-09-20T14:30:00.000Z\", \"Moid\": \"6aab13f26972653301d8bc4a\", \"ObjectMoid\": \"6904eb1775646132011532fb\", \"ObjectType\": \"aaa.AuditRecord\", \"Owners\": [\"660de283756461330140b580\"], \"PermissionResources\": [], \"Request\": {}, \"SessionId\": \"6aaaed1d75646133016c3ae4\", \"SourceIp\": \"\", \"Tags\": [], \"Timestamp\": \"2026-09-20T14:30:00.000ZISO_TIMESTAMP2026-09-20T14:30:00.000Z\", \"TraceId\": \"BOpaqDwdwAOnAmLtv3am2LSscZuDxlvKUIr03XoPgds2-LJucFNE3A==\", \"UserAgent\": {\"ClassId\": \"aaa.UserAgent\", \"ObjectType\": \"aaa.UserAgent\", \"OsFamily\": \"\", \"OsVersion\": \"\", \"SoftwareFamily\": \"\", \"SoftwareSubtype\": \"\", \"SoftwareType\": \"\", \"SoftwareVersion\": \"\"}, \"UserAgentString\": \"\", \"UserIdOrEmail\": \"dieherna@cisco.com\", \"updated_at\": \"2026-09-20T14:30:00.000ZISO_TIMESTAMP2026-09-20T14:30:00.000Z\", \"account_name\": \"MAPLE\"}"
  },
  {
    "id": "cisco:intersight:compute",
    "label": "Cisco Intersight Compute",
    "vendor": "cisco",
    "category": "Cisco Intersight",
    "index": "netops_logs",
    "sample": "{\"AccountMoid\": \"660de283756461330140b580\", \"AlarmType\": \"minor\", \"Ancestors\": [{\"Moid\": \"69ea646f76752d340195f1c8\", \"ObjectType\": \"network.Element\", \"link\": \"https://www.intersight.com/api/v1/network/Elements/69ea646f76752d340195f1c8\"}], \"CreateTime\": \"2026-09-20T14:30:00.000ZISO_TIMESTAMP2026-09-20T14:30:00.000Z\", \"DeviceMoId\": \"69ea646e6f7261350123bfde\", \"Dn\": \"switch-FDO2441072E/stor-part-mnt_pss\", \"DomainGroupMoid\": \"660de283756461330140b581\", \"InventoryDeviceInfo\": null, \"ModTime\": \"2026-09-20T14:30:00.000ZISO_TIMESTAMP2026-09-20T14:30:00.000Z\", \"Moid\": \"69ea64717572792d41c44add\", \"Name\": \"mnt_pss\", \"NetworkElement\": {\"Moid\": \"69ea646f76752d340195f1c8\", \"ObjectType\": \"network.Element\", \"link\": \"https://www.intersight.com/api/v1/network/Elements/69ea646f76752d340195f1c8\"}, \"ObjectType\": \"storage.Item\", \"OperState\": \"mounted\", \"Owners\": [\"660de283756461330140b580\", \"69ea646e6f7261350123bfde\"], \"Parent\": {\"Moid\": \"69ea646f76752d340195f1c8\", \"ObjectType\": \"network.Element\", \"link\": \"https://www.intersight.com/api/v1/network/Elements/69ea646f76752d340195f1c8\"}, \"PermissionResources\": [{\"Moid\": \"660de2876972653301d369bd\", \"ObjectType\": \"organization.Organization\", \"link\": \"https://www.intersight.com/api/v1/organization/Organizations/660de2876972653301d369bd\"}], \"RegisteredDevice\": {\"ConnectionStatus\": \"Connected\", \"DeviceHostname\": [\"Mercury\"], \"Moid\": \"69ea646e6f7261350123bfde\", \"ObjectType\": \"asset.DeviceRegistration\"}, \"Rn\": \"\", \"SharedScope\": \"\", \"Size\": \"119\", \"StorageControllerDrive\": null, \"StorageFiles\": [], \"Tags\": [], \"Used\": \"6\", \"UsedVal\": 6, \"account_name\": \"MAPLE\", \"updated_at\": \"2026-09-20T14:30:00.000ZISO_TIMESTAMP2026-09-20T14:30:00.000Z\"}"
  },
  {
    "id": "cisco:intersight:contracts",
    "label": "Cisco Intersight Contracts",
    "vendor": "cisco",
    "category": "Cisco Intersight",
    "index": "netops_logs",
    "sample": "{\"AccountMoid\": \"660de283756461330140b580\", \"ContractStatus\": \"Not Covered\", \"ContractStatusReason\": \"\", \"ContractUnavailableRetryCount\": 1, \"ContractUpdatedTime\": \"2026-09-20T14:30:00.000ZISO_TIMESTAMP2026-09-20T14:30:00.000Z\", \"CoveredProductLineEndDate\": \"2023-10-13\", \"CreateTime\": \"2026-09-20T14:30:00.000ZISO_TIMESTAMP2026-09-20T14:30:00.000Z\", \"DeviceId\": \"WZP263600LU\", \"DeviceType\": \"CiscoUcsServer\", \"DomainGroupMoid\": \"660de283756461330140b581\", \"IsValid\": true, \"ItemType\": \"CHASSIS\", \"LastDateOfSupport\": \"2026-09-20T14:30:00.000ZISO_TIMESTAMP2026-09-20T14:30:00.000Z\", \"MaintenancePurchaseOrderNumber\": \"\", \"MaintenanceSalesOrderNumber\": \"\", \"ModTime\": \"2026-09-20T14:30:00.000ZISO_TIMESTAMP2026-09-20T14:30:00.000Z\", \"Moid\": \"6758d747626572320164d9cf\", \"ObjectType\": \"asset.DeviceContractInformation\", \"Owners\": [\"660de283756461330140b580\", \"6758d7476f72613501ed5d4d\"], \"Parent\": {\"Moid\": \"6758d7bd76752d310168a1c2\", \"ObjectType\": \"compute.RackUnit\", \"link\": \"https://intersight.com/api/v1/compute/RackUnits/6758d7bd76752d310168a1c2\"}, \"PermissionResources\": [{\"Moid\": \"660de2876972653301d369bd\", \"ObjectType\": \"organization.Organization\", \"link\": \"https://intersight.com/api/v1/organization/Organizations/660de2876972653301d369bd\"}], \"PlatformType\": \"IMCRack\", \"PurchaseOrderNumber\": \"SCM-PO-053434\", \"RegisteredDevice\": {\"DeviceHostname\": [\"Galaxy1\"], \"Moid\": \"6758d7476f72613501ed5d4d\", \"ObjectType\": \"asset.DeviceRegistration\"}, \"SalesOrderNumber\": \"114744016\", \"ServiceDescription\": \"\", \"ServiceEndDate\": \"2026-09-20T14:30:00.000ZISO_TIMESTAMP2026-09-20T14:30:00.000Z\", \"ServiceLevel\": \"\", \"ServiceSku\": \"\", \"ServiceStartDate\": \"2026-09-20T14:30:00.000ZISO_TIMESTAMP2026-09-20T14:30:00.000Z\", \"Source\": {\"Moid\": \"6758d7bd76752d310168a1c2\", \"ObjectType\": \"compute.RackUnit\", \"link\": \"https://intersight.com/api/v1/compute/RackUnits/6758d7bd76752d310168a1c2\"}, \"StateContract\": \"OK\", \"Tags\": [], \"WarrantyEndDate\": \"2026-09-20T14:30:00.000ZISO_TIMESTAMP2026-09-20T14:30:00.000Z\", \"WarrantyType\": \"WARR-3YR-HW-90D-SW\", \"account_name\": \"MAPLE\", \"updated_at\": \"2026-09-20T14:30:00.000ZISO_TIMESTAMP2026-09-20T14:30:00.000Z\"}"
  },
  {
    "id": "cisco:intersight:licenses",
    "label": "Cisco Intersight Licenses",
    "vendor": "cisco",
    "category": "Cisco Intersight",
    "index": "netops_logs",
    "sample": "{\"Account\": {\"Moid\": \"660de283756461330140b580\", \"ObjectType\": \"iam.Account\", \"link\": \"https://intersight.com/api/v1/iam/Accounts/660de283756461330140b580\"}, \"AccountId\": \"660de283756461330140b580\", \"AccountMoid\": \"660de283756461330140b580\", \"AuthExpireTime\": \"2026-12-16 19:44:09\", \"AuthInitialTime\": \"2026-09-17 19:49:10\", \"AuthNextTime\": \"2026-09-18 07:49:10\", \"Category\": \"e\", \"CreateTime\": \"2026-09-20T14:30:00.000ZISO_TIMESTAMP2026-09-20T14:30:00.000Z\", \"DefaultLicenseType\": \"Advantage\", \"DefaultLicenseTypeNewerModels\": \"Advantage\", \"DomainGroupMoid\": \"660de283756461330140b581\", \"ErrorDesc\": \"\", \"Group\": \"default\", \"HighestCompliantLicenseTier\": \"Advantage\", \"LastCssmSync\": \"2026-09-20T14:30:00.000ZISO_TIMESTAMP2026-09-20T14:30:00.000Z\", \"LastRenew\": \"2026-09-20T14:30:00.000ZISO_TIMESTAMP2026-09-20T14:30:00.000Z\", \"LastSync\": \"2026-09-20T14:30:00.000ZISO_TIMESTAMP2026-09-20T14:30:00.000Z\", \"LastUpdatedTime\": \"2026-09-20T14:30:00.000ZISO_TIMESTAMP2026-09-20T14:30:00.000Z\", \"LicenseState\": \"\", \"LicenseTechSupportInfo\": \"\", \"ModTime\": \"2026-09-20T14:30:00.000ZISO_TIMESTAMP2026-09-20T14:30:00.000Z\", \"Moid\": \"660de286636f6e3201b04ad4\", \"ObjectType\": \"license.AccountLicenseData\", \"Owners\": [\"660de283756461330140b580\"], \"PermissionResources\": [], \"RegisterExpireTime\": \"2027-09-12 05:38:40\", \"RegisterInitialTime\": \"2024-04-03 23:14:21\", \"RegisterNextTime\": \"1970-01-01 00:00:00\", \"RegistrationStatus\": \"REGISTERED\", \"RenewFailureString\": \"\", \"SharedScope\": \"\", \"SmartAccount\": \"InternalTestDemoAccount1.cisco.com\", \"SmartAccountDomain\": \"internaltestdemoaccount1.cisco.com\", \"SmartApiEnabled\": false, \"SmartApiSyncStatus\": \"FailedToEnable\", \"SyncStatus\": \"UpdateSuccess\", \"Tags\": [{\"Key\": \"MigrateM8BaseToDefault\", \"Propagated\": false, \"SysTag\": false, \"Type\": \"KeyValue\", \"Value\": \"true\"}], \"VirtualAccount\": \"se.ott02OLD\", \"account_name\": \"MAPLE\", \"updated_at\": \"2026-09-20T14:30:00.000ZISO_TIMESTAMP2026-09-20T14:30:00.000Z\"}"
  },
  {
    "id": "cisco:intersight:metrics",
    "label": "Cisco Intersight Metrics",
    "vendor": "cisco",
    "category": "Cisco Intersight",
    "index": "cisco_mdt_metrics",
    "sample": "{\"version\": \"v1\", \"timestamp\": \"2026-09-20T14:30:00.000ZISO_TIMESTAMP2026-09-20T14:30:00.000Z\", \"event\": {\"entdfmx\": null, \"nura\": null, \"nirr\": null, \"nurc\": null, \"nrrmn\": null, \"nirs\": null, \"enlcmx\": null, \"entdfmn\": null, \"nrrmx\": null, \"enrdmx\": null, \"id\": \"/api/v1/fc/PhysicalPorts/69ea64737572792d41c44ae6\", \"enlcmn\": null, \"nprpppsum\": null, \"enrnbr\": null, \"nurmn\": null, \"enrnbs\": null, \"nurmx\": null, \"entjds\": null, \"nrrs\": null, \"nrrr\": null, \"nirmx\": null, \"ntpds\": null, \"ncrcc\": null, \"nprpppmn\": null, \"nutc\": null, \"nitmn\": null, \"nuta\": null, \"nits\": null, \"nprpppmx\": null, \"nitr\": null, \"enlcr\": null, \"hw.network.port.role\": \"unconfigured\", \"enlcs\": null, \"nptppps\": null, \"nitds\": null, \"entjmx\": null, \"nptpppr\": null, \"nitspa\": null, \"ntac\": null, \"host.id\": \"/api/v1/network/Elements/69ea646f76752d340195f1c8\", \"entjmn\": null, \"nptpppsag\": null, \"serial_number\": \"FDO2441072E\", \"nprpppds\": null, \"nprppps\": null, \"model_generation\": \"6400 Series\", \"nprpppr\": null, \"encss\": null, \"entds\": null, \"ntps\": null, \"entdr\": null, \"nurs\": null, \"ntpr\": null, \"encsr\": null, \"nrrds\": null, \"nptpppds\": null, \"enrtlmn\": null, \"enrtlmx\": null, \"nrpmn\": null, \"nitsag\": null, \"nptpppmn\": null, \"nrpmx\": null, \"host.name\": \"Mercury FI-A\", \"nirspa\": null, \"nptpppmx\": null, \"entdmn\": null, \"enrnbds\": null, \"nutmn\": null, \"encsmn\": null, \"enrtsds\": null, \"entjr\": null, \"nuts\": null, \"entdds\": null, \"nprpppsag\": null, \"entjs\": null, \"enrnbmn\": null, \"nitmx\": null, \"nutmx\": null, \"model_family\": \"Fabric Interconnect\", \"encsds\": null, \"nirmn\": null, \"ncrccr\": null, \"ncrccs\": null, \"enrnbmx\": null, \"enrtsmn\": null, \"ntpmn\": null, \"nirsag\": null, \"ntpmx\": null, \"encsmx\": null, \"enrtsmx\": null, \"nrac\": null, \"enrtss\": null, \"enrtsr\": null, \"nirds\": null, \"entdmx\": null, \"enrdmn\": null, \"entdfds\": null, \"enrtlr\": null, \"enrtls\": null, \"nrps\": null, \"enlcds\": null, \"nrpr\": null, \"enrdr\": null, \"enrdds\": null, \"nptpppsum\": null, \"nrpds\": null, \"entdfr\": null, \"enrds\": null, \"entdfs\": null, \"enrtld\": null, \"DomainName\": \"Mercury\", \"AccountMoid\": \"660de283756461330140b580\", \"hwNetworkPortAggregate_port\": 0, \"hwChassis\": null, \"hwChassisNumber\": null, \"hwNetworkState\": \"failed\", \"ParentId\": \"/api/v1/network/Elements/69ea646f76752d340195f1c8\", \"hwNetworkPeerId\": null, \"physical_address\": null, \"hwNetworkPortPort_channel\": \"0\", \"Name\": \"fc1/4\", \"hwNetworkPortNumber\": \"4\", \"hwNetworkPortType\": \"fibre_channel\", \"DomainId\": \"/api/v1/asset/DeviceRegistrations/69ea646e6f7261350123bfde\", \"hwtype\": \"network\", \"hwNetworkPortSlot\": \"1\", \"hwServerId\": null, \"HostName\": \"Mercury FI-A\", \"HostType\": \"network.Element\", \"Model\": \"UCS-FI-6454\", \"assetDrMoid\": \"69ea646e6f7261350123bfde\", \"vendor\": \"Cisco Systems, Inc.\", \"ParentName\": \"Mercury FI-A\", \"host.tags\": []}, \"account_name\": \"MAPLE\"}"
  },
  {
    "id": "cisco:intersight:networkelements",
    "label": "Cisco Intersight Networkelements",
    "vendor": "cisco",
    "category": "Cisco Intersight",
    "index": "netops_logs",
    "sample": "{\"AccountMoid\": \"660de283756461330140b580\", \"AdminEvacState\": \"disabled\", \"AdminInbandInterfaceState\": \"disabled\", \"AlarmSummary\": {\"Critical\": 2, \"Health\": \"Critical\", \"Info\": 0, \"ObjectType\": \"compute.AlarmSummary\", \"Suppressed\": false, \"SuppressedCritical\": 0, \"SuppressedInfo\": 0, \"SuppressedWarning\": 0, \"Warning\": 0}, \"Ancestors\": [], \"AssignedLocation\": null, \"AvailableMemory\": \"\", \"Cards\": [{\"Moid\": \"69ea646e7572792d41c44a8b\", \"ObjectType\": \"equipment.SwitchCard\", \"link\": \"https://www.intersight.com/api/v1/equipment/SwitchCards/69ea646e7572792d41c44a8b\"}], \"CdpEnabled\": false, \"CdpNeighbor\": [], \"Chassis\": \"\", \"ChassisController\": null, \"ConfModTs\": \"\", \"ConfModTsBackup\": \"\", \"ConfigRestoreState\": false, \"ConnectionStatus\": \"Not Supported\", \"Console\": [], \"CreateTime\": \"2026-09-20T14:30:00.000ZISO_TIMESTAMP2026-09-20T14:30:00.000Z\", \"DefaultDomain\": \"\", \"DeviceMoId\": \"69ea646e6f7261350123bfde\", \"Dn\": \"switch-FDO2441072E\", \"Dns\": [], \"DomainGroupMoid\": \"660de283756461330140b581\", \"EquipmentChassis\": null, \"EtherPortChannels\": [], \"EthernetMode\": \"\", \"EthernetSwitchingMode\": \"end-host\", \"Fanmodules\": [{\"Moid\": \"69ea64717572792d41c44a95\", \"ObjectType\": \"equipment.FanModule\", \"link\": \"https://www.intersight.com/api/v1/equipment/FanModules/69ea64717572792d41c44a95\"}, {\"Moid\": \"69ea64717572792d41c44a96\", \"ObjectType\": \"equipment.FanModule\", \"link\": \"https://www.intersight.com/api/v1/equipment/FanModules/69ea64717572792d41c44a96\"}, {\"Moid\": \"69ea64717572792d41c44a97\", \"ObjectType\": \"equipment.FanModule\", \"link\": \"https://www.intersight.com/api/v1/equipment/FanModules/69ea64717572792d41c44a97\"}, {\"Moid\": \"69ea64717572792d41c44a98\", \"ObjectType\": \"equipment.FanModule\", \"link\": \"https://www.intersight.com/api/v1/equipment/FanModules/69ea64717572792d41c44a98\"}], \"FaultSummary\": 0, \"FcMode\": \"\", \"FcPortChannels\": [], \"FcSwitchingMode\": \"switch\", \"FeatureControl\": [], \"FpgaUpgradeNeeded\": true, \"InbandIpAddress\": \"0.0.0.0\", \"InbandIpGateway\": \"0.0.0.0\", \"InbandIpMask\": \"255.255.255.0\", \"InbandIpv6Address\": \"\", \"InbandIpv6Gateway\": \"\", \"InbandIpv6Prefix\": \"\", \"InbandMac\": \"\", \"InbandVlan\": 0, \"InterClusterLinkState\": \"Up\", \"InterfaceList\": [], \"InventoryDeviceInfo\": null, \"IsUpgraded\": false, \"JumboFrameEnabled\": true, \"LicenseFile\": [], \"LldpEnabled\": false, \"LldpNeighbor\": [{\"Moid\": \"6aa98a8c76752d3401a646ce\", \"ObjectType\": \"network.DiscoveredNeighbor\", \"link\": \"https://www.intersight.com/api/v1/network/DiscoveredNeighbors/6aa98a8c76752d3401a646ce\"}, {\"Moid\": \"6aa9926e76752d3401b37f13\", \"ObjectType\": \"network.DiscoveredNeighbor\", \"link\": \"https://www.intersight.com/api/v1/network/DiscoveredNeighbors/6aa9926e76752d3401b37f13\"}], \"LocationDetails\": null, \"LocatorLed\": {\"Moid\": \"69ea646f76752d340195f1ce\", \"ObjectType\": \"equipment.LocatorLed\", \"link\": \"https://www.intersight.com/api/v1/equipment/LocatorLeds/69ea646f76752d340195f1ce\"}, \"ManagementController\": {\"Moid\": \"69ea647176752d340195f7ee\", \"ObjectType\": \"management.Controller\", \"link\": \"https://www.intersight.com/api/v1/management/Controllers/69ea647176752d340195f7ee\"}, \"ManagementEntity\": null, \"ManagementMode\": \"Intersight\", \"ModTime\": \"2026-09-20T14:30:00.000ZISO_TIMESTAMP2026-09-20T14:30:00.000Z\", \"Model\": \"UCS-FI-6454\", \"Moid\": \"69ea646f76752d340195f1c8\", \"NetworkFcZoneInfo\": null, \"NetworkVlanPortInfo\": {\"Moid\": \"69ea79ac76752d3401b627e1\", \"ObjectType\": \"network.VlanPortInfo\", \"link\": \"https://www.intersight.com/api/v1/network/VlanPortInfos/69ea79ac76752d3401b627e1\"}, \"NtpServer\": [], \"ObjectType\": \"network.Element\", \"OperEvacState\": \"disabled\", \"Operability\": \"online\", \"OutOfBandIpAddress\": \"10.0.255.4\", \"OutOfBandIpGateway\": \"10.0.255.1\", \"OutOfBandIpMask\": \"255.255.255.0\", \"OutOfBandIpv4Address\": \"10.0.255.4\", \"OutOfBandIpv4Gateway\": \"10.0.255.1\", \"OutOfBandIpv4Mask\": \"255.255.255.0\", \"OutOfBandIpv6Address\": \"\", \"OutOfBandIpv6Error\": \"\", \"OutOfBandIpv6Gateway\": \"\", \"OutOfBandIpv6Mode\": \"\", \"OutOfBandIpv6Prefix\": \"\", \"OutOfBandIpv6Redirects\": \"\", \"OutOfBandIpv6SlaacIidMode\": \"\", \"OutOfBandIpv6Status\": \"\", \"OutOfBandMac\": \"00:3A:9C:DA:2D:C0\", \"Owners\": [\"660de283756461330140b580\", \"69ea646e6f7261350123bfde\"], \"Parent\": null, \"PartNumber\": \"\", \"PeerFirmwareOutOfSync\": false, \"PermissionResources\": [{\"Moid\": \"660de2876972653301d369bd\", \"ObjectType\": \"organization.Organization\", \"link\": \"https://www.intersight.com/api/v1/organization/Organizations/660de2876972653301d369bd\"}], \"PortMacBindings\": [], \"Presence\": \"\", \"PreviousFru\": null, \"ProcessorUnit\": [], \"Psus\": [{\"Moid\": \"69ea64737572792d41c44ae7\", \"ObjectType\": \"equipment.Psu\", \"link\": \"https://www.intersight.com/api/v1/equipment/Psus/69ea64737572792d41c44ae7\"}, {\"Moid\": \"69ea64737572792d41c44ae8\", \"ObjectType\": \"equipment.Psu\", \"link\": \"https://www.intersight.com/api/v1/equipment/Psus/69ea64737572792d41c44ae8\"}], \"RegisteredDevice\": {\"ConnectionStatus\": \"Connected\", \"DeviceHostname\": [\"Mercury\"], \"Moid\": \"69ea646e6f7261350123bfde\", \"ObjectType\": \"asset.DeviceRegistration\"}, \"ReservedVlanStartId\": 3915, \"Revision\": \"0\", \"Rn\": \"\", \"RouterMac\": \"00:3a:9c:da:2d:c7\", \"SecureRouterInfo\": null, \"Sensors\": [], \"Serial\": \"FDO2441072E\", \"SharedScope\": \"\", \"SlotId\": 0, \"Status\": \"\", \"StorageItems\": [{\"Moid\": \"69ea64717572792d41c44ad5\", \"ObjectType\": \"storage.Item\", \"link\": \"https://www.intersight.com/api/v1/storage/Items/69ea64717572792d41c44ad5\"}, {\"Moid\": \"69ea64717572792d41c44ad6\", \"ObjectType\": \"storage.Item\", \"link\": \"https://www.intersight.com/api/v1/storage/Items/69ea64717572792d41c44ad6\"}, {\"Moid\": \"69ea64717572792d41c44ad7\", \"ObjectType\": \"storage.Item\", \"link\": \"https://www.intersight.com/api/v1/storage/Items/69ea64717572792d41c44ad7\"}, {\"Moid\": \"69ea64717572792d41c44ad8\", \"ObjectType\": \"storage.Item\", \"link\": \"https://www.intersight.com/api/v1/storage/Items/69ea64717572792d41c44ad8\"}, {\"Moid\": \"69ea64717572792d41c44ad9\", \"ObjectType\": \"storage.Item\", \"link\": \"https://www.intersight.com/api/v1/storage/Items/69ea64717572792d41c44ad9\"}, {\"Moid\": \"69ea64717572792d41c44ada\", \"ObjectType\": \"storage.Item\", \"link\": \"https://www.intersight.com/api/v1/storage/Items/69ea64717572792d41c44ada\"}, {\"Moid\": \"69ea64717572792d41c44adb\", \"ObjectType\": \"storage.Item\", \"link\": \"https://www.intersight.com/api/v1/storage/Items/69ea64717572792d41c44adb\"}, {\"Moid\": \"69ea64717572792d41c44adc\", \"ObjectType\": \"storage.Item\", \"link\": \"https://www.intersight.com/api/v1/storage/Items/69ea64717572792d41c44adc\"}, {\"Moid\": \"69ea64717572792d41c44add\", \"ObjectType\": \"storage.Item\", \"link\": \"https://www.intersight.com/api/v1/storage/Items/69ea64717572792d41c44add\"}], \"StpMode\": \"Disabled\", \"SupervisorCard\": [], \"SwitchId\": \"A\", \"SwitchProfileName\": \"Mercury-A\", \"SwitchType\": \"FabricInterconnect\", \"SwitchWwn\": \"20:00:00:3a:9c:da:2d:c0\", \"SystemUpTime\": \"\", \"Tags\": [], \"Thermal\": \"ok\", \"TopSystem\": null, \"TotalMemory\": 64265, \"UcsmRunningFirmware\": {\"Moid\": \"69ea64717572792d41c44ad4\", \"ObjectType\": \"firmware.RunningFirmware\", \"link\": \"https://www.intersight.com/api/v1/firmware/RunningFirmwares/69ea64717572792d41c44ad4\"}, \"UserLabel\": \"\", \"Vendor\": \"Cisco Systems, Inc.\", \"Version\": \"\", \"Veths\": [{\"Moid\": \"69ea647476752d340195fcdc\", \"ObjectType\": \"network.Vethernet\", \"link\": \"https://www.intersight.com/api/v1/network/Vethernets/69ea647476752d340195fcdc\"}], \"Vfcs\": [{\"Moid\": \"69ea647476752d340195fcfa\", \"ObjectType\": \"network.Vfc\", \"link\": \"https://www.intersight.com/api/v1/network/Vfcs/69ea647476752d340195fcfa\"}], \"VpcDomain\": null, \"VpcMember\": [], \"VpcPeer\": [], \"Vrf\": [], \"account_name\": \"MAPLE\", \"updated_at\": \"2026-09-20T14:30:00.000ZISO_TIMESTAMP2026-09-20T14:30:00.000Z\"}"
  },
  {
    "id": "cisco:intersight:networkobjects",
    "label": "Cisco Intersight Networkobjects",
    "vendor": "cisco",
    "category": "Cisco Intersight",
    "index": "netops_logs",
    "sample": "{\"AccessVlan\": \"\", \"AccountMoid\": \"660de283756461330140b580\", \"AcknowledgedPeerInterface\": null, \"AdminFec\": \"\", \"AdminSpeed\": \"\", \"AdminState\": \"Disabled\", \"AggregatePortId\": 0, \"AllowedVlans\": \"\", \"Ancestors\": [{\"Moid\": \"68c9a91876752d340185118d\", \"ObjectType\": \"port.Group\", \"link\": \"https://intersight.com/api/v1/port/Groups/68c9a91876752d340185118d\"}, {\"Moid\": \"68c9a915422d332d421b8ff6\", \"ObjectType\": \"equipment.SwitchCard\", \"link\": \"https://intersight.com/api/v1/equipment/SwitchCards/68c9a915422d332d421b8ff6\"}, {\"Moid\": \"68c9a91576752d3401850f0f\", \"ObjectType\": \"network.Element\", \"link\": \"https://intersight.com/api/v1/network/Elements/68c9a91576752d3401850f0f\"}], \"CreateTime\": \"2026-09-20T14:30:00.000ZISO_TIMESTAMP2026-09-20T14:30:00.000Z\", \"DeviceMoId\": \"68c9a9116f72613501b9a069\", \"Dn\": \"switch-FDO26140CQK/slot-1/switch-ether/port-10\", \"DomainGroupMoid\": \"660de283756461330140b581\", \"InventoryDeviceInfo\": null, \"LicenseGrace\": \"\", \"LicenseState\": \"\", \"MacAddress\": \"00:08:31:10:E2:51\", \"MacsecOperData\": {\"AuthMode\": \"\", \"CipherSuite\": \"\", \"ConfidentialityOffset\": \"\", \"KeyServer\": \"\", \"ObjectType\": \"ether.MacsecOperData\", \"SessionState\": \"\", \"StateReason\": \"\"}, \"ModTime\": \"2026-09-20T14:30:00.000ZISO_TIMESTAMP2026-09-20T14:30:00.000Z\", \"Mode\": \"access\", \"Moid\": \"699f1b4376752d34017c6bad\", \"Name\": \"\", \"NativeVlan\": \"\", \"ObjectType\": \"ether.PhysicalPort\", \"OperFec\": \"\", \"OperSpeed\": \"auto\", \"OperState\": \"down\", \"OperStateQual\": \"xcvr-absent\", \"OperVlans\": \"\", \"Owners\": [\"660de283756461330140b580\", \"68c9a9116f72613501b9a069\"], \"Parent\": {\"Dn\": \"switch-FDO26140CQK/slot-1/switch-ether\", \"Moid\": \"68c9a91876752d340185118d\", \"ObjectType\": \"port.Group\"}, \"PeerDn\": \"\", \"PeerInterface\": null, \"PermissionResources\": [{\"Moid\": \"660de2876972653301d369bd\", \"ObjectType\": \"organization.Organization\", \"link\": \"https://intersight.com/api/v1/organization/Organizations/660de2876972653301d369bd\"}], \"PortChannelId\": 0, \"PortGroup\": {\"Moid\": \"68c9a91876752d340185118d\", \"ObjectType\": \"port.Group\", \"link\": \"https://intersight.com/api/v1/port/Groups/68c9a91876752d340185118d\"}, \"PortId\": 10, \"PortName\": \"\", \"PortSubGroup\": null, \"PortType\": \"\", \"RegisteredDevice\": {\"Moid\": \"68c9a9116f72613501b9a069\", \"ObjectType\": \"asset.DeviceRegistration\", \"link\": \"https://intersight.com/api/v1/asset/DeviceRegistrations/68c9a9116f72613501b9a069\"}, \"Rn\": \"\", \"Role\": \"unknown\", \"SharedScope\": \"\", \"SlotId\": 1, \"SwitchId\": \"B\", \"Tags\": [], \"TransceiverType\": \"unknown\", \"UserLabel\": \"\", \"account_name\": \"MAPLE\", \"updated_at\": \"2026-09-20T14:30:00.000ZISO_TIMESTAMP2026-09-20T14:30:00.000Z\"}"
  },
  {
    "id": "cisco:intersight:profiles",
    "label": "Cisco Intersight Profiles",
    "vendor": "cisco",
    "category": "Cisco Intersight",
    "index": "netops_logs",
    "sample": "{\"AccountMoid\": \"660de283756461330140b580\", \"Action\": \"No-op\", \"ActionParams\": [], \"Ancestors\": [], \"AssignedServer\": {\"Moid\": \"68c9aa8676752d340186a914\", \"Name\": \"MAPLE-FI-FAB-3-1-1\", \"ObjectType\": \"compute.Blade\"}, \"AssociatedServer\": {\"Moid\": \"68c9aa8676752d340186a914\", \"ObjectType\": \"compute.Blade\", \"link\": \"https://intersight.com/api/v1/compute/Blades/68c9aa8676752d340186a914\"}, \"ConfigChangeContext\": {\"ConfigChangeError\": \"\", \"ConfigChangeState\": \"Ok\", \"InitialConfigContext\": {\"ConfigState\": \"Associated\", \"ConfigStateSummary\": \"Associated\", \"ConfigType\": \"\", \"ControlAction\": \"No-op\", \"ErrorState\": \"\", \"InconsistencyReason\": [], \"ObjectType\": \"policy.ConfigContext\", \"OperState\": \"Ok\"}, \"ObjectType\": \"policy.ConfigChangeContext\"}, \"ConfigChangeDetails\": [], \"ConfigChanges\": {\"Changes\": [], \"Disruptions\": [], \"ObjectType\": \"policy.ConfigChange\", \"PolicyDisruptions\": []}, \"ConfigContext\": {\"ConfigState\": \"Associated\", \"ConfigStateSummary\": \"Associated\", \"ConfigType\": \"\", \"ControlAction\": \"No-op\", \"ErrorState\": \"\", \"InconsistencyReason\": [], \"ObjectType\": \"policy.ConfigContext\", \"OperState\": \"Ok\"}, \"ConfigResult\": {\"Moid\": \"68d5164a77696e33011804be\", \"ObjectType\": \"server.ConfigResult\", \"link\": \"https://intersight.com/api/v1/server/ConfigResults/68d5164a77696e33011804be\"}, \"CreateTime\": \"2026-09-20T14:30:00.000ZISO_TIMESTAMP2026-09-20T14:30:00.000Z\", \"DeployStatus\": \"Complete\", \"DeployedPolicies\": [\"vnic.LanConnectivityPolicy\", \"server.Profile\", \"kvm.Policy\", \"iam.EndPointUserPolicy\", \"snmp.Policy\", \"syslog.Policy\", \"bios.Policy\", \"vmedia.Policy\", \"boot.PrecisionPolicy\", \"storage.StoragePolicy\", \"firmware.Policy\", \"access.Policy\", \"vnic.SanConnectivityPolicy\", \"certificatemanagement.Policy\"], \"DeployedSwitches\": \"AB\", \"Description\": \"\", \"DomainGroupMoid\": \"660de283756461330140b581\", \"IncompletePolicies\": [], \"InitialAutoDeployConfigComplete\": false, \"InitialAutoDeployMode\": false, \"InitialAutoDeployState\": \"None\", \"InternalReservationReferences\": [], \"IsPmcDeployedSecurePassphraseSet\": false, \"LocationDetails\": null, \"ManagementMode\": \"Intersight\", \"ModTime\": \"2026-09-20T14:30:00.000ZISO_TIMESTAMP2026-09-20T14:30:00.000Z\", \"Moid\": \"68d5164a77696e33011804a8\", \"Name\": \"MAPLE-VXLAN-ESXI-3-1-1\", \"ObjectType\": \"server.Profile\", \"Organization\": {\"Moid\": \"660de2876972653301d369bd\", \"ObjectType\": \"organization.Organization\", \"link\": \"https://intersight.com/api/v1/organization/Organizations/660de2876972653301d369bd\"}, \"OverriddenList\": [], \"Owners\": [\"660de283756461330140b580\"], \"PartiallyDeployedPolicies\": [], \"PermissionResources\": [{\"Moid\": \"660de2876972653301d369bd\", \"ObjectType\": \"organization.Organization\", \"link\": \"https://intersight.com/api/v1/organization/Organizations/660de2876972653301d369bd\"}], \"PolicyBucket\": [{\"Moid\": \"68ac89596275723101707e54\", \"Name\": \"MAPLE-ESXI-LOCAL_USER\", \"ObjectType\": \"iam.EndPointUserPolicy\"}, {\"Moid\": \"68a22bb66275723101c7e751\", \"Name\": \"MAPLE-SNMP\", \"ObjectType\": \"snmp.Policy\"}, {\"Moid\": \"68ac89996275723101709f66\", \"Name\": \"MAPLE-SPLUNK-HF\", \"ObjectType\": \"syslog.Policy\"}, {\"Moid\": \"68ac89c8627572310170be87\", \"Name\": \"MAPLE-ACI-vKVM\", \"ObjectType\": \"kvm.Policy\"}, {\"Moid\": \"68ae40796275723101833b4e\", \"Name\": \"MAPLE-BOOT-OPTIONS\", \"ObjectType\": \"boot.PrecisionPolicy\"}, {\"Moid\": \"68ae0ebf6275723101649e6e\", \"Name\": \"MAPLE-vMEDIA_ENABLED\", \"ObjectType\": \"vmedia.Policy\"}, {\"Moid\": \"68ac9822656f6e310138d099\", \"Name\": \"MAPLE-M2_RAID1\", \"ObjectType\": \"storage.StoragePolicy\"}, {\"Moid\": \"66298f0e6275723101482d2b\", \"Name\": \"vmware-esxi-m6\", \"ObjectType\": \"bios.Policy\"}, {\"InbandIpPool\": null, \"Moid\": \"68d5782d6275723101dbc2a7\", \"Name\": \"MAPLE-VXLAN-ESXI-CIMC-OOB\", \"ObjectType\": \"access.Policy\", \"OutOfBandIpPool\": {\"Moid\": \"68ae0baa69627532013f86e2\", \"ObjectType\": \"ippool.Pool\", \"link\": \"https://intersight.com/api/v1/ippool/Pools/68ae0baa69627532013f86e2\"}}, {\"Moid\": \"662bc3ac0c89d7c6010f8412\", \"Name\": \"maple-fc\", \"ObjectType\": \"vnic.SanConnectivityPolicy\", \"WwnnPool\": {\"Moid\": \"66298f0e69627532015ecdb3\", \"ObjectType\": \"fcpool.Pool\", \"link\": \"https://intersight.com/api/v1/fcpool/Pools/66298f0e69627532015ecdb3\"}}, {\"IqnPool\": null, \"Moid\": \"6aaacdf2e4c3fe6101d59ae4\", \"Name\": \"MAPLE-VXLAN-OCP-LAN_CONN_POL\", \"ObjectType\": \"vnic.LanConnectivityPolicy\"}], \"PolicyChangeDetails\": [], \"PostDeployAction\": [\"None\"], \"RemovedPolicies\": [], \"ReportedPolicyChanges\": [{\"ChangeId\": \"d8296b42ca650c14-1772033559\", \"ChangeStatus\": \"Reported\", \"ObjectType\": \"policy.ReportedPolicyChange\", \"PolicyType\": \"syslog.Policy\"}, {\"ChangeId\": \"2e160b5edbceb76b-1774580414\", \"ChangeStatus\": \"Reported\", \"ObjectType\": \"policy.ReportedPolicyChange\", \"PolicyType\": \"vnic.SanConnectivityPolicy\"}, {\"ChangeId\": \"55911fd4ddc7fe82-1781721826\", \"ChangeStatus\": \"Reported\", \"ObjectType\": \"policy.ReportedPolicyChange\", \"PolicyType\": \"snmp.Policy\"}, {\"ChangeId\": \"5d5aa76d71595a1b-1789580283\", \"ChangeStatus\": \"Reported\", \"ObjectType\": \"policy.ReportedPolicyChange\", \"PolicyType\": \"vnic.LanConnectivityPolicy\"}], \"ReservationReferences\": [], \"ResourceLease\": {\"Moid\": \"6a0dddf7696275320125e720\", \"ObjectType\": \"resourcepool.Lease\", \"link\": \"https://intersight.com/api/v1/resourcepool/Leases/6a0dddf7696275320125e720\"}, \"RunningWorkflows\": [], \"ScheduledActions\": [], \"ScheduledServerAssignment\": null, \"ServerAssignmentMode\": \"Static\", \"ServerFamily\": \"All\", \"ServerPool\": null, \"ServerPreAssignBySerial\": \"\", \"ServerPreAssignBySlot\": {\"ChassisId\": 0, \"DomainName\": \"\", \"ObjectType\": \"server.ServerAssignTypeSlot\", \"SlotId\": 0}, \"ServerReservation\": {\"ObjectType\": \"resourcepool.ReservationReference\", \"PoolMoid\": \"\", \"ReservationId\": \"\", \"ReservationMoid\": \"\", \"ResourceSerial\": \"\", \"ResourceType\": \"\"}, \"SharedScope\": \"\", \"SrcTemplate\": null, \"StaticUuidAddress\": \"\", \"Tags\": [], \"TargetPlatform\": \"FIAttached\", \"TemplateActions\": [], \"TemplateSyncErrors\": [], \"TemplateSyncStatus\": \"None\", \"Type\": \"instance\", \"UndeployWfTasks\": [], \"UserLabel\": \"\", \"Uuid\": \"AAAAAAAA-AAAA-AAAA-AAAA-000000000002\", \"UuidAddressType\": \"POOL\", \"UuidLease\": {\"Moid\": \"6aaad42d69627532013ba33b\", \"ObjectType\": \"uuidpool.UuidLease\", \"link\": \"https://intersight.com/api/v1/uuidpool/UuidLeases/6aaad42d69627532013ba33b\"}, \"UuidPool\": {\"Moid\": \"68ac865669627532013eb82e\", \"ObjectType\": \"uuidpool.Pool\", \"link\": \"https://intersight.com/api/v1/uuidpool/Pools/68ac865669627532013eb82e\"}, \"account_name\": \"MAPLE\", \"updated_at\": \"2026-09-20T14:30:00.000ZISO_TIMESTAMP2026-09-20T14:30:00.000Z\"}"
  },
  {
    "id": "cisco:intersight:targets",
    "label": "Cisco Intersight Targets",
    "vendor": "cisco",
    "category": "Cisco Intersight",
    "index": "netops_logs",
    "sample": "{\"AccountMoid\": \"660de283756461330140b580\", \"AlarmSummary\": {\"Critical\": 0, \"Health\": \"Healthy\", \"Info\": 0, \"ObjectType\": \"asset.AlarmSummary\", \"SuppressedCritical\": 0, \"SuppressedInfo\": 0, \"SuppressedWarning\": 0, \"Warning\": 0}, \"AssignedLocation\": null, \"Assist\": null, \"ClaimedByUserName\": \"tiagosil@cisco.com\", \"ClaimedTime\": \"2026-09-20T14:30:00.000ZISO_TIMESTAMP2026-09-20T14:30:00.000Z\", \"ConnectorVersion\": \"1.0.11-20260615170508583\", \"CreateTime\": \"2026-09-20T14:30:00.000ZISO_TIMESTAMP2026-09-20T14:30:00.000Z\", \"CustomPermissionResources\": [{\"Moid\": \"660de2876972653301d369bd\", \"ObjectType\": \"organization.Organization\", \"link\": \"https://intersight.com/api/v1/organization/Organizations/660de2876972653301d369bd\"}], \"ExternalIpAddress\": \"64.100.57.80\", \"IpAddress\": [\"fd0a:9b09:1f7:8080:e64e:2dff:fe55:a6d0\", \"10.0.255.72\"], \"ManagementLocation\": \"DeviceConnector\", \"ModTime\": \"2026-09-20T14:30:00.000ZISO_TIMESTAMP2026-09-20T14:30:00.000Z\", \"Moid\": \"6a2c11056f726135012187e6\", \"Name\": \"DNAC-MAPLE-CIMC\", \"ObjectType\": \"asset.Target\", \"Owners\": [\"660de283756461330140b580\"], \"PermissionResources\": [{\"Moid\": \"660de2876972653301d369bd\", \"ObjectType\": \"organization.Organization\", \"link\": \"https://intersight.com/api/v1/organization/Organizations/660de2876972653301d369bd\"}], \"ProductId\": [\"DN2-HW-APL-U\"], \"ReadOnly\": false, \"RegisteredDevice\": {\"ConnectionStatus\": \"Connected\", \"Moid\": \"6a2c11056f726135012187e2\", \"ObjectType\": \"asset.DeviceRegistration\"}, \"Reservation\": null, \"Services\": [], \"Status\": \"Connected\", \"StatusErrorReason\": \"\", \"Tags\": [], \"TargetId\": [\"WMP254600GS\"], \"TargetType\": \"IMCM5\", \"TrustPoint\": null, \"Vendor\": \"Cisco Systems, Inc.\", \"WorkflowInfo\": null, \"account_name\": \"MAPLE\", \"updated_at\": \"2026-09-20T14:30:00.000ZISO_TIMESTAMP2026-09-20T14:30:00.000Z\"}"
  },
  {
    "id": "cisco:sdwan:AAA-6-METHOD_LIST_STATE",
    "label": "Cisco Sdwan Aaa 6 Method List State",
    "vendor": "cisco",
    "category": "Cisco SD-WAN",
    "index": "netops_logs",
    "sample": "2026-09-20T14:30:00.000ZTS2026-09-20T14:30:00.000Z 10.201.48.116 175: *2026-09-20T14:30:00.000ZTS2026-09-20T14:30:00.000Z:  %AAA-6-METHOD_LIST_STATE: authen mlist  pvt_authen_0 of DOT1X service is marked for notifyingstate and its current state is : DEAD"
  },
  {
    "id": "cisco:sdwan:AAA-6-NOTIFY_MLIST_STATE_TO_AAA_CLIENT",
    "label": "Cisco Sdwan Aaa 6 Notify Mlist State To Aaa Client",
    "vendor": "cisco",
    "category": "Cisco SD-WAN",
    "index": "netops_logs",
    "sample": "2026-09-20T14:30:00.000ZTS2026-09-20T14:30:00.000Z 10.201.48.116 179: *2026-09-20T14:30:00.000ZTS2026-09-20T14:30:00.000Z:  %AAA-6-NOTIFY_MLIST_STATE_TO_AAA_CLIENT: Notifying state of authentication method list  pvt_authen_0 of DOT1X service as DEAD"
  },
  {
    "id": "cisco:sdwan:AAA_AUDIT_MESSAGE-6-METHOD_LIST_STATE",
    "label": "Cisco Sdwan Aaa Audit Message 6 Method List State",
    "vendor": "cisco",
    "category": "Cisco SD-WAN",
    "index": "netops_logs",
    "sample": "2026-09-20T14:30:00.000ZTS2026-09-20T14:30:00.000Z 10.201.48.116 172: *2026-09-20T14:30:00.000ZTS2026-09-20T14:30:00.000Z:  %AAA_AUDIT_MESSAGE-6-METHOD_LIST_STATE: Switch 1 R0/0: sessmgrd: mlist default of 8021X service is marked for notifying  state and its current state is : ALIVE"
  },
  {
    "id": "cisco:sdwan:AAA_AUDIT_MESSAGE-6-NOTIFY_MLIST_STATE_TO_AAA_CLIENT",
    "label": "Cisco Sdwan Aaa Audit Message 6 Notify Mlist State To Aaa Client",
    "vendor": "cisco",
    "category": "Cisco SD-WAN",
    "index": "netops_logs",
    "sample": "2026-09-20T14:30:00.000ZTS2026-09-20T14:30:00.000Z 10.201.48.116 171: *2026-09-20T14:30:00.000ZTS2026-09-20T14:30:00.000Z:  %AAA_AUDIT_MESSAGE-6-NOTIFY_MLIST_STATE_TO_AAA_CLIENT: Switch 1 R0/0: sessmgrd: Notifying state of authentication method list default of 8021X service as ALIVE"
  },
  {
    "id": "cisco:sdwan:BGP-5-NBR_RESET",
    "label": "Cisco Sdwan Bgp 5 Nbr Reset",
    "vendor": "cisco",
    "category": "Cisco SD-WAN",
    "index": "netops_logs",
    "sample": "2026-09-20T14:30:00.000ZTS2026-09-20T14:30:00.000Z 10.201.48.121 3712: *2026-09-20T14:30:00.000ZTS2026-09-20T14:30:00.000Z:  %BGP-5-NBR_RESET: Neighbor 10.201.130.61 passive reset (Peer closed the session)"
  },
  {
    "id": "cisco:sdwan:BGP-6-NEXTHOP",
    "label": "Cisco Sdwan Bgp 6 Nexthop",
    "vendor": "cisco",
    "category": "Cisco SD-WAN",
    "index": "netops_logs",
    "sample": "2026-09-20T14:30:00.000ZTS2026-09-20T14:30:00.000Z 10.201.48.118 3181: *2026-09-20T14:30:00.000ZTS2026-09-20T14:30:00.000Z:  %BGP-6-NEXTHOP: Invalid next hop (0.0.0.0) received from 10.201.48.114: martian next hop"
  },
  {
    "id": "cisco:sdwan:BGP_SESSION-5-ADJCHANGE",
    "label": "Cisco Sdwan Bgp Session 5 Adjchange",
    "vendor": "cisco",
    "category": "Cisco SD-WAN",
    "index": "netops_logs",
    "sample": "2026-09-20T14:30:00.000ZTS2026-09-20T14:30:00.000Z 10.201.48.120 3263: *2026-09-20T14:30:00.000ZTS2026-09-20T14:30:00.000Z:  %BGP_SESSION-5-ADJCHANGE: neighbor 10.201.152.1 IPv4 Unicast vpn vrf UBC_TENANT topology base removed from session  Neighbor deleted"
  },
  {
    "id": "cisco:sdwan:CDP-4-NATIVE_VLAN_MISMATCH",
    "label": "Cisco Sdwan Cdp 4 Native Vlan Mismatch",
    "vendor": "cisco",
    "category": "Cisco SD-WAN",
    "index": "netops_logs",
    "sample": "2026-09-20T14:30:00.000ZTS2026-09-20T14:30:00.000Z 10.201.48.120 1044: *2026-09-20T14:30:00.000ZTS2026-09-20T14:30:00.000Z:  %CDP-4-NATIVE_VLAN_MISMATCH: Native VLAN mismatch discovered on GigabitEthernet1/0/4 (1), with switch2 GigabitEthernet0/1 (201)."
  },
  {
    "id": "cisco:sdwan:CRYPTO-6-ISAKMP_ON_OFF",
    "label": "Cisco Sdwan Crypto 6 Isakmp On Off",
    "vendor": "cisco",
    "category": "Cisco SD-WAN",
    "index": "netops_logs",
    "sample": "2026-09-20T14:30:00.000ZSYSLOG_TIMESTAMP2026-09-20T14:30:00.000Z 2026-09-20T14:30:00.000ZHOST2026-09-20T14:30:00.000Z 14675: 2026-09-20T14:30:00.000ZSYSLOG_TIMESTAMP2026-09-20T14:30:00.000Z.701: %CRYPTO-6-ISAKMP_ON_OFF: ISAKMP is ON"
  },
  {
    "id": "cisco:sdwan:CTS-3-AAA_NO_RADIUS_SERVER",
    "label": "Cisco Sdwan Cts 3 Aaa No Radius Server",
    "vendor": "cisco",
    "category": "Cisco SD-WAN",
    "index": "netops_logs",
    "sample": "2026-09-20T14:30:00.000ZTS2026-09-20T14:30:00.000Z 10.201.48.116 173: *2026-09-20T14:30:00.000ZTS2026-09-20T14:30:00.000Z:  %CTS-3-AAA_NO_RADIUS_SERVER: No RADIUS servers available for CTS AAA request for CTS env-data SM"
  },
  {
    "id": "cisco:sdwan:DMI-5-AUTH_PASSED",
    "label": "Cisco Sdwan Dmi 5 Auth Passed",
    "vendor": "cisco",
    "category": "Cisco SD-WAN",
    "index": "netops_logs",
    "sample": "2026-09-20T14:30:00.000ZSYSLOG_TIMESTAMP2026-09-20T14:30:00.000Z 2026-09-20T14:30:00.000ZHOST2026-09-20T14:30:00.000Z 91622: 2026-09-20T14:30:00.000ZSYSLOG_TIMESTAMP2026-09-20T14:30:00.000Z.691: %DMI-5-AUTH_PASSED: R0/0: dmiauthd: User ''vmanage-admin'' authenticated successfully from 1.1.1.105:36298  for netconf over ssh. External groups:"
  },
  {
    "id": "cisco:sdwan:DMI-5-CONFIG_I",
    "label": "Cisco Sdwan Dmi 5 Config I",
    "vendor": "cisco",
    "category": "Cisco SD-WAN",
    "index": "netops_logs",
    "sample": "2026-09-20T14:30:00.000ZSYSLOG_TIMESTAMP2026-09-20T14:30:00.000Z 2026-09-20T14:30:00.000ZHOST2026-09-20T14:30:00.000Z 14666: *2026-09-20T14:30:00.000ZSYSLOG_TIMESTAMP2026-09-20T14:30:00.000Z.404: %DMI-5-CONFIG_I: R0/0: dmiauthd: Configured from NETCONF/RESTCONF by system-ompd-fwd, transaction-id 682279"
  },
  {
    "id": "cisco:sdwan:DMI-5-SYNC_COMPLETE",
    "label": "Cisco Sdwan Dmi 5 Sync Complete",
    "vendor": "cisco",
    "category": "Cisco SD-WAN",
    "index": "netops_logs",
    "sample": "2026-09-20T14:30:00.000ZTS2026-09-20T14:30:00.000Z 10.201.48.115 3103: *2026-09-20T14:30:00.000ZTS2026-09-20T14:30:00.000Z:  %DMI-5-SYNC_COMPLETE: Switch 1 R0/0: dmiauthd: The running configuration has been synchronized to the NETCONF running data store."
  },
  {
    "id": "cisco:sdwan:DMI-5-SYNC_NEEDED",
    "label": "Cisco Sdwan Dmi 5 Sync Needed",
    "vendor": "cisco",
    "category": "Cisco SD-WAN",
    "index": "netops_logs",
    "sample": "2026-09-20T14:30:00.000ZTS2026-09-20T14:30:00.000Z 10.201.48.115 3101: *2026-09-20T14:30:00.000ZTS2026-09-20T14:30:00.000Z:  %DMI-5-SYNC_NEEDED: Switch 1 R0/0: dmiauthd: Configuration change requiring running configuration sync detected - ''no vrf forwarding ''. The running configuration will be synchronized  to the NETCONF running data store."
  },
  {
    "id": "cisco:sdwan:DMI-5-SYNC_START",
    "label": "Cisco Sdwan Dmi 5 Sync Start",
    "vendor": "cisco",
    "category": "Cisco SD-WAN",
    "index": "netops_logs",
    "sample": "2026-09-20T14:30:00.000ZTS2026-09-20T14:30:00.000Z 10.201.48.115 3102: *2026-09-20T14:30:00.000ZTS2026-09-20T14:30:00.000Z:  %DMI-5-SYNC_START: Switch 1 R0/0: dmiauthd: Synchronization of the running configuration to the NETCONF running data store has started."
  },
  {
    "id": "cisco:sdwan:ENVIRONMENTAL-1-ALERT",
    "label": "Cisco Sdwan Environmental 1 Alert",
    "vendor": "cisco",
    "category": "Cisco SD-WAN",
    "index": "netops_logs",
    "sample": "2026-09-20T14:30:00.000ZSYSLOG_TIMESTAMP2026-09-20T14:30:00.000Z 2026-09-20T14:30:00.000ZHOST2026-09-20T14:30:00.000Z 27774: 2026-09-20T14:30:00.000ZSYSLOG_TIMESTAMP2026-09-20T14:30:00.000Z.765: %ENVIRONMENTAL-1-ALERT: Temp: Inlet 1, Location: R0, State: Warning, Reading: 43 Celsius"
  },
  {
    "id": "cisco:sdwan:EVENTLIB-3-CPUHOG",
    "label": "Cisco Sdwan Eventlib 3 Cpuhog",
    "vendor": "cisco",
    "category": "Cisco SD-WAN",
    "index": "netops_logs",
    "sample": "2026-09-20T14:30:00.000ZTS2026-09-20T14:30:00.000Z 10.201.48.121 3697: *2026-09-20T14:30:00.000ZTS2026-09-20T14:30:00.000Z:  %EVENTLIB-3-CPUHOG: Switch 1 R0/0: hman: undefined: 1026ms, Traceback=1#9c98bc34b8a46399248b88656ef73fd3  c:7F7229A64000+42630 c:7F7229A64000+FE9AD c:7F7229A64000+86F9E c:7F7229A64000+8804A c:7F7229A64000+65A4C c:7F7229A64000+58469 procmib_lib:7F722BC6A000+8309 :5B96778E7000+426F1 evlib:7F722D007000+9336 evlib:7F722D007000+9D70 orchestrator_lib:7F722BFB6000+12BE4"
  },
  {
    "id": "cisco:sdwan:IOSXE-3-PLATFORM",
    "label": "Cisco Sdwan Iosxe 3 Platform",
    "vendor": "cisco",
    "category": "Cisco SD-WAN",
    "index": "netops_logs",
    "sample": "2026-09-20T14:30:00.000ZTS2026-09-20T14:30:00.000Z 10.201.48.115 288: *2026-09-20T14:30:00.000ZTS2026-09-20T14:30:00.000Z:  %IOSXE-3-PLATFORM: Switch 1 R0/0: kernel: eth2: mtu greater than device maximum"
  },
  {
    "id": "cisco:sdwan:IOSXE_INFRA-4-NO_PUNT_KEEPALIVE",
    "label": "Cisco Sdwan Iosxe Infra 4 No Punt Keepalive",
    "vendor": "cisco",
    "category": "Cisco SD-WAN",
    "index": "netops_logs",
    "sample": "2026-09-20T14:30:00.000ZTS2026-09-20T14:30:00.000Z 10.201.48.120 2870: *2026-09-20T14:30:00.000ZTS2026-09-20T14:30:00.000Z:  %IOSXE_INFRA-4-NO_PUNT_KEEPALIVE:  Keepalive not received for 20 seconds"
  },
  {
    "id": "cisco:sdwan:IOSXE_RP_PAE_NOT-6-PAE_STARTUP",
    "label": "Cisco Sdwan Iosxe Rp Pae Not 6 Pae Startup",
    "vendor": "cisco",
    "category": "Cisco SD-WAN",
    "index": "netops_logs",
    "sample": "2026-09-20T14:30:00.000ZTS2026-09-20T14:30:00.000Z 10.201.48.115 2135: *2026-09-20T14:30:00.000ZTS2026-09-20T14:30:00.000Z:  %IOSXE_RP_PAE_NOT-6-PAE_STARTUP: Product Analytics is Disabled"
  },
  {
    "id": "cisco:sdwan:LINEPROTO-5-UPDOWN",
    "label": "Cisco Sdwan Lineproto 5 Updown",
    "vendor": "cisco",
    "category": "Cisco SD-WAN",
    "index": "netops_logs",
    "sample": "2026-09-20T14:30:00.000ZTS2026-09-20T14:30:00.000Z 10.201.48.115 3322: *2026-09-20T14:30:00.000ZTS2026-09-20T14:30:00.000Z:  %LINEPROTO-5-UPDOWN: Line protocol on Interface Vlan1930, changed state to down"
  },
  {
    "id": "cisco:sdwan:LINK-5-CHANGED",
    "label": "Cisco Sdwan Link 5 Changed",
    "vendor": "cisco",
    "category": "Cisco SD-WAN",
    "index": "netops_logs",
    "sample": "2026-09-20T14:30:00.000ZTS2026-09-20T14:30:00.000Z 10.201.48.115 3442: *2026-09-20T14:30:00.000ZTS2026-09-20T14:30:00.000Z:  %LINK-5-CHANGED: Interface Vlan1930, changed state to administratively down"
  },
  {
    "id": "cisco:sdwan:LINK-5-UPDOWN",
    "label": "Cisco Sdwan Link 5 Updown",
    "vendor": "cisco",
    "category": "Cisco SD-WAN",
    "index": "netops_logs",
    "sample": "2026-09-20T14:30:00.000ZTS2026-09-20T14:30:00.000Z 10.201.48.115 287: *2026-09-20T14:30:00.000ZTS2026-09-20T14:30:00.000Z:  %LINK-5-UPDOWN: Interface GigabitEthernet1/0/2, changed state to up"
  },
  {
    "id": "cisco:sdwan:MDT_CONNECTION-6-STATE_CHANGED",
    "label": "Cisco Sdwan Mdt Connection 6 State Changed",
    "vendor": "cisco",
    "category": "Cisco SD-WAN",
    "index": "cisco_mdt_metrics",
    "sample": "2026-09-20T14:30:00.000ZTS2026-09-20T14:30:00.000Z 10.201.48.120 3927: *2026-09-20T14:30:00.000ZTS2026-09-20T14:30:00.000Z:  %MDT_CONNECTION-6-STATE_CHANGED: Switch 1 R0/0: pubd: Connection state changed (id 6 - 10.20.1.16:25103:0:10.201.48.120): DOWN"
  },
  {
    "id": "cisco:sdwan:MSDP-5-PEER_UPDOWN",
    "label": "Cisco Sdwan Msdp 5 Peer Updown",
    "vendor": "cisco",
    "category": "Cisco SD-WAN",
    "index": "netops_logs",
    "sample": "2026-09-20T14:30:00.000ZTS2026-09-20T14:30:00.000Z 10.201.48.119 4394: *2026-09-20T14:30:00.000ZTS2026-09-20T14:30:00.000Z:  %MSDP-5-PEER_UPDOWN: Session to peer 10.201.151.1 going down"
  },
  {
    "id": "cisco:sdwan:NDBMAN-5-CONFIG_I",
    "label": "Cisco Sdwan Ndbman 5 Config I",
    "vendor": "cisco",
    "category": "Cisco SD-WAN",
    "index": "netops_logs",
    "sample": "2026-09-20T14:30:00.000ZTS2026-09-20T14:30:00.000Z 10.201.48.118 3269: *2026-09-20T14:30:00.000ZTS2026-09-20T14:30:00.000Z:  %NDBMAN-5-CONFIG_I: Switch 1 R0/0: ndbmand: Configured feature ''yang-mapping'' from 127.0.0.1:0 via INTERNAL-API user yang_mgmt_infra session 20, transaction-id 102"
  },
  {
    "id": "cisco:sdwan:OSPF-5-ADJCHG",
    "label": "Cisco Sdwan Ospf 5 Adjchg",
    "vendor": "cisco",
    "category": "Cisco SD-WAN",
    "index": "netops_logs",
    "sample": "2026-09-20T14:30:00.000ZTS2026-09-20T14:30:00.000Z 10.201.48.119 4393: *2026-09-20T14:30:00.000ZTS2026-09-20T14:30:00.000Z:  %OSPF-5-ADJCHG: Process 1, Nbr 10.201.48.120 on GigabitEthernet1/0/5 from FULL to DOWN, Neighbor Down: Dead timer expired"
  },
  {
    "id": "cisco:sdwan:PKI-6-AUTHORITATIVE_CLOCK",
    "label": "Cisco Sdwan Pki 6 Authoritative Clock",
    "vendor": "cisco",
    "category": "Cisco SD-WAN",
    "index": "netops_logs",
    "sample": "2026-09-20T14:30:00.000ZSYSLOG_TIMESTAMP2026-09-20T14:30:00.000Z 2026-09-20T14:30:00.000ZHOST2026-09-20T14:30:00.000Z 11108: 2026-09-20T14:30:00.000ZSYSLOG_TIMESTAMP2026-09-20T14:30:00.000Z.633: %PKI-6-AUTHORITATIVE_CLOCK: The system clock has been set."
  },
  {
    "id": "cisco:sdwan:PLATFORM-4-ELEMENT_WARNING",
    "label": "Cisco Sdwan Platform 4 Element Warning",
    "vendor": "cisco",
    "category": "Cisco SD-WAN",
    "index": "netops_logs",
    "sample": "2026-09-20T14:30:00.000ZSYSLOG_TIMESTAMP2026-09-20T14:30:00.000Z 2026-09-20T14:30:00.000ZHOST2026-09-20T14:30:00.000Z 14767: 2026-09-20T14:30:00.000ZSYSLOG_TIMESTAMP2026-09-20T14:30:00.000Z.919: %PLATFORM-4-ELEMENT_WARNING: R0/0: smand: RP/0: 5-Minute Load Average value 6.11 exceeds warning level 6.10."
  },
  {
    "id": "cisco:sdwan:sitehealth",
    "label": "Cisco Sdwan Sitehealth",
    "vendor": "cisco",
    "category": "Cisco SD-WAN",
    "index": "netops_logs",
    "sample": "{\"site_id\": \"500\", \"site_name\": \"SITE_500\", \"latitude\": \"45.424721\", \"longitude\": \"-75.695\", \"fromGps\": \"false\", \"site_health\": \"good\", \"devices_health\": \"good\", \"tunnels_health\": \"no_data\", \"apps_health\": \"no_data\", \"devices_health_score\": 10.0, \"tunnels_health_score\": -1.0, \"apps_health_score\": -1.0, \"apps_usage\": 0.0, \"prev_apps_usage\": 0.0, \"region_list\": [], \"role\": [], \"device_type\": [], \"lastUpdated\": 1784258195806}"
  },
  {
    "id": "cisco:sdwan:ssetunnels",
    "label": "Cisco Sdwan Ssetunnels",
    "vendor": "cisco",
    "category": "Cisco SD-WAN",
    "index": "netops_logs",
    "sample": "{\"device-state\": \"Up\", \"tunnel-if-name\": \"Tunnel17000102\", \"vdevice-name\": \"172.80.1.10\", \"createTimeStamp\": 2026-09-20T14:30:00.000ZEPOCH_MS2026-09-20T14:30:00.000Z, \"sse-tcsm\": \"-\", \"vdevice-host-name\": \"C1131X-site8000\", \"tunnelType\": \"SSE-Private access\", \"vdevice-dataKey\": \"172.80.1.10-Tunnel17000102--\", \"destination-data-center\": \"35.171.214.188\", \"vmanage-system-ip\": \"172.80.1.10\", \"tenantId\": \"default\", \"lastupdated\": 2026-09-20T14:30:00.000ZEPOCH_MS2026-09-20T14:30:00.000Z, \"sig-state\": \"Up\", \"eventNumber\": 0, \"site-name\": \"Montreal\", \"device-packets-in\": 0, \"device-packets-out\": 0, \"site-id\": \"8000\", \"tunnel-name\": \"us-east-1\", \"tunnel-id\": \"666447230\", \"tunnel-type\": \"IPSEC\", \"provider\": \"Cisco Secure Access\", \"lastModified\": 2026-09-20T14:30:00.000ZEPOCH_MS2026-09-20T14:30:00.000Z}"
  },
  {
    "id": "cisco:sdwan:SYS-5-CONFIG_P",
    "label": "Cisco Sdwan Sys 5 Config P",
    "vendor": "cisco",
    "category": "Cisco SD-WAN",
    "index": "netops_logs",
    "sample": "2026-09-20T14:30:00.000ZSYSLOG_TIMESTAMP2026-09-20T14:30:00.000Z 2026-09-20T14:30:00.000ZHOST2026-09-20T14:30:00.000Z 14667: *2026-09-20T14:30:00.000ZSYSLOG_TIMESTAMP2026-09-20T14:30:00.000Z.559: %SYS-5-CONFIG_P: Configured programmatically by process iosp_dmiauthd_conn_100001_vty_100001 from console as system-ompd-fwd on vty4294966494"
  },
  {
    "id": "cisco:sdwan:syslog",
    "label": "Cisco Sdwan Syslog",
    "vendor": "cisco",
    "category": "Cisco SD-WAN",
    "index": "netops_logs",
    "sample": "2026-09-20T14:30:00.000ZSYSLOG_TIMESTAMP2026-09-20T14:30:00.000Z 2026-09-20T14:30:00.000ZHOST2026-09-20T14:30:00.000Z 186746: 2026-09-20T14:30:00.000ZSYSLOG_TIMESTAMP2026-09-20T14:30:00.000Z.730: %DMI-5-AUTH_PASSED: R0/0: dmiauthd: User ''vmanage-admin'' authenticated successfully from 1.1.1.105:54758  for netconf over ssh. External groups:"
  },
  {
    "id": "cisco:sdwan:system:logs",
    "label": "Cisco Sdwan System Logs",
    "vendor": "cisco",
    "category": "Cisco SD-WAN",
    "index": "netops_logs",
    "sample": "2026-09-20T14:30:00.000ZSYSLOG_TIMESTAMP2026-09-20T14:30:00.000Z 2026-09-20T14:30:00.000ZHOST2026-09-20T14:30:00.000Z 162896: 2026-09-20T14:30:00.000ZSYSLOG_TIMESTAMP2026-09-20T14:30:00.000Z.857: %SDWAN-5-FPMD : FLOW LOG device-vpn: 4099 tenant-vpn: 4099 src: 10.201.48.53/179 dst: 10.201.48.54/54097 proto: 6 tos: 192 direction: from-service, policy: data_service_CiscoLive_AAR_Policy-vpn_Service_VPN_Secure, sequence: 1, Result: accept Pkt count: 211900 bytes: 14305753 Ingress-Intf: GigabitEthernet0/0/2.3105 Egress-intf: Unknown Tenant: Not-Applicable"
  },
  {
    "id": "cisco:sdwan:sytem:logs",
    "label": "Cisco Sdwan Sytem Logs",
    "vendor": "cisco",
    "category": "Cisco SD-WAN",
    "index": "netops_logs",
    "sample": "2026-09-20T14:30:00.000ZTS2026-09-20T14:30:00.000Z 192.168.128.1 1 1772323200.984001859 MX_67_Home ip_flow_end src=192.168.128.102 dst=23.220.93.204 protocol=tcp sport=52390 dport=443 translated_src_ip=192.168.1.66 translated_port=52390"
  },
  {
    "id": "cisco:sdwan:tunnelhealth",
    "label": "Cisco Sdwan Tunnelhealth",
    "vendor": "cisco",
    "category": "Cisco SD-WAN",
    "index": "netops_logs",
    "sample": "{\"loss_percentage\": 0.0, \"latency\": 0.0, \"jitter\": 0.0, \"tx_octets\": 10411.0, \"rx_octets\": 67099.0, \"vqoe_score\": 10.0, \"name\": \"1.1.1.110:private2-1.1.1.100:private2\", \"remote_color\": \"private2\", \"remote_system_ip\": \"1.1.1.100\", \"remote-host-name\": \"SD-WAN_Edge-Kanata\", \"remote_site_id\": \"100\", \"remoteDeviceClass\": \"cisco-router\", \"remote_latitude\": \"45.3422\", \"remote_longitude\": \"-75.92656\", \"local_color\": \"private2\", \"local_system_ip\": \"1.1.1.110\", \"device-type\": \"vedge\", \"deviceClass\": \"cisco-router\", \"site_id\": \"110\", \"state\": \"Up\", \"health\": \"green\", \"lastUpdated\": 1784258197832}"
  },
  {
    "id": "cisco:sdwan:utd:logs",
    "label": "Cisco Sdwan Utd Logs",
    "vendor": "cisco",
    "category": "Cisco SD-WAN",
    "index": "netops_logs",
    "sample": "2026-09-20T14:30:00.000ZTS2026-09-20T14:30:00.000Z 192.168.128.132 2026/03/01-00:00:00.307403 UTC [**] [Hostname: c8kv-site-3000-gw1] [**] [System_IP: 172.100.1.5] [**] [Instance_ID: 1] [**] Drop [**] UTD WebFilter Category/Reputation [**] [URL: www.tekdefense.com/downloads/malware-samples/1.exe.zip] ** [Category: Malware Sites] ** [Reputation: 10] [POLICY: BR-TYPE2-AIP] {TCP} 10.33.35.101:55924 -> 198.185.159.160:80"
  },
  {
    "id": "cisco:sdwan:utdhealth",
    "label": "Cisco Sdwan Utdhealth",
    "vendor": "cisco",
    "category": "Cisco SD-WAN",
    "index": "netops_logs",
    "sample": "{\"vdevice-dataKey\": \"172.100.1.5\", \"utd-engine-status-version\": \"1.1.0_SV3.3.5.0_XE17.18\", \"vdevice-name\": \"172.100.1.5\", \"utd-engine-status-memory-status\": \"utd-oper-status-green\", \"lastupdated\": 2026-09-20T14:30:00.000ZEPOCH_MS2026-09-20T14:30:00.000Z, \"utd-engine-status-status\": \"utd-oper-status-green\", \"utd-engine-status-memory-usage\": \"44.9\", \"vdevice-host-name\": \"c8kv-site-3000-gw1\", \"utd-engine-status-profile\": \"Cloud-Low\"}"
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
    "sample": "{  \"serial\": \"Q2QN-TOR-MX100\",  \"networkName\": \"Toronto Hub\",  \"uplinks\": [   {    \"interface\": \"wan1\",    \"status\": \"active\",    \"ip\": \"198.51.100.2\",    \"gateway\": \"198.51.100.1\",    \"publicIp\": \"198.51.100.2\"   }  ],  \"vpnPeers\": [   {    \"peerNetworkId\": \"N_EDMONTON_B1\",    \"peerName\": \"Edmonton Branch 1\",    \"reachability\": \"reachable\",    \"mode\": \"spoke\"   },   {    \"peerNetworkId\": \"N_CALGARY_B2\",    \"peerName\": \"Calgary Branch 2\",    \"reachability\": \"reachable\",    \"mode\": \"spoke\"   }  ] }"
  },
  {
    "id": "meraki:assurancealerts",
    "label": "Meraki Assurancealerts",
    "vendor": "cisco",
    "category": "Meraki",
    "index": "netops_logs",
    "sample": "{  \"id\": \"alert_tor_0000\",  \"networkId\": \"N_TORONTO_DC\",  \"scope\": \"network\",  \"severity\": \"info\",  \"category\": \"Connectivity\",  \"type\": \"NetworkStatusNormal\",  \"title\": \"All devices operating within expected assurance parameters\",  \"startedAt\": \"2026-09-20T14:30:00.000ZISO_TS2026-09-20T14:30:00.000Z\",  \"resolvedAt\": \"2026-09-20T14:30:00.000ZISO_TS2026-09-20T14:30:00.000Z\",  \"device\": {   \"serial\": \"Q2QN-TOR-MX100\",   \"name\": \"MX100-Toronto-Hub\"  } }"
  },
  {
    "id": "meraki:devices",
    "label": "Meraki Devices",
    "vendor": "cisco",
    "category": "Meraki",
    "index": "netops_logs",
    "sample": "{  \"serial\": \"Q2QN-TOR-MS250\",  \"name\": \"MS250-Toronto-Core\",  \"mac\": \"0c:8d:db:6f:10:01\",  \"networkId\": \"N_TORONTO_DC\",  \"model\": \"MS250-48FP\",  \"address\": \"150 King St W, Toronto, ON M5H 1J9\",  \"lat\": 43.6487,  \"lng\": -79.3854,  \"notes\": \"Toronto Hub Core Switch\",  \"tags\": [\"hub\", \"datacenter\", \"core\"],  \"lanIp\": \"10.10.10.2\",  \"firmware\": \"MS 15.21.1\",  \"status\": \"online\",  \"productType\": \"switch\" }"
  },
  {
    "id": "meraki:devicesavailabilitieschangehistory",
    "label": "Meraki Devices Availabilities",
    "vendor": "cisco",
    "category": "Meraki",
    "index": "netops_logs",
    "sample": "{  \"ts\": \"2026-09-20T14:30:00.000ZISO_TS2026-09-20T14:30:00.000Z\",  \"device\": {   \"serial\": \"Q2QN-TOR-MX100\",   \"name\": \"MX100-Toronto-Hub\",   \"productType\": \"appliance\",   \"model\": \"MX100\"  },  \"network\": {   \"id\": \"N_TORONTO_DC\",   \"name\": \"Toronto Hub\"  },  \"oldStatus\": \"offline\",  \"newStatus\": \"online\",  \"duration\": 3600000 }"
  },
  {
    "id": "meraki:organizationsecurity",
    "label": "Meraki Organizationsecurity",
    "vendor": "cisco",
    "category": "Meraki",
    "index": "netops_logs",
    "sample": "{  \"ts\": \"2026-09-20T14:30:00.000ZISO_TS2026-09-20T14:30:00.000Z\",  \"event\": \"ids_alert\",  \"organizationId\": \"ORG_ACME_CANADA\",  \"networkName\": \"Toronto Hub\",  \"clientMac\": \"f0:18:98:3a:11:02\",  \"message\": \"Routine signature database check completed\",  \"action\": \"allow\",  \"priority\": \"low\" }"
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
    "sample": "{  \"networkId\": \"N_TORONTO_DC\",  \"topClients\": [   {\"name\": \"tor-db-backup-01\", \"mac\": \"00:50:56:a1:b2:c3\", \"totalBytes\": 1250000000, \"sentBytes\": 850000000, \"recvBytes\": 400000000},   {\"name\": \"tor-app-srv-02\", \"mac\": \"00:50:56:d4:e5:f6\", \"totalBytes\": 890000000, \"sentBytes\": 490000000, \"recvBytes\": 400000000},   {\"name\": \"mrayani-laptop\", \"mac\": \"f0:18:98:77:22:11\", \"totalBytes\": 45000000, \"sentBytes\": 12000000, \"recvBytes\": 33000000}  ] }"
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
    "sample": "{  \"serial\": \"Q2QN-TOR-MS250\",  \"switchName\": \"MS250-Toronto-Core\",  \"portId\": \"24\",  \"name\": \"Uplink to MX100 WAN\",  \"enabled\": true,  \"status\": \"Connected\",  \"speed\": \"1 Gbps\",  \"duplex\": \"full\",  \"vlan\": 1,  \"traffic\": {   \"totalBytes\": 145028090,   \"sentBytes\": 78201940,   \"recvBytes\": 66826150  },  \"errors\": {   \"crc\": 0,   \"runts\": 0,   \"giants\": 0,   \"fragments\": 0,   \"collisions\": 0,   \"jabbers\": 0  },  \"discards\": {   \"input\": 0,   \"output\": 0  } }"
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
    "sample": "{\"2026-09-20T14:30:00.000Zreserved\": {\"2026-09-20T14:30:00.000Zfv\": \"v4.r0\"}, \"2026-09-20T14:30:00.000ZobjectType\": \"monitoring.v4.serviceability.Alert\", \"extId\": \"d711c281-18fe-4fcc-8937-333d41165889\", \"isAcknowledged\": true, \"acknowledgedTime\": \"2026-09-20T14:30:00.000ZISO_TIMESTAMP2026-09-20T14:30:00.000Z\", \"isAutoResolved\": true, \"isResolved\": true, \"resolvedTime\": \"2026-09-20T14:30:00.000ZISO_TIMESTAMP2026-09-20T14:30:00.000Z\", \"sourceEntity\": {\"2026-09-20T14:30:00.000Zreserved\": {\"2026-09-20T14:30:00.000Zfv\": \"v4.r0\"}, \"2026-09-20T14:30:00.000ZobjectType\": \"monitoring.v4.common.AlertEntityReference\", \"type\": \"node\", \"name\": \"CCHCI-07.maple.ciscolabs.com\", \"extId\": \"64f966f6-49ef-40ba-ae85-987ad33edc34\"}, \"affectedEntities\": [{\"2026-09-20T14:30:00.000Zreserved\": {\"2026-09-20T14:30:00.000Zfv\": \"v4.r0\"}, \"2026-09-20T14:30:00.000ZobjectType\": \"monitoring.v4.common.EntityReference\", \"type\": \"node\", \"name\": \"CCHCI-07.maple.ciscolabs.com\", \"extId\": \"64f966f6-49ef-40ba-ae85-987ad33edc34\"}], \"severityTrails\": [{\"2026-09-20T14:30:00.000Zreserved\": {\"2026-09-20T14:30:00.000Zfv\": \"v4.r0\"}, \"2026-09-20T14:30:00.000ZobjectType\": \"monitoring.v4.serviceability.SeverityTrail\", \"severity\": \"CRITICAL\", \"severityChangeTime\": \"2026-09-20T14:30:00.000ZISO_TIMESTAMP2026-09-20T14:30:00.000Z\"}], \"title\": \"Disk mounted at /home/nutanix/data/stargate-storage/disks/S5MPNA0N901932 on CVM 10.0.4.127 Failed/Marked offline\", \"alertType\": \"A1044\", \"classifications\": [\"Hardware\", \"Storage\"], \"clusterUUID\": \"00061768-f76f-4f95-3e5f-0025b500016f\", \"creationTime\": \"2026-09-20T14:30:00.000ZISO_TIMESTAMP2026-09-20T14:30:00.000Z\", \"impactTypes\": [\"SYSTEM_INDICATOR\"], \"lastUpdatedTime\": \"2026-09-20T14:30:00.000ZISO_TIMESTAMP2026-09-20T14:30:00.000Z\", \"message\": \"Disk mounted at /home/nutanix/data/stargate-storage/disks/S5MPNA0N901932 on node 10.0.4.127 with ID 159094719 has been marked offline.\", \"originatingClusterUUID\": \"00061768-f76f-4f95-3e5f-0025b500016f\", \"severity\": \"CRITICAL\", \"isUserDefined\": false, \"parameters\": [{\"paramValue\": {\"2026-09-20T14:30:00.000Zreserved\": {\"2026-09-20T14:30:00.000Zfv\": \"v4.r0\"}, \"2026-09-20T14:30:00.000ZobjectType\": \"monitoring.v4.common.BoolValue\", \"boolValue\": true}, \"2026-09-20T14:30:00.000Zreserved\": {\"2026-09-20T14:30:00.000Zfv\": \"v4.r0\"}, \"2026-09-20T14:30:00.000ZobjectType\": \"monitoring.v4.common.Parameter\", \"paramName\": \"alert_log_collect\"}, {\"paramValue\": {\"2026-09-20T14:30:00.000Zreserved\": {\"2026-09-20T14:30:00.000Zfv\": \"v4.r0\"}, \"2026-09-20T14:30:00.000ZobjectType\": \"monitoring.v4.common.StringValue\", \"stringValue\": \"disk_failure\"}, \"paramName\": \"alert_log_tag_list\"}, {\"paramValue\": {\"2026-09-20T14:30:00.000Zreserved\": {\"2026-09-20T14:30:00.000Zfv\": \"v4.r0\"}, \"2026-09-20T14:30:00.000ZobjectType\": \"monitoring.v4.common.StringValue\", \"stringValue\": \"-4h\"}, \"paramName\": \"alert_log_duration\"}, {\"paramValue\": {\"2026-09-20T14:30:00.000Zreserved\": {\"2026-09-20T14:30:00.000Zfv\": \"v4.r0\"}, \"2026-09-20T14:30:00.000ZobjectType\": \"monitoring.v4.common.StringValue\", \"stringValue\": \"/home/nutanix/data/stargate-storage/disks/S5MPNA0N901932\"}, \"paramName\": \"mount_path\"}, {\"paramValue\": {\"2026-09-20T14:30:00.000Zreserved\": {\"2026-09-20T14:30:00.000Zfv\": \"v4.r0\"}, \"2026-09-20T14:30:00.000ZobjectType\": \"monitoring.v4.common.StringValue\", \"stringValue\": \"/home/nutanix/data/stargate-storage/disks/S5MPNA0N901932\"}}, {\"paramValue\": {\"2026-09-20T14:30:00.000Zreserved\": {\"2026-09-20T14:30:00.000Zfv\": \"v4.r0\"}, \"2026-09-20T14:30:00.000ZobjectType\": \"monitoring.v4.common.StringValue\", \"stringValue\": \"10.0.4.127\"}, \"paramName\": \"ip_address\"}, {\"paramValue\": {\"2026-09-20T14:30:00.000Zreserved\": {\"2026-09-20T14:30:00.000Zfv\": \"v4.r0\"}, \"2026-09-20T14:30:00.000ZobjectType\": \"monitoring.v4.common.IntValue\", \"intValue\": 159094719}, \"paramName\": \"service_vm_id\"}, {\"paramValue\": {\"2026-09-20T14:30:00.000Zreserved\": {\"2026-09-20T14:30:00.000Zfv\": \"v4.r0\"}, \"2026-09-20T14:30:00.000ZobjectType\": \"monitoring.v4.common.IntValue\", \"intValue\": 159094719}, \"paramName\": \"arithmos_id\"}, {\"paramValue\": {\"2026-09-20T14:30:00.000Zreserved\": {\"2026-09-20T14:30:00.000Zfv\": \"v4.r0\"}, \"2026-09-20T14:30:00.000ZobjectType\": \"monitoring.v4.common.StringValue\", \"stringValue\": \"5.1.1-16f10d0e\"}, \"paramName\": \"ncc_version\"}, {\"paramValue\": {\"2026-09-20T14:30:00.000Zreserved\": {\"2026-09-20T14:30:00.000Zfv\": \"v4.r0\"}, \"2026-09-20T14:30:00.000ZobjectType\": \"monitoring.v4.common.StringValue\", \"stringValue\": \"6.10\"}, \"paramName\": \"nos_version\"}, {\"paramValue\": {\"2026-09-20T14:30:00.000Zreserved\": {\"2026-09-20T14:30:00.000Zfv\": \"v4.r0\"}, \"2026-09-20T14:30:00.000ZobjectType\": \"monitoring.v4.common.StringValue\", \"stringValue\": \"64f966f6-49ef-40ba-ae85-987ad33edc34\"}, \"paramName\": \"node_uuid\"}, {\"paramValue\": {\"2026-09-20T14:30:00.000Zreserved\": {\"2026-09-20T14:30:00.000Zfv\": \"v4.r0\"}, \"2026-09-20T14:30:00.000ZobjectType\": \"monitoring.v4.common.StringValue\", \"stringValue\": \"WMP245000FS\"}, \"paramName\": \"node_serial\"}, {\"paramValue\": {\"2026-09-20T14:30:00.000Zreserved\": {\"2026-09-20T14:30:00.000Zfv\": \"v4.r0\"}, \"2026-09-20T14:30:00.000ZobjectType\": \"monitoring.v4.common.StringValue\", \"stringValue\": \"WMP245000FS\"}, \"paramName\": \"block_serial\"}], \"rootCauseAnalysis\": [{\"2026-09-20T14:30:00.000Zreserved\": {\"2026-09-20T14:30:00.000Zfv\": \"v4.r0\"}, \"2026-09-20T14:30:00.000ZobjectType\": \"monitoring.v4.serviceability.RootCauseAnalysis\", \"cause\": \"A drive on the node was marked offline.\", \"resolution\": \"Investigate disk health. Please refer to KB 8453\"}]}"
  },
  {
    "id": "nutanixpc_cluster_performance",
    "label": "Nutanixpc Cluster Performance",
    "vendor": "nutanix",
    "category": "Nutanix PC",
    "index": "cisco_mdt_metrics",
    "sample": "{\"timestamp\": \"2026-09-20T14:30:00.000ZISO_TIMESTAMP2026-09-20T14:30:00.000Z\", \"extId\": \"00063ffb-2c0b-2e6c-7635-0025b500010e\", \"controllerAvgIoLatencyUsecs\": 2709, \"controllerAvgReadIoLatencyUsecs\": 806, \"controllerAvgWriteIoLatencyUsecs\": 2721, \"controllerNumIops\": 690, \"controllerNumReadIops\": 4, \"controllerNumWriteIops\": 686, \"ioBandwidthKbps\": 31861, \"controllerReadIoBandwidthKbps\": 153, \"controllerWriteIoBandwidthKbps\": 31708, \"hypervisorCpuUsagePpm\": 627193, \"aggregateHypervisorMemoryUsagePpm\": 847926, \"storageUsageBytes\": 7863761616896, \"storageCapacityBytes\": 25629749702147, \"freePhysicalStorageBytes\": 17765988085251, \"logicalStorageUsageBytes\": 12305592614912, \"overallMemoryUsageBytes\": 0}"
  },
  {
    "id": "nutanixpc_clusters",
    "label": "Nutanixpc Clusters",
    "vendor": "nutanix",
    "category": "Nutanix PC",
    "index": "netops_logs",
    "sample": "{\"2026-09-20T14:30:00.000Zreserved\": {\"2026-09-20T14:30:00.000Zfv\": \"v4.r0\"}, \"2026-09-20T14:30:00.000ZobjectType\": \"clustermgmt.v4.config.Cluster\", \"extId\": \"00063ffb-2c0b-2e6c-7635-0025b500010e\", \"vmCount\": 32, \"inefficientVmCount\": 0, \"backupEligibilityScore\": 4, \"name\": \"Fab1-CCHCI-AHV\", \"nodes\": {\"numberOfNodes\": 4, \"2026-09-20T14:30:00.000Zreserved\": {\"2026-09-20T14:30:00.000Zfv\": \"v4.r0\"}, \"2026-09-20T14:30:00.000ZobjectType\": \"clustermgmt.v4.config.NodeReference\", \"nodeList\": [{\"nodeUuid\": \"aeae14aa-ba3d-438b-b88b-5c803e72b6e4\", \"2026-09-20T14:30:00.000Zreserved\": {\"2026-09-20T14:30:00.000Zfv\": \"v4.r0\"}, \"2026-09-20T14:30:00.000ZobjectType\": \"clustermgmt.v4.config.NodeListItemReference\", \"controllerVmIp\": {\"2026-09-20T14:30:00.000Zreserved\": {\"2026-09-20T14:30:00.000Zfv\": \"v1.r0\"}, \"2026-09-20T14:30:00.000ZobjectType\": \"common.v1.config.IPAddress\", \"ipv4\": {\"2026-09-20T14:30:00.000Zreserved\": {\"2026-09-20T14:30:00.000Zfv\": \"v1.r0\"}, \"2026-09-20T14:30:00.000ZobjectType\": \"common.v1.config.IPv4Address\", \"value\": \"10.0.4.128\", \"prefixLength\": 32}}, \"hostIp\": {\"2026-09-20T14:30:00.000Zreserved\": {\"2026-09-20T14:30:00.000Zfv\": \"v1.r0\"}, \"2026-09-20T14:30:00.000ZobjectType\": \"common.v1.config.IPAddress\", \"ipv4\": {\"2026-09-20T14:30:00.000Zreserved\": {\"2026-09-20T14:30:00.000Zfv\": \"v1.r0\"}, \"2026-09-20T14:30:00.000ZobjectType\": \"common.v1.config.IPv4Address\", \"value\": \"10.0.4.141\", \"prefixLength\": 32}}}, {\"nodeUuid\": \"923664c7-2f66-4a08-a81d-dae05d9d5b04\", \"controllerVmIp\": {\"2026-09-20T14:30:00.000Zreserved\": {\"2026-09-20T14:30:00.000Zfv\": \"v1.r0\"}, \"2026-09-20T14:30:00.000ZobjectType\": \"common.v1.config.IPAddress\", \"ipv4\": {\"2026-09-20T14:30:00.000Zreserved\": {\"2026-09-20T14:30:00.000Zfv\": \"v1.r0\"}, \"2026-09-20T14:30:00.000ZobjectType\": \"common.v1.config.IPv4Address\", \"value\": \"10.0.4.129\", \"prefixLength\": 32}}, \"hostIp\": {\"2026-09-20T14:30:00.000Zreserved\": {\"2026-09-20T14:30:00.000Zfv\": \"v1.r0\"}, \"2026-09-20T14:30:00.000ZobjectType\": \"common.v1.config.IPAddress\", \"ipv4\": {\"2026-09-20T14:30:00.000Zreserved\": {\"2026-09-20T14:30:00.000Zfv\": \"v1.r0\"}, \"2026-09-20T14:30:00.000ZobjectType\": \"common.v1.config.IPv4Address\", \"value\": \"10.0.4.142\", \"prefixLength\": 32}}}, {\"nodeUuid\": \"1d538f08-44db-4bf5-ab0f-06b84f6d2ab9\", \"controllerVmIp\": {\"2026-09-20T14:30:00.000Zreserved\": {\"2026-09-20T14:30:00.000Zfv\": \"v1.r0\"}, \"2026-09-20T14:30:00.000ZobjectType\": \"common.v1.config.IPAddress\", \"ipv4\": {\"2026-09-20T14:30:00.000Zreserved\": {\"2026-09-20T14:30:00.000Zfv\": \"v1.r0\"}, \"2026-09-20T14:30:00.000ZobjectType\": \"common.v1.config.IPv4Address\", \"value\": \"10.0.4.130\", \"prefixLength\": 32}}, \"hostIp\": {\"2026-09-20T14:30:00.000Zreserved\": {\"2026-09-20T14:30:00.000Zfv\": \"v1.r0\"}, \"2026-09-20T14:30:00.000ZobjectType\": \"common.v1.config.IPAddress\", \"ipv4\": {\"2026-09-20T14:30:00.000Zreserved\": {\"2026-09-20T14:30:00.000Zfv\": \"v1.r0\"}, \"2026-09-20T14:30:00.000ZobjectType\": \"common.v1.config.IPv4Address\", \"value\": \"10.0.4.143\", \"prefixLength\": 32}}}, {\"nodeUuid\": \"dc8562d0-9e55-4b4e-8bba-9f2e123dc411\", \"controllerVmIp\": {\"2026-09-20T14:30:00.000Zreserved\": {\"2026-09-20T14:30:00.000Zfv\": \"v1.r0\"}, \"2026-09-20T14:30:00.000ZobjectType\": \"common.v1.config.IPAddress\", \"ipv4\": {\"2026-09-20T14:30:00.000Zreserved\": {\"2026-09-20T14:30:00.000Zfv\": \"v1.r0\"}, \"2026-09-20T14:30:00.000ZobjectType\": \"common.v1.config.IPv4Address\", \"value\": \"10.0.4.126\", \"prefixLength\": 32}}, \"hostIp\": {\"2026-09-20T14:30:00.000Zreserved\": {\"2026-09-20T14:30:00.000Zfv\": \"v1.r0\"}, \"2026-09-20T14:30:00.000ZobjectType\": \"common.v1.config.IPAddress\", \"ipv4\": {\"2026-09-20T14:30:00.000Zreserved\": {\"2026-09-20T14:30:00.000Zfv\": \"v1.r0\"}, \"2026-09-20T14:30:00.000ZobjectType\": \"common.v1.config.IPv4Address\", \"value\": \"10.0.4.116\", \"prefixLength\": 32}}}]}, \"config\": {\"incarnationId\": 1759197868535404, \"hypervisorTypes\": [\"AHV\"], \"timezone\": \"UTC\", \"clusterSoftwareMap\": [{\"2026-09-20T14:30:00.000Zreserved\": {\"2026-09-20T14:30:00.000Zfv\": \"v4.r0\"}, \"2026-09-20T14:30:00.000ZobjectType\": \"clustermgmt.v4.config.SoftwareMapReference\", \"softwareType\": \"NCC\", \"version\": \"ncc-5.0.1.1\"}, {\"softwareType\": \"NOS\", \"version\": \"el8.5-release-fraser-6.10.1.8-stable-79931c46cc24c096b11202ff0865b34741ff8d41\"}], \"isRemoteSupportEnabled\": false, \"isLts\": true, \"isPasswordRemoteLoginEnabled\": true, \"isAvailable\": true, \"2026-09-20T14:30:00.000Zreserved\": {\"2026-09-20T14:30:00.000Zfv\": \"v4.r0\"}, \"2026-09-20T14:30:00.000ZobjectType\": \"clustermgmt.v4.config.ClusterConfigReference\", \"buildInfo\": {\"2026-09-20T14:30:00.000Zreserved\": {\"2026-09-20T14:30:00.000Zfv\": \"v4.r0\"}, \"2026-09-20T14:30:00.000ZobjectType\": \"clustermgmt.v4.config.BuildReference\", \"buildType\": \"release\", \"version\": \"6.10\", \"fullVersion\": \"el8.5-release-fraser-6.10.1.8-stable-79931c46cc24c096b11202ff0865b34741ff8d41\", \"commitId\": \"79931c46cc24c096b11202ff0865b34741ff8d41\", \"shortCommitId\": \"79931c\"}, \"clusterFunction\": [\"AOS\"], \"authorizedPublicKeyList\": [{\"2026-09-20T14:30:00.000Zreserved\": {\"2026-09-20T14:30:00.000Zfv\": \"v4.r0\"}, \"2026-09-20T14:30:00.000ZobjectType\": \"clustermgmt.v4.config.PublicKey\", \"name\": \"1d538f08-44db-4bf5-ab0f-06b84f6d2ab9\", \"key\": \"ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCwlis0+IKeKzgbU031f+DdqOWb7lvUA9Ua+BNP7P7yuNgQ3QQ/JQL237XWwMb7NvYpUkHxGpLechw+D8YouLdxYXUyPW+TGsmDNze5t7/Kya3HumjdPu2cDO05ZyHO15saE4t0Y3EMT7HDMQlC6d2n9xLzQS8Bbp+X56ZybnKNw8J/qnf9YEc+3JS6T4rlVwtJ5s80HOt5e5g6124bI3WR1UoJwqHbHVBaCg5a8NHhc0TTtEk/5kCIPS7tpC/c/XVRJ95mY39D2jmwUOQVCfc+jTFV2cNO1lPP10uhYdjg7V89mWDvu5HRV9PAoM4kDUie9DWn2bZ2mMQA2Y5VmqkZ nutanix@ntnx-wzp22020d80-a-cvm\"}, {\"name\": \"923664c7-2f66-4a08-a81d-dae05d9d5b04\", \"key\": \"ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQD1+IL0Uj9uTyQ2JxD4L3IVYgICTLBs7fFTnJyiExnH5SgjTbjJUqnewdgMnb/ggFJyXeISaN7vID+GL6XYOHvBDKLxrI6TB5L6p6DnjSpWzdBZBhKj4g7eaihXzf5HLv3tTjgfuX5rtx3qzov3X02NfBeBoBLyLvq42ObIbLX8XXZnTZ3w4xJVGVbPy1ng062xYOzRpT/6NZDRqhJOiGdkX9KExn9QUG9C0kqnRUx4WiUZrBK386ZkDTzJAlOnLY7Ji+JbUPLUKfk4wU12tNgj3Ftyn47NYst8a+bpKdU97lR35mNs6FScNIo+HpnO5ob16mChuPsAXNV+hXLMcliR nutanix@ntnx-wzp22020d7k-a-cvm\"}, {\"name\": \"aeae14aa-ba3d-438b-b88b-5c803e72b6e4\", \"key\": \"ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCwy3W3j/qCF3F/4in169zE8EpUBz50MT1vhv+wRO0qvgzNGT+WeUeh+ge1EE7fnQUXIsfIjWkDvq/wKALnfuugPESPdupez4M6pY+VNk6H+emiI/C+fwkQHq8XqOy+ymHJMZg2XD6q4UpiNbebseHGWWprXF2bdWbl5fBEGqX2Ijg6SbgTb5RMsXpLoh7zzIEzsNNBmKiunbnvBpXT1SBtXOFAS0K9nDnMvxFpm2RTO2VHMORf0QaRdcTeRmjimzevlGdM+cFP0ozF/1WYlqTpzhX79fB3jDkCebBTU4KGjE2+0LCJGdl5YAPGw0xr+Lo2DwfUMyWzEk0LdLv5ZbCT nutanix@ntnx-wzp22011m0r-a-cvm\"}, {\"name\": \"dc8562d0-9e55-4b4e-8bba-9f2e123dc411\", \"key\": \"ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQDBIw9vgiV7qA1+1ohpSqdURmw3+jPw2Qt6TcbIBTZJRz0xY6yFIiygWk/ZwCeJXNy+UVbmr85MrS6Fj9rUc97yH7gxyuNzCKU+lGRfVmO9sDCV6nS2VTSKfpQA97yAmsOx7XLE3GgEFDJ8Hbdu9DyHbysr+/Q1R6qVzEhppilMb3azByiH+Bu6QfddFn5H06VWT9wxmbge0P4KRGvS3JbLNrKJDDz/YkOUs+HSPSg9RxCcJ02lfdIw8uNfrtDCLAydFXy9HzVgwzTwuaWbPbDyvyxjVhrTpIZpacYFJNnXBIKgtlr3pUkSEE2B8mwuTaTTjBK1II7GYuTAkPHjowpza6nCxEoVsL5hafBXeZ2gEJig9xS7Yvypgtr8pQ7nMkPr2e+f+VK+dWdjopjuZv4TCPOn/UsM74/Ce4B+1Lq5Ct/Um0LWI4H0TRHnM0HufglZozHDTljEcKpHHtnCJnmN5kx4TUcLZke0nMzn5oYX0RcUkQ+gxGcM5dIiAq5Fhjk= nutanix@ntnx-wmp244201ar-a-cvm\"}], \"redundancyFactor\": 2, \"clusterArch\": \"X86_64\", \"faultToleranceState\": {\"currentMaxFaultTolerance\": 1, \"desiredMaxFaultTolerance\": 1, \"2026-09-20T14:30:00.000Zreserved\": {\"2026-09-20T14:30:00.000Zfv\": \"v4.r0\"}, \"2026-09-20T14:30:00.000ZobjectType\": \"clustermgmt.v4.config.FaultToleranceState\", \"domainAwarenessLevel\": \"NODE\"}, \"operationMode\": \"NORMAL\", \"pulseStatus\": {\"2026-09-20T14:30:00.000Zreserved\": {\"2026-09-20T14:30:00.000Zfv\": \"v4.r0\"}, \"2026-09-20T14:30:00.000ZobjectType\": \"clustermgmt.v4.config.PulseStatus\", \"isEnabled\": false}}, \"network\": {\"externalSubnet\": \"10.0.4.0/255.255.255.0\", \"internalSubnet\": \"192.168.5.0/255.255.255.128\", \"2026-09-20T14:30:00.000Zreserved\": {\"2026-09-20T14:30:00.000Zfv\": \"v4.r0\"}, \"2026-09-20T14:30:00.000ZobjectType\": \"clustermgmt.v4.config.ClusterNetworkReference\", \"externalAddress\": {\"2026-09-20T14:30:00.000Zreserved\": {\"2026-09-20T14:30:00.000Zfv\": \"v1.r0\"}, \"2026-09-20T14:30:00.000ZobjectType\": \"common.v1.config.IPAddress\", \"ipv4\": {\"2026-09-20T14:30:00.000Zreserved\": {\"2026-09-20T14:30:00.000Zfv\": \"v1.r0\"}, \"2026-09-20T14:30:00.000ZobjectType\": \"common.v1.config.IPv4Address\", \"value\": \"10.0.4.110\", \"prefixLength\": 32}}, \"externalDataServiceIp\": {\"2026-09-20T14:30:00.000Zreserved\": {\"2026-09-20T14:30:00.000Zfv\": \"v1.r0\"}, \"2026-09-20T14:30:00.000ZobjectType\": \"common.v1.config.IPAddress\"}, \"nfsSubnetWhitelist\": [\"10.0.52.200/255.255.255.255\"], \"nameServerIpList\": [{\"2026-09-20T14:30:00.000Zreserved\": {\"2026-09-20T14:30:00.000Zfv\": \"v1.r0\"}, \"2026-09-20T14:30:00.000ZobjectType\": \"common.v1.config.IPAddressOrFQDN\", \"ipv4\": {\"2026-09-20T14:30:00.000Zreserved\": {\"2026-09-20T14:30:00.000Zfv\": \"v1.r0\"}, \"2026-09-20T14:30:00.000ZobjectType\": \"common.v1.config.IPv4Address\", \"value\": \"10.0.10.23\", \"prefixLength\": 32}}, {\"ipv4\": {\"2026-09-20T14:30:00.000Zreserved\": {\"2026-09-20T14:30:00.000Zfv\": \"v1.r0\"}, \"2026-09-20T14:30:00.000ZobjectType\": \"common.v1.config.IPv4Address\", \"value\": \"10.0.10.22\", \"prefixLength\": 32}}], \"ntpServerIpList\": [{\"2026-09-20T14:30:00.000Zreserved\": {\"2026-09-20T14:30:00.000Zfv\": \"v1.r0\"}, \"2026-09-20T14:30:00.000ZobjectType\": \"common.v1.config.IPAddressOrFQDN\", \"ipv4\": {\"2026-09-20T14:30:00.000Zreserved\": {\"2026-09-20T14:30:00.000Zfv\": \"v1.r0\"}, \"2026-09-20T14:30:00.000ZobjectType\": \"common.v1.config.IPv4Address\", \"value\": \"10.0.10.252\", \"prefixLength\": 32}}, {\"ipv4\": {\"2026-09-20T14:30:00.000Zreserved\": {\"2026-09-20T14:30:00.000Zfv\": \"v1.r0\"}, \"2026-09-20T14:30:00.000ZobjectType\": \"common.v1.config.IPv4Address\", \"value\": \"10.0.10.253\", \"prefixLength\": 32}}], \"backplane\": {\"2026-09-20T14:30:00.000Zreserved\": {\"2026-09-20T14:30:00.000Zfv\": \"v4.r0\"}, \"2026-09-20T14:30:00.000ZobjectType\": \"clustermgmt.v4.config.BackplaneNetworkParams\", \"isSegmentationEnabled\": false}}, \"upgradeStatus\": \"SUCCEEDED\", \"pc_ip\": \"10.0.4.120\"}"
  },
  {
    "id": "nutanixpc_disk_performance",
    "label": "Nutanixpc Disk Performance",
    "vendor": "nutanix",
    "category": "Nutanix PC",
    "index": "cisco_mdt_metrics",
    "sample": "{\"timestamp\": \"2026-09-20T14:30:00.000ZISO_TIMESTAMP2026-09-20T14:30:00.000Z\", \"extId\": \"ff26ab7c-0d68-4421-b6bc-6cc4abf18975\", \"diskUsagePpm\": 455057, \"diskCapacityBytes\": 0, \"diskNumIops\": 0, \"diskIoBandwidthkbps\": 0, \"diskAvgIoLatencyMicrosec\": 0, \"diskFreeBytes\": 0, \"diskUsageBytes\": 0, \"diskReadIops\": 0, \"diskWriteIops\": 0, \"diskReadIoBandwidthkbps\": 0, \"diskWriteIoBandwidthkbps\": 0, \"diskReadIoPpm\": 0, \"diskWriteIoPpm\": 0}"
  },
  {
    "id": "nutanixPC_disks",
    "label": "Nutanixpc Disks",
    "vendor": "nutanix",
    "category": "Nutanix PC",
    "index": "netops_logs",
    "sample": "{\"2026-09-20T14:30:00.000Zreserved\": {\"2026-09-20T14:30:00.000Zfv\": \"v4.r0\"}, \"2026-09-20T14:30:00.000ZobjectType\": \"clustermgmt.v4.config.Disk\", \"extId\": \"ff26ab7c-0d68-4421-b6bc-6cc4abf18975\", \"links\": [{\"2026-09-20T14:30:00.000Zreserved\": {\"2026-09-20T14:30:00.000Zfv\": \"v1.r0\"}, \"2026-09-20T14:30:00.000ZobjectType\": \"common.v1.response.ApiLink\", \"href\": \"2026-09-20T14:30:00.000ZHOST2026-09-20T14:30:00.000Z/ff26ab7c-0d68-4421-b6bc-6cc4abf18975\", \"rel\": \"disk\"}], \"clusterName\": \"Fab1-CCHCI-AHV\", \"clusterExtId\": \"00063ffb-2c0b-2e6c-7635-0025b500010e\", \"storagePoolExtId\": \"3d2e376e-5978-474c-b4f4-a11dd814a4f8\", \"serviceVMId\": \"00063ffb-2c0b-2e6c-7635-0025b500010e::5\", \"nodeExtId\": \"1d538f08-44db-4bf5-ab0f-06b84f6d2ab9\", \"mountPath\": \"/home/nutanix/data/stargate-storage/disks/18G0A0ETTMEE\", \"location\": 8, \"serialNumber\": \"18G0A0ETTMEE\", \"diskSizeBytes\": 320582727018, \"physicalCapacityBytes\": 400088457216, \"model\": \"PX05SMB040\", \"vendor\": \"TOSHIBA\", \"firmwareVersion\": \"0104\", \"targetFirmwareVersion\": \"0104\", \"hostName\": \"CCHCI-AHV-03\", \"status\": \"NORMAL\", \"storageTier\": \"SSD_SATA\", \"cvmIpAddress\": {\"2026-09-20T14:30:00.000Zreserved\": {\"2026-09-20T14:30:00.000Zfv\": \"v1.r0\"}, \"2026-09-20T14:30:00.000ZobjectType\": \"common.v1.config.IPAddress\", \"ipv4\": {\"2026-09-20T14:30:00.000Zreserved\": {\"2026-09-20T14:30:00.000Zfv\": \"v1.r0\"}, \"2026-09-20T14:30:00.000ZobjectType\": \"common.v1.config.IPv4Address\", \"value\": \"10.0.4.130\", \"prefixLength\": 32}}, \"nodeIpAddress\": {\"2026-09-20T14:30:00.000Zreserved\": {\"2026-09-20T14:30:00.000Zfv\": \"v1.r0\"}, \"2026-09-20T14:30:00.000ZobjectType\": \"common.v1.config.IPAddress\", \"ipv4\": {\"2026-09-20T14:30:00.000Zreserved\": {\"2026-09-20T14:30:00.000Zfv\": \"v1.r0\"}, \"2026-09-20T14:30:00.000ZobjectType\": \"common.v1.config.IPv4Address\", \"value\": \"10.0.4.143\", \"prefixLength\": 32}}, \"diskAdvanceConfig\": {\"2026-09-20T14:30:00.000Zreserved\": {\"2026-09-20T14:30:00.000Zfv\": \"v4.r0\"}, \"2026-09-20T14:30:00.000ZobjectType\": \"clustermgmt.v4.config.DiskAdvanceConfig\", \"isSelfEncryptingDrive\": false, \"isSelfManagedNvme\": false, \"isBootDisk\": false, \"hasBootPartitionsOnly\": false, \"isSpdkManaged\": false, \"isOnline\": true, \"isMarkedForRemoval\": false, \"isDataMigrated\": false, \"isUnhealthy\": false, \"isSuspectedUnhealthy\": false, \"isMounted\": true, \"isUnderDiagnosis\": false, \"isDiagnosticInfoAvailable\": false, \"isErrorFoundInLog\": false, \"isPlannedOutage\": false}}"
  },
  {
    "id": "nutanixpc_events",
    "label": "Nutanixpc Events",
    "vendor": "nutanix",
    "category": "Nutanix PC",
    "index": "netops_logs",
    "sample": "{\"2026-09-20T14:30:00.000Zreserved\": {\"2026-09-20T14:30:00.000Zfv\": \"v4.r0\"}, \"2026-09-20T14:30:00.000ZobjectType\": \"monitoring.v4.serviceability.Event\", \"extId\": \"ee77555c-a7ef-4358-864f-43295cd62561\", \"eventType\": \"IAMAdministrationEventAudit\", \"classifications\": [\"UserAction\"], \"sourceClusterUUID\": \"8ae8575f-53ab-4152-a483-d6fc980bd4cc\", \"creationTime\": \"2026-09-20T14:30:00.000ZISO_TIMESTAMP2026-09-20T14:30:00.000Z\", \"message\": \"User admin granted permission to [(''Health_Check_Remote_Connection'',)] on remote_connection with attributes {''type'': ''remote_connection''} from \", \"clusterUUID\": \"8ae8575f-53ab-4152-a483-d6fc980bd4cc\", \"parameters\": [{\"paramValue\": {\"2026-09-20T14:30:00.000Zreserved\": {\"2026-09-20T14:30:00.000Zfv\": \"v4.r0\"}, \"2026-09-20T14:30:00.000ZobjectType\": \"monitoring.v4.common.StringValue\"}, \"2026-09-20T14:30:00.000Zreserved\": {\"2026-09-20T14:30:00.000Zfv\": \"v4.r0\"}, \"2026-09-20T14:30:00.000ZobjectType\": \"monitoring.v4.common.Parameter\", \"paramName\": \"ip_address\"}, {\"paramValue\": {\"2026-09-20T14:30:00.000Zreserved\": {\"2026-09-20T14:30:00.000Zfv\": \"v4.r0\"}, \"2026-09-20T14:30:00.000ZobjectType\": \"monitoring.v4.common.StringValue\", \"stringValue\": \"admin\"}, \"paramName\": \"audit_user\"}]}"
  },
  {
    "id": "nutanixpc_host_performance",
    "label": "Nutanixpc Host Performance",
    "vendor": "nutanix",
    "category": "Nutanix PC",
    "index": "cisco_mdt_metrics",
    "sample": "{\"timestamp\": \"2026-09-20T14:30:00.000ZISO_TIMESTAMP2026-09-20T14:30:00.000Z\", \"extId\": \"dc8562d0-9e55-4b4e-8bba-9f2e123dc411\", \"controllerAvgIoLatencyUsecs\": 3891, \"controllerAvgReadIoLatencyUsecs\": 768, \"controllerAvgWriteIoLatencyUsecs\": 3892, \"controllerNumIops\": 173, \"controllerNumReadIops\": 0, \"controllerNumWriteIops\": 173, \"ioBandwidthKbps\": 18671, \"controllerReadIoBandwidthKbps\": 0, \"controllerWriteIoBandwidthKbps\": 18670, \"hypervisorCpuUsagePpm\": 929754, \"aggregateHypervisorMemoryUsagePpm\": 872223, \"storageUsageBytes\": 2484247200782, \"storageCapacityBytes\": 10326957305327, \"freePhysicalStorageBytes\": 7842710104545, \"memoryCapacityBytes\": 0, \"cpuCapacityHz\": 0, \"overollMemoryUsagePpm\": 0}"
  },
  {
    "id": "nutanixpc_hosts",
    "label": "Nutanixpc Hosts",
    "vendor": "nutanix",
    "category": "Nutanix PC",
    "index": "netops_logs",
    "sample": "{\"2026-09-20T14:30:00.000Zreserved\": {\"2026-09-20T14:30:00.000Zfv\": \"v4.r0\"}, \"2026-09-20T14:30:00.000ZobjectType\": \"clustermgmt.v4.config.Host\", \"extId\": \"dc8562d0-9e55-4b4e-8bba-9f2e123dc411\", \"hostName\": \"CCHCI-AHV-04\", \"hostType\": \"HYPER_CONVERGED\", \"hypervisor\": {\"2026-09-20T14:30:00.000Zreserved\": {\"2026-09-20T14:30:00.000Zfv\": \"v4.r0\"}, \"2026-09-20T14:30:00.000ZobjectType\": \"clustermgmt.v4.config.HypervisorReference\", \"externalAddress\": {\"2026-09-20T14:30:00.000Zreserved\": {\"2026-09-20T14:30:00.000Zfv\": \"v1.r0\"}, \"2026-09-20T14:30:00.000ZobjectType\": \"common.v1.config.IPAddress\", \"ipv4\": {\"2026-09-20T14:30:00.000Zreserved\": {\"2026-09-20T14:30:00.000Zfv\": \"v1.r0\"}, \"2026-09-20T14:30:00.000ZobjectType\": \"common.v1.config.IPv4Address\", \"value\": \"10.0.4.116\", \"prefixLength\": 32}}, \"userName\": \"root\", \"fullName\": \"Nutanix 20230302.103053\", \"type\": \"AHV\", \"numberOfVms\": 5, \"state\": \"ACROPOLIS_NORMAL\", \"acropolisConnectionState\": \"CONNECTED\"}, \"cluster\": {\"name\": \"Fab1-CCHCI-AHV\", \"2026-09-20T14:30:00.000Zreserved\": {\"2026-09-20T14:30:00.000Zfv\": \"v4.r0\"}, \"2026-09-20T14:30:00.000ZobjectType\": \"clustermgmt.v4.config.ClusterReference\", \"uuid\": \"00063ffb-2c0b-2e6c-7635-0025b500010e\"}, \"controllerVm\": {\"2026-09-20T14:30:00.000Zreserved\": {\"2026-09-20T14:30:00.000Zfv\": \"v4.r0\"}, \"2026-09-20T14:30:00.000ZobjectType\": \"clustermgmt.v4.config.ControllerVmReference\", \"externalAddress\": {\"2026-09-20T14:30:00.000Zreserved\": {\"2026-09-20T14:30:00.000Zfv\": \"v1.r0\"}, \"2026-09-20T14:30:00.000ZobjectType\": \"common.v1.config.IPAddress\", \"ipv4\": {\"2026-09-20T14:30:00.000Zreserved\": {\"2026-09-20T14:30:00.000Zfv\": \"v1.r0\"}, \"2026-09-20T14:30:00.000ZobjectType\": \"common.v1.config.IPv4Address\", \"value\": \"10.0.4.126\", \"prefixLength\": 32}}, \"backplaneAddress\": {\"2026-09-20T14:30:00.000Zreserved\": {\"2026-09-20T14:30:00.000Zfv\": \"v1.r0\"}, \"2026-09-20T14:30:00.000ZobjectType\": \"common.v1.config.IPAddress\", \"ipv4\": {\"2026-09-20T14:30:00.000Zreserved\": {\"2026-09-20T14:30:00.000Zfv\": \"v1.r0\"}, \"2026-09-20T14:30:00.000ZobjectType\": \"common.v1.config.IPv4Address\", \"value\": \"10.0.4.126\", \"prefixLength\": 32}}}, \"disk\": [{\"2026-09-20T14:30:00.000Zreserved\": {\"2026-09-20T14:30:00.000Zfv\": \"v4.r0\"}, \"2026-09-20T14:30:00.000ZobjectType\": \"clustermgmt.v4.config.DiskReference\", \"uuid\": \"605e3e96-6b22-49c5-8dd2-6d7c68571272\", \"mountPath\": \"/home/nutanix/data/stargate-storage/disks/S5MPNA0N901950\", \"sizeInBytes\": 3535141351649, \"serialId\": \"S5MPNA0N901950\", \"storageTier\": \"SATA_SSD\"}, {\"uuid\": \"a1695dac-ab6f-4918-9383-eb6672d8e4de\", \"mountPath\": \"/home/nutanix/data/stargate-storage/disks/S5MPNA0N901920\", \"sizeInBytes\": 3395907976839, \"serialId\": \"S5MPNA0N901920\", \"storageTier\": \"SATA_SSD\"}, {\"uuid\": \"01c04f9e-d3ac-4829-b112-a096edd28afd\", \"mountPath\": \"/home/nutanix/data/stargate-storage/disks/S5MPNA0N901919\", \"sizeInBytes\": 3395907976839, \"serialId\": \"S5MPNA0N901919\", \"storageTier\": \"SATA_SSD\"}], \"isSecureBooted\": false, \"isHardwareVirtualized\": false, \"hasCsr\": false, \"numberOfCpuCores\": 16, \"numberOfCpuThreads\": 32, \"numberOfCpuSockets\": 1, \"cpuFrequencyHz\": 2900000000, \"cpuModel\": \"Intel(R) Xeon(R) Gold 6226R CPU @ 2.90GHz\", \"bootTimeUsecs\": 1782412221171302, \"memorySizeBytes\": 403605291008, \"blockSerial\": \"WMP244201AR\", \"blockModel\": \"Cisco Demo C220-M5SX\", \"maintenanceState\": \"normal\", \"nodeStatus\": \"NORMAL\", \"ipmi\": {\"2026-09-20T14:30:00.000Zreserved\": {\"2026-09-20T14:30:00.000Zfv\": \"v4.r0\"}, \"2026-09-20T14:30:00.000ZobjectType\": \"clustermgmt.v4.config.IpmiReference\", \"ip\": {\"2026-09-20T14:30:00.000Zreserved\": {\"2026-09-20T14:30:00.000Zfv\": \"v1.r0\"}, \"2026-09-20T14:30:00.000ZobjectType\": \"common.v1.config.IPAddress\"}, \"username\": \"ADMIN\"}, \"rackableUnitUuid\": \"67b5323a-ce1c-468a-b3b0-828b0d557d27\"}"
  },
  {
    "id": "nutanixpc_prismCentrals",
    "label": "Nutanixpc Prismcentrals",
    "vendor": "nutanix",
    "category": "Nutanix PC",
    "index": "netops_logs",
    "sample": "{\"2026-09-20T14:30:00.000Zreserved\": {\"2026-09-20T14:30:00.000Zfv\": \"v4.r0\"}, \"2026-09-20T14:30:00.000ZobjectType\": \"clustermgmt.v4.config.Cluster\", \"extId\": \"8ae8575f-53ab-4152-a483-d6fc980bd4cc\", \"name\": \"CCHCI-PC\", \"nodes\": {\"numberOfNodes\": 1, \"2026-09-20T14:30:00.000Zreserved\": {\"2026-09-20T14:30:00.000Zfv\": \"v4.r0\"}, \"2026-09-20T14:30:00.000ZobjectType\": \"clustermgmt.v4.config.NodeReference\", \"nodeList\": [{\"nodeUuid\": \"9126a468-46ed-4f3a-af0e-82de8185335c\", \"2026-09-20T14:30:00.000Zreserved\": {\"2026-09-20T14:30:00.000Zfv\": \"v4.r0\"}, \"2026-09-20T14:30:00.000ZobjectType\": \"clustermgmt.v4.config.NodeListItemReference\", \"controllerVmIp\": {\"2026-09-20T14:30:00.000Zreserved\": {\"2026-09-20T14:30:00.000Zfv\": \"v1.r0\"}, \"2026-09-20T14:30:00.000ZobjectType\": \"common.v1.config.IPAddress\", \"ipv4\": {\"2026-09-20T14:30:00.000Zreserved\": {\"2026-09-20T14:30:00.000Zfv\": \"v1.r0\"}, \"2026-09-20T14:30:00.000ZobjectType\": \"common.v1.config.IPv4Address\", \"value\": \"10.0.4.120\", \"prefixLength\": 32}}}]}, \"config\": {\"incarnationId\": 785974201913393490, \"hypervisorTypes\": [\"2026-09-20T14:30:00.000ZUNKNOWN\"], \"timezone\": \"America/Los_Angeles\", \"clusterSoftwareMap\": [{\"2026-09-20T14:30:00.000Zreserved\": {\"2026-09-20T14:30:00.000Zfv\": \"v4.r0\"}, \"2026-09-20T14:30:00.000ZobjectType\": \"clustermgmt.v4.config.SoftwareMapReference\", \"softwareType\": \"NCC\", \"version\": \"ncc-5.1.1\"}, {\"softwareType\": \"PRISM_CENTRAL\", \"version\": \"el8.5-release-fraser-2024.3.1.1-stable-65c1d82b97162bf232e5453e933f1a84ed1db2f6\"}], \"isRemoteSupportEnabled\": false, \"isLts\": false, \"isAvailable\": true, \"2026-09-20T14:30:00.000Zreserved\": {\"2026-09-20T14:30:00.000Zfv\": \"v4.r0\"}, \"2026-09-20T14:30:00.000ZobjectType\": \"clustermgmt.v4.config.ClusterConfigReference\", \"buildInfo\": {\"2026-09-20T14:30:00.000Zreserved\": {\"2026-09-20T14:30:00.000Zfv\": \"v4.r0\"}, \"2026-09-20T14:30:00.000ZobjectType\": \"clustermgmt.v4.config.BuildReference\", \"buildType\": \"release\", \"version\": \"2024.3\", \"fullVersion\": \"el8.5-release-fraser-2024.3.1.1-stable-65c1d82b97162bf232e5453e933f1a84ed1db2f6\", \"commitId\": \"65c1d82b97162bf232e5453e933f1a84ed1db2f6\", \"shortCommitId\": \"65c1d8\"}, \"clusterFunction\": [\"PRISM_CENTRAL\"], \"authorizedPublicKeyList\": [{\"2026-09-20T14:30:00.000Zreserved\": {\"2026-09-20T14:30:00.000Zfv\": \"v4.r0\"}, \"2026-09-20T14:30:00.000ZobjectType\": \"clustermgmt.v4.config.PublicKey\", \"name\": \"9126a468-46ed-4f3a-af0e-82de8185335c\", \"key\": \"ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDQHooMhsOBQNcLXx8yP9u2RI2o35Lng+jIEquNio6aOoEo5erdKMck2rM/Z/t8NgH0uNrOd8oM+paEqjTWh/6v/AfETYbp8YZEEU6riQUh2glINczKQLp6I93LGcqF+JehgO9SkhFsGbIe6GibuwC1umwLcQj2aBt5swmiKCzNgT/aRGni6P9TR0/r/uH6RANTJTzZdcqozOXirK4yY/v7LCvt5Bm7Bz4VjOARak3VcGi21wwPTB5T577MlktCDe7SJZxqqINXWR6QGs7AprjAASz95H/RRgqSpv7uIfaS/Y4Zp1J2Pr7Nic7ZF/Luybt6qiTPFI/lx5TMpPgJVf3V nutanix@ntnx-10-0-4-120-a-pcvm\"}], \"redundancyFactor\": 1, \"clusterArch\": \"X86_64\", \"faultToleranceState\": {\"currentMaxFaultTolerance\": 0, \"desiredMaxFaultTolerance\": 0, \"2026-09-20T14:30:00.000Zreserved\": {\"2026-09-20T14:30:00.000Zfv\": \"v4.r0\"}, \"2026-09-20T14:30:00.000ZobjectType\": \"clustermgmt.v4.config.FaultToleranceState\", \"domainAwarenessLevel\": \"NODE\", \"currentClusterFaultTolerance\": \"CFT_0N_AND_0D\", \"desiredClusterFaultTolerance\": \"CFT_0N_AND_0D\"}, \"pulseStatus\": {\"2026-09-20T14:30:00.000Zreserved\": {\"2026-09-20T14:30:00.000Zfv\": \"v4.r0\"}, \"2026-09-20T14:30:00.000ZobjectType\": \"clustermgmt.v4.config.PulseStatus\", \"isEnabled\": false}}, \"network\": {\"externalSubnet\": \"10.0.4.0/255.255.255.0\", \"internalSubnet\": \"10.0.4.0/255.255.255.0\", \"2026-09-20T14:30:00.000Zreserved\": {\"2026-09-20T14:30:00.000Zfv\": \"v4.r0\"}, \"2026-09-20T14:30:00.000ZobjectType\": \"clustermgmt.v4.config.ClusterNetworkReference\", \"externalAddress\": {\"2026-09-20T14:30:00.000Zreserved\": {\"2026-09-20T14:30:00.000Zfv\": \"v1.r0\"}, \"2026-09-20T14:30:00.000ZobjectType\": \"common.v1.config.IPAddress\"}, \"externalDataServiceIp\": {\"2026-09-20T14:30:00.000Zreserved\": {\"2026-09-20T14:30:00.000Zfv\": \"v1.r0\"}, \"2026-09-20T14:30:00.000ZobjectType\": \"common.v1.config.IPAddress\"}, \"nameServerIpList\": [{\"2026-09-20T14:30:00.000Zreserved\": {\"2026-09-20T14:30:00.000Zfv\": \"v1.r0\"}, \"2026-09-20T14:30:00.000ZobjectType\": \"common.v1.config.IPAddressOrFQDN\", \"ipv4\": {\"2026-09-20T14:30:00.000Zreserved\": {\"2026-09-20T14:30:00.000Zfv\": \"v1.r0\"}, \"2026-09-20T14:30:00.000ZobjectType\": \"common.v1.config.IPv4Address\", \"value\": \"127.0.0.1\", \"prefixLength\": 32}}, {\"ipv4\": {\"2026-09-20T14:30:00.000Zreserved\": {\"2026-09-20T14:30:00.000Zfv\": \"v1.r0\"}, \"2026-09-20T14:30:00.000ZobjectType\": \"common.v1.config.IPv4Address\", \"value\": \"10.0.10.201\", \"prefixLength\": 32}}, {\"ipv4\": {\"2026-09-20T14:30:00.000Zreserved\": {\"2026-09-20T14:30:00.000Zfv\": \"v1.r0\"}, \"2026-09-20T14:30:00.000ZobjectType\": \"common.v1.config.IPv4Address\", \"value\": \"10.0.10.202\", \"prefixLength\": 32}}], \"ntpServerIpList\": [{\"2026-09-20T14:30:00.000Zreserved\": {\"2026-09-20T14:30:00.000Zfv\": \"v1.r0\"}, \"2026-09-20T14:30:00.000ZobjectType\": \"common.v1.config.IPAddressOrFQDN\", \"ipv4\": {\"2026-09-20T14:30:00.000Zreserved\": {\"2026-09-20T14:30:00.000Zfv\": \"v1.r0\"}, \"2026-09-20T14:30:00.000ZobjectType\": \"common.v1.config.IPv4Address\", \"value\": \"10.0.0.252\", \"prefixLength\": 32}}, {\"ipv4\": {\"2026-09-20T14:30:00.000Zreserved\": {\"2026-09-20T14:30:00.000Zfv\": \"v1.r0\"}, \"2026-09-20T14:30:00.000ZobjectType\": \"common.v1.config.IPv4Address\", \"value\": \"10.0.0.253\", \"prefixLength\": 32}}], \"backplane\": {\"2026-09-20T14:30:00.000Zreserved\": {\"2026-09-20T14:30:00.000Zfv\": \"v4.r0\"}, \"2026-09-20T14:30:00.000ZobjectType\": \"clustermgmt.v4.config.BackplaneNetworkParams\", \"isSegmentationEnabled\": false}}, \"pc_ip\": \"10.0.4.120\"}"
  },
  {
    "id": "nutanixpc_storage_containers",
    "label": "Nutanixpc Storage Containers",
    "vendor": "nutanix",
    "category": "Nutanix PC",
    "index": "netops_logs",
    "sample": "{\"2026-09-20T14:30:00.000Zreserved\": {\"2026-09-20T14:30:00.000Zfv\": \"v4.r0\"}, \"2026-09-20T14:30:00.000ZobjectType\": \"clustermgmt.v4.config.StorageContainer\", \"links\": [{\"2026-09-20T14:30:00.000Zreserved\": {\"2026-09-20T14:30:00.000Zfv\": \"v1.r0\"}, \"2026-09-20T14:30:00.000ZobjectType\": \"common.v1.response.ApiLink\", \"href\": \"2026-09-20T14:30:00.000ZHOST2026-09-20T14:30:00.000Z/f8edb45b-13e1-4927-954c-b0c3f1c91a33\", \"rel\": \"storage-container\"}, {\"href\": \"https://10.0.4.120:9440/api/clustermgmt/v4.0/stats/storage-containers/f8edb45b-13e1-4927-954c-b0c3f1c91a33\", \"rel\": \"storage-container-stats\"}], \"clusterExtId\": \"00063ffb-2c0b-2e6c-7635-0025b500010e\", \"storagePoolExtId\": \"3d2e376e-5978-474c-b4f4-a11dd814a4f8\", \"isMarkedForRemoval\": false, \"markedForRemoval\": false, \"maxCapacityBytes\": 25636192153091, \"logicalImplicitReservedCapacityBytes\": 0, \"isNfsWhitelistInherited\": true, \"clusterName\": \"Fab1-CCHCI-AHV\", \"containerExtId\": \"f8edb45b-13e1-4927-954c-b0c3f1c91a33\", \"ownerExtId\": \"00000000-0000-0000-0000-000000000000\", \"name\": \"default-container-62746583239497\", \"logicalExplicitReservedCapacityBytes\": 0, \"replicationFactor\": 2, \"erasureCode\": \"OFF\", \"isInlineEcEnabled\": false, \"hasHigherEcFaultDomainPreference\": true, \"cacheDeduplication\": \"OFF\", \"onDiskDedup\": \"POST_PROCESS\", \"isCompressionEnabled\": true, \"compressionDelaySecs\": 3600, \"isInternal\": false, \"isSoftwareEncryptionEnabled\": false}"
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
    "sample": "{\"timestamp\": \"2026-09-20T14:30:00.000ZISO_TIMESTAMP2026-09-20T14:30:00.000Z\", \"cluster\": \"00061768-f76f-4f95-3e5f-0025b500016f\", \"hypervisorType\": \"kVMware\", \"memoryReservedBytes\": \"\", \"extId\": \"ca90dbd8-ccdf-4525-8dd2-3c8c1c842262\", \"controllerAvgIoLatencyMicros\": 1941, \"controllerAvgReadIoLatencyMicros\": 0, \"controllerAvgReadIoSizeKb\": 0, \"controllerAvgWriteIoLatencyMicros\": 1941, \"controllerAvgWriteIoSizeKb\": 4, \"controllerIoBandwidthKbps\": 42, \"controllerNumIo\": 176, \"controllerNumIops\": 8, \"controllerNumReadIo\": 0, \"controllerNumReadIops\": 0, \"controllerNumWriteIo\": 176, \"controllerNumWriteIops\": 8, \"controllerOplogDrainDestHddBytes\": 0, \"controllerOplogDrainDestSsdBytes\": 0, \"controllerReadIoBandwidthKbps\": 0, \"controllerReadIoPpm\": 0, \"controllerReadSourceEstoreHddLocalBytes\": 0, \"controllerReadSourceEstoreSsdLocalBytes\": 0, \"controllerReadSourceEstoreHddRemoteBytes\": 0, \"controllerReadSourceEstoreSsdRemoteBytes\": 0, \"controllerReadSourceOplogBytes\": 0, \"controllerSharedUsageBytes\": 0, \"controllerSnapshotUsageBytes\": 0, \"controllerStorageTierSsdUsageBytes\": 122976747520, \"controllerTimespanMicros\": 20000000, \"controllerTotalIoSizeKb\": 852, \"controllerTotalIoTimeMicros\": 341638, \"controllerTotalReadIoSizeKb\": 0, \"controllerTotalReadIoTimeMicros\": 0, \"controllerTotalTransformedUsageBytes\": 0, \"controllerUserBytes\": 29835442176, \"controllerWriteDestEstoreSsdBytes\": 0, \"controllerWriteDestEstoreHddBytes\": 0, \"controllerWriteIoBandwidthKbps\": 42, \"controllerWriteIoPpm\": 1000000, \"controllerWss120SecondUnionMb\": 0, \"controllerWss120SecondReadMb\": 0, \"controllerWss120SecondWriteMb\": 0, \"controllerWss3600SecondUnionMb\": 0, \"controllerWss3600SecondReadMb\": 0, \"controllerWss3600SecondWriteMb\": 0, \"guestMemoryUsagePpm\": 0, \"hypervisorAvgIoLatencyMicros\": 3000, \"hypervisorCpuReadyTimePpm\": 118, \"hypervisorCpuUsagePpm\": 800, \"hypervisorIoBandwidthKbps\": 65, \"hypervisorMemoryUsagePpm\": 9900, \"hypervisorNumIo\": 360, \"hypervisorNumIops\": 12, \"hypervisorNumReadIops\": 0, \"hypervisorNumReadIo\": 0, \"hypervisorNumReceivedBytes\": 0, \"hypervisorNumReceivePacketsDropped\": 0, \"hypervisorNumTransmittedBytes\": 0, \"hypervisorNumTransmitPacketsDropped\": 0, \"hypervisorNumWriteIo\": 360, \"hypervisorNumWriteIops\": 12, \"hypervisorReadIoBandwidthKbps\": 0, \"hypervisorTimespanMicros\": 30000000, \"hypervisorTotalIoSizeKb\": 1950, \"hypervisorTotalIoTimeMicros\": 1080000, \"hypervisorTotalReadIoSizeKb\": 0, \"hypervisorVmRunningTimeUsecs\": 0, \"hypervisorWriteIoBandwidthKbps\": 65, \"memoryUsagePpm\": 9900, \"numVcpusUsedPpm\": 0, \"diskUsagePpm\": 0, \"diskCapacityBytes\": 0}"
  },
  {
    "id": "nutanixpc_vms",
    "label": "Nutanixpc Vms",
    "vendor": "nutanix",
    "category": "Nutanix PC",
    "index": "netops_logs",
    "sample": "{\"timestamp\":\"2026-09-20T14:30:00.000Z\",\"vm_name\":\"app-server-prod-04\",\"vm_uuid\":\"e4d2a1b9-c8f7-4a02-b2d9-123456789abc\",\"cluster_name\":\"Prism-Prod-01\",\"power_state\":\"ON\",\"cpu_cores\":8,\"memory_gb\":32,\"cpu_usage_pct\":42.5,\"memory_usage_pct\":68.2,\"disk_read_iops\":1250,\"disk_write_iops\":480,\"status\":\"NORMAL\"}"
  },
  {
    "id": "nutanixpc_volume_groups",
    "label": "Nutanixpc Volume Groups",
    "vendor": "nutanix",
    "category": "Nutanix PC",
    "index": "netops_logs",
    "sample": "{\"2026-09-20T14:30:00.000Zreserved\": {\"2026-09-20T14:30:00.000Zfv\": \"v4.r0\"}, \"2026-09-20T14:30:00.000ZobjectType\": \"volumes.v4.config.VolumeGroup\", \"extId\": \"a8589f1c-3418-4e4c-9c55-109eeb10c261\", \"links\": [{\"2026-09-20T14:30:00.000Zreserved\": {\"2026-09-20T14:30:00.000Zfv\": \"v1.r0\"}, \"2026-09-20T14:30:00.000ZobjectType\": \"common.v1.response.ApiLink\", \"href\": \"2026-09-20T14:30:00.000ZHOST2026-09-20T14:30:00.000Z/a8589f1c-3418-4e4c-9c55-109eeb10c261\", \"rel\": \"volume_group\"}], \"name\": \"pvc-8934bad9-c9ba-4490-81b3-04c4ee83d857\", \"description\": \"FS:ext4, PVC:anc-mysql-certs, NS:default, POD:anc-mysql-0, SA:default\", \"shouldLoadBalanceVmAttachments\": false, \"sharingStatus\": \"SHARED\", \"targetName\": \"ntnx-k8s-a8589f1c-3418-4e4c-9c55-109eeb10c261\", \"clusterReference\": \"00061768-f76f-4f95-3e5f-0025b500016f\", \"storageFeatures\": {\"2026-09-20T14:30:00.000Zreserved\": {\"2026-09-20T14:30:00.000Zfv\": \"v4.r0\"}, \"2026-09-20T14:30:00.000ZobjectType\": \"volumes.v4.config.StorageFeatures\", \"flashMode\": {\"2026-09-20T14:30:00.000Zreserved\": {\"2026-09-20T14:30:00.000Zfv\": \"v4.r0\"}, \"2026-09-20T14:30:00.000ZobjectType\": \"volumes.v4.config.FlashMode\", \"isEnabled\": false}}, \"usageType\": \"INTERNAL\", \"isHidden\": true}"
  },
  {
    "id": "nutanixpc:syslog",
    "label": "Nutanix Prism Central Syslog (Colon Format)",
    "vendor": "nutanix",
    "category": "Nutanix PC",
    "index": "idx_performance_metrics",
    "sample": "May 20 14:00:24 nutanix-pc-01 cluster: %ALERT-3-HOST_HA_DEGRADED: Node 10.20.0.12 in cluster \\\"Prism-Prod-01\\\" uncontactable by Acropolis Leader. HA failover initiated."
  },
  {
    "id": "nutanixpc:vms",
    "label": "Nutanix Prism Central VM Inventory (Colon Format)",
    "vendor": "nutanix",
    "category": "Nutanix PC",
    "index": "idx_performance_metrics",
    "sample": "{\\\"vm_name\\\": \\\"app-server-prod-04\\\", \\\"vm_uuid\\\": \\\"e4d2a1b9-c8f7-4820-9948-201849201849\\\", \\\"cluster_name\\\": \\\"Prism-Prod-01\\\", \\\"power_state\\\": \\\"ON\\\", \\\"memory_capacity_mb\\\": 65536, \\\"memory_usage_ppm\\\": 784000, \\\"num_vcpus\\\": 16, \\\"cpu_usage_ppm\\\": 342000, \\\"ip_addresses\\\": [\\\"10.20.12.45\\\"]}"
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
    "sample": "{\"level\":\"info\",\"ts\":\"2026-09-20T14:30:00.000ZISO_TIMESTAMP2026-09-20T14:30:00.000Z\",\"logger\":\"cert-rotation\",\"msg\":\"Ensuring CA cert\",\"name\":\"bgppeers.metallb.io\",\"gvk\":\"apiextensions.k8s.io/v1, Kind=CustomResourceDefinition\",\"name\":\"bgppeers.metallb.io\",\"gvk\":\"apiextensions.k8s.io/v1, Kind=CustomResourceDefinition\",\"stacktrace\":\"github.com/open-policy-agent/cert-controller/pkg/rotator.(*ReconcileWH).ensureCerts\\n\\t/go/pkg/mod/github.com/open-policy-agent/cert-controller@v0.10.2-0.20240531181455-2649f121ab97/pkg/rotator/rotator.go:827\\ngithub.com/open-policy-agent/cert-controller/pkg/rotator.(*ReconcileWH).Reconcile\\n\\t/go/pkg/mod/github.com/open-policy-agent/cert-controller@v0.10.2-0.20240531181455-2649f121ab97/pkg/rotator/rotator.go:784\\nsigs.k8s.io/controller-runtime/pkg/internal/controller.(*Controller[...]).Reconcile\\n\\t/go/pkg/mod/sigs.k8s.io/controller-runtime@v0.19.3/pkg/internal/controller/controller.go:116\\nsigs.k8s.io/controller-runtime/pkg/internal/controller.(*Controller[...]).reconcileHandler\\n\\t/go/pkg/mod/sigs.k8s.io/controller-runtime@v0.19.3/pkg/internal/controller/controller.go:303\\nsigs.k8s.io/controller-runtime/pkg/internal/controller.(*Controller[...]).processNextWorkItem\\n\\t/go/pkg/mod/sigs.k8s.io/controller-runtime@v0.19.3/pkg/internal/controller/controller.go:263\\nsigs.k8s.io/controller-runtime/pkg/internal/controller.(*Controller[...]).Start.func2.2\\n\\t/go/pkg/mod/sigs.k8s.io/controller-runtime@v0.19.3/pkg/internal/controller/controller.go:224\"}"
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
    "sample": "level=info ts=2026-09-20T14:30:00.000ZISO_TIMESTAMP2026-09-20T14:30:00.000Z caller=tls_config.go:316 msg=\"TLS is disabled.\" http2=false address=[::]:9216"
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
    "sample": "10.0.10.104 - - [18/Sep/2026:17:34:40 +0000] \"GET / HTTP/1.1\" 200 112 \"-\" \"kube-probe/1.33\" \"-\""
  },
  {
    "id": "kube:container:mongodb",
    "label": "Kube Container Mongodb",
    "vendor": "k8s",
    "category": "Kubernetes Containers",
    "index": "netops_logs",
    "sample": "{\"t\":{\"2026-09-20T14:30:00.000Zdate\":\"2026-09-20T14:30:00.000ZISO_TIMESTAMP2026-09-20T14:30:00.000Z\"},\"s\":\"I\",  \"c\":\"NETWORK\",  \"id\":22944,   \"ctx\":\"conn1056316\",\"msg\":\"Connection ended\",\"attr\":{\"remote\":\"127.0.0.1:46412\",\"uuid\":{\"uuid\":{\"2026-09-20T14:30:00.000Zuuid\":\"84987fc8-3103-4265-ad17-df1ea9c7e8f4\"}},\"connectionId\":1056316,\"connectionCount\":57}}"
  },
  {
    "id": "kube:container:redis",
    "label": "Kube Container Redis",
    "vendor": "k8s",
    "category": "Kubernetes Containers",
    "index": "netops_logs",
    "sample": "1:M 02 2026-09-20T14:30:00.000ZSYSLOG_TIMESTAMP2026-09-20T14:30:00.000Z.400 * Ready to accept connections tcp"
  },
  {
    "id": "kube:container:speaker",
    "label": "Kube Container Speaker",
    "vendor": "k8s",
    "category": "Kubernetes Containers",
    "index": "netops_logs",
    "sample": "{\"caller\":\"layer2_status_controller.go:111\",\"controller\":\"Layer2StatusReconciler\",\"end reconcile\":\"sc4snmp/snmp-splunk-connect-for-snmp-trap\",\"level\":\"info\",\"ts\":\"2026-09-20T14:30:00.000ZISO_TIMESTAMP2026-09-20T14:30:00.000Z\"}"
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
    "sample": "2026-09-02 10:13:21.421 [INFO][1] ipam/ipam_plugin.go 100: migration from host-local to calico-ipam complete node=\"maple-splunk-vm4-hf\""
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
    "sample": "{\"apiVersion\":\"v1\",\"kind\":\"Pod\",\"metadata\":{\"annotations\":{\"cni.projectcalico.org/containerID\":\"96bd3467252947d40fa4395800e49066dee4c94fc5c66d39080fdd7767725252\",\"cni.projectcalico.org/podIP\":\"10.1.5.238/32\",\"cni.projectcalico.org/podIPs\":\"10.1.5.238/32\"},\"creationTimestamp\":\"2026-09-20T14:30:00.000ZISO_TIMESTAMP2026-09-20T14:30:00.000Z\",\"generateName\":\"snmp-splunk-connect-for-snmp-worker-trap-56dd75bf88-\",\"generation\":1,\"labels\":{\"app.kubernetes.io/instance\":\"snmp\",\"app.kubernetes.io/name\":\"splunk-connect-for-snmp-worker-trap\",\"pod-template-hash\":\"56dd75bf88\"},\"managedFields\":[{\"apiVersion\":\"v1\",\"fieldsType\":\"FieldsV1\",\"fieldsV1\":{\"f:metadata\":{\"f:generateName\":{},\"f:labels\":{\".\":{},\"f:app.kubernetes.io/instance\":{},\"f:app.kubernetes.io/name\":{},\"f:pod-template-hash\":{}},\"f:ownerReferences\":{\".\":{},\"k:{\\\"uid\\\":\\\"b1613111-daeb-4dbd-94d2-5dc038838011\\\"}\":{}}},\"f:spec\":{\"f:affinity\":{\".\":{},\"f:podAntiAffinity\":{\".\":{},\"f:preferredDuringSchedulingIgnoredDuringExecution\":{}}},\"f:containers\":{\"k:{\\\"name\\\":\\\"splunk-connect-for-snmp-worker-trap\\\"}\":{\".\":{},\"f:args\":{},\"f:env\":{\".\":{},\"k:{\\\"name\\\":\\\"CELERY_BROKER_URL\\\"}\":{\".\":{},\"f:name\":{},\"f:value\":{}},\"k:{\\\"name\\\":\\\"CONFIG_PATH\\\"}\":{\".\":{},\"f:name\":{},\"f:value\":{}},\"k:{\\\"name\\\":\\\"DISABLE_MONGO_DEBUG_LOGGING\\\"}\":{\".\":{},\"f:name\":{},\"f:value\":{}},\"k:{\\\"name\\\":\\\"IGNORE_EMPTY_VARBINDS\\\"}\":{\".\":{},\"f:name\":{},\"f:value\":{}},\"k:{\\\"name\\\":\\\"IPv6_ENABLED\\\"}\":{\".\":{},\"f:name\":{},\"f:value\":{}},\"k:{\\\"name\\\":\\\"LOG_LEVEL\\\"}\":{\".\":{},\"f:name\":{},\"f:value\":{}},\"k:{\\\"name\\\":\\\"MAX_DNS_CACHE_SIZE_TRAPS\\\"}\":{\".\":{},\"f:name\":{},\"f:value\":{}},\"k:{\\\"name\\\":\\\"MAX_OID_TO_PROCESS\\\"}\":{\".\":{},\"f:name\":{},\"f:value\":{}},\"k:{\\\"name\\\":\\\"MAX_REPETITIONS\\\"}\":{\".\":{},\"f:name\":{},\"f:value\":{}},\"k:{\\\"name\\\":\\\"METRICS_INDEXING_ENABLED\\\"}\":{\".\":{},\"f:name\":{},\"f:value\":{}},\"k:{\\\"name\\\":\\\"MIB_INDEX\\\"}\":{\".\":{},\"f:name\":{},\"f:value\":{}},\"k:{\\\"name\\\":\\\"MIB_SOURCES\\\"}\":{\".\":{},\"f:name\":{},\"f:value\":{}},\"k:{\\\"name\\\":\\\"MIB_STANDARD\\\"}\":{\".\":{},\"f:name\":{},\"f:value\":{}},\"k:{\\\"name\\\":\\\"MONGO_URI\\\"}\":{\".\":{},\"f:name\":{},\"f:value\":{}},\"k:{\\\"name\\\":\\\"POLL_BASE_PROFILES\\\"}\":{\".\":{},\"f:name\":{},\"f:value\":{}},\"k:{\\\"name\\\":\\\"PREFETCH_COUNT\\\"}\":{\".\":{},\"f:name\":{},\"f:value\":{}},\"k:{\\\"name\\\":\\\"PROFILES_RELOAD_DELAY\\\"}\":{\".\":{},\"f:name\":{},\"f:value\":{}},\"k:{\\\"name\\\":\\\"PYSNMP_DEBUG\\\"}\":{\".\":{},\"f:name\":{}},\"k:{\\\"name\\\":\\\"REDIS_URL\\\"}\":{\".\":{},\"f:name\":{},\"f:value\":{}},\"k:{\\\"name\\\":\\\"RESOLVE_TRAP_ADDRESS\\\"}\":{\".\":{},\"f:name\":{},\"f:value\":{}},\"k:{\\\"name\\\":\\\"SC4SNMP_VERSION\\\"}\":{\".\":{},\"f:name\":{},\"f:value\":{}},\"k:{\\\"name\\\":\\\"SPLUNK_AGGREGATE_TRAPS_EVENTS\\\"}\":{\".\":{},\"f:name\":{},\"f:value\":{}},\"k:{\\\"name\\\":\\\"SPLUNK_HEC_HOST\\\"}\":{\".\":{},\"f:name\":{},\"f:value\":{}},\"k:{\\\"name\\\":\\\"SPLUNK_HEC_INDEX_EVENTS\\\"}\":{\".\":{},\"f:name\":{},\"f:value\":{}},\"k:{\\\"name\\\":\\\"SPLUNK_HEC_INDEX_METRICS\\\"}\":{\".\":{},\"f:name\":{},\"f:value\":{}},\"k:{\\\"name\\\":\\\"SPLUNK_HEC_INSECURESSL\\\"}\":{\".\":{},\"f:name\":{},\"f:value\":{}},\"k:{\\\"name\\\":\\\"SPLUNK_HEC_PORT\\\"}\":{\".\":{},\"f:name\":{},\"f:value\":{}},\"k:{\\\"name\\\":\\\"SPLUNK_HEC_SCHEME\\\"}\":{\".\":{},\"f:name\":{},\"f:value\":{}},\"k:{\\\"name\\\":\\\"SPLUNK_HEC_TOKEN\\\"}\":{\".\":{},\"f:name\":{},\"f:valueFrom\":{\".\":{},\"f:secretKeyRef\":{}}},\"k:{\\\"name\\\":\\\"SPLUNK_METRIC_NAME_HYPHEN_TO_UNDERSCORE\\\"}\":{\".\":{},\"f:name\":{},\"f:value\":{}},\"k:{\\\"name\\\":\\\"SPLUNK_SOURCETYPE_POLLING_EVENTS\\\"}\":{\".\":{},\"f:name\":{},\"f:value\":{}},\"k:{\\\"name\\\":\\\"SPLUNK_SOURCETYPE_POLLING_METRICS\\\"}\":{\".\":{},\"f:name\":{},\"f:value\":{}},\"k:{\\\"name\\\":\\\"SPLUNK_SOURCETYPE_TRAPS\\\"}\":{\".\":{},\"f:name\":{},\"f:value\":{}},\"k:{\\\"name\\\":\\\"TTL_DNS_CACHE_TRAPS\\\"}\":{\".\":{},\"f:name\":{},\"f:value\":{}},\"k:{\\\"name\\\":\\\"UDP_CONNECTION_TIMEOUT\\\"}\":{\".\":{},\"f:name\":{},\"f:value\":{}},\"k:{\\\"name\\\":\\\"WALK_MAX_RETRIES\\\"}\":{\".\":{},\"f:name\":{},\"f:value\":{}},\"k:{\\\"name\\\":\\\"WALK_RETRY_MAX_INTERVAL\\\"}\":{\".\":{},\"f:name\":{},\"f:value\":{}},\"k:{\\\"name\\\":\\\"WORKER_CONCURRENCY\\\"}\":{\".\":{},\"f:name\":{},\"f:value\":{}}},\"f:image\":{},\"f:imagePullPolicy\":{},\"f:name\":{},\"f:resources\":{\".\":{},\"f:limits\":{\".\":{},\"f:cpu\":{}},\"f:requests\":{\".\":{},\"f:cpu\":{}}},\"f:securityContext\":{\".\":{},\"f:capabilities\":{\".\":{},\"f:drop\":{}},\"f:readOnlyRootFilesystem\":{},\"f:runAsGroup\":{},\"f:runAsNonRoot\":{},\"f:runAsUser\":{}},\"f:terminationMessagePath\":{},\"f:terminationMessagePolicy\":{},\"f:volumeMounts\":{\".\":{},\"k:{\\\"mountPath\\\":\\\"/.pysnmp/\\\"}\":{\".\":{},\"f:mountPath\":{},\"f:name\":{}},\"k:{\\\"mountPath\\\":\\\"/app/config\\\"}\":{\".\":{},\"f:mountPath\":{},\"f:name\":{},\"f:readOnly\":{}},\"k:{\\\"mountPath\\\":\\\"/tmp/\\\"}\":{\".\":{},\"f:mountPath\":{},\"f:name\":{}}}}},\"f:dnsPolicy\":{},\"f:enableServiceLinks\":{},\"f:restartPolicy\":{},\"f:schedulerName\":{},\"f:securityContext\":{\".\":{},\"f:fsGroup\":{}},\"f:serviceAccount\":{},\"f:serviceAccountName\":{},\"f:terminationGracePeriodSeconds\":{},\"f:volumes\":{\".\":{},\"k:{\\\"name\\\":\\\"config\\\"}\":{\".\":{},\"f:configMap\":{\".\":{},\"f:defaultMode\":{},\"f:items\":{},\"f:name\":{}},\"f:name\":{}},\"k:{\\\"name\\\":\\\"pysnmp-cache-volume\\\"}\":{\".\":{},\"f:emptyDir\":{},\"f:name\":{}},\"k:{\\\"name\\\":\\\"tmp\\\"}\":{\".\":{},\"f:emptyDir\":{},\"f:name\":{}}}}},\"manager\":\"kubelite\",\"operation\":\"Update\",\"time\":\"2026-09-20T14:30:00.000ZISO_TIMESTAMP2026-09-20T14:30:00.000Z\"},{\"apiVersion\":\"v1\",\"fieldsType\":\"FieldsV1\",\"fieldsV1\":{\"f:metadata\":{\"f:annotations\":{\".\":{},\"f:cni.projectcalico.org/containerID\":{},\"f:cni.projectcalico.org/podIP\":{},\"f:cni.projectcalico.org/podIPs\":{}}}},\"manager\":\"calico\",\"operation\":\"Update\",\"subresource\":\"status\",\"time\":\"2026-09-20T14:30:00.000ZISO_TIMESTAMP2026-09-20T14:30:00.000Z\"},{\"apiVersion\":\"v1\",\"fieldsType\":\"FieldsV1\",\"fieldsV1\":{\"f:status\":{\"f:conditions\":{\"k:{\\\"type\\\":\\\"ContainersReady\\\"}\":{\".\":{},\"f:lastProbeTime\":{},\"f:lastTransitionTime\":{},\"f:status\":{},\"f:type\":{}},\"k:{\\\"type\\\":\\\"Initialized\\\"}\":{\".\":{},\"f:lastProbeTime\":{},\"f:lastTransitionTime\":{},\"f:status\":{},\"f:type\":{}},\"k:{\\\"type\\\":\\\"PodReadyToStartContainers\\\"}\":{\".\":{},\"f:lastProbeTime\":{},\"f:lastTransitionTime\":{},\"f:status\":{},\"f:type\":{}},\"k:{\\\"type\\\":\\\"Ready\\\"}\":{\".\":{},\"f:lastProbeTime\":{},\"f:lastTransitionTime\":{},\"f:status\":{},\"f:type\":{}}},\"f:containerStatuses\":{},\"f:hostIP\":{},\"f:hostIPs\":{},\"f:phase\":{},\"f:podIP\":{},\"f:podIPs\":{\".\":{},\"k:{\\\"ip\\\":\\\"10.1.5.238\\\"}\":{\".\":{},\"f:ip\":{}}},\"f:startTime\":{}}},\"manager\":\"kubelite\",\"operation\":\"Update\",\"subresource\":\"status\",\"time\":\"2026-09-20T14:30:00.000ZISO_TIMESTAMP2026-09-20T14:30:00.000Z\"}],\"name\":\"snmp-splunk-connect-for-snmp-worker-trap-56dd75bf88-6zh4g\",\"namespace\":\"sc4snmp\",\"ownerReferences\":[{\"apiVersion\":\"apps/v1\",\"blockOwnerDeletion\":true,\"controller\":true,\"kind\":\"ReplicaSet\",\"name\":\"snmp-splunk-connect-for-snmp-worker-trap-56dd75bf88\",\"uid\":\"b1613111-daeb-4dbd-94d2-5dc038838011\"}],\"resourceVersion\":\"36704899\",\"uid\":\"9600b10e-4814-4aa5-8fea-002019bf4a01\"},\"spec\":{\"affinity\":{\"podAntiAffinity\":{\"preferredDuringSchedulingIgnoredDuringExecution\":[{\"podAffinityTerm\":{\"labelSelector\":{\"matchLabels\":{\"app.kubernetes.io/instance\":\"snmp\",\"app.kubernetes.io/name\":\"splunk-connect-for-snmp-worker-trap\"}},\"topologyKey\":\"kubernetes.io/hostname\"},\"weight\":1}]}},\"containers\":[{\"args\":[\"celery\",\"worker-trap\"],\"env\":[{\"name\":\"CONFIG_PATH\",\"value\":\"/app/config/config.yaml\"},{\"name\":\"REDIS_URL\",\"value\":\"redis://snmp-redis-master:6379/1\"},{\"name\":\"SC4SNMP_VERSION\",\"value\":\"1.14.1\"},{\"name\":\"CELERY_BROKER_URL\",\"value\":\"redis://snmp-redis-master:6379/0\"},{\"name\":\"MONGO_URI\",\"value\":\"mongodb://snmp-mongodb:27017\"},{\"name\":\"WALK_RETRY_MAX_INTERVAL\",\"value\":\"180\"},{\"name\":\"WALK_MAX_RETRIES\",\"value\":\"5\"},{\"name\":\"METRICS_INDEXING_ENABLED\",\"value\":\"false\"},{\"name\":\"POLL_BASE_PROFILES\",\"value\":\"true\"},{\"name\":\"LOG_LEVEL\",\"value\":\"INFO\"},{\"name\":\"DISABLE_MONGO_DEBUG_LOGGING\",\"value\":\"true\"},{\"name\":\"UDP_CONNECTION_TIMEOUT\",\"value\":\"3\"},{\"name\":\"MAX_OID_TO_PROCESS\",\"value\":\"70\"},{\"name\":\"MAX_REPETITIONS\",\"value\":\"10\"},{\"name\":\"PYSNMP_DEBUG\"},{\"name\":\"PROFILES_RELOAD_DELAY\",\"value\":\"60\"},{\"name\":\"MIB_SOURCES\",\"value\":\"http://snmp-mibserver/asn1/@mib@\"},{\"name\":\"MIB_INDEX\",\"value\":\"http://snmp-mibserver/index.csv\"},{\"name\":\"MIB_STANDARD\",\"value\":\"http://snmp-mibserver/standard.txt\"},{\"name\":\"SPLUNK_HEC_SCHEME\",\"value\":\"https\"},{\"name\":\"SPLUNK_HEC_HOST\",\"value\":\"10.0.10.104\"},{\"name\":\"IGNORE_EMPTY_VARBINDS\",\"value\":\"false\"},{\"name\":\"SPLUNK_HEC_PORT\",\"value\":\"8088\"},{\"name\":\"SPLUNK_HEC_INSECURESSL\",\"value\":\"true\"},{\"name\":\"SPLUNK_AGGREGATE_TRAPS_EVENTS\",\"value\":\"false\"},{\"name\":\"SPLUNK_METRIC_NAME_HYPHEN_TO_UNDERSCORE\",\"value\":\"false\"},{\"name\":\"SPLUNK_HEC_TOKEN\",\"valueFrom\":{\"secretKeyRef\":{\"key\":\"hec_token\",\"name\":\"splunk-connect-for-snmp-splunk\"}}},{\"name\":\"SPLUNK_HEC_INDEX_EVENTS\",\"value\":\"netops\"},{\"name\":\"SPLUNK_HEC_INDEX_METRICS\",\"value\":\"netmetrics\"},{\"name\":\"SPLUNK_SOURCETYPE_TRAPS\",\"value\":\"sc4snmp:traps\"},{\"name\":\"SPLUNK_SOURCETYPE_POLLING_EVENTS\",\"value\":\"sc4snmp:event\"},{\"name\":\"SPLUNK_SOURCETYPE_POLLING_METRICS\",\"value\":\"sc4snmp:metric\"},{\"name\":\"WORKER_CONCURRENCY\",\"value\":\"4\"},{\"name\":\"PREFETCH_COUNT\",\"value\":\"30\"},{\"name\":\"RESOLVE_TRAP_ADDRESS\",\"value\":\"false\"},{\"name\":\"MAX_DNS_CACHE_SIZE_TRAPS\",\"value\":\"500\"},{\"name\":\"TTL_DNS_CACHE_TRAPS\",\"value\":\"1800\"},{\"name\":\"IPv6_ENABLED\",\"value\":\"false\"}],\"image\":\"ghcr.io/splunk/splunk-connect-for-snmp/container:1.14.1\",\"imagePullPolicy\":\"Always\",\"name\":\"splunk-connect-for-snmp-worker-trap\",\"resources\":{\"limits\":{\"cpu\":\"500m\"},\"requests\":{\"cpu\":\"250m\"}},\"securityContext\":{\"capabilities\":{\"drop\":[\"ALL\"]},\"readOnlyRootFilesystem\":true,\"runAsGroup\":10001,\"runAsNonRoot\":true,\"runAsUser\":10001},\"terminationMessagePath\":\"/dev/termination-log\",\"terminationMessagePolicy\":\"File\",\"volumeMounts\":[{\"mountPath\":\"/app/config\",\"name\":\"config\",\"readOnly\":true},{\"mountPath\":\"/.pysnmp/\",\"name\":\"pysnmp-cache-volume\"},{\"mountPath\":\"/tmp/\",\"name\":\"tmp\"},{\"mountPath\":\"/var/run/secrets/kubernetes.io/serviceaccount\",\"name\":\"kube-api-access-r9bmp\",\"readOnly\":true}]}],\"dnsPolicy\":\"ClusterFirst\",\"enableServiceLinks\":true,\"nodeName\":\"maple-splunk-vm4-hf\",\"preemptionPolicy\":\"PreemptLowerPriority\",\"priority\":0,\"restartPolicy\":\"Always\",\"schedulerName\":\"default-scheduler\",\"securityContext\":{\"fsGroup\":10001},\"serviceAccount\":\"snmp-splunk-connect-for-snmp-user\",\"serviceAccountName\":\"snmp-splunk-connect-for-snmp-user\",\"terminationGracePeriodSeconds\":30,\"tolerations\":[{\"effect\":\"NoExecute\",\"key\":\"node.kubernetes.io/not-ready\",\"operator\":\"Exists\",\"tolerationSeconds\":300},{\"effect\":\"NoExecute\",\"key\":\"node.kubernetes.io/unreachable\",\"operator\":\"Exists\",\"tolerationSeconds\":300}],\"volumes\":[{\"configMap\":{\"defaultMode\":420,\"items\":[{\"key\":\"config.yaml\",\"path\":\"config.yaml\"}],\"name\":\"splunk-connect-for-snmp-config\"},\"name\":\"config\"},{\"emptyDir\":{},\"name\":\"pysnmp-cache-volume\"},{\"emptyDir\":{},\"name\":\"tmp\"},{\"name\":\"kube-api-access-r9bmp\",\"projected\":{\"defaultMode\":420,\"sources\":[{\"serviceAccountToken\":{\"expirationSeconds\":3607,\"path\":\"token\"}},{\"configMap\":{\"items\":[{\"key\":\"ca.crt\",\"path\":\"ca.crt\"}],\"name\":\"kube-root-ca.crt\"}},{\"downwardAPI\":{\"items\":[{\"fieldRef\":{\"apiVersion\":\"v1\",\"fieldPath\":\"metadata.namespace\"},\"path\":\"namespace\"}]}}]}}]},\"status\":{\"conditions\":[{\"lastProbeTime\":null,\"lastTransitionTime\":\"2026-09-20T14:30:00.000ZISO_TIMESTAMP2026-09-20T14:30:00.000Z\",\"status\":\"True\",\"type\":\"PodReadyToStartContainers\"},{\"lastProbeTime\":null,\"lastTransitionTime\":\"2026-09-20T14:30:00.000ZISO_TIMESTAMP2026-09-20T14:30:00.000Z\",\"status\":\"True\",\"type\":\"Initialized\"},{\"lastProbeTime\":null,\"lastTransitionTime\":\"2026-09-20T14:30:00.000ZISO_TIMESTAMP2026-09-20T14:30:00.000Z\",\"status\":\"True\",\"type\":\"Ready\"},{\"lastProbeTime\":null,\"lastTransitionTime\":\"2026-09-20T14:30:00.000ZISO_TIMESTAMP2026-09-20T14:30:00.000Z\",\"status\":\"True\",\"type\":\"ContainersReady\"},{\"lastProbeTime\":null,\"lastTransitionTime\":\"2026-09-20T14:30:00.000ZISO_TIMESTAMP2026-09-20T14:30:00.000Z\",\"status\":\"True\",\"type\":\"PodScheduled\"}],\"containerStatuses\":[{\"allocatedResources\":{\"cpu\":\"250m\"},\"containerID\":\"containerd://d8dd4f7da3b9a459f9a8f14e19f3aec11b4ffbf186cfdb578e2a82545f848352\",\"image\":\"ghcr.io/splunk/splunk-connect-for-snmp/container:1.14.1\",\"imageID\":\"ghcr.io/splunk/splunk-connect-for-snmp/container@sha256:227b5de509fa27713e78c5bc07f1bd0533a846f87a4035a144d2b361c0286b2c\",\"lastState\":{},\"name\":\"splunk-connect-for-snmp-worker-trap\",\"ready\":true,\"resources\":{\"limits\":{\"cpu\":\"500m\"},\"requests\":{\"cpu\":\"250m\"}},\"restartCount\":12,\"started\":true,\"state\":{\"running\":{\"startedAt\":\"2026-09-20T14:30:00.000ZISO_TIMESTAMP2026-09-20T14:30:00.000Z\"}},\"volumeMounts\":[{\"mountPath\":\"/app/config\",\"name\":\"config\",\"readOnly\":true,\"recursiveReadOnly\":\"Disabled\"},{\"mountPath\":\"/.pysnmp/\",\"name\":\"pysnmp-cache-volume\"},{\"mountPath\":\"/tmp/\",\"name\":\"tmp\"},{\"mountPath\":\"/var/run/secrets/kubernetes.io/serviceaccount\",\"name\":\"kube-api-access-r9bmp\",\"readOnly\":true,\"recursiveReadOnly\":\"Disabled\"}]}],\"hostIP\":\"10.0.10.104\",\"hostIPs\":[{\"ip\":\"10.0.10.104\"}],\"phase\":\"Running\",\"podIP\":\"10.1.5.238\",\"podIPs\":[{\"ip\":\"10.1.5.238\"}],\"qosClass\":\"Burstable\",\"startTime\":\"2026-09-20T14:30:00.000ZISO_TIMESTAMP2026-09-20T14:30:00.000Z\"}}"
  },
  {
    "id": "stream:netflow",
    "label": "Stream Netflow",
    "vendor": "other",
    "category": "stream-netflow",
    "index": "netops_logs",
    "sample": "{\"endtime\":\"2026-09-20T14:30:00.000ZISO_TIMESTAMP2026-09-20T14:30:00.000Z\",\"timestamp\":\"2026-09-20T14:30:00.000ZISO_TIMESTAMP2026-09-20T14:30:00.000Z\",\"app_tag\":\"USER-DEF : 009311\",\"event_name\":\"netFlowData\",\"exporter_ip\":\"10.201.51.68\",\"exporter_time\":\"2026-Sep-18 17:34:43\",\"exporter_uptime\":3046802704,\"flow_dir\":0,\"flow_end_time_milli\":1789752881000,\"flow_start_time_milli\":1789752866000,\"netflow_elements\":[\"UNKNOWN : ac190e02\",\"UNKNOWN : 0a14010a\",\"UNKNOWN : 147e\",\"UNKNOWN : 0000000000000000\",\"UNKNOWN : 0000000000000598\"],\"netflow_version\":9,\"observation_domain_id\":16777217,\"observation_point_id\":4294967314,\"protoid\":17,\"seqnumber\":722423,\"src_mac\":\"70:69:5a:76:54:58\",\"version\":4}"
  },
  {
    "id": "vmware:perf:cpu",
    "label": "Vmware Esx Perf",
    "vendor": "other",
    "category": "vmware-esx-perf",
    "index": "cisco_mdt_metrics",
    "sample": "{\"timestamp\": \"2026-09-20T14:30:00.000ZISO_TS2026-09-20T14:30:00.000Z\", \"epoch\": 2026-09-20T14:30:00.000ZEPOCH2026-09-20T14:30:00.000Z, \"host\": \"esx-maple-compute-01.maple.ciscolabs.com\", \"vm_name\": \"web-srv-01\", \"cpu.usage.average\": 2026-09-20T14:30:00.000ZCPU_PCT2026-09-20T14:30:00.000Z, \"cpu.usagemhz.average\": 480, \"status\": \"green\"}"
  },
  {
    "id": "cisco:ftd:syslog",
    "label": "Cisco Ftd Syslog",
    "vendor": "cisco",
    "category": "Cisco Security & Telemetry",
    "index": "netops_logs",
    "sample": "2026-09-20T14:30:00.000ZSYSLOG_TIMESTAMP2026-09-20T14:30:00.000Z 2026-09-20T14:30:00.000ZHOST2026-09-20T14:30:00.000Z :2026-09-20T14:30:00.000ZSYSLOG_TIMESTAMP2026-09-20T14:30:00.000Z UTC: %FTD--6-805002: TCP Flow is no longer offloaded for connection 35430004 from INTERNET:32.185.98.157/443 (32.185.98.157/443) to INSIDE:10.0.10.95/17229 (64.100.57.80/17229)"
  },
  {
    "id": "cisco:ise:radius:authz:policy",
    "label": "Cisco Ise Radius Authz Policy",
    "vendor": "cisco",
    "category": "Cisco Security & Telemetry",
    "index": "netops_logs",
    "sample": "{\"rule\": {\"default\": true, \"id\": \"70c8186d-e2ef-4482-bd89-394cd9b723e4\", \"name\": \"Default\", \"hitCounts\": 0, \"rank\": 15, \"state\": \"enabled\", \"condition\": null}, \"profile\": [\"DenyAccess\"], \"securityGroup\": null, \"link\": {\"rel\": \"self\", \"href\": \"2026-09-20T14:30:00.000ZHOST2026-09-20T14:30:00.000Z/api/v1/policy/network-access/policy-set/f26b5958-d128-4f4b-9e17-d0338af2b891/authorization/70c8186d-e2ef-4482-bd89-394cd9b723e4\", \"type\": \"application/json\"}, \"policy_id\": \"f26b5958-d128-4f4b-9e17-d0338af2b891\", \"lastUpdated\": 1784258516483}"
  },
  {
    "id": "cisco:ise:radius:policyset",
    "label": "Cisco Ise Radius Policyset",
    "vendor": "cisco",
    "category": "Cisco Security & Telemetry",
    "index": "netops_logs",
    "sample": "{\"default\": true, \"id\": \"f26b5958-d128-4f4b-9e17-d0338af2b891\", \"name\": \"Default\", \"description\": \"Default policy set\", \"hitCounts\": 238844, \"rank\": 0, \"state\": \"enabled\", \"condition\": null, \"serviceName\": \"Default Network Access\", \"isProxy\": false, \"link\": {\"rel\": \"self\", \"href\": \"2026-09-20T14:30:00.000ZHOST2026-09-20T14:30:00.000Z/api/v1/policy/network-access/policy-set/f26b5958-d128-4f4b-9e17-d0338af2b891\", \"type\": \"application/json\"}, \"lastUpdated\": 1784258516483}"
  },
  {
    "id": "cisco:ise:syslog",
    "label": "Cisco Ise Syslog",
    "vendor": "cisco",
    "category": "Cisco Security & Telemetry",
    "index": "netops_logs",
    "sample": "2026-09-20T14:30:00.000ZSYSLOG_TIMESTAMP2026-09-20T14:30:00.000Z 2026-09-20T14:30:00.000ZHOST2026-09-20T14:30:00.000Z 2026-09-20T14:30:00.000ZSYSLOG_TIMESTAMP2026-09-20T14:30:00.000Z maple-ise02 CISE_Failed_Attempts 0002840615 1 0 2026-09-18 17:34:43.705 +00:00 0056893972 5400 NOTICE Failed-Attempt: Authentication failed, ConfigVersionId=101, Device IP Address=10.0.0.1, Device Port=18330, DestinationIPAddress=2026-09-20T14:30:00.000ZHOST2026-09-20T14:30:00.000Z, DestinationPort=1812, RadiusPacketType=AccessRequest, UserName=INVALID, Protocol=Radius, ExternalErrorCode=40008, NetworkDeviceName=FTD-DOVETAIL01, User-Name=INVALID, NAS-IP-Address=10.0.0.1, NAS-Port=2241802240, Called-Station-ID=64.100.57.98, Calling-Station-ID=45.149.145.155, NAS-Port-Type=Virtual, Tunnel-Client-Endpoint=(tag=0) 45.149.145.155, cisco-av-pair=audit-session-id=0a000001859f30006aad7633, cisco-av-pair=ip:source-ip=45.149.145.155, cisco-av-pair=coa-push=true, MS-CHAP-Challenge=a5:2c:00:e6:1e:b1:3e:06:ea:18:f1:5e:4d:48:f7:48, MS-CHAP2-Response=00:00:b3:0d:ac:89:95:df:35:12:71:17:6c:aa:62:fd:98:e4:00:00:00:00:00:00:00:00:e3:31:02:ea:9f:15:85:52:f9:e3:76:d8:d5:6c:56:2a:f8:25:ea:a8:0e:e5:af:58, CVPN3000/ASA/PIX7x-Tunnel-Group-Name=MAPLE-NON_DUO, NetworkDeviceProfileName=Cisco, NetworkDeviceProfileId=b0699505-3150-4215-a80e-6753d45bf56c, IsThirdPartyDeviceFlow=false, SSID=64.100.57.98, CVPN3000/ASA/PIX7x-Client-Type=2, AcsSessionID=maple-ise02/571877645/2000730, AuthenticationMethod=MSCHAPV2, SelectedAccessService=Default Network Access, RequestLatency=8, FailureReason=22056 Subject not found in the applicable identity store(s), Step=11001, Step=11017, Step=15049, Step=15008, Step=15041, Step=15048, Step=15048, Step=15048, Step=15048, Step=15048, Step=22072, Step=15013, Step=24210, Step=24216, Step=15013, Step=24430, Step=24325, Step=24313, Step=24318, Step=24322, Step=24352, Step=24412, Step=15013, Step=24631, Step=24633, Step=22016, Step=22056, Step=22058, Step=22061, Step=11003, SelectedAuthenticationIdentityStores=Internal Users, SelectedAuthenticationIdentityStores=All_AD_Join_Points, SelectedAuthenticationIdentityStores=Guest Users, NetworkDeviceGroups=Location#All Locations#OTT02-Kanata, NetworkDeviceGroups=IPSEC#Is IPSEC Device#No, NetworkDeviceGroups=DNAC#DNAC Devices, NetworkDeviceGroups=Device Type#All Device Types, IdentityPolicyMatchedRule=Default, CPMSessionID=0a000001859f30006aad7633, ISEPolicySetName=Default, IdentitySelectionMatchedRule=Default, StepLatency=1=0\\;2=1\\;3=0\\;4=0\\;5=1\\;6=0\\;7=0\\;8=0\\;9=0\\;10=0\\;11=0\\;12=0\\;13=2\\;14=0\\;15=0\\;16=2\\;17=0\\;18=0\\;19=0\\;20=0\\;21=0\\;22=0\\;23=0\\;24=2\\;25=0\\;26=0\\;27=0\\;28=0\\;29=0, StepData=5= Network Access.EapAuthentication, StepData=6= Normalised Radius.RadiusFlowType, StepData=7= Normalised Radius.RadiusFlowType, StepData=8= Normalised Radius.RadiusFlowType, StepData=9= Normalised Radius.RadiusFlowType, StepData=10=All_User_ID_Stores, StepData=11=Internal Users, StepData=14=All_AD_Join_Points, StepData=15=All_AD_Join_Points, StepData=16=INVALID, StepData=17=maple.ciscolabs.com, StepData=18=maple.ciscolabs.com, StepData=20=ERROR_NO_SUCH_USER, StepData=21=All_AD_Join_Points, StepData=22=Guest Users, TotalAuthenLatency=8, ClientLatency=0, IsMachineIdentity=false, DTLSSupport=Unknown, EndPointIPAddress=45.149.145.155, DNAC=DNAC#DNAC Devices, Network Device Profile=Cisco, Location=Location#All Locations#OTT02-Kanata, Device Type=Device Type#All Device Types, IPSEC=IPSEC#Is IPSEC Device#No, Response={RadiusPacketType=AccessReject; AuthenticationResult=UnknownUser; MS-CHAP-Error="
  },
  {
    "id": "cisco:ise:tacacs:authz:policy",
    "label": "Cisco Ise Tacacs Authz Policy",
    "vendor": "cisco",
    "category": "Cisco Security & Telemetry",
    "index": "netops_logs",
    "sample": "{\"rule\": {\"default\": true, \"id\": \"b47a6faa-f732-4007-b33f-04f0b8c884b3\", \"name\": \"Default\", \"hitCounts\": 0, \"rank\": 8, \"state\": \"enabled\", \"condition\": null}, \"commands\": [\"DenyAllCommands\"], \"profile\": \"Deny All Shell Profile\", \"link\": {\"rel\": \"self\", \"href\": \"2026-09-20T14:30:00.000ZHOST2026-09-20T14:30:00.000Z/api/v1/policy/device-admin/policy-set/56576c80-2c47-40bb-a344-b40ef71aa8f1/authorization/b47a6faa-f732-4007-b33f-04f0b8c884b3\", \"type\": \"application/json\"}, \"policy_id\": \"56576c80-2c47-40bb-a344-b40ef71aa8f1\", \"lastUpdated\": 1784258516494}"
  },
  {
    "id": "cisco:ise:tacacs:policyset",
    "label": "Cisco Ise Tacacs Policyset",
    "vendor": "cisco",
    "category": "Cisco Security & Telemetry",
    "index": "netops_logs",
    "sample": "{\"default\": true, \"id\": \"56576c80-2c47-40bb-a344-b40ef71aa8f1\", \"name\": \"Default\", \"description\": \"Tacacs Default policy set\", \"hitCounts\": 22, \"rank\": 0, \"state\": \"enabled\", \"condition\": null, \"serviceName\": \"Default Device Admin\", \"isProxy\": false, \"link\": {\"rel\": \"self\", \"href\": \"2026-09-20T14:30:00.000ZHOST2026-09-20T14:30:00.000Z/api/v1/policy/device-admin/policy-set/56576c80-2c47-40bb-a344-b40ef71aa8f1\", \"type\": \"application/json\"}, \"lastUpdated\": 1784258516494}"
  },
  {
    "id": "httpevent",
    "label": "Cisco Metrics Bgp Rib",
    "vendor": "other",
    "category": "Cisco Security & Telemetry",
    "index": "cisco_mdt_metrics",
    "sample": "{\"time\": 2026-09-20T14:30:00.000ZEPOCH2026-09-20T14:30:00.000Z, \"event\": \"metric\", \"source\": \"otel:cisco:xr\", \"sourcetype\": \"httpevent\", \"host\": \"2026-09-20T14:30:00.000ZNODE2026-09-20T14:30:00.000Z\", \"index\": \"splunk_otel\", \"fields\": {\"metric_name:cisco.total-cpu-one-minute\": 2026-09-20T14:30:00.000ZCPU_1M2026-09-20T14:30:00.000Z, \"metric_name:cisco.total-cpu-five-minute\": 2026-09-20T14:30:00.000ZCPU_5M2026-09-20T14:30:00.000Z, \"metric_name:cisco.total-cpu-fifteen-minute\": 2026-09-20T14:30:00.000ZCPU_5M2026-09-20T14:30:00.000Z, \"metric_name:cisco.temperature\": 2026-09-20T14:30:00.000ZTEMP2026-09-20T14:30:00.000Z, \"metric_name:cisco.voltage\": 12, \"metric_name:cisco.vrf.established-neighbors-count\": 2, \"metric_name:cisco.vrf.neighbors-count\": 2, \"metric_name:cisco.statistics.pspn-stats.pdu-counters.pdu-dropped-count\": 0, \"metric_name:cisco.statistics.pspn-stats.pdu-counters.pdu-receive-count\": 4820, \"metric_name:cisco.statistics.pspn-stats.pdu-counters.pdu-send-count\": 4790, \"metric_name:system.memory.usage\": 2026-09-20T14:30:00.000ZMEM_USAGE2026-09-20T14:30:00.000Z, \"cisco.node_id\": \"2026-09-20T14:30:00.000ZNODE2026-09-20T14:30:00.000Z\", \"vrf-name\": \"default\"}}"
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
    "sample": "{\"id\": 1789751173971923653, \"timestamp\": 1789751173, \"timestamp_nanoseconds\": 971923000, \"date\": \"2026-09-20T14:30:00.000ZISO_TIMESTAMP2026-09-20T14:30:00.000Z\", \"event_type\": \"Fault Cleared\", \"event_type_id\": 553648196, \"connector_guid\": \"519f89fd-a1db-458b-b551-5bb7ec1f8474\", \"group_guids\": [\"fa567a34-1239-4be4-9a2d-30d2a9d05d16\"], \"computer\": {\"connector_guid\": \"519f89fd-a1db-458b-b551-5bb7ec1f8474\", \"hostname\": \"fileserver01\", \"external_ip\": \"64.100.57.80\", \"active\": true, \"network_addresses\": [{\"ip\": \"10.0.10.14\", \"mac\": \"00:50:56:83:9e:a5\"}, {\"ip\": \"172.17.0.1\", \"mac\": \"9a:1f:01:44:2a:40\"}], \"links\": {\"computer\": \"https://api.amp.cisco.com/v1/computers/519f89fd-a1db-458b-b551-5bb7ec1f8474\", \"trajectory\": \"https://api.amp.cisco.com/v1/computers/519f89fd-a1db-458b-b551-5bb7ec1f8474/trajectory\", \"group\": \"https://api.amp.cisco.com/v1/groups/fa567a34-1239-4be4-9a2d-30d2a9d05d16\"}}, \"fault_event_title\": \"Connector event monitoring is overloaded\", \"EndpointDataType\": \"events\", \"groups\": [{\"guid\": \"fa567a34-1239-4be4-9a2d-30d2a9d05d16\", \"name\": \"MAPLE-PROTECT\"}]}"
  },
  {
    "id": "cisco:sfw:estreamer",
    "label": "Cisco Sfw Estreamer",
    "vendor": "cisco",
    "category": "Cisco Security & Telemetry",
    "index": "netops_logs",
    "sample": "{\"EventType\": \"ConnectionEvent\", \"FirstPacketSecond\": 1789752808, \"DeviceUUID\": \"84663f36-6213-11ec-943b-b10f15a5650d\", \"InstanceID\": 16, \"ConnectionID\": 61483, \"AC_RuleAction\": \"Allow\", \"InitiatorIP\": \"10.100.1.105\", \"ResponderIP\": \"208.67.222.222\", \"InitiatorPort\": 36665, \"ResponderPort\": 53, \"Protocol\": \"udp\", \"IngressInterface\": \"INSIDE.800\", \"EgressInterface\": \"INTERNET\", \"IngressZone\": \"INSIDE\", \"EgressZone\": \"INTERNET\", \"IngressVRF\": \"Global\", \"EgressVRF\": \"Global\", \"FirewallPolicy\": \"FTD-DOVETAIL01\", \"FirewallRule\": \"ALLOW_ALL\", \"PrefilterPolicy\": \"Default Prefilter Policy\", \"ClientApplication\": \"DNS\", \"Application\": \"DNS\", \"InitiatorPackets\": 1, \"ResponderPackets\": 0, \"InitiatorBytes\": 94, \"ResponderBytes\": 0, \"NAP_Policy\": \"Balanced Security and Connectivity\", \"DNS_Query\": \"us02.analytics.sdwan.cisco.com\", \"DNS_RecordDescription\": \"a host address\", \"DNS_ResponseType\": \"No Error\", \"ReferencedHost\": \"us02.analytics.sdwan.cisco.com\", \"NAT_InitiatorPort\": 36665, \"NAT_ResponderPort\": 53, \"NAT_InitiatorIP\": \"64.100.57.80\", \"NAT_ResponderIP\": \"208.67.222.222\", \"ClientAppDetector\": \"AppID\", \"Device\": \"FTD-DOVETAIL01\", \"DeviceIP\": \"10.0.255.11,\", \"DeviceSerialNumber\": \"FCH19057MC9\", \"SourceHost\": \"2026-09-20T14:30:00.000ZHOST2026-09-20T14:30:00.000Z\"}"
  },
  {
    "id": "cisco:sfw:policy",
    "label": "Cisco Sfw Policy",
    "vendor": "cisco",
    "category": "Cisco Security & Telemetry",
    "index": "netops_logs",
    "sample": "{\"name\": \"AMP_Policy\", \"id\": \"fb73018e-682d-11ec-bf59-9b66d79cfdcf\", \"type\": \"FilePolicy\", \"archiveDepth\": 2, \"archiveDepthAction\": true, \"blockEncryptedArchives\": false, \"cleanList\": true, \"customDetectionList\": true, \"firstTimeFileAnalysis\": true, \"inspectArchives\": false, \"threatScore\": \"DISABLED\", \"links\": {\"self\": \"https://fmc.maple.ciscolabs.com/api/fmc_config/v1/domain/e276abec-e0f2-11e3-8169-6d9ed49b625f/policy/filepolicies/fb73018e-682d-11ec-bf59-9b66d79cfdcf\"}, \"metadata\": {\"readOnly\": {\"state\": false}, \"timestamp\": 1715113568, \"lastUser\": {\"name\": \"admin\", \"id\": \"68d03c42-d9bd-11dc-89f2-b7961d42c462\", \"type\": \"user\"}, \"domain\": {\"name\": \"Global\", \"id\": \"e276abec-e0f2-11e3-8169-6d9ed49b625f\", \"type\": \"Domain\"}}}"
  },
  {
    "id": "cisco_syslog",
    "label": "Cisco Syslog",
    "vendor": "cisco",
    "category": "Cisco Security & Telemetry",
    "index": "netops_logs",
    "sample": "2026-09-20T14:30:00.000ZSYSLOG_TIMESTAMP2026-09-20T14:30:00.000Z 2026-09-20T14:30:00.000ZHOST2026-09-20T14:30:00.000Z 1 2026-09-20T14:30:00.000ZISO_TIMESTAMP2026-09-20T14:30:00.000Z R03 ifmgr 202 - - 1430004: LC/0/0/CPU0:ifmgr[202]: %PKT_INFRA-LINEPROTO-5-UPDOWN : Line protocol on Interface HundredGigE0/0/1/2, changed state to Up "
  },
  {
    "id": "cisco:thousandeyes:event",
    "label": "Cisco Thousandeyes Event",
    "vendor": "cisco",
    "category": "Cisco Security & Telemetry",
    "index": "netops_logs",
    "sample": "{\"id\": \"a78ef292-6962-333c-b97d-a74ec8fad6d9\", \"type\": \"target\", \"agentType\": \"cloud-enterprise-agent\", \"typeName\": \"Network Outage\", \"title\": \"targets 64.100.2.10 +6\", \"state\": \"active\", \"startDate\": \"2026-09-20T14:30:00.000ZISO_TIMESTAMP2026-09-20T14:30:00.000Z\", \"endDate\": null, \"severity\": \"low\", \"affectedTests\": {\"total\": 7, \"inAccountGroup\": 1}, \"affectedTargets\": {\"total\": 7, \"inAccountGroup\": 1}, \"affectedAgents\": {\"total\": 6, \"inAccountGroup\": 1}, \"_links\": {\"self\": {\"href\": \"https://api.thousandeyes.com/v7/events/a78ef292-6962-333c-b97d-a74ec8fad6d9\"}}, \"aid\": \"230661\"}"
  },
  {
    "id": "cisco:thousandeyes:path-vis",
    "label": "Cisco Thousandeyes Path Vis",
    "vendor": "cisco",
    "category": "Cisco Security & Telemetry",
    "index": "netops_logs",
    "sample": "{\"agentId\": \"bac16802-df59-4327-8b7e-33a29e86cde7\", \"aid\": \"230661\", \"testId\": \"414718\", \"roundId\": 1789748220, \"serverIp\": \"144.196.36.211\", \"systemMetrics\": {\"startTimeMs\": 1789748234758, \"endTimeMs\": 1789748246768, \"cpuUtilization\": {\"min\": 0.1530758226037196, \"max\": 0.27266187050359714, \"mean\": 0.21063021312772753, \"median\": 0.19385182153090463, \"stdDev\": 0.044302459250538766, \"count\": 12}, \"physicalMemoryTotalBytes\": 25769803776, \"physicalMemoryUsedBytes\": {\"min\": 21357887488.0, \"max\": 21650030592.0, \"mean\": 21553431788.307693, \"median\": 21596995584.0, \"stdDev\": 97787243.79763554, \"count\": 13}}, \"networkProfile\": {\"gateway\": \"192.168.2.1\", \"wirelessProfile\": {\"bssid\": \"ae:17:d8:c9:0f:e5\", \"channel\": 153, \"noise\": -95, \"phyMode\": \"802.11ac\", \"quality\": 100, \"rssi\": -37, \"snr\": 58, \"ssid\": \"BeerNTalk\", \"txRate\": 866, \"vendor\": \"CiscoMer\"}, \"ipAddress\": \"192.168.2.103\", \"subnetMask\": \"255.255.255.0\", \"publicIpAddress\": \"70.54.105.178\", \"localPrefix\": \"192.168.2.0\", \"publicIpRange\": \"70.54.96.0-70.54.127.255\", \"dnsServers\": [\"192.168.2.1\", \"207.164.234.193\"], \"hardwareType\": \"wireless\", \"interfaceName\": \"en0\"}, \"platform\": \"mac\", \"application\": \"webex\", \"server\": \"webex.native-app-monitoring.thousandeyes.com:80\", \"sourceIp\": \"192.168.2.103\", \"sourcePrefix\": \"70.54.96.0/19\", \"asnDetails\": {\"asNumber\": 577, \"asName\": \"Bell Canada\"}, \"location\": \"Ottawa, Canada\", \"pathTraces\": [{\"protocol\": \"udp\", \"udpPathTraceMode\": \"stun-pcap\", \"pathId\": \"148184821266924280465351411352952237694001384979247714593828443550044609810682605093870579857362855299935263900333220402789324365511216\", \"numberOfHops\": 17, \"responseTime\": 53, \"ipAddress\": \"144.196.36.211\"}, {\"protocol\": \"udp\", \"udpPathTraceMode\": \"stun-pcap\", \"pathId\": \"148184821266924280465351411352952237694001384979247714593828443550044609810682605093870579857362855299935263900333220402789324365511217\", \"numberOfHops\": 17, \"responseTime\": 51, \"ipAddress\": \"144.196.36.211\"}]}"
  },
  {
    "id": "cisco:asa:syslog",
    "label": "Cisco ASA Syslog Message Stream",
    "vendor": "cisco",
    "category": "Cisco Security & Telemetry",
    "index": "idx_security_fw",
    "sample": "May 20 14:00:00 fw-cisco-asa-01 : %ASA-6-302013: Built outbound TCP connection 184920 for outside:198.51.100.80/443 to inside:10.20.10.45/52140"
  },
  {
    "id": "cisco:ios:mdt:metric",
    "label": "Cisco IOS-XE / IOS-XR Model-Driven Telemetry (gRPC/JSON)",
    "vendor": "cisco",
    "category": "Cisco Security & Telemetry",
    "index": "cisco_mdt_metrics",
    "sample": "{\"time\": 2026-09-20T14:30:00.000ZEPOCH2026-09-20T14:30:00.000Z, \"event\": \"metric\", \"source\": \"cisco:ios:mdt\", \"sourcetype\": \"cisco:ios:mdt:metric\", \"host\": \"leaf01.dc.cisco.com\", \"index\": \"cisco_mdt_metrics\", \"fields\": {\"metric_name:cpu.utilization\": 24.8, \"metric_name:memory.utilization\": 36.4, \"metric_name:interface.octets.in\": 9845129840.0, \"metric_name:interface.octets.out\": 8741029810.0, \"metric_name:interface.errors.in\": 0.0, \"metric_name:interface.errors.out\": 0.0, \"metric_name:carrier.transitions\": 1.0, \"_value\": 24.8, \"interface\": \"GigabitEthernet0/0/1\", \"vendor\": \"cisco\", \"device\": \"leaf01\"}}"
  },
  {
    "id": "cisco:ios:syslog",
    "label": "Cisco IOS System Syslog Facility",
    "vendor": "cisco",
    "category": "Cisco Security & Telemetry",
    "index": "idx_network_ops",
    "sample": "May 20 14:00:08 rtr-core-01 1849: *May 20 14:00:08.124 UTC: %LINK-3-UPDOWN: Interface GigabitEthernet0/0/1, changed state to up"
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
    "sample": "May 20 14:00:00 ap-aruba-515-01 stm[2948]: <501095> <NOTI> <ap-aruba-515-01 10.254.16.42> Auth success: 00:4e:01:aa:bb:cc: AP 10.254.16.42-d8:c7:c8:11:22:33-corp_wifi ESSID: corp_secure VLAN: 100"
  },
  {
    "id": "aruba:authmgr",
    "label": "Aruba Controller Authentication Manager",
    "vendor": "aruba",
    "category": "Aruba Networks",
    "index": "idx_wireless_ops",
    "sample": "May 20 14:00:00 wlc-aruba-7210 authmgr[1842]: <522008> <INFO> <wlc-aruba-7210 10.254.16.1> User Authentication Successful: username=corp\\\\alice.sec MAC=00:4e:01:11:22:33 IP=10.20.16.45 role=corp-employee VLAN=100"
  },
  {
    "id": "aruba:stm",
    "label": "Aruba Station Management (STM)",
    "vendor": "aruba",
    "category": "Aruba Networks",
    "index": "idx_wireless_ops",
    "sample": "May 20 14:00:00 wlc-aruba-7210 stm[2104]: <501065> <NOTI> <wlc-aruba-7210 10.254.16.1> Station 00:4e:01:aa:bb:cc: Associated with BSSID d8:c7:c8:11:22:33 on AP ap-aruba-515-01 Channel 36 Radio 0 (802.11ax/Wi-Fi 6)"
  },
  {
    "id": "cloudflare:json",
    "label": "Cloudflare Json",
    "vendor": "cloudflare",
    "category": "Cloudflare Core & R2",
    "index": "netops_logs",
    "sample": "{\"EdgeStartTimestamp\": \"2026-09-18T21:15:35Z\", \"ClientIP\": \"203.0.113.89\", \"ClientRequestHost\": \"api.acme.com\", \"ClientRequestMethod\": \"POST\", \"ClientRequestPath\": \"/v1/auth/token\", \"ClientRequestUserAgent\": \"Mozilla/5.0 (Windows NT 10.0; Win64; x64)\", \"EdgeResponseStatus\": 403, \"OriginIP\": \"10.100.2.14\", \"ClientRequestBytes\": 1420, \"EdgeResponseBytes\": 428, \"EdgeRateLimitAction\": \"block\", \"WAFAction\": \"block\", \"WAFAttackScore\": 92, \"EdgePath\": \"/us-east/edge-ingress-04\"}"
  },
  {
    "id": "cloudflare:r2:json",
    "label": "Cloudflare R2 Metrics",
    "vendor": "cloudflare",
    "category": "Cloudflare Core & R2",
    "index": "cisco_mdt_metrics",
    "sample": "{\"time\": 1789761340, \"event\": \"metric\", \"source\": \"cloudflare:r2\", \"sourcetype\": \"cloudflare:r2:json\", \"host\": \"cloudflare.r2.acme\", \"index\": \"cisco_mdt_metrics\", \"fields\": {\"metric_name:r2_operation_count\": 1, \"metric_name:r2_bytes_uploaded\": 2097152, \"metric_name:r2_latency_ms\": 14.8, \"account_id\": \"acme-cf-r2-prod\", \"bucket_name\": \"acme-telemetry-archive\", \"operation\": \"PutObject\", \"status_code\": 200}}"
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
    "sample": "{\"time\": 1789761345, \"event\": \"metric\", \"source\": \"extrahop:eda\", \"sourcetype\": \"extrahop:eda:metrics\", \"host\": \"core-switch-01\", \"index\": \"cisco_mdt_metrics\", \"fields\": {\"metric_name:extrahop_turnaround_time_ms\": 4.2, \"metric_name:extrahop_tcp_zero_window\": 0, \"metric_name:extrahop_rtt_ms\": 1.4, \"metric_name:extrahop_dns_error_count\": 0, \"device_oid\": \"1.3.6.1.4.1.3814.1.1.9281\", \"object_type\": \"network_device\", \"display_name\": \"Core-Spine-01\", \"macaddr\": \"00:22:bd:f8:11:00\", \"ipaddr4\": \"10.0.0.1\"}}"
  },
  {
    "id": "fgt_event",
    "label": "Fortinet Fortigate Sdwan Alert",
    "vendor": "other",
    "category": "Fortinet FortiGate",
    "index": "netops_logs",
    "sample": "date=2026-09-18 time=17:15:51 devname=\"FGT-Edge-01\" devid=\"FGT60E4Q16000001\" vd=\"root\" type=\"event\" subtype=\"sdwan\" level=\"warning\" logid=\"0100022923\" msg=\"SD-WAN SLA path quality degradation alert\" sla_rule=\"SLA_Voice_HighPri\" interface=\"wan2\" latency=142.5 jitter=28.4 packet_loss=6.8 link_status=\"degraded\" action=\"failover\""
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
    "sample": "date=2026-09-20 time=14:00:16 devname=\\\"fg-branch-01\\\" devid=\\\"FGT60E4Q18012840\\\" logid=\\\"0100032001\\\" type=\\\"event\\\" subtype=\\\"system\\\" level=\\\"information\\\" action=\\\"login\\\" status=\\\"success\\\" user=\\\"admin\\\" ui=\\\"gui(10.254.99.10)\\\" msg=\\\"Administrator admin logged in from gui\\\""
  },
  {
    "id": "fortigate_traffic",
    "label": "Fortinet FortiGate Traffic Log",
    "vendor": "paloalto",
    "category": "Fortinet FortiGate",
    "index": "idx_security_fw",
    "sample": "date=2026-09-20 time=14:00:17 devname=\\\"fg-branch-01\\\" devid=\\\"FGT60E4Q18012840\\\" logid=\\\"0000000013\\\" type=\\\"traffic\\\" subtype=\\\"forward\\\" level=\\\"notice\\\" srcip=10.20.10.45 srcport=54210 srcintf=\\\"lan\\\" dstip=198.51.100.80 dstport=443 dstintf=\\\"wan1\\\" polid=1 proto=6 action=\\\"accept\\\" duration=45 sentbyte=2410 rcvdbyte=89420"
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
    "vendor": "netskope",
    "category": "Netskope SSE Framework",
    "index": "netops_logs",
    "sample": "{\"timestamp\": 1789761360, \"vendor_product\": \"Netskope\", \"event_type\": \"dlp_violation\", \"user\": \"m.smith@acme.corp\", \"user_department\": \"Finance\", \"app\": \"Microsoft OneDrive\", \"activity\": \"Upload\", \"file_name\": \"Q3_Customer_PII_Export.xlsx\", \"file_size\": 248102, \"dlp_rule\": \"PCI_SSN_Strict_Rule\", \"dlp_incident_id\": \"DLP-2026-8812\", \"action\": \"block\", \"c_ip\": \"10.20.10.45\", \"s_ip\": \"13.107.136.9\", \"policy_name\": \"Corporate_DLP_CloudStorage_Enforcement\"}"
  },
  {
    "id": "netskope:sse",
    "label": "Netskope Security Service Edge (SSE)",
    "vendor": "netskope",
    "category": "Netskope SSE Framework",
    "index": "idx_security_fw",
    "sample": "{\\\"timestamp\\\": 1789840800, \\\"tenant_id\\\": \\\"corp-tenant-01\\\", \\\"traffic_type\\\": \\\"CloudApp\\\", \\\"app_name\\\": \\\"Salesforce\\\", \\\"user\\\": \\\"alice.sec@corp.internal\\\", \\\"client_ip\\\": \\\"198.51.100.42\\\", \\\"pop\\\": \\\"US-West-SJC\\\", \\\"action\\\": \\\"allow\\\", \\\"dlp_incident\\\": false, \\\"policy\\\": \\\"Default_Corporate_Cloud_Permit\\\"}"
  },
  {
    "id": "radware:ddos",
    "label": "Radware Csms Ddos",
    "vendor": "other",
    "category": "Radware CSMS & CWAF",
    "index": "netops_logs",
    "sample": "Sep 18 17:16:05 radware-defensepro CSMS-DDOS,timestamp=\"2026-09-18 17:16:05\",device_name=\"DP-01-Border\",attack_name=\"Volumetric UDP Flood\",policy=\"Perimeter-Shield\",dest_ip=\"198.51.100.10\",dest_port=53,threshold_pps=250000,actual_pps=890000,packet_volume_drop=640000,action=\"Drop\",severity=\"Critical\""
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
    "vendor": "f5",
    "category": "F5 BIG-IP",
    "index": "netops_logs",
    "sample": "Sep 18 17:16:15 f5-bigip-01.acme.local notice mcpd[8142]: 01070638:5: Pool /Common/pool_app_backend member /Common/10.0.10.51:8080 monitor status down. [ was up for 48hrs ]"
  },
  {
    "id": "f5:bigip:ltm",
    "label": "F5 BIG-IP Local Traffic Manager (LTM)",
    "vendor": "f5",
    "category": "F5 BIG-IP",
    "index": "idx_performance_metrics",
    "sample": "May 20 14:00:15 lb-f5-vip-01 notice tmm[14820]: 01010028:5: Pool /Common/pool_corp_web member /Common/10.20.1.10:80 monitor status up [ /Common/http: up ]"
  },
  {
    "id": "juniper:syslog",
    "label": "Juniper Syslog",
    "vendor": "juniper",
    "category": "Juniper Networks",
    "index": "netops_logs",
    "sample": "Sep 18 17:16:20 juniper-mx960-core-01 rpd[1422]: RPD_BGP_NEIGHBOR_STATE_CHANGED: BGP neighbor 10.255.10.1 (Internal AS 65000) changed state from Established to Idle (BGP notification sent: cease)"
  },
  {
    "id": "juniper:junos:syslog",
    "label": "Juniper Junos Syslog Transport",
    "vendor": "juniper",
    "category": "Juniper Networks",
    "index": "idx_network_ops",
    "sample": "May 20 14:00:20 rtr-juniper-ptx01 chassisd[1420]: %CHASSIS-5-CHASSISD_SNMP_ALARM: Alarm set: FPC color=YELLOW, class=CHASSIS, reason=FPC 0 Minor Temperature Alarm (52 C)"
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
    "vendor": "zscaler",
    "category": "Zscaler SSE Infrastructure",
    "index": "netops_logs",
    "sample": "Sep 18 17:16:31 zscaler-nss zscalernss-tunnel: datetime=Fri Sep 18 17:16:31 2026,tunnel_name=\"Zscaler-GRE-Toronto-Primary\",tunnel_status=\"DOWN\",remote_ip=198.51.100.200,local_ip=10.0.255.50,drop_reason=\"Keepalive timeout exceeded\",downtime_sec=45"
  },
  {
    "id": "zscaler:web",
    "label": "Zscaler Sse Web",
    "vendor": "zscaler",
    "category": "Zscaler SSE Infrastructure",
    "index": "netops_logs",
    "sample": "Sep 18 17:16:30 zscaler-nss zscalernss-web: datetime=Fri Sep 18 17:16:30 2026,user=alice.johnson@acme.corp,department=Engineering,location=Toronto-Branch,reqaction=Blocked,urlcategory=Malware_Sites,hostname=bad-download.compromised.com,clientip=10.10.40.12,serverip=198.51.100.99,reqmethod=GET,respcode=403,threatname=Trojan.Generic.KD,tunnel_id=TUN-TO-8891,policy_action=Block"
  },
  {
    "id": "datablaster:preflight",
    "label": "NetSpout Ingestion Preflight Probe",
    "vendor": "other",
    "category": "Other",
    "index": "idx_network_ops",
    "sample": "{\\\"timestamp\\\": 1789840800, \\\"component\\\": \\\"preflight\\\", \\\"check\\\": \\\"splunk_hec_port\\\", \\\"endpoint\\\": \\\"https://127.0.0.1:8888/services/collector\\\", \\\"http_status\\\": 200, \\\"status\\\": \\\"PASSED\\\", \\\"latency_ms\\\": 2.4}"
  },
  {
    "id": "datablaster:probe",
    "label": "NetSpout Telemetry Canary Probe",
    "vendor": "other",
    "category": "Other",
    "index": "idx_network_ops",
    "sample": "{\\\"timestamp\\\": 1789840800, \\\"probe_id\\\": \\\"probe-mdt-canary-01\\\", \\\"target_index\\\": \\\"cisco_mdt_metrics\\\", \\\"eps_measured\\\": 1000, \\\"rtt_ms\\\": 1.1, \\\"status\\\": \\\"HEALTHY\\\"}"
  },
  {
    "id": "nokia:sros:syslog",
    "label": "Nokia 7750 SR OS Syslog Facility",
    "vendor": "nokia",
    "category": "Other",
    "index": "idx_network_ops",
    "sample": "May 20 14:00:23 rtr-nokia-7750-01 MAJOR: SYSTEM #2041 Base SYSTEM-ENV-3-OVERTEMP: Chassis slot 1 temperature 68 C exceeds high warning threshold (65 C)"
  },
  {
    "id": "snmp:trap",
    "label": "Universal SNMP Trap Receiver Event",
    "vendor": "other",
    "category": "Other",
    "index": "idx_network_ops",
    "sample": "May 20 14:00:27 10.254.8.1 [UDP: [10.254.8.1]:54210->[10.254.99.50]:162]: DISMAN-EVENT-MIB::sysUpTimeInstance = Timeticks: (1849200) 5:08:12.00 .1.3.6.1.6.3.1.1.4.1.0 = OID: IF-MIB::linkUp IF-MIB::ifIndex = INTEGER: 2 IF-MIB::ifAdminStatus = INTEGER: up(1) IF-MIB::ifOperStatus = INTEGER: up(1)"
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

  // Pre-configured Multi-Vendor Telemetry Suites
  var MULTI_BATCH_PRESETS = {
    cisco_sdwan_suite: [
      "cisco:sdwan:linkhealth", "cisco:sdwan:BGP-5-ADJCHANGE", "cisco:sdwan:BGP-5-NBR_RESET",
      "cisco:sdwan:AAA-6-METHOD_LIST_STATE", "cisco:sdwan:DMI-5-SYNC_COMPLETE", "cisco:sdwan:ENVIRONMENTAL-1-ALERT"
    ],
    cisco_catalyst_suite: [
      "cisco:catalyst:clienthealth", "cisco:catalyst:devicehealth", "cisco:catalyst:networkhealth",
      "cisco:catalyst:rogue:threat_details", "cisco:catalyst:security:events", "cisco:catalyst:issue"
    ],
    cisco_duo_suite: [
      "cisco:duo:authentication", "cisco:duo:authentication_v2", "cisco:duo:push:prompt",
      "cisco:duo:endpoint:posture", "cisco:duo:zerotrust:policy", "cisco:duo:administrator"
    ],
    cisco_intersight_suite: [
      "cisco:intersight:compute", "cisco:intersight:alarms", "cisco:intersight:advisories",
      "cisco:intersight:metrics", "cisco:intersight:auditrecords"
    ],
    cisco_dc_suite: [
      "cisco:dc:nexus9k", "cisco:dc:nexus9k:syslog", "cisco:dc:aci:health",
      "cisco:dc:aci:events", "cisco:nexus", "cisco:nxos:syslog"
    ],
    cisco_security_suite: [
      "cisco:ftd:syslog", "cisco:ftd", "cisco:ise:syslog", "cisco:ise:nac:8021x",
      "cisco:ise:trustsec:sgt", "cisco:asa:syslog", "cisco:asa"
    ],
    all_cisco_stack: [
      "cisco:dc:nexus9k", "cisco:dnac:audit:logs", "cisco:dnac:client", "cisco:dnac:clienthealth",
      "cisco:dnac:compliance", "cisco:dnac:devicehealth", "cisco:dnac:issue", "cisco:dnac:networkhealth",
      "cisco:dnac:securityadvisory", "cisco:dnac:site:topology", "cisco:duo:account", "cisco:duo:activity",
      "cisco:duo:administrator", "cisco:duo:authentication", "cisco:duo:authentication_v2", "cisco:duo:endpoint",
      "cisco:duo:user", "cisco:ftd:syslog", "cisco:intersight:advisories", "cisco:intersight:alarms",
      "cisco:intersight:auditrecords", "cisco:intersight:compute", "cisco:intersight:contracts",
      "cisco:intersight:licenses", "cisco:intersight:metrics", "cisco:intersight:networkelements",
      "cisco:intersight:networkobjects", "cisco:intersight:profiles", "cisco:intersight:targets",
      "cisco:ise:radius:authz:policy", "cisco:ise:radius:policyset", "cisco:ise:syslog",
      "cisco:ise:tacacs:authz:policy", "cisco:ise:tacacs:policyset"
    ],
    multivendor_ngfw: [
      "pan:traffic", "pan:threat", "fortinet:fortigate", "fgt_traffic", "checkpoint:cef", "cisco:ftd:syslog"
    ],
    cloud_sase_suite: [
      "zscaler:zia", "zscaler:lss", "netskope:sse", "netskope:json", "cisco:thousandeyes:event", "cisco:thousandeyes:metric"
    ]
  };

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

    if (stepNum === 3 || stepNum === 4) {
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

  // Populate Single Sourcetype Dropdown with dynamic filtering and grouping
  function populateSingleSourcetypeCatalog(searchTerm) {
    var sel = $('#wizard-single-sourcetype-select');
    var currentVal = wizardState.selectedSourcetype || sel.val() || (SOURCETYPE_CATALOG[0] ? SOURCETYPE_CATALOG[0].id : '');
    sel.empty();

    var term = (searchTerm || '').toLowerCase().trim();
    var filtered = SOURCETYPE_CATALOG;
    if (term) {
      filtered = SOURCETYPE_CATALOG.filter(function(item) {
        var id = (item.id || '').toLowerCase();
        var lbl = (item.label || '').toLowerCase();
        var cat = (item.category || '').toLowerCase();
        var ven = (item.vendor || '').toLowerCase();
        return id.indexOf(term) !== -1 || lbl.indexOf(term) !== -1 || cat.indexOf(term) !== -1 || ven.indexOf(term) !== -1;
      });
    }

    if (filtered.length === 0) {
      var noOpt = $('<option></option>')
        .val(term)
        .text('Custom: ' + term + ' (Click to use)')
        .prop('selected', true);
      sel.append(noOpt);
      wizardState.selectedSourcetype = term;
      updateSinglePreview();
      return;
    }

    var grouped = {};
    filtered.forEach(function(item) {
      var cat = item.category || "General";
      if (!grouped[cat]) grouped[cat] = [];
      grouped[cat].push(item);
    });

    var hasSelected = false;
    Object.keys(grouped).forEach(function(cat) {
      var optgroup = $('<optgroup></optgroup>').attr('label', cat + ' (' + grouped[cat].length + ')');
      grouped[cat].forEach(function(item) {
        var opt = $('<option></option>').val(item.id).text(item.id + ' — ' + item.label);
        if (item.id === currentVal) {
          opt.prop('selected', true);
          hasSelected = true;
        }
        optgroup.append(opt);
      });
      sel.append(optgroup);
    });

    if (!hasSelected && filtered.length > 0) {
      sel.val(filtered[0].id);
    }

    wizardState.selectedSourcetype = sel.val();
    updateSinglePreview();
  }

  // Render Real-Time Autocomplete Dropdown Panel
  function renderSourcetypeAutocomplete(term) {
    var panel = $('#wizard-sourcetype-autocomplete');
    if (!panel.length) return;

    term = (term || '').toLowerCase().trim();
    if (!term) {
      panel.hide().empty();
      return;
    }

    var matches = SOURCETYPE_CATALOG.filter(function(item) {
      var id = (item.id || '').toLowerCase();
      var lbl = (item.label || '').toLowerCase();
      var cat = (item.category || '').toLowerCase();
      var ven = (item.vendor || '').toLowerCase();
      return id.indexOf(term) !== -1 || lbl.indexOf(term) !== -1 || cat.indexOf(term) !== -1 || ven.indexOf(term) !== -1;
    }).slice(0, 15);

    panel.empty();

    if (matches.length === 0) {
      var customRow = $(
        '<div class="st-autocomplete-item" data-id="' + term + '" style="padding: 10px 14px; cursor: pointer; border-bottom: 1px solid #1e293b; color: #38bdf8; font-family: monospace; font-size: 11px;">' +
          '➕ <b>Use custom sourcetype:</b> <span style="color: #4ade80;">' + term + '</span>' +
        '</div>'
      );
      panel.append(customRow);
      panel.show();
      return;
    }

    matches.forEach(function(item) {
      var row = $(
        '<div class="st-autocomplete-item" data-id="' + item.id + '" style="padding: 8px 12px; cursor: pointer; border-bottom: 1px solid #1e293b; transition: background 0.15s ease;">' +
          '<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 2px;">' +
            '<span style="color: #38bdf8; font-family: monospace; font-weight: 600; font-size: 11px;">' + item.id + '</span>' +
            '<span style="background: #1e293b; color: #94a3b8; font-size: 9px; padding: 2px 6px; border-radius: 3px;">' + (item.vendor || 'network').toUpperCase() + '</span>' +
          '</div>' +
          '<div style="color: #94a3b8; font-size: 10px; text-overflow: ellipsis; white-space: nowrap; overflow: hidden;">' + item.label + '</div>' +
        '</div>'
      );
      panel.append(row);
    });

    panel.show();
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
        var targetSelect = $('#wizard-target-index-select');
        if (targetSelect.find('option[value="' + st.index + '"]').length === 0) {
          targetSelect.append($('<option></option>').val(st.index).text(st.index + ' (Recommended)'));
        }
        targetSelect.val(st.index);
        updateActiveIndexDisplay();
      }
    } else if (selVal) {
      $('#wizard-single-preview').text("Custom Sourcetype: " + selVal + "\nReady to emit simulated payload to Splunk HEC.");
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
      updateSummaryBanner();
    });

    // Multi Batch Preset Dropdown Change
    $(document).on('change', '#wizard-multi-batch-preset-select', function() {
      var preset = $(this).val();
      if (preset && MULTI_BATCH_PRESETS[preset]) {
        var targets = MULTI_BATCH_PRESETS[preset];
        wizardState.selectedMultiSourcetypes = targets.slice();
        $('#multi-sourcetype-grid input').each(function() {
          var val = $(this).val();
          $(this).prop('checked', targets.indexOf(val) !== -1);
        });
        updateMultiSelectedCount();
        updateSummaryBanner();
      }
    });

    // Scenario Dropdown Change
    $(document).on('change', '#wizard-scenario-select', function() {
      var scId = $(this).val();
      wizardState.selectedScenario = scId;
      $('.scenario-pick-card').each(function() {
        var isThis = $(this).data('scenario') === scId;
        $(this).css('border', isThis ? '2px solid #0284c7' : '1px solid #334155');
        $(this).find('input').prop('checked', isThis);
      });
      updateSummaryBanner();
    });

    // Scenario Pick Card Click
    $(document).on('click', '.scenario-pick-card', function() {
      var scId = $(this).data('scenario');
      if (scId) {
        wizardState.selectedScenario = scId;
        $('#wizard-scenario-select').val(scId);
        $('.scenario-pick-card').css('border', '1px solid #334155').find('input').prop('checked', false);
        $(this).css('border', '2px solid #0284c7').find('input').prop('checked', true);
        updateSummaryBanner();
      }
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
    
    // Single Sourcetype Quick Search Filter & Real-Time Autocomplete
    $(document).on('input keyup', '#wizard-sourcetype-search', function() {
      var term = $(this).val();
      populateSingleSourcetypeCatalog(term);
      renderSourcetypeAutocomplete(term);
    });

    $(document).on('focus', '#wizard-sourcetype-search', function() {
      var term = $(this).val();
      if (term) renderSourcetypeAutocomplete(term);
    });

    // Autocomplete item selection
    $(document).on('click', '.st-autocomplete-item', function(e) {
      e.stopPropagation();
      var id = $(this).data('id');
      if (!id) return;
      $('#wizard-sourcetype-search').val(id);
      $('#wizard-sourcetype-autocomplete').hide();
      populateSingleSourcetypeCatalog(id);
      $('#wizard-single-sourcetype-select').val(id);
      wizardState.selectedSourcetype = id;
      updateSinglePreview();
    });

    $(document).on('mouseenter', '.st-autocomplete-item', function() {
      $(this).css('background', '#1e293b');
    }).on('mouseleave', '.st-autocomplete-item', function() {
      $(this).css('background', 'transparent');
    });

    // Close autocomplete on click outside
    $(document).on('click', function(e) {
      if (!$(e.target).closest('#single-catalog-container').length) {
        $('#wizard-sourcetype-autocomplete').hide();
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
