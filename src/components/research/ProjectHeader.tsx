import { useEffect, useState } from 'react';
import { chainMeta } from '../../data/projects';
import { SNAPSHOT_DATE, useProject, useProjectLive } from '../../lib/project-context';
import { TokenMark, ChainMark } from '../primitives/TokenMark';
import { XAvatar } from '../primitives/XAvatar';
import { ProvChip } from '../primitives/Bits';
import { Icon } from '../app/Icons';
import { useCopy } from '../../lib/hooks';
import { compact, price, pct, int, shortAddr } from '../../lib/format';
import { addWatch, fetchWatchlist, removeWatch } from '../../lib/live/product';

export function ProjectHeader() {
  const { project } = useProject();
  const live = useProjectLive();
  const mk = live.provenance === 'live' ? live.data?.market.data ?? null : null;
  const sec = live.provenance === 'live' ? live.data?.security.data ?? null : null;
  const top = mk?.pairs[0];
  const isLive = !!top;
  const [copied, copy] = useCopy();
  const [watched, setWatched] = useState(false);
  const [canWatch, setCanWatch] = useState(false);
  useEffect(() => {
    let alive = true;
    fetchWatchlist()
      .then((w) => {
        if (!alive) return;
        setCanWatch(true);
        setWatched(w.some((i) => i.address === project.contract.toLowerCase()));
      })
      .catch(() => alive && setCanWatch(false));
    return () => {
      alive = false;
    };
  }, [project.contract]);
  const toggleWatch = () => {
    const next = !watched;
    setWatched(next);
    (next ? addWatch(project.contract, project.ticker) : removeWatch(project.contract)).catch(() =>
      setWatched(!next)
    );
  };
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

  /* Live from the API when it answers; otherwise the dated snapshot the
     case study was built from, under a Sample badge. Never a mix. */
  const ageOf = (ms: number) => {
    const d = (Date.now() - ms) / 86_400_000;
    return d < 1 ? `${Math.max(1, Math.round(d * 24))}h` : d < 60 ? `${Math.round(d)}d` : `${(d / 30.44).toFixed(1)}mo`;
  };
  const metrics = top
    ? [
        {
          k: 'Price',
          v: price(top.price),
          s: pct(top.change24h),
          tone: top.change24h >= 0 ? 'var(--pos)' : 'var(--neg)',
        },
        {
          k: 'Market cap',
          v: top.marketCap ? `$${compact(top.marketCap)}` : '—',
          s: top.fdv ? `FDV $${compact(top.fdv)}` : '',
        },
        {
          k: 'Volume 24h',
          v: `$${compact(top.volume24h)}`,
          s: `${int(top.buys24h + top.sells24h)} txns`,
        },
        {
          k: 'Liquidity',
          v: `$${compact(top.liquidity)}`,
          s: top.marketCap ? `${((top.liquidity / top.marketCap) * 100).toFixed(1)}% of cap` : `deepest pool · ${top.quote}`,
          tone: top.marketCap && top.liquidity / top.marketCap < 0.05 ? 'var(--warn)' : undefined,
        },
        {
          k: 'Holders',
          v: sec?.holders == null ? '—' : int(sec.holders),
          s: sec?.top10Pct == null ? 'GoPlus' : `top 10 hold ${sec.top10Pct.toFixed(0)}%`,
        },
        { k: 'Pair age', v: top.createdAt ? ageOf(top.createdAt) : '—', s: top.dex },
        { k: 'Category', v: project.category, s: project.categoryDetail },
      ]
    : [
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
        { k: 'Holders', v: int(m.holders), s: pct(m.holdersChange24h) },
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
          <ProvChip
            live={isLive}
            why={live.loading ? 'loading live market data' : `snapshot of ${SNAPSHOT_DATE}, not live`}
            note={
              isLive
                ? 'Market figures from DexScreener and GoPlus, through the BlockLens API, fetched just now.'
                : `The API could not be used (${live.reason}). These are the figures captured on ${SNAPSHOT_DATE}.`
            }
          />
          <button
            className="bl-btn bl-btn--sm bl-btn--ghost"
            onClick={toggleWatch}
            disabled={!canWatch}
            title={canWatch ? undefined : 'The BlockLens API is not reachable'}
          >
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
