import { useEffect, useMemo, useState } from 'react';
import {
  Activity,
  BookOpen,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  CircleAlert,
  Database,
  Eye,
  FileCode2,
  Layers3,
  Play,
  Search,
  Send,
  Server,
} from 'lucide-react';
import type { ExperienceMode } from '../../app/navigation';
import { generationApi } from '../../lib/generationApi';
import type {
  GenerationCapabilities,
  GenerationMode,
  GenerationPreflight,
  GenerationPreview,
  GenerationRequest,
  GenerationRun,
  GenerationScenario,
  GenerationSource,
  GenerationStep,
  InvestigationResult,
} from '../../types/generation';
import { TopologyPreview } from './TopologyPreview';

const STEPS: GenerationStep[] = ['CHOOSE', 'PREVIEW', 'CONFIGURE', 'RUN', 'OBSERVE', 'INVESTIGATE'];

const modeIcons = {
  SCENARIO: Layers3,
  DATA_SOURCE: Server,
  SOURCETYPE: FileCode2,
  SINGLE_EVENT: Send,
};

interface GenerationLabProps {
  experienceMode: ExperienceMode;
  initialMode?: GenerationMode;
  initialStep?: GenerationStep;
}

function stateClass(value: string) {
  const normalized = value.toLowerCase().replaceAll('_', '-').replaceAll(' ', '-');
  return `generation-status generation-status--${normalized}`;
}

function StateLabel({ value }: { value: string }) {
  return <span className={stateClass(value)}>{value.replaceAll('_', ' ')}</span>;
}

function selectionForMode(capabilities: GenerationCapabilities, mode: GenerationMode) {
  if (mode === 'SCENARIO') return capabilities.scenarios[0]?.scenario_id ?? '';
  if (mode === 'DATA_SOURCE') return capabilities.sources[0]?.source_id ?? '';
  if (mode === 'SOURCETYPE') return capabilities.sourcetypes[0]?.name ?? '';
  return capabilities.event_families[0]?.event_family_id ?? '';
}

function requestFor(
  mode: GenerationMode,
  selectionId: string,
  count: number,
  rateEps: number,
  durationSeconds: number,
  transportId: string,
  destinationId: string,
): GenerationRequest {
  return {
    mode,
    selection_id: selectionId,
    transport_id: transportId,
    destination_id: destinationId,
    count: mode === 'SINGLE_EVENT' ? 1 : count,
    rate_eps: rateEps,
    duration_seconds: durationSeconds,
    scenario_parameters: mode === 'SCENARIO' ? { intensity: 1 } : {},
  };
}

