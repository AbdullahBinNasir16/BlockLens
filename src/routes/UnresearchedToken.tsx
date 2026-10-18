import { useEffect, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { TokenMark, ChainMark } from '../components/primitives/TokenMark';
import { EmptyNote, Stat } from '../components/primitives/Bits';
import { Icon } from '../components/app/Icons';
import { chainMeta } from '../data/projects';
import { compact, price, pct, int, shortAddr } from '../lib/format';
import { fetchLiveToken, isEvmAddress, type LiveToken } from '../lib/live/token';
import { fetchHolders, type HolderInfo } from '../lib/live/trending';
import { fetchTracked, riskBand, type Launch } from '../lib/live/launches';
import { bandColor } from '../lib/format';

/* ============================================================
   A token BlockLens has not researched.

   The one rule: never render a profile, a score or a sample section
   under a real token's name. This page says the project has not been
   researched and shows only what live public sources report about it
   right now, each figure labelled with where it came from.
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

  const [market, setMarket] = useState<Load<LiveToken | null>>({ state: 'loading' });
  const [holders, setHolders] = useState<Load<HolderInfo>>({ state: 'loading' });
  const [tracked, setTracked] = useState<Launch | null>(null);

  useEffect(() => {
    if (!valid || !supported) return;
    let alive = true;
    setMarket({ state: 'loading' });
    setHolders({ state: 'loading' });
    fetchLiveToken(address)
      .then((v) => alive && setMarket({ state: 'ok', value: v }))
      .catch((e) => alive && setMarket({ state: 'error', msg: String(e?.message ?? e) }));
    fetchTracked(address.toLowerCase())
      .then((t) => alive && setTracked(t))
      .catch(() => alive && setTracked(null));
    fetchHolders(address.toLowerCase(), 0)
      .then((v) => alive && setHolders({ state: 'ok', value: v }))
      .catch((e) => alive && setHolders({ state: 'error', msg: String(e?.message ?? e) }));
    return () => {
      alive = false;
    };
  }, [address, valid, supported]);

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
        </div>
      </header>

      <div className="bl-unres__notice">
        <p className="bl-unres__lede">BlockLens has not researched this project yet.</p>
        <p className="meta">
          There is no intelligence profile, risk score, wallet analysis or KOL record for this
          token, and none is shown. Everything below is live market data from public sources,
          fetched just now. It is not an assessment.
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
              <span className="bl-live__state" data-status={market.state === 'ok' ? 'live' : market.state === 'error' ? 'error' : 'loading'}>
                <span className="bl-live__dot" />
                {market.state === 'loading' ? 'Fetching' : market.state === 'error' ? 'Unavailable' : 'Live · DexScreener'}
              </span>
            </div>
            {market.state === 'loading' && <p className="meta">Looking up Base pairs…</p>}
            {market.state === 'error' && (
              <EmptyNote title="DexScreener could not be reached" detail={market.msg} />
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
                <Stat label="Volume 24h" value={`$${compact(Math.round(top.volume24h))}`} sub={`${int(top.txns24h)} txns`} />
                <Stat label="Market cap" value={top.marketCap ? `$${compact(Math.round(top.marketCap))}` : '—'}
                  sub={top.fdv ? `FDV $${compact(Math.round(top.fdv))}` : undefined} />
                <Stat label="Pool age" value={age(top.createdAt)} sub={top.dex} />
              </div>
            )}
          </section>

          <section className="bl-unres__sec">
            <div className="bl-unres__sech">
              <h2 className="eyebrow">Holders &amp; contract flags</h2>
              <span className="bl-live__state" data-status={holders.state === 'ok' ? 'live' : holders.state === 'error' ? 'error' : 'loading'}>
                <span className="bl-live__dot" />
                {holders.state === 'loading' ? 'Fetching' : holders.state === 'error' ? 'Unavailable' : 'Live · GoPlus'}
              </span>
            </div>
            {holders.state === 'loading' && <p className="meta">Asking GoPlus…</p>}
            {holders.state === 'error' && (
              <EmptyNote title="GoPlus could not be reached" detail={holders.msg} />
            )}
            {h && (
              <div className="bl-unres__grid">
                <Stat label="Holders" value={h.count == null ? '—' : int(h.count)} />
                <Stat
                  label="Top 10 hold"
                  value={h.top10 == null ? '—' : `${h.top10.toFixed(1)}%`}
                  tone={h.top10 != null && h.top10 >= 80 ? 'var(--neg)' : h.top10 != null && h.top10 >= 50 ? 'var(--warn)' : undefined}
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

          {tracked && (
            <section className="bl-unres__sec">
              <div className="bl-unres__sech">
                <h2 className="eyebrow">Launch signals · scored at minute 5</h2>
                <span className="bl-live__state" data-status="live">
                  <span className="bl-live__dot" />
                  Model · buyer-loss-v1
                </span>
              </div>
              <div className="bl-unres__grid">
                <Stat
                  label="Launch type"
                  value={tracked.launch_type === 'self-deployed' ? 'Self-deployed' : tracked.launch_type === 'launchpad' ? 'Launchpad' : '—'}
                  sub={tracked.launch_type === 'self-deployed'
                    ? 'deployer holds withdrawable liquidity; pulled in 109 of 113 held-out launches'
                    : tracked.launch_type === 'launchpad' ? 'liquidity locked at launch; pulled in 0 of 74' : undefined}
                  tone={tracked.launch_type === 'self-deployed' ? 'var(--neg)' : undefined}
                />
                <Stat
                  label="Buyer-loss risk"
                  value={tracked.risk == null ? 'Not scored' : `${Math.round(tracked.risk * 100)}%`}
                  sub={tracked.risk == null ? tracked.status.replace('not scored: ', '')
                    : 'chance a minute-5 buy is worth ≤ half at hour 6'}
                  tone={tracked.risk == null ? undefined : bandColor[riskBand(tracked.risk)]}
                />
                <Stat label="Swaps by minute 5" value={tracked.swaps_by_cutoff ?? '—'} />
                <Stat label="Buyers by minute 5" value={tracked.buyers_by_cutoff ?? '—'} />
              </div>
              <p className="meta" style={{ marginTop: 14 }}>
                A model estimate, validated on 2026 Base launches (see Fresh Launches for the record).
                It describes the launch at minute 5, not the token today.
              </p>
            </section>
          )}

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
        finding. A full investigation requires this project to be researched.
      </p>
    </div>
  );
}
