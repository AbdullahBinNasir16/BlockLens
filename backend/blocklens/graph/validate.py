"""Evidence that the clusters are real, before anything is built on them.

Clustering without ground truth is where a project quietly fools itself: any
algorithm returns groups, and groups look meaningful. These four checks are
the difference between "we clustered the wallets" and "we clustered the
wallets and showed the clusters correspond to something".

1. **Co-movement lift.** Do wallets in one cluster buy the same tokens
   within a short window more often than random pairs from the same token
   set? This needs no external labels, which is why it is the primary check.
2. **Synthetic positive control.** Wallets with a known common funder,
   recovered by the pipeline. Catches implementation bugs, which is a
   different question from whether the method is sound.
3. **Negative control.** Shuffle the funding edges, preserving the degree
   distribution, and measure the lift again. It must collapse. If a
   randomised graph produces a similar lift then the metric is measuring
   something structural about the graph rather than the clustering, and the
   headline number is worthless.
4. **Hand inspection.** The five largest clusters, written up with
   addresses, in `reports/cluster_cases.md`.

The brief is explicit and it is right: if the lift comes out near one, that
is a finding to report, not a number to tune until it improves. A lift near
one would mean either the funding trace does not capture the relationship on
this chain, or the operators here are not using the pattern we assumed.
"""
from __future__ import annotations

import random
from collections import defaultdict
from math import exp, lgamma, log
from dataclasses import dataclass, field

import networkx as nx

# The window two buys must fall inside to count as co-movement. Matches
# build.CO_PURCHASE_WINDOW on purpose: measuring lift at a different window
# from the one the edges were drawn with would be measuring two things.
CO_MOVE_WINDOW = 300
RANDOM_PAIRS = 20_000
SEED = 20261013


@dataclass
class LiftResult:
    cluster_pairs: int = 0
    cluster_co_moves: int = 0
    random_pairs: int = 0
    random_co_moves: int = 0
    note: str = ""

    @property
    def cluster_rate(self) -> float:
        return self.cluster_co_moves / self.cluster_pairs if self.cluster_pairs else 0.0

    @property
    def random_rate(self) -> float:
        return self.random_co_moves / self.random_pairs if self.random_pairs else 0.0

    @property
    def lift(self) -> float:
        """Cluster rate over baseline rate. 1.0 means the clustering found
        nothing; the whole module rests on this being well above 1."""
        r = self.random_rate
        return (self.cluster_rate / r) if r else float("inf") if self.cluster_rate else 0.0

    @property
    def p_value(self) -> float | None:
        """P(at least this many co-moves | baseline rate), exactly.

        A lift is a ratio and a ratio of small counts can look impressive on
        almost no evidence: 12 co-moving pairs out of 155 is a lift of 4.7
        and also only 12 events. The binomial tail says whether that is
        distinguishable from the baseline at all, which is the question a
        reader should be asking and should not have to compute themselves.
        """
        n, k, p = self.cluster_pairs, self.cluster_co_moves, self.random_rate
        if not n or not p or k == 0 or k > n or p >= 1.0:
            return None

        # Summed in log space. The direct form overflowed on the shuffled
        # control, where n is 2,000: comb(2000, i) does not fit in a float
        # long before the probability it is multiplied by makes the term
        # negligible.
        def log_pmf(i: int) -> float:
            return (lgamma(n + 1) - lgamma(i + 1) - lgamma(n - i + 1)
                    + i * log(p) + (n - i) * log(1.0 - p))

        total = 0.0
        for i in range(k, n + 1):
            term = exp(log_pmf(i))
            total += term
            # The tail decays geometrically once past the mode; stopping
            # early keeps a 2,000-term loop from doing pointless work.
            if term < 1e-18 and i > n * p:
                break
        return min(1.0, total)

    def as_dict(self) -> dict:
        return {
            "cluster_pairs": self.cluster_pairs,
            "cluster_co_moves": self.cluster_co_moves,
            "cluster_rate": round(self.cluster_rate, 6),
            "random_pairs": self.random_pairs,
            "random_co_moves": self.random_co_moves,
            "random_rate": round(self.random_rate, 6),
            "lift": round(self.lift, 3) if self.lift != float("inf") else None,
            "expected_co_moves_at_baseline": round(self.cluster_pairs * self.random_rate, 2),
            "p_value": self.p_value,
            "note": self.note,
        }


@dataclass
class BuyIndex:
    """Who bought what, when — indexed for the pair comparisons."""
    by_wallet: dict[str, dict[str, float]] = field(default_factory=dict)
    wallets: list[str] = field(default_factory=list)

    @classmethod
    def build(cls, buys) -> "BuyIndex":
        by_wallet: dict[str, dict[str, float]] = defaultdict(dict)
        for b in buys:
            ts = b.ts.timestamp()
            prev = by_wallet[b.wallet].get(b.token)
            if prev is None or ts < prev:
                by_wallet[b.wallet][b.token] = ts
        return cls(by_wallet=dict(by_wallet), wallets=sorted(by_wallet))

    def co_moves(self, a: str, b: str, *, window: int = CO_MOVE_WINDOW) -> bool:
        """True if the pair bought any token within `window` of each other."""
        ta, tb = self.by_wallet.get(a), self.by_wallet.get(b)
        if not ta or not tb:
            return False
        for token, t_a in ta.items():
            t_b = tb.get(token)
            if t_b is not None and abs(t_a - t_b) <= window:
                return True
        return False


