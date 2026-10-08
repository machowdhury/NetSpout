import { expect, test } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';
import { artifactPath } from './artifact-paths';

const raw = JSON.parse(
  fs.readFileSync(path.resolve(process.cwd(), '../catalog/industry_packs.json'), 'utf8'),
);

const scenarioByIndustry: Record<string, { scenario_id: string; title: string; source_ids: string[] }> = {
  'financial-services': {
    scenario_id: 'C100-CRI-002',
    title: 'Telecom Operations Network Degradation — Correlated Reference',
    source_ids: ['cisco-ios-xe-interface-syslog', 'cisco-ios-xr-interface-syslog'],
  },
  healthcare: {
    scenario_id: 'C100-ENT-001',
    title: 'Campus Access Link Degradation — IOS XE Reference',
    source_ids: ['cisco-ios-xe-interface-syslog'],
  },
  manufacturing: {
    scenario_id: 'C100-DC-001',
    title: 'Nexus Fabric Uplink Degradation — NX-OS Reference',
    source_ids: ['cisco-nx-os-interface-syslog'],
  },
};

const industries = raw.industries.map((item: any) => ({
  ...item,
  scenario_references: [{
    ...scenarioByIndustry[item.industry_id],
    investigation_recipe_ids: [`investigate-${item.industry_id}`],
    scenario_maturity: 'GOLDEN',
  }],
}));

const catalog = {
  schema_version: raw.schema_version,
  registry_version: raw.registry_version,
  industries,
  future_categories: ['Retail', 'Energy', 'Transportation'],
};

const evidence = (observed: boolean) => [
  { stage: 'GENERATED', state: 'PROVEN', count: 8, detail: 'Generated.' },
  { stage: 'RECEIVER_OBSERVED', state: 'PROVEN', count: 8, detail: 'Receiver observed.' },
  { stage: 'SPLUNK_OBSERVED', state: observed ? 'PROVEN' : 'PENDING', count: observed ? 8 : 0, detail: observed ? 'Fresh authenticated search proved observation.' : 'Awaiting search.' },
];

const run = (observed: boolean) => ({
  run_id: '10101010-2222-4333-8444-555555555555',
  mode: 'SCENARIO',
  selection_id: 'C100-CRI-002',
  scenario_id: 'C100-CRI-002',
  source_ids: scenarioByIndustry['financial-services'].source_ids,
  generator_ids: ['generator-one', 'generator-two'],
  transport_id: 'transport-local-hec',
  destination_id: 'destination-local-docker-splunk',
  started_at: '2026-10-08T01:00:00Z',
  completed_at: '2026-10-08T01:00:01Z',
  current_phase: 'RECOVERY',
  status: observed ? 'OBSERVED' : 'COMPLETED',
  events: [],
  evidence: evidence(observed),
  channel_results: [],
  validation: [],
  integration_readiness: [],
  investigations: [{
    recipe_id: 'investigate-financial-services',
    title: 'Trace the modeled dependency',
    question: 'Which technical dependency changed?',
    hint: 'Order interface transitions.',
    spl: 'search index=idx_network_ops netspout_run_id=...',
    portability: 'NETSPOUT_SPECIFIC',
    source_ids: scenarioByIndustry['financial-services'].source_ids,
    required_fields: ['netspout_run_id'],
    expected_finding: 'Both network channels reached recovery.',
    explanation: 'Business impact remains modeled.',
    evidence_ids: [],
  }],
  limitations: ['Business impact is modeled.'],
});

