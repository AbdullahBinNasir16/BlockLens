"""Assemble the graph: nodes, funding edges, co-occurrence edges.

Two edge kinds, never mixed, because they are not the same kind of claim:

* **funding** — A sent B tokens. A relationship between two addresses, and
  the only edge type a provable cluster may be built from.
* **co-occurrence** — A and B bought the same token inside a short window.
  On its own this is a coincidence; thousands of people buy the same launch
  in the same minute. It becomes evidence only in aggregate, and only ever
  feeds the probabilistic layer.

NetworkX, in memory, on purpose. At ~14k wallets and ~60k candidate edges
this fits comfortably and a graph database would be infrastructure bought
for a scale we do not have. If the node count passes a few hundred thousand
that calculation changes, and `stats()` reports the count so the moment is
visible rather than discovered.

## The co-purchase window

`CO_PURCHASE_WINDOW` is 300 seconds. Two reasons, and the second is the one
that matters: the sampling resolution of the launches themselves means the
interesting activity is minutes-scale, and a window much wider than that on
a fresh launch connects everyone to everyone, because in the first hour of a
token nearly every buy is within minutes of another. A window much narrower
than a block or two is measuring block inclusion rather than intent.

The window is stored on every edge it creates, because the edge is
meaningless without it.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime

import networkx as nx
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..ingest.evm import UNISWAP_V4_POOL_MANAGER as POOL_MANAGER
from .funding import ZERO, AddressBook, FundingEdge, load_address_book, pool_addresses

CO_PURCHASE_WINDOW = 300          # seconds
# A token bought by more wallets than this in one window would create a
# clique of millions of edges and say nothing. Capped, and the cap is
# reported rather than silently applied.
MAX_CO_PURCHASE_CLIQUE = 60


@dataclass
class Buy:
    wallet: str
    token: str
    ts: datetime
    amount: float


def load_buys(session: Session, *, chain: str,
              as_of_ts: datetime | None = None) -> list[Buy]:
    """First acquisition of each token by each wallet, from the pool.

    Taken from transfers out of a pool rather than from the `swap` table,
    because Part A proved `swap.wallet_address` is the router on aggregator
    routes and Phase 1 therefore leaves it null. The token leaving the pool
    to an address is the one buy signal that survives any route.

    **The holder is not always the pair.** On Uniswap V4 one PoolManager
    holds every pool's funds, and the `pair` row for a V4 pool is keyed by
    its 32-byte pool id, which never appears as a transfer counterparty. An
    earlier version joined `from_address` to `pair.address` for every venue
    and found 19 buys in the whole dataset instead of tens of thousands,
    because V4 is ~95% of it. The co-movement lift computed on that came out
    at zero, which would have been reported as a finding about the chain
    rather than a bug in one join.
    """
    sql = """
        select distinct on (t.to_address, t.token_address)
               t.to_address, t.token_address, t.block_ts, t.value_normalised
        from transfer t
        join pair p
          on p.token_address = t.token_address and p.chain = t.chain
        where t.chain = :chain
          and t.to_address <> :zero
          and t.from_address = case when p.dex = 'uniswap-v4'
                                    then :pool_manager else p.address end
          {cutoff}
        order by t.to_address, t.token_address, t.block_ts
    """.format(cutoff="and t.block_ts <= :as_of" if as_of_ts else "")
    params = {"chain": chain, "zero": ZERO, "pool_manager": POOL_MANAGER}
    if as_of_ts:
        params["as_of"] = as_of_ts

    rows = session.execute(text(sql), params).all()
    return [Buy(wallet=w.lower(), token=tok.lower(), ts=ts,
                amount=float(amt) if amt is not None else 0.0)
            for w, tok, ts, amt in rows]


def load_market_actions(session: Session, *, chain: str,
                        as_of_ts: datetime | None = None) -> list[Buy]:
    """First *market action* per wallet per token: a buy or a sell.

    The co-movement metric in the brief is defined on buys, and that is
    measured too — but on this dataset buy-only co-movement is computable
    for a small minority of pairs. The provable funding clusters here are
    mostly disperser recipients: tokens were sent to them, so they never
    appear as buyers, and a metric that only sees buyers cannot see them at
    all. The first measurement rested on 13 pairs.

    A sell is a market action in exactly the same sense, and coordinated
    *dumping* is the behaviour this module exists to catch, so widening the
    metric to either direction is a truer test of "behaves like one actor"
    rather than a convenience. Both numbers are reported; neither replaces
    the other.
    """
    sql = """
        select distinct on (w, t.token_address) w, t.token_address, t.block_ts, side
        from (
            select t.*, t.to_address as w, 'buy' as side
            from transfer t join pair p
              on p.token_address = t.token_address and p.chain = t.chain
            where t.chain = :chain and t.to_address <> :zero
              and t.from_address = case when p.dex = 'uniswap-v4'
                                        then :pool_manager else p.address end
            union all
            select t.*, t.from_address as w, 'sell' as side
            from transfer t join pair p
              on p.token_address = t.token_address and p.chain = t.chain
            where t.chain = :chain and t.from_address <> :zero
              and t.to_address = case when p.dex = 'uniswap-v4'
                                      then :pool_manager else p.address end
        ) t
        where true {cutoff}
        order by w, t.token_address, t.block_ts
    """.format(cutoff="and t.block_ts <= :as_of" if as_of_ts else "")
    params = {"chain": chain, "zero": ZERO, "pool_manager": POOL_MANAGER}
    if as_of_ts:
        params["as_of"] = as_of_ts

    rows = session.execute(text(sql), params).all()
    return [Buy(wallet=w.lower(), token=tok.lower(), ts=ts, amount=0.0)
            for w, tok, ts, _side in rows]


def co_purchase_edges(buys: list[Buy], *,
                      window: int = CO_PURCHASE_WINDOW,
                      max_clique: int = MAX_CO_PURCHASE_CLIQUE) -> tuple[list[dict], dict]:
    """Pairs of wallets that bought the same token within `window` seconds.

    A sweep over each token's buys in time order, which is O(n) per token
    plus the pairs actually emitted — not the O(n^2) a naive all-pairs
    comparison would cost on a token with thousands of buyers.
    """
    by_token: dict[str, list[Buy]] = defaultdict(list)
    for b in buys:
        by_token[b.token].append(b)

    edges: dict[tuple[str, str, str], dict] = {}
    capped: list[str] = []
    for token, rows in by_token.items():
        rows.sort(key=lambda b: b.ts)
        start = 0
        for i, b in enumerate(rows):
            while rows[start].ts.timestamp() < b.ts.timestamp() - window:
                start += 1
            group = rows[start:i]
            if len(group) > max_clique:
                # Too many simultaneous buyers for the pairing to mean
                # anything: this is a crowd, not a coordination signal.
                capped.append(token)
                continue
            for other in group:
                if other.wallet == b.wallet:
                    continue
                src, dst = sorted((other.wallet, b.wallet))
                gap = abs(b.ts.timestamp() - other.ts.timestamp())
                key = (src, dst, token)
                prev = edges.get(key)
                # Closer in time is stronger; keep the closest sighting.
                if prev is None or gap < prev["_gap"]:
                    edges[key] = {
                        "src": src, "dst": dst, "token_address": token,
                        "kind": "co_purchase",
                        "weight": 1.0 - (gap / window) if window else 1.0,
                        "amount": None, "block_number": None,
                        "ts": max(b.ts, other.ts),
                        "window_seconds": window, "funding_source": None,
                        "_gap": gap,
                    }

    out = []
    for e in edges.values():
        e.pop("_gap", None)
        e["provenance"] = "live"
        out.append(e)
    return out, {"tokens_capped": len(set(capped)),
                 "max_clique": max_clique, "window_seconds": window}


def funding_edge_rows(edges: list[FundingEdge], *, chain: str) -> list[dict]:
    return [{
        "chain": chain, "kind": "funding", "src": e.funder, "dst": e.wallet,
        "token_address": e.token_address, "weight": 1.0, "amount": e.amount,
        "block_number": e.block_number, "ts": e.ts, "window_seconds": None,
        "funding_source": e.source, "provenance": "live",
    } for e in edges]


def build_graph(funding: list[dict], co_purchase: list[dict], *,
                book: AddressBook | None = None) -> nx.DiGraph:
    """A directed graph of funding, with co-purchase carried alongside.

    Funding is directed (A funded B) because direction is the whole point:
    the funder is upstream. Co-purchase is symmetric and is attached as an
    undirected view so community detection can use it without pretending it
    has a direction it does not have.
    """
    book = book or load_address_book()
    excluded = book.excluded

    g = nx.DiGraph()
    for e in funding:
        if e["src"] in excluded or e["dst"] in excluded:
            continue
        g.add_edge(e["src"], e["dst"], kind="funding", weight=float(e["weight"] or 1.0),
                   amount=e.get("amount"), ts=e.get("ts"),
                   funding_source=e.get("funding_source"))

    co = nx.Graph()
    for e in co_purchase:
        if e["src"] in excluded or e["dst"] in excluded:
            continue
        w = float(e.get("weight") or 0.0)
        if co.has_edge(e["src"], e["dst"]):
            d = co[e["src"]][e["dst"]]
            d["weight"] += w
            d["tokens"] += 1
        else:
            co.add_edge(e["src"], e["dst"], weight=w, tokens=1,
                        window_seconds=e.get("window_seconds"))
    g.graph["co_purchase"] = co
    return g


def stats(g: nx.DiGraph) -> dict:
    co: nx.Graph = g.graph.get("co_purchase") or nx.Graph()
    out = {
        "funding_nodes": g.number_of_nodes(),
        "funding_edges": g.number_of_edges(),
        "co_purchase_nodes": co.number_of_nodes(),
        "co_purchase_edges": co.number_of_edges(),
        "nodes_total": len(set(g.nodes) | set(co.nodes)),
    }
    # The moment in-memory stops being the right call, made visible.
    out["in_memory_still_appropriate"] = out["nodes_total"] < 300_000
    return out
