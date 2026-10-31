// Browser check of the INSTALLED app pages in the isolated lab: Command Center, Use Case Explorer (data through the gateway) and two dashboards opened with the run ids from e2e.json.
// Run from frontend/:  node ../scripts/render_installed_app.mjs     Credentials: git-ignored tests/lab/ta_validation/.env.lab (never printed).
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
const { chromium } = createRequire(path.join(process.cwd(), 'package.json'))('@playwright/test');
const root = path.resolve(process.cwd(), '..');
const env = Object.fromEntries(fs.readFileSync(path.join(root, 'tests/lab/ta_validation/.env.lab'), 'utf8').split('\n').filter((l) => l.includes('=')).map((l) => [l.slice(0, l.indexOf('=')), l.slice(l.indexOf('=') + 1).trim()]));
const evDir = path.join(root, 'docs/verification/evidence/installed_app');
const e2e = JSON.parse(fs.readFileSync(path.join(evDir, 'e2e.json'), 'utf8'));
const base = `http://127.0.0.1:${env.LAB_WEB_PORT}`;
fs.mkdirSync(path.join(evDir, 'screens'), { recursive: true });
const cached = path.join(process.env.HOME, 'Library/Caches/ms-playwright/chromium_headless_shell-1234/chrome-headless-shell-mac-arm64/chrome-headless-shell');
const browser = await chromium.launch(fs.existsSync(cached) ? { executablePath: cached } : {});
const page = await (await browser.newContext({ viewport: { width: 1520, height: 1100 } })).newPage();
await page.goto(`${base}/en-US/account/login`, { waitUntil: 'domcontentloaded' });
await page.fill('input[name="username"]', 'admin');
await page.fill('input[name="password"]', env.LAB_SPLUNK_PASSWORD);
await page.keyboard.press('Enter');
await page.waitForURL((u) => !u.pathname.includes('/account/login'), { timeout: 60000 });
const results = {};
async function visit(name, url, probe, wait = 25000) {
  const r = { url: url.replace(base, '') };
  try {
    const resp = await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 90000 });
    r.http_status = resp ? resp.status() : null;
    await page.waitForFunction(probe, null, { timeout: wait }).catch(() => (r.errors = ['probe not satisfied']));
    await page.waitForTimeout(4000);
    const text = await page.evaluate(() => document.body.innerText);
    r.error_text = (text.match(/(Search (failed|error)|Error in|Unable to load|Could not (load|run)|Page not found|404)[^\n]{0,80}/gi) || []).slice(0, 3);
    r.text_sample = text.replace(/\s+/g, ' ').slice(0, 160);
    await page.screenshot({ path: path.join(evDir, 'screens', `${name}.jpg`), type: 'jpeg', quality: 55, fullPage: true });
    r.ok = r.http_status === 200 && !r.errors && r.error_text.length === 0;
  } catch (e) { r.ok = false; r.errors = [String(e).slice(0, 160)]; }
  results[name] = r;
  console.log((r.ok ? 'PASS ' : 'FAIL ') + name + (r.ok ? '' : ' ' + JSON.stringify(r)));
}
await visit('command_center', `${base}/en-US/app/netspout/pulseforge_command_center`, () => /PulseForge|NetSpout/i.test(document.body.innerText));
await visit('use_case_explorer', `${base}/en-US/app/netspout/use_case_explorer`, () => document.querySelectorAll('[data-testid="explorer-card"]').length > 0 || /Use Case Explorer/i.test(document.body.innerText), 40000);
results.use_case_explorer.cards = await page.locator('[data-testid="explorer-card"]').count().catch(() => null);
await visit('dashboard_replay_session', `${base}/en-US/app/netspout/pf_rp_cloud_control_plane_activity?form.run_tok=${encodeURIComponent(e2e.runs.replay_session)}`, () => document.body.innerText.includes('12'));
await visit('dashboard_incident_run', `${base}/en-US/app/netspout/pf_network_01_campus_link?form.run_tok=${encodeURIComponent(e2e.runs.incident_run)}`, () => document.body.innerText.includes('30'));
fs.writeFileSync(path.join(evDir, 'browser.json'), JSON.stringify({ generated_utc: new Date().toISOString(), results }, null, 1) + '\n');
await browser.close();
