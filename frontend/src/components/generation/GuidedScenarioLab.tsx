import { useEffect, useMemo, useState, type ReactNode } from 'react';
import { generationApi } from '../../lib/generationApi';
import type {
  GenerationCapabilities,
  GenerationPreflight,
  GenerationPreview,
  GenerationRequest,
  GenerationRun,
  GenerationScenario,
  GuidedInvestigationStep,
  InvestigationResult,
} from '../../types/generation';
import type { ExperienceMode } from '../../app/navigation';
import { TopologyPreview } from './TopologyPreview';
import type { VisualizationLens } from './scenarioVisualization';

type GuidedStep = 'UNDERSTAND' | 'PREPARE' | 'RUN' | 'OBSERVE' | 'INVESTIGATE' | 'VALIDATE';
type GuidedView = 'HOME' | GuidedStep | 'COMPLETE';

const DEFAULT_STEPS: GuidedStep[] = ['UNDERSTAND', 'PREPARE', 'RUN', 'OBSERVE', 'INVESTIGATE', 'VALIDATE'];

const badge = (value: string) => value.replaceAll('_', ' ');

function requestFor(
  scenario: GenerationScenario,
  nativeLifecycle: boolean,
): GenerationRequest {
  return {
    mode: 'SCENARIO',
    selection_id: scenario.scenario_id,
    transport_id: 'transport-local-hec',
    destination_id: 'destination-local-docker-splunk',
    count: nativeLifecycle ? 1 : scenario.timeline.length,
    rate_eps: 10,
    duration_seconds: nativeLifecycle ? undefined : 1,
    scenario_parameters: { intensity: 1 },
  };
}

