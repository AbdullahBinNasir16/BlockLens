import { useMemo, useRef, useState } from 'react';
import type { Trade } from '../../data/types';
import { BOOK_NOW, INCEPTION, START_CAPITAL, TRADES } from '../../data/portfolio';
import { DAY, EQUITY, byMonth, isOpen, isWin, tradeReturn } from '../../lib/portfolio';
import { compact, dateShort } from '../../lib/format';

/* ============================================================
   The book over time.

   Three bands on one time axis: the equity curve, the positions that
   made it (one bar per trade, from buy to sell), and the months. They
   share an x-axis on purpose — a step in the curve always has a bar
   ending directly beneath it, so the reader can see which trade did it.
   ============================================================ */

type Range = '1m' | '3m' | 'all';
const RANGES: { id: Range; label: string; days: number }[] = [
  { id: '1m', label: '1M', days: 31 },
  { id: '3m', label: '3M', days: 92 },
  { id: 'all', label: 'All', days: Infinity },
];

const W = 1000;
const CH = 290;
const PAD = { l: 6, r: 62, t: 20, b: 24 };
const LANE_H = 15;
const LANE_GAP = 6;
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

const labelPx = (t: Trade) => t.ticker.length * 6.4 + 16;

/** Lanes are packed once over the whole book, so a bar never jumps lanes
 *  when the range changes. A bar too short to hold its own label carries
 *  the label just after it, so that stretch is reserved too — otherwise a
 *  five-day trade's ticker lands on top of the next bar in its lane. */
const LANES = (() => {
  const pxPerDay = (W - PAD.l - PAD.r) / ((BOOK_NOW - INCEPTION) / DAY);
  const ends: number[] = [];
  const lane = new Map<string, number>();
  for (const t of [...TRADES].sort((a, b) => a.entryAt - b.entryAt)) {
    const exit = t.exitAt ?? BOOK_NOW;
    const barPx = ((exit - t.entryAt) / DAY) * pxPerDay;
    const reserved = barPx > labelPx(t) ? exit : exit + ((labelPx(t) + 6) / pxPerDay) * DAY;
    let i = ends.findIndex((e) => e + 2 * DAY < t.entryAt);
    if (i === -1) {
      i = ends.length;
      ends.push(0);
    }
    ends[i] = reserved;
    lane.set(t.id, i);
  }
  return { lane, count: ends.length };
})();

function niceStep(raw: number) {
  const mag = Math.pow(10, Math.floor(Math.log10(raw)));
  const f = raw / mag;
  return (f < 1.5 ? 1 : f < 3 ? 2 : f < 7 ? 5 : 10) * mag;
}

const tone = (t: Trade) => (isOpen(t) ? 'open' : isWin(t) ? 'win' : 'loss');