test.beforeEach(async ({ page }) => {
  await page.route('**/api/industries', (route) => route.fulfill({ json: catalog }));
  await page.route('**/api/industries/compose', async (route) => {
    const request = route.request().postDataJSON();
    const industry = industries.find((item: any) => item.industry_id === request.industry_id);
    const environment = industry.environments.find((item: any) => item.environment_id === request.environment_id);
    const scenario = scenarioByIndustry[industry.industry_id];
    await route.fulfill({ json: {
      industry_id: industry.industry_id,
      environment_id: environment.environment_id,
      scenario_id: scenario.scenario_id,
      seed: request.seed,
      source_ids: scenario.source_ids,
      investigation_recipe_ids: [`investigate-${industry.industry_id}`],
      technical_evidence_classification: 'NOT_ESTABLISHED',
      business_impact_classification: 'MODELED',
      generation_request: {
        mode: 'SCENARIO',
        selection_id: scenario.scenario_id,
        transport_id: 'transport-local-hec',
        destination_id: 'destination-local-docker-splunk',
        count: 1,
        rate_eps: 1,
        scenario_parameters: { seed: request.seed },
      },
      impact_preview: {
        propagated_entity_ids: environment.entity_ids,
        dependency_ids: environment.dependency_ids,
        technical_evidence: { status: 'NOT_ESTABLISHED', detail: 'Awaiting run.' },
        business_impacts: industry.business_impacts,
      },
    } });
  });
  await page.route('**/api/generation/preflight', (route) => route.fulfill({ json: {
    state: 'READY_WITH_WARNINGS',
    checks: [{ check_id: 'contracts', label: 'Contracts', state: 'PASS', detail: 'Verified.' }],
    source_ids: scenarioByIndustry['financial-services'].source_ids,
    generator_ids: ['generator-one', 'generator-two'],
    transport_id: 'transport-local-hec',
    destination_id: 'destination-local-docker-splunk',
  } }));
  await page.route('**/api/generation/runs', (route) => route.fulfill({ json: run(false) }));
  await page.route('**/api/generation/runs/*/observe', (route) => route.fulfill({ json: run(true) }));
  await page.route('**/api/generation/runs/*/investigate/*', (route) => route.fulfill({ json: {
    run_id: run(true).run_id,
    recipe_id: 'investigate-financial-services',
    portability: 'NETSPOUT_SPECIFIC',
    query: 'search index=idx_network_ops netspout_run_id=...',
    status: 'SUCCEEDED',
    result_count: 8,
    detail: 'Splunk returned correlated results.',
  } }));
  await page.route('**/api/industries/*/studio-draft', (route) => route.fulfill({ json: {
    pack_id: 'private-industry-clone',
    scenario_id: 'studio-industry-clone',
    title: 'Financial Services Private Clone',
    description: 'Industry clone',
    story: 'Clone',
    creation_path: 'CLONE_SCENARIO',
    maturity: 'DRAFT',
    privacy_status: 'SANITIZED',
    provenance: 'NETSPOUT_GENERATED',
    redistribution: 'PRIVATE',
    source_ids: scenarioByIndustry['financial-services'].source_ids,
    custom_sources: [],
    zones: [],
    entities: [],
    relationships: [],
    baseline: [],
    timeline: [],
    parameters: [],
    correlation_mappings: [],
    investigations: [],
    contract_fingerprints: {},
    layout_hints: {},
    cloned_from_scenario_id: 'C100-CRI-002',
    definition_only: false,
    industry_id: 'financial-services',
    industry_environment_id: 'financial-retail-branch',
    business_impact_assumptions: ['No alternate path is instrumented.'],
    created_at: null,
    updated_at: null,
  } }));
  await page.setViewportSize({ width: 1600, height: 1050 });
});

test('runs the Industry Studio journey and preserves evidence separation', async ({ page }) => {
  await page.goto('/#/build/industry-studio');
  await expect(page.getByRole('heading', { name: 'Connect technical evidence to modeled business impact' })).toBeVisible();
  await expect(page.getByLabel('Industry choices').getByRole('button')).toHaveCount(3);
  await page.screenshot({ path: artifactPath('phase10-industry', '01-financial-industry-selection.png'), fullPage: true });

  await page.getByRole('button', { name: 'Business', exact: true }).click();
  await expect(page.getByText('Business Dependency View')).toBeVisible();
  await expect(page.getByText('MODELED', { exact: true })).toBeVisible();
  await page.screenshot({ path: artifactPath('phase10-industry', '02-business-dependency-view.png'), fullPage: true });

  await page.getByRole('button', { name: 'Run preflight' }).click();
  await expect(page.getByText('READY_WITH_WARNINGS')).toBeVisible();
  await page.getByRole('button', { name: 'Run incident' }).click();
  await expect(page.getByText(/Run 10101010/)).toBeVisible();
  await page.getByRole('button', { name: 'Observe in Splunk' }).click();
  await expect(page.locator('.generation-guided-grid article').first().getByText('OBSERVED', { exact: true })).toBeVisible();
  await page.screenshot({ path: artifactPath('phase10-industry', '03-observed-versus-modeled.png'), fullPage: true });

  await page.getByRole('button', { name: 'Investigate', exact: true }).click();
  await expect(page.getByText(/SUCCEEDED/)).toBeVisible();
  await expect(page.getByText(/8 result/)).toBeVisible();
  await page.screenshot({ path: artifactPath('phase10-industry', '04-investigation-validation.png'), fullPage: true });

  await page.getByRole('button', { name: /Healthcare/ }).click();
  await expect(page.getByText(/No patient identity/)).toBeVisible();
  await page.getByRole('button', { name: /Manufacturing/ }).click();
  await expect(page.getByText(/No PLC/)).toBeVisible();
});

test('shows advanced contracts and hands a clone to Scenario Studio', async ({ page }) => {
  await page.goto('/#/build/industry-studio');
  await page.getByRole('button', { name: 'Advanced', exact: true }).click();
  const advancedContractView = page.getByText('Advanced contract view');
  await expect(advancedContractView).toBeVisible();
  await expect(page.getByText('cisco-ios-xe-interface-syslog', { exact: true })).toBeVisible();
  await advancedContractView.scrollIntoViewIfNeeded();
  await page.screenshot({ path: artifactPath('phase10-industry', '05-advanced-source-contracts.png'), fullPage: true });
  const cloneRequest = page.waitForRequest('**/api/industries/*/studio-draft');
  await page.getByRole('button', { name: 'Clone in Scenario Studio' }).click();
  const request = await cloneRequest;
  expect(request.postDataJSON().industry_id).toBe('financial-services');
  await expect(page).toHaveURL(/#\/build\/studio/);
});
