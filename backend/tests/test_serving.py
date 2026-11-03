"""Phase 7, the serving layer: every route answers in the contract, the model
is never served outside its scope, and the contract has not drifted."""
from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

os.environ["BLOCKLENS_LIVE"] = "0"

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from blocklens.api import contract as C  # noqa: E402
from blocklens.api import market, risk  # noqa: E402
from blocklens.api import screener as screener_mod  # noqa: E402
from blocklens.api.app import app, get_session  # noqa: E402
from blocklens.api.upstream import UPSTREAM, SourceStats  # noqa: E402
from tests.conftest import mock_client  # noqa: E402

BACKEND = Path(__file__).resolve().parents[1]
TOKEN = "0x" + "ab" * 20
POOL = "0x" + "cd" * 20

GT = {"data": [{"id": "base_" + POOL, "attributes": {
    "address": POOL, "name": "TEST / WETH", "base_token_price_usd": "0.5",
    "price_change_percentage": {"h24": "12.5"}, "volume_usd": {"h24": "1000"},
    "transactions": {"h24": {"buys": 10, "sells": 4, "buyers": 7, "sellers": 3}},
    "reserve_in_usd": "5000", "fdv_usd": "90000", "market_cap_usd": None,
    "pool_created_at": "2026-11-01T00:00:00Z"},
    "relationships": {"base_token": {"data": {"id": "base_" + TOKEN}},
                      "quote_token": {"data": {"id": "base_weth"}},
                      "dex": {"data": {"id": "uniswap-v3-base"}}}}],
    "included": [{"id": "base_" + TOKEN, "attributes": {"address": TOKEN, "name": "Test", "symbol": "test"}},
                 {"id": "base_weth", "attributes": {"symbol": "WETH"}}]}
DS_PAIRS = {"pairs": [{"pairAddress": POOL, "priceUsd": "0.6", "priceChange": {"h24": 20},
                       "volume": {"h24": 1500}, "txns": {"h24": {"buys": 11, "sells": 5}},
                       "liquidity": {"usd": 5100}, "fdv": 95000}]}
DS_TOKEN = [{"pairAddress": POOL, "dexId": "uniswap", "baseToken": {"address": TOKEN, "name": "Test", "symbol": "test"},
             "quoteToken": {"symbol": "WETH"}, "priceUsd": "0.6", "priceChange": {"h24": 20},
             "volume": {"h24": 1500}, "txns": {"h24": {"buys": 11, "sells": 5}},
             "liquidity": {"usd": 5100}, "fdv": 95000, "pairCreatedAt": 1761955200000}]
GOPLUS = {"code": 1, "result": {TOKEN: {"holder_count": "120", "is_honeypot": "0",
                                        "holders": [{"percent": "0.1"}, {"percent": "0.05"}]}}}
ROUTES = {"trending_pools": GT, "latest/dex/pairs": DS_PAIRS, "tokens/v1/base": DS_TOKEN,
          "token_security": GOPLUS, "/networks?page": {"data": []},
          "token-profiles": [], "supported_chains": {"code": 1, "result": []}}


@pytest.fixture()
def upstream(monkeypatch):
    """The shared upstream, on recorded payloads, with a clean cache."""
    monkeypatch.setattr(UPSTREAM, "client", mock_client(ROUTES))
    monkeypatch.setattr(UPSTREAM, "_cache", {})
    monkeypatch.setattr(UPSTREAM, "stats", {s: SourceStats() for s in UPSTREAM.stats})
    monkeypatch.setattr(market, "_ranking", {})
    return UPSTREAM


@pytest.fixture()
def client(session, upstream):
    app.dependency_overrides[get_session] = lambda: session
    risk._forward.update(doc=None, at=0.0)
    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.clear()


# ---- every route answers in the contract ------------------------------------

def test_trending_validates_against_the_contract(client):
    r = client.get("/api/trending?window=h24&pages=1")
    assert r.status_code == 200
    d = C.TrendingResponse.model_validate(r.json())
    assert d.provenance.value == "live" and d.pools[0].symbol == "TEST"
    assert d.pools[0].price == 0.6                      # DexScreener's price over the ranking's
    assert d.pools[0].makers.h24 == 10


def test_trending_is_cached_for_every_viewer(client, upstream):
    client.get("/api/trending?window=h24&pages=1")
    calls = upstream.stats["geckoterminal"].calls
    client.get("/api/trending?window=h24&pages=1")
    assert upstream.stats["geckoterminal"].calls == calls
    assert upstream.stats["geckoterminal"].cache_hits >= 1


def test_project_validates_and_carries_section_provenance(client):
    r = client.get(f"/api/project/{TOKEN}")
    assert r.status_code == 200
    d = C.ProjectLiveResponse.model_validate(r.json())
    assert d.market.provenance.value == "live" and d.market.data.symbol == "TEST"
    assert d.security.data.holders == 120 and d.security.data.honeypot is False
    assert abs(d.security.data.top10Pct - 15.0) < 1e-9


