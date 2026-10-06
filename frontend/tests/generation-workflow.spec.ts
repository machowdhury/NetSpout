import { expect, test, type Page } from '@playwright/test';
import { mkdir } from 'node:fs/promises';
import path from 'node:path';

const source = {
  source_id: 'ietf-syslog-rfc5424',
  vendor: 'IETF',
  product: 'Syslog Protocol',
  product_family: 'Internet Standards',
  domains: ['netops', 'secops', 'itops'],
  telemetry_source: 'RFC 5424 syslog message',
  applicable_industries: [],
  verification_state: 'VERIFIED',
  provenance: ['STANDARD_DOCUMENTED', 'MODELED_PAYLOAD'],
  evidence_ids: ['EVID-IETF-RFC5424'],
  native_contract: {
    contract_id: 'native-ietf-syslog-rfc5424',
    verification_state: 'VERIFIED',
    format: 'RFC 5424 structured syslog message',
    schema: 'PRI VERSION TIMESTAMP HOSTNAME APP-NAME PROCID MSGID STRUCTURED-DATA MSG',
    transports: [{ protocol: 'TCP', default_port: 514, encoding: 'UTF-8' }],
    structural_fields: ['PRI', 'VERSION', 'TIMESTAMP'],
    evidence_ids: ['EVID-IETF-RFC5424'],
  },
  splunk_contract: {
    contract_id: 'splunk-ietf-syslog-rfc5424',
    verification_state: 'PARTIALLY_VERIFIED',
    input_mechanisms: ['NetSpout direct structured ingestion'],
    integration_ids: ['netspout-direct-structured-ingestion'],
    sourcetypes: [{ name: 'netspout:rfc5424', authority: 'NETSPOUT_DEFINED', evidence_ids: ['EVID-NETSPOUT'] }],
    cim_mappings: [],
    evidence_ids: ['EVID-NETSPOUT'],
  },
  netspout_contract: {
    contract_id: 'netspout-ietf-syslog-rfc5424',
    verification_state: 'PARTIALLY_VERIFIED',
    schema_classification: 'MODELED_PAYLOAD',
    generator: 'netspout_core.log_engine.SplunkLogEngine',
    validator: null,
    transports: ['HEC'],
    modeled_fields: ['interface state'],
    structural_fields: ['PRI', 'VERSION', 'TIMESTAMP'],
    scenario_ids: ['rfc5424-link-state-lifecycle'],
    generation_modes: ['MODE_A', 'MODE_B', 'MODE_C', 'MODE_D'],
    runtime_status: 'AVAILABLE',
    maturity: 'BETA',
    evidence_ids: ['EVID-NETSPOUT'],
  },
  spl_field_scope: {
    production_fields: ['_raw'],
    netspout_only_fields: ['netspout_run_id'],
    portable_spl_status: 'PARTIALLY_VERIFIED',
  },
  known_limitations: ['HEC is not the native syslog transport.'],
  generation: {
    runnable: true,
    state: 'READY',
    reason: 'Validated catalog source with an allow-listed generator.',
  },
};

const unsupportedSource = {
  ...source,
  source_id: 'supply-chain-platform-unselected',
  vendor: 'Not selected',
  product: 'Supply chain platform',
  telemetry_source: 'Platform-specific audit telemetry',
  verification_state: 'UNSUPPORTED',
  provenance: ['UNSUPPORTED_TELEMETRY'],
  generation: { runnable: false, state: 'UNSUPPORTED', reason: 'UNSUPPORTED TELEMETRY' },
};

