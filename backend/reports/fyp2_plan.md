# FYP 2 (January–May 2027): revised plan

This replaces the slide 9 Gantt, which assumed four engines would be built
in parallel. It is based on what is actually left
(`reports/promise_audit.md`), not on the original slide. It is a draft for
the team to decide on. Lane owners are the ones in the proposal; changes
are marked.

## What is left

**Slipped from FYP 1:**

| Item | Proposal promise | Present state |
|---|---|---|
| Insider / bundler detection | slide 6, wallet screening engine Detector v0 exists (21 Nov, pre-registered): 34 of 983 launches bundled (3.5%). Precision and recall wait on the blind hand labels |
| Calibration | slide 8, "does 70% mean 70%" | Fails forward. Shadow score A passed its Phase 11 criterion on 25 Nov, but only because of one scam family; without it, it matches the mean and does not beat a constant (`phase11_shadow.md`) |
| Fusion: one risk view with its confidence | slide 6 | Launch type and buyer loss are shown separately |
| Drawdown for the agent | slide 8 | Computed post hoc on a fixed-stake book (`paper_drawdown.md`); not for a sized book |
| Accessibility | slide 10 | Automated audit done and fixed (0 axe violations, gated in CI); manual and screen-reader audit not done |
| Dataset size | slide 8, 5,000 launches | 983 labelled alive, plus a 10,233-launch forward record on a different label |
| Decay study | slide 8 | Thin: few positives in later months |
| AI text layer | slide 6 | Not started. Decide: build it with a narrow scope, or descope it with a reason |
| Hosting | (FYP-1 scope M11) | Runs on one laptop; outage gaps in the forward record |

**New:** the portfolio agent as the main new module.
- What exists is a fixed-rule paper agent: buy launchpad launches with a
  score under 0.2, sell at hour 6.
- FYP 2's version would add position sizing, size-dependent slippage,
  drawdown and risk limits, more than one strategy, and a held-out
  evaluation.
- Post hoc, the current agent's edge comes from the launch-type filter.
  So the agent's research question is whether any risk-aware sizing beats
  the launchpad-only rule forward.

**What the graph result implies for Abdullah's lane.**
- The proposal's premise ("wallet grouping is the core problem") was
  contradicted: graph features add nothing to prediction (Figure 8).
- The clusters are real in a narrower sense: co-movement lift (Figure 9)
  and visible bundling (Figure 10).
- The defensible pivot is from **prediction to detection**: a
  bundle/sybil detector whose output is a measured finding about launches
  ("X% of launches have a bundled first buy"), validated against labelled
  examples.
- This also fills the empty identity fields in the live screener (funding
  source, cluster), which are disabled today.

**Evaluation that needs the dataset to keep growing:**
- Model v2 on the forward record with a pull-aware label: first a
  separately pre-registered record, then a forward test.
- The decay study by month, once each month has enough positives.
- The Phase 11 result is in (25 Nov: both criteria pass; post hoc, one
  scam family drives A's pass). A recalibrated model in
  production.

## Plan by month

| Month | A: Muhammad Abbas Raza (data and risk model) | B: Abdullah Bin Nasir (wallet graph, **pivot to detection**) | S: Shahmeer (**platform and agent**; was social and agent) |
|---|---|---|---|
| Jan | Phase 11 write-up; label v3 with pulls counted; dataset card from the forward record | Score detector v0 against the blind labels (`scripts/bundles.py score`); if precision is poor, a pre-registered v1 | Host the stack on a VM (M11); uptime on Model Health |
| Feb | Train model v2 on the forward record (pre-registered); recalibrate | Detector v1; precision and recall against the hand labels | Agent v2: sizing, slippage by size, drawdown, risk limits |
| Mar | v2 forward record runs; decay by month | Detector on the full store and live; populate screener identity fields | Agent v2 forward, pre-registered against launchpad-only |
| Apr | Fusion: one view (launch type, then model) with a stated confidence; ablations | Sybil validation: dispersers vs organic, held out | Accessibility audit and fixes; the AI text layer **or** its descope paper trail |
| May | Thesis results chapters | Thesis detection chapter | Thesis system and agent chapters; demo hardening |
| All three | Thesis, defence, and reviewing each other's PRs (approvals back on) | | |

## The honest capacity read

**It does not obviously fill three people for a semester, as listed.**

- **Lane A** is full. Model v2, recalibration and the forward record are
  each real work.
- **Lane B** is full only if the detector is done properly. That means
  hand-labelled ground truth and measured precision and recall. Without
  them it is a few weeks of code.
- **Lane S** is the risk.
  - Hosting is about a week.
  - Agent v2 is real but bounded: perhaps six to eight weeks done well.
  - Accessibility is about two weeks.
  - That leaves roughly a month uncommitted, unless the AI text layer is
    built.

**Ways to add scope deliberately, rather than scramble in April.** These
are options for the team, not recommendations:
1. **Build the AI text layer** with a narrow, testable scope. For example:
   extract stated tokenomics from a token's website and check them against
   on-chain supply and liquidity. That keeps "AI reads text, never scores"
   (slide 8).
2. **A user study:** do traders shown the forward band decide differently
   from those shown a raw score? This measures the product claim, not just
   the model.
3. **A second chain, as a transfer test of the frozen model,** not as a
   product feature. Solana's per-token volume breaks the free tiers first
   (`spikes/FINDINGS.md` §6), so the cost must be costed before choosing it.

**Risks to this plan:**
- The keyless log cap: resolution already runs at Tenderly's limit, about
  1,700 a day.
- A further chain change, such as another block-time change, is now
  guarded by the drift halt.
- Hand-labelling time for the detector.
