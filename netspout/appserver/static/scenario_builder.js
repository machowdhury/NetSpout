/*
 * Splunk App: TA-network-data-blaster
 * View Script: scenario_builder.js
 * Clean enterprise network engineering interface
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

  // Device Class & Platform Matrix
  var PLATFORM_MATRIX = {
    "firewall": [
      { id: "paloalto", name: "Palo Alto Networks (PAN-OS)", index: "idx_security_fw", sourcetypes: ["pan:traffic", "pan:threat", "pan:system"], template: '1,2026/09/19 14:00:00,001801000001,TRAFFIC,drop,1,2026/09/19 14:00:00,198.51.100.42,10.254.1.10,0.0.0.0,0.0.0.0,rule_syn_flood,vsys1,untrust,trust,ethernet1/1,ethernet1/2,default-log-forwarding,2026/09/19 14:00:00,0,1,54210,443,0,0,0x0,tcp,deny,64,64,0,1,2026/09/19 14:00:00,0,any,0,12345678,0x0,United States,10.0.0.0-10.255.255.255,0,1,0,threat-drop,0,0,0,0,,pa-5450-fw01,from-policy' },
      { id: "fortinet", name: "Fortinet FortiGate (FortiOS)", index: "idx_security_fw", sourcetypes: ["fortinet:fortigate", "fortigate_traffic", "fortigate_event"], template: 'date=2026-09-19 time=14:00:00 devname="fortigate-3700d" devid="FG370D4615800001" eventtime=1789840800 level="warning" vd="root" type="traffic" subtype="forward" action="accept" policyid=12 sessionid=9872411 srcip=10.254.2.50 dstip=198.51.100.80 proto=6 sentbyte=2400 rcvdbyte=8900 utmaction="allow" transport="sdwan" sla="violated" msg="dynamic path failover to biz-internet"' },
      { id: "checkpoint", name: "Check Point Quantum (Gaia)", index: "idx_security_fw", sourcetypes: ["checkpoint:cef"], template: 'CEF:0|Check Point|VPN-1 & FireWall-1|Check Point|Log|drop|act=drop suser=mchen src=10.40.12.88 spt=54215 dst=198.51.100.66 dpt=23 proto=tcp product=VPN-1 & FireWall-1 cs1Label=Rule cs1=Deny_Telnet_Global' },
      { id: "cisco_ftd", name: "Cisco Secure Firewall (FTD / ASA)", index: "idx_security_fw", sourcetypes: ["cisco:ftd:syslog", "cisco:asa:syslog", "cisco:asa"], template: '%FTD-1-430002: EventPriority: Low, DeviceUUID: 4f1a23-8991, SnortId: 1:31456, Event: MALWARE-CNC Win.Trojan.CobaltStrike beacon detected, SrcIP: 10.40.12.88, DstIP: 198.51.100.99, Action: Dropped' }
    ],
    "router": [
      { id: "cisco_ios", name: "Cisco IOS-XE (Catalyst 8000 / ASR)", index: "idx_network_ops", sourcetypes: ["cisco:ios", "cisco:ios:syslog", "cisco:ios:mdt", "cisco:metrics"], template: '<189>Sep 19 14:00:00 edge-core-01 %LINEPROTO-5-UPDOWN: Line protocol on Interface GigabitEthernet1/0/24, changed state to down' },
      { id: "cisco_sdwan", name: "Cisco SD-WAN (Viptela OS)", index: "idx_network_ops", sourcetypes: ["cisco:sdwan:syslog", "cisco:sdwan:linkhealth", "cisco:sdwan:sitehealth", "cisco:sdwan:tunnelhealth", "cisco:sdwan:BGP-5-ADJCHANGE"], template: '{"edge_device": "sdwan-toronto-edge01", "tunnel": "biz-internet", "latency_ms": 14.2, "jitter_ms": 1.1, "loss_percentage": 0.02, "sla_status": "in_sla"}' },
      { id: "juniper", name: "Juniper Networks (Junos MX)", index: "idx_network_ops", sourcetypes: ["juniper:junos", "juniper:syslog"], template: '<14>Sep 19 14:00:00 core-juniper-mx960 rpd[4821]: %ROUTING-4-BGP_PEER_FLAP: BGP peer 198.51.100.1 (External AS 65001) state changed from Established to Idle (HoldTimer expired)' },
      { id: "nokia", name: "Nokia Service Router (SR OS 7750)", index: "idx_network_ops", sourcetypes: ["nokia:sros", "nokia:sros:syslog"], template: '<165>Sep 19 14:00:00 pe01-toronto-7750 Major: BGP #2002 Base Peer 10.254.0.1: Peer entered Established state; Session uptime 4d 12h.' }
    ],
    "switch_dc": [
      { id: "arista", name: "Arista Networks (EOS / RoCE v2)", index: "idx_performance_metrics", sourcetypes: ["arista:eos", "arista:eos:syslog", "arista:telemetry:json"], template: '{"timestamp": 1789840800.0, "device": "dc-spine-arista7060", "interface": "Ethernet1/1", "pfc_pause_rx": 48201, "ecn_marked_packets": 1284, "buffer_utilization_pct": 98.4, "status": "CONGESTION_ROCE_V2"}' },
      { id: "cisco_nexus", name: "Cisco Nexus NX-OS & ACI Fabric", index: "idx_network_ops", sourcetypes: ["cisco:nexus", "cisco:nxos", "cisco:nxos:syslog", "cisco:dc:nexus9k", "cisco:dc:aci:health"], template: '<187>Sep 19 14:00:00 dc-spine-nexus %ETHPORT-5-IF_DOWN_LINK_FAILURE: Interface Ethernet1/1 is down (Link failure)' }
    ],
    "switch_campus": [
      { id: "cisco_cat", name: "Cisco Catalyst 9300/9500 Fabric", index: "idx_network_ops", sourcetypes: ["cisco:catalyst:networkhealth", "cisco:catalyst:devicehealth", "cisco:catalyst:compliance", "cisco:catalyst:issue"], template: '{"deviceName": "cat9k-core.campus.acme.net", "healthScore": 99, "cpuScore": 100, "memoryScore": 98, "packetScore": 100, "linkHealth": 99}' },
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
    ]
  };

  // 10 Topology Path Nodes
  var PATH_NODES = [
    { id: "sase", name: "zscaler-edge-ingress", role: "Cloud SASE Gateway", vendor: "Zscaler", class: "sase", x: 80, y: 70, ip: "165.225.1.1", index: "idx_security_fw", platform: "zscaler", color: "#0ea5e9" },
    { id: "fw", name: "pa-5450-perimeter", role: "Perimeter Next-Gen FW", vendor: "Palo Alto", class: "firewall", x: 230, y: 150, ip: "10.254.1.1", index: "idx_security_fw", platform: "paloalto", color: "#f97316" },
    { id: "sdwan", name: "fortigate-3700d-sdwan", role: "SD-WAN Edge Hub", vendor: "Fortinet", class: "firewall", x: 380, y: 80, ip: "10.254.2.1", index: "idx_security_fw", platform: "fortinet", color: "#22c55e" },
    { id: "core", name: "core-juniper-mx960", role: "Core MPLS/BGP Router", vendor: "Juniper", class: "router", x: 540, y: 220, ip: "10.254.3.1", index: "idx_network_ops", platform: "juniper", color: "#3b82f6" },
    { id: "nokia", name: "core-nokia-7750", role: "100G Coherent Optical", vendor: "Nokia", class: "optical", x: 700, y: 120, ip: "10.254.4.1", index: "idx_network_ops", platform: "nokia_opt", color: "#a855f7" },
    { id: "spine", name: "dc-spine-arista7060", role: "AI DC Spine Switch", vendor: "Arista", class: "switch_dc", x: 860, y: 240, ip: "10.254.5.1", index: "idx_performance_metrics", platform: "arista", color: "#10b981" },
    { id: "gpu", name: "nvidia-quantum-h100", role: "AI GPU Fabric Cluster", vendor: "NVIDIA", class: "switch_dc", x: 1020, y: 350, ip: "10.254.6.1", index: "idx_performance_metrics", platform: "arista", color: "#84cc16" },
    { id: "f5", name: "bigip-ltm-cluster", role: "App Load Balancer", vendor: "F5", class: "loadbalancer", x: 860, y: 390, ip: "10.254.7.1", index: "idx_network_ops", platform: "f5", color: "#ef4444" },
    { id: "campus", name: "campus-cat9k-access", role: "Campus Access Switch", vendor: "Cisco", class: "switch_campus", x: 380, y: 330, ip: "10.254.8.1", index: "idx_network_ops", platform: "cisco_cat", color: "#38bdf8" },
    { id: "wifi", name: "aruba-ap635-campus", role: "Campus WiFi 6E AP", vendor: "Aruba", class: "wireless", x: 230, y: 390, ip: "10.254.9.1", index: "idx_wireless_ops", platform: "aruba_ap", color: "#eab308" }
  ];

  var PATH_LINKS = [
    { from: "sase", to: "fw", label: "GRE / IPsec" },
    { from: "fw", to: "sdwan", label: "100G Trunk" },
    { from: "sdwan", to: "core", label: "BGP AS 65001" },
    { from: "core", to: "nokia", label: "100G DWDM" },
    { from: "nokia", to: "spine", label: "400G SR-OS" },
    { from: "spine", to: "gpu", label: "RoCE v2 PFC" },
    { from: "spine", to: "f5", label: "LACP 100G" },
    { from: "sdwan", to: "campus", label: "802.1Q Core" },
    { from: "campus", to: "wifi", label: "PoE+ 10GE" }
  ];

  var selectedNode = PATH_NODES[1];
  var continuousTimer = null;
  var pathStreamTimer = null;
  var streamStats = { totalEvents: 0, startTime: 0 };

  function log(msg) {
    var el = document.getElementById('emit-log-console');
    if (!el) return;
    var time = new Date().toLocaleTimeString();
    el.innerHTML = '<div style="margin-bottom: 2px;">[' + time + '] ' + msg + '</div>' + el.innerHTML;
  }

  function getCheckedSourcetypes() {
    var cbs = document.querySelectorAll('#sourcetype-checkbox-group input[type="checkbox"]:checked');
    var result = [];
    cbs.forEach(function(cb) { result.push(cb.value); });
    return result;
  }

  function populateSourcetypeCheckboxes(sourcetypes) {
    var grp = document.getElementById('sourcetype-checkbox-group');
    var selectSingle = document.getElementById('select-single-sourcetype');
    if (grp) grp.innerHTML = '';
    if (selectSingle) selectSingle.innerHTML = '';

    sourcetypes.forEach(function(st, idx) {
      // Checkbox pill
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

      // Single select dropdown option
      if (selectSingle) {
        var opt = document.createElement('option');
        opt.value = st;
        opt.textContent = st;
        selectSingle.appendChild(opt);
      }
    });
  }

  window.datablasterToggleAllSourcetypes = function() {
    var cbs = document.querySelectorAll('#sourcetype-checkbox-group input[type="checkbox"]');
    var anyUnchecked = false;
    cbs.forEach(function(cb) { if (!cb.checked) anyUnchecked = true; });
    cbs.forEach(function(cb) { cb.checked = anyUnchecked; });
  };

  window.datablasterOnClassChange = function() {
    var clsEl = document.getElementById('emit-class');
    if (!clsEl) return;
    var cls = clsEl.value;
    var vendorSel = document.getElementById('emit-vendor');
    if (!vendorSel) return;
    vendorSel.innerHTML = '';
    var platforms = PLATFORM_MATRIX[cls] || [];
    platforms.forEach(function(p) {
      var opt = document.createElement('option');
      opt.value = p.id;
      opt.textContent = p.name;
      vendorSel.appendChild(opt);
    });
    window.datablasterOnVendorChange();
  };

  window.datablasterOnVendorChange = function() {
    var clsEl = document.getElementById('emit-class');
    var vEl = document.getElementById('emit-vendor');
    if (!clsEl || !vEl) return;
    var cls = clsEl.value;
    var vId = vEl.value;
    var platforms = PLATFORM_MATRIX[cls] || [];
    var matched = platforms.find(function(p) { return p.id === vId; }) || platforms[0];
    if (matched) {
      if (document.getElementById('emit-index')) document.getElementById('emit-index').value = matched.index;
      if (document.getElementById('emit-payload')) document.getElementById('emit-payload').value = matched.template;
      populateSourcetypeCheckboxes(matched.sourcetypes);
      log('Active platform: ' + matched.name + ' (' + matched.sourcetypes.length + ' sourcetypes, index: ' + matched.index + ')');
    }
  };

  window.datablasterReloadTemplate = function() {
    var clsEl = document.getElementById('emit-class');
    var vEl = document.getElementById('emit-vendor');
    if (!clsEl || !vEl) return;
    var platforms = PLATFORM_MATRIX[clsEl.value] || [];
    var matched = platforms.find(function(p) { return p.id === vEl.value; });
    if (matched) {
      document.getElementById('emit-payload').value = matched.template;
      log('Reset payload template for ' + matched.name);
    }
  };

  // Render SVG Canvas
  function renderCanvas() {
    var svg = document.getElementById('canvas-svg');
    if (!svg) return;
    svg.innerHTML = '';

    // Draw Links
    PATH_LINKS.forEach(function(l) {
      var n1 = PATH_NODES.find(function(n) { return n.id === l.from; });
      var n2 = PATH_NODES.find(function(n) { return n.id === l.to; });
      if (n1 && n2) {
        var gLink = document.createElementNS('http://www.w3.org/2000/svg', 'g');

        var line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
        line.setAttribute('x1', n1.x);
        line.setAttribute('y1', n1.y);
        line.setAttribute('x2', n2.x);
        line.setAttribute('y2', n2.y);
        line.setAttribute('stroke', '#334155');
        line.setAttribute('stroke-width', '2');
        line.setAttribute('stroke-dasharray', '4,4');
        gLink.appendChild(line);

        // Link Label
        var midX = (n1.x + n2.x) / 2;
        var midY = (n1.y + n2.y) / 2 - 6;
        var txt = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        txt.setAttribute('x', midX);
        txt.setAttribute('y', midY);
        txt.setAttribute('text-anchor', 'middle');
        txt.setAttribute('fill', '#64748b');
        txt.setAttribute('font-size', '8px');
        txt.setAttribute('font-family', 'monospace');
        txt.textContent = l.label;
        gLink.appendChild(txt);

        // Animated Packet Particle
        var circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
        circle.setAttribute('r', '3.5');
        circle.setAttribute('fill', '#38bdf8');
        var anim = document.createElementNS('http://www.w3.org/2000/svg', 'animateMotion');
        anim.setAttribute('path', 'M ' + n1.x + ' ' + n1.y + ' L ' + n2.x + ' ' + n2.y);
        anim.setAttribute('dur', '2.5s');
        anim.setAttribute('repeatCount', 'indefinite');
        circle.appendChild(anim);
        gLink.appendChild(circle);

        svg.appendChild(gLink);
      }
    });

    // Draw Nodes
    PATH_NODES.forEach(function(n) {
      var g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
      g.style.cursor = 'pointer';
      g.onclick = function() { window.datablasterSelectNode(n); };

      var isSel = (selectedNode && selectedNode.id === n.id);

      // Node Body
      var rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
      rect.setAttribute('x', n.x - 55);
      rect.setAttribute('y', n.y - 25);
      rect.setAttribute('width', '110');
      rect.setAttribute('height', '50');
      rect.setAttribute('rx', '4');
      rect.setAttribute('fill', isSel ? '#1e293b' : '#0f172a');
      rect.setAttribute('stroke', isSel ? '#38bdf8' : '#334155');
      rect.setAttribute('stroke-width', isSel ? '2.5' : '1');
      g.appendChild(rect);

      // Status indicator bar
      var bar = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
      bar.setAttribute('x', n.x - 55);
      bar.setAttribute('y', n.y - 25);
      bar.setAttribute('width', '4');
      bar.setAttribute('height', '50');
      bar.setAttribute('rx', '2');
      bar.setAttribute('fill', n.color);
      g.appendChild(bar);

      // Hostname Title
      var title = document.createElementNS('http://www.w3.org/2000/svg', 'text');
      title.setAttribute('x', n.x - 45);
      title.setAttribute('y', n.y - 8);
      title.setAttribute('fill', isSel ? '#38bdf8' : '#f8fafc');
      title.setAttribute('font-size', '10px');
      title.setAttribute('font-family', 'monospace');
      title.setAttribute('font-weight', 'bold');
      title.textContent = n.name.length > 14 ? n.name.slice(0, 13) + '..' : n.name;
      g.appendChild(title);

      // Role / Vendor
      var roleText = document.createElementNS('http://www.w3.org/2000/svg', 'text');
      roleText.setAttribute('x', n.x - 45);
      roleText.setAttribute('y', n.y + 6);
      roleText.setAttribute('fill', '#94a3b8');
      roleText.setAttribute('font-size', '8px');
      roleText.textContent = n.role;
      g.appendChild(roleText);

      // IP Subtitle
      var sub = document.createElementNS('http://www.w3.org/2000/svg', 'text');
      sub.setAttribute('x', n.x - 45);
      sub.setAttribute('y', n.y + 18);
      sub.setAttribute('fill', n.color);
      sub.setAttribute('font-size', '8px');
      sub.setAttribute('font-family', 'monospace');
      sub.textContent = n.vendor + ' - ' + n.ip;
      g.appendChild(sub);

      svg.appendChild(g);
    });
  }

  // Render Device Grid
  function renderDeviceGrid() {
    var grid = document.getElementById('device-path-grid');
    if (!grid) return;
    grid.innerHTML = '';
    PATH_NODES.forEach(function(n, idx) {
      var isSel = (selectedNode && selectedNode.id === n.id);
      var card = document.createElement('div');
      card.style.cssText = 'background: ' + (isSel ? '#1e293b' : '#0f172a') + '; border: 1px solid ' + (isSel ? '#38bdf8' : '#1e293b') + '; border-radius: 6px; padding: 12px; cursor: pointer; transition: border-color 0.15s;';
      card.onclick = function() { window.datablasterSelectNode(n); };

      var html = '<div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 6px;">';
      html += '<div><div style="color: ' + (isSel ? '#38bdf8' : '#f8fafc') + '; font-size: 12px; font-weight: 600; font-family: monospace;">' + n.name + '</div>';
      html += '<div style="color: #94a3b8; font-size: 11px;">' + n.role + '</div></div>';
      html += '<span style="font-size: 10px; background: #334155; color: #cbd5e1; padding: 2px 6px; border-radius: 3px; font-family: monospace;">' + n.class + '</span>';
      html += '</div>';

      html += '<div style="display: flex; justify-content: space-between; align-items: center; margin-top: 10px; border-top: 1px solid #1e293b; padding-top: 8px;">';
      html += '<div style="font-size: 11px; font-family: monospace; color: ' + n.color + ';">' + n.vendor + ' (' + n.ip + ')</div>';
      html += '<button type="button" class="btn-grid-blast" data-index="' + idx + '" style="background: #0284c7; border: none; color: #fff; border-radius: 3px; padding: 4px 10px; font-size: 11px; font-weight: 600; cursor: pointer;">Select &amp; Emit</button>';
      html += '</div>';

      card.innerHTML = html;
      grid.appendChild(card);
    });

    // Delegate grid blast buttons
    $('.btn-grid-blast').off('click').on('click', function(e) {
      e.stopPropagation();
      var nodeIndex = parseInt($(this).data('index'), 10);
      if (!isNaN(nodeIndex) && PATH_NODES[nodeIndex]) {
        window.datablasterSelectNode(PATH_NODES[nodeIndex]);
        window.datablasterEmitSingleSourcetype(1);
      }
    });
  }

  window.datablasterSelectNode = function(n) {
    selectedNode = n;
    if (document.getElementById('canvas-selected-name')) document.getElementById('canvas-selected-name').textContent = n.name;
    if (document.getElementById('canvas-selected-vendor')) document.getElementById('canvas-selected-vendor').textContent = n.vendor;
    var lbl = document.getElementById('grid-selection-label');
    if (lbl) lbl.textContent = 'Active Node: ' + n.name + ' (' + n.vendor + ' - ' + n.ip + ')';

    if (document.getElementById('emit-host')) document.getElementById('emit-host').value = n.name;
    if (document.getElementById('emit-ip')) document.getElementById('emit-ip').value = n.ip;
    if (document.getElementById('emit-index')) document.getElementById('emit-index').value = n.index;

    // Synchronize Class and Platform dropdowns
    if (document.getElementById('emit-class')) {
      document.getElementById('emit-class').value = n.class;
      window.datablasterOnClassChange();
      if (n.platform && document.getElementById('emit-vendor')) {
        document.getElementById('emit-vendor').value = n.platform;
        window.datablasterOnVendorChange();
      }
    }

    renderCanvas();
    renderDeviceGrid();
  };

  // Emit Single Sourcetype
  window.datablasterEmitSingleSourcetype = function(count) {
    var mode = document.querySelector('input[name="sourcetype_mode"]:checked');
    var singleSt = "";
    if (mode && mode.value === "single") {
      var selEl = document.getElementById('select-single-sourcetype');
      singleSt = selEl ? selEl.value : "";
    }
    if (!singleSt) {
      var checked = getCheckedSourcetypes();
      singleSt = checked.length > 0 ? checked[0] : "";
    }

    if (!singleSt) {
      alert('Please select a sourcetype to emit.');
      return;
    }

    var cfg = {};
    try { cfg = JSON.parse(localStorage.getItem('datablaster_config') || '{}'); } catch(e) {}
    var hecUrl = cfg.hec_url || "https://127.0.0.1:8888/services/collector";
    var token = cfg.hec_token || "00000000-0000-0000-0000-000000000000";

    var host = (document.getElementById('emit-host') || {}).value || "device01";
    var ip = (document.getElementById('emit-ip') || {}).value || "10.0.0.1";
    var idx = (document.getElementById('emit-index') || {}).value || "idx_network_ops";
    var vendor = (document.getElementById('emit-vendor') || {}).value || "Cisco";
    var payloadTpl = (document.getElementById('emit-payload') || {}).value || "TEST_EVENT";

    log('Emitting ' + (count || 1) + ' event(s) -> [' + idx + '] sourcetype=' + singleSt + ' to Splunk HEC...');

    var payload = {
      action: "blast_single_device",
      hec: hecUrl,
      token: token,
      count: count || 1,
      device_info: {
        name: host,
        host: host,
        ip: ip,
        index: idx,
        sourcetype: singleSt,
        vendor: vendor,
        sampleEvent: payloadTpl
      }
    };

    fetch(getRestUrl(), {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify(payload)
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
      if (data.status === 'success' || data.code === 200) {
        log('<span style="color: #22c55e; font-weight: bold;">SUCCESS:</span> Ingested ' + (count || 1) + ' event(s) -> index=' + idx + ' sourcetype=' + singleSt + ' (HTTP 200)');
        streamStats.totalEvents += (count || 1);
        updateLiveCounter();
      } else {
        log('<span style="color: #ef4444;">HEC ERROR:</span> ' + (data.message || JSON.stringify(data)));
      }
    })
    .catch(function(err) {
      log('<span style="color: #ef4444;">COMMUNICATION ERROR:</span> ' + err.message);
    });
  };

  // Emit All Selected Sourcetypes
  window.datablasterEmitCount = function(count) {
    var selectedSourcetypes = getCheckedSourcetypes();
    if (selectedSourcetypes.length === 0) {
      alert('Please check at least one sourcetype.');
      return;
    }

    var cfg = {};
    try { cfg = JSON.parse(localStorage.getItem('datablaster_config') || '{}'); } catch(e) {}
    var hecUrl = cfg.hec_url || "https://127.0.0.1:8888/services/collector";
    var token = cfg.hec_token || "00000000-0000-0000-0000-000000000000";

    var host = (document.getElementById('emit-host') || {}).value || "device01";
    var ip = (document.getElementById('emit-ip') || {}).value || "10.0.0.1";
    var idx = (document.getElementById('emit-index') || {}).value || "idx_network_ops";
    var vendor = (document.getElementById('emit-vendor') || {}).value || "Cisco";
    var payloadTpl = (document.getElementById('emit-payload') || {}).value || "TEST_EVENT";

    log('Blasting ' + count + ' event(s) simultaneously across ' + selectedSourcetypes.length + ' sourcetypes (' + selectedSourcetypes.join(', ') + ')...');

    selectedSourcetypes.forEach(function(st) {
      var payload = {
        action: "blast_single_device",
        hec: hecUrl,
        token: token,
        count: count || 1,
        device_info: {
          name: host,
          host: host,
          ip: ip,
          index: idx,
          sourcetype: st,
          vendor: vendor,
          sampleEvent: payloadTpl
        }
      };

      fetch(getRestUrl(), {
        method: 'POST',
        headers: getHeaders(),
        body: JSON.stringify(payload)
      })
      .then(function(r) { return r.json(); })
      .then(function(data) {
        if (data.status === 'success' || data.code === 200) {
          log('<span style="color: #22c55e;">SUCCESS:</span> ' + count + ' event(s) -> [' + idx + '] sourcetype=' + st);
          streamStats.totalEvents += (count || 1);
          updateLiveCounter();
        } else {
          log('<span style="color: #ef4444;">HEC ERROR [' + st + ']:</span> ' + (data.message || JSON.stringify(data)));
        }
      })
      .catch(function(err) {
        log('<span style="color: #ef4444;">ERROR [' + st + ']:</span> ' + err.message);
      });
    });
  };

  // Continuous Telemetry Streaming (Without Scenario)
  window.datablasterStartContinuousStream = function() {
    if (continuousTimer) return;

    var rateEl = document.getElementById('continuous-rate-select');
    var rate = parseInt(rateEl ? rateEl.value : "10", 10) || 10;
    var batchSize = Math.max(1, Math.round(rate / 2));
    var intervalMs = Math.round((batchSize / rate) * 1000);

    var btnStart = document.getElementById('btn-start-continuous');
    var btnStop = document.getElementById('btn-stop-continuous');
    var badge = document.getElementById('continuous-status-badge');

    if (btnStart) btnStart.style.display = 'none';
    if (btnStop) btnStop.style.display = 'inline-flex';
    if (badge) {
      badge.textContent = 'STREAMING ACTIVE (' + rate + ' EPS)';
      badge.style.background = '#15803d';
      badge.style.color = '#ffffff';
    }

    log('<span style="color: #22c55e; font-weight: bold;">CONTINUOUS INGESTION STARTED:</span> Pumping live telemetry at target ' + rate + ' EPS without scenario constraints...');

    continuousTimer = setInterval(function() {
      var mode = (document.querySelector('input[name="sourcetype_mode"]:checked') || {}).value || "all";
      if (mode === "single") {
        window.datablasterEmitSingleSourcetype(batchSize);
      } else {
        window.datablasterEmitCount(batchSize);
      }
    }, intervalMs);
  };

  window.datablasterStopContinuousStream = function() {
    if (continuousTimer) clearInterval(continuousTimer);
    continuousTimer = null;

    var btnStart = document.getElementById('btn-start-continuous');
    var btnStop = document.getElementById('btn-stop-continuous');
    var badge = document.getElementById('continuous-status-badge');

    if (btnStart) btnStart.style.display = 'inline-flex';
    if (btnStop) btnStop.style.display = 'none';
    if (badge) {
      badge.textContent = 'STREAM IDLE';
      badge.style.background = '#334155';
      badge.style.color = '#94a3b8';
    }

    log('<span style="color: #f59e0b; font-weight: bold;">CONTINUOUS INGESTION STOPPED:</span> Stream halted.');
  };

  // Full Network Path Sequential Traversal Stream
  window.datablasterStartStream = function() {
    var streamBtn = document.getElementById('btn-stream-path');
    var stopBtn = document.getElementById('btn-stop-path');
    if (streamBtn) streamBtn.style.display = 'none';
    if (stopBtn) stopBtn.style.display = 'inline-flex';
    log('<span style="color: #0284c7; font-weight: bold;">PATH FLOW ACTIVE:</span> Traversing all 10 network path devices in sequence...');

    var nodeIdx = 0;
    pathStreamTimer = setInterval(function() {
      var n = PATH_NODES[nodeIdx % PATH_NODES.length];
      window.datablasterSelectNode(n);
      window.datablasterEmitSingleSourcetype(1);
      nodeIdx++;
    }, 1500);
  };

  window.datablasterStopStream = function() {
    if (pathStreamTimer) clearInterval(pathStreamTimer);
    pathStreamTimer = null;
    var streamBtn = document.getElementById('btn-stream-path');
    var stopBtn = document.getElementById('btn-stop-path');
    if (streamBtn) streamBtn.style.display = 'inline-flex';
    if (stopBtn) stopBtn.style.display = 'none';
    log('<span style="color: #f59e0b; font-weight: bold;">PATH FLOW STOPPED:</span> Traversal terminated.');
  };

  function updateLiveCounter() {
    var ctr = document.getElementById('live-total-counter');
    if (ctr) ctr.textContent = streamStats.totalEvents.toLocaleString();
  }

  // Bind Mode Radio Changes
  window.datablasterOnModeChange = function() {
    var mode = (document.querySelector('input[name="sourcetype_mode"]:checked') || {}).value || "all";
    var singleContainer = document.getElementById('container-single-sourcetype');
    var multiContainer = document.getElementById('container-multi-sourcetype');
    if (mode === "single") {
      if (singleContainer) singleContainer.style.display = 'block';
      if (multiContainer) multiContainer.style.display = 'none';
    } else {
      if (singleContainer) singleContainer.style.display = 'none';
      if (multiContainer) multiContainer.style.display = 'block';
    }
  };

  // Direct jQuery Event Listeners
  function bindDomEvents() {
    $('#emit-class').on('change', window.datablasterOnClassChange);
    $('#emit-vendor').on('change', window.datablasterOnVendorChange);
    $('input[name="sourcetype_mode"]').on('change', window.datablasterOnModeChange);

    $('#btn-emit-single-st').on('click', function() { window.datablasterEmitSingleSourcetype(1); });
    $('#btn-emit-selected').on('click', function() { window.datablasterEmitCount(1); });
    $('#btn-burst-50').on('click', function() { window.datablasterEmitCount(50); });
    $('#btn-burst-100').on('click', function() { window.datablasterEmitCount(100); });
    $('#btn-blast-selected-1').on('click', function() { window.datablasterEmitSingleSourcetype(1); });
    $('#btn-blast-selected-50').on('click', function() { window.datablasterEmitCount(50); });

    $('#btn-start-continuous').on('click', window.datablasterStartContinuousStream);
    $('#btn-stop-continuous').on('click', window.datablasterStopContinuousStream);
    $('#btn-stream-path').on('click', window.datablasterStartStream);
    $('#btn-stop-path').on('click', window.datablasterStopStream);

    $('#btn-select-all-st').on('click', window.datablasterToggleAllSourcetypes);
    $('#btn-reset-template').on('click', window.datablasterReloadTemplate);
  }

  // Initialization
  function initializeDashboard() {
    bindDomEvents();
    window.datablasterOnClassChange();
    renderCanvas();
    renderDeviceGrid();
    window.datablasterOnModeChange();
    log('Scenario Builder & Device Blaster ready. Topology canvas rendered with 10 network devices.');
  }

  // Retry loop until SimpleXML panel DOM nodes exist
  var initAttempts = 0;
  function pollReady() {
    initAttempts++;
    if (document.getElementById('canvas-svg') && document.getElementById('emit-class')) {
      initializeDashboard();
    } else if (initAttempts < 30) {
      setTimeout(pollReady, 100);
    }
  }

  pollReady();
});
