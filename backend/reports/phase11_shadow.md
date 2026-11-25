# Phase 11: shadow scores, result (2026-11-25)

**Protocol:** `DECISIONS.md`, Phase 11, pre-registered 2026-11-03 before any
fit. One recorded deviation (2026-11-16): the evaluation set starts when
the block-time fix was deployed (16 Nov 06:30 UTC), not on 4 Nov.

**Numbers:**
- Section 1: `reports/shadow_scores.json`, from
  `python -m scripts.phase11_shadow report`.
- Section 2: `reports/shadow_scores_posthoc.json`, from
  `python -m scripts.phase11_posthoc`.
- Both were run on 25 Nov, back to back, on the same rows.

**The two scores** are both computed from v1's `risk` and `launch_type`.
Neither is shown in the product.
- **A** recalibrates v1's buyer-loss risk.
- **B** predicts buyer loss **or** a liquidity pull by hour 6.

Both were fitted once, on 8,296 launches before 3 Nov 12:00 PKT, and never
refitted.

**Evaluation set:** 2,333 timely, resolved, valid launches from 16 Nov
11:32 to 20 Nov 19:43 PKT. It has 534 buyer losses and 1,232 `y_B`
positives. The floor is 2,000 launches with 50 losses, and it is passed.

## 1. Pre-registered result: both criteria pass

**Score A.** Criterion: its Brier score is below that of a constant
prediction at the fitting set's base rate (0.0236), with the interval of
the difference below zero.

| Measure | Value |
|---|---|
| Brier, score A | 0.2083 |
| Brier, constant at 0.0236 | 0.2186 |
| A minus constant, 95% interval | −0.0118 to −0.0090 |
| **Criterion** | **Pass** |

Also reported:
- **v1's raw risk:** Brier 0.1501.
- **Average prediction:** 0.027 from A, against an observed rate of 0.229.
- **Ten-bin reliability:**

| A's bin | Launches | Mean predicted | Observed |
|---|---:|---:|---:|
| 0.0–0.1 | 2,299 | 0.025 | 0.224 |
| 0.1–0.2 | 31 | 0.133 | 0.581 |
| 0.2–0.3 | 2 | 0.230 | 0.500 |
| 0.3–0.4 | 1 | 0.325 | 1.000 |

**Score B.** Criterion: its PR-AUC for `y_B` exceeds that of launch type
alone, with the interval of the difference above zero. Its Brier score is
below the fitting set's constant `y_B` rate (0.454).

| Measure | Value |
|---|---|
| PR-AUC, score B | 0.890 |
| PR-AUC, launch type alone | 0.739 |
| B minus launch type, 95% interval | +0.136 to +0.167 |
| Brier, score B | 0.2155 |
| Brier, constant at 0.454 | 0.2547 |
| **Criterion** | **Pass** |

By the pre-registered test, **both scores succeed.**

## 2. What the evaluation set is made of (post hoc)

This section was written after section 1 was seen. It changes nothing in
section 1.

**The base rate moved.** Buyer losses were 2.4% of the fitting set and
22.9% of the evaluation set.

**One launch family carries almost all of the change.** It is the scam
template first recorded on 3 Nov (`DECISIONS.md`, 2026-11-16):
- a Uniswap V4 pool seeded with 1.5 B tokens;
- about two hours of trading;
- then a sale of 500 M tokens into the pool.

It is tagged here by the seed: a token reserve at minute 5 between
1.49e27 and 1.50e27 base units. The earlier tag, an exact ×34,600 minute-5
run-up, misses later variants, whose seeding swap differs.

| Set | Part | Launches | Buyer losses | Loss rate | v1 mean risk |
|---|---|---:|---:|---:|---:|
| Fitting | the family | 40 | 28 | 70.0% | 0.591 |
| Fitting | other launchpad | 4,099 | 160 | 3.9% | 0.065 |
| Fitting | self-deployed | 4,184 | 8 | 0.2% | 0.105 |
| Evaluation | the family | 611 | 498 | 81.5% | 0.221 |
| Evaluation | other launchpad | 944 | 34 | 3.6% | 0.050 |
| Evaluation | self-deployed | 778 | 2 | 0.3% | 0.099 |

The fitting-set rows total 8,323, not the 8,296 the scores were fitted
on: 27 launches from before 3 Nov resolved after the fit on 3 Nov.

- The family went from 0.5% of the fitting set to 26% of the evaluation
  set.
- Outside it, the loss rate is the same in both sets: 3.6–3.9% for
  launchpad, and 0.2–0.3% for self-deployed.
- v1 scores the family lower than before: a mean risk of 0.221, against
  0.591.

**The same evaluation on each part:**

| Measure | All (2,333) | The family (611) | Without the family (1,722; 36 losses) |
|---|---|---|---|
| A: mean predicted / observed | 0.027 / 0.229 | 0.043 / 0.815 | **0.021 / 0.021** |
| A: Brier / constant / v1 raw | 0.208 / 0.219 / 0.150 | 0.739 / 0.777 / 0.479 | 0.0201 / 0.0205 / 0.0333 |
| A minus constant, 95% interval | −0.012 to −0.009 | −0.042 to −0.035 | −0.0012 to +0.0002 |
| v1 PR-AUC for buyer loss | 0.610 | 0.949 | 0.099 (base 0.021) |
| B: PR-AUC / launch type | 0.890 / 0.739 | 0.949 / 0.815 | 0.911 / 0.878 |
| B minus launch type, 95% interval | +0.136 to +0.167 | +0.107 to +0.165 | +0.016 to +0.053 |
| B: Brier / constant | 0.216 / 0.255 | 0.630 / 0.281 | 0.069 / 0.245 |

Facts from this table:
- **Without the family:**
  - A's average prediction equals the observed rate, and its Brier score is
    lower than v1's raw risk (0.0201 against 0.0333).
  - But the interval of A's difference from the constant crosses zero, so
    A's criterion would not pass on this part alone.
- **On the whole set:**
  - A's pass comes from the family, where A predicts 4% against 81.5%
    observed.
  - v1's raw risk has a lower Brier score than A, because v1 predicts
    higher.
- **B beats launch type on both parts.** On the family, B's Brier score is
  worse than the constant's.
- **Without the family there are 36 losses.** That is under the floor of
  50, so these per-part numbers are descriptive only.

## Limits

- The family is tagged by a rule written after the result was seen. It
  matches the one recorded on 3 Nov, but it is still a post-hoc
  definition.
- The evaluation covers about four days of launches, 16–20 Nov.
  Resolution runs behind; the backlog is in `honest_results.md` item 7.
- The 6-hour buyer-loss label does not count pulls (`honest_results.md`
  item 10). Score B exists for that reason.

> **[Ours to write]** What the pre-registered pass means, given section 2.
> Whether A is the calibration slide 8 asked for. Whether either score
> should replace v1's display.
