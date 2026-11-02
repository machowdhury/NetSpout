import { expect, test } from '@playwright/test';
import { readFileSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

// Authentic observation pack (Cisco IOS-XE) through the Use Case Explorer inside Splunk Web (PLAYWRIGHT_SPLUNK=1).
// The Explorer's Verify step and this spec's own splunkd search must both agree with the number of events generated.
test.skip(!process.env.PLAYWRIGHT_SPLUNK, 'Splunk lab not configured');
test.setTimeout(300_000);

const WEB = process.env.SPLUNK_WEB ?? 'http://127.0.0.1:18000';
const MGMT = process.env.SPLUNK_MGMT ?? 'https://127.0.0.1:18191';
const OUT = process.env.SHOT_DIR ?? 'test-results';
const env = Object.fromEntries(
  readFileSync(fileURLToPath(new URL('../../tests/lab/phase4e/.env.lab', import.meta.url)), 'utf8').split('\n').filter((l) => l.includes('=')).map((l) => l.split(/=(.*)/s).slice(0, 2)),
);

test('pack scenario: Explorer Select -> Configure -> Generate -> Ingest -> Verify with independent counts', async ({ page, playwright }) => {
  await page.setViewportSize({ width: 1600, height: 1400 });
  await page.goto(`${WEB}/en-US/account/login`);
  await page.locator('input[name="username"]').fill('admin');
  await page.locator('input[name="password"]').fill(env.LAB_SPLUNK_PASSWORD);
  await page.keyboard.press('Enter');
  await page.waitForURL(/\/app\//, { timeout: 60_000 });
  await page.goto(`${WEB}/en-US/app/netspout/use_case_explorer`);
  const ex = page.frameLocator('#netspout-canvas-frame');
  await ex.getByLabel('Demo-ready only').uncheck();
  await ex.getByLabel('Search use cases').fill('Cisco Change-Induced Outage');
  await expect(ex.getByTestId('explorer-card')).toHaveCount(1, { timeout: 30_000 });
  await ex.getByTestId('explorer-card').first().click();
  await ex.getByLabel('Index').selectOption('idx_network_ops');
  const run = async (step: string) => {
    const el = ex.getByTestId(`step-${step}`);
    await el.getByRole('button', { name: 'Run' }).click();
    await expect(el).toHaveClass(/ux-step--ok/, { timeout: 120_000 });
    return el;
  };
  await run('CONFIGURE');
  const gen = await run('GENERATE');
  await expect(gen).toContainText('generated 20 events');
  const runId = (await gen.textContent())!.match(/Run (\S+?):/)![1];
  await expect(await run('INGEST')).toContainText('HEC accepted 20 of 20 events');
  await expect(await run('VERIFY')).toContainText('Splunk indexed 20 of 20 events');
  await expect(ex.getByTestId('step-DASHBOARD')).toHaveClass(/ux-step--blocked/);
  await page.screenshot({ path: `${OUT}/pack-explorer.png` });

  const admin = await playwright.request.newContext({
    baseURL: MGMT, ignoreHTTPSErrors: true,
    extraHTTPHeaders: { Authorization: 'Basic ' + Buffer.from(`admin:${env.LAB_SPLUNK_PASSWORD}`).toString('base64') },
  });
  const res = await admin.post('/services/search/jobs/export', { form: { search: `search index=idx_network_ops netspout_run_id="${runId}" | stats count by netspout_phase`, output_mode: 'json', earliest_time: '-1h' } });
  const byPhase = Object.fromEntries((await res.text()).trim().split('\n').filter((l) => l.includes('"result"')).map((l) => JSON.parse(l).result).map((r) => [r.netspout_phase, Number(r.count)]));
  expect(byPhase).toEqual({ BASELINE: 3, CHANGE: 4, FAULT: 8, RECOVERY: 5 });
  writeFileSync(`${OUT}/pack-scenario.json`, JSON.stringify({ runId, byPhase }, null, 2));
  await admin.dispose();
});
