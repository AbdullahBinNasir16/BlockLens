/* The live launch feed, from the BlockLens API (backend/blocklens/api). */

export interface Launch {
  token: string;
  pool: string;
  dex: string;
  quote: string;
  created_block: number;
  launch_ts: string;
  status: string;
  launch_type: 'launchpad' | 'self-deployed' | null;
  risk: number | null;
  swaps_by_cutoff: number | null;
  buyers_by_cutoff: number | null;
  run_up_by_cutoff: number | null;
  scored_at: string | null;
}

export interface ModelMeta {
  version: string;
  target: string;
  applies_to: string;
  trained_on: { tokens: number; losses: number; launches: [string, string] };
  validation: {
    in_period: { set: string; tokens: number; pr_auc: number; base_rate: number; rule_checker_pr_auc: number };
    out_of_time: { set: string; tokens: number; pr_auc: number; rule_checker_pr_auc: number };
    regime_check: { set: string; tokens: number; losses: number; flagged_at_0_5: number; losses_caught: number };
  };
  launch_type_signal: { self_deployed_rug_rate_eval: string; launchpad_rug_rate_eval: string };
}

export interface ForwardRecord {
  protocol: string;
  report_floor: { resolved: number; losses: number };
  logged: number;
  scored: number;
  since: string | null;
  buyer_loss: {
    resolved: number;
    losses: number;
    base_rate?: number;
    mean_predicted?: number;
    brier?: number;
    brier_base_rate?: number;
    pr_auc?: number;
    roc_auc?: number;
    pr_auc_minus_base_rate_ci?: [number, number];
    flagged_at_0_5?: number;
    precision_at_0_5?: number | null;
    reportable?: boolean;
  };
  launch_type: Record<string, Record<string, { resolved: number; pulled: number; rate: number }>>;
  paper_agent?: {
    floor: number;
    policies: Record<string, Record<string, any>>;
  };
}

export interface Feed {
  model: ModelMeta;
  forward: ForwardRecord | null;
  scanned_to_block: number | null;
  last_run: string | null;
  last_error: string | null;
  launches: Launch[];
}

export async function fetchFeed(): Promise<Feed> {
  const r = await fetch('/api/launches');
  if (!r.ok) throw new Error(`API ${r.status}`);
  return r.json();
}

export async function fetchTracked(address: string): Promise<Launch | null> {
  const r = await fetch(`/api/token/${address}`);
  if (!r.ok) return null;
  const d = await r.json();
  return d.tracked ? d.launch : null;
}

/** Symbols for display, from DexScreener (≤ 30 per call). */
export async function fetchSymbols(tokens: string[]): Promise<Record<string, { symbol: string; name: string }>> {
  const out: Record<string, { symbol: string; name: string }> = {};
  for (let i = 0; i < tokens.length; i += 30) {
    try {
      const r = await fetch(`/ds/tokens/v1/base/${tokens.slice(i, i + 30).join(',')}`);
      if (!r.ok) continue;
      for (const p of (await r.json()) ?? []) {
        const a = String(p?.baseToken?.address ?? '').toLowerCase();
        if (a && !out[a]) out[a] = { symbol: p.baseToken.symbol ?? '', name: p.baseToken.name ?? '' };
      }
    } catch {
      /* names are a nicety; the feed stands without them */
    }
  }
  return out;
}

export function riskBand(p: number): 'low' | 'medium' | 'high' {
  if (p >= 0.5) return 'high';
  if (p >= 0.2) return 'medium';
  return 'low';
}
