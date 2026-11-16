"""Base's clock: block numbers to times and back, across block-time changes.

Every duration in the live system used to be a block count at 2 seconds a
block. At block 53,556,128 (2026-11-05 18:00:01 UTC) Base moved to 0.2 s
blocks, and from then on "150 blocks" meant 30 seconds, not 5 minutes
(DECISIONS.md, 2026-11-16). Durations are now times, converted here, and
nowhere else.

The regimes are fixed, measured points: block -> (timestamp, seconds per
block). The clock is exact on the 2 s side (every block was 2 s apart) and
on the 0.2 s side at Base's nominal rate. `drift` compares it with a real
block's timestamp, so the live scorer can stop, loudly, the next time the
chain changes under it.
"""
from __future__ import annotations

from bisect import bisect_right
from datetime import datetime, timezone

# (first block of the regime, its timestamp in UTC seconds, seconds per block)
# The 2 s regime is anchored on the last 2 s block before the switch.
SWITCH_BLOCK = 53_556_128
SWITCH_TS = 1_793_901_601                      # 2026-11-05 18:00:01 UTC, block 53,556,127
REGIMES: list[tuple[int, float, float]] = [
    (0, SWITCH_TS - (SWITCH_BLOCK - 1) * 2.0, 2.0),
    (SWITCH_BLOCK, float(SWITCH_TS), 0.2),
]
# Seconds of disagreement with a real block timestamp before the clock is
# declared wrong. Block timestamps are whole seconds; normal jitter is ~1 s.
MAX_DRIFT_S = 30.0


def _regime_for_block(block: int) -> tuple[int, float, float]:
    i = bisect_right([r[0] for r in REGIMES], block) - 1
    return REGIMES[max(0, i)]


def ts_of(block: int) -> float:
    """UTC seconds at `block`."""
    b0, t0, s = _regime_for_block(block)
    return t0 + (block - b0) * s


def block_at(ts: float) -> int:
    """The last block at or before UTC seconds `ts`."""
    for b0, t0, s in reversed(REGIMES):
        if ts >= t0:
            return b0 + int((ts - t0) // s)
    b0, t0, s = REGIMES[0]
    return b0 + int((ts - t0) // s)


def dt_of(block: int) -> datetime:
    return datetime.fromtimestamp(ts_of(block), timezone.utc)


def seconds_between(a: int, b: int) -> float:
    return ts_of(b) - ts_of(a)


def block_after(block: int, seconds: float) -> int:
    """The block `seconds` after `block`: 5 minutes is 150 blocks before the
    switch and 1,500 after it, and a window that spans the switch is both."""
    return block_at(ts_of(block) + seconds)


def drift(block: int, real_ts: float) -> float:
    """How far the clock is from a real block's timestamp, in seconds."""
    return ts_of(block) - real_ts