export function GuidedScenarioLab({ experienceMode }: { experienceMode: ExperienceMode }) {
  const [capabilities, setCapabilities] = useState<GenerationCapabilities | null>(null);
  const [selectedScenarioId, setSelectedScenarioId] = useState('');
  const [loadError, setLoadError] = useState<string | null>(null);
  const [view, setView] = useState<GuidedView>('HOME');
  const [completed, setCompleted] = useState<Set<GuidedStep>>(new Set());
  const [preview, setPreview] = useState<GenerationPreview | null>(null);
  const [preflight, setPreflight] = useState<GenerationPreflight | null>(null);
  const [run, setRun] = useState<GenerationRun | null>(null);
  const [previousRunId, setPreviousRunId] = useState<string | null>(null);
  const [activePhase, setActivePhase] = useState<string | undefined>();
  const [lens, setLens] = useState<VisualizationLens>('OVERVIEW');
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [selectedRelationshipId, setSelectedRelationshipId] = useState<string | null>(null);
  const [hintsVisible, setHintsVisible] = useState(false);
  const [investigationIndex, setInvestigationIndex] = useState(0);
  const [investigationResults, setInvestigationResults] = useState<Record<string, InvestigationResult>>({});
  const [explanations, setExplanations] = useState<Set<string>>(new Set());
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  useEffect(() => {
    generationApi.capabilities()
      .then((value) => {
        setCapabilities(value);
        setSelectedScenarioId(
          value.scenarios.find((item) => item.runnable)?.scenario_id ?? '',
        );
      })
      .catch((error: unknown) => setLoadError(error instanceof Error ? error.message : 'Scenario capabilities unavailable'));
  }, []);

  const scenario = capabilities?.scenarios.find(
    (item) => item.scenario_id === selectedScenarioId && item.runnable,
  ) ?? null;
  const request = useMemo(
    () => (
      scenario
        ? requestFor(
          scenario,
          capabilities?.native_runtime?.scenario_ids?.includes(
            scenario.scenario_id,
          ) ?? false,
        )
        : null
    ),
    [capabilities, scenario],
  );
  const steps = (capabilities?.guided_workflow ?? DEFAULT_STEPS) as GuidedStep[];
  const sources = capabilities?.sources.filter((source) => scenario?.source_ids.includes(source.source_id)) ?? [];
  const investigations = useMemo(
    () => guidedInvestigations(scenario, preview),
    [scenario, preview],
  );

  const markComplete = (step: GuidedStep) => {
    setCompleted((current) => new Set([...current, step]));
  };

  const start = async (advanced = false) => {
    if (!request) return;
    setBusy(true);
    setActionError(null);
    try {
      const value = await generationApi.preview(request);
      setPreview(value);
      setActivePhase(value.scenario?.timeline[0]?.stage);
      setSelectedNodeId(null);
      setSelectedRelationshipId(null);
      setView(advanced ? 'PREPARE' : 'UNDERSTAND');
      if (advanced) markComplete('UNDERSTAND');
    } catch (error) {
      setActionError(error instanceof Error ? error.message : 'Scenario preview unavailable');
    } finally {
      setBusy(false);
    }
  };

  const prepare = async () => {
    if (!request) return;
    setBusy(true);
    setActionError(null);
    try {
      setPreflight(await generationApi.preflight(request));
    } catch (error) {
      setActionError(error instanceof Error ? error.message : 'Preflight unavailable');
    } finally {
      setBusy(false);
    }
  };

  const execute = async () => {
    if (!request) return;
    setBusy(true);
    setActionError(null);
    try {
      const value = await generationApi.run(request);
      setRun(value);
      setActivePhase(value.current_phase);
      markComplete('RUN');
    } catch (error) {
      setActionError(error instanceof Error ? error.message : 'Scenario run failed');
    } finally {
      setBusy(false);
    }
  };

  const observe = async () => {
    if (!run) return;
    setBusy(true);
    setActionError(null);
    try {
      const value = await generationApi.observe(run.run_id);
      setRun(value);
      if (value.evidence.find((item) => item.stage === 'SPLUNK_OBSERVED')?.state === 'PROVEN') {
        markComplete('OBSERVE');
      }
    } catch (error) {
      setActionError(error instanceof Error ? error.message : 'Splunk observation unavailable');
    } finally {
      setBusy(false);
    }
  };

  const investigate = async (step: GuidedInvestigationStep) => {
    if (!run) return;
    setBusy(true);
    setActionError(null);
    try {
      const value = await generationApi.investigate(run.run_id, step.recipe_id);
      setInvestigationResults((current) => ({ ...current, [step.step_id]: value }));
      if (value.status === 'SUCCEEDED' && investigationIndex === investigations.length - 1) {
        markComplete('INVESTIGATE');
      }
    } catch (error) {
      setActionError(error instanceof Error ? error.message : 'Investigation unavailable');
    } finally {
      setBusy(false);
    }
  };

  const replay = async () => {
    if (!request || !run) return;
    setBusy(true);
    setActionError(null);
    try {
      const oldRunId = run.run_id;
      const value = await generationApi.run(request);
      setPreviousRunId(oldRunId);
      setRun(value);
      setActivePhase(value.current_phase);
      setInvestigationResults({});
      setInvestigationIndex(0);
      setCompleted(new Set(['UNDERSTAND', 'PREPARE', 'RUN']));
      setView('RUN');
    } catch (error) {
      setActionError(error instanceof Error ? error.message : 'Replay unavailable');
    } finally {
      setBusy(false);
    }
  };

  if (loadError) return <div className="generation-state generation-state--error">{loadError}</div>;
  if (!capabilities || !scenario || !request) return <div className="generation-state">Loading guided scenario…</div>;

  const go = (next: GuidedStep) => {
    const index = steps.indexOf(next);
    const available = index === 0 || completed.has(steps[index - 1]) || next === view;
    if (available) setView(next);
  };

  return (
    <div className="guided-lab" data-testid="guided-scenario-lab">
      {view !== 'HOME' && view !== 'COMPLETE' && (
        <GuidedProgress steps={steps} active={view} completed={completed} onNavigate={go} />
      )}
      {actionError && <div className="generation-alert generation-alert--error" role="alert">{actionError}</div>}

      {view === 'HOME' && (
        <>
          <label className="guided-scenario-picker">
            <span>Choose guided scenario</span>
            <select
              aria-label="Choose guided scenario"
              value={selectedScenarioId}
              onChange={(event) => {
                setSelectedScenarioId(event.target.value);
                setCompleted(new Set());
                setPreview(null);
                setPreflight(null);
                setRun(null);
                setLens('OVERVIEW');
              }}
            >
              {capabilities.scenarios
                .filter((item) => item.runnable)
                .map((item) => (
                  <option key={item.scenario_id} value={item.scenario_id}>
                    {item.title}
                  </option>
                ))}
            </select>
          </label>
          <ScenarioHome
            scenario={scenario}
            sources={sources}
            busy={busy}
            onStart={() => start(false)}
            onAdvanced={() => start(true)}
            lens={lens}
            onLens={setLens}
            selectedNodeId={selectedNodeId}
            selectedRelationshipId={selectedRelationshipId}
            onNode={setSelectedNodeId}
            onRelationship={setSelectedRelationshipId}
          />
        </>
      )}

      {view === 'UNDERSTAND' && preview && (
        <section className="guided-workspace" aria-labelledby="understand-heading">
          <SectionHeading eyebrow="Guided lab · Understand" title="Understand the modeled incident" id="understand-heading" />
          <div className="guided-teaching-grid">
            <TeachingCard title="What is normal?" text={scenario.baseline_description} fallback="Baseline guidance is not declared." />
            <TeachingCard title="What will change?" text={scenario.incident_description} fallback="Incident-transition guidance is not declared." />
            <TeachingCard title="What evidence should appear?" text={scenario.expected_evidence.join(' ')} fallback="Expected evidence is not declared." />
            <TeachingCard title="What should you discover?" text={scenario.discovery_prompt} fallback="A discovery prompt is not declared." />
          </div>
          <button type="button" className="guided-link-button" onClick={() => setHintsVisible((value) => !value)}>
            {hintsVisible ? 'Hide learning hints' : 'Show learning hints'}
          </button>
          {hintsVisible && (
            <ul className="guided-hints">
              {(scenario.learning_hints ?? []).map((hint) => <li key={hint}>{hint}</li>)}
            </ul>
          )}
          <TopologyPanel
            scenario={scenario}
            sources={sources}
            run={run}
            activePhase={activePhase}
            lens={lens}
            onLens={setLens}
            selectedNodeId={selectedNodeId}
            selectedRelationshipId={selectedRelationshipId}
            onNode={setSelectedNodeId}
            onRelationship={setSelectedRelationshipId}
          />
          <GuidedActions
            back={() => setView('HOME')}
            next={() => { markComplete('UNDERSTAND'); setView('PREPARE'); }}
            nextLabel="Prepare environment"
          />
        </section>
      )}

      {view === 'PREPARE' && preview && (
        <section className="guided-workspace" aria-labelledby="prepare-heading">
          <SectionHeading eyebrow="Guided lab · Prepare" title="Prepare the lab environment" id="prepare-heading" />
          <div className="guided-readiness-summary">
            <div><span>Telemetry channels</span><strong>{preview.bindings.map((item) => (item.source_transport_id ?? item.transport_id).replace(/^transport-native-/, '')).join(' · ')}</strong></div>
            <div><span>Splunk readiness</span><strong>{preview.integration_readiness.every((item) => item.detected || item.requirement !== 'REQUIRED') ? 'READY' : 'ACTION REQUIRED'}</strong></div>
            <div><span>Integrations</span><strong>{preview.integration_readiness.length} declared</strong></div>
          </div>
          <div className="guided-preflight">
            <div className="guided-section-title"><h4>Environment readiness</h4>{preflight && <Status value={preflight.state} />}</div>
            {!preflight ? (
              <div className="generation-empty">Run the Phase 3 preflight against this exact composition.</div>
            ) : preflight.checks.map((check) => (
              <div className="guided-check" key={check.check_id}>
                <span aria-hidden>{check.state === 'PASS' ? '✓' : check.state === 'WARN' ? '!' : '×'}</span>
                <div><strong>{check.label}</strong><small>{check.detail}</small></div>
                <Status value={check.state} />
              </div>
            ))}
          </div>
          <GuidedActions
            back={() => setView('UNDERSTAND')}
            middle={<button type="button" onClick={prepare} disabled={busy}>{busy ? 'Checking…' : 'Run preflight'}</button>}
            next={() => { markComplete('PREPARE'); setView('RUN'); }}
            nextLabel="Continue to run"
            nextDisabled={!preflight || preflight.state === 'BLOCKED'}
          />
        </section>
      )}

      {view === 'RUN' && preview && (
        <section className="guided-workspace" aria-labelledby="run-heading">
          <SectionHeading eyebrow="Guided lab · Run" title="Run the modeled lifecycle" id="run-heading" />
          {previousRunId && run && <div className="guided-run-boundary">Replay created a new run context. Previous <code>{previousRunId}</code> · Current <code>{run.run_id}</code></div>}
          {!run ? (
            <div className="guided-run-launch">
              <strong>{scenario.timeline.length} manifest-defined phases</strong>
              <span>Execution uses the validated Phase 3 composition and destination.</span>
              <button type="button" className="generation-run-button" onClick={execute} disabled={busy}>{busy ? 'Running…' : 'Run scenario'}</button>
            </div>
          ) : (
            <div className="guided-run-strip">
              <div><span>Run ID</span><code>{run.run_id}</code></div>
              <div><span>Status</span><strong>{run.status}</strong></div>
              <div><span>Channels</span><strong>{run.channel_results?.length || run.source_ids.length}</strong></div>
              <div><span>Current phase</span><strong>{run.current_phase}</strong></div>
            </div>
          )}
          <InteractiveTimeline scenario={scenario} run={run} activePhase={activePhase} onPhase={(phase, nodeId) => {
            setActivePhase(phase);
            if (nodeId) setSelectedNodeId(nodeId);
          }} />
          <TopologyPanel
            scenario={scenario}
            sources={sources}
            run={run}
            activePhase={activePhase}
            lens={lens}
            onLens={setLens}
            selectedNodeId={selectedNodeId}
            selectedRelationshipId={selectedRelationshipId}
            onNode={setSelectedNodeId}
            onRelationship={setSelectedRelationshipId}
          />
          <GuidedActions
            back={() => setView('PREPARE')}
            next={() => setView('OBSERVE')}
            nextLabel="Observe evidence"
            nextDisabled={!run}
          />
        </section>
      )}

      {view === 'OBSERVE' && run && (
        <section className="guided-workspace" aria-labelledby="observe-heading">
          <SectionHeading eyebrow="Guided lab · Observe" title="Connect evidence to the environment" id="observe-heading" />
          <div className="guided-correlation" aria-label="Correlation view">
            <span>ENTITY</span><b>↕</b><span>TIMELINE</span><b>↕</b><span>TELEMETRY</span><b>↕</b><span>SPLUNK EVENT</span><b>↕</b><span>INVESTIGATION</span>
          </div>
          {selectedNodeId && (
            <div className="guided-evidence-focus" role="status">
              Evidence focus: <strong>{scenario.nodes.find((node) => node.node_id === selectedNodeId)?.label ?? selectedNodeId}</strong>
              <span>{channelCountForNode(run, scenario, selectedNodeId, 'GENERATED')} generated observations reported by selected channels</span>
            </div>
          )}
          <div className="guided-evidence-grid">
            {(run.channel_results?.length
              ? run.channel_results.flatMap((channel) => channel.evidence.map((item) => ({ ...item, channel: channel.channel, sourceId: channel.source_id })))
              : run.evidence.map((item) => ({ ...item, channel: 'RUN', sourceId: run.source_ids[0] }))).map((item, index) => (
              <button
                type="button"
                key={`${item.channel}-${item.stage}-${index}`}
                onClick={() => {
                  const node = scenario.nodes.find((candidate) => candidate.source_ids.includes(item.sourceId));
                  setSelectedNodeId(node?.node_id ?? null);
                }}
              >
                <span>{item.channel} · {item.stage.replaceAll('_', ' ')}</span>
                <strong>{item.count}</strong>
                <Status value={item.state} />
                <small>{item.detail}</small>
              </button>
            ))}
          </div>
          <button type="button" onClick={observe} disabled={busy}>{busy ? 'Searching Splunk…' : 'Refresh Splunk observation'}</button>
          <TopologyPanel
            scenario={scenario}
            sources={sources}
            run={run}
            activePhase={activePhase}
            lens="SPLUNK"
            onLens={setLens}
            selectedNodeId={selectedNodeId}
            selectedRelationshipId={selectedRelationshipId}
            onNode={setSelectedNodeId}
            onRelationship={setSelectedRelationshipId}
          />
          <GuidedActions
            back={() => setView('RUN')}
            next={() => setView('INVESTIGATE')}
            nextLabel="Investigate"
            nextDisabled={!completed.has('OBSERVE')}
          />
        </section>
      )}

      {view === 'INVESTIGATE' && run && (
        <GuidedInvestigation
          steps={investigations}
          index={investigationIndex}
          result={investigations[investigationIndex] ? investigationResults[investigations[investigationIndex].step_id] : undefined}
          explanationVisible={investigations[investigationIndex] ? explanations.has(investigations[investigationIndex].step_id) : false}
          busy={busy}
          run={run}
          recipe={preview?.investigations.find((item) => item.recipe_id === investigations[investigationIndex]?.recipe_id)}
          onRun={() => investigations[investigationIndex] && investigate(investigations[investigationIndex])}
          onHint={() => setHintsVisible((value) => !value)}
          hintVisible={hintsVisible}
          onExplanation={() => {
            const step = investigations[investigationIndex];
            if (step) setExplanations((current) => new Set([...current, step.step_id]));
          }}
          onViewTopology={() => {
            const step = investigations[investigationIndex];
            setSelectedNodeId(step?.node_ids[0] ?? null);
          }}
          onPrevious={() => setInvestigationIndex((value) => Math.max(0, value - 1))}
          onNext={() => setInvestigationIndex((value) => Math.min(investigations.length - 1, value + 1))}
          onBack={() => setView('OBSERVE')}
          onValidate={() => setView('VALIDATE')}
          canValidate={completed.has('INVESTIGATE')}
        >
          <TopologyPanel
            scenario={scenario}
            sources={sources}
            run={run}
            activePhase={activePhase}
            lens={lens}
            onLens={setLens}
            selectedNodeId={selectedNodeId}
            selectedRelationshipId={selectedRelationshipId}
            onNode={setSelectedNodeId}
            onRelationship={setSelectedRelationshipId}
          />
        </GuidedInvestigation>
      )}

      {view === 'VALIDATE' && run && (
        <ValidationStep
          scenario={scenario}
          run={run}
          onBack={() => setView('INVESTIGATE')}
          onComplete={() => { markComplete('VALIDATE'); setView('COMPLETE'); }}
        />
      )}

      {view === 'COMPLETE' && run && (
        <CompletionSummary
          scenario={scenario}
          run={run}
          investigationCount={Object.values(investigationResults).filter((item) => item.status === 'SUCCEEDED').length}
          onReplay={replay}
          busy={busy}
          experienceMode={experienceMode}
        />
      )}
    </div>
  );
}

