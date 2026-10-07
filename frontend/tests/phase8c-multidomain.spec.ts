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
});
