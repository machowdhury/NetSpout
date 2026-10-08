import { useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import {
  Activity,
  AlertTriangle,
  ArrowLeft,
  CheckCircle2,
  Download,
  Maximize2,
  Network,
  Search,
  ShieldCheck,
  X,
} from 'lucide-react';
import { dashboardApi } from '../../lib/dashboardApi';
import type {
  DashboardCatalog,
  DashboardEligibility,
  DashboardPack,
  DashboardPanel,
  DashboardPerspective,
} from '../../types/dashboard';

const PERSPECTIVES: DashboardPerspective[] = ['NOC', 'ENGINEER', 'EVIDENCE'];
const INSPECTOR_TABS = [
  'Overview',
  'Visualization',
  'Data',
  'SPL',
  'Fields',
  'CIM',
  'Tokens',
  'Dependencies',
  'Validation',
] as const;

const initialDashboard = () =>
  new URLSearchParams(window.location.search).get('dashboard') ?? '';
const initialRun = () =>
  new URLSearchParams(window.location.search).get('run') ?? '';

export function DashboardStudio() {
  const [catalog, setCatalog] = useState<DashboardCatalog | null>(null);
  const [selectedId, setSelectedId] = useState(initialDashboard);
  const [runId, setRunId] = useState(initialRun);
  const [pack, setPack] = useState<DashboardPack | null>(null);
  const [perspective, setPerspective] = useState<DashboardPerspective>('NOC');
  const [query, setQuery] = useState('');
  const [domain, setDomain] = useState('ALL');
  const [scenarioMaturity, setScenarioMaturity] = useState('ALL');
  const [dashboardMaturity, setDashboardMaturity] = useState('ALL');
  const [industry, setIndustry] = useState('ALL');
  const [validatedOnly, setValidatedOnly] = useState(false);
  const [recentOnly, setRecentOnly] = useState(false);
  const [recent, setRecent] = useState<string[]>([]);
  const [selectedPanel, setSelectedPanel] = useState<DashboardPanel | null>(null);
  const [inspectorTab, setInspectorTab] =
    useState<(typeof INSPECTOR_TABS)[number]>('Overview');
  const [tokens, setTokens] = useState<Record<string, string>>({});
  const [wallboard, setWallboard] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    dashboardApi
      .catalog()
      .then(setCatalog)
      .catch(() => setError('Dashboard catalog is unavailable.'));
  }, []);

  useEffect(() => {
    if (!selectedId) {
      return;
    }
    dashboardApi
      .pack(selectedId, runId || undefined)
      .then((result) => {
        setError('');
        setPack(result);
        setRecent((items) => [selectedId, ...items.filter((item) => item !== selectedId)].slice(0, 6));
      })
      .catch(() => {
        setPack(null);
        setError('This dashboard cannot be generated from verified scenario evidence.');
      })
      .finally(() => setBusy(false));
  }, [selectedId, runId]);

  useEffect(() => {
    const url = new URL(window.location.href);
    if (selectedId) url.searchParams.set('dashboard', selectedId);
    else url.searchParams.delete('dashboard');
    if (runId) url.searchParams.set('run', runId);
    else url.searchParams.delete('run');
    window.history.replaceState({}, '', url);
  }, [selectedId, runId]);

  const entries = useMemo(() => {
    if (!catalog) return [];
    const normalized = query.trim().toLowerCase();
    return catalog.dashboards.filter((item) => {
      const matchesQuery =
        !normalized ||
        `${item.title} ${item.scenario_id} ${item.source_ids.join(' ')}`
          .toLowerCase()
          .includes(normalized);
      return (
        matchesQuery &&
        (domain === 'ALL' || item.domain === domain) &&
        (industry === 'ALL' || item.industry_id === industry) &&
        (scenarioMaturity === 'ALL' || item.scenario_maturity === scenarioMaturity) &&
        (dashboardMaturity === 'ALL' || item.dashboard_maturity === dashboardMaturity) &&
        (!validatedOnly ||
          ['SPL_VALIDATED', 'DATA_VALIDATED', 'VISUALLY_VALIDATED', 'DASHBOARD_READY'].includes(
            item.dashboard_maturity,
          )) &&
        (!recentOnly || recent.includes(item.dashboard_id))
      );
    });
  }, [
    catalog,
    dashboardMaturity,
    domain,
    industry,
    query,
    recent,
    recentOnly,
    scenarioMaturity,
    validatedOnly,
  ]);

  const selectDashboard = (entry: DashboardEligibility) => {
    setSelectedId(entry.dashboard_id);
    setPerspective('NOC');
    setSelectedPanel(null);
    setTokens({});
  };

  const exportDashboard = async () => {
    if (!pack) return;
    setBusy(true);
    try {
      const result = await dashboardApi.export(pack.dashboard_id, runId || undefined);
      const blob = new Blob([JSON.stringify(result.definition, null, 2)], {
        type: 'application/json',
      });
      const href = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = href;
      anchor.download = `${pack.dashboard_id}.dashboard-studio.json`;
      anchor.click();
      URL.revokeObjectURL(href);
    } catch {
      setError('Validated export preview is unavailable.');
    } finally {
      setBusy(false);
    }
  };

  if (!pack) {
    return (
      <section className="dashboard-gallery" data-testid="dashboard-gallery">
        <header className="dashboard-gallery__hero">
          <div>
            <span className="dashboard-eyebrow">Scenario-aware operations</span>
            <h2>Dashboard Gallery</h2>
            <p>
              Select an eligible scenario to generate topology, investigations, and
              evidence from its verified contracts.
            </p>
          </div>
          <div className="dashboard-gallery__stats">
            <strong>{catalog?.eligible_count ?? '—'}</strong>
            <span>eligible scenarios</span>
            <strong>{catalog?.recipes.length ?? '—'}</strong>
            <span>reusable recipes</span>
          </div>
        </header>

        <div className="dashboard-filters">
          <label className="dashboard-search">
            <Search aria-hidden="true" />
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search scenario, source, vendor, or product"
              aria-label="Search dashboards"
            />
          </label>
          <FilterSelect label="Domain" value={domain} onChange={setDomain} values={unique(catalog?.dashboards.map((item) => item.domain))} />
          <FilterSelect label="Industry" value={industry} onChange={setIndustry} values={unique(catalog?.dashboards.map((item) => item.industry_id).filter(Boolean) as string[])} />
          <FilterSelect label="Scenario maturity" value={scenarioMaturity} onChange={setScenarioMaturity} values={unique(catalog?.dashboards.map((item) => item.scenario_maturity))} />
          <FilterSelect label="Dashboard maturity" value={dashboardMaturity} onChange={setDashboardMaturity} values={unique(catalog?.dashboards.map((item) => item.dashboard_maturity))} />
          <button type="button" className={validatedOnly ? 'is-active' : ''} onClick={() => setValidatedOnly((value) => !value)}>
            Validated
          </button>
          <button type="button" className={recentOnly ? 'is-active' : ''} onClick={() => setRecentOnly((value) => !value)}>
            Recently used
          </button>
        </div>

        {error && <div className="dashboard-notice dashboard-notice--error">{error}</div>}
        <div className="dashboard-gallery__grid">
          {entries.map((entry) => (
            <article
              className={`dashboard-card ${entry.state !== 'ELIGIBLE' ? 'dashboard-card--blocked' : ''}`}
              key={entry.dashboard_id}
            >
              <div className="dashboard-card__topline">
                <span>{entry.domain}</span>
                <Maturity value={entry.dashboard_maturity} />
              </div>
              <h3>{entry.title}</h3>
              <code>{entry.scenario_id}</code>
              <p>{entry.reasons.join(' ')}</p>
              <div className="dashboard-card__meta">
                <span>{entry.source_ids.length} sources</span>
                <span>{entry.recipe_ids.length} recipes</span>
                <span>{entry.industry_id ?? entry.scenario_maturity}</span>
              </div>
              <button
                type="button"
                disabled={entry.state !== 'ELIGIBLE'}
                onClick={() => selectDashboard(entry)}
              >
                {entry.state === 'ELIGIBLE' ? 'Open dashboard' : 'Research required'}
              </button>
            </article>
          ))}
        </div>
      </section>
    );
  }

  const visiblePanels = pack.panels.filter((item) => item.perspective === perspective);
  const selectedEligibility = catalog?.dashboards.find(
    (item) => item.dashboard_id === pack.dashboard_id,
  );

  return (
    <section
      className={`dashboard-studio ${wallboard ? 'dashboard-studio--wallboard' : ''}`}
      data-testid="dashboard-studio"
    >
      <header className="dashboard-studio__header">
        <button type="button" className="dashboard-back" onClick={() => setSelectedId('')}>
          <ArrowLeft /> Gallery
        </button>
        <div>
          <span className="dashboard-eyebrow">{pack.domain} · {pack.category}</span>
          <h2>{pack.title}</h2>
          <span>{pack.scenario_id} · {pack.topology_ref}</span>
        </div>
        <label className="dashboard-run">
          Run context
          <input
            value={runId}
            placeholder="Select or enter run ID"
            onChange={(event) => setRunId(event.target.value.replace(/[^A-Za-z0-9_.:-]/g, ''))}
          />
        </label>
        <Maturity value={pack.maturity} />
        <button type="button" onClick={() => setWallboard((value) => !value)}>
          {wallboard ? <X /> : <Maximize2 />} {wallboard ? 'Exit wallboard' : 'NOC wallboard'}
        </button>
        <button type="button" onClick={exportDashboard} disabled={busy}>
          <Download /> Export JSON
        </button>
      </header>

      {!runId && (
        <div className="dashboard-notice">
          Preview mode — select a run to generate executable, run-scoped SPL. No telemetry
          values are inferred.
        </div>
      )}
      {error && <div className="dashboard-notice dashboard-notice--error">{error}</div>}

      {!wallboard && (
        <div className="dashboard-perspectives" role="tablist" aria-label="Dashboard perspective">
          {PERSPECTIVES.map((item) => (
            <button
              type="button"
              role="tab"
              aria-selected={perspective === item}
              className={perspective === item ? 'is-active' : ''}
              onClick={() => setPerspective(item)}
              key={item}
            >
              {item}
            </button>
          ))}
        </div>
      )}

      <div className="dashboard-kpis">
        <Kpi label="Incident state" value={runId ? 'AWAITING VALIDATION' : 'NOT RUN'} icon={<Activity />} />
        <Kpi label="Scenario severity" value="MODELED IN PACK" icon={<AlertTriangle />} />
        <Kpi label="Affected entities" value={runId ? 'NOT VERIFIED' : 'NOT RUN'} icon={<Network />} />
        <Kpi label="Validation" value={pack.maturity.replaceAll('_', ' ')} icon={<ShieldCheck />} />
      </div>

      <div className="dashboard-studio__layout">
        <DashboardTopology
          pack={pack}
          activeEntity={tokens.entity}
          onEntity={(value) => setTokens((current) => ({ ...current, entity: value }))}
          onRelationship={(value) =>
            setTokens((current) => ({ ...current, relationship: value }))
          }
        />

        <div className="dashboard-impact">
          <span>Operational context</span>
          <strong>{selectedEligibility?.title ?? pack.scenario_id}</strong>
          <p>{pack.description}</p>
          <dl>
            <div><dt>Sources</dt><dd>{pack.telemetry_manifest.length}</dd></div>
            <div><dt>Investigations</dt><dd>{pack.investigation_recipe_ids.length}</dd></div>
            <div><dt>CIM</dt><dd>{pack.cim_status}</dd></div>
            <div><dt>Recovery</dt><dd>{runId ? 'NOT VERIFIED' : 'NOT RUN'}</dd></div>
          </dl>
        </div>
      </div>

      {!wallboard && (
        <>
          <div className="dashboard-tokenbar">
            <span>Active filters</span>
            {Object.entries(tokens).map(([key, value]) => (
              <button type="button" key={key} onClick={() => setTokens((current) => {
                const next = { ...current };
                delete next[key];
                return next;
              })}>
                {key}: {value} <X />
              </button>
            ))}
            {Object.keys(tokens).length > 0 && (
              <button type="button" onClick={() => setTokens({})}>Clear all</button>
            )}
            {Object.keys(tokens).length === 0 && <em>Full scenario</em>}
          </div>

          <div className="dashboard-panels">
            {visiblePanels.map((panel) => (
              <PanelCard
                key={panel.panel_id}
                panel={panel}
                runId={runId}
                onInspect={() => {
                  setSelectedPanel(panel);
                  setInspectorTab('Overview');
                }}
                onDrilldown={(token, value) =>
                  setTokens((current) => ({ ...current, [token]: value }))
                }
              />
            ))}
          </div>
        </>
      )}

      {selectedPanel && (
        <AdvancedInspector
          panel={selectedPanel}
          pack={pack}
          tab={inspectorTab}
          onTab={setInspectorTab}
          onClose={() => setSelectedPanel(null)}
        />
      )}
    </section>
  );
}

