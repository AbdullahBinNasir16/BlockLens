# Phase 2 spike — can the labels be built, and from what?

Measured 2026-10-13 on Base, keyless, before writing any label code. The
brief asks to be told when a criterion or a data source looks wrong before
it is implemented. Four things do.

Evidence: `B1_historical_reach.json`, `B2_cheaper_history.json`,
`B3_archive_sampling.json`, `B4_balance_sampling.json`,
`B5_v4_pool_state.json`.

---

## 1. The age gate fires. Phase 1's tokens are two days old.

| | |
|---|---|
| backfilled 24-hour windows | 159 |
| of those, launched ≥ 90 days ago | **0** |
| launch dates covered | 2026-10-10 → 2026-10-11 |
| tokens in `token` with `created_ts` ≥ 90 days old | 5 |

Those 5 are not usable either: they are established majors (BRETT and
friends) that arrived through DexScreener enrichment, not launches found by
discovery, and none has a backfilled window.

**This is fixable, and the fix is cheap.** The node serves historical logs:

| Probe | Result |
|---|---|
| `eth_getBlockByNumber` at −90d / −180d | both OK |
| `eth_getLogs` V4 `Initialize`, 1,000 blocks at −90d | 74 pools |
| `eth_getLogs` V4 `Initialize`, 1,000 blocks at −180d | 492 pools |

So `discover --offset-hours 2160` reaches the right era, and backfilling
those tokens' first 24 hours costs the same 44 calls each that Phase 1
measured. Candidate supply is not a problem at that depth.

## 2. The brief's data source does not exist in this project

> "using the same `alchemy_getAssetTransfers` path Phase 1 settled on"

Phase 1 settled on no such thing. Part A left `getAssetTransfers`
**unverified** — §0 of `FINDINGS.md` records that there is no Alchemy key in
this environment and that the public `demo` key returns HTTP 429 on Base.
Phase 1 runs entirely on keyless `eth_getLogs`, and `AlchemySource` is
inert without a key.

So the reconstruction has to be done some other way, or a key has to be
bought — which the "unpaid work only" rule forbids.

## 3. Reconstructing reserves from transfers is unaffordable

The 1,000-block range cap is **absolute**. It is not relaxed by narrowing
the query, which was the hope:

| Query | Result |
|---|---|
| `[pair]` over 5,000 blocks | refused |
| `[pair]` over 50,000 / 500,000 / 3,888,000 blocks | refused |
| `[pair]` + `Sync` topic over 50,000 blocks | refused |

90 days is 3,888,000 blocks on Base, so a per-token reserve history costs
**3,888 calls**. For 200 tokens that is 777,600 requests — days of
wall-clock against a public endpoint we do not own.

Alternative endpoints were measured:

| Endpoint | Max address-filtered span | Calls/token for 90d |
|---|---|---|
| PublicNode | 10,000 | 389 |
| Tenderly (ours) | 1,000 | 3,888 |
| official, dRPC, meowRPC | failed outright (429 / 400 / method disabled) |
| LlamaRPC, BlockPI, 1RPC | unreachable (525 / 521 / 503) |

PublicNode's 10× range looked like the answer for about four minutes, then
returned `403 Forbidden` to everything — it had rate-banned the probe. It
is not a foundation to build on.

Blockscout's public API returns `403` to both `/api/v2` and the legacy
`/api`, with a browser user-agent as well as ours. Not available.

## 4. There is a better method, and it is cheaper *and* more accurate

**Archive `eth_call` works on the free gateway, at least 365 days back.**
That changes the shape of the problem: the quote reserve does not have to be
*reconstructed* from a running sum, it can be *read*.

`balanceOf(quoteToken, pairAddress)` at a historical block **is** the quote
reserve, by definition, for every venue that holds its own funds:

