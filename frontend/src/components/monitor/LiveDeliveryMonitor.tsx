import { useCallback, useEffect, useRef, useState } from 'react';
import { checkReadiness, controlRun, getRun, verifyRun, type Readiness, type RunSnapshot } from '../../lib/runsApi';

const KEY = 'netspout.monitor.run';
const FINAL = ['COMPLETED', 'STOPPED', 'FAILED', 'INTERRUPTED'];

export function rememberRun(id: string, scope = '') {
  try { sessionStorage.setItem(KEY + scope, id); } catch { /* storage unavailable: monitor still works without refresh recovery */ }
}
export function rememberedRun(scope = ''): string | null {
  try { return sessionStorage.getItem(KEY + scope); } catch { return null; }
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

// Dashboards live in Splunk Web on the same origin as this iframe; the run id and a time window are passed as form tokens.
function dashboardHref(r: Readiness): string | null {
  const m = window.location.pathname.match(/^\/([a-zA-Z]{2}-[a-zA-Z]{2})\/static\/app\/netspout\//);
  if (!r.dashboard || !m) return null;
  const qs = Object.entries(r.dashboard.tokens).map(([k, v]) => `${k}=${encodeURIComponent(String(v))}`).join('&');
  return `/${m[1]}/app/netspout/${r.dashboard.view}?${qs}`;
}

const POLL_MS = 5000;
const POLL_MAX = 60;   // about five minutes after delivery ends, then the last state stands (DEGRADED/INDEXING) instead of spinning forever

function ReadinessPanel({ run }: { run: RunSnapshot }) {
  const [r, setR] = useState<Readiness | null>(null);
  const [shown, setShown] = useState(true);
  const final = FINAL.includes(run.state);
  useEffect(() => {
    if (!final || run.counters.accepted === 0 && run.state !== 'FAILED') return undefined;
    let cancelled = false; let n = 0; let timer = 0;
    const tick = async () => {
      try { const x = await checkReadiness(run.run_id); if (cancelled) return; setR(x); n += 1; if (!['READY', 'FAILED', 'DEGRADED'].includes(x.state) && n < POLL_MAX) timer = window.setTimeout(tick, POLL_MS); }
      catch { if (!cancelled && n < POLL_MAX) { n += 1; timer = window.setTimeout(tick, POLL_MS); } }
    };
    tick();
    return () => { cancelled = true; window.clearTimeout(timer); };
  }, [final, run.run_id, run.state, run.counters.accepted]);
  const state = r?.state ?? (final ? 'INDEXING' : run.counters.attempts === 0 ? 'GENERATING' : 'DELIVERING');
  const href = r ? dashboardHref(r) : null;
  return (
    <div className={`pf-mon-ready pf-mon-ready--${state}`} data-testid="readiness" role="status">
      <b data-testid="readiness-state">{state}</b>
      {state === 'READY' && shown ? (
        <div className="pf-mon-toast" data-testid="readiness-toast">
          <strong>Your scenario data is ready in Splunk.</strong>
          <span>{r?.title || r?.scenario} · run <code>{r?.run_id}</code> · {fmt(r?.present?.events_indexed)} events indexed{r?.verification?.metric_datapoints_indexed != null ? `, ${fmt(r.verification.metric_datapoints_indexed)} metric datapoints` : ''} · {dur(r?.elapsed_to_ready_s ?? r?.elapsed_s)}</span>
          {href ? <a href={href} target="_top">Open dashboard</a> : <span>{r?.dashboard ? 'Open the dashboard from Splunk Web' : 'This scenario has no dashboard'}</span>}
          <a href="#evidence" onClick={(e) => { e.preventDefault(); document.querySelector('.pf-mon-verify')?.scrollIntoView({ block: 'center' }); }}>View evidence</a>
          <button type="button" onClick={() => setShown(false)}>Dismiss</button>
        </div>
      ) : null}
      {state === 'PARTIALLY_READY' && <span> Present: {Object.entries(r?.present?.sourcetypes ?? {}).map(([k, v]) => `${k} ${v}`).join(', ') || 'some events'}. Missing: {(r?.missing ?? []).join(', ') || 'remaining events'}.</span>}
      {state === 'INDEXING' && <span> Delivery is finished; checking Splunk for this run&apos;s events. Indexing can lag, so verification is in progress.</span>}
      {state === 'DELIVERING' && <span> Events are being delivered; indexing is checked after the run ends.</span>}
      {['DEGRADED', 'FAILED', 'UNKNOWN'].includes(state) && <span> {(r?.notes ?? []).join(' ')}{href && state === 'DEGRADED' ? ' ' : ''}{href && state === 'DEGRADED' && <a href={href} target="_top">Open dashboard anyway</a>}</span>}
    </div>
  );
}

export function LiveDeliveryMonitor({ runId, onClose }: { runId: string; onClose?: () => void }) {
  const [run, setRun] = useState<RunSnapshot | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const [transition, setTransition] = useState<{ label: string; want: string[]; until: number } | null>(null);
  const [lagS, setLagS] = useState(0);
  const lastOk = useRef(Date.now());
  const inflight = useRef(false);
  // One poll at a time: a stalled gateway must not pile up requests, because browsers allow only a few connections per origin and the control POSTs would queue behind them.
  const refresh = useCallback(async () => {
    if (inflight.current) return;
    inflight.current = true;
    try { setRun(await getRun(runId)); lastOk.current = Date.now(); setError(null); } catch (e) { setError(e instanceof Error ? e.message : String(e)); } finally { inflight.current = false; }
  }, [runId]);

  useEffect(() => {
    refresh();
    const t = window.setInterval(() => { if (!run || !FINAL.includes(run.state)) refresh(); }, 1000);
    return () => window.clearInterval(t);
  }, [refresh, run]);

  // Seconds since the last answer from the engine through the gateway: a stalled gateway shows as lag, not as a state the run does not have.
  useEffect(() => {
    const t = window.setInterval(() => setLagS(Math.round((Date.now() - lastOk.current) / 1000)), 1000);
    return () => window.clearInterval(t);
  }, []);
  useEffect(() => {
    if (transition && (run && (transition.want.includes(run.state) || FINAL.includes(run.state)) || Date.now() > transition.until)) setTransition(null);
  }, [run, transition, lagS]);

  const TRANSITIONS: Record<string, { label: string; want: string[] }> = { pause: { label: 'PAUSING', want: ['PAUSED'] }, resume: { label: 'RESUMING', want: ['RUNNING'] }, stop: { label: 'STOPPING', want: ['STOPPING', 'STOPPED', 'COMPLETED'] } };
  const control = (action: 'pause' | 'resume' | 'stop') => {
    setTransition({ ...TRANSITIONS[action], until: Date.now() + 20000 });
    return act(() => controlRun(runId, action));
  };

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
            {run.destination?.name} · index {run.destination?.index} · run <code>{run.run_id}</code>{run.mode ? ` · ${run.mode === 'continuous' ? 'continuous, runs until stopped' : run.mode}` : ''}
          </div>
        </div>
        <span className="pf-mon-state" data-engine-state={run.state}>{transition ? `${transition.label}…` : run.state}</span>
      </header>
      {lagS >= 4 && !FINAL.includes(run.state) && <p className="pf-mon-warn" data-testid="gateway-lag">No answer from the engine through the gateway for {lagS}s. The state shown is the last one received; the run itself is not affected by this delay.</p>}
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
      {run.flow_wire && (
        <section className="pf-mon-wire" data-testid="flow-wire" aria-label="NetFlow wire stages">
          <b>NetFlow/IPFIX stages</b>
          <table className="pf-mon-table"><thead><tr><th>Stage</th><th>Records</th><th>Meaning</th></tr></thead><tbody>
            <tr><td>Generated flows</td><td>{run.flow_wire.generated}</td><td>Deterministic synthetic flow records</td></tr>
            <tr><td>UDP exported (IPFIX)</td><td>{run.flow_wire.udp_exported ?? 0}</td><td>{run.flow_wire.state}{run.flow_wire.collector ? ` → ${run.flow_wire.collector}` : ''}; the OS accepted the datagrams</td></tr>
            <tr><td>Collector decoded</td><td>{run.flow_wire.collector_decoded ?? 'n/a'}</td><td>GoFlow2 record counter delta; not HEC and not indexing</td></tr>
            <tr><td>HEC accepted (normalized events)</td><td>{c.accepted}</td><td>What this monitor counts{run.sourcetype ? ` · ${run.sourcetype}` : ''}</td></tr>
          </tbody></table>
          {run.flow_wire.note && <p className="pf-mon-note">{run.flow_wire.note}</p>}
        </section>
      )}
      <ReadinessPanel run={run} />
      <Chart points={run.throughput ?? []} />
      {sts.length > 0 && (
        <table className="pf-mon-table"><thead><tr><th>Sourcetype</th><th>Generated</th><th>Accepted</th><th>Rejected</th><th>Unknown</th></tr></thead>
          <tbody>{sts.map(([k, v]) => <tr key={k}><td>{k}</td><td>{v.total ?? 0}</td><td>{v.accepted ?? 0}</td><td>{v.rejected ?? 0}</td><td>{v.unknown ?? 0}</td></tr>)}</tbody></table>
      )}
      {(run.by_phase ?? []).length > 0 && (
        <table className="pf-mon-table"><thead><tr><th>Phase</th><th>Accepted</th><th>Total</th></tr></thead>
          <tbody>{run.by_phase!.map((p) => <tr key={String(p.phase)}><td>{String(p.phase)}</td><td>{p.accepted ?? 0}</td><td>{p.total ?? '—'}</td></tr>)}</tbody></table>
      )}
      {(run.recent_errors ?? []).length > 0 && (
        <ul className="pf-mon-errors">{run.recent_errors!.slice(-5).map((e, i) => <li key={i}>{e.at} {e.sourcetype} {e.outcome}: {e.message}</li>)}</ul>
      )}
      {run.verification && (
        <p className="pf-mon-verify">Verification: <b>{run.verification.status}</b>{run.verification.indexed != null && ` — ${run.verification.indexed} indexed of ${run.verification.accepted} accepted`}{run.verification.error && ` — ${run.verification.error}`}</p>
      )}
      {(run as RunSnapshot & { controls_note?: string }).controls_note && <p className="pf-mon-note">{(run as RunSnapshot & { controls_note?: string }).controls_note}</p>}
      <footer className="pf-mon-actions">
        <button disabled={busy || !run.controls.pause} onClick={() => control('pause')}>Pause</button>
        <button disabled={busy || !run.controls.resume} onClick={() => control('resume')}>Resume</button>
        <button disabled={busy || !run.controls.stop} onClick={() => control('stop')}>Stop</button>
        <button disabled={busy} onClick={() => act(() => verifyRun(runId))}>Verify in Splunk</button>
        {run.links?.dashboard && <a href={run.links.dashboard}>Open dashboard</a>}
        {onClose && <button onClick={onClose}>Close</button>}
      </footer>
      <p className="pf-mon-note">{run.accounting_note ?? 'HEC accepted means Splunk acknowledged the request. Only Verify proves events are indexed.'}</p>
    </section>
  );
}