function ScenarioHome({
  scenario,
  sources,
  busy,
  onStart,
  onAdvanced,
  lens,
  onLens,
  selectedNodeId,
  selectedRelationshipId,
  onNode,
  onRelationship,
}: {
  scenario: GenerationScenario;
  sources: GenerationCapabilities['sources'];
  busy: boolean;
  onStart: () => void;
  onAdvanced: () => void;
  lens: VisualizationLens;
  onLens: (lens: VisualizationLens) => void;
  selectedNodeId: string | null;
  selectedRelationshipId: string | null;
  onNode: (id: string | null) => void;
  onRelationship: (id: string | null) => void;
}) {
  return (
    <section className="scenario-home" aria-labelledby="scenario-home-heading">
      <header className="scenario-home__hero">
        <div>
          <span className="generation-eyebrow">Guided Scenario Experience</span>
          <h2 id="scenario-home-heading">{scenario.title}</h2>
          <p>{scenario.story}</p>
          <div className="scenario-home__meta">
            <Status value={scenario.difficulty} />
            <span>{scenario.domain ?? 'Domain not declared'}</span>
            <span>~{scenario.expected_duration_minutes} min</span>
            <Status value={scenario.guided_completeness?.state ?? 'PARTIAL'} />
          </div>
          <div className="scenario-home__actions">
            <button type="button" className="generation-primary" onClick={onStart} disabled={busy}>Start guided lab</button>
            <button type="button" onClick={onAdvanced} disabled={busy}>Advanced run</button>
          </div>
        </div>
        <div className="scenario-home__impact">
          <span>Why it matters</span>
          <strong>{scenario.business_impact}</strong>
          <small>{scenario.guided_completeness?.passed ?? 0}/{scenario.guided_completeness?.total ?? 12} guided completeness checks · no automatic READY promotion</small>
        </div>
      </header>
      <div className="scenario-home__section">
        <div className="guided-section-title"><h3>What you will learn</h3><span>Manifest-defined objectives</span></div>
        <ul className="scenario-home__objectives">{scenario.learning_objectives.map((item) => <li key={item}>{item}</li>)}</ul>
      </div>
      <TopologyPanel
        scenario={scenario}
        sources={sources}
        run={null}
        lens={lens}
        onLens={onLens}
        selectedNodeId={selectedNodeId}
        selectedRelationshipId={selectedRelationshipId}
        onNode={onNode}
        onRelationship={onRelationship}
      />
      <div className="scenario-home__lower">
        <div><span>Telemetry</span>{sources.map((source) => <strong key={source.source_id}>{source.telemetry_source}</strong>)}</div>
        <div><span>Splunk readiness</span><strong>{scenario.integration_count} evidence-backed integration requirement</strong></div>
        <div><span>Provenance</span><strong>{sources.flatMap((source) => source.provenance).join(' · ')}</strong></div>
      </div>
    </section>
  );
}

