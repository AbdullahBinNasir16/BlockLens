# Label sensitivity

`v1-2026-10` on `base`, 46 labelled tokens, generated 2026-10-13 10:20 UTC.

Each threshold is swept on its own with the rest held at their current values, and every verdict is re-derived from the stored observations — no network access, and no re-approximation of what the pool was doing. "Changed" counts tokens whose class differs from the baseline.

Observations were available for 46/46 rows; the rest fall back to their stored summary measurements.

## Baseline

| Class | Count | Share |
|---|---|---|
| RUG | 20 | 43.5% |
| FAILED | 24 | 52.2% |
| UNCLEAR | 1 | 2.2% |
| NEVER_LAUNCHED | 1 | 2.2% |

## Each threshold, swept

### Liquidity drop

Currently `LIQUIDITY_DROP_FRACTION = 0.9`.

| Value | Changed | Share changed | Classes |
|---|---|---|---|
| 70% | 1 | 2.2% | RUG=21, FAILED=23, UNCLEAR=1, NEVER_LAUNCHED=1 |
| 75% | 1 | 2.2% | RUG=21, FAILED=23, UNCLEAR=1, NEVER_LAUNCHED=1 |
| 80% | 0 | 0.0% | RUG=20, FAILED=24, UNCLEAR=1, NEVER_LAUNCHED=1 |
| 85% | 0 | 0.0% | RUG=20, FAILED=24, UNCLEAR=1, NEVER_LAUNCHED=1 |
| 90% **(current)** | 0 | 0.0% | RUG=20, FAILED=24, UNCLEAR=1, NEVER_LAUNCHED=1 |
| 95% | 0 | 0.0% | RUG=20, FAILED=24, UNCLEAR=1, NEVER_LAUNCHED=1 |
| 99% | 0 | 0.0% | RUG=20, FAILED=24, UNCLEAR=1, NEVER_LAUNCHED=1 |

### Collapse floor

Currently `COLLAPSE_FRACTION = 0.05`.

| Value | Changed | Share changed | Classes |
|---|---|---|---|
| 1% of peak | 0 | 0.0% | RUG=20, FAILED=24, UNCLEAR=1, NEVER_LAUNCHED=1 |
| 2% of peak | 0 | 0.0% | RUG=20, FAILED=24, UNCLEAR=1, NEVER_LAUNCHED=1 |
| 5% of peak **(current)** | 0 | 0.0% | RUG=20, FAILED=24, UNCLEAR=1, NEVER_LAUNCHED=1 |
| 10% of peak | 0 | 0.0% | RUG=20, FAILED=24, UNCLEAR=1, NEVER_LAUNCHED=1 |
| 15% of peak | 0 | 0.0% | RUG=20, FAILED=24, UNCLEAR=1, NEVER_LAUNCHED=1 |
| 20% of peak | 0 | 0.0% | RUG=20, FAILED=24, UNCLEAR=1, NEVER_LAUNCHED=1 |

### Dead active-day cutoff

Currently `DEAD_ACTIVE_DAYS = 2`.

| Value | Changed | Share changed | Classes |
|---|---|---|---|
| 0 days | 24 | 52.2% | RUG=20, UNCLEAR=25, NEVER_LAUNCHED=1 |
| 1 days | 0 | 0.0% | RUG=20, FAILED=24, UNCLEAR=1, NEVER_LAUNCHED=1 |
| 2 days **(current)** | 0 | 0.0% | RUG=20, FAILED=24, UNCLEAR=1, NEVER_LAUNCHED=1 |
| 3 days | 0 | 0.0% | RUG=20, FAILED=24, UNCLEAR=1, NEVER_LAUNCHED=1 |
| 5 days | 0 | 0.0% | RUG=20, FAILED=24, UNCLEAR=1, NEVER_LAUNCHED=1 |
| 8 days | 1 | 2.2% | RUG=20, FAILED=25, NEVER_LAUNCHED=1 |
| 12 days | 1 | 2.2% | RUG=20, FAILED=25, NEVER_LAUNCHED=1 |
| 20 days | 1 | 2.2% | RUG=20, FAILED=25, NEVER_LAUNCHED=1 |

### Live active-day cutoff

Currently `LIVE_ACTIVE_DAYS = 8`.

| Value | Changed | Share changed | Classes |
|---|---|---|---|
| 2 days | 1 | 2.2% | RUG=20, FAILED=24, SURVIVED=1, NEVER_LAUNCHED=1 |
| 4 days | 1 | 2.2% | RUG=20, FAILED=24, SURVIVED=1, NEVER_LAUNCHED=1 |
| 6 days | 1 | 2.2% | RUG=20, FAILED=24, SURVIVED=1, NEVER_LAUNCHED=1 |
| 8 days **(current)** | 0 | 0.0% | RUG=20, FAILED=24, UNCLEAR=1, NEVER_LAUNCHED=1 |
| 12 days | 0 | 0.0% | RUG=20, FAILED=24, UNCLEAR=1, NEVER_LAUNCHED=1 |
| 16 days | 0 | 0.0% | RUG=20, FAILED=24, UNCLEAR=1, NEVER_LAUNCHED=1 |
| 20 days | 0 | 0.0% | RUG=20, FAILED=24, UNCLEAR=1, NEVER_LAUNCHED=1 |

