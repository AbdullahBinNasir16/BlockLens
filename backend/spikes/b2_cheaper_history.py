"""Phase 2 spike: is there a keyless source that makes 90-day history affordable?

B1 established the problem: the default gateway caps `eth_getLogs` at 1,000
blocks no matter how narrow the filter, so 90 days of a pair's history costs
~3,888 calls per token. For even 200 tokens that is three quarters of a
million requests. Not viable.

Two escape routes worth measuring before telling the user it cannot be done:

1. **Another free RPC with a larger range cap.** Part A found 10-1,000 across
   providers, but tested broad queries. Re-test with a narrow address filter,
   which is what Phase 2 actually needs.
2. **Blockscout's public REST API.** Base runs a Blockscout instance with no
   key required. Its address endpoints paginate an address's entire transfer
   history with no block-range concept at all, which would suit this well:
   the tokens Phase 2 cares most about (rugs, dead launches) are precisely
   the ones with little activity to page through.

Throwaway. Not part of the system.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

PAIR = "0x4e829f8a5213c42535ab84aa40bd4adcce9cba02"   # BRETT/WETH, Aerodrome
WETH = "0x4200000000000000000000000000000000000006"
OUT = Path(__file__).parent / "B2_cheaper_history.json"

ENDPOINTS = {
    "tenderly": "https://base.gateway.tenderly.co",
    "official": "https://mainnet.base.org",
    "publicnode": "https://base-rpc.publicnode.com",
    "llamarpc": "https://base.llamarpc.com",
    "drpc": "https://base.drpc.org",
    "blockpi": "https://base.blockpi.network/v1/rpc/public",
    "1rpc": "https://1rpc.io/base",
    "meowrpc": "https://base.meowrpc.com",
}

BLOCKSCOUT = "https://base.blockscout.com/api/v2"
TIMEOUT = httpx.Timeout(connect=10.0, read=40.0, write=10.0, pool=10.0)


def rpc(client, url, method, params):
    r = client.post(url, json={"jsonrpc": "2.0", "id": 1, "method": method,
                               "params": params})
    r.raise_for_status()
    body = r.json()
    if "error" in body:
        raise RuntimeError(str(body["error"])[:200])
    return body["result"]


def max_span(client, url, head) -> dict:
    """Largest address-filtered range the endpoint will answer."""
    best, note = 0, ""
    for span in (1_000, 10_000, 100_000, 1_000_000, 4_000_000):
        try:
            t0 = time.time()
            logs = rpc(client, url, "eth_getLogs", [{
                "address": PAIR,
                "fromBlock": hex(head - span + 1), "toBlock": hex(head),
            }])
            best, note = span, f"{len(logs)} logs in {time.time() - t0:.1f}s"
        except Exception as e:  # noqa: BLE001
            note = f"capped above {best:,}: {str(e)[:110]}"
            break
    return {"max_span": best, "note": note}


def main() -> None:
    results = {}
    with httpx.Client(timeout=TIMEOUT, headers={"user-agent": "blocklens-spike/0.1"}) as c:
        print("Q1 largest address-filtered eth_getLogs range, per endpoint\n")
        for name, url in ENDPOINTS.items():
            try:
                head = int(rpc(c, url, "eth_blockNumber", []), 16)
            except Exception as e:  # noqa: BLE001
                results[name] = {"reachable": False, "error": str(e)[:140]}
                print(f"  {name:<12} unreachable: {str(e)[:70]}")
                continue
            r = max_span(c, url, head)
            r["reachable"] = True
            results[name] = r
            calls_for_90d = -(-3_888_000 // r["max_span"]) if r["max_span"] else None
            r["calls_per_token_90d"] = calls_for_90d
            cost = f"{calls_for_90d:,}" if calls_for_90d else "n/a"
            print(f"  {name:<12} max span {r['max_span']:>9,}  "
                  f"-> {cost:>9} calls/token for 90d   {r['note'][:58]}")

        print("\nQ2 Blockscout public API, no key")
        bs = {}
        try:
            t0 = time.time()
            r = c.get(f"{BLOCKSCOUT}/addresses/{PAIR}/token-transfers",
                      params={"type": "ERC-20"})
            r.raise_for_status()
            d = r.json()
            items = d.get("items") or []
            bs["ok"] = True
            bs["page_size"] = len(items)
            bs["has_next"] = bool(d.get("next_page_params"))
            bs["seconds"] = round(time.time() - t0, 2)
            bs["keys"] = sorted(items[0].keys())[:14] if items else []
            if items:
                it = items[0]
                bs["sample"] = {
                    "block": it.get("block_number") or it.get("block"),
                    "ts": it.get("timestamp"),
                    "token": (it.get("token") or {}).get("symbol"),
                    "from": ((it.get("from") or {}).get("hash") or "")[:12],
                    "to": ((it.get("to") or {}).get("hash") or "")[:12],
                    "value": (it.get("total") or {}).get("value"),
                    "decimals": (it.get("total") or {}).get("decimals"),
                }
            print(f"  token-transfers: {len(items)} rows/page, "
                  f"next_page={bs['has_next']}, {bs['seconds']}s")
            print(f"  sample: {bs.get('sample')}")
        except Exception as e:  # noqa: BLE001
            bs = {"ok": False, "error": str(e)[:200]}
            print(f"  FAILED: {str(e)[:150]}")
        results["blockscout_token_transfers"] = bs

        # counters tell us how many pages a full history would take
        try:
            r = c.get(f"{BLOCKSCOUT}/addresses/{PAIR}/counters")
            r.raise_for_status()
            results["blockscout_counters"] = r.json()
            print(f"  counters: {r.json()}")
        except Exception as e:  # noqa: BLE001
            results["blockscout_counters"] = {"error": str(e)[:160]}
            print(f"  counters failed: {str(e)[:120]}")

    OUT.write_text(json.dumps(results, indent=1), encoding="utf8")
    print(f"\nwrote {OUT.name}")


if __name__ == "__main__":
    main()
