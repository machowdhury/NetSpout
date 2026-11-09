import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { compatApi, type CompatCatalog, type Preview, type SourcetypeEntry } from '../../lib/compatApi';
import { explorerApi } from '../../lib/explorerApi';
import { startRun } from '../../lib/runsApi';
import { AuthorizeDestination, useDestinationAuthorization } from '../../lib/authorize';
import { Outcome } from './Outcome';
import { EngineNotice } from './EngineNotice';
import { useEngineStatus } from '../../lib/engineApi';
import { LiveDeliveryMonitor } from '../monitor/LiveDeliveryMonitor';
import './simple.css';

type Mode = 'finite' | 'continuous';
type Selected = { vendor_id: string; vendorName: string; product: string; sourcetype: string; kind: string; status: string; status_label: string; count: number };
type MultiPreview = { loading?: boolean; error?: string; raw?: string[]; target?: string };

const FRIENDLY_VENDOR: Record<string, string> = {
  cisco_aci: 'Cisco ACI', cisco_asa: 'Cisco ASA and Cloud Security', cisco_catalyst: 'Cisco Catalyst Center', cisco_intersight: 'Cisco Intersight',
  cisco_ios: 'Cisco IOS, IOS-XE and IOS-XR', cisco_ise: 'Cisco ISE', cisco_sdwan: 'Cisco SD-WAN',
};

function Status({ s, label }: { s: string; label: string }) {
  return <span className={`sx-status sx-status--${s}`} data-testid="status-badge" data-status={s}>{label}</span>;
}

