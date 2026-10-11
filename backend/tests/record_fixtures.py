"""Record real API responses once, so the tests can run with no network.

Not a test. Run it by hand when a fixture needs refreshing:

    python -m tests.record_fixtures

The recorded files are the only API shapes the suite trusts. Writing them
by hand would prove nothing — a decoder that passes against an invented
response has only been tested against my own assumptions.
"""
from __future__ import annotations

import json
from pathlib import Path

from blocklens.config import CONFIG
from blocklens.ingest.budget import Budget
from blocklens.ingest.evm import SWAP_TOPICS, TRANSFER, UNISWAP_V3_FACTORY, V3_POOL_CREATED
from blocklens.ingest.sources import DexScreenerSource, RpcSource

HERE = Path(__file__).parent / "fixtures"

# A Base token with real history, and the pool DexScreener reports as its
# deepest: an Aerodrome (V2-style) pair, which is what Base actually trades
# on. A Uniswap V3 pool was tried first and sat idle through the window,
# which is itself the reason the fixture search below exists.
TOKEN = "0x532f27101965dd16442e59d40670faf5ebb142e4"      # BRETT
PAIR = "0x4e829f8a5213c42535ab84aa40bd4adcce9cba02"       # BRETT/WETH, Aerodrome
QUOTE = "0x4200000000000000000000000000000000000006"      # WETH


def main() -> None:
    HERE.mkdir(parents=True, exist_ok=True)
    budget = Budget(max_calls=40)
    rpc = RpcSource(budget)
    ds = DexScreenerSource(budget)

    head = rpc.block_number()
    # Walk back in small windows until one holds both a transfer and a swap.
    # A fixture without a swap in it cannot test the swap decoder, and which
    # 200 blocks happen to contain a trade is not knowable in advance.
    logs, from_block, to_block = [], 0, 0
    for back in range(10_000, 10_000 + 20 * 200, 200):
        to_block = head - back
        from_block = to_block - 199
        logs = rpc.get_logs(addresses=[TOKEN, PAIR], from_block=from_block, to_block=to_block)
        has_swap = any((l.get("topics") or [""])[0] in SWAP_TOPICS for l in logs)
        has_transfer = any((l.get("topics") or [""])[0] == TRANSFER for l in logs)
        if has_swap and has_transfer:
            break
    else:
        raise SystemExit("found no window with both a transfer and a swap")
    print(f"window {from_block:,}..{to_block:,}: {len(logs)} logs")
    block = rpc.get_block(to_block)
    # One span exactly: the gateway refuses more, which is the cap Part A
    # measured and the reason rpc_log_span is config rather than a constant.
    pools = rpc.get_logs(addresses=[UNISWAP_V3_FACTORY], from_block=head - rpc.log_span + 1,
                         to_block=head, topics=[V3_POOL_CREATED])

    write = {
        "rpc_get_logs.json": {
            "note": "eth_getLogs for [token, pair] over a 200-block window on Base; chosen because it contains both transfers and swaps",
            "token": TOKEN, "pair": PAIR, "quote": QUOTE,
            "from_block": from_block, "to_block": to_block,
            "transfer_topic": TRANSFER,
            "result": logs,
        },
        "rpc_get_block.json": {"note": "eth_getBlockByNumber, header only", "result": block},
        "rpc_pool_created.json": {
            "note": "Uniswap V3 PoolCreated logs on Base",
            "from_block": head - rpc.log_span + 1, "to_block": head, "result": pools[:40],
        },
        "dexscreener_tokens.json": {
            "note": "GET /tokens/v1/base/{addresses}",
            "addresses": [TOKEN], "result": ds.tokens_batch("base", [TOKEN]),
        },
    }
    for name, payload in write.items():
        path = HERE / name
        path.write_text(json.dumps(payload, indent=1), encoding="utf8")
        n = len(payload.get("result") or [])
        print(f"{name:<28} {path.stat().st_size:>9,} bytes  ({n} rows)")

    rpc.close()
    ds.close()
    print(f"\n{budget.requests} calls, waited {budget.waited_seconds:.1f}s")


if __name__ == "__main__":
    main()
