"""A1, step six: real Base launches across several days.

Scans the Uniswap V3 factory for pools created on a set of historical
days, then asks DexScreener which of those tokens ever traded. A token
counts as a launch only if its oldest pair is the one found that day.
"""
import json, sys, time
from datetime import datetime, timezone
from _http import STATS, get_json, rpc, save

URL = "https://base.gateway.tenderly.co"
SPAN = 1_000
V3 = "0x33128a8fc17869897dce68ed026d694621f6fdfd"
QUOTES = {"0x4200000000000000000000000000000000000006", "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913",
          "0x50c5725949a6f0c72e6c4a641f24049a917db0cb", "0xd9aaec86b65d86f6a7b5b1b0c42ffa531710b6ca"}
DAYS = ["2026-07-20", "2026-08-12", "2026-09-05", "2026-09-28"]


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


def pools_on(day):
    start = block_at(int(datetime.fromisoformat(day + "T00:00:00+00:00").timestamp()))
    end = start + 43_200
    logs, calls, b = [], 0, start
    while b <= end:
        to_b = min(b + SPAN - 1, end)
        res, err = rpc(URL, "eth_getLogs", [{"fromBlock": hex(b), "toBlock": hex(to_b), "address": V3}],
                       allow_error=True, retries=2, timeout=60)
        calls += 1
        if not err: logs.extend(res)
        b = to_b + 1
        time.sleep(0.1)
    toks = {}
    for l in logs:
        if len(l["topics"]) < 3: continue
        a, bb = "0x" + l["topics"][1][-40:], "0x" + l["topics"][2][-40:]
        new = [t for t in (a, bb) if t.lower() not in QUOTES]
        if len(new) == 1:
            toks[new[0].lower()] = {"token": new[0], "pool": "0x" + l["data"][-40:],
                                    "created_block": int(l["blockNumber"], 16), "day": day}
    print(f"  {day}: blocks {start}-{end}, {len(logs)} pools, {len(toks)} tokens, {calls} calls")
    return start, end, list(toks.values()), calls


def main():
    all_tokens, calls_total, spans = [], 0, {}
    for day in DAYS:
        s, e, toks, calls = pools_on(day)
        spans[day] = {"start": s, "end": e}
        all_tokens += toks
        calls_total += calls
    print(f"  {len(all_tokens)} tokens total from {calls_total} RPC calls")

    traded = []
    for i, t in enumerate(all_tokens):
        try:
            pairs = get_json(f"https://api.dexscreener.com/token-pairs/v1/base/{t['token']}")
        except Exception:
            pairs = []
        if isinstance(pairs, list) and pairs:
            dated = [p for p in pairs if p.get("pairCreatedAt")] or pairs
            p = min(dated, key=lambda p: p.get("pairCreatedAt") or 0)
            created = p.get("pairCreatedAt")
            launch_day = datetime.fromtimestamp(created / 1000, timezone.utc).date().isoformat() if created else None
            liq = (p.get("liquidity") or {}).get("usd") or 0
            vol = (p.get("volume") or {}).get("h24") or 0
            traded.append({**t, "symbol": p["baseToken"]["symbol"], "pair": p["pairAddress"],
                           "dex": p.get("dexId"), "quote": p["quoteToken"]["address"],
                           "quote_symbol": p["quoteToken"]["symbol"], "created_ms": created,
                           "launch_day": launch_day, "is_launch_day": launch_day == t["day"],
                           "liq": round(liq), "vol24h": round(vol), "fdv": p.get("fdv")})
        time.sleep(0.3)
        if (i + 1) % 100 == 0:
            print(f"    classified {i + 1}/{len(all_tokens)}")

    launches = [r for r in traded if r["is_launch_day"]]
    print(f"\n  traded at all: {len(traded)}/{len(all_tokens)}   true launches that traded: {len(launches)}")
    for r in sorted(launches, key=lambda r: -(r["fdv"] or 0)):
        print(f"    {r['symbol']:<14} {r['launch_day']} liq ${r['liq']:>9,} vol24h ${r['vol24h']:>8,} "
              f"fdv {r['fdv']}  {r['dex']:<12} {r['token']}")
    save("launches.json", {"spans": spans, "tokens": all_tokens, "traded": traded, "launches": launches})
    save("http_stats_v3.json", STATS.report())


if __name__ == "__main__":
    main()
