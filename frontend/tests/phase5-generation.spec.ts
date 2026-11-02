import { expect, test, type Page } from '@playwright/test';

const source = (id: string, label: string, protocol: string) => ({
  source_id: id,
  vendor: 'Fixture',
  product: label,
  product_family: 'Phase 5',
  domains: ['netops'],
  telemetry_source: label,
  applicable_industries: [],
  verification_state: 'VERIFIED',
  provenance: ['MODELED_PAYLOAD'],
  evidence_ids: [],
  native_contract: { contract_id: `native-${id}`, verification_state: 'VERIFIED', format: protocol, schema: protocol, transports: [], structural_fields: [], evidence_ids: [] },
  splunk_contract: { contract_id: `splunk-${id}`, verification_state: 'PARTIALLY_VERIFIED', input_mechanisms: ['HEC'], integration_ids: ['fixture-integration'], sourcetypes: [{ name: `fixture:${id}`, authority: 'NETSPOUT_DEFINED', evidence_ids: [] }], cim_mappings: [], evidence_ids: [] },
  netspout_contract: { contract_id: `netspout-${id}`, verification_state: 'PARTIALLY_VERIFIED', schema_classification: 'MODELED_PAYLOAD', generator: 'fixture', validator: null, transports: ['HEC'], modeled_fields: [], structural_fields: [], scenario_ids: ['phase5-multi-channel'], generation_modes: ['MODE_A'], runtime_status: 'AVAILABLE', maturity: 'BETA', evidence_ids: [] },
  spl_field_scope: { production_fields: [], netspout_only_fields: [], portable_spl_status: 'PARTIALLY_VERIFIED' },
  known_limitations: [],
  generation: { runnable: true, state: 'READY', reason: 'Fixture runtime binding.' },
});

const sources = [
  source('syslog-source', 'RFC 5424 syslog', 'RFC 5424 UTF-8 over TCP'),
  source('flow-source', 'IPFIX flow', 'IPFIX binary records over UDP'),
];

const scenario = {
  scenario_id: 'phase5-multi-channel',
  title: 'Phase 5 Multi-Channel Scenario',
  description: 'Exercises native syslog and IPFIX channels.',
  story: 'A router emits two selected telemetry channels.',
  difficulty: 'INTERMEDIATE',
  expected_duration_minutes: 1,
  learning_objectives: ['Compare channel evidence.'],
  business_impact: 'Verifies independent channel delivery.',
  prerequisites: [],
  technology_ids: ['syslog', 'ipfix'],
  source_ids: sources.map((item) => item.source_id),
  entities: ['Router', 'Collector', 'Splunk'],
  zones: [{ zone_id: 'source', label: 'Source' }, { zone_id: 'observe', label: 'Observe' }],
  nodes: [
    { node_id: 'router', technology_id: 'router', zone_id: 'source', role: 'router', source_ids: sources.map((item) => item.source_id), label: 'Router' },
    { node_id: 'collector', technology_id: 'collector', zone_id: 'observe', role: 'collector', source_ids: [], label: 'Collector' },
    { node_id: 'splunk', technology_id: 'splunk', zone_id: 'observe', role: 'splunk', source_ids: [], label: 'Splunk' },
  ],
  relationships: [
    { relationship_id: 'native-edge', source_node_id: 'router', target_node_id: 'collector', relationship_type: 'native-telemetry', protocol: 'TCP / UDP', telemetry_source_ids: sources.map((item) => item.source_id) },
    { relationship_id: 'hec-edge', source_node_id: 'collector', target_node_id: 'splunk', relationship_type: 'destination-delivery', protocol: 'HEC', telemetry_source_ids: sources.map((item) => item.source_id) },
  ],
  telemetry_paths: sources.map((item) => ({ path_id: item.source_id, source_id: item.source_id, producer_node_id: 'router', observer_node_id: 'splunk', label: item.telemetry_source, protocol: 'NATIVE' })),
  incident_path: ['router'],
  runtime_state_keys: [],
  timeline: [{ step_id: 'incident', stage: 'INCIDENT', description: 'Emit selected channels.', state_changes: { router: 'degraded' }, incident_ids: [] }],
  expected_evidence: ['Per-channel runtime evidence.'],
  investigation_recipe_ids: [],
  integration_recommendation_ids: ['fixture-ready'],
  production_replication_guidance: [],
  composition_id: 'phase5-composition',
  verification_state: 'PARTIALLY_VERIFIED',
  maturity: 'BETA',
  source_count: 2,
  integration_count: 1,
  runnable: true,
};