function FilterSelect({
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
    <label>
      <span>{label}</span>
      <select value={value} onChange={(event) => onChange(event.target.value)}>
        <option value="ALL">All</option>
        {values.map((item) => <option value={item} key={item}>{item}</option>)}
      </select>
    </label>
  );
}

function Maturity({ value }: { value: string }) {
  return <span className={`dashboard-maturity dashboard-maturity--${value.toLowerCase()}`}>{value.replaceAll('_', ' ')}</span>;
}

function Kpi({ label, value, icon }: { label: string; value: string; icon: ReactNode }) {
  return <div className="dashboard-kpi">{icon}<span>{label}</span><strong>{value}</strong></div>;
}

function DashboardTopology({
  pack,
  activeEntity,
  onEntity,
  onRelationship,
}: {
  pack: DashboardPack;
  activeEntity?: string;
  onEntity: (value: string) => void;
  onRelationship: (value: string) => void;
}) {
  const nodes = pack.entity_graph.nodes;
  const positioned = nodes.map((node, index) => ({
    node,
    id: node.node_id ?? node.entity_id ?? `entity-${index}`,
    x: 100 + (index % 4) * 190,
    y: 90 + Math.floor(index / 4) * 145,
  }));
  const byId = new Map(positioned.map((item) => [item.id, item]));
  return (
    <div className="dashboard-topology" data-testid="dashboard-topology">
      <div className="dashboard-panel__heading"><span>Primary topology</span><small>Shared scenario graph</small></div>
      <svg viewBox="0 0 760 390" role="img" aria-label={`${pack.title} topology`}>
        {pack.entity_graph.relationships.map((relationship) => {
          const source = byId.get(relationship.source_node_id ?? relationship.source_entity_id ?? '');
          const target = byId.get(relationship.target_node_id ?? relationship.target_entity_id ?? '');
          if (!source || !target) return null;
          return (
            <g
              key={relationship.relationship_id}
              role="button"
              tabIndex={0}
              onClick={() => onRelationship(relationship.relationship_id)}
            >
              <line x1={source.x} y1={source.y} x2={target.x} y2={target.y} />
              <text x={(source.x + target.x) / 2} y={(source.y + target.y) / 2 - 8}>
                {relationship.relationship_type}
              </text>
            </g>
          );
        })}
        {positioned.map(({ node, id, x, y }) => (
          <g
            key={id}
            className={activeEntity === id ? 'is-selected' : ''}
            transform={`translate(${x} ${y})`}
            role="button"
            tabIndex={0}
            onClick={() => onEntity(id)}
          >
            <rect x="-55" y="-28" width="110" height="56" rx="8" />
            <text y="-3">{node.label ?? id}</text>
            <text className="dashboard-topology__role" y="15">{node.role ?? node.entity_type ?? 'ENTITY'}</text>
          </g>
        ))}
      </svg>
    </div>
  );
}

