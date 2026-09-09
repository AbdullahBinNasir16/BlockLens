import { useMemo } from 'react';
import { linePath } from '../../lib/format';

/* ============================================================
   The hero is an annotated technical plate of a live chain:
   blocks (rounded squares, echoing the mark), wallet nodes,
   connector wires, and three project nodes riding the lattice.

   Performance contract:
   · geometry is computed once at module scope, never per frame
   · the only running animation is stroke-dashoffset on 6 wires
   · scroll drives transform + dashoffset only — no layout, no paint
   ============================================================ */

const W = 1440;
const H = 820;

function seeded(seed: number) {
  let s = seed >>> 0;
  return () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296);
}

/* The layout is an editorial split: type owns the left column, the chain
   owns the right. Nothing is ever drawn left of TYPE_EDGE, and nothing
   below FLOOR, which keeps the plate clear of the status strip. */
const TYPE_EDGE = 740;
const CEIL = 150;
const FLOOR = 655;

/* --- the chain spine, ascending left to right --- */
const BLOCKS = [
  { x: 752, y: 626 },
  { x: 862, y: 566 },
  { x: 972, y: 602 },
  { x: 1082, y: 512 },
  { x: 1192, y: 548 },
  { x: 1302, y: 448 },
  { x: 1412, y: 386 },
];

/* --- three project nodes --- */
const SERIES_UP = [22, 26, 24, 30, 34, 31, 40, 46, 43, 54, 62, 58, 70, 78, 74, 88];
const SERIES_DOWN = [78, 82, 74, 69, 72, 61, 56, 48, 51, 40, 34, 30, 25, 27, 19, 12];
const SERIES_FLAT = [48, 52, 47, 54, 50, 56, 51, 58, 53, 57, 52, 59, 54, 60, 55, 58];

const PROJECTS = [
  {
    id: 'a',
    name: 'PROJECT A',
    x: 768,
    y: 232,
    series: SERIES_UP,
    drift: -74,
    result: '+420%',
    tone: 'pos' as const,
  },
  {
    id: 'b',
    name: 'PROJECT B',
    x: 1232,
    y: 214,
    series: SERIES_DOWN,
    drift: 104,
    result: '−93%',
    tone: 'neg' as const,
  },
  {
    id: 'c',
    name: 'PROJECT C',
    x: 1000,
    y: 256,
    series: SERIES_FLAT,
    drift: -22,
    result: 'FLAT',
    tone: 'neutral' as const,
  },
];

/* Project cards are 124 × 82 and travel by `drift` as you scroll.
   Reserve the whole swept area so no wallet dot is ever underneath one. */
const BOXES = PROJECTS.map((p) => ({
  x0: p.x - 16,
  x1: p.x + 140,
  y0: p.y + Math.min(0, p.drift) - 16,
  y1: p.y + 82 + Math.max(0, p.drift) + 16,
}));

/* --- wallet satellites, generated once, kept clear of type and cards --- */
const WALLETS = (() => {
  const rnd = seeded(41062026);
  const out: { x: number; y: number; r: number; link: number }[] = [];
  let guard = 0;
  while (out.length < 30 && guard++ < 1600) {
    const x = TYPE_EDGE + rnd() * (W - TYPE_EDGE - 24);
    const y = CEIL + rnd() * (FLOOR - CEIL);
    if (BOXES.some((b) => x > b.x0 && x < b.x1 && y > b.y0 && y < b.y1)) continue;
    if (out.some((o) => (o.x - x) ** 2 + (o.y - y) ** 2 < 52 ** 2)) continue;
    let link = 0;
    let best = Infinity;
    BLOCKS.forEach((b, i) => {
      const d = (b.x - x) ** 2 + (b.y - y) ** 2;
      if (d < best) {
        best = d;
        link = i;
      }
    });
    out.push({ x, y, r: rnd() > 0.82 ? 4.2 : rnd() > 0.5 ? 3 : 2.2, link });
  }
  return out;
})();

const ANNOTATIONS = [
  { x: 972, y: 602, tx: 918, ty: 650, text: 'block', anchor: 'end' as const },
  { x: 1192, y: 548, tx: 1252, ty: 614, text: 'contract deploy', anchor: 'start' as const },
  { x: 862, y: 566, tx: 806, ty: 512, text: 'confirmed', anchor: 'end' as const },
  { x: 1412, y: 386, tx: 1362, ty: 326, text: 'pending', anchor: 'end' as const },
  { x: 1132, y: 174, tx: 1190, ty: 152, text: 'wallet', anchor: 'start' as const },
];

const spinePath = BLOCKS.map((b, i) => `${i ? 'L' : 'M'}${b.x},${b.y}`).join(' ');

