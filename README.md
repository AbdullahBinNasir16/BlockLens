# BlockLens

[![CI](https://github.com/AbdullahBinNasir16/BlockLens/actions/workflows/ci.yml/badge.svg)](https://github.com/AbdullahBinNasir16/BlockLens/actions/workflows/ci.yml) [![CD](https://github.com/AbdullahBinNasir16/BlockLens/actions/workflows/cd.yml/badge.svg)](https://github.com/AbdullahBinNasir16/BlockLens/actions/workflows/cd.yml)

Blockchain project intelligence. One contract address in, a complete visual
investigation out.

Two halves:

- **The front end** (`src/`). Its three research profiles still come from
  data files, each section labelled `Sourced` or `Sample`, and the rest of
  this file describes them. Three pages are live:
  - **Trending Tokens**, from GeckoTerminal, DexScreener and GoPlus;
  - the page for **any token BlockLens has not researched**, which shows
    live market data and never a sample profile;
  - **Fresh Launches**, which reads the backend API.
- **The backend** (`backend/`), on free keyless Base sources:
  - ingestion and labels;
  - the Phase 5 integrity audit and a properly sampled dataset (458-token
    random cohort, case-control training strata, operator families);
  - two validated signals at launch + 5 minutes: **launch type** and
    **buyer-loss risk**;
  - a FastAPI service that scores every new launch live, and a
    pre-registered **forward test** of those scores.

  See [`backend/README.md`](backend/README.md) to run it, and
  [`DECISIONS.md`](DECISIONS.md) for every choice, measurement and
  negative result behind it.

**What the research supports, and what it does not.** At launch + 5
minutes on Base:

- **Launch type decides liquidity-pull risk:** self-deployed tokens were
  pulled 109 times in 113, launchpad tokens 0 times in 74.
- **A model can rank buyer-loss risk well:** PR-AUC 0.83 against 0.37 for
  a fixed rule checker, 0.76 out of time.
- **The wallet-graph features add nothing over entry timing,** at token or
  wallet level, on a properly powered test. The three profiles' risk
  scores, KOL figures and portfolio remain **Sample** and are not findings.

Three real projects are loaded, all on Base:

| Project | Ticker | Contract | Links |
| --- | --- | --- | --- |
| Nockchain | NOCK | `0x9b5e…1722` | [nockchain.org](https://nockchain.org) · [@nockchain](https://x.com/nockchain) |
| Sibyl | SIBYL | `0x797f…4714` | [sibyllabs.org](https://sibyllabs.org) · [@sibylcap](https://x.com/sibylcap) |
| Dot | DOT | `0x23a2…fe51` | [usedot.xyz](https://usedot.xyz) · [@usedotai](https://x.com/usedotai) |

## Sourced vs. sample — read this before demoing

Because real, named projects are on screen, the interface separates the two
kinds of data and labels every section with which one it is:

- **Sourced** — captured 09 Sep 2026 from public endpoints and pasted into the
  data files: market and pair figures (DexScreener), supply and valuation
  (CoinGecko), holder counts, top-10 concentration and creator balances
  (Blockscout, Base), paid-listing status (DexScreener orders), repository stats
  (GitHub API), and links and roadmaps from each project's own site. These are
  reproducible.
- **Sample** — illustrative shapes so the UI has something to render: risk and
  parameter scores, holder distribution and behaviour, KOL rosters and win
  rates, and the social series. **These are not findings about these projects.**

Every section header carries a `Sourced` or `Sample` chip, the wallet section
says so in a callout, and the final assessment repeats it in the footnote.

**The KOL section and the KOL directory name real accounts and show their real
profile pictures, but every number beside them — followers, social score, win
rate, thesis writing, outcome, calls — is a placeholder. No promotion record has
been measured.** That is stated under the section, under the directory's title
and in its footer. If this goes in front of anyone outside the team, either wire
those numbers to a real source or say out loud that they are dummies.

**The Portfolio now leads with the real paper agent**: a pre-registered forward
record from the live API, with returns hidden until its floor is reached
(DECISIONS.md, Phase 9). Below a divider marked *Illustrative simulation — not
a record*, **the old book is simulated end to end** — the model, its trades, prices and
returns. Its memecoin lore names real companies and people (Amazon, Nvidia,
TSMC, Robinhood's Vlad Tenev, Strategy, Palantir, Zcash) to show how the model
argues, and some of it is invented: in particular, **the dog's name "Pepper" is
made up**, and the SEND / AMZN reading ("the pair is a sentence") is this
build's interpretation, not a sourced story. Replace them with the real events
before showing it outside the team. The page says it is simulated under the
title, on a `Sample` chip, in its footer, and at the foot of every trade.

Nockchain's roadmap is its own published one: 33 dated items with statuses, from
nockchain.org/roadmap. Sibyl's and Dot's are built from dated, verifiable events
plus their published docs indexes; Dot's two `missed` entries rest on the GitHub
API showing an eight-week gap with no public push.

To swap a sample section for a real one, replace the values in the project's
data file and flip its entry in `provenance` from `'sample'` to `'live'`.

## The intelligence page

Twelve sections, in order:

| # | Section | Shape |
| --- | --- | --- |
| 00 | Overview | Two score rings, radar, 13 parameters with hover drivers |
| 01 | Fundamentals | Idea, uniqueness and innovation arcs, key findings |
| 02 | Developer | Profile, deployment timeline, activity bars |
| 03 | On-Chain | Seven gauges, then holder growth, flow, position sizes |
| 04 | Wallets | Holder bubble field with a detail drawer |
| 05 | KOLs | X avatar, score ring, outcome — nothing else |
| 06 | GitHub | Repo stats, contribution heatmap, timeline, consistency |
| 07 | Social | Growth, mentions, reach bars, diverging momentum |
| 08 | Roadmap | Status bar, filters, dated items (green / amber / red / hollow) |
| 09 | Narrative | Narrative map, relevance arc |
| 10 | Risk | One spectrum, every signal on it, compact ranked list |
| 11 | Assessment | Ring, three stats, marked bullets |

In the holder bubble field, area is the size of the position, green marks
wallets that hold and add, red marks wallets that bought and left quickly, and
hovering or clicking one opens its detail.

The seven on-chain gauges are top 10 holders, insiders, dev holding, bundlers,
LP burned, dex paid and smart traders. Three of them are sourced per project —
top 10 holders and dev holding from Blockscout, dex paid from the DexScreener
orders endpoint. The other four need cluster and launch-block analysis this
build does not run, so they show a qualitative band rather than a fabricated
percentage, and each gauge carries a filled or hollow dot saying which it is.

## Run it

The live pages (**Trending Tokens**, **Fresh Launches**, and the page for a
token BlockLens has not researched) need `npm run dev` or `npm run preview`,
which proxy the public APIs. **Fresh Launches** also needs the backend API
running: see `backend/README.md`, Phase 7.


```bash
npm install
npm run dev        # http://localhost:5173
npm run build      # type-check + production bundle
npm run preview    # serve the built bundle
```

## The path through the app

```
/                        Landing — chain plate, moon/rug story, process, coverage
  └─ Open Workspace
/app/new                 New Investigation — contract address + chain
  └─ Investigate
/app/investigating       Staged research animation (~4.5s)
  └─ resolves to
/app/project/:id         The intelligence profile — 12 sections
/app/trending            Discovery. Metadata only, no analysis.
/app/wallets             Wallet Screener — cross-project wallet discovery
/app/kols                KOL directory — every tracked account, filterable
/app/portfolio           Portfolio — the trading model's own book, trade by trade
/app/watchlist           Saved projects with risk and score change
/app/history             Previous investigations, grouped by day
```

Pasting a known contract address resolves to that project's profile; anything
else falls back to Nockchain so the flow always completes.

## The Wallet Screener

`/app/wallets`, **Screener** in the sidebar. Section 04's bubble field answers
"who holds *this* project"; the screener answers "which wallets, anywhere in
coverage, behave like *this*".

The page is one panel of four numbered steps, then the results.

1. **Chain** — exactly one per search: Ethereum, Base, Solana or BNB Chain.
2. **Contracts** — paste a contract address and press **+**; add as many as you
   like. Projects are entered by address, never picked by name. Each added
   address resolves to its token mark and ticker, or stays visible marked
   `not indexed` or `on <other chain>` and is left out of the search. The
   input validates the address format for the chosen chain and rejects
   duplicates in any letter case. Below it, the prototype's indexed contracts
   are listed as addresses for one-click adding.
3. **Window** — 7D / 30D / 90D / YTD / Custom. Every trade-derived value is
   computed from activity inside it.
4. **Filters** — every check is already on screen as a one- or two-word chip,
   with no descriptions. Click a chip and it fills with ink and opens its own
   value in place: `PnL ≥ $2,000`, `Hold time ≥ 15 min`, `Funding is Fresh`.
   Click the operator to flip ≥/≤, type the number, pick a unit; click the
   label or × to turn it off.

The chips sit in two blocks, and the split is the query model:

- **In each project** — evaluated once per added contract. The block's header
  carries the rule: *must pass in at least / exactly / at most N of M
  projects*. The rule belongs to the block, not to any chip, so a wallet with
  $50k of PnL in one project fails *at least 2*, and the drawer shows why.
- **Whole wallet** — measured once, across every project in scope.

Everything combines with **AND**. There is no OR, no nesting and nowhere to type
a formula, so a check exists only if a backend could index and evaluate it on
its own. A hollow ring marks the six **derived** checks — funding, cluster,
smart money, insider, rug exposure, first pump — which need clustering,
labelling or price history a real deployment would supply. Direct checks carry
no mark, because direct is the normal case.

**Search** sits in a bar pinned to the bottom of the panel, with a one-line
summary of the question. It stays disabled until at least one indexed contract
is on the chosen chain. Results never update silently: change a filter after
searching and the results are marked out of date until you search again.

**Results** come back as a **List** or as **Bubbles** — your choice — with a
one-line funnel above them showing what each stage removed. One sort control
(PnL, win rate, average hold, projects matched, last active; ascending or
descending) drives both views. In the list, column headers sort too. In the
bubble field, circle size is the sort metric, colour is profit or loss, and the
top of the sort sits at the centre. Hovering a circle reads it, and clicking
opens it; the field shows the first 60 and the list keeps every row.

Opening any wallet shows its positions with entry and exit, a cumulative
realized-PnL line, and **every switched-on filter with the value it actually
saw, marked pass or fail** — per project for the project rule. A wallet never
appears without its reason. If nothing passes, the empty state names the stage
that removed the last wallets and offers one concrete way to loosen it.

Three presets switch on a set of filters and a window; they never touch the
chain or the contracts.

### The screener corpus is generated — say so

The section carries a `Sample` chip and repeats it in the footer. `wallets.ts`
builds **400 wallets from a seeded generator** (fixed clock, fixed seed, so the
same query always returns the same rows). The distribution is deliberately
unkind: 41% of wallets are profitable, 20 clear $50k realized, holding times are
log-normal (p10/p50/p90 = 2m / 1.4d / 94d) and there is a visible knot of 47
sub-minute round-trippers for the sniper checks to find.

The acceptance query — *Base, all three contracts, 01 Jun – 01 Sep 2026, PnL
≥ $2,000 and hold time ≥ 15 minutes in at least 2 projects, win rate ≥ 55%* — is
built entirely in the UI by pasting the three addresses and switching on three
chips, and returns 8 wallets. Of the 65 wallets with exactly one qualifying
project, none appear; the plainest case, `0x63d2…5641`, has a single $73k win
and nothing else, and is excluded. Two of the three presets use a year-to-date
window, because fresh wallets and sub-minute round trips cluster around
launches that a 90-day window cuts off.

What makes it more than decoration: **every wallet stores what moved** —
invested, fraction sold, proceeds, value still held, and the timestamps around
them. PnL, win rate and holding time are never stored. `evaluateQuery` derives
them the same way a backend would, so if the arithmetic is wrong it is wrong in
the open. No address in the corpus corresponds to a real wallet.

All three demo projects are on Base. Choose another chain and the added
contracts stay on screen marked `on Base`, and Search stays disabled until a
contract on that chain is added. There used to be a *Distinct chains* check;
with one chain per search it would always read 1, so it was removed.

## The KOL directory

`/app/kols`, **KOLs** in the sidebar. Every account BlockLens tracks — 24 of
them — each leading with its X profile picture.

**Filters apply as they move.** There are two dozen accounts, not four hundred
wallets, so there is no Search button:

- a search box for name or @handle;
- **Focus** chips — AI, Memes, DeFi, Infra, Trading, Research, NFTs — and
  **Chain** chips; several picks inside one group mean *any of these*;
- five threshold sliders: **Followers** (log scale, since reach spans two
  orders of magnitude), **Social score**, **Win rate**, **Thesis writing** and
  **Outcome**. Every account is a tick on each slider's track, ink if it clears
  the threshold and faint if not, with a live "16 of 24" under it — so you can
  see what a setting removes before you let go.

Different filters combine with AND. Each active filter shows as a removable
pill above the results, and **Reset all** clears them. If nothing passes, the
empty state works out which single filter is costing the most — "Dropping
Social ≥ 95 would bring back 16 accounts" — and offers to drop it.

Results come as **Cards** or a **Map**:

- **Cards** — face, name, @handle linking to X, focus tags, chains, a social
  score ring, win-rate and thesis bars, outcome, followers, calls, and the token
  marks of any indexed project the account covered, linking to that project's
  research. Sort by followers, social, win rate, thesis, outcome or calls,
  ascending or descending; the measure you sort by is marked on every card.
- **Map** — every account placed by thesis writing (across) against win rate
  (up), sized by followers and drawn with its profile picture. Your win-rate
  and thesis thresholds are dashed lines, and the corner they keep is shaded.
  Accounts any filter removes stay on the map, greyed, so the filter is read
  against what it removed. Hover any face to read it.

The directory is the one source of every KOL record. Project pages list handles
and read the numbers through `kolsFor`, so an account cannot show one win rate
on a project and another in the directory, and "covered" marks are read from
the project records rather than typed separately. Each project's KOL section
links to the directory.

Ten accounts were added for the directory — @MustStopMurad, @Pentosh1,
@CryptoCred, @DegenSpartan, @rektcapital, @thedefiedge, @milesdeutscher,
@Route2FI, @aixbt_agent and @CryptoHayes — with profile pictures captured like
the rest. @AltcoinGordon was tried and dropped: the account no longer resolves,
and a placeholder face would have been worse than leaving it out.

## The Portfolio

`/app/portfolio`, **Portfolio** in the sidebar, second from the top; its count
is the number of open positions. BlockLens runs a model that buys new launches
when they clear its gate, sizes them by how far inside the gate they sit, and
writes down why. This page is its book: 21 trades since 05 Jan 2026, $100K to
$144,335 (+44.3%), a 59% win rate (10 of 17 closed), 4 positions open.

Read top to bottom it answers four questions.

**How is it doing.** Book value, return, realized and unrealized, a win-rate
ring, and trades / open / average hold / max drawdown / best / worst — the best
and worst open their trades. "Where it made money" splits P&L and win rate by
kind: memecoins, AI, infra, DeFi. Below, one chart in three bands on a shared
time axis: the equity curve with every exit marked on it in green or red, a
**positions** lane where each trade is a bar from buy to sell, and each month's
return. Hover the curve for a crosshair; hover a bar to shade its holding
period on the curve; click either to open the trade. 1M / 3M / All ranges.

**How it decides.** The gate: age ≤ 48h, confidence ≥ 65, risk ≤ 55 (≤ 50 for
memecoins since 13 Jun), liquidity ≥ $40K, and lore ≥ 60 for memecoins. A
funnel — 1,106 launches scored, 107 cleared the scores, 21 bought — and why the
other 86 were passed over. A dated log of rule changes: the memecoin risk
ceiling was lowered after the OPTIMUS loss. Beside it, every launch scored this
year plotted by risk against confidence, the "buy" corner shaded, the buys
coloured by outcome. Click any buy to read it.

**What it holds.** Four cards: return, the position's price path, P&L, size,
days held, the line it was bought on, and what it is watching for an exit.

**What it has done.** Every trade, filterable by kind and outcome, sortable by
date, return or size. Each row carries the line that says why — for a memecoin,
its lore hook, set in quotation marks — and a return bar on a log scale, so a
doubling and a halving draw the same length.

Every trade opens the same **dossier**: return and P&L, entry, exit, days held,
hours after launch; the price path with entry, peak and exit marked; **why it
bought**; for a memecoin, **the lore** — the hook, the moment, the pair ("SEND
priced in AMZN") and why it lasts, with its lore score; **at the gate**, each
criterion drawn against the limit in force the day it was bought; and **why it
sold**, or what would make it sell. SIBYL and DOT link to their research pages,
and their gate scores match those pages' scores; DOT's mark is the price
captured on its page.

Two things are enforced rather than promised:

- **A memecoin cannot exist without its lore.** `Trade` is a discriminated
  union; a `kind: 'meme'` trade without a `lore` block and a lore score fails
  to compile.
- **Performance is computed, never stored.** Returns, win rate, the equity
  curve, drawdown, monthly and by-kind figures are all derived from the trades
  in `lib/portfolio.ts`. Each trade stores entry, exit and peak; the path
  between them is a seeded bridge pinned to all three, so the curve is
  deterministic and honest to the numbers that matter.

The memecoin book: SEND / AMZN, AI / NVDA, AU / TSM, ZCAT / ZEC, PEPPER / HOOD,
CHIPS / INTC, LASER / MSTR, OPTIMUS / TSLA, RING / PLTR and BOBO / SOL.

## Data model

Data is fully separated from the UI. No component invents a value; they only
render these records.

| File | Holds |
| --- | --- |
| `src/data/types.ts` | Every interface, including `ProjectDataset` — the contract a backend must satisfy |
| `src/data/projects/nockchain.ts` | Complete record for NOCK |
| `src/data/projects/sibyl.ts` | Complete record for SIBYL |
| `src/data/projects/dot.ts` | Complete record for DOT |
| `src/data/projects/index.ts` | Registry, `getDataset`, `findByContract`, chain identity |
| `src/data/lists.ts` | Trending, watchlist and history — all projections of the registry |
| `src/data/synth.ts` | Seeded builders for the illustrative series |
| `src/data/labels.ts` | Shared display labels |
| `src/data/checks.ts` | The screener's check library — 38 chips, and the only place a check is declared |
| `src/data/wallets.ts` | The 400-wallet screener corpus, seeded and deterministic |
| `src/data/presets.ts` | Window ranges, the empty query, the three presets |
| `src/lib/screener.ts` | `evaluateQuery` and the per-check metrics — the backend seam |
| `src/lib/pack.ts` | Deterministic circle packing shared by both bubble fields |
| `src/data/kols.ts` | The KOL directory — 24 accounts, and `kolsFor`, which every project's KOL list reads through |
| `src/data/portfolio.ts` | The model's book — 21 trades with theses and lore, the gate, the rule log, and the seeded field of scored launches |
| `src/lib/portfolio.ts` | Book arithmetic — returns, win rate, equity curve, drawdown, monthly and by-kind figures, price paths, gate checks |

`ProjectDataset` carries only what the page renders. When a section was removed,
its data went with it — there is no dead payload behind the UI.

Each `ProjectDataset` is one project's whole research record. `ProjectProvider`
puts it in context and every section reads it through `useProject()`, so adding
a fourth project means adding one file and one registry entry — no component
changes.

### Swapping in a backend

1. Keep the interfaces in `types.ts`; make the API return `ProjectDataset`.
2. Replace `datasets` in `projects/index.ts` with a loader keyed by contract
   address. `getDataset` and `findByContract` are the only two call sites.
3. Flip each section's `provenance` entry to `'live'` as real data replaces the
   sample values, so the chips stay honest.
4. Node positions in the wallet and relationship graphs are authored, not
   simulated. A backend either supplies positions or you add a layout pass —
   the components read `x`, `y`, `r` and nothing else.

For the screener, the seam is one function:

1. `evaluateQuery(query, corpus)` in `src/lib/screener.ts` is pure — a
   `ScreenerQuery` and a `WalletRecord[]` in, a `ScreenerResult` out, no UI
   imports and no reads of the clock. Replace its body with a `POST` and keep
   the signature (returning a promise, with the route holding the pending
   state). `src/routes/Screener.tsx` is the only call site and treats the
   result as opaque.
2. `ScreenerQuery` is the request body and `ScreenerResult` the response, both
   in `types.ts`. Scope arrives as `{ chain, contracts, from, to }` — the
   addresses exactly as the user added them — so the server resolves contracts
   against its own token index; here the registry stands in. The server owes
   back `matches`, the `funnel` stages in order, and `scopedWallets`;
   `limitingStage` is derivable from the funnel if the server would rather not
   send it.
3. Contract resolution for the chips (`resolveContract` in
   `components/screener/FilterPanel.tsx`) is the second call a real deployment
   makes — a token lookup when an address is added. It reads `findByContract`
   today.
4. **Adding a check is one definition plus one predicate.** Append a
   `CheckDefinition` to `CHECKS` in `data/checks.ts`, then a metric to
   `PROJECT_METRICS` or `WALLET_METRICS` in `lib/screener.ts` under the same id.
   No component changes — the chip, its value editor and the drawer all read
   the definition, and the chip lands in the right block and category row by
   itself. An unknown check id fails closed rather than silently passing, so a
   half-added check cannot masquerade as a working one.
5. `WALLET_CORPUS` is the only import of the generated data. A real deployment
   drops `data/wallets.ts` entirely and lets the server hold the corpus.
6. Positions here are stored whole, so one counts when its activity range
   overlaps the window. A backend with per-trade records should compute from
   the trades inside the window and split positions across the boundary — that
   is the one place this evaluator is coarser than the real thing, and it is
   noted in the file.

## Design system

The visual language lives in eight stylesheets, loaded in this order from
`src/main.tsx`:

- `styles/global.css` — tokens, type scale, motion primitives
- `styles/primitives.css` — rings, meters, charts, tags, drawer, and the shared
  controls: segmented selector, sort bar, text buttons, empty state
- `styles/landing.css` — the marketing surface
- `styles/app.css` — workspace shell, tables, forms
- `styles/research.css` — the intelligence profile
- `styles/screener.css` — the filter panel and chips, results, bubbles, wallet drawer
- `styles/kols.css` — the KOL directory: threshold sliders, cards, map
- `styles/portfolio.css` — the Portfolio: hero, equity chart, gate, positions,
  history, dossier and lore

Class names are global, so each page's blocks carry their own prefix
(`bl-pf…`, `bl-tpair`, `bl-tlore`, `bl-kdir`). Two older stylesheets still hold
unused blocks named `.bl-kols`, `.bl-pair` and `.bl-lore`; reusing a name like
that restyles both pages at once, which is how it was caught.

Rules the whole interface follows:

- **Paper and ink.** Background is `#faf9f6`. No gradient backgrounds anywhere.
- **Colour is information.** Green is a healthy signal, red a concerning one,
  amber neutral or uncertain. Nothing is coloured for decoration.
- **Times New Roman** for everything readable; a monospace stack for numbers,
  addresses, labels, and metadata. Body text is 16–17px, not 13px.
- **Hairlines over boxes.** Structure comes from 1px rules and whitespace.
- **Round where it means something.** Score rings, arc meters, radial maps,
  pills, arched section frames — not rounded rectangles everywhere.

## Performance

- No chart library. Every visualisation is hand-built SVG or CSS.
- Only three dependencies: React, ReactDOM, React Router.
- Graph and lattice geometry is computed once at module scope, never per frame.
- Scroll-driven sections use one rAF-throttled reader that only runs while the
  section is on screen, and only ever writes `transform`, `opacity`, or
  `stroke-dashoffset` — no layout in the scroll path.
- The hero's ambient animation is six `stroke-dashoffset` loops, and it stops
  once the hero scrolls away.
- Reveal animations fire once via `IntersectionObserver`, which disconnects
  immediately after.
- `prefers-reduced-motion` disables all of it.
- The screener corpus is built once at module scope. `evaluateQuery` runs only
  on Search and costs under a millisecond over 400 wallets; the short pause
  after pressing Search is deliberate, and `prefers-reduced-motion` removes it.
- The results table renders a fixed-height window of rows rather than the whole
  set, which is why row height is pinned in CSS. The bubble field is packed
  once per search or sort, never per frame.
- The KOL map lays out once, with a short deterministic pass that nudges
  overlapping faces apart; filtering only greys circles, it never re-lays them.

Production bundle: ~88 KB app + ~54 KB vendor + ~22 KB CSS, gzipped.

## Assets

`blocklens-logo.png` is the supplied logo. `public/blocklens-mark.png` is the
same artwork with its flat paper background keyed out and trimmed, so the mark
can sit on any surface. The wordmark is set in the body serif next to it.

`public/tokens/` holds each project's own logo, taken from its official site and
normalised to a 256px square tile. `public/chains/` holds the network marks —
Ethereum, Base, BNB Chain and Solana — normalised to 64px with transparency.
`public/avatars/` holds X profile pictures, one 400px `<handle>.jpg` per
account, captured once (via unavatar.io) so the page makes no third-party
request at view time. A handle with no file falls back to a generated identicon,
so adding an account is just dropping a file in. They are used wherever an X
account appears: the project header, the developer row, the KOL grid, the
social reach list, and the KOL directory's cards and map.
Token tiles carry the chain mark as a corner badge, and the chain mark also
appears in the chain selector, the table chain column and the project header.
Third-party marks are used only to identify the projects and networks they
belong to.

## What is deliberately not here

No authentication, no persistence, no real chain access. Watchlist changes and
the collapsed sidebar are component state and reset on reload.

The screener deliberately has no saved queries, no CSV export, no OR logic, no
user-authored checks, and no pagination beyond the windowed list. Each filter
is on or off, never on twice, so there is one project rule rather than several
independent groups.
