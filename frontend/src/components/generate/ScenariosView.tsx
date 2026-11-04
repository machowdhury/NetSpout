import { useEffect, useMemo, useState } from 'react';
import { compatApi, type ScenarioCompat, type ScenarioPreview } from '../../lib/compatApi';
import { explorerApi } from '../../lib/explorerApi';
import { startRun } from '../../lib/runsApi';
import { LiveDeliveryMonitor } from '../monitor/LiveDeliveryMonitor';
import { Outcome } from './Outcome';
import { EngineNotice } from './EngineNotice';
import { useEngineStatus } from '../../lib/engineApi';
import './simple.css';

const STATE_TEXT: Record<ScenarioCompat['run_state'], { label: string; cls: string; explain: string }> = {
  VERIFIED_IN_SPLUNK: { label: 'Verified in Splunk', cls: 'VERIFIED', explain: 'Every source this scenario needs has been tested against its add-on in a live Splunk.' },
  RUNNABLE_UNVERIFIED: { label: 'Can run, not fully tested in Splunk', cls: 'GENERATOR_UNVERIFIED', explain: 'NetSpout can generate every source this scenario needs. That is not the same as verified: at least one source has not been tested against its add-on in Splunk.' },
  NOT_RUNNABLE: { label: 'Cannot run', cls: 'UNSUPPORTED', explain: 'This scenario will not run until the problems listed under “Why it cannot run” are fixed.' },
};

