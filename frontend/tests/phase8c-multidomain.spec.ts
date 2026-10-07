import { expect, test } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';

const repoRoot = path.resolve(process.cwd(), '..');
const base = JSON.parse(
  fs.readFileSync(path.join(repoRoot, 'catalog', 'cisco_100_scenarios.json'), 'utf8'),
);
const overlay = JSON.parse(
  fs.readFileSync(path.join(repoRoot, 'catalog', 'phase8c_scenario_promotions.json'), 'utf8'),
);
const promotions = new Map(
  overlay.promotions.map((item: { scenario_id: string }) => [item.scenario_id, item]),
);
const scenarios = base.scenarios.map((scenario: { scenario_id: string }) => ({
  ...scenario,
  ...(promotions.get(scenario.scenario_id) ?? {}),
}));
const countBy = (values: string[]) =>
  values.reduce<Record<string, number>>((result, value) => {
    result[value] = (result[value] ?? 0) + 1;
    return result;
  }, {});
const maturityNames = [
  'CANDIDATE', 'RESEARCHED', 'CONTRACTED', 'FORMAT_VALIDATED',
  'RUNTIME_VALIDATED', 'SPLUNK_VALIDATED', 'GOLDEN',
  'RESEARCH_REQUIRED', 'UNSUPPORTED', 'BLOCKED',
];
const maturityObserved = countBy(
  scenarios.map((item: { maturity: string }) => item.maturity),
);
const catalog = {
  ...base,
  catalog_version: overlay.catalog_version,
  scenarios,
  shared_assets: [...base.shared_assets, ...overlay.shared_assets],
  summary: {
    scenario_definitions: scenarios.length,
    domains: countBy(scenarios.map((item: { domain: string }) => item.domain)),
    maturity: Object.fromEntries(
      maturityNames.map((item) => [item, maturityObserved[item] ?? 0]),
    ),
    products_represented: new Set(
      scenarios.flatMap((item: { technologies: string[] }) => item.technologies),
    ).size,
    source_contracts: new Set(
      scenarios.flatMap((item: { source_contracts: string[] }) => item.source_contracts),
    ).size,
    native_protocols: new Set(
      scenarios.flatMap((item: { native_transports: string[] }) => item.native_transports),
    ).size,
    verified_splunk_integrations: 0,
  },
  evidence_debt: {
    missing_native_contract: scenarios.filter(
      (item: { source_contracts: string[] }) => !item.source_contracts.length,
    ).length,
    missing_splunk_mapping: scenarios.filter(
      (item: { splunk_integrations: string[] }) => !item.splunk_integrations.length,
    ).length,
    runtime_blocked: scenarios.filter(
      (item: { runtime_validation: string[] }) => !item.runtime_validation.length,
    ).length,
    cim_not_established: scenarios.filter(
      (item: { cim_relationships: Record<string, string> }) =>
        !Object.keys(item.cim_relationships).length
        || Object.values(item.cim_relationships).includes('NOT_ESTABLISHED'),
    ).length,
    provenance_blocked: 0,
    licensing_blocked: 0,
  },
  filter_result_count: scenarios.length,
  query_ms: 0.1,
};

test('shows truthful readiness for all five domain references', async ({ page }) => {
  await page.route('**/api/cisco100', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(catalog),
    }));
  await page.route('**/api/generation/capabilities', () => {});
  await page.goto('/#/catalog/cisco-100');

  const readiness = page.getByTestId('cisco100-reference-readiness');
  await expect(readiness).toBeVisible();
  await expect(readiness.getByRole('button')).toHaveCount(5);
  await expect(readiness).toContainText('C100-ENT-001');
  await expect(readiness).toContainText('C100-SP-001');
  await expect(readiness).toContainText('C100-DC-001');
  await expect(readiness).toContainText('C100-SEC-001');
  await expect(readiness).toContainText('C100-CRI-002');

  await readiness.getByRole('button', { name: /C100-SEC-001/ }).click();
  await expect(page.getByTestId('cisco100-scenario-detail')).toContainText(
    'EVID-P8C-CISCO-ASA-302013-302014',
  );
  await expect(page.getByText(/302013 indicates connection creation/i)).toBeVisible();
  await page.getByRole('button', { name: 'Open Guided Scenario' }).click();
  await expect(page).toHaveURL(/#\/generate\/scenarios$/);
  await expect.poll(() => page.evaluate(
    () => window.sessionStorage.getItem('netspout-guided-scenario-id'),
  )).toBe('C100-SEC-001');
});

