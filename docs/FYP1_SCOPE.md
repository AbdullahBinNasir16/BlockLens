# BlockLens — FYP scope

*Written 2026-10-22 for the FYP-1 mid supervisory evaluation. This page is
the agreed boundary of the project: what the product is, what is built, what
is still to build, and what was cut and why. It should be read with
`DECISIONS.md`, which holds the evidence behind each cut.*

## 1. The product in one paragraph

A new token appears on Base roughly every minute, and most of them lose the
people who buy them money, either because the deployer withdraws the
liquidity (a "rug") or because the price never recovers from its first hour.
BlockLens watches the chain directly, judges every new launch once, at launch
plus five minutes, and shows a trader two defended signals: **who holds the
liquidity** (self-deployed and withdrawable, or launchpad and locked) and the
**probability a buy at that moment is worth half or less six hours later**.
Each signal carries its own validation record on screen, and every prediction
is written down before its outcome exists, so the product's accuracy is a
public running score rather than a claim.

## 2. What exists today

| Component | Where | Status | Data |
|---|---|---|---|
| On-chain ingestion of new Base pools, first 24 h of transfers and swaps | `backend/blocklens/ingest` | done, tested | live chain (keyless RPC) + DexScreener |
| Outcome labelling (RUG / FAILED / SURVIVED / NEVER_LAUNCHED) with sensitivity analysis | `backend/blocklens/label` | done, tested | archive `eth_call` samples |
| Sampling design, integrity audit, 458-token random cohort, case-control training set | `backend/blocklens/sampling`, `model/audit.py` | done | 1,066 alive tokens, 841 operator families |
| Launch-type signal and buyer-loss model (`buyer_loss_v1`) with held-out and out-of-time validation | `backend/blocklens/model`, `reports/model_card_*.md` | done | PR-AUC 0.83 in period, 0.76 out of time |
| Live scorer and FastAPI service (`/api/launches`, `/api/token/{addr}`, `/api/forward`, `/api/health`) | `backend/blocklens/live`, `api` | done, tested | live chain, every minute |
| Pre-registered forward validation and paper agent | `backend/blocklens/live/resolver.py`, `reports/paper_agent.md` | running since 2026-10-19 | 832 resolved predictions so far |
| Wallet graph: funding edges, clusters, 95 propagated features | `backend/blocklens/graph` | done, tested; **no predictive value found** | stored transfers |
| **Fresh Launches** page reading the API | `src/routes/Launches.tsx` | done | live API |
| **Trending Tokens** and the page for any unresearched token | `src/routes/Trending.tsx`, `UnresearchedToken.tsx` | done | GeckoTerminal, DexScreener, GoPlus (live) |
| Twelve-section research profile for three named projects | `src/routes/ProjectIntelligence.tsx` | done as a UI; most sections are **Sample** | data files, labelled Sourced / Sample |
| Wallet Screener over a 400-wallet corpus | `src/routes/Screener.tsx` | done as a UI; corpus is **generated** | seeded generator |
| KOL directory (24 accounts) | `src/routes/Kols.tsx` | done as a UI; every number is a **placeholder** | none |
| Portfolio page | `src/routes/Portfolio.tsx` | real paper-agent record on top; simulated book below | API + invented trades |
| Watchlist, history | `src/routes/WatchlistPage.tsx`, `HistoryPage.tsx` | static, reset on reload | projections of the three profiles |
| CI/CD pipeline, containers, branch process | `.github/workflows`, `Dockerfile`, `backend/Dockerfile`, `CONTRIBUTING.md` | added 2026-10-22 | — |

The pattern is clear: the backend is real, measured and tested; the front end
is wide, and about half of it renders sample data. The scope below narrows the
front end to what the backend can stand behind, and names the rest as
deferred or cut.

## 3. Scope decision

**The core module is Launch Risk Intelligence for Base:** discover every new
pool on chain, score it once at minute 5 with the two validated signals, serve
that through the API to the Fresh Launches feed and the token page, and keep
a public forward record of how right the scores were. Everything else is
either built on top of that or removed.

### 3.1 In scope for FYP-1 (mid evaluation and final)

| # | Module | Owner | State |
|---|---|---|---|
| M1 | **Ingestion and labelling pipeline** (Phases 1, 2, 5) | Abdullah | done |
| M2 | **Launch risk signals**: launch type + buyer-loss model, with validation (Phases 5, 6) | Abdullah | done |
| M3 | **Live scoring API and Fresh Launches feed** (Phase 7) | Abdullah | done |
| M4 | **Forward validation and paper agent** (Phases 8, 9) | Abdullah | running; first 7-day liquidity results due 2026-10-26 |
| M5 | **CI/CD and delivery**: GitHub Actions CI for both halves (unit, API, audit, end-to-end), container images on GHCR with a vulnerability scan, production compose, branch protection, PR process | Shahmir | pipeline complete; branch protection to switch on |
| M6 | **Product around the signal**: token page for any Base contract (live market and security data merged with the BlockLens signal and its anatomy), push alerts, the Paper Agent page, Model Health, watchlist and history | both | done (Phase 10) |

### 3.2 In scope for FYP-2

