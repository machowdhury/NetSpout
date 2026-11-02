import { expect, test } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';

const capabilityPath = process.env.NETSPOUT_PHASE9_CAPABILITIES;
const screenshotRoot = process.env.NETSPOUT_SCREENSHOT_ROOT;

test('reviews the actual Phase 9 gallery, detail, topology, and analytics metadata', async ({ page }) => {
  test.skip(!capabilityPath || !screenshotRoot, 'Phase 9 current-run review was not requested.');
  const capabilities = JSON.parse(fs.readFileSync(capabilityPath as string, 'utf8'));
  const scenario = capabilities.scenarios.find(
    (item: { scenario_id: string }) => item.scenario_id === 'SEC-P9-F-CROSS-SOURCE',
  );
  const sources = capabilities.sources.filter(
    (item: { source_id: string }) => scenario.source_ids.includes(item.source_id),
  );
  const investigations = capabilities.investigations.filter(
    (item: { recipe_id: string }) => scenario.investigation_recipe_ids.includes(item.recipe_id),
  );
  const preview = {
    mode: 'SCENARIO',
    selection_id: scenario.scenario_id,
    scenario,
    sources,
    bindings: [],
    integration_readiness: capabilities.integration_recommendations.filter(
      (item: { recommendation_id: string }) =>
        scenario.integration_recommendation_ids.includes(item.recommendation_id),
    ),
    investigations,
    raw_preview: [],
    preview_notice: 'Native binary telemetry is produced only during execution.',
    native_contract: sources[0].native_contract,
    splunk_contract: sources[0].splunk_contract,
    netspout_contract: sources[0].netspout_contract,
    known_limitations: sources.flatMap((item: { known_limitations: string[] }) => item.known_limitations),
  };
  await page.route('**/api/generation/capabilities', (route) => route.fulfill({ json: capabilities }));
  await page.route('**/api/generation/preview', (route) => route.fulfill({ json: preview }));
  await page.setViewportSize({ width: 1600, height: 1050 });
  await page.goto('/#/generate/scenarios');

  const output = screenshotRoot as string;
  fs.mkdirSync(output, { recursive: true });
  const capture = (name: string) => page.screenshot({
    path: path.join(output, name),
    fullPage: true,
  });

  await page.getByLabel('Choose guided scenario').selectOption(scenario.scenario_id);
  await expect(page.getByRole('heading', { name: scenario.title })).toBeVisible();
  await capture('01-security-scenario-gallery-and-detail.png');
  await page.getByTestId('scenario-topology').screenshot({
    path: path.join(output, '02-cross-source-topology.png'),
  });

  await page.getByRole('button', { name: 'Start guided lab' }).click();
  await expect(page.getByLabel('Security behavior progression')).toContainText(
    'SUSPICIOUS ACTIVITY',
  );
  await expect(page.getByText('Evidence-gated analytics')).toBeVisible();
  await capture('03-security-understand-baseline-incident.png');
  await page.getByRole('button', { name: 'Incident Lens' }).click();
  await capture('04-security-incident-lens.png');
  await page.getByRole('button', { name: 'Splunk Lens' }).click();
  await capture('05-security-evidence-paths.png');
});
