import { expect, test, type Page } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';
import { artifactPath } from './artifact-paths';

const repoRoot = path.resolve(process.cwd(), '..');
const source = JSON.parse(
  fs.readFileSync(path.join(repoRoot, 'catalog', 'cisco_100_scenarios.json'), 'utf8'),
);

const maturityNames = [
  'CANDIDATE', 'RESEARCHED', 'CONTRACTED', 'FORMAT_VALIDATED',
  'RUNTIME_VALIDATED', 'SPLUNK_VALIDATED', 'GOLDEN',
  'RESEARCH_REQUIRED', 'UNSUPPORTED', 'BLOCKED',
];
const countBy = (values: string[]) =>
  values.reduce<Record<string, number>>((result, value) => {
    result[value] = (result[value] ?? 0) + 1;
    return result;
  }, {});

const domains = countBy(source.scenarios.map((item: { domain: string }) => item.domain));
const maturityObserved = countBy(source.scenarios.map((item: { maturity: string }) => item.maturity));
const maturity = Object.fromEntries(maturityNames.map((item) => [item, maturityObserved[item] ?? 0]));
const unique = (values: string[]) => new Set(values.filter(Boolean)).size;
const catalog = {
  ...source,
  summary: {
    scenario_definitions: source.scenarios.length,
    domains,
    maturity,
    products_represented: unique(source.scenarios.flatMap((item: { technologies: string[] }) => item.technologies)),
    source_contracts: unique(source.scenarios.flatMap((item: { source_contracts: string[] }) => item.source_contracts)),
    native_protocols: unique(source.scenarios.flatMap((item: { native_transports: string[] }) => item.native_transports)),
    verified_splunk_integrations: unique(source.scenarios.flatMap((item: { splunk_integrations: string[] }) => item.splunk_integrations)),
  },
  evidence_debt: {
    missing_native_contract: source.scenarios.filter((item: { source_contracts: string[] }) => !item.source_contracts.length).length,
    missing_splunk_mapping: source.scenarios.filter((item: { splunk_integrations: string[] }) => !item.splunk_integrations.length).length,
    runtime_blocked: source.scenarios.filter((item: { runtime_validation: string[] }) => !item.runtime_validation.length).length,
    cim_not_established: source.scenarios.filter((item: { cim_relationships: Record<string, string> }) =>
      !Object.keys(item.cim_relationships).length || Object.values(item.cim_relationships).includes('NOT_ESTABLISHED')).length,
    provenance_blocked: 0,
    licensing_blocked: 0,
  },
  filter_result_count: source.scenarios.length,
  query_ms: 0.1,
};

const image = (number: number, name: string) =>
  artifactPath(
    'phase8-cisco100',
    `phase8-${String(number).padStart(2, '0')}-${name}.png`,
  );

async function capture(page: Page, number: number, name: string, selector?: string) {
  if (selector) {
    await page.locator(selector).screenshot({ path: image(number, name) });
  } else {
    await page.screenshot({ path: image(number, name), fullPage: true });
  }
}

async function selectScenario(page: Page, id: string) {
  await page
    .getByTestId('cisco100-scenario-list')
    .getByRole('button', { name: new RegExp(id) })
    .click();
  await expect(page.getByTestId('cisco100-scenario-detail')).toContainText(id);
}

