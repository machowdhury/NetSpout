// Browser check of the Live Delivery Monitor inside the INSTALLED app in the isolated lab (Splunk Web, real gateway, real engine).
// Run from frontend/:  node ../scripts/render_monitor_live.mjs [probe]     Credentials: git-ignored tests/lab/ta_validation/.env.lab (never printed).
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
const { chromium } = createRequire(path.join(process.cwd(), 'package.json'))('@playwright/test');
const root = path.resolve(process.cwd(), '..');
const env = Object.fromEntries(fs.readFileSync(path.join(root, 'tests/lab/ta_validation/.env.lab'), 'utf8').split('\n').filter((l) => l.includes('=')).map((l) => [l.slice(0, l.indexOf('=')), l.slice(l.indexOf('=') + 1).trim()]));
const evDir = path.join(root, 'docs/verification/evidence/monitor');
fs.mkdirSync(path.join(evDir, 'screens'), { recursive: true });
const base = `http://127.0.0.1:${env.LAB_WEB_PORT}`;
const cached = path.join(process.env.HOME, 'Library/Caches/ms-playwright/chromium_headless_shell-1234/chrome-headless-shell-mac-arm64/chrome-headless-shell');
const browser = await chromium.launch(fs.existsSync(cached) ? { executablePath: cached } : {});
const page = await (await browser.newContext({ viewport: { width: 1500, height: 1300 } })).newPage();
await page.goto(`${base}/en-US/account/login`, { waitUntil: 'domcontentloaded' });
await page.fill('input[name="username"]', 'admin');
await page.fill('input[name="password"]', env.LAB_SPLUNK_PASSWORD);
await page.keyboard.press('Enter');
await page.waitForURL((u) => !u.pathname.includes('/account/login'), { timeout: 60000 });
const shot = (n) => page.screenshot({ path: path.join(evDir, 'screens', n + '.jpg'), type: 'jpeg', quality: 60, fullPage: true });

