# Forward validation: the pre-registered result (2026-11-03)

**Protocol:** DECISIONS.md, Phase 8, fixed on 2026-10-19 before any outcome
existed.

**Data:** `reports/forward_validation.json`, from
`python -m scripts.phase8_report`.

**Model:** `buyer-loss-v1`, frozen. It has not been retrained, recalibrated
or re-thresholded since the test began.

**Scope:**
- Launches from 2026-10-19 to 2026-11-03.
- 25,583 logged; 8,259 scored on time and resolved at hour 6.
- 290 late scores are excluded, as the timely-only rule requires.

## 1. Pre-registered result: both criteria pass

| Criterion | Result | Pass? |
|---|---|---|
| Forward PR-AUC above the base rate, 95% interval of the difference above zero | 0.108 against 0.023; interval +0.055 to +0.124 | **Yes** |
| Self-deployed pull rate at 7 days above launchpad's | 89.2% (2,480) against 0.63% (2,370) | **Yes** |

The other pre-registered metrics:

**ROC-AUC:** 0.671.

**Calibration fails.** The Brier score is 0.038, worse than the 0.023
from always predicting the base rate. The mean prediction is 8.7%, against
2.3% observed. The reliability curve is far from the diagonal:

| Predicted | Tokens | Observed |
|---|---:|---:|
| 0.0–0.1 | 6,047 | 1.7% |
| 0.1–0.2 | 1,190 | 1.7% |
| 0.2–0.3 | 618 | 1.5% |
| 0.3–0.4 | 94 | 10.6% |
| 0.5–0.6 | 69 | 11.6% |
| 0.7–0.8 | 65 | 44.6% |
| 0.9–1.0 | 23 | 26.1% |

**Precision at risk ≥ 0.5:** 20%, with 232 tokens flagged.

The score ranks better than chance, but it is not a probability. A
recalibrated model would be a new, separately reported record (Phase 8
rule).

## 2. What it rests on (post hoc, added after seeing section 1)

### The label does not see liquidity pulls

Buyer loss is the hour-6 price against the minute-5 price. A pull leaves
the last price standing.

- 3,557 scored pools had their liquidity pulled by hour 6; only 6 of them
  are labelled losses.
- Phase 6 defined this label on tokens that were *not* rugged, so this is
  the training definition carried over. In the live record, however, it
  counts most self-deployed pools as "no loss".
- This explains the strange-looking base rates by type: 4.5% for launchpad,
  0.19% for self-deployed.

Re-scored on two populations:

| Population | Losses / tokens | Model PR-AUC | Launch type alone | Phase 6 checker | Model minus launch type, 95% CI |
|---|---|---:|---:|---:|---|
| Not pulled by hour 6 (the model's own population) | 185 / 4,703 (3.9%) | **0.152** | 0.033 | 0.031 | +0.083 to +0.162 |
| All pools, pull counted as a loss | 3,742 / 8,260 (45%) | 0.671 | **0.837** | 0.311 | −0.187 to −0.147 |

* **On the population it was built for, the model works forward.**
  - PR-AUC is 3.9 times the base rate, and ROC-AUC is 0.78.
  - It clearly beats launch type and both fixed checkers.
  - Within launchpad tokens alone: PR-AUC 0.171 against a 4.5% base rate,
    interval +0.087 to +0.175.
* **For the question a buyer asks ("will I lose my money?"), launch type
  alone is the better first test.** The model should be applied after it,
  to launchpad tokens. That is exactly the paper agent's policy, and it
  agrees with the paper agent's result (`reports/paper_agent.md`).

### The fixed rule checkers do not work forward

| Ranker | PR-AUC | ROC-AUC | Flagged | Precision |
|---|---:|---:|---:|---:|
| Phase 5 checker | 0.024 | 0.48 | 5,619 | 2.3% |
| Phase 6 checker | 0.025 | 0.52 | 6,259 | 2.3% |

Both checkers perform at the base rate. The model minus each checker:
+0.051 to +0.127. The "model beats the rule checker" result from Phases 5
and 6 holds forward.

### Coverage

- The longest gap is 33 hours (2026-10-19 22:05 PKT, the known outage).
- There are 16 gaps longer than 2 hours, mostly when the machine was off.
  25 Oct, 29–30 Oct and 1 Nov have about half the usual count.
- Gaps lose launches; they do not bias the scores of those kept, because
  only timely predictions count.

## Plain statement

The pre-registered forward test passes on both criteria, on 8,259 launches
the model had never seen. Three limits come with that:

1. The score is badly calibrated. Read it as a ranking.
2. The buyer-loss label ignores liquidity pulls, so the model answers
   "will the price fall, given the pool stays?", not "will a buyer lose
   money?".
3. For the second question, the launch-type rule is the first test, and
   the model adds value only after it, on launchpad tokens.
