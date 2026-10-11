"""A5: the launch census my first pass missed — Uniswap V4.

V4 pools live in one singleton PoolManager, so they emit no per-pool
creation event of the kind the V2/V3 factory scan filtered on. Counting
them needs a topic filter on Initialize instead. Event topics are computed
in keccak.py, not recalled.
"""
import json, time
from datetime import datetime, timezone
from _http import STATS, get_json, rpc, save
from keccak import topic

URL = "https://base.gateway.tenderly.co"
SPAN = 1_000
PM = "0x498581ff718922c3f8e6a244956af099b2652b2b"
INIT = topic("Initialize(bytes32,address,address,uint24,int24,address,uint160,int24)")
QUOTES = {"0x4200000000000000000000000000000000000006", "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913",
          "0x50c5725949a6f0c72e6c4a641f24049a917db0cb", "0xd9aaec86b65d86f6a7b5b1b0c42ffa531710b6ca",
          "0x0000000000000000000000000000000000000000"}
DAY = "2026-09-05"
SAMPLE = 60


def block_at(ts):
    head, _ = rpc(URL, "eth_blockNumber", [], retries=3)
    hi, lo = int(head, 16), 1
    lo = max(1, hi - 20_000_000)
    while lo < hi:
        mid = (lo + hi) // 2
        b, err = rpc(URL, "eth_getBlockByNumber", [hex(mid), False], allow_error=True, retries=2)
        if err or not b:
            time.sleep(0.4); continue
        if int(b["timestamp"], 16) < ts: lo = mid + 1
        else: hi = mid
        time.sleep(0.07)
    return lo


def main():
    start = block_at(int(datetime.fromisoformat(DAY + "T00:00:00+00:00").timestamp()))
    end = start + 43_200
    print(f"  V4 Initialize scan, {DAY}, blocks {start}-{end}")

    logs, calls, b = [], 0, start
    while b <= end:
        to_b = min(b + SPAN - 1, end)
        res, err = rpc(URL, "eth_getLogs",
                       [{"fromBlock": hex(b), "toBlock": hex(to_b), "address": PM, "topics": [INIT]}],
                       allow_error=True, retries=2, timeout=60)
        calls += 1
        if not err:
            logs.extend(res)
        b = to_b + 1
        time.sleep(0.1)

    toks = {}
    for l in logs:
        c0, c1 = "0x" + l["topics"][2][-40:], "0x" + l["topics"][3][-40:]
        new = [c for c in (c0, c1) if c.lower() not in QUOTES]
        if len(new) == 1:
            toks.setdefault(new[0].lower(), {"token": new[0], "pool_id": l["topics"][1],
                                             "block": int(l["blockNumber"], 16)})
    print(f"  {len(logs)} Initialize events in {calls} calls -> {len(toks)} distinct new tokens "
          f"paired against a known quote")

    sample = list(toks.values())[:SAMPLE]
    traded, launched_today = 0, 0
    rows = []
    for i, t in enumerate(sample):
        try:
            pairs = get_json(f"https://api.dexscreener.com/token-pairs/v1/base/{t['token']}")
        except Exception:
            pairs = []
        if isinstance(pairs, list) and pairs:
            traded += 1
            dated = [p for p in pairs if p.get("pairCreatedAt")] or pairs
            p = min(dated, key=lambda p: p.get("pairCreatedAt") or 0)
            created = p.get("pairCreatedAt")
            day = datetime.fromtimestamp(created / 1000, timezone.utc).date().isoformat() if created else None
            if day == DAY:
                launched_today += 1
            rows.append({**t, "symbol": p["baseToken"]["symbol"], "pair": p["pairAddress"],
                         "dex": p.get("dexId"), "launch_day": day,
                         "liq": round((p.get("liquidity") or {}).get("usd") or 0),
                         "vol24h": round((p.get("volume") or {}).get("h24") or 0),
                         "fdv": p.get("fdv")})
        time.sleep(0.3)
        if (i + 1) % 20 == 0:
            print(f"    classified {i + 1}/{len(sample)}")

    rate = traded / len(sample) if sample else 0
    print(f"\n  of {len(sample)} sampled V4 tokens: {traded} ever traded ({rate:.0%}), "
          f"{launched_today} first paired that day")
    print(f"  implied tradeable V4 launches on {DAY}: ~{round(len(toks) * rate)}")
    for r in sorted(rows, key=lambda r: -(r["liq"] or 0))[:10]:
        print(f"    {r['symbol']:<14} {r['launch_day']} liq ${r['liq']:>9,} vol24h ${r['vol24h']:>9,} {r['dex']}")
    save("v4_census.json", {"day": DAY, "start_block": start, "end_block": end, "calls": calls,
                            "initialize_events": len(logs), "distinct_tokens": len(toks),
                            "sampled": len(sample), "traded_in_sample": traded,
                            "launched_that_day_in_sample": launched_today,
                            "implied_tradeable": round(len(toks) * rate), "rows": rows})
    save("http_stats_v4.json", STATS.report())


if __name__ == "__main__":
    main()
