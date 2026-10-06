import { expect, test, type Page } from '@playwright/test';
import { mkdir } from 'node:fs/promises';
import path from 'node:path';

const screenshotDir = path.resolve(process.cwd(), '../docs/implementation/images');
const capture = async (page: Page, name: string) => {
  await mkdir(screenshotDir, { recursive: true });
  await page.screenshot({ path: path.join(screenshotDir, name), fullPage: true });
};

const source = {
  source_id: 'ietf-syslog-rfc5424',
  vendor: 'IETF',
  product: 'Syslog Protocol',
  product_family: 'Internet Standards',
  domains: ['netops'],
  telemetry_source: 'RFC 5424 syslog message',
  applicable_industries: [],
  verification_state: 'VERIFIED',
  provenance: ['STANDARD_DOCUMENTED', 'MODELED_PAYLOAD'],
  evidence_ids: ['EVID-IETF-RFC5424'],
  native_contract: { contract_id: 'native-ietf-syslog-rfc5424', verification_state: 'VERIFIED', format: 'RFC 5424', schema: 'PRI VERSION TIMESTAMP HOSTNAME APP-NAME PROCID MSGID STRUCTURED-DATA MSG', transports: [], structural_fields: [], evidence_ids: ['EVID-IETF-RFC5424'] },
  splunk_contract: { contract_id: 'splunk-ietf-syslog-rfc5424', verification_state: 'PARTIALLY_VERIFIED', input_mechanisms: ['HEC'], integration_ids: ['netspout-direct-structured-ingestion'], sourcetypes: [{ name: 'netspout:rfc5424', authority: 'NETSPOUT_DEFINED', evidence_ids: ['EVID-NETSPOUT'] }], cim_mappings: [], evidence_ids: ['EVID-NETSPOUT'] },
  netspout_contract: { contract_id: 'netspout-ietf-syslog-rfc5424', verification_state: 'PARTIALLY_VERIFIED', schema_classification: 'MODELED_PAYLOAD', generator: 'allowlist:rfc5424-modeled', validator: null, transports: ['HEC'], modeled_fields: [], structural_fields: [], scenario_ids: ['rfc5424-link-state-lifecycle'], generation_modes: ['MODE_A'], runtime_status: 'AVAILABLE', maturity: 'BETA', evidence_ids: ['EVID-NETSPOUT'] },
  spl_field_scope: { production_fields: ['_raw'], netspout_only_fields: ['netspout_run_id'], portable_spl_status: 'PARTIALLY_VERIFIED' },
  known_limitations: ['Modeled lab payload.'],
  generation: { runnable: true, state: 'READY', reason: 'Validated catalog source.' },
};

const timeline = ['BASELINE', 'PRECURSOR', 'INCIDENT', 'IMPACT', 'DETECTION', 'RECOVERY'].map((stage, index) => ({
  step_id: stage.toLowerCase(),
  stage,
  description: `${stage} modeled observation.`,
  state_changes: index < 2 ? { 'edge-router': index === 0 ? 'normal' : 'degraded' } : index < 5 ? { 'edge-router': 'affected' } : { 'edge-router': 'recovered', 'branch-user': 'recovered' },
  entity_state_changes: index < 2 ? { 'edge-router': index === 0 ? 'normal' : 'degraded' } : index < 5 ? { 'edge-router': 'affected' } : { 'edge-router': 'recovered', 'branch-user': 'recovered' },
  telemetry_state_changes: { 'ietf-syslog-rfc5424': index < 4 ? 'ACTIVE' : 'OBSERVED' },
  expected_observations: [`${stage} event expected.`],
  evidence_source_ids: ['ietf-syslog-rfc5424'],
  incident_ids: index >= 2 && index < 5 ? ['incident'] : [],
}));

const investigationStep = {
  step_id: 'find-lifecycle',
  recipe_id: 'investigate-rfc5424-run',
  title: 'Find and order the modeled lifecycle',
  question: 'Which entity changed state, and did Splunk observe every phase?',
  expected_finding: 'Six events progress from BASELINE through RECOVERY.',
  explanation: 'The events are observations of one modeled state transition.',
  hint: 'Confirm the result count and then inspect phase order.',
  node_ids: ['edge-router', 'splunk-local'],
  source_ids: ['ietf-syslog-rfc5424'],
};

