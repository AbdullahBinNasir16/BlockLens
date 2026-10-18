"""Phase 5, Part C — retrain properly, and answer Part D.

    python -m scripts.phase5_model features     # token rows at launch + 5 min (cached)
    python -m scripts.phase5_model run          # every result, written to reports/

Sets, fixed by the sampling design (`reports/sampling_design.md`):

* TRAIN — `train_case`, `train_control` and `survivor_enum` strata, launched before the split
  date, family-capped, no family shared with the random cohort.
* CAL — the `random` cohort before the split date. True prevalence; used
  only to calibrate.
* EVAL — the `random` cohort on and after the split date. True prevalence,
  out of time, never seen by training or calibration. **Every headline
  number is computed here.**

Target: RUG against FAILED + SURVIVED. UNCLEAR and NEVER_LAUNCHED are not
outcomes and are excluded, as in Phase 2.
"""
from __future__ import annotations

import argparse
import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sqlalchemy import text

from blocklens.label.rules import RULE_VERSION
from blocklens.model import rulecheck
from blocklens.model import token_features as tf
from blocklens.sampling import design as d
from blocklens.store.db import session_factory

CHAIN = "base"
CACHE = Path("data/phase5_features.json")
OUT = Path("reports/phase5_results.json")
SEED = 20261018
BOOT = 2000
KS = (10, 25, 50)


# ------------------------------------------------------------------ features

def cmd_features(args: argparse.Namespace) -> int:
    cache = json.loads(CACHE.read_text(encoding="utf8")) if CACHE.exists() else {}
    with session_factory()() as s:
        toks = [t for (t,) in s.execute(text("""
            select s.token_address from token_sample s
            join token_label l on l.token_address = s.token_address and l.chain = s.chain
                               and l.rule_version = :rv
            where s.chain = :c and s.alive_at_cutoff and s.excluded_reason is null
        """), {"c": CHAIN, "rv": RULE_VERSION}).all()]
        todo = [t for t in toks if t not in cache or args.refresh]
        print(f"{len(toks)} labelled sampled tokens, {len(todo)} to compute")
        ctx = tf.Context(s, CHAIN)
        for i, t in enumerate(todo, 1):
            row = tf.token_row(s, ctx, token=t)
            if row is not None:
                cache[t] = row
            if i % 100 == 0:
                print(f"  {i}/{len(todo)}", flush=True)
                CACHE.parent.mkdir(parents=True, exist_ok=True)
                CACHE.write_text(json.dumps(cache), encoding="utf8")
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(cache), encoding="utf8")
    print(f"cached {len(cache)} rows -> {CACHE}")
    return 0


# ------------------------------------------------------------------ data

def load() -> dict:
    feats = json.loads(CACHE.read_text(encoding="utf8"))
    with session_factory()() as s:
        rows = s.execute(text("""
            select s.token_address, s.sampling_stratum, s.launch_ts, s.family_id, l.label
            from token_sample s
            join token_label l on l.token_address = s.token_address and l.chain = s.chain
                               and l.rule_version = :rv
            where s.chain = :c and s.alive_at_cutoff and s.excluded_reason is null
              and l.label in ('RUG', 'FAILED', 'SURVIVED')
        """), {"c": CHAIN, "rv": RULE_VERSION}).all()
    data = {"TRAIN": [], "CAL": [], "EVAL": []}
    for tok, stratum, launch, fam, label in rows:
        if tok not in feats:
            continue
        before = launch < d.SPLIT_DATE
        if stratum in ("train_case", "train_control", "survivor_enum") and before:
            side = "TRAIN"
        elif stratum == "random":
            side = "CAL" if before else "EVAL"
        else:
            continue
        data[side].append({"token": tok, "stratum": stratum, "launch": launch,
                           "family": fam, "label": label, "y": int(label == "RUG"),
                           **feats[tok]})
    # No family on both sides, enforced again here rather than trusted.
    held = {r["family"] for r in data["CAL"] + data["EVAL"]}
    dropped = [r for r in data["TRAIN"] if r["family"] in held]
    data["TRAIN"] = [r for r in data["TRAIN"] if r["family"] not in held]
    data["train_dropped_family_overlap"] = len(dropped)
    return data


def matrix(rows: list[dict], names: list[str]) -> np.ndarray:
    return np.array([[float(r.get(n, 0.0) or 0.0) for n in names] for r in rows])


