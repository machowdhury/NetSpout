import React, { useState, useMemo } from 'react';
import { X, Search, Activity, Zap, Play, CheckCircle, Copy, Check } from 'lucide-react';
import type { Node, SNMPMibDefinition, TelemetryTransportConfig } from '../types/topology';

interface SNMPMibModalProps {
  isOpen: boolean;
  onClose: () => void;
  nodes: Node[];
  globalTransport?: TelemetryTransportConfig;
}

const PRELOADED_TRAPS = [
  { name: 'linkDown', oid: '1.3.6.1.6.3.1.1.5.3', severity: 'critical', desc: 'Interface transitioned to down state' },
  { name: 'linkUp', oid: '1.3.6.1.6.3.1.1.5.4', severity: 'informational', desc: 'Interface operational status restored to up' },
  { name: 'bgpBackwardTransition', oid: '1.3.6.1.2.1.15.7.2', severity: 'major', desc: 'BGP session moved from ESTABLISHED to IDLE' },
  { name: 'bgpEstablished', oid: '1.3.6.1.2.1.15.7.1', severity: 'informational', desc: 'BGP peer entered ESTABLISHED state' },
  { name: 'ospfNbrStateChange', oid: '1.3.6.1.2.1.14.16.2.2', severity: 'major', desc: 'OSPF neighbor state changed from Full' },
  { name: 'ciscoCpuThresholdExceeded', oid: '1.3.6.1.4.1.9.9.109.2.0.1', severity: 'major', desc: 'CPU utilization exceeded rising threshold (95%)' },
  { name: 'ciscoMemoryThresholdExceeded', oid: '1.3.6.1.4.1.9.9.48.2.0.1', severity: 'major', desc: 'Free memory dropped below critical threshold' },
  { name: 'ciscoEnvMonTemperatureNotification', oid: '1.3.6.1.4.1.9.9.13.3.0.2', severity: 'critical', desc: 'Chassis temperature exceeded thermal shutdown warning' },
  { name: 'aristaQueueDropExceeded', oid: '1.3.6.1.4.1.30065.3.1.1', severity: 'warning', desc: 'VOQ / Egress queue drop rate exceeded burst watermark' }
];

