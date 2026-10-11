"""The write gate: the two properties the whole pipeline rests on.

1. A row from after `as_of_ts` cannot be written. Lookahead is the failure
   mode that makes a backtest look brilliant and a live model lose money,
   and it is invisible once it is in the data — so it is refused at the
   only door into the store.
2. Running the same ingestion twice writes the same rows. A backfill that
   crashes halfway has to be safe to restart, and a re-run must not inflate
   a count that a result will later be computed from.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import func, select

from blocklens.store import write
from blocklens.store.models import Token, Transfer

CHAIN = "base"
AS_OF = datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc)
TOKEN = "0x" + "a1" * 20
WALLET = "0x" + "b2" * 20


def transfer(ix: int, ts: datetime, value: int = 1000) -> dict:
    return {
        "chain": CHAIN, "tx_hash": "0x" + f"{ix:064x}", "log_index": ix,
        "block_number": 30_000_000 + ix, "block_ts": ts,
        "token_address": TOKEN, "from_address": TOKEN, "to_address": WALLET,
        "raw_value": value, "value_normalised": value / 1e18, "provenance": "live",
    }


def count(session) -> int:
    return session.scalar(
        select(func.count()).select_from(Transfer).where(Transfer.token_address == TOKEN)
    )


def test_gate_refuses_a_future_dated_row(session):
    rows = [
        transfer(1, AS_OF - timedelta(hours=1)),
        transfer(2, AS_OF + timedelta(seconds=1)),     # one second too late
    ]
    with pytest.raises(write.LookaheadError) as e:
        write.write_transfers(session, rows, as_of_ts=AS_OF)

    # The message has to name the offender. A gate that fires without
    # saying which row tripped it is a gate nobody can debug.
    assert "transfer" in str(e.value)
    assert "1 row(s)" in str(e.value)


def test_gate_refuses_the_whole_batch_not_just_the_bad_row(session):
    """Partial writes are worse than failures: the caller would believe it
    had written a complete window."""
    rows = [transfer(i, AS_OF - timedelta(minutes=i)) for i in range(1, 5)]
    rows.append(transfer(99, AS_OF + timedelta(days=1)))

    with pytest.raises(write.LookaheadError):
        write.write_transfers(session, rows, as_of_ts=AS_OF)
    session.rollback()

    assert count(session) == 0, "a refused batch must leave nothing behind"


def test_gate_allows_a_row_exactly_at_the_cutoff(session):
    """`as_of_ts` is inclusive: a feature computed at midnight may see the
    trade that happened at midnight."""
    res = write.write_transfers(session, [transfer(7, AS_OF)], as_of_ts=AS_OF)
    assert res.inserted == 1


def test_gate_requires_an_as_of_ts(session):
    with pytest.raises(ValueError):
        write.write_transfers(session, [transfer(1, AS_OF)], as_of_ts=None)


def test_rerun_writes_no_new_rows(session):
    rows = [transfer(i, AS_OF - timedelta(minutes=i)) for i in range(1, 51)]

    first = write.write_transfers(session, rows, as_of_ts=AS_OF)
    assert (first.inserted, first.updated) == (50, 0)
    assert count(session) == 50

    second = write.write_transfers(session, rows, as_of_ts=AS_OF)
    assert second.inserted == 0, "a re-run inserted rows that already existed"
    assert second.updated == 50
    assert count(session) == 50, "a re-run duplicated rows"


def test_rerun_overwrites_a_corrected_value(session):
    """Idempotent is not the same as inert. If a value changes — a decimals
    fix, a re-decode — the upsert has to carry the correction through."""
    write.write_transfers(session, [transfer(3, AS_OF, value=1000)], as_of_ts=AS_OF)
    write.write_transfers(session, [transfer(3, AS_OF, value=2000)], as_of_ts=AS_OF)

    row = session.get(Transfer, {"chain": CHAIN, "tx_hash": "0x" + f"{3:064x}", "log_index": 3})
    assert float(row.raw_value) == 2000.0
    assert count(session) == 1


def test_empty_write_is_a_no_op(session):
    res = write.write_transfers(session, [], as_of_ts=AS_OF)
    assert (res.inserted, res.updated, res.total) == (0, 0, 0)


def test_a_source_that_does_not_know_a_field_cannot_erase_it(session):
    """Enrichment runs after discovery and sees less of the token than the
    chain did. An absent value must leave the known one standing."""
    token = {"address": TOKEN, "chain": CHAIN, "symbol": None, "name": None,
             "decimals": 9, "created_block": 41, "created_ts": AS_OF,
             "creator_address": None, "provenance": "live"}
    write.write_tokens(session, [token], as_of_ts=AS_OF)

    # A second writer that knows the name but not the decimals.
    write.write_tokens(session, [{**token, "symbol": "PEPPER", "decimals": None,
                                  "created_block": None}], as_of_ts=AS_OF)

    row = session.get(Token, {"address": TOKEN, "chain": CHAIN})
    session.refresh(row)
    assert row.symbol == "PEPPER", "the new value should have been written"
    assert row.decimals == 9, "an absent value erased a known one"
    assert row.created_block == 41


def test_a_real_change_still_overwrites(session):
    """COALESCE must not make the store append-only: a corrected value wins."""
    token = {"address": TOKEN, "chain": CHAIN, "symbol": "OLD", "name": None,
             "decimals": 18, "created_block": 1, "created_ts": AS_OF,
             "creator_address": None, "provenance": "live"}
    write.write_tokens(session, [token], as_of_ts=AS_OF)
    write.write_tokens(session, [{**token, "symbol": "NEW", "decimals": 6}], as_of_ts=AS_OF)

    row = session.get(Token, {"address": TOKEN, "chain": CHAIN})
    session.refresh(row)
    assert (row.symbol, row.decimals) == ("NEW", 6)