function GuidedProgress({ steps, active, completed, onNavigate }: { steps: GuidedStep[]; active: GuidedStep; completed: Set<GuidedStep>; onNavigate: (step: GuidedStep) => void }) {
  return (
    <nav className="guided-progress" aria-label="Guided lab progress">
      {steps.map((step, index) => {
        const available = index === 0 || completed.has(steps[index - 1]) || step === active;
        return (
          <button type="button" key={step} disabled={!available} className={step === active ? 'is-active' : completed.has(step) ? 'is-complete' : ''} onClick={() => onNavigate(step)}>
            <span>{completed.has(step) ? '✓' : index + 1}</span>{step}
          </button>
        );
      })}
    </nav>
  );
}

function TopologyPanel(props: {
  scenario: GenerationScenario;
  sources: GenerationCapabilities['sources'];
  run: GenerationRun | null;
  activePhase?: string;
  lens: VisualizationLens;
  onLens: (lens: VisualizationLens) => void;
  selectedNodeId: string | null;
  selectedRelationshipId: string | null;
  onNode: (id: string | null) => void;
  onRelationship: (id: string | null) => void;
}) {
  return (
    <div className="guided-topology-panel">
      <div className="guided-section-title">
        <div><h3>Scenario environment</h3><span>Topology, timeline and evidence share one manifest</span></div>
        <div className="guided-lenses" aria-label="Visualization lens">
          {(['OVERVIEW', 'TELEMETRY', 'INCIDENT', 'SPLUNK'] as VisualizationLens[]).map((lens) => (
            <button type="button" key={lens} aria-pressed={props.lens === lens} className={props.lens === lens ? 'is-active' : ''} onClick={() => props.onLens(lens)}>
              {lens === 'OVERVIEW' ? 'Overview' : `${lens[0]}${lens.slice(1).toLowerCase()} Lens`}
            </button>
          ))}
        </div>
      </div>
      <TopologyPreview
        scenario={props.scenario}
        activePhase={props.activePhase}
        lens={props.lens}
        run={props.run}
        sources={props.sources}
        selectedNodeId={props.selectedNodeId}
        selectedRelationshipId={props.selectedRelationshipId}
        onSelectNode={props.onNode}
        onSelectRelationship={props.onRelationship}
      />
    </div>
  );
}

