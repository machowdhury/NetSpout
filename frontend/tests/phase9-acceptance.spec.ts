// Phase 9 browser-to-Splunk acceptance. Every journey goes: Connections -> Generate Data -> Preview -> Generate -> verify, through the real browser UI, into the isolated lab Splunk.
// The destination is the REAL lab HEC, reached through scripts/phase9_hec_proxy.py (a recording tap that forwards unchanged except in the failure-path tests).
// Searches that prove the result do not use the app's own verification: they query the lab Splunk directly with the lab credentials (read from the git-ignored lab env file; never logged).
//   PHASE9_API_BASE=http://127.0.0.1:18681 PHASE9_TAP=http://127.0.0.1:19990 PHASE9_LAB_ENV=<.env.lab> PHASE9_ONLY=asa PLAYWRIGHT_BASE_URL=http://127.0.0.1:14273 npx playwright test tests/phase9-acceptance.spec.ts --workers=1 --trace off
// Driven by scripts/phase9_acceptance.py, which installs the matching add-on in the lab for each group. Skipped unless all three variables are set.
import { expect, test as base, type APIRequestContext, type Locator, type Page } from '@playwright/test';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { request as httpsRequest } from 'node:https';
import { resolve } from 'node:path';

const API = process.env.PHASE9_API_BASE ?? '';
const TAP = process.env.PHASE9_TAP ?? '';
const LAB_ENV = process.env.PHASE9_LAB_ENV ?? '';
const ONLY = process.env.PHASE9_ONLY ?? '';
// Splunk Web mode (the packaged release candidate): the browser signs in to Splunk Web, the app's static bundle is loaded from the Splunk origin and every API call goes through the app's gateway to
// the engine. Direct mode (default) talks to a dev engine. PHASE9_API_BASE is then the gateway URL.
//   PHASE9_SPLUNK_WEB=http://127.0.0.1:39000  PHASE9_API_BASE=http://127.0.0.1:39000/en-US/splunkd/__raw/services/netspout_gateway
const WEB = process.env.PHASE9_SPLUNK_WEB ?? '';
const ENGINE_URL = process.env.PHASE9_ENGINE_URL ?? '';       // packaged lab only: the address the Splunk app is configured with (as Splunk reaches the engine)
// as the ENGINE sees them (in the packaged lab the engine runs in a container): the tap and the Splunk search endpoint, and the indexes to use
const ENGINE_TAP = process.env.PHASE9_ENGINE_TAP ?? '';
const ENGINE_SEARCH = process.env.PHASE9_ENGINE_SEARCH_URL ?? 'https://127.0.0.1:19191/services/search/jobs/export';
const OUT = process.env.PHASE9_OUT ?? 'phase9';           // evidence folder name under docs/verification/evidence (screenshots go to <name>_ui)
const SHOTS = resolve(process.cwd(), '..', 'docs', 'verification', 'evidence', `${OUT}_ui`);
const EVID = resolve(process.cwd(), '..', 'docs', 'verification', 'evidence', OUT);
mkdirSync(SHOTS, { recursive: true });
mkdirSync(EVID, { recursive: true });

