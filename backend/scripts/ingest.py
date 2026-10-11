"""The operator's interface. Four verbs, no surprises.

    python -m scripts.ingest discover --chain base --limit 100
    python -m scripts.ingest backfill --token 0x...
    python -m scripts.ingest backfill --all-pending --max-cu 2000000
    python -m scripts.ingest status

Nothing here writes a row directly; every path goes through the write gate,
and every network call goes through the budget.
"""
from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

from blocklens.config import CONFIG
from blocklens.ingest import chain as chain_ingest
from blocklens.ingest import dexscreener as ds_ingest
from blocklens.ingest.budget import BudgetExhausted
from blocklens.ingest.runner import run_scope
from blocklens.ingest.sources import DexScreenerSource, RpcSource
from blocklens.store import write
from blocklens.store.db import database_available, has_timescaledb, session_scope
from blocklens.store.models import (
    BackfillCheckpoint, IngestRun, Pair, PairSnapshot, Swap, Token, Transfer, Wallet,
)


def _die(msg: str) -> None:
    print(f"error: {msg}", file=sys.stderr)
    raise SystemExit(2)


# --------------------------------------------------------------------------
# discover
# --------------------------------------------------------------------------

def cmd_discover(args: argparse.Namespace) -> int:
    """Find pools created in the recent past, record them, then ask
    DexScreener what it knows about them.

    Run this often. Every hour it does not run is an hour of launches whose
    first 24 hours can still be recovered from logs, but whose *market*
    history at that moment cannot.
    """
    if args.watch:
        return _watch(args)
    hours, offset = args.hours, args.offset_hours
    scope = f"last {hours}h" if not offset else f"{offset}h..{offset + hours}h ago"
    with run_scope(source="chain-discover", scope=scope, chain=args.chain,
                   max_calls=args.max_calls) as ctx:
        rpc = RpcSource(ctx.budget)
        head = rpc.block_number()
        # An offset points the scan at an older window. That is how a run
        # finds tokens whose 24 hours have already closed and can therefore
        # be backfilled completely, rather than ones still in progress.
        end = max(1, head - int(offset * 3600 / CONFIG.block_seconds))
        start = max(1, end - int(hours * 3600 / CONFIG.block_seconds))
        print(f"scanning blocks {start:,}..{end:,} ({scope}) for new pools")

        try:
            cands = chain_ingest.discover_pools(rpc, from_block=start, to_block=end)
        except BudgetExhausted as e:
            print(f"stopped: {e}")
            raise

        # Newest first: a limited run should take the freshest launches,
        # because those are the ones whose 24-hour window is still open.
        cands.sort(key=lambda c: c["created_block"], reverse=True)
        if args.limit:
            cands = cands[:args.limit]
        print(f"candidates: {len(cands)}")
        if not cands:
            return 0

        # Timestamp each creation block, so `created_ts` is real and the
        # gate has something true to check.
        ts_of = rpc.block_timestamps({c["created_block"] for c in cands})
        newest = max(ts_of.values())
        for c in cands:
            c["created_ts"] = datetime.fromtimestamp(ts_of[c["created_block"]], timezone.utc)

        as_of = datetime.fromtimestamp(newest, timezone.utc)
        ctx.add_rows(ds_ingest.seed_tokens(ctx.session, cands, chain=args.chain, as_of_ts=as_of))
        ctx.session.commit()

        by_dex: dict[str, int] = {}
        for c in cands:
            by_dex[c["dex"]] = by_dex.get(c["dex"], 0) + 1
        print("by venue:", ", ".join(f"{k}={v}" for k, v in sorted(by_dex.items())))

        if not args.no_enrich:
            ds = DexScreenerSource(ctx.budget)
            res = ds_ingest.enrich(ctx.session, ds, [c["token_address"] for c in cands],
                                   chain=args.chain)
            ctx.add_rows(res["tokens"] + res["pairs"] + res["snapshots"])
            print(f"dexscreener: {res['tokens']} tokens, {res['pairs']} pairs, "
                  f"{res['snapshots']} snapshots, {len(res['unknown'])} not indexed yet")
            ds.close()
        rpc.close()
        print(f"calls: {ctx.budget.requests}, waited {ctx.budget.waited_seconds:.1f}s on rate limits")
    return 0


