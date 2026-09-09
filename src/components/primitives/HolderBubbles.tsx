import { useMemo, useState } from 'react';
import type { Holder } from '../../data/types';
import { compact } from '../../lib/format';
import { cropBox, spiralPack } from '../../lib/pack';

/* ============================================================
   Holder field.

   Area is proportional to position size, so a wallet twice the size
   of another draws twice the ink — radius scales with the square root.
   Colour carries behaviour: green for wallets that hold and add, red
   for wallets that bought and left, neutral grey for everything else.

   Packing is a deterministic spiral with collision push-back — no
   simulation loop, so it costs nothing per frame.
   ============================================================ */

const TONE: Record<string, { fill: string; stroke: string; text: string }> = {
  smart: { fill: 'var(--pos-soft)', stroke: 'var(--pos)', text: 'var(--pos)' },
  seller: { fill: 'var(--neg-soft)', stroke: 'var(--neg)', text: 'var(--neg)' },
  neutral: { fill: 'var(--paper)', stroke: 'var(--ink-4)', text: 'var(--ink-3)' },
};

const W = 320;
const H = 200;

interface Packed extends Holder {
  x: number;
  y: number;
  r: number;
}

function pack(holders: Holder[]): Packed[] {
  const max = Math.max(...holders.map((h) => h.pct));
  /* sqrt keeps area proportional; clamp so dust is still clickable */
  const radius = (pct: number) => Math.max(7, Math.sqrt(pct / max) * 34);

  const ordered = [...holders].sort((a, b) => b.pct - a.pct);
  const circles = spiralPack(
    ordered.map((h) => radius(h.pct)),
    { cx: W / 2, cy: H / 2, step: 13.5, stretch: 1.32, gap: 3, push: 2.2 }
  );
  return ordered.map((h, i) => ({ ...h, ...circles[i] }));
}

export function HolderBubbles({
  holders,
  onSelect,
  run = true,
}: {
  holders: Holder[];
  onSelect?: (h: Holder) => void;
  run?: boolean;
}) {
  const { bubbles, box } = useMemo(() => {
    const b = pack(holders);
    return { bubbles: b, box: cropBox(b, 6) };
  }, [holders]);
  const [hot, setHot] = useState<string | null>(null);
  const active = bubbles.find((b) => b.address === hot) ?? null;

  const counts = {
    smart: holders.filter((h) => h.behaviour === 'smart').length,
    seller: holders.filter((h) => h.behaviour === 'seller').length,
    neutral: holders.filter((h) => h.behaviour === 'neutral').length,
  };

  return (
    <div className="bl-bub">
      <div className="bl-bub__plot">
        <svg
          viewBox={box}
          preserveAspectRatio="xMidYMid meet"
          className="bl-bub__svg"
          onMouseLeave={() => setHot(null)}
        >
          {bubbles.map((b, i) => {
            const tone = TONE[b.behaviour];
            const on = hot === b.address;
            const dim = hot !== null && !on;
            return (
              <g
                key={b.address}
                opacity={run ? (dim ? 0.32 : 1) : 0}
                style={{
                  transition: `opacity 360ms var(--ease) ${i * 34}ms`,
                  cursor: onSelect ? 'pointer' : 'default',
                }}
                onMouseEnter={() => setHot(b.address)}
                onClick={() => onSelect?.(b)}
              >
                <circle
                  cx={b.x}
                  cy={b.y}
                  r={run ? b.r : 0}
                  fill={tone.fill}
                  stroke={tone.stroke}
                  strokeWidth={on ? 1.6 : 1}
                  style={{ transition: `r 520ms var(--ease) ${i * 34}ms` }}
                />
                {b.r > 15 && (
                  <text
                    x={b.x}
                    y={b.y + 1.5}
                    textAnchor="middle"
                    fontFamily="var(--mono)"
                    fontSize={b.r > 24 ? 8 : 6.5}
                    fill={tone.text}
                    style={{ pointerEvents: 'none' }}
                  >
                    {b.pct}%
                  </text>
                )}
              </g>
            );
          })}
        </svg>

        {/* readout sits beside the field rather than floating over it */}
        <div className="bl-bub__read" data-on={!!active}>
          {active ? (
            <>
              <span className="bl-bub__tag" style={{ color: TONE[active.behaviour].text }}>
                ● {active.behaviour === 'seller' ? 'quick seller' : active.behaviour}
              </span>
              <span className="bl-bub__label">{active.label}</span>
              <span className="bl-bub__addr num">{active.address}</span>
              <div className="bl-bub__stats">
                <span>
                  <b className="num">{active.pct}%</b> of supply
                </span>
                <span>
                  <b className="num">${compact(active.value)}</b>
                </span>
                <span>
                  held <b className="num">{active.held}</b>
                </span>
                <span
                  className="num"
                  style={{
                    color:
                      active.change === 0
                        ? 'var(--ink-4)'
                        : active.change > 0
                          ? 'var(--pos)'
                          : 'var(--neg)',
                  }}
                >
                  {active.change === 0
                    ? 'flat 24h'
                    : `${active.change > 0 ? '+' : ''}${active.change}% 24h`}
                </span>
              </div>
              <p className="bl-bub__note">{active.note}</p>
            </>
          ) : (
            <>
              <span className="eyebrow">Holder field</span>
              <p className="bl-bub__idle">
                Each circle is a holder. Area is the size of the position. Hover one to read it.
              </p>
              <div className="bl-bub__legend">
                <span style={{ color: TONE.smart.text }}>
                  ● {counts.smart} holding &amp; adding
                </span>
                <span style={{ color: TONE.neutral.text }}>● {counts.neutral} neutral</span>
                <span style={{ color: TONE.seller.text }}>● {counts.seller} quick sellers</span>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
