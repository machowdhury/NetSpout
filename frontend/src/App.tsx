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
  PRESET_OPENCONFIG_CORE
} from './presets/defaultTopologies';

const BACKEND_HTTP = typeof window !== 'undefined' && window.location.port === '8081'
  ? window.location.origin
  : 'http://localhost:8081';

const BACKEND_WS = typeof window !== 'undefined' && window.location.port === '8081'
  ? ((window.location.protocol === 'https:' ? 'wss://' : 'ws://') + window.location.host + '/ws/logs')
  : 'ws://localhost:8081/ws/logs';

export const App: React.FC = () => {
  // Main State
  const [ecosystemMode, setEcosystemMode] = useState<EcosystemMode>('mixed_vendor');
  const [topology, setTopology] = useState<TopologyState>(PRESET_MIXED_EDGE);
  const [scenario, setScenario] = useState<ScenarioType>('mixed_edge_breach');
  const [isRunning, setIsRunning] = useState<boolean>(false);
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
    if (presetId === 'bypassed') selectedPreset = PRESET_BYPASSED;
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
      nextScenario = 'cisco_campus_rogue';
      nextPreset = PRESET_CISCO_CAMPUS;
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
    if (nextScenario === 'cisco_campus_rogue') handleLoadPreset('cisco_campus');
    else if (nextScenario === 'cisco_sdwan_brownout') handleLoadPreset('cisco_sdwan');
    else if (nextScenario === 'cisco_aci_microburst') handleLoadPreset('cisco_aci');
    else if (nextScenario === 'mixed_edge_breach') handleLoadPreset('mixed_edge');
    else if (nextScenario === 'mixed_sase_degradation') handleLoadPreset('mixed_sase');
    else if (nextScenario === 'mixed_backbone_optical') handleLoadPreset('mixed_optical');
    else if (nextScenario === 'openconfig_mdt_streaming') handleLoadPreset('openconfig_core');

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
    </div>
  );
};

export default App;

