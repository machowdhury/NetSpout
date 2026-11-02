import { useEffect, useMemo, useState } from 'react';
import { AlertTriangle, Boxes, Filter, Network, Search, ShieldCheck } from 'lucide-react';
import { cisco100Api } from '../../lib/cisco100Api';
import type { Cisco100Catalog, Cisco100Scenario } from '../../types/cisco100';
import type { GenerationScenario } from '../../types/generation';
import { TopologyPreview } from '../generation/TopologyPreview';
import { Panel, StatePanel, StatusBadge } from '../ui/SystemPrimitives';

type ViewMode = 'browser' | 'matrix' | 'debt';

const maturityOrder = [
  'GOLDEN',
  'SPLUNK_VALIDATED',
  'RUNTIME_VALIDATED',
  'FORMAT_VALIDATED',
  'CONTRACTED',
  'RESEARCHED',
  'CANDIDATE',
  'RESEARCH_REQUIRED',
  'UNSUPPORTED',
  'BLOCKED',
] as const;

const referenceScenarioIds = [
  'C100-ENT-001',
  'C100-SP-001',
  'C100-DC-001',
  'C100-SEC-001',
  'C100-CRI-002',
] as const;

function options(values: string[]) {
  return [...new Set(values)].sort();
}

function toVisualizationScenario(scenario: Cisco100Scenario): GenerationScenario {
  const zoneId = scenario.zones[0]?.toLowerCase().replaceAll(/[^a-z0-9]+/g, '-') ?? 'scenario';
  const observerId = 'splunk-observer.example';
  const nodes = scenario.entities.map((entity, index) => {
    const technology = scenario.technologies[index % scenario.technologies.length] ?? 'External dependency';
    return {
      node_id: entity,
      entity_id: entity,
      technology_id: technology,
      zone_id: zoneId,
      role: index === 0 ? 'affected-origin' : 'dependency',
      source_ids: index === 0 ? scenario.telemetry_sources : [],
      label: `${entity} · ${technology}`,
      description: `${technology} scenario-definition entity`,
    };
  });
  if (scenario.telemetry_sources.length) {
    nodes.push({
      node_id: observerId,
      entity_id: observerId,
      technology_id: 'splunk-enterprise',
      zone_id: zoneId,
      role: 'observer',
      source_ids: [],
      label: 'Splunk',
      description: 'Declared observation destination',
    });
  }
  return {
    scenario_id: scenario.scenario_id,
    title: scenario.title,
    description: scenario.technical_objective,
    story: scenario.story,
    domain: scenario.domain,
    category: scenario.category,
    technical_description: scenario.technical_objective,
    difficulty: scenario.difficulty,
    expected_duration_minutes: Math.max(1, Math.ceil(Math.max(...scenario.timeline.map((item) => item.offset_seconds), 60) / 60)),
    learning_objectives: [scenario.technical_objective],
    business_impact: scenario.business_impact,
    prerequisites: scenario.research_gaps,
    technology_ids: scenario.technologies,
    source_ids: scenario.telemetry_sources,
    entities: [...scenario.entities, ...(scenario.telemetry_sources.length ? [observerId] : [])],
    zones: [{ zone_id: zoneId, label: scenario.zones.join(' / ') }],
    nodes,
    relationships: scenario.relationships.map((relationship, index) => ({
      relationship_id: `relationship-${index + 1}`,
      source_node_id: scenario.entities[Math.min(index, scenario.entities.length - 1)],
      target_node_id: scenario.entities[Math.min(index + 1, scenario.entities.length - 1)],
      relationship_type: relationship,
      protocol: null,
      telemetry_source_ids: scenario.telemetry_sources,
    })),
    telemetry_paths: scenario.telemetry_sources.map((sourceId) => ({
      path_id: `path-${sourceId}`,
      source_id: sourceId,
      producer_node_id: scenario.entities[0],
      observer_node_id: observerId,
      label: sourceId,
      protocol: scenario.native_transports.join(', ') || 'NOT ESTABLISHED',
    })),
    incident_path: scenario.entities,
    runtime_state_keys: Object.keys(scenario.enterprise_state),
    timeline: scenario.timeline.map((item, index) => ({
      step_id: `${item.stage}-${index}`,
      stage: item.stage,
      description: item.expected_observation,
      state_changes: item.state_changes,
      entity_state_changes: { [scenario.entities[0]]: Object.entries(item.state_changes).map(([key, value]) => `${key}=${value}`).join(',') },
      incident_ids: item.stage === 'INCIDENT' ? [`incident-${scenario.scenario_id}`] : [],
      evidence_source_ids: scenario.telemetry_sources,
    })),
    expected_evidence: scenario.runtime_validation,
    investigation_recipe_ids: scenario.investigation_pack.recipe_ids,
    integration_recommendation_ids: scenario.splunk_integrations,
    production_replication_guidance: scenario.production_portability.requirements,
    visualization: { mode: 'AUTOMATIC', direction: 'LEFT_TO_RIGHT', curated_layout_ref: null },
    composition_id: `definition-${scenario.scenario_id}`,
    verification_state: scenario.maturity === 'GOLDEN' ? 'VERIFIED' : 'RESEARCH_REQUIRED',
    maturity: scenario.maturity,
    source_count: scenario.telemetry_sources.length,
    integration_count: scenario.splunk_integrations.length,
    runnable: scenario.execution_enabled,
  };
}

