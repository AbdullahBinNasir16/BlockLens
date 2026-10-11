"""Rate limiting and spend ceilings. Every metered call goes through here.

Three separate ideas, deliberately not conflated:

* a **token bucket** per source, so we stay inside the documented rate and
  are a polite guest on public infrastructure we do not own;
* a **monthly counter**, persisted in the database so a restart cannot
  forget what the month has already cost;
* a **hard ceiling**, so a run that would cross it stops cleanly and writes
  down why, rather than burning the month's allowance at 3am.

The clock and sleep are injectable so the bucket can be tested without
making the suite slow.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable

from ..config import CONFIG, Config


class BudgetExhausted(RuntimeError):
    """A ceiling would be crossed. The run stops; it does not push through."""


class TokenBucket:
    """Classic leaky bucket. `acquire` blocks until a token is free."""

    def __init__(self, rate: float, burst: int,
                 clock: Callable[[], float] = time.monotonic,
                 sleep: Callable[[float], None] = time.sleep):
        self.rate = float(rate)
        self.burst = max(1, int(burst))
        self._clock = clock
        self._sleep = sleep
        self._tokens = float(self.burst)
        self._last = clock()

    def _refill(self) -> None:
        now = self._clock()
        if now > self._last:
            self._tokens = min(self.burst, self._tokens + (now - self._last) * self.rate)
            self._last = now

    def acquire(self, n: int = 1) -> float:
        """Returns the seconds spent waiting — the caller may want to log it."""
        waited = 0.0
        while True:
            self._refill()
            if self._tokens >= n:
                self._tokens -= n
                return waited
            deficit = n - self._tokens
            pause = deficit / self.rate if self.rate > 0 else 0.05
            self._sleep(pause)
            waited += pause


@dataclass
class Budget:
    """Per-run spend, checked against per-month and per-run ceilings."""

    config: Config = CONFIG
    max_calls: int | None = None
    monthly_cu_used: int = 0           # loaded from the ledger at run start
    requests: int = 0
    compute_units: int = 0
    waited_seconds: float = 0.0
    by_source: dict[str, int] = field(default_factory=dict)
    _buckets: dict[str, TokenBucket] = field(default_factory=dict)
    _clock: Callable[[], float] = time.monotonic
    _sleep: Callable[[float], None] = time.sleep

    def __post_init__(self) -> None:
        if self.max_calls is None:
            self.max_calls = self.config.default_max_calls_per_run
        for name, lim in self.config.limits.items():
            self._buckets[name] = TokenBucket(lim.rate, lim.burst, self._clock, self._sleep)

    @staticmethod
    def period(now: datetime | None = None) -> str:
        return (now or datetime.now(timezone.utc)).strftime("%Y-%m")

    def charge(self, source: str, cu: int = 0) -> None:
        """Call immediately before a metered request. Blocks, or raises."""
        if self.max_calls is not None and self.requests >= self.max_calls:
            raise BudgetExhausted(
                f"run call ceiling reached ({self.max_calls} requests); stopping cleanly"
            )
        if cu and (self.monthly_cu_used + self.compute_units + cu) > self.config.monthly_cu_ceiling:
            raise BudgetExhausted(
                f"monthly CU ceiling would be crossed: "
                f"{self.monthly_cu_used + self.compute_units + cu:,} > "
                f"{self.config.monthly_cu_ceiling:,}; stopping cleanly"
            )
        bucket = self._buckets.get(source)
        if bucket is not None:
            self.waited_seconds += bucket.acquire()
        self.requests += 1
        self.compute_units += cu
        self.by_source[source] = self.by_source.get(source, 0) + 1

    def remaining_calls(self) -> int:
        return max(0, (self.max_calls or 0) - self.requests)

    def remaining_cu(self) -> int:
        return max(0, self.config.monthly_cu_ceiling - self.monthly_cu_used - self.compute_units)
