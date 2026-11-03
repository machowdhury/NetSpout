import { useEffect, useMemo, useState } from 'react';
import { compatApi, type ScenarioCompat } from '../../lib/compatApi';
import { explorerApi } from '../../lib/explorerApi';
import { startRun } from '../../lib/runsApi';
import { LiveDeliveryMonitor } from '../monitor/LiveDeliveryMonitor';
import './simple.css';

const STATE_TEXT: Record<ScenarioCompat['run_state'], { label: string; cls: string; explain: string }> = {
  VERIFIED_IN_SPLUNK: { label: 'Verified in Splunk', cls: 'VERIFIED', explain: 'Every source this scenario needs has been tested against its add-on in a live Splunk.' },
  RUNNABLE_UNVERIFIED: { label: 'Runnable, not verified in Splunk', cls: 'GENERATOR_UNVERIFIED', explain: 'NetSpout can generate every source this scenario needs. That is not the same as verified: at least one source has not been tested against its add-on in Splunk.' },
  NOT_RUNNABLE: { label: 'Cannot run', cls: 'UNSUPPORTED', explain: 'This scenario will not run until the problems below are fixed.' },
};

export function ScenariosView() {
  const [list, setList] = useState<ScenarioCompat[]>([]);
  const [studio, setStudio] = useState<Set<string>>(new Set());
  const [err, setErr] = useState('');
  const [category, setCategory] = useState('ALL');
  const [canRunOnly, setCanRunOnly] = useState(true);
  const [id, setId] = useState('');
  const [configured, setConfigured] = useState<boolean | null>(null);
  const [runId, setRunId] = useState<string | null>(null);
  const [startErr, setStartErr] = useState('');

  useEffect(() => {
    compatApi.scenarios().then((r) => setList(r.scenarios), (e) => setErr(e instanceof Error ? e.message : String(e)));
    compatApi.dashboards().then((r) => setStudio(new Set(r.recipes.map((x) => x.scenario_id))), () => undefined);
    explorerApi.setup().then((s) => setConfigured(!!s.configured), () => setConfigured(false));
  }, []);

  const categories = useMemo(() => ['ALL', ...Array.from(new Set(list.map((s) => s.category ?? 'OTHER'))).sort()], [list]);
  const visible = useMemo(() => list.filter((s) => (category === 'ALL' || (s.category ?? 'OTHER') === category) && (!canRunOnly || s.runnable)), [list, category, canRunOnly]);
  const sc = visible.find((s) => s.id === id) ?? visible[0];
  useEffect(() => { setRunId(null); setStartErr(''); }, [sc?.id]);

  const reason = !sc ? '' : !sc.runnable ? sc.reasons.join(' ') : configured === false ? 'No Splunk destination is set up yet. Open Connections, save a destination, then come back.' : '';
  const run = async () => {
    if (!sc) return;
    setStartErr('');
    try { setRunId((await startRun({ kind: 'scenario', target: sc.id })).run_id); } catch (e) { setStartErr(e instanceof Error ? e.message : String(e)); }
  };
  const st = sc ? STATE_TEXT[sc.run_state] : null;
  const hasDashboard = !!sc && studio.has(sc.id);

  return (
    <div className="sx" data-testid="scenarios-view">
      <div>
        <h2>Scenarios</h2>
        <p className="sx-muted">Run a prepared incident story. Each one lists the sources it needs and whether they are ready.</p>
      </div>
      {err && <div className="sx-box sx-blocked" role="alert">The scenario list could not be loaded: {err}</div>}
      <section className="sx-box">
        <span className="sx-step">1 · Choose</span>
        <div className="sx-row">
          <label>Category<select data-testid="category" value={category} onChange={(e) => setCategory(e.target.value)}>{categories.map((c) => <option key={c}>{c}</option>)}</select></label>
          <label>Scenario<select data-testid="scenario" value={sc?.id ?? ''} onChange={(e) => setId(e.target.value)}>
            {visible.map((s) => <option key={s.id} value={s.id}>{s.title}{s.run_state === 'NOT_RUNNABLE' ? ' — cannot run' : ''}</option>)}
          </select></label>
        </div>
        <label className="sx-check"><input type="checkbox" data-testid="runnable-only" checked={canRunOnly} onChange={(e) => setCanRunOnly(e.target.checked)} /> Only show scenarios that can run ({list.filter((s) => s.runnable).length} of {list.length})</label>
      </section>

      {sc && st && (
        <section className="sx-box" data-testid="scenario-detail">
          <span className={`sx-status sx-status--${st.cls}`} data-testid="scenario-state" data-state={sc.run_state}>{st.label}</span>
          <p>{sc.summary}</p>
          <p className="sx-muted">{st.explain}</p>
          {sc.reasons.map((r) => <p className="sx-bad" key={r} data-testid="scenario-reason">{r}</p>)}
          {sc.warnings.map((w) => <p className="sx-muted" key={w}>{w}</p>)}
          <b>Sources it needs</b>
          <ul className="sx-list" data-testid="required">
            {sc.required.map((r) => <li key={r.sourcetype}><div className="sx-row"><code>{r.sourcetype}</code><span className={`sx-status sx-status--${r.status}`}>{r.status_label}</span></div>{r.block && <span className="sx-muted">{r.block.message}</span>}</li>)}
          </ul>
        </section>
      )}

      <section className="sx-box">
        <span className="sx-step">2 · Run</span>
        <div className="sx-row"><button type="button" className="sx-primary" data-testid="run-scenario" disabled={!sc || !!reason} onClick={() => void run()}>Run scenario</button>{configured === false && <a href="#/system/connections">Set up Connections</a>}</div>
        {reason && <p className="sx-bad" data-testid="cannot-run">{reason}</p>}
        {startErr && <p className="sx-bad" role="alert" data-testid="start-error">{startErr}</p>}
      </section>

      {runId && sc && (
        <section className="sx-box">
          <span className="sx-step">3 · Watch and investigate</span>
          <LiveDeliveryMonitor runId={runId} />
          {hasDashboard
            ? <a href={`?dashboard=scenario-${encodeURIComponent(sc.id)}&run=${encodeURIComponent(runId)}#/observe/dashboards`}>Investigate in Dashboard Studio</a>
            : <p className="sx-muted">This scenario has no Dashboard Studio dashboard yet.</p>}
        </section>
      )}
    </div>
  );
}
