import type { ProjectDataset } from '../types';
import { heatmap, growth, spikeSeries, flow } from '../synth';

/* ============================================================
   SIBYL — SIBYL by Virtuals, on Base

   Sourced figures (captured 09 Sep 2026):
     · market + pair data      DexScreener, Base / Uniswap SIBYL-VIRTUAL
     · supply + valuation      CoinGecko
     · repository              GitHub API, Sibyl-Labs/Sibyl-Memory
     · links + documentation   sibyllabs.org, docs.sibylcap.com
   Sections marked 'sample' below carry illustrative shapes only.
   ============================================================ */

const CONTRACT = '0x797f214a2cd64a4963a91fa21c8c55ec3eba4714';
const DAYS = ['8d', '7d', '6d', '5d', '4d', '3d', '2d', '1d', 'now'];

export const sibyl: ProjectDataset = {
  project: {
    id: 'sibyl',
    name: 'Sibyl',
    ticker: 'SIBYL',
    chain: 'base',
    contract: CONTRACT,
    deployedAt: '18 Mar 2026',
    category: 'AI Agent',
    categoryDetail: 'Autonomous agent · Virtuals',
    logo: '/tokens/sibyl.png',
    monogram: 'S',
    venue: 'Uniswap · SIBYL/VIRTUAL',
    snapshotAt: '09 Sep 2026',
    oneLiner:
      'An autonomous agent that takes token positions in early projects and provides ongoing advisory, operated by a named company.',
    idea: 'Sibyl Labs builds the memory architecture and agent framework; the agent runs on it in production — trading engine, on-chain messaging, an x402 payment rail, and an advisory dashboard.',

    metrics: {
      price: 0.001913,
      priceChange24h: 151.0,
      marketCap: 1_871_542,
      fdv: 1_913_067,
      volume24h: 159_423,
      liquidity: 199_955,
      holders: 3_157,
      holdersChange24h: 4.8,
      ageLabel: '175d',
      ageHours: 4200,
      txns24h: { buys: 221, sells: 168 },
      supply: 1_000_000_000,
    },

    links: {
      explorer: `https://basescan.org/token/${CONTRACT}`,
      website: 'sibyllabs.org',
      x: 'sibylcap',
      github: 'Sibyl-Labs/Sibyl-Memory',
      docs: 'docs.sibylcap.com',
      discord: 'discord.gg/vhpTJwt9PX',
      extra: [{ label: 'Agent', url: 'https://sibylcap.com' }],
    },

    narrative: {
      primary: 'Agent Infrastructure',
      relevance: 69,
      tags: ['AI Agents', 'Virtuals', 'Agent Memory', 'x402', 'Base'],
    },

    scores: { risk: 52, confidence: 71, conviction: 'Moderate', riskLevel: 'medium' },

    parameters: [
      {
        id: 'fundamentals',
        label: 'Project Fundamentals',
        score: 74,
        note: 'A named LLC, shipped open-source packages, and a benchmark result behind the agent.',
        drivers: [
          { label: 'Operating company is named', weight: 32, signal: 'positive' },
          { label: 'Shipped memory package, MIT', weight: 30, signal: 'positive' },
          { label: 'Revenue model still early', weight: 22, signal: 'neutral' },
          { label: 'Market cap under $2M', weight: 16, signal: 'neutral' },
        ],
      },
      {
        id: 'idea',
        label: 'Idea / Uniqueness',
        score: 81,
        note: 'File-based agent memory with no vector store is a genuinely contrarian design.',
        drivers: [
          { label: 'No embeddings, no vector DB', weight: 40, signal: 'positive' },
          { label: 'Benchmark result published', weight: 30, signal: 'positive' },
          { label: 'Crowded agent-token field', weight: 30, signal: 'neutral' },
        ],
      },
      {
        id: 'developer',
        label: 'Developer',
        score: 68,
        note: 'Three contributors. Small team, but shipping into a public repo weekly.',
        drivers: [
          { label: 'Pushed within the last week', weight: 34, signal: 'positive' },
          { label: 'Named legal entity', weight: 30, signal: 'positive' },
          { label: 'Only 3 contributors', weight: 36, signal: 'negative' },
        ],
      },
      {
        id: 'onchain',
        label: 'On-Chain',
        score: 62,
        note: 'Low absolute activity: 389 transactions in 24 hours.',
        drivers: [
          { label: 'Buy/sell ratio 1.32 : 1', weight: 30, signal: 'positive' },
          { label: 'Only 389 txns in 24h', weight: 36, signal: 'negative' },
          { label: 'Two pairs, one of them dust', weight: 34, signal: 'negative' },
        ],
      },
      {
        id: 'wallets',
        label: 'Wallets',
        score: 41,
        note: 'Top 10 hold 58.7% of supply across 3,157 holders.',
        drivers: [
          { label: 'Top 10 hold 58.7% of supply', weight: 40, signal: 'negative' },
          { label: 'Two contracts hold 31.7%', weight: 34, signal: 'negative' },
          { label: 'Only 3,157 holders', weight: 26, signal: 'negative' },
        ],
      },
      {
        id: 'kols',
        label: 'Promotion',
        score: 47,
        note: 'Sample roster. Very little third-party coverage at this size.',
        drivers: [
          { label: 'Low promotional footprint', weight: 34, signal: 'positive' },
          { label: 'Almost no external coverage', weight: 40, signal: 'negative' },
          { label: 'Audience concentrated in Virtuals', weight: 26, signal: 'neutral' },
        ],
      },
      {
        id: 'github',
        label: 'GitHub',
        score: 72,
        note: '147 stars, MIT, pushed 7 Sep 2026 — but only three contributors.',
        drivers: [
          { label: 'Active and recent', weight: 34, signal: 'positive' },
          { label: '147 stars, 14 forks', weight: 26, signal: 'positive' },
          { label: 'Bus factor of three', weight: 40, signal: 'negative' },
        ],
      },
      {
        id: 'x',
        label: 'X Analysis',
        score: 74,
        note: 'Sample behavioural read on @sibylcap.',
        drivers: [
          { label: 'Consistent build-in-public posting', weight: 38, signal: 'positive' },
          { label: 'Account age matches launch', weight: 30, signal: 'neutral' },
          { label: 'Engagement narrow but real', weight: 32, signal: 'neutral' },
        ],
      },
      {
        id: 'social',
        label: 'Social',
        score: 61,
        note: 'Sample. Small, technical community around the agent.',
        drivers: [
          { label: 'Discord present and active', weight: 32, signal: 'positive' },
          { label: 'Small absolute audience', weight: 38, signal: 'negative' },
          { label: 'Virtuals ecosystem overlap', weight: 30, signal: 'neutral' },
        ],
      },
      {
        id: 'narrative',
        label: 'Narrative',
        score: 69,
        note: 'Agent tokens are past their first peak; agent infrastructure is holding.',
        drivers: [
          { label: 'Memory / infra angle is durable', weight: 38, signal: 'positive' },
          { label: 'Agent-token narrative cooled', weight: 36, signal: 'negative' },
          { label: 'Virtuals ecosystem still active', weight: 26, signal: 'neutral' },
        ],
      },
      {
        id: 'liquidity',
        label: 'Liquidity',
        score: 57,
        note: '$200K against a $1.87M cap — a healthy 10.7% ratio, but small in absolute terms.',
        drivers: [
          { label: 'Liquidity-to-cap ratio 10.7%', weight: 38, signal: 'positive' },
          { label: 'Only $200K of absolute depth', weight: 36, signal: 'negative' },
          { label: 'Quote asset is VIRTUAL, not ETH', weight: 26, signal: 'negative' },
        ],
      },
      {
        id: 'docs',
        label: 'Documentation',
        score: 76,
        note: 'Two sites and a docs domain. Lab and agent are documented separately.',
        drivers: [
          { label: 'Dedicated docs domain', weight: 34, signal: 'positive' },
          { label: 'Lab and agent both documented', weight: 30, signal: 'positive' },
          { label: 'No whitepaper', weight: 36, signal: 'negative' },
        ],
      },
      {
        id: 'risk',
        label: 'Risk Posture',
        score: 58,
        note: 'Small cap, thin absolute depth, three contributors. No contract-level flags found.',
        drivers: [
          { label: 'Open source, named entity', weight: 34, signal: 'positive' },
          { label: 'Size makes it easy to move', weight: 34, signal: 'negative' },
          { label: 'Key-person concentration', weight: 32, signal: 'negative' },
        ],
      },
    ],

    fundamentals: {
      uniqueness: {
        score: 81,
        note: 'Durable file-based memory with no vector database is the opposite of the standard retrieval stack, and there is a published benchmark to argue it.',
      },
      innovation: {
        score: 74,
        note: 'Strong on the memory layer. The agent-with-a-company framing is positioning more than technology.',
      },
      keyFindings: [
        {
          text: 'Operated by a named company, Sibyl Labs LLC, rather than an anonymous team.',
          signal: 'positive',
        },
        {
          text: 'Three contributors on the main repository — a real key-person concentration.',
          signal: 'negative',
        },
        {
          text: 'Priced against VIRTUAL rather than ETH, so it inherits that pair’s volatility.',
          signal: 'neutral',
        },
      ],
    },

    assessment: {
      bullets: [
        { text: 'Operated by a named company, Sibyl Labs LLC — unusual clarity at a $1.9M cap.', signal: 'positive' },
        { text: 'Memory package shipped under MIT with 147 stars and a push within the last week.', signal: 'positive' },
        { text: 'The agent was running in production a month before the token existed.', signal: 'positive' },
        { text: 'Liquidity is 10.7% of cap — a healthy ratio, but only $200K in absolute terms.', signal: 'neutral' },
        { text: 'Three contributors, with the lead writing roughly 74% of commits.', signal: 'negative' },
        { text: '389 transactions in 24 hours is thin even for this size.', signal: 'negative' },
        { text: 'Priced against VIRTUAL rather than ETH, so it inherits that pair’s volatility.', signal: 'negative' },
      ],
    },
  },

  developer: {
    id: 'dev-sibyl',
    alias: 'Sibyl Labs LLC',
    handle: 'sibylcap',
    githubUser: 'Sibyl-Labs',
    wallet: '0x797f214a2cd64a4963a91fa21c8c55ec3eba4714',
    firstSeen: 'Mar 2026',
    identityConfidence: 84,
    doxxed: false,
    summary:
      'A named limited company rather than a pseudonym. The lab publishes under Sibyl-Labs on GitHub and operates the agent under sibylcap.com.',
    stats: { deployments: 1, activeProjects: 1, abandoned: 0, rugs: 0 },
    history: [
      {
        year: '2026',
        name: 'Agent in production',
        ticker: 'AGENT',
        chain: 'base',
        outcome: 'Running',
        outcomeSignal: 'positive',
        peak: '—',
        duration: '7 months',
        note: 'The agent has been operating since February 2026, before the token existed.',
      },
      {
        year: '2026',
        name: 'Token launch',
        ticker: 'SIBYL',
        chain: 'base',
        outcome: 'Live',
        outcomeSignal: 'neutral',
        peak: '—',
        duration: '175 days',
        note: 'Launched through Virtuals Protocol. Uniswap SIBYL/VIRTUAL pair created 18 Mar 2026.',
      },
      {
        year: '2026',
        name: 'Sibyl-Memory published',
        ticker: 'REPO',
        chain: 'base',
        outcome: 'Active',
        outcomeSignal: 'positive',
        peak: '—',
        duration: '4 months',
        note: 'Repository created 20 May 2026 under MIT. 147 stars, last push 7 Sep 2026.',
        current: true,
      },
    ],
    activity: [
      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 14, 28, 44, 58, 51, 66, 74, 69, 81, 77, 88, 92,
    ],
  },

  deployerFacts: [
    { label: 'Entity', value: 'Named LLC', signal: 'positive' },
    { label: 'Contributors', value: '3', signal: 'negative' },
    { label: 'Repo age', value: '4mo', signal: 'neutral' },
    { label: 'Licence', value: 'MIT', signal: 'positive' },
    { label: 'Rugs on record', value: '0', signal: 'positive' },
    { label: 'First seen', value: 'Mar 2026', signal: 'neutral' },
  ],



  /* Sample roster. Handles are placeholders — no real account is scored here. */
  /* Real accounts. The win rate and outcome beside each one are prototype
     sample values, not a measured record — see the section note. */
  /* read from the directory, so the record matches everywhere it appears */


  github: {
    repo: 'Sibyl-Labs/Sibyl-Memory',
    url: 'https://github.com/Sibyl-Labs/Sibyl-Memory',
    description:
      'Durable, file-based long-term memory for AI agents. SDK, CLI, MCP server, Hermes adapter and a LangGraph BaseStore. No vector database, no embeddings.',
    stars: 147,
    forks: 14,
    watchers: 6,
    contributors: 3,
    commits: 486,
    openIssues: 3,
    license: 'MIT',
    createdAt: 'May 2026',
    lastCommit: '7 Sep 2026',
    primaryLanguage: 'Python',
    languages: [
      { name: 'Python', pct: 99.9 },
      { name: 'Dockerfile', pct: 0.1 },
    ],
    heatmap: heatmap(880226, { ramp: 40, quiet: [], recent: 0.62, base: 0.06 }),
    timeline: [
      { date: 'Feb 2026', label: 'Agent in production', detail: 'Running before the repo was published', kind: 'origin' },
      { date: 'Mar 2026', label: 'Token launch', detail: 'Via Virtuals Protocol on Base', kind: 'release' },
      { date: 'May 2026', label: 'Sibyl-Memory published', detail: 'Repository created 20 May 2026 · MIT', kind: 'build' },
      { date: 'Jul 2026', label: 'Plugin family fills out', detail: 'SDK, CLI, MCP server, Hermes adapter, LangGraph store', kind: 'build' },
      { date: 'Sep 2026', label: 'Active', detail: 'Last push 7 Sep 2026 · 3 contributors', kind: 'current' },
    ],
    topContributors: [
      { user: 'lead maintainer', commits: 361, share: 74, linked: true },
      { user: 'second contributor', commits: 92, share: 19, linked: false },
      { user: 'third contributor', commits: 33, share: 7, linked: false },
    ],
    consistency: [
      { label: 'Active weeks', value: 84, note: 'Consistent since the repo opened' },
      { label: 'Bus factor', value: 34, note: 'Lead writes roughly three quarters of commits' },
      { label: 'Post-launch activity', value: 88, note: 'Repo opened after the token, still accelerating' },
      { label: 'Issue hygiene', value: 91, note: 'Only 3 issues open' },
    ],
  },

  social: {
    handle: 'sibylcap',
    url: 'https://x.com/sibylcap',
    followers: 14_200,
    followersChange7d: 12.4,
    posts30d: 96,
    avgEngagement: 4.1,
    accountCreated: '2026',
    growth: growth(5511, DAYS, 12_600, 14_200, 0.02),
    mentions: spikeSeries(5512, DAYS, 40, 320, 7),
    topAccounts: [
      { handle: 'sibylcap', followers: 14200, kind: 'Official', sentiment: 'neutral' },
      { handle: 'virtuals_io', followers: 268000, kind: 'Ecosystem', sentiment: 'neutral' },
      { handle: 'base', followers: 1240000, kind: 'Ecosystem', sentiment: 'neutral' },
      { handle: 'notthreadguy', followers: 341000, kind: 'Commentary', sentiment: 'neutral' },
    ],
    momentum: [
      { label: 'Mention velocity', value: 71, delta: 28 },
      { label: 'Unique authors', value: 54, delta: 11 },
      { label: 'Reply depth', value: 62, delta: 4 },
      { label: 'Sentiment', value: 68, delta: 14 },
    ],
    authenticity: {
      overall: 74,
      verdict: 'Strong',
      axes: [
        { label: 'Account age', value: 62, note: 'Roughly the same age as the token' },
        { label: 'Posting consistency', value: 88, note: '96 posts in 30 days, no gaps' },
        { label: 'Original content', value: 84, note: 'Build-in-public rather than reposting' },
        { label: 'Engagement consistency', value: 69, note: 'Steady, small numbers' },
        { label: 'Follower behaviour', value: 64, note: 'Sample axis — needs follower-level data' },
        { label: 'Posting pattern', value: 76, note: 'Human-consistent hours' },
      ],
      notes: [
        { text: 'Posting cadence is high and consistent for a team of three.', signal: 'positive' },
        { text: 'The account is about as old as the token, so age carries little signal here.', signal: 'neutral' },
        { text: 'Audience overlaps heavily with the Virtuals ecosystem.', signal: 'neutral' },
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
        display: '58.7%',
        dial: 8,
        caption: 'top three addresses hold 41.7%',
        tone: 'bad',
        sourced: true,
      },
      {
        id: 'insiders',
        label: 'Insiders',
        display: 'Elevated',
        dial: 28,
        caption: 'two unlabelled contracts hold 31.7%',
        tone: 'bad',
        sourced: false,
      },
      {
        id: 'dev',
        label: 'Dev holding',
        display: 'Unknown',
        dial: 50,
        caption: 'no creator address exposed — factory deploy',
        tone: 'warn',
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
        display: 'Locked',
        dial: 68,
        caption: 'Virtuals launch terms · not independently verified',
        tone: 'warn',
        sourced: false,
      },
      {
        id: 'dexpaid',
        label: 'Dex paid',
        display: 'Yes · 18 boosts',
        dial: 100,
        caption: 'profile 19 Mar 2026 · latest boost today',
        tone: 'good',
        sourced: true,
      },
      {
        id: 'smart',
        label: 'Smart traders',
        display: 'Thin',
        dial: 34,
        caption: '389 transactions across 24 hours',
        tone: 'bad',
        sourced: false,
      },
    ],
    distribution: [
      { label: '< $100', pct: 52.1, wallets: 1_645, signal: 'positive' },
      { label: '$100 – $1K', pct: 30.4, wallets: 960, signal: 'positive' },
      { label: '$1K – $10K', pct: 13.8, wallets: 436, signal: 'neutral' },
      { label: '$10K – $50K', pct: 3.1, wallets: 98, signal: 'neutral' },
      { label: '> $50K', pct: 0.6, wallets: 18, signal: 'neutral' },
    ],
    holderGrowth: growth(6601, ['Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep'], 210, 3_157, 0.04),
    buySell: flow(6602, 9, 221, 168),
    concentration: {
      top10: 58.74,
      top50: 80.49,
      gini: 0.79,
      verdict: 'Heavy · top three hold 41.7%',
      signal: 'negative',
    },
    liquidity: {
      pooled: 200_030,
      lockedPct: 0,
      lockUntil: 'Not disclosed',
      pairs: [
        { dex: 'Uniswap', pair: 'SIBYL / VIRTUAL', liquidity: 199_955, share: 99.96 },
        { dex: 'Equalizer', pair: 'SIBYL / WETH', liquidity: 75, share: 0.04 },
      ],
    },
  },

  /* Ranks 1-10 mirror the real Blockscout ordering; the rest are sample
     wallets that give the field its shape. */
  topHolders: [
    { rank: 1, address: '0x6151AA06…d44d', label: 'Unlabelled contract', pct: 18.9, value: 353700, change: 0, kind: 'cluster', behaviour: 'neutral', held: 'since launch', note: 'Largest holder, an unlabelled contract. Not resolved to an owner.' },
    { rank: 2, address: '0xD6B830F7…cF11', label: 'Unlabelled contract', pct: 12.77, value: 238900, change: 0, kind: 'cluster', behaviour: 'neutral', held: 'since launch', note: 'Second unlabelled contract. Together with rank 1 it holds 31.7%.' },
    { rank: 3, address: '0xbB78E626…Fe7F', label: 'Whale', pct: 10.06, value: 188200, change: -0.8, kind: 'whale', behaviour: 'neutral', held: '5 months', note: 'Largest externally owned account.' },
    { rank: 4, address: '0x43447F02…3243', label: 'Uniswap V2 pair', pct: 7.88, value: 147400, change: 0, kind: 'lp', behaviour: 'neutral', held: 'since Mar 2026', note: 'The SIBYL/VIRTUAL pool. Depth, not a position.' },
    { rank: 5, address: '0x46b6A099…7E6A', label: 'Holder', pct: 2.03, value: 38000, change: 0.4, kind: 'holder', behaviour: 'smart', held: '4 months', note: 'Steady adds, no sells recorded.' },
    { rank: 6, address: '0xAB564b88…2760', label: 'FPair', pct: 1.92, value: 35900, change: 0, kind: 'lp', behaviour: 'neutral', held: 'since Mar 2026', note: 'Virtuals bonding pair contract.' },
    { rank: 7, address: '0x02F67B2e…eDa9', label: 'Unlabelled contract', pct: 1.7, value: 31800, change: 0, kind: 'cluster', behaviour: 'neutral', held: 'since launch', note: 'Unlabelled contract, no outflows observed.' },
    { rank: 8, address: '0xB9c22EEB…00E3', label: 'Holder', pct: 1.38, value: 25800, change: -2.1, kind: 'holder', behaviour: 'seller', held: '2 weeks', note: 'Reduced most of the position after the run.' },
    { rank: 9, address: '0x49DCf8E7…8780', label: 'Holder', pct: 1.09, value: 20400, change: 0, kind: 'holder', behaviour: 'neutral', held: '3 months', note: 'No pattern strong enough to classify.' },
    { rank: 10, address: '0x591Be26c…eBb4', label: 'Unlabelled contract', pct: 1.01, value: 18900, change: 0, kind: 'cluster', behaviour: 'neutral', held: 'since launch', note: 'Unlabelled contract.' },
    { rank: 11, address: '0x6c19d3a0…091d', label: 'Agent treasury · sample', pct: 0.92, value: 17200, change: 0, kind: 'treasury', behaviour: 'smart', held: 'since launch', note: 'Models the agent taking positions, as the docs describe.' },
    { rank: 12, address: '0xa27e01b6…72a1', label: 'Tier holder · sample', pct: 0.81, value: 15200, change: 0.3, kind: 'whale', behaviour: 'smart', held: '5 months', note: 'Staking-tier position, added twice, never sold.' },
    { rank: 13, address: '0x40b719ec…3f0e', label: 'Rotator · sample', pct: 0.74, value: 13800, change: -3.9, kind: 'holder', behaviour: 'seller', held: '9 days', note: 'Entered on the run and exited most of it.' },
    { rank: 14, address: '0xd5813b26…8a41', label: 'Unlabelled · sample', pct: 0.66, value: 12400, change: 0, kind: 'holder', behaviour: 'neutral', held: '3 months', note: 'No pattern strong enough to classify.' },
    { rank: 15, address: '0x7f238c04…19b7', label: 'Accumulator · sample', pct: 0.58, value: 10900, change: 1.1, kind: 'holder', behaviour: 'smart', held: '4 months', note: 'Adds steadily, no sells on record.' },
    { rank: 16, address: '0x0c48d712…5e03', label: 'Unlabelled · sample', pct: 0.51, value: 9500, change: 0.2, kind: 'holder', behaviour: 'neutral', held: '6 weeks', note: 'No pattern strong enough to classify.' },
    { rank: 17, address: '0xbe374a09…c186', label: 'Quick seller · sample', pct: 0.44, value: 8200, change: -7.4, kind: 'holder', behaviour: 'seller', held: '4 days', note: 'Bought and exited within the same week.' },
    { rank: 18, address: '0x52f16d83…a047', label: 'Unlabelled · sample', pct: 0.38, value: 7100, change: 0, kind: 'holder', behaviour: 'neutral', held: '2 months', note: 'No pattern strong enough to classify.' },
    { rank: 19, address: '0x1a90c375…7b28', label: 'Quick seller · sample', pct: 0.32, value: 6000, change: -5.1, kind: 'holder', behaviour: 'seller', held: '6 days', note: 'Short hold, sold into the spike.' },
    { rank: 20, address: '0xc7e40b19…3d64', label: 'Unlabelled · sample', pct: 0.27, value: 5100, change: 0.1, kind: 'holder', behaviour: 'neutral', held: '5 weeks', note: 'No pattern strong enough to classify.' },
    { rank: 21, address: '0x93b02c69…8f15', label: 'Equalizer pool', pct: 0.004, value: 75, change: 0, kind: 'lp', behaviour: 'neutral', held: 'since 2026', note: 'Effectively unusable at $75 of depth.' },
  ],



  /* Built from dated, verifiable events and the published docs index at
     docs.sibylcap.com. Items still only documented are marked planned. */
  roadmap: [
    {
      date: 'Feb 2026',
      label: 'Agent in production',
      detail: 'Running and shipping before any token existed.',
      status: 'done',
      track: 'Product',
    },
    {
      date: '18 Mar 2026',
      label: 'Token launch on Virtuals',
      detail: 'Uniswap SIBYL/VIRTUAL pair created on Base.',
      status: 'done',
      track: 'Ecosystem',
    },
    {
      date: '2026',
      label: 'ERC-8004 identity',
      detail: 'On-chain agent identity registered, agent ID 20880.',
      status: 'done',
      track: 'Infrastructure',
    },
    {
      date: '20 May 2026',
      label: 'Sibyl-Memory open sourced',
      detail: 'File-based long-term memory published under MIT.',
      status: 'done',
      track: 'Product',
    },
    {
      date: '2026',
      label: 'Plugin family shipped',
      detail: 'SDK, CLI, MCP server, Hermes adapter and a LangGraph BaseStore.',
      status: 'done',
      track: 'Product',
    },
    {
      date: '2026',
      label: 'Benchmark published',
      detail: 'LongMemEval Oracle result stated at 95.6%.',
      status: 'done',
      track: 'Product',
    },
    {
      date: '7 Sep 2026',
      label: 'Latest push',
      detail: 'Repository active within the last week.',
      status: 'done',
      track: 'Product',
    },
    {
      date: 'Q3 2026',
      label: 'Staking tiers',
      detail: 'Four-tier staking documented; contract-level verification pending.',
      status: 'active',
      track: 'Token',
    },
    {
      date: 'Q3 2026',
      label: 'x402 payment rail',
      detail: 'Documented in the infrastructure section, live status unverified.',
      status: 'active',
      track: 'Infrastructure',
    },
    {
      date: 'Q4 2026',
      label: 'Vesting schedule',
      detail: 'Documented but no vesting contract address published.',
      status: 'planned',
      track: 'Token',
    },
    {
      date: 'Q4 2026',
      label: 'Talos engine',
      detail: 'Trading engine documented, no public release located.',
      status: 'planned',
      track: 'Product',
    },
    {
      date: '2027',
      label: 'Revenue share',
      detail: 'Described in the token docs, not yet observable on-chain.',
      status: 'planned',
      track: 'Token',
    },
  ],
  narrative: {
    nodes: [
      { id: 'core', label: 'Agent Infrastructure', strength: 100, phase: 'Expanding', x: 100, y: 65, relation: 'Primary' },
      { id: 'agents', label: 'AI Agents', strength: 78, phase: 'Cooling', x: 34, y: 26, relation: 'Parent narrative' },
      { id: 'memory', label: 'Agent Memory', strength: 72, phase: 'Emerging', x: 166, y: 28, relation: 'Core competence' },
      { id: 'virtuals', label: 'Virtuals Ecosystem', strength: 66, phase: 'Cooling', x: 176, y: 94, relation: 'Launch platform' },
      { id: 'base', label: 'Base Ecosystem', strength: 74, phase: 'Expanding', x: 100, y: 118, relation: 'Deployment chain' },
      { id: 'x402', label: 'Agent Payments', strength: 61, phase: 'Emerging', x: 24, y: 96, relation: 'Implements' },
      { id: 'identity', label: 'On-chain Identity', strength: 48, phase: 'Emerging', x: 62, y: 8, relation: 'ERC-8004' },
      { id: 'aitokens', label: 'AI Tokens', strength: 40, phase: 'Cooling', x: 150, y: 118, relation: 'Loose association' },
    ],
    edges: [
      ['core', 'agents'],
      ['core', 'memory'],
      ['core', 'virtuals'],
      ['core', 'base'],
      ['core', 'x402'],
      ['agents', 'identity'],
      ['agents', 'aitokens'],
      ['virtuals', 'aitokens'],
    ],
    reading: [
      { label: 'Narrative relevance', value: 69, note: 'Infrastructure angle holds up better than the agent-token wrapper.' },
      { label: 'Category crowding', value: 74, note: 'Agent tokens on Virtuals are numerous.' },
      { label: 'Differentiation', value: 79, note: 'File-based memory with no vector store is a distinct technical position.' },
    ],
  },



  risks: [
    { id: 's-r1', label: 'Absolute Liquidity', level: 'high', score: 68, summary: 'Only $200K of depth. A $20K order moves price about 10%.' },
    { id: 's-r2', label: 'Key-Person Concentration', level: 'medium', score: 61, summary: 'Three contributors, with the lead writing roughly 74% of commits.' },
    { id: 's-r3', label: 'Quote Asset Risk', level: 'medium', score: 54, summary: 'Priced against VIRTUAL rather than ETH or a stablecoin.' },
    { id: 's-r4', label: 'Activity Depth', level: 'medium', score: 57, summary: '389 transactions in 24 hours is thin, even for this cap.' },
    { id: 's-r5', label: 'Unverified Claims', level: 'medium', score: 44, summary: 'Production date and benchmark are stated by the project, not independently confirmed.' },
    { id: 's-r6', label: 'Developer Risk', level: 'low', score: 26, summary: 'Named entity, open licence, current commits, no prior failures on record.' },
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
