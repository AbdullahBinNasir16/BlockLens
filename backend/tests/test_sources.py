"""The two remaining external APIs, against recorded responses.

DexScreener's fixture is a real captured response. X's is synthetic and
says so in the file itself — recording one needs a paid bearer token, and
the project runs unpaid. So the X tests assert the shape and the locks,
and claim nothing about X's data.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import func, select

from blocklens.config import Config
from blocklens.ingest import dexscreener as ds_ingest
from blocklens.ingest import xapi
from blocklens.ingest.budget import Budget, BudgetExhausted
from blocklens.ingest.sources import DexScreenerSource
from blocklens.store.models import Pair, PairSnapshot, Token
from tests.conftest import load, mock_client

DS_FIX = load("dexscreener_tokens.json")
TOKEN = DS_FIX["addresses"][0].lower()


def ds_source(budget: Budget | None = None) -> DexScreenerSource:
    budget = budget or Budget(max_calls=10)
    return DexScreenerSource(budget, client=mock_client({"/tokens/v1/": DS_FIX["result"]}))


# ---- dexscreener ---------------------------------------------------------

def test_enrich_writes_tokens_pairs_and_a_snapshot(session):
    budget = Budget(max_calls=10)
    res = ds_ingest.enrich(session, ds_source(budget), [TOKEN], chain="base")

    assert res["asked"] == 1
    assert res["unknown"] == []
    assert res["tokens"] >= 1 and res["pairs"] >= 1 and res["snapshots"] >= 1
    assert budget.requests == 1, "one batch must cost one call"

    token = session.get(Token, {"address": TOKEN, "chain": "base"})
    assert token.symbol == DS_FIX["result"][0]["baseToken"]["symbol"]
    assert token.provenance == "live"

    pair_addr = DS_FIX["result"][0]["pairAddress"].lower()
    pair = session.get(Pair, {"address": pair_addr, "chain": "base"})
    assert pair.token_address == TOKEN
    assert pair.dex == DS_FIX["result"][0]["dexId"]


def test_every_poll_appends_a_snapshot_even_when_nothing_moved(session):
    """A gap in the series would otherwise be indistinguishable from a poll
    that found no change."""
    t0 = datetime(2026, 10, 10, 9, 0, tzinfo=timezone.utc)
    ds_ingest.enrich(session, ds_source(), [TOKEN], chain="base", as_of_ts=t0)
    ds_ingest.enrich(session, ds_source(), [TOKEN], chain="base",
                     as_of_ts=t0 + timedelta(minutes=5))

    n = session.scalar(select(func.count()).select_from(PairSnapshot))
    assert n == 2, "the second poll did not record its own observation"


def test_the_same_poll_twice_is_not_two_observations(session):
    """Re-running an ingestion must not invent market history: the snapshot
    key is (pair, ts), so an identical poll upserts."""
    t0 = datetime(2026, 10, 10, 9, 0, tzinfo=timezone.utc)
    ds_ingest.enrich(session, ds_source(), [TOKEN], chain="base", as_of_ts=t0)
    ds_ingest.enrich(session, ds_source(), [TOKEN], chain="base", as_of_ts=t0)

    assert session.scalar(select(func.count()).select_from(PairSnapshot)) == 1


def test_a_token_dexscreener_has_never_heard_of_is_reported_not_invented(session):
    unknown = "0x" + "ee" * 20
    res = ds_ingest.enrich(session, ds_source(), [TOKEN, unknown], chain="base")

    assert res["unknown"] == [unknown]
    assert session.get(Token, {"address": unknown, "chain": "base"}) is None


def test_missing_numbers_stay_null_rather_than_becoming_zero():
    """An unknown liquidity and a zero liquidity are different claims."""
    assert ds_ingest._f(None) is None
    assert ds_ingest._f("") is None
    assert ds_ingest._f("not a number") is None
    assert ds_ingest._f("0") == 0.0
    assert ds_ingest._f("0.005774") == pytest.approx(0.005774)


def test_snapshot_reads_the_numbers_the_api_actually_sent():
    pair = DS_FIX["result"][0]
    ts = datetime(2026, 10, 10, tzinfo=timezone.utc)
    row = ds_ingest._snapshot_row(pair, "base", ts)

    assert row["price_usd"] == pytest.approx(float(pair["priceUsd"]))
    assert row["liquidity_usd"] == pytest.approx(float(pair["liquidity"]["usd"]))
    assert row["volume_24h"] == pytest.approx(float(pair["volume"]["h24"]))
    assert row["txns_buy_24h"] == pair["txns"]["h24"]["buys"]
    assert row["source"] == "dexscreener"


def test_enrich_does_not_overwrite_decimals_with_a_guess(session):
    """DexScreener does not publish decimals. The chain does, and a later
    enrich must not clobber what the chain told us."""
    ds_ingest.seed_tokens(session, [{
        "token_address": TOKEN, "decimals": 9, "created_block": 1,
        "created_ts": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "pair_address": "0x" + "11" * 20, "quote_address": "0x" + "22" * 20,
        "dex": "uniswap-v3",
    }], chain="base", as_of_ts=datetime(2026, 1, 2, tzinfo=timezone.utc))
    session.flush()

    ds_ingest.enrich(session, ds_source(), [TOKEN], chain="base")

    token = session.get(Token, {"address": TOKEN, "chain": "base"})
    session.refresh(token)
    assert token.decimals == 9, "a known decimals was overwritten by an unknown one"


# ---- x -------------------------------------------------------------------

def x_source(tmp_path, budget: Budget | None = None, **kw) -> xapi.XSource:
    budget = budget or Budget(max_calls=5)
    return xapi.XSource(budget, cache_dir=tmp_path, **kw)


def test_x_refuses_to_run_when_it_is_switched_off(tmp_path):
    src = x_source(tmp_path, bearer="pretend-token")

    with pytest.raises(xapi.XDisabled):
        src.search(None, "from:someone", max_results=10)

    with pytest.raises(xapi.XDisabled):
        # Even asking for the network explicitly is not enough: X_ENABLED
        # is the second lock and it is off by default.
        src.search(None, "from:someone", max_results=10, allow_network=True)


def test_x_replays_a_cached_response_without_a_network(tmp_path):
    query, n = "$PEPPER", 10
    payload = load("x_search_recent.json")
    (tmp_path / f"{xapi.cache_key(query, max_results=n)}.json").write_text(
        json.dumps(payload), encoding="utf8")

    budget = Budget(max_calls=5)
    got = x_source(tmp_path, budget).search(None, query, max_results=n)

    assert got["_cache"] == "hit"
    assert len(got["data"]) == 3
    assert budget.requests == 0, "a cache hit must not be charged as a request"


def test_x_post_budget_defaults_to_zero_posts():
    assert Config().x_post_budget == 0
    assert Config().x_enabled is False


def test_x_stops_before_spending_past_its_ceiling(session, tmp_path):
    """The ceiling is a count of posts for the whole project, read from the
    ledger so a restart cannot forget what has been spent."""
    from blocklens.store import write

    period = Budget.period()
    write.bump_budget(session, source="x", period=period, requests=1, compute_units=95)
    session.flush()

    cfg = Config(x_post_budget=100, x_enabled=True)
    src = xapi.XSource(Budget(config=cfg, max_calls=5), config=cfg,
                       cache_dir=tmp_path, bearer="pretend-token")

    with pytest.raises(BudgetExhausted) as e:
        src.search(session, "$PEPPER", max_results=10, allow_network=True)
    assert "95 + 10 > 100" in str(e.value)


def test_posts_parse_into_rows_without_a_network_or_a_database():
    rows = xapi.posts_from(load("x_search_recent.json"))

    assert len(rows) == 3
    assert rows[0]["post_id"] == "1799000000000000001"
    assert rows[0]["likes"] == 97
    assert rows[0]["created_ts"] == datetime(2026, 10, 9, 14, 3, 11, tzinfo=timezone.utc)
    # Cashtags are normalised, so $pepper and $PEPPER are one tag.
    assert rows[1]["cashtags"] == ["BRETT", "PEPPER"]
    assert rows[2]["cashtags"] == []
