# Promise audit: what the proposal defence said, against what exists

**Source of the claims:** `BlockLens FYP Proposal Defence.pptx` (11
slides, 11 Sep 2026). The brief also names
`claude/proposal-defence-research-base.md`. **That file does not exist**:
not in the repository, and not anywhere on the development machine (searched
21 Nov 2026). The citations used here are therefore the ones on slide 4.

**Statuses:**
- **delivered:** what the slide said exists and is evidenced.
- **partially delivered:** something real exists, but less than, or
  different from, what was claimed.
- **descoped:** dropped, with a recorded reason.
- **contradicted by findings:** the work showed the claim to be wrong.
- **not started.**

**Evidence:** every row names where it can be checked. Numbers are those in
`results/manifest.json` (generated 2026-11-21) unless the row says
otherwise.

## Slide 1: the platform

| Claim | Status | Evidence | Where |
|---|---|---|---|
| "Four networks in scope" (Ethereum, Base, Solana, BNB) | descoped | Every measurement, source and model is Base only. The other chains are shown disabled in the UI, "not supported". | `SCOPE.md`; `docs/FYP1_SCOPE.md` §3.3 |
| The problem: no tool shows how often its own warnings were right | delivered | A pre-registered forward record: 10,233 valid resolved predictions, shown on Fresh Launches beside every score. | `reports/forward_validation.md`; `DECISIONS.md` Phase 8 |

## Slide 3: the gap BlockLens fills (the columns of the comparison table)

| Claim | Status | Evidence | Where |
|---|---|---|---|
| Contract checks | partially delivered | The honeypot flag comes from GoPlus, a third party, shown live. BlockLens does no contract analysis of its own. | `backend/blocklens/api/market.py` |
| Holder and supply | partially delivered | Holder count and top-10 share from GoPlus, live, with plausibility checks. Not computed from chain data by BlockLens. | `market.py`; `plausibility.py` |
| Wallet clustering | partially delivered | 134 provable funding clusters, with a co-movement lift of 3.6× (buys, p = 0.049) and 4.7× (buys or sells, p = 1.3e-5); a shuffled control collapses (0.26×). But: the edges are **token-acquisition provenance, not ETH funding** (no keyless source exists); counts are small (3 of 40 cluster pairs, buys only); and the largest clusters are dispersers. | Figure 9; `reports/cluster_validation.json`; `graph/funding.py` docstring |
| Insider / bundler detection | partially delivered | Rule-checker flags exist (`bundled_launch`, `dev_sniped`, same-block buyers), and bundling is visible in the data (Figure 10: one contract seeds 81 wallets, then two single transactions buy and spread tokens to all 81). There is **no insider or bundler detection module** and no measured detection rate. | Figure 10; `model/rulecheck.py` |
| KOL record | descoped | The X API charges per post read; there is no keyless substitute. | `SCOPE.md`; `DECISIONS.md` 2026-10-19 and Phase 7 |
| Learned model | delivered | `buyer-loss-v1` (gradient boosting, 23 features at launch + 5 minutes). | `data/models/buyer_loss_v1.json`; Figure 4 |
| Publishes its accuracy | delivered | The forward record and the model card are shown on screen beside the score. | Fresh Launches; `RiskPanel` |
| Trades its own signal | delivered | Paper agent, pre-registered (Phase 9): it beats buy-everything forward. Post hoc, the edge is the launch-type filter, not the risk score. | `reports/paper_agent.md` |

## Slide 4: what the cited research was taken to mean for the design

| Claim | Status | Evidence | Where |
|---|---|---|---|
| "Watch behaviour, not contract code" | delivered | All 23 features are on-chain behaviour in the first five minutes. | `model/token_features.py` |
| "A useful answer must come within the hour" | delivered | Scored once, at launch + 5 minutes. After the 0.2 s block switch, scoring ran a median of 149 minutes late until 21 Nov; resolution now has its own thread. | `DECISIONS.md` 2026-11-16 and 2026-11-21 |
| "Wallet grouping is the core problem" | contradicted by findings | At full power, graph features add nothing over entry timing. Boosting: timing only 0.828, both 0.833, with overlapping 95% intervals. | Figure 8; `DECISIONS.md` Phase 5 Part D, Phase 6 |
| "Never train on anything from after the event; hence our 24-hour input freeze" | contradicted by findings | The 24-hour window was **censored**: all 28 RUG tokens rugged inside it, so the features partly measured the outcome. The freeze became launch + 5 minutes with a survival requirement. | `reports/leakage_audit.md`; `reports/sampling_design.md` |
| "Inputs matter more than architecture" | delivered | The feature-group result (Figure 8) and the permutation importance (Figure 7) are about inputs; logistic and boosting are compared. | Figures 7 and 8 |
| "Study the neighbourhood, not the wallet" (two-hop features) | partially delivered | Two-hop graph features are built (95 in Phase 3; 7 graph features in the minute-5 set). They do not improve prediction. | `graph/features.py`; Figure 8 |

