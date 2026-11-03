"""Phase 8 — the forward record, once it passed its floor.

    python -m scripts.phase8_report        # -> reports/forward_validation.{json,md}

Section `pre_registered` is `resolver.scoreboard` exactly as fixed on
2026-10-19 (DECISIONS.md, Phase 8). Everything in `post_hoc` was added after
the headline was seen, to say what it rests on:

* the two fixed rule checkers (Phase 5 and Phase 6), scored on the same
  forward launches from the stored minute-5 features, as rankers;
* launch type alone as a ranker, and the model within each launch type;
* coverage: scored launches per day and the longest gap between them.
"""
from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from sklearn.metrics import average_precision_score, roc_auc_score
from sqlalchemy import text

from blocklens.live import resolver as rv
from blocklens.model import rulecheck, rulecheck_x
from blocklens.store.db import session_factory

OUT = Path(__file__).resolve().parents[1] / "reports"
SEED = 20261103
BOOT = 1000


def rows(s) -> list[dict]:
    q = s.execute(text("""
        select risk, launch_type, buyer_loss, features, launch_ts, reserve_cutoff, reserve_6h
        from live_prediction
        where chain = :c and status = 'scored' and buyer_loss is not null
          and scored_at <= launch_ts + interval '6 hours'
    """), {"c": rv.CHAIN}).all()
    out = []
    for risk, kind, y, feats, ts, rc, r6 in q:
        f = feats if isinstance(feats, dict) else json.loads(feats or "{}")
        ref = max(float(rc or 0), float(r6 or 0))
        pulled = ref > 0 and r6 is not None and float(r6) <= rv.PULLED_AT * ref
        out.append({"p": float(risk), "kind": kind, "y": int(bool(y)), "f": f, "ts": ts,
                    "pulled_6h": pulled})
    return out


def pr(y, s) -> float | None:
    return float(average_precision_score(y, s)) if 0 < y.sum() < len(y) else None


def roc(y, s) -> float | None:
    return float(roc_auc_score(y, s)) if 0 < y.sum() < len(y) else None


def paired_ci(y, a, b, rng) -> list[float]:
    """95% bootstrap interval of PR-AUC(a) - PR-AUC(b) on the same resamples."""
    d = []
    for _ in range(BOOT):
        i = rng.integers(0, len(y), len(y))
        if 0 < y[i].sum() < len(i):
            d.append(average_precision_score(y[i], a[i]) - average_precision_score(y[i], b[i]))
    return [round(float(np.percentile(d, 2.5)), 4), round(float(np.percentile(d, 97.5)), 4)]


def r4(x):
    return None if x is None else round(x, 4)


