import type { Trade, TradeKind } from '../data/types';
import { BOOK_NOW, GATE, INCEPTION, RISK_TIGHTENED_AT, START_CAPITAL, TRADES } from '../data/portfolio';
import { seeded } from '../data/synth';

/* ============================================================
   Book arithmetic.

   Everything the Portfolio page states about performance is computed
   here from the trade records — nothing is stored. If a headline number
   is wrong, it is wrong because a trade is wrong, and the trade is on the
   same page to be checked.
   ============================================================ */

export const DAY = 24 * 60 * 60 * 1000;

export const isOpen = (t: Trade) => t.exitAt === null;
export const multiple = (t: Trade) => t.lastPrice / t.entryPrice;
export const tradeReturn = (t: Trade) => multiple(t) - 1;
export const tradePnl = (t: Trade) => t.size * tradeReturn(t);
export const isWin = (t: Trade) => !isOpen(t) && t.lastPrice > t.entryPrice;
export const heldDays = (t: Trade) => ((t.exitAt ?? BOOK_NOW) - t.entryAt) / DAY;

/* ---------------- price paths ----------------
   The book stores entry, exit and peak — not every tick. The path between
   them is a seeded Brownian bridge in log space, pinned at 1× on entry, at
   the recorded peak, and at the recorded exit, so it is honest to the
   three numbers that matter and deterministic everywhere else. */

function hash(s: string) {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 16777619) >>> 0;
  }
  return h;
}

function bridge(n: number, from: number, to: number, sigma: number, r: () => number): number[] {
  if (n <= 1) return [to];
  const walk = [0];
  for (let i = 1; i < n; i++) walk.push(walk[i - 1] + sigma * (r() * 2 - 1));
  const last = walk[n - 1];
  return walk.map((w, i) => {
    const f = i / (n - 1);
    return from + (to - from) * f + (w - last * f);
  });
}

const VOL: Record<TradeKind, number> = { meme: 0.16, ai: 0.07, infra: 0.05, defi: 0.04 };

const PATHS = new Map<string, number[]>();

/** Daily multiples of entry, from the day of entry to exit (or now). */
export function tradePath(t: Trade): number[] {
  const cached = PATHS.get(t.id);
  if (cached) return cached;

  const r = seeded(hash(t.id));
  const days = Math.max(2, Math.ceil(heldDays(t)) + 1);
  const peakLog = Math.log(t.peak);
  const endLog = Math.log(multiple(t));
  /* memes peak early, everything else later */
  const frac = t.kind === 'meme' ? 0.18 + r() * 0.35 : 0.35 + r() * 0.45;
  const k = Math.max(1, Math.min(days - 2, Math.round((days - 1) * frac)));

  const up = bridge(k + 1, 0, peakLog, VOL[t.kind], r);
  const down = bridge(days - k, peakLog, endLog, VOL[t.kind], r);
  /* The recorded peak is the ceiling — noise never invents a higher one.
     Overshoot is reflected back below it rather than clamped, because a
     clamp draws a flat shelf along the peak that no real chart has. */
  const logs = [...up, ...down.slice(1)].map((v) => (v > peakLog ? peakLog - (v - peakLog) : v));
  logs[0] = 0;
  logs[k] = peakLog;
  logs[logs.length - 1] = endLog;

  const path = logs.map((v) => Math.exp(v));
  PATHS.set(t.id, path);
  return path;
}

/** The position's multiple on a given day. At or after the position's
 *  last moment it is the recorded mark exactly — the path's final step is
 *  a part-day, and reading it by whole days would stop one sample short. */
function multipleOn(t: Trade, when: number): number {
  if (when >= (t.exitAt ?? BOOK_NOW)) return multiple(t);
  const path = tradePath(t);
  const i = Math.floor((when - t.entryAt) / DAY);
  return path[Math.max(0, Math.min(path.length - 1, i))];
}

/* ---------------- equity ---------------- */

export interface EquityPoint {
  t: number;
  v: number;
}

function equityAt(when: number): number {
  let v = START_CAPITAL;
  for (const t of TRADES) {
    if (t.entryAt > when) continue;
    if (t.exitAt !== null && t.exitAt <= when) v += tradePnl(t);
    else v += t.size * (multipleOn(t, when) - 1);
  }
  return v;
}

/** One point a day from inception, then one at "now". */
export const EQUITY: EquityPoint[] = (() => {
  const out: EquityPoint[] = [];
  for (let d = INCEPTION; d < BOOK_NOW; d += DAY) out.push({ t: d, v: equityAt(d) });
  out.push({ t: BOOK_NOW, v: equityAt(BOOK_NOW) });
  return out;
})();

/* ---------------- headline ---------------- */

export interface BookStats {
  value: number;
  ret: number;
  realized: number;
  unrealized: number;
  closed: number;
  wins: number;
  winRate: number;
  open: number;
  avgHoldDays: number;
  best: Trade;
  worst: Trade;
  maxDrawdown: number;
  lastEntry: Trade;
}

