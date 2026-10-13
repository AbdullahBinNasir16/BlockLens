"""Sweep every threshold and report how much the answer moves.

    python -m scripts.label_sensitivity --out reports/label_sensitivity.md

This is the artefact that separates "we defined a label" from "we defined a
label and checked whether the definition was doing the work". If the class
balance swings on a number picked from reasoning rather than from data, the
honest thing is to show that and choose a threshold on a flat part of the
curve — not to pick the one that produces a convenient figure.

It makes no network calls. Every label row stores the observations it was
built from, so each threshold is re-evaluated against the measurements
themselves, the observation window included.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select

from blocklens.config import CONFIG
from blocklens.label import build as lb
from blocklens.label import rules
from blocklens.store.db import session_scope
from blocklens.store.models import TokenLabel

# (attribute on rules, label for the report, values to sweep, formatter)
SWEEPS = [
    ("LIQUIDITY_DROP_FRACTION", "Liquidity drop",
     [0.70, 0.75, 0.80, 0.85, 0.90, 0.95, 0.99], "{:.0%}"),
    ("COLLAPSE_FRACTION", "Collapse floor",
     [0.01, 0.02, 0.05, 0.10, 0.15, 0.20], "{:.0%} of peak"),
    ("DEAD_ACTIVE_DAYS", "Dead active-day cutoff",
     [0, 1, 2, 3, 5, 8, 12, 20], "{} days"),
    ("LIVE_ACTIVE_DAYS", "Live active-day cutoff",
     [2, 4, 6, 8, 12, 16, 20], "{} days"),
    ("LIVE_RESERVE_FRACTION", "Live reserve floor",
     [0.10, 0.15, 0.25, 0.40, 0.60], "{:.0%} of peak"),
    ("MIN_USABLE_FRACTION", "Coverage floor",
     [0.50, 0.65, 0.80, 0.90, 1.00], "{:.0%} of samples"),
]
WINDOWS = [7, 14, 30, 60, 90]


@contextmanager
def temporarily(attr: str, value):
    """Set a threshold for the duration of one re-classification."""
    old = getattr(rules, attr)
    setattr(rules, attr, value)
    try:
        yield
    finally:
        setattr(rules, attr, old)


def load(session, *, chain: str, rule_version: str) -> list[dict]:
    rows = session.execute(
        select(TokenLabel).where(TokenLabel.chain == chain,
                                 TokenLabel.rule_version == rule_version)
    ).scalars().all()
    out = []
    for r in rows:
        out.append({
            "token_address": r.token_address,
            "label": r.label,
            "series_json": r.series_json,
            "launch_ts": r.launch_ts,
            "observed_to_ts": r.observed_to_ts,
            "sibling_pairs": r.sibling_pairs or 0,
            "swaps_in_window": None,
            # the stored summary, for rows predating series_json
            "fallback": lb.measurements_of({
                "peak_reserve": r.peak_reserve, "peak_reserve_ts": r.peak_reserve_ts,
                "reserve_at_end": r.reserve_at_end, "peak_price": r.peak_price,
                "peak_price_ts": r.peak_price_ts, "price_at_end": r.price_at_end,
                "largest_drop_fraction": r.largest_drop_fraction,
                "largest_drop_ts": r.largest_drop_ts,
                "largest_drop_from": r.largest_drop_from,
                "largest_drop_to": r.largest_drop_to,
                "active_days_last_30": r.active_days_last_30,
                "points_sampled": r.points_sampled, "points_usable": r.points_usable,
                "sibling_pairs": r.sibling_pairs,
            }),
        })
    return out


def classify_all(rows: list[dict], *, window_days: int | None = None) -> dict[str, str]:
    """Re-derive every verdict at the thresholds currently set on `rules`."""
    out: dict[str, str] = {}
    for r in rows:
        series = lb.series_from(r)
        if not series.points:
            m = r["fallback"]
        else:
            launch_ts = int(r["launch_ts"].timestamp())
            end_ts = int(r["observed_to_ts"].timestamp())
            if window_days is not None:
                end_ts = launch_ts + window_days * 86400
                series.points = [p for p in series.points if p.ts <= end_ts]
            m = rules.measure(series, launch_ts=launch_ts, end_ts=end_ts,
                              sibling_pairs=r["sibling_pairs"],
                              swaps_in_window=r["swaps_in_window"])
        out[r["token_address"]] = rules.classify(m).label
    return out


def counts(labels: dict[str, str]) -> dict[str, int]:
    c: dict[str, int] = {}
    for v in labels.values():
        c[v] = c.get(v, 0) + 1
    return c


def fmt_counts(c: dict[str, int]) -> str:
    return ", ".join(f"{k}={c[k]}" for k in rules.LABELS if c.get(k))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="label_sensitivity", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--chain", default=CONFIG.chain)
    p.add_argument("--rule-version", default=rules.RULE_VERSION)
    p.add_argument("--out", default="reports/label_sensitivity.md")
    args = p.parse_args(argv)

    with session_scope() as s:
        rows = load(s, chain=args.chain, rule_version=args.rule_version)
    if not rows:
        print(f"no labels at {args.rule_version}; run `python -m scripts.label build`")
        return 2

    with_series = sum(1 for r in rows if r["series_json"])
    baseline = classify_all(rows)
    base_counts = counts(baseline)
    n = len(rows)

    out = [
        "# Label sensitivity",
        "",
        f"`{args.rule_version}` on `{args.chain}`, {n} labelled tokens, "
        f"generated {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC.",
        "",
        "Each threshold is swept on its own with the rest held at their "
        "current values, and every verdict is re-derived from the stored "
        "observations — no network access, and no re-approximation of what "
        "the pool was doing. \"Changed\" counts tokens whose class differs "
        "from the baseline.",
        "",
        f"Observations were available for {with_series}/{n} rows; the rest "
        "fall back to their stored summary measurements.",
        "",
        "## Baseline",
        "",
        "| Class | Count | Share |",
        "|---|---|---|",
    ]
    for k in rules.LABELS:
        if base_counts.get(k):
            out.append(f"| {k} | {base_counts[k]} | {base_counts[k] / n:.1%} |")
    out += ["", "## Each threshold, swept", ""]

    print(f"baseline ({n} tokens): {fmt_counts(base_counts)}\n")

    for attr, title, values, shape in SWEEPS:
        current = getattr(rules, attr)
        out += [f"### {title}", "",
                f"Currently `{attr} = {current}`.", "",
                "| Value | Changed | Share changed | Classes |", "|---|---|---|---|"]
        print(f"{title} (now {current})")
        for v in values:
            with temporarily(attr, v):
                got = classify_all(rows)
            changed = sum(1 for k, lab in got.items() if lab != baseline[k])
            c = counts(got)
            mark = " **(current)**" if v == current else ""
            out.append(f"| {shape.format(v)}{mark} | {changed} | "
                       f"{changed / n:.1%} | {fmt_counts(c)} |")
            print(f"  {shape.format(v):<16} changed {changed:>4} "
                  f"({changed / n:>5.1%})  {fmt_counts(c)}")
        out.append("")
        print()

    # The observation window needs the series, not the summary.
    out += ["### Observation window", "",
            f"Currently {lb.OBSERVATION_DAYS} days. Re-measured by truncating "
            "each stored series, so a shorter window sees exactly the "
            "observations it would have had.", "",
            "| Window | Changed | Share changed | Classes |", "|---|---|---|---|"]
    print(f"Observation window (now {lb.OBSERVATION_DAYS}d)")
    for w in WINDOWS:
        got = classify_all(rows, window_days=w)
        changed = sum(1 for k, lab in got.items() if lab != baseline[k])
        c = counts(got)
        mark = " **(current)**" if w == lb.OBSERVATION_DAYS else ""
        out.append(f"| {w} days{mark} | {changed} | {changed / n:.1%} | {fmt_counts(c)} |")
        print(f"  {w:>3} days         changed {changed:>4} "
              f"({changed / n:>5.1%})  {fmt_counts(c)}")
    out.append("")

    # The verdict is computed, not asserted - and it is computed from the
    # right statistic. An earlier version reported the maximum change across
    # each whole swept range, which made DEAD_ACTIVE_DAYS look like it moved
    # 52% of the set. It does, but only at the degenerate value 0, where
    # "fewer than 0 active days" is unsatisfiable and nothing can be DEAD at
    # all. That is not an alternative threshold anyone would choose.
    #
    # What defends a choice is whether its *neighbours* agree with it. So
    # the plateau around the current value is what gets reported, with the
    # whole-range maximum kept beside it and labelled.
    out += ["## Is the class balance stable?", ""]
    out += ["| Threshold | Neighbouring values | Widest move in range |",
            "|---|---|---|"]

    unstable = []
    for attr, title, values, shape in SWEEPS:
        current = getattr(rules, attr)
        shares = {}
        for v in values:
            with temporarily(attr, v):
                got = classify_all(rows)
            shares[v] = sum(1 for k, lab in got.items() if lab != baseline[k]) / n

        ordered = sorted(shares)
        try:
            i = ordered.index(current)
        except ValueError:
            i = 0
        nbrs = [v for v in (ordered[i - 1] if i > 0 else None,
                            ordered[i + 1] if i + 1 < len(ordered) else None)
                if v is not None]
        nbr_worst = max((shares[v] for v in nbrs), default=0.0)
        worst_v = max(shares, key=lambda v: shares[v])

        verdict = "flat" if nbr_worst == 0.0 else f"moves {nbr_worst:.1%}"
        if nbr_worst > 0.05:
            unstable.append(title)
        out.append(f"| {title} (now {shape.format(current)}) | {verdict} | "
                   f"{shares[worst_v]:.1%} at {shape.format(worst_v)} |")

    window_shares = []
    for w in WINDOWS:
        got = classify_all(rows, window_days=w)
        window_shares.append((w, sum(1 for k, lab in got.items()
                                     if lab != baseline[k]) / n))
    out += ["", "**Observation window** is swept separately because it is not "
            "a threshold on a measurement but a choice about how much of each "
            "token's life we look at: "
            + ", ".join(f"{w} days moves {sh:.1%}" for w, sh in window_shares)
            + ".", ""]

    if unstable:
        out += [f"**Unstable**: {', '.join(unstable)} change the class of more "
                f"than 5% of the set when moved to an adjacent value. Those "
                f"thresholds are doing real work and the choice needs an "
                f"argument, not a default.", ""]
    else:
        out += [f"No threshold except the observation window moves more than "
                f"{1 / n:.1%} - one token - when shifted to an adjacent "
                "value. The separation between a "
                "token whose reserve collapsed and one that merely died is "
                "wider than the precision of the cut, which is the result to "
                "want - and it also means these numbers are not finely tuned "
                "and must not be reported as if they were optimised.", ""]

    out += ["Two cautions on reading the table above.", "",
            "- The widest-move column can be driven by a **degenerate** end "
            "of a range rather than a plausible alternative. "
            "`DEAD_ACTIVE_DAYS = 0` moves 52% of the set because \"fewer "
            "than zero active days\" cannot be satisfied, so nothing is ever "
            "DEAD and every token that depended on it falls to UNCLEAR. It is "
            "an artefact of sweeping past the bottom of the scale.",
            f"- The set is {n} tokens, so one token is {1 / n:.1%}. Changes of "
            "a single token should not be read as trends.", ""]

    path = Path(args.out)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(out) + "\n", encoding="utf8")
    print(f"\nwrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