export function GenerationLab({
  experienceMode,
  initialMode = 'SCENARIO',
  initialStep = 'CHOOSE',
}: GenerationLabProps) {
  const [capabilities, setCapabilities] = useState<GenerationCapabilities | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [step, setStep] = useState<GenerationStep>(initialStep);
  const [mode, setMode] = useState<GenerationMode>(initialMode);
  const [selectionId, setSelectionId] = useState('');
  const [searchText, setSearchText] = useState('');
  const [domainFilter, setDomainFilter] = useState('all');
  const [preview, setPreview] = useState<GenerationPreview | null>(null);
  const [preflight, setPreflight] = useState<GenerationPreflight | null>(null);
  const [run, setRun] = useState<GenerationRun | null>(null);
  const [investigationResult, setInvestigationResult] = useState<InvestigationResult | null>(null);
  const [count, setCount] = useState(6);
  const [rateEps, setRateEps] = useState(10);
  const [durationSeconds, setDurationSeconds] = useState(1);
  const [transportId, setTransportId] = useState('transport-local-hec');
  const [destinationId, setDestinationId] = useState('destination-local-docker-splunk');
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [rawVisible, setRawVisible] = useState(false);

  useEffect(() => {
    let active = true;
    generationApi.capabilities()
      .then((value) => {
        if (!active) return;
        setCapabilities(value);
        setSelectionId(selectionForMode(value, initialMode));
        setTransportId(value.transports[0]?.transport_id ?? '');
        setDestinationId(value.destinations[0]?.destination_id ?? '');
        setLoading(false);
      })
      .catch((error: unknown) => {
        if (!active) return;
        setLoadError(error instanceof Error ? error.message : 'Capability service unavailable');
        setLoading(false);
      });
    return () => { active = false; };
  }, [initialMode]);

  const generationRequest = useMemo(
    () => requestFor(mode, selectionId, count, rateEps, durationSeconds, transportId, destinationId),
    [mode, selectionId, count, rateEps, durationSeconds, transportId, destinationId],
  );

  const selectedScenario = capabilities?.scenarios.find((scenario) => scenario.scenario_id === selectionId)
    ?? preview?.scenario
    ?? null;
  const selectionRunnable = useMemo(() => {
    if (!capabilities) return false;
    if (mode === 'SCENARIO') return Boolean(capabilities.scenarios.find((item) => item.scenario_id === selectionId)?.runnable);
    if (mode === 'DATA_SOURCE') return Boolean(capabilities.sources.find((item) => item.source_id === selectionId)?.generation.runnable);
    if (mode === 'SOURCETYPE') return Boolean(capabilities.sourcetypes.find((item) => item.name === selectionId)?.runnable);
    return Boolean(capabilities.event_families.find((item) => item.event_family_id === selectionId)?.runnable);
  }, [capabilities, mode, selectionId]);

  const resetFromSelection = (nextMode: GenerationMode, nextSelection?: string) => {
    if (!capabilities) return;
    const selection = nextSelection ?? selectionForMode(capabilities, nextMode);
    setMode(nextMode);
    setSelectionId(selection);
    setPreview(null);
    setPreflight(null);
    setRun(null);
    setInvestigationResult(null);
    setActionError(null);
    setRawVisible(false);
  };

  const goToPreview = async () => {
    setBusy(true);
    setActionError(null);
    try {
      const value = await generationApi.preview(generationRequest);
      setPreview(value);
      setStep('PREVIEW');
    } catch (error) {
      setActionError(error instanceof Error ? error.message : 'Preview unavailable');
    } finally {
      setBusy(false);
    }
  };

  const runPreflight = async () => {
    setBusy(true);
    setActionError(null);
    try {
      setPreflight(await generationApi.preflight(generationRequest));
    } catch (error) {
      setActionError(error instanceof Error ? error.message : 'Preflight unavailable');
    } finally {
      setBusy(false);
    }
  };

  const execute = async () => {
    setBusy(true);
    setActionError(null);
    try {
      setRun(await generationApi.run(generationRequest));
    } catch (error) {
      setActionError(error instanceof Error ? error.message : 'Generation failed');
    } finally {
      setBusy(false);
    }
  };

  const observe = async () => {
    if (!run) return;
    setBusy(true);
    setActionError(null);
    try {
      setRun(await generationApi.observe(run.run_id));
    } catch (error) {
      setActionError(error instanceof Error ? error.message : 'Observation failed');
    } finally {
      setBusy(false);
    }
  };

  const investigate = async (recipeId: string) => {
    if (!run) return;
    setBusy(true);
    setActionError(null);
    try {
      setInvestigationResult(await generationApi.investigate(run.run_id, recipeId));
    } catch (error) {
      setActionError(error instanceof Error ? error.message : 'Investigation failed');
    } finally {
      setBusy(false);
    }
  };

  if (loading) {
    return <div className="generation-state"><Activity className="generation-spin" /> Loading generation capabilities…</div>;
  }
  if (loadError || !capabilities) {
    return (
      <div className="generation-state generation-state--error">
        <CircleAlert />
        <div><strong>Generation capabilities unavailable</strong><span>{loadError ?? 'NOT AVAILABLE'}</span></div>
      </div>
    );
  }

  const stepIndex = STEPS.indexOf(step);
  return (
    <div className="generation-lab" data-testid="generation-lab">
      <header className="generation-hero">
        <div>
          <span className="generation-eyebrow">Unified Generation Experience</span>
          <h2>Choose, generate, and prove telemetry</h2>
          <p>One catalog-driven workflow from contract selection through Splunk investigation.</p>
        </div>
        <div className="generation-hero__summary">
          <span><strong>{capabilities.scenarios.filter((item) => item.runnable).length}</strong> runnable scenario</span>
          <span><strong>{capabilities.sources.filter((item) => item.generation.runnable).length}</strong> runnable source</span>
          <StateLabel value="FAIL CLOSED" />
        </div>
      </header>

      <nav className="generation-stepper" aria-label="Generation workflow">
        {STEPS.map((item, index) => (
          <button
            type="button"
            key={item}
            className={index === stepIndex ? 'is-active' : index < stepIndex ? 'is-complete' : ''}
            onClick={() => {
              if (index <= stepIndex || (item === 'INVESTIGATE' && run)) setStep(item);
            }}
            disabled={index > stepIndex && !(item === 'INVESTIGATE' && run)}
          >
            <span>{index < stepIndex ? '✓' : index + 1}</span>
            {item}
          </button>
        ))}
      </nav>

      {actionError && (
        <div className="generation-alert generation-alert--error" role="alert">
          <CircleAlert /> <span>{actionError}</span>
        </div>
      )}

      {step === 'CHOOSE' && (
        <ChooseStep
          capabilities={capabilities}
          mode={mode}
          selectionId={selectionId}
          searchText={searchText}
          domainFilter={domainFilter}
          onModeChange={(nextMode) => resetFromSelection(nextMode)}
          onSelectionChange={(value) => resetFromSelection(mode, value)}
          onSearchChange={setSearchText}
          onDomainChange={setDomainFilter}
          onContinue={goToPreview}
          runnable={selectionRunnable}
          busy={busy}
        />
      )}

      {step === 'PREVIEW' && preview && (
        <PreviewStep
          preview={preview}
          experienceMode={experienceMode}
          rawVisible={rawVisible}
          onRawToggle={() => setRawVisible((value) => !value)}
          onBack={() => setStep('CHOOSE')}
          onContinue={() => setStep('CONFIGURE')}
        />
      )}

      {step === 'CONFIGURE' && preview && (
        <ConfigureStep
          capabilities={capabilities}
          request={generationRequest}
          mode={mode}
          count={count}
          rateEps={rateEps}
          durationSeconds={durationSeconds}
          experienceMode={experienceMode}
          preflight={preflight}
          busy={busy}
          onCountChange={setCount}
          onRateChange={setRateEps}
          onDurationChange={setDurationSeconds}
          onTransportChange={setTransportId}
          onDestinationChange={setDestinationId}
          onPreflight={runPreflight}
          onBack={() => setStep('PREVIEW')}
          onContinue={() => setStep('RUN')}
        />
      )}

      {step === 'RUN' && preview && (
        <RunStep
          scenario={selectedScenario}
          request={generationRequest}
          run={run}
          busy={busy}
          onRun={execute}
          onBack={() => setStep('CONFIGURE')}
          onObserve={() => setStep('OBSERVE')}
        />
      )}

      {step === 'OBSERVE' && run && (
        <ObserveStep
          run={run}
          busy={busy}
          onRefresh={observe}
          onBack={() => setStep('RUN')}
          onInvestigate={() => setStep('INVESTIGATE')}
        />
      )}

      {step === 'INVESTIGATE' && run && (
        <InvestigateStep
          run={run}
          result={investigationResult}
          busy={busy}
          onRun={investigate}
          onBack={() => setStep('OBSERVE')}
        />
      )}
    </div>
  );
}

