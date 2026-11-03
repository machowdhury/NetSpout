import { useCallback, useEffect, useRef, useState } from 'react';
import { controlRun, getRun, verifyRun, type RunSnapshot } from '../../lib/runsApi';

const FINAL = ['COMPLETED', 'STOPPED', 'FAILED', 'INTERRUPTED'];
const MAX_CHECKS = 6;
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
      <div className="sx-row">
        {run.controls.stop && <button type="button" onClick={() => void controlRun(runId, 'stop')}>Stop</button>}
        {final && accepted > 0 && <button type="button" data-testid="check-again" disabled={verifying} onClick={() => { attempts.current = 0; void doVerify(); }}>{verifying ? 'Checking…' : 'Check Splunk again'}</button>}
      </div>
    </div>
  );
}