# ------------------------------------------------------------------ models

def logistic(C: float = 0.5):
    return Pipeline([("scale", StandardScaler()),
                     ("clf", LogisticRegression(C=C, max_iter=5000, random_state=SEED))])


def boosting():
    return HistGradientBoostingClassifier(max_depth=3, max_iter=300, learning_rate=0.05,
                                          min_samples_leaf=20, l2_regularization=1.0,
                                          random_state=SEED)


def logit(p):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


def sigmoid(z):
    return 1 / (1 + np.exp(-z))


def prior_shift(p_model: np.ndarray, train_rate: float, true_rate: float) -> np.ndarray:
    """Case-control correction (King & Zeng 2001): move the intercept by the
    log ratio of the true odds to the sampled odds."""
    return sigmoid(logit(p_model) - logit(train_rate) + logit(true_rate))


def platt(p_cal: np.ndarray, y_cal: np.ndarray):
    lr = LogisticRegression(C=1e6, max_iter=5000)
    lr.fit(logit(p_cal).reshape(-1, 1), y_cal)
    return lambda p: lr.predict_proba(logit(p).reshape(-1, 1))[:, 1]


# ------------------------------------------------------------------ metrics

def precision_at(y: np.ndarray, s: np.ndarray, k: int) -> float | None:
    if len(y) < k:
        return None
    order = np.argsort(-s, kind="mergesort")
    return float(y[order[:k]].mean())


def reliability(y: np.ndarray, p: np.ndarray, bins: int = 10) -> list[dict]:
    out = []
    edges = np.linspace(0, 1, bins + 1)
    for i in range(bins):
        m = (p >= edges[i]) & ((p < edges[i + 1]) if i < bins - 1 else (p <= 1))
        if m.sum():
            out.append({"bin": f"{edges[i]:.1f}-{edges[i + 1]:.1f}", "n": int(m.sum()),
                        "mean_predicted": round(float(p[m].mean()), 4),
                        "observed_rate": round(float(y[m].mean()), 4)})
    return out


def metrics(y: np.ndarray, s: np.ndarray, *, prob: bool) -> dict:
    out = {"n": int(len(y)), "positives": int(y.sum()),
           "pr_auc": round(float(average_precision_score(y, s)), 4),
           "roc_auc": round(float(roc_auc_score(y, s)), 4)}
    for k in KS:
        v = precision_at(y, s, k)
        out[f"precision_at_{k}"] = None if v is None else round(v, 4)
    if prob:
        out["brier"] = round(float(brier_score_loss(y, s)), 4)
        out["brier_base_rate"] = round(float(brier_score_loss(y, np.full_like(s, y.mean()))), 4)
    return out


def family_bootstrap(y, fams, scores: dict[str, np.ndarray], pairs: list[tuple[str, str]],
                     seed: int = SEED, n: int = BOOT) -> dict:
    """95% intervals for PR-AUC and for PR-AUC differences, resampling
    *families*, because tokens in one family are not independent."""
    rng = np.random.default_rng(seed)
    idx_by_fam = defaultdict(list)
    for i, f in enumerate(fams):
        idx_by_fam[f].append(i)
    fam_list = list(idx_by_fam)
    draws = {k: [] for k in scores}
    diffs = {f"{a} - {b}": [] for a, b in pairs}
    for _ in range(n):
        pick = rng.integers(0, len(fam_list), len(fam_list))
        idx = np.concatenate([idx_by_fam[fam_list[j]] for j in pick])
        yy = y[idx]
        if yy.min() == yy.max():
            continue
        ap = {k: average_precision_score(yy, v[idx]) for k, v in scores.items()}
        for k in scores:
            draws[k].append(ap[k])
        for a, b in pairs:
            diffs[f"{a} - {b}"].append(ap[a] - ap[b])

    def ci(v):
        if not v:
            return None
        return [round(float(np.percentile(v, 2.5)), 4), round(float(np.percentile(v, 97.5)), 4)]

    return {"resamples": len(next(iter(draws.values()))) if draws else 0,
            "families": len(fam_list),
            "pr_auc_ci": {k: ci(v) for k, v in draws.items()},
            "difference_ci": {k: ci(v) for k, v in diffs.items()},
            "difference_share_above_zero": {k: round(float(np.mean(np.array(v) > 0)), 4)
                                            for k, v in diffs.items() if v}}


# ------------------------------------------------------------------ run

