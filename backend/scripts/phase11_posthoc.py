"""Phase 11, post hoc (2026-11-25): what the evaluation set is made of.

    python -m scripts.phase11_posthoc     # -> reports/shadow_scores_posthoc.json

Written **after** the pre-registered result (`scripts/phase11_shadow.py`)
was seen. It changes nothing in that result. It splits the evaluation set
by one launch family and reruns the same evaluation on each part.

The family: a Uniswap V4 pool whose token reserve at minute 5 is about
1.5 B tokens (1.49e27 to 1.50e27 base units). It is the scam template first
recorded on 3 Nov (DECISIONS.md, 2026-11-16): seed 1.5 B tokens, trade for
about two hours, then sell 500 M tokens into the pool. The earlier tag (an
exact x34,600 minute-5 run-up) misses later variants, whose seeding swap
differs; the seed size does not.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from sklearn.metrics import average_precision_score
from sqlalchemy import text

from blocklens.live import resolver as rv
from blocklens.live import shadow
from blocklens.store.db import session_factory
from scripts.phase11_shadow import EVAL_FROM, FIT_BEFORE, PARAMS

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "shadow_scores_posthoc.json"
FAMILY_SQL = "(dex = 'uniswap-v4' and reserve_cutoff between 1.49e27 and 1.50e27)"


def load(s, where: str, ts: str) -> list[tuple[shadow.Row, bool, str]]:
    q = s.execute(text(f"""
        select risk, launch_type, buyer_loss, reserve_cutoff, reserve_6h, coalesce({FAMILY_SQL}, false)
        from live_prediction
        where chain = :c and status = 'scored' and buyer_loss is not null
          and scored_at <= launch_ts + interval '6 hours'
          and launch_ts {where} cast(:ts as timestamptz) and {rv.VALID_SQL}
    """), {"c": rv.CHAIN, "ts": ts, **rv.VALID_PARAMS}).all()
    out = []
    for risk, kind, y, rc, r6, fam in q:
        ref = max(float(rc or 0), float(r6 or 0))
        pulled = ref > 0 and r6 is not None and float(r6) <= rv.PULLED_AT * ref
        out.append((shadow.Row(risk=float(risk), self_deployed=kind == "self-deployed",
                               buyer_loss=bool(y), pulled_6h=pulled), bool(fam), kind))
    return out


def describe(rows) -> dict:
    by = {}
    for fam in (True, False):
        for kind in ("launchpad", "self-deployed"):
            rs = [r for r, f, k in rows if f == fam and k == kind]
            if rs:
                by[f"{'family' if fam else 'other'}/{kind}"] = {
                    "n": len(rs), "buyer_losses": sum(r.buyer_loss for r in rs),
                    "loss_rate": round(sum(r.buyer_loss for r in rs) / len(rs), 4),
                    "mean_v1_risk": round(float(np.mean([r.risk for r in rs])), 4)}
    return by


def v1_pr_auc(rs: list[shadow.Row]):
    y = [int(r.buyer_loss) for r in rs]
    return round(float(average_precision_score(y, [r.risk for r in rs])), 4) if 0 < sum(y) < len(y) else None


def main() -> None:
    p = json.loads(PARAMS.read_text(encoding="utf8"))
    with session_factory()() as s:
        fit_rows = load(s, "<", FIT_BEFORE)
        ev = load(s, ">=", EVAL_FROM)
    parts = {"all": [r for r, _, _ in ev], "family": [r for r, f, _ in ev if f],
             "without_family": [r for r, f, _ in ev if not f]}
    res = {}
    for name, rs in parts.items():
        e = shadow.evaluate(p, rs)
        e.pop("reportable", None)  # the floor belongs to the pre-registered result only
        e["v1_pr_auc_buyer_loss"] = v1_pr_auc(rs)
        e["v1_mean_risk"] = round(float(np.mean([r.risk for r in rs])), 4) if rs else None
        res[name] = e
    doc = {"generated_at": datetime.now(timezone.utc).isoformat(), "post_hoc": True,
           "family_rule": FAMILY_SQL, "eval_from": EVAL_FROM,
           "composition": {"fitting_set": describe(fit_rows), "evaluation_set": describe(ev)},
           "by_part": res}
    OUT.write_text(json.dumps(doc, indent=1), encoding="utf8")
    print(json.dumps(doc["composition"], indent=1))
    for name, e in res.items():
        print(name, {"n": e["resolved"], "losses": e["losses"], "v1_pr_auc": e["v1_pr_auc_buyer_loss"],
                     "A": {k: e["A"][k] for k in ("brier", "brier_constant", "brier_v1", "mean_predicted", "observed", "pass")},
                     "B": {k: e["B"][k] for k in ("pr_auc", "pr_auc_launch_type", "pr_auc_minus_launch_type_ci", "brier", "brier_constant", "pass")}})


if __name__ == "__main__":
    main()
