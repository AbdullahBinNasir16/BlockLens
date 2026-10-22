import { describe, expect, it } from 'vitest';
import { equityCurve, picks, policyStats, withoutCapped, type PaperTrade } from './paper';

const t = (over: Partial<PaperTrade>, i: number): PaperTrade => ({
  token: `0x${String(i).padStart(40, '0')}`,
  pool: '0x' + 'p'.repeat(40),
  dex: 'uniswap-v4',
  launch_ts: new Date(Date.UTC(2026, 9, 20, 0, i)).toISOString(),
  scored_at: null,
  risk: 0.1,
  launch_type: 'launchpad',
  agent: true,
  pulled: false,
  price_6h_vs_cutoff: 1.2,
  return: 0.164,
  capped: false,
  ...over,
});

/* Four trades: two agent buys, one self-deployed rug the agent refused,
   one launchpad launch the model refused on risk. */
const BOOK: PaperTrade[] = [
  t({ return: 0.5 }, 1),
  t({ return: -0.3 }, 2),
  t({ launch_type: 'self-deployed', agent: false, pulled: true, return: -1 }, 3),
  t({ risk: 0.6, agent: false, return: 2.0, capped: false }, 4),
];

describe('picks', () => {
  it('reads each pre-registered policy', () => {
    expect(BOOK.filter((x) => picks(x, 'AGENT')).length).toBe(2);
    expect(BOOK.filter((x) => picks(x, 'CONTROL')).length).toBe(4);
    expect(BOOK.filter((x) => picks(x, 'AVOIDED')).length).toBe(2);
    expect(BOOK.filter((x) => picks(x, 'LAUNCHPAD')).length).toBe(3);
  });
});

describe('policyStats', () => {
  it('derives mean, median, hit rate and pulled count from the rows', () => {
    const a = policyStats(BOOK, 'AGENT')!;
    expect(a.trades).toBe(2);
    expect(a.mean).toBeCloseTo(0.1, 10);
    expect(a.median).toBeCloseTo(0.1, 10);
    expect(a.hitRate).toBe(0.5);
    const c = policyStats(BOOK, 'CONTROL')!;
    expect(c.pulled).toBe(1);
    expect(c.total).toBeCloseTo(1.2, 10);
  });
  it('is null when a policy took no trades', () => {
    expect(policyStats([], 'AGENT')).toBeNull();
    expect(policyStats(BOOK.filter((x) => x.agent), 'AVOIDED')).toBeNull();
  });
  it('ignores trades whose price could not be read', () => {
    const s = policyStats([...BOOK, t({ return: null, price_6h_vs_cutoff: null }, 5)], 'AGENT')!;
    expect(s.trades).toBe(2);
  });
});

describe('equityCurve', () => {
  it('accumulates one unit per trade in launch order', () => {
    const c = equityCurve([...BOOK].reverse(), 'CONTROL');
    expect(c.map((p) => p.n)).toEqual([1, 2, 3, 4]);
    expect(c[c.length - 1].v).toBeCloseTo(1.2, 10);
    expect(c[0].t).toBeLessThan(c[1].t);
  });
});

describe('withoutCapped', () => {
  it('drops the capped trades and nothing else', () => {
    const capped = [...BOOK, t({ return: 10, capped: true }, 6)];
    expect(policyStats(capped, 'AGENT')!.capped).toBe(1);
    expect(withoutCapped(capped)).toHaveLength(4);
  });
});
