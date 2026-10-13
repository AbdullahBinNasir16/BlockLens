"""Wallet features, and their propagation across the graph.

## Why propagation is the point

A flat per-wallet rule finds the lazy operator and misses everyone else. The
adversary knows what the heuristics look like: funding twenty wallets from
one address is the obvious pattern and it has already been designed out. So
features computed from a wallet's own behaviour describe a wallet that was
built to look ordinary.

Propagated features describe its *neighbourhood*, which is the thing an
operator cannot make ordinary without giving up the operation. A wallet
funded by an address that also funded fifteen wallets which all dumped
inside an hour carries that signal even when its own trading looks clean.
The cited result — F1 0.93 for two-hop propagated subgraph features against
0.81 for flat clustering on the same data — is the justification for this
module existing, and reproducing the *shape* of that gap is the goal.

## What a feature may see

Everything is computed as of one cutoff and written through the Phase 1
gate. Walking a graph is the easiest place in the system to pull in an event
from after the cutoff: a two-hop neighbour is two joins away from anything,
and one of those joins is very easy to write without a time bound. Every
aggregation here filters on `as_of_ts` before it aggregates, and the gate
refuses the row if anything slipped through.

## Honest limits on the money features

Position values are in **quote units** (usually WETH), not dollars. Base
launches are quoted in ETH and Phase 1 has no historical ETH/USD series, so
a dollar figure would be invented. The price of a buy comes from joining the
wallet's transfer to the pool's `Swap` event in the same transaction, which
is the only way to price a wallet's trade given that `swap.wallet_address`
is null by design (Part A: the counterparty on an aggregator route is the
router, not the trader).
"""
from __future__ import annotations

import statistics
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime

import networkx as nx
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..ingest.evm import UNISWAP_V4_POOL_MANAGER as POOL_MANAGER
from .funding import ZERO

FEATURE_SET_VERSION = "f1-2026-10"

# Two hops, not three. Each hop multiplies the neighbourhood and dilutes the
# signal: at two hops a wallet's features already reach its funder's other
# fundees, which is the relationship the method is built on. At three hops
# on a graph with 5,000-wallet dispersers, nearly every wallet reaches
# nearly every other, and the feature stops distinguishing anything. The
# cited paper also stops at two.
MAX_HOPS = 2

# Aggregations applied to each neighbour feature. Count is separate and
# applies once per hop rather than per feature.
AGGS = ("mean", "max", "std")


@dataclass
class WalletBase:
    """One wallet's own behaviour, before any neighbour is consulted."""
    address: str
    first_seen_ts: float | None = None
    funding_source: str = "unknown"
    funding_amount: float = 0.0
    funded_at_ts: float | None = None

    buy_count: int = 0
    sell_count: int = 0
    tokens_traded: int = 0
    tokens_received: int = 0

    entry_delays: list[float] = field(default_factory=list)
    hold_times: list[float] = field(default_factory=list)
    buy_quote: float = 0.0
    sell_quote: float = 0.0
    tokens_bought: float = 0.0
    tokens_sold: float = 0.0

    averaged_down: bool = False
    sold_first_pump: bool = False
    went_to_zero: bool = False

    def numeric(self) -> dict[str, float]:
        """The numeric view, which is what gets propagated.

        Booleans become 0/1 so a neighbourhood mean reads as "what fraction
        of my neighbours did this", which is the useful form.
        """
        delays = self.entry_delays or [0.0]
        holds = self.hold_times or [0.0]
        realised = self.sell_quote - self.buy_quote
        return {
            "buy_count": float(self.buy_count),
            "sell_count": float(self.sell_count),
            "tokens_traded": float(self.tokens_traded),
            "tokens_received": float(self.tokens_received),
            "entry_delay_min": float(min(delays)),
            "entry_delay_mean": float(sum(delays) / len(delays)),
            "hold_time_mean": float(sum(holds) / len(holds)),
            "hold_time_max": float(max(holds)),
            "buy_quote": float(self.buy_quote),
            "sell_quote": float(self.sell_quote),
            "realised_quote": float(realised),
            "sold_fraction": float(self.tokens_sold / self.tokens_bought)
            if self.tokens_bought else 0.0,
            "funding_amount": float(self.funding_amount),
            "averaged_down": 1.0 if self.averaged_down else 0.0,
            "sold_first_pump": 1.0 if self.sold_first_pump else 0.0,
            "went_to_zero": 1.0 if self.went_to_zero else 0.0,
        }


