import { useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import {
  Activity,
  AlertTriangle,
  ArrowLeft,
  CheckCircle2,
  ChevronRight,
  Download,
  Grid2X2,
  List,
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
  DashboardStudioExport,
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
  const [galleryLayout, setGalleryLayout] = useState<'CARD' | 'TABLE'>('CARD');
  const [researchEntry, setResearchEntry] = useState<DashboardEligibility | null>(null);
  const [selectedPanel, setSelectedPanel] = useState<DashboardPanel | null>(null);
  const [inspectorTab, setInspectorTab] =
    useState<(typeof INSPECTOR_TABS)[number]>('Overview');
  const [tokens, setTokens] = useState<Record<string, string>>({});
  const [wallboard, setWallboard] = useState(false);
  const [busy, setBusy] = useState(false);
  const [exportOpen, setExportOpen] = useState(false);
  const [exportMode, setExportMode] = useState<'EXPORT' | 'DEPLOY'>('EXPORT');
  const [exportPreview, setExportPreview] = useState<DashboardStudioExport | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    dashboardApi
      .catalog()
      .then((result) => {
        setCatalog(result);
        const selected = result.dashboards.find(
          (item) => item.dashboard_id === selectedId,
        );
        if (selected && selected.state !== 'ELIGIBLE') {
          setResearchEntry(selected);
          setPack(null);
          setSelectedId('');
          setRunId('');
          setError('');
        }
      })
      .catch(() => setError('Dashboard catalog is unavailable.'));
  }, [selectedId]);

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
    if (entry.state !== 'ELIGIBLE') {
      setResearchEntry(entry);
      setPack(null);
      setSelectedId('');
      return;
    }
    setResearchEntry(null);
    setPack(null);
    setSelectedId(entry.dashboard_id);
    setRunId('');
    setPerspective('NOC');
    setSelectedPanel(null);
    setTokens({});
    setExportOpen(false);
  };

  const openExportPreview = async () => {
    if (!pack) return;
    setBusy(true);
    setExportOpen(true);
    setExportMode('EXPORT');
    try {
      const result = await dashboardApi.export(pack.dashboard_id, runId || undefined);
      setExportPreview(result);
    } catch {
      setError('Validated export preview is unavailable.');
      setExportPreview(null);
    } finally {
      setBusy(false);
    }
  };

  const downloadExport = () => {
    if (!pack || !exportPreview?.validation.valid) return;
    const blob = new Blob([JSON.stringify(exportPreview.definition, null, 2)], {
      type: 'application/json',
    });
    const href = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = href;
    anchor.download = `${pack.dashboard_id}.dashboard-studio.json`;
    anchor.click();
    URL.revokeObjectURL(href);
  };

  if (researchEntry) {
    return (
      <ResearchRequiredState
        entry={researchEntry}
        entries={catalog?.dashboards ?? []}
        onBack={() => setResearchEntry(null)}
        onSelect={(dashboardId) => {
          const entry = catalog?.dashboards.find((item) => item.dashboard_id === dashboardId);
          if (entry) selectDashboard(entry);
        }}
      />
    );
  }

  if (!pack) {
    const references =
      catalog?.dashboards.filter(
        (item) =>
          item.state === 'ELIGIBLE' &&
          item.dashboard_id.startsWith('scenario-c100-'),
      ) ?? [];
    const readyCount =
      catalog?.dashboards.filter((item) => item.dashboard_maturity === 'DASHBOARD_READY')
        .length ?? 0;
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
            <strong>{readyCount}</strong>
            <span>dashboard ready</span>
            <strong>{catalog?.eligible_count ?? '—'}</strong>
            <span>eligible scenarios</span>
          </div>
        </header>

        <section className="dashboard-reference-rail" aria-label="Golden Cisco references">
          <div>
            <span>Validated scenario references</span>
            <strong>Five Cisco Golden scenarios</strong>
            <small>Scenario and dashboard maturity remain independent.</small>
          </div>
          {references.map((entry) => (
            <button type="button" key={entry.dashboard_id} onClick={() => selectDashboard(entry)}>
              <code>{entry.scenario_id}</code>
              <span>{entry.title}</span>
              <Maturity value={entry.dashboard_maturity} />
            </button>
          ))}
        </section>

        <section className="dashboard-recipe-strip" aria-label="Dashboard recipe chain">
          {[
            ['Scenario metadata', 'Intent · entities · findings'],
            ['Verified contracts', 'Native · Splunk · NetSpout'],
            ['Dashboard recipe', 'Registry-selected panels'],
            ['Validation chain', 'Required before Dashboard Ready'],
          ].map(([title, detail], index) => (
            <div key={title}>
              <span>{index + 1}</span>
              <p><strong>{title}</strong><small>{detail}</small></p>
              {index < 3 && <ChevronRight aria-hidden="true" />}
            </div>
          ))}
        </section>

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
          <div className="dashboard-layout-toggle" aria-label="Gallery layout">
            <button type="button" className={galleryLayout === 'CARD' ? 'is-active' : ''} onClick={() => setGalleryLayout('CARD')} aria-label="Card view"><Grid2X2 /></button>
            <button type="button" className={galleryLayout === 'TABLE' ? 'is-active' : ''} onClick={() => setGalleryLayout('TABLE')} aria-label="Table view"><List /></button>
          </div>
        </div>

        {error && <div className="dashboard-notice dashboard-notice--error">{error}</div>}
        {galleryLayout === 'CARD' ? <div className="dashboard-gallery__grid">
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
                onClick={() => selectDashboard(entry)}
              >
                {entry.state === 'ELIGIBLE' ? 'Open dashboard' : 'View missing evidence'}
              </button>
            </article>
          ))}
        </div> : (
          <div className="dashboard-compact-table" role="table" aria-label="Dashboard catalog">
            <div role="row"><span>Scenario</span><span>Domain</span><span>Scenario maturity</span><span>Dashboard maturity</span><span>Sources</span><span>Action</span></div>
            {entries.map((entry) => (
              <div role="row" key={entry.dashboard_id}>
                <span><code>{entry.scenario_id}</code><strong>{entry.title}</strong></span>
                <span>{entry.industry_id ?? entry.domain}</span>
                <span>{entry.scenario_maturity}</span>
                <Maturity value={entry.dashboard_maturity} />
                <span>{entry.source_ids.length}</span>
                <button type="button" onClick={() => selectDashboard(entry)}>
                  {entry.state === 'ELIGIBLE' ? 'Open' : 'Evidence gaps'}
                </button>
              </div>
            ))}
          </div>
        )}
      </section>
    );
  }

  const visiblePanels = pack.panels.filter((item) => item.perspective === perspective);
  const selectedEligibility = catalog?.dashboards.find(
    (item) => item.dashboard_id === pack.dashboard_id,
  );
  const eligibleEntries =
    catalog?.dashboards.filter((item) => item.state === 'ELIGIBLE') ?? [];
  const nocPanels = pack.panels.filter((item) => item.perspective === 'NOC').slice(0, 6);
  const validation = validationStages(pack);
  const latestEvidence = pack.validation_evidence.at(-1) as
    | {
        source_coverage_validated?: boolean | null;
        source_observations?: Record<string, boolean>;
        failures?: string[];
      }
    | undefined;
  const missingSources = Object.entries(latestEvidence?.source_observations ?? {})
    .filter(([, observed]) => !observed)
    .map(([sourceId]) => sourceId);

  return (
    <section
      className={`dashboard-studio ${wallboard ? 'dashboard-studio--wallboard' : ''}`}
      data-testid="dashboard-studio"
    >
      <header className="dashboard-studio__header">
        <button type="button" className="dashboard-back" onClick={() => {
          setSelectedId('');
          setPack(null);
          setRunId('');
        }}>
          <ArrowLeft /> Gallery
        </button>
        <div className="dashboard-studio__identity">
          <span className="dashboard-eyebrow">Dashboards / {pack.scenario_id} / {perspective}</span>
          <h2>{pack.title}</h2>
          <span>{pack.domain} · {pack.category} · {pack.topology_ref}</span>
        </div>
        <label className="dashboard-scenario-switcher">
          Scenario dashboard
          <select
            value={pack.dashboard_id}
            aria-label="Switch scenario dashboard"
            onChange={(event) => {
              const entry = eligibleEntries.find((item) => item.dashboard_id === event.target.value);
              if (entry) selectDashboard(entry);
            }}
          >
            {eligibleEntries.map((entry) => (
              <option value={entry.dashboard_id} key={entry.dashboard_id}>
                {entry.scenario_id} · {entry.title}
              </option>
            ))}
          </select>
        </label>
        <label className="dashboard-run">
          Run context
          <input
            value={runId}
            placeholder="Select or enter run ID"
            onChange={(event) => setRunId(event.target.value.replace(/[^A-Za-z0-9_.:-]/g, ''))}
          />
        </label>
        <Maturity value={pack.maturity} />
        <button type="button" onClick={() => {
          setTokens({});
          setSelectedPanel(null);
          setPerspective('NOC');
        }}>Reset</button>
        <button type="button" onClick={() => setWallboard((value) => !value)}>
          {wallboard ? <X /> : <Maximize2 />} {wallboard ? 'Exit wallboard' : 'NOC wallboard'}
        </button>
        <button type="button" onClick={openExportPreview} disabled={busy}>
          <Download /> Export / Deploy
        </button>
      </header>

      {!runId && (
        <div className="dashboard-notice">
          Preview mode — select a run to generate executable, run-scoped SPL. No telemetry
          values are inferred.
        </div>
      )}
      {error && <div className="dashboard-notice dashboard-notice--error">{error}</div>}
      {latestEvidence?.source_coverage_validated === false && (
        <div className="dashboard-notice dashboard-notice--error" data-testid="dashboard-source-limitation">
          Required source observation is incomplete
          {missingSources.length > 0 ? `: ${missingSources.join(', ')}` : ''}. Dependent
          panels cannot be visually validated or promoted to Dashboard Ready.
        </div>
      )}

      {!wallboard && (
        <div className="dashboard-subnav">
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
              <button type="button" onClick={() => setTokens({})}>Clear filters</button>
            )}
            {Object.keys(tokens).length === 0 && <em>Full scenario</em>}
          </div>
          <span className="dashboard-context-label">CIM · {pack.cim_status}</span>
        </div>
      )}

      <div className="dashboard-kpis">
        {nocPanels.map((panel, index) => (
          <Kpi
            key={panel.panel_id}
            label={panel.title}
            value={
              panel.executable
                ? pack.maturity === 'DASHBOARD_READY'
                  ? 'VALIDATED'
                  : runId
                    ? 'DATA VALIDATED'
                    : 'RUN REQUIRED'
                : 'CONTRACT DERIVED'
            }
            detail={panel.visualization_id}
            tone={index === 0 ? 'warning' : panel.executable ? 'info' : 'healthy'}
            icon={index === 0 ? <Activity /> : index === 1 ? <Network /> : <ShieldCheck />}
            onClick={() => {
              setSelectedPanel(panel);
              setInspectorTab('Data');
              setTokens((current) => ({ ...current, kpi: panel.recipe_id }));
            }}
          />
        ))}
      </div>

      {perspective === 'EVIDENCE' && !wallboard && (
        <ValidationChain stages={validation} />
      )}

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
          <span>{perspective === 'NOC' ? 'Operational context' : perspective === 'ENGINEER' ? 'Investigation scope' : 'Evidence position'}</span>
          <strong>{selectedEligibility?.title ?? pack.scenario_id}</strong>
          <p>{pack.description}</p>
          <dl>
            <div><dt>Sources</dt><dd>{pack.telemetry_manifest.length}</dd></div>
            <div><dt>Investigations</dt><dd>{pack.investigation_recipe_ids.length}</dd></div>
            <div><dt>CIM</dt><dd>{pack.cim_status}</dd></div>
            <div><dt>Dashboard</dt><dd>{pack.maturity.replaceAll('_', ' ')}</dd></div>
          </dl>
        </div>
      </div>

      {!wallboard && (
        <>
          <div className="dashboard-panels">
            {visiblePanels.map((panel) => (
              <PanelCard
                key={panel.panel_id}
                panel={panel}
                runId={runId}
                pack={pack}
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
          visualizations={catalog?.visualizations ?? []}
          tokens={tokens}
          tab={inspectorTab}
          onTab={setInspectorTab}
          onClose={() => setSelectedPanel(null)}
        />
      )}
      {exportOpen && (
        <DashboardExportDialog
          pack={pack}
          preview={exportPreview}
          mode={exportMode}
          busy={busy}
          stages={validation}
          onMode={setExportMode}
          onDownload={downloadExport}
          onClose={() => setExportOpen(false)}
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

function Kpi({
  label,
  value,
  detail,
  tone,
  icon,
  onClick,
}: {
  label: string;
  value: string;
  detail: string;
  tone: 'info' | 'warning' | 'healthy';
  icon: ReactNode;
  onClick: () => void;
}) {
  return (
    <button type="button" className={`dashboard-kpi dashboard-kpi--${tone}`} onClick={onClick}>
      {icon}<span>{label}</span><strong>{value}</strong><small>{detail}</small>
    </button>
  );
}

type ValidationState = 'PASSED' | 'PENDING' | 'FAILED' | 'NOT APPLICABLE';

const VALIDATION_LABELS = [
  'Generated',
  'SPL Checked',
  'Search Executed',
  'Fields Verified',
  'Data Shape Verified',
  'Visualization Rendered',
  'Drilldowns Tested',
  'Dashboard Ready',
] as const;

function validationStages(pack: DashboardPack): ValidationState[] {
  const rank = [
    'NOT_STARTED',
    'GENERATED',
    'SPL_VALIDATED',
    'DATA_VALIDATED',
    'VISUALLY_VALIDATED',
    'DASHBOARD_READY',
  ].indexOf(pack.maturity);
  if (pack.maturity === 'VALIDATION_FAILED' || pack.maturity === 'DEPENDENCY_BLOCKED') {
    return ['PASSED', 'FAILED', 'FAILED', 'PENDING', 'PENDING', 'PENDING', 'PENDING', 'PENDING'];
  }
  return [
    rank >= 1 ? 'PASSED' : 'PENDING',
    rank >= 2 ? 'PASSED' : 'PENDING',
    rank >= 2 ? 'PASSED' : 'PENDING',
    rank >= 3 ? 'PASSED' : 'PENDING',
    rank >= 3 ? 'PASSED' : 'PENDING',
    rank >= 4 ? 'PASSED' : 'PENDING',
    rank >= 4 ? 'PASSED' : 'PENDING',
    rank >= 5 ? 'PASSED' : 'PENDING',
  ];
}

function ValidationChain({ stages }: { stages: ValidationState[] }) {
  return (
    <section className="dashboard-validation" aria-label="Dashboard validation chain">
      <header>
        <div><span>Dashboard validation</span><strong>Generated to Dashboard Ready</strong></div>
        <small>{stages.filter((item) => item === 'PASSED').length} of 8 passed</small>
      </header>
      <div className="dashboard-validation__steps">
        {VALIDATION_LABELS.map((label, index) => (
          <div className={`dashboard-validation__step is-${stages[index].toLowerCase().replaceAll(' ', '-')}`} key={label}>
            <i>{stages[index] === 'PASSED' ? <CheckCircle2 /> : index + 1}</i>
            <span><strong>{label}</strong><small>{stages[index]}</small></span>
            {index < VALIDATION_LABELS.length - 1 && <b />}
          </div>
        ))}
      </div>
    </section>
  );
}

function ResearchRequiredState({
  entry,
  entries,
  onBack,
  onSelect,
}: {
  entry: DashboardEligibility;
  entries: DashboardEligibility[];
  onBack: () => void;
  onSelect: (dashboardId: string) => void;
}) {
  return (
    <section className="dashboard-studio dashboard-studio--research" data-testid="dashboard-research-required">
      <header className="dashboard-studio__header">
        <button type="button" onClick={onBack}><ArrowLeft /> Gallery</button>
        <div className="dashboard-studio__identity">
          <span className="dashboard-eyebrow">Dashboards / {entry.scenario_id}</span>
          <h2>{entry.title}</h2>
        </div>
        <label className="dashboard-scenario-switcher">
          Scenario dashboard
          <select value={entry.dashboard_id} onChange={(event) => onSelect(event.target.value)}>
            {entries.map((item) => <option value={item.dashboard_id} key={item.dashboard_id}>{item.scenario_id} · {item.title}</option>)}
          </select>
        </label>
        <Maturity value="RESEARCH_REQUIRED" />
      </header>
      <main className="dashboard-research-state">
        <AlertTriangle aria-hidden="true" />
        <div>
          <span>Execution and dashboard blocked</span>
          <h2>Evidence is incomplete</h2>
          <p>{entry.reasons.join(' ')}</p>
          <ul>
            <li>Scenario maturity: {entry.scenario_maturity}</li>
            <li>Source Contracts: {entry.source_ids.length ? entry.source_ids.join(', ') : 'NOT VERIFIED'}</li>
            <li>Investigation Pack: {entry.investigation_recipe_ids.length ? 'REFERENCED' : 'NOT ESTABLISHED'}</li>
            <li>CIM: NOT ESTABLISHED</li>
          </ul>
          <strong>No fallback event, SPL, vendor field, TA, CIM mapping, or runnable dashboard is generated.</strong>
          <button type="button" onClick={onBack}>Back to Gallery</button>
        </div>
      </main>
    </section>
  );
}

function DashboardExportDialog({
  pack,
  preview,
  mode,
  busy,
  stages,
  onMode,
  onDownload,
  onClose,
}: {
  pack: DashboardPack;
  preview: DashboardStudioExport | null;
  mode: 'EXPORT' | 'DEPLOY';
  busy: boolean;
  stages: ValidationState[];
  onMode: (mode: 'EXPORT' | 'DEPLOY') => void;
  onDownload: () => void;
  onClose: () => void;
}) {
  return (
    <div className="dashboard-modal-backdrop">
      <section className="dashboard-export-dialog" role="dialog" aria-label="Dashboard export and deployment preview">
        <header>
          <div><span>Export / deployment preview</span><strong>{pack.scenario_id} · {pack.title}</strong></div>
          <button type="button" onClick={onClose} aria-label="Close export preview"><X /></button>
        </header>
        <nav>
          <button type="button" className={mode === 'EXPORT' ? 'is-active' : ''} onClick={() => onMode('EXPORT')}>Export artifact</button>
          <button type="button" className={mode === 'DEPLOY' ? 'is-active' : ''} onClick={() => onMode('DEPLOY')}>Deploy to Splunk</button>
        </nav>
        <ValidationChain stages={stages} />
        {mode === 'EXPORT' ? (
          <div className="dashboard-export-dialog__content">
            <dl>
              <div><dt>Format</dt><dd>{preview?.format ?? 'Dashboard Studio JSON'}</dd></div>
              <div><dt>Schema</dt><dd>{preview?.validation.valid ? 'VALID' : busy ? 'CHECKING' : 'NOT VERIFIED'}</dd></div>
              <div><dt>Dependencies</dt><dd>{pack.panels.some((item) => item.dependency_state.startsWith('FALLBACK')) ? 'SUPPORTED FALLBACK ACTIVE' : 'NATIVE / DOCUMENTED'}</dd></div>
              <div><dt>Scenario/run</dt><dd>{pack.scenario_id} · {pack.run_id ?? 'DESIGN PREVIEW'}</dd></div>
            </dl>
            <div className="dashboard-export-warning">
              <ShieldCheck /><p>Export creates a validated artifact. It is not deployment evidence and cannot overwrite a Splunk dashboard.</p>
            </div>
            <footer><button type="button" onClick={onClose}>Cancel</button><button type="button" onClick={onDownload} disabled={!preview?.validation.valid || busy}>Download JSON</button></footer>
          </div>
        ) : (
          <div className="dashboard-export-dialog__content">
            <dl>
              <div><dt>Target</dt><dd>{preview?.deployment.target ?? 'Configured authorized lab only'}</dd></div>
              <div><dt>Status</dt><dd>{preview?.deployment.deployment_status ?? 'PREVIEW ONLY'}</dd></div>
              <div><dt>Overwrite</dt><dd>{preview?.deployment.overwrite_allowed ? 'ALLOWED' : 'PROHIBITED'}</dd></div>
              <div><dt>Permissions</dt><dd>{preview?.deployment.required_permissions.join(', ') || 'NOT AUTHORIZED'}</dd></div>
            </dl>
            <div className="dashboard-export-warning">
              <AlertTriangle /><p>No deployment request will be sent. Connection, authorization, compatibility, dependency, and conflict checks are required.</p>
            </div>
            <footer><button type="button" onClick={onClose}>Cancel</button><button type="button" disabled>Deploy unavailable</button></footer>
          </div>
        )}
      </section>
    </div>
  );
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
  const compactLabel = (value: string, limit = 12) =>
    value.length > limit ? `${value.slice(0, limit - 1)}…` : value;
  const nodes = pack.entity_graph.nodes;
  const topologyPanel = pack.panels.find((item) => item.recipe_id === 'dashboard-topology-health');
  const positioned = nodes.map((node, index) => ({
    node,
    id: node.node_id ?? node.entity_id ?? `entity-${index}`,
    x: 100 + (index % 4) * 190,
    y: 90 + Math.floor(index / 4) * 145,
  }));
  const byId = new Map(positioned.map((item) => [item.id, item]));
  return (
    <div className="dashboard-topology" data-testid="dashboard-topology">
      <div className="dashboard-panel__heading">
        <div><span>Primary topology</span><small>{topologyPanel?.visualization_id ?? 'netspout-native-network-graph'} · shared scenario graph</small></div>
        <Maturity value={topologyPanel?.dependency_state ?? 'VERIFIED'} />
      </div>
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
                {compactLabel(relationship.relationship_type, 9)}
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
            <title>{node.label ?? id}</title>
            <rect x="-55" y="-28" width="110" height="56" rx="8" />
            <text y="-3">{compactLabel(node.label ?? id)}</text>
            <text className="dashboard-topology__role" y="15">
              {compactLabel(node.role ?? node.entity_type ?? 'ENTITY', 16)}
            </text>
          </g>
        ))}
      </svg>
      <div className="dashboard-topology__decision">
        <span>Selection</span><strong>{topologyPanel?.requested_visualization_id ?? 'Native Network Graph'}</strong>
        <span>Supported result</span><strong>{topologyPanel?.visualization_id ?? 'Native Network Graph'}</strong>
        <span>Compatibility</span><strong>{topologyPanel?.dependency_state ?? 'VERIFIED'}</strong>
      </div>
    </div>
  );
}

function PanelCard({
  panel,
  runId,
  pack,
  onInspect,
  onDrilldown,
}: {
  panel: DashboardPanel;
  runId: string;
  pack: DashboardPack;
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
      {panel.dependency_state.startsWith('FALLBACK') && (
        <div className="dashboard-panel__dependency">
          Requested {panel.requested_visualization_id} is {panel.dependency_state.replace('FALLBACK:', '')}. Using supported {panel.visualization_id}.
        </div>
      )}
      <div className="dashboard-panel__state">
        {runId && panel.executable ? (
          <><CheckCircle2 /> Run-scoped SPL · {pack.maturity.replaceAll('_', ' ')}</>
        ) : panel.executable ? (
          <><AlertTriangle /> Query unavailable</>
        ) : (
          <><Network /> Contract-derived context · no measured value claimed</>
        )}
      </div>
      <div className="dashboard-panel__drilldowns">
        {panel.drilldowns.map((item) => {
          const supported =
            pack.observed_fields.includes(item.field) ||
            panel.required_fields.includes(item.field) ||
            panel.optional_fields.includes(item.field) ||
            ['entity', 'relationship', 'investigation', 'business_capability'].includes(item.token);
          return (
            <button
              type="button"
              key={`${item.token}-${item.field}`}
              disabled={!supported}
              title={supported ? item.semantics : `${item.field} is not verified for this run`}
              onClick={() => onDrilldown(item.token, item.field)}
            >
              {item.token} → {supported ? item.field : 'NOT VERIFIED'}
            </button>
          );
        })}
      </div>
    </article>
  );
}

function AdvancedInspector({
  panel,
  pack,
  visualizations,
  tokens,
  tab,
  onTab,
  onClose,
}: {
  panel: DashboardPanel;
  pack: DashboardPack;
  visualizations: Array<Record<string, unknown>>;
  tokens: Record<string, string>;
  tab: (typeof INSPECTOR_TABS)[number];
  onTab: (value: (typeof INSPECTOR_TABS)[number]) => void;
  onClose: () => void;
}) {
  const latestEvidence = pack.validation_evidence.at(-1) as
    | {
        recorded_at?: string;
        spl_validated?: boolean;
        data_validated?: boolean;
        visually_validated?: boolean;
        export_validated?: boolean;
        failures?: string[];
        evidence_refs?: string[];
      }
    | undefined;
  const unavailableVisualizations = visualizations.filter(
    (item) => item.compatibility === 'NOT_VERIFIED' || item.compatibility === 'INCOMPATIBLE',
  );
  const content: Record<(typeof INSPECTOR_TABS)[number], ReactNode> = {
    Overview: <><h4>{panel.title}</h4><p>{panel.purpose}</p><code>{panel.recipe_id}</code></>,
    Visualization: <dl><div><dt>Requested</dt><dd>{panel.requested_visualization_id}</dd></div><div><dt>Selected / fallback</dt><dd>{panel.visualization_id}</dd></div><div><dt>Compatibility</dt><dd>{panel.dependency_state}</dd></div><div><dt>Required shape</dt><dd>{Object.keys(panel.expected_shape).join(', ') || 'ENTITY GRAPH'}</dd></div></dl>,
    Data: <><p>Expected result shape</p><Json value={panel.expected_shape} /><p>Telemetry manifest</p><Json value={pack.telemetry_manifest} /></>,
    SPL: panel.query ? <pre>{panel.query}</pre> : <p>NOT GENERATED — select a run context.</p>,
    Fields: <><p>Required: {panel.required_fields.join(', ') || 'NONE'}</p><p>Optional: {panel.optional_fields.join(', ') || 'NONE'}</p><p>Observed: {pack.observed_fields.join(', ') || 'NOT VERIFIED'}</p></>,
    CIM: <p>{pack.cim_status === 'NOT_ESTABLISHED' ? 'NOT ESTABLISHED — no CIM-dependent functionality is claimed.' : pack.cim_status}</p>,
    Tokens: <><p>Active dashboard filters</p><Json value={tokens} /><p>Declared mappings</p><Json value={panel.drilldowns} /></>,
    Dependencies: <><dl><div><dt>Requested</dt><dd>{panel.requested_visualization_id}</dd></div><div><dt>State</dt><dd>{panel.dependency_state}</dd></div><div><dt>Supported result</dt><dd>{panel.visualization_id}</dd></div></dl><h4>Unavailable optional visualizations</h4>{unavailableVisualizations.map((item) => <p className="dashboard-dependency-state" key={String(item.visualization_id)}><strong>{String(item.display_name ?? item.visualization_id)}</strong><span>{String(item.compatibility).replaceAll('_', ' ')} · fallback {String(item.fallback_id ?? 'NOT AVAILABLE')}</span></p>)}</>,
    Validation: <><p>Dashboard maturity: {pack.maturity}</p><ValidationChain stages={validationStages(pack)} /><Json value={latestEvidence ?? { state: 'NOT VERIFIED' }} /></>,
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
