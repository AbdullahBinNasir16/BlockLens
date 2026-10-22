import { describe, expect, it } from 'vitest';
import { START_CAPITAL, TRADES } from '../data/portfolio';
import { EQUITY, bookStats, byKind, byMonth, isOpen, tradePath, tradePnl } from './portfolio';

/* The Portfolio page's simulated book is derived from its trade records and
   nothing is stored, so the arithmetic is checked here as invariants rather
   than as fixed numbers: change a trade and the headline must follow. */
describe('bookStats', () => {
  const s = bookStats();

  it('counts open and closed trades from the records', () => {
    expect(s.open).toBe(TRADES.filter(isOpen).length);
    expect(s.closed).toBe(TRADES.length - s.open);
  });

  it('derives value from start capital plus realised and unrealised PnL', () => {
    expect(s.value).toBeCloseTo(START_CAPITAL + s.realized + s.unrealized, 6);
    expect(s.ret).toBeCloseTo(s.value / START_CAPITAL - 1, 10);
  });

  it('computes the win rate over closed trades only', () => {
    expect(s.winRate).toBeCloseTo(s.wins / s.closed, 10);
    expect(s.wins).toBeLessThanOrEqual(s.closed);
  });

  it('ends the equity curve at the current book value', () => {
    expect(EQUITY[EQUITY.length - 1].v).toBeCloseTo(s.value, 6);
  });

  it('keeps drawdown inside [0, 1]', () => {
    expect(s.maxDrawdown).toBeGreaterThanOrEqual(0);
    expect(s.maxDrawdown).toBeLessThanOrEqual(1);
  });
});

describe('byKind and byMonth', () => {
  it('partition the book PnL (realised and unrealised) exactly', () => {
    const total = TRADES.reduce((a, t) => a + tradePnl(t), 0);
    const kinds = byKind();
    expect(kinds.reduce((a, k) => a + k.pnl, 0)).toBeCloseTo(total, 6);
    expect(kinds.reduce((a, k) => a + k.trades, 0)).toBe(TRADES.length);
    expect(kinds.reduce((a, k) => a + k.closed, 0)).toBe(TRADES.filter((t) => !isOpen(t)).length);
  });

  it('chains monthly returns into the overall return', () => {
    const months = byMonth();
    expect(months.length).toBeGreaterThan(0);
    const chained = months.reduce((a, m) => a * (1 + m.ret), 1) - 1;
    expect(chained).toBeCloseTo(bookStats().ret, 6);
  });
});

describe('tradePath', () => {
  it('is pinned at entry, peak and exit, and deterministic', () => {
    for (const t of TRADES) {
      const p = tradePath(t);
      expect(p[0]).toBeCloseTo(1, 6);
      expect(Math.max(...p)).toBeCloseTo(t.peak, 6);
      expect(tradePath(t)).toEqual(p);
    }
  });
});
