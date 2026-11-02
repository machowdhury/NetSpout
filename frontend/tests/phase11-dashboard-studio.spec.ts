import { expect, test } from '@playwright/test';
import { artifactPath } from './artifact-paths';

const eligible = [
  ['scenario-c100-ent-001', 'C100-ENT-001', 'Campus Link Degradation', 'networking', null],
  ['scenario-c100-sp-001', 'C100-SP-001', 'Service Provider Correlation', 'networking', null],
  ['scenario-c100-dc-001', 'C100-DC-001', 'Data Center Fabric Degradation', 'networking', null],
  ['scenario-c100-sec-001', 'C100-SEC-001', 'Security Policy Incident', 'security', null],
  ['scenario-c100-cri-002', 'C100-CRI-002', 'Cross-Domain Critical Incident', 'networking', null],
  ['scenario-sec-p9-a-traffic-flood', 'SEC-P9-A-TRAFFIC-FLOOD', 'Traffic Flood', 'security', null],
  ['scenario-sec-p9-b-dns-anomaly', 'SEC-P9-B-DNS-ANOMALY', 'DNS Anomaly', 'security', null],
  ['scenario-sec-p9-c-beaconing', 'SEC-P9-C-BEACONING', 'Beaconing', 'security', null],
  ['scenario-sec-p9-d-internal-recon', 'SEC-P9-D-INTERNAL-RECON', 'Internal Reconnaissance', 'security', null],
  ['scenario-sec-p9-e-dns-tunnel', 'SEC-P9-E-DNS-TUNNEL', 'DNS Tunneling Indicators', 'security', null],
  ['scenario-sec-p9-f-cross-source', 'SEC-P9-F-CROSS-SOURCE', 'Cross-Source Incident', 'security', null],
  ['industry-financial-services', 'financial-services', 'Financial Services', 'industry', 'financial-services'],
  ['industry-healthcare', 'healthcare', 'Healthcare', 'industry', 'healthcare'],
  ['industry-manufacturing', 'manufacturing', 'Manufacturing', 'industry', 'manufacturing'],
] as const;

const dashboards = [
  ...eligible.map(([dashboard_id, scenario_id, title, domain, industry_id], index) => ({
    dashboard_id,
    scenario_id,
    runtime_scenario_id: scenario_id,
    title,
    domain,
    category: domain,
    industry_id,
    scenario_maturity: 'GOLDEN',
    dashboard_maturity: index === 0 ? 'DATA_VALIDATED' : 'NOT_STARTED',
    state: 'ELIGIBLE',
    reasons: ['verified mature scenario metadata is complete'],
    source_ids: index % 2 ? ['ietf-syslog-rfc5424'] : ['openconfig-gnmi-interfaces'],
    investigation_recipe_ids: ['investigate-run'],
    recipe_ids: ['dashboard-operational-summary', 'dashboard-evidence-chain'],
  })),
  {
    dashboard_id: 'scenario-rfc5424-link-state-lifecycle',
    scenario_id: 'rfc5424-link-state-lifecycle',
    runtime_scenario_id: 'rfc5424-link-state-lifecycle',
    title: 'Link State Lifecycle',
    domain: 'networking',
    category: 'networking',
    industry_id: null,
    scenario_maturity: 'BETA',
    dashboard_maturity: 'NOT_STARTED',
    state: 'RESEARCH_REQUIRED',
    reasons: ['scenario maturity BETA is below the executable threshold'],
    source_ids: ['ietf-syslog-rfc5424'],
    investigation_recipe_ids: [],
    recipe_ids: [],
  },
];

const panel = (perspective: string, suffix: string, executable = true) => ({
  panel_id: `panel-${suffix}`,
  recipe_id: `dashboard-${suffix}`,
  title: suffix.replaceAll('-', ' '),
  purpose: `Verified ${suffix} context for the selected scenario and run.`,
  perspective,
  executable,
  query: executable
    ? 'search index="idx_network_ops" sourcetype="netspout:gnmi:event" netspout_run_id="run-phase11" earliest=-15m latest=now | stats count as observations by sourcetype'
    : null,
  portability: 'NETSPOUT_SPECIFIC',
  required_fields: ['netspout_run_id', 'sourcetype'],
  optional_fields: ['device_id'],
  expected_shape: { sourcetype: 'string', observations: 'number' },
  visualization_id: executable ? 'splunk-table' : 'netspout-network-graph',
  requested_visualization_id: executable ? 'splunk-table' : 'network-diagram-viz',
  dependency_state: executable ? 'VERIFIED' : 'FALLBACK:NOT_VERIFIED',
  drilldowns: [{ token: 'source', field: 'sourcetype', semantics: 'Filter to supporting source telemetry.' }],
  evidence_requirements: ['SPLUNK_OBSERVED'],
});

