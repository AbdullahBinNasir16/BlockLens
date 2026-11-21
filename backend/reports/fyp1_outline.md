# FYP-1 report: annotated outline

**Values:** every number here is the value in `results/manifest.json`
(generated 2026-11-21 from git `62f565a`; rerun
`python -m scripts.make_figures` to refresh it). The "forward" numbers come
from the live record, which keeps growing: quote them with their date.

**Who writes:**
- **US** means the team writes it. It argues, frames, or concludes.
- **TOOL** means it is factual, assembled from evidence (tables, figure
  captions, procedures). The team still owns it and must check it.

**The existing draft:** `report/` already holds a LaTeX draft in the FAST
template, mostly drafted by Shahmeer, with tooling edits through PR #10.
This outline maps onto its chapters. Where a chapter exists, the column
says what to check it against.

**Gaps:** ⚠ marks a claim with no evidence behind it yet. Those are the
remaining work.

**Citations:** only the papers on the proposal deck's slide 4 are on hand.
The research-base document the brief names does not exist. Full
references are in `report/references/references.bib`; check each against
it.

| Short name | Paper |
|---|---|
| Solana rugs | arXiv 2603.24625 (2026) |
| Spammers and snipers | arXiv 2206.08202 |
| TM-RugPull | arXiv 2602.21529 (2026) |
| TON early warning | arXiv 2509.01168 (2025) |
| Sybil two-hop | arXiv 2505.09313 (2025) |
| Market context | Chainalysis 2025; CoinGecko Research, Apr 2026 (slide 2) |

---

## Front matter

| Section | Writer | Contents and numbers | Must establish | Gaps |
|---|---|---|---|---|
| Title, submission and declaration pages | US | Names and roll numbers. ⚠ The deck has **Abbas 23i-0733, Abdullah 23i-0803**; the report's title page has **Abbas i230803, Abdullah i230733**. One of them is wrong. | Correct identities | ⚠ Roll numbers |
| Abstract (`04_abstract.tex`) | US | Forward result on 8,259 launches (PR-AUC 0.108 vs 0.023 at the 3 Nov floor); calibration fails; paper agent beats buy-everything | The contribution, in 200 words | Refresh to the final numbers |
| Executive summary (`06`) | US | Same numbers, plus the block-time incident | | |

## Chapter 1: Introduction and project vision

| Section | Writer | Numbers, tables and figures | Citations | Must establish |
|---|---|---|---|---|
| Problem | US | 1.7% of 2.06M tokens survived 30 days; 26.7% of pump.fun wallets lost money | Chainalysis 2025; CoinGecko 2026 | Why a launch-time signal with a published record matters |
| Objectives and their status | US (TOOL table) | The promise-audit tally: 41 delivered, 24 partially delivered, 9 descoped, 4 contradicted by findings, 3 not started (of 85 rows) | | What was promised and what stands |
| Scope, and what is out of it (KOL descope paragraph, done Phase 7) | TOOL (done) | X at ~$0.005 a post (published, not measured); ~$70/day estimate; Base only | | That the descopes have stated reasons |

## Chapter 2: Research and existing solutions

| Section | Writer | Numbers | Citations | Must establish | Gaps |
|---|---|---|---|---|---|
| Existing tools | US | The slide 3 comparison table | | The gap | |
| Literature | US | Solana rugs: 100,063 tokens, 76% rugs. TON: AUC 0.891 from 5 minutes. Sybil: F1 0.930. TM-RugPull: inputs from the first half of a project's life | all five on slide 4 | What was borrowed, and where our findings diverge (graph null; censoring) | ⚠ No literature beyond the five slide-4 papers. A related-work section usually needs more |

## Chapter 3: Proposal feedback and iteration plan

| Section | Writer | Contents | Must establish | Gaps |
|---|---|---|---|---|
| Feedback received at the defence | US | | What the committee asked for | ⚠ The feedback is not recorded anywhere in the repository |
| Iterations | TOOL | Phase timeline from `DECISIONS.md` (Phases 1–11 with dates) | How the plan changed and why | |

## Chapter 4: Software requirements

| Section | Writer | Contents | Must establish |
|---|---|---|---|
| Functional and non-functional requirements; use cases | TOOL (exists) | Check FR-4.3 ("too early below the floor"): it is now superseded, because the floor has passed | Requirements match what was built |

## Chapter 5: System design

| Section | Writer | Numbers and figures | Must establish |
|---|---|---|---|
| Architecture | TOOL | **Figure 11** (pipeline); the API routes; the generated contract | How the parts fit |
| Data and labels | TOOL | Rule v2 (RUG / FAILED / SURVIVED / NEVER_LAUNCHED); a 90-day window; **Figure 2** (one step either side moves ≤ 42 of 1,058; dead-day 0 moves 648; windows under 60 days move ~300) | The label is defined and tested |
| Sampling design | TOOL | Case-control strata + random cohort; split 20 Apr 2026; families one side only; 983 alive labelled; **Figure 1** (RUG rate: training 29.0%, random before split 7.9%, after 45.0%) and **Figure 3** | The design answers the censoring and leakage problems |
| Time on chain | TOOL | Two-regime clock (2 s; 0.2 s from block 53,556,128); drift halt | That durations are times |

## Chapter 6: Iteration 1, design and implementation

