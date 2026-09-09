import { useMemo, useState } from 'react';
import { linePath } from '../../lib/format';

/* ---------------- Sparkline ---------------- */

export function Sparkline({
  values,
  width = 88,
  height = 26,
  color,
}: {
  values: number[];
  width?: number;
  height?: number;
  color?: string;
}) {
  const up = values[values.length - 1] >= values[0];
  const stroke = color ?? (up ? 'var(--pos)' : 'var(--neg)');
  const d = useMemo(() => linePath(values, width, height, 2), [values, width, height]);
  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} aria-hidden="true">
      <path d={d} fill="none" stroke={stroke} strokeWidth="1.4" strokeLinejoin="round" strokeLinecap="round" />
    </svg>
  );
}

/* ---------------- Area / line chart with crosshair ---------------- */

export function AreaChart({
  data,
  height = 200,
  color = 'var(--ink)',
  fill = true,
  run = true,
  valueFormat = (v: number) => String(v),
  yTicks = 4,
}: {
  data: { t: string; v: number }[];
  height?: number;
  color?: string;
  fill?: boolean;
  run?: boolean;
  valueFormat?: (v: number) => string;
  yTicks?: number;
}) {
  const W = 720;
  const H = height;
  const padL = 8;
  const padR = 8;
  const padT = 14;
  const padB = 22;
  const [hover, setHover] = useState<number | null>(null);

  const vals = data.map((d) => d.v);
  const min = Math.min(...vals);
  const max = Math.max(...vals);
  const span = max - min || 1;

  const xAt = (i: number) => padL + (i / (data.length - 1 || 1)) * (W - padL - padR);
  const yAt = (v: number) => padT + (1 - (v - min) / span) * (H - padT - padB);

  const d = useMemo(() => {
    const pts = data.map((p, i) => [xAt(i), yAt(p.v)] as const);
    let s = `M${pts[0][0].toFixed(1)},${pts[0][1].toFixed(1)}`;
    for (let i = 0; i < pts.length - 1; i++) {
      const cxm = (pts[i][0] + pts[i + 1][0]) / 2;
      s += `C${cxm.toFixed(1)},${pts[i][1].toFixed(1)} ${cxm.toFixed(1)},${pts[i + 1][1].toFixed(
        1
      )} ${pts[i + 1][0].toFixed(1)},${pts[i + 1][1].toFixed(1)}`;
    }
    return s;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data, H]);

  const areaD = `${d} L${xAt(data.length - 1).toFixed(1)},${(H - padB).toFixed(1)} L${padL},${(
    H - padB
  ).toFixed(1)} Z`;

  const gridVals = Array.from({ length: yTicks + 1 }, (_, i) => min + (span * i) / yTicks);

  const onMove = (e: React.MouseEvent<SVGSVGElement>) => {
    const r = e.currentTarget.getBoundingClientRect();
    const x = ((e.clientX - r.left) / r.width) * W;
    const i = Math.round(((x - padL) / (W - padL - padR)) * (data.length - 1));
    setHover(Math.max(0, Math.min(data.length - 1, i)));
  };

  const hi = hover ?? null;

  return (
    <div className="bl-chart">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        preserveAspectRatio="none"
        className="bl-chart__svg"
        style={{ height: H }}
        onMouseMove={onMove}
        onMouseLeave={() => setHover(null)}
      >
        {gridVals.map((g, i) => (
          <line
            key={i}
            x1={padL}
            x2={W - padR}
            y1={yAt(g)}
            y2={yAt(g)}
            stroke="var(--rule-faint)"
            strokeWidth="1"
            vectorEffect="non-scaling-stroke"
          />
        ))}

        {fill && (
          <path
            d={areaD}
            fill={color}
            opacity={run ? 0.06 : 0}
            style={{ transition: 'opacity 700ms var(--ease) 300ms' }}
          />
        )}

        <path
          d={d}
          fill="none"
          stroke={color}
          strokeWidth="1.8"
          vectorEffect="non-scaling-stroke"
          strokeLinejoin="round"
          strokeLinecap="round"
          pathLength={1}
          strokeDasharray={1}
          strokeDashoffset={run ? 0 : 1}
          style={{ transition: 'stroke-dashoffset 1100ms var(--ease)' }}
        />

        {hi !== null && (
          <g>
            <line
              x1={xAt(hi)}
              x2={xAt(hi)}
              y1={padT - 6}
              y2={H - padB}
              stroke="var(--ink)"
              strokeWidth="1"
              strokeDasharray="2 3"
              vectorEffect="non-scaling-stroke"
            />
            <circle cx={xAt(hi)} cy={yAt(data[hi].v)} r="3.6" fill="var(--paper)" stroke={color} strokeWidth="1.8" vectorEffect="non-scaling-stroke" />
          </g>
        )}
      </svg>

      <div className="bl-chart__axis">
        <span className="meta">{data[0]?.t}</span>
        <span className="meta">{data[data.length - 1]?.t}</span>
      </div>

      <div className="bl-chart__read" data-on={hi !== null}>
        {hi !== null ? (
          <>
            <span className="meta">{data[hi].t}</span>
            <span className="num bl-chart__readv">{valueFormat(data[hi].v)}</span>
          </>
        ) : (
          <>
            <span className="meta">Latest</span>
            <span className="num bl-chart__readv">{valueFormat(data[data.length - 1]?.v ?? 0)}</span>
          </>
        )}
      </div>
    </div>
  );
}

