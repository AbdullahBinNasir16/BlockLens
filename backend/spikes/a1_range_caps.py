"""A1, step four: the real eth_getLogs range cap on every free Base RPC.

The project's cost model lives or dies on this number: a day of Base is
~43,200 blocks, so calls-per-token-day = 43,200 / cap.
"""
import time
from _http import STATS, rpc, save

TR = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
TOKEN = "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913"
SIZES = [50, 100, 500, 1_000, 2_000, 5_000, 10_000, 43_200]
ENDPOINTS = [
    "https://1rpc.io/base", "https://base.drpc.org", "https://base.meowrpc.com",
    "https://base.gateway.tenderly.co", "https://base-mainnet.public.blastapi.io",
    "https://base.api.onfinality.io/public", "https://base-pokt.nodies.app",
    "https://mainnet.base.org",
]


def main():
    out = []
    for url in ENDPOINTS:
        head, err = rpc(url, "eth_blockNumber", [], allow_error=True, retries=2, timeout=15)
        if err or not head:
            out.append({"endpoint": url, "reachable": False, "error": str(err)[:160]})
            print(f"{url:<46} unreachable")
            continue
        h = int(head, 16)
        row = {"endpoint": url, "reachable": True, "head": h, "tries": {}}
        best = 0
        for span in SIZES:
            to_b = h - 100_000
            res, err = rpc(url, "eth_getLogs",
                           [{"fromBlock": hex(to_b - span + 1), "toBlock": hex(to_b),
                             "address": TOKEN, "topics": [TR]}],
                           allow_error=True, retries=1, timeout=45)
            if err:
                row["tries"][span] = {"ok": False, "error": str(err)[:200]}
            else:
                row["tries"][span] = {"ok": True, "logs": len(res)}
                best = span
            time.sleep(1.2)   # be a polite guest on free infrastructure
        row["max_range"] = best
        row["calls_per_token_day"] = (43_200 // best + 1) if best else None
        out.append(row)
        msg = next((t["error"] for s, t in row["tries"].items() if not t["ok"]), "")
        print(f"{url:<46} max range {best:>6} blocks -> {row['calls_per_token_day']} calls/token-day   {msg[:80]}")
    save("range_caps.json", out)
    save("http_stats_caps.json", STATS.report())


if __name__ == "__main__":
    main()