const packFor = (dashboardId: string, runId: string | null) => {
  const entry = dashboards.find((item) => item.dashboard_id === dashboardId)!;
  return {
    schema_version: '1.0.0',
    dashboard_id: dashboardId,
    dashboard_version: '1.0.0',
    title: `${entry.title} Dashboard`,
    description: 'Scenario-aware dashboard generated from verified contracts. Unsupported fields remain unclaimed.',
    scenario_id: entry.scenario_id,
    runtime_scenario_id: entry.runtime_scenario_id,
    scenario_version: '1.0.0',
    run_id: runId,
    domain: entry.domain,
    category: entry.category,
    industry_id: entry.industry_id,
    source_contracts: [{ source_id: entry.source_ids[0], native_contract_id: 'native-contract', verification_state: 'VERIFIED' }],
    splunk_contracts: [{ source_id: entry.source_ids[0], splunk_contract_id: 'splunk-contract', cim_mappings: [] }],
    investigation_recipe_ids: ['investigate-run'],
    detection_pack_ids: [],
    entity_graph: {
      shared_with_scenario: true,
      nodes: [
        { node_id: 'edge-1', label: 'Edge Router', role: 'router' },
        { node_id: 'core-1', label: 'Core Service', role: 'service' },
        { node_id: 'splunk-1', label: 'Splunk', role: 'splunk' },
      ],
      relationships: [
        { relationship_id: 'path-1', source_node_id: 'edge-1', target_node_id: 'core-1', relationship_type: 'routes_to' },
        { relationship_id: 'path-2', source_node_id: 'core-1', target_node_id: 'splunk-1', relationship_type: 'observed_by' },
      ],
    },
    topology_ref: `scenario:${entry.runtime_scenario_id}`,
    telemetry_manifest: [{ source_id: entry.source_ids[0], sourcetypes: ['netspout:gnmi:event'] }],
    observed_fields: runId ? ['netspout_run_id', 'sourcetype'] : [],
    panels: [
      panel('NOC', 'operational-summary'),
      panel('NOC', 'topology-health', false),
      panel('ENGINEER', 'source-detail'),
      panel('ENGINEER', 'investigation-workbench'),
      panel('EVIDENCE', 'evidence-chain'),
      panel('EVIDENCE', 'recovery-validation'),
    ],
    perspectives: {},
    maturity: runId ? 'DATA_VALIDATED' : 'GENERATED',
    validation_evidence: runId ? [{ evidence_id: 'dashboard-evidence-1' }] : [],
    cim_status: 'NOT_ESTABLISHED',
    export_compatibility: 'SPLUNK_DASHBOARD_STUDIO_JSON',
    limitations: ['Optional topology app is not verified; native fallback selected.'],
  };
};

test.beforeEach(async ({ page }) => {
  await page.route('**/api/dashboards**', async (route) => {
    const url = new URL(route.request().url());
    const parts = url.pathname.split('/').filter(Boolean);
    if (parts.length === 2) {
      await route.fulfill({ json: {
        schema_version: '1.0.0',
        registry_version: '1.0.0',
        dashboards,
        eligible_count: 14,
        recipes: Array.from({ length: 19 }, (_, index) => ({ recipe_id: `recipe-${index}` })),
        visualizations: Array.from({ length: 11 }, (_, index) => ({ visualization_id: `visual-${index}` })),
      } });
      return;
    }
    const dashboardId = decodeURIComponent(parts[2]);
    if (parts[3] === 'export') {
      await route.fulfill({ json: {
        format: 'SPLUNK_DASHBOARD_STUDIO_JSON',
        definition: { title: dashboardId, dataSources: {}, visualizations: {}, layout: {} },
        validation: { valid: true, errors: [] },
        deployment: { deployment_status: 'PREVIEW_ONLY', target: 'configured lab only', overwrite_allowed: false, required_permissions: [], search_workload: {} },
      } });
      return;
    }
    await route.fulfill({ json: packFor(dashboardId, url.searchParams.get('run_id')) });
  });
  await page.setViewportSize({ width: 1600, height: 1050 });
});