export function GenerateData() {
  const [catalog, setCatalog] = useState<CompatCatalog | null>(null);
  const [loadErr, setLoadErr] = useState('');
  const [showAll, setShowAll] = useState(false);
  const [vendorId, setVendorId] = useState('');
  const [product, setProduct] = useState('');
  const [productQuery, setProductQuery] = useState('');
  const [sourcetype, setSourcetype] = useState('');
  const [count, setCount] = useState(20);
  const [mode, setMode] = useState<Mode>('finite');
  const [eps, setEps] = useState(5);
  const [indexes, setIndexes] = useState<string[]>([]);
  const auth = useDestinationAuthorization();
  const [configured, setConfigured] = useState<boolean | null>(null);
  const [index, setIndex] = useState('');
  const [preview, setPreview] = useState<Preview | null>(null);
  const [previewErr, setPreviewErr] = useState('');
  const [previewing, setPreviewing] = useState(false);
  const [runId, setRunId] = useState<string | null>(null);
  const [startErr, setStartErr] = useState('');
  const [details, setDetails] = useState(false);
  const engine = useEngineStatus();
  const [several, setSeveral] = useState(false);                      // false: one sourcetype; true: several sourcetypes in one run
  const [selected, setSelected] = useState<Selected[]>([]);
  const [previews, setPreviews] = useState<Record<string, MultiPreview>>({});

  useEffect(() => { compatApi.catalog().then(setCatalog, (e) => setLoadErr(e instanceof Error ? e.message : String(e))); }, []);
  useEffect(() => {
    explorerApi.setup().then((s) => {
      setConfigured(!!s.configured);
      const list = s.indexes ?? [];
      setIndexes(list);
      setIndex((cur) => cur || list.find((i) => !/metric/i.test(i)) || list[0] || '');
    }, () => setConfigured(false));
  }, []);

  const vendors = useMemo(() => {
    if (!catalog) return [];
    return catalog.vendors.filter((v) => showAll || v.best === 0);
  }, [catalog, showAll]);
  // Several catalog vendors share a display name (the Cisco product families all say "Cisco Systems"), so those get a name a person recognises.
  const vendorLabel = (v: { id: string; name: string }) => FRIENDLY_VENDOR[v.id] ?? (catalog && catalog.vendors.filter((x) => x.name === v.name).length > 1 ? `${v.name} — ${v.id.replace(/^[a-z]+_/, '').replace(/_/g, ' ')}` : v.name);
  const vendor = vendors.find((v) => v.id === vendorId) ?? vendors[0];
  const allProducts = useMemo(() => (vendor ? vendor.products.filter((p) => showAll || p.best === 0) : []), [vendor, showAll]);
  // Some vendors have dozens of products (SD-WAN has 41), so the list can be narrowed by typing.
  const products = useMemo(() => allProducts.filter((p) => p.name.toLowerCase().includes(productQuery.trim().toLowerCase())), [allProducts, productQuery]);
  const prod = products.find((p) => p.name === product) ?? products[0];
  const entries: SourcetypeEntry[] = useMemo(() => (prod ? prod.sourcetypes.filter((s) => showAll || s.status === 'VERIFIED') : []), [prod, showAll]);
  const entry = entries.find((s) => s.sourcetype === sourcetype) ?? entries[0];

  // The selects show derived values (first valid item when the stored choice is gone); state is only written by the user's own changes, so no effect can overwrite a click.

  const loadMultiPreview = useCallback(async (v: string, st: string) => {
    setPreviews((p) => ({ ...p, [st]: { loading: true } }));
    try { const pv = await compatApi.preview(v, st, 2, index || undefined); setPreviews((p) => ({ ...p, [st]: { raw: pv.events.map((e) => (e.kind === 'metric' ? Object.entries(e.metrics ?? {}).map(([k, x]) => `${k} = ${x}`).join('\n') : e.raw ?? '')), target: pv.events[0]?.index } })); }
    catch (e) { setPreviews((p) => ({ ...p, [st]: { error: e instanceof Error ? e.message : String(e) } })); }
  }, [index]);
  const addSource = () => {
    if (!entry || !vendor || entry.block || selected.some((x) => x.sourcetype === entry.sourcetype)) return;
    setSelected((cur) => [...cur, { vendor_id: vendor.id, vendorName: vendorLabel(vendor), product: prod?.name ?? '', sourcetype: entry.sourcetype, kind: entry.kind ?? 'event', status: entry.status, status_label: entry.status_label, count: 20 }]);
    void loadMultiPreview(vendor.id, entry.sourcetype);
  };
  const removeSource = (st: string) => { setSelected((cur) => cur.filter((x) => x.sourcetype !== st)); setPreviews(({ [st]: _gone, ...rest }) => rest); };
  const setSourceCount = (st: string, n: number) => setSelected((cur) => cur.map((x) => (x.sourcetype === st ? { ...x, count: Math.max(1, Math.min(1000, n || 1)) } : x)));
  const multiTotal = selected.reduce((n, x) => n + x.count, 0);
  const setTotal = (t: number) => setSelected((cur) => { const n = cur.length || 1, total = Math.max(n, Math.min(1000 * n, t || n)); return cur.map((x, i) => ({ ...x, count: Math.floor(total / n) + (i < total % n ? 1 : 0) })); });

  const previewSeq = useRef(0);
  const loadPreview = useCallback(async () => {
    if (!entry || !vendor) return;
    const seq = ++previewSeq.current;               // a slow answer for a previous selection must never replace the current one
    setPreviewErr(''); setPreview(null);
    if (entry.block) return;
    setPreviewing(true);
    try { const p = await compatApi.preview(vendor.id, entry.sourcetype, 3, index || undefined); if (seq === previewSeq.current) setPreview(p); }
    catch (e) { if (seq === previewSeq.current) setPreviewErr(e instanceof Error ? e.message : String(e)); }
    finally { if (seq === previewSeq.current) setPreviewing(false); }
  }, [entry, vendor, index]);
  // Only ever show a preview that belongs to the current selection.
  const shown = preview && entry && preview.sourcetype === entry.sourcetype && preview.vendor_id === vendor?.id ? preview : null;
  useEffect(() => { void loadPreview(); }, [entry?.sourcetype, vendor?.id]);   // eslint-disable-line react-hooks/exhaustive-deps

  const engineReason = engine && !engine.connected ? engine.message : '';
  const multiReason = engineReason || (configured === false ? 'No Splunk destination is set up yet. Open Connections, save a destination, then come back.'
    : selected.length === 0 ? 'Add at least one sourcetype to the run.'
    : selected.some((x) => previews[x.sourcetype]?.error) ? 'A preview failed, so nothing is sent. Remove that sourcetype or use New preview.' : '');
  const blockedReason = engineReason || (entry?.block?.message ?? (configured === false ? 'No Splunk destination is set up yet. Open Connections, save a destination, then come back.'
    : previewErr ? 'The preview could not be generated, so nothing is sent. Use New preview; if it keeps failing the selected source cannot be used right now.' : ''));
  const generate = async () => {
    if (several) {
      setStartErr(''); setRunId(null);
      try {
        const r = await startRun({ kind: 'multi', sources: selected.map((x) => ({ vendor_id: x.vendor_id, sourcetype: x.sourcetype, count: x.count })), index: index || undefined, eps, mode });
        setRunId(r.run_id); setDetails(false);
      } catch (e) { setStartErr(e instanceof Error ? e.message : String(e)); }
      return;
    }
    if (!entry || !vendor) return;
    setStartErr(''); setRunId(null);
    try {
      const r = await startRun({ kind: 'sourcetype', target: entry.sourcetype, vendor_id: vendor.id, index: index || undefined, eps, mode, count: mode === 'finite' ? count : undefined });
      setRunId(r.run_id); setDetails(false);
    } catch (e) { setStartErr(e instanceof Error ? e.message : String(e)); }
  };
  const verifiedCount = catalog ? catalog.vendors.reduce((n, v) => n + v.products.reduce((m, p) => m + p.sourcetypes.filter((s) => s.status === 'VERIFIED').length, 0), 0) : 0;
  const totalCount = catalog ? catalog.vendors.reduce((n, v) => n + v.products.reduce((m, p) => m + p.sourcetypes.length, 0), 0) : 0;

  return (
    <div className="sx" data-testid="generate-data">
      <div>
        <h2>Generate data</h2>
        <p className="sx-muted">Pick a source, check the telemetry, send it to Splunk, and see whether Splunk received it.</p>
      </div>
      <EngineNotice status={engine} />
      {loadErr && !engine && <div className="sx-box sx-blocked" role="alert">The catalog could not be loaded: {loadErr}</div>}
      <div className="sx-row" role="radiogroup" aria-label="How many sourcetypes">
        <label className="sx-check"><input type="radio" name="source-mode" data-testid="mode-single" checked={!several} onChange={() => { setSeveral(false); setRunId(null); }} /> One sourcetype</label>
        <label className="sx-check"><input type="radio" name="source-mode" data-testid="mode-multi" checked={several} onChange={() => { setSeveral(true); setRunId(null); }} /> Several sourcetypes</label>
      </div>
      <section className="sx-box" aria-label="Choose a sourcetype">
        <span className="sx-step">1 · Choose</span>
        <div className="sx-row">
          <label>Vendor<select data-testid="vendor" value={vendor?.id ?? ''} onChange={(e) => { setVendorId(e.target.value); setProduct(''); setSourcetype(''); setProductQuery(''); }}>
            {vendors.map((v) => <option key={v.id} value={v.id}>{vendorLabel(v)}{showAll && v.best === 0 ? ' — verified' : ''}</option>)}
          </select></label>
          {allProducts.length > 8 && <label>Find a product<input type="search" data-testid="product-search" value={productQuery} placeholder={`Search ${allProducts.length} products`} onChange={(e) => { setProductQuery(e.target.value); setProduct(''); setSourcetype(''); }} /></label>}
          <label>Product<select data-testid="product" value={prod?.name ?? ''} onChange={(e) => { setProduct(e.target.value); setSourcetype(''); }}>
            {products.length === 0 && <option value="">No product matches “{productQuery}”</option>}
            {products.map((p) => <option key={p.name} value={p.name}>{p.name}</option>)}
          </select></label>
          <label>Sourcetype<select data-testid="sourcetype" value={entry?.sourcetype ?? ''} onChange={(e) => setSourcetype(e.target.value)}>
            {entries.map((s) => <option key={s.sourcetype} value={s.sourcetype}>{s.sourcetype}{showAll ? ` — ${s.status_label}` : ''}</option>)}
          </select></label>
        </div>
        <label className="sx-check"><input type="checkbox" data-testid="show-all" checked={showAll} onChange={(e) => setShowAll(e.target.checked)} /> Also show sources that are not yet tested in Splunk or cannot send data ({totalCount - verifiedCount} more; {verifiedCount} are tested)</label>
        {entry && (
          <div data-testid="selection-status">
            <Status s={entry.status} label={entry.status_label} />
            {entry.status === 'VERIFIED' && entry.evidence && <p className="sx-muted">Tested in a live Splunk with {entry.evidence.add_on}: {entry.evidence.live_checks.PASS} checks passed, {entry.evidence.live_checks.FAIL} failed{entry.evidence.live_checks.NOT_RUN ? `, ${entry.evidence.live_checks.NOT_RUN} could not be run` : ''}. Only representative events were tested.</p>}
            {entry.notes.map((n) => <p className="sx-muted" key={n}>{n}</p>)}
          </div>
        )}
        {several && <div className="sx-row"><button type="button" data-testid="add-source" disabled={!entry || !!entry.block || selected.some((x) => x.sourcetype === entry?.sourcetype)} onClick={addSource}>{entry && selected.some((x) => x.sourcetype === entry.sourcetype) ? 'Already in this run' : 'Add to this run'}</button>{entry?.block && <span className="sx-bad" data-testid="add-blocked">This sourcetype cannot send data: {entry.block.message}</span>}</div>}
      </section>

      {several && (
        <section className="sx-box" aria-label="Selected sourcetypes" data-testid="selected-sources">
          <span className="sx-step">Selected for this run ({selected.length})</span>
          {selected.length === 0 && <p className="sx-muted">Choose a vendor, product and sourcetype above, then use Add to this run. You can mix vendors and products.</p>}
          {selected.length > 0 && (
            <table className="sx-table"><thead><tr><th>Vendor</th><th>Product</th><th>Sourcetype</th><th>Status</th><th>Goes to</th><th>Events</th><th /></tr></thead>
              <tbody>{selected.map((x) => (
                <tr key={x.sourcetype} data-testid={`selected-${x.sourcetype}`}>
                  <td>{x.vendorName}</td><td>{x.product}</td><td><code>{x.sourcetype}</code></td>
                  <td><span className={`sx-status sx-status--${x.status}`}>{x.status_label}</span></td>
                  <td>{x.kind === 'metric' ? 'the metric index' : <>index <code>{index}</code></>}</td>
                  <td><input type="number" min={1} max={1000} value={x.count} aria-label={`Events for ${x.sourcetype}`} data-testid={`count-${x.sourcetype}`} onChange={(e) => setSourceCount(x.sourcetype, Number(e.target.value))} /></td>
                  <td><button type="button" data-testid={`remove-${x.sourcetype}`} onClick={() => removeSource(x.sourcetype)}>Remove</button></td>
                </tr>))}</tbody></table>
          )}
          {selected.length > 0 && <div className="sx-row"><label>Total events<input type="number" min={selected.length} data-testid="total-count" value={multiTotal} onChange={(e) => setTotal(Number(e.target.value))} /></label><span className="sx-muted">Changing the total splits it evenly; each row can still be set on its own.</span></div>}
        </section>
      )}

      {several ? (
        <section className="sx-box" aria-label="Preview" data-testid="multi-preview">
          <span className="sx-step">2 · Preview</span>
          {selected.length === 0 && <p className="sx-muted">Previews appear here for every sourcetype you add.</p>}
          {selected.map((x) => { const pv = previews[x.sourcetype]; return (
            <div key={x.sourcetype} data-testid={`preview-${x.sourcetype}`}>
              <p className="sx-muted"><code>{x.sourcetype}</code>{pv?.target ? <> → {x.kind === 'metric' ? 'metric index' : 'index'} <code>{pv.target}</code></> : null}</p>
              {pv?.loading && <p className="sx-muted">Generating a preview…</p>}
              {pv?.error && <div><p className="sx-bad" role="alert">Preview failed: {pv.error}</p><button type="button" onClick={() => void loadMultiPreview(x.vendor_id, x.sourcetype)}>New preview</button></div>}
              {pv?.raw?.map((raw, i) => <pre className="sx-pre" key={i} data-testid="preview-raw">{raw}</pre>)}
            </div>); })}
        </section>
      ) : entry?.block ? (
        <section className="sx-box sx-blocked" data-testid="blocked" role="alert">
          <b>This selection cannot generate data.</b>
          <p>{entry.block.message}</p>
        </section>
      ) : (
        <section className="sx-box" aria-label="Preview">
          <span className="sx-step">2 · Preview</span>
          {previewing && <p className="sx-muted">Generating a preview…</p>}
          {previewErr && <div><p className="sx-bad" role="alert" data-testid="preview-error">Preview failed: {previewErr}</p><button type="button" onClick={() => void loadPreview()} disabled={previewing}>New preview</button></div>}
          {shown && (
            <div data-testid="preview">
              <p className="sx-muted">Sourcetype that will be sent: <code data-testid="preview-sourcetype">{shown.events[0]?.sourcetype}</code> · {shown.events[0]?.kind === 'metric' ? 'metric index' : 'index'} <code>{shown.events[0]?.index}</code> · generator: {shown.generator_mode}</p>
              {shown.events.map((e, i) => (e.kind === 'metric'
                ? <pre className="sx-pre" key={i} data-testid="preview-raw">{Object.entries(e.metrics ?? {}).map(([k, v]) => `${k} = ${v}`).join('\n')}</pre>
                : <pre className="sx-pre" key={i} data-testid="preview-raw">{e.raw}</pre>))}
              <p className="sx-muted">{shown.disclaimer}</p>
              <button type="button" onClick={() => void loadPreview()} disabled={previewing}>New preview</button>
            </div>
          )}
        </section>
      )}

      {(several || !entry?.block) && <section className="sx-box" aria-label="Generate">
        <span className="sx-step">3 · Generate</span>
        <div className="sx-row">
          {!several && mode === 'finite' && <label>Events<input type="number" min={1} max={1000} value={count} data-testid="count" onChange={(e) => setCount(Math.max(1, Math.min(1000, Number(e.target.value) || 1)))} /></label>}
          {!several && entry?.kind === 'metric'
            ? <label>Index<input type="text" value="the metric index saved in Connections" readOnly /></label>
            : <label>Index<select value={index} onChange={(e) => setIndex(e.target.value)} data-testid="index">{indexes.filter((i) => !/metric/i.test(i)).map((i) => <option key={i}>{i}</option>)}</select></label>}
        </div>
        <details className="sx-advanced"><summary>More options</summary>
          <div className="sx-row">
            <label>Send<select value={mode} onChange={(e) => setMode(e.target.value as Mode)} data-testid="mode"><option value="finite">A set number of events</option><option value="continuous">Keep streaming until I stop</option></select></label>
            <label>Events per second<input type="number" data-testid="eps" min={1} max={200} value={eps} onChange={(e) => setEps(Math.max(1, Math.min(200, Number(e.target.value) || 1)))} /></label>
          </div>
        </details>
        <div className="sx-row">
          <AuthorizeDestination auth={auth} index={index} />
          <button type="button" className="sx-primary" data-testid="generate" disabled={auth.blocked || (several ? !!multiReason : (!!blockedReason || !entry))} onClick={() => void generate()}>Generate and send to Splunk</button>
          {configured === false && <a href="#/system/connections">Set up Connections</a>}
        </div>
        {several ? (multiReason && <p className="sx-bad" data-testid="cannot-run">{multiReason}</p>) : (blockedReason && !entry?.block && <p className="sx-bad" data-testid="cannot-run">{blockedReason}</p>)}
        {startErr && <p className="sx-bad" role="alert" data-testid="start-error">{startErr}</p>}
      </section>}

      {runId && (
        <section aria-label="Result" className="sx-box">
          <span className="sx-step">4 · Did Splunk receive it?</span>
          <Outcome runId={runId} />
          <details open={details} onToggle={(e) => setDetails((e.target as HTMLDetailsElement).open)}><summary>Delivery details</summary>{details && <LiveDeliveryMonitor runId={runId} />}</details>
        </section>
      )}
    </div>
  );
}