def _watch(args: argparse.Namespace) -> int:
    """Run discovery on an interval until interrupted.

    The brief asks for this to be running early, because every hour it is
    not running is an hour of `pair_snapshot` history no later run can
    reconstruct — transfers keep, market state does not.

    Each pass is its own `ingest_run`, so a crash mid-poll is visible in the
    run table rather than hidden inside a long-lived process. A failing pass
    is reported and the loop continues; the next window is still worth
    having.
    """
    every = args.watch
    once = argparse.Namespace(**{**vars(args), "watch": None})
    passes, failures = 0, 0
    print(f"polling every {every}s, Ctrl-C to stop "
          f"(window: last {args.hours}h, limit {args.limit})")
    try:
        while True:
            started = time.time()
            passes += 1
            print()
            print(f"--- pass {passes} at {datetime.now(timezone.utc):%H:%M:%S} UTC")
            try:
                cmd_discover(once)
            except KeyboardInterrupt:
                raise
            except Exception as e:  # noqa: BLE001
                failures += 1
                print(f"pass failed: {type(e).__name__}: {str(e)[:160]}")
            # Measured from the start of the pass, so the cadence does not
            # drift by however long the pass itself took.
            nap = max(5.0, every - (time.time() - started))
            time.sleep(nap)
    except KeyboardInterrupt:
        print()
        print(f"stopped after {passes} pass(es), {failures} failed")
    return 0


# --------------------------------------------------------------------------
# backfill
# --------------------------------------------------------------------------

def _pending(session, chain: str, limit: int | None) -> list[dict]:
    """Tokens with a pool and an unfinished (or unstarted) first window.

    Oldest first, because a launch whose window has already closed can be
    backfilled completely, while a launch an hour old cannot.
    """
    q = (
        select(Token.address, Token.decimals, Token.created_block,
               Pair.address, Pair.quote_token, Pair.dex)
        .join(Pair, (Pair.token_address == Token.address) & (Pair.chain == Token.chain))
        .outerjoin(BackfillCheckpoint,
                   (BackfillCheckpoint.token_address == Token.address)
                   & (BackfillCheckpoint.chain == Token.chain))
        .where(Token.chain == chain, Token.created_block.is_not(None),
               (BackfillCheckpoint.done.is_(None)) | (BackfillCheckpoint.done.is_(False)))
        .order_by(Token.created_block.asc())
    )
    if limit:
        q = q.limit(limit)
    # One token can have several pair rows: the pool we found on-chain, and
    # whatever DexScreener later reported for the same token. Prefer ours —
    # it is the pool whose creation block the window is measured from, and
    # its venue label is one the backfill knows how to read.
    best: dict[str, dict] = {}
    for addr, decimals, created_block, pair_addr, quote, dex in session.execute(q):
        dex = dex or ""
        # Decided by the key's shape, not by the venue label. A pool id is 32
        # bytes and an address is 20, and DexScreener reports a V4 pool as
        # dex "uniswap" with its pool id in the pairAddress field — so
        # trusting the label sent a pool id into an address filter, and the
        # gateway answered "invalid params" 16 tokens into a 105-token run.
        is_pool_id = len(pair_addr or "") > 42
        row = {
            "token_address": addr, "decimals": decimals, "start_block": created_block,
            "quote_address": quote or "", "dex": dex,
            "pair_address": None if is_pool_id else pair_addr,
            "pool_id": pair_addr if is_pool_id else None,
            "_ours": dex in ("uniswap-v3", "uniswap-v4"),
        }
        prev = best.get(addr)
        if prev is None or (row["_ours"] and not prev["_ours"]):
            best[addr] = row
    return sorted(best.values(), key=lambda r: r["start_block"])


