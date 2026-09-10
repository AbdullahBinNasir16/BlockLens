import { useEffect, useMemo, useState } from 'react';
import type { WalletMatch } from '../../data/types';
import { datasets } from '../../data/projects';
import { cropBox, spiralPack } from '../../lib/pack';
import { dateShort, duration, int, shortAddr, signedUsd } from '../../lib/format';
import { TokenMark } from '../primitives/TokenMark';
import { Icon } from '../app/Icons';
import { SORTS, type SortKey } from './ResultsTable';

/* ============================================================
   Wallets as a field.

   Size is whatever the results are sorted by, so switching the sort
   redraws the question: sorted by PnL, the biggest circle made the most;
   sorted by win rate, it won most often. Colour never changes meaning —
   green took profit, red took a loss. Placement follows the sort order,
   first at the centre.
   ============================================================ */

/** A field past this many circles stops being readable. The list keeps
 *  every row; the field shows the top of the current sort. */
const LIMIT = 60;

const DAY = 24 * 60 * 60 * 1000;

function magnitude(m: WalletMatch, k: SortKey, oldest: number): number {
  switch (k) {
    case 'realizedPnl':
      return Math.abs(m.realizedPnl);
    case 'winRate':
      return m.winRate;
    /* holding times span seconds to months; linear sizing would leave one
       giant and fifty specks */
    case 'avgHoldingTime':
      return Math.log1p(m.avgHoldingTime);
    case 'matched':
      return m.matchedProjects.length;
    case 'lastActive':
      return (m.lastActive - oldest) / DAY + 1;
  }
}

function metricLabel(m: WalletMatch, k: SortKey): string {
  switch (k) {
    case 'realizedPnl':
      return signedUsd(m.realizedPnl);
    case 'winRate':
      return `${m.winRate.toFixed(0)}%`;
    case 'avgHoldingTime':
      return duration(m.avgHoldingTime);
    case 'matched':
      return `${m.matchedProjects.length}`;
    case 'lastActive':
      return dateShort(m.lastActive).slice(0, 6);
  }
}

const tone = (pnl: number) =>
  pnl > 0
    ? { fill: 'var(--pos-soft)', stroke: 'var(--pos)', text: 'var(--pos)' }
    : pnl < 0
      ? { fill: 'var(--neg-soft)', stroke: 'var(--neg)', text: 'var(--neg)' }
      : { fill: 'var(--paper)', stroke: 'var(--ink-4)', text: 'var(--ink-3)' };