/* ---------------- Paired columns (buys vs sells) ---------------- */

export function PairedColumns({
  data,
  height = 168,
  run = true,
}: {
  data: { t: string; buys: number; sells: number }[];
  height?: number;
  run?: boolean;
}) {
  const [hi, setHi] = useState<number | null>(null);
  const max = Math.max(...data.flatMap((d) => [d.buys, d.sells]));

  return (
    <div className="bl-pcol" style={{ height: height + 26 }} onMouseLeave={() => setHi(null)}>
      <div className="bl-pcol__plot" style={{ height }}>
        {data.map((d, i) => (
          <div
            key={d.t}
            className="bl-pcol__grp"
            data-hi={hi === i}
            onMouseEnter={() => setHi(i)}
          >
            <span
              className="bl-pcol__bar bl-pcol__bar--b"
              style={{
                height: run ? `${(d.buys / max) * 100}%` : 0,
                transitionDelay: `${i * 40}ms`,
              }}
            />
            <span
              className="bl-pcol__bar bl-pcol__bar--s"
              style={{
                height: run ? `${(d.sells / max) * 100}%` : 0,
                transitionDelay: `${i * 40 + 60}ms`,
              }}
            />
          </div>
        ))}
      </div>
      <div className="bl-pcol__x">
        {data.map((d, i) => (
          <span key={d.t} className="meta" data-hi={hi === i}>
            {d.t}
          </span>
        ))}
      </div>
      <div className="bl-pcol__tip meta" data-on={hi !== null}>
        {hi !== null && (
          <>
            <b className="num" style={{ color: 'var(--pos)' }}>
              {data[hi].buys.toLocaleString()}
            </b>{' '}
            buys ·{' '}
            <b className="num" style={{ color: 'var(--neg)' }}>
              {data[hi].sells.toLocaleString()}
            </b>{' '}
            sells
          </>
        )}
      </div>
    </div>
  );
}

/* ---------------- Segmented distribution rail ---------------- */

export function DistributionRail({
  segments,
  run = true,
  onHover,
  activeIndex,
}: {
  segments: { label: string; pct: number; signal?: string }[];
  run?: boolean;
  onHover?: (i: number | null) => void;
  activeIndex?: number | null;
}) {
  const shades = ['var(--ink)', '#3d3d39', '#6b6a64', '#9a9891', '#c4c1b8'];
  return (
    <div className="bl-dist" onMouseLeave={() => onHover?.(null)}>
      {segments.map((s, i) => (
        <span
          key={s.label}
          className="bl-dist__seg"
          data-dim={activeIndex !== null && activeIndex !== undefined && activeIndex !== i}
          style={{
            flexBasis: run ? `${s.pct}%` : '0%',
            background: shades[i % shades.length],
            transitionDelay: `${i * 70}ms`,
          }}
          onMouseEnter={() => onHover?.(i)}
          title={`${s.label} — ${s.pct}%`}
        />
      ))}
    </div>
  );
}

/* ---------------- Contribution heatmap ---------------- */

const HEAT = ['var(--rule-faint)', '#d5d2c8', '#a5a29a', '#5f5e58', 'var(--ink)'];

export function Heatmap({
  weeks,
  gap = 3,
  run = true,
}: {
  weeks: number[][];
  gap?: number;
  run?: boolean;
}) {
  const [hi, setHi] = useState<{ w: number; d: number } | null>(null);
  const months = ['Sep', 'Oct', 'Nov', 'Dec', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug'];

  /* Columns are fractional, so the grid always spans the container and the
     month scale above it stays aligned at any width. */
  return (
    <div className="bl-heat">
      <div className="bl-heat__months">
        {months.map((m, i) => (
          <span key={m} className="meta" style={{ left: `${(i / 12) * 100}%` }}>
            {i % 2 === 0 ? m : ''}
          </span>
        ))}
      </div>
      <div
        className="bl-heat__grid"
        style={{ gap, gridTemplateColumns: `repeat(${weeks.length}, 1fr)` }}
        onMouseLeave={() => setHi(null)}
      >
        {weeks.map((week, w) => (
          <div key={w} className="bl-heat__col" style={{ gap }}>
            {week.map((v, d) => (
              <span
                key={d}
                className="bl-heat__c"
                style={{
                  background: run ? HEAT[v] : 'var(--rule-faint)',
                  transitionDelay: `${w * 8}ms`,
                  outline: hi && hi.w === w && hi.d === d ? '1.5px solid var(--ink)' : 'none',
                  outlineOffset: '1px',
                }}
                onMouseEnter={() => setHi({ w, d })}
              />
            ))}
          </div>
        ))}
      </div>
      <div className="bl-heat__legend">
        <span className="bl-heat__tip meta">
          {hi
            ? `${['no', '1–3', '4–8', '9–16', '17+'][weeks[hi.w][hi.d]]} commits · week ${
                hi.w + 1
              } of ${weeks.length}`
            : 'Hover a day'}
        </span>
        <span className="bl-heat__scale">
          <span className="meta">Less</span>
          {HEAT.map((c) => (
            <span key={c} style={{ background: c, width: 10, height: 10 }} />
          ))}
          <span className="meta">More</span>
        </span>
      </div>
    </div>
  );
}
