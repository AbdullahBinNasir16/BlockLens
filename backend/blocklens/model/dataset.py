"""Assemble the training matrix, and say honestly what each row is.

## The unit of observation is a wallet, grouped by token

There are 44 tokens with both features and a label, and 95 features per
wallet. A token-level model is therefore p > n before it starts: any score
it produced would be a description of 44 points, and the paper's F1 0.93
against 0.81 could not be distinguished from noise at that size.

So rows are wallets (667 of them) and each inherits its token's label. That
is a real question rather than a workaround — "is this wallet trading a
token that will be rugged" is what the product has to answer when someone
pastes an address — but it changes the statistics in one way that must be
honoured: **wallets within a token are not independent**. They see the same
launch, the same liquidity event, the same deployer. A random split would
put siblings on both sides and return an inflated score.

Every split in this module is therefore grouped by token, so a token appears
in exactly one fold. `GroupKFold` is not a detail here; without it the
numbers are meaningless.

## The target

`RUG` against everything else, collapsed at training time exactly as Phase 2
said it should be. The alternative — three-class — splits 44 tokens into
groups too small to learn from, and the question the project asks is binary
anyway.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..store.models import TokenLabel, WalletFeature

TARGET_LABEL = "RUG"
# Labels that are not a statement about the token's fate and must not be
# trained on. Phase 2 excludes NEVER_LAUNCHED from the dataset outright, and
# UNCLEAR means "we could not tell" rather than "nothing happened".
EXCLUDED_LABELS = ("NEVER_LAUNCHED", "UNCLEAR")


@dataclass
class Dataset:
    X: np.ndarray
    y: np.ndarray
    groups: np.ndarray            # token address per row, for grouped CV
    feature_names: list[str]
    tokens: list[str]             # distinct tokens, in order of first appearance
    token_labels: dict[str, str]
    dropped_features: list[str] = field(default_factory=list)

    @property
    def n_rows(self) -> int:
        return int(self.X.shape[0])

    @property
    def n_features(self) -> int:
        return int(self.X.shape[1])

    @property
    def n_tokens(self) -> int:
        return len(self.tokens)

    def summary(self) -> dict:
        pos = int(self.y.sum())
        tok_pos = sum(1 for t in self.tokens
                      if self.token_labels[t] == TARGET_LABEL)
        return {
            "rows_wallets": self.n_rows,
            "features": self.n_features,
            "tokens": self.n_tokens,
            "positive_rows": pos,
            "positive_row_share": round(pos / self.n_rows, 4) if self.n_rows else 0.0,
            "positive_tokens": tok_pos,
            "positive_token_share": round(tok_pos / self.n_tokens, 4)
            if self.n_tokens else 0.0,
            "majority_row_baseline": round(
                max(pos, self.n_rows - pos) / self.n_rows, 4) if self.n_rows else 0.0,
            "dropped_features": self.dropped_features,
        }


def hop_subset(names: list[str], hops: int) -> list[str]:
    """Feature names for an ablation level.

    `hops=0` is the flat model — a wallet's own behaviour only, which is the
    baseline the propagated features have to beat for this project to have a
    contribution at all.
    """
    keep = [n for n in names if n.startswith("base_")]
    for h in range(1, hops + 1):
        keep += [n for n in names if n.startswith(f"h{h}_")]
    return sorted(keep)


def load(session: Session, *, chain: str, rule_version: str,
         feature_set_version: str | None = None,
         drop_features: list[str] | None = None) -> Dataset:
    """Join wallet features to their token's label.

    Rows whose token carries an excluded label are left out rather than
    folded into the negative class: training a model to call UNCLEAR
    "not a rug" would teach it that our own uncertainty is evidence of
    safety, which is the wrong lesson and an easy one to miss.
    """
    labels = dict(session.execute(
        select(TokenLabel.token_address, TokenLabel.label)
        .where(TokenLabel.chain == chain,
               TokenLabel.rule_version == rule_version)).all())

    q = select(WalletFeature.token_address, WalletFeature.wallet_address,
               WalletFeature.features).where(WalletFeature.chain == chain)
    if feature_set_version:
        q = q.where(WalletFeature.feature_set_version == feature_set_version)
    rows = session.execute(q.order_by(WalletFeature.token_address,
                                      WalletFeature.wallet_address)).all()

    usable = [(t, w, f) for t, w, f in rows
              if labels.get(t) and labels[t] not in EXCLUDED_LABELS]
    if not usable:
        raise ValueError("no wallet features join to a usable label")

    # One canonical feature order, from the union of keys seen. A missing
    # key becomes 0.0 rather than dropping the row: a wallet with no
    # neighbours legitimately has no neighbour aggregates.
    names = sorted({k for _, _, f in usable for k in f})
    drop = set(drop_features or [])
    kept = [n for n in names if n not in drop]

    X = np.array([[float(f.get(n, 0.0) or 0.0) for n in kept]
                  for _, _, f in usable], dtype=float)
    y = np.array([1 if labels[t] == TARGET_LABEL else 0 for t, _, _ in usable],
                 dtype=int)
    groups = np.array([t for t, _, _ in usable], dtype=object)

    seen: list[str] = []
    for t, _, _ in usable:
        if t not in seen:
            seen.append(t)

    # Guard against a column that is constant across the whole set: it
    # cannot carry information and some estimators will divide by its zero
    # variance.
    variance = X.var(axis=0)
    constant = [kept[i] for i, v in enumerate(variance) if v == 0.0]
    if constant:
        keep_idx = [i for i, v in enumerate(variance) if v > 0.0]
        X = X[:, keep_idx]
        kept = [kept[i] for i in keep_idx]

    return Dataset(X=X, y=y, groups=groups, feature_names=kept,
                   tokens=seen, token_labels=labels,
                   dropped_features=sorted(drop | set(constant)))
