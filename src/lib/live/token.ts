/* Live market state for one Base token that BlockLens has not researched.
   DexScreener for the pairs, through the same `/ds` proxy as Trending. */

export interface LivePair {
  pool: string;
  url: string;
  dex: string;
  quote: string;
  price: number;
  change24h: number;
  volume24h: number;
  txns24h: number;
  liquidity: number;
  marketCap: number;
  fdv: number;
  createdAt: number;
}

export interface LiveToken {
  address: string;
  name: string;
  symbol: string;
  logo?: string;
  website?: string;
  pairs: LivePair[];          // by liquidity, deepest first
}

export const isEvmAddress = (a: string) => /^0x[0-9a-fA-F]{40}$/.test(a.trim());

const num = (v: unknown) => {
  const n = typeof v === 'string' ? parseFloat(v) : typeof v === 'number' ? v : NaN;
  return Number.isFinite(n) ? n : 0;
};

/** null when DexScreener has no Base pair for the address. */
export async function fetchLiveToken(address: string): Promise<LiveToken | null> {
  const a = address.trim().toLowerCase();
  const r = await fetch(`/ds/tokens/v1/base/${a}`);
  if (!r.ok) throw new Error(`DexScreener ${r.status}`);
  const rows: any[] = await r.json();
  const mine = (rows ?? []).filter((p) => p?.baseToken?.address?.toLowerCase() === a);
  const list = mine.length ? mine : rows ?? [];
  if (!list.length) return null;

  const pairs: LivePair[] = list
    .map((p) => ({
      pool: p.pairAddress,
      url: p.url ?? `https://dexscreener.com/base/${p.pairAddress}`,
      dex: [p.dexId, ...(p.labels ?? [])].filter(Boolean).join(' '),
      quote: (p.quoteToken?.symbol ?? '').toUpperCase(),
      price: num(p.priceUsd),
      change24h: num(p.priceChange?.h24),
      volume24h: num(p.volume?.h24),
      txns24h: num(p.txns?.h24?.buys) + num(p.txns?.h24?.sells),
      liquidity: num(p.liquidity?.usd),
      marketCap: num(p.marketCap),
      fdv: num(p.fdv),
      createdAt: num(p.pairCreatedAt),
    }))
    .sort((x, y) => y.liquidity - x.liquidity);

  const head = list[0];
  const base = mine.length ? head.baseToken : head.quoteToken;
  return {
    address: a,
    name: base?.name ?? 'Unknown token',
    symbol: (base?.symbol ?? '').toUpperCase(),
    logo: list.find((p) => p.info?.imageUrl)?.info?.imageUrl,
    website: list.find((p) => p.info?.websites?.length)?.info?.websites?.[0]?.url,
    pairs,
  };
}
