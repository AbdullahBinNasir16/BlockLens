"""Reserve and price, sampled at historical blocks.

Every label criterion reads from here, and nothing here decides anything.

**Why sampling rather than reconstruction.** The brief specified building a
reserve series by accumulating quote-token transfers in and out of the pair.
That was measured and rejected: the keyless gateway caps `eth_getLogs` at
1,000 blocks however narrowly the query is filtered, so 90 days costs 3,888
calls per token — 777,600 for a 200-token set. Archive `eth_call` works on
the same endpoint at least 365 days back, which means a reserve can be
*read* at a block instead of accumulated, for one call: 90 daily points in
43 seconds, measured.

It is also the more accurate of the two. A cumulative sum is only right if
every transfer in 90 days was captured, and one missed window biases every
later point with no way to notice. Each sampled balance is independent and
exact, so there is nothing to drift.

**What is measured, per venue.** `balanceOf(token, holder)` is the pool's
token reserve, where the holder is the pair contract on V2/V3/Aerodrome, and
the Uniswap V4 PoolManager on V4. That the V4 case is exact is not assumed:
spike B6 checked it against Phase 1's own stored transfers for five tokens
and matched to the wei on all five.

The quote side is readable for the venues that hold their own funds, but not
on V4, where one PoolManager holds every pool's WETH at once. So the
token-side reserve is the uniform signal and the quote side is a bonus where
it exists. That is not a loss for the label: an LP withdrawal removes both
sides, so a token reserve collapsing is the withdrawal signal, while a
sell-off *raises* the token reserve — the two are distinguishable by sign,
which they would not be on the quote side alone.

See `spikes/B_FINDINGS.md` for the measurements.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..config import CONFIG, Config
from ..ingest.budget import Budget
from ..ingest.evm import UNISWAP_V4_POOL_MANAGER, keccak256
from ..ingest.sources import RpcSource, SourceError

BALANCE_OF = "0x70a08231"
# V4 keeps pool state in a mapping at slot 6; `extsload` is the contract's
# own accessor for it. Selectors are computed, never pasted (Phase 1 rule).
EXTSLOAD = "0x" + keccak256(b"extsload(bytes32)").hex()[:8]
V4_POOLS_SLOT = 6

# Confirmed by agreement, not by a published list: spike B5 called this and
# `extsload` on the same pool and got byte-identical slot0. Two of the three
# candidate addresses returned nothing.
STATE_VIEW = "0xa3c0c9b65bad0b08107aa264b0f3db444b867a71"

Q96 = 2 ** 96


@dataclass
class Point:
    """One observation of a pool, at one block."""
    block: int
    ts: int
    error: str | None = None
    token_reserve: float | None = None
    quote_reserve: float | None = None
    # A *relative* price: the label only ever compares a price to this
    # token's own peak, so an unscaled ratio is sufficient and avoids
    # inventing a dollar figure the data cannot support.
    price: float | None = None
    source: str = ""


@dataclass
class Series:
    token_address: str
    pair_key: str
    dex: str
    points: list[Point] = field(default_factory=list)
    calls: int = 0
    errors: list[str] = field(default_factory=list)
    # "coarse" when the cheap pass showed a pool that never moved,
    # "refined" when the dense grid was needed, "dense" when forced.
    mode: str = "dense"

    @property
    def ok(self) -> list[Point]:
        return [p for p in self.points if p.token_reserve is not None]

    def peak_reserve(self) -> float | None:
        vals = [p.token_reserve for p in self.ok]
        return max(vals) if vals else None

    def peak_price(self, after_ts: int | None = None) -> float | None:
        """Peak price, optionally ignoring everything before `after_ts`.

        The label excludes the first hour, because a launch candle is an
        artefact of there being almost no liquidity yet rather than a price
        anyone could trade at in size.
        """
        vals = [p.price for p in self.points
                if p.price is not None and (after_ts is None or p.ts >= after_ts)]
        return max(vals) if vals else None


def _word(res: str, i: int = 0) -> int:
    raw = res[2:] if res.startswith("0x") else res
    chunk = raw[i * 64:(i + 1) * 64]
    return int(chunk, 16) if chunk else 0


def v4_state_slot(pool_id: str) -> str:
    """keccak256(poolId . uint256(6)) — where a V4 pool's state lives."""
    raw = bytes.fromhex(pool_id[2:]) + V4_POOLS_SLOT.to_bytes(32, "big")
    return "0x" + keccak256(raw).hex()