# The features that get propagated. Keeping this explicit, rather than
# propagating whatever `numeric()` happens to return, means adding a base
# feature does not silently triple the feature count.
PROPAGATED = (
    "buy_count", "sell_count", "tokens_traded", "entry_delay_min",
    "entry_delay_mean", "hold_time_mean", "realised_quote", "sold_fraction",
    "averaged_down", "sold_first_pump", "went_to_zero",
)

# How long after a buy counts as "sold into the first pump".
FIRST_PUMP_SECONDS = 3600
# Holding below this fraction of what was bought counts as having exited.
EXIT_FRACTION = 0.05


def load_wallet_behaviour(session: Session, *, chain: str,
                          as_of_ts: datetime) -> dict[str, WalletBase]:
    """Per-wallet behaviour from the stored transfers, up to the cutoff.

    One query. Every wallet-side trade is a transfer with a pool at the
    other end — the pair contract on V2/V3, the PoolManager on V4 — and the
    price of that trade is the `Swap` event in the same transaction.
    """
    rows = session.execute(text("""
        with pools as (
            select token_address,
                   case when dex = 'uniswap-v4' then :pool_manager else address end
                        as holder,
                   address as pair_key, created_ts
            from pair where chain = :chain
        ),
        trades as (
            select t.to_address as wallet, 'buy' as side, t.token_address,
                   t.block_ts, t.value_normalised as tokens, t.tx_hash,
                   po.created_ts, po.pair_key
            from transfer t
            join pools po on po.token_address = t.token_address
                         and po.holder = t.from_address
            where t.chain = :chain and t.to_address <> :zero
              and t.block_ts <= :as_of
            union all
            select t.from_address as wallet, 'sell' as side, t.token_address,
                   t.block_ts, t.value_normalised as tokens, t.tx_hash,
                   po.created_ts, po.pair_key
            from transfer t
            join pools po on po.token_address = t.token_address
                         and po.holder = t.to_address
            where t.chain = :chain and t.from_address <> :zero
              and t.block_ts <= :as_of
        )
        select tr.wallet, tr.side, tr.token_address, tr.block_ts, tr.tokens,
               tr.created_ts,
               -- price of this trade, from the pool event in the same tx
               case when s.token_amount is not null and s.token_amount <> 0
                    then s.quote_amount / s.token_amount end as price
        from trades tr
        left join swap s on s.chain = :chain and s.tx_hash = tr.tx_hash
                        and s.pair_address = tr.pair_key
        order by tr.wallet, tr.token_address, tr.block_ts
    """), {"chain": chain, "zero": ZERO, "as_of": as_of_ts,
           "pool_manager": POOL_MANAGER}).all()

    wallets: dict[str, WalletBase] = {}
    # (wallet, token) -> the trades, in order, for the per-token flags
    per_token: dict[tuple[str, str], list[tuple]] = defaultdict(list)

    for wallet, side, token, ts, tokens, created, price in rows:
        w = (wallet or "").lower()
        if not w:
            continue
        wb = wallets.setdefault(w, WalletBase(address=w))
        amount = float(tokens or 0.0)
        p = float(price) if price is not None else None

        if side == "buy":
            wb.buy_count += 1
            wb.tokens_bought += amount
            if p:
                wb.buy_quote += amount * p
            if created is not None:
                wb.entry_delays.append(max(0.0, ts.timestamp() - created.timestamp()))
        else:
            wb.sell_count += 1
            wb.tokens_sold += amount
            if p:
                wb.sell_quote += amount * p
        per_token[(w, (token or "").lower())].append(
            (side, ts.timestamp(), amount, p))

    for (w, _token), trades in per_token.items():
        wb = wallets.get(w)
        if wb is None:
            continue
        trades.sort(key=lambda r: r[1])
        buys = [t for t in trades if t[0] == "buy"]
        sells = [t for t in trades if t[0] == "sell"]

        # averaged down: bought again at a lower price than a previous buy
        priced = [t for t in buys if t[3]]
        if any(priced[j][3] < priced[i][3]
               for i in range(len(priced)) for j in range(i + 1, len(priced))):
            wb.averaged_down = True

        # sold into the first pump: a sell within the hour after the first buy
        if buys and sells and sells[0][1] - buys[0][1] <= FIRST_PUMP_SECONDS:
            wb.sold_first_pump = True

        # held to zero: bought, and never sold a meaningful share
        bought = sum(t[2] for t in buys)
        sold = sum(t[2] for t in sells)
        if bought and sold / bought < EXIT_FRACTION:
            wb.went_to_zero = True

        if buys:
            last = sells[-1][1] if sells else None
            if last:
                wb.hold_times.append(max(0.0, last - buys[0][1]))
        wb.tokens_traded += 1

    return wallets


