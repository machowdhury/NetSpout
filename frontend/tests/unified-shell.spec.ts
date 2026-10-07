import { expect, test } from '@playwright/test';
import { access } from 'node:fs/promises';
import { artifactPath } from './artifact-paths';

const evidence = [
  {
    evidence_id: 'EVID-STANDARD',
    title: 'Open telemetry standard',
    publisher: 'Standards body',
    reference: 'https://example.test/standard',
    provenance: 'STANDARD_DOCUMENTED',
    verification_state: 'VERIFIED',
    notes: 'Defines the native contract.',
  },
  {
    evidence_id: 'EVID-NETSPOUT',
    title: 'NetSpout telemetry contract schema',
    publisher: 'NetSpout',
    reference: 'repo://src/catalog_contracts.py',
    provenance: 'NETSPOUT_SCHEMA',
    verification_state: 'VERIFIED',
    notes: 'Defines NetSpout-owned modeled fields.',
  },
];

const source = {
  source_id: 'openconfig-gnmi-interfaces',
  vendor: 'OpenConfig',
  product: 'gNMI with openconfig-interfaces',
  product_family: 'Model-Driven Telemetry',
  domains: ['netops', 'observability'],
  telemetry_source: 'gNMI Subscribe notifications for interface state',
  applicable_industries: [],
  verification_state: 'PARTIALLY_VERIFIED',
  provenance: ['STANDARD_DOCUMENTED', 'NETSPOUT_SCHEMA', 'MODELED_VALUE'],
  evidence_ids: ['EVID-STANDARD', 'EVID-NETSPOUT'],
  native_contract: {
    contract_id: 'native-openconfig',
    verification_state: 'VERIFIED',
    format: 'gNMI protobuf Notification and Update messages',
    schema: 'openconfig-interfaces YANG',
    transports: [{ protocol: 'gRPC over HTTP/2', default_port: 57400, encoding: 'PROTO' }],
    structural_fields: ['timestamp', 'path', 'typed value'],
    evidence_ids: ['EVID-STANDARD'],
  },
  splunk_contract: {
    contract_id: 'splunk-openconfig',
    verification_state: 'PARTIALLY_VERIFIED',
    input_mechanisms: ['NetSpout direct structured ingestion'],
    integration_ids: ['netspout-direct-structured-ingestion'],
    sourcetypes: [{
      name: 'openconfig:gnmi:telemetry',
      authority: 'NETSPOUT_DEFINED',
      evidence_ids: ['EVID-NETSPOUT'],
    }],
    cim_mappings: [],
    evidence_ids: ['EVID-NETSPOUT'],
  },
  netspout_contract: {
    contract_id: 'netspout-openconfig',
    verification_state: 'PARTIALLY_VERIFIED',
    schema_classification: 'MODELED_VALUE',
    generator: 'netspout_core.gnmi.TelemetrySensorRegistry',
    validator: 'netspout_core.gnmi.audit_sensor_registry',
    transports: ['gNMI STREAM'],
    modeled_fields: ['interface names', 'counter values'],
    structural_fields: ['YANG path', 'typed value'],
    scenario_ids: ['openconfig_mdt_streaming'],
    generation_modes: ['MODE_A', 'MODE_B'],
    runtime_status: 'DEGRADED',
    maturity: 'PARTIAL',
    evidence_ids: ['EVID-NETSPOUT'],
  },
  spl_field_scope: {
    production_fields: ['path', 'timestamp'],
    netspout_only_fields: ['netspout_run_id'],
    portable_spl_status: 'PARTIALLY_VERIFIED',
  },
  known_limitations: ['The sourcetype is NetSpout-defined, not official Splunk naming.'],
};

const researchSource = {
  ...source,
  source_id: 'windows-security-audit-research',
  vendor: 'Microsoft',
  product: 'Windows Security auditing',
  telemetry_source: 'Windows Security Event Log',
  verification_state: 'RESEARCH_REQUIRED',
  provenance: ['RESEARCH_REQUIRED'],
  evidence_ids: [],
  native_contract: { ...source.native_contract, contract_id: 'native-windows', verification_state: 'RESEARCH_REQUIRED', format: 'RESEARCH REQUIRED', schema: null, transports: [], structural_fields: [], evidence_ids: [] },
  splunk_contract: { ...source.splunk_contract, contract_id: 'splunk-windows', verification_state: 'RESEARCH_REQUIRED', input_mechanisms: [], integration_ids: [], sourcetypes: [], evidence_ids: [] },
  netspout_contract: { ...source.netspout_contract, contract_id: 'netspout-windows', verification_state: 'RESEARCH_REQUIRED', generator: null, validator: null, modeled_fields: [], structural_fields: [], scenario_ids: [], generation_modes: [], evidence_ids: [] },
  spl_field_scope: { production_fields: [], netspout_only_fields: [], portable_spl_status: 'RESEARCH_REQUIRED' },
};

