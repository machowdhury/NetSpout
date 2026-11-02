import { expect, test } from '@playwright/test';

const sourceResponse = {
  summary: {
    schema_version: '1.0.0',
    catalog_version: 'phase13-test',
    source_count: 2,
    runnable_count: 1,
    status_counts: { IMPLEMENTED_AND_VALIDATED: 1, NOT_IMPLEMENTED: 1 },
    domain_counts: { 'Network security': 2 },
  },
  sources: [
    {
      coverage_id: 'validated',
      vendor: 'Example',
      product: 'Validated firewall',
      product_version_scope: 'Synthetic test scope',
      domain: 'Network security',
      event_family: 'Firewall events',
      native_format: 'Documented format',
      transports: ['HEC'],
      splunk_sourcetypes: ['example:firewall'],
      technology_add_on: 'None',
      cim_status: 'NOT_ESTABLISHED',
      required_fields: ['action'],
      scenario_ids: ['TEST-001'],
      catalog_source_ids: ['test-source'],
      contract_provenance: ['Test provenance'],
      validation_evidence: ['Test evidence'],
      runtime_maturity: 'SPLUNK_VALIDATED',
      splunk_observation: 'OBSERVED',
      distribution_availability: ['SPLUNK_APP', 'DOCKER_LAB'],
      status: 'IMPLEMENTED_AND_VALIDATED',
      sample_generation: { runnable: true, mode: 'DATA_SOURCE' },
      known_limitations: ['Synthetic browser fixture.'],
    },
    {
      coverage_id: 'blocked',
      vendor: 'Example',
      product: 'Unsupported endpoint',
      product_version_scope: 'None',
      domain: 'Network security',
      event_family: 'Endpoint events',
      native_format: 'Not selected',
      transports: [],
      splunk_sourcetypes: [],
      technology_add_on: 'Not selected',
      cim_status: 'NOT_ESTABLISHED',
      required_fields: [],
      scenario_ids: [],
      catalog_source_ids: [],
      contract_provenance: [],
      validation_evidence: [],
      runtime_maturity: 'NOT_IMPLEMENTED',
      splunk_observation: 'NOT_OBSERVED',
      distribution_availability: [],
      status: 'NOT_IMPLEMENTED',
      sample_generation: { runnable: false, reason: 'No source contract.' },
      known_limitations: [],
    },
  ],
};

test('security source catalog is searchable and fails closed', async ({ page }) => {
  await page.route('**/api/security-sources', (route) => route.fulfill({ json: sourceResponse }));
  await page.goto('/#/catalog/security-sources');
  await expect(page.getByTestId('security-source-catalog')).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Validated firewall', exact: true })).toBeVisible();
  await page.getByLabel('Search security sources').fill('unsupported');
  await page.getByRole('button', { name: /Unsupported endpoint/ }).click();
  await expect(page.getByText('No source contract.')).toBeVisible();
  await expect(page.getByRole('link', { name: 'Generate bounded sample' })).toHaveCount(0);
});

test('setup wizard masks secrets and reports independent health checks', async ({ page }) => {
  await page.route('**/api/setup', async (route) => {
    if (route.request().method() === 'POST') {
      const body = route.request().postDataJSON();
      expect(body.hec_token).toBe('browser-only-value');
      return route.fulfill({
        json: {
          configured: true,
          deployment_mode: body.deployment_mode,
          ...body,
          hec_token: undefined,
          search_secret: undefined,
          secret_state: { hec_token_configured: true, search_secret_configured: true },
        },
      });
    }
    return route.fulfill({
      json: {
        configured: false,
        deployment_mode: null,
        secret_state: { hec_token_configured: false, search_secret_configured: false },
      },
    });
  });
  await page.route('**/api/setup/validate', (route) => route.fulfill({
    json: {
      status: 'PASS',
      checks: [
        { id: 'hec', status: 'PASS', detail: 'HTTP 200' },
        { id: 'search', status: 'PASS', detail: 'HTTP 200' },
        { id: 'indexes', status: 'PASS', detail: 'Authorized index configured' },
      ],
    },
  }));
  await page.goto('/#/system/connections');
  await expect(page.getByTestId('setup-wizard')).toBeVisible();
  await page.getByRole('textbox', { name: 'HEC token', exact: true }).fill('browser-only-value');
  await page.getByRole('textbox', { name: 'Search credential', exact: true }).fill('browser-only-secret');
  await page.getByRole('button', { name: 'Save secure configuration' }).click();
  await expect(page.getByText('Present')).toBeVisible();
  await expect(page.getByText('browser-only-value')).toHaveCount(0);
  await page.getByRole('button', { name: 'Validate' }).click();
  await expect(page.getByText('HTTP 200').first()).toBeVisible();
});

test('source catalog supports keyboard navigation and narrow reflow', async ({ page }) => {
  await page.route('**/api/security-sources', (route) => route.fulfill({ json: sourceResponse }));
  await page.setViewportSize({ width: 320, height: 800 });
  await page.goto('/#/catalog/security-sources');
  await page.getByLabel('Search security sources').focus();
  await page.keyboard.type('unsupported');
  await page.keyboard.press('Tab');
  await expect(page.getByLabel('Filter source domain')).toBeFocused();
  const overflow = await page.evaluate(() => ({
    scroll: document.documentElement.scrollWidth,
    client: document.documentElement.clientWidth,
  }));
  expect(overflow.scroll).toBeLessThanOrEqual(overflow.client + 1);
});
