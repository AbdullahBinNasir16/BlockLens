"""Phase 2 spike: is `balanceOf(token, PoolManager)` a V4 pool's token reserve?

B5 left V4 without a reserve: the PoolManager holds every pool's *quote*
token at once, so a WETH balance there is meaningless per pool, and
`getLiquidity` returns active-at-tick liquidity, which is 0 whenever price
leaves the positions.

But the asymmetry is the opening. The PoolManager holds **this token** only
on account of pools containing this token. If a launch has exactly one
pool - the common case - then the PoolManager's balance of that token *is*
that pool's token reserve, exactly and for one call.

This is checkable without trusting anything: Phase 1 already stored every
transfer of these tokens for their first 24 hours. The net flow into the
PoolManager over that window must equal its balance at the window's end.
If the two agree to the wei, the method is sound.

Throwaway. Not part of the system.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import httpx
from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from blocklens.ingest.evm import keccak256                      # noqa: E402
from blocklens.store.db import session_scope                    # noqa: E402

OUT = Path(__file__).parent / "B6_v4_token_reserve.json"
RPC = "https://base.gateway.tenderly.co"
POOL_MANAGER = "0x498581ff718922c3f8e6a244956af099b2652b2b"
BALANCE_OF = "0x70a08231"
TIMEOUT = httpx.Timeout(connect=20.0, read=40.0, write=20.0, pool=20.0)


def post(client, payload, tries=3):
    for i in range(tries):
        try:
            return client.post(RPC, json=payload).json()
        except Exception:  # noqa: BLE001
            if i == tries - 1:
                raise
            time.sleep(2)


def balance_raw(client, token: str, holder: str, block) -> int:
    data = BALANCE_OF + "0" * 24 + holder[2:].lower()
    tag = block if isinstance(block, str) else hex(block)
    b = post(client, {"jsonrpc": "2.0", "id": 1, "method": "eth_call",
                      "params": [{"to": token, "data": data}, tag]})
    if "error" in b:
        raise RuntimeError(str(b["error"])[:140])
    res = b["result"]
    return int(res, 16) if res and res != "0x" else 0


def main() -> None:
    results = {}
    with session_scope() as s:
        # V4 tokens whose first 24 hours we hold in full.
        rows = s.execute(text("""
            select p.token_address, p.address as pool_id, c.to_block,
                   count(t.tx_hash) as transfers
            from pair p
            join backfill_checkpoint c
              on c.token_address = p.token_address and c.chain = p.chain
            join transfer t
              on t.token_address = p.token_address and t.chain = p.chain
            where p.dex = 'uniswap-v4' and c.done
            group by 1, 2, 3
            having count(t.tx_hash) > 50
            order by count(t.tx_hash) desc
            limit 5
        """)).all()

        # How many V4 pools does each of these tokens have? The method is
        # only exact when the answer is one.
        pool_counts = dict(s.execute(text("""
            select token_address, count(*) from pair
            where dex = 'uniswap-v4' group by 1
        """)).all())

    print(f"checking {len(rows)} V4 tokens\n")
    with httpx.Client(timeout=TIMEOUT, headers={"user-agent": "blocklens-spike/0.1"}) as c:
        checks = []
        for token, pool_id, to_block, n_transfers in rows:
            with session_scope() as s:
                # Net flow into the PoolManager across the stored window.
                inflow = s.execute(text("""
                    select coalesce(sum(raw_value), 0) from transfer
                    where token_address = :t and to_address = :pm
                      and block_number <= :b
                """), {"t": token, "pm": POOL_MANAGER, "b": to_block}).scalar()
                outflow = s.execute(text("""
                    select coalesce(sum(raw_value), 0) from transfer
                    where token_address = :t and from_address = :pm
                      and block_number <= :b
                """), {"t": token, "pm": POOL_MANAGER, "b": to_block}).scalar()

            expected = int(inflow) - int(outflow)
            try:
                actual = balance_raw(c, token, POOL_MANAGER, to_block)
            except Exception as e:  # noqa: BLE001
                print(f"  {token[:12]}  FAIL {str(e)[:70]}")
                continue

            diff = actual - expected
            rel = abs(diff) / actual if actual else (0.0 if not diff else 1.0)
            row = {
                "token": token, "pools": pool_counts.get(token, 0),
                "transfers_in_window": n_transfers, "at_block": to_block,
                "expected_from_transfers": str(expected),
                "actual_balance_of": str(actual),
                "difference": str(diff), "relative_error": rel,
                "exact": diff == 0,
            }
            checks.append(row)
            flag = "EXACT" if diff == 0 else f"off by {rel:.2%}"
            print(f"  {token[:12]}  pools={row['pools']}  "
                  f"expected={expected/1e18:>18,.4f}  "
                  f"actual={actual/1e18:>18,.4f}  {flag}")
            time.sleep(0.3)

    results["checks"] = checks
    results["exact_count"] = sum(1 for c_ in checks if c_["exact"])
    results["single_pool_count"] = sum(1 for c_ in checks if c_["pools"] == 1)
    OUT.write_text(json.dumps(results, indent=1), encoding="utf8")
    print(f"\n{results['exact_count']}/{len(checks)} exact; "
          f"{results['single_pool_count']}/{len(checks)} have exactly one V4 pool")
    print(f"wrote {OUT.name}")


if __name__ == "__main__":
    main()
