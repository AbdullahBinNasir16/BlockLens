import type { Chain, FundingSource, WalletProjectPosition, WalletRecord } from './types';
import { seeded } from './synth';
import { datasets } from './projects';

/* ============================================================
   Screener corpus — 400 synthetic wallets.

   These wallets are generated, not observed. Nothing here is a claim
   about any real address; the section carries a Sample chip saying so.

   The generator stores only what actually moved — spent, taken out,
   still held, and the timestamps around it. PnL, win rate and holding
   time are never written down. The screener derives them from these
   positions the same way a backend would, which is the point: if the
   evaluation is wrong, it is wrong here too, where it can be seen.

   Seeded and deterministic, so every reload and every viewer sees the
   same corpus and the acceptance query returns the same set.
   ============================================================ */

/** The corpus reference clock. Fixed rather than `Date.now()` so results
 *  never drift — a screener that returns different rows tomorrow for the
 *  same query is untestable. Matches the snapshot date on the projects. */
export const CORPUS_NOW = Date.UTC(2026, 8, 9, 12, 0, 0);

const MINUTE = 60_000;
const DAY = 24 * 60 * MINUTE;

/** Pair-creation dates, taken from the project records. Entry delay is
 *  measured from these. */
const LAUNCH: Record<string, number> = {
  nockchain: Date.UTC(2025, 11, 22),
  sibyl: Date.UTC(2026, 2, 18),
  dot: Date.UTC(2026, 4, 27),
};

const PROJECT_IDS = Object.keys(datasets);

/* ---------------- distributions ---------------- */

/** Box–Muller, driven by the seeded stream so it stays deterministic. */
function gauss(rnd: () => number): number {
  const u = Math.max(1e-9, rnd());
  const v = rnd();
  return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v);
}

/** Log-normal draw. Holding times and position sizes are both heavily
 *  right-skewed in reality, which is what makes a median useful. */
function logNormal(rnd: () => number, median: number, sigma: number): number {
  return Math.exp(Math.log(median) + sigma * gauss(rnd));
}

const between = (rnd: () => number, lo: number, hi: number) => lo + rnd() * (hi - lo);

const pick = <T,>(rnd: () => number, xs: readonly T[]): T => xs[Math.floor(rnd() * xs.length) % xs.length];

/* ---------------- archetypes ----------------
   Weights sum to 400. The mix is deliberately unkind: most wallets lose,
   a thin tail wins big, and there is a visible knot of sub-minute
   round-trippers so the sniper checks have something to find. */

interface Archetype {
  id: string;
  weight: number;
  /** distinct projects traded */
  projects: [number, number];
  /** median holding time in minutes, and its log-normal spread */
  holdMedian: number;
  holdSigma: number;
  /** probability a closed position ended up */
  winP: number;
  /** median USD committed per position */
  sizeMedian: number;
  sizeSigma: number;
  roiWin: [number, number];
  roiLoss: [number, number];
  /** chance a position is still open */
  openP: number;
  /** chance a realised position was only partly sold */
  partialP: number;
  smartP: number;
  insiderP: number;
  funding: readonly FundingSource[];
  /** wallet age in days before its first buy */
  ageDays: [number, number];
  /** entered close to launch */
  earlyP: number;
}

