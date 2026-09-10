import { useMemo, useState } from 'react';
import type { KolProfile } from '../../data/types';
import { compact } from '../../lib/format';

/* ============================================================
   The directory as a field.

   Across: how often an account writes its reasoning down. Up: how often
   its calls work. Size: followers. The two thresholds the reader has set
   are drawn as lines, and the corner they fence off — the accounts that
   pass — is the only shaded region. Accounts filtered out stay on the
   map, greyed, so the filter is seen against what it removed.

   Circles are nudged apart where they would overlap, by a few pixels at
   most and never across a gridline's worth of value.
   ============================================================ */

const W = 760;
const H = 440;
const PAD = { l: 52, r: 22, t: 18, b: 42 };
const Y_MIN = 30;
const Y_MAX = 90;

const x = (thesis: number) => PAD.l + (thesis / 100) * (W - PAD.l - PAD.r);
const y = (win: number) =>
  PAD.t + (1 - (Math.max(Y_MIN, Math.min(Y_MAX, win)) - Y_MIN) / (Y_MAX - Y_MIN)) * (H - PAD.t - PAD.b);

interface Placed {
  k: KolProfile;
  x: number;
  y: number;
  r: number;
}

function layout(kols: KolProfile[]): Placed[] {
  const max = Math.max(...kols.map((k) => k.followers));
  const pts = kols.map((k) => ({
    k,
    x: x(k.thesisScore),
    y: y(k.winRate),
    ox: x(k.thesisScore),
    oy: y(k.winRate),
    r: 11 + Math.sqrt(k.followers / max) * 15,
  }));

  /* relax overlaps, with a spring back to the true position so the nudge
     stays small — deterministic, computed once */
  for (let it = 0; it < 80; it++) {
    for (let i = 0; i < pts.length; i++) {
      for (let j = i + 1; j < pts.length; j++) {
        const a = pts[i];
        const b = pts[j];
        const dx = b.x - a.x || 0.01;
        const dy = b.y - a.y;
        const d = Math.hypot(dx, dy);
        const min = a.r + b.r + 2;
        if (d < min) {
          const push = (min - d) / 2;
          a.x -= (dx / d) * push;
          a.y -= (dy / d) * push;
          b.x += (dx / d) * push;
          b.y += (dy / d) * push;
        }
      }
    }
    for (const p of pts) {
      p.x += (p.ox - p.x) * 0.08;
      p.y += (p.oy - p.y) * 0.08;
      p.x = Math.max(PAD.l + p.r, Math.min(W - PAD.r - p.r, p.x));
      p.y = Math.max(PAD.t + p.r, Math.min(H - PAD.b - p.r, p.y));
    }
  }
  return pts.map(({ k, x, y, r }) => ({ k, x, y, r }));
}