const scenario = {
  scenario_id: 'rfc5424-link-state-lifecycle',
  title: 'Modeled Link-State Lifecycle',
  description: 'A standards-structured lab scenario showing an interface transition.',
  story: 'A fictional branch uplink deteriorates, goes down, and returns to service.',
  difficulty: 'BEGINNER',
  expected_duration_minutes: 1,
  learning_objectives: ['Distinguish sent and observed evidence.'],
  business_impact: 'Demonstrates interruption of a fictional branch application path.',
  prerequisites: ['Configured local Docker Splunk destination'],
  technology_ids: ['rfc5424', 'splunk-hec'],
  source_ids: ['ietf-syslog-rfc5424'],
  entities: ['Fictional branch user', 'Fictional edge router', 'Local Splunk'],
  zones: [
    { zone_id: 'branch-zone', label: 'Fictional Branch' },
    { zone_id: 'observability-zone', label: 'Observability' },
  ],
  nodes: [
    { node_id: 'branch-user', technology_id: 'generic-user', zone_id: 'branch-zone', role: 'user', source_ids: [] },
    { node_id: 'edge-router', technology_id: 'rfc5424', zone_id: 'branch-zone', role: 'router', source_ids: ['ietf-syslog-rfc5424'] },
    { node_id: 'splunk-local', technology_id: 'splunk-hec', zone_id: 'observability-zone', role: 'splunk', source_ids: [] },
  ],
  relationships: [
    { relationship_id: 'branch-to-router', source_node_id: 'branch-user', target_node_id: 'edge-router', relationship_type: 'application-path' },
    { relationship_id: 'router-to-splunk', source_node_id: 'edge-router', target_node_id: 'splunk-local', relationship_type: 'telemetry-delivery' },
  ],
  telemetry_paths: [{ path_id: 'path', source_id: 'ietf-syslog-rfc5424', producer_node_id: 'edge-router', observer_node_id: 'splunk-local' }],
  incident_path: ['edge-router'],
  runtime_state_keys: ['normal', 'affected', 'recovered'],
  timeline: ['BASELINE', 'PRECURSOR', 'INCIDENT', 'IMPACT', 'DETECTION', 'RECOVERY'].map((stage) => ({
    step_id: stage.toLowerCase(),
    stage,
    description: `${stage} stage`,
    state_changes: stage === 'RECOVERY' ? { 'edge-router': 'recovered' } : {},
    incident_ids: [],
  })),
  expected_evidence: ['Six ordered RFC 5424 events.'],
  investigation_recipe_ids: ['investigate-rfc5424-run'],
  integration_recommendation_ids: ['recommend-rfc5424-direct-ingestion'],
  production_replication_guidance: ['Replace lab metadata with production integration fields.'],
  composition_id: 'compose-rfc5424-link-state-local',
  verification_state: 'PARTIALLY_VERIFIED',
  maturity: 'BETA',
  source_count: 1,
  integration_count: 1,
  runnable: true,
};

const readiness = {
  recommendation_id: 'recommend-rfc5424-direct-ingestion',
  source_id: 'ietf-syslog-rfc5424',
  integration_id: 'netspout-direct-structured-ingestion',
  requirement: 'REQUIRED',
  evidence_ids: ['EVID-NETSPOUT'],
  notes: 'Required for the NetSpout-defined lab sourcetype.',
  name: 'NetSpout direct structured ingestion',
  publisher: 'NetSpout',
  support_state: 'LAB_ONLY',
  detected: true,
  evidence: [],
};

const recipe = {
  recipe_id: 'investigate-rfc5424-run',
  title: 'Trace the modeled link-state lifecycle',
  portability: 'NETSPOUT_SPECIFIC',
  spl: 'index=idx_network_ops sourcetype="netspout:rfc5424" netspout_run_id="$run_id$" | sort 0 _time',
  source_ids: ['ietf-syslog-rfc5424'],
  required_fields: ['netspout_run_id'],
  cim_requirements: [],
  netspout_only_fields: ['netspout_run_id'],
  evidence_ids: ['EVID-NETSPOUT'],
};

