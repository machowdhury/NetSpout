import { expect, test } from '@playwright/test';
import { mkdir } from 'node:fs/promises';
import path from 'node:path';

test.beforeEach(async ({ page }) => {
  await page.route('**/health', async (route) => {
    await route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify({ status: 'ok', service: 'netspout-simulation-engine' }),
    });
  });

  await page.route('**/api/health/pipelines', async (route) => {
    await route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify({
        status: 'DEGRADED',
        pipelines: {
          syslog: {
            state: 'LISTENING',
            type: 'Embedded RFC 5424/3164 Syslog Receiver',
            host: '127.0.0.1',
            port: 1514,
            captured_count: 0,
          },
          gnmi: {
            state: 'NOT AVAILABLE',
            type: 'Native gNMI Server',
          },
        },
      }),
    });
  });
});

test('supports navigation, domains, and experience modes', async ({ page }) => {
  await page.goto('/#/');

  await expect(page.getByRole('heading', { name: 'Overview', exact: true })).toBeVisible();
  await expect(page.getByText('Unified Enterprise Telemetry Lab').first()).toBeVisible();

  for (const domain of [
    'NetOps',
    'SecOps',
    'ITOps',
    'Observability',
    'Agentic AI',
    'Supply Chain',
  ]) {
    await expect(page.getByRole('button', { name: new RegExp(domain) })).toBeVisible();
  }

  await page.getByRole('button', { name: /SecOps/ }).click();
  await expect(page.getByText('Current perspective').locator('..')).toContainText('SecOps');

  await expect(page.getByRole('button', { name: 'Scenario Builder' })).toHaveCount(0);
  await page.getByRole('button', { name: 'Advanced', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Scenario Builder' })).toBeVisible();

  await page.locator('.app-nav').getByRole('button', { name: 'Quick Generate', exact: true }).click();
  await expect(page).toHaveURL(/#\/generate\/quick$/);
  await expect(page.getByRole('heading', { name: 'Quick Generate', exact: true })).toBeVisible();

  await page.getByRole('button', { name: /Telemetry Explorer/ }).click();
  await expect(page).toHaveURL(/#\/observe\/telemetry$/);
  await expect(page.getByText('PLANNED').first()).toBeVisible();
});

test('renders responsive navigation and captures Phase 1 evidence', async ({ page }) => {
  await page.goto('/#/');
  await page.setViewportSize({ width: 1440, height: 1000 });

  const evidenceDir = path.resolve(process.cwd(), '../docs/implementation/images');
  await mkdir(evidenceDir, { recursive: true });
  await page.screenshot({
    path: path.join(evidenceDir, 'phase1-unified-shell.png'),
    fullPage: true,
  });

  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByRole('button', { name: 'Open navigation' }).click();
  await expect(page.getByRole('dialog', { name: 'Navigation' })).toBeVisible();
  await page.getByRole('button', { name: 'Pipeline Health' }).click();
  await expect(page).toHaveURL(/#\/observe\/pipeline-health$/);
  await expect(page.locator('h1', { hasText: 'Pipeline Health' })).toBeVisible();
});