const unsupportedSource = {
  ...researchSource,
  source_id: 'supply-chain-platform-unselected',
  vendor: 'Not selected',
  product: 'Supply chain platform',
  verification_state: 'UNSUPPORTED',
  provenance: ['UNSUPPORTED_TELEMETRY'],
  native_contract: { ...researchSource.native_contract, contract_id: 'native-supply', verification_state: 'UNSUPPORTED', format: 'UNSUPPORTED TELEMETRY' },
  splunk_contract: { ...researchSource.splunk_contract, contract_id: 'splunk-supply', verification_state: 'UNSUPPORTED' },
  netspout_contract: { ...researchSource.netspout_contract, contract_id: 'netspout-supply', verification_state: 'UNSUPPORTED' },
  spl_field_scope: { production_fields: [], netspout_only_fields: [], portable_spl_status: 'UNSUPPORTED' },
};

const integrations = [
  {
    integration_id: 'splunk-native-network-input',
    name: 'Splunk TCP/UDP Network Input',
    publisher: 'Splunk',
    integration_type: 'NATIVE_INPUT',
    supported_source_ids: ['openconfig-gnmi-interfaces'],
    splunkbase_id: null,
    verification_state: 'VERIFIED',
    support_state: 'SUPPORTED',
    sourcetypes: [],
    cim_mappings: [],
    netspout_coverage: 'PARTIALLY_VERIFIED',
    evidence_ids: ['EVID-STANDARD'],
    notes: 'A native input, not a Technical Add-on.',
  },
  {
    integration_id: 'splunkbase-cisco-network-data-1467',
    name: 'Add-on for Cisco Network Data',
    publisher: 'Splunkbase community',
    integration_type: 'SPLUNKBASE_ADD_ON',
    supported_source_ids: ['openconfig-gnmi-interfaces'],
    splunkbase_id: '1467',
    verification_state: 'VERIFIED',
    support_state: 'DEPRECATED',
    sourcetypes: [{ name: 'cisco:ios', authority: 'SPLUNK_DOCUMENTED', evidence_ids: ['EVID-STANDARD'] }],
    cim_mappings: [],
    netspout_coverage: 'PARTIALLY_VERIFIED',
    evidence_ids: ['EVID-STANDARD'],
    notes: 'Deprecated in favor of a newer separately cataloged app.',
  },
  {
    integration_id: 'netspout-direct-structured-ingestion',
    name: 'NetSpout direct structured ingestion',
    publisher: 'NetSpout',
    integration_type: 'DIRECT_STRUCTURED_INGESTION',
    supported_source_ids: ['openconfig-gnmi-interfaces'],
    splunkbase_id: null,
    verification_state: 'PARTIALLY_VERIFIED',
    support_state: 'LAB_ONLY',
    sourcetypes: [{ name: 'openconfig:gnmi:telemetry', authority: 'NETSPOUT_DEFINED', evidence_ids: ['EVID-NETSPOUT'] }],
    cim_mappings: [],
    netspout_coverage: 'PARTIALLY_VERIFIED',
    evidence_ids: ['EVID-NETSPOUT'],
    notes: 'NetSpout-defined lab ingestion; not an official Technical Add-on.',
  },
  {
    integration_id: 'unresearched-integration',
    name: 'Unresearched integration',
    publisher: 'Unknown',
    integration_type: 'COLLECTOR',
    supported_source_ids: [],
    splunkbase_id: null,
    verification_state: 'RESEARCH_REQUIRED',
    support_state: 'UNSUPPORTED',
    sourcetypes: [],
    cim_mappings: [],
    netspout_coverage: 'RESEARCH_REQUIRED',
    evidence_ids: [],
    notes: 'No integration evidence has been promoted.',
  },
];

test.beforeEach(async ({ page }) => {
  await page.route('**/health', async (route) => {
    await route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify({ status: 'ok', service: 'netspout-simulation-engine' }),
    });
  });

  await page.route('**/api/health/pipelines', async (route) => {
    await route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify({
        components: [
          { component: 'syslog_receiver', state: 'RUNNING', detail: 'Receiver is listening.', channel: 'SYSLOG' },
          { component: 'gnmi_subscriber', state: 'NOT_CONFIGURED', detail: 'Subscriber is not configured.', channel: 'GNMI' },
          { component: 'splunk_hec', state: 'REACHABLE', detail: 'HEC health succeeded.', channel: null },
        ],
      }),
    });
  });

  const catalogResponses: Record<string, unknown> = {
    '/api/catalog/sources': [source, researchSource, unsupportedSource],
    '/api/catalog/integrations': integrations,
    '/api/catalog/evidence': evidence,
    '/api/catalog/summary': {
      schema_version: '1.0.0',
      catalog_version: '2026.10-phase2-test',
      source_count: 3,
      integration_count: 4,
      evidence_count: 2,
      source_manifest_count: 1,
      verification_counts: { PARTIALLY_VERIFIED: 1, RESEARCH_REQUIRED: 1, UNSUPPORTED: 1 },
      provenance_counts: {},
      domain_counts: {},
      sourcetype_counts: { NETSPOUT_DEFINED: 1 },
    },
  };

  if (process.env.PLAYWRIGHT_LIVE_CATALOG !== '1') {
    for (const [endpoint, body] of Object.entries(catalogResponses)) {
      await page.route(`**${endpoint}`, async (route) => {
        await route.fulfill({ contentType: 'application/json', body: JSON.stringify(body) });
      });
    }
  }
});