const rawEvent = {
  event_id: 'event-001',
  source_id: 'ietf-syslog-rfc5424',
  contract_id: 'native-ietf-syslog-rfc5424',
  provenance: ['STANDARD_DOCUMENTED', 'MODELED_PAYLOAD'],
  transport_id: 'transport-local-hec',
  sourcetype: 'netspout:rfc5424',
  sourcetype_authority: 'NETSPOUT_DEFINED',
  phase: 'BASELINE',
  raw: '<134>1 2026-10-06T12:00:00Z edge-router.example.invalid netspout 4242 LINK_STATE [netspout@32473 run_id="fixture-run" modeled="true"] interface=GigabitEthernet1/0/1 state=up',
};

const capabilities = {
  schema_version: '1.0.0',
  workflow: ['CHOOSE', 'PREVIEW', 'CONFIGURE', 'RUN', 'OBSERVE', 'INVESTIGATE'],
  modes: [
    { id: 'SCENARIO', label: 'Scenario', description: 'Generate one correlated modeled incident lifecycle.' },
    { id: 'DATA_SOURCE', label: 'Data Source', description: 'Generate one catalog source independently.' },
    { id: 'SOURCETYPE', label: 'Sourcetype / Event Family', description: 'Generate a supported sourcetype.' },
    { id: 'SINGLE_EVENT', label: 'Single Event', description: 'Generate and send exactly one supported event.' },
  ],
  sources: [source, unsupportedSource],
  scenarios: [scenario],
  sourcetypes: [{
    name: 'netspout:rfc5424',
    authority: 'NETSPOUT_DEFINED',
    source_id: source.source_id,
    vendor: source.vendor,
    product: source.product,
    source: source.telemetry_source,
    verification_state: source.verification_state,
    provenance: source.provenance,
    integration_ids: source.splunk_contract.integration_ids,
    cim_mappings: [],
    runnable: true,
    generation_controls: ['count', 'rate_eps', 'duration_seconds'],
  }],
  event_families: [{
    event_family_id: 'modeled-link-state',
    label: 'Modeled interface link-state event',
    source_id: source.source_id,
    sourcetype: 'netspout:rfc5424',
    runnable: true,
    count: 1,
  }],
  transports: [{
    transport_id: 'transport-local-hec',
    component: 'NetSpout telemetry dispatcher',
    protocol: 'HEC',
    signals: ['EVENTS'],
    compatible_source_ids: [source.source_id],
    verification_state: 'PARTIALLY_VERIFIED',
    implemented: true,
    evidence_ids: ['EVID-NETSPOUT'],
    notes: 'Lab path.',
  }],
  destinations: [{
    destination_id: 'destination-local-docker-splunk',
    destination_type: 'LOCAL_DOCKER_SPLUNK',
    accepted_transport_ids: ['transport-local-hec'],
    verification_state: 'PARTIALLY_VERIFIED',
    evidence_ids: ['EVID-NETSPOUT'],
    label: 'Local Docker Splunk',
    configured: true,
  }],
  integration_recommendations: [readiness],
  investigations: [recipe],
  raw_preview_policy: 'Fictional modeled values with RFC 5424 structure.',
};

const preview = {
  mode: 'SCENARIO',
  selection_id: scenario.scenario_id,
  scenario,
  sources: [source],
  bindings: [{
    source_id: source.source_id,
    generator_id: 'generator-rfc5424-modeled',
    transport_id: 'transport-local-hec',
    destination_id: 'destination-local-docker-splunk',
    validator_ids: ['validator-rfc5424-structure'],
  }],
  integration_readiness: [readiness],
  investigations: [recipe],
  raw_preview: [rawEvent],
  preview_notice: 'Preview values are fictional modeled values.',
  native_contract: source.native_contract,
  splunk_contract: source.splunk_contract,
  netspout_contract: source.netspout_contract,
  known_limitations: source.known_limitations,
};

const preflight = {
  state: 'READY_WITH_WARNINGS',
  checks: [
    { check_id: 'composition', label: 'Composition contract valid', state: 'PASS', detail: 'Validated references.' },
    { check_id: 'destination-reachable', label: 'Splunk destination reachable', state: 'PASS', detail: 'HEC HTTP 200.' },
    { check_id: 'index', label: 'Index available', state: 'WARN', detail: 'Verified after run.' },
  ],
  source_ids: [source.source_id],
  generator_ids: ['generator-rfc5424-modeled'],
  transport_id: 'transport-local-hec',
  destination_id: 'destination-local-docker-splunk',
};

