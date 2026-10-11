"""Phase 2 spike: can reserves be *sampled* at old blocks instead of
reconstructed from every transfer?

B1/B2 priced the brief's approach at 3,888 calls per token on the default
gateway, or 389 on PublicNode's 10,000-block ranges. Both are for scanning
every block of 90 days. But most of what the label needs is a coarse series:

    peak reserve, reserve at T+90d, price at T+90d

If `eth_call` works at historical blocks (an archive capability, which is
not the same as serving old *logs*), a daily sample is 90 calls per token
and gives all three. The expensive part - *where* the liquidity went - then
only needs one precise 1,000-block scan around the collapse the sampled
series points at, instead of 90 days of scanning.

That would be ~100 calls per token rather than 3,888: a 39x difference, and
the difference between Phase 2 being affordable and not.

Also retries Blockscout with a browser user-agent, since its 403 looked
like a bot block rather than a missing endpoint.

Throwaway. Not part of the system.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

OUT = Path(__file__).parent / "B3_archive_sampling.json"
BLOCKS_PER_DAY = 43_200

# Aerodrome BRETT/WETH: a V2-style pool, so getReserves() applies.
PAIR = "0x4e829f8a5213c42535ab84aa40bd4adcce9cba02"
GET_RESERVES = "0x0902f1ac"      # getReserves()
TOTAL_SUPPLY = "0x18160ddd"      # totalSupply() - LP supply, for pull detection
TOKEN0 = "0x0dfe1681"            # token0()

ENDPOINTS = {
    "tenderly": "https://base.gateway.tenderly.co",
    "publicnode": "https://base-rpc.publicnode.com",
}
TIMEOUT = httpx.Timeout(connect=10.0, read=40.0, write=10.0, pool=10.0)
BROWSER_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")


def rpc(client, url, method, params):
    r = client.post(url, json={"jsonrpc": "2.0", "id": 1, "method": method,
                               "params": params})
    r.raise_for_status()
    body = r.json()
    if "error" in body:
        raise RuntimeError(str(body["error"])[:180])
    return body["result"]


def reserves_at(client, url, block: int | str):
    tag = block if isinstance(block, str) else hex(block)
    res = rpc(client, url, "eth_call", [{"to": PAIR, "data": GET_RESERVES}, tag])
    if not res or res == "0x":
        raise RuntimeError("empty result")
    w = res[2:]
    return int(w[0:64], 16) / 1e18, int(w[64:128], 16) / 1e18


def main() -> None:
    results = {}
    with httpx.Client(timeout=TIMEOUT, headers={"user-agent": "blocklens-spike/0.1"}) as c:
        head = int(rpc(c, ENDPOINTS["tenderly"], "eth_blockNumber", []), 16)
        results["head"] = head
        print(f"head {head:,}\n")

        print("Q1 does eth_call work at historical blocks (archive)")
        for name, url in ENDPOINTS.items():
            row = {}
            for label, blk in (("latest", "latest"),
                               ("-1d", head - BLOCKS_PER_DAY),
                               ("-30d", head - 30 * BLOCKS_PER_DAY),
                               ("-90d", head - 90 * BLOCKS_PER_DAY),
                               ("-180d", head - 180 * BLOCKS_PER_DAY)):
                try:
                    t0 = time.time()
                    r0, r1 = reserves_at(c, url, blk)
                    row[label] = {"ok": True, "reserve0": round(r0, 4),
                                  "reserve1": round(r1, 6),
                                  "seconds": round(time.time() - t0, 2)}
                    print(f"  {name:<12} {label:<7} OK   r0={r0:>16,.2f}  r1={r1:>12,.4f}")
                except Exception as e:  # noqa: BLE001
                    row[label] = {"ok": False, "error": str(e)[:160]}
                    print(f"  {name:<12} {label:<7} FAIL {str(e)[:80]}")
                time.sleep(0.25)
            results[f"archive_{name}"] = row

        print("\nQ2 PublicNode's true range cap, probed gently")
        caps = {}
        url = ENDPOINTS["publicnode"]
        for span in (10_000, 20_000, 50_000, 100_000, 500_000):
            try:
                t0 = time.time()
                logs = rpc(c, url, "eth_getLogs", [{
                    "address": PAIR, "fromBlock": hex(head - span + 1), "toBlock": hex(head)}])
                caps[span] = {"ok": True, "logs": len(logs),
                              "seconds": round(time.time() - t0, 2)}
                print(f"  {span:>9,} blocks  OK   {len(logs):>6} logs in "
                      f"{caps[span]['seconds']}s")
            except Exception as e:  # noqa: BLE001
                caps[span] = {"ok": False, "error": str(e)[:160]}
                print(f"  {span:>9,} blocks  FAIL {str(e)[:90]}")
            time.sleep(1.5)
        results["publicnode_caps"] = caps

        print("\nQ3 LP total supply at old blocks (how a pull is detected)")
        lp = {}
        for label, blk in (("latest", "latest"), ("-90d", head - 90 * BLOCKS_PER_DAY)):
            try:
                res = rpc(c, ENDPOINTS["publicnode"], "eth_call",
                          [{"to": PAIR, "data": TOTAL_SUPPLY},
                           blk if isinstance(blk, str) else hex(blk)])
                lp[label] = int(res, 16) / 1e18
                print(f"  LP supply {label:<7} {lp[label]:,.4f}")
            except Exception as e:  # noqa: BLE001
                lp[label] = f"FAIL {str(e)[:120]}"
                print(f"  LP supply {label:<7} FAIL {str(e)[:90]}")
        results["lp_supply"] = lp

    print("\nQ4 Blockscout with a browser user-agent")
    bs = {}
    with httpx.Client(timeout=TIMEOUT, headers={"user-agent": BROWSER_UA,
                                                "accept": "application/json"}) as c:
        for host in ("https://base.blockscout.com/api/v2",
                     "https://base.blockscout.com/api"):
            try:
                if host.endswith("/v2"):
                    r = c.get(f"{host}/addresses/{PAIR}/token-transfers",
                              params={"type": "ERC-20"})
                else:
                    r = c.get(host, params={"module": "account", "action": "tokentx",
                                            "address": PAIR, "page": 1, "offset": 100})
                r.raise_for_status()
                d = r.json()
                items = d.get("items") or d.get("result") or []
                bs[host] = {"ok": True, "rows": len(items) if isinstance(items, list) else 0}
                print(f"  {host:<45} OK  {bs[host]['rows']} rows")
            except Exception as e:  # noqa: BLE001
                bs[host] = {"ok": False, "error": str(e)[:150]}
                print(f"  {host:<45} FAIL {str(e)[:70]}")
    results["blockscout"] = bs

    OUT.write_text(json.dumps(results, indent=1), encoding="utf8")
    print(f"\nwrote {OUT.name}")


if __name__ == "__main__":
    main()
