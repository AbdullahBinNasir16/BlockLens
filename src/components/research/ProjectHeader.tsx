import { useState } from 'react';
import { chainMeta } from '../../data/projects';
import { useProject } from '../../lib/project-context';
import { TokenMark, ChainMark } from '../primitives/TokenMark';
import { XAvatar } from '../primitives/XAvatar';
import { Sparkline } from '../primitives/Charts';
import { Icon } from '../app/Icons';
import { useCopy } from '../../lib/hooks';
import { compact, price, pct, int, shortAddr } from '../../lib/format';

function sparkFor(change: number, seed: number) {
  let s = seed >>> 0;
  const rnd = () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296);
  const drift = Math.max(-1, Math.min(1, change / 60));
  const out: number[] = [];
  let v = 50 - drift * 22;
  for (let i = 0; i < 16; i++) {
    v += drift * 2.75 + (rnd() - 0.5) * 9;
    out.push(Math.max(4, Math.min(96, v)));
  }
  return out;
}

export function ProjectHeader() {
  const { project } = useProject();
  const [copied, copy] = useCopy();
  const [watched, setWatched] = useState(true);
  const m = project.metrics;
  const up = m.priceChange24h >= 0;

  const links = [
    { k: 'Explorer', v: project.links.explorer },
    { k: 'Website', v: project.links.website },
    { k: 'X', v: project.links.x && `x.com/${project.links.x}` },
    { k: 'GitHub', v: project.links.github && `github.com/${project.links.github}` },
    { k: 'Docs', v: project.links.docs },
    { k: 'Telegram', v: project.links.telegram },
    { k: 'Discord', v: project.links.discord },
    ...(project.links.extra ?? []).map((e) => ({ k: e.label, v: e.url })),
  ].filter((l) => l.v) as { k: string; v: string }[];

  const metrics = [
    {
      k: 'Price',
      v: price(m.price),
      s: pct(m.priceChange24h),
      tone: up ? 'var(--pos)' : 'var(--neg)',
    },
    { k: 'Market cap', v: `$${compact(m.marketCap)}`, s: `FDV $${compact(m.fdv)}` },
    {
      k: 'Volume 24h',
      v: `$${compact(m.volume24h)}`,
      s: `${int(m.txns24h.buys + m.txns24h.sells)} txns`,
    },
    {
      k: 'Liquidity',
      v: `$${compact(m.liquidity)}`,
      s: `${((m.liquidity / m.marketCap) * 100).toFixed(1)}% of cap`,
      tone: m.liquidity / m.marketCap < 0.05 ? 'var(--warn)' : undefined,
    },
    { k: 'Holders', v: int(m.holders), s: pct(m.holdersChange24h), tone: 'var(--pos)' },
    { k: 'Pair age', v: m.ageLabel, s: `since ${project.deployedAt}` },
    { k: 'Category', v: project.category, s: project.categoryDetail },
  ];

  return (
    <header className="bl-ph">
      <div className="bl-ph__top">
        <div className="bl-ph__id">
          <TokenMark
            logo={project.logo}
            monogram={project.monogram}
            chain={project.chain}
            size={64}
            radius={20}
            chainBadge
          />
          <div className="bl-ph__names">
            <h1 className="bl-ph__name display">{project.name}</h1>
            <div className="bl-ph__sub">
              <span className="bl-ph__ticker num">${project.ticker}</span>
              <span className="bl-ph__dot" />
              <span className="bl-chaindot">
                <ChainMark chain={project.chain} size={13} />
                {chainMeta[project.chain].label}
              </span>
              <span className="bl-ph__dot" />
              <button
                className="bl-ph__addr num"
                onClick={() => copy(project.contract)}
                title="Copy contract address"
              >
                {shortAddr(project.contract, 10, 6)}
                <span className="bl-ph__copy">
                  {copied ? <Icon.Check size={13} /> : <Icon.Copy size={13} />}
                </span>
              </button>
              {copied && <span className="meta bl-ph__copied">Copied</span>}
            </div>
          </div>
        </div>

        <div className="bl-ph__right">
          <div className="bl-ph__spark">
            <Sparkline
              values={sparkFor(m.priceChange24h, project.id.length * 977)}
              width={132}
              height={38}
              color={up ? 'var(--pos)' : 'var(--neg)'}
            />
            <span className="meta">24h</span>
          </div>
          <button className="bl-btn bl-btn--sm bl-btn--ghost" onClick={() => setWatched((w) => !w)}>
            <Icon.Star size={13} filled={watched} />
            {watched ? 'Watching' : 'Watch'}
          </button>
        </div>
      </div>

      <nav className="bl-ph__links">
        {project.links.x && (
          <a
            className="bl-plink bl-plink--x"
            href={`https://x.com/${project.links.x}`}
            target="_blank"
            rel="noreferrer noopener"
          >
            <XAvatar handle={project.links.x} size={20} />
            <span className="bl-plink__k">@{project.links.x}</span>
            <Icon.Ext size={12} />
          </a>
        )}
        {links
          .filter((l) => l.k !== 'X')
          .map((l) => (
            <a
              key={l.k}
              className="bl-plink"
              href={l.v.startsWith('http') ? l.v : `https://${l.v}`}
              target="_blank"
              rel="noreferrer noopener"
            >
              <span className="bl-plink__k">{l.k}</span>
              <Icon.Ext size={12} />
            </a>
          ))}
        <span className="bl-ph__venue meta">{project.venue}</span>
      </nav>

      <div className="bl-ph__strip">
        {metrics.map((x) => (
          <div key={x.k} className="bl-phm">
            <span className="bl-phm__k eyebrow">{x.k}</span>
            <span className="bl-phm__v num">{x.v}</span>
            <span className="bl-phm__s meta" style={x.tone ? { color: x.tone } : undefined}>
              {x.s}
            </span>
          </div>
        ))}
      </div>
    </header>
  );
}
