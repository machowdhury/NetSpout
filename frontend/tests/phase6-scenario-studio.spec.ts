import { expect, test, type Page, type Route } from '@playwright/test';
import { artifactPath } from './artifact-paths';

const image = (name: string) =>
  artifactPath('phase6-scenario-studio', `phase6-${name}.png`);

const source = {
  source_id: 'ietf-syslog-rfc5424',
  vendor: 'IETF',
  product: 'RFC 5424',
  product_family: 'Syslog',
  domains: ['netops'],
  telemetry_source: 'RFC 5424 structured syslog',
  applicable_industries: [],
  verification_state: 'VERIFIED',
  provenance: ['STANDARD_DOCUMENTED'],
  evidence_ids: ['rfc5424'],
  native_contract: { contract_id: 'native-rfc5424', verification_state: 'VERIFIED', format: 'RFC5424', transports: [], structural_fields: ['version'], evidence_ids: ['rfc5424'] },
  splunk_contract: { contract_id: 'splunk-rfc5424', verification_state: 'PARTIALLY_VERIFIED', input_mechanisms: ['UDP'], integration_ids: [], sourcetypes: [{ name: 'netspout:rfc5424', authority: 'NETSPOUT_DEFINED', evidence_ids: [] }], cim_mappings: [], evidence_ids: [] },
  netspout_contract: { contract_id: 'netspout-rfc5424', verification_state: 'VERIFIED', schema_classification: 'MODELED_VALUE', generator: 'fixture', validator: 'fixture', transports: ['UDP'], modeled_fields: ['interface.status'], structural_fields: ['version'], scenario_ids: ['golden-link'], generation_modes: ['MODE_A'], runtime_status: 'AVAILABLE', maturity: 'BETA', evidence_ids: [] },
  spl_field_scope: { production_fields: [], netspout_only_fields: ['netspout_run_id'], portable_spl_status: 'PARTIALLY_VERIFIED' },
  known_limitations: [],
  generation: { runnable: true, state: 'READY', reason: 'Validated binding.' },
};

const goldenScenario = {
  scenario_id: 'golden-link',
  title: 'Golden Link Degradation',
  description: 'A verified link lifecycle.',
  story: 'One link degrades and recovers.',
  difficulty: 'INTERMEDIATE',
  expected_duration_minutes: 10,
  learning_objectives: [],
  business_impact: 'Branch connectivity degrades.',
  prerequisites: [],
  technology_ids: ['router'],
  source_ids: [source.source_id],
  entities: ['router-01.example'],
  zones: [{ zone_id: 'lab', label: 'Private Lab' }],
  nodes: [{ node_id: 'router-01.example', entity_id: 'router-01.example', technology_id: 'router', zone_id: 'lab', role: 'router', source_ids: [source.source_id], label: 'Router 01' }],
  relationships: [],
  telemetry_paths: [],
  incident_path: ['router-01.example'],
  runtime_state_keys: ['interface.status'],
  timeline: [{ step_id: 'incident', stage: 'INCIDENT', description: 'Link down', state_changes: {}, entity_state_changes: { 'router-01.example': 'interface.status=DOWN' }, incident_ids: ['incident'], evidence_source_ids: [source.source_id] }],
  expected_evidence: ['GENERATED'],
  investigation_recipe_ids: [],
  integration_recommendation_ids: [],
  production_replication_guidance: [],
  visualization: { mode: 'AUTOMATIC', direction: 'LEFT_TO_RIGHT', curated_layout_ref: null },
  composition_id: 'compose-golden-link',
  verification_state: 'VERIFIED',
  maturity: 'READY',
  source_count: 1,
  integration_count: 0,
  runnable: true,
};

const draft = {
  pack_id: 'private-phase6-journey',
  scenario_id: 'studio-phase6-journey',
  title: 'Private Phase 6 Journey',
  description: 'A private deterministic Studio scenario.',
  story: 'A fictional router degrades and recovers.',
  creation_path: 'IMPORT_SANITIZED_SAMPLE',
  maturity: 'DRAFT',
  privacy_status: 'SANITIZED',
  provenance: 'LAB SAMPLE — SANITIZED',
  redistribution: 'PRIVATE',
  source_ids: [] as string[],
  custom_sources: [] as unknown[],
  zones: [{ zone_id: 'lab', label: 'Private Lab' }],
  entities: [{ entity_id: 'router-01.example', label: 'Router 01', entity_type: 'router', zone_id: 'lab', attributes: { address: '192.0.2.10' }, x: null, y: null }],
  relationships: [],
  baseline: [{ state_key: 'interface.status', entity_id: 'router-01.example', value: 'UP', unit: null }],
  timeline: [
    { transition_id: 'baseline', stage: 'BASELINE', offset_seconds: 0, title: 'Baseline', state_changes: [{ state_key: 'interface.status', entity_id: 'router-01.example', value: 'UP', unit: null }], source_ids: [] as string[] },
    { transition_id: 'incident', stage: 'INCIDENT', offset_seconds: 300, title: 'Incident', state_changes: [{ state_key: 'interface.status', entity_id: 'router-01.example', value: 'DOWN', unit: null }], source_ids: [] as string[] },
    { transition_id: 'recovery', stage: 'RECOVERY', offset_seconds: 600, title: 'Recovery', state_changes: [{ state_key: 'interface.status', entity_id: 'router-01.example', value: 'UP', unit: null }], source_ids: [] as string[] },
  ],
  parameters: [],
  correlation_mappings: [],
  investigations: [],
  contract_fingerprints: {},
  layout_hints: {},
  cloned_from_scenario_id: null,
  created_at: null,
  updated_at: null,
};

