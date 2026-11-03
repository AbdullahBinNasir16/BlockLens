"""The BlockLens API: what the front end reads instead of fixtures.

    uvicorn blocklens.api.app:app --port 8000

Phase 7 started small and honest: the live launch feed and its model, and a
per-token lookup into it. Every response carries the model's validation
record, so no score can be shown without it. Phase 10 adds the score's
anatomy, the paper agent's book, the system's own health, a push stream
for newly scored launches, and the product's state (watchlist, history).
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import threading
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..live import health as health_mod
from ..live import resolver
from ..live.scorer import Scorer
from ..store import write
from ..store.db import session_factory
from . import screener as screener_corpus
from .deps import CHAIN, STATE, get_session  # noqa: F401 - get_session is the tests' override point
from .deps import address as _address
from .deps import db_call as _db
from .deps import scorer as _s
from .routes import health as r_health
from .routes import project as r_project
from .routes import screener as r_screener
from .routes import token_risk as r_token_risk
from .routes import trending as r_trending

logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"),
                    format="%(asctime)s %(levelname)s %(name)s %(message)s")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    STATE.scorer = Scorer()
    if os.environ.get("BLOCKLENS_LIVE", "1") == "1":
        threading.Thread(target=STATE.scorer.run_forever, name="live-scorer", daemon=True).start()
        # the screener's corpus takes tens of seconds to build: start it now
        screener_corpus.corpus(session_factory)
    yield


app = FastAPI(title="BlockLens API", version="0.3.0", lifespan=lifespan)
# Phase 7: one route module per screen, each answering in the contract
for r in (r_health, r_trending, r_project, r_token_risk, r_screener):
    app.include_router(r.router)


# ---- the feed (Phase 7) ----------------------------------------------------

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
    a = _address(address)
    t = _s().token(a)
    return {"tracked": t is not None, "launch": t, "model": _s().meta["validation"]}


# ---- Phase 10: anatomy, book, health, stream -------------------------------

@app.get("/api/explain")
def explain_meta() -> dict:
    """What the explanations are made of: the base rate and the feature labels."""
    from ..live.explain import LABELS
    ex = _s().explainer
    return {"method": "tree SHAP, path-dependent; additive in log-odds",
            "base_rate": round(ex.base_rate, 4), "features": ex.features, "labels": LABELS}


@app.get("/api/paper-agent/trades")
def paper_trades(limit: int = 300, s: Session = Depends(get_session)) -> dict:
    limit = max(1, min(limit, 2000))
    trades = _db(lambda db: resolver.paper_trades(db, limit=limit), s)
    return {"protocol": "DECISIONS.md, Phase 9", "cost": resolver.COSTS["headline"],
            "cap": resolver.RETURN_CAP, "max_risk": resolver.AGENT_MAX_RISK, "trades": trades}


@app.get("/api/model/health")
def model_health(s: Session = Depends(get_session)) -> dict:
    out = _db(health_mod.health, s)
    snap = _s().snapshot()
    out["scorer"] = {"last_run": snap["last_run"], "last_error": snap["last_error"],
                     "scanned_to_block": snap["scanned_to_block"],
                     "tracked": len(snap["launches"])}
    out["model"] = {"version": _s().meta["version"], "trained": _s().meta.get("trained")}
    return out


@app.get("/api/stream")
async def stream(ticks: int = 0) -> StreamingResponse:
    """Server-sent events: `hello` once, then `scored` for each launch that
    reaches a verdict, and a comment ping to keep the connection open.
    `ticks` bounds the number of polls (0 = until the client goes away); a
    health check or a test asks for one."""
    async def gen():
        seen = {l["token"]: l["status"] for l in _s().snapshot()["launches"]}
        yield f"event: hello\ndata: {json.dumps({'tracked': len(seen)})}\n\n"
        n = 0
        while ticks <= 0 or n < ticks:
            for l in _s().snapshot()["launches"]:
                if l["status"] == "scored" and seen.get(l["token"]) != "scored":
                    yield f"event: scored\ndata: {json.dumps(l)}\n\n"
                seen[l["token"]] = l["status"]
            yield ": ping\n\n"
            n += 1
            if ticks <= 0 or n < ticks:
                await asyncio.sleep(5)

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# ---- Phase 10: product state ------------------------------------------------

class WatchIn(BaseModel):
    address: str
    chain: str = CHAIN
    label: str | None = Field(default=None, max_length=64)
    note: str | None = Field(default=None, max_length=2000)


class HistoryIn(BaseModel):
    address: str
    chain: str = CHAIN
    outcome: str = Field(pattern="^(profile|tracked|live)$")


def _watch_rows(s: Session) -> list[dict]:
    rows = s.execute(text("""
        select token_address, chain, label, note, added_at from watchlist_item
        order by added_at desc
    """)).all()
    return [{"address": a, "chain": c, "label": l, "note": n, "added_at": t.isoformat()}
            for a, c, l, n, t in rows]


@app.get("/api/watchlist")
def watchlist(s: Session = Depends(get_session)) -> dict:
    return {"items": _db(_watch_rows, s)}


@app.post("/api/watchlist", status_code=201)
def watch(body: WatchIn, s: Session = Depends(get_session)) -> dict:
    a = _address(body.address)
    if body.chain != CHAIN:
        raise HTTPException(400, "only base is supported")

    def go(db: Session):
        r = write.upsert_watchlist(db, token=a, chain=body.chain, label=body.label,
                                   note=body.note, as_of_ts=datetime.now(timezone.utc))
        db.commit()
        return r
    r = _db(go, s)
    return {"address": a, "chain": body.chain, "created": bool(r.inserted)}


@app.delete("/api/watchlist/{address}")
def unwatch(address: str, s: Session = Depends(get_session)) -> dict:
    a = _address(address)

    def go(db: Session):
        n = write.remove_watchlist(db, token=a, chain=CHAIN)
        db.commit()
        return n
    n = _db(go, s)
    if not n:
        raise HTTPException(404, "not on the watchlist")
    return {"address": a, "removed": True}


@app.get("/api/history")
def history(limit: int = 50, s: Session = Depends(get_session)) -> dict:
    limit = max(1, min(limit, 500))

    def go(db: Session):
        rows = db.execute(text("""
            select id, token_address, chain, outcome, opened_at from investigation
            order by opened_at desc, id desc limit :n
        """), {"n": limit}).all()
        return [{"id": i, "address": a, "chain": c, "outcome": o, "opened_at": t.isoformat()}
                for i, a, c, o, t in rows]
    return {"items": _db(go, s)}


@app.post("/api/history", status_code=201)
def record_investigation(body: HistoryIn, s: Session = Depends(get_session)) -> dict:
    a = _address(body.address)

    def go(db: Session):
        i = write.add_investigation(db, token=a, chain=body.chain, outcome=body.outcome,
                                    as_of_ts=datetime.now(timezone.utc))
        db.commit()
        return i
    return {"id": _db(go, s), "address": a}
