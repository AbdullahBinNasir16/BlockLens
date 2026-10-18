"""Phase 5 features: one row per token, frozen at launch + 5 minutes.

Three rules, each a lesson from the Part A audit:

1. **Nothing after the cutoff.** Every query is bounded by the token's own
   cutoff block. Graph features may read *other* tokens' transfers, but only
   from blocks at or before this token's cutoff. That is history a live
   product would also have.
2. **Nothing aggregated across tokens into a wallet's own row.** Phase 4's
   `base_*` block was a wallet's behaviour over every token it touched, so
   the same vector appeared on both sides of a split. Here a token's timing
   features describe that token's own first five minutes and nothing else.
3. **Tokens, not wallets, are the unit.** With ~1,000 tokens and ~40
   features the token-level question is well posed, and it is the one the
   product asks. Wallet-level questions are answered separately, in Part D.

Groups, so Part C can run its three-way comparison:

* `t_*` — timing and flow inside the token's own window (Phase 4's "entry
  timing", rebuilt per token).
* `g_*` — the wallet graph: Phase 3's funding and co-purchase relationships
  among the token's early buyers, built from transfers up to the cutoff.
* `r_*` — the inputs to the fixed rule checker (`rulecheck.py`); also usable
  as features.
"""
from __future__ import annotations

import json
import math
import statistics
from collections import defaultdict
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

from ..ingest.evm import UNISWAP_V4_POOL_MANAGER as PM
from ..sampling.design import BLOCK_SECONDS, CUTOFF_BLOCKS

ZERO = "0x0000000000000000000000000000000000000000"
FEATURE_SET_VERSION = "t5-2026-10"
# Phase 3's co-purchase window.
CO_PURCHASE_SECONDS = 300
# Senders with more distinct wallet recipients than this, anywhere in the
# store, are infrastructure (dispensers, aggregators), not funders. This is
# Phase 3's degree profiling, computed once over the store.
INFRA_FANOUT = 500


def _known_infra() -> set[str]:
    out = set()
    root = Path(__file__).resolve().parent.parent / "graph" / "known_addresses"
    # launchpad.json: Phase 6, launchpad lockers / fee collectors / routers
    for f in ("routers.json", "cex.json", "bridges.json", "burn.json", "launchpad.json"):
        try:
            doc = json.loads((root / f).read_text(encoding="utf8"))
        except FileNotFoundError:
            continue
        for a in doc.get("addresses", []):
            if isinstance(a, dict) and a.get("address"):
                out.add(a["address"].lower())
    return out


class Context:
    """Store-wide facts computed once: which addresses are pools, which are
    infrastructure."""

    def __init__(self, session: Session, chain: str):
        self.chain = chain
        self.pools = {r[0] for r in session.execute(text("""
            select distinct lower(address) from pair where chain = :c and length(address) = 42
        """), {"c": chain}).all()} | {PM}
        fan = session.execute(text("""
            select from_address from transfer where chain = :c
            group by from_address having count(distinct to_address) > :n
        """), {"c": chain, "n": INFRA_FANOUT}).all()
        self.infra = _known_infra() | {r[0] for r in fan} | {ZERO}

    def is_wallet(self, a: str) -> bool:
        return bool(a) and a not in self.pools and a not in self.infra


def token_row(session: Session, ctx: Context, *, token: str) -> dict | None:
    """Features for one sampled token, or None if it has no pool row."""
    r = session.execute(text("""
        select s.pool_key, s.dex, s.created_block
        from token_sample s where s.chain = :c and s.token_address = :t
    """), {"c": ctx.chain, "t": token}).first()
    if r is None:
        return None
    pool, dex, created = r
    holder = PM if dex == "uniswap-v4" else pool
    cut = created + CUTOFF_BLOCKS

    swaps = session.execute(text("""
        select block_number, tx_hash, side, token_amount, quote_amount
        from swap where chain = :c and pair_address = :p
          and block_number between :lo and :hi
    """), {"c": ctx.chain, "p": pool, "lo": created, "hi": cut}).all()
    swap_tx = {s[1] for s in swaps}

    tr = session.execute(text("""
        select block_number, tx_hash, from_address, to_address, value_normalised
        from transfer where chain = :c and token_address = :t
          and block_number between :lo and :hi
        order by block_number, log_index
    """), {"c": ctx.chain, "t": token, "lo": created, "hi": cut}).all()

    buys: list[tuple[int, str, float]] = []      # (block, wallet, amount)
    sells: list[tuple[int, str, float]] = []
    reserve = peak = 0.0
    minted_to = lp_from = None
    for blk, tx, fr, to, v in tr:
        amount = float(v or 0.0)
        if fr == ZERO and minted_to is None:
            minted_to = to
        if to == holder:
            reserve += amount
            if fr != ZERO and tx not in swap_tx and lp_from is None:
                lp_from = fr
        if fr == holder:
            reserve -= amount
        peak = max(peak, reserve)
        # Inside a swap transaction, tokens reaching a wallet from the pool
        # *or from a router* are a buy, and the reverse a sell. Counting only
        # pool -> wallet missed every routed trade (Part A: on an aggregator
        # route the pool's counterparty is the router) and left 14% of alive
        # tokens with no buyers at all.
        if tx in swap_tx:
            via = fr == holder or fr in ctx.pools or fr in ctx.infra
            back = to == holder or to in ctx.pools or to in ctx.infra
            if via and ctx.is_wallet(to):
                buys.append((blk, to, amount))
            elif back and ctx.is_wallet(fr):
                sells.append((blk, fr, amount))

    buyers = sorted({w for _, w, _ in buys})
    n_buy, n_sell = len(buys), len(sells)
    delays = [(b - created) * BLOCK_SECONDS for b, _, _ in buys]
    bought = defaultdict(float)
    for _, w, a in buys:
        bought[w] += a
    total_bought = sum(bought.values())
    top_share = (max(bought.values()) / total_bought) if total_bought else 0.0
    first_block_buyers = {w for b, w, _ in buys if b - created <= 1}
    deployer_keys = {k for k in (minted_to, lp_from) if k}

    prices = [float(q) / float(t) for _, _, _, t, q in swaps if t and q and float(t) > 0]
    price_drift = (prices[-1] / prices[0]) if len(prices) >= 2 and prices[0] else 1.0

    row: dict = {
        # ---- timing and flow, this token only
        "t_buys": n_buy,
        "t_sells": n_sell,
        "t_unique_buyers": len(buyers),
        "t_unique_sellers": len({w for _, w, _ in sells}),
        "t_sell_buy_ratio": n_sell / n_buy if n_buy else 0.0,
        "t_first_buy_delay_s": min(delays) if delays else CUTOFF_BLOCKS * BLOCK_SECONDS,
        "t_median_buy_delay_s": statistics.median(delays) if delays else CUTOFF_BLOCKS * BLOCK_SECONDS,
        "t_share_buys_first_minute": (sum(1 for x in delays if x <= 60) / n_buy) if n_buy else 0.0,
        "t_same_block_buyers": len(first_block_buyers),
        "t_top_buyer_share": top_share,
        "t_reserve_vs_peak": (reserve / peak) if peak else 1.0,
        "t_log_price_drift": math.log(max(1e-12, price_drift)),
        "t_swaps": len(swaps),
        "t_is_v4": 1.0 if dex == "uniswap-v4" else 0.0,
        # ---- rule-checker inputs
        "r_mint_in_window": 1.0 if minted_to else 0.0,
        "r_deployer_bought": 1.0 if deployer_keys & set(buyers) else 0.0,
    }
    row.update(_graph(session, ctx, buyers=buyers, deployer_keys=deployer_keys,
                      created=created, cut=cut, token=token))
    return row