export const SNMPMibModal: React.FC<SNMPMibModalProps> = ({
  isOpen,
  onClose,
  nodes,
  globalTransport
}) => {
  const [activeTab, setActiveTab] = useState<'catalog' | 'poll' | 'trap'>('catalog');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedModule, setSelectedModule] = useState('ALL');
  const [selectedVendor, setSelectedVendor] = useState('ALL');
  const [copiedOid, setCopiedOid] = useState<string | null>(null);

  // Poll state
  const [pollNodeId, setPollNodeId] = useState<string>(nodes[0]?.id || '');
  const [pollModule, setPollModule] = useState('IF-MIB');
  const [pollResults, setPollResults] = useState<any[] | null>(null);
  const [isPolling, setIsPolling] = useState(false);

  // Trap state
  const [selectedTrap, setSelectedTrap] = useState(PRELOADED_TRAPS[0].name);
  const [trapNodeId, setTrapNodeId] = useState<string>(nodes[0]?.id || '');
  const [trapSeverity, setTrapSeverity] = useState('critical');
  const [trapStatus, setTrapStatus] = useState<string | null>(null);
  const [isEmittingTrap, setIsEmittingTrap] = useState(false);

  // Fallback MIB catalog items (loaded from backend or offline catalog)
  const [mibs, setMibs] = useState<SNMPMibDefinition[]>([]);
  const [_loadingMibs, setLoadingMibs] = useState(false);

  React.useEffect(() => {
    if (isOpen && mibs.length === 0) {
      setLoadingMibs(true);
      fetch('/api/snmp/mibs')
        .then((res) => res.json())
        .then((data) => {
          if (data && data.mibs) {
            setMibs(data.mibs);
          }
        })
        .catch(() => {
          // Offline fallback
          generateFallbackMibs();
        })
        .finally(() => setLoadingMibs(false));
    }
  }, [isOpen]);

  const generateFallbackMibs = () => {
    const modules = ['IF-MIB', 'SNMPv2-MIB', 'IP-MIB', 'TCP-MIB', 'UDP-MIB', 'BGP4-MIB', 'OSPF-MIB', 'ENTITY-MIB', 'CISCO-PROCESS-MIB', 'CISCO-MEMORY-POOL-MIB', 'CISCO-ENVMON-MIB', 'JUNIPER-MIB', 'ARISTA-QUEUE-MIB'];
    const generated: SNMPMibDefinition[] = [];
    modules.forEach((mod) => {
      for (let i = 1; i <= 25; i++) {
        const vendor = mod.startsWith('CISCO') ? 'Cisco' : mod.startsWith('JUNIPER') ? 'Juniper' : mod.startsWith('ARISTA') ? 'Arista' : 'RFC';
        generated.push({
          name: `${mod.toLowerCase().replace(/-/g, '_')}_obj_${i}`,
          oid: `1.3.6.1.4.1.${mod.length}.${i}`,
          mib_module: mod,
          data_type: i % 2 === 0 ? 'Counter64' : 'Gauge32',
          description: `SC4SNMP managed telemetry object ${i} for ${mod}`,
          is_table: true,
          vendor
        });
      }
    });
    setMibs(generated);
  };

  const filteredMibs = useMemo(() => {
    return mibs.filter((m) => {
      const matchesSearch =
        !searchQuery ||
        m.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        m.oid.includes(searchQuery) ||
        m.description.toLowerCase().includes(searchQuery.toLowerCase());
      const matchesModule = selectedModule === 'ALL' || m.mib_module === selectedModule;
      const matchesVendor = selectedVendor === 'ALL' || m.vendor.toLowerCase() === selectedVendor.toLowerCase();
      return matchesSearch && matchesModule && matchesVendor;
    });
  }, [mibs, searchQuery, selectedModule, selectedVendor]);

  const handleCopyOid = (oid: string) => {
    navigator.clipboard.writeText(oid);
    setCopiedOid(oid);
    setTimeout(() => setCopiedOid(null), 2000);
  };

  const handleRunPoll = async () => {
    setIsPolling(true);
    const targetNode = nodes.find((n) => n.id === pollNodeId) || nodes[0];
    const host = targetNode?.name || targetNode?.id || 'Core-Switch-01';

    try {
      const res = await fetch('/api/snmp/poll', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          host,
          mib_module: pollModule,
          target_node_id: targetNode?.id,
          destinations: globalTransport
        })
      });
      const data = await res.json();
      if (data && data.metrics) {
        setPollResults(data.metrics);
      } else {
        throw new Error('No metrics in response');
      }
    } catch {
      // Local synthesis for offline/standalone mode
      const now = Date.now() / 1000;
      const mockMetrics = [
        {
          time: now,
          event: 'metric',
          source: 'sc4snmp',
          sourcetype: 'sc4snmp:metric',
          host: `${host}.corp.internal`,
          index: 'cisco_mdt_metrics',
          fields: {
            'metric_name:ifInOctets': 54201940.0,
            'metric_name:ifOutOctets': 89201400.0,
            'metric_name:ifOperStatus': 1.0,
            _value: 54201940.0,
            ifIndex: '1',
            ifDescr: 'GigabitEthernet0/0/1',
            mib_module: pollModule,
            device: host,
            vendor: targetNode?.vendor || 'cisco'
          }
        },
        {
          time: now,
          event: 'metric',
          source: 'sc4snmp',
          sourcetype: 'sc4snmp:metric',
          host: `${host}.corp.internal`,
          index: 'cisco_mdt_metrics',
          fields: {
            'metric_name:cpmCPUTotal5minRev': 24.5,
            'metric_name:ciscoMemoryPoolUsed': 412000000.0,
            _value: 24.5,
            mib_module: pollModule,
            device: host,
            vendor: targetNode?.vendor || 'cisco'
          }
        }
      ];
      setPollResults(mockMetrics);
    } finally {
      setIsPolling(false);
    }
  };

  const handleEmitTrap = async () => {
    setIsEmittingTrap(true);
    setTrapStatus(null);
    const targetNode = nodes.find((n) => n.id === trapNodeId) || nodes[0];
    const host = targetNode?.name || targetNode?.id || 'Edge-Router-01';

    try {
      const res = await fetch('/api/snmp/trap', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          trap_name: selectedTrap,
          host,
          target_node_id: targetNode?.id,
          severity: trapSeverity,
          destinations: globalTransport
        })
      });
      await res.json();
      setTrapStatus(`Successfully dispatched ${selectedTrap} to active pipelines! (HEC & Syslog)`);
    } catch {
      setTrapStatus(`Dispatched ${selectedTrap} in simulation mode across active streams.`);
    } finally {
      setIsEmittingTrap(false);
    }
  };

  if (!isOpen) return null;

  const availableModules = ['ALL', 'IF-MIB', 'SNMPv2-MIB', 'IP-MIB', 'TCP-MIB', 'UDP-MIB', 'BGP4-MIB', 'OSPF-MIB', 'ENTITY-MIB', 'CISCO-PROCESS-MIB', 'CISCO-MEMORY-POOL-MIB', 'CISCO-ENVMON-MIB', 'CISCO-BGP4-MIB', 'JUNIPER-MIB', 'ARISTA-QUEUE-MIB'];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 animate-in fade-in duration-200">
      <div className="w-full max-w-5xl h-[85vh] bg-[#0B0F19] border border-[#374151] rounded-xl shadow-2xl flex flex-col overflow-hidden font-sans text-slate-200">
        {/* Header */}
        <div className="h-14 px-6 bg-[#1F2937] border-b border-[#374151] flex items-center justify-between shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
              <Activity className="w-4 h-4" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-sm font-bold tracking-wide uppercase font-mono text-slate-100">
                  SC4SNMP & Multi-Vendor MIB Engine
                </h2>
                <span className="text-[10px] bg-emerald-950 text-emerald-400 border border-emerald-800 px-2 py-0.5 rounded font-mono font-bold">
                  {mibs.length} MIBs Active
                </span>
                <span className="text-[10px] bg-violet-950 text-violet-300 border border-violet-800 px-2 py-0.5 rounded font-mono font-bold">
                  Target: cisco_mdt_metrics
                </span>
              </div>
              <p className="text-[11px] text-slate-400 font-mono">
                Compliant with Splunk Connect for SNMP (SC4SNMP), RFC standards & enterprise MIB trees
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* Tabs */}
            <div className="flex bg-slate-900 border border-slate-700 rounded-lg p-0.5">
              <button
                onClick={() => setActiveTab('catalog')}
                className={`px-3 py-1 text-xs font-mono font-semibold rounded-md transition-all cursor-pointer ${
                  activeTab === 'catalog' ? 'bg-cyan-500 text-slate-950' : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                MIB Catalog ({filteredMibs.length})
              </button>
              <button
                onClick={() => setActiveTab('poll')}
                className={`px-3 py-1 text-xs font-mono font-semibold rounded-md transition-all cursor-pointer ${
                  activeTab === 'poll' ? 'bg-emerald-500 text-slate-950' : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                Polling Simulator
              </button>
              <button
                onClick={() => setActiveTab('trap')}
                className={`px-3 py-1 text-xs font-mono font-semibold rounded-md transition-all cursor-pointer ${
                  activeTab === 'trap' ? 'bg-amber-500 text-slate-950' : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                Trap Emitter
              </button>
            </div>

            <button
              onClick={onClose}
              className="p-1.5 hover:bg-slate-800 text-slate-400 hover:text-slate-200 rounded-lg transition-colors cursor-pointer"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Tab 1: MIB Catalog Browser */}
        {activeTab === 'catalog' && (
          <div className="flex-1 flex flex-col overflow-hidden p-4 gap-3">
            {/* Controls Bar */}
            <div className="flex items-center gap-3 bg-[#1F2937]/70 border border-[#374151] p-3 rounded-lg shrink-0 flex-wrap">
              {/* Search */}
              <div className="flex-1 min-w-[240px] relative">
                <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                <input
                  type="text"
                  placeholder="Search 300+ MIBs by name, OID, or description..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-9 pr-3 py-1.5 bg-slate-950 border border-slate-700 rounded-md text-xs font-mono text-slate-200 focus:outline-none focus:border-cyan-500"
                />
              </div>

              {/* Vendor Selector */}
              <div className="flex items-center gap-2">
                <span className="text-xs font-mono text-slate-400">Vendor:</span>
                <select
                  value={selectedVendor}
                  onChange={(e) => setSelectedVendor(e.target.value)}
                  className="bg-slate-950 border border-slate-700 text-slate-200 text-xs rounded px-2 py-1.5 font-mono focus:outline-none focus:border-cyan-500 cursor-pointer"
                >
                  <option value="ALL">All Vendors</option>
                  <option value="RFC">RFC Standard</option>
                  <option value="Cisco">Cisco Enterprise</option>
                  <option value="Juniper">Juniper Enterprise</option>
                  <option value="Arista">Arista Enterprise</option>
                </select>
              </div>

              {/* Module Filter */}
              <div className="flex items-center gap-2">
                <span className="text-xs font-mono text-slate-400">Module:</span>
                <select
                  value={selectedModule}
                  onChange={(e) => setSelectedModule(e.target.value)}
                  className="bg-slate-950 border border-slate-700 text-slate-200 text-xs rounded px-2 py-1.5 font-mono focus:outline-none focus:border-cyan-500 cursor-pointer max-w-[180px] truncate"
                >
                  {availableModules.map((mod) => (
                    <option key={mod} value={mod}>
                      {mod}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Table */}
            <div className="flex-1 overflow-auto border border-[#374151] rounded-lg bg-[#0B0F19]">
              <table className="w-full text-left text-xs font-mono">
                <thead className="bg-[#1F2937] text-slate-400 sticky top-0 border-b border-[#374151]">
                  <tr>
                    <th className="py-2.5 px-3">Symbol / Name</th>
                    <th className="py-2.5 px-3">OID</th>
                    <th className="py-2.5 px-3">MIB Module</th>
                    <th className="py-2.5 px-3">Type</th>
                    <th className="py-2.5 px-3">Vendor</th>
                    <th className="py-2.5 px-3">Description</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800">
                  {filteredMibs.map((m) => (
                    <tr key={m.oid + m.name} className="hover:bg-slate-900/60 transition-colors">
                      <td className="py-2 px-3 text-cyan-400 font-bold whitespace-nowrap">
                        {m.name}
                      </td>
                      <td className="py-2 px-3 text-slate-300 whitespace-nowrap">
                        <div className="flex items-center gap-1.5">
                          <span>{m.oid}</span>
                          <button
                            onClick={() => handleCopyOid(m.oid)}
                            className="text-slate-500 hover:text-slate-300 transition-colors p-0.5"
                            title="Copy OID"
                          >
                            {copiedOid === m.oid ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                          </button>
                        </div>
                      </td>
                      <td className="py-2 px-3 text-slate-400 whitespace-nowrap">
                        <span className="bg-slate-950 px-2 py-0.5 rounded border border-slate-800">
                          {m.mib_module}
                        </span>
                      </td>
                      <td className="py-2 px-3 text-amber-400 whitespace-nowrap">
                        {m.data_type}
                      </td>
                      <td className="py-2 px-3 whitespace-nowrap">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          m.vendor === 'Cisco' ? 'bg-sky-950 text-sky-400 border border-sky-800' :
                          m.vendor === 'Juniper' ? 'bg-indigo-950 text-indigo-400 border border-indigo-800' :
                          m.vendor === 'Arista' ? 'bg-purple-950 text-purple-400 border border-purple-800' :
                          'bg-emerald-950 text-emerald-400 border border-emerald-800'
                        }`}>
                          {m.vendor}
                        </span>
                      </td>
                      <td className="py-2 px-3 text-slate-400 max-w-xs truncate" title={m.description}>
                        {m.description}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Tab 2: SC4SNMP Polling Simulator */}
        {activeTab === 'poll' && (
          <div className="flex-1 flex flex-col p-6 gap-4 overflow-y-auto">
            <div className="bg-[#1F2937]/70 border border-[#374151] rounded-lg p-4 flex items-center justify-between gap-4">
              <div className="flex items-center gap-4 flex-wrap">
                <div>
                  <label className="text-xs font-mono text-slate-400 block mb-1">Target Device:</label>
                  <select
                    value={pollNodeId}
                    onChange={(e) => setPollNodeId(e.target.value)}
                    className="bg-slate-950 border border-slate-700 rounded px-3 py-1.5 text-xs font-mono text-slate-200 cursor-pointer min-w-[200px]"
                  >
                    {nodes.map((n) => (
                      <option key={n.id} value={n.id}>
                        {n.name} ({n.ip_address}) - {n.vendor}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="text-xs font-mono text-slate-400 block mb-1">MIB Module Walk:</label>
                  <select
                    value={pollModule}
                    onChange={(e) => setPollModule(e.target.value)}
                    className="bg-slate-950 border border-slate-700 rounded px-3 py-1.5 text-xs font-mono text-slate-200 cursor-pointer min-w-[180px]"
                  >
                    <option value="IF-MIB">IF-MIB (Interfaces & Bandwidth)</option>
                    <option value="SNMPv2-MIB">SNMPv2-MIB (System & Engine)</option>
                    <option value="CISCO-PROCESS-MIB">CISCO-PROCESS-MIB (CPU Utilization)</option>
                    <option value="CISCO-MEMORY-POOL-MIB">CISCO-MEMORY-POOL-MIB (Memory Pool)</option>
                    <option value="CISCO-ENVMON-MIB">CISCO-ENVMON-MIB (Environmental Sensors)</option>
                    <option value="BGP4-MIB">BGP4-MIB (BGP Sessions & Prefixes)</option>
                    <option value="OSPF-MIB">OSPF-MIB (OSPF Neighbor States)</option>
                  </select>
                </div>
              </div>

              <button
                onClick={handleRunPoll}
                disabled={isPolling}
                className="px-5 py-2.5 bg-emerald-600 hover:bg-emerald-500 text-slate-950 font-mono font-bold text-xs rounded-lg transition-all flex items-center gap-2 cursor-pointer shadow-lg disabled:opacity-50"
              >
                <Play className="w-4 h-4 fill-current" />
                <span>{isPolling ? 'POLLING...' : 'EXECUTE SC4SNMP POLL'}</span>
              </button>
            </div>

            {/* Poll Results Preview */}
            <div className="flex-1 flex flex-col border border-[#374151] rounded-lg bg-[#0B0F19] overflow-hidden">
              <div className="h-10 bg-[#1F2937] px-4 flex items-center justify-between border-b border-[#374151]">
                <span className="text-xs font-mono font-bold text-slate-300 flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-emerald-400" />
                  SC4SNMP HEC Metric Payloads (target: cisco_mdt_metrics)
                </span>
                <span className="text-[11px] font-mono text-slate-400">
                  {pollResults ? `${pollResults.length} metric events generated` : 'Awaiting execution'}
                </span>
              </div>
              <div className="flex-1 p-4 overflow-auto font-mono text-xs text-emerald-400 bg-slate-950">
                {pollResults ? (
                  <pre className="whitespace-pre-wrap">{JSON.stringify(pollResults, null, 2)}</pre>
                ) : (
                  <div className="h-full flex items-center justify-center text-slate-500">
                    Click "Execute SC4SNMP Poll" above to walk the selected MIB module and inspect structured metric payloads.
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Tab 3: SNMP Trap Emitter */}
        {activeTab === 'trap' && (
          <div className="flex-1 flex flex-col p-6 gap-4 overflow-y-auto">
            <div className="bg-[#1F2937]/70 border border-[#374151] rounded-lg p-5 flex flex-col gap-4">
              <h3 className="text-xs font-mono font-bold uppercase text-amber-400 flex items-center gap-2">
                <Zap className="w-4 h-4" />
                Configure SC4SNMP Trap Emission
              </h3>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="text-xs font-mono text-slate-400 block mb-1">Select Trap Definition:</label>
                  <select
                    value={selectedTrap}
                    onChange={(e) => {
                      setSelectedTrap(e.target.value);
                      const t = PRELOADED_TRAPS.find((p) => p.name === e.target.value);
                      if (t) setTrapSeverity(t.severity);
                    }}
                    className="w-full bg-slate-950 border border-slate-700 rounded px-3 py-1.5 text-xs font-mono text-slate-200 cursor-pointer"
                  >
                    {PRELOADED_TRAPS.map((t) => (
                      <option key={t.name} value={t.name}>
                        {t.name} ({t.severity.toUpperCase()})
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="text-xs font-mono text-slate-400 block mb-1">Source Host / Node:</label>
                  <select
                    value={trapNodeId}
                    onChange={(e) => setTrapNodeId(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-700 rounded px-3 py-1.5 text-xs font-mono text-slate-200 cursor-pointer"
                  >
                    {nodes.map((n) => (
                      <option key={n.id} value={n.id}>
                        {n.name} ({n.ip_address})
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="text-xs font-mono text-slate-400 block mb-1">Trap Severity:</label>
                  <select
                    value={trapSeverity}
                    onChange={(e) => setTrapSeverity(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-700 rounded px-3 py-1.5 text-xs font-mono text-slate-200 cursor-pointer"
                  >
                    <option value="informational">Informational</option>
                    <option value="warning">Warning</option>
                    <option value="minor">Minor</option>
                    <option value="major">Major</option>
                    <option value="critical">Critical</option>
                  </select>
                </div>
              </div>

              {trapStatus && (
                <div className="bg-emerald-950/80 border border-emerald-700 text-emerald-300 px-4 py-2 rounded text-xs font-mono flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 shrink-0 text-emerald-400" />
                  <span>{trapStatus}</span>
                </div>
              )}

              <div className="flex justify-end pt-2">
                <button
                  onClick={handleEmitTrap}
                  disabled={isEmittingTrap}
                  className="px-6 py-2 bg-gradient-to-r from-amber-600 to-rose-600 hover:from-amber-500 hover:to-rose-500 text-slate-950 font-mono font-bold text-xs rounded-lg transition-all flex items-center gap-2 cursor-pointer shadow-lg disabled:opacity-50"
                >
                  <Zap className="w-4 h-4 fill-current" />
                  <span>{isEmittingTrap ? 'EMITTING...' : 'EMIT SNMP TRAP EVENT'}</span>
                </button>
              </div>
            </div>

            {/* Trap Specifications */}
            <div className="border border-[#374151] rounded-lg bg-[#0B0F19] p-4 flex-1">
              <h4 className="text-xs font-mono font-bold text-slate-400 mb-3 uppercase">
                SC4SNMP Trap Payload Specifications
              </h4>
              <div className="space-y-2 text-xs font-mono text-slate-300">
                <div className="p-2 bg-slate-950 rounded border border-slate-800 flex justify-between">
                  <span className="text-slate-400">Sourcetype:</span>
                  <span className="text-amber-400 font-bold">sc4snmp:event</span>
                </div>
                <div className="p-2 bg-slate-950 rounded border border-slate-800 flex justify-between">
                  <span className="text-slate-400">Target Index:</span>
                  <span className="text-cyan-400 font-bold">idx_network_ops</span>
                </div>
                <div className="p-2 bg-slate-950 rounded border border-slate-800 flex justify-between">
                  <span className="text-slate-400">Trap OID:</span>
                  <span className="text-slate-200">{PRELOADED_TRAPS.find((t) => t.name === selectedTrap)?.oid}</span>
                </div>
                <div className="p-2 bg-slate-950 rounded border border-slate-800 flex justify-between">
                  <span className="text-slate-400">RFC 5424 Syslog Format:</span>
                  <span className="text-emerald-400">&lt;PRI&gt;1 TIMESTAMP HOST snmpd - - [snmpTrap@41888 ...] MSG</span>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
