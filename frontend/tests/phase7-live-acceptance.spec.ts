import { expect, test } from '@playwright/test';
import path from 'node:path';

const live = process.env.NETSPOUT_PHASE7_LIVE === '1';
const image = (name: string) => path.resolve(
  process.cwd(),
  '../docs/implementation/images',
  `phase7-${name}.png`,
);

test('captures the live Docker Studio clone and completion journey', async ({ page }) => {
  test.skip(!live, 'Set NETSPOUT_PHASE7_LIVE=1 against the running Docker stack.');
  test.setTimeout(4 * 60_000);
  await page.setViewportSize({ width: 1600, height: 1000 });

  await page.goto('/#/catalog/cisco-coverage');
  await expect(page.getByRole('heading', { name: 'Evidence before generation' })).toBeVisible();

  await page.goto('/#/build/studio');
  await expect(page.getByTestId('studio-home')).toBeVisible();
  await page.getByRole('button', { name: /Phase 7 IOS XR Private Variant/ }).click();
  await expect(page.getByRole('heading', { name: 'Phase 7 IOS XR Private Variant' })).toBeVisible();
  await page.screenshot({ path: image('20-scenario-studio-clone-edit'), fullPage: true });

  await page.getByLabel('Scenario Studio steps').getByRole('button', { name: /SAVE & RUN$/i }).click();
  await page.getByRole('button', { name: /Run Draft Scenario/ }).click();
  await expect(page.getByText(/COMPLETED/).first()).toBeVisible({ timeout: 150_000 });
  await page.screenshot({ path: image('21-scenario-completion'), fullPage: true });
});
