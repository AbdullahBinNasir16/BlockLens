"""Bundle detection: one transaction that buys a token and spreads it to
many wallets (DECISIONS.md, "Bundle detection, pre-registered", 2026-11-21).

The definition is fixed: a **bundle transaction** is a transaction inside a
launch's first five minutes that contains a swap of that launch's pool and
delivers the token to at least `MIN_RECIPIENTS` distinct wallets (not a
pool, not known infrastructure, not the zero address). A launch is
**bundled** if it has at least one.

Why this and not "wallets funded by one address that bought together": a
search of the store found no case of independent funded wallets buying the
same token within 90 seconds, while single transactions delivering a token
to dozens of wallets are plain in the data (Figure 10). On a holder list
those wallets look like many buyers; on chain they are one actor's action.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.orm import Session

from ..model import token_features as tf
from ..sampling.design import cutoff_block

MIN_RECIPIENTS = 3
# Deviation recorded 2026-11-21, before any label was collected: an address
# that receives the token in candidate transactions of this many different
# launches is a fee or reward collector (two such addresses appeared in 65 and
# 54 of the first 111 detections), not a wallet.
RECURRENCE_INFRA = 10


@dataclass
class BundleReading:
    token: str
    bundle_txs: int
    max_recipients: int
    buyers: int                    # distinct wallets that acquired the token in swap txs by minute 5
    buyers_via_bundles: int

    @property
    def bundled(self) -> bool:
        return self.bundle_txs > 0

    @property
    def bundled_share(self) -> float:
        return self.buyers_via_bundles / self.buyers if self.buyers else 0.0


def classify_tx(recipients: set[str]) -> bool:
    """A swap transaction is a bundle if it reaches enough distinct wallets."""
    return len(recipients) >= MIN_RECIPIENTS


def candidate_recipients(s: Session, ctx: tf.Context, *, token: str, pool: str, created_block: int,
                         chain: str = "base") -> dict[str, set[str]]:
    """Per swap transaction in the first five minutes: the wallets it reached."""
    cut = cutoff_block(created_block)
    swap_tx = {r[0] for r in s.execute(text("""
        select distinct tx_hash from swap
        where chain = :c and pair_address = :p and block_number between :lo and :hi
    """), {"c": chain, "p": pool, "lo": created_block, "hi": cut})}
    if not swap_tx:
        return {}
    per_tx: dict[str, set[str]] = defaultdict(set)
    for tx, to in s.execute(text("""
        select tx_hash, to_address from transfer
        where chain = :c and token_address = :t and block_number between :lo and :hi
          and tx_hash = any(:x)
    """), {"c": chain, "t": token, "lo": created_block, "hi": cut, "x": list(swap_tx)}).all():
        if ctx.is_wallet(to):
            per_tx[tx].add(to)
    return per_tx


def recurring_collectors(per_launch: dict[str, dict[str, set[str]]],
                         min_launches: int = RECURRENCE_INFRA) -> set[str]:
    """Addresses reached by multi-recipient swap transactions in at least
    `min_launches` different launches: fee and reward collectors."""
    seen: dict[str, set[str]] = defaultdict(set)
    for token, per_tx in per_launch.items():
        for ws in per_tx.values():
            if len(ws) >= 2:
                for w in ws:
                    seen[w].add(token)
    return {w for w, toks in seen.items() if len(toks) >= min_launches}


def from_recipients(token: str, per_tx: dict[str, set[str]], exclude: set[str] = frozenset()) -> BundleReading:
    per = {tx: ws - exclude for tx, ws in per_tx.items()}
    per = {tx: ws for tx, ws in per.items() if ws}
    buyers = set().union(*per.values()) if per else set()
    bundles = [w for w in per.values() if classify_tx(w)]
    via = set().union(*bundles) if bundles else set()
    return BundleReading(token=token, bundle_txs=len(bundles),
                         max_recipients=max((len(w) for w in per.values()), default=0),
                         buyers=len(buyers), buyers_via_bundles=len(via))


def read(s: Session, ctx: tf.Context, *, token: str, pool: str, created_block: int,
         collectors: set[str] = frozenset(), chain: str = "base") -> BundleReading:
    """One launch. Pass the store-wide `recurring_collectors` set, or fee
    collectors will be counted as wallets (the 2026-11-21 deviation)."""
    per_tx = candidate_recipients(s, ctx, token=token, pool=pool, created_block=created_block, chain=chain)
    return from_recipients(token, per_tx, exclude=collectors)
