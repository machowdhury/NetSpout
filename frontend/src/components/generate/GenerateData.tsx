import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { compatApi, type CompatCatalog, type Preview, type SourcetypeEntry } from '../../lib/compatApi';
import { explorerApi } from '../../lib/explorerApi';
import { controlRun, getRun, startRun, verifyRun, type RunSnapshot } from '../../lib/runsApi';
import { LiveDeliveryMonitor } from '../monitor/LiveDeliveryMonitor';
import './simple.css';

const FINAL = ['COMPLETED', 'STOPPED', 'FAILED', 'INTERRUPTED'];
type Mode = 'finite' | 'continuous';

function Status({ s, label }: { s: string; label: string }) {
  return <span className={`sx-status sx-status--${s}`} data-testid="status-badge" data-status={s}>{label}</span>;
}

// Plain-language answer to "did Splunk receive it?". HEC acceptance and a search that finds the events are reported as different things.
function Outcome({ runId, destinationIndex }: { runId: string; destinationIndex: string }) {
  const [run, setRun] = useState<RunSnapshot | null>(null);
  const [verify, setVerify] = useState<{ status: string; indexed?: number | null; accepted?: number; error?: string | null } | null>(null);
  const [verifying, setVerifying] = useState(false);
  const attempts = useRef(0);
  useEffect(() => { setRun(null); setVerify(null); attempts.current = 0; }, [runId]);
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
    try { const v = await verifyRun(runId); setVerify(v); return v; } catch (e) { const v = { status: 'ERROR', error: e instanceof Error ? e.message : String(e) }; setVerify(v); return v; } finally { setVerifying(false); }
  }, [runId]);
  // After delivery ends, search Splunk for this run's events; indexing can lag, so a few retries before the answer stands.
  useEffect(() => {
    if (!final || accepted === 0 || verify?.status === 'VERIFIED') return undefined;
    if (verify && !['INCOMPLETE', 'NOT_RUN'].includes(verify.status)) return undefined;
    if (attempts.current >= 6) return undefined;
    const t = window.setTimeout(() => { attempts.current += 1; void doVerify(); }, verify ? 5000 : 2500);
    return () => window.clearTimeout(t);
  }, [final, accepted, verify, doVerify]);
  if (!run) return <div className="sx-box" data-testid="outcome">Starting…</div>;
  const c = run.counters;
  let tone = '', text = '';
  if (!final) text = `Sending… ${c.accepted.toLocaleString()} accepted by Splunk HEC so far${c.rejected ? `, ${c.rejected} rejected` : ''}${run.mode === 'continuous' ? ' (streaming until stopped)' : ''}.`;
  else if (run.state === 'FAILED' || (c.generated > 0 && c.accepted === 0)) { tone = 'sx-bad'; text = `Splunk did not receive these events. ${run.error ?? run.recent_errors?.slice(-1)[0]?.message ?? 'The destination rejected or could not be reached.'}`; }
  else if (c.rejected > 0 || c.unknown > 0) { tone = 'sx-bad'; text = `Only ${c.accepted} of ${c.generated} events were accepted (${c.rejected} rejected, ${c.unknown} unconfirmed). ${run.recent_errors?.slice(-1)[0]?.message ?? ''}`; }
  else if (verify?.status === 'VERIFIED') { tone = 'sx-ok'; text = `Verified: ${verify.indexed} of ${c.accepted} events were found in Splunk (index ${destinationIndex}).`; }
  else if (verify?.status === 'INCOMPLETE') text = `Splunk accepted ${c.accepted} events; ${verify.indexed ?? 0} are searchable so far. Indexing can lag; still checking.`;
  else if (verify && ['ERROR', 'NOT_RUN', 'UNAVAILABLE', 'FAILED'].includes(verify.status)) { tone = 'sx-bad'; text = `Splunk accepted ${c.accepted} events, but this app could not confirm they are searchable: ${verify.error ?? verify.status}. Accepted is not the same as indexed.`; }
  else text = `Splunk accepted ${c.accepted} of ${c.generated} events. Checking that they are searchable…`;
  return (
    <div className="sx-box" data-testid="outcome" role="status">
      <p className={tone} data-testid="outcome-text">{text}</p>
      <div className="sx-row">
        {run.controls.stop && <button type="button" onClick={() => void controlRun(runId, 'stop')}>Stop</button>}
        {final && accepted > 0 && <button type="button" disabled={verifying} onClick={() => void doVerify()}>{verifying ? 'Checking…' : 'Verify in Splunk again'}</button>}
      </div>
    </div>
  );
}

