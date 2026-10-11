"""A1, step two: what do public Base RPCs actually allow?

Alchemy's free plan documents a 10-block cap on eth_getLogs. Public
endpoints have their own limits, and the spike needs one that can scan
factory events cheaply. Probes range caps and response-size caps by
asking for progressively wider windows of real Transfer logs.
"""
import json
from _http import STATS, rpc, save

ENDPOINTS = [
    "https://mainnet.base.org",
    "https://base-rpc.publicnode.com",
    "https://base.llamarpc.com",
    "https://1rpc.io/base",
    "https://base.drpc.org",
]
TRANSFER = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
RANGES = [1, 10, 100, 1_000, 10_000, 50_000, 100_000]


def probe(url):
    out = {"endpoint": url}
    head, err = rpc(url, "eth_blockNumber", [], allow_error=True, retries=2)
    if err or not head:
        out["reachable"] = False
        out["error"] = str(err)[:200]
        return out
    out["reachable"] = True
    head = int(head, 16)
    out["head_block"] = head

    caps = {}
    for span in RANGES:
        # a window a week back, so it is real archived data rather than the tip
        to_b = head - 50_000
        from_b = to_b - span + 1
        res, err = rpc(
            url, "eth_getLogs",
            [{"fromBlock": hex(from_b), "toBlock": hex(to_b), "topics": [TRANSFER]}],
            allow_error=True, retries=1, timeout=40,
        )
        if err:
            caps[span] = {"ok": False, "error": json.dumps(err)[:160]}
        else:
            caps[span] = {"ok": True, "logs": len(res)}
        # stop widening once it refuses
        if err:
            break
    out["ranges"] = caps
    widest = max((s for s, r in caps.items() if r.get("ok")), default=0)
    out["widest_ok_range"] = widest
    out["logs_at_widest"] = caps.get(widest, {}).get("logs")
    return out


def main():
    print("A1: probing public Base RPC limits")
    rows = []
    for url in ENDPOINTS:
        r = probe(url)
        rows.append(r)
        if not r["reachable"]:
            print(f"  {url:<34} unreachable: {r['error'][:70]}")
            continue
        print(f"  {url:<34} head {r['head_block']}  widest ok range: {r['widest_ok_range']} blocks "
              f"({r['logs_at_widest']} logs)")
        for span, res in r["ranges"].items():
            if not res.get("ok"):
                print(f"      refused at {span}: {res['error'][:110]}")
    save("rpc_limits.json", rows)
    save("http_stats_probe.json", STATS.report())


if __name__ == "__main__":
    main()