interface ChooseProps {
  capabilities: GenerationCapabilities;
  mode: GenerationMode;
  selectionId: string;
  searchText: string;
  domainFilter: string;
  runnable: boolean;
  busy: boolean;
  onModeChange: (mode: GenerationMode) => void;
  onSelectionChange: (id: string) => void;
  onSearchChange: (value: string) => void;
  onDomainChange: (value: string) => void;
  onContinue: () => void;
}

function ChooseStep(props: ChooseProps) {
  const query = props.searchText.trim().toLowerCase();
  const scenarios = props.capabilities.scenarios.filter((scenario) => {
    const sourceDomains = props.capabilities.sources
      .filter((source) => scenario.source_ids.includes(source.source_id))
      .flatMap((source) => source.domains);
    return (!query || `${scenario.title} ${scenario.description} ${scenario.technology_ids.join(' ')}`.toLowerCase().includes(query))
      && (props.domainFilter === 'all' || sourceDomains.includes(props.domainFilter));
  });
  const sources = props.capabilities.sources.filter((source) =>
    !query || `${source.vendor} ${source.product} ${source.telemetry_source}`.toLowerCase().includes(query));

  return (
    <section className="generation-workspace" aria-labelledby="choose-heading">
      <div className="generation-section-heading">
        <div><span>Step 1</span><h3 id="choose-heading">Choose what to generate</h3></div>
        <p>Only validated catalog capabilities can run. Other entries remain inspectable.</p>
      </div>
      <div className="generation-mode-grid">
        {props.capabilities.modes.map((item) => {
          const Icon = modeIcons[item.id];
          return (
            <button
              type="button"
              key={item.id}
              className={item.id === props.mode ? 'generation-mode-card is-selected' : 'generation-mode-card'}
              onClick={() => props.onModeChange(item.id)}
            >
              <Icon />
              <strong>{item.label}</strong>
              <span>{item.description}</span>
            </button>
          );
        })}
      </div>

      <div className="generation-browser">
        <div className="generation-browser__toolbar">
          <label className="generation-search">
            <Search />
            <input
              aria-label="Search generation catalog"
              placeholder="Search scenario, vendor, source…"
              value={props.searchText}
              onChange={(event) => props.onSearchChange(event.target.value)}
            />
          </label>
          {props.mode === 'SCENARIO' && (
            <select
              aria-label="Filter scenario domain"
              value={props.domainFilter}
              onChange={(event) => props.onDomainChange(event.target.value)}
            >
              <option value="all">All supported domains</option>
              <option value="netops">NetOps</option>
              <option value="secops">SecOps</option>
              <option value="itops">ITOps / AIOps</option>
              <option value="observability">Application &amp; Cloud Observability</option>
              <option value="agentic-ai">Agentic AI</option>
              <option value="supply-chain">Software Supply Chain</option>
            </select>
          )}
        </div>

        {props.mode === 'SCENARIO' && (
          <div className="scenario-card-grid">
            {scenarios.length === 0 && <div className="generation-empty">No catalog-backed scenarios match this filter.</div>}
            {scenarios.map((scenario) => (
              <ScenarioCard
                key={scenario.scenario_id}
                scenario={scenario}
                selected={scenario.scenario_id === props.selectionId}
                onSelect={() => props.onSelectionChange(scenario.scenario_id)}
              />
            ))}
          </div>
        )}

        {props.mode === 'DATA_SOURCE' && (
          <div className="generation-selection-list">
            {sources.map((source) => (
              <SourceChoice
                key={source.source_id}
                source={source}
                selected={source.source_id === props.selectionId}
                onSelect={() => props.onSelectionChange(source.source_id)}
              />
            ))}
          </div>
        )}

        {props.mode === 'SOURCETYPE' && (
          <div className="generation-selection-list">
            {props.capabilities.sourcetypes.map((item) => (
              <button
                type="button"
                key={item.name}
                className={item.name === props.selectionId ? 'generation-choice is-selected' : 'generation-choice'}
                onClick={() => props.onSelectionChange(item.name)}
              >
                <div><code>{item.name}</code><span>{item.vendor} · {item.product}</span></div>
                <div><StateLabel value={item.authority.replace('_', '-')} /><StateLabel value={item.runnable ? 'READY' : 'NOT AVAILABLE'} /></div>
              </button>
            ))}
          </div>
        )}

        {props.mode === 'SINGLE_EVENT' && (
          <div className="generation-selection-list">
            {props.capabilities.event_families.map((item) => (
              <button
                type="button"
                key={item.event_family_id}
                className={item.event_family_id === props.selectionId ? 'generation-choice is-selected' : 'generation-choice'}
                onClick={() => props.onSelectionChange(item.event_family_id)}
              >
                <div><strong>{item.label}</strong><code>{item.sourcetype}</code></div>
                <div><StateLabel value="EXACTLY 1 EVENT" /><StateLabel value={item.runnable ? 'READY' : 'NOT AVAILABLE'} /></div>
              </button>
            ))}
          </div>
        )}
      </div>

      {!props.runnable && props.selectionId && (
        <div className="generation-alert generation-alert--blocked">
          <CircleAlert />
          <div>
            <strong>{sources.find((item) => item.source_id === props.selectionId)?.generation.state ?? 'NOT AVAILABLE'}</strong>
            <span>{sources.find((item) => item.source_id === props.selectionId)?.generation.reason ?? 'This selection has no validated runtime composition.'}</span>
            <a href="#/catalog/provenance">View evidence</a>
          </div>
        </div>
      )}
      <div className="generation-actions">
        <span />
        <button type="button" className="generation-primary" disabled={!props.runnable || props.busy} onClick={props.onContinue}>
          Preview <ChevronRight />
        </button>
      </div>
    </section>
  );
}