const fields = [
  { name: 'event_type', data_type: 'str', classification: 'STRUCTURAL', authority: 'INFERRED', description: '', enum_values: ['interface_health'], numeric_min: null, numeric_max: null },
  { name: 'device', data_type: 'str', classification: 'MODELED', authority: 'INFERRED', description: '', enum_values: ['router-01.example'], numeric_min: null, numeric_max: null },
  { name: 'loss_pct', data_type: 'float', classification: 'MODELED', authority: 'INFERRED', description: '', enum_values: [], numeric_min: 0.1, numeric_max: 8 },
  { name: 'session_id', data_type: 'str', classification: 'CORRELATION', authority: 'INFERRED', description: '', enum_values: ['session-test-01'], numeric_min: null, numeric_max: null },
];

async function mockStudio(page: Page) {
  let saved: Record<string, unknown> | null = null;
  await page.route('**/api/studio**', async (route: Route) => {
    const request = route.request();
    const url = new URL(request.url());
    const body = request.method() === 'POST' ? request.postDataJSON() : null;
    if (url.pathname === '/api/studio' && request.method() === 'GET') {
      return route.fulfill({ json: {
        creation_paths: [
          { id: 'EXISTING_SOURCES', title: 'Use Existing Sources', description: 'Build from the verified NetSpout catalog.' },
          { id: 'IMPORT_SANITIZED_SAMPLE', title: 'Import Sanitized Sample', description: 'Create a private custom source.' },
          { id: 'CLONE_SCENARIO', title: 'Clone Existing Scenario', description: 'Preserve contracts and edit modeled state.' },
        ],
        import_notice: 'Import only telemetry you are authorized to use. Remove credentials, secrets, customer identifiers and personal information before importing.',
        sources: [source],
        scenarios: [goldenScenario],
        private_packs: saved ? [{ pack_id: draft.pack_id, scenario_id: draft.scenario_id, title: String(saved.title), maturity: 'STRUCTURE VALIDATED', privacy_status: 'SANITIZED', provenance: 'LAB SAMPLE — SANITIZED', redistribution: 'PRIVATE', source_count: 1, custom_source_count: 1, updated_at: '2026-10-06T18:00:00Z' }] : [],
      } });
    }
    if (url.pathname.endsWith('/samples/analyze')) {
      const blocked = String(body.sample).includes('password');
      return route.fulfill({ json: blocked ? {
        sample_fingerprint: 'blocked-test-fingerprint',
        blocked: true,
        privacy_status: 'FINDINGS_REQUIRE_REVIEW',
        findings: [{ category: 'CREDENTIAL', location: 'line 1', redacted_preview: 'credential-like value: [REDACTED]', severity: 'CRITICAL', fingerprint: 'finding-test-01' }],
        format: 'LOGFMT', record_count: 1, fields: [], record_boundary: 'newline', notes: ['Local only.'],
      } : {
        sample_fingerprint: 'clean-test-fingerprint',
        blocked: false,
        privacy_status: 'SANITIZED',
        findings: [],
        format: 'JSON',
        record_count: 1,
        fields,
        record_boundary: 'single JSON object',
        notes: ['Suggested classifications are not vendor verification.'],
      } });
    }
    if (url.pathname.endsWith('/custom-sources/validate')) {
      return route.fulfill({ json: { valid: true, errors: [], privacy_status: 'SANITIZED', native_contract: {}, splunk_contract: {}, netspout_contract: {} } });
    }
    if (url.pathname.endsWith('/drafts')) {
      return route.fulfill({ json: { ...draft, creation_path: body.creation_path, title: body.title } });
    }
    if (url.pathname.endsWith('/packs/validate')) {
      return route.fulfill({ json: { valid: true, maturity_ceiling: 'STRUCTURE VALIDATED', checks: [
        { check_id: 'contracts', state: 'PASS', detail: 'Structural contracts remain immutable.' },
        { check_id: 'privacy', state: 'PASS', detail: 'Approved sanitized input only.' },
        { check_id: 'runtime', state: 'PASS', detail: 'Generator and transport are available.' },
      ], errors: [], warnings: ['Draft is private and not production verified.'] } });
    }
    if (url.pathname === '/api/studio/packs' && request.method() === 'POST') {
      saved = { ...body, maturity: 'STRUCTURE VALIDATED', created_at: '2026-10-06T18:00:00Z', updated_at: '2026-10-06T18:00:00Z' };
      return route.fulfill({ json: saved });
    }
    if (url.pathname.startsWith('/api/studio/packs/') && request.method() === 'GET' && saved) {
      return route.fulfill({ json: saved });
    }
    if (url.pathname.endsWith('/run')) {
      return route.fulfill({ json: {
        run_id: 'phase6-studio-run', mode: 'SCENARIO', selection_id: draft.scenario_id,
        scenario_id: draft.scenario_id, source_ids: ['private-synthetic-source'],
        generator_ids: ['generator-private-synthetic-source-private-template'],
        transport_id: 'transport-private-synthetic-source-private-hec',
        destination_id: 'destination-private-synthetic-source-private-splunk',
        started_at: '2026-10-06T18:00:00Z', completed_at: '2026-10-06T18:00:01Z',
        current_phase: 'RECOVERY', status: 'COMPLETED',
        events: [{ event_id: 'event-test-01', source_id: 'private-synthetic-source', contract_id: 'native-private-synthetic-source', provenance: ['RESEARCH_REQUIRED', 'MODELED_VALUE', 'PRIVATE_LOCAL'], transport_id: 'transport-private-synthetic-source-private-hec', sourcetype: 'netspout:custom:synthetic', sourcetype_authority: 'NETSPOUT_DEFINED', phase: 'INCIDENT', raw: '{"device":"router-01.example","loss_pct":8,"netspout_run_id":"phase6-studio-run"}' }],
        evidence: [{ stage: 'GENERATED', state: 'PROVEN', count: 3, detail: 'Generated from reviewed private template.' }, { stage: 'SPLUNK_OBSERVED', state: 'PENDING', count: 0, detail: 'Authenticated observation not run in fixture.' }],
        channel_results: [], validation: [], integration_readiness: [], investigations: [], limitations: ['No CIM mapping is claimed.'],
      } });
    }
    return route.fulfill({ status: 404, json: { detail: 'Unmocked Studio route' } });
  });
  await page.route('**/health', (route) => route.fulfill({ json: { status: 'ok' } }));
}

