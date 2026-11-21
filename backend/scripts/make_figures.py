"""Every figure in the FYP-1 report, regenerated from the database in one go.

    python -m scripts.make_figures          # -> report/figures/generated/*.{pdf,svg}
                                            #    report/figures/generated/captions.{md,tex}
                                            #    results/manifest.json

No figure in the report is a screenshot or a hand drawing. Every number a
figure shows, and every headline number the report quotes, is written to
`results/manifest.json` by this run, with the git SHA it came from.

Standards (Phase 8 brief):
* vector output (PDF for LaTeX, SVG for the web), sized for an A4 page;
* one style for all eleven figures, set once below;
* colour-blind-safe colours (Okabe-Ito), and every series is also told
  apart by line style, marker or hatching, so a greyscale print still reads;
* axis labels with units; a caption per figure that works on its own.

Inputs: the PostgreSQL store, `data/phase5_features.json` and
`data/phase6_extraction.json` (the feature and extraction caches built by
`scripts/phase5_model.py features` and `scripts/phase6.py`), and
`reports/cluster_validation.json`. See REPRODUCE.md.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import networkx as nx  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402
from sklearn.inspection import permutation_importance  # noqa: E402
from sklearn.linear_model import LogisticRegression  # noqa: E402
from sklearn.metrics import average_precision_score, precision_recall_curve  # noqa: E402
from sklearn.model_selection import GroupKFold  # noqa: E402
from sqlalchemy import text  # noqa: E402

import scripts.phase6_model as m6  # noqa: E402
from blocklens.config import SEEDS  # noqa: E402
from blocklens.label import rules  # noqa: E402
from blocklens.live import resolver as rv  # noqa: E402
from blocklens.live.explain import LABELS  # noqa: E402
from blocklens.model import rulecheck, rulecheck_x  # noqa: E402
from blocklens.model import token_features as tf  # noqa: E402
from blocklens.sampling import design as d  # noqa: E402
from blocklens.store.db import session_factory  # noqa: E402
from scripts import label_sensitivity as ls  # noqa: E402
from scripts.phase5_model import boosting, logistic, matrix  # noqa: E402

BACKEND = Path(__file__).resolve().parents[1]
ROOT = BACKEND.parent
OUT = ROOT / "report" / "figures" / "generated"
MANIFEST = ROOT / "results" / "manifest.json"
SEED = SEEDS.sampling
BOOT = 1000

# ---- the one style --------------------------------------------------------
# Okabe-Ito: distinguishable under the common colour-vision deficiencies.
INK, GREY = "#222222", "#8a8a8a"
C = {"blue": "#0072B2", "orange": "#E69F00", "green": "#009E73", "vermillion": "#D55E00",
     "purple": "#CC79A7", "sky": "#56B4E9", "yellow": "#F0E442"}
# Every series also carries a non-colour cue.
SERIES = [
    dict(color=C["blue"], linestyle="-", marker="o", hatch=""),
    dict(color=C["vermillion"], linestyle="--", marker="s", hatch="///"),
    dict(color=C["green"], linestyle="-.", marker="^", hatch="..."),
    dict(color=C["purple"], linestyle=":", marker="D", hatch="xx"),
    dict(color=C["orange"], linestyle=(0, (5, 1, 1, 1)), marker="v", hatch="\\\\"),
]
plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 9, "axes.titlesize": 10, "axes.labelsize": 9,
    "xtick.labelsize": 8, "ytick.labelsize": 8, "legend.fontsize": 8, "legend.frameon": False,
    "axes.spines.top": False, "axes.spines.right": False, "axes.edgecolor": INK,
    "axes.labelcolor": INK, "xtick.color": INK, "ytick.color": INK, "text.color": INK,
    "axes.grid": True, "grid.color": "#dddddd", "grid.linewidth": 0.6, "grid.linestyle": "-",
    "lines.linewidth": 1.6, "lines.markersize": 4.5, "hatch.linewidth": 0.6,
    "savefig.bbox": "tight", "savefig.pad_inches": 0.04, "svg.fonttype": "none",
    "pdf.fonttype": 42, "figure.dpi": 100,
})
WIDTH = 6.3                      # inches: an A4 text block
CAPTIONS: dict[str, dict] = {}
NUMBERS: dict[str, object] = {}


def save(fig, name: str, title: str, caption: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "svg"):
        fig.savefig(OUT / f"{name}.{ext}")
    # A greyscale proof of every figure: what a black-and-white print shows.
    # Not used in the report; it is how "works in greyscale" is checked.
    from io import BytesIO
    from PIL import Image
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=150)
    (OUT / "greyscale_proof").mkdir(exist_ok=True)
    Image.open(buf).convert("L").save(OUT / "greyscale_proof" / f"{name}.png")
    plt.close(fig)
    CAPTIONS[name] = {"title": title, "caption": caption}
    print(f"  {name}")


def bars(ax, xs, hs, i, **kw):
    s = SERIES[i % len(SERIES)]
    return ax.bar(xs, hs, color=s["color"], hatch=s["hatch"], edgecolor=INK, linewidth=0.6, **kw)


def line(ax, x, y, i, **kw):
    s = SERIES[i % len(SERIES)]
    return ax.plot(x, y, color=s["color"], linestyle=s["linestyle"], marker=s["marker"], **kw)


# ---- shared data ----------------------------------------------------------

def labelled_population(s) -> list[dict]:
    rows = s.execute(text("""
        select s.token_address, s.sampling_stratum, s.launch_ts, l.label
        from token_sample s
        join token_label l on l.token_address = s.token_address and l.chain = s.chain
                           and l.rule_version = :rv
        where s.chain = 'base' and s.alive_at_cutoff and s.excluded_reason is null
    """), {"rv": rules.RULE_VERSION}).all()
    return [{"token": t, "stratum": st, "launch": lt, "label": lab} for t, st, lt, lab in rows]


def group_of(stratum: str) -> str:
    return "random cohort" if stratum == "random" else "case-control strata"


def family_ci(y, fam, s, rng, boot=BOOT):
    fams = sorted(set(fam))
    idx = defaultdict(list)
    for i, f in enumerate(fam):
        idx[f].append(i)
    vals = []
    for _ in range(boot):
        pick = rng.choice(len(fams), len(fams))
        ii = np.concatenate([idx[fams[k]] for k in pick])
        if 0 < y[ii].sum() < len(ii):
            vals.append(average_precision_score(y[ii], s[ii]))
    return [float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))]


# ---- figures --------------------------------------------------------------

def fig01_class_balance(pop):
    groups = ["case-control strata", "random cohort"]
    labels = ["RUG", "FAILED", "SURVIVED"]
    cnt = Counter((group_of(r["stratum"]), r["label"]) for r in pop)
    fig, (a, b) = plt.subplots(1, 2, figsize=(WIDTH, 2.6), gridspec_kw={"width_ratios": [1.2, 1]})
    bottom = np.zeros(len(groups))
    for i, lab in enumerate(labels):
        h = np.array([cnt[(g, lab)] for g in groups])
        bars(a, groups, h, i, bottom=bottom, label=lab, width=0.55)
        for k, v in enumerate(h):
            if v >= 12:
                a.text(k, bottom[k] + v / 2, str(v), ha="center", va="center", fontsize=7.5,
                       bbox=dict(facecolor="white", edgecolor="none", pad=0.6))
        bottom += h
    a.set_ylabel("tokens alive at minute 5 (count)")
    a.set_title("(a) labelled tokens by stratum")
    a.set_ylim(0, bottom.max() * 1.28)
    a.legend(loc="upper center", ncol=3, bbox_to_anchor=(0.5, 1.0), fontsize=7.5)
    # base rates of RUG
    rnd = [r for r in pop if r["stratum"] == "random"]
    pre = [r for r in rnd if r["launch"] < d.SPLIT_DATE]
    post = [r for r in rnd if r["launch"] >= d.SPLIT_DATE]
    trn = [r for r in pop if r["stratum"] != "random" and r["launch"] < d.SPLIT_DATE]
    rate = lambda rs: sum(r["label"] == "RUG" for r in rs) / max(1, len(rs))
    names = ["training", "random,\nbefore split", "random,\nafter split"]
    vals = [rate(trn), rate(pre), rate(post)]
    ns = [len(trn), len(pre), len(post)]
    for i, (nm, v) in enumerate(zip(names, vals)):
        bars(b, [nm], [v * 100], 0, width=0.55)
        b.text(i, v * 100 + 1.5, f"{v:.1%}\nn={ns[i]}", ha="center", va="bottom", fontsize=7.5)
    b.set_ylabel("share labelled RUG (%)")
    b.set_ylim(0, max(vals) * 100 * 1.35)
    b.set_title("(b) RUG base rate")
    NUMBERS["dataset.labelled_alive"] = len(pop)
    NUMBERS["dataset.by_group_and_label"] = {f"{g}/{l}": cnt[(g, l)] for g in groups for l in labels}
    NUMBERS["dataset.rug_rate"] = {"training_sampled": round(vals[0], 4), "random_before_split": round(vals[1], 4),
                                   "random_after_split": round(vals[2], 4), "n": ns}
    save(fig, "fig01_class_balance", "Class balance and base rate",
         f"Labelled tokens alive at launch + 5 minutes ({len(pop):,}), by how they were sampled (a) and the "
         f"share labelled RUG (b). The case-control strata deliberately over-sample rare outcomes, so their "
         f"RUG rate ({vals[0]:.1%}) is a design choice, not a property of Base; the random cohort gives the "
         f"true rate, which moved from {vals[1]:.1%} before the {d.SPLIT_DATE:%d %b %Y} split to {vals[2]:.1%} "
         f"after it. Any metric read without the random cohort's base rate beside it is uninterpretable.")


def fig02_label_sensitivity(s):
    rows = ls.load(s, chain="base", rule_version=rules.RULE_VERSION)
    base = ls.classify_all(rows)
    n = len(rows)
    sweeps = ls.SWEEPS
    fig, axes = plt.subplots(2, 4, figsize=(WIDTH, 3.8))
    out = {}
    for ax, (attr, title, values, shape) in zip(axes.flat, sweeps):
        cur = getattr(rules, attr)
        ch = []
        for v in values:
            with ls.temporarily(attr, v):
                got = ls.classify_all(rows)
            ch.append(sum(1 for k, lab in got.items() if lab != base[k]))
        xs = list(range(len(values)))
        line(ax, xs, ch, 0)
        ci = values.index(cur) if cur in values else None
        if ci is not None:
            ax.plot([ci], [ch[ci]], marker="o", markersize=8, markerfacecolor="white",
                    markeredgecolor=INK, linestyle="none")
        ax.set_xticks(xs, [shape.format(v).replace(" of peak", "").replace(" of samples", "").replace(" days", "d")
                           for v in values], rotation=60)
        ax.set_title(title, fontsize=8.5)
        out[attr] = dict(zip([str(v) for v in values], ch))
    ax = axes.flat[len(sweeps)]
    ch = []
    for w in ls.WINDOWS:
        got = ls.classify_all(rows, window_days=w)
        ch.append(sum(1 for k, lab in got.items() if lab != base[k]))
    line(ax, list(range(len(ls.WINDOWS))), ch, 1)
    ax.set_xticks(range(len(ls.WINDOWS)), [f"{w}d" for w in ls.WINDOWS], rotation=60)
    ax.set_title("Observation window", fontsize=8.5)
    out["window_days"] = dict(zip([str(w) for w in ls.WINDOWS], ch))
    for ax in axes.flat[len(sweeps) + 1:]:
        ax.axis("off")
    for ax in axes[:, 0]:
        ax.set_ylabel("tokens changing class")
    worst = max(max(v.values()) for v in out.values())
    fig.tight_layout(h_pad=0.6, w_pad=0.4)
    NUMBERS["label_sensitivity"] = {"tokens": n, "rule_version": rules.RULE_VERSION, "changed": out,
                                    "max_changed": worst}
    near = {}
    for attr, title, values, shape in sweeps:
        cur = getattr(rules, attr)
        if cur in values:
            i = values.index(cur)
            nb = [out[attr][str(v)] for v in values[max(0, i - 1):i + 2] if v != cur]
            near[title] = max(nb) if nb else 0
    stable = sorted(near.items(), key=lambda kv: kv[1])
    dead = out["DEAD_ACTIVE_DAYS"]
    win = out["window_days"]
    save(fig, "fig02_label_sensitivity", "Label sensitivity",
         f"How many of the {n:,} labelled tokens change class when one labelling threshold is moved and the "
         f"rest are held at their current values (open circle: the value in use; each panel has its own scale). "
         f"Every verdict is re-derived from the stored pool observations. One step either side of the value in "
         f"use moves at most {max(near.values())} tokens ({max(near.values()) / n:.1%}). The label is not robust "
         f"everywhere: calling a token dead only if it never trades again (dead-day cutoff 0) moves "
         f"{dead['0']} tokens, and observing for fewer than 60 days instead of 90 moves {min(win['7'], win['14'], win['30'])}"
         f"-{max(win['7'], win['14'], win['30'])}, because FAILED needs a long observation to be told apart from "
         f"a slow token.")


def fig03_launch_dates(pop):
    labels = ["RUG", "FAILED", "SURVIVED"]
    t0 = min(r["launch"] for r in pop)
    weeks = lambda dt: int((dt - t0).total_seconds() // (7 * 86400))
    nweeks = max(weeks(r["launch"]) for r in pop) + 1
    edges = [t0 + timedelta(weeks=w) for w in range(nweeks + 1)]
    fig, ax = plt.subplots(figsize=(WIDTH, 2.5))
    for i, lab in enumerate(labels):
        h = np.zeros(nweeks)
        for r in pop:
            if r["label"] == lab:
                h[weeks(r["launch"])] += 1
        xs = [e for e in edges[:-1]]
        s = SERIES[i]
        ax.step(xs, h, where="post", color=s["color"], linestyle=s["linestyle"], label=f"{lab} ({int(h.sum())})")
    ax.axvline(d.SPLIT_DATE, color=INK, linewidth=1.0)
    ax.text(d.SPLIT_DATE, ax.get_ylim()[1] * 0.95, f"  split {d.SPLIT_DATE:%d %b}", fontsize=7.5, va="top")
    ax.set_ylabel("tokens launched per week (count)")
    ax.set_xlabel("launch date (2026, weekly bins)")
    ax.legend(loc="upper left")
    fig.autofmt_xdate()
    save(fig, "fig03_launch_dates", "Launch dates per class",
         "Weekly launch counts per class for every labelled token alive at minute 5, with the temporal "
         f"split on {d.SPLIT_DATE:%d %B %Y} (vertical line). Models are trained only on launches before it and "
         "tested on launches after it, so a model cannot learn from the period it is judged on. The class mix "
         "is not stable across the split: after it, RUG dominates, which is why results are reported per period.")


def t2_sets():
    sets = m6.load()
    names = sorted({k for r in sets["TRAIN"] for k in r if k.startswith(("t_", "g_", "r_"))})
    tr, ytr = m6.scored(sets["TRAIN"], "t2")
    ca, yca = m6.scored(sets["CAL"], "t2")
    return sets, names, tr, ytr, ca, yca


def fig04_pr_curves(names, tr, ytr, ca, yca):
    fam = [r["family"] for r in ca]
    rng = np.random.default_rng(SEED)
    scores = {
        "rule checker (Phase 5, 5 flags)": np.array([rulecheck.score(r) for r in ca], float),
        "early-concentration checker": np.array([rulecheck_x.score(r) for r in ca], float),
        "logistic regression (23 features)": logistic(1.0).fit(matrix(tr, names), ytr).predict_proba(matrix(ca, names))[:, 1],
        "gradient boosting (23 features)": boosting().fit(matrix(tr, names), ytr).predict_proba(matrix(ca, names))[:, 1],
    }
    fig, ax = plt.subplots(figsize=(WIDTH * 0.72, 3.6))
    res = {}
    for i, (nm, sc) in enumerate(scores.items()):
        p, r, _ = precision_recall_curve(yca, sc)
        ap = average_precision_score(yca, sc)
        ci = family_ci(yca, fam, sc, rng)
        res[nm] = {"pr_auc": round(ap, 4), "ci95": [round(x, 4) for x in ci]}
        st = SERIES[i]
        ax.step(r, p, where="post", color=st["color"], linestyle=st["linestyle"],
                label=f"{nm}: {ap:.2f}")
    ax.axhline(yca.mean(), color=GREY, linewidth=1.0, linestyle=(0, (2, 2)))
    ax.text(0.01, yca.mean() - 0.045, f"base rate {yca.mean():.2f}", ha="left", fontsize=7.5, color=GREY)
    ax.set_xlabel("recall (share of losses caught)")
    ax.set_ylabel("precision (share of flags that were losses)")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1.02)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.17), ncol=1, title="PR-AUC on this set", title_fontsize=8)
    NUMBERS["buyer_loss.cal"] = {"tokens": len(yca), "losses": int(yca.sum()), "base_rate": round(float(yca.mean()), 4),
                                 "models": res}
    b = res["gradient boosting (23 features)"]
    rc = res["early-concentration checker"]
    save(fig, "fig04_pr_curves", "Precision-recall, three baselines",
         f"Precision-recall on the random cohort before the split ({len(yca)} tokens, {int(yca.sum())} buyer "
         f"losses, base rate {yca.mean():.2f}) for the target 'a buy at minute 5 is worth half or less at hour 6'. "
         f"Models were trained on the case-control strata, with no operator family on both sides. Gradient "
         f"boosting reaches PR-AUC {b['pr_auc']:.2f} (95% family bootstrap {b['ci95'][0]:.2f}-{b['ci95'][1]:.2f}); "
         f"the fixed rule checkers sit near the base rate ({rc['pr_auc']:.2f}). This set is out of sample but not "
         f"out of time (Figure 6).")
    return scores


def platt_crossfit(y, s, fam, k=5):
    out = np.zeros_like(s, dtype=float)
    z = np.log(np.clip(s, 1e-4, 1 - 1e-4) / (1 - np.clip(s, 1e-4, 1 - 1e-4)))[:, None]
    for a, b in GroupKFold(n_splits=k).split(z, y, fam):
        m = LogisticRegression(C=1e6, max_iter=1000).fit(z[a], y[a])
        out[b] = m.predict_proba(z[b])[:, 1]
    return out


def rel_bins(y, p, edges):
    pts = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (p >= lo) & (p < hi) if hi < 1 else (p >= lo) & (p <= hi)
        if m.sum() >= 5:
            pts.append((float(p[m].mean()), float(y[m].mean()), int(m.sum())))
    return pts


def fig05_reliability(scores, ca, yca, s):
    raw = scores["gradient boosting (23 features)"]
    fam = np.array([r["family"] for r in ca])
    cal = platt_crossfit(yca, raw, fam)
    edges = np.quantile(raw, np.linspace(0, 1, 6))
    edges[0], edges[-1] = 0.0, 1.0
    fig, (a, b) = plt.subplots(1, 2, figsize=(WIDTH, 2.9))
    for ax in (a, b):
        ax.plot([0, 1], [0, 1], color=GREY, linestyle=(0, (2, 2)), linewidth=1.0)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.set_xlabel("mean predicted probability")
    rb = rel_bins(yca, raw, edges)
    ce = np.quantile(cal, np.linspace(0, 1, 6))
    ce[0], ce[-1] = 0.0, 1.0
    rc = rel_bins(yca, cal, ce)
    for i, (pts, nm) in enumerate(((rb, "before: raw boosting"), (rc, "after: cross-fitted Platt"))):
        line(a, [x for x, _, _ in pts], [y for _, y, _ in pts], i, label=nm)
    brier = lambda p: float(np.mean((p - yca) ** 2))
    a.set_ylabel("observed share of buyer losses")
    a.set_title(f"(a) random cohort, Jan-Apr, n={len(yca)}", fontsize=9)
    a.legend(loc="upper left")
    fwd = rv.scoreboard(s)
    bins = fwd["buyer_loss"].get("reliability") or []
    xs = [b_["mean_predicted"] for b_ in bins if b_["n"] >= 20]
    ys = [b_["observed"] for b_ in bins if b_["n"] >= 20]
    line(b, xs, ys, 0, label="raw buyer-loss-v1, forward")
    b.set_title(f"(b) forward record, n={fwd['buyer_loss']['resolved']:,}", fontsize=9)
    b.legend(loc="upper left")
    NUMBERS["calibration"] = {"cal_brier_raw": round(brier(raw), 4), "cal_brier_platt": round(brier(cal), 4),
                              "cal_brier_base_rate": round(float(np.mean((yca.mean() - yca) ** 2)), 4),
                              "forward_brier": fwd["buyer_loss"].get("brier"),
                              "forward_brier_base_rate": fwd["buyer_loss"].get("brier_base_rate"),
                              "forward_mean_predicted": fwd["buyer_loss"].get("mean_predicted"),
                              "forward_base_rate": fwd["buyer_loss"].get("base_rate")}
    c = NUMBERS["calibration"]
    save(fig, "fig05_reliability", "Reliability before and after calibration",
         f"Reliability curves (points: equal-count bins; dashed line: perfect calibration). (a) On the random "
         f"cohort before the split, raw boosting (Brier {c['cal_brier_raw']:.3f}) against the same scores after "
         f"Platt scaling fitted out of fold by operator family (Brier {c['cal_brier_platt']:.3f}; base-rate "
         f"Brier {c['cal_brier_base_rate']:.3f}). (b) The frozen live model on launches it had never seen: its "
         f"scores average {c['forward_mean_predicted']:.3f} against an observed rate of {c['forward_base_rate']:.3f}, "
         f"and its Brier ({c['forward_brier']:.3f}) is worse than always predicting the base rate "
         f"({c['forward_brier_base_rate']:.3f}). The model ranks well forward but its probabilities are not "
         f"calibrated, which is why the product shows the forward band, not the raw score.")


def fig06_decay(sets, names, s):
    rows = [r for side in ("TRAIN", "CAL", "EVAL") for r in sets[side] if r["t2"] is not None]
    cut = datetime(2026, 3, 1, tzinfo=timezone.utc)
    train = [r for r in rows if r["launch"] < cut]
    held = {r["family"] for r in train}
    test = [r for r in sets["CAL"] + sets["EVAL"] if r["t2"] is not None and r["launch"] >= cut
            and r["family"] not in held]
    y_tr = np.array([r["t2"] for r in train])
    m = boosting().fit(matrix(train, names), y_tr)
    months = sorted({(r["launch"].year, r["launch"].month) for r in test})
    res = []
    for ym in months:
        rs = [r for r in test if (r["launch"].year, r["launch"].month) == ym]
        y = np.array([r["t2"] for r in rs])
        p = m.predict_proba(matrix(rs, names))[:, 1]
        ap = float(average_precision_score(y, p)) if 0 < y.sum() < len(y) else None
        res.append({"month": f"{ym[0]}-{ym[1]:02d}", "tokens": len(rs), "losses": int(y.sum()),
                    "base_rate": round(float(y.mean()), 4), "pr_auc": None if ap is None else round(ap, 4)})
    marapr = [r for r in test if r["launch"] < datetime(2026, 4, 18, tzinfo=timezone.utc)]
    y = np.array([r["t2"] for r in marapr])
    oot = float(average_precision_score(y, m.predict_proba(matrix(marapr, names))[:, 1]))
    rcx = float(average_precision_score(y, np.array([rulecheck_x.score(r) for r in marapr], float)))
    # forward, by week, valid predictions only
    q = s.execute(text(f"""
        select date_trunc('week', launch_ts at time zone 'UTC') w, risk, buyer_loss from live_prediction
        where chain = 'base' and status = 'scored' and buyer_loss is not null
          and scored_at <= launch_ts + interval '6 hours' and {rv.VALID_SQL}
    """), rv.VALID_PARAMS).all()
    wk = defaultdict(list)
    for w, r_, y_ in q:
        wk[w].append((float(r_), int(bool(y_))))
    fwd = []
    for w in sorted(wk):
        a = np.array(wk[w])
        if len(a) >= 50 and 0 < a[:, 1].sum() < len(a):
            fwd.append({"week": w.date().isoformat(), "launches": len(a), "losses": int(a[:, 1].sum()),
                        "base_rate": round(float(a[:, 1].mean()), 4),
                        "pr_auc": round(float(average_precision_score(a[:, 1], a[:, 0])), 4)})
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(WIDTH, 2.8), gridspec_kw={"width_ratios": [1.1, 1]})
    xs = np.arange(len(res))
    pr = [r_["pr_auc"] if r_["pr_auc"] is not None else 0 for r_ in res]
    bars(a1, xs - 0.18, pr, 0, width=0.36, label="model PR-AUC")
    bars(a1, xs + 0.18, [r_["base_rate"] for r_ in res], 1, width=0.36, label="base rate")
    for i, r_ in enumerate(res):
        lab = f"n={r_['tokens']}\n{r_['losses']} loss" + ("" if r_["losses"] == 1 else "es")
        if r_["pr_auc"] is None:
            lab += "\nundefined"
        a1.text(i, max(pr[i], r_["base_rate"]) + 0.03, lab, ha="center", fontsize=6.8)
    a1.set_xticks(xs, [r_["month"][5:] + "/26" for r_ in res])
    a1.set_ylim(0, 1.25)
    a1.set_ylabel("PR-AUC / base rate")
    a1.set_xlabel("test month (trained before 1 Mar 2026)")
    a1.set_title("(a) research data, out of time")
    a1.legend(loc="upper center", ncol=2, bbox_to_anchor=(0.5, 1.0), fontsize=7.5)
    a1.set_ylim(0, 1.45)
    xf = np.arange(len(fwd))
    line(a2, xf, [f_["pr_auc"] for f_ in fwd], 0, label="buyer-loss-v1 PR-AUC")
    line(a2, xf, [f_["base_rate"] for f_ in fwd], 1, label="base rate")
    a2.set_xticks(xf, [f_["week"][5:] for f_ in fwd], rotation=45)
    a2.set_ylim(0, max([f_["pr_auc"] for f_ in fwd] + [0.1]) * 1.3)
    a2.set_xlabel("week of launch (2026)")
    a2.set_title("(b) live forward record, frozen model")
    a2.legend(loc="upper left")
    NUMBERS["decay"] = {"by_month": res, "oot_mar1_apr17": {"tokens": len(marapr), "losses": int(y.sum()),
                        "pr_auc": round(oot, 4), "early_concentration_checker": round(rcx, 4),
                        "model_card_reported": 0.758}, "forward_by_week": fwd}
    save(fig, "fig06_decay", "Performance by test period",
         f"(a) A model trained only on launches before 1 March 2026, scored on each later month of the random "
         f"cohort. On 1 March-17 April combined it reaches PR-AUC {oot:.3f} ({len(marapr)} tokens; the "
         f"early-concentration checker {rcx:.3f}). From May, buyer losses almost vanish from the data, so PR-AUC "
         f"rests on a handful of positives or is undefined. (b) The frozen live model, week by week, on launches "
         f"that had not happened when it was trained; weeks with fewer than 50 resolved launches are omitted, "
         f"the weeks around Base's block-time switch (5-16 November) are excluded by rule, and the last week is "
         f"still resolving oldest-first. Performance moves with the base rate and the launch mix (a scam wave on "
         f"one launchpad template from 3 November), not steadily down.")


def fig07_importance(names, tr, ytr, ca, yca):
    m = boosting().fit(matrix(tr, names), ytr)
    pi = permutation_importance(m, matrix(ca, names), yca, scoring="average_precision",
                                n_repeats=30, random_state=SEED)
    order = np.argsort(-pi.importances_mean)[:20][::-1]
    fig, ax = plt.subplots(figsize=(WIDTH, 4.2))
    labs = [f"{LABELS.get(names[i], names[i])}  [{names[i]}]" for i in order]
    ax.barh(range(len(order)), pi.importances_mean[order], xerr=pi.importances_std[order],
            color=SERIES[0]["color"], edgecolor=INK, linewidth=0.5, error_kw=dict(ecolor=INK, lw=0.7, capsize=2))
    ax.axvline(0, color=INK, linewidth=0.8)
    ax.set_yticks(range(len(order)), labs, fontsize=7.2)
    ax.set_xlabel("drop in PR-AUC when the feature is shuffled (mean of 30 repeats, ±1 s.d.)")
    top = [{"feature": names[i], "mean": round(float(pi.importances_mean[i]), 4),
            "std": round(float(pi.importances_std[i]), 4)} for i in order[::-1]]
    NUMBERS["permutation_importance_top20"] = top
    save(fig, "fig07_importance", "Permutation feature importance",
         f"The 20 features whose shuffling most reduces gradient boosting's PR-AUC on the random cohort before "
         f"the split (30 repeats each; bars ±1 s.d.). The top feature, {LABELS.get(top[0]['feature'], top[0]['feature'])}, "
         f"costs {top[0]['mean']:.3f}. Graph features (g_) carry little weight, consistent with Figure 8. "
         f"Importance is measured on held-out data, so it says what the model relies on there, not what causes a loss.")


def fig08_three_way(names, tr, ytr, ca, yca):
    timing = tf.group(names, tf.TIMING) + tf.group(names, tf.RULE_INPUTS)
    graph = tf.group(names, tf.GRAPH)
    fam = [r["family"] for r in ca]
    rng = np.random.default_rng(SEED)
    res = {}
    fig, ax = plt.subplots(figsize=(WIDTH * 0.7, 2.7))
    groups = [("timing only", timing), ("graph only", graph), ("both", names)]
    for j, kind in enumerate(("logistic regression", "gradient boosting")):
        for i, (gname, feats) in enumerate(groups):
            mdl = (logistic(1.0) if j == 0 else boosting()).fit(matrix(tr, feats), ytr)
            p = mdl.predict_proba(matrix(ca, feats))[:, 1]
            ap = float(average_precision_score(yca, p))
            ci = family_ci(yca, fam, p, rng)
            res[f"{kind}: {gname}"] = {"features": len(feats), "pr_auc": round(ap, 4), "ci95": [round(x, 4) for x in ci]}
            x = i + (j - 0.5) * 0.28
            st = SERIES[j]
            ax.errorbar([x], [ap], yerr=[[ap - ci[0]], [ci[1] - ap]], fmt=st["marker"], color=st["color"],
                        markersize=6, capsize=3, label=kind if i == 0 else None)
    ax.axhline(yca.mean(), color=GREY, linewidth=1.0, linestyle=(0, (2, 2)))
    ax.text(2.45, yca.mean() + 0.01, "base rate", fontsize=7.5, color=GREY, ha="right")
    ax.set_xticks(range(3), [f"{g}\n({len(f)} features)" for g, f in groups])
    ax.set_ylabel("PR-AUC (95% family bootstrap)")
    ax.set_ylim(0, 1)
    ax.legend(loc="lower right")
    NUMBERS["graph_comparison"] = res
    b = res
    save(fig, "fig08_three_way", "Timing, graph, or both",
         f"PR-AUC with 95% family-bootstrap intervals for each feature group on the random cohort before the "
         f"split. With gradient boosting, timing features alone reach {b['gradient boosting: timing only']['pr_auc']:.2f} "
         f"and both together {b['gradient boosting: both']['pr_auc']:.2f}: the intervals overlap, so the wallet-graph "
         f"features add nothing measurable over entry timing. Graph features alone reach "
         f"{b['gradient boosting: graph only']['pr_auc']:.2f}. This is the outcome the project reports as its "
         f"graph result (DECISIONS.md, Phase 5 Part D and Phase 6).")


def fig09_comovement():
    v = json.loads((BACKEND / "reports" / "cluster_validation.json").read_text(encoding="utf8"))["measurements"]
    fig, axes = plt.subplots(1, 2, figsize=(WIDTH, 2.8), sharey=True)
    out = {}
    for ax, (key, title) in zip(axes, (("buys_only", "(a) buys only"), ("buy_or_sell", "(b) buys or sells"))):
        m = v[key]
        real, ctl = m["real"], m["shuffled_control"]
        cats = [("same\ncluster", real["cluster_rate"], real["cluster_co_moves"], real["cluster_pairs"]),
                ("random\npairs", real["random_rate"], real["random_co_moves"], real["random_pairs"]),
                ("shuffled\ncontrol", ctl["cluster_rate"], ctl["cluster_co_moves"], ctl["cluster_pairs"])]
        for i, (nm, r_, k, n) in enumerate(cats):
            bars(ax, [i], [r_ * 100], i, width=0.6)
            ax.text(i, r_ * 100 + 0.25, f"{r_:.1%}\n{k:,}/{n:,} pairs", ha="center", va="bottom", fontsize=7)
        ax.set_xticks(range(3), [c[0] for c in cats], fontsize=8)
        ax.set_title(f"{title}: lift {real['lift']:.1f}×, p = {real['p_value']:.2g}", fontsize=8.5)
        out[key] = {"cluster_rate": real["cluster_rate"], "cluster_pairs": real["cluster_pairs"],
                    "cluster_co_moves": real["cluster_co_moves"], "random_rate": real["random_rate"],
                    "lift": real["lift"], "p_value": real["p_value"], "shuffled_rate": ctl["cluster_rate"],
                    "shuffled_lift": ctl["lift"]}
    axes[0].set_ylabel("pairs that traded the same token\nwithin the window (%)")
    axes[0].set_ylim(0, 10.5)
    NUMBERS["comovement"] = out
    r = out["buys_only"]
    save(fig, "fig09_comovement", "Co-movement lift",
         f"How often two wallets trade the same token at about the same time: pairs inside one funding cluster, "
         f"random pairs, and a degree-preserving shuffle of the cluster graph. Cluster pairs co-move "
         f"{r['lift']:.1f}× as often as random pairs when only buys count (p = {r['p_value']:.2g}) and "
         f"{out['buy_or_sell']['lift']:.1f}× for buys or sells (p = {out['buy_or_sell']['p_value']:.1g}); the "
         f"shuffled control falls to {r['shuffled_lift']:.2f}×, so the effect is in the clusters, not the "
         f"degree structure. The counts are small ({r['cluster_co_moves']} of {r['cluster_pairs']} cluster pairs "
         f"for buys only), and the clusters are token-acquisition provenance, not ETH funding (Section on gaps).")


def fig10_cluster_case(s):
    funder = "0x46876d5bde89e716663973c5750959f2a5050520"
    seeded = s.execute(text("""select dst, ts, token_address from graph_edge
        where kind = 'funding' and src = :f order by dst"""), {"f": funder}).all()
    wallets = [w for w, _, _ in seeded]
    t_fund = seeded[0][1]
    seed_tok = seeded[0][2]
    events = []
    for tok in ("0x778711d426fdc19eb8b70767488d2b4b580251d6", "0xa397e19528b45e97bd19cc4781155cadeb8ad303"):
        rs = s.execute(text("""select t.to_address, t.tx_hash, t.block_ts from transfer t
            where t.chain = 'base' and t.token_address = :t and t.to_address = any(:w)
              and exists (select 1 from swap w where w.tx_hash = t.tx_hash)"""),
            {"t": tok, "w": wallets}).all()
        events.append({"token": tok, "wallets": len({r[0] for r in rs}), "txs": len({r[1] for r in rs}),
                       "first": min(r[2] for r in rs), "last": max(r[2] for r in rs)})
    G = nx.DiGraph()
    G.add_node("F")
    for w in wallets:
        G.add_edge("F", w)
    pos = {"F": (0, 0)}
    for k, w in enumerate(wallets):
        ang = 2 * np.pi * k / len(wallets)
        pos[w] = (np.cos(ang), np.sin(ang))
    fig, (a, b) = plt.subplots(1, 2, figsize=(WIDTH, 3.1), gridspec_kw={"width_ratios": [1, 1.25]})
    nx.draw_networkx_edges(G, pos, ax=a, edge_color=GREY, width=0.5, arrows=True, arrowsize=5,
                           arrowstyle="-|>", node_size=14)
    nx.draw_networkx_nodes(G, pos, nodelist=wallets, ax=a, node_size=14, node_color="white",
                           edgecolors=SERIES[0]["color"], linewidths=0.8)
    nx.draw_networkx_nodes(G, pos, nodelist=["F"], ax=a, node_size=260, node_color=SERIES[1]["color"],
                           edgecolors=INK, node_shape="s")
    a.text(0, -0.22, "funder\n(contract)", ha="center", va="top", fontsize=7.5,
           bbox=dict(facecolor="white", edgecolor="none", pad=0.5))
    a.set_title(f"(a) one transaction seeds {len(wallets)} wallets", fontsize=8.5)
    a.set_axis_off()
    a.set_aspect("equal")
    rows = [("seeded with token", t_fund, len(wallets), 1, seed_tok)] + \
           [(f"bundle {i + 1}: buy + spread", e["first"], e["wallets"], e["txs"], e["token"]) for i, e in enumerate(events)]
    mins = [(r[1] - t_fund).total_seconds() / 60 for r in rows]
    for i, (r, mnt) in enumerate(zip(rows, mins)):
        st = SERIES[i]
        b.plot([mnt], [r[2]], marker=st["marker"], color=st["color"], markersize=9, linestyle="none")
        off = [(8, 8), (-118, -40), (10, 10)][i]
        b.annotate(f"{r[0]}\n{r[2]} wallets in {r[3]} tx\ntoken {r[4][:8]}…", (mnt, r[2]),
                   textcoords="offset points", xytext=off, fontsize=7,
                   arrowprops=dict(arrowstyle="-", color=GREY, linewidth=0.6) if i == 1 else None)
    b.set_xlim(-5, max(mins) + 22)
    b.set_ylim(0, len(wallets) * 1.35)
    b.set_xlabel(f"minutes after seeding ({t_fund:%d %b %Y %H:%M} PKT)")
    b.set_ylabel("wallets reached (count)")
    b.set_title("(b) what happened to those wallets", fontsize=8.5)
    NUMBERS["cluster_case"] = {"funder": funder, "wallets": len(wallets), "seeded_at": t_fund.isoformat(),
                               "events": [{**e, "first": e["first"].isoformat(), "last": e["last"].isoformat()}
                                          for e in events]}
    e1, e2 = events
    save(fig, "fig10_cluster_case", "A funding cluster, drawn",
         f"A real cluster from the store (funder {funder[:10]}…, a contract). (a) One transaction sends a token to "
         f"{len(wallets)} wallets. (b) {mins[1]:.0f} minutes later, a single swap transaction buys token "
         f"{e1['token'][:8]}… and delivers it to {e1['wallets']} of them; {mins[2] - mins[1]:.0f} minutes after that, "
         f"another does the same with token {e2['token'][:8]}…. This is bundling: the wallets look like many "
         f"buyers on a token's holder list, but they are one actor's {e1['txs']}-transaction operation. It is not "
         f"{len(wallets)} independent decisions, and the search for independent wallets buying together within 90 "
         f"seconds found none in the store.")


def fig11_pipeline():
    fig, ax = plt.subplots(figsize=(WIDTH, 3.9))
    ax.set_xlim(-0.1, 12.1)
    ax.set_ylim(1.1, 6.9)
    ax.set_axis_off()

    def box(x, y, w, h, title, sub, i):
        st = SERIES[i % len(SERIES)]
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.12",
                                    facecolor="white", edgecolor=st["color"], linewidth=1.4,
                                    linestyle=st["linestyle"] if i % 2 else "-"))
        ax.text(x + w / 2, y + h * 0.7, title, ha="center", va="center", fontsize=6.5, weight="bold")
        ax.text(x + w / 2, y + h * 0.32, sub, ha="center", va="center", fontsize=5.6, color="#444444")

    def arrow(x1, y1, x2, y2, dashed=False):
        ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=9,
                                     color=INK, linewidth=0.9, linestyle="--" if dashed else "-"))

    box(0.1, 5.4, 2.3, 1.2, "Base chain", "keyless RPC pool\n(1,000-block log cap)", 0)
    box(0.1, 3.6, 2.3, 1.2, "Market sources", "GeckoTerminal, DexScreener,\nGoPlus (keyless)", 4)
    box(3.0, 5.4, 2.4, 1.2, "Ingestion", "pools, transfers, swaps;\ncall budget; chain clock", 1)
    box(6.0, 5.4, 2.3, 1.2, "PostgreSQL store", "token, pair, transfer,\nswap, wallet, graph_edge", 2)
    box(9.0, 5.4, 2.8, 1.2, "Labels", "rule v2 (RUG / FAILED /\nSURVIVED); extraction", 3)
    box(9.0, 3.4, 2.8, 1.2, "Features at minute 5", "23 token features\n(timing, rule, graph)", 0)
    box(6.0, 3.4, 2.3, 1.2, "Models", "rule checkers, logistic,\nboosting (frozen v1)", 1)
    box(3.0, 1.4, 2.4, 1.2, "Live scorer", "every new pool, once,\nat launch + 5 min", 2)
    box(6.0, 1.4, 2.3, 1.2, "Resolver", "outcome at 6 h; reserves\nat 1/7/30/90 days", 3)
    box(9.0, 1.4, 2.8, 1.2, "Forward record", "append-only log, timely\nonly; paper agent", 4)
    box(0.1, 1.4, 2.3, 1.2, "FastAPI + React", "contract-typed routes;\nlive or sample, badged", 0)
    arrow(2.4, 6.0, 3.0, 6.0)
    arrow(5.4, 6.0, 6.0, 6.0)
    arrow(8.3, 6.0, 9.0, 6.0)
    arrow(10.4, 5.4, 10.4, 4.6)
    arrow(9.0, 4.0, 8.3, 4.0)
    arrow(7.15, 3.4, 4.6, 2.6)
    arrow(5.4, 2.0, 6.0, 2.0)
    arrow(8.3, 2.0, 9.0, 2.0)
    arrow(3.0, 2.0, 2.4, 2.0)
    arrow(1.25, 3.6, 1.25, 2.6)
    arrow(2.4, 5.7, 3.4, 2.6, dashed=True)
    ax.text(2.55, 4.15, "head, logs", fontsize=6.3, rotation=-62, color="#444444")
    save(fig, "fig11_pipeline", "Pipeline",
         "The system as built. Research path (top): keyless RPC reads of Base go through ingestion into "
         "PostgreSQL, are labelled by rule, and become 23 features at launch + 5 minutes for the models. Live "
         "path (bottom): the scorer judges every new pool once at minute 5 with the frozen model, the resolver "
         "measures the outcome at hour 6 and later horizons, and the append-only forward record and paper agent "
         "are built from those rows. The API serves both, plus proxied market data, to the React front end, "
         "where every section is badged live or sample. Durations are converted to blocks through one clock "
         "that knows Base's 2-second and 0.2-second regimes.")


# ---- manifest -------------------------------------------------------------

def manifest(s, pop) -> dict:
    sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    dirty = bool(subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True).stdout.strip())
    lab = s.execute(text("select token_address, label from token_label where rule_version = :rv order by 1"),
                    {"rv": rules.RULE_VERSION}).all()
    digest = hashlib.sha256("\n".join(f"{t},{l}" for t, l in lab).encode()).hexdigest()
    p5 = json.loads((BACKEND / "reports" / "phase5_results.json").read_text(encoding="utf8"))
    meta = json.loads((BACKEND / "data" / "models" / "buyer_loss_v1.json").read_text(encoding="utf8"))
    fwd = rv.scoreboard(s)
    pa = rv.paper_agent(s)["policies"]["headline"]
    fv = json.loads((BACKEND / "reports" / "forward_validation.json").read_text(encoding="utf8"))
    return {
        "generated": datetime.now(timezone.utc).isoformat(),
        "git_sha": sha, "working_tree_dirty": dirty,
        "model": {"version": meta["version"], "trained": meta["trained"], "trained_on": meta["trained_on"],
                  "feature_set": meta["feature_set"]},
        "dataset": {"rule_version": rules.RULE_VERSION, "labelled_tokens": len(lab),
                    "labels_sha256": digest, "by_label": dict(Counter(l for _, l in lab)),
                    "alive_labelled_in_population": len(pop)},
        "split": {"temporal_split": d.SPLIT_DATE.isoformat(), "period": [d.PERIOD_START.isoformat(), d.PERIOD_END.isoformat()],
                  "cutoff_minutes": d.CUTOFF_MINUTES,
                  "block_time_switch": {"block": 53_556_128, "utc": "2026-11-05T18:00:01Z"}},
        "seeds": SEEDS.__dict__,
        "headline": {
            "launch_type": {"self_deployed_pulled_eval": "109 of 113", "launchpad_pulled_eval": "0 of 74",
                            "source": "reports/model_card_v2.md"},
            "phase5_rug_rule_checker_eval_pr_auc": p5["rule_checker"]["eval"]["pr_auc"],
            "forward_3nov_preregistered": {k: fv["pre_registered"]["buyer_loss"].get(k) for k in
                                           ("resolved", "losses", "base_rate", "pr_auc", "pr_auc_minus_base_rate_ci",
                                            "brier", "brier_base_rate")},
            "forward_now_valid": {k: fwd["buyer_loss"].get(k) for k in
                                  ("resolved", "losses", "base_rate", "pr_auc", "pr_auc_minus_base_rate_ci",
                                   "brier", "brier_base_rate")},
            "forward_launch_type": fwd["launch_type"],
            "forward_excluded_block_time": fwd.get("block_time_excluded"),
            "paper_agent": {k: pa[k] for k in ("AGENT", "CONTROL", "LAUNCHPAD") if k in pa} |
                           {"agent_minus_control_ci": pa.get("agent_minus_control_ci"),
                            "agent_minus_launchpad_ci": pa.get("agent_minus_launchpad_ci")},
        },
        "figures": NUMBERS,
    }


def write_captions():
    md = ["# Figure captions (generated by scripts/make_figures.py)", ""]
    tex = ["% Generated by backend/scripts/make_figures.py. Do not edit; rerun the script.", ""]
    for i, (name, c) in enumerate(CAPTIONS.items(), 1):
        md += [f"**Figure {i}. {c['title']}.** {c['caption']}", f"`report/figures/generated/{name}.pdf`", ""]
        cap = c["caption"].replace("%", r"\%").replace("&", r"\&").replace("_", r"\_").replace("×", r"$\times$")
        tex += [r"\begin{figure}[htbp]\centering",
                rf"\includegraphics[width=\textwidth]{{figures/generated/{name}.pdf}}",
                rf"\caption{{\textbf{{{c['title']}.}} {cap}}}\label{{fig:{name}}}", r"\end{figure}", ""]
    (OUT / "captions.md").write_text("\n".join(md), encoding="utf8")
    (OUT / "captions.tex").write_text("\n".join(tex), encoding="utf8")


def main() -> int:
    print("figures ->", OUT)
    with session_factory()() as s:
        pop = labelled_population(s)
        fig01_class_balance(pop)
        fig02_label_sensitivity(s)
        fig03_launch_dates(pop)
        sets, names, tr, ytr, ca, yca = t2_sets()
        scores = fig04_pr_curves(names, tr, ytr, ca, yca)
        fig05_reliability(scores, ca, yca, s)
        fig06_decay(sets, names, s)
        fig07_importance(names, tr, ytr, ca, yca)
        fig08_three_way(names, tr, ytr, ca, yca)
        fig09_comovement()
        fig10_cluster_case(s)
        fig11_pipeline()
        write_captions()
        MANIFEST.parent.mkdir(parents=True, exist_ok=True)
        MANIFEST.write_text(json.dumps(manifest(s, pop), indent=1, default=str), encoding="utf8")
    print(f"wrote {len(CAPTIONS)} figures, captions and {MANIFEST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
