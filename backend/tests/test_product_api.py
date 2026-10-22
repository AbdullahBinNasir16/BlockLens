"""Phase 10 endpoints: product state, the paper book and health, on a real
database (rolled back after every test), with the feed's own endpoints."""
from __future__ import annotations

import os

import pytest

os.environ["BLOCKLENS_LIVE"] = "0"

from fastapi.testclient import TestClient  # noqa: E402

from blocklens.api.app import app, get_session  # noqa: E402

ADDR = "0x" + "ab" * 20


@pytest.fixture()
def client(session):
    app.dependency_overrides[get_session] = lambda: session
    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.clear()


def test_watchlist_round_trip(client):
    assert client.get("/api/watchlist").json()["items"] == []
    r = client.post("/api/watchlist", json={"address": ADDR.upper(), "label": "test"})
    assert r.status_code == 201 and r.json()["created"] is True
    r = client.post("/api/watchlist", json={"address": ADDR, "note": "again"})
    assert r.json()["created"] is False                       # same row, updated
    items = client.get("/api/watchlist").json()["items"]
    assert [i["address"] for i in items] == [ADDR]
    assert items[0]["label"] == "test" and items[0]["note"] == "again"   # coalesced, not erased
    assert client.delete(f"/api/watchlist/{ADDR}").json()["removed"] is True
    assert client.delete(f"/api/watchlist/{ADDR}").status_code == 404


def test_watchlist_refuses_junk(client):
    assert client.post("/api/watchlist", json={"address": "nope"}).status_code == 400
    assert client.post("/api/watchlist", json={"address": ADDR, "chain": "solana"}).status_code == 400


def test_history_is_newest_first(client):
    for o in ("live", "profile", "tracked"):
        assert client.post("/api/history", json={"address": ADDR, "outcome": o}).status_code == 201
    items = client.get("/api/history?limit=2").json()["items"]
    assert [i["outcome"] for i in items] == ["tracked", "profile"]
    assert client.post("/api/history", json={"address": ADDR, "outcome": "guess"}).status_code == 422


def test_paper_book_and_health_answer_on_an_empty_log(client):
    b = client.get("/api/paper-agent/trades").json()
    assert b["trades"] == [] and b["cost"] == 0.03
    h = client.get("/api/model/health").json()
    assert h["days"] == [] and h["outages"] == [] and h["totals"]["logged"] == 0
    assert h["model"]["version"] == "buyer-loss-v1"


def test_explain_metadata_lists_every_feature(client):
    e = client.get("/api/explain").json()
    assert set(e["features"]) <= set(e["labels"]) and 0 < e["base_rate"] < 1


def test_stream_says_hello_then_pings(client):
    r = client.get("/api/stream?ticks=1")
    assert r.headers["content-type"].startswith("text/event-stream")
    lines = r.text.splitlines()
    assert lines[0] == "event: hello" and lines[1].startswith("data: ")
    assert ": ping" in lines
