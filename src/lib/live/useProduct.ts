import { useEffect, useState } from 'react';
import { PRODUCT_EVENT, fetchHistory, fetchWatchlist, type HistoryEntry, type WatchItem } from './product';

/** The watchlist and history, refreshed whenever a page changes them. */
export function useProductState() {
  const [watchlist, setWatchlist] = useState<WatchItem[]>([]);
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [available, setAvailable] = useState(false);

  useEffect(() => {
    let alive = true;
    const load = () =>
      Promise.all([fetchWatchlist(), fetchHistory(50)])
        .then(([w, h]) => {
          if (!alive) return;
          setWatchlist(w);
          setHistory(h);
          setAvailable(true);
        })
        .catch(() => alive && setAvailable(false));
    load();
    window.addEventListener(PRODUCT_EVENT, load);
    return () => {
      alive = false;
      window.removeEventListener(PRODUCT_EVENT, load);
    };
  }, []);

  return { watchlist, history, available };
}