export function bookStats(): BookStats {
  const closed = TRADES.filter((t) => !isOpen(t));
  const open = TRADES.filter(isOpen);
  const wins = closed.filter(isWin).length;
  const realized = closed.reduce((a, t) => a + tradePnl(t), 0);
  const unrealized = open.reduce((a, t) => a + tradePnl(t), 0);
  const value = START_CAPITAL + realized + unrealized;

  let peak = -Infinity;
  let maxDrawdown = 0;
  for (const p of EQUITY) {
    peak = Math.max(peak, p.v);
    maxDrawdown = Math.max(maxDrawdown, (peak - p.v) / peak);
  }

  const byReturn = [...TRADES].sort((a, b) => tradeReturn(b) - tradeReturn(a));
  return {
    value,
    ret: value / START_CAPITAL - 1,
    realized,
    unrealized,
    closed: closed.length,
    wins,
    winRate: closed.length ? wins / closed.length : 0,
    open: open.length,
    avgHoldDays: closed.reduce((a, t) => a + heldDays(t), 0) / (closed.length || 1),
    best: byReturn[0],
    worst: byReturn[byReturn.length - 1],
    maxDrawdown,
    lastEntry: [...TRADES].sort((a, b) => b.entryAt - a.entryAt)[0],
  };
}

/* ---------------- by kind ---------------- */

export interface KindRow {
  kind: TradeKind;
  trades: number;
  closed: number;
  wins: number;
  pnl: number;
}

export function byKind(): KindRow[] {
  const kinds: TradeKind[] = ['meme', 'ai', 'infra', 'defi'];
  return kinds.map((kind) => {
    const ts = TRADES.filter((t) => t.kind === kind);
    const closed = ts.filter((t) => !isOpen(t));
    return {
      kind,
      trades: ts.length,
      closed: closed.length,
      wins: closed.filter(isWin).length,
      pnl: ts.reduce((a, t) => a + tradePnl(t), 0),
    };
  });
}

/* ---------------- by month ---------------- */

export interface MonthRow {
  start: number;
  end: number;
  ret: number;
}

export function byMonth(): MonthRow[] {
  const out: MonthRow[] = [];
  const first = new Date(INCEPTION);
  let y = first.getUTCFullYear();
  let m = first.getUTCMonth();
  for (;;) {
    const start = Math.max(INCEPTION, Date.UTC(y, m, 1));
    if (start >= BOOK_NOW) break;
    const end = Math.min(BOOK_NOW, Date.UTC(y, m + 1, 1));
    const a = equityAt(start);
    out.push({ start, end, ret: equityAt(end) / a - 1 });
    m++;
    if (m > 11) {
      m = 0;
      y++;
    }
  }
  return out;
}

/* ---------------- the gate, as it stood ---------------- */

export interface GateCheck {
  id: string;
  label: string;
  value: number;
  limit: number;
  /** 'min' passes at or above the limit, 'max' at or below */
  side: 'min' | 'max';
  pass: boolean;
  /** 0-100 scale for drawing */
  scale: number;
}

/** Every criterion the trade had to clear, with the limit in force on the
 *  day it was bought — the memecoin risk ceiling moved in June, and a
 *  January trade is judged by January's rule. */
export function gateChecks(t: Trade): GateCheck[] {
  const riskCap = t.kind === 'meme' && t.entryAt >= RISK_TIGHTENED_AT ? GATE.maxRiskMeme : GATE.maxRisk;
  const rows: GateCheck[] = [
    {
      id: 'age',
      label: 'Age at entry',
      value: t.gate.ageHours,
      limit: GATE.maxAgeHours,
      side: 'max',
      pass: t.gate.ageHours <= GATE.maxAgeHours,
      scale: 72,
    },
    {
      id: 'confidence',
      label: 'Confidence',
      value: t.gate.confidence,
      limit: GATE.minConfidence,
      side: 'min',
      pass: t.gate.confidence >= GATE.minConfidence,
      scale: 100,
    },
    {
      id: 'risk',
      label: 'Risk',
      value: t.gate.risk,
      limit: riskCap,
      side: 'max',
      pass: t.gate.risk <= riskCap,
      scale: 100,
    },
    {
      id: 'liquidity',
      label: 'Liquidity',
      value: t.gate.liquidity,
      limit: GATE.minLiquidity,
      side: 'min',
      pass: t.gate.liquidity >= GATE.minLiquidity,
      scale: 250_000,
    },
  ];
  if (t.kind === 'meme') {
    rows.push({
      id: 'lore',
      label: 'Lore',
      value: t.gate.lore,
      limit: GATE.minLore,
      side: 'min',
      pass: t.gate.lore >= GATE.minLore,
      scale: 100,
    });
  }
  return rows;
}
