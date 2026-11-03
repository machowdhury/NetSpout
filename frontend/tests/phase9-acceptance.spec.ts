// Phase 9 browser-to-Splunk acceptance. Every journey goes: Connections -> Generate Data -> Preview -> Generate -> verify, through the real browser UI, into the isolated lab Splunk.
// The destination is the REAL lab HEC, reached through scripts/phase9_hec_proxy.py (a recording tap that forwards unchanged except in the failure-path tests).
// Searches that prove the result do not use the app's own verification: they query the lab Splunk directly with the lab credentials (read from the git-ignored lab env file; never logged).
//   PHASE9_API_BASE=http://127.0.0.1:18681 PHASE9_TAP=http://127.0.0.1:19990 PHASE9_LAB_ENV=<.env.lab> PHASE9_ONLY=asa PLAYWRIGHT_BASE_URL=http://127.0.0.1:14273 npx playwright test tests/phase9-acceptance.spec.ts --workers=1 --trace off
// Driven by scripts/phase9_acceptance.py, which installs the matching add-on in the lab for each group. Skipped unless all three variables are set.
import { expect, test, type APIRequestContext, type Locator, type Page } from '@playwright/test';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { request as httpsRequest } from 'node:https';
import { resolve } from 'node:path';

const API = process.env.PHASE9_API_BASE ?? '';
const TAP = process.env.PHASE9_TAP ?? '';
const LAB_ENV = process.env.PHASE9_LAB_ENV ?? '';
const ONLY = process.env.PHASE9_ONLY ?? '';
const SHOTS = resolve(process.cwd(), '..', 'docs', 'verification', 'evidence', 'phase9_ui');
const EVID = resolve(process.cwd(), '..', 'docs', 'verification', 'evidence', 'phase9');
test.skip(!API || !TAP || !LAB_ENV, 'set PHASE9_API_BASE, PHASE9_TAP and PHASE9_LAB_ENV (isolated backend, recording tap, lab env file)');
mkdirSync(SHOTS, { recursive: true });
mkdirSync(EVID, { recursive: true });

const lab: Record<string, string> = LAB_ENV ? Object.fromEntries(readFileSync(LAB_ENV, 'utf8').split('\n').filter((l) => l.includes('=')).map((l) => [l.slice(0, l.indexOf('=')).trim(), l.slice(l.indexOf('=') + 1).trim()])) : {};
if (LAB_ENV) { if (lab.LAB_MGMT_PORT !== '19191' || lab.LAB_HEC_PORT !== '19088') throw new Error('Phase 9 only runs against the isolated TA-validation lab (mgmt 19191, HEC 19088)'); }
const TAP_HEC = `${TAP}/services/collector`;
const SEARCH_URL = 'https://127.0.0.1:19191/services/search/jobs/export';
const EVENT_INDEX = 'ta_validation';
const METRIC_INDEX = 'cisco_metrics';
const group = (g: string) => test.skip(!!ONLY && ONLY !== g, `group ${g} is not selected`);

