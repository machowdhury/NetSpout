/*
 * Splunk App: NetSpout (TA-network-data-blaster)
 * View Script: scenario_builder.js
 * Scenario Builder, OpenConfig MDT Telemetry Emitter & Path Orchestrator
 */

require([
  'jquery',
  'splunkjs/mvc',
  'splunkjs/mvc/simplexml/ready!'
], function($, mvc) {
  'use strict';

  // REST URL and CSRF Helpers
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

  // Multi-Vendor Syslog & Event Platform Matrix
  var PLATFORM_MATRIX = {
    "identity": [
      { id: "cisco_ise", name: "Cisco ISE (Identity Services Engine)", index: "idx_network_ops", sourcetypes: ["cisco:ise:nac:8021x", "cisco:ise:byod:provisioning", "cisco:ise:trustsec:sgt", "cisco:ise:deviceadmin:tacacs", "cisco:ise:guest:voucher"], template: 'CISE_Passed_Authentications 0001847295 1 0 2026-09-19T14:00:00.000Z +00:00 0029481925 5200 NOTICE Passed-Authentication: Authentication succeeded, ConfigVersionId=127, Device IP Address=10.254.8.1, DestinationPort=1812, UserName=corp\\alice.sec, Protocol=Radius, NAS-Port-Id=GigabitEthernet1/0/24, Framed-IP-Address=10.20.10.45, EapAuthentication=EAP-TLS, IdentityGroup=SecOps_Endpoints, SelectedAuthorizationProfiles=TrustSec_SecOps_Permit' },
      { id: "cisco_duo", name: "Cisco Duo (Cloud MFA & Zero Trust)", index: "idx_security_fw", sourcetypes: ["cisco:duo:push:prompt", "cisco:duo:endpoint:posture", "cisco:duo:sso:saml", "cisco:duo:zerotrust:policy", "cisco:duo:remote:vpn"], template: '{"timestamp":1789840800,"iso_timestamp":"2026-09-19T14:00:00.000Z","event_type":"authentication","factor":"duo_push","result":"SUCCESS","reason":"user_approved","user":{"name":"m.chowdhury@corp.internal","groups":["Enterprise_Admins","NetDevOps"]},"application":{"name":"Splunk Enterprise Production NOC","key":"DI94810294810"},"auth_device":{"name":"iPhone 15 Pro","ip":"198.51.100.42","location":{"city":"San Jose","state":"California","country":"US"}},"txid":"duo-tx-9948201"}' }
    ],
    "storage": [
      { id: "cisco_san", name: "Cisco MDS 9700 SAN Director", index: "idx_performance_metrics", sourcetypes: ["cisco:mds:san:fc"], template: '%PORT-3-CREDIT_LOSS: Interface fc1/14 Tx credit loss detected. Peer device slow drain. Dropped frames: 842. B2B credit recovery initiated.' },
      { id: "netapp_nas", name: "NetApp ONTAP Storage Cluster", index: "idx_performance_metrics", sourcetypes: ["netapp:ontap:nas"], template: '{"timestamp":"2026-09-19T14:00:00.000Z","cluster":"netapp-ontap-01","node":"node-01","vserver":"vs_prod","volume":"vol_analytics","iops":128400,"throughput_mbps":1480,"latency_ms":48.2,"protocol":"nfs4.1","status":"DEGRADED"}' }
    ],
    "firewall": [
      { id: "paloalto", name: "Palo Alto Networks (PAN-OS)", index: "idx_security_fw", sourcetypes: ["pan:traffic", "pan:threat", "pan:system"], template: '1,2026/09/19 14:00:00,001801000001,TRAFFIC,drop,1,2026/09/19 14:00:00,198.51.100.42,10.254.1.10,0.0.0.0,0.0.0.0,rule_syn_flood,vsys1,untrust,trust,ethernet1/1,ethernet1/2,default-log-forwarding,2026/09/19 14:00:00,0,1,54210,443,0,0,0x0,tcp,deny,64,64,0,1,2026/09/19 14:00:00,0,any,0,12345678,0x0,United States,10.0.0.0-10.255.255.255,0,1,0,threat-drop,0,0,0,0,,pa-5450-fw01,from-policy' },
      { id: "fortinet", name: "Fortinet FortiGate (FortiOS)", index: "idx_security_fw", sourcetypes: ["fortinet:fortigate", "fortigate_traffic", "fortigate_event"], template: 'date=2026-09-19 time=14:00:00 devname="fortigate-3700d" devid="FG370D4615800001" eventtime=1789840800 level="warning" vd="root" type="traffic" subtype="forward" action="accept" policyid=12 sessionid=9872411 srcip=10.254.2.50 dstip=198.51.100.80 proto=6 sentbyte=2400 rcvdbyte=8900 utmaction="allow" transport="sdwan" sla="violated" msg="dynamic path failover to biz-internet"' },
      { id: "checkpoint", name: "Check Point Quantum (Gaia)", index: "idx_security_fw", sourcetypes: ["checkpoint:cef"], template: 'CEF:0|Check Point|VPN-1 & FireWall-1|Check Point|Log|drop|act=drop suser=mchen src=10.40.12.88 spt=54215 dst=198.51.100.66 dpt=23 proto=tcp product=VPN-1 & FireWall-1 cs1Label=Rule cs1=Deny_Telnet_Global' },
      { id: "cisco_ftd", name: "Cisco Secure Firewall (FTD / ASA)", index: "idx_security_fw", sourcetypes: ["cisco:ftd:syslog", "cisco:asa:syslog", "cisco:asa"], template: '%FTD-1-430002: EventPriority: Low, DeviceUUID: 4f1a23-8991, SnortId: 1:31456, Event: MALWARE-CNC Win.Trojan.CobaltStrike beacon detected, SrcIP: 10.40.12.88, DstIP: 198.51.100.99, Action: Dropped' }
    ],
    "router": [
      { id: "cisco_ios", name: "Cisco IOS-XR / IOS-XE (8000 / ASR)", index: "idx_network_ops", sourcetypes: ["cisco:ios", "cisco:ios:syslog", "cisco:ios:mdt", "cisco:metrics"], template: '<189>Sep 19 14:00:00 rtr-cisco-8000-01 %LINEPROTO-5-UPDOWN: Line protocol on Interface HundredGigE0/0/0/0, changed state to up' },
      { id: "cisco_sdwan", name: "Cisco SD-WAN (Viptela OS)", index: "idx_network_ops", sourcetypes: ["cisco:sdwan:syslog", "cisco:sdwan:linkhealth", "cisco:sdwan:sitehealth", "cisco:sdwan:tunnelhealth", "cisco:sdwan:BGP-5-ADJCHANGE"], template: '{"edge_device": "sdwan-branch-vedge", "tunnel": "biz-internet", "latency_ms": 14.2, "jitter_ms": 1.1, "loss_percentage": 0.02, "sla_status": "in_sla"}' },
      { id: "juniper", name: "Juniper Networks (Junos PTX / MX)", index: "idx_network_ops", sourcetypes: ["juniper:junos", "juniper:syslog"], template: '<14>Sep 19 14:00:00 rtr-juniper-ptx01 rpd[4821]: %ROUTING-4-BGP_PEER_FLAP: BGP peer 198.51.100.1 (External AS 65001) state changed from Established to Idle (HoldTimer expired)' },
      { id: "nokia", name: "Nokia Service Router (SR OS 7750)", index: "idx_network_ops", sourcetypes: ["nokia:sros", "nokia:sros:syslog"], template: '<165>Sep 19 14:00:00 pe01-toronto-7750 Major: BGP #2002 Base Peer 10.254.0.1: Peer entered Established state; Session uptime 4d 12h.' }
    ],
    "switch_dc": [
      { id: "arista", name: "Arista Networks (EOS / 7280R3)", index: "idx_performance_metrics", sourcetypes: ["arista:eos", "arista:eos:syslog", "arista:telemetry:json"], template: '{"timestamp": 1789840800.0, "device": "sw-arista-7280-01", "interface": "Ethernet1/1", "pfc_pause_rx": 48201, "ecn_marked_packets": 1284, "buffer_utilization_pct": 98.4, "status": "CONGESTION_ROCE_V2"}' },
      { id: "cisco_nexus", name: "Cisco Nexus NX-OS & ACI Fabric", index: "idx_network_ops", sourcetypes: ["cisco:nexus", "cisco:nxos", "cisco:nxos:syslog", "cisco:dc:nexus9k", "cisco:dc:aci:health"], template: '<187>Sep 19 14:00:00 dc-spine-nexus %ETHPORT-5-IF_DOWN_LINK_FAILURE: Interface Ethernet1/1 is down (Link failure)' }
    ],
    "switch_campus": [
      { id: "cisco_cat", name: "Cisco Catalyst 9600/9300 Fabric", index: "idx_network_ops", sourcetypes: ["cisco:catalyst:networkhealth", "cisco:catalyst:devicehealth", "cisco:catalyst:compliance", "cisco:catalyst:issue"], template: '{"deviceName": "sw-cat9600-01.campus.internal", "healthScore": 99, "cpuScore": 100, "memoryScore": 98, "packetScore": 100, "linkHealth": 99}' },
      { id: "aruba_cx", name: "Aruba Networks (AOS-CX 8300)", index: "idx_network_ops", sourcetypes: ["aruba:syslog"], template: '<189>Sep 19 14:00:00 aruba-cx-switch01 hpe-authmgr[1142]: User A4:83:E7:4B:11:02 authenticated on port 1/1/12 via 802.1X VLAN 40' }
    ],
    "loadbalancer": [
      { id: "f5", name: "F5 Networks (BIG-IP LTM / AFM)", index: "idx_network_ops", sourcetypes: ["f5:bigip:syslog", "f5:bigip:ltm"], template: '<133>Sep 19 14:00:00 bigip-ltm-cluster tmm[8921]: 01010028:5: No members available for pool /Common/pool_ai_inference_vllm (Threshold exceeded)' }
    ],
    "sase": [
      { id: "zscaler", name: "Zscaler SSE (ZIA / ZPA / LSS)", index: "idx_security_fw", sourcetypes: ["zscaler:zia", "zscaler:tunnel", "zscaler:web"], template: '{"datetime":"2026-09-19 14:00:00","user":"eng-dev@corp.internal","app":"ChatGPT-Enterprise","action":"Allow","proto":"HTTPS","url":"https://api.openai.com/v1/models","threatname":"None","riskscore":"0","egress_dc":"iad-zscaler"}' },
      { id: "netskope", name: "Netskope SSE / CASB", index: "idx_security_fw", sourcetypes: ["netskope:sse", "netskope:json"], template: '{"timestamp":"2026-09-19T14:00:00Z","app":"Box","user":"user@corp.internal","action":"dlp_scan","dlp_incident":"false","bandwidth":1048576}' }
    ],
    "wireless": [
      { id: "aruba_ap", name: "Aruba Wireless AP (AP-555/635)", index: "idx_wireless_ops", sourcetypes: ["aruba", "aruba:syslog", "aruba:authmgr"], template: '<189>Sep 19 14:00:00 aruba-ap635-campus stm[3411]: <NOTI> Client 9c:76:13:aa:bb:cc roam failure to BSSID 00:1a:1e:88:99:aa reason="reassociation timeout"' },
      { id: "cisco_wlc", name: "Cisco Catalyst 9800 WLC", index: "idx_wireless_ops", sourcetypes: ["cisco:catalyst:client", "cisco:catalyst:clienthealth", "cisco:catalyst:rogue:allowed"], template: '{"clientMac": "A4:83:E7:4B:11:02", "healthScore": 94, "snr": 38, "rssi": -55, "txRate": 866000000, "band": "5GHz", "ssid": "ACME-CORP-SECURE"}' },
      { id: "meraki_mr", name: "Cisco Meraki MR Cloud Access Points", index: "idx_wireless_ops", sourcetypes: ["meraki:accesspoints", "meraki:devices", "meraki:appliancesdwanstatistics"], template: '{"name": "MR46-Floor1-East", "serial": "Q2MN-1182-3341", "clientsCount": 24, "channel24": 6, "channel5": 149, "powerUsage": 12.4}' }
    ],
    "optical": [
      { id: "nokia_opt", name: "Nokia 100G Optical DWDM / TI-LFA", index: "idx_network_ops", sourcetypes: ["nokia:sros", "nokia:sros:syslog"], template: '<134>Sep 19 14:00:00 core-nokia-7750 OPTICAL-4-RX_POWER_DEGRADE: Transceiver port 1/1/c1/1 optical power dropped to -26.4 dBm. Pre-FEC BER exceeds 1.2e-3. TI-LFA Fast Reroute triggered.' }
    ],
    "snmp": [
      { id: "sc4snmp_poll", name: "Splunk Connect for SNMP (Polling Walk)", index: "cisco_mdt_metrics", sourcetypes: ["sc4snmp:metric"], template: '{"time": 1789840800.0, "event": "metric", "source": "sc4snmp", "sourcetype": "sc4snmp:metric", "host": "rtr-cisco-8000-01.corp.internal", "index": "cisco_mdt_metrics", "fields": {"metric_name:ifInOctets": 58920140.0, "metric_name:ifOutOctets": 84920194.0, "metric_name:ifOperStatus": 1.0, "_value": 58920140.0, "ifIndex": "1", "ifDescr": "GigabitEthernet0/0/1", "device": "rtr-cisco-8000-01", "vendor": "cisco"}}' },
      { id: "sc4snmp_trap", name: "Splunk Connect for SNMP (Traps)", index: "idx_network_ops", sourcetypes: ["sc4snmp:event"], template: '{"time": 1789840800.0, "source": "sc4snmp:trap", "sourcetype": "sc4snmp:event", "host": "rtr-cisco-8000-01.corp.internal", "index": "idx_network_ops", "event": {"snmp_trap_name": "linkDown", "snmp_trap_oid": "1.3.6.1.6.3.1.1.5.3", "enterprise": "1.3.6.1.4.1", "severity": "critical", "varbinds": {"ifIndex": 1, "ifAdminStatus": 1, "ifOperStatus": 2, "ifDescr": "GigabitEthernet0/0/1"}}, "fields": {"snmp_trap_name": "linkDown", "snmp_trap_oid": "1.3.6.1.6.3.1.1.5.3", "severity": "critical"}}' }
    ]
  };

  // Pre-Built Topology Presets (All 22 Network Architectures & Scenarios)
  var TOPOLOGY_PRESETS = {
    "openconfig_core": {
      title: "OpenConfig MDT Core Fabric (Cisco 8000, Juniper PTX, Arista 7280R, Cat 9600)",
      badge: "4 MDT gNMI Nodes",
      nodes: [
        { id: "oc_cisco8k", name: "rtr-cisco-8000-01", role: "Core Backbone Router", vendor: "Cisco", class: "router", x: 140, y: 130, ip: "10.254.0.1", index: "cisco_mdt_metrics", platform: "cisco_ios", color: "#0284c7" },
        { id: "oc_juniper_ptx", name: "rtr-juniper-ptx01", role: "Core Spine Router", vendor: "Juniper", class: "router", x: 420, y: 90, ip: "10.254.0.2", index: "cisco_mdt_metrics", platform: "juniper", color: "#38bdf8" },
        { id: "oc_arista_7280", name: "sw-arista-7280-01", role: "DC Spine Switch", vendor: "Arista", class: "switch_dc", x: 700, y: 150, ip: "10.254.1.1", index: "cisco_mdt_metrics", platform: "arista", color: "#10b981" },
        { id: "oc_cat9600", name: "sw-cat9600-01", role: "Campus / DC Leaf", vendor: "Cisco", class: "switch_campus", x: 420, y: 310, ip: "10.254.2.1", index: "cisco_mdt_metrics", platform: "cisco_cat", color: "#8b5cf6" }
      ],
      links: [
        { from: "oc_cisco8k", to: "oc_juniper_ptx", label: "400GE-ZR+ / BGP EVPN" },
        { from: "oc_juniper_ptx", to: "oc_arista_7280", label: "100GE / gNMI Stream" },
        { from: "oc_arista_7280", to: "oc_cat9600", label: "40GE MDT Telemetry" },
        { from: "oc_cisco8k", to: "oc_cat9600", label: "100GE L3 Trunk" }
      ]
    },
    "multivendor_enterprise": {
      title: "Enterprise 5-Tier Backbone (Palo Alto, Fortinet, Juniper, Nokia, Arista, F5, Meraki)",
      badge: "10 Active Corridor Nodes",
      nodes: [
        { id: "sase", name: "zscaler-edge-ingress", role: "Cloud SASE Gateway", vendor: "Zscaler", class: "sase", x: 70, y: 70, ip: "165.225.1.1", index: "idx_security_fw", platform: "zscaler", color: "#0ea5e9" },
        { id: "fw", name: "pa-5450-perimeter", role: "Perimeter Next-Gen FW", vendor: "Palo Alto", class: "firewall", x: 210, y: 150, ip: "10.254.1.1", index: "idx_security_fw", platform: "paloalto", color: "#f97316" },
        { id: "sdwan", name: "fortigate-3700d-sdwan", role: "SD-WAN Edge Hub", vendor: "Fortinet", class: "firewall", x: 350, y: 80, ip: "10.254.2.1", index: "idx_security_fw", platform: "fortinet", color: "#22c55e" },
        { id: "core", name: "core-juniper-mx960", role: "Core MPLS/BGP Router", vendor: "Juniper", class: "router", x: 490, y: 220, ip: "10.254.3.1", index: "idx_network_ops", platform: "juniper", color: "#3b82f6" },
        { id: "nokia", name: "core-nokia-7750", role: "100G Coherent Optical", vendor: "Nokia", class: "optical", x: 630, y: 120, ip: "10.254.4.1", index: "idx_network_ops", platform: "nokia_opt", color: "#a855f7" },
        { id: "spine", name: "dc-spine-arista7060", role: "AI DC Spine Switch", vendor: "Arista", class: "switch_dc", x: 770, y: 240, ip: "10.254.5.1", index: "idx_performance_metrics", platform: "arista", color: "#10b981" },
        { id: "gpu", name: "nvidia-quantum-h100", role: "AI GPU Fabric Cluster", vendor: "NVIDIA", class: "switch_dc", x: 910, y: 350, ip: "10.254.6.1", index: "idx_performance_metrics", platform: "arista", color: "#84cc16" },
        { id: "f5", name: "bigip-ltm-cluster", role: "App Load Balancer", vendor: "F5", class: "loadbalancer", x: 770, y: 390, ip: "10.254.7.1", index: "idx_network_ops", platform: "f5", color: "#ef4444" },
        { id: "campus", name: "campus-cat9k-access", role: "Campus Access Switch", vendor: "Cisco", class: "switch_campus", x: 350, y: 330, ip: "10.254.8.1", index: "idx_network_ops", platform: "cisco_cat", color: "#38bdf8" },
        { id: "wifi", name: "aruba-ap635-campus", role: "Campus WiFi 6E AP", vendor: "Aruba", class: "wireless", x: 210, y: 390, ip: "10.254.9.1", index: "idx_wireless_ops", platform: "aruba_ap", color: "#eab308" }
      ],
      links: [
        { from: "sase", to: "fw", label: "GRE / IPsec" },
        { from: "fw", to: "sdwan", label: "100G Trunk" },
        { from: "sdwan", to: "core", label: "BGP AS 65001" },
        { from: "core", to: "nokia", label: "100G DWDM" },
        { from: "nokia", to: "spine", label: "400G SR-OS" },
        { from: "spine", to: "gpu", label: "RoCE v2 PFC" },
        { from: "spine", to: "f5", label: "LACP 100G" },
        { from: "sdwan", to: "campus", label: "802.1Q Core" },
        { from: "campus", to: "wifi", label: "PoE+ 10GE" }
      ]
    },
    "roce_ai_fabric": {
      title: "AI Data Center Fabric - RoCE v2 Buffer Congestion (Arista, NVIDIA, Nexus)",
      badge: "4 GPU Fabric Nodes",
      nodes: [
        { id: "gpu_worker", name: "gpu-worker-01", role: "NVIDIA H100 SuperPOD", vendor: "NVIDIA", class: "switch_dc", x: 140, y: 220, ip: "10.200.1.1", index: "idx_performance_metrics", platform: "arista", color: "#84cc16" },
        { id: "leaf_qm", name: "leaf-quantum-01", role: "NVIDIA Quantum QM9700", vendor: "NVIDIA", class: "switch_dc", x: 380, y: 110, ip: "10.200.0.1", index: "idx_performance_metrics", platform: "arista", color: "#10b981" },
        { id: "spine_7060", name: "spine-arista-7060", role: "Arista 7060X5 800G Spine", vendor: "Arista", class: "switch_dc", x: 640, y: 190, ip: "10.200.0.10", index: "idx_performance_metrics", platform: "arista", color: "#0ea5e9" },
        { id: "storage_nexus", name: "nexus-storage-01", role: "Nexus 9364C RoCE Storage", vendor: "Cisco", class: "switch_dc", x: 380, y: 320, ip: "10.200.0.20", index: "idx_network_ops", platform: "cisco_nexus", color: "#f59e0b" }
      ],
      links: [
        { from: "gpu_worker", to: "leaf_qm", label: "RoCE v2 400G PFC" },
        { from: "leaf_qm", to: "spine_7060", label: "800G ECN Fabric" },
        { from: "spine_7060", to: "storage_nexus", label: "NVMe-oF RoCE" },
        { from: "gpu_worker", to: "storage_nexus", label: "Direct RDMA" }
      ]
    },
    "sdwan_branch": {
      title: "SD-WAN Branch Brownout & Dynamic SLA Failover (FortiGate, Cisco vEdge)",
      badge: "4 WAN Nodes",
      nodes: [
        { id: "branch_edge", name: "sdwan-branch-vedge", role: "Catalyst 8300 SD-WAN", vendor: "Cisco", class: "router", x: 140, y: 200, ip: "10.10.1.1", index: "idx_network_ops", platform: "cisco_sdwan", color: "#0284c7" },
        { id: "inet_biz", name: "inet-circuit-biz", role: "Biz Internet Primary ISP", vendor: "Fortinet", class: "firewall", x: 400, y: 100, ip: "198.51.100.1", index: "idx_security_fw", platform: "fortinet", color: "#22c55e" },
        { id: "lte_5g", name: "lte-backup-5g", role: "5G Cellular Backup Circuit", vendor: "Cisco", class: "router", x: 400, y: 300, ip: "203.0.113.1", index: "idx_network_ops", platform: "cisco_sdwan", color: "#f97316" },
        { id: "hub_core", name: "hub-vedge-core", role: "HQ Aggregation Hub", vendor: "Cisco", class: "router", x: 680, y: 200, ip: "10.254.0.1", index: "idx_network_ops", platform: "cisco_sdwan", color: "#8b5cf6" }
      ],
      links: [
        { from: "branch_edge", to: "inet_biz", label: "IPsec Primary (SLA)" },
        { from: "branch_edge", to: "lte_5g", label: "5G Standby" },
        { from: "inet_biz", to: "hub_core", label: "BFD Echo 15ms" },
        { from: "lte_5g", to: "hub_core", label: "Failover Tunnel" }
      ]
    },
    "campus_security": {
      title: "Campus Core Rogue AP & MAC Flapping Threat (Catalyst 9300, WLC, ISE)",
      badge: "4 Security Nodes",
      nodes: [
        { id: "cat9300_sw", name: "cat9300-access-sw01", role: "Catalyst 9300 Access", vendor: "Cisco", class: "switch_campus", x: 140, y: 200, ip: "10.30.1.1", index: "idx_network_ops", platform: "cisco_cat", color: "#38bdf8" },
        { id: "rogue_ap", name: "rogue-ap-floor3", role: "Rogue Evil-Twin AP", vendor: "Cisco", class: "wireless", x: 400, y: 100, ip: "10.30.1.99", index: "idx_wireless_ops", platform: "cisco_wlc", color: "#ef4444" },
        { id: "cat9800_wlc", name: "cat9800-wlc-core", role: "Catalyst 9800 WLC", vendor: "Cisco", class: "wireless", x: 400, y: 300, ip: "10.30.0.1", index: "idx_wireless_ops", platform: "cisco_wlc", color: "#eab308" },
        { id: "cisco_ise", name: "cisco-ise-node01", role: "Cisco ISE Identity Engine", vendor: "Cisco", class: "firewall", x: 680, y: 200, ip: "10.30.0.10", index: "idx_security_fw", platform: "cisco_ftd", color: "#a855f7" }
      ],
      links: [
        { from: "cat9300_sw", to: "rogue_ap", label: "Unauth Port Gi1/0/14" },
        { from: "cat9300_sw", to: "cat9800_wlc", label: "CAPWAP Tunnel" },
        { from: "cat9800_wlc", to: "cisco_ise", label: "RADIUS CoA Quarantine" },
        { from: "cat9300_sw", to: "cisco_ise", label: "802.1X Auth" }
      ]
    },

    // 11 Network Architectures (PAN to GAN)
    "arch_pan": {
      title: "PAN: Personal Area Network - IoT Sensor Cluster & Bluetooth Mesh",
      badge: "IoT Mesh Tier",
      nodes: [
        { id: "pan_sensor1", name: "ble-sensor-rack01", role: "Bluetooth LE Beacon", vendor: "Generic", class: "switch_dc", x: 140, y: 120, ip: "192.168.99.11", index: "idx_network_ops", platform: "cisco_ios", color: "#10b981" },
        { id: "pan_sensor2", name: "zigbee-env-temp02", role: "Zigbee Thermal Probe", vendor: "Generic", class: "switch_dc", x: 140, y: 280, ip: "192.168.99.12", index: "idx_network_ops", platform: "cisco_ios", color: "#10b981" },
        { id: "pan_gateway", name: "iot-pan-gateway01", role: "PAN Micro-Gateway", vendor: "Cisco", class: "router", x: 420, y: 200, ip: "10.254.99.1", index: "idx_network_ops", platform: "cisco_ios", color: "#0284c7" },
        { id: "pan_collector", name: "iot-telemetry-server", role: "OTel IoT Collector", vendor: "Generic", class: "switch_dc", x: 700, y: 200, ip: "10.254.99.50", index: "idx_network_ops", platform: "cisco_ios", color: "#8b5cf6" }
      ],
      links: [
        { from: "pan_sensor1", to: "pan_gateway", label: "BLE 5.2 Mesh" },
        { from: "pan_sensor2", to: "pan_gateway", label: "Zigbee 3.0" },
        { from: "pan_gateway", to: "pan_collector", label: "MQTT / CoAP TLS" }
      ]
    },
    "arch_lan": {
      title: "LAN: Local Area Network - Enterprise Campus Switching & 802.1Q",
      badge: "Campus L2/L3 Tier",
      nodes: [
        { id: "lan_client", name: "workstation-corp-01", role: "Enterprise End User", vendor: "Generic", class: "switch_campus", x: 140, y: 200, ip: "10.20.10.45", index: "idx_network_ops", platform: "cisco_cat", color: "#38bdf8" },
        { id: "lan_acc", name: "cat9300-access-sw", role: "Catalyst 9300 Access", vendor: "Cisco", class: "switch_campus", x: 380, y: 200, ip: "10.20.10.1", index: "idx_network_ops", platform: "cisco_cat", color: "#0284c7" },
        { id: "lan_dist", name: "cat9500-dist-sw", role: "Catalyst 9500 Distribution", vendor: "Cisco", class: "switch_campus", x: 620, y: 200, ip: "10.20.0.1", index: "idx_network_ops", platform: "cisco_cat", color: "#8b5cf6" },
        { id: "lan_ise", name: "ise-pan01-auth", role: "Cisco ISE 802.1X NAC", vendor: "Cisco", class: "firewall", x: 620, y: 340, ip: "10.20.0.50", index: "idx_security_fw", platform: "cisco_ftd", color: "#a855f7" }
      ],
      links: [
        { from: "lan_client", to: "lan_acc", label: "802.1X EAP-TLS" },
        { from: "lan_acc", to: "lan_dist", label: "100G 802.1Q Trunk" },
        { from: "lan_acc", to: "lan_ise", label: "RADIUS AAA Port 1812" }
      ]
    },
    "arch_wlan": {
      title: "WLAN: Wireless Local Area Network - Catalyst 9800 & Meraki Wi-Fi 6E/7",
      badge: "Enterprise Wi-Fi Tier",
      nodes: [
        { id: "wlan_mr", name: "meraki-mr56-east", role: "Meraki MR56 Wi-Fi 6 AP", vendor: "Cisco", class: "wireless", x: 140, y: 120, ip: "10.40.1.10", index: "idx_wireless_ops", platform: "meraki_mr", color: "#10b981" },
        { id: "wlan_cat", name: "catalyst-9130-west", role: "Catalyst 9130AX AP", vendor: "Cisco", class: "wireless", x: 140, y: 280, ip: "10.40.1.20", index: "idx_wireless_ops", platform: "cisco_wlc", color: "#0284c7" },
        { id: "wlan_wlc", name: "cat9800-wlc-cluster", role: "Catalyst 9800 WLC HA", vendor: "Cisco", class: "wireless", x: 420, y: 200, ip: "10.40.0.1", index: "idx_wireless_ops", platform: "cisco_wlc", color: "#eab308" },
        { id: "wlan_dash", name: "catalyst-center-assurance", role: "DNA-C Wireless Assurance", vendor: "Cisco", class: "switch_campus", x: 700, y: 200, ip: "10.40.0.100", index: "idx_network_ops", platform: "cisco_cat", color: "#8b5cf6" }
      ],
      links: [
        { from: "wlan_mr", to: "wlan_wlc", label: "CAPWAP / Cloud Link" },
        { from: "wlan_cat", to: "wlan_wlc", label: "CAPWAP Data & Control" },
        { from: "wlan_wlc", to: "wlan_dash", label: "Telemetry Stream" }
      ]
    },
    "arch_can": {
      title: "CAN: Campus Area Network - Multi-Building Backbone & Catalyst Center",
      badge: "Multi-Building Core",
      nodes: [
        { id: "can_bldga", name: "bldg-a-cat9500", role: "Building A Aggregation", vendor: "Cisco", class: "switch_campus", x: 140, y: 120, ip: "10.100.1.1", index: "idx_network_ops", platform: "cisco_cat", color: "#0284c7" },
        { id: "can_bldgb", name: "bldg-b-cat9500", role: "Building B Aggregation", vendor: "Cisco", class: "switch_campus", x: 140, y: 280, ip: "10.100.2.1", index: "idx_network_ops", platform: "cisco_cat", color: "#0284c7" },
        { id: "can_core", name: "cat9600-quad-sup", role: "Campus Core 9600 Redundant", vendor: "Cisco", class: "switch_campus", x: 440, y: 200, ip: "10.100.0.1", index: "idx_network_ops", platform: "cisco_cat", color: "#8b5cf6" },
        { id: "can_dc", name: "dc-spine-nexus", role: "Enterprise DC Interconnect", vendor: "Cisco", class: "switch_dc", x: 720, y: 200, ip: "10.100.0.254", index: "idx_network_ops", platform: "cisco_nexus", color: "#10b981" }
      ],
      links: [
        { from: "can_bldga", to: "can_core", label: "100G Dark Fiber (OSPF)" },
        { from: "can_bldgb", to: "can_core", label: "100G Dark Fiber (OSPF)" },
        { from: "can_core", to: "can_dc", label: "400G L3 EVPN Link" }
      ]
    },
    "arch_man": {
      title: "MAN: Metropolitan Area Network - 100G Carrier Ethernet Ring & G.8032 ERPS",
      badge: "Metro Ring 100G",
      nodes: [
        { id: "man_n1", name: "metro-nokia-pe01", role: "Metro Hub North", vendor: "Nokia", class: "optical", x: 160, y: 90, ip: "10.220.0.1", index: "idx_network_ops", platform: "nokia_opt", color: "#a855f7" },
        { id: "man_n2", name: "metro-juniper-pe02", role: "Metro Hub East", vendor: "Juniper", class: "router", x: 640, y: 90, ip: "10.220.0.2", index: "idx_network_ops", platform: "juniper", color: "#3b82f6" },
        { id: "man_n3", name: "metro-cisco-pe03", role: "Metro Hub South", vendor: "Cisco", class: "router", x: 640, y: 310, ip: "10.220.0.3", index: "idx_network_ops", platform: "cisco_ios", color: "#0284c7" },
        { id: "man_n4", name: "metro-arista-pe04", role: "Metro Hub West", vendor: "Arista", class: "switch_dc", x: 160, y: 310, ip: "10.220.0.4", index: "idx_performance_metrics", platform: "arista", color: "#10b981" }
      ],
      links: [
        { from: "man_n1", to: "man_n2", label: "100GE G.8032 ERPS" },
        { from: "man_n2", to: "man_n3", label: "100GE G.8032 ERPS" },
        { from: "man_n3", to: "man_n4", label: "100GE G.8032 ERPS" },
        { from: "man_n4", to: "man_n1", label: "RPL (Ring Protection Link)" }
      ]
    },
    "arch_wan": {
      title: "WAN: Wide Area Network - Global BGP/MPLS L3VPN Backbone & DWDM",
      badge: "Inter-Continental WAN",
      nodes: [
        { id: "wan_ny", name: "cisco8k-nyc-core", role: "North America Core P/PE", vendor: "Cisco", class: "router", x: 140, y: 140, ip: "198.51.100.1", index: "cisco_mdt_metrics", platform: "cisco_ios", color: "#0284c7" },
        { id: "wan_lon", name: "ptx-london-core", role: "Europe Core P/PE", vendor: "Juniper", class: "router", x: 420, y: 140, ip: "198.51.100.2", index: "idx_network_ops", platform: "juniper", color: "#38bdf8" },
        { id: "wan_tokyo", name: "nokia-tokyo-core", role: "Asia-Pacific Core P/PE", vendor: "Nokia", class: "optical", x: 700, y: 140, ip: "198.51.100.3", index: "idx_network_ops", platform: "nokia_opt", color: "#a855f7" },
        { id: "wan_trans", name: "subsea-lambda-transport", role: "Trans-Oceanic DWDM Link", vendor: "Generic", class: "optical", x: 420, y: 310, ip: "198.51.100.254", index: "idx_network_ops", platform: "nokia_opt", color: "#f59e0b" }
      ],
      links: [
        { from: "wan_ny", to: "wan_lon", label: "Transatlantic 400G SRv6" },
        { from: "wan_lon", to: "wan_tokyo", label: "Eurasia Terrestrial 100G" },
        { from: "wan_tokyo", to: "wan_trans", label: "Transpacific 200G DWDM" },
        { from: "wan_trans", to: "wan_ny", label: "Subsea Cable Return" }
      ]
    },
    "arch_san": {
      title: "SAN: Storage Area Network - Cisco MDS 9700 Fibre Channel & NVMe-oF",
      badge: "64G Fibre Channel",
      nodes: [
        { id: "san_srv", name: "compute-esxi-cluster", role: "VMware vSphere ESXi Host", vendor: "Generic", class: "switch_dc", x: 140, y: 200, ip: "10.80.1.10", index: "idx_performance_metrics", platform: "arista", color: "#38bdf8" },
        { id: "san_mds1", name: "mds9700-director-a", role: "Cisco MDS 9718 Director A", vendor: "Cisco", class: "switch_dc", x: 420, y: 120, ip: "10.80.0.1", index: "idx_performance_metrics", platform: "cisco_nexus", color: "#0284c7" },
        { id: "san_mds2", name: "mds9700-director-b", role: "Cisco MDS 9718 Director B", vendor: "Cisco", class: "switch_dc", x: 420, y: 280, ip: "10.80.0.2", index: "idx_performance_metrics", platform: "cisco_nexus", color: "#0284c7" },
        { id: "san_pure", name: "flasharray-x90-nvme", role: "Pure FlashArray NVMe-oF", vendor: "Generic", class: "switch_dc", x: 700, y: 200, ip: "10.80.2.50", index: "idx_performance_metrics", platform: "cisco_nexus", color: "#f97316" }
      ],
      links: [
        { from: "san_srv", to: "san_mds1", label: "64G FC HBA 1 (Fabric A)" },
        { from: "san_srv", to: "san_mds2", label: "64G FC HBA 2 (Fabric B)" },
        { from: "san_mds1", to: "san_pure", label: "NVMe-over-FC ISL" },
        { from: "san_mds2", to: "san_pure", label: "NVMe-over-FC ISL" }
      ]
    },
    "arch_nas": {
      title: "NAS: Network-Attached Storage - NetApp ONTAP & PowerScale Clusters",
      badge: "Petabyte NFS/SMB Tier",
      nodes: [
        { id: "nas_client", name: "ai-inference-workers", role: "PyTorch Training Cluster", vendor: "Generic", class: "switch_dc", x: 140, y: 200, ip: "10.70.1.10", index: "idx_performance_metrics", platform: "arista", color: "#84cc16" },
        { id: "nas_switch", name: "nexus9336-storage-sw", role: "Nexus 9336C Storage Switch", vendor: "Cisco", class: "switch_dc", x: 420, y: 200, ip: "10.70.0.1", index: "idx_network_ops", platform: "cisco_nexus", color: "#0284c7" },
        { id: "nas_netapp", name: "netapp-ontap-a900", role: "NetApp AFF A900 Cluster", vendor: "Generic", class: "switch_dc", x: 700, y: 120, ip: "10.70.2.1", index: "idx_performance_metrics", platform: "arista", color: "#38bdf8" },
        { id: "nas_isilon", name: "powerscale-f900", role: "Dell PowerScale Clustered NAS", vendor: "Generic", class: "switch_dc", x: 700, y: 280, ip: "10.70.2.2", index: "idx_performance_metrics", platform: "arista", color: "#f59e0b" }
      ],
      links: [
        { from: "nas_client", to: "nas_switch", label: "100G RDMA (NFS over RDMA)" },
        { from: "nas_switch", to: "nas_netapp", label: "100G LACP (NFSv4.1)" },
        { from: "nas_switch", to: "nas_isilon", label: "100G LACP (SMB3 Multichannel)" }
      ]
    },
    "arch_vpn": {
      title: "VPN: Virtual Private Network - Cisco AnyConnect & Site-to-Site IPsec",
      badge: "Remote Access & IPsec",
      nodes: [
        { id: "vpn_user", name: "remote-workforce-client", role: "Cisco Secure Client User", vendor: "Generic", class: "switch_campus", x: 140, y: 120, ip: "198.51.100.88", index: "idx_security_fw", platform: "cisco_ftd", color: "#f43f5e" },
        { id: "vpn_branch", name: "branch-router-ipsec", role: "Branch Office Router", vendor: "Cisco", class: "router", x: 140, y: 280, ip: "203.0.113.15", index: "idx_network_ops", platform: "cisco_ios", color: "#f97316" },
        { id: "vpn_hub", name: "asa5585-vpn-concentrator", role: "Cisco ASA / FTD Headend", vendor: "Cisco", class: "firewall", x: 440, y: 200, ip: "10.240.0.1", index: "idx_security_fw", platform: "cisco_ftd", color: "#0284c7" },
        { id: "vpn_duo", name: "duo-cloud-mfa-sso", role: "Cisco Duo Zero Trust SSO", vendor: "Cisco", class: "firewall", x: 720, y: 200, ip: "10.240.0.50", index: "idx_security_fw", platform: "cisco_ftd", color: "#10b981" }
      ],
      links: [
        { from: "vpn_user", to: "vpn_hub", label: "TLS 1.3 / DTLS Tunnel" },
        { from: "vpn_branch", to: "vpn_hub", label: "IKEv2 IPsec VTI Tunnel" },
        { from: "vpn_hub", to: "vpn_duo", label: "SAML 2.0 / Push MFA" }
      ]
    },
    "arch_epn": {
      title: "EPN: Enterprise Private Network - Isolated Corporate Intranet & QinQ",
      badge: "Multi-Tenant Intranet",
      nodes: [
        { id: "epn_hq", name: "hq-campus-core", role: "HQ Corporate Boundary", vendor: "Cisco", class: "router", x: 140, y: 120, ip: "10.150.1.1", index: "idx_network_ops", platform: "cisco_ios", color: "#0284c7" },
        { id: "epn_branch", name: "remote-factory-edge", role: "Industrial Factory Edge", vendor: "Cisco", class: "router", x: 140, y: 280, ip: "10.150.2.1", index: "idx_network_ops", platform: "cisco_ios", color: "#f97316" },
        { id: "epn_carrier", name: "carrier-carrier-8000", role: "Private Carrier Core (QinQ)", vendor: "Cisco", class: "router", x: 440, y: 200, ip: "10.254.0.1", index: "idx_network_ops", platform: "cisco_ios", color: "#8b5cf6" },
        { id: "epn_cloud", name: "aws-directconnect-gw", role: "Private Cloud VPC Interconnect", vendor: "Generic", class: "sase", x: 720, y: 200, ip: "10.150.100.1", index: "idx_security_fw", platform: "zscaler", color: "#38bdf8" }
      ],
      links: [
        { from: "epn_hq", to: "epn_carrier", label: "802.1ad QinQ S-VLAN 200" },
        { from: "epn_branch", to: "epn_carrier", label: "802.1ad QinQ S-VLAN 200" },
        { from: "epn_carrier", to: "epn_cloud", label: "DirectConnect 10G Private VIF" }
      ]
    },
    "arch_gan": {
      title: "GAN: Global Area Network - Worldwide Multi-Cloud & Subsea Cable Transit",
      badge: "Worldwide Cloud Transit",
      nodes: [
        { id: "gan_subsea", name: "subsea-landing-station", role: "Subsea Transponder Terminal", vendor: "Nokia", class: "optical", x: 140, y: 200, ip: "198.51.100.99", index: "idx_network_ops", platform: "nokia_opt", color: "#a855f7" },
        { id: "gan_sase", name: "zscaler-cloud-transit", role: "Cloud SASE Backbone", vendor: "Zscaler", class: "sase", x: 400, y: 100, ip: "165.225.0.1", index: "idx_security_fw", platform: "zscaler", color: "#0ea5e9" },
        { id: "gan_express", name: "azure-expressroute-core", role: "Azure ExpressRoute Gateway", vendor: "Generic", class: "router", x: 400, y: 300, ip: "198.51.100.150", index: "idx_network_ops", platform: "cisco_ios", color: "#38bdf8" },
        { id: "gan_aws", name: "aws-transit-gateway", role: "AWS TGW Global Mesh", vendor: "Generic", class: "router", x: 680, y: 200, ip: "198.51.100.200", index: "idx_network_ops", platform: "cisco_ios", color: "#10b981" }
      ],
      links: [
        { from: "gan_subsea", to: "gan_sase", label: "Global Lambda 400G" },
        { from: "gan_subsea", to: "gan_express", label: "Direct Fiber Cross-Connect" },
        { from: "gan_sase", to: "gan_aws", label: "Cloud WAN Peering" },
        { from: "gan_express", to: "gan_aws", label: "Multi-Cloud Interconnect" }
      ]
    },

    // Specialized Enterprise & Service Provider Architectures
    "pure_cisco_enterprise": {
      title: "Pure Cisco Enterprise Fabric (Catalyst 9600, 9500, 9300, 9800, ISE, DNA-C)",
      badge: "All-Cisco Campus Tier",
      nodes: [
        { id: "cisco_core", name: "cat9600-campus-core", role: "Catalyst 9600 Core (Quad-Sup)", vendor: "Cisco", class: "switch_campus", x: 140, y: 200, ip: "10.254.1.1", index: "idx_network_ops", platform: "cisco_cat", color: "#0284c7" },
        { id: "cisco_dist", name: "cat9500-distribution", role: "Catalyst 9500 Distribution", vendor: "Cisco", class: "switch_campus", x: 380, y: 120, ip: "10.254.2.1", index: "idx_network_ops", platform: "cisco_cat", color: "#38bdf8" },
        { id: "cisco_acc", name: "cat9300-access-sw", role: "Catalyst 9300 UPOE Access", vendor: "Cisco", class: "switch_campus", x: 620, y: 120, ip: "10.254.3.1", index: "idx_network_ops", platform: "cisco_cat", color: "#38bdf8" },
        { id: "cisco_wlc_node", name: "cat9800-wlc-ha", role: "Catalyst 9800-80 WLC HA", vendor: "Cisco", class: "wireless", x: 380, y: 280, ip: "10.254.4.1", index: "idx_wireless_ops", platform: "cisco_wlc", color: "#eab308" },
        { id: "cisco_ise_node", name: "cisco-ise-primary", role: "Cisco ISE 3.3 Node (TrustSec)", vendor: "Cisco", class: "firewall", x: 620, y: 280, ip: "10.254.5.1", index: "idx_security_fw", platform: "cisco_ftd", color: "#a855f7" }
      ],
      links: [
        { from: "cisco_core", to: "cisco_dist", label: "100G StackWise-Virtual" },
        { from: "cisco_dist", to: "cisco_acc", label: "40G L2/L3 Trunk" },
        { from: "cisco_core", to: "cisco_wlc_node", label: "CAPWAP Aggregation" },
        { from: "cisco_dist", to: "cisco_ise_node", label: "802.1X / RADIUS CoA" },
        { from: "cisco_acc", to: "cisco_ise_node", label: "TrustSec SGT Tagging" }
      ]
    },
    "sp_cisco": {
      title: "Service Provider Network - All Cisco (Cisco 8000, NCS 5500, IOS-XR SRv6)",
      badge: "Carrier SRv6 Fabric",
      nodes: [
        { id: "sp_cisco_8k", name: "cisco8808-core-p01", role: "Cisco 8808 28.8Tbps Core Router", vendor: "Cisco", class: "router", x: 140, y: 200, ip: "10.0.0.1", index: "cisco_mdt_metrics", platform: "cisco_ios", color: "#0284c7" },
        { id: "sp_cisco_ncs", name: "ncs5508-metro-pe01", role: "NCS 5508 Metro Aggregation", vendor: "Cisco", class: "router", x: 420, y: 120, ip: "10.0.0.2", index: "cisco_mdt_metrics", platform: "cisco_ios", color: "#38bdf8" },
        { id: "sp_cisco_asr", name: "asr9904-access-pe02", role: "ASR 9904 Edge Router", vendor: "Cisco", class: "router", x: 420, y: 280, ip: "10.0.0.3", index: "idx_network_ops", platform: "cisco_ios", color: "#38bdf8" },
        { id: "sp_cisco_dc", name: "nexus-edge-dc01", role: "Nexus 9500 Cloud Gateway", vendor: "Cisco", class: "switch_dc", x: 700, y: 200, ip: "10.0.0.4", index: "idx_network_ops", platform: "cisco_nexus", color: "#10b981" }
      ],
      links: [
        { from: "sp_cisco_8k", to: "sp_cisco_ncs", label: "400GE-ZR+ SRv6" },
        { from: "sp_cisco_8k", to: "sp_cisco_asr", label: "400GE-ZR+ SRv6" },
        { from: "sp_cisco_ncs", to: "sp_cisco_dc", label: "100G EVPN L3VPN" },
        { from: "sp_cisco_asr", to: "sp_cisco_dc", label: "100G EVPN L3VPN" }
      ]
    },
    "sp_mixed": {
      title: "Service Provider Network - Mixed Vendor (Cisco 8000, Juniper PTX, Nokia 7750)",
      badge: "Multi-Carrier Core",
      nodes: [
        { id: "spm_cisco", name: "cisco8201-transit-p01", role: "Cisco 8201 10.8T Router", vendor: "Cisco", class: "router", x: 140, y: 200, ip: "10.254.0.1", index: "cisco_mdt_metrics", platform: "cisco_ios", color: "#0284c7" },
        { id: "spm_juniper", name: "ptx10008-spine-p02", role: "Juniper PTX10008 Spine", vendor: "Juniper", class: "router", x: 420, y: 120, ip: "10.254.0.2", index: "idx_network_ops", platform: "juniper", color: "#38bdf8" },
        { id: "spm_nokia", name: "nokia-7750-sr14s", role: "Nokia 7750 SR-14s PE", vendor: "Nokia", class: "optical", x: 420, y: 280, ip: "10.254.0.3", index: "idx_network_ops", platform: "nokia_opt", color: "#a855f7" },
        { id: "spm_arista", name: "arista-7800r3-pe", role: "Arista 7800R3 Cloud PE", vendor: "Arista", class: "switch_dc", x: 700, y: 200, ip: "10.254.0.4", index: "idx_performance_metrics", platform: "arista", color: "#10b981" }
      ],
      links: [
        { from: "spm_cisco", to: "spm_juniper", label: "400GE BGP-LU Peer" },
        { from: "spm_cisco", to: "spm_nokia", label: "400G Coherent Optical" },
        { from: "spm_juniper", to: "spm_arista", label: "100G RSVP-TE Tunnel" },
        { from: "spm_nokia", to: "spm_arista", label: "100G SR-OS MPLS" }
      ]
    },
    "sdwan_core_cisco": {
      title: "Dedicated SD-WAN Connected to Core Backbone (All Cisco)",
      badge: "Catalyst SD-WAN Fabric",
      nodes: [
        { id: "sdw_branch1", name: "cedge-branch-8300", role: "Catalyst 8300 Branch Edge", vendor: "Cisco", class: "router", x: 140, y: 120, ip: "10.10.1.1", index: "idx_network_ops", platform: "cisco_sdwan", color: "#0284c7" },
        { id: "sdw_branch2", name: "vedge-branch-2000", role: "vEdge 2000 Retail Edge", vendor: "Cisco", class: "router", x: 140, y: 280, ip: "10.10.2.1", index: "idx_network_ops", platform: "cisco_sdwan", color: "#f97316" },
        { id: "sdw_hub", name: "cedge-hub-8500", role: "Catalyst 8500 Aggregation Hub", vendor: "Cisco", class: "router", x: 420, y: 200, ip: "10.254.10.1", index: "idx_network_ops", platform: "cisco_sdwan", color: "#0284c7" },
        { id: "sdw_core", name: "cat9600-core-backbone", role: "Catalyst 9600 Campus Core", vendor: "Cisco", class: "switch_campus", x: 700, y: 200, ip: "10.254.0.1", index: "idx_network_ops", platform: "cisco_cat", color: "#8b5cf6" }
      ],
      links: [
        { from: "sdw_branch1", to: "sdw_hub", label: "OMP / IPsec SLA Tunnel" },
        { from: "sdw_branch2", to: "sdw_hub", label: "OMP / IPsec SLA Tunnel" },
        { from: "sdw_hub", to: "sdw_core", label: "100G L3 Trunk / BGP" }
      ]
    },
    "wireless_core_cisco": {
      title: "Enterprise Wireless Connected to Campus Core (All Cisco)",
      badge: "WLAN to Core Fabric",
      nodes: [
        { id: "wcc_ap1", name: "catalyst-9130ax-01", role: "Catalyst 9130AX AP (Bldg 1)", vendor: "Cisco", class: "wireless", x: 140, y: 120, ip: "10.30.1.11", index: "idx_wireless_ops", platform: "cisco_wlc", color: "#0284c7" },
        { id: "wcc_ap2", name: "catalyst-9130ax-02", role: "Catalyst 9130AX AP (Bldg 2)", vendor: "Cisco", class: "wireless", x: 140, y: 280, ip: "10.30.1.12", index: "idx_wireless_ops", platform: "cisco_wlc", color: "#0284c7" },
        { id: "wcc_wlc", name: "cat9800-80-wlc", role: "Catalyst 9800-80 Core WLC", vendor: "Cisco", class: "wireless", x: 420, y: 200, ip: "10.30.0.1", index: "idx_wireless_ops", platform: "cisco_wlc", color: "#eab308" },
        { id: "wcc_core", name: "cat9600-core-spine", role: "Catalyst 9600 Core Switch", vendor: "Cisco", class: "switch_campus", x: 700, y: 200, ip: "10.30.0.254", index: "idx_network_ops", platform: "cisco_cat", color: "#8b5cf6" }
      ],
      links: [
        { from: "wcc_ap1", to: "wcc_wlc", label: "CAPWAP Data Tunnel" },
        { from: "wcc_ap2", to: "wcc_wlc", label: "CAPWAP Data Tunnel" },
        { from: "wcc_wlc", to: "wcc_core", label: "100G 802.1Q LACP Trunk" }
      ]
    },
    "wireless_core_mixed": {
      title: "Enterprise Wireless Connected to Core (Mixed Vendor)",
      badge: "Meraki / Arista Core",
      nodes: [
        { id: "wcm_meraki", name: "meraki-mr56-wifi6e", role: "Meraki MR56 Cloud AP", vendor: "Cisco", class: "wireless", x: 140, y: 120, ip: "10.50.1.10", index: "idx_wireless_ops", platform: "meraki_mr", color: "#10b981" },
        { id: "wcm_aruba", name: "aruba-ap635-wifi6e", role: "Aruba AP-635 Campus AP", vendor: "Aruba", class: "wireless", x: 140, y: 280, ip: "10.50.1.20", index: "idx_wireless_ops", platform: "aruba_ap", color: "#eab308" },
        { id: "wcm_pan", name: "pa-5450-fw01", role: "Palo Alto NGFW Perimeter", vendor: "Palo Alto", class: "firewall", x: 420, y: 200, ip: "10.50.0.1", index: "idx_security_fw", platform: "paloalto", color: "#f97316" },
        { id: "wcm_core", name: "arista-7280r3-core", role: "Arista 7280R3 Core Switch", vendor: "Arista", class: "switch_dc", x: 700, y: 200, ip: "10.50.0.254", index: "idx_performance_metrics", platform: "arista", color: "#10b981" }
      ],
      links: [
        { from: "wcm_meraki", to: "wcm_pan", label: "10G PoE+ Segment" },
        { from: "wcm_aruba", to: "wcm_pan", label: "10G PoE+ Segment" },
        { from: "wcm_pan", to: "wcm_core", label: "100G Trunk Inspection" }
      ]
    }
  };

  // State
  var activePresetKey = "openconfig_core";
  var currentPreset = TOPOLOGY_PRESETS[activePresetKey];
  var selectedNode = currentPreset.nodes[0];
  var activeTab = "openconfig"; // "openconfig" or "syslog"
  var continuousTimer = null;
  var pathStreamTimer = null;
  var openconfigStreamTimer = null;
  var streamStats = { totalEvents: 0 };

  function log(msg) {
    var el = document.getElementById('emit-log-console');
    if (!el) return;
    var time = new Date().toLocaleTimeString();
    el.innerHTML = '<div style="margin-bottom: 3px;">[' + time + '] ' + msg + '</div>' + el.innerHTML;
  }

  function updateLiveCounter() {
    var ctr = document.getElementById('live-total-counter');
    if (ctr) ctr.textContent = streamStats.totalEvents.toLocaleString();
  }

  // 24 Key OpenConfig YANG Models Catalog
  var KEY_OPENCONFIG_XPATHS = [
    { xpath: "/interfaces/interface/state/counters", category: "interfaces", desc: "Interface octets in/out, packets, errors, discards" },
    { xpath: "/interfaces/interface/state/oper-status", category: "interfaces", desc: "Operational & admin status (UP/DOWN), last state transition" },
    { xpath: "/interfaces/interface/state/high-speed", category: "interfaces", desc: "Line rate speed (100G/400G), duplex full, MTU 9216" },
    { xpath: "/interfaces/interface/subinterfaces/subinterface/state/counters", category: "interfaces", desc: "VLAN subinterface ingress/egress routed octets" },
    { xpath: "/interfaces/interface/ethernet/state/auto-negotiate", category: "interfaces", desc: "Ethernet auto-negotiation, carrier pulse, FEC status" },

    { xpath: "/network-instances/network-instance/protocols/protocol/bgp/neighbors/neighbor/state/session-state", category: "bgp", desc: "BGP FSM state: ESTABLISHED, IDLE, ACTIVE" },
    { xpath: "/network-instances/network-instance/protocols/protocol/bgp/neighbors/neighbor/afi-safis/afi-safi/state/prefixes/received", category: "bgp", desc: "BGP IPv4/IPv6 Unicast received prefix count" },
    { xpath: "/network-instances/network-instance/protocols/protocol/bgp/neighbors/neighbor/afi-safis/afi-safi/state/prefixes/installed", category: "bgp", desc: "BGP installed prefixes in routing table (RIB)" },
    { xpath: "/network-instances/network-instance/protocols/protocol/bgp/neighbors/neighbor/state/messages/sent", category: "bgp", desc: "BGP Keepalive & Update protocol messages sent" },
    { xpath: "/network-instances/network-instance/protocols/protocol/bgp/neighbors/neighbor/state/messages/received", category: "bgp", desc: "BGP protocol messages received & hold-timer tracking" },

    { xpath: "/components/component/cpu/state/utilization", category: "platform", desc: "Control plane & forwarding engine CPU utilization (%)" },
    { xpath: "/components/component/memory/state/utilized", category: "platform", desc: "Forwarding ASIC & system RAM allocated vs available" },
    { xpath: "/components/component/state/temperature", category: "platform", desc: "Chassis & ASIC thermal sensor readings (Celsius)" },
    { xpath: "/components/component/power-supply/state/capacity", category: "platform", desc: "PSU input/output wattage draw & redundant status" },
    { xpath: "/components/component/fan/state/speed", category: "platform", desc: "Chassis fan tray tachometer speed (RPM) & health" },

    { xpath: "/optical-transport-line/optical-channel/state/laser-bias-current", category: "optics", desc: "Transceiver laser bias current (mA)" },
    { xpath: "/optical-transport-line/optical-channel/state/output-power", category: "optics", desc: "Optical channel Tx output power (dBm)" },
    { xpath: "/optical-transport-line/optical-channel/state/input-power", category: "optics", desc: "Optical channel Rx input power (dBm) & LOS alarm" },
    { xpath: "/components/component/transceiver/state/vendor", category: "optics", desc: "QSFP28/SFP+ optical vendor, part number, serial" },

    { xpath: "/qos/interfaces/interface/output/queues/queue/state/transmit-pkts", category: "qos", desc: "Egress QoS hardware priority queue transmitted packets" },
    { xpath: "/qos/interfaces/interface/output/queues/queue/state/dropped-pkts", category: "qos", desc: "Egress QoS congestion tail-drops & WRED discards" },
    { xpath: "/qos/interfaces/interface/input/classifiers/classifier/state/matched-pkts", category: "qos", desc: "Ingress DSCP / 802.1p CoS classifier matched packets" },

    { xpath: "/system/state/current-datetime", category: "system", desc: "High-precision RFC 3339 system timestamp & uptime" },
    { xpath: "/system/ntp/state/peer-type", category: "system", desc: "NTP synchronization stratum level, offset & jitter" }
  ];

  function populateOpenConfigXPathCheckboxes() {
    var container = document.getElementById('openconfig-xpath-checkbox-list');
    if (!container) return;
    container.innerHTML = '';

    KEY_OPENCONFIG_XPATHS.forEach(function(item, idx) {
      var row = document.createElement('label');
      row.style.cssText = 'display: flex; align-items: center; justify-content: space-between; padding: 4px 6px; border-radius: 3px; font-size: 11px; cursor: pointer; transition: background 0.1s ease; border-bottom: 1px solid rgba(30, 41, 59, 0.4);';
      row.onmouseover = function() { this.style.background = '#0f172a'; };
      row.onmouseout = function() { this.style.background = 'transparent'; };

      var leftDiv = document.createElement('div');
      leftDiv.style.cssText = 'display: flex; align-items: center; gap: 8px; flex: 1; overflow: hidden;';

      var chk = document.createElement('input');
      chk.type = 'checkbox';
      chk.className = 'xpath-checkbox';
      chk.value = item.xpath;
      chk.dataset.cat = item.category;
      chk.checked = true; // All key XPaths selected by default
      chk.style.cssText = 'accent-color: #0284c7; cursor: pointer; margin: 0;';

      var pathSpan = document.createElement('span');
      pathSpan.style.cssText = 'font-family: monospace; color: #38bdf8; font-weight: 600; font-size: 11px; white-space: nowrap;';
      pathSpan.textContent = item.xpath;

      var descSpan = document.createElement('span');
      descSpan.style.cssText = 'color: #94a3b8; font-size: 10px; margin-left: 6px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;';
      descSpan.textContent = '(' + item.desc + ')';

      leftDiv.appendChild(chk);
      leftDiv.appendChild(pathSpan);
      leftDiv.appendChild(descSpan);

      var catBadge = document.createElement('span');
      catBadge.style.cssText = 'font-size: 9px; font-weight: 700; text-transform: uppercase; padding: 1px 6px; border-radius: 2px; margin-left: 8px; white-space: nowrap;';
      if (item.category === 'interfaces') { catBadge.style.background = 'rgba(56, 189, 248, 0.15)'; catBadge.style.color = '#38bdf8'; }
      else if (item.category === 'bgp') { catBadge.style.background = 'rgba(168, 85, 247, 0.15)'; catBadge.style.color = '#c084fc'; }
      else if (item.category === 'platform') { catBadge.style.background = 'rgba(34, 197, 94, 0.15)'; catBadge.style.color = '#4ade80'; }
      else if (item.category === 'optics') { catBadge.style.background = 'rgba(234, 179, 8, 0.15)'; catBadge.style.color = '#facc15'; }
      else if (item.category === 'qos') { catBadge.style.background = 'rgba(239, 68, 68, 0.15)'; catBadge.style.color = '#f87171'; }
      else { catBadge.style.background = 'rgba(148, 163, 184, 0.15)'; catBadge.style.color = '#cbd5e1'; }
      catBadge.textContent = item.category;

      row.appendChild(leftDiv);
      row.appendChild(catBadge);
      container.appendChild(row);
    });

    updateXPathSelectionCount();
  }

  function getSelectedXPaths() {
    var checked = [];
    var cbs = document.querySelectorAll('.xpath-checkbox:checked');
    cbs.forEach(function(cb) { checked.push(cb.value); });
    if (checked.length === 0) {
      checked.push("/interfaces/interface/state/counters");
    }
    return checked;
  }

  function updateXPathSelectionCount() {
    var total = KEY_OPENCONFIG_XPATHS.length;
    var count = document.querySelectorAll('.xpath-checkbox:checked').length;
    var el = document.getElementById('xpath-selected-count');
    if (el) el.textContent = count;
  }


  function generateSingleXPathMetric(xpath, host, vendor, now) {
    var inOctets = Math.floor(Math.random() * 50000000) + 950000000;
    var outOctets = Math.floor(Math.random() * 40000000) + 840000000;
    var bandwidthPct = parseFloat((Math.random() * 25 + 35).toFixed(1));
    var throughputBps = Math.floor(Math.random() * 200000000) + 750000000;
    var latencyMs = parseFloat((Math.random() * 3.5 + 1.2).toFixed(2));
    var jitterMs = parseFloat((Math.random() * 0.8 + 0.1).toFixed(2));
    var cpu = parseFloat((Math.random() * 15 + 18).toFixed(1));
    var mem = parseFloat((Math.random() * 8 + 38).toFixed(1));
    var tempC = parseFloat((Math.random() * 6 + 39).toFixed(1));

    var fields = {
      "device": host,
      "vendor": vendor,
      "xpath": xpath,
      "oper_status": "UP"
    };

    if (xpath.indexOf("/interfaces") !== -1) {
      fields["interface"] = "HundredGigE0/0/0/0";
      fields["metric_name:interface.octets.in"] = inOctets;
      fields["metric_name:interface.octets.out"] = outOctets;
      fields["metric_name:interface.packets.in"] = Math.floor(inOctets / 1024);
      fields["metric_name:interface.packets.out"] = Math.floor(outOctets / 1024);
      fields["metric_name:interface.errors.in"] = 0;
      fields["metric_name:interface.errors.out"] = 0;
      fields["metric_name:interface.discards.in"] = 0;
      fields["metric_name:interface.discards.out"] = 0;
      fields["metric_name:bandwidth.utilization_pct"] = bandwidthPct;
      fields["metric_name:throughput_bps"] = throughputBps;
    } else if (xpath.indexOf("/bgp") !== -1) {
      fields["peer_ip"] = "198.51.100.1";
      fields["peer_asn"] = 64512;
      fields["metric_name:bgp.session_up"] = 1.0;
      fields["metric_name:bgp.peer_state_code"] = 6;
      fields["metric_name:bgp.prefixes.received"] = 849200;
      fields["metric_name:bgp.prefixes.installed"] = 849180;
      fields["metric_name:bgp.messages.sent"] = 14820;
      fields["metric_name:bgp.messages.received"] = 14819;
      fields["metric_name:bgp.holdtime_seconds"] = 90;
    } else if (xpath.indexOf("/cpu") !== -1) {
      fields["component"] = "CPU-RoutingEngine-0";
      fields["metric_name:cpu.utilization"] = cpu;
      fields["metric_name:cpu.1min_avg"] = parseFloat((cpu * 0.95).toFixed(1));
      fields["metric_name:cpu.5min_avg"] = parseFloat((cpu * 0.90).toFixed(1));
    } else if (xpath.indexOf("/memory") !== -1) {
      fields["component"] = "RAM-System";
      fields["metric_name:memory.utilization_pct"] = mem;
      fields["metric_name:memory.utilized_bytes"] = Math.floor(34359738368 * (mem / 100));
      fields["metric_name:memory.total_bytes"] = 34359738368;
    } else if (xpath.indexOf("/temperature") !== -1) {
      fields["component"] = "Sensor-ASIC-Core";
      fields["metric_name:hardware.temperature_celsius"] = tempC;
      fields["metric_name:hardware.thermal_alarm"] = 0;
    } else if (xpath.indexOf("/power-supply") !== -1) {
      fields["component"] = "PSU-0";
      fields["metric_name:power.consumed_watts"] = 420.0;
      fields["metric_name:power.capacity_watts"] = 1200.0;
      fields["metric_name:power.psu_redundant"] = 1;
    } else if (xpath.indexOf("/fan") !== -1) {
      fields["component"] = "FanTray-1";
      fields["metric_name:fan.speed_rpm"] = 7200;
      fields["metric_name:fan.status_code"] = 1;
    } else if (xpath.indexOf("/optical") !== -1 || xpath.indexOf("/transceiver") !== -1) {
      fields["interface"] = "HundredGigE0/0/0/0";
      fields["optic_channel"] = "Channel-1";
      fields["metric_name:optics.laser_bias_ma"] = 48.2;
      fields["metric_name:optics.tx_power_dbm"] = -1.5;
      fields["metric_name:optics.rx_power_dbm"] = -8.4;
      fields["metric_name:optics.laser_temp_celsius"] = 38.5;
    } else if (xpath.indexOf("/qos") !== -1) {
      fields["interface"] = "HundredGigE0/0/0/0";
      fields["queue"] = "Queue-Voice-EF";
      fields["metric_name:qos.queue.tx_packets"] = 948201;
      fields["metric_name:qos.queue.dropped_packets"] = 0;
      fields["metric_name:qos.queue.wred_discards"] = 0;
    } else {
      fields["metric_name:system.uptime_seconds"] = 1849200;
      fields["metric_name:ntp.offset_ms"] = 0.42;
      fields["metric_name:ntp.jitter_ms"] = 0.12;
      fields["metric_name:ntp.stratum"] = 2;
    }

    return JSON.stringify({
      "time": now,
      "event": "metric",
      "source": "openconfig_telemetry",
      "sourcetype": "cisco:mdt:grpc",
      "host": host,
      "index": "cisco_mdt_metrics",
      "fields": fields
    });
  }

  // Generate OpenConfig MDT Telemetry Payloads Across Selected Models
  function generateOpenConfigPayload() {
    var xpaths = getSelectedXPaths();
    var host = $('#openconfig-host').val() || (selectedNode ? selectedNode.name : "rtr-cisco-8000-01.corp.internal");
    var vendor = selectedNode ? selectedNode.vendor : "Cisco";
    var format = $('input[name="openconfig_format"]:checked').val() || "metric";
    var now = parseFloat((Date.now() / 1000).toFixed(3));

    if (format === "metric") {
      var lines = [];
      xpaths.forEach(function(xp) {
        lines.push(generateSingleXPathMetric(xp, host, vendor, now));
      });
      return lines.join("\n");
    } else {
      // RFC 7951 JSON-IETF
      var yangDoc = {
        "ietf-yang-library:modules-state": {
          "module": [
            { "name": "openconfig-interfaces", "revision": "2024-01-15", "namespace": "http://openconfig.net/yang/interfaces" },
            { "name": "openconfig-bgp", "revision": "2024-02-01", "namespace": "http://openconfig.net/yang/bgp" },
            { "name": "openconfig-platform", "revision": "2024-01-10", "namespace": "http://openconfig.net/yang/platform" }
          ]
        },
        "selected_xpaths": xpaths,
        "device": host,
        "vendor": vendor,
        "openconfig-interfaces:interfaces": {
          "interface": [
            {
              "name": "HundredGigE0/0/0/0",
              "config": { "name": "HundredGigE0/0/0/0", "type": "iana-if-type:ethernetCsmacd", "enabled": true },
              "state": {
                "admin-status": "UP",
                "oper-status": "UP",
                "counters": {
                  "in-octets": Math.floor(Math.random() * 50000000) + 950000000,
                  "out-octets": Math.floor(Math.random() * 40000000) + 840000000,
                  "in-errors": 0,
                  "out-errors": 0
                }
              }
            }
          ]
        }
      };
      return JSON.stringify(yangDoc, null, 2);
    }
  }

  function updateOpenConfigPayloadBox() {
    var p = generateOpenConfigPayload();
    $('#openconfig-payload').val(p);
  }

  // Switch Tabs
  function setTab(tab) {
    activeTab = tab;
    if (tab === "openconfig") {
      $('#tab-btn-openconfig').css({ 'background': '#0284c7', 'color': '#ffffff', 'border': 'none' });
      $('#tab-btn-syslog').css({ 'background': '#1e293b', 'color': '#94a3b8', 'border': '1px solid #334155' });
      $('#panel-tab-openconfig').show();
      $('#panel-tab-syslog').hide();
      updateOpenConfigPayloadBox();
    } else {
      $('#tab-btn-openconfig').css({ 'background': '#1e293b', 'color': '#94a3b8', 'border': '1px solid #334155' });
      $('#tab-btn-syslog').css({ 'background': '#0284c7', 'color': '#ffffff', 'border': 'none' });
      $('#panel-tab-openconfig').hide();
      $('#panel-tab-syslog').show();
    }
  }

  // Change Active Preset
  function loadPreset(key) {
    if (!TOPOLOGY_PRESETS[key]) return;
    activePresetKey = key;
    currentPreset = TOPOLOGY_PRESETS[key];
    selectedNode = currentPreset.nodes[0];

    $('#canvas-scenario-title').text(currentPreset.title);
    $('#canvas-node-count-badge').text(currentPreset.badge);

    renderCanvas();
    renderDeviceGrid();
    bindSelectedNode(selectedNode);

    // Auto switch to OpenConfig for core router/switch presets
    if (key === "openconfig_core" || (selectedNode && (selectedNode.class === "router" || selectedNode.class.indexOf("switch") !== -1))) {
      setTab("openconfig");
    } else {
      setTab("syslog");
    }

    log('Loaded scenario preset: <b>' + currentPreset.title + '</b>');
  }

  // Populate Sourcetype Checkboxes for Syslog
  function populateSourcetypeCheckboxes(sourcetypes) {
    var grp = document.getElementById('sourcetype-checkbox-group');
    var selectSingle = document.getElementById('select-single-sourcetype');
    if (grp) grp.innerHTML = '';
    if (selectSingle) selectSingle.innerHTML = '';

    sourcetypes.forEach(function(st) {
      if (grp) {
        var label = document.createElement('label');
        label.style.cssText = 'display: inline-flex; align-items: center; gap: 6px; font-size: 11px; font-family: monospace; background: #1e293b; padding: 4px 10px; border-radius: 4px; border: 1px solid #334155; color: #f8fafc; cursor: pointer; user-select: none;';
        var chk = document.createElement('input');
        chk.type = 'checkbox';
        chk.value = st;
        chk.checked = true;
        chk.style.margin = '0';
        label.appendChild(chk);
        label.appendChild(document.createTextNode(st));
        grp.appendChild(label);
      }

      if (selectSingle) {
        var opt = document.createElement('option');
        opt.value = st;
        opt.textContent = st;
        selectSingle.appendChild(opt);
      }
    });
  }

  function getCheckedSourcetypes() {
    var cbs = document.querySelectorAll('#sourcetype-checkbox-group input[type="checkbox"]:checked');
    var result = [];
    cbs.forEach(function(cb) { result.push(cb.value); });
    return result;
  }

  // Bind Selected Node to Form
  function bindSelectedNode(node) {
    if (!node) return;
    selectedNode = node;

    // Update headers & badges
    $('#canvas-selected-name').text(node.name);
    $('#canvas-selected-vendor').text(node.vendor);
    $('#grid-selection-label').text('Active Node: ' + node.name);

    // OpenConfig tab bindings
    $('#openconfig-host').val(node.name + '.corp.internal');
    updateOpenConfigPayloadBox();

    // Syslog tab bindings
    $('#emit-class').val(node.class);
    updateVendorDropdown();

    var platforms = PLATFORM_MATRIX[node.class] || [];
    var matched = platforms.find(function(p) { return p.id === node.platform; }) || platforms[0];
    if (matched) {
      $('#emit-vendor').val(matched.id);
      $('#emit-index').val(matched.index);
      $('#emit-host').val(node.name + '.corp.internal');
      $('#emit-ip').val(node.ip);
      $('#emit-payload').val(matched.template);
      populateSourcetypeCheckboxes(matched.sourcetypes);
    }

    // Re-render SVG to highlight node
    highlightActiveSvgNode(node.id);
    highlightActiveGridCard(node.id);
  }

  function updateVendorDropdown() {
    var cls = $('#emit-class').val();
    var vendorSel = $('#emit-vendor');
    vendorSel.empty();
    var platforms = PLATFORM_MATRIX[cls] || [];
    platforms.forEach(function(p) {
      var opt = $('<option></option>').val(p.id).text(p.name);
      vendorSel.append(opt);
    });
  }

  function highlightActiveSvgNode(nodeId) {
    $('#canvas-svg circle.node-glow').attr('stroke', 'none').attr('stroke-width', '0');
    var glow = $('#glow-' + nodeId);
    if (glow.length) {
      glow.attr('stroke', '#38bdf8').attr('stroke-width', '4');
    }
  }

  function highlightActiveGridCard(nodeId) {
    $('.device-path-card').css({ 'border': '1px solid #1e293b', 'background': '#0f172a' });
    var activeCard = $('#grid-card-' + nodeId);
    if (activeCard.length) {
      activeCard.css({ 'border': '2px solid #0284c7', 'background': '#0c1a2e' });
    }
  }

  // Render SVG Canvas
  function renderCanvas() {
    var svg = document.getElementById('canvas-svg');
    if (!svg) return;
    svg.innerHTML = '';

    // Draw Links
    currentPreset.links.forEach(function(l) {
      var n1 = currentPreset.nodes.find(function(n) { return n.id === l.from; });
      var n2 = currentPreset.nodes.find(function(n) { return n.id === l.to; });
      if (n1 && n2) {
        var gLink = document.createElementNS('http://www.w3.org/2000/svg', 'g');

        var line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
        line.setAttribute('x1', n1.x);
        line.setAttribute('y1', n1.y);
        line.setAttribute('x2', n2.x);
        line.setAttribute('y2', n2.y);
        line.setAttribute('stroke', '#334155');
        line.setAttribute('stroke-width', '2');
        line.setAttribute('stroke-dasharray', '5,5');
        gLink.appendChild(line);

        // Link Label
        var midX = (n1.x + n2.x) / 2;
        var midY = (n1.y + n2.y) / 2 - 6;
        var txt = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        txt.setAttribute('x', midX);
        txt.setAttribute('y', midY);
        txt.setAttribute('text-anchor', 'middle');
        txt.setAttribute('fill', '#64748b');
        txt.setAttribute('font-size', '9px');
        txt.setAttribute('font-family', 'monospace');
        txt.textContent = l.label;
        gLink.appendChild(txt);

        svg.appendChild(gLink);
      }
    });

    // Draw Nodes
    currentPreset.nodes.forEach(function(n) {
      var gNode = document.createElementNS('http://www.w3.org/2000/svg', 'g');
      gNode.setAttribute('cursor', 'pointer');
      gNode.setAttribute('id', 'svg-node-' + n.id);

      // Glow / Selection Ring
      var glow = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
      glow.setAttribute('id', 'glow-' + n.id);
      glow.setAttribute('cx', n.x);
      glow.setAttribute('cy', n.y);
      glow.setAttribute('r', '26');
      glow.setAttribute('fill', 'transparent');
      glow.setAttribute('class', 'node-glow');
      glow.setAttribute('stroke', n.id === selectedNode.id ? '#38bdf8' : 'none');
      glow.setAttribute('stroke-width', n.id === selectedNode.id ? '4' : '0');
      gNode.appendChild(glow);

      // Main Circle
      var c = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
      c.setAttribute('cx', n.x);
      c.setAttribute('cy', n.y);
      c.setAttribute('r', '20');
      c.setAttribute('fill', n.color);
      c.setAttribute('stroke', '#ffffff');
      c.setAttribute('stroke-width', '2');
      gNode.appendChild(c);

      // Node Icon / Letter
      var letter = document.createElementNS('http://www.w3.org/2000/svg', 'text');
      letter.setAttribute('x', n.x);
      letter.setAttribute('y', n.y + 4);
      letter.setAttribute('text-anchor', 'middle');
      letter.setAttribute('fill', '#ffffff');
      letter.setAttribute('font-size', '11px');
      letter.setAttribute('font-weight', 'bold');
      letter.setAttribute('font-family', 'sans-serif');
      letter.textContent = n.vendor.charAt(0);
      gNode.appendChild(letter);

      // Label (Node Name)
      var nameTxt = document.createElementNS('http://www.w3.org/2000/svg', 'text');
      nameTxt.setAttribute('x', n.x);
      nameTxt.setAttribute('y', n.y + 36);
      nameTxt.setAttribute('text-anchor', 'middle');
      nameTxt.setAttribute('fill', '#f1f5f9');
      nameTxt.setAttribute('font-size', '10px');
      nameTxt.setAttribute('font-weight', 'bold');
      nameTxt.setAttribute('font-family', 'monospace');
      nameTxt.textContent = n.name;
      gNode.appendChild(nameTxt);

      // Sub-label (Role)
      var roleTxt = document.createElementNS('http://www.w3.org/2000/svg', 'text');
      roleTxt.setAttribute('x', n.x);
      roleTxt.setAttribute('y', n.y + 48);
      roleTxt.setAttribute('text-anchor', 'middle');
      roleTxt.setAttribute('fill', '#94a3b8');
      roleTxt.setAttribute('font-size', '9px');
      roleTxt.setAttribute('font-family', 'sans-serif');
      roleTxt.textContent = n.role;
      gNode.appendChild(roleTxt);

      // Click Handler
      gNode.addEventListener('click', function() {
        bindSelectedNode(n);
      });

      svg.appendChild(gNode);
    });
  }

  // Render Device Directory Grid
  function renderDeviceGrid() {
    var grid = document.getElementById('device-path-grid');
    if (!grid) return;
    grid.innerHTML = '';

    currentPreset.nodes.forEach(function(n) {
      var isSelected = (selectedNode && selectedNode.id === n.id);
      var card = document.createElement('div');
      card.className = 'device-path-card';
      card.id = 'grid-card-' + n.id;
      card.style.cssText = 'background: ' + (isSelected ? '#0c1a2e' : '#0f172a') + '; border: ' + (isSelected ? '2px solid #0284c7' : '1px solid #1e293b') + '; border-radius: 6px; padding: 12px; cursor: pointer; transition: all 0.15s ease;';

      card.innerHTML =
        '<div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 6px;">' +
          '<div>' +
            '<b style="color: #f8fafc; font-size: 12px; font-family: monospace; display: block;">' + n.name + '</b>' +
            '<span style="color: #94a3b8; font-size: 11px;">' + n.role + '</span>' +
          '</div>' +
          '<span style="background: ' + n.color + '; color: #fff; font-size: 10px; font-weight: bold; padding: 2px 6px; border-radius: 3px;">' + n.vendor + '</span>' +
        '</div>' +
        '<div style="display: flex; justify-content: space-between; align-items: center; margin-top: 8px; font-size: 11px; color: #64748b; font-family: monospace;">' +
          '<span>' + n.ip + '</span>' +
          '<span style="color: #38bdf8;">' + n.index + '</span>' +
        '</div>';

      card.addEventListener('click', function() {
        bindSelectedNode(n);
      });

      grid.appendChild(card);
    });
  }

  // Emit Ingestion Call
  function sendIngestion(sourcetype, index, content, host, ip, count) {
    var cfg = {};
    try { cfg = JSON.parse(localStorage.getItem('datablaster_config') || '{}'); } catch(e) {}
    var hecUrl = cfg.hec_url || "https://127.0.0.1:8888/services/collector";
    var token = cfg.hec_token || "00000000-0000-0000-0000-000000000000";
    var sslVerify = cfg.ssl_verify || false;

    var payload = {
      action: "onboard_sample",
      sourcetype: sourcetype,
      index: index,
      sample_content: content,
      host: host,
      ip: ip,
      count: count || 1,
      hec: hecUrl,
      token: token,
      ssl_verify: sslVerify
    };

    fetch(getRestUrl(), {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify(payload)
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
      if (data.status === 'success' || data.code === 200) {
        log('<span style="color: #4ade80;">✔ SUCCESS:</span> ' + (count || 1) + ' event(s) -> [' + index + '] sourcetype=' + sourcetype + ' host=' + host);
        streamStats.totalEvents += (count || 1);
        updateLiveCounter();
      } else {
        log('<span style="color: #f87171;">✖ HEC ERROR [' + sourcetype + ']:</span> ' + (data.message || JSON.stringify(data)));
      }
    })
    .catch(function(err) {
      log('<span style="color: #f87171;">✖ REST ERROR:</span> ' + err.message);
    });
  }

  // OpenConfig MDT Emit Handlers
  function emitOpenConfigProbe() {
    var xpaths = getSelectedXPaths();
    var payloadStr = generateOpenConfigPayload();
    var format = $('input[name="openconfig_format"]:checked').val() || "metric";
    var targetIndex = format === "metric" ? "cisco_mdt_metrics" : "idx_network_ops";
    var sourcetype = format === "metric" ? "cisco:mdt:grpc" : "openconfig:yang:json";
    var host = $('#openconfig-host').val() || (selectedNode ? selectedNode.name : "rtr-cisco-8000-01.corp.internal");

    log('Emitting OpenConfig probe (' + format + ') across <b style="color: #38bdf8;">' + xpaths.length + ' selected XPath model(s)</b> to index <b style="color: #38bdf8;">' + targetIndex + '</b>...');
    sendIngestion(sourcetype, targetIndex, payloadStr, host, selectedNode ? selectedNode.ip : "10.254.0.1", xpaths.length);
  }

  function startOpenConfigStream() {
    if (openconfigStreamTimer) return;
    $('#btn-stream-openconfig').hide();
    $('#btn-stop-openconfig-stream').show();

    log('<span style="color: #4ade80; font-weight: bold;">OPENCONFIG MDT ACTIVE:</span> Continuous gNMI telemetry streaming (10 msg/sec) to cisco_mdt_metrics...');

    openconfigStreamTimer = setInterval(function() {
      var payloadStr = generateOpenConfigPayload();
      var host = $('#openconfig-host').val() || "rtr-cisco-8000-01.corp.internal";
      sendIngestion("cisco:mdt:grpc", "cisco_mdt_metrics", payloadStr, host, selectedNode ? selectedNode.ip : "10.254.0.1", 1);
    }, 100);
  }

  function stopOpenConfigStream() {
    if (openconfigStreamTimer) clearInterval(openconfigStreamTimer);
    openconfigStreamTimer = null;
    $('#btn-stream-openconfig').show();
    $('#btn-stop-openconfig-stream').hide();
    log('<span style="color: #f59e0b; font-weight: bold;">OPENCONFIG MDT STOPPED:</span> MDT telemetry stream halted.');
  }

  // Syslog Emit Handlers
  function emitSyslogCount(count) {
    var sts = getCheckedSourcetypes();
    if (sts.length === 0) {
      log('<span style="color: #f87171;">WARNING:</span> No sourcetypes selected.');
      return;
    }
    var idx = $('#emit-index').val() || 'idx_network_ops';
    var host = $('#emit-host').val() || 'network-device.corp.internal';
    var ip = $('#emit-ip').val() || '10.254.1.1';
    var content = $('#emit-payload').val();

    sts.forEach(function(st) {
      sendIngestion(st, idx, content, host, ip, count);
    });
  }

  function emitSyslogSingle(count) {
    var st = $('#select-single-sourcetype').val() || "cisco:ios";
    var idx = $('#emit-index').val() || 'idx_network_ops';
    var host = $('#emit-host').val() || 'network-device.corp.internal';
    var ip = $('#emit-ip').val() || '10.254.1.1';
    var content = $('#emit-payload').val();
    sendIngestion(st, idx, content, host, ip, count);
  }

  // Continuous Streamer (Syslog / Selected Mode)
  function startContinuousStream() {
    if (continuousTimer) return;
    var rate = parseInt($('#continuous-rate-select').val() || "50", 10);
    var intervalMs = Math.round(1000 / Math.min(rate, 20));
    var burstPerTick = Math.max(1, Math.round(rate / 20));

    $('#btn-start-continuous').hide();
    $('#btn-stop-continuous').show();
    $('#continuous-status-badge').text('STREAMING ACTIVE (' + rate + ' EPS)').css({ 'background': '#15803d', 'color': '#ffffff' });

    log('<span style="color: #4ade80; font-weight: bold;">CONTINUOUS STREAM STARTED:</span> Target rate ' + rate + ' EPS...');

    continuousTimer = setInterval(function() {
      var mode = $('input[name="sourcetype_mode"]:checked').val();
      if (mode === "single") {
        emitSyslogSingle(burstPerTick);
      } else {
        emitSyslogCount(burstPerTick);
      }
    }, intervalMs);
  }

  function stopContinuousStream() {
    if (continuousTimer) clearInterval(continuousTimer);
    continuousTimer = null;
    $('#btn-start-continuous').show();
    $('#btn-stop-continuous').hide();
    $('#continuous-status-badge').text('STREAM IDLE').css({ 'background': '#334155', 'color': '#94a3b8' });
    log('<span style="color: #f59e0b; font-weight: bold;">CONTINUOUS STREAM STOPPED.</span>');
  }

  // Sequential Path Flow Traversal Stream
  function startPathStream() {
    if (pathStreamTimer) return;
    $('#btn-stream-path').hide();
    $('#btn-stop-path').show();
    log('<span style="color: #0284c7; font-weight: bold;">PATH FLOW ACTIVE:</span> Traversing ' + currentPreset.nodes.length + ' architecture devices in sequence...');

    var idx = 0;
    pathStreamTimer = setInterval(function() {
      var n = currentPreset.nodes[idx % currentPreset.nodes.length];
      bindSelectedNode(n);
      if (activeTab === "openconfig") {
        emitOpenConfigProbe();
      } else {
        emitSyslogSingle(1);
      }
      idx++;
    }, 1500);
  }

  function stopPathStream() {
    if (pathStreamTimer) clearInterval(pathStreamTimer);
    pathStreamTimer = null;
    $('#btn-stream-path').show();
    $('#btn-stop-path').hide();
    log('<span style="color: #f59e0b; font-weight: bold;">PATH FLOW STOPPED.</span>');
  }

  // DOM Event Bindings
  function bindEvents() {
    // Preset Dropdown
    $('#select-topology-preset').on('change', function() {
      loadPreset($(this).val());
    });

    // Tab Buttons
    $('#tab-btn-openconfig').on('click', function() { setTab('openconfig'); });
    $('#tab-btn-syslog').on('click', function() { setTab('syslog'); });

    // OpenConfig controls & XPath multi-select handlers
    $(document).on('change', '.xpath-checkbox', function() {
      updateXPathSelectionCount();
      updateOpenConfigPayloadBox();
    });

    $(document).on('click', '#btn-xpath-select-all', function() {
      $('.xpath-checkbox').prop('checked', true);
      updateXPathSelectionCount();
      updateOpenConfigPayloadBox();
    });

    $(document).on('click', '#btn-xpath-clear-all', function() {
      $('.xpath-checkbox').prop('checked', false);
      // Keep primary interface counters active
      $('.xpath-checkbox[value="/interfaces/interface/state/counters"]').prop('checked', true);
      updateXPathSelectionCount();
      updateOpenConfigPayloadBox();
    });

    $(document).on('click', '.btn-xpath-cat', function() {
      var cat = $(this).data('cat');
      var cbs = $('.xpath-checkbox[data-cat="' + cat + '"]');
      var anyUnchecked = false;
      cbs.each(function() { if (!this.checked) anyUnchecked = true; });
      cbs.prop('checked', anyUnchecked);
      updateXPathSelectionCount();
      updateOpenConfigPayloadBox();
    });

    $('#select-openconfig-xpath').on('change', updateOpenConfigPayloadBox);
    $('input[name="openconfig_format"]').on('change', updateOpenConfigPayloadBox);
    $('#btn-refresh-openconfig-payload').on('click', updateOpenConfigPayloadBox);
    $('#btn-emit-openconfig-probe').on('click', emitOpenConfigProbe);
    $('#btn-stream-openconfig').on('click', startOpenConfigStream);
    $('#btn-stop-openconfig-stream').on('click', stopOpenConfigStream);

    // Syslog controls
    $('#emit-class').on('change', function() {
      updateVendorDropdown();
      var cls = $(this).val();
      var platforms = PLATFORM_MATRIX[cls] || [];
      if (platforms.length) {
        $('#emit-vendor').val(platforms[0].id);
        $('#emit-index').val(platforms[0].index);
        $('#emit-payload').val(platforms[0].template);
        populateSourcetypeCheckboxes(platforms[0].sourcetypes);
      }
    });

    $('#emit-vendor').on('change', function() {
      var cls = $('#emit-class').val();
      var vId = $(this).val();
      var platforms = PLATFORM_MATRIX[cls] || [];
      var matched = platforms.find(function(p) { return p.id === vId; });
      if (matched) {
        $('#emit-index').val(matched.index);
        $('#emit-payload').val(matched.template);
        populateSourcetypeCheckboxes(matched.sourcetypes);
      }
    });

    $('#btn-reset-template').on('click', function() {
      var cls = $('#emit-class').val();
      var vId = $('#emit-vendor').val();
      var platforms = PLATFORM_MATRIX[cls] || [];
      var matched = platforms.find(function(p) { return p.id === vId; });
      if (matched) $('#emit-payload').val(matched.template);
    });

    $('#btn-select-all-st').on('click', function() {
      var cbs = $('#sourcetype-checkbox-group input[type="checkbox"]');
      var anyUnchecked = false;
      cbs.each(function() { if (!this.checked) anyUnchecked = true; });
      cbs.prop('checked', anyUnchecked);
    });

    $('input[name="sourcetype_mode"]').on('change', function() {
      var mode = $(this).val();
      $('#container-single-sourcetype').toggle(mode === 'single');
    });

    // Emission buttons
    $('#btn-emit-single-st').on('click', function() { emitSyslogSingle(1); });
    $('#btn-emit-selected').on('click', function() { emitSyslogCount(1); });
    $('#btn-burst-50').on('click', function() { emitSyslogCount(50); });
    $('#btn-burst-100').on('click', function() { emitSyslogCount(100); });
    $('#btn-blast-selected-1').on('click', function() {
      if (activeTab === "openconfig") emitOpenConfigProbe();
      else emitSyslogSingle(1);
    });
    $('#btn-blast-selected-50').on('click', function() {
      if (activeTab === "openconfig") {
        for (var i = 0; i < 5; i++) emitOpenConfigProbe();
      } else {
        emitSyslogCount(50);
      }
    });

    // Streaming buttons
    $('#btn-start-continuous').on('click', startContinuousStream);
    $('#btn-stop-continuous').on('click', stopContinuousStream);
    $('#btn-stream-path').on('click', startPathStream);
    $('#btn-stop-path').on('click', stopPathStream);

    // Visual Canvas Navigation & Drawer Handlers
    $(document).on('click', '#btn-open-visual-canvas', function(e) {
      e.preventDefault();
      var localeMatch = window.location.pathname.match(/^\/([a-zA-Z]{2}-[a-zA-Z]{2})\//);
      var locale = localeMatch ? localeMatch[1] : 'en-US';
      window.open('/' + locale + '/app/netspout/netspout_canvas', '_blank');
    });

    $(document).on('click', '#btn-toggle-inline-canvas', function() {
      var localeMatch = window.location.pathname.match(/^\/([a-zA-Z]{2}-[a-zA-Z]{2})\//);
      var locale = localeMatch ? localeMatch[1] : 'en-US';
      var frame = document.getElementById('inline-canvas-frame');
      if (frame && (!frame.src || frame.src.indexOf('index.html') === -1 || frame.src.indexOf('netspout_canvas') !== -1)) {
        frame.src = '/' + locale + '/static/app/netspout/dist/index.html';
      }
      $('#inline-canvas-drawer').slideToggle(200);
    });
    $(document).on('click', '#btn-close-inline-canvas', function() {
      $('#inline-canvas-drawer').slideUp(200);
    });
  }

  // Initialization
  function init() {
    bindEvents();
    populateOpenConfigXPathCheckboxes();
    loadPreset("openconfig_core");
    log('Scenario Builder & Path Flow Canvas initialized with 24 OpenConfig MDT Streaming models.');
  }

  function pollReady() {
    if (document.getElementById('canvas-svg') && document.getElementById('select-topology-preset')) {
      init();
    } else {
      setTimeout(pollReady, 100);
    }
  }

  pollReady();
});
