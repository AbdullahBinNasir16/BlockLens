import type { ProjectDataset } from '../types';
import { heatmap, growth, spikeSeries, flow } from '../synth';
import { kolsFor } from '../kols';

/* ============================================================
   DOT — Dot, on Base

   Sourced figures (captured 09 Sep 2026):
     · market + pair data      DexScreener, Base / Uniswap DOT-ETH
     · supply + valuation      CoinGecko
     · repositories            GitHub API, usedotai/dot-loom + dot-reflex
     · links + documentation   usedot.xyz, git.usedot.xyz
   Sections marked 'sample' below carry illustrative shapes only.
   ============================================================ */

const CONTRACT = '0x23a2847d772803f9efc64b4277b782b06296fe51';
const DAYS = ['8d', '7d', '6d', '5d', '4d', '3d', '2d', '1d', 'now'];

export const dot: ProjectDataset = {
  project: {
    id: 'dot',
    name: 'Dot',
    ticker: 'DOT',
    chain: 'base',
    contract: CONTRACT,
    deployedAt: '27 May 2026',
    category: 'Infrastructure',
    categoryDetail: 'Private AI · inference and tooling',
    logo: '/tokens/dot.png',
    monogram: 'D',
    venue: 'Uniswap · DOT/ETH',
    snapshotAt: '09 Sep 2026',
    oneLiner:
      'An accountless AI platform — inference, coding, media generation and API access — where identity is stripped before the model call and payment is separated from usage.',
    idea: 'One interface over several model providers, with prompts detached from identity: memory stays in the browser, credits are encrypted, and payment settles in USDC or DOT rather than against a user account.',

    metrics: {
      price: 0.005437,
      priceChange24h: -3.8,
      marketCap: 4_789_905,
      fdv: 5_839_251,
      volume24h: 1_265_451,
      liquidity: 370_120,
      holders: 1_504,
      holdersChange24h: 2.9,
      ageLabel: '105d',
      ageHours: 2520,
      txns24h: { buys: 1_621, sells: 944 },
      supply: 1_000_000_000,
    },

    links: {
      explorer: `https://basescan.org/token/${CONTRACT}`,
      website: 'usedot.xyz',
      x: 'usedotai',
      github: 'usedotai/dot-loom',
      docs: 'git.usedot.xyz',
      telegram: 't.me/usedotxyz',
    },

    narrative: {
      primary: 'Private AI',
      relevance: 78,
      tags: ['Private Inference', 'AI Infrastructure', 'x402', 'Agent Payments', 'Base'],
    },

    scores: { risk: 46, confidence: 68, conviction: 'Moderate', riskLevel: 'medium' },

    parameters: [
      {
        id: 'fundamentals',
        label: 'Project Fundamentals',
        score: 76,
        note: 'A working product with published usage figures, and two open-source components.',
        drivers: [
          { label: 'Product is live and usable', weight: 34, signal: 'positive' },
          { label: 'Published throughput numbers', weight: 26, signal: 'positive' },
          { label: 'Two repos under permissive licences', weight: 22, signal: 'positive' },
          { label: 'Usage figures self-reported', weight: 18, signal: 'neutral' },
        ],
      },
      {
        id: 'idea',
        label: 'Idea / Uniqueness',
        score: 84,
        note: 'Privacy as the product rather than a feature is a defensible position in AI tooling.',
        drivers: [
          { label: 'Accountless by design', weight: 38, signal: 'positive' },
          { label: 'Payment separated from prompts', weight: 32, signal: 'positive' },
          { label: 'Privacy claims hard to verify', weight: 30, signal: 'neutral' },
        ],
      },
      {
        id: 'developer',
        label: 'Developer',
        score: 63,
        note: 'Public repos exist but have gone quiet — the active work is not in the open.',
        drivers: [
          { label: 'Two repos published', weight: 28, signal: 'positive' },
          { label: 'dot-loom last pushed 16 Jul', weight: 38, signal: 'negative' },
          { label: 'dot-reflex pushed once, never again', weight: 34, signal: 'negative' },
        ],
      },
      {
        id: 'onchain',
        label: 'On-Chain',
        score: 71,
        note: 'Very high turnover: 24h volume is 26% of market cap.',
        drivers: [
          { label: 'Buy/sell ratio 1.72 : 1', weight: 32, signal: 'positive' },
          { label: '2,565 transactions in 24h', weight: 30, signal: 'positive' },
          { label: 'Turnover of 26% is speculative', weight: 38, signal: 'neutral' },
        ],
      },
      {
        id: 'wallets',
        label: 'Wallets',
        score: 61,
        note: 'Top 10 hold 25.0% across only 1,504 holders.',
        drivers: [
          { label: 'Creator holds only 2.9%', weight: 32, signal: 'positive' },
          { label: 'Only 1,504 holders', weight: 38, signal: 'negative' },
          { label: 'Vesting contract holds 5.0%', weight: 30, signal: 'neutral' },
        ],
      },
      {
        id: 'kols',
        label: 'KOLs',
        score: 52,
        note: 'Sample roster. Ecosystem accounts have picked it up; win-rate history is thin.',
        drivers: [
          { label: 'Ecosystem coverage on Base', weight: 34, signal: 'positive' },
          { label: 'Short promoter track records', weight: 36, signal: 'negative' },
          { label: 'Disclosure inconsistent', weight: 30, signal: 'negative' },
        ],
      },
      {
        id: 'github',
        label: 'GitHub',
        score: 64,
        note: '180 and 80 stars, but neither repo has been pushed in weeks.',
        drivers: [
          { label: '260 stars across two repos', weight: 26, signal: 'positive' },
          { label: 'No push in 8 weeks', weight: 40, signal: 'negative' },
          { label: 'Zero forks on either repo', weight: 34, signal: 'negative' },
        ],
      },
      {
        id: 'x',
        label: 'X Analysis',
        score: 71,
        note: 'Sample behavioural read on @usedotai.',
        drivers: [
          { label: 'Product-led posting', weight: 34, signal: 'positive' },
          { label: 'Account age matches token', weight: 32, signal: 'neutral' },
          { label: 'Engagement tracks price closely', weight: 34, signal: 'neutral' },
        ],
      },
      {
        id: 'social',
        label: 'Social',
        score: 69,
        note: 'Sample. Growing interest, concentrated in the Base ecosystem.',
        drivers: [
          { label: 'Ecosystem amplification', weight: 36, signal: 'positive' },
          { label: 'Conversation is price-heavy', weight: 34, signal: 'neutral' },
          { label: 'Telegram and X only', weight: 30, signal: 'neutral' },
        ],
      },
      {
        id: 'narrative',
        label: 'Narrative',
        score: 78,
        note: 'Private inference is an expanding sub-narrative with few credible entrants.',
        drivers: [
          { label: 'Privacy narrative expanding', weight: 40, signal: 'positive' },
          { label: 'Few direct competitors onchain', weight: 32, signal: 'positive' },
          { label: 'Depends on the wider AI trade', weight: 28, signal: 'neutral' },
        ],
      },
      {
        id: 'liquidity',
        label: 'Liquidity',
        score: 66,
        note: '$370K against a $4.79M cap — 7.7%, with volume well above depth.',
        drivers: [
          { label: 'Quoted against ETH', weight: 30, signal: 'positive' },
          { label: 'Liquidity-to-cap ratio 7.7%', weight: 32, signal: 'neutral' },
          { label: 'Volume is 3.4× pool depth', weight: 38, signal: 'negative' },
        ],
      },
      {
        id: 'docs',
        label: 'Documentation',
        score: 58,
        note: 'A docs site exists. No whitepaper, no tokenomics page, no audit.',
        drivers: [
          { label: 'Docs site published', weight: 30, signal: 'positive' },
          { label: 'No tokenomics disclosure', weight: 36, signal: 'negative' },
          { label: 'No audit located', weight: 34, signal: 'negative' },
        ],
      },
      {
        id: 'risk',
        label: 'Risk Posture',
        score: 62,
        note: 'The product is real; the disclosure and repo-activity gaps are the concerns.',
        drivers: [
          { label: 'Working product with usage', weight: 34, signal: 'positive' },
          { label: 'Public repos gone quiet', weight: 34, signal: 'negative' },
          { label: 'Token utility undocumented', weight: 32, signal: 'negative' },
        ],
      },
    ],

    fundamentals: {
      uniqueness: {
        score: 84,
        note: 'Most AI wrappers compete on model access or price. Competing on identity separation — accountless usage, browser-side memory, payment decoupled from prompts — is a different axis.',
      },
      innovation: {
        score: 71,
        note: 'The privacy architecture is thoughtful, but it composes existing pieces rather than introducing a new primitive.',
      },
      keyFindings: [
        {
          text: 'The product is live with published throughput — 5.5B tokens processed since 6 July.',
          signal: 'positive',
        },
        {
          text: 'Neither public repository has been pushed in eight weeks; dot-reflex was pushed once and never updated.',
          signal: 'negative',
        },
        {
          text: '24h volume is 3.4× the pool depth, which is a speculative rather than organic ratio.',
          signal: 'neutral',
        },
      ],
    },

    assessment: {
      bullets: [
        { text: 'Working product with published throughput — 5.5B tokens processed since 6 July.', signal: 'positive' },
        { text: 'Privacy as the product, not a feature, is a genuinely differentiated position.', signal: 'positive' },
        { text: 'Quoted against ETH with liquidity at 7.7% of market cap.', signal: 'positive' },
        { text: 'Neither public repository has been pushed in eight weeks.', signal: 'negative' },
        { text: 'A VestingManager contract holds 5.0% on-chain, but no schedule is published.', signal: 'negative' },
        { text: '24h volume is 3.4× pool depth — a speculative rather than organic ratio.', signal: 'negative' },
        { text: 'Usage and privacy claims are self-reported and off-chain by nature.', signal: 'neutral' },
      ],
    },
  },

  developer: {
    id: 'dev-dot',
    alias: 'usedotai',
    handle: 'usedotai',
    githubUser: 'usedotai',
    wallet: CONTRACT,
    firstSeen: 'May 2026',
    identityConfidence: 58,
    doxxed: false,
    summary:
      'Pseudonymous org. Two repositories published under usedotai, both quiet since mid-summer, while the hosted product continues to report usage.',
    stats: { deployments: 1, activeProjects: 1, abandoned: 0, rugs: 0 },
    history: [
      {
        year: '2026',
        name: 'Token pair opened',
        ticker: 'DOT',
        chain: 'base',
        outcome: 'Live',
        outcomeSignal: 'neutral',
        peak: '—',
        duration: '105 days',
        note: 'Uniswap DOT/ETH created 27 May 2026.',
      },
      {
        year: '2026',
        name: 'dot-loom published',
        ticker: 'REPO',
        chain: 'base',
        outcome: 'Stale',
        outcomeSignal: 'negative',
        peak: '—',
        duration: '3 weeks active',
        note: 'Created 23 Jun 2026, last push 16 Jul 2026. 180 stars, zero forks.',
      },
      {
        year: '2026',
        name: 'Product usage reported',
        ticker: 'PROD',
        chain: 'base',
        outcome: 'Running',
        outcomeSignal: 'positive',
        peak: '—',
        duration: 'since 6 Jul',
        note: '5.5B tokens processed, 400M in the single biggest day, 99%+ reported uptime.',
      },
      {
        year: '2026',
        name: 'dot-reflex published',
        ticker: 'REPO',
        chain: 'base',
        outcome: 'One push only',
        outcomeSignal: 'negative',
        peak: '—',
        duration: '1 day',
        note: 'Created and last pushed on the same day, 28 Aug 2026. 80 stars, zero forks.',
        current: true,
      },
    ],
    activity: [
      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 22, 71, 88, 34, 8, 26, 4,
    ],
  },

  deployerFacts: [
    { label: 'Repositories', value: '2', signal: 'neutral' },
    { label: 'Last push', value: '8wk ago', signal: 'negative' },
    { label: 'Forks', value: '0', signal: 'negative' },
    { label: 'Licences', value: 'MIT · Apache', signal: 'positive' },
    { label: 'Identity', value: 'Pseudonymous', signal: 'neutral' },
    { label: 'First seen', value: 'May 2026', signal: 'neutral' },
  ],



  /* Sample roster. Handles are placeholders — no real account is scored here. */
  /* Real accounts. The win rate and outcome beside each one are prototype
     sample values, not a measured record — see the section note. */
  /* read from the directory, so the record matches everywhere it appears */
  kols: kolsFor(['DrShillBee', 'kyle', 'blknoiz06', 'HsakaTrades', 'CryptoKaleo', 'gainzy222']),


  github: {
    repo: 'usedotai/dot-loom',
    url: 'https://github.com/usedotai/dot-loom',
    description:
      'Provider-pluggable orchestration runtime for multi-model AI inference. A second repository, dot-reflex, holds the agent execution-recovery controller.',
    stars: 180,
    forks: 0,
    watchers: 1,
    contributors: 2,
    commits: 148,
    openIssues: 0,
    license: 'MIT',
    createdAt: 'Jun 2026',
    lastCommit: '16 Jul 2026',
    primaryLanguage: 'JavaScript',
    languages: [
      { name: 'JavaScript', pct: 52.5 },
      { name: 'Python', pct: 39.1 },
      { name: 'CSS', pct: 5.9 },
      { name: 'Other', pct: 2.5 },
    ],
    heatmap: heatmap(990327, { ramp: 44, quiet: [49, 50, 51, 52], recent: 0.1, base: 0.04 }),
    timeline: [
      { date: 'May 2026', label: 'Token pair opens', detail: 'Uniswap DOT/ETH · 27 May 2026', kind: 'release' },
      { date: 'Jun 2026', label: 'dot-loom published', detail: 'Created 23 Jun 2026 · MIT · 180 stars', kind: 'build' },
      { date: 'Jul 2026', label: 'Product usage begins', detail: 'Throughput reported from 6 Jul onward', kind: 'release' },
      { date: 'Jul 2026', label: 'dot-loom goes quiet', detail: 'Last push 16 Jul 2026', kind: 'audit' },
      { date: 'Aug 2026', label: 'dot-reflex published', detail: 'Created and last pushed 28 Aug 2026 · 80 stars', kind: 'build' },
      { date: 'Sep 2026', label: 'No public commits', detail: 'Eight weeks with no push on either repository', kind: 'current' },
    ],
    topContributors: [
      { user: 'primary author', commits: 121, share: 82, linked: false },
      { user: 'second author', commits: 27, share: 18, linked: false },
    ],
    consistency: [
      { label: 'Active weeks', value: 22, note: '3 active weeks since the repo opened' },
      { label: 'Bus factor', value: 28, note: 'One author writes 82% of commits' },
      { label: 'Post-launch activity', value: 18, note: 'No push in 8 weeks' },
      { label: 'Downstream use', value: 12, note: 'Zero forks on either repository' },
    ],
  },

  social: {
    handle: 'usedotai',
    url: 'https://x.com/usedotai',
    followers: 31_800,
    followersChange7d: 18.6,
    posts30d: 74,
    avgEngagement: 3.8,
    accountCreated: '2026',
    growth: growth(7711, DAYS, 26_100, 31_800, 0.025),
    mentions: spikeSeries(7712, DAYS, 90, 610, 5),
    topAccounts: [
      { handle: 'usedotai', followers: 31800, kind: 'Official', sentiment: 'neutral' },
      { handle: 'AIonBase_', followers: 46200, kind: 'Ecosystem', sentiment: 'neutral' },
      { handle: 'base', followers: 1240000, kind: 'Ecosystem', sentiment: 'neutral' },
      { handle: 'blknoiz06', followers: 812000, kind: 'Commentary', sentiment: 'neutral' },
    ],
    momentum: [
      { label: 'Mention velocity', value: 76, delta: 31 },
      { label: 'Unique authors', value: 68, delta: 19 },
      { label: 'Reply depth', value: 44, delta: -12 },
      { label: 'Sentiment', value: 71, delta: 8 },
    ],
    authenticity: {
      overall: 71,
      verdict: 'Mixed',
      axes: [
        { label: 'Account age', value: 58, note: 'Roughly the same age as the token' },
        { label: 'Posting consistency', value: 82, note: '74 posts in 30 days' },
        { label: 'Original content', value: 76, note: 'Product updates dominate' },
        { label: 'Engagement consistency', value: 61, note: 'Tracks price closely' },
        { label: 'Follower behaviour', value: 66, note: 'Sample axis — needs follower-level data' },
        { label: 'Posting pattern', value: 72, note: 'Human-consistent hours' },
      ],
      notes: [
        { text: 'Posting is product-led rather than purely promotional.', signal: 'positive' },
        { text: 'Engagement rises and falls with price, which weakens it as an independent signal.', signal: 'neutral' },
        { text: 'Reply depth is the one falling metric on the roster.', signal: 'negative' },
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
        display: '25.0%',
        dial: 58,
        caption: 'PoolManager 6.3% · VestingManager 5.0%',
        tone: 'warn',
        sourced: true,
      },
      {
        id: 'insiders',
        label: 'Insiders',
        display: 'Not measured',
        dial: 50,
        caption: 'clustering not run · 7 of top 10 are contracts',
        tone: 'warn',
        sourced: false,
      },
      {
        id: 'dev',
        label: 'Dev holding',
        display: '2.9%',
        dial: 71,
        caption: 'creator contract 0xD2Be…9880',
        tone: 'good',
        sourced: true,
      },
      {
        id: 'bundlers',
        label: 'Bundlers',
        display: 'Not measured',
        dial: 50,
        caption: 'launch-block analysis not run',
        tone: 'warn',
        sourced: false,
      },
      {
        id: 'lp',
        label: 'LP burned',
        display: 'Not burned',
        dial: 38,
        caption: 'Uniswap v4 PoolManager holds 6.3%',
        tone: 'warn',
        sourced: false,
      },
      {
        id: 'dexpaid',
        label: 'Dex paid',
        display: 'Yes',
        dial: 100,
        caption: 'token profile approved 27 May 2026',
        tone: 'good',
        sourced: true,
      },
      {
        id: 'smart',
        label: 'Smart traders',
        display: 'Mixed',
        dial: 55,
        caption: 'high churn against 1,504 holders',
        tone: 'warn',
        sourced: false,
      },
    ],
    distribution: [
      { label: '< $100', pct: 44.8, wallets: 674, signal: 'positive' },
      { label: '$100 – $1K', pct: 33.1, wallets: 498, signal: 'positive' },
      { label: '$1K – $10K', pct: 16.4, wallets: 247, signal: 'neutral' },
      { label: '$10K – $50K', pct: 4.4, wallets: 66, signal: 'neutral' },
      { label: '> $50K', pct: 1.3, wallets: 19, signal: 'neutral' },
    ],
    holderGrowth: growth(8801, ['May', 'Jun', 'Jul', 'Aug', 'Sep'], 180, 1_504, 0.05),
    buySell: flow(8802, 9, 1_621, 944),
    concentration: {
      top10: 24.97,
      top50: 50.28,
      gini: 0.62,
      verdict: 'Moderate · 7 of top 10 are contracts',
      signal: 'neutral',
    },
    liquidity: {
      pooled: 370_257,
      lockedPct: 0,
      lockUntil: 'Not disclosed',
      pairs: [
        { dex: 'Uniswap', pair: 'DOT / ETH', liquidity: 370_120, share: 99.96 },
        { dex: 'Uniswap', pair: 'DOT / USDC', liquidity: 120, share: 0.03 },
        { dex: '5 other pairs', pair: 'mixed', liquidity: 17, share: 0.01 },
      ],
    },
  },

  /* Ranks 1-10 mirror the real Blockscout ordering; the rest are sample
     wallets that give the field its shape. */
  topHolders: [
    { rank: 1, address: '0x498581fF…2b2b', label: 'Uniswap v4 PoolManager', pct: 6.29, value: 301300, change: 0, kind: 'lp', behaviour: 'neutral', held: 'since May 2026', note: 'The singleton pool contract. Depth, not a position.' },
    { rank: 2, address: '0x7ca3dE7D…20c5', label: 'VestingManager', pct: 5, value: 239500, change: 0, kind: 'treasury', behaviour: 'neutral', held: 'since launch', note: 'A vesting contract exists on-chain. No schedule is published anywhere.' },
    { rank: 3, address: '0xD2BeA426…9880', label: 'Creator contract', pct: 2.91, value: 139400, change: 0, kind: 'deployer', behaviour: 'neutral', held: 'since launch', note: 'The address that deployed the token. Holds 2.9%.' },
    { rank: 4, address: '0x3E032031…D0B7', label: 'Unlabelled contract', pct: 2.13, value: 102000, change: 0, kind: 'cluster', behaviour: 'neutral', held: 'since launch', note: 'Unlabelled contract, no outflows observed.' },
    { rank: 5, address: '0x28C66690…C245', label: 'Whale', pct: 2.04, value: 97700, change: -1.6, kind: 'whale', behaviour: 'neutral', held: '3 months', note: 'Largest externally owned account.' },
    { rank: 6, address: '0x46b6A099…7E6A', label: 'Holder', pct: 1.53, value: 73300, change: 0.5, kind: 'holder', behaviour: 'smart', held: '3 months', note: 'Adds steadily, no sells recorded.' },
    { rank: 7, address: '0xc9cAfef2…48e2', label: 'Unlabelled contract', pct: 1.5, value: 71800, change: 0, kind: 'cluster', behaviour: 'neutral', held: 'since launch', note: 'Unlabelled contract.' },
    { rank: 8, address: '0x82846457…6a88', label: 'Holder', pct: 1.2, value: 57500, change: -3.2, kind: 'holder', behaviour: 'seller', held: '12 days', note: 'Reduced most of the position within two weeks.' },
    { rank: 9, address: '0xba66D0C5…02D9', label: 'Holder', pct: 1.2, value: 57500, change: 0, kind: 'holder', behaviour: 'neutral', held: '2 months', note: 'No pattern strong enough to classify.' },
    { rank: 10, address: '0xEEfE9aBB…b072', label: 'Unlabelled contract', pct: 1.17, value: 56000, change: 0, kind: 'cluster', behaviour: 'neutral', held: 'since launch', note: 'Unlabelled contract.' },
    { rank: 11, address: '0x7e2c04a9…c204', label: 'Active trader · sample', pct: 1.04, value: 49800, change: -2.7, kind: 'whale', behaviour: 'seller', held: '2 weeks', note: 'High turnover, matching the 26% daily churn.' },
    { rank: 12, address: '0x159e83b0…e185', label: 'Long holder · sample', pct: 0.93, value: 44500, change: 0, kind: 'early', behaviour: 'smart', held: '3 months', note: 'Entered near launch, no sells recorded.' },
    { rank: 13, address: '0x62d17a90…4c81', label: 'Accumulator · sample', pct: 0.84, value: 40200, change: 1.8, kind: 'holder', behaviour: 'smart', held: '2 months', note: 'Adds on weakness, position still growing.' },
    { rank: 14, address: '0xae0413c7…9f30', label: 'Rotator · sample', pct: 0.76, value: 36400, change: -4.4, kind: 'holder', behaviour: 'seller', held: '6 days', note: 'Entered late, exited most of it within a week.' },
    { rank: 15, address: '0x0f836b12…2a95', label: 'Unlabelled · sample', pct: 0.68, value: 32600, change: 0.2, kind: 'holder', behaviour: 'neutral', held: '7 weeks', note: 'No pattern strong enough to classify.' },
    { rank: 16, address: '0xd47ac025…6e18', label: 'Early buyer · sample', pct: 0.61, value: 29200, change: 0, kind: 'early', behaviour: 'smart', held: '3 months', note: 'First-week entry, has never trimmed.' },
    { rank: 17, address: '0x2b6e91f4…70b3', label: 'Quick seller · sample', pct: 0.55, value: 26300, change: -8.1, kind: 'holder', behaviour: 'seller', held: '2 days', note: 'Round trip inside 48 hours.' },
    { rank: 18, address: '0x8c053e71…41ba', label: 'Unlabelled · sample', pct: 0.49, value: 23500, change: 0.4, kind: 'holder', behaviour: 'neutral', held: '5 weeks', note: 'No pattern strong enough to classify.' },
    { rank: 19, address: '0xf3197ab2…08c7', label: 'Unlabelled · sample', pct: 0.44, value: 21100, change: -0.3, kind: 'holder', behaviour: 'neutral', held: '1 month', note: 'No pattern strong enough to classify.' },
    { rank: 20, address: '0x6a2d80f5…b391', label: 'Quick seller · sample', pct: 0.39, value: 18700, change: -6.6, kind: 'holder', behaviour: 'seller', held: '4 days', note: 'Short hold, sold into the first run.' },
    { rank: 21, address: '0x1c95e370…d284', label: 'Accumulator · sample', pct: 0.34, value: 16300, change: 0.7, kind: 'holder', behaviour: 'smart', held: '6 weeks', note: 'Small but consistently adding.' },
    { rank: 22, address: '0xb08f24c6…5a71', label: 'Unlabelled · sample', pct: 0.29, value: 13900, change: 0, kind: 'holder', behaviour: 'neutral', held: '4 weeks', note: 'No pattern strong enough to classify.' },
  ],



  /* Built from the product and docs index at git.usedot.xyz plus dated
     repository events. Repository cadence is marked missed on the evidence
     of an 8-week gap with no public push. */
  roadmap: [
    {
      date: '27 May 2026',
      label: 'Token pair opens',
      detail: 'Uniswap DOT/ETH created on Base.',
      status: 'done',
      track: 'Ecosystem',
    },
    {
      date: 'Jun 2026',
      label: 'Dot Loom open sourced',
      detail: 'Provider-pluggable orchestration runtime published under MIT.',
      status: 'done',
      track: 'Product',
    },
    {
      date: '6 Jul 2026',
      label: 'Inference goes live',
      detail: '5.5B tokens processed since, with 400M in the largest single day.',
      status: 'done',
      track: 'Product',
    },
    {
      date: '2026',
      label: 'Product surfaces shipped',
      detail: 'DotChat, DotCode, DotImage and DotVideo documented as live.',
      status: 'done',
      track: 'Product',
    },
    {
      date: '28 Aug 2026',
      label: 'Dot Reflex open sourced',
      detail: 'Agent execution-recovery controller published under Apache-2.0.',
      status: 'done',
      track: 'Product',
    },
    {
      date: 'Jul–Sep 2026',
      label: 'Open-source cadence',
      detail: 'No public push in eight weeks; dot-reflex was pushed once and never updated.',
      status: 'missed',
      track: 'Product',
    },
    {
      date: '2026',
      label: 'Tokenomics disclosure',
      detail: 'A VestingManager contract holds 5.0% on-chain, but no schedule is published anywhere.',
      status: 'missed',
      track: 'Token',
    },
    {
      date: 'Q3 2026',
      label: 'DotAPI and DotMCP',
      detail: 'Programmatic and MCP access documented; availability unverified.',
      status: 'active',
      track: 'Product',
    },
    {
      date: 'Q3 2026',
      label: 'DotPay and $DOT rails',
      detail: 'Inference payable in USDC and DOT; settlement path not traced.',
      status: 'active',
      track: 'Token',
    },
    {
      date: 'Q4 2026',
      label: 'Verify v.01',
      detail: 'Verifiability layer described in the docs, not yet released.',
      status: 'planned',
      track: 'Infrastructure',
    },
    {
      date: 'Q4 2026',
      label: 'Governance',
      detail: 'Token governance described in the docs index only.',
      status: 'planned',
      track: 'Token',
    },
  ],
  narrative: {
    nodes: [
      { id: 'core', label: 'Private AI', strength: 100, phase: 'Expanding', x: 100, y: 65, relation: 'Primary' },
      { id: 'inference', label: 'Inference Markets', strength: 74, phase: 'Expanding', x: 34, y: 26, relation: 'Parent narrative' },
      { id: 'privacy', label: 'Onchain Privacy', strength: 68, phase: 'Emerging', x: 166, y: 28, relation: 'Parent narrative' },
      { id: 'x402', label: 'Agent Payments', strength: 62, phase: 'Emerging', x: 176, y: 94, relation: 'Implements' },
      { id: 'base', label: 'Base Ecosystem', strength: 76, phase: 'Expanding', x: 100, y: 118, relation: 'Deployment chain' },
      { id: 'agents', label: 'Agent Tooling', strength: 58, phase: 'Cooling', x: 24, y: 96, relation: 'Adjacent' },
      { id: 'aitokens', label: 'AI Tokens', strength: 46, phase: 'Cooling', x: 62, y: 8, relation: 'Loose association' },
      { id: 'depin', label: 'Compute Markets', strength: 52, phase: 'Expanding', x: 150, y: 118, relation: 'Adjacent' },
    ],
    edges: [
      ['core', 'inference'],
      ['core', 'privacy'],
      ['core', 'x402'],
      ['core', 'base'],
      ['core', 'agents'],
      ['inference', 'aitokens'],
      ['inference', 'depin'],
      ['privacy', 'x402'],
    ],
    reading: [
      { label: 'Narrative relevance', value: 78, note: 'Private inference is expanding and thinly populated onchain.' },
      { label: 'Category crowding', value: 46, note: 'Few direct onchain competitors on privacy specifically.' },
      { label: 'Differentiation', value: 84, note: 'Accountless usage is a clear axis of separation.' },
    ],
  },



  risks: [
    { id: 'd-r1', label: 'Repository Dormancy', level: 'high', score: 72, summary: 'Eight weeks with no push, and one repo was pushed exactly once.' },
    { id: 'd-r2', label: 'Disclosure Gaps', level: 'medium', score: 58, summary: 'A VestingManager contract holds 5.0% on-chain, yet no schedule or allocation is published.' },
    { id: 'd-r3', label: 'Turnover vs Depth', level: 'medium', score: 58, summary: 'Daily volume is 3.4× pool depth — a speculative ratio.' },
    { id: 'd-r4', label: 'Holder Base', level: 'high', score: 66, summary: 'Only 1,504 holders, and seven of the top ten addresses are contracts.' },
    { id: 'd-r5', label: 'Unverifiable Claims', level: 'medium', score: 47, summary: 'Usage and privacy claims are self-reported and off-chain by nature.' },
    { id: 'd-r6', label: 'Contract Risk', level: 'low', score: 28, summary: 'No contract-level flags found. Licences are permissive and published.' },
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
