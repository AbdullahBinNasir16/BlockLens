"""Train the shipped buyer-loss model and write it with its validation record.

    python -m scripts.train_buyer_loss     # -> data/models/buyer_loss_v1.joblib (+ .json)

The artefact is fitted on every labelled non-RUG token alive at minute 5
(all strata, all months), because a shipped model should use all the
evidence. Its *validation* numbers are not computed on that fit: they are
copied from the held-out runs in `reports/model_card_phase6.md`, and the
API shows them beside every score.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np

import scripts.phase6_model as m6
from blocklens.model import token_features as tf
from scripts.phase5_model import boosting, matrix

OUT = Path("data/models/buyer_loss_v1.joblib")
VERSION = "buyer-loss-v1"


def main() -> int:
    sets = m6.load()
    rows = [r for side in ("TRAIN", "CAL", "EVAL") for r in sets[side] if r["t2"] is not None]
    names = sorted({k for r in rows for k in r if k.startswith(("t_", "g_", "r_"))})
    y = np.array([r["t2"] for r in rows])
    model = boosting().fit(matrix(rows, names), y)
    res = json.loads(Path("reports/phase6_results.json").read_text(encoding="utf8"))
    meta = {
        "version": VERSION, "feature_set": tf.FEATURE_SET_VERSION, "features": names,
        "trained": datetime.now(timezone.utc).isoformat(),
        "trained_on": {"tokens": len(rows), "losses": int(y.sum()),
                       "launches": [min(r["launch"] for r in rows).date().isoformat(),
                                    max(r["launch"] for r in rows).date().isoformat()]},
        "target": "a buy at the price 5 minutes after launch is worth <= 50% six hours after launch",
        "applies_to": "Base Uniswap V3/V4 pools, scored once, at launch + 5 minutes, "
                      "only if traded by then; not for RUG risk (see launch type)",
        "validation": {
            "in_period": {"set": "random cohort Jan 20 - Apr 19 2026", "tokens": 179,
                          "pr_auc": res["T2"]["models"]["boosting: all"]["pr_auc"],
                          "base_rate": res["T2"]["prevalence_cal"],
                          "rule_checker_pr_auc": res["T2"]["models"]["early-concentration checker"]["pr_auc"]},
            "out_of_time": {"set": "trained before Mar 1, tested Mar 1 - Apr 17 2026", "tokens": 57,
                            "pr_auc": 0.758, "rule_checker_pr_auc": 0.331},
            "regime_check": {"set": "May - Jul 2026", "tokens": 78, "losses": 3,
                             "flagged_at_0_5": 5, "losses_caught": 3},
        },
        "launch_type_signal": {
            "self_deployed_rug_rate_eval": "109 of 113",
            "launchpad_rug_rate_eval": "0 of 74",
            "source": "reports/model_card_v2.md",
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": model, "meta": meta}, OUT)
    OUT.with_suffix(".json").write_text(json.dumps(meta, indent=1), encoding="utf8")
    print(f"trained on {len(rows)} tokens ({int(y.sum())} losses), {len(names)} features -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
