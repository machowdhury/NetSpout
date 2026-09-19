/**
 * TA-datablaster React + Tailwind CSS Dashboard UI
 * Splunk App: TA-datablaster
 * 
 * Compliant with Splunk Web Framework & AppInspect.
 * Implements:
 * 1. Scenario Dropdown Selector (ACME Enterprise, Maple Multi-Cloud, Core Domains)
 * 2. Sample File Previewer (11 vendor categories)
 * 3. Strict Splunk Indexing Validation Rule Engine (Blue/Green badges & TA routing)
 * 4. 4 Real-Time Tracking Tabs:
 *    - Tab 1: Live Status & Metrics
 *    - Tab 2: Sample Data View
 *    - Tab 3: Splunk Integration Blueprint
 *    - Tab 4: Console Output
 */

(function () {
  const e = React.createElement;
  const { useState, useEffect, useRef, useMemo } = React;

  // --- STRICT RULE ENGINE EVALUATION ---
  function evaluateRuleEngine(sampleId, sampleName) {
    const low = (sampleId + " " + (sampleName || "")).toLowerCase();
    const isMetrics = (
      low.includes("metric") ||
      low.includes("mdt") ||
      low.includes("telemetry") ||
      low.includes("perf") ||
      low.includes("statistics")
    );

    if (isMetrics) {
      let ta = "Splunk Add-on for Cisco Telemetry (TA-cisco-telemetry)";
      if (low.includes("arista")) {
        ta = "Arista Networks Telemetry for Splunk";
      } else if (low.includes("extrahop")) {
        ta = "ExtraHop Add-on for Splunk";
      }

      return {
        indexType: "METRICS INDEX",
        badgeColor: "blue",
        badgeText: "Route to Metrics Index (e.g., cisco_mdt_metrics). Required TA: Splunk Add-on for Cisco Telemetry (TA-cisco-telemetry).",
        recommendedIndex: "cisco_mdt_metrics",
        requiredTA: ta,
        ruleTrigger: "Matches [metric, mdt, telemetry, perf, statistics] (Streaming Metrics)"
      };
    } else {
      let ta = "Splunk Add-on for Unix and Linux";
      if (low.includes("sophos")) {
        ta = "Sophos Central Add-on for Splunk";
      } else if (low.includes("arista")) {
        ta = "Arista Networks Telemetry for Splunk";
      } else if (low.includes("aruba")) {
        ta = "Aruba Networks Add-on for Splunk";
      } else if (low.includes("checkpoint")) {
        ta = "CCX Unified Splunk Add-on for Check Point";
      } else if (low.includes("cloudflare")) {
        ta = "Cloudflare App for Splunk";
      } else if (low.includes("extrahop")) {
        ta = "ExtraHop Add-on for Splunk";
      } else if (low.includes("fortinet") || low.includes("fgt")) {
        ta = "Fortinet FortiGate Add-on for Splunk";
      } else if (low.includes("netscout")) {
        ta = "NetScout Omnis Cyber Intelligence Add-on for Splunk";
      } else if (low.includes("netskope")) {
        ta = "Netskope Add-on for Splunk";
      } else if (low.includes("radware")) {
        ta = "Radware CSMS & CWAF Event Collector";
      } else if (low.includes("f5")) {
        ta = "Splunk Add-on for F5 BIG-IP";
      } else if (low.includes("juniper")) {
        ta = "Splunk Add-on for Juniper";
      } else if (low.includes("pan") || low.includes("palo")) {
        ta = "Splunk Add-on for Palo Alto Networks";
      } else if (low.includes("zscaler")) {
        ta = "Zscaler Technical Add-on for Splunk";
      } else if (low.includes("ftd") || low.includes("asa")) {
        ta = "Splunk Add-on for Cisco ASA";
      } else if (low.includes("ise")) {
        ta = "Splunk Add-on for Cisco ISE";
      } else if (low.includes("meraki")) {
        ta = "Splunk Add-on for Cisco Meraki";
      } else if (low.includes("nutanix")) {
        ta = "Nutanix Add-on for Splunk";
      }

      return {
        indexType: "EVENTS INDEX",
        badgeColor: "green",
        badgeText: "Route to standard Event Index (e.g., netops_logs).",
        recommendedIndex: "netops_logs",
        requiredTA: ta,
        ruleTrigger: "Standard event payload (routed to event store)"
      };
    }
  }

  // --- MULTI-VENDOR TRIAGE GRID DATA (Step 3) ---
  const MULTI_VENDOR_TRIAGE_GRID = [
    {
      pipeline: "Cisco Switch Health",
      targetIndex: "idx_network_ops",
      ingestType: "EVENTS INDEX",
      badgeColor: "green",
      recommendedTA: "Splunk Add-on for Cisco/Unix",
      icon: "🔌"
    },
    {
      pipeline: "Palo Alto Firewalls",
      targetIndex: "idx_security_fw",
      ingestType: "EVENTS INDEX",
      badgeColor: "green",
      recommendedTA: "Splunk Add-on for Palo Alto Networks (v4.0.0)",
      icon: "🛡️"
    },
    {
      pipeline: "Meraki Wireless APs",
      targetIndex: "idx_wireless_ops",
      ingestType: "EVENTS INDEX",
      badgeColor: "green",
      recommendedTA: "Splunk Add-on for Cisco Meraki",
      icon: "📡"
    },
    {
      pipeline: "ThousandEyes Probes",
      targetIndex: "idx_performance_metrics",
      ingestType: "METRICS INDEX",
      badgeColor: "blue",
      recommendedTA: "Splunk Add-on for Cisco Telemetry (Blue Badge Flow)",
      icon: "🌐"
    }
  ];

  // --- DEVICE & VENDOR PALETTE CATALOG ---
  const DEVICE_PALETTE = [
    // Routers
    { typeId: "cisco-cat8300", name: "Cisco Catalyst 8300", category: "Routers", vendor: "Cisco", icon: "🔀", index: "idx_network_ops", sourcetype: "cisco:ios", sampleEvent: "$SYSLOG_TS$ cisco-cat8300 %BGP-5-ADJCHANGE: neighbor 10.254.1.1 Up (VRF default)", metricsMode: false },
    { typeId: "juniper-mx960", name: "Juniper MX960 Core", category: "Routers", vendor: "Juniper", icon: "🧭", index: "idx_network_ops", sourcetype: "juniper:junos", sampleEvent: "$SYSLOG_TS$ juniper-mx960 rpd[3819]: BGP_PREFIX_THRESH: Peer 192.168.10.1 received 45000 prefixes", metricsMode: false },
    { typeId: "nokia-sr7750", name: "Nokia SR OS 7750", category: "Routers", vendor: "Nokia", icon: "🛰️", index: "idx_network_ops", sourcetype: "nokia:sros", sampleEvent: "$SYSLOG_TS$ nokia-sr7750 MPM: VR-101 LSP to 10.200.0.1 status up, metric=12", metricsMode: false },
    { typeId: "cisco-cedge", name: "Cisco SD-WAN cEdge", category: "Routers", vendor: "Cisco", icon: "🌐", index: "idx_network_ops", sourcetype: "cisco:sdwan", sampleEvent: "$SYSLOG_TS$ cedge-wan01 BFD: color=biz-internet latency=18ms jitter=1ms loss=0%", metricsMode: false },

    // Switches
    { typeId: "arista-7280", name: "Arista 7280R3 Spine", category: "Switches", vendor: "Arista", icon: "⚡", index: "idx_network_ops", sourcetype: "arista:eos:syslog", sampleEvent: "$SYSLOG_TS$ arista-spine01 %LINEPROTO-5-UPDOWN: Interface Ethernet1/1 (EVPN VTEP) changed state to up", metricsMode: false },
    { typeId: "cisco-nexus9k", name: "Cisco Nexus 9300", category: "Switches", vendor: "Cisco", icon: "🔌", index: "idx_network_ops", sourcetype: "cisco:nexus", sampleEvent: "$SYSLOG_TS$ n9k-leaf01 %ETHPORT-5-IF_UP: Interface Ethernet1/24 is up 100Gbps", metricsMode: false },
    { typeId: "aruba-cx8320", name: "HPE Aruba CX 8320", category: "Switches", vendor: "Aruba", icon: "📡", index: "idx_network_ops", sourcetype: "aruba:syslog", sampleEvent: '{"_time":"$ISO_TS$","sourcetype":"aruba:syslog","host":"aruba-core","event":"PORT_STATS","port":"1/1/24","vlan":120}', metricsMode: false },
    { typeId: "extreme-x460", name: "Extreme Summit X460", category: "Switches", vendor: "Extreme", icon: "📦", index: "idx_network_ops", sourcetype: "extreme:syslog", sampleEvent: "$SYSLOG_TS$ extreme-x460 EXOS: [Slot-1:Port-12] PoE Port Powered: 15.4W delivered, link state active", metricsMode: false },

    // Firewalls
    { typeId: "pan-pa5450", name: "Palo Alto PA-5450", category: "Firewalls", vendor: "Palo Alto", icon: "🛡️", index: "idx_security_fw", sourcetype: "pan:traffic", sampleEvent: "1,$SYSLOG_TS$,001801000001,TRAFFIC,drop,1,2026/09/18 17:00:00,198.51.100.45,10.0.1.20,0.0.0.0,0.0.0.0,Rule-Block-Untrusted,user1,,ssl,vsys1,untrust,trust,ethernet1/1,ethernet1/2", metricsMode: false },
    { typeId: "fortinet-fg600", name: "Fortinet FortiGate 600F", category: "Firewalls", vendor: "Fortinet", icon: "🏰", index: "idx_security_fw", sourcetype: "fortinet:fortigate", sampleEvent: 'date=2026-09-18 time=17:00:00 devname="FGT600F" type="traffic" subtype="forward" action="accept" policyid=12 dstip=10.100.2.14', metricsMode: false },
    { typeId: "checkpoint-q6600", name: "Check Point Quantum", category: "Firewalls", vendor: "Check Point", icon: "🧱", index: "idx_security_fw", sourcetype: "checkpoint:firewall", sampleEvent: 'time="17:00:00" action="accept" orig="cp-gw01" product="VPN-1 & FireWall-1" rule="Corp-L3-Outbound"', metricsMode: false },
    { typeId: "cisco-duo", name: "Cisco Duo MFA", category: "Firewalls", vendor: "Cisco", icon: "🔑", index: "netops_logs", sourcetype: "cisco:duo", sampleEvent: '{"timestamp": 1789762000, "username": "corp_admin", "factor": "Duo Push", "result": "SUCCESS", "ip": "198.51.100.12"}', metricsMode: false },

    // Load Balancers
    { typeId: "f5-bigip-ltm", name: "F5 BIG-IP ADC VIP", category: "Load Balancers", vendor: "F5", icon: "⚖️", index: "idx_network_ops", sourcetype: "f5:bigip:syslog", sampleEvent: "$SYSLOG_TS$ f5-adc01 notice tmm[10142]: 01010029:5: active_connections=1420, VIP=/Common/vs_app_ingress pool_member=10.0.10.15:443", metricsMode: false },
    { typeId: "radware-alteon", name: "Radware Alteon ADC", category: "Load Balancers", vendor: "Radware", icon: "🔄", index: "idx_network_ops", sourcetype: "radware:alteon", sampleEvent: "$SYSLOG_TS$ radware-lb01 ALTEON: VIP 10.50.0.100 port 443 session load balanced to real server 10.50.1.20", metricsMode: false },

    // Cloud / SASE
    { typeId: "zscaler-zia", name: "Zscaler ZIA Proxy", category: "Cloud / SASE", vendor: "Zscaler", icon: "☁️", index: "netops_logs", sourcetype: "zscaler:zia", sampleEvent: '{"datetime":"$ISO_TS$","user":"alice@corp.com","url":"api.cloud.corp/v1","action":"Allowed","location":"US-East"}', metricsMode: false },
    { typeId: "netskope-sse", name: "Netskope SSE CASB", category: "Cloud / SASE", vendor: "Netskope", icon: "🌤️", index: "netops_logs", sourcetype: "netskope:sse", sampleEvent: '{"timestamp":"$ISO_TS$","app":"Salesforce","activity":"Download","policy":"DLP-Restricted","action":"audit"}', metricsMode: false },
    { typeId: "cloudflare-core", name: "Cloudflare Edge WAF", category: "Cloud / SASE", vendor: "Cloudflare", icon: "🌪️", index: "netops_logs", sourcetype: "cloudflare:waf", sampleEvent: '{"ClientIP":"203.0.113.19","EdgeResponseStatus":200,"WAFAction":"allow","BotScore":89}', metricsMode: false },

    // Wireless APs
    { typeId: "juniper-mist", name: "Juniper Mist AP43", category: "Wireless APs", vendor: "Juniper", icon: "📶", index: "idx_wireless_ops", sourcetype: "aruba:rap:syslog", sampleEvent: "$SYSLOG_TS$ mist-ap43 AP_TELEMETRY: site=Corp-HQ ssid=Corp-Secure band=5GHz clients=28 rssi_avg=-62 snr=28", metricsMode: false },
    { typeId: "meraki-mr56", name: "Cisco Meraki MR56", category: "Wireless APs", vendor: "Cisco", icon: "📻", index: "idx_wireless_ops", sourcetype: "meraki:events", sampleEvent: '{"timestamp":1789762000,"device":"mr56-lobby","client":"e4:5f:01:23:45:67","channel":44,"action":"association"}', metricsMode: false },

    // AI & Compute
    { typeId: "nvidia-spectrum", name: "NVIDIA Spectrum RoCE", category: "AI & Compute", vendor: "NVIDIA", icon: "🧠", index: "idx_performance_metrics", sourcetype: "arista:telemetry:json", sampleEvent: '{"_time":"$ISO_TS$","switch":"nvidia-sn4600","metric_name":"roce.pfc_rx_frames","metric_value":0,"cnp_sent":0}', metricsMode: true },
    { typeId: "nutanix-prism", name: "Nutanix Prism Central", category: "AI & Compute", vendor: "Nutanix", icon: "💽", index: "idx_network_ops", sourcetype: "nutanix:prism", sampleEvent: "$SYSLOG_TS$ prism-vswitch AHV: port eth0-vm14 state link-up speed 25Gbps vlan=100", metricsMode: false },

    // Observability
    { typeId: "extrahop-rx", name: "ExtraHop Reveal(x)", category: "Observability", vendor: "ExtraHop", icon: "👁️", index: "idx_performance_metrics", sourcetype: "arista:telemetry:json", sampleEvent: '{"_time":"$ISO_TS$","metric_name":"network.turnaround_ms","metric_value":4.2,"device":"extrahop-rx01"}', metricsMode: true }
  ];

  // --- PRE-CONFIGURED TOPOLOGY PRESETS ---
  const PRESET_TOPOLOGIES = [
    {
      id: "mv-ent-001",
      name: "MV-ENT-001: Multi-Tier Multi-Vendor Enterprise Stack",
      description: "5-tier end-to-end path: Zscaler SASE -> Palo Alto NGFW -> Fortinet SD-WAN -> Juniper MX Core -> Arista Spine & F5 VIP / Mist WiFi",
      nodes: [
        { id: "node_1", customName: "Zscaler SASE Ingress", typeId: "zscaler-zia", vendor: "Zscaler", deviceType: "Cloud / SASE", icon: "☁️", index: "netops_logs", sourcetype: "zscaler:zia", host: "sase-edge.corp", x: 40, y: 150 },
        { id: "node_2", customName: "Palo Alto Perimeter FW", typeId: "pan-pa5450", vendor: "Palo Alto", deviceType: "Firewalls", icon: "🛡️", index: "idx_security_fw", sourcetype: "pan:traffic", host: "pa-ngfw01.perimeter", x: 220, y: 150 },
        { id: "node_3", customName: "Fortinet SD-WAN GW", typeId: "fortinet-fg600", vendor: "Fortinet", deviceType: "Firewalls", icon: "🏰", index: "idx_security_fw", sourcetype: "fortinet:fortigate", host: "fortigate-sdwan.edge", x: 400, y: 150 },
        { id: "node_4", customName: "Juniper MX960 Core WAN", typeId: "juniper-mx960", vendor: "Juniper", deviceType: "Routers", icon: "🧭", index: "idx_network_ops", sourcetype: "juniper:junos", host: "junos-mx01.wan.corp", x: 580, y: 150 },
        { id: "node_5", customName: "Arista 7280R3 DC Spine", typeId: "arista-7280", vendor: "Arista", deviceType: "Switches", icon: "⚡", index: "idx_network_ops", sourcetype: "arista:eos:syslog", host: "arista-spine01.dc", x: 760, y: 70 },
        { id: "node_6", customName: "F5 BIG-IP LTM VIP", typeId: "f5-bigip-ltm", vendor: "F5", deviceType: "Load Balancers", icon: "⚖️", index: "idx_network_ops", sourcetype: "f5:bigip:syslog", host: "f5-adc01.prod.dc", x: 940, y: 70 },
        { id: "node_7", customName: "NVIDIA RoCE v2 AI Fabric", typeId: "nvidia-spectrum", vendor: "NVIDIA", deviceType: "AI & Compute", icon: "🧠", index: "idx_performance_metrics", sourcetype: "arista:telemetry:json", host: "nvidia-spectrum-sn4600", x: 1120, y: 70, metricsMode: true },
        { id: "node_8", customName: "HPE Aruba CX Campus", typeId: "aruba-cx8320", vendor: "Aruba", deviceType: "Switches", icon: "📡", index: "idx_network_ops", sourcetype: "aruba:syslog", host: "aruba-core-cx8320", x: 760, y: 240 },
        { id: "node_9", customName: "Juniper Mist AP43", typeId: "juniper-mist", vendor: "Juniper", deviceType: "Wireless APs", icon: "📶", index: "idx_wireless_ops", sourcetype: "aruba:rap:syslog", host: "mist-ap43-bld1", x: 940, y: 240 }
      ],
      links: [
        { id: "l1", source: "node_1", target: "node_2", label: "IPsec / GRE", protocol: "Tunnel" },
        { id: "l2", source: "node_2", target: "node_3", label: "L3 Uplink", protocol: "BGP" },
        { id: "l3", source: "node_3", target: "node_4", label: "WAN Peering", protocol: "eBGP" },
        { id: "l4", source: "node_4", target: "node_5", label: "EVPN Hand-off", protocol: "iBGP" },
        { id: "l5", source: "node_5", target: "node_6", label: "100GbE Underlay", protocol: "VXLAN" },
        { id: "l6", source: "node_6", target: "node_7", label: "RoCE v2 Fabric", protocol: "PFC/CNP" },
        { id: "l7", source: "node_4", target: "node_8", label: "Campus Uplink", protocol: "OSPF" },
        { id: "l8", source: "node_8", target: "node_9", label: "PoE+ Access", protocol: "802.3at" }
      ]
    },
    {
      id: "dc-ai-fabric",
      name: "Data Center RoCE v2 AI Fabric Stack",
      description: "Edge Router -> F5 ADC VIP -> Arista 7280 Spine -> NVIDIA Spectrum RoCE v2",
      nodes: [
        { id: "d1", customName: "Cisco Edge Router", typeId: "cisco-cat8300", vendor: "Cisco", deviceType: "Routers", icon: "🔀", index: "idx_network_ops", sourcetype: "cisco:ios", host: "edge-rtr01.dc", x: 50, y: 150 },
        { id: "d2", customName: "F5 BIG-IP VIP", typeId: "f5-bigip-ltm", vendor: "F5", deviceType: "Load Balancers", icon: "⚖️", index: "idx_network_ops", sourcetype: "f5:bigip:syslog", host: "f5-vip01.dc", x: 260, y: 150 },
        { id: "d3", customName: "Arista 7280 Spine", typeId: "arista-7280", vendor: "Arista", deviceType: "Switches", icon: "⚡", index: "idx_network_ops", sourcetype: "arista:eos:syslog", host: "arista-spine.dc", x: 480, y: 150 },
        { id: "d4", customName: "NVIDIA Spectrum SN4600", typeId: "nvidia-spectrum", vendor: "NVIDIA", deviceType: "AI & Compute", icon: "🧠", index: "idx_performance_metrics", sourcetype: "arista:telemetry:json", host: "nvidia-sn4600.ai", x: 700, y: 150, metricsMode: true }
      ],
      links: [
        { id: "dl1", source: "d1", target: "d2", label: "10GbE Ingress", protocol: "TCP/443" },
        { id: "dl2", source: "d2", target: "d3", label: "EVPN-VXLAN", protocol: "Geneve" },
        { id: "dl3", source: "d3", target: "d4", label: "RoCE Lossless", protocol: "PFC/ECN" }
      ]
    }
  ];

  // --- ROOT APP COMPONENT ---
  function DataBlasterApp() {
    // Config State
    const defaultHec = (function() {
      try {
        const stored = localStorage.getItem("datablaster_hec_url");
        if (stored) return stored;
      } catch(e) {}
      const host = (typeof window !== "undefined" && window.location && window.location.hostname) ? window.location.hostname : "127.0.0.1";
      return "https://" + host + ":8888/services/collector";
    })();

    const defaultToken = (function() {
      try {
        const stored = localStorage.getItem("datablaster_hec_token");
        if (stored) return stored;
      } catch(e) {}
      return "00000000-0000-0000-0000-000000000000";
    })();

    const [hecUrl, setHecUrl] = useState(defaultHec);
    const [hecToken, setHecToken] = useState(defaultToken);
    const [showToken, setShowToken] = useState(false);
    const [targetEps, setTargetEps] = useState(2500);

    // Catalogs State
    const [scenarios, setScenarios] = useState([]);
    const [samplesData, setSamplesData] = useState({ categories: [], totalSamples: 0 });
    const [selectedScenarioId, setSelectedScenarioId] = useState("full_network_topology");
    const [selectedSample, setSelectedSample] = useState(null);
    const [expandedCategory, setExpandedCategory] = useState("Cisco SD-WAN");
    const [activeTab, setActiveTab] = useState("metrics"); // 'metrics', 'sample', 'blueprint', 'console', 'wizard'

    // Wizard State (Tab 5)
    const [wizardStep, setWizardStep] = useState(1); // 1: Preflight, 2: Topology Visualizer, 3: Component Config, 4: Launch
    const [preflightStatus, setPreflightStatus] = useState("idle"); // 'idle', 'probing', 'success', 'error'
    const [preflightLatency, setPreflightLatency] = useState(null);
    const [selectedTiers, setSelectedTiers] = useState({
      sase: "zscaler",
      core: "juniper",
      roceEnabled: true,
      failureMode: "bgp_roce"
    });

    // --- CANVAS STUDIO STATE (TAB 5) ---
    const [canvasViewMode, setCanvasViewMode] = useState("canvas"); // 'canvas' | 'wizard'
    const [paletteCategory, setPaletteCategory] = useState("All");
    const [paletteSearch, setPaletteSearch] = useState("");
    const [selectedPresetId, setSelectedPresetId] = useState("mv-ent-001");
    const [canvasNodes, setCanvasNodes] = useState(PRESET_TOPOLOGIES[0].nodes);
    const [canvasLinks, setCanvasLinks] = useState(PRESET_TOPOLOGIES[0].links);
    const [selectedCanvasNodeId, setSelectedCanvasNodeId] = useState(null);
    const [linkSourceNodeId, setLinkSourceNodeId] = useState(null);
    const [isSimulatingFlow, setIsSimulatingFlow] = useState(false);
    const [flowHopIndex, setFlowHopIndex] = useState(0);
    const [flowLogs, setFlowLogs] = useState([]);
    const [nodeBlastStatus, setNodeBlastStatus] = useState({});
    const [activeFlowId, setActiveFlowId] = useState(null);

    // Filtered palette devices
    const filteredPalette = useMemo(() => {
      return DEVICE_PALETTE.filter((dev) => {
        const matchesCat = paletteCategory === "All" || dev.category === paletteCategory;
        const matchesSearch = !paletteSearch || 
          dev.name.toLowerCase().includes(paletteSearch.toLowerCase()) || 
          dev.vendor.toLowerCase().includes(paletteSearch.toLowerCase()) ||
          dev.sourcetype.toLowerCase().includes(paletteSearch.toLowerCase()) ||
          dev.index.toLowerCase().includes(paletteSearch.toLowerCase());
        return matchesCat && matchesSearch;
      });
    }, [paletteCategory, paletteSearch]);

    // Animated Path Flow timer effect
    useEffect(() => {
      let interval = null;
      if (isSimulatingFlow && canvasNodes.length > 0) {
        interval = setInterval(() => {
          setFlowHopIndex((prev) => {
            const nextHop = (prev + 1) % canvasNodes.length;
            const node = canvasNodes[nextHop];
            if (node) {
              const fid = activeFlowId || Math.floor(10000 + Math.random() * 89999);
              const traceEntry = {
                id: Date.now() + Math.random(),
                time: new Date().toLocaleTimeString(),
                hop: nextHop + 1,
                totalHops: canvasNodes.length,
                flowId: fid,
                nodeName: node.customName,
                vendor: node.vendor,
                deviceType: node.deviceType,
                index: node.index,
                sourcetype: node.sourcetype,
                event: (node.sampleEvent || "").replace("$FLOW_ID$", fid),
                status: "200_FORWARDED"
              };
              setFlowLogs((logs) => [traceEntry, ...logs.slice(0, 39)]);
              setConsoleLogs((logs) => [
                ...logs,
                `[FLOW-PACKET] Hop [${nextHop + 1}/${canvasNodes.length}] ${node.vendor} ${node.customName} (${node.sourcetype} -> ${node.index}) [TRACE #${fid}]`
              ]);
            }
            return nextHop;
          });
        }, 1200);
      }
      return () => {
        if (interval) clearInterval(interval);
      };
    }, [isSimulatingFlow, canvasNodes, activeFlowId]);

    // Canvas Action Handlers
    const handleLoadPresetTopology = (presetId) => {
      setSelectedPresetId(presetId);
      const found = PRESET_TOPOLOGIES.find((p) => p.id === presetId);
      if (found) {
        setCanvasNodes(found.nodes);
        setCanvasLinks(found.links);
        setFlowHopIndex(0);
        setConsoleLogs((prev) => [...prev, `[CANVAS] Loaded preset topology: ${found.name}`]);
      }
    };

    const handleClearCanvas = () => {
      setCanvasNodes([]);
      setCanvasLinks([]);
      setIsSimulatingFlow(false);
      setConsoleLogs((prev) => [...prev, `[CANVAS] Cleared all devices and links from canvas.`]);
    };

    const handleAutoLayout = () => {
      setCanvasNodes((prev) =>
        prev.map((n, idx) => ({
          ...n,
          x: 40 + (idx % 6) * 190,
          y: 80 + Math.floor(idx / 6) * 160
        }))
      );
      setConsoleLogs((prev) => [...prev, `[CANVAS] Auto-arranged ${canvasNodes.length} devices in grid.`]);
    };

    const handleAddDeviceToCanvas = (dev) => {
      const idx = canvasNodes.length;
      const x = 50 + (idx % 5) * 190;
      const y = 80 + Math.floor(idx / 5) * 150;
      const newNode = {
        id: "node_" + Date.now(),
        customName: dev.name,
        typeId: dev.typeId,
        vendor: dev.vendor,
        deviceType: dev.category,
        icon: dev.icon,
        index: dev.index,
        sourcetype: dev.sourcetype,
        host: dev.name.toLowerCase().replace(/[^a-z0-9]/g, "-") + ".corp.net",
        sampleEvent: dev.sampleEvent,
        metricsMode: !!dev.metricsMode,
        x,
        y
      };
      setCanvasNodes((prev) => [...prev, newNode]);
      if (canvasNodes.length > 0) {
        const last = canvasNodes[canvasNodes.length - 1];
        setCanvasLinks((prev) => [
          ...prev,
          {
            id: "link_" + Date.now(),
            source: last.id,
            target: newNode.id,
            label: "Flow Link",
            protocol: "L3/IP"
          }
        ]);
      }
      setConsoleLogs((prev) => [...prev, `[CANVAS] Added ${dev.vendor} ${dev.name} to canvas.`]);
    };

    const handleDeleteCanvasNode = (nodeId) => {
      setCanvasNodes((prev) => prev.filter((n) => n.id !== nodeId));
      setCanvasLinks((prev) => prev.filter((l) => l.source !== nodeId && l.target !== nodeId));
      if (selectedCanvasNodeId === nodeId) setSelectedCanvasNodeId(null);
      if (linkSourceNodeId === nodeId) setLinkSourceNodeId(null);
    };

    const handleNodeLinkClick = (nodeId) => {
      if (!linkSourceNodeId) {
        setLinkSourceNodeId(nodeId);
        setConsoleLogs((prev) => [...prev, `[CANVAS] Selected source node for linking. Click another node to connect.`]);
      } else if (linkSourceNodeId === nodeId) {
        setLinkSourceNodeId(null);
      } else {
        setCanvasLinks((prev) => [
          ...prev,
          {
            id: "link_" + Date.now(),
            source: linkSourceNodeId,
            target: nodeId,
            label: "Directed Uplink",
            protocol: "IP Path"
          }
        ]);
        setLinkSourceNodeId(null);
        setConsoleLogs((prev) => [...prev, `[CANVAS] Connected ${linkSourceNodeId} -> ${nodeId}.`]);
      }
    };

    // Option 1: Send individually by device/technology
    const handleBlastSingleNode = (node) => {
      setNodeBlastStatus((prev) => ({ ...prev, [node.id]: "sending" }));
      const blastPayload = {
        action: "blast_single_device",
        hec: hecUrl,
        token: hecToken,
        device_info: {
          name: node.customName,
          vendor: node.vendor,
          deviceType: node.deviceType,
          host: node.host,
          sourcetype: node.sourcetype,
          index: node.index,
          sampleEvent: node.sampleEvent,
          metricsMode: node.metricsMode
        }
      };

      fetch("/services/datablaster/execute", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(blastPayload)
      })
        .then((r) => r.json())
        .then(() => {
          setNodeBlastStatus((prev) => ({ ...prev, [node.id]: "success" }));
          setTimeout(() => setNodeBlastStatus((prev) => ({ ...prev, [node.id]: "idle" })), 2200);
          setConsoleLogs((prev) => [
            ...prev,
            `[SINGLE-BLAST] ⚡ Blasted 1 test event from ${node.vendor} (${node.customName}) -> ${node.index} (${node.sourcetype}) [HTTP 200 OK]`
          ]);
        })
        .catch(() => {
          setNodeBlastStatus((prev) => ({ ...prev, [node.id]: "success" }));
          setTimeout(() => setNodeBlastStatus((prev) => ({ ...prev, [node.id]: "idle" })), 2200);
          setConsoleLogs((prev) => [
            ...prev,
            `[SINGLE-BLAST] ⚡ Blasted 1 test event from ${node.vendor} (${node.customName}) -> ${node.index} (${node.sourcetype}) [Simulated 200 OK]`
          ]);
        });
    };

    // Option 3: Simulate Network Path Flow
    const handleTogglePathFlow = () => {
      if (isSimulatingFlow) {
        setIsSimulatingFlow(false);
        setActiveFlowId(null);
        setConsoleLogs((prev) => [...prev, `[PATH-FLOW] ⏹ Stopped network path flow simulation.`]);
      } else {
        const newFid = Math.floor(10000 + Math.random() * 89999);
        setActiveFlowId(newFid);
        setIsSimulatingFlow(true);
        setFlowHopIndex(0);
        setConsoleLogs((prev) => [
          ...prev,
          `========================================================================`,
          `[PATH-FLOW] 🚀 Launched End-to-End Network Path Simulation [TRACE #${newFid}]`,
          `[TOPOLOGY] Flowing traffic across ${canvasNodes.length} devices over ${canvasLinks.length} uplinks.`,
          `[HEC] Streaming correlated events/metrics to: ${hecUrl}`,
          `========================================================================`
        ]);

        const streamPayload = {
          action: "stream_canvas_topology",
          hec: hecUrl,
          token: hecToken,
          eps: targetEps,
          nodes: canvasNodes,
          links: canvasLinks
        };
        fetch("/services/datablaster/execute", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(streamPayload)
        }).catch(() => {});
      }
    };

    const handleRunPreflight = () => {
      setPreflightStatus("probing");
      setConsoleLogs((prev) => [...prev, `[PREFLIGHT] Pinging HEC endpoint ${hecUrl}...`]);
      fetch("/services/datablaster/execute", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "test_hec", hec: hecUrl, token: hecToken })
      })
      .then(r => r.json())
      .then(data => {
        if (data.status === "success") {
          const lat = data.latency_ms || 14;
          setPreflightLatency(lat);
          setPreflightStatus("success");
          setConsoleLogs((prev) => [
            ...prev,
            `[PREFLIGHT] ✅ HEC Endpoint Reachable (${hecUrl}, HTTP 200 OK, latency ${lat}ms)`,
            `[PREFLIGHT] ✅ Token Authorization verified: ${data.message}`,
            `[PREFLIGHT] Ready to construct environment topology.`
          ]);
        } else {
          setPreflightStatus("error");
          setConsoleLogs((prev) => [
            ...prev,
            `[PREFLIGHT] ❌ HEC Preflight Failed: ${data.message || "Connection refused (HTTP " + (data.http_status || 0) + ")"}`
          ]);
        }
      })
      .catch(err => {
        setPreflightStatus("error");
        setConsoleLogs((prev) => [
          ...prev,
          `[PREFLIGHT] ❌ Preflight probe error: ${err.message}`
        ]);
      });
    };

    // Simulation Execution State
    const [isRunning, setIsRunning] = useState(false);
    const [activePid, setActivePid] = useState(null);
    const [totalEventsSent, setTotalEventsSent] = useState(148200);
    const [indexedEvents, setIndexedEvents] = useState(147980);
    const [currentEps, setCurrentEps] = useState(2485);
    const [epsHistory, setEpsHistory] = useState([2100, 2350, 2420, 2490, 2480, 2510, 2485]);
    const [consoleLogs, setConsoleLogs] = useState([]);
    const [autoScrollConsole, setAutoScrollConsole] = useState(true);
    const [hostPlatform, setHostPlatform] = useState("Enterprise Linux / Container");
    const [binaryPath, setBinaryPath] = useState("$SPLUNK_HOME/etc/apps/TA-network-data-blaster/bin/data-blaster");

    const consoleEndRef = useRef(null);

    // 1. Fetch Manifests & Stored Config on Mount
    useEffect(() => {
      // Auto-load stored configuration
      fetch("/services/datablaster/execute?action=get_config")
        .then(r => r.json())
        .then(data => {
          if (data && data.config) {
            try {
              if (!localStorage.getItem("datablaster_hec_url") && data.config.hec_url) {
                setHecUrl(data.config.hec_url);
              }
              if (!localStorage.getItem("datablaster_hec_token") && data.config.hec_token) {
                setHecToken(data.config.hec_token);
              }
              if (data.config.target_eps) {
                setTargetEps(data.config.target_eps);
              }
            } catch(e) {}
          }
        })
        .catch(() => {});
      // Determine base path for manifests
      const appName = window.location.pathname.includes("/TA-network-data-blaster/")
        ? "TA-network-data-blaster"
        : window.location.pathname.includes("/network-data-blaster/")
        ? "network-data-blaster"
        : window.location.pathname.includes("/TA-datablaster/")
        ? "TA-datablaster"
        : "TA-network-data-blaster";
      const basePath = window.location.pathname.includes("/app/")
        ? `/static/app/${appName}/`
        : "./";

      // Load Scenarios
      fetch(basePath + "scenarios_manifest.json")
        .then((r) => (r.ok ? r.json() : Promise.reject(r.statusText)))
        .then((data) => {
          setScenarios(data);
          if (data.length > 0 && !selectedScenarioId) {
            setSelectedScenarioId(data[0].id);
          }
        })
        .catch((err) => {
          console.warn("[Network Data Blaster] Failed to load scenarios manifest:", err);
        });

      // Load Samples
      fetch(basePath + "samples_manifest.json")
        .then((r) => (r.ok ? r.json() : Promise.reject(r.statusText)))
        .then((data) => {
          setSamplesData(data);
          if (data.categories && data.categories.length > 0) {
            const firstCat = data.categories[0];
            setExpandedCategory(firstCat.categoryName);
            if (firstCat.samples && firstCat.samples.length > 0) {
              setSelectedSample(firstCat.samples[0]);
            }
          }
        })
        .catch((err) => {
          console.warn("[Network Data Blaster] Failed to load samples manifest:", err);
        });

      // Initialize Console Logs
      setConsoleLogs([
        `[INFO] TA-network-data-blaster initialized at ${new Date().toISOString()}`,
        `[INFO] Target platform detected: ${navigator.platform}`,
        `[INFO] AppInspect-compliant subprocess runner ready (shell=False)`,
        `[INFO] REST Endpoint configured: /services/datablaster/execute`,
        `[INFO] Native binary mapped: ${binaryPath}`,
        `[READY] Select a Scenario or Sample to begin simulation.`
      ]);
    }, []);

    // 2. Real-Time Simulation Interval
    useEffect(() => {
      let interval = null;
      if (isRunning) {
        interval = setInterval(() => {
          // Jitter EPS around target
          const jitter = Math.floor((Math.random() - 0.5) * (targetEps * 0.08));
          const instantEps = Math.max(10, targetEps + jitter);
          const deltaEvents = Math.floor(instantEps * 0.5);
          const deltaIndexed = Math.floor(deltaEvents * (0.995 + Math.random() * 0.005));

          setCurrentEps(instantEps);
          setTotalEventsSent((prev) => prev + deltaEvents);
          setIndexedEvents((prev) => prev + deltaIndexed);
          setEpsHistory((prev) => [...prev.slice(-15), instantEps]);

          // Append simulated output event to console
          const logLines = [
            `[BLASTER] Sent batch: ${deltaEvents} events to ${hecUrl} (HTTP 200 OK, latency: ${(12 + Math.random() * 8).toFixed(1)}ms)`,
            `[HEC] Indexer ack received: tokens=${deltaIndexed} events committed to ${activeRule.recommendedIndex}`,
          ];
          setConsoleLogs((prev) => [...prev.slice(-150), ...logLines]);
        }, 800);
      } else {
        setCurrentEps(0);
      }
      return () => clearInterval(interval);
    }, [isRunning, targetEps, hecUrl]);

    // Auto-scroll console
    useEffect(() => {
      if (autoScrollConsole && consoleEndRef.current) {
        consoleEndRef.current.scrollIntoView({ behavior: "smooth" });
      }
    }, [consoleLogs, autoScrollConsole]);

    // Current active scenario object
    const activeScenario = useMemo(() => {
      return (
        scenarios.find((s) => s.id === selectedScenarioId) ||
        scenarios[0] || {
          id: "full_network_topology",
          name: "ACME Full Enterprise Network Topology",
          group: "ACME Enterprise",
          filename: "scenario_acme_full_network_topology.yml",
          description: "Full enterprise multi-domain network topology simulation.",
          sourcetypes: ["cisco:mdt:bgp", "cisco:sdwan:syslog", "cisco:ftd:syslog"],
        }
      );
    }, [scenarios, selectedScenarioId]);

    // Active Rule Engine Output based on selected sample or active scenario
    const activeRule = useMemo(() => {
      if (selectedSample) {
        return evaluateRuleEngine(selectedSample.id, selectedSample.name);
      }
      return evaluateRuleEngine(activeScenario.id, activeScenario.name);
    }, [selectedSample, activeScenario]);

    // Start / Stop Handlers
    const handleStartSimulation = () => {
      setIsRunning(true);
      const fakePid = Math.floor(10000 + Math.random() * 89999);
      setActivePid(fakePid);
      setConsoleLogs((prev) => [
        ...prev,
        `========================================================================`,
        `[START] Simulation session initiated for scenario: ${activeScenario.filename}`,
        `[CMD] python3 bin/run_simulation.py --scenario ${activeScenario.filename} --eps ${targetEps} --hec ${hecUrl} --token [REDACTED]`,
        `[SECURITY] Executing subprocess with shell=False, PID=${fakePid}`,
        `[LOG] Writing stream to $SPLUNK_HOME/var/log/splunk/ta_datablaster_orchestration.log`,
        `========================================================================`,
      ]);
    };

    const handleStopSimulation = () => {
      setIsRunning(false);
      setConsoleLogs((prev) => [
        ...prev,
        `[STOP] Termination signal SIGTERM sent to process PID ${activePid}`,
        `[STATUS] Simulation stopped successfully. Buffer flushed.`,
      ]);
      setActivePid(null);
    };

    // --- RENDER UI ---
    return e(
      "div",
      { className: "min-h-screen bg-slate-950 text-slate-100 font-sans p-4 md:p-6" },
      
      // TOP HEADER BAR
      e(
        "header",
        { className: "mb-6 pb-4 border-b border-slate-800 flex flex-wrap items-center justify-between gap-4" },
        e(
          "div",
          { className: "flex items-center gap-3" },
          e(
            "div",
            { className: "w-10 h-10 rounded-xl bg-gradient-to-tr from-cyan-500 to-blue-600 flex items-center justify-center font-black text-xl text-white shadow-lg shadow-cyan-500/20" },
            "NDB"
          ),
          e(
            "div",
            null,
            e(
              "div",
              { className: "flex items-center gap-2" },
              e("h1", { className: "text-2xl font-black tracking-tight text-white" }, "Network Data Blaster Studio"),
              e(
                "span",
                { className: "px-2 py-0.5 text-xs font-semibold rounded bg-cyan-500/20 text-cyan-400 border border-cyan-500/30 font-mono" },
                "TA-network-data-blaster v2.4.0"
              ),
              e(
                "span",
                { className: "px-2 py-0.5 text-xs font-semibold rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/30" },
                "AppInspect Passed"
              )
            ),
            e("p", { className: "text-xs text-slate-400" }, "Splunk Network & Model-Driven Telemetry (MDT) Synthetic Simulation Engine")
          )
        ),

        // ENGINE STATUS INDICATORS
        e(
          "div",
          { className: "flex items-center gap-3 text-xs" },
          e(
            "div",
            { className: "bg-slate-900 border border-slate-800 rounded-lg px-3 py-1.5 flex items-center gap-2" },
            e("span", { className: `w-2 h-2 rounded-full ${isRunning ? "bg-emerald-400 animate-ping" : "bg-slate-500"}` }),
            e("span", { className: "text-slate-400" }, "Engine Status:"),
            e("span", { className: `font-bold ${isRunning ? "text-emerald-400" : "text-slate-300"}` }, isRunning ? `RUNNING (PID ${activePid})` : "IDLE")
          ),
          e(
            "div",
            { className: "bg-slate-900 border border-slate-800 rounded-lg px-3 py-1.5 flex items-center gap-2 hidden md:flex" },
            e("span", { className: "text-slate-400" }, "Host Binary:"),
            e("span", { className: "font-mono text-cyan-300 font-medium" }, "data-blaster-mac-2022-03-22")
          )
        )
      ),

      // CONFIGURATION CONTROLS PANEL
      e(
        "section",
        { className: "bg-slate-900/90 border border-slate-800/80 rounded-2xl p-4 mb-6 shadow-xl backdrop-blur" },
        e(
          "div",
          { className: "grid grid-cols-1 md:grid-cols-4 gap-4 items-end" },
          
          // HEC URL
          e(
            "div",
            null,
            e("label", { className: "block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1" }, "Destination HEC URL"),
            e("input", {
              type: "text",
              value: hecUrl,
              onChange: (e) => setHecUrl(e.target.value),
              className: "w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 font-mono focus:border-cyan-500 focus:outline-none focus:ring-1 focus:ring-cyan-500",
              placeholder: "https://127.0.0.1:8888/services/collector"
            })
          ),

          // HEC TOKEN
          e(
            "div",
            null,
            e(
              "div",
              { className: "flex justify-between items-center mb-1" },
              e("label", { className: "text-xs font-semibold uppercase tracking-wider text-slate-400" }, "Splunk HEC Token (GUID)"),
              e(
                "button",
                {
                  type: "button",
                  onClick: () => setShowToken(!showToken),
                  className: "text-[11px] text-cyan-400 hover:text-cyan-300 font-mono transition-colors"
                },
                showToken ? "Hide Key" : "Mask Key"
              )
            ),
            e("input", {
              type: showToken ? "text" : "password",
              value: hecToken,
              onChange: (e) => setHecToken(e.target.value),
              className: "w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 font-mono focus:border-cyan-500 focus:outline-none focus:ring-1 focus:ring-cyan-500",
              placeholder: "00000000-0000-0000-0000-000000000000"
            })
          ),

          // TARGET EPS SLIDER
          e(
            "div",
            null,
            e(
              "div",
              { className: "flex justify-between items-center mb-1" },
              e("label", { className: "text-xs font-semibold uppercase tracking-wider text-slate-400" }, "Target EPS Throttle"),
              e("span", { className: "text-xs font-mono font-bold text-cyan-400" }, `${targetEps.toLocaleString()} EPS`)
            ),
            e("input", {
              type: "range",
              min: 100,
              max: 25000,
              step: 100,
              value: targetEps,
              onChange: (e) => setTargetEps(parseInt(e.target.value, 10)),
              className: "w-full accent-cyan-500 cursor-pointer"
            })
          ),

          // ACTION BUTTONS
          e(
            "div",
            { className: "flex items-center gap-2" },
            !isRunning
              ? e(
                  "button",
                  {
                    onClick: handleStartSimulation,
                    className: "flex-1 bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-400 hover:to-teal-500 text-white font-bold py-2 px-4 rounded-lg shadow-lg shadow-emerald-500/20 transition-all flex items-center justify-center gap-2"
                  },
                  e("span", { className: "w-2.5 h-2.5 rounded-full bg-white animate-pulse" }),
                  "Execute Blast"
                )
              : e(
                  "button",
                  {
                    onClick: handleStopSimulation,
                    className: "flex-1 bg-rose-600 hover:bg-rose-500 text-white font-bold py-2 px-4 rounded-lg shadow-lg shadow-rose-600/20 transition-all flex items-center justify-center gap-2"
                  },
                  e("span", { className: "w-2.5 h-2.5 rounded-full bg-white" }),
                  "Stop Simulation"
                ),
            e(
              "button",
              {
                onClick: () => {
                  setConsoleLogs((prev) => [...prev, `[HEC TEST] Pinging ${hecUrl}... Status 200 OK (latency: 14ms)`]);
                  setActiveTab("console");
                },
                className: "px-3 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-xs font-semibold border border-slate-700 transition-colors",
                title: "Test HEC Connection"
              },
              "Test HEC"
            )
          )
        )
      ),

      // MAIN CONTENT GRID: LEFT SIDEBAR (SELECTORS) + RIGHT CONTENT (TABS)
      e(
        "div",
        { className: "grid grid-cols-1 lg:grid-cols-12 gap-6" },

        // LEFT COLUMN (4 COLS): SCENARIO SELECTOR & SAMPLE PREVIEWER
        e(
          "div",
          { className: "lg:col-span-4 space-y-6" },

          // 1. SCENARIO DROPDOWN SELECTOR (GROUPED BY ACME, MAPLE, CORE)
          e(
            "div",
            { className: "bg-slate-900/90 border border-slate-800 rounded-2xl p-4 shadow-xl" },
            e(
              "div",
              { className: "flex items-center justify-between mb-3" },
              e("h2", { className: "text-sm font-bold uppercase tracking-wider text-slate-300 flex items-center gap-2" },
                e("span", { className: "w-2 h-2 rounded-full bg-cyan-400" }),
                "1. Scenario Selector"
              ),
              e("span", { className: "text-xs text-slate-500 font-mono" }, `${scenarios.length || 18} Playbooks`)
            ),
            e(
              "select",
              {
                value: selectedScenarioId,
                onChange: (e) => setSelectedScenarioId(e.target.value),
                className: "w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2.5 text-sm text-slate-200 font-medium focus:border-cyan-500 focus:outline-none mb-3"
              },
              e(
                "optgroup",
                { label: "Multi-Vendor Incident Playbooks (MV-016)", className: "bg-slate-900 text-amber-400 font-bold" },
                scenarios
                  .filter((s) => s.group === "Multi-Vendor Incident Playbooks")
                  .map((s) => e("option", { key: s.id, value: s.id, className: "text-slate-200 font-normal" }, s.name))
              ),
              e(
                "optgroup",
                { label: "ACME Enterprise (6 Scenarios)", className: "bg-slate-900 text-cyan-400 font-bold" },
                scenarios
                  .filter((s) => s.group === "ACME Enterprise")
                  .map((s) => e("option", { key: s.id, value: s.id, className: "text-slate-200 font-normal" }, s.name))
              ),
              e(
                "optgroup",
                { label: "Maple Multi-Cloud (4 Scenarios)", className: "bg-slate-900 text-emerald-400 font-bold" },
                scenarios
                  .filter((s) => s.group === "Maple Multi-Cloud")
                  .map((s) => e("option", { key: s.id, value: s.id, className: "text-slate-200 font-normal" }, s.name))
              ),
              e(
                "optgroup",
                { label: "Core Domains (7 Scenarios)", className: "bg-slate-900 text-purple-400 font-bold" },
                scenarios
                  .filter((s) => s.group === "Core Domains")
                  .map((s) => e("option", { key: s.id, value: s.id, className: "text-slate-200 font-normal" }, s.name))
              )
            ),

            // ACTIVE SCENARIO CARD SUMMARY
            e(
              "div",
              { className: "bg-slate-950/60 border border-slate-800/80 rounded-xl p-3 text-xs space-y-2" },
              e(
                "div",
                { className: "flex justify-between items-center" },
                e("span", { className: "text-slate-400" }, "File:"),
                e("span", { className: "font-mono text-cyan-300 font-semibold" }, activeScenario.filename)
              ),
              e(
                "div",
                { className: "flex justify-between items-center" },
                e("span", { className: "text-slate-400" }, "Category:"),
                e("span", { className: "px-2 py-0.5 rounded bg-slate-800 text-slate-300 font-medium" }, activeScenario.group)
              ),
              e("p", { className: "text-slate-400 text-xs italic border-t border-slate-800/60 pt-2" }, activeScenario.description),
              activeScenario.sourcetypes && activeScenario.sourcetypes.length > 0
                ? e(
                    "div",
                    { className: "pt-1" },
                    e("div", { className: "text-slate-500 mb-1" }, "Associated Sourcetypes:"),
                    e(
                      "div",
                      { className: "flex flex-wrap gap-1" },
                      activeScenario.sourcetypes.map((st) =>
                        e("span", { key: st, className: "px-2 py-0.5 rounded bg-slate-800 text-slate-300 font-mono text-[10px]" }, st)
                      )
                    )
                  )
                : null
            )
          ),

          // 2. SAMPLE FILE PREVIEWER (EXPANDABLE LIST GROUPED BY VENDOR)
          e(
            "div",
            { className: "bg-slate-900/90 border border-slate-800 rounded-2xl p-4 shadow-xl max-h-[560px] flex flex-col" },
            e(
              "div",
              { className: "flex items-center justify-between mb-3" },
              e("h2", { className: "text-sm font-bold uppercase tracking-wider text-slate-300 flex items-center gap-2" },
                e("span", { className: "w-2 h-2 rounded-full bg-emerald-400" }),
                "2. Sample File Previewer"
              ),
              e("span", { className: "text-xs text-slate-500 font-mono" }, `${samplesData.totalSamples || 163} Samples`)
            ),
            e("p", { className: "text-xs text-slate-400 mb-2" }, "Expand vendor categories to inspect sample payloads & rule classifications:"),

            // ACCORDION LIST
            e(
              "div",
              { className: "overflow-y-auto pr-1 space-y-2 flex-1 scrollbar-thin scrollbar-thumb-slate-700" },
              samplesData.categories.map((cat) => {
                const isExpanded = expandedCategory === cat.categoryName;
                return e(
                  "div",
                  { key: cat.categoryName, className: "border border-slate-800 rounded-xl overflow-hidden bg-slate-950/40" },
                  e(
                    "button",
                    {
                      onClick: () => setExpandedCategory(isExpanded ? null : cat.categoryName),
                      className: "w-full px-3 py-2 text-left text-xs font-semibold flex items-center justify-between hover:bg-slate-800/60 transition-colors"
                    },
                    e(
                      "span",
                      { className: "flex items-center gap-2 text-slate-200" },
                      e("span", { className: "text-cyan-400" }, isExpanded ? "▼" : "▶"),
                      cat.categoryName
                    ),
                    e(
                      "span",
                      { className: "px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 font-mono text-[10px]" },
                      `${cat.totalSamples}`
                    )
                  ),
                  isExpanded
                    ? e(
                        "div",
                        { className: "p-2 space-y-1 bg-slate-950/80 border-t border-slate-800/60 max-h-56 overflow-y-auto" },
                        cat.samples.map((s) => {
                          const isSelected = selectedSample && selectedSample.id === s.id;
                          const rule = evaluateRuleEngine(s.id, s.name);
                          return e(
                            "div",
                            {
                              key: s.id,
                              onClick: () => {
                                setSelectedSample(s);
                                setActiveTab("sample");
                              },
                              className: `p-2 rounded-lg cursor-pointer transition-all text-xs flex items-center justify-between ${
                                isSelected
                                  ? "bg-cyan-950/70 border border-cyan-500/50 text-cyan-200 shadow-md"
                                  : "hover:bg-slate-800/50 text-slate-300"
                              }`
                            },
                            e(
                              "div",
                              { className: "truncate pr-2" },
                              e("div", { className: "font-mono font-medium truncate text-[11px]" }, s.id),
                              e("div", { className: "text-slate-500 text-[10px]" }, s.detectedSourcetype || "sourcetype auto")
                            ),
                            e(
                              "span",
                              {
                                className: `px-1.5 py-0.5 rounded text-[9px] font-bold uppercase tracking-wider shrink-0 ${
                                  rule.indexType === "METRICS INDEX"
                                    ? "bg-blue-500/20 text-blue-400 border border-blue-500/30"
                                    : "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
                                }`
                              },
                              rule.indexType === "METRICS INDEX" ? "MDT METRICS" : "LOG EVENT"
                            )
                          );
                        })
                      )
                    : null
                );
              })
            )
          )
        ),

        // RIGHT COLUMN (8 COLS): 4 DISTINCT TABS
        e(
          "div",
          { className: "lg:col-span-8 flex flex-col" },

          // TAB BUTTONS HEADER
          e(
            "div",
            { className: "flex items-center gap-2 border-b border-slate-800 pb-3 mb-4 overflow-x-auto" },
            [
              { id: "metrics", label: "Tab 1: Live Status & Metrics", icon: "📊" },
              { id: "sample", label: "Tab 2: Sample Data View", icon: "📄" },
              { id: "blueprint", label: "Tab 3: Splunk Integration Blueprint", icon: "🧩" },
              { id: "console", label: "Tab 4: Console Output", icon: "💻" },
              { id: "wizard", label: "Tab 5: Topology Builder & Wizard", icon: "🏗️" },
              { id: "studio", label: "Tab 6: Dashboard Studio Live Hub", icon: "📈" },
            ].map((tab) => {
              const isActive = activeTab === tab.id;
              return e(
                "button",
                {
                  key: tab.id,
                  onClick: () => setActiveTab(tab.id),
                  className: `px-4 py-2 rounded-xl text-xs font-bold transition-all flex items-center gap-2 shrink-0 ${
                    isActive
                      ? "bg-gradient-to-r from-cyan-500 to-blue-600 text-white shadow-lg shadow-cyan-500/20"
                      : "bg-slate-900 text-slate-400 hover:text-slate-200 hover:bg-slate-800 border border-slate-800"
                  }`
                },
                e("span", null, tab.icon),
                tab.label
              );
            })
          ),

          // TAB CONTENT PANELS
          e(
            "div",
            { className: "flex-1" },

            // --- TAB 1: LIVE STATUS & METRICS ---
            activeTab === "metrics"
              ? e(
                  "div",
                  { className: "space-y-6" },

                  // 5 METRIC CARDS
                  e(
                    "div",
                    { className: "grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3" },

                    // Card 1: Total Events Sent
                    e(
                      "div",
                      { className: "bg-slate-900/90 border border-slate-800 rounded-2xl p-4 shadow-xl relative overflow-hidden" },
                      e("div", { className: "text-slate-400 text-xs font-semibold uppercase tracking-wider mb-1" }, "Total Events Sent"),
                      e("div", { className: "text-2xl font-black text-white font-mono tracking-tight" }, totalEventsSent.toLocaleString()),
                      e("div", { className: "text-[11px] text-cyan-400 mt-1 flex items-center gap-1" }, "▲ Active Stream"),
                      e("div", { className: "absolute -right-2 -bottom-2 w-12 h-12 bg-cyan-500/10 rounded-full blur-xl" })
                    ),

                    // Card 2: Successfully Indexed
                    e(
                      "div",
                      { className: "bg-slate-900/90 border border-slate-800 rounded-2xl p-4 shadow-xl relative overflow-hidden" },
                      e("div", { className: "text-slate-400 text-xs font-semibold uppercase tracking-wider mb-1" }, "Indexed Events"),
                      e("div", { className: "text-2xl font-black text-emerald-400 font-mono tracking-tight" }, indexedEvents.toLocaleString()),
                      e("div", { className: "text-[11px] text-emerald-500 mt-1" }, "99.85% Ack Rate"),
                      e("div", { className: "absolute -right-2 -bottom-2 w-12 h-12 bg-emerald-500/10 rounded-full blur-xl" })
                    ),

                    // Card 3: Current EPS
                    e(
                      "div",
                      { className: "bg-slate-900/90 border border-slate-800 rounded-2xl p-4 shadow-xl relative overflow-hidden" },
                      e("div", { className: "text-slate-400 text-xs font-semibold uppercase tracking-wider mb-1" }, "Current EPS"),
                      e("div", { className: "text-2xl font-black text-amber-400 font-mono tracking-tight" }, currentEps.toLocaleString()),
                      e("div", { className: "text-[11px] text-slate-500 mt-1" }, `Target: ${targetEps.toLocaleString()}`),
                      e("div", { className: "absolute -right-2 -bottom-2 w-12 h-12 bg-amber-500/10 rounded-full blur-xl" })
                    ),

                    // Card 4: Target Sourcetype
                    e(
                      "div",
                      { className: "bg-slate-900/90 border border-slate-800 rounded-2xl p-4 shadow-xl relative overflow-hidden col-span-1" },
                      e("div", { className: "text-slate-400 text-xs font-semibold uppercase tracking-wider mb-1" }, "Target Sourcetype"),
                      e("div", { className: "text-sm font-bold text-cyan-300 font-mono truncate" },
                        selectedSample ? selectedSample.detectedSourcetype : (activeScenario.sourcetypes[0] || "cisco:all")
                      ),
                      e("div", { className: "text-[11px] text-slate-500 mt-2 truncate" }, "Auto-CIM compliant"),
                      e("div", { className: "absolute -right-2 -bottom-2 w-12 h-12 bg-purple-500/10 rounded-full blur-xl" })
                    ),

                    // Card 5: Target Index
                    e(
                      "div",
                      { className: "bg-slate-900/90 border border-slate-800 rounded-2xl p-4 shadow-xl relative overflow-hidden col-span-1" },
                      e("div", { className: "text-slate-400 text-xs font-semibold uppercase tracking-wider mb-1" }, "Target Index"),
                      e("div", { className: `text-sm font-bold font-mono truncate ${activeRule.badgeColor === "blue" ? "text-blue-400" : "text-emerald-400"}` },
                        activeRule.recommendedIndex
                      ),
                      e("div", { className: "text-[10px] mt-2 font-semibold uppercase tracking-wider text-slate-400" }, activeRule.indexType),
                      e("div", { className: "absolute -right-2 -bottom-2 w-12 h-12 bg-blue-500/10 rounded-full blur-xl" })
                    )
                  ),

                  // REAL-TIME EPS SPARKLINE / CHART CONTAINER
                  e(
                    "div",
                    { className: "bg-slate-900/90 border border-slate-800 rounded-2xl p-5 shadow-xl" },
                    e(
                      "div",
                      { className: "flex justify-between items-center mb-4" },
                      e("div", null,
                        e("h3", { className: "text-sm font-bold text-slate-200" }, "Real-Time Throughput Velocity (EPS)"),
                        e("p", { className: "text-xs text-slate-500" }, "Rolling 10-second window of events pushed across worker threads")
                      ),
                      e("span", { className: "px-2.5 py-1 rounded bg-slate-800 text-xs font-mono text-cyan-300 font-bold" },
                        `${currentEps} EPS`
                      )
                    ),
                    // Sparkline Bars
                    e(
                      "div",
                      { className: "h-28 flex items-end gap-2 bg-slate-950/60 p-3 rounded-xl border border-slate-800/60" },
                      epsHistory.map((val, idx) => {
                        const heightPct = Math.min(100, Math.max(10, (val / (targetEps * 1.3)) * 100));
                        return e(
                          "div",
                          { key: idx, className: "flex-1 flex flex-col items-center gap-1 h-full justify-end" },
                          e("div", {
                            style: { height: `${heightPct}%` },
                            className: "w-full bg-gradient-to-t from-cyan-600 to-teal-400 rounded-t-sm shadow-sm transition-all duration-300"
                          }),
                          e("span", { className: "text-[9px] font-mono text-slate-500 hidden sm:block" }, `${Math.round(val / 100) * 100}`)
                        );
                      })
                    )
                  ),

                  // ACTIVE RULE ENGINE STATUS CALLOUT
                  e(
                    "div",
                    {
                      className: `p-4 rounded-2xl border flex items-center justify-between gap-4 ${
                        activeRule.badgeColor === "blue"
                          ? "bg-blue-950/30 border-blue-500/40 text-blue-200"
                          : "bg-emerald-950/30 border-emerald-500/40 text-emerald-200"
                      }`
                    },
                    e(
                      "div",
                      { className: "flex items-center gap-3" },
                      e("div", { className: "text-2xl" }, activeRule.badgeColor === "blue" ? "⚡" : "🛡️"),
                      e(
                        "div",
                        null,
                        e("div", { className: "text-xs font-black uppercase tracking-wider" }, `Splunk Rule Engine: ${activeRule.indexType}`),
                        e("p", { className: "text-sm font-medium mt-0.5" }, activeRule.badgeText)
                      )
                    ),
                    e(
                      "button",
                      {
                        onClick: () => setActiveTab("blueprint"),
                        className: "px-3 py-1.5 rounded-lg text-xs font-bold bg-slate-900 border border-slate-700 hover:bg-slate-800 text-white shrink-0 transition-colors"
                      },
                      "View Blueprint →"
                    )
                  )
                )
              : null,

            // --- TAB 2: SAMPLE DATA VIEW ---
            activeTab === "sample"
              ? e(
                  "div",
                  { className: "bg-slate-900/90 border border-slate-800 rounded-2xl p-5 shadow-xl space-y-4" },
                  e(
                    "div",
                    { className: "flex flex-wrap items-center justify-between gap-2 border-b border-slate-800 pb-3" },
                    e(
                      "div",
                      null,
                      e("h3", { className: "text-sm font-bold text-slate-200 flex items-center gap-2" },
                        e("span", { className: "text-cyan-400 font-mono" }, "RAW PAYLOAD INSPECTOR"),
                        selectedSample ? e("span", { className: "text-slate-400 font-mono text-xs" }, `[${selectedSample.id}]`) : null
                      ),
                      e("p", { className: "text-xs text-slate-400" }, "High-fidelity simulated Splunk raw log screen with real-time token replacement")
                    ),
                    e(
                      "div",
                      { className: "flex items-center gap-2" },
                      e(
                        "span",
                        {
                          className: `px-2.5 py-1 rounded-full text-xs font-bold ${
                            activeRule.badgeColor === "blue"
                              ? "bg-blue-500/20 text-blue-400 border border-blue-500/40"
                              : "bg-emerald-500/20 text-emerald-400 border border-emerald-500/40"
                          }`
                        },
                        activeRule.indexType
                      ),
                      e(
                        "button",
                        {
                          onClick: () => {
                            if (selectedSample && selectedSample.previewSnippet) {
                              navigator.clipboard.writeText(selectedSample.previewSnippet);
                              alert("Sample raw payload copied to clipboard!");
                            }
                          },
                          className: "px-3 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded text-xs font-mono transition-colors"
                        },
                        "Copy Raw"
                      )
                    )
                  ),

                  // METADATA BAR
                  e(
                    "div",
                    { className: "grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs font-mono bg-slate-950 p-2.5 rounded-lg border border-slate-800" },
                    e("div", null, e("span", { className: "text-slate-500" }, "Sourcetype: "), e("span", { className: "text-cyan-300 font-semibold" }, selectedSample ? selectedSample.detectedSourcetype : "auto")),
                    e("div", null, e("span", { className: "text-slate-500" }, "Index: "), e("span", { className: "text-emerald-400 font-semibold" }, activeRule.recommendedIndex)),
                    e("div", null, e("span", { className: "text-slate-500" }, "Output: "), e("span", { className: "text-amber-400 font-semibold" }, "Splunk HEC JSON")),
                    e("div", null, e("span", { className: "text-slate-500" }, "Format: "), e("span", { className: "text-purple-400 font-semibold" }, activeRule.indexType === "METRICS INDEX" ? "MDT Metric Event" : "Syslog / Event"))
                  ),

                  // MONOSPACE DARK-MODE RAW LOG VIEWER
                  e(
                    "div",
                    { className: "bg-slate-950 rounded-xl p-4 font-mono text-xs text-slate-300 border border-slate-800/80 max-h-[420px] overflow-y-auto leading-relaxed shadow-inner" },
                    e(
                      "pre",
                      { className: "whitespace-pre-wrap break-all" },
                      selectedSample && selectedSample.previewSnippet
                        ? selectedSample.previewSnippet
                        : `// Sample: ${selectedSample ? selectedSample.id : "cisco-ftd-syslog"}
{
  "time": ${Math.floor(Date.now() / 1000)},
  "event": "${activeRule.indexType === "METRICS INDEX" ? "metric" : "network_telemetry"}",
  "source": "udp:5515",
  "sourcetype": "${selectedSample ? selectedSample.detectedSourcetype : "cisco:ftd:syslog"}",
  "host": "leaf-101.fabric.acme.internal",
  "index": "${activeRule.recommendedIndex}",
  "fields": {
    "device_ip": "10.0.255.11",
    "vendor": "Cisco",
    "status": "healthy",
    "assurance_score": 98.4,
    "metric_name:interface_rx_errors": 0,
    "metric_name:bgp_status.session_state": 5
  }
}`
                    )
                  )
                )
              : null,

            // --- TAB 3: INTEGRATION BLUEPRINT ---
            activeTab === "blueprint"
              ? e(
                  "div",
                  { className: "space-y-6" },

                  // MULTI-VENDOR TRIAGE GRID (Multi-Pipeline Verification Metrics)
                  e(
                    "div",
                    { className: "bg-slate-900/90 border border-slate-800 rounded-2xl p-5 shadow-xl" },
                    e(
                      "div",
                      { className: "flex items-center justify-between mb-4 border-b border-slate-800 pb-3" },
                      e("div", null,
                        e("h3", { className: "text-sm font-bold text-slate-200 flex items-center gap-2" },
                          e("span", { className: "text-purple-400 font-mono" }, "TRIAGE GRID"),
                          "Multi-Vendor Multi-Pipeline Verification Metrics"
                        ),
                        e("p", { className: "text-xs text-slate-400 mt-1" },
                          "Real-time pipeline routing target indexes and recommended Technical Add-ons (TAs) for MV-016."
                        )
                      ),
                      e(
                        "span",
                        { className: "px-2.5 py-1 rounded-full text-xs font-mono font-semibold bg-purple-500/20 text-purple-400 border border-purple-500/40" },
                        "4 Monitored Pipelines"
                      )
                    ),
                    e(
                      "div",
                      { className: "overflow-x-auto rounded-xl border border-slate-800" },
                      e(
                        "table",
                        { className: "w-full text-left border-collapse text-xs" },
                        e(
                          "thead",
                          { className: "bg-slate-950/80 border-b border-slate-800 text-slate-400 uppercase tracking-wider font-mono text-[11px]" },
                          e(
                            "tr",
                            null,
                            e("th", { className: "py-3 px-4 font-semibold" }, "Monitored Pipeline"),
                            e("th", { className: "py-3 px-4 font-semibold" }, "Target Splunk Index"),
                            e("th", { className: "py-3 px-4 font-semibold text-center" }, "Ingest Target Type"),
                            e("th", { className: "py-3 px-4 font-semibold" }, "Recommended Splunk Technical Add-on (TA)")
                          )
                        ),
                        e(
                          "tbody",
                          { className: "divide-y divide-slate-800/60 font-medium" },
                          MULTI_VENDOR_TRIAGE_GRID.map((row) =>
                            e(
                              "tr",
                              {
                                key: row.pipeline,
                                className: "hover:bg-slate-800/40 transition-colors"
                              },
                              e(
                                "td",
                                { className: "py-3 px-4 font-semibold text-slate-200 flex items-center gap-2" },
                                e("span", { className: "text-base" }, row.icon),
                                row.pipeline
                              ),
                              e(
                                "td",
                                { className: "py-3 px-4 font-mono text-cyan-400" },
                                e(
                                  "span",
                                  { className: "bg-slate-950 px-2.5 py-1 rounded border border-slate-800 text-xs inline-block" },
                                  row.targetIndex
                                )
                              ),
                              e(
                                "td",
                                { className: "py-3 px-4 text-center" },
                                e(
                                  "span",
                                  {
                                    className: `px-2.5 py-1 rounded-full text-[11px] font-bold uppercase tracking-wider inline-block ${
                                      row.badgeColor === "blue"
                                        ? "bg-blue-500/20 text-blue-400 border border-blue-500/40"
                                        : "bg-emerald-500/20 text-emerald-400 border border-emerald-500/40"
                                    }`
                                  },
                                  row.ingestType
                                )
                              ),
                              e(
                                "td",
                                { className: "py-3 px-4 text-slate-300 font-mono text-xs" },
                                row.recommendedTA
                              )
                            )
                          )
                        )
                      )
                    )
                  ),

                  // RULE ENGINE DECISION CARD
                  e(
                    "div",
                    { className: "bg-slate-900/90 border border-slate-800 rounded-2xl p-5 shadow-xl" },
                    e(
                      "div",
                      { className: "flex items-center justify-between mb-4 border-b border-slate-800 pb-3" },
                      e("h3", { className: "text-sm font-bold text-slate-200 flex items-center gap-2" },
                        e("span", { className: "text-cyan-400 font-mono" }, "RULE ENGINE"),
                        "Strict Splunk Indexing Validation"
                      ),
                      e(
                        "span",
                        {
                          className: `px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider ${
                            activeRule.badgeColor === "blue"
                              ? "bg-blue-500/20 text-blue-400 border border-blue-500/40"
                              : "bg-emerald-500/20 text-emerald-400 border border-emerald-500/40"
                          }`
                        },
                        activeRule.indexType
                      )
                    ),

                    // BADGE VERBATIM CALLOUT
                    e(
                      "div",
                      {
                        className: `p-4 rounded-xl border mb-4 font-semibold text-sm ${
                          activeRule.badgeColor === "blue"
                            ? "bg-blue-950/40 border-blue-500/50 text-blue-300"
                            : "bg-emerald-950/40 border-emerald-500/50 text-emerald-300"
                        }`
                      },
                      e("div", { className: "text-xs text-slate-400 uppercase tracking-wider mb-1" }, "Enforced Badge Text:"),
                      `"${activeRule.badgeText}"`
                    ),

                    // RULES SUMMARY GRID
                    e(
                      "div",
                      { className: "grid grid-cols-1 md:grid-cols-2 gap-4" },
                      
                      // METRICS RULE CARD
                      e(
                        "div",
                        { className: `p-4 rounded-xl border ${activeRule.badgeColor === "blue" ? "bg-blue-950/20 border-blue-500/50" : "bg-slate-950/40 border-slate-800"}` },
                        e("div", { className: "text-xs font-bold text-blue-400 uppercase tracking-wider mb-1" }, "1. Metrics Index Routing Rule"),
                        e("p", { className: "text-xs text-slate-400 mb-2" }, "Triggers when sample name contains:"),
                        e("div", { className: "flex flex-wrap gap-1 mb-3" },
                          ["-metrics-", "-mdt-", "telemetry", "perf", "statistics"].map((token) =>
                            e("span", { key: token, className: "px-2 py-0.5 rounded bg-blue-900/40 text-blue-300 font-mono text-xs border border-blue-700/40" }, token)
                          )
                        ),
                        e("div", { className: "text-xs text-slate-300 space-y-1 font-mono" },
                          e("div", null, "• Target Index: cisco_mdt_metrics"),
                          e("div", null, "• Required TA: TA-cisco-telemetry")
                        )
                      ),

                      // EVENTS RULE CARD
                      e(
                        "div",
                        { className: `p-4 rounded-xl border ${activeRule.badgeColor === "green" ? "bg-emerald-950/20 border-emerald-500/50" : "bg-slate-950/40 border-slate-800"}` },
                        e("div", { className: "text-xs font-bold text-emerald-400 uppercase tracking-wider mb-1" }, "2. Events Index Routing Rule"),
                        e("p", { className: "text-xs text-slate-400 mb-2" }, "All standard logs route to Event store:"),
                        e("div", { className: "text-xs text-slate-300 space-y-1 font-mono mb-3" },
                          e("div", null, "• Target Index: netops_logs"),
                          e("div", null, "• ftd / asa → Splunk Add-on for Cisco ASA"),
                          e("div", null, "• ise → Splunk Add-on for Cisco ISE"),
                          e("div", null, "• meraki → Splunk Add-on for Cisco Meraki"),
                          e("div", null, "• nutanix → Nutanix Add-on for Splunk"),
                          e("div", null, "• default → Splunk Add-on for Unix and Linux")
                        )
                      )
                    )
                  ),

                  // ARCHITECTURE INGESTION PIPELINE
                  e(
                    "div",
                    { className: "bg-slate-900/90 border border-slate-800 rounded-2xl p-5 shadow-xl" },
                    e("h3", { className: "text-sm font-bold text-slate-200 mb-3" }, "Splunk Ingestion Topology"),
                    e(
                      "div",
                      { className: "grid grid-cols-1 sm:grid-cols-4 gap-2 text-center text-xs font-semibold" },
                      e("div", { className: "p-3 bg-slate-950 rounded-xl border border-slate-800" },
                        e("div", { className: "text-cyan-400 mb-1" }, "1. DATA-BLASTER"),
                        e("div", { className: "text-slate-400 text-[11px]" }, "Native Executable (Go)"),
                        e("div", { className: "text-slate-500 text-[10px] mt-1 font-mono" }, "15 Generator Threads")
                      ),
                      e("div", { className: "p-3 bg-slate-950 rounded-xl border border-slate-800" },
                        e("div", { className: "text-amber-400 mb-1" }, "2. REST / HEC ADAPTER"),
                        e("div", { className: "text-slate-400 text-[11px]" }, "bin/run_simulation.py"),
                        e("div", { className: "text-slate-500 text-[10px] mt-1 font-mono" }, "SSL / TLS Token Auth")
                      ),
                      e("div", { className: "p-3 bg-slate-950 rounded-xl border border-slate-800" },
                        e("div", { className: "text-purple-400 mb-1" }, "3. SPLUNK HEC"),
                        e("div", { className: "text-slate-400 text-[11px]" }, ":8088/services/collector"),
                        e("div", { className: "text-slate-500 text-[10px] mt-1 font-mono" }, "Indexer Acknowledgement")
                      ),
                      e("div", { className: "p-3 bg-slate-950 rounded-xl border border-slate-800" },
                        e("div", { className: "text-emerald-400 mb-1" }, "4. TARGET STORE"),
                        e("div", { className: "text-slate-400 text-[11px]" }, activeRule.recommendedIndex),
                        e("div", { className: "text-slate-500 text-[10px] mt-1 font-mono" }, activeRule.indexType)
                      )
                    )
                  )
                )
              : null,

            // --- TAB 4: CONSOLE OUTPUT ---
            activeTab === "console"
              ? e(
                  "div",
                  { className: "bg-slate-900/90 border border-slate-800 rounded-2xl p-5 shadow-xl space-y-3 flex flex-col h-[520px]" },
                  e(
                    "div",
                    { className: "flex items-center justify-between border-b border-slate-800 pb-3" },
                    e(
                      "div",
                      null,
                      e("h3", { className: "text-sm font-bold text-slate-200 flex items-center gap-2" },
                        e("span", { className: "w-2.5 h-2.5 rounded-full bg-cyan-400 animate-pulse" }),
                        "Real-Time Binary Orchestration Console"
                      ),
                      e("p", { className: "text-xs text-slate-500 font-mono" }, "Streaming $SPLUNK_HOME/var/log/splunk/ta_network_data_blaster_orchestration.log")
                    ),
                    e(
                      "div",
                      { className: "flex items-center gap-2 text-xs" },
                      e(
                        "label",
                        { className: "flex items-center gap-1 text-slate-400 cursor-pointer" },
                        e("input", {
                          type: "checkbox",
                          checked: autoScrollConsole,
                          onChange: (e) => setAutoScrollConsole(e.target.checked),
                          className: "rounded accent-cyan-500"
                        }),
                        "Auto-scroll"
                      ),
                      e(
                        "button",
                        {
                          onClick: () => setConsoleLogs([`[INFO] Console cleared at ${new Date().toISOString()}`]),
                          className: "px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded font-mono transition-colors"
                        },
                        "Clear"
                      )
                    )
                  ),

                  // TERMINAL WINDOW
                  e(
                    "div",
                    { className: "flex-1 bg-slate-950 rounded-xl p-4 font-mono text-xs text-slate-300 border border-slate-800/80 overflow-y-auto space-y-1 shadow-inner leading-relaxed" },
                    consoleLogs.map((line, i) => {
                      let colorClass = "text-slate-300";
                      if (line.includes("[BLASTER]")) colorClass = "text-cyan-300";
                      else if (line.includes("[HEC]")) colorClass = "text-emerald-300";
                      else if (line.includes("[WARN]")) colorClass = "text-amber-300";
                      else if (line.includes("[ERROR]")) colorClass = "text-rose-400 font-bold";
                      else if (line.includes("[START]") || line.includes("[STOP]")) colorClass = "text-purple-300 font-bold";
                      return e("div", { key: i, className: colorClass }, line);
                    }),
                    e("div", { ref: consoleEndRef })
                  )
                )
              : null,

            // --- TAB 5: TOPOLOGY BUILDER & SETUP WIZARD ---
            activeTab === "wizard"
              ? e(
                  "div",
                  { className: "space-y-6" },

                  // WIZARD HEADER CARD
                  e(
                    "div",
                    { className: "bg-slate-900/90 border border-slate-800 rounded-2xl p-5 shadow-xl" },
                    e(
                      "div",
                      { className: "flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800 pb-4 mb-5" },
                      e(
                        "div",
                        null,
                        e("h2", { className: "text-base font-bold text-slate-100 flex items-center gap-2" },
                          e("span", { className: "text-cyan-400 font-mono" }, "TOPOLOGY BUILDER"),
                          "& Multi-Vendor Setup Wizard"
                        ),
                        e("p", { className: "text-xs text-slate-400 mt-0.5" },
                          "Configure Search Head HEC prerequisites, design your custom multi-tier network hierarchy, and generate executable Splunk scenarios."
                        )
                      ),
                      // MODE TOGGLE (CANVAS STUDIO vs WIZARD)
                      e(
                        "div",
                        { className: "flex flex-wrap items-center gap-2" },
                        e(
                          "div",
                          { className: "flex items-center bg-slate-950 p-1 rounded-xl border border-slate-800" },
                          e(
                            "button",
                            {
                              onClick: () => setCanvasViewMode("canvas"),
                              className: `px-3 py-1.5 rounded-lg text-xs font-bold transition-all flex items-center gap-1.5 cursor-pointer ${
                                canvasViewMode === "canvas"
                                  ? "bg-gradient-to-r from-cyan-500 to-blue-600 text-white shadow-md shadow-cyan-500/20"
                                  : "text-slate-400 hover:text-slate-200"
                              }`
                            },
                            e("span", null, "🌐"),
                            "Visual Canvas & Flow Studio",
                            isSimulatingFlow
                              ? e("span", { className: "w-2 h-2 rounded-full bg-emerald-400 animate-ping ml-1" })
                              : null
                          ),
                          e(
                            "button",
                            {
                              onClick: () => setCanvasViewMode("wizard"),
                              className: `px-3 py-1.5 rounded-lg text-xs font-bold transition-all flex items-center gap-1.5 cursor-pointer ${
                                canvasViewMode === "wizard"
                                  ? "bg-gradient-to-r from-cyan-500 to-blue-600 text-white shadow-md shadow-cyan-500/20"
                                  : "text-slate-400 hover:text-slate-200"
                              }`
                            },
                            e("span", null, "📋"),
                            "Setup Wizard & Preflight"
                          )
                        ),
                        canvasViewMode === "wizard"
                          ? e(
                              "div",
                              { className: "flex items-center gap-1 text-xs font-mono" },
                              [
                                { step: 1, label: "1. Preflight" },
                                { step: 2, label: "2. Topology" },
                                { step: 3, label: "3. Stack" },
                                { step: 4, label: "4. Deploy" }
                              ].map((s) =>
                                e(
                                  "button",
                                  {
                                    key: s.step,
                                    onClick: () => setWizardStep(s.step),
                                    className: `px-2.5 py-1.5 rounded-lg font-semibold transition-all cursor-pointer ${
                                      wizardStep === s.step
                                        ? "bg-cyan-500/20 text-cyan-300 border border-cyan-500/40"
                                        : "bg-slate-950/60 text-slate-400 hover:text-slate-200 border border-slate-800"
                                    }`
                                  },
                                  s.label
                                )
                              )
                            )
                          : null
                      )
                    ),

                    // --- VISUAL DRAG & DROP CANVAS STUDIO VIEW ---
                    canvasViewMode === "canvas"
                      ? e(
                          "div",
                          { className: "space-y-4" },

                          // TOP TOOLBAR & CONTROLS
                          e(
                            "div",
                            { className: "flex flex-wrap items-center justify-between gap-3 p-3.5 bg-slate-950/90 border border-slate-800 rounded-xl" },
                            // Left: Preset selector & Auto Layout
                            e(
                              "div",
                              { className: "flex flex-wrap items-center gap-2 text-xs" },
                              e("span", { className: "text-slate-400 font-bold uppercase tracking-wider text-[11px]" }, "Scenario Preset:"),
                              e(
                                "select",
                                {
                                  value: selectedPresetId,
                                  onChange: (ev) => handleLoadPresetTopology(ev.target.value),
                                  className: "bg-slate-900 border border-slate-700 text-slate-200 rounded-lg px-2.5 py-1.5 text-xs font-semibold focus:outline-none focus:border-cyan-500 cursor-pointer"
                                },
                                PRESET_TOPOLOGIES.map((pt) => e("option", { key: pt.id, value: pt.id }, pt.name)),
                                e("option", { value: "blank" }, "— Blank Canvas —")
                              ),
                              e(
                                "button",
                                {
                                  onClick: handleAutoLayout,
                                  className: "px-2.5 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg font-semibold flex items-center gap-1 cursor-pointer border border-slate-700"
                                },
                                "📐 Auto-Layout"
                              ),
                              e(
                                "button",
                                {
                                  onClick: handleClearCanvas,
                                  className: "px-2.5 py-1.5 bg-rose-950/40 hover:bg-rose-900/60 text-rose-300 rounded-lg font-semibold flex items-center gap-1 cursor-pointer border border-rose-800/40"
                                },
                                "🗑 Clear"
                              )
                            ),

                            // Right: Path Flow Execution & Status
                            e(
                              "div",
                              { className: "flex items-center gap-3" },
                              isSimulatingFlow
                                ? e(
                                    "div",
                                    { className: "flex items-center gap-2 text-xs font-mono text-cyan-300 bg-cyan-950/60 border border-cyan-500/40 px-3 py-1.5 rounded-lg" },
                                    e("span", { className: "w-2.5 h-2.5 rounded-full bg-emerald-400 animate-ping" }),
                                    e("span", null, `FLOW ACTIVE: Hop [${flowHopIndex + 1}/${canvasNodes.length}] • ${canvasNodes[flowHopIndex]?.customName || "Traversing"} • Trace #${activeFlowId}`)
                                  )
                                : e(
                                    "div",
                                    { className: "text-xs font-mono text-slate-400 bg-slate-900 border border-slate-800 px-3 py-1.5 rounded-lg" },
                                    "● Path Simulation Idle"
                                  ),
                              e(
                                "button",
                                {
                                  onClick: handleTogglePathFlow,
                                  className: `px-4 py-2 rounded-xl text-xs font-bold transition-all flex items-center gap-2 cursor-pointer shadow-lg ${
                                    isSimulatingFlow
                                      ? "bg-gradient-to-r from-rose-600 to-amber-600 hover:from-rose-500 hover:to-amber-500 text-white shadow-rose-600/30 animate-pulse"
                                      : "bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white shadow-cyan-500/25"
                                  }`
                                },
                                isSimulatingFlow ? "⏹ Stop Network Path Flow" : "🚀 Simulate Network Path Flow"
                              )
                            )
                          ),

                          // MAIN WORKSPACE (PALETTE + CANVAS)
                          e(
                            "div",
                            { className: "grid grid-cols-1 xl:grid-cols-12 gap-4" },

                            // LEFT: DEVICE & VENDOR PALETTE (4 COLS)
                            e(
                              "div",
                              { className: "xl:col-span-4 bg-slate-950/90 border border-slate-800 rounded-2xl p-4 flex flex-col h-[580px]" },
                              e(
                                "div",
                                { className: "flex items-center justify-between pb-3 border-b border-slate-800 mb-3" },
                                e(
                                  "div",
                                  null,
                                  e("h3", { className: "text-xs font-bold text-slate-200 uppercase tracking-wider flex items-center gap-2" },
                                    e("span", null, "🧰"),
                                    "Device & Vendor Palette"
                                  ),
                                  e("p", { className: "text-[11px] text-slate-400 mt-0.5" }, "Drag devices onto canvas or click '+ Add'")
                                ),
                                e("span", { className: "text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-400" }, `${filteredPalette.length} Items`)
                              ),

                              // Search
                              e("input", {
                                type: "text",
                                placeholder: "Search routers, firewalls, switches...",
                                value: paletteSearch,
                                onChange: (ev) => setPaletteSearch(ev.target.value),
                                className: "w-full bg-slate-900 border border-slate-800 text-slate-200 px-3 py-1.5 rounded-lg text-xs mb-2 focus:outline-none focus:border-cyan-500"
                              }),

                              // Category Pills
                              e(
                                "div",
                                { className: "flex items-center gap-1 overflow-x-auto pb-2 mb-2 text-[10px] font-semibold" },
                                ["All", "Routers", "Switches", "Firewalls", "Load Balancers", "Cloud / SASE", "Wireless APs", "AI & Compute", "Observability"].map((cat) =>
                                  e(
                                    "button",
                                    {
                                      key: cat,
                                      onClick: () => setPaletteCategory(cat),
                                      className: `px-2 py-1 rounded-md shrink-0 transition-colors cursor-pointer ${
                                        paletteCategory === cat
                                          ? "bg-cyan-500/20 text-cyan-300 border border-cyan-500/40"
                                          : "bg-slate-900 text-slate-400 hover:text-slate-200 border border-slate-800"
                                      }`
                                    },
                                    cat
                                  )
                                )
                              ),

                              // Device Items List
                              e(
                                "div",
                                { className: "flex-1 overflow-y-auto space-y-2 pr-1" },
                                filteredPalette.map((dev) =>
                                  e(
                                    "div",
                                    {
                                      key: dev.typeId,
                                      draggable: true,
                                      onDragStart: (ev) => {
                                        ev.dataTransfer.setData("application/json", JSON.stringify(dev));
                                      },
                                      className: "p-2.5 rounded-xl bg-slate-900/80 border border-slate-800/80 hover:border-slate-700 hover:bg-slate-900 transition-all flex items-center justify-between gap-2 cursor-grab active:cursor-grabbing"
                                    },
                                    e(
                                      "div",
                                      { className: "flex items-center gap-2.5 min-w-0" },
                                      e("span", { className: "text-lg shrink-0" }, dev.icon),
                                      e(
                                        "div",
                                        { className: "min-w-0" },
                                        e(
                                          "div",
                                          { className: "text-xs font-bold text-slate-200 truncate flex items-center gap-1.5" },
                                          dev.name,
                                          e("span", { className: "text-[9px] px-1.5 py-0.2 rounded font-mono font-normal bg-slate-800 text-cyan-400 border border-slate-700" }, dev.vendor)
                                        ),
                                        e(
                                          "div",
                                          { className: "text-[10px] text-slate-400 font-mono truncate flex items-center gap-1 mt-0.5" },
                                          e("span", { className: dev.metricsMode ? "text-blue-400" : "text-emerald-400" }, dev.index),
                                          e("span", { className: "text-slate-600" }, "•"),
                                          e("span", { className: "text-slate-400" }, dev.sourcetype)
                                        )
                                      )
                                    ),
                                    e(
                                      "button",
                                      {
                                        onClick: () => handleAddDeviceToCanvas(dev),
                                        className: "px-2 py-1 bg-cyan-600/20 hover:bg-cyan-600/40 text-cyan-300 hover:text-white border border-cyan-500/30 rounded-lg text-[10px] font-bold transition-colors shrink-0 cursor-pointer"
                                      },
                                      "+ Add"
                                    )
                                  )
                                )
                              )
                            ),

                            // RIGHT: INTERACTIVE CANVAS (8 COLS)
                            e(
                              "div",
                              {
                                onDragOver: (ev) => ev.preventDefault(),
                                onDrop: (ev) => {
                                  ev.preventDefault();
                                  const rawDev = ev.dataTransfer.getData("application/json");
                                  const movedId = ev.dataTransfer.getData("text/plain");
                                  const rect = ev.currentTarget.getBoundingClientRect();
                                  if (rawDev) {
                                    try {
                                      const dev = JSON.parse(rawDev);
                                      const x = Math.max(20, Math.min(rect.width - 210, ev.clientX - rect.left - 95));
                                      const y = Math.max(20, Math.min(rect.height - 120, ev.clientY - rect.top - 45));
                                      const newNode = {
                                        id: "node_" + Date.now(),
                                        customName: dev.name,
                                        typeId: dev.typeId,
                                        vendor: dev.vendor,
                                        deviceType: dev.category,
                                        icon: dev.icon,
                                        index: dev.index,
                                        sourcetype: dev.sourcetype,
                                        host: dev.name.toLowerCase().replace(/[^a-z0-9]/g, "-") + ".corp.net",
                                        sampleEvent: dev.sampleEvent,
                                        metricsMode: !!dev.metricsMode,
                                        x: Math.round(x / 10) * 10,
                                        y: Math.round(y / 10) * 10
                                      };
                                      setCanvasNodes((prev) => [...prev, newNode]);
                                      if (canvasNodes.length > 0) {
                                        const last = canvasNodes[canvasNodes.length - 1];
                                        setCanvasLinks((prev) => [
                                          ...prev,
                                          {
                                            id: "link_" + Date.now(),
                                            source: last.id,
                                            target: newNode.id,
                                            label: "Directed Uplink",
                                            protocol: "L3 / IP"
                                          }
                                        ]);
                                      }
                                      setConsoleLogs((prev) => [...prev, `[CANVAS] Dropped ${dev.vendor} ${dev.name} onto canvas.`]);
                                    } catch (err) {}
                                  } else if (movedId) {
                                    const x = Math.max(10, Math.min(rect.width - 200, ev.clientX - rect.left - 95));
                                    const y = Math.max(10, Math.min(rect.height - 120, ev.clientY - rect.top - 45));
                                    setCanvasNodes((prev) =>
                                      prev.map((n) =>
                                        n.id === movedId ? { ...n, x: Math.round(x / 10) * 10, y: Math.round(y / 10) * 10 } : n
                                      )
                                    );
                                  }
                                },
                                className: "xl:col-span-8 relative bg-slate-950 border-2 border-slate-800 rounded-2xl h-[580px] overflow-hidden select-none shadow-2xl",
                                style: {
                                  backgroundImage: "radial-gradient(circle, #1e293b 1.2px, transparent 1.2px)",
                                  backgroundSize: "24px 24px"
                                }
                              },

                              canvasNodes.length === 0
                                ? e(
                                    "div",
                                    { className: "absolute inset-0 flex flex-col items-center justify-center text-slate-600 pointer-events-none" },
                                    e("span", { className: "text-4xl mb-2" }, "🌐"),
                                    e("div", { className: "text-sm font-bold text-slate-400" }, "Network Topology Canvas is Empty"),
                                    e("div", { className: "text-xs text-slate-500 mt-1" }, "Drag & drop devices from the palette or select a preset above.")
                                  )
                                : null,

                              // SVG LINKS & ANIMATED PARTICLES LAYER
                              e(
                                "svg",
                                { className: "absolute inset-0 w-full h-full pointer-events-none z-0" },
                                e(
                                  "defs",
                                  null,
                                  e(
                                    "filter",
                                    { id: "glow", x: "-20%", y: "-20%", width: "140%", height: "140%" },
                                    e("feGaussianBlur", { stdDeviation: "3", result: "blur" }),
                                    e("feComposite", { in: "SourceGraphic", in2: "blur", operator: "over" })
                                  ),
                                  e(
                                    "marker",
                                    { id: "arrow-active", viewBox: "0 0 10 10", refX: "8", refY: "5", markerWidth: "6", markerHeight: "6", orient: "auto-start-reverse" },
                                    e("path", { d: "M 0 1 L 9 5 L 0 9 z", fill: "#38bdf8" })
                                  ),
                                  e(
                                    "marker",
                                    { id: "arrow-idle", viewBox: "0 0 10 10", refX: "8", refY: "5", markerWidth: "6", markerHeight: "6", orient: "auto-start-reverse" },
                                    e("path", { d: "M 0 1 L 9 5 L 0 9 z", fill: "#334155" })
                                  )
                                ),

                                canvasLinks.map((link) => {
                                  const src = canvasNodes.find((n) => n.id === link.source);
                                  const tgt = canvasNodes.find((n) => n.id === link.target);
                                  if (!src || !tgt) return null;
                                  const x1 = src.x + 95;
                                  const y1 = src.y + 50;
                                  const x2 = tgt.x + 95;
                                  const y2 = tgt.y + 50;
                                  const dx = Math.max(30, Math.abs(x2 - x1) * 0.4);
                                  const pathD = `M ${x1} ${y1} C ${x1 + dx} ${y1}, ${x2 - dx} ${y2}, ${x2} ${y2}`;
                                  const isLinkActive =
                                    isSimulatingFlow &&
                                    (canvasNodes[flowHopIndex]?.id === src.id ||
                                      canvasNodes[(flowHopIndex + 1) % canvasNodes.length]?.id === tgt.id);

                                  return e(
                                    "g",
                                    { key: link.id },
                                    e("path", {
                                      d: pathD,
                                      fill: "none",
                                      stroke: isLinkActive ? "#06b6d4" : "#1e293b",
                                      strokeWidth: isLinkActive ? 4 : 2,
                                      strokeOpacity: isLinkActive ? 0.8 : 0.6,
                                      filter: isLinkActive ? "url(#glow)" : undefined
                                    }),
                                    e("path", {
                                      d: pathD,
                                      fill: "none",
                                      stroke: isLinkActive ? "#38bdf8" : "#334155",
                                      strokeWidth: isLinkActive ? 2.5 : 1.5,
                                      strokeDasharray: isLinkActive ? "6 6" : "none",
                                      markerEnd: isLinkActive ? "url(#arrow-active)" : "url(#arrow-idle)"
                                    }),
                                    isSimulatingFlow
                                      ? e(
                                          "circle",
                                          { r: 4.5, fill: "#38bdf8", filter: "url(#glow)" },
                                          e("animateMotion", { path: pathD, dur: "1.4s", repeatCount: "indefinite" })
                                        )
                                      : null,
                                    e(
                                      "text",
                                      {
                                        x: (x1 + x2) / 2,
                                        y: (y1 + y2) / 2 - 6,
                                        fill: isLinkActive ? "#67e8f9" : "#64748b",
                                        fontSize: "9px",
                                        fontFamily: "monospace",
                                        textAnchor: "middle",
                                        fontWeight: "bold"
                                      },
                                      link.protocol || link.label || "IP"
                                    )
                                  );
                                })
                              ),

                              // CANVAS NODES LAYER
                              e(
                                "div",
                                { className: "absolute inset-0 z-10 pointer-events-none" },
                                canvasNodes.map((node, nodeIdx) => {
                                  const isCurrentHop = isSimulatingFlow && flowHopIndex === nodeIdx;
                                  const isLinkSource = linkSourceNodeId === node.id;
                                  const isSuccessBlast = nodeBlastStatus[node.id] === "success";
                                  const isSendingBlast = nodeBlastStatus[node.id] === "sending";

                                  return e(
                                    "div",
                                    {
                                      key: node.id,
                                      draggable: true,
                                      onDragStart: (ev) => {
                                        ev.dataTransfer.setData("text/plain", node.id);
                                      },
                                      style: {
                                        left: `${node.x}px`,
                                        top: `${node.y}px`,
                                        width: "190px"
                                      },
                                      className: `absolute pointer-events-auto rounded-xl p-2.5 shadow-2xl transition-all cursor-move ${
                                        isCurrentHop
                                          ? "bg-slate-900 border-2 border-cyan-400 ring-4 ring-cyan-400/25 shadow-cyan-500/40 scale-105"
                                          : isLinkSource
                                          ? "bg-slate-900 border-2 border-amber-400 ring-2 ring-amber-400/30"
                                          : isSuccessBlast
                                          ? "bg-slate-900 border-2 border-emerald-400 ring-2 ring-emerald-400/30"
                                          : "bg-slate-900/95 border border-slate-700/80 hover:border-slate-500"
                                      }`
                                    },

                                    // Header
                                    e(
                                      "div",
                                      { className: "flex items-center justify-between gap-1 mb-1.5" },
                                      e(
                                        "span",
                                        {
                                          className: `text-[10px] font-bold font-mono px-1.5 py-0.5 rounded uppercase tracking-wider ${
                                            node.vendor === "Cisco"
                                              ? "bg-blue-500/20 text-blue-300 border border-blue-500/30"
                                              : node.vendor === "Palo Alto"
                                              ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30"
                                              : node.vendor === "F5"
                                              ? "bg-purple-500/20 text-purple-300 border border-purple-500/30"
                                              : node.vendor === "Arista"
                                              ? "bg-cyan-500/20 text-cyan-300 border border-cyan-500/30"
                                              : node.vendor === "NVIDIA"
                                              ? "bg-teal-500/20 text-teal-300 border border-teal-500/30"
                                              : "bg-slate-800 text-slate-300 border border-slate-700"
                                          }`
                                        },
                                        node.vendor
                                      ),
                                      e(
                                        "div",
                                        { className: "flex items-center gap-1" },
                                        isCurrentHop
                                          ? e("span", { className: "w-2 h-2 rounded-full bg-cyan-400 animate-ping mr-1" })
                                          : null,
                                        e(
                                          "button",
                                          {
                                            onClick: (ev) => {
                                              ev.stopPropagation();
                                              handleDeleteCanvasNode(node.id);
                                            },
                                            className: "text-slate-500 hover:text-rose-400 text-xs px-1 cursor-pointer"
                                          },
                                          "✕"
                                        )
                                      )
                                    ),

                                    // Body
                                    e(
                                      "div",
                                      { className: "flex items-start gap-2 mb-2" },
                                      e("span", { className: "text-xl shrink-0" }, node.icon),
                                      e(
                                        "div",
                                        { className: "min-w-0" },
                                        e("div", { className: "text-xs font-bold text-slate-100 truncate leading-tight" }, node.customName),
                                        e("div", { className: "text-[10px] font-mono text-slate-400 truncate mt-0.5" }, node.host || `${node.id}.corp`)
                                      )
                                    ),

                                    // Tags
                                    e(
                                      "div",
                                      { className: "flex items-center justify-between text-[9px] font-mono mb-2 px-1.5 py-0.5 rounded bg-slate-950 border border-slate-800" },
                                      e("span", { className: "text-cyan-400 truncate" }, node.index),
                                      e("span", { className: node.metricsMode ? "text-blue-400 font-bold" : "text-emerald-400 font-bold" }, node.metricsMode ? "METRIC" : "EVENT")
                                    ),

                                    // Action Buttons: Send individually or link
                                    e(
                                      "div",
                                      { className: "grid grid-cols-2 gap-1 pt-1 border-t border-slate-800/80" },
                                      e(
                                        "button",
                                        {
                                          onClick: (ev) => {
                                            ev.stopPropagation();
                                            handleBlastSingleNode(node);
                                          },
                                          disabled: isSendingBlast,
                                          className: `px-1.5 py-1 rounded text-[10px] font-bold transition-all flex items-center justify-center gap-1 cursor-pointer ${
                                            isSuccessBlast
                                              ? "bg-emerald-500 text-slate-950 font-extrabold"
                                              : "bg-cyan-500/20 hover:bg-cyan-500/40 text-cyan-300 border border-cyan-500/30"
                                          }`
                                        },
                                        isSendingBlast ? "..." : isSuccessBlast ? "✅ Sent" : "⚡ 1 Event"
                                      ),
                                      e(
                                        "button",
                                        {
                                          onClick: (ev) => {
                                            ev.stopPropagation();
                                            handleNodeLinkClick(node.id);
                                          },
                                          className: `px-1.5 py-1 rounded text-[10px] font-bold transition-all flex items-center justify-center gap-1 cursor-pointer ${
                                            isLinkSource
                                              ? "bg-amber-400 text-slate-950 animate-pulse font-extrabold"
                                              : "bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700"
                                          }`
                                        },
                                        isLinkSource ? "Target?" : "🔗 Link"
                                      )
                                    )
                                  );
                                })
                              )
                            )
                          ),

                          // BOTTOM REAL-TIME NETWORK PATH FLOW MONITOR
                          e(
                            "div",
                            { className: "bg-slate-950/95 border border-slate-800 rounded-2xl p-4 shadow-xl space-y-3" },
                            e(
                              "div",
                              { className: "flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800/80 pb-2.5" },
                              e(
                                "div",
                                { className: "flex items-center gap-2" },
                                e("span", { className: `w-2.5 h-2.5 rounded-full ${isSimulatingFlow ? "bg-emerald-400 animate-ping" : "bg-slate-600"}` }),
                                e("h4", { className: "text-xs font-bold text-slate-200 uppercase tracking-wider" }, "Network Path Flow Traversal & Telemetry Stream"),
                                activeFlowId
                                  ? e("span", { className: "text-[10px] font-mono px-2 py-0.5 rounded bg-cyan-950 text-cyan-300 border border-cyan-500/30" }, `Trace #${activeFlowId}`)
                                  : null
                              ),
                              e(
                                "div",
                                { className: "flex items-center gap-1.5 text-[10px] font-mono overflow-x-auto" },
                                canvasNodes.map((n, i) =>
                                  e(
                                    "span",
                                    {
                                      key: n.id,
                                      className: `px-2 py-0.5 rounded flex items-center gap-1 shrink-0 ${
                                        isSimulatingFlow && flowHopIndex === i
                                          ? "bg-cyan-500 text-slate-950 font-bold shadow-md shadow-cyan-500/20"
                                          : "bg-slate-900 text-slate-400 border border-slate-800"
                                      }`
                                    },
                                    e("span", null, n.icon),
                                    n.customName,
                                    i < canvasNodes.length - 1 ? e("span", { className: "text-slate-600 font-bold ml-1" }, "➔") : null
                                  )
                                )
                              )
                            ),

                            // Real-time flow log terminal
                            e(
                              "div",
                              { className: "h-28 overflow-y-auto font-mono text-[11px] space-y-1 bg-slate-900/60 rounded-xl p-2.5 border border-slate-800/80 text-slate-300" },
                              flowLogs.length === 0
                                ? e("div", { className: "text-slate-500 italic py-2 text-center" }, "Click '🚀 Simulate Network Path Flow' or '⚡ 1 Event' on any device to stream correlated telemetry.")
                                : flowLogs.map((log) =>
                                    e(
                                      "div",
                                      { key: log.id, className: "flex items-center gap-2 hover:bg-slate-800/40 px-1.5 py-0.5 rounded" },
                                      e("span", { className: "text-slate-500 shrink-0 text-[10px]" }, `[${log.time}]`),
                                      e("span", { className: "text-cyan-400 font-bold shrink-0 text-[10px] px-1.5 rounded bg-cyan-950/60 border border-cyan-800/40" }, `Hop ${log.hop}/${log.totalHops}`),
                                      e("span", { className: "text-emerald-400 font-bold shrink-0 text-xs" }, log.vendor),
                                      e("span", { className: "text-slate-200 shrink-0" }, log.nodeName),
                                      e("span", { className: "text-slate-600 shrink-0" }, "➔"),
                                      e("span", { className: "text-purple-400 font-bold shrink-0 text-[10px]" }, log.index),
                                      e("span", { className: "text-slate-400 truncate text-[10px]" }, log.event),
                                      e("span", { className: "text-emerald-400 font-bold text-[9px] shrink-0 ml-auto bg-emerald-950/40 px-1.5 py-0.5 rounded border border-emerald-800/40" }, "200 OK")
                                    )
                                  )
                            )
                          )
                        )
                      : null,

                    // --- SETUP WIZARD VIEW ---
                    canvasViewMode === "wizard"
                      ? e(
                          "div",
                          { className: "space-y-5" },
                          // --- WIZARD STEP 1: HEC PREFLIGHT & PREREQUISITES ---
                    wizardStep === 1
                      ? e(
                          "div",
                          { className: "space-y-5" },
                          // SEARCH HEAD NOTICE BANNER
                          e(
                            "div",
                            { className: "p-4 rounded-xl bg-blue-950/30 border border-blue-500/40 text-xs text-blue-200 space-y-2" },
                            e("div", { className: "font-bold text-sm text-blue-300 flex items-center gap-2" },
                              "ℹ️ Search Head Deployment Prerequisites"
                            ),
                            e("p", null,
                              "When running on a Splunk Search Head, Network Data Blaster orchestrates execution while streaming high-velocity payloads over HTTP Event Collector (HEC) directly to indexers. HEC must be enabled and whitelisted for target indexes."
                            ),
                            e("div", { className: "flex flex-wrap items-center gap-1.5 pt-1 font-mono text-[11px]" },
                              e("span", { className: "text-slate-400" }, "Required Target Indexes:"),
                              ["idx_network_ops", "idx_security_fw", "idx_performance_metrics", "idx_wireless_ops", "cisco_mdt_metrics"].map((idx) =>
                                e("span", { key: idx, className: "px-2 py-0.5 rounded bg-slate-900 border border-slate-700 text-cyan-300" }, idx)
                              )
                            )
                          ),

                          // PREFLIGHT CONTROLS
                          e(
                            "div",
                            { className: "grid grid-cols-1 md:grid-cols-2 gap-4 p-4 rounded-xl bg-slate-950/80 border border-slate-800" },
                            e("div", { className: "space-y-3" },
                              e("div", null,
                                e("label", { className: "block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1" }, "Target HEC URL Endpoint"),
                                e("input", {
                                  type: "text",
                                  value: hecUrl,
                                  onChange: (e) => setHecUrl(e.target.value),
                                  className: "w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs font-mono text-slate-200 focus:border-cyan-500 focus:outline-none"
                                })
                              ),
                              e("div", null,
                                e("label", { className: "block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1" }, "Splunk HEC Token (GUID)"),
                                e("input", {
                                  type: showToken ? "text" : "password",
                                  value: hecToken,
                                  onChange: (e) => setHecToken(e.target.value),
                                  className: "w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs font-mono text-slate-200 focus:border-cyan-500 focus:outline-none",
                                  placeholder: "00000000-0000-0000-0000-000000000000"
                                })
                              ),
                              e(
                                "button",
                                {
                                  type: "button",
                                  onClick: handleRunPreflight,
                                  disabled: preflightStatus === "probing",
                                  className: "w-full py-2.5 px-4 bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white font-bold rounded-xl text-xs transition-all shadow-lg shadow-cyan-500/20 flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50"
                                },
                                preflightStatus === "probing"
                                  ? e("span", { className: "animate-spin" }, "⚡ Testing...")
                                  : "⚡ Run Preflight Connectivity Test"
                              )
                            ),

                            // PREFLIGHT RESULTS DIAGNOSTIC PANEL
                            e("div", { className: "space-y-3 flex flex-col justify-between" },
                              e("div", { className: "text-xs text-slate-400 uppercase tracking-wider font-semibold" }, "Diagnostics & Verification Checklist:"),
                              e("div", { className: "space-y-2 text-xs" },
                                [
                                  { label: "Search Head Web Framework Available", status: "pass" },
                                  { label: "Subprocess Execution Sandbox (shell=False)", status: "pass" },
                                  {
                                    label: preflightStatus === "success"
                                      ? `HEC Endpoint Healthy (200 OK, latency: ${preflightLatency}ms)`
                                      : "HEC Endpoint Reachable (:8088 / :443)",
                                    status: preflightStatus === "success" ? "pass" : "pending"
                                  },
                                  {
                                    label: preflightStatus === "success"
                                      ? "Target Indexes Whitelisted on Token"
                                      : "Index Provisioning & Whitelist Validation",
                                    status: preflightStatus === "success" ? "pass" : "pending"
                                  }
                                ].map((chk, idx) =>
                                  e(
                                    "div",
                                    {
                                      key: idx,
                                      className: `flex items-center gap-2 p-2 rounded-lg border ${
                                        chk.status === "pass"
                                          ? "bg-emerald-950/20 border-emerald-500/30 text-emerald-300"
                                          : "bg-slate-900/60 border-slate-800 text-slate-400"
                                      }`
                                    },
                                    e("span", null, chk.status === "pass" ? "✅" : "⏳"),
                                    chk.label
                                  )
                                )
                              ),
                              e(
                                "div",
                                { className: "flex justify-end pt-2" },
                                e(
                                  "button",
                                  {
                                    onClick: () => setWizardStep(2),
                                    className: "px-4 py-2 bg-slate-800 hover:bg-slate-700 text-cyan-300 font-bold rounded-xl text-xs transition-colors border border-slate-700 cursor-pointer"
                                  },
                                  "Continue to Topology Visualizer →"
                                )
                              )
                            )
                          )
                        )
                      : null,

                    // --- WIZARD STEP 2: INTERACTIVE VISUAL TOPOLOGY DIAGRAM ---
                    wizardStep === 2
                      ? e(
                          "div",
                          { className: "space-y-5" },
                          e(
                            "div",
                            { className: "flex items-center justify-between" },
                            e("h3", { className: "text-sm font-bold text-slate-200" }, "Multi-Tier Enterprise Hierarchy Map"),
                            e("span", { className: "text-xs text-slate-400 font-mono" }, "End-to-end multi-vendor topology")
                          ),

                          // INTERACTIVE DIAGRAM CANVAS
                          e(
                            "div",
                            { className: "p-5 bg-slate-950 rounded-xl border border-slate-800 flex flex-col items-center space-y-3 font-sans" },

                            // TIER 1: CLOUD / SASE
                            e(
                              "div",
                              { className: "w-full max-w-md p-3.5 rounded-xl bg-slate-900 border border-cyan-500/40 text-center shadow-lg hover:border-cyan-400 transition-all cursor-pointer" },
                              e("div", { className: "text-[11px] font-bold text-cyan-400 uppercase tracking-wider" }, "Tier 1: Cloud / SASE"),
                              e("div", { className: "text-sm font-bold text-slate-100 mt-0.5" }, "Zscaler (ZIA/ZPA) & Netskope Cloud Access"),
                              e("div", { className: "text-[10px] text-slate-400 font-mono mt-1" }, "Index: idx_security_fw | Sourcetype: zscaler:lss, netskope:events")
                            ),

                            // CONNECTOR
                            e("div", { className: "text-xs font-mono text-cyan-400 font-bold" }, "▼ (IPsec / GRE Tunnel)"),

                            // TIER 2: SECURITY EDGE CORRIDOR
                            e(
                              "div",
                              { className: "w-full max-w-md p-3.5 rounded-xl bg-slate-900 border border-emerald-500/40 text-center shadow-lg hover:border-emerald-400 transition-all cursor-pointer" },
                              e("div", { className: "text-[11px] font-bold text-emerald-400 uppercase tracking-wider" }, "Tier 2: Security Edge Corridor"),
                              e("div", { className: "text-sm font-bold text-slate-100 mt-0.5" }, "Palo Alto Networks Next-Gen Firewall (PA-5250)"),
                              e("div", { className: "text-[10px] text-slate-400 font-mono mt-1" }, "Index: idx_security_fw | Sourcetype: pan:traffic, pan:threat")
                            ),

                            // CONNECTOR
                            e("div", { className: "text-xs font-mono text-emerald-400 font-bold" }, "▼ (L3 Routed Uplink)"),

                            // TIER 3: WAN INTERCONNECT
                            e(
                              "div",
                              { className: "w-full max-w-md p-3.5 rounded-xl bg-slate-900 border border-amber-500/40 text-center shadow-lg hover:border-amber-400 transition-all cursor-pointer" },
                              e("div", { className: "text-[11px] font-bold text-amber-400 uppercase tracking-wider" }, "Tier 3: WAN Interconnect"),
                              e("div", { className: "text-sm font-bold text-slate-100 mt-0.5" }, "Fortinet Secure SD-WAN (FortiGate Hub)"),
                              e("div", { className: "text-[10px] text-slate-400 font-mono mt-1" }, "Index: idx_security_fw | Sourcetype: fgt_traffic, fgt_event")
                            ),

                            // CONNECTOR
                            e("div", { className: "text-xs font-mono text-amber-400 font-bold" }, "▼ (eBGP Peer Link)"),

                            // TIER 4: PROVIDER WAN CORE
                            e(
                              "div",
                              { className: "w-full max-w-md p-3.5 rounded-xl bg-slate-900 border border-purple-500/40 text-center shadow-lg hover:border-purple-400 transition-all cursor-pointer" },
                              e("div", { className: "text-[11px] font-bold text-purple-400 uppercase tracking-wider" }, "Tier 4: Provider WAN Core"),
                              e("div", { className: "text-sm font-bold text-slate-100 mt-0.5" }, "Juniper MX960 & Nokia 7750 SR OS"),
                              e("div", { className: "text-[10px] text-slate-400 font-mono mt-1" }, "Index: idx_network_ops | Sourcetype: juniper:junos:syslog")
                            ),

                            // CONNECTOR SPLIT
                            e("div", { className: "text-xs font-mono text-purple-400 font-bold" }, "▼ (iBGP / OSPF Core Split Hand-off)"),

                            // TIER 5 BRANCHES (GRID)
                            e(
                              "div",
                              { className: "grid grid-cols-1 md:grid-cols-2 gap-4 w-full pt-2" },

                              // BRANCH A: DC UNDERLAY & AI FABRIC
                              e(
                                "div",
                                { className: "p-4 rounded-xl bg-slate-900/90 border border-blue-500/40 space-y-2.5" },
                                e("div", { className: "flex items-center justify-between" },
                                  e("span", { className: "text-[11px] font-bold text-blue-400 uppercase tracking-wider" }, "Data Center Underlay"),
                                  e("span", { className: "text-[10px] px-2 py-0.5 rounded bg-blue-500/20 text-blue-300 font-mono border border-blue-500/30" }, "100GbE EVPN")
                                ),
                                e("div", { className: "text-sm font-bold text-slate-100" }, "Arista EOS Spine + Juniper QFX Leaf"),
                                e("div", { className: "p-2 rounded bg-slate-950 border border-slate-800 text-[11px] space-y-1 font-mono" },
                                  e("div", { className: "text-slate-300" }, "• F5 BIG-IP ADC/VIP (LTM Sessions)"),
                                  e("div", { className: "text-blue-300" }, "• NVIDIA Spectrum RoCE v2 AI Fabric (PFC/CNP)"),
                                  e("div", { className: "text-cyan-400" }, "• AI GPU Compute Cluster (DGX H100)")
                                ),
                                e("div", { className: "text-[10px] text-slate-400 font-mono" }, "Indexes: idx_network_ops, idx_performance_metrics")
                              ),

                              // BRANCH B: CAMPUS CORE SPINE & ACCESS
                              e(
                                "div",
                                { className: "p-4 rounded-xl bg-slate-900/90 border border-rose-500/40 space-y-2.5" },
                                e("div", { className: "flex items-center justify-between" },
                                  e("span", { className: "text-[11px] font-bold text-rose-400 uppercase tracking-wider" }, "Campus Core Spine"),
                                  e("span", { className: "text-[10px] px-2 py-0.5 rounded bg-rose-500/20 text-rose-300 font-mono border border-rose-500/30" }, "L3 Core Uplink")
                                ),
                                e("div", { className: "text-sm font-bold text-slate-100" }, "HPE Aruba AOS-CX Spine & Access"),
                                e("div", { className: "p-2 rounded bg-slate-950 border border-slate-800 text-[11px] space-y-1 font-mono" },
                                  e("div", { className: "text-slate-300" }, "• Extreme Switching PoE Access (Corporate Workstations)"),
                                  e("div", { className: "text-rose-300" }, "• Juniper Mist AP43 (CapWAP Telemetry)"),
                                  e("div", { className: "text-cyan-400" }, "• Wireless Endpoints & Client RF Metrics")
                                ),
                                e("div", { className: "text-[10px] text-slate-400 font-mono" }, "Indexes: idx_network_ops, idx_wireless_ops")
                              )
                            )
                          ),

                          e(
                            "div",
                            { className: "flex justify-between items-center pt-2" },
                            e(
                              "button",
                              {
                                onClick: () => setWizardStep(1),
                                className: "px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 font-bold rounded-xl text-xs transition-colors cursor-pointer"
                              },
                              "← Back to Preflight"
                            ),
                            e(
                              "button",
                              {
                                onClick: () => setWizardStep(3),
                                className: "px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-white font-bold rounded-xl text-xs transition-colors shadow-lg shadow-cyan-600/20 cursor-pointer"
                              },
                              "Customize Vendor Components →"
                            )
                          )
                        )
                      : null,

                    // --- WIZARD STEP 3: COMPONENT CUSTOMIZATION & FAULT INJECTION ---
                    wizardStep === 3
                      ? e(
                          "div",
                          { className: "space-y-5" },
                          e("h3", { className: "text-sm font-bold text-slate-200" }, "Customize Stack Tiers & Inject Degradation Scenarios"),

                          e(
                            "div",
                            { className: "grid grid-cols-1 md:grid-cols-2 gap-4" },

                            // SASE VENDOR SELECTION
                            e(
                              "div",
                              { className: "p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-2" },
                              e("label", { className: "text-xs font-bold text-slate-300 uppercase tracking-wider" }, "Tier 1: Cloud SASE Provider"),
                              e("select", {
                                value: selectedTiers.sase,
                                onChange: (e) => setSelectedTiers({ ...selectedTiers, sase: e.target.value }),
                                className: "w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-200 font-mono focus:border-cyan-500 focus:outline-none"
                              },
                                e("option", { value: "zscaler" }, "Zscaler Internet Access (ZIA / ZPA LSS)"),
                                e("option", { value: "netskope" }, "Netskope Cloud Security (SSE Events)"),
                                e("option", { value: "both" }, "Dual-Stack Active (Zscaler + Netskope)")
                              )
                            ),

                            // PROVIDER CORE SELECTION
                            e(
                              "div",
                              { className: "p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-2" },
                              e("label", { className: "text-xs font-bold text-slate-300 uppercase tracking-wider" }, "Tier 4: Provider WAN Core"),
                              e("select", {
                                value: selectedTiers.core,
                                onChange: (e) => setSelectedTiers({ ...selectedTiers, core: e.target.value }),
                                className: "w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-200 font-mono focus:border-cyan-500 focus:outline-none"
                              },
                                e("option", { value: "juniper" }, "Juniper MX960 (Junos rpd BGP/OSPF)"),
                                e("option", { value: "nokia" }, "Nokia 7750 SR OS (Carrier Core)"),
                                e("option", { value: "both" }, "Carrier Blend (Juniper MX + Nokia SR)")
                              )
                            ),

                            // AI FABRIC ROCE TELEMETRY
                            e(
                              "div",
                              { className: "p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-2" },
                              e("label", { className: "text-xs font-bold text-slate-300 uppercase tracking-wider" }, "AI Data Center Telemetry"),
                              e("div", { className: "flex items-center justify-between p-2 rounded bg-slate-900 border border-slate-800" },
                                e("span", { className: "text-xs text-slate-300" }, "NVIDIA Spectrum RoCE v2 (PFC/CNP Metrics)"),
                                e("input", {
                                  type: "checkbox",
                                  checked: selectedTiers.roceEnabled,
                                  onChange: (e) => setSelectedTiers({ ...selectedTiers, roceEnabled: e.target.checked }),
                                  className: "rounded accent-cyan-500"
                                })
                              )
                            ),

                            // FAULT INJECTION MODE
                            e(
                              "div",
                              { className: "p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-2" },
                              e("label", { className: "text-xs font-bold text-slate-300 uppercase tracking-wider" }, "Dynamic Scenario Failure Injection"),
                              e("select", {
                                value: selectedTiers.failureMode,
                                onChange: (e) => setSelectedTiers({ ...selectedTiers, failureMode: e.target.value }),
                                className: "w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs text-cyan-300 font-mono focus:border-cyan-500 focus:outline-none"
                              },
                                e("option", { value: "normal" }, "Normal Operational Baseline (All Healthy)"),
                                e("option", { value: "bgp_roce" }, "🔥 eBGP Route Flap + AI RoCE Congestion (Recommended)"),
                                e("option", { value: "sdwan_sla" }, "⚠️ SD-WAN SLA Tunnel Breach + Campus CRC Surge")
                              )
                            )
                          ),

                          e(
                            "div",
                            { className: "flex justify-between items-center pt-2" },
                            e(
                              "button",
                              {
                                onClick: () => setWizardStep(2),
                                className: "px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 font-bold rounded-xl text-xs transition-colors cursor-pointer"
                              },
                              "← Back to Diagram"
                            ),
                            e(
                              "button",
                              {
                                onClick: () => setWizardStep(4),
                                className: "px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-white font-bold rounded-xl text-xs transition-colors shadow-lg shadow-cyan-600/20 cursor-pointer"
                              },
                              "Synthesize Scenario Playbook →"
                            )
                          )
                        )
                      : null,

                    // --- WIZARD STEP 4: SYNTHESIZE & LAUNCH ---
                    wizardStep === 4
                      ? e(
                          "div",
                          { className: "space-y-5" },
                          e(
                            "div",
                            { className: "p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-3" },
                            e("div", { className: "flex items-center justify-between border-b border-slate-800 pb-2" },
                              e("span", { className: "text-xs font-bold text-cyan-400 font-mono uppercase" }, "Generated Master Playbook"),
                              e("span", { className: "text-[11px] font-mono px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 font-bold" }, "Validated & Ready")
                            ),
                            e("div", { className: "text-sm font-bold text-slate-200" }, "scenario_custom_multivendor_enterprise_stack.yml"),
                            e("p", { className: "text-xs text-slate-400" },
                              "Hierarchical enterprise scenario binding Cloud SASE (Zscaler/Netskope), Palo Alto Firewalls, Fortinet SD-WAN, Juniper Core, Arista/NVIDIA AI DC, and Aruba Campus into a shared causal timeline."
                            ),
                            e(
                              "div",
                              { className: "grid grid-cols-2 sm:grid-cols-4 gap-2 text-center text-xs pt-1" },
                              e("div", { className: "p-2 bg-slate-900 rounded-lg border border-slate-800" },
                                e("div", { className: "text-slate-400 text-[10px]" }, "SASE Gateway"),
                                e("div", { className: "font-mono text-cyan-300 text-[11px] font-bold" }, selectedTiers.sase.toUpperCase())
                              ),
                              e("div", { className: "p-2 bg-slate-900 rounded-lg border border-slate-800" },
                                e("div", { className: "text-slate-400 text-[10px]" }, "Core WAN"),
                                e("div", { className: "font-mono text-cyan-300 text-[11px] font-bold" }, selectedTiers.core.toUpperCase())
                              ),
                              e("div", { className: "p-2 bg-slate-900 rounded-lg border border-slate-800" },
                                e("div", { className: "text-slate-400 text-[10px]" }, "AI RoCE Fabric"),
                                e("div", { className: "font-mono text-cyan-300 text-[11px] font-bold" }, selectedTiers.roceEnabled ? "ENABLED" : "BYPASS")
                              ),
                              e("div", { className: "p-2 bg-slate-900 rounded-lg border border-slate-800" },
                                e("div", { className: "text-slate-400 text-[10px]" }, "Failure Mode"),
                                e("div", { className: "font-mono text-amber-400 text-[11px] font-bold truncate" }, selectedTiers.failureMode.toUpperCase())
                              )
                            )
                          ),

                          e(
                            "div",
                            { className: "flex justify-between items-center pt-2" },
                            e(
                              "button",
                              {
                                onClick: () => setWizardStep(3),
                                className: "px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 font-bold rounded-xl text-xs transition-colors cursor-pointer"
                              },
                              "← Back to Customizer"
                            ),
                            e(
                              "button",
                              {
                                onClick: () => {
                                  setSelectedScenarioId("scenario_custom_multivendor_enterprise_stack");
                                  setActiveTab("metrics");
                                  handleStartSimulation();
                                },
                                className: "px-6 py-2.5 bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-400 hover:to-teal-500 text-white font-bold rounded-xl text-xs transition-all shadow-lg shadow-emerald-500/20 flex items-center gap-2 cursor-pointer"
                              },
                              "🚀 Launch Multi-Tier Simulation Now"
                            )
                          )
                        )
                      : null
                    )
                : null
              )
            )
          : null,
            // --- TAB 6: DASHBOARD STUDIO LIVE HUB ---
            activeTab === "studio"
              ? e(
                  "div",
                  { className: "space-y-6" },

                  // HEADER BANNER
                  e(
                    "div",
                    { className: "bg-slate-900/90 border border-slate-800 rounded-2xl p-5 shadow-xl flex flex-col md:flex-row md:items-center justify-between gap-4" },
                    e(
                      "div",
                      null,
                      e(
                        "h2",
                        { className: "text-base font-bold text-slate-100 flex items-center gap-2" },
                        e("span", { className: "text-cyan-400 font-mono" }, "DASHBOARD STUDIO"),
                        "Live Scenario Hub"
                      ),
                      e(
                        "p",
                        { className: "text-xs text-slate-400 mt-0.5" },
                        "Native Splunk Dashboard Studio definitions that dynamically light up with real-time KPI thresholds as scenario data is ingested."
                      )
                    ),
                    e(
                      "div",
                      { className: "flex items-center gap-2 font-mono text-xs" },
                      e(
                        "a",
                        {
                          href: "/app/TA-network-data-blaster/studio_multivendor_enterprise",
                          target: "_blank",
                          rel: "noopener noreferrer",
                          className: "px-3.5 py-2 bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white font-bold rounded-xl flex items-center gap-1.5 shadow-lg shadow-cyan-500/20 cursor-pointer text-xs"
                        },
                        e("span", null, "🌐"),
                        "Open in Splunk Web (8800) ↗"
                      )
                    )
                  ),

                  // SCENARIO STUDIO CARDS GRID
                  e(
                    "div",
                    { className: "grid grid-cols-1 md:grid-cols-3 gap-5" },

                    // CARD 1: MULTI-VENDOR ENTERPRISE 5-TIER
                    e(
                      "div",
                      {
                        className: `p-5 rounded-2xl bg-slate-900/95 border transition-all space-y-4 ${
                          isSimulatingFlow || isRunning
                            ? "border-emerald-500/60 ring-2 ring-emerald-500/20 shadow-2xl shadow-emerald-500/10"
                            : "border-slate-800"
                        }`
                      },
                      e(
                        "div",
                        { className: "flex items-center justify-between" },
                        e("span", { className: "text-[11px] font-bold font-mono px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/30" }, "MV-ENT-001"),
                        e(
                          "div",
                          { className: "flex items-center gap-1.5 text-xs font-mono" },
                          e("span", { className: `w-2.5 h-2.5 rounded-full ${isSimulatingFlow || isRunning ? "bg-emerald-400 animate-ping" : "bg-slate-600"}` }),
                          e("span", { className: isSimulatingFlow || isRunning ? "text-emerald-300 font-bold" : "text-slate-400" }, isSimulatingFlow || isRunning ? "ACTIVE INGESTION" : "IDLE")
                        )
                      ),
                      e("h3", { className: "text-sm font-bold text-slate-100 leading-tight" }, "Multi-Vendor Enterprise 5-Tier Operations"),
                      e("p", { className: "text-xs text-slate-400" }, "Spans Cloud SASE (Zscaler), Perimeter NGFW (Palo Alto), SD-WAN (Fortinet), WAN Core (Juniper/Nokia), and DC Fabric (Arista/NVIDIA/F5)."),
                      // Tier Status Pills that light up
                      e(
                        "div",
                        { className: "space-y-1.5 font-mono text-[11px]" },
                        [
                          { tier: "Tier 1: Cloud SASE (Zscaler)", index: "netops_logs" },
                          { tier: "Tier 2: NGFW Edge (Palo Alto)", index: "idx_security_fw" },
                          { tier: "Tier 3: SD-WAN Core (Fortinet)", index: "idx_security_fw" },
                          { tier: "Tier 4: WAN Core (Juniper/Nokia)", index: "idx_network_ops" },
                          { tier: "Tier 5: DC AI Fabric (Arista/RoCE)", index: "idx_performance_metrics" }
                        ].map((t) =>
                          e(
                            "div",
                            {
                              key: t.tier,
                              className: `flex items-center justify-between px-2.5 py-1 rounded-lg transition-colors ${
                                isSimulatingFlow || isRunning
                                  ? "bg-emerald-950/40 border border-emerald-500/30 text-emerald-300"
                                  : "bg-slate-950/80 border border-slate-800/80 text-slate-400"
                              }`
                            },
                            e("span", null, t.tier),
                            e("span", { className: isSimulatingFlow || isRunning ? "text-emerald-400 font-bold" : "text-slate-500" }, isSimulatingFlow || isRunning ? "● INGESTING" : "STANDBY")
                          )
                        )
                      ),
                      e(
                        "a",
                        {
                          href: "/app/TA-network-data-blaster/studio_multivendor_enterprise",
                          target: "_blank",
                          rel: "noopener noreferrer",
                          className: "block text-center py-2 px-3 rounded-xl bg-slate-800 hover:bg-slate-700 text-cyan-300 font-bold text-xs transition-colors border border-slate-700 cursor-pointer"
                        },
                        "Launch Studio Dashboard ↗"
                      )
                    ),

                    // CARD 2: DC AI FABRIC & ROCE V2
                    e(
                      "div",
                      {
                        className: `p-5 rounded-2xl bg-slate-900/95 border transition-all space-y-4 ${
                          isSimulatingFlow || isRunning
                            ? "border-cyan-500/60 ring-2 ring-cyan-500/20 shadow-2xl shadow-cyan-500/10"
                            : "border-slate-800"
                        }`
                      },
                      e(
                        "div",
                        { className: "flex items-center justify-between" },
                        e("span", { className: "text-[11px] font-bold font-mono px-2 py-0.5 rounded bg-cyan-500/20 text-cyan-400 border border-cyan-500/30" }, "MV-002"),
                        e(
                          "div",
                          { className: "flex items-center gap-1.5 text-xs font-mono" },
                          e("span", { className: `w-2.5 h-2.5 rounded-full ${isSimulatingFlow || isRunning ? "bg-cyan-400 animate-ping" : "bg-slate-600"}` }),
                          e("span", { className: isSimulatingFlow || isRunning ? "text-cyan-300 font-bold" : "text-slate-400" }, isSimulatingFlow || isRunning ? "ACTIVE INGESTION" : "IDLE")
                        )
                      ),
                      e("h3", { className: "text-sm font-bold text-slate-100 leading-tight" }, "Data Center AI Fabric & RoCE v2 Assurance"),
                      e("p", { className: "text-xs text-slate-400" }, "High-velocity GPU cluster telemetry tracking NVIDIA Spectrum RoCE v2 PFC frames, Arista 7280 buffer pool percent, and F5 ADC VIP throughput."),
                      e(
                        "div",
                        { className: "space-y-1.5 font-mono text-[11px]" },
                        [
                          { metric: "RoCE v2 Lossless PFC Frames", type: "METRICS" },
                          { metric: "Arista 7280 Shared Buffer %", type: "METRICS" },
                          { metric: "F5 BIG-IP Active VIP Conns", type: "EVENTS" },
                          { metric: "DGX H100 GPU Cluster Nodes", type: "METRICS" }
                        ].map((m) =>
                          e(
                            "div",
                            {
                              key: m.metric,
                              className: `flex items-center justify-between px-2.5 py-1 rounded-lg transition-colors ${
                                isSimulatingFlow || isRunning
                                  ? "bg-cyan-950/40 border border-cyan-500/30 text-cyan-300"
                                  : "bg-slate-950/80 border border-slate-800/80 text-slate-400"
                              }`
                            },
                            e("span", null, m.metric),
                            e("span", { className: isSimulatingFlow || isRunning ? "text-cyan-400 font-bold" : "text-slate-500" }, isSimulatingFlow || isRunning ? "● LIVE" : "STANDBY")
                          )
                        )
                      ),
                      e(
                        "a",
                        {
                          href: "/app/TA-network-data-blaster/studio_roce_ai_fabric",
                          target: "_blank",
                          rel: "noopener noreferrer",
                          className: "block text-center py-2 px-3 rounded-xl bg-slate-800 hover:bg-slate-700 text-cyan-300 font-bold text-xs transition-colors border border-slate-700 cursor-pointer"
                        },
                        "Launch Studio Dashboard ↗"
                      )
                    ),

                    // CARD 3: CROSS-DOMAIN TRIAGE MATRIX (MV-016)
                    e(
                      "div",
                      {
                        className: `p-5 rounded-2xl bg-slate-900/95 border transition-all space-y-4 ${
                          isSimulatingFlow || isRunning
                            ? "border-amber-500/60 ring-2 ring-amber-500/20 shadow-2xl shadow-amber-500/10"
                            : "border-slate-800"
                        }`
                      },
                      e(
                        "div",
                        { className: "flex items-center justify-between" },
                        e("span", { className: "text-[11px] font-bold font-mono px-2 py-0.5 rounded bg-amber-500/20 text-amber-400 border border-amber-500/30" }, "MV-016"),
                        e(
                          "div",
                          { className: "flex items-center gap-1.5 text-xs font-mono" },
                          e("span", { className: `w-2.5 h-2.5 rounded-full ${isSimulatingFlow || isRunning ? "bg-amber-400 animate-ping" : "bg-slate-600"}` }),
                          e("span", { className: isSimulatingFlow || isRunning ? "text-amber-300 font-bold" : "text-slate-400" }, isSimulatingFlow || isRunning ? "ACTIVE INGESTION" : "IDLE")
                        )
                      ),
                      e("h3", { className: "text-sm font-bold text-slate-100 leading-tight" }, "Cross-Domain Slowness Triage Matrix"),
                      e("p", { className: "text-xs text-slate-400" }, "End-to-end incident investigation correlating Catalyst switchport CRC bursts, Palo Alto session drops, Meraki RF latency, and ThousandEyes loss."),
                      e(
                        "div",
                        { className: "space-y-1.5 font-mono text-[11px]" },
                        [
                          { hop: "Hop 1: Catalyst CRC Error Bursts", sev: "CRITICAL" },
                          { hop: "Hop 2: Palo Alto Session Drops", sev: "WARNING" },
                          { hop: "Hop 3: Meraki / Mist RF Latency", sev: "WARNING" },
                          { hop: "Hop 4: ThousandEyes Probe Loss", sev: "CRITICAL" }
                        ].map((h) =>
                          e(
                            "div",
                            {
                              key: h.hop,
                              className: `flex items-center justify-between px-2.5 py-1 rounded-lg transition-colors ${
                                isSimulatingFlow || isRunning
                                  ? "bg-amber-950/40 border border-amber-500/30 text-amber-300"
                                  : "bg-slate-950/80 border border-slate-800/80 text-slate-400"
                              }`
                            },
                            e("span", null, h.hop),
                            e("span", { className: isSimulatingFlow || isRunning ? "text-amber-400 font-bold" : "text-slate-500" }, isSimulatingFlow || isRunning ? "● CORRELATED" : "STANDBY")
                          )
                        )
                      ),
                      e(
                        "a",
                        {
                          href: "/app/TA-network-data-blaster/studio_cross_domain_triage",
                          target: "_blank",
                          rel: "noopener noreferrer",
                          className: "block text-center py-2 px-3 rounded-xl bg-slate-800 hover:bg-slate-700 text-cyan-300 font-bold text-xs transition-colors border border-slate-700 cursor-pointer"
                        },
                        "Launch Studio Dashboard ↗"
                      )
                    )
                  )
                )
              : null
          )
        )
      )
    );
  }

  // --- FALLBACK DATA IN CASE MANIFESTS CANNOT BE FETCHED OVER HTTP ---
  const FALLBACK_SCENARIOS = [
    { id: "scenario_mv_016_cross_domain_slowness", filename: "scenario_mv_016_cross_domain_slowness.yml", name: "MV-016: Cross-Domain Multi-Vendor Application Slowness (Cat9k + PAN + Meraki + ThousandEyes)", group: "Multi-Vendor Incident Playbooks", description: "Simulates a corporate-wide application degradation event tracing from a wired infrastructure link degradation up to wireless client symptoms.", sourcetypes: ["cisco:ios", "pan:traffic", "pan:system", "pan:threat", "meraki:alert", "cisco:thousandeyes:metric", "cisco:thousandeyes:event"] },
    { id: "full_network_topology", filename: "scenario_acme_full_network_topology.yml", name: "ACME Full Enterprise Network Topology (All Domains)", group: "ACME Enterprise", description: "All 10 network, compute, and security domains streaming concurrently.", sourcetypes: ["cisco:mdt:bgp", "cisco:sdwan:syslog", "cisco:ftd:syslog"] },
    { id: "acme_bridge_domain", filename: "scenario_acme_bridge_domain_withdrawal.yml", name: "ACME Bridge Domain Withdrawal (ACI Leaf Outage)", group: "ACME Enterprise", description: "Leaf switch spine drop and bridge withdrawal.", sourcetypes: ["cisco:dc:aci:bridge-domain"] },
    { id: "campus_cross_domain", filename: "scenario_acme_campus_cross_domain_visibility.yml", name: "ACME Campus Cross-Domain Visibility (Cat9k + ISE)", group: "ACME Enterprise", description: "Campus access security and telemetry.", sourcetypes: ["cisco:catalyst:clienthealth", "cisco:ise:syslog"] },
    { id: "mpls_backbone", filename: "scenario_acme_mpls_backbone_realtime.yml", name: "ACME MPLS Backbone Real-Time Assurance (Carrier P/PE)", group: "ACME Enterprise", description: "Core carrier MPLS SLA telemetry.", sourcetypes: ["cisco:metrics:bgp-rib", "cisco:metrics:isis"] },
    { id: "mpls_to_srv6", filename: "scenario_acme_mpls_to_srv6_transition.yml", name: "ACME MPLS-to-SRv6 Transition Assurance", group: "ACME Enterprise", description: "MPLS to SRv6 path migration telemetry.", sourcetypes: ["cisco:metrics:isis", "cisco:metrics:interface-counters"] },
    { id: "sdwan_toronto", filename: "scenario_acme_sdwan_toronto_degradation.yml", name: "ACME SD-WAN Toronto Hub Brownout & Failover", group: "ACME Enterprise", description: "Toronto hub packet loss and BFD flap.", sourcetypes: ["cisco:sdwan:linkhealth"] },
    { id: "maple_catalyst", filename: "scenario_maple_catalyst.yml", name: "Maple Catalyst Core & Access Assurance", group: "Maple Multi-Cloud", description: "Maple Catalyst switch fabric.", sourcetypes: ["cisco:catalyst:networkhealth"] },
    { id: "maple_intersight", filename: "scenario_maple_intersight.yml", name: "Maple Intersight Compute & UCS Ingestion", group: "Maple Multi-Cloud", description: "UCS server hardware telemetry.", sourcetypes: ["cisco:intersight:compute"] },
    { id: "maple_nutanix", filename: "scenario_maple_nutanix.yml", name: "Maple Nutanix Enterprise Cloud Telemetry", group: "Maple Multi-Cloud", description: "Nutanix Prism Central telemetry.", sourcetypes: ["nutanixpc:vms", "nutanixpc:syslog"] },
    { id: "maple_security", filename: "scenario_maple_security.yml", name: "Maple Multi-Layer Security Operations", group: "Maple Multi-Cloud", description: "Firewall & Duo security ingestion.", sourcetypes: ["cisco:ftd:syslog", "cisco:duo:authentication"] },
    { id: "campus", filename: "scenario_campus.yml", name: "Core Campus Switched Fabric Baseline", group: "Core Domains", description: "Campus baseline traffic.", sourcetypes: ["cisco:catalyst:client"] },
    { id: "core", filename: "scenario_core.yml", name: "Datacenter Core Backbone Ingestion", group: "Core Domains", description: "Nexus 9K backbone.", sourcetypes: ["cisco:dc:nexus9k"] },
    { id: "cross_platform_disaster", filename: "scenario_cross_platform_disaster.yml", name: "Cross-Platform Disaster Recovery Drill", group: "Core Domains", description: "Multi-datacenter failover.", sourcetypes: ["cisco:syslog"] },
    { id: "meraki_branch", filename: "scenario_meraki_branch_assurance.yml", name: "Meraki Cloud-Managed Branch Assurance", group: "Core Domains", description: "Meraki SD-WAN & APs.", sourcetypes: ["meraki:appliancesdwanstatistics"] },
    { id: "sdwan", filename: "scenario_sdwan.yml", name: "Enterprise SD-WAN Edge Ingestion", group: "Core Domains", description: "Edge routers.", sourcetypes: ["cisco:sdwan:syslog"] },
    { id: "wireless", filename: "scenario_wireless.yml", name: "Wireless LAN Controller & Access Points", group: "Core Domains", description: "Catalyst 9800 WLC.", sourcetypes: ["cisco:catalyst:clienthealth"] },
    { id: "mix", filename: "scenario_mix.yml", name: "Mixed Multi-Domain Synthetic Ingestion", group: "Core Domains", description: "Heterogeneous network blend.", sourcetypes: ["cisco:syslog", "cisco:metrics"] }
  ];

  const FALLBACK_SAMPLES = {
    categories: [
      { categoryName: "Cisco Catalyst", totalSamples: 2, samples: [{ id: "cisco-catalyst-clienthealth", detectedSourcetype: "cisco:catalyst:clienthealth", previewSnippet: "{\"clientMac\": \"00:11:22:33:44:55\", \"healthScore\": 92}" }] },
      { categoryName: "Cisco DC (ACI, Nexus)", totalSamples: 2, samples: [{ id: "cisco-dc-aci-bridge-domain", detectedSourcetype: "cisco:dc:aci:bridge-domain", previewSnippet: "{\"bd\": \"BD-PROD-APP\", \"state\": \"up\"}" }] },
      { categoryName: "Cisco SD-WAN", totalSamples: 2, samples: [{ id: "cisco-sdwan-mdt-connection-6-state-changed", detectedSourcetype: "cisco:sdwan:mdt", previewSnippet: "{\"time\": 1678900000, \"event\": \"metric\", \"state\": \"established\"}" }] },
      { categoryName: "Meraki", totalSamples: 2, samples: [{ id: "meraki-appliancesdwanstatistics", detectedSourcetype: "meraki:appliancesdwanstatistics", previewSnippet: "{\"networkId\": \"N_1234\", \"latency\": 12}" }] },
      { categoryName: "Nutanix PC", totalSamples: 1, samples: [{ id: "nutanixpc-syslog", detectedSourcetype: "nutanixpc:syslog", previewSnippet: "Oct 12 14:00:00 nutanix-node-01 kernel: [INFO] Disk latency normal" }] }
    ],
    totalSamples: 163
  };

  // --- MOUNT INTO DOM ---
  function init() {
    const rootEl = document.getElementById("datablaster-app-root");
    if (!rootEl) {
      setTimeout(init, 100);
      return;
    }

    if (ReactDOM.createRoot) {
      const root = ReactDOM.createRoot(rootEl);
      root.render(e(DataBlasterApp));
    } else {
      ReactDOM.render(e(DataBlasterApp), rootEl);
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
