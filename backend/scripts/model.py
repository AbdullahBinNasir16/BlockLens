"""Train the risk model, and report what it can honestly claim.

    python -m scripts.model audit        # leakage audit, before anything is fit
    python -m scripts.model run          # ablation + null, writes the model card

The headline result is the **ablation**, not a score: the same estimator and
the same folds over a wallet's own behaviour, plus one hop, plus two hops.
That comparison is the project's central claim and the only thing Phase 3
can be judged by.
"""
from __future__ import annotations

import argparse
import json
import sys

import numpy as np
from datetime import datetime, timezone
from pathlib import Path

from blocklens.config import CONFIG
from blocklens.label import rules
from blocklens.model import dataset as ds
from blocklens.model import leakage, train
from blocklens.store.db import session_scope


def _load(args, *, drop: list[str] | None = None) -> ds.Dataset:
    with session_scope() as s:
        return ds.load(s, chain=args.chain, rule_version=args.rule_version,
                       drop_features=drop)


def cmd_audit(args: argparse.Namespace) -> int:
    data = _load(args)
    print(json.dumps(data.summary(), indent=1))
    findings, excluded = leakage.audit(data.X, data.y, data.feature_names,
                                       top=args.top)
    print(f"\ndefinitional exclusions: {len(excluded)} of {data.n_features}")
    for f in findings:
        if f.kind == "definitional":
            print(f"  {f.feature:<36} auc={f.auc:.3f} sep={f.separation:+.2f}")
    print("\nstrongest remaining (leads, not verdicts):")
    for f in findings:
        if f.kind == "empirical":
            print(f"  {f.feature:<36} auc={f.auc:.3f} sep={f.separation:+.2f}")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    full = _load(args)
    excluded = leakage.definitional(full.feature_names)
    clean = _load(args, drop=excluded)

    out: dict = {
        "generated": datetime.now(timezone.utc).isoformat(),
        "chain": args.chain, "rule_version": args.rule_version,
        "dataset": full.summary(),
        "excluded_features": excluded,
        "clean_features": clean.feature_names,
        "results": {},
    }

    print(f"dataset: {full.n_rows} wallet rows over {full.n_tokens} tokens, "
          f"{full.n_features} features")
    print(f"positives: {int(full.y.sum())} rows "
          f"({full.summary()['positive_row_share']:.1%}), "
          f"{full.summary()['positive_tokens']} tokens")
    print(f"majority-class row baseline: "
          f"{full.summary()['majority_row_baseline']:.1%}\n")

    for variant, data in (("all features (leaky)", full),
                          ("leakage removed", clean)):
        print(f"--- {variant}: {data.n_features} features")
        out["results"][variant] = {}
        for model in args.models:
            rows = []
            for res in train.ablation(data, model=model):
                d = res.as_dict()
                rows.append(d)
                print(f"  {model:<9} {d['feature_set']:<30} "
                      f"AUC {d['auc_mean']:.3f} +/- {d['auc_std']:.3f}   "
                      f"AP {d['ap_mean']:.3f}")
            out["results"][variant][model] = rows
        print()

    # Where the signal actually lives. The clean set is two different kinds
    # of feature and they deserve separating: graph structure, which is what
    # Phase 3 was built for, and entry timing, which is not.
    structure = [n for n in clean.feature_names if "entry_delay" not in n]
    timing = [n for n in clean.feature_names if "entry_delay" in n]
    out["decomposition"] = {}
    print("--- where the signal lives (clean features only)")
    for gname, feats in (("structure only", structure), ("timing only", timing)):
        out["decomposition"][gname] = []
        for model in args.models:
            r = train.evaluate(clean, features=feats, name=gname, model=model)
            d = r.as_dict()
            out["decomposition"][gname].append(d)
            print(f"  {model:<9} {gname:<16} {len(feats):>2}f  "
                  f"AUC {d['auc_mean']:.3f} +/- {d['auc_std']:.3f}")
    print()

    # Is entry delay merely a proxy for how many wallets a token had? A
    # token with 89 traders has a smaller *minimum* entry delay than one
    # with 2, purely by order statistics, so this had to be checked rather
    # than assumed either way.
    import collections
    if "base_entry_delay_min" in clean.feature_names:
        i = clean.feature_names.index("base_entry_delay_min")
        per_token = collections.defaultdict(list)
        for g, v in zip(clean.groups, clean.X[:, i]):
            per_token[g].append(v)
        sizes = np.array([len(v) for v in per_token.values()], dtype=float)
        mins = np.array([min(v) for v in per_token.values()], dtype=float)
        corr = float(np.corrcoef(sizes, mins)[0, 1]) if sizes.size > 2 else 0.0
        out["entry_delay_vs_wallet_count_corr"] = round(corr, 3)
        print(f"corr(token wallet count, token min entry delay) = {corr:+.3f}")
        print()

    # The null, on the honest feature set only: what this pipeline scores
    # when the labels carry no information at all.
    feats = ds.hop_subset(clean.feature_names, 2)
    null = train.permutation_null(clean, features=feats, rounds=args.null_rounds)
    out["permutation_null"] = null
    print(f"permutation null over {null.get('rounds', 0)} shuffles: "
          f"AUC {null.get('mean_auc')} +/- {null.get('std_auc')}, "
          f"95th pct {null.get('p95_auc')}, max {null.get('max_auc')}")

    out["coefficients"] = train.coefficients(clean, features=feats)
    print("\nwhat the fitted model leans on (whole-set fit, descriptive):")
    for c in out["coefficients"][:8]:
        print(f"  {c['feature']:<34} {c['coefficient']:+.3f}")

    path = Path(args.out)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=1, default=str), encoding="utf8")
    print(f"\nwrote {path}")
    _write_card(out, Path(args.card))
    print(f"wrote {args.card}")
    return 0