test('captures the complete safe Scenario Studio authoring journey', async ({ page }) => {
  test.setTimeout(120_000);
  await mockStudio(page);
  await page.goto('/#/build/studio');
  await expect(page.getByTestId('studio-home')).toBeVisible();
  await page.screenshot({ path: image('01-studio-home'), fullPage: true });

  await page.getByTestId('studio-path-existing_sources').click();
  await page.screenshot({ path: image('02-existing-source-selection'), fullPage: true });
  await page.getByRole('button', { name: /Studio Home/ }).click();

  await page.getByTestId('studio-path-clone_scenario').click();
  await page.screenshot({ path: image('03-clone-scenario'), fullPage: true });
  await page.getByRole('button', { name: /Studio Home/ }).click();

  await page.getByTestId('studio-path-import_sanitized_sample').click();
  await page.screenshot({ path: image('04-import-sample'), fullPage: true });
  await page.getByLabel('Sanitized telemetry sample').fill('username=test-user password=TEST_ONLY_NOT_A_SECRET');
  await page.getByLabel(/I am authorized/).check();
  await page.getByRole('button', { name: /Analyze Locally/ }).click();
  await expect(page.getByTestId('studio-sensitive-warning')).toBeVisible();
  await page.getByTestId('studio-sensitive-warning').scrollIntoViewIfNeeded();
  await page.screenshot({ path: image('05-sensitive-data-warning'), fullPage: true });
  await expect(page.getByTestId('studio-sensitive-warning')).not.toContainText('TEST_ONLY_NOT_A_SECRET');

  await page.getByLabel('Sanitized telemetry sample').fill('{"event_type":"interface_health","device":"router-01.example","loss_pct":8,"session_id":"session-test-01"}');
  await page.getByRole('button', { name: /Analyze Locally/ }).click();
  await expect(page.getByTestId('studio-field-classification')).toBeVisible();
  await page.screenshot({ path: image('06-field-classification'), fullPage: true });
  await page.screenshot({ path: image('07-contract-builder'), fullPage: true });

  await page.getByRole('button', { name: /Approve Sanitized Contract/ }).click();
  await expect(page.getByTestId('studio-environment-builder')).toBeVisible();
  await page.screenshot({ path: image('08-environment-builder'), fullPage: true });

  const steps = [
    ['Topology', '09-topology-builder'],
    ['State', '10-state-builder'],
    ['Timeline', '11-timeline-builder'],
    ['Telemetry', '12-telemetry-configuration'],
    ['Parameters', '13-scenario-parameters'],
    ['Investigation', '14-investigation-builder'],
    ['Preview', '15-preview'],
  ] as const;
  for (const [label, filename] of steps) {
    await page
      .getByLabel('Scenario Studio steps')
      .getByRole('button', { name: new RegExp(`${label}$`, 'i') })
      .click();
    await page.screenshot({ path: image(filename), fullPage: true });
  }
  await page.getByRole('heading', { name: 'Guided Lab Preview' }).scrollIntoViewIfNeeded();
  await page.screenshot({ path: image('16-guided-lab-preview'), fullPage: true });

  await page.getByRole('button', { name: /Validate Draft/ }).click();
  await expect(page.getByText('Structural contracts remain immutable.')).toBeVisible();
  await page.screenshot({ path: image('17-validation'), fullPage: true });
  await page.getByRole('button', { name: /Save as Private Pack/ }).click();
  await expect(page.getByRole('heading', { name: 'Saved locally' })).toBeVisible();
  await page.screenshot({ path: image('18-save-private-pack'), fullPage: true });

  await page.getByRole('button', { name: /Run Draft Scenario/ }).click();
  await expect(page.getByText('phase6-studio-run')).toBeVisible();
  await page.screenshot({ path: image('19-custom-live-run'), fullPage: true });
  await expect(page.getByText('Splunk validation')).toBeVisible();
  await page.getByText('Splunk validation').scrollIntoViewIfNeeded();
  await page.screenshot({ path: image('20-splunk-validation'), fullPage: true });

  await page.getByRole('button', { name: /Studio Home/ }).click();
  await page.getByRole('button', { name: /Private Custom Telemetry/ }).click();
  await expect(page.getByRole('heading', { name: 'Private Custom Telemetry' })).toBeVisible();
});

