# Leakage audit — Phase 5, Part A

Generated 2026-10-18 from `token_label` (`v1-2026-10`) and `wallet_feature`
(`f1-2026-10`) on Base. Every number below is in
[`leakage_audit.json`](leakage_audit.json), written by
`python -m scripts.leakage_audit`, which reads the store and changes nothing.
The code is `blocklens/model/audit.py`.

## Verdict

**The Phase 4 result does not survive the audit, and neither of its two
claims can be made.** "Entry timing predicts rugs" fails on three
independent grounds below, and any one of them would be enough. "Graph
features carry no signal" was never supported: the experiment that produced
it had, in effect, **one positive example**.

| | Result |
|---|---|
| Rugs that were still alive at the end of their own feature window | **0 of 28** |
| Phase 4 timing-only AUC, as published (logistic / boosting) | 0.793 / 0.970 |
| Same model, trained only on rugs still alive at window end | **not estimable: 0 positives** |
| Token-level AUC of mean wallet entry delay | **0.544** (no signal) |
| RUG tokens in the feature set that share wallets with one another | **20 of 20**, one component |
| Feature rows whose `base_*` block is identical across the wallet's tokens | 407 of 667 |
| Hours between the first and last launch in the feature set | **0.84** (50 minutes) |
| RUG positives that are pools initialised at an untradeable price | 8 of 20 |

---

## A1. Censoring — present, and total

**Test.** For every labelled token, the moment of death is measured from
transfers inside launch + 24h: the first time the pool's holdings of the
token fall to 10% of their running peak, which is Phase 2's 90% drop. The
label's own `largest_drop_ts` can't answer this. It is the first *sample*
after the drop, and Phase 2 samples six hours apart near launch, so for 27
of 28 rugs it reads exactly "hour 6".

**Result.**

| | All labelled | In the feature set |
|---|---|---|
| RUG tokens | 28 | 20 |
| rugged **inside** the 24h window | **28** | **20** |
| rugged **after** the window | **0** | **0** |
| rug minute, median (p25–p75) | 15.4 (0.0–17.3) | 6.8 (0.0–15.7) |
| last trade minute in window, RUG, median | 17.3 | 17.5 |
| last trade minute in window, FAILED, median | 4.3 | 8.5 |

Every rug in this dataset happened inside its feature window, nearly all in
the first twenty minutes. A wallet's "entry delay" on such a token is
bounded by the token's death, which is the outcome itself.

**Both numbers, side by side, as required:**

| Model | Phase 4, all tokens | Rugs alive at the end of their window vs controls |
|---|---|---|
| logistic, timing only | AUC 0.793 ± 0.154 | **not estimable** — 0 positive tokens |
| boosting, timing only | AUC 0.970 ± 0.027 | **not estimable** — 0 positive tokens |

The second column can't be filled, and that is the result. There is no
token in the set on which the Phase 4 model could have been predicting
rather than describing.

**A further check.** At token level, rather than per wallet, the signal
disappears:

| Single variable, token level (44 tokens) | AUC |
|---|---|
| mean wallet entry delay | 0.544 |
| minute of the last trade in the window | 0.435 |
| Spearman correlation between the two | 0.745 |

Entry delay is mostly a reading of when trading stopped (ρ = 0.745), and
neither one separates RUG from FAILED tokens. The 0.970 was a property of
rows, not tokens, and the next section explains which rows.

## A2. The fix — recommendation, not yet implemented

The distribution has to come first, because it fixes the shortest window
that can work. Tokens still trading at minute N, and not yet at the reserve
floor:

| N (min) | RUG alive | of 28 | FAILED alive | of 45 |
|---|---|---|---|---|
| 1 | 20 | | 27 | |
| 2 | 20 | | 23 | |
| **5** | **20** | | **18** | |
| 10 | 15 | | 15 | |
| 15 | 15 | | 13 | |
| 30 | 3 | | 12 | |
| 60 | 2 | | 10 | |

