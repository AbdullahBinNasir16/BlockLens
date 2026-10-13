# Model card — BlockLens rug risk

> **Withdrawn — see [`leakage_audit.md`](leakage_audit.md) (Phase 5, Part A).** Every rug in this dataset died inside its own feature window, all 20 RUG tokens belong to one shared-wallet operation, and 8 of them are untradeable pools. No result on this card, positive or negative, may be quoted.

Generated 2026-10-13T17:43 UTC from `wallet_feature` and `token_label` at `v1-2026-10` on `base`.

## What it predicts

Given a wallet's behaviour and its neighbourhood in the funding graph, as of 24 hours after a token launched: **will that token be classified RUG at 90 days?**

One row is a wallet, not a token. That is a deliberate choice forced by size — there are only 44 tokens with both features and a label, against 85 features, so a token-level model is p > n before it starts. Wallets within a token are **not independent**, so every split here is grouped by token and a token appears in exactly one fold.

## Data

| | |
|---|---|
| wallet rows | 667 |
| tokens | 44 |
| positive rows (RUG) | 572 (85.8%) |
| positive tokens | 20 (45.5%) |
| majority-class row baseline | 85.8% |

## The leakage problem, which dominates everything below

64 of 85 features were removed before training, and the reason is structural rather than incidental.

Phase 2 assigns `FAILED` partly through a `DEAD` criterion computed from **whether the price moved** — which is to say, from whether the token traded. Almost every behavioural feature measures how much a wallet traded. `base_buy_quote` scored AUC **0.922** on its own, and it is zero exactly when no priced swap exists, which is the same condition that sends a token to FAILED. A model fed those features learns a tautology and reports it as a discovery.

So the two columns below are not two tunings. The first is what the numbers look like when the model is allowed to read the label back out of the features; it is reported **only** to show the size of the effect, and must not be quoted as a result.

| Feature set | All features (leaky) | Leakage removed |
|---|---|---|
| flat | 0.972 ± 0.017 | 0.796 ± 0.153 |
| 1 hop | 0.972 ± 0.017 | 0.798 ± 0.152 |
| 2 hop | 0.977 ± 0.020 | 0.798 ± 0.151 |

**Permutation null**: shuffling labels at the token level and re-running the whole pipeline 25 times gives AUC 0.5481 ± 0.0859, with a 95th percentile of 0.6979 and a maximum of 0.7179. Any result below that 95th percentile is indistinguishable from noise at this sample size.

## Does propagation beat flat features?

**not detectably, on this data**: flat features score AUC 0.796 ± 0.153 and two-hop features 0.798 ± 0.151, a difference of +0.003 against a fold-to-fold spread of ±0.153.

That spread is the number to attend to. With 44 tokens across 5 folds, a difference smaller than the spread is not a finding. The cited paper's F1 0.93 against 0.81 cannot be confirmed or refuted at this size — it can only be left open.

## Where the signal actually lives

The surviving features are two different kinds of thing, and separating them answers the question Phase 3 exists to ask.

| Feature group | Logistic AUC | Boosting AUC |
|---|---|---|
| structure only (7f) | 0.585 ± 0.077 | 0.584 ± 0.077 |
| timing only (14f) | 0.793 ± 0.154 | 0.970 ± 0.027 |

**Graph structure alone is indistinguishable from noise** — 0.585 against a null mean of 0.5481 and a null 95th percentile of 0.6979. All of the measurable signal is in **entry timing**: wallets that buy sooner after a launch are trading tokens that go on to be rugged.

Entry timing is not merely a proxy for how many wallets a token had. That had to be checked — a token with 89 traders has a smaller *minimum* entry delay than one with 2, purely by order statistics — and the correlation between a token's wallet count and its minimum entry delay is **-0.127**, which is too weak to explain the result.

## What this model must not be used for

- **A deployment decision.** It is fitted on 44 tokens from a three-hour slice of one chain's history, with no SURVIVED examples at all, so it has never seen what a healthy launch looks like.
- **A number in a report, unqualified.** Any AUC here carries a fold-to-fold spread of the same order as the differences being discussed.
- **Ranking wallets by risk.** The target is a property of the token, inherited by its wallets. A high score means "this wallet is trading a token that looks like a rug", never "this wallet is a bad actor".

## What would change the answer

1. **More tokens.** The pipeline is built and the cost is known: about 44 calls to backfill a token and 235 to label it. Several hundred tokens is hours of unattended running, not new work.
2. **A label contrast that is not confounded with activity.** RUG against SURVIVED would compare two tokens that both traded. There are currently zero SURVIVED tokens, which is itself a finding about 95-day-old Base launches.
3. **Features not downstream of trade volume.** The surviving set is graph structure and entry timing. More of that kind — funding ancestry, which needs an indexing API — is the direction that does not re-introduce the leak.

