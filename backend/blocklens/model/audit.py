"""Phase 5, Part A: is the Phase 4 result prediction, or something else?

Three questions, each answered from the stored rows rather than argued:

1. **Censoring.** Features are frozen at launch + 24h. A token that rugged at
   minute 15 has fifteen minutes of activity inside that window, so every
   wallet's entry delay is under fifteen minutes *because the token was
   dead*, not because early entry predicts death. The write gate cannot see
   this: every event really is before the cutoff. The test is to find when
   each token actually died, and re-run the model on the rugs that were
   still alive at the end of their own window.

2. **Cross-token leakage through the wallet.** `load_wallet_behaviour`
   aggregates a wallet's trades over *every* token it touched up to the
   cutoff. A wallet that traded tokens A and B carries its behaviour on B
   into A's feature row. Grouping folds by token does not stop that: if B is
   in the test fold and A in training, the model has seen B through W.

3. **The split.** Phase 4's `GroupKFold` is grouped but not temporal. A
   model scored on launches that precede its training launches is being
   asked an easier question than the product asks.

The rug time here is measured from transfers, not taken from the label. The
label's `largest_drop_ts` is the first *sample* after the drop, and Phase 2
samples at roughly six-hour spacing near launch, so it can only say "before
hour 6". The transfers say the minute.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta

import numpy as np
from sklearn.metrics import average_precision_score, roc_auc_score
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..ingest.evm import UNISWAP_V4_POOL_MANAGER as POOL_MANAGER
from . import train
from .dataset import Dataset

# A token is "rugged" at the first moment its pool holdings of the token fall
# to this fraction of their running peak. Matches Phase 2's 90% drop.
RUG_RESERVE_FRACTION = 0.10
WINDOW_HOURS = 24
# Minutes at which to count survivors, for choosing a shorter window.
SURVIVAL_MARKS_MIN = (1, 2, 5, 10, 15, 30, 60, 180, 360, 1440)


@dataclass
class TokenTimeline:
    token: str
    label: str
    launch_ts: datetime
    dex: str
    creator: str | None
    n_wallets: int                     # rows in wallet_feature
    n_trades: int                      # pool-side transfers in the window
    first_trade_min: float | None
    last_trade_min: float | None
    rug_min: float | None              # from transfers, inside the window
    label_drop_h: float | None         # from Phase 2's sampled series
    trade_minutes: list[float] = field(default_factory=list)

    @property
    def rugged_in_window(self) -> bool:
        return self.rug_min is not None

    def trading_after(self, minute: float) -> bool:
        return any(m > minute for m in self.trade_minutes)


def timelines(session: Session, *, chain: str, rule_version: str) -> list[TokenTimeline]:
    """One timeline per labelled RUG/FAILED token, from its own window."""
    toks = session.execute(text("""
        select l.token_address, l.label, l.launch_ts,
               extract(epoch from (l.largest_drop_ts - l.launch_ts)) / 3600.0,
               t.creator_address,
               (select count(*) from wallet_feature w
                 where w.chain = l.chain and w.token_address = l.token_address)
        from token_label l
        left join token t on t.address = l.token_address and t.chain = l.chain
        where l.chain = :chain and l.rule_version = :rv
          and l.label in ('RUG', 'FAILED')
        order by l.launch_ts
    """), {"chain": chain, "rv": rule_version}).all()

    out: list[TokenTimeline] = []
    for token, label, launch, drop_h, creator, n_wallets in toks:
        pools = session.execute(text("""
            select case when dex = 'uniswap-v4' then :pm else address end, dex
            from pair where chain = :chain and token_address = :t
        """), {"chain": chain, "t": token, "pm": POOL_MANAGER}).all()
        holders = {p[0] for p in pools}
        dex = ",".join(sorted({p[1] or "?" for p in pools}))

        rows = session.execute(text("""
            select block_ts, from_address, to_address, value_normalised
            from transfer
            where chain = :chain and token_address = :t
              and block_ts >= :s and block_ts <= :e
            order by block_ts
        """), {"chain": chain, "t": token, "s": launch,
               "e": launch + timedelta(hours=WINDOW_HOURS)}).all()

        reserve = peak = 0.0
        rug_min = None
        minutes: list[float] = []
        for ts, fr, to, v in rows:
            amount = float(v or 0.0)
            into, out_of = to in holders, fr in holders
            if into:
                reserve += amount
            if out_of:
                reserve -= amount
            if into != out_of:
                minutes.append((ts - launch).total_seconds() / 60)
            peak = max(peak, reserve)
            if rug_min is None and peak > 0 and reserve <= RUG_RESERVE_FRACTION * peak:
                rug_min = (ts - launch).total_seconds() / 60

        out.append(TokenTimeline(
            token=token, label=label, launch_ts=launch, dex=dex, creator=creator,
            n_wallets=int(n_wallets), n_trades=len(minutes),
            first_trade_min=minutes[0] if minutes else None,
            last_trade_min=minutes[-1] if minutes else None,
            rug_min=rug_min,
            label_drop_h=float(drop_h) if drop_h is not None else None,
            trade_minutes=minutes))
    return out


def survival_table(tl: list[TokenTimeline]) -> list[dict]:
    """How many tokens of each class are still trading at minute N.

    "Still trading" means a pool-side transfer after minute N. A RUG token
    must also not yet have hit the reserve floor. This is the table that
    decides a shorter window: N has to be early enough to keep most rugs,
    and late enough that there is something to measure.
    """
    out = []
    for n in SURVIVAL_MARKS_MIN:
        row = {"minute": n}
        for label in ("RUG", "FAILED"):
            group = [t for t in tl if t.label == label]
            alive = [t for t in group
                     if t.trading_after(n) and (t.rug_min is None or t.rug_min > n)]
            row[label] = len(alive)
            row[f"{label}_with_features"] = sum(1 for t in alive if t.n_wallets)
            row[f"{label}_total"] = len(group)
        out.append(row)
    return out


# ---- the model, re-run under different conditions -----------------------

def subset(data: Dataset, tokens: set[str]) -> Dataset:
    mask = np.array([g in tokens for g in data.groups])
    kept = [t for t in data.tokens if t in tokens]
    return Dataset(X=data.X[mask], y=data.y[mask], groups=data.groups[mask],
                   feature_names=data.feature_names, tokens=kept,
                   token_labels=data.token_labels,
                   dropped_features=data.dropped_features)


def regroup(data: Dataset, mapping: dict[str, str]) -> Dataset:
    """Same rows, coarser groups. GroupKFold then keeps a whole group in one
    fold, which is how a leak through shared wallets is closed."""
    groups = np.array([mapping.get(g, g) for g in data.groups], dtype=object)
    return Dataset(X=data.X, y=data.y, groups=groups,
                   feature_names=data.feature_names, tokens=data.tokens,
                   token_labels=data.token_labels,
                   dropped_features=data.dropped_features)


def shared_wallet_components(session: Session, *, chain: str,
                             tokens: list[str]) -> dict[str, str]:
    """Tokens joined if any wallet has a feature row on both.

    Connected components of the token-wallet bipartite graph, returned as
    token -> component id. Tokens in one component cannot be separated by
    any split without a wallet's cross-token behaviour crossing the split.
    """
    rows = session.execute(text("""
        select wallet_address, token_address from wallet_feature
        where chain = :chain
    """), {"chain": chain}).all()
    parent = {t: t for t in tokens}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    by_wallet: dict[str, list[str]] = defaultdict(list)
    for w, t in rows:
        if t in parent:
            by_wallet[w].append(t)
    for ts in by_wallet.values():
        for t in ts[1:]:
            a, b = find(ts[0]), find(t)
            if a != b:
                parent[a] = b
    return {t: find(t) for t in tokens}


def wallet_overlap(session: Session, *, chain: str) -> dict:
    """How much of the feature table is the same wallet on several tokens."""
    rows = session.execute(text("""
        select wallet_address, token_address, features from wallet_feature
        where chain = :chain
    """), {"chain": chain}).all()
    per_wallet: dict[str, list] = defaultdict(list)
    for w, t, f in rows:
        per_wallet[w].append((t, f))
    multi = {w: v for w, v in per_wallet.items() if len(v) > 1}
    rows_multi = sum(len(v) for v in multi.values())
    # identical own-behaviour vectors across a wallet's tokens: the base_*
    # block is the part built from cross-token aggregation
    identical = 0
    for v in multi.values():
        bases = {tuple(sorted((k, round(float(x), 9)) for k, x in f.items()
                              if k.startswith("base_"))) for _, f in v}
        if len(bases) == 1:
            identical += len(v)
    return {
        "feature_rows": len(rows),
        "distinct_wallets": len(per_wallet),
        "wallets_on_2plus_tokens": len(multi),
        "rows_from_those_wallets": rows_multi,
        "rows_share": round(rows_multi / len(rows), 4) if rows else 0.0,
        "rows_with_identical_base_vector_across_tokens": identical,
        "max_tokens_per_wallet": max((len(v) for v in per_wallet.values()), default=0),
    }


def fold_dates(data: Dataset, launch: dict[str, datetime]) -> list[dict]:
    """Launch-date range of each GroupKFold test fold, to show whether the
    Phase 4 split was temporal (it was not)."""
    from sklearn.model_selection import GroupKFold
    out = []
    splits = min(train.N_SPLITS, len(set(data.groups)))
    for k, (tr, te) in enumerate(GroupKFold(n_splits=splits).split(
            data.X, data.y, data.groups)):
        tr_t = {g for g in data.groups[tr]}
        te_t = {g for g in data.groups[te]}
        out.append({
            "fold": k,
            "train_launch_min": min(launch[t] for t in tr_t).isoformat(),
            "train_launch_max": max(launch[t] for t in tr_t).isoformat(),
            "test_launch_min": min(launch[t] for t in te_t).isoformat(),
            "test_launch_max": max(launch[t] for t in te_t).isoformat(),
            "test_tokens": len(te_t),
        })
    return out


def temporal_holdout(data: Dataset, launch: dict[str, datetime], *,
                     features: list[str], model: str,
                     test_share: float = 0.3,
                     groups: dict[str, str] | None = None) -> dict:
    """Train on the earliest launches, test on the latest.

    The cut is placed between *groups* (shared-wallet components when given)
    so that no component straddles it; a component's date is its earliest
    launch.
    """
    groups = groups or {t: t for t in data.tokens}
    comp_start: dict[str, datetime] = {}
    for t in data.tokens:
        g = groups.get(t, t)
        comp_start[g] = min(comp_start.get(g, launch[t]), launch[t])
    ordered = sorted(comp_start, key=comp_start.get)
    n_tok = len(data.tokens)
    test_comps: set[str] = set()
    count = 0
    for g in reversed(ordered):
        if count >= test_share * n_tok:
            break
        test_comps.add(g)
        count += sum(1 for t in data.tokens if groups.get(t, t) == g)
    test_tokens = {t for t in data.tokens if groups.get(t, t) in test_comps}
    train_tokens = set(data.tokens) - test_tokens

    idx = [data.feature_names.index(f) for f in features if f in data.feature_names]
    tr = np.array([g in train_tokens for g in data.groups])
    te = ~tr
    res = {
        "train_tokens": len(train_tokens), "test_tokens": len(test_tokens),
        "train_launch_min": min(launch[t] for t in train_tokens).isoformat(),
        "train_launch_max": max(launch[t] for t in train_tokens).isoformat(),
        "test_launch_min": min(launch[t] for t in test_tokens).isoformat(),
        "test_launch_max": max(launch[t] for t in test_tokens).isoformat(),
        "train_pos_tokens": sum(1 for t in train_tokens if data.token_labels[t] == "RUG"),
        "test_pos_tokens": sum(1 for t in test_tokens if data.token_labels[t] == "RUG"),
    }
    y_tr, y_te = data.y[tr], data.y[te]
    if len(set(y_tr)) < 2 or len(set(y_te)) < 2:
        res.update(auc=None, ap=None, note="one side has a single class")
        return res
    est = train.make_model(model)
    est.fit(data.X[tr][:, idx], y_tr)
    p = est.predict_proba(data.X[te][:, idx])[:, 1]
    res.update(auc=round(float(roc_auc_score(y_te, p)), 4),
               ap=round(float(average_precision_score(y_te, p)), 4))
    return res


# ---- per-token timing, with no cross-token aggregation ------------------

def per_token_timing(session: Session, *, chain: str, data: Dataset,
                     window_minutes: float = WINDOW_HOURS * 60) -> Dataset:
    """Entry-delay features rebuilt from each (wallet, token) pair alone.

    Same rows as `data`, but the timing columns describe this wallet's buys
    of *this* token inside `window_minutes` of launch, rather than its buys
    of everything. The structure columns are dropped: they are graph-wide by
    construction and are a separate question.
    """
    rows = session.execute(text("""
        with pools as (
            select token_address,
                   case when dex = 'uniswap-v4' then :pm else address end as holder,
                   created_ts
            from pair where chain = :chain
        )
        select t.to_address, t.token_address,
               extract(epoch from (t.block_ts - po.created_ts))
        from transfer t
        join pools po on po.token_address = t.token_address
                     and po.holder = t.from_address
        join token_label l on l.token_address = t.token_address and l.chain = :chain
        where t.chain = :chain
          and t.block_ts <= l.launch_ts + make_interval(mins => :win)
    """), {"chain": chain, "pm": POOL_MANAGER, "win": int(window_minutes)}).all()
    delays: dict[tuple[str, str], list[float]] = defaultdict(list)
    for w, t, d in rows:
        delays[((w or "").lower(), t)].append(max(0.0, float(d or 0.0)))

    wallets = session.execute(text("""
        select wallet_address, token_address from wallet_feature
        where chain = :chain order by token_address, wallet_address
    """), {"chain": chain}).all()
    # dataset.load orders rows by (token, wallet), so this lines up with it
    keyed = [(w, t) for w, t in wallets if t in set(data.tokens)]
    assert len(keyed) == data.n_rows, "row order no longer matches dataset.load"

    names = ["pt_entry_delay_min", "pt_entry_delay_mean", "pt_buy_seen"]
    X = np.zeros((len(keyed), len(names)))
    for i, (w, t) in enumerate(keyed):
        d = delays.get((w, t))
        if d:
            X[i] = [min(d), sum(d) / len(d), 1.0]
    return Dataset(X=X, y=data.y, groups=data.groups, feature_names=names,
                   tokens=data.tokens, token_labels=data.token_labels)