def test_health_validates_and_reports_each_source(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    d = C.HealthResponse.model_validate(r.json())
    assert d.model.loaded and d.model.version == "buyer-loss-v1"
    assert set(d.upstream) == {"geckoterminal", "dexscreener", "goplus"}
    assert d.alerts.enabled is False and d.alerts.sent == 0


def test_screener_validates_against_the_contract(client, monkeypatch):
    doc = {"provenance": "live", "asOf": "2026-11-03T00:00:00+00:00", "unit": "ETH",
           "tokens": [{"address": TOKEN, "symbol": "", "name": "", "launchedAt": 1.0, "wallets": 1}],
           "wallets": [{"address": "0x" + "01" * 20, "firstSeen": 1.0, "fundingSource": "unknown",
                        "clusterSize": 1, "smartMoney": False, "insiderLinked": False,
                        "positions": [{"projectId": TOKEN, "chain": "base", "firstBuy": 1.0,
                                       "lastSell": None, "buys": 1, "sells": 0, "invested": 0.1,
                                       "soldFraction": 0.0, "proceeds": 0.0, "remainingValue": 0.1,
                                       "entryDelay": 0.0, "averagedDown": False, "soldFirstPump": False,
                                       "wentToZero": False, "honeypot": False}]}]}
    monkeypatch.setattr(screener_mod, "corpus", lambda f: (doc, "ready"))
    r = client.get("/api/screener")
    assert r.status_code == 200
    C.ScreenerResponse.model_validate(r.json())


def test_screener_says_so_while_building(client, monkeypatch):
    monkeypatch.setattr(screener_mod, "corpus", lambda f: (None, "building"))
    assert client.get("/api/screener").status_code == 503


# ---- the model is not served out of distribution ----------------------------

def _prediction(session, token: str, status: str, risk_: float | None, launched: datetime):
    session.execute(text("""
        insert into live_prediction (token_address, chain, pool_key, dex, created_block, launch_ts,
            model_version, status, scored_at, risk, launch_type, explanation, recorded_at)
        values (:t, 'base', :p, 'uniswap-v3', 1, :lt, 'buyer-loss-v1', :st, :sa, :r, 'launchpad',
            cast(:x as jsonb), :lt)
    """), {"t": token, "p": POOL, "lt": launched, "st": status,
           "sa": launched + timedelta(minutes=5) if risk_ is not None else None, "r": risk_,
           "x": '{"base_rate": 0.3, "drivers": [{"feature": "t_buys", "label": "buys by minute 5", '
                '"value": 3, "display": "3", "contribution": 0.4, "direction": "raises"}]}'})
    session.flush()


def test_a_token_the_feed_never_saw_is_out_of_scope(client):
    r = client.get("/api/token-risk/0x" + "0" * 39 + "1")
    d = C.TokenRiskResponse.model_validate(r.json())
    assert d.state.value == "out_of_scope" and d.score is None
    assert "not trained on" in d.reason
    assert d.model.version == "buyer-loss-v1" and d.model.trainedOnLaunches == ["2026-01-20", "2026-07-16"]
    assert d.model.trainedAt == "2026-10-19"


def test_a_pool_seen_but_not_scored_says_why_and_shows_no_score(client, session):
    _prediction(session, TOKEN, "not scored: no trades in the first 5 minutes", None,
                datetime(2026, 10, 28, tzinfo=timezone.utc))
    d = C.TokenRiskResponse.model_validate(client.get(f"/api/token-risk/{TOKEN}").json())
    assert d.state.value == "not_scored" and d.score is None
    assert "no trades in the first 5 minutes" in d.reason


def test_a_scored_launch_carries_its_drivers_and_forward_band(client, session):
    _prediction(session, TOKEN, "scored", 0.74, datetime(2026, 11, 3, tzinfo=timezone.utc))
    risk._forward.update(doc={"since": "2026-10-19", "buyer_loss": {"reliability": [
        {"bin": "0.7-0.8", "n": 70, "mean_predicted": 0.75, "observed": 0.4857}]}}, at=1e18)
    d = C.TokenRiskResponse.model_validate(client.get(f"/api/token-risk/{TOKEN}").json())
    assert d.state.value == "scored" and d.score.risk == 0.74
    assert d.score.band.launches == 70 and d.score.band.losses == 34
    assert d.score.drivers[0].feature == "t_buys"


# ---- the contract itself ----------------------------------------------------

def test_the_backend_contract_matches_the_schema():
    r = subprocess.run([sys.executable, str(BACKEND / "scripts" / "contract.py"), "--check"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
