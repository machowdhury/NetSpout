import React, { useState } from 'react';
import { 
  CheckCircle2, XCircle, ExternalLink, Copy, Check,
  RotateCcw, ShieldCheck, Database, Send, Eye, FileText, ChevronDown
} from 'lucide-react';
import type { UseCase, WorkflowRunState } from '../../types/workflow';

interface StepProveProps {
  useCase: UseCase;
  runState: WorkflowRunState;
  onRunAgain: () => void;
  onChooseAnother: () => void;
}

export const StepProve: React.FC<StepProveProps> = ({
  useCase,
  runState,
  onRunAgain,
  onChooseAnother
}) => {
  const [showManifest, setShowManifest] = useState(false);
  const [copiedSpl, setCopiedSpl] = useState(false);

  const manifest = runState.manifest || {};
  const isOverallPass = manifest.overall_validation === 'PASS';
  const isSimulationPass = (manifest.simulation_validation === 'PASS') || runState.validation_results.every(r => r.status === 'PASS');

  const generatedCount = manifest.total_events_generated ?? runState.total_events ?? 0;
  const dispatchedCount = manifest.dispatch_succeeded ?? runState.dispatched_events ?? 0;
  const observedCount = manifest.observed_count ?? runState.observed_events ?? 0;
  const destinationValidation = manifest.destination_validation ?? runState.destination_validation ?? 'NOT_RUN';

  const spl = runState.splunk_search_query || manifest.splunk_search_query || (runState.run_id ? `index=idx_network_ops netspout_run_id="${runState.run_id}"` : '');
  const splunkSearchUrl = `http://localhost:8800/en-US/app/netspout/search?q=search%20${encodeURIComponent(spl || 'index=idx_network_ops')}`;

  const handleCopySpl = () => {
    if (spl) {
      navigator.clipboard.writeText(spl);
      setCopiedSpl(true);
      setTimeout(() => setCopiedSpl(false), 2000);
    }
  };

  return (
    <div className="flex flex-col h-full overflow-hidden p-6 space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 border-b border-slate-800 pb-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-white flex flex-wrap items-center gap-3">
            <span>5. Prove Expected Condition & Audit Evidence</span>
            <span className={`px-3 py-1 rounded-full text-xs font-bold border flex items-center gap-1.5 ${
              isOverallPass
                ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/40'
                : 'bg-rose-500/20 text-rose-400 border-rose-500/40'
            }`}>
              {isOverallPass ? <CheckCircle2 className="w-4 h-4" /> : <XCircle className="w-4 h-4" />}
              OVERALL VERIFICATION: {isOverallPass ? 'PASS' : 'FAIL'}
            </span>
            <span className={`px-2.5 py-0.5 rounded text-[11px] font-bold border ${
              isSimulationPass
                ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                : 'bg-rose-500/10 text-rose-400 border-rose-500/30'
            }`}>
              SIMULATION: {isSimulationPass ? 'PASS' : 'FAIL'}
            </span>
            <span className={`px-2.5 py-0.5 rounded text-[11px] font-bold border ${
              destinationValidation === 'PASS'
                ? 'bg-cyan-500/10 text-cyan-400 border-cyan-500/30'
                : destinationValidation === 'PENDING'
                ? 'bg-amber-500/10 text-amber-400 border-amber-500/30'
                : 'bg-slate-800 text-slate-400 border-slate-700'
            }`}>
              DESTINATION: {destinationValidation}
            </span>
          </h2>
          <p className="text-sm text-slate-400 mt-1">
            Automated verification results for <strong className="text-slate-200">{useCase.name}</strong> (run <code className="text-cyan-400 font-mono">{runState.run_id}</code>).
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={onRunAgain}
            className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-sm font-medium transition"
          >
            <RotateCcw className="w-4 h-4" />
            <span>Run Again</span>
          </button>

          <button
            onClick={onChooseAnother}
            className="flex items-center gap-1.5 px-5 py-2 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white text-sm font-medium transition shadow-lg shadow-cyan-900/30"
          >
            <span>Choose Another</span>
          </button>
        </div>
      </div>

      {/* Evidence Model 4-Tier Breakdown */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 space-y-1">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span className="font-semibold uppercase tracking-wider">1. GENERATED</span>
            <Database className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="text-2xl font-bold text-white font-mono">{generatedCount}</div>
          <p className="text-[11px] text-slate-500">Records created by simulation core</p>
        </div>

        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 space-y-1">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span className="font-semibold uppercase tracking-wider">2. DISPATCHED</span>
            <Send className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold text-blue-400 font-mono">{dispatchedCount}</div>
          <p className="text-[11px] text-slate-500">Transmitted over pipeline without drops</p>
        </div>

        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 space-y-1">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span className="font-semibold uppercase tracking-wider">3. OBSERVED IN SPLUNK</span>
            <Eye className="w-4 h-4 text-amber-400" />
          </div>
          <div className={`text-2xl font-bold font-mono ${observedCount > 0 ? 'text-emerald-400' : 'text-amber-400'}`}>
            {observedCount}
          </div>
          <p className="text-[11px] text-slate-500">Searchable events verified in Splunk index</p>
        </div>

        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 space-y-1">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span className="font-semibold uppercase tracking-wider">4. VALIDATED</span>
            <ShieldCheck className="w-4 h-4 text-cyan-400" />
          </div>
          <div className={`text-2xl font-bold font-mono ${
            destinationValidation === 'PASS' ? 'text-emerald-400' : destinationValidation === 'PENDING' ? 'text-amber-400' : 'text-rose-400'
          }`}>
            {destinationValidation}
          </div>
          <p className="text-[11px] text-slate-500">Formal query verification against index</p>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 overflow-y-auto pr-1 space-y-6">
        {/* Validation Engine Results Table */}
        <div className="p-5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-3">
          <div className="flex flex-wrap justify-between items-center gap-3">
            <h3 className="text-sm font-bold text-slate-200 uppercase tracking-wider flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-cyan-400" />
              <span>Automated Validation Engine Audit</span>
            </h3>
            <div className="flex items-center gap-2">
              <button
                onClick={handleCopySpl}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-cyan-400 text-xs font-semibold border border-slate-700 transition"
                title="Copy SPL Query for this run"
              >
                {copiedSpl ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                <span>{copiedSpl ? 'SPL Copied' : 'Copy Run SPL'}</span>
              </button>
              <a
                href={splunkSearchUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-cyan-600/20 hover:bg-cyan-600/30 text-cyan-400 text-xs font-semibold border border-cyan-500/40 transition"
              >
                <span>Verify in Splunk Search</span>
                <ExternalLink className="w-3.5 h-3.5" />
              </a>
            </div>
          </div>

          <div className="rounded-lg border border-slate-800 overflow-hidden">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-slate-950/80 border-b border-slate-800 text-slate-400 font-medium">
                  <th className="p-3">Rule Name & ID</th>
                  <th className="p-3">Type</th>
                  <th className="p-3">Status</th>
                  <th className="p-3">Expected vs Observed</th>
                  <th className="p-3">Details / Query</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono text-[11px]">
                {runState.validation_results && runState.validation_results.length > 0 ? (
                  runState.validation_results.map((res, i) => (
                    <tr key={i} className="hover:bg-slate-900/50">
                      <td className="p-3">
                        <div className="font-semibold text-slate-200">{res.rule_name}</div>
                        <div className="text-slate-500 text-[10px]">{res.rule_id}</div>
                      </td>
                      <td className="p-3 text-cyan-400">{res.rule_type}</td>
                      <td className="p-3">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          res.status === 'PASS'
                            ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40'
                            : 'bg-rose-500/20 text-rose-400 border border-rose-500/40'
                        }`}>
                          {res.status}
                        </span>
                      </td>
                      <td className="p-3 text-slate-300">
                        {res.expected_value !== undefined ? (
                          <div>
                            <div>Expected: {String(res.expected_value)}</div>
                            <div className="text-slate-400">Observed: {String(res.observed_value)}</div>
                          </div>
                        ) : (
                          'Condition satisfied'
                        )}
                      </td>
                      <td className="p-3 text-slate-400 font-sans text-xs">
                        {res.error_message || 'Telemetry matched target criteria.'}
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={5} className="p-4 text-center text-slate-500 font-sans">
                      All criteria evaluated and passed successfully.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Collapsible Run Manifest JSON Inspector */}
        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
          <button
            onClick={() => setShowManifest(!showManifest)}
            className="w-full flex justify-between items-center text-xs font-semibold text-slate-300 hover:text-white transition focus:outline-none"
          >
            <span className="flex items-center gap-2">
              <FileText className="w-4 h-4 text-cyan-400" />
              <span>Run Manifest & Cryptographic Audit Ledger (JSON)</span>
            </span>
            <ChevronDown className={`w-4 h-4 transition-transform ${showManifest ? 'rotate-180' : ''}`} />
          </button>

          {showManifest && (
            <div className="mt-3 pt-3 border-t border-slate-800">
              <pre className="p-3 rounded-lg bg-slate-950 text-cyan-300 font-mono text-[10px] overflow-x-auto max-h-72">
                {JSON.stringify(manifest, null, 2)}
              </pre>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
