import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { CheckCircle2, CircleDashed, Loader2, Lock, Play, Search, ShieldAlert, XCircle } from 'lucide-react';
import {
  explorerApi,
  type ExplorerEntry,
  type ExplorerSummary,
  type Prerequisites,
  type StepName,
} from '../../lib/explorerApi';
import { LiveDeliveryMonitor, rememberRun } from '../monitor/LiveDeliveryMonitor';
import { startRun } from '../../lib/runsApi';
import './explorer.css';

type StepStatus = 'idle' | 'running' | 'ok' | 'failed';
// Only meaningful inside Splunk Web, where the app's views live on the same origin as this iframe.
function splunkDashboardHref(view?: string | null, runId?: string): string | null {
  const m = window.location.pathname.match(/^\/([a-zA-Z]{2}-[a-zA-Z]{2})\/static\/app\/netspout\//);
  return view && m ? `/${m[1]}/app/netspout/${view}?form.run_tok=${encodeURIComponent(runId ?? '*')}` : null;
}

interface StepState { status: StepStatus; lines: string[] }
type Steps = Partial<Record<StepName, StepState>>;

interface RunContext {
  runId?: string;        // operational run id, or security replay run id
  expected?: number;     // scenario pack: events generated
  accepted?: number;     // scenario pack: events HEC accepted
  metricIndex?: string;  // incident pack: metric index used
  metricExpected?: number; // incident pack: gauge datapoints generated
  eventExpected?: number;  // incident pack: log events generated
  localId?: string;      // retrieved dataset id
  datasetPath?: string;
  indexed?: number;      // events actually observed in Splunk
  replayState?: string;  // replay pack: session state
}

const TIER_LABEL: Record<string, string> = {
  CERTIFIED: 'Certified', VALIDATED: 'Validated', FORMAT_VALIDATED: 'Format validated',
  CONTRACTED: 'Contracted only', CATALOGED: 'Cataloged candidate', NOT_ESTABLISHED: 'Not established',
};
const STEP_LABEL: Record<StepName, string> = {
  SELECT: 'Select', CONFIGURE: 'Configure', GENERATE: 'Generate', INGEST: 'Ingest', VERIFY: 'Verify',
  DASHBOARD: 'Dashboard', PREREQUISITES: 'Prerequisites', ENABLE_DETECTION: 'Enable detection',
};
const errText = (e: unknown) => (e instanceof Error ? e.message : 'Unexpected error');
const stageOf = (evidence: Array<{ stage: string; state: string }>, stage: string) =>
  evidence.find((s) => s.stage === stage)?.state ?? 'NOT_REPORTED';

function MaturityBadge({ entry }: { entry: ExplorerEntry }) {
  if (entry.kind === 'security' && entry.readiness) {
    return <span className={`ux-badge ux-badge--${entry.readiness.level.toLowerCase()}`} title={entry.readiness.label}>{entry.readiness.level.replaceAll('_', ' ')}</span>;
  }
  const tier = entry.maturity?.tier ?? 'NOT_ESTABLISHED';
  return <span className={`ux-badge ux-badge--${tier.toLowerCase()}`} title={`catalog maturity: ${entry.maturity?.raw}`}>{TIER_LABEL[tier]}</span>;
}

export function UseCaseExplorer() {
  const [summary, setSummary] = useState<ExplorerSummary | null>(null);
  const [q, setQ] = useState('');
  const [kind, setKind] = useState<'' | 'operational' | 'security'>('');
  const [industry, setIndustry] = useState('');
  const [demoOnly, setDemoOnly] = useState(true);
  const [items, setItems] = useState<ExplorerEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [selected, setSelected] = useState<ExplorerEntry | null>(null);

  useEffect(() => {
    explorerApi.summary().then(setSummary, (e) => setLoadError(errText(e)));
  }, []);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    const timer = window.setTimeout(() => {
      explorerApi
        .search({ q, kind: kind || undefined, industry: industry || undefined, demoReady: demoOnly ? true : undefined })
        .then((r) => { if (!cancelled) { setItems(r.items); setTotal(r.total); setLoadError(null); } })
        .catch((e) => { if (!cancelled) setLoadError(errText(e)); })
        .finally(() => { if (!cancelled) setLoading(false); });
    }, 200);
    return () => { cancelled = true; window.clearTimeout(timer); };
  }, [q, kind, industry, demoOnly]);

  const open = async (entry: ExplorerEntry) => {
    try {
      setSelected(await explorerApi.entry(entry.entry_id));
    } catch (e) {
      setLoadError(errText(e));
    }
  };

  return (
    <div className="ux" data-testid="use-case-explorer">
      <header className="ux-head">
        <div>
          <h1>Use Case Explorer</h1>
          <p>
            Find a use case, then run it end to end. Maturity shown is the catalog's recorded maturity; a step only turns
            green when the backend reports evidence for it.
          </p>
        </div>
        {summary && (
          <dl className="ux-stats">
            <div><dt>Operational</dt><dd>{summary.operational.total}</dd><small>{summary.operational.demo_ready} certified/validated</small></div>
            <div><dt>Security stories</dt><dd>{summary.security.total}</dd><small>{summary.security.demo_ready} with a runnable workflow</small></div>
          </dl>
        )}
      </header>

      {summary && (
        <p className="ux-note" role="note">{summary.taxonomy.note}</p>
      )}
      {summary?.industries.find((i) => i.id === industry)?.subdomains && (
        <p className="ux-note">
          Subdomains: {summary.industries.find((i) => i.id === industry)!.subdomains!.map((d) => d.name).join(' · ')}.
          Subdomain tags appear only where a source supports one; mappings marked * are editorial.
        </p>
      )}

      <div className="ux-filters">
        <label className="ux-search">
          <Search size={14} aria-hidden />
          <input type="search" placeholder="Search title, vendor, sourcetype, MITRE ID…" value={q}
                 onChange={(e) => setQ(e.target.value)} aria-label="Search use cases" />
        </label>
        <select value={kind} onChange={(e) => setKind(e.target.value as typeof kind)} aria-label="Type">
          <option value="">All types</option>
          <option value="operational">Operational</option>
          <option value="security">Security analytic stories</option>
        </select>
        <select value={industry} onChange={(e) => setIndustry(e.target.value)} aria-label="Industry">
          <option value="">All industries</option>
          {summary?.industries.map((i) => (
            <option key={i.id} value={i.id}>{i.name} ({i.scenarios_runnable ?? 0} runnable / {i.scenarios_total} documented)</option>
          ))}
        </select>
        <label className="ux-check">
          <input type="checkbox" checked={demoOnly} onChange={(e) => setDemoOnly(e.target.checked)} />
          Demo-ready only
        </label>
      </div>

      {loadError && <p className="ux-error" role="alert">{loadError}</p>}

      <div className="ux-body">
        <section className="ux-results" aria-label="Results">
          <p className="ux-count">{loading ? 'Searching…' : `${total} match${total === 1 ? '' : 'es'}`}{items.length < total ? ` · showing ${items.length}` : ''}</p>
          {!loading && total === 0 && !loadError && (
            <p className="ux-empty">
              Nothing matches.{demoOnly ? ' Demo-ready only is on; turn it off to see contracted and replay-only entries.' : ''}
              {industry && ' Industries without mapped scenarios stay empty rather than being padded.'}
            </p>
          )}
          <ul>
            {items.map((entry) => (
              <li key={entry.entry_id}>
                <button type="button" className={`ux-card${selected?.entry_id === entry.entry_id ? ' is-active' : ''}`}
                        onClick={() => open(entry)} data-testid="explorer-card">
                  <span className="ux-card__top">
                    <span className="ux-kind">{entry.kind === 'security' ? 'Security story' : 'Operational'}</span>
                    <MaturityBadge entry={entry} />
                  </span>
                  <strong>{entry.title}</strong>
                  <span className="ux-card__sum">{entry.summary}</span>
                  {entry.industries.length > 0 && (
                    <span className="ux-tags">{entry.industries.map((i) => (
                      <em key={`${i.id}-${i.subdomain ?? ''}`} title={`mapping basis: ${i.basis}${i.subdomain ? `; subdomain ${i.subdomain}` : ''}${i.source_subindustry ? `; source sub-industry ${i.source_subindustry}` : ''}`}>
                        {i.id}{i.subdomain ? ` / ${i.subdomain.replace('gov-', '')}` : ''}{i.basis.startsWith('EDITORIAL') || i.basis === 'editorial' ? '*' : ''}
                      </em>))}</span>
                  )}
                </button>
              </li>
            ))}
          </ul>
        </section>

        <section className="ux-detail" aria-label="Workflow">
          {selected ? <Workflow key={selected.entry_id} entry={selected} /> :
            <p className="ux-empty">Select a use case to see its workflow and what is blocked.</p>}
        </section>
      </div>
    </div>
  );
}

