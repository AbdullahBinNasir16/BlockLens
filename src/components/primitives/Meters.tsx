import { arcPath, polar } from '../../lib/format';

/* ---------------- Mini ring ---------------- */

export function MiniRing({
  value,
  color,
  size = 56,
  stroke = 4,
  run = true,
  delay = 0,
  children,
}: {
  value: number;
  color: string;
  size?: number;
  stroke?: number;
  run?: boolean;
  delay?: number;
  children?: React.ReactNode;
}) {
  const R = 50 - stroke * 1.4;
  const C = 2 * Math.PI * R;
  const frac = Math.max(0, Math.min(1, value / 100));
  return (
    <span className="bl-mini" style={{ width: size, height: size }}>
      <svg viewBox="0 0 100 100" width={size} height={size} aria-hidden="true">
        <circle cx="50" cy="50" r={R} fill="none" stroke="var(--rule)" strokeWidth={stroke * 1.6} />
        <circle
          cx="50"
          cy="50"
          r={R}
          fill="none"
          stroke={color}
          strokeWidth={stroke * 1.6}
          strokeLinecap="round"
          strokeDasharray={C}
          strokeDashoffset={run ? C * (1 - frac) : C}
          transform="rotate(-90 50 50)"
          style={{ transition: `stroke-dashoffset 820ms var(--ease) ${delay}ms` }}
        />
      </svg>
      <span className="bl-mini__in">{children}</span>
    </span>
  );
}

/* ---------------- Arc meter (half dial) ---------------- */

export function ArcMeter({
  value,
  color,
  width = 132,
  run = true,
  delay = 0,
  showNeedle = false,
}: {
  value: number;
  color: string;
  width?: number;
  run?: boolean;
  delay?: number;
  /** off by default — the filled arc already carries the reading, and a
   *  pivot dot in the middle of a small dial reads as clutter */
  showNeedle?: boolean;
}) {
  const h = width * 0.61;
  const cx = 100;
  const cy = 92;
  const R = 74;
  const start = -110;
  const end = 110;
  const frac = Math.max(0, Math.min(1, value / 100));
  const deg = start + (end - start) * frac;

  /* dash animation along the arc */
  const arcLen = (Math.abs(end - start) / 360) * 2 * Math.PI * R;
  const tip = polar(cx, cy, R, deg);
  const base = polar(cx, cy, R - 22, deg);

  return (
    /* 122 tall, not 116: at ±110° the arc ends dip just past the pivot line */
    <svg viewBox="0 0 200 122" width={width} height={h} aria-hidden="true" className="bl-arc">
      <path
        d={arcPath(cx, cy, R, start, end)}
        fill="none"
        stroke="var(--rule)"
        strokeWidth="8"
        strokeLinecap="round"
      />
      <path
        d={arcPath(cx, cy, R, start, end)}
        fill="none"
        stroke={color}
        strokeWidth="8"
        strokeLinecap="round"
        strokeDasharray={arcLen}
        strokeDashoffset={run ? arcLen * (1 - frac) : arcLen}
        style={{ transition: `stroke-dashoffset 900ms var(--ease) ${delay}ms` }}
      />
      {[0, 25, 50, 75, 100].map((t) => {
        const d = start + (end - start) * (t / 100);
        const a = polar(cx, cy, R + 8, d);
        const b = polar(cx, cy, R + 13, d);
        return (
          <line key={t} x1={a.x} y1={a.y} x2={b.x} y2={b.y} stroke="var(--rule-strong)" strokeWidth="1.2" />
        );
      })}
      {showNeedle && (
        <g
          style={{
            transformOrigin: `${cx}px ${cy}px`,
            transition: `opacity 400ms var(--ease) ${delay + 500}ms`,
            opacity: run ? 1 : 0,
          }}
        >
          <line x1={base.x} y1={base.y} x2={tip.x} y2={tip.y} stroke="var(--ink)" strokeWidth="1.6" />
          <circle cx={cx} cy={cy} r="3.4" fill="var(--ink)" />
        </g>
      )}
    </svg>
  );
}

/* ---------------- Dot scale ---------------- */

export function DotScale({
  value,
  color,
  count = 10,
  run = true,
  delay = 0,
  dot = 6,
}: {
  value: number;
  color: string;
  count?: number;
  run?: boolean;
  delay?: number;
  dot?: number;
}) {
  const filled = Math.round((value / 100) * count);
  return (
    <span className="bl-dots" style={{ gap: Math.max(3, dot * 0.55) }}>
      {Array.from({ length: count }, (_, i) => (
        <span
          key={i}
          className="bl-dots__d"
          style={{
            width: dot,
            height: dot,
            background: run && i < filled ? color : 'var(--rule)',
            transition: `background 200ms var(--ease) ${delay + i * 26}ms`,
          }}
        />
      ))}
    </span>
  );
}

/* ---------------- Horizontal hairline scale ---------------- */

