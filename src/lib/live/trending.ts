/* ============================================================
   Live Base trending, from the BlockLens API (Phase 7).

   The browser used to call GeckoTerminal, DexScreener and GoPlus itself,
   through the Vite dev server's proxy, which a production build does not
   have. The API now makes those calls once for every viewer, behind the
   rate budget and a shared cache (`backend/blocklens/api/market.py`), and
   this file only reads `/api/trending`.
   ============================================================ */
import type { TokenSecurity, TrendingPool, TrendingResponse, TrendingWindow } from '../../data/api';
import { apiGet } from '../api';

export type Window = TrendingWindow;
export type LivePool = TrendingPool;

export interface HolderInfo {
  count: number | null;
  top10: number | null;
  honeypot: boolean | null;
  fetchedAt: number;
}

export function holderInfo(s: TokenSecurity | null | undefined): HolderInfo | undefined {
  if (!s) return undefined;
  return { count: s.holders, top10: s.top10Pct, honeypot: s.honeypot, fetchedAt: Date.parse(s.asOf) || 0 };
}

export function fetchTrending(window: Window, pages: number): Promise<TrendingResponse> {
  return apiGet<TrendingResponse>(`/api/trending?window=${window}&pages=${pages}`);
}
