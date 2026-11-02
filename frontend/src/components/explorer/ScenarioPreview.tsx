import { useEffect, useState } from 'react';
import { scenarioPreview, type ScenarioPreviewData } from '../../lib/explorerApi';

// Shown before a run: what will be sent, where, how much (only when calculable), and which dashboard it feeds. Catalog-only entries get their blockers instead of a run path.
export function ScenarioPreview({ entryId, index, eps }: { entryId: string; index: string; eps?: number }) {
  const [p, setP] = useState<ScenarioPreviewData | null>(null);
  useEffect(() => { setP(null); scenarioPreview(entryId).then(setP, () => setP(null)); }, [entryId]);
  if (!p) return null;
  const total = (p.volume.events ?? 0) + (p.volume.metric_events ?? 0);
  return (
    <section className="ux-preview" data-testid="scenario-preview" aria-label="Scenario preview">
      <h3>{p.runnable ? 'What this run will do' : 'This scenario cannot be run yet'}</h3>
      {!p.runnable && <p className="ux-note" data-testid="blockers">Blocked: {p.blockers.join('; ') || 'no authentic execution path exists for this catalog entry.'}</p>}
      <dl>
        <dt>Telemetry</dt><dd>{p.required_sourcetypes.length ? p.required_sourcetypes.join(', ') : 'sourcetypes are decided by the engine at run time'}</dd>
        {p.volume.phases.length > 0 && <><dt>Phases</dt><dd>{p.volume.phases.map((x) => `${x.phase} (${x.events})`).join(' → ')}</dd></>}
        <dt>Volume</dt><dd>{total ? `${p.volume.events} events${p.volume.metric_events ? ` + ${p.volume.metric_events} metric events` : ''} (${p.volume.basis})` : p.volume.basis}</dd>
        {p.runnable && <><dt>Destination</dt><dd>{p.execution.destination ?? 'Connection Center not active'} · {p.execution.path} · index {index || '—'}{p.execution.metric_index ? ` · metrics ${p.execution.metric_index}` : ''}</dd></>}
        {p.runnable && total > 0 && eps ? <><dt>Estimated duration</dt><dd>about {Math.ceil(total / eps)}s at {eps} EPS (planned events ÷ EPS; excludes indexing lag)</dd></> : null}
        <dt>Dashboard</dt><dd>{p.dashboard ? `${p.dashboard.view} (${p.dashboard.maturity ?? 'installed'}). ${p.dashboard.note}.` : 'none for this scenario'}</dd>
      </dl>
      {p.runnable && <p className="ux-foot">Delivery is acknowledged by HEC first; indexing and search visibility can trail. {p.timing.note} The monitor opens immediately and checks dashboard readiness for this run automatically.</p>}
    </section>
  );
}
