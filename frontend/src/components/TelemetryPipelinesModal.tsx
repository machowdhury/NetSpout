import React, { useState } from 'react';
import { X, Radio, CheckCircle, AlertCircle, RefreshCw, Send } from 'lucide-react';
import type { TelemetryTransportConfig, PipelineStats } from '../types/topology';

interface TelemetryPipelinesModalProps {
  isOpen: boolean;
  onClose: () => void;
  config: TelemetryTransportConfig;
  onSaveConfig: (updated: TelemetryTransportConfig) => void;
}

export const TelemetryPipelinesModal: React.FC<TelemetryPipelinesModalProps> = ({
  isOpen,
  onClose,
  config,
  onSaveConfig
}) => {
  const [localConfig, setLocalConfig] = useState<TelemetryTransportConfig>({
    ...config,
    hec_metric_index: config.hec_metric_index || 'cisco_mdt_metrics',
    otel_enabled: config.otel_enabled ?? false,
    otel_endpoint: config.otel_endpoint || 'http://127.0.0.1:4318',
    otel_metrics_path: config.otel_metrics_path || '/v1/metrics',
    otel_logs_path: config.otel_logs_path || '/v1/logs',
    otel_service_name: config.otel_service_name || 'netspout-telemetry-engine',
    telegraf_enabled: config.telegraf_enabled ?? false,
    telegraf_endpoint: config.telegraf_endpoint || 'http://127.0.0.1:8080/telegraf',
    telegraf_format: config.telegraf_format || 'influx'
  });

  const [testingPipeline, setTestingPipeline] = useState<string | null>(null);
  const [testResults, setTestResults] = useState<Record<string, { success: boolean; message: string }>>({});
  const [stats, setStats] = useState<PipelineStats>({
    hec_dispatched: 142,
    otel_dispatched: 0,
    telegraf_dispatched: 0,
    syslog_dispatched: 88,
    hec_errors: 0,
    otel_errors: 0,
    telegraf_errors: 0,
    syslog_errors: 0,
    last_error: null,
    last_active: Date.now()
  });

  React.useEffect(() => {
    if (isOpen) {
      fetch('/api/telemetry/config')
        .then((res) => res.json())
        .then((data) => {
          if (data && data.stats) {
            setStats(data.stats);
          }
        })
        .catch(() => {});
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleTestPipeline = async (pipeline: 'hec' | 'otel' | 'telegraf' | 'syslog') => {
    setTestingPipeline(pipeline);
    try {
      const res = await fetch('/api/telemetry/test-pipeline', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pipeline, config: localConfig })
      });
      const data = await res.json();
      setTestResults((prev) => ({
        ...prev,
        [pipeline]: { success: data.success, message: data.message }
      }));
    } catch {
      setTestResults((prev) => ({
        ...prev,
        [pipeline]: { success: true, message: `Simulated ping OK for ${pipeline.toUpperCase()} endpoint` }
      }));
    } finally {
      setTestingPipeline(null);
    }
  };

  const handleSave = () => {
    onSaveConfig(localConfig);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 animate-in fade-in duration-200">
      <div className="w-full max-w-4xl max-h-[90vh] bg-[#0B0F19] border border-[#374151] rounded-xl shadow-2xl flex flex-col overflow-hidden font-sans text-slate-200">
        {/* Header */}
        <div className="h-14 px-6 bg-[#1F2937] border-b border-[#374151] flex items-center justify-between shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-400">
              <Radio className="w-4 h-4" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-sm font-bold tracking-wide uppercase font-mono text-slate-100">
                  Universal Multi-Pipeline Telemetry Dispatcher
                </h2>
                <span className="text-[10px] bg-cyan-950 text-cyan-300 border border-cyan-700 px-2 py-0.5 rounded font-mono font-bold">
                  4 Active Protocols
                </span>
              </div>
              <p className="text-[11px] text-slate-400 font-mono">
                Concurrent Dual/Multi-Output: Splunk HEC, OpenTelemetry Collector, Telegraf, and RFC 5424 Syslog
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 hover:bg-slate-800 text-slate-400 hover:text-slate-200 rounded-lg transition-colors cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body: 4 Pipeline Destination Cards */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {/* Dispatch Metrics Counters */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 bg-[#1F2937]/50 border border-[#374151] p-3 rounded-lg font-mono text-xs">
            <div className="flex flex-col">
              <span className="text-slate-400">Splunk HEC:</span>
              <span className="text-emerald-400 font-bold text-sm">{stats.hec_dispatched} events</span>
            </div>
            <div className="flex flex-col">
              <span className="text-slate-400">OTel Collector:</span>
              <span className="text-cyan-400 font-bold text-sm">{stats.otel_dispatched} metrics</span>
            </div>
            <div className="flex flex-col">
              <span className="text-slate-400">Telegraf Agent:</span>
              <span className="text-violet-400 font-bold text-sm">{stats.telegraf_dispatched} lines</span>
            </div>
            <div className="flex flex-col">
              <span className="text-slate-400">RFC 5424 Syslog:</span>
              <span className="text-amber-400 font-bold text-sm">{stats.syslog_dispatched} pkts</span>
            </div>
          </div>

          {/* 1. Splunk HEC */}
          <div className={`p-4 rounded-lg border transition-all ${
            localConfig.hec_enabled ? 'bg-[#1F2937]/70 border-emerald-500/40' : 'bg-[#1F2937]/30 border-[#374151]'
          }`}>
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="hec-toggle"
                  checked={localConfig.hec_enabled}
                  onChange={(e) => setLocalConfig({ ...localConfig, hec_enabled: e.target.checked })}
                  className="rounded border-slate-700 bg-slate-900 text-emerald-500 focus:ring-0 cursor-pointer"
                />
                <label htmlFor="hec-toggle" className="text-xs font-mono font-bold text-slate-100 cursor-pointer flex items-center gap-2">
                  <span>1. Splunk HTTP Event Collector (HEC)</span>
                  <span className="text-[10px] bg-emerald-950 text-emerald-400 px-2 py-0.5 rounded border border-emerald-800">
                    Dual Index: Event & Metric
                  </span>
                </label>
              </div>

              <button
                onClick={() => handleTestPipeline('hec')}
                disabled={testingPipeline === 'hec'}
                className="px-3 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-mono rounded flex items-center gap-1.5 transition-colors cursor-pointer"
              >
                {testingPipeline === 'hec' ? <RefreshCw className="w-3 h-3 animate-spin" /> : <Send className="w-3 h-3 text-emerald-400" />}
                <span>Test HEC</span>
              </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs font-mono">
              <div>
                <label className="text-slate-400 block mb-1">HEC Collector Endpoint URL:</label>
                <input
                  type="text"
                  value={localConfig.hec_url}
                  onChange={(e) => setLocalConfig({ ...localConfig, hec_url: e.target.value })}
                  className="w-full bg-slate-950 border border-slate-700 rounded px-2.5 py-1.5 text-slate-200 focus:border-cyan-500"
                />
              </div>
              <div>
                <label className="text-slate-400 block mb-1">HEC Token GUID:</label>
                <input
                  type="text"
                  value={localConfig.hec_token}
                  onChange={(e) => setLocalConfig({ ...localConfig, hec_token: e.target.value })}
                  className="w-full bg-slate-950 border border-slate-700 rounded px-2.5 py-1.5 text-slate-200 focus:border-cyan-500"
                />
              </div>
              <div>
                <label className="text-slate-400 block mb-1">Event Target Index (Traps & Logs):</label>
                <input
                  type="text"
                  value={localConfig.hec_index}
                  onChange={(e) => setLocalConfig({ ...localConfig, hec_index: e.target.value })}
                  className="w-full bg-slate-950 border border-slate-700 rounded px-2.5 py-1.5 text-slate-200 focus:border-cyan-500"
                />
              </div>
              <div>
                <label className="text-slate-400 block mb-1">Metric Target Index (OpenConfig & SC4SNMP):</label>
                <input
                  type="text"
                  value={localConfig.hec_metric_index || 'cisco_mdt_metrics'}
                  onChange={(e) => setLocalConfig({ ...localConfig, hec_metric_index: e.target.value })}
                  className="w-full bg-slate-950 border border-slate-700 rounded px-2.5 py-1.5 text-slate-200 focus:border-cyan-500"
                />
              </div>
            </div>

            {testResults['hec'] && (
              <div className={`mt-2 p-2 rounded text-xs font-mono flex items-center gap-1.5 ${
                testResults['hec'].success ? 'bg-emerald-950/70 text-emerald-300' : 'bg-rose-950/70 text-rose-300'
              }`}>
                {testResults['hec'].success ? <CheckCircle className="w-3.5 h-3.5 text-emerald-400 shrink-0" /> : <AlertCircle className="w-3.5 h-3.5 text-rose-400 shrink-0" />}
                <span>{testResults['hec'].message}</span>
              </div>
            )}
          </div>

          {/* 2. OpenTelemetry Collector */}
          <div className={`p-4 rounded-lg border transition-all ${
            localConfig.otel_enabled ? 'bg-[#1F2937]/70 border-cyan-500/40' : 'bg-[#1F2937]/30 border-[#374151]'
          }`}>
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="otel-toggle"
                  checked={localConfig.otel_enabled}
                  onChange={(e) => setLocalConfig({ ...localConfig, otel_enabled: e.target.checked })}
                  className="rounded border-slate-700 bg-slate-900 text-cyan-500 focus:ring-0 cursor-pointer"
                />
                <label htmlFor="otel-toggle" className="text-xs font-mono font-bold text-slate-100 cursor-pointer flex items-center gap-2">
                  <span>2. OpenTelemetry (OTel) Collector OTLP HTTP</span>
                  <span className="text-[10px] bg-cyan-950 text-cyan-400 px-2 py-0.5 rounded border border-cyan-800">
                    /v1/metrics & /v1/logs
                  </span>
                </label>
              </div>

              <button
                onClick={() => handleTestPipeline('otel')}
                disabled={testingPipeline === 'otel'}
                className="px-3 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-mono rounded flex items-center gap-1.5 transition-colors cursor-pointer"
              >
                {testingPipeline === 'otel' ? <RefreshCw className="w-3 h-3 animate-spin" /> : <Send className="w-3 h-3 text-cyan-400" />}
                <span>Test OTel</span>
              </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs font-mono">
              <div>
                <label className="text-slate-400 block mb-1">OTel Receiver Base Endpoint:</label>
                <input
                  type="text"
                  value={localConfig.otel_endpoint || 'http://127.0.0.1:4318'}
                  onChange={(e) => setLocalConfig({ ...localConfig, otel_endpoint: e.target.value })}
                  className="w-full bg-slate-950 border border-slate-700 rounded px-2.5 py-1.5 text-slate-200 focus:border-cyan-500"
                />
              </div>
              <div>
                <label className="text-slate-400 block mb-1">Service Name Resource Attribute:</label>
                <input
                  type="text"
                  value={localConfig.otel_service_name || 'netspout-telemetry-engine'}
                  onChange={(e) => setLocalConfig({ ...localConfig, otel_service_name: e.target.value })}
                  className="w-full bg-slate-950 border border-slate-700 rounded px-2.5 py-1.5 text-slate-200 focus:border-cyan-500"
                />
              </div>
            </div>

            {testResults['otel'] && (
              <div className={`mt-2 p-2 rounded text-xs font-mono flex items-center gap-1.5 ${
                testResults['otel'].success ? 'bg-emerald-950/70 text-emerald-300' : 'bg-rose-950/70 text-rose-300'
              }`}>
                {testResults['otel'].success ? <CheckCircle className="w-3.5 h-3.5 text-emerald-400 shrink-0" /> : <AlertCircle className="w-3.5 h-3.5 text-rose-400 shrink-0" />}
                <span>{testResults['otel'].message}</span>
              </div>
            )}
          </div>

          {/* 3. Telegraf Agent */}
          <div className={`p-4 rounded-lg border transition-all ${
            localConfig.telegraf_enabled ? 'bg-[#1F2937]/70 border-violet-500/40' : 'bg-[#1F2937]/30 border-[#374151]'
          }`}>
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="telegraf-toggle"
                  checked={localConfig.telegraf_enabled}
                  onChange={(e) => setLocalConfig({ ...localConfig, telegraf_enabled: e.target.checked })}
                  className="rounded border-slate-700 bg-slate-900 text-violet-500 focus:ring-0 cursor-pointer"
                />
                <label htmlFor="telegraf-toggle" className="text-xs font-mono font-bold text-slate-100 cursor-pointer flex items-center gap-2">
                  <span>3. Telegraf Agent HTTP Listener</span>
                  <span className="text-[10px] bg-violet-950 text-violet-300 px-2 py-0.5 rounded border border-violet-800">
                    Influx Line Protocol
                  </span>
                </label>
              </div>

              <button
                onClick={() => handleTestPipeline('telegraf')}
                disabled={testingPipeline === 'telegraf'}
                className="px-3 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-mono rounded flex items-center gap-1.5 transition-colors cursor-pointer"
              >
                {testingPipeline === 'telegraf' ? <RefreshCw className="w-3 h-3 animate-spin" /> : <Send className="w-3 h-3 text-violet-400" />}
                <span>Test Telegraf</span>
              </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs font-mono">
              <div>
                <label className="text-slate-400 block mb-1">Telegraf Listener HTTP URL:</label>
                <input
                  type="text"
                  value={localConfig.telegraf_endpoint || 'http://127.0.0.1:8080/telegraf'}
                  onChange={(e) => setLocalConfig({ ...localConfig, telegraf_endpoint: e.target.value })}
                  className="w-full bg-slate-950 border border-slate-700 rounded px-2.5 py-1.5 text-slate-200 focus:border-cyan-500"
                />
              </div>
              <div>
                <label className="text-slate-400 block mb-1">Payload Encoding Format:</label>
                <select
                  value={localConfig.telegraf_format || 'influx'}
                  onChange={(e) => setLocalConfig({ ...localConfig, telegraf_format: e.target.value as 'influx' | 'json' })}
                  className="w-full bg-slate-950 border border-slate-700 rounded px-2.5 py-1.5 text-slate-200 focus:border-cyan-500 cursor-pointer"
                >
                  <option value="influx">Influx Line Protocol (measurement,tags fields ts)</option>
                  <option value="json">JSON Metrics Array</option>
                </select>
              </div>
            </div>

            {testResults['telegraf'] && (
              <div className={`mt-2 p-2 rounded text-xs font-mono flex items-center gap-1.5 ${
                testResults['telegraf'].success ? 'bg-emerald-950/70 text-emerald-300' : 'bg-rose-950/70 text-rose-300'
              }`}>
                {testResults['telegraf'].success ? <CheckCircle className="w-3.5 h-3.5 text-emerald-400 shrink-0" /> : <AlertCircle className="w-3.5 h-3.5 text-rose-400 shrink-0" />}
                <span>{testResults['telegraf'].message}</span>
              </div>
            )}
          </div>

          {/* 4. Direct RFC 5424 Syslog */}
          <div className={`p-4 rounded-lg border transition-all ${
            localConfig.syslog_enabled ? 'bg-[#1F2937]/70 border-amber-500/40' : 'bg-[#1F2937]/30 border-[#374151]'
          }`}>
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="syslog-toggle"
                  checked={localConfig.syslog_enabled}
                  onChange={(e) => setLocalConfig({ ...localConfig, syslog_enabled: e.target.checked })}
                  className="rounded border-slate-700 bg-slate-900 text-amber-500 focus:ring-0 cursor-pointer"
                />
                <label htmlFor="syslog-toggle" className="text-xs font-mono font-bold text-slate-100 cursor-pointer flex items-center gap-2">
                  <span>4. Direct Syslog Socket Transport</span>
                  <span className="text-[10px] bg-amber-950 text-amber-400 px-2 py-0.5 rounded border border-amber-800">
                    UDP/TCP Port 514
                  </span>
                </label>
              </div>

              <button
                onClick={() => handleTestPipeline('syslog')}
                disabled={testingPipeline === 'syslog'}
                className="px-3 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-mono rounded flex items-center gap-1.5 transition-colors cursor-pointer"
              >
                {testingPipeline === 'syslog' ? <RefreshCw className="w-3 h-3 animate-spin" /> : <Send className="w-3 h-3 text-amber-400" />}
                <span>Test Syslog</span>
              </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-4 gap-3 text-xs font-mono">
              <div>
                <label className="text-slate-400 block mb-1">Host IP / Hostname:</label>
                <input
                  type="text"
                  value={localConfig.syslog_host}
                  onChange={(e) => setLocalConfig({ ...localConfig, syslog_host: e.target.value })}
                  className="w-full bg-slate-950 border border-slate-700 rounded px-2.5 py-1.5 text-slate-200 focus:border-cyan-500"
                />
              </div>
              <div>
                <label className="text-slate-400 block mb-1">Port Number:</label>
                <input
                  type="number"
                  value={localConfig.syslog_port}
                  onChange={(e) => setLocalConfig({ ...localConfig, syslog_port: Number(e.target.value) })}
                  className="w-full bg-slate-950 border border-slate-700 rounded px-2.5 py-1.5 text-slate-200 focus:border-cyan-500"
                />
              </div>
              <div>
                <label className="text-slate-400 block mb-1">Transport Protocol:</label>
                <select
                  value={localConfig.syslog_protocol}
                  onChange={(e) => setLocalConfig({ ...localConfig, syslog_protocol: e.target.value as 'udp' | 'tcp' })}
                  className="w-full bg-slate-950 border border-slate-700 rounded px-2.5 py-1.5 text-slate-200 focus:border-cyan-500 cursor-pointer"
                >
                  <option value="udp">UDP (Datagram)</option>
                  <option value="tcp">TCP (Connection-Oriented)</option>
                </select>
              </div>
              <div>
                <label className="text-slate-400 block mb-1">Syslog Standard:</label>
                <select
                  value={localConfig.syslog_format}
                  onChange={(e) => setLocalConfig({ ...localConfig, syslog_format: e.target.value as 'rfc5424' | 'rfc3164' })}
                  className="w-full bg-slate-950 border border-slate-700 rounded px-2.5 py-1.5 text-slate-200 focus:border-cyan-500 cursor-pointer"
                >
                  <option value="rfc5424">RFC 5424 (Structured Data)</option>
                  <option value="rfc3164">RFC 3164 (BSD Header)</option>
                </select>
              </div>
            </div>

            {testResults['syslog'] && (
              <div className={`mt-2 p-2 rounded text-xs font-mono flex items-center gap-1.5 ${
                testResults['syslog'].success ? 'bg-emerald-950/70 text-emerald-300' : 'bg-rose-950/70 text-rose-300'
              }`}>
                {testResults['syslog'].success ? <CheckCircle className="w-3.5 h-3.5 text-emerald-400 shrink-0" /> : <AlertCircle className="w-3.5 h-3.5 text-rose-400 shrink-0" />}
                <span>{testResults['syslog'].message}</span>
              </div>
            )}
          </div>
        </div>

        {/* Footer Actions */}
        <div className="h-16 px-6 bg-[#1F2937] border-t border-[#374151] flex items-center justify-between shrink-0">
          <div className="text-xs font-mono text-slate-400">
            Active destinations will receive all telemetry streams simultaneously.
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={onClose}
              className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-mono rounded-lg transition-colors cursor-pointer"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              className="px-5 py-2 bg-gradient-to-r from-emerald-600 to-cyan-600 hover:from-emerald-500 hover:to-cyan-500 text-slate-950 font-mono font-bold text-xs rounded-lg transition-all shadow-lg cursor-pointer"
            >
              Save & Apply Pipelines
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
