import { expect, test } from '@playwright/test';
import { readFileSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

// NetSpout incident pack through the Use Case Explorer inside Splunk Web (PLAYWRIGHT_SPLUNK=1): Verify must see the run-scoped log events AND the mstats datapoints.
test.skip(!process.env.PLAYWRIGHT_SPLUNK, 'Splunk lab not configured');
test.setTimeout(300_000);

const WEB = process.env.SPLUNK_WEB ?? 'http://127.0.0.1:18000';
const OUT = process.env.SHOT_DIR ?? 'test-results';
const env = Object.fromEntries(
  readFileSync(fileURLToPath(new URL('../../tests/lab/phase4e/.env.lab', import.meta.url)), 'utf8').split('\n').filter((l) => l.includes('=')).map((l) => l.split(/=(.*)/s).slice(0, 2)),
);

for (const [title, expectedEvents, expectedMetrics] of [['Campus link failure/recovery', 30, 50], ['5G RAN cell degradation', 30, 30]] as const) {
  test(`incident pack "${title}": Select -> Configure -> Generate -> Ingest -> Verify (events + mstats)`, async ({ page }) => {
    await page.setViewportSize({ width: 1600, height: 1400 });
    await page.goto(`${WEB}/en-US/account/login`);
    await page.locator('input[name="username"]').fill('admin');
    await page.locator('input[name="password"]').fill(env.LAB_SPLUNK_PASSWORD);
    await page.keyboard.press('Enter');
    await page.waitForURL(/\/app\//, { timeout: 60_000 });
    await page.goto(`${WEB}/en-US/app/netspout/use_case_explorer`);
    const ex = page.frameLocator('#netspout-canvas-frame');
    await ex.getByLabel('Demo-ready only').uncheck();
    await ex.getByLabel('Search use cases').fill(title);
    await expect(ex.getByTestId('explorer-card')).toHaveCount(1, { timeout: 30_000 });
    await ex.getByTestId('explorer-card').first().click();
    await ex.getByLabel('Index').selectOption('idx_network_ops');
    const run = async (step: string) => {
      const el = ex.getByTestId(`step-${step}`);
      await el.getByRole('button', { name: 'Run' }).click();
      await expect(el).toHaveClass(/ux-step--ok/, { timeout: 150_000 });
      return el;
    };
    await run('CONFIGURE');
    await expect(await run('GENERATE')).toContainText('generated 40 events');
    await expect(await run('INGEST')).toContainText('HEC accepted 40 of 40 events');
    const verify = await run('VERIFY');
    await expect(verify).toContainText(`Splunk indexed ${expectedEvents} of ${expectedEvents} events`);
    await expect(verify).toContainText(`mstats counted ${expectedMetrics} of ${expectedMetrics} metric datapoints`);
    await expect(ex.getByTestId('step-DASHBOARD')).toHaveClass(/ux-step--blocked/);
    writeFileSync(`${OUT}/incident-${expectedMetrics}.txt`, (await verify.textContent()) ?? '');
    await page.screenshot({ path: `${OUT}/incident-${expectedMetrics}.png` });
  });
}
