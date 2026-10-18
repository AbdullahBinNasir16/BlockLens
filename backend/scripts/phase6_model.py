"""Phase 6 — models for the FAILED split, against the pre-registered baselines.

    python -m scripts.phase6_model          # -> reports/phase6_results.json

Targets (pre-registered in `blocklens/model/rulecheck_x.py`), on non-RUG
tokens alive at minute 5:

* T1 EXTRACTED — from `data/phase6_extraction.json`.
* T2 BUYER_LOSS — a buy at the minute-5 price is worth <= 50% at hour 6.

**Deviation from the pre-registration, stated before any result below:**
the pre-registered evaluation set (random cohort after 2026-04-20) holds 0
EXTRACTED and 3 BUYER_LOSS tokens of 78, so it can evaluate nothing. Both
targets are therefore evaluated on the random cohort *before* the split
(CAL): true prevalence, no family shared with training, out of sample but
**not out of time**. There is no third set to calibrate on, so only ranking
metrics and raw Brier are reported. T1 has 9 positives in training, so no
model is fitted for it: only the fixed rule checkers are scored.
"""
from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from sklearn.inspection import permutation_importance
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import GroupKFold
from sqlalchemy import text

from blocklens.label.rules import RULE_VERSION
from blocklens.model import rulecheck, rulecheck_x
from blocklens.model import token_features as tf
from blocklens.sampling import design as d
from blocklens.store.db import session_factory
from scripts.phase5_model import (
    SEED, boosting, family_bootstrap, logistic, matrix, metrics,
)

FEATS = Path("data/phase5_features.json")
EXTR = Path("data/phase6_extraction.json")
OUT = Path("reports/phase6_results.json")


def load() -> dict:
    feats = json.loads(FEATS.read_text(encoding="utf8"))
    extr = json.loads(EXTR.read_text(encoding="utf8"))
    with session_factory()() as s:
        rows = s.execute(text("""
            select s.token_address, s.sampling_stratum, s.launch_ts, s.family_id, l.label
            from token_sample s
            join token_label l on l.token_address = s.token_address and l.chain = s.chain
                               and l.rule_version = :rv
            where s.chain = 'base' and s.alive_at_cutoff and s.excluded_reason is null
              and l.label in ('FAILED', 'SURVIVED')
        """), {"rv": RULE_VERSION}).all()
    sets = {"TRAIN": [], "CAL": [], "EVAL": []}
    for tok, stratum, launch, fam, label in rows:
        if tok not in feats or tok not in extr:
            continue
        before = launch < d.SPLIT_DATE
        if stratum in ("train_case", "train_control", "survivor_enum") and before:
            side = "TRAIN"
        elif stratum == "random":
            side = "CAL" if before else "EVAL"
        else:
            continue
        x = extr[tok]
        pe = x.get("price_end_vs_cutoff")
        sets[side].append({
            "token": tok, "family": fam, "launch": launch, "v2": label,
            "t1": None if x["mode"] == "UNCLEAR" else int(x["mode"] == "EXTRACTED"),
            "t2": None if pe is None else int(pe <= rulecheck_x.BUYER_LOSS_AT),
            **feats[tok]})
    held = {r["family"] for r in sets["CAL"] + sets["EVAL"]}
    sets["TRAIN"] = [r for r in sets["TRAIN"] if r["family"] not in held]
    return sets


def scored(rows, target):
    rows = [r for r in rows if r[target] is not None]
    return rows, np.array([r[target] for r in rows])


