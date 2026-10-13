"""Find the features that restate the label instead of predicting it.

This runs before training, not after, because the kind of leakage at risk
here is **definitional** and no amount of cross-validation will reveal it.
A feature that is partly a restatement of the labelling rule will score well
in every fold, look like a discovery, and mean nothing.

The specific hazard in this project, found by measurement rather than
suspicion: RUG tokens average **89.5 wallets** and FAILED tokens **24.8**.
That is not a market fact the model gets to use. Phase 2's `DEAD` criterion
is *defined* on whether the price moved, and a token whose price never moved
is a token almost nobody traded, which is a token with few wallets. So any
feature counting activity — wallets, buys, sells, tokens traded — is
downstream of the thing that decided the label.

Two kinds of suspect, kept separate because they need different treatment:

* **definitional** — the feature and the label are computed from
  overlapping evidence. Judged by reading both definitions, not by
  correlation, because a definitional leak can have modest correlation and
  still be circular.
* **empirical** — the feature separates the classes far better than anything
  else, which is a reason to look at it rather than a verdict.

The module reports both and provides the exclusion set. `train.py` fits with
and without it, and both results are published: dropping features always
lowers a score, and quietly reporting only the lower one is as misleading as
quietly reporting only the higher.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

# Features whose evidence overlaps Phase 2's labelling rule.
#
# `DEAD` (and so `FAILED`) is decided by price-movement days, and
# `NEVER_LAUNCHED` by swap count. Anything that counts a wallet's trades, or
# aggregates its neighbours' trade counts, is measuring the same activity
# the label was derived from.
# The list below grew once the audit ran, and the reason is the heart of
# Phase 4's finding. `base_buy_quote` scored AUC 0.922 - apparently the best
# predictor in the set. It is zero whenever no priced swap exists for a
# wallet, and "almost no swaps" is precisely what sends a token to FAILED
# via the DEAD criterion. The same holds for every money, holding-time and
# behavioural-flag feature: each one requires trades to be non-trivial, so
# each one is partly a restatement of which class the token is in.
DEFINITIONAL_PREFIXES = (
    # counts of activity
    "base_buy_count", "base_sell_count", "base_tokens_traded",
    "base_tokens_received",
    # money, which is zero without priced swaps
    "base_buy_quote", "base_sell_quote", "base_realised_quote",
    # exit behaviour, undefined without a sell
    "base_hold_time", "base_sold_fraction", "base_sold_first_pump",
    "base_averaged_down", "base_went_to_zero",
)
# The propagated forms of the same quantities. A neighbourhood mean of buy
# counts is no less circular than a buy count.
DEFINITIONAL_SUFFIXES = (
    "_buy_count", "_sell_count", "_tokens_traded",
    "_buy_quote", "_sell_quote", "_realised_quote",
    "_hold_time_mean", "_hold_time_max", "_sold_fraction",
    "_sold_first_pump", "_averaged_down", "_went_to_zero",
)
# Neighbour *counts* are the subtlest case and the one the 89.5-vs-24.8 gap
# points at directly: how many wallets a token had is close to how much it
# traded, which is close to how it was labelled.
COUNT_FEATURES = ("h1_count", "h2_count", "h1_with_behaviour",
                  "h2_with_behaviour")


@dataclass
class Finding:
    feature: str
    kind: str                 # "definitional" | "empirical"
    reason: str
    separation: float = 0.0   # standardised mean difference between classes
    auc: float = 0.5          # single-feature ranking power


# What survives, and why it is defensible. Graph structure comes from
# funding edges rather than from trading, so it is not downstream of the
# DEAD criterion at all. Entry delay requires a buy to exist, but given one,
# it measures *when* rather than *how much* - it is conditional on being a
# trader, which the label is not.
LEGITIMATE_PREFIXES = (
    "base_in_degree", "base_out_degree", "base_cluster_size",
    "base_community_size", "base_hops_from_cex", "base_entry_delay",
)


def definitional(names: list[str]) -> list[str]:
    """Features excluded by reading the definitions, not the data."""
    out = set()
    for n in names:
        if n.startswith(DEFINITIONAL_PREFIXES):
            out.add(n)
        elif any(n.endswith(s) for s in DEFINITIONAL_SUFFIXES):
            out.add(n)
        elif n in COUNT_FEATURES:
            out.add(n)
    return sorted(out)


def _auc(x: np.ndarray, y: np.ndarray) -> float:
    """Rank AUC of one feature, by the Mann-Whitney identity.

    Written out rather than imported so that the number in the report comes
    from an expression a reader can check against the definition.
    """
    pos, neg = x[y == 1], x[y == 0]
    if pos.size == 0 or neg.size == 0:
        return 0.5
    order = np.argsort(x, kind="mergesort")
    ranks = np.empty_like(order, dtype=float)
    ranks[order] = np.arange(1, x.size + 1)
    # average ranks over ties, so a constant feature scores 0.5 exactly
    _, inverse, counts = np.unique(x, return_inverse=True, return_counts=True)
    sums = np.zeros(counts.size)
    np.add.at(sums, inverse, ranks)
    ranks = (sums / counts)[inverse]
    r_pos = ranks[y == 1].sum()
    n1, n0 = pos.size, neg.size
    return float((r_pos - n1 * (n1 + 1) / 2) / (n1 * n0))


def audit(X: np.ndarray, y: np.ndarray, names: list[str], *,
          top: int = 12) -> tuple[list[Finding], list[str]]:
    """Both kinds of suspect, and the set to exclude.

    Returns (findings, exclusion set). The exclusion set is the definitional
    group only: an empirically strong feature is a lead to investigate, and
    dropping features for being predictive would be its own kind of
    dishonesty.
    """
    excluded = definitional(names)
    findings: list[Finding] = []

    for n in excluded:
        i = names.index(n)
        findings.append(Finding(
            feature=n, kind="definitional",
            reason="counts trading activity, which is the evidence Phase 2's "
                   "DEAD criterion is computed from",
            separation=_std_diff(X[:, i], y), auc=_auc(X[:, i], y)))

    scored = []
    for i, n in enumerate(names):
        if n in excluded:
            continue
        scored.append((abs(_auc(X[:, i], y) - 0.5), i, n))
    scored.sort(reverse=True)

    for _, i, n in scored[:top]:
        a = _auc(X[:, i], y)
        findings.append(Finding(
            feature=n, kind="empirical",
            reason="separates the classes more than most; a lead, not a verdict",
            separation=_std_diff(X[:, i], y), auc=a))

    return findings, excluded


def _std_diff(x: np.ndarray, y: np.ndarray) -> float:
    """Standardised mean difference, pooled. Scale-free, so features in
    wildly different units stay comparable."""
    pos, neg = x[y == 1], x[y == 0]
    if pos.size < 2 or neg.size < 2:
        return 0.0
    sd = np.sqrt((pos.var(ddof=1) + neg.var(ddof=1)) / 2)
    if sd == 0:
        return 0.0
    return float((pos.mean() - neg.mean()) / sd)
