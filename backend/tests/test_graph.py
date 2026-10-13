"""The graph's four guarantees.

A funding chain resolves to the right hops and the right component; a router
never creates an edge; a two-hop feature cannot see past its cutoff; and the
same input always produces the same clusters. Each one is a way the module
could be quietly wrong in a way nothing downstream would reveal.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import networkx as nx
import pytest

from blocklens.graph import build as gb
from blocklens.graph import cluster as gc
from blocklens.graph import features as gf
from blocklens.graph import funding as fn
from blocklens.graph import validate as gv
from blocklens.store import write

A = "0x" + "a1" * 20
B = "0x" + "b2" * 20
C = "0x" + "c3" * 20
D = "0x" + "d4" * 20
ROUTER = "0x2626664c2603336e57b271c5c0b26f421741e481"      # SwapRouter02, listed
POOL_MANAGER = "0x498581ff718922c3f8e6a244956af099b2652b2b"
TOKEN = "0x" + "11" * 20
NOW = datetime(2026, 7, 1, tzinfo=timezone.utc)


def edge(src: str, dst: str, *, kind: str = "funding", ts=NOW, **kw) -> dict:
    row = {
        "chain": "base", "kind": kind, "src": src, "dst": dst,
        "token_address": TOKEN, "weight": 1.0, "amount": 1.0,
        "block_number": 1, "ts": ts, "window_seconds": None,
        "funding_source": "cluster", "provenance": "live",
    }
    row.update(kw)
    return row


# ---- the funding chain ---------------------------------------------------

def test_a_funding_chain_resolves_to_one_component_and_the_right_hops():
    """A funds B funds C. All three are one actor's wallets, and the hop
    distances have to reflect the chain rather than the direction."""
    g = gb.build_graph([edge(A, B), edge(B, C)], [])

    layer1 = gc.funding_components(g)
    assert layer1.n_clusters == 1
    assert layer1.components[0] == {A, B, C}
    assert layer1.size_of[A] == 3

    # From B, A and C are both one hop away: the walk is undirected on
    # purpose, because a funder's other fundees are the informative
    # neighbours and a directed walk would never reach them.
    assert gf.neighbours(g, B, hop=1) == {A, C}
    assert gf.neighbours(g, A, hop=1) == {B}
    assert gf.neighbours(g, A, hop=2) == {C}


def test_siblings_are_two_hops_apart_not_unreachable():
    """B and C were both funded by A. They are the pair the whole method
    rests on, and a directed-only walk would never connect them."""
    g = gb.build_graph([edge(A, B), edge(A, C)], [])

    assert gf.neighbours(g, B, hop=2) == {C}
    assert gc.funding_components(g).components[0] == {A, B, C}


def test_an_unrelated_wallet_stays_in_its_own_component():
    g = gb.build_graph([edge(A, B), edge(C, D)], [])
    comps = gc.funding_components(g).components
    assert len(comps) == 2
    assert {frozenset(c) for c in comps} == {frozenset({A, B}), frozenset({C, D})}


# ---- routers must not create edges --------------------------------------

def test_a_listed_router_creates_no_funding_edge():
    """A wallet 'funded by' the Uniswap router is an artefact of how a swap
    settles, not a relationship with anyone."""
    g = gb.build_graph([edge(ROUTER, A), edge(ROUTER, B)], [])

    assert g.number_of_edges() == 0
    assert gc.funding_components(g).n_clusters == 0, \
        "the router joined two unrelated wallets into a cluster"


def test_the_router_list_actually_contains_the_routers_it_claims():
    book = fn.load_address_book()
    assert ROUTER in book.routers
    assert POOL_MANAGER in book.routers
    assert fn.ZERO in book.burn
    assert book.kind(ROUTER) == "router"
    assert ROUTER in book.excluded


def test_a_heavy_funder_is_classified_by_token_spread_not_wallet_count():
    """The distinction that makes the graph non-empty.

    Wallet count alone called the PoolManager and a 5,400-wallet disperser
    the same thing and excluded both, leaving 451 edges from 14,507 wallets.
    Infrastructure serves the whole chain; a disperser serves a few tokens.
    """
    # PoolManager-shaped: many wallets, many tokens.
    assert fn.classify_funder(3366, 219, listed_kind=None) == "infrastructure"
    # Disperser-shaped: many wallets, few tokens.
    assert fn.classify_funder(5400, 5, listed_kind=None) == "disperser"
    assert fn.classify_funder(942, 1, listed_kind=None) == "disperser"
    # Listed infrastructure stays infrastructure whatever its shape.
    assert fn.classify_funder(5400, 5, listed_kind="router") == "infrastructure"
    # An ordinary wallet that funded a couple of others.
    assert fn.classify_funder(3, 1, listed_kind=None) == "ordinary"


# ---- the cutoff ---------------------------------------------------------

def test_the_gate_refuses_an_edge_from_after_the_cutoff(session):
    """A graph walk is the easiest place in the system to pick up next
    week's event: a two-hop neighbour is two joins from anything."""
    rows = [edge(A, B, ts=NOW), edge(B, C, ts=NOW + timedelta(days=1))]
    with pytest.raises(write.LookaheadError):
        write.write_graph_edges(session, rows, as_of_ts=NOW)


