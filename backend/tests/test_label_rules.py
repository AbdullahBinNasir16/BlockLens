"""The label definition, criterion by criterion.

No network, no database, no sampling: `rules` is a pure function of
measurements, which is the whole reason it was written that way. These tests
are what make a threshold safe to change — move a constant and they say
exactly which criterion moved with it.
"""
from __future__ import annotations

import pytest

from blocklens.label import rules
from blocklens.label.sample import Point, Series

LAUNCH = 1_760_000_000
DAY = 86_400


def m(**kw) -> rules.Measurements:
    """A measurement bundle that is healthy unless a test says otherwise."""
    base = dict(
        swaps_in_window=50,
        peak_reserve=1_000.0, peak_reserve_ts=LAUNCH + DAY,
        reserve_at_end=900.0,
        peak_price=10.0, peak_price_ts=LAUNCH + DAY, price_at_end=9.0,
        largest_drop_fraction=0.05, largest_drop_ts=LAUNCH + 2 * DAY,
        largest_drop_from=1_000.0, largest_drop_to=950.0,
        active_days_last_30=20,
        points_sampled=100, points_usable=100,
        sibling_pairs_within_window=0,
    )
    base.update(kw)
    return rules.Measurements(**base)


# ---- each criterion in isolation -----------------------------------------

def test_liquidity_pulled_fires_at_the_threshold_and_not_below():
    assert rules.liquidity_pulled(m(largest_drop_fraction=0.90)) is True
    assert rules.liquidity_pulled(m(largest_drop_fraction=0.8999)) is False


def test_liquidity_pulled_does_not_claim_who_took_it():
    """The criterion is about the reserve, not about attribution.

    The brief wanted the outflow tied to the deployer or its funding
    cluster. That needs a cluster, which is Phase 3, so the rule claims only
    what it measured and `build` records the destination as evidence beside
    it. If this ever starts asserting attribution, this test should fail.
    """
    verdict = rules.classify(m(largest_drop_fraction=0.95))
    assert verdict.label == "RUG"
    assert verdict.liquidity_pulled is True
    assert not hasattr(verdict, "outflow_to_deployer")


def test_sustained_collapse_compares_against_the_peak():
    assert rules.sustained_collapse(m(peak_price=10.0, price_at_end=0.5)) is True
    assert rules.sustained_collapse(m(peak_price=10.0, price_at_end=0.51)) is False


def test_sustained_collapse_is_false_when_there_is_no_price():
    assert rules.sustained_collapse(m(peak_price=None, price_at_end=None)) is False


def test_dead_counts_days_the_price_moved():
    assert rules.dead(m(active_days_last_30=1)) is True
    assert rules.dead(m(active_days_last_30=2)) is False


def test_still_live_needs_both_liquidity_and_trading():
    assert rules.still_live(m(reserve_at_end=900.0, active_days_last_30=20)) is True
    # holds its liquidity but nobody trades it
    assert rules.still_live(m(reserve_at_end=900.0, active_days_last_30=1)) is False
    # actively traded but the liquidity has gone
    assert rules.still_live(m(reserve_at_end=10.0, active_days_last_30=20)) is False


def test_never_launched_when_nothing_ever_traded():
    assert rules.never_launched(m(swaps_in_window=0)) is True
    assert rules.never_launched(m(swaps_in_window=1)) is False


def test_never_launched_when_no_observation_landed():
    assert rules.never_launched(m(points_usable=0)) is True


def test_insufficient_coverage_is_about_our_data_not_the_token():
    assert rules.insufficient_coverage(m(points_sampled=100, points_usable=79)) is True
    assert rules.insufficient_coverage(m(points_sampled=100, points_usable=80)) is False


# ---- the combination -----------------------------------------------------

def test_a_pull_is_a_rug():
    assert rules.classify(m(largest_drop_fraction=0.95)).label == "RUG"


def test_a_collapse_without_a_pull_is_failed_not_rug():
    """The distinction the whole dataset rests on: a token nobody wanted is
    not a token whose deployer took the money."""
    v = rules.classify(m(largest_drop_fraction=0.10, peak_price=10.0, price_at_end=0.1))
    assert v.label == "FAILED"
    assert v.sustained_collapse is True
    assert v.liquidity_pulled is False


def test_dead_without_a_pull_is_failed():
    v = rules.classify(m(largest_drop_fraction=0.0, active_days_last_30=0,
                         price_at_end=9.0))
    assert v.label == "FAILED"
    assert v.dead is True


def test_healthy_is_survived():
    assert rules.classify(m()).label == "SURVIVED"


def test_a_migration_withholds_a_rug_verdict():
    """Liquidity leaving a pool is also what a migration looks like."""
    v = rules.classify(m(largest_drop_fraction=0.99, sibling_pairs_within_window=1))
    assert v.label != "RUG"
    assert v.possible_migration is True
    assert v.liquidity_pulled is True, "the measurement still stands"
    assert any("migration" in n for n in v.notes)