const scenario = {
  scenario_id: 'rfc5424-link-state-lifecycle',
  title: 'Modeled Link-State Lifecycle',
  description: 'A standards-structured guided lab.',
  story: 'A fictional branch uplink deteriorates, goes down, and returns to service.',
  domain: 'NETOPS',
  category: 'OPERATIONAL_RESILIENCE',
  technical_description: 'Six modeled RFC 5424 events use the declared HEC lab path.',
  difficulty: 'BEGINNER',
  expected_duration_minutes: 1,
  learning_objectives: ['Distinguish sent from observed evidence.', 'Reconstruct an ordered lifecycle.'],
  skills_practiced: ['Timeline reconstruction'],
  expected_outcome: 'Prove all six modeled events reached Splunk.',
  baseline_description: 'The fictional uplink begins healthy.',
  incident_description: 'The modeled uplink transitions down and affects the user path.',
  discovery_prompt: 'Determine which entity changed state.',
  learning_hints: ['Compare generated and observed counts.'],
  business_impact: 'A fictional user loses application reachability.',
  prerequisites: ['Configured local Docker Splunk destination'],
  technology_ids: ['rfc5424', 'splunk-hec'],
  source_ids: ['ietf-syslog-rfc5424'],
  entities: ['Branch User', 'Edge Router', 'Local Splunk'],
  zones: [{ zone_id: 'branch-zone', label: 'Fictional Branch' }, { zone_id: 'observability-zone', label: 'Observability' }],
  nodes: [
    { node_id: 'branch-user', technology_id: 'generic-user', zone_id: 'branch-zone', role: 'user', source_ids: [], label: 'Branch User', entity_id: 'fictional-user', description: 'Fictional impacted user.' },
    { node_id: 'edge-router', technology_id: 'rfc5424', zone_id: 'branch-zone', role: 'router', source_ids: ['ietf-syslog-rfc5424'], label: 'Edge Router', entity_id: 'fictional-router', description: 'Modeled source entity.' },
    { node_id: 'splunk-local', technology_id: 'splunk-hec', zone_id: 'observability-zone', role: 'splunk', source_ids: [], label: 'Local Splunk', entity_id: 'local-splunk', description: 'Local destination.' },
  ],
  relationships: [
    { relationship_id: 'user-router', source_node_id: 'branch-user', target_node_id: 'edge-router', relationship_type: 'depends-on', protocol: null, purpose: 'User path dependency.', telemetry_source_ids: [], incident_relevance: 'User impact follows uplink loss.' },
    { relationship_id: 'router-splunk', source_node_id: 'edge-router', target_node_id: 'splunk-local', relationship_type: 'forwards-telemetry-to', protocol: 'HEC', purpose: 'Lab telemetry delivery.', telemetry_source_ids: ['ietf-syslog-rfc5424'], incident_relevance: null },
  ],
  telemetry_paths: [{ path_id: 'rfc5424-path', source_id: 'ietf-syslog-rfc5424', producer_node_id: 'edge-router', observer_node_id: 'splunk-local', label: 'RFC 5424 events', protocol: 'HEC' }],
  incident_path: ['edge-router', 'branch-user'],
  incident_summary: 'The modeled link state affects the fictional user path.',
  runtime_state_keys: ['normal', 'active', 'degraded', 'affected', 'recovered'],
  timeline,
  incidents: [{ incident_id: 'incident', source_ids: ['ietf-syslog-rfc5424'], assertion: 'Modeled fixture only.', corroboration_required: false }],
  parameters: [],
  expected_evidence: ['Six ordered modeled RFC 5424 events.'],
  investigation_recipe_ids: ['investigate-rfc5424-run'],
  investigation_steps: [investigationStep],
  integration_recommendation_ids: ['recommend-rfc5424-direct-ingestion'],
  validation_expectations: ['GENERATED', 'SENT', 'SPLUNK_OBSERVED', 'SOURCETYPE_VERIFIED'].map((evidence_stage) => ({ validation_id: evidence_stage.toLowerCase(), label: `${evidence_stage} expected`, evidence_stage, expected_state: 'PROVEN', requirement: 'REQUIRED', source_id: 'ietf-syslog-rfc5424' })),
  visualization: { mode: 'AUTOMATIC', direction: 'LEFT_TO_RIGHT', curated_layout_ref: null },
  replay_policy: { creates_new_run_id: true, preserves_history: true, reset_to_step: 'RUN' },
  troubleshooting_steps: [],
  cim_validation: [],
  production_replication_guidance: ['Replace lab-only correlation with verified production fields.'],
  curated_layout_ref: null,
  composition_id: 'compose-rfc5424-link-state-local',
  verification_state: 'PARTIALLY_VERIFIED',
  maturity: 'BETA',
  source_count: 1,
  integration_count: 1,
  runnable: true,
  guided_completeness: { state: 'PARTIAL', passed: 12, total: 12, checks: {}, production_guidance_available: true },
};

