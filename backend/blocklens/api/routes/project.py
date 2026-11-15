"""The live half of a token page: market, security and the model's risk.
Each section carries its own provenance and fails on its own: a GoPlus
outage does not take the market section down with it."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import market
from ..contract import ProjectLiveResponse
from ..deps import address, db_call, get_session
from ..upstream import UpstreamError
from .token_risk import lookup

router = APIRouter()


@router.get("/api/project/{addr}", response_model=ProjectLiveResponse,
            response_model_exclude_unset=True)
def project(addr: str, s: Session = Depends(get_session)) -> dict:
    a = address(addr)
    out: dict = {"address": a}
    try:
        out["market"] = {"provenance": "live", "data": market.token_market(a)}
    except UpstreamError as e:
        out["market"] = {"provenance": "live", "data": None, "error": str(e)}
    try:
        out["security"] = {"provenance": "live", "data": market.security(a)}
    except UpstreamError as e:
        out["security"] = {"provenance": "live", "data": None, "error": str(e)}
    out["risk"] = db_call(lambda db: lookup(a, db), s)
    return out
