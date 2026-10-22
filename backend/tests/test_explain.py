"""The explanation is an exact decomposition of the shipped model's score."""
from __future__ import annotations

import math

import joblib
import numpy as np
import pytest

from blocklens.live.explain import LABELS, Explainer, display

ART = "data/models/buyer_loss_v1.joblib"


@pytest.fixture(scope="module")
def ex():
    a = joblib.load(ART)
    return Explainer(a["model"], a["meta"]["features"]), a["model"], a["meta"]["features"]


def _row(names, **over):
    row = {n: 0.0 for n in names}
    row.update({"t_reserve_vs_peak": 1.0, "t_unique_buyers": 9, "t_buys": 11, "t_swaps": 12,
                "t_first_buy_delay_s": 4, "t_median_buy_delay_s": 60, "t_is_v4": 1.0})
    row.update(over)
    return row


def test_every_feature_has_a_label(ex):
    _, _, names = ex
    assert set(names) <= set(LABELS)


def test_contributions_add_up_to_the_models_logit(ex):
    e, model, names = ex
    for over in ({}, {"r_mint_in_window": 1.0}, {"t_top_buyer_share": 0.9, "t_same_block_buyers": 6}):
        row = _row(names, **over)
        x = np.array([[float(row[n]) for n in names]])
        p = float(model.predict_proba(x)[0, 1])
        logit = math.log(p / (1 - p))
        out = e.explain(row, top=23)
        assert abs(out["logit"] - logit) < 1e-3
        assert abs(out["risk"] - p) < 1e-3
        assert abs(out["rest"]) < 1e-9          # all features listed: nothing left over


def test_drivers_are_ranked_by_size_and_carry_their_direction(ex):
    e, _, names = ex
    out = e.explain(_row(names, r_mint_in_window=1.0), top=5)
    mags = [abs(d["contribution"]) for d in out["drivers"]]
    assert mags == sorted(mags, reverse=True) and len(mags) == 5
    for d in out["drivers"]:
        assert d["direction"] == ("raises" if d["contribution"] > 0 else "lowers" if d["contribution"] < 0 else "neutral")
        assert d["label"] == LABELS[d["feature"]]
    assert 0 < out["base_rate"] < 1


def test_display_speaks_the_features_own_unit():
    assert display("r_mint_in_window", 1.0) == "yes"
    assert display("t_reserve_vs_peak", 0.734) == "73%"
    assert display("t_first_buy_delay_s", 4) == "4 s"
    assert display("t_first_buy_delay_s", 300) == "5.0 min"
    assert display("t_log_price_drift", math.log(2.5)) == "×2.50"
    assert display("t_unique_buyers", 12) == "12"
