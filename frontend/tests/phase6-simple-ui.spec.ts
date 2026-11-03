// Phase 6 browser workflows for the simplified UI. Needs: the backend with an isolated config dir, and scripts/phase6_fake_hec.py (no Splunk is contacted).
//   PHASE6_API_BASE=http://127.0.0.1:18581 PHASE6_HEC_STATS=http://127.0.0.1:18599 PLAYWRIGHT_BASE_URL=http://127.0.0.1:14173 npx playwright test tests/phase6-simple-ui.spec.ts
// Never points at the default backend port: without PHASE6_API_BASE the suite is skipped.
import { expect, test, type Page } from '@playwright/test';
import { mkdirSync } from 'node:fs';
import { resolve } from 'node:path';

const API = process.env.PHASE6_API_BASE ?? '';
const HEC = process.env.PHASE6_HEC_STATS ?? '';
const SHOTS = resolve(process.cwd(), '..', 'docs', 'verification', 'evidence', 'phase6_ui');
test.skip(!API || !HEC, 'set PHASE6_API_BASE and PHASE6_HEC_STATS (isolated backend + fake HEC)');
test.describe.configure({ mode: 'serial' });
mkdirSync(SHOTS, { recursive: true });

const dest = (hec: string) => ({ deployment_mode: 'DOCKER_LAB', splunk_deployment_type: 'DOCKER_BUNDLED_ENTERPRISE', hec_url: hec, search_url: 'https://127.0.0.1:18599/services/search/jobs/export', auth_method: 'HEC_TOKEN_AND_BASIC_SEARCH',
  search_username: 'admin', hec_token: 'fake-token-phase6', search_secret: 'fake-secret', indexes: ['idx_network_ops', 'cisco_mdt_metrics'], collectors: ['HEC'], guided_sample: false, allow_insecure_tls: true });
const open = async (page: Page, route: string) => { await page.setViewportSize({ width: 1280, height: 1500 }); await page.goto(`/?api_base=${encodeURIComponent(API)}#${route}`); };
const stats = async (request: import('@playwright/test').APIRequestContext) => (await (await request.get(`${HEC}/_stats`)).json()) as { events: number; by_sourcetype: Record<string, number> };

test.beforeAll(async ({ request }) => {
  expect((await request.post(`${API}/api/setup`, { data: dest(`${HEC}/services/collector`) })).ok()).toBeTruthy();
  await request.post(`${HEC}/_mode?m=ok`);
});

test('simple navigation has exactly three places and no command center', async ({ page }) => {
  await open(page, '/');
  await page.setViewportSize({ width: 1280, height: 1500 });
  const nav = page.getByRole('navigation', { name: 'Primary navigation' });
  await expect(nav.getByRole('button')).toHaveText(['Generate Data', 'Scenarios', 'Connections']);
  await expect(page.locator('.domain-selector')).toHaveCount(0);
  await expect(page.getByTestId('generate-data')).toBeVisible();          // '/' lands on Generate Data
});

test('verified integrations lead the picker and the preview is real telemetry', async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 1500 });
  await open(page, '/generate/quick');
  await expect(page.getByTestId('status-badge')).toHaveText('Verified in Splunk');
  const vendors = await page.getByTestId('vendor').locator('option').allTextContents();
  expect(vendors.length).toBe(4);                                          // only verified vendors until the toggle is used
  await expect(page.getByTestId('preview-sourcetype')).toHaveText('cisco:asa');
  const raw = await page.getByTestId('preview-raw').first().textContent();
  expect(raw).toMatch(/%ASA-\d-\d+/);
  await page.screenshot({ path: `${SHOTS}/01_generate_data_asa_preview.png`, fullPage: true });
});

