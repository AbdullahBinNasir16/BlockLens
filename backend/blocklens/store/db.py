"""Engine and session plumbing. Nothing here writes rows."""
from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from ..config import CONFIG

_engine: Engine | None = None
_Session: sessionmaker[Session] | None = None


def engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = create_engine(CONFIG.database_url, pool_pre_ping=True, future=True)
    return _engine


def session_factory() -> sessionmaker[Session]:
    global _Session
    if _Session is None:
        _Session = sessionmaker(bind=engine(), expire_on_commit=False, future=True)
    return _Session


@contextmanager
def session_scope() -> Iterator[Session]:
    s = session_factory()()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()


def database_available() -> bool:
    try:
        with engine().connect() as c:
            c.execute(text("select 1"))
        return True
    except Exception:  # noqa: BLE001
        return False


def has_timescaledb() -> bool:
    try:
        with engine().connect() as c:
            return bool(c.execute(
                text("select 1 from pg_extension where extname='timescaledb'")
            ).first())
    except Exception:  # noqa: BLE001
        return False
