"""Phase 11 — shadow scores (DECISIONS.md, Phase 11, pre-registered).

    python -m scripts.phase11_shadow fit       # once -> data/models/shadow_v1.json
    python -m scripts.phase11_shadow report    # -> reports/shadow_scores.json

`fit` refuses to run twice: the parameters are fixed once, by protocol.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import text

from blocklens.live import resolver as rv
from blocklens.live import shadow
from blocklens.store.db import session_factory

ROOT = Path(__file__).resolve().parents[1]
PARAMS = ROOT / "data" / "models" / "shadow_v1.json"
REPORT = ROOT / "reports" / "shadow_scores.json"
FIT_BEFORE = "2026-11-03T12:00:00+05:00"
EVAL_FROM = "2026-11-04T00:00:00+05:00"


def load(s, where: str, ts: str) -> list[shadow.Row]:
    q = s.execute(text(f"""
        select risk, launch_type, buyer_loss, reserve_cutoff, reserve_6h
        from live_prediction
        where chain = :c and status = 'scored' and buyer_loss is not null
          and scored_at <= launch_ts + interval '6 hours'
          and launch_ts {where} cast(:ts as timestamptz)
    """), {"c": rv.CHAIN, "ts": ts}).all()
    out = []
    for risk, kind, y, rc, r6 in q:
        ref = max(float(rc or 0), float(r6 or 0))
        pulled = ref > 0 and r6 is not None and float(r6) <= rv.PULLED_AT * ref
        out.append(shadow.Row(risk=float(risk), self_deployed=kind == "self-deployed",
                              buyer_loss=bool(y), pulled_6h=pulled))
    return out


def fit() -> None:
    if PARAMS.exists():
        sys.exit(f"{PARAMS} exists: Phase 11 parameters are fitted once and never refitted.")
    with session_factory()() as s:
        rows = load(s, "<", FIT_BEFORE)
    p = shadow.fit(rows)
    p.update({"version": "shadow-v1", "protocol": "DECISIONS.md, Phase 11 (pre-registered 2026-11-03)",
              "over_model": "buyer-loss-v1", "fit_before": FIT_BEFORE, "eval_from": EVAL_FROM,
              "fitted_at": datetime.now(timezone.utc).isoformat()})
    PARAMS.write_text(json.dumps(p, indent=2), encoding="utf8")
    print(json.dumps(p, indent=2))


def report() -> None:
    p = json.loads(PARAMS.read_text(encoding="utf8"))
    with session_factory()() as s:
        rows = load(s, ">=", EVAL_FROM)
    doc = {"generated_at": datetime.now(timezone.utc).isoformat(), "params": p,
           "evaluation": shadow.evaluate(p, rows)}
    REPORT.write_text(json.dumps(doc, indent=2), encoding="utf8")
    e = doc["evaluation"]
    print({k: e[k] for k in ("resolved", "losses", "y_b_positives", "reportable")})
    if e["reportable"]:
        print("A:", {k: v for k, v in e["A"].items() if k != "reliability"})
        print("B:", {k: v for k, v in e["B"].items() if k != "reliability"})
    else:
        print("below the floor: no result yet")


if __name__ == "__main__":
    {"fit": fit, "report": report}[sys.argv[1]]()
