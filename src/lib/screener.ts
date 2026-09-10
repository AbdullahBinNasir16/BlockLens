import type {
  AppliedCheck,
  CheckOperator,
  CheckValue,
  FunnelStage,
  ScreenerQuery,
  ScreenerResult,
  WalletMatch,
  WalletProjectPosition,
  WalletRecord,
} from '../data/types';
import { CHECK_BY_ID } from '../data/checks';
import { CORPUS_NOW } from '../data/wallets';
import { datasets } from '../data/projects';

/* ============================================================
   BACKEND SEAM

   `evaluateQuery` is the single call site a real backend replaces. It is
   pure: a query and a corpus in, a result out, no imports from the UI and
   no reads of the clock. Swapping it for a network call means changing
   this file and nothing else — the route already treats the result as
   opaque and renders whatever comes back.

   Every check is a metric plus a comparison. Metrics live in the two
   lookups below, keyed by check id, so adding a check is one entry in
   `data/checks.ts` and one entry here. No component changes.

   Scope arrives as contract addresses on one chain, because that is how
   the user enters it. Positions are keyed by project id, so the contracts
   are resolved through the registry here — a backend would resolve them
   against its own token index instead.

   Windowing note: positions are stored whole, not as individual trades,
   so a position counts when its activity range overlaps the date window.
   A backend holding per-trade records would instead compute PnL from the
   trades inside the window and could split a position across it. That is
   the one place this evaluator is coarser than the real thing.
   ============================================================ */

/** project id → lowercase contract, built once */
const CONTRACT_OF: Record<string, string> = Object.fromEntries(
  Object.values(datasets).map((d) => [d.project.id, d.project.contract.toLowerCase()])
);

const MINUTE = 60_000;
const DAY = 24 * 60 * MINUTE;

export interface MetricCtx {
  from: number;
  to: number;
  now: number;
}

/* ---------------- position arithmetic ----------------
   Nothing below reads a stored PnL. Every figure is recomputed from what
   moved, which is what keeps the prototype honest about its own maths. */

export const realizedPnl = (p: WalletProjectPosition) =>
  p.proceeds - p.invested * p.soldFraction;

export const unrealizedPnl = (p: WalletProjectPosition) =>
  p.remainingValue - p.invested * (1 - p.soldFraction);

export const totalPnl = (p: WalletProjectPosition) => realizedPnl(p) + unrealizedPnl(p);

export const roiMultiple = (p: WalletProjectPosition) =>
  p.invested > 0 ? (p.proceeds + p.remainingValue) / p.invested : 0;

export const holdingMinutes = (p: WalletProjectPosition, now: number) =>
  Math.max(0, ((p.lastSell ?? now) - p.firstBuy) / MINUTE);

/** A position counts toward win rate once it has realised something. An
 *  untouched open position is not yet a win or a loss. */
export const isRealised = (p: WalletProjectPosition) => p.soldFraction > 0;

export const isWin = (p: WalletProjectPosition) => isRealised(p) && realizedPnl(p) > 0;

export const lastActivity = (p: WalletProjectPosition) => p.lastSell ?? p.firstBuy;

function median(xs: number[]): number {
  if (!xs.length) return 0;
  const s = [...xs].sort((a, b) => a - b);
  const mid = s.length >> 1;
  return s.length % 2 ? s[mid] : (s[mid - 1] + s[mid]) / 2;
}

/* ---------------- metrics ---------------- */

type ProjectMetric = (
  p: WalletProjectPosition,
  w: WalletRecord,
  ctx: MetricCtx
) => number | boolean | string;

type WalletMetric = (
  ps: WalletProjectPosition[],
  w: WalletRecord,
  ctx: MetricCtx
) => number | boolean | string;

export const PROJECT_METRICS: Record<string, ProjectMetric> = {
  realizedPnl: (p) => realizedPnl(p),
  unrealizedPnl: (p) => unrealizedPnl(p),
  roiMultiple: (p) => roiMultiple(p),
  holdingTime: (p, _w, ctx) => holdingMinutes(p, ctx.now),
  entryDelay: (p) => p.entryDelay / MINUTE,
  buyCount: (p) => p.buys,
  sellCount: (p) => p.sells,
  partialExitRatio: (p) => p.soldFraction * 100,
  averagedDown: (p) => p.averagedDown,
  /* only a fully closed position is a round trip — a partial exit has not
     completed the loop, however fast the first sell was */
  roundTripUnder: (p, _w, ctx) =>
    p.soldFraction >= 0.999 ? holdingMinutes(p, ctx.now) : Number.POSITIVE_INFINITY,
  soldFirstPump: (p) => p.soldFirstPump,
};