export function BlockchainPlate({ p }: { p: number }) {
  /* p: 0 → 1 scroll progress through the hero */
  const sparks = useMemo(
    () =>
      PROJECTS.map((pr) => ({
        id: pr.id,
        d: linePath(pr.series, 108, 42, 3),
      })),
    []
  );

  const toneVar = { pos: 'var(--pos)', neg: 'var(--neg)', neutral: 'var(--ink-4)' };

  return (
    <svg
      className="bl-plate"
      viewBox={`0 0 ${W} ${H}`}
      preserveAspectRatio="xMidYMid slice"
      aria-hidden="true"
    >
      {/* ---- wires from wallets to their nearest block ---- */}
      <g stroke="var(--rule-strong)" strokeWidth="0.8" fill="none" opacity="0.75">
        {WALLETS.map((w, i) => {
          const b = BLOCKS[w.link];
          const mx = (w.x + b.x) / 2;
          return <path key={i} d={`M${w.x},${w.y} Q${mx},${w.y} ${b.x},${b.y}`} />;
        })}
      </g>

      {/* ---- the spine ---- */}
      <path d={spinePath} fill="none" stroke="var(--ink-4)" strokeWidth="1.1" />

      {/* ---- travelling transactions: one animated property, 6 elements ---- */}
      <g className="bl-plate__tx" fill="none" strokeLinecap="round">
        {[0, 1, 2, 3, 4, 5].map((i) => (
          <path
            key={i}
            d={spinePath}
            stroke="var(--ink)"
            strokeWidth="2.4"
            strokeDasharray="14 1600"
            style={{ animationDelay: `${i * 1.5}s` }}
          />
        ))}
      </g>

      {/* ---- wallet nodes ---- */}
      <g>
        {WALLETS.map((w, i) => (
          <circle
            key={i}
            cx={w.x}
            cy={w.y}
            r={w.r}
            fill={i % 7 === 0 ? 'var(--ink)' : 'var(--paper)'}
            stroke="var(--ink-3)"
            strokeWidth="1"
          />
        ))}
      </g>

      {/* ---- blocks: rounded squares, the mark's own geometry ---- */}
      <g>
        {BLOCKS.map((b, i) => (
          <g key={i}>
            <rect
              x={b.x - 13}
              y={b.y - 13}
              width="26"
              height="26"
              rx="7"
              fill={i === BLOCKS.length - 1 ? 'var(--paper)' : 'var(--ink)'}
              stroke="var(--ink)"
              strokeWidth="1.4"
            />
            {i === BLOCKS.length - 1 && (
              <rect
                x={b.x - 13}
                y={b.y - 13}
                width="26"
                height="26"
                rx="7"
                fill="none"
                stroke="var(--ink)"
                strokeWidth="1.4"
                className="bl-plate__pending"
              />
            )}
          </g>
        ))}
      </g>

      {/* ---- annotations: leader lines, like a technical plate ---- */}
      <g className="bl-plate__anno">
        {ANNOTATIONS.map((a, i) => (
          <g key={i}>
            <path
              d={`M${a.x},${a.y} L${a.tx},${a.ty}`}
              stroke="var(--ink-4)"
              strokeWidth="0.8"
              fill="none"
            />
            <circle cx={a.x} cy={a.y} r="2.4" fill="var(--ink)" />
            <text
              x={a.tx + (a.anchor === 'start' ? 6 : -6)}
              y={a.ty - 5}
              textAnchor={a.anchor}
              fontFamily="var(--mono)"
              fontSize="11"
              letterSpacing="0.14em"
              fill="var(--ink-3)"
              stroke="var(--paper)"
              strokeWidth="3.4"
              paintOrder="stroke"
            >
              {a.text.toUpperCase()}
            </text>
          </g>
        ))}
      </g>

      {/* ---- project nodes: they ride the lattice as you scroll ---- */}
      <g>
        {PROJECTS.map((pr, idx) => {
          const dy = pr.drift * p;
          const spark = sparks[idx];
          const revealed = p > 0.34;
          return (
            <g
              key={pr.id}
              transform={`translate(${pr.x} ${pr.y + dy})`}
              style={{ transition: 'transform 60ms linear' }}
            >
              {/* trail showing where it came from */}
              <line
                x1="60"
                y1={-dy}
                x2="60"
                y2="0"
                stroke={toneVar[pr.tone]}
                strokeWidth="1"
                strokeDasharray="2 4"
                opacity={Math.min(0.55, Math.abs(dy) / 60)}
              />
              <rect
                x="0"
                y="0"
                width="124"
                height="82"
                rx="16"
                fill="var(--paper)"
                stroke="var(--ink)"
                strokeWidth="1.2"
              />
              <text
                x="12"
                y="20"
                fontFamily="var(--mono)"
                fontSize="10"
                letterSpacing="0.16em"
                fill="var(--ink-3)"
              >
                {pr.name}
              </text>
              {/* the chart already exists at rest; scrolling extends it
                  and commits it to a colour */}
              <g transform="translate(8 26)">
                <path
                  d={spark.d}
                  fill="none"
                  stroke={p > 0.18 ? toneVar[pr.tone] : 'var(--ink-4)'}
                  strokeWidth="1.6"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  pathLength={1}
                  strokeDasharray={1}
                  strokeDashoffset={Math.max(0, 0.55 - p * 1.4)}
                  style={{ transition: 'stroke 200ms var(--ease)' }}
                />
              </g>
              <text
                x="112"
                y="74"
                textAnchor="end"
                fontFamily="var(--mono)"
                fontSize="12"
                letterSpacing="0.04em"
                fill={toneVar[pr.tone]}
                opacity={revealed ? 1 : 0}
                style={{ transition: 'opacity 240ms var(--ease)' }}
              >
                {pr.result}
              </text>
              {/* flag */}
              {revealed && pr.tone !== 'neutral' && (
                <g transform="translate(104 12)" opacity={revealed ? 1 : 0}>
                  <circle r="8" fill={toneVar[pr.tone]} />
                  <text
                    textAnchor="middle"
                    dominantBaseline="central"
                    fontFamily="var(--mono)"
                    fontSize="10"
                    fill="#fff"
                    dy="0.5"
                  >
                    {pr.tone === 'pos' ? '✓' : '!'}
                  </text>
                </g>
              )}
            </g>
          );
        })}
      </g>
    </svg>
  );
}
