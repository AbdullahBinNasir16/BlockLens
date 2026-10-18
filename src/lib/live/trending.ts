/* ============================================================
   Live Base trending — the first thing in the prototype that
   fetches at runtime. Three free, keyless sources, each used for
   what only it does well:

   - GeckoTerminal  /networks/base/trending_pools  → which pools
     are trending, ranked, with makers (unique buyers + sellers).
     Its free limit is far tighter than documented (429s after a
     handful of calls), so it is used for the ranking and nothing
     else, and the last ranking is kept in localStorage.
   - DexScreener    /latest/dex/pairs/base/{≤30}   → fast refresh
     of price, changes, volume, txns and liquidity (300 req/min).
   - GoPlus         /token_security/8453           → holder count,
     top-10 share and honeypot flag. One token per call on the
     free tier, so these are queued, throttled and cached.

   All three go through same-origin paths proxied by Vite (see
   vite.config.ts): GeckoTerminal sends 429s without CORS headers,
   which a browser would otherwise report as a network failure.
   ============================================================ */

export type Window = 'm5' | 'h1' | 'h6' | 'h24';

export interface LivePool {
  rank: number;
  pool: string;
  url: string;
  dex: string;
  token: string;
  name: string;
  symbol: string;
  quote: string;
  logo?: string;
  price: number;
  change: Record<Window, number>;
  volume: Record<Window, number>;
  buys: Record<Window, number>;
  sells: Record<Window, number>;
  makers: Record<Window, number | null>;
  liquidity: number;
  marketCap: number;
  fdv: number;
  createdAt: number;
}

export interface HolderInfo {
  count: number | null;
  top10: number | null;
  honeypot: boolean | null;
  fetchedAt: number;
}

const GT = '/gt';
const DS = '/ds';
const GP = '/gp';
const TRENDING_FRESH_MS = 30_000;
const HOLDER_TTL_MS = 15 * 60_000;
const HOLDER_CACHE_KEY = 'bl.live.holders.v2';
const RANKING_CACHE_KEY = 'bl.live.trending.v1';

const WINDOWS: Window[] = ['m5', 'h1', 'h6', 'h24'];

const num = (v: unknown): number => {
  const n = typeof v === 'string' ? parseFloat(v) : typeof v === 'number' ? v : NaN;
  return Number.isFinite(n) ? n : 0;
};

export class RateLimited extends Error {}

/* ---------------- throttled request queues ---------------- */

type Job = { url: string; priority: number; resolve: (v: any) => void; reject: (e: unknown) => void };

/** Serial queue: one request at a time, `spacing` apart, lowest priority
 *  number first. A rate limit pauses the whole queue for `backoff`. */
function makeQueue(
  base: string,
  spacing: number,
  backoff: number,
  limited: (status: number, body: any) => boolean
) {
  const jobs: Job[] = [];
  let pumping = false;
  let pausedUntil = 0;

  async function pump() {
    if (pumping) return;
    pumping = true;
    while (jobs.length) {
      const wait = Math.max(0, pausedUntil - Date.now());
      if (wait) await sleep(wait);
      const job = jobs.shift();
      if (!job) break;
      try {
        const r = await fetch(job.url, { headers: { Accept: 'application/json' } });
        const body = r.status === 429 ? null : await r.json().catch(() => null);
        if (limited(r.status, body)) {
          pausedUntil = Date.now() + backoff;
          job.reject(new RateLimited(`${base} rate limit`));
        } else if (!r.ok || body == null) {
          job.reject(new Error(`HTTP ${r.status}`));
        } else {
          job.resolve(body);
        }
      } catch (e) {
        job.reject(e);
      }
      await sleep(spacing);
    }
    pumping = false;
  }

  return {
    get<T = any>(path: string, priority = 0): Promise<T> {
      return new Promise((resolve, reject) => {
        jobs.push({ url: base + path, priority, resolve, reject });
        jobs.sort((a, b) => a.priority - b.priority);
        pump();
      });
    },
    clear() {
      for (const j of jobs.splice(0)) j.reject(new Error('cancelled'));
    },
  };
}