test.beforeEach(async ({ page }) => {
  await page.route('**/api/cisco100/scenarios/*/studio-draft', async (route) => {
    const id = route.request().url().split('/').at(-2) ?? 'C100-ENT-001';
    const scenario = source.scenarios.find((item: { scenario_id: string }) => item.scenario_id === id);
    const zoneId = 'reserved-test-environment';
    const draft = {
      pack_id: `private-${id.toLowerCase()}-definition`,
      scenario_id: `studio-${id.toLowerCase()}-definition`,
      title: `${scenario.title} — Private Definition`,
      description: scenario.technical_objective,
      story: scenario.story,
      creation_path: 'CLONE_SCENARIO',
      maturity: 'DRAFT',
      privacy_status: 'SANITIZED',
      provenance: 'NETSPOUT GENERATED',
      redistribution: 'PRIVATE',
      source_ids: [],
      custom_sources: [],
      zones: [{ zone_id: zoneId, label: 'Reserved Test Environment' }],
      entities: scenario.entities.map((entity_id: string) => ({ entity_id, label: entity_id, entity_type: 'scenario-entity', zone_id: zoneId, attributes: {}, x: null, y: null })),
      relationships: [{ relationship_id: 'definition-relationship-1', source_entity_id: scenario.entities[0], target_entity_id: scenario.entities[1], relationship_type: scenario.relationships[0], protocol: null }],
      baseline: Object.entries(scenario.enterprise_state).map(([state_key, value]) => ({ state_key, entity_id: scenario.entities[0], value, unit: null })),
      timeline: scenario.timeline.map((item: { stage: string; offset_seconds: number; state_changes: Record<string, string> }, index: number) => ({
        transition_id: `${item.stage.toLowerCase()}-${index + 1}`, stage: item.stage, offset_seconds: item.offset_seconds, title: item.stage,
        state_changes: Object.entries(item.state_changes).map(([state_key, value]) => ({ state_key, entity_id: scenario.entities[0], value, unit: null })),
        source_ids: [],
      })),
      parameters: [], correlation_mappings: [], investigations: [], contract_fingerprints: {}, layout_hints: {},
      cloned_from_scenario_id: id, definition_only: true, source_definition_id: id,
      definition_contract_ids: scenario.source_contracts, definition_contract_fingerprint: 'fixture',
      execution_blockers: scenario.research_gaps, created_at: null, updated_at: null,
    };
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(draft) });
  });
  await page.route('**/api/cisco100', (route) =>
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(catalog) }));
  await page.route('**/api/studio', (route) => route.fulfill({ json: {
    creation_paths: [], import_notice: 'Test-only private draft.', sources: [], scenarios: [], private_packs: [],
  } }));
  await page.goto('/#/catalog/cisco-100');
  await expect(page.getByRole('heading', { name: 'Scenario breadth without fabricated support' })).toBeVisible();
});

