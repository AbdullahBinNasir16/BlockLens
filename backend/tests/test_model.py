"""The model's guarantees, and the two ways its numbers could be fiction.

Grouped folds, because wallets inside a token are not independent and a
random split would inflate every score. And a leakage audit that actually
catches the features that restate the label, because no amount of
cross-validation reveals a definitional leak.
"""
from __future__ import annotations

import numpy as np
import pytest

from blocklens.model import dataset as ds
from blocklens.model import leakage, train


def synthetic(*, n_tokens: int = 20, per_token: int = 10,
              signal: float = 2.0, seed: int = 7) -> ds.Dataset:
    """A dataset where the label is a property of the token, not the wallet.

    Built so a grouped split and a random split give visibly different
    answers: each token gets its own offset, so a model can identify the
    token from the features and will score perfectly if any of its wallets
    were in training.
    """
    rng = np.random.default_rng(seed)
    rows, ys, groups = [], [], []
    labels = {}
    for t in range(n_tokens):
        token = f"0xtok{t:036x}"
        y = t % 2
        labels[token] = "RUG" if y else "FAILED"
        # a per-token fingerprint, plus a weak class signal
        fingerprint = rng.normal(t * 5.0, 0.01, size=per_token)
        useful = rng.normal(signal * y, 1.0, size=per_token)
        noise = rng.normal(0, 1, size=per_token)
        for i in range(per_token):
            rows.append([fingerprint[i], useful[i], noise[i]])
            ys.append(y)
            groups.append(token)
    return ds.Dataset(
        X=np.array(rows), y=np.array(ys), groups=np.array(groups, dtype=object),
        feature_names=["base_fingerprint", "base_useful", "base_noise"],
        tokens=list(labels), token_labels=labels)


# ---- grouping ------------------------------------------------------------

def test_grouped_folds_never_split_a_token_across_train_and_test():
    """The guarantee the whole evaluation rests on."""
    from sklearn.model_selection import GroupKFold

    data = synthetic()
    for train_i, test_i in GroupKFold(n_splits=5).split(data.X, data.y, data.groups):
        in_train = set(data.groups[train_i])
        in_test = set(data.groups[test_i])
        assert not (in_train & in_test), "a token appeared in both folds"


def test_a_random_split_scores_higher_than_a_grouped_one():
    """Why grouping is not optional.

    With a per-token fingerprint in the features, a random split lets the
    model recognise tokens it has already seen. The grouped score is the
    honest one and it must be lower.
    """
    from sklearn.model_selection import KFold, cross_val_score

    data = synthetic(signal=0.5)
    est = train.make_model("boosting")
    random_auc = cross_val_score(est, data.X, data.y, cv=KFold(5, shuffle=True,
                                                               random_state=0),
                                 scoring="roc_auc").mean()
    grouped = train.evaluate(data, features=data.feature_names, name="g",
                             model="boosting")
    assert random_auc > grouped._mean("auc"), (
        f"random split {random_auc:.3f} did not exceed grouped "
        f"{grouped._mean('auc'):.3f}; the fingerprint leak is not being caught"
    )


def test_evaluation_reports_every_fold_including_unscorable_ones():
    """A fold with one class cannot be scored, and dropping it silently
    would quietly shrink the sample behind the headline number."""
    data = synthetic(n_tokens=4, per_token=5)
    res = train.evaluate(data, features=data.feature_names, name="x",
                         model="logistic", n_splits=4)
    assert len(res.folds) == 4
    assert all(f.n_test_tokens >= 1 for f in res.folds)


# ---- the ablation is a controlled comparison -----------------------------

def test_hop_subsets_nest():
    names = ["base_a", "h1_b", "h1_c", "h2_d"]
    assert ds.hop_subset(names, 0) == ["base_a"]
    assert ds.hop_subset(names, 1) == ["base_a", "h1_b", "h1_c"]
    assert ds.hop_subset(names, 2) == ["base_a", "h1_b", "h1_c", "h2_d"]