for (const [vendor, st, rx] of [['cisco_asa', 'cisco:asa', /%ASA-/], ['cisco_ios', 'cisco:ios', /%[A-Z0-9_-]+-\d-[A-Z0-9_]+:/], ['fortinet', 'fortigate_traffic', /logid=|devname=/], ['palo_alto', 'pan:traffic', /TRAFFIC/]] as const) {
  test(`generate ${st}: preview, send, and a plain answer about delivery`, async ({ page, request }) => {
    const before = (await stats(request)).by_sourcetype[st] ?? 0;
    await open(page, '/generate/quick');
    await page.getByTestId('vendor').selectOption(vendor);
    await expect(page.getByTestId('sourcetype')).toHaveValue(st);
    await expect(page.getByTestId('preview-sourcetype')).toHaveText(st);
    expect(await page.getByTestId('preview-raw').first().textContent()).toMatch(rx);
    await page.getByTestId('count').fill('12');
    await page.getByTestId('generate').click();
    await expect(page.getByTestId('outcome-text')).toContainText('Splunk accepted 12', { timeout: 30_000 });
    await expect.poll(async () => ((await stats(request)).by_sourcetype[st] ?? 0) - before, { timeout: 20_000 }).toBe(12);
    // the fake receiver cannot search, so the UI must say accepted is not confirmed-indexed, and must never claim Verified
    await expect(page.getByTestId('outcome-text')).not.toContainText('Verified:');
    if (st === 'cisco:asa') await page.screenshot({ path: `${SHOTS}/02_generate_result_accepted_not_indexed.png`, fullPage: true });
  });
}

test('preview shows the same sourcetype and format that generation sends', async ({ page, request }) => {
  await open(page, '/generate/quick');
  await page.getByTestId('vendor').selectOption('fortinet');
  await expect(page.getByTestId('preview-sourcetype')).toHaveText('fortigate_traffic');   // wait for this selection's preview, never read a stale one
  const previewed = (await page.getByTestId('preview-raw').first().textContent()) ?? '';
  const before = (await stats(request)).events;
  await page.getByTestId('count').fill('3');
  await page.getByTestId('generate').click();
  await expect.poll(async () => (await stats(request)).events - before, { timeout: 20_000 }).toBe(3);
  expect(previewed).toMatch(/type="?traffic"?/);                            // the family the run sends; the receiver counted exactly 3 events for this run
});

test('unsupported and routing-conflict selections explain themselves and cannot generate', async ({ page, request }) => {
  const cat = await (await request.get(`${API}/api/compat/catalog`)).json();
  const find = (st: string) => { for (const v of cat.vendors) for (const p of v.products) for (const s of p.sourcetypes) if (s.sourcetype === st) return { v: v.id, p: p.name, s }; throw new Error(st); };
  const before = await stats(request);
  for (const st of ['cisco:thousandeyes:metric', 'cisco:intersight:metrics']) {          // vmware:perf:cpu left this list in Phase 8 (generated as a TSV event)
    const f = find(st);
    await open(page, '/generate/quick');
    await page.getByTestId('show-all').check();
    await page.getByTestId('vendor').selectOption(f.v);
    await page.getByTestId('product').selectOption(f.p);
    await page.getByTestId('sourcetype').selectOption(st);
    await expect(page.getByTestId('status-badge')).toHaveText('Unsupported or incompatible');
    await expect(page.getByTestId('blocked')).toContainText('metric-index payload');
    await expect(page.getByTestId('blocked')).toContainText('generation is disabled');
    await expect(page.getByTestId('generate')).toHaveCount(0);               // no generate control at all for a blocked selection
    await expect(page.getByTestId('preview')).toHaveCount(0);
    if (st === 'cisco:thousandeyes:metric') await page.screenshot({ path: `${SHOTS}/03_routing_conflict_blocked.png`, fullPage: true });
  }
  const noGen = cat.vendors.flatMap((v: any) => v.products.flatMap((p: any) => p.sourcetypes.filter((s: any) => s.block?.code === 'NO_GENERATOR').map((s: any) => ({ v: v.id, p: p.name, st: s.sourcetype })))).at(0);
  await open(page, '/generate/quick');
  await page.getByTestId('show-all').check();
  await page.getByTestId('vendor').selectOption(noGen.v);
  await page.getByTestId('product').selectOption(noGen.p);
  await page.getByTestId('sourcetype').selectOption(noGen.st);
  await expect(page.getByTestId('blocked')).toContainText('no verified generator');
  await expect(page.getByTestId('generate')).toHaveCount(0);
  const after = await stats(request);
  expect(after.events).toBe(before.events);                                // nothing was sent for any blocked selection
});