const results = {};
const open = async () => {
  await page.goto(`${base}/en-US/app/netspout/use_case_explorer`, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(12000);
  return page.frames().find((f) => f !== page.mainFrame());
};
const tile = async (app, label) => Number((await app.locator(`.pf-mon div:has(> span:text-is("${label}")) > b`).first().innerText()).replace(/,/g, ''));
async function runCase(name, search, how) {
  const r = { search };
  let app = await open();
  try {
    await app.locator('input[type="checkbox"]').first().uncheck().catch(() => {});
    await app.locator('input[placeholder^="Search"]').fill(search);
    await app.waitForFunction((t) => (document.querySelector('.ux-card')?.innerText || '').toLowerCase().includes(t), search.toLowerCase().slice(0, 14), { timeout: 20000 });
    await app.locator('.ux-card').first().click();
    await app.waitForTimeout(2500);
    r.engine_card = (await app.locator('.ux-card.is-active').first().innerText()).replace(/\s+/g, ' ').slice(0, 90);
    if (how === 'replay') await app.locator('.ux-steps li').filter({ hasText: /Generate/i }).locator('button').first().click();
    else await app.locator('[data-testid="monitored-run"]').click();
    await app.waitForSelector('.pf-mon', { timeout: 30000 });
    const mid = [];
    for (let i = 0; i < 40; i++) {
      const state = await app.locator('.pf-mon-state').innerText();
      mid.push({ state, generated: await tile(app, 'Generated'), accepted: await tile(app, 'HEC accepted') });
      if (i === 1) await shot(name + '_running');
      if (['COMPLETED', 'STOPPED', 'FAILED'].includes(state) || (how === 'replay' && i > 6)) break;
      await app.waitForTimeout(700);
    }
    r.samples = mid.slice(0, 8);
    if (how === 'replay') { await app.locator('.pf-mon-actions button', { hasText: 'Stop' }).click().catch(() => {}); await app.waitForTimeout(1500); }
    for (let i = 0; i < 40 && !['COMPLETED', 'STOPPED', 'FAILED', 'INTERRUPTED'].includes(await app.locator('.pf-mon-state').innerText()); i++) await app.waitForTimeout(500);
    r.final_state = await app.locator('.pf-mon-state').innerText();
    r.counters = { generated: await tile(app, 'Generated'), attempts: await tile(app, 'Attempts'), accepted: await tile(app, 'HEC accepted'), rejected: await tile(app, 'Rejected'), unknown: await tile(app, 'Unknown'), pending: await tile(app, 'Pending') };
    r.indexed_before_verify = await app.locator('.pf-mon div:has(> span:text-is("Indexed (verified)")) > b').innerText();
    await app.locator('.pf-mon-actions button', { hasText: 'Verify in Splunk' }).click();
    for (let i = 0; i < 12; i++) { await app.waitForTimeout(4000); const v = await app.locator('.pf-mon-verify').innerText().catch(() => ''); r.verification = v; if (/VERIFIED/.test(v) && !/INCOMPLETE/.test(v)) break; await app.locator('.pf-mon-actions button', { hasText: 'Verify in Splunk' }).click(); }
    r.indexed_after_verify = await app.locator('.pf-mon div:has(> span:text-is("Indexed (verified)")) > b').innerText();
    r.controls_note = await app.locator('.pf-mon-note').first().innerText().catch(() => null);
    r.rows = await app.locator('.pf-mon-table tbody tr').count();
    await shot(name + '_final');
    // browser refresh: the monitor must come back for the same run id with the same counters
    app = await open();
    await app.locator('input[type="checkbox"]').first().uncheck().catch(() => {});
    await app.locator('input[placeholder^="Search"]').fill(search);
    await app.waitForFunction((t) => (document.querySelector('.ux-card')?.innerText || '').toLowerCase().includes(t), search.toLowerCase().slice(0, 14), { timeout: 20000 });
    await app.locator('.ux-card').first().click();
    await app.waitForSelector('.pf-mon', { timeout: 20000 });
    r.after_refresh = { state: await app.locator('.pf-mon-state').innerText(), accepted: await tile(app, 'HEC accepted') };
    r.refresh_recovered = r.after_refresh.accepted === r.counters.accepted;
    await shot(name + '_after_refresh');
    r.ok = r.refresh_recovered && /VERIFIED/.test(r.verification || '') && !/INCOMPLETE/.test(r.verification || '');
  } catch (e) { r.ok = false; r.error = String(e).slice(0, 200); await shot(name + '_error').catch(() => {}); }
  results[name] = r;
  console.log((r.ok ? 'PASS ' : 'FAIL ') + name + (r.ok ? '' : ' ' + JSON.stringify(r).slice(0, 500)));
}
async function controlsCase(name, search) {
  const r = { search };
  try {
    const app = await open();
    await app.locator('input[type="checkbox"]').first().uncheck().catch(() => {});
    await app.locator('input[placeholder^="Search"]').fill(search);
    await app.waitForFunction((t) => (document.querySelector('.ux-card')?.innerText || '').toLowerCase().includes(t), search.toLowerCase().slice(0, 14), { timeout: 20000 });
    await app.locator('.ux-card').first().click();
    await app.waitForTimeout(2000);
    await app.locator('select').filter({ hasText: 'Continuous' }).selectOption('continuous');
    await app.locator('.ux-steps li').filter({ hasText: /Generate/i }).locator('button').first().click();
    await app.waitForSelector('.pf-mon', { timeout: 30000 });
    await app.waitForTimeout(3000);
    const btn = (t) => app.locator('.pf-mon-actions button', { hasText: new RegExp('^' + t + '$') });
    await btn('Pause').click(); await app.waitForTimeout(2500);
    const paused = { state: await app.locator('.pf-mon-state').innerText(), accepted: await tile(app, 'HEC accepted') };
    await app.waitForTimeout(3000);
    const still = await tile(app, 'HEC accepted');
    await shot(name + '_paused');
    app.page().on('request', (rq) => { if (rq.method() === 'POST') (r.posts = r.posts || []).push('REQ ' + rq.url().split('/api/')[1]); });
    app.page().on('requestfailed', (rq) => { (r.posts = r.posts || []).push('FAILED ' + rq.url().split('/api/')[1] + ' ' + rq.failure()?.errorText); });
    app.page().on('response', async (resp) => { if (resp.request().method() === 'POST') (r.posts = r.posts || []).push('RESP ' + resp.url().split('/api/')[1] + ' ' + resp.status()); });
    await btn('Resume').click();
    r.seq = [];
    for (let i = 0; i < 8; i++) { await app.waitForTimeout(1000); r.seq.push((await app.locator('.pf-mon-state').innerText()) + ':' + (await tile(app, 'HEC accepted'))); }
    const resumed = { state: await app.locator('.pf-mon-state').innerText(), accepted: await tile(app, 'HEC accepted') };
    await btn('Stop').click();
    for (let i = 0; i < 40 && !['STOPPED', 'COMPLETED', 'FAILED'].includes(await app.locator('.pf-mon-state').innerText()); i++) await app.waitForTimeout(500);
    r.paused = paused; r.held_while_paused = still <= paused.accepted + 1; r.resumed = resumed; r.final_state = await app.locator('.pf-mon-state').innerText();
    r.counters = { accepted: await tile(app, 'HEC accepted'), pending: await tile(app, 'Pending') };
    await shot(name + '_stopped');
    r.ok = paused.state === 'PAUSED' && r.held_while_paused && resumed.accepted > paused.accepted && r.final_state === 'STOPPED';
  } catch (e) { r.ok = false; r.error = String(e).slice(0, 200); }
  results[name] = r;
  console.log((r.ok ? 'PASS ' : 'FAIL ') + name + (r.ok ? '' : ' ' + JSON.stringify(r).slice(0, 500)));
}
const only = process.argv[2];
if (only === 'controls' || only === 'all') { await controlsCase('replay_controls', 'credential-file access with system'); }
const cases = [
  ['unified_generation', 'Golden Scenario', 'monitored'],
  ['scenario_runner', 'Campus Core L2/3 Disturbance', 'monitored'],
  ['native_pack', 'AWS CloudTrail Recon', 'monitored'],
  ['incident_pack', '5G core user-plane degradation', 'monitored'],
  ['replay_pack', 'credential-file access with system', 'replay'],
];
for (const c of cases) if (!only || only === c[0] || only === 'all') await runCase(...c);
const file = path.join(evDir, 'browser.json');
const prev = fs.existsSync(file) ? JSON.parse(fs.readFileSync(file, 'utf8')).results : {};
fs.writeFileSync(file, JSON.stringify({ generated_utc: new Date().toISOString(), results: { ...prev, ...results } }, null, 1) + '\n');
await browser.close();
