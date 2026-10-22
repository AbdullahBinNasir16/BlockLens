/* Records a two-minute walk through the product against the running dev
   server and API, for the demo backup. Not a test.
     node e2e/record-demo.mjs [out.webm]                          */
import { chromium } from '@playwright/test';

const BASE = process.env.DEMO_URL ?? 'http://localhost:5173';
const out = process.argv[2] ?? 'report/figures/demo';
const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, recordVideo: { dir: out, size: { width: 1440, height: 900 } } });
const page = await ctx.newPage();
const pause = (ms) => page.waitForTimeout(ms * 1.8);
const scrollBy = async (y) => { await page.mouse.wheel(0, y); await pause(1200); };

await page.goto(`${BASE}/`); await pause(3000); await scrollBy(700); await scrollBy(700); await pause(1500);
await page.goto(`${BASE}/app/new`); await pause(2500);
await page.getByRole('button', { name: /nockchain/i }).first().click(); await pause(1200);
await page.getByRole('button', { name: /investigate/i }).click();
await page.waitForURL(/\/app\/project\/nockchain/, { timeout: 20000 }); await pause(3000); await scrollBy(600); await scrollBy(600); await pause(1000);
await page.goto(`${BASE}/app/launches`); await pause(5000); await scrollBy(400); await pause(1500);
const why = page.getByRole('button', { name: /the score's anatomy/i }).first();
if (await why.count()) { await why.click(); await pause(6000); await page.keyboard.press('Escape'); await pause(800); }
const row = page.locator('tr.bl-tr').first();
if (await row.count()) { await row.click(); await page.waitForURL(/\/app\/token\//, { timeout: 15000 }); await pause(4000); await scrollBy(600); await pause(2500); }
await page.goto(`${BASE}/app/portfolio`); await pause(5000); await scrollBy(600); await pause(2500);
await page.goto(`${BASE}/app/model`); await pause(5000); await scrollBy(600); await pause(2500);
await page.goto(`${BASE}/app/watchlist`); await pause(3000);
await page.goto(`${BASE}/app/trending`); await pause(5000);
await ctx.close(); await browser.close();
console.log('recorded to', out);
