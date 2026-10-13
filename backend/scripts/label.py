"""Build the labelled set.

    python -m scripts.label build --limit 200
    python -m scripts.label status
    python -m scripts.label show --token 0x...
    python -m scripts.label sample --label RUG -n 10

Every row goes through the Phase 1 write gate with `as_of_ts` at launch plus
the observation window, which is the first moment the verdict could honestly
have been known.
"""
from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime, timezone

from sqlalchemy import func, select

from blocklens.config import CONFIG
from blocklens.ingest.budget import BudgetExhausted
from blocklens.ingest.runner import run_scope
from blocklens.ingest.sources import RpcSource
from blocklens.label import build as lb
from blocklens.label import rules
from blocklens.label.sample import Sampler
from blocklens.store.db import database_available, session_scope
from blocklens.store.models import TokenLabel


def _die(msg: str) -> None:
    print(f"error: {msg}", file=sys.stderr)
    raise SystemExit(2)


def cmd_build(args: argparse.Namespace) -> int:
    with run_scope(source="label", scope=f"{rules.RULE_VERSION} limit={args.limit}",
                   chain=args.chain, max_calls=args.max_calls) as ctx:
        rpc = RpcSource(ctx.budget)
        sampler = Sampler(rpc, ctx.budget)
        head = rpc.block_number()

        todo = lb.candidates(ctx.session, chain=args.chain, head_block=head,
                             limit=args.limit,
                             rule_version=rules.RULE_VERSION,
                             observation_days=args.days)
        counts = lb.excluded_counts(ctx.session, chain=args.chain, head_block=head,
                                    observation_days=args.days)
        print(f"rule_version {rules.RULE_VERSION}, observation window {args.days}d")
        print(f"old enough with a feature window: {counts['old_enough_with_window']}")
        print(f"  traded at least once:           {counts['traded_at_least_once']}")
        print(f"  excluded, never traded:         {counts['excluded_never_traded']}")
        print(f"to label now: {len(todo)}\n")

        tally: dict[str, int] = {}
        failed, too_young = 0, 0
        for i, tok in enumerate(todo, 1):
            t0 = time.time()
            try:
                row = lb.label_token(ctx.session, sampler, rpc, token=tok,
                                     chain=args.chain, observation_days=args.days)
            except lb.TooYoung as e:
                too_young += 1
                print(f"[{i}/{len(todo)}] {tok['token_address'][:14]} REFUSED: {e}")
                continue
            except BudgetExhausted as e:
                print(f"stopping: {e}")
                break
            except Exception as e:  # noqa: BLE001
                ctx.session.rollback()
                failed += 1
                print(f"[{i}/{len(todo)}] {tok['token_address'][:14]} FAILED: "
                      f"{type(e).__name__}: {str(e)[:110]}")
                continue

            res = lb.write_label(ctx.session, row)
            ctx.session.commit()
            ctx.add_rows(res.total)
            tally[row["label"]] = tally.get(row["label"], 0) + 1
            print(f"[{i}/{len(todo)}] {row['token_address'][:14]} "
                  f"{row['label']:<14} pts={row['points_usable']:>3}/"
                  f"{row['points_sampled']:<3} {row['calls_spent']:>3} calls "
                  f"{time.time() - t0:>5.1f}s  {row['notes'] or ''}")

        rpc.close()
        print()
        for k in sorted(tally, key=lambda x: -tally[x]):
            print(f"  {k:<16} {tally[k]}")
        if too_young:
            print(f"  refused as too young: {too_young}")
        if failed:
            print(f"  failed: {failed}")
        print(f"calls: {ctx.budget.requests}, waited "
              f"{ctx.budget.waited_seconds:.1f}s on rate limits")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    if not database_available():
        _die(f"no database at {CONFIG.database_url}")
    with session_scope() as s:
        versions = s.execute(
            select(TokenLabel.rule_version, func.count())
            .where(TokenLabel.chain == args.chain)
            .group_by(TokenLabel.rule_version).order_by(TokenLabel.rule_version)
        ).all()
        if not versions:
            print("no labels yet")
            return 0
        for version, n in versions:
            print(f"\nrule_version {version}  ({n} rows)")
            rows = s.execute(
                select(TokenLabel.label, func.count())
                .where(TokenLabel.chain == args.chain,
                       TokenLabel.rule_version == version)
                .group_by(TokenLabel.label).order_by(func.count().desc())
            ).all()
            total = sum(n_ for _, n_ in rows)
            for label, n_ in rows:
                print(f"  {label:<16} {n_:>5}  {n_ / total:>6.1%}")
            rug = dict(rows).get("RUG", 0)
            inset = total - dict(rows).get("NEVER_LAUNCHED", 0)
            if inset:
                print(f"  base rate (RUG of labelled): {rug / inset:.1%}")
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    with session_scope() as s:
        row = s.execute(
            select(TokenLabel).where(
                TokenLabel.chain == args.chain,
                TokenLabel.token_address == args.token.lower(),
                TokenLabel.rule_version == args.rule_version)
        ).scalars().first()
        if row is None:
            _die(f"no label for {args.token} at {args.rule_version}")
        _print_row(row)
    return 0


