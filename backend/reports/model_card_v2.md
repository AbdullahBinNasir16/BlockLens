# Model card v2 — BlockLens rug risk at launch + 5 minutes

Phase 5, Part C. Every number below is computed on the **random cohort after
2026-04-20 (EVAL)**: 187 tokens from 119 operator families, with 109 RUG,
true prevalence **58.3%**. That set was never seen by training or
calibration. Source: [`phase5_results.json`](phase5_results.json), from
`python -m scripts.phase5_model run`. The sampling design is in
[`sampling_design.md`](sampling_design.md). Rule `v2-2026-10`; features
`t5-2026-10`.

## Headline, stated plainly

1. **The model beats the pre-registered rule checker by a wide margin.**
   PR-AUC 0.999 against 0.485, family-bootstrap 95% CI of the difference
   [+0.346, +0.643].
2. **That margin is mostly a statement about the rule checker.** The
   pre-registered checker left out the most standard rug check there is,
   whether liquidity is locked. A one-line version of it, added after the
   results were seen, scores **PR-AUC 0.965, precision 0.965, recall 1.000**
   on its own. The model beats that too, but by **+0.034 [+0.007, +0.075]**.
3. **On this chain and population, the RUG label is close to decided at
   minute 0 by launch type.**
   * Self-deployed tokens, whose deployer holds withdrawable liquidity: 109
     of 113 rugged in EVAL.
   * Launchpad tokens, minted and supplied with liquidity in a single
     factory transaction: 0 of 74.
   * Inside either group there are fewer than 10 tokens of the minority
     class, so nothing remains to predict and nothing can be evaluated.
4. **Part D: the graph features add nothing, at token level or at wallet
   level.** At token level the experiment is at ceiling. At wallet level it
   is properly powered, with 10,680 wallets, and graph position does not
   predict dumping. Details below.

## What is predicted

Given only what is observable in a token's first five minutes on Base: will
its pool's liquidity be pulled (v2 RUG: a ≥ 90% token-reserve collapse
between consecutive samples, within 90 days)? Only tokens still alive at
minute 5 are scored. This is the product question, and it is the fix for
Part A's censoring.

## The three baselines, on the same split

| model | features | PR-AUC | ROC-AUC | P@10 | P@25 | P@50 | Brier, raw → calibrated |
|---|---|---|---|---|---|---|---|
| **rule checker (pre-registered)** | 5 flags | **0.485** | 0.074 | 0.10 | 0.04 | 0.10 | – |
| logistic regression | all 23 | 0.996 | 0.992 | 1.00 | 1.00 | 1.00 | 0.019 → 0.047 |
| gradient boosting | all 23 | **0.999** | 0.999 | 1.00 | 1.00 | 1.00 | 0.0125 → 0.0128 |

The pre-registered rule checker is worse than random: ROC-AUC 0.074 means it
ranks safe tokens above risky ones. Its *thin* and *concentrated* flags fire
on launchpad tokens, which are the ones that almost never rug. As a verdict
(≥ 2 flags) it flags 59 tokens, with precision 0.085 and recall 0.046. It is
reported exactly as it was fixed, because a baseline adjusted after seeing
the results is just another model.

**Post hoc, and labelled as such:**

| rule | PR-AUC | precision | recall |
|---|---|---|---|
| liquidity not locked by a launchpad (no mint + LP in one transaction) | 0.965 | 0.965 | 1.000 |
| pre-registered checker + that rule | 0.934 | – | – |
| gradient boosting, all features, minus that rule | 0.999 − **0.034** [0.007, 0.075] | | |

## Feature count, and where it saturates

The feature set is 23 token-level features, not Phase 4's 95 wallet-level
ones, so the brief's 10 / 30 / all curve becomes 5 / 10 / all. The ranking
was done on TRAIN only.

| features | logistic PR-AUC | boosting PR-AUC |
|---|---|---|
| top 5 | 0.996 | 0.998 |
| top 10 | 0.999 | 0.999 |
| all 23 | 0.996 | 0.999 |
| all but the launch-type feature | 0.966 | 0.985 |

Performance saturates at 5 features. Remove the launch-type feature and the
others recover most of it, because several of them (prior wallet activity,
funding, buyer concentration) differ between launchpad and self-deployed
launches.

## Permutation importance (EVAL, average-precision scoring, 30 repeats)

| feature | logistic | boosting |
|---|---|---|
| `r_mint_in_window` (launch type) | **0.216** | **0.163** |
| `t_first_buy_delay_s` | 0.011 | 0.000 |
| `t_same_block_buyers` | 0.002 | 0.000 |
| `g_prior_tokens_mean` | 0.002 | 0.000 |
| `t_reserve_vs_peak` | 0.001 | 0.000 |

Every other feature is ≤ 0.001. Split-based importance is not reported, for
the reason the brief gives.

## Calibration, before and after