const recipe = {
  recipe_id: 'investigate-rfc5424-run',
  title: 'Trace the modeled link-state lifecycle',
  objective: 'Find one run.',
  question: investigationStep.question,
  expected_finding: investigationStep.expected_finding,
  explanation: investigationStep.explanation,
  hint: investigationStep.hint,
  portability: 'NETSPOUT_SPECIFIC',
  spl: 'search index=idx_network_ops sourcetype="netspout:rfc5424" netspout_run_id="$run_id$" | sort 0 _time',
  source_ids: ['ietf-syslog-rfc5424'],
  required_fields: ['netspout_run_id'],
  cim_requirements: [],
  netspout_only_fields: ['netspout_run_id'],
  evidence_ids: ['EVID-NETSPOUT'],
};

const capabilities = {
  schema_version: '1.0.0',
  workflow: ['CHOOSE', 'PREVIEW', 'CONFIGURE', 'RUN', 'OBSERVE', 'INVESTIGATE'],
  guided_workflow: ['UNDERSTAND', 'PREPARE', 'RUN', 'OBSERVE', 'INVESTIGATE', 'VALIDATE'],
  modes: [],
  sources: [source],
  scenarios: [scenario],
  sourcetypes: [],
  event_families: [],
  transports: [],
  destinations: [],
  integration_recommendations: [],
  investigations: [recipe],
  raw_preview_policy: 'Modeled fixture.',
};

const preview = {
  mode: 'SCENARIO',
  selection_id: scenario.scenario_id,
  scenario,
  sources: [source],
  bindings: [{ source_id: source.source_id, generator_id: 'generator-rfc5424-modeled', transport_id: 'transport-local-hec', destination_id: 'destination-local-docker-splunk', validator_ids: ['validator-rfc5424-structure'] }],
  integration_readiness: [{ recommendation_id: 'recommend-rfc5424-direct-ingestion', source_id: source.source_id, integration_id: 'netspout-direct-structured-ingestion', requirement: 'REQUIRED', evidence_ids: ['EVID-NETSPOUT'], notes: 'Lab only.', name: 'NetSpout direct structured ingestion', publisher: 'NetSpout', support_state: 'LAB_ONLY', detected: true, evidence: [] }],
  investigations: [recipe],
  raw_preview: [],
  preview_notice: 'Fictional modeled values.',
  native_contract: source.native_contract,
  splunk_contract: source.splunk_contract,
  netspout_contract: source.netspout_contract,
  known_limitations: source.known_limitations,
};

const preflight = {
  state: 'READY_WITH_WARNINGS',
  checks: [
    { check_id: 'composition', label: 'Scenario contract valid', state: 'PASS', detail: 'Validated references.' },
    { check_id: 'generator', label: 'Generator available', state: 'PASS', detail: 'Allow-listed adapter.' },
    { check_id: 'transport', label: 'Transport available', state: 'PASS', detail: 'HEC lab path.' },
    { check_id: 'destination', label: 'Splunk destination reachable', state: 'PASS', detail: 'HTTP 200.' },
    { check_id: 'index', label: 'Index observation', state: 'WARN', detail: 'Verified after run.' },
  ],
  source_ids: [source.source_id],
  generator_ids: ['generator-rfc5424-modeled'],
  transport_id: 'transport-local-hec',
  destination_id: 'destination-local-docker-splunk',
};