### Live reserve floor

Currently `LIVE_RESERVE_FRACTION = 0.25`.

| Value | Changed | Share changed | Classes |
|---|---|---|---|
| 10% of peak | 0 | 0.0% | RUG=20, FAILED=24, UNCLEAR=1, NEVER_LAUNCHED=1 |
| 15% of peak | 0 | 0.0% | RUG=20, FAILED=24, UNCLEAR=1, NEVER_LAUNCHED=1 |
| 25% of peak **(current)** | 0 | 0.0% | RUG=20, FAILED=24, UNCLEAR=1, NEVER_LAUNCHED=1 |
| 40% of peak | 0 | 0.0% | RUG=20, FAILED=24, UNCLEAR=1, NEVER_LAUNCHED=1 |
| 60% of peak | 0 | 0.0% | RUG=20, FAILED=24, UNCLEAR=1, NEVER_LAUNCHED=1 |

### Coverage floor

Currently `MIN_USABLE_FRACTION = 0.8`.

| Value | Changed | Share changed | Classes |
|---|---|---|---|
| 50% of samples | 0 | 0.0% | RUG=20, FAILED=24, UNCLEAR=1, NEVER_LAUNCHED=1 |
| 65% of samples | 0 | 0.0% | RUG=20, FAILED=24, UNCLEAR=1, NEVER_LAUNCHED=1 |
| 80% of samples **(current)** | 0 | 0.0% | RUG=20, FAILED=24, UNCLEAR=1, NEVER_LAUNCHED=1 |
| 90% of samples | 0 | 0.0% | RUG=20, FAILED=24, UNCLEAR=1, NEVER_LAUNCHED=1 |
| 100% of samples | 1 | 2.2% | RUG=19, FAILED=24, UNCLEAR=2, NEVER_LAUNCHED=1 |

### Observation window

Currently 90 days. Re-measured by truncating each stored series, so a shorter window sees exactly the observations it would have had.

| Window | Changed | Share changed | Classes |
|---|---|---|---|
| 7 days | 5 | 10.9% | RUG=20, FAILED=20, SURVIVED=1, UNCLEAR=4, NEVER_LAUNCHED=1 |
| 14 days | 5 | 10.9% | RUG=20, FAILED=20, SURVIVED=1, UNCLEAR=4, NEVER_LAUNCHED=1 |
| 30 days | 5 | 10.9% | RUG=20, FAILED=20, SURVIVED=1, UNCLEAR=4, NEVER_LAUNCHED=1 |
| 60 days | 1 | 2.2% | RUG=20, FAILED=24, SURVIVED=1, NEVER_LAUNCHED=1 |
| 90 days **(current)** | 0 | 0.0% | RUG=20, FAILED=24, UNCLEAR=1, NEVER_LAUNCHED=1 |

## Is the class balance stable?

| Threshold | Neighbouring values | Widest move in range |
|---|---|---|
| Liquidity drop (now 90%) | flat | 2.2% at 70% |
| Collapse floor (now 5% of peak) | flat | 0.0% at 1% of peak |
| Dead active-day cutoff (now 2 days) | flat | 52.2% at 0 days |
| Live active-day cutoff (now 8 days) | moves 2.2% | 2.2% at 2 days |
| Live reserve floor (now 25% of peak) | flat | 0.0% at 10% of peak |
| Coverage floor (now 80% of samples) | flat | 2.2% at 100% of samples |

**Observation window** is swept separately because it is not a threshold on a measurement but a choice about how much of each token's life we look at: 7 days moves 10.9%, 14 days moves 10.9%, 30 days moves 10.9%, 60 days moves 2.2%, 90 days moves 0.0%.

No threshold except the observation window moves more than 2.2% - one token - when shifted to an adjacent value. The separation between a token whose reserve collapsed and one that merely died is wider than the precision of the cut, which is the result to want - and it also means these numbers are not finely tuned and must not be reported as if they were optimised.

Two cautions on reading the table above.

- The widest-move column can be driven by a **degenerate** end of a range rather than a plausible alternative. `DEAD_ACTIVE_DAYS = 0` moves 52% of the set because "fewer than zero active days" cannot be satisfied, so nothing is ever DEAD and every token that depended on it falls to UNCLEAR. It is an artefact of sweeping past the bottom of the scale.
- The set is 46 tokens, so one token is 2.2%. Changes of a single token should not be read as trends.