// ------------------------------------------------------------------------------------------------------------------------------ helpers
function splunk(search: string, earliest = '-3h'): Promise<Array<Record<string, any>>> {
  return new Promise((ok, bad) => {
    const body = new URLSearchParams({ search: /^\s*(\||search )/.test(search) ? search : 'search ' + search, output_mode: 'json', earliest_time: earliest, latest_time: '+1h' }).toString();
    const req = httpsRequest({ host: '127.0.0.1', port: 19191, path: '/services/search/jobs/export', method: 'POST', rejectUnauthorized: false, headers: { Authorization: 'Basic ' + Buffer.from('admin:' + lab.LAB_SPLUNK_PASSWORD).toString('base64'), 'Content-Type': 'application/x-www-form-urlencoded', 'Content-Length': Buffer.byteLength(body) } }, (res) => {
      let d = ''; res.on('data', (c) => (d += c)); res.on('end', () => ok(d.split('\n').filter(Boolean).map((l) => { try { return JSON.parse(l); } catch { return null; } }).filter((x) => x && x.result).map((x) => x.result)));
    });
    req.on('error', bad); req.write(body); req.end();
  });
}
async function until<T>(fn: () => Promise<T>, good: (v: T) => boolean, ms = 90_000, every = 3000): Promise<T> {
  const end = Date.now() + ms; let v = await fn();
  while (!good(v) && Date.now() < end) { await new Promise((r) => setTimeout(r, every)); v = await fn(); }
  return v;
}
const open = async (page: Page, route: string) => { await page.setViewportSize({ width: 1280, height: 1500 }); await page.goto(`/?api_base=${encodeURIComponent(API)}#${route}`); };
const secret = async (loc: Locator, value: string) => { try { await loc.fill(value); } catch (e) { throw new Error('could not fill a secret field: ' + String((e as Error).message).split(value).join('***').split('\n').slice(0, 4).join(' | ').slice(0, 300)); } };   // a failing fill must never print the secret
type Cfg = { hec?: string; search?: string; token?: string; secret?: string; eventIndex?: string; metricIndex?: string };
async function configure(page: Page, o: Cfg = {}) {
  await open(page, '/system/connections');
  await expect(page.getByTestId('setup-wizard')).toBeVisible();
  await page.getByLabel('HEC endpoint').fill(o.hec ?? TAP_HEC);
  await page.getByLabel('Search API endpoint').fill(o.search ?? SEARCH_URL);
  await page.getByLabel('Search username').fill('admin');
  await secret(page.locator('input[type=password]').nth(0), o.token ?? lab.LAB_HEC_TOKEN);               // HEC token
  await secret(page.locator('input[type=password]').nth(1), o.secret ?? lab.LAB_SPLUNK_PASSWORD);      // search credential
  await page.getByTestId('event-index').fill(o.eventIndex ?? EVENT_INDEX);
  await page.getByTestId('metric-index').fill(o.metricIndex ?? METRIC_INDEX);
  // what is in the form is what will be saved: checked before the click (secret fields by length only, so a mismatch never prints them)
  await expect(page.getByLabel('HEC endpoint')).toHaveValue(o.hec ?? TAP_HEC);
  await expect(page.getByLabel('Search API endpoint')).toHaveValue(o.search ?? SEARCH_URL);
  await expect(page.getByTestId('event-index')).toHaveValue(o.eventIndex ?? EVENT_INDEX);
  await expect(page.getByTestId('metric-index')).toHaveValue(o.metricIndex ?? METRIC_INDEX);
  expect(await page.locator('input[type=password]').nth(0).evaluate((e, n) => (e as HTMLInputElement).value.length === n, (o.token ?? lab.LAB_HEC_TOKEN).length)).toBe(true);
  expect(await page.locator('input[type=password]').nth(1).evaluate((e, n) => (e as HTMLInputElement).value.length === n, (o.secret ?? lab.LAB_SPLUNK_PASSWORD).length)).toBe(true);
  await page.getByRole('button', { name: 'Save secure configuration' }).click();
  await expect(page.getByTestId('connection-status')).toContainText('A Splunk destination is saved.');
  expect((await (await page.request.get(`${API}/api/setup`)).json()).hec_url).toBe(o.hec ?? TAP_HEC);   // and the server saved exactly that
}
const tapMode = (request: APIRequestContext, m: string, to = 'main') => request.post(`${TAP}/_mode?m=${m}&to=${to}`);
const tapReset = (request: APIRequestContext) => request.post(`${TAP}/_reset`);
type Tapped = { kind: string; sourcetype: string; index: string; host: string; source: string; time: number; run_id: string | null; scenario_id: string | null; phase: string | null; metric_names: string[] | null; dimension_names: string[] | null; metric_values: Record<string, number> | null; run_dims: Record<string, string> | null; upstream_status: number | string; mode: string };
const tapped = async (request: APIRequestContext, runId?: string): Promise<Tapped[]> => { const j = await (await request.get(`${TAP}/_payloads`)).json(); return j.payloads.filter((p: Tapped) => !runId || p.run_id === runId); };
const save = (name: string, o: unknown) => writeFileSync(`${EVID}/${name}.json`, JSON.stringify(o, null, 1) + '\n');
async function startFromUi(page: Page): Promise<string> {
  const [resp] = await Promise.all([page.waitForResponse((r) => r.url().endsWith('/api/runs') && r.request().method() === 'POST'), page.getByTestId('generate').click()]);
  expect(resp.ok()).toBeTruthy();
  return (await resp.json()).run_id as string;
}
const catalog = async (request: APIRequestContext) => (await (await request.get(`${API}/api/compat/catalog`)).json()) as { vendors: Array<{ id: string; name: string; products: Array<{ name: string; sourcetypes: Array<{ sourcetype: string; status: string; status_label: string; block: { code: string; message: string } | null }> }> }> };
const findEntry = async (request: APIRequestContext, st: string) => { const c = await catalog(request); for (const v of c.vendors) for (const p of v.products) for (const s of p.sourcetypes) if (s.sourcetype === st) return { vendor: v.id, product: p.name, entry: s }; throw new Error('not in catalog: ' + st); };
async function pick(page: Page, request: APIRequestContext, st: string) {
  const f = await findEntry(request, st);
  await open(page, '/generate/quick');
  await page.getByTestId('show-all').check();
  await page.getByTestId('vendor').selectOption(f.vendor);
  await page.getByTestId('product').selectOption(f.product);
  await page.getByTestId('sourcetype').selectOption(st);
  return f;
}
const SHADOW = ['action', 'signature', 'status', 'src_ip', 'dest_ip', 'protocol', 'vendor', 'node_type'];

// ------------------------------------------------------------------------------------------------------------------------------ the four established integrations
const CASES = [
  { tag: 'asa', vendor: 'cisco_asa', st: 'cisco:asa', fields: ['message_id', 'vendor_action', 'action', 'src_ip', 'dest_ip'], every: ['message_id'] },
  { tag: 'ios', vendor: 'cisco_ios', st: 'cisco:ios', fields: ['facility', 'severity_id', 'mnemonic'], every: ['facility', 'severity_id', 'mnemonic'] },
  { tag: 'fortinet', vendor: 'fortinet', st: 'fortigate_traffic', fields: ['src_ip', 'dest_ip', 'src_port', 'dest_port', 'transport', 'vendor_action', 'action', 'dvc'], every: ['src_ip', 'dest_ip'] },
  { tag: 'pan', vendor: 'palo_alto', st: 'pan:traffic', fields: ['src_ip', 'dest_ip', 'rule', 'src_zone', 'dest_zone', 'app', 'vendor_action', 'action'], every: ['src_ip', 'dest_ip', 'action'] },
] as const;
const N = 20;