def test_the_gate_refuses_a_feature_row_filed_under_the_wrong_cutoff(session):
    row = {
        "wallet_address": A, "chain": "base", "token_address": TOKEN,
        "as_of_ts": NOW + timedelta(hours=1),
        "feature_set_version": gf.FEATURE_SET_VERSION,
        "n_features": 1, "features": {"base_buy_count": 1.0},
        "computed_at": NOW, "provenance": "live",
    }
    with pytest.raises(write.LookaheadError):
        write.write_wallet_features(session, [row], as_of_ts=NOW)


def test_a_two_hop_feature_only_sees_neighbours_inside_the_graph_given():
    """The cutoff is enforced by building the graph from bounded data, so
    the feature code must not reach outside the graph it was handed."""
    g = gb.build_graph([edge(A, B)], [])          # C is not in this graph
    base = {
        A: gf.WalletBase(address=A, buy_count=1),
        B: gf.WalletBase(address=B, buy_count=2),
        C: gf.WalletBase(address=C, buy_count=99),
    }
    vec = gf.features_for(g, A, base)

    assert vec["h1_count"] == 1.0
    assert vec["h1_max_buy_count"] == 2.0, "a neighbour outside the graph leaked in"
    assert vec["h2_count"] == 0.0


# ---- determinism --------------------------------------------------------

def test_the_same_graph_gives_the_same_clusters_every_time():
    """The brief requires a re-run to be identical. Greedy modularity has no
    random component, so this is a property of the algorithm rather than of
    a seed we remembered to set."""
    rows = [edge(A, B), edge(B, C), edge(C, D), edge(A, D)]
    runs = []
    for _ in range(3):
        g = gb.build_graph(rows, [edge(A, C, kind="co_purchase", weight=0.9)])
        sim = gc.similarity_graph(g)
        runs.append((gc.funding_components(g).cluster_of,
                     gc.communities(sim).cluster_of))
    assert runs[0] == runs[1] == runs[2]


def test_the_lift_measurement_is_reproducible():
    """A fixed seed, because the pair sampling is random and a number that
    moves between runs cannot be reported."""
    class FakeBuy:
        def __init__(self, w, t, ts):
            self.wallet, self.token, self.ts = w, t, ts

    base = datetime(2026, 7, 1, tzinfo=timezone.utc)
    buys = [FakeBuy(w, "0xtok", base + timedelta(seconds=i * 10))
            for i, w in enumerate([A, B, C, D] * 3)]
    idx = gv.BuyIndex.build(buys)
    comps = [{A, B, C, D}]

    first = gv.co_movement_lift(idx, comps).as_dict()
    second = gv.co_movement_lift(idx, comps).as_dict()
    assert first == second


