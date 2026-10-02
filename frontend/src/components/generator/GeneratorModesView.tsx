import React, { useState } from 'react';
import { 
  Zap, Play, Send, 
  Terminal, Server, FileText, Layers
} from 'lucide-react';

export const GeneratorModesView: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'single_event' | 'sourcetype' | 'data_source'>('single_event');
  
  // Single Event state (Mode D)
  const [seVendor, setSeVendor] = useState('cisco_ios');
  const [seSourcetype, setSeSourcetype] = useState('cisco:ios:syslog');
  const [seEventName, setSeEventName] = useState('Interface Link Down');
  const [seDispatch, setSeDispatch] = useState(false);
  const [seIndex, setSeIndex] = useState('idx_network_ops');
  const [seResult, setSeResult] = useState<any | null>(null);
  const [seLoading, setSeLoading] = useState(false);

  // Sourcetype Batch state (Mode C)
  const [stVendor, setStVendor] = useState('arista_eos');
  const [stSourcetype, setStSourcetype] = useState('arista:eos');
  const [stCount, setStCount] = useState(10);
  const [stRate, setStRate] = useState(10);
  const [stDispatch, setStDispatch] = useState(false);
  const [stIndex, setStIndex] = useState('idx_network_ops');
  const [stResult, setStResult] = useState<any | null>(null);
  const [stLoading, setStLoading] = useState(false);

  // Data Source state (Mode B)
  const [dsVendor, setDsVendor] = useState('palo_alto');
  const [dsProduct, setDsProduct] = useState('PAN-OS Firewall');
  const [dsTransport, setDsTransport] = useState('syslog');
  const [dsCount, setDsCount] = useState(25);
  const [dsDispatch, setDsDispatch] = useState(false);
  const [dsIndex, setDsIndex] = useState('idx_network_ops');
  const [dsResult, setDsResult] = useState<any | null>(null);
  const [dsLoading, setDsLoading] = useState(false);

  // Mode D: Generate Single Event
  const handleGenerateSingleEvent = async () => {
    setSeLoading(true);
    setSeResult(null);
    try {
      const res = await fetch('/api/generate/single-event', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          vendor_id: seVendor,
          sourcetype: seSourcetype,
          event_name: seEventName,
          dispatch: seDispatch,
          index: seIndex
        })
      });
      const data = await res.json();
      setSeResult(data);
    } catch (e: any) {
      setSeResult({ error: e.message });
    } finally {
      setSeLoading(false);
    }
  };

  // Mode C: Generate Sourcetype Batch
  const handleGenerateSourcetype = async () => {
    setStLoading(true);
    setStResult(null);
    try {
      const res = await fetch('/api/generate/sourcetype', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          vendor_id: stVendor,
          sourcetype: stSourcetype,
          count: stCount,
          rate_eps: stRate,
          dispatch: stDispatch,
          index: stIndex
        })
      });
      const data = await res.json();
      setStResult(data);
    } catch (e: any) {
      setStResult({ error: e.message });
    } finally {
      setStLoading(false);
    }
  };

  // Mode B: Generate Data Source
  const handleGenerateDataSource = async () => {
    setDsLoading(true);
    setDsResult(null);
    try {
      const res = await fetch('/api/generate/data-source', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          vendor_id: dsVendor,
          product: dsProduct,
          transport: dsTransport,
          count: dsCount,
          dispatch: dsDispatch,
          index: dsIndex
        })
      });
      const data = await res.json();
      setDsResult(data);
    } catch (e: any) {
      setDsResult({ error: e.message });
    } finally {
      setDsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full bg-[#0b0f19] text-slate-100 p-6 overflow-y-auto space-y-6">
      {/* Header */}
      <div className="border-b border-slate-800 pb-4">
        <h2 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
          <Zap className="w-6 h-6 text-cyan-400" />
          <span>Precision Telemetry Generator</span>
          <span className="text-xs font-semibold px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/30">
            Modes B, C &amp; D
          </span>
        </h2>
        <p className="text-sm text-slate-400 mt-1">
          Generate vendor-grounded telemetry without launching a full operational scenario. Perfect for Splunk app development, field extraction validation, dashboard testing, and detection tuning.
        </p>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-2 border-b border-slate-800">
        <button
          onClick={() => setActiveTab('single_event')}
          className={`flex items-center gap-2 px-4 py-2.5 text-xs font-bold font-mono border-b-2 transition ${
            activeTab === 'single_event'
              ? 'border-cyan-400 text-cyan-400 bg-cyan-950/20'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <FileText className="w-4 h-4" />
          <span>Mode D: Single Event (1-Click)</span>
        </button>
        <button
          onClick={() => setActiveTab('sourcetype')}
          className={`flex items-center gap-2 px-4 py-2.5 text-xs font-bold font-mono border-b-2 transition ${
            activeTab === 'sourcetype'
              ? 'border-cyan-400 text-cyan-400 bg-cyan-950/20'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Layers className="w-4 h-4" />
          <span>Mode C: Sourcetype / Event Family Batch</span>
        </button>
        <button
          onClick={() => setActiveTab('data_source')}
          className={`flex items-center gap-2 px-4 py-2.5 text-xs font-bold font-mono border-b-2 transition ${
            activeTab === 'data_source'
              ? 'border-cyan-400 text-cyan-400 bg-cyan-950/20'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Server className="w-4 h-4" />
          <span>Mode B: Data Source Stream</span>
        </button>
      </div>

      {/* Tab 1: Mode D Single Event */}
      {activeTab === 'single_event' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="p-5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-4">
            <h3 className="text-sm font-bold text-slate-200 uppercase tracking-wider font-mono">
              Generate Exactly One Event
            </h3>
            <p className="text-xs text-slate-400">
              Emit one precision vendor log into Splunk to test CIM normalization, field extractions, or alerting triggers.
            </p>

            <div className="space-y-3">
              <div>
                <label className="text-xs text-slate-400 font-mono">Vendor / Ecosystem</label>
                <select
                  value={seVendor}
                  onChange={(e) => setSeVendor(e.target.value)}
                  className="w-full mt-1 px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs font-mono text-slate-200 focus:outline-none focus:border-cyan-500"
                >
                  <option value="cisco_ios">Cisco Systems (IOS / IOS XR / Catalyst)</option>
                  <option value="arista_eos">Arista Networks (EOS)</option>
                  <option value="palo_alto">Palo Alto Networks (PAN-OS)</option>
                  <option value="juniper_junos">Juniper Networks (Junos OS)</option>
                  <option value="f5">F5 Networks (BIG-IP LTM)</option>
                  <option value="fortinet">Fortinet (FortiGate)</option>
                </select>
              </div>

              <div>
                <label className="text-xs text-slate-400 font-mono">Splunk Sourcetype</label>
                <input
                  type="text"
                  value={seSourcetype}
                  onChange={(e) => setSeSourcetype(e.target.value)}
                  className="w-full mt-1 px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs font-mono text-slate-200 focus:outline-none focus:border-cyan-500"
                />
              </div>

              <div>
                <label className="text-xs text-slate-400 font-mono">Event Name / Failure Description</label>
                <input
                  type="text"
                  value={seEventName}
                  onChange={(e) => setSeEventName(e.target.value)}
                  className="w-full mt-1 px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs font-mono text-slate-200 focus:outline-none focus:border-cyan-500"
                />
              </div>

              <div>
                <label className="text-xs text-slate-400 font-mono">Target Splunk Index</label>
                <input
                  type="text"
                  value={seIndex}
                  onChange={(e) => setSeIndex(e.target.value)}
                  className="w-full mt-1 px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs font-mono text-slate-200 focus:outline-none focus:border-cyan-500"
                />
              </div>

              <div className="flex items-center gap-2 pt-2">
                <input
                  type="checkbox"
                  id="se-dispatch"
                  checked={seDispatch}
                  onChange={(e) => setSeDispatch(e.target.checked)}
                  className="rounded bg-slate-950 border-slate-800 text-cyan-600 focus:ring-0"
                />
                <label htmlFor="se-dispatch" className="text-xs text-slate-300 font-mono cursor-pointer">
                  Dispatch immediately to configured Splunk HEC / Syslog destination
                </label>
              </div>

              <button
                onClick={handleGenerateSingleEvent}
                disabled={seLoading}
                className="w-full mt-4 flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-bold font-mono transition shadow-lg shadow-cyan-950/50 disabled:opacity-50"
              >
                <Play className="w-3.5 h-3.5 fill-current" />
                <span>{seLoading ? 'Generating...' : 'Generate 1 Event'}</span>
              </button>
            </div>
          </div>

          <div className="p-5 rounded-xl bg-slate-900/60 border border-slate-800 flex flex-col">
            <h3 className="text-sm font-bold text-slate-200 uppercase tracking-wider font-mono mb-3">
              Generated Event Output
            </h3>
            {seResult ? (
              <div className="flex-1 flex flex-col space-y-3 font-mono text-xs">
                {seResult.status === 'TELEMETRY_NOT_GROUNDED' ? (
                  <div className="p-4 rounded-lg bg-red-950/40 border border-red-500/40 space-y-2">
                    <div className="flex items-center gap-2 text-red-400 font-bold">
                      <span className="px-1.5 py-0.5 rounded bg-red-500/20 text-[10px]">ANTI-FABRICATION GUARD</span>
                      <span>TELEMETRY NOT GROUNDED</span>
                    </div>
                    <p className="text-slate-300 text-xs">{seResult.reason}</p>
                    <div className="text-[11px] text-slate-400">
                      Provenance Requirement: <span className="text-cyan-300">{seResult.source_requirement}</span>
                    </div>
                  </div>
                ) : (
                  <>
                    <div className="flex items-center justify-between text-slate-400 text-[11px] pb-2 border-b border-slate-800">
                      <span>Event ID: <b className="text-cyan-300">{seResult.event_id}</b></span>
                      <span>Dispatched: <b className={seResult.dispatched ? "text-emerald-400" : "text-amber-400"}>{seResult.dispatched ? "YES" : "NO (DRY RUN)"}</b></span>
                    </div>
                    {seResult.provenance && (
                      <div className="flex items-center justify-between p-2 rounded bg-cyan-950/20 border border-cyan-800/40 text-[10px] text-slate-300">
                        <span>Classification: <b className="text-cyan-300">{seResult.provenance.classification}</b></span>
                        <span className="truncate max-w-[240px]" title={seResult.provenance.source}>Source: {seResult.provenance.source}</span>
                      </div>
                    )}
                    <div className="flex-1 p-3 rounded-lg bg-slate-950 border border-slate-800/80 text-emerald-400 overflow-x-auto whitespace-pre-wrap leading-relaxed select-all">
                      {seResult.raw || JSON.stringify(seResult, null, 2)}
                    </div>
                  </>
                )}
              </div>
            ) : (
              <div className="flex-1 flex flex-col items-center justify-center text-slate-500 gap-2 p-8 border border-dashed border-slate-800 rounded-xl">
                <Terminal className="w-8 h-8 text-slate-600" />
                <p className="text-xs">Click "Generate 1 Event" to produce a vendor-grounded log sample.</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Tab 2: Mode C Sourcetype Batch */}
      {activeTab === 'sourcetype' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="p-5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-4">
            <h3 className="text-sm font-bold text-slate-200 uppercase tracking-wider font-mono">
              Batch Sourcetype Generation
            </h3>
            <p className="text-xs text-slate-400">
              Generate a burst or sustained stream of events for a specific Splunk sourcetype with custom rate pacing.
            </p>

            <div className="space-y-3">
              <div>
                <label className="text-xs text-slate-400 font-mono">Vendor</label>
                <select
                  value={stVendor}
                  onChange={(e) => setStVendor(e.target.value)}
                  className="w-full mt-1 px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs font-mono text-slate-200 focus:outline-none focus:border-cyan-500"
                >
                  <option value="arista_eos">Arista Networks (EOS)</option>
                  <option value="cisco_ios">Cisco Systems (IOS / IOS XR)</option>
                  <option value="palo_alto">Palo Alto Networks (PAN-OS)</option>
                  <option value="juniper_junos">Juniper Networks (Junos OS)</option>
                </select>
              </div>

              <div>
                <label className="text-xs text-slate-400 font-mono">Sourcetype</label>
                <input
                  type="text"
                  value={stSourcetype}
                  onChange={(e) => setStSourcetype(e.target.value)}
                  className="w-full mt-1 px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs font-mono text-slate-200 focus:outline-none focus:border-cyan-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-slate-400 font-mono">Event Count</label>
                  <input
                    type="number"
                    value={stCount}
                    onChange={(e) => setStCount(Number(e.target.value))}
                    min={1}
                    max={1000}
                    className="w-full mt-1 px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs font-mono text-slate-200 focus:outline-none focus:border-cyan-500"
                  />
                </div>
                <div>
                  <label className="text-xs text-slate-400 font-mono">Rate (Events/sec)</label>
                  <input
                    type="number"
                    value={stRate}
                    onChange={(e) => setStRate(Number(e.target.value))}
                    min={1}
                    max={100}
                    className="w-full mt-1 px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs font-mono text-slate-200 focus:outline-none focus:border-cyan-500"
                  />
                </div>
              </div>

              <div>
                <label className="text-xs text-slate-400 font-mono">Target Splunk Index</label>
                <input
                  type="text"
                  value={stIndex}
                  onChange={(e) => setStIndex(e.target.value)}
                  className="w-full mt-1 px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs font-mono text-slate-200 focus:outline-none focus:border-cyan-500"
                />
              </div>

              <div className="flex items-center gap-2 pt-2">
                <input
                  type="checkbox"
                  id="st-dispatch"
                  checked={stDispatch}
                  onChange={(e) => setStDispatch(e.target.checked)}
                  className="rounded bg-slate-950 border-slate-800 text-cyan-600 focus:ring-0"
                />
                <label htmlFor="st-dispatch" className="text-xs text-slate-300 font-mono cursor-pointer">
                  Dispatch directly to Splunk HEC
                </label>
              </div>

              <button
                onClick={handleGenerateSourcetype}
                disabled={stLoading}
                className="w-full mt-4 flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-bold font-mono transition shadow-lg shadow-cyan-950/50 disabled:opacity-50"
              >
                <Send className="w-3.5 h-3.5" />
                <span>{stLoading ? 'Generating Batch...' : `Emit ${stCount} Events`}</span>
              </button>
            </div>
          </div>

          <div className="p-5 rounded-xl bg-slate-900/60 border border-slate-800 flex flex-col">
            <h3 className="text-sm font-bold text-slate-200 uppercase tracking-wider font-mono mb-3">
              Batch Execution Summary
            </h3>
            {stResult ? (
              <div className="flex-1 flex flex-col space-y-3 font-mono text-xs">
                {stResult.status === 'TELEMETRY_NOT_GROUNDED' ? (
                  <div className="p-4 rounded-lg bg-red-950/40 border border-red-500/40 space-y-2">
                    <div className="flex items-center gap-2 text-red-400 font-bold">
                      <span className="px-1.5 py-0.5 rounded bg-red-500/20 text-[10px]">ANTI-FABRICATION GUARD</span>
                      <span>TELEMETRY NOT GROUNDED</span>
                    </div>
                    <p className="text-slate-300 text-xs">{stResult.reason}</p>
                    <div className="text-[11px] text-slate-400">
                      Provenance Requirement: <span className="text-cyan-300">{stResult.source_requirement}</span>
                    </div>
                  </div>
                ) : (
                  <>
                    <div className="grid grid-cols-2 gap-2 p-3 rounded-lg bg-slate-950 border border-slate-800 text-[11px]">
                      <div>Requested: <b className="text-cyan-300">{stResult.count_requested}</b></div>
                      <div>Generated: <b className="text-emerald-400">{stResult.count_generated}</b></div>
                      <div>Dispatched: <b className="text-cyan-300">{stResult.count_dispatched}</b></div>
                      <div>Index: <b className="text-slate-300">{stResult.index}</b></div>
                    </div>
                    {stResult.provenance && (
                      <div className="flex items-center justify-between p-2 rounded bg-cyan-950/20 border border-cyan-800/40 text-[10px] text-slate-300">
                        <span>Classification: <b className="text-cyan-300">{stResult.provenance.classification}</b></span>
                        <span className="truncate max-w-[240px]" title={stResult.provenance.source}>Source: {stResult.provenance.source}</span>
                      </div>
                    )}
                    <div className="flex-1 p-3 rounded-lg bg-slate-950 border border-slate-800/80 text-slate-300 overflow-x-auto space-y-2 text-[11px]">
                      <div className="text-slate-500 font-bold uppercase">Sample Previews:</div>
                      {stResult.sample_preview?.map((sm: string, idx: number) => (
                        <div key={idx} className="p-2 rounded bg-slate-900 border border-slate-800 text-emerald-400">
                          {sm}
                        </div>
                      ))}
                    </div>
                  </>
                )}
              </div>
            ) : (
              <div className="flex-1 flex flex-col items-center justify-center text-slate-500 gap-2 p-8 border border-dashed border-slate-800 rounded-xl">
                <Layers className="w-8 h-8 text-slate-600" />
                <p className="text-xs">Configure parameters and click "Emit Events" to generate a sourcetype batch.</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Tab 3: Mode B Data Source */}
      {activeTab === 'data_source' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="p-5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-4">
            <h3 className="text-sm font-bold text-slate-200 uppercase tracking-wider font-mono">
              Vendor Technology Telemetry Stream
            </h3>
            <p className="text-xs text-slate-400">
              Generate continuous baseline telemetry for a specific vendor device family without injecting failure faults.
            </p>

            <div className="space-y-3">
              <div>
                <label className="text-xs text-slate-400 font-mono">Vendor</label>
                <select
                  value={dsVendor}
                  onChange={(e) => setDsVendor(e.target.value)}
                  className="w-full mt-1 px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs font-mono text-slate-200 focus:outline-none focus:border-cyan-500"
                >
                  <option value="palo_alto">Palo Alto Networks</option>
                  <option value="cisco_ios">Cisco Systems</option>
                  <option value="arista_eos">Arista Networks</option>
                  <option value="juniper_junos">Juniper Networks</option>
                  <option value="fortinet">Fortinet</option>
                  <option value="f5">F5 Networks</option>
                </select>
              </div>

              <div>
                <label className="text-xs text-slate-400 font-mono">Product / Platform</label>
                <input
                  type="text"
                  value={dsProduct}
                  onChange={(e) => setDsProduct(e.target.value)}
                  className="w-full mt-1 px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs font-mono text-slate-200 focus:outline-none focus:border-cyan-500"
                />
              </div>

              <div>
                <label className="text-xs text-slate-400 font-mono">Transport Protocol</label>
                <select
                  value={dsTransport}
                  onChange={(e) => setDsTransport(e.target.value)}
                  className="w-full mt-1 px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs font-mono text-slate-200 focus:outline-none focus:border-cyan-500"
                >
                  <option value="syslog">Syslog (RFC 5424 / RFC 3164)</option>
                  <option value="snmp">SNMPv2c (BER Traps &amp; Informs)</option>
                  <option value="gnmi">gNMI / OpenConfig Streaming</option>
                  <option value="hec">Splunk HEC (Direct)</option>
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-slate-400 font-mono">Record Count</label>
                  <input
                    type="number"
                    value={dsCount}
                    onChange={(e) => setDsCount(Number(e.target.value))}
                    min={1}
                    max={1000}
                    className="w-full mt-1 px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs font-mono text-slate-200 focus:outline-none focus:border-cyan-500"
                  />
                </div>
                <div>
                  <label className="text-xs text-slate-400 font-mono">Target Splunk Index</label>
                  <input
                    type="text"
                    value={dsIndex}
                    onChange={(e) => setDsIndex(e.target.value)}
                    className="w-full mt-1 px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs font-mono text-slate-200 focus:outline-none focus:border-cyan-500"
                  />
                </div>
              </div>

              <div className="flex items-center gap-2 pt-2">
                <input
                  type="checkbox"
                  id="ds-dispatch"
                  checked={dsDispatch}
                  onChange={(e) => setDsDispatch(e.target.checked)}
                  className="rounded bg-slate-950 border-slate-800 text-cyan-600 focus:ring-0"
                />
                <label htmlFor="ds-dispatch" className="text-xs text-slate-300 font-mono cursor-pointer">
                  Dispatch events directly into Splunk
                </label>
              </div>

              <button
                onClick={handleGenerateDataSource}
                disabled={dsLoading}
                className="w-full mt-4 flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-bold font-mono transition shadow-lg shadow-cyan-950/50 disabled:opacity-50"
              >
                <Play className="w-3.5 h-3.5 fill-current" />
                <span>{dsLoading ? 'Starting Stream...' : `Stream ${dsCount} Telemetry Records`}</span>
              </button>
            </div>
          </div>

          <div className="p-5 rounded-xl bg-slate-900/60 border border-slate-800 flex flex-col">
            <h3 className="text-sm font-bold text-slate-200 uppercase tracking-wider font-mono mb-3">
              Data Source Stream Log
            </h3>
            {dsResult ? (
              <div className="flex-1 flex flex-col space-y-3 font-mono text-xs">
                <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 text-[11px] flex items-center justify-between">
                  <span>Product: <b className="text-cyan-300">{dsProduct}</b></span>
                  <span>Generated: <b className="text-emerald-400">{dsResult.count_generated} records</b></span>
                </div>
                <div className="flex-1 p-3 rounded-lg bg-slate-950 border border-slate-800/80 text-emerald-400 overflow-x-auto space-y-2 text-[11px]">
                  {dsResult.sample_preview?.map((sm: string, idx: number) => (
                    <div key={idx} className="p-2 rounded bg-slate-900 border border-slate-800">
                      {sm}
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="flex-1 flex flex-col items-center justify-center text-slate-500 gap-2 p-8 border border-dashed border-slate-800 rounded-xl">
                <Server className="w-8 h-8 text-slate-600" />
                <p className="text-xs">Select vendor and click "Stream Records" to generate a live source stream.</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
