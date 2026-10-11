"""Decoding real recorded logs, with no network.

Every assertion here is against `tests/fixtures/rpc_get_logs.json`, which
is a genuine `eth_getLogs` response from Base — 200 blocks of BRETT and its
Aerodrome pool. Values are checked against the raw hex in that file rather
than against numbers I believe to be right.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from blocklens.ingest import chain as chain_ingest
from blocklens.ingest import evm
from blocklens.ingest.budget import Budget
from blocklens.ingest.sources import RpcSource
from tests.conftest import load, rpc_client

FIX = load("rpc_get_logs.json")
LOGS = FIX["result"]
TOKEN = FIX["token"].lower()
PAIR = FIX["pair"].lower()
QUOTE = FIX["quote"].lower()
AS_OF = datetime(2030, 1, 1, tzinfo=timezone.utc)      # far future: not the subject here


def transfers() -> list[dict]:
    return [l for l in LOGS
            if l["address"].lower() == TOKEN and l["topics"][0] == evm.TRANSFER]


def swaps() -> list[dict]:
    return [l for l in LOGS if l["topics"][0] in evm.SWAP_TOPICS]


# ---- topics --------------------------------------------------------------

def test_topics_are_computed_not_pasted():
    """The known-good values for the three signatures that are stable
    across the industry. If keccak were wrong, everything else here would
    silently decode nothing."""
    assert evm.TRANSFER == \
        "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
    assert evm.V2_SWAP == \
        "0xd78ad95fa46c994b6551d0da85fc275fe613ce37657fb8d5e3d130840159d822"
    assert evm.V3_SWAP == \
        "0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67"


def test_keccak_matches_a_known_digest():
    assert evm.keccak256(b"").hex() == \
        "c5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470"


# ---- transfers -----------------------------------------------------------

def test_fixture_contains_what_the_tests_assume():
    """A fixture that quietly changed shape would make every test below
    pass against nothing."""
    assert len(transfers()) == 18
    assert len(swaps()) == 6


def test_transfer_decodes_against_the_raw_hex():
    log = transfers()[0]
    row = chain_ingest._decode_transfer(log, "base", 18)

    assert row["from_address"] == "0x" + log["topics"][1][-40:].lower()
    assert row["to_address"] == "0x" + log["topics"][2][-40:].lower()
    assert row["raw_value"] == int(log["data"], 16)
    assert row["value_normalised"] == pytest.approx(int(log["data"], 16) / 1e18)
    assert row["block_number"] == int(log["blockNumber"], 16)
    assert row["log_index"] == int(log["logIndex"], 16)
    assert row["provenance"] == "live"


def test_decimals_change_the_normalised_value_not_the_raw_one():
    log = transfers()[0]
    a = chain_ingest._decode_transfer(log, "base", 18)
    b = chain_ingest._decode_transfer(log, "base", 6)

    assert a["raw_value"] == b["raw_value"], "raw_value must stay as the chain reported it"
    assert b["value_normalised"] == pytest.approx(a["value_normalised"] * 10 ** 12)


def test_a_transfer_missing_its_indexed_parties_is_skipped_not_guessed():
    log = dict(transfers()[0])
    log["topics"] = log["topics"][:2]
    assert chain_ingest._decode_transfer(log, "base", 18) is None


# ---- swaps ---------------------------------------------------------------

def _by_tx(rows):
    out = {}
    for r in rows:
        out.setdefault(r["tx_hash"], []).append(r)
    return out


def test_swap_side_comes_from_the_transfers_not_the_event_sign():
    """The pool sending tokens out is a buy, whatever the venue's sign
    convention happens to be. This fixture's pool is an Aerodrome
    concentrated-liquidity pool, which emits the Uniswap V3 signature."""
    rows = [chain_ingest._decode_transfer(l, "base", 18) for l in transfers()]
    for r in rows:
        r["block_ts"] = AS_OF
    by_tx = _by_tx(rows)

    decoded = []
    for log in swaps():
        row = chain_ingest._decode_swap(
            log, chain="base", token=TOKEN, quote=QUOTE, token_dec=18,
            quote_dec=18, pair_key=PAIR, counterparty=PAIR, transfers_by_tx=by_tx,
        )
        assert row is not None
        decoded.append(row)

    assert all(r["side"] in ("buy", "sell") for r in decoded)
    # Every swap in this window moved tokens out of the pool.
    assert [r["side"] for r in decoded] == ["buy"] * 6

    for r, log in zip(decoded, swaps()):
        a0, a1 = evm.to_int(evm.words(log["data"])[0]), evm.to_int(evm.words(log["data"])[1])
        token0_is_token = TOKEN < QUOTE
        expected_quote = abs(a1 if token0_is_token else a0) / 1e18
        assert r["quote_amount"] == pytest.approx(expected_quote)
        assert r["token_amount"] > 0
        assert r["pair_address"] == PAIR
        # Part A proved the counterparty is a router, so this stays null.
        assert r["wallet_address"] is None


def test_price_is_left_null_for_a_weth_quoted_pool():
    """A WETH-quoted price is not a dollar price, and Phase 1 has no
    historical ETH price. Null beats a number that looks like dollars."""
    rows = [chain_ingest._decode_transfer(l, "base", 18) for l in transfers()]
    for r in rows:
        r["block_ts"] = AS_OF
    row = chain_ingest._decode_swap(
        swaps()[0], chain="base", token=TOKEN, quote=QUOTE, token_dec=18,
        quote_dec=18, pair_key=PAIR, counterparty=PAIR, transfers_by_tx=_by_tx(rows),
    )
    assert row["price_usd"] is None


def test_price_is_computed_for_a_stablecoin_quoted_pool():
    rows = [chain_ingest._decode_transfer(l, "base", 18) for l in transfers()]
    for r in rows:
        r["block_ts"] = AS_OF
    usdc = evm.USDC
    row = chain_ingest._decode_swap(
        swaps()[0], chain="base", token=TOKEN, quote=usdc, token_dec=18,
        quote_dec=6, pair_key=PAIR, counterparty=PAIR, transfers_by_tx=_by_tx(rows),
    )
    assert row["price_usd"] == pytest.approx(row["quote_amount"] / row["token_amount"])


# ---- wallets -------------------------------------------------------------

def test_wallets_exclude_the_pool_and_the_zero_address():
    rows = [chain_ingest._decode_transfer(l, "base", 18) for l in transfers()]
    for r in rows:
        r["block_ts"] = AS_OF

    wallets = chain_ingest._wallets_from(rows, chain="base", pair=PAIR)
    addrs = {w["address"] for w in wallets}

    assert PAIR not in addrs
    assert evm.ZERO_ADDRESS not in addrs
    assert evm.UNISWAP_V4_POOL_MANAGER not in addrs
    assert addrs, "the window has counterparties, so some wallets are expected"
    assert all(w["funding_source"] == "unknown" for w in wallets), \
        "Phase 1 must not claim to know how a wallet was funded"


def test_wallet_first_seen_is_the_earliest_block_not_the_last():
    rows = [chain_ingest._decode_transfer(l, "base", 18) for l in transfers()]
    for r in rows:
        r["block_ts"] = AS_OF
    wallets = {w["address"]: w for w in
               chain_ingest._wallets_from(rows, chain="base", pair=PAIR)}

    for r in rows:
        for side in ("from_address", "to_address"):
            w = wallets.get(r[side])
            if w:
                assert w["first_seen_block"] <= r["block_number"]


# ---- discovery -----------------------------------------------------------

def test_pool_created_logs_yield_candidates(no_network):
    fix = load("rpc_pool_created.json")
    cands = [c for c in (chain_ingest._candidate(l, "uniswap-v3") for l in fix["result"]) if c]

    assert cands, "the recorded PoolCreated logs produced no candidates"
    for c in cands:
        assert c["token_address"].startswith("0x") and len(c["token_address"]) == 42
        assert c["quote_address"] in chain_ingest.V4_QUOTES
        assert c["pair_address"] and len(c["pair_address"]) == 42
        assert c["pool_id"] is None, "a V3 pool has an address, not a pool id"
        assert c["dex"] == "uniswap-v3"


def test_a_pool_between_two_majors_is_not_a_candidate():
    """WETH/USDC is not a launch, and a scan that returns it is a scan that
    will spend its budget on the wrong tokens."""
    log = {
        "topics": ["0x" + "00" * 32,
                   "0x" + "0" * 24 + evm.WETH[2:],
                   "0x" + "0" * 24 + evm.USDC[2:],
                   "0x" + f"{3000:064x}"],
        "data": "0x" + f"{60:064x}" + "0" * 24 + "ab" * 20,
        "blockNumber": "0x1",
    }
    assert chain_ingest._candidate(log, "uniswap-v3") is None


def test_v4_candidate_carries_a_pool_id_and_no_address():
    """V4 is a singleton: the pool has no address of its own, and native ETH
    as the zero address is a quote asset there rather than a bad value."""
    novel = "0x" + "cd" * 20
    log = {
        "topics": ["0x" + "00" * 32,
                   "0x" + "7f" * 32,                       # pool id: not an address
                   "0x" + "0" * 64,                        # native ETH
                   "0x" + "0" * 24 + novel[2:]],
        "data": "0x",
        "blockNumber": "0x2",
    }
    cand = chain_ingest._candidate(log, "uniswap-v4")

    assert cand["token_address"] == novel
    assert cand["quote_address"] == evm.ZERO_ADDRESS
    assert cand["pool_id"] == "0x" + "7f" * 32
    assert cand["pair_address"] is None


# ---- the source itself ---------------------------------------------------

def test_rpc_source_reads_the_recorded_response_without_a_network(no_network):
    budget = Budget(max_calls=10)
    rpc = RpcSource(budget, client=rpc_client({
        "eth_getLogs": LOGS,
        "eth_getBlockByNumber": load("rpc_get_block.json")["result"],
    }))

    got = rpc.get_logs(addresses=[TOKEN, PAIR], from_block=FIX["from_block"],
                       to_block=FIX["to_block"])

    assert len(got) == len(LOGS)
    assert budget.requests == 1, "every call must be charged to the budget exactly once"


def test_block_timestamps_are_cached_so_a_hot_block_costs_one_call(no_network):
    budget = Budget(max_calls=10)
    rpc = RpcSource(budget, client=rpc_client({
        "eth_getBlockByNumber": load("rpc_get_block.json")["result"],
    }))

    rpc.block_timestamps([100, 100, 100, 101])

    assert budget.requests == 2, "the cache did not spare the repeated block"


def test_timestamps_come_free_from_the_logs_when_the_endpoint_sends_them(no_network):
    """The dominant cost of a backfill, if this field were missing."""
    budget = Budget(max_calls=10)
    rpc = RpcSource(budget, client=rpc_client({}))   # any call at all would fail

    blocks = {int(l["blockNumber"], 16) for l in LOGS}
    ts = chain_ingest._timestamps(rpc, LOGS, blocks)

    assert ts.keys() == blocks
    assert all(v > 1_600_000_000 for v in ts.values())
    assert budget.requests == 0, "a timestamp already in the log was fetched again"


def test_timestamps_fall_back_to_fetching_what_the_logs_omit(no_network):
    budget = Budget(max_calls=10)
    rpc = RpcSource(budget, client=rpc_client({
        "eth_getBlockByNumber": load("rpc_get_block.json")["result"],
    }))
    stripped = [{k: v for k, v in l.items() if k != "blockTimestamp"} for l in LOGS[:3]]
    blocks = {int(l["blockNumber"], 16) for l in stripped}

    ts = chain_ingest._timestamps(rpc, stripped, blocks)

    assert ts.keys() == blocks
    assert budget.requests == len(blocks)


# ---- the activity probe --------------------------------------------------

def test_the_probe_passes_a_token_that_traded(no_network):
    """Four windows instead of forty-four. A token with real transfers in a
    sampled window has to survive the filter."""
    budget = Budget(max_calls=20)
    rpc = RpcSource(budget, client=rpc_client({"eth_getLogs": LOGS}))

    got = chain_ingest.probe_activity(
        rpc, token_address=TOKEN, start_block=FIX["from_block"],
        pair_address=PAIR)

    assert got["active"] is True
    assert got["buys_seen"] > 0
    # Stops as soon as it has an answer rather than reading all four.
    assert got["windows_read"] == 1
    assert budget.requests == 1


def test_the_probe_rejects_a_pool_with_nothing_in_it(no_network):
    budget = Budget(max_calls=20)
    rpc = RpcSource(budget, client=rpc_client({"eth_getLogs": []}))

    got = chain_ingest.probe_activity(
        rpc, token_address=TOKEN, start_block=FIX["from_block"],
        pair_address=PAIR)

    assert got["active"] is False
    assert got["buys_seen"] == 0
    # It paid for every sample before concluding nothing is there, which is
    # the honest cost of a negative answer.
    assert got["windows_read"] == len(chain_ingest.PROBE_FRACTIONS)


def test_a_lone_mint_is_not_treated_as_trading(no_network):
    """A pool whose only event is the mint never traded. Counting it as
    active would put the spam back into the dataset the probe exists to
    keep out."""
    # a transfer that is not from the pool: a mint or an ordinary send
    one_mint = [l for l in LOGS
                if l["address"].lower() == TOKEN
                and l["topics"][0] == evm.TRANSFER
                and evm.addr_from_topic(l["topics"][1]) != PAIR][:1]
    budget = Budget(max_calls=20)
    rpc = RpcSource(budget, client=rpc_client({"eth_getLogs": one_mint}))

    got = chain_ingest.probe_activity(
        rpc, token_address=TOKEN, start_block=FIX["from_block"], pair_address=PAIR)

    assert got["active"] is False, "a single transfer is a mint, not a market"
