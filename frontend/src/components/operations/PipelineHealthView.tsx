import { useEffect, useMemo, useState } from 'react';
import { RefreshCw } from 'lucide-react';
import { fetchJson } from '../../lib/api';
import {
  Panel,
  StatePanel,
  StatusBadge,
  TechnicalTable,
  type TableColumn,
} from '../ui/SystemPrimitives';

interface PipelineDetail {
  state?: string;
  type?: string;
  host?: string;
  port?: number;
  captured_count?: number;
  dispatched_count?: number;
}

interface HealthResponse {
  pipelines?: Record<string, PipelineDetail>;
}

interface PipelineRow {
  id: string;
  detail: PipelineDetail;
}

export function PipelineHealthView() {
  const [reloadKey, setReloadKey] = useState(0);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;

    fetchJson<HealthResponse>('/api/health/pipelines')
      .then((response) => {
        if (!active) return;
        setHealth(response);
        setError(null);
        setLoading(false);
      })
      .catch((reason: unknown) => {
        if (!active) return;
        setError(reason instanceof Error ? reason.message : 'Unknown runtime error');
        setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [reloadKey]);

  const rows = useMemo<PipelineRow[]>(
    () =>
      Object.entries(health?.pipelines ?? {}).map(([id, detail]) => ({
        id,
        detail,
      })),
    [health],
  );

  const columns: TableColumn<PipelineRow>[] = [
    {
      key: 'pipeline',
      header: 'Pipeline',
      render: (row) => (
        <div>
          <strong>{row.id === 'otlp' ? 'OTel Collector / OTLP' : row.id.toUpperCase()}</strong>
          <span className="table-subtext">{row.detail.type ?? 'Type not reported'}</span>
        </div>
      ),
    },
    {
      key: 'runtime',
      header: 'Runtime',
      render: (row) => <StatusBadge status={row.detail.state ?? 'NOT AVAILABLE'} />,
    },
    {
      key: 'endpoint',
      header: 'Endpoint',
      render: (row) =>
        row.detail.host && row.detail.port ? (
          <code>
            {row.detail.host}:{row.detail.port}
          </code>
        ) : (
          <span className="muted-value">NOT REPORTED</span>
        ),
    },
    {
      key: 'receiver',
      header: 'Receiver observed',
      render: (row) =>
        typeof row.detail.captured_count === 'number' ? (
          row.detail.captured_count
        ) : (
          <span className="muted-value">N/A</span>
        ),
    },
    {
      key: 'splunk',
      header: 'Splunk observed',
      render: () => <span className="muted-value">NOT MEASURED</span>,
    },
  ];

  const refresh = () => {
    setLoading(true);
    setReloadKey((value) => value + 1);
  };

  return (
    <div className="workspace-stack">
      <Panel
        title="Pipeline Health"
        description="Runtime states are shown exactly as reported. Process availability is not treated as receipt or Splunk observation."
        actions={
          <button type="button" className="button button--quiet" onClick={refresh}>
            <RefreshCw /> Refresh
          </button>
        }
      >
        {loading && <StatePanel kind="loading" message="Querying pipeline runtime evidence." />}
        {!loading && error && (
          <StatePanel
            kind="error"
            title="Pipeline evidence unavailable"
            message={`The backend request failed: ${error}`}
          />
        )}
        {!loading && !error && rows.some((row) => row.detail.state === 'DEGRADED') && (
          <StatePanel
            kind="degraded"
            message="At least one pipeline explicitly reports a degraded state."
          />
        )}
        {!loading && !error && (
          <TechnicalTable
            columns={columns}
            rows={rows}
            getRowKey={(row) => row.id}
            emptyMessage="No pipeline records were returned by the backend."
          />
        )}
      </Panel>
      <StatePanel
        kind="unavailable"
        title="Splunk observation is separate"
        message="This endpoint does not provide search-backed Splunk observation. Those cells remain NOT MEASURED instead of inheriting generated or dispatched counts."
      />
    </div>
  );
}
