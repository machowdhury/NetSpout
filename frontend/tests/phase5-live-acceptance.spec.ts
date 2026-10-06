import path from 'node:path';
import { expect, test, type Page } from '@playwright/test';

const live = process.env.NETSPOUT_PHASE5_LIVE === '1';
const healthCapture = process.env.NETSPOUT_PHASE5_HEALTH_CAPTURE;
const image = (name: string) => path.resolve(
  process.cwd(),
  '../docs/implementation/images',
  `phase5-${name}.png`,
);

async function shot(page: Page, name: string) {
  await page.screenshot({ path: image(name), fullPage: true });
}

async function runSource(
  page: Page,
  sourceId: string,
  screenshot: string,
  observationScreenshot?: string,
) {
  await page.goto('/#/observe/live-runs');
  await page.reload();
  await expect(page.getByRole('heading', { name: 'Choose what to generate' })).toBeVisible();
  await page.locator('.generation-mode-card').filter({ hasText: 'Data Source' }).click();
  await page.locator('.generation-choice').filter({ hasText: sourceId }).click();
  await page.getByRole('button', { name: /^Preview/ }).click();
  await page.getByRole('button', { name: /^Configure/ }).click();
  await page.getByRole('button', { name: 'Run Preflight' }).click();
  await expect(page.getByRole('button', { name: 'Checking…' })).toHaveCount(0, {
    timeout: 60_000,
  });
  await expect(page.getByText(/READY/).first()).toBeVisible();
  await page.getByRole('button', { name: /Continue to Run/ }).click();
  await page.getByRole('button', { name: 'Run', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Channel results' })).toBeVisible({
    timeout: 120_000,
  });
  await shot(page, screenshot);
  if (observationScreenshot) {
    await page.getByRole('button', { name: /Observe Evidence/ }).click();
    await page.getByRole('button', { name: /Refresh Splunk Observation/ }).click();
    await expect(page.getByText('Searching Splunk…')).toHaveCount(0, {
      timeout: 30_000,
    });
    await shot(page, observationScreenshot);
  }
}

test.describe('Phase 5 live Docker evidence', () => {
  test.skip(!live, 'Set NETSPOUT_PHASE5_LIVE=1 against the running Docker stack.');
  test.describe.configure({ mode: 'serial' });

  test('captures runtime-derived acceptance views', async ({ page }) => {
    test.skip(Boolean(healthCapture), 'A focused health-state capture was requested.');
    test.setTimeout(12 * 60_000);
    page.setDefaultTimeout(15_000);
    page.on('request', (request) => {
      if (request.url().includes('/api/generation/')) {
        console.log(request.method(), request.url(), request.postData() ?? '');
      }
    });
    await page.setViewportSize({ width: 1600, height: 1000 });

    await page.goto('/#/observe/pipeline-health');
    await expect(page.getByText('syslog receiver')).toBeVisible();
    await shot(page, '01-pipeline-health');

    await page.goto('/#/generate/scenarios');
    await page.getByLabel('Choose guided scenario').selectOption(
      'test-correlated-interface-degradation',
    );
    await expect(
      page.getByRole('heading', { name: 'Test Enterprise Interface Degradation' }),
    ).toBeVisible();
    await shot(page, '02-multi-telemetry-ready');
    await shot(page, '03-native-topology');
    await page.getByRole('button', { name: 'Telemetry Lens' }).click();
    await shot(page, '04-telemetry-lens');
    await page.getByRole('button', { name: 'Splunk Lens' }).click();
    await shot(page, '05-splunk-lens');

    await page.goto('/#/observe/live-runs');
    await page.locator('.scenario-card').filter({
      hasText: 'Test Enterprise Interface Degradation',
    }).click();
    await page.getByRole('button', { name: /^Preview/ }).click();
    await shot(page, '06-scenario-preview');
    await page.getByRole('button', { name: 'Advanced', exact: true }).click();
    await shot(page, '07-advanced-diagnostics');
    await page.getByRole('button', { name: /^Configure/ }).click();
    await page.getByRole('button', { name: 'Run Preflight' }).click();
    await expect(page.getByRole('button', { name: 'Checking…' })).toHaveCount(0, {
      timeout: 60_000,
    });
    await expect(page.getByText(/READY/).first()).toBeVisible();
    await shot(page, '08-protocol-preflight');
    await page.getByRole('button', { name: /Continue to Run/ }).click();
    await shot(page, '09-correlated-ready-to-run');

    await runSource(
      page,
      'ietf-syslog-rfc5424',
      '11-syslog-runtime',
      '10-splunk-observation',
    );
    await runSource(page, 'ietf-snmpv2c-ifmib', '12-snmp-runtime');
    await runSource(page, 'openconfig-gnmi-interfaces', '13-gnmi-runtime');
    await runSource(page, 'ietf-netflow-v9', '14-netflow-runtime');
    await runSource(page, 'ietf-ipfix', '15-ipfix-evidence-inspector');
  });

  test('captures a requested pipeline health state', async ({ page }) => {
    test.skip(!healthCapture, 'Set NETSPOUT_PHASE5_HEALTH_CAPTURE for this evidence.');
    await page.setViewportSize({ width: 1600, height: 1000 });
    await page.goto('/#/observe/pipeline-health');
    await expect(page.getByText('syslog receiver')).toBeVisible();
    if (healthCapture === 'collector-failure') {
      await expect(page.getByText('DEGRADED').first()).toBeVisible();
      await shot(page, '16-deliberate-collector-failure');
    } else {
      await expect(page.getByText('READY').first()).toBeVisible();
      await shot(page, '17-recovery');
    }
  });
});
