# Paper agent: drawdown (post hoc, 2026-11-21)

**Status:** post hoc. The Phase 9 pre-registration fixed only mean return
against CONTROL; drawdown was promised on slide 8 but never pre-registered.
Numbers: `reports/paper_drawdown.json`, from `python -m scripts.drawdown`.

**Book.** One stake on every trade the policy takes, opened at minute 5 and
closed at hour 6, 3% round-trip cost; P&L counts when a trade closes. Rows
are the Phase 9 rows: timely, resolved, and valid under the block-time rule.
Launches run from 19 Oct to 17 Nov 2026. Those from 5 Nov 18:00 UTC to the
16 Nov fix are excluded, and the curve joins across that gap. "Capital" is
the most positions open at once, i.e. the smallest bankroll that takes every
trade. "Order luck" replays the same returns in 2,000 random orders.

## At the pre-registered cap (+1,000% per trade)

| Policy | Trades | Total P&L (stakes) | Max drawdown (stakes) | Capital (stakes) | Drawdown / capital | Longest run below a peak (trades) | Order-luck drawdown, median / 95th pct |
|---|---:|---:|---:|---:|---:|---:|---|
| AGENT | 4,742 | +2,231 | 14.6 | 241 | 6.1% | 152 | 8.7 / 12.3 |
| LAUNCHPAD | 5,389 | +2,100 | 89.2 | 286 | 31.2% | 297 | 15.5 / 22.0 |
| CONTROL | 10,419 | −2,018 | 2,019 | 409 | 494% | 10,375 | 2,030 / 2,063 |

- AGENT's and LAUNCHPAD's largest drawdowns both fall on 17–18 Nov, the
  newest trades in the record, which is still resolving.
- AGENT's actual drawdown (14.6) is above the 95th percentile of its
  random orders (12.3): its losses were bunched in time.

## The same book at +200%, and with capped trades dropped

| Policy | +200% cap: total / max drawdown / share of capital | Capped dropped: total / max drawdown / share of capital |
|---|---|---|
| AGENT | +221 / 30.8 / 12.8% | −129 / 142.8 / 61.3% |
| LAUNCHPAD | −53 / 203.5 / 71.2% | −430 / 439.1 / 158% |
| CONTROL | −4,307 / 4,307 / 1,053% | −4,618 / 4,618 / 1,143% |

- With the 236 capped trades removed, AGENT loses money. It has been below
  its 22 Oct peak since then (4,104 trades).
- AGENT and LAUNCHPAD have similar totals at the pre-registered cap. AGENT's
  drawdowns are smaller in every variant.

## Limits

- The stake is fixed: there is no position sizing, no size-dependent
  slippage and no compounding (FYP-2 agent v2).
- Drawdown is a property of one path. It has no interval, and the order-luck
  replay is a check on that path, not a confidence interval.
- The 21 Oct report (`paper_agent.md`) is unchanged. These numbers use the
  record as of 21 Nov.

> **[Ours to write]** What the drawdown says about the agent, and whether
> AGENT's smaller drawdowns credit the risk score.
