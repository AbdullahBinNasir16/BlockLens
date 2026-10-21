# Paper agent: first reportable result (2026-10-21)

Protocol: DECISIONS.md, Phase 9. Pre-registered 2026-10-19, before any
outcome resolved. Numbers: `reports/paper_agent.json`, produced by
`python -m scripts.phase9_report`. Only timely predictions are included
(scored at or before launch + 6 hours). Launches run from 2026-10-19 07:32
to 2026-10-21 12:14 PKT, with a 38-hour outage in between. Launches missed
during the outage are excluded.

## 1. Pre-registered result: success

Headline cost is 3% per round trip; returns are capped at +1,000% per trade.

| Policy | Trades | Mean | Median | Hit rate |
|---|---:|---:|---:|---:|
| AGENT (launchpad and risk < 0.2) | 315 | +49.3% | −3.0% | 7.0% |
| CONTROL (every scored launch) | 832 | −33.4% | −100% | 3.4% |
| AVOIDED (what AGENT refused) | 517 | −83.8% | −100% | 1.2% |

The 95% interval for AGENT minus CONTROL is **+55% to +110%**, which is
above zero. The floor of 100 agent trades has been passed. By the
pre-registered test, this is a **success**. The result holds at 1% and 10%
cost.

## 2. What it rests on (post hoc, added after seeing section 1)

**The edge is the launch-type filter, not the risk score.** LAUNCHPAD buys
every launchpad launch and uses no model. It does almost exactly as well as
AGENT:

| Cap per trade | AGENT mean | LAUNCHPAD mean | AGENT − LAUNCHPAD, 95% CI | AGENT − CONTROL, 95% CI |
|---|---:|---:|---|---|
| +1,000% (pre-reg.) | +49.3% | +47.0% | −31% to +36% | +58% to +111% |
| +500% | +23.4% | +21.4% | −16% to +20% | +53% to +83% |
| +200% | +6.0% | +4.2% | −6% to +10% | +50% to +64% |
| +100% | −0.1% | −1.8% | −3% to +7% | +48% to +58% |
| capped trades dropped | −1.6% | −3.6% | −6% to +10% | +47% to +61% |

* The model turned down only 22 of the 337 launchpad launches, so AGENT and
  LAUNCHPAD are nearly the same set of trades. Those 22 did worse: −21%
  mean at the +200% cap. That points the right way, but 22 trades decide
  nothing.
* Self-deployed launches lost −88% on average (495 trades, median −100%).
  86% of them had their liquidity pulled within a day, against 0.4% of
  launchpad launches. This repeats the Phase 5 launch-type finding, now
  forward and out of sample.
* **The positive mean comes from a few trades.** The median AGENT trade is
  −3%, which is just the cost. 16 trades hit the cap, and without them the
  mean is −1.6%. AGENT avoids losses; it does not pick winners.
* **The cap result is robust.** Beating CONTROL holds at every cap and with
  the capped trades dropped, because CONTROL's losses are rug losses, not
  missed spikes.

## 3. Buyer-loss model, forward (not yet reportable)

831 timely predictions have resolved and 14 were losses. The floor is 200
resolved **and 20 losses**, so no conclusion is drawn yet. For the record
only:

* PR-AUC is 0.146 against a base rate of 0.017.
* ROC-AUC is 0.676.
* At the 0.5 threshold, 11 tokens were flagged and 2 of them were losses.

## Plain statement

The pre-registered agent beats buy-everything forward, by a wide and robust
margin. In the data so far, all of that margin can be explained by one rule
an analyst could write without a model: *only buy launchpad launches (where
liquidity is locked)*. The risk score has not yet been shown to add to that
rule.
