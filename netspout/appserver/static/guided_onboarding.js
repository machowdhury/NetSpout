/*
 * Splunk App: TA-network-data-blaster
 * View Script: guided_onboarding.js
 * Guided Onboarding Wizard Controller
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

  // Catalog of Network Sourcetypes
  var SOURCETYPE_CATALOG = [
    {
      id: "cisco:ios",
      label: "Cisco IOS-XE / Classic Syslog",
      vendor: "cisco",
      category: "Routing & Core",
      index: "idx_network_ops",
      sample: "%BGP-5-ADJCHANGE: neighbor 198.51.100.1 Up"
    },
    {
      id: "cisco:asa",
      label: "Cisco ASA Adaptive Security Appliance",
      vendor: "cisco",
      category: "Security & Firewall",
      index: "idx_security_fw",
      sample: "%ASA-4-106023: Deny tcp src outside:198.51.100.77/44321 dst inside:10.0.1.50/80 by access-group \"OUTSIDE_IN\" [0x0, 0x0]"
    },
    {
      id: "cisco:ftd",
      label: "Cisco Firepower Threat Defense (FTD)",
      vendor: "cisco",
      category: "Security & Firewall",
      index: "idx_security_fw",
      sample: "%FTD-1-430002: EventPriority: High, DeviceUUID: 4f1c9c7e-8c52, Intrusion Rule: 1:2100498, Protocol: TCP, SrcIP: 203.0.113.88, DstIP: 10.100.4.15"
    },
    {
      id: "cisco:catalyst:security:events",
      label: "Cisco Catalyst 9300 Security Events",
      vendor: "cisco",
      category: "Campus Access",
      index: "idx_network_ops",
      sample: "%SW_MATM-4-MACFLAP_NOTIF: Host 00:1a:2b:3c:4d:5e in vlan 20 is flapping between port Gi1/0/12 and port Gi1/0/24"
    },
    {
      id: "cisco:catalyst:rogue:threat_details",
      label: "Cisco Catalyst Rogue AP Detection",
      vendor: "cisco",
      category: "Wireless & Access",
      index: "idx_wireless_ops",
      sample: "cisco:catalyst:rogue:threat_details ap_name=\"AP-HQ-Floor3\" rogue_bssid=\"70:69:79:4c:11:02\" ssid=\"Corporate-Guest-EvilTwin\" rogue_type=\"Unclassified\" classification=\"Threat\" state=\"Alert\""
    },
    {
      id: "cisco:sdwan:linkhealth",
      label: "Cisco SD-WAN vEdge Link Health",
      vendor: "cisco",
      category: "WAN & SD-WAN",
      index: "idx_network_ops",
      sample: "vEdge-1000-Core: bfd: event=state_change local_color=biz-internet remote_color=biz-internet loss_pct=14.8 latency_ms=184.2 jitter_ms=42.1 sla_state=violated"
    },
    {
      id: "cisco:sdwan:BGP-5-ADJCHANGE",
      label: "Cisco SD-WAN BGP Route Failover",
      vendor: "cisco",
      category: "WAN & SD-WAN",
      index: "idx_network_ops",
      sample: "%BGP-5-ADJCHANGE: neighbor 198.51.100.1 vpn 10 Down BFD session down"
    },
    {
      id: "cisco:ise:syslog",
      label: "Cisco ISE Identity Services Engine",
      vendor: "cisco",
      category: "Security & Identity",
      index: "idx_security_fw",
      sample: "CISE_Passed_Authentications 0000000001 1 0 2026-09-19 12:00:00.000 +00:00 0000000001 5200 NOTICE Passed-Authentication: Authentication succeeded, User=jsmith, MAC=00:11:22:33:44:55"
    },
    {
      id: "cisco:thousandeyes:metric",
      label: "Cisco ThousandEyes Synthetic Metrics",
      vendor: "cisco",
      category: "Observability",
      index: "idx_performance_metrics",
      sample: "{\"test_name\":\"SaaS CRM Portal\",\"test_type\":\"http-server\",\"loss\":0.12,\"latency\":182.4,\"jitter\":15.1,\"response_code\":200,\"status\":\"degraded\"}"
    },
    {
      id: "cisco:thousandeyes:path-vis",
      label: "Cisco ThousandEyes Path Visualization",
      vendor: "cisco",
      category: "Observability",
      index: "idx_performance_metrics",
      sample: "{\"test_id\":9941,\"agent_name\":\"Enterprise Agent Dallas\",\"hop_index\":4,\"ip\":\"198.51.100.14\",\"rtt_ms\":48.2,\"loss_pct\":12.5}"
    },
    {
      id: "cisco:dc:nexus9k:syslog",
      label: "Cisco Nexus 9000 DC Switch Syslog",
      vendor: "cisco",
      category: "Data Center Fabric",
      index: "idx_performance_metrics",
      sample: "%ETHPORT-5-IF_DOWN_TX_PAUSE: Interface Ethernet1/12 buffer congestion pause frames transmitted threshold exceeded"
    },
    {
      id: "cisco:dc:aci:health",
      label: "Cisco ACI Spine/Leaf Fabric Health",
      vendor: "cisco",
      category: "Data Center Fabric",
      index: "idx_performance_metrics",
      sample: "{\"component\":\"topology/pod-1/node-101\",\"fabric_health_score\":74,\"queue_drops\":14820,\"status\":\"warning\"}"
    },
    {
      id: "cisco:ios:mdt",
      label: "Cisco Model-Driven Telemetry (MDT)",
      vendor: "cisco",
      category: "Streaming Telemetry",
      index: "cisco_mdt_metrics",
      sample: "{\"event\": \"metric\", \"fields\": {\"metric_name:memory.total_bytes\": 33554432, \"metric_name:memory.free_bytes\": 14208000, \"metric_name:cpu.utilization\": 24.5, \"metric_name:interface.octets.in\": 9845129840, \"metric_name:interface.octets.out\": 8741029810, \"_value\": 24.5, \"node_id\": \"DC-LEAF-01\", \"subscription_id\": 42, \"path\": \"Cisco-IOS-XE-memory-oper:memory-statistics\"}}"
    },
    {
      id: "pan:traffic",
      label: "Palo Alto Networks NGFW Traffic",
      vendor: "paloalto",
      category: "Security & Firewall",
      index: "idx_security_fw",
      sample: "1,2026/09/19 12:00:00,001801000001,TRAFFIC,drop,2304,2026/09/19 12:00:00,198.51.100.44,10.0.1.20,0.0.0.0,0.0.0.0,Rule-Deny-External,user1,,ssl,vsys1,untrust,trust,ethernet1/1,ethernet1/2,Log-Forward,2026/09/19 12:00:00,10482,1,54321,443,0,0,0x0,tcp,deny,128,128,0,1,2026/09/19 12:00:00,0,any,0,2984920,0x0,192.0.2.0-192.0.2.255,US,0,1,0,policy-deny,0,0,0,0,,PA-VM,from-policy"
    },
    {
      id: "pan:threat",
      label: "Palo Alto Networks Threat & IPS",
      vendor: "paloalto",
      category: "Security & Firewall",
      index: "idx_security_fw",
      sample: "1,2026/09/19 12:00:00,001801000001,THREAT,vulnerability,9941,2026/09/19 12:00:00,198.51.100.55,10.100.4.15,0.0.0.0,0.0.0.0,Security-Profile-Alert,attacker,,web-browsing,vsys1,untrust,trust,ethernet1/1,ethernet1/2,Log-Forward,2026/09/19 12:00:00,9841,1,41234,80,0,0,0x0,tcp,reset-both,\"Apache Log4j RCE CVE-2021-44228\"(30001),any,critical,client-to-server,2984921,0x0,192.0.2.0-192.0.2.255,US,0,1,0"
    },
    {
      id: "pan:system",
      label: "Palo Alto Networks System Events",
      vendor: "paloalto",
      category: "Security & Firewall",
      index: "idx_security_fw",
      sample: "1,2026/09/19 12:00:00,001801000001,SYSTEM,ha,0,2026/09/19 12:00:00,,ha-peer-up,HA Group 1: Peer transitioned to state active"
    },
    {
      id: "fortinet:fortigate",
      label: "Fortinet FortiGate UTM Syslog",
      vendor: "paloalto",
      category: "Security & Firewall",
      index: "idx_security_fw",
      sample: "date=2026-09-19 time=12:00:00 devname=\"FGT-EDGE-01\" devid=\"FG100ETK18000001\" type=\"utm\" subtype=\"ips\" level=\"alert\" vd=\"root\" srcip=198.51.100.99 srcport=49152 dstip=10.0.2.10 dstport=80 action=\"dropped\" attack=\"SQL.Injection.Union.Select\""
    },
    {
      id: "meraki:assurancealerts",
      label: "Cisco Meraki Assurance Alerts",
      vendor: "cisco",
      category: "Wireless & Access",
      index: "idx_wireless_ops",
      sample: "{\"version\":\"0.1\",\"sharedSecret\":\"meraki123\",\"sentAt\":\"2026-09-19T12:00:00.000Z\",\"organizationId\":\"98124\",\"networkId\":\"N_10928\",\"alertType\":\"rogue_ap_detected\",\"alertData\":{\"bssid\":\"00:14:22:01:23:45\",\"channel\":6,\"rssi\":-48}}"
    },
    {
      id: "meraki:traffic",
      label: "Cisco Meraki MX/MR Flow Traffic",
      vendor: "cisco",
      category: "Wireless & Access",
      index: "idx_wireless_ops",
      sample: "timestamp=1789780000.123 client_mac=00:11:22:33:44:55 ip=10.0.10.155 sport=52140 dport=443 dst=142.250.190.46 protocol=tcp app=Google-Services sent=4819 recv=28941 duration=14.2"
    },
    {
      id: "arista:telemetry:json",
      label: "Arista EOS Streaming Telemetry",
      vendor: "arista",
      category: "Data Center Fabric",
      index: "idx_performance_metrics",
      sample: "{\"timestamp\": 1789780000.456, \"device\": \"leaf-dc-01\", \"interface\": \"Ethernet1/1\", \"in_octets\": 894120489, \"out_octets\": 1048291048, \"pfc_rx_frames\": 4210, \"pfc_tx_frames\": 0}"
    },
    {
      id: "arista:flow:ipfix",
      label: "Arista IPFIX Flow Records",
      vendor: "arista",
      category: "Data Center Fabric",
      index: "idx_performance_metrics",
      sample: "flow_record: router=leaf-dc-02 src=10.200.1.10 dst=10.200.2.20 sport=9000 dport=9000 proto=udp bytes=28401948 packets=19482 dscp=46 flow_direction=ingress"
    },
    {
      id: "juniper:junos",
      label: "Juniper Junos Core Routing & MPLS",
      vendor: "arista",
      category: "Routing & Core",
      index: "idx_network_ops",
      sample: "Sep 19 12:00:00 pe-router-01 rpd[3021]: %DAEMON-4-RPD_MPLS_LSP_CHANGE: LSP to 192.0.2.1 switched to secondary path bypass-rsvp-te-02"
    },
    {
      id: "nokia:sros",
      label: "Nokia SR-OS Optical & Carrier Core",
      vendor: "arista",
      category: "Routing & Core",
      index: "idx_network_ops",
      sample: "1 2026-09-19T12:00:00.000Z 7750SR-12-Core-01 Root: 2004 - [SONET/SDH-4-OPTICAL_LOS] Optical loss of signal detected on port 1/1/c1/1"
    },
    {
      id: "zscaler:zia",
      label: "Zscaler Internet Access (ZIA) Cloud Proxy",
      vendor: "cloud",
      category: "SASE & Cloud Edge",
      index: "idx_security_fw",
      sample: "{\"datetime\":\"2026-09-19 12:00:00\",\"user\":\"jsmith@company.com\",\"url\":\"https://salesforce.com/api\",\"action\":\"Allowed\",\"proto\":\"HTTPS\",\"threatname\":\"None\",\"riskscore\":0,\"latency_ms\":42}"
    },
    {
      id: "zscaler:lss",
      label: "Zscaler Private Access (ZPA) LSS",
      vendor: "cloud",
      category: "SASE & Cloud Edge",
      index: "idx_security_fw",
      sample: "{\"datetime\":\"2026-09-19 12:00:00\",\"Customer\":\"Acme-Enterprise\",\"Application\":\"Internal-ERP\",\"ClientIP\":\"10.45.2.14\",\"ServerIP\":\"10.100.1.5\",\"PolicyRule\":\"Engineering-Access\",\"Status\":\"Success\"}"
    },
    {
      id: "cloudflare:r2",
      label: "Cloudflare Edge & Storage Telemetry",
      vendor: "cloud",
      category: "SASE & Cloud Edge",
      index: "idx_network_ops",
      sample: "{\"timestamp\":\"2026-09-19T12:00:00Z\",\"action\":\"GetObject\",\"bucket\":\"acme-prod-assets\",\"status\":200,\"client_ip\":\"198.51.100.10\",\"edge_latency_ms\":14.2}"
    }
  ];

  // Scenarios Catalog
  var SCENARIOS_CATALOG = [
    {
      id: "scenario_custom_multivendor_enterprise_stack.yml",
      title: "Full Multi-Vendor Enterprise Ingestion (MV-ENT-001)",
      desc: "5-tier end-to-end multi-vendor topology: Cisco Catalyst core, Meraki edge, Palo Alto NGFW, Arista spine/leaf, and Cloudflare SASE.",
      sourcetypes: ["cisco:ios", "pan:traffic", "arista:telemetry:json", "meraki:traffic"]
    },
    {
      id: "scenario_roce_v2_ai_fabric_congestion.yml",
      title: "AI Data Center Fabric - RoCE v2 Buffer Congestion (MV-002)",
      desc: "High-density GPU AI cluster simulation with PFC pause frame flapping, ASIC queue depth spikes, and telemetry loss.",
      sourcetypes: ["arista:telemetry:json", "cisco:dc:nexus9k:syslog", "arista:flow:ipfix"]
    },
    {
      id: "scenario_core_bgp_route_flap.yml",
      title: "Core BGP Instability & Route Flapping (MV-006)",
      desc: "Upstream transit carrier link oscillation triggers BFD dampening, BGP neighbor drops, and cross-domain reroutes.",
      sourcetypes: ["cisco:ios", "juniper:junos", "cisco:sdwan:BGP-5-ADJCHANGE"]
    },
    {
      id: "scenario_sdwan_branch_brownout.yml",
      title: "SD-WAN Branch Brownout & Dynamic SLA (MV-008)",
      desc: "Branch Internet circuit packet loss and jitter spikes force Cisco Catalyst 8000 SD-WAN tunnel failover.",
      sourcetypes: ["cisco:sdwan:linkhealth", "cisco:thousandeyes:metric", "cisco:sdwan:BGP-5-ADJCHANGE"]
    },
    {
      id: "scenario_core_100g_optical_attenuation.yml",
      title: "Core 100G Optical Degradation & TI-LFA (MV-011)",
      desc: "DWDM fiber attenuation on Nokia SR-OS triggers fast-reroute switch to Juniper MX RSVP-TE backup path.",
      sourcetypes: ["nokia:sros", "juniper:junos", "cisco:ios"]
    },
    {
      id: "scenario_edge_ngfw_capacity_saturation.yml",
      title: "Edge Next-Gen Firewall Capacity Saturation (MV-014)",
      desc: "Inbound threat surge saturates Palo Alto session tables, causing session drops and FortiGate failover.",
      sourcetypes: ["pan:traffic", "pan:threat", "fortinet:fortigate"]
    },
    {
      id: "scenario_cross_domain_slowness_triage.yml",
      title: "Cross-Domain Slowness Triage (MV-016)",
      desc: "Enterprise application performance degradation spanning Zscaler SASE proxy, Cisco WAN edge, and DC backend.",
      sourcetypes: ["zscaler:zia", "cisco:thousandeyes:metric", "pan:traffic"]
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
      return wizardState.selectedMultiSourcetypes;
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

    // Toggle container views
    $('.wizard-step-container').hide();
    $('#container-step-' + stepNum).show();

    // Step-specific initialization
    if (stepNum === 2) {
      updateActiveIndexDisplay();
    } else if (stepNum === 4) {
      updateSummaryTable();
    }
  }

  function updateActiveIndexDisplay() {
    var idx = $('#wizard-target-index-select').val();
    wizardState.targetIndex = idx;
    $('#active-index-label').text(idx);
    $('#wizard-desc-index').text(idx);
  }

  function updateSummaryTable() {
    var modeLabel = wizardState.mode === "single" ? "Single Sourcetype" : (wizardState.mode === "multi" ? "Multi-Sourcetype Batch" : "Architectural Scenario");
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
        optgroup.append(opt);
      });
      sel.append(optgroup);
    });

    sel.on('change', function() {
      wizardState.selectedSourcetype = $(this).val();
      updateSinglePreview();
    });

    updateSinglePreview();
  }

  function updateSinglePreview() {
    var st = SOURCETYPE_CATALOG.find(function(item) { return item.id === wizardState.selectedSourcetype; });
    if (st) {
      $('#wizard-single-preview').text(st.sample);
      // Auto-suggest best index for sourcetype
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

    SCENARIOS_CATALOG.forEach(function(item, idx) {
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
        $('.scenario-pick-card').css('border', '1px solid #334155');
        card.css('border', '2px solid #0284c7');
        card.find('input').prop('checked', true);
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
      if (res.status === 'success' || res.http_status === 200) {
        hecBadge.css({ 'background': '#14532d', 'color': '#4ade80' }).text('ONLINE (' + res.latency_ms + 'ms)');
        tokenBadge.css({ 'background': '#14532d', 'color': '#4ade80' }).text('AUTHENTICATED');
        logOutput('<span style="color: #4ade80;">✔ Preflight HEC & Token verification passed (HTTP 200, ' + res.latency_ms + 'ms latency).</span>');
      } else {
        hecBadge.css({ 'background': '#7f1d1d', 'color': '#f87171' }).text('HTTP ' + (res.http_status || 'ERR'));
        tokenBadge.css({ 'background': '#7f1d1d', 'color': '#f87171' }).text('FAIL');
        logOutput('<span style="color: #f87171;">✖ HEC Response: ' + (res.message || 'Error connecting to HEC') + '</span>');
      }
    })
    .catch(function(err) {
      hecBadge.css({ 'background': '#7f1d1d', 'color': '#f87171' }).text('NETWORK ERR');
      tokenBadge.css({ 'background': '#7f1d1d', 'color': '#f87171' }).text('UNREACHABLE');
      logOutput('<span style="color: #f87171;">✖ Preflight probe error: ' + err.message + '</span>');
    });
  }

  // Execute Ingestion Blast
  function executeWizardBlast() {
    var btn = $('#btn-wizard-blast-now');
    var spinner = $('#wizard-blast-spinner');
    var verifyContainer = $('#wizard-verification-container');
    var searchLink = $('#link-splunk-search');

    btn.prop('disabled', true).css('opacity', 0.6);
    spinner.show();
    verifyContainer.hide();

    var cfg = {};
    try { cfg = JSON.parse(localStorage.getItem('datablaster_config') || '{}'); } catch(e) {}
    var hecUrl = cfg.hec_url || "https://127.0.0.1:8888/services/collector";
    var token = cfg.hec_token || "00000000-0000-0000-0000-000000000000";
    var sslVerify = cfg.ssl_verify || false;
    var targetIndex = wizardState.targetIndex || "idx_security_fw";
    var volume = wizardState.volume || 1;

    logOutput('Starting ingestion blast via Splunk REST orchestrator...');
    logOutput('Destination Index: <b style="color: #38bdf8;">' + targetIndex + '</b> | Target HEC: <span style="color: #94a3b8;">' + hecUrl + '</span>');

    if (wizardState.mode === "single") {
      var sourcetype = "";
      var content = "";

      if (wizardState.singleSourceType === "upload") {
        sourcetype = $('#wizard-custom-sourcetype-name').val().trim() || "custom:network:log";
        content = $('#wizard-custom-content').val().trim();
      } else {
        var catItem = SOURCETYPE_CATALOG.find(function(c) { return c.id === wizardState.selectedSourcetype; });
        sourcetype = catItem ? catItem.id : "cisco:ios";
        content = catItem ? catItem.sample : "%BGP-5-ADJCHANGE: neighbor 198.51.100.1 Up";
      }

      logOutput('Blasting ' + volume + ' event(s) for single sourcetype: <span style="color: #a855f7;">[' + sourcetype + ']</span>');

      var payload = {
        action: "onboard_sample",
        sourcetype: sourcetype,
        index: targetIndex,
        sample_content: content,
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
        btn.prop('disabled', false).css('opacity', 1);
        spinner.hide();

        if (data.status === 'success' || data.code === 200) {
          logOutput('<span style="color: #4ade80; font-weight: bold;">SUCCESS:</span> ' + (data.message || 'Indexed events successfully into Splunk'));
          showVerification(targetIndex, [sourcetype]);
        } else {
          logOutput('<span style="color: #f87171;">HEC ERROR:</span> ' + (data.message || JSON.stringify(data)));
        }
      })
      .catch(function(err) {
        btn.prop('disabled', false).css('opacity', 1);
        spinner.hide();
        logOutput('<span style="color: #f87171;">HTTP/REST ERROR:</span> ' + err.message);
      });

    } else if (wizardState.mode === "multi") {
      var sourcetypes = wizardState.selectedMultiSourcetypes;
      if (sourcetypes.length === 0) {
        alert('Please select at least one sourcetype in Step 1.');
        btn.prop('disabled', false).css('opacity', 1);
        spinner.hide();
        return;
      }

      logOutput('Initiating batch multi-sourcetype blast for ' + sourcetypes.length + ' sourcetypes...');
      var completed = 0;
      var failed = 0;

      function blastNext(index) {
        if (index >= sourcetypes.length) {
          btn.prop('disabled', false).css('opacity', 1);
          spinner.hide();
          logOutput('<span style="color: #4ade80; font-weight: bold;">BATCH COMPLETE:</span> Ingested ' + completed + ' sourcetypes successfully (' + failed + ' failed).');
          showVerification(targetIndex, sourcetypes);
          return;
        }

        var st = sourcetypes[index];
        var item = SOURCETYPE_CATALOG.find(function(c) { return c.id === st; });
        var content = item ? item.sample : "%BGP-5-ADJCHANGE: neighbor 198.51.100.1 Up";

        fetch(getRestUrl(), {
          method: 'POST',
          headers: getHeaders(),
          body: JSON.stringify({
            action: "onboard_sample",
            sourcetype: st,
            index: targetIndex,
            sample_content: content,
            hec: hecUrl,
            token: token,
            ssl_verify: sslVerify
          })
        })
        .then(function(r) { return r.json(); })
        .then(function(res) {
          if (res.status === 'success' || res.code === 200) {
            completed++;
            logOutput('✔ [' + (index + 1) + '/' + sourcetypes.length + '] ' + st + ' -> ' + targetIndex + ' (OK)');
          } else {
            failed++;
            logOutput('✖ [' + (index + 1) + '/' + sourcetypes.length + '] ' + st + ' -> ' + (res.message || 'failed'));
          }
          blastNext(index + 1);
        })
        .catch(function(err) {
          failed++;
          logOutput('✖ [' + (index + 1) + '/' + sourcetypes.length + '] ' + st + ' -> Error: ' + err.message);
          blastNext(index + 1);
        });
      }

      blastNext(0);

    } else if (wizardState.mode === "scenario") {
      logOutput('Launching architectural scenario: <b style="color: #38bdf8;">' + wizardState.selectedScenario + '</b>');

      fetch(getRestUrl(), {
        method: 'POST',
        headers: getHeaders(),
        body: JSON.stringify({
          action: "start",
          scenario: wizardState.selectedScenario,
          eps: 100,
          hec: hecUrl,
          token: token
        })
      })
      .then(function(r) { return r.json(); })
      .then(function(data) {
        btn.prop('disabled', false).css('opacity', 1);
        spinner.hide();

        if (data.status === 'success' || data.code === 200) {
          logOutput('<span style="color: #4ade80; font-weight: bold;">SCENARIO ACTIVE:</span> ' + (data.message || 'Simulation runner started under PID ' + data.pid));
          var sc = SCENARIOS_CATALOG.find(function(s) { return s.id === wizardState.selectedScenario; });
          showVerification(targetIndex, sc ? sc.sourcetypes : []);
        } else {
          logOutput('<span style="color: #f87171;">SCENARIO LAUNCH ERROR:</span> ' + (data.message || JSON.stringify(data)));
        }
      })
      .catch(function(err) {
        btn.prop('disabled', false).css('opacity', 1);
        spinner.hide();
        logOutput('<span style="color: #f87171;">HTTP/REST ERROR:</span> ' + err.message);
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

  // Wizard Bindings
  function initWizard() {
    // Mode Radio Cards
    $('.mode-selection-card').on('click', function() {
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
    $('input[name="single_source_type"]').on('change', function() {
      var type = $(this).val();
      wizardState.singleSourceType = type;
      $('#single-catalog-container').toggle(type === 'catalog');
      $('#single-upload-container').toggle(type === 'upload');
    });

    // Single File Upload Dropzone
    var dropzone = $('#wizard-dropzone');
    var fileInput = $('#wizard-file-input');
    var fileBadge = $('#wizard-file-badge');

    dropzone.on('click', function() { fileInput.trigger('click'); });
    dropzone.on('dragover dragenter', function(e) {
      e.preventDefault();
      dropzone.css({ 'border-color': '#0284c7', 'background': 'rgba(2, 132, 199, 0.08)' });
    });
    dropzone.on('dragleave dragend', function(e) {
      e.preventDefault();
      dropzone.css({ 'border-color': '#475569', 'background': '#0f172a' });
    });
    dropzone.on('drop', function(e) {
      e.preventDefault();
      dropzone.css({ 'border-color': '#475569', 'background': '#0f172a' });
      var files = e.originalEvent.dataTransfer ? e.originalEvent.dataTransfer.files : null;
      if (files && files.length > 0) processWizardFile(files[0]);
    });
    fileInput.on('change', function(e) {
      if (e.target.files && e.target.files.length > 0) processWizardFile(e.target.files[0]);
    });

    function processWizardFile(file) {
      var reader = new FileReader();
      reader.onload = function(evt) {
        var content = evt.target.result;
        $('#wizard-custom-content').val(content);
        var lines = content.split('
').filter(function(l) { return l.trim().length > 0; });
        var sizeKb = (file.size / 1024).toFixed(1);
        fileBadge.show().text('📄 ' + file.name + ' (' + sizeKb + ' KB, ' + lines.length + ' lines)');

        var baseName = file.name.replace(/\.[^/.]+$/, '').toLowerCase().replace(/[^a-z0-9]+/g, ':').replace(/^:+|:+$/g, '');
        if (baseName && baseName.length > 2) {
          $('#wizard-custom-sourcetype-name').val(baseName);
        }
      };
      reader.readAsText(file);
    }

    // Multi Filter Buttons
    $('.vendor-filter-btn').on('click', function() {
      $('.vendor-filter-btn').css({ 'background': '#1e293b', 'color': '#cbd5e1', 'border': '1px solid #334155' });
      $(this).css({ 'background': '#0284c7', 'color': '#fff', 'border': 'none' });
      var vendor = $(this).data('vendor');
      populateMultiGrid(vendor);
    });

    // Multi Select All / Clear
    $('#btn-multi-select-all').on('click', function() {
      $('#multi-sourcetype-grid input').prop('checked', true).trigger('change');
    });
    $('#btn-multi-clear-all').on('click', function() {
      $('#multi-sourcetype-grid input').prop('checked', false).trigger('change');
      wizardState.selectedMultiSourcetypes = [];
      updateMultiSelectedCount();
    });

    // Target Index Select
    $('#wizard-target-index-select').on('change', function() {
      updateActiveIndexDisplay();
    });

    // Custom Index Drawer
    $('#btn-wizard-open-custom-index').on('click', function() {
      $('#wizard-custom-index-drawer').slideDown(150);
      $('#wizard-custom-index-name').focus();
    });
    $('#btn-wizard-close-custom-index').on('click', function() {
      $('#wizard-custom-index-drawer').slideUp(150);
    });
    $('#btn-wizard-submit-custom-index').on('click', function() {
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
    $('.volume-card').on('click', function() {
      $('.volume-card').css('border', '1px solid #334155');
      $(this).css('border', '2px solid #0284c7');
      wizardState.volume = parseInt($(this).data('volume'), 10) || 1;
    });

    // Preflight Test Button
    $('#btn-wizard-run-preflight').on('click', runWizardPreflight);

    // Blast Button
    $('#btn-wizard-blast-now').on('click', executeWizardBlast);

    // Restart Wizard
    $('#btn-wizard-restart').on('click', function() {
      goToStep(1);
    });

    // Stepper Navigation Buttons
    $('#badge-step-1').on('click', function() { goToStep(1); });
    $('#badge-step-2').on('click', function() { goToStep(2); });
    $('#badge-step-3').on('click', function() { goToStep(3); });
    $('#badge-step-4').on('click', function() { goToStep(4); });

    $('#btn-next-step-1').on('click', function() { goToStep(2); });
    $('#btn-back-step-2').on('click', function() { goToStep(1); });
    $('#btn-next-step-2').on('click', function() { goToStep(3); });
    $('#btn-back-step-3').on('click', function() { goToStep(2); });
    $('#btn-next-step-3').on('click', function() { goToStep(4); });
    $('#btn-back-step-4').on('click', function() { goToStep(3); });

    // Initialize catalogs & components
    populateSingleSourcetypeCatalog();
    populateMultiGrid('all');
    populateScenarioCards();
    loadAvailableIndexes();
  }

  var attempts = 0;
  function pollReady() {
    attempts++;
    if (document.getElementById('wizard-stepper')) {
      initWizard();
    } else if (attempts < 30) {
      setTimeout(pollReady, 100);
    }
  }

  pollReady();
});
