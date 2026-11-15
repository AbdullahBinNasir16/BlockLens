"""The serving layer's one door to third-party market data (Phase 7).

GeckoTerminal, DexScreener and GoPlus used to be called from every browser
through the Vite dev proxy, which a production build does not have. Now the
API calls them, once, for everyone:

* a TTL cache keyed per request, shared by every viewer;
* the `ingest/budget.py` token buckets and a daily call ceiling, so one busy
  page cannot spend a source's rate limit for everyone else;
* a cooldown after a 429, so a throttled source is left alone;
* per-source counters and one structured log line per upstream call, so the
  budget's consumption stays visible (`/api/health`, and the log).
"""
from __future__ import annotations

import json
import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

import httpx

from ..config import CONFIG, Config
from ..ingest.budget import Budget, BudgetExhausted

log = logging.getLogger("blocklens.upstream")

SOURCES = ("geckoterminal", "dexscreener", "goplus")


class UpstreamError(RuntimeError):
    def __init__(self, source: str, message: str):
        super().__init__(f"{source}: {message}")
        self.source = source


class RateLimited(UpstreamError):
    pass


@dataclass
class SourceStats:
    calls: int = 0
    cache_hits: int = 0
    errors: int = 0
    rate_limited: int = 0
    last_ok: bool | None = None
    last_latency_ms: float | None = None
    last_error: str | None = None
    last_at: str | None = None
    cooldown_until: float = 0.0


@dataclass
class Upstream:
    config: Config = CONFIG
    clock: Callable[[], float] = time.monotonic
    client: httpx.Client | None = None
    stats: dict[str, SourceStats] = field(default_factory=lambda: {s: SourceStats() for s in SOURCES})
    _cache: dict[str, tuple[float, Any]] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock)
    _budget: Budget | None = None
    _budget_day: str = ""

    def __post_init__(self) -> None:
        if self.client is None:
            self.client = httpx.Client(timeout=self.config.upstream_timeout_s,
                                       headers={"Accept": "application/json",
                                                "User-Agent": "BlockLens/0.3 (FYP research)"})

    def base(self, source: str) -> str:
        return {"geckoterminal": self.config.geckoterminal_url,
                "dexscreener": self.config.dexscreener_url,
                "goplus": self.config.goplus_url}[source]

    def _charge(self, source: str) -> None:
        day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        with self._lock:
            if self._budget is None or self._budget_day != day:
                self._budget = Budget(config=self.config,
                                      max_calls=self.config.upstream_max_calls_per_day)
                self._budget_day = day
            budget = self._budget
        budget.charge(source)            # blocks on the source's bucket, or raises

    def cached(self, key: str) -> Any | None:
        hit = self._cache.get(key)
        return hit[1] if hit and hit[0] > self.clock() else None

    def stale(self, key: str) -> Any | None:
        """The last value for `key`, however old: served when a source throttles."""
        hit = self._cache.get(key)
        return hit[1] if hit else None

    def get(self, source: str, path: str, ttl: float, *,
            limited: Callable[[int, Any], bool] | None = None) -> Any:
        key = f"{source}:{path}"
        st = self.stats[source]
        hit = self.cached(key)
        if hit is not None:
            st.cache_hits += 1
            return hit
        if st.cooldown_until > self.clock():
            raise RateLimited(source, "cooling down after a rate limit")
        try:
            self._charge(source)
        except BudgetExhausted as e:
            raise UpstreamError(source, str(e)) from e
        t0 = time.perf_counter()
        status, body, err = None, None, None
        try:
            r = self.client.get(self.base(source) + path)
            status = r.status_code
            body = r.json() if status != 429 else None
        except (httpx.HTTPError, ValueError) as e:
            err = f"{type(e).__name__}: {str(e)[:120]}"
        ms = round((time.perf_counter() - t0) * 1000, 1)
        st.calls += 1
        st.last_latency_ms = ms
        st.last_at = datetime.now(timezone.utc).isoformat()
        is_limited = status == 429 or (limited is not None and status is not None and limited(status, body))
        log.info(json.dumps({"event": "upstream", "source": source, "path": path.split("?")[0],
                             "status": status, "ms": ms, "limited": is_limited,
                             "calls": st.calls, "cache_hits": st.cache_hits}))
        if is_limited:
            st.rate_limited += 1
            st.last_ok, st.last_error = False, "rate limited"
            st.cooldown_until = self.clock() + 60
            raise RateLimited(source, "rate limited")
        if err or status is None or status >= 400 or body is None:
            st.errors += 1
            st.last_ok, st.last_error = False, err or f"HTTP {status}"
            raise UpstreamError(source, st.last_error)
        st.last_ok, st.last_error = True, None
        self._cache[key] = (self.clock() + ttl, body)
        return body

    def health(self) -> dict:
        return {s: {"ok": bool(v.last_ok) if v.last_ok is not None else False,
                    "latencyMs": v.last_latency_ms, "checkedAt": v.last_at or "",
                    "calls": v.calls, "cacheHits": v.cache_hits,
                    **({"error": v.last_error} if v.last_error else
                       {"error": "not called yet"} if v.last_ok is None else {})}
                for s, v in self.stats.items()}


UPSTREAM = Upstream()