def test_poor_coverage_yields_unclear_not_a_confident_verdict():
    """A token whose samples mostly failed must not be called anything.

    This exists because an earlier version did exactly that: 12 of 112
    usable observations, and a confident FAILED.
    """
    v = rules.classify(m(points_sampled=112, points_usable=12,
                         active_days_last_30=0))
    assert v.label == "UNCLEAR"
    assert v.dead is False, "no criterion should be asserted on bad coverage"
    assert v.liquidity_pulled is False
    assert any("usable" in n for n in v.notes)


def test_never_launched_short_circuits_everything():
    v = rules.classify(m(swaps_in_window=0, largest_drop_fraction=0.99))
    assert v.label == "NEVER_LAUNCHED"
    assert v.liquidity_pulled is False, "an excluded token gets no verdict"


def test_unclear_is_reachable_and_is_not_an_error():
    """A token that holds liquidity but barely trades is genuinely unclear:
    not pulled, not collapsed, not dead, not live."""
    v = rules.classify(m(largest_drop_fraction=0.1, peak_price=10.0,
                         price_at_end=9.0, active_days_last_30=4,
                         reserve_at_end=900.0))
    assert v.label == "UNCLEAR"


def test_every_label_is_one_of_the_declared_set():
    cases = [m(), m(swaps_in_window=0), m(largest_drop_fraction=0.99),
             m(active_days_last_30=0), m(points_usable=1),
             m(peak_price=10.0, price_at_end=0.01)]
    for case in cases:
        assert rules.classify(case).label in rules.LABELS


# ---- measurement, from a series -----------------------------------------

def series(points: list[tuple[int, float | None, float | None]]) -> Series:
    s = Series(token_address="0xtoken", pair_key="0xpair", dex="uniswap-v4")
    for off, reserve, price in points:
        s.points.append(Point(block=off // 2, ts=LAUNCH + off,
                              token_reserve=reserve, price=price))
    return s


def test_measure_finds_the_sharpest_single_day_fall():
    s = series([(0, 1000.0, 1.0), (DAY, 950.0, 0.9),
                (2 * DAY, 50.0, 0.1), (3 * DAY, 45.0, 0.1)])
    got = rules.measure(s, launch_ts=LAUNCH, end_ts=LAUNCH + 90 * DAY)

    assert got.largest_drop_fraction == pytest.approx((950 - 50) / 950)
    assert got.largest_drop_from == 950.0
    assert got.largest_drop_to == 50.0
    assert got.largest_drop_ts == LAUNCH + 2 * DAY


def test_measure_ignores_a_fall_across_a_gap_too_long_to_call_a_day():
    """With daily sampling, a 24-hour collapse is a move between adjacent
    samples. A drop spanning a month-long gap is not evidence of one."""
    s = series([(0, 1000.0, 1.0), (40 * DAY, 10.0, 0.1)])
    got = rules.measure(s, launch_ts=LAUNCH, end_ts=LAUNCH + 90 * DAY)
    assert got.largest_drop_fraction == 0.0


def test_measure_excludes_the_launch_hour_from_the_peak_price():
    """At near-zero liquidity the first price is an artefact, not a level
    anyone could trade at in size."""
    s = series([(0, 100.0, 1_000.0), (2 * 3600, 100.0, 5.0),
                (DAY, 100.0, 4.0)])
    got = rules.measure(s, launch_ts=LAUNCH, end_ts=LAUNCH + 90 * DAY)
    assert got.peak_price == 5.0, "the launch candle leaked into the peak"


def test_measure_counts_active_days_only_inside_the_window():
    end = LAUNCH + 90 * DAY
    pts = [(d * DAY, 100.0, float(d)) for d in range(90)]      # price moves daily
    got = rules.measure(series(pts), launch_ts=LAUNCH, end_ts=end)
    assert got.active_days_last_30 is not None
    assert 25 <= got.active_days_last_30 <= 30


def test_measure_reports_a_still_pool_as_zero_active_days():
    pts = [(d * DAY, 100.0, 7.0) for d in range(90)]           # price never moves
    got = rules.measure(series(pts), launch_ts=LAUNCH, end_ts=LAUNCH + 90 * DAY)
    assert got.active_days_last_30 == 0


def test_thresholds_are_all_reported_for_the_record():
    t = rules.thresholds()
    assert t["rule_version"] == rules.RULE_VERSION
    for key in ("liquidity_drop_fraction", "collapse_fraction",
                "dead_active_days", "live_active_days", "live_reserve_fraction",
                "min_usable_fraction", "min_swaps_in_window"):
        assert key in t, f"{key} missing from the recorded thresholds"