def cmd_backfill(args: argparse.Namespace) -> int:
    if not (args.token or args.all_pending):
        _die("give --token ADDRESS or --all-pending")

    with run_scope(source="chain-backfill",
                   scope=args.token or f"all-pending limit={args.limit}",
                   chain=args.chain, max_calls=args.max_calls) as ctx:
        if args.token:
            todo = _pending(ctx.session, args.chain, None)
            todo = [t for t in todo if t["token_address"] == args.token.lower()]
            if not todo:
                _die(f"{args.token} is not a pending token on {args.chain} "
                     f"(unknown, or its window is already complete)")
        else:
            todo = _pending(ctx.session, args.chain, None)
            # Disjoint slices, so several workers can share the queue.
            # Needed because throughput is bounded by per-call round-trip
            # latency rather than by the rate limiter: 45 sequential calls
            # at ~0.25 s each is ~11 s per token however high the bucket is
            # set, and raising it from 4 to 10 req/s measurably changed
            # nothing. Four workers over disjoint slices is the only lever
            # that moves, and it keeps each worker's own limiter intact.
            if args.offset:
                todo = todo[args.offset:]
            if args.limit:
                todo = todo[:args.limit]

        print(f"backfilling {len(todo)} token(s), window = "
              f"{CONFIG.feature_window_hours}h = {CONFIG.blocks_per_window:,} blocks")
        if args.max_cu and not CONFIG.alchemy_enabled:
            # Compute units are an Alchemy meter. On the keyless sources this
            # project runs on, nothing ever charges one, so the counter stays
            # at zero and this ceiling can never be reached. Saying so beats
            # accepting a flag that silently bounds nothing.
            print(f"note: --max-cu {args.max_cu:,} has no effect without "
                  f"ALCHEMY_API_KEY - keyless sources charge no compute units. "
                  f"Use --max-calls to bound this run (currently "
                  f"{ctx.budget.max_calls:,}).")
        rpc = RpcSource(ctx.budget)
        head = rpc.block_number()

        done, failed, probed_inactive = 0, [], 0
        for i, t in enumerate(todo, 1):
            stop = t["start_block"] + CONFIG.blocks_per_window
            if stop > head:
                # The window has not closed yet. Backfilling it now would
                # write a partial window that a later run would read as
                # complete, so it waits.
                print(f"[{i}/{len(todo)}] {t['token_address']} skipped: "
                      f"window closes at block {stop:,}, head is {head:,}")
                continue
            if args.probe:
                try:
                    probe = chain_ingest.probe_activity(
                        rpc, token_address=t["token_address"],
                        start_block=t["start_block"],
                        pair_address=t["pair_address"], pool_id=t["pool_id"])
                except BudgetExhausted as e:
                    print(f"stopping: {e}")
                    break
                if not probe["active"]:
                    probed_inactive += 1
                    continue

            if args.max_cu and ctx.budget.compute_units >= args.max_cu:
                print(f"stopping: CU ceiling for this run reached ({args.max_cu:,})")
                break
            try:
                res = chain_ingest.backfill_token(
                    ctx.session, rpc, ctx.budget, chain=args.chain,
                    token_address=t["token_address"], quote_address=t["quote_address"],
                    start_block=t["start_block"], pair_address=t["pair_address"],
                    pool_id=t["pool_id"], decimals=t["decimals"],
                )
            except BudgetExhausted as e:
                print(f"stopping: {e}")
                break
            except Exception as e:  # noqa: BLE001
                # One malformed token must not end a run of a hundred. The
                # failure is printed and counted, its checkpoint keeps
                # whatever it reached, and the next token proceeds.
                ctx.session.rollback()
                failed.append((t["token_address"], f"{type(e).__name__}: {e}"))
                print(f"[{i}/{len(todo)}] {t['token_address']} FAILED: "
                      f"{type(e).__name__}: {str(e)[:120]}")
                continue
            ctx.add_rows(res["transfers"] + res["swaps"] + res["wallets"])
            done += 1 if res.get("complete") else 0
            print(f"[{i}/{len(todo)}] {t['token_address']} "
                  f"{res['transfers']:>6} transfers {res['swaps']:>5} swaps "
                  f"{res['wallets']:>5} wallets  {res['calls']:>4} calls"
                  f"{'' if res.get('complete') else '  INCOMPLETE'}")

        rpc.close()
        print()
        print(f"complete windows this run: {done}/{len(todo)}")
        if probed_inactive:
            print(f"skipped by probe (no trading found): {probed_inactive}")
        if failed:
            print(f"failed: {len(failed)}")
            for addr, err in failed[:10]:
                print(f"  {addr}  {err[:100]}")
            ctx.notes["failed"] = failed
        print(f"calls: {ctx.budget.requests}, waited {ctx.budget.waited_seconds:.1f}s, "
              f"CU: {ctx.budget.compute_units:,}")
    return 0