def _graph(session: Session, ctx: Context, *, buyers: list[str], deployer_keys: set[str],
           created: int, cut: int, token: str) -> dict:
    """Phase 3's relationships among this token's early buyers, as of the cutoff."""
    out = {"g_largest_component_share": 0.0, "g_buyers_funded_by_deployer": 0.0,
           "g_mean_funders_per_buyer": 0.0, "g_dispersers": 0.0,
           "g_buyers_with_funder": 0.0, "g_copurchase_tie_share": 0.0,
           "g_prior_tokens_mean": 0.0}
    if not buyers:
        return out
    B = set(buyers)

    # Funding edges into early buyers: wallet-to-wallet token transfers, any
    # token, at or before this token's cutoff. Pools and infrastructure never
    # count as funders.
    rows = session.execute(text("""
        select from_address, to_address from transfer
        where chain = :c and to_address = any(:b) and block_number <= :cut
    """), {"c": ctx.chain, "b": list(B), "cut": cut}).all()
    funders: dict[str, set[str]] = defaultdict(set)
    for fr, to in rows:
        if ctx.is_wallet(fr) and fr != to:
            funders[to].add(fr)

    parent = {w: w for w in B}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    by_funder: dict[str, list[str]] = defaultdict(list)
    for w, fs in funders.items():
        for f in fs:
            by_funder[f].append(w)
            if f in B:
                parent[find(f)] = find(w)
    for ws in by_funder.values():
        for w in ws[1:]:
            parent[find(ws[0])] = find(w)
    comp = defaultdict(int)
    for w in B:
        comp[find(w)] += 1

    out["g_largest_component_share"] = max(comp.values()) / len(B) if len(B) > 1 else 0.0
    out["g_buyers_funded_by_deployer"] = float(sum(1 for w in B if funders.get(w, set()) & deployer_keys))
    out["g_mean_funders_per_buyer"] = sum(len(funders.get(w, ())) for w in B) / len(B)
    out["g_dispersers"] = float(sum(1 for ws in by_funder.values() if len(ws) >= 3))
    out["g_buyers_with_funder"] = sum(1 for w in B if funders.get(w)) / len(B)

    # Prior co-purchase ties: two early buyers who bought the same *other*
    # token within 300 s of each other, before this token launched.
    prior = session.execute(text("""
        select to_address, token_address, block_number from transfer
        where chain = :c and to_address = any(:b) and block_number < :lo
          and token_address <> :t and from_address = any(:pools)
    """), {"c": ctx.chain, "b": list(B), "lo": created, "t": token,
           "pools": list(ctx.pools)}).all()
    by_tok: dict[str, list[tuple[int, str]]] = defaultdict(list)
    per_wallet_tokens: dict[str, set[str]] = defaultdict(set)
    for w, t, blk in prior:
        by_tok[t].append((blk, w))
        per_wallet_tokens[w].add(t)
    tied: set[str] = set()
    win = CO_PURCHASE_SECONDS // BLOCK_SECONDS
    for evs in by_tok.values():
        evs.sort()
        for i in range(len(evs)):
            j = i + 1
            while j < len(evs) and evs[j][0] - evs[i][0] <= win:
                if evs[j][1] != evs[i][1]:
                    tied.update((evs[i][1], evs[j][1]))
                j += 1
    out["g_copurchase_tie_share"] = len(tied & B) / len(B)
    out["g_prior_tokens_mean"] = sum(len(per_wallet_tokens.get(w, ())) for w in B) / len(B)
    return out


TIMING = ("t_",)
GRAPH = ("g_",)
RULE_INPUTS = ("r_",)


def group(names: list[str], prefixes: tuple[str, ...]) -> list[str]:
    return [n for n in names if n.startswith(prefixes)]
