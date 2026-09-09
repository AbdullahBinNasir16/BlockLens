import type { AppliedCheck, CheckOperator, CheckValue, ScreenerQuery } from './types';
import { CHECK_BY_ID } from './checks';
import { CORPUS_NOW } from './wallets';

/* ============================================================
   Starting points.

   A preset switches a set of filters on and sets the window. It never
   touches the chain or the contracts — those are the user's question;
   a preset only suggests how to ask it.
   ============================================================ */

const DAY = 24 * 60 * 60 * 1000;

/** Windows are relative to the corpus clock, not the wall clock, so a
 *  search returns the same rows whenever it is run. */
export const WINDOW_PRESETS: { id: string; label: string; days: number | 'ytd' }[] = [
  { id: '7d', label: '7D', days: 7 },
  { id: '30d', label: '30D', days: 30 },
  { id: '90d', label: '90D', days: 90 },
  { id: 'ytd', label: 'YTD', days: 'ytd' },
];

export function windowRange(id: string): { from: number; to: number } {
  const to = CORPUS_NOW;
  if (id === 'ytd') return { from: Date.UTC(new Date(to).getUTCFullYear(), 0, 1), to };
  const preset = WINDOW_PRESETS.find((w) => w.id === id);
  const days = typeof preset?.days === 'number' ? preset.days : 90;
  return { from: to - days * DAY, to };
}

export function makeCheck(checkId: string, operator?: CheckOperator, value?: CheckValue): AppliedCheck {
  const def = CHECK_BY_ID[checkId];
  return {
    checkId,
    operator: operator ?? def.operators[0],
    value: value ?? def.defaultValue,
  };
}

export function emptyQuery(): ScreenerQuery {
  return {
    scope: { chain: 'base', contracts: [], ...windowRange('90d') },
    projectRule: { quantifier: 'atLeast', count: 1, checks: [] },
    walletChecks: [],
  };
}

export interface Preset {
  id: string;
  label: string;
  apply: (q: ScreenerQuery) => ScreenerQuery;
}

export const PRESETS: Preset[] = [
  {
    id: 'multi-winner',
    label: 'Multi-project winners',
    apply: (q) => ({
      scope: { ...q.scope, ...windowRange('90d') },
      projectRule: {
        quantifier: 'atLeast',
        count: 2,
        checks: [makeCheck('realizedPnl', 'gte', 2000), makeCheck('holdingTime', 'gte', 15)],
      },
      walletChecks: [makeCheck('winRate', 'gte', 55)],
    }),
  },
  {
    id: 'fast-flippers',
    label: 'Fast flippers',
    /* year-to-date, because sub-minute round trips cluster at launch and a
       90-day window cuts most launches off */
    apply: (q) => ({
      scope: { ...q.scope, ...windowRange('ytd') },
      projectRule: { quantifier: 'atLeast', count: 2, checks: [makeCheck('roundTripUnder', 'lte', 1)] },
      walletChecks: [makeCheck('medianHoldingTime', 'lte', 60)],
    }),
  },
  {
    id: 'fresh-outsized',
    label: 'Fresh wallets',
    /* same reason: a fresh wallet's first buy is usually near a launch */
    apply: (q) => ({
      scope: { ...q.scope, ...windowRange('ytd') },
      projectRule: { quantifier: 'atLeast', count: 1, checks: [makeCheck('realizedPnl', 'gte', 5000)] },
      walletChecks: [
        makeCheck('walletAgeAtFirstBuy', 'lte', 30 * 24 * 60),
        makeCheck('fundingSource', 'is', 'fresh'),
      ],
    }),
  },
];