export function GenerateData() {
  const [catalog, setCatalog] = useState<CompatCatalog | null>(null);
  const [loadErr, setLoadErr] = useState('');
  const [showAll, setShowAll] = useState(false);
  const [vendorId, setVendorId] = useState('');
  const [product, setProduct] = useState('');
  const [sourcetype, setSourcetype] = useState('');
  const [count, setCount] = useState(20);
  const [mode, setMode] = useState<Mode>('finite');
  const [eps, setEps] = useState(5);
  const [indexes, setIndexes] = useState<string[]>([]);
  const [configured, setConfigured] = useState<boolean | null>(null);
  const [index, setIndex] = useState('');
  const [preview, setPreview] = useState<Preview | null>(null);
  const [previewErr, setPreviewErr] = useState('');
  const [previewing, setPreviewing] = useState(false);
  const [runId, setRunId] = useState<string | null>(null);
  const [startErr, setStartErr] = useState('');
  const [details, setDetails] = useState(false);

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
  // Several catalog vendors share a display name (for example the Cisco product families); the id tells them apart.
  const vendorLabel = (v: { id: string; name: string }) => (vendors.filter((x) => x.name === v.name).length > 1 ? `${v.name} (${v.id})` : v.name);
  const vendor = vendors.find((v) => v.id === vendorId) ?? vendors[0];
  const products = useMemo(() => (vendor ? vendor.products.filter((p) => showAll || p.best === 0) : []), [vendor, showAll]);
  const prod = products.find((p) => p.name === product) ?? products[0];
  const entries: SourcetypeEntry[] = useMemo(() => (prod ? prod.sourcetypes.filter((s) => showAll || s.status === 'VERIFIED') : []), [prod, showAll]);
  const entry = entries.find((s) => s.sourcetype === sourcetype) ?? entries[0];

  // The selects show derived values (first valid item when the stored choice is gone); state is only written by the user's own changes, so no effect can overwrite a click.

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

  const blockedReason = entry?.block?.message ?? (configured === false ? 'No Splunk destination is set up yet. Open Connections, save a destination, then come back.' : '');
  const generate = async () => {
    if (!entry || !vendor) return;
    setStartErr(''); setRunId(null);
    try {
      const r = await startRun({ kind: 'sourcetype', target: entry.sourcetype, vendor_id: vendor.id, index: entry.kind === 'event' ? index || undefined : undefined, eps, mode, count: mode === 'finite' ? count : undefined });
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
      {loadErr && <div className="sx-box sx-blocked" role="alert">The catalog could not be loaded: {loadErr}</div>}
      <section className="sx-box" aria-label="Choose a sourcetype">
        <span className="sx-step">1 · Choose</span>
        <div className="sx-row">
          <label>Vendor<select data-testid="vendor" value={vendor?.id ?? ''} onChange={(e) => { setVendorId(e.target.value); setProduct(''); setSourcetype(''); }}>
            {vendors.map((v) => <option key={v.id} value={v.id}>{vendorLabel(v)}{showAll && v.best === 0 ? ' — verified' : ''}</option>)}
          </select></label>
          <label>Product<select data-testid="product" value={prod?.name ?? ''} onChange={(e) => { setProduct(e.target.value); setSourcetype(''); }}>
            {products.map((p) => <option key={p.name} value={p.name}>{p.name}</option>)}
          </select></label>
          <label>Sourcetype<select data-testid="sourcetype" value={entry?.sourcetype ?? ''} onChange={(e) => setSourcetype(e.target.value)}>
            {entries.map((s) => <option key={s.sourcetype} value={s.sourcetype}>{s.sourcetype}{showAll ? ` — ${s.status_label}` : ''}</option>)}
          </select></label>
        </div>
        <label className="sx-check"><input type="checkbox" data-testid="show-all" checked={showAll} onChange={(e) => setShowAll(e.target.checked)} /> Also show unverified and unsupported entries ({totalCount - verifiedCount} more; {verifiedCount} verified)</label>
        {entry && (
          <div data-testid="selection-status">
            <Status s={entry.status} label={entry.status_label} />
            {entry.status === 'VERIFIED' && entry.evidence && <p className="sx-muted">Tested in a live Splunk with {entry.evidence.add_on}: {entry.evidence.live_checks.PASS} checks passed, {entry.evidence.live_checks.FAIL} failed{entry.evidence.live_checks.NOT_RUN ? `, ${entry.evidence.live_checks.NOT_RUN} could not be run` : ''}. Only representative events were tested.</p>}
            {entry.notes.map((n) => <p className="sx-muted" key={n}>{n}</p>)}
          </div>
        )}
      </section>

      {entry?.block ? (
        <section className="sx-box sx-blocked" data-testid="blocked" role="alert">
          <b>This selection cannot generate data.</b>
          <p>{entry.block.message}</p>
        </section>
      ) : (
        <section className="sx-box" aria-label="Preview">
          <span className="sx-step">2 · Preview</span>
          {previewing && <p className="sx-muted">Generating a preview…</p>}
          {previewErr && <p className="sx-bad" role="alert">{previewErr}</p>}
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

      {!entry?.block && <section className="sx-box" aria-label="Generate">
        <span className="sx-step">3 · Generate</span>
        <div className="sx-row">
          <label>Send<select value={mode} onChange={(e) => setMode(e.target.value as Mode)} data-testid="mode"><option value="finite">A set number of events</option><option value="continuous">Keep streaming until I stop</option></select></label>
          {mode === 'finite' && <label>Events<input type="number" min={1} max={1000} value={count} data-testid="count" onChange={(e) => setCount(Math.max(1, Math.min(1000, Number(e.target.value) || 1)))} /></label>}
          <label>Events per second<input type="number" min={1} max={200} value={eps} onChange={(e) => setEps(Math.max(1, Math.min(200, Number(e.target.value) || 1)))} /></label>
          {entry?.kind === 'metric'
            ? <label>Index<input type="text" value="metric index from Connections" readOnly /></label>
            : <label>Index<select value={index} onChange={(e) => setIndex(e.target.value)} data-testid="index">{indexes.filter((i) => !/metric/i.test(i)).map((i) => <option key={i}>{i}</option>)}</select></label>}
        </div>
        <div className="sx-row">
          <button type="button" className="sx-primary" data-testid="generate" disabled={!!blockedReason || !entry} onClick={() => void generate()}>Generate and send to Splunk</button>
          {configured === false && <a href="#/system/connections">Set up Connections</a>}
        </div>
        {blockedReason && !entry?.block && <p className="sx-bad" data-testid="cannot-run">{blockedReason}</p>}
        {startErr && <p className="sx-bad" role="alert" data-testid="start-error">{startErr}</p>}
      </section>}

      {runId && (
        <section aria-label="Result" className="sx-box">
          <span className="sx-step">4 · Did Splunk receive it?</span>
          <Outcome runId={runId} destinationIndex={entry?.kind === 'metric' ? 'metric index' : index} />
          <details open={details} onToggle={(e) => setDetails((e.target as HTMLDetailsElement).open)}><summary>Delivery details</summary>{details && <LiveDeliveryMonitor runId={runId} />}</details>
        </section>
      )}
    </div>
  );
}
