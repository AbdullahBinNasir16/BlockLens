/* ============================================================
   Deterministic series builders.

   These generate the *shape* of illustrative series (holder curves,
   contribution heatmaps, daily flow) so the prototype does not carry
   hundreds of hand-typed numbers. They are seeded, so every reload and
   every viewer sees identical data.

   Anything produced here is sample data. Real figures live inline in the
   project files and are marked `provenance: 'live'` on their section.
   ============================================================ */

export function seeded(seed: number) {
  let s = seed >>> 0;
  return () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296);
}

/** 53 weeks x 7 days of 0-4 intensity, shaped by a repo's real activity. */
export function heatmap(
  seed: number,
  opts: { ramp?: number; quiet?: number[]; recent?: number; base?: number } = {}
): number[][] {
  const rnd = seeded(seed);
  const { ramp = 8, quiet = [], recent = 0.62, base = 0.42 } = opts;
  const weeks: number[][] = [];
  for (let w = 0; w < 53; w++) {
    let p = base;
    if (w < ramp) p = base * (0.25 + (w / ramp) * 0.6);
    else if (w > 46) p = recent;
    else if (w > 38) p = (base + recent) / 2;
    if (quiet.includes(w)) p = 0.05;

    const days: number[] = [];
    for (let d = 0; d < 7; d++) {
      const weekend = d === 0 || d === 6 ? 0.42 : 1;
      const r = rnd();
      const q = p * weekend;
      days.push(r < q * 0.32 ? 4 : r < q * 0.7 ? 3 : r < q * 1.15 ? 2 : r < q * 1.7 ? 1 : 0);
    }
    weeks.push(days);
  }
  return weeks;
}

/** Monotonic-ish accumulation curve from `from` to `to`. */
export function growth(
  seed: number,
  labels: string[],
  from: number,
  to: number,
  jitter = 0.04
): { t: string; v: number }[] {
  const rnd = seeded(seed);
  const n = labels.length;
  return labels.map((t, i) => {
    const k = i / (n - 1 || 1);
    /* ease-out so most of the growth lands early, as launches do */
    const eased = 1 - Math.pow(1 - k, 1.7);
    const v = from + (to - from) * eased;
    const noise = i === 0 || i === n - 1 ? 0 : (rnd() - 0.5) * 2 * jitter * v;
    return { t, v: Math.max(from, Math.round(v + noise)) };
  });
}

/** Daily mention/volume style series that spikes at launch then settles. */
export function spikeSeries(
  seed: number,
  labels: string[],
  baseline: number,
  peak: number,
  peakAt = 4
): { t: string; v: number }[] {
  const rnd = seeded(seed);
  return labels.map((t, i) => {
    const d = Math.abs(i - peakAt);
    const decay = Math.exp(-d / 2.6);
    const v = baseline + (peak - baseline) * decay;
    return { t, v: Math.round(v * (0.86 + rnd() * 0.28)) };
  });
}

/** Daily buys/sells that end on the token's real 24h counts. */
export function flow(
  seed: number,
  days: number,
  finalBuys: number,
  finalSells: number
): { t: string; buys: number; sells: number }[] {
  const rnd = seeded(seed);
  const out = [];
  for (let i = 0; i < days; i++) {
    const k = i / (days - 1 || 1);
    /* early days run hotter than the current baseline */
    const heat = 1 + (1 - k) * 1.6;
    const wob = 0.72 + rnd() * 0.56;
    out.push({
      t: `D${i + 1}`,
      buys: i === days - 1 ? finalBuys : Math.round(finalBuys * heat * wob),
      sells: i === days - 1 ? finalSells : Math.round(finalSells * heat * (0.7 + rnd() * 0.7)),
    });
  }
  return out;
}

/** Evenly spaced day labels ending today. */
export function dayLabels(n: number, endLabel = 'now'): string[] {
  const out: string[] = [];
  for (let i = n - 1; i > 0; i--) out.push(`${i}d`);
  out.push(endLabel);
  return out;
}