function ScenarioCard({ scenario, selected, onSelect }: { scenario: GenerationScenario; selected: boolean; onSelect: () => void }) {
  return (
    <button type="button" className={selected ? 'scenario-card is-selected' : 'scenario-card'} onClick={onSelect}>
      <div className="scenario-card__header">
        <div><h4>{scenario.title}</h4><p>{scenario.description}</p></div>
        <StateLabel value={scenario.verification_state} />
      </div>
      <div className="scenario-card__tags">
        <span>{scenario.difficulty}</span>
        {scenario.technology_ids.map((technology) => <code key={technology}>{technology}</code>)}
      </div>
      <div className="scenario-card__footer">
        <span>{scenario.source_count} telemetry source{scenario.source_count === 1 ? '' : 's'}</span>
        <span>{scenario.integration_count} integration requirement{scenario.integration_count === 1 ? '' : 's'}</span>
        <StateLabel value={scenario.maturity} />
      </div>
    </button>
  );
}

function SourceChoice({ source, selected, onSelect }: { source: GenerationSource; selected: boolean; onSelect: () => void }) {
  return (
    <button type="button" className={selected ? 'generation-choice is-selected' : 'generation-choice'} onClick={onSelect}>
      <div>
        <strong>{source.product}</strong>
        <span>{source.vendor} · {source.telemetry_source}</span>
        <code>{source.source_id}</code>
      </div>
      <div>
        <StateLabel value={source.verification_state} />
        <StateLabel value={source.generation.state} />
      </div>
    </button>
  );
}