export function ScenariosView() {
  const [list, setList] = useState<ScenarioCompat[]>([]);
  const [studio, setStudio] = useState<Map<string, string>>(new Map());   // scenario id -> Dashboard Studio dashboard id
  const [err, setErr] = useState('');
  const [category, setCategory] = useState('ALL');
  const [canRunOnly, setCanRunOnly] = useState(true);
  const [id, setId] = useState('');
  const [configured, setConfigured] = useState<boolean | null>(null);
  const [index, setIndex] = useState('');
  const [runId, setRunId] = useState<string | null>(null);
  const [startErr, setStartErr] = useState('');
  const engine = useEngineStatus();
  const [preview, setPreview] = useState<ScenarioPreview | null>(null);
  const [previewErr, setPreviewErr] = useState('');

  useEffect(() => {
    compatApi.scenarios().then((r) => setList(r.scenarios), (e) => setErr(e instanceof Error ? e.message : String(e)));
    compatApi.dashboards().then((r) => setStudio(new Map(r.dashboards.flatMap((x) => [[x.runtime_scenario_id, x.dashboard_id], [x.scenario_id, x.dashboard_id]] as Array<[string, string]>))), () => undefined);
    explorerApi.setup().then((s) => { setConfigured(!!s.configured); setIndex((s.indexes ?? []).find((i) => !/metric/i.test(i)) ?? ''); }, () => setConfigured(false));
  }, []);

  const categories = useMemo(() => ['ALL', ...Array.from(new Set(list.map((s) => s.category ?? 'OTHER'))).sort()], [list]);
  const visible = useMemo(() => list.filter((s) => (category === 'ALL' || (s.category ?? 'OTHER') === category) && (!canRunOnly || s.runnable)), [list, category, canRunOnly]);
  const sc = visible.find((s) => s.id === id) ?? visible[0];
  useEffect(() => { setRunId(null); setStartErr(''); }, [sc?.id]);
  useEffect(() => {
    setPreview(null); setPreviewErr('');
    if (!sc || !sc.runnable) return undefined;
    let alive = true;
    compatApi.scenarioPreview(sc.id, index || undefined).then((p) => alive && setPreview(p), (e) => alive && setPreviewErr(e instanceof Error ? e.message : String(e)));
    return () => { alive = false; };
  }, [sc?.id, sc?.runnable, index]);   // eslint-disable-line react-hooks/exhaustive-deps

  const reason = engine && !engine.connected ? engine.message : !sc ? '' : !sc.runnable ? sc.reasons.join(' ') : configured === false ? 'No Splunk destination is set up yet. Open Connections, save a destination, then come back.' : '';
  const run = async () => {
    if (!sc) return;
    setStartErr('');
    try { setRunId((await startRun({ kind: 'scenario', target: sc.id, index: index || undefined })).run_id); } catch (e) { setStartErr(e instanceof Error ? e.message : String(e)); }
  };
  const st = sc ? STATE_TEXT[sc.run_state] : null;
  const dashboardId = sc ? studio.get(sc.id) : undefined;
  const hasDashboard = !!dashboardId;
  const hasOwnView = !!sc?.dashboard;   // the scenario's own Dashboard Studio view installed with the app; Outcome links it with the run id

  return (
    <div className="sx" data-testid="scenarios-view">
      <div>
        <h2>Scenarios</h2>
        <p className="sx-muted">Run a prepared incident story. Each one lists the sources it needs and whether they are ready.</p>
      </div>
      <EngineNotice status={engine} />
      {err && !engine && <div className="sx-box sx-blocked" role="alert">The scenario list could not be loaded: {err}</div>}
      <section className="sx-box">
        <span className="sx-step">1 · Choose</span>
        <div className="sx-row">
          <label>Category<select data-testid="category" value={category} onChange={(e) => setCategory(e.target.value)}>{categories.map((c) => <option key={c}>{c}</option>)}</select></label>
          <label>Scenario<select data-testid="scenario" value={sc?.id ?? ''} onChange={(e) => setId(e.target.value)}>
            {visible.map((s) => <option key={s.id} value={s.id}>{s.title}{s.run_state === 'NOT_RUNNABLE' ? ' — cannot run' : ''}</option>)}
          </select></label>
        </div>
        <label className="sx-check"><input type="checkbox" data-testid="runnable-only" checked={canRunOnly} onChange={(e) => setCanRunOnly(e.target.checked)} /> Only show scenarios that can run now ({list.filter((s) => s.runnable).length} of {list.length})</label>
      </section>

      {sc && st && (
        <section className="sx-box" data-testid="scenario-detail">
          <span className={`sx-status sx-status--${st.cls}`} data-testid="scenario-state" data-state={sc.run_state}>{st.label}</span>
          <p>{sc.summary}</p>
          <p className="sx-muted">{st.explain}</p>
          {sc.reasons.length > 0 && <div data-testid="why-cannot-run"><b>Why it cannot run</b>{sc.reasons.map((r) => <p className="sx-bad" key={r} data-testid="scenario-reason">{r}</p>)}</div>}
          {sc.warnings.map((w) => <p className="sx-muted" key={w}>{w}</p>)}
          <b>Sources it needs</b>
          <ul className="sx-list" data-testid="required">
            {sc.required.map((r) => <li key={r.sourcetype}><div className="sx-row"><code>{r.sourcetype}</code><span className={`sx-status sx-status--${r.status}`}>{r.status_label}</span></div>{r.block && <span className="sx-muted">{r.block.message}</span>}</li>)}
          </ul>
        </section>
      )}

      {sc && sc.runnable && (
        <section className="sx-box" data-testid="scenario-preview">
          <span className="sx-step">2 · Preview</span>
          {!preview && !previewErr && <p className="sx-muted">Preparing a preview…</p>}
          {previewErr && <p className="sx-bad" role="alert" data-testid="preview-error">Preview failed: {previewErr}</p>}
          {preview && !preview.available && <p className="sx-muted">{preview.note}</p>}
          {preview?.available && (
            <div>
              <p data-testid="preview-summary"><b>{preview.total_events} events</b> in {preview.phases?.length} phases, about {preview.estimated_seconds} seconds. <span className="sx-muted">{preview.estimate_note}</span></p>
              <ul className="sx-list" data-testid="preview-phases">{preview.phases?.map((p) => <li key={p.phase}>{p.phase}: {p.events} events</li>)}</ul>
              <ul className="sx-list" data-testid="preview-counts">{Object.entries(preview.by_sourcetype ?? {}).map(([k, v]) => <li key={k}><code>{k}</code>: {v} events</li>)}</ul>
              {preview.samples?.map((x) => (
                <div key={x.sourcetype} data-testid={`sample-${x.sourcetype}`}>
                  <p className="sx-muted"><code>{x.sourcetype}</code> · host <code>{x.host}</code> · {x.kind === 'metric' ? 'metric index' : 'index'} <code>{x.index}</code>{x.phase ? ` · phase ${x.phase}` : ''}</p>
                  <pre className="sx-pre" data-testid="preview-raw">{x.kind === 'metric' ? Object.entries(x.metrics ?? {}).map(([k, v]) => `${k} = ${v}`).join('\n') : x.raw}</pre>
                </div>))}
            </div>
          )}
        </section>
      )}

      <section className="sx-box">
        <span className="sx-step">3 · Run</span>
        <div className="sx-row">{index && <span className="sx-muted" data-testid="scenario-index">Sends to index <code>{index}</code></span>}<button type="button" className="sx-primary" data-testid="run-scenario" disabled={!sc || !!reason} onClick={() => void run()}>Run scenario</button>{configured === false && <a href="#/system/connections">Set up Connections</a>}</div>
        {reason && <p className="sx-bad" data-testid="cannot-run">{reason}</p>}
        {startErr && <p className="sx-bad" role="alert" data-testid="start-error">{startErr}</p>}
      </section>

      {runId && sc && (
        <section className="sx-box">
          <span className="sx-step">4 · Verify and investigate</span>
          <Outcome runId={runId} />
          <details><summary>Delivery details</summary><LiveDeliveryMonitor runId={runId} /></details>
          {hasDashboard
            ? <a href={`?dashboard=${encodeURIComponent(dashboardId!)}&run=${encodeURIComponent(runId)}#/observe/dashboards`}>Investigate in Dashboard Studio</a>
            : hasOwnView ? null : <p className="sx-muted" data-testid="no-dashboard">No Dashboard Studio dashboard exists for this scenario yet. The run investigation dashboard and the Splunk search above still show everything it sent.</p>}
        </section>
      )}
    </div>
  );
}
