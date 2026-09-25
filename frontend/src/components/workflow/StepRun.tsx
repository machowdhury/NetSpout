import React, { useState } from 'react';
import { 
  Play, Square, Copy, Check, CheckCircle2, 
  Terminal, ArrowRight, ArrowLeft, ExternalLink
} from 'lucide-react';
import type { UseCase, WorkflowRunState } from '../../types/workflow';

interface StepRunProps {
  useCase: UseCase;
  runState: WorkflowRunState;
  onStartRun: (speedMode: 'TEST' | 'ACCELERATED' | 'REALTIME') => void;
  onStopRun: () => void;
  onBack: () => void;
  onNext: () => void;
}

const LIFECYCLE_PHASES = [
  'INITIALIZE', 'BASELINE', 'DEGRADE', 'FAULT', 
  'PROPAGATE', 'FAILOVER', 'RECOVER', 'VALIDATE', 'COMPLETE'
];

export const StepRun: React.FC<StepRunProps> = ({
  useCase,
  runState,
  onStartRun,
  onStopRun,
  onBack,
  onNext
}) => {
  const [speedMode, setSpeedMode] = useState<'TEST' | 'ACCELERATED' | 'REALTIME'>('ACCELERATED');
  const [copiedRunId, setCopiedRunId] = useState(false);
  const [copiedSpl, setCopiedSpl] = useState(false);

  const spl = runState.splunk_search_query || (runState.run_id ? `index=idx_network_ops netspout_run_id="${runState.run_id}"` : '');
  const splunkSearchUrl = `http://localhost:8800/en-US/app/netspout/search?q=search%20${encodeURIComponent(spl || 'index=idx_network_ops')}`;

  const handleCopyRunId = () => {
    if (runState.run_id) {
      navigator.clipboard.writeText(runState.run_id);
      setCopiedRunId(true);
      setTimeout(() => setCopiedRunId(false), 2000);
    }
  };

  const handleCopySpl = () => {
    if (spl) {
      navigator.clipboard.writeText(spl);
      setCopiedSpl(true);
      setTimeout(() => setCopiedSpl(false), 2000);
    }
  };

  const isRunning = runState.status === 'running';
  const isFinished = runState.status === 'completed' || runState.status === 'stopped';
  const activePhaseIdx = LIFECYCLE_PHASES.indexOf(runState.phase.toUpperCase());

  return (
    <div className="flex flex-col h-full overflow-hidden p-6 space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 border-b border-slate-800 pb-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
            <span>4. Run Lifecycle Simulation</span>
            {runState.status === 'running' && (
              <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-amber-500/20 text-amber-400 border border-amber-500/40 animate-pulse">
                SIMULATION ACTIVE ({runState.phase})
              </span>
            )}
            {runState.status === 'completed' && (
              <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/40">
                COMPLETE (100%)
              </span>
            )}
            {runState.status === 'stopped' && (
              <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-rose-500/20 text-rose-400 border border-rose-500/40">
                STOPPED
              </span>
            )}
          </h2>
          <p className="text-sm text-slate-400 mt-1">
            Executing deterministic 9-phase scenario with stamped run identity and ground truth correlation.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={onBack}
            disabled={isRunning}
            className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-sm font-medium transition disabled:opacity-40"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Connection</span>
          </button>

          {isFinished && (
            <button
              onClick={onNext}
              className="flex items-center gap-1.5 px-5 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium transition shadow-lg shadow-emerald-900/30 focus:outline-none focus:ring-2 focus:ring-emerald-400"
            >
              <span>View Evidence & Proof</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* Run Identity & Controls Ribbon */}
      <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-lg bg-cyan-950/60 border border-cyan-800 text-cyan-400 font-mono text-sm">
            RUN ID:
          </div>
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-base font-bold text-white font-mono">
                {runState.run_id || 'NOT LAUNCHED'}
              </span>
              {runState.run_id && (
                <>
                  <button
                    onClick={handleCopyRunId}
                    className="p-1 rounded hover:bg-slate-800 text-slate-400 hover:text-slate-200 transition"
                    title="Copy Run ID"
                  >
                    {copiedRunId ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                  </button>
                  <button
                    onClick={handleCopySpl}
                    className="flex items-center gap-1 px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-cyan-400 text-xs font-semibold border border-slate-700 transition"
                    title="Copy run inspection SPL query"
                  >
                    {copiedSpl ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                    <span>{copiedSpl ? 'SPL Copied' : 'Copy SPL'}</span>
                  </button>
                  <a
                    href={splunkSearchUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-1 px-2.5 py-1 rounded bg-cyan-950/60 hover:bg-cyan-900/60 text-cyan-300 text-xs font-semibold border border-cyan-800 transition"
                    title="Open run query in Splunk Search app"
                  >
                    <span>Open in Splunk</span>
                    <ExternalLink className="w-3.5 h-3.5" />
                  </a>
                </>
              )}
            </div>
            <span className="text-xs text-slate-400">
              Scenario: <strong className="text-slate-200">{useCase.name}</strong>
            </span>
          </div>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-2">
          {!isRunning ? (
            <>
              <div className="flex items-center bg-slate-950 p-1 rounded-lg border border-slate-800 text-xs">
                {(['TEST', 'ACCELERATED', 'REALTIME'] as const).map((m) => (
                  <button
                    key={m}
                    onClick={() => setSpeedMode(m)}
                    className={`px-2.5 py-1 rounded font-medium transition ${
                      speedMode === m
                        ? 'bg-cyan-600 text-white shadow-sm'
                        : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    {m}
                  </button>
                ))}
              </div>

              <button
                onClick={() => onStartRun(speedMode)}
                className="flex items-center gap-2 px-5 py-2.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white font-bold text-sm transition shadow-lg shadow-cyan-900/40 focus:outline-none focus:ring-2 focus:ring-cyan-400"
              >
                <Play className="w-4 h-4 fill-current" />
                <span>{runState.status === 'idle' ? 'Launch Scenario' : 'Run Again'}</span>
              </button>
            </>
          ) : (
            <button
              onClick={onStopRun}
              className="flex items-center gap-2 px-5 py-2.5 rounded-lg bg-rose-600 hover:bg-rose-500 text-white font-bold text-sm transition shadow-lg shadow-rose-900/40 focus:outline-none focus:ring-2 focus:ring-rose-400"
            >
              <Square className="w-4 h-4 fill-current" />
              <span>Stop Run</span>
            </button>
          )}
        </div>
      </div>

      {/* 9-Phase Lifecycle Progression Track */}
      <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 space-y-2">
        <div className="flex justify-between items-center text-xs text-slate-400 font-medium px-1">
          <span>Lifecycle Phase Progression</span>
          <span>Phase {Math.max(0, activePhaseIdx + 1)} of 9</span>
        </div>

        <div className="grid grid-cols-3 md:grid-cols-9 gap-1.5">
          {LIFECYCLE_PHASES.map((p, idx) => {
            const isPast = activePhaseIdx > idx || runState.status === 'completed';
            const isCurrent = activePhaseIdx === idx && runState.status === 'running';

            let style = 'bg-slate-950/60 text-slate-500 border-slate-800';
            if (isCurrent) {
              style = 'bg-cyan-950/80 text-cyan-300 border-cyan-500 shadow-sm shadow-cyan-500/30 animate-pulse';
            } else if (isPast) {
              style = 'bg-emerald-950/30 text-emerald-400 border-emerald-800/60';
            }

            return (
              <div
                key={p}
                className={`flex flex-col items-center justify-center p-2 rounded-lg border text-center transition ${style}`}
              >
                <div className="flex items-center gap-1 mb-1">
                  {isPast ? (
                    <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                  ) : (
                    <span className="text-[10px] font-mono opacity-60">#{idx + 1}</span>
                  )}
                </div>
                <span className="text-[10px] font-bold tracking-wider">{p}</span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Metrics Counters Grid */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <div className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800 text-center">
          <span className="text-xs text-slate-400 font-medium">Elapsed Time</span>
          <div className="text-xl font-bold text-white font-mono mt-1">
            {runState.elapsed_sec.toFixed(1)}s
          </div>
        </div>

        <div className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800 text-center">
          <span className="text-xs text-slate-400 font-medium">Generated</span>
          <div className="text-xl font-bold text-cyan-400 font-mono mt-1">
            {runState.total_events}
          </div>
        </div>

        <div className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800 text-center">
          <span className="text-xs text-slate-400 font-medium">Dispatched</span>
          <div className="text-xl font-bold text-blue-400 font-mono mt-1">
            {runState.dispatched_events}
          </div>
        </div>

        <div className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800 text-center">
          <span className="text-xs text-slate-400 font-medium">Observed in Splunk</span>
          <div className={`text-xl font-bold font-mono mt-1 ${runState.observed_events > 0 ? 'text-emerald-400' : 'text-amber-400'}`}>
            {runState.observed_events}
          </div>
        </div>

        <div className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800 text-center">
          <span className="text-xs text-slate-400 font-medium">Velocity (EPS)</span>
          <div className="text-xl font-bold text-amber-400 font-mono mt-1">
            {runState.eps.toFixed(1)}
          </div>
        </div>
      </div>

      {/* Live Correlated Log Terminal Stream */}
      <div className="flex-1 flex flex-col rounded-xl bg-slate-950 border border-slate-800 overflow-hidden min-h-[220px]">
        <div className="px-4 py-2.5 bg-slate-900/80 border-b border-slate-800 flex justify-between items-center text-xs">
          <span className="font-mono text-slate-300 flex items-center gap-2">
            <Terminal className="w-3.5 h-3.5 text-cyan-400" />
            <span>Correlated Telemetry Stream (Live Stamped Logs)</span>
          </span>
          <span className="text-[11px] text-slate-500">
            Showing last {runState.recent_logs.length} records
          </span>
        </div>

        <div className="flex-1 overflow-y-auto p-3 font-mono text-[11px] space-y-1.5">
          {runState.recent_logs.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-slate-600 space-y-1">
              <Terminal className="w-6 h-6" />
              <span>Awaiting simulation execution...</span>
            </div>
          ) : (
            runState.recent_logs.map((log, i) => (
              <div key={i} className="leading-relaxed hover:bg-slate-900/50 p-1 rounded flex items-center flex-wrap">
                <span className="text-slate-500 mr-2 shrink-0">{log.timestamp}</span>
                <span className="text-cyan-400 font-semibold mr-2 shrink-0">[{log.netspout_phase || 'RUN'}]</span>
                {log.sourcetype && (
                  <span className="px-1.5 py-0.2 rounded bg-violet-950/80 text-violet-300 border border-violet-800/80 text-[10px] mr-2 shrink-0">
                    {log.sourcetype}
                  </span>
                )}
                <span className="text-amber-400 mr-2 shrink-0">{log.device_id}:</span>
                <span className="text-slate-300 break-all">{log.raw_log}</span>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};
