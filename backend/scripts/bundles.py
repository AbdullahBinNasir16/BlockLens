"""Bundle detection over the research population, and its blind validation
(DECISIONS.md, "Bundle detection, pre-registered", 2026-11-21).

    python -m scripts.bundles detect   # -> reports/bundles.json, labelling sheet + hidden key
    python -m scripts.bundles score    # after the team fills in the sheet -> reports/bundle_validation.json

The labelling sheet (`reports/bundle_labelling.csv`) shows each launch's
token, pool and first-five-minute block range with explorer links, and
**not** the detector's call. The calls are in `reports/bundle_labelling_key.json`,
which labellers must not open. Each row is labelled `bundled`, `not bundled`
or `cannot tell` from a block explorer.
"""
from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from sqlalchemy import text

from blocklens.config import SEEDS
from blocklens.graph import bundles as bd
from blocklens.label.rules import RULE_VERSION
from blocklens.model import token_features as tf
from blocklens.model.rulecheck_x import BUYER_LOSS_AT
from blocklens.sampling.design import cutoff_block
from blocklens.store.db import session_factory

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "bundles.json"
SHEET = ROOT / "reports" / "bundle_labelling.csv"
KEY = ROOT / "reports" / "bundle_labelling_key.json"
VALID = ROOT / "reports" / "bundle_validation.json"
EXTR = ROOT / "data" / "phase6_extraction.json"
PER_GROUP = 100
FLOOR = 120              # was 150; the sample shrank to 134 after the collector deviation (DECISIONS.md)
LABELS = ("bundled", "not bundled", "cannot tell")


def detect() -> None:
    extr = json.loads(EXTR.read_text(encoding="utf8")) if EXTR.exists() else {}
    with session_factory()() as s:
        ctx = tf.Context(s, "base")
        rows = s.execute(text("""
            select s.token_address, s.pool_key, s.created_block, s.launch_ts, l.label
            from token_sample s
            join token_label l on l.token_address = s.token_address and l.chain = s.chain
                               and l.rule_version = :rv
            where s.chain = 'base' and s.alive_at_cutoff and s.excluded_reason is null
        """), {"rv": RULE_VERSION}).all()
        per_launch = {tok: bd.candidate_recipients(s, ctx, token=tok, pool=pool, created_block=cb)
                      for tok, pool, cb, lt, lab in rows}
        collectors = bd.recurring_collectors(per_launch)
        v0 = sum(1 for tok in per_launch if bd.from_recipients(tok, per_launch[tok]).bundled)
        out = []
        for tok, pool, cb, lt, lab in rows:
            r = bd.from_recipients(tok, per_launch[tok], exclude=collectors)
            pe = (extr.get(tok) or {}).get("price_end_vs_cutoff")
            out.append({"token": tok, "pool": pool, "created_block": cb, "launch_ts": lt.isoformat(),
                        "label": lab, "buyer_loss": None if pe is None else int(pe <= BUYER_LOSS_AT),
                        "bundled": r.bundled, "bundle_txs": r.bundle_txs, "max_recipients": r.max_recipients,
                        "buyers": r.buyers, "buyers_via_bundles": r.buyers_via_bundles})
    n = len(out)
    b = [r for r in out if r["bundled"]]
    nb = [r for r in out if not r["bundled"]]

    def rate(rs, f):
        vals = [f(r) for r in rs if f(r) is not None]
        return {"n": len(vals), "rate": round(float(np.mean(vals)), 4) if vals else None}

    summary = {
        "generated": datetime.now(timezone.utc).isoformat(),
        "definition": {"min_recipients": bd.MIN_RECIPIENTS, "window": "launch to launch + 5 minutes",
                       "population": "labelled research launches alive at minute 5"},
        "launches": n, "bundled": len(b), "prevalence": round(len(b) / n, 4) if n else None,
        "deviation": {"recorded": "2026-11-21, before any label",
                      "rule": f"addresses reached in multi-recipient swap txs of >= {bd.RECURRENCE_INFRA} launches are collectors, not wallets",
                      "collectors_excluded": sorted(collectors),
                      "bundled_under_original_definition": v0},
        "max_recipients_distribution": dict(Counter(min(r["max_recipients"], 20) for r in out)),
        "descriptive_not_causal": {
            "RUG_rate": {"bundled": rate(b, lambda r: int(r["label"] == "RUG")),
                         "not_bundled": rate(nb, lambda r: int(r["label"] == "RUG"))},
            "buyer_loss_rate": {"bundled": rate(b, lambda r: r["buyer_loss"]),
                                "not_bundled": rate(nb, lambda r: r["buyer_loss"])},
        },
        "launches_detail": out,
    }
    OUT.write_text(json.dumps(summary, indent=1), encoding="utf8")

    # the blind labelling sample: stratified by the detector's call
    rng = np.random.default_rng(SEEDS.bundles)
    pick = []
    for group in (b, nb):
        k = min(PER_GROUP, len(group))
        pick += [group[i] for i in rng.choice(len(group), k, replace=False)]
    order = rng.permutation(len(pick))
    pick = [pick[i] for i in order]
    with SHEET.open("w", newline="", encoding="utf8") as f:
        w = csv.writer(f)
        w.writerow(["id", "token", "pool", "first_block", "last_block_minute5", "token_link", "pool_link",
                    "label (bundled / not bundled / cannot tell)", "labeller", "notes"])
        for i, r in enumerate(pick, 1):
            w.writerow([i, r["token"], r["pool"], r["created_block"], cutoff_block(r["created_block"]),
                        f"https://basescan.org/token/{r['token']}",
                        f"https://basescan.org/address/{r['pool']}" if len(r["pool"]) == 42
                        else f"https://app.uniswap.org/explore/pools/base/{r['pool']}", "", "", ""])
    KEY.write_text(json.dumps({
        "do_not_open_while_labelling": True,
        "strata": {"bundled": len(b), "not_bundled": len(nb)},
        "sampled": {"bundled": min(PER_GROUP, len(b)), "not_bundled": min(PER_GROUP, len(nb))},
        "calls": {str(i): r["bundled"] for i, r in enumerate(pick, 1)},
    }, indent=1), encoding="utf8")
    print(f"{n} launches; {len(b)} bundled ({len(b) / n:.1%}); {v0} under the original definition; "
          f"{len(collectors)} collectors excluded")
    print("descriptive:", json.dumps(summary["descriptive_not_causal"]))
    print(f"labelling sheet: {SHEET} ({len(pick)} rows); key: {KEY}")


