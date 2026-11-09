import { expect, test, type Page } from '@playwright/test';
import fs from 'fs';

// Packaged browser acceptance for the single-package Enterprise app, against a disposable Splunk Web (never a protected or remote one):
//   PLAYWRIGHT_BASE_URL=http://127.0.0.1:18000 P17_PASSWORD_FILE=<0600 file> P17_HEC_TOKEN=<token> [P17_UPLOAD=/path/netspout.spl] npx playwright test tests/phase17-splunk-web.spec.ts
// P17_UPLOAD (fresh container only) first installs the package through Splunk Web's "Install app from file". Credentials come from the environment, never from this file.
const enabled = !!process.env.PLAYWRIGHT_BASE_URL && !!process.env.P17_PASSWORD_FILE;
const pw = enabled ? fs.readFileSync(process.env.P17_PASSWORD_FILE!, 'utf8').trim() : '';
const APP = '/en-US/static/app/netspout/dist/index.html';

test.describe.configure({ mode: 'serial' });
test.setTimeout(300_000);
test.skip(!enabled, 'needs a disposable Splunk Web');

async function login(page: Page, user = 'admin', password = pw) {
  await page.goto('/en-US/account/login');
  await page.fill('input[name=username]', user);
  await page.fill('input[name=password]', password);
  await page.keyboard.press('Enter');
  await page.waitForURL(/en-US\/(app|manager)/, { timeout: 60_000 });
}

test('install netspout.spl through Splunk Web (Install app from file)', async ({ page }) => {
  test.skip(!process.env.P17_UPLOAD, 'upload step only on a fresh Splunk');
  await login(page);
  await page.goto('/en-US/manager/appinstall/_upload');
  await page.setInputFiles('input[type=file]', process.env.P17_UPLOAD!);
  await page.getByRole('button', { name: /^upload$/i }).click();
  await expect(page.locator('body')).toContainText(/restart|netspout|installed/i, { timeout: 180_000 });
  await page.screenshot({ path: 'test-results/phase17-upload.png' });
});

test('Connections shows a Splunk-managed engine and no engine URL form', async ({ page }) => {
  await login(page);
  await page.goto(APP);
  await page.getByText('Connections', { exact: true }).first().click();
  await expect(page.getByTestId('engine-status')).toContainText('managed by Splunk (healthy)', { timeout: 60_000 });
  await expect(page.getByTestId('engine-url')).toHaveCount(0);
  await expect(page.getByTestId('engine-managed-note')).toBeVisible();
  await expect(page.getByTestId('restart-engine')).toHaveCount(0);   // healthy: nothing to restart
  await page.screenshot({ path: 'test-results/phase17-connections.png' });
});

test('first-run configuration entirely in Splunk Web, then a tested connection', async ({ page }) => {
  await login(page);
  await page.goto(APP);
  await page.getByText('Connections', { exact: true }).first().click();
  await expect(page.getByTestId('setup-wizard')).toBeVisible();
  await expect(page.locator('form.setup-form')).toHaveAttribute('data-loaded', 'true', { timeout: 60_000 });
  const form = page.locator('form.setup-form');
  await form.getByLabel('Search username', { exact: true }).fill('admin');
  await form.getByLabel('HEC token', { exact: true }).fill(process.env.P17_HEC_TOKEN!);
  await form.getByLabel('Search credential', { exact: true }).fill(pw);
  await form.getByTestId('event-index').fill('dev_test_replay');
  await form.getByTestId('metric-index').fill('dev_test_replay_metrics');
  await form.getByLabel(/loopback-only lab certificate exception/).check();
  await form.getByRole('button', { name: /save secure configuration/i }).click();
  await expect(page.getByTestId('connection-status')).toContainText('A Splunk destination is saved', { timeout: 60_000 });
  await expect(page.getByTestId('connection-status')).toContainText('HEC token is stored');
  await page.getByTestId('test-index').fill('dev_test_replay');
  await page.getByTestId('test-connection').click();
  await expect(page.getByTestId('connection-summary')).toBeVisible({ timeout: 120_000 });
  const summary = await page.getByTestId('connection-summary').innerText();
  fs.mkdirSync('test-results', { recursive: true });
  fs.writeFileSync('test-results/phase17-connection-summary.txt', summary);
  expect(summary).not.toContain(process.env.P17_HEC_TOKEN!);
  expect(summary).not.toContain(pw);
});

test('Generate Data from the UI is indexed and verified by an independent search', async ({ page }) => {
  await login(page);
  await page.goto(APP);
  await page.getByText('Generate Data', { exact: true }).first().click();
  await page.getByTestId('vendor').selectOption({ label: 'Fortinet' });
  await page.getByTestId('sourcetype').selectOption('fortigate_traffic');
  await page.getByTestId('count').fill('10');
  await expect(page.getByTestId('generate')).toBeDisabled();            // nothing starts until the destination is authorized
  await page.getByTestId('authorize-destination').check();
  await page.getByTestId('generate').click();
  await expect(page.getByTestId('outcome')).toHaveAttribute('data-verification', 'VERIFIED', { timeout: 240_000 });
  await expect(page.getByTestId('totals')).toContainText('10 accepted');
  await page.screenshot({ path: 'test-results/phase17-generate-verified.png' });
});

test('a viewer sees the app but is refused when starting a run', async ({ browser }) => {
  test.skip(!process.env.P17_VIEWER_PASSWORD, 'viewer user is created by the acceptance driver');
  const ctx = await browser.newContext();
  const page = await ctx.newPage();
  await login(page, 'p17_viewer', process.env.P17_VIEWER_PASSWORD!);
  await page.goto(APP);
  await page.getByText('Generate Data', { exact: true }).first().click();
  await page.getByTestId('vendor').selectOption({ label: 'Fortinet' });
  await page.getByTestId('sourcetype').selectOption('fortigate_traffic');
  await page.getByTestId('authorize-destination').check();
  await page.getByTestId('generate').click();
  await expect(page.locator('body')).toContainText(/netspout_admin|capability|403|not allowed|forbidden/i, { timeout: 60_000 });
  await ctx.close();
});
