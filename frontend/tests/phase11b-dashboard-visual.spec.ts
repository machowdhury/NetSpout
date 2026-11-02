import { expect, test } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';
import { artifactPath, testArtifactRoot } from './artifact-paths';

type RuntimeResult = {
  run_id: string;
  all_required_splunk_observed: boolean;
  required_sources?: Array<{ source_id: string; splunk_observed: boolean }>;
};

type DashboardResult = {
  dashboard_id: string;
  scenario_id: string;
  runtime_scenario_id: string;
  run_id: string;
  export_valid: boolean;
};

type LiveMatrix = {
  runtime_scenarios: Record<string, RuntimeResult>;
  dashboards: DashboardResult[];
};

const liveEnabled = process.env.NETSPOUT_PHASE11B_LIVE === '1';
const matrixPath =
  process.env.NETSPOUT_PHASE11B_MATRIX ??
  path.resolve(process.cwd(), '..', '.artifacts/phase11b/live/phase11-dashboard-live-validation.json');
const matrix = liveEnabled
  ? (JSON.parse(fs.readFileSync(matrixPath, 'utf8')) as LiveMatrix)
  : ({ runtime_scenarios: {}, dashboards: [] } as LiveMatrix);

test.describe('Phase 11B live visual acceptance', () => {
  test.skip(!liveEnabled, 'requires fresh Phase 11B live evidence and the real API');
  test.describe.configure({ mode: 'serial' });

  test('renders and captures every eligible dashboard in all perspectives', async ({ page }) => {
    test.setTimeout(240_000);
    expect(matrix.dashboards).toHaveLength(14);
    await page.setViewportSize({ width: 1440, height: 900 });

    const results: Array<Record<string, unknown>> = [];
    for (const dashboard of matrix.dashboards) {
      await page.goto(
        `/?dashboard=${encodeURIComponent(dashboard.dashboard_id)}&run=${encodeURIComponent(dashboard.run_id)}#/observe/dashboards`,
      );
      await expect(page.getByTestId('dashboard-studio')).toBeVisible();
      await expect(page.getByLabel('Run context')).toHaveValue(dashboard.run_id);
      await expect(page.getByText(dashboard.scenario_id, { exact: false }).first()).toBeVisible();
      await expect(page.getByTestId('dashboard-topology')).toBeVisible();
      await expect(page.locator('.dashboard-panel').first()).toBeVisible();

      const slug = dashboard.dashboard_id.toLowerCase().replace(/[^a-z0-9]+/g, '-');
      const sourceCoverage =
        matrix.runtime_scenarios[dashboard.runtime_scenario_id]?.all_required_splunk_observed;
      if (sourceCoverage === false) {
        await expect(page.getByTestId('dashboard-source-limitation')).toBeVisible();
      } else {
        await expect(page.getByTestId('dashboard-source-limitation')).toHaveCount(0);
      }

      for (const perspective of ['NOC', 'ENGINEER', 'EVIDENCE'] as const) {
        if (perspective !== 'NOC') {
          await page.getByRole('tab', { name: perspective }).click({ force: true });
        }
        await expect(page.locator('.dashboard-panel').first()).toBeVisible();
        await page.screenshot({
          path: artifactPath('phase11b-dashboard', `${slug}-${perspective.toLowerCase()}-1440.png`),
          fullPage: true,
        });
      }
      const enabledDrilldown = page
        .locator('.dashboard-panel__drilldowns button:not(:disabled)')
        .first();
      await expect(enabledDrilldown).toBeVisible();
      await enabledDrilldown.click();
      await expect(page.locator('.dashboard-tokenbar button').first()).toBeVisible();
      await page.getByRole('button', { name: 'Clear filters' }).click();
      await page.getByRole('button', { name: 'Inspect' }).first().click();
      const inspector = page.getByLabel('Advanced Inspector');
      await expect(inspector).toBeVisible();
      await page.getByRole('button', { name: 'Validation', exact: true }).click();
      await expect(inspector).toContainText('Dashboard maturity');
      await page.getByRole('button', { name: 'Dependencies', exact: true }).click();
      await expect(inspector).not.toContainText('DEPENDENCY_BLOCKED');
      await page.getByLabel('Close inspector').click();
      results.push({
        dashboard_id: dashboard.dashboard_id,
        scenario_id: dashboard.scenario_id,
        run_id: dashboard.run_id,
        source_coverage_validated: sourceCoverage,
        browser_rendered: true,
        scenario_run_binding: true,
        perspectives: ['NOC', 'ENGINEER', 'EVIDENCE'],
      });
    }

    const output = path.join(testArtifactRoot(), 'phase11b-visual-browser-matrix.json');
    fs.mkdirSync(path.dirname(output), { recursive: true });
    fs.writeFileSync(output, `${JSON.stringify(results, null, 2)}\n`, 'utf8');
  });

  test('replaces scenario context and validates interactions without stale state', async ({ page }) => {
    test.setTimeout(120_000);
    const sequence = [
      'scenario-c100-ent-001',
      'scenario-sec-p9-b-dns-anomaly',
      'industry-healthcare',
    ].map((id) => matrix.dashboards.find((item) => item.dashboard_id === id)!);

    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto(
      `/?dashboard=${sequence[0].dashboard_id}&run=${sequence[0].run_id}#/observe/dashboards`,
    );
    await expect(page.getByLabel('Run context')).toHaveValue(sequence[0].run_id);
    await page.getByRole('tab', { name: 'ENGINEER' }).click();
    await page.getByRole('button', { name: 'Inspect' }).first().click();
    await expect(page.getByLabel('Advanced Inspector')).toBeVisible();
    await page.getByRole('button', { name: 'SPL', exact: true }).click();
    await expect(page.locator('.dashboard-inspector pre')).toContainText(sequence[0].run_id);
    await page.getByLabel('Close inspector').click();
    const drilldown = page.locator('.dashboard-panel__drilldowns button:not(:disabled)').first();
    if (await drilldown.count()) {
      await drilldown.click();
      await expect(page.locator('.dashboard-tokenbar button').first()).toBeVisible();
    }

    for (const next of sequence.slice(1)) {
      await page.getByLabel('Switch scenario dashboard').selectOption(next.dashboard_id);
      await page.getByLabel('Run context').fill(next.run_id);
      await expect(page).toHaveURL(new RegExp(`dashboard=${next.dashboard_id}`));
      await expect(page.getByLabel('Run context')).toHaveValue(next.run_id);
      await expect(page.getByText(next.scenario_id, { exact: false }).first()).toBeVisible();
      await expect(page.locator('.dashboard-tokenbar')).toContainText('Full scenario');
      await expect(page.getByRole('tab', { name: 'NOC' })).toHaveAttribute('aria-selected', 'true');
    }

    await page.getByRole('button', { name: 'Export / Deploy' }).click();
    const dialog = page.getByRole('dialog', { name: 'Dashboard export and deployment preview' });
    await expect(dialog).toContainText('VALID');
    await expect(dialog).toContainText(sequence[2].scenario_id);
    await page.screenshot({
      path: artifactPath('phase11b-dashboard', 'scenario-switching-export-preview.png'),
      fullPage: true,
    });
    await page.getByLabel('Close export preview').click();

    await page.getByRole('button', { name: 'NOC wallboard' }).click();
    await expect(page.getByRole('button', { name: 'Exit wallboard' })).toBeVisible();
    await expect(page.getByText(sequence[2].scenario_id, { exact: false }).first()).toBeVisible();
    await page.screenshot({
      path: artifactPath('phase11b-dashboard', 'healthcare-wallboard.png'),
      fullPage: true,
    });
  });

  test('renders research-required and dependency fallback states', async ({ page }) => {
    const catalog = await (await page.request.get('/api/dashboards')).json();
    await page.goto('/#/observe/dashboards');
    await expect(page.getByRole('heading', { name: 'Dashboard Gallery' })).toBeVisible();
    await expect(page.locator('.dashboard-card')).toHaveCount(catalog.dashboards.length);
    await expect(
      page.getByRole('region', { name: 'Golden Cisco references' }).getByRole('button'),
    ).toHaveCount(5);
    await page.screenshot({
      path: artifactPath('phase11b-dashboard', 'dashboard-gallery.png'),
      fullPage: true,
    });
    const research = catalog.dashboards.find(
      (item: { state: string }) => item.state === 'RESEARCH_REQUIRED',
    );
    expect(research).toBeTruthy();
    await page.goto(`/?dashboard=${research.dashboard_id}#/observe/dashboards`);
    await expect(page.getByTestId('dashboard-research-required')).toBeVisible();
    await expect(page.getByTestId('dashboard-research-required')).toContainText('No fallback event');
    await page.screenshot({
      path: artifactPath('phase11b-dashboard', 'research-required.png'),
      fullPage: true,
    });

    const dashboard = matrix.dashboards[0];
    await page.goto(
      `/?dashboard=${dashboard.dashboard_id}&run=${dashboard.run_id}#/observe/dashboards`,
    );
    await page.getByRole('button', { name: 'Inspect' }).first().click();
    await page.getByRole('button', { name: 'Dependencies', exact: true }).click();
    const dependencyInspector = page.getByLabel('Advanced Inspector');
    await expect(dependencyInspector).toContainText('Unavailable optional visualizations');
    await expect(dependencyInspector).toContainText('NOT VERIFIED');
    await expect(dependencyInspector).toContainText(/fallback/i);
    await page.screenshot({
      path: artifactPath('phase11b-dashboard', 'visualization-dependency-inspector.png'),
      fullPage: true,
    });
  });

  for (const viewport of [
    { width: 1440, height: 900 },
    { width: 1920, height: 1080 },
    { width: 2560, height: 1440 },
    { width: 1280, height: 800 },
  ]) {
    test(`has no horizontal clipping at ${viewport.width}x${viewport.height}`, async ({ page }) => {
      const dashboard = matrix.dashboards[0];
      await page.setViewportSize(viewport);
      await page.goto(
        `/?dashboard=${dashboard.dashboard_id}&run=${dashboard.run_id}#/observe/dashboards`,
      );
      await expect(page.getByTestId('dashboard-studio')).toBeVisible();
      const overflow = await page.evaluate(
        () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
      );
      expect(overflow).toBeLessThanOrEqual(1);
      await page.screenshot({
        path: artifactPath(
          'phase11b-dashboard',
          `responsive-${viewport.width}x${viewport.height}.png`,
        ),
        fullPage: true,
      });
    });
  }
});