function PreviewStep({
  preview,
  experienceMode,
  rawVisible,
  onRawToggle,
  onBack,
  onContinue,
}: {
  preview: GenerationPreview;
  experienceMode: ExperienceMode;
  rawVisible: boolean;
  onRawToggle: () => void;
  onBack: () => void;
  onContinue: () => void;
}) {
  const source = preview.sources[0];
  return (
    <section className="generation-workspace" aria-labelledby="preview-heading">
      <div className="generation-section-heading">
        <div><span>Step 2</span><h3 id="preview-heading">Preview generation plan</h3></div>
        <StateLabel value={preview.scenario?.verification_state ?? source.verification_state} />
      </div>

      {preview.scenario && (
        <>
          <div className="generation-guided-grid">
            <article><span>Story</span><h4>What is happening?</h4><p>{preview.scenario.story}</p></article>
            <article><span>Why it matters</span><h4>Operational impact</h4><p>{preview.scenario.business_impact}</p></article>
            <article><span>What NetSpout simulates</span><h4>Modeled lifecycle</h4><p>{preview.scenario.description}</p></article>
            <article><span>Expected outcome</span><h4>Evidence</h4><p>{preview.scenario.expected_evidence.join(' ')}</p></article>
          </div>
          <div className="generation-panel">
            <div className="generation-panel__header"><h4>Scenario Topology</h4><span>Manifest-driven SVG</span></div>
            <TopologyPreview scenario={preview.scenario} />
          </div>
        </>
      )}

      <div className="generation-panel">
        <div className="generation-panel__header"><h4>What will be generated</h4><span>{preview.bindings.length} validated binding</span></div>
        <div className="generation-table-wrap">
          <table className="generation-table">
            <thead><tr><th>Source</th><th>Generator</th><th>Transport</th><th>Splunk</th><th>Provenance</th></tr></thead>
            <tbody>
              {preview.bindings.map((binding) => (
                <tr key={binding.source_id}>
                  <td><strong>{source.telemetry_source}</strong><code>{binding.source_id}</code></td>
                  <td><code>{binding.generator_id}</code></td>
                  <td><code>{binding.transport_id}</code></td>
                  <td>{source.splunk_contract.sourcetypes.map((item) => <code key={item.name}>{item.name} · {item.authority}</code>)}</td>
                  <td><div className="generation-inline-badges">{source.provenance.map((item) => <StateLabel key={item} value={item} />)}</div></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="generation-panel">
        <div className="generation-panel__header"><h4>Splunk Integration Readiness</h4><span>Evidence-backed relationships only</span></div>
        <div className="integration-readiness-list">
          {preview.integration_readiness.map((item) => (
            <article key={item.recommendation_id}>
              <div><strong>{item.name}</strong><span>{item.notes}</span></div>
              <StateLabel value={item.requirement} />
              <span className={item.detected ? 'integration-detected' : 'integration-missing'}>
                Detected: {item.detected ? 'Yes' : 'No'}
              </span>
            </article>
          ))}
        </div>
      </div>

      <div className="generation-panel">
        <div className="generation-panel__header">
          <div><h4>Raw Event Preview</h4><span>{preview.preview_notice}</span></div>
          <button type="button" className="generation-secondary" onClick={onRawToggle}><Eye /> {rawVisible ? 'Hide' : 'Preview Raw Event'}</button>
        </div>
        {rawVisible && (
          <div className="raw-preview">
            <div>
              <span>Source</span><code>{preview.raw_preview[0]?.source_id}</code>
              <span>Contract</span><code>{preview.raw_preview[0]?.contract_id}</code>
              <span>Transport</span><code>{preview.raw_preview[0]?.transport_id}</code>
              <span>Sourcetype</span><code>{preview.raw_preview[0]?.sourcetype} · {preview.raw_preview[0]?.sourcetype_authority}</code>
            </div>
            <pre>{preview.raw_preview[0]?.raw ?? 'NOT AVAILABLE'}</pre>
          </div>
        )}
      </div>

      {experienceMode === 'advanced' && (
        <div className="generation-contract-grid">
          <article><h4>Native Contract</h4><code>{preview.native_contract.contract_id}</code><p>{preview.native_contract.format}</p><StateLabel value={preview.native_contract.verification_state} /></article>
          <article><h4>Splunk Contract</h4><code>{preview.splunk_contract.contract_id}</code><p>{preview.splunk_contract.input_mechanisms.join(', ')}</p><StateLabel value={preview.splunk_contract.verification_state} /></article>
          <article><h4>NetSpout Contract</h4><code>{preview.netspout_contract.contract_id}</code><p>Modeled: {preview.netspout_contract.modeled_fields.join(', ')}</p><StateLabel value={preview.netspout_contract.verification_state} /></article>
        </div>
      )}

      <div className="generation-actions">
        <button type="button" className="generation-secondary" onClick={onBack}><ChevronLeft /> Choose</button>
        <a href="#/catalog/provenance">View provenance</a>
        <button type="button" className="generation-primary" onClick={onContinue}>Configure <ChevronRight /></button>
      </div>
    </section>
  );
}

function ConfigureStep({
  capabilities,
  request,
  mode,
  count,
  rateEps,
  durationSeconds,
  experienceMode,
  preflight,
  busy,
  onCountChange,
  onRateChange,
  onDurationChange,
  onTransportChange,
  onDestinationChange,
  onPreflight,
  onBack,
  onContinue,
}: {
  capabilities: GenerationCapabilities;
  request: GenerationRequest;
  mode: GenerationMode;
  count: number;
  rateEps: number;
  durationSeconds: number;
  experienceMode: ExperienceMode;
  preflight: GenerationPreflight | null;
  busy: boolean;
  onCountChange: (value: number) => void;
  onRateChange: (value: number) => void;
  onDurationChange: (value: number) => void;
  onTransportChange: (value: string) => void;
  onDestinationChange: (value: string) => void;
  onPreflight: () => void;
  onBack: () => void;
  onContinue: () => void;
}) {
  return (
    <section className="generation-workspace" aria-labelledby="configure-heading">
      <div className="generation-section-heading">
        <div><span>Step 3</span><h3 id="configure-heading">Configure and preflight</h3></div>
        <p>Connection credentials remain in Connection Center and are never returned here.</p>
      </div>
      <div className="generation-config-grid">
        <div className="generation-panel">
          <div className="generation-panel__header"><h4>Generation</h4><span>{experienceMode === 'simple' ? 'Recommended defaults' : 'Supported controls'}</span></div>
          <div className="generation-form-grid">
            {mode !== 'SCENARIO' && mode !== 'SINGLE_EVENT' && (
              <>
                <label>Count<input aria-label="Event count" type="number" min={1} max={100} value={count} onChange={(event) => onCountChange(Number(event.target.value))} /></label>
                <label>EPS<input aria-label="Events per second" type="number" min={1} max={100} value={rateEps} onChange={(event) => onRateChange(Number(event.target.value))} /></label>
                <label>Duration (seconds)<input aria-label="Duration seconds" type="number" min={1} max={300} value={durationSeconds} onChange={(event) => onDurationChange(Number(event.target.value))} /></label>
              </>
            )}
            {mode === 'SINGLE_EVENT' && <div className="generation-fixed-value"><span>Count</span><strong>1 — enforced</strong></div>}
            {mode === 'SCENARIO' && <div className="generation-fixed-value"><span>Timeline</span><strong>Manifest-defined phases</strong></div>}
            {experienceMode === 'advanced' && (
              <div className="generation-fixed-value"><span>Scenario parameter</span><strong>Intensity 1 · modeled values only</strong></div>
            )}
          </div>
        </div>
        <div className="generation-panel">
          <div className="generation-panel__header"><h4>Delivery</h4><span>Transport and destination remain distinct</span></div>
          <div className="generation-form-grid">
            <label>Transport
              <select aria-label="Transport" value={request.transport_id} onChange={(event) => onTransportChange(event.target.value)}>
                {capabilities.transports.filter((item) => item.implemented).map((item) => <option key={item.transport_id} value={item.transport_id}>{item.protocol} · {item.component}</option>)}
              </select>
            </label>
            <label>Destination
              <select aria-label="Destination" value={request.destination_id} onChange={(event) => onDestinationChange(event.target.value)}>
                {capabilities.destinations.filter((item) => item.configured).map((item) => <option key={item.destination_id} value={item.destination_id}>{item.label}</option>)}
              </select>
            </label>
          </div>
          <a href="#/system/connections">Manage connection in Connection Center</a>
        </div>
      </div>

      <div className="generation-panel" data-testid="preflight-panel">
        <div className="generation-panel__header">
          <div><h4>Preflight</h4><span>Backend-derived checks; no static READY state</span></div>
          {preflight && <StateLabel value={preflight.state} />}
        </div>
        {!preflight ? (
          <div className="generation-empty">Run preflight to validate this exact composition and destination.</div>
        ) : (
          <div className="preflight-list">
            {preflight.checks.map((check) => (
              <article key={check.check_id}>
                {check.state === 'PASS' ? <CheckCircle2 /> : <CircleAlert />}
                <div><strong>{check.label}</strong><span>{check.detail}</span></div>
                <StateLabel value={check.state} />
              </article>
            ))}
          </div>
        )}
      </div>

      <div className="generation-actions">
        <button type="button" className="generation-secondary" onClick={onBack}><ChevronLeft /> Preview</button>
        <button type="button" className="generation-secondary" disabled={busy} onClick={onPreflight}>{busy ? 'Checking…' : 'Run Preflight'}</button>
        <button type="button" className="generation-primary" disabled={!preflight || preflight.state === 'BLOCKED'} onClick={onContinue}>Continue to Run <ChevronRight /></button>
      </div>
    </section>
  );
}

function RunStep({
  scenario,
  request,
  run,
  busy,
  onRun,
  onBack,
  onObserve,
}: {
  scenario: GenerationScenario | null;
  request: GenerationRequest;
  run: GenerationRun | null;
  busy: boolean;
  onRun: () => void;
  onBack: () => void;
  onObserve: () => void;
}) {
  return (
    <section className="generation-workspace" aria-labelledby="run-heading">
      <div className="generation-section-heading">
        <div><span>Step 4</span><h3 id="run-heading">Run generation</h3></div>
        {run && <StateLabel value={run.status} />}
      </div>
      {!run ? (
        <div className="generation-run-ready">
          <Play />
          <h4>Ready to execute</h4>
          <p>{request.mode} · {request.selection_id}</p>
          <button type="button" className="generation-run-button" disabled={busy} onClick={onRun}>{busy ? 'Running…' : 'Run'}</button>
        </div>
      ) : (
        <>
          <div className="generation-run-metadata">
            <div><span>Run ID</span><code>{run.run_id}</code></div>
            <div><span>Started</span><code>{run.started_at}</code></div>
            <div><span>Current phase</span><strong>{run.current_phase}</strong></div>
            <div><span>Events</span><strong>{run.events.length}</strong></div>
          </div>
          {scenario && (
            <>
              <div className="generation-timeline">
                {scenario.timeline.map((item) => (
                  <div key={item.step_id} className={item.stage === run.current_phase ? 'is-active' : 'is-complete'}>
                    <span />
                    <strong>{item.stage}</strong>
                    <small>{item.description}</small>
                  </div>
                ))}
              </div>
              <TopologyPreview scenario={scenario} activePhase={run.current_phase} />
            </>
          )}
          <EvidenceSummary run={run} />
        </>
      )}
      <div className="generation-actions">
        <button type="button" className="generation-secondary" onClick={onBack}><ChevronLeft /> Configure</button>
        <span />
        {run && <button type="button" className="generation-primary" onClick={onObserve}>Observe Evidence <ChevronRight /></button>}
      </div>
    </section>
  );
}

function EvidenceSummary({ run }: { run: GenerationRun }) {
  return (
    <div className="generation-panel">
      <div className="generation-panel__header"><h4>Execution Evidence</h4><span>Stages are intentionally distinct</span></div>
      <div className="evidence-stage-grid">
        {run.evidence.map((item) => (
          <article key={item.stage}>
            <span>{item.stage.replaceAll('_', ' ')}</span>
            <strong>{item.count}</strong>
            <StateLabel value={item.state} />
            <small>{item.detail}</small>
          </article>
        ))}
      </div>
    </div>
  );
}

function ObserveStep({ run, busy, onRefresh, onBack, onInvestigate }: { run: GenerationRun; busy: boolean; onRefresh: () => void; onBack: () => void; onInvestigate: () => void }) {
  const bySource = run.source_ids.map((sourceId) => ({
    sourceId,
    events: run.events.filter((event) => event.source_id === sourceId),
  }));
  return (
    <section className="generation-workspace" aria-labelledby="observe-heading">
      <div className="generation-section-heading">
        <div><span>Step 5</span><h3 id="observe-heading">Observe evidence</h3></div>
        <button type="button" className="generation-secondary" disabled={busy} onClick={onRefresh}><Activity /> {busy ? 'Searching Splunk…' : 'Refresh Splunk Observation'}</button>
      </div>
      <EvidenceSummary run={run} />
      <div className="generation-panel">
        <div className="generation-panel__header"><h4>Evidence by Source</h4><span>Runtime counts only</span></div>
        <div className="evidence-source-list">
          {bySource.map((group) => (
            <details key={group.sourceId}>
              <summary><div><Database /><strong>{group.sourceId}</strong></div><span>{group.events.length} generated</span></summary>
              <div className="evidence-event-list">
                {group.events.map((event) => (
                  <article key={event.event_id}>
                    <div><code>{event.phase}</code><StateLabel value={event.sourcetype_authority} /></div>
                    <code>{event.raw}</code>
                  </article>
                ))}
              </div>
            </details>
          ))}
        </div>
      </div>
      {run.limitations.map((limitation) => <div key={limitation} className="generation-alert"><CircleAlert /> {limitation}</div>)}
      <div className="generation-actions">
        <button type="button" className="generation-secondary" onClick={onBack}><ChevronLeft /> Run</button>
        <span />
        <button type="button" className="generation-primary" disabled={run.investigations.length === 0} onClick={onInvestigate}>Investigate <ChevronRight /></button>
      </div>
    </section>
  );
}

function InvestigateStep({ run, result, busy, onRun, onBack }: { run: GenerationRun; result: InvestigationResult | null; busy: boolean; onRun: (recipeId: string) => void; onBack: () => void }) {
  return (
    <section className="generation-workspace" aria-labelledby="investigate-heading">
      <div className="generation-section-heading">
        <div><span>Step 6</span><h3 id="investigate-heading">Guided investigation</h3></div>
        <p>Queries appear only when supplied by an attached Investigation Pack.</p>
      </div>
      {run.investigations.length === 0 ? (
        <div className="generation-empty">No investigation pack is available for this selection.</div>
      ) : (
        <div className="investigation-list">
          {run.investigations.map((recipe, index) => (
            <article key={recipe.recipe_id}>
              <div className="investigation-list__number">{index + 1}</div>
              <div>
                <div className="investigation-list__header"><h4>{recipe.title}</h4><StateLabel value={recipe.portability} /></div>
                <p>{recipe.portability === 'PRODUCTION_PORTABLE' ? 'Uses verified production fields or CIM relationships.' : 'Depends on NetSpout lab metadata and must be adapted for production.'}</p>
                <pre>{recipe.spl.replace('$run_id$', run.run_id)}</pre>
                <button type="button" className="generation-primary" disabled={busy} onClick={() => onRun(recipe.recipe_id)}><BookOpen /> {busy ? 'Running in Splunk…' : 'Run in Splunk'}</button>
              </div>
            </article>
          ))}
        </div>
      )}
      {result && (
        <div className={`generation-alert ${result.status === 'SUCCEEDED' ? 'generation-alert--success' : 'generation-alert--error'}`}>
          {result.status === 'SUCCEEDED' ? <CheckCircle2 /> : <CircleAlert />}
          <div><strong>{result.status} · {result.result_count} result{result.result_count === 1 ? '' : 's'}</strong><span>{result.detail}</span></div>
        </div>
      )}
      <div className="generation-actions">
        <button type="button" className="generation-secondary" onClick={onBack}><ChevronLeft /> Evidence</button>
      </div>
    </section>
  );
}