## Slide 6: the proposed solution

| Claim | Status | Evidence | Where |
|---|---|---|---|
| Sources: on-chain transfers, liquidity, holders | delivered | Keyless RPC ingestion of pools, transfers and swaps; 5 GB store. | `ingest/`; Figure 11 |
| Sources: market price, volume, pairs | delivered | GeckoTerminal and DexScreener, through the API. | `api/market.py` |
| Sources: GitHub activity | not started (for live tokens) | GitHub figures exist only as a 9 Sep 2026 snapshot in the three case studies, badged sample. | `src/data/projects/*` |
| Sources: social posts on X | descoped | The X API is paid. | `SCOPE.md` |
| Temporal feature store, frozen 24 h after launch | contradicted by findings | Replaced by a launch + 5 minute cutoff (censoring; see slide 4). | `reports/leakage_audit.md` |
| Engine: twelve-section project research report on one token | partially delivered | Twelve sections exist as UI, for three case studies only; all research sections are sample. Live tokens get a live section (market, contract flags, model view). | `ProjectIntelligence.tsx`; `UnresearchedToken.tsx` |
| Engine: wallet screening (group wallets, find insiders and bundlers) | partially delivered | The screener runs on 70,480 real wallets from 771 labelled launches, USD at each trade's day. Grouping exists (funding clusters), but its fields are placeholders in the live corpus; no insider finding. | `api/screener.py`; `SCOPE.md` |
| Engine: KOL scoring | descoped | | `SCOPE.md` |
| Engine: risk model | delivered | `buyer-loss-v1` and the launch-type signal. | Figure 4; `model_card_v2.md` |
| Engine: AI text layer (reads whitepapers and posts, never scores) | not started | No LLM component exists. | none |
| Fusion and calibration (one risk score, its confidence, and every piece of evidence) | partially delivered | There is **no fusion**: launch type and buyer-loss risk are shown separately. Every score shows its inputs (exact SHAP terms). Calibration was measured and **fails forward** (Brier 0.043 against 0.044 for the base rate; mean prediction 0.096 against 0.047 observed), so scores are presented as the forward band's observed rate. | Figure 5; `RiskPanel.tsx`; `DECISIONS.md` Phase 7 |
| Output: intelligence report per token | partially delivered | The live token page for any Base address (market, flags, model where in scope); full reports only for three sample case studies. | `UnresearchedToken.tsx` |
| Output: wallet screener (cross-project) | delivered | Real wallets, cross-token, USD. | `/app/wallets` |
| Output: KOL leaderboard | descoped | | |
| Output: portfolio agent (trades our own signal) | delivered (early; it was FYP 2 on slide 8) | A paper agent with fixed rules. 3,763 agent trades by 3 Nov; beats buy-everything (interval +57% to +73%). | `reports/paper_agent.md` |
| Contribution: a dataset of real launches labelled by outcome with no hindsight | partially delivered | 1,058 labelled tokens (rule v2), 983 of them alive at minute 5, with a sensitivity analysis (Figure 2). **Fewer than the 5,000 proposed** (slide 8). The live forward record adds 10,233 resolved launches, on a different label (6-hour buyer loss and pulls). | Figures 1-2; `dataset_card.md` |
| Contribution: a risk model that publishes its accuracy and must beat a rule checker | delivered | Beats the checkers in-period (0.833 vs 0.370), out of time (0.796 vs 0.331), and forward (checkers at the base rate). | Figures 4 and 6; `forward_validation.md` |
| Contribution: a KOL score from realised results | descoped | | |
| Contribution: an agent that puts our signal on the line and reports what it earned | delivered | Reports losses as well as wins; median trade −3%. | `paper_agent.md` |

## Slide 8: the evaluation plan and risks