def co_movement_lift(index: BuyIndex, components: list[set[str]], *,
                     window: int = CO_MOVE_WINDOW,
                     random_pairs: int = RANDOM_PAIRS,
                     seed: int = SEED,
                     max_pairs_per_cluster: int = 2_000,
                     note: str = "") -> LiftResult:
    """Co-movement inside clusters against co-movement between random pairs.

    The baseline is drawn from the same wallet population, so it controls for
    the obvious confounder: wallets in this dataset all bought *something*
    in the same few days, and any two of them have a non-trivial chance of
    overlapping by coincidence. Comparing against zero would flatter the
    result; comparing against random pairs from the same population does not.

    Large clusters are sub-sampled rather than compared exhaustively — a
    5,000-wallet component is 12.5M pairs — with a fixed seed so the number
    is reproducible.
    """
    rng = random.Random(seed)
    res = LiftResult(note=note)

    for comp in components:
        members = [w for w in comp if w in index.by_wallet]
        if len(members) < 2:
            continue
        pairs = [(members[i], members[j])
                 for i in range(len(members)) for j in range(i + 1, len(members))]
        if len(pairs) > max_pairs_per_cluster:
            pairs = rng.sample(pairs, max_pairs_per_cluster)
        for a, b in pairs:
            res.cluster_pairs += 1
            if index.co_moves(a, b, window=window):
                res.cluster_co_moves += 1

    pool = index.wallets
    if len(pool) >= 2:
        for _ in range(random_pairs):
            a, b = rng.sample(pool, 2)
            res.random_pairs += 1
            if index.co_moves(a, b, window=window):
                res.random_co_moves += 1
    return res


def shuffled_funding_graph(g: nx.DiGraph, *, seed: int = SEED) -> nx.DiGraph:
    """A degree-preserving shuffle of the funding edges.

    Degree-preserving matters: a shuffle that also destroyed the degree
    distribution would compare the real graph against a graph that is
    different in two ways, and a collapse in lift would not say which one
    mattered. This keeps every node's in- and out-degree and randomises only
    *who is connected to whom*, which is exactly the thing the clustering
    claims to be reading.
    """
    rng = random.Random(seed)
    funding = [(u, v, d) for u, v, d in g.edges(data=True)
               if d.get("kind") == "funding"]
    sources = [u for u, _, _ in funding]
    targets = [v for _, v, _ in funding]
    rng.shuffle(targets)

    h = nx.DiGraph()
    for (u, _, d), v in zip(funding, targets):
        if u == v:
            continue
        h.add_edge(u, v, **d)
    for u in sources:
        h.add_node(u)
    h.graph["co_purchase"] = g.graph.get("co_purchase")
    return h


def synthetic_positive_control(funder: str, wallets: list[str]) -> nx.DiGraph:
    """A graph with one known funder feeding a known set of wallets.

    Built from real addresses out of the dataset rather than invented ones,
    so the test exercises the same code path with the same address shapes.
    The pipeline must put all of them in one component; if it does not, the
    bug is in the implementation and not in the method, and those two
    failures need telling apart.
    """
    g = nx.DiGraph()
    for w in wallets:
        g.add_edge(funder.lower(), w.lower(), kind="funding", weight=1.0,
                   amount=1.0, ts=None, funding_source="cluster")
    g.graph["co_purchase"] = nx.Graph()
    return g


def summarise(real: LiftResult, shuffled: LiftResult) -> dict:
    """The three numbers the brief wants reported together, plus a verdict.

    The verdict is deliberately blunt. A lift near 1, or a shuffled control
    that does not collapse, means the result does not support what Phase 4
    would want to build on it.
    """
    collapse = (shuffled.lift / real.lift) if real.lift not in (0, float("inf")) else None
    verdict = "inconclusive"
    pv = real.p_value
    if real.lift >= 2 and (collapse is not None and collapse <= 0.5):
        verdict = "clusters co-move far more than chance, and the control collapses"
        if pv is not None and pv > 0.05:
            # A big ratio built on a handful of events is not a result.
            verdict = (f"lift is {real.lift:.1f} and the control collapses, but "
                       f"only {real.cluster_co_moves} pairs co-moved out of "
                       f"{real.cluster_pairs} (p={pv:.3f}): UNDERPOWERED, and "
                       f"the ratio should not be quoted on its own")
    elif real.lift < 1.25:
        verdict = ("LIFT IS NEAR 1: the clustering is not finding co-movement. "
                   "Report this rather than tuning thresholds.")
    elif collapse is not None and collapse > 0.75:
        verdict = ("CONTROL DID NOT COLLAPSE: the lift is structural, not a "
                   "property of the clustering. The headline number is not usable.")
    return {
        "real": real.as_dict(),
        "shuffled_control": shuffled.as_dict(),
        "control_collapse_ratio": round(collapse, 3) if collapse is not None else None,
        "verdict": verdict,
    }
