"""Phase 6 label work: how a FAILED token failed.

**Why not "insiders exited before the collapse".** That was the first
definition, and a 50-token pilot rejected it. 563 of 584 FAILED tokens never
collapse: on a V4 launchpad pool the liquidity is single-sided, so the
launch price is a floor, and a failed token returns to it rather than
falling through it. The median FAILED token's sampled price at 1 h, 6 h, a
week and day 90 is its launch price. The pilot also found zero identifiable
insiders for the median token, because launchpad tokens have no dev
allocation in the launch transaction. The definition had no collapse to
anchor to and no insiders to follow.

**What a FAILED token actually is.** A day-0 round trip: early buyers buy,
later buyers pay more, the early buyers sell into them, and the price
returns to the floor. The money did not leave through the liquidity pool,
as in a RUG; it moved between traders. So the question that splits FAILED
is whether that transfer happened:

* **EXTRACTED** — the wallets that were in by the cutoff (minute 5) took
  out, in realised cash, at least `EXTRACT_SHARE` of what later buyers put
  in; later buyers lost money; and later buyers supplied a material share
  of all the money.

**Realised cash only.** An earlier version valued unsold tokens at the last
swap price. The last trade is often dust at a spiked price, and launch
allocations cost nothing, so paper value swamped real money: the full run
showed later buyers "gaining" 36x their stake at the 90th percentile. Cash
in and out of a cohort is what was actually extracted, and it cannot be
inflated. Trades *within* the early cohort cancel, so a net-positive early
cohort was paid by someone outside it.
* **DECAY** — no material transfer. Either nobody came after minute 5, or
  they came and did not fund the early wallets.

Everything is measured over the first `WINDOW_HOURS` hours, from stored
swaps and transfers. Cohorts are decided by the first moment a wallet
acquired the token, so the early cohort is exactly the set of holders the
product could see at minute 5. Quote amounts come from the pool's own swap
events, attributed to wallets through the transfers in the same transaction
— the only way to price a routed trade (Phase 3). Everything is a ratio, so
WETH- and USDC-quoted pools are comparable without a dollar price.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from sqlalchemy import text
from sqlalchemy.orm import Session

from ..ingest.evm import UNISWAP_V4_POOL_MANAGER as PM
from ..sampling.design import BLOCK_SECONDS, CUTOFF_BLOCKS

EXTRACTION_VERSION = "x1-2026-10"
ZERO = "0x0000000000000000000000000000000000000000"
WINDOW_HOURS = 6
WINDOW_BLOCKS = WINDOW_HOURS * 3600 // BLOCK_SECONDS
# The criterion, swept in the sensitivity report.
EXTRACT_SHARE = 0.25        # early cohort's profit >= 25% of late buyers' spend
LATE_SPEND_SHARE = 0.10     # late buyers supplied >= 10% of all buy-side money
MIN_PRICED_SHARE = 0.80     # swaps with a quote amount, else UNCLEAR


@dataclass
class Extraction:
    token: str
    mode: str = "UNCLEAR"
    swaps: int = 0
    priced_share: float = 0.0
    early_wallets: int = 0
    late_wallets: int = 0
    early_spend: float = 0.0
    late_spend: float = 0.0
    early_net: float = 0.0                    # realised cash out - cash in
    late_net: float = 0.0
    extract_share: float | None = None        # early_net / late_spend
    late_spend_share: float | None = None     # late_spend / all spend
    price_end_vs_cutoff: float | None = None
    last_swap_minute: float | None = None
    notes: list[str] = field(default_factory=list)


def measure(session: Session, *, chain: str, token: str, pools: set[str],
            infra: set[str]) -> Extraction:
    x = Extraction(token=token)
    r = session.execute(text("""
        select pool_key, dex, created_block from token_sample
        where chain = :c and token_address = :t
    """), {"c": chain, "t": token}).first()
    if r is None:
        x.notes.append("not sampled")
        return x
    pool, dex, created = r
    holder = PM if dex == "uniswap-v4" else pool
    hi = created + WINDOW_BLOCKS
    cut = created + CUTOFF_BLOCKS

    swaps = session.execute(text("""
        select tx_hash, block_number, side, token_amount, quote_amount from swap
        where chain = :c and pair_address = :p and block_number between :lo and :hi
        order by block_number, log_index
    """), {"c": chain, "p": pool, "lo": created, "hi": hi}).all()
    x.swaps = len(swaps)
    if not swaps:
        x.mode = "DECAY"
        x.notes.append("no swaps in the window")
        return x
    priced = [s for s in swaps if s[4] and s[3]]
    x.priced_share = len(priced) / len(swaps)
    x.last_swap_minute = (swaps[-1][1] - created) * BLOCK_SECONDS / 60

    # quote per side per tx, from the pool's own events
    tx_quote: dict[tuple[str, str], float] = defaultdict(float)
    for tx, _b, side, _ta, qa in swaps:
        if qa:
            tx_quote[(tx, side)] += float(qa)
    swap_tx = {s[0] for s in swaps}

    tr = session.execute(text("""
        select tx_hash, block_number, from_address, to_address, value_normalised
        from transfer where chain = :c and token_address = :t
          and block_number between :lo and :hi
        order by block_number, log_index
    """), {"c": chain, "t": token, "lo": created, "hi": hi}).all()

    def wallet(a: str) -> bool:
        return bool(a) and a != holder and a not in pools and a not in infra and a != ZERO

    first_in: dict[str, int] = {}
    tokens_net: dict[str, float] = defaultdict(float)
    spent: dict[str, float] = defaultdict(float)
    got: dict[str, float] = defaultdict(float)
    # per tx: who received / sent tokens across a swap
    recv: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    sent: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for tx, blk, fr, to, v in tr:
        a = float(v or 0.0)
        if wallet(to):
            first_in.setdefault(to, blk)
            tokens_net[to] += a
        if wallet(fr):
            tokens_net[fr] -= a
        if tx in swap_tx:
            src_is_market = fr == holder or fr in pools or fr in infra
            dst_is_market = to == holder or to in pools or to in infra
            if src_is_market and wallet(to):
                recv[tx][to] += a
            elif dst_is_market and wallet(fr):
                sent[tx][fr] += a

    for tx, who in recv.items():
        q, tot = tx_quote.get((tx, "buy"), 0.0), sum(who.values())
        for w, a in who.items():
            if tot:
                spent[w] += q * a / tot
    for tx, who in sent.items():
        q, tot = tx_quote.get((tx, "sell"), 0.0), sum(who.values())
        for w, a in who.items():
            if tot:
                got[w] += q * a / tot

    # price at the cutoff and at the end, from the last priced swap of each
    def price_upto(b: int) -> float | None:
        ps = [float(qa) / float(ta) for _tx, blk, _sd, ta, qa in priced if blk <= b]
        return ps[-1] if ps else None
    p_cut, p_end = price_upto(cut), price_upto(hi)
    if p_cut and p_end:
        x.price_end_vs_cutoff = p_end / p_cut

    early = {w for w, b in first_in.items() if b <= cut}
    late = {w for w, b in first_in.items() if b > cut}
    x.early_wallets, x.late_wallets = len(early), len(late)

    def net(ws: set[str]) -> float:
        return sum(got[w] - spent[w] for w in ws)

    x.early_spend = sum(spent[w] for w in early)
    x.late_spend = sum(spent[w] for w in late)
    x.early_net, x.late_net = net(early), net(late)
    total = x.early_spend + x.late_spend
    x.late_spend_share = x.late_spend / total if total else None
    x.extract_share = x.early_net / x.late_spend if x.late_spend else None
    x.mode = classify(x)
    return x


def classify(x: Extraction, *, extract_share: float = EXTRACT_SHARE,
             late_spend_share: float = LATE_SPEND_SHARE) -> str:
    if x.swaps and x.priced_share < MIN_PRICED_SHARE:
        return "UNCLEAR"
    if not x.late_spend or (x.late_spend_share or 0) < late_spend_share:
        return "DECAY"
    if x.late_net < 0 and (x.extract_share or 0) >= extract_share:
        return "EXTRACTED"
    return "DECAY"
