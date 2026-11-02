import { useEffect, useMemo, useState } from 'react';
import { Building2, GitBranch, Play, RefreshCw, Save, ShieldCheck } from 'lucide-react';
import type { ExperienceMode } from '../../app/navigation';
import { generationApi } from '../../lib/generationApi';
import { industryApi } from '../../lib/industryApi';
import type { GenerationPreflight, GenerationRun, GenerationScenario, InvestigationResult } from '../../types/generation';
import type { IndustryCatalog, IndustryEnvironment, IndustryPack } from '../../types/industry';
import { TopologyPreview } from '../generation/TopologyPreview';
import { StatusBadge } from '../ui/SystemPrimitives';

type Perspective = 'TECHNICAL' | 'BUSINESS';
type Step = 'CHOOSE' | 'EXPLORE' | 'CONFIGURE' | 'RUN' | 'OBSERVE' | 'INVESTIGATE' | 'VALIDATE';

const STEPS: Step[] = ['CHOOSE', 'EXPLORE', 'CONFIGURE', 'RUN', 'OBSERVE', 'INVESTIGATE', 'VALIDATE'];

function graphScenario(pack: IndustryPack, environment: IndustryEnvironment): GenerationScenario {
  const entities = pack.entities.filter((item) => environment.entity_ids.includes(item.entity_id));
  const dependencies = pack.dependencies.filter((item) => environment.dependency_ids.includes(item.dependency_id));
  const zones = [...new Set(entities.map((item) => item.zone_id))].map((zoneId) => ({
    zone_id: zoneId,
    label: zoneId.replaceAll('-', ' ').toUpperCase(),
  }));
  return {
    scenario_id: `industry-${pack.industry_id}-${environment.environment_id}`,
    title: `${pack.name} — ${environment.name}`,
    description: environment.description,
    story: pack.description,
    domain: 'industry',
    category: 'INDUSTRY_REFERENCE',
    technical_description: pack.implemented_scope,
    difficulty: 'GUIDED',
    expected_duration_minutes: 15,
    learning_objectives: ['Separate observed technical evidence from modeled business impact.'],
    business_impact: pack.business_impacts[0]?.statement ?? 'Modeled dependency risk.',
    prerequisites: ['Configured local Splunk destination'],
    technology_ids: [...new Set(entities.map((item) => item.entity_kind.toLowerCase()))],
    source_ids: environment.telemetry_source_ids,
    entities: entities.map((item) => item.entity_id),
    zones,
    nodes: entities.map((item) => ({
      node_id: item.entity_id,
      technology_id: item.entity_kind.toLowerCase(),
      zone_id: item.zone_id,
      role: item.entity_kind.toLowerCase(),
      source_ids: item.attributes.view === 'technical' ? environment.telemetry_source_ids : [],
      label: item.label,
      entity_id: item.entity_id,
      description: item.description,
    })),
    relationships: dependencies.map((item) => ({
      relationship_id: item.dependency_id,
      source_node_id: item.source_entity_id,
      target_node_id: item.target_entity_id,
      relationship_type: item.relationship_type,
      protocol: 'DECLARED DEPENDENCY',
      telemetry_source_ids: [],
    })),
    telemetry_paths: [],
    incident_path: entities.map((item) => item.entity_id),
    runtime_state_keys: [],
    timeline: [],
    expected_evidence: ['RECEIVER_OBSERVED', 'SPLUNK_OBSERVED'],
    investigation_recipe_ids: pack.scenario_references.find(
      (item) => item.scenario_id === environment.default_scenario_id,
    )?.investigation_recipe_ids ?? [],
    integration_recommendation_ids: [],
    production_replication_guidance: [
      'Replace modeled dependencies with a reviewed service map.',
      'Validate source fields, indexes, and recovery criteria in the target deployment.',
    ],
    visualization: { mode: 'AUTOMATIC', direction: 'LEFT_TO_RIGHT', curated_layout_ref: null },
    composition_id: `industry-compose-${pack.industry_id}`,
    verification_state: 'VERIFIED',
    maturity: pack.maturity,
    source_count: environment.telemetry_source_ids.length,
    integration_count: 0,
    runnable: true,
  };
}