export function BarScale({
  value,
  color,
  run = true,
  delay = 0,
  height = 3,
  marker,
}: {
  value: number;
  color: string;
  run?: boolean;
  delay?: number;
  height?: number;
  marker?: number;
}) {
  return (
    <span className="bl-bar" style={{ height }}>
      <span className="bl-bar__track" />
      <span
        className="bl-bar__fill"
        style={{
          width: run ? `${value}%` : 0,
          background: color,
          transition: `width 760ms var(--ease) ${delay}ms`,
        }}
      />
      {marker !== undefined && (
        <span className="bl-bar__marker" style={{ left: `${marker}%` }} />
      )}
    </span>
  );
}

/* ---------------- Labelled gauge ----------------
   A reading, its scale, and what the reading means — in one unit.
   Used wherever a number needs context rather than a card. */

export function Gauge({
  label,
  value,
  display,
  caption,
  color,
  sourced,
  run = true,
  delay = 0,
  width = 150,
}: {
  label: string;
  /** 0-100 position on the dial; higher always means healthier */
  value: number;
  /** what to print in the middle; defaults to the value */
  display?: string;
  caption?: string;
  color: string;
  /** when given, marks whether the figure was sourced or is illustrative */
  sourced?: boolean;
  run?: boolean;
  delay?: number;
  width?: number;
}) {
  /* readings are words as often as numbers, so the type has to flex */
  const text = String(display ?? Math.round(value));
  const size = text.length > 13 ? 15 : text.length > 9 ? 18 : text.length > 6 ? 22 : 27;

  return (
    <figure className="bl-gauge" style={{ width }}>
      <ArcMeter value={value} color={color} width={width} run={run} delay={delay} />
      <figcaption>
        {/* the reading sits under the dial — inside it, a word would collide
            with both the arc and the needle */}
        <span className="bl-gauge__v num" style={{ color, fontSize: size }}>
          {text}
        </span>
        <span className="bl-gauge__l eyebrow">
          {sourced !== undefined && (
            <span
              className="bl-src"
              data-on={sourced}
              title={
                sourced
                  ? 'Sourced from a public endpoint'
                  : 'Illustrative — not a measured figure'
              }
            />
          )}
          {label}
        </span>
        {caption && <span className="bl-gauge__c meta">{caption}</span>}
      </figcaption>
    </figure>
  );
}

/* ---------------- Radial fingerprint (all parameters at once) ---------------- */

export function Radar({
  points,
  size = 260,
  run = true,
  activeIndex,
  onHover,
}: {
  points: { label: string; value: number }[];
  size?: number;
  run?: boolean;
  activeIndex?: number | null;
  onHover?: (i: number | null) => void;
}) {
  const cx = 100;
  const cy = 100;
  const R = 74;
  const n = points.length;

  const coords = points.map((p, i) => {
    const deg = (i / n) * 360;
    return polar(cx, cy, (R * p.value) / 100, deg);
  });
  const outer = points.map((_, i) => polar(cx, cy, R, (i / n) * 360));

  const poly = coords.map((c) => `${c.x.toFixed(1)},${c.y.toFixed(1)}`).join(' ');
  const collapsed = points.map(() => `${cx},${cy}`).join(' ');

  return (
    <svg
      viewBox="0 0 200 200"
      width={size}
      height={size}
      className="bl-radar"
      onMouseLeave={() => onHover?.(null)}
    >
      {[0.25, 0.5, 0.75, 1].map((r) => (
        <circle
          key={r}
          cx={cx}
          cy={cy}
          r={R * r}
          fill="none"
          stroke="var(--rule)"
          strokeWidth="0.6"
          strokeDasharray={r === 1 ? undefined : '1.5 2.5'}
        />
      ))}
      {outer.map((o, i) => (
        <line
          key={i}
          x1={cx}
          y1={cy}
          x2={o.x}
          y2={o.y}
          stroke={activeIndex === i ? 'var(--ink-3)' : 'var(--rule)'}
          strokeWidth={activeIndex === i ? 1 : 0.6}
        />
      ))}
      <polygon
        points={run ? poly : collapsed}
        fill="var(--ink)"
        fillOpacity="0.07"
        stroke="var(--ink)"
        strokeWidth="1.2"
        strokeLinejoin="round"
        style={{ transition: 'all 900ms var(--ease)' }}
      />
      {coords.map((c, i) => (
        <circle
          key={i}
          cx={run ? c.x : cx}
          cy={run ? c.y : cy}
          r={activeIndex === i ? 3.4 : 2}
          fill={activeIndex === i ? 'var(--ink)' : 'var(--paper)'}
          stroke="var(--ink)"
          strokeWidth="1.1"
          style={{ transition: 'all 900ms var(--ease)', cursor: 'pointer' }}
          onMouseEnter={() => onHover?.(i)}
        />
      ))}
    </svg>
  );
}
