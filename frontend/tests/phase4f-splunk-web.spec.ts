import { expect, test, type Page } from '@playwright/test';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

// Live acceptance inside authenticated Splunk Web (PLAYWRIGHT_SPLUNK=1). Reads the lab password from the git-ignored
// tests/lab/phase4e/.env.lab; nothing here is mocked. SPLUNK_WEB overrides the lab URL.
test.skip(!process.env.PLAYWRIGHT_SPLUNK, 'Splunk lab not configured');
test.setTimeout(180_000);

const WEB = process.env.SPLUNK_WEB ?? 'http://127.0.0.1:18000';
const SHOTS = process.env.SHOT_DIR ?? 'test-results';
const env = Object.fromEntries(
  readFileSync(fileURLToPath(new URL('../../tests/lab/phase4e/.env.lab', import.meta.url)), 'utf8').split('\n').filter((l) => l.includes('=')).map((l) => l.split(/=(.*)/s).slice(0, 2)),
);

async function login(page: Page) {
  await page.goto(`${WEB}/en-US/account/login`);
  await page.locator('input[name="username"]').fill('admin');
  await page.locator('input[name="password"]').fill(env.LAB_SPLUNK_PASSWORD);
  await page.keyboard.press('Enter');
  await page.waitForURL(/\/app\//, { timeout: 60_000 });
}

function trackNetwork(page: Page) {
  const seen = { backendPort: [] as string[], gateway: [] as number[], failures: [] as string[] };
  page.on('request', (r) => { if (/:8081\b/.test(r.url())) seen.backendPort.push(r.url()); });
  page.on('response', (r) => {
    if (r.url().includes('/netspout_gateway/')) {
      seen.gateway.push(r.status());
      if (r.status() >= 400) seen.failures.push(`${r.status()} ${r.url()}`);
    }
  });
  return seen;
}

test('Command Center and Use Case Explorer are native nav entries that work through the Splunk origin', async ({ page }) => {
  const net = trackNetwork(page);
  await login(page);
  await page.goto(`${WEB}/en-US/app/netspout/pulseforge_command_center`);
  const nav = page.locator('[data-test="navigation"], .navbar, header').first();
  await expect(page.getByRole('link', { name: 'PulseForge Command Center' }).first()).toBeVisible({ timeout: 30_000 });
  await expect(page.getByRole('link', { name: 'Use Case Explorer' }).first()).toBeVisible();
  void nav;

  // Command Center = React home inside the app iframe
  const cc = page.frameLocator('#netspout-canvas-frame');
  await expect(cc.locator('body')).toContainText(/PulseForge|NetSpout/i, { timeout: 30_000 });
  await page.screenshot({ path: `${SHOTS}/command-center.png` });

  await page.getByRole('link', { name: 'Use Case Explorer' }).first().click();
  await page.waitForURL(/use_case_explorer/);
  const ex = page.frameLocator('#netspout-canvas-frame');
  await expect(ex.getByTestId('use-case-explorer')).toBeVisible({ timeout: 30_000 });
  await expect(ex.getByTestId('explorer-card').first()).toBeVisible();
  expect(await ex.getByLabel('Industry').locator('option').count()).toBe(19);
  await page.screenshot({ path: `${SHOTS}/use-case-explorer.png` });

  // reload keeps the Splunk session and the backend destination (no re-login, still configured)
  await page.reload();
  await expect(page.frameLocator('#netspout-canvas-frame').getByTestId('explorer-card').first()).toBeVisible({ timeout: 30_000 });
  const setup = await page.evaluate(async () => {
    const r = await fetch('/en-US/splunkd/__raw/services/netspout_gateway/api/setup', { headers: { 'X-Requested-With': 'XMLHttpRequest' } });
    const j = await r.json();
    return { status: r.status, configured: j.configured, leaksSecret: JSON.stringify(j).includes('"search_secret"') || JSON.stringify(j).includes('"hec_token"') };
  });
  expect(setup).toEqual({ status: 200, configured: true, leaksSecret: false });

  expect(net.backendPort, 'browser must never contact the backend port').toEqual([]);
  expect(net.gateway.length).toBeGreaterThan(0);
  expect(net.failures).toEqual([]);
});

test('a stock Splunk user role can read through the gateway but cannot change NetSpout state', async ({ browser, playwright }) => {
  const MGMT = process.env.SPLUNK_MGMT ?? 'https://127.0.0.1:18191';
  const admin = await playwright.request.newContext({
    baseURL: MGMT, ignoreHTTPSErrors: true,
    extraHTTPHeaders: { Authorization: 'Basic ' + Buffer.from(`admin:${env.LAB_SPLUNK_PASSWORD}`).toString('base64') },
  });
  const name = 'pf_probe_viewer';
  const password = 'Pf' + Math.random().toString(36).slice(2) + 'Xq9!';
  await admin.delete(`/services/authentication/users/${name}`);
  const created = await admin.post('/services/authentication/users', { form: { name, password, roles: 'user', output_mode: 'json' } });
  expect(created.ok()).toBeTruthy();
  try {
    const context = await browser.newContext();
    const page = await context.newPage();
    await page.goto(`${WEB}/en-US/account/login`);
    await page.locator('input[name="username"]').fill(name);
    await page.locator('input[name="password"]').fill(password);
    await page.keyboard.press('Enter');
    await page.waitForURL(/\/app\//, { timeout: 60_000 });
    await page.goto(`${WEB}/en-US/app/netspout/use_case_explorer`);
    const result = await page.evaluate(async () => {
      const csrf = document.cookie.split('; ').find((c) => c.startsWith('splunkweb_csrf_token'))?.split('=')[1] ?? '';
      const h = { 'X-Splunk-Form-Key': csrf, 'X-Requested-With': 'XMLHttpRequest', 'Content-Type': 'application/json' };
      const read = await fetch('/en-US/splunkd/__raw/services/netspout_gateway/api/explorer/summary', { headers: h });
      const write = await fetch('/en-US/splunkd/__raw/services/netspout_gateway/api/explorer/detections/x/enable', { method: 'POST', headers: h, body: '{"index":"idx_security_fw"}' });
      return { read: read.status, write: write.status };
    });
    expect(result).toEqual({ read: 200, write: 403 });
    await context.close();
  } finally {
    await admin.delete(`/services/authentication/users/${name}`);
    await admin.dispose();
  }
});