def cmd_run(args: argparse.Namespace) -> int:
    data = load()
    names = sorted({k for r in data["TRAIN"] for k in r if k.startswith(("t_", "g_", "r_"))})
    timing = tf.group(names, tf.TIMING) + tf.group(names, tf.RULE_INPUTS)
    graph = tf.group(names, tf.GRAPH)
    tr, ca, ev = data["TRAIN"], data["CAL"], data["EVAL"]
    ytr = np.array([r["y"] for r in tr])
    yca = np.array([r["y"] for r in ca])
    yev = np.array([r["y"] for r in ev])
    fam_ev = [r["family"] for r in ev]
    out: dict = {"generated": datetime.now(timezone.utc).isoformat(),
                 "rule_version": RULE_VERSION, "feature_set": tf.FEATURE_SET_VERSION,
                 "split_date": d.SPLIT_DATE.isoformat(), "features": names}

    def side(rows, y):
        fams = {r["family"] for r in rows}
        return {"tokens": len(rows), "families": len(fams),
                "classes": dict(Counter(r["label"] for r in rows)),
                "positive_rate": round(float(y.mean()), 4) if len(y) else None,
                "launch_min": min(r["launch"] for r in rows).isoformat() if rows else None,
                "launch_max": max(r["launch"] for r in rows).isoformat() if rows else None}
    out["sets"] = {"TRAIN": side(tr, ytr), "CAL": side(ca, yca), "EVAL": side(ev, yev),
                   "train_dropped_family_overlap": data["train_dropped_family_overlap"]}
    print(json.dumps(out["sets"], indent=1, default=str))
    true_rate = float(np.concatenate([yca]).mean())
    train_rate = float(ytr.mean())
    out["prevalence"] = {"train_sampled": round(train_rate, 4), "cal_true": round(true_rate, 4),
                         "eval_true": round(float(yev.mean()), 4)}

    # ---- the rule checker, on the same split
    rc_ev = np.array([rulecheck.score(r) for r in ev], dtype=float)
    out["rule_checker"] = {"flags": list(rulecheck.FLAGS), "verdict_at": rulecheck.VERDICT_AT,
                           "eval": metrics(yev, rc_ev, prob=False)}
    verdict = rc_ev >= rulecheck.VERDICT_AT
    tp = int((verdict & (yev == 1)).sum())
    out["rule_checker"]["verdict"] = {
        "flagged": int(verdict.sum()), "true_positives": tp,
        "precision": round(tp / verdict.sum(), 4) if verdict.sum() else None,
        "recall": round(tp / yev.sum(), 4) if yev.sum() else None}

    # ---- feature ranking for the 10 / all curve, on TRAIN only
    Xtr_all = matrix(tr, names)
    single = []
    for j, n in enumerate(names):
        x = Xtr_all[:, j]
        a = roc_auc_score(ytr, x) if x.std() > 0 else 0.5
        single.append((abs(a - 0.5), n))
    ranked = [n for _, n in sorted(single, reverse=True)]
    out["train_feature_ranking"] = ranked

    # ---- C for the logistic model, by family-grouped CV on TRAIN only
    groups = np.array([r["family"] for r in tr])
    best_c, best_ap = 0.5, -1
    for C in (0.01, 0.05, 0.1, 0.5, 1.0):
        aps = []
        for a, b in GroupKFold(n_splits=5).split(Xtr_all, ytr, groups):
            if ytr[b].min() == ytr[b].max():
                continue
            m = logistic(C).fit(Xtr_all[a], ytr[a])
            aps.append(average_precision_score(ytr[b], m.predict_proba(Xtr_all[b])[:, 1]))
        if aps and np.mean(aps) > best_ap:
            best_c, best_ap = C, float(np.mean(aps))
    out["logistic_C"] = {"chosen": best_c, "train_cv_pr_auc": round(best_ap, 4)}

    results, scores_ev, probs = {}, {"rule_checker": rc_ev}, {}

    def fit_eval(name: str, feats: list[str], kind: str):
        Xtr, Xca, Xev = matrix(tr, feats), matrix(ca, feats), matrix(ev, feats)
        m = logistic(best_c) if kind == "logistic" else boosting()
        m.fit(Xtr, ytr)
        p_ca, p_ev = m.predict_proba(Xca)[:, 1], m.predict_proba(Xev)[:, 1]
        res = {"features": len(feats), "model": kind}
        res["eval_raw"] = metrics(yev, p_ev, prob=True)
        if kind == "logistic":
            cal = lambda p: prior_shift(p, train_rate, true_rate)  # noqa: E731
            res["calibration"] = "prior shift (intercept += logit(true) - logit(sampled))"
        else:
            cal = platt(p_ca, yca)
            res["calibration"] = "Platt scaling fitted on CAL"
        p_ev_c = cal(p_ev)
        res["eval_calibrated"] = metrics(yev, p_ev_c, prob=True)
        res["reliability_before"] = reliability(yev, p_ev)
        res["reliability_after"] = reliability(yev, p_ev_c)
        results[name] = res
        scores_ev[name] = p_ev_c
        probs[name] = (m, feats)
        e = res["eval_calibrated"]
        print(f"  {name:<28} {len(feats):>2}f  PR-AUC {e['pr_auc']:.3f}  ROC {e['roc_auc']:.3f}  "
              f"P@25 {e['precision_at_25']}  Brier {e['brier']:.4f} (raw {res['eval_raw']['brier']:.4f})")

    print(f"\nEVAL: {len(ev)} tokens, prevalence {yev.mean():.3f}; rule checker PR-AUC "
          f"{out['rule_checker']['eval']['pr_auc']:.3f}")
    for kind in ("logistic", "boosting"):
        fit_eval(f"{kind}: all", names, kind)
        fit_eval(f"{kind}: top 10", ranked[:10], kind)
        fit_eval(f"{kind}: top 5", ranked[:5], kind)
        fit_eval(f"{kind}: timing only", timing, kind)
        fit_eval(f"{kind}: graph only", graph, kind)
    out["models"] = results

    pairs = [("logistic: all", "rule_checker"), ("boosting: all", "rule_checker"),
             ("logistic: all", "logistic: timing only"), ("boosting: all", "boosting: timing only"),
             ("logistic: graph only", "rule_checker"), ("boosting: graph only", "rule_checker")]
    out["bootstrap"] = family_bootstrap(yev, fam_ev, scores_ev, pairs)

    # permutation null on EVAL for the graph-only model: does it beat noise?
    rng = np.random.default_rng(SEED)
    null = []
    for _ in range(200):
        null.append(average_precision_score(rng.permutation(yev), scores_ev["boosting: graph only"]))
    out["graph_only_null"] = {"mean": round(float(np.mean(null)), 4),
                              "p95": round(float(np.percentile(null, 95)), 4)}

    # ---- permutation importance, on EVAL, for the two full models
    out["permutation_importance"] = {}
    for name in ("logistic: all", "boosting: all"):
        m, feats = probs[name]
        pi = permutation_importance(m, matrix(ev, feats), yev, scoring="average_precision",
                                    n_repeats=30, random_state=SEED)
        order = np.argsort(-pi.importances_mean)
        out["permutation_importance"][name] = [
            {"feature": feats[i], "mean": round(float(pi.importances_mean[i]), 4),
             "std": round(float(pi.importances_std[i]), 4)} for i in order]

    # ---- decay: by month of launch on EVAL
    by_month = defaultdict(list)
    for i, r in enumerate(ev):
        by_month[r["launch"].strftime("%Y-%m")].append(i)
    out["decay"] = {}
    for mth, idx in sorted(by_month.items()):
        idx = np.array(idx)
        if yev[idx].min() == yev[idx].max():
            out["decay"][mth] = {"n": len(idx), "note": "single class"}
            continue
        out["decay"][mth] = {"n": len(idx), "positives": int(yev[idx].sum()),
                             "rule_checker_pr_auc": round(float(average_precision_score(yev[idx], rc_ev[idx])), 4),
                             "boosting_all_pr_auc": round(float(average_precision_score(yev[idx], scores_ev["boosting: all"][idx])), 4),
                             "logistic_all_pr_auc": round(float(average_precision_score(yev[idx], scores_ev["logistic: all"][idx])), 4)}

    # ---- post hoc, and labelled as such ------------------------------
    # The pre-registered checker omitted the most standard rug check there
    # is: whether liquidity is locked. On this population "minted and
    # liquidity-added in one transaction" is a launchpad launch with locked
    # liquidity, and its absence is a deployer holding withdrawable
    # liquidity. Added *after* seeing the results, so it is reported beside
    # the pre-registered baseline and never instead of it.
    lp_rule = np.array([0.0 if r["r_mint_in_window"] else 1.0 for r in ev])
    rc_plus = rc_ev + 10.0 * lp_rule
    post = {"note": "added after the pre-registered results were seen",
            "lp_not_locked_rule": metrics(yev, lp_rule, prob=False),
            "rule_checker_plus_lp_rule": metrics(yev, rc_plus, prob=False)}
    flag = lp_rule == 1
    tp = int((flag & (yev == 1)).sum())
    post["lp_not_locked_rule"]["verdict"] = {
        "flagged": int(flag.sum()), "true_positives": tp,
        "precision": round(tp / flag.sum(), 4) if flag.sum() else None,
        "recall": round(tp / yev.sum(), 4)}
    no_mint = [n for n in names if n != "r_mint_in_window"]
    for kind in ("logistic", "boosting"):
        fit_eval(f"{kind}: all but mint", no_mint, kind)
        post[f"{kind}: all but mint"] = results[f"{kind}: all"] and results[f"{kind}: all but mint"]["eval_calibrated"]
    scores_ev["lp_rule"] = lp_rule
    scores_ev["rule_checker_plus_lp_rule"] = rc_plus
    post["bootstrap"] = family_bootstrap(yev, fam_ev, scores_ev, [
        ("boosting: all", "lp_rule"), ("logistic: all", "lp_rule"),
        ("boosting: all", "rule_checker_plus_lp_rule")])
    # within each launch type: is there anything left to predict?
    post["within_launch_type"] = {}
    for nm, sel in (("self-deployed (no mint in window)", lp_rule == 1),
                    ("launchpad (mint + LP in one tx)", lp_rule == 0)):
        yy = yev[sel]
        post["within_launch_type"][nm] = {"tokens": int(sel.sum()), "rug": int(yy.sum()),
                                         "not_rug": int(len(yy) - yy.sum())}
        if 0 < yy.sum() < len(yy) and min(yy.sum(), len(yy) - yy.sum()) >= 10:
            post["within_launch_type"][nm]["boosting_pr_auc"] = round(
                float(average_precision_score(yy, scores_ev["boosting: all"][sel])), 4)
        else:
            post["within_launch_type"][nm]["note"] = "fewer than 10 tokens in the minority class: not evaluable"
    out["post_hoc"] = post

    out["part_d_wallet_level"] = wallet_level(ca + ev)

    OUT.write_text(json.dumps(out, indent=1, default=str), encoding="utf8")
    print(f"\nwrote {OUT}")
    print(json.dumps(out["bootstrap"], indent=1))
    print("wallet level:", json.dumps(out["part_d_wallet_level"], indent=1))
    return 0


