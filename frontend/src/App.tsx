import React, { useState, useEffect, useRef, useCallback } from 'react';
import { TopBar } from './components/TopBar';
import { NodePalette } from './components/NodePalette';
import { TopologyCanvas } from './components/TopologyCanvas';
import { LogTerminal } from './components/LogTerminal';
import { NodeInspectorModal } from './components/NodeInspectorModal';
import { SyslogConfigModal } from './components/SyslogConfigModal';
import { FaultInjectionModal } from './components/FaultInjectionModal';
import { OpenConfigTreeModal } from './components/OpenConfigTreeModal';
import { SNMPMibModal } from './components/SNMPMibModal';
import { TelemetryPipelinesModal } from './components/TelemetryPipelinesModal';
import { VendorAddonsModal } from './components/VendorAddonsModal';
import { SPLPlaygroundModal } from './components/SPLPlaygroundModal';
import { UseCaseRepositoryModal } from './components/UseCaseRepositoryModal';
import { NocSocMetricsModal } from './components/NocSocMetricsModal';
import type {
  TopologyState,
  ScenarioType,
  LogEntry,
  NodeType,
  Node,
  EcosystemMode,
  TelemetryTransportConfig
} from './types/topology';
import {
  PRESET_SECURE,
  PRESET_BYPASSED,
  PRESET_LATERAL,
  PRESET_CISCO_CAMPUS,
  PRESET_CISCO_SDWAN,
  PRESET_CISCO_ACI,
  PRESET_MIXED_EDGE,
  PRESET_MIXED_SASE,
  PRESET_MIXED_OPTICAL,
  PRESET_OPENCONFIG_CORE,
  PRESET_PAN,
  PRESET_LAN,
  PRESET_WLAN,
  PRESET_SAN,
  PRESET_NAS,
  PRESET_VPN,
  PRESET_PURE_CISCO_ENT
} from './presets/defaultTopologies';

const BACKEND_HTTP = typeof window !== 'undefined' && window.location.port === '8081'
  ? window.location.origin
  : 'http://localhost:8081';

const BACKEND_WS = typeof window !== 'undefined' && window.location.port === '8081'
  ? ((window.location.protocol === 'https:' ? 'wss://' : 'ws://') + window.location.host + '/ws/logs')
  : 'ws://localhost:8081/ws/logs';