* **Logistic regression, prior shift.** Before: tokens scored ≥ 0.9 are 92,
  all RUG. Those scored < 0.1 are 76, with 1.3% RUG. After the intercept
  correction, 43 tokens are scored between 0.3 and 0.8, and 80–100% of them
  are RUG: the correction **under-predicts**.
* **Gradient boosting, Platt scaling fitted on CAL.** Before and after: 76
  tokens < 0.1 (1.3% RUG), 103–106 tokens ≥ 0.9 (100% RUG). It is
  essentially unchanged and well calibrated.

The reason is in `sampling_design.md` §5. CAL and EVAL differ by covariate
shift: self-deployed launches went from 4–11% to 63–69% of the population.
P(RUG | launch type) is stable across months, so a correction tuned to
January–April prevalence is the wrong correction for May–July. Full
ten-bin tables are in `phase5_results.json` under `reliability_before` and
`reliability_after`.

## Decay, by launch month (EVAL)

| month | tokens | RUG | rule checker | logistic | boosting |
|---|---|---|---|---|---|
| 2026-04 (from 20th) | 7 | 3 | 0.429 | 1.000 | 1.000 |
| 2026-05 | 103 | 64 | 0.521 | 0.9995 | 0.9998 |
| 2026-06 | 45 | 31 | 0.591 | 1.000 | 1.000 |
| 2026-07 | 32 | 11 | 0.317 | 0.942 | 0.986 |

There is no meaningful decay across three months, which is what a label
decided by a structural fact should show. July is the weakest month: 2 of
its 13 self-deployed tokens did not rug.

## Part D: the graph features

Three models on the same split, family-bootstrap CIs.

| | logistic PR-AUC | boosting PR-AUC |
|---|---|---|
| entry timing (+ rule inputs), 16f | 0.995 | 0.999 |
| graph only, 7f | 0.915 | 0.962 |
| both | 0.996 | 0.999 |
| **both − timing** | **+0.001 [−0.001, +0.006]** | **+0.0003 [0.000, +0.0005]** |

Graph features alone score far above a label-shuffled null (null mean
0.593, 95th percentile 0.651). But they add nothing over timing, and the
reason is not that the graph is uninformative. Every model is at the
ceiling set by launch type, so there is no residual left for any feature
group to explain. **At token level, on LP-pull rugs, the hypothesis cannot
be tested on this population.** That is a statement about the label, not
about Abdullah's module.

The wallet-level test (option 2) is the one that *can* be run at power:

* **Units:** 10,680 early buyers across 317 random-cohort tokens.
* **Outcome:** sold at least 90% of what the wallet bought, within the first
  hour, measured after the cutoff. 33.1% of early buyers do.
* **Folds:** grouped by token.

| predictor (as of minute 5) | AUC |
|---|---|
| funded by the deployer | 0.507 (dump rate 69% vs 33%, but only 0.9% of wallets) |
| in the largest funding component among the token's buyers | 0.502 |
| has any funder | 0.513 |
| **graph position, all three (grouped CV)** | **0.518 ± 0.010** |
| own entry delay (grouped CV) | 0.602 ± 0.061 |
| both | 0.604 ± 0.063 |

### The Part D answer, not softened

**Outcome 3: the graph features add nothing anywhere, at full power, for the
questions this data can ask.**

* At token level they are redundant with launch type.
* At wallet level, graph position does not predict a wallet's own dumping
  behaviour (AUC 0.52), while the wallet's own timing does, weakly (0.60).

The one positive in the table is narrow. Deployer-funded wallets dump at
twice the base rate, which is an insider signal, but they are 0.9% of
buyers. That is too rare to move an AUC, and too few to be a screener
feature on their own.

Why a reasonable hypothesis from the literature did not replicate here:

1. **Base launches in 2026 are dominated by launchpads that mint and lock
   liquidity in one transaction.** On those, the funding-graph insider
   pattern the cited paper detects has no LP to pull.
2. **The edges are token-acquisition provenance, not ETH funding**, because
   no keyless funding index exists (Phase 3, Part A). The relationship the
   paper uses is mostly invisible here.
3. **The paper's setting is the one in which the graph matters:** a
   population where rug and non-rug launches look alike structurally. Ours
   does not look alike.

## What this model must not be used for, and what to do next

* **Not as evidence that rugs are predictable in general.** It predicts one
  rug mechanism, liquidity withdrawal, on a population where that mechanism
  is almost entirely gated by launch type. A token checker that only asked
  "is liquidity locked?" would get 96.5% precision.
* **Not on launchpad tokens.** For them the model's answer is always "won't
  be LP-pulled". That is true and useless, because 99% of them become
  FAILED.
* **Not as a calibrated probability across regimes.** The launch-type mix
  shifted sevenfold in three months.
* **The real open problem is inside FAILED.** Launchpad tokens die by supply
  dumping, not liquidity removal. A v3 label that separates a dev or insider
  dump from organic decay among launchpad tokens is where the graph module,
  the deployer-funded-wallet signal and timing would be tested on a question
  that is not already answered at minute 0. That is the recommended next
  step before any of this reaches the UI.