export function EquityChart({ onSelect }: { onSelect: (t: Trade) => void }) {
  const [range, setRange] = useState<Range>('all');
  const [hover, setHover] = useState<number | null>(null);
  const [hotTrade, setHotTrade] = useState<string | null>(null);
  const svgRef = useRef<SVGSVGElement>(null);

  const days = RANGES.find((r) => r.id === range)!.days;
  const from = Math.max(INCEPTION, BOOK_NOW - days * DAY);

  const geo = useMemo(() => {
    const pts = EQUITY.filter((p) => p.t >= from);
    const vals = pts.map((p) => p.v);
    let lo = Math.min(...vals);
    let hi = Math.max(...vals);
    const pad = (hi - lo || 1) * 0.14;
    lo -= pad;
    hi += pad;

    const x = (t: number) => PAD.l + ((t - from) / (BOOK_NOW - from)) * (W - PAD.l - PAD.r);
    const y = (v: number) => PAD.t + (1 - (v - lo) / (hi - lo)) * (CH - PAD.t - PAD.b);

    const line = pts.map((p, i) => `${i ? 'L' : 'M'}${x(p.t).toFixed(1)},${y(p.v).toFixed(1)}`).join('');
    const area = `${line}L${x(BOOK_NOW).toFixed(1)},${CH - PAD.b}L${x(pts[0].t).toFixed(1)},${CH - PAD.b}Z`;

    const step = niceStep((hi - lo) / 4);
    const yTicks: number[] = [];
    for (let v = Math.ceil(lo / step) * step; v <= hi; v += step) yTicks.push(v);

    /* month starts for the long ranges, weeks for one month */
    const xTicks: { t: number; label: string }[] = [];
    if (range === '1m') {
      for (let t = from + 3 * DAY; t < BOOK_NOW; t += 7 * DAY) xTicks.push({ t, label: dateShort(t).slice(0, 6) });
    } else {
      const d = new Date(from);
      for (let m = d.getUTCMonth() + 1, yr = d.getUTCFullYear(); ; m++) {
        if (m > 11) {
          m = 0;
          yr++;
        }
        const t = Date.UTC(yr, m, 1);
        if (t >= BOOK_NOW) break;
        xTicks.push({ t, label: MONTHS[m] });
      }
    }

    const visible = TRADES.filter((t) => (t.exitAt ?? BOOK_NOW) >= from);
    /* an exit sits on the curve at the day its gain was booked */
    const onCurve = (t: number) => {
      const i = Math.min(EQUITY.length - 1, Math.max(0, Math.ceil((t - INCEPTION) / DAY)));
      return EQUITY[i];
    };

    const months = byMonth()
      .filter((m) => m.end > from)
      .map((m) => ({ ...m, cx: (x(Math.max(m.start, from)) + x(m.end)) / 2 }));

    return { pts, x, y, line, area, lo, hi, yTicks, xTicks, visible, onCurve, months };
  }, [from, range]);

  const lanesTop = CH + 14;
  const lanesH = LANES.count * (LANE_H + LANE_GAP);
  const monthsTop = lanesTop + lanesH + 8;
  const H = monthsTop + 34;

  const point = hover !== null ? geo.pts[hover] : geo.pts[geo.pts.length - 1];
  const first = geo.pts[0];
  const change = point.v / first.v - 1;
  const hotT = hotTrade ? TRADES.find((t) => t.id === hotTrade) ?? null : null;

  const move = (e: React.MouseEvent<SVGSVGElement>) => {
    const r = svgRef.current!.getBoundingClientRect();
    const sx = ((e.clientX - r.left) / r.width) * W;
    const t = from + ((sx - PAD.l) / (W - PAD.l - PAD.r)) * (BOOK_NOW - from);
    let best = 0;
    for (let i = 1; i < geo.pts.length; i++) {
      if (Math.abs(geo.pts[i].t - t) < Math.abs(geo.pts[best].t - t)) best = i;
    }
    setHover(best);
  };

  return (
    <div className="bl-eq">
      <div className="bl-eq__head">
        <div className="bl-eq__read">
          <span className="eyebrow">{hover !== null ? dateShort(point.t) : 'Equity, now'}</span>
          <span className="bl-eq__v num">${Math.round(point.v).toLocaleString('en-US')}</span>
          <span className="bl-eq__d num" data-up={change >= 0}>
            {change >= 0 ? '+' : '−'}
            {Math.abs(change * 100).toFixed(1)}%
            <span className="meta"> over {range === 'all' ? 'the book' : RANGES.find((r) => r.id === range)!.label}</span>
          </span>
        </div>
        <div className="bl-seg bl-seg--sm" role="radiogroup" aria-label="Range">
          {RANGES.map((r) => (
            <button
              key={r.id}
              role="radio"
              aria-checked={range === r.id}
              className="bl-seg__b"
              data-on={range === r.id}
              onClick={() => {
                setRange(r.id);
                setHover(null);
              }}
            >
              {r.label}
            </button>
          ))}
        </div>
      </div>

      <svg
        ref={svgRef}
        className="bl-eq__svg"
        viewBox={`0 0 ${W} ${H}`}
        role="img"
        aria-label={`Portfolio equity, now $${Math.round(EQUITY[EQUITY.length - 1].v).toLocaleString('en-US')}`}
        onMouseMove={move}
        onMouseLeave={() => setHover(null)}
      >
        {/* grid */}
        {geo.yTicks.map((v) => (
          <g key={v}>
            <line x1={PAD.l} x2={W - PAD.r} y1={geo.y(v)} y2={geo.y(v)} stroke="var(--rule-faint)" />
            <text x={W - PAD.r + 10} y={geo.y(v) + 3.5} className="bl-eq__tick">
              ${compact(v)}
            </text>
          </g>
        ))}

        {/* the holding period of the hovered position */}
        {hotT && (
          <rect
            x={geo.x(Math.max(hotT.entryAt, from))}
            y={PAD.t}
            width={Math.max(2, geo.x(hotT.exitAt ?? BOOK_NOW) - geo.x(Math.max(hotT.entryAt, from)))}
            height={lanesTop + lanesH - PAD.t}
            className="bl-eq__span"
            data-tone={tone(hotT)}
          />
        )}

        {START_CAPITAL > geo.lo && START_CAPITAL < geo.hi && (
          <g>
            <line
              x1={PAD.l}
              x2={W - PAD.r}
              y1={geo.y(START_CAPITAL)}
              y2={geo.y(START_CAPITAL)}
              className="bl-eq__start"
            />
            <text x={PAD.l + 4} y={geo.y(START_CAPITAL) - 6} className="bl-eq__startl">
              start · $100K
            </text>
          </g>
        )}

        <path d={geo.area} className="bl-eq__area" />
        <path d={geo.line} className="bl-eq__line" />

        {/* every exit, on the curve, coloured by how it ended */}
        {geo.visible
          .filter((t) => t.exitAt !== null && t.exitAt >= from)
          .map((t) => {
            const p = geo.onCurve(t.exitAt!);
            return (
              <circle
                key={t.id}
                cx={geo.x(p.t)}
                cy={geo.y(p.v)}
                r={hotTrade === t.id ? 6 : 4}
                className="bl-eq__exit"
                data-tone={tone(t)}
                onMouseEnter={() => setHotTrade(t.id)}
                onMouseLeave={() => setHotTrade(null)}
                onClick={() => onSelect(t)}
              />
            );
          })}

        {/* crosshair */}
        {hover !== null && (
          <g className="bl-eq__cross" aria-hidden="true">
            <line x1={geo.x(point.t)} x2={geo.x(point.t)} y1={PAD.t - 6} y2={lanesTop + lanesH} />
            <circle cx={geo.x(point.t)} cy={geo.y(point.v)} r="4.5" />
          </g>
        )}

        {geo.xTicks.map((tk) => (
          <text key={tk.t} x={geo.x(tk.t)} y={CH - 6} textAnchor="middle" className="bl-eq__tick">
            {tk.label}
          </text>
        ))}

        {/* positions */}
        <text x={PAD.l} y={lanesTop - 4} className="bl-eq__band">
          positions
        </text>
        {geo.visible.map((t) => {
          const lane = LANES.lane.get(t.id)!;
          const x0 = geo.x(Math.max(t.entryAt, from));
          const x1 = geo.x(t.exitAt ?? BOOK_NOW);
          const w = Math.max(4, x1 - x0);
          const yy = lanesTop + lane * (LANE_H + LANE_GAP);
          const label = t.ticker;
          const fits = w > labelPx(t);
          return (
            <g
              key={t.id}
              className="bl-eq__pos"
              data-tone={tone(t)}
              data-on={hotTrade === t.id}
              onMouseEnter={() => setHotTrade(t.id)}
              onMouseLeave={() => setHotTrade(null)}
              onClick={() => onSelect(t)}
              role="button"
              tabIndex={0}
              aria-label={`${t.ticker}: ${(tradeReturn(t) * 100).toFixed(0)}%`}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  onSelect(t);
                }
              }}
            >
              <rect x={x0} y={yy} width={w} height={LANE_H} rx={LANE_H / 2} />
              <text
                x={fits ? x0 + 8 : x1 + 5}
                y={yy + LANE_H / 2 + 3.4}
                className="bl-eq__posl"
                data-inside={fits}
              >
                {label}
              </text>
            </g>
          );
        })}

        {/* months */}
        {geo.months.map((m) => (
          <g key={m.start}>
            <line
              x1={geo.x(Math.max(m.start, from))}
              x2={geo.x(Math.max(m.start, from))}
              y1={monthsTop}
              y2={monthsTop + 26}
              stroke="var(--rule)"
            />
            <text x={m.cx} y={monthsTop + 11} textAnchor="middle" className="bl-eq__mon">
              {MONTHS[new Date(m.start).getUTCMonth()]}
            </text>
            <text
              x={m.cx}
              y={monthsTop + 25}
              textAnchor="middle"
              className="bl-eq__monr"
              data-up={m.ret >= 0}
            >
              {m.ret >= 0 ? '+' : '−'}
              {Math.abs(m.ret * 100).toFixed(1)}%
            </text>
          </g>
        ))}
      </svg>
    </div>
  );
}
