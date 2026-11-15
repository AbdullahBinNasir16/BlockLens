"""Phase 11 shadow scores: the fit recovers what it should, and the
evaluation applies the pre-registered criteria."""
from __future__ import annotations

import numpy as np

from blocklens.live import shadow


def synth(n: int, seed: int) -> list[shadow.Row]:
    """v1 risk four times too high, as forward; self-deployed pools pulled."""
    rng = np.random.default_rng(seed)
    rows = []
    for _ in range(n):
        true = rng.uniform(0.005, 0.2)
        sd = bool(rng.random() < 0.5)
        rows.append(shadow.Row(risk=min(true * 4, 0.99), self_deployed=sd,
                               buyer_loss=bool(rng.random() < true),
                               pulled_6h=sd and bool(rng.random() < 0.85)))
    return rows


def test_pull_aware_label_counts_a_pull_as_a_loss():
    assert shadow.Row(0.1, True, False, True).y_b
    assert not shadow.Row(0.1, False, False, False).y_b


def test_calibration_brings_the_mean_down_to_the_observed_rate():
    rows = synth(6000, 1)
    p = shadow.fit(rows)
    a = shadow.score_a(p, rows)
    observed = np.mean([r.buyer_loss for r in rows])
    assert abs(a.mean() - observed) < 0.01
    assert np.mean([r.risk for r in rows]) > 3 * observed


def test_evaluation_passes_on_a_held_out_set_from_the_same_process():
    p = shadow.fit(synth(6000, 2))
    e = shadow.evaluate(p, synth(4000, 3))
    assert e["reportable"]
    assert e["A"]["pass"]
    assert e["A"]["brier"] < e["A"]["brier_v1"]


def test_below_the_floor_is_not_reportable():
    p = shadow.fit(synth(3000, 4))
    assert not shadow.evaluate(p, synth(500, 5))["reportable"]