test('filters the gallery and explains research-required scenarios', async ({ page }) => {
  await page.goto('/#/observe/dashboards');
  await expect(page.getByRole('heading', { name: 'Dashboard Gallery' })).toBeVisible();
  await expect(page.getByText('14', { exact: true })).toBeVisible();
  await expect(page.locator('.dashboard-card')).toHaveCount(15);
  await page.getByLabel('Search dashboards').fill('DNS');
  await expect(page.locator('.dashboard-card')).toHaveCount(2);
  await page.getByLabel('Search dashboards').fill('Link State');
  await page.getByRole('button', { name: 'View missing evidence' }).click();
  await expect(page.getByTestId('dashboard-research-required')).toContainText('No fallback event');
  await page.screenshot({ path: artifactPath('phase11-dashboard', '01-gallery-research-state.png'), fullPage: true });
});

test('runs NOC, Engineer, Evidence, drilldown, inspector, export, and wallboard journeys', async ({ page }) => {
  await page.goto('/#/observe/dashboards');
  await page.getByRole('button', { name: 'Open dashboard' }).first().click();
  await expect(page.getByTestId('dashboard-topology')).toBeVisible();
  await expect(page.getByText(/Preview mode/)).toBeVisible();
  await page.getByLabel('Run context').fill('run-phase11');
  await expect(page).toHaveURL(/dashboard=scenario-c100-ent-001/);
  await expect(page).toHaveURL(/run=run-phase11/);
  await page.screenshot({ path: artifactPath('phase11-dashboard', '02-noc-perspective.png'), fullPage: true });

  await page.getByRole('tab', { name: 'ENGINEER' }).click();
  await expect(page.getByText('source detail', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: /source → sourcetype/ }).first().click();
  await expect(page.getByText('source: sourcetype')).toBeVisible();
  await page.getByRole('button', { name: 'Inspect' }).first().click();
  await expect(page.getByLabel('Advanced Inspector')).toBeVisible();
  await page.getByRole('button', { name: 'SPL', exact: true }).click();
  await expect(page.getByText(/earliest=-15m/)).toBeVisible();
  await page.getByRole('button', { name: 'CIM', exact: true }).click();
  await expect(page.getByText(/NOT ESTABLISHED/)).toBeVisible();
  await page.screenshot({ path: artifactPath('phase11-dashboard', '03-advanced-inspector.png'), fullPage: true });
  await page.getByLabel('Close inspector').click();

  await page.getByRole('tab', { name: 'EVIDENCE' }).click();
  await expect(page.getByText('evidence chain', { exact: true })).toBeVisible();
  const download = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Export / Deploy' }).click();
  await expect(page.getByRole('dialog', { name: 'Dashboard export and deployment preview' })).toBeVisible();
  await page.getByRole('button', { name: 'Download JSON' }).click();
  expect((await download).suggestedFilename()).toContain('dashboard-studio.json');
  await page.getByLabel('Close export preview').click();

  await page.getByRole('button', { name: 'NOC wallboard' }).click();
  await expect(page.getByRole('button', { name: 'Exit wallboard' })).toBeVisible();
  await page.screenshot({ path: artifactPath('phase11-dashboard', '04-noc-wallboard.png'), fullPage: true });
});

test('generates distinct dashboard context for all fourteen eligible references', async ({ page }) => {
  for (const [dashboardId, scenarioId, title] of eligible) {
    await page.goto(`/?dashboard=${encodeURIComponent(dashboardId)}&run=matrix-run#/observe/dashboards`);
    await expect(page.getByRole('heading', { name: `${title} Dashboard` })).toBeVisible();
    await expect(page.getByText(scenarioId, { exact: false }).first()).toBeVisible();
    await expect(page.getByTestId('dashboard-topology')).toBeVisible();
  }
});
