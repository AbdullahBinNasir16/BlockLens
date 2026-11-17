"""Plausibility checks on third-party market figures (Phase 7 follow-up).

DexScreener and GeckoTerminal report what a pool's contracts say, and a
pool's contracts can say anything: a 45-minute-old token was shown with a
$197M market cap and $29.65M of liquidity on 151 trades
(docs/EXAMINER_WALK.md). BlockLens does not correct such figures. It says,
next to them, when they fail a check a careful reader would make. Each check
is one line, stated in words on screen, and none is a finding about the
token.
"""
from __future__ import annotations

import time

DAY_MS = 86_400_000


def doubts(*, liquidity: float, market_cap: float, fdv: float, volume24h: float,
           txns24h: float, created_at_ms: float, now_ms: float | None = None) -> list[str]:
    now_ms = now_ms if now_ms is not None else time.time() * 1000
    age_ms = now_ms - created_at_ms if created_at_ms else None
    young = age_ms is not None and age_ms < DAY_MS
    cap = market_cap or fdv
    out: list[str] = []
    if cap and liquidity > cap:
        out.append("liquidity is larger than the market cap")
    if young and cap >= 10_000_000 and txns24h < 500:
        out.append("a valuation over $10M on a pool under a day old with fewer than 500 trades")
    if young and liquidity >= 1_000_000 and volume24h < 0.01 * liquidity:
        out.append("over $1M of liquidity with almost no trading against it")
    return out
