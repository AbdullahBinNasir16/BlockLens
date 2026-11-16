"""Base's two block-time regimes (DECISIONS.md, 2026-11-16).

The research window is all 2 s blocks, where the clock must give exactly
what the old arithmetic gave; after block 53,556,128 a block is 0.2 s, and
"5 minutes" or "6 hours" must still mean 5 minutes and 6 hours."""
from __future__ import annotations

from datetime import datetime, timezone

from blocklens import chain_time as ct
from blocklens.label import extraction as ex
from blocklens.sampling import design as d

S = ct.SWITCH_BLOCK


def test_the_switch_is_where_it_was_measured():
    assert ct.dt_of(S - 1) == datetime(2026, 11, 5, 18, 0, 1, tzinfo=timezone.utc)
    assert ct.seconds_between(S - 2, S - 1) == 2.0
    assert abs(ct.seconds_between(S, S + 5) - 1.0) < 1e-9


def test_research_blocks_keep_the_old_arithmetic():
    created = 40_000_000                                  # mid-2026 research window
    assert d.cutoff_block(created) == created + d.CUTOFF_BLOCKS == created + 150
    assert ex.window_end(created) == created + ex.WINDOW_BLOCKS == created + 10_800
    assert ct.seconds_between(created, created + 30) == 60.0


def test_after_the_switch_five_minutes_is_1500_blocks():
    created = 58_000_000
    assert d.cutoff_block(created) - created == 1_500
    assert ex.window_end(created) - created == 108_000


def test_a_window_spanning_the_switch_is_counted_in_time():
    created = S - 50          # 98 s before block S (S-1 and S share a second)
    end = d.cutoff_block(created)
    # 98 s of 2 s blocks, then 202 s of 0.2 s blocks: exact to one new block
    assert abs(ct.seconds_between(created, end) - 300) <= 0.2 + 1e-6
    assert abs((end - created) - (50 + 1_010)) <= 1


def test_block_at_inverts_ts_of_on_both_sides():
    for b in (1_000_000, S - 2, S, S + 1, 58_085_970):
        assert ct.block_at(ct.ts_of(b)) == b
    # the last 2 s block and the first 0.2 s block share a timestamp
    # (18:00:01); "the last block at or before" that second is the later one
    assert ct.block_at(ct.ts_of(S - 1)) == S


def test_drift_flags_a_clock_the_chain_disagrees_with():
    assert abs(ct.drift(S + 1000, ct.ts_of(S + 1000))) < 1e-9
    # if the chain went back to 2 s blocks unannounced, an hour later the
    # clock would be ~54 minutes off: far past the alarm
    assert ct.drift(S + 1800, ct.ts_of(S) + 1800 * 2.0) < -ct.MAX_DRIFT_S
