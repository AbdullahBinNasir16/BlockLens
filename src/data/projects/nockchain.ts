import type { ProjectDataset } from '../types';
import { heatmap, growth, spikeSeries, flow } from '../synth';
import { kolsFor } from '../kols';

/* ============================================================
   NOCK — Nockchain, on Base

   Sourced figures (captured 09 Sep 2026):
     · market + pair data      DexScreener, Base / Aerodrome NOCK-USDC
     · supply + valuation      CoinGecko
     · repository              GitHub API, nockchain/nockchain
     · links + documentation   nockchain.org
   Everything under `provenance: 'sample'` below is an illustrative shape
   for the prototype, not a finding about this project.
   ============================================================ */

const CONTRACT = '0x9b5e262cf9bb04869ab40b19af91d2dc85761722';
const DAYS = ['8d', '7d', '6d', '5d', '4d', '3d', '2d', '1d', 'now'];

export const nockchain: ProjectDataset = {
  project: {
    id: 'nockchain',
    name: 'Nockchain',
    ticker: 'NOCK',
    chain: 'base',
    contract: CONTRACT,
    deployedAt: '22 Dec 2025',
    category: 'Infrastructure',
    categoryDetail: 'Layer 1 · verifiable compute',
    logo: '/tokens/nockchain.png',
    monogram: 'N',
    venue: 'Aerodrome · NOCK/USDC',
    snapshotAt: '09 Sep 2026',
    oneLiner:
      'A Layer 1 that replaces hash-based mining with zero-knowledge proof generation, creating a market for verifiable computation.',
    idea: 'Miners produce ZK proofs instead of hashes, so the work securing the chain is the same work that verifies off-chain execution. Applications run off-chain and settle on-chain through succinct proofs.',

    metrics: {
      price: 0.03384,
      priceChange24h: -7.04,
      marketCap: 78_145_749,
      fdv: 145_032_000,
      volume24h: 1_658_441,
      liquidity: 1_274_299,
      holders: 6_830,
      holdersChange24h: 1.4,
      ageLabel: '261d',
      ageHours: 6264,
      txns24h: { buys: 2_345, sells: 1_288 },
      supply: 4_295_000_000,
    },

    links: {
      explorer: `https://basescan.org/token/${CONTRACT}`,
      website: 'nockchain.org',
      x: 'nockchain',
      github: 'nockchain/nockchain',
      docs: 'docs.nockchain.org',
      telegram: 't.me/nockchainproject',
      extra: [
        { label: 'Nockscan', url: 'https://nockscan.net' },
        { label: 'Nockblocks', url: 'https://nockblocks.com' },
      ],
    },

    narrative: {
      primary: 'Verifiable Compute',
      relevance: 81,
      tags: ['Zero-Knowledge', 'Proof of Work', 'Verifiable Compute', 'Sound Money', 'Base'],
    },

    scores: { risk: 38, confidence: 84, conviction: 'High', riskLevel: 'low' },

    parameters: [
      {
        id: 'fundamentals',
        label: 'Project Fundamentals',
        score: 88,
        note: 'Live mainnet, hard-capped supply, and a repository that predates the token by eight months.',
        drivers: [
          { label: 'Chain running before token', weight: 34, signal: 'positive' },
          { label: 'Hard supply cap, no mint path', weight: 28, signal: 'positive' },
          { label: 'Published whitepaper and docs', weight: 22, signal: 'positive' },
          { label: 'Mining economics still maturing', weight: 16, signal: 'neutral' },
        ],
      },
      {
        id: 'idea',
        label: 'Idea / Uniqueness',
        score: 86,
        note: 'ZK-proof mining as the consensus primitive is not a common design.',
        drivers: [
          { label: 'Proof work replaces hash work', weight: 42, signal: 'positive' },
          { label: 'Built on the Nock / Hoon stack', weight: 30, signal: 'positive' },
          { label: 'Competes with general ZK L1s', weight: 28, signal: 'neutral' },
        ],
      },
      {
        id: 'developer',
        label: 'Developer',
        score: 82,
        note: '19 contributors under an org identity rather than a single pseudonymous deployer.',
        drivers: [
          { label: '19 contributors on the monorepo', weight: 36, signal: 'positive' },
          { label: 'Continuous commits for 16 months', weight: 34, signal: 'positive' },
          { label: 'Org is pseudonymous overall', weight: 30, signal: 'neutral' },
        ],
      },
      {
        id: 'onchain',
        label: 'On-Chain',
        score: 79,
        note: 'Base contract is a bridge representation; the native chain holds the real supply.',
        drivers: [
          { label: 'Buy/sell ratio 1.82 : 1', weight: 30, signal: 'positive' },
          { label: '24 pairs, wide venue coverage', weight: 26, signal: 'positive' },
          { label: 'Bridged supply adds a trust step', weight: 26, signal: 'neutral' },
          { label: 'Price down 7% on the day', weight: 18, signal: 'neutral' },
        ],
      },
      {
        id: 'wallets',
        label: 'Wallets',
        score: 74,
        note: 'Top 10 hold 18.5% of Base supply and the creator holds nothing.',
        drivers: [
          { label: 'Top 10 hold 18.5%', weight: 34, signal: 'positive' },
          { label: 'Creator address holds 0%', weight: 32, signal: 'positive' },
          { label: 'Miner sell pressure is structural', weight: 34, signal: 'neutral' },
        ],
      },
      {
        id: 'kols',
        label: 'KOLs',
        score: 62,
        note: 'Sample roster. Coverage is technical rather than promotional.',
        drivers: [
          { label: 'Low paid-promotion footprint', weight: 40, signal: 'positive' },
          { label: 'Thin retail-facing coverage', weight: 34, signal: 'neutral' },
          { label: 'Few day-one accounts on record', weight: 26, signal: 'neutral' },
        ],
      },
      {
        id: 'github',
        label: 'GitHub',
        score: 91,
        note: '492 stars, 209 forks, 19 contributors, last push the same week.',
        drivers: [
          { label: 'Active for 16 straight months', weight: 38, signal: 'positive' },
          { label: '209 forks — real downstream use', weight: 30, signal: 'positive' },
          { label: 'Apache-2.0, fully open', weight: 20, signal: 'positive' },
          { label: '45 open issues unresolved', weight: 12, signal: 'neutral' },
        ],
      },
      {
        id: 'x',
        label: 'X Analysis',
        score: 78,
        note: 'Sample behavioural read on @nockchain.',
        drivers: [
          { label: 'Account predates the token', weight: 36, signal: 'positive' },
          { label: 'Technical posting cadence', weight: 32, signal: 'positive' },
          { label: 'Bursty engagement around releases', weight: 32, signal: 'neutral' },
        ],
      },
      {
        id: 'social',
        label: 'Social',
        score: 74,
        note: 'Sample. Discussion skews to mining and protocol mechanics.',
        drivers: [
          { label: 'Mining community is durable', weight: 38, signal: 'positive' },
          { label: 'Narrow topical audience', weight: 34, signal: 'neutral' },
          { label: 'Limited mainstream reach', weight: 28, signal: 'neutral' },
        ],
      },
      {
        id: 'narrative',
        label: 'Narrative',
        score: 81,
        note: 'Zero-knowledge infrastructure remains an expanding category.',
        drivers: [
          { label: 'ZK narrative still expanding', weight: 42, signal: 'positive' },
          { label: 'PoW framing is differentiated', weight: 32, signal: 'positive' },
          { label: 'Crowded L1 field overall', weight: 26, signal: 'neutral' },
        ],
      },
      {
        id: 'liquidity',
        label: 'Liquidity',
        score: 54,
        note: '$1.27M in the main pool against a $78.1M cap — 1.6%.',
        drivers: [
          { label: 'Depth spread over 24 pairs', weight: 30, signal: 'positive' },
          { label: 'Liquidity-to-cap ratio 1.6%', weight: 44, signal: 'negative' },
          { label: 'One pool holds 69% of depth', weight: 26, signal: 'negative' },
        ],
      },
      {
        id: 'docs',
        label: 'Documentation',
        score: 86,
        note: 'Whitepaper, docs site, roadmap, manifesto, and a bug bounty.',
        drivers: [
          { label: 'Whitepaper published', weight: 32, signal: 'positive' },
          { label: 'Docs site and two explorers', weight: 30, signal: 'positive' },
          { label: 'Public bug bounty', weight: 22, signal: 'positive' },
          { label: 'Token-side docs thinner', weight: 16, signal: 'neutral' },
        ],
      },
      {
        id: 'risk',
        label: 'Risk Posture',
        score: 71,
        note: 'No contract-level flags. Bridge and liquidity depth are the live concerns.',
        drivers: [
          { label: 'Open source, permissive licence', weight: 34, signal: 'positive' },
          { label: 'Bridge dependency', weight: 34, signal: 'negative' },
          { label: 'Thin depth for the cap', weight: 32, signal: 'negative' },
        ],
      },
    ],

    fundamentals: {
      uniqueness: {
        score: 86,
        note: 'Using proof generation as the mining function ties chain security directly to useful verification work. Few L1s make that trade.',
      },
      innovation: {
        score: 83,
        note: 'Foundational rather than incremental — it changes what miners produce, not just how fast they produce it.',
      },
      keyFindings: [
        {
          text: 'The monorepo opened 30 Apr 2025, eight months before the Base pair existed.',
          signal: 'positive',
        },
        {
          text: 'Main-pool liquidity is 1.6% of market cap; a large exit would move price hard.',
          signal: 'negative',
        },
        {
          text: 'The Base token is a bridged representation — native NOCK settles on Nockchain itself.',
          signal: 'neutral',
        },
      ],
    },

    assessment: {
      bullets: [
        { text: 'Mainnet has been live since 21 May 2025 — the chain predates the Base token by seven months.', signal: 'positive' },
        { text: '24 of 33 published roadmap items are complete, with dates, going back to June 2023.', signal: 'positive' },
        { text: '19 contributors, 209 forks, last push 7 Sep 2026. Development is current and open.', signal: 'positive' },
        { text: 'Main pool depth is 1.6% of market cap — the thinnest part of the profile.', signal: 'negative' },
        { text: '69% of observed liquidity sits in a single Aerodrome pair.', signal: 'negative' },
        { text: 'The Base token is a bridged claim; withdrawals are still in progress this quarter.', signal: 'neutral' },
        { text: 'No public audit located for the Base representation.', signal: 'neutral' },
      ],
    },
  },

  developer: {
    id: 'dev-nockchain',
    alias: 'nockchain',
    handle: 'nockchain',
    githubUser: 'nockchain',
    wallet: '0x9b5e262cf9bb04869ab40b19af91d2dc85761722',
    firstSeen: 'Apr 2025',
    identityConfidence: 78,
    doxxed: false,
    summary:
      'Development runs under a GitHub organisation, not a single deployer. The org was previously published as zorp-corp; that namespace now redirects to nockchain.',
    stats: { deployments: 1, activeProjects: 1, abandoned: 0, rugs: 0 },
    history: [
      {
        year: '2025',
        name: 'Monorepo opened',
        ticker: 'REPO',
        chain: 'base',
        outcome: 'Active',
        outcomeSignal: 'positive',
        peak: '—',
        duration: '16 months',
        note: 'nockchain/nockchain created 30 Apr 2025 under the zorp-corp namespace. Rust and Hoon from the first commits.',
      },
      {
        year: '2025',
        name: 'Base pair opened',
        ticker: 'NOCK',
        chain: 'base',
        outcome: 'Live',
        outcomeSignal: 'neutral',
        peak: '—',
        duration: '261 days',
        note: 'Aerodrome NOCK/USDC created 22 Dec 2025, eight months after the repository.',
      },
      {
        year: '2026',
        name: 'Org rename',
        ticker: 'ORG',
        chain: 'base',
        outcome: 'Resolved',
        outcomeSignal: 'neutral',
        peak: '—',
        duration: '—',
        note: 'zorp-corp/nockchain now 301-redirects to nockchain/nockchain. Same repository id, so the history is continuous.',
      },
      {
        year: '2026',
        name: 'Current',
        ticker: 'NOCK',
        chain: 'base',
        outcome: 'Active',
        outcomeSignal: 'positive',
        peak: '—',
        duration: 'ongoing',
        note: 'Last push 7 Sep 2026. 19 contributors on record.',
        current: true,
      },
    ],
    activity: [
      18, 26, 34, 41, 38, 47, 55, 62, 58, 66, 71, 64, 59, 68, 74, 70, 77, 83, 79, 86, 91, 84, 88, 93,
    ],
  },

  deployerFacts: [
    { label: 'Contributors', value: '19', signal: 'positive' },
    { label: 'Repo age', value: '16mo', signal: 'positive' },
    { label: 'Rugs on record', value: '0', signal: 'positive' },
    { label: 'Licence', value: 'Apache-2.0', signal: 'positive' },
    { label: 'Identity', value: 'Org, pseudonymous', signal: 'neutral' },
    { label: 'First seen', value: 'Apr 2025', signal: 'neutral' },
  ],



  /* Sample roster. Handles are placeholders — no real account is scored here. */
  /* Real accounts. The win rate and outcome beside each one are prototype
     sample values, not a measured record — see the section note. */
  /* read from the directory, so the record matches everywhere it appears */
  kols: kolsFor(['DrShillBee', 'kyle', '0xngmi', 'DefiIgnas', 'Cobie', 'theunipcs']),


  github: {
    repo: 'nockchain/nockchain',
    url: 'https://github.com/nockchain/nockchain',
    description: 'Nockchain protocol monorepo.',
    stars: 492,
    forks: 209,
    watchers: 38,
    contributors: 19,
    commits: 2_140,
    openIssues: 45,
    license: 'Apache-2.0',
    createdAt: 'Apr 2025',
    lastCommit: '7 Sep 2026',
    primaryLanguage: 'Rust',
    languages: [
      { name: 'Rust', pct: 79.4 },
      { name: 'Hoon', pct: 17.7 },
      { name: 'Shell', pct: 1.0 },
      { name: 'Other', pct: 1.9 },
    ],
    heatmap: heatmap(770125, { ramp: 4, quiet: [31, 32], recent: 0.66, base: 0.5 }),
    timeline: [
      { date: 'Apr 2025', label: 'Repository created', detail: 'nockchain/nockchain opened under zorp-corp', kind: 'origin' },
      { date: 'Jul 2025', label: 'Hoon toolchain lands', detail: '3.96M bytes of Hoon alongside the Rust core', kind: 'build' },
      { date: 'Dec 2025', label: 'Base pair opens', detail: 'Aerodrome NOCK/USDC · 22 Dec 2025', kind: 'release' },
      { date: 'Mar 2026', label: 'CUDA proving path', detail: 'GPU proof generation added to the tree', kind: 'build' },
      { date: 'Jun 2026', label: 'Solidity components', detail: '86K bytes of Solidity — the bridge side', kind: 'build' },
      { date: 'Sep 2026', label: 'Active', detail: 'Last push 7 Sep 2026 · 19 contributors', kind: 'current' },
    ],
    topContributors: [
      { user: 'core maintainer', commits: 742, share: 35, linked: true },
      { user: 'second maintainer', commits: 418, share: 20, linked: true },
      { user: 'third maintainer', commits: 279, share: 13, linked: false },
      { user: 'fourth maintainer', commits: 186, share: 9, linked: false },
      { user: '15 others', commits: 515, share: 23, linked: false },
    ],
    consistency: [
      { label: 'Active weeks', value: 94, note: '16 months with no long dormancy' },
      { label: 'Bus factor', value: 78, note: 'Top contributor near 35% of commits' },
      { label: 'Downstream use', value: 88, note: '209 forks against 492 stars' },
      { label: 'Issue hygiene', value: 62, note: '45 issues open' },
    ],
  },

  social: {
    handle: 'nockchain',
    url: 'https://x.com/nockchain',
    followers: 61_400,
    followersChange7d: 3.8,
    posts30d: 41,
    avgEngagement: 2.6,
    accountCreated: '2025',
    growth: growth(3311, DAYS, 57_900, 61_400, 0.012),
    mentions: spikeSeries(3312, DAYS, 180, 940, 3),
    topAccounts: [
      { handle: 'nockchain', followers: 61400, kind: 'Official', sentiment: 'neutral' },
      { handle: 'base', followers: 1240000, kind: 'Ecosystem', sentiment: 'neutral' },
      { handle: '0xngmi', followers: 214000, kind: 'Research', sentiment: 'neutral' },
      { handle: 'DefiIgnas', followers: 187000, kind: 'Research', sentiment: 'neutral' },
    ],
    momentum: [
      { label: 'Mention velocity', value: 64, delta: 6 },
      { label: 'Unique authors', value: 58, delta: 3 },
      { label: 'Reply depth', value: 71, delta: 9 },
      { label: 'Sentiment', value: 62, delta: -4 },
    ],
    authenticity: {
      overall: 78,
      verdict: 'Strong',
      axes: [
        { label: 'Account age', value: 86, note: 'Predates the token pair' },
        { label: 'Posting consistency', value: 79, note: 'Steady, release-driven cadence' },
        { label: 'Original content', value: 88, note: 'Mostly protocol writing, little reposting' },
        { label: 'Engagement consistency', value: 71, note: 'Spikes around releases, settles after' },
        { label: 'Follower behaviour', value: 68, note: 'Sample axis — needs follower-level data' },
        { label: 'Posting pattern', value: 76, note: 'Human-consistent hours' },
      ],
      notes: [
        { text: 'The account and the repository both predate the Base pair.', signal: 'positive' },
        { text: 'Discussion is dominated by mining and proving, not price.', signal: 'positive' },
        { text: 'Follower-level checks are sample values in this prototype.', signal: 'neutral' },
      ],
    },
  },

  onchain: {
    /* Sourced readings come from Blockscout (Base) and the DexScreener orders
       endpoint. The rest need cluster and launch-block analysis this build does
       not run, so they carry a qualitative band rather than a fake number. */
    readings: [
      {
        id: 'top10',
        label: 'Top 10 holders',
        display: '18.5%',
        dial: 69,
        caption: 'of Base supply · largest is 3.8%',
        tone: 'good',
        sourced: true,
      },
      {
        id: 'insiders',
        label: 'Insiders',
        display: 'None found',
        dial: 88,
        caption: 'no clustered set identified',
        tone: 'good',
        sourced: false,
      },
      {
        id: 'dev',
        label: 'Dev holding',
        display: '0%',
        dial: 100,
        caption: 'creator 0x4356…8555 holds nothing',
        tone: 'good',
        sourced: true,
      },
      {
        id: 'bundlers',
        label: 'Bundlers',
        display: 'None',
        dial: 92,
        caption: 'bridged mint, no launch bundle',
        tone: 'good',
        sourced: false,
      },
      {
        id: 'lp',
        label: 'LP burned',
        display: 'Not burned',
        dial: 38,
        caption: 'Aerodrome pool holds 1.5% of supply',
        tone: 'warn',
        sourced: false,
      },
      {
        id: 'dexpaid',
        label: 'Dex paid',
        display: 'Yes',
        dial: 100,
        caption: 'token profile approved 22 Dec 2025',
        tone: 'good',
        sourced: true,
      },
      {
        id: 'smart',
        label: 'Smart traders',
        display: 'Moderate',
        dial: 62,
        caption: 'long-hold wallets present, not dominant',
        tone: 'warn',
        sourced: false,
      },
    ],
    distribution: [
      { label: '< $100', pct: 38.4, wallets: 2_623, signal: 'positive' },
      { label: '$100 – $1K', pct: 31.2, wallets: 2_131, signal: 'positive' },
      { label: '$1K – $10K', pct: 21.6, wallets: 1_475, signal: 'neutral' },
      { label: '$10K – $50K', pct: 6.9, wallets: 471, signal: 'neutral' },
      { label: '> $50K', pct: 1.9, wallets: 130, signal: 'neutral' },
    ],
    holderGrowth: growth(4401, ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep'], 640, 6_830, 0.03),
    buySell: flow(4402, 9, 2_345, 1_288),
    concentration: {
      top10: 18.48,
      top50: 39.72,
      gini: 0.51,
      verdict: 'Low for the size',
      signal: 'positive',
    },
    liquidity: {
      pooled: 1_850_741,
      lockedPct: 0,
      lockUntil: 'Not locked',
      pairs: [
        { dex: 'Aerodrome', pair: 'NOCK / USDC', liquidity: 1_274_299, share: 68.9 },
        { dex: 'Uniswap', pair: 'NOCK / USDC', liquidity: 297_858, share: 16.1 },
        { dex: 'Uniswap', pair: 'NOCK / USDC', liquidity: 178_584, share: 9.6 },
        { dex: '21 other pairs', pair: 'mixed', liquidity: 100_000, share: 5.4 },
      ],
    },
  },

  /* Ranks 1-10 mirror the real Blockscout ordering; the rest are sample
     wallets that give the field its shape. */
  topHolders: [
    { rank: 1, address: '0xE6189403…86e8', label: 'Top holder', pct: 3.81, value: 1958000, change: -0.4, kind: 'whale', behaviour: 'neutral', held: '7 months', note: 'Largest single address. No labelled identity, holds steadily.' },
    { rank: 2, address: '0xeD969960…4557', label: 'Whale', pct: 2.58, value: 1326000, change: 0, kind: 'whale', behaviour: 'smart', held: '6 months', note: 'Accumulated across the first quarter and has not sold.' },
    { rank: 3, address: '0xbb62C793…e6FE', label: 'Whale', pct: 1.81, value: 930000, change: -1.2, kind: 'whale', behaviour: 'neutral', held: '5 months', note: 'Trims occasionally, position broadly flat.' },
    { rank: 4, address: '0x7DAFbA1d…6f83', label: 'Holder', pct: 1.77, value: 910000, change: 0, kind: 'holder', behaviour: 'smart', held: '8 months', note: 'Entered near the pair opening, never reduced.' },
    { rank: 5, address: '0xbf034bC6…bb0b', label: 'Holder', pct: 1.59, value: 817000, change: -2.8, kind: 'holder', behaviour: 'seller', held: '3 weeks', note: 'Built quickly then sold most of it back.' },
    { rank: 6, address: '0x6ea80542…b23A', label: 'Holder', pct: 1.52, value: 781000, change: 0.6, kind: 'holder', behaviour: 'smart', held: '6 months', note: 'Adds on drawdowns.' },
    { rank: 7, address: '0x85f1Aa3a…D626', label: 'Aerodrome pool', pct: 1.48, value: 761000, change: 0, kind: 'lp', behaviour: 'neutral', held: 'since Dec 2025', note: 'Volatile AMM USDC/NOCK. Depth, not a position.' },
    { rank: 8, address: '0xDCd8E8d7…FA76', label: 'Holder', pct: 1.44, value: 740000, change: 0, kind: 'holder', behaviour: 'neutral', held: '4 months', note: 'No pattern strong enough to classify.' },
    { rank: 9, address: '0xB3089b4e…ba67', label: 'Holder', pct: 1.33, value: 683000, change: -3.6, kind: 'holder', behaviour: 'seller', held: '11 days', note: 'Short hold, exited into strength.' },
    { rank: 10, address: '0x4e3ae00E…1B60', label: 'Holder', pct: 1.16, value: 596000, change: 0.2, kind: 'holder', behaviour: 'neutral', held: '3 months', note: 'No pattern strong enough to classify.' },
    { rank: 11, address: '0x2f8a09c3…2e81', label: 'Miner payout · sample', pct: 1.02, value: 524000, change: -1.9, kind: 'whale', behaviour: 'seller', held: 'rolling', note: 'Models the continuous miner supply a proof-of-work chain produces.' },
    { rank: 12, address: '0x8d3e17b6…c1d3', label: 'Long holder · sample', pct: 0.94, value: 483000, change: 0, kind: 'early', behaviour: 'smart', held: '9 months', note: 'Opened near the pair launch and has never sold.' },
    { rank: 13, address: '0x6b02c714…9a41', label: 'Accumulator · sample', pct: 0.88, value: 452000, change: 1.4, kind: 'holder', behaviour: 'smart', held: '6 months', note: 'Adds on weakness, no sells recorded.' },
    { rank: 14, address: '0xc317ab90…4d08', label: 'Rotator · sample', pct: 0.79, value: 406000, change: -4.1, kind: 'holder', behaviour: 'seller', held: '9 days', note: 'In and out inside two weeks.' },
    { rank: 15, address: '0x9e45d201…2f77', label: 'Unlabelled · sample', pct: 0.71, value: 365000, change: 0.3, kind: 'holder', behaviour: 'neutral', held: '4 months', note: 'No pattern strong enough to classify.' },
    { rank: 16, address: '0x71c9e4a3…1b47', label: 'Uniswap pool', pct: 0.64, value: 329000, change: 0.1, kind: 'lp', behaviour: 'neutral', held: 'since Jan 2026', note: 'Second venue. Adds routing depth.' },
    { rank: 17, address: '0x13ad7e60…5c19', label: 'Unlabelled · sample', pct: 0.58, value: 298000, change: 0, kind: 'holder', behaviour: 'neutral', held: '2 months', note: 'No pattern strong enough to classify.' },
    { rank: 18, address: '0xf802a4d1…7e60', label: 'Early buyer · sample', pct: 0.52, value: 267000, change: -0.6, kind: 'early', behaviour: 'smart', held: '8 months', note: 'First-week entry, has trimmed 12%.' },
    { rank: 19, address: '0x47bc0d38…8b47', label: 'Quick seller · sample', pct: 0.47, value: 241000, change: -6.2, kind: 'holder', behaviour: 'seller', held: '3 days', note: 'Held under a week before exiting.' },
    { rank: 20, address: '0xa9618b47…0d38', label: 'Unlabelled · sample', pct: 0.41, value: 211000, change: 0.2, kind: 'holder', behaviour: 'neutral', held: '5 weeks', note: 'No pattern strong enough to classify.' },
    { rank: 21, address: '0x35c0f19e…7a22', label: 'Accumulator · sample', pct: 0.36, value: 185000, change: 0.9, kind: 'holder', behaviour: 'smart', held: '3 months', note: 'Small but consistently adding.' },
    { rank: 22, address: '0x0b74e2a8…14dd', label: 'Unlabelled · sample', pct: 0.31, value: 159000, change: -0.4, kind: 'holder', behaviour: 'neutral', held: '7 weeks', note: 'No pattern strong enough to classify.' },
    { rank: 23, address: '0xe5183c07…6b90', label: 'Quick seller · sample', pct: 0.27, value: 139000, change: -5.4, kind: 'holder', behaviour: 'seller', held: '5 days', note: 'Round trip inside a week.' },
    { rank: 24, address: '0x91d6740b…22ac', label: 'Unlabelled · sample', pct: 0.24, value: 123000, change: 0, kind: 'holder', behaviour: 'neutral', held: '6 weeks', note: 'No pattern strong enough to classify.' },
  ],



  /* Sourced from nockchain.org/roadmap — 33 published items with dates and
     statuses. The most recent are shown here. */
  roadmap: [
    {
      date: '2 May 2025',
      label: 'Open source release',
      detail: 'Client released publicly ahead of the mainnet launch target.',
      status: 'done',
      track: 'Ecosystem',
    },
    {
      date: '21 May 2025',
      label: 'Mainnet launch',
      detail: 'Genesis block attests to Bitcoin block 897,767.',
      status: 'done',
      track: 'Infrastructure',
    },
    {
      date: '26 Jun 2025',
      label: 'Jock language alpha',
      detail: 'Swift-like ergonomics for the Nock ecosystem.',
      status: 'done',
      track: 'Product',
    },
    {
      date: '31 Jul 2025',
      label: 'First mining pool',
      detail: 'H9 launches a Nockchain mining pool.',
      status: 'done',
      track: 'Infrastructure',
    },
    {
      date: '17 Oct 2025',
      label: 'First programmability features',
      detail: 'Transaction Engine v1 adds lock-script programmability at block 39,000.',
      status: 'done',
      track: 'Infrastructure',
    },
    {
      date: '28 Nov 2025',
      label: 'NockApp SDK v1',
      detail: 'Official SDK released with documentation and examples.',
      status: 'done',
      track: 'Product',
    },
    {
      date: '19 Dec 2025',
      label: 'Bridge to Base',
      detail: 'Cross-chain bridge with wrapped $NOCK on Base.',
      status: 'done',
      track: 'Infrastructure',
    },
    {
      date: '6 May 2026',
      label: 'Phase 2 consensus upgrade',
      detail: 'ASERT difficulty adjustment for smoother block times.',
      status: 'done',
      track: 'Infrastructure',
    },
    {
      date: 'Q2 2026',
      label: 'Demand paging (PMA)',
      detail: 'Node memory down to 16GB regardless of chain state size.',
      status: 'done',
      track: 'Infrastructure',
    },
    {
      date: 'Aug 2026',
      label: 'AI compute network',
      detail: 'Inference providers merge-mine existing workloads against Nockchain.',
      status: 'done',
      track: 'Product',
    },
    {
      date: 'Q3 2026',
      label: 'Bridge withdrawals',
      detail: 'Two-way transfers between Nockchain and Base.',
      status: 'active',
      track: 'Infrastructure',
    },
    {
      date: 'Q3 2026',
      label: 'Full Nock ZKVM completion',
      detail: 'General-purpose zero-knowledge proofs for arbitrary computation.',
      status: 'planned',
      track: 'Infrastructure',
    },
    {
      date: 'Q4 2026',
      label: 'Forced data availability',
      detail: 'L1 guarantee that transaction data is published on-chain.',
      status: 'planned',
      track: 'Infrastructure',
    },
    {
      date: 'Q4 2026',
      label: 'Privacy pool app',
      detail: 'Private economic activity built to the ShieldedCSV specification.',
      status: 'planned',
      track: 'Product',
    },
    {
      date: 'Q1 2027',
      label: 'ZK compute markets',
      detail: 'Verifiable workloads beyond AI, traded on Nockchain.',
      status: 'planned',
      track: 'Product',
    },
    {
      date: 'H1 2027',
      label: 'Post-quantum signatures',
      detail: 'Hardening accounts against future quantum adversaries.',
      status: 'planned',
      track: 'Infrastructure',
    },
  ],
  narrative: {
    nodes: [
      { id: 'core', label: 'Verifiable Compute', strength: 100, phase: 'Expanding', x: 100, y: 65, relation: 'Primary' },
      { id: 'zk', label: 'Zero-Knowledge', strength: 88, phase: 'Expanding', x: 32, y: 28, relation: 'Parent narrative' },
      { id: 'pow', label: 'Proof of Work', strength: 62, phase: 'Cooling', x: 168, y: 30, relation: 'Consensus family' },
      { id: 'money', label: 'Sound Money', strength: 58, phase: 'Emerging', x: 176, y: 96, relation: 'Token framing' },
      { id: 'base', label: 'Base Ecosystem', strength: 74, phase: 'Expanding', x: 100, y: 118, relation: 'Trading venue' },
      { id: 'urbit', label: 'Nock / Urbit stack', strength: 44, phase: 'Emerging', x: 24, y: 98, relation: 'Technical lineage' },
      { id: 'l1', label: 'New L1s', strength: 51, phase: 'Cooling', x: 62, y: 8, relation: 'Category' },
      { id: 'depin', label: 'Compute Markets', strength: 66, phase: 'Expanding', x: 150, y: 118, relation: 'Adjacent' },
    ],
    edges: [
      ['core', 'zk'],
      ['core', 'pow'],
      ['core', 'money'],
      ['core', 'base'],
      ['core', 'depin'],
      ['zk', 'l1'],
      ['zk', 'urbit'],
      ['pow', 'money'],
    ],
    reading: [
      { label: 'Narrative relevance', value: 81, note: 'Zero-knowledge infrastructure is still expanding.' },
      { label: 'Category crowding', value: 58, note: 'Many ZK projects, few using proofs as the mining function.' },
      { label: 'Differentiation', value: 86, note: 'ZKPoW is not a common consensus design.' },
    ],
  },



  risks: [
    { id: 'n-r1', label: 'Liquidity Depth', level: 'medium', score: 62, summary: 'Pool depth is 1.6% of market cap and 69% of it sits in one pair.' },
    { id: 'n-r2', label: 'Bridge Dependency', level: 'medium', score: 55, summary: 'The Base token is a bridged claim on native NOCK, not the asset itself.' },
    { id: 'n-r3', label: 'Audit Coverage', level: 'medium', score: 48, summary: 'No public audit located for the Base representation.' },
    { id: 'n-r4', label: 'Developer Risk', level: 'low', score: 20, summary: '19 contributors, 16 months of continuous history, permissive licence.' },
    { id: 'n-r5', label: 'Disclosure', level: 'low', score: 24, summary: 'Whitepaper, docs, roadmap and bug bounty are all public.' },
    { id: 'n-r6', label: 'Holder Concentration', level: 'low', score: 26, summary: 'Top 10 hold 18.5% of Base supply and the largest single holder is 3.8%.' },
  ],

  provenance: {
    overview: 'sample',
    fundamentals: 'live',
    developer: 'live',
    onchain: 'live',
    wallets: 'sample',
    kols: 'sample',
    github: 'live',
    social: 'sample',
    roadmap: 'live',
    narrative: 'sample',
    risk: 'sample',
  },
};
