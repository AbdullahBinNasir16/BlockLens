"""What every route needs: the running scorer, a database session, and an
address check. Kept apart from `app.py` so route modules can import it."""
from __future__ import annotations

from typing import Iterator

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..live.scorer import Scorer
from ..store.db import session_factory

CHAIN = "base"


class _State:
    scorer: Scorer | None = None


STATE = _State()


def scorer() -> Scorer:
    if STATE.scorer is None:
        raise HTTPException(503, "scorer not started")
    return STATE.scorer


def get_session() -> Iterator[Session]:
    """A database session per request. Tests override this with a session on
    a transaction that is rolled back afterwards."""
    try:
        s = session_factory()()
    except Exception as e:  # noqa: BLE001
        raise HTTPException(503, f"database unavailable: {type(e).__name__}") from e
    try:
        yield s
    finally:
        s.close()


def address(a: str) -> str:
    a = a.strip().lower()
    if not (a.startswith("0x") and len(a) == 42 and all(c in "0123456789abcdef" for c in a[2:])):
        raise HTTPException(400, "not a contract address")
    return a


def db_call(fn, s: Session):
    try:
        return fn(s)
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001 - a dead database is a 503, not a 500
        s.rollback()
        raise HTTPException(503, f"database error: {type(e).__name__}") from e
