import React, { useState } from 'react';
import type { Node, NodePowerState, ZoneAnnotation } from '../types/topology';
import { Power, Cpu, Network, Shield, X, Check, AlertTriangle } from 'lucide-react';

interface NodeInspectorModalProps {
  node: Node;
  zones?: ZoneAnnotation[];
  onClose: () => void;
  onUpdateNode: (updatedNode: Node) => void;
}

export const NodeInspectorModal: React.FC<NodeInspectorModalProps> = ({
  node,
  zones = [],
  onClose,
  onUpdateNode,
}) => {
  const [name, setName] = useState(node.name);
  const [ipAddress, setIpAddress] = useState(node.ip_address);
  const [powerState, setPowerState] = useState<NodePowerState>(node.power_state || 'running');
  const [zoneId, setZoneId] = useState(node.zone_id || '');
  
  // Hardware Specs
  const [vcpu, setVcpu] = useState(node.hardware?.vcpu_count || 2);
  const [ramMb, setRamMb] = useState(node.hardware?.ram_mb || 4096);
  const cpuUsage = node.hardware?.cpu_utilization_pct || 22.5;
  const memUsage = node.hardware?.memory_utilization_pct || 36.0;
  const tempC = node.hardware?.temperature_celsius || 41.0;

  // Interfaces
  const defaultInterfaces = node.hardware?.interfaces && node.hardware.interfaces.length > 0
    ? node.hardware.interfaces
    : [
        { name: node.interface || 'GigabitEthernet0/0/1', ip_address: node.ip_address, speed_mbps: 1000, duplex: 'full', mtu: 1500, oper_status: 'up' as const, admin_status: 'up' as const, in_octets: 4892010, out_octets: 7892014, in_errors: 0, out_errors: 0 },
        { name: 'GigabitEthernet0/0/2', ip_address: '10.0.1.254', speed_mbps: 1000, duplex: 'full', mtu: 1500, oper_status: 'up' as const, admin_status: 'up' as const, in_octets: 120489, out_octets: 98401, in_errors: 0, out_errors: 0 }
      ];
  const [interfaces, setInterfaces] = useState(defaultInterfaces);

  const handleSave = () => {
    const updated: Node = {
      ...node,
      name,
      ip_address: ipAddress,
      power_state: powerState,
      status: powerState === 'stopped' ? 'stopped' : (powerState === 'paused' ? 'paused' : 'active'),
      zone_id: zoneId || undefined,
      hardware: {
        vcpu_count: vcpu,
        ram_mb: ramMb,
        boot_time_sec: node.hardware?.boot_time_sec || 5,
        cpu_utilization_pct: cpuUsage,
        memory_utilization_pct: memUsage,
        temperature_celsius: tempC,
        interfaces
      }
    };
    onUpdateNode(updated);
    onClose();
  };

  const toggleInterfaceStatus = (index: number) => {
    const next = [...interfaces];
    next[index].oper_status = next[index].oper_status === 'up' ? 'down' : 'up';
    setInterfaces(next);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
      <div className="bg-slate-900 border border-slate-700 rounded-xl shadow-2xl w-full max-w-2xl max-h-[90vh] flex flex-col overflow-hidden text-slate-200">
        
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-slate-950/60">
          <div className="flex items-center gap-3">
            <div className={`p-2 rounded-lg ${
              powerState === 'running' ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' :
              powerState === 'paused' ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30' :
              'bg-slate-800 text-slate-400 border border-slate-700'
            }`}>
              <Power className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-base font-bold text-slate-100">{node.name}</h3>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 border border-slate-700 text-cyan-400 uppercase">
                  {node.type}
                </span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-blue-950 border border-blue-800 text-blue-300">
                  {node.vendor}
                </span>
              </div>
              <p className="text-xs text-slate-400 font-mono mt-0.5">ID: {node.id} &bull; IP: {node.ip_address}</p>
            </div>
          </div>
          <button onClick={onClose} className="p-1 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-lg transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          
          {/* Identity & Network Address */}
          <div className="bg-slate-950/40 border border-slate-800 rounded-lg p-4 grid grid-cols-2 gap-4">
            <div>
              <label className="text-xs font-semibold text-slate-400 block mb-1">
                Node / Host Name
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-slate-100 font-mono focus:border-cyan-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-slate-400 block mb-1">
                Management IP Address
              </label>
              <input
                type="text"
                value={ipAddress}
                onChange={(e) => setIpAddress(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-slate-100 font-mono focus:border-cyan-500 focus:outline-none"
              />
            </div>
          </div>

          {/* Power Controls */}
          <div className="bg-slate-950/40 border border-slate-800 rounded-lg p-4">
            <label className="text-xs font-semibold text-slate-300 uppercase tracking-wider block mb-3">
              Device Power Lifecycle (GNS3 / EVE-NG Mode)
            </label>
            <div className="grid grid-cols-4 gap-3">
              <button
                type="button"
                onClick={() => setPowerState('running')}
                className={`flex items-center justify-center gap-2 py-2 px-3 rounded-lg text-xs font-semibold transition-all ${
                  powerState === 'running'
                    ? 'bg-emerald-600 text-white shadow-lg shadow-emerald-900/40'
                    : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
                }`}
              >
                <Power className="w-3.5 h-3.5" /> Power On
              </button>
              <button
                type="button"
                onClick={() => setPowerState('paused')}
                className={`flex items-center justify-center gap-2 py-2 px-3 rounded-lg text-xs font-semibold transition-all ${
                  powerState === 'paused'
                    ? 'bg-amber-600 text-white shadow-lg shadow-amber-900/40'
                    : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
                }`}
              >
                <AlertTriangle className="w-3.5 h-3.5" /> Pause
              </button>
              <button
                type="button"
                onClick={() => setPowerState('stopped')}
                className={`flex items-center justify-center gap-2 py-2 px-3 rounded-lg text-xs font-semibold transition-all ${
                  powerState === 'stopped'
                    ? 'bg-rose-600 text-white shadow-lg shadow-rose-900/40'
                    : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
                }`}
              >
                <Power className="w-3.5 h-3.5" /> Shutdown
              </button>
              <button
                type="button"
                onClick={() => {
                  setPowerState('stopped');
                  setName(node.type.toUpperCase() + '-DEFAULT');
                }}
                className="flex items-center justify-center gap-2 py-2 px-3 rounded-lg text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-400 transition-colors"
              >
                Wipe Config
              </button>
            </div>
          </div>

          {/* Virtual Hardware Specs (vCPU, RAM, Meters) */}
          <div className="bg-slate-950/40 border border-slate-800 rounded-lg p-4 space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-2">
                <Cpu className="w-4 h-4 text-cyan-400" /> Virtual Hardware Allocation &amp; Compute Specs
              </span>
              <span className="text-xs text-cyan-400 font-mono">{tempC.toFixed(1)}&deg;C Normal</span>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <div className="flex justify-between text-xs text-slate-400 mb-1">
                  <span>vCPU Cores</span>
                  <span className="font-mono text-cyan-400 font-bold">{vcpu} Core(s)</span>
                </div>
                <input
                  type="range"
                  min="1"
                  max="16"
                  value={vcpu}
                  onChange={(e) => setVcpu(parseInt(e.target.value))}
                  className="w-full h-1.5 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-cyan-500"
                />
              </div>

              <div>
                <div className="flex justify-between text-xs text-slate-400 mb-1">
                  <span>Virtual Memory (RAM)</span>
                  <span className="font-mono text-cyan-400 font-bold">{(ramMb / 1024).toFixed(1)} GB</span>
                </div>
                <input
                  type="range"
                  min="1024"
                  max="32768"
                  step="1024"
                  value={ramMb}
                  onChange={(e) => setRamMb(parseInt(e.target.value))}
                  className="w-full h-1.5 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-cyan-500"
                />
              </div>
            </div>

            {/* Live Utilization Meters */}
            <div className="grid grid-cols-2 gap-4 pt-2 border-t border-slate-800">
              <div>
                <div className="flex justify-between text-xs text-slate-400 mb-1">
                  <span>Simulated CPU Load</span>
                  <span className="font-mono text-slate-200">{cpuUsage.toFixed(1)}%</span>
                </div>
                <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                  <div className={`h-full transition-all ${cpuUsage > 80 ? 'bg-rose-500' : 'bg-cyan-500'}`} style={{ width: `${cpuUsage}%` }}></div>
                </div>
              </div>

              <div>
                <div className="flex justify-between text-xs text-slate-400 mb-1">
                  <span>Simulated Memory Load</span>
                  <span className="font-mono text-slate-200">{memUsage.toFixed(1)}%</span>
                </div>
                <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                  <div className={`h-full transition-all ${memUsage > 80 ? 'bg-rose-500' : 'bg-purple-500'}`} style={{ width: `${memUsage}%` }}></div>
                </div>
              </div>
            </div>
          </div>

          {/* Network Interfaces Table */}
          <div className="bg-slate-950/40 border border-slate-800 rounded-lg p-4">
            <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-2 mb-3">
              <Network className="w-4 h-4 text-emerald-400" /> Physical &amp; Logical Network Interfaces
            </span>
            <div className="space-y-2">
              {interfaces.map((intf, idx) => (
                <div key={idx} className="flex items-center justify-between p-2.5 rounded bg-slate-900 border border-slate-800 text-xs">
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => toggleInterfaceStatus(idx)}
                      className={`w-3 h-3 rounded-full cursor-pointer transition-colors ${intf.oper_status === 'up' ? 'bg-emerald-500 shadow-sm shadow-emerald-500' : 'bg-rose-500'}`}
                      title={`Toggle ${intf.name} status`}
                    />
                    <span className="font-mono font-semibold text-slate-200">{intf.name}</span>
                    <span className="text-[10px] text-slate-400 font-mono">({intf.speed_mbps} Mbps)</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="font-mono text-slate-400">{intf.ip_address || 'Unassigned'}</span>
                    <span className={`px-2 py-0.5 rounded text-[10px] uppercase font-mono font-bold ${
                      intf.oper_status === 'up' ? 'bg-emerald-950 text-emerald-300 border border-emerald-800' : 'bg-rose-950 text-rose-300 border border-rose-800'
                    }`}>
                      {intf.oper_status}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Security Zone Assignment */}
          <div className="bg-slate-950/40 border border-slate-800 rounded-lg p-4">
            <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-2 mb-3">
              <Shield className="w-4 h-4 text-purple-400" /> Security Zone Perimeter Association
            </span>
            <select
              value={zoneId}
              onChange={(e) => setZoneId(e.target.value)}
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-cyan-500 font-mono"
            >
              <option value="">(No Explicit Zone - Unrestricted)</option>
              {zones.map((z) => (
                <option key={z.id} value={z.id}>
                  {z.name} [{z.zone_type.toUpperCase()}]
                </option>
              ))}
            </select>
          </div>

        </div>

        {/* Footer Actions */}
        <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-slate-800 bg-slate-950/60">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 rounded-lg text-xs font-semibold text-slate-400 hover:text-slate-200 bg-slate-800 hover:bg-slate-700 transition-colors"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleSave}
            className="flex items-center gap-1.5 px-5 py-2 rounded-lg text-xs font-bold text-white bg-cyan-600 hover:bg-cyan-500 transition-colors shadow-lg shadow-cyan-900/30"
          >
            <Check className="w-4 h-4" /> Save Node Specifications
          </button>
        </div>

      </div>
    </div>
  );
};
