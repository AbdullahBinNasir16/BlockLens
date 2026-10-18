"""Phase 5 sampling design: windows, the screen, the population, families.

The argument for every choice here is in `reports/sampling_design.md`. In
short:

* **Population.** Uniswap V3/V4 pools on Base launched 2026-01-20 to
  2026-07-19 that are *alive at the cutoff*: at least one swap in the first
  `CUTOFF_MINUTES`, at least one more after it, and the pool's token reserve
  not already below 10% of its running peak at the cutoff. Phase 5, Part A
  showed that a window long enough for a rug to happen inside it measures
  the outcome, so the question is asked of tokens still alive when it is
  asked.
* **Strata.** `random`: uniform 1,000-block windows across the whole period,
  outcome-blind; the only stratum at the true prevalence. `train`: separate
  uniform windows before `SPLIT_DATE`, labelled until the class targets
  fill. `survivor_enum`: pools enumerated because they trade today, the only
  practical source of SURVIVED examples at a ~2% base rate.
* **Time.** Training strata launch before `SPLIT_DATE`. The random cohort
  is split at the same date: before it calibrates, after it evaluates. So
  every headline number is out of time as well as out of sample.
* **Families.** Phase 4's positive class was one operation. Tokens are
  grouped into operator families before labelling, training strata are
  capped per family, and no family appears on both sides of the split.
"""
from __future__ import annotations

import random
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import text
from sqlalchemy.orm import Session

from ..ingest import chain as chain_ingest
from ..ingest.evm import (
    UNISWAP_V3_FACTORY, UNISWAP_V4_POOL_MANAGER, V3_POOL_CREATED, V3_SWAP,
    V4_INITIALIZE, V4_SWAP, words,
)
from ..ingest.sources import RpcSource

SEED = 20261018
PERIOD_START = datetime(2026, 1, 20, tzinfo=timezone.utc)
PERIOD_END = datetime(2026, 7, 19, tzinfo=timezone.utc)
SPLIT_DATE = datetime(2026, 4, 20, tzinfo=timezone.utc)

CUTOFF_MINUTES = 5
BLOCK_SECONDS = 2
CUTOFF_BLOCKS = CUTOFF_MINUTES * 60 // BLOCK_SECONDS          # 150
WINDOW_BLOCKS = 1000                                           # ~33 minutes
SCREEN_AFTER_BLOCKS = 1000          # "still trading" is looked for here
ALIVE_AFTER_MINUTES = 60            # final check, from stored swaps
RESERVE_FLOOR = 0.10                # Phase 2's 90% drop, at the cutoff

TARGETS = {
    "random": 500,                  # alive tokens, the evaluation cohort
    "RUG": 400, "FAILED": 300, "SURVIVED": 300,   # training strata
}
FAMILY_CAP = 3
# An address seen as deployer/LP/early buyer on tokens spread over more
# than this many days is infrastructure (a launchpad, router, or sniper
# bot), not an operator, and does not join families.
HUB_SPAN_DAYS = 7
SHARED_BUYERS_TO_LINK = 2
LINK_WITHIN_HOURS = 24

# sqrt-price bounds of Uniswap V3/V4. A pool initialised at either is
# untradeable; v2 labels it NEVER_LAUNCHED anyway, and the screen drops it
# before a single call is spent on it.
MIN_SQRT = 4295128739
MAX_SQRT = 1461446703485210103287273052203988822378723970342


# ---- windows ---------------------------------------------------------------

@dataclass
class Window:
    id: str
    stratum: str
    round: int
    week: int
    start_ts: datetime
    start_block: int = 0

    @property
    def end_block(self) -> int:
        return self.start_block + WINDOW_BLOCKS - 1


def weeks() -> list[tuple[datetime, datetime]]:
    out, t = [], PERIOD_START
    while t < PERIOD_END:
        out.append((t, min(PERIOD_END, t + timedelta(days=7))))
        t += timedelta(days=7)
    return out


def draw(stratum: str, round_: int) -> list[Window]:
    """One uniformly placed window per week, deterministic in (stratum,
    round, week). Training windows only come from weeks that end before the
    split date."""
    out = []
    span = WINDOW_BLOCKS * BLOCK_SECONDS
    for w, (a, b) in enumerate(weeks()):
        if stratum == "train" and b > SPLIT_DATE:
            continue
        rng = random.Random(f"{SEED}:{stratum}:{round_}:{w}")
        secs = (b - a).total_seconds() - span
        start = a + timedelta(seconds=rng.uniform(0, max(0.0, secs)))
        out.append(Window(id=f"{stratum}:r{round_}:w{w:02d}", stratum=stratum,
                          round=round_, week=w, start_ts=start))
    return out


