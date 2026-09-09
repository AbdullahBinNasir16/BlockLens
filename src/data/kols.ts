import type { Kol, KolFocus, KolProfile } from './types';

/* ============================================================
   KOL directory.

   Every account BlockLens tracks, in one place. The handles and profile
   pictures are real; every number is a sample value — followers included.
   Nothing here is a measurement of these accounts, and the page says so.

   Project pages do not keep their own copy of a KOL's record. They list
   handles and read the numbers from here through `kolsFor`, so an account
   cannot show one win rate on a project and another in the directory.
   ============================================================ */

export const FOCUS_ORDER: KolFocus[] = ['AI', 'Memes', 'DeFi', 'Infra', 'Trading', 'Research', 'NFTs'];

export const KOLS: KolProfile[] = [
  { id: 'k-drshillbee', handle: 'DrShillBee', name: 'Dr Shill Bee', followers: 118_000, socialScore: 74, winRate: 71, avgOutcome: 96, thesisScore: 58, calls: 132, focus: ['Memes', 'AI'], chains: ['base', 'solana'] },
  { id: 'k-kyle', handle: 'kyle', name: 'Kyle', followers: 86_000, socialScore: 66, winRate: 64, avgOutcome: 58, thesisScore: 71, calls: 64, focus: ['AI', 'Infra'], chains: ['base', 'ethereum'] },
  { id: 'k-0xngmi', handle: '0xngmi', name: 'ngmi', followers: 61_000, socialScore: 58, winRate: 78, avgOutcome: 121, thesisScore: 88, calls: 38, focus: ['DeFi', 'Research'], chains: ['ethereum', 'base'] },
  { id: 'k-defiignas', handle: 'DefiIgnas', name: 'Ignas', followers: 164_000, socialScore: 77, winRate: 69, avgOutcome: 84, thesisScore: 92, calls: 71, focus: ['DeFi', 'Research', 'AI'], chains: ['ethereum', 'base', 'solana'] },
  { id: 'k-cobie', handle: 'Cobie', name: 'Cobie', followers: 812_000, socialScore: 91, winRate: 74, avgOutcome: 143, thesisScore: 81, calls: 24, focus: ['Trading', 'Research'], chains: ['ethereum'] },
  { id: 'k-theunipcs', handle: 'theunipcs', name: 'unipcs', followers: 47_000, socialScore: 49, winRate: 52, avgOutcome: 22, thesisScore: 34, calls: 158, focus: ['Memes'], chains: ['solana', 'base'] },
  { id: 'k-notthreadguy', handle: 'notthreadguy', name: 'threadguy', followers: 238_000, socialScore: 82, winRate: 58, avgOutcome: 41, thesisScore: 45, calls: 176, focus: ['Memes', 'Trading'], chains: ['solana', 'base'] },
  { id: 'k-danny_crypton', handle: 'Danny_Crypton', name: 'Danny', followers: 142_000, socialScore: 68, winRate: 61, avgOutcome: 66, thesisScore: 52, calls: 118, focus: ['Memes', 'AI'], chains: ['solana', 'base', 'bnb'] },
  { id: 'k-mrpunkdoteth', handle: 'mrpunkdoteth', name: 'mrpunk', followers: 74_000, socialScore: 55, winRate: 47, avgOutcome: -12, thesisScore: 39, calls: 142, focus: ['Memes', 'NFTs'], chains: ['ethereum', 'base'] },
  { id: 'k-inversebrah', handle: 'inversebrah', name: 'inversebrah', followers: 196_000, socialScore: 79, winRate: 55, avgOutcome: 34, thesisScore: 28, calls: 96, focus: ['Trading', 'Memes'], chains: ['ethereum', 'solana'] },
  { id: 'k-blknoiz06', handle: 'blknoiz06', name: 'Ansem', followers: 734_000, socialScore: 94, winRate: 76, avgOutcome: 158, thesisScore: 63, calls: 88, focus: ['Memes', 'Trading'], chains: ['solana', 'base'] },
  { id: 'k-hsakatrades', handle: 'HsakaTrades', name: 'Hsaka', followers: 468_000, socialScore: 86, winRate: 73, avgOutcome: 112, thesisScore: 57, calls: 61, focus: ['Trading'], chains: ['ethereum', 'solana'] },
  { id: 'k-cryptokaleo', handle: 'CryptoKaleo', name: 'Kaleo', followers: 671_000, socialScore: 83, winRate: 49, avgOutcome: -6, thesisScore: 31, calls: 204, focus: ['Trading', 'Memes'], chains: ['ethereum', 'bnb', 'solana'] },
  { id: 'k-gainzy222', handle: 'gainzy222', name: 'gainzy', followers: 181_000, socialScore: 71, winRate: 43, avgOutcome: -19, thesisScore: 22, calls: 231, focus: ['Memes'], chains: ['solana', 'base'] },
  { id: 'k-muststopmurad', handle: 'MustStopMurad', name: 'Murad', followers: 412_000, socialScore: 88, winRate: 68, avgOutcome: 134, thesisScore: 94, calls: 29, focus: ['Memes', 'Research'], chains: ['solana', 'ethereum'] },
  { id: 'k-pentosh1', handle: 'Pentosh1', name: 'Pentoshi', followers: 846_000, socialScore: 84, winRate: 66, avgOutcome: 72, thesisScore: 48, calls: 97, focus: ['Trading'], chains: ['ethereum', 'solana'] },
  { id: 'k-cryptocred', handle: 'CryptoCred', name: 'Cred', followers: 398_000, socialScore: 69, winRate: 63, avgOutcome: 44, thesisScore: 86, calls: 42, focus: ['Trading', 'Research'], chains: ['ethereum'] },
  { id: 'k-degenspartan', handle: 'DegenSpartan', name: 'Degen Spartan', followers: 254_000, socialScore: 73, winRate: 62, avgOutcome: 51, thesisScore: 66, calls: 57, focus: ['DeFi', 'Trading'], chains: ['ethereum', 'solana'] },
  { id: 'k-rektcapital', handle: 'rektcapital', name: 'Rekt Capital', followers: 521_000, socialScore: 76, winRate: 57, avgOutcome: 29, thesisScore: 61, calls: 188, focus: ['Trading'], chains: ['ethereum', 'bnb'] },
  { id: 'k-thedefiedge', handle: 'thedefiedge', name: 'The DeFi Edge', followers: 263_000, socialScore: 71, winRate: 65, avgOutcome: 47, thesisScore: 90, calls: 49, focus: ['DeFi', 'Research'], chains: ['ethereum', 'base'] },
  { id: 'k-milesdeutscher', handle: 'milesdeutscher', name: 'Miles Deutscher', followers: 548_000, socialScore: 85, winRate: 60, avgOutcome: 53, thesisScore: 79, calls: 112, focus: ['AI', 'Research', 'Trading'], chains: ['ethereum', 'solana', 'base'] },
  { id: 'k-route2fi', handle: 'Route2FI', name: 'Route 2 FI', followers: 247_000, socialScore: 70, winRate: 64, avgOutcome: 62, thesisScore: 83, calls: 74, focus: ['DeFi', 'AI'], chains: ['ethereum', 'base', 'solana'] },
  { id: 'k-aixbt_agent', handle: 'aixbt_agent', name: 'aixbt', followers: 492_000, socialScore: 89, winRate: 59, avgOutcome: 38, thesisScore: 72, calls: 318, focus: ['AI', 'Research'], chains: ['base', 'solana', 'ethereum'] },
  { id: 'k-cryptohayes', handle: 'CryptoHayes', name: 'Arthur Hayes', followers: 689_000, socialScore: 90, winRate: 67, avgOutcome: 88, thesisScore: 97, calls: 18, focus: ['Research', 'Trading'], chains: ['ethereum'] },
];

export const KOL_BY_HANDLE: Record<string, KolProfile> = Object.fromEntries(
  KOLS.map((k) => [k.handle.toLowerCase(), k])
);

/** A project's KOL list, read from the directory. Throws on an unknown
 *  handle — a typo should break the build, not render an empty card. */
export function kolsFor(handles: string[]): Kol[] {
  return handles.map((h) => {
    const k = KOL_BY_HANDLE[h.toLowerCase()];
    if (!k) throw new Error(`Unknown KOL handle: ${h}`);
    return { id: k.id, handle: k.handle, name: k.name, winRate: k.winRate, avgOutcome: k.avgOutcome };
  });
}

export const KOL_NOTE =
  'Handles and profile pictures are real. Every number on this page — followers included — ' +
  'is a sample value for the prototype, not a measurement of these accounts.';
