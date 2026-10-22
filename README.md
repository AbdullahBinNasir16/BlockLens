# BlockLens

[![CI](https://github.com/AbdullahBinNasir16/BlockLens/actions/workflows/ci.yml/badge.svg)](https://github.com/AbdullahBinNasir16/BlockLens/actions/workflows/ci.yml) [![CD](https://github.com/AbdullahBinNasir16/BlockLens/actions/workflows/cd.yml/badge.svg)](https://github.com/AbdullahBinNasir16/BlockLens/actions/workflows/cd.yml)

Blockchain project intelligence. One contract address in, a complete visual
investigation out.

Two halves, one product: a backend that watches Base directly and judges
every new launch once, at launch + 5 minutes, and a front end that shows the
verdict, its anatomy, and the public running score of how right it has been.

- **The backend** (`backend/`), on free keyless Base sources: on-chain
  discovery and ingestion; outcome labels with a sensitivity analysis; the
  Phase 5 integrity audit and a properly sampled dataset (458-token random
  cohort, case-control training strata, operator families); two validated
  signals at launch + 5 minutes, **launch type** and **buyer-loss risk**; a
  FastAPI service that scores every new launch live, explains each score
  exactly, pushes the ones worth hearing about, and keeps a pre-registered
  forward record and paper-agent book.
- **The front end** (`src/`): Fresh Launches, the token page for any Base
  contract, the Paper Agent's book, Model Health, Trending Tokens, a
  watchlist and history held by the API, a wallet screener over a generated
  corpus (labelled as such), and three hand-built research profiles kept as
  labelled case studies.

See `backend/README.md` to run the backend, `DECISIONS.md` for every choice,
measurement and negative result behind it, `docs/FYP1_SCOPE.md` for what is in
and out of scope and why, and `CONTRIBUTING.md` for the branch and CI/CD
process.

## What the research supports, and what it does not

At launch + 5 minutes on Base:

- **Launch type decides liquidity-pull risk.** Self-deployed tokens were
  pulled 109 times in 113 held-out launches; launchpad tokens 0 times in 74.
  Forward, out of sample: 86% of self-deployed launches lost their liquidity
  within a day, against 0.4% of launchpad launches.
- **A model can rank buyer-loss risk.** PR-AUC 0.83 in period against 0.37
  for a fixed rule checker, 0.76 out of time.
- **The paper agent beats buy-everything** on its pre-registered test (315
  trades, +55% to +110% over control), and the page says where that edge
  comes from: the launch-type filter. The risk score has not yet been shown
  to add to it.
- **The wallet-graph features add nothing** over entry timing, at token or
  wallet level, on a properly powered test. They stay in the backend as a
  documented negative result.
- **The three case-study profiles are illustrations.** Their risk scores and
  parameter scores are **Sample** and are labelled so on every section.

## Run it

```bash
# backend: PostgreSQL 16, then
cd backend && python -m pip install -e . && python -m alembic upgrade head
uvicorn blocklens.api.app:app --port 8000          # API + live scorer

# front end
npm install
npm run dev        # http://localhost:5173, proxies /api and the public sources
npm run build      # type-check + production bundle
npm test           # vitest unit tests
```

Or the whole product from the published images:

```bash
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d     # http://localhost:8080
```

Alerts: set `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` on the API and every
scored launchpad launch with risk under 20% is sent to that chat. Unset,
nothing is sent.

## The path through the app

```
/                        Landing
/app/new                 New Investigation: any Base contract address
  └─ /app/investigating  resolves a case-study address to its profile…
  └─ /app/token/:address …and every other address to the live token page
/app/launches            Fresh Launches: every new pool, scored at minute 5, with push
/app/trending            Trending Tokens: GeckoTerminal, DexScreener, GoPlus, live
/app/portfolio           Paper Agent: the forward record, trade by trade
/app/model               Model Health: volume, reasons, drift, calibration, outages
/app/wallets             Wallet Screener over a generated corpus (Sample)
/app/watchlist           Starred tokens, held by the API
/app/history             Every address investigated, held by the API
/app/project/:id         The three case-study profiles
```

### Fresh Launches

Every new Base Uniswap V3/V4 pool, discovered from the chain itself, scored
once at its five-minute mark. Two signals, because they are the two the
research can defend: **launch type** (self-deployed and withdrawable, or
launchpad and locked) and **buyer-loss risk** (the chance a buy at the
minute-5 price is worth half or less six hours later). A pool outside the
scoring conditions shows the reason, never a number.

Every score opens its **anatomy**: the model's exact per-feature terms (tree
SHAP on the frozen artefact, in log-odds, summing to the score), each with
its value in the feature's own unit. New verdicts arrive by **push**
(server-sent events) as toasts, and, with permission, as browser
notifications for the launches the paper agent itself would buy.

The validation record travels with every API response and is printed on the
page. Below it, the **forward record**: predictions logged before their
outcome existed, reported only above a pre-registered floor.

### The token page

Any Base address. Live market data (DexScreener), holders, top-10 share and
honeypot flag (GoPlus), the pools, and, if the launch was tracked at
minute 5, its signals and anatomy. Nothing sample is ever shown under a real
token's name. Star it to keep it on the watchlist; every visit is recorded in
history.

### Paper Agent

The pre-registered forward test of the signal (DECISIONS.md, Phase 9). The
agent buys at minute 5 only a launchpad launch with risk under 20%, sells at
hour 6, pays 3% per round trip; −100% when the pool's liquidity was gone by
then; returns capped at +1,000% per trade. Four policies are computed from
the same rows (agent, buy everything, every launchpad launch, what the agent
refused), a cumulative-return chart, and every trade. All of it is derived in
`src/lib/live/paper.ts` from `/api/paper-agent/trades`; nothing about
performance is stored.

### Model Health

The live system reporting on itself, from the forward log: launches a day
and why each was or was not scored, the self-deployed share per day (the
regime shift that broke calibration in Phase 5), forward calibration by risk
bin, scoring delay, and outages. Deliberately separate from validation.

### Trending Tokens

Discovery over live pools from GeckoTerminal, enriched by DexScreener and
GoPlus through the Vite proxy. Metadata only, no analysis.

### The case studies

Three real Base projects (Nockchain, Sibyl, Dot) with hand-built profiles in
eight sections: overview, fundamentals, developer, on-chain, GitHub,
roadmap, risk, assessment. Market, supply, holder, repository and roadmap
figures were captured from public endpoints on 09 Sep 2026 and are marked
**Sourced**; scores and parameter readings are illustrative and marked
**Sample** on every section header and in the final assessment's footnote.
They exist to show what a full research record looks like; they are not
findings about those projects.

## The Wallet Screener

`/app/wallets`. Section-by-section documentation is in the file headers; the
short version: one chain per search, contracts pasted by address, a window,
and filters as one-word chips in two blocks, **in each project** (with a
must-pass-in-N-of-M rule) and **whole wallet**. Everything combines with AND.
Results come as a list or bubbles with a funnel above them, and every match
carries the reason it matched.

The corpus is **generated** and the page says so: `src/data/wallets.ts`
builds 400 wallets from a seeded generator, so the same query always returns
the same rows. No address corresponds to a real wallet. The evaluator,
`evaluateQuery` in `src/lib/screener.ts`, is pure and unit-tested; the README's
acceptance query (Base, three contracts, Jun–Sep 2026, PnL ≥ $2,000 and hold
≥ 15 min in at least two projects, win rate ≥ 55%) returns eight wallets and
that is asserted in `src/lib/screener.test.ts`. Replacing the corpus with the
backend's early-buyer cohorts is FYP-2 work (`docs/FYP1_SCOPE.md`, M9).

## Data model

Data is separated from the UI. No component invents a value.

| File | Holds |
|---|---|
| `src/data/types.ts` | Every interface, including `ProjectDataset`, the case-study record |
| `src/data/projects/*.ts` | The three case studies and the registry (`getDataset`, `findByContract`) |
| `src/data/checks.ts`, `wallets.ts`, `presets.ts` | The screener's check library, generated corpus and presets |
| `src/lib/screener.ts` | `evaluateQuery`: the screener's evaluator, the backend seam |
| `src/lib/live/launches.ts` | The feed, the model's validation record, `Explanation` |
| `src/lib/live/paper.ts` | The paper agent's book and its arithmetic |
| `src/lib/live/health.ts` | Model health and its series |
| `src/lib/live/product.ts` | Watchlist, history, the push stream |
| `src/lib/live/token.ts`, `trending.ts` | DexScreener, GeckoTerminal and GoPlus readers |

## Design system

Eight stylesheets, loaded in order from `src/main.tsx`: `global`, `primitives`,
`landing`, `app`, `research`, `screener`, `trending`, `live`. Paper and ink
(`#faf9f6`, no gradients); colour only as information (green healthy, red
concerning, amber uncertain); Times New Roman for prose, a monospace stack
for numbers and labels; hairlines over boxes; round where it means something.

## Performance

No chart library: every visualisation is hand-built SVG or CSS. Three
runtime dependencies (React, ReactDOM, React Router). Geometry is computed
once at module scope, scroll-driven work is rAF-throttled and writes only
transforms and opacity, reveals fire once, `prefers-reduced-motion` disables
all of it. The screener evaluates in under a millisecond over 400 wallets
and its table renders a windowed set of rows.

## Assets

`public/blocklens-mark.png` is the mark with its paper background keyed out.
`public/tokens/` holds each case study's logo, `public/chains/` the network
marks, `public/avatars/` the X profile pictures used in the case-study
headers and developer rows, captured once so the page makes no third-party
request at view time. Third-party marks identify the projects and networks
they belong to and nothing else.

## What is deliberately not here

No accounts: the product is single-user at this stage and its state lives in
the API's store. No KOL or social scoring: both need paid reads of X and
there is no keyless substitute, so they were cut rather than faked. No
chains other than Base: every source, label and model is measured there.
