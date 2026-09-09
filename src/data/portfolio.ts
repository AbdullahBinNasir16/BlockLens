import type { GateCandidate, RuleChange, Trade } from './types';
import { seeded } from './synth';
import { CORPUS_NOW } from './wallets';

/* ============================================================
   The model's book.

   BlockLens runs a model that buys new launches when they clear its gate,
   sizes them by how far inside the gate they sit, and writes down why.
   This file is that record — simulated for the prototype.

   Stored here: what the model did (entry, exit, size, scores, reasons).
   Not stored: returns, win rate, equity. Those are computed from the
   trades in `lib/portfolio.ts`, so the headline number cannot disagree
   with the rows underneath it.

   Lore that names real people and companies is illustrative — written to
   show how the model argues, not reported as events. The page says so.
   ============================================================ */

/** The book's clock is the corpus clock, so every page in the product
 *  agrees on what "now" is. */
export const BOOK_NOW = CORPUS_NOW;
export const INCEPTION = Date.UTC(2026, 0, 5);
export const START_CAPITAL = 100_000;

const at = (y: number, m: number, d: number, h = 12) => Date.UTC(y, m - 1, d, h);

/** The gate as it stands today. The rule log records how it got here. */
export const GATE = {
  maxAgeHours: 48,
  minConfidence: 65,
  maxRisk: 55,
  maxRiskMeme: 50,
  minLiquidity: 40_000,
  minLore: 60,
};

export const RISK_TIGHTENED_AT = at(2026, 6, 13);

export const RULE_LOG: RuleChange[] = [
  {
    at: INCEPTION,
    text: 'Model goes live. It buys launches under 48 hours old with confidence ≥ 65, risk ≤ 55 and at least $40K of liquidity; memecoins must also score ≥ 60 on lore. Size runs from 2.5% at the edge of the gate to 6% deep inside it.',
  },
  {
    at: RISK_TIGHTENED_AT,
    text: 'Risk ceiling for memecoins lowered from 55 to 50, after OPTIMUS — a funding cluster the risk score had priced at 54.',
  },
];

const WETH = { ticker: 'WETH', name: 'Wrapped Ether', kind: 'crypto' } as const;
const USDC = { ticker: 'USDC', name: 'USD Coin', kind: 'stable' } as const;
const SOL = { ticker: 'SOL', name: 'Solana', kind: 'crypto' } as const;

