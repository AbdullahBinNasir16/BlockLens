"""The budget: does the bucket actually block, and does the ceiling stop a run.

The clock and sleep are injected, so these assertions are about the
arithmetic rather than about wall-clock time. A rate limiter tested with
real sleeps is a slow test that proves less.
"""
from __future__ import annotations

import pytest

from blocklens.config import Config, RateLimit
from blocklens.ingest.budget import Budget, BudgetExhausted, TokenBucket


class FakeClock:
    """A clock that only moves when something sleeps — which is exactly the
    condition under which a blocking limiter is correct."""

    def __init__(self):
        self.t = 1000.0
        self.slept: list[float] = []

    def now(self) -> float:
        return self.t

    def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)
        self.t += seconds


def test_bucket_lets_the_burst_through_without_waiting():
    c = FakeClock()
    b = TokenBucket(rate=2.0, burst=5, clock=c.now, sleep=c.sleep)

    waits = [b.acquire() for _ in range(5)]

    assert waits == [0.0] * 5
    assert c.slept == [], "the burst should not have had to wait"


def test_bucket_blocks_once_the_burst_is_spent():
    c = FakeClock()
    b = TokenBucket(rate=2.0, burst=2, clock=c.now, sleep=c.sleep)

    b.acquire()
    b.acquire()
    waited = b.acquire()        # the bucket is empty: this one has to wait

    assert waited > 0, "the limiter did not block"
    assert c.slept, "the limiter returned without sleeping"
    # At 2 tokens a second, one token costs half a second.
    assert waited == pytest.approx(0.5, abs=1e-6)


def test_bucket_sustains_the_configured_rate():
    """Twenty calls at 4/s must take at least the five seconds they imply,
    minus the free burst."""
    c = FakeClock()
    b = TokenBucket(rate=4.0, burst=4, clock=c.now, sleep=c.sleep)

    for _ in range(20):
        b.acquire()

    elapsed = c.t - 1000.0
    assert elapsed == pytest.approx((20 - 4) / 4.0, abs=1e-6)


def test_bucket_refills_over_time():
    c = FakeClock()
    b = TokenBucket(rate=10.0, burst=3, clock=c.now, sleep=c.sleep)
    for _ in range(3):
        b.acquire()

    c.t += 1.0                  # a second passes elsewhere in the program

    assert b.acquire() == 0.0, "a refilled bucket should not block"
    assert c.slept == []


def _config(**kw) -> Config:
    base = dict(
        limits={"rpc": RateLimit(rate=1000.0, burst=1000)},
        monthly_cu_ceiling=kw.pop("monthly_cu_ceiling", 1_000),
    )
    base.update(kw)
    return Config(**base)


def test_run_call_ceiling_stops_the_run():
    budget = Budget(config=_config(), max_calls=3)
    for _ in range(3):
        budget.charge("rpc")

    with pytest.raises(BudgetExhausted) as e:
        budget.charge("rpc")
    assert "call ceiling" in str(e.value)
    assert budget.requests == 3, "a refused call must not be counted as spent"


def test_monthly_cu_ceiling_accounts_for_what_the_month_already_spent():
    """The ceiling is monthly, not per-run, so a fresh process has to start
    from the ledger rather than from zero."""
    budget = Budget(config=_config(monthly_cu_ceiling=1_000), monthly_cu_used=900)

    budget.charge("alchemy", cu=100)            # exactly at the ceiling: allowed

    with pytest.raises(BudgetExhausted) as e:
        budget.charge("alchemy", cu=1)
    assert "monthly CU ceiling" in str(e.value)
    assert budget.remaining_cu() == 0


def test_charges_are_attributed_per_source():
    budget = Budget(config=_config(), max_calls=100)
    for _ in range(3):
        budget.charge("rpc")
    budget.charge("dexscreener")

    assert budget.by_source == {"rpc": 3, "dexscreener": 1}
    assert budget.requests == 4
