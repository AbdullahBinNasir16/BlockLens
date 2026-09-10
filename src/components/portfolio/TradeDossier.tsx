import { Link } from 'react-router-dom';
import type { Trade } from '../../data/types';
import { chainMeta } from '../../data/projects';
import { BOOK_NOW } from '../../data/portfolio';
import { gateChecks, heldDays, isOpen, isWin, multiple, tradePath, tradePnl, tradeReturn } from '../../lib/portfolio';
import { compact, dateShort, price } from '../../lib/format';
import { Drawer } from '../primitives/Bits';
import { MiniRing } from '../primitives/Meters';
import { KindTag, PairMark } from './PairMark';

/* ============================================================
   One trade, read in full.

   Laid out like a short article, because that is what it is: the model
   bought something and has to say why. The figures come first so the
   reader knows how it ended before reading the argument; for a memecoin,
   the lore gets its own block, because the lore was the argument.
   ============================================================ */

function PathChart({ t }: { t: Trade }) {
  const W = 620;
  const H = 170;
  const P = { l: 6, r: 44, t: 18, b: 22 };
  const path = tradePath(t);
  const lo = Math.min(1, ...path) * 0.92;
  const hi = Math.max(1, ...path) * 1.06;
  /* log scale: 2× and 0.5× sit the same distance from the entry line */
  const ly = (v: number) => Math.log(v);
  const x = (i: number) => P.l + (i / Math.max(1, path.length - 1)) * (W - P.l - P.r);
  const y = (v: number) => P.t + (1 - (ly(v) - ly(lo)) / (ly(hi) - ly(lo))) * (H - P.t - P.b);

  const d = path.map((v, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join('');
  const peakI = path.indexOf(Math.max(...path));
  const end = path.length - 1;
  const up = multiple(t) >= 1;
  const ticks = [0.25, 0.5, 1, 2, 4, 8].filter((v) => v > lo && v < hi);

  return (
    <figure className="bl-path">
      <svg viewBox={`0 0 ${W} ${H}`} className="bl-path__svg" role="img" aria-label="Price since entry, as a multiple of the entry price">
        {ticks.map((v) => (
          <g key={v}>
            <line x1={P.l} x2={W - P.r} y1={y(v)} y2={y(v)} className={v === 1 ? 'bl-path__base' : 'bl-path__grid'} />
            <text x={W - P.r + 8} y={y(v) + 3.5} className="bl-path__tick">
              {v}×
            </text>
          </g>
        ))}
        {/* area between the path and entry — gain above, loss below */}
        <path d={`${d}L${x(end)},${y(1)}L${x(0)},${y(1)}Z`} className="bl-path__area" data-up={up} />
        <path d={d} className="bl-path__line" data-up={up} />

        <circle cx={x(0)} cy={y(1)} r="4" className="bl-path__in" />
        <text x={x(0) + 8} y={y(1) + 14} className="bl-path__lab">
          in · {dateShort(t.entryAt).slice(0, 6)}
        </text>

        {peakI > 0 && peakI < end && (
          <g>
            <circle cx={x(peakI)} cy={y(path[peakI])} r="3" className="bl-path__peak" />
            <text x={x(peakI)} y={y(path[peakI]) - 8} textAnchor="middle" className="bl-path__lab">
              peak {t.peak}×
            </text>
          </g>
        )}

        <circle cx={x(end)} cy={y(path[end])} r="4.5" className="bl-path__out" data-up={up} data-open={isOpen(t)} />
        <text x={x(end) - 8} y={y(path[end]) + (up ? -10 : 16)} textAnchor="end" className="bl-path__lab">
          {isOpen(t) ? 'now' : 'out'} · {multiple(t).toFixed(2)}×
        </text>
      </svg>
    </figure>
  );
}

function Gate({ t }: { t: Trade }) {
  return (
    <ul className="bl-dgate">
      {gateChecks(t).map((c) => {
        const pos = Math.min(1, c.value / c.scale);
        const lim = Math.min(1, c.limit / c.scale);
        const shown = c.id === 'liquidity' ? `$${compact(c.value)}` : c.id === 'age' ? `${c.value}h` : c.value;
        const limit = c.id === 'liquidity' ? `$${compact(c.limit)}` : c.id === 'age' ? `${c.limit}h` : c.limit;
        return (
          <li key={c.id} className="bl-dgate__r" data-pass={c.pass}>
            <span className="bl-dgate__k">{c.label}</span>
            <span className="bl-dgate__track" aria-hidden="true">
              {/* the allowed stretch of the scale, then the threshold, then the reading */}
              <span
                className="bl-dgate__ok"
                style={c.side === 'min' ? { left: `${lim * 100}%`, right: 0 } : { left: 0, width: `${lim * 100}%` }}
              />
              <span className="bl-dgate__lim" style={{ left: `${lim * 100}%` }} />
              <span className="bl-dgate__dot" style={{ left: `${pos * 100}%` }} />
            </span>
            <span className="bl-dgate__v num">{shown}</span>
            <span className="bl-dgate__l meta">
              {c.side === 'min' ? '≥' : '≤'} {limit}
            </span>
            <span className="bl-dgate__m" aria-label={c.pass ? 'passed' : 'failed'}>
              {c.pass ? '✓' : '×'}
            </span>
          </li>
        );
      })}
    </ul>
  );
}

export function TradeDossier({ trade, onClose }: { trade: Trade | null; onClose: () => void }) {
  if (!trade) return null;
  const t = trade;
  const ret = tradeReturn(t);
  const up = ret >= 0;
  const open = isOpen(t);
  const status = open ? 'Open' : isWin(t) ? 'Closed · won' : 'Closed · lost';
  const hoursIn = Math.round((t.entryAt - t.launchedAt) / 3_600_000);

  return (
    <Drawer
      open
      onClose={onClose}
      eyebrow={`${chainMeta[t.chain].label} · ${status}`}
      title={<PairMark trade={t} size="xl" />}
      width={720}
    >
      <div className="bl-dos">
        <div className="bl-dos__tags">
          <KindTag kind={t.kind} />
          <span className="meta">
            {t.name} · quoted in {t.quote.name}
          </span>
        </div>

        <div className="bl-dos__figs">
          <div className="bl-dos__ret">
            <span className="eyebrow">{open ? 'Unrealized' : 'Return'}</span>
            <span className="bl-dos__retv num" data-up={up}>
              {up ? '+' : '−'}
              {Math.abs(ret * 100).toFixed(0)}%
            </span>
            <span className="meta num">
              {up ? '+' : '−'}${Math.abs(Math.round(tradePnl(t))).toLocaleString('en-US')} on ${compact(t.size)}
            </span>
          </div>
          <dl className="bl-dos__kv">
            <div>
              <dt>Entry</dt>
              <dd className="num">{price(t.entryPrice)}</dd>
            </div>
            <div>
              <dt>{open ? 'Mark' : 'Exit'}</dt>
              <dd className="num">{price(t.lastPrice)}</dd>
            </div>
            <div>
              <dt>Held</dt>
              <dd className="num">{Math.max(1, Math.round(heldDays(t)))}d</dd>
            </div>
            <div>
              <dt>Bought</dt>
              <dd className="num">
                {hoursIn}h after launch
              </dd>
            </div>
          </dl>
        </div>

        <PathChart t={t} />
        <p className="bl-dos__dates meta">
          {dateShort(t.entryAt)} → {open ? `${dateShort(BOOK_NOW)}, still held` : dateShort(t.exitAt!)}
        </p>

        <section className="bl-dos__sec">
          <h3 className="bl-dos__h">Why it bought</h3>
          <div className="bl-dos__thesis">
            {t.thesis.map((p, i) => (
              <p key={i}>{p}</p>
            ))}
          </div>
        </section>

        {t.kind === 'meme' && (
          <section className="bl-tlore" aria-label="The lore">
            <div className="bl-tlore__top">
              <span className="eyebrow eyebrow-ink">The lore</span>
              <span className="bl-tlore__score">
                <MiniRing value={t.gate.lore} color="var(--ink)" size={52} stroke={3.4}>
                  <span className="num" style={{ fontSize: 14 }}>
                    {t.gate.lore}
                  </span>
                </MiniRing>
                <span className="meta">lore score</span>
              </span>
            </div>

            <blockquote className="bl-tlore__hook">{t.lore.hook}</blockquote>

            <div className="bl-tlore__part">
              <span className="bl-tlore__k">The moment</span>
              <p>{t.lore.origin}</p>
            </div>

            {t.lore.pairing && (
              <div className="bl-tlore__part">
                <span className="bl-tlore__k">The pair</span>
                <div className="bl-tlore__eq" aria-hidden="true">
                  <span className="bl-tlore__tok">{t.ticker}</span>
                  <span className="bl-tlore__in">priced in</span>
                  <span className="bl-tlore__tok bl-tlore__tok--q">
                    {t.quote.ticker}
                    <small>{t.quote.name}</small>
                  </span>
                </div>
                <p>{t.lore.pairing}</p>
              </div>
            )}

            <div className="bl-tlore__part">
              <span className="bl-tlore__k">Why it lasts</span>
              <p>{t.lore.legs}</p>
            </div>
          </section>
        )}

        <section className="bl-dos__sec">
          <h3 className="bl-dos__h">At the gate</h3>
          <Gate t={t} />
        </section>

        <section className="bl-dos__sec">
          <h3 className="bl-dos__h">{open ? 'What would make it sell' : 'Why it sold'}</h3>
          <p className="bl-dos__exit">{t.exitNote}</p>
        </section>

        {t.projectId && (
          <Link to={`/app/project/${t.projectId}`} className="bl-dos__research" onClick={onClose}>
            <span>
              <span className="eyebrow">Researched by BlockLens</span>
              <span className="bl-dos__researcht">Open the {t.name} intelligence profile</span>
            </span>
            <svg viewBox="0 0 20 20" width="18" height="18" aria-hidden="true">
              <path d="M4 10h12M11.5 5.5L16 10l-4.5 4.5" stroke="currentColor" strokeWidth="1.5" fill="none" />
            </svg>
          </Link>
        )}

        <p className="bl-dos__foot meta">
          Simulated trade. Prices and returns are illustrative; lore naming real people and companies
          shows how the model argues and is not a report of events.
        </p>
      </div>
    </Drawer>
  );
}
