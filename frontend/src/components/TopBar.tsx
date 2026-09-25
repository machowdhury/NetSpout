import React, { useState, useRef, useEffect } from 'react';
import { 
  Play, Pause, Trash2, Download, Activity, Gauge, Network, Layers, 
  Shield, Radio, Power, Zap, Database, Package, Terminal, BookOpen, 
  BarChart3, ChevronDown, Wrench, Check 
} from 'lucide-react';
import type { ScenarioType, EcosystemMode, TelemetryTransportConfig } from '../types/topology';
import { SCENARIOS } from '../presets/defaultTopologies';

interface TopBarProps {
  appMode?: 'workflow' | 'advanced' | 'operations';
  onSelectAppMode?: (mode: 'workflow' | 'advanced' | 'operations') => void;
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
  onOpenSNMPModal: () => void;
  onOpenPipelinesModal: () => void;
  onOpenVendorAddonsModal: () => void;
  onOpenSPLPlayground: () => void;
  onOpenUseCaseRepo: () => void;
  onOpenNocSocMetrics: () => void;
  onPowerAll: (power: 'running' | 'stopped') => void;
  transportConfig?: TelemetryTransportConfig;
}

export const TopBar: React.FC<TopBarProps> = ({
  appMode = 'workflow',
  onSelectAppMode,
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
  onOpenSNMPModal,
  onOpenPipelinesModal,
  onOpenVendorAddonsModal,
  onOpenSPLPlayground,
  onOpenUseCaseRepo,
  onOpenNocSocMetrics,
  onPowerAll,
  transportConfig
}) => {
  const [toolsOpen, setToolsOpen] = useState<boolean>(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setToolsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const filteredScenarios = SCENARIOS.filter(
    (s) => s.ecosystem === ecosystemMode || s.ecosystem === 'both'
  );

  const getScenarioSourcetype = (sc: ScenarioType): string => {
    switch (sc) {
      case 'openconfig_mdt_streaming':
        return 'cisco:ios:mdt:metric';
      case 'cisco_campus_rogue':
        return 'cisco:catalyst:rogue:threat_details';
      case 'cisco_sdwan_brownout':
        return 'cisco:sdwan:linkhealth';
      case 'cisco_aci_microburst':
        return 'cisco:dc:nexus9k:syslog';
      case 'mixed_edge_breach':
        return 'meraki:assurancealerts';
      case 'mixed_sase_degradation':
        return 'zscaler:zia';
      case 'mixed_backbone_optical':
        return 'nokia:sros:optical';
      case 'arch_vpn_remote_workforce':
        return 'cisco:asa / duo:push';
      case 'arch_wlan_meraki_catalyst':
        return 'meraki:accesspoints';
      case 'arch_san_fibre_channel':
        return 'cisco:mds:san:fc';
      case 'arch_nas_storage_cluster':
        return 'netapp:ontap:nas';
      case 'arch_pan_iot_mesh':
        return 'pan:ble:iot:sensor';
      case 'pure_cisco_enterprise':
        return 'cisco:catalyst:networkhealth';
      case 'mixed_vendor_enterprise':
        return 'cisco:ios:syslog';
      default:
        return 'cisco:ios:syslog';
    }
  };

  const activeSourcetype = getScenarioSourcetype(scenario);
  const hecTargetHost = transportConfig?.hec_url 
    ? transportConfig.hec_url.replace(/^https?:\/\//, '').replace(/\/services\/collector$/, '')
    : '127.0.0.1:8888';
  const targetIndex = transportConfig?.hec_index || 'idx_network_ops';
  const currentEps = isRunning ? (1000 / speedMs).toFixed(1) : '0';

  return (
    <header className="h-14 bg-[#111827] border-b border-[#374151] px-3 flex items-center justify-between backdrop-blur select-none z-30 shrink-0 gap-2">
      {/* 1. Left: Brand & Mode Toggle */}
      <div className="flex items-center gap-2 shrink-0">
        <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-cyan-500/10 border border-cyan-500/30 text-cyan-400">
          <Activity className="w-4 h-4 animate-pulse text-cyan-400" />
        </div>
        <div className="flex flex-col">
          <div className="flex items-center gap-1.5">
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-violet-400 via-cyan-400 to-emerald-400 font-black text-sm font-mono tracking-wide">
              NetSpout
            </span>
            <span className="text-[10px] bg-violet-950/80 text-violet-300 px-1.5 py-0.2 rounded border border-violet-700/60 font-mono font-bold">
              v2.0
            </span>
          </div>
          <div className="flex items-center gap-1.5 text-[10px] text-slate-400 font-mono">
            <span className={`inline-block w-1.5 h-1.5 rounded-full ${isConnected ? 'bg-emerald-400 shadow-[0_0_6px_#10B981]' : 'bg-rose-500'}`} />
            <span>{isConnected ? 'ONLINE' : 'OFFLINE'}</span>
            <span className="text-slate-600">·</span>
            <span>Logs: <b className="text-cyan-300">{totalLogs}</b></span>
          </div>
        </div>

        {/* Mode Toggle */}
        <div className="flex items-center bg-slate-900 border border-slate-700/80 rounded-md p-0.5 ml-1">
          <button
            onClick={() => onSelectEcosystemMode('pure_cisco')}
            className={`px-2 py-0.5 text-[11px] font-mono font-bold rounded flex items-center gap-1 transition-all cursor-pointer ${
              ecosystemMode === 'pure_cisco'
                ? 'bg-sky-500 text-slate-950 shadow-[0_0_8px_rgba(14,165,233,0.4)]'
                : 'text-slate-400 hover:text-slate-200'
            }`}
            title="Switch to Cisco-only infrastructure"
          >
            <Network className="w-3 h-3" />
            <span>Cisco</span>
          </button>
          <button
            onClick={() => onSelectEcosystemMode('mixed_vendor')}
            className={`px-2 py-0.5 text-[11px] font-mono font-bold rounded flex items-center gap-1 transition-all cursor-pointer ${
              ecosystemMode === 'mixed_vendor'
                ? 'bg-gradient-to-r from-cyan-500 to-indigo-500 text-slate-950 shadow-[0_0_8px_rgba(6,182,212,0.4)]'
                : 'text-slate-400 hover:text-slate-200'
            }`}
            title="Switch to Heterogeneous Multi-Vendor"
          >
            <Layers className="w-3 h-3" />
            <span>Multi-Vendor</span>
          </button>
        </div>

        {/* Top-Level Navigation Tabs */}
        <div className="flex items-center bg-slate-900 border border-slate-700/80 rounded-lg p-0.5 ml-2">
          <button
            onClick={() => onSelectAppMode && onSelectAppMode('workflow')}
            className={`px-3 py-1 text-xs font-semibold rounded-md transition cursor-pointer ${
              appMode === 'workflow'
                ? 'bg-cyan-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Use Cases (5-Step)
          </button>
          <button
            onClick={() => onSelectAppMode && onSelectAppMode('advanced')}
            className={`px-3 py-1 text-xs font-semibold rounded-md transition cursor-pointer ${
              appMode === 'advanced'
                ? 'bg-cyan-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Canvas Orchestrator
          </button>
          <button
            onClick={() => onSelectAppMode && onSelectAppMode('operations')}
            className={`px-3 py-1 text-xs font-semibold rounded-md transition cursor-pointer ${
              appMode === 'operations'
                ? 'bg-cyan-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Operations
          </button>
        </div>
      </div>

      {/* 2. Center: Scenario, Play/Pause, and Live Active Transmission Telemetry */}
      <div className="flex items-center gap-2 min-w-0">
        <div className="flex items-center gap-1.5 bg-slate-900/90 border border-slate-700/80 px-2 py-1 rounded-lg">
          <select
            value={scenario}
            onChange={(e) => onSelectScenario(e.target.value as ScenarioType)}
            className="bg-slate-950 border border-slate-700 text-slate-200 text-xs rounded px-2 py-0.5 font-mono focus:outline-none focus:border-cyan-500 cursor-pointer max-w-[190px] truncate"
            title="Operational Scenario"
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
          className={`px-2.5 py-1 rounded-lg text-xs font-bold font-mono tracking-wider flex items-center gap-1.5 transition-all shadow cursor-pointer shrink-0 ${
            isRunning
              ? 'bg-amber-500/20 text-amber-300 border border-amber-500/60 shadow-[0_0_10px_rgba(245,158,11,0.2)] hover:bg-amber-500/30'
              : 'bg-emerald-600 hover:bg-emerald-500 text-slate-950 font-black shadow-[0_0_10px_rgba(16,185,129,0.3)]'
          }`}
          title={isRunning ? 'Pause Ingestion' : 'Start Simulation'}
        >
          {isRunning ? (
            <>
              <Pause className="w-3 h-3 fill-current" />
              <span>PAUSE</span>
            </>
          ) : (
            <>
              <Play className="w-3 h-3 fill-current" />
              <span>RESUME</span>
            </>
          )}
        </button>

        {/* Active Transmission Status Display - "If I am sending something it should tell me what it is sending" */}
        <div className="flex items-center gap-1.5 bg-slate-950/90 border border-slate-700/80 px-2.5 py-1 rounded-lg font-mono text-[11px] shadow-inner shrink-0">
          <div className="flex items-center gap-1 shrink-0">
            <span
              className={`inline-block w-2 h-2 rounded-full ${
                isRunning
                  ? 'bg-emerald-400 shadow-[0_0_8px_#34d399] animate-pulse'
                  : 'bg-amber-400 shadow-[0_0_8px_#f59e0b]'
              }`}
            />
            <span className={`font-bold ${isRunning ? 'text-emerald-300' : 'text-amber-300'}`}>
              {isRunning ? 'EMITTING' : 'PAUSED'}
            </span>
          </div>

          <span className="text-slate-600">|</span>

          <div className="flex items-center gap-1 text-slate-300 whitespace-nowrap">
            <span className="text-slate-500">HEC:</span>
            <span className="text-cyan-300 font-semibold">{hecTargetHost}</span>
            <span className="text-slate-500">&rarr;</span>
            <span className="text-emerald-300 font-semibold">{targetIndex}</span>
          </div>

          <span className="text-slate-600">|</span>

          <div className="flex items-center gap-1 whitespace-nowrap">
            <span className="text-amber-300 font-semibold max-w-[130px] truncate" title={activeSourcetype}>
              {activeSourcetype}
            </span>
            <span className="text-cyan-400 font-bold ml-0.5">({currentEps} EPS)</span>
          </div>
        </div>

        {/* Speed Slider */}
        <div className="flex items-center gap-1 bg-slate-900/80 border border-slate-800 px-1.5 py-0.5 rounded-lg shrink-0">
          <Gauge className="w-3 h-3 text-cyan-400 shrink-0" />
          <input
            type="range"
            min="100"
            max="2000"
            step="50"
            value={speedMs}
            onChange={(e) => onChangeSpeed(Number(e.target.value))}
            className="w-12 h-1 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-cyan-400"
            title={`Rate: ${speedMs}ms`}
          />
        </div>
      </div>

      {/* 3. Right: Presets Dropdown & Consolidated Telemetry Tools Menu */}
      <div className="flex items-center gap-2 shrink-0">
        {/* Presets Dropdown */}
        <select
          onChange={(e) => {
            if (e.target.value) {
              onLoadPreset(e.target.value);
              e.target.value = '';
            }
          }}
          defaultValue=""
          className="bg-slate-900 border border-slate-700 text-slate-300 text-xs rounded-lg px-2 py-1 font-mono focus:outline-none focus:border-cyan-500 cursor-pointer max-w-[130px] truncate"
          title="Load Predefined Topologies"
        >
          <option value="" disabled>Presets...</option>
          <optgroup label="Unified Topologies">
            <option value="pure_cisco">Pure Cisco Fabric</option>
            <option value="openconfig_core">OpenConfig MDT</option>
            <option value="secure">Secure Perimeter</option>
            <option value="bypassed">Bypassed (Breach)</option>
            <option value="lateral">Flat Subnet</option>
          </optgroup>
          <optgroup label="11 Architectures">
            <option value="pan">PAN: IoT Sensor</option>
            <option value="lan">LAN: Campus Access</option>
            <option value="wlan">WLAN: 9800 & Meraki</option>
            <option value="san">SAN: MDS 9700 FC</option>
            <option value="nas">NAS: NetApp ONTAP</option>
            <option value="vpn">VPN: Duo MFA</option>
          </optgroup>
          <optgroup label="Operational Modes">
            <option value="cisco_campus">Campus Rogue AP</option>
            <option value="cisco_sdwan">SD-WAN Brownout</option>
            <option value="cisco_aci">DC ACI Microburst</option>
            <option value="mixed_edge">Edge Breach</option>
            <option value="mixed_sase">SASE Degradation</option>
            <option value="mixed_optical">Optical Shift</option>
          </optgroup>
        </select>

        {/* Consolidated Telemetry Tools ▾ Dropdown */}
        <div className="relative" ref={dropdownRef}>
          <button
            onClick={() => setToolsOpen(!toolsOpen)}
            className={`px-2.5 py-1 rounded-lg border text-xs font-mono font-bold flex items-center gap-1.5 transition-all cursor-pointer ${
              toolsOpen
                ? 'bg-cyan-950/90 text-cyan-300 border-cyan-500 shadow-[0_0_12px_rgba(6,182,212,0.3)]'
                : 'bg-slate-900 hover:bg-slate-800 text-slate-200 border-slate-700 hover:text-cyan-300'
            }`}
            title="Access Network Telemetry Tools, Transports, Fault Injection, and Modals"
          >
            <Wrench className="w-3.5 h-3.5 text-cyan-400" />
            <span>Telemetry Tools</span>
            <ChevronDown className={`w-3.5 h-3.5 text-slate-400 transition-transform duration-200 ${toolsOpen ? 'rotate-180 text-cyan-300' : ''}`} />
          </button>

          {/* Tools Dropdown Menu (Consolidating all 10 tools + Power + Export + Clear) */}
          {toolsOpen && (
            <div className="absolute right-0 top-full mt-1.5 w-84 bg-slate-900/98 border border-slate-700 rounded-xl shadow-2xl z-50 py-1.5 text-xs font-mono backdrop-blur-xl animate-in fade-in slide-in-from-top-2 duration-150 divide-y divide-slate-800/80 max-h-[85vh] overflow-y-auto">
              <div className="px-3 py-1.5 text-[10px] font-bold text-slate-400 uppercase tracking-wider flex items-center justify-between">
                <span>Ingestion & Orchestration</span>
                <span className="text-cyan-400 font-mono">10 SUITES</span>
              </div>

              <div className="py-1">
                <button
                  onClick={() => { setToolsOpen(false); onOpenSyslogModal(); }}
                  className="w-full px-3 py-2 text-left hover:bg-slate-800/90 flex items-center justify-between text-slate-200 hover:text-cyan-300 transition-colors cursor-pointer group"
                >
                  <div className="flex items-center gap-2.5">
                    <Radio className="w-4 h-4 text-emerald-400 group-hover:scale-110 transition-transform" />
                    <div>
                      <div className="font-bold">Dual Transport (HEC & Syslog)</div>
                      <div className="text-[10px] text-slate-400">Configure Splunk HEC & UDP/TCP 514</div>
                    </div>
                  </div>
                  <span className="text-[10px] bg-emerald-950/80 text-emerald-400 px-1.5 py-0.5 rounded border border-emerald-800">HEC+UDP</span>
                </button>

                <button
                  onClick={() => { setToolsOpen(false); onOpenFaultModal(); }}
                  className="w-full px-3 py-2 text-left hover:bg-slate-800/90 flex items-center justify-between text-slate-200 hover:text-amber-300 transition-colors cursor-pointer group"
                >
                  <div className="flex items-center gap-2.5">
                    <Zap className="w-4 h-4 text-amber-400 group-hover:scale-110 transition-transform" />
                    <div>
                      <div className="font-bold">Fault Injection Engine</div>
                      <div className="text-[10px] text-slate-400">Link cuts, BGP flaps & microbursts</div>
                    </div>
                  </div>
                  <span className="text-[10px] bg-amber-950/80 text-amber-400 px-1.5 py-0.5 rounded border border-amber-800">CHAOS</span>
                </button>

                <button
                  onClick={() => { setToolsOpen(false); onOpenOpenConfigModal(); }}
                  className="w-full px-3 py-2 text-left hover:bg-slate-800/90 flex items-center justify-between text-slate-200 hover:text-cyan-300 transition-colors cursor-pointer group"
                >
                  <div className="flex items-center gap-2.5">
                    <Database className="w-4 h-4 text-cyan-400 group-hover:scale-110 transition-transform" />
                    <div>
                      <div className="font-bold">OpenConfig & gNMI Telemetry</div>
                      <div className="text-[10px] text-slate-400">YANG operational state tree streaming</div>
                    </div>
                  </div>
                  <span className="text-[10px] bg-cyan-950/80 text-cyan-400 px-1.5 py-0.5 rounded border border-cyan-800">gNMI</span>
                </button>

                <button
                  onClick={() => { setToolsOpen(false); onOpenSNMPModal(); }}
                  className="w-full px-3 py-2 text-left hover:bg-slate-800/90 flex items-center justify-between text-slate-200 hover:text-emerald-300 transition-colors cursor-pointer group"
                >
                  <div className="flex items-center gap-2.5">
                    <Activity className="w-4 h-4 text-emerald-400 group-hover:scale-110 transition-transform" />
                    <div>
                      <div className="font-bold">SC4SNMP (330+ MIBs)</div>
                      <div className="text-[10px] text-slate-400">MIB catalog, polling walks & traps</div>
                    </div>
                  </div>
                  <span className="text-[10px] bg-emerald-950/80 text-emerald-400 px-1.5 py-0.5 rounded border border-emerald-800">330+</span>
                </button>

                <button
                  onClick={() => { setToolsOpen(false); onOpenPipelinesModal(); }}
                  className="w-full px-3 py-2 text-left hover:bg-slate-800/90 flex items-center justify-between text-slate-200 hover:text-violet-300 transition-colors cursor-pointer group"
                >
                  <div className="flex items-center gap-2.5">
                    <Radio className="w-4 h-4 text-violet-400 group-hover:scale-110 transition-transform" />
                    <div>
                      <div className="font-bold">Universal 4-Way Pipelines</div>
                      <div className="text-[10px] text-slate-400">Splunk HEC, OTel, Telegraf, Syslog</div>
                    </div>
                  </div>
                  <span className="text-[10px] bg-violet-950/80 text-violet-400 px-1.5 py-0.5 rounded border border-violet-800">MATRIX</span>
                </button>
              </div>

              <div className="py-1">
                <button
                  onClick={() => { setToolsOpen(false); onOpenVendorAddonsModal(); }}
                  className="w-full px-3 py-2 text-left hover:bg-slate-800/90 flex items-center justify-between text-slate-200 hover:text-blue-300 transition-colors cursor-pointer group"
                >
                  <div className="flex items-center gap-2.5">
                    <Package className="w-4 h-4 text-blue-400 group-hover:scale-110 transition-transform" />
                    <div>
                      <div className="font-bold">Vendor Technology Add-ons (TAs)</div>
                      <div className="text-[10px] text-slate-400">Cisco, Palo Alto, Meraki, Arista TAs</div>
                    </div>
                  </div>
                  <span className="text-[10px] bg-blue-950/80 text-blue-400 px-1.5 py-0.5 rounded border border-blue-800">TAs</span>
                </button>

                <button
                  onClick={() => { setToolsOpen(false); onOpenSPLPlayground(); }}
                  className="w-full px-3 py-2 text-left hover:bg-slate-800/90 flex items-center justify-between text-slate-200 hover:text-cyan-300 transition-colors cursor-pointer group"
                >
                  <div className="flex items-center gap-2.5">
                    <Terminal className="w-4 h-4 text-cyan-400 group-hover:scale-110 transition-transform" />
                    <div>
                      <div className="font-bold">Interactive SPL Playground</div>
                      <div className="text-[10px] text-slate-400">Live search against Splunk Enterprise</div>
                    </div>
                  </div>
                  <span className="text-[10px] bg-cyan-950/80 text-cyan-300 px-1.5 py-0.5 rounded border border-cyan-800">LIVE SPL</span>
                </button>

                <button
                  onClick={() => { setToolsOpen(false); onOpenUseCaseRepo(); }}
                  className="w-full px-3 py-2 text-left hover:bg-slate-800/90 flex items-center justify-between text-slate-200 hover:text-emerald-300 transition-colors cursor-pointer group"
                >
                  <div className="flex items-center gap-2.5">
                    <BookOpen className="w-4 h-4 text-emerald-400 group-hover:scale-110 transition-transform" />
                    <div>
                      <div className="font-bold">NOC & SOC Use Cases</div>
                      <div className="text-[10px] text-slate-400">Pre-built validation test harness</div>
                    </div>
                  </div>
                  <span className="text-[10px] bg-emerald-950/80 text-emerald-400 px-1.5 py-0.5 rounded border border-emerald-800">TESTS</span>
                </button>

                <button
                  onClick={() => { setToolsOpen(false); onOpenNocSocMetrics(); }}
                  className="w-full px-3 py-2 text-left hover:bg-slate-800/90 flex items-center justify-between text-slate-200 hover:text-cyan-300 transition-colors cursor-pointer group"
                >
                  <div className="flex items-center gap-2.5">
                    <BarChart3 className="w-4 h-4 text-cyan-400 group-hover:scale-110 transition-transform" />
                    <div>
                      <div className="font-bold">NOC & SOC Metric Telemetry</div>
                      <div className="text-[10px] text-slate-400">MOS, Goodput, Optical dBm & DDI</div>
                    </div>
                  </div>
                  <span className="text-[10px] bg-cyan-950/80 text-cyan-300 px-1.5 py-0.5 rounded border border-cyan-800">METRICS</span>
                </button>

                <button
                  onClick={() => { setToolsOpen(false); onToggleZones(); }}
                  className="w-full px-3 py-2 text-left hover:bg-slate-800/90 flex items-center justify-between text-slate-200 hover:text-cyan-300 transition-colors cursor-pointer group"
                >
                  <div className="flex items-center gap-2.5">
                    <Shield className="w-4 h-4 text-cyan-400 group-hover:scale-110 transition-transform" />
                    <div>
                      <div className="font-bold">Security Zone Overlays</div>
                      <div className="text-[10px] text-slate-400">Toggle DMZ, Edge & Internal overlays</div>
                    </div>
                  </div>
                  {showZones ? (
                    <span className="text-[10px] bg-cyan-900/60 text-cyan-300 px-1.5 py-0.5 rounded border border-cyan-700 flex items-center gap-1 font-bold">
                      <Check className="w-3 h-3" /> ON
                    </span>
                  ) : (
                    <span className="text-[10px] bg-slate-800 text-slate-400 px-1.5 py-0.5 rounded border border-slate-700">
                      OFF
                    </span>
                  )}
                </button>
              </div>

              {/* Section 3: Topology Management, Power & Export */}
              <div className="py-1">
                <div className="px-3 py-1 text-[10px] font-bold text-slate-500 uppercase tracking-wider">
                  Node & Data Operations
                </div>
                <div className="flex items-center justify-between px-3 py-1.5 hover:bg-slate-800/90">
                  <div className="flex items-center gap-2 text-slate-200">
                    <Power className="w-3.5 h-3.5 text-emerald-400" />
                    <span>Power All Nodes</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <button
                      onClick={() => onPowerAll('running')}
                      className="px-2 py-0.5 text-[10px] bg-emerald-950 text-emerald-300 border border-emerald-800 rounded hover:bg-emerald-900 cursor-pointer"
                    >
                      Power ON
                    </button>
                    <button
                      onClick={() => onPowerAll('stopped')}
                      className="px-2 py-0.5 text-[10px] bg-rose-950 text-rose-300 border border-rose-800 rounded hover:bg-rose-900 cursor-pointer"
                    >
                      Halt
                    </button>
                  </div>
                </div>

                <div className="flex items-center justify-between px-3 py-1.5 hover:bg-slate-800/90">
                  <div className="flex items-center gap-2 text-slate-200">
                    <Download className="w-3.5 h-3.5 text-cyan-400" />
                    <span>Export Telemetry</span>
                  </div>
                  <div className="flex items-center gap-1 font-mono text-[10px]">
                    <button onClick={() => onExportLogs('csv')} className="px-1.5 py-0.5 bg-slate-800 text-cyan-300 rounded hover:bg-slate-700 cursor-pointer">CSV</button>
                    <button onClick={() => onExportLogs('json')} className="px-1.5 py-0.5 bg-slate-800 text-cyan-300 rounded hover:bg-slate-700 cursor-pointer">JSON</button>
                    <button onClick={() => onExportLogs('raw')} className="px-1.5 py-0.5 bg-slate-800 text-cyan-300 rounded hover:bg-slate-700 cursor-pointer">RAW</button>
                  </div>
                </div>

                <button
                  onClick={() => { setToolsOpen(false); onClearCanvas(); }}
                  className="w-full px-3 py-1.5 text-left hover:bg-rose-950/40 text-rose-300 hover:text-rose-200 flex items-center gap-2 transition-colors cursor-pointer"
                >
                  <Trash2 className="w-3.5 h-3.5 text-rose-400" />
                  <span>Clear Canvas Topology</span>
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};
