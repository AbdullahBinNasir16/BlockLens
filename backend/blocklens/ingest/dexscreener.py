"""Market state: what a token is called, and what its pools looked like.

The chain knows a token's address and its transfers. It does not know the
symbol, the liquidity, or the dollar price, and recovering those from
on-chain state alone means reading reserves and pricing the quote asset.
DexScreener gives all of it, keyless, at 60 requests a minute.

Two jobs, deliberately separate:

* `enrich` fills in `token` and `pair` — names, decimals, venues. Idempotent,
  cheap, and batched 30 addresses to a call.
* `snapshot` appends a `pair_snapshot` row **every poll**, even when nothing
  moved. A gap in a time series is indistinguishable from a missing poll
  otherwise, and a flat stretch is itself a fact about the token.

Everything here is `provenance='live'` and `source='dexscreener'`, so a
query can tell a third party's number from one we derived ourselves.
"""
from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Iterable, Sequence

from sqlalchemy.orm import Session

from ..config import CONFIG, Config
from ..store import write
from .sources import DexScreenerSource

BATCH = 30          # the documented maximum for /tokens/v1


def _f(v) -> float | None:
    """DexScreener omits fields rather than nulling them, and sometimes
    sends numbers as strings. Anything unreadable becomes None, never 0.0:
    a zero liquidity and an unknown liquidity are not the same claim."""
    if v is None or v == "":
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    # inf and nan are not quantities. They arrive from overflowing JSON
    # literals and would be rejected by the database anyway, one row at a
    # time, taking the whole batch with them.
    return f if math.isfinite(f) else None


def _i(v) -> int | None:
    f = _f(v)
    return int(f) if f is not None else None


def _token_row(pair: dict, chain: str, *, side: str = "base") -> dict | None:
    t = pair.get(f"{side}Token") or {}
    addr = (t.get("address") or "").lower()
    if not addr:
        return None
    created_ms = pair.get("pairCreatedAt")
    return {
        "address": addr,
        "chain": chain,
        "symbol": (t.get("symbol") or None),
        "name": (t.get("name") or None),
        # DexScreener does not publish decimals; the chain does, and
        # `chain.token_decimals` fills it. Left alone here rather than
        # guessed, so an upsert cannot overwrite a known value with 18.
        "decimals": None,
        "created_block": None,
        "created_ts": datetime.fromtimestamp(created_ms / 1000, timezone.utc) if created_ms else None,
        "creator_address": None,
        "provenance": "live",
    }


def _pair_row(pair: dict, chain: str) -> dict | None:
    addr = (pair.get("pairAddress") or "").lower()
    base = ((pair.get("baseToken") or {}).get("address") or "").lower()
    if not addr or not base:
        return None
    created_ms = pair.get("pairCreatedAt")
    return {
        "address": addr,
        "chain": chain,
        "token_address": base,
        "quote_token": ((pair.get("quoteToken") or {}).get("address") or "").lower() or None,
        "dex": pair.get("dexId"),
        "created_block": None,
        "created_ts": datetime.fromtimestamp(created_ms / 1000, timezone.utc) if created_ms else None,
        "provenance": "live",
    }


def _snapshot_row(pair: dict, chain: str, ts: datetime) -> dict | None:
    addr = (pair.get("pairAddress") or "").lower()
    if not addr:
        return None
    txns = ((pair.get("txns") or {}).get("h24") or {})
    return {
        "pair_address": addr,
        "ts": ts,
        "chain": chain,
        "price_usd": _f(pair.get("priceUsd")),
        "liquidity_usd": _f((pair.get("liquidity") or {}).get("usd")),
        "fdv": _f(pair.get("fdv") or pair.get("marketCap")),
        "volume_24h": _f((pair.get("volume") or {}).get("h24")),
        "txns_buy_24h": _i(txns.get("buys")),
        "txns_sell_24h": _i(txns.get("sells")),
        "source": "dexscreener",
        "provenance": "live",
    }


def _batched(items: Sequence[str], size: int = BATCH) -> Iterable[Sequence[str]]:
    for i in range(0, len(items), size):
        yield items[i:i + size]


def enrich(session: Session, source: DexScreenerSource, addresses: Sequence[str], *,
           chain: str | None = None, config: Config = CONFIG,
           as_of_ts: datetime | None = None, snapshot: bool = True) -> dict:
    """Fill names and venues for a set of token addresses, and snapshot
    their pools while we have the response open.

    `as_of_ts` defaults to now, which is correct here and only here: a poll
    reports the present, so the present is what we knew. Everything with a
    historical window passes its own cutoff.
    """
    chain = chain or config.chain
    now = as_of_ts or datetime.now(timezone.utc)
    wanted = [a.lower() for a in dict.fromkeys(addresses) if a]

    tokens: dict[tuple[str, str], dict] = {}
    pairs: dict[tuple[str, str], dict] = {}
    snaps: dict[tuple[str, datetime], dict] = {}
    seen: set[str] = set()

    for chunk in _batched(wanted):
        for pair in source.tokens_batch(chain, chunk):
            if (pair.get("chainId") or chain) != chain:
                continue
            row = _token_row(pair, chain)
            if row:
                # One token can have many pools; the first row wins and the
                # rest are identical, so there is nothing to reconcile.
                tokens.setdefault((row["address"], chain), row)
                seen.add(row["address"])
            pr = _pair_row(pair, chain)
            if pr:
                pairs.setdefault((pr["address"], chain), pr)
            if snapshot:
                sr = _snapshot_row(pair, chain, now)
                if sr:
                    snaps.setdefault((sr["pair_address"], now), sr)

    res_t = write.write_tokens(session, list(tokens.values()), as_of_ts=now)
    res_p = write.write_pairs(session, list(pairs.values()), as_of_ts=now)
    res_s = write.write_pair_snapshots(session, list(snaps.values()), as_of_ts=now)

    return {
        "asked": len(wanted),
        # A token DexScreener has never indexed is the normal case for a
        # launch minutes old, not an error. Reported so a run can show how
        # much of its discovery the market has caught up with.
        "unknown": sorted(set(wanted) - seen),
        "tokens": res_t.inserted + res_t.updated,
        "tokens_new": res_t.inserted,
        "pairs": res_p.inserted + res_p.updated,
        "snapshots": res_s.inserted,
        "ts": now,
    }


def seed_tokens(session: Session, rows: Sequence[dict], *, chain: str,
                as_of_ts: datetime) -> int:
    """Record tokens straight from on-chain discovery, before DexScreener
    has heard of them. Symbol and name stay null until `enrich` runs.

    The pair row is what makes a token backfillable, so it is written here
    too — a V4 pool is keyed by its pool id, which is the only identifier
    it has (see chain.backfill_token).
    """
    tokens, pairs = [], []
    for r in rows:
        created_ts = r.get("created_ts")
        tokens.append({
            "address": r["token_address"], "chain": chain,
            "symbol": None, "name": None, "decimals": r.get("decimals"),
            "created_block": r.get("created_block"), "created_ts": created_ts,
            "creator_address": None, "provenance": "live",
        })
        key = r.get("pair_address") or r.get("pool_id")
        if key:
            pairs.append({
                "address": key.lower(), "chain": chain,
                "token_address": r["token_address"],
                "quote_token": r.get("quote_address"),
                "dex": r.get("dex"),
                "created_block": r.get("created_block"), "created_ts": created_ts,
                "provenance": "live",
            })
    t = write.write_tokens(session, tokens, as_of_ts=as_of_ts)
    p = write.write_pairs(session, pairs, as_of_ts=as_of_ts)
    return t.inserted + p.inserted
