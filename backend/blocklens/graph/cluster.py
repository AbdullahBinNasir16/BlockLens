"""Two clustering layers, kept in separate columns on purpose.

**Layer one is provable.** Connected components over funding edges, with
routers, exchanges and burn sinks removed as cut points. Every wallet in one
of these components is joined to the others by a chain of actual transfers.
High precision, low recall: it finds operators who fed their wallets from an
address we can see, and it cannot see through a centralised exchange at all.
This populates `wallet.cluster_id` and `cluster_size`.

**Layer two is inferred.** Community detection over a weighted graph that
combines funding adjacency, co-purchase overlap and behavioural similarity.
These are wallets behaving like one actor without a provable funding link,
and they carry a confidence. This populates `community_id` and
`community_confidence`.

The two never merge into one number. The question "which of these can you
prove and which did you infer" has to have an answer in the schema, because
it is the first question anyone serious will ask.

## Which community algorithm, and why

**Louvain with a fixed seed.** This is a reversal, and the reason is worth
recording rather than hiding.

Greedy modularity (Clauset-Newman-Moore) was chosen first, on the argument
that it is deterministic by construction while Louvain depends on node visit
order and needs a seed — a weaker guarantee than an algorithm with no random
component at all. That argument was sound and it did not survive contact
with the data: CNM did not complete on the real similarity graph (about
15,000 nodes and 96,000 edges) in over ten minutes, because its cost grows
far faster than Louvain's on a graph that dense.

An algorithm that does not finish has no determinism to offer. So: Louvain,
with `SEED` fixed and passed explicitly, which is reproducible for the same
graph and the same seed. `test_graph.py` asserts three consecutive runs
agree, so the guarantee is checked rather than assumed.

The honest shape of the trade: CNM would have given determinism without a
seed; Louvain gives determinism conditional on the seed, and gives it in
seconds. The second is usable and the first is not.
"""
from __future__ import annotations

from dataclasses import dataclass

import networkx as nx

from .funding import AddressBook, load_address_book

# Weights for the layer-two similarity graph. Funding adjacency dominates
# because it is the only component that is evidence on its own; co-purchase
# and behaviour are corroboration, and weighting them equally would let a
# crowd of unrelated buyers outvote an actual transfer.
W_FUNDING = 1.0
W_CO_PURCHASE = 0.4
W_BEHAVIOUR = 0.2

# Below this combined weight an edge is noise and is dropped before
# community detection, which otherwise merges half the graph through
# single coincidental co-purchases.
MIN_COMMUNITY_EDGE_WEIGHT = 0.5

# Louvain is seeded, so a re-run reproduces the same assignments. Fixed in
# the source rather than passed in: a seed that varies per invocation is a
# reproducibility claim nobody can check.
SEED = 20261013


@dataclass
class Clustering:
    cluster_of: dict[str, int]
    size_of: dict[str, int]
    components: list[set[str]]

    @property
    def n_clusters(self) -> int:
        return len(self.components)

    def distribution(self) -> dict[int, int]:
        """size -> how many clusters have that size."""
        out: dict[int, int] = {}
        for c in self.components:
            out[len(c)] = out.get(len(c), 0) + 1
        return dict(sorted(out.items()))


def funding_components(g: nx.DiGraph, *, book: AddressBook | None = None,
                       min_size: int = 2) -> Clustering:
    """Layer one. Provable common funding, nothing inferred.

    Taken on the *undirected* view: A and B funded by the same address are
    in one cluster even though no edge runs between them, which is the whole
    point. Infrastructure is removed first, so a router cannot act as the
    bridge that joins two unrelated operators.
    """
    book = book or load_address_book()
    h = nx.Graph()
    for src, dst, data in g.edges(data=True):
        if data.get("kind") != "funding":
            continue
        if src in book.excluded or dst in book.excluded:
            continue
        h.add_edge(src, dst)

    components = [c for c in nx.connected_components(h) if len(c) >= min_size]
    components.sort(key=len, reverse=True)

    cluster_of: dict[str, int] = {}
    size_of: dict[str, int] = {}
    for i, comp in enumerate(components, start=1):
        for node in comp:
            cluster_of[node] = i
            size_of[node] = len(comp)
    return Clustering(cluster_of=cluster_of, size_of=size_of, components=components)


