import { useEffect, useRef, useState } from 'react';
import type { TrendingResponse } from '../../data/api';
import type { Provenance } from '../../data/types';
import { SAMPLE_TRENDING } from '../../data/trending';
import { liveEnabled } from '../api';
import { type HolderInfo, type LivePool, type Window, fetchTrending, holderInfo } from './trending';

const EVERY_MS = 10_000;

export type LiveStatus = 'loading' | 'live' | 'limited' | 'error';

export interface TrendingState {
  pools: LivePool[];
  holders: Record<string, HolderInfo>;
  status: LiveStatus;
  error: string;
  updatedAt: number;
  running: boolean;
  provenance: Provenance;
  /** why the list is sample, or why a live list is stale */
  reason: string;
}

function split(r: TrendingResponse) {
  const holders: Record<string, HolderInfo> = {};
  for (const p of r.pools) {
    const h = holderInfo(p.holders);
    if (h) holders[p.token] = h;
  }
  return { pools: r.pools, holders };
}

/** Live Base trending from `/api/trending`, polled every ten seconds; the
 *  API's shared cache decides how often the sources are actually asked.
 *  Until a live list arrives, or when the API is down, the frozen sample
 *  ranking is shown with `provenance: 'sample'`; a live list that later
 *  fails to refresh stays on screen, marked stale, rather than being
 *  swapped for sample numbers. Stops while the tab is hidden or paused. */
export function useLiveTrending(win: Window, pages: number, paused: boolean): TrendingState {
  const enabled = liveEnabled('trending');
  const [state, setState] = useState<TrendingState>(() => ({
    ...split(SAMPLE_TRENDING),
    status: enabled ? 'loading' : 'error',
    error: '',
    updatedAt: 0,
    running: false,
    provenance: 'sample',
    reason: enabled ? 'loading live data' : 'live data is switched off for this screen',
  }));
  const [visible, setVisible] = useState(!document.hidden);
  const live = useRef(false);

  useEffect(() => {
    const on = () => setVisible(!document.hidden);
    document.addEventListener('visibilitychange', on);
    return () => document.removeEventListener('visibilitychange', on);
  }, []);

  const running = enabled && visible && !paused;

  /* a new window or page count is a new list: back to loading */
  useEffect(() => {
    live.current = false;
    setState((s) => ({ ...s, status: enabled ? 'loading' : 'error' }));
  }, [win, pages, enabled]);

  useEffect(() => {
    if (!running) {
      setState((s) => ({ ...s, running: false }));
      return;
    }
    let alive = true;
    let t: ReturnType<typeof setTimeout>;
    const load = async () => {
      try {
        const r = await fetchTrending(win, pages);
        if (!alive) return;
        live.current = true;
        setState({
          ...split(r),
          status: r.stale ? 'limited' : 'live',
          error: '',
          updatedAt: Date.parse(r.asOf) || Date.now(),
          running: true,
          provenance: 'live',
          reason: r.stale ? 'GeckoTerminal is throttling; showing the last good ranking' : '',
        });
      } catch (e) {
        if (!alive) return;
        const why = e instanceof Error ? e.message : String(e);
        setState((s) =>
          live.current
            ? { ...s, status: 'error', error: why, reason: `last refresh failed: ${why}` }
            : {
                ...split(SAMPLE_TRENDING),
                status: 'error',
                error: why,
                updatedAt: 0,
                running: true,
                provenance: 'sample',
                reason: why,
              }
        );
      }
      if (alive) t = setTimeout(load, EVERY_MS);
    };
    load();
    return () => {
      alive = false;
      clearTimeout(t);
    };
  }, [win, pages, running]);

  return { ...state, running };
}
