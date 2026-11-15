import { afterEach, describe, expect, it, vi } from 'vitest';
import { ApiError, apiGet, liveEnabled } from './api';
import { SAMPLE_TRENDING } from '../data/trending';
import { SAMPLE_CORPUS, liveCorpus } from './corpus';
import { holdingMinutes } from './screener';
import type { WalletProjectPosition } from '../data/types';

afterEach(() => {
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
});

describe('apiGet', () => {
  it('turns a dead network into a readable reason, not a crash', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')));
    await expect(apiGet('/api/x')).rejects.toThrow('the API is not reachable');
  });

  it('carries the status and the API detail on an HTTP error', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: 'screener corpus building' }), { status: 503 }))
    );
    const e = (await apiGet("/api/screener").catch((x: unknown) => x)) as ApiError;
    expect(e).toBeInstanceOf(ApiError);
    expect(e.status).toBe(503);
    expect(e.message).toBe('screener corpus building');
  });
});

describe('live flags', () => {
  it('a screen is live unless its flag is 0', () => {
    expect(liveEnabled('trending')).toBe(true);
    vi.stubEnv('VITE_LIVE_TRENDING', '0');
    expect(liveEnabled('trending')).toBe(false);
  });
});

describe('sample fallbacks are marked as sample', () => {
  it('the trending snapshot is sample and holds no holder counts', () => {
    expect(SAMPLE_TRENDING.provenance).toBe('sample');
    expect(SAMPLE_TRENDING.pools.every((p) => p.holders === null)).toBe(true);
  });

  it('the sample corpus is sample; a live corpus is live', () => {
    expect(SAMPLE_CORPUS.provenance).toBe('sample');
    const live = liveCorpus({
      provenance: 'live', asOf: '2026-11-03', unit: 'USD', contracts: [], wallets: [],
      tokens: [{ address: '0xab', symbol: '', name: '', launchedAt: Date.UTC(2026, 6, 16), wallets: 3 }],
    });
    expect(live.provenance).toBe('live');
    // the clock comes from the index, a day after the last launch
    expect(live.now).toBe(Date.UTC(2026, 6, 17));
  });
});

describe('open positions in a windowed record', () => {
  const p = (extra: Partial<WalletProjectPosition>): WalletProjectPosition => ({
    projectId: 'x', chain: 'base', firstBuy: 0, lastSell: null, buys: 1, sells: 0, invested: 1,
    soldFraction: 0, proceeds: 0, remainingValue: 1, entryDelay: 0, averagedDown: false,
    soldFirstPump: false, wentToZero: false, honeypot: false, ...extra,
  });
  const HOUR = 3_600_000;

  it('are held only until the record stops observing them', () => {
    expect(holdingMinutes(p({ observedUntil: 24 * HOUR }), 1000 * HOUR)).toBe(24 * 60);
  });

  it('without a window, are held to the corpus clock, as before', () => {
    expect(holdingMinutes(p({}), 10 * HOUR)).toBe(600);
  });
});
