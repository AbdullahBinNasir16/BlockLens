"""Phase 5's new guarantees.

* Rule v2 turns untradeable pools into NEVER_LAUNCHED, never RUG.
* The batched sampler decodes exactly as the serial one does.
* A pooled batch never drops the tail of a long request (a real bug, found
  in the first six Phase 5 labels).
* The rule checker is fixed, and the prior correction does what it says.
* Window draws are deterministic, and training windows stay before the split.
"""
from __future__ import annotations

import numpy as np

from blocklens.ingest.budget import Budget
from blocklens.ingest.sources import Endpoint, PooledRpcSource, SourceError
from blocklens.label import rules
from blocklens.label.sample import Sampler
from blocklens.model import rulecheck
from blocklens.sampling import design as d
from scripts.phase5_model import prior_shift

LAUNCH = 1_760_000_000
DAY = 86_400


def m(**kw) -> rules.Measurements:
    base = dict(swaps_in_window=50, peak_reserve=1_000.0, peak_reserve_ts=LAUNCH,
                reserve_at_end=0.0, peak_price=10.0, peak_price_ts=LAUNCH,
                price_at_end=10.0, largest_drop_fraction=1.0,
                largest_drop_ts=LAUNCH + DAY, active_days_last_30=0,
                points_sampled=100, points_usable=100)
    base.update(kw)
    return rules.Measurements(**base)


def test_v1_rug_with_extreme_price_is_never_launched_under_v2():
    v = rules.classify(m(extreme_price_seen=True))
    assert v.label == "NEVER_LAUNCHED" and v.degenerate_pool


def test_outflow_above_peak_reserve_is_degenerate():
    assert rules.classify(m(largest_outflow_amount=20_400.0)).label == "NEVER_LAUNCHED"
    assert rules.classify(m(largest_outflow_amount=1_000.0)).label == "RUG"


def test_a_real_pull_is_still_rug():
    assert rules.classify(m()).label == "RUG"


class ScriptedRpc:
    """Answers `batch` from a function of (method, params)."""

    def __init__(self, answer):
        self.answer = answer
        self.calls = 0

    def batch(self, calls, size=20):
        self.calls += len(calls)
        return [self.answer(mth, p) for mth, p in calls]


def test_batched_points_decode_like_serial_points():
    word = "0x" + format(10**21, "064x")
    sqrt = 2**96 * 3
    slot0 = "0x" + format(sqrt, "064x") + "0" * 64
    rpc = ScriptedRpc(lambda mth, p: slot0 if p[0]["data"].startswith("0x3850c7bd") else word)
    s = Sampler(rpc, Budget(max_calls=10))
    pts = s.points([(100, 1), (200, 2)], token="0x" + "1" * 40, quote="0x" + "2" * 40,
                   dex="uniswap-v3", pair_key="0x" + "3" * 40, token_decimals=18,
                   quote_decimals=18, token_is_zero=True)
    assert [p.token_reserve for p in pts] == [1000.0, 1000.0]
    assert [p.quote_reserve for p in pts] == [1000.0, 1000.0]
    assert pts[0].price == 9.0           # (sqrt / 2^96)^2


def test_reverted_slot0_falls_back_to_the_reserve_ratio():
    word = "0x" + format(2 * 10**18, "064x")
    rpc = ScriptedRpc(lambda mth, p: SourceError("revert")
                      if p[0]["data"].startswith("0x3850c7bd") else word)
    s = Sampler(rpc, Budget(max_calls=10))
    (pt,) = s.points([(100, 1)], token="0x" + "1" * 40, quote="0x" + "2" * 40,
                     dex="uniswap-v2", pair_key="0x" + "3" * 40, token_decimals=18,
                     quote_decimals=18, token_is_zero=True)
    assert pt.price == 1.0


def test_pooled_batch_serves_every_call_of_a_long_request(monkeypatch):
    rpc = PooledRpcSource(Budget(max_calls=10_000),
                          pool=[Endpoint("http://a", batch=8, logs=False, interval=0.0)])

    def post(e, body):
        return [{"id": b["id"], "result": "0x" + format(b["params"][0], "064x")} for b in body]

    monkeypatch.setattr(rpc, "_post", post)
    calls = [("eth_call", [i]) for i in range(330)]        # 42 batches of 8
    out = rpc.batch(calls)
    assert not any(isinstance(o, SourceError) for o in out)
    assert [int(o, 16) for o in out] == list(range(330))


def test_rule_checker_is_fixed_and_counts_flags():
    quiet = dict(t_buys=10, t_sells=4, t_top_buyer_share=0.2, t_unique_buyers=9,
                 r_deployer_bought=0, t_same_block_buyers=0)
    assert rulecheck.score(quiet) == 0 and not rulecheck.verdict(quiet)
    loud = dict(quiet, t_sells=0, t_top_buyer_share=0.9)
    assert rulecheck.score(loud) == 2 and rulecheck.verdict(loud)


def test_prior_shift_recovers_the_true_rate_at_the_sampled_rate():
    p = np.array([0.5])
    assert np.isclose(prior_shift(p, 0.5, 0.1), 0.1)
    assert np.isclose(prior_shift(np.array([0.3]), 0.3, 0.3), 0.3)


def test_windows_are_deterministic_and_training_stays_before_the_split():
    a, b = d.draw("train", 0), d.draw("train", 0)
    assert [w.start_ts for w in a] == [w.start_ts for w in b]
    assert all(w.start_ts < d.SPLIT_DATE for w in a)
    assert len(d.draw("random", 0)) == len(d.weeks())
    assert d.draw("random", 0)[0].start_ts != d.draw("random", 1)[0].start_ts


# ---- Phase 6: the FAILED split ------------------------------------------

from blocklens.label import extraction as ex
from blocklens.model import rulecheck_x


def x(**kw) -> ex.Extraction:
    base = dict(token="0xt", swaps=20, priced_share=1.0, late_spend=10.0,
                late_spend_share=0.5, early_net=5.0, late_net=-6.0, extract_share=0.5)
    base.update(kw)
    o = ex.Extraction(token=base.pop("token"))
    for k, v in base.items():
        setattr(o, k, v)
    return o


def test_cash_out_to_early_wallets_paid_by_later_losers_is_extracted():
    assert ex.classify(x()) == "EXTRACTED"


def test_no_later_buyers_is_decay_not_extraction():
    assert ex.classify(x(late_spend=0.0, late_spend_share=0.0, extract_share=None)) == "DECAY"


def test_later_buyers_who_did_not_lose_were_not_extracted_from():
    assert ex.classify(x(late_net=1.0)) == "DECAY"


def test_poorly_priced_tokens_are_unclear():
    assert ex.classify(x(priced_share=0.5)) == "UNCLEAR"


def test_early_concentration_checker_counts_its_flags():
    r = dict(t_top_buyer_share=0.9, t_same_block_buyers=0, t_share_buys_first_minute=0.1,
             t_log_price_drift=2.0, t_sell_buy_ratio=0.1)
    assert rulecheck_x.score(r) == 2


# ---- Phase 9: the paper agent ---------------------------------------------

from blocklens.live import resolver as rv


def test_a_pulled_pool_is_a_total_loss_whatever_its_last_price():
    assert rv._trade_return(5.0, True, 0.03) == -1.0


def test_return_is_net_of_cost_and_capped():
    assert abs(rv._trade_return(1.0, False, 0.03) - (-0.03)) < 1e-12
    assert rv._trade_return(10_000.0, False, 0.03) == rv.RETURN_CAP


def test_unpriced_exit_is_not_a_trade():
    assert rv._trade_return(None, False, 0.03) is None