test('captures and inspects the Cisco 100 engineering experience', async ({ page }) => {
  test.setTimeout(120_000);
  await capture(page, 1, 'dashboard');
  await capture(page, 2, 'five-domain-browser', '.c100-domain-strip');

  const domainCaptures: Array<[string, number, string]> = [
    ['Enterprise Networking', 3, 'enterprise-networking-list'],
    ['Service Provider & Carrier', 4, 'service-provider-list'],
    ['Data Center & AI Cloud', 5, 'data-center-list'],
    ['Security & SASE', 6, 'security-sase-list'],
    ['Sovereign Critical Infrastructure & Mixed Cross-Domain', 7, 'critical-cross-domain-list'],
  ];
  for (const [domain, number, filename] of domainCaptures) {
    await page.getByRole('button', { name: new RegExp(`${domain} 20`) }).click();
    await expect(page.locator('.c100-scenarios > button')).toHaveCount(20);
    await capture(page, number, filename, '.c100-scenarios');
    await page.getByRole('button', { name: new RegExp(`${domain} 20`) }).click();
  }

  await page.getByLabel('Product / technology').selectOption({ label: 'IOS XR' });
  await capture(page, 8, 'product-filter');
  await page.getByLabel('Product / technology').selectOption('');

  const telemetryFilter = page.locator('.c100-filter').filter({ hasText: /^Telemetry/ }).locator('select');
  await telemetryFilter.selectOption({ label: 'cisco-ios-xr-interface-syslog' });
  await capture(page, 9, 'telemetry-filter');
  await telemetryFilter.selectOption('');

  await page.locator('.c100-maturity-grid').getByRole('button', { name: /RESEARCH REQUIRED/ }).click();
  await capture(page, 10, 'maturity-filter');
  await page.locator('.c100-maturity-grid').getByRole('button', { name: /RESEARCH REQUIRED/ }).click();

  await page.getByRole('button', { name: 'matrix' }).click();
  await expect(page.getByTestId('cisco100-matrix')).toBeVisible();
  await capture(page, 11, 'coverage-matrix');

  await page.getByRole('button', { name: 'Readiness & Evidence Debt' }).click();
  await expect(page.getByTestId('cisco100-evidence-debt')).toBeVisible();
  await capture(page, 12, 'readiness-evidence-debt');

  await page.getByRole('button', { name: 'browser' }).click();
  await selectScenario(page, 'C100-SP-001');
  await page.locator('.c100-detail__header').screenshot({ path: image(13, 'golden-scenario') });

  await page.getByRole('button', { name: /Service Provider & Carrier 20/ }).click();
  await page.locator('.c100-maturity-grid').getByRole('button', { name: /RESEARCH REQUIRED/ }).click();
  await selectScenario(page, 'C100-SP-020');
  const researchBlocked = page.getByText('Research required — generation blocked')
    .locator('xpath=ancestor::div[contains(@class,"state-panel")][1]');
  await expect(researchBlocked).toBeVisible();
  await researchBlocked.screenshot({ path: image(14, 'research-required-scenario') });
  await page.locator('.c100-maturity-grid').getByRole('button', { name: /RESEARCH REQUIRED/ }).click();
  await page.getByRole('button', { name: /Service Provider & Carrier 20/ }).click();

  await selectScenario(page, 'C100-CRI-014');
  await page.getByRole('heading', { name: 'Scenario topology' })
    .locator('xpath=ancestor::section[1]')
    .screenshot({ path: image(15, 'multi-product-topology') });

  await selectScenario(page, 'C100-SP-001');
  await page.getByRole('heading', { name: 'Telemetry and contracts' })
    .locator('xpath=ancestor::section[1]')
    .screenshot({ path: image(16, 'multi-channel-runtime') });
  await page.getByRole('heading', { name: 'Evidence Inspector' })
    .locator('xpath=ancestor::section[1]')
    .screenshot({ path: image(17, 'evidence-inspector') });
  await page.getByRole('heading', { name: 'Investigation Pack' })
    .locator('xpath=ancestor::section[1]')
    .screenshot({ path: image(18, 'splunk-investigation') });
  await page.getByRole('heading', { name: 'Troubleshooting guidance' })
    .locator('xpath=ancestor::section[1]')
    .screenshot({ path: image(19, 'troubleshooting-guidance') });
  await page.getByRole('heading', { name: 'Take This to Production' })
    .locator('xpath=ancestor::section[1]')
    .screenshot({ path: image(20, 'take-this-to-production') });

  await selectScenario(page, 'C100-ENT-001');
  await page.getByRole('button', { name: 'Clone definition in Scenario Studio' }).click();
  await expect(page).toHaveURL(/#\/build\/studio/);
  await expect(page.getByTestId('studio-environment-builder')).toBeVisible();
  await capture(page, 21, 'scenario-studio-clone');
});

test('captures representative mixed, security, carrier, data-center, and cross-domain definitions', async ({ page }) => {
  await selectScenario(page, 'C100-CRI-014');
  await expect(page.getByTestId('cisco100-scenario-detail').getByText(/Palo Alto Networks/).first()).toBeVisible();
  await page.getByRole('heading', { name: 'Architecture' })
    .locator('xpath=ancestor::section[1]')
    .screenshot({ path: image(22, 'mixed-vendor-scenario') });

  await selectScenario(page, 'C100-SEC-001');
  await page.locator('.c100-detail__header').screenshot({ path: image(23, 'security-scenario') });

  await selectScenario(page, 'C100-SP-001');
  await page.locator('.c100-detail__header').screenshot({ path: image(24, 'service-provider-scenario') });

  await selectScenario(page, 'C100-DC-001');
  await page.locator('.c100-detail__header').screenshot({ path: image(25, 'data-center-scenario') });

  await selectScenario(page, 'C100-CRI-001');
  await page.locator('.c100-detail__header').screenshot({ path: image(26, 'cross-domain-scenario') });

  await expect(page.getByText(
    'NetSpout is an independent project and is not Cisco certified, Cisco approved, Splunk certified, or endorsed by either vendor.',
  )).toBeVisible();
  await expect(page.getByText(/official Cisco simulator/i)).toHaveCount(0);
  await expect(page.getByText('Definitions are not support claims')).toBeVisible();
});
