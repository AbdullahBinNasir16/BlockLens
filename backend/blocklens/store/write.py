"""THE WRITE GATE — the only module in the codebase allowed to write rows.

Everything else returns data and hands it over. One entry point per table,
and every one of them takes an explicit `as_of_ts`.

The gate refuses, loudly, if any row carries a timestamp later than
`as_of_ts`. It raises; it does not warn, and it does not silently filter.
Filtering would be worse than failing, because the caller would never learn
that it had asked for the future.

This looks like overkill in Phase 1, when nothing computes features yet.
It is not. It is the mechanism that makes lookahead impossible later, and
it has to exist before anything depends on it. A feature computed at
`as_of_ts` can only ever see rows this gate allowed in.

Writes are upserts on natural keys, never blind inserts, so a crashed run
is safe to restart. Each function reports inserts and updates separately —
`xmax = 0` is true only for a freshly inserted row — which is what lets the
acceptance test prove a re-run writes zero new rows.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Sequence

from sqlalchemy import func, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from .models import (
    BackfillCheckpoint, BudgetLedger, GraphEdge, IngestRun, Pair, PairSnapshot,
    Swap, Token, TokenLabel, Transfer, Wallet, WalletFeature,
)


UPSERT_BATCH = 5_000


class LookaheadError(RuntimeError):
    """A row claimed to happen after the moment the caller said it knew about.

    Raised rather than handled. If this fires, a caller has a bug in its
    windowing and the only safe thing to do is stop.
    """


@dataclass(frozen=True)
class WriteResult:
    inserted: int = 0
    updated: int = 0

    @property
    def total(self) -> int:
        return self.inserted + self.updated

    def __add__(self, other: "WriteResult") -> "WriteResult":
        return WriteResult(self.inserted + other.inserted, self.updated + other.updated)


def _as_utc(v: Any) -> datetime | None:
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return datetime.fromtimestamp(v, timezone.utc)
    if isinstance(v, datetime):
        return v if v.tzinfo else v.replace(tzinfo=timezone.utc)
    raise TypeError(f"not a timestamp: {v!r}")


def _gate(rows: Sequence[dict], as_of_ts: datetime, field: str, table: str) -> None:
    """Refuse the whole batch if any row is from after `as_of_ts`."""
    cutoff = _as_utc(as_of_ts)
    if cutoff is None:
        raise ValueError(f"{table}: as_of_ts is required")
    offenders = []
    for r in rows:
        ts = _as_utc(r.get(field))
        if ts is not None and ts > cutoff:
            offenders.append((r.get("tx_hash") or r.get("address") or r.get("pair_address"), ts))
    if offenders:
        head = ", ".join(f"{k}@{t.isoformat()}" for k, t in offenders[:5])
        raise LookaheadError(
            f"{table}: {len(offenders)} row(s) carry {field} after as_of_ts "
            f"{cutoff.isoformat()} - refusing the write. First: {head}"
        )


def _upsert(session: Session, model, rows: Sequence[dict], keys: list[str]) -> WriteResult:
    """Upsert on the natural key, and never let a partial observer erase a
    fact a better-informed one recorded.

    Every writer here sees only part of the picture: the chain knows a
    token's decimals and nothing about its name, DexScreener knows the name
    and never reports decimals. A plain `SET col = excluded.col` therefore
    overwrites a known value with a NULL the moment the other source runs,
    which is how a correct decimals became None in testing.

    So a nullable column takes `COALESCE(excluded.col, existing.col)`: a new
    value wins, an absent one leaves the old value alone. Required columns
    are overwritten outright, because no writer can be missing those.
    """
    if not rows:
        return WriteResult()

    # Written in batches. A single statement carrying every row is fine at
    # the hundreds Phase 1 writes per window, and is not fine at the ~107,000
    # co-purchase edges Phase 3 produces: one upsert that size, with a
    # RETURNING clause on every row, did not finish in ten minutes. The
    # batch size is a round number rather than a tuned one - the cost here
    # is dominated by there being any bound at all.
    rows = list(rows)
    if len(rows) > UPSERT_BATCH:
        total = WriteResult()
        for i in range(0, len(rows), UPSERT_BATCH):
            total = total + _upsert(session, model, rows[i:i + UPSERT_BATCH], keys)
        return total

    stmt = insert(model).values(rows)
    table = model.__table__
    updatable = {
        c.name: (
            func.coalesce(stmt.excluded[c.name], table.c[c.name])
            if c.nullable else stmt.excluded[c.name]
        )
        for c in table.columns
        if c.name not in keys
    }
    stmt = stmt.on_conflict_do_update(index_elements=keys, set_=updatable)
    # xmax = 0 marks a row this statement inserted rather than updated
    stmt = stmt.returning(text("(xmax = 0) AS inserted"))
    res = session.execute(stmt).all()
    ins = sum(1 for r in res if r[0])
    return WriteResult(inserted=ins, updated=len(res) - ins)


# --------------------------------------------------------------------------
# one entry point per table
# --------------------------------------------------------------------------

def write_tokens(session: Session, rows: Sequence[dict], *, as_of_ts: datetime) -> WriteResult:
    _gate(rows, as_of_ts, "created_ts", "token")
    return _upsert(session, Token, rows, ["address", "chain"])


def write_pairs(session: Session, rows: Sequence[dict], *, as_of_ts: datetime) -> WriteResult:
    _gate(rows, as_of_ts, "created_ts", "pair")
    return _upsert(session, Pair, rows, ["address", "chain"])


def write_pair_snapshots(session: Session, rows: Sequence[dict], *, as_of_ts: datetime) -> WriteResult:
    _gate(rows, as_of_ts, "ts", "pair_snapshot")
    return _upsert(session, PairSnapshot, rows, ["pair_address", "ts"])


def write_transfers(session: Session, rows: Sequence[dict], *, as_of_ts: datetime) -> WriteResult:
    _gate(rows, as_of_ts, "block_ts", "transfer")
    return _upsert(session, Transfer, rows, ["chain", "tx_hash", "log_index"])


def write_swaps(session: Session, rows: Sequence[dict], *, as_of_ts: datetime) -> WriteResult:
    _gate(rows, as_of_ts, "block_ts", "swap")
    return _upsert(session, Swap, rows, ["chain", "tx_hash", "log_index"])


def write_wallets(session: Session, rows: Sequence[dict], *, as_of_ts: datetime) -> WriteResult:
    _gate(rows, as_of_ts, "first_seen_ts", "wallet")
    return _upsert(session, Wallet, rows, ["address", "chain"])


def write_token_labels(session: Session, rows: Sequence[dict], *,
                       as_of_ts: datetime) -> WriteResult:
    """Phase 2's outcomes. The gate applies here exactly as elsewhere.

    `as_of_ts` is the end of the observation window — launch plus 90 days —
    which is honest: this verdict genuinely could not have been known before
    then. That is also what stops a label ever being mistaken for a feature:
    anything computed at the feature cutoff cannot see a row the gate only
    admitted three months later.

    Keyed by `(token_address, chain, rule_version)`, so a threshold change
    writes a new generation and leaves the old verdicts standing.
    """
    _gate(rows, as_of_ts, "observed_to_ts", "token_label")
    return _upsert(session, TokenLabel, rows,
                   ["token_address", "chain", "rule_version"])


def write_graph_edges(session: Session, rows: Sequence[dict], *,
                      as_of_ts: datetime) -> WriteResult:
    """Funding and co-occurrence edges. Keyed so a re-run is idempotent.

    Gated on `ts`, so an edge drawn from an event after the cutoff cannot be
    stored against that cutoff. Walking a graph is the easiest place in the
    whole system to pull in next week's event by accident — a two-hop
    neighbour is two joins away from anything — which is why the gate sits
    here rather than being a convention the graph code is trusted to follow.
    """
    _gate(rows, as_of_ts, "ts", "graph_edge")
    return _upsert(session, GraphEdge, rows,
                   ["chain", "kind", "src", "dst", "token_address"])


def write_wallet_features(session: Session, rows: Sequence[dict], *,
                          as_of_ts: datetime) -> WriteResult:
    """Per-wallet features, frozen at `as_of_ts`.

    The gate checks `as_of_ts` on the row against the cutoff it was asked
    for, which catches the specific accident this table invites: computing a
    neighbour aggregate at one cutoff and filing it under another.
    """
    _gate(rows, as_of_ts, "as_of_ts", "wallet_feature")
    return _upsert(session, WalletFeature, rows,
                   ["wallet_address", "chain", "token_address", "as_of_ts"])


# --------------------------------------------------------------------------
# bookkeeping — runs, budget, checkpoints
# --------------------------------------------------------------------------

def start_run(session: Session, *, source: str, chain: str, scope: str | None,
              config_json: dict, git_sha: str) -> int:
    run = IngestRun(
        started_at=datetime.now(timezone.utc), source=source, chain=chain, scope=scope,
        status="running", config_json=config_json, git_sha=git_sha,
    )
    session.add(run)
    session.flush()
    return run.id


def finish_run(session: Session, run_id: int, *, status: str, requests_made: int = 0,
               compute_units: int = 0, rows_written: int = 0, error: str | None = None) -> None:
    run = session.get(IngestRun, run_id)
    if run is None:
        return
    run.finished_at = datetime.now(timezone.utc)
    run.status = status
    run.requests_made = requests_made
    run.compute_units = compute_units
    run.rows_written = rows_written
    run.error = error[:4000] if error else None


def bump_budget(session: Session, *, source: str, period: str,
                requests: int = 0, compute_units: int = 0) -> None:
    stmt = insert(BudgetLedger).values(
        source=source, period=period, requests=requests, compute_units=compute_units,
        updated_at=datetime.now(timezone.utc),
    ).on_conflict_do_update(
        index_elements=["source", "period"],
        set_={
            "requests": BudgetLedger.requests + requests,
            "compute_units": BudgetLedger.compute_units + compute_units,
            "updated_at": datetime.now(timezone.utc),
        },
    )
    session.execute(stmt)


def read_budget(session: Session, *, source: str, period: str) -> tuple[int, int]:
    row = session.get(BudgetLedger, (source, period))
    return (row.requests, row.compute_units) if row else (0, 0)


def save_checkpoint(session: Session, *, chain: str, token_address: str, from_block: int,
                    to_block: int, next_block: int, as_of_ts: datetime, done: bool) -> None:
    stmt = insert(BackfillCheckpoint).values(
        chain=chain, token_address=token_address, from_block=from_block, to_block=to_block,
        next_block=next_block, as_of_ts=as_of_ts, done=done,
        updated_at=datetime.now(timezone.utc),
    ).on_conflict_do_update(
        index_elements=["chain", "token_address"],
        set_={"next_block": next_block, "done": done, "to_block": to_block,
              "updated_at": datetime.now(timezone.utc)},
    )
    session.execute(stmt)


def get_checkpoint(session: Session, *, chain: str, token_address: str) -> BackfillCheckpoint | None:
    return session.get(BackfillCheckpoint, (chain, token_address))