test('creates from a catalog source and clones without exposing contract edits', async ({ page }) => {
  await mockStudio(page);
  await page.goto('/#/build/studio');
  await page.getByTestId('studio-path-existing_sources').click();
  await page.getByText('RFC 5424', { exact: true }).click();
  await page.getByRole('button', { name: /Build Environment/ }).click();
  await expect(page.getByTestId('studio-environment-builder')).toBeVisible();
  await expect(page.getByText('contracts remain immutable')).toBeVisible();

  await page.getByRole('button', { name: /Studio Home/ }).click();
  await page.getByTestId('studio-path-clone_scenario').click();
  await page.getByRole('button', { name: /Golden Link Degradation/ }).click();
  await expect(page.getByTestId('studio-environment-builder')).toBeVisible();
  await expect(page.getByLabel('Entity identity')).toHaveAttribute('readonly', '');
});

test('preserves unknown provenance and renders fail-closed validation', async ({ page }) => {
  await mockStudio(page);
  await page.route('**/api/studio/packs/validate', (route) => route.fulfill({ json: {
    valid: false,
    maturity_ceiling: 'DRAFT',
    checks: [{ check_id: 'transport', state: 'FAIL', detail: 'Unsupported transport is blocked.' }],
    errors: ['Unsupported transport is blocked.'],
    warnings: [],
  } }));
  await page.goto('/#/build/studio');
  await page.getByTestId('studio-path-import_sanitized_sample').click();
  await page.getByLabel('Sanitized telemetry sample').fill('{"event_type":"interface_health","device":"router-01.example","loss_pct":8}');
  await page.getByLabel(/I am authorized/).check();
  await page.getByRole('button', { name: /Analyze Locally/ }).click();
  await page.getByLabel('Provenance').selectOption('UNKNOWN ORIGIN');
  await page.getByRole('button', { name: /Approve Sanitized Contract/ }).click();
  await page.getByLabel('Scenario Studio steps').getByRole('button', { name: /Preview$/i }).click();
  await expect(page.getByText('UNKNOWN ORIGIN')).toBeVisible();
  await page.getByRole('button', { name: /Validate Draft/ }).click();
  await expect(page.getByText('Unsupported transport is blocked.').first()).toBeVisible();
  await expect(page.getByRole('button', { name: /Save as Private Pack/ })).toBeDisabled();
});