# ------------------------------------------------------------------ Part D, option 2

def wallet_level(rows: list[dict]) -> dict:
    """Does graph position predict a wallet's own insider behaviour?

    Unit: an early buyer (bought by the cutoff) of a random-cohort token.
    Outcome, observed after the cutoff and inside the stored first hour:
    the wallet sold at least 90% of what it bought, within the hour - a
    dump. Predictors, as of the cutoff: graph position (funded by the
    deployer, in the largest funding component among the token's early
    buyers, has any funder, has prior co-purchase ties) against the wallet's
    own timing (seconds after launch it first bought). Grouped by token, so
    no token's wallets sit on both sides of any comparison.
    """
    from blocklens.ingest.evm import UNISWAP_V4_POOL_MANAGER as PM
    toks = {r["token"] for r in rows}
    if not toks:
        return {}
    ys, feats, grp = [], [], []
    with session_factory()() as s:
        ctx = tf.Context(s, CHAIN)
        for t in toks:
            pool, dex, created = s.execute(text("""
                select pool_key, dex, created_block from token_sample
                where chain = :c and token_address = :t"""), {"c": CHAIN, "t": t}).one()
            holder = PM if dex == "uniswap-v4" else pool
            cut = created + d.CUTOFF_BLOCKS
            tr = s.execute(text("""
                select block_number, tx_hash, from_address, to_address, value_normalised
                from transfer
                where chain = :c and token_address = :t and block_number <= :end
                order by block_number, log_index"""),
                {"c": CHAIN, "t": t, "end": created + 1800}).all()
            swap_tx = {x for (x,) in s.execute(text(
                "select tx_hash from swap where chain = :c and pair_address = :p"),
                {"c": CHAIN, "p": pool}).all()}
            minted = lp = None
            bought, sold, first = defaultdict(float), defaultdict(float), {}
            for blk, tx, fr, to, v in tr:
                a = float(v or 0)
                if fr == tf.ZERO and minted is None:
                    minted = to
                if to == holder and fr != tf.ZERO and tx not in swap_tx and lp is None:
                    lp = fr
                if tx not in swap_tx:
                    continue
                via = fr == holder or fr in ctx.pools or fr in ctx.infra
                back = to == holder or to in ctx.pools or to in ctx.infra
                if via and ctx.is_wallet(to):
                    bought[to] += a
                    if blk <= cut:
                        first.setdefault(to, blk)
                elif back and ctx.is_wallet(fr) and fr in bought:
                    sold[fr] += a
            early = [w for w in first]
            if len(early) < 2:
                continue
            keys = {k for k in (minted, lp) if k}
            fund = s.execute(text("""
                select from_address, to_address from transfer
                where chain = :c and to_address = any(:b) and block_number <= :cut"""),
                {"c": CHAIN, "b": early, "cut": cut}).all()
            funders = defaultdict(set)
            for fr, to in fund:
                if ctx.is_wallet(fr) and fr != to:
                    funders[to].add(fr)
            parent = {w: w for w in early}

            def find(x):
                while parent[x] != x:
                    parent[x] = parent[parent[x]]
                    x = parent[x]
                return x
            byf = defaultdict(list)
            for w, fs in funders.items():
                for f in fs:
                    byf[f].append(w)
                    if f in parent:
                        parent[find(f)] = find(w)
            for ws in byf.values():
                for w in ws[1:]:
                    parent[find(ws[0])] = find(w)
            size = Counter(find(w) for w in early)
            big = max(size.values())
            for w in early:
                ys.append(int(bought[w] > 0 and sold[w] >= 0.9 * bought[w]))
                feats.append({
                    "funded_by_deployer": int(bool(funders.get(w, set()) & keys)),
                    "in_largest_component": int(size[find(w)] == big and big > 1),
                    "has_funder": int(bool(funders.get(w))),
                    "own_entry_delay_s": (first[w] - created) * d.BLOCK_SECONDS,
                })
                grp.append(t)
    y = np.array(ys)
    out = {"wallets": len(y), "tokens": len(set(grp)),
           "dump_rate": round(float(y.mean()), 4) if len(y) else None}
    if len(y) < 20 or y.min() == y.max():
        out["note"] = "too few wallets or a single class"
        return out
    for k in ("funded_by_deployer", "in_largest_component", "has_funder"):
        x = np.array([f[k] for f in feats])
        out[k] = {"share_of_wallets": round(float(x.mean()), 4),
                  "dump_rate_if_1": round(float(y[x == 1].mean()), 4) if x.sum() else None,
                  "dump_rate_if_0": round(float(y[x == 0].mean()), 4) if (x == 0).sum() else None,
                  "auc": round(float(roc_auc_score(y, x)), 4) if x.std() > 0 else None}
    delay = np.array([f["own_entry_delay_s"] for f in feats])
    out["own_entry_delay_auc (earlier = dump)"] = round(float(roc_auc_score(y, -delay)), 4)

    # grouped CV: graph position vs own timing vs both
    X_graph = np.array([[f["funded_by_deployer"], f["in_largest_component"], f["has_funder"]]
                        for f in feats], dtype=float)
    X_time = delay.reshape(-1, 1).astype(float)
    g = np.array(grp)
    cv = {}
    for name, X in (("graph position", X_graph), ("own timing", X_time),
                    ("both", np.hstack([X_graph, X_time]))):
        aucs = []
        for a, b in GroupKFold(n_splits=5).split(X, y, g):
            if y[b].min() == y[b].max() or y[a].min() == y[a].max():
                continue
            m = logistic(1.0).fit(X[a], y[a])
            aucs.append(roc_auc_score(y[b], m.predict_proba(X[b])[:, 1]))
        cv[name] = {"auc_mean": round(float(np.mean(aucs)), 4) if aucs else None,
                    "auc_std": round(float(np.std(aucs)), 4) if aucs else None}
    out["grouped_cv"] = cv
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="phase5_model")
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("features")
    f.add_argument("--refresh", action="store_true")
    f.set_defaults(fn=cmd_features)
    sub.add_parser("run").set_defaults(fn=cmd_run)
    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
