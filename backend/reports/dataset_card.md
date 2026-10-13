# Dataset card — BlockLens labelled launches

Generated 2026-10-13 10:20 UTC from `token_label` at rule version `v1-2026-10`.

## What this is

One row per token launch on Base, carrying an outcome 90 days after launch and the measurements that outcome was derived from. The features it is meant to be joined to are the first 24 hours of each token's transfers and swaps, collected in Phase 1.

## Composition

| | |
|---|---|
| chain | base |
| launches covered | 2026-07-09 to 2026-07-10 |
| rows in this version | 46 |
| in the usable set | 45 |
| observation window | 90 days |
| feature window | 24 hours |
| tokens in the store overall | 590 |
| transfers backing the features | 105,440 across 531 tokens |
| swaps | 18,765 |

## Classes

| Class | Count | Share | Meaning |
|---|---|---|---|
| RUG | 20 | 43.5% | token reserve collapsed inside one sampling window |
| FAILED | 24 | 52.2% | price collapsed or trading stopped, without a reserve collapse |
| SURVIVED | 0 | 0.0% | still holds its liquidity and still trades |
| UNCLEAR | 1 | 2.2% | none of the above, or too few observations to judge |
| NEVER_LAUNCHED | 1 | 2.2% | excluded, not a finding |

**Base rate: 44.4% of the usable set is RUG** (20 of 45).

Every metric decision downstream follows from that number. At this balance, accuracy is close to useless as a measure and precision and recall on the RUG class are what matter.

RUG and FAILED are kept apart on purpose. A token that collapsed because nobody wanted it is not a token whose deployer took the liquidity, and merging them would teach a model "this went down", which is not worth predicting. The binary target is RUG against the rest, and that collapse belongs at training time.

## What was excluded, and why

| Reason | Count |
|---|---|
| old enough, with a complete feature window | 370 |
| of those, traded at least once | 135 |
| **excluded: never traded** | 235 |

A pool nobody ever traded in is evidence about pool spam, not about rug pulls. On this chain that is most of what gets deployed: a single family of vanity-mined addresses accounts for hundreds of the tokens discovery found, each with a pool and no trades. Left in, they would dominate every class count and the base rate would describe a bot rather than a market.

## Known biases

- **Venue coverage.** Discovery reads Uniswap V4 `Initialize` and V3 `PoolCreated`. A launch on a venue with neither event is invisible to this dataset. Venues actually present:

| Venue | Tokens |
|---|---|
| uniswap-v4 | 45 |
| uniswap | 2 |

- **Quote coverage.** Only pools against a known quote asset are picked up, because a pool between two unknown tokens cannot be priced. Quotes present:

| Quote | Tokens |
|---|---|
| `0x0000000000000000000000000000000000000000` | 27 |
| `0x4200000000000000000000000000000000000006` | 15 |
| `0x833589fcd6edb6e08f4c7c32d4f71b54bda02913` | 5 |

- **No survivorship filter from DexScreener.** Discovery is on-chain, so unlike a dataset built from an aggregator's listings this one is not restricted to tokens that became well known enough to be indexed. Measured: DexScreener had indexed 3 of 400 tokens from one historical window. That bias is absent here, which is the main reason discovery was moved on-chain.

- **Sampling resolution.** 1 of 46 rows were decided from the coarse pass alone — nine observations across the window, taken because reserve and price were identical at every one of them. For those tokens nothing happened, so there was nothing to resolve more finely; the rest were re-sampled every 6 hours for a week and daily thereafter.

- **Migrations.** 0 token(s) showed liquidity leaving alongside a new pool appearing within 7 days, and were withheld from RUG. Sibling pools are counted from our own `pair` table, so a migration to a venue discovery does not watch, or to another chain, would be missed and could read as a rug.

## What this dataset cannot answer

- **Who pulled the liquidity.** `largest_outflow_to` records where the biggest outflow went, but attributing it to the deployer needs a funding cluster, which is Phase 3. No row claims attribution.
- **Whether a wallet was a bot, a sniper or a person.** `wallet.funding_source` is `unknown` throughout Phase 1.
- **Dollar values.** Prices here are ratios against each token's own quote asset, used only to compare a token to its own peak. Base launches are quoted in ETH, and without a historical ETH/USD series no dollar figure would be honest.
- **Intent.** The chain records liquidity moving. A rug and an abandoned honest project can look identical, and this dataset measures the movement, not the motive.
- **Anything about tokens younger than the observation window.** Those are refused, not labelled.

## Thresholds in force

| Threshold | Value |
|---|---|
| `rule_version` | v1-2026-10 |
| `liquidity_drop_fraction` | 0.9 |
| `drop_window_hours` | 24 |
| `collapse_fraction` | 0.05 |
| `peak_excludes_first_hours` | 1 |
| `dead_active_days` | 2 |
| `live_active_days` | 8 |
| `activity_window_days` | 30 |
| `live_reserve_fraction` | 0.25 |
| `min_reserve_floor` | 0.0 |
| `min_usable_fraction` | 0.8 |
| `min_swaps_in_window` | 1 |
| `migration_window_days` | 7 |
| `migration_liquidity_fraction` | 0.25 |

See `reports/label_sensitivity.md` for how far each of these can move before the class balance moves with it, and `DECISIONS.md` for why each number was chosen.