The 8 rugs missing from minute 1 onward are the untradeable pools under A3
(their "reserve" is gone at minute 0, by a measurement that means nothing).

**Recommendation: option 1, a short window with a survival requirement, at
N = 5 minutes,** with N = 2 and N = 10 as sensitivity runs. This agrees
with your instinct, and the distribution is the reason, not the precedent:

* At 5 minutes every genuine rug in the set is still alive and still has
  about 10 minutes to go (median death at about 15 minutes). That is the
  real product question: "this token is alive in front of me, will it be
  pulled?"
* At 30 minutes the RUG class is nearly gone (3 of 28). A window long
  enough to see "behaviour" is a window that can only contain the rugs that
  haven't happened yet, which is the censoring problem again with a
  different number.
* What it costs: FAILED tokens drop from 45 to 18 at N = 5, because most of
  them never trade after minute 5. They are excluded, not relabelled.
  "Never got a second trade" is not a class we can predict at minute 5,
  because by minute 5 it has already happened.

**Why not survival modelling.** It is the more defensible framework in
general, but on this population it buys almost nothing. Every rug happens
in the first 6 hours, and none in the window between 24h and the 90-day
horizon, so a time-to-rug model would be estimating a hazard that is
essentially a single early spike. That is the binary question at N
minutes, at much greater cost and much harder to present. It is worth
revisiting if Part B produces a population with real late rugs; the
`survival_by_minute` table will show that immediately.

The TON paper's precedent (predict within an hour from the first five
minutes) is consistent with this, and worth citing for the window length.
It should not be cited as support for the result until the result exists.

## A3. Leakage sweep

### 1. Features computed beyond the window — clean

All 667 feature rows have `as_of_ts` exactly at launch + 24h
(`feature_rows_with_cutoff_not_launch_plus_24h: 0`), and every query in
`graph/features.py`, `graph/funding.py` and `graph/build.py` filters on
`block_ts <= as_of` before it aggregates. Nothing is computed from the full
token lifetime. **No fix needed.**

### 2. Features derived from a field the labeller used — clean by name, but the label itself is a problem

No feature reads `peak_reserve`, `reserve_at_end`, `peak_price`,
`price_at_end`, the drop fields, `active_days` or the outflow fields (none
of the 21 clean feature names match). Peak reserve in particular is never a
feature. The overlap that *does* exist is the activity-count one Phase 4
already removed (64 features), plus the censoring above, which is overlap
in *time* rather than in fields.

Reading the RUG rows to check this turned up a problem with the label
itself:

* **8 of the 20 RUG tokens in the feature set** come from one deployer
  (`0xe85a…83a9`), all with `peak_price` = 3.40 × 10³⁸ = 2¹²⁸, i.e. pools
  initialised at the extreme of Uniswap's price range, where no one can
  trade. Their largest outflow is **20.4×** the measured "peak reserve",
  which can't be true of a real reserve. These are spam or test pools, not
  launches, and labelling them RUG is a measurement artefact.
* For **all 20**, `price_at_end` equals `peak_price` exactly. For the 12
  that aren't degenerate, that is consistent with liquidity being withdrawn
  (removing liquidity doesn't move the price, and nothing trades
  afterwards). But it means no RUG in this set was ever *priced* as a
  collapse, and the label rests entirely on the token-side reserve, which
  is all Uniswap V4 lets us read.

**Fix (for Part B):** a degenerate-pool filter before labelling: initial
price at either sqrt-price bound, or a largest outflow greater than the
peak reserve, means `NEVER_LAUNCHED`, not RUG.

### 3. Cross-token leakage through the wallet — present, and it is most of the Phase 4 score

You suspected this one, and it's there. `load_wallet_behaviour` aggregates
a wallet's trades over **every** token it touched up to the cutoff. So the
`base_*` block of a feature row describes the wallet, not the
(wallet, token) pair.