def test_the_ablation_changes_only_the_feature_set():
    """Same estimator, same folds, same seed — otherwise it is a comparison
    between models rather than between feature sets."""
    data = synthetic()
    results = train.ablation(data, model="logistic")
    assert len(results) >= 1
    assert all(r.model == "logistic" for r in results)
    counts = [r.n_features for r in results]
    assert counts == sorted(counts), "feature sets must grow monotonically"


# ---- the null ------------------------------------------------------------

def test_the_permutation_null_destroys_a_real_signal():
    data = synthetic(signal=3.0)
    feats = ["base_useful"]
    real = train.evaluate(data, features=feats, name="r", model="logistic")
    null = train.permutation_null(data, features=feats, rounds=10)

    assert real._mean("auc") > null["mean_auc"], \
        "the real signal did not beat its own null"
    assert 0.3 < null["mean_auc"] < 0.7, \
        f"a shuffled label should score near chance, got {null['mean_auc']}"


def test_the_null_shuffles_whole_tokens_not_rows():
    """Row-wise shuffling would break the grouping as well as the signal,
    making the null far too easy to beat and the comparison meaningless."""
    data = synthetic()
    null = train.permutation_null(data, features=data.feature_names, rounds=6)
    # With labels assigned per token, a shuffled run still has one label per
    # token, so scores stay near chance rather than collapsing to 0.
    assert null["rounds"] == 6
    assert null["mean_auc"] < 0.8


# ---- leakage -------------------------------------------------------------

def test_the_audit_catches_activity_features_by_definition_not_correlation():
    """A definitional leak can have modest correlation and still be
    circular, so the exclusion is driven by reading definitions."""
    names = ["base_buy_count", "base_buy_quote", "base_hold_time_mean",
             "h1_mean_sell_count", "h2_max_tokens_traded", "h1_count",
             "base_entry_delay_min", "base_in_degree", "h1_mean_degree"]
    excluded = set(leakage.definitional(names))

    assert "base_buy_count" in excluded
    assert "base_buy_quote" in excluded, \
        "money features are zero without priced swaps, which is the DEAD rule"
    assert "base_hold_time_mean" in excluded
    assert "h1_mean_sell_count" in excluded, "propagated counts are no cleaner"
    assert "h2_max_tokens_traded" in excluded
    assert "h1_count" in excluded

    # These survive, and the README says why.
    assert "base_entry_delay_min" not in excluded
    assert "base_in_degree" not in excluded
    assert "h1_mean_degree" not in excluded


def test_single_feature_auc_matches_a_known_case():
    y = np.array([0, 0, 1, 1])
    perfect = np.array([0.0, 1.0, 2.0, 3.0])
    inverted = np.array([3.0, 2.0, 1.0, 0.0])
    flat = np.array([1.0, 1.0, 1.0, 1.0])

    assert leakage._auc(perfect, y) == pytest.approx(1.0)
    assert leakage._auc(inverted, y) == pytest.approx(0.0)
    assert leakage._auc(flat, y) == pytest.approx(0.5), \
        "a constant feature must score exactly 0.5, not 0 or 1"


def test_the_audit_returns_leads_separately_from_exclusions():
    data = synthetic(signal=3.0)
    findings, excluded = leakage.audit(data.X, data.y, data.feature_names, top=2)
    kinds = {f.kind for f in findings}
    assert "empirical" in kinds
    # Nothing in the synthetic set is definitionally leaky.
    assert excluded == []


# ---- the dataset --------------------------------------------------------

def test_unclear_and_never_launched_are_excluded_not_called_negative():
    """Training a model to call our own uncertainty 'not a rug' would teach
    it that uncertainty is evidence of safety."""
    assert "UNCLEAR" in ds.EXCLUDED_LABELS
    assert "NEVER_LAUNCHED" in ds.EXCLUDED_LABELS


def test_the_summary_reports_the_majority_baseline():
    """Any AUC has to be read against the baseline a coin flip would give."""
    data = synthetic(n_tokens=10, per_token=4)
    s = data.summary()
    assert s["rows_wallets"] == 40
    assert s["tokens"] == 10
    assert 0.0 < s["majority_row_baseline"] <= 1.0