export const App: React.FC = () => {
  // Main State - Defaults to Pure Cisco Enterprise Fabric with simulation running
  const [ecosystemMode, setEcosystemMode] = useState<EcosystemMode>('pure_cisco');
  const [topology, setTopology] = useState<TopologyState>(PRESET_PURE_CISCO_ENT);
  const [scenario, setScenario] = useState<ScenarioType>('pure_cisco_enterprise');
  const [isRunning, setIsRunning] = useState<boolean>(true);
  const [speedMs, setSpeedMs] = useState<number>(500);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [selectedEdgeId, setSelectedEdgeId] = useState<string | null>(null);
  const [isConnected, setIsConnected] = useState<boolean>(false);

  // Security Zones, Node Inspector, and Dual Transport Modal States
  const [showZones, setShowZones] = useState<boolean>(true);
  const [inspectingNode, setInspectingNode] = useState<Node | null>(null);
  const [showSyslogModal, setShowSyslogModal] = useState<boolean>(false);
  const [showFaultModal, setShowFaultModal] = useState<boolean>(false);
  const [showOpenConfigModal, setShowOpenConfigModal] = useState<boolean>(false);
  const [showSNMPModal, setShowSNMPModal] = useState<boolean>(false);
  const [showPipelinesModal, setShowPipelinesModal] = useState<boolean>(false);
  const [showVendorAddonsModal, setShowVendorAddonsModal] = useState<boolean>(false);
  const [showSPLModal, setShowSPLModal] = useState<boolean>(false);
  const [showUseCaseModal, setShowUseCaseModal] = useState<boolean>(false);
  const [showMetricsModal, setShowMetricsModal] = useState<boolean>(false);
  const [splInitialQuery, setSplInitialQuery] = useState<string | undefined>(undefined);
  const [transportConfig, setTransportConfig] = useState<TelemetryTransportConfig>({
    hec_enabled: true,
    hec_url: 'http://127.0.0.1:8888/services/collector',
    hec_token: '00000000-0000-0000-0000-000000000000',
    hec_index: 'idx_network_ops',
    syslog_enabled: true,
    syslog_host: '127.0.0.1',
    syslog_port: 514,
    syslog_protocol: 'udp',
    syslog_facility: 16,
    syslog_format: 'rfc5424'
  });

  const wsRef = useRef<WebSocket | null>(null);
  const syncTimeoutRef = useRef<any>(null);

  // Refresh Topology from Backend after fault injection / recovery
  const handleTopologyMutated = useCallback(() => {
    fetch(`${BACKEND_HTTP}/api/topology`)
      .then((res) => res.json())
      .then((data) => {
        if (data && Array.isArray(data.nodes)) {
          setTopology(data);
        }
      })
      .catch((err) => console.warn('Failed to refresh topology:', err));
  }, []);

  // Sync Topology to Backend REST API
  const syncTopologyToBackend = useCallback((nextTop: TopologyState) => {
    if (syncTimeoutRef.current) {
      clearTimeout(syncTimeoutRef.current);
    }
    syncTimeoutRef.current = setTimeout(() => {
      fetch(`${BACKEND_HTTP}/api/topology`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(nextTop)
      }).catch((err) => console.warn('Failed to sync topology to backend:', err));
    }, 200);
  }, []);

  // Update Topology handler
  const handleUpdateTopology = (nextTopology: TopologyState) => {
    setTopology(nextTopology);
    syncTopologyToBackend(nextTopology);
  };

  // Add Node from Palette
  const handleAddNode = (type: NodeType, overrides?: Partial<Node>) => {
    const id = `node-${type}-${Date.now().toString().slice(-4)}`;
    const count = topology.nodes.filter((n) => n.type === type).length + 1;
    const newNode: Node = {
      id,
      name: overrides?.name || `${type.replace('_', ' ').toUpperCase()} ${count}`,
      type,
      x: 350 + Math.floor(Math.random() * 80) - 40,
      y: 200 + Math.floor(Math.random() * 80) - 40,
      ip_address: overrides?.ip_address || `10.0.${Math.floor(Math.random() * 10) + 1}.${Math.floor(Math.random() * 200) + 10}`,
      status: 'active',
      vendor: overrides?.vendor || 'generic',
      sourcetype: overrides?.sourcetype
    };
    const nextTopology: TopologyState = {
      ...topology,
      nodes: [...topology.nodes, newNode]
    };
    setTopology(nextTopology);
    setSelectedNodeId(id);
    syncTopologyToBackend(nextTopology);
  };

  // Update selected node properties
  const handleUpdateSelectedNode = (updated: Partial<Node>) => {
    if (!selectedNodeId) return;
    const nextNodes = topology.nodes.map((n) => (n.id === selectedNodeId ? { ...n, ...updated } : n));
    const nextTopology = { ...topology, nodes: nextNodes };
    setTopology(nextTopology);
    syncTopologyToBackend(nextTopology);
  };

  // Delete selected node
  const handleDeleteSelectedNode = (nodeId: string) => {
    const nextNodes = topology.nodes.filter((n) => n.id !== nodeId);
    const nextEdges = topology.edges.filter((e) => e.source !== nodeId && e.target !== nodeId);
    const nextTopology = { nodes: nextNodes, edges: nextEdges };
    setTopology(nextTopology);
    setSelectedNodeId(null);
    syncTopologyToBackend(nextTopology);
  };

  // Preset Loader
  const handleLoadPreset = (presetId: string) => {
    let selectedPreset = PRESET_SECURE;
    if (presetId === 'pure_cisco') selectedPreset = PRESET_PURE_CISCO_ENT;
    else if (presetId === 'pan') selectedPreset = PRESET_PAN;
    else if (presetId === 'lan') selectedPreset = PRESET_LAN;
    else if (presetId === 'wlan') selectedPreset = PRESET_WLAN;
    else if (presetId === 'san') selectedPreset = PRESET_SAN;
    else if (presetId === 'nas') selectedPreset = PRESET_NAS;
    else if (presetId === 'vpn') selectedPreset = PRESET_VPN;
    else if (presetId === 'bypassed') selectedPreset = PRESET_BYPASSED;
    else if (presetId === 'lateral') selectedPreset = PRESET_LATERAL;
    else if (presetId === 'cisco_campus') selectedPreset = PRESET_CISCO_CAMPUS;
    else if (presetId === 'cisco_sdwan') selectedPreset = PRESET_CISCO_SDWAN;
    else if (presetId === 'cisco_aci') selectedPreset = PRESET_CISCO_ACI;
    else if (presetId === 'mixed_edge') selectedPreset = PRESET_MIXED_EDGE;
    else if (presetId === 'mixed_sase') selectedPreset = PRESET_MIXED_SASE;
    else if (presetId === 'mixed_optical') selectedPreset = PRESET_MIXED_OPTICAL;
    else if (presetId === 'openconfig_core') selectedPreset = PRESET_OPENCONFIG_CORE;

    setTopology(selectedPreset);
    setSelectedNodeId(null);
    setSelectedEdgeId(null);
    syncTopologyToBackend(selectedPreset);
  };

  // Clear Canvas
  const handleClearCanvas = () => {
    if (confirm('Clear entire topology canvas?')) {
      const emptyTop: TopologyState = { nodes: [], edges: [] };
      setTopology(emptyTop);
      setSelectedNodeId(null);
      setSelectedEdgeId(null);
      syncTopologyToBackend(emptyTop);
    }
  };

  // Toggle Simulation Play/Pause
  const handleTogglePlay = () => {
    const nextRunning = !isRunning;
    setIsRunning(nextRunning);
    fetch(`${BACKEND_HTTP}/api/scenarios/run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        scenario,
        ecosystem_mode: ecosystemMode,
        running: nextRunning,
        speed_ms: speedMs
      })
    }).catch((e) => console.warn('Simulation control error:', e));
  };

  // Switch Ecosystem Mode
  const handleSelectEcosystemMode = (nextMode: EcosystemMode) => {
    setEcosystemMode(nextMode);
    let nextScenario = scenario;
    let nextPreset = topology;

    if (nextMode === 'pure_cisco') {
      nextScenario = 'pure_cisco_enterprise';
      nextPreset = PRESET_PURE_CISCO_ENT;
    } else {
      nextScenario = 'mixed_edge_breach';
      nextPreset = PRESET_MIXED_EDGE;
    }

    setScenario(nextScenario);
    setTopology(nextPreset);
    setSelectedNodeId(null);
    setSelectedEdgeId(null);
    syncTopologyToBackend(nextPreset);

    fetch(`${BACKEND_HTTP}/api/scenarios/run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        scenario: nextScenario,
        ecosystem_mode: nextMode,
        running: isRunning,
        speed_ms: speedMs
      })
    }).catch((e) => console.warn('Mode switch error:', e));
  };

  // Switch Scenario
  const handleSelectScenario = (nextScenario: ScenarioType) => {
    setScenario(nextScenario);

    // Auto load correlated topology preset for optimal visual alignment
    if (nextScenario === 'pure_cisco_enterprise') handleLoadPreset('pure_cisco');
    else if (nextScenario === 'cisco_campus_rogue') handleLoadPreset('cisco_campus');
    else if (nextScenario === 'cisco_sdwan_brownout') handleLoadPreset('cisco_sdwan');
    else if (nextScenario === 'cisco_aci_microburst') handleLoadPreset('cisco_aci');
    else if (nextScenario === 'mixed_vendor_enterprise') handleLoadPreset('mixed_edge');
    else if (nextScenario === 'mixed_edge_breach') handleLoadPreset('mixed_edge');
    else if (nextScenario === 'mixed_sase_degradation') handleLoadPreset('mixed_sase');
    else if (nextScenario === 'mixed_backbone_optical') handleLoadPreset('mixed_optical');
    else if (nextScenario === 'openconfig_mdt_streaming') handleLoadPreset('openconfig_core');
    else if (nextScenario === 'arch_pan_iot_mesh') handleLoadPreset('pan');
    else if (nextScenario === 'arch_lan_campus_access') handleLoadPreset('lan');
    else if (nextScenario === 'arch_wlan_meraki_catalyst') handleLoadPreset('wlan');
    else if (nextScenario === 'arch_san_fibre_channel') handleLoadPreset('san');
    else if (nextScenario === 'arch_nas_storage_cluster') handleLoadPreset('nas');
    else if (nextScenario === 'arch_vpn_remote_workforce') handleLoadPreset('vpn');

    fetch(`${BACKEND_HTTP}/api/scenarios/run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        scenario: nextScenario,
        ecosystem_mode: ecosystemMode,
        running: isRunning,
        speed_ms: speedMs
      })
    }).catch((e) => console.warn('Scenario switch error:', e));
  };

  // Change Tick Rate Speed Slider
  const handleChangeSpeed = (nextSpeed: number) => {
    setSpeedMs(nextSpeed);
    fetch(`${BACKEND_HTTP}/api/scenarios/run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        scenario,
        ecosystem_mode: ecosystemMode,
        running: isRunning,
        speed_ms: nextSpeed
      })
    }).catch((e) => console.warn('Speed adjust error:', e));
  };

  // Export Logs (Raw KV, JSON, CSV)
  const handleExportLogs = (format: 'raw' | 'json' | 'csv') => {
    window.open(`${BACKEND_HTTP}/api/export-logs?format=${format}`, '_blank');
  };

  // Clear Logs
  const handleClearLogs = () => {
    setLogs([]);
    fetch(`${BACKEND_HTTP}/api/logs`, { method: 'DELETE' }).catch(() => {});
  };

  // WebSocket Connection Management
  useEffect(() => {
    let reconnectTimeout: any;

    const connectWs = () => {
      try {
        const ws = new WebSocket(BACKEND_WS);
        wsRef.current = ws;

        ws.onopen = () => {
          setIsConnected(true);
          syncTopologyToBackend(topology);
        };

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            if (data.raw_log && data.timestamp) {
              const entry: LogEntry = data;
              setLogs((prev) => [...prev.slice(-1500), entry]);

              if (entry.status === 'breached' && entry.node_id) {
                setTopology((prev) => {
                  const updatedNodes = prev.nodes.map((n) =>
                    n.id === entry.node_id ? { ...n, status: 'breached' as const } : n
                  );
                  return { ...prev, nodes: updatedNodes };
                });
              }
            } else if (data.type === 'simulation_state') {
              setIsRunning(data.running);
            } else if (data.type === 'scenario_state') {
              setScenario(data.scenario);
            }
          } catch (err) {
            console.error('Error parsing WS log payload:', err);
          }
        };

        ws.onclose = () => {
          setIsConnected(false);
          reconnectTimeout = setTimeout(connectWs, 2500);
        };

        ws.onerror = () => {
          setIsConnected(false);
          ws.close();
        };
      } catch (e) {
        setIsConnected(false);
        reconnectTimeout = setTimeout(connectWs, 2500);
      }
    };

    connectWs();

    return () => {
      if (wsRef.current) wsRef.current.close();
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
    };
  }, []);

  // In-Browser Local Simulation Fallback (Ensures simulation always works even without external Python server)
  useEffect(() => {
    if (!isRunning || isConnected) return;

    const interval = setInterval(() => {
      const activeNodes = topology.nodes.filter(n => n.power_state !== "stopped");
      if (activeNodes.length === 0) return;

      const randomNode = activeNodes[Math.floor(Math.random() * activeNodes.length)];
      const ts = new Date().toISOString();
      const timeSec = Math.floor(Date.now() / 1000);

      let logText = "";
      let sourcetype = randomNode.sourcetype || "cisco:ios:syslog";
      let action: "allowed" | "blocked" | "alerted" | "dropped" = "allowed";

      if (scenario === "openconfig_mdt_streaming") {
        sourcetype = "cisco:ios:mdt:metric";
        const inOctets = Math.floor(Math.random() * 50000000) + 10000000;
        const outOctets = Math.floor(Math.random() * 40000000) + 8000000;
        const cpu = (Math.random() * 15 + 15).toFixed(1);
        const mem = (Math.random() * 10 + 30).toFixed(1);
        logText = `cisco:ios:mdt:metric host=${randomNode.name} openconfig_path="/interfaces/interface[name=Gi1/0/1]/state/counters" metric_name:interface.octets.in=${inOctets} metric_name:interface.octets.out=${outOctets} metric_name:cpu.utilization=${cpu} metric_name:memory.utilization=${mem} oper_status=UP`;

        // Direct HEC push if enabled
        if (transportConfig.hec_enabled) {
          fetch(transportConfig.hec_url, {
            method: "POST",
            headers: {
              "Authorization": `Splunk ${transportConfig.hec_token}`,
              "Content-Type": "application/json"
            },
            body: JSON.stringify({
              time: timeSec,
              event: "metric",
              source: "cisco:ios:mdt",
              sourcetype: "cisco:ios:mdt:metric",
              host: `${randomNode.name}.corp.internal`,
              index: "cisco_mdt_metrics",
              fields: {
                "metric_name:interface.octets.in": inOctets,
                "metric_name:interface.octets.out": outOctets,
                "metric_name:cpu.utilization": parseFloat(cpu),
                "metric_name:memory.utilization": parseFloat(mem),
                "metric_name:carrier.transitions": 0.0,
                "_value": inOctets,
                "interface": "GigabitEthernet1/0/1",
                "oper_status": "UP",
                "device": randomNode.name
              }
            })
          }).catch(() => {});
        }
      } else if (scenario === "cisco_campus_rogue") {
        sourcetype = "cisco:catalyst:rogue:threat_details";
        logText = `cisco:catalyst:rogue:threat_details ap_name="${randomNode.name}" rogue_bssid="70:69:79:4c:11:02" ssid="Corporate-Guest-EvilTwin" rogue_type="Unclassified" classification="Threat" state="Alert" signal_rssi=-68`;
        action = "alerted";
      } else if (scenario === "cisco_sdwan_brownout") {
        sourcetype = "cisco:sdwan:linkhealth";
        logText = `${randomNode.name}: bfd: event=state_change local_color=biz-internet remote_color=biz-internet loss_pct=14.8 latency_ms=184.2 jitter_ms=42.1 sla_state=violated`;
        action = "alerted";
      } else if (scenario === "pure_cisco_enterprise") {
        if (randomNode.vendor === "cisco_ise") {
          sourcetype = "cisco:ise:nac:8021x";
          logText = `CISE_Passed_Authentications 00000001 1 0 ${ts} host=${randomNode.name} User-Name=alex.turner@enterprise.corp Calling-Station-Id=70-69-79-4C-11-02 NAS-IP-Address=10.254.3.1 NAS-Port=50101 Framing-Protocol=PPP Tunnel-Type=VLAN Tunnel-Medium-Type=802 Tunnel-Private-Group-ID=VLAN_DATA cisco-av-pair=profile-name=Apple-Device cisco-av-pair=security-group-tag=0004-TrustSec-Employee EapAuthentication=EAP-TLS Response=Passed`;
        } else if (randomNode.type === "wlc_controller") {
          sourcetype = "cisco:catalyst:clienthealth";
          logText = `cisco:catalyst:clienthealth timestamp="${ts}" controller="${randomNode.name}" client_mac="70:69:79:4c:11:02" ap_name="Meraki-MR56-AP" client_ip="10.40.1.105" ssid="Corp-Secure-WPA3" health_score=98 rssi=-58 snr=38 channel=36 throughput_mbps=482.5 status=HEALTHY`;
        } else {
          sourcetype = "cisco:catalyst:networkhealth";
          logText = `cisco:catalyst:networkhealth timestamp="${ts}" device_name="${randomNode.name}" management_ip="${randomNode.ip_address}" platform="Catalyst 9600" overall_health=95 cpu_utilization_pct=${(Math.random() * 15 + 20).toFixed(1)} memory_utilization_pct=${(Math.random() * 10 + 35).toFixed(1)} thermal_state="normal" routing_table_version=1420 bgp_prefixes=18400 psu_status="redundant_ok"`;
        }
      } else if (scenario === "arch_vpn_remote_workforce") {
        if (randomNode.vendor === "cisco_duo") {
          sourcetype = "cisco:duo:push:prompt";
          logText = `timestamp="${ts}" host="${randomNode.name}" event_type="authentication" user="marcus.vance@enterprise.corp" factor="duo_push" result="SUCCESS" ip_address="198.51.100.88" integration="Cisco ASA AnyConnect SSL-VPN" device="iPhone 15 Pro iOS 17.4" posture_state="COMPLIANT" location="Austin, TX, US"`;
        } else {
          sourcetype = "cisco:asa";
          logText = `%ASA-6-725001: Group <Employee-VPN-Policy> User <marcus.vance> IP <198.51.100.88> Assigned IPv4 address <10.240.1.55> to remote user, encryption=AES-GCM-256, hashing=SHA-384, posture=compliant.`;
        }
      } else if (scenario === "arch_wlan_meraki_catalyst") {
        sourcetype = randomNode.sourcetype || "meraki:accesspoints";
        logText = `meraki:accesspoints timestamp="${ts}" network_id="N_88192031" device_serial="Q2KD-99A1-XZ34" name="${randomNode.name}" client_count=34 channel_utilization_2_4ghz=18% channel_utilization_5ghz=42% tx_power_dbm=17 rx_packets=1289004 tx_packets=2490182 mesh_role="root" status="online"`;
      } else if (scenario === "arch_san_fibre_channel") {
        sourcetype = "cisco:mds:san:fc";
        logText = `cisco:mds:san:fc timestamp="${ts}" switch="${randomNode.name}" vsan=100 fc_port="fc1/1" rx_frames=2948010 tx_frames=3819020 rx_bytes=64424509440 tx_bytes=85899345920 b2b_credit_drops=0 link_resets=0 crc_errors=0 throughput_gbps=64.0 status=optimal`;
      } else if (scenario === "arch_nas_storage_cluster") {
        sourcetype = "netapp:ontap:nas";
        logText = `netapp:ontap:nas timestamp="${ts}" cluster="${randomNode.name}" vserver="svm_corp_nfs" volume="vol_prod_ai_models" protocol="NFSv4.1" iops=42800 throughput_mbps=1240.5 latency_ms=0.85 capacity_used_pct=64.2 multi_path="active-active"`;
      } else if (scenario === "arch_pan_iot_mesh") {
        sourcetype = "pan:ble:iot:sensor";
        logText = `pan:ble:iot:sensor timestamp="${ts}" sensor_id="${randomNode.name}" protocol="BLE_MESH" adv_interval_ms=100 rssi=-54 battery_pct=96.4 temperature_celsius=${(Math.random() * 2 + 23).toFixed(1)} humidity_pct=45.2 vibration_g=0.02 status="nominal"`;
      } else {
        sourcetype = randomNode.sourcetype || "cisco:ios:syslog";
        logText = `%SEC-6-IPACCESSLOGP: list 101 permitted tcp 192.168.1.100(49201) -> ${randomNode.ip_address}(443)`;
      }

      const newEntry: LogEntry = {
        timestamp: ts,
        device_id: randomNode.id,
        node_id: randomNode.id,
        node_type: randomNode.type,
        src_ip: "192.168.1.100",
        dest_ip: randomNode.ip_address,
        protocol: "TCP",
        duration: "14ms",
        action: action,
        signature: action === "alerted" ? "MALWARE-CNC-BEACON" : "TCP-FLOW-NORMAL",
        status: (randomNode.status === 'blocked' || randomNode.status === 'breached' || randomNode.status === 'degraded')
          ? randomNode.status
          : 'normal',
        raw_log: logText,
        sourcetype: sourcetype
      };

      setLogs((prev) => [...prev.slice(-1500), newEntry]);
    }, speedMs);

    return () => clearInterval(interval);
  }, [isRunning, isConnected, speedMs, scenario, topology, transportConfig]);

  // Fetch Telemetry Transport Config on Mount
  useEffect(() => {
    fetch(`${BACKEND_HTTP}/api/telemetry/config`)
      .then((res) => res.json())
      .then((data) => {
        if (data.global_transport) {
          setTransportConfig(data.global_transport);
        }
      })
      .catch((err) => console.warn('Could not load telemetry transport config:', err));
  }, []);

  // Global Power Controls (Power All On / Halt All)
  const handlePowerAll = (power: 'running' | 'stopped') => {
    const nextNodes = topology.nodes.map((n) => ({
      ...n,
      power_state: power,
      status: power === 'stopped' ? ('stopped' as const) : ('active' as const)
    }));
    const nextTop = { ...topology, nodes: nextNodes };
    setTopology(nextTop);
    syncTopologyToBackend(nextTop);
  };

  // Node Inspector Save Handler
  const handleUpdateNodeFromInspector = (updatedNode: Node) => {
    const nextNodes = topology.nodes.map((n) => (n.id === updatedNode.id ? updatedNode : n));
    const nextTop = { ...topology, nodes: nextNodes };
    setTopology(nextTop);
    syncTopologyToBackend(nextTop);
    setInspectingNode(null);

    // Sync power state to backend power endpoint
    fetch(`${BACKEND_HTTP}/api/nodes/${updatedNode.id}/power`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ power_state: updatedNode.power_state || 'running' })
    }).catch(() => {});
  };

  // Save Telemetry Transport Config (Dual Splunk HEC & Direct Syslog UDP/TCP 514)
  const handleSaveTransportConfig = (updated: TelemetryTransportConfig) => {
    setTransportConfig(updated);
    fetch(`${BACKEND_HTTP}/api/telemetry/config`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(updated)
    }).catch((e) => console.warn('Failed to update telemetry config:', e));
    setShowSyslogModal(false);
  };

  const selectedNode = topology.nodes.find((n) => n.id === selectedNodeId) || null;

  return (
    <div className="flex flex-col h-screen w-screen overflow-hidden bg-[#0B0F19] text-slate-100">
      {/* Top Navigation & Action Controls */}
      <TopBar
        ecosystemMode={ecosystemMode}
        onSelectEcosystemMode={handleSelectEcosystemMode}
        scenario={scenario}
        onSelectScenario={handleSelectScenario}
        isRunning={isRunning}
        onTogglePlay={handleTogglePlay}
        speedMs={speedMs}
        onChangeSpeed={handleChangeSpeed}
        onClearCanvas={handleClearCanvas}
        onLoadPreset={handleLoadPreset}
        onExportLogs={handleExportLogs}
        isConnected={isConnected}
        totalLogs={logs.length}
        showZones={showZones}
        onToggleZones={() => setShowZones(!showZones)}
        onOpenSyslogModal={() => setShowSyslogModal(true)}
        onOpenFaultModal={() => setShowFaultModal(true)}
        onOpenOpenConfigModal={() => setShowOpenConfigModal(true)}
        onOpenSNMPModal={() => setShowSNMPModal(true)}
        onOpenPipelinesModal={() => setShowPipelinesModal(true)}
        onOpenVendorAddonsModal={() => setShowVendorAddonsModal(true)}
        onOpenSPLPlayground={() => setShowSPLModal(true)}
        onOpenUseCaseRepo={() => setShowUseCaseModal(true)}
        onOpenNocSocMetrics={() => setShowMetricsModal(true)}
        onPowerAll={handlePowerAll}
      />

      {/* 3-Column Split Screen Dashboard */}
      <div className="flex-1 flex overflow-hidden relative">
        {/* Left: Categorized Component Palette & Node Inspector */}
        <NodePalette
          ecosystemMode={ecosystemMode}
          onAddNode={handleAddNode}
          selectedNode={selectedNode}
          onUpdateSelectedNode={handleUpdateSelectedNode}
          onDeleteSelectedNode={handleDeleteSelectedNode}
          activeScenario={scenario}
        />

        {/* Center: GNS3 Interactive Topology Canvas */}
        <TopologyCanvas
          topology={topology}
          onUpdateTopology={handleUpdateTopology}
          selectedNodeId={selectedNodeId}
          onSelectNode={setSelectedNodeId}
          selectedEdgeId={selectedEdgeId}
          onSelectEdge={setSelectedEdgeId}
          isRunning={isRunning}
          showZones={showZones}
          onInspectNode={(node) => setInspectingNode(node)}
        />

        {/* Right: Splunk Live Streaming Log Terminal */}
        <LogTerminal
          logs={logs}
          onClearLogs={handleClearLogs}
          isRunning={isRunning}
          onTogglePlay={handleTogglePlay}
        />
      </div>

      {/* Virtual Hardware & Node Power Inspector Modal */}
      {inspectingNode && (
        <NodeInspectorModal
          node={inspectingNode}
          zones={topology.zones}
          onClose={() => setInspectingNode(null)}
          onUpdateNode={handleUpdateNodeFromInspector}
        />
      )}

      {/* Dual Transport & Direct Syslog UDP/TCP Port 514 Modal */}
      {showSyslogModal && (
        <SyslogConfigModal
          config={transportConfig}
          onClose={() => setShowSyslogModal(false)}
          onSave={handleSaveTransportConfig}
        />
      )}

      {/* Dynamic Fault & Anomaly Injection Engine Modal */}
      <FaultInjectionModal
        isOpen={showFaultModal}
        onClose={() => setShowFaultModal(false)}
        topology={topology}
        onTopologyMutated={handleTopologyMutated}
      />

      {/* OpenConfig YANG & Model-Driven Telemetry Tree Modal */}
      <OpenConfigTreeModal
        isOpen={showOpenConfigModal}
        onClose={() => setShowOpenConfigModal(false)}
        topology={topology}
      />

      {/* SC4SNMP 300+ MIB Explorer & Trap Emitter Modal */}
      <SNMPMibModal
        isOpen={showSNMPModal}
        onClose={() => setShowSNMPModal(false)}
        nodes={topology.nodes}
        globalTransport={transportConfig}
      />

      {/* Universal 4-Way Pipeline Matrix Modal */}
      <TelemetryPipelinesModal
        isOpen={showPipelinesModal}
        onClose={() => setShowPipelinesModal(false)}
        config={transportConfig}
        onSaveConfig={handleSaveTransportConfig}
      />

      {/* Splunk Vendor Technology Add-on (TA) Directory Modal */}
      <VendorAddonsModal
        isOpen={showVendorAddonsModal}
        onClose={() => setShowVendorAddonsModal(false)}
      />

      {/* Interactive Jupyter-like SPL Playground Modal */}
      <SPLPlaygroundModal
        isOpen={showSPLModal}
        onClose={() => {
          setShowSPLModal(false);
          setSplInitialQuery(undefined);
        }}
        logs={logs}
        initialQuery={splInitialQuery}
      />

      {/* NOC & SOC Use Case Repository & Test Harness Modal */}
      <UseCaseRepositoryModal
        isOpen={showUseCaseModal}
        onClose={() => setShowUseCaseModal(false)}
        logs={logs}
        onOpenInSPL={(query) => {
          setSplInitialQuery(query);
          setShowSPLModal(true);
        }}
      />

      {/* NOC & SOC Metrics Matrix Modal */}
      <NocSocMetricsModal
        isOpen={showMetricsModal}
        onClose={() => setShowMetricsModal(false)}
      />
    </div>
  );
};

export default App;