for (const c of CASES) {
  test(`[${c.tag}] Connections, Generate Data, Preview, Generate, Splunk: ${c.st}`, async ({ page, request }) => {
    group(c.tag);
    test.setTimeout(240_000);
    await tapMode(request, 'pass'); await tapReset(request);
    // Connections: the real form, the saved destination, and the single Test connection control
    await configure(page);
    await page.getByTestId('test-connection').click();
    await expect(page.getByTestId('connection-summary')).toContainText('Working:', { timeout: 60_000 });
    if (c.tag === 'asa') await page.screenshot({ path: `${SHOTS}/p9_01_connections_working.png`, fullPage: true });
    // Generate Data: select, preview
    await open(page, '/generate/quick');
    await page.getByTestId('vendor').selectOption(c.vendor);
    await expect(page.getByTestId('sourcetype')).toHaveValue(c.st);
    await expect(page.getByTestId('status-badge')).toHaveText('Verified in Splunk');
    await expect(page.getByTestId('preview-sourcetype')).toHaveText(c.st);
    const previewInfo = (await page.getByTestId('preview').locator('p').first().textContent()) ?? '';
    expect(previewInfo).toContain(EVENT_INDEX);
    const previewRaw = (await page.getByTestId('preview-raw').first().textContent()) ?? '';
    await page.screenshot({ path: `${SHOTS}/p9_02_${c.tag}_selected_and_previewed.png`, fullPage: true });
    // Generate, and read the plain answer
    await page.getByTestId('count').fill(String(N));
    const t0 = Date.now() / 1000;
    const runId = await startFromUi(page);
    await expect(page.getByTestId('outcome-text')).toContainText(`Verified: found ${N} of ${N} events in index ${EVENT_INDEX}`, { timeout: 120_000 });
    await page.screenshot({ path: `${SHOTS}/p9_03_${c.tag}_verified_in_splunk.png`, fullPage: true });
    // 3. exact outgoing sourcetype and index, from the tap
    const out = await tapped(request, runId);
    expect(out.length).toBe(N);
    expect(new Set(out.map((p) => p.sourcetype))).toEqual(new Set([c.st]));
    expect(new Set(out.map((p) => p.index))).toEqual(new Set([EVENT_INDEX]));
    expect(out.every((p) => p.upstream_status === 200)).toBeTruthy();
    // 5-9. independent searches in the lab Splunk
    const base = `index=${EVENT_INDEX} netspout_run_id="${runId}"`;
    const stats = await until(() => splunk(`${base} | stats count min(_time) as t0 max(_time) as t1 values(sourcetype) as st values(index) as ix values(host) as hosts values(source) as src`), (r) => Number(r[0]?.count ?? 0) >= N);
    expect(Number(stats[0].count)).toBe(N);
    expect([].concat(stats[0].st)).toEqual([c.st]);
    expect([].concat(stats[0].ix)).toEqual([EVENT_INDEX]);
    const hostsSplunk = [].concat(stats[0].hosts).sort(); const hostsSent = [...new Set(out.map((p) => p.host))].sort();
    expect(hostsSplunk).toEqual(hostsSent);                                                  // host: what NetSpout sent is what Splunk stored
    const sent = out.map((p) => p.time);
    expect(Number(stats[0].t0)).toBeGreaterThanOrEqual(Math.min(...sent) - 3); expect(Number(stats[0].t1)).toBeLessThanOrEqual(Math.max(...sent) + 3);   // _time is the explicit send time
    expect(Math.min(...sent)).toBeGreaterThanOrEqual(t0 - 5);
    const fieldRows = await splunk(`${base} | stats count as total ${c.fields.map((f) => `count(${f}) as ${f}`).join(' ')}`);
    for (const f of c.fields) expect(Number(fieldRows[0][f]), `TA field ${f} extracted in at least one event`).toBeGreaterThan(0);
    for (const f of c.every) expect(Number(fieldRows[0][f]), `TA field ${f} extracted in every event`).toBe(N);
    // no vendor-field shadowing: NetSpout sends none of the vendor/CIM names as indexed fields (the tap saw the exact HEC field names), and Splunk holds no indexed field of those names
    for (const p of out) { for (const f of SHADOW) expect(p.field_names ?? [], `bare field ${f} in the outgoing payload`).not.toContain(f); expect(p.field_names ?? []).toContain('netspout_run_id'); }
    const indexedBare: Record<string, number> = {};
    for (const f of SHADOW) { const r = await splunk(`| tstats count WHERE index=${EVENT_INDEX} netspout_run_id="${runId}" BY ${f}`); indexedBare[f] = r.filter((x) => x[f] !== undefined && x[f] !== null && String(x[f]) !== '').length; expect(indexedBare[f], `Splunk has an indexed field ${f}`).toBe(0); }
    const sample = await splunk(`${base} | head 2 | table _time host source sourcetype index _raw`);
    save(`journey_${c.tag}`, { sourcetype: c.st, vendor: c.vendor, run_id: runId, ui: { status_badge: 'Verified in Splunk', preview_sourcetype: c.st, preview_info: previewInfo, preview_first_event: previewRaw.slice(0, 400), outcome: await page.getByTestId('outcome-text').textContent() },
      outgoing_by_tap: { count: out.length, sourcetypes: [...new Set(out.map((p) => p.sourcetype))], indexes: [...new Set(out.map((p) => p.index))], hosts: hostsSent, hec_status: [...new Set(out.map((p) => p.upstream_status))] },
      splunk: { count: Number(stats[0].count), sourcetype: stats[0].st, index: stats[0].ix, hosts: hostsSplunk, sources: stats[0].src, time_first: Number(stats[0].t0), time_last: Number(stats[0].t1), send_time_first: Math.min(...sent), send_time_last: Math.max(...sent) },
      ta_fields_extracted_counts: Object.fromEntries(c.fields.map((f) => [f, Number(fieldRows[0][f])])), indexed_bare_vendor_fields_in_splunk: indexedBare, bare_vendor_fields_in_outgoing_payload: SHADOW.filter((f) => out.some((p) => (p.field_names ?? []).includes(f))), sample_events: sample });
  });
}