function PanelCard({
  panel,
  runId,
  onInspect,
  onDrilldown,
}: {
  panel: DashboardPanel;
  runId: string;
  onInspect: () => void;
  onDrilldown: (token: string, value: string) => void;
}) {
  return (
    <article className="dashboard-panel">
      <div className="dashboard-panel__heading">
        <div><span>{panel.title}</span><small>{panel.visualization_id}</small></div>
        <button type="button" onClick={onInspect}>Inspect</button>
      </div>
      <p>{panel.purpose}</p>
      <div className="dashboard-panel__state">
        {runId && panel.executable ? (
          <><CheckCircle2 /> Run-scoped SPL generated · data pending validation</>
        ) : panel.executable ? (
          <><AlertTriangle /> Query unavailable</>
        ) : (
          <><Network /> Contract-derived context · no measured value claimed</>
        )}
      </div>
      <div className="dashboard-panel__drilldowns">
        {panel.drilldowns.map((item) => (
          <button type="button" key={`${item.token}-${item.field}`} onClick={() => onDrilldown(item.token, item.field)}>
            {item.token} → {item.field}
          </button>
        ))}
      </div>
    </article>
  );
}

function AdvancedInspector({
  panel,
  pack,
  tab,
  onTab,
  onClose,
}: {
  panel: DashboardPanel;
  pack: DashboardPack;
  tab: (typeof INSPECTOR_TABS)[number];
  onTab: (value: (typeof INSPECTOR_TABS)[number]) => void;
  onClose: () => void;
}) {
  const content: Record<(typeof INSPECTOR_TABS)[number], ReactNode> = {
    Overview: <><h4>{panel.title}</h4><p>{panel.purpose}</p><code>{panel.recipe_id}</code></>,
    Visualization: <dl><div><dt>Requested</dt><dd>{panel.requested_visualization_id}</dd></div><div><dt>Selected</dt><dd>{panel.visualization_id}</dd></div><div><dt>Compatibility</dt><dd>{panel.dependency_state}</dd></div></dl>,
    Data: <><p>Expected result shape</p><Json value={panel.expected_shape} /></>,
    SPL: panel.query ? <pre>{panel.query}</pre> : <p>NOT GENERATED — select a run context.</p>,
    Fields: <><p>Required: {panel.required_fields.join(', ') || 'NONE'}</p><p>Optional: {panel.optional_fields.join(', ') || 'NONE'}</p><p>Observed: {pack.observed_fields.join(', ') || 'NOT VERIFIED'}</p></>,
    CIM: <p>{pack.cim_status === 'NOT_ESTABLISHED' ? 'NOT ESTABLISHED — no CIM-dependent functionality is claimed.' : pack.cim_status}</p>,
    Tokens: <Json value={panel.drilldowns} />,
    Dependencies: <><p>{panel.dependency_state}</p><p>Fallback: {panel.visualization_id}</p></>,
    Validation: <><p>Dashboard maturity: {pack.maturity}</p><p>Evidence: {pack.validation_evidence.length ? `${pack.validation_evidence.length} record(s)` : 'NOT VERIFIED'}</p><p>Export: {pack.export_compatibility}</p></>,
  };
  return (
    <aside className="dashboard-inspector" aria-label="Advanced Inspector">
      <header><div><span>Advanced Inspector</span><strong>{panel.panel_id}</strong></div><button type="button" onClick={onClose} aria-label="Close inspector"><X /></button></header>
      <nav>{INSPECTOR_TABS.map((item) => <button type="button" className={tab === item ? 'is-active' : ''} onClick={() => onTab(item)} key={item}>{item}</button>)}</nav>
      <div className="dashboard-inspector__content">{content[tab]}</div>
    </aside>
  );
}

function Json({ value }: { value: unknown }) {
  return <pre>{JSON.stringify(value, null, 2)}</pre>;
}

function unique(values: string[] | undefined) {
  return [...new Set(values ?? [])].sort();
}
