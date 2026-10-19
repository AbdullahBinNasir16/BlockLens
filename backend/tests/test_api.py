"""The API serves the feed with its validation record, and refuses junk."""
from __future__ import annotations

import os

import pytest

os.environ["BLOCKLENS_LIVE"] = "0"        # no background loop, no network

from fastapi.testclient import TestClient  # noqa: E402

from blocklens.api.app import app  # noqa: E402


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def test_every_feed_response_carries_the_validation_record(client):
    r = client.get("/api/launches")
    assert r.status_code == 200
    v = r.json()["model"]["validation"]
    assert {"in_period", "out_of_time", "regime_check"} <= set(v)


def test_token_lookup_rejects_a_non_address(client):
    assert client.get("/api/token/not-an-address").status_code == 400


def test_untracked_token_says_so(client):
    r = client.get("/api/token/0x" + "0" * 39 + "1")
    assert r.status_code == 200 and r.json()["tracked"] is False


def test_forward_record_endpoint_answers(client):
    r = client.get("/api/forward")
    assert r.status_code == 200 and isinstance(r.json(), dict)
