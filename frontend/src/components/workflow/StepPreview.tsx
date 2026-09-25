import React from 'react';
import { 
  ArrowLeft, ArrowRight, Clock, CheckCircle2, 
  Layers, Radio, Network
} from 'lucide-react';
import type { UseCase } from '../../types/workflow';

interface StepPreviewProps {
  useCase: UseCase;
  onBack: () => void;
  onNext: () => void;
}

export const StepPreview: React.FC<StepPreviewProps> = ({ useCase, onBack, onNext }) => {
  return (
    <div className="flex flex-col h-full overflow-hidden p-6 space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 border-b border-slate-800 pb-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
            <span>2. Preview Scenario & Evidence Contract</span>
            <span className="text-xs font-semibold px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/30">
              {useCase.category}
            </span>
          </h2>
          <p className="text-sm text-slate-400 mt-1">
            Review the expected progression, affected topology entities, required telemetry, and validation criteria.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={onBack}
            className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-sm font-medium transition focus:outline-none focus:ring-2 focus:ring-slate-500"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Choose Different</span>
          </button>

          <button
            onClick={onNext}
            className="flex items-center gap-1.5 px-5 py-2 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white text-sm font-medium transition shadow-lg shadow-cyan-900/30 focus:outline-none focus:ring-2 focus:ring-cyan-400"
          >
            <span>Configure Connection</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Main Grid: Left info & Topology / Right Phases & Validation */}
      <div className="flex-1 overflow-y-auto pr-1 grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Use Case Overview & Topology Blueprint */}
        <div className="lg:col-span-1 space-y-5">
          <div className="p-5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-4">
            <div>
              <span className="text-xs font-semibold text-cyan-400 uppercase tracking-wider block">Use Case</span>
              <h3 className="text-lg font-bold text-white mt-1 leading-snug">{useCase.name}</h3>
            </div>

            <div className="space-y-2 text-xs">
              <div>
                <span className="text-slate-500 font-medium block">Objective:</span>
                <p className="text-slate-300 mt-0.5 leading-relaxed">{useCase.objective}</p>
              </div>

              <div>
                <span className="text-slate-500 font-medium block">Description:</span>
                <p className="text-slate-400 mt-0.5 leading-relaxed">{useCase.description}</p>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2 pt-2 border-t border-slate-800/80 text-xs">
              <div className="p-2 rounded bg-slate-950/60 border border-slate-800/60">
                <span className="text-slate-500 block text-[10px]">Estimated Runtime</span>
                <span className="font-semibold text-slate-200 flex items-center gap-1 mt-0.5">
                  <Clock className="w-3.5 h-3.5 text-cyan-400" />
                  {useCase.estimated_runtime_sec} seconds
                </span>
              </div>
              <div className="p-2 rounded bg-slate-950/60 border border-slate-800/60">
                <span className="text-slate-500 block text-[10px]">Difficulty</span>
                <span className="font-semibold text-slate-200 mt-0.5 block">{useCase.difficulty}</span>
              </div>
            </div>
          </div>

          <div className="p-5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-3">
            <h4 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
              <Network className="w-4 h-4 text-cyan-400" />
              <span>Target Topology Blueprint</span>
            </h4>
            <div className="p-3 rounded-lg bg-slate-950/80 border border-slate-800/80 text-xs space-y-2">
              <div className="flex justify-between items-center text-slate-400">
                <span>Topology Model:</span>
                <code className="text-cyan-400 font-mono text-[11px]">{useCase.default_topology_id}</code>
              </div>
              <div className="flex justify-between items-center text-slate-400">
                <span>Vendor Scope:</span>
                <span className="text-slate-300 font-mono text-[11px]">{useCase.vendors.join(', ')}</span>
              </div>
              <div className="flex justify-between items-center text-slate-400">
                <span>Lifecycle Phases:</span>
                <span className="text-slate-300 font-semibold">{useCase.phases.length || 9} Distinct Phases</span>
              </div>
            </div>
          </div>

          <div className="p-5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-3">
            <h4 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
              <Radio className="w-4 h-4 text-cyan-400" />
              <span>Required Telemetry Sourcetypes</span>
            </h4>
            <div className="flex flex-wrap gap-1.5">
              {useCase.sourcetypes.map((st, i) => (
                <span key={i} className="px-2 py-1 rounded bg-slate-950 text-cyan-300 border border-slate-800 font-mono text-xs">
                  {st}
                </span>
              ))}
            </div>
          </div>
        </div>

        {/* Right Column: 9-Phase Progression & Validation Rules */}
        <div className="lg:col-span-2 space-y-5">
          <div className="p-5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-4">
            <h4 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
              <Layers className="w-4 h-4 text-cyan-400" />
              <span>Deterministic Lifecycle Progression</span>
            </h4>

            <div className="space-y-2.5">
              {useCase.phases && useCase.phases.length > 0 ? (
                useCase.phases.map((p, idx) => (
                  <div key={idx} className="flex items-start gap-3 p-3 rounded-lg bg-slate-950/60 border border-slate-800/80 text-xs">
                    <span className="px-2 py-1 rounded bg-slate-900 text-cyan-400 font-mono font-bold text-[10px] shrink-0 border border-slate-700/60">
                      {p.phase}
                    </span>
                    <div className="flex-1 min-w-0">
                      <div className="flex justify-between items-center">
                        <span className="font-semibold text-slate-200">{p.name}</span>
                        <span className="text-slate-500 font-mono text-[10px]">{p.duration_ticks} ticks</span>
                      </div>
                      <p className="text-slate-400 mt-0.5 leading-relaxed">{p.description}</p>
                      {p.expected_observations && p.expected_observations.length > 0 && (
                        <div className="mt-1 flex items-center gap-1.5 text-slate-400 text-[11px]">
                          <span className="text-slate-500">Expected:</span>
                          <span className="text-cyan-300/90 font-medium">{p.expected_observations.join(', ')}</span>
                        </div>
                      )}
                    </div>
                  </div>
                ))
              ) : (
                <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800 text-xs text-slate-400">
                  Standard 9-Phase progression: INITIALIZE → BASELINE → DEGRADE → FAULT → PROPAGATE → FAILOVER → RECOVER → VALIDATE → COMPLETE.
                </div>
              )}
            </div>
          </div>

          <div className="p-5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-3">
            <h4 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              <span>Evidence Contract & Validation Rules</span>
            </h4>
            <p className="text-xs text-slate-400">
              The automated validation engine will evaluate these criteria upon scenario completion:
            </p>

            <div className="space-y-2">
              {useCase.validation_rules && useCase.validation_rules.length > 0 ? (
                useCase.validation_rules.map((rule, idx) => (
                  <div key={idx} className="p-3 rounded-lg bg-slate-950/80 border border-slate-800/80 text-xs space-y-1">
                    <div className="flex justify-between items-center">
                      <span className="font-semibold text-slate-100 flex items-center gap-2">
                        <span className="w-2 h-2 rounded-full bg-cyan-400" />
                        {rule.name}
                      </span>
                      <span className="px-1.5 py-0.5 rounded bg-cyan-950 text-cyan-300 border border-cyan-800 font-mono text-[10px]">
                        {rule.type}
                      </span>
                    </div>
                    {rule.description && (
                      <p className="text-slate-400 text-[11px]">{rule.description}</p>
                    )}
                    {rule.target_sourcetype && (
                      <p className="text-slate-500 font-mono text-[10px]">
                        Target: <span className="text-slate-300">{rule.target_sourcetype}</span> (min {rule.min_count || 1} events)
                      </p>
                    )}
                  </div>
                ))
              ) : (
                <div className="p-3 rounded bg-slate-950 text-slate-400 text-xs">
                  Telemetry presence and state transition audit verified upon completion.
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
