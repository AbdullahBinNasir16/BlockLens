/* ============================================================
   BlockLens — data model
   Every shape here is designed to be swapped 1:1 with a backend
   response later. UI components never invent data; they only
   render these records.
   ============================================================ */

export type Chain = 'ethereum' | 'base' | 'solana' | 'bnb';

export type Signal = 'positive' | 'negative' | 'neutral';

/** Where a section's numbers come from.
 *  'live'   — fetched from a public source and reproducible
 *  'sample' — illustrative shape for the prototype, not a real finding */
export type Provenance = 'live' | 'sample';

export type Verdict = 'supported' | 'partial' | 'contradicted' | 'unknown';

export type RiskLevel = 'low' | 'medium' | 'high';

/* ---------------- Token / project ---------------- */

export interface TokenMetrics {
  price: number;
  priceChange24h: number;
  marketCap: number;
  fdv: number;
  volume24h: number;
  liquidity: number;
  holders: number;
  holdersChange24h: number;
  ageLabel: string;
  ageHours: number;
  txns24h: { buys: number; sells: number };
  supply: number;
}

export interface ProjectLinks {
  explorer: string;
  website?: string;
  x?: string;
  github?: string;
  docs?: string;
  telegram?: string;
  discord?: string;
  extra?: { label: string; url: string }[];
}

export interface ParameterScore {
  id: string;
  label: string;
  score: number;
  /** what fed the score — surfaced on hover */
  drivers: { label: string; weight: number; signal: Signal }[];
  note: string;
}

/** How a wallet has behaved with its position. Drives bubble colour. */
export type Behaviour = 'smart' | 'neutral' | 'seller';

export interface Holder {
  rank: number;
  address: string;
  label: string;
  pct: number;
  value: number;
  change: number;
  kind: string;
  behaviour: Behaviour;
  /** holding period, shown on hover */
  held: string;
  /** one line explaining the classification */
  note: string;
}

export type RoadmapStatus = 'done' | 'active' | 'planned' | 'missed';

export interface RoadmapItem {
  date: string;
  label: string;
  detail: string;
  status: RoadmapStatus;
  track: string;
}

export interface Project {
  id: string;
  name: string;
  ticker: string;
  chain: Chain;
  contract: string;
  deployedAt: string;
  category: string;
  categoryDetail: string;
  /** path under /public for the token's own logo */
  logo: string;
  /** two-letter fallback if the logo fails to load */
  monogram: string;
  /** primary venue, e.g. "Aerodrome · NOCK/USDC" */
  venue: string;
  /** when the live figures on this record were captured */
  snapshotAt: string;
  oneLiner: string;
  idea: string;
  metrics: TokenMetrics;
  links: ProjectLinks;
  narrative: { primary: string; relevance: number; tags: string[] };
  scores: {
    risk: number;
    confidence: number;
    conviction: 'Low' | 'Moderate' | 'High';
    riskLevel: RiskLevel;
  };
  parameters: ParameterScore[];
  fundamentals: {
    uniqueness: { score: number; note: string };
    innovation: { score: number; note: string };
    keyFindings: { text: string; signal: Signal }[];
  };
  /** the final read, as marked bullets */
  assessment: { bullets: { text: string; signal: Signal }[] };
}

/* ---------------- People & wallets ---------------- */

export interface DeployedProject {
  year: string;
  name: string;
  ticker: string;
  chain: Chain;
  outcome: string;
  outcomeSignal: Signal;
  peak: string;
  duration: string;
  note: string;
  current?: boolean;
}

export interface Developer {
  id: string;
  alias: string;
  handle: string;
  githubUser: string;
  wallet: string;
  firstSeen: string;
  identityConfidence: number;
  doxxed: boolean;
  summary: string;
  stats: { deployments: number; activeProjects: number; abandoned: number; rugs: number };
  history: DeployedProject[];
  activity: number[];
}

/* ---------------- GitHub / social ---------------- */

export interface GithubData {
  repo: string;
  url: string;
  description: string;
  stars: number;
  forks: number;
  watchers: number;
  contributors: number;
  commits: number;
  openIssues: number;
  license: string;
  createdAt: string;
  lastCommit: string;
  primaryLanguage: string;
  languages: { name: string; pct: number }[];
  /** 53 weeks x 7 days, 0-4 intensity */
  heatmap: number[][];
  timeline: { date: string; label: string; detail: string; kind: string }[];
  topContributors: { user: string; commits: number; share: number; linked: boolean }[];
  consistency: { label: string; value: number; note: string }[];
}