| Claim | Status | Evidence | Where |
|---|---|---|---|
| Collect 5,000 launches | partially delivered | 15,087 pools discovered and screened; 1,058 labelled; 983 alive at minute 5. The case-control design was chosen to get power on rare outcomes from fewer labels (297k RPC calls for the Phase 5 set). | `reports/sampling_design.md`; `phase5_counts.md` |
| Label the outcome at 90 days | delivered | 90-day observation window, rule v2, swept in Figure 2. Windows under 60 days would flip about 300 labels. | Figure 2; `label/rules.py` |
| Freeze the first 24 hours | contradicted by findings | Launch + 5 minutes (censoring). | `leakage_audit.md` |
| Split: old trains, new tests | delivered | Split on 20 Apr 2026; no operator family on both sides; a 1 Mar out-of-time check; forward from 19 Oct. | Figure 3; `sampling_design.md` |
| Score: rank and calibrate | partially delivered | Ranking delivered. Calibration fails forward (Figure 5b). Platt on the research cohort does not improve Brier (0.129 vs 0.127). | Figure 5 |
| Report catch rate at a fixed alert budget | partially delivered | Precision at k (10/25/50) and recall on PR curves are reported. Recall at a fixed budget is not tabulated as such. | `model_card_phase6.md`; Figure 4 |
| Report precision of the strongest warnings | delivered | P@10 0.90, P@25 0.92 (boosting, research cohort). Forward precision at ≥ 0.5: 20%. | `model_card_phase6.md`; `forward_validation.md` |
| Report calibration ("does 70% mean 70%") | delivered as a measurement; the answer is no | Forward: scores in the 0.7-0.8 band came true 49% of the time; overall the scores run about twice the observed rate. | Figure 5b |
| Report decay: how fast the model ages | partially delivered | By test month and by forward week (Figure 6). Thin: April has 1 loss in 14 tokens; June and July have none. | Figure 6 |
| Beat a simple rule checker, then a basic model | delivered | Boosting > logistic > both checkers. | Figure 4 |
| Agent: paper trading only, against buying every launch | delivered | | `paper_agent.md` |
| Agent: return, win rate and drawdown reported | partially delivered | Mean and median return, hit rate and total are reported. **Drawdown is not.** | `resolver.paper_agent` |
| Agent: every trade logged with its trigger signal | delivered | The paper book lists every trade with its risk and launch type. | `/api/paper-agent/trades` |
| Risk mitigation: X cost → smaller sample, cache | descoped instead | | `SCOPE.md` |
| Risk mitigation: chain limits → one chain first, free indexer tiers | delivered (one chain); indexer not used | Blockscout returns 403; keyless RPC only, with a 1,000-block log cap. | `docs/FYP1_SCOPE.md` §4 |
| Risk mitigation: scam hard to define → several criteria tested against each other | delivered | Label rules swept (Figure 2); extraction vs buyer loss vs RUG compared (Phase 6). | Figure 2; `model_card_phase6.md` |
| Risk mitigation: class imbalance → rare-event metrics | delivered | PR-AUC, P@k, base rate beside every metric. | Figures 4-6 |
| Risk mitigation: scammers adapt → decay on later months | partially delivered | Measured (Figure 6), but the later months have too few positives to read. | Figure 6 |
| Risk mitigation: agent overfits → paper only, held-out period, fixed rules | delivered | Pre-registered rules, forward period. | `DECISIONS.md` Phase 9 |
| Risk mitigation: thin liquidity → position caps and slippage modelled | partially delivered | Round-trip costs of 1/3/10% and a +1,000% cap per trade. No position sizing or size-dependent slippage. | `paper_agent.md` |
| Risk mitigation: team capacity → agent in FYP 2, cut first | not applicable | The agent was built early; KOL was cut instead. | |
| "We succeed if we beat a rule checker on unseen tokens" | delivered | In-period 0.833 vs 0.370; out of time 0.796 vs 0.331; forward, the model's PR-AUC is above the base rate (interval +0.055 to +0.124 at the 3 Nov floor), and both checkers sit at the base rate. | Figures 4 and 6; `forward_validation.md` |
| "AI reads text, never scores or trades" | not applicable | No AI text component exists. | |

## Slide 9: work division (FYP 1 items, to December)