def score() -> None:
    key = json.loads(KEY.read_text(encoding="utf8"))
    calls = {int(k): v for k, v in key["calls"].items()}
    with SHEET.open(encoding="utf8") as f:
        rows = list(csv.DictReader(f))
    lab_col = [c for c in rows[0] if c.startswith("label")][0]
    labelled = [(int(r["id"]), r[lab_col].strip().lower()) for r in rows if r[lab_col].strip()]
    bad = [lab for _, lab in labelled if lab not in LABELS]
    if bad:
        sys.exit(f"unknown labels: {sorted(set(bad))}; use one of {LABELS}")
    out = {"labelled": len(labelled), "floor": FLOOR, "cannot_tell": sum(l == "cannot tell" for _, l in labelled)}
    if len(labelled) < FLOOR:
        out["reportable"] = False
        VALID.write_text(json.dumps(out, indent=1), encoding="utf8")
        print(f"{len(labelled)} labelled; the floor is {FLOOR}: no precision or recall yet")
        return
    # inverse-probability weights: each stratum's sample stands for its stratum
    st, sm = key["strata"], key["sampled"]
    w = {True: st["bundled"] / sm["bundled"], False: st["not_bundled"] / sm["not_bundled"]}
    clear = [(i, l == "bundled") for i, l in labelled if l != "cannot tell"]
    tp = sum(w[calls[i]] for i, y in clear if calls[i] and y)
    fp = sum(w[calls[i]] for i, y in clear if calls[i] and not y)
    fn = sum(w[calls[i]] for i, y in clear if not calls[i] and y)
    out.update(reportable=True, precision=round(tp / (tp + fp), 4) if tp + fp else None,
               recall_weighted=round(tp / (tp + fn), 4) if tp + fn else None,
               counts={"bundled_called_and_labelled_bundled": sum(1 for i, y in clear if calls[i] and y),
                       "called_bundled_labelled_not": sum(1 for i, y in clear if calls[i] and not y),
                       "called_not_labelled_bundled": sum(1 for i, y in clear if not calls[i] and y),
                       "called_not_labelled_not": sum(1 for i, y in clear if not calls[i] and not y)})
    VALID.write_text(json.dumps(out, indent=1), encoding="utf8")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    {"detect": detect, "score": score}[sys.argv[1]]()