function InteractiveTimeline({ scenario, run, activePhase, onPhase }: { scenario: GenerationScenario; run: GenerationRun | null; activePhase?: string; onPhase: (phase: string, nodeId?: string) => void }) {
  return (
    <div className="guided-timeline" aria-label="Scenario timeline">
      {scenario.timeline.map((step, index) => {
        const event = run?.events.find((item) => item.phase === step.stage);
        const isCurrent = run?.current_phase === step.stage;
        const stateChanges = { ...step.state_changes, ...(step.entity_state_changes ?? {}) };
        return (
          <button type="button" key={step.step_id} className={activePhase === step.stage || isCurrent ? 'is-active' : event ? 'is-complete' : ''} onClick={() => onPhase(step.stage, Object.keys(stateChanges)[0])}>
            <span>{index + 1}</span>
            <strong>{step.stage}</strong>
            <small>{step.description}</small>
            <em>{event ? 'Backend event available' : isCurrent ? 'Current backend phase' : 'No phase event returned'}</em>
          </button>
        );
      })}
    </div>
  );
}

function GuidedInvestigation({
  steps,
  index,
  result,
  explanationVisible,
  busy,
  run,
  recipe,
  onRun,
  onHint,
  hintVisible,
  onExplanation,
  onViewTopology,
  onPrevious,
  onNext,
  onBack,
  onValidate,
  canValidate,
  children,
}: {
  steps: GuidedInvestigationStep[];
  index: number;
  result?: InvestigationResult;
  explanationVisible: boolean;
  busy: boolean;
  run: GenerationRun;
  recipe?: GenerationPreview['investigations'][number];
  onRun: () => void;
  onHint: () => void;
  hintVisible: boolean;
  onExplanation: () => void;
  onViewTopology: () => void;
  onPrevious: () => void;
  onNext: () => void;
  onBack: () => void;
  onValidate: () => void;
  canValidate: boolean;
  children: ReactNode;
}) {
  const step = steps[index];
  if (!step || !recipe) return <div className="generation-empty">No guided investigation step is declared.</div>;
  return (
    <section className="guided-workspace" aria-labelledby="investigate-heading">
      <SectionHeading eyebrow={`Guided investigation · Step ${index + 1} of ${steps.length}`} title={step.title} id="investigate-heading" />
      <div className="guided-investigation-card">
        <div><span>Question</span><h4>{step.question}</h4></div>
        <div className="guided-investigation-tools">
          <button type="button" onClick={onViewTopology}>View topology</button>
          {step.hint && <button type="button" onClick={onHint}>{hintVisible ? 'Hide hint' : 'Hint'}</button>}
        </div>
        {hintVisible && step.hint && <p className="guided-hint">{step.hint}</p>}
        <div className="guided-query">
          <Status value={recipe.portability} />
          <pre>{recipe.spl.replace('$run_id$', run.run_id)}</pre>
          <button type="button" onClick={onRun} disabled={busy}>{busy ? 'Searching…' : 'Run in Splunk'}</button>
        </div>
        {result && <div className={`guided-result guided-result--${result.status.toLowerCase()}`}><strong>{result.status} · {result.result_count} results</strong><span>{result.detail}</span></div>}
        <div className="guided-expected"><span>Expected finding</span><p>{step.expected_finding}</p><button type="button" onClick={onExplanation}>Show explanation</button></div>
        {explanationVisible && <p className="guided-explanation">{step.explanation}</p>}
      </div>
      {children}
      <div className="guided-actions">
        <button type="button" onClick={onBack}>Evidence</button>
        <div><button type="button" onClick={onPrevious} disabled={index === 0}>Previous step</button><button type="button" onClick={onNext} disabled={index === steps.length - 1}>Next step</button></div>
        <button type="button" className="generation-primary" onClick={onValidate} disabled={!canValidate}>Validate learning</button>
      </div>
    </section>
  );
}

