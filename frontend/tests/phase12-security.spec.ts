import { expect, test } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';
import { artifactPath, testArtifactRoot } from './artifact-paths';

type DashboardResult = {
  dashboard_id: string;
  scenario_id: string;
  run_id: string;
  export_valid: boolean;
  data_validated: boolean;
};

type DashboardMatrix = {
  dashboards: DashboardResult[];
};

const liveEnabled = process.env.NETSPOUT_PHASE12_LIVE === '1';
const matrixPath =
  process.env.NETSPOUT_PHASE12_MATRIX ??
  path.resolve(
    process.cwd(),
    '..',
    '.artifacts/phase12-current/phase12/phase12-dashboard-validation.json',
  );
const matrix = liveEnabled
  ? (JSON.parse(fs.readFileSync(matrixPath, 'utf8')) as DashboardMatrix)
  : ({ dashboards: [] } as DashboardMatrix);

test.describe('Phase 12 agentic AI and supply-chain journeys', () => {
  test.skip(!liveEnabled, 'requires fresh Phase 12 Splunk and dashboard evidence');
  test.describe.configure({ mode: 'serial' });

  test('renders all Phase 12 dashboards with run, topology, perspectives, inspector, and export', async ({
    page,
  }) => {
    test.setTimeout(300_000);
    expect(matrix.dashboards).toHaveLength(13);
    const results: Array<Record<string, unknown>> = [];
    await page.setViewportSize({ width: 1440, height: 900 });

    for (const dashboard of matrix.dashboards) {
      expect(dashboard.data_validated).toBe(true);
      await page.goto(
        `/?dashboard=${encodeURIComponent(dashboard.dashboard_id)}&run=${encodeURIComponent(dashboard.run_id)}#/observe/dashboards`,
      );
      await expect(page.getByTestId('dashboard-studio')).toBeVisible();
      await expect(page.getByLabel('Run context')).toHaveValue(dashboard.run_id);
      await expect(page.getByText(dashboard.scenario_id, { exact: false }).first()).toBeVisible();
      await expect(page.getByTestId('dashboard-topology')).toBeVisible();
      await expect(page.locator('.dashboard-panel').first()).toBeVisible();

      const slug = dashboard.dashboard_id.toLowerCase().replace(/[^a-z0-9]+/g, '-');
      for (const perspective of ['NOC', 'ENGINEER', 'EVIDENCE'] as const) {
        if (perspective !== 'NOC') {
          await page.getByRole('tab', { name: perspective }).click({ force: true });
        }
        await expect(page.locator('.dashboard-panel').first()).toBeVisible();
        await page.screenshot({
          path: artifactPath(
            'phase12-dashboard',
            `${slug}-${perspective.toLowerCase()}-1440.png`,
          ),
          fullPage: true,
        });
      }
      await page.getByRole('tab', { name: 'NOC' }).click({ force: true });
      await page.getByRole('button', { name: 'Inspect' }).first().click();
      const inspector = page.getByLabel('Advanced Inspector');
      await expect(inspector).toBeVisible();
      await page.getByRole('button', { name: 'SPL', exact: true }).click();
      await expect(inspector).toContainText(dashboard.run_id);
      await page.getByRole('button', { name: 'Dependencies', exact: true }).click();
      await expect(inspector).not.toContainText('DEPENDENCY_BLOCKED');
      await page.getByLabel('Close inspector').click();

      await page.getByRole('button', { name: 'Export / Deploy' }).click();
      const dialog = page.getByRole('dialog', {
        name: 'Dashboard export and deployment preview',
      });
      await expect(dialog).toContainText('VALID');
      await expect(dialog).toContainText('not deployment evidence');
      await page.getByLabel('Close export preview').click();
      results.push({
        ...dashboard,
        browser_rendered: true,
        scenario_run_binding: true,
        perspectives: ['NOC', 'ENGINEER', 'EVIDENCE'],
        inspector_tested: true,
        export_preview_tested: true,
      });
    }

    const output = path.join(
      testArtifactRoot(),
      'phase12',
      'phase12-visual-browser-matrix.json',
    );
    fs.mkdirSync(path.dirname(output), { recursive: true });
    fs.writeFileSync(output, `${JSON.stringify(results, null, 2)}\n`, 'utf8');
  });

  test('shows the five bounded learning journeys and preserves old dashboard eligibility', async ({
    page,
  }) => {
    const catalog = await (await page.request.get('/api/dashboards')).json();
    expect(catalog.eligible_count).toBe(27);
    const phase12Ids = new Set(matrix.dashboards.map((item) => item.dashboard_id));
    expect(phase12Ids).toEqual(
      new Set([
        'scenario-ai-001',
        'scenario-ai-002',
        'scenario-ai-003',
        'scenario-ai-004',
        'scenario-ai-005',
        'scenario-ai-006',
        'scenario-sc-001',
        'scenario-sc-002',
        'scenario-sc-003',
        'scenario-sc-004',
        'scenario-sc-005',
        'scenario-p12-xd-001',
        'scenario-p12-xd-002',
      ]),
    );
    for (const anchor of [
      'scenario-ai-001',
      'scenario-ai-002',
      'scenario-ai-005',
      'scenario-sc-003',
      'scenario-p12-xd-001',
    ]) {
      const dashboard = matrix.dashboards.find((item) => item.dashboard_id === anchor)!;
      await page.goto(
        `/?dashboard=${dashboard.dashboard_id}&run=${dashboard.run_id}#/observe/dashboards`,
      );
      await expect(page.getByText(dashboard.scenario_id, { exact: false }).first()).toBeVisible();
      await expect(page.locator('.dashboard-panel').first()).toBeVisible();
    }
    const legacyEligible = catalog.dashboards.filter(
      (item: { state: string; scenario_id: string; industry_id?: string }) =>
        item.state === 'ELIGIBLE' &&
        !phase12Ids.has(`scenario-${item.scenario_id.toLowerCase()}`),
    );
    expect(legacyEligible).toHaveLength(14);
  });

  test('rejects unsupported external Scenario Studio content through the real API', async ({
    request,
  }) => {
    const draftResponse = await request.post('/api/studio/drafts', {
      data: {
        creation_path: 'CLONE_SCENARIO',
        clone_scenario_id: 'AI-002',
        title: 'Phase 12 private clone',
      },
    });
    expect(draftResponse.ok()).toBe(true);
    const draft = await draftResponse.json();
    expect(draft.cloned_from_scenario_id).toBe('AI-002');
    expect(draft.parameters.map((item: { parameter_id: string }) => item.parameter_id)).toEqual(
      expect.arrayContaining(['intensity', 'policy_mode']),
    );
    draft.parameters.find(
      (item: { parameter_id: string }) => item.parameter_id === 'intensity',
    ).default = 2;
    const cleanValidation = await request.post('/api/studio/packs/validate', {
      data: draft,
    });
    expect(cleanValidation.ok()).toBe(true);
    expect((await cleanValidation.json()).valid).toBe(true);
    const savedResponse = await request.post('/api/studio/packs', { data: draft });
    expect(savedResponse.ok()).toBe(true);
    const saved = await savedResponse.json();
    const reloadedResponse = await request.get(`/api/studio/packs/${saved.pack_id}`);
    expect(reloadedResponse.ok()).toBe(true);
    const reloaded = await reloadedResponse.json();
    expect(
      reloaded.parameters.find(
        (item: { parameter_id: string }) => item.parameter_id === 'intensity',
      ).default,
    ).toBe(2);
    const runResponse = await request.post(`/api/studio/packs/${saved.pack_id}/run`, {
      data: { parameters: { intensity: 2, policy_mode: 'enforce' }, seed: 1212 },
    });
    expect(runResponse.ok()).toBe(true);
    const run = await runResponse.json();
    expect(run.scenario_id).toBe(saved.scenario_id);
    expect(run.events).not.toHaveLength(0);

    const unsafe = structuredClone(draft);
    unsafe.entities[0].attributes.endpoint = 'https://external.invalid/mcp';
    const validation = await request.post('/api/studio/packs/validate', { data: unsafe });
    expect(validation.ok()).toBe(true);
    const report = await validation.json();
    expect(report.valid).toBe(false);
    expect(
      report.checks.some(
        (item: { check_id: string; state: string }) =>
          item.check_id === 'execution-containment' && item.state === 'FAIL',
      ),
    ).toBe(true);
  });
});