const gtQueue = makeQueue(GT, 2500, 60_000, (s) => s === 429);
/* GoPlus answers a limit with HTTP 200 and a non-1 code */
const gpQueue = makeQueue(GP, 1200, 30_000, (s, b) => s === 429 || (b != null && b.code !== 1));

/** Drop queued holder lookups — called when the visible set changes. */
export function clearHolderQueue() {
  gpQueue.clear();
}

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

/* ---------------- trending pools ---------------- */

/* One ranking request per key at a time, and a fresh result is reused —
   remounts and React's dev double-effects would otherwise spend the
   rate budget twice. */
const inflight = new Map<string, Promise<LivePool[]>>();
const recent = new Map<string, { at: number; pools: LivePool[] }>();

export function fetchTrending(window: Window, pages: number): Promise<LivePool[]> {
  const key = `${window}:${pages}`;
  const hit = recent.get(key);
  if (hit && Date.now() - hit.at < TRENDING_FRESH_MS) return Promise.resolve(hit.pools);
  let p = inflight.get(key);
  if (!p) {
    p = loadTrending(window, pages)
      .then((pools) => {
        recent.set(key, { at: Date.now(), pools });
        try {
          localStorage.setItem(RANKING_CACHE_KEY, JSON.stringify({ key, at: Date.now(), pools }));
        } catch {
          /* storage blocked — memory only */
        }
        return pools;
      })
      .finally(() => inflight.delete(key));
    inflight.set(key, p);
  }
  return p;
}

/** The last ranking this browser loaded, shown while a fresh one is on
 *  its way or while GeckoTerminal is throttling. */
export function lastRanking(window: Window, pages: number): { at: number; pools: LivePool[] } | null {
  try {
    const raw = localStorage.getItem(RANKING_CACHE_KEY);
    if (!raw) return null;
    const c = JSON.parse(raw);
    if (c.key !== `${window}:${pages}` || !Array.isArray(c.pools)) return null;
    return { at: c.at, pools: c.pools };
  } catch {
    return null;
  }
}

async function loadTrending(window: Window, pages: number): Promise<LivePool[]> {
  const duration = { m5: '5m', h1: '1h', h6: '6h', h24: '24h' }[window];
  const out: LivePool[] = [];
  const seen = new Set<string>();

  for (let page = 1; page <= pages; page++) {
    let res: any;
    try {
      res = await gtQueue.get(
        `/networks/base/trending_pools?include=base_token,quote_token,dex&duration=${duration}&page=${page}`
      );
    } catch (e) {
      /* a later page failing still leaves a usable list */
      if (out.length) break;
      throw e;
    }
    const inc = new Map<string, any>();
    for (const x of res.included ?? []) inc.set(x.id, x.attributes);

    for (const p of res.data ?? []) {
      const a = p.attributes;
      const baseId = p.relationships?.base_token?.data?.id;
      const quoteId = p.relationships?.quote_token?.data?.id;
      const base = inc.get(baseId) ?? {};
      const quote = inc.get(quoteId) ?? {};
      const token = (base.address ?? baseId?.replace('base_', '') ?? '').toLowerCase();
      /* one row per token, as DexScreener does — the first (highest
         ranked) pool for a token stands for it */
      if (!token || seen.has(token)) continue;
      seen.add(token);

      const tx = a.transactions ?? {};
      const rec = <T,>(f: (w: Window) => T) =>
        Object.fromEntries(WINDOWS.map((w) => [w, f(w)])) as Record<Window, T>;

      out.push({
        rank: out.length + 1,
        pool: a.address,
        url: `https://dexscreener.com/base/${a.address}`,
        dex: inc.get(p.relationships?.dex?.data?.id)?.name ?? p.relationships?.dex?.data?.id ?? '',
        token,
        name: base.name ?? a.name,
        symbol: (base.symbol ?? a.name?.split(' / ')[0] ?? '').toUpperCase(),
        quote: (quote.symbol ?? a.name?.split(' / ')[1]?.split(' ')[0] ?? '').toUpperCase(),
        logo: base.image_url && base.image_url !== 'missing.png' ? base.image_url : undefined,
        price: num(a.base_token_price_usd),
        change: rec((w) => num(a.price_change_percentage?.[w])),
        volume: rec((w) => num(a.volume_usd?.[w])),
        buys: rec((w) => num(tx[w]?.buys)),
        sells: rec((w) => num(tx[w]?.sells)),
        makers: rec((w) =>
          tx[w] ? num(tx[w].buyers) + num(tx[w].sellers) : null
        ),
        liquidity: num(a.reserve_in_usd),
        marketCap: num(a.market_cap_usd) || num(a.fdv_usd),
        fdv: num(a.fdv_usd),
        createdAt: a.pool_created_at ? Date.parse(a.pool_created_at) : 0,
      });
    }
  }
  return out;
}