const ARCHETYPES: Archetype[] = [
  {
    id: 'sniper',
    weight: 50,
    projects: [1, 3],
    holdMedian: 0.9,
    holdSigma: 1.15,
    winP: 0.33,
    sizeMedian: 1_500,
    sizeSigma: 0.8,
    roiWin: [1.08, 2.2],
    roiLoss: [0.35, 0.96],
    openP: 0.02,
    partialP: 0.08,
    smartP: 0.04,
    insiderP: 0.02,
    funding: ['fresh', 'fresh', 'cluster', 'unknown'],
    ageDays: [0, 14],
    earlyP: 0.8,
  },
  {
    id: 'flipper',
    weight: 100,
    projects: [1, 4],
    holdMedian: 95,
    holdSigma: 1.3,
    winP: 0.35,
    sizeMedian: 2_400,
    sizeSigma: 0.9,
    roiWin: [1.15, 3.1],
    roiLoss: [0.3, 0.94],
    openP: 0.12,
    partialP: 0.3,
    smartP: 0.05,
    insiderP: 0.01,
    funding: ['cex', 'fresh', 'bridge', 'unknown'],
    ageDays: [3, 400],
    earlyP: 0.35,
  },
  {
    id: 'swing',
    weight: 110,
    projects: [1, 3],
    holdMedian: 2_600,
    holdSigma: 1.2,
    winP: 0.34,
    sizeMedian: 3_400,
    sizeSigma: 1.0,
    roiWin: [1.2, 4.0],
    roiLoss: [0.25, 0.92],
    openP: 0.25,
    partialP: 0.35,
    smartP: 0.06,
    insiderP: 0.01,
    funding: ['cex', 'cex', 'bridge', 'unknown'],
    ageDays: [20, 900],
    earlyP: 0.18,
  },
  {
    id: 'holder',
    weight: 70,
    projects: [1, 2],
    holdMedian: 19_000,
    holdSigma: 0.95,
    winP: 0.31,
    sizeMedian: 3_900,
    sizeSigma: 1.0,
    roiWin: [1.3, 6.0],
    roiLoss: [0.12, 0.9],
    openP: 0.55,
    partialP: 0.22,
    smartP: 0.08,
    insiderP: 0.01,
    funding: ['cex', 'bridge', 'unknown'],
    ageDays: [60, 1400],
    earlyP: 0.2,
  },
  {
    id: 'whale',
    weight: 22,
    projects: [1, 3],
    holdMedian: 4_200,
    holdSigma: 1.1,
    winP: 0.45,
    sizeMedian: 58_000,
    sizeSigma: 0.8,
    roiWin: [1.25, 3.4],
    roiLoss: [0.42, 0.96],
    openP: 0.35,
    partialP: 0.42,
    smartP: 0.25,
    insiderP: 0.03,
    funding: ['cex', 'bridge', 'cluster'],
    ageDays: [90, 1600],
    earlyP: 0.25,
  },
  {
    id: 'pro',
    weight: 28,
    projects: [2, 3],
    holdMedian: 2_100,
    holdSigma: 1.0,
    winP: 0.8,
    sizeMedian: 9_000,
    sizeSigma: 0.7,
    roiWin: [1.6, 5.0],
    roiLoss: [0.55, 0.95],
    openP: 0.12,
    partialP: 0.35,
    smartP: 0.5,
    insiderP: 0.02,
    funding: ['cex', 'bridge', 'cluster'],
    ageDays: [120, 1700],
    earlyP: 0.3,
  },
  {
    id: 'insider',
    weight: 12,
    projects: [1, 2],
    holdMedian: 5_600,
    holdSigma: 1.0,
    winP: 0.85,
    sizeMedian: 12_000,
    sizeSigma: 0.7,
    roiWin: [2.0, 9.0],
    roiLoss: [0.6, 0.96],
    openP: 0.2,
    partialP: 0.4,
    smartP: 0.3,
    insiderP: 1,
    funding: ['cluster', 'fresh'],
    ageDays: [0, 30],
    earlyP: 0.95,
  },
  {
    id: 'dormant',
    weight: 8,
    projects: [1, 1],
    holdMedian: 30_000,
    holdSigma: 0.8,
    winP: 0.25,
    sizeMedian: 800,
    sizeSigma: 0.9,
    roiWin: [1.1, 1.8],
    roiLoss: [0.02, 0.6],
    openP: 0.4,
    partialP: 0.1,
    smartP: 0,
    insiderP: 0,
    funding: ['fresh', 'unknown'],
    ageDays: [200, 1500],
    earlyP: 0.1,
  },
];

/* ---------------- generation ---------------- */

const HEX = '0123456789abcdef';

function address(rnd: () => number): string {
  let s = '0x';
  for (let i = 0; i < 40; i++) s += HEX[Math.floor(rnd() * 16)];
  return s;
}

const ENS_WORDS = [
  'ember', 'lattice', 'harbor', 'quartz', 'meridian', 'cobalt', 'vellum', 'sable',
  'nimbus', 'onyx', 'flint', 'tessera', 'cinder', 'aurum', 'basalt', 'corvid',
];

const LABELS = [
  'Early buyer', 'Long holder', 'Rotator', 'Known cluster', 'Market maker',
  'Accumulator', 'Quick seller', 'Bridge relay',
];

