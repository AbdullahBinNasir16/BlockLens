"""The model's score for one token, only where the model was built to give
one (DECISIONS.md, Phase 7 serving rule)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import risk
from ..contract import TokenRiskResponse
from ..deps import address, db_call, get_session, scorer

router = APIRouter()


def lookup(a: str, s: Session | None) -> dict:
    sc = scorer()
    snap = sc.snapshot()
    return risk.token_risk(s, a, meta=sc.meta, forward=snap["forward"], tracked=sc.token(a),
                           base_rate=sc.explainer.base_rate)


@router.get("/api/token-risk/{addr}", response_model=TokenRiskResponse,
            response_model_exclude_unset=True)
def token_risk(addr: str, s: Session = Depends(get_session)) -> dict:
    a = address(addr)
    return db_call(lambda db: lookup(a, db), s)
