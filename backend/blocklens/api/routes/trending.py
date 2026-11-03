"""Trending Tokens, served: GeckoTerminal ranking, DexScreener prices and
GoPlus holders, fetched by the API once for every viewer."""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException

from .. import market
from ..contract import SymbolsResponse, TrendingResponse
from ..upstream import UpstreamError

router = APIRouter()


@router.get("/api/trending", response_model=TrendingResponse, response_model_exclude_unset=True)
def trending(window: Literal["m5", "h1", "h6", "h24"] = "h24", pages: int = 2) -> dict:
    try:
        return market.trending(window, max(1, min(pages, 5)))
    except UpstreamError as e:
        # no ranking has ever loaded: the front end falls back to its sample
        raise HTTPException(503, f"trending unavailable: {e}") from e


@router.get("/api/symbols", response_model=SymbolsResponse, response_model_exclude_unset=True)
def symbols(tokens: str = "") -> dict:
    """`tokens` is a comma-separated list of addresses, at most 120."""
    want = [t.strip().lower() for t in tokens.split(",") if t.strip()][:120]
    return {"provenance": "live", "symbols": market.symbols(want)}
