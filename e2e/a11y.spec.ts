import AxeBuilder from '@axe-core/playwright';
import { expect, test } from '@playwright/test';
import { mkdirSync, writeFileSync } from 'node:fs';

/* Automated accessibility audit (slide 10: "works without perfect sight or
   a mouse"). axe-core checks every screen against WCAG 2.1 A and AA rules.
   It finds roughly a third to a half of real problems; colour meaning, focus
   order sense and screen-reader wording still need a person.

   Every result is written to test-results/a11y/*.json. The test fails on any
   serious or critical violation. */

const SCREENS: [string, string][] = [
  ['Landing', '/'],
  ['New investigation', '/app/new'],
  ['Case study', '/app/project/nockchain'],
  ['Live token', '/app/token/0x' + '1'.repeat(40)],
  ['Trending', '/app/trending'],
  ['Fresh launches', '/app/launches'],
  ['Wallet screener', '/app/wallets'],
  ['Model health', '/app/model'],
  ['Portfolio', '/app/portfolio'],
  ['Watchlist', '/app/watchlist'],
  ['History', '/app/history'],
];

/* One file per test: a failing test restarts the worker, which would lose
   anything held in memory. */
const save = (name: string, data: unknown) => {
  mkdirSync('test-results/a11y', { recursive: true });
  writeFileSync(`test-results/a11y/${name.replace(/\W+/g, '_')}.json`, JSON.stringify({ name, ...(data as object) }, null, 1));
};

for (const [name, path] of SCREENS) {
  test(`axe: ${name}`, async ({ page }) => {
    await page.goto(path);
    await page.waitForLoadState('networkidle', { timeout: 15_000 }).catch(() => {});
    const r = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']).analyze();
    const v = r.violations.map((x) => ({
      id: x.id, impact: x.impact, help: x.help, nodes: x.nodes.length,
      examples: x.nodes.slice(0, 3).map((n) => n.target.join(' ')),
    }));
    save(name, { path, violations: v, passes: r.passes.length, incomplete: r.incomplete.length });
    const bad = v.filter((x) => x.impact === 'serious' || x.impact === 'critical');
    expect.soft(bad, `${name}: serious or critical violations`).toEqual([]);
  });
}

test('keyboard: every workspace nav link is reachable by Tab', async ({ page }) => {
  await page.goto('/app/new');
  const links = await page.getByRole('navigation').getByRole('link').all();
  const want = new Set<string>();
  for (const l of links) want.add((await l.getAttribute('href')) ?? '');
  const reached = new Set<string>();
  for (let i = 0; i < 80 && reached.size < want.size; i++) {
    await page.keyboard.press('Tab');
    const href = await page.evaluate(() => document.activeElement?.getAttribute('href') ?? null);
    if (href && want.has(href)) reached.add(href);
  }
  save('keyboard', { navLinks: want.size, reachedByTab: reached.size });
  expect([...want].filter((h) => !reached.has(h))).toEqual([]);
});