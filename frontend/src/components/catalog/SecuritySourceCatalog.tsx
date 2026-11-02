import { useEffect, useMemo, useState } from 'react';
import { CircleAlert, Database, Play, Search, ShieldCheck } from 'lucide-react';
import { fetchJson } from '../../lib/api';
import type { ExperienceMode } from '../../app/navigation';
import type { SecuritySource, SecuritySourceResponse } from '../../types/release';

function badge(status: string) {
  return `source-status source-status--${status.toLowerCase().replaceAll('_', '-')}`;
}

export function SecuritySourceCatalog({ mode }: { mode: ExperienceMode }) {
  const [data, setData] = useState<SecuritySourceResponse | null>(null);
  const [error, setError] = useState('');
  const [query, setQuery] = useState('');
  const [domain, setDomain] = useState('all');
  const [status, setStatus] = useState('all');
  const [transport, setTransport] = useState('all');
  const [selected, setSelected] = useState<SecuritySource | null>(null);

  useEffect(() => {
    fetchJson<SecuritySourceResponse>('/api/security-sources')
      .then((response) => {
        setData(response);
        setSelected(response.sources[0] ?? null);
      })
      .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : 'Catalog unavailable'));
  }, []);

  const filtered = useMemo(() => {
    if (!data) return [];
    const needle = query.trim().toLowerCase();
    return data.sources.filter((source) => (
      (!needle || `${source.vendor} ${source.product} ${source.event_family} ${source.splunk_sourcetypes.join(' ')}`.toLowerCase().includes(needle))
      && (domain === 'all' || source.domain === domain)
      && (status === 'all' || source.status === status)
      && (transport === 'all' || source.transports.includes(transport))
    ));
  }, [data, domain, query, status, transport]);

  if (error) return <div className="generation-alert generation-alert--error" role="alert"><CircleAlert /> Security source catalog unavailable: {error}</div>;
  if (!data) return <div className="generation-state">Loading audited security source coverage…</div>;

  const domains = [...new Set(data.sources.map((source) => source.domain))].sort();
  const transports = [...new Set(data.sources.flatMap((source) => source.transports))].sort();

  return (
    <div className="workspace-stack source-catalog" data-testid="security-source-catalog">
      <header className="generation-hero">
        <div>
          <span className="generation-eyebrow">Release-candidate coverage</span>
          <h2>Security Event Source Catalog</h2>
          <p>Browse source support independently from scenarios. Maturity is based on source contracts and evidence, never vendor name recognition.</p>
        </div>
        <div className="generation-hero__summary">
          <span><strong>{data.summary.source_count}</strong> audited families</span>
          <span><strong>{data.summary.runnable_count}</strong> bounded generation paths</span>
        </div>
      </header>

      <section className="source-toolbar" aria-label="Security source filters">
        <label className="generation-search"><Search /><input aria-label="Search security sources" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Vendor, product, event family, sourcetype…" /></label>
        <select aria-label="Filter source domain" value={domain} onChange={(event) => setDomain(event.target.value)}>
          <option value="all">All domains</option>
          {domains.map((item) => <option key={item}>{item}</option>)}
        </select>
        <select aria-label="Filter source maturity" value={status} onChange={(event) => setStatus(event.target.value)}>
          <option value="all">All maturity states</option>
          {Object.keys(data.summary.status_counts).sort().map((item) => <option key={item}>{item}</option>)}
        </select>
        <select aria-label="Filter source transport" value={transport} onChange={(event) => setTransport(event.target.value)}>
          <option value="all">All transports</option>
          {transports.map((item) => <option key={item}>{item}</option>)}
        </select>
      </section>

      <div className="source-layout">
        <section className="source-list" aria-label={`${filtered.length} matching security sources`}>
          {filtered.length === 0 && <div className="generation-empty">No sources match these filters.</div>}
          {filtered.map((source) => (
            <button type="button" className={selected?.coverage_id === source.coverage_id ? 'source-card is-selected' : 'source-card'} key={source.coverage_id} onClick={() => setSelected(source)}>
              <div><strong>{source.product}</strong><span>{source.vendor} · {source.event_family}</span></div>
              <span className={badge(source.status)}>{source.status.replaceAll('_', ' ')}</span>
            </button>
          ))}
        </section>

        {selected && (
          <article className="source-detail" aria-live="polite">
            <header><div><span>{selected.domain}</span><h3>{selected.product}</h3><p>{selected.vendor} · {selected.product_version_scope}</p></div><span className={badge(selected.status)}>{selected.status.replaceAll('_', ' ')}</span></header>
            <dl className="source-facts">
              <div><dt>Event family</dt><dd>{selected.event_family}</dd></div>
              <div><dt>Native format</dt><dd>{selected.native_format}</dd></div>
              <div><dt>Transport</dt><dd>{selected.transports.join(', ') || 'NOT ESTABLISHED'}</dd></div>
              <div><dt>Splunk sourcetype</dt><dd>{selected.splunk_sourcetypes.join(', ') || 'NOT ESTABLISHED'}</dd></div>
              <div><dt>Technology Add-on</dt><dd>{selected.technology_add_on}</dd></div>
              <div><dt>CIM mapping</dt><dd>{selected.cim_status}</dd></div>
              <div><dt>Runtime maturity</dt><dd>{selected.runtime_maturity}</dd></div>
              <div><dt>Splunk observation</dt><dd>{selected.splunk_observation}</dd></div>
            </dl>
            <section><h4><Database /> Required fields</h4><p>{selected.required_fields.join(', ') || 'No validated field contract.'}</p></section>
            <section><h4><ShieldCheck /> Provenance and evidence</h4><p>{[...selected.contract_provenance, ...selected.validation_evidence].join(' · ') || 'No validation evidence.'}</p></section>
            <section><h4>Related scenarios</h4><p>{selected.scenario_ids.join(', ') || 'No supported scenarios.'}</p></section>
            {mode === 'advanced' && <section><h4>Distribution</h4><p>{selected.distribution_availability.join(', ') || 'Not distributed'}</p></section>}
            <section>
              <h4>Known limitations</h4>
              <p>{selected.known_limitations.join(' ') || 'No additional limitations recorded.'}</p>
            </section>
            {selected.sample_generation.runnable ? (
              <a className="generation-primary source-run-link" href="#/generate/quick"><Play /> Generate bounded sample</a>
            ) : (
              <div className="generation-alert generation-alert--blocked"><CircleAlert /> {selected.sample_generation.reason}</div>
            )}
          </article>
        )}
      </div>
    </div>
  );
}
