# Phase 6 — how FAILED tokens fail, and what can be predicted about it

Sources: `data/phase6_extraction.json` (`python -m scripts.phase6 run`) and
[`phase6_results.json`](phase6_results.json) (`python -m scripts.phase6_model`).
Definitions: `blocklens/label/extraction.py`. Pre-registration:
`blocklens/model/rulecheck_x.py` and DECISIONS.md, written before results.

## 1. The answer to "insider dump or organic decay?"

**Organic decay, overwhelmingly.** Of 593 non-RUG tokens alive at minute
5, measured over their first six hours:

| mode | tokens | share |
|---|---|---|
| DECAY: no material cash transfer from later buyers to earlier ones | 552 | 93.1% |
| **EXTRACTED**: the minute-5 cohort took out ≥ 25% of later buyers' money in realised cash, and later buyers lost | **22** | **3.7%** |
| UNCLEAR: < 80% of swaps priced | 19 | 3.2% |

The finding holds across the threshold grid: 14–27 tokens EXTRACTED for an
extraction share of 0.1–0.5 and a late-spend share of 0.05–0.25. In the
random cohort, EXTRACTED is 13 of 168 judged tokens before April and **0 of
78 after**.

What a failed launchpad token actually looks like:

* **A median of 14 swaps in six hours,** 4 early wallets and 2 later ones.
  In a quarter of tokens nobody at all arrives after minute 5.
* **Later buyers lose:** their realised cash is a median −96.5% of what
  they spent.
* **The early cohort is usually net negative in cash too** (median −0.99 of
  late spend). Nobody took the money out. It sits in the pool's
  single-sided position, backing tokens that buyers still hold and can no
  longer sell back at the price they paid.
* **The launch price is a floor.** The median token's price at day 90 is
  its launch price, so there is no "collapse" for an insider to exit before.
  That is why the first definition was rejected in the pilot (DECISIONS,
  Phase 6).

Plainly: on this population, a failed token is not usually a scheme. It is
a handful of wallets, many of them bots, trading among themselves for
minutes, after which nobody comes.

## 2. T1 (EXTRACTED) cannot be modelled

* **Training holds 9 positives.** The pre-registered evaluation set (random,
  after 20 April) holds 0 EXTRACTED, so no model was fitted.
* **The two fixed checkers, scored on the January–April random cohort**
  (13 positives in 168, prevalence 7.7%), are both at or below chance:

  | checker | PR-AUC |
  |---|---|
  | Phase 5 five-flag | 0.125 |
  | early-concentration (pre-registered) | 0.073 |

## 3. T2 (BUYER_LOSS): a real result

**Target:** a buy at the minute-5 price is worth at most half as much at
hour 6. This is the question a user in front of a live token actually has.

**Deviation from the pre-registration, stated plainly.** The pre-registered
evaluation set (random, after 20 April) has 3 positives in 78, so it can
evaluate nothing. Results are instead on the **January–April random cohort**:

* 179 tokens, 148 families, 64 losses (prevalence 35.8%);
* true prevalence, and no family shared with training;
* out of sample, but **not out of time**;
* no third set to calibrate on, so only ranking metrics and raw Brier.

Launch type does not decide this target: 175 of the 179 are launchpad
tokens.

| model | features | PR-AUC [95% CI, family bootstrap] | ROC-AUC | P@10 | P@25 | P@50 | Brier |
|---|---|---|---|---|---|---|---|
| Phase 5 rule checker | 5 flags | 0.365 [0.259, 0.488] | 0.498 | 0.30 | 0.32 | 0.42 | – |
| early-concentration checker (pre-registered) | 5 flags | 0.370 [0.283, 0.475] | 0.532 | 0.30 | 0.36 | 0.36 | – |
| logistic regression | all 23 | 0.643 [0.531, 0.769] | 0.737 | 0.80 | 0.80 | 0.56 | 0.194 |
| **gradient boosting** | all 23 | **0.833 [0.731, 0.911]** | 0.883 | 0.90 | 0.92 | 0.84 | 0.127 |

**The model beats both pre-registered checkers.** Boosting against the
early-concentration checker: +0.36 to +0.55 PR-AUC, positive in 100% of
2,000 family resamples. Both checkers sit at the base rate, which is what a
checker with no information looks like.

**It is not one feature in disguise** (post hoc, after the Phase 5 lesson):

| | PR-AUC |
|---|---|
| best single feature, run-up by minute 5 (`t_log_price_drift`) | 0.575 |
| reserve at minute 5 vs its peak, alone | 0.537 |
| boosting without the run-up feature | 0.653 |
| boosting, all, minus the best single feature | +0.16 to +0.34 |

Permutation importance (boosting): the run-up by minute 5 (0.335),
reserve vs peak (0.117), swap count (0.102), first-buy delay (0.073), then
small contributions from buyer concentration and funding. In words: a token
that has already run up sharply by minute 5, on few swaps and early buyers,
and whose pool has already started to give tokens back, is a token whose
minute-5 buyer loses.

### Out of time, checked afterwards (2026-10-19)

The CAL result above is not out of time. Two follow-up checks are:

* **Inside January–April, split by date.** Train on launches before 1
  March, test on random-cohort launches from 1 March to 17 April (57
  tokens, 20 losses). Boosting scores 0.758 [0.393, 0.883] against the
  early-concentration checker's 0.331. The difference is +0.13 to +0.59,
  positive in every resample. A 15 March cut leaves 26 test tokens, too few
  to read.
* **May–July, where buyer loss nearly vanished** (3 of 78). The model,
  trained on January–April, predicts a mean risk of 0.119, flags 5 tokens
  at ≥ 0.5, and 3 of those are the 3 losses, ranked 2nd, 3rd and 4th of
  78. Brier 0.030 against 0.037 for always predicting the base rate. It
  follows the regime change instead of raising false alarms. With three
  positives this is suggestive, not a measurement.

## 4. Part D, re-run on a target launch type does not decide

| | logistic PR-AUC | boosting PR-AUC |
|---|---|---|
| timing (+ rule inputs) | 0.608 | 0.828 |
| graph only | 0.451 | 0.543 |
| both | 0.643 | 0.833 |
| **both − timing** | **+0.035 [−0.016, +0.084]** | **+0.005 [−0.028, +0.033]** |

* **Graph features alone beat a label-shuffled null:** boosting 0.543
  against a null 95th percentile of 0.443, logistic 0.451 against 0.438.
  They carry signal.
* **They add nothing detectable over timing.** The boosting interval
  straddles zero tightly. The logistic difference is positive in 91% of
  resamples, which is suggestive but not a finding.
* **The wallet-level test from Phase 5 stands:** graph position predicts a
  wallet's own dumping at AUC 0.52.

**Part D outcome: 3, now on a target that is not saturated.** On a powered
experiment where the answer is not decided at minute 0, Phase 3's graph
features contain information, but nothing that entry timing and flow do not
already carry. This is the negative result the Phase 5 brief anticipated,
from an experiment that can now resolve it. The reasons it did not
replicate are in `model_card_v2.md`, and the launchpad structure in §1 adds
one more: there is rarely a coordinated insider group to find.

## 5. Limits

* **Out-of-time evidence is thin:** 57 test tokens for the date split, 3
  positives for May–July. A buyer-loss score shown in the UI must say which
  period it was validated on, and on how many tokens.
* **The early cohort includes bots**, deliberately: they are early traders.
  "EXTRACTED" describes where cash went, not who intended what.
* **Realised cash undercounts value moved** when tokens are moved
  wallet-to-wallet and sold elsewhere. That would affect EXTRACTED, not T2,
  which is read from the pool price.