// ------------------------------------------------------------------------------------------------------------------------------ metrics
const METRIC_ST = 'cisco:ios:mdt:metric';
test('[metrics] IOS XR metrics: Connections (metric index cisco_metrics), preview, generate, mstats', async ({ page, request }) => {
  group('metrics');
  test.setTimeout(240_000);
  await tapMode(request, 'pass'); await tapReset(request);
  await configure(page, { metricIndex: METRIC_INDEX });
  const f = await pick(page, request, METRIC_ST);
  await expect(page.getByTestId('status-badge')).toHaveText('Can send data, not tested in Splunk');   // untested metric names are never promoted
  await expect(page.getByTestId('preview-sourcetype')).toHaveText(METRIC_ST);
  const previewInfo = (await page.getByTestId('preview').locator('p').first().textContent()) ?? '';
  expect(previewInfo).toContain('metric index');
  expect(previewInfo).toContain(METRIC_INDEX);
  const previewRaw = (await page.getByTestId('preview-raw').allTextContents()).join('\n');
  expect(previewRaw).toMatch(/interface_generic_counters\.\w+ = [\d.]+|Cisco-IOS-XR-wdsysmon-fd-oper:system-monitoring\/cpu-utilization\.total_cpu_one_minute = [\d.]+/);
  await page.screenshot({ path: `${SHOTS}/p9_04_metrics_selected_and_previewed.png`, fullPage: true });
  await page.getByTestId('count').fill('28');
  const runId = await startFromUi(page);
  const out = await until(() => tapped(request, runId), (r) => r.length >= 28, 60_000, 1000);
  expect(out.length).toBe(28);
  expect(out.every((p) => p.kind === 'metric' && p.index === METRIC_INDEX && p.upstream_status === 200)).toBeTruthy();
  const datapoints = out.reduce((n, p) => n + (p.metric_names?.length ?? 0), 0);
  await expect(page.getByTestId('outcome-text')).toContainText(`Verified: found ${datapoints} of ${datapoints} metric datapoints in metric index ${METRIC_INDEX} (mstats search)`, { timeout: 120_000 });
  await page.screenshot({ path: `${SHOTS}/p9_05_metrics_verified_by_mstats.png`, fullPage: true });
  expect(await page.getByTestId('outcome-text').textContent()).not.toMatch(/events in index/);   // metric success is never phrased as an event-index result
  // independent mstats / mcatalog in the lab, by run id
  const MN = '(metric_name="interface_generic_counters.*" OR metric_name="Cisco-IOS-XR-wdsysmon-fd-oper:system-monitoring/cpu-utilization.total_cpu_*")';
  const per = await until(() => splunk(`| mstats sum(_value) as v count(_value) as n WHERE index=${METRIC_INDEX} AND ${MN} AND netspout_run_id="${runId}" BY metric_name`), (r) => r.reduce((a, x) => a + Number(x.n), 0) >= datapoints);
  const sentNames = new Set(out.flatMap((p) => p.metric_names ?? []));
  expect(new Set(per.map((r) => r.metric_name))).toEqual(sentNames);
  expect(per.reduce((a, x) => a + Number(x.n), 0)).toBe(datapoints);
  const sums: Record<string, number> = {}; for (const p of out) for (const [k, v] of Object.entries(p.metric_values ?? {})) sums[k] = (sums[k] ?? 0) + v;
  for (const r of per) expect(Math.abs(Number(r.v) - sums[r.metric_name])).toBeLessThanOrEqual(1e-6 * Math.max(1, sums[r.metric_name]));   // numeric values equal what was sent
  const ev = JSON.parse(readFileSync(resolve(process.cwd(), '..', 'docs', 'contracts', 'phase7', 'phase8_metric_evidence.json'), 'utf8')).metrics as Record<string, { dims: string[]; path: string }>;
  const dims = await splunk(`| mcatalog values(_dims) as dims values(path) as path WHERE index=${METRIC_INDEX} AND netspout_run_id="${runId}" BY metric_name | eval dims=mvjoin(dims,",")`);
  for (const r of dims) { expect(new Set(r.dims.split(',').filter((d: string) => !d.startsWith('netspout_')))).toEqual(new Set(ev[r.metric_name].dims)); expect(r.path).toBe(ev[r.metric_name].path); }
  const asEvents = await splunk(`search index=${EVENT_INDEX} netspout_run_id="${runId}" | stats count`);
  expect(Number(asEvents[0]?.count ?? 0)).toBe(0);                    // nothing of this run is in the event index: the event index cannot be what proved the metrics
  const idx = await splunk(`| rest /services/data/indexes/${METRIC_INDEX} splunk_server=local | table title datatype`, '-5m');
  expect(idx[0].datatype).toBe('metric');
  save('journey_metrics', { sourcetype: METRIC_ST, product: f.product, run_id: runId, ui: { status_badge: 'Can send data, not tested in Splunk', preview_info: previewInfo, preview_metrics: previewRaw.split('\n').slice(0, 6), outcome: await page.getByTestId('outcome-text').textContent() },
    outgoing_by_tap: { hec_events: out.length, datapoints, index: [...new Set(out.map((p) => p.index))], metric_names: [...sentNames].sort(), dimension_sets: [...new Set(out.map((p) => (p.dimension_names ?? []).join(',')))] },
    mstats: per.map((r) => ({ metric_name: r.metric_name, datapoints: Number(r.n), sum: Number(r.v), sent_sum: sums[r.metric_name] })), mcatalog_dims: dims.map((r) => ({ metric_name: r.metric_name, dims: r.dims, path: r.path })),
    event_index_rows_for_this_run: 0, metric_index_datatype: idx[0].datatype,
    not_promoted: 'only the 14 documented series are generated; the other cisco_metrics names stay unsupported and the capability status stays "Can send data, not tested in Splunk"' });
});

// ------------------------------------------------------------------------------------------------------------------------------ failure paths: the UI must never say Verified because HEC accepted the payload
const NEVER_VERIFIED = async (page: Page) => { const t = (await page.getByTestId('outcome-text').textContent()) ?? ''; expect(t).not.toMatch(/Verified:/); return t; };
async function generateAsa(page: Page, request: APIRequestContext, n = 10) {
  await open(page, '/generate/quick');
  await page.getByTestId('vendor').selectOption('cisco_asa');
  await expect(page.getByTestId('preview-sourcetype')).toHaveText('cisco:asa');
  await page.getByTestId('count').fill(String(n));
  return startFromUi(page);
}

