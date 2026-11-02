import { expect, test } from '@playwright/test';

// Runs against the real backend (proxied by the dev server). Connection Center is expected to be unconfigured,
// so these tests assert truthful gating, not live Splunk results.
test.describe('Use Case Explorer', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/#/explore');
    await expect(page.getByTestId('use-case-explorer')).toBeVisible();
    await expect(page.getByTestId('explorer-card').first()).toBeVisible();
  });

  test('lists 18 industries and shows the approved taxonomy with editorial-mapping caveat', async ({ page }) => {
    await expect(page.getByRole('note')).toContainText('editorial');
    const industries = page.getByLabel('Industry').locator('option');
    expect(await industries.count()).toBe(19); // 18 + "All industries"
  });

  test('every approved industry lists documented candidates that are never runnable', async ({ page }) => {
    await page.getByLabel('Demo-ready only').uncheck();
    await page.getByLabel('Industry').selectOption('insurance-insurtech');
    const cards = page.getByTestId('explorer-card');
    await expect(cards.first()).toContainText('Cataloged candidate');
    await cards.first().click();
    await expect(page.getByTestId('candidate-provenance')).toContainText('Documented candidate, not executable');
    await expect(page.getByTestId('explorer-workflow').getByRole('button', { name: 'Run' })).toHaveCount(0);
  });

  test('search narrows results and empty industries are not padded', async ({ page }) => {
    await page.getByLabel('Search use cases').fill('dns');
    await expect(page.getByTestId('explorer-card').first()).toContainText(/dns/i);
    await page.getByLabel('Search use cases').fill('');
    await page.getByLabel('Industry').selectOption('insurance-insurtech');
    await expect(page.getByText('Nothing matches.')).toBeVisible();
  });

  test('operational workflow shows ordered steps and never claims dashboard readiness', async ({ page }) => {
    await page.getByLabel('Type').selectOption('operational');
    await expect(page.getByTestId('explorer-card').first()).toContainText('Operational');
    await page.getByTestId('explorer-card').first().click();
    const wf = page.getByTestId('explorer-workflow');
    for (const step of ['SELECT', 'CONFIGURE', 'GENERATE', 'INGEST', 'VERIFY', 'DASHBOARD']) {
      await expect(wf.getByTestId(`step-${step}`)).toBeVisible();
    }
    await expect(wf.getByTestId('step-DASHBOARD')).not.toContainText(/dashboard[_ ]ready/i);
    // Without a run, verify must refuse rather than pass.
    await wf.getByTestId('step-VERIFY').getByRole('button', { name: 'Run' }).click();
    await expect(wf.getByTestId('step-VERIFY')).toContainText('Run the Generate step first');
  });

  test('security story: only runtime-approved stories offer the full workflow, with no dashboard step', async ({ page }) => {
    await page.getByLabel('Type').selectOption('security');
    await expect(page.getByTestId('explorer-card')).toHaveCount(1); // exactly one runtime-approved story today
    await expect(page.getByTestId('explorer-card').first()).toContainText('RUNTIME APPROVED');
    await page.getByTestId('explorer-card').first().click();
    const wf = page.getByTestId('explorer-workflow');
    await expect(wf.getByTestId('step-PREREQUISITES')).toBeVisible();
    await expect(wf.getByTestId('step-ENABLE_DETECTION')).toBeVisible();
    await expect(wf.getByTestId('step-DASHBOARD')).toHaveCount(0);
    await expect(wf).toContainText('Security stories do not require a dashboard');
    // Unconfigured Connection Center: prerequisites must report FAIL, not pass.
    await wf.getByTestId('step-PREREQUISITES').getByRole('button', { name: 'Run' }).click();
    await expect(wf.getByTestId('step-PREREQUISITES')).toContainText('FAIL · Connection Center configured');
    await expect(wf.getByTestId('step-PREREQUISITES')).toContainText('NOT_TESTED');
  });

  test('replay-only story blocks enable and verify with a reason', async ({ page }) => {
    await page.getByLabel('Type').selectOption('security');
    await page.getByLabel('Search use cases').fill('phishing');
    await page.getByLabel('Demo-ready only').uncheck();
    await expect(page.getByTestId('explorer-card').first()).toContainText('REPLAY ONLY');
    await page.getByTestId('explorer-card').first().click();
    const wf = page.getByTestId('explorer-workflow');
    await expect(wf.getByTestId('step-ENABLE_DETECTION')).toContainText('Blocked');
    await expect(wf.getByTestId('step-VERIFY')).toContainText('Blocked');
  });
});
