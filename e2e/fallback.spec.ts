import { expect, test } from '@playwright/test';

/* Phase 7: the live and sample boundary, in a real browser.
   - With the API cut off, every model screen degrades to its sample with a
     visible badge, never a blank page, and no score is invented.
   - The browser never calls a third-party source itself.
   - A token the live feed never saw is out of the model's scope. */

const blockApi = async (page: import('@playwright/test').Page) => {
  await page.route(/\/api\//, (r) => r.abort());
};

test('trending falls back to its dated sample, badged, when the API is down', async ({ page }) => {
  await blockApi(page);
  await page.goto('/app/trending');
  await expect(page.locator('.bl-prov', { hasText: /sample data/i }).first()).toBeVisible({ timeout: 20_000 });
  await expect(page.locator('.bl-samplebar')).toContainText(/not live/i);
  await expect(page.locator('tbody tr').first()).toBeVisible();
});

test('the model screens degrade to their snapshots, badged', async ({ page }) => {
  await blockApi(page);
  for (const path of ['/app/launches', '/app/model', '/app/portfolio']) {
    await page.goto(path);
    await expect(page.locator('.bl-samplebar')).toBeVisible({ timeout: 20_000 });
    await expect(page.locator('.bl-prov', { hasText: /sample data/i }).first()).toBeVisible();
  }
});

test('the screener degrades to the generated corpus, badged', async ({ page }) => {
  await blockApi(page);
  await page.goto('/app/wallets');
  await expect(page.locator('.bl-samplebar')).toContainText(/not real wallets/i, { timeout: 20_000 });
});

test('a real token never gets a sample score when the API is down', async ({ page }) => {
  await blockApi(page);
  await page.goto('/app/token/0x' + '3'.repeat(40));
  await expect(page.locator('.bl-risk-panel')).toContainText(/no sample score is ever shown/i, { timeout: 20_000 });
  await expect(page.locator('.bl-risk-panel')).not.toContainText(/in 100/);
});

test('the browser never calls a third-party market source', async ({ page }) => {
  const third: string[] = [];
  page.on('request', (r) => {
    if (/geckoterminal|dexscreener|gopluslabs/.test(r.url())) third.push(r.url());
  });
  await page.goto('/app/trending');
  await page.waitForTimeout(3000);
  await page.goto('/app/token/0x' + '3'.repeat(40));
  await page.waitForTimeout(3000);
  expect(third).toEqual([]);
});

test('a token the live feed never saw is outside the model scope', async ({ page }) => {
  await page.goto('/app/token/0x' + '4'.repeat(40));
  await expect(page.locator('.bl-risk-panel')).toContainText(/outside the model's scope/i, { timeout: 20_000 });
  await expect(page.locator('.bl-risk-panel')).toContainText(/not trained on/i);
});
