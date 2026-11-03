"""The wallet screener's real corpus (positions from the store)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ...store.db import session_factory
from .. import screener as corpus_mod
from ..contract import ScreenerResponse

router = APIRouter()


@router.get("/api/screener", response_model=ScreenerResponse, response_model_exclude_unset=True)
def screener() -> dict:
    doc, status = corpus_mod.corpus(session_factory)
    if doc is None:
        # the front end shows its sample corpus, badged, until this is ready
        raise HTTPException(503, f"screener corpus {status}")
    return doc
