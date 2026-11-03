"""Shaping third-party market data into the contract (Phase 7).

Ported from the browser (`src/lib/live/trending.ts`, `token.ts`), which no
longer calls these sources itself. Each source is used for what only it does
well: GeckoTerminal for which pools trend (and maker counts), DexScreener
for fast prices and per-token pairs, GoPlus for holders and the honeypot
flag.
"""
from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Any

from .upstream import UPSTREAM, RateLimited, Upstream, UpstreamError

WINDOWS = ("m5", "h1", "h6", "h24")
DURATION = {"m5": "5m", "h1": "1h", "h6": "6h", "h24": "24h"}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def num(v: Any) -> float:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return 0.0
    return f if f == f and f not in (float("inf"), float("-inf")) else 0.0


def _ms(iso: str | None) -> float:
    if not iso:
        return 0.0
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp() * 1000
    except ValueError:
        return 0.0


# ---- GoPlus: holders and honeypot -----------------------------------------

def _goplus_limited(status: int, body: Any) -> bool:
    # GoPlus answers its limit with HTTP 200 and a code other than 1
    return isinstance(body, dict) and body.get("code") not in (1, None)


def security(token: str, up: Upstream = UPSTREAM) -> dict | None:
    token = token.lower()
    body = up.get("goplus", f"/api/v1/token_security/8453?contract_addresses={token}",
                  up.config.holders_ttl_s, limited=_goplus_limited)
    res = (body or {}).get("result") or {}
    r = res.get(token) or (next(iter(res.values())) if res else None)
    if not r:
        return None
    top = r.get("holders") if isinstance(r.get("holders"), list) else []
    hp = r.get("is_honeypot")
    return {
        "holders": num(r["holder_count"]) if r.get("holder_count") not in (None, "") else None,
        "top10Pct": min(100.0, sum(num(h.get("percent")) for h in top[:10]) * 100) if top else None,
        "honeypot": True if hp == "1" else False if hp == "0" else None,
        "asOf": now_iso(),
    }


def cached_security(token: str, up: Upstream = UPSTREAM) -> dict | None:
    """From the cache only; never spends a call."""
    path = f"/api/v1/token_security/8453?contract_addresses={token.lower()}"
    if up.cached(f"goplus:{path}") is None:
        return None
    try:
        return security(token, up)
    except UpstreamError:
        return None


# ---- DexScreener: one token's pairs ---------------------------------------

def token_market(address: str, up: Upstream = UPSTREAM) -> dict | None:
    a = address.lower()
    rows = up.get("dexscreener", f"/tokens/v1/base/{a}", up.config.market_ttl_s) or []
    if not isinstance(rows, list):
        rows = []
    mine = [p for p in rows if str((p.get("baseToken") or {}).get("address", "")).lower() == a]
    lst = mine or rows
    if not lst:
        return None
    pairs = sorted(({
        "pool": p.get("pairAddress", ""),
        "url": p.get("url") or f"https://dexscreener.com/base/{p.get('pairAddress', '')}",
        "dex": " ".join([x for x in [p.get("dexId"), *(p.get("labels") or [])] if x]),
        "quote": str((p.get("quoteToken") or {}).get("symbol", "")).upper(),
        "price": num(p.get("priceUsd")),
        "change24h": num((p.get("priceChange") or {}).get("h24")),
        "volume24h": num((p.get("volume") or {}).get("h24")),
        "buys24h": num(((p.get("txns") or {}).get("h24") or {}).get("buys")),
        "sells24h": num(((p.get("txns") or {}).get("h24") or {}).get("sells")),
        "liquidity": num((p.get("liquidity") or {}).get("usd")),
        "marketCap": num(p.get("marketCap")),
        "fdv": num(p.get("fdv")),
        "createdAt": num(p.get("pairCreatedAt")),
    } for p in lst), key=lambda x: -x["liquidity"])
    head = lst[0]
    base = head.get("baseToken") if mine else head.get("quoteToken")
    base = base or {}
    logo = next(((p.get("info") or {}).get("imageUrl") for p in lst if (p.get("info") or {}).get("imageUrl")), None)
    site = next((((p.get("info") or {}).get("websites") or [{}])[0].get("url")
                 for p in lst if (p.get("info") or {}).get("websites")), None)
    out = {"address": a, "name": base.get("name") or "Unknown token",
           "symbol": str(base.get("symbol") or "").upper(), "pairs": pairs, "asOf": now_iso()}
    if logo:
        out["logo"] = logo
    if site:
        out["website"] = site
    return out


# ---- the trending list ----------------------------------------------------

