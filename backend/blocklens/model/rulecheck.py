"""The rule checker: the baseline the proposal says the model must beat.

Five fixed flags in the style of public token checkers (RugCheck,
TokenSniffer), each computable at launch + 5 minutes from the token's own
window. **The thresholds were written down before any Phase 5 model was
fitted and are never tuned**: a baseline that is optimised on the data is
just another model.

The score is the number of flags raised, so it can be ranked for PR-AUC and
precision-at-k exactly like a model's probability; the checker's own
verdict is "RUG" at two flags or more.
"""
from __future__ import annotations

FLAGS = {
    # sells impossible or absent: buys happened, nobody could or did sell
    "honeypot_like": lambda r: r["t_buys"] >= 3 and r["t_sells"] == 0,
    # one wallet took most of what was bought
    "concentrated": lambda r: r["t_top_buyer_share"] > 0.5,
    # almost nobody is trading it
    "thin": lambda r: r["t_unique_buyers"] < 5,
    # the deployer or liquidity provider bought its own launch
    "dev_sniped": lambda r: r["r_deployer_bought"] >= 1,
    # three or more wallets bought in the creation block or the next: a bundle
    "bundled": lambda r: r["t_same_block_buyers"] >= 3,
}
VERDICT_AT = 2


def flags(row: dict) -> dict[str, bool]:
    return {k: bool(f(row)) for k, f in FLAGS.items()}


def score(row: dict) -> int:
    return sum(flags(row).values())


def verdict(row: dict) -> bool:
    return score(row) >= VERDICT_AT
