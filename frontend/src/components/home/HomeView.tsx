import { useEffect, useMemo, useState } from 'react';
import {
  Activity,
  ArrowRight,
  FlaskConical,
  Layers3,
  Link2,
  Network,
  Search,
  ShieldCheck,
} from 'lucide-react';
import { DOMAINS, type AppRoute, type DomainId, type ExperienceMode } from '../../app/navigation';
import { fetchJson } from '../../lib/api';
import {
  Panel,
  ProvenanceBadge,
  StatePanel,
  StatusBadge,
  TechnicalTable,
  type TableColumn,
} from '../ui/SystemPrimitives';

interface ServiceHealth {
  status?: string;
  service?: string;
}

interface PipelineRecord {
  state?: string;
  type?: string;
  host?: string;
  port?: number;
  captured_count?: number;
  dispatched_count?: number;
}

interface PipelineHealth {
  status?: string;
  pipelines?: Record<string, PipelineRecord>;
}

interface RuntimeSnapshot {
  state: 'loading' | 'ready' | 'degraded' | 'error';
  backend?: ServiceHealth;
  pipelines?: PipelineHealth;
  error?: string;
}

interface PipelineRow {
  id: string;
  name: string;
  record: PipelineRecord;
}

const WORKFLOW = [
  { label: 'Choose', detail: 'Select a scenario, source, or event family.' },
  { label: 'Run', detail: 'Execute through the supported runtime path.' },
  { label: 'Observe', detail: 'Inspect evidence at each measured stage.' },
  { label: 'Correlate', detail: 'Relate state, behavior, and telemetry.' },
  { label: 'Investigate', detail: 'Confirm observations in Splunk.' },
];