def main() -> int:
    sets = load()
    names = sorted({k for r in sets["TRAIN"] for k in r if k.startswith(("t_", "g_", "r_"))})
    timing = tf.group(names, tf.TIMING) + tf.group(names, tf.RULE_INPUTS)
    graph = tf.group(names, tf.GRAPH)
    out = {"generated": datetime.now(timezone.utc).isoformat(),
           "deviation": "evaluated on CAL (random cohort, Jan-Apr): the pre-registered "
                        "EVAL set has 0 EXTRACTED and 3 BUYER_LOSS tokens",
           "counts": {}}
    for side, rows in sets.items():
        out["counts"][side] = {
            "tokens": len(rows), "families": len({r["family"] for r in rows}),
            "t1": dict(Counter(r["t1"] for r in rows)), "t2": dict(Counter(r["t2"] for r in rows))}
    print(json.dumps(out["counts"], indent=1, default=str))

    # ---- T1: rule checkers only
    cal1, y1 = scored(sets["CAL"], "t1")
    out["T1"] = {"positives_in_train": int(sum(r["t1"] or 0 for r in sets["TRAIN"])),
                 "model": "not fitted: too few training positives"}
    if y1.sum() and y1.sum() < len(y1):
        for nm, fn in (("rule checker (Phase 5)", rulecheck.score),
                       ("early-concentration checker", rulecheck_x.score)):
            out["T1"][nm] = metrics(y1, np.array([fn(r) for r in cal1], dtype=float), prob=False)
        print("T1 on CAL:", {k: v.get("pr_auc") for k, v in out["T1"].items() if isinstance(v, dict)},
              "prevalence", round(float(y1.mean()), 3))

    # ---- T2: the full comparison
    tr, ytr = scored(sets["TRAIN"], "t2")
    ca, yca = scored(sets["CAL"], "t2")
    fam = [r["family"] for r in ca]
    groups = np.array([r["family"] for r in tr])
    Xall = matrix(tr, names)
    best_c, best = 0.5, -1.0
    for C in (0.01, 0.05, 0.1, 0.5, 1.0):
        aps = []
        for a, b in GroupKFold(n_splits=5).split(Xall, ytr, groups):
            if ytr[b].min() != ytr[b].max():
                aps.append(average_precision_score(
                    ytr[b], logistic(C).fit(Xall[a], ytr[a]).predict_proba(Xall[b])[:, 1]))
        if aps and np.mean(aps) > best:
            best_c, best = C, float(np.mean(aps))
    t2 = {"prevalence_train": round(float(ytr.mean()), 4), "prevalence_cal": round(float(yca.mean()), 4),
          "logistic_C": best_c, "models": {}}
    scores = {"rule checker (Phase 5)": np.array([rulecheck.score(r) for r in ca], dtype=float),
              "early-concentration checker": np.array([rulecheck_x.score(r) for r in ca], dtype=float)}
    for nm, s in scores.items():
        t2["models"][nm] = metrics(yca, s, prob=False)
    fitted = {}
    for kind in ("logistic", "boosting"):
        for gname, feats in (("all", names), ("timing", timing), ("graph", graph)):
            m = (logistic(best_c) if kind == "logistic" else boosting()).fit(matrix(tr, feats), ytr)
            p = m.predict_proba(matrix(ca, feats))[:, 1]
            key = f"{kind}: {gname}"
            scores[key] = p
            fitted[key] = (m, feats)
            t2["models"][key] = {"features": len(feats), **metrics(yca, p, prob=True)}
    for k, v in t2["models"].items():
        print(f"  T2 {k:<32} PR-AUC {v['pr_auc']:.3f}  ROC {v['roc_auc']:.3f}  P@25 {v['precision_at_25']}")
    pairs = [("boosting: all", "early-concentration checker"), ("logistic: all", "early-concentration checker"),
             ("boosting: all", "rule checker (Phase 5)"),
             ("boosting: all", "boosting: timing"), ("logistic: all", "logistic: timing"),
             ("boosting: graph", "early-concentration checker")]
    t2["bootstrap"] = family_bootstrap(yca, fam, scores, pairs)
    rng = np.random.default_rng(SEED)
    for k in ("boosting: graph", "logistic: graph"):
        null = [average_precision_score(rng.permutation(yca), scores[k]) for _ in range(500)]
        t2[f"{k} null"] = {"mean": round(float(np.mean(null)), 4), "p95": round(float(np.percentile(null, 95)), 4)}
    t2["permutation_importance"] = {}
    for k in ("logistic: all", "boosting: all"):
        m, feats = fitted[k]
        pi = permutation_importance(m, matrix(ca, feats), yca, scoring="average_precision",
                                    n_repeats=30, random_state=SEED)
        order = np.argsort(-pi.importances_mean)
        t2["permutation_importance"][k] = [
            {"feature": feats[i], "mean": round(float(pi.importances_mean[i]), 4),
             "std": round(float(pi.importances_std[i]), 4)} for i in order[:10]]
    # launch type is not deciding this one: check
    lt = np.array([r["r_mint_in_window"] for r in ca])
    t2["by_launch_type"] = {
        "launchpad": {"tokens": int((lt == 1).sum()), "loss": int(yca[lt == 1].sum())},
        "self-deployed": {"tokens": int((lt == 0).sum()), "loss": int(yca[lt == 0].sum())}}
    out["T2"] = t2
    OUT.write_text(json.dumps(out, indent=1, default=str), encoding="utf8")
    print(json.dumps({k: t2[k] for k in ("bootstrap", "boosting: graph null", "logistic: graph null",
                                          "by_launch_type")}, indent=1))
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
