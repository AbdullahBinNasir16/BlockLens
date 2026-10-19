"""The BlockLens API: what the front end reads instead of fixtures.

    uvicorn blocklens.api.app:app --port 8000

Phase 7 starts small and honest: the live launch feed and its model, and a
per-token lookup into it. Every response carries the model's validation
record, so no score can be shown without it.
"""
from __future__ import annotations

import os
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

from ..live.scorer import Scorer

_scorer: Scorer | None = None


@asynccontextmanager
async def lifespan(_app: FastAPI):
    global _scorer
    _scorer = Scorer()
    if os.environ.get("BLOCKLENS_LIVE", "1") == "1":
        threading.Thread(target=_scorer.run_forever, name="live-scorer", daemon=True).start()
    yield


app = FastAPI(title="BlockLens API", version="0.1.0", lifespan=lifespan)


def _s() -> Scorer:
    if _scorer is None:
        raise HTTPException(503, "scorer not started")
    return _scorer


@app.get("/api/health")
def health() -> dict:
    s = _s()
    snap = s.snapshot()
    return {"ok": True, "last_run": snap["last_run"], "last_error": snap["last_error"],
            "scanned_to_block": snap["scanned_to_block"], "tracked": len(snap["launches"])}


@app.get("/api/model")
def model() -> dict:
    return _s().meta


@app.get("/api/launches")
def launches() -> dict:
    return _s().snapshot()


@app.get("/api/forward")
def forward() -> dict:
    """The pre-registered forward record (DECISIONS.md, Phase 8)."""
    return _s().snapshot()["forward"] or {}


@app.get("/api/token/{address}")
def token(address: str) -> dict:
    if not (address.startswith("0x") and len(address) == 42):
        raise HTTPException(400, "not a contract address")
    t = _s().token(address)
    return {"tracked": t is not None, "launch": t, "model": _s().meta["validation"]}