export const WALLET_METRICS: Record<string, WalletMetric> = {
  walletRealizedPnl: (ps) => ps.reduce((a, p) => a + realizedPnl(p), 0),
  winRate: (ps) => {
    const closed = ps.filter(isRealised);
    return closed.length ? (closed.filter(isWin).length / closed.length) * 100 : 0;
  },
  bestTradeMultiple: (ps) => (ps.length ? Math.max(...ps.map(roiMultiple)) : 0),
  medianTradePnl: (ps) => median(ps.filter(isRealised).map(realizedPnl)),
  totalVolume: (ps) => ps.reduce((a, p) => a + p.invested + p.proceeds, 0),
  lossCount: (ps) => ps.filter((p) => isRealised(p) && realizedPnl(p) <= 0).length,

  avgHoldingTime: (ps, _w, ctx) =>
    ps.length ? ps.reduce((a, p) => a + holdingMinutes(p, ctx.now), 0) / ps.length : 0,
  medianHoldingTime: (ps, _w, ctx) => median(ps.map((p) => holdingMinutes(p, ctx.now))),
  minHoldingTime: (ps, _w, ctx) =>
    ps.length ? Math.min(...ps.map((p) => holdingMinutes(p, ctx.now))) : 0,
  maxHoldingTime: (ps, _w, ctx) =>
    ps.length ? Math.max(...ps.map((p) => holdingMinutes(p, ctx.now))) : 0,

  distinctProjects: (ps) => new Set(ps.map((p) => p.projectId)).size,
  pnlConcentration: (ps) => {
    const gains = ps.map(totalPnl).filter((v) => v > 0);
    const sum = gains.reduce((a, v) => a + v, 0);
    return sum > 0 ? (Math.max(...gains) / sum) * 100 : 0;
  },
  newPositions: (ps, _w, ctx) =>
    ps.filter((p) => p.firstBuy >= ctx.from && p.firstBuy <= ctx.to).length,

  walletAgeAtFirstBuy: (ps, w) => {
    if (!ps.length) return 0;
    const first = Math.min(...ps.map((p) => p.firstBuy));
    return Math.max(0, (first - w.firstSeen) / MINUTE);
  },
  fundingSource: (_ps, w) => w.fundingSource,
  clusterSize: (_ps, w) => w.clusterSize,
  smartMoney: (_ps, w) => w.smartMoney,
  insiderLinked: (_ps, w) => w.insiderLinked,
  hasLabel: (_ps, w) => Boolean(w.label || w.ens),

  zeroedTokens: (ps) => ps.filter((p) => p.wentToZero).length,
  honeypotInteractions: (ps) => ps.filter((p) => p.honeypot).length,
  rugExposure: (ps) => {
    const total = ps.reduce((a, p) => a + p.invested, 0);
    const rugged = ps.filter((p) => p.wentToZero || p.honeypot).reduce((a, p) => a + p.invested, 0);
    return total > 0 ? (rugged / total) * 100 : 0;
  },
  avgPositionSize: (ps) => (ps.length ? ps.reduce((a, p) => a + p.invested, 0) / ps.length : 0),

  lastActive: (ps) => (ps.length ? Math.max(...ps.map(lastActivity)) : 0),
  activeDays: (ps) => {
    /* buys and sells are the only timestamps stored, so a "day with a trade"
       is a day carrying one of those two */
    const days = new Set<number>();
    for (const p of ps) {
      days.add(Math.floor(p.firstBuy / DAY));
      if (p.lastSell !== null) days.add(Math.floor(p.lastSell / DAY));
    }
    return days.size;
  },
  firstSeen: (_ps, w) => w.firstSeen,
  tradeSpanDays: (ps) => {
    if (!ps.length) return 0;
    const first = Math.min(...ps.map((p) => p.firstBuy));
    const last = Math.max(...ps.map(lastActivity));
    return Math.round((last - first) / DAY);
  },
};

/* ---------------- comparison ---------------- */

export function compare(op: CheckOperator, actual: CheckValue, target: CheckValue): boolean {
  switch (op) {
    case 'gte':
      return Number(actual) >= Number(target);
    case 'lte':
      return Number(actual) <= Number(target);
    case 'is':
      return actual === target;
    case 'isNot':
      return actual !== target;
    default:
      return true;
  }
}

/** The value a check sees for one position. Exported so the wallet drawer
 *  can show pass/fail per check without duplicating the maths. */
export function projectCheckValue(
  check: AppliedCheck,
  p: WalletProjectPosition,
  w: WalletRecord,
  ctx: MetricCtx
): CheckValue | undefined {
  return PROJECT_METRICS[check.checkId]?.(p, w, ctx);
}

export function walletCheckValue(
  check: AppliedCheck,
  ps: WalletProjectPosition[],
  w: WalletRecord,
  ctx: MetricCtx
): CheckValue | undefined {
  return WALLET_METRICS[check.checkId]?.(ps, w, ctx);
}

const testProject = (
  check: AppliedCheck,
  p: WalletProjectPosition,
  w: WalletRecord,
  ctx: MetricCtx
) => {
  const v = projectCheckValue(check, p, w, ctx);
  /* an unknown check id must not silently pass — that would let a broken
     query look like a working one */
  return v === undefined ? false : compare(check.operator, v, check.value);
};

