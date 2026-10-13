"""Fit, evaluate honestly, and test the project's central claim.

## What is being claimed, and how it could be wrong

The claim this whole project rests on is that **propagated neighbourhood
features beat flat per-wallet features**. The cited paper reports F1 0.93
against 0.81. If that gap does not appear here, Phase 3 was expensive
decoration and Phase 4 should say so.

So the headline result is not a score, it is an **ablation**: the same
estimator, the same folds, the same seed, over three feature sets — a
wallet's own behaviour, plus one hop, plus two hops. Anything else is a
comparison between models rather than between feature sets.

## Why every number here is conservative

Three decisions, all of which lower the reported score and all of which are
necessary for it to mean anything:

1. **Grouped folds.** A token appears in exactly one fold. Wallets in a
   token see the same launch and the same deployer; a random split puts
   siblings on both sides and inflates everything.
2. **Definitional leakage excluded.** Activity-count features are dropped
   because Phase 2's `DEAD` criterion is computed from activity. Results are
   reported both ways, because dropping features always lowers a score and
   publishing only the lower one is as selective as publishing only the
   higher.
3. **A permutation null.** Labels are shuffled *at the token level* and the
   whole pipeline re-run. With 44 tokens, a cross-validated AUC of 0.8 can
   arise from nothing; the null distribution says how often it does.

## Why logistic regression is the primary model

Regularised logistic regression, with gradient boosting reported beside it.
At 667 rows and tens of features the limit is the data, not the estimator,
and a linear model has two properties that matter more than a point of AUC:
its coefficients are readable, and it cannot manufacture the interaction
effects that a boosted tree will happily invent from 44 tokens.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from .dataset import Dataset, hop_subset

SEED = 20261013
N_SPLITS = 5


def make_model(kind: str = "logistic"):
    """The estimators, both with class weighting.

    At the wallet level the positive class is most of the data, and an
    unweighted fit would learn to say RUG and be right most of the time.
    """
    if kind == "logistic":
        return Pipeline([
            ("scale", StandardScaler()),
            ("clf", LogisticRegression(
                max_iter=5000, class_weight="balanced",
                # Strong regularisation on purpose: tens of features over 44
                # independent groups will otherwise fit the groups.
                C=0.1, random_state=SEED)),
        ])
    if kind == "boosting":
        return HistGradientBoostingClassifier(
            max_depth=3, max_iter=200, learning_rate=0.05,
            class_weight="balanced", random_state=SEED)
    raise ValueError(f"unknown model: {kind}")


@dataclass
class FoldScore:
    auc: float
    ap: float
    n_test_rows: int
    n_test_tokens: int
    positives_in_test: int


@dataclass
class Result:
    name: str
    model: str
    n_features: int
    folds: list[FoldScore] = field(default_factory=list)

    def _mean(self, attr: str) -> float:
        vals = [getattr(f, attr) for f in self.folds
                if not np.isnan(getattr(f, attr))]
        return float(np.mean(vals)) if vals else float("nan")

    def _std(self, attr: str) -> float:
        vals = [getattr(f, attr) for f in self.folds
                if not np.isnan(getattr(f, attr))]
        return float(np.std(vals)) if len(vals) > 1 else 0.0

    def as_dict(self) -> dict:
        return {
            "feature_set": self.name, "model": self.model,
            "n_features": self.n_features,
            "auc_mean": round(self._mean("auc"), 4),
            "auc_std": round(self._std("auc"), 4),
            "ap_mean": round(self._mean("ap"), 4),
            "ap_std": round(self._std("ap"), 4),
            "folds": len(self.folds),
            "fold_aucs": [round(f.auc, 4) for f in self.folds],
        }


def evaluate(data: Dataset, *, features: list[str], name: str,
             model: str = "logistic", n_splits: int = N_SPLITS) -> Result:
    """Grouped cross-validation over one feature set."""
    idx = [data.feature_names.index(f) for f in features
           if f in data.feature_names]
    X = data.X[:, idx]
    y, groups = data.y, data.groups

    n_groups = len(set(groups))
    splits = min(n_splits, n_groups)
    res = Result(name=name, model=model, n_features=len(idx))
    if splits < 2:
        return res

    for train_i, test_i in GroupKFold(n_splits=splits).split(X, y, groups):
        y_tr, y_te = y[train_i], y[test_i]
        # A fold with one class in it cannot be scored; recorded as NaN and
        # averaged over rather than quietly dropped.
        if len(set(y_tr)) < 2 or len(set(y_te)) < 2:
            res.folds.append(FoldScore(
                auc=float("nan"), ap=float("nan"),
                n_test_rows=len(test_i),
                n_test_tokens=len(set(groups[test_i])),
                positives_in_test=int(y_te.sum())))
            continue
        est = make_model(model)
        est.fit(X[train_i], y_tr)
        p = est.predict_proba(X[test_i])[:, 1]
        res.folds.append(FoldScore(
            auc=float(roc_auc_score(y_te, p)),
            ap=float(average_precision_score(y_te, p)),
            n_test_rows=len(test_i),
            n_test_tokens=len(set(groups[test_i])),
            positives_in_test=int(y_te.sum())))
    return res


def ablation(data: Dataset, *, model: str = "logistic") -> list[Result]:
    """The project's central claim, as a controlled comparison.

    Same estimator, same folds, same seed; only the feature set moves.
    """
    out = []
    for hops, label in ((0, "flat (own behaviour only)"),
                        (1, "+ 1 hop"),
                        (2, "+ 2 hops")):
        feats = hop_subset(data.feature_names, hops)
        if not feats:
            continue
        out.append(evaluate(data, features=feats,
                            name=f"{label} [{len(feats)}f]", model=model))
    return out


def permutation_null(data: Dataset, *, features: list[str], model: str = "logistic",
                     rounds: int = 25, seed: int = SEED) -> dict:
    """What this pipeline scores when the labels mean nothing.

    Shuffled **at the token level**, preserving each token's wallet count and
    the class balance, so the null keeps every structure in the data except
    the association being measured. Shuffling row-wise would break the
    grouping too and make the null far too easy to beat.
    """
    rng = np.random.default_rng(seed)
    tokens = list(data.tokens)
    truth = {t: data.token_labels[t] for t in tokens}
    labels = np.array([1 if truth[t] == "RUG" else 0 for t in tokens])

    scores = []
    for _ in range(rounds):
        shuffled = labels.copy()
        rng.shuffle(shuffled)
        mapping = dict(zip(tokens, shuffled))
        fake = Dataset(
            X=data.X, y=np.array([mapping[t] for t in data.groups], dtype=int),
            groups=data.groups, feature_names=data.feature_names,
            tokens=tokens,
            token_labels={t: ("RUG" if mapping[t] else "FAILED") for t in tokens})
        r = evaluate(fake, features=features, name="null", model=model)
        m = r._mean("auc")
        if not np.isnan(m):
            scores.append(m)

    if not scores:
        return {"rounds": 0}
    arr = np.array(scores)
    return {
        "rounds": len(scores),
        "mean_auc": round(float(arr.mean()), 4),
        "std_auc": round(float(arr.std()), 4),
        "p95_auc": round(float(np.percentile(arr, 95)), 4),
        "max_auc": round(float(arr.max()), 4),
    }


def coefficients(data: Dataset, *, features: list[str], top: int = 15) -> list[dict]:
    """What the fitted model actually leans on, over the whole set.

    Fitted once on everything, so this is a description of the data rather
    than an out-of-sample claim — which is the only honest reading of a
    coefficient table anyway.
    """
    idx = [data.feature_names.index(f) for f in features
           if f in data.feature_names]
    est = make_model("logistic")
    est.fit(data.X[:, idx], data.y)
    coefs = est.named_steps["clf"].coef_[0]
    names = [data.feature_names[i] for i in idx]
    order = np.argsort(np.abs(coefs))[::-1][:top]
    return [{"feature": names[i], "coefficient": round(float(coefs[i]), 4)}
            for i in order]
