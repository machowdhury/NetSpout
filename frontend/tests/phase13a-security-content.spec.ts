import { expect, test } from '@playwright/test';

const detection = {
  catalog_key: 'detection:test:detections/network/test.yml',
  content_id: 'test-detection-id',
  name: 'Reviewed Network Detection',
  description: 'Detects a bounded network test condition.',
  category: 'network',
  security_domain: 'network',
  detection_type: 'TTP',
  status: 'production',
  version: 1,
  analytic_stories: ['Browser Fixture Story'],
  mitre_attack_ids: ['T1190'],
  data_source_names: ['Cisco Secure Firewall'],
  products: ['Splunk Enterprise'],
  repository_commit: 'security-content-test-sha',
  file_path: 'detections/network/test.yml',
  compatibility: {
    status: 'REQUIRES_TRANSFORMATION',
    matched_netspout_sources: [],
    missing_macros: [],
    missing_lookups: [],
    reasons: ['Curated replay exists; native source support is not established.'],
    structural_compatibility: false,
    runtime_compatibility: 'NOT_TESTED',
    splunk_compatibility: 'NOT_TESTED',
    detection_validation: 'NOT_TESTED',
    production_detection_efficacy: 'NOT_ESTABLISHED',
  },
  has_attack_data: true,
};

test.beforeEach(async ({ page }) => {
  await page.route('**/api/telemetry/config', (route) => route.fulfill({ json: {} }));
  await page.route('**/api/security-content/summary', (route) => route.fulfill({ json: {
    detections: 2181,
    analytic_stories: 365,
    attack_dataset_manifests: 1400,
    attack_dataset_files: 1474,
    dependencies_resolved: 2024,
    duplicate_ids: 23,
    parse_failures: 0,
    compatibility_counts: { REQUIRES_TRANSFORMATION: 1, RESEARCH_REQUIRED: 157 },
    upstreams: {
      security_content: { commit: 'security-content-test-sha', branch: 'develop' },
      attack_data: { commit: 'attack-data-test-sha', branch: 'master' },
    },
  } }));
  await page.route('**/api/security-content/detections?**', (route) => route.fulfill({
    json: { total: 1, offset: 0, limit: 200, items: [detection] },
  }));
  await page.route('**/api/security-content/detections/detection%3Atest%3Adetections%2Fnetwork%2Ftest.yml', (route) => route.fulfill({
    json: {
      ...detection,
      author: 'Fixture Author',
      how_to_implement: 'Use the reviewed fixture.',
      known_false_positives: 'None in fixture.',
      spl: 'search index=test earliest=-15m latest=now',
      dependencies: {
        resolution: 'RESOLVED',
        indexes: [],
        sourcetypes: ['cisco:sfw:estreamer'],
        required_fields: ['signature_id'],
        data_models: [],
        macros: [],
        lookups: [],
        technology_add_ons: ['Cisco Security Cloud'],
        search_commands: ['search'],
        unresolved_reasons: [],
        parser_scope: 'Conservative fixture parsing.',
      },
      attack_data: [{ url: 'https://example.invalid/test.log' }],
      production_detection_efficacy: 'NOT_ESTABLISHED',
    },
  }));
  await page.route('**/api/security-content/datasets?**', (route) => route.fulfill({ json: [] }));
  await page.route('**/api/security-content/stories?**', (route) => route.fulfill({ json: [] }));
  await page.route('**/api/security-content/mitre', (route) => route.fulfill({ json: [{
    technique: 'T1190',
    name: 'Exploit Public-Facing Application',
    tactics: ['initial-access'],
    detections: 1,
    telemetry_available: 1,
    test_data_available: 1,
    detection_validated: 0,
  }] }));
  await page.route('**/api/security-content/validations', (route) => route.fulfill({ json: [] }));
});

test('Security Content Lab explains compatibility without efficacy claims', async ({ page }) => {
  await page.goto('/#/security-content');
  await expect(page.getByRole('heading', { name: 'Splunk Detection Compatibility' })).toBeVisible();
  await page.getByRole('button', { name: 'Reviewed Network Detection' }).click();
  await expect(page.getByText('cisco:sfw:estreamer')).toBeVisible();
  await expect(page.getByText(/Production efficacy: NOT_ESTABLISHED/)).toBeVisible();
  await page.getByRole('button', { name: 'MITRE Coverage' }).click();
  await expect(page.getByLabel('MITRE ATT&CK coverage')).toBeVisible();
});
