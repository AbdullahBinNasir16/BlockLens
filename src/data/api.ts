/* ============================================================
   The API contract (Phase 7).

   Every response the BlockLens API serves to a screen is one of the
   `*Response` types below. They are the single source of truth:

     npm run contract   →  contract/blocklens.schema.json  (ts-json-schema-generator)
                        →  backend/blocklens/api/contract.py (datamodel-code-generator)

   Both generated files are committed, and a test on each side fails when
   either has drifted from this file. Change a response here first.

   Provenance is carried per section, not per page, because a page such as
   Project Intelligence is genuinely mixed: its market section can be live
   while its research sections are sample. Within one section, live and
   sample never appear together.
   ============================================================ */

import type { Provenance, WalletRecord } from './types';

export type TrendingWindow = 'm5' | 'h1' | 'h6' | 'h24';

/** One row per token: the highest-ranked pool stands for it. */
export interface TrendingPool {
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
  change: Record<TrendingWindow, number>;
  volume: Record<TrendingWindow, number>;
  buys: Record<TrendingWindow, number>;
  sells: Record<TrendingWindow, number>;
  /** unique buyers + sellers, from GeckoTerminal; null where it gives none */
  makers: Record<TrendingWindow, number | null>;
  liquidity: number;
  marketCap: number;
  fdv: number;
  /** ms epoch */
  createdAt: number;
  holders: TokenSecurity | null;
}

export interface TrendingResponse {
  provenance: Provenance;
  window: TrendingWindow;
  /** ISO time the ranking was fetched upstream */
  asOf: string;
  /** true when GeckoTerminal is throttling and the last good ranking is served */
  stale: boolean;
  pools: TrendingPool[];
}

/** GoPlus token security, the parts the UI shows. */
export interface TokenSecurity {
  holders: number | null;
  /** share of supply held by the ten largest holders, percent */
  top10Pct: number | null;
  honeypot: boolean | null;
  asOf: string;
}

export interface MarketPair {
  pool: string;
  url: string;
  dex: string;
  quote: string;
  price: number;
  change24h: number;
  volume24h: number;
  buys24h: number;
  sells24h: number;
  liquidity: number;
  marketCap: number;
  fdv: number;
  /** ms epoch */
  createdAt: number;
}

export interface TokenMarket {
  address: string;
  name: string;
  symbol: string;
  logo?: string;
  website?: string;
  /** deepest first */
  pairs: MarketPair[];
  asOf: string;
}

export interface MarketSection {
  provenance: Provenance;
  /** null when DexScreener has no Base pair for the address */
  data: TokenMarket | null;
  error?: string;
}

export interface SecuritySection {
  provenance: Provenance;
  data: TokenSecurity | null;
  error?: string;
}

/** The live half of a token page. The research sections are not here:
 *  they are sample, held by the front end, and badged as such. */
export interface ProjectLiveResponse {
  address: string;
  market: MarketSection;
  security: SecuritySection;
  risk: TokenRiskResponse;
}

/** Display names for a batch of tokens (DexScreener, cached server side). */
export interface SymbolsResponse {
  provenance: Provenance;
  symbols: Record<string, { symbol: string; name: string }>;
}

/* ---------------- model risk ---------------- */

export type RiskState = 'scored' | 'pending' | 'not_scored' | 'out_of_scope';

export interface ModelCard {
  version: string;
  /** what the score predicts, in words */
  target: string;
  /** the population the model was trained to judge */
  appliesTo: string;
  trainedOnLaunches: string[];
  trainedOnTokens: number;
  /** date the model artifact was written */
  trainedAt: string;
}

/** What happened, forward, to launches the model scored in the same band.
 *  This is the honest reading of a score: the model's raw probabilities are
 *  not calibrated forward (DECISIONS.md, Phase 8 result). */
export interface ForwardBand {
  lo: number;
  hi: number;
  launches: number;
  losses: number;
  /** losses / launches */
  observed: number;
  since: string;
}

export interface Driver {
  feature: string;
  label: string;
  value: number;
  display: string;
  /** additive, in log-odds */
  contribution: number;
  direction: 'raises' | 'lowers' | 'neutral';
}

export interface RiskScore {
  /** the model's raw output: a ranking, not a calibrated probability */
  risk: number;
  launchType: 'launchpad' | 'self-deployed' | null;
  launchTs: string;
  scoredAt: string;
  band: ForwardBand | null;
  drivers: Driver[];
  /** what every feature outside `drivers` contributed, together (log-odds) */
  rest: number;
  /** the model's score for a launch about which nothing is known */
  baseRate: number;
}

export interface TokenRiskResponse {
  address: string;
  provenance: Provenance;
  state: RiskState;
  /** why there is or is not a score, in a sentence a user can read */
  reason: string;
  model: ModelCard;
  score: RiskScore | null;
}

/* ---------------- wallet screener ---------------- */

export interface ScreenerToken {
  address: string;
  symbol: string;
  name: string;
  /** ms epoch of the first swap BlockLens stored */
  launchedAt: number;
  wallets: number;
}

export interface ScreenerResponse {
  provenance: Provenance;
  asOf: string;
  /** positions' money: ETH amounts from the store, converted at each trade's
   *  own day's ETH close (GeckoTerminal daily candles, WETH/USDC on Base) */
  unit: 'USD';
  tokens: ScreenerToken[];
  /** the contracts asked for; wallets are those with a position in one of
   *  them, with all their positions. Empty when only the index was asked. */
  contracts: string[];
  wallets: WalletRecord[];
}

/* ---------------- health ---------------- */

export interface UpstreamHealth {
  ok: boolean;
  latencyMs: number | null;
  error?: string;
  checkedAt: string;
  /** calls made to this source since the API started */
  calls: number;
  cacheHits: number;
}

export interface HealthResponse {
  ok: boolean;
  database: { ok: boolean; error?: string };
  model: { loaded: boolean; version: string | null };
  scorer: {
    running: boolean;
    lastRun: string | null;
    lastError: string | null;
    scannedToBlock: number | null;
    tracked: number;
  };
  alerts: { enabled: boolean; sent: number; lastError: string | null };
  upstream: Record<string, UpstreamHealth>;
}