export const TRADES: Trade[] = [
  {
    id: 't-chips',
    kind: 'meme',
    ticker: 'CHIPS',
    name: 'Chips',
    chain: 'solana',
    quote: { ticker: 'INTC', name: 'Intel, tokenized', kind: 'stock' },
    launchedAt: at(2026, 1, 14, 15),
    entryAt: at(2026, 1, 14, 18),
    exitAt: at(2026, 1, 19, 10),
    entryPrice: 0.000842,
    lastPrice: 0.000404,
    peak: 1.31,
    size: 3000,
    gate: { confidence: 69, risk: 51, liquidity: 58_000, ageHours: 3, lore: 64 },
    thesis: [
      'Cleared the gate on its story more than its structure — confidence 69 and risk 51, both inside the rule, neither by much.',
      'Stock-paired launches earn extra weight when the pair explains itself in one read, because screenshots do the marketing. CHIPS against Intel does.',
      'Sized at 3% because policy lore waits on the next headline, and none was scheduled.',
    ],
    lore: {
      hook: 'The only chip stock with a government on the cap table.',
      origin:
        'Washington took an equity stake in Intel in 2025, and “CHIPS” has been the name of the policy ever since. A CHIPS token launched quoted in tokenized Intel — industrial policy, turned into a trading pair.',
      pairing:
        'CHIPS priced in INTC puts the act and the company it was written to rescue on one chart. Every Intel headline becomes this token’s headline.',
      legs: 'Policy lore is slow lore: it needs a news cycle to move, and news cycles are not on a schedule. The model knew that at entry and sized for it.',
    },
    exitNote:
      'Liquidity halved on day four with no new headline to refill it. Sold at −52% before the pool thinned further.',
  },
  {
    id: 't-orrery',
    kind: 'infra',
    ticker: 'ORRERY',
    name: 'Orrery',
    chain: 'ethereum',
    quote: WETH,
    launchedAt: at(2026, 1, 16, 9),
    entryAt: at(2026, 1, 16, 17),
    exitAt: at(2026, 2, 20, 14),
    entryPrice: 0.412,
    lastPrice: 0.338,
    peak: 1.22,
    size: 5000,
    gate: { confidence: 74, risk: 36, liquidity: 410_000, ageHours: 8 },
    thesis: [
      'A shared-sequencer marketplace for rollups, launched with three rollups already routing through it — usage before the token, which is what the model looks for in infrastructure.',
      'The cleanest structure of January: risk 36, $410K of liquidity at eight hours, vesting published and enforced on-chain.',
      'Sized at 5% and bought to hold through a quarter. Infrastructure rarely moves in weeks.',
    ],
    exitNote:
      'Two of the three launch rollups moved to a competitor within a month. The usage the thesis rested on shrank, and the position went with it at −18%.',
  },
  {
    id: 't-carto',
    kind: 'defi',
    ticker: 'CARTO',
    name: 'Cartograph',
    chain: 'base',
    quote: USDC,
    launchedAt: at(2026, 1, 21, 13),
    entryAt: at(2026, 1, 21, 19),
    exitAt: at(2026, 2, 27, 11),
    entryPrice: 0.0891,
    lastPrice: 0.1167,
    peak: 1.58,
    size: 5000,
    gate: { confidence: 70, risk: 43, liquidity: 236_000, ageHours: 6 },
    thesis: [
      'Perpetuals on Base with fees switched on from the first block — revenue on day one, which removes the usual “when fee switch” overhang.',
      'Confidence 70, risk 43. The audit was public and matched the deployed bytecode, which the model checks rather than assumes.',
      'Quoted in USDC, so the chart is the token alone — no quote-asset beta to untangle.',
    ],
    exitNote:
      'Sold at 1.31× after a 1.58× peak. Fees plateaued in week five, and a perps token without growing fees is a governance token.',
  },
  {
    id: 't-ai',
    kind: 'meme',
    ticker: 'AI',
    name: 'AI',
    chain: 'solana',
    quote: { ticker: 'NVDA', name: 'Nvidia, tokenized', kind: 'stock' },
    launchedAt: at(2026, 1, 27, 14),
    entryAt: at(2026, 1, 27, 16),
    exitAt: at(2026, 2, 26, 21),
    entryPrice: 0.00237,
    lastPrice: 0.006778,
    peak: 3.4,
    size: 4500,
    gate: { confidence: 78, risk: 38, liquidity: 142_000, ageHours: 2, lore: 88 },
    thesis: [
      'The highest lore score the gate had seen at the time — 88 — with clean structure behind it: $142K of liquidity two hours in and no bundled supply above 4%.',
      'For a stock-paired launch the model asks one question first: does the pair read as a sentence? AI against Nvidia needs no explaining to anyone who has ever opened a brokerage app.',
      'Held through the earnings run-up on purpose. The exit was set on the print, not on a price.',
    ],
    lore: {
      hook: 'The most literal pair on-chain.',
      origin:
        'A token called AI, launched into a pool quoted in tokenized Nvidia instead of SOL. No mascot, no website — the pair is the entire pitch.',
      pairing:
        'AI priced in NVDA is the idea quoted in the company that sells the shovels for it. The token and its quote asset tell one story from two ends.',
      legs: 'It borrows a calendar. Nvidia reports on a schedule, so the lore refreshes itself every quarter without anyone having to post.',
    },
    exitNote:
      'Sold on Nvidia’s earnings day, as planned — the catalyst it was bought for had arrived. It peaked at 3.4×; the exit was 2.86×.',
  },
  {
    id: 't-pepper',
    kind: 'meme',
    ticker: 'PEPPER',
    name: 'Pepper',
    chain: 'solana',
    quote: { ticker: 'HOOD', name: 'Robinhood, tokenized', kind: 'stock' },
    launchedAt: at(2026, 2, 11, 17),
    entryAt: at(2026, 2, 11, 18),
    exitAt: at(2026, 2, 14, 18),
    entryPrice: 0.000118,
    lastPrice: 0.000434,
    peak: 4.9,
    size: 2500,
    gate: { confidence: 72, risk: 47, liquidity: 74_000, ageHours: 1, lore: 91 },
    thesis: [
      'The fastest entry in the book — one hour after launch — because celebrity-pet tokens decide their fate on the first day.',
      'Lore 91: a named public figure, a named dog, and a quote asset that ties the two together. Structure was acceptable rather than good: risk 47, liquidity $74K.',
      'Bought with a 72-hour clock. Pet lore does not compound; it spikes, and the model sells the spike.',
    ],
    lore: {
      hook: 'A billionaire said his dog’s name out loud.',
      origin:
        'Vlad Tenev introduced his dog, Pepper, on a Robinhood livestream. A PEPPER token existed eleven minutes later.',
      pairing:
        'PEPPER priced in HOOD is the dog quoted in its owner’s company, traded against Robinhood’s own tokenized stock. The pair makes the joke before anyone has to.',
      legs: 'Celebrity-pet lore burns hot and short. The model gave it 72 hours by rule and sized it at 2.5% to match.',
    },
    exitNote:
      'Sold on the 72-hour clock at 3.68×, below the 4.9× peak. The rule was time, not price — and the rule held.',
  },
  {
    id: 't-hearth',
    kind: 'ai',
    ticker: 'HEARTH',
    name: 'Hearth',
    chain: 'base',
    quote: WETH,
    launchedAt: at(2026, 2, 24, 10),
    entryAt: at(2026, 2, 24, 14),
    exitAt: at(2026, 3, 24, 16),
    entryPrice: 0.0164,
    lastPrice: 0.03477,
    peak: 2.61,
    size: 4000,
    gate: { confidence: 75, risk: 40, liquidity: 188_000, ageHours: 4 },
    thesis: [
      'Agent-to-agent payments on Base, launched with a public ledger of agents already settling through it — 1,400 on the first day.',
      'Confidence 75 on product evidence; risk 40 with the team allocation locked in a contract the model could read, not a promise it had to take on trust.',
      'AI-agent launches are bought when the agents are visibly working at launch. Hearth’s were paying each other before the token listed.',
    ],
    exitNote:
      'Sold at 2.12× when the number of agents settling each day fell for eight days straight — the usage that justified the entry had turned.',
  },
  {
    id: 't-send',
    kind: 'meme',
    ticker: 'SEND',
    name: 'Send',
    chain: 'solana',
    quote: { ticker: 'AMZN', name: 'Amazon, tokenized', kind: 'stock' },
    launchedAt: at(2026, 3, 3, 13),
    entryAt: at(2026, 3, 3, 15),
    exitAt: at(2026, 4, 2, 20),
    entryPrice: 0.000356,
    lastPrice: 0.001823,
    peak: 6.2,
    size: 3500,
    gate: { confidence: 76, risk: 41, liquidity: 118_000, ageHours: 2, lore: 90 },
    thesis: [
      'Lore 90 with structure to match: $118K of liquidity at two hours, a renounced mint, no wallet above 3%.',
      'The model’s test for stock-paired launches is whether the base ticker and the quote company form a phrase a stranger understands at a glance. SEND against Amazon is the cleanest pass the gate has recorded.',
      'Sized at 3.5% and allowed to run. Pair lore outlasts event lore, because the joke never expires.',
    ],
    lore: {
      hook: 'The pair is a sentence: send it, Amazon.',
      origin:
        'SEND launched into a pool quoted in tokenized Amazon rather than SOL. Nothing else about the token mattered — the ticker and its quote asset read as an instruction.',
      pairing:
        'Amazon’s whole business is the verb in this ticker: it sends more parcels in a day than most chains settle transactions. Quote SEND in AMZN and every chart is a delivery joke that needs no caption.',
      legs: 'It spreads by screenshot. A pair that reads as a sentence gets reposted by people who never buy it, and that is free distribution.',
    },
    exitNote:
      'Scaled out between 4× and 6×; the final tranche went at 5.12× when volume fell below a third of its peak week.',
  },
  {
    id: 't-sibyl',
    kind: 'ai',
    ticker: 'SIBYL',
    name: 'Sibyl',
    chain: 'base',
    quote: WETH,
    launchedAt: at(2026, 3, 18, 12),
    entryAt: at(2026, 3, 18, 18),
    exitAt: at(2026, 4, 9, 15),
    entryPrice: 0.00162,
    lastPrice: 0.002657,
    peak: 1.97,
    size: 5000,
    gate: { confidence: 71, risk: 52, liquidity: 96_000, ageHours: 6 },
    projectId: 'sibyl',
    thesis: [
      'An autonomous capital-allocation agent on Base with a working product at launch rather than a roadmap. BlockLens scores it 71 confidence and 52 risk — inside the gate, with the risk carried by holder concentration rather than the contract.',
      'The model buys AI-agent launches when the agent does something visible on day one. Sibyl’s treasury was acting on-chain from its first block.',
      'Sized mid-book: strong product evidence, young holder base.',
    ],
    exitNote:
      'Took profit at 1.64× when the top-ten holders’ share crept back toward where it stood at entry — concentration was the risk it had been bought in spite of.',
  },
  {
    id: 't-stratum',
    kind: 'defi',
    ticker: 'STRATUM',
    name: 'Stratum',
    chain: 'ethereum',
    quote: WETH,
    launchedAt: at(2026, 3, 30, 8),
    entryAt: at(2026, 3, 30, 20),
    exitAt: at(2026, 5, 12, 13),
    entryPrice: 1.284,
    lastPrice: 1.438,
    peak: 1.29,
    size: 6000,
    gate: { confidence: 77, risk: 33, liquidity: 1_240_000, ageHours: 12 },
    thesis: [
      'Restaking vaults with a published slashing model — the rare launch that says exactly how depositors lose money, and prices it.',
      'The lowest-risk entry in the book at 33, with $1.24M of liquidity. The largest size, 6%, followed from that.',
      'Bought for carry rather than a re-rating: the vault’s yield was the thesis, and the token a claim on its fees.',
    ],
    exitNote:
      'Sold at 1.12× when a larger competitor launched with double the incentive budget. The thesis was yield, and the yield had just been outbid.',
  },
  {
    id: 't-au',
    kind: 'meme',
    ticker: 'AU',
    name: 'Au',
    chain: 'solana',
    quote: { ticker: 'TSM', name: 'TSMC, tokenized', kind: 'stock' },
    launchedAt: at(2026, 4, 15, 12),
    entryAt: at(2026, 4, 15, 16),
    exitAt: at(2026, 4, 29, 14),
    entryPrice: 0.00521,
    lastPrice: 0.00323,
    peak: 1.44,
    size: 3000,
    gate: { confidence: 67, risk: 49, liquidity: 66_000, ageHours: 4, lore: 72 },
    thesis: [
      'Inside the gate on every score, but only narrowly on lore — 72 against a floor of 60 — which is why it was sized at 3%.',
      'The idea is good: AU, gold’s symbol on the periodic table, quoted in the company whose fabs are the scarcest capacity on earth.',
      'The concern at entry, written down at the time: a pair that needs two facts to decode travels slower than one that needs none.',
    ],
    lore: {
      hook: 'Gold, measured in wafers.',
      origin:
        'AU — the chemical symbol for gold — launched into a pool quoted in tokenized TSMC, at a moment when the scarce thing everyone argued about was leading-edge chip capacity, not bullion.',
      pairing:
        'AU priced in TSM is the old store of value quoted in the new one. The joke is that the fab is the vault now.',
      legs: 'Clever, but it asks the reader to know two things: the symbol for gold, and what TSMC makes. The model marked the lore down for that before it bought.',
    },
    exitNote:
      'Cut at −38%. The pair needed explaining, and lore that needs explaining does not travel — the risk the model had written into its own entry.',
  },
  {
    id: 't-quire',
    kind: 'ai',
    ticker: 'QUIRE',
    name: 'Quire',
    chain: 'solana',
    quote: SOL,
    launchedAt: at(2026, 4, 22, 9),
    entryAt: at(2026, 4, 22, 15),
    exitAt: at(2026, 5, 1, 12),
    entryPrice: 0.0472,
    lastPrice: 0.0349,
    peak: 1.18,
    size: 4000,
    gate: { confidence: 66, risk: 53, liquidity: 83_000, ageHours: 6 },
    thesis: [
      'A shared memory layer for AI agents: agents write down what they learn, and other agents pay to read it. Live integrations with two agent frameworks at launch.',
      'Borderline on both scores, 66 and 53. Bought on the integrations, which were live and could be checked.',
      'Sized at 4%, because a borderline entry gets a smaller share of the book by rule.',
    ],
    exitNote:
      'One of the two framework integrations was quietly removed from its repository in week one. The evidence the entry leaned on was gone, so the position went at −26%.',
  },
  {
    id: 't-laser',
    kind: 'meme',
    ticker: 'LASER',
    name: 'Laser',
    chain: 'solana',
    quote: { ticker: 'MSTR', name: 'Strategy, tokenized', kind: 'stock' },
    launchedAt: at(2026, 5, 6, 13),
    entryAt: at(2026, 5, 6, 15),
    exitAt: at(2026, 5, 21, 18),
    entryPrice: 0.00188,
    lastPrice: 0.003647,
    peak: 2.35,
    size: 3000,
    gate: { confidence: 70, risk: 44, liquidity: 88_000, ageHours: 2, lore: 79 },
    thesis: [
      'Lore 79 and a structure the model trusts: renounced mint, no wallet above 3%, $88K of liquidity at two hours.',
      'The trade was borrowed beta. MSTR moves like leveraged bitcoin, so quoting a memecoin in it hands the token a macro trend it could never generate alone.',
      'Bought into a green bitcoin week; the exit was tied to the week turning.',
    ],
    lore: {
      hook: 'Laser eyes, priced in the company that became a bitcoin treasury.',
      origin:
        'Laser eyes were the bitcoin maximalist’s profile picture. Strategy is the listed company that turned its balance sheet into bitcoin. LASER, quoted in tokenized MSTR, joins the meme to its most literal corporate form.',
      pairing:
        'Every MSTR move is a bitcoin move with leverage attached, so the pair gives a memecoin a macro beta it would never have on its own.',
      legs: 'Bitcoin culture is the oldest lore in crypto. It doesn’t need a new story to keep going — only a green week.',
    },
    exitNote:
      'Sold at 1.94× when bitcoin’s week turned red. The thesis was borrowed beta, and the borrowing had stopped paying.',
  },
  {
    id: 't-dot',
    kind: 'infra',
    ticker: 'DOT',
    name: 'Dot',
    chain: 'base',
    quote: WETH,
    launchedAt: at(2026, 5, 27, 11),
    entryAt: at(2026, 5, 27, 16),
    exitAt: null,
    entryPrice: 0.00394,
    /* the sourced price on Dot's research page, so the mark here agrees
       with it */
    lastPrice: 0.005437,
    peak: 1.71,
    size: 4500,
    gate: { confidence: 68, risk: 46, liquidity: 81_000, ageHours: 5 },
    projectId: 'dot',
    thesis: [
      'Private AI inference and tooling on Base, launched with a live product and documentation that matched it. BlockLens scores it 68 confidence and 46 risk — inside the gate on both.',
      'The model buys infrastructure when the product exists before the token does. Dot’s did.',
      'Held rather than traded: infrastructure re-rates on usage, which takes quarters, not days.',
    ],
    exitNote:
      'Watching the repository. Dot’s research page already flags an eight-week gap in public commits; a second gap like it is the exit.',
  },
  {
    id: 't-vesper',
    kind: 'infra',
    ticker: 'VESPER',
    name: 'Vesper',
    chain: 'base',
    quote: WETH,
    launchedAt: at(2026, 6, 3, 10),
    entryAt: at(2026, 6, 3, 19),
    exitAt: at(2026, 7, 16, 15),
    entryPrice: 0.221,
    lastPrice: 0.3249,
    peak: 1.66,
    size: 5000,
    gate: { confidence: 73, risk: 39, liquidity: 322_000, ageHours: 9 },
    thesis: [
      'Proof-of-location oracles for Base — hardware in the field, reporting on-chain, with 2,000 devices live at launch.',
      'Confidence 73, risk 39. The device count could be checked on-chain, which the model prefers to any partnership announcement.',
      'Bought to hold for a quarter: oracles are paid per query, and queries take time to arrive.',
    ],
    exitNote:
      'Sold at 1.47× after queries grew six weeks running and the price got ahead of them. The model trims when price outruns the usage it was bought on.',
  },
  {
    id: 't-optimus',
    kind: 'meme',
    ticker: 'OPTIMUS',
    name: 'Optimus',
    chain: 'solana',
    quote: { ticker: 'TSLA', name: 'Tesla, tokenized', kind: 'stock' },
    launchedAt: at(2026, 6, 10, 16),
    entryAt: at(2026, 6, 10, 19),
    exitAt: at(2026, 6, 13, 9),
    entryPrice: 0.000731,
    lastPrice: 0.000212,
    peak: 1.52,
    size: 2500,
    gate: { confidence: 66, risk: 54, liquidity: 52_000, ageHours: 3, lore: 70 },
    thesis: [
      'Inside the gate on every measure, at the edge of two: risk 54 against a ceiling of 55, liquidity $52K against a floor of $40K.',
      'The lore was clean — the robot quoted in the company that builds it, launched on a humanoid-robot demo day.',
      'Sized at the minimum, 2.5%, because an entry at the edge of the rule gets the smallest share of the book.',
    ],
    lore: {
      hook: 'The robot, priced in the company that builds it.',
      origin:
        'OPTIMUS launched into a pool quoted in tokenized Tesla on the day of a humanoid-robot demo. Robot lore and Tesla lore, in one pair.',
      pairing:
        'OPTIMUS priced in TSLA gives a demo-day memecoin the most-watched retail stock as its quote asset — every Tesla headline becomes its headline.',
      legs: 'Demo-day lore has a half-life of one news cycle. The model gave it a week.',
    },
    exitNote:
      'Stopped out at −71% after three wallets funded from one source sold together — a cluster the risk score had priced at 54. The loss changed the rule: the memecoin risk ceiling is now 50.',
  },
  {
    id: 't-sextant',
    kind: 'ai',
    ticker: 'SEXTANT',
    name: 'Sextant',
    chain: 'base',
    quote: WETH,
    launchedAt: at(2026, 6, 26, 12),
    entryAt: at(2026, 6, 26, 17),
    exitAt: at(2026, 7, 6, 10),
    entryPrice: 0.0913,
    lastPrice: 0.0603,
    peak: 1.21,
    size: 4000,
    gate: { confidence: 69, risk: 45, liquidity: 104_000, ageHours: 5 },
    thesis: [
      'A research agent that files on-chain reports on new launches — the same job BlockLens does, which the model treated as a reason for care rather than enthusiasm.',
      'Confidence 69, risk 45. The agent’s reports were public and could be checked against what happened next.',
      'Bought small, as a test of whether the market pays for machine research.',
    ],
    exitNote:
      'Checked against outcomes, its reports were right less than half the time by week two. The product was the thesis, and the product was wrong more often than not: sold at −34%.',
  },
  {
    id: 't-zcat',
    kind: 'meme',
    ticker: 'ZCAT',
    name: 'ZCat',
    chain: 'solana',
    quote: { ticker: 'ZEC', name: 'Zcash, wrapped', kind: 'crypto' },
    launchedAt: at(2026, 7, 8, 14),
    entryAt: at(2026, 7, 8, 16),
    exitAt: null,
    entryPrice: 0.00241,
    lastPrice: 0.003952,
    peak: 2.08,
    size: 3000,
    gate: { confidence: 73, risk: 42, liquidity: 97_000, ageHours: 2, lore: 83 },
    thesis: [
      'Lore 83 under the tightened memecoin rule — risk 42 against the new ceiling of 50.',
      'The model reads ZCAT as a proxy for Zcash itself: a mascot trade that only works while the coin underneath is a live trade.',
      'Quoted in ZEC rather than SOL, so the position carries Zcash’s direction by construction — a deliberate choice, not an accident of the pool.',
    ],
    lore: {
      hook: 'The privacy trade got a mascot you can’t see.',
      origin:
        'Zcash spent 2025 turning from a relic back into a trade. ZCAT launched as its cat — quoted in ZEC itself rather than in SOL or a stablecoin.',
      pairing:
        'ZCAT priced in ZEC is a mascot that only makes sense to people already holding the coin — which is exactly who buys a mascot.',
      legs: 'Communities adopt mascots when they are winning and want something to post. While ZEC is a live trade, ZCAT has an audience.',
    },
    exitNote:
      'Watching ZEC, not ZCAT. The lore is a proxy for Zcash’s run, so a ZEC reversal is the exit, whatever the cat is doing.',
  },
  {
    id: 't-ring',
    kind: 'meme',
    ticker: 'RING',
    name: 'Ring',
    chain: 'solana',
    quote: { ticker: 'PLTR', name: 'Palantir, tokenized', kind: 'stock' },
    launchedAt: at(2026, 7, 22, 13),
    entryAt: at(2026, 7, 22, 16),
    exitAt: at(2026, 8, 12, 17),
    entryPrice: 0.00098,
    lastPrice: 0.002509,
    peak: 3.1,
    size: 3000,
    gate: { confidence: 71, risk: 45, liquidity: 91_000, ageHours: 3, lore: 86 },
    thesis: [
      'Lore 86 and risk 45 — comfortably inside the tightened rule.',
      'The pair is a Tolkien joke with a listed company on the other side of it. Lore that rewards the people who get it is lore that those people buy.',
      'Held for three weeks, through Palantir’s earnings.',
    ],
    lore: {
      hook: 'One ring, priced in the seeing stone.',
      origin:
        'Palantir is named after the seeing-stones of The Lord of the Rings, and the industry around it has kept naming companies from Tolkien ever since — Anduril, Mithril, Valar. RING launched quoted in tokenized Palantir.',
      pairing:
        'RING priced in PLTR sets the One Ring beside the palantír — two artefacts of power from the same book, one of them a listed company.',
      legs: 'Tolkien lore is evergreen, and the industry renews it for free every time it names something.',
    },
    exitNote: 'Sold at 2.56× the week after Palantir reported — the catalyst it was held for had passed.',
  },
  {
    id: 't-keel',
    kind: 'defi',
    ticker: 'KEEL',
    name: 'Keel',
    chain: 'base',
    quote: USDC,
    launchedAt: at(2026, 7, 29, 10),
    entryAt: at(2026, 7, 29, 21),
    exitAt: null,
    entryPrice: 0.742,
    lastPrice: 0.8088,
    peak: 1.18,
    size: 5000,
    gate: { confidence: 76, risk: 35, liquidity: 860_000, ageHours: 11 },
    thesis: [
      'A stable-yield vault on Base that publishes where every dollar sits, every day. Risk 35 — the second-lowest in the book.',
      'Bought for the fee stream: the token takes a share of vault performance, and deposits were growing before launch.',
      'Held as ballast. Not every position in a new-launch book has to be a lottery ticket.',
    ],
    exitNote: 'Watching deposits. The token is a claim on vault fees, so two straight weeks of net outflows is the exit.',
  },
  {
    id: 't-bobo',
    kind: 'meme',
    ticker: 'BOBO',
    name: 'Bobo',
    chain: 'solana',
    quote: SOL,
    launchedAt: at(2026, 8, 4, 21),
    entryAt: at(2026, 8, 4, 22),
    exitAt: at(2026, 8, 9, 14),
    entryPrice: 0.000612,
    lastPrice: 0.000337,
    peak: 1.36,
    size: 2000,
    gate: { confidence: 66, risk: 48, liquidity: 61_000, ageHours: 1, lore: 67 },
    thesis: [
      'A contrarian entry, and written down as one: the only memecoin in the book bought because the market was falling.',
      'Lore 67, risk 48 — inside the tightened rule, at the minimum size.',
      'The bet was that a bad week would keep going and the bear would become its mascot.',
    ],
    lore: {
      hook: 'The bear, launched on the red day.',
      origin:
        'Bobo — crypto’s old bear-market mascot — relaunched the evening bitcoin printed its worst daily candle of the quarter.',
      legs: 'Contrarian lore needs the market to stay bad. It lasts exactly as long as the drawdown does.',
    },
    exitNote:
      'The market bounced two days later, and a bear mascot in a green week has nothing to say. Sold at −45%.',
  },
  {
    id: 't-cairn',
    kind: 'ai',
    ticker: 'CAIRN',
    name: 'Cairn',
    chain: 'solana',
    quote: SOL,
    launchedAt: at(2026, 8, 19, 11),
    entryAt: at(2026, 8, 19, 17),
    exitAt: null,
    entryPrice: 0.0385,
    lastPrice: 0.03504,
    peak: 1.26,
    size: 4000,
    gate: { confidence: 72, risk: 44, liquidity: 152_000, ageHours: 6 },
    thesis: [
      'Verifiable compute for agents on Solana — every inference ships with a proof a contract can check, and the proofs were live at launch.',
      'Confidence 72, risk 44. The team’s previous project is still running, which the model counts as evidence.',
      'Down 9% three weeks in — inside what the model expects of infrastructure that has not yet been priced on usage.',
    ],
    exitNote:
      'Watching proof volume. If proofs verified per day have not doubled by week eight, the thesis has not happened and the position goes.',
  },
];