const run = {
  run_id: '11111111-2222-4333-8444-555555555555',
  mode: 'SCENARIO',
  selection_id: scenario.scenario_id,
  scenario_id: scenario.scenario_id,
  source_ids: [source.source_id],
  generator_ids: ['generator-rfc5424-modeled'],
  transport_id: 'transport-local-hec',
  destination_id: 'destination-local-docker-splunk',
  started_at: '2026-10-06T12:00:00Z',
  completed_at: '2026-10-06T12:00:01Z',
  current_phase: 'RECOVERY',
  status: 'COMPLETED',
  events: Array.from({ length: 6 }, (_, index) => ({ ...rawEvent, event_id: `event-${index}`, phase: scenario.timeline[index].stage })),
  evidence: [
    { stage: 'GENERATED', state: 'PROVEN', count: 6, detail: 'Created locally.' },
    { stage: 'ENCODED_PUBLISHED', state: 'PROVEN', count: 6, detail: 'Structure validated.' },
    { stage: 'SENT', state: 'PROVEN', count: 6, detail: 'HEC accepted.' },
    { stage: 'RECEIVER_OBSERVED', state: 'NOT_AVAILABLE', count: 0, detail: 'No independent receiver adapter.' },
    { stage: 'NORMALIZED', state: 'NOT_AVAILABLE', count: 0, detail: 'No CIM claim.' },
    { stage: 'SPLUNK_DISPATCHED', state: 'PROVEN', count: 6, detail: 'HEC HTTP acceptance.' },
    { stage: 'SPLUNK_OBSERVED', state: 'PENDING', count: 0, detail: 'Awaiting search.' },
    { stage: 'VALIDATED', state: 'PROVEN', count: 6, detail: 'RFC structure only.' },
  ],
  integration_readiness: [readiness],
  investigations: [recipe],
  limitations: ['HEC acceptance proves dispatch, not indexed observation.'],
};

async function installMocks(page: Page) {
  if (process.env.PLAYWRIGHT_LIVE_GENERATION === '1') return;
  await page.route('**/api/generation/capabilities', (route) => route.fulfill({ json: capabilities }));
  await page.route('**/api/generation/preview', (route) => route.fulfill({ json: preview }));
  await page.route('**/api/generation/preflight', (route) => route.fulfill({ json: preflight }));
  await page.route('**/api/generation/runs', (route) => route.fulfill({ json: run }));
  await page.route('**/api/generation/runs/*/observe', (route) => route.fulfill({
    json: {
      ...run,
      status: 'OBSERVED',
      evidence: run.evidence.map((item) => item.stage === 'SPLUNK_OBSERVED' ? { ...item, state: 'PROVEN', count: 6, detail: 'Authenticated search proved observation.' } : item),
    },
  }));
  await page.route('**/api/generation/runs/*/investigate/*', (route) => route.fulfill({
    json: {
      run_id: run.run_id,
      recipe_id: recipe.recipe_id,
      portability: recipe.portability,
      query: recipe.spl.replace('$run_id$', run.run_id),
      status: 'SUCCEEDED',
      result_count: 6,
      detail: 'Splunk returned the investigation result.',
    },
  }));
  await page.route('**/health', (route) => route.fulfill({ json: { status: 'ok' } }));
}

const screenshotDir = path.resolve(process.cwd(), '../docs/implementation/images');
const screenshot = async (page: Page, name: string) => {
  await mkdir(screenshotDir, { recursive: true });
  await page.screenshot({ path: path.join(screenshotDir, name), fullPage: true });
};

test.beforeEach(async ({ page }) => {
  await installMocks(page);
});

