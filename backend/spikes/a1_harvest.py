"""A1, step three: harvest Base pairs from DexScreener search and classify.

DexScreener's profile and boost feeds carried no Base tokens at all, so
discovery goes through search instead: many short queries, keep every Base
pair, then classify by age and by what is left in the pool today.
"""
import json, time
from datetime import datetime, timezone
from _http import STATS, get_json, save

NOW_MS = datetime.now(timezone.utc).timestamp() * 1000
QUERIES = ["WETH", "USDC", "base", "cat", "dog", "ai", "moon", "pepe", "clanker",
           "virtuals", "degen", "toshi", "brett", "higher", "mog", "sol", "eth",
           "inu", "coin", "token", "trump", "doge", "meme", "bot", "agent"]


def main():
    seen = {}
    for q in QUERIES:
        try:
            d = get_json(f"https://api.dexscreener.com/latest/dex/search?q={q}")
        except Exception as e:  # noqa: BLE001
            print(f"  ! {q}: {e}")
            continue
        for p in d.get("pairs") or []:
            if p.get("chainId") == "base" and p.get("pairCreatedAt"):
                seen[p["pairAddress"]] = p
        time.sleep(1.05)   # 60/min documented
    print(f"  distinct Base pairs: {len(seen)}")

    rows = []
    for p in seen.values():
        liq = (p.get("liquidity") or {}).get("usd") or 0
        vol = (p.get("volume") or {}).get("h24") or 0
        txns = (p.get("txns") or {}).get("h24") or {}
        rows.append({
            "symbol": p["baseToken"]["symbol"],
            "name": p["baseToken"].get("name"),
            "token": p["baseToken"]["address"],
            "pair": p["pairAddress"],
            "dex": p.get("dexId"),
            "quote_symbol": p["quoteToken"]["symbol"],
            "quote": p["quoteToken"]["address"],
            "created_ms": p["pairCreatedAt"],
            "created_utc": datetime.fromtimestamp(p["pairCreatedAt"] / 1000, timezone.utc).isoformat(),
            "age_days": round((NOW_MS - p["pairCreatedAt"]) / 86_400_000, 1),
            "liq_usd": round(liq),
            "vol24h": round(vol),
            "txns24h": (txns.get("buys") or 0) + (txns.get("sells") or 0),
            "fdv": p.get("fdv"),
        })

    recent = [r for r in rows if r["age_days"] <= 183]
    dead = sorted([r for r in recent if r["liq_usd"] < 4000 and r["vol24h"] < 400],
                  key=lambda r: -(r["fdv"] or 0))
    live = sorted([r for r in recent if r["liq_usd"] > 100_000 and r["vol24h"] > 25_000],
                  key=lambda r: -r["liq_usd"])

    print(f"  launched < 6 months: {len(recent)}   dead: {len(dead)}   live: {len(live)}")
    for r in dead:
        print(f"    DEAD {r['symbol']:<12} {r['age_days']:>6}d  liq ${r['liq_usd']:<8} vol24h ${r['vol24h']:<7} "
              f"fdv {r['fdv']}  {r['dex']}  {r['token']}")
    for r in live[:5]:
        print(f"    LIVE {r['symbol']:<12} {r['age_days']:>6}d  liq ${r['liq_usd']:<8} vol24h ${r['vol24h']:<7} "
              f"{r['dex']}  {r['token']}")

    save("harvest.json", {"all": rows, "recent": recent, "dead": dead, "live": live})
    save("http_stats_harvest.json", STATS.report())


if __name__ == "__main__":
    main()