def _print_row(row) -> None:
    def f(v, nd=6):
        return "None" if v is None else f"{float(v):,.{nd}f}"

    print(f"token            {row.token_address}")
    print(f"label            {row.label}   ({row.rule_version})")
    print(f"launched         {row.launch_ts:%Y-%m-%d %H:%M} UTC")
    print(f"observed to      {row.observed_to_ts:%Y-%m-%d %H:%M} UTC")
    print(f"criteria         pulled={row.liquidity_pulled} "
          f"collapse={row.sustained_collapse} dead={row.dead} "
          f"live={row.still_live} migration={row.possible_migration}")
    print(f"reserve ({row.reserve_side})  peak {f(row.peak_reserve, 2)} "
          f"-> end {f(row.reserve_at_end, 2)}")
    print(f"largest drop     {f(row.largest_drop_fraction, 4)} "
          f"({f(row.largest_drop_from, 2)} -> {f(row.largest_drop_to, 2)})"
          + (f" at {row.largest_drop_ts:%Y-%m-%d %H:%M}" if row.largest_drop_ts else ""))
    print(f"price            peak {row.peak_price} -> end {row.price_at_end}")
    print(f"activity         {row.active_days_last_30} active days in last 30; "
          f"sibling pairs {row.sibling_pairs}")
    print(f"largest outflow  {f(row.largest_outflow_amount, 2)} "
          f"-> {row.largest_outflow_to}")
    print(f"observations     {row.points_usable}/{row.points_sampled}  "
          f"({row.calls_spent} calls)")
    print(f"notes            {row.notes or '-'}")


def cmd_sample(args: argparse.Namespace) -> int:
    """Random rows of one class, with their evidence.

    Random on purpose: the acceptance criterion is to spot check rows the
    author did not choose, and picking the clearest ten would defeat it.
    """
    with session_scope() as s:
        rows = s.execute(
            select(TokenLabel)
            .where(TokenLabel.chain == args.chain,
                   TokenLabel.rule_version == args.rule_version,
                   TokenLabel.label == args.label)
            .order_by(func.random()).limit(args.n)
        ).scalars().all()
        if not rows:
            print(f"no {args.label} rows at {args.rule_version}")
            return 0
        print(f"{len(rows)} random {args.label} rows "
              f"(seeded by the database, not chosen)\n")
        for i, row in enumerate(rows, 1):
            print(f"--- {i} " + "-" * 60)
            _print_row(row)
            print()
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="label", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--chain", default=CONFIG.chain)
    p.add_argument("--rule-version", default=rules.RULE_VERSION)
    sub = p.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("build", help="label every eligible token")
    b.add_argument("--limit", type=int, default=None)
    b.add_argument("--days", type=int, default=lb.OBSERVATION_DAYS)
    b.add_argument("--max-calls", type=int, default=None)
    b.set_defaults(func=cmd_build)

    st = sub.add_parser("status", help="class counts and the base rate")
    st.set_defaults(func=cmd_status)

    sh = sub.add_parser("show", help="one token's verdict and evidence")
    sh.add_argument("--token", required=True)
    sh.set_defaults(func=cmd_show)

    sa = sub.add_parser("sample", help="random rows of one class, with evidence")
    sa.add_argument("--label", default="RUG", choices=rules.LABELS)
    sa.add_argument("-n", type=int, default=10)
    sa.set_defaults(func=cmd_sample)

    try:
        sys.stdout.reconfigure(line_buffering=True)
    except (AttributeError, ValueError):
        pass
    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