const testWallet = (
  check: AppliedCheck,
  ps: WalletProjectPosition[],
  w: WalletRecord,
  ctx: MetricCtx
) => {
  const v = walletCheckValue(check, ps, w, ctx);
  return v === undefined ? false : compare(check.operator, v, check.value);
};

export function quantifierHolds(q: string, count: number, target: number): boolean {
  if (q === 'atLeast') return count >= target;
  if (q === 'atMost') return count <= target;
  return count === target;
}

/* ---------------- scope ---------------- */

/** A position is in scope when its project's contract was added, it sits
 *  on the searched chain, and its activity range overlaps the window. */
function inScope(p: WalletProjectPosition, q: ScreenerQuery, wanted: Set<string>): boolean {
  if (p.chain !== q.scope.chain) return false;
  if (!wanted.has(CONTRACT_OF[p.projectId])) return false;
  const start = p.firstBuy;
  const end = p.lastSell ?? CORPUS_NOW;
  return end >= q.scope.from && start <= q.scope.to;
}

const contractSet = (q: ScreenerQuery) =>
  new Set(q.scope.contracts.map((c) => c.trim().toLowerCase()));

/* ---------------- evaluation ---------------- */

interface Candidate {
  wallet: WalletRecord;
  positions: WalletProjectPosition[];
  matched: string[];
}

export function evaluateQuery(query: ScreenerQuery, corpus: WalletRecord[]): ScreenerResult {
  const ctx: MetricCtx = { from: query.scope.from, to: query.scope.to, now: CORPUS_NOW };
  const wanted = contractSet(query);
  const rule = query.projectRule;
  const funnel: FunnelStage[] = [];

  funnel.push({ id: 'population', label: 'Wallets', remaining: corpus.length, removed: 0 });

  let candidates: Candidate[] = [];
  for (const wallet of corpus) {
    const positions = wallet.positions.filter((p) => inScope(p, query, wanted));
    if (positions.length) {
      candidates.push({
        wallet,
        positions,
        matched: [...new Set(positions.map((p) => p.projectId))],
      });
    }
  }

  funnel.push({
    id: 'scope',
    label: 'In scope',
    remaining: candidates.length,
    removed: corpus.length - candidates.length,
  });
  const scopedWallets = candidates.length;

  /* The rule only runs when a per-project filter is on. With none, it
     would count projects traded — which the Projects filter already asks,
     more plainly. */
  if (rule.checks.length) {
    const before = candidates.length;
    const next: Candidate[] = [];
    for (const c of candidates) {
      /* Distinct projects, not positions. Two qualifying re-entries into the
         same token are still one project passing the rule. */
      const matched = [
        ...new Set(
          c.positions
            .filter((p) => rule.checks.every((chk) => testProject(chk, p, c.wallet, ctx)))
            .map((p) => p.projectId)
        ),
      ];
      if (quantifierHolds(rule.quantifier, matched.length, rule.count)) {
        next.push({ ...c, matched });
      }
    }
    candidates = next;
    funnel.push({
      id: 'rule',
      label: 'Project rule',
      remaining: candidates.length,
      removed: before - candidates.length,
    });
  }

  /* Wallet filters run in the order they were switched on, so the funnel
     attributes each drop to the filter the user chose. */
  for (const check of query.walletChecks) {
    const before = candidates.length;
    candidates = candidates.filter((c) => testWallet(check, c.positions, c.wallet, ctx));
    funnel.push({
      id: `check:${check.checkId}`,
      label: CHECK_BY_ID[check.checkId]?.label ?? check.checkId,
      remaining: candidates.length,
      removed: before - candidates.length,
    });
  }

  const matches: WalletMatch[] = candidates.map((c) => {
    return {
      wallet: c.wallet,
      matchedProjects: c.matched,
      realizedPnl: WALLET_METRICS.walletRealizedPnl(c.positions, c.wallet, ctx) as number,
      winRate: WALLET_METRICS.winRate(c.positions, c.wallet, ctx) as number,
      avgHoldingTime: WALLET_METRICS.avgHoldingTime(c.positions, c.wallet, ctx) as number,
      lastActive: WALLET_METRICS.lastActive(c.positions, c.wallet, ctx) as number,
      projectsTraded: new Set(c.positions.map((p) => p.projectId)).size,
    };
  });

  matches.sort((a, b) => b.realizedPnl - a.realizedPnl);

  /* The stage that first emptied the set is the one worth naming in the
     zero state — later stages had nothing left to remove. */
  const limitingStage =
    matches.length === 0 ? funnel.find((s) => s.remaining === 0 && s.removed > 0) : undefined;

  return { matches, funnel, limitingStage, scopedWallets };
}

/** In-scope positions for one wallet — the drawer needs the same slice the
 *  evaluator used, or its per-check readout would disagree with the table. */
export function scopedPositions(
  wallet: WalletRecord,
  query: ScreenerQuery
): WalletProjectPosition[] {
  const wanted = contractSet(query);
  return wallet.positions.filter((p) => inScope(p, query, wanted));
}