/* ---------------- DexScreener fast refresh ---------------- */

export type PoolPatch = Partial<Pick<LivePool, 'price' | 'change' | 'volume' | 'buys' | 'sells' | 'liquidity' | 'marketCap' | 'fdv' | 'logo'>>;

export async function fetchPatches(pools: string[]): Promise<Map<string, PoolPatch>> {
  const out = new Map<string, PoolPatch>();
  for (let i = 0; i < pools.length; i += 30) {
    const ids = pools.slice(i, i + 30).join(',');
    const r = await fetch(`${DS}/latest/dex/pairs/base/${ids}`);
    if (!r.ok) continue;
    const d = await r.json();
    for (const p of d.pairs ?? []) {
      const rec = (o: any, f: (v: any) => number) =>
        Object.fromEntries(WINDOWS.map((w) => [w, f(o?.[w])])) as Record<Window, number>;
      out.set(String(p.pairAddress).toLowerCase(), {
        price: num(p.priceUsd),
        change: rec(p.priceChange, num),
        volume: rec(p.volume, num),
        buys: rec(p.txns, (t) => num(t?.buys)),
        sells: rec(p.txns, (t) => num(t?.sells)),
        liquidity: num(p.liquidity?.usd),
        marketCap: num(p.marketCap) || num(p.fdv),
        fdv: num(p.fdv),
        logo: p.info?.imageUrl,
      });
    }
  }
  return out;
}

/* ---------------- holders, cached ---------------- */

const holderCache: Map<string, HolderInfo> = (() => {
  try {
    const raw = localStorage.getItem(HOLDER_CACHE_KEY);
    if (raw) return new Map(Object.entries(JSON.parse(raw)) as [string, HolderInfo][]);
  } catch {
    /* storage blocked — memory only */
  }
  return new Map();
})();

function persist() {
  try {
    const fresh = [...holderCache].filter(([, v]) => Date.now() - v.fetchedAt < HOLDER_TTL_MS);
    localStorage.setItem(HOLDER_CACHE_KEY, JSON.stringify(Object.fromEntries(fresh)));
  } catch {
    /* ignore */
  }
}

export function cachedHolders(token: string): HolderInfo | undefined {
  const h = holderCache.get(token);
  return h && Date.now() - h.fetchedAt < HOLDER_TTL_MS ? h : undefined;
}

export async function fetchHolders(token: string, priority: number): Promise<HolderInfo> {
  const hit = cachedHolders(token);
  if (hit) return hit;
  const res = await gpQueue.get(`/api/v1/token_security/8453?contract_addresses=${token}`, priority);
  const r = res.result?.[token] ?? Object.values(res.result ?? {})[0] ?? {};
  const top = Array.isArray(r.holders) ? r.holders.slice(0, 10) : [];
  const info: HolderInfo = {
    count: r.holder_count != null && r.holder_count !== '' ? num(r.holder_count) : null,
    /* GoPlus gives shares as fractions of supply */
    top10: top.length ? Math.min(100, top.reduce((s: number, h: any) => s + num(h.percent), 0) * 100) : null,
    honeypot: r.is_honeypot === '1' ? true : r.is_honeypot === '0' ? false : null,
    fetchedAt: Date.now(),
  };
  holderCache.set(token, info);
  persist();
  return info;
}