const readiness = { recommendation_id: 'fixture-ready', source_id: 'syslog-source', integration_id: 'fixture-integration', requirement: 'REQUIRED', evidence_ids: [], notes: 'Fixture integration.', name: 'Splunk destination integration', publisher: 'Fixture', support_state: 'LAB_ONLY', detected: true, evidence: [] };
const bindings = [
  { source_id: 'syslog-source', generator_id: 'syslog-generator', transport_id: 'transport-native-syslog-tcp', source_transport_id: 'transport-native-syslog-tcp', destination_transport_id: 'transport-local-hec', destination_id: 'destination-local-docker-splunk', validator_ids: [], required: true, runtime_adapter_ref: 'run_syslog', receiver_component_id: 'syslog_receiver' },
  { source_id: 'flow-source', generator_id: 'flow-generator', transport_id: 'transport-native-ipfix-udp', source_transport_id: 'transport-native-ipfix-udp', destination_transport_id: 'transport-local-hec', destination_id: 'destination-local-docker-splunk', validator_ids: [], required: false, runtime_adapter_ref: 'run_flow', receiver_component_id: 'flow_collector' },
];
const evidence = (generated: number, received: number, splunk: number, failed = false) => [
  { stage: 'GENERATED', state: 'PROVEN', count: generated, detail: 'Runtime generated.' },
  { stage: 'COLLECTOR_RECEIVED', state: received ? 'PROVEN' : 'FAILED', count: received, detail: 'Collector evidence.' },
  { stage: 'SPLUNK_OBSERVED', state: splunk ? 'PROVEN' : 'PENDING', count: splunk, detail: 'Search-backed observation.' },
  ...(failed ? [{ stage: 'DECODED', state: 'FAILED', count: 0, detail: 'Decode failed.' }] : []),
];
const channelResults = [
  { source_id: 'syslog-source', channel: 'SYSLOG', required: true, runtime_adapter_ref: 'run_syslog', receiver_component_id: 'syslog_receiver', source_transport_id: 'transport-native-syslog-tcp', destination_transport_id: 'transport-local-hec', run_id: 'phase5-run', scenario_id: scenario.scenario_id, entity_id: 'router', seed: 5, clock_state: '2026-10-06T00:00:00Z', status: 'COMPLETED', evidence: evidence(7, 7, 6), errors: [] },
  { source_id: 'flow-source', channel: 'IPFIX', required: false, runtime_adapter_ref: 'run_flow', receiver_component_id: 'flow_collector', source_transport_id: 'transport-native-ipfix-udp', destination_transport_id: 'transport-local-hec', run_id: 'phase5-run', scenario_id: scenario.scenario_id, entity_id: 'router', seed: 5, clock_state: '2026-10-06T00:00:00Z', status: 'FAILED', evidence: evidence(4, 2, 0, true), errors: ['Collector decode failed without exposing payload secrets.'] },
];
const capabilities = {
  schema_version: '1.0.0',
  workflow: ['CHOOSE', 'PREVIEW', 'CONFIGURE', 'RUN', 'OBSERVE', 'INVESTIGATE'],
  modes: [{ id: 'SCENARIO', label: 'Scenario', description: 'Run selected telemetry channels.' }],
  sources,
  scenarios: [scenario],
  sourcetypes: [],
  event_families: [],
  transports: [{ transport_id: 'transport-local-hec', component: 'Splunk destination', protocol: 'HEC', signals: ['EVENTS'], compatible_source_ids: sources.map((item) => item.source_id), verification_state: 'PARTIALLY_VERIFIED', implemented: true, evidence_ids: [], notes: 'Destination path.' }],
  destinations: [{ destination_id: 'destination-local-docker-splunk', destination_type: 'SPLUNK', accepted_transport_ids: ['transport-local-hec'], verification_state: 'PARTIALLY_VERIFIED', evidence_ids: [], label: 'Local Splunk', configured: true }],
  integration_recommendations: [readiness],
  investigations: [],
  native_runtime: {
    capabilities: bindings.map((item, index) => ({ channel: index ? 'IPFIX' : 'SYSLOG', level: 'EXECUTABLE', source_transport: item.source_transport_id, destination_transport: item.destination_transport_id, evidence_stages: ['GENERATED', 'COLLECTOR_RECEIVED', 'SPLUNK_OBSERVED'], note: 'Fixture capability.' })),
    component_health: [{ component: 'syslog_receiver', state: 'RUNNING', detail: 'Listening.', channel: 'SYSLOG' }],
  },
  raw_preview_policy: 'Native preview may be empty.',
};
const preview = { mode: 'SCENARIO', selection_id: scenario.scenario_id, scenario, sources, bindings, integration_readiness: [readiness], investigations: [], raw_preview: [], preview_notice: 'Native payload is not fabricated.', native_contract: sources[0].native_contract, splunk_contract: sources[0].splunk_contract, netspout_contract: sources[0].netspout_contract, known_limitations: [] };
const preflight = { state: 'READY_WITH_WARNINGS', checks: [{ check_id: 'native-syslog', label: 'syslog_receiver', state: 'PASS', detail: 'RUNNING' }, { check_id: 'native-flow', label: 'flow_collector', state: 'WARN', detail: 'Optional collector is DEGRADED.' }, { check_id: 'destination-reachable', label: 'Splunk HEC reachable', state: 'PASS', detail: 'HEC health succeeded.' }], source_ids: sources.map((item) => item.source_id), generator_ids: ['syslog-generator', 'flow-generator'], transport_id: 'transport-local-hec', destination_id: 'destination-local-docker-splunk' };
const run = { run_id: 'phase5-run', mode: 'SCENARIO', selection_id: scenario.scenario_id, scenario_id: scenario.scenario_id, source_ids: sources.map((item) => item.source_id), generator_ids: ['syslog-generator', 'flow-generator'], transport_id: 'transport-local-hec', destination_id: 'destination-local-docker-splunk', started_at: '2026-10-06T00:00:00Z', completed_at: '2026-10-06T00:00:01Z', current_phase: 'INCIDENT', status: 'DEGRADED', events: [], evidence: [{ stage: 'GENERATED', state: 'PROVEN', count: 11, detail: 'Aggregated by backend.' }], channel_results: channelResults, integration_readiness: [readiness], investigations: [], limitations: ['Counts are independently proven per channel.'] };

