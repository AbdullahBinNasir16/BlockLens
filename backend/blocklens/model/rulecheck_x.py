"""Pre-registered for Phase 6, written before any Phase 6 model or full label
run existed (2026-10-19). Not to be edited after results are seen; a change
would be a new, separately reported baseline.

Targets, on non-RUG tokens alive at minute 5 (FAILED + SURVIVED):

* **T1 — EXTRACTED** (primary, the question asked): the early cohort took
  a profit of at least 25% of what later buyers put in, over the first six
  hours (`blocklens/label/extraction.py`).
* **T2 — BUYER_LOSS** (secondary, the product question): a buy at the
  minute-5 price is worth at most half as much at hour 6
  (`price_end_vs_cutoff <= 0.5`).

Baseline for both: the Phase 5 five-flag checker, unchanged, plus this
early-concentration checker, which is what a human looking at the first
five minutes of a launchpad token would check.
"""
from __future__ import annotations

FLAGS = {
    # one wallet bought most of what was bought by minute 5
    "one_wallet_dominates": lambda r: r["t_top_buyer_share"] > 0.5,
    # a bundle in the creation block or the next
    "bundled_launch": lambda r: r["t_same_block_buyers"] >= 3,
    # half of the first five minutes' buys landed in the first minute: sniped
    "sniped": lambda r: r["t_share_buys_first_minute"] >= 0.5,
    # the price already ran: up more than 5x from the first swap by minute 5
    "already_pumped": lambda r: r["t_log_price_drift"] >= 1.609,
    # early holders already selling hard by minute 5
    "early_selling": lambda r: r["t_sell_buy_ratio"] >= 0.5,
}
VERDICT_AT = 2
BUYER_LOSS_AT = 0.5


def score(row: dict) -> int:
    return sum(bool(f(row)) for f in FLAGS.values())
