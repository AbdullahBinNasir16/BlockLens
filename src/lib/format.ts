export function compact(n: number): string {
  const a = Math.abs(n);
  if (a >= 1e9) return (n / 1e9).toFixed(2).replace(/\.?0+$/, '') + 'B';
  if (a >= 1e6) return (n / 1e6).toFixed(2).replace(/\.?0+$/, '') + 'M';
  if (a >= 1e3) return (n / 1e3).toFixed(1).replace(/\.0$/, '') + 'K';
  return String(n);
}

export function usd(n: number): string {
  return '$' + compact(n);
}

export function price(n: number): string {
  if (n === 0) return '$0';
  if (n >= 1) return '$' + n.toFixed(2);
  if (n >= 0.01) return '$' + n.toFixed(4);
  if (n >= 0.0001) return '$' + n.toFixed(6).replace(/0+$/, '');
  /* Written out in full rather than with subscript-zero notation: the
     subscript digits are missing from most monospace fallbacks. */
  const zeros = -Math.floor(Math.log10(n)) - 1;
  return '$' + n.toFixed(Math.min(12, zeros + 4)).replace(/0+$/, '');
}

export function pct(n: number, digits = 1): string {
  return `${n > 0 ? '+' : ''}${n.toFixed(digits)}%`;
}

export function int(n: number): string {
  return n.toLocaleString('en-US');
}

export function shortAddr(a: string, head = 6, tail = 4): string {
  if (a.length <= head + tail + 2) return a;
  return `${a.slice(0, head)}…${a.slice(-tail)}`;
}

/** Minutes → the largest unit that still reads precisely. Holding times
 *  span seconds to months, so a single unit would be unreadable at one end. */
export function duration(minutes: number): string {
  const m = Math.abs(minutes);
  if (m < 1) return `${Math.round(m * 60)}s`;
  if (m < 60) return `${m < 10 ? m.toFixed(1).replace(/\.0$/, '') : Math.round(m)}m`;
  if (m < 60 * 24) {
    const h = Math.floor(m / 60);
    const rem = Math.round(m % 60);
    return rem ? `${h}h ${rem}m` : `${h}h`;
  }
  if (m < 60 * 24 * 60) {
    const d = Math.floor(m / (60 * 24));
    const h = Math.round((m % (60 * 24)) / 60);
    return h ? `${d}d ${h}h` : `${d}d`;
  }
  return `${(m / (60 * 24 * 30.44)).toFixed(1)}mo`;
}

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

/** UTC throughout — the corpus clock is fixed in UTC, so rendering in the
 *  viewer's zone would shift dates for no reason. */
export function dateShort(ms: number): string {
  const d = new Date(ms);
  return `${String(d.getUTCDate()).padStart(2, '0')} ${MONTHS[d.getUTCMonth()]} ${d.getUTCFullYear()}`;
}

/** yyyy-mm-dd, for <input type="date"> round-tripping. */
export function dateInput(ms: number): string {
  return new Date(ms).toISOString().slice(0, 10);
}

/** Signed currency, compacted. Screener PnL columns need the sign. */
export function signedUsd(n: number): string {
  return `${n < 0 ? '−' : '+'}$${compact(Math.abs(Math.round(n)))}`;
}

/** Risk score → semantic band. Low score = low risk = good. */
export function riskBand(score: number): 'low' | 'medium' | 'high' {
  if (score < 40) return 'low';
  if (score < 65) return 'medium';
  return 'high';
}

/** Quality score → semantic band. High score = good. */
export function qualityBand(score: number): 'low' | 'medium' | 'high' {
  if (score >= 75) return 'high';
  if (score >= 55) return 'medium';
  return 'low';
}

export const bandColor: Record<string, string> = {
  low: 'var(--pos)',
  medium: 'var(--warn)',
  high: 'var(--neg)',
};

/** For quality scores, high is good — invert the palette. */
export const qualityColor: Record<string, string> = {
  high: 'var(--pos)',
  medium: 'var(--warn)',
  low: 'var(--neg)',
};

export const signalColor: Record<string, string> = {
  positive: 'var(--pos)',
  negative: 'var(--neg)',
  neutral: 'var(--warn)',
};

export const verdictMark: Record<string, string> = {
  supported: '✓',
  partial: '~',
  contradicted: '×',
  unknown: '?',
};

export const verdictColor: Record<string, string> = {
  supported: 'var(--pos)',
  partial: 'var(--warn)',
  contradicted: 'var(--neg)',
  unknown: 'var(--ink-4)',
};

export const verdictLabel: Record<string, string> = {
  supported: 'Supported',
  partial: 'Partial',
  contradicted: 'Contradicted',
  unknown: 'Unknown',
};

/** Build an SVG path through points, mildly smoothed. */
export function linePath(
  values: number[],
  w: number,
  h: number,
  pad = 0,
  smooth = true
): string {
  if (values.length === 0) return '';
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const n = values.length;
  const pts = values.map((v, i) => {
    const x = pad + (i / (n - 1 || 1)) * (w - pad * 2);
    const y = pad + (1 - (v - min) / span) * (h - pad * 2);
    return [x, y] as const;
  });

  if (!smooth || pts.length < 3) {
    return pts.map((p, i) => `${i ? 'L' : 'M'}${p[0].toFixed(2)},${p[1].toFixed(2)}`).join('');
  }

  let d = `M${pts[0][0].toFixed(2)},${pts[0][1].toFixed(2)}`;
  for (let i = 0; i < pts.length - 1; i++) {
    const p0 = pts[i];
    const p1 = pts[i + 1];
    const cx = (p0[0] + p1[0]) / 2;
    d += `C${cx.toFixed(2)},${p0[1].toFixed(2)} ${cx.toFixed(2)},${p1[1].toFixed(
      2
    )} ${p1[0].toFixed(2)},${p1[1].toFixed(2)}`;
  }
  return d;
}

/** Polar helper for arcs and rings. */
export function polar(cx: number, cy: number, r: number, deg: number) {
  const rad = ((deg - 90) * Math.PI) / 180;
  return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) };
}

/** Sweeps clockwise from startDeg to endDeg. Direction matters: a dash
 *  reveal on this path has to fill from the low end of the scale up. */
export function arcPath(
  cx: number,
  cy: number,
  r: number,
  startDeg: number,
  endDeg: number
): string {
  const s = polar(cx, cy, r, startDeg);
  const e = polar(cx, cy, r, endDeg);
  const large = Math.abs(endDeg - startDeg) <= 180 ? 0 : 1;
  return `M${s.x.toFixed(2)},${s.y.toFixed(2)} A${r},${r} 0 ${large} 1 ${e.x.toFixed(
    2
  )},${e.y.toFixed(2)}`;
}
