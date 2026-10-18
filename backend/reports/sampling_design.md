# Sampling design — Phase 5, Part B

How a dataset with power was built from a population where the outcome of
interest is rare, and how the evaluation was kept honest despite that. Every
count here comes from `token_sample`, `token_label` (rule `v2-2026-10`) and
`reports/phase5_windows.json`. The per-class tables and launch histograms are
in [`phase5_counts.md`](phase5_counts.md). Code: `blocklens/sampling/design.py`
and `scripts/phase5.py`.

## 1. The population

**Uniswap V3/V4 pools on Base, launched 2026-01-20 to 2026-07-19, alive at
launch + 5 minutes.** "Alive" means three things, all observable at minute 5:

* at least one swap at or before minute 5,
* at least one more swap within the following hour (checked from stored
  swaps after backfill; the screen checks the following ~33 minutes),
* the pool's token reserve at minute 5 still above 10% of its running peak.

This follows from the Part A audit. A 24-hour feature window contained every
rug in the Phase 4 data, so the features described the outcome. A 5-minute
window with a survival requirement asks the product question: this token is
alive in front of you, will its liquidity be pulled? Of 137,852 discovered
pools, 1,066 met the definition (0.77%). Most pools never trade at all.

## 2. The strata

| stratum | how a token gets in | used for | tokens alive | labelled |
|---|---|---|---|---|
| `random` | every pool created in a uniformly placed 1,000-block window, one per week for 26 weeks, outcome-blind | calibration (before split) and **all headline metrics** (after split) | 458 | 458 |
| `train_case` | separate uniform windows (10 per pre-split week); passed the screen; coarse reserve drop ≥ 80% | training only | 189 | 166 |
| `train_control` | same windows; passed the screen; a seeded 20% Bernoulli draw of the rest | training only | 416 | 356 |
| `survivor_enum` | trading today, created in the period (GeckoTerminal pool lists) | training only | 3 | 3 |
| `phase2` | Phase 2's 75 tokens | nothing; kept only for the v1→v2 comparison | – | 75 |

Every token carries its `sampling_stratum`, set when it first entered. First
stratum wins, and the random cohort was drawn first.

### Why the training strata are case-control and not class quotas

The brief planned class targets (RUG 400, FAILED 300, SURVIVED 300). The
first random labels showed the actual prevalence: RUG is **8.7%** of the
random cohort before the split and SURVIVED is **0.2%** overall (1 of 458).
Labelling blind until 400 RUGs appeared would have needed ~5,000 full
labels, about two days of collection.

So the training strata sample on a **proxy of the outcome**, which is
standard case-control design. Every training candidate first gets the
labeller's own nine coarse reserve points (~20 calls, no backfill). Tokens
whose coarse series shows a ≥ 80% reserve drop become cases, and a seeded
Bernoulli 20% of the rest become controls. Both then go through the
unchanged v2 labeller. The proxy selects well: 151 of the 166 labelled cases
are RUG (91%), and none of the 356 labelled controls is.

The deliberate SURVIVED stratum mostly failed. Of 96 currently trading pools
created in the period, 56 could not be matched to an on-chain creation event
near GeckoTerminal's stated creation time, and 3 passed the population
screen. **SURVIVED is not a modellable class here (6 examples in total)**,
and the binary target is RUG against FAILED + SURVIVED, as Phase 2 defined
it.

## 3. Time

* **Split date: 2026-04-20.** Training strata launch strictly before it.
* The random cohort is split at the same date. **CAL** (before, 196
  outcome-labelled tokens) is used only to calibrate. **EVAL** (after, 187
  tokens) is used only to report.
* So every headline number is out of sample *and* out of time. The model
  never sees a launch from the evaluation months, in training or in
  calibration.

## 4. Operator families

Phase 4's positive class was one operation. Families are computed over every
alive sampled token, before training-stratum labelling:

* **Linked** if the tokens share a deployer key (first mint recipient, or
  first liquidity sender into the pool), or share at least two early buyers
  and launched within 24 hours of each other.
* **Never linking:** any address active across more than 7 days (launchpad
  factories, routers, sniper bots), and any wallet that bought 50+ launches.
* **Result:** 1,066 alive tokens in 841 families. 793 families are
  singletons, and the largest has 67 tokens.

How families are enforced:

* At most 3 labelled training tokens per family (9 tokens set aside).
* **No family on both sides of the split.** 74 training tokens were set
  aside because their family appears in the random cohort, plus 1 more
  caught when the sets were assembled.
* Every confidence interval in the model card resamples families, not tokens.

The evaluation set's 109 RUGs come from 75 different families.

## 5. The correction

* **Train** on the strata (31% RUG by construction).
* **Logistic regression:** the King–Zeng prior correction. The intercept
  moves by logit(true rate) − logit(sampled rate), with the true rate taken
  from CAL (8.67%).
* **Gradient boosting:** Platt scaling fitted on CAL.
* Reliability tables before and after both corrections are in the model
  card.

The correction assumes the class-conditional distributions are the same in
CAL and EVAL. **That assumption fails here, and the data says why.** RUG
prevalence in the random cohort jumps from 8.7% (Jan–Apr) to 58% (late
Apr–Jul). The risk *within* each launch type is constant: self-deployed
tokens rug 95–100% of the time in every month, and launchpad tokens almost
never. What changed is the mix: self-deployed launches were 4–11% of alive
launches in Jan–Mar and 63–69% in May–Jun. That is covariate shift. The
intercept correction, fitted to the earlier prevalence, makes the logistic
model *less* calibrated on EVAL (Brier 0.019 raw against 0.047 corrected),
and this is reported rather than quietly dropped.

## 6. Budget

The keyless sources have no monthly allowance to exceed: the RPC ledger
before Phase 5 stood at 63,608 requests this month, against no ceiling. The
binding constraint is wall-clock time at a polite rate, so that is what was
budgeted.

| step | calls | hours | per unit |
|---|---|---|---|
| discovery + screen (146 windows, 137,852 pools) | 7,995 | 1.4 | ~55 per window |
| coarse pre-screen (2,226 training tokens) | 41,580 | 1.1 | ~19 per token |
| backfill, first hour (1,078 tokens) | 5,873 | 1.1 | ~5 per token |
| labels, v2 (983 tokens) | 241,342 | 5.8 (worker-hours) | ~245 per token |
| survivors | 179 | 0.1 | |
| **total** | **297k** | | |

The plan in the brief (1,500 blind labels at ~245 calls) would have cost
~370k calls. The case-control design spent 297k and produced 152 training
RUGs rather than the ~40 that blind labelling of the same discovery windows
would have.

Throughput came from two changes, both verified before use:

* **JSON-RPC batching.** `scripts.phase5 verify-batch` re-read 72 stored
  Phase 2 points and matched all 72 exactly.
* **A pool of four keyless providers** (`PooledRpcSource`). Each provider is
  paced at no more than about one HTTP request per second per worker, with
  per-provider back-off on 429.

As the brief instructed, the random cohort was reduced last. It is 458
against a target of 500; the shortfall is 8%.

## 7. Deviations from the brief, stated plainly

1. **Class targets became case-control strata.** RUG 152 against 400,
   FAILED 331 against 300, SURVIVED 5 against 300. SURVIVED is
   unattainable at a 0.2% base rate without a different enumeration source.
2. **Random cohort 458 against 500.**
3. **Launches span six months (Jan 20 to Jul 19)**, but as the counts file
   shows, the random cohort's RUGs are concentrated after April. That
   concentration is the covariate shift described above, not a class/month
   artefact of the sampling: the training strata are spread Jan–Apr and the
   random cohort is uniform in time.
4. **The rule checker was pre-specified with five flags and no
   liquidity-lock rule.** See the model card for what that omission meant.
