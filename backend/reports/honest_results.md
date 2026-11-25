# The results that were not what we hoped

Every item uses the same four headings: what we expected, what we found,
how we know, and what we did about it. Numbers come from the source named
in each item, and the headline ones also appear in `results/manifest.json`.

**Writing line:** this is evidence and factual description, written by the
tooling. How the report *frames* these findings, and what it argues from
them, is the team's to write. Each item ends with a marked hook for that.

---

## 1. Censoring: the feature window was measuring the outcome

**Expected.** The proposal froze inputs "exactly as they stood 24 hours
after launch" (slide 6), following TM-RugPull's rule of using only data
from before the event (slide 4).

**Found.**
- **All 28 RUG tokens** in the Phase 4 set rugged **inside** the 24-hour
  feature window. The median rug came 15.4 minutes after launch, and the
  label's drop time was hour 6 for all of them.
- Features over that window therefore included the rug itself. In
  particular, entry timing partly encoded how soon the token died.
- **All 20 RUG positives used by the Phase 4 model sat in one connected
  component** of shared wallets (26 of 44 tokens), so cross-validation
  folds shared operators.
- **8 of those were degenerate pools** (untradeable initial prices)
  labelled RUG.
- Phase 4's model scored **AUC 0.97–0.98** with all features, and **0.80**
  (fold range 0.58–1.00) once the leaking features were removed. Its
  permutation null averaged 0.548 (95th percentile 0.698).

**How we know.**
- `reports/leakage_audit.md` and `.json`: A1 censoring, A3 cross-token
  overlap (61% of feature rows came from wallets on 2+ tokens), and A3
  split dates (every Phase 4 fold came from one day, 10 July).
- `reports/model_results.json` for the Phase 4 scores.

**What we did.**
- The Phase 4 result was withdrawn (`model_card.md` carries the banner).
- Rule v2 makes degenerate pools NEVER_LAUNCHED.
- The cutoff moved to launch + 5 minutes, with a survival requirement:
  only tokens alive at minute 5 are scored.
- The dataset was redesigned as case-control strata plus a random cohort
  (`sampling_design.md`).
- Operator families are kept to one side of the split, and every interval
  is a family bootstrap.

> **[Ours to write]** Why this is a methodological finding, and how it
> bears on the complex-computing criterion.

---

## 2. Wallet-graph features add nothing measurable

**Expected.** "Wallet grouping is the core problem" (slide 4). The
proposal cited sybil detection at F1 0.930 with two-hop features (arXiv
2505.09313).

**Found.**
- On the random cohort before the split (179 tokens, 64 buyer losses),
  gradient boosting scores **PR-AUC 0.828 on timing features alone and
  0.833 with the graph added**. The 95% family-bootstrap intervals overlap
  almost entirely: 0.731–0.904 and 0.725–0.913.
- Graph features alone reach 0.543, above the 0.358 base rate but far
  below timing.
- Phase 5 reached the same outcome for RUG, and so did the wallet-level
  analysis ("outcome 3" in `DECISIONS.md`).

**How we know.** Figure 8; `reports/phase6_results.json` (family
bootstrap of boosting-all against boosting-timing); `DECISIONS.md` Phase 5
Part D and Phase 6.

**What we did.** The graph features stay in the model, because removing
them would change the frozen artefact. They are not credited with
anything, and the report states the null result. The clusters themselves
are validated separately: co-movement lift (Figure 9).

> **[Ours to write]** What a null result at this power does and does not
> rule out, and what it implies for Abdullah's FYP-2 module.

---

## 3. Dataset size: about 1,000 labelled launches, not 5,000

**Expected.** "Collect 5,000 launches" (slide 8).

**Found.**
- **1,058 tokens labelled** under rule v2, 983 of them alive at
  minute 5.
- The random cohort holds 458 (216 before the split, 242 after).
- 15,087 pools were discovered and screened to get there.

**Why.**
- Labelling a token needs archive reads of its pool across 90 days.
- The only keyless log endpoint caps a query at **1,000 blocks**.
- The Phase 5 set alone cost about **297,000 RPC calls**
  (`DECISIONS.md` Phase 5).

