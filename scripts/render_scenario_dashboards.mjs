// Opens every installed pf_* dashboard in Splunk Web (isolated lab) with the run context applied, checks the rendered page and saves a screenshot.
// Run from frontend/ so node_modules resolves:  node ../scripts/render_scenario_dashboards.mjs [id1,id2,...]
// Credentials come from the git-ignored tests/lab/ta_validation/.env.lab and are never printed.
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';

const { chromium } = createRequire(path.join(process.cwd(), 'package.json'))('@playwright/test');

const root = path.resolve(process.cwd(), '..');
const env = Object.fromEntries(fs.readFileSync(path.join(root, 'tests/lab/ta_validation/.env.lab'), 'utf8').split('\n').filter((l) => l.includes('=')).map((l) => [l.slice(0, l.indexOf('=')), l.slice(l.indexOf('=') + 1).trim()]));
const evDir = path.join(root, 'docs/verification/evidence/dashboards');
const sessions = JSON.parse(fs.readFileSync(path.join(evDir, 'sessions.json'), 'utf8')).sessions;
const shots = new Set((process.env.SHOT || '').split(',').filter(Boolean));   // screenshots are stored only for these ids (all tabs)
const SENT = { NOC: 'Affected assets and services', Engineer: 'Telemetry volume trend by source', Overview: 'Detection status', Investigation: 'Investigation evidence', Evidence: 'Provenance and contract' };
const only = process.argv[2] ? process.argv[2].split(',') : null;
const base = `http://127.0.0.1:${env.LAB_WEB_PORT}`;
fs.mkdirSync(path.join(evDir, 'screens'), { recursive: true });

// The cached Chromium build (1234) predates the installed playwright's expected build; use it explicitly when present.
const cached = path.join(process.env.HOME, 'Library/Caches/ms-playwright/chromium_headless_shell-1234/chrome-headless-shell-mac-arm64/chrome-headless-shell');
const browser = await chromium.launch(fs.existsSync(cached) ? { executablePath: cached } : {});
const ctx = await browser.newContext({ viewport: { width: 1520, height: 1900 } });
const page = await ctx.newPage();
await page.goto(`${base}/en-US/account/login`, { waitUntil: 'domcontentloaded' });
await page.fill('input[name="username"]', 'admin');
await page.fill('input[name="password"]', env.LAB_SPLUNK_PASSWORD);
await page.keyboard.press('Enter');
await page.waitForURL((u) => !u.pathname.includes('/account/login'), { timeout: 60000 });

const results = {};
async function renderOne(pid, info) {
  const page = await ctx.newPage();
  const sid = info.run;
  const url = `${base}/en-US/app/netspout/pf_${pid}?form.run_tok=${encodeURIComponent(sid)}&form.global_time.earliest=-24h%40h&form.global_time.latest=now`;
  const r = { url: url.replace(base, ''), session_id: sid, family: info.family, errors: [], tabs: {} };
  try {
    const resp = await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 90000 });
    r.http_status = resp ? resp.status() : null;
    const want = String(info.expected_events);
    await page.waitForFunction((w) => document.body.innerText.includes(w), want, { timeout: 90000 }).catch(() => r.errors.push('events count never rendered'));
    await page.waitForTimeout(5000);
    let text = await page.evaluate(() => document.body.innerText);
    r.title_rendered = text.includes(info.title.slice(0, 30));
    r.events_count_rendered = text.includes(want);
    r.expected_events = Number(want);
    r.run_filter_shows_session = text.includes(sid);
    const labels = info.kind === 'operational' ? ['NOC', 'Engineer', 'Evidence'] : ['Overview', 'Investigation', 'Evidence'];
    for (const [i, label] of labels.entries()) {
      if (i > 0) { await page.getByText(label, { exact: true }).first().click({ timeout: 15000 }).catch((e) => r.errors.push('tab ' + label + ': ' + String(e).slice(0, 80))); await page.waitForTimeout(6000); text = await page.evaluate(() => document.body.innerText); }
      const t = { sentinel_rendered: text.includes(SENT[label]), error_text: (text.match(/(Search (failed|error)|Error in|Unable to load|Could not (load|run)|Search not found)[^\n]{0,80}/gi) || []).slice(0, 3), waiting: (text.match(/Waiting for (data|input)/gi) || []).length };
      r.tabs[label] = t;
      if (shots.has(pid)) await page.screenshot({ path: path.join(evDir, 'screens', `${pid}__${label}.jpg`), type: 'jpeg', quality: 55, fullPage: true });
    }
  } catch (e) {
    r.errors.push(String(e).slice(0, 200));
  }
  const tabsOk = Object.values(r.tabs).length === 3 && Object.values(r.tabs).every((t) => t.sentinel_rendered && t.error_text.length === 0 && t.waiting === 0);
  r.ok = r.http_status === 200 && r.title_rendered && r.events_count_rendered && tabsOk && r.errors.length === 0;
  results[pid] = r;
  console.log((r.ok ? 'PASS ' : 'FAIL ') + pid + (r.ok ? '' : ' ' + JSON.stringify({ e: r.errors, c: r.events_count_rendered, t: r.tabs })));
  await page.close();
}
const queue = Object.entries(sessions).filter(([pid]) => !only || only.includes(pid));
const conc = Number(process.env.CONC || 4);   // bounded concurrency: a few independent pages against the lab
await Promise.all(Array.from({ length: conc }, async () => { for (let item; (item = queue.shift());) await renderOne(item[0], item[1]); }));
const out = path.join(evDir, 'browser_render.json');
const prev = fs.existsSync(out) ? JSON.parse(fs.readFileSync(out, 'utf8')).dashboards : {};
fs.writeFileSync(out, JSON.stringify({ generated_utc: new Date().toISOString(), splunk_web: 'isolated lab', dashboards: only ? { ...prev, ...results } : results }, null, 1) + '\n');
await browser.close();
