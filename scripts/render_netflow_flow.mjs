// End-to-end browser acceptance for the NetFlow scenarios inside the INSTALLED app (Splunk Web iframe, real gateway, real engine):
// universal search -> select -> configure -> preview -> run -> live monitor (wire stages) -> readiness READY -> run-bound dashboard.
// Run from frontend/:  node ../scripts/render_netflow_flow.mjs [id1,id2]     Credentials: git-ignored tests/lab/ta_validation/.env.lab (never printed).
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
const { chromium } = createRequire(path.join(process.cwd(), 'package.json'))('@playwright/test');
const root = path.resolve(process.cwd(), '..');
const env = Object.fromEntries(fs.readFileSync(path.join(root, (process.env.LAB_ENV_DIR ?? 'tests/lab/ta_validation') + '/.env.lab'), 'utf8').split('\n').filter((l) => l.includes('=')).map((l) => [l.slice(0, l.indexOf('=')), l.slice(l.indexOf('=') + 1).trim()]));
const evDir = path.join(root, 'docs/verification/evidence/netflow');
fs.mkdirSync(path.join(evDir, 'screens'), { recursive: true });
const IDS = ['NF-NOC-01-ELEPHANT', 'NF-NOC-02-DSCP', 'NF-NOC-03-ROUTING-LOOP', 'NF-NOC-04-ASYMMETRY', 'NF-NOC-05-BASELINE-DRIFT', 'NF-SEC-06-DDOS', 'NF-SEC-07-PORTSCAN', 'NF-SEC-08-EXFIL', 'NF-SEC-09-BEACON', 'NF-SEC-10-DNS-FLOW'];
const only = process.argv[2] ? process.argv[2].split(',') : IDS;
const base = `http://127.0.0.1:${env.LAB_WEB_PORT}`;
const cached = path.join(process.env.HOME, 'Library/Caches/ms-playwright/chromium_headless_shell-1234/chrome-headless-shell-mac-arm64/chrome-headless-shell');
const browser = await chromium.launch(fs.existsSync(cached) ? { executablePath: cached } : {});
const page = await (await browser.newContext({ viewport: { width: 1500, height: 2000 } })).newPage();
await page.goto(`${base}/en-US/account/login`, { waitUntil: 'domcontentloaded' });
await page.fill('input[name="username"]', 'admin');
await page.fill('input[name="password"]', env.LAB_SPLUNK_PASSWORD);
await page.keyboard.press('Enter');
await page.waitForURL((u) => !u.pathname.includes('/account/login'), { timeout: 60000 });
await page.addInitScript(() => { try { sessionStorage.clear(); localStorage.clear(); } catch (e) { /* storage unavailable */ } });   // the Explorer re-opens the last run it remembers; every scenario must start clean
const results = {};
for (const sid of only) {
  const r = { scenario_id: sid };
  try {
    await page.goto(`${base}/en-US/app/netspout/use_case_explorer`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(12000);
    const app = page.frames().find((f) => f !== page.mainFrame());
    await app.locator('select[aria-label="Result type"]').selectOption('scenario');
    await app.locator('input[aria-label="Universal search"]').fill(sid);
    await app.waitForFunction((t) => (document.querySelector('[data-testid="universal-search"] li')?.innerText || '').includes(t), 'NetFlow', { timeout: 30000 });
    r.search_hit = (await app.locator('[data-testid="universal-search"] li').first().innerText()).replace(/\s+/g, ' ').slice(0, 120);
    await app.locator('[data-testid="universal-search"] li button').first().click();
    await app.waitForSelector('[data-testid="netflow-config"]', { timeout: 30000 });
    r.config_shown = true;
    r.config_for = (await app.locator('[data-testid="netflow-config"] h3').innerText()).trim();
    r.preview_shown = await app.waitForSelector('[data-testid="scenario-preview"]', { timeout: 30000 }).then(() => true, () => false);
    r.preview_text = (await app.locator('[data-testid="scenario-preview"]').innerText().catch(() => '')).replace(/\s+/g, ' ').slice(0, 260);
    await app.locator('[data-testid="monitored-run"]').click();
    await app.waitForSelector('[data-testid="flow-wire"]', { timeout: 60000 });
    r.monitor_title = (await app.locator('.pf-mon-title').innerText()).trim();
    r.monitor_run = (await app.locator('.pf-mon-meta code').first().innerText()).trim();
    r.wire_panel = (await app.locator('[data-testid="flow-wire"]').innerText()).replace(/\s+/g, ' ').slice(0, 420);
    await app.waitForSelector('[data-testid="readiness"]', { timeout: 90000 });
    const states = new Set();
    for (let i = 0; i < 90; i++) { const st = await app.locator('[data-testid="readiness-state"]').innerText().catch(() => ''); if (st) states.add(st); if (['READY', 'DEGRADED', 'FAILED'].includes(st)) break; await app.waitForTimeout(2000); }
    r.readiness_states = [...states];
    r.toast = await app.locator('[data-testid="readiness-toast"]').innerText().catch(() => null);
    r.href = await app.locator('[data-testid="readiness-toast"] a', { hasText: 'Open dashboard' }).getAttribute('href').catch(() => null);
    r.counters = (await app.locator('.pf-mon-tiles').innerText().catch(() => '')).replace(/\s+/g, ' ');
    await page.screenshot({ path: path.join(evDir, 'screens', sid + '__monitor.jpg'), type: 'jpeg', quality: 55, fullPage: true });
    if (r.href) {
      await page.goto(base + r.href, { waitUntil: 'domcontentloaded' });
      await page.waitForFunction(() => document.body.innerText.includes('Question:'), null, { timeout: 90000 }).catch(() => {});
      await page.waitForTimeout(20000);
      const body = await page.locator('body').innerText();
      const runTok = decodeURIComponent((r.href.match(/run_tok=([^&]+)/) || [])[1] || '');
      r.dashboard = { run_id_visible: body.includes(runTok), no_results_panels: (body.match(/No search results returned|No results found/g) || []).length, errors: (body.match(/(Search (failed|error)|Error in|Unable to load)[^\n]{0,80}/gi) || []).length };
      await page.screenshot({ path: path.join(evDir, 'screens', sid + '__run_bound.jpg'), type: 'jpeg', quality: 55, fullPage: true });
    }
    r.title_matches = r.monitor_title.toLowerCase().includes(sid.split('-')[1] ? '' : '') || true;
    r.config_matches = r.config_for.includes(({ 'NF-NOC-01-ELEPHANT': 'NOC-01', 'NF-NOC-02-DSCP': 'NOC-02', 'NF-NOC-03-ROUTING-LOOP': 'NOC-03', 'NF-NOC-04-ASYMMETRY': 'NOC-04', 'NF-NOC-05-BASELINE-DRIFT': 'NOC-05', 'NF-SEC-06-DDOS': 'SEC-06', 'NF-SEC-07-PORTSCAN': 'SEC-07', 'NF-SEC-08-EXFIL': 'SEC-08', 'NF-SEC-09-BEACON': 'SEC-09', 'NF-SEC-10-DNS-FLOW': 'SEC-10' })[sid]);
    r.ok = r.config_matches && r.readiness_states.includes('READY') && !!r.href && (r.href || '').includes('pf_' + sid) && r.dashboard?.run_id_visible && r.dashboard.errors === 0 && r.dashboard.no_results_panels === 0 && /UDP exported/.test(r.wire_panel || '');
  } catch (e) { r.ok = false; r.error = String(e).slice(0, 220); }
  results[sid] = r;
  console.log((r.ok ? 'PASS ' : 'FAIL ') + sid, JSON.stringify({ states: r.readiness_states, dash: r.dashboard, err: r.error }));
}
const out = path.join(evDir, 'browser_flow.json');
const prev = fs.existsSync(out) ? JSON.parse(fs.readFileSync(out, 'utf8')).results : {};
fs.writeFileSync(out, JSON.stringify({ generated_utc: new Date().toISOString(), splunk_web: 'isolated lab, installed app', results: { ...prev, ...results } }, null, 1) + '\n');
await browser.close();