export function IndustryStudio({ experienceMode }: { experienceMode: ExperienceMode }) {
  const [catalog, setCatalog] = useState<IndustryCatalog | null>(null);
  const [industryId, setIndustryId] = useState('');
  const [environmentId, setEnvironmentId] = useState('');
  const [scenarioId, setScenarioId] = useState('');
  const [perspective, setPerspective] = useState<Perspective>('TECHNICAL');
  const [step, setStep] = useState<Step>('CHOOSE');
  const [seed, setSeed] = useState(1010);
  const [preflight, setPreflight] = useState<GenerationPreflight | null>(null);
  const [run, setRun] = useState<GenerationRun | null>(null);
  const [investigation, setInvestigation] = useState<InvestigationResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    industryApi.catalog().then((result) => {
      setCatalog(result);
      const first = result.industries[0];
      if (first) {
        setIndustryId(first.industry_id);
        setEnvironmentId(first.environments[0]?.environment_id ?? '');
        setScenarioId(first.environments[0]?.default_scenario_id ?? '');
      }
    }).catch((reason) => setError(String(reason)));
  }, []);

  const industry = useMemo(
    () => catalog?.industries.find((item) => item.industry_id === industryId) ?? null,
    [catalog, industryId],
  );
  const environment = useMemo(
    () => industry?.environments.find((item) => item.environment_id === environmentId) ?? null,
    [industry, environmentId],
  );
  const graph = useMemo(
    () => (industry && environment ? graphScenario(industry, environment) : null),
    [industry, environment],
  );
  const observed = run?.evidence.some((item) => item.stage === 'SPLUNK_OBSERVED' && item.state === 'PROVEN') ?? false;

  const chooseIndustry = (nextId: string) => {
    const next = catalog?.industries.find((item) => item.industry_id === nextId);
    setIndustryId(nextId);
    setEnvironmentId(next?.environments[0]?.environment_id ?? '');
    setScenarioId(next?.environments[0]?.default_scenario_id ?? '');
    setRun(null);
    setPreflight(null);
    setInvestigation(null);
  };

  const request = async () => {
    if (!industry || !environment) throw new Error('Choose an industry environment.');
    return industryApi.compose(industry.industry_id, environment.environment_id, scenarioId, seed);
  };

  const prepare = async () => {
    setBusy(true);
    setError('');
    try {
      const composition = await request();
      setPreflight(await generationApi.preflight(composition.generation_request));
      setStep('RUN');
    } catch (reason) {
      setError(String(reason));
    } finally {
      setBusy(false);
    }
  };

  const execute = async () => {
    setBusy(true);
    setError('');
    try {
      const composition = await request();
      setRun(await generationApi.run(composition.generation_request));
      setStep('OBSERVE');
    } catch (reason) {
      setError(String(reason));
    } finally {
      setBusy(false);
    }
  };

  const observe = async () => {
    if (!run) return;
    setBusy(true);
    try {
      setRun(await generationApi.observe(run.run_id));
      setStep('INVESTIGATE');
    } catch (reason) {
      setError(String(reason));
    } finally {
      setBusy(false);
    }
  };

  const investigate = async () => {
    if (!run || !run.investigations[0]) return;
    setBusy(true);
    try {
      setInvestigation(await generationApi.investigate(run.run_id, run.investigations[0].recipe_id));
      setStep('VALIDATE');
    } catch (reason) {
      setError(String(reason));
    } finally {
      setBusy(false);
    }
  };

  const cloneToStudio = async () => {
    if (!industry || !environment) return;
    setBusy(true);
    try {
      const draft = await industryApi.cloneToStudio(industry.industry_id, environment.environment_id, scenarioId);
      window.sessionStorage.setItem('netspout-studio-import-draft', JSON.stringify(draft));
      window.location.hash = '#/build/studio';
    } catch (reason) {
      setError(String(reason));
    } finally {
      setBusy(false);
    }
  };

  if (!catalog || !industry || !environment || !graph) {
    return <div className="generation-empty">Loading the validated Industry Pack catalog…</div>;
  }

  return (
    <div className="generation-lab industry-studio">
      <header className="generation-hero">
        <div>
          <span className="generation-eyebrow">Phase 10 · Industry Studio</span>
          <h2>Connect technical evidence to modeled business impact</h2>
          <p>Choose a bounded reference environment, run its existing verified scenario, and trace one shared dependency graph.</p>
        </div>
        <div className="generation-hero__summary">
          <strong>{catalog.industries.length}</strong>
          <span>validated reference packs</span>
        </div>
      </header>

      <nav className="generation-stepper" aria-label="Industry Studio workflow">
        {STEPS.map((item, index) => (
          <button key={item} type="button" className={item === step ? 'is-active' : ''} onClick={() => setStep(item)}>
            <span>{index + 1}</span>{item}
          </button>
        ))}
      </nav>

      {error && <div className="generation-alert generation-alert--error"><strong>Blocked</strong><span>{error}</span></div>}

      <section className="generation-workspace">
        <div className="generation-panel">
          <div className="generation-panel__header">
            <div><span>Industry catalog</span><h4>Choose industry and environment</h4></div>
            <StatusBadge status={industry.maturity} />
          </div>
          <div className="generation-mode-grid" aria-label="Industry choices">
            {catalog.industries.map((item) => (
              <button key={item.industry_id} type="button" className={`generation-mode-card ${item.industry_id === industryId ? 'is-selected' : ''}`} onClick={() => chooseIndustry(item.industry_id)}>
                <Building2 />
                <strong>{item.name}</strong>
                <span>{item.implemented_scope}</span>
              </button>
            ))}
          </div>
          <div className="generation-form-grid">
            <label>Environment<select aria-label="Industry environment" value={environmentId} onChange={(event) => {
              const next = industry.environments.find((item) => item.environment_id === event.target.value);
              setEnvironmentId(event.target.value);
              setScenarioId(next?.default_scenario_id ?? '');
            }}>{industry.environments.map((item) => <option key={item.environment_id} value={item.environment_id}>{item.name}</option>)}</select></label>
            <label>Incident<select aria-label="Industry incident" value={scenarioId} onChange={(event) => setScenarioId(event.target.value)}>{environment.scenario_ids.map((item) => {
              const reference = industry.scenario_references.find((candidate) => candidate.scenario_id === item);
              return <option key={item} value={item}>{reference?.title ?? item}</option>;
            })}</select></label>
            <label>Deterministic seed<input aria-label="Industry seed" type="number" min={0} value={seed} onChange={(event) => setSeed(Number(event.target.value))} /></label>
          </div>
        </div>

        <div className="generation-actions">
          <button type="button" onClick={() => setStep('EXPLORE')}><GitBranch />Explore architecture</button>
          <button type="button" onClick={cloneToStudio} disabled={busy}><Save />Clone in Scenario Studio</button>
        </div>

        <div className="generation-panel">
          <div className="generation-panel__header">
            <div><span>One entity graph · two perspectives</span><h4>{perspective === 'TECHNICAL' ? 'Technical Topology' : 'Business Dependency View'}</h4></div>
            <div className="generation-actions">
              <button type="button" className={perspective === 'TECHNICAL' ? 'generation-primary' : ''} onClick={() => setPerspective('TECHNICAL')}>Technical</button>
              <button type="button" className={perspective === 'BUSINESS' ? 'generation-primary' : ''} onClick={() => setPerspective('BUSINESS')}>Business</button>
            </div>
          </div>
          <TopologyPreview scenario={graph} lens={perspective === 'TECHNICAL' ? 'TELEMETRY' : 'INCIDENT'} run={run} />
        </div>

        <div className="generation-guided-grid">
          <article><span>Observed technical evidence</span><strong>{observed ? 'OBSERVED' : 'NOT ESTABLISHED'}</strong><p>{environment.telemetry_source_ids.join(', ')}</p></article>
          <article><span>Modeled business impact</span><strong>MODELED</strong><p>{industry.business_impacts[0]?.statement}</p></article>
          <article><span>Explicit assumptions</span><strong>{industry.business_impacts[0]?.assumptions.length ?? 0}</strong><p>{industry.business_impacts[0]?.assumptions.join(' ')}</p></article>
          <article><span>CIM</span><strong>NOT ESTABLISHED</strong><p>No industry context promotes source CIM status.</p></article>
        </div>

        {experienceMode === 'advanced' && (
          <div className="generation-panel">
            <div className="generation-panel__header"><div><span>Advanced contract view</span><h4>Source and dependency requirements</h4></div></div>
            <div className="generation-selection-list">
              {industry.telemetry_requirements.map((item) => <div className="generation-choice" key={item.source_id}><strong>{item.source_id}</strong><span>{item.role} · requires {item.evidence_classification}</span></div>)}
              {industry.dependencies.map((item) => <div className="generation-choice" key={item.dependency_id}><strong>{item.relationship_type}</strong><span>{item.assumption}</span></div>)}
            </div>
          </div>
        )}

        <div className="generation-panel">
          <div className="generation-panel__header"><div><span>Execute existing Scenario Pack</span><h4>Configure, run, observe, investigate, validate</h4></div><StatusBadge status={run?.status ?? preflight?.state ?? 'READY'} /></div>
          <div className="generation-actions">
            <button type="button" onClick={prepare} disabled={busy}><ShieldCheck />Run preflight</button>
            <button type="button" className="generation-primary" onClick={execute} disabled={busy || preflight?.state === 'BLOCKED'}><Play />Run incident</button>
            <button type="button" onClick={observe} disabled={busy || !run}><RefreshCw />Observe in Splunk</button>
            <button type="button" onClick={investigate} disabled={busy || !run}>Investigate</button>
            <button type="button" onClick={() => { setRun(null); setInvestigation(null); setSeed((value) => value + 1); setStep('CONFIGURE'); }}>Replay</button>
          </div>
          {run && <p>Run <code>{run.run_id}</code> · {run.status} · {run.source_ids.length} source channel(s)</p>}
          {investigation && <div className="generation-alert"><strong>{investigation.status}</strong><span>{investigation.result_count} result(s) · {investigation.detail}</span></div>}
        </div>

        <div className="generation-panel">
          <div className="generation-panel__header"><div><span>Impact guardrails</span><h4>What this reference does not claim</h4></div></div>
          <ul>{industry.business_impacts.flatMap((item) => item.exclusions).map((item) => <li key={item}>{item}</li>)}</ul>
        </div>
      </section>
    </div>
  );
}