test('hands a runnable Golden reference to Scenario Studio', async ({ page }) => {
  await page.route('**/api/cisco100', (route) =>
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(catalog) }));
  await page.route('**/api/cisco100/scenarios/C100-DC-001/studio-draft', (route) =>
    route.fulfill({ json: {
      pack_id: 'private-c100-dc-001-clone',
      scenario_id: 'studio-c100-dc-001-clone',
      title: 'Nexus Fabric Uplink Degradation — Private Clone',
      description: 'A runnable private clone.',
      story: 'A fictional Nexus uplink degrades and recovers.',
      creation_path: 'CLONE_SCENARIO',
      maturity: 'DRAFT',
      privacy_status: 'SANITIZED',
      provenance: 'NETSPOUT-GENERATED',
      redistribution: 'PRIVATE',
      source_ids: ['cisco-nx-os-interface-syslog'],
      custom_sources: [],
      zones: [{ zone_id: 'lab', label: 'Private Lab' }],
      entities: [{
        entity_id: 'nexus-9000-leaf01',
        label: 'Nexus 9000 Leaf 01',
        entity_type: 'switch',
        zone_id: 'lab',
        attributes: {},
        x: null,
        y: null,
      }],
      relationships: [],
      baseline: [],
      timeline: [{
        transition_id: 'baseline',
        stage: 'BASELINE',
        offset_seconds: 0,
        title: 'Baseline',
        state_changes: [],
        source_ids: ['cisco-nx-os-interface-syslog'],
      }],
      parameters: [],
      correlation_mappings: [],
      investigations: [],
      contract_fingerprints: { 'cisco-nx-os-interface-syslog': 'fixture-fingerprint' },
      layout_hints: {},
      cloned_from_scenario_id: 'C100-DC-001',
      definition_only: false,
      source_definition_id: null,
      definition_contract_ids: [],
      definition_contract_fingerprint: null,
      execution_blockers: [],
      created_at: null,
      updated_at: null,
    } }));
  await page.route('**/api/studio', (route) =>
    route.fulfill({ json: {
      creation_paths: [],
      import_notice: 'Private test workspace.',
      sources: [],
      scenarios: [],
      private_packs: [],
    } }));

  await page.goto('/#/catalog/cisco-100');
  const readiness = page.getByTestId('cisco100-reference-readiness');
  await readiness.getByRole('button', { name: /C100-DC-001/ }).click();
  await page.getByRole('button', {
    name: 'Clone runnable reference in Scenario Studio',
  }).click();

  await expect(page).toHaveURL(/#\/build\/studio$/);
  await expect(page.getByTestId('studio-environment-builder')).toBeVisible();
  await expect(page.getByText('Catalog definition-only draft')).toHaveCount(0);
  if (process.env.NETSPOUT_SCREENSHOT_ROOT) {
    fs.mkdirSync(process.env.NETSPOUT_SCREENSHOT_ROOT, { recursive: true });
    await page.screenshot({
      path: path.join(process.env.NETSPOUT_SCREENSHOT_ROOT, '29-scenario-studio-runnable-clone.png'),
      fullPage: true,
    });
  }
});

