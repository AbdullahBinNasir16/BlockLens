/* The live system's own health, from /api/model/health, and the series the
   Model Health page draws from it. */

export interface HealthDay {
  day: string;
  logged: number;
  reasons: Record<string, number>;
  launch_type: Record<string, number>;
  scored: number;
  mean_risk: number | null;
  median_delay_s: number | null;
  self_deployed_share: number | null;
  resolved: number;
  losses: number;
}

export interface Outage {
  from: string;
  to: string;
  minutes: number;
}

export interface Health {
  window_days: number;
  days: HealthDay[];
  outages: Outage[];
  outage_threshold_minutes: number;
  totals: {
    logged: number;
    scored: number;
    resolved: number;
    losses: number;
    since: string | null;
    last_record: string | null;
  };
  scorer: {
    last_run: string | null;
    last_error: string | null;
    scanned_to_block: number | null;
    tracked: number;
  };
  model: { version: string; trained: string | null };
}

export async function fetchHealth(): Promise<Health> {
  const r = await fetch('/api/model/health');
  if (!r.ok) throw new Error(`API ${r.status}`);
  return r.json();
}

/** Every reason the scorer records, in the order the page stacks them. */
export const REASON_ORDER = [
  'scored',
  'never traded',
  'drained before minute 5',
  'untradeable price',
  'missed during an outage',
  'could not read the chain',
  'other',
];

export const REASON_TONE: Record<string, string> = {
  scored: 'var(--ink)',
  'never traded': 'var(--ink-4)',
  'drained before minute 5': 'var(--neg)',
  'untradeable price': 'var(--warn)',
  'missed during an outage': 'var(--rule-strong)',
  'could not read the chain': 'var(--warn)',
  other: 'var(--rule-strong)',
};

export function reasonTotals(days: HealthDay[]): { reason: string; count: number }[] {
  const sum: Record<string, number> = {};
  for (const d of days) for (const [k, v] of Object.entries(d.reasons)) sum[k] = (sum[k] ?? 0) + v;
  return REASON_ORDER.filter((r) => sum[r]).map((r) => ({ reason: r, count: sum[r] }));
}

export interface StackedDay {
  day: string;
  total: number;
  parts: { reason: string; count: number }[];
}

export function stackedDays(days: HealthDay[]): StackedDay[] {
  return [...days]
    .sort((a, b) => a.day.localeCompare(b.day))
    .map((d) => ({
      day: d.day,
      total: d.logged,
      parts: REASON_ORDER.filter((r) => d.reasons[r]).map((r) => ({ reason: r, count: d.reasons[r] })),
    }));
}

/** The self-deployed share of scored launches per day: the regime shift
 *  that moved from 4–11% to 63–69% in 2026 and broke calibration. */
export function driftSeries(days: HealthDay[]): { day: string; share: number | null; n: number }[] {
  return [...days]
    .sort((a, b) => a.day.localeCompare(b.day))
    .map((d) => ({ day: d.day, share: d.self_deployed_share, n: d.scored }));
}