function ValidationStep({ scenario, run, onBack, onComplete }: { scenario: GenerationScenario; run: GenerationRun; onBack: () => void; onComplete: () => void }) {
  const results = run.validation ?? [];
  const requiredPassed = results.filter((item) => item.requirement === 'REQUIRED').every((item) => item.state === 'PROVEN');
  return (
    <section className="guided-workspace" aria-labelledby="validation-heading">
      <SectionHeading eyebrow="Guided lab · Validate" title="Validate only what was proven" id="validation-heading" />
      <div className="guided-validation-list">
        {results.map((item) => (
          <div key={item.validation_id}>
            <span aria-hidden>{item.state === 'PROVEN' ? '✓' : '—'}</span>
            <div><strong>{item.label}</strong><small>{item.detail}</small></div>
            <Status value={item.state} />
          </div>
        ))}
        <div><span aria-hidden>—</span><div><strong>CIM</strong><small>No CIM relationship is declared for this NetSpout-defined sourcetype.</small></div><Status value="NOT VALIDATED" /></div>
        <div><span aria-hidden>—</span><div><strong>Detection</strong><small>No detection object is configured for this scenario.</small></div><Status value="NOT CONFIGURED" /></div>
      </div>
      <div className="guided-validation-summary">
        <span>Expected outcome</span>
        <strong>{scenario.expected_outcome ?? 'No expected outcome is declared.'}</strong>
      </div>
      <GuidedActions back={onBack} next={onComplete} nextLabel="Complete scenario" nextDisabled={!requiredPassed || results.length === 0} />
    </section>
  );
}

