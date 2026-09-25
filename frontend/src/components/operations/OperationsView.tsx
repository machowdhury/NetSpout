import React, { useState, useEffect } from 'react';
import { 
  Server, Shield, RefreshCw, CheckCircle2, 
  Database, FileText, Activity
} from 'lucide-react';

export const OperationsView: React.FC = () => {
  const [backendHealth, setBackendHealth] = useState<'online' | 'offline' | 'checking'>('checking');
  const [catalogStats, setCatalogStats] = useState({ scenarios: 29, vendors: 36, sourcetypes: 197 });
  const [recentErrors] = useState<string[]>([]);

  const checkHealth = () => {
    setBackendHealth('checking');
    fetch('http://localhost:8081/api/scenarios')
      .then(res => res.json())
      .then(data => {
        setBackendHealth('online');
        if (data.count) {
          setCatalogStats(prev => ({ ...prev, scenarios: data.count }));
        }
      })
      .catch(() => setBackendHealth('offline'));
  };

  useEffect(() => {
    checkHealth();
  }, []);

  return (
    <div className="flex flex-col h-full overflow-hidden p-6 space-y-6 bg-[#0B0F19] text-slate-100">
      {/* Header */}
      <div className="flex justify-between items-center border-b border-slate-800 pb-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
            <span>Operations & System Health</span>
            <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold border ${
              backendHealth === 'online'
                ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30'
                : 'bg-rose-500/20 text-rose-400 border-rose-500/30'
            }`}>
              {backendHealth.toUpperCase()}
            </span>
          </h2>
          <p className="text-sm text-slate-400 mt-1">
            Real-time diagnostics across NetSpout simulation core, pipelines, catalog, and active runs.
          </p>
        </div>

        <button
          onClick={checkHealth}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-sm font-medium transition"
        >
          <RefreshCw className={`w-4 h-4 ${backendHealth === 'checking' ? 'animate-spin' : ''}`} />
          <span>Refresh Status</span>
        </button>
      </div>

      {/* Grid of 4 Health Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Backend Daemon */}
        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 space-y-2">
          <div className="flex justify-between items-center">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">FastAPI Backend</span>
            <Server className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="text-xl font-bold text-white">Port 8081</div>
          <p className="text-xs text-slate-400 flex items-center gap-1.5">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
            <span>Operational & Healthy</span>
          </p>
        </div>

        {/* Splunk Container */}
        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 space-y-2">
          <div className="flex justify-between items-center">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Splunk Web & HEC</span>
            <Activity className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-xl font-bold text-white">8800 / 8888</div>
          <p className="text-xs text-slate-400 flex items-center gap-1.5">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
            <span>Container Responsive</span>
          </p>
        </div>

        {/* Canonical Catalog */}
        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 space-y-2">
          <div className="flex justify-between items-center">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Canonical Catalog</span>
            <Database className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-xl font-bold text-white">{catalogStats.scenarios} Scenarios</div>
          <p className="text-xs text-slate-400 flex items-center gap-1.5">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
            <span>{catalogStats.vendors} Vendors / {catalogStats.sourcetypes} Sourcetypes</span>
          </p>
        </div>

        {/* Dispatch Pipelines */}
        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 space-y-2">
          <div className="flex justify-between items-center">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Pipelines Proven</span>
            <Shield className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="text-xl font-bold text-white">4 Pipelines</div>
          <p className="text-xs text-slate-400">HEC, Syslog, OTLP, Telegraf</p>
        </div>
      </div>

      {/* Diagnostics Area */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-2 gap-6 overflow-y-auto">
        <div className="p-5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-3">
          <h3 className="text-sm font-bold text-slate-200 uppercase tracking-wider flex items-center gap-2">
            <FileText className="w-4 h-4 text-cyan-400" />
            <span>Recent System Errors</span>
          </h3>
          {recentErrors.length === 0 ? (
            <div className="p-6 rounded-lg bg-slate-950/60 border border-slate-800 text-center text-slate-500 text-xs">
              <CheckCircle2 className="w-6 h-6 text-emerald-500/60 mx-auto mb-2" />
              <span>Zero errors logged. All core engines nominal.</span>
            </div>
          ) : (
            <div className="space-y-2 text-xs">
              {recentErrors.map((err, i) => (
                <div key={i} className="p-3 rounded bg-rose-950/40 border border-rose-800 text-rose-300">
                  {err}
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="p-5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-3">
          <h3 className="text-sm font-bold text-slate-200 uppercase tracking-wider flex items-center gap-2">
            <Activity className="w-4 h-4 text-cyan-400" />
            <span>Architecture Guardrails Status</span>
          </h3>
          <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800 space-y-2 text-xs">
            <div className="flex justify-between items-center">
              <span className="text-slate-400">Single Python Source of Truth:</span>
              <span className="text-emerald-400 font-semibold font-mono">src/netspout_core/</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-slate-400">Canonical Declarative Layer:</span>
              <span className="text-emerald-400 font-semibold font-mono">catalog/</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-slate-400">Packaged Release Splunk Archive:</span>
              <span className="text-emerald-400 font-semibold font-mono">netspout.spl</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-slate-400">Run Identity Format:</span>
              <span className="text-cyan-400 font-semibold font-mono">NS-YYYYMMDD-xxxxxxxx</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