| # | Module | What it means | Why it is feasible |
|---|---|---|---|
| M7 | **One investigation flow** | `/app/new` resolves any Base address to the token page (M6). The three hand-built profiles stay as research case studies, reached from a "Case studies" link, with their Sample chips | removes the "paste anything, get Nockchain" fallback that evaluators will probe |
| M8 | **Persistence**: accounts-free watchlist and investigation history stored by the API | two tables, four endpoints; the UI already has both pages | small, and gives the product state that survives reload |
| M9 | **Early-buyer screener** (replaces the generated 400-wallet corpus) | "which wallets bought tracked launches in their first six hours, and what did they realise" over the backend's stored transfers and swaps; the existing `evaluateQuery` seam becomes a POST | the backend already builds minute-5 buyer cohorts and realised cash for Phase 6; the screener UI and filter chips exist and are unit-tested |
| M10 | **Model v2 on the forward record** | retrain buyer-loss on the live predictions once the pre-registered floor is passed, reported as a new record | the floor is 200 resolved / 20 losses; 832 / 14 as of 2026-10-21 |
| M11 | **Hosting** | the compose stack on a cloud VM so the feed runs without anyone's laptop | images already publish; needs a host (see 4) |

### 3.3 Cut from the project

| Feature | Why | What replaces it |
|---|---|---|
| **KOL scoring** (win rates, social score, thesis writing, calls) | needs paid reads of X posts (about half a US cent each) and there is no keyless source; decided in `DECISIONS.md`, 2026-10-19 | the directory page is removed from the product. If a reference list of accounts is wanted later, it is links only, with no numbers |
| **Social growth, mentions and reach; narrative map** | same source, same cost | removed from the token page |
| **Simulated portfolio** (21 invented trades, memecoin "lore") | invented trades beside a real forward record invite the question "which of these is real"; the lore names real companies and people | the Portfolio page shows the real paper agent only (M4) |
| **Holder bubble field and sample risk / parameter scores on the three profiles** | hand-authored positions and scores, not measurements | the profiles become labelled case studies (M7); the live token page carries measured values only |
| **Wallet-graph features in the product** | measured to add nothing over entry timing, at token and wallet level, at full power (Phase 5 Part D, Phase 6) | kept in the backend as a documented negative result; it is a research contribution of the report, not a feature |
| **Multi-chain** (Ethereum, Solana, BNB in the chain selector) | every measurement, source and model is Base; Solana's per-token volume breaks a free tier first | chain selector shows Base only; the others are listed as future work |

## 4. What is not possible, and the alternative

| Not possible | Reason | Alternative adopted |
|---|---|---|
| Real KOL / social numbers | X API is paid; no keyless substitute | cut (3.3) |
| Blockscout for holder counts and top-10 concentration | `base.blockscout.com` now returns HTTP 403 to every request | **GoPlus** token security (free): holder count, top-10 holders, LP holders, owner, honeypot and tax flags. Already wired on the Trending page |
| Who the trader is on an aggregator swap | the transfer counterparty is the router; the real wallet needs a transaction index that is not keyless | the screener (M9) covers direct pool buyers, which is what the backend already measures; stated on the page |
| Dollar PnL for wallets | most Base launches are quoted in WETH, and there is no historical ETH/USD series in the store | GeckoTerminal OHLCV (free) for the ETH/USD series, built as part of M9; until then, PnL is in quote units |
| GitHub Pages for the front end | not available on a private repository on the free plan | CD publishes container images to GHCR plus a GitHub Release with the bundle. For a public URL, either a free Render/Vercel/Cloudflare Pages site for the web image and a small VM for the API, or make the repo public |
| Docker on Abdullah's development machine | no admin rights | the pipeline builds the images in CI, and the store tests run against a PostgreSQL service in CI, so nothing depends on local Docker |
| The forward test surviving a reboot | it runs as a Windows scheduled task on one laptop; a 38-hour outage has already happened | M11: the compose stack on a VM with `restart: unless-stopped` |

## 5. Mid-evaluation deliverables

What the committee asked for: the core module live, with a CI/CD pipeline,
meaningful branches and automated tests, and the report.

1. **Core module demo** (M1 to M4): start the API, open Fresh Launches, show
   pools arriving and being scored at minute 5, open one, show the forward
   record and the paper-agent panel. Then `/api/launches` raw, to show the
   validation record travels with every response.
2. **Pipeline**: the CI runs on pull requests #1 to #5 (frontend typecheck,
   33 unit tests with a coverage floor, build; backend 161 tests against
   PostgreSQL; dependency audits; 7 browser end-to-end tests), the CD run
   publishing and scanning two images, the branch graph `main ← develop ←
   feature/*`, and branch protection on both.
3. **Tests**: `npm test` and `pytest` locally, the same as CI.
4. **Report**: the FYP-1 mid report in the FAST template under `report/`,
   compiled by the `Report` workflow, with this scope as section 1.6 and
   `DECISIONS.md` as the evidence base for chapters 2 and 5.

## 6. Branch protection

GitHub offers branch protection rules on a private repository only on a
paid plan (or on a public repository). Until the repository is made public,
the rule is enforced by convention: every change to `develop` and `main`
arrives as a reviewed, CI-green pull request, which the merge history shows.
The day the repository goes public: Settings → Branches → Add rule for
`main` and `develop`: require a pull request, 1 approval, and the
**Frontend** and **Backend** checks; no bypass.

## 7. Timeline

| When | Milestone |
|---|---|
| 2026-10-22 | CI/CD, tests, Phase 10, product rework and the report draft in pull requests #1 to #5 |
| 2026-10-26 | first 7-day liquidity results on the forward record |
| before the mid evaluation | `develop` → `main` release `v0.1.0`; branch protection on; report submitted |
| FYP-1, after the mid evaluation | M7 (single investigation flow) and the product cuts in 3.3 |
| FYP-2 | M8 persistence, M9 early-buyer screener, M10 model v2, M11 hosting |
