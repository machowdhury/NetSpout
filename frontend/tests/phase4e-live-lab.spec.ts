import { expect, test } from '@playwright/test';

// Live acceptance: requires a configured Connection Center pointing at a real Splunk lab (PLAYWRIGHT_LIVE=1).
// Every step must turn green from backend evidence; nothing here is mocked.
test.skip(!process.env.PLAYWRIGHT_LIVE, 'live Splunk lab not configured');
test.setTimeout(240_000);

async function run(page: import('@playwright/test').Page, step: string) {
  const el = page.getByTestId(`step-${step}`);
  await el.getByRole('button', { name: 'Run' }).click();
  await expect(el).toHaveClass(/ux-step--ok/, { timeout: 120_000 });
  return el;
}

test('operational: DNS scenario Select -> Configure -> Generate -> Ingest -> Verify -> Dashboard', async ({ page }) => {
  await page.goto('/#/explore');
  await page.getByLabel('Search use cases').fill('DNS Diversity');
  await page.getByTestId('explorer-card').first().click();
  await expect(page.getByLabel('Index')).toHaveValue('idx_network_ops');
  await run(page, 'CONFIGURE');
  const gen = await run(page, 'GENERATE');
  await expect(gen).toContainText('GENERATED: PROVEN');
  await expect(await run(page, 'INGEST')).toContainText(/SPLUNK_DISPATCHED \S+: PROVEN/);
  await expect(await run(page, 'VERIFY')).toContainText('SPLUNK_OBSERVED: PROVEN');
  const dash = await run(page, 'DASHBOARD');
  await expect(dash).toContainText('Dashboard maturity: DATA_VALIDATED');
  await expect(dash).not.toContainText(/DASHBOARD_READY/);
});

test('security: React2Shell Select -> Prerequisites -> Generate -> Ingest -> Enable -> Verify', async ({ page }) => {
  await page.goto('/#/explore');
  await page.getByLabel('Type').selectOption('security');
  await expect(page.getByTestId('explorer-card')).toHaveCount(1);
  await page.getByTestId('explorer-card').first().click();
  await page.getByLabel('Index').selectOption('idx_security_fw');
  await run(page, 'PREREQUISITES');
  await expect(await run(page, 'GENERATE')).toContainText('integrity checked');
  await expect(await run(page, 'INGEST')).toContainText('Splunk observed 1 events (OBSERVED)');
  await expect(await run(page, 'ENABLE_DETECTION')).toContainText('ENABLED');
  await expect(await run(page, 'VERIFY')).toContainText('POSITIVE_CASE_VALIDATED');
});
