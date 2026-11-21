"""Bundle detection: the transaction rule, and the collector exclusion that
was added before any label was collected (DECISIONS.md, 2026-11-21)."""
from __future__ import annotations

from blocklens.graph import bundles as bd


def test_a_transaction_reaching_three_wallets_is_a_bundle():
    assert bd.classify_tx({"a", "b", "c"})
    assert not bd.classify_tx({"a", "b"})


def test_buyers_reached_by_bundles_are_counted_once():
    r = bd.from_recipients("t", {"tx1": {"a", "b", "c"}, "tx2": {"c", "d"}})
    assert r.bundled and r.bundle_txs == 1 and r.buyers == 4 and r.buyers_via_bundles == 3
    assert r.max_recipients == 3


def test_a_fee_collector_seen_across_many_launches_is_not_a_wallet():
    per_launch = {f"t{i}": {"tx": {f"buyer{i}", "fees", "reward"}} for i in range(12)}
    collectors = bd.recurring_collectors(per_launch)
    assert collectors == {"fees", "reward"}
    # buyer + two collectors: three recipients, but one wallet: not a bundle
    assert not bd.from_recipients("t0", per_launch["t0"], exclude=collectors).bundled


def test_a_rare_address_is_not_called_a_collector():
    per_launch = {f"t{i}": {"tx": {f"w{i}", f"x{i}", "fees"}} for i in range(5)}
    assert bd.recurring_collectors(per_launch) == set()
