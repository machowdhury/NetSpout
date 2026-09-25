import React, { useState, useEffect } from 'react';
import { StepChoose } from './StepChoose';
import { StepPreview } from './StepPreview';
import { StepConnect } from './StepConnect';
import { StepRun } from './StepRun';
import { StepProve } from './StepProve';
import type { 
  UseCase, WorkflowStep, PipelineConnection, 
  WorkflowRunState, ValidationResultItem 
} from '../../types/workflow';

interface FiveStepWorkflowProps {
  onOpenCanvas: () => void;
}

const STEPS: { id: WorkflowStep; label: string; number: number }[] = [
  { id: 'CHOOSE', label: 'Choose Use Case', number: 1 },
  { id: 'PREVIEW', label: 'Preview Scenario', number: 2 },
  { id: 'CONNECT', label: 'Connect Pipeline', number: 3 },
  { id: 'RUN', label: 'Run Simulation', number: 4 },
  { id: 'PROVE', label: 'Prove Expected Condition', number: 5 },
];

export const FiveStepWorkflow: React.FC<FiveStepWorkflowProps> = ({ onOpenCanvas }) => {
  const [currentStep, setCurrentStep] = useState<WorkflowStep>('CHOOSE');
  const [useCases, setUseCases] = useState<UseCase[]>([]);
  const [selectedUseCase, setSelectedUseCase] = useState<UseCase | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [connection, setConnection] = useState<PipelineConnection>({
    type: 'splunk_hec',
    name: 'Splunk HEC (HTTP Event Collector)',
    endpoint: 'https://127.0.0.1:8888/services/collector',
    token: '00000000-0000-0000-0000-000000000000',
    index: 'idx_network_ops',
    status: 'CONFIGURED',
    allow_insecure_tls: false
  });

  const [runState, setRunState] = useState<WorkflowRunState>({
    run_id: null,
    scenario_id: null,
    scenario_name: '',
    phase: 'INITIALIZE',
    status: 'idle',
    elapsed_sec: 0,
    total_events: 0,
    dispatched_events: 0,
    observed_events: 0,
    destination_validation: 'NOT_RUN',
    observation_status: 'NOT_RUN',
    splunk_search_query: '',
    eps: 0,
    affected_devices: [],
    manifest: null,
    validation_results: [],
    recent_logs: [],
    error: null
  });

  // Fetch canonical use cases on mount
  useEffect(() => {
    fetch('http://localhost:8081/api/use-cases')
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((data) => {
        if (data && Array.isArray(data.use_cases)) {
          setUseCases(data.use_cases);
          if (data.use_cases.length > 0) {
            setSelectedUseCase(data.use_cases[0]);
          }
        }
      })
      .catch((err) => {
        console.warn('Could not fetch /api/use-cases, falling back to /api/scenarios:', err);
        // Fallback to /api/scenarios
        fetch('http://localhost:8081/api/scenarios')
          .then(r => r.json())
          .then(scData => {
            if (scData && Array.isArray(scData.scenarios)) {
              const mapped: UseCase[] = scData.scenarios.map((s: any) => ({
                id: `uc-${s.id}`,
                scenario_id: s.id,
                name: s.name,
                category: s.category || 'NETWORK_OPERATIONS',
                domain: (s.category || 'NETWORK_OPERATIONS').replace('_', ' '),
                difficulty: s.difficulty || 'INTERMEDIATE',
                estimated_runtime_sec: s.estimated_duration_sec || 30,
                vendors: s.vendor_scope || [],
                sourcetypes: s.sourcetypes || [],
                description: s.description || '',
                objective: s.use_case?.objective || s.description || '',
                expected_observations: s.use_case?.expected_observations || [],
                validation_rules: s.validation_rules || [],
                default_topology_id: s.default_topology_id || 'default_secure',
                phases: s.phases || [],
                source: 'SCENARIO_BOUND'
              }));
              setUseCases(mapped);
              if (mapped.length > 0) setSelectedUseCase(mapped[0]);
            }
          })
          .catch(e => setError(e.message));
      })
      .finally(() => setLoading(false));
  }, []);

  // Execution Handler
  const handleStartRun = async (speedMode: 'TEST' | 'ACCELERATED' | 'REALTIME') => {
    if (!selectedUseCase) return;

    setRunState(prev => ({
      ...prev,
      status: 'running',
      phase: 'INITIALIZE',
      elapsed_sec: 0,
      total_events: 0,
      dispatched_events: 0,
      observed_events: 0,
      destination_validation: 'NOT_RUN',
      observation_status: 'NOT_RUN',
      splunk_search_query: '',
      recent_logs: [],
      error: null
    }));

    try {
      const res = await fetch(`http://localhost:8081/api/scenarios/${selectedUseCase.scenario_id}/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          mode: speedMode,
          seed: 42,
          dispatch_telemetry: true,
          transport_config: {
            hec_endpoint: connection.endpoint,
            hec_token: connection.token || '00000000-0000-0000-0000-000000000000',
            default_index: connection.index || 'idx_network_ops',
            hec_ssl_verify: !connection.allow_insecure_tls,
            hec_allow_insecure_tls: Boolean(connection.allow_insecure_tls)
          }
        })
      });

      const manifest = await res.json();
      if (!res.ok) throw new Error(manifest.detail || 'Execution failed');

      // Fetch logs
      let logs: any[] = [];
      try {
        const logRes = await fetch(`http://localhost:8081/api/scenarios/runs/${manifest.run_id}/logs?limit=50`);
        const logData = await logRes.json();
        logs = logData.logs || [];
      } catch (e) {}

      // Observation polling if pending
      let observedCount = manifest.observed_count ?? 0;
      let observationStatus = manifest.observation_status || 'NOT_RUN';
      let destValidation = manifest.destination_validation || 'NOT_RUN';

      if (observationStatus === 'OBSERVATION_PENDING' || (manifest.dispatch_succeeded > 0 && observedCount === 0)) {
        for (let attempt = 0; attempt < 3; attempt++) {
          await new Promise(r => setTimeout(r, 1000));
          try {
            const obsRes = await fetch(`http://localhost:8081/api/scenarios/runs/${manifest.run_id}/observation`);
            if (obsRes.ok) {
              const obsData = await obsRes.json();
              observedCount = obsData.observed_count ?? observedCount;
              observationStatus = obsData.observation_status ?? observationStatus;
              destValidation = obsData.destination_validation ?? destValidation;
              if (observationStatus === 'VERIFIED') break;
            }
          } catch (e) {}
        }
      }

      // Update manifest with final observation state
      manifest.observed_count = observedCount;
      manifest.observation_status = observationStatus;
      manifest.destination_validation = destValidation;

      if (destValidation === 'PASS' || observedCount > 0) {
        setConnection(c => ({
          ...c,
          status: 'VERIFIED',
          last_verified: new Date().toLocaleTimeString()
        }));
      }

      // Validation results
      const valResults: ValidationResultItem[] = (manifest.validation_results || []).map((v: any) => ({
        rule_id: v.rule_id || 'rule-1',
        rule_name: v.rule_name || 'Validation Check',
        status: v.status || 'PASS',
        rule_type: v.rule_type || 'COUNT_THRESHOLD',
        observed_value: v.observed_value,
        expected_value: v.expected_value,
        error_message: v.error_message
      }));

      setRunState({
        run_id: manifest.run_id,
        scenario_id: manifest.scenario_id,
        scenario_name: manifest.scenario_name,
        phase: 'COMPLETE',
        status: 'completed',
        elapsed_sec: manifest.duration_sec || 0.1,
        total_events: manifest.total_events_generated || 0,
        dispatched_events: manifest.dispatch_succeeded ?? 0,
        observed_events: observedCount,
        destination_validation: destValidation,
        observation_status: observationStatus,
        splunk_search_query: manifest.splunk_search_query || `index=${connection.index || 'idx_network_ops'} netspout_run_id="${manifest.run_id}"`,
        eps: manifest.duration_sec ? Math.round(manifest.total_events_generated / manifest.duration_sec) : 100,
        affected_devices: manifest.affected_devices || [],
        manifest,
        validation_results: valResults,
        recent_logs: logs,
        error: null
      });
    } catch (err: any) {
      setRunState(prev => ({
        ...prev,
        status: 'failed',
        error: err.message
      }));
    }
  };

  const handleStopRun = async () => {
    try {
      await fetch('http://localhost:8081/api/scenarios/run/stop', { method: 'POST' });
    } catch (e) {}
    setRunState(prev => ({ ...prev, status: 'stopped', phase: 'COMPLETE' }));
  };

  return (
    <div className="flex flex-col h-full w-full overflow-hidden bg-[#0B0F19] text-slate-100">
      {/* 5-Step Persistent Breadcrumb Step-Bar */}
      <div className="bg-slate-900/90 border-b border-slate-800 px-6 py-3 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center space-x-1 sm:space-x-2">
          {STEPS.map((s, idx) => {
            const isActive = currentStep === s.id;
            const isClickable = true;

            return (
              <div key={s.id} className="flex items-center">
                <button
                  onClick={() => setCurrentStep(s.id)}
                  disabled={!isClickable}
                  className={`flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-semibold transition focus:outline-none focus:ring-1 focus:ring-cyan-500 ${
                    isActive
                      ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/40'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                  }`}
                >
                  <span className={`w-4 h-4 rounded-full flex items-center justify-center text-[10px] font-bold ${
                    isActive ? 'bg-cyan-500 text-slate-950' : 'bg-slate-800 text-slate-400'
                  }`}>
                    {s.number}
                  </span>
                  <span className="hidden sm:inline">{s.label}</span>
                </button>
                {idx < STEPS.length - 1 && (
                  <span className="text-slate-600 mx-1">/</span>
                )}
              </div>
            );
          })}
        </div>

        <button
          onClick={onOpenCanvas}
          className="text-xs text-slate-400 hover:text-cyan-400 font-medium transition flex items-center gap-1"
        >
          <span>Switch to Interactive Canvas Orchestrator</span>
          <span className="text-cyan-500">→</span>
        </button>
      </div>

      {/* Step View Switcher */}
      <div className="flex-1 overflow-hidden">
        {currentStep === 'CHOOSE' && (
          <StepChoose
            useCases={useCases}
            selectedUseCase={selectedUseCase}
            onSelectUseCase={(uc) => setSelectedUseCase(uc)}
            onNext={() => setCurrentStep('PREVIEW')}
            loading={loading}
            error={error}
          />
        )}

        {currentStep === 'PREVIEW' && selectedUseCase && (
          <StepPreview
            useCase={selectedUseCase}
            onBack={() => setCurrentStep('CHOOSE')}
            onNext={() => setCurrentStep('CONNECT')}
          />
        )}

        {currentStep === 'CONNECT' && (
          <StepConnect
            connection={connection}
            onUpdateConnection={setConnection}
            onBack={() => setCurrentStep('PREVIEW')}
            onNext={() => setCurrentStep('RUN')}
          />
        )}

        {currentStep === 'RUN' && selectedUseCase && (
          <StepRun
            useCase={selectedUseCase}
            runState={runState}
            onStartRun={handleStartRun}
            onStopRun={handleStopRun}
            onBack={() => setCurrentStep('CONNECT')}
            onNext={() => setCurrentStep('PROVE')}
          />
        )}

        {currentStep === 'PROVE' && selectedUseCase && (
          <StepProve
            useCase={selectedUseCase}
            runState={runState}
            onRunAgain={() => setCurrentStep('RUN')}
            onChooseAnother={() => setCurrentStep('CHOOSE')}
          />
        )}
      </div>
    </div>
  );
};
