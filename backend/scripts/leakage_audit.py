"""Phase 5, Part A — the integrity audit of the Phase 4 result.

    python -m scripts.leakage_audit            # writes reports/leakage_audit.json

Every number in `reports/leakage_audit.md` comes from the JSON this writes.
The script changes nothing in the store.
"""
from __future__ import annotations

import argparse
import json
import statistics
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from sklearn.metrics import roc_auc_score

from blocklens.label.rules import RULE_VERSION
from blocklens.model import audit, leakage, train
from blocklens.model import dataset as ds
from blocklens.store.db import session_factory

MODELS = ("logistic", "boosting")


def _q(xs: list[float]) -> dict:
    if not xs:
        return {"n": 0}
    a = np.array(xs, dtype=float)
    return {"n": len(xs), "min": round(float(a.min()), 2),
            "p25": round(float(np.percentile(a, 25)), 2),
            "median": round(float(np.median(a)), 2),
            "p75": round(float(np.percentile(a, 75)), 2),
            "max": round(float(a.max()), 2)}


def _cv(data: ds.Dataset, feats: list[str], name: str) -> list[dict]:
    out = []
    for m in MODELS:
        d = train.evaluate(data, features=feats, name=name, model=m).as_dict()
        out.append(d)
        print(f"  {m:<9} {name:<44} AUC {d['auc_mean']:.3f} +/- {d['auc_std']:.3f}"
              f"  AP {d['ap_mean']:.3f}  folds {d['folds']}")
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--chain", default="base")
    ap.add_argument("--rule-version", default=RULE_VERSION)
    ap.add_argument("--out", default="reports/leakage_audit.json")
    args = ap.parse_args(argv)

    out: dict = {"generated": datetime.now(timezone.utc).isoformat(),
                 "chain": args.chain, "rule_version": args.rule_version}

    with session_factory()() as s:
        full = ds.load(s, chain=args.chain, rule_version=args.rule_version)
        excluded = leakage.definitional(full.feature_names)
        clean = ds.load(s, chain=args.chain, rule_version=args.rule_version,
                        drop_features=excluded)
        timing = [n for n in clean.feature_names if "entry_delay" in n]
        structure = [n for n in clean.feature_names if "entry_delay" not in n]
        print(f"dataset: {clean.n_rows} rows, {clean.n_tokens} tokens, "
              f"{len(timing)} timing + {len(structure)} structure features\n")

        # ---- A1: when did each token die? --------------------------------
        tl = audit.timelines(s, chain=args.chain, rule_version=args.rule_version)
        by = {t.token: t for t in tl}
        launch = {t.token: t.launch_ts for t in tl}
        in_model = set(clean.tokens)

        def grp(label: str, model_only: bool = False):
            return [t for t in tl if t.label == label
                    and (not model_only or t.token in in_model)]

        a1 = {"definition": f"rug = pool holdings of the token <= "
                            f"{audit.RUG_RESERVE_FRACTION:.0%} of running peak, "
                            f"measured from transfers inside launch + {audit.WINDOW_HOURS}h"}
        for scope, only in (("all_labelled", False), ("in_model", True)):
            r = grp("RUG", only)
            f = grp("FAILED", only)
            a1[scope] = {
                "RUG_tokens": len(r),
                "RUG_rugged_inside_window": sum(t.rugged_in_window for t in r),
                "RUG_alive_at_window_end": sum(not t.rugged_in_window for t in r),
                "RUG_rug_minute": _q([t.rug_min for t in r if t.rug_min is not None]),
                "RUG_last_trade_minute": _q([t.last_trade_min for t in r
                                             if t.last_trade_min is not None]),
                "FAILED_tokens": len(f),
                "FAILED_last_trade_minute": _q([t.last_trade_min for t in f
                                                if t.last_trade_min is not None]),
                "label_drop_hour_RUG": _q([t.label_drop_h for t in r
                                           if t.label_drop_h is not None]),
            }
        a1["survival_by_minute"] = audit.survival_table(tl)
        a1["tokens"] = [{
            "token": t.token, "label": t.label, "dex": t.dex,
            "launch": t.launch_ts.isoformat(), "wallet_rows": t.n_wallets,
            "trades_in_window": t.n_trades,
            "rug_minute": None if t.rug_min is None else round(t.rug_min, 1),
            "last_trade_minute": None if t.last_trade_min is None else round(t.last_trade_min, 1),
            "label_drop_hour": None if t.label_drop_h is None else round(t.label_drop_h, 1),
        } for t in tl]

        print("A1 — Phase 4 as published (timing only, all tokens)")
        a1["number_1_phase4_timing_all_tokens"] = _cv(clean, timing, "timing only, all tokens")

        late = {t.token for t in grp("RUG", True) if not t.rugged_in_window}
        controls = {t.token for t in grp("FAILED", True)}
        alive_set = late | controls
        n_late = len(late)
        print(f"\nA1 — rugs alive at the end of their own window: {n_late} token(s) "
              f"with features")
        if n_late >= 2:
            a1["number_2_timing_rugs_alive_at_window_end"] = _cv(
                audit.subset(clean, alive_set), timing, "timing only, late rugs vs controls")
        else:
            a1["number_2_timing_rugs_alive_at_window_end"] = {
                "positive_tokens": n_late,
                "result": "not estimable: no rug in the feature set was still "
                          "alive at the end of its feature window"}
            print("  not estimable — there are no positives to train or test on")

        # The censoring variable by itself. If when-trading-stopped predicts
        # the label as well as entry timing does, entry timing is a proxy
        # for the outcome, not a predictor of it.
        tok_y = np.array([1 if by[t].label == "RUG" else 0 for t in clean.tokens])
        last = np.array([by[t].last_trade_min or 0.0 for t in clean.tokens])
        i_mean = clean.feature_names.index("base_entry_delay_mean")
        mean_delay = np.array([np.mean(clean.X[clean.groups == t, i_mean])
                               for t in clean.tokens])
        a1["token_level_single_variable_auc"] = {
            "last_trade_minute_in_window (lower = RUG)":
                round(float(roc_auc_score(tok_y, -last)), 4),
            "mean_wallet_entry_delay (lower = RUG)":
                round(float(roc_auc_score(tok_y, -mean_delay)), 4),
            "spearman_last_trade_vs_mean_entry_delay":
                round(float(_spearman(last, mean_delay)), 4),
        }
        print(f"  token-level AUCs: {a1['token_level_single_variable_auc']}")
        out["A1_censoring"] = a1

        # ---- A3: cross-token leakage through the wallet ------------------
        print("\nA3 — cross-token wallet leakage")
        a3: dict = {"overlap": audit.wallet_overlap(s, chain=args.chain)}
        print(f"  {a3['overlap']}")
        comps = audit.shared_wallet_components(s, chain=args.chain, tokens=clean.tokens)
        n_comp = len(set(comps.values()))
        sizes = sorted((sum(1 for v in comps.values() if v == c) for c in set(comps.values())),
                       reverse=True)
        a3["components"] = {"tokens": len(comps), "components": n_comp,
                            "largest_component_sizes": sizes[:8]}
        mixed = 0
        for c in set(comps.values()):
            labs = {clean.token_labels[t] for t, v in comps.items() if v == c}
            mixed += len(labs) > 1
        a3["components"]["components_with_both_classes"] = mixed
        print(f"  {n_comp} shared-wallet components over {len(comps)} tokens; "
              f"largest {sizes[:6]}")

        by_comp = audit.regroup(clean, comps)
        a3["timing_grouped_by_token"] = a1["number_1_phase4_timing_all_tokens"]
        a3["timing_grouped_by_component"] = _cv(by_comp, timing, "timing, folds by shared-wallet component")
        a3["structure_grouped_by_component"] = _cv(by_comp, structure, "structure, folds by component")
        a3["both_grouped_by_component"] = _cv(by_comp, timing + structure, "both, folds by component")

        pt = audit.per_token_timing(s, chain=args.chain, data=clean)
        a3["per_token_timing_grouped_by_token"] = _cv(pt, pt.feature_names, "per-token timing, folds by token")
        a3["per_token_timing_grouped_by_component"] = _cv(
            audit.regroup(pt, comps), pt.feature_names, "per-token timing, folds by component")

        # the same per-token features, but frozen at 5 minutes and only on
        # tokens still alive then — a preview of the A2 option, not the fix
        alive5 = {t.token for t in tl if t.token in in_model
                  and t.trading_after(5) and (t.rug_min is None or t.rug_min > 5)}
        pt5 = audit.per_token_timing(s, chain=args.chain, data=clean, window_minutes=5)
        sub5 = audit.subset(pt5, alive5)
        a3["preview_5min_window_alive_at_5"] = {
            "tokens": len(alive5),
            "rug_tokens": sum(1 for t in alive5 if clean.token_labels[t] == "RUG"),
            "components": len({comps[t] for t in alive5}),
        }
        if len({clean.token_labels[t] for t in alive5}) == 2:
            a3["preview_5min_window_alive_at_5"]["results"] = _cv(
                audit.regroup(sub5, comps), pt5.feature_names,
                "per-token timing @5min, alive@5, by component")
        out["A3_cross_token"] = a3

        # ---- A3: the split ------------------------------------------------
        print("\nA3 — the split")
        a3s: dict = {"phase4_groupkfold_fold_dates": audit.fold_dates(clean, launch)}
        for f in a3s["phase4_groupkfold_fold_dates"]:
            print(f"  fold {f['fold']}: test {f['test_launch_min'][:16]} .. "
                  f"{f['test_launch_max'][:16]}   train {f['train_launch_min'][:16]} .. "
                  f"{f['train_launch_max'][:16]}")
        a3s["temporal_holdout"] = {}
        for name, feats, data in (("timing", timing, clean),
                                  ("structure", structure, clean),
                                  ("per_token_timing", pt.feature_names, pt)):
            a3s["temporal_holdout"][name] = {}
            for m in MODELS:
                r = audit.temporal_holdout(data, launch, features=feats, model=m,
                                           groups=comps)
                a3s["temporal_holdout"][name][m] = r
                print(f"  temporal {name:<17} {m:<9} AUC {r.get('auc')}  "
                      f"train {r['train_launch_min'][:10]}..{r['train_launch_max'][:10]} "
                      f"({r['train_tokens']}t, {r['train_pos_tokens']} RUG)  "
                      f"test {r['test_launch_min'][:10]}..{r['test_launch_max'][:10]} "
                      f"({r['test_tokens']}t, {r['test_pos_tokens']} RUG)")
        out["A3_split"] = a3s

        # ---- A3: what the features may see -------------------------------
        out["A3_static"] = _static_checks(s, args.chain, clean)
        print(f"\nA3 — static checks: {out['A3_static']}")

    p = Path(args.out)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=1, default=str), encoding="utf8")
    print(f"\nwrote {p}")
    return 0


def _spearman(a: np.ndarray, b: np.ndarray) -> float:
    ra = np.argsort(np.argsort(a))
    rb = np.argsort(np.argsort(b))
    return float(np.corrcoef(ra, rb)[0, 1])


def _static_checks(s, chain: str, clean: ds.Dataset) -> dict:
    from sqlalchemy import text
    window = s.execute(text("""
        select count(*) filter (where w.as_of_ts <> l.launch_ts + interval '24 hours'),
               count(*)
        from wallet_feature w
        join token_label l on l.token_address = w.token_address and l.chain = w.chain
        where w.chain = :c
    """), {"c": chain}).one()
    label_fields = {"peak_reserve", "reserve_at_end", "peak_price", "price_at_end",
                    "largest_drop", "active_days", "sibling_pairs", "outflow"}
    hits = [n for n in clean.feature_names if any(f in n for f in label_fields)]
    return {
        "feature_rows_with_cutoff_not_launch_plus_24h": int(window[0]),
        "feature_rows_checked": int(window[1]),
        "features_named_after_label_fields": hits,
    }


if __name__ == "__main__":
    raise SystemExit(main())
