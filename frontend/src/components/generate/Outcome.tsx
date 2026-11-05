import { useCallback, useEffect, useRef, useState } from 'react';
import { controlRun, getRun, verifyRun, type RunSnapshot } from '../../lib/runsApi';
import { insideSplunk } from '../../lib/engineApi';

const FINAL = ['COMPLETED', 'STOPPED', 'FAILED', 'INTERRUPTED'];
const MAX_CHECKS = 6;
const RESULT_WORD: Record<string, string> = { VERIFIED: 'Verified', INCOMPLETE: 'Not all found yet', NOT_SENT: 'Nothing accepted', UNKNOWN: 'Could not be checked', UNMATCHED: 'Could not be matched by name' };

// Where the run's data can be examined in Splunk: the app's run-investigation dashboard (its own index, time range and run id) and a plain search.
function investigationLinks(run: RunSnapshot) {
  const m = window.location.pathname.match(/^\/([a-zA-Z]{2}-[a-zA-Z]{2})\/static\/app\/netspout\//);
  if (!m) return null;
  const idx = run.destination?.index ?? '', midx = run.destination?.metric_index ?? '';
  const t0 = run.started_at ? Math.floor(Date.parse(run.started_at) / 1000) - 300 : Math.floor(Date.now() / 1000) - 3600;
  const t1 = Math.floor(Date.now() / 1000) + 300;
  const q = new URLSearchParams({ 'form.run_tok': run.run_id, 'form.index_tok': idx, 'form.global_time.earliest': String(t0), 'form.global_time.latest': String(t1) });
  if (midx) q.set('form.mindex_tok', midx);
  const search = new URLSearchParams({ q: `search index="${idx}" netspout_run_id="${run.run_id}" | stats count by sourcetype, host`, earliest: String(t0), latest: String(t1) });
  const own = run.links?.dashboard_view;   // the scenario's own dashboard, when it has one
  return { own: own ? `/${m[1]}/app/netspout/${own}?${q}` : null, dashboard: `/${m[1]}/app/netspout/netspout_run_investigation?${q}`, search: `/${m[1]}/app/search/search?${search}` };
}
type Verify = NonNullable<RunSnapshot['verification']>;

// Plain-language answer to "did Splunk receive it?". Delivery (HEC accepted it) and indexing (a search finds it) are different facts, and the page
// says "Verified" only when an independent search in the destination index (events) or an mstats search in the metric index (metrics) found them.
export function Outcome({ runId }: { runId: string }) {
  const [run, setRun] = useState<RunSnapshot | null>(null);
  const [verify, setVerify] = useState<Verify | null>(null);
  const [verifying, setVerifying] = useState(false);
  const [, setChecks] = useState(0);   // a re-render trigger: the check counter itself lives in a ref
  const attempts = useRef(0);
  useEffect(() => { setRun(null); setVerify(null); setChecks(0); attempts.current = 0; }, [runId]);
  useEffect(() => {
    if (run && FINAL.includes(run.state)) return undefined;
    const t = window.setInterval(() => getRun(runId).then(setRun, () => undefined), 1000);
    getRun(runId).then(setRun, () => undefined);
    return () => window.clearInterval(t);
  }, [runId, run?.state]);
  const final = !!run && FINAL.includes(run.state);
  const accepted = run?.counters.accepted ?? 0;
  const doVerify = useCallback(async () => {
    setVerifying(true);
    try { const v = await verifyRun(runId); setVerify(v); return v; } catch (e) { const v = { status: 'ERROR', error: e instanceof Error ? e.message : String(e) }; setVerify(v); return v; } finally { setVerifying(false); setChecks((n) => n + 1); }
  }, [runId]);
  // After delivery ends, search Splunk for this run's data; indexing can lag, so a few retries before the answer stands.
  useEffect(() => {
    if (!final || accepted === 0 || verify?.status === 'VERIFIED') return undefined;
    if (verify && !['INCOMPLETE', 'NOT_RUN'].includes(verify.status)) return undefined;
    if (attempts.current >= MAX_CHECKS) return undefined;
    const t = window.setTimeout(() => { attempts.current += 1; void doVerify(); }, verify ? 5000 : 2500);
    return () => window.clearTimeout(t);
  }, [final, accepted, verify, doVerify]);
  if (!run) return <div className="sx-box" data-testid="outcome">Starting…</div>;
  const c = run.counters;
  const idx = run.destination?.index ?? 'the event index';
  const midx = run.destination?.metric_index ?? 'the metric index';
  const wantsMetric = (verify?.metric_datapoints_expected ?? 0) > 0;
  const wantsEvents = (verify?.expected_log_events ?? c.accepted) > 0;
  const exhausted = attempts.current >= MAX_CHECKS && verify?.status === 'INCOMPLETE' && !verifying;
  const found = [
    wantsEvents ? `${(verify?.indexed ?? 0) === 0 ? 'none of the' : `${verify?.indexed} of`} ${verify?.expected_log_events ?? c.accepted} events in index ${idx}` : '',
    wantsMetric ? `${(verify?.metric_datapoints_indexed ?? 0) === 0 ? 'none of the' : `${verify?.metric_datapoints_indexed} of`} ${verify?.metric_datapoints_expected} metric datapoints in metric index ${midx} (mstats search)` : '',
  ].filter(Boolean).join(' and ');
  const sources = run.kind === 'scenario' || run.kind === 'multi' ? Object.entries(run.by_sourcetype ?? {}) : [];
  const vs = Object.values(verify?.by_sourcetype ?? {}).filter((x) => x.accepted > 0);
  const okSources = vs.filter((x) => x.status === 'VERIFIED').length, sentSources = vs.length;
  const partial = final && sentSources > 1 && okSources > 0 && okSources < sentSources;
  const links = final && accepted > 0 && run.kind !== 'replay' ? investigationLinks(run) : null;
  let tone = '', text = '';
  if (!final) text = `Sending… ${c.accepted.toLocaleString()} accepted by Splunk HEC so far${c.rejected ? `, ${c.rejected} rejected` : ''}${run.mode === 'continuous' ? ' (streaming until stopped)' : ''}.`;
  else if (run.state === 'FAILED' || (c.generated > 0 && c.accepted === 0)) { tone = 'sx-bad'; text = `Splunk did not receive this data. ${run.error ?? run.recent_errors?.slice(-1)[0]?.message ?? 'The destination rejected it or could not be reached.'}`; }
  else if (c.rejected > 0 || c.unknown > 0) { tone = 'sx-bad'; text = `Only ${c.accepted} of ${c.generated} were accepted (${c.rejected} rejected, ${c.unknown} unconfirmed). ${run.recent_errors?.slice(-1)[0]?.message ?? ''}`; }
  else if (verify?.status === 'VERIFIED') { tone = 'sx-ok'; text = `Verified: found ${found} that this run sent.`; }
  else if (exhausted) { tone = 'sx-bad'; text = `Not confirmed: Splunk accepted ${c.accepted}, but a search found ${found || 'none of it'}, after ${MAX_CHECKS} checks. It may have gone to a different index, been dropped, or still be indexing. Accepted by Splunk is not the same as searchable.`; }
  else if (verify?.status === 'INCOMPLETE') text = `Splunk accepted ${c.accepted}; so far a search found ${found || 'none of it'}. Indexing can lag, so this is still being checked.`;
  else if (verify && ['ERROR', 'NOT_RUN', 'UNAVAILABLE', 'FAILED'].includes(verify.status)) { tone = 'sx-bad'; text = `Splunk accepted ${c.accepted}, but this app could not check whether it is searchable: ${verify.error ?? verify.status}. Accepted by Splunk is not the same as searchable, so this is not verified.`; }
  else text = `Splunk accepted ${c.accepted} of ${c.generated}. Checking that it is searchable…`;
  return (
    <div className="sx-box" data-testid="outcome" role="status" data-verification={verify?.status ?? 'PENDING'}>
      <p className={tone} data-testid="outcome-text">{text}</p>
      {partial && <p className="sx-bad" data-testid="partial">Partly verified: {okSources} of {sentSources} sources were found in Splunk. The table shows which ones were not.</p>}
      {sources.length > 0 && (
        <table className="sx-table" data-testid="by-source"><thead><tr><th>Sourcetype</th><th>Goes to</th><th>Accepted</th><th>Rejected</th><th>Found in Splunk</th><th>Result</th></tr></thead>
          <tbody>{sources.map(([st, c]) => { const v = verify?.by_sourcetype?.[st]; const metric = v?.kind === 'metric'; const rej = (c.rejected ?? 0) + (c.unknown ?? 0); return (
            <tr key={st} data-testid={`source-${st}`} data-result={v?.status ?? (rej && !(c.accepted ?? 0) ? 'NOT_SENT' : 'PENDING')}>
              <td><code>{st}</code></td><td>{metric ? `metric index ${v?.index}` : `index ${v?.index ?? idx}`}</td>
              <td>{c.accepted ?? 0}</td><td>{rej}</td>
              <td>{v ? (v.indexed === null ? 'unknown' : metric ? `${v.indexed} of ${v.expected} datapoints` : `${v.indexed} of ${v.expected}`) : '…'}</td>
              <td className={v?.status === 'VERIFIED' ? 'sx-ok' : v || rej ? 'sx-bad' : ''}>{v ? RESULT_WORD[v.status] : rej && !(c.accepted ?? 0) ? 'Nothing accepted' : final ? 'Checking…' : 'Sending…'}</td>
            </tr>); })}</tbody></table>
      )}
      {sources.length > 1 && final && (
        <p className="sx-muted" data-testid="totals">Totals: {c.accepted} accepted · {c.rejected + c.unknown} rejected or unconfirmed{verify?.indexed != null ? ` · ${verify.indexed} events found in Splunk` : ''}{verify?.metric_datapoints_indexed != null ? ` · ${verify.metric_datapoints_indexed} of ${verify.metric_datapoints_expected} metric datapoints found` : ''}.</p>
      )}
      <div className="sx-row">
        {run.controls.stop && <button type="button" data-testid="stop-run" onClick={() => void controlRun(runId, 'stop')}>Stop</button>}
        {final && accepted > 0 && <button type="button" data-testid="check-again" disabled={verifying} onClick={() => { attempts.current = 0; void doVerify(); }}>{verifying ? 'Checking…' : 'Check Splunk again'}</button>}
      </div>
      {final && accepted > 0 && (
        <div data-testid="investigate">
          <b>Investigate</b>
          {links ? <div className="sx-row">
            {links.own && <a data-testid="investigate-scenario-dashboard" href={links.own} target="_blank" rel="noreferrer">Open the scenario's Dashboard Studio dashboard</a>}
            <a data-testid="investigate-dashboard" href={links.dashboard} target="_blank" rel="noreferrer">Open this run in the investigation dashboard</a>
            <a data-testid="investigate-search" href={links.search} target="_blank" rel="noreferrer">Search this run in Splunk</a>
          </div> : <p className="sx-muted">{insideSplunk() ? '' : 'Open the app inside Splunk to investigate this run in a dashboard. Its run id is '}<code>{run.run_id}</code></p>}
        </div>
      )}
    </div>
  );
}