export function HomeView({
  domain,
  mode,
  onNavigate,
}: {
  domain: DomainId;
  mode: ExperienceMode;
  onNavigate: (route: AppRoute) => void;
}) {
  const [reloadKey, setReloadKey] = useState(0);
  const [runtime, setRuntime] = useState<RuntimeSnapshot>({ state: 'loading' });

  useEffect(() => {
    let active = true;

    Promise.allSettled([
      fetchJson<ServiceHealth>('/health'),
      fetchJson<PipelineHealth>('/api/health/pipelines'),
    ]).then(([backendResult, pipelineResult]) => {
      if (!active) return;

      const backend =
        backendResult.status === 'fulfilled' ? backendResult.value : undefined;
      const pipelines =
        pipelineResult.status === 'fulfilled' ? pipelineResult.value : undefined;

      if (!backend && !pipelines) {
        setRuntime({
          state: 'error',
          error: 'The NetSpout backend did not return runtime evidence.',
        });
        return;
      }

      setRuntime({
        state: backend && pipelines ? 'ready' : 'degraded',
        backend,
        pipelines,
      });
    });

    return () => {
      active = false;
    };
  }, [reloadKey]);

  const pipelineRows = useMemo<PipelineRow[]>(
    () =>
      Object.entries(runtime.pipelines?.pipelines ?? {}).map(([id, record]) => ({
        id,
        name: id === 'otlp' ? 'OTel Collector / OTLP' : id.toUpperCase(),
        record,
      })),
    [runtime.pipelines],
  );

  const pipelineColumns: TableColumn<PipelineRow>[] = [
    {
      key: 'pipeline',
      header: 'Pipeline',
      render: (row) => (
        <div>
          <strong>{row.name}</strong>
          <span className="table-subtext">{row.record.type ?? 'Type not reported'}</span>
        </div>
      ),
    },
    {
      key: 'runtime',
      header: 'Runtime',
      render: (row) => <StatusBadge status={row.record.state ?? 'NOT AVAILABLE'} />,
    },
    {
      key: 'endpoint',
      header: 'Endpoint',
      render: (row) =>
        row.record.host && row.record.port ? (
          <code>
            {row.record.host}:{row.record.port}
          </code>
        ) : (
          <span className="muted-value">NOT REPORTED</span>
        ),
    },
    {
      key: 'evidence',
      header: 'Last evidence',
      render: (row) => {
        const observed = row.record.captured_count ?? row.record.dispatched_count;
        return typeof observed === 'number' && observed > 0 ? (
          <span>{observed} runtime observations</span>
        ) : (
          <span className="muted-value">NO EVIDENCE</span>
        );
      },
    },
  ];

  const activeDomain = DOMAINS.find((item) => item.id === domain) ?? DOMAINS[0];

  return (
    <div className="workspace-stack">
      <section className="home-hero">
        <div className="home-hero__content">
          <div className="home-hero__kicker">
            <FlaskConical />
            Unified Enterprise Telemetry Lab
          </div>
          <h2>Simulate the enterprise. Preserve the telemetry contract.</h2>
          <p>
            Simulate enterprise incidents, generate authentic telemetry, correlate what
            happened, and investigate measured evidence in Splunk.
          </p>
          <div className="home-hero__actions">
            <button
              type="button"
              className="button button--primary"
              onClick={() => onNavigate('/generate/scenarios')}
            >
              Choose a scenario <ArrowRight />
            </button>
            <button
              type="button"
              className="button button--secondary"
              onClick={() => onNavigate('/generate/quick')}
            >
              Quick generate
            </button>
          </div>
        </div>
        <div className="home-hero__context">
          <span>Current perspective</span>
          <strong>{activeDomain.label}</strong>
          <StatusBadge status={activeDomain.maturity} />
          <p>{activeDomain.description}</p>
          <div className="home-hero__mode">
            <span>Experience</span>
            <strong>{mode === 'simple' ? 'Simple guidance' : 'Advanced technical detail'}</strong>
          </div>
        </div>
      </section>

      <Panel
        title="Choose → Run → Observe → Correlate → Investigate"
        description="One shared flow across six operational perspectives."
      >
        <ol className="workflow-strip">
          {WORKFLOW.map((step, index) => (
            <li key={step.label}>
              <span className="workflow-strip__number">{String(index + 1).padStart(2, '0')}</span>
              <div>
                <strong>{step.label}</strong>
                <p>{step.detail}</p>
              </div>
            </li>
          ))}
        </ol>
      </Panel>

      <div className="home-grid">
        <Panel
          title="Runtime evidence"
          description="States below come from the current backend response; missing stages remain explicit."
          actions={
            <button
              type="button"
              className="button button--quiet"
              onClick={() => {
                setRuntime({ state: 'loading' });
                setReloadKey((value) => value + 1);
              }}
            >
              Refresh
            </button>
          }
          className="home-grid__runtime"
        >
          {runtime.state === 'loading' && (
            <StatePanel kind="loading" message="Querying backend and pipeline evidence." />
          )}
          {runtime.state === 'error' && (
            <StatePanel
              kind="error"
              message={runtime.error ?? 'Runtime evidence is unavailable.'}
            />
          )}
          {runtime.state === 'degraded' && (
            <StatePanel
              kind="degraded"
              message="Only part of the runtime evidence could be loaded."
            />
          )}
          {runtime.state !== 'loading' && runtime.backend && (
            <div className="runtime-summary">
              <div>
                <span>Backend</span>
                <StatusBadge
                  status={runtime.backend.status === 'ok' ? 'READY' : 'DEGRADED'}
                />
              </div>
              <div>
                <span>Splunk observation</span>
                <StatusBadge status="NOT AVAILABLE" />
              </div>
              <div>
                <span>Detection evaluation</span>
                <StatusBadge status="NOT CONFIGURED" />
              </div>
            </div>
          )}
          {runtime.state !== 'loading' && (
            <TechnicalTable
              columns={pipelineColumns}
              rows={pipelineRows}
              getRowKey={(row) => row.id}
              emptyMessage="The backend returned no pipeline records."
            />
          )}
        </Panel>

        <Panel
          title="Telemetry trust"
          description="Operational claims remain bounded by their source evidence."
          className="home-grid__trust"
        >
          <div className="trust-list">
            <div>
              <Network />
              <span>
                <strong>Native contract</strong>
                What the technology actually produces.
              </span>
              <ProvenanceBadge state="STANDARD VERIFIED" />
            </div>
            <div>
              <Search />
              <span>
                <strong>Splunk contract</strong>
                How Splunk ingests and normalizes it.
              </span>
              <ProvenanceBadge state="SPLUNK VERIFIED" />
            </div>
            <div>
              <ShieldCheck />
              <span>
                <strong>NetSpout contract</strong>
                What the lab models without changing structure.
              </span>
              <ProvenanceBadge state="NETSPOUT SCHEMA" />
            </div>
          </div>
          <button
            type="button"
            className="text-link"
            onClick={() => onNavigate('/catalog/provenance')}
          >
            Open provenance catalog <ArrowRight />
          </button>
        </Panel>
      </div>

      <Panel title="Start a workflow">
        <div className="quick-actions">
          <button type="button" onClick={() => onNavigate('/generate/scenarios')}>
            <Layers3 />
            <span>
              <strong>Run a scenario</strong>
              Complete correlated incident
            </span>
            <ArrowRight />
          </button>
          <button type="button" onClick={() => onNavigate('/generate/quick')}>
            <Activity />
            <span>
              <strong>Generate telemetry</strong>
              Source, event family, or one event
            </span>
            <ArrowRight />
          </button>
          <button type="button" onClick={() => onNavigate('/observe/pipeline-health')}>
            <Link2 />
            <span>
              <strong>Inspect pipelines</strong>
              Runtime and evidence states
            </span>
            <ArrowRight />
          </button>
        </div>
      </Panel>
    </div>
  );
}
