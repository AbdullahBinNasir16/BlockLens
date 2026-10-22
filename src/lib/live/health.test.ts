import { describe, expect, it } from 'vitest';
import { REASON_ORDER, driftSeries, reasonTotals, stackedDays, type HealthDay } from './health';

const day = (d: string, over: Partial<HealthDay>): HealthDay => ({
  day: d,
  logged: 0,
  reasons: {},
  launch_type: {},
  scored: 0,
  mean_risk: null,
  median_delay_s: null,
  self_deployed_share: null,
  resolved: 0,
  losses: 0,
  ...over,
});

const DAYS = [
  day('2026-10-21', { logged: 5, reasons: { scored: 2, 'never traded': 3 }, scored: 2, self_deployed_share: 0.5 }),
  day('2026-10-20', { logged: 4, reasons: { scored: 1, 'drained before minute 5': 3 }, scored: 1, self_deployed_share: 1 }),
];

describe('reasonTotals', () => {
  it('sums every reason across days in the stacking order', () => {
    expect(reasonTotals(DAYS)).toEqual([
      { reason: 'scored', count: 3 },
      { reason: 'never traded', count: 3 },
      { reason: 'drained before minute 5', count: 3 },
    ]);
    expect(REASON_ORDER[0]).toBe('scored');
  });
});

describe('stackedDays', () => {
  it('orders days chronologically and keeps the parts in reason order', () => {
    const s = stackedDays(DAYS);
    expect(s.map((d) => d.day)).toEqual(['2026-10-20', '2026-10-21']);
    expect(s[1].parts.map((p) => p.reason)).toEqual(['scored', 'never traded']);
    expect(s[0].total).toBe(4);
  });
});

describe('driftSeries', () => {
  it('carries the self-deployed share and the count behind it', () => {
    expect(driftSeries(DAYS)).toEqual([
      { day: '2026-10-20', share: 1, n: 1 },
      { day: '2026-10-21', share: 0.5, n: 2 },
    ]);
  });
});
