import type { CheckCategory, CheckDefinition, CheckOperator } from './types';

/* ============================================================
   The check library.

   Every filter the screener can apply is declared here and nowhere else.
   A check earns its place only if a backend could index and evaluate it
   independently — that constraint is why there is no formula editor.

   Labels are one or two words because the label is the whole chip. The
   meaning has to survive without a description, so a name that needs one
   is the wrong name.

   Adding a check means adding one entry here and one metric in
   `src/lib/screener.ts`. No UI file changes.

   Canonical units, so the evaluator never has to guess:
     currency  USD
     percent   0-100
     duration  minutes
     multiple  ×, where 1 is break-even
     date      ms epoch
   ============================================================ */

export const CATEGORY_LABEL: Record<CheckCategory, string> = {
  performance: 'Performance',
  timing: 'Timing',
  breadth: 'Breadth',
  identity: 'Identity',
  risk: 'Risk',
  activity: 'Activity',
};

export const CATEGORY_ORDER: CheckCategory[] = [
  'performance',
  'timing',
  'breadth',
  'identity',
  'risk',
  'activity',
];

const HOUR = 60;
const DAY = 60 * 24;

const range: CheckOperator[] = ['gte', 'lte'];
const ceiling: CheckOperator[] = ['lte', 'gte'];

