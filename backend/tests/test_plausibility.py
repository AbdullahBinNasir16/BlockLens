"""The plausibility checks flag what a careful reader would doubt, and
leave ordinary pools alone."""
from __future__ import annotations

from blocklens.api.plausibility import DAY_MS, doubts

NOW = 1_800_000_000_000


def test_the_walk_through_case_is_doubted():
    # UTDF: 45 minutes old, $197.65M cap, $29.65M liquidity, 151 trades, $17.3K volume
    d = doubts(liquidity=29.65e6, market_cap=197.65e6, fdv=197.65e6, volume24h=17.3e3,
               txns24h=151, created_at_ms=NOW - 45 * 60_000, now_ms=NOW)
    assert any("under a day old" in x for x in d)
    assert any("almost no trading" in x for x in d)


def test_an_ordinary_old_pool_is_not_doubted():
    assert doubts(liquidity=900e3, market_cap=30e6, fdv=20e6, volume24h=320e3, txns24h=774,
                  created_at_ms=NOW - 300 * DAY_MS, now_ms=NOW) == []


def test_liquidity_above_market_cap_is_doubted_at_any_age():
    d = doubts(liquidity=5e6, market_cap=1e6, fdv=1e6, volume24h=1e6, txns24h=10_000,
               created_at_ms=NOW - 400 * DAY_MS, now_ms=NOW)
    assert d == ["liquidity is larger than the market cap"]
