"""The reserve method, checked two independent ways.

Everything in Phase 2 rests on one claim: that `balanceOf(token, holder)`
read at a historical block is that pool's token reserve at that block. If it
is wrong, every label is wrong, and nothing downstream would reveal it.

So it is checked against a second, unrelated path to the same number — a net
sum of Phase 1's stored transfers into and out of the pool's holder — at
three blocks where the reserve actually differs.

The brief asked for a block explorer. Basescan is paid on Base and
Blockscout returns 403 to every request (spikes B2, B3), so one was not
available; and this check is better than the screenshot would have been,
because it re-runs. Regenerate with `python -m tests.record_reserve_check`.
"""
from __future__ import annotations

import pytest

from tests.conftest import load

FIX = load("reserve_check.json")
CHECKS = FIX["checks"]


def test_balance_of_matches_the_transfer_sum_at_every_block():
    """Two independent computations of the same quantity, to the wei."""
    assert len(CHECKS) == 3, "the method is checked at three blocks, not one"
    for c in CHECKS:
        assert c["exact"], (
            f"at block {c['block']} ({c['at']}): transfers say "
            f"{c['from_transfers']}, balanceOf says {c['from_balance_of']}, "
            f"difference {c['difference']}"
        )


def test_the_three_blocks_do_not_all_hold_the_same_value():
    """Three agreements on one number is barely one check.

    The first version of this fixture sampled evenly across the window and
    got the same balance three times, because the pool went static early.
    The blocks are now picked from the transfer history so the reserve
    genuinely moves between them.
    """
    values = {c["from_balance_of"] for c in CHECKS}
    assert len(values) >= 2, f"all three blocks returned {values}"


def test_the_fixture_describes_a_pool_with_real_history():
    assert FIX["transfers_in_window"] > 100
    assert FIX["holder"].startswith("0x")
    assert FIX["window"]["to_block"] > FIX["window"]["from_block"]


def test_blocks_are_inside_the_window_they_claim_to_check():
    lo, hi = FIX["window"]["from_block"], FIX["window"]["to_block"]
    for c in CHECKS:
        assert lo <= c["block"] <= hi, (
            f"block {c['block']} is outside the backfilled window "
            f"{lo}..{hi}, so the transfer sum would be incomplete and the "
            f"comparison meaningless"
        )


@pytest.mark.parametrize("field", ["from_transfers", "from_balance_of"])
def test_recorded_quantities_are_exact_integers_not_floats(field):
    """Stored as strings on purpose: these are wei-scale integers and a
    float would quietly lose the low digits that make the check exact."""
    for c in CHECKS:
        assert isinstance(c[field], str)
        int(c[field])      # raises if it was ever rounded through a float
