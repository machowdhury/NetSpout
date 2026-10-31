import { useCallback, useEffect, useState } from 'react';
import { controlRun, getRun, verifyRun, type RunSnapshot } from '../../lib/runsApi';

const KEY = 'netspout.monitor.run';
const FINAL = ['COMPLETED', 'STOPPED', 'FAILED', 'INTERRUPTED'];

export function rememberRun(id: string) {
  try { sessionStorage.setItem(KEY, id); } catch { /* storage unavailable: monitor still works without refresh recovery */ }
}
export function rememberedRun(): string | null {
  try { return sessionStorage.getItem(KEY); } catch { return null; }
}

const fmt = (n: number | null | undefined) => (n === null || n === undefined ? '—' : n.toLocaleString());
const dur = (s: number | null | undefined) => (s === null || s === undefined ? '—' : `${Math.floor(s / 60)}m ${Math.round(s % 60)}s`);

function Chart({ points }: { points: Array<{ t: number; eps: number }> }) {
  if (points.length < 2) return <div className="pf-mon-empty">Collecting throughput…</div>;
  const max = Math.max(...points.map((p) => p.eps), 1);
  const d = points.map((p, i) => `${(i / (points.length - 1)) * 300},${60 - (p.eps / max) * 56}`).join(' ');
  return (
    <svg viewBox="0 0 300 60" className="pf-mon-chart" role="img" aria-label={`Throughput, peak ${max.toFixed(1)} events per second`}>
      <polyline points={d} fill="none" stroke="currentColor" strokeWidth="1.5" />
    </svg>
  );
}

export function LiveDeliveryMonitor({ runId, onClose }: { runId: string; onClose?: () => void }) {
  const [run, setRun] = useState<RunSnapshot | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async () => {
    try { setRun(await getRun(runId)); setError(null); } catch (e) { setError(e instanceof Error ? e.message : String(e)); }
  }, [runId]);

  useEffect(() => {
    refresh();
    const t = window.setInterval(() => { if (!run || !FINAL.includes(run.state)) refresh(); }, 1000);
    return () => window.clearInterval(t);
  }, [refresh, run]);

  const act = async (fn: () => Promise<unknown>) => {
    setBusy(true);
    try { await fn(); await refresh(); } catch (e) { setError(e instanceof Error ? e.message : String(e)); } finally { setBusy(false); }
  };

  if (!run) return <div className="pf-mon">{error ? `Monitor unavailable: ${error}` : 'Loading run…'}</div>;
  const c = run.counters;
  const finite = run.progress?.pct !== null && run.progress?.pct !== undefined;
  const tiles: Array<[string, string, string?]> = [
    ['Generated', fmt(c.generated)], ['Attempts', fmt(c.attempts)], ['HEC accepted', fmt(c.accepted), 'Transport acknowledgement, not indexing'],
    ['Rejected', fmt(c.rejected)], ['Unknown', fmt(c.unknown), 'Outcome not confirmed; never resent'], ['Pending', fmt(c.pending)],
    ['Indexed (verified)', c.indexed === null ? 'Not verified' : fmt(c.indexed), 'Only from an independent Splunk search'],
    ['EPS now / avg', `${run.rate?.current_eps ?? 0} / ${run.rate?.average_eps ?? 0}`], ['Elapsed', dur(run.elapsed_s)], ['ETA', finite ? dur(run.eta_s) : 'n/a'],
  ];
  const sts = Object.entries(run.by_sourcetype ?? {});
  return (
    <section className="pf-mon" aria-label="Live delivery monitor" data-state={run.state}>
      <header className="pf-mon-head">
        <div>
          <div className="pf-mon-title">{run.title || run.target}</div>
          <div className="pf-mon-meta">
            {run.destination?.name} · index {run.destination?.index} · run <code>{run.run_id}</code>
          </div>
        </div>
        <span className="pf-mon-state">{run.state}</span>
      </header>
      {run.interrupted_note && <p className="pf-mon-warn">{run.interrupted_note}</p>}
      {run.error && <p className="pf-mon-warn">{run.error}</p>}
      {error && <p className="pf-mon-warn">Engine unreachable: {error}. Showing the last known counters.</p>}
      <div className="pf-mon-bar" role="progressbar" aria-valuenow={finite ? run.progress!.pct! : undefined} aria-valuemin={0} aria-valuemax={100}>
        <div className={finite ? 'pf-mon-fill' : 'pf-mon-fill indeterminate'} style={finite ? { width: `${run.progress!.pct}%` } : undefined} />
      </div>
      <div className="pf-mon-tiles">
        {tiles.map(([k, v, hint]) => (
          <div key={k} title={hint}><span>{k}</span><b>{v}</b></div>
        ))}
      </div>
      <Chart points={run.throughput ?? []} />
      {sts.length > 0 && (
        <table className="pf-mon-table"><thead><tr><th>Sourcetype</th><th>Generated</th><th>Accepted</th><th>Rejected</th><th>Unknown</th></tr></thead>
          <tbody>{sts.map(([k, v]) => <tr key={k}><td>{k}</td><td>{v.generated}</td><td>{v.accepted}</td><td>{v.rejected}</td><td>{v.unknown}</td></tr>)}</tbody></table>
      )}
      {(run.by_phase ?? []).length > 0 && (
        <table className="pf-mon-table"><thead><tr><th>Phase</th><th>Accepted</th><th>Total</th></tr></thead>
          <tbody>{run.by_phase!.map((p) => <tr key={String(p.phase)}><td>{String(p.phase)}</td><td>{p.accepted}</td><td>{p.total ?? '—'}</td></tr>)}</tbody></table>
      )}
      {(run.recent_errors ?? []).length > 0 && (
        <ul className="pf-mon-errors">{run.recent_errors!.slice(-5).map((e, i) => <li key={i}>{e.at} {e.sourcetype} {e.outcome}: {e.message}</li>)}</ul>
      )}
      {run.verification && (
        <p className="pf-mon-verify">Verification: <b>{run.verification.status}</b>{run.verification.indexed != null && ` — ${run.verification.indexed} indexed of ${run.verification.accepted} accepted`}{run.verification.error && ` — ${run.verification.error}`}</p>
      )}
      <footer className="pf-mon-actions">
        <button disabled={busy || !run.controls.pause} onClick={() => act(() => controlRun(runId, 'pause'))}>Pause</button>
        <button disabled={busy || !run.controls.resume} onClick={() => act(() => controlRun(runId, 'resume'))}>Resume</button>
        <button disabled={busy || !run.controls.stop} onClick={() => act(() => controlRun(runId, 'stop'))}>Stop</button>
        <button disabled={busy} onClick={() => act(() => verifyRun(runId))}>Verify in Splunk</button>
        {run.links?.dashboard && <a href={run.links.dashboard}>Open dashboard</a>}
        {onClose && <button onClick={onClose}>Close</button>}
      </footer>
      <p className="pf-mon-note">{run.accounting_note ?? 'HEC accepted means Splunk acknowledged the request. Only Verify proves events are indexed.'}</p>
    </section>
  );
}
