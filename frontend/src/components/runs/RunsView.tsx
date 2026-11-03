import { useCallback, useEffect, useMemo, useState } from 'react';
import type React from 'react';
import { RefreshCw } from 'lucide-react';
import { checkReadiness, listRuns, verifyRun, type Readiness, type RunSnapshot } from '../../lib/runsApi';
import { dashboardHref, runSearchSpl, splunkSearchHref } from '../../lib/splunkLinks';
import { Panel, StatePanel, StatusBadge, TechnicalTable, type RuntimeStatus, type TableColumn } from '../ui/SystemPrimitives';
import type { AppRoute } from '../../app/navigation';

const FINAL = ['COMPLETED', 'STOPPED', 'FAILED'];
const SELECTED_KEY = 'netspout.selectedRun';
// The iframe body inherits Splunk's dark-theme text colour, so content outside the shared primitives states its own colours.
const TEXT: React.CSSProperties = { color: 'var(--ns-text)' };
const PRE: React.CSSProperties = { background: 'var(--ns-surface-subtle)', border: '1px solid var(--ns-border)', borderRadius: 4, padding: 8, margin: '4px 0 12px', whiteSpace: 'pre-wrap', wordBreak: 'break-all', fontFamily: 'var(--ns-font-mono)', fontSize: 12 };
const fmt = (n: number | null | undefined) => (n === null || n === undefined ? 'n/a' : n.toLocaleString());

function remembered(): string | null { try { return window.sessionStorage.getItem(SELECTED_KEY); } catch { return null; } }
function remember(id: string) { try { window.sessionStorage.setItem(SELECTED_KEY, id); } catch { /* storage unavailable: selection is simply not carried over */ } }

/** What the evidence of a run proves, stated from its own counters and its independent verification only. */
export function validationSummary(run: RunSnapshot): { tone: 'ok' | 'warn' | 'bad' | 'neutral'; text: string } {
  const v = run.verification;
  const c = run.counters;
  if (run.state === 'FAILED') return { tone: 'bad', text: run.error ?? 'The run failed before delivery finished.' };
  if (!v || v.status === 'NOT_RUN') return { tone: 'neutral', text: c.accepted ? `${fmt(c.accepted)} events were accepted by HEC. Not yet verified in Splunk: press Verify in Splunk.` : 'Nothing accepted yet.' };
  if (v.status === 'VERIFIED' && v.indexed != null && v.indexed >= (v.accepted ?? 0)) return { tone: 'ok', text: `Verified by an independent Splunk search: ${fmt(v.indexed)} of ${fmt(v.accepted)} accepted events are indexed.` };
  if (v.indexed != null) return { tone: 'warn', text: `${fmt(v.indexed)} of ${fmt(v.accepted)} accepted events are indexed so far. Indexing can trail HEC acceptance; verify again in a moment.` };
  return { tone: 'warn', text: v.error ? `Splunk verification could not complete: ${v.error}` : `Verification status ${v.status}.` };
}