function buildPosition(
  rnd: () => number,
  a: Archetype,
  projectId: string,
  chain: Chain
): WalletProjectPosition {
  const launch = LAUNCH[projectId] ?? CORPUS_NOW - 200 * DAY;
  const live = CORPUS_NOW - launch;

  const holdMinutes = Math.max(0.2, logNormal(rnd, a.holdMedian, a.holdSigma));
  const holdMs = holdMinutes * MINUTE;

  /* Entry is biased toward the recent half of the project's life — most
     wallets in a corpus are late, and it keeps the default 90-day window
     populated rather than empty. */
  const early = rnd() < a.earlyP;
  const frac = early ? Math.pow(rnd(), 3) * 0.12 : Math.pow(rnd(), 0.6);
  const maxStart = Math.max(0, live - holdMs);
  const firstBuy = launch + Math.min(maxStart, frac * live);

  const open = rnd() < a.openP;
  const won = rnd() < a.winP;
  const roi = won ? between(rnd, a.roiWin[0], a.roiWin[1]) : between(rnd, a.roiLoss[0], a.roiLoss[1]);

  const soldFraction = open ? 0 : rnd() < a.partialP ? between(rnd, 0.25, 0.85) : 1;
  const lastSell = soldFraction > 0 ? firstBuy + holdMs : null;

  const invested = Math.round(logNormal(rnd, a.sizeMedian, a.sizeSigma));
  const proceeds = Math.round(invested * soldFraction * roi);
  const remainingValue = Math.round(invested * (1 - soldFraction) * roi);

  const buys = 1 + Math.floor(rnd() * (a.holdMedian > 500 ? 4 : 2));
  const sells = soldFraction === 0 ? 0 : 1 + Math.floor(rnd() * (soldFraction < 1 ? 3 : 2));

  return {
    projectId,
    chain,
    firstBuy: Math.round(firstBuy),
    lastSell: lastSell === null ? null : Math.round(lastSell),
    buys,
    sells,
    invested,
    soldFraction: Number(soldFraction.toFixed(3)),
    proceeds,
    remainingValue,
    entryDelay: Math.round(firstBuy - launch),
    averagedDown: buys > 1 && rnd() < 0.35,
    soldFirstPump: soldFraction > 0 && holdMinutes < 240 && rnd() < 0.45,
    wentToZero: roi < 0.06,
    honeypot: rnd() < 0.02,
  };
}

function buildCorpus(): WalletRecord[] {
  const rnd = seeded(90_452_117);
  const out: WalletRecord[] = [];

  for (const a of ARCHETYPES) {
    for (let i = 0; i < a.weight; i++) {
      const count = Math.min(
        PROJECT_IDS.length,
        Math.round(between(rnd, a.projects[0], a.projects[1]))
      );

      /* pick without replacement so a wallet never holds one project twice */
      const pool = [...PROJECT_IDS];
      const chosen: string[] = [];
      for (let k = 0; k < count && pool.length; k++) {
        chosen.push(pool.splice(Math.floor(rnd() * pool.length), 1)[0]);
      }

      const positions = chosen.map((id) =>
        buildPosition(rnd, a, id, datasets[id].project.chain)
      );

      const earliestBuy = Math.min(...positions.map((p) => p.firstBuy));
      const ageDays = between(rnd, a.ageDays[0], a.ageDays[1]);

      const named = rnd() < 0.12;
      out.push({
        address: address(rnd),
        label: named && rnd() < 0.5 ? pick(rnd, LABELS) : undefined,
        ens: named && rnd() < 0.6 ? `${pick(rnd, ENS_WORDS)}.eth` : undefined,
        firstSeen: Math.round(earliestBuy - ageDays * DAY),
        fundingSource: pick(rnd, a.funding),
        clusterSize: rnd() < 0.22 ? 2 + Math.floor(rnd() * 6) : 1,
        smartMoney: rnd() < a.smartP,
        insiderLinked: rnd() < a.insiderP,
        positions,
      });
    }
  }

  return out;
}

export const WALLET_CORPUS: WalletRecord[] = buildCorpus();

/** Only the archetype mix is worth stating in the UI — the labels
 *  themselves are not exposed, since a real corpus would not come
 *  pre-sorted into tidy behavioural buckets. */
export const CORPUS_NOTE =
  '400 generated wallets holding real position records. PnL, win rate and holding ' +
  'time are computed from those positions, never stored — the screener filters the ' +
  'way a backend would. No address here corresponds to a real wallet.';