export interface SocialData {
  handle: string;
  url: string;
  followers: number;
  followersChange7d: number;
  posts30d: number;
  avgEngagement: number;
  accountCreated: string;
  growth: { t: string; v: number }[];
  mentions: { t: string; v: number }[];
  topAccounts: { handle: string; followers: number; kind: string; sentiment: Signal }[];
  momentum: { label: string; value: number; delta: number }[];
  authenticity: {
    overall: number;
    verdict: 'Strong' | 'Mixed' | 'Weak';
    axes: { label: string; value: number; note: string }[];
    notes: { text: string; signal: Signal }[];
  };
}

/* ---------------- On-chain ---------------- */

/** One dial on the on-chain wall. `dial` is always 0-100 with higher meaning
 *  healthier, so every meter reads the same way regardless of what it measures. */
export interface OnChainReading {
  id: string;
  label: string;
  /** printed inside the dial — a percentage, a count, or a word */
  display: string;
  dial: number;
  caption: string;
  tone: 'good' | 'warn' | 'bad';
  /** true when the figure came from a public source rather than a sample */
  sourced: boolean;
}

export interface OnChainData {
  readings: OnChainReading[];
  distribution: { label: string; pct: number; wallets: number; signal: Signal }[];
  holderGrowth: { t: string; v: number }[];
  buySell: { t: string; buys: number; sells: number }[];
  concentration: { top10: number; top50: number; gini: number; verdict: string; signal: Signal };
  liquidity: {
    pooled: number;
    lockedPct: number;
    lockUntil: string;
    pairs: { dex: string; pair: string; liquidity: number; share: number }[];
  };
}

export interface RiskSignal {
  id: string;
  label: string;
  level: RiskLevel;
  score: number;
  summary: string;
}

/* ---------------- Lists ---------------- */

export interface TrendingToken {
  id: string;
  name: string;
  ticker: string;
  chain: Chain;
  logo: string;
  monogram: string;
  price: number;
  change24h: number;
  volume: number;
  liquidity: number;
  marketCap: number;
  holders: number;
  age: string;
  category: string;
  spark: number[];
  researched?: boolean;
}

/* ---------------- Narrative map ---------------- */

export interface NarrativeNode {
  id: string;
  label: string;
  strength: number;
  phase: 'Emerging' | 'Expanding' | 'Peaking' | 'Cooling';
  x: number;
  y: number;
  relation: string;
}

export interface NarrativeMap {
  nodes: NarrativeNode[];
  edges: [string, string][];
  reading: { label: string; value: number; note: string }[];
}

/* ============================================================
   One project's complete research record.

   This is the unit a backend would return for a contract address.
   Every section component reads from exactly one of these.
   ============================================================ */

export interface ProjectDataset {
  project: Project;
  developer: Developer;
  deployerFacts: { label: string; value: string; signal: Signal }[];
  github: GithubData;
  social: SocialData;
  onchain: OnChainData;
  /** rendered as the bubble field in Wallet Intelligence */
  topHolders: Holder[];
  roadmap: RoadmapItem[];
  narrative: NarrativeMap;
  risks: RiskSignal[];
  /** which sections carry sourced figures rather than illustrative ones */
  provenance: Record<string, Provenance>;
}

/* ============================================================
   Wallet screener

   Cross-project wallet discovery. The user never authors a check — every
   filter is a fixed toggle, so every predicate here is one a backend can
   index and evaluate on its own.
   ============================================================ */

export type CheckCategory =
  | 'performance'
  | 'timing'
  | 'breadth'
  | 'identity'
  | 'risk'
  | 'activity';

/** Where a check is evaluated.
 *  'project' — once per added project; the project rule then counts passes
 *  'wallet'  — once per wallet, over everything it traded in scope */
export type CheckTier = 'project' | 'wallet';

/** Whether a real backend could answer this from chain data alone.
 *  'direct'  — public chain data is enough
 *  'derived' — needs clustering, labelling or price history */
