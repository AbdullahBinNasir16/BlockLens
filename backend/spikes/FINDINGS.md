# Part A — data access spike: findings

Run 11 October 2026. Throwaway scripts in this directory; 1,029 HTTP calls in
total, all to free, keyless endpoints. Every number below is either
**measured** (I made the call and counted), **computed** (measured volume × a
published price), or **unverified** (the vendor's documentation, which I could
not test). Each is labelled. Nothing here is an estimate dressed up as a
measurement.

---

## 0. The one thing I could not settle, and why

**There is no Alchemy API key in this environment, and I cannot create an
account.** So the specific question Part A was written to answer — *does the
free plan allow `alchemy_getAssetTransfers` at full block range* — is **still
open**. Alchemy's public `demo` key returns HTTP 429 on Base, so it cannot
stand in.

What I did instead: measured the real first-24-hour data volume per token on
Base, which is the input the cost model actually needs, and measured every free
alternative I could reach. The arithmetic below is therefore sound up to one
unverified constant (Alchemy's per-call CU price) and one unverified behaviour
(whether the free plan caps `getAssetTransfers` range).

**To close it I need one free Alchemy key.** With it, A1 and A2 are about
fifteen minutes of work.

---

## 1. Verdict

| Question | Answer |
|---|---|
| Is `eth_getLogs` viable for backfill on a free tier? | **No — on any provider, not just Alchemy.** Confirmed in §2. |
| Is `getAssetTransfers` the likely path? | **Yes, on the measured volumes** — if the free plan allows full range. Unverified. |
| Can Base be done on free tiers? | **Probably yes for transfers** (~31,000–71,000 tokens/month, computed). **No, if every trade needs its wallet attributed** (~450 tokens/month). That is the real constraint, and it is the only one that does not fit. |
| Does swap reconstruction need a second source? | **No second source. But it needs transaction-level data, which is the dominant cost.** See §4. |
| Which chain for Phase 1? | **Base**, on the evidence in §7. The dataset-target worry in my first report is now resolved — see §5. The decision is yours. |

---

## 2. The block-range cap is universal, not an Alchemy quirk — *measured*

Base is **2.00 s/block exactly**: blocks 51,000,000 → 51,043,200 spanned
86,400 s. One token-day is therefore **43,200 blocks**, as the proposal assumed.

Every free Base endpoint I could reach, probed with a real address-filtered
`eth_getLogs` at widening ranges:

| Endpoint | Max range | Calls per token-day | How it refuses |
|---|---|---|---|
| `base.gateway.tenderly.co` | **1,000 blocks** | **44** | `Block range too large for public access: maximum 1000 blocks`; separately caps at 20,000 results |
| `base.drpc.org` | 100 | 433 | `ranges over 1000 blocks are not allowed`, then times out on the free plan |
| `base-pokt.nodies.app` | 50 | 865 | `Block range too large: maximum allowed is 50 blocks` |
| `1rpc.io/base` | 10, then 429 | 4,320 | `eth_getLogs is limited to 0 - 50 blocks range` |
| `mainnet.base.org` | — | — | HTTP 429 `request limit reached` on any `getLogs` |
| `base-rpc.publicnode.com` | — | — | HTTP 403 `Archive requests require…` — no historical data at all |
| `base-mainnet.public.blastapi.io`, `base.api.onfinality.io`, `base.meowrpc.com` | — | — | 429 / 400 immediately |
| `base.blockpi.network`, `endpoints.omniatech.io`, `base.lava.build`, `base.llamarpc.com` | — | — | unreachable (521 / 410 / 525) |

**The proposal's arithmetic is confirmed.** At Alchemy's documented 10-block
free cap, one token-day of `eth_getLogs` is 4,320 calls × 60 CU = **259,200
CU**, i.e. **115 tokens/month** against 30M CU *(computed from Alchemy's
published price; unverified)*. That path is dead, and it is dead everywhere —
an industry-wide free-tier posture, not one vendor's pricing choice.

Two sources that used to be keyless no longer are, which matters because both
appear in older write-ups as free options:

- **Blockscout** (`base.blockscout.com`) — now behind a Cloudflare challenge;
  every API call returns HTTP 403 `Just a moment...`.
- **Envio HyperSync** (`base.hypersync.xyz`) — now HTTP 401,
  `API Tokens can be created at app.envio.dev`.

---

## 3. What a token actually costs — *measured volume, computed CU*

Four real Base tokens, each scanned across its **complete first 24 hours**
(43,200 blocks, 44 calls each via Tenderly, no sampling):

| Token | State today | Transfers | Transactions | Pool logs | Buyers in hour 1 |
|---|---|---|---|---|---|
| XDP | dead, liq $242 | **0** | 0 | 0 | 0 |
| gSPEED | dying, liq $40.7k | **443** | 272 | 261 | 36 |
| SNDKc | dead, liq $2.8k | **3,270** | 1,900 | 13 | 0 |
| CAS | liquid, liq $328k | **7,679** | 2,522 | 3,983 | 0 |

XDP is not an error: its pool was created and the token never moved. Verified
twice, from the DexScreener pair date and again from the factory's own
pool-creation block. A sizeable share of "launches" have no first day at all.

`getAssetTransfers` returns 1,000 transfers per page, so pages =
⌈transfers/1000⌉ and CU = pages × 120 *(the brief's price; Alchemy's docs have
also listed 150 — unverified either way)*:

| Token | Pages | CU/token-day | Tokens/month @ 30M CU |
|---|---|---|---|
| XDP | 1 | 120 | 250,000 |
| gSPEED | 1 | 120 | 250,000 |
| SNDKc | 4 | 480 | 62,500 |
| CAS | 8 | 960 | **31,250** |

### The number, in large friendly letters

> **A complete first day of transfer history costs 120–960 CU, mean 420 CU.
> Against 30,000,000 CU that is roughly 31,000 tokens a month at the worst
> token measured, and ~71,000 at the mean.**
>
> **Phase 1 needs 100. The transfer path has about two orders of magnitude of
> headroom — _if_ the free plan allows full-range `getAssetTransfers`.**

The spike's own run is the sanity check: 580 Tenderly calls covered four
token-days plus five days of factory discovery, in about seven minutes.

---

## 4. Swaps: no second source, but a real cost — *measured*

**Transfers alone give you the trade.** For any pool, token-in/token-out and
quote-in/quote-out appear as ERC-20 `Transfer` logs to and from the pool
address, so direction and both amounts are recoverable, and price in quote
terms is their ratio. USD then needs the quote asset's price, which
`pair_snapshot` already provides. Pool logs cost nothing extra: one
`eth_getLogs` filtered on `[token, pool]` returns both, which is how §3 was
built.

**Transfers alone do not give you the trader.** I took a real CAS swap
(`0x6bf7c013…`) and compared:

- The transaction carries **15 logs and 8 ERC-20 transfers** — an aggregator
  route, not a simple swap.
- Naive "counterparty of the pool transfer" attribution returns
  `0x498581ff…`, which is **Uniswap V4's PoolManager** — a contract, not a
  trader — and it **sums two separate legs** into a single amount.
- The real trader is `tx.from` = `0x7372e848…`, reachable only from the
  transaction, not from any log. `tx.value` is 0, so the native-transfer trick
  does not recover it either.

Cost of the obvious fix, `eth_getTransactionByHash` per transaction at 26 CU
*(published price, unverified)*:

| Token | Transactions | CU for attribution | CU total | Tokens/month |
|---|---|---|---|---|
| gSPEED | 272 | 7,072 | 7,192 | 4,171 |
| SNDKc | 1,900 | 49,400 | 49,880 | 601 |
| CAS | 2,522 | 65,572 | 66,532 | **450** |

**Wallet attribution, not transfer volume, is what would blow the budget** —
roughly 70× the cost of the transfers themselves. Phase 1 does not need it (the
schema stores `from`/`to` as recorded), but Phase 3's clustering does, so it
needs deciding early. Cheaper routes exist and should be measured in Phase 2:
joining the `external` and `erc20` categories of `getAssetTransfers` on `hash`
recovers the EOA for natively-paid swaps at no extra call, leaving only
stablecoin-quoted aggregator routes needing a receipt.

---

## 5. Base's launch population — *measured, and my first pass was wrong*

I reported a floor of 1–3 tradeable launches a day and flagged that it
excluded Uniswap V4. Having now scanned V4, that caveat was the whole story,
and the corrected number changes what is reachable.

**V2/V3-style factories** (what the first pass counted):

- DexScreener's `token-profiles/latest` and `token-boosts/top` feeds, 60 rows
  combined: **23 and 28 of 30 were Solana. Zero were Base.**
- Uniswap V3 factory across four days (2026-07-20, 08-12, 09-05, 09-28): **321
  pools created; 9 of those tokens had ever traded; 2 were true launches that
  traded.**
- Aerodrome, PancakeSwap, BaseSwap and AlienBase on 2026-06-15: 11 pools, **1**
  of which ever traded.

**Uniswap V4, on a single day (2026-09-05)** — scanned by filtering the
singleton `PoolManager` on the `Initialize` topic, computed in `keccak.py`:

| Measure | Value |
|---|---|
| `Initialize` events in 24 h | **3,115** |
| Distinct new tokens paired against a known quote | **1,540** |
| Sampled for DexScreener presence | 60 |
| Of those, ever traded | **5 (8%)** |
| Implied tradeable tokens that day | **~128** (95% CI roughly 45–280 on n=60) |

So Base's tradeable-token inflow is on the order of **10² per day, not 10⁰**.
At ~128/day, 5,000 tokens is roughly **40 days of Base history**, not years.
The earlier figure was an artefact of counting only the venues that emit a
per-pool creation event; V4 is where Base's launch volume now is, and the
largest pools in the sample (Basecat, $544k liquidity; STONX, $443k) are all
V4.

Two honest qualifications:

- 8% on n=60 is a small sample. The implied count is the right order of
  magnitude, not a precise figure.
- None of the five traded tokens in the sample was *first* paired that day:
  their oldest DexScreener pair is earlier, so a V4 `Initialize` is often a
  second pool for an existing token rather than a birth. "Tradeable tokens
  touched per day" is the defensible reading; a strict launch census needs the
  token's first-ever pool, which is one more scan.

**The cost model is unaffected.** Transfers are fetched by token address
regardless of venue, and V4 swaps are reachable by filtering `PoolManager` on
the pool id — the same 44 calls per token-day as everything else.

---

## 6. The fallbacks — *measured*

### Etherscan V2, free tier, probed without a key

The API distinguishes its two refusals cleanly, so chain coverage is readable
without an account:

| Chain | chainid | Free tier? | Response |
|---|---|---|---|
| Ethereum | 1 | **yes** | `Missing/Invalid API Key` |
| Arbitrum One | 42161 | **yes** | `Missing/Invalid API Key` |
| Unichain | 130 | **yes** | `Missing/Invalid API Key` |
| Polygon | 137 | **yes** | `Missing/Invalid API Key` |
| Blast | 81457 | **yes** | `Missing/Invalid API Key` |
| Linea | 59144 | **yes** | `Missing/Invalid API Key` |
| **Base** | 8453 | **no** | `Free API access is not supported for this chain. Please upgrade…` |
| **BNB Chain** | 56 | **no** | same |
| **Optimism** | 10 | **no** | same |

Confirms the brief's table and adds **Optimism** to the paid-only list. At
100,000 calls/day with `tokentx` paging 10,000 rows, an Arbitrum or Unichain
token-day is one call for all but the busiest tokens — effectively unlimited at
Phase 1 scale, but those chains are not where the memecoin launches are.

### Solana — *measured, and it is the opposite problem*

Three tokens from DexScreener's latest profiles, counted on the public RPC
(`getSignaturesForAddress`, 1,000/page):

| Mint | Signatures read | Pages | Window observed | Implied rate |
|---|---|---|---|---|
| `HmHjsh3biZ…` | 5,260 | 6 | **0.1 h** | ~52,600/hour |
| `Fyt4p5wVhc…` | 4,990 | 5 | 1.6 h | ~3,100/hour |
| `4KxoBymf7p…` | 2,906 | 3 | 0.6 h | ~4,800/hour |

I paged backwards from newest, so this is each token's *current* rate, not its
first day — first days are typically busier. Even so, extrapolated to 24 hours
these are **75,000 to 1.2 million signatures per token-day**: 75–1,260 pages
for signatures alone, before fetching a single transaction body. Helius's free
tier is documented at 1M credits/month *(unverified)*. One busy Solana memecoin
could consume a month of it.

**Solana has the launch volume the project wants and a per-token data volume
one to two orders of magnitude worse than Base.** The two biggest papers being
cited are Solana studies, but they were not written on a free tier.

---

## 7. Recommendation

**Target Base for Phase 1.** In order:

1. **It fits.** 120–960 CU per token-day, computed from measured volume. One
   hundred tokens is ~42,000 CU — 0.14% of a monthly allowance. Solana's
   per-token volume is 10–100× larger; Arbitrum and Unichain fit comfortably
   but carry little of the launch activity the project studies.
2. **The pipeline is the deliverable, not the dataset.** Phase 1 proves
   correctness and cost. Base is the cheapest place to prove both.
3. **It is already the product's chain.** All three indexed projects in the
   frontend are Base, so the schema, the `Provenance` enum and the frontend's
   `Chain` type line up with no translation layer.
4. **Solana stays the Phase 4 argument.** If the paper needs that launch
   volume, it becomes a funded-tier decision made against a measured number,
   which this spike now supplies.

**Two things in the proposal must change. Reporting them is mine; deciding is
yours:**

- **The 5,000-token target is reachable on Base after all.** Counting Uniswap
  V4 (§5), Base touches on the order of 128 tradeable tokens a day, so 5,000 is
  about 40 days of history rather than years. My first report said otherwise;
  it was counting the wrong venues. No change to the proposal's target is
  needed on this ground.
- **Wallet attribution needs a decision before Phase 3.** At 26 CU per
  transaction it costs 70× the transfers, and it is the only measured figure
  here that does *not* fit a free tier.

---

## 8. Where the documentation was wrong, or incomplete

| Claim | What I found |
|---|---|
| Etherscan V2 free tier excludes Base and BNB | **Correct**, and it also excludes **Optimism** |
| Alchemy free `eth_getLogs` capped at 10 blocks on Base | **Could not verify** (no key), but every other free provider caps at 10–1,000 blocks, so the posture is industry-wide |
| Base ≈ 2 s/block, ~43,200 blocks/day | **Correct, exactly** — measured 86,400 s across 43,200 blocks |
| Blockscout's public API is a free fallback | **No longer true** — Cloudflare challenge, HTTP 403 on every call |
| Envio HyperSync is keyless | **No longer true** — HTTP 401, API token required |
| DexScreener is a discovery source for Base | **Weak for new launches** — its profile and boost feeds carried zero Base tokens, and search returns established tokens. On-chain factory scanning was required |
| `getAssetTransfers` gives you swaps | **Half true** — amounts and direction yes; the trading wallet, no, on aggregator routes |
| *(my own first report)* Base yields 1–3 tradeable launches/day | **Wrong, and corrected in §5** — that counted only venues emitting per-pool creation events. With Uniswap V4 included it is ~128/day |

---

## 9. What I need from you

1. **A free Alchemy key** (`ALCHEMY_API_KEY`) to close §0: whether full-range
   `getAssetTransfers` is permitted, and its true CU price.
2. **The chain call.** My recommendation is Base, with the §7 caveats.
3. **A ruling on the token target.** §5 now says 5,000 is reachable on Base in
   ~40 days of history. Phase 1 still builds 100 either way, so this only
   affects what Phase 4 promises.

Part B has not been started, as instructed.

---

## 10. Files

| File | What it holds |
|---|---|
| `_http.py` | stdlib HTTP/JSON-RPC helper with per-host call and timing counters |
| `a1_probe_rpc.py`, `a1_range_caps.py` | range-cap probes → `rpc_limits.json`, `range_caps.json` |
| `a1_harvest.py` | DexScreener search harvest → `harvest.json` |
| `a1_discover.py`, `a1_discover_v3.py` | factory scans → `discovered.json`, `launches.json` |
| `a2_measure.py` | the 24-hour scans → `measurements.json`, `cost_table.json` |
| `a3_swaps.py` | swap reconstruction → `a3_swap_reconstruction.json`, `a3_wallet_attribution.json` |
| `a4_fallbacks.py` | Etherscan chain probe, Solana volume, block time → `a4_fallbacks.json` |
| `keccak.py` | pure-python keccak-256 so event topics are computed, not recalled; self-tests against the canonical `Transfer` topic |
| `a5_v4_census.py` | the Uniswap V4 launch census → `v4_census.json`, `v4_signature.json` |
| `http_stats_total.json` | the spike's own cost: 1,029 calls |

All of it is throwaway, as instructed. Nothing here is designed to survive into
Part B.
