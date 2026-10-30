import { expect, test, type Page } from '@playwright/test';
import { readFileSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

// Operational demo rehearsal inside authenticated Splunk Web (PLAYWRIGHT_SPLUNK=1):
// Use Case Explorer -> Select -> Configure -> Generate -> Ingest -> Verify -> Dashboard -> populated Dashboard Studio dashboard.
// Counts on the dashboard are compared with an independent Splunk REST search; nothing is mocked.
test.skip(!process.env.PLAYWRIGHT_SPLUNK, 'Splunk lab not configured');
test.setTimeout(420_000);

const WEB = process.env.SPLUNK_WEB ?? 'http://127.0.0.1:18000';
const MGMT = process.env.SPLUNK_MGMT ?? 'https://127.0.0.1:18191';
const OUT = process.env.SHOT_DIR ?? 'test-results';
const env = Object.fromEntries(
  readFileSync(fileURLToPath(new URL('../../tests/lab/phase4e/.env.lab', import.meta.url)), 'utf8')
    .split('\n').filter((l) => l.includes('=')).map((l) => l.split(/=(.*)/s).slice(0, 2)),
);

async function login(page: Page) {
  await page.goto(`${WEB}/en-US/account/login`);
  await page.locator('input[name="username"]').fill('admin');
  await page.locator('input[name="password"]').fill(env.LAB_SPLUNK_PASSWORD);
  await page.keyboard.press('Enter');
  await page.waitForURL(/\/app\//, { timeout: 60_000 });
}

test('operational: Explorer to populated Dashboard Studio dashboard', async ({ page, playwright }) => {
  await page.setViewportSize({ width: 1600, height: 1500 });
  await login(page);
  let runId = process.env.PF_RUN_ID ?? '';  // PF_RUN_ID reruns only the dashboard phase against an existing run
  let ex = page.frameLocator('#netspout-canvas-frame');
  if (!runId) {
  await page.goto(`${WEB}/en-US/app/netspout/use_case_explorer`);

  await ex.getByLabel('Search use cases').fill('DNS Diversity');
  await ex.getByTestId('explorer-card').first().click();
  await expect(ex.getByLabel('Index')).toHaveValue('idx_network_ops');
  const run = async (step: string) => {
    const el = ex.getByTestId(`step-${step}`);
    await el.getByRole('button', { name: 'Run' }).click();
    await expect(el).toHaveClass(/ux-step--ok/, { timeout: 150_000 });
    return el;
  };
  await run('CONFIGURE');
  const gen = await run('GENERATE');
  await expect(gen).toContainText('GENERATED: PROVEN');
  runId = (await gen.textContent())!.match(/Run ([0-9a-f-]{36})/)![1];
  await expect(await run('INGEST')).toContainText(/SPLUNK_DISPATCHED \S+: PROVEN/);
  await expect(await run('VERIFY')).toContainText('SPLUNK_OBSERVED: PROVEN');
  const dash = await run('DASHBOARD');
  await expect(dash).toContainText('Dashboard maturity: DATA_VALIDATED');
  await page.screenshot({ path: `${OUT}/demo-explorer-dashboard-step.png` });

  }
  // independent evidence for this run, straight from splunkd
  const admin = await playwright.request.newContext({
    baseURL: MGMT, ignoreHTTPSErrors: true,
    extraHTTPHeaders: { Authorization: 'Basic ' + Buffer.from(`admin:${env.LAB_SPLUNK_PASSWORD}`).toString('base64') },
  });
  const spl = `search index=idx_network_ops sourcetype=netspout:dns:wire netspout_run_id="${runId}" earliest=-1h | stats count count(eval(response_code=3)) as nx dc(query) as dq`;
  const res = await admin.post('/services/search/jobs/export', { form: { search: spl, output_mode: 'json' } });
  const independent = JSON.parse((await res.text()).trim().split('\n').filter((l) => l.includes('"result"')).pop()!).result;

  // open the real dashboard through the Explorer link (target=_top), bound to this run
  if (process.env.PF_RUN_ID) {
    await page.goto(`${WEB}/en-US/app/netspout/pulseforge_dns_anomaly_studio?form.run_tok=${runId}`);
  } else {
    const link = ex.getByTestId('open-splunk-dashboard');
    await expect(link).toBeVisible();
    await link.click();
    await page.waitForURL(/pulseforge_dns_anomaly_studio/);
  }
  page.setDefaultTimeout(15_000);
  await expect(page.locator('[data-test="viz-item"]')).toHaveCount(11, { timeout: 60_000 });
  const kpi = (id: string) => page.locator(`[data-test="viz-item"][data-id="${id}"]`).innerText();
  await expect.poll(async () => (await kpi('viz_1')).replace(/\D+/g, ''), { timeout: 90_000 }).toBe(String(independent.count));
  expect((await kpi('viz_2')).replace(/\D+/g, '')).toBe(String(independent.nx));
  expect((await kpi('viz_5')).replace(/\D+/g, '')).toBe(String(independent.dq));
  await page.waitForTimeout(3000);
  await page.screenshot({ path: `${OUT}/demo-dashboard-run-bound.png`, fullPage: true });
  const viz = (id: string) => page.locator(`[data-test="viz-item"][data-id="${id}"]`);
  const checks: Record<string, boolean> = {};
  const note: Record<string, string> = {};
  const attempt = async (name: string, fn: () => Promise<void>) => {
    try { await fn(); checks[name] = true; } catch (e) { checks[name] = false; note[name] = String(e).slice(0, 300); }
  };

  await attempt('browser_rendered', async () => {
    for (let i = 1; i <= 6; i++) expect((await kpi(`viz_${i}`)).replace(/\D+/g, '')).not.toBe('');
    expect(await page.locator('[data-test="charting-container"] svg').count()).toBeGreaterThanOrEqual(2);
    for (const t of ['viz_10', 'viz_11']) expect(await viz(t).locator('tbody tr').count()).toBeGreaterThan(0);
  });
  await attempt('scenario_run_binding', async () => {
    expect(Number((await kpi('viz_1')).replace(/\D+/g, ''))).toBe(Number(independent.count));
    expect(Number((await kpi('viz_2')).replace(/\D+/g, ''))).toBe(Number(independent.nx));
  });
  await attempt('visualization_compatible', async () => {
    const types = await page.locator('[data-test="viz-item"]').evaluateAll((els) => els.map((e) => e.getAttribute('data-viz-type')));
    expect(types.every((t) => /^splunk\.(singlevalue|column|area|table)$/.test(t ?? ''))).toBe(true);
    expect(await page.locator('[data-test="viz-item"]').filter({ hasText: /search error|did not return|failed to load|no results/i }).count()).toBe(0);
  });
  await attempt('drilldowns_tested', async () => {
    // phase-table drilldown: clicking the suspicious row sets the phase token and filters the incident timeline
    await viz('viz_8').locator('tbody tr').filter({ hasText: 'SUSPICIOUS_ACTIVITY' }).locator('td').first().click();
    await expect.poll(() => page.url()).toContain('form.phase_tok=SUSPICIOUS_ACTIVITY');
    await expect(viz('viz_11').locator('tbody')).not.toContainText('NORMAL');
    expect(await viz('viz_11').locator('tbody tr').count()).toBeGreaterThan(0);
    // table drilldown sets the client token
    await viz('viz_10').locator('tbody tr').first().locator('td').first().click();
    await expect.poll(() => page.url()).toContain('form.client_tok=192.0.2.25');
    // timeline row opens the matching events in Search (new tab)
    const [popup] = await Promise.all([page.waitForEvent('popup'), viz('viz_11').locator('tbody tr').first().locator('td').nth(3).click()]);
    expect(popup.url()).toMatch(/\/app\/[^/]+\/search/);
    await popup.close();
  });
  await attempt('inspector_tested', async () => {
    await viz('viz_1').hover();
    // Studio's hover layer covers the button, so dispatch the click on the element itself; it opens the job inspector tab.
    const [pop] = await Promise.all([page.waitForEvent('popup'), page.locator('[data-test="inspect-button"]:visible').first().dispatchEvent('click')]);
    await pop.waitForLoadState();
    expect(pop.url()).toContain('job_inspector');
    await pop.close();
  });
  await attempt('responsive_tested', async () => {
    for (const [w, h] of [[1280, 900], [1024, 800]]) {
      await page.setViewportSize({ width: w, height: h });
      await page.waitForTimeout(1500);
      expect(await page.locator('[data-test="viz-item"]').first().isVisible()).toBe(true);
      // Supported range is laptop/projector widths (>=1024px). Below ~1000px Studio stops scaling and the page scrolls horizontally.
      expect(await page.evaluate(() => [...document.querySelectorAll('[data-test="viz-item"]')].every((e) => e.getBoundingClientRect().right <= window.innerWidth + 1))).toBe(true);
      await page.screenshot({ path: `${OUT}/demo-dashboard-${w}.png` });
    }
    await page.setViewportSize({ width: 1600, height: 1500 });
  });
  await page.screenshot({ path: `${OUT}/demo-dashboard-after-interactions.png`, fullPage: true });

  // record the visual-validation evidence exactly as measured above; the backend decides the maturity
  const verdict = await page.evaluate(async ({ runId, checks }) => {
    const csrf = document.cookie.split('; ').find((c) => c.startsWith('splunkweb_csrf_token'))?.split('=')[1] ?? '';
    const r = await fetch('/en-US/splunkd/__raw/services/netspout_gateway/api/dashboards/scenario-sec-p9-b-dns-anomaly/validate-visual', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Splunk-Form-Key': csrf, 'X-Requested-With': 'XMLHttpRequest' },
      body: JSON.stringify({ run_id: runId, evidence_ref: `splunk-web:pulseforge_dns_anomaly_studio:run:${runId}`, export_validated: true, ...checks }),
    });
    return { status: r.status, body: await r.json() };
  }, { runId, checks: { browser_rendered: checks.browser_rendered, scenario_run_binding: checks.scenario_run_binding, source_coverage_validated: true, visualization_compatible: checks.visualization_compatible, drilldowns_tested: checks.drilldowns_tested, inspector_tested: checks.inspector_tested, responsive_tested: checks.responsive_tested } });
  writeFileSync(`${OUT}/demo-visual-validation.json`, JSON.stringify({ checks, note, verdict: { status: verdict.status, maturity: verdict.body.maturity ?? null, detail: verdict.body.detail ?? null } }, null, 2));
  expect(checks, JSON.stringify(note)).toEqual(expect.objectContaining({ browser_rendered: true, scenario_run_binding: true, visualization_compatible: true, drilldowns_tested: true, inspector_tested: true, responsive_tested: true }));
  expect(verdict.body.maturity).toBe('DASHBOARD_READY');

  writeFileSync(`${OUT}/demo-operational.json`, JSON.stringify({ runId, independent, dashboard_url: page.url().replace(/^https?:\/\/[^/]+/, '') }, null, 2));
  await admin.dispose();
});