/* ---------------- every launch the model scored ----------------
   Generated, deterministic. The bought trades are not in this list —
   they are drawn from TRADES at their real gate scores. */

function gauss(r: () => number) {
  const u = Math.max(1e-9, r());
  return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * r());
}

const clamp = (v: number) => Math.max(2, Math.min(98, Math.round(v)));

function buildCandidates(): GateCandidate[] {
  const r = seeded(51_207);
  const out: GateCandidate[] = [];
  for (let i = 0; i < 1085; i++) {
    const confidence = clamp(48 + 14 * gauss(r));
    /* weaker launches tend to be riskier, but not always */
    const risk = clamp(62 - 0.45 * (confidence - 48) + 13 * gauss(r));
    const inCorner = confidence >= GATE.minConfidence && risk <= GATE.maxRisk;
    let passedOver: GateCandidate['passedOver'];
    if (inCorner) {
      const x = r();
      passedOver = x < 0.45 ? 'liquidity' : x < 0.7 ? 'lore' : x < 0.9 ? 'age' : 'capacity';
    }
    out.push({ confidence, risk, passedOver });
  }
  return out;
}

export const CANDIDATES: GateCandidate[] = buildCandidates();

export const PORTFOLIO_NOTE =
  'The model and its book are simulated for this prototype. Trades, prices and returns are illustrative, and lore that names real people and companies is written to show how the model argues — not a report of events.';
