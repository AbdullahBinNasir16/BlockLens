"""Backfill: a token's complete first window of on-chain history.

Also holds pool discovery, which is on-chain rather than DexScreener-led.
That is a deviation from the brief and it is deliberate: Part A measured
DexScreener's new-token feeds returning *zero* Base tokens across 60 rows,
and its search surfacing established tokens rather than launches. Base's
launches are visible on-chain or not at all — 3,115 Uniswap V4 pools in a
day, against 39–158 from every V2/V3-style factory combined.

The log scan is filtered to the token's own address, so one `eth_getLogs`
per window yields every transfer. Swaps come free in the same call when the
venue emits them from a dedicated pool address (V2, V3, Aerodrome). Uniswap
V4 is a singleton: every pool on Base emits from one PoolManager, so it
needs its own topic-filtered call — see `backfill_token`.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy.orm import Session

from ..config import CONFIG, Config
from ..store import write
from .budget import Budget, BudgetExhausted
from .evm import (
    QUOTE_TOKENS, STABLE_QUOTES, SWAP_TOPICS, TRANSFER, UNISWAP_V3_FACTORY,
    UNISWAP_V4_POOL_MANAGER, V2_SWAP, V3_POOL_CREATED, V3_SWAP, V4_INITIALIZE, V4_SWAP,
    ZERO_ADDRESS, addr_from_topic, looks_like_address, to_int, to_uint, words,
)
from .sources import RpcSource

DECIMALS_SELECTOR = "0x313ce567"

# Native ETH is currency0 on a great many V4 pools, encoded as the zero
# address. It is a quote asset there, not a nonsense value.
NATIVE_ETH = ZERO_ADDRESS
V4_QUOTES = QUOTE_TOKENS | {NATIVE_ETH}


def _utc(ts: int) -> datetime:
    return datetime.fromtimestamp(ts, timezone.utc)


# --------------------------------------------------------------------------
# discovery
# --------------------------------------------------------------------------

def discover_pools(rpc: RpcSource, *, from_block: int, to_block: int) -> list[dict]:
    """New pools in a block range, from both venue styles.

    Returns candidates only; nothing is written here. Writing is the gate's
    job and discovery has no business knowing about it.

    A V4 candidate carries `pool_id` and no pool address, because it has
    none. A V3 candidate carries the pool address out of the event data.
    """
    found: dict[str, dict] = {}
    span = rpc.log_span

    for address, topic0, dex in (
        (UNISWAP_V4_POOL_MANAGER, V4_INITIALIZE, "uniswap-v4"),
        (UNISWAP_V3_FACTORY, V3_POOL_CREATED, "uniswap-v3"),
    ):
        b = from_block
        while b <= to_block:
            hi = min(b + span - 1, to_block)
            logs = rpc.get_logs(addresses=[address], from_block=b, to_block=hi, topics=[topic0])
            for log in logs:
                cand = _candidate(log, dex)
                if cand and cand["token_address"] not in found:
                    found[cand["token_address"]] = cand
            b = hi + 1
    return list(found.values())


def _candidate(log: dict, dex: str) -> dict | None:
    """One pool-creation log to one candidate token, or nothing.

    The asset positions are read from each event's declared layout, not
    sniffed by shape. Shape-sniffing was tried first and was wrong: V3's
    third indexed field is the fee, a uint24, and a fee of 3000 has the same
    24 leading zero-nibbles as an address, so it passed for one.

        V3  PoolCreated(token0 idx, token1 idx, fee idx, tickSpacing, pool)
        V4  Initialize(id idx, currency0 idx, currency1 idx, fee,
                       tickSpacing, hooks, sqrtPriceX96, tick)
    """
    topics = log.get("topics") or []
    need = 4 if dex == "uniswap-v4" else 3
    if len(topics) < need:
        return None

    if dex == "uniswap-v4":
        assets = [addr_from_topic(topics[2]), addr_from_topic(topics[3])]
        pool_id, pair_address = topics[1], None
        quotes = V4_QUOTES          # native ETH is a quote asset on V4
    else:
        assets = [addr_from_topic(topics[1]), addr_from_topic(topics[2])]
        # V3 PoolCreated ends its data with the new pool's address.
        data = words(log.get("data") or "0x")
        pool_id, pair_address = None, ("0x" + data[-1][-40:]) if data else None
        quotes = QUOTE_TOKENS

    if not all(looks_like_address("0x" + "0" * 24 + a[2:]) for a in assets):
        return None

    novel = [a for a in assets if a not in quotes]
    quote = [a for a in assets if a in quotes]
    # Exactly one side must be unknown to us. Two unknowns is a pool between
    # two things we cannot price; none is a pool between two majors.
    if len(novel) != 1 or len(quote) != 1:
        return None

    return {
        "token_address": novel[0],
        "quote_address": quote[0],
        "pair_address": pair_address,
        "pool_id": pool_id,
        "dex": dex,
        "created_block": int(log["blockNumber"], 16),
    }


# --------------------------------------------------------------------------
# decoding
# --------------------------------------------------------------------------

def token_decimals(rpc: RpcSource, token: str, default: int = 18) -> int:
    try:
        res = rpc.call("eth_call", [{"to": token, "data": DECIMALS_SELECTOR}, "latest"])
        return int(res, 16) if res and res != "0x" else default
    except Exception:  # noqa: BLE001 - a token that will not answer decimals is not fatal
        return default


def _decode_transfer(log: dict, chain: str, decimals: int) -> dict | None:
    topics = log.get("topics") or []
    if len(topics) < 3:
        return None          # non-standard tokens that leave the parties unindexed
    data = log.get("data") or "0x"
    raw = to_uint(words(data)[0]) if data not in ("0x", "") else 0
    return {
        "chain": chain,
        "tx_hash": log["transactionHash"],
        "log_index": int(log["logIndex"], 16),
        "block_number": int(log["blockNumber"], 16),
        "token_address": log["address"].lower(),
        "from_address": addr_from_topic(topics[1]),
        "to_address": addr_from_topic(topics[2]),
        "raw_value": raw,
        "value_normalised": raw / (10 ** decimals),
        "provenance": "live",
    }


def _decode_swap(log: dict, *, chain: str, token: str, quote: str, token_dec: int,
                 quote_dec: int, pair_key: str, counterparty: str,
                 transfers_by_tx: dict[str, list[dict]]) -> dict | None:
    """Direction and token amount come from the token's own transfers, not
    from the event's sign convention, which differs across V2, V3 and V4.
    The quote amount comes from the event, because the quote token's
    transfers are not in our filter — WETH chain-wide would swamp it.

    `pair_key` identifies the pool in our own tables; `counterparty` is the
    address that actually holds the funds on-chain. They are the same thing
    everywhere except V4, where one PoolManager holds every pool.
    """
    topic0 = (log.get("topics") or [""])[0]
    w = words(log.get("data") or "0x")
    token0_is_token = token.lower() < quote.lower()

    quote_amount = None
    if topic0 == V2_SWAP and len(w) >= 4:
        in0, in1, out0, out1 = to_uint(w[0]), to_uint(w[1]), to_uint(w[2]), to_uint(w[3])
        raw = (in1 + out1) if token0_is_token else (in0 + out0)
        quote_amount = raw / (10 ** quote_dec)
    elif topic0 in (V3_SWAP, V4_SWAP) and len(w) >= 2:
        a0, a1 = to_int(w[0]), to_int(w[1])
        quote_amount = abs(a1 if token0_is_token else a0) / (10 ** quote_dec)

    side, token_amount = None, None
    for tr in transfers_by_tx.get(log["transactionHash"], []):
        if tr["from_address"] == counterparty:
            side, token_amount = "buy", tr["value_normalised"]
            break
        if tr["to_address"] == counterparty:
            side, token_amount = "sell", tr["value_normalised"]
            break
    if side is None:
        # Nothing in this tx moved the token to or from the pool, so fall
        # back to the event's own sign. Recorded either way: an unmatched
        # swap is still a trade, and dropping it would bias the volume.
        if topic0 in (V3_SWAP, V4_SWAP) and len(w) >= 2:
            delta = to_int(w[0]) if token0_is_token else to_int(w[1])
            side = "buy" if delta < 0 else "sell"
            token_amount = abs(delta) / (10 ** token_dec)
        elif topic0 == V2_SWAP and len(w) >= 4:
            out = to_uint(w[2]) if token0_is_token else to_uint(w[3])
            side = "buy" if out > 0 else "sell"
            token_amount = (out / (10 ** token_dec)) or None
        else:
            return None

    # A price is only honest when the quote *is* dollars. A WETH-quoted
    # price needs the historical ETH price, which Phase 1 does not have.
    price_usd = None
    if quote in STABLE_QUOTES and token_amount:
        price_usd = (quote_amount or 0.0) / token_amount

    return {
        "chain": chain,
        "tx_hash": log["transactionHash"],
        "log_index": int(log["logIndex"], 16),
        "block_number": int(log["blockNumber"], 16),
        "pair_address": pair_key,
        # Part A proved the transfer counterparty is the router, not the
        # trader, on aggregator routes. Left null rather than wrong; filling
        # it needs a receipt or trace per transaction, which is Phase 3.
        "wallet_address": None,
        "side": side,
        "token_amount": token_amount,
        "quote_amount": quote_amount,
        "price_usd": price_usd,
        "provenance": "live",
    }


def _timestamps(rpc: RpcSource, logs: Sequence[dict], blocks: set[int]) -> dict[int, int]:
    """Block number to unix seconds, as cheaply as the endpoint allows.

    The default gateway returns `blockTimestamp` on every log, which makes
    this free. Measured before relying on it: without that field, a token
    active in 500 distinct blocks would cost 500 `eth_getBlockByNumber`
    calls on top of its 44 log calls — an order of magnitude more than the
    backfill itself, and enough to change what the free tier can do.

    Not every endpoint sends it, so anything still missing is fetched.
    """
    out: dict[int, int] = {}
    for log in logs:
        raw = log.get("blockTimestamp")
        if raw:
            out[int(log["blockNumber"], 16)] = int(raw, 16)
    missing = blocks - out.keys()
    if missing:
        out.update(rpc.block_timestamps(sorted(missing)))
    return out


def _wallets_from(transfers: Sequence[dict], *, chain: str, pair: str) -> list[dict]:
    """Addresses seen holding the token, with the earliest moment we saw one.

    `funding_source` stays 'unknown', as the brief requires for Phase 1.
    Part A measured why: attribution costs more than the transfers do.
    """
    first: dict[str, dict] = {}
    for r in transfers:
        for addr in (r["from_address"], r["to_address"]):
            if addr in (ZERO_ADDRESS, pair, UNISWAP_V4_POOL_MANAGER):
                continue
            prev = first.get(addr)
            if prev is None or r["block_number"] < prev["first_seen_block"]:
                first[addr] = {
                    "address": addr,
                    "chain": chain,
                    "first_seen_block": r["block_number"],
                    "first_seen_ts": r["block_ts"],
                    "funding_source": "unknown",
                    "funded_by_address": None,
                    "provenance": "live",
                }
    return list(first.values())


# --------------------------------------------------------------------------
# backfill
# --------------------------------------------------------------------------

# How many windows a probe samples across the feature window, and where.
# Four points, at the start and then spread through the day.
PROBE_FRACTIONS = (0.0, 0.25, 0.5, 0.75)


def probe_activity(rpc: RpcSource, *, token_address: str, start_block: int,
                   pair_address: str | None = None, pool_id: str | None = None,
                   config: Config = CONFIG) -> dict:
    """Did this token ever trade? Four calls instead of forty-four.

    Backfilling a token costs ~44 calls, and on this chain roughly 86% of
    discovered tokens never trade - they are pool spam, and Phase 2 excludes
    them anyway. Paying the full cost to find that out is what made a
    900-token expansion a five-hour job.

    **What counts as trading.** Transfers whose *sender is the pool*: tokens
    leaving a pool to an address is a buy, and it is the one signal that
    survives any routing (Part A proved `swap.wallet_address` is the router
    on aggregator routes). Counting transfers in general does not work - a
    mint from the zero address and the deployer's liquidity add are both
    transfers, and a pool that only ever saw those never traded. An earlier
    version counted every transfer and summed across windows, so four lone
    mints added up to "active"; a test caught it.

    **The bias this introduces, stated rather than hidden.** Four samples of
    1,000 blocks cover 4,000 of 43,200, so about 9% of the window is
    observed. A token whose entire trading history falls between the samples
    is missed and never enters the dataset. That is adequate for a token
    with sustained volume and genuinely lossy for one brief burst, so the
    probe is a cost control for dataset *expansion* and not a definition of
    what counts as a launch: it is opt-in (`--probe`), and the token set
    built without it is unaffected.
    """
    token_address = token_address.lower()
    holder = (UNISWAP_V4_POOL_MANAGER if pool_id
              else (pair_address or "")).lower()
    span = int(config.feature_window_hours * 3600 / config.block_seconds)
    buys, windows_read = 0, 0

    for frac in PROBE_FRACTIONS:
        at = start_block + int(span * frac)
        hi = at + rpc.log_span - 1
        try:
            logs = rpc.get_logs(addresses=[token_address], from_block=at, to_block=hi)
        except BudgetExhausted:
            raise
        except Exception:  # noqa: BLE001 - a refused window is not a verdict
            continue
        windows_read += 1
        for log in logs:
            topics = log.get("topics") or []
            if len(topics) < 3 or topics[0] != TRANSFER:
                continue
            if holder and addr_from_topic(topics[1]) == holder:
                buys += 1
        if buys:
            # One buy is enough: this pool traded. Stop paying.
            break

    return {"token": token_address, "buys_seen": buys,
            "windows_read": windows_read, "active": buys > 0}


def backfill_token(session: Session, rpc: RpcSource, budget: Budget, *, chain: str,
                   token_address: str, quote_address: str, start_block: int,
                   pair_address: str | None = None, pool_id: str | None = None,
                   config: Config = CONFIG, decimals: int | None = None,
                   quote_decimals: int = 18, end_block: int | None = None) -> dict:
    """Every transfer, and every swap we can get, across the first window.

    Resumes from a checkpoint, writes through the gate with `as_of_ts` set
    to the end of the window, and reports what it spent.

    Costs one call per window for transfers, plus one more per window only
    for a V4 pool, where swaps live behind a topic filter on the singleton.
    """
    token_address = token_address.lower()
    quote_address = quote_address.lower()
    # On V4 the pool has no address of its own: funds and events both sit
    # with one PoolManager, so that is the counterparty a transfer shows.
    # It cannot be the pool's key, though — every V4 pool would collide on
    # it — so the pool id is what identifies the pool in our tables.
    pair_key = (pair_address or pool_id or "").lower()
    counterparty = (pair_address or (UNISWAP_V4_POOL_MANAGER if pool_id else "")).lower()

    stop_block = end_block if end_block is not None else start_block + config.blocks_per_window
    cp = write.get_checkpoint(session, chain=chain, token_address=token_address)
    if cp is not None and cp.done:
        return {"token": token_address, "skipped": "already complete", "calls": 0,
                "transfers": 0, "swaps": 0, "wallets": 0, "complete": True}
    cursor = cp.next_block if cp is not None else start_block

    # The end of the window is the moment the gate is told we know about.
    end_ts = int(rpc.get_block(stop_block)["timestamp"], 16)
    as_of_ts = _utc(end_ts)
    if decimals is None:
        decimals = token_decimals(rpc, token_address)

    span = rpc.log_span
    calls_at_start = budget.requests
    totals = {"transfers": 0, "swaps": 0, "wallets": 0}
    stopped = None

    while cursor <= stop_block:
        hi = min(cursor + span - 1, stop_block)
        try:
            # Addresses: the token always; the pool too when it has its own
            # address, which makes its swaps free. Never the V4 singleton —
            # unfiltered it would return every V4 swap on the chain.
            addresses = [token_address] if pool_id else [token_address, counterparty]
            logs = rpc.get_logs(addresses=[a for a in addresses if a],
                                from_block=cursor, to_block=hi)
            # The V4 swap scan is a second call, so it is only worth making
            # when the token moved at all in this window. A swap of this
            # token cannot exist in a window where the token did not move,
            # and most new pools never trade: that check halves the cost of
            # a V4 backfill without giving up a single row.
            if pool_id and any((l.get("topics") or [""])[0] == TRANSFER for l in logs):
                logs = logs + rpc.get_logs(addresses=[UNISWAP_V4_POOL_MANAGER],
                                           from_block=cursor, to_block=hi,
                                           topics=[V4_SWAP, pool_id])
        except BudgetExhausted:
            stopped = "budget"
            break

        transfers, swap_logs = [], []
        for log in logs:
            emitter = log["address"].lower()
            topic0 = (log.get("topics") or [""])[0]
            if emitter == token_address and topic0 == TRANSFER:
                row = _decode_transfer(log, chain, decimals)
                if row:
                    transfers.append(row)
            elif topic0 in SWAP_TOPICS:
                swap_logs.append(log)

        if transfers or swap_logs:
            blocks = {r["block_number"] for r in transfers}
            blocks |= {int(l["blockNumber"], 16) for l in swap_logs}
            ts_of = _timestamps(rpc, logs, blocks)

            by_tx: dict[str, list[dict]] = {}
            for r in transfers:
                r["block_ts"] = _utc(ts_of.get(r["block_number"], end_ts))
                by_tx.setdefault(r["tx_hash"], []).append(r)

            swaps = []
            for log in swap_logs:
                row = _decode_swap(log, chain=chain, token=token_address,
                                   quote=quote_address, token_dec=decimals,
                                   quote_dec=quote_decimals, pair_key=pair_key,
                                   counterparty=counterparty, transfers_by_tx=by_tx)
                if row:
                    row["block_ts"] = _utc(ts_of.get(row["block_number"], end_ts))
                    swaps.append(row)

            wallets = _wallets_from(transfers, chain=chain, pair=counterparty)

            totals["transfers"] += write.write_transfers(session, transfers, as_of_ts=as_of_ts).total
            totals["swaps"] += write.write_swaps(session, swaps, as_of_ts=as_of_ts).total
            totals["wallets"] += write.write_wallets(session, wallets, as_of_ts=as_of_ts).total

        cursor = hi + 1
        write.save_checkpoint(session, chain=chain, token_address=token_address,
                              from_block=start_block, to_block=stop_block,
                              next_block=cursor, as_of_ts=as_of_ts,
                              done=cursor > stop_block)
        session.commit()

    return {
        "token": token_address,
        "transfers": totals["transfers"],
        "swaps": totals["swaps"],
        "wallets": totals["wallets"],
        "calls": budget.requests - calls_at_start,
        "complete": cursor > stop_block,
        "stopped": stopped,
        "from_block": start_block,
        "to_block": stop_block,
        "as_of_ts": as_of_ts,
    }
