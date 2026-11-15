"""Is the system up, and what is it running? Database, model, scorer and the
three market sources. Always 200: the body says what is wrong."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter
from sqlalchemy import text

from ...store.db import session_factory
from ..contract import HealthResponse
from ..deps import STATE
from ..upstream import UPSTREAM, UpstreamError

router = APIRouter()

# A cheap request per source, cached for five minutes, made only when the
# source has not been called recently: health must not spend the budget.
PROBES = {"geckoterminal": "/networks?page=1", "dexscreener": "/token-profiles/latest/v1",
          "goplus": "/api/v1/supported_chains"}
PROBE_TTL = 300


def _probe() -> None:
    now = datetime.now(timezone.utc)
    for src, path in PROBES.items():
        st = UPSTREAM.stats[src]
        recent = st.last_at and (now - datetime.fromisoformat(st.last_at)).total_seconds() < PROBE_TTL
        if not recent:
            try:
                UPSTREAM.get(src, path, PROBE_TTL)
            except UpstreamError:
                pass


@router.get("/api/health", response_model=HealthResponse, response_model_exclude_unset=True)
def health(probe: bool = True) -> dict:
    db = {"ok": True}
    try:
        with session_factory()() as s:
            s.execute(text("select 1"))
    except Exception as e:  # noqa: BLE001
        db = {"ok": False, "error": f"{type(e).__name__}: {str(e)[:160]}"}
    sc = STATE.scorer
    snap = sc.snapshot() if sc else {}
    if probe:
        _probe()
    return {
        "ok": db["ok"] and sc is not None,
        "database": db,
        "model": {"loaded": sc is not None, "version": sc.meta["version"] if sc else None},
        "scorer": {"running": bool(sc and sc.running), "lastRun": snap.get("last_run"),
                   "lastError": snap.get("last_error"), "scannedToBlock": snap.get("scanned_to_block"),
                   "tracked": len(snap.get("launches", []))},
        "alerts": {"enabled": bool(sc and sc.notifier.enabled), "sent": sc.notifier.sent if sc else 0,
                   "lastError": sc.notifier.last_error if sc else None},
        "upstream": UPSTREAM.health(),
    }