class Clock:
    """Block <-> time on a chain with exactly two-second blocks, anchored once
    on the head and checked against one real block per run."""

    def __init__(self, rpc: RpcSource):
        head = rpc.block_number()
        self.head = head
        self.head_ts = int(rpc.get_block(head)["timestamp"], 16)

    def block_at(self, ts: datetime) -> int:
        return self.head - int((self.head_ts - ts.timestamp()) // BLOCK_SECONDS)

    def ts_of(self, block: int) -> datetime:
        return datetime.fromtimestamp(self.head_ts - (self.head - block) * BLOCK_SECONDS,
                                      timezone.utc)

    def check(self, rpc: RpcSource, block: int) -> int:
        real = int(rpc.get_block(block)["timestamp"], 16)
        return real - int(self.ts_of(block).timestamp())


# ---- discovery and the screen -------------------------------------------------

def discover(rpc: RpcSource, w: Window, to_block: int | None = None) -> list[dict]:
    """Every pool created in the window, with V4's initial sqrt price.
    `to_block` caps the window, for live use near the chain head."""
    found: dict[str, dict] = {}
    end = min(w.end_block, to_block) if to_block is not None else w.end_block
    for address, topic0, dex in ((UNISWAP_V4_POOL_MANAGER, V4_INITIALIZE, "uniswap-v4"),
                                 (UNISWAP_V3_FACTORY, V3_POOL_CREATED, "uniswap-v3")):
        logs = rpc.get_logs(addresses=[address], from_block=w.start_block,
                            to_block=end, topics=[topic0])
        for log in logs:
            c = chain_ingest._candidate(log, dex)
            if not c or c["token_address"] in found:
                continue
            if dex == "uniswap-v4":
                ws = words(log.get("data") or "0x")
                c["sqrt_price"] = int(ws[3], 16) if len(ws) > 3 else None
            else:
                c["sqrt_price"] = None
            c["pool_key"] = (c.get("pool_id") or c.get("pair_address") or "").lower()
            found[c["token_address"]] = c
    return list(found.values())


def degenerate_start(c: dict) -> bool:
    s = c.get("sqrt_price")
    return s is not None and (s <= MIN_SQRT * 2 or s >= MAX_SQRT // 2)


def screen(rpc: RpcSource, w: Window, cands: list[dict]) -> None:
    """Swaps per pool, by the cutoff and in the 1,000 blocks after it.

    Two filtered queries per 1,000 blocks for the whole window: V4 swaps by
    an OR-list of pool ids, V3 swaps by a list of pool addresses. Adds
    `swaps_by_cutoff` and `swaps_after_cutoff` to each candidate in place.
    """
    hi = w.end_block + CUTOFF_BLOCKS + SCREEN_AFTER_BLOCKS
    v4 = {c["pool_key"]: c for c in cands if c["dex"] == "uniswap-v4" and not degenerate_start(c)}
    v3 = {c["pool_key"]: c for c in cands if c["dex"] == "uniswap-v3"}
    for c in cands:
        c["swaps_by_cutoff"] = 0
        c["swaps_after_cutoff"] = 0
    blocks: dict[str, list[int]] = defaultdict(list)

    b = w.start_block
    while b <= hi:
        top = min(b + rpc.log_span - 1, hi)
        ids = list(v4)
        for i in range(0, len(ids), 60):
            for log in rpc.get_logs(addresses=[UNISWAP_V4_POOL_MANAGER], from_block=b,
                                    to_block=top, topics=[V4_SWAP, ids[i:i + 60]]):
                t = log.get("topics") or []
                if len(t) > 1:
                    blocks[t[1].lower()].append(int(log["blockNumber"], 16))
        addrs = list(v3)
        for i in range(0, len(addrs), 60):
            for log in rpc.get_logs(addresses=addrs[i:i + 60], from_block=b,
                                    to_block=top, topics=[V3_SWAP]):
                blocks[log["address"].lower()].append(int(log["blockNumber"], 16))
        b = top + 1

    for key, c in {**v4, **v3}.items():
        for blk in blocks.get(key, []):
            d = blk - c["created_block"]
            if 0 <= d <= CUTOFF_BLOCKS:
                c["swaps_by_cutoff"] += 1
            elif CUTOFF_BLOCKS < d <= CUTOFF_BLOCKS + SCREEN_AFTER_BLOCKS:
                c["swaps_after_cutoff"] += 1


def passes_screen(c: dict) -> bool:
    return (not degenerate_start(c) and c["swaps_by_cutoff"] > 0
            and c["swaps_after_cutoff"] > 0)


# ---- after backfill: the population decision ----------------------------------

def alive_at_cutoff(session: Session, *, chain: str, token: str) -> tuple[bool, str]:
    """The final, stored-data version of the screen.

    Alive means: a swap at or before the cutoff, another within
    `ALIVE_AFTER_MINUTES` after it, and the pool's token reserve at the
    cutoff still above `RESERVE_FLOOR` of its running peak.
    """
    row = session.execute(text("""
        select p.address, p.dex, p.created_block, t.created_ts
        from token_sample s
        join pair p on p.token_address = s.token_address and p.chain = s.chain
                    and lower(p.address) = s.pool_key
        join token t on t.address = s.token_address and t.chain = s.chain
        where s.chain = :c and s.token_address = :t
    """), {"c": chain, "t": token}).first()
    if row is None:
        return False, "no pool row"
    pool, dex, created, launch = row
    swaps = [b for (b,) in session.execute(text("""
        select block_number from swap where chain = :c and pair_address = :p
    """), {"c": chain, "p": pool}).all()]
    by = sum(1 for b in swaps if 0 <= b - created <= CUTOFF_BLOCKS)
    after = sum(1 for b in swaps
                if CUTOFF_BLOCKS < b - created <= ALIVE_AFTER_MINUTES * 30 + CUTOFF_BLOCKS)
    if not by:
        return False, "no swap by the cutoff"
    if not after:
        return False, "no swap after the cutoff"

    holder = UNISWAP_V4_POOL_MANAGER if dex == "uniswap-v4" else pool
    rows = session.execute(text("""
        select block_number, from_address, to_address, value_normalised from transfer
        where chain = :c and token_address = :t and block_number <= :cut
          and (from_address = :h or to_address = :h)
        order by block_number, log_index
    """), {"c": chain, "t": token, "h": holder, "cut": created + CUTOFF_BLOCKS}).all()
    reserve = peak = 0.0
    for _b, fr, to, v in rows:
        amount = float(v or 0)
        if to == holder:
            reserve += amount
        if fr == holder:
            reserve -= amount
        peak = max(peak, reserve)
    if peak > 0 and reserve <= RESERVE_FLOOR * peak:
        return False, "reserve below the floor at the cutoff"
    return True, ""


# ---- operator families ------------------------------------------------------

def families(session: Session, *, chain: str) -> dict[str, str]:
    """token -> family id, over every alive sampled token.

    Two tokens are one family if they share a deployer key (first mint
    recipient, or first liquidity sender into the pool) or share at least
    `SHARED_BUYERS_TO_LINK` early buyers and launched within
    `LINK_WITHIN_HOURS` of each other. Addresses active across more than
    `HUB_SPAN_DAYS` are infrastructure and never link anything.
    """
    toks = session.execute(text("""
        select s.token_address, s.created_block, s.launch_ts, s.dex, s.pool_key
        from token_sample s where s.chain = :c and s.alive_at_cutoff
    """), {"c": chain}).all()
    info = {t: (blk, ts, dex, key) for t, blk, ts, dex, key in toks}

    keys: dict[str, set[str]] = defaultdict(set)      # token -> deployer keys
    buyers: dict[str, set[str]] = defaultdict(set)    # token -> early buyers
    for t, (blk, _ts, dex, key) in info.items():
        holder = UNISWAP_V4_POOL_MANAGER if dex == "uniswap-v4" else key
        rows = session.execute(text("""
            select from_address, to_address from transfer
            where chain = :c and token_address = :t
              and block_number <= :cut
            order by block_number, log_index
        """), {"c": chain, "t": t, "cut": blk + CUTOFF_BLOCKS}).all()
        minted = lp = None
        for fr, to in rows:
            if minted is None and fr == "0x0000000000000000000000000000000000000000":
                minted = to
            if lp is None and to == holder and fr != "0x0000000000000000000000000000000000000000":
                lp = fr
            if fr == holder and to != holder:
                buyers[t].add(to)
        for k in (minted, lp):
            if k and k != holder:
                keys[t].add(k)

    def spans(m: dict[str, set[str]]) -> dict[str, float]:
        seen: dict[str, list[datetime]] = defaultdict(list)
        for t, addrs in m.items():
            for a in addrs:
                seen[a].append(info[t][1])
        return {a: (max(v) - min(v)).total_seconds() / 86400 for a, v in seen.items()}

    hub = {a for a, d in {**spans(keys), **spans(buyers)}.items() if d > HUB_SPAN_DAYS}

    parent = {t: t for t in info}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)

    by_key: dict[str, list[str]] = defaultdict(list)
    for t, ks in keys.items():
        for k in ks - hub:
            by_key[k].append(t)
    for ts in by_key.values():
        for t in ts[1:]:
            union(ts[0], t)

    by_buyer: dict[str, list[str]] = defaultdict(list)
    for t, bs in buyers.items():
        for b in bs - hub:
            by_buyer[b].append(t)
    shared: dict[tuple[str, str], int] = defaultdict(int)
    for ts in by_buyer.values():
        if len(ts) > 50:
            continue                  # a wallet on 50 launches is a bot
        for i in range(len(ts)):
            for j in range(i + 1, len(ts)):
                a, b = sorted((ts[i], ts[j]))
                shared[(a, b)] += 1
    window = timedelta(hours=LINK_WITHIN_HOURS)
    for (a, b), n in shared.items():
        if n >= SHARED_BUYERS_TO_LINK and abs(info[a][1] - info[b][1]) <= window:
            union(a, b)

    return {t: "fam:" + find(t)[:18] for t in info}