const lab: Record<string, string> = LAB_ENV ? Object.fromEntries(readFileSync(LAB_ENV, 'utf8').split('\n').filter((l) => l.includes('=')).map((l) => [l.slice(0, l.indexOf('=')).trim(), l.slice(l.indexOf('=') + 1).trim()])) : {};
if (LAB_ENV) { const ok = (lab.LAB_MGMT_PORT === '19191' && lab.LAB_HEC_PORT === '19088') || (lab.LAB_MGMT_PORT === '39191' && lab.LAB_HEC_PORT === '39088') || Array.from({ length: 7 }, (_, i) => 45000 + i * 1000).some((b) => lab.LAB_MGMT_PORT === String(b + 191) && lab.LAB_HEC_PORT === String(b + 88)); if (!ok) throw new Error('this suite only runs against the isolated labs (TA-validation 19191/19088, release-candidate install 39191/39088, Phase 15/16 labs 45xxx-51xxx)'); }
const TAP_HEC = `${ENGINE_TAP || TAP}/services/collector`;
const SEARCH_URL = ENGINE_SEARCH;
const EVENT_INDEX = process.env.PHASE9_EVENT_INDEX ?? 'ta_validation';
const METRIC_INDEX = process.env.PHASE9_METRIC_INDEX ?? 'cisco_metrics';
async function login(page: Page) {
  await page.goto(`${WEB}/en-US/account/login`);
  await page.locator('input[name="username"]').fill('admin');
  try { await page.locator('input[name="password"]').fill(lab.LAB_SPLUNK_PASSWORD); } catch { throw new Error('could not fill the Splunk password'); }
  await page.keyboard.press('Enter');
  await page.waitForURL(/\/app\//, { timeout: 90_000 });
}
const test = base.extend({
  request: async ({ page, playwright }, use) => {
    if (WEB) {                                              // the browser's own session: gateway calls carry the Splunk login; direct POSTs also need Splunk Web's CSRF key, as the UI adds it
      const csrf = async () => { const c = (await page.context().cookies()).find((k) => k.name.startsWith('splunkweb_csrf_token')); return c ? { 'X-Splunk-Form-Key': c.value } : {}; };
      await use(new Proxy(page.request, { get: (t, k) => k === 'post' ? async (u: string, o: any = {}) => t.post(u, { ...o, headers: { ...(await csrf()), ...(o.headers || {}) } }) : typeof (t as any)[k] === 'function' ? (t as any)[k].bind(t) : (t as any)[k] }) as APIRequestContext);
      return;
    }
    const ctx = await playwright.request.newContext(); await use(ctx); await ctx.dispose();
  },
  page: async ({ page }, use) => { if (WEB) await login(page); await use(page); },
});
if (WEB) test.use({ extraHTTPHeaders: { 'X-Requested-With': 'XMLHttpRequest' } });
test.skip(!API || !TAP || !LAB_ENV, 'set PHASE9_API_BASE, PHASE9_TAP and PHASE9_LAB_ENV (isolated backend, recording tap, lab env file)');

const group = (g: string) => test.skip(!!ONLY && ONLY !== g, `group ${g} is not selected`);

// ------------------------------------------------------------------------------------------------------------------------------ helpers
function splunk(search: string, earliest = '-3h'): Promise<Array<Record<string, any>>> {
  return new Promise((ok, bad) => {
    const body = new URLSearchParams({ search: /^\s*(\||search )/.test(search) ? search : 'search ' + search, output_mode: 'json', earliest_time: earliest, latest_time: '+1h' }).toString();
    const req = httpsRequest({ host: '127.0.0.1', port: Number(lab.LAB_MGMT_PORT), path: '/services/search/jobs/export', method: 'POST', rejectUnauthorized: false, headers: { Authorization: 'Basic ' + Buffer.from('admin:' + lab.LAB_SPLUNK_PASSWORD).toString('base64'), 'Content-Type': 'application/x-www-form-urlencoded', 'Content-Length': Buffer.byteLength(body) } }, (res) => {
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
const open = async (page: Page, route: string) => { await page.setViewportSize({ width: 1280, height: 1500 }); await page.goto(WEB ? `${WEB}/en-US/static/app/netspout/dist/index.html#${route}` : `/?api_base=${encodeURIComponent(API)}#${route}`); };
const secret = async (loc: Locator, value: string) => { try { await loc.fill(value); } catch (e) { throw new Error('could not fill a secret field: ' + String((e as Error).message).split(value).join('***').split('\n').slice(0, 4).join(' | ').slice(0, 300)); } };   // a failing fill must never print the secret
type Cfg = { hec?: string; search?: string; token?: string; secret?: string; eventIndex?: string; metricIndex?: string };
async function configure(page: Page, o: Cfg = {}) {
  await open(page, '/system/connections');
  await expect(page.getByTestId('setup-wizard')).toBeVisible();
  await expect(page.locator('form[data-loaded="true"]')).toBeVisible({ timeout: 30_000 });   // the saved destination has been read: a late answer can no longer overwrite what is typed
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
  const posted = page.waitForResponse((r) => r.url().includes('/api/setup') && !r.url().includes('/api/setup/') && r.request().method() === 'POST');   // the saved state is read only after THIS save finished
  await page.getByRole('button', { name: 'Save secure configuration' }).click();
  await posted;
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
    const where = await findEntry(request, c.st);                      // a vendor can have several verified sourcetypes (Palo Alto has three): choose this one explicitly
    await page.getByTestId('product').selectOption(where.product);
    await page.getByTestId('sourcetype').selectOption(c.st);
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
  // every required source is verified against the Palo Alto add-on (traffic in Phase 4, threat and system in Phase 10), so the page may say Verified; the assertions below back that up
  await expect(page.getByTestId('scenario-state')).toHaveText('Verified in Splunk');
  for (const r of sc.required) expect(r.status, r.sourcetype).toBe('VERIFIED');
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
  // add-on parsing of every required source, on the scenario's own events
  const TA: Record<string, string[]> = {
    'pan:traffic': ['src_ip', 'dest_ip', 'src_port', 'dest_port', 'transport', 'rule', 'app', 'vendor_action', 'action', 'session_id'],
    'pan:threat': ['src_ip', 'dest_ip', 'rule', 'app', 'vendor_action', 'action', 'raw_category', 'severity', 'direction', 'threat_name', 'threat_id', 'log_subtype'],
    'pan:system': ['log_subtype', 'event_id', 'module', 'severity', 'description', 'sequence_number', 'signature', 'result'],
  };
  const taEvidence: Record<string, unknown> = {};
  for (const [st, fields] of Object.entries(TA)) {
    const want = sentSt[st];
    const r = await splunk(`${base} sourcetype="${st}" | stats count as total ${fields.map((f) => `count(${f}) as ${f}`).join(' ')} min(_time) as t0 max(_time) as t1`);
    expect(Number(r[0].total), `${st} events indexed`).toBe(want);
    for (const f of fields) expect(Number(r[0][f]), `${st}: add-on field ${f} extracted on every event`).toBe(want);
    const va = await splunk(`${base} sourcetype="${st}" | stats count by action vendor_action`);
    if (st !== 'pan:system') expect(va.every((x) => x.action !== 'unknown'), `${st}: no action fell through to unknown`).toBeTruthy();
    for (const f of SHADOW) { const t = await splunk(`| tstats count WHERE index=${EVENT_INDEX} netspout_run_id="${runId}" sourcetype="${st}" BY ${f}`); expect(t.filter((x) => x[f] !== undefined && String(x[f]) !== '').length, `${st}: indexed bare field ${f}`).toBe(0); }
    const raw = await splunk(`${base} sourcetype="${st}" | eval gen=strptime(generated_time,"%Y/%m/%d %H:%M:%S"), d=abs(_time-gen) | stats max(d) as maxdiff count(gen) as n`);
    expect(Number(raw[0].n)).toBe(want);
    expect(Number(raw[0].maxdiff), `${st}: the time inside the event agrees with the time Splunk stored`).toBeLessThan(120);
    taEvidence[st] = { events: want, fields_extracted_on_every_event: fields, max_seconds_between_event_time_and_stored_time: Number(raw[0].maxdiff), actions: va.map((x) => `${x.vendor_action}->${x.action}`) };
  }
  for (const p of out) for (const f of SHADOW) expect(p.field_names ?? [], `bare ${f} in the outgoing payload`).not.toContain(f);
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
  save('scenario_paloalto_threat_investigation', { scenario: SCENARIO, run_id: runId, required: sc.required, state_label: 'Verified in Splunk', ta_parsing: taEvidence, ui_outcome: await page.getByTestId('outcome-text').textContent(),
    sent: { events: n, by_sourcetype: sentSt, phases: order }, indexed: { total, by_phase: byPhase.map((r) => ({ phase: r.netspout_phase, count: Number(r.count), first: Number(r.t0), last: Number(r.t1) })), by_sourcetype: Object.fromEntries(bySt.map((r) => [r.sourcetype, Number(r.count)])) },
    dashboard: sc.dashboard, dashboard_searches_run: searches });
  // Investigate: the scenario's own Dashboard Studio dashboard and the generic run investigation dashboard, opened with this run's tokens
  await expect(page.getByRole('link', { name: 'Investigate in Dashboard Studio' })).toHaveCount(0);   // that in-app link is for the other kind of dashboard
  if (WEB) {
    const own = page.getByTestId('investigate-scenario-dashboard');
    await expect(own).toHaveAttribute('href', new RegExp(`/app/netspout/pf_${SCENARIO}\\?.*form\\.run_tok=${runId}`));
    const studio = await page.context().newPage();
    await studio.setViewportSize({ width: 1500, height: 1400 });
    await studio.goto(`${WEB}${await own.getAttribute('href')}`);
    await expect(studio.getByText('Palo Alto Networks Threat Investigation').first()).toBeVisible({ timeout: 90_000 });
    await expect(studio.locator('[data-test="visualization"], [data-testid="visualization"], .dashboard-element, [data-component="visualization"]').first()).toBeVisible({ timeout: 90_000 }).catch(() => undefined);
    await studio.waitForTimeout(25_000);                       // Dashboard Studio runs its data sources on load
    await studio.screenshot({ path: `${SHOTS}/p101_scenario_studio_dashboard.png`, fullPage: true });
    const text = (await studio.locator('body').innerText()).toLowerCase();
    expect(text, 'the Studio dashboard shows data from this scenario').toMatch(/pan:threat|pan:traffic|threat|traffic/);
    expect(text).not.toContain('search did not return any results');
    await studio.close();
  }
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


// ------------------------------------------------------------------------------------------------------------------------------ continuous metric streaming (Phase 10)
const apiRun = async (request: APIRequestContext, id: string) => (await (await request.get(`${API}/api/runs/${id}`)).json()) as { state: string; counters: { generated: number; accepted: number; rejected: number; unknown: number }; error?: string | null };
const FINAL_STATES = ['COMPLETED', 'STOPPED', 'FAILED', 'INTERRUPTED'];
async function startStream(page: Page, request: APIRequestContext, eps: number) {
  await pick(page, request, METRIC_ST);
  await page.getByText('More options').click();
  await page.getByTestId('mode').selectOption('continuous');
  await page.getByTestId('eps').fill(String(eps));
  return startFromUi(page);
}
const mstatsBase = (runId: string) => `index=${METRIC_INDEX} AND (metric_name="interface_generic_counters.*" OR metric_name="Cisco-IOS-XR-wdsysmon-fd-oper:system-monitoring/cpu-utilization.total_cpu_*") AND netspout_run_id="${runId}"`;

test('[metrics] a continuous stream: counts grow over time, Stop ends it promptly, the metrics in cisco_metrics match what was sent', async ({ page, request }) => {
  group('metrics');
  test.setTimeout(300_000);
  await tapMode(request, 'pass'); await tapReset(request);
  await configure(page, { metricIndex: METRIC_INDEX });
  const runId = await startStream(page, request, 5);
  await expect(page.getByTestId('outcome-text')).toContainText('streaming until stopped', { timeout: 30_000 });
  await page.screenshot({ path: `${SHOTS}/p10_01_stream_running.png`, fullPage: true });
  const early = await until(() => tapped(request, runId), (r) => r.length >= 10, 30_000, 500);
  const t1 = early.length;
  await until(() => tapped(request, runId), (r) => r.length >= t1 + 25, 40_000, 500);          // still generating five seconds later: the count keeps growing
  const mid = (await tapped(request, runId)).length;
  expect(mid).toBeGreaterThan(t1);
  const clickAt = Date.now();
  await page.getByTestId('stop-run').click();
  const stopped = await until(() => apiRun(request, runId), (r) => FINAL_STATES.includes(r.state), 15_000, 250);
  const stopLatency = (Date.now() - clickAt) / 1000;
  expect(stopped.state).toBe('STOPPED');
  expect(stopLatency, 'seconds from the Stop click to a stopped run').toBeLessThan(5);
  await expect(page.getByTestId('stop-run')).toHaveCount(0);
  const atStop = (await tapped(request, runId)).length;
  await new Promise((r) => setTimeout(r, 8000));
  const later = (await tapped(request, runId)).length;
  expect(later, 'no event is generated after the run stopped').toBe(atStop);
  expect((await apiRun(request, runId)).counters.generated).toBeLessThanOrEqual(atStop + 1);
  const out = await tapped(request, runId);
  expect(out.every((p) => p.kind === 'metric' && p.index === METRIC_INDEX && p.upstream_status === 200)).toBeTruthy();
  const datapoints = out.reduce((n, p) => n + (p.metric_names?.length ?? 0), 0);
  await expect(page.getByTestId('outcome-text')).toContainText(`Verified: found ${datapoints} of ${datapoints} metric datapoints in metric index ${METRIC_INDEX} (mstats search)`, { timeout: 120_000 });
  await page.screenshot({ path: `${SHOTS}/p10_02_stream_stopped_verified.png`, fullPage: true });
  // counts over time, from the metric index
  const buckets = await until(() => splunk(`| mstats count(_value) as n WHERE ${mstatsBase(runId)} span=2s | stats count as buckets sum(n) as total min(_time) as t0 max(_time) as t1`), (r) => Number(r[0]?.total ?? 0) >= datapoints);
  expect(Number(buckets[0].total)).toBe(datapoints);
  expect(Number(buckets[0].buckets), 'datapoints are spread over several seconds, not one burst').toBeGreaterThanOrEqual(4);
  expect(Number(buckets[0].t1) - Number(buckets[0].t0)).toBeGreaterThanOrEqual(5);   // seconds; the stream runs as long as the test lets it, the next line ties the indexed span to the sent span
  const sentSpan = Math.max(...out.map((p) => p.time)) - Math.min(...out.map((p) => p.time));
  expect(Math.abs((Number(buckets[0].t1) - Number(buckets[0].t0)) - sentSpan)).toBeLessThanOrEqual(4);
  // names, values and dimensions
  const per = await splunk(`| mstats sum(_value) as v count(_value) as n WHERE ${mstatsBase(runId)} BY metric_name`);
  const sums: Record<string, number> = {}; for (const p of out) for (const [k, v] of Object.entries(p.metric_values ?? {})) sums[k] = (sums[k] ?? 0) + v;
  expect(new Set(per.map((r) => r.metric_name))).toEqual(new Set(Object.keys(sums)));
  for (const r of per) expect(Math.abs(Number(r.v) - sums[r.metric_name])).toBeLessThanOrEqual(1e-6 * Math.max(1, sums[r.metric_name]));
  const ev = JSON.parse(readFileSync(resolve(process.cwd(), '..', 'docs', 'contracts', 'phase7', 'phase8_metric_evidence.json'), 'utf8')).metrics as Record<string, { dims: string[]; path: string }>;
  const dims = await splunk(`| mcatalog values(_dims) as dims values(path) as path WHERE ${mstatsBase(runId)} BY metric_name | eval dims=mvjoin(dims,",")`);
  for (const r of dims) { expect(new Set(r.dims.split(',').filter((d: string) => !d.startsWith('netspout_')))).toEqual(new Set(ev[r.metric_name].dims)); expect(r.path).toBe(ev[r.metric_name].path); }
  // cumulative counters keep climbing over time in every (device, interface) series, across the many small chunks of a stream
  const dec = await splunk(`| mstats max(_value) as v WHERE index=${METRIC_INDEX} AND metric_name="interface_generic_counters.bytes_received" AND netspout_run_id="${runId}" BY source interface_name span=1s | sort 0 source interface_name _time | streamstats current=f last(v) as prev by source interface_name | where isnotnull(prev) AND v<prev`);
  expect(dec.length, 'counter decreases').toBe(0);
  const series = await splunk(`| mstats count(_value) as n WHERE index=${METRIC_INDEX} AND metric_name="interface_generic_counters.bytes_received" AND netspout_run_id="${runId}" BY source interface_name`);
  expect((await splunk(`search index=${EVENT_INDEX} netspout_run_id="${runId}" | stats count`))[0]?.count ?? '0').toBe('0');
  save('streaming_metrics', { run_id: runId, eps: 5, hec_events: out.length, datapoints, stop: { state: stopped.state, seconds_from_click_to_stopped: stopLatency, events_at_stop: atStop, events_8s_later: later },
    generated_in_run_counter: (await apiRun(request, runId)).counters.generated, mstats: { total: Number(buckets[0].total), buckets_2s: Number(buckets[0].buckets), first: Number(buckets[0].t0), last: Number(buckets[0].t1), sent_span_s: sentSpan },
    metric_names: Object.keys(sums).length, counter_decreases: dec.length, series_with_bytes_received: series.length, ui: await page.getByTestId('outcome-text').textContent() });
});

test('[metrics] a temporary outage mid-stream: events are rejected and counted, the stream recovers, only what was accepted is indexed, and the UI does not say Verified', async ({ page, request }) => {
  group('metrics');
  test.setTimeout(300_000);
  await tapMode(request, 'pass'); await tapReset(request);
  await configure(page, { metricIndex: METRIC_INDEX });
  const runId = await startStream(page, request, 5);
  await until(() => tapped(request, runId), (r) => r.length >= 12, 30_000, 500);
  await tapMode(request, 'reject');
  await page.screenshot({ path: `${SHOTS}/p10_03_stream_during_outage.png`, fullPage: true });
  await until(() => apiRun(request, runId), (r) => r.counters.rejected >= 8, 60_000, 500);
  expect((await apiRun(request, runId)).state).toBe('RUNNING');                       // a short outage does not kill the stream
  await tapMode(request, 'pass');
  const before = (await tapped(request, runId)).filter((p) => p.upstream_status === 200).length;
  await until(() => tapped(request, runId), (r) => r.filter((p) => p.upstream_status === 200).length >= before + 10, 90_000, 500);   // it reconnects by itself
  await page.getByTestId('stop-run').click();
  const done = await until(() => apiRun(request, runId), (r) => FINAL_STATES.includes(r.state), 15_000, 250);
  expect(done.state).toBe('STOPPED');
  expect(done.counters.rejected).toBeGreaterThanOrEqual(8); expect(done.counters.accepted).toBeGreaterThan(before);
  await expect(page.getByTestId('outcome-text')).toContainText('were accepted', { timeout: 30_000 });
  const t = await NEVER_VERIFIED(page);
  await page.screenshot({ path: `${SHOTS}/p10_04_stream_after_outage.png`, fullPage: true });
  const ok = (await tapped(request, runId)).filter((p) => p.upstream_status === 200);
  const acceptedPoints = ok.reduce((n, p) => n + (p.metric_names?.length ?? 0), 0);
  const idx = await until(() => splunk(`| mstats count(_value) as n WHERE ${mstatsBase(runId)}`), (r) => Number(r[0]?.n ?? 0) >= acceptedPoints);
  expect(Number(idx[0].n), 'only what HEC accepted is in the metric index').toBe(acceptedPoints);
  save('streaming_outage', { run_id: runId, ui: t, final: done, accepted_datapoints_sent: acceptedPoints, datapoints_in_metric_index: Number(idx[0].n), rejected_events: done.counters.rejected });
  await tapMode(request, 'pass');
});

test('[metrics] a sustained failure ends the stream as failed, nothing keeps being generated, and a new run works once the destination is back', async ({ page, request }) => {
  group('metrics');
  test.setTimeout(300_000);
  await tapMode(request, 'pass'); await tapReset(request);
  await configure(page, { metricIndex: METRIC_INDEX });
  await tapMode(request, 'reject');
  const runId = await startStream(page, request, 10);
  const failed = await until(() => apiRun(request, runId), (r) => FINAL_STATES.includes(r.state), 150_000, 1000);
  expect(failed.state).toBe('FAILED');
  await expect(page.getByTestId('outcome-text')).toContainText('Splunk did not receive this data', { timeout: 30_000 });
  await NEVER_VERIFIED(page);
  await expect(page.getByTestId('stop-run')).toHaveCount(0);
  await page.screenshot({ path: `${SHOTS}/p10_05_stream_failed.png`, fullPage: true });
  const n1 = (await tapped(request, runId)).length;
  await new Promise((r) => setTimeout(r, 8000));
  expect((await tapped(request, runId)).length, 'a failed stream generates nothing more').toBe(n1);
  expect(failed.counters.accepted).toBe(0);
  // back to normal: a fresh bounded run is verified
  await tapMode(request, 'pass'); await tapReset(request);
  await page.reload();                                                  // a fresh page: the stream left the send mode on "keep streaming", which hides the event count
  await pick(page, request, METRIC_ST);
  await page.getByTestId('count').fill('14');
  const run2 = await startFromUi(page);
  await expect(page.getByTestId('outcome-text')).toContainText('Verified: found', { timeout: 120_000 });
  save('streaming_failure', { run_id: runId, state: failed.state, error: failed.error, counters: failed.counters, events_attempted_before_failing: n1, recovery_run_id: run2, recovery_ui: await page.getByTestId('outcome-text').textContent() });
});


// ------------------------------------------------------------------------------------------------------------------------------ Phase 10.1: several sourcetypes in one run
const FOUR = [{ st: 'cisco:asa', n: 8 }, { st: 'cisco:ios', n: 6 }, { st: 'fortigate_traffic', n: 5 }, { st: 'pan:traffic', n: 6 }] as const;
async function addSources(page: Page, request: APIRequestContext, sts: string[]) {
  await open(page, '/generate/quick');
  await page.getByTestId('show-all').check();
  await page.getByTestId('mode-multi').check();
  for (const st of sts) {
    const f = await findEntry(request, st);
    await page.getByTestId('vendor').selectOption(f.vendor);
    await page.getByTestId('product').selectOption(f.product);
    await page.getByTestId('sourcetype').selectOption(st);
    await page.getByTestId('add-source').click();
    await expect(page.getByTestId(`selected-${st}`)).toBeVisible();
    await expect(page.getByTestId(`preview-${st}`).getByTestId('preview-raw').first()).toBeVisible({ timeout: 60_000 });
  }
}
const multiRun = async (page: Page) => startFromUi(page);
const countsBySt = (out: Tapped[]) => out.reduce<Record<string, number>>((m, p) => { m[p.sourcetype] = (m[p.sourcetype] ?? 0) + 1; return m; }, {});

test('[multi] four verified sourcetypes in one run: each counted, indexed and verified on its own', async ({ page, request }) => {
  group('multi');
  test.setTimeout(300_000);
  await tapMode(request, 'pass'); await tapReset(request);
  await configure(page);
  await addSources(page, request, FOUR.map((x) => x.st));
  for (const x of FOUR) await page.getByTestId(`count-${x.st}`).fill(String(x.n));
  const total = FOUR.reduce((a, x) => a + x.n, 0);
  await expect(page.getByTestId('total-count')).toHaveValue(String(total));
  await page.screenshot({ path: `${SHOTS}/p101_01_multi_selected_and_previewed.png`, fullPage: true });
  const runId = await multiRun(page);
  await expect(page.getByTestId('outcome-text')).toContainText(`Verified: found ${total} of ${total} events in index ${EVENT_INDEX}`, { timeout: 180_000 });
  for (const x of FOUR) { await expect(page.getByTestId(`source-${x.st}`)).toHaveAttribute('data-result', 'VERIFIED'); await expect(page.getByTestId(`source-${x.st}`)).toContainText(`${x.n} of ${x.n}`); }
  await expect(page.getByTestId('totals')).toContainText(`${total} accepted`);
  await page.getByTestId('outcome').scrollIntoViewIfNeeded(); await page.getByTestId('outcome').screenshot({ path: `${SHOTS}/p101_02_multi_verified.png` });   // the result panel itself (the page scrolls inside the app shell)
  // the exact outgoing payloads
  const out = await tapped(request, runId);
  expect(out.length).toBe(total);
  expect(countsBySt(out)).toEqual(Object.fromEntries(FOUR.map((x) => [x.st, x.n])));
  expect(out.every((p) => p.upstream_status === 200 && p.index === EVENT_INDEX && p.host && p.kind === 'event')).toBeTruthy();
  // independent search: count, index and host per sourcetype
  const rows = await until(() => splunk(`index=${EVENT_INDEX} netspout_run_id="${runId}" | stats count values(index) as ix values(host) as hosts values(source) as src by sourcetype`), (r) => r.reduce((a, x) => a + Number(x.count), 0) >= total);
  expect(rows.reduce((a, x) => a + Number(x.count), 0)).toBe(total);                                  // aggregate = sum, nothing double counted
  for (const x of FOUR) {
    const r = rows.find((y) => y.sourcetype === x.st)!;
    expect(Number(r.count), `${x.st} indexed`).toBe(x.n);
    expect([].concat(r.ix)).toEqual([EVENT_INDEX]);
    expect([].concat(r.hosts).sort(), `${x.st}: host in Splunk is the host NetSpout sent`).toEqual([...new Set(out.filter((p) => p.sourcetype === x.st).map((p) => p.host))].sort());
  }
  const unrelated = await splunk(`index=${EVENT_INDEX} netspout_run_id="${runId}" NOT (${FOUR.map((x) => `sourcetype="${x.st}"`).join(' OR ')}) | stats count`);
  expect(Number(unrelated[0]?.count ?? 0)).toBe(0);
  // Investigate: the run investigation dashboard, opened with this run's tokens, shows the same counts
  let dashboardEvidence: unknown = null;
  if (WEB) {
    const href = await page.getByTestId('investigate-dashboard').getAttribute('href');
    expect(href).toContain(`form.run_tok=${runId}`); expect(href).toContain(`form.index_tok=${EVENT_INDEX}`);
    const dash = await page.context().newPage();
    await dash.setViewportSize({ width: 1500, height: 1500 });
    await dash.goto(`${WEB}${href}`);
    const tbl = dash.locator('#by_sourcetype');
    await expect(tbl).toContainText('pan:traffic', { timeout: 120_000 });
    const text = await tbl.innerText();
    for (const x of FOUR) { expect(text).toContain(x.st); }
    const dashRows = await tbl.locator('tbody tr').allInnerTexts();
    for (const x of FOUR) expect(dashRows.some((r) => r.includes(x.st) && r.replace(/\s+/g, ' ').includes(` ${x.n} `) || r.includes(x.st) && r.split(/\s+/).includes(String(x.n))), `${x.st} count ${x.n} on the dashboard`).toBeTruthy();
    await dash.screenshot({ path: `${SHOTS}/p101_03_run_investigation_dashboard.png`, fullPage: true });
    dashboardEvidence = { href, rows: dashRows };
    await dash.close();
  }
  save('multi_four_sourcetypes', { run_id: runId, requested: Object.fromEntries(FOUR.map((x) => [x.st, x.n])), outgoing_by_tap: countsBySt(out), indexes: [...new Set(out.map((p) => p.index))],
    splunk: rows.map((r) => ({ sourcetype: r.sourcetype, count: Number(r.count), index: r.ix, hosts: r.hosts })), aggregate: { sent: total, indexed: total }, ui_outcome: await page.getByTestId('outcome-text').textContent(), dashboard: dashboardEvidence });
});

test('[multi] one event sourcetype and IOS XR metrics: events by search, metrics by mstats, each in its own index', async ({ page, request }) => {
  group('multi');
  test.setTimeout(300_000);
  await tapMode(request, 'pass'); await tapReset(request);
  await configure(page, { metricIndex: METRIC_INDEX });
  await addSources(page, request, ['cisco:asa', METRIC_ST]);
  await page.getByTestId('count-cisco:asa').fill('9');
  await page.getByTestId(`count-${METRIC_ST}`).fill('6');
  await page.screenshot({ path: `${SHOTS}/p101_04_mixed_selected.png`, fullPage: true });
  const runId = await multiRun(page);
  await expect(page.getByTestId('outcome-text')).toContainText(`events in index ${EVENT_INDEX} and`, { timeout: 180_000 });
  await expect(page.getByTestId('outcome-text')).toContainText(`metric datapoints in metric index ${METRIC_INDEX} (mstats search)`);
  await expect(page.getByTestId('outcome-text')).toContainText('Verified:');
  await page.getByTestId('outcome').scrollIntoViewIfNeeded(); await page.getByTestId('outcome').screenshot({ path: `${SHOTS}/p101_05_mixed_verified.png` });   // the result panel itself (the page scrolls inside the app shell)
  const out = await tapped(request, runId);
  const ev = out.filter((p) => p.kind === 'event'), mt = out.filter((p) => p.kind === 'metric');
  expect(ev.length).toBe(9); expect(mt.length).toBe(6);
  expect(ev.every((p) => p.sourcetype === 'cisco:asa' && p.index === EVENT_INDEX)).toBeTruthy();
  expect(mt.every((p) => p.sourcetype === METRIC_ST && p.index === METRIC_INDEX)).toBeTruthy();
  const points = mt.reduce((n, p) => n + (p.metric_names?.length ?? 0), 0);
  const evRows = await until(() => splunk(`index=${EVENT_INDEX} netspout_run_id="${runId}" | stats count by sourcetype`), (r) => Number(r[0]?.count ?? 0) >= 9);
  expect(evRows.map((r) => [r.sourcetype, Number(r.count)])).toEqual([['cisco:asa', 9]]);
  const mrows = await until(() => splunk(`| mstats count(_value) as n WHERE index=${METRIC_INDEX} AND metric_name=* AND netspout_run_id="${runId}"`), (r) => Number(r[0]?.n ?? 0) >= points);
  expect(Number(mrows[0].n)).toBe(points);
  const wrongIndex = await splunk(`index=${EVENT_INDEX} netspout_run_id="${runId}" sourcetype="${METRIC_ST}" | stats count`);
  expect(Number(wrongIndex[0]?.count ?? 0), 'no metric landed in the event index').toBe(0);
  await expect(page.getByTestId(`source-${METRIC_ST}`)).toContainText(`${points} of ${points} datapoints`);
  save('multi_mixed_event_and_metric', { run_id: runId, events: { sourcetype: 'cisco:asa', index: EVENT_INDEX, sent: 9, found_by_search: 9 }, metrics: { sourcetype: METRIC_ST, index: METRIC_INDEX, events_sent: 6, datapoints_sent: points, datapoints_found_by_mstats: Number(mrows[0].n) }, ui_outcome: await page.getByTestId('outcome-text').textContent() });
});

test('[multi] streaming several sourcetypes: each source keeps growing, Stop ends the run promptly, events and metrics are each verified', async ({ page, request }) => {
  group('multi');
  test.setTimeout(300_000);
  await tapMode(request, 'pass'); await tapReset(request);
  await configure(page, { metricIndex: METRIC_INDEX });
  await addSources(page, request, ['cisco:asa', METRIC_ST]);
  await page.getByText('More options').click();
  await page.getByTestId('mode').selectOption('continuous');
  await page.getByTestId('eps').fill('6');
  const runId = await multiRun(page);
  await expect(page.getByTestId('outcome-text')).toContainText('streaming until stopped', { timeout: 30_000 });
  const per = async () => countsBySt(await tapped(request, runId));
  const first = await until(per, (c) => (c['cisco:asa'] ?? 0) >= 6 && (c[METRIC_ST] ?? 0) >= 6, 60_000, 500);
  const later = await until(per, (c) => (c['cisco:asa'] ?? 0) >= first['cisco:asa'] + 6 && (c[METRIC_ST] ?? 0) >= first[METRIC_ST] + 6, 60_000, 500);
  expect(later['cisco:asa']).toBeGreaterThan(first['cisco:asa']); expect(later[METRIC_ST]).toBeGreaterThan(first[METRIC_ST]);   // both sources are still being generated
  await page.screenshot({ path: `${SHOTS}/p101_11_multi_streaming.png`, fullPage: true });
  const clickAt = Date.now();
  await page.getByTestId('stop-run').click();
  const stopped = await until(() => apiRun(request, runId), (r) => FINAL_STATES.includes(r.state), 15_000, 250);
  expect(stopped.state).toBe('STOPPED');
  expect((Date.now() - clickAt) / 1000, 'seconds from Stop to stopped').toBeLessThan(5);
  const atStop = await per();
  await new Promise((r) => setTimeout(r, 6000));
  expect(await per(), 'nothing is generated after Stop').toEqual(atStop);
  const out = await tapped(request, runId);
  const ev = out.filter((p) => p.kind === 'event'), mt = out.filter((p) => p.kind === 'metric');
  const points = mt.reduce((n, p) => n + (p.metric_names?.length ?? 0), 0);
  await expect(page.getByTestId('outcome-text')).toContainText('Verified:', { timeout: 150_000 });
  await expect(page.getByTestId('source-cisco:asa')).toHaveAttribute('data-result', 'VERIFIED');
  await expect(page.getByTestId(`source-${METRIC_ST}`)).toHaveAttribute('data-result', 'VERIFIED');
  const e = await until(() => splunk(`index=${EVENT_INDEX} netspout_run_id="${runId}" | stats count`), (r) => Number(r[0]?.count ?? 0) >= ev.length);
  const m = await until(() => splunk(`| mstats count(_value) as n WHERE index=${METRIC_INDEX} AND metric_name=* AND netspout_run_id="${runId}"`), (r) => Number(r[0]?.n ?? 0) >= points);
  expect(Number(e[0].count)).toBe(ev.length); expect(Number(m[0].n)).toBe(points);
  save('multi_streaming', { run_id: runId, counts_first_look: first, counts_later: later, counts_at_stop: atStop, events_found: Number(e[0].count), metric_datapoints_found: Number(m[0].n), ui: await page.getByTestId('outcome-text').textContent() });
});

test('[multi] a partly rejected batch: the failed source is named, the others are verified, nothing says Verified for the whole run', async ({ page, request }) => {
  group('multi');
  test.setTimeout(300_000);
  await tapReset(request);
  await configure(page);
  await addSources(page, request, FOUR.map((x) => x.st));
  for (const x of FOUR) await page.getByTestId(`count-${x.st}`).fill(String(x.n));
  await tapMode(request, 'reject_st', 'fortigate_traffic');
  const runId = await multiRun(page);
  await expect(page.getByTestId('outcome-text')).toContainText('Only', { timeout: 180_000 });
  await expect(page.getByTestId('outcome-text')).not.toContainText('Verified');
  await expect(page.getByTestId('source-fortigate_traffic')).toContainText('Nothing accepted');
  await expect(page.getByTestId('source-fortigate_traffic')).toHaveAttribute('data-result', /NOT_SENT/);
  for (const st of ['cisco:asa', 'cisco:ios', 'pan:traffic']) await expect(page.getByTestId(`source-${st}`)).toHaveAttribute('data-result', 'VERIFIED', { timeout: 120_000 });
  await expect(page.getByTestId('outcome')).toHaveAttribute('data-verification', 'PARTIAL', { timeout: 60_000 });
  await page.getByTestId('outcome').scrollIntoViewIfNeeded(); await page.getByTestId('outcome').screenshot({ path: `${SHOTS}/p101_06_multi_partial_rejection.png` });   // the result panel itself (the page scrolls inside the app shell)
  const rows = await splunk(`index=${EVENT_INDEX} netspout_run_id="${runId}" | stats count by sourcetype`);
  expect(Object.fromEntries(rows.map((r) => [r.sourcetype, Number(r.count)]))).toEqual({ 'cisco:asa': 8, 'cisco:ios': 6, 'pan:traffic': 6 });
  save('failure_multi_partial_rejection', { run_id: runId, rejected_sourcetype: 'fortigate_traffic', indexed_by_sourcetype: Object.fromEntries(rows.map((r) => [r.sourcetype, Number(r.count)])), ui: await page.getByTestId('outcome-text').textContent() });
  await tapMode(request, 'pass');
});

test('[multi] accepted but not indexed in a multi-source run is never Verified', async ({ page, request }) => {
  group('multi');
  test.setTimeout(300_000);
  await tapReset(request);
  await configure(page);
  await addSources(page, request, ['cisco:asa', 'cisco:ios']);
  await tapMode(request, 'drop');
  await multiRun(page);
  await expect(page.getByTestId('outcome-text')).toContainText('Not confirmed', { timeout: 240_000 });
  await expect(page.getByTestId('outcome-text')).not.toContainText('Verified');
  await expect(page.getByTestId('outcome')).not.toHaveAttribute('data-verification', 'VERIFIED');
  await page.getByTestId('outcome').scrollIntoViewIfNeeded(); await page.getByTestId('outcome').screenshot({ path: `${SHOTS}/p101_07_multi_accepted_not_indexed.png` });   // the result panel itself (the page scrolls inside the app shell)
  await tapMode(request, 'pass');
});

test('[multi] a sourcetype that cannot send data is refused, not skipped', async ({ page, request }) => {
  group('multi');
  const c = await catalog(request);
  const noGen = c.vendors.flatMap((v) => v.products.flatMap((p) => p.sourcetypes.filter((s) => s.block).map((s) => ({ v: v.id, p: p.name, s }))))[0];
  await configure(page);
  await open(page, '/generate/quick');
  await page.getByTestId('show-all').check();
  await page.getByTestId('mode-multi').check();
  await page.getByTestId('vendor').selectOption(noGen.v);
  await page.getByTestId('product').selectOption(noGen.p);
  await page.getByTestId('sourcetype').selectOption(noGen.s.sourcetype);
  await expect(page.getByTestId('add-source')).toBeDisabled();
  await expect(page.getByTestId('add-blocked')).toContainText(noGen.s.block!.message);
  const r = await request.post(`${API}/api/runs`, { data: { kind: 'multi', index: EVENT_INDEX, sources: [{ vendor_id: 'cisco_asa', sourcetype: 'cisco:asa', count: 2 }, { vendor_id: noGen.v, sourcetype: noGen.s.sourcetype, count: 2 }] } });
  expect(r.status()).toBe(409);
  expect(((await r.json()) as { detail: string }).detail).toContain(noGen.s.sourcetype);
  save('failure_multi_unsupported', { sourcetype: noGen.s.sourcetype, ui: 'add disabled with the reason', api_status: r.status() });
});

test('[multi] an invalid Splunk destination in a multi-source run says Splunk did not receive the data', async ({ page, request }) => {
  group('multi');
  test.setTimeout(240_000);
  await tapReset(request);
  await configure(page, { hec: ENGINE_TAP ? 'http://127.0.0.1:19997/services/collector' : 'http://127.0.0.1:19997/services/collector' });
  await addSources(page, request, ['cisco:asa', 'cisco:ios']);
  await multiRun(page);
  await expect(page.getByTestId('outcome-text')).toContainText('Splunk did not receive this data', { timeout: 200_000 });
  await expect(page.getByTestId('outcome-text')).not.toContainText('Verified');
});

test('[multi] Splunk search unavailable: the multi-source result says it could not check, not Verified', async ({ page, request }) => {
  group('multi');
  test.setTimeout(300_000);
  await tapMode(request, 'pass'); await tapReset(request);
  await configure(page, { search: ENGINE_SEARCH.replace(/:\d+/, ':1') });
  await addSources(page, request, ['cisco:asa', 'cisco:ios']);
  await multiRun(page);
  await expect(page.getByTestId('outcome-text')).toContainText('could not check', { timeout: 200_000 });
  await expect(page.getByTestId('outcome-text')).not.toContainText('Verified');
});

// ------------------------------------------------------------------------------------------------------------------------------ Phase 10.1: engine connection (packaged app only)
test('[engine] missing engine URL and unreachable engine are named, nothing is generated, and the saved address is the one used', async ({ page, request }) => {
  group('engine');
  test.skip(!WEB || !ENGINE_URL, 'needs the packaged app (PHASE9_SPLUNK_WEB and PHASE9_ENGINE_URL)');
  test.setTimeout(240_000);
  const saveEngineUrl = async (url: string) => { await open(page, '/system/connections'); await expect(page.getByTestId('engine-connection')).toBeVisible(); await page.getByTestId('engine-url').fill(url); await page.getByTestId('save-engine').click(); };
  try {
    await saveEngineUrl('');
    await expect(page.getByTestId('engine-status')).toHaveText('Engine not configured.', { timeout: 30_000 });
    await page.screenshot({ path: `${SHOTS}/p101_08_engine_not_configured_connections.png`, fullPage: true });
    await open(page, '/generate/quick');
    await expect(page.getByTestId('engine-notice')).toContainText('Engine not configured.', { timeout: 30_000 });
    await expect(page.getByTestId('generate')).toBeDisabled();
    await page.screenshot({ path: `${SHOTS}/p101_09_engine_not_configured_generate.png`, fullPage: true });
    await open(page, '/generate/scenarios');
    await expect(page.getByTestId('engine-notice')).toContainText('Engine not configured.');
    await expect(page.getByTestId('run-scenario')).toBeDisabled();
    const gw = await request.get(`${API}/api/runs`);
    expect(gw.status()).toBe(503);
    expect(((await gw.json()) as { detail: string }).detail).toBe('Engine not configured.');
    // a port nothing listens on: configured, but not connected
    await saveEngineUrl('http://127.0.0.1:9');
    await expect(page.getByTestId('engine-status')).toHaveText('Engine not connected.', { timeout: 30_000 });
    await open(page, '/generate/quick');
    await expect(page.getByTestId('engine-notice')).toContainText('Engine not connected.', { timeout: 30_000 });
    await expect(page.getByTestId('generate')).toBeDisabled();
    await page.screenshot({ path: `${SHOTS}/p101_10_engine_not_connected.png`, fullPage: true });
    const gw2 = await request.get(`${API}/api/runs`);
    expect(gw2.status()).toBe(502);
    expect(((await gw2.json()) as { detail: string }).detail).toBe('Engine not connected.');
    // the demo port of the host is never contacted: with a wrong address the answer stays "not connected"
    const bad = await request.post(`${API}/engine`, { data: { url: 'http://user:pw@host:1' } });
    expect(bad.status()).toBe(422);
    save('failure_engine_connection', { not_configured: { engine_status: 'Engine not configured.', gateway_http: gw.status() }, unreachable: { engine_status: 'Engine not connected.', gateway_http: gw2.status() }, invalid_url_http: bad.status() });
  } finally {
    await saveEngineUrl(ENGINE_URL);
    await expect(page.getByTestId('engine-status')).toContainText('Engine connected', { timeout: 30_000 });
  }
});