| Section | Writer | Contents | Gaps |
|---|---|---|---|
| What was built | TOOL (exists) | Screens, API, scorer, resolver, paper agent | Refresh for Phase 7 (live/sample badges, real screener) and Phase 8 |
| Who built what | US | | ⚠ Attribution: every research commit is under one account, and Ch. 9 says Abbas did no code. Resolve before the viva |

## Chapter 7 (new, suggested): Results

| Section | Writer | Numbers and figures | Must establish |
|---|---|---|---|
| Launch type (RUG) | TOOL | Self-deployed pulled 109 of 113 vs launchpad 0 of 74 (held out). Forward at 7 days: 85.4% of 3,249 vs 0.83% of 3,236 | The strongest signal is one line |
| Buyer-loss model vs baselines | TOOL | **Figure 4**, research cohort, n = 179 with 64 losses (base 0.358). PR-AUC with 95% family interval: boosting 0.833 [0.725–0.913]; logistic 0.643 [0.520–0.761]; early-concentration checker 0.370; Phase 5 checker 0.365 | It beats a rule checker on unseen tokens (the slide 8 success criterion) |
| Out of time | TOOL | **Figure 6a**: trained before 1 Mar; on 1 Mar–17 Apr (57 tokens, 20 losses) PR-AUC **0.796** vs checker 0.331. The model card's 0.758 is not reproducible from committed code | Generalisation over time |
| Feature importance | TOOL | **Figure 7**: the top features are price run-up by minute 5 (0.335), liquidity vs peak (0.117), swaps (0.102), time to first buy (0.073) | What the model uses |
| Graph features | TOOL figure, US interpretation | **Figure 8**: boosting timing 0.828 [0.731–0.904], graph 0.543 [0.411–0.682], both 0.833 [0.725–0.913] | The null result |
| Clusters are real | TOOL figure, US interpretation | **Figure 9**: lift 3.6× (buys, 3/40 pairs, p = 0.049) and 4.7× (buys or sells, 12/155, p = 1.3e-5); shuffled control 0.26×. **Figure 10**: the bundle case (81 wallets, 2 transactions each) | Grouping finds structure, even though it does not predict |
| Calibration | TOOL | **Figure 5**: research cohort Brier 0.127 raw, 0.129 Platt, base 0.230. Forward: Brier 0.043 vs 0.044; mean prediction 0.096 vs observed 0.047 | The probabilities are not calibrated forward |
| Forward validation | TOOL | Pre-registered at the 3 Nov floor: 8,259 resolved, 191 losses, PR-AUC 0.108 vs 0.023 (interval +0.055 to +0.124); 7-day pulls 89.2% vs 0.63%. **Now** (valid, 21 Nov): 10,233 resolved, 476 losses, PR-AUC 0.319; 14,503 excluded by the block-time rule. **Figure 6b** | That predictions made before their outcomes held up |
| Paper agent | TOOL | 3,763 trades; beats buy-everything (+57% to +73%); not distinguishable from launchpad-only; median trade −3% | "Trades our own signal", and what it shows |

## Chapter 8: Testing and early validation

| Section | Writer | Numbers | Gaps |
|---|---|---|---|
| Automated tests | TOOL | Backend 185, frontend 40, Playwright 13; CI with a clean-machine compose job | |
| The results that were not what we hoped | TOOL facts (done: `reports/honest_results.md`), US framing | Items 1–10 | |
| Reproducibility | TOOL | `REPRODUCE.md`; manifest; seeds in `config.Seeds` | ⚠ Reproduction from the raw chain was not re-run end to end (days of RPC); only from the store snapshot |

## Chapter 9: Project management and development evidence

| Section | Writer | Contents | Gaps |
|---|---|---|---|
| Contribution table | US | Git history; PRs #1–#16 | ⚠ The attribution conflict above |
| Risks | TOOL (updated) | Block time, outages, X cost | |

## Chapter 10: Remaining FYP plan

| Section | Writer | Contents |
|---|---|---|
| FYP-2 plan | TOOL draft (`reports/fyp2_plan.md`), US decision | See that file. ⚠ The current workload does not obviously fill three people (stated there) |

## Conclusion

| Writer | Must establish |
|---|---|
| US | What FYP 1 shows, and what it does not |

## Appendices

| Appendix | Writer | Contents | Gaps |
|---|---|---|---|
| Figures and captions | TOOL | `report/figures/generated/captions.tex` (all 11) | |
| Promise audit | TOOL | `reports/promise_audit.md` | |
| Meeting records | US | | ⚠ Supervisor meeting minutes are not in the repository |
| Screenshots (current `report/figures/*.png`) | | | ⚠ Screenshots of the UI predate Phase 7 (badges, real screener). Retake them, or drop them: the brief asks for generated figures, not screenshots |

## Evidence gaps (the remaining work)

1. **Roll numbers** disagree between the deck and the report.
2. **Attribution:** research code under one account vs the Ch. 9
   statement.
3. **Literature beyond the five slide-4 papers.**
4. **Defence feedback**, and **meeting minutes**, are not recorded.
5. **Reproduction from raw chain data** was not re-run end to end.
6. **No accessibility audit** (slide 10 promise).
7. **Drawdown** for the paper agent (slide 8 promise) is not computed.
8. **Insider detection** has no measured result (slide 6 engine).
9. **The UI screenshots** are out of date.