**What the design does about it.**
- **Case-control sampling** enriches the rare outcomes for power
  (training: 152 RUG, 331 FAILED).
- **The random cohort** gives true base rates (RUG 7.9% before the split,
  45.0% after; Figure 1).
- **A prior correction** maps sampled rates back to true ones.
- **Separately, the live forward record** adds **10,233 resolved
  launches**. These were judged by a frozen model before their outcomes
  existed, on a 6-hour buyer-loss and liquidity-pull label rather than the
  90-day one.

**How we know.** Figure 1; `phase5_counts.md`; `sampling_design.md`;
`results/manifest.json` → `dataset`.

> **[Ours to write]** Whether 983 plus 10,233 answers the 5,000 promise,
> and how the two datasets differ in what they can claim.

---

## 4. KOL scoring descoped

**Expected.** A KOL score computed from what promoters' calls actually did
(slides 3 and 6).

**Found.**
- The X API has no free tier for reading posts and charges per post read:
  about **$0.005 at its published price**.
- **This was never measured on a paid call.** No key was bought, and
  `xapi.py` is locked at 0 posts.
- Estimate: the measured launch rate (about 700 scored a day) × an assumed
  20 post reads per launch × the published price = **about $70 a day, or
  $2,100 a month**, before reading any promoter's history.

**What we did.** Descoped, with the reason (`SCOPE.md`; `DECISIONS.md`
2026-10-19 and Phase 7). The KOL page was removed. The social signal is
not replaced.

> **[Ours to write]** What the descope costs the contribution.

---

## 5. Free-tier limits the spikes proved wrong

**Expected.** The proposal's risk table planned for "free indexer tiers"
(slide 8).

**Found** (`backend/spikes/FINDINGS.md` §2 and §8, measured 2026-10-11 to
10-13):

| Documented or assumed | Measured |
|---|---|
| Blockscout's public API is a free fallback | HTTP 403 (Cloudflare challenge) on every call |
| Envio HyperSync is keyless | HTTP 401; a token is required |
| Alchemy's free tier as the main path | No key could be created; the public demo key returns 429 on Base |
| Free RPC getLogs ranges | 10 to 1,000 blocks; only Tenderly serves 1,000 (re-measured 21 Nov: drpc 100, blastapi 10, mainnet.base.org refuses) |
| DexScreener discovers new Base launches | Its feeds carried zero Base tokens; on-chain factory scanning was required |
| GeckoTerminal ~30 requests/min | 429s after a handful of calls |
| Base yields 1–3 tradeable launches a day (our own first report) | About 128 a day once Uniswap V4 is included |
| Base ≈ 2 s per block | True when measured. **False from 5 Nov 2026:** Base moved to 0.2 s blocks (item 7) |

**What we did.** A keyless multi-endpoint RPC pool with batching
(verified exact on 72 of 72 points), a call budget, and factory scanning
of V3 and V4.

---

## 6. The model's probabilities are not calibrated forward

**Expected.** "Calibration: does 70 percent mean 70 percent" (slide 8). A
calibrated risk score.

**Found.**
- On launches it had never seen, the frozen model's scores average
  **0.096 against an observed 0.047**.
- Its Brier score, **0.043**, is no better than always predicting the base
  rate (0.044).
- Scores in the 0.7–0.8 band came true 49% of the time.
- On the research cohort, Platt scaling does not improve Brier (0.129 vs
  0.127).

**How we know.** Figure 5; `reports/forward_validation.md`;
`results/manifest.json` → `calibration`.

**What we did.**
- The product shows the forward band's observed rate ("about 49 in 100"),
  never the raw score as a probability.
- A recalibrated score (Phase 11, shadow score A) was pre-registered on
  3 Nov. On 25 Nov it **passed its criterion**, but its pass comes from one
  scam family that raised the loss rate from 2.4% to 22.9%.
  - A predicts 2.7% on average against 22.9% observed.
  - Without the family, A's average matches the observed 2.1%, but its
    interval against a constant crosses zero.
  - Source: `phase11_shadow.md`.

---

## 7. Base changed its block time, and 11 days of the live record were invalid

