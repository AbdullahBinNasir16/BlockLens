"""The wallet screener's corpus, from the real store (Phase 7).

The front end's query logic (`src/lib/screener.ts`) derives every figure
from positions, so the backend only has to return positions: what each
wallet spent, took out and still held in each token. Built from the labelled
research population (tokens with a `token_label`, WETH- or ETH-quoted), over
the window the store holds for each (its first 24 hours).

* **The trader** is recovered from token transfers inside each swap
  transaction, exactly as the model's features do (`token_features.py`):
  `swap.wallet_address` is never filled, because on an aggregator route the
  pool's counterparty is the router, not the wallet.
* **Money is in USD**, converted trade by trade at that day's ETH close
  (GeckoTerminal's daily candles for the deepest WETH/USDC pool on Base,
  `market.eth_usd_daily`). The store holds ETH amounts; the screener's
  checks are in USD, so the conversion is made once, here, at the trade's
  own date, never at a single assumed rate.
* **Built once in the background** and written to `data/screener_corpus.json`
  (it takes tens of seconds); served from memory after that.
"""
from __future__ import annotations

import json
import logging
import threading
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

from ..config import CONFIG
from ..model import token_features as tf

log = logging.getLogger("blocklens.screener")

CHAIN = "base"
ETH_QUOTES = ("0x4200000000000000000000000000000000000006", "0x0000000000000000000000000000000000000000")
CACHE = Path(__file__).resolve().parents[2] / "data" / "screener_corpus.json"
FUNDING = {"fresh", "cex", "bridge", "cluster", "unknown"}
WINDOW_MS = 24 * 3600 * 1000           # FEATURE_WINDOW_HOURS: what the store holds per launch

_lock = threading.Lock()
_state: dict = {"doc": None, "building": False, "error": None}


def _ms(dt) -> float:
    return dt.timestamp() * 1000


def _px(prices: dict[str, float], dt: datetime) -> float:
    """The ETH close on `dt`'s day, or the nearest earlier day held."""
    day = dt.astimezone(timezone.utc).date().isoformat()
    if day in prices:
        return prices[day]
    earlier = [d for d in prices if d <= day]
    if not earlier:
        raise ValueError(f"no ETH price at or before {day}")
    return prices[max(earlier)]