function SelectFilter({
  label,
  value,
  values,
  onChange,
}: {
  label: string;
  value: string;
  values: string[];
  onChange: (value: string) => void;
}) {
  return (
    <label className="c100-filter">
      <span>{label}</span>
      <select value={value} onChange={(event) => onChange(event.target.value)}>
        <option value="">All</option>
        {values.map((item) => <option value={item} key={item}>{item}</option>)}
      </select>
    </label>
  );
}

function ScenarioDetail({ scenario }: { scenario: Cisco100Scenario }) {
  const canRun = scenario.execution_enabled && scenario.runtime_scenario_id;
  const visualization = useMemo(() => toVisualizationScenario(scenario), [scenario]);
  const [cloneError, setCloneError] = useState('');
  const [cloning, setCloning] = useState(false);
  const openGuidedReference = () => {
    if (!scenario.runtime_scenario_id) return;
    window.sessionStorage.setItem(
      'netspout-guided-scenario-id',
      scenario.runtime_scenario_id,
    );
    window.location.hash = '/generate/scenarios';
  };
  const cloneDefinition = async () => {
    setCloning(true);
    setCloneError('');
    try {
      const draft = await cisco100Api.studioDraft(scenario.scenario_id);
      window.sessionStorage.setItem('netspout-studio-import-draft', JSON.stringify(draft));
      window.location.hash = '/build/studio';
    } catch (reason) {
      setCloneError(String(reason));
      setCloning(false);
    }
  };
  return (
    <section className="c100-detail" data-testid="cisco100-scenario-detail">
      <header className="c100-detail__header">
        <div>
          <span className="eyebrow">{scenario.scenario_id} · {scenario.domain}</span>
          <h2>{scenario.title}</h2>
          <p>{scenario.story}</p>
        </div>
        <StatusBadge status={scenario.maturity.replaceAll('_', ' ')} />
      </header>

      <div className="c100-detail__grid">
        <Panel title="Objective and impact">
          <strong>Technical objective</strong>
          <p>{scenario.technical_objective}</p>
          <strong>Business impact</strong>
          <p>{scenario.business_impact}</p>
          <strong>Failure / attack vector</strong>
          <p>{scenario.failure_or_attack_vector}</p>
        </Panel>
        <Panel title="Architecture">
          <strong>Technologies</strong>
          <p>{scenario.technologies.join(' · ')}</p>
          <strong>Entities and zones</strong>
          <p>{scenario.entities.join(' → ')}</p>
          <p>{scenario.zones.join(' · ')}</p>
          <strong>Relationships</strong>
          <p>{scenario.relationships.join(' · ')}</p>
        </Panel>
      </div>

      <Panel title="Scenario topology">
        <TopologyPreview scenario={visualization} sources={[]} />
      </Panel>

      <Panel title="Shared enterprise state and simulation clock">
        <div className="c100-timeline">
          {scenario.timeline.map((transition) => (
            <article key={`${transition.stage}-${transition.offset_seconds}`}>
              <span>{transition.offset_seconds}s</span>
              <strong>{transition.stage}</strong>
              <code>{Object.entries(transition.state_changes).map(([key, value]) => `${key}=${value}`).join(', ')}</code>
              <p>{transition.expected_observation}</p>
            </article>
          ))}
        </div>
      </Panel>

      <div className="c100-detail__grid">
        <Panel title="Telemetry and contracts">
          <strong>Sources</strong>
          <p>{scenario.telemetry_sources.join(' · ') || 'RESEARCH REQUIRED'}</p>
          <strong>Native transports</strong>
          <p>{scenario.native_transports.join(' · ') || 'NOT ESTABLISHED'}</p>
          <strong>Source contracts / Product Packs</strong>
          <p>{[...scenario.source_contracts, ...scenario.product_packs].join(' · ') || 'NOT ESTABLISHED'}</p>
          <strong>Splunk / sourcetypes</strong>
          <p>{[...scenario.splunk_integrations, ...scenario.sourcetypes].join(' · ') || 'NOT ESTABLISHED'}</p>
          <strong>CIM</strong>
          <p>{Object.keys(scenario.cim_relationships).length
            ? Object.entries(scenario.cim_relationships).map(([key, value]) => `${key}: ${value}`).join(' · ')
            : 'NOT ESTABLISHED'}</p>
        </Panel>
        <Panel title="Evidence Inspector">
          <strong>Evidence references</strong>
          <p>{scenario.evidence_references.join(' · ') || 'No authoritative telemetry evidence attached at this maturity.'}</p>
          <strong>Validation state</strong>
          <p>{scenario.validation_state.replaceAll('_', ' ')}</p>
          <strong>Known limitations</strong>
          <ul>{scenario.limitations.map((item) => <li key={item}>{item}</li>)}</ul>
        </Panel>
      </div>

      {scenario.maturity === 'RESEARCH_REQUIRED' && (
        <StatePanel
          kind="unavailable"
          title="Research required — generation blocked"
          message={`Missing evidence: ${scenario.research_gaps.join('; ')}. No fallback event, sourcetype, TA, or CIM mapping will be generated.`}
        />
      )}

      <div className="c100-detail__grid">
        <Panel title="Investigation Pack">
          <StatusBadge status={scenario.investigation_pack.status.replaceAll('_', ' ')} />
          <ul>
            {scenario.investigation_pack.questions.map((item) => <li key={item}>{item}</li>)}
            {scenario.investigation_pack.expected_findings.map((item) => <li key={item}>Expected: {item}</li>)}
          </ul>
          <p>SPL: {scenario.investigation_pack.spl_classifications.join(' · ') || 'NOT CLASSIFIED'}</p>
          {scenario.production_portability.production_portable_spl.map((query) => (
            <code className="c100-query" key={query}>PRODUCTION-PORTABLE · {query}</code>
          ))}
          {scenario.production_portability.netspout_specific_spl.map((query) => (
            <code className="c100-query" key={query}>NETSPOUT-SPECIFIC · {query}</code>
          ))}
        </Panel>
        <Panel title="Troubleshooting guidance">
          <StatusBadge status={scenario.troubleshooting_pack.status.replaceAll('_', ' ')} />
          <p>{scenario.troubleshooting_pack.operation_ids.join(' · ')
            || scenario.troubleshooting_pack.research_required.join(' · ')}</p>
        </Panel>
      </div>

      <Panel title="Take This to Production">
        <StatusBadge status={scenario.production_portability.status.replaceAll('_', ' ')} />
        <div className="c100-production">
          <section><strong>Requirements</strong><ul>{scenario.production_portability.requirements.map((item) => <li key={item}>{item}</li>)}</ul></section>
          <section><strong>Production-portable SPL</strong><ul>{scenario.production_portability.production_portable_spl.map((item) => <li key={item}><code>{item}</code></li>)}</ul></section>
          <section><strong>Known gaps</strong><ul>{scenario.production_portability.known_gaps.map((item) => <li key={item}>{item}</li>)}</ul></section>
        </div>
      </Panel>

      <div className="c100-actions">
        {canRun
          ? <button className="button button--primary" type="button" onClick={openGuidedReference}>Open Guided Scenario</button>
          : <button className="button button--primary" type="button" disabled>Generation blocked at {scenario.maturity}</button>}
        <button className="button button--quiet" type="button" disabled={cloning} onClick={cloneDefinition}>
          {cloning
            ? 'Preparing private draft…'
            : canRun
              ? 'Clone runnable reference in Scenario Studio'
              : 'Clone definition in Scenario Studio'}
        </button>
      </div>
      {cloneError && <StatePanel kind="error" message={cloneError} />}
    </section>
  );
}

