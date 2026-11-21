"""Drawdown of the paper agent's book (post hoc; not part of the Phase 9
pre-registration, which fixed only mean return against CONTROL).

    python -m scripts.drawdown        # -> reports/paper_drawdown.json

Slide 8 promised drawdown for the agent. The book here is the simplest one
the Phase 9 rules imply: **one unit staked on every trade**, opened at the
launch's minute 5 and closed at hour 6, P&L realised at close. On that book:

* max drawdown: the largest fall of cumulative realised P&L from a running
  peak, in stakes, with its peak and trough times and the longest run of
  trades closed below a previous peak (in trades: a clock in hours would
  count the 5-16 Nov exclusion gap);
* capital needed: the most positions open at once, in stakes. Drawdown as
  a share of that is the drawdown of a bankroll just large enough to take
  every trade;
* order luck: the same trades in 2,000 random orders. The 95th percentile
  max drawdown says how much worse the path could have been with the same
  returns.

Rows are the Phase 9 rows (timely, resolved, valid under the block-time
exclusion rule). Returns use the headline 3% cost, at the pre-registered
+1,000% cap, at +200%, and with capped trades dropped.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

from blocklens.config import SEEDS
from blocklens.store.db import session_factory
from scripts.phase9_report import POLICIES, ret, rows

OUT = Path(__file__).resolve().parents[1] / "reports" / "paper_drawdown.json"
OPEN, CLOSE = timedelta(minutes=5), timedelta(hours=6)
SHUFFLES = 2000
SHOWN = ("AGENT", "LAUNCHPAD", "CONTROL")


def max_drawdown(pnl: np.ndarray) -> tuple[float, int, int]:
    """Largest peak-to-trough fall of the cumulative sum, and its indices."""
    eq = np.concatenate([[0.0], np.cumsum(pnl)])
    peak_at = np.maximum.accumulate(np.arange(len(eq)) * (eq == np.maximum.accumulate(eq)))
    dd = np.maximum.accumulate(eq) - eq
    j = int(dd.argmax())
    return float(dd[j]), int(peak_at[j]), j


def max_concurrent(trades: list[tuple[datetime, datetime]]) -> int:
    ev = sorted([(o, 1) for o, _ in trades] + [(c, -1) for _, c in trades], key=lambda e: (e[0], e[1]))
    cur = best = 0
    for _, d in ev:
        cur += d
        best = max(best, cur)
    return best


def book(ts: list[dict], pick, cap: float | None, drop_capped: bool, rng) -> dict:
    tr = [(t["ts"] + OPEN, t["ts"] + CLOSE, r) for t in ts if pick(t)
          for r in [ret(t, cap)] if r is not None and not (drop_capped and r >= 10.0)]
    if not tr:
        return {"trades": 0}
    tr.sort(key=lambda x: x[1])
    pnl = np.array([r for *_, r in tr])
    closes = [c for _, c, _ in tr]
    dd, i, j = max_drawdown(pnl)
    eq = np.concatenate([[0.0], np.cumsum(pnl)])
    # longest run of trades closed below a previous peak. Counted in trades,
    # not hours: the clock would include the 5-16 Nov block-time exclusion gap.
    run_peak, run, longest = 0.0, 0, 0
    for v in eq[1:]:
        run = run + 1 if v < run_peak else 0
        run_peak = max(run_peak, v)
        longest = max(longest, run)
    cap_needed = max_concurrent([(o, c) for o, c, _ in tr])
    shuffled = [max_drawdown(rng.permutation(pnl))[0] for _ in range(SHUFFLES)]
    when = lambda k: closes[k - 1].isoformat() if k > 0 else "start"
    return {"trades": len(tr), "total_pnl_stakes": round(float(pnl.sum()), 2),
            "max_drawdown_stakes": round(dd, 2), "peak_at": when(i), "trough_at": when(j),
            "longest_under_water_trades": longest,
            "capital_needed_stakes": cap_needed,
            "max_drawdown_share_of_capital": round(dd / cap_needed, 3) if cap_needed else None,
            "order_luck_drawdown_p50_p95": [round(float(np.percentile(shuffled, q)), 2) for q in (50, 95)]}


def main() -> None:
    with session_factory()() as s:
        ts = rows(s)
    rng = np.random.default_rng(SEEDS.paper_report)
    variants = {"cap_10_preregistered": (10.0, False), "cap_2": (2.0, False), "capped_dropped": (10.0, True)}
    doc = {"generated_at": datetime.now(timezone.utc).isoformat(), "post_hoc": True,
           "book": "one stake per trade, minute 5 to hour 6, 3% round-trip cost",
           "launches": [min(t["ts"] for t in ts).isoformat(), max(t["ts"] for t in ts).isoformat()],
           "rows": len(ts),
           "gap": "launches from 5 Nov 18:00 UTC to the 16 Nov fix are excluded (block-time rule); the curve joins across them",
           "results": {v: {p: book(ts, POLICIES[p], cap, drop, rng) for p in SHOWN}
                       for v, (cap, drop) in variants.items()}}
    OUT.write_text(json.dumps(doc, indent=1), encoding="utf8")
    print(json.dumps(doc, indent=1))


if __name__ == "__main__":
    main()