export function WalletBubbles({
  rows,
  sort,
  desc,
  onOpen,
}: {
  rows: WalletMatch[];
  sort: SortKey;
  desc: boolean;
  onOpen: (m: WalletMatch) => void;
}) {
  const shown = useMemo(() => rows.slice(0, LIMIT), [rows]);

  const { circles, box } = useMemo(() => {
    const oldest = Math.min(...shown.map((m) => m.lastActive));
    const vals = shown.map((m) => magnitude(m, sort, oldest));
    const max = Math.max(...vals, 1e-9);
    /* sqrt keeps area proportional; the floor keeps a zero clickable */
    const radii = vals.map((v) => Math.max(7, Math.sqrt(v / max) * 42));
    const c = spiralPack(radii, { cx: 300, cy: 190, step: 15, stretch: 1.5, gap: 3, push: 2.4 });
    return { circles: c, box: cropBox(c, 8) };
  }, [shown, sort]);

  /* grow in once per new field — a re-sort or a new search replays it */
  const [run, setRun] = useState(false);
  useEffect(() => {
    setRun(false);
    const id = requestAnimationFrame(() => setRun(true));
    return () => cancelAnimationFrame(id);
  }, [shown, sort]);

  const [hot, setHot] = useState<string | null>(null);
  const active = shown.find((m) => m.wallet.address === hot) ?? null;
  const sortLabel = SORTS.find((s) => s.k === sort)?.label ?? sort;
  const profit = shown.filter((m) => m.realizedPnl > 0).length;
  const loss = shown.filter((m) => m.realizedPnl < 0).length;

  return (
    <div className="bl-wbub">
      <div className="bl-wbub__plot">
        <svg
          viewBox={box}
          preserveAspectRatio="xMidYMid meet"
          className="bl-wbub__svg"
          role="img"
          aria-label={`${shown.length} wallets sized by ${sortLabel}`}
          onMouseLeave={() => setHot(null)}
        >
          {shown.map((m, i) => {
            const c = circles[i];
            const t = tone(m.realizedPnl);
            const on = hot === m.wallet.address;
            const dim = hot !== null && !on;
            const delay = Math.min(i, 40) * 18;
            return (
              <g
                key={m.wallet.address}
                className="bl-wbub__g"
                opacity={run ? (dim ? 0.3 : 1) : 0}
                style={{ transition: `opacity 320ms var(--ease) ${delay}ms` }}
                onMouseEnter={() => setHot(m.wallet.address)}
                onFocus={() => setHot(m.wallet.address)}
                onClick={() => onOpen(m)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    onOpen(m);
                  }
                }}
                tabIndex={0}
                role="button"
                aria-label={`${shortAddr(m.wallet.address)} — ${metricLabel(m, sort)}`}
              >
                <circle
                  cx={c.x}
                  cy={c.y}
                  r={run ? c.r : 0}
                  fill={t.fill}
                  stroke={t.stroke}
                  strokeWidth={on ? 1.8 : 1}
                  style={{ transition: `r 480ms var(--ease) ${delay}ms` }}
                />
                {c.r > 17 && (
                  <text
                    x={c.x}
                    y={c.y + 3}
                    textAnchor="middle"
                    fontFamily="var(--mono)"
                    fontSize={c.r > 30 ? 10 : 8}
                    fill={t.text}
                    style={{ pointerEvents: 'none' }}
                  >
                    {metricLabel(m, sort)}
                  </text>
                )}
              </g>
            );
          })}
        </svg>
      </div>

      {/* the readout sits beside the field rather than floating over it */}
      <aside className="bl-wbub__read" data-on={!!active}>
        {active ? (
          <>
            <span className="eyebrow">Wallet</span>
            <span className="bl-wbub__addr num">{shortAddr(active.wallet.address, 10, 8)}</span>
            {(active.wallet.ens || active.wallet.label) && (
              <span className="bl-wbub__label">{active.wallet.ens ?? active.wallet.label}</span>
            )}
            <dl className="bl-wbub__stats">
              <div>
                <dt className="meta">PnL</dt>
                <dd
                  className="num"
                  style={{ color: active.realizedPnl >= 0 ? 'var(--pos)' : 'var(--neg)' }}
                >
                  {signedUsd(active.realizedPnl)}
                </dd>
              </div>
              <div>
                <dt className="meta">Win rate</dt>
                <dd className="num">{active.winRate.toFixed(0)}%</dd>
              </div>
              <div>
                <dt className="meta">Avg hold</dt>
                <dd className="num">{duration(active.avgHoldingTime)}</dd>
              </div>
              <div>
                <dt className="meta">Last active</dt>
                <dd className="num">{dateShort(active.lastActive)}</dd>
              </div>
            </dl>
            <span className="bl-wbub__marks">
              {[...new Set(active.matchedProjects)].map((id) => {
                const p = datasets[id]?.project;
                return p ? (
                  <TokenMark key={id} logo={p.logo} monogram={p.monogram} size={22} radius={7} />
                ) : null;
              })}
              <span className="meta">
                {active.matchedProjects.length}/{active.projectsTraded} projects matched
              </span>
            </span>
            <span className="bl-wbub__open meta">
              Click to open <Icon.Arrow size={12} />
            </span>
          </>
        ) : (
          <>
            <span className="eyebrow">Wallet field</span>
            <p className="bl-wbub__idle">
              Sized by <b>{sortLabel}</b>, {desc ? 'highest' : 'lowest'} at the centre. Hover a
              circle to read it; click to open it.
            </p>
            <div className="bl-wbub__legend meta">
              <span style={{ color: 'var(--pos)' }}>● {profit} in profit</span>
              <span style={{ color: 'var(--neg)' }}>● {loss} at a loss</span>
            </div>
            {rows.length > LIMIT && (
              <p className="meta bl-wbub__cap">
                Showing the first {LIMIT} of {int(rows.length)}. The list view keeps every row.
              </p>
            )}
          </>
        )}
      </aside>
    </div>
  );
}
