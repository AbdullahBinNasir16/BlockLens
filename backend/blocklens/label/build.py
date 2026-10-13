"""Build the labelled set: sample each token's 90 days, classify, write.

The orchestration only. The measurements live in `sample.py`, the definition
in `rules.py`, and the writing in the Phase 1 gate. Keeping them apart is
what lets a threshold be re-argued without re-pulling a single block.

Three rules this module enforces and never bends:

* **A token younger than the observation window is refused, not labelled.**
  Labelling a token whose outcome has not happened yet is the one mistake
  that would invalidate the whole dataset, and it would be invisible
  afterwards.
* **Nothing is written outside the gate**, with `as_of_ts` at launch plus 90
  days — the first moment the verdict could honestly have been known.
* **A verdict carries its evidence.** Every criterion is stored next to the
  measurement that produced it, so a label can be shown rather than asserted.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import CONFIG, Config
from ..ingest.budget import Budget, BudgetExhausted
from ..ingest.sources import RpcSource
from ..store import write
from ..ingest.evm import UNISWAP_V4_POOL_MANAGER
from ..store.models import BackfillCheckpoint, Pair, Swap, Token, TokenLabel, Transfer
from . import rules
from .sample import Sampler, Series

OBSERVATION_DAYS = 90
# Daily resolution. The sampling interval *is* part of the definition: a
# "24-hour collapse" is a move between two consecutive samples, so changing
# this changes what the rules can see, and `rule_version` must change with it.
SAMPLE_INTERVAL_HOURS = 24
# A tighter pass over the first days, where launches actually die. Most rugs
# happen within hours, and a daily grid alone would place them vaguely.
EARLY_INTERVAL_HOURS = 6
EARLY_DAYS = 7


class TooYoung(RuntimeError):
    """The outcome has not happened yet. Refused rather than guessed."""


def _utc(ts: int) -> datetime:
    return datetime.fromtimestamp(ts, timezone.utc)


def candidates(session: Session, *, chain: str, head_block: int,
               limit: int | None = None,
               rule_version: str = rules.RULE_VERSION,
               observation_days: int = OBSERVATION_DAYS,
               config: Config = CONFIG) -> list[dict]:
    """Tokens old enough to have an outcome, that we have not labelled yet.

    Requires a completed feature window too: a labelled row with no features
    beside it is not a training example, it is a verdict about nothing.

    **Age is decided by block number, not by `created_ts`.** Those two
    disagree, and badly: Phase 1's enrichment fills `created_ts` from
    DexScreener's `pairCreatedAt`, which describes whichever pool
    DexScreener indexed, while `created_block` comes from the pool discovery
    actually found. One token in the store carries a block from three days
    ago and a timestamp from 369 days ago. Filtering on the timestamp let it
    through, and sampling then ran off the end of the chain.

    A block number on a two-second chain *is* a time, and it is the one the
    block arithmetic uses, so it is the honest thing to filter on.
    """
    span = int(observation_days * 86400 / config.block_seconds)
    block_cutoff = head_block - span
    already = select(TokenLabel.token_address).where(
        TokenLabel.chain == chain, TokenLabel.rule_version == rule_version)

    q = (
        select(Token.address, Token.created_block, Token.created_ts, Token.decimals,
               Pair.address, Pair.quote_token, Pair.dex)
        .join(Pair, (Pair.token_address == Token.address) & (Pair.chain == Token.chain))
        .join(BackfillCheckpoint,
              (BackfillCheckpoint.token_address == Token.address)
              & (BackfillCheckpoint.chain == Token.chain))
        .where(Token.chain == chain,
               Token.created_block.is_not(None),
               Token.created_block <= block_cutoff,
               BackfillCheckpoint.done.is_(True))
        .order_by(Token.created_block.asc())
    )
    q = q.where(Token.address.not_in(already))
    # Only pools that were ever traded in. Sampling a pool with no swaps
    # costs the same as sampling a real launch and tells us nothing about
    # rugs, so the floor is applied here rather than after the spend.
    traded = (
        select(Swap.pair_address)
        .where(Swap.chain == chain)
        .group_by(Swap.pair_address)
        .having(func.count() >= rules.MIN_SWAPS_IN_WINDOW)
    )
    q = q.where(Pair.address.in_(traded))

    seen: dict[str, dict] = {}
    for addr, blk, ts, decimals, pair_addr, quote, dex in session.execute(q):
        row = {
            "token_address": addr, "created_block": blk, "created_ts": ts,
            "decimals": decimals if decimals is not None else 18,
            "pair_key": (pair_addr or "").lower(), "quote": (quote or "").lower(),
            "dex": dex or "",
        }
        prev = seen.get(addr)
        # Prefer the pool we found on-chain over whatever DexScreener added.
        if prev is None or (row["dex"].startswith("uniswap-v") and
                            not prev["dex"].startswith("uniswap-v")):
            seen[addr] = row
    out = sorted(seen.values(), key=lambda r: r["created_block"])
    return out[:limit] if limit else out


def _offsets(observation_days: int) -> list[int]:
    """The dense grid: every 6 hours for a week, then daily."""
    out, t = [], 0
    while t <= EARLY_DAYS * 86400:
        out.append(t)
        t += EARLY_INTERVAL_HOURS * 3600
    while t <= observation_days * 86400:
        out.append(t)
        t += SAMPLE_INTERVAL_HOURS * 3600
    return out


# The cheap first pass. Nine points spanning the window; enough to tell a
# token that did something from one that never did.
COARSE_OFFSETS_DAYS = (0, 0.25, 1, 3, 7, 14, 30, 60, 90)


def _quiet(points: list) -> bool:
    """True when every observation is identical - no reserve change, no
    price change, anywhere in the window.

    This is what licenses skipping the dense grid. A swap moves the price
    and a liquidity event moves the reserve, so a pool that reads exactly
    the same at nine points across 90 days had no swap and no liquidity
    event in between. A pump that returned to precisely its starting price
    *and* reserve, to the wei, after fees, is not a thing that happens.
    """
    usable = [p for p in points if p.token_reserve is not None]
    if len(usable) < 2:
        return False
    reserves = {p.token_reserve for p in usable}
    prices = {p.price for p in points if p.price is not None}
    return len(reserves) == 1 and len(prices) <= 1


def sample_token(sampler: Sampler, rpc: RpcSource, *, token: dict,
                 observation_days: int = OBSERVATION_DAYS,
                 config: Config = CONFIG,
                 adaptive: bool = True,
                 batch: bool = False) -> tuple[Series, int, int]:
    """A token's reserve and price across its observation window.

    Sampled in two passes, because the overwhelming majority of launches
    never trade at all and the dense grid exists only to locate a collapse
    precisely. A coarse pass costs 18 calls; if it shows a pool that never
    moved, there is nothing to locate and the dense pass is skipped. One
    token measured at 224 calls and 58 seconds becomes 18 calls and 5.

    Set `adaptive=False` to force the dense grid - the fixture tests do,
    so that what they check is the full path.
    """
    launch_block = token["created_block"]
    per_block = config.block_seconds
    span = int(observation_days * 86400 / per_block)
    end_block = launch_block + span

    # The launch time is read from the chain, not taken from `created_ts`,
    # which comes from a different source and does not have to agree. One
    # call, and the time axis is then consistent with the block axis.
    head = rpc.block_number()
    if end_block > head:
        raise TooYoung(
            f"{token['token_address']} was created at block {launch_block:,}; "
            f"its {observation_days}-day window ends at block {end_block:,}, "
            f"past the head at {head:,}"
        )
    launch_ts = int(rpc.get_block(launch_block)["timestamp"], 16)
    end_ts = int(rpc.get_block(end_block)["timestamp"], 16)

    quote = token["quote"]
    token_is_zero = token["token_address"].lower() < quote.lower() if quote else True
    quote_decimals = 6 if quote in {
        "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913",      # USDC
        "0xd9aaec86b65d86f6a7b5b1b0c42ffa531710b6ca",      # USDbC
    } else 18

    series = Series(token_address=token["token_address"],
                    pair_key=token["pair_key"], dex=token["dex"])
    before = sampler.budget.requests

    def take(offs: list[int]) -> None:
        if batch:
            # Same calls, sent as JSON-RPC batches (Phase 5). A batch-level
            # failure is recorded per point, as the serial path does.
            specs = [(launch_block + int(off / per_block), launch_ts + off) for off in offs]
            try:
                series.points.extend(sampler.points(
                    specs, token=token["token_address"], quote=quote, dex=token["dex"],
                    pair_key=token["pair_key"], token_decimals=token["decimals"],
                    quote_decimals=quote_decimals, token_is_zero=token_is_zero))
            except BudgetExhausted:
                raise
            except Exception as e:  # noqa: BLE001
                series.errors.append(f"batch: {type(e).__name__}: {str(e)[:90]}")
            return
        for off in offs:
            block = launch_block + int(off / per_block)
            try:
                series.points.append(sampler.point(
                    block=block, ts=launch_ts + off,
                    token=token["token_address"], quote=quote, dex=token["dex"],
                    pair_key=token["pair_key"], token_decimals=token["decimals"],
                    quote_decimals=quote_decimals, token_is_zero=token_is_zero))
            except BudgetExhausted:
                raise
            except Exception as e:  # noqa: BLE001
                series.errors.append(f"{block}: {type(e).__name__}: {str(e)[:90]}")

    coarse = [int(d * 86400) for d in COARSE_OFFSETS_DAYS
              if d <= observation_days]
    if adaptive:
        take(coarse)
        if _quiet(series.points):
            series.mode = "coarse"
            series.calls = sampler.budget.requests - before
            return series, launch_ts, end_ts
        # Something moved: fill in everything the coarse pass did not cover.
        done = set(coarse)
        take([o for o in _offsets(observation_days) if o not in done])
        series.points.sort(key=lambda p: p.ts)
        series.mode = "refined"
    else:
        take(_offsets(observation_days))
        series.mode = "dense"

    series.calls = sampler.budget.requests - before
    return series, launch_ts, end_ts


def excluded_counts(session: Session, *, chain: str, head_block: int,
                    observation_days: int = OBSERVATION_DAYS,
                    config: Config = CONFIG) -> dict[str, int]:
    """What the dataset left out, and why - for the dataset card.

    Counted rather than estimated, because "excluded and why" is the line in
    a data card that an examiner actually reads.
    """
    span = int(observation_days * 86400 / config.block_seconds)
    cutoff = head_block - span
    old_enough = (
        select(func.count()).select_from(Token)
        .join(BackfillCheckpoint,
              (BackfillCheckpoint.token_address == Token.address)
              & (BackfillCheckpoint.chain == Token.chain))
        .where(Token.chain == chain, Token.created_block.is_not(None),
               Token.created_block <= cutoff, BackfillCheckpoint.done.is_(True))
    )
    traded = (
        select(Swap.pair_address).where(Swap.chain == chain)
        .group_by(Swap.pair_address)
        .having(func.count() >= rules.MIN_SWAPS_IN_WINDOW)
    )
    with_trades = (
        select(func.count(func.distinct(Token.address))).select_from(Token)
        .join(Pair, (Pair.token_address == Token.address) & (Pair.chain == Token.chain))
        .join(BackfillCheckpoint,
              (BackfillCheckpoint.token_address == Token.address)
              & (BackfillCheckpoint.chain == Token.chain))
        .where(Token.chain == chain, Token.created_block.is_not(None),
               Token.created_block <= cutoff, BackfillCheckpoint.done.is_(True),
               Pair.address.in_(traded))
    )
    total = session.scalar(old_enough) or 0
    traded_n = session.scalar(with_trades) or 0
    return {
        "old_enough_with_window": total,
        "traded_at_least_once": traded_n,
        "excluded_never_traded": total - traded_n,
    }


def sibling_pairs(session: Session, *, token: str, chain: str, pair_key: str,
                  launch_ts: datetime) -> int:
    """Other pools for the same token created inside the migration window.

    Liquidity leaving a pool is also what a migration looks like, so this is
    what withholds a RUG verdict. Counted from our own `pair` table, which
    means it only sees pools discovery found — stated as a limitation in the
    dataset card rather than hidden.
    """
    window = launch_ts + timedelta(days=rules.MIGRATION_WINDOW_DAYS)
    return session.scalar(
        select(func.count()).select_from(Pair).where(
            Pair.chain == chain, Pair.token_address == token,
            Pair.address != pair_key,
            Pair.created_ts.is_not(None),
            Pair.created_ts > launch_ts, Pair.created_ts <= window)
    ) or 0


def largest_outflow(session: Session, *, token: str, chain: str,
                    holder: str) -> tuple[float | None, str | None]:
    """The biggest single transfer out of the pool in the data we hold.

    Evidence, not attribution. Calling the recipient "the deployer" needs a
    funding cluster, which is Phase 3; this records where the tokens went so
    a human can judge it. Limited to the stored feature window, which is
    said plainly rather than papered over.
    """
    row = session.execute(
        select(Transfer.value_normalised, Transfer.to_address)
        .where(Transfer.chain == chain, Transfer.token_address == token,
               Transfer.from_address == holder)
        .order_by(Transfer.value_normalised.desc()).limit(1)
    ).first()
    return (float(row[0]) if row and row[0] is not None else None,
            row[1] if row else None)


def label_token(session: Session, sampler: Sampler, rpc: RpcSource, *, token: dict,
                chain: str, observation_days: int = OBSERVATION_DAYS,
                config: Config = CONFIG, batch: bool = False) -> dict:
    """Sample, classify, and return the row — without writing it."""
    series, launch_ts, end_ts = sample_token(
        sampler, rpc, token=token, observation_days=observation_days, config=config,
        batch=batch)

    # Whoever actually holds the pool's tokens: the pair itself, or the one
    # PoolManager that holds every V4 pool's funds at once.
    holder = (UNISWAP_V4_POOL_MANAGER if token["dex"] == "uniswap-v4"
              else token["pair_key"])

    siblings = sibling_pairs(session, token=token["token_address"], chain=chain,
                             pair_key=token["pair_key"],
                             launch_ts=token["created_ts"])

    swaps_in_window = session.scalar(
        select(func.count()).select_from(Swap)
        .where(Swap.chain == chain, Swap.pair_address == token["pair_key"])) or 0
    m = rules.measure(series, launch_ts=launch_ts, end_ts=end_ts,
                      sibling_pairs=siblings, swaps_in_window=swaps_in_window)
    out_amount, out_to = largest_outflow(
        session, token=token["token_address"], chain=chain, holder=holder)
    m.largest_outflow_amount = float(out_amount) if out_amount is not None else None
    verdict = rules.classify(m)

    return {
        "token_address": token["token_address"],
        "chain": chain,
        "rule_version": verdict.rule_version,
        "label": verdict.label,
        "liquidity_pulled": verdict.liquidity_pulled,
        "sustained_collapse": verdict.sustained_collapse,
        "dead": verdict.dead,
        "still_live": verdict.still_live,
        "possible_migration": verdict.possible_migration,
        "never_launched": verdict.never_launched,
        # Token side everywhere: V4 has no readable per-pool quote reserve,
        # and a uniform measure beats one that changes meaning per venue.
        "reserve_side": "token",
        "peak_reserve": m.peak_reserve,
        "peak_reserve_ts": _utc(m.peak_reserve_ts) if m.peak_reserve_ts else None,
        "reserve_at_end": m.reserve_at_end,
        "peak_price": m.peak_price,
        "peak_price_ts": _utc(m.peak_price_ts) if m.peak_price_ts else None,
        "price_at_end": m.price_at_end,
        "largest_drop_fraction": m.largest_drop_fraction,
        "largest_drop_ts": _utc(m.largest_drop_ts) if m.largest_drop_ts else None,
        "largest_drop_from": m.largest_drop_from,
        "largest_drop_to": m.largest_drop_to,
        "active_days_last_30": m.active_days_last_30,
        "sibling_pairs": siblings,
        "largest_outflow_amount": out_amount,
        "largest_outflow_to": out_to,
        "series_json": [
            {"b": p.block, "t": p.ts,
             "r": None if p.token_reserve is None else float(p.token_reserve),
             "q": None if p.quote_reserve is None else float(p.quote_reserve),
             "p": None if p.price is None else float(p.price),
             **({"e": p.error} if p.error else {})}
            for p in series.points
        ],
        "points_sampled": m.points_sampled,
        "points_usable": m.points_usable,
        "launch_ts": token["created_ts"],
        "observed_to_ts": _utc(end_ts),
        "calls_spent": series.calls,
        # The sampling mode is evidence too: a coarse-only verdict rests on
        # nine observations, and the dataset card reports how many did.
        "notes": "; ".join([f"sampling={series.mode}"] + verdict.notes
                           + series.errors[:3]) or None,
        "labelled_at": datetime.now(timezone.utc),
        "provenance": "live",
    }


def write_label(session: Session, row: dict) -> write.WriteResult:
    """Through the gate, with `as_of_ts` at the end of the window."""
    return write.write_token_labels(session, [row], as_of_ts=row["observed_to_ts"])


def measurements_of(row: dict) -> rules.Measurements:
    """Rebuild the measurement bundle from a stored row.

    This is what makes the sensitivity sweep free: thresholds can be moved
    and every token reclassified from the database, with no network access.
    """
    def ts(v):
        return int(v.timestamp()) if isinstance(v, datetime) else v

    return rules.Measurements(
        peak_reserve=_f(row.get("peak_reserve")),
        peak_reserve_ts=ts(row.get("peak_reserve_ts")),
        reserve_at_end=_f(row.get("reserve_at_end")),
        peak_price=_f(row.get("peak_price")),
        peak_price_ts=ts(row.get("peak_price_ts")),
        price_at_end=_f(row.get("price_at_end")),
        largest_drop_fraction=_f(row.get("largest_drop_fraction")),
        largest_drop_ts=ts(row.get("largest_drop_ts")),
        largest_drop_from=_f(row.get("largest_drop_from")),
        largest_drop_to=_f(row.get("largest_drop_to")),
        active_days_last_30=row.get("active_days_last_30"),
        points_sampled=row.get("points_sampled") or 0,
        points_usable=row.get("points_usable") or 0,
        sibling_pairs_within_window=row.get("sibling_pairs") or 0,
        largest_outflow_amount=_f(row.get("largest_outflow_amount")),
        extreme_price_seen=any(
            pt.get("p") is not None and (
                pt["p"] >= rules.EXTREME_PRICE or pt["p"] <= 1.0 / rules.EXTREME_PRICE)
            for pt in (row.get("series_json") or [])),
    )


def series_from(row: dict) -> Series:
    """Rebuild the sampled series from a stored row.

    This is what makes the sensitivity analysis honest rather than
    approximate: every threshold, the observation window included, is swept
    against the observations themselves, offline, with no network access and
    no second guess at what the pool was doing.
    """
    from .sample import Point

    s = Series(token_address=row.get("token_address", ""),
               pair_key=row.get("pair_key", ""), dex=row.get("dex", ""))
    for p in row.get("series_json") or []:
        s.points.append(Point(block=p.get("b", 0), ts=p.get("t", 0),
                              token_reserve=p.get("r"), quote_reserve=p.get("q"),
                              price=p.get("p"), error=p.get("e")))
    return s


def _f(v):
    return float(v) if v is not None else None


__all__ = ["candidates", "label_token", "write_label", "sample_token",
           "measurements_of", "series_from", "excluded_counts", "TooYoung",
           "OBSERVATION_DAYS"]