test('[failures] invalid destination: the test says not working and a run says Splunk did not receive the data', async ({ page, request }) => {
  group('asa');
  test.setTimeout(180_000);
  await configure(page, { hec: 'http://127.0.0.1:19997/services/collector' });
  await page.getByTestId('test-connection').click();
  await expect(page.getByTestId('connection-summary')).toContainText('Not working', { timeout: 60_000 });
  await page.screenshot({ path: `${SHOTS}/p9_10_failure_invalid_destination_connections.png`, fullPage: true });
  const connText = (await page.getByTestId('connection-summary').textContent()) ?? '';
  const runId = await generateAsa(page, request);
  await expect(page.getByTestId('outcome-text')).toContainText('Splunk did not receive this data', { timeout: 60_000 });
  const t = await NEVER_VERIFIED(page);
  await page.screenshot({ path: `${SHOTS}/p9_11_failure_invalid_destination_run.png`, fullPage: true });
  const n = await splunk(`search index=${EVENT_INDEX} netspout_run_id="${runId}" | stats count`);
  save('failure_invalid_destination', { ui_connection: connText, ui_run: t, splunk_events_for_run: Number(n[0]?.count ?? 0) });
  expect(Number(n[0]?.count ?? 0)).toBe(0);
});

test('[failures] HEC rejection (real Splunk refuses the token)', async ({ page, request }) => {
  group('asa');
  test.setTimeout(180_000);
  await tapMode(request, 'pass'); await tapReset(request);
  await configure(page, { token: 'deadbeef-0000-4000-8000-000000000000' });
  await page.getByTestId('test-connection').click();
  await expect(page.getByTestId('connection-summary')).toContainText('Not working', { timeout: 60_000 });
  const runId = await generateAsa(page, request);
  await expect(page.getByTestId('outcome-text')).toContainText('Splunk did not receive this data', { timeout: 60_000 });
  const t = await NEVER_VERIFIED(page);
  const out = await tapped(request, runId);
  await page.screenshot({ path: `${SHOTS}/p9_12_failure_hec_rejection.png`, fullPage: true });
  const n = await splunk(`search index=${EVENT_INDEX} netspout_run_id="${runId}" | stats count`);
  save('failure_hec_rejection', { ui_run: t, hec_status_seen_by_tap: [...new Set(out.map((p) => p.upstream_status))], splunk_events_for_run: Number(n[0]?.count ?? 0) });
  expect(out.length).toBeGreaterThan(0); expect(out.every((p) => p.upstream_status !== 200)).toBeTruthy();
  expect(Number(n[0]?.count ?? 0)).toBe(0);
});

test('[failures] accepted but not indexed: HEC says success, nothing reaches the index, the UI does not say Verified', async ({ page, request }) => {
  group('asa');
  test.setTimeout(240_000);
  await configure(page);
  await tapReset(request); await tapMode(request, 'drop');
  await page.getByTestId('test-connection').click();
  await expect(page.getByTestId('connection-summary')).toContainText('Partly working', { timeout: 90_000 });       // accepted, but a search cannot find the marked test event
  await page.screenshot({ path: `${SHOTS}/p9_13_failure_accepted_not_indexed_connections.png`, fullPage: true });
  const runId = await generateAsa(page, request);
  await expect(page.getByTestId('outcome-text')).toContainText('Not confirmed:', { timeout: 150_000 });
  const t = await NEVER_VERIFIED(page);
  await page.screenshot({ path: `${SHOTS}/p9_14_failure_accepted_not_indexed_run.png`, fullPage: true });
  const out = await tapped(request, runId);
  const n = await splunk(`search index=* netspout_run_id="${runId}" | stats count`);
  save('failure_accepted_not_indexed', { ui_run: t, hec_replies_seen_by_tap: [...new Set(out.map((p) => p.upstream_status))], splunk_events_for_run_in_any_index: Number(n[0]?.count ?? 0) });
  await tapMode(request, 'pass');
  expect(Number(n[0]?.count ?? 0)).toBe(0);
});

test('[failures] wrong event index: events land elsewhere, the UI does not say Verified', async ({ page, request }) => {
  group('asa');
  test.setTimeout(240_000);
  await configure(page);
  await tapReset(request); await tapMode(request, 'reindex_event', 'main');
  const runId = await generateAsa(page, request);
  await expect(page.getByTestId('outcome-text')).toContainText('Not confirmed:', { timeout: 150_000 });
  const t = await NEVER_VERIFIED(page);
  await page.screenshot({ path: `${SHOTS}/p9_15_failure_wrong_event_index.png`, fullPage: true });
  const inMain = await until(() => splunk(`search index=main netspout_run_id="${runId}" | stats count`), (r) => Number(r[0]?.count ?? 0) >= 10);
  const inDest = await splunk(`search index=${EVENT_INDEX} netspout_run_id="${runId}" | stats count`);
  save('failure_wrong_event_index', { ui_run: t, events_in_expected_index: Number(inDest[0]?.count ?? 0), events_actually_in_main: Number(inMain[0]?.count ?? 0) });
  await tapMode(request, 'pass');
  expect(Number(inMain[0]?.count ?? 0)).toBe(10); expect(Number(inDest[0]?.count ?? 0)).toBe(0);
});

test('[failures] wrong metric index: metrics land in another metric index, the UI does not say Verified', async ({ page, request }) => {
  group('asa');
  test.setTimeout(240_000);
  await configure(page);
  await tapReset(request); await tapMode(request, 'reindex_metric', 'dev_test_replay_metrics');
  await pick(page, request, METRIC_ST);
  await page.getByTestId('count').fill('14');
  const runId = await startFromUi(page);
  await expect(page.getByTestId('outcome-text')).toContainText('Not confirmed:', { timeout: 150_000 });
  const t = await NEVER_VERIFIED(page);
  await page.screenshot({ path: `${SHOTS}/p9_16_failure_wrong_metric_index.png`, fullPage: true });
  const MN = 'metric_name="interface_generic_counters.*"';
  const where = await until(() => splunk(`| mstats count(_value) as n WHERE index=dev_test_replay_metrics AND ${MN} AND netspout_run_id="${runId}"`), (r) => Number(r[0]?.n ?? 0) > 0);
  const expected = await splunk(`| mstats count(_value) as n WHERE index=${METRIC_INDEX} AND ${MN} AND netspout_run_id="${runId}"`);
  save('failure_wrong_metric_index', { ui_run: t, datapoints_in_expected_metric_index: Number(expected[0]?.n ?? 0), datapoints_actually_in_dev_test_replay_metrics: Number(where[0]?.n ?? 0) });
  await tapMode(request, 'pass');
  expect(Number(expected[0]?.n ?? 0)).toBe(0); expect(Number(where[0]?.n ?? 0)).toBeGreaterThan(0);
});

