import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { EmptyNote } from '../components/primitives/Bits';
import { Icon } from '../components/app/Icons';
import { findByContract } from '../data/projects';
import { shortAddr } from '../lib/format';
import { fetchSymbols } from '../lib/live/launches';
import { fetchWatchlist, removeWatch, type WatchItem } from '../lib/live/product';

/* ============================================================
   Watchlist — tokens the user is keeping an eye on, held by the API.
   ============================================================ */

type Load<T> = { state: 'loading' } | { state: 'ok'; value: T } | { state: 'error'; msg: string };

function when(iso: string): string {
  return iso.slice(0, 16).replace('T', ' ');
}

export function WatchlistPage() {
  const nav = useNavigate();
  const [items, setItems] = useState<Load<WatchItem[]>>({ state: 'loading' });
  const [names, setNames] = useState<Record<string, { symbol: string; name: string }>>({});

  useEffect(() => {
    let alive = true;
    fetchWatchlist()
      .then(async (w) => {
        if (!alive) return;
        setItems({ state: 'ok', value: w });
        const got = await fetchSymbols(w.map((i) => i.address));
        if (alive) setNames(got);
      })
      .catch((e) => alive && setItems({ state: 'error', msg: String(e?.message ?? e) }));
    return () => {
      alive = false;
    };
  }, []);

  const rows = items.state === 'ok' ? items.value : [];
  const open = (a: string) => {
    const known = findByContract(a);
    nav(known ? `/app/project/${known.project.id}` : `/app/token/${a}`);
  };

  return (
    <div className="bl-page">
      <header className="bl-page__head">
        <div>
          <p className="eyebrow">Saved</p>
          <h1 className="display d2">Watchlist</h1>
          <p className="bl-page__sub">Tokens you starred. Open one for its live data and, if it was tracked at launch, its minute-5 signals.</p>
        </div>
        <div className="bl-page__headr">
          <span className="meta">{rows.length} tokens</span>
        </div>
      </header>

      {items.state === 'error' && (
        <EmptyNote title="The BlockLens API is not answering" detail={`${items.msg}. The watchlist lives in the API's store.`} />
      )}
      {items.state === 'ok' && rows.length === 0 && (
        <EmptyNote title="Watchlist is empty" detail="Star a token from its page, or a case study from its header, to keep it here." />
      )}

      {rows.length > 0 && (
        <div className="bl-tablewrap">
          <table className="bl-table">
            <thead>
              <tr>
                <th>Token</th>
                <th>Address</th>
                <th>Kind</th>
                <th className="bl-th--r">Added (UTC)</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {rows.map((w) => {
                const known = findByContract(w.address);
                const n = names[w.address];
                return (
                  <tr key={w.address} className="bl-tr" onClick={() => open(w.address)}>
                    <td>
                      <span className="bl-tokencell__b">
                        <span className="bl-tokencell__n">{known?.project.name ?? n?.symbol ?? w.label ?? shortAddr(w.address, 6, 4)}</span>
                        <span className="bl-tokencell__t meta">{known ? `$${known.project.ticker}` : n?.name ?? w.label ?? ''}</span>
                      </span>
                    </td>
                    <td className="num meta">{shortAddr(w.address, 10, 6)}</td>
                    <td className="meta">{known ? 'case study' : 'live token'}</td>
                    <td className="bl-td--r num meta">{when(w.added_at)}</td>
                    <td className="bl-td--act">
                      <span className="bl-rowacts">
                        <button
                          className="bl-iconbtn"
                          title="Remove from watchlist"
                          onClick={(e) => {
                            e.stopPropagation();
                            removeWatch(w.address)
                              .then(() => setItems({ state: 'ok', value: rows.filter((r) => r.address !== w.address) }))
                              .catch(() => undefined);
                          }}
                        >
                          <Icon.Star size={14} filled />
                        </button>
                        <span className="bl-rowact">
                          Open <Icon.Arrow size={13} />
                        </span>
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