export type CheckDerivation = 'direct' | 'derived';

export type CheckValueType =
  | 'currency'
  | 'percent'
  | 'duration'
  | 'integer'
  | 'multiple'
  | 'date'
  | 'enum'
  | 'boolean';

/** No OR and no nesting, so the operator set stays small. */
export type CheckOperator = 'gte' | 'lte' | 'is' | 'isNot';

export type CheckValue = number | string | boolean;

export interface CheckDefinition {
  id: string;
  /** one or two words — it is the whole chip */
  label: string;
  category: CheckCategory;
  tier: CheckTier;
  valueType: CheckValueType;
  derivation: CheckDerivation;
  /** operators the chip cycles through; the first is the default */
  operators: CheckOperator[];
  defaultValue: CheckValue;
  /** choices when valueType is 'enum' */
  options?: { value: string; label: string }[];
}

/** A switched-on filter. A check is either on or off, never on twice, so
 *  its id is its identity. */
export interface AppliedCheck {
  checkId: string;
  operator: CheckOperator;
  value: CheckValue;
}

export type Quantifier = 'atLeast' | 'exactly' | 'atMost';

/** The per-project filters and the rule that counts them. The quantifier
 *  belongs to the rule, not to any one filter: "$2k PnL in ≥2 projects" is
 *  a different question from "≥2 projects, and $2k PnL somewhere". */
export interface ProjectRule {
  quantifier: Quantifier;
  count: number;
  checks: AppliedCheck[];
}

export interface ScreenerScope {
  /** one chain per search */
  chain: Chain;
  /** contract addresses exactly as the user added them */
  contracts: string[];
  /** ms epoch, inclusive */
  from: number;
  to: number;
}

export interface ScreenerQuery {
  scope: ScreenerScope;
  projectRule: ProjectRule;
  walletChecks: AppliedCheck[];
}

export type FundingSource = 'fresh' | 'cex' | 'bridge' | 'cluster' | 'unknown';

/** One wallet's position in one project.
 *
 *  Money is stored as what actually moved — spent, taken out, still held —
 *  and never as a pre-computed PnL. Every figure the screener filters on is
 *  derived from these, so the prototype filters the way a backend would. */
export interface WalletProjectPosition {
  projectId: string;
  chain: Chain;
  /** ms epoch of the first buy */
  firstBuy: number;
  /** ms epoch of the last sell; null while the position is still open */
  lastSell: number | null;
  buys: number;
  sells: number;
  /** USD spent acquiring the position */
  invested: number;
  /** share of the position that has been sold, 0-1 */
  soldFraction: number;
  /** USD received from those sells */
  proceeds: number;
  /** USD value of what is still held */
  remainingValue: number;
  /** ms between the project's first pair activity and this wallet's first buy */
  entryDelay: number;
  averagedDown: boolean;
  soldFirstPump: boolean;
  wentToZero: boolean;
  honeypot: boolean;
}

export interface WalletRecord {
  address: string;
  /** a known identity, when one exists */
  label?: string;
  ens?: string;
  /** ms epoch the wallet first appeared on chain */
  firstSeen: number;
  fundingSource: FundingSource;
  /** wallets funded from the same origin, including this one */
  clusterSize: number;
  smartMoney: boolean;
  insiderLinked: boolean;
  positions: WalletProjectPosition[];
}

/** One rung of the funnel. `removed` is what this stage eliminated, which is
 *  the number a user actually wants when a filter guts their result set. */
export interface FunnelStage {
  id: string;
  label: string;
  remaining: number;
  removed: number;
}

export interface WalletMatch {
  wallet: WalletRecord;
  /** projects that passed every per-project filter — or, with none on,
   *  every project the wallet traded in scope */
  matchedProjects: string[];
  realizedPnl: number;
  winRate: number;
  avgHoldingTime: number;
  lastActive: number;
  /** distinct projects traded in scope — shown against `matchedProjects`,
   *  because "matched 2 of 3" is what explains a loss on the third */
  projectsTraded: number;
}

export interface ScreenerResult {
  matches: WalletMatch[];
  funnel: FunnelStage[];
  /** the stage that removed the last candidates — drives the zero state */
  limitingStage?: FunnelStage;
  scopedWallets: number;
}
