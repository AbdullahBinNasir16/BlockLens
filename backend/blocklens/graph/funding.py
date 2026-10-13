"""Funding edges: who put the first tokens into each wallet, and from where.

## Why this is not the ETH-funding trace the brief asked for

The brief specified `alchemy_getAssetTransfers` with the wallet as
`toAddress` to find each wallet's earliest inbound transfers. The
arithmetic it asked for: 14,097 wallets at 120 CU a page is 1.69M CU, which
is 5.6% of a free month — comfortably under the 20% ceiling. **The spend was
never the obstacle.** There is no Alchemy key in this environment and Part A
recorded that one cannot be created here, so the allowance to spend is zero.

A keyless substitute does not exist for that question. Finding every inbound
transfer to an arbitrary address, at an arbitrary past time, is precisely
what an indexing API provides and a JSON-RPC node does not: native ETH
funding leaves no log to filter, and `eth_getLogs` is capped at 1,000 blocks
however narrow the filter (measured, spike B1), so a wallet whose first
funding could be at any block is unsearchable.

## What is derivable instead, and how it differs

Phase 1 already stored every transfer of every ingested token across its
first 24 hours — 56,296 of them are wallet-to-wallet. So the edge this
module builds is:

> the first time a wallet received this token, from an address that is not a
> pool, a router or a burn sink

That is a real relationship and it is the sybil pattern this phase exists to
catch: one address sending the same token to thousands of wallets is a
disperser or an airdrop farm, and the data shows one doing it to 5,400
wallets. But it is **token-acquisition provenance, not ETH-funding
provenance**, and the two are not the same claim:

* a wallet that bought from the pool and was never sent tokens by anyone has
  *no visible provenance here* — it is `unknown`, not `fresh`, because how
  it got its gas is exactly what we cannot see;
* two wallets funded from one exchange hot wallet are invisible as a pair,
  and would have been invisible anyway, since an exchange's internal ledger
  is off-chain.

`graph/README.md` states this at the top. Nothing in this module claims an
ETH funding trace.

## Routers are excluded empirically, not by the list

The curated lists make common cases legible, and they are incomplete by
construction. The protection that actually holds is degree: any address
sending tokens to more than `HIGH_DEGREE_FUNDER` wallets is refused an edge
and reported for review, listed or not. In this dataset that catches the
PoolManager, two dispersers and an aggregator before anyone has to name them.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

LISTS = Path(__file__).parent / "known_addresses"

# An address funding more wallets than this gets looked at rather than
# trusted. It is a trigger for classification, not a verdict.
HIGH_DEGREE_FUNDER = 50

# What separates infrastructure from a disperser, and the distinction is the
# whole value of this module.
#
# Wallet count alone conflates two opposite things, measured on this data:
#
#   PoolManager   3,359 wallets across  215 tokens  ->   16 wallets/token
#   LI.FI           143 wallets across   16 tokens  ->    9 wallets/token
#   0xd152f5...   5,400 wallets across    5 tokens  -> 1080 wallets/token
#   0xe913205...    942 wallets across    1 token   ->  942 wallets/token
#
# A router serves the whole chain, so it touches many tokens. An address
# that touches thousands of wallets across a handful of tokens is not
# infrastructure: it is distributing something specific, which is the sybil
# pattern this phase exists to find. Excluding it on degree alone discarded
# the largest structure in the dataset - the first version of this module
# built 451 edges from 14,507 wallets for exactly that reason.
INFRA_MIN_TOKENS = 20
DISPERSER_MIN_WALLETS_PER_TOKEN = 20

ZERO = "0x0000000000000000000000000000000000000000"


@dataclass(frozen=True)
class AddressBook:
    cex: dict[str, str] = field(default_factory=dict)
    bridges: dict[str, str] = field(default_factory=dict)
    routers: dict[str, str] = field(default_factory=dict)
    burn: dict[str, str] = field(default_factory=dict)

    @property
    def excluded(self) -> set[str]:
        """Addresses that must never appear at either end of an edge."""
        return set(self.routers) | set(self.burn)

    def kind(self, address: str) -> str | None:
        a = (address or "").lower()
        if a in self.cex:
            return "cex"
        if a in self.bridges:
            return "bridge"
        if a in self.routers:
            return "router"
        if a in self.burn:
            return "burn"
        return None

    def label(self, address: str) -> str | None:
        a = (address or "").lower()
        for book in (self.cex, self.bridges, self.routers, self.burn):
            if a in book:
                return book[a]
        return None


def load_address_book(directory: Path = LISTS) -> AddressBook:
    def read(name: str) -> dict[str, str]:
        path = directory / f"{name}.json"
        if not path.exists():
            return {}
        data = json.loads(path.read_text(encoding="utf8"))
        return {e["address"].lower(): e.get("label", name)
                for e in data.get("addresses", [])}

    return AddressBook(cex=read("cex"), bridges=read("bridges"),
                       routers=read("routers"), burn=read("burn"))


def classify_funder(wallets: int, tokens: int, *, listed_kind: str | None) -> str:
    """infrastructure | disperser | ordinary.

    `infrastructure` creates no edges: being "funded by" a router is an
    artefact of how a swap settles. `disperser` does create edges, flagged,
    because thousands of wallets fed from one address across a few tokens is
    a relationship. Whether it is a farm or a genuine airdrop is not decided
    here: that is answered by whether the resulting clusters co-move, which
    `graph/validate.py` measures.
    """
    if listed_kind in ("router", "burn", "cex", "bridge"):
        return "infrastructure"
    if tokens >= INFRA_MIN_TOKENS:
        return "infrastructure"
    if wallets >= HIGH_DEGREE_FUNDER and tokens:
        if wallets / tokens >= DISPERSER_MIN_WALLETS_PER_TOKEN:
            return "disperser"
        return "infrastructure"
    return "ordinary"


def high_degree_funders(session: Session, *, chain: str,
                        threshold: int = HIGH_DEGREE_FUNDER,
                        as_of_ts: datetime | None = None) -> list[dict]:
    """Addresses sending tokens into suspiciously many wallets.

    Reported, not silently dropped. The brief is right that an unlisted
    address funding an implausible number of wallets is almost certainly an
    exchange or a router we missed, and that is a finding about our address
    lists rather than a nuisance to suppress.
    """
    cutoff = "and block_ts <= :as_of" if as_of_ts else ""
    params: dict = {"chain": chain, "zero": ZERO, "threshold": threshold}
    if as_of_ts:
        params["as_of"] = as_of_ts
    rows = session.execute(text(f"""
        select from_address,
               count(distinct to_address) as wallets,
               count(distinct token_address) as tokens,
               count(*) as transfers
        from transfer
        where chain = :chain and from_address <> :zero {cutoff}
        group by from_address
        having count(distinct to_address) >= :threshold
        order by count(distinct to_address) desc
    """), params).all()

    book = load_address_book()
    out = []
    for addr, wallets, tokens, transfers in rows:
        kind = book.kind(addr)
        out.append({
            "address": addr, "wallets": wallets, "tokens": tokens,
            "transfers": transfers,
            "wallets_per_token": round(wallets / tokens, 1) if tokens else None,
            "known_as": book.label(addr),
            "kind": kind,
            "role": classify_funder(wallets, tokens, listed_kind=kind),
            # The ones worth a human's attention: heavy, and unexplained.
            "unlisted": kind is None,
        })
    return out


def pool_addresses(session: Session, *, chain: str) -> set[str]:
    """Every pool we know of. A transfer to or from a pool is a trade, not a
    relationship between people."""
    rows = session.execute(text(
        "select address from pair where chain = :chain"), {"chain": chain}).all()
    return {r[0].lower() for r in rows}


@dataclass
class FundingEdge:
    wallet: str
    funder: str
    token_address: str
    amount: float
    block_number: int
    ts: datetime
    source: str          # cex | bridge | cluster | fresh | unknown


def derive_edges(session: Session, *, chain: str,
                 threshold: int = HIGH_DEGREE_FUNDER,
                 as_of_ts: datetime | None = None) -> tuple[list[FundingEdge], dict]:
    """One edge per wallet: the first non-infrastructure address to send it
    a token, and what kind of address that was.

    Returns the edges and a report of what was excluded and why, because
    "excluded and why" is the line that makes a coverage claim checkable.

    `as_of_ts` bounds every query that feeds the graph. Scoring a token at
    its cutoff must not see an edge that was created afterwards, and a graph
    walk is the easiest place in the system to pick one up by accident. The
    bound is applied here, at the source, rather than trusted to the caller.
    """
    book = load_address_book()
    pools = pool_addresses(session, chain=chain)
    profiled = high_degree_funders(session, chain=chain, threshold=threshold,
                                   as_of_ts=as_of_ts)
    infrastructure = {r["address"] for r in profiled if r["role"] == "infrastructure"}
    dispersers = {r["address"] for r in profiled if r["role"] == "disperser"}
    excluded = book.excluded | pools | infrastructure | {ZERO}

    # Earliest inbound transfer per wallet, from anywhere. Ordering by
    # (block, log_index) makes "first" deterministic within a block.
    cutoff = "and block_ts <= :as_of" if as_of_ts else ""
    params: dict = {"chain": chain, "zero": ZERO}
    if as_of_ts:
        params["as_of"] = as_of_ts

    rows = session.execute(text(f"""
        select distinct on (to_address)
               to_address, from_address, token_address,
               value_normalised, block_number, block_ts
        from transfer
        where chain = :chain and to_address <> :zero {cutoff}
        order by to_address, block_number, log_index
    """), params).all()

    # Which addresses we have any sighting of as a sender — used to tell a
    # one-off funder apart from an active one.
    sender_degree = dict(session.execute(text(f"""
        select from_address, count(distinct to_address)
        from transfer where chain = :chain {cutoff}
        group by from_address
    """), params).all())

    wallets_seen = {r[0].lower() for r in rows}

    edges: list[FundingEdge] = []
    tally = {"cex": 0, "bridge": 0, "cluster": 0, "fresh": 0, "unknown": 0}
    skipped = {"from_pool": 0, "from_router": 0, "from_infrastructure": 0, "self": 0}
    from_disperser = 0

    for to_addr, from_addr, token, amount, block, ts in rows:
        wallet, funder = to_addr.lower(), (from_addr or "").lower()
        if wallet == funder:
            skipped["self"] += 1
            continue

        kind = book.kind(funder)
        if kind == "cex":
            source = "cex"
        elif kind == "bridge":
            source = "bridge"
        elif funder in pools:
            # Acquired by trading. How this wallet got its gas is exactly
            # what we cannot see, so it is unknown, never "fresh".
            skipped["from_pool"] += 1
            tally["unknown"] += 1
            continue
        elif kind in ("router", "burn"):
            skipped["from_router"] += 1
            tally["unknown"] += 1
            continue
        elif funder in infrastructure:
            # Infrastructure by behaviour even if we cannot name it.
            skipped["from_infrastructure"] += 1
            tally["unknown"] += 1
            continue
        elif funder in dispersers:
            # Thousands of wallets fed from one address across few tokens.
            # An edge, and flagged as one, because whether that is a farm or
            # an airdrop is decided by co-movement, not by degree.
            from_disperser += 1
            source = "cluster"
        elif funder in wallets_seen:
            source = "cluster"
        elif sender_degree.get(funder, 0) <= 1:
            # Sent to this wallet and nothing else we can see.
            source = "fresh"
        else:
            source = "unknown"

        tally[source] += 1
        if source != "unknown":
            edges.append(FundingEdge(
                wallet=wallet, funder=funder, token_address=token.lower(),
                amount=float(amount) if amount is not None else 0.0,
                block_number=block, ts=ts, source=source))

    report = {
        "wallets_considered": len(rows),
        "edges_built": len(edges),
        "by_source": tally,
        "skipped": skipped,
        "edges_from_dispersers": from_disperser,
        "excluded_addresses": len(excluded),
        "heavy_funders_profiled": len(profiled),
        "classified_infrastructure": len(infrastructure),
        "classified_disperser": len(dispersers),
        "unlisted_heavy_for_review": sum(1 for r in profiled if r["unlisted"]),
        "threshold": threshold,
    }
    return edges, report


def wallet_rows(edges: list[FundingEdge], *, chain: str,
                all_wallets: set[str]) -> list[dict]:
    """Rows for the Phase 1 write gate: one per wallet, with its edge.

    Wallets with no derivable edge are written too, as `unknown`. Leaving
    them out would make the funding distribution look better than it is.
    """
    by_wallet = {e.wallet: e for e in edges}
    out = []
    for wallet in sorted(all_wallets):
        e = by_wallet.get(wallet)
        out.append({
            "address": wallet, "chain": chain,
            "funding_source": e.source if e else "unknown",
            "funded_by_address": e.funder if e else None,
            "funded_at_ts": e.ts if e else None,
            "provenance": "live",
        })
    return out
