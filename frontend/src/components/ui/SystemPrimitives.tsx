import React from 'react';
import {
  AlertTriangle,
  CircleDashed,
  LoaderCircle,
  OctagonX,
  SearchX,
} from 'lucide-react';

export type RuntimeStatus =
  | 'STARTING'
  | 'READY'
  | 'LISTENING'
  | 'RECEIVING'
  | 'STREAMING'
  | 'CONFIGURED'
  | 'DEGRADED'
  | 'FAILED'
  | 'STOPPED'
  | 'NOT CONFIGURED'
  | 'NOT AVAILABLE'
  | 'PLANNED'
  | 'RESEARCH REQUIRED'
  | 'UNSUPPORTED'
  | string;

const statusTone: Record<string, string> = {
  READY: 'status-badge--success',
  LISTENING: 'status-badge--success',
  RECEIVING: 'status-badge--success',
  STREAMING: 'status-badge--success',
  AVAILABLE: 'status-badge--success',
  CONFIGURED: 'status-badge--info',
  BETA: 'status-badge--info',
  PARTIAL: 'status-badge--warning',
  STARTING: 'status-badge--warning',
  DEGRADED: 'status-badge--warning',
  PLANNED: 'status-badge--neutral',
  INITIALIZED: 'status-badge--neutral',
  STOPPED: 'status-badge--neutral',
  'NOT CONFIGURED': 'status-badge--neutral',
  'NOT AVAILABLE': 'status-badge--neutral',
  'RESEARCH REQUIRED': 'status-badge--research',
  UNSUPPORTED: 'status-badge--danger',
  FAILED: 'status-badge--danger',
  ERROR: 'status-badge--danger',
};

export function StatusBadge({ status }: { status: RuntimeStatus }) {
  const normalized = status?.toUpperCase() || 'NOT AVAILABLE';
  return (
    <span className={`status-badge ${statusTone[normalized] ?? 'status-badge--neutral'}`}>
      {normalized}
    </span>
  );
}

export type ProvenanceState =
  | 'VENDOR VERIFIED'
  | 'STANDARD VERIFIED'
  | 'SPLUNK VERIFIED'
  | 'DATASET VERIFIED'
  | 'NETSPOUT SCHEMA'
  | 'MODELED VALUE'
  | 'RESEARCH REQUIRED'
  | 'UNSUPPORTED';

export function ProvenanceBadge({ state }: { state: ProvenanceState }) {
  const verified = state.endsWith('VERIFIED');
  return (
    <span
      className={`provenance-badge ${
        verified
          ? 'provenance-badge--verified'
          : state === 'RESEARCH REQUIRED'
            ? 'provenance-badge--research'
            : state === 'UNSUPPORTED'
              ? 'provenance-badge--unsupported'
              : 'provenance-badge--modeled'
      }`}
    >
      {state}
    </span>
  );
}

interface PanelProps {
  title?: string;
  description?: string;
  actions?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}

export function Panel({ title, description, actions, children, className = '' }: PanelProps) {
  return (
    <section className={`technical-panel ${className}`}>
      {(title || description || actions) && (
        <header className="technical-panel__header">
          <div>
            {title && <h2 className="technical-panel__title">{title}</h2>}
            {description && <p className="technical-panel__description">{description}</p>}
          </div>
          {actions && <div className="technical-panel__actions">{actions}</div>}
        </header>
      )}
      <div className="technical-panel__body">{children}</div>
    </section>
  );
}

type StateKind = 'loading' | 'empty' | 'unavailable' | 'degraded' | 'error';

const statePresentation: Record<
  StateKind,
  { icon: React.ComponentType<{ className?: string }>; defaultTitle: string }
> = {
  loading: { icon: LoaderCircle, defaultTitle: 'Loading' },
  empty: { icon: SearchX, defaultTitle: 'No evidence' },
  unavailable: { icon: CircleDashed, defaultTitle: 'Not available' },
  degraded: { icon: AlertTriangle, defaultTitle: 'Degraded' },
  error: { icon: OctagonX, defaultTitle: 'Unable to load' },
};

export function StatePanel({
  kind,
  title,
  message,
  action,
}: {
  kind: StateKind;
  title?: string;
  message: string;
  action?: React.ReactNode;
}) {
  const presentation = statePresentation[kind];
  const Icon = presentation.icon;

  return (
    <div className={`state-panel state-panel--${kind}`} role={kind === 'error' ? 'alert' : 'status'}>
      <Icon className={kind === 'loading' ? 'state-panel__icon animate-spin' : 'state-panel__icon'} />
      <div>
        <h3>{title ?? presentation.defaultTitle}</h3>
        <p>{message}</p>
      </div>
      {action && <div className="state-panel__action">{action}</div>}
    </div>
  );
}

export interface TableColumn<T> {
  key: string;
  header: string;
  render: (row: T) => React.ReactNode;
  align?: 'left' | 'right';
}

export function TechnicalTable<T>({
  columns,
  rows,
  getRowKey,
  emptyMessage = 'No records available.',
}: {
  columns: TableColumn<T>[];
  rows: T[];
  getRowKey: (row: T) => string;
  emptyMessage?: string;
}) {
  if (rows.length === 0) {
    return <StatePanel kind="empty" message={emptyMessage} />;
  }

  return (
    <div className="technical-table-wrap">
      <table className="technical-table">
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column.key} className={column.align === 'right' ? 'text-right' : undefined}>
                {column.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={getRowKey(row)}>
              {columns.map((column) => (
                <td key={column.key} className={column.align === 'right' ? 'text-right' : undefined}>
                  {column.render(row)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
