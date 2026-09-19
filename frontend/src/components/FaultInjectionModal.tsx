import React, { useState, useEffect } from 'react';
import { AlertTriangle, Zap, CheckCircle2, RotateCcw, Activity, ShieldAlert, Cpu, Network, Radio } from 'lucide-react';
import type { TopologyState, FaultScenarioType, FaultEventRecord } from '../types/topology';

interface FaultInjectionModalProps {
  isOpen: boolean;
  onClose: () => void;
  topology: TopologyState;
  onTopologyMutated: () => void;
}

export const FaultInjectionModal: React.FC<FaultInjectionModalProps> = ({
  isOpen,
  onClose,
  topology,
  onTopologyMutated,
}) => {
  const [scenarioType, setScenarioType] = useState<FaultScenarioType>('link_cut');
  const [selectedEdgeId, setSelectedEdgeId] = useState<string>('');
  const [selectedNodeId, setSelectedNodeId] = useState<string>('');
  const [activeFaults, setActiveFaults] = useState<FaultEventRecord[]>([]);
  const [injecting, setInjecting] = useState<boolean>(false);
  const [lastResult, setLastResult] = useState<any>(null);

  useEffect(() => {
    if (topology.edges && topology.edges.length > 0 && !selectedEdgeId) {
      setSelectedEdgeId(topology.edges[0].id);
    }
    if (topology.nodes && topology.nodes.length > 0 && !selectedNodeId) {
      setSelectedNodeId(topology.nodes[0].id);
    }
  }, [topology, selectedEdgeId, selectedNodeId]);

  const fetchActiveFaults = async () => {
    try {
      const res = await fetch('/api/faults/history');
      if (res.ok) {
        const data = await res.json();
        setActiveFaults(data.active_faults || []);
      }
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchActiveFaults();
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleInject = async () => {
    setInjecting(true);
    try {
      const res = await fetch('/api/faults/inject', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          scenario_type: scenarioType,
          target_edge_id: scenarioType === 'link_cut' ? selectedEdgeId : undefined,
          target_node_id: scenarioType !== 'link_cut' ? selectedNodeId : undefined,
          cascade_enabled: true
        })
      });
      const data = await res.json();
      setLastResult(data);
      await fetchActiveFaults();
      onTopologyMutated();
    } catch (e) {
      console.error(e);
    } finally {
      setInjecting(false);
    }
  };

  const handleRecover = async (edgeId?: string, nodeId?: string, faultId?: string) => {
    try {
      await fetch('/api/faults/recover', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          target_edge_id: edgeId,
          target_node_id: nodeId,
          fault_id: faultId
        })
      });
      await fetchActiveFaults();
      onTopologyMutated();
    } catch (e) {
      console.error(e);
    }
  };

  const scenarios: { id: FaultScenarioType; title: string; desc: string; icon: any; color: string }[] = [
    {
      id: 'link_cut',
      title: 'Physical Link Sever (Fiber Cut)',
      desc: 'Cuts link, triggers interface carrier loss (LOS), SNMP linkDown, and BGP/OSPF neighbor drop.',
      icon: Network,
      color: 'from-rose-500/20 to-red-600/20 text-rose-400 border-rose-500/30'
    },
    {
      id: 'hardware_exhaustion',
      title: 'Hardware Resource Saturation',
      desc: 'Spikes CPU to 98.4% and RAM to 95.2%, generates buffer queue drops and transit delays.',
      icon: Cpu,
      color: 'from-amber-500/20 to-orange-600/20 text-amber-400 border-amber-500/30'
    },
    {
      id: 'bgp_route_flap',
      title: 'BGP Route Flapping & Prefix Leak',
      desc: 'Forces rapid BGP peer transitions between ESTABLISHED and IDLE with prefix churn.',
      icon: Activity,
      color: 'from-cyan-500/20 to-blue-600/20 text-cyan-400 border-cyan-500/30'
    },
    {
      id: 'ddos_syn_flood',
      title: 'Volumetric DDoS SYN Flood',
      desc: 'Saturates state table with 145,000 PPS, triggering firewall rate-limit drops & Radware scrubbing.',
      icon: ShieldAlert,
      color: 'from-red-500/20 to-rose-700/20 text-red-400 border-red-500/30'
    },
    {
      id: 'lateral_movement',
      title: 'Internal Kerberos Lateral Movement',
      desc: 'Failed Kerberos pre-auth followed by suspicious SMB/RPC mapping into Database tier.',
      icon: AlertTriangle,
      color: 'from-purple-500/20 to-indigo-600/20 text-purple-400 border-purple-500/30'
    },
    {
      id: 'optical_ber_degradation',
      title: 'Transceiver Pre-FEC BER Degradation',
      desc: 'Simulates transceiver degradation with optical Bit Error Rate climbing above 10^-3.',
      icon: Radio,
      color: 'from-emerald-500/20 to-teal-600/20 text-emerald-400 border-emerald-500/30'
    }
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 overflow-y-auto">
      <div className="bg-[#1F2937] border border-[#374151] w-full max-w-4xl rounded-xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="px-6 py-4 bg-[#111827] border-b border-[#374151] flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-amber-500/20 border border-amber-500/40 rounded-lg text-amber-400">
              <Zap className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white tracking-wide">
                Dynamic Fault & Failure Injection Engine
              </h2>
              <p className="text-xs text-slate-400">
                Orchestrate multi-device anomalies with chronologically correlated log & OpenConfig MDT metric cascades
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white px-3 py-1 rounded bg-slate-800 hover:bg-slate-700 border border-slate-600 text-sm transition-colors"
          >
            Close
          </button>
        </div>

        <div className="p-6 space-y-6 overflow-y-auto flex-1 custom-scrollbar">
          {/* Active Faults Banner */}
          {activeFaults.length > 0 && (
            <div className="bg-rose-950/40 border border-rose-500/40 rounded-lg p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-semibold text-rose-300 flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 text-rose-400 animate-pulse" />
                  {activeFaults.length} Active Injected Fault(s) Disrupting Infrastructure
                </span>
              </div>
              <div className="space-y-2">
                {activeFaults.map((f) => (
                  <div key={f.id} className="flex items-center justify-between bg-slate-900/60 p-2.5 rounded border border-rose-900/50 text-xs">
                    <div>
                      <span className="font-mono text-rose-400 font-bold mr-2">[{f.scenario_type.toUpperCase()}]</span>
                      <span className="text-slate-200">{f.description}</span>
                    </div>
                    <button
                      onClick={() => handleRecover(f.affected_edges[0], f.affected_nodes[0], f.id)}
                      className="px-2.5 py-1 bg-emerald-600/30 hover:bg-emerald-600/50 text-emerald-300 border border-emerald-500/50 rounded flex items-center gap-1 transition-all"
                    >
                      <RotateCcw className="w-3 h-3" /> Restore State
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Fault Scenario Selector Grid */}
          <div>
            <label className="text-xs font-semibold text-slate-300 uppercase tracking-wider block mb-3">
              1. Select Failure Injection Scenario
            </label>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {scenarios.map((sc) => {
                const IconComponent = sc.icon;
                const isSelected = scenarioType === sc.id;
                return (
                  <div
                    key={sc.id}
                    onClick={() => setScenarioType(sc.id)}
                    className={`p-3.5 rounded-lg border cursor-pointer transition-all bg-gradient-to-br ${
                      isSelected
                        ? `${sc.color} ring-1 ring-amber-400 shadow-lg`
                        : 'bg-slate-800/50 border-slate-700/80 hover:bg-slate-800 text-slate-300'
                    }`}
                  >
                    <div className="flex items-start gap-3">
                      <div className={`p-2 rounded-md ${isSelected ? 'bg-black/30' : 'bg-slate-700/50'}`}>
                        <IconComponent className="w-5 h-5" />
                      </div>
                      <div>
                        <h4 className="text-sm font-semibold text-white">{sc.title}</h4>
                        <p className="text-xs text-slate-400 mt-1 leading-relaxed">{sc.desc}</p>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Target Selection */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 bg-slate-800/40 p-4 rounded-lg border border-slate-700/60">
            {scenarioType === 'link_cut' ? (
              <div className="col-span-2">
                <label className="text-xs font-semibold text-slate-300 block mb-1">
                  Target Link to Sever (Physical Carrier Drop)
                </label>
                <select
                  value={selectedEdgeId}
                  onChange={(e) => setSelectedEdgeId(e.target.value)}
                  className="w-full bg-[#1F2937] border border-[#374151] rounded px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-amber-500"
                >
                  {topology.edges.map((e) => {
                    const srcNode = topology.nodes.find((n) => n.id === e.source)?.name || e.source;
                    const dstNode = topology.nodes.find((n) => n.id === e.target)?.name || e.target;
                    return (
                      <option key={e.id} value={e.id}>
                        {srcNode} ({e.source_port || 'port-1'}) ↔ {dstNode} ({e.target_port || 'port-1'}) [{e.link_type?.toUpperCase() || 'ETH'}, {e.bandwidth_mbps || 1000}M]
                      </option>
                    );
                  })}
                </select>
              </div>
            ) : (
              <div className="col-span-2">
                <label className="text-xs font-semibold text-slate-300 block mb-1">
                  Target Node for Injection
                </label>
                <select
                  value={selectedNodeId}
                  onChange={(e) => setSelectedNodeId(e.target.value)}
                  className="w-full bg-[#1F2937] border border-[#374151] rounded px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-amber-500"
                >
                  {topology.nodes.map((n) => (
                    <option key={n.id} value={n.id}>
                      {n.name} [{n.type?.toUpperCase()} | IP: {n.ip_address} | Vendor: {n.vendor}]
                    </option>
                  ))}
                </select>
              </div>
            )}
          </div>

          {/* Action Button */}
          <div className="flex justify-end gap-3 pt-2">
            <button
              onClick={handleInject}
              disabled={injecting}
              className="px-6 py-2.5 bg-gradient-to-r from-amber-500 to-rose-600 hover:from-amber-600 hover:to-rose-700 text-white font-semibold rounded-lg shadow-lg flex items-center gap-2 text-sm transition-all disabled:opacity-50"
            >
              {injecting ? (
                <>
                  <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Orchestrating Cascade...
                </>
              ) : (
                <>
                  <Zap className="w-4 h-4" />
                  ⚡ Inject Fault &amp; Run Multi-Device Cascade
                </>
              )}
            </button>
          </div>

          {/* Execution Output Panel */}
          {lastResult && (
            <div className="bg-[#0B0F19] border border-slate-800 rounded-lg p-4 space-y-3">
              <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                <span className="text-xs font-semibold text-emerald-400 flex items-center gap-1.5">
                  <CheckCircle2 className="w-4 h-4" /> Fault Dispatched Successfully ({lastResult.cascading_logs_count} logs, {lastResult.metrics_count} OpenConfig MDT metrics)
                </span>
                <span className="text-[11px] font-mono text-slate-500">ID: {lastResult.record?.id}</span>
              </div>
              <div className="space-y-1.5 max-h-48 overflow-y-auto custom-scrollbar font-mono text-xs text-slate-300">
                {lastResult.logs?.map((l: any, idx: number) => (
                  <div key={idx} className="bg-slate-900/60 p-2 rounded border border-slate-800/80">
                    <span className="text-amber-400">[{l.timestamp}]</span> <span className="text-sky-400 font-bold">{l.device_id}</span> <span className="text-rose-400 font-semibold">{l.signature}</span>
                    <div className="text-slate-400 text-[11px] truncate mt-0.5">{l.raw_log}</div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