test('[failures] unsupported sourcetype and metric/event routing conflict: no generate control and the server refuses', async ({ page, request }) => {
  group('asa');
  const cat = await catalog(request);
  const noGen = cat.vendors.flatMap((v) => v.products.flatMap((p) => p.sourcetypes.filter((s) => s.block?.code === 'NO_GENERATOR').map((s) => ({ v: v.id, p: p.name, s })))) [0];
  const un = await pick(page, request, noGen.s.sourcetype);
  await expect(page.getByTestId('status-badge')).toHaveText('Cannot send data');
  await expect(page.getByTestId('blocked')).toContainText('cannot generate data');
  await expect(page.getByTestId('generate')).toHaveCount(0);
  await page.screenshot({ path: `${SHOTS}/p9_17_unsupported_sourcetype.png`, fullPage: true });
  const r1 = await request.post(`${API}/api/runs`, { data: { kind: 'sourcetype', target: noGen.s.sourcetype, vendor_id: un.vendor, index: EVENT_INDEX, count: 1 } });
  expect(r1.status()).toBe(409);
  await pick(page, request, 'cisco:thousandeyes:metric');
  await expect(page.getByTestId('status-badge')).toHaveText('Cannot send data');
  await expect(page.getByTestId('blocked')).toContainText('metric-index payload');
  await expect(page.getByTestId('blocked')).toContainText('generation is disabled');
  await expect(page.getByTestId('generate')).toHaveCount(0);
  await page.screenshot({ path: `${SHOTS}/p9_18_routing_conflict.png`, fullPage: true });
  const r2 = await request.post(`${API}/api/runs`, { data: { kind: 'sourcetype', target: 'cisco:thousandeyes:metric', vendor_id: 'cisco_thousandeyes', count: 1 } });
  expect(r2.status()).toBe(409);
  const pv = await request.post(`${API}/api/generate/preview`, { data: { vendor_id: 'cisco_thousandeyes', sourcetype: 'cisco:thousandeyes:metric', count: 1 } });
  expect(pv.status()).toBe(409);
  save('failure_unsupported_and_routing', { unsupported_example: noGen.s.sourcetype, unsupported_block: noGen.s.block, run_http_status: r1.status(), routing_conflict: 'cisco:thousandeyes:metric', routing_run_http_status: r2.status(), routing_preview_http_status: pv.status() });
});

test('[failures] preview generation failure: the error is shown and nothing can be sent', async ({ page, request }) => {
  group('asa');
  await configure(page);
  await open(page, '/generate/quick');
  await page.route('**/api/generate/preview', (route) => route.fulfill({ status: 500, contentType: 'application/json', body: JSON.stringify({ detail: 'preview generator failed (injected for this test)' }) }));
  await page.getByTestId('vendor').selectOption('cisco_ios');
  await expect(page.getByTestId('preview-error')).toContainText('preview generator failed');
  await expect(page.getByTestId('generate')).toBeDisabled();
  await expect(page.getByTestId('cannot-run')).toContainText('preview could not be generated');
  await page.screenshot({ path: `${SHOTS}/p9_19_preview_failure.png`, fullPage: true });
  save('failure_preview', { injected: 'HTTP 500 from /api/generate/preview via browser route interception', generate_disabled: true });
});

test('[failures] Splunk search unavailable: HEC accepts, the UI says it could not check and does not say Verified', async ({ page, request }) => {
  group('asa');
  test.setTimeout(240_000);
  await tapMode(request, 'pass'); await tapReset(request);
  await configure(page, { search: 'https://127.0.0.1:19998/services/search/jobs/export' });
  await page.getByTestId('test-connection').click();
  await expect(page.getByTestId('connection-summary')).toContainText('Partly working', { timeout: 90_000 });
  await expect(page.getByTestId('connection-summary')).toContainText('cannot confirm that anything is searchable');
  await page.screenshot({ path: `${SHOTS}/p9_20a_failure_search_unavailable_connections.png`, fullPage: true });
  const runId = await generateAsa(page, request);
  await expect(page.getByTestId('outcome-text')).toContainText('could not check whether it is searchable', { timeout: 150_000 });
  const t = await NEVER_VERIFIED(page);
  await page.screenshot({ path: `${SHOTS}/p9_20_failure_search_unavailable.png`, fullPage: true });
  const n = await until(() => splunk(`search index=${EVENT_INDEX} netspout_run_id="${runId}" | stats count`), (r) => Number(r[0]?.count ?? 0) >= 10);
  save('failure_search_unavailable', { ui_run: t, note: 'the events really were indexed (checked by this test directly); the app still did not claim Verified because its own search could not run', splunk_events_for_run: Number(n[0]?.count ?? 0) });
  await configure(page);          // leave a working destination behind
});