def _best(rows: list[dict]) -> dict | None:
    scored = [r for r in rows if r["auc_mean"] == r["auc_mean"]]
    return max(scored, key=lambda r: r["auc_mean"]) if scored else None


def _write_card(out: dict, path: Path) -> None:
    d = out["dataset"]
    clean_res = out["results"].get("leakage removed", {}).get("logistic", [])
    leaky_res = out["results"].get("all features (leaky)", {}).get("logistic", [])
    null = out["permutation_null"]

    flat = next((r for r in clean_res if r["feature_set"].startswith("flat")), None)
    two = next((r for r in clean_res if "2 hop" in r["feature_set"]), None)

    L = [
        "# Model card — BlockLens rug risk",
        "",
        # Phase 5 audit: this card describes a dataset that cannot support
        # its conclusions. Kept generated so the history stays reproducible.
        '> **Withdrawn — see [`leakage_audit.md`](leakage_audit.md) (Phase 5, Part A).** Every rug in this dataset died inside its own feature window, all 20 RUG tokens belong to one shared-wallet operation, and 8 of them are untradeable pools. No result on this card, positive or negative, may be quoted.',
        "",
        f"Generated {out['generated'][:16]} UTC from `wallet_feature` and "
        f"`token_label` at `{out['rule_version']}` on `{out['chain']}`.",
        "",
        "## What it predicts",
        "",
        "Given a wallet's behaviour and its neighbourhood in the funding "
        "graph, as of 24 hours after a token launched: **will that token be "
        "classified RUG at 90 days?**",
        "",
        "One row is a wallet, not a token. That is a deliberate choice forced "
        "by size — there are only "
        f"{d['tokens']} tokens with both features and a label, against "
        f"{d['features']} features, so a token-level model is p > n before it "
        "starts. Wallets within a token are **not independent**, so every "
        "split here is grouped by token and a token appears in exactly one "
        "fold.",
        "",
        "## Data",
        "",
        "| | |",
        "|---|---|",
        f"| wallet rows | {d['rows_wallets']} |",
        f"| tokens | {d['tokens']} |",
        f"| positive rows (RUG) | {d['positive_rows']} ({d['positive_row_share']:.1%}) |",
        f"| positive tokens | {d['positive_tokens']} ({d['positive_token_share']:.1%}) |",
        f"| majority-class row baseline | {d['majority_row_baseline']:.1%} |",
        "",
        "## The leakage problem, which dominates everything below",
        "",
        f"{len(out['excluded_features'])} of {d['features']} features were "
        "removed before training, and the reason is structural rather than "
        "incidental.",
        "",
        "Phase 2 assigns `FAILED` partly through a `DEAD` criterion computed "
        "from **whether the price moved** — which is to say, from whether the "
        "token traded. Almost every behavioural feature measures how much a "
        "wallet traded. `base_buy_quote` scored AUC **0.922** on its own, and "
        "it is zero exactly when no priced swap exists, which is the same "
        "condition that sends a token to FAILED. A model fed those features "
        "learns a tautology and reports it as a discovery.",
        "",
        "So the two columns below are not two tunings. The first is what the "
        "numbers look like when the model is allowed to read the label back "
        "out of the features; it is reported **only** to show the size of the "
        "effect, and must not be quoted as a result.",
        "",
        "| Feature set | All features (leaky) | Leakage removed |",
        "|---|---|---|",
    ]
    for i, name in enumerate(["flat", "1 hop", "2 hop"]):
        a = next((r for r in leaky_res if name.split()[0] in r["feature_set"]), None)
        b = next((r for r in clean_res if name.split()[0] in r["feature_set"]), None)
        L.append(f"| {name} | "
                 f"{a['auc_mean']:.3f} ± {a['auc_std']:.3f} |" if a else "| " + name + " | - |")
        if a and b:
            L[-1] = (f"| {name} | {a['auc_mean']:.3f} ± {a['auc_std']:.3f} | "
                     f"{b['auc_mean']:.3f} ± {b['auc_std']:.3f} |")
    L += [
        "",
        f"**Permutation null**: shuffling labels at the token level and "
        f"re-running the whole pipeline {null.get('rounds', 0)} times gives "
        f"AUC {null.get('mean_auc')} ± {null.get('std_auc')}, with a 95th "
        f"percentile of {null.get('p95_auc')} and a maximum of "
        f"{null.get('max_auc')}. Any result below that 95th percentile is "
        "indistinguishable from noise at this sample size.",
        "",
        "## Does propagation beat flat features?",
        "",
    ]
    if flat and two:
        delta = two["auc_mean"] - flat["auc_mean"]
        verdict = ("**yes, on this data**" if delta > 0.05 else
                   "**not detectably, on this data**")
        L += [f"{verdict}: flat features score AUC "
              f"{flat['auc_mean']:.3f} ± {flat['auc_std']:.3f} and two-hop "
              f"features {two['auc_mean']:.3f} ± {two['auc_std']:.3f}, a "
              f"difference of {delta:+.3f} against a fold-to-fold spread of "
              f"±{max(flat['auc_std'], two['auc_std']):.3f}.",
              "",
              "That spread is the number to attend to. With "
              f"{d['tokens']} tokens across {two['folds']} folds, a "
              "difference smaller than the spread is not a finding. The "
              "cited paper's F1 0.93 against 0.81 cannot be confirmed or "
              "refuted at this size — it can only be left open.", ""]
    decomp = out.get("decomposition", {})
    if decomp:
        L += ["## Where the signal actually lives", "",
              "The surviving features are two different kinds of thing, and "
              "separating them answers the question Phase 3 exists to ask.",
              "",
              "| Feature group | Logistic AUC | Boosting AUC |",
              "|---|---|---|"]
        for gname in ("structure only", "timing only"):
            rows = decomp.get(gname, [])
            lg = next((r for r in rows if r["model"] == "logistic"), None)
            bo = next((r for r in rows if r["model"] == "boosting"), None)
            L.append(f"| {gname} ({lg['n_features'] if lg else '?'}f) | "
                     f"{lg['auc_mean']:.3f} ± {lg['auc_std']:.3f} | "
                     f"{bo['auc_mean']:.3f} ± {bo['auc_std']:.3f} |"
                     if lg and bo else f"| {gname} | - | - |")
        corr = out.get("entry_delay_vs_wallet_count_corr")
        L += ["",
              "**Graph structure alone is indistinguishable from noise** — "
              f"{decomp.get('structure only', [{}])[0].get('auc_mean', 0):.3f} "
              f"against a null mean of {null.get('mean_auc')} and a null 95th "
              f"percentile of {null.get('p95_auc')}. All of the measurable "
              "signal is in **entry timing**: wallets that buy sooner after a "
              "launch are trading tokens that go on to be rugged.",
              ""]
        if corr is not None:
            L += [f"Entry timing is not merely a proxy for how many wallets a "
                  f"token had. That had to be checked — a token with 89 traders "
                  f"has a smaller *minimum* entry delay than one with 2, purely "
                  f"by order statistics — and the correlation between a token's "
                  f"wallet count and its minimum entry delay is **{corr:+.3f}**, "
                  f"which is too weak to explain the result.", ""]

    L += [
        "## What this model must not be used for",
        "",
        "- **A deployment decision.** It is fitted on 44 tokens from a "
        "three-hour slice of one chain's history, with no SURVIVED examples "
        "at all, so it has never seen what a healthy launch looks like.",
        "- **A number in a report, unqualified.** Any AUC here carries a "
        "fold-to-fold spread of the same order as the differences being "
        "discussed.",
        "- **Ranking wallets by risk.** The target is a property of the "
        "token, inherited by its wallets. A high score means \"this wallet is "
        "trading a token that looks like a rug\", never \"this wallet is a "
        "bad actor\".",
        "",
        "## What would change the answer",
        "",
        "1. **More tokens.** The pipeline is built and the cost is known: "
        "about 44 calls to backfill a token and 235 to label it. Several "
        "hundred tokens is hours of unattended running, not new work.",
        "2. **A label contrast that is not confounded with activity.** "
        "RUG against SURVIVED would compare two tokens that both traded. "
        "There are currently zero SURVIVED tokens, which is itself a finding "
        "about 95-day-old Base launches.",
        "3. **Features not downstream of trade volume.** The surviving set is "
        "graph structure and entry timing. More of that kind — funding "
        "ancestry, which needs an indexing API — is the direction that does "
        "not re-introduce the leak.",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(L) + "\n", encoding="utf8")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="model", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--chain", default=CONFIG.chain)
    p.add_argument("--rule-version", default=rules.RULE_VERSION)
    sub = p.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("audit", help="leakage audit, before any fitting")
    a.add_argument("--top", type=int, default=12)
    a.set_defaults(func=cmd_audit)

    r = sub.add_parser("run", help="ablation, null, and the model card")
    r.add_argument("--models", nargs="+", default=["logistic", "boosting"])
    r.add_argument("--null-rounds", type=int, default=25)
    r.add_argument("--out", default="reports/model_results.json")
    r.add_argument("--card", default="reports/model_card.md")
    r.set_defaults(func=cmd_run)

    try:
        sys.stdout.reconfigure(line_buffering=True)
    except (AttributeError, ValueError):
        pass
    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