const evidence = (observed: boolean) => [
  { stage: 'GENERATED', state: 'PROVEN', count: 6, detail: 'Created locally.' },
  { stage: 'ENCODED_PUBLISHED', state: 'PROVEN', count: 6, detail: 'Structure validated.' },
  { stage: 'SENT', state: 'PROVEN', count: 6, detail: 'HEC accepted.' },
  { stage: 'RECEIVER_OBSERVED', state: 'NOT_AVAILABLE', count: 0, detail: 'No independent receiver adapter.' },
  { stage: 'NORMALIZED', state: 'NOT_AVAILABLE', count: 0, detail: 'No CIM claim.' },
  { stage: 'SPLUNK_DISPATCHED', state: 'PROVEN', count: 6, detail: 'HEC HTTP acceptance.' },
  { stage: 'SPLUNK_OBSERVED', state: observed ? 'PROVEN' : 'PENDING', count: observed ? 6 : 0, detail: observed ? 'Authenticated search proved observation.' : 'Awaiting search.' },
  { stage: 'SOURCETYPE_VERIFIED', state: observed ? 'PROVEN' : 'PENDING', count: observed ? 6 : 0, detail: observed ? 'Observed.' : 'Awaiting search.' },
  { stage: 'FIELDS_VERIFIED', state: observed ? 'PROVEN' : 'PENDING', count: observed ? 6 : 0, detail: observed ? 'Observed.' : 'Awaiting search.' },
  { stage: 'VALIDATED', state: 'PROVEN', count: 6, detail: 'Structure only.' },
];

const makeRun = (runId: string, observed: boolean) => ({
  run_id: runId,
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
  status: observed ? 'OBSERVED' : 'COMPLETED',
  events: timeline.map((item, index) => ({ event_id: `event-${index}`, source_id: source.source_id, contract_id: source.native_contract.contract_id, provenance: source.provenance, transport_id: 'transport-local-hec', sourcetype: 'netspout:rfc5424', sourcetype_authority: 'NETSPOUT_DEFINED', phase: item.stage, raw: `<134>1 2026-10-06T12:00:0${index}Z edge-router.example.invalid netspout 4242 LINK_STATE - modeled=true` })),
  evidence: evidence(observed),
  validation: ['GENERATED', 'SENT', 'SPLUNK_OBSERVED', 'SOURCETYPE_VERIFIED'].map((stage) => ({ validation_id: stage.toLowerCase(), label: `${stage} expected`, evidence_stage: stage, requirement: 'REQUIRED', state: observed || ['GENERATED', 'SENT'].includes(stage) ? 'PROVEN' : 'PENDING', detail: 'Evidence-derived result.' })),
  integration_readiness: preview.integration_readiness,
  investigations: [recipe],
  limitations: ['HEC acceptance is not indexed observation.', 'No CIM claim.'],
});

async function installMocks(page: Page) {
  if (process.env.PLAYWRIGHT_LIVE_GUIDED === '1') return;
  let runCount = 0;
  await page.route('**/api/generation/capabilities', (route) => route.fulfill({ json: capabilities }));
  await page.route('**/api/generation/preview', (route) => route.fulfill({ json: preview }));
  await page.route('**/api/generation/preflight', (route) => route.fulfill({ json: preflight }));
  await page.route('**/api/generation/runs', (route) => {
    runCount += 1;
    route.fulfill({ json: makeRun(runCount === 1 ? '11111111-2222-4333-8444-555555555555' : 'aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee', false) });
  });
  await page.route('**/api/generation/runs/*/observe', (route) => route.fulfill({ json: makeRun('11111111-2222-4333-8444-555555555555', true) }));
  await page.route('**/api/generation/runs/*/investigate/*', (route) => route.fulfill({ json: { run_id: '11111111-2222-4333-8444-555555555555', recipe_id: recipe.recipe_id, portability: recipe.portability, query: recipe.spl, status: 'SUCCEEDED', result_count: 6, detail: 'Splunk returned results.' } }));
}

test.beforeEach(async ({ page }) => {
  await installMocks(page);
  await page.setViewportSize({ width: 1440, height: 1000 });
});