// ------------------------------------------------------------------------------------------------------------------------------ the finished simple UI
test('[ui] one connection test, readable vendor names, searchable products, plain status words, advanced settings tucked away', async ({ page, request }) => {
  group('asa');
  await configure(page);
  // Connections: a single Test connection control; the old Validate / Connection health / HEC connection test sections are gone
  await expect(page.getByRole('button', { name: /^Validate/ })).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Test connection' })).toHaveCount(1);
  await expect(page.getByText('Connection health')).toHaveCount(0);
  await expect(page.getByText('HEC connection test')).toHaveCount(0);
  expect(await page.locator('details.setup-advanced').evaluate((d) => (d as HTMLDetailsElement).open)).toBe(false);
  await page.screenshot({ path: `${SHOTS}/p9_30_connections_simple.png`, fullPage: true });
  // Generate Data
  await open(page, '/generate/quick');
  await page.getByTestId('show-all').check();
  const vendors = await page.getByTestId('vendor').locator('option').allTextContents();
  expect(vendors.filter((v) => v.replace(' — verified', '') === 'Cisco Systems')).toEqual([]);
  expect(new Set(vendors.map((v) => v.replace(' — verified', ''))).size).toBe(vendors.length);       // every vendor entry reads differently
  const cisco = vendors.filter((v) => v.startsWith('Cisco'));
  await page.getByTestId('vendor').selectOption('cisco_sdwan');
  const before = await page.getByTestId('product').locator('option').count();
  expect(before).toBeGreaterThan(8);
  await expect(page.getByTestId('product-search')).toBeVisible();
  await page.getByTestId('product-search').fill('link health');
  const after = await page.getByTestId('product').locator('option').allTextContents();
  expect(after.length).toBeLessThan(before); expect(after.length).toBeGreaterThan(0);
  await page.screenshot({ path: `${SHOTS}/p9_31_product_search.png`, fullPage: true });
  await page.getByTestId('product-search').fill('no such product xyz');
  await expect(page.getByTestId('product')).toContainText('No product matches');
  await page.getByTestId('product-search').fill('');
  await page.getByTestId('vendor').selectOption('cisco_asa');
  await expect(page.getByTestId('status-badge')).toBeVisible();
  const labels = new Set<string>();
  for (const st of ['cisco:asa', 'cisco:ise:syslog', METRIC_ST, 'cisco:thousandeyes:metric']) { await pick(page, request, st); labels.add((await page.getByTestId('status-badge').textContent()) ?? ''); }
  expect([...labels].sort()).toEqual(['Can send data, not tested in Splunk', 'Cannot send data', 'Checked offline only, not tested in Splunk', 'Verified in Splunk'].sort());
  // advanced options are collapsed (a fresh page: the previous steps left a blocked selection on screen)
  await open(page, '/generate/quick');
  await page.reload();
  await expect(page.getByTestId('count')).toBeVisible();
  await expect(page.getByTestId('mode')).toBeHidden();
  await page.screenshot({ path: `${SHOTS}/p9_32_generate_simple.png`, fullPage: true });
  save('ui_polish', { vendor_names_cisco: cisco, products_before_search: before, products_after_search_link_health: after, status_words: [...labels] });
});

test('[ui] a scenario that cannot run says exactly why', async ({ page, request }) => {
  group('asa');
  const sc = ((await (await request.get(`${API}/api/compat/scenarios`)).json()) as { scenarios: Array<{ id: string; title: string; runnable: boolean; reasons: string[] }> }).scenarios.find((s) => s.id === 'C100-CRI-001')!;
  expect(sc.runnable).toBeFalsy();
  await open(page, '/generate/scenarios');
  await page.getByTestId('runnable-only').uncheck();
  await page.getByTestId('category').selectOption('ALL');
  await page.getByTestId('scenario').selectOption(sc.id);
  await expect(page.getByTestId('scenario-state')).toHaveText('Cannot run');
  await expect(page.getByTestId('why-cannot-run')).toContainText('cisco:thousandeyes:metric');
  await expect(page.getByTestId('why-cannot-run')).toContainText('generation is disabled');
  await expect(page.getByTestId('run-scenario')).toBeDisabled();
  await expect(page.getByTestId('cannot-run')).toContainText('cisco:thousandeyes:metric');
  await page.screenshot({ path: `${SHOTS}/p9_33_scenario_cannot_run_reason.png`, fullPage: true });
  save('ui_scenario_reason', { scenario: sc.id, reasons: sc.reasons });
});