function CompletionSummary({ scenario, run, investigationCount, onReplay, busy, experienceMode }: { scenario: GenerationScenario; run: GenerationRun; investigationCount: number; onReplay: () => void; busy: boolean; experienceMode: ExperienceMode }) {
  const observed = run.channel_results?.length
    ? run.channel_results.reduce((total, channel) => total + (channel.evidence.find((item) => item.stage === 'SPLUNK_OBSERVED')?.count ?? 0), 0)
    : run.evidence.find((item) => item.stage === 'SPLUNK_OBSERVED')?.count ?? 0;
  const generated = run.channel_results?.length
    ? run.channel_results.reduce((total, channel) => total + (channel.evidence.find((item) => item.stage === 'GENERATED')?.count ?? 0), 0)
    : run.events.length;
  return (
    <section className="guided-complete" aria-labelledby="complete-heading">
      <span className="guided-complete__mark" aria-hidden>✓</span>
      <span className="generation-eyebrow">Scenario complete</span>
      <h2 id="complete-heading">{scenario.title}</h2>
      <p>You ran the modeled incident, connected its entity and timeline, searched Splunk, and validated the declared evidence conditions.</p>
      <div className="guided-complete__proof">
        <div><span>Run</span><code>{run.run_id}</code></div>
        <div><span>Evidence generated</span><strong>{generated}</strong></div>
        <div><span>Splunk observed</span><strong>{observed}</strong></div>
        <div><span>Investigations completed</span><strong>{investigationCount}</strong></div>
      </div>
      <div className="guided-complete__learning">
        <div><h3>What you learned</h3><ul>{scenario.learning_objectives.map((item) => <li key={item}>{item}</li>)}</ul></div>
        <div><h3>Production portability</h3><p>The current investigation is NetSpout-specific. Production guidance is metadata, not a verified production deployment.</p>{scenario.production_replication_guidance.map((item) => <small key={item}>{item}</small>)}</div>
        <div><h3>Known limitations</h3>{run.limitations.map((item) => <small key={item}>{item}</small>)}</div>
      </div>
      {experienceMode === 'advanced' && <details open><summary>Advanced run identity</summary><pre>{JSON.stringify({ scenario_id: scenario.scenario_id, run_id: run.run_id, transport_id: run.transport_id, destination_id: run.destination_id }, null, 2)}</pre></details>}
      <button type="button" className="generation-primary" onClick={onReplay} disabled={busy}>{busy ? 'Creating new run…' : 'Replay scenario'}</button>
    </section>
  );
}