async function mockGeneration(page: Page) {
  await page.route('**/api/generation/capabilities', (route) => route.fulfill({ json: capabilities }));
  await page.route('**/api/generation/preview', (route) => route.fulfill({ json: preview }));
  await page.route('**/api/generation/preflight', (route) => route.fulfill({ json: preflight }));
  await page.route('**/api/generation/runs', (route) => route.fulfill({ json: run }));
  await page.route('**/health', (route) => route.fulfill({ json: { status: 'ok' } }));
}

test('shows simple readiness while advanced mode exposes native transport detail', async ({ page }) => {
  await mockGeneration(page);
  await page.goto('/#/observe/live-runs');
  await page.getByRole('button', { name: /^Preview/ }).click();
  await expect(page.getByRole('heading', { name: 'Selected telemetry channels' })).toBeVisible();
  await expect(page.getByText('Splunk destination integration')).toBeVisible();
  await expect(page.getByText('transport-native-syslog-tcp')).toHaveCount(0);

  await page.getByRole('button', { name: 'Advanced', exact: true }).click();
  await expect(page.getByText('transport-native-syslog-tcp')).toBeVisible();
  await expect(page.getByText('syslog_receiver')).toBeVisible();
  await expect(page.getByText('No raw preview was returned.')).toBeVisible();
});

test('renders actual preflight components and independent multi-channel counts', async ({ page }) => {
  await mockGeneration(page);
  await page.goto('/#/observe/live-runs');
  await page.getByRole('button', { name: /^Preview/ }).click();
  await page.getByRole('button', { name: /^Configure/ }).click();
  await page.getByRole('button', { name: 'Run Preflight' }).click();
  await expect(page.getByText('syslog_receiver')).toBeVisible();
  await expect(page.getByText('flow_collector')).toBeVisible();
  await page.getByRole('button', { name: /Continue to Run/ }).click();
  await page.getByRole('button', { name: 'Run', exact: true }).click();
  await expect(page.getByText('SYSLOG', { exact: true })).toBeVisible();
  await expect(page.getByText('IPFIX', { exact: true })).toBeVisible();
  await expect(page.getByText('7', { exact: true }).first()).toBeVisible();
  await expect(page.getByText('2', { exact: true }).first()).toBeVisible();
  await expect(page.getByText('DEGRADED', { exact: true }).first()).toBeVisible();
});

test('topology inspector distinguishes native and HEC destination paths', async ({ page }) => {
  await mockGeneration(page);
  await page.goto('/#/generate/scenarios');
  await expect(page.getByText('Native protocol path')).toBeVisible();
  await expect(page.getByText('HEC destination path')).toBeVisible();
  await page.locator('.generation-topology__edge').filter({ hasText: 'native-telemetry' }).evaluate((element) => {
    element.dispatchEvent(new MouseEvent('click', { bubbles: true }));
  });
  await expect(page.getByLabel('Topology technical inspector')).toContainText('TCP / UDP');
});

test('pipeline health consumes component status vocabulary without synthetic cells', async ({ page }) => {
  await page.route('**/api/health/pipelines', (route) => route.fulfill({ json: { components: [
    { component: 'syslog_receiver', state: 'RUNNING', detail: 'Listening for RFC 5424.', channel: 'SYSLOG' },
    { component: 'flow_collector', state: 'DEGRADED', detail: 'Decoder lag detected.', channel: 'IPFIX' },
    { component: 'splunk_hec', state: 'REACHABLE', detail: 'HEC health succeeded.', channel: null },
    { component: 'splunk_search', state: 'NOT_CONFIGURED', detail: 'Search credentials are not configured.', channel: null },
  ] } }));
  await page.route('**/health', (route) => route.fulfill({ json: { status: 'ok' } }));
  await page.goto('/#/observe/pipeline-health');
  await expect(page.getByText('RUNNING')).toBeVisible();
  await expect(page.getByText('REACHABLE')).toBeVisible();
  await expect(page.getByText('NOT CONFIGURED')).toBeVisible();
  await expect(page.getByText('Splunk observed')).toHaveCount(0);
  await expect(page.getByText('HEALTHY')).toHaveCount(0);
});