test('completes the guided scenario journey and replay', async ({ page }) => {
  await page.goto('/#/generate/scenarios');
  await expect(page.getByRole('heading', { name: scenario.title })).toBeVisible();
  await capture(page, 'phase4-01-scenario-home.png');

  await page.locator('[data-node-id="edge-router"]').click();
  await expect(page.getByLabel('Topology technical inspector')).toBeVisible();
  await page.getByLabel('Topology technical inspector').scrollIntoViewIfNeeded();
  await capture(page, 'phase4-04-node-inspector.png');
  await page.locator('.generation-topology__edge').last().click();
  await expect(page.getByText('Selected connection')).toBeVisible();

  await page.getByRole('button', { name: 'Telemetry Lens' }).click();
  await capture(page, 'phase4-05-telemetry-lens.png');
  await page.getByRole('button', { name: 'Incident Lens' }).click();
  await capture(page, 'phase4-06-incident-lens.png');
  await page.getByRole('button', { name: 'Splunk Lens' }).click();
  await capture(page, 'phase4-07-splunk-lens.png');

  await page.getByRole('button', { name: 'Start guided lab' }).click();
  await expect(page.getByRole('heading', { name: 'Understand the modeled incident' })).toBeVisible();
  await capture(page, 'phase4-02-guided-understand.png');
  await page.locator('[data-testid="scenario-topology"]').screenshot({ path: path.join(screenshotDir, 'phase4-03-automatic-topology.png') });

  await page.getByRole('button', { name: 'Prepare environment' }).click();
  await page.getByRole('button', { name: 'Run preflight' }).click();
  await expect(page.getByText('READY WITH WARNINGS')).toBeVisible();
  await capture(page, 'phase4-08-prepare-preflight.png');

  await page.getByRole('button', { name: 'Continue to run' }).click();
  await page.getByRole('button', { name: 'Run scenario' }).click();
  await expect(page.getByText(/Run ID/)).toBeVisible();
  await capture(page, 'phase4-09-running-scenario.png');
  await page.locator('.guided-timeline button').filter({ hasText: 'INCIDENT' }).click();
  await expect(page.locator('[data-node-id="edge-router"]')).toHaveClass(/is-selected/);
  await capture(page, 'phase4-10-active-timeline.png');

  await page.getByRole('button', { name: 'Observe evidence' }).click();
  const refreshObservation = page.getByRole('button', { name: 'Refresh Splunk observation' });
  const observedEvidence = page.getByText(/Authenticated (?:Splunk search proved (?:indexed )?|search proved )observation\./);
  for (let attempt = 0; attempt < (process.env.PLAYWRIGHT_LIVE_GUIDED === '1' ? 5 : 1); attempt += 1) {
    await refreshObservation.click();
    if (await observedEvidence.isVisible()) break;
    await page.waitForTimeout(1000);
  }
  await expect(observedEvidence).toBeVisible();
  await expect(refreshObservation).toBeEnabled();
  await expect(page.getByText(/Evidence focus:.*Edge Router/)).toBeVisible();
  await capture(page, 'phase4-11-observe-evidence.png');

  await page.getByRole('button', { name: 'Investigate', exact: true }).click();
  await page.getByRole('heading', { name: scenario.investigation_steps[0].title }).scrollIntoViewIfNeeded();
  await capture(page, 'phase4-12-guided-investigation.png');
  await page.getByRole('button', { name: 'View topology' }).click();
  await expect(page.locator('[data-node-id="edge-router"]')).toHaveClass(/is-selected/);
  await page.getByRole('button', { name: 'Run in Splunk' }).click();
  await expect(page.getByText(/SUCCEEDED · 6 results/)).toBeVisible();
  await capture(page, 'phase4-13-spl-results.png');

  await page.getByRole('button', { name: 'Validate learning' }).click();
  await expect(page.getByRole('heading', { name: 'Validate only what was proven' })).toBeVisible();
  await capture(page, 'phase4-14-validation.png');
  await page.getByRole('button', { name: 'Complete scenario' }).click();
  await expect(page.getByText('Scenario complete')).toBeVisible();
  await capture(page, 'phase4-15-completion.png');

  const firstRun = await page.locator('.guided-complete__proof code').textContent();
  await page.getByRole('button', { name: 'Replay scenario' }).click();
  await expect(page.getByText('Replay created a new run context.')).toBeVisible();
  const currentRun = await page.locator('.guided-run-strip code').textContent();
  expect(currentRun).not.toBe(firstRun);
  await capture(page, 'phase4-16-replay.png');
});