def build(s: Session, prices: dict[str, float] | None = None) -> dict:
    t0 = time.perf_counter()
    if prices is None:
        from .market import eth_usd_daily
        prices = eth_usd_daily()
    ctx = tf.Context(s, CHAIN)
    tokens = s.execute(text("""
        select ts.token_address, ts.pool_key, ts.dex, p.created_ts, l.label,
               coalesce(t.symbol, ''), coalesce(t.name, '')
        from token_sample ts
        join token_label l on l.chain = ts.chain and l.token_address = ts.token_address
        join pair p on p.chain = ts.chain and lower(p.address) = lower(ts.pool_key)
        left join token t on t.chain = ts.chain and t.address = ts.token_address
        where ts.chain = :c and p.quote_token = any(:q)
          and ts.sampling_stratum in ('random', 'train_case', 'train_control', 'survivor_enum')
    """), {"c": CHAIN, "q": list(ETH_QUOTES)}).all()

    positions: dict[str, list[dict]] = defaultdict(list)
    meta = []
    for token, pool, dex, created_ts, label, symbol, name in tokens:
        holder = tf.PM if dex == "uniswap-v4" else pool
        swaps = s.execute(text("""
            select tx_hash, block_ts, side, token_amount, quote_amount
            from swap where chain = :c and pair_address = :p order by block_number, log_index
        """), {"c": CHAIN, "p": pool}).all()
        if not swaps:
            continue
        quote_of: dict[str, float] = defaultdict(float)
        ts_of: dict[str, datetime] = {}
        for tx, ts, side, ta, qa in swaps:
            quote_of[tx] += float(qa or 0)
            ts_of.setdefault(tx, ts)
        tr = s.execute(text("""
            select tx_hash, from_address, to_address, value_normalised
            from transfer where chain = :c and token_address = :t and tx_hash = any(:x)
            order by block_number, log_index
        """), {"c": CHAIN, "t": token, "x": list(quote_of)}).all()

        # one trade per (tx, wallet, side): a routed swap moves tokens more than once
        trades: dict[tuple[str, str, str], float] = {}
        for tx, fr, to, v in tr:
            via = fr == holder or fr in ctx.pools or fr in ctx.infra
            back = to == holder or to in ctx.pools or to in ctx.infra
            if via and ctx.is_wallet(to):
                trades[(tx, to, "buy")] = trades.get((tx, to, "buy"), 0.0) + float(v or 0)
            elif back and ctx.is_wallet(fr):
                trades[(tx, fr, "sell")] = trades.get((tx, fr, "sell"), 0.0) + float(v or 0)

        by_wallet: dict[str, list[tuple[datetime, str, float, float]]] = defaultdict(list)
        for (tx, w, side), amount in trades.items():
            # (time, side, tokens, USD at that day's ETH close)
            by_wallet[w].append((ts_of[tx], side, amount, quote_of[tx] * _px(prices, ts_of[tx])))
        # Holdings are valued at the last trade's own price, quote per token in
        # transfer units, so spent and held are in the same units. (The swap
        # table's token amounts are not always in the transfers' units.)
        last = max(((ts_of[tx], quote_of[tx] / a) for (tx, _, _), a in trades.items() if a > 0),
                   default=(None, 0.0))
        last_price = last[1] * (_px(prices, last[0]) if last[0] else 0.0)   # USD per token
        start = created_ts or min(ts_of.values())
        for w, rows in by_wallet.items():
            rows.sort()
            buys = [r for r in rows if r[1] == "buy"]
            sells = [r for r in rows if r[1] == "sell"]
            if not buys:
                continue            # sold without a stored buy: not a position we can value
            bought = sum(r[2] for r in buys)
            sold = min(bought, sum(r[2] for r in sells))
            first_px = buys[0][3] / buys[0][2] if buys[0][2] else 0.0
            positions[w].append({
                "projectId": token, "chain": "base",
                "firstBuy": _ms(buys[0][0]),
                "lastSell": _ms(sells[-1][0]) if sells and sold >= bought * 0.999 else None,
                "buys": len(buys), "sells": len(sells),
                "invested": round(sum(r[3] for r in buys), 2),
                "soldFraction": round(sold / bought, 6) if bought else 0.0,
                "proceeds": round(sum(r[3] for r in sells), 2),
                "remainingValue": round(max(0.0, bought - sold) * last_price, 2)
                if label != "RUG" else 0.0,
                "entryDelay": max(0.0, _ms(buys[0][0]) - _ms(start)),
                "averagedDown": any(r[2] and r[3] / r[2] < first_px for r in buys[1:]),
                "soldFirstPump": bool(sells and sells[0][2] and first_px
                                      and sells[0][3] / sells[0][2] >= 2 * first_px),
                "wentToZero": label == "RUG",
                "honeypot": False,
                # the store holds each launch's first 24 hours: an open
                # position is "still held when the record stops"
                "observedUntil": _ms(start) + WINDOW_MS,
            })
        meta.append({"address": token, "symbol": symbol, "name": name,
                     "launchedAt": _ms(start), "wallets": len(by_wallet)})

    facts = {}
    addrs = list(positions)
    for i in range(0, len(addrs), 5000):
        for a, first, fund, size, insider in s.execute(text("""
            select address, first_seen_ts, funding_source, cluster_size, insider_linked
            from wallet where chain = :c and address = any(:a)
        """), {"c": CHAIN, "a": addrs[i:i + 5000]}).all():
            facts[a] = (first, fund, size, insider)
    wallets = []
    for a, ps in positions.items():
        first, fund, size, insider = facts.get(a, (None, "unknown", None, None))
        wallets.append({
            "address": a,
            "firstSeen": _ms(first) if first else min(p["firstBuy"] for p in ps),
            "fundingSource": fund if fund in FUNDING else "unknown",
            "clusterSize": int(size or 1),
            "smartMoney": False,            # no defended definition exists; never guessed
            "insiderLinked": bool(insider),
            "positions": ps,
        })
    log.info(json.dumps({"event": "screener_built", "tokens": len(meta), "wallets": len(wallets),
                         "seconds": round(time.perf_counter() - t0, 1)}))
    return {"provenance": "live", "asOf": datetime.now(timezone.utc).isoformat(), "unit": "USD",
            "tokens": sorted(meta, key=lambda m: -m["wallets"]), "wallets": wallets}


def _build_in_background(factory) -> None:
    try:
        with factory()() as s:
            doc = build(s)
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        CACHE.write_text(json.dumps(doc), encoding="utf8")
        with _lock:
            _state.update(doc=doc, error=None)
    except Exception as e:  # noqa: BLE001 - reported on the route, never crashes the API
        log.exception("screener corpus build failed")
        with _lock:
            _state["error"] = f"{type(e).__name__}: {str(e)[:200]}"
    finally:
        with _lock:
            _state["building"] = False


def corpus(factory) -> tuple[dict | None, str]:
    """(doc, status). Starts a build when there is no fresh corpus."""
    with _lock:
        if _state["doc"] is None and CACHE.exists():
            try:
                _state["doc"] = json.loads(CACHE.read_text(encoding="utf8"))
            except ValueError:
                pass
        doc = _state["doc"]
        fresh = CACHE.exists() and time.time() - CACHE.stat().st_mtime < CONFIG.screener_max_age_s
        if (doc is None or not fresh) and not _state["building"]:
            _state["building"] = True
            threading.Thread(target=_build_in_background, args=(factory,), daemon=True,
                             name="screener-build").start()
        status = "ready" if doc else ("failed: " + _state["error"]) if _state["error"] else "building"
    return doc, status