def decode_slot0(word: int) -> tuple[int, int]:
    """slot0 packs sqrtPriceX96 (160 bits) then tick (24, signed)."""
    sqrt_price = word & ((1 << 160) - 1)
    tick = (word >> 160) & ((1 << 24) - 1)
    if tick >= (1 << 23):
        tick -= 1 << 24
    return sqrt_price, tick


class Sampler:
    """Reads a pool's state at a block. One call per quantity, no caching
    beyond what the caller keeps, because each block is asked for once."""

    def __init__(self, rpc: RpcSource, budget: Budget, config: Config = CONFIG):
        self.rpc = rpc
        self.budget = budget
        self.config = config

    # ---- primitives ------------------------------------------------------

    def balance_of(self, token: str, holder: str, block: int) -> float:
        data = BALANCE_OF + "0" * 24 + holder[2:].lower()
        res = self.rpc.call("eth_call", [{"to": token, "data": data}, hex(block)])
        return _word(res) if res and res != "0x" else 0.0

    def v4_slot0(self, pool_id: str, block: int) -> tuple[int, int]:
        data = EXTSLOAD + v4_state_slot(pool_id)[2:]
        res = self.rpc.call(
            "eth_call", [{"to": UNISWAP_V4_POOL_MANAGER, "data": data}, hex(block)])
        return decode_slot0(_word(res))

    def v3_slot0(self, pair: str, block: int) -> tuple[int, int]:
        sig = "0x" + keccak256(b"slot0()").hex()[:8]
        res = self.rpc.call("eth_call", [{"to": pair, "data": sig}, hex(block)])
        sqrt_price = _word(res, 0)
        tick = _word(res, 1)
        if tick >= (1 << 255):
            tick -= 1 << 256
        return sqrt_price, tick

    # ---- one observation -------------------------------------------------

    def point(self, *, block: int, ts: int, token: str, quote: str, dex: str,
              pair_key: str, token_decimals: int, quote_decimals: int,
              token_is_zero: bool) -> Point:
        """Everything knowable about a pool at one block, cheaply.

        Two calls on V4 (token balance, slot0), two or three elsewhere.
        A failure on one quantity does not discard the others — a pool can
        answer its balance and revert on its price.
        """
        p = Point(block=block, ts=ts, source=dex)
        is_v4 = dex == "uniswap-v4"
        holder = UNISWAP_V4_POOL_MANAGER if is_v4 else pair_key

        try:
            p.token_reserve = self.balance_of(token, holder, block) / (10 ** token_decimals)
        except SourceError as e:
            # Recorded, not swallowed. An early version discarded these and
            # a token whose samples had almost all failed still produced a
            # confident label off the 12 points that worked.
            p.error = str(e)[:160]
            p.source = f"{dex}/balance-failed"

        if not is_v4:
            # The quote side is only meaningful where the pool holds its own
            # funds. On V4 the PoolManager's WETH belongs to every pool.
            try:
                p.quote_reserve = (
                    self.balance_of(quote, pair_key, block) / (10 ** quote_decimals))
            except SourceError:
                pass

        try:
            if is_v4:
                sqrt_price, _tick = self.v4_slot0(pair_key, block)
                p.price = self._price_from_sqrt(sqrt_price, token_is_zero)
            else:
                try:
                    sqrt_price, _tick = self.v3_slot0(pair_key, block)
                    p.price = self._price_from_sqrt(sqrt_price, token_is_zero)
                except SourceError:
                    # A constant-product pool has no slot0; its price is the
                    # ratio of the two balances, which we already hold.
                    if p.token_reserve and p.quote_reserve:
                        p.price = p.quote_reserve / p.token_reserve
        except SourceError:
            pass

        return p

    def points(self, specs: list[tuple[int, int]], *, token: str, quote: str, dex: str,
               pair_key: str, token_decimals: int, quote_decimals: int,
               token_is_zero: bool) -> list[Point]:
        """`point` for many (block, ts) pairs, as JSON-RPC batches.

        The same calls as `point`, issued together and decoded the same way,
        including the constant-product fallback when `slot0` reverts. Phase 5
        checked equivalence against stored Phase 2 series before using it
        (`scripts/phase5.py verify-batch`).
        """
        is_v4 = dex == "uniswap-v4"
        holder = UNISWAP_V4_POOL_MANAGER if is_v4 else pair_key
        bal = lambda t, h: BALANCE_OF + "0" * 24 + h[2:].lower()  # noqa: E731
        slot0_v3 = "0x" + keccak256(b"slot0()").hex()[:8]

        calls: list[tuple[str, list]] = []
        layout: list[tuple[int, str]] = []          # (spec index, quantity)
        for i, (block, _ts) in enumerate(specs):
            tag = hex(block)
            calls.append(("eth_call", [{"to": token, "data": bal(token, holder)}, tag]))
            layout.append((i, "token"))
            if not is_v4:
                calls.append(("eth_call", [{"to": quote, "data": bal(quote, pair_key)}, tag]))
                layout.append((i, "quote"))
            if is_v4:
                data = EXTSLOAD + v4_state_slot(pair_key)[2:]
                calls.append(("eth_call", [{"to": UNISWAP_V4_POOL_MANAGER, "data": data}, tag]))
            else:
                calls.append(("eth_call", [{"to": pair_key, "data": slot0_v3}, tag]))
            layout.append((i, "slot0"))

        results = self.rpc.batch(calls)
        got: dict[tuple[int, str], Any] = {k: r for k, r in zip(layout, results)}

        out: list[Point] = []
        for i, (block, ts) in enumerate(specs):
            p = Point(block=block, ts=ts, source=dex)
            r = got.get((i, "token"))
            if isinstance(r, SourceError):
                p.error = str(r)[:160]
                p.source = f"{dex}/balance-failed"
            else:
                p.token_reserve = (_word(r) if r and r != "0x" else 0.0) / (10 ** token_decimals)
            if not is_v4:
                q = got.get((i, "quote"))
                if not isinstance(q, SourceError):
                    p.quote_reserve = (_word(q) if q and q != "0x" else 0.0) / (10 ** quote_decimals)
            s = got.get((i, "slot0"))
            if isinstance(s, SourceError):
                if not is_v4 and p.token_reserve and p.quote_reserve:
                    p.price = p.quote_reserve / p.token_reserve
            else:
                word = _word(s) if s and s != "0x" else 0
                if is_v4:
                    sqrt_price, _tick = decode_slot0(word)
                else:
                    sqrt_price = word
                p.price = self._price_from_sqrt(sqrt_price, token_is_zero)
            out.append(p)
        return out

    @staticmethod
    def _price_from_sqrt(sqrt_price: int, token_is_zero: bool) -> float | None:
        """Price of the token in quote units, up to a constant.

        Decimals are deliberately not applied. Every use of this number is a
        comparison against the same token's own peak, so a constant factor
        cancels — and applying a decimals correction we are not certain of
        would turn a sound ratio into an unsound absolute.
        """
        if not sqrt_price:
            return None
        ratio = (sqrt_price / Q96) ** 2      # price of token0 in token1
        if ratio <= 0:
            return None
        return ratio if token_is_zero else 1.0 / ratio