test('supports navigation, domains, and experience modes', async ({ page }) => {
  await page.goto('/#/');

  await expect(page.getByRole('heading', { name: 'Overview', exact: true })).toBeVisible();
  await expect(page.getByText('Unified Enterprise Telemetry Lab').first()).toBeVisible();

  for (const domain of [
    'NetOps',
    'SecOps',
    'ITOps',
    'Observability',
    'Agentic AI',
    'Supply Chain',
  ]) {
    await expect(page.getByRole('button', { name: new RegExp(domain) })).toBeVisible();
  }

  await page.getByRole('button', { name: /SecOps/ }).click();
  await expect(page.getByText('Current perspective').locator('..')).toContainText('SecOps');

  await expect(page.getByRole('button', { name: 'Scenario Builder' })).toHaveCount(0);
  await page.getByRole('button', { name: 'Advanced', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Scenario Builder' })).toBeVisible();

  await page.locator('.app-nav').getByRole('button', { name: 'Quick Generate', exact: true }).click();
  await expect(page).toHaveURL(/#\/generate\/quick$/);
  await expect(page.getByRole('heading', { name: 'Quick Generate', exact: true })).toBeVisible();

  await page.getByRole('button', { name: /Telemetry Explorer/ }).click();
  await expect(page).toHaveURL(/#\/observe\/telemetry$/);
  await expect(page.getByText('PLANNED').first()).toBeVisible();
});

test('renders responsive navigation without replacing Phase 1 evidence', async ({ page }) => {
  await page.goto('/#/');
  await page.setViewportSize({ width: 1440, height: 1000 });

  const phaseOneEvidence = artifactPath(
    'unified-shell',
    'phase1-unified-shell.png',
  );
  await access(phaseOneEvidence).catch(async () => {
    await page.screenshot({ path: phaseOneEvidence, fullPage: true });
  });

  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByRole('button', { name: 'Open navigation' }).click();
  await expect(page.getByRole('dialog', { name: 'Navigation' })).toBeVisible();
  await page.getByRole('button', { name: 'Pipeline Health' }).click();
  await expect(page).toHaveURL(/#\/observe\/pipeline-health$/);
  await expect(page.locator('h1', { hasText: 'Pipeline Health' })).toBeVisible();
});

test('renders Provenance in simple and advanced modes from catalog APIs', async ({ page }) => {
  await page.goto('/#/catalog/provenance');

  await expect(page.getByRole('heading', { name: 'Telemetry Provenance' })).toBeVisible();
  await expect(page.getByText('What is this', { exact: true })).toBeVisible();
  await expect(page.getByText('What Splunk calls it', { exact: true })).toBeVisible();
  await expect(page.getByText('NETSPOUT-DEFINED', { exact: true })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Native Contract' })).toHaveCount(0);

  await page.getByRole('button', { name: 'Advanced', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Native Contract' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Splunk Contract' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'NetSpout Contract' })).toBeVisible();
  await expect(page.getByText('Production fields', { exact: true })).toBeVisible();
  await expect(page.getByText('NetSpout-only fields', { exact: true })).toBeVisible();

  await page.getByPlaceholder('Search source, vendor, domain…').fill('Windows');
  await page.getByRole('option', { name: /Windows Security auditing/ }).click();
  await expect(page.getByText('RESEARCH REQUIRED').first()).toBeVisible();

  await page.getByPlaceholder('Search source, vendor, domain…').fill('Supply chain');
  await page.getByRole('option', { name: /Supply chain platform/ }).click();
  await expect(page.getByText('UNSUPPORTED').first()).toBeVisible();
});

test('renders classified Splunk integrations and catalog states', async ({ page }) => {
  await page.goto('/#/catalog/splunk-integrations');

  await expect(page.getByRole('heading', { name: 'Splunk Integrations', exact: true, level: 2 })).toBeVisible();
  await expect(page.getByText('Native input', { exact: true })).toBeVisible();
  await expect(page.getByText('Splunkbase add-on', { exact: true })).toBeVisible();
  await expect(page.getByText('DEPRECATED', { exact: true })).toBeVisible();
  await expect(page.getByText('Lab-only direct ingestion', { exact: true })).toBeVisible();
  await expect(page.getByText('NETSPOUT-DEFINED', { exact: true })).toBeVisible();
  await expect(page.getByText('SPLUNK-DOCUMENTED', { exact: true })).toBeVisible();
  await expect(page.getByText('RESEARCH REQUIRED').first()).toBeVisible();
  await expect(page.getByText('UNSUPPORTED').first()).toBeVisible();
  await expect(page.getByText('Splunkbase ID', { exact: true })).toHaveCount(1);
});

test('captures Phase 2 catalog provenance evidence', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto('/#/catalog/provenance');
  await page.getByRole('button', { name: 'Advanced', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Native Contract' })).toBeVisible();

  await page.screenshot({
    path: artifactPath('unified-shell', 'phase2-catalog-provenance.png'),
    fullPage: true,
  });
});