function channelCountForNode(
  run: GenerationRun,
  scenario: GenerationScenario,
  nodeId: string,
  stage: string,
) {
  const sourceIds = scenario.nodes.find((node) => node.node_id === nodeId)?.source_ids ?? [];
  if (run.channel_results?.length) {
    return run.channel_results
      .filter((channel) => sourceIds.includes(channel.source_id))
      .reduce((total, channel) => total + (channel.evidence.find((item) => item.stage === stage)?.count ?? 0), 0);
  }
  return run.events.filter((event) => sourceIds.includes(event.source_id)).length;
}

function SectionHeading({ eyebrow, title, id }: { eyebrow: string; title: string; id: string }) {
  return <div className="guided-heading"><span>{eyebrow}</span><h2 id={id}>{title}</h2></div>;
}

function TeachingCard({ title, text, fallback }: { title: string; text?: string | null; fallback: string }) {
  return <article><span>{title}</span><p>{text ?? fallback}</p></article>;
}

function Status({ value }: { value: string }) {
  return <span className={`guided-status guided-status--${value.toLowerCase().replaceAll('_', '-')}`}>{badge(value)}</span>;
}

function GuidedActions({ back, middle, next, nextLabel, nextDisabled = false }: { back: () => void; middle?: ReactNode; next: () => void; nextLabel: string; nextDisabled?: boolean }) {
  return (
    <div className="guided-actions">
      <button type="button" onClick={back}>Back</button>
      <div>{middle}</div>
      <button type="button" className="generation-primary" onClick={next} disabled={nextDisabled}>{nextLabel}</button>
    </div>
  );
}

function guidedInvestigations(scenario: GenerationScenario | null, preview: GenerationPreview | null): GuidedInvestigationStep[] {
  if (!scenario) return [];
  if (scenario.investigation_steps?.length) return scenario.investigation_steps;
  return (preview?.investigations ?? []).map((recipe, index) => ({
    step_id: `recipe-${index + 1}`,
    recipe_id: recipe.recipe_id,
    title: recipe.title,
    question: recipe.question ?? recipe.objective ?? 'What does the attached investigation prove?',
    expected_finding: recipe.expected_finding ?? 'Expected finding is not declared.',
    explanation: recipe.explanation ?? 'Explanation is not declared.',
    hint: recipe.hint ?? null,
    node_ids: [],
    source_ids: recipe.source_ids,
  }));
}