def similarity_graph(g: nx.DiGraph, *,
                     behaviour: dict[tuple[str, str], float] | None = None,
                     min_weight: float = MIN_COMMUNITY_EDGE_WEIGHT) -> nx.Graph:
    """The weighted graph layer two runs on.

    Three sources combined, each contributing on its own scale, and the
    weights are declared constants rather than tuned until the answer looked
    good. If they are ever tuned, the co-movement lift is what has to
    justify it.
    """
    sim = nx.Graph()
    for src, dst, data in g.edges(data=True):
        if data.get("kind") != "funding":
            continue
        w = sim.get_edge_data(src, dst, {}).get("weight", 0.0)
        sim.add_edge(src, dst, weight=w + W_FUNDING)

    co: nx.Graph = g.graph.get("co_purchase") or nx.Graph()
    for src, dst, data in co.edges(data=True):
        # Normalised by token count so one pair that bought twenty tokens
        # together does not score twenty times a pair that bought one.
        strength = min(1.0, float(data.get("weight", 0.0)) / max(1, data.get("tokens", 1)))
        prev = sim.get_edge_data(src, dst, {}).get("weight", 0.0)
        sim.add_edge(src, dst, weight=prev + W_CO_PURCHASE * strength)

    for (a, b), score in (behaviour or {}).items():
        prev = sim.get_edge_data(a, b, {}).get("weight", 0.0)
        sim.add_edge(a, b, weight=prev + W_BEHAVIOUR * float(score))

    thin = [(a, b) for a, b, d in sim.edges(data=True)
            if d.get("weight", 0.0) < min_weight]
    sim.remove_edges_from(thin)
    sim.remove_nodes_from([n for n in list(sim.nodes) if sim.degree(n) == 0])
    return sim


def communities(sim: nx.Graph, *, min_size: int = 2) -> Clustering:
    """Layer two. Seeded Louvain — see the module docstring.

    Confidence is the community's internal edge density: a community whose
    members are all connected to each other is a stronger claim than a
    chain, at the same size.
    """
    if sim.number_of_edges() == 0:
        return Clustering(cluster_of={}, size_of={}, components=[])

    found = nx.community.louvain_communities(sim, weight="weight", seed=SEED)
    comps = [set(c) for c in found if len(c) >= min_size]
    comps.sort(key=len, reverse=True)

    cluster_of: dict[str, int] = {}
    size_of: dict[str, int] = {}
    for i, comp in enumerate(comps, start=1):
        for node in comp:
            cluster_of[node] = i
            size_of[node] = len(comp)
    return Clustering(cluster_of=cluster_of, size_of=size_of, components=comps)


def confidence(sim: nx.Graph, members: set[str]) -> float:
    """Internal edge density, 0..1. A clique scores 1, a chain scores low."""
    n = len(members)
    if n < 2:
        return 0.0
    sub = sim.subgraph(members)
    possible = n * (n - 1) / 2
    return min(1.0, sub.number_of_edges() / possible) if possible else 0.0


def insider_links(g: nx.DiGraph, layer1: Clustering, *,
                  deployers: dict[str, str]) -> dict[str, str]:
    """Wallets in the deployer's cluster, or funded by it directly.

    `deployers` maps a deployer address to the token it deployed. Returns
    wallet -> reason, because a bare boolean would be unusable: the
    interface has to be able to say *why* a wallet is flagged, and "insider"
    is a serious thing to assert about an address.
    """
    out: dict[str, str] = {}
    for deployer, token in deployers.items():
        d = deployer.lower()
        cid = layer1.cluster_of.get(d)
        if cid is not None:
            for node, node_cid in layer1.cluster_of.items():
                if node_cid == cid and node != d:
                    out[node] = (f"in the same provable funding cluster "
                                 f"(#{cid}) as the deployer of {token}")
        if d in g:
            for fed in g.successors(d):
                out.setdefault(fed, f"funded directly by the deployer of {token}")
    return out