| Claim | Status | Evidence | Where |
|---|---|---|---|
| A, Muhammad Abbas Raza: ingestion pipeline | delivered (as a project) | `ingest/`. **Attribution:** every research commit is under the AbdullahBinNasir16 account, and report Ch. 9 says Abbas's work was "non-code, 0 commits". The deck assigns this lane to Abbas. This needs resolving before the viva. | git log; `report/chapters/chapter9_development_evidence.tex` |
| A: labelled dataset | partially delivered | 1,058 labelled vs 5,000. | Figure 1 |
| A: baseline model | delivered | Logistic and boosting, plus fixed checkers. | Figure 4 |
| B, Abdullah Bin Nasir: transaction graph | delivered | 17,599 nodes; funding and co-purchase edges. | `cluster_validation.json` |
| B: two-hop features | delivered | `graph/features.py` (Phase 3, 95 features). | `DECISIONS.md` Phase 3 |
| B: clustering prototype | delivered | Two layers: provable components and Louvain communities. | `graph/cluster.py` |
| S, Shahmeer: X ingestion | partially delivered, then descoped | `ingest/xapi.py` is built and tested on a fixture, locked at 0 posts; never run. | `xapi.py` |
| S: match calls to outcomes | descoped | | |
| S: KOL prototype | descoped | The sample KOL UI was removed in PR #3. | `SCOPE.md` |
| What Shahmeer actually delivered | (not in the plan) | CI/CD and containers; the Phase 10 backend (explanations, alerts, paper book, health, product state); the product rework; CI hardening and end-to-end tests; the FYP-1 LaTeX report; hosting blueprints. | PRs #1-#6 |
| "Contract agreed first, week 2" | delivered | `src/data/types.ts`, and since Phase 7 a generated, drift-checked contract. | `contract/`; `npm run contract` |

## Slide 10: ethics, legal, DEI

| Claim | Status | Evidence | Where |
|---|---|---|---|
| Scores always show their inputs | delivered | Exact per-feature SHAP terms beside every score. | `RiskPanel.tsx`; `live/explain.py` |
| Generated data is labelled as generated | delivered | Per-section Live / Sample / No data badges; tested with the API down. | `e2e/fallback.spec.ts` |
| The agent publishes its losses too | delivered | | `paper_agent.md` |
| Group wallets, never name people | delivered | No identity is attached to any address. | |
| Paper trading only; no custody, brokerage or advice | delivered | | |
| Public APIs used within their terms | delivered | Keyless tiers, rate-limited by the budget module. | `ingest/budget.py` |
| Named accounts can ask for a correction | not applicable | No named accounts are scored (KOL descoped). | |
| Works without perfect sight or a mouse | not started (unverified) | Some ARIA labels exist; no accessibility audit has been done. | none |
| Free tier from the first release | delivered | Everything runs keyless. | `RUNNING.md` |
| Each member reviews another member's code | partially delivered | PRs #1-#6 and #11 were reviewed. Required approvals on `develop` were turned off on 17 Nov at the team's request, so later PRs merged without a second reviewer. | GitHub PR history |
| Never publish a score that cannot be reproduced | partially delivered | The out-of-time PR-AUC 0.758 in the model card came from an uncommitted run; committed code gives 0.796 on the same 57 tokens. Since Phase 8 every reported number is regenerated by `scripts/make_figures.py` into `results/manifest.json`. | Figure 6; `results/manifest.json` |

## Slide 11: the stack

| Claim | Status | Evidence | Where |
|---|---|---|---|
| FastAPI, schema generated from the contract | delivered | | `backend/blocklens/api/contract.py` (generated) |
| scikit-learn baseline, then LightGBM | partially delivered | scikit-learn throughout; `HistGradientBoostingClassifier` (the same algorithm family) instead of LightGBM. | `scripts/phase5_model.py` |
| NetworkX, two-hop wallet features | delivered | | `graph/` |
| PostgreSQL with TimescaleDB | partially delivered | PostgreSQL 16. TimescaleDB is in the compose file, but the development store is a portable PostgreSQL without it (no admin rights for Docker locally). | `docker-compose.yml`; `DECISIONS.md` 2026-10-11 |
| Ingestion: Python, web3.py, Base indexer API | partially delivered | Python over raw JSON-RPC (httpx), not web3.py; no indexer API (Blockscout 403, Alchemy keyless impossible). | `ingest/sources.py` |

## Tally

| Status | Rows |
|---|---|
| delivered | 41 |
| partially delivered | 24 |
| descoped | 9 |
| contradicted by findings | 4 |
| not started | 3 |
| not applicable | 3 |
| context row (not a claim) | 1 |
| **total** | **85** |

Counted from the table rows above (a status cell beginning "partially delivered, then descoped" counts as partially delivered). A reading aid, not a metric: rows differ in weight.
