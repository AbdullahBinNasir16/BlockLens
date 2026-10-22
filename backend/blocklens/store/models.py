"""The store's shape.

Rules that are not negotiable, and why:

* `provenance` is on every table, as the enum the frontend already uses
  (`Provenance` in src/data/types.ts: 'live' | 'sample'). A row that cannot
  say where it came from is not allowed in.
* `transfer` and `swap` carry natural primary keys — (chain, tx_hash,
  log_index) — so a re-run upserts instead of duplicating. A crashed
  backfill must be safe to restart.
* `block_ts` is stored on every event row, so no time question needs a
  join to a blocks table.
* `wallet.funding_source` uses exactly the frontend's `FundingSource`
  values. Phase 1 leaves it 'unknown'; filling it is Phase 3.
* **No foreign keys**, deliberately. Ingestion order is not guaranteed: a
  backfill decodes a swap on a pool before enrichment has described that
  pool, and a wallet appears the moment it receives a token. A foreign key
  would reject rows that are true, and losing a true row to preserve a
  referential claim is the wrong trade for a research store. The joins are
  written explicitly instead, and `chain` is part of every key so they
  cannot silently cross chains.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger, Boolean, DateTime, Float, Enum, Index, Integer, Numeric, String, Text, text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


# Matches src/data/types.ts — keep the two in step.
PROVENANCE = Enum("live", "sample", name="provenance", create_type=True)
FUNDING_SOURCE = Enum(
    "fresh", "cex", "bridge", "cluster", "unknown", name="funding_source", create_type=True
)
SWAP_SIDE = Enum("buy", "sell", name="swap_side", create_type=True)
RUN_STATUS = Enum(
    "running", "completed", "failed", "stopped_budget", name="run_status", create_type=True
)

# uint256 needs 78 digits, and that bound is exact.
RAW = Numeric(78, 0)

# Everything else is deliberately unconstrained, which is not laziness.
# Numeric(38, 18) and Numeric(38, 12) were tried first and both failed
# against real Base data on the same day they were written:
#
#   * a token minting 10^30 units gives DexScreener an FDV above 10^26,
#     which overflows a precision-38 scale-12 column outright;
#   * a dust memecoin's price is routinely below 10^-12, which that same
#     column silently rounds to zero — the worse of the two failures,
#     because it looks like data.
#
# An unconstrained PostgreSQL numeric holds both ends without rounding. A
# fixed scale would be a claim about magnitudes this project does not get
# to make: it is reading whatever anyone chose to deploy.
NORMALISED = Numeric()
USD = Numeric()


class Token(Base):
    __tablename__ = "token"
    address: Mapped[str] = mapped_column(String(66), primary_key=True)
    chain: Mapped[str] = mapped_column(String(16), primary_key=True)
    symbol: Mapped[str | None] = mapped_column(String(64))
    name: Mapped[str | None] = mapped_column(Text)
    decimals: Mapped[int | None] = mapped_column(Integer)
    created_block: Mapped[int | None] = mapped_column(BigInteger)
    created_ts: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    creator_address: Mapped[str | None] = mapped_column(String(66))
    provenance: Mapped[str] = mapped_column(PROVENANCE, nullable=False)
    first_seen_run_id: Mapped[int | None] = mapped_column(BigInteger)


class Pair(Base):
    __tablename__ = "pair"
    address: Mapped[str] = mapped_column(String(66), primary_key=True)
    chain: Mapped[str] = mapped_column(String(16), primary_key=True)
    token_address: Mapped[str] = mapped_column(String(66), nullable=False)
    quote_token: Mapped[str | None] = mapped_column(String(66))
    dex: Mapped[str | None] = mapped_column(String(64))
    created_block: Mapped[int | None] = mapped_column(BigInteger)
    created_ts: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    provenance: Mapped[str] = mapped_column(PROVENANCE, nullable=False)

    __table_args__ = (Index("ix_pair_token", "chain", "token_address"),)


class PairSnapshot(Base):
    """Market state as observed at `ts`.

    DexScreener does not serve this retroactively, so the poller is the only
    way this history will ever exist. Every day it does not run is a day that
    cannot be recovered.

    Hypertable on `ts` where TimescaleDB is available; see the migration.
    """
    __tablename__ = "pair_snapshot"
    pair_address: Mapped[str] = mapped_column(String(66), primary_key=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    chain: Mapped[str] = mapped_column(String(16), nullable=False)
    price_usd: Mapped[float | None] = mapped_column(USD)
    liquidity_usd: Mapped[float | None] = mapped_column(USD)
    fdv: Mapped[float | None] = mapped_column(USD)
    volume_24h: Mapped[float | None] = mapped_column(USD)
    txns_buy_24h: Mapped[int | None] = mapped_column(Integer)
    txns_sell_24h: Mapped[int | None] = mapped_column(Integer)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    provenance: Mapped[str] = mapped_column(PROVENANCE, nullable=False)


class Transfer(Base):
    __tablename__ = "transfer"
    chain: Mapped[str] = mapped_column(String(16), primary_key=True)
    tx_hash: Mapped[str] = mapped_column(String(66), primary_key=True)
    log_index: Mapped[int] = mapped_column(Integer, primary_key=True)
    block_number: Mapped[int] = mapped_column(BigInteger, nullable=False)
    block_ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    token_address: Mapped[str] = mapped_column(String(66), nullable=False)
    from_address: Mapped[str] = mapped_column(String(66), nullable=False)
    to_address: Mapped[str] = mapped_column(String(66), nullable=False)
    raw_value: Mapped[float] = mapped_column(RAW, nullable=False)
    value_normalised: Mapped[float | None] = mapped_column(NORMALISED)
    provenance: Mapped[str] = mapped_column(PROVENANCE, nullable=False)

    __table_args__ = (
        Index("ix_transfer_token_ts", "chain", "token_address", "block_ts"),
        Index("ix_transfer_block", "chain", "block_number"),
        Index("ix_transfer_to", "chain", "to_address", "block_number"),
    )


class Swap(Base):
    __tablename__ = "swap"
    chain: Mapped[str] = mapped_column(String(16), primary_key=True)
    tx_hash: Mapped[str] = mapped_column(String(66), primary_key=True)
    log_index: Mapped[int] = mapped_column(Integer, primary_key=True)
    block_number: Mapped[int] = mapped_column(BigInteger, nullable=False)
    block_ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    pair_address: Mapped[str] = mapped_column(String(66), nullable=False)
    # The trader. Part A proved this is NOT the transfer counterparty on
    # aggregator routes, so it stays nullable until Phase 2 resolves it.
    wallet_address: Mapped[str | None] = mapped_column(String(66))
    side: Mapped[str] = mapped_column(SWAP_SIDE, nullable=False)
    token_amount: Mapped[float | None] = mapped_column(NORMALISED)
    quote_amount: Mapped[float | None] = mapped_column(NORMALISED)
    price_usd: Mapped[float | None] = mapped_column(USD)
    provenance: Mapped[str] = mapped_column(PROVENANCE, nullable=False)

    __table_args__ = (
        Index("ix_swap_pair_ts", "chain", "pair_address", "block_ts"),
        Index("ix_swap_wallet", "chain", "wallet_address"),
    )


class Wallet(Base):
    __tablename__ = "wallet"
    address: Mapped[str] = mapped_column(String(66), primary_key=True)
    chain: Mapped[str] = mapped_column(String(16), primary_key=True)
    first_seen_block: Mapped[int | None] = mapped_column(BigInteger)
    first_seen_ts: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    funding_source: Mapped[str] = mapped_column(
        FUNDING_SOURCE, nullable=False, server_default=text("'unknown'")
    )
    funded_by_address: Mapped[str | None] = mapped_column(String(66))
    # Phase 3. The edge itself is what the graph needs, not just the category.
    funded_at_ts: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Two clustering layers, deliberately in separate columns. Layer one is
    # provable: a connected component over funding edges with routers and
    # exchanges cut out. Layer two is inferred from behaviour and carries a
    # confidence. Merging them into one number would destroy the only
    # answer that matters when someone asks which wallets you can prove.
    cluster_id: Mapped[int | None] = mapped_column(Integer)
    cluster_size: Mapped[int | None] = mapped_column(Integer)
    community_id: Mapped[int | None] = mapped_column(Integer)
    community_confidence: Mapped[float | None] = mapped_column(NORMALISED)
    insider_linked: Mapped[bool | None] = mapped_column()
    insider_reason: Mapped[str | None] = mapped_column(Text)
    provenance: Mapped[str] = mapped_column(PROVENANCE, nullable=False)


class IngestRun(Base):
    __tablename__ = "ingest_run"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    chain: Mapped[str] = mapped_column(String(16), nullable=False)
    scope: Mapped[str | None] = mapped_column(Text)
    requests_made: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    compute_units: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default=text("0"))
    rows_written: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    status: Mapped[str] = mapped_column(RUN_STATUS, nullable=False)
    error: Mapped[str | None] = mapped_column(Text)
    config_json: Mapped[dict | None] = mapped_column(JSONB)
    git_sha: Mapped[str | None] = mapped_column(String(40))


class BudgetLedger(Base):
    """Spend per source per calendar month, persisted so a restart cannot
    forget what the month has already cost. Not in the brief's table list;
    the brief's budget requirement ("persisted in the database so it
    survives restarts") needs somewhere to live.
    """
    __tablename__ = "budget_ledger"
    source: Mapped[str] = mapped_column(String(32), primary_key=True)
    period: Mapped[str] = mapped_column(String(7), primary_key=True)   # YYYY-MM
    compute_units: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default=text("0"))
    requests: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default=text("0"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class BackfillCheckpoint(Base):
    """Where a token's backfill got to, so a crashed run resumes instead of
    starting over and re-spending the budget."""
    __tablename__ = "backfill_checkpoint"
    chain: Mapped[str] = mapped_column(String(16), primary_key=True)
    token_address: Mapped[str] = mapped_column(String(66), primary_key=True)
    from_block: Mapped[int] = mapped_column(BigInteger, nullable=False)
    to_block: Mapped[int] = mapped_column(BigInteger, nullable=False)
    next_block: Mapped[int] = mapped_column(BigInteger, nullable=False)
    as_of_ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    done: Mapped[bool] = mapped_column(nullable=False, server_default=text("false"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

LABEL = Enum("RUG", "FAILED", "SURVIVED", "UNCLEAR", "NEVER_LAUNCHED",
             name="token_label_kind", create_type=True)
RESERVE_SIDE = Enum("token", "quote", name="reserve_side", create_type=True)


class TokenLabel(Base):
    """Phase 2's deliverable: an outcome per token, with its evidence.

    Keyed by `(token_address, chain, rule_version)`, so changing a threshold
    writes a new generation of rows rather than mutating the old ones. The
    previous labels stay, which is what lets a report show how the set moved
    when the definition moved.

    Every criterion is stored as its own boolean *next to the measurement
    that produced it*. That is what lets the interface show why a token was
    called a rug instead of asserting it, and it means a threshold change can
    be re-evaluated from these columns with no network access at all.

    `reserve_side` is not decoration. On Uniswap V4 one PoolManager holds
    every pool's quote token, so a per-pool quote reserve cannot be read and
    the token side is measured instead. A row that does not say which side it
    measured would be claiming more than it knows.
    """
    __tablename__ = "token_label"
    token_address: Mapped[str] = mapped_column(String(66), primary_key=True)
    chain: Mapped[str] = mapped_column(String(16), primary_key=True)
    rule_version: Mapped[str] = mapped_column(String(32), primary_key=True)

    label: Mapped[str] = mapped_column(LABEL, nullable=False)

    # one column per criterion
    liquidity_pulled: Mapped[bool] = mapped_column(nullable=False)
    sustained_collapse: Mapped[bool] = mapped_column(nullable=False)
    dead: Mapped[bool] = mapped_column(nullable=False)
    still_live: Mapped[bool] = mapped_column(nullable=False)
    possible_migration: Mapped[bool] = mapped_column(nullable=False)
    never_launched: Mapped[bool] = mapped_column(nullable=False)

    # the measurements behind them
    reserve_side: Mapped[str] = mapped_column(RESERVE_SIDE, nullable=False)
    peak_reserve: Mapped[float | None] = mapped_column(NORMALISED)
    peak_reserve_ts: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reserve_at_end: Mapped[float | None] = mapped_column(NORMALISED)
    peak_price: Mapped[float | None] = mapped_column(USD)
    peak_price_ts: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    price_at_end: Mapped[float | None] = mapped_column(USD)
    largest_drop_fraction: Mapped[float | None] = mapped_column(NORMALISED)
    largest_drop_ts: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    largest_drop_from: Mapped[float | None] = mapped_column(NORMALISED)
    largest_drop_to: Mapped[float | None] = mapped_column(NORMALISED)

    # Activity is days on which the price moved, not a swap count: a count
    # costs a 1,296-call log scan per token, 14x the price series, and this
    # falls out of samples already taken. See label/rules.py.
    active_days_last_30: Mapped[int | None] = mapped_column(Integer)
    sibling_pairs: Mapped[int | None] = mapped_column(Integer)

    # Evidence for the outflow, recorded but never asserted as attribution:
    # naming the recipient as the deployer needs a funding cluster, which is
    # Phase 3. The destination is stored so a human can judge it.
    largest_outflow_amount: Mapped[float | None] = mapped_column(NORMALISED)
    largest_outflow_to: Mapped[str | None] = mapped_column(String(66))

    # The sampled series itself, kept so the definition can be re-argued
    # offline. Without it the sensitivity sweep cannot move the observation
    # window at all - that threshold is not recoverable from summary
    # measurements - and every other threshold sweep would be re-derived
    # from numbers rather than from observations.
    series_json: Mapped[list | None] = mapped_column(JSONB)
    points_sampled: Mapped[int | None] = mapped_column(Integer)
    points_usable: Mapped[int | None] = mapped_column(Integer)
    launch_ts: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    observed_to_ts: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    calls_spent: Mapped[int | None] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(Text)

    labelled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    provenance: Mapped[str] = mapped_column(PROVENANCE, nullable=False)


Index("ix_token_label_label", TokenLabel.chain, TokenLabel.rule_version, TokenLabel.label)

class WalletFeature(Base):
    """Phase 3's output: one wallet's features, frozen at a moment.

    Keyed by `(wallet_address, chain, token_address, as_of_ts)`. The token is
    part of the key because these features are computed *for scoring a
    particular launch*: the same wallet has different features at the cutoff
    of one token than at another, and conflating them is how a feature ends
    up seeing the future.

    The features themselves live in `features` as JSONB rather than in ~70
    columns. That is a deliberate trade. Named columns would be stricter,
    but the feature set is explicitly expected to change shape during Phase 4
    tuning, and a migration per experiment would make the schema the
    bottleneck. `feature_set_version` and `n_features` make a row's shape
    checkable, and `graph/features.py` owns the names.
    """
    __tablename__ = "wallet_feature"
    wallet_address: Mapped[str] = mapped_column(String(66), primary_key=True)
    chain: Mapped[str] = mapped_column(String(16), primary_key=True)
    token_address: Mapped[str] = mapped_column(String(66), primary_key=True)
    as_of_ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)

    feature_set_version: Mapped[str] = mapped_column(String(32), nullable=False)
    n_features: Mapped[int] = mapped_column(Integer, nullable=False)
    features: Mapped[dict] = mapped_column(JSONB, nullable=False)

    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    provenance: Mapped[str] = mapped_column(PROVENANCE, nullable=False)


Index("ix_wallet_feature_token", WalletFeature.chain, WalletFeature.token_address)


class GraphEdge(Base):
    """An edge, stored so the graph can be rebuilt without re-deriving it.

    `kind` separates funding edges from co-occurrence edges and they are
    never mixed: one is "A sent B tokens", the other is "A and B bought the
    same thing at about the same time". Only the first is a relationship
    between addresses; the second is a coincidence that becomes evidence
    only in aggregate. `window_seconds` records the window a co-occurrence
    edge was drawn with, since the edge means nothing without it.
    """
    __tablename__ = "graph_edge"
    chain: Mapped[str] = mapped_column(String(16), primary_key=True)
    kind: Mapped[str] = mapped_column(String(16), primary_key=True)
    src: Mapped[str] = mapped_column(String(66), primary_key=True)
    dst: Mapped[str] = mapped_column(String(66), primary_key=True)
    token_address: Mapped[str] = mapped_column(String(66), primary_key=True,
                                               server_default=text("''"))

    weight: Mapped[float | None] = mapped_column(NORMALISED)
    amount: Mapped[float | None] = mapped_column(NORMALISED)
    block_number: Mapped[int | None] = mapped_column(BigInteger)
    ts: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    window_seconds: Mapped[int | None] = mapped_column(Integer)
    funding_source: Mapped[str | None] = mapped_column(String(16))
    provenance: Mapped[str] = mapped_column(PROVENANCE, nullable=False)


Index("ix_graph_edge_src", GraphEdge.chain, GraphEdge.kind, GraphEdge.src)
Index("ix_graph_edge_dst", GraphEdge.chain, GraphEdge.kind, GraphEdge.dst)



class TokenSample(Base):
    """Phase 5: how each token entered the dataset, and what the screen saw.

    `sampling_stratum` is the column the whole sampling design depends on.
    The stratified strata are for training only; the `random` cohort is the
    only part of the set at the true prevalence, and every headline metric
    is computed on it. Mixing them without this column would be the error
    the design exists to avoid. See `reports/sampling_design.md`.

    strata: `random` (uniform launch windows, outcome-blind), `train`
    (separate uniform windows, labelled until the class targets fill),
    `survivor_enum` (pools enumerated because they trade today),
    `phase2` (the 75 tokens labelled before this design existed).
    """
    __tablename__ = "token_sample"
    token_address: Mapped[str] = mapped_column(String(66), primary_key=True)
    chain: Mapped[str] = mapped_column(String(16), primary_key=True)
    sampling_stratum: Mapped[str] = mapped_column(String(24), nullable=False)
    window_id: Mapped[str | None] = mapped_column(String(48))
    window_start_block: Mapped[int | None] = mapped_column(BigInteger)
    window_end_block: Mapped[int | None] = mapped_column(BigInteger)
    pool_key: Mapped[str | None] = mapped_column(String(66))
    dex: Mapped[str | None] = mapped_column(String(32))
    created_block: Mapped[int | None] = mapped_column(BigInteger)
    launch_ts: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    initial_sqrt_price: Mapped[str | None] = mapped_column(String(80))
    # the screen: swaps by the cutoff minute, and in the 1,000 blocks after
    screened: Mapped[bool] = mapped_column(nullable=False, server_default=text("false"))
    swaps_by_cutoff: Mapped[int | None] = mapped_column(Integer)
    swaps_after_cutoff: Mapped[int | None] = mapped_column(Integer)
    # decided after backfill, from stored swaps and reserves
    alive_at_cutoff: Mapped[bool | None] = mapped_column()
    family_id: Mapped[str | None] = mapped_column(String(80))
    excluded_reason: Mapped[str | None] = mapped_column(Text)
    # Part B case-control pre-screen: the labeller's own nine coarse points,
    # read before deciding which training tokens get the dense pass.
    coarse_max_drop: Mapped[float | None] = mapped_column(Numeric)
    coarse_end_vs_peak: Mapped[float | None] = mapped_column(Numeric)
    coarse_calls: Mapped[int | None] = mapped_column(Integer)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


Index("ix_token_sample_stratum", TokenSample.chain, TokenSample.sampling_stratum)


class WatchlistItem(Base):
    """Product state: a token the user is keeping an eye on.

    No account and no owner column: the product is single-user by design
    at this stage (docs/FYP1_SCOPE.md, M8). Keyed by address so a token can
    be on the list once, whatever the letter case it was pasted in.
    """
    __tablename__ = "watchlist_item"
    token_address: Mapped[str] = mapped_column(String(66), primary_key=True)
    chain: Mapped[str] = mapped_column(String(16), primary_key=True)
    label: Mapped[str | None] = mapped_column(String(64))
    note: Mapped[str | None] = mapped_column(Text)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Investigation(Base):
    """Product state: every address the user opened, and what it resolved to.

    `outcome` is `profile` (one of the researched case studies), `tracked`
    (a launch the live feed scored) or `live` (public market data only).
    """
    __tablename__ = "investigation"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    token_address: Mapped[str] = mapped_column(String(66), nullable=False)
    chain: Mapped[str] = mapped_column(String(16), nullable=False)
    outcome: Mapped[str] = mapped_column(String(24), nullable=False)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class LivePrediction(Base):
    """Phase 8: the forward-validation log, one row per launch the live feed
    reached a verdict on, written once and never edited (live/resolver.py).

    Declared here so the test schema matches the migrated one; the
    migrations (`a9c1d2e3f405`, `b7a8c9d0e1f2`) remain the source of truth
    for a real database.
    """
    __tablename__ = "live_prediction"
    __table_args__ = (Index("ix_live_prediction_launch", "chain", "launch_ts"),)
    token_address: Mapped[str] = mapped_column(String(66), primary_key=True)
    chain: Mapped[str] = mapped_column(String(16), primary_key=True)
    pool_key: Mapped[str] = mapped_column(String(66), nullable=False)
    dex: Mapped[str] = mapped_column(String(32), nullable=False)
    created_block: Mapped[int] = mapped_column(BigInteger, nullable=False)
    launch_ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    model_version: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    scored_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    risk: Mapped[float | None] = mapped_column(Float)
    launch_type: Mapped[str | None] = mapped_column(String(16))
    features: Mapped[dict | None] = mapped_column(JSONB)
    reserve_cutoff: Mapped[float | None] = mapped_column(Numeric)
    explanation: Mapped[dict | None] = mapped_column(JSONB)
    resolved_6h_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    price_6h_vs_cutoff: Mapped[float | None] = mapped_column(Float)
    buyer_loss: Mapped[bool | None] = mapped_column(Boolean)
    reserve_6h: Mapped[float | None] = mapped_column(Numeric)
    reserve_1d: Mapped[float | None] = mapped_column(Numeric)
    reserve_7d: Mapped[float | None] = mapped_column(Numeric)
    reserve_30d: Mapped[float | None] = mapped_column(Numeric)
    reserve_90d: Mapped[float | None] = mapped_column(Numeric)
    notes: Mapped[str | None] = mapped_column(Text)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