def hops_from(g: nx.DiGraph, targets: set[str], *, limit: int = 6) -> dict[str, int]:
    """Shortest funding distance from any address in `targets`.

    Used for `hops_from_cex`. On this dataset the CEX list is empty, so this
    returns almost nothing — which is the honest consequence of not being
    able to label exchange addresses here, not a bug to hide. The function
    exists and is correct, so populating the list later fills the feature in
    without touching this code.
    """
    if not targets:
        return {}
    rev = g.reverse(copy=False)
    out: dict[str, int] = {}
    frontier = {t for t in targets if t in g}
    depth = 0
    seen = set(frontier)
    while frontier and depth < limit:
        depth += 1
        nxt: set[str] = set()
        for node in frontier:
            for nb in g.successors(node) if node in g else ():
                if nb not in seen:
                    seen.add(nb)
                    out[nb] = depth
                    nxt.add(nb)
        frontier = nxt
    _ = rev
    return out


def neighbours(g: nx.DiGraph, node: str, *, hop: int) -> set[str]:
    """Addresses exactly `hop` funding steps away, in either direction.

    Undirected on purpose: the wallets that matter are a funder's *other*
    fundees, and those are reached by going up an edge and back down it.
    A directed-only walk would never see a sibling, which is the single most
    informative neighbour a wallet has.
    """
    if node not in g:
        return set()
    seen = {node}
    frontier = {node}
    for _ in range(hop):
        nxt: set[str] = set()
        for n in frontier:
            nxt |= set(g.successors(n)) | set(g.predecessors(n))
        frontier = nxt - seen
        seen |= frontier
    return frontier


def _aggregate(values: list[float]) -> dict[str, float]:
    if not values:
        return {"mean": 0.0, "max": 0.0, "std": 0.0}
    return {
        "mean": float(sum(values) / len(values)),
        "max": float(max(values)),
        "std": float(statistics.pstdev(values)) if len(values) > 1 else 0.0,
    }


def features_for(g: nx.DiGraph, wallet: str,
                 base: dict[str, WalletBase], *,
                 cluster_size: int = 0, community_size: int = 0,
                 hops_cex: dict[str, int] | None = None,
                 max_hops: int = MAX_HOPS) -> dict[str, float]:
    """One wallet's full feature vector: its own, then its neighbourhood's.

    Names are systematic — `base_*`, `h1_mean_*`, `h2_max_*` — so the
    feature-importance output in Phase 4 reads without a lookup table.
    """
    own = base.get(wallet) or WalletBase(address=wallet)
    out: dict[str, float] = {f"base_{k}": v for k, v in own.numeric().items()}

    out["base_in_degree"] = float(g.in_degree(wallet)) if wallet in g else 0.0
    out["base_out_degree"] = float(g.out_degree(wallet)) if wallet in g else 0.0
    out["base_cluster_size"] = float(cluster_size)
    out["base_community_size"] = float(community_size)
    out["base_hops_from_cex"] = float((hops_cex or {}).get(wallet, -1))

    for hop in range(1, max_hops + 1):
        nbrs = neighbours(g, wallet, hop=hop)
        out[f"h{hop}_count"] = float(len(nbrs))
        vectors = [base[n].numeric() for n in nbrs if n in base]
        out[f"h{hop}_with_behaviour"] = float(len(vectors))
        for name in PROPAGATED:
            agg = _aggregate([v[name] for v in vectors])
            for how in AGGS:
                out[f"h{hop}_{how}_{name}"] = agg[how]
        # Neighbourhood shape, which is what a funder's fan-out looks like.
        degs = [float(g.degree(n)) for n in nbrs if n in g]
        shape = _aggregate(degs)
        out[f"h{hop}_mean_degree"] = shape["mean"]
        out[f"h{hop}_max_degree"] = shape["max"]
    return out


def feature_names(max_hops: int = MAX_HOPS) -> list[str]:
    """Every name this module produces, for the record and for tests."""
    probe = features_for(nx.DiGraph(), "0xprobe", {}, max_hops=max_hops)
    return sorted(probe)


def rows_for_write(features: dict[str, dict[str, float]], *, chain: str,
                   token_address: str, as_of_ts: datetime,
                   computed_at: datetime) -> list[dict]:
    return [{
        "wallet_address": wallet, "chain": chain,
        "token_address": token_address, "as_of_ts": as_of_ts,
        "feature_set_version": FEATURE_SET_VERSION,
        "n_features": len(vec), "features": vec,
        "computed_at": computed_at, "provenance": "live",
    } for wallet, vec in features.items()]