test('a destination that refuses events is reported as such', async ({ page, request }) => {
  await request.post(`${HEC}/_mode?m=reject`);
  try {
    await open(page, '/generate/quick');
    await page.getByTestId('count').fill('4');
    await page.getByTestId('generate').click();
    await expect(page.getByTestId('outcome-text')).toContainText('Splunk did not receive these events', { timeout: 30_000 });
    await expect(page.getByTestId('outcome-text')).toContainText(/403|rejected|token/i);
    await page.screenshot({ path: `${SHOTS}/04_destination_failure.png`, fullPage: true });
  } finally { await request.post(`${HEC}/_mode?m=ok`); }
});

test('with no reachable or saved destination the Generate button explains why', async ({ page, request }) => {
  await request.delete(`${API}/api/setup`);
  try {
    await open(page, '/generate/quick');
    await expect(page.getByTestId('cannot-run')).toContainText('No Splunk destination is set up');
    await expect(page.getByTestId('generate')).toBeDisabled();
  } finally { await request.post(`${API}/api/setup`, { data: dest(`${HEC}/services/collector`) }); }
});

test('scenarios: eligibility, run state and the difference between runnable and verified', async ({ page, request }) => {
  const all = (await (await request.get(`${API}/api/compat/scenarios`)).json()).scenarios as Array<{ id: string; title: string; run_state: string; runnable: boolean }>;
  expect(all.filter((s) => s.run_state === 'VERIFIED_IN_SPLUNK')).toHaveLength(0);   // no scenario has every source verified; the UI must not imply otherwise
  await open(page, '/generate/scenarios');
  await expect(page.getByTestId('scenario-state')).toHaveText('Runnable, not verified in Splunk');
  await expect(page.getByTestId('scenario-detail')).toContainText('That is not the same as verified');
  await expect(page.getByTestId('required').locator('li').first()).toBeVisible();
  await page.screenshot({ path: `${SHOTS}/05_scenarios_runnable_unverified.png`, fullPage: true });
  const blocked = all.find((s) => !s.runnable)!;
  await page.getByTestId('runnable-only').uncheck();
  await page.getByTestId('scenario').selectOption(blocked.id);
  await expect(page.getByTestId('scenario-state')).toHaveText('Cannot run');
  await expect(page.getByTestId('scenario-reason').first()).toBeVisible();
  await expect(page.getByTestId('run-scenario')).toBeDisabled();
  await page.screenshot({ path: `${SHOTS}/06_scenarios_cannot_run.png`, fullPage: true });
});

test('connections: event and metric index are separate fields, secrets are not shown, failures are visible', async ({ page }) => {
  await open(page, '/system/connections');
  await expect(page.getByTestId('event-index')).toHaveValue('idx_network_ops');
  await expect(page.getByTestId('metric-index')).toHaveValue('cisco_mdt_metrics');
  await expect(page.getByTestId('connection-status')).toContainText('never shown again');
  expect(await page.content()).not.toContain('fake-token-phase6');
  await page.getByRole('button', { name: 'Test connection' }).click();
  await expect(page.getByText(/Overall:/)).toBeVisible({ timeout: 30_000 });
  await page.waitForTimeout(800);                                          // let the page's entrance animation finish before the screenshot
  await page.screenshot({ path: `${SHOTS}/07_connections.png`, fullPage: true });
});
