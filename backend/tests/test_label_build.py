"""The labeller's guarantees: refuse the young, never duplicate, never peek.

These are the three ways a labelled dataset gets quietly ruined — a token
labelled before its outcome happened, a re-run inflating the counts a result
will later be computed from, and a label leaking into the features. Each one
is invisible afterwards, so each one is a test.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import func, select

from blocklens.ingest.budget import Budget
from blocklens.ingest.sources import RpcSource
from blocklens.label import build as lb
from blocklens.label import rules
from blocklens.label.sample import Sampler
from blocklens.store import write
from blocklens.store.models import (
    BackfillCheckpoint, Pair, Swap, Token, TokenLabel,
)
from tests.conftest import rpc_client

CHAIN = "base"
HEAD = 52_000_000
BLOCKS_PER_DAY = 43_200
LAUNCH_TS = datetime(2026, 6, 1, tzinfo=timezone.utc)


def label_row(token: str, **kw) -> dict:
    base = dict(
        token_address=token, chain=CHAIN, rule_version=rules.RULE_VERSION,
        label="RUG", liquidity_pulled=True, sustained_collapse=False,
        dead=False, still_live=False, possible_migration=False,
        never_launched=False, reserve_side="token",
        peak_reserve=1000.0, peak_reserve_ts=LAUNCH_TS,
        reserve_at_end=10.0, peak_price=5.0, peak_price_ts=LAUNCH_TS,
        price_at_end=0.1, largest_drop_fraction=0.99,
        largest_drop_ts=LAUNCH_TS + timedelta(days=2),
        largest_drop_from=1000.0, largest_drop_to=10.0,
        active_days_last_30=0, sibling_pairs=0,
        largest_outflow_amount=990.0, largest_outflow_to="0x" + "ab" * 20,
        series_json=[], points_sampled=100, points_usable=100,
        launch_ts=LAUNCH_TS,
        observed_to_ts=LAUNCH_TS + timedelta(days=90),
        calls_spent=18, notes="sampling=coarse",
        labelled_at=datetime.now(timezone.utc), provenance="live",
    )
    base.update(kw)
    return base


# ---- the gate applies to labels too --------------------------------------

def test_a_label_dated_after_its_as_of_is_refused(session):
    row = label_row("0x" + "11" * 20)
    with pytest.raises(write.LookaheadError):
        write.write_token_labels(session, [row],
                                 as_of_ts=row["observed_to_ts"] - timedelta(days=1))


def test_a_label_at_its_own_cutoff_is_allowed(session):
    row = label_row("0x" + "12" * 20)
    res = write.write_token_labels(session, [row], as_of_ts=row["observed_to_ts"])
    assert res.inserted == 1


def test_relabelling_writes_no_new_rows(session):
    """A re-run must not inflate a count the base rate is computed from."""
    rows = [label_row(f"0x{i:040x}") for i in range(1, 21)]
    as_of = rows[0]["observed_to_ts"]

    first = write.write_token_labels(session, rows, as_of_ts=as_of)
    assert (first.inserted, first.updated) == (20, 0)

    second = write.write_token_labels(session, rows, as_of_ts=as_of)
    assert second.inserted == 0, "a re-run inserted rows that already existed"

    n = session.scalar(select(func.count()).select_from(TokenLabel))
    assert n == 20


def test_a_new_rule_version_is_a_new_generation_not_an_overwrite(session):
    """Old verdicts have to survive a threshold change, or there is no way
    to show how the set moved when the definition moved."""
    token = "0x" + "13" * 20
    as_of = LAUNCH_TS + timedelta(days=90)
    write.write_token_labels(session, [label_row(token, rule_version="v1-2026-10")],
                             as_of_ts=as_of)
    write.write_token_labels(session, [label_row(token, rule_version="v2-2026-11",
                                                 label="FAILED")],
                             as_of_ts=as_of)

    got = session.execute(
        select(TokenLabel.rule_version, TokenLabel.label)
        .where(TokenLabel.token_address == token)
        .order_by(TokenLabel.rule_version)).all()
    assert got == [("v1-2026-10", "RUG"), ("v2-2026-11", "FAILED")]


# ---- too young -----------------------------------------------------------

def _sampler(head: int = HEAD):
    budget = Budget(max_calls=50)
    rpc = RpcSource(budget, client=rpc_client({
        "eth_blockNumber": hex(head),
        "eth_getBlockByNumber": {"timestamp": hex(int(LAUNCH_TS.timestamp()))},
        "eth_call": "0x" + f"{0:064x}",
    }))
    return Sampler(rpc, budget), rpc


def test_a_token_younger_than_the_window_is_refused_not_labelled():
    """The one mistake that would invalidate the whole dataset, and the one
    that would be invisible once made."""
    sampler, rpc = _sampler(head=HEAD)
    token = {
        "token_address": "0x" + "14" * 20,
        # only 10 days of chain left after it: the window cannot have closed
        "created_block": HEAD - 10 * BLOCKS_PER_DAY,
        "created_ts": LAUNCH_TS, "decimals": 18,
        "pair_key": "0x" + "15" * 20, "quote": "0x" + "16" * 20,
        "dex": "uniswap-v3",
    }
    with pytest.raises(lb.TooYoung) as e:
        lb.sample_token(sampler, rpc, token=token)
    assert "past the head" in str(e.value)


def test_a_token_old_enough_is_not_refused():
    sampler, rpc = _sampler(head=HEAD)
    token = {
        "token_address": "0x" + "17" * 20,
        "created_block": HEAD - 120 * BLOCKS_PER_DAY,
        "created_ts": LAUNCH_TS, "decimals": 18,
        "pair_key": "0x" + "18" * 20, "quote": "0x" + "19" * 20,
        "dex": "uniswap-v3",
    }
    series, launch_ts, end_ts = lb.sample_token(sampler, rpc, token=token)
    assert series.points, "nothing was sampled"
    assert end_ts >= launch_ts


# ---- candidate selection -------------------------------------------------

def _seed(session, *, token: str, created_block: int, swaps: int,
          dex: str = "uniswap-v3") -> None:
    pair = "0x" + token[2:10] + "cc" * 16
    session.add(Token(address=token, chain=CHAIN, decimals=18,
                      created_block=created_block,
                      # deliberately inconsistent with the block, as the real
                      # store is: created_ts comes from a different source
                      created_ts=LAUNCH_TS, provenance="live"))
    session.add(Pair(address=pair, chain=CHAIN, token_address=token,
                     quote_token="0x" + "99" * 20, dex=dex,
                     created_block=created_block, created_ts=LAUNCH_TS,
                     provenance="live"))
    session.add(BackfillCheckpoint(
        chain=CHAIN, token_address=token, from_block=created_block,
        to_block=created_block + BLOCKS_PER_DAY,
        next_block=created_block + BLOCKS_PER_DAY + 1,
        as_of_ts=LAUNCH_TS, done=True, updated_at=datetime.now(timezone.utc)))
    for i in range(swaps):
        session.add(Swap(
            chain=CHAIN, tx_hash=f"0x{token[2:10]}{i:056x}", log_index=i,
            block_number=created_block + i, block_ts=LAUNCH_TS,
            pair_address=pair, side="buy", token_amount=1.0, quote_amount=1.0,
            provenance="live"))
    session.flush()


def test_candidates_uses_block_age_not_created_ts(session):
    """`created_ts` and `created_block` disagree in the real store, because
    enrichment fills the timestamp from DexScreener's pair while discovery
    supplies the block. One token carries a block from three days ago and a
    timestamp from 369 days ago. Age has to come from the block.
    """
    old = "0x" + "21" * 20
    young = "0x" + "22" * 20
    _seed(session, token=old, created_block=HEAD - 200 * BLOCKS_PER_DAY, swaps=5)
    _seed(session, token=young, created_block=HEAD - 10 * BLOCKS_PER_DAY, swaps=5)

    got = {c["token_address"] for c in
           lb.candidates(session, chain=CHAIN, head_block=HEAD)}

    assert old in got
    assert young not in got, "a token whose window has not closed was offered"


def test_candidates_excludes_pools_that_never_traded(session):
    traded = "0x" + "23" * 20
    quiet = "0x" + "24" * 20
    _seed(session, token=traded, created_block=HEAD - 200 * BLOCKS_PER_DAY, swaps=3)
    _seed(session, token=quiet, created_block=HEAD - 200 * BLOCKS_PER_DAY, swaps=0)

    got = {c["token_address"] for c in
           lb.candidates(session, chain=CHAIN, head_block=HEAD)}

    assert traded in got
    assert quiet not in got, "a pool with no trades was offered for labelling"


def test_candidates_skips_what_is_already_labelled(session):
    token = "0x" + "25" * 20
    _seed(session, token=token, created_block=HEAD - 200 * BLOCKS_PER_DAY, swaps=5)
    assert token in {c["token_address"] for c in
                     lb.candidates(session, chain=CHAIN, head_block=HEAD)}

    write.write_token_labels(session, [label_row(token)],
                             as_of_ts=LAUNCH_TS + timedelta(days=90))
    session.flush()

    assert token not in {c["token_address"] for c in
                         lb.candidates(session, chain=CHAIN, head_block=HEAD)}


def test_excluded_counts_add_up(session):
    _seed(session, token="0x" + "26" * 20,
          created_block=HEAD - 200 * BLOCKS_PER_DAY, swaps=4)
    _seed(session, token="0x" + "27" * 20,
          created_block=HEAD - 200 * BLOCKS_PER_DAY, swaps=0)

    c = lb.excluded_counts(session, chain=CHAIN, head_block=HEAD)

    assert c["old_enough_with_window"] == 2
    assert c["traded_at_least_once"] == 1
    assert c["excluded_never_traded"] == 1


# ---- round-tripping the series ------------------------------------------

def test_a_stored_series_rebuilds_into_the_same_measurements():
    """What makes the sensitivity sweep trustworthy: the observations stored
    on a row reproduce the verdict that was written from them."""
    pts = [{"b": 100 + i, "t": 1_760_000_000 + i * 86_400,
            "r": 1000.0 - i * 10, "q": None, "p": 5.0 - i * 0.05}
           for i in range(30)]
    rebuilt = lb.series_from({"series_json": pts})

    assert len(rebuilt.points) == 30
    assert rebuilt.points[0].token_reserve == 1000.0
    assert rebuilt.points[-1].price == pytest.approx(5.0 - 29 * 0.05)

    m = rules.measure(rebuilt, launch_ts=1_760_000_000,
                      end_ts=1_760_000_000 + 30 * 86_400)
    assert m.peak_reserve == 1000.0
    assert m.points_usable == 30
