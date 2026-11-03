"""Phase 11: shadow scores over the frozen v1 record (DECISIONS.md, Phase 11).

Both scores are functions of two values the live log already holds at
minute 5, v1's `risk` and the `launch_type`, so they can be recomputed
exactly for any logged launch and no live code changes.

* A, calibrated buyer loss: Platt scaling of v1, same label.
* B, pull-aware buyer outcome: `buyer_loss OR pulled by hour 6`, from
  launch type, logit(risk) and their product.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score

CLIP = 1e-4
SEED = 20261104
BOOT = 1000
FLOOR = {"resolved": 2000, "losses": 50}


@dataclass
class Row:
    risk: float
    self_deployed: bool
    buyer_loss: bool
    pulled_6h: bool

    @property
    def y_b(self) -> bool:
        return self.buyer_loss or self.pulled_6h


def logit(p: np.ndarray) -> np.ndarray:
    p = np.clip(p, CLIP, 1 - CLIP)
    return np.log(p / (1 - p))


def _xa(rows: list[Row]) -> np.ndarray:
    return logit(np.array([r.risk for r in rows]))[:, None]


def _xb(rows: list[Row]) -> np.ndarray:
    z = logit(np.array([r.risk for r in rows]))
    s = np.array([float(r.self_deployed) for r in rows])
    return np.column_stack([s, z, s * z])


def _fit(x: np.ndarray, y: np.ndarray) -> dict:
    # Unpenalised: a handful of parameters on thousands of rows.
    m = LogisticRegression(C=np.inf, solver="lbfgs", max_iter=1000).fit(x, y)
    return {"coef": [float(c) for c in m.coef_[0]], "intercept": float(m.intercept_[0])}


def _apply(p: dict, x: np.ndarray) -> np.ndarray:
    return 1 / (1 + np.exp(-(x @ np.array(p["coef"]) + p["intercept"])))


def fit(rows: list[Row]) -> dict:
    ya = np.array([r.buyer_loss for r in rows], dtype=int)
    yb = np.array([r.y_b for r in rows], dtype=int)
    return {"A": _fit(_xa(rows), ya), "B": _fit(_xb(rows), yb),
            "fit_rows": len(rows), "fit_base_rate_A": float(ya.mean()),
            "fit_base_rate_B": float(yb.mean())}


def score_a(params: dict, rows: list[Row]) -> np.ndarray:
    return _apply(params["A"], _xa(rows))


def score_b(params: dict, rows: list[Row]) -> np.ndarray:
    return _apply(params["B"], _xb(rows))


def reliability(p: np.ndarray, y: np.ndarray) -> list[dict]:
    out = []
    for lo in np.arange(0, 1, 0.1):
        m = (p >= lo) & ((p < lo + 0.1) if lo < 0.9 else (p <= 1))
        if m.any():
            out.append({"bin": f"{lo:.1f}-{lo + 0.1:.1f}", "n": int(m.sum()),
                        "mean_predicted": round(float(p[m].mean()), 4),
                        "observed": round(float(y[m].mean()), 4)})
    return out


def _ci(d: list[float]) -> list[float]:
    return [round(float(np.percentile(d, 2.5)), 4), round(float(np.percentile(d, 97.5)), 4)]


def evaluate(params: dict, rows: list[Row]) -> dict:
    """The Phase 11 criteria on an evaluation set, exactly as pre-registered."""
    ya = np.array([r.buyer_loss for r in rows], dtype=int)
    yb = np.array([r.y_b for r in rows], dtype=int)
    out: dict = {"resolved": len(rows), "losses": int(ya.sum()), "y_b_positives": int(yb.sum()),
                 "floor": FLOOR,
                 "reportable": len(rows) >= FLOOR["resolved"] and int(ya.sum()) >= FLOOR["losses"]}
    if not rows:
        return out
    pa, pb = score_a(params, rows), score_b(params, rows)
    ca = np.full(len(rows), params["fit_base_rate_A"])
    cb = np.full(len(rows), params["fit_base_rate_B"])
    kind = np.array([float(r.self_deployed) for r in rows])
    v1 = np.array([r.risk for r in rows])
    rng = np.random.default_rng(SEED)
    da, db_pr, db_brier = [], [], []
    for _ in range(BOOT):
        i = rng.integers(0, len(rows), len(rows))
        da.append(np.mean((pa[i] - ya[i]) ** 2) - np.mean((ca[i] - ya[i]) ** 2))
        db_brier.append(np.mean((pb[i] - yb[i]) ** 2) - np.mean((cb[i] - yb[i]) ** 2))
        if 0 < yb[i].sum() < len(i):
            db_pr.append(average_precision_score(yb[i], pb[i]) - average_precision_score(yb[i], kind[i]))
    out["A"] = {"brier": round(float(np.mean((pa - ya) ** 2)), 4),
                "brier_constant": round(float(np.mean((ca - ya) ** 2)), 4),
                "brier_v1": round(float(np.mean((v1 - ya) ** 2)), 4),
                "brier_minus_constant_ci": _ci(da),
                "mean_predicted": round(float(pa.mean()), 4),
                "observed": round(float(ya.mean()), 4),
                "reliability": reliability(pa, ya)}
    out["A"]["pass"] = out["A"]["brier_minus_constant_ci"][1] < 0
    both = 0 < yb.sum() < len(yb)
    out["B"] = {"pr_auc": round(float(average_precision_score(yb, pb)), 4) if both else None,
                "pr_auc_launch_type": round(float(average_precision_score(yb, kind)), 4) if both else None,
                "pr_auc_minus_launch_type_ci": _ci(db_pr) if db_pr else None,
                "brier": round(float(np.mean((pb - yb) ** 2)), 4),
                "brier_constant": round(float(np.mean((cb - yb) ** 2)), 4),
                "brier_minus_constant_ci": _ci(db_brier),
                "reliability": reliability(pb, yb)}
    out["B"]["pass"] = bool(db_pr) and out["B"]["pr_auc_minus_launch_type_ci"][0] > 0 \
        and out["B"]["brier"] < out["B"]["brier_constant"]
    return out
