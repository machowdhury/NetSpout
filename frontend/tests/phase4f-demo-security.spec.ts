import { expect, test, type Page } from '@playwright/test';
import { readFileSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

// Security demo rehearsal inside authenticated Splunk Web (PLAYWRIGHT_SPLUNK=1):
// Use Case Explorer -> React2Shell -> Prerequisites -> Generate -> Ingest -> Enable saved-search detection ->
// independent proof (via splunkd) that Splunk's own scheduler ran the saved search after this replay and that it matched.
// Not Enterprise Security, not CIM, no notable events, and not the upstream Cisco TA: none of that is exercised here.
test.skip(!process.env.PLAYWRIGHT_SPLUNK, 'Splunk lab not configured');
test.setTimeout(1_500_000);

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

test('security: React2Shell through Splunk Web with independent scheduler evidence', async ({ page, playwright }) => {
  await page.setViewportSize({ width: 1600, height: 1400 });
  await login(page);
  await page.goto(`${WEB}/en-US/app/netspout/use_case_explorer`);
  const ex = page.frameLocator('#netspout-canvas-frame');
  const admin = await playwright.request.newContext({
    baseURL: MGMT, ignoreHTTPSErrors: true,
    extraHTTPHeaders: { Authorization: 'Basic ' + Buffer.from(`admin:${env.LAB_SPLUNK_PASSWORD}`).toString('base64') },
  });
  const search = async (spl: string, earliest = '-1h') => {
    const r = await admin.post('/services/search/jobs/export', { form: { search: spl, output_mode: 'json', earliest_time: earliest } });
    return (await r.text()).trim().split('\n').filter((l) => l.includes('"result"')).map((l) => JSON.parse(l).result);
  };

  await ex.getByLabel('Type').selectOption('security');
  await expect(ex.getByTestId('explorer-card')).toHaveCount(1);
  await ex.getByTestId('explorer-card').first().click();
  await ex.getByLabel('Index').selectOption('idx_security_fw');
  const run = async (step: string) => {
    const el = ex.getByTestId(`step-${step}`);
    await el.getByRole('button', { name: 'Run' }).click();
    await expect(el).toHaveClass(/ux-step--ok/, { timeout: 150_000 });
    return el;
  };
  await run('PREREQUISITES');
  await expect(await run('GENERATE')).toContainText('integrity checked');
  const replayStarted = Math.floor(Date.now() / 1000) - 5;
  const ingest = await run('INGEST');
  await expect(ingest).toContainText('Splunk observed 1 events (OBSERVED)');
  const runId = (await ingest.textContent())!.match(/Replay (\S+?):/)![1];
  const enable = await run('ENABLE_DETECTION');
  await expect(enable).toContainText('ENABLED');
  await expect(await run('VERIFY')).toContainText('POSITIVE_CASE_VALIDATED');
  await page.screenshot({ path: `${OUT}/demo-security-explorer.png` });

  // The saved search exists, is scheduled and enabled on Splunk read-back
  const ss = await search('| rest /servicesNS/-/netspout/saved/searches splunk_server=local | search title="NetSpout - Cisco Secure Firewall - React Server Components RCE Attempt" | table title cron_schedule disabled is_scheduled');
  expect(ss[0]).toMatchObject({ disabled: '0', is_scheduled: '1', cron_schedule: '*/15 * * * *' });
  const name = ss[0].title as string;

  // Wait for Splunk's scheduler to run it AFTER this replay, with at least one match
  const fired = { result_count: 0, status: '', time: '' };
  const deadline = Date.now() + 20 * 60_000;
  while (Date.now() < deadline) {
    const rows = await search(`search index=_internal sourcetype=scheduler savedsearch_name="${name}" earliest=${replayStarted} | table _time status result_count run_time | sort 0 _time`, `${replayStarted}`);
    const hit = rows.find((r) => r.status === 'success' && Number(r.result_count) >= 1);
    if (hit) { fired.result_count = Number(hit.result_count); fired.status = hit.status; fired.time = hit._time; break; }
    await page.waitForTimeout(20_000);
  }
  expect(fired.result_count, 'scheduler must run the saved search after the replay and match').toBeGreaterThanOrEqual(1);

  // Independent confirmation: the replayed event itself is in Splunk with this run id
  const indexed = await search(`search index=idx_security_fw netspout_run_id="${runId}" | stats count`);
  expect(Number(indexed[0].count)).toBeGreaterThanOrEqual(1);
  writeFileSync(`${OUT}/demo-security.json`, JSON.stringify({ replay_run_id: runId, saved_search: name, scheduler: fired, indexed_events: Number(indexed[0].count) }, null, 2));
  await admin.dispose();
});
