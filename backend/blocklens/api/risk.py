"""`token_risk`: a model score only where the model was built to give one.

`buyer-loss-v1` judges a launch from its first five minutes, once, at launch
+ 5 minutes. Asked about a token that launched three months ago it would
still answer, and the answer would mean nothing. So a score is served only
for a launch the live scorer saw and scored at its own minute 5; everything
else gets an explicit state and a sentence saying why (DECISIONS.md,
Phase 7 serving rule).

A score is presented as what happened forward to launches scored in the
same band, not as the raw probability: the forward record showed the raw
probabilities run about four times too high (DECISIONS.md, Phase 8 result).
"""
from __future__ import annotations

import time
from datetime import timezone

from sqlalchemy import text
from sqlalchemy.orm import Session

from ..live import resolver

CHAIN = "base"
FORWARD_TTL_S = 600
_forward: dict = {"at": 0.0, "doc": None}


def forward_record(s: Session | None, live: dict | None) -> dict | None:
    """The scorer's last record, or the database's when the scorer has not
    ticked yet (a fresh start, or a test): the band must not vanish."""
    if live:
        return live
    if s is None:
        return None
    if _forward["doc"] is None or time.monotonic() - _forward["at"] > FORWARD_TTL_S:
        _forward.update(doc=resolver.scoreboard(s), at=time.monotonic())
    return _forward["doc"]


def _utc(dt) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

OUT_OF_SCOPE = (
    "The model judges a launch once, at launch + 5 minutes, from those five minutes only. "
    "It scores Base Uniswap V3/V4 pools that launched while the live feed was running "
    "(since {since}). This token was not seen launching, so a score now would be the model "
    "answering a question it was not trained on."
)


def model_card(meta: dict) -> dict:
    t = meta.get("trained_on") or {}
    return {"version": meta.get("version", "unknown"), "target": meta.get("target", ""),
            "appliesTo": meta.get("applies_to", ""),
            "trainedOnLaunches": list(t.get("launches") or []),
            "trainedOnTokens": int(t.get("tokens") or 0),
            "trainedAt": str(meta.get("trained", ""))[:10]}


def band(forward: dict | None, risk: float) -> dict | None:
    """The forward reliability bin that `risk` falls in, as counts."""
    bl = (forward or {}).get("buyer_loss") or {}
    for b in bl.get("reliability") or []:
        lo, hi = (float(x) for x in b["bin"].split("-"))
        if lo <= risk < hi or (hi >= 1.0 and risk <= 1.0 and lo <= risk):
            n = int(b["n"])
            return {"lo": lo, "hi": hi, "launches": n,
                    "losses": int(round(b["observed"] * n)), "observed": b["observed"],
                    "since": str((forward or {}).get("since") or "")[:10]}
    return None


def token_risk(s: Session | None, address: str, *, meta: dict, forward: dict | None,
               tracked: dict | None, base_rate: float) -> dict:
    card = model_card(meta)
    forward = forward_record(s, forward)
    since = str((forward or {}).get("since") or "2026-10-19")[:10]
    out = {"address": address, "provenance": "live", "model": card, "score": None}

    row = None
    if s is not None:
        row = s.execute(text("""
            select status, risk, launch_type, launch_ts, scored_at, explanation
            from live_prediction where chain = :c and token_address = :t
        """), {"c": CHAIN, "t": address}).first()

    if row is None and tracked is not None:
        if tracked.get("status") == "waiting for minute 5":
            return {**out, "state": "pending",
                    "reason": f"Launched {str(tracked.get('launch_ts'))[:16].replace('T', ' ')} UTC. "
                              "The model scores it once, at launch + 5 minutes."}
        return {**out, "state": "not_scored",
                "reason": _reason(tracked.get("status", ""), str(tracked.get("launch_ts", ""))[:10])}
    if row is None:
        return {**out, "state": "out_of_scope", "reason": OUT_OF_SCOPE.format(since=since)}

    status, risk, kind, launch_ts, scored_at, why = row
    if status != "scored" or risk is None:
        return {**out, "state": "not_scored", "reason": _reason(status, launch_ts.isoformat()[:10])}
    why = why or {}
    return {**out, "state": "scored",
            "reason": f"The live feed saw this pool open on {launch_ts.isoformat()[:10]} and scored it "
                      f"once, at launch + 5 minutes ({_utc(scored_at)}), "
                      "from what happened in those five minutes. The score describes that moment, "
                      "not the token today.",
            "score": {"risk": round(float(risk), 4), "launchType": kind,
                      "launchTs": launch_ts.isoformat(), "scoredAt": scored_at.isoformat(),
                      "band": band(forward, float(risk)),
                      "drivers": why.get("drivers") or [],
                      "rest": round(float(why.get("rest", 0.0)), 4),
                      "baseRate": round(float(why.get("base_rate", base_rate)), 4)}}


def _reason(status: str, day: str) -> str:
    """The feed watches pools, not tokens: a new pool for an old token is
    logged too, so the sentence says what was seen, a pool opening."""
    s = status.removeprefix("not scored: ")
    return (f"The live feed saw a pool for this token open on {day}, but did not score it: {s}. "
            "No score is shown.")
