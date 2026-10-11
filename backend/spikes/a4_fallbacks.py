"""A4: price the fallbacks — Etherscan V2 chains, and Solana.

Etherscan: probe which chains the free tier actually serves, without a
key, by reading how the API refuses. "not supported for this chain" is a
plan limit; "missing api key" means the chain is on the free tier and only
a key is missing.

Solana: count a token's first-day transaction signatures on the public
RPC, which is the same unit Helius bills per call.
"""
import json, time
from _http import STATS, get_json, rpc, save

ETHERSCAN = "https://api.etherscan.io/v2/api"
CHAINS = {"Ethereum": 1, "Base": 8453, "BNB Chain": 56, "Arbitrum One": 42161,
          "Unichain": 130, "Polygon": 137, "Blast": 81457, "Linea": 59144, "Optimism": 10}
SOL_RPC = "https://api.mainnet-beta.solana.com"


def etherscan_probe():
    out = {}
    for name, cid in CHAINS.items():
        url = (f"{ETHERSCAN}?chainid={cid}&module=block&action=getblocknobytime"
               f"&timestamp=1760000000&closest=before")
        try:
            d = get_json(url, retries=2)
            msg = str(d.get("result") or d.get("message"))[:120]
            status = d.get("status")
        except Exception as e:  # noqa: BLE001
            msg, status = f"error {e}"[:120], "?"
        gated = "not supported for this chain" in msg.lower() or "upgrade" in msg.lower()
        out[name] = {"chainid": cid, "status": status, "message": msg,
                     "free_tier": "NO - paid plan required" if gated else "yes (key required)"}
        print(f"  {name:<14} chainid {cid:<6} {out[name]['free_tier']:<24} {msg[:70]}")
        time.sleep(0.4)
    return out


def solana_token_day(mint, label):
    """Signatures that mention the mint, oldest first, capped at 10 pages."""
    sigs, calls, before, oldest, newest = 0, 0, None, None, None
    pages = []
    while calls < 10:
        params = [mint, {"limit": 1000, **({"before": before} if before else {})}]
        res, err = rpc(SOL_RPC, "getSignaturesForAddress", params, allow_error=True, retries=2, timeout=40)
        calls += 1
        if err:
            print(f"    ! {label}: {str(err)[:90]}")
            break
        if not res:
            break
        sigs += len(res)
        pages.append(len(res))
        newest = newest or res[0].get("blockTime")
        oldest = res[-1].get("blockTime")
        before = res[-1]["signature"]
        if len(res) < 1000:
            break
        time.sleep(0.6)
    span_h = round((newest - oldest) / 3600, 1) if newest and oldest else None
    print(f"    {label}: {sigs} signatures over {calls} calls, spanning {span_h}h (newest-first)")
    return {"mint": mint, "signatures_seen": sigs, "calls": calls, "pages": pages, "span_hours": span_h}


def main():
    print("A4a: Etherscan V2 free-tier chain coverage (no key, reading the refusal)")
    es = etherscan_probe()

    print("\nA4b: Solana — recent tokens from DexScreener, first-day signature volume")
    sol = []
    try:
        prof = get_json("https://api.dexscreener.com/token-profiles/latest/v1")
        mints = [p["tokenAddress"] for p in prof if p.get("chainId") == "solana"][:3]
    except Exception as e:  # noqa: BLE001
        print("  !", e); mints = []
    for m in mints:
        sol.append(solana_token_day(m, m[:10]))
        time.sleep(1.0)

    print("\nA4c: Base block time, measured")
    b1, _ = rpc("https://base.gateway.tenderly.co", "eth_getBlockByNumber", [hex(51_000_000), False], retries=3)
    b2, _ = rpc("https://base.gateway.tenderly.co", "eth_getBlockByNumber", [hex(51_043_200), False], retries=3)
    dt = int(b2["timestamp"], 16) - int(b1["timestamp"], 16)
    print(f"  43,200 blocks spanned {dt}s ({dt/3600:.2f}h) -> {dt/43200:.2f}s per block")

    save("a4_fallbacks.json", {"etherscan": es, "solana": sol,
                               "base_block_seconds": dt / 43200,
                               "base_blocks_per_day": round(86400 / (dt / 43200))})
    save("http_stats_a4.json", STATS.report())


if __name__ == "__main__":
    main()
