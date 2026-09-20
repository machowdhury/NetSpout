import React from 'react';
import { Play, Pause, Trash2, Download, Activity, Gauge, Network, Layers, Shield, Radio, Power, Zap, Database } from 'lucide-react';
import type { ScenarioType, EcosystemMode } from '../types/topology';
import { SCENARIOS } from '../presets/defaultTopologies';

interface TopBarProps {
  ecosystemMode: EcosystemMode;
  onSelectEcosystemMode: (mode: EcosystemMode) => void;
  scenario: ScenarioType;
  onSelectScenario: (s: ScenarioType) => void;
  isRunning: boolean;
  onTogglePlay: () => void;
  speedMs: number;
  onChangeSpeed: (ms: number) => void;
  onClearCanvas: () => void;
  onLoadPreset: (presetId: string) => void;
  onExportLogs: (format: 'raw' | 'json' | 'csv') => void;
  isConnected: boolean;
  totalLogs: number;
  showZones: boolean;
  onToggleZones: () => void;
  onOpenSyslogModal: () => void;
  onOpenFaultModal: () => void;
  onOpenOpenConfigModal: () => void;
  onPowerAll: (power: 'running' | 'stopped') => void;
}

export const TopBar: React.FC<TopBarProps> = ({
  ecosystemMode,
  onSelectEcosystemMode,
  scenario,
  onSelectScenario,
  isRunning,
  onTogglePlay,
  speedMs,
  onChangeSpeed,
  onClearCanvas,
  onLoadPreset,
  onExportLogs,
  isConnected,
  totalLogs,
  showZones,
  onToggleZones,
  onOpenSyslogModal,
  onOpenFaultModal,
  onOpenOpenConfigModal,
  onPowerAll
}) => {
  const filteredScenarios = SCENARIOS.filter(
    (s) => s.ecosystem === ecosystemMode || s.ecosystem === 'both'
  );

  return (
    <header className="h-16 bg-[#1F2937] border-b border-[#374151] px-4 flex items-center justify-between backdrop-blur select-none z-30 shrink-0 gap-3">
      {/* Left: Brand & Mode Toggle */}
      <div className="flex items-center gap-3 shrink-0">
        <div className="flex items-center justify-center w-9 h-9 rounded-lg bg-cyan-500/10 border border-cyan-500/30 text-cyan-400">
          <Activity className="w-5 h-5 animate-pulse text-cyan-400" />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-sm font-black tracking-wider text-slate-100 uppercase font-mono flex items-center gap-1.5">
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-violet-400 via-cyan-400 to-emerald-400 font-black text-base">NetSpout</span>
              <span className="text-slate-400 text-xs font-normal">NOC Canvas</span>
            </h1>
            <span className="text-[10px] bg-violet-950/80 text-violet-300 px-2 py-0.5 rounded border border-violet-700/60 font-mono font-bold">
              SPLUNK NATIVE v2.0
            </span>
          </div>
          <div className="flex items-center gap-2 text-[11px] text-slate-400 font-mono">
            <span
              className={`inline-block w-2 h-2 rounded-full ${
                isConnected ? 'bg-[#10B981] shadow-[0_0_8px_#10B981]' : 'bg-[#EF4444] shadow-[0_0_8px_#EF4444]'
              }`}
            />
            <span>{isConnected ? 'LIVE WS CONNECTED' : 'OFFLINE'}</span>
            <span className="text-slate-600">|</span>
            <span>Logged: <b className="text-cyan-400">{totalLogs}</b></span>
          </div>
        </div>

        {/* Dual Ecosystem Mode Toggle */}
        <div className="flex items-center bg-slate-900 border border-slate-700/80 rounded-lg p-0.5 ml-2">
          <button
            onClick={() => onSelectEcosystemMode('pure_cisco')}
            className={`px-2.5 py-1 text-xs font-mono font-bold rounded-md flex items-center gap-1.5 transition-all cursor-pointer ${
              ecosystemMode === 'pure_cisco'
                ? 'bg-sky-500 text-slate-950 shadow-[0_0_12px_rgba(14,165,233,0.4)]'
                : 'text-slate-400 hover:text-slate-200'
            }`}
            title="Switch to Cisco-only infrastructure (Catalyst, Nexus, ACI, SD-WAN, ISE, ThousandEyes)"
          >
            <Network className="w-3.5 h-3.5" />
            <span>Pure Cisco</span>
          </button>
          <button
            onClick={() => onSelectEcosystemMode('mixed_vendor')}
            className={`px-2.5 py-1 text-xs font-mono font-bold rounded-md flex items-center gap-1.5 transition-all cursor-pointer ${
              ecosystemMode === 'mixed_vendor'
                ? 'bg-gradient-to-r from-cyan-500 to-indigo-500 text-slate-950 shadow-[0_0_12px_rgba(6,182,212,0.4)]'
                : 'text-slate-400 hover:text-slate-200'
            }`}
            title="Switch to heterogeneous enterprise stack (Cisco, Meraki, Palo Alto, Arista, Juniper, Nokia, Zscaler)"
          >
            <Layers className="w-3.5 h-3.5" />
            <span>Mixed-Vendor Enterprise</span>
          </button>
        </div>
      </div>

      {/* Center: Scenario Selector & Play / Pause */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2 bg-slate-900/90 border border-slate-700/80 px-2.5 py-1.5 rounded-lg shadow-inner">
          <label className="text-xs font-semibold text-slate-400 whitespace-nowrap">
            Scenario:
          </label>
          <select
            value={scenario}
            onChange={(e) => onSelectScenario(e.target.value as ScenarioType)}
            className="bg-slate-950 border border-slate-700 text-slate-200 text-xs rounded px-2.5 py-1 font-mono focus:outline-none focus:border-cyan-500 cursor-pointer max-w-[280px] truncate"
          >
            {filteredScenarios.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
        </div>

        {/* Global Play / Pause */}
        <button
          onClick={onTogglePlay}
          className={`px-4 py-2 rounded-lg text-xs font-bold font-mono tracking-wider flex items-center gap-2 transition-all shadow-lg cursor-pointer ${
            isRunning
              ? 'bg-amber-500/20 text-amber-300 border border-amber-500/60 shadow-[0_0_15px_rgba(245,158,11,0.25)] hover:bg-amber-500/30'
              : 'bg-emerald-600 hover:bg-emerald-500 text-slate-950 font-black shadow-[0_0_15px_rgba(16,185,129,0.3)]'
          }`}
          title={isRunning ? 'Pause Event Generation' : 'Start Real-time Simulation'}
        >
          {isRunning ? (
            <>
              <Pause className="w-4 h-4 fill-current" />
              <span>PAUSE</span>
            </>
          ) : (
            <>
              <Play className="w-4 h-4 fill-current" />
              <span>START SIMULATION</span>
            </>
          )}
        </button>

        {/* Tick Rate Speed Slider */}
        <div className="flex items-center gap-2 bg-slate-900/80 border border-slate-800 px-2.5 py-1 rounded-lg">
          <Gauge className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
          <div className="flex flex-col">
            <div className="flex items-center justify-between text-[10px] font-mono text-slate-400 gap-2">
              <span>Tick Rate:</span>
              <span className="text-cyan-300 font-bold">{speedMs}ms ({(1000 / speedMs).toFixed(1)}/s)</span>
            </div>
            <input
              type="range"
              min="100"
              max="2000"
              step="50"
              value={speedMs}
              onChange={(e) => onChangeSpeed(Number(e.target.value))}
              className="w-24 h-1 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-cyan-400"
              title="Adjust simulation frequency between 100ms and 2000ms"
            />
          </div>
        </div>
      </div>

      {/* Right: Presets, Zones, Dual Transport, Power, Clear, Export Actions */}
      <div className="flex items-center gap-2">
        {/* Security Zones Toggle */}
        <button
          onClick={onToggleZones}
          className={`px-2.5 py-1.5 rounded-lg border text-xs font-mono font-bold flex items-center gap-1.5 transition-all cursor-pointer ${
            showZones
              ? 'bg-cyan-950/80 text-cyan-300 border-cyan-600 shadow-[0_0_10px_rgba(6,182,212,0.25)]'
              : 'bg-slate-900 text-slate-400 border-slate-700 hover:text-slate-200'
          }`}
          title={showZones ? 'Hide Security Zone Overlays' : 'Display Security Zone Overlays (DMZ, Internal, Edge)'}
        >
          <Shield className="w-3.5 h-3.5 text-cyan-400" />
          <span>Zones</span>
        </button>

        {/* Dual Transport & Direct Syslog Modal Trigger */}
        <button
          onClick={onOpenSyslogModal}
          className="px-2.5 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-300 hover:text-cyan-300 border border-slate-700 text-xs font-mono font-bold flex items-center gap-1.5 transition-all cursor-pointer"
          title="Configure Splunk HEC & Direct Syslog UDP/TCP Port 514 Destinations"
        >
          <Radio className="w-3.5 h-3.5 text-emerald-400" />
          <span>Dual Transport</span>
        </button>

        {/* Dynamic Fault Injection Modal Trigger */}
        <button
          onClick={onOpenFaultModal}
          className="px-2.5 py-1.5 rounded-lg bg-amber-950/60 hover:bg-amber-900/60 text-amber-300 hover:text-amber-200 border border-amber-600/60 text-xs font-mono font-bold flex items-center gap-1.5 transition-all cursor-pointer shadow-[0_0_10px_rgba(245,158,11,0.2)]"
          title="Dynamic Fault & Failure Injection Engine (Link Cuts, BGP Flaps, Resource Exhaustion)"
        >
          <Zap className="w-3.5 h-3.5 text-amber-400" />
          <span>Fault Inject</span>
        </button>

        {/* OpenConfig & gNMI Telemetry Modal Trigger */}
        <button
          onClick={onOpenOpenConfigModal}
          className="px-2.5 py-1.5 rounded-lg bg-cyan-950/60 hover:bg-cyan-900/60 text-cyan-300 hover:text-cyan-200 border border-cyan-600/60 text-xs font-mono font-bold flex items-center gap-1.5 transition-all cursor-pointer shadow-[0_0_10px_rgba(6,182,212,0.2)]"
          title="OpenConfig YANG Operational State Tree & gNMI Telemetry Streaming"
        >
          <Database className="w-3.5 h-3.5 text-cyan-400" />
          <span>OpenConfig / gNMI</span>
        </button>

        {/* Global Node Power Controls */}
        <div className="flex items-center bg-slate-900 border border-slate-700 rounded-lg p-0.5">
          <button
            onClick={() => onPowerAll('running')}
            className="px-2 py-1 text-[11px] font-mono text-emerald-400 hover:bg-emerald-950/60 rounded flex items-center gap-1 transition-colors cursor-pointer"
            title="Power ON all virtual network nodes"
          >
            <Power className="w-3 h-3 text-emerald-400" />
            <span>Power All</span>
          </button>
          <button
            onClick={() => onPowerAll('stopped')}
            className="px-2 py-1 text-[11px] font-mono text-slate-400 hover:text-rose-400 hover:bg-rose-950/40 rounded flex items-center gap-1 transition-colors cursor-pointer"
            title="Halt / Power OFF all virtual network nodes"
          >
            <span>Halt All</span>
          </button>
        </div>

        {/* Presets Dropdown */}
        <div className="relative">
          <select
            onChange={(e) => {
              if (e.target.value) {
                onLoadPreset(e.target.value);
                e.target.value = '';
              }
            }}
            defaultValue=""
            className="bg-slate-900 border border-slate-700 text-slate-300 text-xs rounded-lg px-2.5 py-1.5 font-mono focus:outline-none focus:border-cyan-500 cursor-pointer max-w-[190px] truncate"
            title="Load Predefined Topologies"
          >
            <option value="" disabled>
              Topology Presets...
            </option>
            <optgroup label="Baseline Topologies">
              <option value="secure">Standard Secure Perimeter</option>
              <option value="bypassed">Bypassed Firewall (Breach)</option>
              <option value="lateral">Flat Subnet (Lateral Ransomware)</option>
            </optgroup>
            <optgroup label="Mode A: Pure Cisco Architecture">
              <option value="cisco_campus">Mode A1: Campus Core Rogue AP & ISE</option>
              <option value="cisco_sdwan">Mode A2: SD-WAN Brownout & Failover</option>
              <option value="cisco_aci">Mode A3: DC ACI Ingress Microburst</option>
            </optgroup>
            <optgroup label="Mode B: Mixed-Vendor Infrastructure">
              <option value="mixed_edge">Mode B1: Edge Breach (Meraki-PA-Catalyst)</option>
              <option value="mixed_sase">Mode B2: SASE Cloud Degradation (Zscaler-PA)</option>
              <option value="mixed_optical">Mode B3: MPLS Optical Carrier Shift (Nokia-Juniper)</option>
            </optgroup>
            <optgroup label="Mode C: OpenConfig Model-Driven Telemetry">
              <option value="openconfig_core">Mode C1: OpenConfig MDT Core Fabric</option>
            </optgroup>
          </select>
        </div>

        {/* Clear Canvas */}
        <button
          onClick={onClearCanvas}
          className="p-2 text-slate-400 hover:text-red-400 hover:bg-slate-900 border border-slate-800 rounded-lg transition-colors cursor-pointer"
          title="Clear Canvas (Remove all nodes and links)"
        >
          <Trash2 className="w-4 h-4" />
        </button>

        {/* Export Logs Tri-Format */}
        <div className="flex items-center bg-slate-900 border border-slate-700 rounded-lg overflow-hidden">
          <button
            onClick={() => onExportLogs('csv')}
            className="px-2.5 py-1.5 hover:bg-slate-800 text-slate-200 text-xs flex items-center gap-1 font-mono cursor-pointer transition-colors border-r border-slate-800"
            title="Export as RFC4180 CSV with Splunk CIM attributes"
          >
            <Download className="w-3 h-3 text-cyan-400" />
            <span>CSV</span>
          </button>
          <button
            onClick={() => onExportLogs('json')}
            className="px-2.5 py-1.5 hover:bg-slate-800 text-slate-300 hover:text-cyan-300 text-xs font-mono cursor-pointer transition-colors border-r border-slate-800"
            title="Export as JSON Array"
          >
            JSON
          </button>
          <button
            onClick={() => onExportLogs('raw')}
            className="px-2.5 py-1.5 hover:bg-slate-800 text-slate-400 hover:text-cyan-300 text-xs font-mono cursor-pointer transition-colors"
            title="Export Raw Splunk Key-Value (.log)"
          >
            RAW
          </button>
        </div>
      </div>
    </header>
  );
};

