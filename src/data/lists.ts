import type { TrendingToken, WatchlistItem, HistoryItem, ProjectDataset } from './types';
import { datasets } from './projects';

export { chainMeta, CHAINS } from './projects';

/* ============================================================
   Discovery, watchlist and history lists.

   All three are projections of the project registry, so a figure
   only ever has to be corrected in one place.
   ============================================================ */

/** Deterministic price path ending in the direction of the real 24h move. */
function spark(seed: number, change24h: number): number[] {
  let s = seed >>> 0;
  const rnd = () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296);
  const n = 16;
  const drift = Math.max(-1, Math.min(1, change24h / 60));
  const out: number[] = [];
  let v = 50 - drift * 22;
  for (let i = 0; i < n; i++) {
    v += drift * (44 / n) + (rnd() - 0.5) * 9;
    out.push(Math.max(4, Math.min(96, v)));
  }
  return out;
}

const SEEDS: Record<string, number> = { nockchain: 1201, sibyl: 1202, dot: 1203 };

function toTrending(d: ProjectDataset): TrendingToken {
  const p = d.project;
  return {
    id: p.id,
    name: p.name,
    ticker: p.ticker,
    chain: p.chain,
    logo: p.logo,
    monogram: p.monogram,
    price: p.metrics.price,
    change24h: p.metrics.priceChange24h,
    volume: p.metrics.volume24h,
    liquidity: p.metrics.liquidity,
    marketCap: p.metrics.marketCap,
    holders: p.metrics.holders,
    age: p.metrics.ageLabel,
    category: p.category,
    spark: spark(SEEDS[p.id] ?? 7, p.metrics.priceChange24h),
    researched: true,
  };
}

export const trending: TrendingToken[] = Object.values(datasets)
  .map(toTrending)
  .sort((a, b) => b.volume - a.volume);

/* ---------------- watchlist ---------------- */

const WATCH_META: Record<string, { riskDelta: number; lastResearched: string }> = {
  nockchain: { riskDelta: -4, lastResearched: '2h ago' },
  sibyl: { riskDelta: 6, lastResearched: '5h ago' },
  dot: { riskDelta: -2, lastResearched: '1d ago' },
};

export const watchlist: WatchlistItem[] = Object.values(datasets).map((d) => {
  const p = d.project;
  const m = WATCH_META[p.id];
  return {
    id: p.id,
    name: p.name,
    ticker: p.ticker,
    chain: p.chain,
    logo: p.logo,
    monogram: p.monogram,
    risk: p.scores.risk,
    riskLevel: p.scores.riskLevel,
    riskDelta: m.riskDelta,
    price: p.metrics.price,
    change24h: p.metrics.priceChange24h,
    liquidity: p.metrics.liquidity,
    lastResearched: m.lastResearched,
    spark: spark(SEEDS[p.id] ?? 7, p.metrics.priceChange24h),
  };
});

/* ---------------- research history ---------------- */

/* `iso` exists only to sort — the display string is `date`. */
const HISTORY_META: Record<
  string,
  { iso: string; date: string; time: string; status: HistoryItem['status'] }[]
> = {
  nockchain: [
    { iso: '2026-09-09', date: '09 Sep 2026', time: '14:22', status: 'complete' },
    { iso: '2026-09-02', date: '02 Sep 2026', time: '09:41', status: 'stale' },
  ],
  sibyl: [
    { iso: '2026-09-09', date: '09 Sep 2026', time: '11:08', status: 'complete' },
    { iso: '2026-08-28', date: '28 Aug 2026', time: '17:53', status: 'stale' },
  ],
  dot: [
    { iso: '2026-09-08', date: '08 Sep 2026', time: '19:36', status: 'partial' },
    { iso: '2026-08-31', date: '31 Aug 2026', time: '13:12', status: 'complete' },
  ],
};

export const history: HistoryItem[] = Object.values(datasets)
  .flatMap((d) => {
    const p = d.project;
    return (HISTORY_META[p.id] ?? []).map((h) => ({
      id: p.id,
      name: p.name,
      ticker: p.ticker,
      chain: p.chain,
      logo: p.logo,
      monogram: p.monogram,
      date: h.date,
      time: h.time,
      risk: p.scores.risk,
      riskLevel: p.scores.riskLevel,
      confidence: p.scores.confidence,
      category: p.category,
      status: h.status,
      sortKey: `${h.iso} ${h.time}`,
    }));
  })
  .sort((a, b) => b.sortKey.localeCompare(a.sortKey))
  .map(({ sortKey: _sortKey, ...rest }) => rest);