test('advanced mode reveals guided runtime detail', async ({ page }) => {
  await page.goto('/#/generate/scenarios');
  await page.getByRole('button', { name: 'Advanced', exact: true }).click();
  await page.getByRole('button', { name: 'Advanced run' }).click();
  await page.getByRole('button', { name: 'Run preflight' }).click();
  await page.getByRole('button', { name: 'Continue to run' }).click();
  await page.getByRole('button', { name: 'Run scenario' }).click();
  await page.getByRole('button', { name: 'Observe evidence' }).click();
  const refreshObservation = page.getByRole('button', { name: 'Refresh Splunk observation' });
  await refreshObservation.click();
  await expect(refreshObservation).toBeEnabled();
  await page.getByRole('button', { name: 'Investigate', exact: true }).click();
  await page.getByRole('button', { name: 'Run in Splunk' }).click();
  await page.getByRole('button', { name: 'Validate learning' }).click();
  await page.getByRole('button', { name: 'Complete scenario' }).click();
  const advancedDetail = page.getByText('Advanced run identity');
  await expect(advancedDetail).toBeVisible();
  await advancedDetail.scrollIntoViewIfNeeded();
  await capture(page, 'phase4-17-advanced-mode.png');
});

test('same deterministic renderer handles a mixed-vendor architecture fixture', async ({ page }) => {
  const fixture = {
    ...scenario,
    scenario_id: 'fixture-mixed-vendor-topology',
    title: 'Mixed-Vendor Architecture Fixture',
    story: 'Architecture-only fixture. No telemetry support claim.',
    domain: 'ARCHITECTURE TEST',
    difficulty: 'FIXTURE ONLY',
    learning_objectives: ['Prove one neutral renderer handles mixed-vendor identity metadata.'],
    expected_outcome: 'Deterministic node placement only; no runtime or telemetry claim.',
    business_impact: 'Not applicable. This non-production fixture validates renderer neutrality.',
    technology_ids: ['aruba-edge', 'cisco-ise', 'palo-alto-firewall', 'microsoft-entra', 'crowdstrike-endpoint'],
    source_ids: [],
    zones: [{ zone_id: 'access', label: 'Access' }, { zone_id: 'security', label: 'Security' }, { zone_id: 'cloud', label: 'Cloud' }],
    nodes: [
      { node_id: 'aruba-edge', technology_id: 'aruba-edge', zone_id: 'access', role: 'switch', source_ids: [], label: 'Aruba Edge', vendor: 'Aruba' },
      { node_id: 'cisco-ise', technology_id: 'cisco-ise', zone_id: 'security', role: 'identity', source_ids: [], label: 'Cisco ISE', vendor: 'Cisco' },
      { node_id: 'palo-firewall', technology_id: 'palo-alto-firewall', zone_id: 'security', role: 'firewall', source_ids: [], label: 'Palo Alto Firewall', vendor: 'Palo Alto Networks' },
      { node_id: 'entra', technology_id: 'microsoft-entra', zone_id: 'cloud', role: 'identity', source_ids: [], label: 'Microsoft Entra', vendor: 'Microsoft' },
      { node_id: 'crowdstrike', technology_id: 'crowdstrike-endpoint', zone_id: 'access', role: 'endpoint', source_ids: [], label: 'CrowdStrike Endpoint', vendor: 'CrowdStrike' },
    ],
    relationships: [
      { relationship_id: 'endpoint-edge', source_node_id: 'crowdstrike', target_node_id: 'aruba-edge', relationship_type: 'connected-to', telemetry_source_ids: [] },
      { relationship_id: 'edge-ise', source_node_id: 'aruba-edge', target_node_id: 'cisco-ise', relationship_type: 'authenticates-through', telemetry_source_ids: [] },
      { relationship_id: 'edge-firewall', source_node_id: 'aruba-edge', target_node_id: 'palo-firewall', relationship_type: 'routes-through', telemetry_source_ids: [] },
      { relationship_id: 'ise-entra', source_node_id: 'cisco-ise', target_node_id: 'entra', relationship_type: 'depends-on', telemetry_source_ids: [] },
    ],
    telemetry_paths: [],
    incident_path: [],
    timeline: [],
    runnable: true,
    source_count: 0,
    integration_count: 0,
    guided_completeness: { state: 'PARTIAL', passed: 3, total: 12, checks: {}, production_guidance_available: false },
  };
  await page.route('**/api/generation/capabilities', (route) => route.fulfill({ json: { ...capabilities, scenarios: [fixture], sources: [] } }));
  await page.goto('/#/generate/scenarios');
  await expect(page.getByRole('heading', { name: fixture.title })).toBeVisible();
  const first = await page.locator('[data-node-id]').evaluateAll((nodes) => nodes.map((node) => node.getAttribute('data-layout')));
  await page.reload();
  const second = await page.locator('[data-node-id]').evaluateAll((nodes) => nodes.map((node) => node.getAttribute('data-layout')));
  expect(second).toEqual(first);
  expect(first).toHaveLength(5);
  await capture(page, 'phase4-18-mixed-vendor-fixture.png');
});