test('supports Choose through Investigate with truthful stage distinctions', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto('/#/generate/scenarios');
  await expect(page.getByRole('heading', { name: 'Choose what to generate' })).toBeVisible();
  await screenshot(page, 'phase3-01-choose-scenario.png');
  await screenshot(page, 'phase3-12-simple-mode.png');

  await page.getByRole('button', { name: /^Preview/ }).click();
  await expect(page.getByRole('heading', { name: 'Preview generation plan' })).toBeVisible();
  await screenshot(page, 'phase3-02-scenario-preview.png');
  await page.getByRole('button', { name: /Preview Raw Event/ }).click();
  await expect(page.getByText('edge-router.example.invalid')).toBeVisible();
  await page.locator('[data-testid="scenario-topology"]').screenshot({ path: path.join(screenshotDir, 'phase3-03-scenario-topology.png') });

  await page.getByRole('button', { name: /^Configure/ }).click();
  await screenshot(page, 'phase3-04-configure.png');
  await page.getByRole('button', { name: 'Run Preflight' }).click();
  await expect(page.getByText('READY WITH WARNINGS')).toBeVisible();
  await screenshot(page, 'phase3-05-preflight.png');

  await page.getByRole('button', { name: /Continue to Run/ }).click();
  await page.getByRole('button', { name: 'Run', exact: true }).click();
  await expect(page.getByText(run.run_id)).toBeVisible();
  await screenshot(page, 'phase3-06-live-run.png');

  await page.getByRole('button', { name: /Observe Evidence/ }).click();
  await expect(page.getByRole('heading', { name: 'Observe evidence' })).toBeVisible();
  await expect(page.getByText('RECEIVER OBSERVED')).toBeVisible();
  await expect(page.getByText('NOT AVAILABLE').first()).toBeVisible();
  await screenshot(page, 'phase3-07-evidence-observe.png');

  await page.getByRole('button', { name: /^Investigate/ }).click();
  await expect(page.getByText('NETSPOUT SPECIFIC')).toBeVisible();
  await screenshot(page, 'phase3-08-investigate.png');
  await page.getByRole('button', { name: 'Run in Splunk' }).click();
  await expect(page.getByText(/SUCCEEDED/)).toBeVisible();
});

test('renders all generation modes and unsupported state without hard-coded inputs', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto('/#/generate/quick');
  await expect(page.getByRole('button', { name: /Data Source/ }).first()).toHaveClass(/is-selected/);
  await screenshot(page, 'phase3-09-data-source-mode.png');

  await page.getByRole('button', { name: /Sourcetype \/ Event Family/ }).first().click();
  await expect(page.getByText('netspout:rfc5424').first()).toBeVisible();
  await screenshot(page, 'phase3-10-sourcetype-mode.png');

  await page.getByRole('button', { name: /Single Event/ }).first().click();
  await expect(page.getByText('EXACTLY 1 EVENT')).toBeVisible();
  await screenshot(page, 'phase3-11-single-event-mode.png');

  await page.getByRole('button', { name: /Data Source/ }).first().click();
  await page.getByRole('button', { name: /Supply chain platform/ }).click();
  await expect(page.getByText('UNSUPPORTED TELEMETRY')).toBeVisible();
  await expect(page.getByRole('button', { name: /^Preview/ })).toBeDisabled();
  await screenshot(page, 'phase3-14-unsupported-state.png');
});

test('advanced mode reveals contracts and responsive layout remains usable', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto('/#/generate/scenarios');
  await page.getByRole('button', { name: 'Advanced', exact: true }).click();
  await page.getByRole('button', { name: /^Preview/ }).click();
  await expect(page.getByRole('heading', { name: 'Native Contract' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Splunk Contract' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'NetSpout Contract' })).toBeVisible();
  await screenshot(page, 'phase3-13-advanced-mode.png');

  await page.setViewportSize({ width: 390, height: 844 });
  await expect(page.getByRole('heading', { name: 'Preview generation plan' })).toBeVisible();
  await expect(page.locator('.generation-lab')).toBeVisible();
  const horizontalOverflow = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth);
  expect(horizontalOverflow).toBe(false);
});