# --------------------------------------------------------------------------
# first-hour
# --------------------------------------------------------------------------

def cmd_first_hour(args: argparse.Namespace) -> int:
    """Distinct wallets that bought a token in its first hour.

    Derived from transfers out of the pool, not from `swap.wallet_address`,
    which Phase 1 leaves null on purpose: Part A proved the transfer
    counterparty on an aggregator route is the router, not the trader. A
    token leaving the pool to an address is the one buy signal that is true
    whatever route it took.
    """
    token = args.token.lower()
    with session_scope() as s:
        cp = s.get(BackfillCheckpoint, {"chain": args.chain, "token_address": token})
        if cp is None:
            _die(f"{token} has not been backfilled on {args.chain}")
        if not cp.done:
            print("warning: this token's window is incomplete, so the cohort is partial")

        pairs = s.execute(select(Pair.address).where(
            Pair.chain == args.chain, Pair.token_address == token)).scalars().all()
        pools = {p.lower() for p in pairs} | {chain_ingest.UNISWAP_V4_POOL_MANAGER}

        launch = s.scalar(select(func.min(Transfer.block_ts)).where(
            Transfer.chain == args.chain, Transfer.token_address == token))
        if launch is None:
            print("no transfers recorded for this token")
            return 0
        cutoff = launch + timedelta(hours=args.hours)

        rows = s.execute(
            select(Transfer.to_address,
                   func.count().label("buys"),
                   func.sum(Transfer.value_normalised).label("tokens"),
                   func.min(Transfer.block_ts).label("first_buy"))
            .where(Transfer.chain == args.chain,
                   Transfer.token_address == token,
                   Transfer.from_address.in_(pools),
                   Transfer.block_ts >= launch,
                   Transfer.block_ts < cutoff)
            .group_by(Transfer.to_address)
            .order_by(func.min(Transfer.block_ts))
        ).all()

        print(f"token            {token}")
        print(f"first transfer   {launch:%Y-%m-%d %H:%M:%S} UTC")
        print(f"window           first {args.hours:g}h, to {cutoff:%H:%M:%S} UTC")
        print(f"pools counted    {len(pools) - 1} recorded + the V4 PoolManager")
        print()
        print(f"distinct wallets that bought in the first hour: {len(rows)}")
        print()
        for addr, buys, tokens, first in rows[:args.show]:
            delta = int((first - launch).total_seconds())
            print(f"  {addr}  {buys:>3} buy(s)  {float(tokens):>22,.4f} tokens  "
                  f"+{delta:>5}s")
        if len(rows) > args.show:
            print(f"  ... and {len(rows) - args.show} more")
    return 0


# --------------------------------------------------------------------------
# status
# --------------------------------------------------------------------------

