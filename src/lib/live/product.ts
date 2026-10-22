/* Product state and push, from the BlockLens API (backend/blocklens/api).
   Single-user by design at this stage: no accounts, one watchlist. */

import type { Launch } from './launches';

export interface WatchItem {
  address: string;
  chain: string;
  label: string | null;
  note: string | null;
  added_at: string;
}

export type Outcome = 'profile' | 'tracked' | 'live';

export interface HistoryEntry {
  id: number;
  address: string;
  chain: string;
  outcome: Outcome;
  opened_at: string;
}

export const OUTCOME_LABEL: Record<Outcome, string> = {
  profile: 'case study',
  tracked: 'scored launch',
  live: 'live data',
};

const JSON_HEADERS = { 'content-type': 'application/json' };

async function j<T>(p: Promise<Response>): Promise<T> {
  const r = await p;
  if (!r.ok) throw new Error(`API ${r.status}`);
  return r.json();
}

/** Pages that change product state announce it, so the sidebar's counts
 *  follow without a refresh. */
export const PRODUCT_EVENT = 'bl:product';
const announce = () => window.dispatchEvent(new Event(PRODUCT_EVENT));

export const fetchWatchlist = () =>
  j<{ items: WatchItem[] }>(fetch('/api/watchlist')).then((d) => d.items);

export async function addWatch(address: string, label?: string): Promise<void> {
  await j(fetch('/api/watchlist', { method: 'POST', headers: JSON_HEADERS, body: JSON.stringify({ address, label }) }));
  announce();
}

export async function removeWatch(address: string): Promise<void> {
  await j(fetch(`/api/watchlist/${address.toLowerCase()}`, { method: 'DELETE' }));
  announce();
}

export const fetchHistory = (limit = 100) =>
  j<{ items: HistoryEntry[] }>(fetch(`/api/history?limit=${limit}`)).then((d) => d.items);

/** Fire and forget: a failed history write must never break a page. */
export function recordInvestigation(address: string, outcome: Outcome): void {
  fetch('/api/history', { method: 'POST', headers: JSON_HEADERS, body: JSON.stringify({ address, outcome }) })
    .then((r) => r.ok && announce())
    .catch(() => undefined);
}

/** Server-sent events from /api/stream. Returns the function that closes it. */
export function openScoredStream(
  onScored: (l: Launch) => void,
  onState?: (connected: boolean) => void
): () => void {
  if (typeof EventSource === 'undefined') return () => undefined;
  const es = new EventSource('/api/stream');
  es.addEventListener('scored', (e) => {
    try {
      onScored(JSON.parse((e as MessageEvent).data) as Launch);
    } catch {
      /* a malformed event is dropped, not fatal */
    }
  });
  es.onopen = () => onState?.(true);
  es.onerror = () => onState?.(false);
  return () => es.close();
}
