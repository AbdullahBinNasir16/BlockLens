/* The paper agent's book, from /api/paper-agent/trades, and the arithmetic
   the Paper Agent page shows. Every number on that page is derived here
   from the trade rows; nothing about performance is stored. The policies
   and the cost are the pre-registered ones (DECISIONS.md, Phase 9). */

export interface PaperTrade {
  token: string;
  pool: string;
  dex: string;
  launch_ts: string;
  scored_at: string | null;
  risk: number | null;
  launch_type: 'launchpad' | 'self-deployed' | null;
  /** the agent's own rule: launchpad and risk under the ceiling */
  agent: boolean;
  /** liquidity gone by hour 6: the trade returns −100% */
  pulled: boolean;
  price_6h_vs_cutoff: number | null;
  /** return at the headline cost, capped; null when the price could not be read */
  return: number | null;
  capped: boolean;
}

export interface PaperBook {
  protocol: string;
  cost: number;
  cap: number;
  max_risk: number;
  trades: PaperTrade[];
}

export type Policy = 'AGENT' | 'CONTROL' | 'LAUNCHPAD' | 'AVOIDED';

export const POLICY_LABEL: Record<Policy, string> = {
  AGENT: 'Agent',
  CONTROL: 'Buy everything',
  LAUNCHPAD: 'Every launchpad launch',
  AVOIDED: 'What the agent refused',
};

export const POLICY_RULE: Record<Policy, string> = {
  AGENT: 'launchpad launch and risk under the ceiling',
  CONTROL: 'every scored launch, no model',
  LAUNCHPAD: 'every launchpad launch, no model (post hoc)',
  AVOIDED: 'every scored launch the agent did not buy',
};

export async function fetchPaperBook(): Promise<PaperBook> {
  const r = await fetch('/api/paper-agent/trades?limit=2000');
  if (!r.ok) throw new Error(`API ${r.status}`);
  return r.json();
}

export function picks(t: PaperTrade, policy: Policy): boolean {
  if (policy === 'AGENT') return t.agent;
  if (policy === 'AVOIDED') return !t.agent;
  if (policy === 'LAUNCHPAD') return t.launch_type === 'launchpad';
  return true;
}

export interface PolicyStats {
  trades: number;
  mean: number;
  median: number;
  hitRate: number;
  total: number;
  capped: number;
  pulled: number;
}

/** Stats over the trades a policy would have taken; null when it took none. */
export function policyStats(trades: PaperTrade[], policy: Policy): PolicyStats | null {
  const rets = trades.filter((t) => picks(t, policy) && t.return != null).map((t) => t.return as number);
  if (!rets.length) return null;
  const sorted = [...rets].sort((a, b) => a - b);
  const mid = sorted.length >> 1;
  return {
    trades: rets.length,
    mean: rets.reduce((a, b) => a + b, 0) / rets.length,
    median: sorted.length % 2 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2,
    hitRate: rets.filter((r) => r > 0).length / rets.length,
    total: rets.reduce((a, b) => a + b, 0),
    capped: trades.filter((t) => picks(t, policy) && t.capped).length,
    pulled: trades.filter((t) => picks(t, policy) && t.pulled).length,
  };
}

export interface EquityPoint {
  t: number;
  /** cumulative return in units of notional: one unit per trade */
  v: number;
  n: number;
}

/** One unit of notional per trade, in launch order. */
export function equityCurve(trades: PaperTrade[], policy: Policy): EquityPoint[] {
  const rows = trades
    .filter((t) => picks(t, policy) && t.return != null)
    .map((t) => ({ t: Date.parse(t.launch_ts), r: t.return as number }))
    .sort((a, b) => a.t - b.t);
  const out: EquityPoint[] = [];
  let v = 0;
  rows.forEach((row, i) => {
    v += row.r;
    out.push({ t: row.t, v, n: i + 1 });
  });
  return out;
}

/** The same stats without the capped trades: the honest reading of a mean
 *  that a handful of +1,000% spikes can carry on their own. */
export function withoutCapped(trades: PaperTrade[]): PaperTrade[] {
  return trades.filter((t) => !t.capped);
}
