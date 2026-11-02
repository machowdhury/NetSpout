import { expect, test, type Page } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';
import { artifactPath } from './artifact-paths';

const repoRoot = path.resolve(process.cwd(), '..');
const catalog = JSON.parse(
  fs.readFileSync(path.join(repoRoot, 'catalog', 'vendor_coverage.json'), 'utf8'),
);

catalog.summary = {
  vendor_id: 'cisco',
  products_researched: 2,
  source_contracts: 3,
  golden_sources: 0,
  golden_scenarios: 0,
  research_required: 1,
};

async function capture(page: Page, name: string, locator?: ReturnType<Page['locator']>) {
  const target = artifactPath('phase7-cisco-coverage', name);
  if (locator) {
    await locator.screenshot({ path: target });
  } else {
    await page.screenshot({ path: target, fullPage: true });
  }
}

test.beforeEach(async ({ page }) => {
  await page.route('**/api/coverage/cisco', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(catalog) });
  });
  await page.goto('/#/catalog/cisco-coverage');
  await expect(page.getByRole('heading', { name: 'Evidence before generation' })).toBeVisible();
});

test('renders truthful Cisco coverage, contracts, research gaps, and production guidance', async ({ page }) => {
  await capture(page, 'phase7-01-cisco-coverage-catalog.png');
  await capture(page, 'phase7-02-cisco-product-detail.png', page.locator('.coverage-product-header'));
  await capture(page, 'phase7-03-native-contract.png', page.getByTestId('cisco-contracts').locator('article').nth(0));
  await capture(page, 'phase7-04-splunk-contract.png', page.getByTestId('cisco-contracts').locator('article').nth(1));
  await capture(page, 'phase7-05-netspout-contract.png', page.getByTestId('cisco-contracts').locator('article').nth(2));
  await capture(page, 'phase7-06-evidence-panel.png', page.locator('.coverage-contract-evidence'));
  await capture(page, 'phase7-07-source-maturity.png', page.locator('.coverage-source-list'));

  await page.getByRole('button', { name: /Cisco Secure Access/ }).click();
  await expect(page.getByText('No authoritative source has established this contract.')).toBeVisible();
  await capture(page, 'phase7-08-research-required.png');

  await page.getByRole('button', { name: /Cisco IOS XR/ }).click();
  await page.getByRole('button', { name: 'Golden Scenario' }).click();
  await expect(page.getByTestId('golden-scenario')).toBeVisible();
  await capture(page, 'phase7-09-golden-scenario-home.png');
  await capture(page, 'phase7-10-scenario-topology.png', page.locator('.coverage-flow'));
  await capture(page, 'phase7-11-telemetry-lens.png', page.locator('.coverage-channel-grid'));
  await capture(page, 'phase7-12-incident-lens.png', page.locator('.coverage-hero-card'));
  await capture(page, 'phase7-13-splunk-lens.png', page.getByText(/SPL portability/).locator('xpath=ancestor::section[contains(@class,"technical-panel")][1]'));
  await capture(page, 'phase7-14-multi-channel-runtime.png', page.locator('.coverage-channel-grid'));

  await page.getByRole('button', { name: 'contracts' }).click();
  await capture(page, 'phase7-15-raw-evidence.png', page.getByTestId('cisco-contracts').locator('article').nth(0));
  await page.getByRole('button', { name: 'Golden Scenario' }).click();
  await capture(page, 'phase7-16-guided-investigation.png', page.getByText('Guided investigation').locator('xpath=ancestor::section[contains(@class,"technical-panel")][1]'));
  await page.getByRole('button', { name: 'contracts' }).click();
  await capture(page, 'phase7-17-field-cim-validation.png', page.getByTestId('cisco-contracts').locator('article').nth(1));

  await page.getByRole('button', { name: 'production' }).click();
  await expect(page.getByTestId('production-guidance')).toBeVisible();
  await capture(page, 'phase7-18-troubleshooting-guidance.png', page.getByText('Platform-correct troubleshooting').locator('xpath=ancestor::section[contains(@class,"technical-panel")][1]'));
  await capture(page, 'phase7-19-take-this-to-production.png', page.getByText('Take This to Production').locator('xpath=ancestor::section[contains(@class,"technical-panel")][1]'));

  await page.getByRole('button', { name: 'Golden Scenario' }).click();

  await expect(page.getByText('CIM NOT VALIDATED')).toHaveCount(0);
  await page.getByRole('button', { name: 'contracts' }).click();
  await expect(page.getByText('CIM NOT VALIDATED')).toBeVisible();
  await expect(page.getByText(/Cisco 100 Complete/i)).toHaveCount(0);
});