// ------------------------------------------------------------------------------------------------------------------------------ scenario through the UI into the lab
const SCENARIO = 'paloalto_threat_investigation';
test('[pan] scenario through the UI: events indexed, correlation ids, phase order, expected searches', async ({ page, request }) => {
  group('pan');
  test.setTimeout(300_000);
  await tapMode(request, 'pass'); await tapReset(request);
  await configure(page);
  const sc = ((await (await request.get(`${API}/api/compat/scenarios`)).json()) as { scenarios: Array<{ id: string; title: string; runnable: boolean; run_state: string; dashboard: string | null; required: Array<{ sourcetype: string; status: string }> }> }).scenarios.find((s) => s.id === SCENARIO)!;
  expect(sc.runnable).toBeTruthy();
  await open(page, '/generate/scenarios');
  await page.getByTestId('category').selectOption('ALL');
  await page.getByTestId('scenario').selectOption(SCENARIO);
  await expect(page.getByTestId('scenario-state')).toHaveText('Can run, not fully tested in Splunk');       // not verified: two required sources are only format-checked
  await page.screenshot({ path: `${SHOTS}/p9_40_scenario_selected.png`, fullPage: true });
  const [resp] = await Promise.all([page.waitForResponse((r) => r.url().endsWith('/api/runs') && r.request().method() === 'POST'), page.getByTestId('run-scenario').click()]);
  expect(resp.ok()).toBeTruthy();
  const runId = (await resp.json()).run_id as string;
  await expect(page.getByTestId('outcome-text')).toContainText('Verified: found', { timeout: 240_000 });
  await page.screenshot({ path: `${SHOTS}/p9_41_scenario_result.png`, fullPage: true });
  const out = await tapped(request, runId);
  const n = out.length; expect(n).toBeGreaterThan(5);
  expect(out.every((p) => p.upstream_status === 200 && p.index === EVENT_INDEX)).toBeTruthy();
  const base = `index=${EVENT_INDEX} netspout_run_id="${runId}"`;
  const byPhase = await until(() => splunk(`${base} | stats count min(_time) as t0 max(_time) as t1 values(netspout_scenario_id) as sid by netspout_phase | sort t0`), (r) => r.reduce((a, x) => a + Number(x.count), 0) >= n);
  const total = byPhase.reduce((a, x) => a + Number(x.count), 0);
  expect(total).toBe(n);
  expect(byPhase.every((r) => [].concat(r.sid).join() === SCENARIO)).toBeTruthy();                               // correlation: scenario id and run id on every indexed event
  const sentPhases = out.map((p) => p.phase); const order = [...new Set(sentPhases)];
  expect(byPhase.map((r) => r.netspout_phase)).toEqual(order);                                                   // phases appear in Splunk in the order NetSpout sent them
  for (let i = 1; i < byPhase.length; i++) expect(Number(byPhase[i].t0)).toBeGreaterThanOrEqual(Number(byPhase[i - 1].t0));
  const ids = await splunk(`${base} | stats dc(netspout_event_id) as ids count as c`);
  expect(Number(ids[0].ids)).toBe(Number(ids[0].c));                                                              // every event has its own event id
  const bySt = await splunk(`${base} | stats count by sourcetype`);
  const sentSt = out.reduce<Record<string, number>>((m, p) => { m[p.sourcetype] = (m[p.sourcetype] ?? 0) + 1; return m; }, {});
  for (const r of bySt) expect(Number(r.count)).toBe(sentSt[r.sourcetype]);
  // the scenario's own investigation searches: every data source of its Dashboard Studio dashboard, run against this run's data
  const xml = readFileSync(resolve(process.cwd(), '..', 'netspout', 'default', 'data', 'ui', 'views', `pf_${SCENARIO}.xml`), 'utf8');
  const def = JSON.parse(/<!\[CDATA\[([\s\S]*?)\]\]>/.exec(xml)![1]) as { dataSources: Record<string, { options: { query?: string } }> };
  const searches: Array<{ source: string; rows: number }> = [];
  for (const [k, v] of Object.entries(def.dataSources)) {
    const q = (v.options.query ?? '').replace(/\$index_tok\$/g, EVENT_INDEX).replace(/\$run_tok\$/g, runId).replace(/\$phase_tok\$/g, '*');
    if (!q) continue;
    const rows = await splunk(q);
    searches.push({ source: k, rows: rows.length });
  }
  expect(searches.length).toBeGreaterThanOrEqual(12);
  for (const x of searches) expect(x.rows, `dashboard search ${x.source} returns rows for this run`).toBeGreaterThan(0);
  save('scenario_paloalto_threat_investigation', { scenario: SCENARIO, run_id: runId, required: sc.required, state_label: 'Can run, not fully tested in Splunk', ui_outcome: await page.getByTestId('outcome-text').textContent(),
    sent: { events: n, by_sourcetype: sentSt, phases: order }, indexed: { total, by_phase: byPhase.map((r) => ({ phase: r.netspout_phase, count: Number(r.count), first: Number(r.t0), last: Number(r.t1) })), by_sourcetype: Object.fromEntries(bySt.map((r) => [r.sourcetype, Number(r.count)])) },
    dashboard: sc.dashboard, dashboard_searches_run: searches });
  // this scenario's investigation view is a native Splunk dashboard (pf_*), not a Dashboard Studio dashboard: the page must say so rather than show a dead link
  await expect(page.getByRole('link', { name: 'Investigate in Dashboard Studio' })).toHaveCount(0);
  await expect(page.getByText('has no Dashboard Studio dashboard yet')).toBeVisible();
});

test('[pan] a scenario that has a Dashboard Studio dashboard shows the link with the run id', async ({ page, request }) => {
  group('pan');
  test.setTimeout(240_000);
  await tapMode(request, 'pass'); await tapReset(request);
  await configure(page);
  const dash = ((await (await request.get(`${API}/api/dashboards`)).json()) as { dashboards: Array<{ dashboard_id: string; scenario_id: string; runtime_scenario_id: string }> }).dashboards.find((d) => d.runtime_scenario_id === 'C100-SEC-001')!;
  await open(page, '/generate/scenarios');
  await page.getByTestId('category').selectOption('ALL');
  await page.getByTestId('scenario').selectOption('C100-SEC-001');
  const [resp] = await Promise.all([page.waitForResponse((r) => r.url().endsWith('/api/runs') && r.request().method() === 'POST'), page.getByTestId('run-scenario').click()]);
  expect(resp.ok()).toBeTruthy();
  const runId = (await resp.json()).run_id as string;
  await expect(page.getByTestId('outcome-text')).toContainText('Verified: found', { timeout: 180_000 });
  const link = page.getByRole('link', { name: 'Investigate in Dashboard Studio' });
  await expect(link).toHaveAttribute('href', new RegExp(`dashboard=${dash.dashboard_id}&run=${runId}`));
  await page.screenshot({ path: `${SHOTS}/p9_42_scenario_with_studio_link.png`, fullPage: true });
  const out = await tapped(request, runId);
  const n = await until(() => splunk(`search index=${EVENT_INDEX} netspout_run_id="${runId}" | stats count`), (r) => Number(r[0]?.count ?? 0) >= out.filter((p) => p.kind === 'event').length);
  expect(Number(n[0].count)).toBe(out.filter((p) => p.kind === 'event').length);
  save('scenario_with_studio_link', { scenario: 'C100-SEC-001', dashboard_id: dash.dashboard_id, run_id: runId, link_href: await link.getAttribute('href'), events_indexed: Number(n[0].count), note: 'sourcetype netspout:cisco:asa:syslog is a NetSpout-defined source, not a TA sourcetype: delivery and indexing are checked, TA parsing is not claimed' });
});
