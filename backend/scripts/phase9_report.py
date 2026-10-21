"""Phase 9 — the paper agent's record, once it passed its floor.

    python -m scripts.phase9_report        # -> reports/paper_agent.{json,md}

Section 1 is the pre-registered result (DECISIONS.md, Phase 9), exactly as
`resolver.paper_agent` computes it. Everything after it is **post hoc**:
added after the headline was seen, to say what the headline rests on.

* Cap dependence: the same policies with the per-trade cap at 10 (the
  pre-registered value), 5, 2 and 1, and with capped trades dropped.
* Model vs launch type: AGENT buys launchpad launches with risk < 0.2.
  LAUNCHPAD buys every launchpad launch, with no model. If AGENT does not
  beat LAUNCHPAD, the result is the launch-type rule, not the model.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from sqlalchemy import text

from blocklens.live import resolver as rv
from blocklens.store.db import session_factory

OUT = Path(__file__).resolve().parents[1] / "reports"
SEED = 20261021
COST = rv.COSTS["headline"]


def rows(s) -> list[dict]:
    q = s.execute(text("""
        select risk, launch_type, price_6h_vs_cutoff, reserve_cutoff, reserve_6h, launch_ts
        from live_prediction
        where chain = :c and status = 'scored' and resolved_6h_at is not null
          and scored_at <= launch_ts + interval '6 hours'
    """), {"c": rv.CHAIN}).all()
    out = []
    for risk, kind, ratio, rc, r6, ts in q:
        ref = max(float(rc or 0), float(r6 or 0))
        pulled = ref > 0 and r6 is not None and float(r6) <= rv.PULLED_AT * ref
        out.append({"risk": risk, "kind": kind, "ratio": ratio, "pulled": pulled, "ts": ts})
    return out


def ret(t: dict, cap: float | None) -> float | None:
    if t["pulled"]:
        return -1.0
    if t["ratio"] is None:
        return None
    r = float(t["ratio"]) * (1 - COST) - 1
    return r if cap is None else min(r, cap)


POLICIES = {
    "AGENT": lambda t: t["risk"] is not None and t["risk"] < rv.AGENT_MAX_RISK
                       and t["kind"] == "launchpad",
    "CONTROL": lambda t: True,
    "LAUNCHPAD": lambda t: t["kind"] == "launchpad",
    "LAUNCHPAD_REJECTED": lambda t: t["kind"] == "launchpad" and t["risk"] is not None
                                    and t["risk"] >= rv.AGENT_MAX_RISK,
    "SELF_DEPLOYED": lambda t: t["kind"] == "self-deployed",
}


def summary(a: np.ndarray, cap: float | None) -> dict:
    if not len(a):
        return {"trades": 0}
    return {"trades": len(a), "mean": round(float(a.mean()), 4),
            "median": round(float(np.median(a)), 4),
            "hit_rate": round(float((a > 0).mean()), 4),
            "total": round(float(a.sum()), 4),
            "at_cap": int((a >= cap).sum()) if cap is not None else None}


def diff_ci(a: np.ndarray, b: np.ndarray, rng) -> list[float]:
    d = [rng.choice(a, len(a)).mean() - rng.choice(b, len(b)).mean() for _ in range(4000)]
    return [round(float(np.percentile(d, 2.5)), 4), round(float(np.percentile(d, 97.5)), 4)]


def returns(ts: list[dict], pick, cap) -> np.ndarray:
    return np.array([r for t in ts if pick(t) for r in [ret(t, cap)] if r is not None])


def main() -> None:
    with session_factory()() as s:
        headline = rv.paper_agent(s)
        ts = rows(s)
    rng = np.random.default_rng(SEED)

    caps = {}
    for label, cap in (("cap_10", 10.0), ("cap_5", 5.0), ("cap_2", 2.0), ("cap_1", 1.0)):
        pol = {n: summary(returns(ts, p, cap), cap) for n, p in POLICIES.items()}
        pol["agent_minus_control_ci"] = diff_ci(returns(ts, POLICIES["AGENT"], cap),
                                                returns(ts, POLICIES["CONTROL"], cap), rng)
        pol["agent_minus_launchpad_ci"] = diff_ci(returns(ts, POLICIES["AGENT"], cap),
                                                  returns(ts, POLICIES["LAUNCHPAD"], cap), rng)
        caps[label] = pol

    # Dropping the trades that reached the pre-registered cap entirely.
    no_cap = {}
    for n, p in POLICIES.items():
        a = returns(ts, p, 10.0)
        no_cap[n] = summary(a[a < 10.0], None)
    ag = returns(ts, POLICIES["AGENT"], 10.0)
    co = returns(ts, POLICIES["CONTROL"], 10.0)
    lp = returns(ts, POLICIES["LAUNCHPAD"], 10.0)
    no_cap["agent_minus_control_ci"] = diff_ci(ag[ag < 10], co[co < 10], rng)
    no_cap["agent_minus_launchpad_ci"] = diff_ci(ag[ag < 10], lp[lp < 10], rng)

    span = [min(t["ts"] for t in ts).isoformat(), max(t["ts"] for t in ts).isoformat()] if ts else None
    doc = {"generated_at": datetime.now(timezone.utc).isoformat(),
           "launches": span, "timely_resolved_scored": len(ts),
           "pre_registered": headline,
           "post_hoc": {"by_cap": caps, "capped_trades_dropped": no_cap}}
    OUT.mkdir(exist_ok=True)
    (OUT / "paper_agent.json").write_text(json.dumps(doc, indent=2, default=str), encoding="utf8")
    print(json.dumps(doc["post_hoc"], indent=1, default=str))
    print("launches", span, "rows", len(ts))


if __name__ == "__main__":
    main()
