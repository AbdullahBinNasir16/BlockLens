"""The label definition. Every criterion is its own named, testable boolean.

The chain never records "this was a rug pull". It records liquidity moving.
An honest migration and a theft look identical in the raw data, so the label
does not exist until we define it — and the definition is the contribution,
not a detail. Everything here is therefore written to be argued with:
thresholds are named constants, each criterion is a separate function of
measurements only, and the combination is one readable expression.

Nothing in this module makes a network call or touches the database. Give it
a `Series` and it returns a verdict and the measurements behind it, which is
what makes the whole thing testable against hand-checked tokens.

## Where the thresholds came from

They came from the brief, which took them from the literature. They are
*proposals*. `scripts/label_sensitivity.py` sweeps each one and reports how
many tokens change class, and `DECISIONS.md` records the final choice
against that curve. A threshold defended by "it is what we picked" is worth
nothing; a threshold at a flat part of the sensitivity curve is defensible.

## Two deliberate departures from the brief

1. **`DEAD` and `STILL_LIVE` count days on which the price moved, not swaps.**
   A swap count needs a log scan: 1,296 calls per token for 30 days, 14x the
   cost of the entire price series. A pool with no swaps has an unchanged
   tick, so "days the price moved" falls out of samples already taken, for
   free. It measures trading activity, which is what `DEAD` reaches for;
   the swap count was itself only a proxy for that. It is coarser — one swap
   and four hundred look alike — and that is stated in the dataset card.

2. **`LIQUIDITY_PULLED` reads the token side, not the quote side.** On
   Uniswap V4, which is 95% of Base launches, one PoolManager holds every
   pool's quote token, so a per-pool quote reserve does not exist to be
   read. The token side does, exactly (spike B6, verified to the wei). It
   also separates the two cases better: withdrawing liquidity removes both
   sides, so the token reserve collapses, whereas a sell-off *raises* it.
   A quote-side rule cannot tell those apart by sign; this one can.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .sample import Series

# v2 (Phase 5): adds `degenerate_pool`. v1 labelled pools initialised at the
# edge of Uniswap's price range RUG; they are untradeable and are not launches.
RULE_VERSION = "v2-2026-10"

# ---- thresholds, every one of them arguable ------------------------------

# A withdrawal this large in a day is not ordinary trading.
LIQUIDITY_DROP_FRACTION = 0.90
# The window a drop is measured over. Daily sampling is the resolution.
DROP_WINDOW_HOURS = 24
# Below this fraction of peak price, the token has not "dipped".
COLLAPSE_FRACTION = 0.05
# The launch hour is excluded from the peak: at near-zero liquidity the
# price is an artefact, not a level anyone could trade at in size.
PEAK_EXCLUDES_FIRST_HOURS = 1
# Activity, measured in days on which the price moved at all.
DEAD_ACTIVE_DAYS = 2
LIVE_ACTIVE_DAYS = 8
ACTIVITY_WINDOW_DAYS = 30
# Still holding this much of its peak liquidity is the "survived" bar.
LIVE_RESERVE_FRACTION = 0.25
# Below this, the pool never really existed and is excluded, not labelled.
MIN_RESERVE_FLOOR = 0.0
# A verdict needs most of its observations to have landed. Below this the
# answer is "we could not see it", which is UNCLEAR and not a finding. An
# earlier version had no such rule and confidently called a token FAILED on
# 12 of 112 usable samples.
MIN_USABLE_FRACTION = 0.80
# A pool nobody ever traded in is not evidence about rug pulls; it is
# evidence about pool spam. Measured on this chain: 42 of 66 historical
# tokens had zero swaps in their first 24 hours, and 300 of the tokens
# discovery found carry vanity-mined addresses of one spam family. Left in,
# they would dominate every class count and make the base rate a statement
# about a bot rather than about launches.
MIN_SWAPS_IN_WINDOW = 1
# A new pool with comparable liquidity this soon after is a migration.
MIGRATION_WINDOW_DAYS = 7
MIGRATION_LIQUIDITY_FRACTION = 0.25

LABELS = ("RUG", "FAILED", "SURVIVED", "UNCLEAR", "NEVER_LAUNCHED")


@dataclass
class Measurements:
    """Everything the criteria are computed from, kept so a verdict can be
    shown with its evidence rather than asserted."""
    swaps_in_window: int | None = None
    peak_reserve: float | None = None
    peak_reserve_ts: int | None = None
    reserve_at_end: float | None = None
    peak_price: float | None = None
    peak_price_ts: int | None = None
    price_at_end: float | None = None
    largest_drop_fraction: float | None = None
    largest_drop_ts: int | None = None
    largest_drop_from: float | None = None
    largest_drop_to: float | None = None
    active_days_last_30: int | None = None
    points_sampled: int = 0
    points_usable: int = 0
    sibling_pairs_within_window: int = 0
    # filled by the builder from stored transfers, for `degenerate_pool`
    largest_outflow_amount: float | None = None
    extreme_price_seen: bool = False


# A raw (undecimalised) price this far from 1 can only come from a pool
# sitting at the edge of Uniswap's sqrt-price range: MIN_SQRT_RATIO and
# MAX_SQRT_RATIO square to ~2.9e-39 and ~3.4e38. A real launch, even quoted
# in 6-decimal USDC at a millionth of a cent, sits around 1e-21.
EXTREME_PRICE = 1e35
# An outflow larger than everything the pool ever held is not a withdrawal
# of that reserve; it means the reserve measurement is not of this pool.
OUTFLOW_OVER_PEAK = 1.05


@dataclass
class Verdict:
    label: str
    rule_version: str = RULE_VERSION
    liquidity_pulled: bool = False
    sustained_collapse: bool = False
    dead: bool = False
    still_live: bool = False
    possible_migration: bool = False
    never_launched: bool = False
    degenerate_pool: bool = False
    measurements: Measurements = field(default_factory=Measurements)
    notes: list[str] = field(default_factory=list)


# ---- the measurements ----------------------------------------------------

def measure(series: Series, *, launch_ts: int, end_ts: int,
            sibling_pairs: int = 0, swaps_in_window: int | None = None) -> Measurements:
    """Reduce a sampled series to the numbers the criteria need.

    Deliberately separate from the criteria: a threshold change re-runs this
    for free off stored measurements, with no network access at all.
    """
    m = Measurements(points_sampled=len(series.points),
                     points_usable=len(series.ok),
                     sibling_pairs_within_window=sibling_pairs,
                     swaps_in_window=swaps_in_window)
    usable = sorted(series.ok, key=lambda p: p.ts)
    if not usable:
        return m

    peak = max(usable, key=lambda p: p.token_reserve)
    m.peak_reserve = peak.token_reserve
    m.peak_reserve_ts = peak.ts
    m.reserve_at_end = usable[-1].token_reserve

    priced = [p for p in sorted(series.points, key=lambda q: q.ts) if p.price]
    m.extreme_price_seen = any(
        p.price >= EXTREME_PRICE or p.price <= 1.0 / EXTREME_PRICE for p in priced)
    if priced:
        after = launch_ts + PEAK_EXCLUDES_FIRST_HOURS * 3600
        eligible = [p for p in priced if p.ts >= after] or priced
        pk = max(eligible, key=lambda p: p.price)
        m.peak_price = pk.price
        m.peak_price_ts = pk.ts
        m.price_at_end = priced[-1].price

    # The sharpest fall between consecutive observations. With daily
    # sampling a "24h window" is the gap between two samples, which is what
    # makes the resolution of the series part of the definition.
    window = DROP_WINDOW_HOURS * 3600
    worst = 0.0
    for a, b in zip(usable, usable[1:]):
        if b.ts - a.ts > window * 1.5:
            continue              # a gap we cannot call a 24-hour move
        if not a.token_reserve:
            continue
        drop = (a.token_reserve - b.token_reserve) / a.token_reserve
        if drop > worst:
            worst = drop
            m.largest_drop_fraction = drop
            m.largest_drop_ts = b.ts
            m.largest_drop_from = a.token_reserve
            m.largest_drop_to = b.token_reserve
    if m.largest_drop_fraction is None:
        m.largest_drop_fraction = 0.0

    # Activity: days on which the price is different from the day before.
    cutoff = end_ts - ACTIVITY_WINDOW_DAYS * 86400
    recent = [p for p in priced if p.ts >= cutoff]
    moved = 0
    for a, b in zip(recent, recent[1:]):
        if a.price and b.price and a.price != b.price:
            moved += 1
    m.active_days_last_30 = moved if recent else 0
    return m


# ---- the criteria, one function each -------------------------------------

def liquidity_pulled(m: Measurements) -> bool:
    """Token reserve collapsed inside one sampling window.

    The brief also required the outflow to go to the deployer or its funding
    cluster. That attribution needs the transfers of the collapse day and
    a funding cluster that is Phase 3 work, so it is **not** asserted here.
    `build.py` records the largest outflow and its destination as evidence
    alongside the verdict; the criterion itself claims only what it measured.
    """
    return (m.largest_drop_fraction or 0.0) >= LIQUIDITY_DROP_FRACTION


def sustained_collapse(m: Measurements) -> bool:
    if not m.peak_price or m.price_at_end is None:
        return False
    return m.price_at_end <= COLLAPSE_FRACTION * m.peak_price


def dead(m: Measurements) -> bool:
    if m.active_days_last_30 is None:
        return False
    return m.active_days_last_30 < DEAD_ACTIVE_DAYS


def still_live(m: Measurements) -> bool:
    if not m.peak_reserve or m.reserve_at_end is None:
        return False
    holds = m.reserve_at_end >= LIVE_RESERVE_FRACTION * m.peak_reserve
    trading = (m.active_days_last_30 or 0) >= LIVE_ACTIVE_DAYS
    return holds and trading


def never_launched(m: Measurements) -> bool:
    """Never traded, no usable observation, or never any liquidity.

    Excluded from the dataset rather than labelled: a pool that never held
    anything is not evidence about rugs, and leaving it in would flatter
    whichever class it landed in.
    """
    if m.swaps_in_window is not None and m.swaps_in_window < MIN_SWAPS_IN_WINDOW:
        return True
    if m.points_usable == 0:
        return True
    return (m.peak_reserve or 0.0) <= MIN_RESERVE_FLOOR


def insufficient_coverage(m: Measurements) -> bool:
    """Too few observations landed to say anything.

    Not the same as `NEVER_LAUNCHED`: that is a claim about the token, this
    is a claim about our data. Keeping them apart matters, because one
    belongs out of the dataset and the other belongs in it as UNCLEAR.
    """
    if not m.points_sampled:
        return True
    return (m.points_usable / m.points_sampled) < MIN_USABLE_FRACTION


def degenerate_pool(m: Measurements) -> bool:
    """An untradeable pool, not a launch (v2).

    Found by the Phase 5 audit: 8 of Phase 4's 20 RUG positives were one
    deployer's pools initialised at price 2^128, whose largest outflow was
    20x their measured peak reserve. Either sign is enough.
    """
    if m.extreme_price_seen:
        return True
    if m.largest_outflow_amount and m.peak_reserve:
        return m.largest_outflow_amount > OUTFLOW_OVER_PEAK * m.peak_reserve
    return False


def possible_migration(m: Measurements) -> bool:
    """Liquidity leaving a pool is also what a migration looks like.

    Any sibling pair for the same token, created inside the window and with
    comparable liquidity, is enough to withhold a RUG verdict. The count is
    stored so the dataset card can report how many this caught — the first
    thing an examiner will ask about.
    """
    return m.sibling_pairs_within_window > 0


# ---- the combination -----------------------------------------------------

def classify(m: Measurements) -> Verdict:
    """One readable expression, never an opaque function.

    RUG and FAILED stay separate on purpose. A token that collapsed because
    nobody wanted it is not a token whose deployer took the liquidity, and
    collapsing them teaches a model "this went down", which is useless. The
    binary target is RUG versus the rest, and that collapse happens at
    training time, not here.
    """
    v = Verdict(label="UNCLEAR", measurements=m)
    v.never_launched = never_launched(m)
    if v.never_launched:
        v.label = "NEVER_LAUNCHED"
        return v
    v.degenerate_pool = degenerate_pool(m)
    if v.degenerate_pool:
        v.never_launched = True
        v.label = "NEVER_LAUNCHED"
        v.notes.append("degenerate pool: price at the sqrt-price bound, or an "
                       "outflow above the peak reserve - not a launch")
        return v

    if insufficient_coverage(m):
        v.notes.append(
            f"only {m.points_usable}/{m.points_sampled} observations usable "
            f"(<{MIN_USABLE_FRACTION:.0%}): not enough to judge")
        return v        # stays UNCLEAR, criteria left False

    v.liquidity_pulled = liquidity_pulled(m)
    v.sustained_collapse = sustained_collapse(m)
    v.dead = dead(m)
    v.still_live = still_live(m)
    v.possible_migration = possible_migration(m)

    if v.liquidity_pulled and not v.possible_migration:
        v.label = "RUG"
    elif (v.sustained_collapse or v.dead) and not v.liquidity_pulled:
        v.label = "FAILED"
    elif v.still_live:
        v.label = "SURVIVED"
    else:
        v.label = "UNCLEAR"

    if v.liquidity_pulled and v.possible_migration:
        v.notes.append("liquidity left, but a sibling pair appeared: "
                       "withheld from RUG as a possible migration")
    return v


def thresholds() -> dict[str, float | int | str]:
    """Everything a run was decided by, stamped into the report."""
    return {
        "rule_version": RULE_VERSION,
        "liquidity_drop_fraction": LIQUIDITY_DROP_FRACTION,
        "drop_window_hours": DROP_WINDOW_HOURS,
        "collapse_fraction": COLLAPSE_FRACTION,
        "peak_excludes_first_hours": PEAK_EXCLUDES_FIRST_HOURS,
        "dead_active_days": DEAD_ACTIVE_DAYS,
        "live_active_days": LIVE_ACTIVE_DAYS,
        "activity_window_days": ACTIVITY_WINDOW_DAYS,
        "live_reserve_fraction": LIVE_RESERVE_FRACTION,
        "min_reserve_floor": MIN_RESERVE_FLOOR,
        "min_usable_fraction": MIN_USABLE_FRACTION,
        "min_swaps_in_window": MIN_SWAPS_IN_WINDOW,
        "migration_window_days": MIGRATION_WINDOW_DAYS,
        "migration_liquidity_fraction": MIGRATION_LIQUIDITY_FRACTION,
    }
