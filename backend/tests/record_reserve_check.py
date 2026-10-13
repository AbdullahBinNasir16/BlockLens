"""Verify the reserve method at three points in time, and keep the result.

    python -m tests.record_reserve_check

The brief asked for this to be checked against a block explorer. It is
checked against something stronger and reproducible instead: Phase 1's own
stored transfers. For a chosen block, the net flow of the token into the
pool's holder — every transfer in, minus every transfer out, summed from the
`transfer` table — must equal `balanceOf(token, holder)` read at that same
block. Two independent paths to the same number.

That substitution is not a convenience. Basescan is paid on Base and
Blockscout's public API returns 403 to every request (spikes B2, B3), so an
explorer was not available; and an explorer check would in any case be a
screenshot nobody could re-run, whereas this one is in the test suite.

Three blocks, not one, because a single agreement could be luck in a pool
that never moved.
"""
from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import text

from blocklens.ingest.budget import Budget
from blocklens.ingest.evm import UNISWAP_V4_POOL_MANAGER
from blocklens.ingest.sources import RpcSource
from blocklens.label.sample import Sampler
from blocklens.store.db import session_scope

OUT = Path(__file__).parent / "fixtures" / "reserve_check.json"


def main() -> None:
    budget = Budget(max_calls=60)
    rpc = RpcSource(budget)
    sampler = Sampler(rpc, budget)

    with session_scope() as s:
        # A V4 token with enough movement that agreement cannot be luck.
        row = s.execute(text("""
            select p.token_address, p.address as pool_id,
                   c.from_block, c.to_block, count(t.tx_hash) as transfers
            from pair p
            join backfill_checkpoint c
              on c.token_address = p.token_address and c.chain = p.chain
            join transfer t
              on t.token_address = p.token_address and t.chain = p.chain
            where p.dex = 'uniswap-v4' and c.done
            group by 1, 2, 3, 4
            having count(t.tx_hash) > 100
            order by count(t.tx_hash) desc
            limit 1
        """)).first()
        if row is None:
            raise SystemExit("no suitable V4 token with a complete window")

        token, pool_id, from_block, to_block, n = row
        print(f"token {token}  window {from_block:,}..{to_block:,}  "
              f"{n} transfers\n")

        # Blocks chosen where the balance actually differs. Evenly spaced
        # blocks all returned the same number, because the pool went static
        # early - three agreements on one value is barely one check, so the
        # blocks are picked from the transfer history instead.
        active = [r[0] for r in s.execute(text("""
            select distinct block_number from transfer
            where token_address = :t and (to_address = :h or from_address = :h)
            order by block_number
        """), {"t": token, "h": UNISWAP_V4_POOL_MANAGER}).all()]
        if len(active) >= 3:
            picks = [("first move", active[0]),
                     ("mid history", active[len(active) // 2]),
                     ("window end", to_block)]
        else:
            span = to_block - from_block
            picks = [("one third", from_block + span // 3),
                     ("two thirds", from_block + 2 * span // 3),
                     ("window end", to_block)]
        print(f"  (pool touched in {len(active)} distinct blocks)")
        print()

        checks = []
        for label, block in picks:
            inflow = s.execute(text("""
                select coalesce(sum(raw_value), 0) from transfer
                where token_address = :t and to_address = :h and block_number <= :b
            """), {"t": token, "h": UNISWAP_V4_POOL_MANAGER, "b": block}).scalar()
            outflow = s.execute(text("""
                select coalesce(sum(raw_value), 0) from transfer
                where token_address = :t and from_address = :h and block_number <= :b
            """), {"t": token, "h": UNISWAP_V4_POOL_MANAGER, "b": block}).scalar()
            expected = int(inflow) - int(outflow)
            actual = int(sampler.balance_of(token, UNISWAP_V4_POOL_MANAGER, block))

            checks.append({
                "at": label, "block": block,
                "from_transfers": str(expected),
                "from_balance_of": str(actual),
                "difference": str(actual - expected),
                "exact": actual == expected,
            })
            print(f"  {label:<12} block {block:,}  "
                  f"transfers={expected/1e18:>20,.6f}  "
                  f"balanceOf={actual/1e18:>20,.6f}  "
                  f"{'EXACT' if actual == expected else 'MISMATCH'}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "note": "The reserve method checked two independent ways at three "
                "blocks: a net sum of Phase 1's stored transfers against "
                "balanceOf read at the same block. Substitutes for a block "
                "explorer, which is paid (Basescan) or 403 (Blockscout) on "
                "this chain - and unlike a screenshot, this is re-runnable.",
        "token_address": token, "pool_id": pool_id,
        "holder": UNISWAP_V4_POOL_MANAGER,
        "window": {"from_block": from_block, "to_block": to_block},
        "transfers_in_window": n,
        "checks": checks,
        "distinct_values": len({c["from_balance_of"] for c in checks}),
    }, indent=1), encoding="utf8")
    rpc.close()
    print(f"\nwrote {OUT}  ({budget.requests} calls)")


if __name__ == "__main__":
    main()