function useRuns(auto: boolean) {
  const [runs, setRuns] = useState<RunSnapshot[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const load = useCallback(async () => {
    try { const list = await listRuns(); setRuns([...list].sort((a, b) => (b.started_at ?? '').localeCompare(a.started_at ?? ''))); setError(null); } catch (e) { setError(e instanceof Error ? e.message : String(e)); }
  }, []);
  useEffect(() => { load(); }, [load]);
  useEffect(() => {
    if (!auto) return undefined;
    const t = window.setInterval(() => { load(); }, 5000);
    return () => window.clearInterval(t);
  }, [auto, load]);
  return { runs, error, load };
}

interface Props { mode: 'observe' | 'investigate'; onNavigate: (route: AppRoute) => void }

export function RunsView({ mode, onNavigate }: Props) {
  const { runs, error, load } = useRuns(mode === 'observe');
  const [selectedId, setSelectedId] = useState<string | null>(remembered());
  const [busy, setBusy] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [readiness, setReadiness] = useState<Record<string, Readiness>>({});
  const selected = useMemo(() => runs?.find((r) => r.run_id === selectedId) ?? runs?.find((r) => r.counters.accepted > 0) ?? runs?.[0] ?? null, [runs, selectedId]);

  const select = (id: string) => { setSelectedId(id); remember(id); };
  const verify = async (id: string) => {
    setBusy(id); setActionError(null);
    try { await verifyRun(id); await load(); } catch (e) { setActionError(e instanceof Error ? e.message : String(e)); } finally { setBusy(null); }
  };
  const openReadiness = useCallback(async (id: string) => {
    try { const r = await checkReadiness(id); setReadiness((prev) => ({ ...prev, [id]: r })); } catch (e) { setActionError(e instanceof Error ? e.message : String(e)); }
  }, []);
  useEffect(() => { if (mode === 'investigate' && selected && selected.counters.accepted > 0 && !readiness[selected.run_id]) openReadiness(selected.run_id); }, [mode, selected, readiness, openReadiness]);

  if (error && !runs) return <StatePanel kind="error" message={`Runs are unavailable: ${error}`} />;
  if (!runs) return <StatePanel kind="loading" message="Loading runs from the engine." />;

  const columns: Array<TableColumn<RunSnapshot>> = [
    { key: 'run', header: 'Run', render: (r) => (<div><strong>{r.title || r.target || r.kind}</strong><span className="table-subtext"><code>{r.run_id}</code></span></div>) },
    { key: 'state', header: 'State', render: (r) => <StatusBadge status={r.state as RuntimeStatus} /> },
    { key: 'counts', header: 'Generated / accepted / indexed', render: (r) => `${fmt(r.counters.generated)} / ${fmt(r.counters.accepted)} / ${r.verification?.indexed != null ? fmt(r.verification.indexed) : 'not verified'}` },
    { key: 'index', header: 'Index', render: (r) => <code>{r.destination?.index ?? 'n/a'}</code> },
    { key: 'actions', header: 'Actions', render: (r) => (
      <div className="runs-actions" style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        <button type="button" className="button button--quiet" onClick={() => { select(r.run_id); onNavigate('/investigate'); }}>Investigate</button>
        <button type="button" className="button button--quiet" disabled={busy === r.run_id || !FINAL.includes(r.state)} onClick={() => verify(r.run_id)}>{busy === r.run_id ? 'Verifying…' : 'Verify in Splunk'}</button>
      </div>
    ) },
  ];

  if (mode === 'observe') {
    return (
      <div className="runs-view" data-testid="runs-observe" style={TEXT}>
        <Panel title="Live runs" description="Every run the engine knows about, with the counters it reports and what an independent Splunk search confirmed."
          actions={<button type="button" className="button button--quiet" onClick={() => { load(); }}><RefreshCw size={14} /> Refresh</button>}>
          {error && <StatePanel kind="degraded" message={`The last refresh failed (${error}); showing the previous list.`} />}
          {actionError && <StatePanel kind="error" message={actionError} />}
          <TechnicalTable columns={columns} rows={runs} getRowKey={(r) => r.run_id} emptyMessage="No runs yet. Start one from Scenarios." />
          <p style={{ marginTop: 12 }}>
            <button type="button" className="button" onClick={() => onNavigate('/explore')}>Start a scenario run</button>{' '}
            <button type="button" className="button button--quiet" onClick={() => onNavigate('/generate/scenarios')}>Guided scenarios</button>
          </p>
        </Panel>
      </div>
    );
  }

  if (!selected) {
    return (
      <Panel title="Investigate a run" description="Pick a run to open its events in Splunk Search or its dashboard.">
        <StatePanel kind="degraded" message="There are no runs to investigate yet. Start one from Scenarios, then return here." />
        <p><button type="button" className="button" onClick={() => onNavigate('/explore')}>Go to Scenarios</button></p>
      </Panel>
    );
  }
  const summary = validationSummary(selected);
  const ready = readiness[selected.run_id];
  const dash = ready?.dashboard?.view && ready.dashboard.tokens ? dashboardHref(ready.dashboard.view, ready.dashboard.tokens) : null;
  const sts = Object.keys(selected.by_sourcetype ?? {});
  const searches: Array<{ label: string; spl: string }> = [
    { label: 'All events of this run', spl: runSearchSpl(selected, '| sort 0 _time') },
    { label: 'Event count by sourcetype', spl: runSearchSpl(selected, '| stats count by sourcetype') },
    ...(selected.by_phase?.length ? [{ label: 'Event count by phase', spl: runSearchSpl(selected, '| stats count by netspout_phase') }] : []),
    ...sts.slice(0, 5).map((st) => ({ label: `Events of ${st}`, spl: runSearchSpl({ ...selected, sourcetype: st }, '| sort 0 _time') })),
  ];
  return (
    <div className="runs-view" data-testid="runs-investigate" style={TEXT}>
      <Panel title="Investigate a run" description="Open the run's own events in Splunk Search, or the dashboard bound to the same run, index and time range.">
        <label>Run{' '}
          <select value={selected.run_id} onChange={(e) => select(e.target.value)} aria-label="Run to investigate">
            {runs.map((r) => (<option key={r.run_id} value={r.run_id}>{(r.title || r.target || r.kind)} · {r.run_id.slice(0, 13)} · {r.state}</option>))}
          </select>
        </label>
        <dl style={{ marginTop: 12 }}>
          <div><dt>Run ID</dt><dd><code>{selected.run_id}</code></dd></div>
          <div><dt>Index</dt><dd><code>{selected.destination?.index ?? 'n/a'}</code></dd></div>
          <div><dt>Started</dt><dd>{selected.started_at ?? 'n/a'}</dd></div>
          <div><dt>Counters</dt><dd>{fmt(selected.counters.generated)} generated · {fmt(selected.counters.accepted)} accepted · {fmt(selected.counters.rejected)} rejected</dd></div>
        </dl>
        <div data-testid="validation" data-tone={summary.tone}><strong>Validation</strong> <StatusBadge status={(selected.verification?.status ?? 'NOT VERIFIED') as RuntimeStatus} /> {summary.text}</div>
        <p style={{ marginTop: 8 }}>
          <button type="button" className="button button--quiet" disabled={busy === selected.run_id || !FINAL.includes(selected.state)} onClick={() => verify(selected.run_id)}>{busy === selected.run_id ? 'Verifying…' : 'Verify in Splunk'}</button>
        </p>
        {actionError && <StatePanel kind="error" message={actionError} />}
      </Panel>
      <Panel title="Open in Splunk" description="These links open Splunk Web in this window with the search already filled in.">
        <ul data-testid="investigation-links">
          {searches.map((s) => { const href = splunkSearchHref(s.spl, selected.started_at); return (
            <li key={s.label}>{href ? <a href={href} target="_top">{s.label}</a> : <span>{s.label}</span>}<pre style={PRE}>{s.spl}</pre></li>); })}
          <li>{dash ? <a href={dash} target="_top">Open the matching dashboard ({ready?.dashboard?.view})</a> : <span>{ready ? (ready.dashboard ? ready.dashboard.note : 'This scenario has no dashboard.') : 'Checking dashboard readiness…'}</span>}{ready && <span className="table-subtext"> Readiness: {ready.state}{ready.present?.events_indexed != null ? `, ${fmt(ready.present.events_indexed)} events indexed` : ''}</span>}</li>
        </ul>
        {!splunkSearchHref('x') && <StatePanel kind="degraded" message="Splunk Web links are available when the app is opened inside Splunk." />}
      </Panel>
    </div>
  );
}
