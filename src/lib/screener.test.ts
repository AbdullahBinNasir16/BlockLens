import { describe, expect, it } from 'vitest';
import { datasets } from '../data/projects';
import { PRESETS, emptyQuery, makeCheck } from '../data/presets';
import { WALLET_CORPUS } from '../data/wallets';
import type { ScreenerQuery } from '../data/types';
import { evaluateQuery, quantifierHolds } from './screener';

const CONTRACTS = Object.values(datasets).map((d) => d.project.contract);

/** The acceptance query from the README: Base, all three contracts,
 *  01 Jun – 01 Sep 2026, PnL ≥ $2,000 and hold ≥ 15 min in at least two
 *  projects, win rate ≥ 55%. */
function acceptanceQuery(): ScreenerQuery {
  const preset = PRESETS.find((p) => p.id === 'multi-winner')!;
  const q = preset.apply(emptyQuery());
  return {
    ...q,
    scope: {
      chain: 'base',
      contracts: CONTRACTS,
      from: Date.UTC(2026, 5, 1),
      to: Date.UTC(2026, 8, 1),
    },
  };
}

describe('evaluateQuery', () => {
  it('is deterministic over the seeded corpus', () => {
    const a = evaluateQuery(acceptanceQuery(), WALLET_CORPUS);
    const b = evaluateQuery(acceptanceQuery(), WALLET_CORPUS);
    expect(a.matches.map((m) => m.wallet.address)).toEqual(b.matches.map((m) => m.wallet.address));
    expect(a.funnel).toEqual(b.funnel);
  });

  it('returns the documented eight wallets for the acceptance query', () => {
    const r = evaluateQuery(acceptanceQuery(), WALLET_CORPUS);
    expect(r.matches).toHaveLength(8);
  });

  it('never returns a wallet without the reason it matched', () => {
    const r = evaluateQuery(acceptanceQuery(), WALLET_CORPUS);
    for (const m of r.matches) {
      expect(m.matchedProjects.length).toBeGreaterThanOrEqual(2);
      expect(m.winRate).toBeGreaterThanOrEqual(55);
    }
  });

  it('builds a funnel whose stages only ever remove wallets', () => {
    const r = evaluateQuery(acceptanceQuery(), WALLET_CORPUS);
    expect(r.funnel[0].remaining).toBe(WALLET_CORPUS.length);
    for (let i = 1; i < r.funnel.length; i++) {
      expect(r.funnel[i].remaining).toBeLessThanOrEqual(r.funnel[i - 1].remaining);
      expect(r.funnel[i].removed).toBe(r.funnel[i - 1].remaining - r.funnel[i].remaining);
    }
    expect(r.funnel[r.funnel.length - 1].remaining).toBe(r.matches.length);
  });

  it('matches the contracts case-insensitively, as the user pastes them', () => {
    const q = acceptanceQuery();
    q.scope.contracts = CONTRACTS.map((c) => c.toUpperCase());
    expect(evaluateQuery(q, WALLET_CORPUS).matches).toHaveLength(8);
  });

  it('finds nothing on a chain the projects are not on', () => {
    const q = acceptanceQuery();
    q.scope.chain = 'solana';
    const r = evaluateQuery(q, WALLET_CORPUS);
    expect(r.matches).toHaveLength(0);
    expect(r.scopedWallets).toBe(0);
  });

  it('fails closed on a check id it does not know', () => {
    const q = acceptanceQuery();
    q.walletChecks = [{ ...makeCheck('winRate'), checkId: 'notARealCheck' }];
    expect(evaluateQuery(q, WALLET_CORPUS).matches).toHaveLength(0);
  });

  it('applies the project rule to the block, not to each chip', () => {
    // Exactly one qualifying project must be rarer than at least one.
    const atLeast = evaluateQuery(acceptanceQuery(), WALLET_CORPUS);
    const q = acceptanceQuery();
    q.projectRule = { ...q.projectRule, quantifier: 'atLeast', count: 1 };
    const looser = evaluateQuery(q, WALLET_CORPUS);
    expect(looser.matches.length).toBeGreaterThanOrEqual(atLeast.matches.length);
  });
});

describe('quantifierHolds', () => {
  it('reads at least / exactly / at most', () => {
    expect(quantifierHolds('atLeast', 2, 2)).toBe(true);
    expect(quantifierHolds('atLeast', 1, 2)).toBe(false);
    expect(quantifierHolds('exactly', 2, 2)).toBe(true);
    expect(quantifierHolds('exactly', 3, 2)).toBe(false);
    expect(quantifierHolds('atMost', 1, 2)).toBe(true);
    expect(quantifierHolds('atMost', 3, 2)).toBe(false);
  });
});
