import { expect, test } from '@playwright/test';

/* The product's main paths, driven through a real browser against the
   real API. These are smoke tests: they prove the halves are wired, not
   every detail of each page. */

/* A syntactically valid address no source knows, so the row must fall back
   to the label the test gave it. */
const FAKE = '0x' + '2e'.repeat(20);

test('landing page offers the workspace', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('navigation').getByRole('link', { name: /open workspace/i })).toBeVisible();
});

test('a case-study address resolves to its profile', async ({ page }) => {
  await page.goto('/app/new');
  const nock = page.getByRole('button', { name: /nockchain/i }).first();
  await nock.click();
  await page.getByRole('button', { name: /investigate/i }).click();
  await expect(page).toHaveURL(/\/app\/project\/nockchain/, { timeout: 20_000 });
  await expect(page.getByRole('heading', { name: 'Nockchain' })).toBeVisible();
});

test('an unknown address goes to the live token page, never a sample profile', async ({ page }) => {
  await page.goto('/app/new');
  await page.getByLabel(/contract address/i).fill('0x' + '1'.repeat(40));
  await page.getByRole('button', { name: /investigate/i }).click();
  await expect(page).toHaveURL(/\/app\/token\/0x1{40}/);
  await expect(page.getByText(/no hand-built research profile/i)).toBeVisible();
});

test('fresh launches shows the model and its validation record', async ({ page }) => {
  await page.goto('/app/launches');
  await expect(page.getByText(/buyer-loss risk · buyer-loss-v1/i)).toBeVisible({ timeout: 15_000 });
  await expect(page.getByText(/PR-AUC/).first()).toBeVisible();
  await expect(page.getByText(/^Live$/)).toBeVisible();
});

test('model health reads the forward log', async ({ page }) => {
  await page.goto('/app/model');
  await expect(page.getByText(/launches a day, and why each was or was not scored/i)).toBeVisible({ timeout: 15_000 });
  await expect(page.getByText('buyer-loss-v1')).toBeVisible();
});

test('the paper agent page answers', async ({ page }) => {
  await page.goto('/app/portfolio');
  await expect(page.getByRole('heading', { name: 'Paper Agent' })).toBeVisible();
  await expect(page.getByText(/no resolved trades yet|agent mean return/i)).toBeVisible({ timeout: 15_000 });
});

test('the watchlist round-trips through the API', async ({ page, request }) => {
  const r = await request.post('http://127.0.0.1:8000/api/watchlist', { data: { address: FAKE, label: 'e2e-watch' } });
  expect(r.ok()).toBeTruthy();
  await page.goto('/app/watchlist');
  await expect(page.getByRole('table').getByText('e2e-watch').first()).toBeVisible({ timeout: 15_000 });
  const d = await request.delete(`http://127.0.0.1:8000/api/watchlist/${FAKE}`);
  expect(d.ok()).toBeTruthy();
});
