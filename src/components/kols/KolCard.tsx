import { Link } from 'react-router-dom';
import type { KolProfile, Project } from '../../data/types';
import { XAvatar } from '../primitives/XAvatar';
import { MiniRing, BarScale } from '../primitives/Meters';
import { TokenMark, ChainMark } from '../primitives/TokenMark';
import { compact, qualityBand, qualityColor } from '../../lib/format';

export type KolSortKey = 'followers' | 'socialScore' | 'winRate' | 'thesisScore' | 'avgOutcome' | 'calls';

/* One account. The measure the list is sorted by is lifted on every card,
   so a reader scanning down the grid is comparing the thing they asked
   about rather than hunting for it. */

function Metric({
  label,
  value,
  bar,
  color,
  on,
}: {
  label: string;
  value: React.ReactNode;
  bar?: number;
  color: string;
  on: boolean;
}) {
  return (
    <div className="bl-kc__row" data-on={on}>
      <dt className="bl-kc__rl">{label}</dt>
      <dd className="bl-kc__rv num" style={bar === undefined ? { color } : undefined}>
        {value}
      </dd>
      {bar !== undefined && (
        <span className="bl-kc__rb">
          <BarScale value={bar} color={color} height={3} />
        </span>
      )}
    </div>
  );
}

export function KolCard({
  kol,
  rank,
  sort,
  covered,
  run,
}: {
  kol: KolProfile;
  rank: number;
  sort: KolSortKey;
  /** indexed projects this account has covered */
  covered: Project[];
  run: boolean;
}) {
  const winColor = qualityColor[qualityBand(kol.winRate)];
  const up = kol.avgOutcome >= 0;

  return (
    <article className="bl-kc">
      <span className="bl-kc__rank num">{String(rank).padStart(2, '0')}</span>

      <header className="bl-kc__h">
        <XAvatar handle={kol.handle} size={58} />
        <span className="bl-kc__who">
          <span className="bl-kc__name">{kol.name}</span>
          <a
            className="bl-kc__handle num"
            href={`https://x.com/${kol.handle}`}
            target="_blank"
            rel="noreferrer noopener"
          >
            @{kol.handle}
            <svg viewBox="0 0 20 20" width="10" height="10" aria-hidden="true">
              <path d="M7 13L13 7M8 7h5v5" stroke="currentColor" strokeWidth="1.6" fill="none" />
            </svg>
          </a>
        </span>
      </header>

      <div className="bl-kc__tags">
        {kol.focus.map((f) => (
          <span key={f} className="bl-kc__tag">
            {f}
          </span>
        ))}
        <span className="bl-kc__chains">
          {kol.chains.map((c) => (
            <ChainMark key={c} chain={c} size={14} />
          ))}
        </span>
      </div>

      <div className="bl-kc__body">
        <span className="bl-kc__ring" data-on={sort === 'socialScore'}>
          <MiniRing value={kol.socialScore} color="var(--ink)" size={72} stroke={3.6} run={run}>
            <span className="num" style={{ fontSize: 18 }}>
              {kol.socialScore}
            </span>
          </MiniRing>
          <span className="eyebrow">Social</span>
        </span>

        <dl className="bl-kc__m">
          <Metric
            label="Win rate"
            value={`${kol.winRate}%`}
            bar={run ? kol.winRate : 0}
            color={winColor}
            on={sort === 'winRate'}
          />
          <Metric
            label="Thesis"
            value={kol.thesisScore}
            bar={run ? kol.thesisScore : 0}
            color="var(--ink-2)"
            on={sort === 'thesisScore'}
          />
          <Metric
            label="Outcome"
            value={`${up ? '+' : '−'}${Math.abs(kol.avgOutcome)}%`}
            color={up ? 'var(--pos)' : 'var(--neg)'}
            on={sort === 'avgOutcome'}
          />
        </dl>
      </div>

      <footer className="bl-kc__f">
        <span className="bl-kc__fs" data-on={sort === 'followers'}>
          <b className="num">{compact(kol.followers)}</b> followers
        </span>
        <span className="bl-kc__fs" data-on={sort === 'calls'}>
          <b className="num">{kol.calls}</b> calls
        </span>
        {covered.length > 0 && (
          <span className="bl-kc__cov" title="Indexed projects this account has covered">
            {covered.map((p) => (
              <Link key={p.id} to={`/app/project/${p.id}`} title={`${p.name} — open research`}>
                <TokenMark logo={p.logo} monogram={p.monogram} size={20} radius={6} />
              </Link>
            ))}
          </span>
        )}
      </footer>
    </article>
  );
}
