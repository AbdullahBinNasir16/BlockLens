from datetime import datetime, timedelta

import numpy as np

from scripts.drawdown import max_concurrent, max_drawdown


def test_max_drawdown_peak_to_trough():
    dd, i, j = max_drawdown(np.array([1.0, 2.0, -4.0, 1.0, -1.0, 5.0]))
    # equity 0,1,3,-1,0,-1,4: peak 3 at index 2, trough -1 at index 3 (first occurrence)
    assert dd == 4.0 and i == 2 and j == 3


def test_max_drawdown_from_start_and_none():
    assert max_drawdown(np.array([-1.0, -2.0]))[:2] == (3.0, 0)
    assert max_drawdown(np.array([1.0, 1.0]))[0] == 0.0


def test_max_concurrent_counts_overlaps_and_touching_ends():
    t = datetime(2026, 11, 1)
    h = lambda n: t + timedelta(hours=n)
    assert max_concurrent([(h(0), h(6)), (h(1), h(7)), (h(2), h(3))]) == 3
    # one closes exactly as the next opens: not concurrent
    assert max_concurrent([(h(0), h(6)), (h(6), h(12))]) == 1
