import { expect, test } from '@playwright/test';

const live = process.env.NETSPOUT_PHASE8_LIVE === '1';
const api = 'http://127.0.0.1:8081';

test('runs truthful Cisco 100 Docker journeys and saves a definition-only Studio clone', async ({ page, request }) => {
  test.skip(!live, 'Set NETSPOUT_PHASE8_LIVE=1 against the running Docker stack.');
  test.setTimeout(4 * 60_000);
  await page.setViewportSize({ width: 1600, height: 1000 });

  await page.goto('/#/catalog/cisco-100');
  await expect(page.getByRole('heading', { name: 'Scenario breadth without fabricated support' })).toBeVisible();
  await expect(page.getByText('100', { exact: true }).first()).toBeVisible();

  const catalogResponse = await request.get(`${api}/api/cisco100`);
  expect(catalogResponse.ok()).toBeTruthy();
  const catalog = await catalogResponse.json();
  expect(catalog.summary.scenario_definitions).toBe(100);
  expect(Object.values(catalog.summary.domains)).toEqual([20, 20, 20, 20, 20]);

  const golden = await request.post(`${api}/api/cisco100/scenarios/C100-SP-001/execute`);
  expect(golden.status()).toBe(200);
  expect((await golden.json()).runtime_scenario_id).toBe('test-correlated-interface-degradation');

  for (const scenarioId of ['C100-ENT-001', 'C100-DC-001', 'C100-SEC-001', 'C100-CRI-001']) {
    const blocked = await request.post(`${api}/api/cisco100/scenarios/${scenarioId}/execute`);
    expect(blocked.status()).toBe(409);
    expect((await blocked.json()).detail).toContain('No fallback event');
  }
  const researchBlocked = await request.post(`${api}/api/cisco100/scenarios/C100-SP-020/execute`);
  expect(researchBlocked.status()).toBe(409);
  expect((await researchBlocked.json()).detail).toContain('RESEARCH_REQUIRED');

  await page.getByRole('button', { name: /C100-ENT-001/ }).click();
  await page.getByRole('button', { name: 'Clone definition in Scenario Studio' }).click();
  await expect(page).toHaveURL(/#\/build\/studio/);
  await expect(page.getByText('Catalog definition-only draft')).toBeVisible();
  await page.getByLabel('Label').first().fill('Edited Enterprise Site');
  await page.getByRole('button', { name: /Add Entity/ }).click();
  await page.getByLabel('Scenario Studio steps').getByRole('button', { name: /PREVIEW$/i }).click();
  await page.getByRole('button', { name: /Validate Draft/ }).click();
  await expect(page.getByRole('heading', { name: 'Structure validated' })).toBeVisible();
  await page.getByRole('button', { name: /Save as Private Pack/ }).click();
  await expect(page.getByText('Definition-only draft — execution blocked')).toBeVisible();
  await expect(page.getByRole('button', { name: /Run Draft Scenario/ })).toBeDisabled();
  const cleanup = await request.delete(`${api}/api/studio/packs/private-c100-ent-001-definition`);
  expect(cleanup.ok()).toBeTruthy();
});
