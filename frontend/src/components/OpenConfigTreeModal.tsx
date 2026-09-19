import React, { useState, useEffect } from 'react';
import { Database, RefreshCw, Send, CheckCircle, Layers, Cpu, Network, Radio } from 'lucide-react';
import type { TopologyState } from '../types/topology';

interface OpenConfigTreeModalProps {
  isOpen: boolean;
  onClose: () => void;
  topology: TopologyState;
}

export const OpenConfigTreeModal: React.FC<OpenConfigTreeModalProps> = ({
  isOpen,
  onClose,
  topology
}) => {
  const [selectedNodeId, setSelectedNodeId] = useState<string>('');
  const [yangTree, setYangTree] = useState<any>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [sampleSuccess, setSampleSuccess] = useState<string | null>(null);

  useEffect(() => {
    if (topology.nodes && topology.nodes.length > 0 && !selectedNodeId) {
      setSelectedNodeId(topology.nodes[0].id);
    }
  }, [topology, selectedNodeId]);

  const fetchTree = async (nodeId: string) => {
    if (!nodeId) return;
    setLoading(true);
    setSampleSuccess(null);
    try {
      const res = await fetch(`/api/openconfig/tree/${nodeId}`);
      if (res.ok) {
        const data = await res.json();
        setYangTree(data.tree);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen && selectedNodeId) {
      fetchTree(selectedNodeId);
    }
  }, [isOpen, selectedNodeId]);

  if (!isOpen) return null;

  const handleSamplePush = async () => {
    setLoading(true);
    try {
      const res = await fetch(`/api/gnmi/sample?node_id=${selectedNodeId}`, { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        setSampleSuccess(`Successfully streamed ${data.total_metrics_emitted} gNMI metrics to cisco_mdt_metrics!`);
        // Refresh tree to see incremented counters
        fetchTree(selectedNodeId);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };


  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 overflow-y-auto">
      <div className="bg-[#1F2937] border border-[#374151] w-full max-w-4xl rounded-xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="px-6 py-4 bg-[#111827] border-b border-[#374151] flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-cyan-500/20 border border-cyan-500/40 rounded-lg text-cyan-400">
              <Database className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white tracking-wide">
                OpenConfig YANG Data Modeling &amp; gNMI Inspector
              </h2>
              <p className="text-xs text-slate-400">
                Inspect live RFC OpenConfig YANG operational states &amp; trigger SAMPLE/ON_CHANGE telemetry streams
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

        {/* Toolbar & Node Selector */}
        <div className="px-6 py-3 bg-slate-850 border-b border-slate-700/60 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold text-slate-300">Device:</span>
            <select
              value={selectedNodeId}
              onChange={(e) => setSelectedNodeId(e.target.value)}
              className="bg-[#1F2937] border border-[#374151] rounded px-3 py-1.5 text-xs text-cyan-300 font-medium focus:outline-none focus:border-cyan-500"
            >
              {topology.nodes.map((n) => (
                <option key={n.id} value={n.id}>
                  {n.name} ({n.ip_address}) [{n.vendor?.toUpperCase()}]
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => fetchTree(selectedNodeId)}
              disabled={loading}
              className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-600 rounded text-xs flex items-center gap-1.5 transition-all"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} /> Refresh YANG Tree
            </button>
            <button
              onClick={handleSamplePush}
              disabled={loading}
              className="px-4 py-1.5 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white font-medium rounded text-xs flex items-center gap-1.5 transition-all shadow-md"
            >
              <Send className="w-3.5 h-3.5" /> ⚡ Stream gNMI SAMPLE Batch
            </button>
          </div>
        </div>

        {/* Success Alert */}
        {sampleSuccess && (
          <div className="mx-6 mt-3 p-2.5 bg-emerald-950/40 border border-emerald-500/50 rounded text-xs text-emerald-300 flex items-center gap-2">
            <CheckCircle className="w-4 h-4 text-emerald-400" />
            {sampleSuccess}
          </div>
        )}

        {/* Content Body */}
        <div className="p-6 overflow-y-auto flex-1 custom-scrollbar space-y-4">
          {/* Quick Metrics Cards */}
          {yangTree && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <div className="bg-[#0B0F19]/60 p-3 rounded-lg border border-slate-800">
                <div className="text-[11px] text-slate-400 flex items-center gap-1 mb-1">
                  <Cpu className="w-3.5 h-3.5 text-cyan-400" /> CPU Utilization
                </div>
                <div className="text-lg font-bold text-white font-mono">
                  {yangTree["openconfig-platform:components"]?.component?.[1]?.state?.["cpu-utilization"] || 18.5}%
                </div>
              </div>
              <div className="bg-[#0B0F19]/60 p-3 rounded-lg border border-slate-800">
                <div className="text-[11px] text-slate-400 flex items-center gap-1 mb-1">
                  <Layers className="w-3.5 h-3.5 text-blue-400" /> Memory Load
                </div>
                <div className="text-lg font-bold text-white font-mono">
                  {yangTree["openconfig-platform:components"]?.component?.[1]?.state?.["memory-utilization"] || 34.0}%
                </div>
              </div>
              <div className="bg-[#0B0F19]/60 p-3 rounded-lg border border-slate-800">
                <div className="text-[11px] text-slate-400 flex items-center gap-1 mb-1">
                  <Network className="w-3.5 h-3.5 text-emerald-400" /> Oper Status
                </div>
                <div className="text-lg font-bold text-emerald-400 font-mono">
                  {yangTree["openconfig-interfaces:interfaces"]?.interface?.[0]?.state?.["oper-status"] || "UP"}
                </div>
              </div>
              <div className="bg-[#0B0F19]/60 p-3 rounded-lg border border-slate-800">
                <div className="text-[11px] text-slate-400 flex items-center gap-1 mb-1">
                  <Radio className="w-3.5 h-3.5 text-amber-400" /> Carrier Transitions
                </div>
                <div className="text-lg font-bold text-amber-400 font-mono">
                  {yangTree["openconfig-interfaces:interfaces"]?.interface?.[0]?.state?.counters?.["carrier-transitions"] || 0}
                </div>
              </div>
            </div>
          )}

          {/* JSON Tree Viewer */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                YANG Operational Data Hierarchy (RFC 7950 / OpenConfig JSON)
              </span>
              <span className="text-[11px] font-mono text-cyan-400">
                Target Splunk Index: cisco_mdt_metrics
              </span>
            </div>
            <pre className="bg-[#0B0F19] border border-slate-800 rounded-lg p-4 text-xs font-mono text-cyan-200 overflow-x-auto max-h-96 custom-scrollbar leading-relaxed">
              {yangTree ? JSON.stringify(yangTree, null, 2) : '// Loading OpenConfig YANG schema tree...'}
            </pre>
          </div>
        </div>
      </div>
    </div>
  );
};