| Pool | −7d | −30d | −90d | −180d | −365d |
|---|---|---|---|---|---|
| BRETT/WETH Aerodrome CL | 166.2 | 143.5 | 168.8 | 213.8 | 301.0 |
| BRETT/WETH Uniswap V3 | 17.8 | 12.4 | 13.7 | 17.1 | 20.8 |

A 90-point daily series: **90/90 points in 42.7 s**, 0.47 s per call.

| | Brief's method | Sampling |
|---|---|---|
| calls per token, 90 days | 3,888 | 90 |
| 200 tokens | 777,600 | 18,000 |
| wall clock, 200 tokens | days | ~2.4 hours |

It is also the **more accurate** of the two. A cumulative sum of transfers
is only correct if every transfer in 90 days was captured; one missed window
silently biases every later point. Each sampled balance is independent and
exact, so there is no drift to accumulate.

What is lost is resolution: daily sampling locates a liquidity pull to
within a day, not to the block. That is recoverable for the tokens that
matter — once the series shows *which day* the reserve collapsed, one
precise 43-call scan of that day finds the transfers and their destination.
Roughly **133 calls per token**, still 29× cheaper than scanning everything.

## 5. Uniswap V4 breaks the reserve criteria, and it is most of Base

V4 keeps every pool's funds in one PoolManager — measured at 4,211 WETH
across all pools at once — so `balanceOf` cannot isolate one pool.

**Price is cheap and exact.** `extsload(poolStateSlot)` on the PoolManager
returns slot0, and the official StateView returns the same thing. Both were
run against the same pool and agree to the digit:

```
extsload  tick=160545  sqrtPriceX96=242613876899705402168497462181292
StateView tick=160545  sqrtPriceX96=242613876899705402168497462181292
```

That agreement is also how the StateView address was confirmed —
`0xa3c0c9b65bad0b08107aa264b0f3db444b867a71`, of three published candidates
(the other two returned empty). Taken from a list it would have been a
guess; checked against an independent method it is a measurement.

**Reserve is not available.** `getLiquidity(poolId)` returns **0** for a
pool with 334 recorded swaps. That is not a bug: on a concentrated-liquidity
pool, `liquidity` is the *active* liquidity at the current tick, which is
zero whenever the price has moved outside every position — indistinguishable,
at this call, from a pool whose liquidity was genuinely withdrawn.

So on V4, `LIQUIDITY_PULLED` and the reserve arm of `STILL_LIVE` cannot be
evaluated the way the brief defines them without reconstructing
`ModifyLiquidity` events, which puts us back at 3,888 calls per token.

This is not a small corner. V4 is **95%** of what discovery found (95 of 99
candidates in the sampled window), and it was already dominant at −180d.

## 6. Swap counts over 90 days are expensive on every venue

`DEAD` (<5 swaps in 30 days) and `STILL_LIVE` (≥20 swaps in 30 days) both
need a swap count, and counting swaps means scanning logs: 1,296 calls per
token for the last 30 days alone — 14× the cost of the whole price series.

**A proposal, at zero extra cost:** the daily samples already distinguish a
trading pool from a still one. A pool with no swaps has an unchanged tick,
so "days on which the price moved, out of the last 30" comes free from the
series we are already pulling. It measures *trading activity*, which is what
`DEAD` is actually reaching for, rather than a swap count, which is the
proxy the brief chose for it. It is coarser — a day with one swap and a day
with four hundred look alike — so if the swap count itself matters, it has
to be paid for.

---

## What this means for the plan

Nothing here says the labels cannot be built. It says three of the brief's
choices need revisiting before they are implemented:

1. the data source (no Alchemy key exists, and the free-tier method is
   sampling, not reconstruction);
2. the venue scope (reserve criteria do not translate to V4, which is most
   of the chain);
3. the activity criteria (swap counts cost 14× the rest of the pipeline).

And one instruction has to be honoured before any of it: the tokens
currently in the store are two days old, so discovery has to be re-pointed
at the historical window first.
