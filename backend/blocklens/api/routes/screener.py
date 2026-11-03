"""The wallet screener's real corpus (positions from the store).

The whole corpus is ~70k wallets and ~50 MB, too much for a browser. The
query logic only ever looks at wallets that traded the contracts in scope,
so the route answers in two steps: the token index alone, then, for a
search, the wallets with a position in the searched contracts (with all
their positions, so wallet-level figures stay whole)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ...store.db import session_factory
from .. import screener as corpus_mod
from ..contract import ScreenerResponse

router = APIRouter()
MAX_CONTRACTS = 10


@router.get("/api/screener", response_model=ScreenerResponse, response_model_exclude_unset=True)
def screener(contracts: str = "") -> dict:
    doc, status = corpus_mod.corpus(session_factory)
    if doc is None:
        # the front end shows its sample corpus, badged, until this is ready
        raise HTTPException(503, f"screener corpus {status}")
    if not doc["tokens"]:
        # a fresh install: the store holds no labelled research launches yet
        raise HTTPException(503, "the store holds no labelled research launches to screen")
    want = sorted({c.strip().lower() for c in contracts.split(",") if c.strip()})[:MAX_CONTRACTS]
    wallets = [w for w in doc["wallets"] if any(p["projectId"] in want for p in w["positions"])] if want else []
    return {"provenance": doc["provenance"], "asOf": doc["asOf"], "unit": doc["unit"],
            "tokens": doc["tokens"], "contracts": want, "wallets": wallets}
