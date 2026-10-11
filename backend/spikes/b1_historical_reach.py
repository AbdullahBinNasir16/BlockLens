"""Phase 2 spike: can the free tier reach 90 days back, and what does a
90-day reserve reconstruction actually cost?

Three questions, in order of how badly a "no" hurts:

1. Does the keyless gateway serve `eth_getLogs` ~3.9M blocks back? If not,
   Phase 2 cannot be built on historical tokens at all on free tiers.
2. Does an *address-filtered* query escape the 1,000-block range cap? The
   cap was measured in Part A on broad queries. If a narrow filter lifts
   it, reconstruction is cheap; if not, it costs ~3,900 calls per token.
3. Do V2-style pools on Base emit `Sync`, which carries reserves directly?
   That would make reserve history exact rather than reconstructed from
   quote-token transfers.

Throwaway. Not part of the system.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from blocklens.ingest.budget import Budget           # noqa: E402
from blocklens.ingest.evm import (                   # noqa: E402
    TRANSFER, UNISWAP_V4_POOL_MANAGER, V3_SWAP, V4_INITIALIZE, topic,
)
from blocklens.ingest.sources import RpcSource, SourceError  # noqa: E402

V2_SYNC = topic("Sync(uint112,uint112)")
BLOCKS_PER_DAY = 43_200
OUT = Path(__file__).parent / "B1_historical_reach.json"

# A long-lived Base pair, from the Phase 1 fixtures: BRETT/WETH on Aerodrome.
PAIR = "0x4e829f8a5213c42535ab84aa40bd4adcce9cba02"
WETH = "0x4200000000000000000000000000000000000006"


def probe(label, fn):
    t0 = time.time()
    try:
        value = fn()
        out = {"ok": True, "value": value, "seconds": round(time.time() - t0, 2)}
    except (SourceError, Exception) as e:  # noqa: BLE001
        out = {"ok": False, "error": str(e)[:300], "seconds": round(time.time() - t0, 2)}
    print(f"  {label:<52} {'OK ' if out['ok'] else 'FAIL'} "
          f"{out.get('value') if out['ok'] else out['error'][:90]}")
    return out


def main() -> None:
    budget = Budget(max_calls=120)
    rpc = RpcSource(budget)
    results = {}

    head = rpc.block_number()
    b90 = head - 90 * BLOCKS_PER_DAY
    b180 = head - 180 * BLOCKS_PER_DAY
    print(f"head {head:,} | 90d ago ~{b90:,} | 180d ago ~{b180:,}\n")
    results["head"] = head
    results["block_90d"] = b90

    print("Q1 does the node serve old data at all")
    results["header_90d"] = probe(
        "eth_getBlockByNumber at 90d",
        lambda: int(rpc.get_block(b90)["timestamp"], 16))
    results["header_180d"] = probe(
        "eth_getBlockByNumber at 180d",
        lambda: int(rpc.get_block(b180)["timestamp"], 16))
    results["v4_initialize_90d"] = probe(
        "eth_getLogs V4 Initialize, 1000 blocks at 90d",
        lambda: len(rpc.get_logs(addresses=[UNISWAP_V4_POOL_MANAGER],
                                 from_block=b90, to_block=b90 + 999,
                                 topics=[V4_INITIALIZE])))
    results["v4_initialize_180d"] = probe(
        "eth_getLogs V4 Initialize, 1000 blocks at 180d",
        lambda: len(rpc.get_logs(addresses=[UNISWAP_V4_POOL_MANAGER],
                                 from_block=b180, to_block=b180 + 999,
                                 topics=[V4_INITIALIZE])))

    print("\nQ2 does an address filter lift the 1,000-block range cap")
    for span in (5_000, 50_000, 500_000, 3_888_000):
        results[f"pair_span_{span}"] = probe(
            f"eth_getLogs [pair] over {span:,} blocks",
            lambda s=span: len(rpc.get_logs(addresses=[PAIR],
                                            from_block=head - s, to_block=head)))

    print("\nQ2b same, with a topic filter as well (narrower still)")
    for span in (50_000, 500_000):
        results[f"pair_topic_span_{span}"] = probe(
            f"eth_getLogs [pair]+Sync over {span:,} blocks",
            lambda s=span: len(rpc.get_logs(addresses=[PAIR], from_block=head - s,
                                            to_block=head, topics=[V2_SYNC])))

    print("\nQ3 what does this pair actually emit (1,000 blocks at head)")
    def census():
        logs = rpc.get_logs(addresses=[PAIR], from_block=head - 999, to_block=head)
        names = {V2_SYNC: "Sync", V3_SWAP: "V3Swap", TRANSFER: "Transfer"}
        counts = {}
        for l in logs:
            t0 = (l.get("topics") or [""])[0]
            counts[names.get(t0, t0[:12])] = counts.get(names.get(t0, t0[:12]), 0) + 1
        return counts
    results["pair_event_census"] = probe("event mix on the pair", census)

    print("\nQ3b can we filter the quote token's transfers to the pair")
    results["quote_inflow"] = probe(
        "eth_getLogs [WETH] topic2=pair, 1000 blocks",
        lambda: len(rpc.get_logs(addresses=[WETH], from_block=head - 999, to_block=head,
                                 topics=[TRANSFER, None, "0x" + "0" * 24 + PAIR[2:]])))

    results["calls_spent"] = budget.requests
    OUT.write_text(json.dumps(results, indent=1), encoding="utf8")
    print(f"\n{budget.requests} calls spent; wrote {OUT.name}")
    rpc.close()


if __name__ == "__main__":
    main()