def _rank(window: str, pages: int, up: Upstream) -> list[dict]:
    out: list[dict] = []
    seen: set[str] = set()
    for page in range(1, pages + 1):
        try:
            res = up.get("geckoterminal",
                         f"/networks/base/trending_pools?include=base_token,quote_token,dex"
                         f"&duration={DURATION[window]}&page={page}", up.config.trending_ttl_s)
        except UpstreamError:
            if out:
                break           # a later page failing still leaves a usable list
            raise
        inc = {x["id"]: x.get("attributes", {}) for x in res.get("included", []) if "id" in x}
        for p in res.get("data", []):
            a = p.get("attributes", {})
            rel = p.get("relationships", {})
            base_id = ((rel.get("base_token") or {}).get("data") or {}).get("id", "")
            quote_id = ((rel.get("quote_token") or {}).get("data") or {}).get("id", "")
            dex_id = ((rel.get("dex") or {}).get("data") or {}).get("id", "")
            base, quote = inc.get(base_id, {}), inc.get(quote_id, {})
            token = str(base.get("address") or base_id.replace("base_", "")).lower()
            if not token or token in seen:
                continue        # one row per token: its highest-ranked pool
            seen.add(token)
            tx = a.get("transactions") or {}
            name = a.get("name") or ""
            img = base.get("image_url")
            row = {
                "rank": len(out) + 1,
                "pool": a.get("address", ""),
                "url": f"https://dexscreener.com/base/{a.get('address', '')}",
                "dex": inc.get(dex_id, {}).get("name") or dex_id,
                "token": token,
                "name": base.get("name") or name,
                "symbol": str(base.get("symbol") or name.split(" / ")[0]).upper(),
                "quote": str(quote.get("symbol") or (name.split(" / ")[1].split(" ")[0]
                                                    if " / " in name else "")).upper(),
                "price": num(a.get("base_token_price_usd")),
                "change": {w: num((a.get("price_change_percentage") or {}).get(w)) for w in WINDOWS},
                "volume": {w: num((a.get("volume_usd") or {}).get(w)) for w in WINDOWS},
                "buys": {w: num((tx.get(w) or {}).get("buys")) for w in WINDOWS},
                "sells": {w: num((tx.get(w) or {}).get("sells")) for w in WINDOWS},
                "makers": {w: (num(tx[w].get("buyers")) + num(tx[w].get("sellers"))) if tx.get(w) else None
                           for w in WINDOWS},
                "liquidity": num(a.get("reserve_in_usd")),
                "marketCap": num(a.get("market_cap_usd")) or num(a.get("fdv_usd")),
                "fdv": num(a.get("fdv_usd")),
                "createdAt": _ms(a.get("pool_created_at")),
                "holders": None,
            }
            if img and img != "missing.png":
                row["logo"] = img
            out.append(row)
    return out


def _patch(pools: list[dict], up: Upstream) -> None:
    """DexScreener's faster prices over GeckoTerminal's ranking, in place."""
    ids = [p["pool"] for p in pools if p["pool"]]
    by_pool = {p["pool"].lower(): p for p in pools}
    for i in range(0, len(ids), 30):
        try:
            d = up.get("dexscreener", f"/latest/dex/pairs/base/{','.join(ids[i:i + 30])}",
                       up.config.prices_ttl_s)
        except UpstreamError:
            continue            # a missed tick is fine: the ranking's prices stand
        for x in (d or {}).get("pairs") or []:
            p = by_pool.get(str(x.get("pairAddress", "")).lower())
            if not p:
                continue
            p["price"] = num(x.get("priceUsd")) or p["price"]
            for k, src in (("change", "priceChange"), ("volume", "volume")):
                p[k] = {w: num((x.get(src) or {}).get(w)) for w in WINDOWS}
            p["buys"] = {w: num(((x.get("txns") or {}).get(w) or {}).get("buys")) for w in WINDOWS}
            p["sells"] = {w: num(((x.get("txns") or {}).get(w) or {}).get("sells")) for w in WINDOWS}
            p["liquidity"] = num((x.get("liquidity") or {}).get("usd")) or p["liquidity"]
            p["marketCap"] = num(x.get("marketCap")) or num(x.get("fdv")) or p["marketCap"]
            p["fdv"] = num(x.get("fdv")) or p["fdv"]
            if "logo" not in p and (x.get("info") or {}).get("imageUrl"):
                p["logo"] = x["info"]["imageUrl"]


_ranking: dict[str, tuple[str, list[dict]]] = {}      # key -> (asOf, pools): last good
_holder_lock = threading.Lock()
_holder_queue: list[str] = []


def _fill_holders(up: Upstream) -> None:
    """Background: GoPlus one token at a time, rank order, behind the bucket."""
    while True:
        with _holder_lock:
            if not _holder_queue:
                return
            token = _holder_queue.pop(0)
        try:
            security(token, up)
        except RateLimited:
            with _holder_lock:
                _holder_queue.clear()   # retried on the next request
            return
        except UpstreamError:
            continue


def trending(window: str, pages: int, up: Upstream = UPSTREAM) -> dict:
    key = f"{window}:{pages}"
    stale = False
    try:
        pools = _rank(window, pages, up)
        _ranking[key] = (now_iso(), pools)
    except UpstreamError:
        if key not in _ranking:
            raise
        stale = True
    as_of, pools = _ranking[key]
    pools = [dict(p) for p in pools]
    _patch(pools, up)
    missing = []
    for p in pools:
        p["holders"] = cached_security(p["token"], up)
        if p["holders"] is None:
            missing.append(p["token"])
    if missing:
        with _holder_lock:
            idle = not _holder_queue
            _holder_queue[:] = missing
        if idle:
            threading.Thread(target=_fill_holders, args=(up,), daemon=True).start()
    return {"provenance": "live", "window": window, "asOf": as_of, "stale": stale, "pools": pools}
