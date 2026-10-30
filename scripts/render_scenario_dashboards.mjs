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
const packs = JSON.parse(fs.readFileSync(path.join(root, 'catalog/replay_packs.json'), 'utf8')).packs;
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
for (const p of packs) {
  if (only && !only.includes(p.id)) continue;
  const sid = sessions[p.id].session_id;
  const url = `${base}/en-US/app/netspout/pf_${p.id}?form.run_tok=${encodeURIComponent(sid)}&form.global_time.earliest=-24h%40h&form.global_time.latest=now`;
  const r = { url: url.replace(base, ''), session_id: sid, errors: [] };
  try {
    const resp = await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 90000 });
    r.http_status = resp ? resp.status() : null;
    const want = String(sessions[p.id].accepted);
    await page.waitForFunction((w) => document.body.innerText.includes(w), want, { timeout: 90000 }).catch(() => r.errors.push('events count never rendered'));
    await page.waitForTimeout(6000);   // let remaining searches finish
    const text = await page.evaluate(() => document.body.innerText);
    r.title_rendered = text.includes(p.title.slice(0, 40));
    r.events_count_rendered = text.includes(want);
    r.expected_events = Number(want);
    r.panel_titles_rendered = ['Incident timeline', 'Events by phase'].every((t) => text.includes(t));
    r.run_filter_shows_session = text.includes(sid);
    r.error_text = (text.match(/(Search (failed|error)|Error in|Unable to load|Could not (load|run)|Search not found)[^\n]{0,80}/gi) || []).slice(0, 5);
    r.waiting_text = (text.match(/Waiting for (data|input)/gi) || []).length;
    r.viz_count = await page.locator('[data-test="visualization"], [data-test="splunk.singlevalue"], [data-test="splunk.table"]').count().catch(() => null);
    await page.screenshot({ path: path.join(evDir, 'screens', `${p.id}.jpg`), type: 'jpeg', quality: 60, fullPage: true });
  } catch (e) {
    r.errors.push(String(e).slice(0, 200));
  }
  r.ok = r.http_status === 200 && r.title_rendered && r.events_count_rendered && r.panel_titles_rendered && r.error_text.length === 0 && r.errors.length === 0 && r.waiting_text === 0;
  results[p.id] = r;
  console.log((r.ok ? 'PASS ' : 'FAIL ') + p.id + (r.ok ? '' : ' ' + JSON.stringify({ e: r.errors, t: r.error_text, w: r.waiting_text, c: r.events_count_rendered })));
}
const out = path.join(evDir, 'browser_render.json');
const prev = fs.existsSync(out) ? JSON.parse(fs.readFileSync(out, 'utf8')).dashboards : {};
fs.writeFileSync(out, JSON.stringify({ generated_utc: new Date().toISOString(), splunk_web: 'isolated lab', dashboards: { ...prev, ...results } }, null, 1) + '\n');
await browser.close();
