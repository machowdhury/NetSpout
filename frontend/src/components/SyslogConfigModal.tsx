import React, { useState } from 'react';
import type { TelemetryTransportConfig } from '../types/topology';
import { Radio, Server, Shield, Send, Check, X } from 'lucide-react';

interface SyslogConfigModalProps {
  config: TelemetryTransportConfig;
  onClose: () => void;
  onSave: (updated: TelemetryTransportConfig) => void;
}

export const SyslogConfigModal: React.FC<SyslogConfigModalProps> = ({
  config,
  onClose,
  onSave,
}) => {
  const [activeTab, setActiveTab] = useState<'syslog' | 'hec'>('syslog');
  
  // Syslog Settings
  const [syslogEnabled, setSyslogEnabled] = useState(config.syslog_enabled);
  const [syslogHost, setSyslogHost] = useState(config.syslog_host || '127.0.0.1');
  const [syslogPort, setSyslogPort] = useState(config.syslog_port || 514);
  const [syslogProtocol, setSyslogProtocol] = useState<'udp' | 'tcp'>(config.syslog_protocol || 'udp');
  const [syslogFormat, setSyslogFormat] = useState<'rfc5424' | 'rfc3164'>(config.syslog_format || 'rfc5424');
  
  // HEC Settings
  const [hecEnabled, setHecEnabled] = useState(config.hec_enabled);
  const [hecUrl, setHecUrl] = useState(config.hec_url || 'https://127.0.0.1:8888/services/collector');
  const [hecToken, setHecToken] = useState(config.hec_token || '00000000-0000-0000-0000-000000000000');
  const [hecIndex, setHecIndex] = useState(config.hec_index || 'idx_network_ops');

  // Test Syslog State
  const [testStatus, setTestStatus] = useState<string | null>(null);
  const [isTesting, setIsTesting] = useState(false);

  const handleTestSyslog = async () => {
    setIsTesting(true);
    setTestStatus('Emitting RFC 5424 test datagram...');
    try {
      const resp = await fetch('/api/telemetry/test-syslog', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          host: syslogHost,
          port: syslogPort,
          protocol: syslogProtocol,
          format: syslogFormat,
          message: 'Diagnostic RFC 5424 Probe from Network Topology Simulator'
        })
      });
      const data = await resp.json();
      if (data.status === 'success') {
        setTestStatus(`✔ Emitted successfully to ${syslogHost}:${syslogPort} (${syslogProtocol.toUpperCase()})`);
      } else {
        setTestStatus(`✖ ${data.message || 'Emission error'}`);
      }
    } catch (e: any) {
      setTestStatus(`✖ Connection failed: ${e.message}`);
    } finally {
      setIsTesting(false);
    }
  };

  const handleSave = () => {
    const updated: TelemetryTransportConfig = {
      hec_enabled: hecEnabled,
      hec_url: hecUrl,
      hec_token: hecToken,
      hec_index: hecIndex,
      syslog_enabled: syslogEnabled,
      syslog_host: syslogHost,
      syslog_port: syslogPort,
      syslog_protocol: syslogProtocol,
      syslog_facility: 16,
      syslog_format: syslogFormat
    };
    onSave(updated);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
      <div className="bg-slate-900 border border-slate-700 rounded-xl shadow-2xl w-full max-w-xl overflow-hidden text-slate-200">
        
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-slate-950/60">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-cyan-500/20 text-cyan-400 border border-cyan-500/30">
              <Radio className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-100">Dual Telemetry Dispatcher Configuration</h3>
              <p className="text-xs text-slate-400">Stream events simultaneously to Splunk HEC and Syslog destinations</p>
            </div>
          </div>
          <button onClick={onClose} className="p-1 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-lg transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tab Selector */}
        <div className="flex border-b border-slate-800 bg-slate-950/40">
          <button
            type="button"
            onClick={() => setActiveTab('syslog')}
            className={`flex-1 py-3 text-xs font-semibold flex items-center justify-center gap-2 border-b-2 transition-all ${
              activeTab === 'syslog'
                ? 'border-cyan-500 text-cyan-400 bg-slate-900/60'
                : 'border-transparent text-slate-400 hover:text-slate-300'
            }`}
          >
            <Server className="w-4 h-4" /> Direct Syslog Destination (UDP/TCP)
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('hec')}
            className={`flex-1 py-3 text-xs font-semibold flex items-center justify-center gap-2 border-b-2 transition-all ${
              activeTab === 'hec'
                ? 'border-cyan-500 text-cyan-400 bg-slate-900/60'
                : 'border-transparent text-slate-400 hover:text-slate-300'
            }`}
          >
            <Shield className="w-4 h-4" /> Splunk HTTP Event Collector (HEC)
          </button>
        </div>

        {/* Form Body */}
        <div className="p-6 space-y-5">
          {activeTab === 'syslog' ? (
            <div className="space-y-4">
              <div className="flex items-center justify-between p-3 rounded-lg bg-slate-950 border border-slate-800">
                <div>
                  <span className="text-xs font-bold text-slate-200 block">Enable Direct Syslog Streaming</span>
                  <span className="text-[11px] text-slate-400">Emits RFC 5424/3164 datagrams directly via raw socket</span>
                </div>
                <input
                  type="checkbox"
                  checked={syslogEnabled}
                  onChange={(e) => setSyslogEnabled(e.target.checked)}
                  className="w-4 h-4 accent-cyan-500 rounded cursor-pointer"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block mb-1">Destination Host / IP</label>
                  <input
                    type="text"
                    value={syslogHost}
                    onChange={(e) => setSyslogHost(e.target.value)}
                    placeholder="127.0.0.1"
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-200 font-mono focus:outline-none focus:border-cyan-500"
                  />
                </div>
                <div>
                  <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block mb-1">Syslog Port</label>
                  <input
                    type="number"
                    value={syslogPort}
                    onChange={(e) => setSyslogPort(parseInt(e.target.value) || 514)}
                    placeholder="514"
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-200 font-mono focus:outline-none focus:border-cyan-500"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block mb-1">Transport Protocol</label>
                  <select
                    value={syslogProtocol}
                    onChange={(e) => setSyslogProtocol(e.target.value as any)}
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-200 font-mono focus:outline-none focus:border-cyan-500"
                  >
                    <option value="udp">UDP (Standard Port 514)</option>
                    <option value="tcp">TCP (Reliable Stream)</option>
                  </select>
                </div>
                <div>
                  <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block mb-1">Syslog Syntax Standard</label>
                  <select
                    value={syslogFormat}
                    onChange={(e) => setSyslogFormat(e.target.value as any)}
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-200 font-mono focus:outline-none focus:border-cyan-500"
                  >
                    <option value="rfc5424">RFC 5424 (Modern Structured)</option>
                    <option value="rfc3164">RFC 3164 (BSD Legacy Header)</option>
                  </select>
                </div>
              </div>

              {/* Test Syslog Action */}
              <div className="pt-2 border-t border-slate-800 flex items-center justify-between">
                <button
                  type="button"
                  disabled={isTesting}
                  onClick={handleTestSyslog}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold text-cyan-400 bg-cyan-950/60 hover:bg-cyan-900/60 border border-cyan-800 transition-colors cursor-pointer"
                >
                  <Send className="w-3.5 h-3.5" /> Send Test Probe
                </button>
                {testStatus && (
                  <span className={`text-xs font-mono ${testStatus.startsWith('✔') ? 'text-emerald-400' : 'text-amber-400'}`}>
                    {testStatus}
                  </span>
                )}
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="flex items-center justify-between p-3 rounded-lg bg-slate-950 border border-slate-800">
                <div>
                  <span className="text-xs font-bold text-slate-200 block">Enable Splunk HEC Ingestion</span>
                  <span className="text-[11px] text-slate-400">Streams directly into Splunk HTTP Event Collector</span>
                </div>
                <input
                  type="checkbox"
                  checked={hecEnabled}
                  onChange={(e) => setHecEnabled(e.target.checked)}
                  className="w-4 h-4 accent-cyan-500 rounded cursor-pointer"
                />
              </div>

              <div>
                <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block mb-1">Splunk HEC Endpoint URL</label>
                <input
                  type="text"
                  value={hecUrl}
                  onChange={(e) => setHecUrl(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-200 font-mono focus:outline-none focus:border-cyan-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block mb-1">HEC Token</label>
                  <input
                    type="password"
                    value={hecToken}
                    onChange={(e) => setHecToken(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-200 font-mono focus:outline-none focus:border-cyan-500"
                  />
                </div>
                <div>
                  <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block mb-1">Target Splunk Index</label>
                  <input
                    type="text"
                    value={hecIndex}
                    onChange={(e) => setHecIndex(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-200 font-mono focus:outline-none focus:border-cyan-500"
                  />
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
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
            <Check className="w-4 h-4" /> Save Dispatcher Settings
          </button>
        </div>

      </div>
    </div>
  );
};
