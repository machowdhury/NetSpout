// Opens the ten NetFlow dashboards in Splunk Web (isolated lab, INSTALLED app) bound to the latest validated run, checks the rendered page and saves a screenshot per dashboard.
// Run from frontend/:  node ../scripts/render_netflow_live.mjs [id1,id2]     Credentials: git-ignored tests/lab/ta_validation/.env.lab (never printed).
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
const { chromium } = createRequire(path.join(process.cwd(), 'package.json'))('@playwright/test');
const root = path.resolve(process.cwd(), '..');
const env = Object.fromEntries(fs.readFileSync(path.join(root, 'tests/lab/ta_validation/.env.lab'), 'utf8').split('\n').filter((l) => l.includes('=')).map((l) => [l.slice(0, l.indexOf('=')), l.slice(l.indexOf('=') + 1).trim()]));
const evDir = path.join(root, 'docs/verification/evidence/netflow');
fs.mkdirSync(path.join(evDir, 'screens'), { recursive: true });
const runs = Object.fromEntries(Object.entries(JSON.parse(fs.readFileSync(path.join(evDir, 'dashboard_validation.json'), 'utf8')).dashboards).map(([k, v]) => [k, v.run_id]));
const only = process.argv[2] ? process.argv[2].split(',') : null;
const base = `http://127.0.0.1:${env.LAB_WEB_PORT}`;
const cached = path.join(process.env.HOME, 'Library/Caches/ms-playwright/chromium_headless_shell-1234/chrome-headless-shell-mac-arm64/chrome-headless-shell');
const browser = await chromium.launch(fs.existsSync(cached) ? { executablePath: cached } : {});
const ctx = await browser.newContext({ viewport: { width: 1520, height: 2300 } });
const login = await ctx.newPage();
await login.goto(`${base}/en-US/account/login`, { waitUntil: 'domcontentloaded' });
await login.fill('input[name="username"]', 'admin');
await login.fill('input[name="password"]', env.LAB_SPLUNK_PASSWORD);
await login.keyboard.press('Enter');
await login.waitForURL((u) => !u.pathname.includes('/account/login'), { timeout: 60000 });
await login.close();

const results = {};
for (const [sid, run] of Object.entries(runs)) {
  if (only && !only.includes(sid)) continue;
  const page = await ctx.newPage();
  const url = `${base}/en-US/app/netspout/pf_${sid}?form.run_tok=${encodeURIComponent(run)}&form.global_time.earliest=-24h%40h&form.global_time.latest=now`;
  const r = { url: url.replace(base, ''), run_id: run, errors: [] };
  try {
    const resp = await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 90000 });
    r.http_status = resp ? resp.status() : null;
    await page.waitForFunction(() => document.body.innerText.includes('Question:'), null, { timeout: 90000 }).catch(() => r.errors.push('banner never rendered'));
    // wait until the panels stop loading (no progress bars / waiting text), up to 90 s
    for (let i = 0; i < 45; i++) {
      const waiting = await page.evaluate(() => (document.body.innerText.match(/Waiting for data|Loading/gi) || []).length + document.querySelectorAll('[data-test="progress-bar"], [data-test="loading"]').length);
      if (waiting === 0 && i > 3) break;
      await page.waitForTimeout(2000);
    }
    await page.waitForTimeout(3000);
    const text = await page.evaluate(() => document.body.innerText);
    r.run_selected = text.includes(run);
    r.error_text = (text.match(/(Search (failed|error)|Error in|Unable to load|Could not (load|run)|Search not found|Invalid)[^\n]{0,100}/gi) || []).slice(0, 4);
    r.no_results_panels = (text.match(/No results found|No data/gi) || []).length;
    r.title_rendered = text.includes('PulseForge');
    r.panels = await page.evaluate(() => document.querySelectorAll('[data-test="visualization"], [data-test="dashboard-panel"], .dashboard-panel').length);
    r.canvas_or_svg = await page.evaluate(() => document.querySelectorAll('svg, canvas').length);
    await page.screenshot({ path: path.join(evDir, 'screens', `${sid}.jpg`), type: 'jpeg', quality: 60, fullPage: true });
  } catch (e) { r.errors.push(String(e).slice(0, 200)); }
  r.ok = r.http_status === 200 && r.title_rendered && r.error_text.length === 0 && r.errors.length === 0 && r.run_selected;
  results[sid] = r;
  console.log((r.ok ? 'PASS ' : 'FAIL ') + sid, 'no-result panels:', r.no_results_panels, 'svg/canvas:', r.canvas_or_svg, r.error_text.length ? JSON.stringify(r.error_text) : '', r.errors.join(';'));
  await page.close();
}
const out = path.join(evDir, 'browser_render.json');
const prev = fs.existsSync(out) ? JSON.parse(fs.readFileSync(out, 'utf8')).dashboards : {};
fs.writeFileSync(out, JSON.stringify({ generated_utc: new Date().toISOString(), splunk_web: 'isolated lab, installed app', dashboards: { ...prev, ...results } }, null, 1) + '\n');
await browser.close();