| | |
|---|---|
| feature rows | 667 |
| distinct wallets | 416 |
| wallets with rows on 2+ tokens | 158 |
| rows belonging to those wallets | 409 (61%) |
| of those, `base_*` vector identical across the wallet's tokens | **407** |
| most tokens one wallet appears on | 15 |

The consequence: the same wallet, carrying the same vector, sits in
training through token A and in test through token B. Grouping folds by
token does not prevent this.

The deeper problem it exposes: joining tokens that share any wallet gives
**16 components over 44 tokens**, and **all 20 RUG tokens fall in one
component** (26 tokens: 20 RUG, 6 FAILED; 572 of the 572 positive rows).
The remaining 15 components are all FAILED. So the positive class is one
interconnected operation, at least partly one deployer, sniped by the same
bot wallets. Phase 4 was learning to recognise that operation's wallets.

| Model, grouping | Timing AUC |
|---|---|
| Phase 4 features, folds by token (as published) | 0.793 / 0.970 |
| per-(wallet, token) timing features, folds by token | 0.734 / 0.820 |
| **any features, folds by shared-wallet component** | **not estimable** |

The last row is not estimable because it can't be: with every positive in
one component, any fold holding that component has no positives in
training. The effective number of independent positive examples is **one**.

**Fixes:**

* Applied now: `audit.per_token_timing` builds timing from the
  (wallet, token) pair alone, and `audit.shared_wallet_components` plus
  `audit.regroup` give the grouping. Both are used in this audit, and Part C
  must use them.
* For Part B: rebuild every `base_*` feature per (wallet, token), and make
  the **operator family** (shared-wallet component, merged with shared
  deployer) the unit of every split. Cap tokens per family when sampling.
  400 RUG tokens from five operators are five samples, not four hundred.

### 4. Train and test split by launch date — impossible on this data

Phase 4's `GroupKFold` was grouped but not temporal. The fold dates show
it:

| fold | test launches | train launches |
|---|---|---|
| 0 | 07-10 10:51 – 11:33 | 07-10 10:49 – 11:39 |
| 1 | 07-10 11:02 – 11:34 | 07-10 10:49 – 11:39 |
| 2 | 07-10 10:49 – 11:39 | 07-10 10:51 – 11:35 |
| 3 | 07-10 10:57 – 11:35 | 07-10 10:49 – 11:39 |
| 4 | 07-10 11:05 – 11:28 | 07-10 10:49 – 11:39 |

(times in PKT, UTC+5)

Every fold interleaves completely, because **all 44 tokens launched within
the same 50 minutes**. A temporal holdout was run anyway, cutting between
components. Training got 29 tokens (20 RUG) and the test side 15 tokens
with **0 RUG**, so no AUC exists. On this dataset a date split and a class
split are the same thing.

**Fix (for Part B):** launches spread over at least six months, as the
brief requires, with the per-class launch histogram printed before
training. The temporal split will cut between operator families, never
through one.

---

## What this means for the plan

1. **Withdraw both Phase 4 claims** from anything a supervisor sees. The
   model card now says so at the top. The correct statement is: *the
   Phase 4 dataset contains one positive operation, observed inside its own
   death window, and supports no conclusion about any feature group.*
2. **Part B targets change.** Counting tokens is the wrong unit. The
   targets should be in **operator families**: 300 RUG tokens from 300
   families is a dataset, and 300 from 10 is not. Sampling has to
   deduplicate by family before it counts.
3. **Three filters go in before labelling:** degenerate pools out;
   alive-at-N-minutes required; features per (wallet, token) at N
   minutes.
4. **The labelled stock is much bigger than it looks.** 1,103 complete
   windows exist and only 75 are labelled. The label run started today
   (run #88) is still marked `running` and appears to have stalled when the
   database stopped. Labelling the remaining ~1,255 tokens launched
   22 Jun – 12 Jul is the cheapest first step of Part B, but it covers
   three weeks, not six months, so it doesn't satisfy the spread
   requirement on its own.