export const CHECKS: CheckDefinition[] = [
  /* ---------------- per project ---------------- */
  { id: 'realizedPnl', label: 'PnL', category: 'performance', tier: 'project', valueType: 'currency', derivation: 'direct', operators: range, defaultValue: 2000 },
  { id: 'unrealizedPnl', label: 'Unrealized', category: 'performance', tier: 'project', valueType: 'currency', derivation: 'direct', operators: range, defaultValue: 0 },
  { id: 'roiMultiple', label: 'ROI', category: 'performance', tier: 'project', valueType: 'multiple', derivation: 'direct', operators: range, defaultValue: 2 },

  { id: 'holdingTime', label: 'Hold time', category: 'timing', tier: 'project', valueType: 'duration', derivation: 'direct', operators: range, defaultValue: 15 },
  { id: 'entryDelay', label: 'Entry delay', category: 'timing', tier: 'project', valueType: 'duration', derivation: 'direct', operators: ceiling, defaultValue: 1 * HOUR },
  { id: 'buyCount', label: 'Buys', category: 'timing', tier: 'project', valueType: 'integer', derivation: 'direct', operators: range, defaultValue: 2 },
  { id: 'sellCount', label: 'Sells', category: 'timing', tier: 'project', valueType: 'integer', derivation: 'direct', operators: range, defaultValue: 1 },
  { id: 'partialExitRatio', label: 'Sold %', category: 'timing', tier: 'project', valueType: 'percent', derivation: 'direct', operators: ceiling, defaultValue: 60 },
  { id: 'averagedDown', label: 'Averaged down', category: 'timing', tier: 'project', valueType: 'boolean', derivation: 'direct', operators: ['is'], defaultValue: true },
  { id: 'roundTripUnder', label: 'Round trip', category: 'timing', tier: 'project', valueType: 'duration', derivation: 'direct', operators: ['lte'], defaultValue: 1 },
  { id: 'soldFirstPump', label: 'First pump', category: 'timing', tier: 'project', valueType: 'boolean', derivation: 'derived', operators: ['is'], defaultValue: true },

  /* ---------------- whole wallet ---------------- */
  { id: 'winRate', label: 'Win rate', category: 'performance', tier: 'wallet', valueType: 'percent', derivation: 'direct', operators: range, defaultValue: 55 },
  { id: 'walletRealizedPnl', label: 'Total PnL', category: 'performance', tier: 'wallet', valueType: 'currency', derivation: 'direct', operators: range, defaultValue: 10000 },
  { id: 'bestTradeMultiple', label: 'Best trade', category: 'performance', tier: 'wallet', valueType: 'multiple', derivation: 'direct', operators: range, defaultValue: 5 },
  { id: 'medianTradePnl', label: 'Median PnL', category: 'performance', tier: 'wallet', valueType: 'currency', derivation: 'direct', operators: range, defaultValue: 0 },
  { id: 'totalVolume', label: 'Volume', category: 'performance', tier: 'wallet', valueType: 'currency', derivation: 'direct', operators: range, defaultValue: 50000 },
  { id: 'lossCount', label: 'Losses', category: 'performance', tier: 'wallet', valueType: 'integer', derivation: 'direct', operators: ceiling, defaultValue: 2 },

  { id: 'avgHoldingTime', label: 'Avg hold', category: 'timing', tier: 'wallet', valueType: 'duration', derivation: 'direct', operators: range, defaultValue: 1 * DAY },
  { id: 'medianHoldingTime', label: 'Median hold', category: 'timing', tier: 'wallet', valueType: 'duration', derivation: 'direct', operators: range, defaultValue: 6 * HOUR },
  { id: 'minHoldingTime', label: 'Min hold', category: 'timing', tier: 'wallet', valueType: 'duration', derivation: 'direct', operators: range, defaultValue: 5 },
  { id: 'maxHoldingTime', label: 'Max hold', category: 'timing', tier: 'wallet', valueType: 'duration', derivation: 'direct', operators: range, defaultValue: 30 * DAY },

  { id: 'distinctProjects', label: 'Projects', category: 'breadth', tier: 'wallet', valueType: 'integer', derivation: 'direct', operators: range, defaultValue: 2 },
  { id: 'pnlConcentration', label: 'Concentration', category: 'breadth', tier: 'wallet', valueType: 'percent', derivation: 'direct', operators: ceiling, defaultValue: 70 },
  { id: 'newPositions', label: 'New entries', category: 'breadth', tier: 'wallet', valueType: 'integer', derivation: 'direct', operators: range, defaultValue: 1 },

  { id: 'walletAgeAtFirstBuy', label: 'Wallet age', category: 'identity', tier: 'wallet', valueType: 'duration', derivation: 'direct', operators: ceiling, defaultValue: 7 * DAY },
  {
    id: 'fundingSource',
    label: 'Funding',
    category: 'identity',
    tier: 'wallet',
    valueType: 'enum',
    derivation: 'derived',
    operators: ['is', 'isNot'],
    defaultValue: 'fresh',
    options: [
      { value: 'fresh', label: 'Fresh' },
      { value: 'cex', label: 'Exchange' },
      { value: 'bridge', label: 'Bridge' },
      { value: 'cluster', label: 'Cluster' },
      { value: 'unknown', label: 'Unknown' },
    ],
  },
  { id: 'clusterSize', label: 'Cluster', category: 'identity', tier: 'wallet', valueType: 'integer', derivation: 'derived', operators: range, defaultValue: 3 },
  { id: 'smartMoney', label: 'Smart money', category: 'identity', tier: 'wallet', valueType: 'boolean', derivation: 'derived', operators: ['is'], defaultValue: true },
  { id: 'insiderLinked', label: 'Insider', category: 'identity', tier: 'wallet', valueType: 'boolean', derivation: 'derived', operators: ['is'], defaultValue: true },
  { id: 'hasLabel', label: 'Labelled', category: 'identity', tier: 'wallet', valueType: 'boolean', derivation: 'direct', operators: ['is'], defaultValue: true },

  { id: 'zeroedTokens', label: 'Zeroed', category: 'risk', tier: 'wallet', valueType: 'integer', derivation: 'direct', operators: ceiling, defaultValue: 0 },
  { id: 'honeypotInteractions', label: 'Honeypots', category: 'risk', tier: 'wallet', valueType: 'integer', derivation: 'direct', operators: ceiling, defaultValue: 0 },
  { id: 'rugExposure', label: 'Rug exposure', category: 'risk', tier: 'wallet', valueType: 'percent', derivation: 'derived', operators: ceiling, defaultValue: 20 },
  { id: 'avgPositionSize', label: 'Avg size', category: 'risk', tier: 'wallet', valueType: 'currency', derivation: 'direct', operators: range, defaultValue: 5000 },

  { id: 'lastActive', label: 'Last active', category: 'activity', tier: 'wallet', valueType: 'date', derivation: 'direct', operators: range, defaultValue: Date.UTC(2026, 7, 1) },
  { id: 'activeDays', label: 'Active days', category: 'activity', tier: 'wallet', valueType: 'integer', derivation: 'direct', operators: range, defaultValue: 5 },
  { id: 'firstSeen', label: 'First seen', category: 'activity', tier: 'wallet', valueType: 'date', derivation: 'direct', operators: ceiling, defaultValue: Date.UTC(2026, 0, 1) },
  { id: 'tradeSpanDays', label: 'Trade span', category: 'activity', tier: 'wallet', valueType: 'integer', derivation: 'direct', operators: range, defaultValue: 30 },
];

export const CHECK_BY_ID: Record<string, CheckDefinition> = Object.fromEntries(
  CHECKS.map((c) => [c.id, c])
);

/** Symbols rather than words: the operator sits inside a chip, where
 *  "at least" would double its width for no gain. */
export const OPERATOR_LABEL: Record<CheckOperator, string> = {
  gte: '≥',
  lte: '≤',
  is: 'is',
  isNot: 'is not',
};

/** Dates read badly as ≥ — they are after and before. */
export const DATE_OPERATOR_LABEL: Partial<Record<CheckOperator, string>> = {
  gte: 'after',
  lte: 'before',
};

export const QUANTIFIER_LABEL: Record<string, string> = {
  atLeast: 'at least',
  exactly: 'exactly',
  atMost: 'at most',
};
