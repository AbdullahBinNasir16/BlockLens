import type { ProjectDataset } from '../types';
import { nockchain } from './nockchain';
import { sibyl } from './sibyl';
import { dot } from './dot';

/* ============================================================
   Project registry.

   One entry per investigated project. A backend would replace this
   with a lookup by contract address; every screen already reads
   through `getDataset`, so nothing else has to change.
   ============================================================ */

export const datasets: Record<string, ProjectDataset> = {
  nockchain,
  sibyl,
  dot,
};

export const projectIds = Object.keys(datasets);

export const DEFAULT_PROJECT = 'nockchain';

export function getDataset(id: string | undefined): ProjectDataset {
  return (id && datasets[id]) || datasets[DEFAULT_PROJECT];
}

/** Resolve a pasted contract address to a known project, if we hold one. */
export function findByContract(address: string): ProjectDataset | undefined {
  const a = address.trim().toLowerCase();
  return Object.values(datasets).find((d) => d.project.contract.toLowerCase() === a);
}

/* ---------------- chain identity ---------------- */

export const chainMeta: Record<
  string,
  { label: string; short: string; logo: string; explorer: string }
> = {
  ethereum: {
    label: 'Ethereum',
    short: 'ETH',
    logo: '/chains/ethereum.png',
    explorer: 'etherscan.io',
  },
  base: { label: 'Base', short: 'BASE', logo: '/chains/base.png', explorer: 'basescan.org' },
  solana: { label: 'Solana', short: 'SOL', logo: '/chains/solana.png', explorer: 'solscan.io' },
  bnb: { label: 'BNB Chain', short: 'BNB', logo: '/chains/bnb.png', explorer: 'bscscan.com' },
};

export const CHAINS = ['ethereum', 'base', 'solana', 'bnb'] as const;