def main() -> None:
    with session_factory()() as s:
        pre = rv.scoreboard(s)
        rs = rows(s)
    rng = np.random.default_rng(SEED)
    y = np.array([r["y"] for r in rs])
    p = np.array([r["p"] for r in rs])
    has = [all(k in r["f"] for k in ("t_top_buyer_share", "t_sell_buy_ratio", "t_buys")) for r in rs]
    m = np.array(has)
    # Ties broken by a tiny copy of the model's own score would flatter the
    # checkers; break them at random instead.
    jitter = rng.uniform(0, 1e-6, len(rs))
    c5 = np.array([rulecheck.score(r["f"]) if h else 0 for r, h in zip(rs, has)]) + jitter
    c6 = np.array([rulecheck_x.score(r["f"]) if h else 0 for r, h in zip(rs, has)]) + jitter
    kind = np.array([1.0 if r["kind"] == "self-deployed" else 0.0 for r in rs]) + jitter

    rankers = {"model": p, "checker_phase5": c5, "checker_phase6": c6, "launch_type_only": kind}
    comp = {"tokens": int(m.sum()), "losses": int(y[m].sum()), "base_rate": r4(float(y[m].mean()))}
    for n, sc in rankers.items():
        comp[n] = {"pr_auc": r4(pr(y[m], sc[m])), "roc_auc": r4(roc(y[m], sc[m]))}
    for n in ("checker_phase5", "checker_phase6", "launch_type_only"):
        comp[f"model_minus_{n}_ci"] = paired_ci(y[m], p[m], rankers[n][m], rng)
    for n, f in (("checker_phase5", rulecheck), ("checker_phase6", rulecheck_x)):
        flag = np.array([f.verdict(r["f"]) if h else False for r, h in zip(rs, has)]) if hasattr(f, "verdict") \
            else (c5 if f is rulecheck else c6) >= 2
        comp[n]["flagged"] = int(flag[m].sum())
        comp[n]["precision"] = r4(float(y[m][flag[m]].mean())) if flag[m].any() else None

    by_kind = {}
    for k in ("launchpad", "self-deployed"):
        km = np.array([r["kind"] == k for r in rs])
        by_kind[k] = {"tokens": int(km.sum()), "losses": int(y[km].sum()),
                      "base_rate": r4(float(y[km].mean())) if km.any() else None,
                      "mean_predicted": r4(float(p[km].mean())) if km.any() else None,
                      "model_pr_auc": r4(pr(y[km], p[km])), "model_roc_auc": r4(roc(y[km], p[km]))}
        if km.any() and 0 < y[km].sum() < km.sum():
            d = []
            for _ in range(BOOT):
                i = rng.integers(0, km.sum(), km.sum())
                yy, pp = y[km][i], p[km][i]
                if 0 < yy.sum() < len(yy):
                    d.append(average_precision_score(yy, pp) - yy.mean())
            by_kind[k]["pr_auc_minus_base_rate_ci"] = [round(float(np.percentile(d, 2.5)), 4),
                                                       round(float(np.percentile(d, 97.5)), 4)]

    # The label scope. Phase 6 defined buyer loss on tokens that were not
    # rugged; the live label is the hour-6 price, which a pull leaves standing,
    # so a pulled pool counts as "no loss". Two re-scopings, both post hoc.
    pull = np.array([r["pulled_6h"] for r in rs])
    scope = {"pulled_by_6h": int(pull.sum()),
             "pulled_by_6h_labelled_loss": int(y[pull].sum())}
    for name, mask, yy in (("not_pulled_by_6h (the model's population)", ~pull, y),
                           ("all, pull counted as loss", np.ones(len(rs), bool),
                            np.maximum(y, pull.astype(int)))):
        e = {"tokens": int(mask.sum()), "losses": int(yy[mask].sum()),
             "base_rate": r4(float(yy[mask].mean())),
             "model_pr_auc": r4(pr(yy[mask], p[mask])), "model_roc_auc": r4(roc(yy[mask], p[mask])),
             "launch_type_only_pr_auc": r4(pr(yy[mask], kind[mask])),
             "checker_phase6_pr_auc": r4(pr(yy[mask], c6[mask]))}
        e["model_minus_launch_type_only_ci"] = paired_ci(yy[mask], p[mask], kind[mask], rng)
        e["model_minus_checker_phase6_ci"] = paired_ci(yy[mask], p[mask], c6[mask], rng)
        scope[name] = e

    ts = sorted(r["ts"] for r in rs)
    gaps = [(b - a).total_seconds() / 3600 for a, b in zip(ts, ts[1:])]
    worst = int(np.argmax(gaps)) if gaps else None
    per_day = Counter(t.date().isoformat() for t in ts)
    coverage = {"first": ts[0].isoformat() if ts else None, "last": ts[-1].isoformat() if ts else None,
                "longest_gap_hours": round(gaps[worst], 1) if gaps else None,
                "longest_gap_from": ts[worst].isoformat() if gaps else None,
                "gaps_over_2h": sum(g > 2 for g in gaps),
                "scored_resolved_per_day": dict(sorted(per_day.items()))}

    doc = {"generated_at": datetime.now(timezone.utc).isoformat(),
           "pre_registered": pre,
           "post_hoc": {"label_scope": scope, "vs_rule_checkers": comp, "by_launch_type": by_kind, "coverage": coverage,
                        "features_missing": int((~m).sum())}}
    OUT.mkdir(exist_ok=True)
    (OUT / "forward_validation.json").write_text(json.dumps(doc, indent=2, default=str), encoding="utf8")
    print(json.dumps(doc["post_hoc"], indent=1, default=str))
    print(json.dumps(pre["buyer_loss"].get("reliability"), indent=0))


if __name__ == "__main__":
    main()
