"""Phase 2 spike, decisive test: `balanceOf(quote, pair)` at historical blocks.

B3 proved nothing either way - `getReserves()` reverted at every block
including `latest`, because the pool under test is an Aerodrome
concentrated-liquidity pool and has no such function. The revert at -180d
was the same revert as at `latest`, which hints the call did execute at that
old block, but hints are not measurements.

`balanceOf(pair)` on the quote token is the right probe, and a better design
besides: it is the quote reserve by definition, it works identically for V2,
V3 and Aerodrome CL pools, and it needs no knowledge of the venue's ABI.

If this answers at 90 and 180 days, the label can sample a daily reserve
series for ~90-180 calls per token instead of scanning 3,888 windows.

(V4 is the known exception: one PoolManager holds every pool's funds, so a
balance there is not one pool's reserve. Measured here, not assumed.)

Throwaway. Not part of the system.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

OUT = Path(__file__).parent / "B4_balance_sampling.json"
BLOCKS_PER_DAY = 43_200
RPC = "https://base.gateway.tenderly.co"

WETH = "0x4200000000000000000000000000000000000006"
USDC = "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913"
BALANCE_OF = "0x70a08231"

PAIRS = {
    # (pair address, quote token, what it is)
    "aerodrome-cl": ("0x4e829f8a5213c42535ab84aa40bd4adcce9cba02", WETH,
                     "BRETT/WETH, concentrated liquidity"),
    "uniswap-v3": ("0x76bf0abd20f1e0155ce40a62615a90a709a6c3d8", WETH,
                   "BRETT/WETH, Uniswap V3"),
    "v4-manager": ("0x498581ff718922c3f8e6a244956af099b2652b2b", WETH,
                   "the V4 PoolManager, which holds every V4 pool at once"),
}
TIMEOUT = httpx.Timeout(connect=10.0, read=40.0, write=10.0, pool=10.0)


def rpc(client, method, params):
    r = client.post(RPC, json={"jsonrpc": "2.0", "id": 1, "method": method,
                               "params": params})
    r.raise_for_status()
    body = r.json()
    if "error" in body:
        raise RuntimeError(str(body["error"])[:180])
    return body["result"]


def balance_of(client, token: str, holder: str, block) -> float:
    data = BALANCE_OF + "0" * 24 + holder[2:].lower()
    tag = block if isinstance(block, str) else hex(block)
    res = rpc(client, "eth_call", [{"to": token, "data": data}, tag])
    if not res or res == "0x":
        raise RuntimeError("empty result")
    return int(res, 16) / 1e18


def main() -> None:
    results = {}
    with httpx.Client(timeout=TIMEOUT, headers={"user-agent": "blocklens-spike/0.1"}) as c:
        head = int(rpc(c, "eth_blockNumber", []), 16)
        results["head"] = head
        print(f"head {head:,}\n")

        points = [("latest", "latest"),
                  ("-7d", head - 7 * BLOCKS_PER_DAY),
                  ("-30d", head - 30 * BLOCKS_PER_DAY),
                  ("-90d", head - 90 * BLOCKS_PER_DAY),
                  ("-180d", head - 180 * BLOCKS_PER_DAY),
                  ("-365d", head - 365 * BLOCKS_PER_DAY)]

        for name, (pair, quote, what) in PAIRS.items():
            print(f"{name}  ({what})")
            row = {}
            for label, blk in points:
                try:
                    t0 = time.time()
                    bal = balance_of(c, quote, pair, blk)
                    row[label] = {"ok": True, "weth": round(bal, 6),
                                  "seconds": round(time.time() - t0, 2)}
                    print(f"  {label:<7} OK   {bal:>18,.6f} WETH   "
                          f"{row[label]['seconds']}s")
                except Exception as e:  # noqa: BLE001
                    row[label] = {"ok": False, "error": str(e)[:170]}
                    print(f"  {label:<7} FAIL {str(e)[:100]}")
                time.sleep(0.3)
            results[name] = row
            print()

        # How long a daily sample actually takes, measured not guessed.
        print("timing a 90-point daily series on one pair")
        pair, quote, _ = PAIRS["uniswap-v3"]
        t0, ok, series = time.time(), 0, []
        for d in range(90):
            try:
                blk = head - d * BLOCKS_PER_DAY
                series.append(round(balance_of(c, quote, pair, blk), 6))
                ok += 1
            except Exception:  # noqa: BLE001
                series.append(None)
            time.sleep(0.05)
        elapsed = time.time() - t0
        results["daily_series_90"] = {
            "points_ok": ok, "seconds": round(elapsed, 1),
            "seconds_per_call": round(elapsed / 90, 3),
            "peak": max((v for v in series if v is not None), default=None),
            "latest": series[0], "oldest": series[-1],
            "series_head": series[:12],
        }
        print(f"  {ok}/90 points in {elapsed:.1f}s ({elapsed / 90:.2f}s per call)")
        print(f"  peak {results['daily_series_90']['peak']:,.4f} WETH, "
              f"now {series[0]:,.4f}, 90d ago {series[-1]:,.4f}")

    OUT.write_text(json.dumps(results, indent=1), encoding="utf8")
    print(f"\nwrote {OUT.name}")


if __name__ == "__main__":
    main()