test('same renderer handles a multi-product architecture fixture without vendor branches', async ({ page }) => {
  const fixture = {
    ...scenario,
    scenario_id: 'fixture-multi-product-topology',
    title: 'Multi-Product Architecture Fixture',
    story: 'Architecture-only Cisco identity fixture. No telemetry support claim.',
    domain: 'ARCHITECTURE TEST',
    difficulty: 'FIXTURE ONLY',
    source_ids: [],
    zones: [{ zone_id: 'branch', label: 'Branch' }, { zone_id: 'wan', label: 'WAN' }, { zone_id: 'security', label: 'Security' }, { zone_id: 'application', label: 'Application' }],
    nodes: [
      { node_id: 'branch', technology_id: 'fixture-cisco-ios-xe', zone_id: 'branch', role: 'router', source_ids: [], label: 'Branch Edge', vendor: 'Cisco' },
      { node_id: 'wan', technology_id: 'fixture-cisco-sdwan', zone_id: 'wan', role: 'router', source_ids: [], label: 'WAN Fabric', vendor: 'Cisco' },
      { node_id: 'security', technology_id: 'fixture-cisco-security', zone_id: 'security', role: 'firewall', source_ids: [], label: 'Security Edge', vendor: 'Cisco' },
      { node_id: 'application', technology_id: 'fixture-application', zone_id: 'application', role: 'application', source_ids: [], label: 'Application', vendor: null },
      { node_id: 'splunk', technology_id: 'fixture-splunk', zone_id: 'application', role: 'splunk', source_ids: [], label: 'Splunk', vendor: 'Splunk' },
    ],
    relationships: [
      { relationship_id: 'branch-wan', source_node_id: 'branch', target_node_id: 'wan', relationship_type: 'routes-through', telemetry_source_ids: [] },
      { relationship_id: 'wan-security', source_node_id: 'wan', target_node_id: 'security', relationship_type: 'routes-through', telemetry_source_ids: [] },
      { relationship_id: 'security-app', source_node_id: 'security', target_node_id: 'application', relationship_type: 'connected-to', telemetry_source_ids: [] },
      { relationship_id: 'app-splunk', source_node_id: 'application', target_node_id: 'splunk', relationship_type: 'monitors', telemetry_source_ids: [] },
    ],
    telemetry_paths: [],
    incident_path: [],
    timeline: [],
    runnable: true,
    source_count: 0,
    integration_count: 0,
  };
  await page.route('**/api/generation/capabilities', (route) => route.fulfill({ json: { ...capabilities, scenarios: [fixture], sources: [] } }));
  await page.goto('/#/generate/scenarios');
  await expect(page.getByRole('heading', { name: fixture.title })).toBeVisible();
  await expect(page.locator('[data-node-id]')).toHaveCount(5);
  await expect(page.locator('[data-node-id="branch"]')).toHaveAttribute('data-layout', /\d+\.\d{2}:\d+\.\d{2}/);
});
