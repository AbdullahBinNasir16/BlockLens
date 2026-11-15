/* ============================================================
   The one way the front end reads the BlockLens API (Phase 7).

   - `VITE_API_URL` is the API's origin; empty means same origin (the dev
     server's /api proxy, or nginx in the container).
   - Each screen has a live flag, `VITE_LIVE_<SCREEN>`; "0" turns the
     screen to its sample data without touching the API.
   - The contract: a live answer renders live with no sample badge; a
     failure, a timeout or a switched-off flag renders the screen's sample
     literal from src/data with `provenance: 'sample'` and a visible badge.
     Never a blank screen, never sample data without the badge, and never
     live and sample mixed inside one section.
   ============================================================ */
import { useEffect, useRef, useState } from 'react';
import type { Provenance } from '../data/types';

export type Screen = 'trending' | 'project' | 'screener' | 'risk' | 'launches';

const ENV = import.meta.env as Record<string, string | undefined>;

export const API_URL = (ENV.VITE_API_URL ?? '').replace(/\/$/, '');
const TIMEOUT_MS = Number(ENV.VITE_API_TIMEOUT_MS ?? 8000);

export function liveEnabled(screen: Screen): boolean {
  return ENV[`VITE_LIVE_${screen.toUpperCase()}`] !== '0';
}

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number | null
  ) {
    super(message);
  }
}

export async function apiGet<T>(path: string, timeoutMs = TIMEOUT_MS): Promise<T> {
  const ctl = new AbortController();
  const t = setTimeout(() => ctl.abort(), timeoutMs);
  try {
    const r = await fetch(API_URL + path, { signal: ctl.signal, headers: { Accept: 'application/json' } });
    if (!r.ok) {
      let detail = '';
      try {
        detail = (await r.json())?.detail ?? '';
      } catch {
        /* not JSON */
      }
      throw new ApiError(detail || `API ${r.status}`, r.status);
    }
    return (await r.json()) as T;
  } catch (e) {
    if (e instanceof ApiError) throw e;
    const aborted = e instanceof DOMException && e.name === 'AbortError';
    throw new ApiError(aborted ? 'the API did not answer in time' : 'the API is not reachable', null);
  } finally {
    clearTimeout(t);
  }
}

export interface Live<T> {
  data: T;
  provenance: Provenance;
  /** why this is sample, when it is */
  reason: string;
  loading: boolean;
  updatedAt: number;
}

/** Fetch `path` (and again every `intervalMs`), falling back to `sample`.
 *  A later failure after a live answer keeps the live data but marks it
 *  stale in `reason`, rather than swapping sample numbers into a live
 *  section; only when nothing live has arrived does sample render. */
export function useLive<T>(
  screen: Screen,
  path: string | null,
  sample: T,
  intervalMs = 0
): Live<T> {
  const enabled = liveEnabled(screen) && path != null;
  const [state, setState] = useState<Live<T>>(() => ({
    data: sample,
    provenance: 'sample',
    reason: enabled ? 'loading live data' : 'live data is switched off for this screen',
    loading: enabled,
    updatedAt: 0,
  }));
  const sampleRef = useRef(sample);
  sampleRef.current = sample;

  useEffect(() => {
    if (!enabled) {
      setState({
        data: sampleRef.current,
        provenance: 'sample',
        reason: 'live data is switched off for this screen',
        loading: false,
        updatedAt: 0,
      });
      return;
    }
    let alive = true;
    let timer: ReturnType<typeof setTimeout>;
    setState((s) => ({ ...s, data: sampleRef.current, provenance: 'sample', loading: true, reason: 'loading live data' }));
    const load = async () => {
      try {
        const d = await apiGet<T>(path!);
        if (alive) setState({ data: d, provenance: 'live', reason: '', loading: false, updatedAt: Date.now() });
      } catch (e) {
        if (!alive) return;
        const why = e instanceof Error ? e.message : String(e);
        setState((s) =>
          s.provenance === 'live'
            ? { ...s, loading: false, reason: `last refresh failed: ${why}` }
            : { data: sampleRef.current, provenance: 'sample', reason: why, loading: false, updatedAt: 0 }
        );
      }
      if (alive && intervalMs > 0) timer = setTimeout(load, intervalMs);
    };
    load();
    return () => {
      alive = false;
      clearTimeout(timer);
    };
  }, [enabled, path, intervalMs]);

  return state;
}
