import { useEffect, useRef, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { TokenMark, ChainMark } from '../components/primitives/TokenMark';
import { EmptyNote, Stat } from '../components/primitives/Bits';
import { Icon } from '../components/app/Icons';
import { chainMeta } from '../data/projects';
import { compact, price, pct, int, shortAddr } from '../lib/format';
import { isEvmAddress } from '../lib/live/token';
import { apiGet } from '../lib/api';
import type { ProjectLiveResponse } from '../data/api';
import { ProvChip } from '../components/primitives/Bits';
import { RiskPanel } from '../components/live/RiskPanel';
import { addWatch, fetchWatchlist, recordInvestigation, removeWatch } from '../lib/live/product';

/* ============================================================
   A token BlockLens has not researched.

   The one rule: never render a profile, a score or a sample section
   under a real token's name. This page says the project has not been
   researched and shows only what live public sources report about it
   right now, each figure labelled with where it came from. All of it
   comes through the BlockLens API (`/api/project`); when the API is down
   the page says so, because there is no honest sample for a real token.
   ============================================================ */

type Load<T> = { state: 'loading' } | { state: 'ok'; value: T } | { state: 'error'; msg: string };

function age(ms: number): string {
  if (!ms) return '—';
  const h = (Date.now() - ms) / 3_600_000;
  if (h < 1) return `${Math.max(1, Math.round(h * 60))} minutes`;
  if (h < 48) return `${Math.round(h)} hours`;
  if (h < 24 * 60) return `${Math.round(h / 24)} days`;
  return `${(h / 24 / 30.44).toFixed(1)} months`;
}

export function UnresearchedToken() {
  const { address = '' } = useParams();
  const [params] = useSearchParams();
  const chain = params.get('chain') ?? 'base';
  const valid = isEvmAddress(address);
  const supported = chain === 'base';

  const [live, setLive] = useState<Load<ProjectLiveResponse>>({ state: 'loading' });
  const [watched, setWatched] = useState<boolean | null>(null);
  const logged = useRef('');

  useEffect(() => {
    if (!valid || !supported) return;
    let alive = true;
    setLive({ state: 'loading' });
    apiGet<ProjectLiveResponse>(`/api/project/${address.toLowerCase()}`, 20_000)
      .then((v) => {
        if (!alive) return;
        setLive({ state: 'ok', value: v });
        if (logged.current !== address) {
          logged.current = address;
          recordInvestigation(address, v.risk.state === 'out_of_scope' ? 'live' : 'tracked');
        }
      })
      .catch((e) => alive && setLive({ state: 'error', msg: String(e?.message ?? e) }));
    fetchWatchlist()
      .then((w) => alive && setWatched(w.some((i) => i.address === address.toLowerCase())))
      .catch(() => alive && setWatched(null));
    return () => {
      alive = false;
    };
  }, [address, valid, supported]);

  const v = live.state === 'ok' ? live.value : null;
  type MarketData = NonNullable<ProjectLiveResponse['market']['data']>;
  type SecurityData = NonNullable<ProjectLiveResponse['security']['data']>;
  const market: Load<MarketData | null> =
    live.state === 'loading'
      ? { state: 'loading' }
      : live.state === 'error'
        ? { state: 'error', msg: live.msg }
        : v!.market.error
          ? { state: 'error', msg: v!.market.error }
          : { state: 'ok', value: v!.market.data ?? null };
  const holders: Load<SecurityData | null> =
    live.state === 'loading'
      ? { state: 'loading' }
      : live.state === 'error'
        ? { state: 'error', msg: live.msg }
        : v!.security.error
          ? { state: 'error', msg: v!.security.error }
          : { state: 'ok', value: v!.security.data ?? null };
  const tok = market.state === 'ok' ? market.value : null;
  const top = tok?.pairs[0];
  const h = holders.state === 'ok' ? holders.value : null;

  return (
    <div className="bl-page bl-unres">
      <header className="bl-page__head">
        <div className="bl-unres__ident">
          {tok && <TokenMark logo={tok.logo} monogram={tok.symbol.slice(0, 2)} size={52} radius={16} />}
          <div>
            <p className="eyebrow">Not researched</p>
            <h1 className="display d2">
              {tok ? (
                <>
                  {tok.name} <span className="bl-unres__sym">${tok.symbol}</span>
                </>
              ) : (
                'Unknown token'
              )}
            </h1>
            <p className="bl-unres__addr num" title={address}>
              {shortAddr(address, 12, 8)}
            </p>
          </div>
        </div>
        <div className="bl-page__headr">
          <span className="bl-tag" data-tone="ink">
            <ChainMark chain={chain} size={13} />
            {chainMeta[chain]?.label ?? chain}
          </span>
          {valid && supported && (
            <button
              className="bl-btn bl-btn--sm bl-btn--ghost"
              disabled={watched === null}
              title={watched === null ? 'The BlockLens API is not reachable' : undefined}
              onClick={() => {
                const next = !watched;
                setWatched(next);
                (next ? addWatch(address, tok?.symbol) : removeWatch(address)).catch(() => setWatched(!next));
              }}
            >
              <Icon.Star size={13} filled={!!watched} />
              {watched ? 'Watching' : 'Watch'}
            </button>
          )}
        </div>
      </header>

      <div className="bl-unres__notice">
        <p className="bl-unres__lede">BlockLens has not researched this project yet.</p>
        <p className="meta">
          There is no hand-built research profile for this token, and no sample section is shown
          under its name. Everything below is live, fetched just now through the BlockLens API:
          market data, holder data, and the model's view where the model was built to give one.
        </p>
      </div>

      {!valid ? (
        <EmptyNote
          title="That is not a contract address"
          detail="Expected 0x followed by 40 hexadecimal characters."
        />
      ) : !supported ? (
        <EmptyNote
          title={`Live lookup covers Base only`}
          detail={`No live source is wired for ${chainMeta[chain]?.label ?? chain} yet, so there is nothing to show.`}
        />
      ) : (
        <>
          <section className="bl-unres__sec">
            <div className="bl-unres__sech">
              <h2 className="eyebrow">Market</h2>
              {market.state === 'ok' ? (
                <ProvChip live note="DexScreener, through the BlockLens API, fetched just now" />
              ) : market.state === 'error' ? (
                <ProvChip live={false} empty why="unavailable right now" />
              ) : (
                <span className="meta">Fetching…</span>
              )}
            </div>
            {market.state === 'loading' && <p className="meta">Looking up Base pairs…</p>}
            {market.state === 'error' && (
              <EmptyNote
                title="Market data could not be fetched"
                detail={`${market.msg}. No sample figures are shown for a real token.`}
              />
            )}
            {market.state === 'ok' && !tok && (
              <EmptyNote
                title="No trading pair found on Base"
                detail="DexScreener lists no Base pool for this address. It may not have launched, or it may not be a token."
              />
            )}
            {top && (
              <div className="bl-unres__grid">
                <Stat label="Price" value={price(top.price)} sub={top.change24h ? `${pct(top.change24h)} 24h` : undefined}
                  tone={undefined} />
                <Stat label="Liquidity" value={`$${compact(Math.round(top.liquidity))}`} sub={`deepest pool · ${top.quote}`} />
                <Stat label="Volume 24h" value={`$${compact(Math.round(top.volume24h))}`} sub={`${int(top.buys24h + top.sells24h)} txns`} />
                <Stat label="Market cap" value={top.marketCap ? `$${compact(Math.round(top.marketCap))}` : '—'}
                  sub={top.fdv ? `FDV $${compact(Math.round(top.fdv))}` : undefined} />
                <Stat label="Pool age" value={age(top.createdAt)} sub={top.dex} />
              </div>
            )}
          </section>

          <section className="bl-unres__sec">
            <div className="bl-unres__sech">
              <h2 className="eyebrow">Holders &amp; contract flags</h2>
              {holders.state === 'ok' ? (
                <ProvChip live note="GoPlus Security, through the BlockLens API, fetched just now" />
              ) : holders.state === 'error' ? (
                <ProvChip live={false} empty why="unavailable right now" />
              ) : (
                <span className="meta">Fetching…</span>
              )}
            </div>
            {holders.state === 'loading' && <p className="meta">Asking GoPlus…</p>}
            {holders.state === 'error' && (
              <EmptyNote
                title="Holder data could not be fetched"
                detail={`${holders.msg}. No sample figures are shown for a real token.`}
              />
            )}
            {holders.state === 'ok' && !h && (
              <EmptyNote title="GoPlus has no record of this address" detail="It may not be a token on Base." />
            )}
            {h && (
              <div className="bl-unres__grid">
                <Stat
                  label="Holders"
                  value={h.holders ? int(h.holders) : '—'}
                  sub={h.holders === 0 ? 'not yet indexed by GoPlus' : undefined}
                />
                <Stat
                  label="Top 10 hold"
                  value={h.top10Pct == null ? '—' : `${h.top10Pct.toFixed(1)}%`}
                  tone={h.top10Pct != null && h.top10Pct >= 80 ? 'var(--neg)' : h.top10Pct != null && h.top10Pct >= 50 ? 'var(--warn)' : undefined}
                />
                <Stat
                  label="Honeypot"
                  value={h.honeypot == null ? 'Unknown' : h.honeypot ? 'Flagged' : 'Not flagged'}
                  tone={h.honeypot ? 'var(--neg)' : undefined}
                  sub="GoPlus simulation"
                />
              </div>
            )}
          </section>

          <RiskPanel
            risk={v?.risk ?? null}
            unavailable={live.state === 'error' ? live.msg : undefined}
          />

          {tok && tok.pairs.length > 0 && (
            <section className="bl-unres__sec">
              <div className="bl-unres__sech">
                <h2 className="eyebrow">Pools · {tok.pairs.length}</h2>
              </div>
              <div className="bl-tablewrap">
                <table className="bl-table">
                  <thead>
                    <tr>
                      <th>Pair</th>
                      <th>DEX</th>
                      <th className="bl-th--r">Price</th>
                      <th className="bl-th--r">Liquidity</th>
                      <th className="bl-th--r">Volume 24h</th>
                      <th className="bl-th--r">Age</th>
                      <th />
                    </tr>
                  </thead>
                  <tbody>
                    {tok.pairs.slice(0, 8).map((p) => (
                      <tr key={p.pool}>
                        <td className="num">
                          {tok.symbol}/{p.quote} <span className="meta">{shortAddr(p.pool, 6, 4)}</span>
                        </td>
                        <td className="meta">{p.dex}</td>
                        <td className="bl-td--r num">{price(p.price)}</td>
                        <td className="bl-td--r num">${compact(Math.round(p.liquidity))}</td>
                        <td className="bl-td--r num">${compact(Math.round(p.volume24h))}</td>
                        <td className="bl-td--r num">{age(p.createdAt)}</td>
                        <td className="bl-td--act">
                          <a className="bl-iconbtn" href={p.url} target="_blank" rel="noreferrer" title="Open on DexScreener">
                            <Icon.Ext size={13} />
                          </a>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          )}
        </>
      )}

      <div className="bl-unres__actions">
        <Link className="bl-fchip" to="/app/new">New investigation</Link>
        <Link className="bl-fchip" to="/app/trending">Trending on Base</Link>
      </div>

      <p className="bl-page__foot meta">
        Market data: DexScreener. Holders, top-10 share and honeypot flag: GoPlus Security. Both
        are third-party readings at the moment of loading and can be wrong; neither is a BlockLens
        finding. The model risk comes from the BlockLens live feed and is shown only for launches it
        scored at their own minute 5. A full investigation requires this project to be researched.
      </p>
    </div>
  );
}