**Expected.** That 2-second blocks were a constant: measured exactly in
the spikes, and used as one throughout.

**Found.**
- At block **53,556,128 (5 Nov 2026, 18:00:01 UTC)** Base moved to
  **0.2-second blocks**.
- Every live duration was a block count. Until the fix on 16 Nov:
  - predictions were made at **30 seconds**, not 5 minutes;
  - outcomes were measured at **36 minutes**, not 6 hours;
  - 14,655 launch times were stamped up to 139 hours wrong.

**How we know.** Real block timestamps (the clock now agrees to within
0.4 s from block 40M to the head); `DECISIONS.md` 2026-11-16.

**What we did.**
- The exclusion rule was committed **before** the fix and before any
  post-fix data was looked at. 14,503 predictions are excluded, and the
  3 Nov result is unaffected.
- Durations are now converted through one clock that knows both regimes.
- The scorer **halts** if that clock drifts more than 30 s from the chain.
- A follow-on cost: a 6-hour outcome now takes about 216 log requests, so
  resolution was moved to its own thread on 21 Nov.

---

## 8. The wallet "funding" graph is token provenance, not ETH funding

**Expected.** Funding edges as "who paid for this wallet" (the brief's
ETH-funding trace).

**Found.**
- No keyless source can find a wallet's first native-ETH funding. Funding
  edges are therefore **the first time a wallet received a token from a
  non-pool address** (`graph/funding.py`).
- The largest clusters are dispersers: one address seeding 5,402 wallets.
- The strongest "coordinated" case in the store is **bundling**, not
  independent wallets. One contract seeds 81 wallets; then two single
  swap transactions buy and spread tokens to all 81 (Figure 10).
- A search for funded wallets buying the same token independently within
  90 seconds **found none**.

**What we did.**
- It is stated in the module docstring, in Figure 9's and Figure 10's
  captions, and in the promise audit.
- Bundling became its own pre-registered detector (21 Nov,
  `graph/bundles.py`). Its first run flagged 111 of 983 launches, but two
  launchpad fee collectors appeared in 65 and 54 of them. A deviation,
  recorded before any label, excludes addresses seen in 10 or more
  launches: **34 of 983 (3.5%)** remain. Precision and recall wait on the
  team's blind labels (`reports/bundle_labelling.csv`).

---

## 9. A headline number that could not be reproduced

**Found.**
- The model card's out-of-time PR-AUC, **0.758**, came from a run that was
  never committed.
- The committed figure script gives **0.796** on the same 57 tokens and 20
  losses, against 0.331 for the early-concentration checker.

**What we did.** `scripts/make_figures.py` now regenerates every reported
number into `results/manifest.json`. The report should quote 0.796 and
note the discrepancy.

---

## 10. Smaller findings the report should not bury

- **The paper agent's edge is the launch-type filter, not the risk
  score.** Agent − launchpad-only: interval −31% to +36%. Its positive mean
  rests on 16 capped trades; the median trade is −3%.
  (`paper_agent.md`)
- **The buyer-loss label ignores liquidity pulls.** It counts a price
  fall, not a pull: of 3,557 pools pulled by hour 6, 6 were labelled
  losses. On the not-pulled population the model works (PR-AUC 0.152 vs
  0.039). With pulls counted as losses, launch type alone ranks better
  (0.837 vs 0.671). (`forward_validation.md`)
- **Part of the forward PR-AUC rise (0.108 → 0.283) is the model
  recognising one scam template.** For tokens on that template, the
  minute-5 "price run-up" measures its seeding swap. (`DECISIONS.md`
  2026-11-16)
- **The label is robust near its chosen thresholds but not everywhere.**
  - One step either side moves at most 42 tokens.
  - A dead-day cutoff of 0 moves 648.
  - Observation windows under 60 days move about 300.

  (Figure 2)
- **Decay is hard to read.** April has 1 loss in 14 test tokens; June and
  July have none. (Figure 6)
- **Attribution.** Every research commit is under one account
  (AbdullahBinNasir16). The FYP report's Ch. 9 says Abbas's work was
  non-code, while the proposal deck assigned him data and the risk model.
  An examiner checking the commit history will see this.