export function KolMap({
  kols,
  passes,
  minWin,
  minThesis,
}: {
  /** every account — the map always shows the whole directory */
  kols: KolProfile[];
  passes: (k: KolProfile) => boolean;
  minWin: number;
  minThesis: number;
}) {
  const placed = useMemo(() => layout(kols), [kols]);
  const [hot, setHot] = useState<string | null>(null);

  /* draw passing accounts above excluded ones, and the hovered one last */
  const order = [...placed].sort((a, b) => {
    const pa = passes(a.k) ? 1 : 0;
    const pb = passes(b.k) ? 1 : 0;
    if (a.k.id === hot) return 1;
    if (b.k.id === hot) return -1;
    return pa - pb || b.r - a.r;
  });

  const active = placed.find((p) => p.k.id === hot)?.k ?? null;
  const shadeX = x(minThesis);
  const shadeY = y(Math.max(Y_MIN, minWin));

  return (
    <div className="bl-kmap">
      <div className="bl-kmap__plot">
        <svg
          viewBox={`0 0 ${W} ${H}`}
          className="bl-kmap__svg"
          role="img"
          aria-label="KOLs by thesis writing and win rate, sized by followers"
          onMouseLeave={() => setHot(null)}
        >
          <defs>
            {placed.map((p) => (
              <clipPath key={p.k.id} id={`kc-${p.k.id}`}>
                <circle cx={p.x} cy={p.y} r={p.r} />
              </clipPath>
            ))}
          </defs>

          {/* the kept corner */}
          <rect
            x={shadeX}
            y={PAD.t}
            width={W - PAD.r - shadeX}
            height={shadeY - PAD.t}
            fill="var(--paper-sunken)"
          />

          {[40, 50, 60, 70, 80, 90].map((v) => (
            <g key={`y${v}`}>
              <line x1={PAD.l} x2={W - PAD.r} y1={y(v)} y2={y(v)} stroke="var(--rule-faint)" />
              <text x={PAD.l - 10} y={y(v) + 3} textAnchor="end" className="bl-kmap__tick">
                {v}%
              </text>
            </g>
          ))}
          {[0, 25, 50, 75, 100].map((v) => (
            <g key={`x${v}`}>
              <line x1={x(v)} x2={x(v)} y1={PAD.t} y2={H - PAD.b} stroke="var(--rule-faint)" />
              <text x={x(v)} y={H - PAD.b + 16} textAnchor="middle" className="bl-kmap__tick">
                {v}
              </text>
            </g>
          ))}
          <text x={W - PAD.r} y={H - 6} textAnchor="end" className="bl-kmap__axis">
            Thesis writing →
          </text>
          {/* reads bottom-to-top, so the arrow points the way the axis grows */}
          <text
            x={14}
            y={H - PAD.b}
            className="bl-kmap__axis"
            transform={`rotate(-90 14 ${H - PAD.b})`}
          >
            Win rate →
          </text>

          {minThesis > 0 && (
            <g>
              <line x1={shadeX} x2={shadeX} y1={PAD.t} y2={H - PAD.b} className="bl-kmap__th" />
              <text x={shadeX + 5} y={H - PAD.b - 6} className="bl-kmap__thl">
                thesis ≥ {minThesis}
              </text>
            </g>
          )}
          {minWin > Y_MIN && (
            <g>
              <line x1={PAD.l} x2={W - PAD.r} y1={shadeY} y2={shadeY} className="bl-kmap__th" />
              <text x={PAD.l + 6} y={shadeY - 6} className="bl-kmap__thl">
                win rate ≥ {minWin}%
              </text>
            </g>
          )}

          {order.map((p) => {
            const ok = passes(p.k);
            const on = hot === p.k.id;
            return (
              <g
                key={p.k.id}
                className="bl-kmap__k"
                data-ok={ok}
                data-on={on}
                onMouseEnter={() => setHot(p.k.id)}
                onFocus={() => setHot(p.k.id)}
                tabIndex={0}
                role="img"
                aria-label={`@${p.k.handle}: win rate ${p.k.winRate}%, thesis ${p.k.thesisScore}${ok ? '' : ', filtered out'}`}
              >
                <circle cx={p.x} cy={p.y} r={p.r + 2} fill="var(--paper)" />
                <image
                  href={`/avatars/${p.k.handle}.jpg`}
                  x={p.x - p.r}
                  y={p.y - p.r}
                  width={p.r * 2}
                  height={p.r * 2}
                  clipPath={`url(#kc-${p.k.id})`}
                  preserveAspectRatio="xMidYMid slice"
                />
                <circle
                  cx={p.x}
                  cy={p.y}
                  r={p.r}
                  fill="none"
                  stroke={on ? 'var(--ink)' : ok ? 'var(--ink-3)' : 'var(--rule-strong)'}
                  strokeWidth={on ? 2 : 1}
                />
              </g>
            );
          })}
        </svg>
      </div>

      <aside className="bl-kmap__read" data-on={!!active}>
        {active ? (
          <>
            <span className="eyebrow">{passes(active) ? 'Passes your filters' : 'Filtered out'}</span>
            <span className="bl-kmap__name">{active.name}</span>
            <a
              className="bl-kmap__handle num"
              href={`https://x.com/${active.handle}`}
              target="_blank"
              rel="noreferrer noopener"
            >
              @{active.handle} ↗
            </a>
            <dl className="bl-kmap__stats">
              <div>
                <dt className="meta">Followers</dt>
                <dd className="num">{compact(active.followers)}</dd>
              </div>
              <div>
                <dt className="meta">Social</dt>
                <dd className="num">{active.socialScore}</dd>
              </div>
              <div>
                <dt className="meta">Win rate</dt>
                <dd className="num">{active.winRate}%</dd>
              </div>
              <div>
                <dt className="meta">Thesis</dt>
                <dd className="num">{active.thesisScore}</dd>
              </div>
              <div>
                <dt className="meta">Outcome</dt>
                <dd
                  className="num"
                  style={{ color: active.avgOutcome >= 0 ? 'var(--pos)' : 'var(--neg)' }}
                >
                  {active.avgOutcome >= 0 ? '+' : '−'}
                  {Math.abs(active.avgOutcome)}%
                </dd>
              </div>
            </dl>
          </>
        ) : (
          <>
            <span className="eyebrow">KOL map</span>
            <p className="bl-kmap__idle">
              Right is more written reasoning, up is more calls that worked. Size is followers.
              The shaded corner is what your win-rate and thesis thresholds keep; anything another
              filter removes is greyed.
            </p>
            <p className="meta bl-kmap__legend">
              {kols.filter(passes).length} pass · {kols.filter((k) => !passes(k)).length} greyed
              out
            </p>
          </>
        )}
      </aside>
    </div>
  );
}
