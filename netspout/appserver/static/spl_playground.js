/**
 * NetSpout SPL Playground & NOC/SOC Analytics Workbench
 * Author: Mahamudul Chowdhury (mchowdhury@splunk.com)
 *
 * Interactive SPL workspace with 30+ pre-canned multi-vendor queries,
 * live Splunkd REST search execution, dynamic table/raw/chart rendering,
 * and automated single-click sample telemetry ingestion.
 */

require(['jquery', 'splunkjs/mvc', 'splunkjs/mvc/simplexml/ready!'], function($, mvc) {
  'use strict';

  // --- Pre-Canned Query Library (30+ Multi-Vendor Queries) ---
  var PRE_CANNED_QUERIES = [
    // CISCO SYSTEMS
    {
      id: 'cisco-crc-flaps',
      category: 'cisco',
      vendor: 'Cisco Systems',
      sourcetype: 'cisco:ios:syslog',
      default_index: 'idx_network_ops',
      title: 'IOS-XE / Catalyst: Interface Errors & Flaps',
      spl: 'index=* (sourcetype="cisco:ios:syslog" OR sourcetype="cisco:ios") ("line protocol" OR "LINK-3-UPDOWN" OR "CRC")\n| rex field=_raw "interface (?<interface>\\S+)"\n| stats count, latest(_time) as last_seen by host, interface\n| where count > 0\n| sort -count',
      description: 'Detects physical layer faults, carrier loss, and CRC frame corruption across Catalyst switches.'
    },
    {
      id: 'cisco-sdwan-sla',
      category: 'cisco',
      vendor: 'Cisco Catalyst SD-WAN',
      sourcetype: 'cisco:sdwan:linkhealth',
      default_index: 'idx_network_ops',
      title: 'SD-WAN: BFD Path Loss & SLA Brownouts',
      spl: 'index=* sourcetype="cisco:sdwan:linkhealth"\n| stats avg(loss_percentage) as avg_loss_pct, max(latency) as max_latency_ms, max(jitter) as max_jitter_ms, count by site_id, site_name, local_color\n| eval avg_loss_pct=round(avg_loss_pct, 2), max_latency_ms=round(max_latency_ms, 1)\n| sort -avg_loss_pct',
      description: 'Surfaces transport circuits breaching enterprise SLA thresholds across MPLS, Internet, and LTE underlay paths.'
    },
    {
      id: 'cisco-sdwan-dpi',
      category: 'cisco',
      vendor: 'Cisco Catalyst SD-WAN',
      sourcetype: 'cisco:sdwan:dpi',
      default_index: 'idx_network_ops',
      title: 'SD-WAN: DPI Application Top Talkers',
      spl: 'index=* sourcetype="cisco:sdwan:dpi"\n| stats sum(bytes_sent) as tx_bytes, sum(bytes_recv) as rx_bytes, dc(src_ip) as active_clients by app_name, vpn_id\n| eval total_mb = round((tx_bytes+rx_bytes)/(1024*1024), 2)\n| sort -total_mb\n| head 10',
      description: 'Aggregates application bandwidth consumption across enterprise VPN segments to isolate bandwidth hogs.'
    },
    {
      id: 'cisco-mdt-optical',
      category: 'cisco',
      vendor: 'Cisco MDT gNMI',
      sourcetype: 'cisco:mdt:telemetry',
      default_index: 'cisco_mdt_metrics',
      title: 'OpenConfig MDT: Optical RX Power & Laser Triage',
      spl: '| mstats avg(_value) as avg_rx_power min(_value) as min_rx_power where index=cisco_mdt_metrics metric_name="*optical-rx-power*" span=1m by device, interface\n| where min_rx_power < -18\n| sort min_rx_power',
      description: 'Monitors pluggable transceiver optical power margins via Model-Driven Telemetry to predict laser degradation.'
    },
    {
      id: 'cisco-ise-nac',
      category: 'cisco',
      vendor: 'Cisco ISE',
      sourcetype: 'cisco:ise:nac:8021x',
      default_index: 'idx_network_ops',
      title: 'ISE: 802.1X NAC Authentication Triage',
      spl: 'index=* (sourcetype="cisco:ise:nac:8021x" OR sourcetype="cisco:ise:syslog")\n| stats count(eval(match(_raw, "Failed|Reject"))) as failed_auths, count(eval(match(_raw, "Passed|Success"))) as passed_auths by host\n| eval fail_rate = round(failed_auths*100/(failed_auths+passed_auths+0.001), 1)\n| sort -failed_auths\n| head 10',
      description: 'Identifies clients failing 802.1X certificate checks, EAP-TLS handshake drops, and unauthorized endpoint probing.'
    },
    {
      id: 'cisco-duo-mfa',
      category: 'cisco',
      vendor: 'Cisco Duo',
      sourcetype: 'cisco:duo:authentication',
      default_index: 'cisco_duo',
      title: 'Duo MFA: Fraud Denials & Impossible Travel',
      spl: 'index=* (sourcetype="cisco:duo:authentication" OR sourcetype="cisco:duo:push:prompt" OR sourcetype="cisco:duo:authentication_v2")\n| spath\n| search result="FRAUD" OR result="DENIED" OR result="FAILURE" OR result="fraud" OR result="denied"\n| eval user=coalesce(username, \'user.name\', \'user\'), city=coalesce(\'location.city\', location, "Unknown")\n| stats count, values(city) as cities, dc(city) as distinct_cities by user\n| where count > 0\n| sort -count',
      description: 'Audits Duo Mobile push fraud alerts, passcode brute-force attempts, and rapid geo-location anomalies.'
    },
    {
      id: 'cisco-meraki-wifi',
      category: 'cisco',
      vendor: 'Cisco Meraki',
      sourcetype: 'meraki:devices',
      default_index: 'idx_wireless_ops',
      title: 'Meraki: Wi-Fi Access Points & Connectivity State',
      spl: 'index=* (sourcetype="meraki:devices" OR sourcetype="meraki:accesspoints")\n| stats count, latest(status) as status by name, serial, productType\n| sort -count',
      description: 'Tracks AP health status, hardware serials, and operating state across enterprise wireless networks.'
    },
    {
      id: 'cisco-mds-san',
      category: 'cisco',
      vendor: 'Cisco MDS SAN',
      sourcetype: 'cisco:mds:san:fc',
      default_index: 'idx_network_ops',
      title: 'Cisco MDS: Fibre Channel B2B Credit Starvation',
      spl: 'index=* sourcetype="cisco:mds:san:fc"\n| rex field=_raw "Interface (?<fc_port>\\S+) Tx credit loss"\n| stats count, latest(_raw) as latest_event by host, fc_port\n| sort -count',
      description: 'Identifies slow-drain storage devices causing Buffer-to-Buffer credit starvation across high-speed SAN fabrics.'
    },

    // PALO ALTO NETWORKS
    {
      id: 'pan-top-dropped',
      category: 'paloalto',
      vendor: 'Palo Alto Networks',
      sourcetype: 'pan:traffic',
      default_index: 'idx_security_fw',
      title: 'PAN-OS: Top Denied Applications & Attacker IPs',
      spl: 'index=* sourcetype="pan:traffic" (action="deny" OR action="drop" OR action="reset-both")\n| stats count as dropped_sessions, sum(bytes) as total_bytes by src, app, dest_port\n| sort -dropped_sessions\n| head 15',
      description: 'Isolates firewall policy violations, blocked reconnaissance attempts, and targeted exploit traffic.'
    },
    {
      id: 'pan-threat-triage',
      category: 'paloalto',
      vendor: 'Palo Alto Networks',
      sourcetype: 'pan:threat',
      default_index: 'idx_security_fw',
      title: 'PAN-OS: Threat & Exploit Prevention Incidents',
      spl: 'index=* sourcetype="pan:threat"\n| stats count, values(threat_name) as threats by severity, src, dst\n| sort -count',
      description: 'Surfaces high-priority CVE vulnerabilities, IPS signatures, and command-and-control beacons.'
    },
    {
      id: 'pan-globalprotect-vpn',
      category: 'paloalto',
      vendor: 'Palo Alto Networks',
      sourcetype: 'pan:globalprotect',
      default_index: 'idx_security_fw',
      title: 'GlobalProtect: Failed Teleworker VPN Handshakes',
      spl: 'index=* sourcetype="pan:globalprotect" (status="failed" OR error="*")\n| stats count by user, client_ver, public_ip, error\n| sort -count',
      description: 'Audits remote teleworker VPN authentication failures and outdated client agent versions.'
    },

    // FORTINET
    {
      id: 'fortigate-traffic-denied',
      category: 'fortinet',
      vendor: 'Fortinet',
      sourcetype: 'fortinet:fortigate:traffic',
      default_index: 'idx_security_fw',
      title: 'FortiGate: Denied Sessions & Policy Violations',
      spl: 'index=* sourcetype="fortinet:fortigate:traffic" (action="deny" OR action="close" OR action="block")\n| stats count, sum(sentbyte) as bytes_sent, sum(rcvdbyte) as bytes_recv by srcip, dstip, proto, app\n| sort -count\n| head 15',
      description: 'Analyzes firewall deny events across FortiOS Next-Gen clusters to detect probing and blocked connections.'
    },
    {
      id: 'fortigate-sdwan-health',
      category: 'fortinet',
      vendor: 'Fortinet',
      sourcetype: 'fortinet:sdwan:health',
      default_index: 'idx_network_ops',
      title: 'FortiGate: SD-WAN Underlay Health & Jitter',
      spl: 'index=* sourcetype="fortinet:sdwan:health"\n| stats avg(packet_loss) as avg_loss, avg(latency) as avg_lat by link_name, gateway\n| sort -avg_loss',
      description: 'Audits multi-path SD-WAN underlays and SLA steering metrics across WAN edge interfaces.'
    },

    // ARISTA NETWORKS
    {
      id: 'arista-interface-flaps',
      category: 'arista',
      vendor: 'Arista Networks',
      sourcetype: 'arista:eos:syslog',
      default_index: 'idx_network_ops',
      title: 'Arista EOS: Interface Flaps & MLAG State',
      spl: 'index=* (sourcetype="arista:eos:syslog" OR sourcetype="arista:eos") ("LINEPROTO" OR "PFC" OR "MLAG" OR "watchdog")\n| stats count, latest(_time) as last_seen by host\n| sort -count',
      description: 'Audits spine-leaf EOS link state transitions, MLAG peer sync drops, and optics flap alarms.'
    },
    {
      id: 'arista-roce-congestion',
      category: 'arista',
      vendor: 'Arista Networks',
      sourcetype: 'arista:eos:telemetry',
      default_index: 'idx_network_ops',
      title: 'Arista RoCE v2: AI DC Buffer Congestion & PFC Pauses',
      spl: 'index=* sourcetype="arista:eos:telemetry" ("buffer" OR "pfc" OR "ecn")\n| stats sum(pause_rx_pkts) as pfc_pauses, avg(queue_depth_pct) as avg_buffer by device, interface\n| sort -pfc_pauses',
      description: 'Tracks RDMA-over-Converged-Ethernet (RoCE v2) fabric headroom and Priority Flow Control frame counts in AI clusters.'
    },

    // JUNIPER NETWORKS
    {
      id: 'juniper-bgp-instability',
      category: 'juniper',
      vendor: 'Juniper Networks',
      sourcetype: 'juniper:junos',
      default_index: 'idx_network_ops',
      title: 'Junos OS: BGP Route Flapping & RPD Faults',
      spl: 'index=* (sourcetype="juniper:junos" OR sourcetype="juniper:syslog") ("BGP" OR "rpd" OR "RPD_" OR "KRT")\n| stats count, latest(_raw) as latest_event by host\n| sort -count',
      description: 'Correlates Routing Protocol Daemon (rpd) exceptions, peer dropouts, and kernel routing table sync delays.'
    },
    {
      id: 'juniper-optical-tilfa',
      category: 'juniper',
      vendor: 'Juniper Networks',
      sourcetype: 'juniper:junos',
      default_index: 'idx_network_ops',
      title: 'Junos OS: Core 100G Optical Degradation & TI-LFA Reroute',
      spl: 'index=* sourcetype="juniper:junos" ("TI-LFA" OR "optics" OR "laser" OR "degraded" OR "reroute")\n| stats count by host, interface\n| sort -count',
      description: 'Surfaces Topology-Independent Loop-Free Alternate (TI-LFA) fast-reroute triggers caused by laser power loss.'
    },

    // STORAGE & EDGE SECURITY
    {
      id: 'zscaler-tunnel-status',
      category: 'storage',
      vendor: 'Zscaler',
      sourcetype: 'zscaler:tunnel',
      default_index: 'netops_logs',
      title: 'Zscaler: Private Access Tunnel Health & Latency',
      spl: 'index=* (sourcetype="zscaler:tunnel" OR sourcetype="zscaler:lss")\n| stats count by Application, PolicyAction, Customer\n| sort -count',
      description: 'Monitors ZPA app connector tunnels, client TLS handshakes, and tunnel round-trip times.'
    },
    {
      id: 'netskope-cloud-dlp',
      category: 'storage',
      vendor: 'Netskope',
      sourcetype: 'netskope:sse',
      default_index: 'netops_logs',
      title: 'Netskope SSE: Cloud App Policy & DLP Violations',
      spl: 'index=* (sourcetype="netskope:sse" OR sourcetype="netskope:json")\n| stats count by app_name, action, user\n| sort -count',
      description: 'Audits Security Service Edge (SSE) CASB violations, sensitive data uploads, and shadow IT services.'
    },
    {
      id: 'f5-bigip-pool-health',
      category: 'storage',
      vendor: 'F5 BIG-IP',
      sourcetype: 'f5:bigip:syslog',
      default_index: 'idx_network_ops',
      title: 'F5 BIG-IP: Virtual Server & Pool Member Flaps',
      spl: 'index=* (sourcetype="f5:bigip:syslog" OR sourcetype="f5:bigip:traffic")\n| stats count by vip_name, pool_name, status\n| sort -count',
      description: 'Monitors LTM pool health monitor timeouts, node markings down, and SSL handshake rejections.'
    },
    {
      id: 'checkpoint-fw-drops',
      category: 'storage',
      vendor: 'Check Point',
      sourcetype: 'checkpoint:cef',
      default_index: 'idx_security_fw',
      title: 'Check Point Quantum: Gateway Drops & Anti-Bot',
      spl: 'index=* sourcetype="checkpoint:cef" (act="Drop" OR act="Reject" OR act="Block")\n| stats count by src, dst, proto, reason\n| sort -count',
      description: 'Analyzes Quantum Security Gateway connection drops, Anti-Bot detections, and IPS signature matches.'
    },
    {
      id: 'nokia-sros-peering',
      category: 'storage',
      vendor: 'Nokia SR OS',
      sourcetype: 'nokia:sros',
      default_index: 'idx_network_ops',
      title: 'Nokia 7750 SR OS: BGP Core Peering State',
      spl: 'index=* (sourcetype="nokia:sros" OR sourcetype="nokia:sros:syslog")\n| stats count, latest(_raw) as latest_event by host\n| sort -count',
      description: 'Tracks Nokia Service Router OS BGP session transitions and MPLS RSVP-TE LSP signal states.'
    },

    // NOC / SOC INCIDENT TRIAGE (MV-001 through MV-016)
    {
      id: 'noc-mv001-backbone',
      category: 'noc_soc',
      vendor: 'Multi-Vendor Enterprise',
      sourcetype: 'cisco:ios',
      default_index: 'idx_network_ops',
      title: 'MV-001: 5-Tier Backbone Multi-Vendor Event Cross-Correlation',
      spl: 'index=* sourcetype IN ("cisco:ios", "pan:traffic", "juniper:junos", "arista:eos")\n| stats count, latest(_time) as last_seen by sourcetype, host\n| sort -count',
      description: 'Cross-correlates multi-vendor syslog and flow events across core, distribution, and edge tiers.'
    },
    {
      id: 'noc-mv002-roce-ai',
      category: 'noc_soc',
      vendor: 'AI DC Fabric',
      sourcetype: 'arista:eos:telemetry',
      default_index: 'idx_network_ops',
      title: 'MV-002: RoCE v2 AI Fabric Congestion Spikes',
      spl: 'index=* sourcetype IN ("arista:eos:telemetry", "arista:eos", "cisco:dc:nexus9k")\n| stats count, latest(_time) as last_seen by host, sourcetype\n| sort -count',
      description: 'Tracks telemetry and packet flow alarms across GPU compute clusters during intensive training workloads.'
    },
    {
      id: 'noc-mv006-bgp-flap',
      category: 'noc_soc',
      vendor: 'Core Routing',
      sourcetype: 'juniper:junos',
      default_index: 'idx_network_ops',
      title: 'MV-006: Core BGP Peering Instability & Convergence',
      spl: 'index=* sourcetype IN ("juniper:junos", "cisco:ios") "BGP"\n| stats count, latest(_time) as last_seen by host, sourcetype\n| sort -count',
      description: 'Monitors peering flushes, hold timer expirations, and BGP route flap dampening across carriers.'
    },
    {
      id: 'noc-mv008-sdwan-brownout',
      category: 'noc_soc',
      vendor: 'SD-WAN Edge',
      sourcetype: 'cisco:sdwan:linkhealth',
      default_index: 'idx_network_ops',
      title: 'MV-008: SD-WAN Dynamic SLA Failover & Path Steering',
      spl: 'index=* sourcetype IN ("cisco:sdwan:linkhealth", "fortinet:sdwan:health")\n| stats count by host, sourcetype\n| sort -count',
      description: 'Validates automated BFD SLA steering away from degraded public broadband underlays to MPLS backbones.'
    },
    {
      id: 'noc-mv014-firewall-capacity',
      category: 'noc_soc',
      vendor: 'Edge Security',
      sourcetype: 'pan:traffic',
      default_index: 'idx_security_fw',
      title: 'MV-014: Next-Gen Firewall Capacity & Session Saturation',
      spl: 'index=* sourcetype IN ("pan:traffic", "fortinet:fortigate:traffic", "checkpoint:cef")\n| stats count by sourcetype, action\n| sort -count',
      description: 'Surfaces edge cluster session table saturation, connection limits, and hardware offload degradation.'
    },
    {
      id: 'noc-mv016-crossdomain-slowness',
      category: 'noc_soc',
      vendor: 'Cross-Domain NOC',
      sourcetype: 'cisco:sdwan:dpi',
      default_index: 'idx_network_ops',
      title: 'MV-016: Cross-Domain User Application Slowness Triage',
      spl: 'index=* sourcetype IN ("cisco:sdwan:dpi", "f5:bigip:traffic", "pan:traffic")\n| stats count by sourcetype\n| sort -count',
      description: 'Pinpoints whether user experience degradation stems from transport WAN latency, ADC load, or security inspection.'
    }
  ];

  var currentResults = { columns: [], rows: [], rawEvents: [] };
  var activeQueryObj = null;

  // --- Render Query Cards in Left Sidebar ---
  function renderQueryList() {
    var category = $('#spl-category-select').val();
    var filter = ($('#spl-search-filter').val() || '').toLowerCase().trim();
    var container = $('#spl-query-list');
    container.empty();

    var filtered = PRE_CANNED_QUERIES.filter(function(q) {
      var catMatch = (category === 'all' || q.category === category);
      var textMatch = !filter ||
        q.title.toLowerCase().indexOf(filter) !== -1 ||
        q.spl.toLowerCase().indexOf(filter) !== -1 ||
        q.vendor.toLowerCase().indexOf(filter) !== -1 ||
        q.description.toLowerCase().indexOf(filter) !== -1;
      return catMatch && textMatch;
    });

    $('#query-count-badge').text(filtered.length + ' Queries');

    if (filtered.length === 0) {
      container.append('<div style="color: #64748b; font-size: 11px; text-align: center; padding: 20px;">No queries match your criteria.</div>');
      return;
    }

    filtered.forEach(function(q) {
      var isActive = activeQueryObj && activeQueryObj.id === q.id;
      var card = $(
        '<div class="spl-query-card" data-id="' + q.id + '" style="' +
          'padding: 10px 12px; border-radius: 6px; cursor: pointer; transition: all 0.15s ease;' +
          'background: ' + (isActive ? '#0284c7' : '#1e293b') + ';' +
          'border: 1px solid ' + (isActive ? '#38bdf8' : '#334155') + ';' +
          'box-shadow: ' + (isActive ? '0 0 8px rgba(56, 189, 248, 0.3)' : 'none') + ';' +
        '">' +
          '<div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 4px;">' +
            '<span style="color: ' + (isActive ? '#ffffff' : '#f8fafc') + '; font-size: 12px; font-weight: 600; line-height: 1.3;">' +
              q.title +
            '</span>' +
          '</div>' +
          '<div style="display: flex; align-items: center; gap: 6px; font-size: 10px; margin-bottom: 4px;">' +
            '<span style="color: ' + (isActive ? '#e0f2fe' : '#38bdf8') + '; font-weight: 600;">' + q.vendor + '</span>' +
            '<span style="color: #64748b;">•</span>' +
            '<span style="color: ' + (isActive ? '#bae6fd' : '#94a3b8') + '; font-family: monospace;">' + (q.default_index || '*') + '</span>' +
          '</div>' +
          '<div style="color: ' + (isActive ? '#f0f9ff' : '#94a3b8') + '; font-size: 11px; line-height: 1.3; overflow: hidden; text-overflow: ellipsis; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;">' +
            q.description +
          '</div>' +
        '</div>'
      );
      container.append(card);
    });
  }

  // --- Select Query from Catalog ---
  function selectQuery(id) {
    var found = PRE_CANNED_QUERIES.find(function(q) { return q.id === id; });
    if (!found) return;

    activeQueryObj = found;
    $('#spl-editor-input').val(found.spl);
    if (found.default_index) {
      $('#spl-target-index').val(found.default_index);
    }

    renderQueryList();
    currentResults = { columns: [], rows: [], rawEvents: [], emptyReason: 'ready_to_run' };
    $('#spl-status-pill').text('READY TO RUN').css({ 'background': '#1e293b', 'color': '#38bdf8' });
    $('#stat-duration').text('0 ms');
    $('#stat-scanned').text('0');
    $('#stat-matched').text('0');
    renderActiveView();
  }

  // --- Prettify SPL ---
  function prettifySPL() {
    var raw = $('#spl-editor-input').val();
    if (!raw) return;
    var lines = raw.split('|').map(function(seg) { return seg.trim(); }).filter(Boolean);
    if (lines.length > 1) {
      var pretty = lines[0] + '\n| ' + lines.slice(1).join('\n| ');
      $('#spl-editor-input').val(pretty);
    }
  }

  // --- Execute Query ---
  function executeQuery() {
    var query = $('#spl-editor-input').val().trim();
    if (!query) {
      $('#spl-editor-input').focus();
      return;
    }

    var mode = $('#spl-exec-mode').val();
    var statusPill = $('#spl-status-pill');
    statusPill.text('RUNNING...').css({ 'background': '#854d0e', 'color': '#fef08a' });

    var startTime = performance.now();

    if (mode === 'splunkd') {
      executeSplunkdSearch(query, startTime);
    } else {
      executeInstantSPL(query, startTime);
    }
  }

  // --- Get CSRF Token Helper ---
  function getCsrfToken() {
    if (window.Splunk && window.Splunk.util && typeof window.Splunk.util.getConfigValue === 'function') {
      var fk = window.Splunk.util.getConfigValue('FORM_KEY');
      if (fk) return fk;
    }
    var m = document.cookie.match(/(?:^|;\s*)(?:splunkweb_csrf_token_[0-9]+|splunkweb_csrf_token)=([^;]*)/);
    return (m && m[1]) ? decodeURIComponent(m[1]) : '';
  }

  // --- Splunkd REST API Search Execution ---
  function executeSplunkdSearch(query, startTime) {
    // If query does not start with | or search, prepend search
    var searchStr = query;
    if (!query.startsWith('|') && !query.startsWith('search ')) {
      searchStr = 'search ' + query;
    }

    var earliest = $('#spl-time-range').val();
    if (earliest === 'all') earliest = '0';

    var exportUrl = '/splunkd/__raw/services/search/jobs/export?output_mode=json';
    var csrfToken = getCsrfToken();

    $.ajax({
      url: exportUrl,
      type: 'POST',
      headers: {
        'X-Splunk-Form-Key': csrfToken,
        'X-Requested-With': 'XMLHttpRequest'
      },
      data: {
        search: searchStr,
        earliest_time: earliest,
        latest_time: 'now',
        preview: 'false'
      },
      timeout: 20000
    })
    .done(function(rawResp) {
      var durationMs = Math.round(performance.now() - startTime);
      var lines = typeof rawResp === 'string' ? rawResp.split('\n').filter(Boolean) : [];
      var events = [];
      lines.forEach(function(l) {
        try {
          var parsed = JSON.parse(l);
          if (parsed && parsed.result) events.push(parsed.result);
        } catch(e) {}
      });

      if (events.length === 0) {
        // Honest Empty State - Do NOT return fake rows!
        currentResults = { columns: [], rows: [], rawEvents: [], emptyReason: 'splunk_no_results' };
        $('#stat-duration').text(durationMs + ' ms');
        $('#stat-scanned').text('0');
        $('#stat-matched').text('0');
        $('#spl-status-pill').text('0 RESULTS (SPLUNKD)').css({ 'background': '#334155', 'color': '#94a3b8' });
        renderActiveView();
        return;
      }

      var colsSet = {};
      events.forEach(function(ev) {
        Object.keys(ev).forEach(function(k) {
          if (!k.startsWith('_') || k === '_time' || k === '_raw') {
            colsSet[k] = true;
          }
        });
      });
      var columns = Object.keys(colsSet);
      var rows = events.map(function(ev) {
        return columns.map(function(c) { return ev[c] !== undefined ? String(ev[c]) : ''; });
      });
      var rawEvents = events.map(function(ev) { return ev._raw || JSON.stringify(ev); });

      currentResults = {
        columns: columns,
        rows: rows,
        rawEvents: rawEvents,
        isLive: true
      };

      $('#stat-duration').text(durationMs + ' ms');
      $('#stat-scanned').text(events.length.toLocaleString());
      $('#stat-matched').text(events.length.toLocaleString());
      $('#spl-status-pill').text('LIVE (' + events.length + ' EVENTS)').css({ 'background': '#14532d', 'color': '#86efac' });

      renderActiveView();
    })
    .fail(function(xhr, textStatus, err) {
      var durationMs = Math.round(performance.now() - startTime);
      console.warn('Splunkd search returned status:', xhr.status, textStatus);
      currentResults = {
        columns: [],
        rows: [],
        rawEvents: [],
        emptyReason: 'splunk_error',
        errorMsg: 'Splunkd Search Error (' + (xhr.status || textStatus) + '): ' + (xhr.responseText ? xhr.responseText.slice(0, 150) : err)
      };
      $('#stat-duration').text(durationMs + ' ms');
      $('#spl-status-pill').text('SEARCH FAILED').css({ 'background': '#7f1d1d', 'color': '#fca5a5' });
      renderActiveView();
    });
  }

  // --- Quick Telemetry Blaster from Playground ---
  function blastSampleForQuery() {
    var st = activeQueryObj ? activeQueryObj.sourcetype : 'cisco:ios';
    var idx = activeQueryObj ? (activeQueryObj.default_index || 'idx_network_ops') : 'idx_network_ops';

    var btn = $('#btn-quick-blast');
    btn.prop('disabled', true).text('⏳ Ingesting real telemetry to ' + idx + '...');

    var localeMatch = window.location.pathname.match(/^\/([a-zA-Z]{2}-[a-zA-Z]{2})\//);
    var locale = localeMatch ? localeMatch[1] : 'en-US';
    var endpoint = '/' + locale + '/splunkd/__raw/services/datablaster/execute';

    $.ajax({
      url: endpoint,
      type: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Splunk-Form-Key': getCsrfToken()
      },
      data: JSON.stringify({
        action: 'blast_hec',
        sourcetype: st,
        index: idx,
        volume: 25
      }),
      timeout: 15000
    })
    .done(function(resp) {
      btn.text('✔ Ingested! Re-running search...').css('background', '#16a34a');
      setTimeout(function() {
        executeQuery();
      }, 1500);
    })
    .fail(function(xhr) {
      btn.text('✖ Ingestion Failed').css('background', '#dc2626');
      setTimeout(function() {
        btn.prop('disabled', false).text('⚡ Retry Telemetry Ingestion').css('background', '#0284c7');
      }, 2500);
    });
  }

  // --- Render Views ---
  function renderActiveView() {
    var activeTab = $('.spl-view-tab.active-view-tab').data('view') || 'table';
    $('#spl-view-table-container').toggle(activeTab === 'table');
    $('#spl-view-raw-container').toggle(activeTab === 'raw');
    $('#spl-view-chart-container').toggle(activeTab === 'chart');

    if (activeTab === 'table') {
      renderTable();
    } else if (activeTab === 'raw') {
      renderRaw();
    } else if (activeTab === 'chart') {
      renderChart();
    }
  }

  function renderTable() {
    var container = $('#spl-results-table');
    container.empty();

    var filter = ($('#spl-results-filter').val() || '').toLowerCase().trim();
    var cols = currentResults.columns;
    var rows = currentResults.rows;


    // Empty state handling
    if (!cols || cols.length === 0 || !rows || rows.length === 0) {
      if (currentResults.emptyReason === 'ready_to_run') {
        var queryTitle = activeQueryObj ? activeQueryObj.title : 'Selected Query';
        var queryDesc = activeQueryObj ? activeQueryObj.description : '';
        var readyHtml =
          '<div style="padding: 40px 20px; text-align: center; color: #94a3b8;">' +
            '<div style="font-size: 32px; margin-bottom: 12px;">🔍</div>' +
            '<div style="font-size: 15px; font-weight: 700; color: #f8fafc; margin-bottom: 8px;">' +
              queryTitle +
            '</div>' +
            '<div style="font-size: 12px; max-width: 580px; margin: 0 auto 18px auto; line-height: 1.5; color: #94a3b8;">' +
              queryDesc + '<br/><span style="color: #38bdf8; display: block; margin-top: 8px;">Click <b>"Execute Query"</b> or press <b>Ctrl+Enter</b> to run this search against live Splunk Enterprise.</span>' +
            '</div>' +
            '<button type="button" onclick="document.getElementById(\'btn-run-spl\').click()" style="background: #16a34a; color: #ffffff; border: none; padding: 10px 22px; border-radius: 6px; font-size: 13px; font-weight: 700; cursor: pointer; display: inline-flex; align-items: center; gap: 8px; box-shadow: 0 2px 8px rgba(22, 163, 74, 0.4);">' +
              '<span>▶</span> Execute Query Against Splunk' +
            '</button>' +
          '</div>';

        container.append(
          '<thead><tr style="background: #1e293b; color: #94a3b8;"><th style="padding: 8px 12px;">Ready</th></tr></thead>' +
          '<tbody><tr><td style="padding: 0;">' + readyHtml + '</td></tr></tbody>'
        );
        return;
      }
      var st = activeQueryObj ? activeQueryObj.sourcetype : 'this vendor';
      var idx = activeQueryObj ? (activeQueryObj.default_index || 'main') : 'main';

      var emptyHtml =
        '<div style="padding: 40px 20px; text-align: center; color: #94a3b8;">' +
          '<div style="font-size: 32px; margin-bottom: 12px;">📡</div>' +
          '<div style="font-size: 15px; font-weight: 700; color: #f8fafc; margin-bottom: 8px;">' +
            (currentResults.emptyReason === 'splunk_error' ? 'Search Execution Failed' : 'No Matching Events Found in Splunk') +
          '</div>' +
          '<div style="font-size: 12px; max-width: 520px; margin: 0 auto 18px auto; line-height: 1.5; color: #94a3b8;">' +
            (currentResults.errorMsg ? currentResults.errorMsg :
              'Splunk executed the search but found 0 events matching this query in index <code>' + idx + '</code>. ' +
              'Telemetry for sourcetype <code>' + st + '</code> has not been indexed yet.') +
          '</div>' +
          '<div style="display: inline-flex; gap: 10px;">' +
            '<button type="button" id="btn-quick-blast" style="background: #0284c7; color: #ffffff; border: none; padding: 9px 18px; border-radius: 6px; font-size: 12px; font-weight: 700; cursor: pointer; display: inline-flex; align-items: center; gap: 6px; box-shadow: 0 2px 8px rgba(2, 132, 199, 0.4);">' +
              '<span>⚡</span> Blast ' + st + ' Telemetry to Splunk Now' +
            '</button>' +

          '</div>' +
        '</div>';

      container.append(
        '<thead><tr style="background: #1e293b; color: #94a3b8;"><th style="padding: 8px 12px;">Status</th></tr></thead>' +
        '<tbody><tr><td style="padding: 0;">' + emptyHtml + '</td></tr></tbody>'
      );
      return;
    }

    var thead = $('<thead><tr style="background: #1e293b; color: #94a3b8; border-bottom: 1px solid #334155; position: sticky; top: 0;"></tr></thead>');
    var htr = thead.find('tr');
    htr.append('<th style="padding: 8px 12px; width: 40px;">#</th>');
    cols.forEach(function(c) {
      htr.append('<th style="padding: 8px 12px; color: #cbd5e1; font-weight: 600;">' + c + '</th>');
    });
    container.append(thead);

    var tbody = $('<tbody></tbody>');
    var displayedCount = 0;

    rows.forEach(function(r, idx) {
      var rowStr = r.join(' ').toLowerCase();
      if (filter && rowStr.indexOf(filter) === -1) return;

      displayedCount++;
      var tr = $('<tr style="border-bottom: 1px solid #1e293b; transition: background 0.1s ease;"></tr>');
      tr.hover(
        function() { $(this).css('background', 'rgba(56, 189, 248, 0.06)'); },
        function() { $(this).css('background', 'transparent'); }
      );

      tr.append('<td style="padding: 6px 12px; color: #64748b; font-size: 11px;">' + displayedCount + '</td>');
      r.forEach(function(cell, cellIdx) {
        var cellText = String(cell);
        var cellColor = '#e2e8f0';
        var isNum = !isNaN(parseFloat(cellText)) && isFinite(cellText);

        if (cellText === 'VIOLATED' || cellText === 'critical' || cellText === 'DOWN' || cellText === 'deny' || cellText === 'blocked' || cellText === 'FRAUD' || cellText === 'DENIED' || cellText === 'FAILURE') {
          cellColor = '#f87171';
        } else if (cellText === 'NORMAL' || cellText === 'healthy' || cellText === 'Passed' || cellText === 'permitted' || cellText === 'SUCCESS') {
          cellColor = '#4ade80';
        } else if (cellText === 'DEGRADED' || cellText === 'warning' || cellText === 'alert') {
          cellColor = '#fbbf24';
        } else if (isNum) {
          cellColor = '#38bdf8';
        }

        tr.append('<td style="padding: 6px 12px; color: ' + cellColor + '; font-size: 11px;">' + cellText + '</td>');
      });
      tbody.append(tr);
    });

    container.append(tbody);
  }

  function renderRaw() {
    var container = $('#spl-view-raw-container');
    container.empty();

    var events = currentResults.rawEvents;
    if (!events || events.length === 0) {
      container.text('No raw events available for this query.');
      return;
    }

    var filter = ($('#spl-results-filter').val() || '').toLowerCase().trim();
    var filtered = events.filter(function(e) { return !filter || e.toLowerCase().indexOf(filter) !== -1; });

    var formatted = filtered.map(function(ev, idx) {
      return (idx + 1) + '  ' + ev;
    }).join('\n\n');

    container.text(formatted);
  }

  function renderChart() {
    var container = $('#spl-chart-bars');
    container.empty();

    var cols = currentResults.columns;
    var rows = currentResults.rows;

    if (!cols || cols.length === 0 || !rows || rows.length === 0) {
      container.append('<div style="color: #64748b; font-size: 11px; text-align: center; padding: 20px;">Chart requires at least one grouped dataset.</div>');
      return;
    }

    var labelColIdx = 0;
    var valColIdx = -1;

    for (var i = cols.length - 1; i >= 0; i--) {
      var sampleVal = rows[0][i];
      if (!isNaN(parseFloat(sampleVal)) && isFinite(sampleVal)) {
        valColIdx = i;
        break;
      }
    }

    if (valColIdx === -1) {
      valColIdx = cols.length - 1;
    }

    var metricName = cols[valColIdx];
    var maxVal = 1;
    rows.forEach(function(r) {
      var v = parseFloat(r[valColIdx]) || 1;
      if (v > maxVal) maxVal = v;
    });

    container.append(
      '<div style="font-size: 11px; color: #94a3b8; font-weight: 600; margin-bottom: 6px;">' +
      'Metric Distribution: <b style="color: #38bdf8;">' + metricName + '</b> by <b style="color: #cbd5e1;">' + cols[labelColIdx] + '</b>' +
      '</div>'
    );

    rows.slice(0, 10).forEach(function(r) {
      var label = r[labelColIdx] + (r[1] && labelColIdx !== 1 ? ' (' + r[1] + ')' : '');
      var rawVal = r[valColIdx];
      var numVal = parseFloat(rawVal) || 0;
      var pct = Math.min(100, Math.max(8, Math.round((numVal / maxVal) * 100)));

      var bar = $(
        '<div style="display: flex; flex-direction: column; gap: 3px;">' +
          '<div style="display: flex; justify-content: space-between; font-size: 11px; font-family: monospace;">' +
            '<span style="color: #cbd5e1; max-width: 400px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">' + label + '</span>' +
            '<span style="color: #38bdf8; font-weight: 700;">' + rawVal + '</span>' +
          '</div>' +
          '<div style="background: #1e293b; height: 16px; border-radius: 3px; overflow: hidden; width: 100%; border: 1px solid #334155;">' +
            '<div style="background: linear-gradient(90deg, #0284c7 0%, #38bdf8 100%); height: 100%; width: ' + pct + '%; border-radius: 2px; transition: width 0.3s ease;"></div>' +
          '</div>' +
        '</div>'
      );
      container.append(bar);
    });
  }

  // --- Export CSV ---
  function exportCSV() {
    var cols = currentResults.columns;
    var rows = currentResults.rows;
    if (!cols || cols.length === 0 || !rows || rows.length === 0) return;

    var csvContent = 'data:text/csv;charset=utf-8,' +
      cols.map(function(c) { return '"' + c + '"'; }).join(',') + '\n' +
      rows.map(function(r) {
        return r.map(function(cell) { return '"' + String(cell).replace(/"/g, '""') + '"'; }).join(',');
      }).join('\n');

    var encodedUri = encodeURI(csvContent);
    var link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', 'netspout_spl_results.csv');
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }

  // --- Open in Splunk Search ---
  function openInSplunkSearch() {
    var query = $('#spl-editor-input').val().trim();
    if (!query) return;

    var earliest = $('#spl-time-range').val();
    if (earliest === 'all') earliest = '0';

    var searchStr = query;
    if (!query.startsWith('|') && !query.startsWith('search ')) {
      searchStr = 'search ' + query;
    }

    var localeMatch = window.location.pathname.match(/^\/([a-zA-Z]{2}-[a-zA-Z]{2})\//);
    var locale = localeMatch ? localeMatch[1] : 'en-US';

    var searchUrl = '/' + locale + '/app/netspout/search?q=' + encodeURIComponent(searchStr) +
                    '&earliest=' + encodeURIComponent(earliest) + '&latest=now';
    window.open(searchUrl, '_blank');
  }

  // --- Event Bindings ---
  function initEvents() {
    $(document).on('change', '#spl-category-select', renderQueryList);
    $(document).on('input keyup', '#spl-search-filter', renderQueryList);

    $(document).on('click', '.spl-query-card', function() {
      var id = $(this).data('id');
      selectQuery(id);
    });

    $(document).on('click', '#btn-run-spl', executeQuery);
    $(document).on('click', '#btn-format-spl', prettifySPL);
    $(document).on('click', '#btn-quick-blast', blastSampleForQuery);

    $(document).on('click', '#btn-clear-spl', function() {
      $('#spl-editor-input').val('');
      currentResults = { columns: [], rows: [], rawEvents: [] };
      renderActiveView();
      $('#spl-status-pill').text('CLEARED').css({ 'background': '#1e293b', 'color': '#94a3b8' });
    });

    $(document).on('click', '#btn-copy-spl', function() {
      var val = $('#spl-editor-input').val();
      if (navigator.clipboard) {
        navigator.clipboard.writeText(val).then(function() {
          var btn = $('#btn-copy-spl');
          btn.text('✔ Copied!').css('color', '#4ade80');
          setTimeout(function() { btn.text('Copy SPL').css('color', '#cbd5e1'); }, 1500);
        });
      }
    });

    $(document).on('click', '#btn-open-splunk-search', openInSplunkSearch);

    $(document).on('click', '.spl-view-tab', function() {
      $('.spl-view-tab').removeClass('active-view-tab').css({ 'background': '#1e293b', 'color': '#cbd5e1', 'border': '1px solid #334155' });
      $(this).addClass('active-view-tab').css({ 'background': '#0284c7', 'color': '#ffffff', 'border': 'none' });
      renderActiveView();
    });

    $(document).on('input keyup', '#spl-results-filter', renderActiveView);
    $(document).on('click', '#btn-export-csv', exportCSV);

    $(document).on('keydown', '#spl-editor-input', function(e) {
      if ((e.ctrlKey || e.metaKey) && e.keyCode === 13) {
        e.preventDefault();
        executeQuery();
      }
    });
  }

  function loadDashboardQueries() {
    var localeMatch = window.location.pathname.match(/^\/([a-zA-Z]{2}-[a-zA-Z]{2})\//);
    var locale = localeMatch ? localeMatch[1] : 'en-US';
    var url = '/' + locale + '/static/app/netspout/dashboard_queries.json';
    fetch(url)
      .then(function(r) { return r.json(); })
      .then(function(data) {
        if (Array.isArray(data) && data.length > 0) {
          var cleaned = [];
          data.slice(0, 80).forEach(function(q) {
            var spl = (q.spl || '')
              .replace(/`cisco_catalyst_app_index`/g, 'index=*')
              .replace(/`cisco_sdwan_index`/g, 'index=*')
              .replace(/`cisco_duo_index`/g, 'index=*')
              .replace(/`cisco_intersight_index`/g, 'index=*')
              .replace(/`cisco_dc_index`/g, 'index=*')
              .replace(/\$cc_host\$/g, '*')
              .replace(/\$domain\$/g, '*')
              .replace(/\$severity\$/g, '*')
              .replace(/\$system_ip\$/g, '*')
              .replace(/\$local_color\$/g, '*')
              .replace(/\$site_id\$/g, '*')
              .replace(/\$vpn_id\$/g, '*');

            if (!PRE_CANNED_QUERIES.some(function(ex) { return ex.id === q.id; })) {
              cleaned.push({
                id: q.id,
                category: q.category || 'cisco',
                vendor: q.vendor || 'Cisco Systems',
                sourcetype: q.sourcetype || 'cisco:ios',
                default_index: q.default_index || 'idx_network_ops',
                title: q.title,
                spl: spl,
                description: q.description || 'Extracted from production Cisco dashboard'
              });
            }
          });
          if (cleaned.length > 0) {
            PRE_CANNED_QUERIES = PRE_CANNED_QUERIES.concat(cleaned);
            renderQueryList();
          }
        }
      })
      .catch(function() {});
  }

  function init() {
    initEvents();
    renderQueryList();
    loadDashboardQueries();
    if (PRE_CANNED_QUERIES.length > 0) {
      selectQuery(PRE_CANNED_QUERIES[0].id);
    }
  }

  function pollReady() {
    if (document.getElementById('spl-editor-input')) {
      init();
    } else {
      setTimeout(pollReady, 100);
    }
  }

  pollReady();
});
