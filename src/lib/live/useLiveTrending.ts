import { useEffect, useRef, useState } from 'react';
import {
  type HolderInfo,
  type LivePool,
  type Window,
  RateLimited,
  cachedHolders,
  clearHolderQueue,
  fetchHolders,
  fetchPatches,
  fetchTrending,
  lastRanking,
} from './trending';

const TRENDING_EVERY_MS = 60_000;
const TRENDING_RETRY_MS = 15_000;
const PRICES_EVERY_MS = 10_000;

export type LiveStatus = 'loading' | 'live' | 'limited' | 'error';

/** Live Base trending list. The ranking comes from GeckoTerminal once a
 *  minute; prices tick from DexScreener every ten seconds; holder counts
 *  (GoPlus) fill in behind, rank order first. Everything stops while the tab is
 *  hidden or `paused` is set. */
export function useLiveTrending(win: Window, pages: number, paused: boolean) {
  const [pools, setPools] = useState<LivePool[]>(() => lastRanking(win, pages)?.pools ?? []);
  const [holders, setHolders] = useState<Record<string, HolderInfo>>({});
  const [status, setStatus] = useState<LiveStatus>('loading');
  const [updatedAt, setUpdatedAt] = useState(() => lastRanking(win, pages)?.at ?? 0);
  const [error, setError] = useState('');
  const [visible, setVisible] = useState(!document.hidden);
  const poolsRef = useRef<LivePool[]>([]);
  poolsRef.current = pools;

  useEffect(() => {
    const on = () => setVisible(!document.hidden);
    document.addEventListener('visibilitychange', on);
    return () => document.removeEventListener('visibilitychange', on);
  }, []);

  const running = visible && !paused;

  /* ranking — refetched on window/page change and once a minute */
  const lastKey = useRef('');
  useEffect(() => {
    if (!running) return;
    let alive = true;
    const key = `${win}:${pages}`;
    if (key !== lastKey.current) {
      lastKey.current = key;
      setStatus('loading');
      /* show this browser's last ranking for the new key, if it has one */
      const cached = lastRanking(win, pages);
      if (cached) {
        setPools(cached.pools);
        setUpdatedAt(cached.at);
      }
    }

    let t: ReturnType<typeof setTimeout>;
    const load = async () => {
      let next = TRENDING_EVERY_MS;
      try {
        const fresh = await fetchTrending(win, pages);
        if (!alive) return;
        setPools(fresh);
        setStatus('live');
        setError('');
        setUpdatedAt(Date.now());
      } catch (e) {
        if (!alive) return;
        const limited = e instanceof RateLimited;
        setStatus(limited ? 'limited' : 'error');
        setError(e instanceof Error ? e.message : String(e));
        /* a failure retries sooner; a rate limit waits out the queue's backoff */
        next = limited ? TRENDING_EVERY_MS : TRENDING_RETRY_MS;
      }
      if (alive) t = setTimeout(load, next);
    };
    load();
    return () => {
      alive = false;
      clearTimeout(t);
    };
  }, [win, pages, running]);

  /* prices — DexScreener, every ten seconds */
  useEffect(() => {
    if (!running) return;
    let alive = true;
    const tick = async () => {
      const ids = poolsRef.current.map((p) => p.pool);
      if (!ids.length) return;
      try {
        const patches = await fetchPatches(ids);
        if (!alive || !patches.size) return;
        setPools((cur) =>
          cur.map((p) => {
            const d = patches.get(p.pool.toLowerCase());
            if (!d) return p;
            /* DexScreener has no maker counts; keep GeckoTerminal's */
            return { ...p, ...d, logo: p.logo ?? d.logo, price: d.price || p.price };
          })
        );
        setUpdatedAt(Date.now());
      } catch {
        /* a missed tick is fine — the next one will land */
      }
    };
    const t = setInterval(tick, PRICES_EVERY_MS);
    return () => {
      alive = false;
      clearInterval(t);
    };
  }, [running]);

  /* holders — queued behind the ranking, cached for 15 minutes */
  const tokenKey = pools.map((p) => p.token).join(',');
  useEffect(() => {
    if (!running || !tokenKey) return;
    let alive = true;
    const tokens = tokenKey.split(',');

    const hits: Record<string, HolderInfo> = {};
    for (const t of tokens) {
      const h = cachedHolders(t);
      if (h) hits[t] = h;
    }
    if (Object.keys(hits).length) setHolders((cur) => ({ ...cur, ...hits }));

    tokens.forEach((t, i) => {
      if (hits[t]) return;
      fetchHolders(t, i + 1)
        .then((h) => alive && setHolders((cur) => ({ ...cur, [t]: h })))
        .catch(() => {
          /* rate-limited or cancelled — retried on the next ranking */
        });
    });
    return () => {
      alive = false;
      clearHolderQueue();
    };
  }, [tokenKey, running]);

  return { pools, holders, status, error, updatedAt, running };
}
