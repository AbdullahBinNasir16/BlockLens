# Decisions

Written as decisions are made, not afterwards. Each entry says what was
decided, when, and why. Entries marked **OPEN** are not mine to close.

---

## 2026-10-11 — Part A spike: documented limits that did not survive contact

Recorded because the project's cost model was built on published figures, and
some of them have moved. Full evidence in `backend/spikes/FINDINGS.md`.

**Confirmed as documented**

- Base runs at exactly 2.00 s/block — 43,200 blocks per day. Measured across
  blocks 51,000,000 → 51,043,200 (86,400 s).
- Etherscan V2's free tier does not serve Base or BNB Chain. It also does not
  serve **Optimism**, which the brief's table did not mention. Ethereum,
  Arbitrum One, Unichain, Polygon, Blast and Linea are on the free tier.
- The `eth_getLogs` arithmetic holds: at a 10-block cap, one token-day is
  4,320 calls, 259,200 CU, about 115 tokens a month. Not viable.

**Proved wrong, or no longer true**

- **Blockscout's public API is no longer a free fallback.** `base.blockscout.com`
  now answers every request with a Cloudflare challenge (HTTP 403). Several
  older write-ups, including our own earlier notes, treat it as keyless.
- **Envio HyperSync is no longer keyless.** HTTP 401; an API token is now
  required.
- **DexScreener is a poor discovery source for new Base tokens.** Its
  `token-profiles/latest` and `token-boosts/top` feeds returned 60 rows with
  **zero** Base tokens (51 of 60 were Solana), and its search surfaces
  established tokens rather than launches. Discovery had to be done on-chain
  against DEX factory events.
- **Counting Base launches from factory events alone undercounts by ~100×.**
  Uniswap V4's singleton emits 3,115 `Initialize` events a day on Base, against
  39–158 pool creations a day across every V2/V3-style factory combined. Any
  discovery design that watches factories will miss most of the chain.
- **The 10-block cap is not an Alchemy quirk.** Every reachable free Base RPC
  caps `eth_getLogs` between 10 and 1,000 blocks, or refuses archive queries
  outright. Tenderly's public gateway is the most generous at 1,000 blocks
  (and a separate 20,000-result cap).

**Could not be verified**

- Whether Alchemy's free plan permits `alchemy_getAssetTransfers` at full block
  range, and its true CU price. There is no Alchemy key in this environment and
  the public `demo` key returns HTTP 429 on Base. This is the single most
  important open question in the project and it stays open until a key exists.

---

## 2026-10-11 — Swaps come from transfers, with one caveat — **PROVISIONAL**

**Decision:** reconstruct trades from ERC-20 `Transfer` logs to and from the
pool address rather than adding a second data source. Pool logs arrive free in
the same `eth_getLogs` call that fetches the token's transfers, so `swap` rows
cost nothing beyond the transfer scan.

**Why:** measured on a real CAS swap. Direction and both amounts are
recoverable from the pool's transfer pairs; price in quote terms is their
ratio, and USD comes from `pair_snapshot`, which we are already collecting.

**The caveat, measured:** transfers do **not** identify the trader on
aggregator routes. In the sampled transaction the transfer counterparty was
Uniswap V4's `PoolManager`, not the trader, and two legs of one route were
summed. The real wallet is `tx.from`, which costs ~26 CU per transaction —
about 70× the cost of the transfers themselves, and the only measured figure in
the spike that does not fit a free tier.

**Consequence for Phase 1:** store `from`/`to` exactly as recorded and do not
attempt wallet attribution. `wallet.funding_source` stays `unknown`, as the
brief already specifies. Phase 2 should measure the cheaper route — joining the
`external` and `erc20` categories of `getAssetTransfers` on transaction hash,
which recovers the EOA for natively-paid swaps at no extra call.

---

## 2026-10-11 — Chain: Base. Sources: free and keyless

**Decision:** Phase 1 targets **Base**, and the ingestion path uses no paid
plan and no API key.

**Why Base, given the instruction was "only unpaid work":** Base is not the
paid option. What is paid on Base is *Etherscan V2 specifically*, and my first
report stated that in a way that was easy to read as "Base costs money". It
does not. The complete first-24-hour history of a Base token is reachable for
**44 calls through Tenderly's public gateway, with no key and no account**, and
discovery and market snapshots come from DexScreener, also keyless. The whole
Part A spike — 2,187 calls — cost nothing and required no signup.

**Why not Solana or Robinhood Chain**, the two named alternatives:

- **Solana** is free to read on the public RPC, but measured per-token volume
  is 75,000–1,200,000 signatures per token-day against Base's 443–7,679
  transfers. It is the chain where a free tier breaks first, not last.
- **Robinhood Chain** appears on DexScreener (4 of 30 rows in one profile
  feed), so it is indexed, but it has no established free archive RPC that I
  measured, and no launch population to speak of. Choosing it would trade a
  measured path for an unmeasured one.

**What this costs us:** the `alchemy_getAssetTransfers` path stays unverified,
because verifying it needs a key. It is implemented as an optional source
behind a config switch, so adding a key later is a config change, not a
rewrite. The keyless path is the default and is what Phase 1 runs on.

**Consequence for the budget module:** the metered resource is no longer
Alchemy compute units but *requests to a public endpoint we do not own*. The
budget enforces a token bucket per source and a per-run call ceiling, and the
persisted monthly counter tracks CU only when the Alchemy source is enabled.

---

## RESOLVED — Which chain Phase 1 targets

**Recommended:** Base. It fits the free tier with two orders of magnitude of
headroom (120–960 CU per token-day, measured volume), it is the chain the
frontend already models, and Solana's per-token volume is 10–100× worse.

**Decided 2026-10-11 by the user, on the rule "unpaid work only":** Base, for
the reasons in the entry above. Solana and Robinhood Chain were the named
alternatives and were rejected on measured grounds.

## 2026-10-11 — The dataset target is reachable on Base (first answer withdrawn)

**What I first reported:** 1–3 tradeable launches a day on Base, making 5,000
tokens "years of history". **That was wrong**, and it was wrong because the
scan only covered venues that emit a per-pool creation event (Uniswap V2/V3,
Aerodrome, PancakeSwap, BaseSwap, AlienBase). Uniswap V4 keeps every pool in a
singleton `PoolManager`, so none of its launches appeared.

**Corrected, measured on 2026-09-05:** 3,115 V4 `Initialize` events in 24 h →
1,540 distinct new tokens against a known quote; 5 of a 60-token sample had
ever traded (8%), implying **~128 tradeable tokens touched that day**. So 5,000
tokens is roughly **40 days of Base history**.

**Consequence:** no change to the proposal's target is needed on this ground,
and Base survives as the recommendation. Phase 1 still builds 100 tokens.

**Still imprecise, deliberately:** 8% on n=60 is an order-of-magnitude
estimate, and none of those five tokens was *first* paired that day — a V4
`Initialize` is often a second pool for an existing token. "Tradeable tokens
touched per day" is what the measurement supports; a strict birth census needs
each token's first-ever pool.

**Method note for later phases:** event topics are now computed with a pure
python keccak (`backend/spikes/keccak.py`), self-tested against the canonical
`Transfer` topic, rather than copied from memory or a blog post. Part B should
carry that habit over — three of the topics I had hardcoded were right, but
only checking proved it.

## OPEN — The 24-hour feature cutoff

Not yet argued. The spike measured first-24h volumes because the brief
specified them, and the write gate is built around `as_of_ts`, but the choice
of 24 over 1 or 72 hours has not been justified and belongs in Phase 2, where
label leakage is the live question. One datum in favour so far: in the single
launch with real first-hour trading (gSPEED), 36 distinct wallets bought inside
hour one, so an hour is enough to have a population to measure — but only on
the liveliest launches.

## OPEN — The X post budget (resolved 2026-10-19: no budget, see the end of this file)

Not set. `ingest/xapi.py` is not to run in Phase 1 at all. The number needs to
be a hard integer in config before that module is switched on.

---

# Phase 1, Part B — ingestion and store (2026-10-11)

## Chain: Base, on free keyless sources

Confirmed by the user after Part A: "i wanna do unpaid work". Base survives
that rule, with one correction to how Part A phrased it — *Etherscan V2 on
Base* is paid, which is not the same as *Base* being paid. Everything Phase 1
needs comes from a public RPC gateway and DexScreener, neither of which takes
a key:

| Need | Source | Key? | Measured limit |
|---|---|---|---|
| transfers, swaps, pool creation | `base.gateway.tenderly.co` | no | 1,000-block ranges, 20,000 results |
| symbol, liquidity, dollar price | DexScreener | no | 60 req/min |
| asset transfers (optional) | Alchemy | yes | **off**: inert without `ALCHEMY_API_KEY` |