def cmd_status(args: argparse.Namespace) -> int:
    if not database_available():
        _die(f"no database at {CONFIG.database_url}")

    with session_scope() as s:
        def n(model, *where):
            return s.scalar(select(func.count()).select_from(model).where(*where)) or 0

        tokens = n(Token, Token.chain == args.chain)
        pairs = n(Pair, Pair.chain == args.chain)
        transfers = n(Transfer, Transfer.chain == args.chain)
        swaps = n(Swap, Swap.chain == args.chain)
        wallets = n(Wallet, Wallet.chain == args.chain)
        snaps = n(PairSnapshot, PairSnapshot.chain == args.chain)
        complete = n(BackfillCheckpoint, BackfillCheckpoint.chain == args.chain,
                     BackfillCheckpoint.done.is_(True))
        partial = n(BackfillCheckpoint, BackfillCheckpoint.chain == args.chain,
                    BackfillCheckpoint.done.is_(False))

        print(f"chain            {args.chain}")
        print(f"timescaledb      {'yes' if has_timescaledb() else 'no (plain table)'}")
        print(f"tokens           {tokens:,}")
        print(f"pairs            {pairs:,}")
        print(f"pair_snapshots   {snaps:,}")
        print(f"transfers        {transfers:,}")
        print(f"swaps            {swaps:,}")
        print(f"wallets          {wallets:,}")
        print(f"windows complete {complete:,}   in progress {partial:,}")

        span = s.execute(select(func.min(Transfer.block_ts), func.max(Transfer.block_ts))
                         .where(Transfer.chain == args.chain)).first()
        if span and span[0]:
            print(f"transfer span    {span[0]:%Y-%m-%d %H:%M} .. {span[1]:%Y-%m-%d %H:%M} UTC")

        print("\nlast runs")
        runs = s.execute(
            select(IngestRun).where(IngestRun.chain == args.chain)
            .order_by(IngestRun.started_at.desc()).limit(args.runs)
        ).scalars().all()
        if not runs:
            print("  (none)")
        for r in runs:
            took = ((r.finished_at or datetime.now(timezone.utc)) - r.started_at)
            print(f"  #{r.id:<4} {r.started_at:%m-%d %H:%M} {r.source:<16} {r.status:<15} "
                  f"{r.requests_made:>6} calls {r.rows_written:>8} rows "
                  f"{str(timedelta(seconds=int(took.total_seconds()))):>8}"
                  + (f"  {r.error[:60]}" if r.error else ""))

        print("\nbudget this month")
        for src in ("rpc", "dexscreener", "alchemy", "x"):
            reqs, cu = write.read_budget(s, source=src, period=datetime.now(timezone.utc).strftime("%Y-%m"))
            if reqs or cu:
                extra = f", {cu:,} CU" if cu else ""
                print(f"  {src:<12} {reqs:,} requests{extra}")
    return 0


# --------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="ingest", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--chain", default=CONFIG.chain)
    sub = p.add_subparsers(dest="cmd", required=True)

    d = sub.add_parser("discover", help="find new pools on-chain and record them")
    d.add_argument("--limit", type=int, default=100, help="keep the newest N candidates")
    d.add_argument("--hours", type=float, default=6.0, help="how far back to scan")
    d.add_argument("--offset-hours", type=float, default=0.0,
                   help="end the scan this many hours before now, to find "
                        "launches whose feature window has already closed")
    d.add_argument("--max-calls", type=int, default=None)
    d.add_argument("--no-enrich", action="store_true", help="skip the DexScreener pass")
    d.add_argument("--watch", type=float, default=None, metavar="SECONDS",
                   help="keep polling on this interval until interrupted")
    d.set_defaults(func=cmd_discover)

    b = sub.add_parser("backfill", help="pull a token's first window of history")
    b.add_argument("--token", help="a single token address")
    b.add_argument("--all-pending", action="store_true")
    b.add_argument("--limit", type=int, default=100)
    b.add_argument("--max-cu", type=int, default=None,
                   help="stop once this many Alchemy compute units are spent; "
                        "inert on keyless sources, which charge none")
    b.add_argument("--max-calls", type=int, default=None)
    b.add_argument("--offset", type=int, default=0,
                   help="skip the first N pending tokens, so several "
                        "workers can take disjoint slices of the queue")
    b.add_argument("--probe", action="store_true",
                   help="sample 4 windows for any trading before paying for "
                        "the full 44-call backfill; skips dead pools ~10x "
                        "cheaper, at the cost of missing a token whose only "
                        "activity falls between the samples")
    b.set_defaults(func=cmd_backfill)

    f = sub.add_parser("first-hour", help="wallets that bought in a token's first hour")
    f.add_argument("--token", required=True)
    f.add_argument("--hours", type=float, default=1.0)
    f.add_argument("--show", type=int, default=15)
    f.set_defaults(func=cmd_first_hour)

    s = sub.add_parser("status", help="what is in the store, and what it cost")
    s.add_argument("--runs", type=int, default=8)
    s.set_defaults(func=cmd_status)

    # Line-buffered, because the normal way to run `discover --watch` is
    # redirected to a log file that someone tails. Python block-buffers
    # stdout when it is not a terminal, so without this a poller writes
    # nothing to its log for minutes at a time and looks hung.
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except (AttributeError, ValueError):  # not a reconfigurable stream
        pass

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
