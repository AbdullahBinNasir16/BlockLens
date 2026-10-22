"""Why a launch got its score: exact per-feature contributions.

The shipped model is a gradient-boosted tree ensemble, so each score can be
decomposed exactly into a base rate plus one additive term per feature
(SHAP, path-dependent tree explainer). The decomposition is in log-odds and
sums to the model's own logit to machine precision, which `test_explain.py`
asserts; nothing here is an approximation of the model, and the frozen
artefact is not touched.

What is shown is "which observations moved this launch's risk, and which
way", in the units the feature was measured in. It is an account of the
model, not a causal claim about the launch.
"""
from __future__ import annotations

import math

import numpy as np

# Plain-language labels for every feature in `t5-2026-10`
# (blocklens/model/token_features.py). Kept beside the explainer so that an
# unlabelled feature fails a test rather than reaching the page as a code.
LABELS: dict[str, str] = {
    "g_buyers_funded_by_deployer": "buyers funded by the deployer",
    "g_buyers_with_funder": "buyers with a traceable funder",
    "g_copurchase_tie_share": "buyers tied by co-purchase",
    "g_dispersers": "disperser-funded buyers",
    "g_largest_component_share": "share of buyers in one funding cluster",
    "g_mean_funders_per_buyer": "funders per buyer",
    "g_prior_tokens_mean": "launches the buyers traded before",
    "r_deployer_bought": "deployer bought its own token",
    "r_mint_in_window": "launchpad launch (minted with locked liquidity)",
    "t_buys": "buys by minute 5",
    "t_first_buy_delay_s": "time to the first buy",
    "t_is_v4": "Uniswap V4 pool",
    "t_log_price_drift": "price run-up by minute 5",
    "t_median_buy_delay_s": "median time to a buy",
    "t_reserve_vs_peak": "liquidity still in the pool vs its peak",
    "t_same_block_buyers": "buyers in the launch block (sniping)",
    "t_sell_buy_ratio": "sells per buy",
    "t_sells": "sells by minute 5",
    "t_share_buys_first_minute": "share of buys in the first minute",
    "t_swaps": "swaps by minute 5",
    "t_top_buyer_share": "largest buyer's share of buying",
    "t_unique_buyers": "distinct buyers",
    "t_unique_sellers": "distinct sellers",
}

_SHARES = {"t_share_buys_first_minute", "t_top_buyer_share", "t_reserve_vs_peak",
           "g_copurchase_tie_share", "g_largest_component_share"}
_FLAGS = {"r_deployer_bought", "r_mint_in_window", "t_is_v4"}
_SECONDS = {"t_first_buy_delay_s", "t_median_buy_delay_s"}


def display(feature: str, value: float) -> str:
    """The value as a person would read it, in the feature's own unit."""
    if feature in _FLAGS:
        return "yes" if value >= 0.5 else "no"
    if feature in _SHARES:
        return f"{value * 100:.0f}%"
    if feature in _SECONDS:
        return f"{value:.0f} s" if value < 120 else f"{value / 60:.1f} min"
    if feature == "t_log_price_drift":
        return f"×{math.exp(value):.2f}"
    if feature == "t_sell_buy_ratio" or feature.startswith("g_mean") or feature.startswith("g_prior"):
        return f"{value:.2f}"
    return f"{value:.0f}"


def sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


class Explainer:
    def __init__(self, model, features: list[str]) -> None:
        import shap  # imported here: slow, and only the API process needs it

        missing = [f for f in features if f not in LABELS]
        if missing:
            raise ValueError(f"unlabelled features: {missing}")
        self.features = list(features)
        self._ex = shap.TreeExplainer(model)
        ev = np.array(self._ex.expected_value).reshape(-1)
        self.base_logit = float(ev[-1])

    @property
    def base_rate(self) -> float:
        """The score of a launch about which nothing is known."""
        return sigmoid(self.base_logit)

    def contributions(self, row: dict) -> np.ndarray:
        x = np.array([[float(row.get(n, 0.0) or 0.0) for n in self.features]])
        return np.array(self._ex.shap_values(x), dtype=float).reshape(-1)[-len(self.features):]

    def explain(self, row: dict, top: int = 6) -> dict:
        """The score's anatomy: base rate, the `top` largest movers each way,
        and what the remaining features contributed between them."""
        sv = self.contributions(row)
        order = sorted(range(len(sv)), key=lambda i: -abs(sv[i]))
        drivers = []
        for i in order[:top]:
            name = self.features[i]
            value = float(row.get(name, 0.0) or 0.0)
            drivers.append({
                "feature": name,
                "label": LABELS[name],
                "value": value,
                "display": display(name, value),
                "contribution": round(float(sv[i]), 4),
                "direction": "raises" if sv[i] > 0 else "lowers" if sv[i] < 0 else "neutral",
            })
        rest = float(sum(sv[i] for i in order[top:]))
        logit = self.base_logit + float(sv.sum())
        return {
            "base_rate": round(self.base_rate, 4),
            "base_logit": round(self.base_logit, 4),
            "logit": round(logit, 4),
            "risk": round(sigmoid(logit), 4),
            "drivers": drivers,
            "rest": round(rest, 4),
            "unit": "log-odds",
        }
