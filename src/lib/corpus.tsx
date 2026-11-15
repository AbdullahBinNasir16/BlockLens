import { createContext, useContext } from 'react';
import type { ScreenerResponse } from '../data/api';
import type { Chain, Provenance, WalletRecord } from '../data/types';
import { datasets } from '../data/projects';
import { CORPUS_NOTE, CORPUS_NOW, WALLET_CORPUS } from '../data/wallets';

/* ============================================================
   What the wallet screener searches (Phase 7).

   The query logic in `screener.ts` derives every figure from positions,
   and was meant to be backend-agnostic. It was not quite: it resolved
   contracts through the sample project registry and measured time from
   the sample corpus's fixed clock. A corpus is therefore three things the
   logic is handed, not imports it reaches for: the wallets, a registry of
   the tokens they traded, and the corpus's own clock. The sample corpus is
   the default, so the logic is unchanged for it.
   ============================================================ */

export interface CorpusToken {
  /** the positions' `projectId` */
  id: string;
  contract: string;
  chain: Chain;
  ticker: string;
  name: string;
  logo?: string;
  monogram: string;
  /** wallets with a position in it, where known */
  wallets?: number;
}

export interface Corpus {
  provenance: Provenance;
  /** the corpus clock: windows and open positions are measured from it */
  now: number;
  registry: Record<string, CorpusToken>;
  wallets: WalletRecord[];
  /** what this corpus is, in a sentence, for the badge and the footer */
  note: string;
  /** filters this corpus has no data for, with the reason: shown disabled,
   *  never silently matching nothing or everything */
  unsupported: Record<string, string>;
}

/* The live store resolves positions, not identities: these wallet fields
   are placeholders there, so their filters would look like findings. */
const LIVE_UNSUPPORTED: Record<string, string> = {
  fundingSource: 'funding origins are not resolved for these wallets',
  clusterSize: 'funding clusters are not computed for these wallets',
  smartMoney: 'no defended definition of smart money exists',
  hasLabel: 'these wallets carry no identity labels',
  honeypotInteractions: 'honeypot status is not recorded for past launches',
  walletAgeAtFirstBuy: "wallets' first-seen dates are mostly not resolved",
  firstSeen: "wallets' first-seen dates are mostly not resolved",
};

export const SAMPLE_CORPUS: Corpus = {
  provenance: 'sample',
  now: CORPUS_NOW,
  registry: Object.fromEntries(
    Object.values(datasets).map(({ project: p }) => [
      p.id,
      { id: p.id, contract: p.contract.toLowerCase(), chain: p.chain, ticker: p.ticker, name: p.name,
        logo: p.logo, monogram: p.monogram },
    ])
  ),
  wallets: WALLET_CORPUS,
  note: CORPUS_NOTE,
  unsupported: {},
};

const DAY = 86_400_000;

export function liveCorpus(r: ScreenerResponse): Corpus {
  /* The clock comes from the token index, never from whichever wallets
     happen to be loaded: positions span each launch's first 24 hours, so
     the corpus ends a day after its last launch. */
  let now = 0;
  for (const t of r.tokens) now = Math.max(now, t.launchedAt + DAY);
  const registry: Record<string, CorpusToken> = {};
  for (const t of r.tokens) {
    const tick = t.symbol || `${t.address.slice(2, 6)}…`;
    registry[t.address] = {
      id: t.address,
      contract: t.address,
      chain: 'base',
      ticker: tick,
      name: t.name || t.address,
      monogram: (t.symbol || t.address.slice(2, 4)).slice(0, 2).toUpperCase(),
      wallets: t.wallets,
    };
  }
  return {
    provenance: 'live',
    now,
    registry,
    wallets: r.wallets,
    note:
      `Real wallets from ${r.tokens.length} labelled Base launches ` +
      `(Jan–Jul 2026), rebuilt from stored transfers and swaps over each launch's first 24 hours. ` +
      `Money is converted at each trade's own day's ETH close.`,
    unsupported: LIVE_UNSUPPORTED,
  };
}

export function findInCorpus(corpus: Corpus, contract: string): CorpusToken | undefined {
  const c = contract.trim().toLowerCase();
  return Object.values(corpus.registry).find((t) => t.contract === c);
}

const Ctx = createContext<Corpus>(SAMPLE_CORPUS);
export const CorpusProvider = Ctx.Provider;

export function useCorpus(): Corpus {
  return useContext(Ctx);
}
