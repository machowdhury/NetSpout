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

type ComponentState = 'RUNNING' | 'REACHABLE' | 'READY' | 'DEGRADED' | 'FAILED' | 'NOT_CONFIGURED';

interface HealthResponse {
  components: Array<{
    component: string;
    state: ComponentState;
    detail: string;
    channel: string | null;
  }>;
}

interface PipelineRow {
  component: string;
  state: ComponentState;
  detail: string;
  channel: string | null;
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
    () => health?.components ?? [],
    [health],
  );

  const columns: TableColumn<PipelineRow>[] = [
    {
      key: 'component',
      header: 'Component',
      render: (row) => (
        <div>
          <strong>{row.component.replaceAll('_', ' ')}</strong>
          <span className="table-subtext">{row.channel ?? 'Shared destination service'}</span>
        </div>
      ),
    },
    {
      key: 'runtime',
      header: 'Runtime',
      render: (row) => <StatusBadge status={row.state} />,
    },
    {
      key: 'channel',
      header: 'Protocol channel',
      render: (row) => row.channel ?? <span className="muted-value">DESTINATION</span>,
    },
    {
      key: 'detail',
      header: 'Diagnostic',
      render: (row) => <span>{row.detail}</span>,
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
        {!loading && !error && rows.some((row) => ['DEGRADED', 'FAILED'].includes(row.state)) && (
          <StatePanel
            kind="degraded"
            message="At least one pipeline explicitly reports a degraded state."
          />
        )}
        {!loading && !error && (
          <TechnicalTable
            columns={columns}
            rows={rows}
            getRowKey={(row) => `${row.component}-${row.channel ?? 'shared'}`}
            emptyMessage="No pipeline records were returned by the backend."
          />
        )}
      </Panel>
      <StatePanel
        kind="unavailable"
        title="Health is component-scoped"
        message="Runtime readiness and reachability do not imply generated, receiver, collector, or Splunk observation counts. Run evidence reports those separately."
      />
    </div>
  );
}
