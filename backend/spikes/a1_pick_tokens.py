"""A1, step one: choose real Base tokens from DexScreener.

Three that launched in the last six months and are now dead, plus one that
is still liquid. Keyless; DexScreener's free tier is 60 req/min, so calls
are spaced. Writes tokens.json for the measurement script.
"""
import time
from datetime import datetime, timezone

from _http import STATS, get_json, save

NOW = datetime.now(timezone.utc)
NOW_MS = NOW.timestamp() * 1000
SIX_MONTHS_MS = 183 * 24 * 3600 * 1000
CHAIN = "base"

DEAD_LIQ = 4_000      # USD in the pool now
DEAD_VOL = 400        # USD traded in 24h now
LIVE_LIQ = 100_000
LIVE_VOL = 25_000


def candidates():
    """Token addresses to inspect: recent profiles and boosted tokens are
    where new launches surface, and most boosted memecoins are dead within
    weeks — which is exactly the population Phase 1 cares about."""
    seen, out = set(), []
    for url in (
        "https://api.dexscreener.com/token-profiles/latest/v1",
        "https://api.dexscreener.com/token-boosts/latest/v1",
        "https://api.dexscreener.com/token-boosts/top/v1",
    ):
        try:
            rows = get_json(url)
        except Exception as e:  # noqa: BLE001
            print(f"  ! {url}: {e}")
            continue
        n = 0
        for r in rows if isinstance(rows, list) else []:
            if r.get("chainId") != CHAIN:
                continue
            a = (r.get("tokenAddress") or "").lower()
            if a and a not in seen:
                seen.add(a)
                out.append(a)
                n += 1
        print(f"  {url.rsplit('/', 2)[-2]}: {n} base tokens")
        time.sleep(1.1)
    return out


def inspect(addr):
    """The token's primary pair: oldest pair is the launch pair."""
    pairs = get_json(f"https://api.dexscreener.com/token-pairs/v1/{CHAIN}/{addr}")
    if not isinstance(pairs, list) or not pairs:
        return None
    dated = [p for p in pairs if p.get("pairCreatedAt")]
    if not dated:
        return None
    p = min(dated, key=lambda p: p["pairCreatedAt"])
    liq = (p.get("liquidity") or {}).get("usd") or 0
    vol = (p.get("volume") or {}).get("h24") or 0
    txns = (p.get("txns") or {}).get("h24") or {}
    created = p["pairCreatedAt"]
    return {
        "token": addr,
        "symbol": (p.get("baseToken") or {}).get("symbol"),
        "name": (p.get("baseToken") or {}).get("name"),
        "pair": p.get("pairAddress"),
        "dex": p.get("dexId"),
        "quote_symbol": (p.get("quoteToken") or {}).get("symbol"),
        "quote_address": (p.get("quoteToken") or {}).get("address"),
        "pair_created_ms": created,
        "pair_created_utc": datetime.fromtimestamp(created / 1000, timezone.utc).isoformat(),
        "age_days": round((NOW_MS - created) / 86_400_000, 1),
        "liquidity_usd_now": round(liq),
        "volume_24h_now": round(vol),
        "txns_24h_now": (txns.get("buys") or 0) + (txns.get("sells") or 0),
        "fdv_now": p.get("fdv"),
    }


def main():
    print("A1: picking Base tokens from DexScreener")
    addrs = candidates()
    print(f"  {len(addrs)} unique Base tokens to inspect")

    rows = []
    for i, a in enumerate(addrs):
        try:
            r = inspect(a)
        except Exception as e:  # noqa: BLE001
            print(f"  ! {a}: {e}")
            r = None
        if r:
            rows.append(r)
        time.sleep(0.25)   # 300/min documented; stay well under
        if (i + 1) % 25 == 0:
            print(f"  inspected {i + 1}/{len(addrs)}")

    recent = [r for r in rows if NOW_MS - r["pair_created_ms"] <= SIX_MONTHS_MS]
    dead = [r for r in recent if r["liquidity_usd_now"] < DEAD_LIQ and r["volume_24h_now"] < DEAD_VOL]
    live = [r for r in recent if r["liquidity_usd_now"] > LIVE_LIQ and r["volume_24h_now"] > LIVE_VOL]

    # A dead token still has to have traded on day one, or it measures nothing.
    # FDV is the only hint of past size left once a pool is drained.
    dead.sort(key=lambda r: -(r["fdv_now"] or 0))
    live.sort(key=lambda r: -r["liquidity_usd_now"])

    print(f"\n  inspected {len(rows)}, launched <6 months: {len(recent)}")
    print(f"  dead candidates: {len(dead)}   live candidates: {len(live)}")
    for r in dead[:8]:
        print(f"    DEAD {r['symbol']:<12} age {r['age_days']:>5}d  liq ${r['liquidity_usd_now']:<8} vol24h ${r['volume_24h_now']:<8} fdv {r['fdv_now']}")
    for r in live[:5]:
        print(f"    LIVE {r['symbol']:<12} age {r['age_days']:>5}d  liq ${r['liquidity_usd_now']:<8} vol24h ${r['volume_24h_now']}")

    save("candidates.json", {"inspected": rows, "dead": dead, "live": live})
    save("http_stats_pick.json", STATS.report())
    print("\n  http:", STATS.report())


if __name__ == "__main__":
    main()