export function Cisco100View() {
  const [catalog, setCatalog] = useState<Cisco100Catalog | null>(null);
  const [error, setError] = useState('');
  const [view, setView] = useState<ViewMode>('browser');
  const [query, setQuery] = useState('');
  const [domain, setDomain] = useState('');
  const [technology, setTechnology] = useState('');
  const [telemetry, setTelemetry] = useState('');
  const [protocol, setProtocol] = useState('');
  const [integration, setIntegration] = useState('');
  const [maturity, setMaturity] = useState('');
  const [category, setCategory] = useState('');
  const [difficulty, setDifficulty] = useState('');
  const [selectedId, setSelectedId] = useState('C100-SP-001');

  useEffect(() => {
    cisco100Api.catalog().then(setCatalog).catch((reason) => setError(String(reason)));
  }, []);

  const filtered = useMemo(() => {
    if (!catalog) return [];
    const needle = query.trim().toLowerCase();
    return catalog.scenarios.filter((scenario) => (
      (!needle || `${scenario.scenario_id} ${scenario.title} ${scenario.story}`.toLowerCase().includes(needle))
      && (!domain || scenario.domain === domain)
      && (!technology || scenario.technologies.includes(technology))
      && (!telemetry || scenario.telemetry_sources.includes(telemetry))
      && (!protocol || scenario.native_transports.includes(protocol))
      && (!integration || scenario.splunk_integrations.includes(integration))
      && (!maturity || scenario.maturity === maturity)
      && (!category || scenario.category === category)
      && (!difficulty || scenario.difficulty === difficulty)
    ));
  }, [catalog, query, domain, technology, telemetry, protocol, integration, maturity, category, difficulty]);

  if (error) return <StatePanel kind="error" title="Cisco 100 unavailable" message={error} />;
  if (!catalog) return <StatePanel kind="loading" message="Loading evidence-gated scenario definitions." />;

  const selected = filtered.find((item) => item.scenario_id === selectedId) ?? filtered[0] ?? null;
  const all = catalog.scenarios;
  const references = referenceScenarioIds
    .map((scenarioId) => all.find((item) => item.scenario_id === scenarioId))
    .filter((item): item is Cisco100Scenario => Boolean(item));
  const showReference = (scenarioId: string) => {
    setView('browser');
    setQuery('');
    setDomain('');
    setTechnology('');
    setTelemetry('');
    setProtocol('');
    setIntegration('');
    setMaturity('');
    setCategory('');
    setDifficulty('');
    setSelectedId(scenarioId);
  };

  return (
    <div className="c100-workspace" data-testid="cisco100-dashboard">
      <header className="c100-hero">
        <div>
          <span className="eyebrow">Cisco 100 Scenario Factory</span>
          <h1>Scenario breadth without fabricated support</h1>
          <p>{catalog.independence_notice}</p>
        </div>
        <div className="c100-primary-metric">
          <strong>{catalog.summary.scenario_definitions}</strong>
          <span>Scenario definitions</span>
          <small>Definitions are not support claims</small>
        </div>
      </header>

      <section className="c100-domain-strip" aria-label="Cisco 100 domain distribution">
        {Object.entries(catalog.summary.domains).map(([name, count]) => (
          <button type="button" key={name} className={domain === name ? 'is-active' : ''} onClick={() => setDomain(domain === name ? '' : name)}>
            <span>{name}</span><strong>{count}</strong>
          </button>
        ))}
      </section>

      <section className="c100-reference-strip" aria-label="Multi-domain reference readiness" data-testid="cisco100-reference-readiness">
        <header>
          <div>
            <span className="eyebrow">Evidence-backed reference depth</span>
            <strong>One truthful reference per Cisco 100 domain</strong>
          </div>
          <small>Runtime and Splunk indicators reflect recorded evidence, not catalog intent.</small>
        </header>
        <div>
          {references.map((scenario) => (
            <button type="button" key={scenario.scenario_id} onClick={() => showReference(scenario.scenario_id)}>
              <span>{scenario.domain}</span>
              <strong>{scenario.scenario_id}</strong>
              <StatusBadge status={scenario.maturity.replaceAll('_', ' ')} />
              <small>{scenario.evidence_references.length} evidence ref{scenario.evidence_references.length === 1 ? '' : 's'}</small>
              <small>Runtime {scenario.runtime_validation.length ? 'recorded' : 'pending'} · Splunk {scenario.splunk_validation.length ? 'recorded' : 'pending'}</small>
            </button>
          ))}
        </div>
      </section>

      <section className="c100-maturity-grid" data-testid="cisco100-maturity">
        {maturityOrder.map((state) => (
          <button type="button" key={state} onClick={() => setMaturity(maturity === state ? '' : state)} className={maturity === state ? 'is-active' : ''}>
            <strong>{catalog.summary.maturity[state]}</strong>
            <span>{state.replaceAll('_', ' ')}</span>
          </button>
        ))}
      </section>

      <nav className="c100-tabs" aria-label="Cisco 100 views">
        {(['browser', 'matrix', 'debt'] as ViewMode[]).map((item) => (
          <button type="button" key={item} className={view === item ? 'is-active' : ''} onClick={() => setView(item)}>
            {item === 'debt' ? 'Readiness & Evidence Debt' : item}
          </button>
        ))}
      </nav>

      {view === 'browser' && (
        <>
          <section className="c100-filters" aria-label="Cisco 100 filters">
            <label className="c100-search"><Search size={16} /><input aria-label="Search Cisco 100" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search ID, title, or story" /></label>
            <SelectFilter label="Product / technology" value={technology} values={options(all.flatMap((item) => item.technologies))} onChange={setTechnology} />
            <SelectFilter label="Telemetry" value={telemetry} values={options(all.flatMap((item) => item.telemetry_sources))} onChange={setTelemetry} />
            <SelectFilter label="Protocol" value={protocol} values={options(all.flatMap((item) => item.native_transports))} onChange={setProtocol} />
            <SelectFilter label="Splunk integration" value={integration} values={options(all.flatMap((item) => item.splunk_integrations))} onChange={setIntegration} />
            <SelectFilter label="Category" value={category} values={options(all.map((item) => item.category))} onChange={setCategory} />
            <SelectFilter label="Difficulty" value={difficulty} values={options(all.map((item) => item.difficulty))} onChange={setDifficulty} />
          </section>
          <div className="c100-browser">
            <aside className="c100-scenarios" data-testid="cisco100-scenario-list">
              <header><Filter size={15} /><strong>{filtered.length} definitions</strong></header>
              {filtered.map((scenario) => (
                <button type="button" key={scenario.scenario_id} className={selected?.scenario_id === scenario.scenario_id ? 'is-selected' : ''} onClick={() => setSelectedId(scenario.scenario_id)}>
                  <span><small>{scenario.scenario_id}</small>{scenario.title}</span>
                  <StatusBadge status={scenario.maturity.replaceAll('_', ' ')} />
                </button>
              ))}
            </aside>
            {selected ? <ScenarioDetail scenario={selected} /> : <StatePanel kind="empty" message="No scenario matches these filters." />}
          </div>
        </>
      )}

      {view === 'matrix' && (
        <Panel title="Product × telemetry × scenario × validation" className="c100-matrix-panel">
          <div className="c100-matrix" data-testid="cisco100-matrix">
            <div className="c100-matrix__header"><span>Scenario</span><span>Products</span><span>Telemetry</span><span>Contract</span><span>Runtime</span><span>Splunk</span><span>CIM</span><span>Golden</span></div>
            {all.map((scenario) => (
              <div key={scenario.scenario_id}>
                <span><strong>{scenario.scenario_id}</strong><small>{scenario.title}</small></span>
                <span>{scenario.technologies.join(', ')}</span>
                <span>{scenario.telemetry_sources.join(', ') || 'Research required'}</span>
                <span>{scenario.source_contracts.length ? '✓' : '—'}</span>
                <span>{scenario.runtime_validation.length ? '✓' : '—'}</span>
                <span>{scenario.splunk_validation.length ? '✓' : '—'}</span>
                <span>{Object.values(scenario.cim_relationships).join(', ') || 'NOT ESTABLISHED'}</span>
                <span>{scenario.maturity === 'GOLDEN' ? '✓' : '—'}</span>
              </div>
            ))}
          </div>
        </Panel>
      )}

      {view === 'debt' && (
        <div className="c100-debt" data-testid="cisco100-evidence-debt">
          <Panel title="Evidence debt">
            <div className="c100-debt-grid">
              {Object.entries(catalog.evidence_debt).map(([key, count]) => (
                <article key={key}><AlertTriangle size={17} /><strong>{count}</strong><span>{key.replaceAll('_', ' ')}</span></article>
              ))}
            </div>
          </Panel>
          <Panel title="Scenario Factory pipeline">
            <div className="c100-pipeline">
              {['Candidate', 'Research', 'Evidence', 'Contracts', 'Static validation', 'Format', 'Runtime', 'Splunk', 'Guided Lab', 'Golden'].map((item) => <span key={item}>{item}</span>)}
            </div>
          </Panel>
          <Panel title="Reusable assets">
            {catalog.shared_assets.map((asset) => (
              <article className="c100-shared-asset" key={asset.asset_id}>
                <Boxes size={17} /><div><strong>{asset.asset_id}</strong><p>{asset.asset_type} · {asset.scenario_ids.join(', ')}</p></div>
              </article>
            ))}
          </Panel>
          <Panel title="Research queue">
            <div className="c100-research-queue">
              {catalog.research_queue.map((item) => (
                <article key={item.research_id}>
                  <span>{item.scenario_id}</span><strong>{item.product}</strong>
                  <p>{item.missing_claim}</p><small>Blocks {item.blocking_gate} · {item.status}</small>
                </article>
              ))}
            </div>
          </Panel>
        </div>
      )}

      <footer className="c100-trust">
        <ShieldCheck size={18} />
        <span>Evidence determines maturity. Research Required and Unsupported are truthful outcomes.</span>
        <Network size={18} />
      </footer>
    </div>
  );
}