## Discovery is on-chain, not DexScreener-led

The brief had DexScreener's new-token feeds driving discovery. They cannot:
Part A measured **zero Base tokens across 60 rows** of those feeds, and the
search endpoint returns established tokens rather than launches.

So `discover_pools` reads pool creation straight from the chain — Uniswap V4
`Initialize` on the singleton PoolManager, and V3 `PoolCreated` on the factory.
Measured on 2026-10-11 over a 1.5-hour window 26 hours old: **99 candidate
tokens, 95 of them V4**. DexScreener had indexed **20 of the 99**. A launch is
visible on-chain long before any aggregator sees it, which is the whole
premise of the project, and this is the first direct evidence for it.

## Uniswap V4's singleton forced two design choices

V4 has no per-pool address: every pool on Base emits from one PoolManager and
that contract holds every pool's funds. Two consequences, both load-bearing:

1. **A V4 pool is keyed by its pool id**, not by an address. Keying it by the
   PoolManager would collide every V4 pool in the `pair` table onto one row.
   The PoolManager is still the address a transfer shows as counterparty, so
   the code carries both: `pair_key` (ours) and `counterparty` (the chain's).
2. **Its swaps need a second, topic-filtered call** per window. Adding the
   PoolManager to the address filter would return every V4 swap on Base.
   That call is skipped in any window where the token itself did not move —
   a swap of a token cannot exist where the token did not move — which halves
   the cost of a V4 backfill and loses nothing. Most new pools never trade.

## Block timestamps come free, and that decides the cost model

The gateway returns `blockTimestamp` on every log. Without it, a token active
in 500 distinct blocks would cost 500 `eth_getBlockByNumber` calls on top of
its 44 log calls — an order of magnitude more than the backfill itself, and
enough to change what a free tier can do. Measured cost per token-window:
**44 calls**, or 88 where a V4 pool actually traded. The per-block fallback is
kept for endpoints that omit the field.

## `wallet_address` on a swap stays NULL

Part A proved the transfer counterparty on an aggregator route is the router,
not the trader. Recording the router as the wallet would quietly poison every
wallet-level metric the project exists to compute. The column is null until
Phase 3 can pay for receipts or traces. Swap **direction** is still correct:
it is read from the token's own transfers to and from the pool rather than
from the event's sign, which differs across V2, V3 and V4.

## `price_usd` only for stablecoin-quoted pools

A WETH-quoted price is not a dollar price and Phase 1 has no historical ETH
price. The column is null rather than carrying a number that looks like
dollars. `quote_amount` is always recorded, so the price can be derived later
when an ETH series exists.

## Amounts are unconstrained numerics

`Numeric(38, 18)` for amounts and `Numeric(38, 12)` for prices both broke
against real Base data on the day they were written:

* a token minting 10^30 units gave DexScreener an FDV above 10^26, which
  overflows precision 38 and aborts the whole insert;
* a dust memecoin's price is routinely below 10^-12, which scale 12 rounds to
  **zero** without complaining. That is the worse failure of the two, because
  a zero price reads as a fact rather than as a lost digit.

Migration `f7b2c337d10e` widens both to unconstrained `NUMERIC`. `raw_value`
stays `NUMERIC(78, 0)`, because uint256 has an exact bound. A fixed scale
anywhere else would be a claim about magnitudes this project does not get to
make — it reads whatever anyone chose to deploy.

## The write gate coalesces rather than overwrites

Every writer here is a partial observer: the chain knows a token's decimals
and nothing about its name, DexScreener knows the name and never reports
decimals. `SET col = excluded.col` therefore erased a correct decimals the
moment enrichment ran — caught by a test, not in production. Nullable columns
now take `COALESCE(excluded.col, existing.col)`: a new value wins, an absent
one leaves the old alone. Required columns are overwritten outright, since no
writer can be missing those.

## Deviations from the brief, stated plainly

| Brief said | Built | Why |
|---|---|---|
| DexScreener drives discovery | chain drives discovery, DexScreener enriches | its feeds carry zero Base tokens |
| `docker compose` for PostgreSQL + TimescaleDB | compose file written; dev store is a portable PostgreSQL 16.10 on 127.0.0.1:5433 | Docker needs rights this account lacks; the timescaledb DLL will not load on 16.10 |
| hypertable on `pair_snapshot` | guarded: created only where the extension is installed | a plain table answers every Phase 1 query correctly, just slower |
| seven tables | nine | `budget_ledger` persists monthly spend across restarts; `backfill_checkpoint` makes a crashed backfill resumable. Both are required by the brief's own budget and resume rules, neither is inferrable from the other seven. |
| swaps possibly need a second source | decoded from pool events in the same scan | they arrive free in the log window the transfers already cost |

## One failure worth recording

The first run to hit the numeric overflow left **no record of itself**: the
bookkeeping in `run_scope`'s `finally` block tried to write to a session
PostgreSQL had already aborted, so `ingest_run` row 3 is stuck at `running`
with zero calls. It is left in the table as the evidence it is. The runner now
rolls back before recording a failure, and a failed run writes its own error
text — which is the only reason the overflow was diagnosable at all.

## Measured consequence: almost nothing gets a dollar price

Of the first 2,064 swaps decoded, **1** carried a `price_usd`. Base launches
are quoted in ETH or WETH, not in stablecoins, so the stablecoin-only pricing
rule above leaves the column null nearly everywhere. `quote_amount` is
populated on **every** swap (zero nulls), so no information is lost — but
turning quote amounts into dollars needs a historical ETH/USD series, and
that is now a **prerequisite** for any PnL work rather than a nicety.

Part A measured a free fallback for exactly this (Etherscan V2 for EVM
prices, Helius for Solana), so the path exists; it just has to be built.

## Acceptance run, 2026-10-11

| | |
|---|---|
| complete 24-hour windows | **159** (target was 100) |
| transfers | 64,354 |
| swaps | 15,628 |
| wallets | 12,158 |
| RPC requests, whole project, this month | 6,035 |
| DexScreener requests | 7 |
| cost | nothing; no key was used |

Measured cost per token-window: **44 calls**, rising to 85 only where a V4
pool actually traded. One run of 95 windows took 20 minutes and 4,760 calls,
with 42 seconds of that spent waiting on our own rate limiter.

## Verified on the stored rows, not just in tests

| Check | Result |
|---|---|
| transfers dated after their window's `as_of_ts` | **0** |
| transfers before their pool's creation block | **0** |
| swaps with a null `quote_amount` | **0** |
| wallets claiming to know their funding source | **0** |
| rows with a provenance other than `live` | **0** |
| re-ingesting 3 complete tokens (checkpoints deleted, 8,234 transfers and 141 calls re-spent) | whole store byte-identical: same counts, same MD5 over every transfer row |
| resuming a backfill killed mid-window | restarted at block 52,444,939 rather than the window's start 52,417,939 — 17 calls instead of 44 |
| buy/sell split across early launches | 1,555 buys to 509 sells |

## Still OPEN

* **An ETH/USD series** — see above. Without it, `quote_amount` cannot become
  a dollar figure and no PnL metric can be computed from swaps.
* **The 24-hour cutoff** — unchanged from Part A: still unargued, still a
  Phase 2 question. `FEATURE_WINDOW_HOURS` is config, so changing it is a
  one-line change plus a re-run.
* **The X post budget** — still unset, still **0**. `ingest/xapi.py` is built
  and tested against a recorded fixture, and was not run in Phase 1.

---

# Phase 2 — the labelled dataset (2026-10-13)

Evidence: `backend/spikes/B_FINDINGS.md` and the five `B*.json` files beside
it. Thresholds and class counts: `backend/reports/label_sensitivity.md` and
`backend/reports/dataset_card.md`.

## The gate fired first: Phase 1's tokens were two days old

The brief said to fix this before labelling anything, and it was right to.
All 159 backfilled windows at the start of this phase launched on 2026-10-10
or 11. Five tokens in `token` were old enough, and all five were established
majors that arrived through DexScreener enrichment rather than launches
discovery found.

Fixed by re-pointing discovery at a historical window
(`discover --offset-hours 2280`, i.e. 95 days back). The node serves logs
that far back without complaint — V4 `Initialize` returns 74 pools per 1,000
blocks at −90d and 492 at −180d — so candidate supply was never the problem.

## Labels are sampled, not reconstructed

**The brief's method could not be afforded, and its premise was wrong.** It
specified accumulating quote-token transfers "using the same
`alchemy_getAssetTransfers` path Phase 1 settled on". Phase 1 settled on no
such thing: Part A left `getAssetTransfers` **unverified** for want of a key,
and Phase 1 runs on keyless `eth_getLogs`.

Measured alternatives for a 90-day reserve history:

| Approach | Calls per token | 200 tokens |
|---|---|---|
| transfer reconstruction, our gateway | 3,888 | 777,600 |
| transfer reconstruction, PublicNode (10k ranges) | 389 | 77,800 |
| **archive `eth_call` sampling** | **90–232** | **~30,000** |

The 1,000-block cap is absolute — neither an address filter nor a topic
filter relaxes it. PublicNode's 10,000-block range worked for about four
minutes and then returned `403` to everything, having rate-banned the probe.
Blockscout's public API returns `403` to both API versions, browser
user-agent included.

So reserves are **read** at a block rather than accumulated.
`balanceOf(quote, pair)` at a historical block *is* the quote reserve, and
archive `eth_call` answers at least 365 days back on the free endpoint:
90 daily points in 42.7 seconds, measured.

This is the more accurate of the two, not a compromise. A cumulative sum is
only correct if every transfer across 90 days was captured, and one missed
window silently biases every later point with no way to notice. Each sampled
balance is independent and exact.

**What is given up** is resolution: daily sampling locates a collapse to a
day, not a block. That is why the sampler is dense (6-hourly) over the first
week, where launches actually die, and daily thereafter.

## Uniswap V4 needed its own method, and it is most of the chain

V4 keeps every pool's funds in one PoolManager — 4,211 WETH across all pools
at once — so a per-pool *quote* reserve does not exist to be read, and
`getLiquidity` returns active-at-tick liquidity, which reads 0 for a pool
with 334 swaps whenever price has left the positions. V4 is 95% of what
discovery finds on Base (95 of 99 candidates in one sampled window), so
excluding it would have meant excluding the dataset.

The asymmetry is the way in: the PoolManager holds **one token** only on
account of pools containing that token. For a launch with a single pool,
`balanceOf(token, PoolManager)` is that pool's token reserve exactly.

**Verified rather than assumed.** Spike B6 compared it against Phase 1's own
stored transfers — the net flow into the PoolManager across each token's
first 24 hours against the balance at the window's end — for five tokens:
**exact to the wei on all five, and all five had exactly one V4 pool.** That
check also independently confirms Phase 1's transfer ingestion is complete,
since a single missing transfer would have broken the equality.

Price on V4 comes from `extsload(poolStateSlot)` on the PoolManager. The
official StateView was called on the same pool and returned byte-identical
slot0 (`tick=160545`), which is how its address was confirmed —
`0xa3c0c9b65bad0b08107aa264b0f3db444b867a71`, of three published candidates,
the other two returning nothing. Taken from a list it would have been a
guess; agreeing with an independent method makes it a measurement.

**Consequence for the definition:** the reserve criteria read the **token**
side, uniformly, on every venue. That is a departure from the brief's
quote-side rule, and it separates the two cases *better*: withdrawing
liquidity removes both sides, so the token reserve collapses, whereas a
sell-off **raises** it. A quote-side rule cannot tell those apart by sign.

## Activity is measured in days the price moved, not swaps

`DEAD` and `STILL_LIVE` were specified on swap counts. A count needs a log
scan — 1,296 calls per token for 30 days, 14× the cost of the entire price
series. A pool with no swaps has an unchanged tick, so "days on which the
price moved" falls out of samples already taken, for **free**.

It measures trading activity, which is what `DEAD` reaches for; the swap
count was itself only a proxy for that. It is **coarser** — a day with one
swap and a day with four hundred look alike — and that is stated in the
dataset card rather than buried. If the count itself turns out to matter, it
has to be paid for.

## Pools that never traded are excluded, not labelled

Measured: 42 of the first 66 historical tokens had **zero** swaps in their
first 24 hours, and 300 of the tokens discovery found carry vanity-mined
addresses of a single spam family (`0xb2000000…`), each with a pool and no
trades.

A pool nobody ever traded in is evidence about pool spam, not about rug
pulls. Left in, it would dominate every class count and the base rate would
describe a bot rather than a market. So `NEVER_LAUNCHED` — the brief's own
exclusion class — is extended to cover "never traded", and the dataset card
reports the count rather than hiding it.

## Two integrity rules added after they were needed

**Age is decided by block number, not by `created_ts`.** Those two disagree
in the real store: Phase 1's enrichment fills `created_ts` from DexScreener's
`pairCreatedAt`, which describes whichever pool DexScreener indexed, while
`created_block` comes from the pool discovery actually found. One token
carries a block from three days ago and a timestamp from 369 days ago.
Filtering on the timestamp let it through, and the sampler then ran off the
end of the chain. A block number on a two-second chain *is* a time, and it
is the one the block arithmetic uses.

**Poor coverage yields UNCLEAR, never a confident verdict.** The first
working version labelled a token `FAILED` on 12 usable observations out of
112, because a failed `balanceOf` was swallowed silently. Failures are now
recorded on the observation, and a row with under 80% usable samples is
UNCLEAR with a note. That is a claim about our data, kept distinct from
`NEVER_LAUNCHED`, which is a claim about the token — one belongs out of the
dataset and the other belongs in it.

## Sampling is adaptive, and why that is safe

A coarse pass of nine points costs 18 calls. If reserve and price are
**identical at every one of them**, the dense grid is skipped: a swap moves
the price and a liquidity event moves the reserve, so a pool reading exactly
the same at nine points across 90 days had neither in between. A pump that
returned to precisely its starting price *and* reserve, to the wei, after
fees, is not a thing that happens.

Measured: 224 calls and 58 seconds becomes 18 calls and 5. In practice the
saving applies mostly to tokens the activity floor now excludes anyway, so
labelled tokens still cost ~232 calls each.

## The observations are stored on the row

`token_label.series_json` holds the sampled series. Without it the
sensitivity sweep cannot move the observation window at all — that threshold
is not recoverable from summary measurements — and every other sweep would be
re-derived from numbers rather than from observations. With it, the entire
sensitivity analysis runs offline.

## Deviations from the brief, stated plainly

| Brief said | Built | Why |
|---|---|---|
| reconstruct reserves from quote-token transfers via `getAssetTransfers` | sample reserves with archive `eth_call` | no Alchemy key exists; reconstruction costs 3,888 calls/token and is less accurate |
| quote-side reserve | token-side reserve, uniformly | V4 has no readable per-pool quote reserve, and the token side separates a withdrawal from a sell-off by sign |
| `swaps_last_30d` | `active_days_last_30` | a swap count costs 14× the whole price series; price movement is free and measures the same thing more coarsely |
| `LIQUIDITY_PULLED` requires the outflow to reach the deployer or its cluster | criterion measures the reserve only; destination stored as evidence | funding clusters are Phase 3, and a criterion must not claim what it did not measure |
| `NEVER_LAUNCHED` = never reached a liquidity floor | also covers never traded | pool spam has liquidity and no trades, and dominates the chain |
| verify reserve reconstruction against a block explorer | verified against Phase 1's own stored transfers | Basescan is paid and Blockscout returns 403; the transfer check is stronger and reproducible |

## Phase 2 results, and the thresholds argued against them

46 tokens labelled at `v1-2026-10`: **20 RUG (43.5%), 24 FAILED (52.2%),
1 UNCLEAR, 1 NEVER_LAUNCHED**. Base rate **44.4% RUG** of the usable set.
10,857 calls, 512 s of that waiting on our own rate limiter.

**No SURVIVED tokens at all.** Of 46 traded launches from 95 days ago, not
one still held a quarter of its peak liquidity and still traded. That is a
finding about Base launches, not a bug: the sensitivity sweep shows a single
token becoming SURVIVED if `LIVE_ACTIVE_DAYS` drops from 8 to 6, so the
class is reachable and simply empty here. It also means a model trained on
this set cannot learn what survival looks like, which is a limitation of the
dataset and is stated in the data card.

### Every threshold, against the sweep

`reports/label_sensitivity.md` has the full tables. The defensible claim is
not "these numbers are right" but "the answer does not depend on them":

| Threshold | Value | Neighbours | Why this value |
|---|---|---|---|
| `LIQUIDITY_DROP_FRACTION` | 0.90 | flat 80–99% | Sits mid-plateau. Every RUG in the set has a drop of **exactly 1.0** — the pool went to zero, not to 10% — so any cut between 0.8 and 0.99 gives the same answer. 0.70 pulls in one extra token. |
| `COLLAPSE_FRACTION` | 0.05 | flat 1–20% | Changes nothing anywhere in the range. It is inert on this set because a drained pool's price *stops* rather than falls (see below), so collapse is never the deciding criterion. |
| `DEAD_ACTIVE_DAYS` | 2 | flat 1–5 | 0 is degenerate — "fewer than zero active days" is unsatisfiable, so nothing is DEAD and 52% of the set falls to UNCLEAR. That 52% is an artefact of sweeping past the bottom of the scale, not evidence of instability. |
| `LIVE_ACTIVE_DAYS` | 8 | moves 1 token | The only threshold whose neighbour disagrees, and it decides whether one token is SURVIVED or UNCLEAR. 8 keeps the stricter reading. |
| `LIVE_RESERVE_FRACTION` | 0.25 | flat 10–60% | Inert: nothing in the set is near the boundary. |
| `MIN_USABLE_FRACTION` | 0.80 | flat 50–90% | At 100% one token becomes UNCLEAR, since one of its 116 observations failed. Demanding perfect coverage would discard a token for a single transient RPC error. |
| `MIN_SWAPS_IN_WINDOW` | 1 | — | Not swept: it is an inclusion rule, not a classifier threshold. Its effect is reported as the exclusion count instead (46 of 137 eligible tokens traded at all). |

### Why 90 days and not 30 or 180

This is the one threshold that genuinely matters, and the sweep says so:
**30 days reclassifies 10.9% of the set, 60 days 2.2%, 90 days is the
baseline.** Shorter windows turn five tokens from FAILED into UNCLEAR,
because a pool that is quiet for a month is not yet distinguishable from one
that is merely slow.

180 days was not swept, for an honest reason rather than a principled one:
the observation window has to close before today, so a 180-day window would
restrict the set to launches from before mid-April and the historical
discovery pass targeted 95 days back. Extending it is a re-run of discovery
at a deeper offset, not a threshold change.

### Migrations caught: zero

`possible_migration` fired on **0 of 46** tokens — no token had a sibling
pool appear within 7 days of liquidity leaving. So no RUG verdict in this
set was withheld on migration grounds.

That number is honest but weak evidence, for a reason worth stating: sibling
pools are counted from our own `pair` table, which contains only pools that
discovery found. A migration to a venue we do not watch, or to another
chain, would be invisible and would read as a rug. The check is implemented
and tested; it has simply not been exercised by this data.

### Why RUG and FAILED stay separate

The contrast in the rows is stark enough to make the case on its own:

* a RUG: peak reserve 1,000,000,000 → **0**, drop 1.0, six hours after launch;
* a FAILED: peak 500,000,000 → **499,999,709**, drop 0.0000, liquidity still
  sitting in the pool three months later, and nobody ever traded it.

Those are not two degrees of the same event. One is a withdrawal, the other
is indifference. Collapsing them teaches a model "this went down", which is
not worth predicting. The binary target is RUG against the rest and that
collapse belongs at training time.

### Three things reading the rows revealed

**1. Sampling understates the peak, in 40% of cases.** For 8 of 20 RUGs the
largest single outflow recorded in the feature window is *larger than the
sampled peak reserve* — one shows an outflow of 100e9 against a sampled peak
of 4.9e9. The pool held more at some moment between two samples than at any
sample. This is the concrete cost of sampling over reconstruction, and it is
worse than the generic "resolution" caveat first recorded: peak-relative
criteria are measured against a floor on the peak, not the peak. It does not
change any verdict here, because the RUG criterion only needs the drop to
exceed 90% and these drops are 100%, but any future criterion that depends
on the peak's *magnitude* cannot use this column as-is.

**2. A drained pool's price stops rather than falls.** `slot0` keeps its last
value forever once liquidity is gone, so `peak_price == price_at_end` on
every RUG and `SUSTAINED_COLLAPSE` never fires for them. That is why the
collapse threshold is inert. The label is still right, and it is right for
the reserve reason rather than the price reason — which is exactly why the
criteria are stored separately instead of as one score.

**3. Every RUG drop is timestamped at launch + 6 hours.** That is the second
sampling point, not the moment of the drain. The reserve already read zero
when first re-measured, so the drain happened somewhere inside the first six
hours and `largest_drop_ts` is an upper bound, not an observation. For
locating a rug in time, the early grid would need to be minutes, not hours.

**4. Some V4 prices are absurd in magnitude** — one reads 3.4e38. Prices are
derived from `sqrtPriceX96` without a decimals correction, which is sound
for comparing a token against its own peak (a constant factor cancels) and
meaningless as an absolute. Stored as-is and used only ratio-wise; this is
why `price_usd` on a swap and `price` here are different things.

## Still OPEN

* **An ETH/USD series.** Unchanged from Phase 1 and now load-bearing: prices
  here are ratios against each token's own quote asset. Honest for comparing
  a token to its own peak, useless for anything cross-sectional in dollars.
* **The X post budget.** Still 0, still not run.

---

# Phase 3 — the wallet graph (2026-10-13)

Module docs: `backend/blocklens/graph/README.md`. Evidence:
`backend/reports/cluster_validation.json` and `cluster_cases.md`.

## Part A could not be built as specified, and the arithmetic says why not

The brief asked for the number before anything ran. It is:

| | |
|---|---|
| wallets in scope | 14,097 |
| `getAssetTransfers`, one page each, at 120 CU | 1,691,640 CU |
| against a 30M free month | **5.6%** |

Comfortably inside the 20% ceiling. **The spend was never the obstacle** —
there is no Alchemy key in this environment, Part A established one cannot
be created here, and so the allowance to spend against is zero.

No keyless substitute exists for "every inbound transfer to this address,
ever". Native ETH funding leaves no log to filter, and `eth_getLogs` is
capped at 1,000 blocks however narrowly the query is written. An indexing
API is exactly the thing a JSON-RPC node is not.

**What was built instead:** edges from the 56,296 wallet-to-wallet transfers
Phase 1 already stored — the first non-infrastructure address to send each
wallet a token. That is **token-acquisition provenance, not ETH-funding
provenance**, and the difference is stated at the top of the module README
rather than glossed. Consequences, in full:

* a wallet that only ever bought from a pool is `unknown`, never `fresh` —
  how it got its gas is precisely what cannot be seen;
* `cex` and `bridge` are **0%**, because the CEX list is empty;
* two wallets funded from one exchange hot wallet are invisible as a pair,
  and would have been under the brief's method too.

## The address lists, and the one that is empty

`graph/known_addresses/` holds `routers.json` (10), `bridges.json` (3),
`burn.json` (2) and `cex.json` (**0**).

The CEX list is empty and that is the honest state, not an oversight.
Attributing a Base address to a named exchange needs a labelled source and
every one of them is paid or blocked here — Basescan is paid, Blockscout
returns 403 to both API versions including with a browser user-agent
(spikes B2, B3). Guessing at addresses and filing the guesses as curated
data would have been worse than leaving it empty, because the coverage
figure would then have been fiction.

The measured consequence is reported in the funding distribution rather than
absorbed, and the mitigation is empirical: every address funding more than
50 wallets is profiled and listed for review.

## Degree alone was the wrong test, and it emptied the graph

The brief says any address funding more than a threshold number of wallets
should be flagged before it is allowed to create edges. Implemented as a
flat exclusion, that produced **451 edges from 14,507 wallets** — a graph
with nothing in it.

The reason is that wallet count conflates two opposite things:

| Address | Wallets | Tokens | Wallets/token | What it is |
|---|---|---|---|---|
| Uniswap V4 PoolManager | 3,366 | 219 | 15 | infrastructure |
| LI.FI / Jumper | 143 | 16 | 9 | infrastructure |
| `0xd152f549…` | 5,400 | **5** | 1,080 | disperser |
| `0xe9132055…` | 942 | **1** | 942 | disperser |

Infrastructure serves the whole chain, so it touches many tokens. An address
touching thousands of wallets across a handful of tokens is distributing
something specific — which is the sybil pattern this module exists to find,
and excluding it discarded the largest structure in the dataset.

**Decision:** `INFRA_MIN_TOKENS = 20` and
`DISPERSER_MIN_WALLETS_PER_TOKEN = 20`. Infrastructure creates no edges;
dispersers create edges and are flagged. Whether a disperser's fundees are a
farm or a genuine airdrop is **not** settled by this rule — it is settled by
whether they co-move, which is what the validation measures. Splitting this
way took the graph from 451 edges to **14,525**.

`HIGH_DEGREE_FUNDER = 50` is the threshold at which an address gets profiled
rather than trusted. It is a trigger for classification, not a verdict.

## Co-purchase window: 300 seconds

Two reasons, and the second is the binding one. The activity on a fresh
launch is minutes-scale, so a window much wider than that connects everyone
to everyone — in the first hour of a token nearly every buy is within
minutes of another. A window much narrower than a block or two measures
block inclusion rather than intent.

The window is stored on every edge it creates, because a co-occurrence edge
is meaningless without knowing the window it was drawn with. A crowd is
capped at `MAX_CO_PURCHASE_CLIQUE = 60` simultaneous buyers rather than
turned into a clique of millions of meaningless pairs.

## Hop limit: 2

Each hop multiplies the neighbourhood and dilutes the signal. At two hops a
wallet already reaches its funder's *other* fundees, which is the
relationship the whole method rests on — and the undirected walk is what
makes siblings reachable at all, since a directed walk would never connect
two wallets fed by the same address.

At three hops, on a graph containing 5,000-wallet dispersers, nearly every
wallet reaches nearly every other and the feature stops distinguishing
anything. The cited paper also stops at two.

## Community detection: Louvain, after a reversal

Greedy modularity (Clauset-Newman-Moore) was chosen first and documented,
on the argument that it is deterministic by construction while Louvain needs
a seed — the stronger guarantee. It did not survive the real graph: **CNM
failed to complete on ~15,000 nodes and ~96,000 edges in over ten minutes.**

An algorithm that does not finish has no determinism to offer. Louvain with
`SEED = 20261013`, fixed in the source rather than passed per invocation,
reproduces the same assignments for the same graph, and `test_graph.py`
asserts three consecutive runs agree. The trade, stated plainly: CNM gives
determinism without a seed and is unusable here; Louvain gives determinism
conditional on the seed, in seconds.

## Features: 95, in two layers

21 base features per wallet, then 37 aggregates at each of one and two hops
(`mean`, `max`, `std` over 11 propagated base features, plus counts and
neighbourhood degree shape). Named systematically — `base_*`, `h1_mean_*`,
`h2_max_*` — so Phase 4's feature importance reads without a lookup table.
The brief targeted around seventy; 95 is the same order.

Position values are in **quote units**, not dollars, and a trade's price
comes from joining the wallet's transfer to the pool's `Swap` event in the
same transaction — the only way to price a wallet's trade given that
`swap.wallet_address` is null by design.

`hops_from_cex` is implemented and correct and returns almost nothing,
because the CEX list is empty. The feature exists so that populating the
list later fills it in without touching the code.

## Deployers are inferred, not read

Phase 1 never captured `creator_address` — discovery reads pool creation,
not contract creation. It is inferred here from the recipient of each
token's first mint out of the zero address. Measured: **all 408 tokens with
a mint sent it to a wallet, never to a pool**, which is what a deployer
minting to themselves before adding liquidity looks like.

It is an inference and not a receipt. Reading the creation transaction would
be proof and needs a transaction index unavailable keylessly, so
`insider_reason` says "initial supply holder" rather than "deployer".

## Two bugs that would have become false findings

**1. The first co-movement lift read 0.00**, and the validator's own verdict
printed "LIFT IS NEAR 1: the clustering is not finding co-movement. Report
this rather than tuning thresholds." Reporting it would have been a
fabricated finding about Base. The cause was one join: `load_buys` matched
`transfer.from_address` against `pair.address`, but a V4 pair row is keyed by
its 32-byte pool id, which never appears as a transfer counterparty. V4 is
~95% of the dataset, so the query found **19 buys in total** instead of
5,509. The same singleton problem as Phase 2's sampler, in a different
query.

**2. A 107,000-row upsert did not finish.** The write gate built one
statement for every row with a `RETURNING` clause on each, which is fine at
the hundreds Phase 1 writes per window and not fine at Phase 3's edge count.
Writes are now batched at 5,000 rows, which benefits every table.

## The measured co-movement lift, and what it rests on

The number the brief wants recorded, because it is the evidence the module
works. Both measurements, with their controls, from
`reports/cluster_validation.json`:

| Measurement | Pairs | Cluster rate | Baseline | **Lift** | Shuffled lift | Collapse | p |
|---|---|---|---|---|---|---|---|
| buys only (as specified) | 40 | 7.5% | 2.1% | **3.63** | 0.26 | 0.071 | **0.050** |
| buy or sell | 155 | 7.7% | 1.7% | **4.66** | 0.23 | 0.050 | **1.3e-05** |

Positive control: a known funder with 40 fundees, recovered as a single
41-member component — **PASS**.

Read these together, because separately each one misleads:

* **The lift is real.** Wallets in a provable cluster buy or sell the same
  token within five minutes of each other 4.7× more often than random pairs
  from the same population, and the degree-preserving shuffle drops that to
  0.23 — a collapse to 5% of the measured value. So the lift is a property
  of *who is connected to whom*, not of the graph's shape.
* **The brief's exact metric is underpowered on this data.** Buys only gives
  3 co-moving pairs out of 40, p = 0.050 — sitting exactly on the
  conventional threshold, which is not a number to build on. Widening to any
  market action gives 12 of 155 at p = 1.3e-05. Coordinated *selling* is
  the behaviour the module is for, so the wider metric is the better test
  rather than a convenient one, but the narrow result is reported too.
* **An early figure of 11.6 was an artefact and should be ignored.** It came
  from 13 comparable pairs before the dataset grew. The better-powered
  estimate is lower, which is the usual direction for a ratio measured on
  almost no events.

`LiftResult.p_value` now computes the binomial tail, so the report carries
its own significance rather than leaving a reader to work out whether a
ratio built on twelve events means anything.

## The finding that constrains Phase 4: the big clusters are dormant

The five largest provable clusters hold **13,975 wallets and 22 traders
between them**:

| Cluster | Wallets | Ever traded |
|---|---|---|
| 1 | 5,402 | **1** (0.0%) |
| 2 | 4,419 | 14 (0.3%) |
| 3 | 2,039 | 5 (0.2%) |
| 4 | 1,166 | 2 (0.2%) |
| 5 | 949 | **0** (0.0%) |

Across all 134 clusters, only **26 contain two or more wallets that ever
traded**; 108 are dormant, holding 6,904 wallets between them.

These are mass airdrop distributions to addresses that never did anything,
not sybil trading farms. The funding relationship is real — one address fed
5,400 wallets — but the actor behind it is distributing tokens, not
operating wallets.

**What this means downstream, stated before Phase 4 can trip over it:**

1. `cluster_size` as a feature would mostly encode *"was this wallet on an
   airdrop list"*, not *"is this wallet part of a trading operation"*. A
   model given it will learn the former, which is nearly useless for
   predicting a rug, and the feature's apparent importance would be
   misleading.
2. The lift is carried entirely by the 26 clusters that can carry evidence.
   Restricting the measurement to them gives the identical 4.66, which
   confirms the dormant clusters contribute nothing either way rather than
   diluting the result.
3. A cluster-quality signal — members who traded, not members — is the
   version of this feature worth using, and it is already available from
   these columns.

This is not a failure of the method. It is a finding about Base: the
dominant multi-wallet pattern here is airdrop distribution, and whatever
coordinated trading exists sits in much smaller groups. Reporting it the
other way round, with a 5,402-wallet "cluster" as a headline, would be the
dishonest reading.

## Acceptance figures

| | |
|---|---|
| funding edges | 14,528 |
| co-purchase edges | 111,705 |
| graph nodes | 17,599 |
| provable clusters (layer 1) | 134, largest 5,402 |
| communities (layer 2) | 141 |
| `wallet_feature` columns | 95 (21 base, 37 per hop) |
| wallets classified | 19,422 |
| insider-linked | 1,190 from 88 inferred deployers |
| **compute units consumed this phase** | **0** |

Funding source distribution, with the gap that matters:

| Source | Wallets | Share |
|---|---|---|
| `cluster` | 14,507 | 74.7% |
| `unknown` | 4,899 | 25.2% |
| `fresh` | 16 | 0.1% |
| `cex` | **0** | **0%** |
| `bridge` | **0** | **0%** |

`cex` and `bridge` are zero because the exchange list is empty and the
bridge list covers only the OP Stack predeploys. 50 heavy funders are
unlisted and flagged for review. A wallet a real exchange funded is counted
somewhere else in this table, which overstates `cluster`, and that is the
single largest known error in the distribution.

Zero compute units: nothing in this phase touched a metered API, so the
monthly allowance is untouched and the 5.6% the brief's method would have
cost was never spent.

## Known limits, recorded as required

* Funding through a centralised exchange **breaks the trace completely**.
  Two wallets funded from the same hot wallet are not evidence of one actor,
  because the exchange's ledger is off chain. We cannot follow it and do not
  claim to.
* Peel chains beyond two hops are not followed, so their actors are not
  grouped. The hop limit is 2 and the reason is above.
* The exchange list is **empty** and the bridge list covers only the OP
  Stack predeploys. Coverage: `cex` 0%, `bridge` 0% of classified wallets.
* **We group pseudonymous addresses. We do not attempt to identify people.**
  This is structural rather than a policy: no code in the module joins to a
  name, handle, IP or KYC record, and no column in `wallet`, `graph_edge` or
  `wallet_feature` can hold one. The curated lists name contracts, never
  persons. The strongest claim available about a wallet is that it moved
  tokens in a pattern shared with other wallets.

---

# Phase 4 — the risk model (2026-10-13)

Built without a brief, on my own judgement, after measuring that the dataset
would not support what a brief would most likely have asked for. Artefacts:
`backend/reports/model_card.md` and `model_results.json`.

## The headline is a negative result, and it is about Phase 3

**Propagated graph features do not improve prediction on this data, and
graph structure alone is indistinguishable from noise.**

| Feature group | Logistic AUC | Boosting AUC |
|---|---|---|
| structure only (7f) | **0.585** ± 0.077 | 0.584 ± 0.077 |
| timing only (14f) | 0.793 ± 0.154 | **0.970** ± 0.027 |
| both (21f) | 0.798 ± 0.151 | 0.970 ± 0.027 |

Permutation null, labels shuffled at token level, 25 rounds: AUC
**0.548 ± 0.086**, 95th percentile **0.698**. Structure-only at 0.585 sits
inside that null. It is not a weak signal; it is no signal.

And the ablation that was supposed to be the project's central result:

| Feature set | AUC (leakage removed) |
|---|---|
| flat, own behaviour only | 0.796 ± 0.153 |
| + 1 hop | 0.798 ± 0.152 |
| + 2 hops | 0.798 ± 0.151 |

A difference of **+0.003** against a fold-to-fold spread of **±0.15**. The
cited F1 0.93 against 0.81 does not reproduce here.

**What that does and does not mean.** It does not mean the paper is wrong or
that propagation is useless. With 44 tokens the experiment cannot resolve a
difference that size — the honest statement is *not detectable at this
sample size*, and it would have been just as wrong to report a flattering
difference of +0.003 as a confirmation. What it does mean is that Phase 3's
features cannot currently be claimed to earn their place, and that saying so
now is cheaper than discovering it in a viva.

All of the measurable signal is in **entry timing**: wallets that buy sooner
after a launch are trading tokens that go on to be rugged. The fitted
coefficients agree — `base_entry_delay_mean` at -1.74 dominates everything
else, with `base_in_degree` a distant +0.16.

## The leakage problem, which had to be solved before any of that meant anything

**64 of 85 features were removed before training.** Not a tuning decision —
a structural one.

Phase 2 assigns `FAILED` partly through a `DEAD` criterion computed from
whether the price moved, which is to say from whether the token traded.
Almost every behavioural feature measures how much a wallet traded. So the
features and the label are computed from overlapping evidence, and a model
fed both learns a tautology.

The audit found it by measurement: **`base_buy_quote` scored AUC 0.922 on
its own.** It is zero exactly when no priced swap exists for a wallet, which
is the same condition that sends its token to FAILED. The same applies to
every money, holding-time and behavioural-flag feature — each needs trades
to be non-trivial.

With those in, the model reports AUC **0.97-0.98**. That number is in the
model card, labelled as what it is, because deleting it would hide the size
of the effect; and it must never be quoted as a result.

**One suspicion that turned out to be unfounded, and is recorded because the
check is the point.** Entry delay survived the audit, but a token with 89
traders has a smaller *minimum* entry delay than one with 2, purely by order
statistics — so entry timing could have been a wallet-count proxy, which is
a count, which is the leak again. Measured: the correlation between a
token's wallet count and its minimum entry delay is **-0.127**. Too weak to
explain an AUC of 0.79. The feature stays.

## Design decisions, and why

**The unit of observation is a wallet, grouped by token.** 44 tokens against
85 features is p > n; a token-level model would be describing 44 points. At
wallet level there are 667 rows. The cost is that wallets within a token are
**not independent** — same launch, same liquidity event, same deployer — so
every split is `GroupKFold` by token. `test_model.py` demonstrates why by
showing a random split scoring higher than a grouped one on synthetic data
with a per-token fingerprint.

**The target is RUG against the rest**, collapsed at training time exactly
as Phase 2 required, with `UNCLEAR` and `NEVER_LAUNCHED` rows dropped rather
than folded into the negative class. Training a model to call our own
uncertainty "not a rug" would teach it that uncertainty is evidence of
safety.

**Logistic regression is primary, gradient boosting reported beside it.** At
this size the limit is the data, not the estimator, and readable
coefficients are worth more than a point of AUC. The gap between them on
timing features (0.79 against 0.97) is itself informative: boosting finds a
threshold in entry delay that a linear term cannot express, which is what
sniping within seconds would look like.

**A permutation null, not just a baseline.** Shuffled at the token level so
the null keeps every structure in the data except the association being
measured. With 44 tokens an AUC of 0.8 can arise from nothing; the null says
how often it does.

## What this model must not be used for

* **A deployment decision.** 44 tokens, one chain, a three-hour slice of
  history, and **zero SURVIVED examples** — it has never seen a healthy
  launch.
* **Ranking wallets by risk.** The target is a property of the token,
  inherited by its wallets. A high score means "this wallet is trading a
  token that looks like a rug", never "this wallet is a bad actor". The
  distinction is the same ethics commitment as Phase 3's.
* **Any unqualified number in a report.** The fold-to-fold spread is the
  same order as the differences being discussed.

## What would change the answer

1. **More tokens.** Discovery of three further historical windows has added
   855 candidates and the backfill is running; at the measured ~14% that
   ever trade, each cycle roughly doubles the labelled set. The pipeline is
   built and the per-token cost is known: ~44 calls to backfill, ~235 to
   label.
2. **A label contrast not confounded with activity.** RUG against SURVIVED
   compares two tokens that both traded, which removes the leak at its root
   instead of deleting 64 features to work around it. There are currently
   zero SURVIVED tokens.
3. **Features not downstream of trade volume.** The surviving set is graph
   structure and entry timing. Funding *ancestry* is the obvious addition
   and it needs the indexing API Part A could not reach.

# Phase 5, Part A — the integrity audit (2026-10-18)

Evidence: `backend/reports/leakage_audit.md` and `leakage_audit.json`,
from `python -m scripts.leakage_audit`. Code: `blocklens/model/audit.py`.

## Censoring was present, and it was total

All 28 labelled rugs died inside their own 24-hour feature window. Measured
from transfers, the median death is at minute 15. The label's
`largest_drop_ts` reads "hour 6" for 27 of them because that is when the
next sample was taken. Retraining on rugs still alive at window end is
**not estimable: there are zero**, against Phase 4's published 0.793 /
0.970. At token level, mean entry delay scores AUC 0.544, and its
correlation with the minute trading stopped is ρ = 0.745. Entry timing was
reading the outcome, not predicting it.

**Done about it:** the Phase 4 model card is marked withdrawn. Neither of its
claims ("entry timing predicts rugs", "graph features carry no signal") may
be quoted.

## Two further findings that matter more than censoring

* **Cross-token leakage through the wallet is present.**
  `load_wallet_behaviour` aggregates each wallet over every token it
  touched, so 407 of 667 rows carry a `base_*` vector identical to the same
  wallet's row on another token. More importantly, **all 20 RUG tokens in
  the feature set form one shared-wallet component**, and 8 have one
  deployer. The positive class is one operation, so the effective positive
  sample size was **one**.
* **8 of those 20 RUG tokens are untradeable pools** initialised at price
  2¹²⁸, with an outflow 20× their measured peak reserve. They are
  measurement artefacts, not rugs.
* All 44 modelled tokens launched within 50 minutes of each other, so no
  temporal split is possible on this data.

## Feature window — PROPOSED, then adopted in Parts B–D (see below)

**5 minutes, with a survival requirement** (still trading after minute 5
and above the reserve floor), with 2 and 10 minutes as sensitivity runs.
Every genuine rug is alive at minute 5. At 30 minutes only 3 of 28 are.
Survival modelling was rejected for this population: every rug falls
inside the first 6 hours, so a hazard model reduces to the same early
binary question at much greater cost. Revisit if Part B finds late rugs.

## Changes Part B has to absorb

* Count **operator families** (shared-wallet component merged with shared
  deployer), not tokens. Cap tokens per family. Every split is by family.
* A degenerate-pool filter before labelling (initial price at a sqrt-price
  bound, or largest outflow above the peak reserve → `NEVER_LAUNCHED`).
* `base_*` features rebuilt per (wallet, token), at the N-minute cutoff.

# Phase 5, Parts B–D — dataset, retrain, decision (2026-10-18)

Evidence: `backend/reports/sampling_design.md`, `phase5_counts.md`,
`model_card_v2.md`, `phase5_results.json`.

## Censoring: present (Part A), fixed by design

The feature window is **launch + 5 minutes**, and only tokens **alive at
minute 5** are in the population: a swap by minute 5, another within the
hour after, and the reserve above 10% of its peak at minute 5. Every genuine
rug in the Part A data was alive at minute 5, and 30 minutes would have kept
3 of 28. Survival modelling was rejected because every rug lands in the
first hours, so it reduces to the same question. 2 and 10 minutes remain
untested sensitivity runs.

## Rule v2

`degenerate_pool` sends pools at the sqrt-price bound, or with an outflow
above their peak reserve, to NEVER_LAUNCHED. Re-judging Phase 2's rows from
stored series moved 9 RUG and 6 FAILED to NEVER_LAUNCHED.

## Sampling design and counts

| stratum | target (brief) | achieved |
|---|---|---|
| random cohort, alive | 500 | **458** |
| RUG (training) | 400 | **152** |
| FAILED (training) | 300 | **331** |
| SURVIVED (training) | 300 | **5** |

* **Random cohort:** uniform 1,000-block windows, one per week for 26 weeks,
  outcome-blind. Before 2026-04-20 it calibrates; after, it is the only
  evaluation set.
* **Training strata:** **case-control**, not class quotas. RUG prevalence
  is 8.7% and SURVIVED 0.2%, so blind labelling to 400 RUGs would have
  needed ~5,000 labels. A coarse nine-point reserve pre-screen picks cases
  (91% turn out RUG), and a 20% Bernoulli draw of the rest gives controls.
* **SURVIVED enumeration from live pool lists yielded 3 tokens.** SURVIVED
  is not a modellable class at this base rate.
* **Families** (shared deployer key, or shared early buyers within 24 h;
  hubs excluded) group the 1,066 alive tokens into 841 families. Training
  is capped at 3 per family, no family crosses the split, and every CI
  resamples families.
* **Budget:** 297k keyless calls. No monthly ceiling applies; the binding
  constraint was wall-clock time. Batched reads were verified exactly (72 of
  72 points) before use.

## Prior correction

* **Logistic regression:** King–Zeng intercept shift to the CAL prevalence.
* **Gradient boosting:** Platt scaling fitted on CAL.

**The intercept shift made the logistic model worse on EVAL** (Brier 0.019
→ 0.047), because CAL and EVAL differ by covariate shift. Self-deployed
launches went from 4–11% to 63–69% of the population while P(RUG | launch
type) stayed flat. Reported, not dropped.

## Does the model beat the rule checker?

* **Against the pre-registered checker, yes, by a wide margin:** PR-AUC
  0.999 vs 0.485.
* **But that checker omitted the liquidity-lock rule,** and is worse than
  random (ROC-AUC 0.074).
* **Against the one-line lock rule, added after the results and labelled
  so:** 0.999 vs 0.965, +0.034 [+0.007, +0.075]. The model wins, narrowly.
* **On this population, LP-pull RUG is close to decided by launch type at
  minute 0:** 109 of 113 self-deployed tokens rugged; 0 of 74 launchpad
  tokens did.

## Part D outcome: 3

The graph features add nothing anywhere, at full power, for the questions
this data can ask.

* **Token level:** graph-only scores far above its null (0.962 vs null p95
  0.651), but adds +0.0003 [0, +0.0005] over timing. Every model is at the
  ceiling set by launch type, so this level cannot test the hypothesis.
* **Wallet level (10,680 early buyers, 317 tokens, grouped CV):** graph
  position predicts a wallet dumping at AUC 0.518, against 0.602 for its
  own entry timing.

Deployer-funded wallets do dump at twice the base rate, but they are 0.9% of
buyers.

## Recommended next step (not started)

A v3 label that splits FAILED into insider/dev dump vs organic decay. That
is where launchpad tokens (99% FAILED) actually lose holders' money, and the
only place left where the graph module can be tested on a question that
launch type does not already answer. Nothing from Phase 5 goes to the UI
until then.

# Phase 6 — splitting FAILED (started 2026-10-19)

## The first definition was rejected by a pilot, before any label was written

"Insiders held ≥5% of supply at minute 5 and ≥80% of it was gone before the
price fell to 10% of peak." A 50-token pilot found:

* **No collapse to anchor to.** 563 of 584 FAILED tokens are `dead`, not
  `collapsed`. On single-sided V4 launchpad pools the launch price is a
  floor, and the median FAILED token's sampled price at 1 h, 6 h, 7 d and
  90 d *is* its launch price. 308 of 584 never move after day 0.
* **No insiders to follow.** The median token has zero identifiable
  insiders: launchpad launches carry no dev allocation in the launch
  transaction, and the factory is correctly excluded.

## The definition used instead: day-0 extraction (`extraction.py`)

A FAILED token is a day-0 round trip, so the split is whether money moved
from later buyers to earlier ones over the first 6 hours. **EXTRACTED**:

* the minute-5 cohort's profit is ≥ 25% of what later buyers spent, and
* later buyers supplied ≥ 10% of all buy-side money.

Otherwise **DECAY**, and UNCLEAR if < 80% of swaps are priced.

Supporting changes:

* **Backfill extended from 1 h to 6 h** for every non-RUG token.
* **26 launchpad/infrastructure contracts** (code-bearing addresses that
  receive tokens in the first 5 minutes of > 2% of launches) are excluded
  from cohorts and funders: `known_addresses/launchpad.json`.
* **Bot wallets on many launches are kept:** they are early traders.

## Pre-registered before results (`model/rulecheck_x.py`)

* **T1 (primary):** EXTRACTED vs DECAY + SURVIVED, on non-RUG alive tokens.
* **T2 (secondary):** buyer loss. A buy at the minute-5 price is worth
  ≤ 50% at hour 6.
* **Baselines:** the Phase 5 five-flag checker unchanged, plus a five-flag
  early-concentration checker (one wallet dominates, bundled launch,
  sniped, already pumped ≥ 5×, early selling), verdict at 2 flags.
* **Sets:** same TRAIN / CAL / EVAL as Phase 5. Families as Phase 5.

## Phase 6 results (2026-10-19) — `backend/reports/model_card_phase6.md`

* **Measurement fix before any result was used.** The first full run
  valued unsold tokens at the last swap price; dust trades at spiked prices
  made later buyers "gain" 36x at p90. Switched to realised cash only.
* **FAILED splits 93.1% DECAY, 3.7% EXTRACTED, 3.2% UNCLEAR** (593 tokens).
  Robust across thresholds (14–27 EXTRACTED). 0 EXTRACTED in the random
  cohort after April. **The answer to "insider dump or organic decay" is
  organic decay.**
* **T1 is not modellable:** 9 training positives, 0 in the pre-registered
  evaluation set. Both fixed checkers are at or below chance on CAL.
* **T2 (buyer loss at hour 6 from the minute-5 price).** The pre-registered
  EVAL set has 3 positives, so it is evaluated on CAL instead: a deviation,
  out of sample but not out of time. Boosting 0.833 against the
  checkers' 0.37 (base rate 0.36): beats both, CI [+0.36, +0.55]. Not one
  feature: the best single feature scores 0.575.
* **Part D, re-run on a non-saturated target: outcome 3 stands.** Graph-only
  0.543 beats its null (p95 0.443), but adds +0.005 [−0.028, +0.033] over
  timing (boosting) and +0.035 [−0.016, +0.084] (logistic).
* **Out-of-time check for T2 (afterwards).** Train before 1 March, test
  March–April: 0.758 vs the checker's 0.331, CI of the difference
  [+0.13, +0.59]. On May–July (3 losses in 78) the model flags 5 tokens,
  including all 3 losses (ranked 2–4), with mean risk 0.12. **Judged good
  enough to show in the product with its validation stated beside it.**

# Phase 7 — the API and the first model in the product (2026-10-19)

* **What ships:** a live **Fresh Launches** feed. Every new Base Uniswap
  pool is scored once, at launch + 5 minutes, with two signals: launch type
  (Phase 5) and buyer-loss risk (Phase 6, `buyer_loss_v1`).
* **Why at minute 5 only:** both signals were validated at that moment. A
  score for a token days old would claim more than the research shows. An
  older token's page says it is not tracked, rather than scoring it.
* **Why it was judged worth showing:**
  * it beats both pre-registered checkers in period (0.833 vs 0.37);
  * it beats them out of time (0.758 vs 0.331, March–April);
  * in May–July it lowered its risk with the regime instead of raising
    false alarms.

  The validation record travels with every API response and is printed on
  the page.
* **Scored only when the training conditions hold:** the pool traded by
  minute 5 and still held its liquidity. Otherwise the reason is shown.
* **The deployed model is fitted on all 593 labelled non-RUG tokens.** The
  numbers it carries come from the held-out runs, not from this fit.
* **Live tokens enter the store as stratum `live`, with an exclusion
  reason,** so research queries never mix them with the sample.
* **The API is FastAPI, served by uvicorn.** The front end reads it through
  the Vite proxy at `/api`. The keyless-source proxies (`/gt`, `/ds`, `/gp`)
  remain as they were.

# Phase 8 — forward validation, pre-registered (2026-10-19, before any outcome)

Every check so far used launches that had already happened. This test uses
launches that have not.

* **Frozen model.** `buyer-loss-v1` exactly as shipped. No retraining,
  recalibration or threshold change while the test runs; any change starts
  a new, separately reported record.
* **Unit.** Every pool the live feed scores at launch + 5 minutes. The
  prediction is written once, at scoring time, and never edited. Pools not
  scored are logged too, with their reason, so the denominators are
  visible.
* **Outcome 1 — buyer loss**, resolved at launch + 6 hours: the minute-5
  price against the hour-6 price, by the same code as the label
  (`extraction.measure`).
* **Outcome 2 — liquidity pulled**, for the launch-type signal: the pool's
  token reserve at 1, 7, 30 and 90 days, read by `balanceOf`. "Pulled" means
  at or below 10% of the larger of its minute-5 and hour-6 reserve.
* **Metrics, fixed now:**
  * buyer loss: PR-AUC, ROC-AUC, Brier against the base rate, ten-bin
    reliability, and precision at risk ≥ 0.5;
  * launch type: pull rate by type at each horizon.
* **Reporting floor.** No forward result is called a finding before **200
  resolved scored predictions with at least 20 losses**. Below that, the page
  shows the counts and says "too early".
* **Success criterion, stated in advance.**
  * The model's forward PR-AUC exceeds the forward base rate, with the
    family-free 95% bootstrap interval of the difference above zero.
  * Self-deployed pull rate at 7 days exceeds launchpad's.

  Failing either is reported as a failure.
* **Started 2026-10-19 07:32 PKT**, detached (`scripts/start_live.ps1`).
  The resolver was checked before use against 4 research tokens with known
  outcomes: hour-6 price ratio identical to Phase 6 on all 4, and reserves
  read at all 5 horizons. The 23 launches scored before the protocol was
  written are not in the log.
* **Expected pace at current launch rates:** about 25 scored launches an
  hour. The floor of 200 resolved should arrive in roughly a day, but at
  May–July's ~4% loss rate, 20 losses needs ~500 resolved: a few days. The
  first 7-day liquidity results arrive on 2026-10-26.

# Phase 9 — the paper agent, pre-registered (2026-10-19, before any outcome resolved)

The proposal's agent "puts our own signal on the line and reports what it
earned." It trades on paper only, on the forward record, with rules fixed
now.

* **When it acts:** every scored launch, at minute 5, at the minute-5
  price. Exit at hour 6 at the hour-6 price. One unit of notional per trade.
* **If liquidity was pulled before the exit** (hour-6 reserve ≤ 10% of the
  larger of the minute-5 and hour-6 reserve), the trade returns −100%: you
  cannot sell into a pool that is gone.
* **Cost:** 3% round trip (fees plus slippage) in the headline, with 1%
  and 10% as sensitivity runs.
* **Return** = price ratio × (1 − cost) − 1, capped at +1,000% per trade,
  so a single dust-priced spike cannot carry the record. The cap is
  reported.
* **Policies, run side by side:**
  * **AGENT:** buy only if the risk is < 0.2 *and* the launch is a
    launchpad (liquidity locked).
  * **CONTROL:** buy every scored launch.
  * **AVOIDED:** the launches AGENT refused. They should do worse.
* **Reported:** trades, mean and median return, hit rate, total, and a 95%
  bootstrap interval of AGENT's mean minus CONTROL's.
* **Floor:** no conclusion before AGENT has 100 resolved trades.
* **Success:** AGENT's mean return beats CONTROL's, with the interval
  above zero. A positive mean is not required: a signal that only loses
  less is still worth knowing. Failure is reported as failure.

## RESOLVED — The X post budget (2026-10-19)

**Decided: no X budget; KOL scoring is out of scope.** It needs paid post
reads (~$0.005 each) and there is no keyless substitute. `X_POST_BUDGET`
stays 0 and `X_ENABLED` stays off. The KOL section and the KOL directory
remain **Sample**, labelled as such on every page. Nothing about any named
account is a measured finding, and nothing in the risk model or the live
feed uses KOL data.

## Phase 8 note — outages and late predictions (2026-10-21)

The live stack was down from 2026-10-19 22:11 to 2026-10-21 12:15 PKT,
after a machine restart. The scanner resumes from its last block, so the
gap's launches are still discovered and scored. But those scores are made
after their six-hour outcome existed.

**Rule, set before any late row was scored:** only *timely* predictions,
scored at or before launch + 6 hours, count toward any forward metric or
the paper agent. Late ones are logged and their count is reported, and
nothing else. No information leaks into them (frozen model, pre-cutoff
data only), but the pre-registration promised predictions made before the
outcome, and only timely ones are.
* **Auto-start registered** (2026-10-21, at the user's request): a per-user
  scheduled task runs `start_live.ps1` at logon, so a restart no longer
  silently stops the forward test.
* **Refined the same day:** launches already past their six-hour mark when
  they fall due are not scored at all. They are logged as "missed during an
  outage". Scoring a 38-hour backlog was delaying today's launches, which
  can still count.

## Phase 9 result — the paper agent passed its floor (2026-10-21)

Full report: `backend/reports/paper_agent.md`. Numbers come from
`scripts/phase9_report.py`.

* **Pre-registered test: success.** AGENT made 315 timely trades with a mean
  of +49.3% and a median of −3.0%. CONTROL made 832 trades with a mean of
  −33.4%. The 95% interval for AGENT − CONTROL is +55% to +110%. The result
  holds at 1% and 10% cost.
* **Post hoc, labelled as such:** the margin is the launch-type filter. A
  model-free LAUNCHPAD policy (buy every launchpad launch) is
  indistinguishable from AGENT at every cap; the AGENT − LAUNCHPAD interval
  spans zero. The risk score turned down only 22 launchpad launches.
* The mean rests on 16 trades that hit the cap. Without them it is −1.6%,
  so AGENT avoids losses; it does not pick winners.
* **Change to the live output:** `paper_agent` now also reports LAUNCHPAD
  and `agent_minus_launchpad_ci`, both marked post hoc. The pre-registered
  policies and their computation are unchanged. The Portfolio page says
  where the edge comes from, instead of "the signal is paying".
* The buyer-loss forward record is still below its floor (831 resolved, 14
  losses against the 20 required). The 7-day launch-type check is still due
  around 2026-10-26.

# Phase 10 — the product around the signal (2026-10-22)

Scope for the FYP-1 mid evaluation is fixed in `docs/FYP1_SCOPE.md`. This
phase adds what a user needs around the two signals, and nothing that the
research cannot stand behind.

## Every score carries its anatomy

**Decision:** each live score is decomposed into a base rate plus one
additive term per feature, by path-dependent tree SHAP on the frozen
`buyer_loss_v1` artefact (`live/explain.py`), and the top movers are shown
beside the score with their values in the feature's own unit.

**Why SHAP and not a surrogate or a feature-importance table:** the
decomposition is exact for a tree ensemble, in log-odds, and sums to the
model's own logit; `test_explain.py` asserts that to 1e-3. A global
importance table says what matters on average; the user is looking at one
launch. The frozen model is not touched, so the forward test (Phase 8) is
unaffected; the explanation is stored beside the prediction
(`live_prediction.explanation`) so the forward record can later be read by
driver.

**What it is not:** a causal account of the launch. The labels say "raises
the risk" and "lowers the risk", meaning the model's estimate, and the page
says so.

## Alerts follow the paper agent's rule, and only that

A scored launchpad launch with risk under the agent's ceiling (0.2) is
pushed over a server-sent-events stream to the open page, and, if a bot
token and chat id are configured, to Telegram. Nothing else is pushed. The
rule is the pre-registered policy from Phase 9 rather than a new threshold,
because a new threshold would be an untested claim. Telegram because its Bot
API is free and keyless beyond the bot's own token; the channel is off
unless both environment variables are set, and a failed send is recorded
and never stops the scorer.

## Product state lives in the store, without accounts

Two tables, `watchlist_item` and `investigation`, written through the gate
like every other row, with no owner column. The product is single-user at
this stage; adding accounts is a column and a filter, not a redesign.
Addresses are lower-cased on write so a token can be on the list once.

## The system reports on itself

`/api/model/health` reads the forward log only: launches a day and why
each was or was not scored, the self-deployed share per day (the regime
drift that broke calibration in Phase 5), scoring delay, and gaps in the
record longer than fifteen minutes, which are the outages. It is the
product's monitoring, deliberately separate from the forward record, which
is the only place accuracy is claimed.

## The front end is narrowed to what the backend can defend

Removed from the product, per the scope: the KOL directory and section
(no keyless source; resolved 2026-10-19), the simulated portfolio (invented
trades beside a real record), the social and narrative sections, and the
chain selector's three unmeasured chains. The three hand-built profiles
remain as labelled case studies. The Portfolio page is the paper agent's
real book, trade by trade, from `/api/paper-agent/trades`.
