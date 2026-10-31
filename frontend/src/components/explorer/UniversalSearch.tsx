import { useEffect, useState } from 'react';
import { universalSearch, type SearchHit, type UniversalResult } from '../../lib/explorerApi';

const KEY = 'pf-find';
const KINDS: Array<['' | SearchHit['kind'], string]> = [['', 'All'], ['sourcetype', 'Sourcetypes'], ['scenario', 'Scenarios'], ['dashboard', 'Dashboards']];

function saved(): { q: string; kind: string; runnable: string; dash: string } {
  try { return { q: '', kind: '', runnable: '', dash: '', ...JSON.parse(sessionStorage.getItem(KEY) || '{}') }; } catch { return { q: '', kind: '', runnable: '', dash: '' }; }
}

// Dashboards open in Splunk Web only when this iframe is served from the app's static path.
function dashHref(view: string): string | null {
  const m = window.location.pathname.match(/^\/([a-zA-Z]{2}-[a-zA-Z]{2})\/static\/app\/netspout\//);
  return m ? `/${m[1]}/app/netspout/${view}` : null;
}

export function UniversalSearch({ onPickScenario }: { onPickScenario: (entryId: string) => void }) {
  const init = saved();
  const [q, setQ] = useState(init.q);
  const [kind, setKind] = useState(init.kind);
  const [runnable, setRunnable] = useState(init.runnable);
  const [dash, setDash] = useState(init.dash);
  const [res, setRes] = useState<UniversalResult | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    try { sessionStorage.setItem(KEY, JSON.stringify({ q, kind, runnable, dash })); } catch { /* per-viewer convenience only */ }
    if (!q && !kind && !runnable && !dash) { setRes(null); return; }
    let cancelled = false;
    const t = window.setTimeout(() => {
      universalSearch({ q, kind: kind || undefined, runnable: runnable || undefined, dashboard_available: dash || undefined, limit: '30' })
        .then((r) => { if (!cancelled) { setRes(r); setErr(null); } }, (e) => { if (!cancelled) setErr(String(e.message || e)); });
    }, 200);
    return () => { cancelled = true; window.clearTimeout(t); };
  }, [q, kind, runnable, dash]);

  return (
    <section className="ux-find" aria-label="Universal search" data-testid="universal-search">
      <div className="ux-filters">
        <label className="ux-search">
          <input type="search" placeholder="Find any sourcetype, scenario or dashboard…" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Universal search" />
        </label>
        <select value={kind} onChange={(e) => setKind(e.target.value)} aria-label="Result type">
          {KINDS.map(([v, l]) => <option key={v} value={v}>{l}{res && v ? ` (${res.counts[v] ?? 0})` : ''}</option>)}
        </select>
        <select value={runnable} onChange={(e) => setRunnable(e.target.value)} aria-label="Runnable">
          <option value="">Runnable or catalog-only</option><option value="true">Runnable only</option><option value="false">Catalog-only only</option>
        </select>
        <select value={dash} onChange={(e) => setDash(e.target.value)} aria-label="Dashboard">
          <option value="">Any dashboard status</option><option value="true">Has dashboard</option><option value="false">No dashboard</option>
        </select>
      </div>
      {err && <p className="ux-error" role="alert">{err}</p>}
      {res && (
        <>
          <p className="ux-count">{res.total} result{res.total === 1 ? '' : 's'}: {Object.entries(res.counts).map(([k, n]) => `${n} ${k}${n === 1 ? '' : 's'}`).join(', ') || 'none'}{res.items.length < res.total ? ` · showing ${res.items.length}` : ''}</p>
          {res.total === 0 && <p className="ux-empty">No match. Try a vendor, protocol, sourcetype name or scenario ID, or clear the filters.</p>}
          <ul className="ux-find__list">
            {res.items.map((h) => {
              const href = h.kind === 'dashboard' ? dashHref(h.id) : null;
              return (
                <li key={h.kind + h.id} className="ux-card" data-kind={h.kind}>
                  <span className="ux-card__top"><span className="ux-kind">{h.kind}</span>
                    <span className="ux-kind">{h.kind === 'dashboard' ? (h.maturity ?? 'installed') : h.runnable ? 'runnable' : 'catalog only'}</span></span>
                  <strong>{h.title}</strong>
                  <span className="ux-card__sum">
                    {[h.subtitle, h.vendor, h.protocol, h.execution_mode, h.dashboard_available && h.kind !== 'dashboard' ? 'dashboard available' : null, h.independently_indexed ? 'independently indexed' : null].filter(Boolean).join(' · ')}
                  </span>
                  <span className="ux-card__sum">Next: {h.next_action}</span>
                  {h.kind === 'scenario' && <button type="button" onClick={() => onPickScenario(h.id)}>{h.runnable ? 'Open scenario workflow' : 'View details (not executable)'}</button>}
                  {h.kind === 'dashboard' && (href ? <a href={href} target="_top">Open dashboard</a> : <span className="ux-card__sum">Opens inside Splunk Web</span>)}
                  {h.kind === 'sourcetype' && !!h.related_scenarios?.length && <span className="ux-card__sum">{h.related_scenarios.length} related scenario(s)</span>}
                </li>
              );
            })}
          </ul>
        </>
      )}
    </section>
  );
}
