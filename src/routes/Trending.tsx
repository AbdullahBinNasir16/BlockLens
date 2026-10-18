import { memo, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { TokenMark } from '../components/primitives/TokenMark';
import { Icon } from '../components/app/Icons';
import { compact, price, pct, int, shortAddr } from '../lib/format';
import { findByContract } from '../data/projects';
import type { HolderInfo, LivePool, Window } from '../lib/live/trending';
import { useLiveTrending } from '../lib/live/useLiveTrending';

type SortKey =
  | 'rank'
  | 'price'
  | 'age'
  | 'txns'
  | 'volume'
  | 'makers'
  | 'm5'
  | 'h1'
  | 'h6'
  | 'h24'
  | 'liquidity'
  | 'marketCap'
  | 'holders'
  | 'top10';

const WINDOWS: { k: Window; label: string }[] = [
  { k: 'm5', label: '5M' },
  { k: 'h1', label: '1H' },
  { k: 'h6', label: '6H' },
  { k: 'h24', label: '24H' },
];

const MIN_LIQ = [0, 10_000, 50_000, 250_000];
const MAX_AGE: { label: string; ms: number }[] = [
  { label: 'Any', ms: Infinity },
  { label: '< 24h', ms: 86_400_000 },
  { label: '< 7d', ms: 7 * 86_400_000 },
  { label: '< 30d', ms: 30 * 86_400_000 },
];

const MAX_PAGES = 10;

function age(ms: number): string {
  if (!ms) return '—';
  const m = (Date.now() - ms) / 60_000;
  if (m < 60) return `${Math.max(1, Math.round(m))}m`;
  if (m < 60 * 24) return `${Math.round(m / 60)}h`;
  if (m < 60 * 24 * 30) return `${Math.round(m / 1440)}d`;
  if (m < 60 * 24 * 365) return `${Math.round(m / 43_800)}mo`;
  return `${(m / 525_600).toFixed(1).replace(/\.0$/, '')}y`;
}

function sortValue(p: LivePool, h: HolderInfo | undefined, k: SortKey, w: Window): number {
  switch (k) {
    case 'rank': return p.rank;
    case 'price': return p.price;
    case 'age': return p.createdAt ? -p.createdAt : -Infinity;
    case 'txns': return p.buys[w] + p.sells[w];
    case 'volume': return p.volume[w];
    case 'makers': return p.makers[w] ?? -1;
    case 'm5': case 'h1': case 'h6': case 'h24': return p.change[k];
    case 'liquidity': return p.liquidity;
    case 'marketCap': return p.marketCap;
    case 'holders': return h?.count ?? -1;
    case 'top10': return h?.top10 ?? -1;
  }
}

export function Trending() {
  const nav = useNavigate();
  const [win, setWin] = useState<Window>('h24');
  const [pages, setPages] = useState(2);
  const [paused, setPaused] = useState(false);
  const [sort, setSort] = useState<{ k: SortKey; desc: boolean }>({ k: 'rank', desc: false });
  const [q, setQ] = useState('');
  const [minLiq, setMinLiq] = useState(0);
  const [maxAge, setMaxAge] = useState(0);
  const [hideHoney, setHideHoney] = useState(true);

  const { pools, holders, status, error, updatedAt, running } = useLiveTrending(win, pages, paused);

  /* "updated Ns ago" has to tick on its own */
  const [, setNow] = useState(0);
  useEffect(() => {
    const t = setInterval(() => setNow((n) => n + 1), 1000);
    return () => clearInterval(t);
  }, []);

  const rows = useMemo(() => {
    const needle = q.trim().toLowerCase();
    const ageCap = MAX_AGE[maxAge].ms;
    const f = pools.filter((p) => {
      if (needle && !`${p.name} ${p.symbol} ${p.token} ${p.pool}`.toLowerCase().includes(needle))
        return false;
      if (p.liquidity < MIN_LIQ[minLiq]) return false;
      if (ageCap !== Infinity && (!p.createdAt || Date.now() - p.createdAt > ageCap)) return false;
      if (hideHoney && holders[p.token]?.honeypot) return false;
      return true;
    });
    const dir = sort.desc ? -1 : 1;
    return f.sort(
      (a, b) =>
        dir * (sortValue(a, holders[a.token], sort.k, win) - sortValue(b, holders[b.token], sort.k, win))
    );
  }, [pools, holders, q, minLiq, maxAge, hideHoney, sort, win]);

  const setSortKey = (k: SortKey) =>
    setSort((s) => (s.k === k ? { k, desc: !s.desc } : { k, desc: k !== 'rank' && k !== 'age' }));

  const holdersKnown = pools.filter((p) => holders[p.token]).length;
  const ago = updatedAt ? Math.max(0, Math.round((Date.now() - updatedAt) / 1000)) : null;

  const open = (p: LivePool) => {
    const known = findByContract(p.token);
    nav(known ? `/app/project/${known.project.id}` : `/app/token/${p.token}`);
  };

  const Th = ({ k, label, align = 'r' }: { k: SortKey; label: string; align?: 'r' | 'l' }) => (
    <th className={align === 'r' ? 'bl-th--r' : undefined}>
      <button className="bl-sortth" data-on={sort.k === k} onClick={() => setSortKey(k)}>
        {label}
        <span className="bl-sortth__a" aria-hidden="true">
          {sort.k === k ? (sort.desc ? '↓' : '↑') : ''}
        </span>
      </button>
    </th>
  );

  return (
    <div className="bl-page">
      <header className="bl-page__head">
        <div>
          <p className="eyebrow">Discovery · Base</p>
          <h1 className="display d2">Trending Tokens</h1>
          <p className="bl-page__sub">
            Live from GeckoTerminal and DexScreener. Market data only — open a token to
            investigate it.
          </p>
        </div>
        <div className="bl-page__headr bl-live">
          <span className="bl-live__state" data-status={running ? status : 'paused'}>
            <span className="bl-live__dot" />
            {!running
              ? 'Paused'
              : status === 'loading'
                ? 'Connecting'
                : status === 'limited'
                  ? pools.length ? 'Rate-limited — prices still live' : 'Rate-limited, retrying'
                  : status === 'error'
                    ? pools.length ? 'Ranking stale — retrying' : 'Source unreachable'
                    : 'Live'}
          </span>
          <span className="meta num">{ago === null ? '—' : `Updated ${ago}s ago`}</span>
          <button className="bl-fchip" onClick={() => setPaused((p) => !p)}>
            {paused ? 'Resume' : 'Pause'}
          </button>
        </div>
      </header>

      <div className="bl-filters">
        <div className="bl-filters__grp">
          <span className="eyebrow">Trending</span>
          {WINDOWS.map((w) => (
            <button key={w.k} className="bl-fchip" data-on={win === w.k} onClick={() => setWin(w.k)}>
              {w.label}
            </button>
          ))}
        </div>
        <div className="bl-filters__grp">
          <span className="eyebrow">Min liq</span>
          {MIN_LIQ.map((v, i) => (
            <button key={v} className="bl-fchip" data-on={minLiq === i} onClick={() => setMinLiq(i)}>
              {v ? `$${compact(v)}` : 'Any'}
            </button>
          ))}
        </div>
        <div className="bl-filters__grp">
          <span className="eyebrow">Age</span>
          {MAX_AGE.map((a, i) => (
            <button key={a.label} className="bl-fchip" data-on={maxAge === i} onClick={() => setMaxAge(i)}>
              {a.label}
            </button>
          ))}
        </div>
        <div className="bl-filters__grp">
          <button className="bl-fchip" data-on={hideHoney} onClick={() => setHideHoney((h) => !h)}>
            Hide honeypots
          </button>
        </div>
        <label className="bl-livesearch">
          <Icon.Search size={14} />
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Name, ticker or address"
            spellCheck={false}
          />
        </label>
      </div>

      <div className="bl-tablewrap">
        <table className="bl-table bl-table--live">
          <thead>
            <tr>
              <Th k="rank" label="#" align="l" />
              <th>Token</th>
              <Th k="price" label="Price" />
              <Th k="age" label="Age" />
              <Th k="txns" label={`Txns ${WINDOWS.find((w) => w.k === win)!.label}`} />
              <Th k="volume" label="Volume" />
              <Th k="makers" label="Makers" />
              <Th k="m5" label="5m" />
              <Th k="h1" label="1h" />
              <Th k="h6" label="6h" />
              <Th k="h24" label="24h" />
              <Th k="liquidity" label="Liquidity" />
              <Th k="marketCap" label="Mcap" />
              <Th k="holders" label="Holders" />
              <Th k="top10" label="Top 10" />
              <th />
            </tr>
          </thead>
          <tbody>
            {rows.map((p) => (
              <Row
                key={p.token}
                p={p}
                h={holders[p.token]}
                w={win}
                onOpen={() => open(p)}
              />
            ))}
            {!rows.length && (
              <tr>
                <td colSpan={16} className="bl-live__empty meta">
                  {status === 'loading' && !pools.length
                    ? 'Loading trending pools on Base…'
                    : status === 'limited' && !pools.length
                      ? 'GeckoTerminal rate limit hit — waiting a minute, then retrying.'
                      : status === 'error' && !pools.length
                        ? `Could not load trending pools (${error || 'network error'}). Retrying in 15 seconds.`
                      : 'No tokens match these filters.'}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="bl-live__more">
        {pages < MAX_PAGES && pools.length > 0 && (
          <button className="bl-fchip" onClick={() => setPages((n) => Math.min(MAX_PAGES, n + 2))}>
            Load more
          </button>
        )}
        <span className="meta num">
          {rows.length} of {pools.length} tokens · holders {holdersKnown}/{pools.length}
        </span>
      </div>

      <p className="bl-page__foot meta">
        Ranking and makers: GeckoTerminal, refreshed every minute. Price, volume, txns and
        liquidity: DexScreener, every 10 seconds. Holders, top-10 share and honeypot flag:
        GoPlus, fetched one token at a time and cached for 15 minutes. Paid listings and trending
        rank are not endorsements.
      </p>
    </div>
  );
}

const Change = ({ v }: { v: number }) => (
  <td className="bl-td--r num" style={{ color: v > 0 ? 'var(--pos)' : v < 0 ? 'var(--neg)' : 'var(--ink-4)' }}>
    {v ? pct(v) : '—'}
  </td>
);

const Row = memo(function Row({
  p,
  h,
  w,
  onOpen,
}: {
  p: LivePool;
  h: HolderInfo | undefined;
  w: Window;
  onOpen: () => void;
}) {
  const prev = useRef(p.price);
  const [flash, setFlash] = useState<'up' | 'down' | null>(null);
  useEffect(() => {
    if (p.price === prev.current) return;
    setFlash(p.price > prev.current ? 'up' : 'down');
    prev.current = p.price;
    const t = setTimeout(() => setFlash(null), 900);
    return () => clearTimeout(t);
  }, [p.price]);

  const txns = p.buys[w] + p.sells[w];
  const top10Tone = h?.top10 == null ? undefined : h.top10 >= 80 ? 'var(--neg)' : h.top10 >= 50 ? 'var(--warn)' : undefined;

  return (
    <tr className="bl-tr" onClick={onOpen}>
      <td className="bl-td--n meta num">{p.rank}</td>
      <td>
        <span className="bl-tokencell">
          <TokenMark logo={p.logo} monogram={p.symbol.slice(0, 2)} size={30} />
          <span className="bl-tokencell__b">
            <span className="bl-tokencell__n">
              {p.symbol}
              <span className="bl-live__quote">/{p.quote}</span>
              {h?.honeypot && (
                <span className="bl-tag" data-size="sm" data-tone="negative">
                  Honeypot
                </span>
              )}
            </span>
            <span className="bl-tokencell__t meta" title={p.token}>
              {p.name.length > 22 ? p.name.slice(0, 21) + '…' : p.name} · {shortAddr(p.token, 6, 4)}
            </span>
          </span>
        </span>
      </td>
      <td className="bl-td--r num bl-live__price" data-flash={flash ?? undefined}>
        {price(p.price)}
      </td>
      <td className="bl-td--r num">{age(p.createdAt)}</td>
      <td className="bl-td--r num" title={`${int(p.buys[w])} buys · ${int(p.sells[w])} sells`}>
        {int(txns)}
      </td>
      <td className="bl-td--r num">${compact(Math.round(p.volume[w]))}</td>
      <td className="bl-td--r num">{p.makers[w] == null ? '—' : int(p.makers[w]!)}</td>
      <Change v={p.change.m5} />
      <Change v={p.change.h1} />
      <Change v={p.change.h6} />
      <Change v={p.change.h24} />
      <td className="bl-td--r num">${compact(Math.round(p.liquidity))}</td>
      <td className="bl-td--r num">{p.marketCap ? `$${compact(Math.round(p.marketCap))}` : '—'}</td>
      <td className="bl-td--r num">
        {h ? (h.count == null ? '—' : int(h.count)) : <span className="bl-live__pending">···</span>}
      </td>
      <td className="bl-td--r num" style={{ color: top10Tone }}>
        {h?.top10 == null ? (h ? '—' : <span className="bl-live__pending">···</span>) : `${h.top10.toFixed(1)}%`}
      </td>
      <td className="bl-td--act">
        <span className="bl-rowacts">
          <a
            className="bl-iconbtn"
            href={p.url}
            target="_blank"
            rel="noreferrer"
            title="Open on DexScreener"
            onClick={(e) => e.stopPropagation()}
          >
            <Icon.Ext size={13} />
          </a>
          <span className="bl-rowact">
            {findByContract(p.token) ? 'Open' : 'Details'} <Icon.Arrow size={13} />
          </span>
        </span>
      </td>
    </tr>
  );
});
