"""Test plumbing: a real PostgreSQL, and no network anywhere.

The store tests run against a real database rather than SQLite, because the
write gate's idempotency proof depends on PostgreSQL specifics — `ON
CONFLICT DO UPDATE` and the `xmax = 0` trick that tells an insert from an
update. Proving it on a different engine would prove nothing about the one
we ship.

Every test gets a transaction that is rolled back afterwards, so the suite
leaves no rows behind and the order of tests cannot matter.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import httpx
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from blocklens.config import CONFIG
from blocklens.store.models import Base

FIXTURES = Path(__file__).parent / "fixtures"

def _test_url() -> str:
    """The configured database with `_test` appended to its name.

    Split from the right: the database name is the last path segment, and
    the username in the URL is usually the same word.
    """
    head, _, name = CONFIG.database_url.rpartition("/")
    return f"{head}/{name}_test"


TEST_URL = os.environ.get("TEST_DATABASE_URL", _test_url())


def load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf8"))


@pytest.fixture(scope="session")
def engine():
    # An explicit connect timeout, because without one a stopped database
    # does not make the suite skip — it makes it hang. That happened: the
    # machine restarted, PostgreSQL was down, and `pytest -q` sat waiting
    # instead of reporting the skip it was written to report.
    eng = create_engine(TEST_URL, future=True,
                        connect_args={"connect_timeout": 3})
    try:
        with eng.connect() as c:
            c.execute(text("select 1"))
    except Exception as e:  # noqa: BLE001
        pytest.skip(f"no test database at {TEST_URL}: {e}")
    # The schema comes from the models rather than from Alembic: this is a
    # scratch database, and the migration is verified separately by actually
    # running it against the real one.
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture
def session(engine) -> Session:
    """A session on a transaction that is always rolled back."""
    conn = engine.connect()
    tx = conn.begin()
    s = Session(bind=conn, expire_on_commit=False, future=True)
    try:
        yield s
    finally:
        s.close()
        tx.rollback()
        conn.close()


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    """Make a real request impossible, so a test that leaks one fails loudly
    instead of quietly passing against the live API.

    The block is at the transport, not at `Client.request`: a MockTransport
    serving a recorded fixture has to keep working, and only a real socket
    is forbidden. Autouse, because remembering to ask for it is exactly the
    kind of thing that gets forgotten in the test that needed it most.
    """
    def forbidden(self, request, *a, **kw):
        raise AssertionError(
            f"a test attempted a real network call: {request.method} {request.url}"
        )

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", forbidden)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", forbidden)
    return True


def mock_client(routes: dict[str, object]) -> httpx.Client:
    """An httpx client that serves recorded payloads and nothing else.

    `routes` maps a substring of the URL to the JSON to return. An
    unmatched request is an error, not an empty response, so a test cannot
    pass by accident when the code calls something unexpected.
    """
    def handler(request: httpx.Request) -> httpx.Response:
        for needle, payload in routes.items():
            if needle in str(request.url):
                return httpx.Response(200, json=payload)
        raise AssertionError(f"unrouted request in test: {request.method} {request.url}")

    return httpx.Client(transport=httpx.MockTransport(handler))


def rpc_client(result_for: dict[str, object]) -> httpx.Client:
    """A JSON-RPC client dispatching on the method in the request body."""
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        method = body.get("method")
        if method not in result_for:
            raise AssertionError(f"unrouted rpc method in test: {method}")
        value = result_for[method]
        if callable(value):
            value = value(body.get("params"))
        return httpx.Response(200, json={"jsonrpc": "2.0", "id": body.get("id"),
                                         "result": value})

    return httpx.Client(transport=httpx.MockTransport(handler))