function Workflow({ entry }: { entry: ExplorerEntry }) {
  const [steps, setSteps] = useState<Steps>({});
  const [ctx, setCtx] = useState<RunContext>({});
  const ctxRef = useRef<RunContext>({});
  const [indexes, setIndexes] = useState<string[]>([]);
  const [index, setIndex] = useState('');
  const [count, setCount] = useState(6);
  const [replayMode, setReplayMode] = useState<'one_shot' | 'continuous'>('one_shot');
  const [replaySpeed, setReplaySpeed] = useState(10);
  const [monitorId, setMonitorId] = useState<string | null>(null);
  const [monitorError, setMonitorError] = useState<string | null>(null);
  const [prereq, setPrereq] = useState<Prerequisites | null>(null);
  const security = entry.kind === 'security';
  const detection = useMemo(
    () => entry.detections?.find((d) => d.runtime_approved && d.replay_datasets.length > 0) ?? null,
    [entry],
  );

  useEffect(() => {
    explorerApi.setup().then((s) => {
      const list = s.indexes ?? [];
      setIndexes(list);
      // Default to an event index: the list is sorted, so list[0] can be the metric store.
      setIndex((cur) => cur || list.find((i) => !/metric/i.test(i)) || list[0] || '');
    }, () => undefined);
  }, []);

  const update = useCallback((patch: Partial<RunContext>) => {
    ctxRef.current = { ...ctxRef.current, ...patch };
    setCtx(ctxRef.current);
  }, []);
  const set = (name: StepName, status: StepStatus, lines: string[] = []) =>
    setSteps((s) => ({ ...s, [name]: { status, lines } }));

  const run = async (name: StepName, fn: () => Promise<{ ok: boolean; lines: string[] }>) => {
    set(name, 'running');
    try {
      const r = await fn();
      set(name, r.ok ? 'ok' : 'failed', r.lines);
    } catch (e) {
      set(name, 'failed', [errText(e)]);
    }
  };

  const needIndex = () => { if (!index) throw new Error('Select an authorized index (Connection Center must be configured).'); return index; };
  const needRun = () => { const id = ctxRef.current.runId; if (!id) throw new Error('Run the Generate step first.'); return id; };

  const actions: Partial<Record<StepName, () => Promise<{ ok: boolean; lines: string[] }>>> = {};
  if (!security) {
    const sid = entry.scenario_id as string;
    const unified = entry.engine === 'unified_generation';
    const incident = entry.engine === 'incident_pack';
    const pack = entry.engine === 'scenario_pack' || incident;
    const replay = entry.engine === 'replay_pack';
    actions.CONFIGURE = async () => {
      if (replay) {
        const p = await explorerApi.replayPreview(sid, replaySpeed);
        return { ok: p.records > 0, lines: [`${p.records} records per cycle, cycle period ${p.period_s.toFixed(1)}s (loop gap ${p.loop_gap_s.toFixed(1)}s)`,
          `Correlation: ${p.correlation_level.replaceAll('_', ' ').toLowerCase()}; chronology: ${p.chronology.replaceAll('_', ' ').toLowerCase()}`,
          ...p.rows.slice(0, 2).map((r) => `Preview [${r.phase ?? ''}] ${r.transformed.slice(0, 110)}`)] };
      }
      if (!unified) return { ok: true, lines: ['Runs against the destination saved in Connection Center. Nothing is sent by this step.'] };
      const p = await explorerApi.preflight(sid, count);
      return { ok: p.state !== 'BLOCKED', lines: [`Preflight: ${p.state}`, ...p.checks.map((c) => `${c.state} · ${c.label}: ${c.detail}`)] };
    };
    actions.GENERATE = async () => {
      if (replay) {
        const r = await explorerApi.replayStart({ pack_id: sid, continuous: replayMode === 'continuous', speed: replaySpeed, index: needIndex() });
        update({ runId: r.session_id, replayState: r.state });
        return { ok: true, lines: [`Replay session ${r.session_id}: ${r.state}`, `Source ${r.source} -> index ${r.index}, host ${r.host}`] };
      }
      if (unified) {
        const r = await explorerApi.generate(sid, count);
        update({ runId: r.run_id });
        return { ok: stageOf(r.evidence, 'GENERATED') === 'PROVEN', lines: [`Run ${r.run_id}: ${r.status}`, ...r.evidence.map((s) => `${s.stage}: ${s.state}`)] };
      }
      if (pack) {
        const r = await explorerApi.generatePack(sid, needIndex());
        const accepted = r.dispatch_results.filter((d) => d.hec?.success).length;
        update({ runId: r.run_id, expected: r.count_generated, accepted, metricIndex: r.indexes?.metrics, metricExpected: r.metric_datapoints_expected, eventExpected: r.event_count });
        return { ok: r.count_generated > 0, lines: [`Run ${r.run_id}: generated ${r.count_generated} events`] };
      }
      const r = await explorerApi.runScenario(sid);
      update({ runId: r.run_id });
      return { ok: r.dispatch_attempted > 0, lines: [`Run ${r.run_id}`, `Dispatch attempted ${r.dispatch_attempted}, succeeded ${r.dispatch_succeeded}, failed ${r.dispatch_failed}`, ...r.errors.slice(0, 3)] };
    };
    actions.INGEST = async () => {
      const id = needRun();
      if (replay) {
        let st = await explorerApi.replayStatus(id);
        for (let i = 0; i < 20 && replayMode === 'one_shot' && ['RUNNING', 'CREATED'].includes(st.state); i++) {
          await new Promise((resolve) => window.setTimeout(resolve, 2000));
          st = await explorerApi.replayStatus(id);
        }
        update({ replayState: st.state, expected: st.counts.delivered, accepted: st.counts.accepted });
        const c = st.counts;
        return { ok: c.delivered > 0 && c.rejected === 0 && c.unknown === 0, lines: [`${st.state}: generated ${c.generated}, delivered ${c.delivered}, HEC accepted ${c.accepted}, rejected ${c.rejected}, unknown ${c.unknown}`,
          ...(c.backpressure_waits ? [`Backpressure waits: ${c.backpressure_waits} (nothing dropped)`] : [])] };
      }
      if (unified) {
        // Dispatch (HEC acknowledgement) is proven per channel; every required channel must prove it.
        const r = await explorerApi.observe(id);
        const channels = r.channel_results.filter((c) => c.required);
        const states = channels.map((c) => `${c.source_id}: ${stageOf(c.evidence, 'SPLUNK_DISPATCHED')}`);
        return { ok: channels.length > 0 && channels.every((c) => stageOf(c.evidence, 'SPLUNK_DISPATCHED') === 'PROVEN'), lines: states.map((x) => `SPLUNK_DISPATCHED ${x}`) };
      }
      if (pack) {
        const { expected = 0, accepted = 0 } = ctxRef.current;
        return { ok: expected > 0 && accepted === expected, lines: [`HEC accepted ${accepted} of ${expected} events`] };
      }
      const r = await explorerApi.runObservation(id);
      return { ok: r.event_observed_count + r.metric_observed_count > 0, lines: [`Observed ${r.event_observed_count} events, ${r.metric_observed_count} metrics (${r.observation_status})`] };
    };
    actions.VERIFY = async () => {
      const id = needRun();
      if (replay) {
        let v = await explorerApi.replayVerify(id);
        for (let i = 0; i < 6 && v.verified && !v.complete; i++) {
          await new Promise((resolve) => window.setTimeout(resolve, 4000));
          v = await explorerApi.replayVerify(id);
        }
        return { ok: !!v.verified && !!v.complete, lines: [v.verified ? `Splunk holds ${v.indexed} events for this session; HEC accepted ${v.accepted}` : `Not verified: ${v.error ?? 'unknown'}`,
          'Independent count only: this is not a TA, dashboard or detection result.'] };
      }
      if (unified) {
        // Events can take a few seconds to become searchable: poll while Splunk reports PENDING, never upgrade it.
        let r = await explorerApi.observe(id);
        for (let i = 0; i < 8 && stageOf(r.evidence, 'SPLUNK_OBSERVED') === 'PENDING'; i++) {
          await new Promise((resolve) => window.setTimeout(resolve, 4000));
          r = await explorerApi.observe(id);
        }
        const st = stageOf(r.evidence, 'SPLUNK_OBSERVED');
        return { ok: st === 'PROVEN', lines: [`SPLUNK_OBSERVED: ${st}`, ...r.evidence.filter((s) => s.stage !== 'SPLUNK_OBSERVED').map((s) => `${s.stage}: ${s.state}`)] };
      }
      if (pack) {
        // Events can take a few seconds to become searchable; poll, never upgrade a short count.
        const { expected = 0, eventExpected, metricExpected = 0, metricIndex } = ctxRef.current;
        const want = incident ? (eventExpected ?? 0) : expected;
        const mIdx = incident ? metricIndex : undefined;
        const done = (x: Awaited<ReturnType<typeof explorerApi.observeReplay>>) =>
          (x.indexed_event_count ?? 0) >= want && (!mIdx || (x.indexed_metric_datapoints ?? 0) >= metricExpected);
        let seen = await explorerApi.observeReplay(needIndex(), id, mIdx);
        for (let i = 0; i < 8 && !done(seen) && !seen.error; i++) {
          await new Promise((resolve) => window.setTimeout(resolve, 4000));
          seen = await explorerApi.observeReplay(needIndex(), id, mIdx);
        }
        const eventsOk = want > 0 && seen.indexed_event_count === want;
        const metricsOk = !mIdx || (metricExpected > 0 && seen.indexed_metric_datapoints === metricExpected);
        return { ok: eventsOk && metricsOk, lines: [`Splunk indexed ${seen.indexed_event_count ?? 'n/a'} of ${want} events for this run`,
          ...(mIdx ? [`mstats counted ${seen.indexed_metric_datapoints ?? 'n/a'} of ${metricExpected} metric datapoints`] : []),
          ...(seen.error ? [seen.error] : []), ...(seen.metric_error ? [seen.metric_error] : [])] };
      }
      const r = await explorerApi.runObservation(id);
      return { ok: r.required_evidence_satisfied, lines: [`Required evidence satisfied: ${r.required_evidence_satisfied}`, `Completeness ${r.observation_completeness_pct}% · contract v${r.schema_version ?? '?'}`] };
    };
    actions.DASHBOARD = async () => {
      const id = needRun();
      const dash = entry.dashboard;
      if (!dash) throw new Error('No dashboard is bound to this scenario.');
      if (entry.dashboard?.scale) {
        // The Dashboard Studio view is a Splunk object: the link below opens it with this replay session as the run context.
        return { ok: true, lines: [`Dashboard ${dash.dashboard_id}: ${dash.dashboard_maturity.replaceAll('_', ' ').toLowerCase()}`,
          `Opens with run context ${id}. Maturity comes from stored evidence; it is not a detection or TA result.`] };
      }
      const ix = needIndex();
      const pack = await explorerApi.dashboard(dash.dashboard_id, id, ix);
      const v = await explorerApi.validateDashboard(dash.dashboard_id, id, ix);
      return {
        ok: v.data_validated && v.failures.length === 0,
        lines: [`${pack.title}: ${pack.panels.length} panels generated`, `Dashboard maturity: ${v.maturity}`, ...v.failures.slice(0, 3)],
      };
    };
  } else {
    actions.PREREQUISITES = async () => {
      const p = await explorerApi.prerequisites(entry.entry_id, index || undefined);
      setPrereq(p);
      return { ok: p.ready, lines: [p.ready ? 'All local prerequisites pass.' : 'Some prerequisites fail.', `Live Splunk reachability: ${p.live_reachability}`] };
    };
    actions.GENERATE = async () => {
      if (!detection) throw new Error('No runtime-approved detection with a replay dataset.');
      const path = detection.replay_datasets[0].dataset_path;
      const r = await explorerApi.retrieveDataset(path);
      update({ localId: r.local_id, datasetPath: path });
      return { ok: true, lines: [`Retrieved ${r.size_bytes} bytes, sha256 ${r.sha256.slice(0, 12)}…`, `Upstream commit ${r.repository_commit.slice(0, 10)} (integrity checked)`] };
    };
    actions.INGEST = async () => {
      const { localId, datasetPath } = ctxRef.current;
      if (!localId || !datasetPath) throw new Error('Run the Generate step first.');
      const r = await explorerApi.replay(localId, datasetPath, needIndex());
      update({ runId: r.run_id });
      const lines = [`Replay ${r.run_id}: ${r.status}, sent ${r.events_sent} of ${r.events_read}`, ...r.errors.slice(0, 2)];
      if (r.events_sent === 0) return { ok: false, lines };
      // "sent" is not "indexed": confirm with a run-scoped count from Splunk, allowing for indexing delay.
      let seen = { status: 'NOT_OBSERVED', indexed_event_count: 0 as number | null, error: null as string | null };
      for (let attempt = 0; attempt < 5; attempt += 1) {
        seen = await explorerApi.observeReplay(index, r.run_id);
        if (seen.status === 'OBSERVED' || seen.status === 'ERROR') break;
        await new Promise((res) => window.setTimeout(res, 2000));
      }
      update({ indexed: seen.indexed_event_count ?? 0 });
      return { ok: seen.status === 'OBSERVED', lines: [...lines, `Splunk observed ${seen.indexed_event_count ?? 'n/a'} events (${seen.status})${seen.error ? `: ${seen.error}` : ''}`] };
    };
    actions.ENABLE_DETECTION = async () => {
      if (!detection) throw new Error('No runtime-approved detection.');
      const r = await explorerApi.enableDetection(detection.content_id, needIndex());
      return { ok: r.enabled, lines: [`${r.status}${r.saved_search ? ` · ${r.saved_search}` : ''}${r.error ? ` · ${r.error}` : ''}`, ...(r.limitations ?? [])] };
    };
    actions.VERIFY = async () => {
      if (!detection) throw new Error('No runtime-approved detection.');
      const { runId, datasetPath, indexed } = ctxRef.current;
      if (!runId || !datasetPath || !indexed) throw new Error('Ingest must observe events in Splunk first.');
      const r = await explorerApi.validateDetection({ detection_id: detection.content_id, run_id: runId, index: needIndex(), dataset_or_scenario_id: datasetPath, indexed_event_count: indexed });
      return { ok: r.status === 'POSITIVE_CASE_VALIDATED', lines: [`${r.status} · ${r.matched_event_count} matching events`, ...(r.error ? [r.error] : []), ...r.limitations] };
    };
  }

  const stepList = entry.workflow;
  const first = stepList.findIndex((s) => s.step !== 'SELECT');
  return (
    <article data-testid="explorer-workflow">
      <header className="ux-detail__head">
        <h2>{entry.title}</h2>
        <MaturityBadge entry={entry} />
      </header>
      <p>{entry.summary}</p>
      {entry.provenance && (
        <p className="ux-note" data-testid="candidate-provenance">
          Source: {entry.provenance.source_id} {entry.provenance.source_ref}
          {entry.provenance.url && <> · <a href={entry.provenance.url} target="_blank" rel="noreferrer">original</a></>}
          {entry.provenance.upstream_industry ? ` · upstream label: ${entry.provenance.upstream_industry}` : ''}. Documented candidate, not executable.
        </p>
      )}
      {entry.live_verified && <p className="ux-note">Live Splunk evidence recorded for this scenario (counts verified independently). This does not imply TA parsing, a dashboard or a detection.</p>}
      {security && entry.readiness && (
        <p className="ux-note">
          {entry.readiness.label}. {entry.readiness.detections_runtime_approved} of {entry.readiness.detections_total} detections
          approved for bounded runtime execution. Production efficacy: {entry.readiness.production_detection_efficacy.replaceAll('_', ' ').toLowerCase()}.
          {detection && <> Workflow runs on <strong>{detection.name}</strong>.</>}
        </p>
      )}
      {!security && entry.maturity && entry.maturity.tier === 'CONTRACTED' && (
        <p className="ux-note">Contract only: this scenario has not been validated end to end. Expect gaps.</p>
      )}

      <div className="ux-controls">
        <label>Index
          <select value={index} onChange={(e) => setIndex(e.target.value)} disabled={indexes.length === 0}>
            {indexes.length === 0 && <option value="">Connection Center not configured</option>}
            {indexes.map((i) => <option key={i}>{i}</option>)}
          </select>
        </label>
        {!security && entry.engine === 'unified_generation' && (
          <label>Events
            <input type="number" min={1} max={100} value={count} onChange={(e) => setCount(Math.max(1, Math.min(100, Number(e.target.value) || 1)))} />
          </label>
        )}
        {!security && entry.engine === 'replay_pack' && (
          <>
            <label>Mode
              <select value={replayMode} onChange={(e) => setReplayMode(e.target.value as 'one_shot' | 'continuous')}>
                <option value="one_shot">One-shot incident playback</option>
                <option value="continuous">Continuous cycles</option>
              </select>
            </label>
            <label>Speed
              <input type="number" min={0.1} max={1000} value={replaySpeed} onChange={(e) => setReplaySpeed(Math.max(0.1, Math.min(1000, Number(e.target.value) || 1)))} />
            </label>
            {ctx.runId && (['pause', 'resume', 'stop'] as const).map((a) => (
              <button key={a} type="button" className="ux-run-btn" data-testid={`replay-${a}`}
                      onClick={() => explorerApi.replayControl(ctxRef.current.runId!, a).then((r) => update({ replayState: r.state }), (e) => set('GENERATE', 'failed', [errText(e)]))}>
                {a[0].toUpperCase() + a.slice(1)}
              </button>))}
            {ctx.replayState && <code className="ux-run">{ctx.replayState}</code>}
          </>
        )}
        {ctx.runId && <code className="ux-run">run {ctx.runId}</code>}
      </div>
      {!security && entry.engine !== 'replay_pack' && (
        <button type="button" className="ux-run-btn" data-testid="monitored-run"
                onClick={() => startRun({ kind: 'scenario', target: entry.scenario_id, index: index || undefined }).then(
                  (r) => { rememberRun(r.run_id); setMonitorId(r.run_id); setMonitorError(null); }, (e) => setMonitorError(errText(e)))}>
          Run with live delivery monitor
        </button>)}
      {monitorError && <p className="ux-foot">{monitorError}</p>}
      {(() => { const id = monitorId ?? (entry.engine === 'replay_pack' ? ctx.runId : null); return id ? <LiveDeliveryMonitor key={id} runId={id} onClose={() => setMonitorId(null)} /> : null; })()}

      <ol className="ux-steps">
        {stepList.map((s, i) => {
          const st = steps[s.step] ?? { status: 'idle' as StepStatus, lines: [] };
          const act = actions[s.step];
          const blocked = !s.available;
          const Icon = blocked ? Lock : st.status === 'ok' ? CheckCircle2 : st.status === 'failed' ? XCircle : st.status === 'running' ? Loader2 : CircleDashed;
          return (
            <li key={s.step} className={`ux-step ux-step--${blocked ? 'blocked' : st.status}`} data-testid={`step-${s.step}`}>
              <Icon size={16} className={st.status === 'running' ? 'spin' : undefined} aria-hidden />
              <div>
                <strong>{i + 1}. {STEP_LABEL[s.step]}</strong>
                <small>{s.success_criterion}</small>
                {blocked && <p className="ux-blocked"><ShieldAlert size={12} aria-hidden /> Blocked: {s.blocked_reason}</p>}
                {s.step === 'PREREQUISITES' && prereq && (
                  <ul className="ux-checks">{prereq.checks.map((c) => (
                    <li key={c.check_id} className={c.state === 'PASS' ? 'is-pass' : 'is-fail'}>{c.state} · {c.label}: {c.detail}</li>))}</ul>
                )}
                {st.lines.map((l, k) => <p className="ux-line" key={k}>{l}</p>)}
                {s.step === 'DASHBOARD' && st.status === 'ok' && splunkDashboardHref(entry.dashboard?.splunk_view, ctxRef.current.runId) && (
                  <a className="ux-line" data-testid="open-splunk-dashboard" target="_top"
                     href={splunkDashboardHref(entry.dashboard?.splunk_view, ctxRef.current.runId)!}>Open the Splunk Dashboard Studio dashboard for this run</a>
                )}
              </div>
              {s.step !== 'SELECT' && act && !blocked && (
                <button type="button" className="ux-run-btn" disabled={blocked || st.status === 'running' || i < first}
                        onClick={() => run(s.step, act)}>
                  <Play size={12} aria-hidden /> Run
                </button>
              )}
            </li>
          );
        })}
      </ol>
      {security && <p className="ux-foot">Security stories do not require a dashboard. Verification shows the detection logic matched replayed data; it does not show scheduled firing or production efficacy.</p>}
    </article>
  );
}