# ---- validation machinery -----------------------------------------------

def test_the_positive_control_recovers_a_known_funder_and_its_fundees():
    """Catches implementation bugs, which is a different question from
    whether the method is sound. Both need answering separately."""
    fundees = [f"0x{i:040x}" for i in range(1, 21)]
    g = gv.synthetic_positive_control(A, fundees)

    layer1 = gc.funding_components(g)

    assert layer1.n_clusters == 1
    assert len(layer1.components[0]) == 21, "the funder plus all twenty fundees"
    assert all(w in layer1.components[0] for w in fundees)


def test_the_shuffle_preserves_the_edge_count_but_not_the_pairings():
    g = gb.build_graph([edge(f"0x{i:040x}", f"0x{i + 100:040x}")
                        for i in range(1, 60)], [])
    h = gv.shuffled_funding_graph(g)

    # Degree is preserved so the comparison isolates *who* is connected,
    # not how many edges there are.
    assert abs(h.number_of_edges() - g.number_of_edges()) <= 1
    same = sum(1 for u, v in g.edges if h.has_edge(u, v))
    assert same < g.number_of_edges(), "the shuffle changed nothing"


def test_a_lift_of_one_is_reported_as_a_failure_not_smoothed_over():
    """The brief is explicit: a lift near 1 is a finding, not a number to
    tune. The summary has to say so in words a reader cannot miss."""
    real = gv.LiftResult(cluster_pairs=100, cluster_co_moves=2,
                         random_pairs=100, random_co_moves=2)
    out = gv.summarise(real, real)
    assert "LIFT IS NEAR 1" in out["verdict"]


def test_a_control_that_fails_to_collapse_is_also_reported():
    real = gv.LiftResult(cluster_pairs=100, cluster_co_moves=40,
                         random_pairs=100, random_co_moves=4)
    # A shuffled graph scoring almost as well means the lift is structural.
    ctrl = gv.LiftResult(cluster_pairs=100, cluster_co_moves=38,
                         random_pairs=100, random_co_moves=4)
    out = gv.summarise(real, ctrl)
    assert "CONTROL DID NOT COLLAPSE" in out["verdict"]


# ---- co-purchase edges --------------------------------------------------

def test_co_purchase_pairs_only_wallets_inside_the_window():
    class FakeBuy:
        def __init__(self, w, t, ts):
            self.wallet, self.token, self.ts = w, t, ts

    base = datetime(2026, 7, 1, tzinfo=timezone.utc)
    buys = [FakeBuy(A, "0xtok", base),
            FakeBuy(B, "0xtok", base + timedelta(seconds=60)),
            FakeBuy(C, "0xtok", base + timedelta(hours=5))]

    edges, report = gb.co_purchase_edges(buys, window=300)
    pairs = {(e["src"], e["dst"]) for e in edges}

    assert (min(A, B), max(A, B)) in pairs
    assert not any(C in p for p in pairs), "a buy five hours later was paired"
    assert all(e["window_seconds"] == 300 for e in edges), \
        "the edge must carry the window it was drawn with"


def test_a_crowd_is_capped_rather_than_turned_into_a_clique():
    """Thousands of simultaneous buyers is a crowd, not coordination, and
    pairing them all would produce millions of meaningless edges."""
    class FakeBuy:
        def __init__(self, w, t, ts):
            self.wallet, self.token, self.ts = w, t, ts

    base = datetime(2026, 7, 1, tzinfo=timezone.utc)
    buys = [FakeBuy(f"0x{i:040x}", "0xtok", base + timedelta(seconds=i))
            for i in range(200)]

    edges, report = gb.co_purchase_edges(buys, window=300, max_clique=20)

    assert report["tokens_capped"] == 1
    assert len(edges) < 200 * 199 / 2
