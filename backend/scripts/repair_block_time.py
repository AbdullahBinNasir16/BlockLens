"""One-off repair after Base's block-time switch (DECISIONS.md, 2026-11-16).

    python -m scripts.repair_block_time            # dry run: counts only
    python -m scripts.repair_block_time --apply

* `launch_ts` is recomputed from `created_block` with the two-regime clock.
  Before the fix it was the head's time minus 2 s a block, which after the
  switch put recent launches up to 10x too far in the past.
* A 1/7/30/90-day reserve read at `created_block + days x 43,200` (the old
  2 s arithmetic) whose block fell after the switch was read at the wrong
  time; it is cleared, and the fixed resolver reads it again at the right one.
Predictions themselves are not touched: the log is append-only, and the
invalid ones are excluded by `resolver.VALID_SQL`, not rewritten.
"""
from __future__ import annotations

import sys

from sqlalchemy import text

from blocklens import chain_time
from blocklens.store.db import session_factory

HORIZONS = {"reserve_1d": 1, "reserve_7d": 7, "reserve_30d": 30, "reserve_90d": 90}


def main() -> None:
    apply = "--apply" in sys.argv
    with session_factory()() as s:
        rows = s.execute(text("select token_address, chain, created_block, launch_ts from live_prediction")).all()
        fixes = []
        for tok, ch, blk, lt in rows:
            right = chain_time.dt_of(blk)
            if lt is None or abs((lt - right).total_seconds()) > 5:
                fixes.append((tok, ch, right, (lt - right).total_seconds() if lt else None))
        worst = max((abs(f[3]) for f in fixes if f[3] is not None), default=0)
        print(f"launch_ts: {len(fixes)} of {len(rows)} rows off by more than 5 s (worst {worst / 3600:.1f} h)")
        cleared = {}
        for col, days in HORIZONS.items():
            n = s.execute(text(f"""select count(*) from live_prediction
                where {col} is not null and created_block + :b > :sw"""),
                {"b": days * 43_200, "sw": chain_time.SWITCH_BLOCK}).scalar()
            cleared[col] = n
        print("horizon reserves read after the switch, to clear:", cleared)
        if not apply:
            print("dry run: nothing changed (pass --apply)")
            return
        for tok, ch, right, _ in fixes:
            s.execute(text("update live_prediction set launch_ts = :t where token_address = :k and chain = :c"),
                      {"t": right, "k": tok, "c": ch})
        for col, days in HORIZONS.items():
            s.execute(text(f"""update live_prediction set {col} = null
                where {col} is not null and created_block + :b > :sw"""),
                {"b": days * 43_200, "sw": chain_time.SWITCH_BLOCK})
        s.commit()
        print("applied")


if __name__ == "__main__":
    main()