test('captures the Phase 8C visual review inventory', async ({ page }) => {
  test.skip(!process.env.NETSPOUT_SCREENSHOT_ROOT, 'Current-run screenshot capture not requested.');
  const output = process.env.NETSPOUT_SCREENSHOT_ROOT as string;
  fs.mkdirSync(output, { recursive: true });
  await page.route('**/api/cisco100', (route) =>
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(catalog) }));
  await page.route('**/api/generation/capabilities', () => {});
  await page.setViewportSize({ width: 1600, height: 1050 });
  await page.goto('/#/catalog/cisco-100');

  const capturePage = async (name: string) => page.screenshot({
    path: path.join(output, name),
    fullPage: true,
  });
  const capturePanel = async (title: string, name: string) => {
    const panel = page.locator('.technical-panel').filter({ hasText: title }).first();
    await expect(panel).toBeVisible();
    await panel.screenshot({ path: path.join(output, name) });
  };
  const selectReference = async (scenarioId: string) => {
    await page.getByTestId('cisco100-reference-readiness')
      .getByRole('button', { name: new RegExp(scenarioId) }).click();
    await expect(page.getByTestId('cisco100-scenario-detail')).toContainText(scenarioId);
  };

  await capturePage('01-domain-depth-overview.png');
  await page.getByTestId('cisco100-reference-readiness').screenshot({
    path: path.join(output, '02-five-domain-reference-readiness.png'),
  });

  await selectReference('C100-ENT-001');
  await capturePage('03-enterprise-reference.png');
  await capturePanel('Scenario topology', '04-enterprise-topology.png');

  await selectReference('C100-SP-001');
  await capturePage('05-service-provider-reference.png');
  await capturePanel('Scenario topology', '06-service-provider-topology.png');
  await capturePanel('Telemetry and contracts', '07-service-provider-native-splunk-contracts.png');
  await capturePanel('Evidence Inspector', '08-service-provider-evidence.png');
  await capturePanel('Investigation Pack', '09-service-provider-investigation.png');
  await capturePanel('Troubleshooting guidance', '10-service-provider-troubleshooting.png');
  await capturePanel('Take This to Production', '11-service-provider-production.png');

  await selectReference('C100-DC-001');
  await capturePage('12-data-center-reference.png');
  await capturePanel('Scenario topology', '13-data-center-topology.png');
  await capturePanel('Telemetry and contracts', '14-data-center-contracts.png');
  await capturePanel('Evidence Inspector', '15-data-center-evidence-runtime.png');
  await capturePanel('Investigation Pack', '16-data-center-investigation.png');

  await selectReference('C100-SEC-001');
  await capturePage('17-security-reference.png');
  await capturePanel('Scenario topology', '18-security-topology.png');
  await capturePanel('Telemetry and contracts', '19-security-native-splunk-contracts.png');
  await capturePanel('Evidence Inspector', '20-security-evidence-runtime.png');
  await capturePanel('Investigation Pack', '21-security-investigation.png');

  await selectReference('C100-CRI-002');
  await capturePage('22-cross-domain-reference.png');
  await capturePanel('Scenario topology', '23-cross-domain-causal-topology.png');
  await capturePanel('Shared enterprise state and simulation clock', '24-cross-domain-propagation.png');
  await capturePanel('Telemetry and contracts', '25-cross-domain-contracts-cim.png');
  await capturePanel('Investigation Pack', '26-cross-domain-correlation.png');
  await capturePanel('Take This to Production', '27-cross-domain-production.png');

  const unresolved = scenarios.find(
    (item: { maturity: string }) => item.maturity === 'RESEARCH_REQUIRED',
  );
  expect(unresolved).toBeTruthy();
  await page.getByRole('button', { name: new RegExp(unresolved.scenario_id) }).last().click();
  const blocked = page.getByText('Research required — generation blocked').locator('..');
  await expect(blocked).toBeVisible();
  await blocked.screenshot({ path: path.join(output, '28-research-required-fail-closed.png') });

  await page.getByRole('button', { name: 'matrix', exact: true }).click();
  await page.getByTestId('cisco100-matrix').screenshot({
    path: path.join(output, '30-cisco-100-maturity-matrix.png'),
  });
  await page.getByRole('button', { name: 'Readiness & Evidence Debt', exact: true }).click();
  await capturePage('31-final-domain-depth-and-evidence-debt.png');
});
